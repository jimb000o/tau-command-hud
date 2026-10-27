"""Read-only WebSocket relay between one Tau testnet node and many browsers.

The node's own WebSocket (port 65433) allows 32 connections and rate-limits the
heavy reads (getblocks, getgovernance, gettaustate) to 0.5/s per connection, so
it cannot face the public. This relay holds ONE upstream connection, polls the
node on a fixed schedule, caches the replies and serves every visitor from that
cache. New blocks, mempool changes and governance changes are pushed to all
visitors as soon as the relay sees them.

Visitors speak the same text protocol as the node ("getblocks 12" in, the
node's JSON envelope out), so the HUD's existing live mode works unchanged.
Only the read commands below are accepted; sendtx, createblock and everything
else are refused here and never reach the node.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import signal
import time
from http import HTTPStatus

from websockets.asyncio.client import connect
from websockets.asyncio.server import ServerConnection, broadcast, serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response

log = logging.getLogger("tau-relay")


def _env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


UPSTREAM_URL = os.environ.get("UPSTREAM_URL", "ws://tau-node:65433")
LISTEN_HOST = os.environ.get("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = _env_int("LISTEN_PORT", 8080)
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get(
    "ALLOWED_ORIGINS", "https://tauhud.com,https://www.tauhud.com,https://jimb000o.github.io"
).split(",") if o.strip()]
# Caddy overwrites X-Forwarded-For with the real client address, so the relay
# may trust it when it is only reachable through Caddy.
TRUST_PROXY = os.environ.get("TRUST_PROXY", "1") == "1"
# Mirrors the node's TAU_GOVERNANCE_OPEN_ADMISSION (docker-compose sets both);
# the node does not expose it over RPC, so the page learns it from here.
OPEN_ADMISSION = os.environ.get("TAU_GOVERNANCE_OPEN_ADMISSION", "false").lower() in ("1", "true", "yes")

MAX_CLIENTS = _env_int("MAX_CLIENTS", 500)
MAX_PER_IP = _env_int("MAX_PER_IP", 8)
CLIENT_BURST = _env_float("CLIENT_BURST", 20)
CLIENT_REFILL = _env_float("CLIENT_REFILL_PER_SEC", 2)
# Account / tx lookups go to the node; this caps them across all visitors.
LOOKUP_BURST = _env_float("LOOKUP_BURST", 5)
LOOKUP_REFILL = _env_float("LOOKUP_REFILL_PER_SEC", 2)
LOOKUP_CACHE_SECONDS = _env_float("LOOKUP_CACHE_SECONDS", 10)

BLOCK_POLL = _env_float("BLOCK_POLL_SECONDS", 3)
MEMPOOL_POLL = _env_float("MEMPOOL_POLL_SECONDS", 3)
GOV_POLL = _env_float("GOV_POLL_SECONDS", 15)
STATE_POLL = _env_float("STATE_POLL_SECONDS", 30)
CACHE_BLOCKS = _env_int("CACHE_BLOCKS", 50)        # most a visitor gets from getblocks
# The relay keeps the whole current chain (for /stats and getblockrange), up to
# this many blocks; ~1,200 blocks a day at the testnet's pace, a few KB each.
CHAIN_BLOCKS = _env_int("CHAIN_BLOCKS", 20000)
RANGE_MAX = 100
UPSTREAM_MAX_SIZE = _env_int("UPSTREAM_MAX_SIZE", 64 * 2**20)
# Chain restarts and transactions that left the mempool without a block are
# kept here so /stats can show them across relay restarts.
EVENTS_PATH = os.environ.get("EVENTS_PATH", "/data/events.json")
EVENTS_MAX = 5000
STATS_CACHE_SECONDS = _env_float("STATS_CACHE_SECONDS", 5)
# a tx that leaves the mempool counts as dropped only if no block holds it
# this long afterwards (the block poll may still be catching up)
DROP_GRACE_SECONDS = _env_float("DROP_GRACE_SECONDS", 30)
UPSTREAM_TIMEOUT = _env_float("UPSTREAM_TIMEOUT_SECONDS", 20)
# The node allows heavy reads at burst 2, 0.5/s per connection; stay just under.
HEAVY_COMMANDS = frozenset({"getblocks", "getgovernance", "gettaustate"})
HEAVY_BURST = 2
HEAVY_REFILL = _env_float("HEAVY_REFILL_PER_SEC", 0.45)

HEX = re.compile(r"^[0-9a-fA-F]{40,192}$")
# command -> validator for its arguments (list of strings). Anything not listed
# here is refused.
LOOKUPS = {
    "getbalance": lambda a: len(a) == 1 and HEX.match(a[0]),
    "getsequence": lambda a: len(a) == 1 and HEX.match(a[0]),
    "getaccountstate": lambda a: len(a) == 1 and HEX.match(a[0]),
    "gettxstatus": lambda a: len(a) == 1 and HEX.match(a[0]),
    "getruleoffers": lambda a: 1 <= len(a) <= 2 and HEX.match(a[0]) and (len(a) == 1 or a[1].lower() in ("in", "out", "all")),
}
CACHED = ("getmempool", "getgovernance", "gettaustate")
# Presence: how many HUD pages are connected right now. Just a count, pushed on
# every change and as a heartbeat; nothing about who is behind a connection.
PRESENCE_HEARTBEAT = _env_float("PRESENCE_HEARTBEAT_SECONDS", 30)


def envelope_error(command: str, message: str, code: str) -> str:
    return json.dumps({"status": "error", "command": command,
                       "error": {"code": code, "message": message}}, separators=(",", ":"))


def envelope_ok(command: str, data: dict) -> str:
    return json.dumps({"status": "ok", "command": command, "data": data}, separators=(",", ":"))


class TokenBucket:
    def __init__(self, capacity: float, refill: float):
        self.capacity, self.refill = capacity, refill
        self.tokens, self.last = capacity, time.monotonic()

    def take(self) -> bool:
        now = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.refill)
        self.last = now
        if self.tokens < 1:
            return False
        self.tokens -= 1
        return True

    async def wait(self):
        while not self.take():
            await asyncio.sleep((1 - self.tokens) / self.refill)


class Upstream:
    """One connection to the node; requests are strictly sequential."""

    def __init__(self, url: str):
        self.url = url
        self.ws = None
        self.lock = asyncio.Lock()
        self.connected = asyncio.Event()
        self.heavy = TokenBucket(HEAVY_BURST, HEAVY_REFILL)

    async def run(self):
        backoff = 1.0
        while True:
            try:
                async with connect(self.url, open_timeout=10, max_size=UPSTREAM_MAX_SIZE,
                                   ping_interval=20, ping_timeout=20) as ws:
                    await ws.send("hello version=1")
                    hello = await asyncio.wait_for(ws.recv(), UPSTREAM_TIMEOUT)
                    if not str(hello).startswith("ok"):
                        raise RuntimeError(f"handshake refused: {hello}")
                    log.info("upstream connected: %s (%s)", self.url, hello)
                    self.ws = ws
                    self.connected.set()
                    backoff = 1.0
                    await ws.wait_closed()
            except (OSError, ConnectionClosed, RuntimeError, asyncio.TimeoutError) as exc:
                log.warning("upstream unavailable: %r", exc)
            finally:
                self.ws = None
                self.connected.clear()
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)

    async def request(self, command: str) -> dict | None:
        """Send one command and return the parsed envelope, or None."""
        async with self.lock:
            if command.split()[0] in HEAVY_COMMANDS:
                await self.heavy.wait()
            ws = self.ws
            if ws is None:
                return None
            try:
                await ws.send(command)
                raw = await asyncio.wait_for(ws.recv(), UPSTREAM_TIMEOUT)
            except (ConnectionClosed, asyncio.TimeoutError) as exc:
                log.warning("upstream %s failed: %r", command.split()[0], exc)
                await ws.close()
                return None
        try:
            msg = json.loads(raw)
        except (TypeError, ValueError):
            log.warning("upstream sent non-JSON for %s: %.80s", command, raw)
            return None
        return msg if isinstance(msg, dict) else None


class Relay:
    def __init__(self, upstream_url: str = UPSTREAM_URL):
        self.upstream = Upstream(upstream_url)
        self.clients: set[ServerConnection] = set()
        self.per_ip: dict[str, int] = {}
        self.blocks: dict[str, dict] = {}       # block_hash -> raw block
        self.total_blocks = 0
        self.cache: dict[str, str] = {}         # command -> envelope text
        self.updated: dict[str, float] = {}
        self.lookup_cache: dict[str, tuple[float, str]] = {}
        self.lookup_bucket = TokenBucket(LOOKUP_BURST, LOOKUP_REFILL)
        self.started = time.time()
        self.need_full = True                   # fetch the whole chain on the next block poll
        self.state = self._load_state()         # restarts, dropped txs, last chain seen
        self.mempool_seen: dict[str, dict] = {}  # tx_hash -> summary, while in the mempool
        self.left_mempool: dict[str, dict] = {}  # tx_hash -> summary, waiting for a block
        self.stats_text: str | None = None
        self.stats_at = 0.0

    # ---------- polling ----------
    async def poll_loop(self, every: float, fn):
        while True:
            await self.upstream.connected.wait()
            try:
                await fn()
            except Exception:  # keep polling whatever one reply looked like
                log.exception("poll failed")
            await asyncio.sleep(every)

    async def poll_blocks(self):
        # The whole chain once (at startup, after a reset or a gap), the tail
        # afterwards. The node's getblocks without a limit returns every row.
        full = self.need_full or not self.blocks
        msg = await self.upstream.request("getblocks" if full else "getblocks 20")
        if not msg or msg.get("status") != "ok":
            self._note_error("getblocks", msg)
            return
        data = msg.get("data") or {}
        total = data.get("total", self.total_blocks)
        reset = False
        if self.blocks and isinstance(total, int) and total < self.total_blocks:
            # The node wiped its chain data (testnet restarted on the same genesis):
            # everything cached belongs to a dead chain.
            log.warning("chain reset: node has %s blocks, had %s; dropping cached blocks", total, self.total_blocks)
            self.blocks.clear()
            reset = True
            self.need_full = True
        fresh = [b for b in data.get("blocks") or []
                 if isinstance(b, dict) and b.get("block_hash") and b["block_hash"] not in self.blocks]
        self.total_blocks = total
        self.updated["getblocks"] = time.time()
        if full and not reset:
            self.need_full = False
        if not fresh:
            return
        for b in fresh:
            # a block at a height we already hold replaces the old one (reorg)
            for old in [o for o in self.blocks.values() if self._height(o) == self._height(b)]:
                self.blocks.pop(old["block_hash"], None)
            self.blocks[b["block_hash"]] = b
        ordered = self.ordered_blocks()
        for b in ordered[:-CHAIN_BLOCKS]:
            if self._height(b) > 1:  # block 1 stays: it identifies the chain for restart detection
                self.blocks.pop(b["block_hash"], None)
        heights = [self._height(b) for b in self.ordered_blocks()]
        if not full and heights and heights[-1] - heights[0] + 1 != len(heights):
            self.need_full = True  # more than 20 blocks arrived between two polls
        self.note_chain()
        self.stats_text = None
        fresh.sort(key=self._height)
        if len(fresh) > 5:
            log.info("new blocks: %s..%s (%s)", self._height(fresh[0]), self._height(fresh[-1]), len(fresh))
        else:
            log.info("new blocks: %s", ", ".join(str(self._height(b)) for b in fresh))
        fresh = fresh[-CACHE_BLOCKS:]
        broadcast(self.clients, envelope_ok("getblocks", {
            "blocks": fresh, "total": self.total_blocks, "truncated": True, "pushed": True,
            # reset: the chain restarted, drop everything you had before these blocks
            **({"reset": True} if reset else {})}))

    async def poll_cached(self, command: str, push: bool):
        msg = await self.upstream.request(command)
        if not msg or msg.get("status") != "ok":
            self._note_error(command, msg)
            return
        if command == "getmempool":
            self.track_mempool(msg.get("data") or {})
        text = json.dumps(msg, separators=(",", ":"))
        changed = self.cache.get(command) != text
        self.cache[command] = text
        self.updated[command] = time.time()
        if changed and push:
            broadcast(self.clients, text)

    # ---------- history: restarts, dropped transactions, /stats ----------
    def _load_state(self) -> dict:
        try:
            with open(EVENTS_PATH) as f:
                state = json.load(f)
            if isinstance(state, dict):
                state.setdefault("restarts", [])
                state.setdefault("dropped", [])
                return state
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s: %r; starting a new history", EVENTS_PATH, exc)
        return {"since": time.time(), "chain": None, "restarts": [], "dropped": []}

    def _save_state(self):
        tmp = EVENTS_PATH + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(self.state, f, separators=(",", ":"))
            os.replace(tmp, EVENTS_PATH)
        except OSError as exc:
            if not getattr(self, "_save_warned", False):
                log.warning("cannot write %s: %r; history lives in memory only", EVENTS_PATH, exc)
                self._save_warned = True

    def chain_info(self) -> dict | None:
        """What identifies the chain we hold: block 1 (the genesis block is the
        same on every restart) and the tip."""
        ordered = self.ordered_blocks()
        first = next((b for b in ordered if self._height(b) == 1), None)
        if not first:
            return None
        tip = ordered[-1]
        return {"block1_hash": first["block_hash"], "block1_ts": self._ts(first),
                "tip": self._height(tip), "tip_hash": tip["block_hash"], "tip_ts": self._ts(tip)}

    def _same_chain(self, known: dict, info: dict) -> bool:
        if known.get("block1_hash") != info["block1_hash"]:
            return False
        # same block 1 but another block at the old tip height: not our chain either
        at_tip = next((b for b in self.blocks.values() if self._height(b) == known.get("tip")), None)
        return at_tip is None or at_tip["block_hash"] == known.get("tip_hash")

    def note_chain(self):
        """Record a restart when block 1 differs from the chain seen last time.

        Covers both a reset seen live (getblocks.total dropped) and one that
        happened while the relay was down, when the cache starts empty."""
        info = self.chain_info()
        if not info:
            return
        known = self.state.get("chain")
        if known and not self._same_chain(known, info):
            log.warning("chain restart recorded: old chain ended at #%s", known.get("tip"))
            self.state["restarts"].append({"detected_at": round(time.time()), "old": known,
                                           "new_block1_ts": info["block1_ts"]})
            self.state["restarts"] = self.state["restarts"][-EVENTS_MAX:]
        self.state["chain"] = info
        self._save_state()

    @staticmethod
    def _tx_summary(t: dict) -> dict:
        ops = t.get("operations") if isinstance(t.get("operations"), dict) else {}
        kind = t.get("tx_type") or "user_tx"
        if kind == "user_tx" and ops.get("0"):
            kind = "rule_deploy"
        return {"type": str(kind)[:40], "sender": str(t.get("sender_pubkey") or t.get("sender") or "")[:200]}

    def track_mempool(self, data: dict):
        """A transaction that leaves the mempool and never shows up in a block
        was dropped by the node (refused on re-check, expired or replaced)."""
        now = time.time()
        current = {}
        for t in data.get("transactions") or []:
            if isinstance(t, dict) and t.get("tx_hash"):
                # getmempool entries carry tx_type only on some node versions; "" = unknown
                current[str(t["tx_hash"])] = self.mempool_seen.get(t["tx_hash"]) or {
                    **self._tx_summary(t), "type": str(t.get("tx_type") or "")[:40], "seen": round(now)}
        for h, info in self.mempool_seen.items():
            if h not in current:
                self.left_mempool[h] = {**info, "left": round(now)}
        self.mempool_seen = current
        if not self.left_mempool:
            return
        sealed = {i for b in self.blocks.values() for i in (b.get("tx_ids") or [])}
        changed = False
        for h, info in list(self.left_mempool.items()):
            if h in sealed:
                del self.left_mempool[h]
            elif now - info["left"] >= DROP_GRACE_SECONDS:
                del self.left_mempool[h]
                self.state["dropped"].append({"tx_hash": h, **info})
                changed = True
        if changed:
            self.state["dropped"] = self.state["dropped"][-EVENTS_MAX:]
            self.stats_text = None
            self._save_state()

    @staticmethod
    def _ts(b: dict) -> int | None:
        try:
            return int((b.get("header") or {}).get("timestamp"))
        except (TypeError, ValueError):
            return None

    def stats_json(self) -> str:
        """Compact per-block history of the current chain plus the event log."""
        if self.stats_text and time.monotonic() - self.stats_at < STATS_CACHE_SECONDS:
            return self.stats_text
        accounts: dict[str, int] = {}
        proposers: dict[str, int] = {}
        rows = []
        for b in self.ordered_blocks():
            h = b.get("header") or {}
            types: dict[str, int] = {}
            senders, transfers, volume = set(), 0, 0
            for t in b.get("transactions") or []:
                if not isinstance(t, dict):
                    continue
                s = self._tx_summary(t)
                types[s["type"]] = types.get(s["type"], 0) + 1
                if s["sender"]:
                    senders.add(accounts.setdefault(s["sender"], len(accounts)))
                ops = t.get("operations") if isinstance(t.get("operations"), dict) else {}
                for x in ops.get("1") or []:
                    if isinstance(x, (list, tuple)) and len(x) >= 3:
                        transfers += 1
                        try:
                            volume += int(x[2])
                        except (TypeError, ValueError):
                            pass
            prop = str(h.get("proposer_pubkey") or "")
            rows.append([self._height(b), self._ts(b), sum(types.values()), transfers, volume,
                         proposers.setdefault(prop, len(proposers)), types, sorted(senders)])
        gov = self.governance()
        archived = gov.get("archival_update_details") or []
        self.stats_text = json.dumps({
            "generated_at": round(time.time()),
            "tracking_since": round(self.state.get("since") or self.started),
            "head": self.height(), "canonical_height": self.canonical_height(), "tip_height": self.tip_height(),
            "total_blocks": self.total_blocks,
            "fields": ["height", "timestamp", "txs", "transfers", "volume", "proposer", "types", "senders"],
            "blocks": rows, "accounts": list(accounts), "proposers": list(proposers),
            "restarts": self.state["restarts"],
            "dropped": self.state["dropped"][-500:], "dropped_total": len(self.state["dropped"]),
            "governance": {
                "pending": len(gov.get("pending_updates") or []),
                "scheduled": len(gov.get("scheduled_updates") or []),
                "activated": sum(1 for u in archived if isinstance(u, dict) and u.get("lifecycle") == "activated"),
                "expired": sum(1 for u in archived if isinstance(u, dict) and u.get("lifecycle") != "activated"),
                "validators": len(gov.get("active_validators") or []),
            },
        }, separators=(",", ":"))
        self.stats_at = time.monotonic()
        return self.stats_text

    def _note_error(self, command, msg):
        if msg:
            log.warning("%s: %s", command, (msg.get("error") or {}).get("code"))

    @staticmethod
    def _height(b: dict) -> int:
        try:
            return int((b.get("header") or {}).get("block_number", 0))
        except (TypeError, ValueError):
            return 0

    def ordered_blocks(self) -> list[dict]:
        return sorted(self.blocks.values(), key=self._height)

    def height(self) -> int | None:
        return self._height(self.ordered_blocks()[-1]) if self.blocks else None

    def governance(self) -> dict:
        try:
            return json.loads(self.cache["getgovernance"])["data"]
        except (KeyError, TypeError, ValueError):
            return {}

    def canonical_height(self) -> int | None:
        """Height of the node's canonical head (getgovernance.head_number).

        getblocks counts every stored block, orphans included, so `height` can
        read 1999 while the node's real chain still sits at genesis.
        """
        try:
            return int(self.governance()["head_number"])
        except (KeyError, TypeError, ValueError):
            return None

    def tip_height(self) -> int | None:
        """Highest network tip the node has heard from its peers (patched
        getgovernance.network_tip); None until a peer was seen or on an
        unpatched node."""
        try:
            return int((self.governance().get("network_tip") or {})["number"])
        except (KeyError, TypeError, ValueError):
            return None

    # ---------- visitor commands ----------
    async def answer(self, message: str) -> str:
        parts = message.split()
        if not parts:
            return envelope_error("", "Empty command.", "INVALID_PARAMS")
        cmd, args = parts[0].lower(), parts[1:]

        if cmd == "hello":
            version = message.split("=", 1)[1].strip() if "=" in message else ""
            if version in ("1", "2"):
                return f"ok version={version} env=testnet node=tau-hud-relay"
            return f"error unsupported_version expected=1|2 got={version}"

        if cmd == "getblocks":
            limit = 12
            if args:
                if len(args) > 1 or not args[0].isdigit() or int(args[0]) < 1:
                    return envelope_error(cmd, "Usage: getblocks [limit]", "INVALID_PARAMS")
                limit = min(int(args[0]), CACHE_BLOCKS)
            if "getblocks" not in self.updated:
                return envelope_error(cmd, "Relay is still syncing with the node.", "NOT_READY")
            blocks = self.ordered_blocks()[-limit:]
            return envelope_ok(cmd, {"blocks": blocks, "total": self.total_blocks,
                                     "truncated": len(blocks) < self.total_blocks})

        if cmd == "getblockrange":
            if len(args) != 2 or not all(a.isdigit() for a in args) or not 1 <= int(args[1]) <= RANGE_MAX:
                return envelope_error(cmd, f"Usage: getblockrange <from_height> <count 1..{RANGE_MAX}>", "INVALID_PARAMS")
            if "getblocks" not in self.updated:
                return envelope_error(cmd, "Relay is still syncing with the node.", "NOT_READY")
            start, count = int(args[0]), int(args[1])
            blocks = [b for b in self.ordered_blocks() if start <= self._height(b) < start + count]
            return envelope_ok(cmd, {"blocks": blocks, "from": start, "total": self.total_blocks, "head": self.height()})

        if cmd == "presence":
            return self.presence_envelope()

        if cmd in CACHED:
            if args:
                return envelope_error(cmd, f"Usage: {cmd}", "INVALID_PARAMS")
            return self.cache.get(cmd) or envelope_error(cmd, "Relay is still syncing with the node.", "NOT_READY")

        if cmd in LOOKUPS:
            if not LOOKUPS[cmd](args):
                return envelope_error(cmd, "Invalid arguments.", "INVALID_PARAMS")
            key = " ".join([cmd] + [a.lower() for a in args])
            hit = self.lookup_cache.get(key)
            if hit and time.monotonic() - hit[0] < LOOKUP_CACHE_SECONDS:
                return hit[1]
            if not self.lookup_bucket.take():
                return envelope_error(cmd, "Relay is busy; retry shortly.", "BUSY")
            msg = await self.upstream.request(key)
            if msg is None:
                return envelope_error(cmd, "Node is not reachable right now.", "UPSTREAM_DOWN")
            text = json.dumps(msg, separators=(",", ":"))
            if len(self.lookup_cache) > 5000:
                self.lookup_cache.clear()
            self.lookup_cache[key] = (time.monotonic(), text)
            return text

        return envelope_error(cmd, "This relay is read-only. Allowed: getblocks, getblockrange, getmempool, getgovernance, "
                              "gettaustate, " + ", ".join(LOOKUPS), "FORBIDDEN")

    # ---------- presence ----------
    def presence_envelope(self) -> str:
        return envelope_ok("presence", {"online": len(self.clients), "pushed": True})

    def push_presence(self):
        broadcast(self.clients, self.presence_envelope())

    async def presence_loop(self):
        while True:
            await asyncio.sleep(PRESENCE_HEARTBEAT)
            self.push_presence()

    # ---------- HTTP side: origin check, limits, /health ----------
    def client_ip(self, connection: ServerConnection, request: Request) -> str:
        if TRUST_PROXY and request.headers.get("X-Forwarded-For"):
            return request.headers["X-Forwarded-For"].split(",")[0].strip()
        return str(connection.remote_address[0]) if connection.remote_address else "?"

    def status(self) -> dict:
        now = time.time()
        return {
            "upstream_connected": self.upstream.connected.is_set(),
            "height": self.height(),
            "canonical_height": self.canonical_height(),
            "tip_height": self.tip_height(),
            # the page may make Live the default view only while the node follows a real chain
            "live_default": bool(self.upstream.connected.is_set() and (self.canonical_height() or 0) > 0),
            # true: any account's vote counts; false: only active validators may vote
            "open_governance_admission": OPEN_ADMISSION,
            "total_blocks": self.total_blocks,
            "clients": len(self.clients),
            "online": len(self.clients),
            "age_seconds": {k: round(now - v, 1) for k, v in self.updated.items()},
            "uptime_seconds": round(now - self.started),
        }

    def origin_ok(self, origin: str | None) -> bool:
        if not origin or origin == "null":
            return True  # non-browser clients; rate limits still apply
        if "*" in ALLOWED_ORIGINS or origin in ALLOWED_ORIGINS:
            return True
        return bool(re.match(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$", origin))

    def process_request(self, connection: ServerConnection, request: Request):
        path = request.path.split("?")[0]
        if path in ("/health", "/status"):
            body = json.dumps(self.status()).encode()
            headers = Headers([("Content-Type", "application/json"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", "no-store")])
            ok = self.upstream.connected.is_set() or path == "/status"
            code = HTTPStatus.OK if ok else HTTPStatus.SERVICE_UNAVAILABLE
            return Response(code.value, code.phrase, headers, body)
        if path == "/stats":
            ready = "getblocks" in self.updated
            body = self.stats_json().encode() if ready else b'{"error":"relay is still syncing with the node"}'
            headers = Headers([("Content-Type", "application/json"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", f"public, max-age={int(STATS_CACHE_SECONDS)}")])
            code = HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE
            return Response(code.value, code.phrase, headers, body)
        if request.headers.get("Upgrade", "").lower() != "websocket":
            return connection.respond(HTTPStatus.OK, "Tau HUD read-only relay. Connect with WebSocket; GET /status for health.\n")
        if not self.origin_ok(request.headers.get("Origin")):
            return connection.respond(HTTPStatus.FORBIDDEN, "origin not allowed\n")
        if len(self.clients) >= MAX_CLIENTS:
            return connection.respond(HTTPStatus.SERVICE_UNAVAILABLE, "relay at capacity\n")
        if self.per_ip.get(self.client_ip(connection, request), 0) >= MAX_PER_IP:
            return connection.respond(HTTPStatus.TOO_MANY_REQUESTS, "too many connections from your address\n")
        return None

    async def handler(self, ws: ServerConnection):
        ip = self.client_ip(ws, ws.request)
        self.per_ip[ip] = self.per_ip.get(ip, 0) + 1
        self.clients.add(ws)
        self.push_presence()
        bucket = TokenBucket(CLIENT_BURST, CLIENT_REFILL)
        try:
            async for message in ws:
                if not isinstance(message, str):
                    message = message.decode("utf-8", errors="replace")
                if not bucket.take():
                    reply = envelope_error("rate_limit", "Rate limit exceeded", "RATE_LIMITED")
                else:
                    reply = await self.answer(message.strip())
                await ws.send(reply)
        except ConnectionClosed:
            pass
        finally:
            self.clients.discard(ws)
            self.per_ip[ip] -= 1
            if self.per_ip[ip] <= 0:
                del self.per_ip[ip]
            self.push_presence()

    async def run(self):
        tasks = [
            asyncio.create_task(self.upstream.run()),
            asyncio.create_task(self.poll_loop(BLOCK_POLL, self.poll_blocks)),
            asyncio.create_task(self.poll_loop(MEMPOOL_POLL, lambda: self.poll_cached("getmempool", True))),
            asyncio.create_task(self.poll_loop(GOV_POLL, lambda: self.poll_cached("getgovernance", True))),
            asyncio.create_task(self.poll_loop(STATE_POLL, lambda: self.poll_cached("gettaustate", False))),
            asyncio.create_task(self.presence_loop()),
        ]
        async with serve(self.handler, LISTEN_HOST, LISTEN_PORT, process_request=self.process_request,
                         max_size=512, max_queue=8, ping_interval=30, ping_timeout=30,
                         server_header="tau-hud-relay") as server:
            log.info("relay listening on %s:%s, upstream %s", LISTEN_HOST, LISTEN_PORT, self.upstream.url)
            loop = asyncio.get_running_loop()
            stop = loop.create_future()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, stop.set_result, None)
            await stop
            server.close()
        for t in tasks:
            t.cancel()


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(Relay().run())

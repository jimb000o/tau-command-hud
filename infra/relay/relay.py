"""WebSocket relay between one Tau testnet node and many browsers.

The node's own WebSocket (port 65433) allows 32 connections and rate-limits the
heavy reads (getblocks, getgovernance, gettaustate) to 0.5/s per connection, so
it cannot face the public. This relay holds ONE upstream connection, polls the
node on a fixed schedule, caches the replies and serves every visitor from that
cache. New blocks, mempool changes and governance changes are pushed to all
visitors as soon as the relay sees them.

Visitors speak the same text protocol as the node ("getblocks 12" in, the
node's JSON envelope out), so the HUD's existing live mode works unchanged.
Only the read commands below are accepted, plus one narrow write door for the
testnet wallet (tauhud.com/wallet/): `sendtx` with a transaction the visitor's
browser already signed, and its dry run `checktx`. Keys never reach the relay.
createblock, consensus rule proposals and everything else are refused here and
never reach the node.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import signal
import time
import urllib.parse
from http import HTTPStatus

from websockets.asyncio.client import connect
from websockets.asyncio.server import ServerConnection, broadcast, serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response

from chat import Chat, parse_say
from chatai import ChatAI
from roadmap import Roadmap, parse_say as parse_road_say
from simpredict import SimPredict
from simprops import SimProps
from simvotes import SimVotes, name_of
from simwallet import SimWallet
from slotlease import SlotLease
from island import Island
from txsources import TxSources
from visits import OWN_HOSTS, SITES, Visits

log = logging.getLogger("tau-relay")


def _env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


UPSTREAM_URL = os.environ.get("UPSTREAM_URL", "ws://tau-node:65433")
LISTEN_HOST = os.environ.get("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = _env_int("LISTEN_PORT", 8080)
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get(
    "ALLOWED_ORIGINS", "https://tauhud.com,https://www.tauhud.com,https://jimb000o.github.io,https://agorzilla.com,https://www.agorzilla.com"
).split(",") if o.strip()]
# Caddy overwrites X-Forwarded-For with the real client address, so the relay
# may trust it when it is only reachable through Caddy.
TRUST_PROXY = os.environ.get("TRUST_PROXY", "1") == "1"
# Mirrors the node's TAU_GOVERNANCE_OPEN_ADMISSION (docker-compose sets both);
# the node does not expose it over RPC, so the page learns it from here.
OPEN_ADMISSION = os.environ.get("TAU_GOVERNANCE_OPEN_ADMISSION", "false").lower() in ("1", "true", "yes")

MAX_CLIENTS = _env_int("MAX_CLIENTS", 500)
# Every open tauhud.com page holds two sockets (its own and the shared header's), the HUD
# three, and a closed tab lingers for up to 30 s; so one person with a few tabs needs well
# over 8. 32 still stops a single address from eating the relay.
MAX_PER_IP = _env_int("MAX_PER_IP", 96)   # sockets per address: every open page holds 2 to 4 (header, page, presence, chat); 32 was hit by one person with many tabs
CLIENT_BURST = _env_float("CLIENT_BURST", 20)
CLIENT_REFILL = _env_float("CLIENT_REFILL_PER_SEC", 2)
# Reads answered from the relay's own memory (the cached commands, getblocks,
# getblockrange, presence) get a second, larger budget per connection and are
# never refused: over budget the connection waits for the next token instead.
# A page loading the whole chain in 100-block pages used to lose an answer to
# the general limit and wait for it forever (accounts stopped at block 1,400).
CHAIN_BURST = _env_float("CHAIN_BURST", 40)
CHAIN_REFILL = _env_float("CHAIN_REFILL_PER_SEC", 10)
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
# Every block of the current chain, one JSON line each, so history survives
# relay restarts (the node only hands out its newest ~900 KB of blocks).
CHAIN_PATH = os.environ.get("CHAIN_PATH", "/data/chain.jsonl")
EVENTS_MAX = 5000
# Availability history for /uptime (the status page): one sample a minute,
# folded into hourly buckets, plus a list of outages. Kept for 31 days.
UPTIME_PATH = os.environ.get("UPTIME_PATH", "/data/uptime.json")
UPTIME_SAMPLE = _env_float("UPTIME_SAMPLE_SECONDS", 60)
UPTIME_DAYS = _env_int("UPTIME_DAYS", 31)
# the node counts as in sync while its verified head is at most this far behind the network tip
SYNC_LAG = _env_int("SYNC_LAG_BLOCKS", 2)
# a gap between two blocks longer than this is listed as a chain stall
STALL_SECONDS = _env_int("STALL_SECONDS", 600)
STATS_CACHE_SECONDS = _env_float("STATS_CACHE_SECONDS", 5)
# Testnet health score (GET /health-score): 0-100 from seven factors, weights add up to 100.
HEALTH_BLOCK_SECONDS = _env_float("HEALTH_BLOCK_SECONDS", 60)  # expected block time until the chain shows its own
HEALTH_OK = _env_int("HEALTH_OK_AT", 80)          # at or above: healthy
HEALTH_DEGRADED = _env_int("HEALTH_DEGRADED_AT", 50)  # at or above: degraded, below: down
HEALTH_WEIGHTS = {"node": 20, "sync": 15, "last_block": 20, "pace": 10, "availability": 10, "stability": 15, "mempool": 10}
# a tx that leaves the mempool counts as dropped only if no block holds it
# this long afterwards (the block poll may still be catching up)
DROP_GRACE_SECONDS = _env_float("DROP_GRACE_SECONDS", 30)
UPSTREAM_TIMEOUT = _env_float("UPSTREAM_TIMEOUT_SECONDS", 20)
# The node allows heavy reads at burst 2, 0.5/s per connection; stay just under.
HEAVY_COMMANDS = frozenset({"getblocks", "getgovernance", "gettaustate", "checktx", "getruleconflict"})
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
    # the wallet's inbox: co-signature requests and undo-able (retractable) transfers of one account
    "getapprovalrequests": lambda a: 1 <= len(a) <= 2 and HEX.match(a[0]) and (len(a) == 1 or a[1].lower() in ("in", "out", "all")),
    "getruleoffer": lambda a: len(a) == 1 and len(a[0]) == 64 and HEX.match(a[0]),   # the full text, needed to accept an offer
    "getretractables": lambda a: 1 <= len(a) <= 2 and HEX.match(a[0]) and (len(a) == 1 or a[1].lower() in ("in", "out", "all")),
    # the node's own conflict report for a rule offered to you, before you accept it (advisory, node-local)
    "getruleconflict": lambda a: len(a) == 1 and len(a[0]) == 64 and HEX.match(a[0]),
}
# /rules: who holds one of the testnet's personal-rule (o5) places. The node caps
# them at 2 chain-wide (consensus/approvals.py MAX_TIER_AUTHORS) and has no
# command that lists them, so the relay takes the candidates from the blocks it
# keeps (senders of an o5 rule, acceptors of an offer) and asks the node for each.
RULES_POLL = _env_float("RULES_POLL_SECONDS", 300)
RULE_PLACES = _env_int("RULE_PLACES", 2)
RULES_MAX_CHECKS = _env_int("RULES_MAX_CHECKS", 40)
NEUTRAL_O5 = "(o5[t]:bv[24]={#x000001}:bv[24])"
# /rulewall: every personal rule in the kept blocks, for the rules wall on tauhud.com/rules/
RULEWALL_MAX = _env_int("RULEWALL_MAX", 200)
RULEWALL_MAX_TEXT = 4000
# Fair turns on those places (slotlease.py): the wallet leaves a pre-signed neutral clause here and the relay sends it
# when the holder's turn is over. One switch turns it off on the server without a rebuild (docker compose up -d).
SLOTLEASE_ENABLED = os.environ.get("SLOTLEASE_ENABLED", "1") not in ("0", "false", "no", "")
CACHED = ("getmempool", "getgovernance", "gettaustate")
FROM_MEMORY = CACHED + ("getblocks", "getblockrange", "presence")   # answered without the node: CHAIN_* budget
# The wallet's write door. The visitor's browser builds and signs the
# transaction (BLS, keys stay in the browser); the relay checks only its shape
# and passes it on, never caching it and never logging its content. Proposing a
# consensus rule change stays with node operators (consensus_rule_update is not
# in the list). Both commands share one bucket per address and one for everyone,
# because the relay holds ONE upstream connection and checktx is a heavy call.
WALLET_COMMANDS = ("sendtx", "checktx")
VIA = re.compile(r"^[a-z0-9-]{1,24}(/[a-z]{2})?$")   # a page name: start, rules, card, hud, story/zh …
WALLET_TX_TYPES = frozenset({
    "user_tx", "consensus_rule_vote", "rule_offer", "rule_offer_accept", "rule_offer_reject",
    "approval_request", "transfer_vote", "retractable_transfer", "retract_transfer",
})
TX_MAX_BYTES = _env_int("TX_MAX_BYTES", 8192)
TX_IP_BURST = _env_float("TX_IP_BURST", 6)
TX_IP_REFILL = _env_float("TX_IP_PER_MINUTE", 12) / 60
TX_ALL_BURST = _env_float("TX_ALL_BURST", 20)
TX_ALL_REFILL = _env_float("TX_ALL_PER_MINUTE", 60) / 60
PUBKEY = re.compile(r"^[0-9a-f]{96}$")
SIGNATURE = re.compile(r"^[0-9a-f]{192}$")
# Presence: how many HUD pages are connected right now. Just a count, pushed on
# every change and as a heartbeat; nothing about who is behind a connection.
PRESENCE_HEARTBEAT = _env_float("PRESENCE_HEARTBEAT_SECONDS", 30)
# Community nodes: nodes run with the operator kit (kit/) may report their head
# once a minute ("report key=… name=… height=… head=…"); GET /community lists
# them next to this relay's own node. The key is the reporter's secret; only
# its hash is shown, so nobody can overwrite another node's row. The reporter's
# address is held in memory for the per-IP cap and never shown or logged.
COMMUNITY_MAX = _env_int("COMMUNITY_MAX", 200)
COMMUNITY_PER_IP = _env_int("COMMUNITY_PER_IP", 3)
COMMUNITY_TTL = _env_float("COMMUNITY_TTL_SECONDS", 15 * 60)
COMMUNITY_MIN_INTERVAL = _env_float("COMMUNITY_MIN_INTERVAL_SECONDS", 20)
# The leaderboard (GET /community/board, badges) remembers every node that
# reported in the last BOARD_KEEP_DAYS, across relay restarts: when it first
# reported, when last, and in how many distinct minutes (its uptime).
BOARD_PATH = os.environ.get("BOARD_PATH", "/data/community.json")
BOARD_KEEP_DAYS = _env_float("BOARD_KEEP_DAYS", 30)
BOARD_MAX = _env_int("BOARD_MAX", 1000)
BOARD_SAVE_SECONDS = _env_float("BOARD_SAVE_SECONDS", 60)
BADGE_PATH = re.compile(r"^/community/badge/([0-9a-f]{12})\.svg$")
# The network as our node sees it (GET /peers): every peer the node talked to
# or heard of from another peer (patched getgovernance.peers, see
# node/patches/peer-book.py), kept for PEERS_KEEP_DAYS across restarts. Peer IDs
# only, never addresses.
PEERS_PATH = os.environ.get("PEERS_PATH", "/data/peers.json")
PEERS_KEEP_DAYS = _env_float("PEERS_KEEP_DAYS", 30)
PEERS_MAX = _env_int("PEERS_MAX", 1000)
PEERS_SAVE_SECONDS = _env_float("PEERS_SAVE_SECONDS", 300)
# A peer counts as online once our node has known it for PEER_STEADY seconds
# (test nodes that come and go for a minute never show up) and until
# PEER_ONLINE seconds after it was last seen (no flicker between two polls).
PEER_STEADY = _env_float("PEER_STEADY_SECONDS", 600)
PEER_ONLINE = _env_float("PEER_ONLINE_SECONDS", 1800)
PEER_ID = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{20,128}$")  # base58, like 12D3KooW...
# the network's bootnode, run by IDNI (infra/docker-compose.yml TAU_BOOTSTRAP_PEERS)
BOOTNODE_ID = os.environ.get("BOOTNODE_PEER_ID", "12D3KooWDpWEYxBy8y84AssrPSLaq9DxC7Lncmn5wERJnAWZFnYC")
# Public read API for other sites (documented on tauhud.com/developers/): one
# cached summary and live SVG badges. Versioned so fields can grow without
# breaking embeds; a field is never renamed or removed within v1.
API_BADGE_PATH = re.compile(r"^/api/v1/badge/(height|status|proposals|validators|health)\.svg$")
API_CACHE_SECONDS = _env_float("API_CACHE_SECONDS", 10)
NETWORK = os.environ.get("TAU_NETWORK", "tau-testnet-v2")
REPORT_FIELDS = {
    "key": re.compile(r"^[0-9a-f]{32}$"),
    "name": re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,23}$"),
    "height": re.compile(r"^\d{1,9}$"),
    "tip": re.compile(r"^(\d{1,9}|none)$"),
    "head": re.compile(r"^[0-9a-f]{64}$"),
    "kit": re.compile(r"^[0-9A-Za-z.-]{1,16}$"),
    "ref": re.compile(r"^[0-9a-f]{7,40}$"),
    "peer": re.compile(r"^[1-9A-HJ-NP-Za-km-z]{20,128}$"),  # its libp2p peer ID (kit 3), names it on /peers
}
REPORT_REQUIRED = ("key", "name", "height", "head")


def envelope_error(command: str, message: str, code: str) -> str:
    return json.dumps({"status": "error", "command": command,
                       "error": {"code": code, "message": message}}, separators=(",", ":"))


def wallet_tx(raw: str) -> tuple[str | None, str]:
    """(compact JSON, "") for a signed tx the wallet door accepts, else (None, reason)."""
    if len(raw.encode()) > TX_MAX_BYTES:
        return None, f"Transaction is larger than {TX_MAX_BYTES} bytes."
    try:
        tx = json.loads(raw)
    except ValueError:
        return None, "Transaction is not valid JSON."
    if not isinstance(tx, dict):
        return None, "Transaction must be a JSON object."
    if tx.get("tx_type") not in WALLET_TX_TYPES:
        return None, "This transaction type is not accepted here."
    if not isinstance(tx.get("sender_pubkey"), str) or not PUBKEY.match(tx["sender_pubkey"]):
        return None, "sender_pubkey must be 96 lowercase hex characters."
    if not isinstance(tx.get("signature"), str) or not SIGNATURE.match(tx["signature"]):
        return None, "signature must be 192 lowercase hex characters."
    return json.dumps(tx, separators=(",", ":"), ensure_ascii=False), ""


def envelope_ok(command: str, data: dict) -> str:
    return json.dumps({"status": "ok", "command": command, "data": data}, separators=(",", ":"))



def site_of_origin(origin: str) -> str:
    """Which of our sites a page came from, by its Origin header: "agorzilla", or "" for Tau HUD and anything else."""
    host = urllib.parse.urlsplit(origin or "").hostname or ""
    return next((site for site in SITES if host in OWN_HOSTS[site]), "")

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
            log.warning("upstream sent non-JSON for %s: %.80s", command.split()[0], raw)
            return None
        return msg if isinstance(msg, dict) else None


class Relay:
    def __init__(self, upstream_url: str = UPSTREAM_URL):
        self.upstream = Upstream(upstream_url)
        self.simvotes = SimVotes()   # visitor votes for the simulation (simvotes.py)
        self.simprops = SimProps(self.simvotes)   # rule changes visitors propose to the simulation (simprops.py)
        self.simwallet = SimWallet()   # the testnet wallet's transactions in simulation mode (simwallet.py)
        self.lease = SlotLease(places=RULE_PLACES)   # fair turns on the personal-rule places (slotlease.py)
        self.island = Island()   # White Rabbit Key: the rival candidates' moves as test transactions (island.py)
        # visitors' forecasts for the same rounds, scored from that ballot (simpredict.py)
        self.simpredict = SimPredict(os.environ.get("SIMPREDICT_PATH", "/data/simpredict.json"), votes=self.simvotes, names=name_of)
        self.visits = Visits()   # cookie-free visitor numbers for the site owner (visits.py)
        self.chat = Chat()       # the troll box (chat.py); pushes go to the sockets that joined it
        self.chat_subs: set[ServerConnection] = set()
        self.chatai = ChatAI()   # optional second look by Claude (chatai.py); off without CHAT_AI_KEY
        self.chat_checks: set[asyncio.Task] = set()
        self.chat.on_hide = lambda mid: broadcast(self.chat_subs, envelope_ok("chat", {"hide": [mid]}))
        self.roadmap = Roadmap(self.chat)   # comments on the road-to-mainnet page, same moderation (roadmap.py)
        self.road_subs: set[ServerConnection] = set()
        self.roadmap.on_hide = lambda cid: broadcast(self.road_subs, envelope_ok("roadmap", {"hide": [cid]}))
        self.clients: set[ServerConnection] = set()
        self.per_ip: dict[str, int] = {}
        # connection -> (address, user agent): one person's tabs, pages and reconnects count
        # once in `online`, keyed like the visit count (visits.person: daily salt + address +
        # user agent, in memory only). Nothing is stored in the browser for it; the viewer
        # token older pages send in "hello … viewer=…" is accepted and ignored.
        self.viewers: dict[ServerConnection, tuple[str, str, str]] = {}   # address, user agent, site (from Origin)
        self.via: dict[ServerConnection, str] = {}   # the page that led this socket's visitor to the wallet
        self.blocks: dict[str, dict] = {}       # block_hash -> raw block
        self.total_blocks = 0
        self.cache: dict[str, str] = {}         # command -> envelope text
        self.updated: dict[str, float] = {}
        self.lookup_cache: dict[str, tuple[float, str]] = {}
        self.lookup_bucket = TokenBucket(LOOKUP_BURST, LOOKUP_REFILL)
        self.tx_bucket = TokenBucket(TX_ALL_BURST, TX_ALL_REFILL)
        self.tx_per_ip: dict[str, TokenBucket] = {}
        self.started = time.time()
        self.need_full = True                   # fetch the whole chain on the next block poll
        self.full_limit = CHAIN_BLOCKS          # how many blocks a full fetch asks for
        self.chain_file_ok = True
        self.state = self._load_state()         # restarts, dropped txs, last chain seen
        self.sources = TxSources()              # which transactions came through this relay, for /api/v1/sources
        self.sources_text, self.sources_at = None, 0.0
        self.uptime = self._load_uptime()       # hourly availability buckets and outages
        self.uptime_text: str | None = None
        self.uptime_at = 0.0
        self.health_cache: tuple[float, dict] | None = None
        self.health_text: str | None = None
        self.health_at = 0.0
        self._load_chain()
        self.mempool_seen: dict[str, dict] = {}  # tx_hash -> summary, while in the mempool
        self.left_mempool: dict[str, dict] = {}  # tx_hash -> summary, waiting for a block
        self.stats_text: str | None = None
        self.stats_at = 0.0
        self.community: dict[str, dict] = {}   # node id -> last report (+ "ip", never shown)
        self.community_text: str | None = None
        self.community_at = 0.0
        self.board = self._load_board()          # node id -> leaderboard row, kept across restarts
        self.board_saved_at = 0.0
        self.board_text: str | None = None
        self.rulewall_text: str | None = None   # /rulewall, rebuilt at most once a minute
        self.rulewall_at = 0.0
        self.board_at = 0.0
        self.peer_book = self._load_peers()      # {"since", "peers": {peer id -> row}}, kept across restarts
        self.peers_saved_at = 0.0
        self.peers_text: str | None = None
        self.peers_at = 0.0
        self.summary_data: dict | None = None
        self.summary_at = 0.0
        self.rules_text: str | None = None      # /rules, refreshed by poll_rules

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
        # afterwards. Over WebSocket the node turns a bare getblocks into
        # "getblocks 50" and refuses replies over ~900 KB (PAYLOAD_TOO_LARGE),
        # so the full fetch names a limit and shrinks it until the reply fits;
        # whatever is older than that window comes from the relay's own copy
        # on disk (CHAIN_PATH).
        full = self.need_full or not self.blocks
        if full and not self.total_blocks:
            # learn the chain length first, so the full fetch can ask for just that
            msg = await self.upstream.request("getblocks 1")
            total = ((msg or {}).get("data") or {}).get("total")
            if msg and msg.get("status") == "ok" and isinstance(total, int) and total > 0:
                self.total_blocks = total
            else:
                self._note_error("getblocks", msg)
            return
        cmd = f"getblocks {min(self.full_limit, self.total_blocks)}" if full else f"getblocks {min(20, self.full_limit)}"
        msg = await self.upstream.request(cmd)
        if msg and msg.get("status") == "error" and (msg.get("error") or {}).get("code") == "PAYLOAD_TOO_LARGE":
            self.full_limit = max(1, min(self.full_limit, self.total_blocks) // 2)
            log.info("getblocks reply too large; full fetch now asks for %s blocks", self.full_limit)
            return
        if not msg or msg.get("status") != "ok":
            self._note_error("getblocks", msg)
            return
        data = msg.get("data") or {}
        total = data.get("total", self.total_blocks)
        fetched = [b for b in data.get("blocks") or [] if isinstance(b, dict) and b.get("block_hash")]
        reset = dropped = False
        if self.total_blocks and isinstance(total, int) and total < self.total_blocks:
            # The node wiped its chain data (testnet restarted on the same genesis):
            # everything cached belongs to a dead chain.
            log.warning("chain reset: node has %s blocks, had %s; dropping cached blocks", total, self.total_blocks)
            self.blocks.clear()
            reset = True
        elif full and self.blocks and self._other_chain(fetched):
            # typically right after a relay start: the blocks on disk are from a chain that is gone
            log.warning("held blocks belong to an earlier chain; dropping them")
            self.blocks.clear()
            dropped = True
            if self.state.get("chain"):
                self._record_restart(self.state["chain"])
                self.state["chain"] = None
        prev_top = self.height()
        fresh = [b for b in fetched if b["block_hash"] not in self.blocks]
        self.total_blocks = total
        self.updated["getblocks"] = time.time()
        if reset:
            self.need_full = True
        elif full:
            self.need_full = False
        if not fresh:
            return
        fresh.sort(key=self._height)
        if not full and prev_top is not None and self._height(fresh[0]) > prev_top + 1:
            self.need_full = True  # more than 20 blocks arrived between two polls
        rewrite = reset or dropped or not self.chain_file_ok
        replaced = []
        for b in fresh:
            # a block at a height we already hold replaces the old one (reorg)
            for old in [o for o in self.blocks.values() if self._height(o) == self._height(b)]:
                self.blocks.pop(old["block_hash"], None)
                replaced.append(self._height(b))
                rewrite = True
            self.blocks[b["block_hash"]] = b
        if replaced and prev_top is not None and not (reset or dropped):
            # depth: how many blocks of the chain we held were replaced, counted from its old tip
            self._record_reorg(min(replaced), prev_top - min(replaced) + 1)
        ordered = self.ordered_blocks()
        if len(ordered) > CHAIN_BLOCKS * 1.1:  # trim in batches so the file is not rewritten every block
            for b in ordered[:-CHAIN_BLOCKS]:
                if self._height(b) > 1:  # block 1 stays: it identifies the chain for restart detection
                    self.blocks.pop(b["block_hash"], None)
            rewrite = True
        self._save_chain(None if rewrite else fresh)
        self.note_chain()
        self.stats_text = self.community_text = self.board_text = None
        if len(fresh) > 5:
            log.info("new blocks: %s..%s (%s)", self._height(fresh[0]), self._height(fresh[-1]), len(fresh))
        else:
            log.info("new blocks: %s", ", ".join(str(self._height(b)) for b in fresh))
        fresh = fresh[-CACHE_BLOCKS:]
        broadcast(self.clients, envelope_ok("getblocks", {
            "blocks": fresh, "total": self.total_blocks, "truncated": True, "pushed": True,
            # reset: the chain restarted, drop everything you had before these blocks
            **({"reset": True} if reset else {})}))

    def _other_chain(self, fetched: list[dict]) -> bool:
        """True when the node's blocks contradict the ones loaded from disk
        below their tip (a replaced tip block is a reorg, not a new chain)."""
        top = self.height() or 0
        held = {self._height(b): b["block_hash"] for b in self.blocks.values()}
        return any(1 <= self._height(b) <= top - 3 and held.get(self._height(b)) not in (None, b["block_hash"])
                   for b in fetched)

    # ---------- the relay's own copy of the chain ----------
    def _load_chain(self):
        try:
            with open(CHAIN_PATH) as f:
                for line in f:
                    try:
                        b = json.loads(line)
                    except ValueError:
                        continue  # a line cut short by a crash
                    if isinstance(b, dict) and b.get("block_hash"):
                        for old in [o for o in self.blocks.values() if self._height(o) == self._height(b)]:
                            self.blocks.pop(old["block_hash"], None)
                        self.blocks[b["block_hash"]] = b
        except FileNotFoundError:
            pass
        except OSError as exc:
            log.warning("cannot read %s: %r", CHAIN_PATH, exc)
        if self.blocks:
            log.info("loaded %s blocks from %s (up to #%s)", len(self.blocks), CHAIN_PATH, self.height())

    def _save_chain(self, appended: list[dict] | None):
        """Append new blocks, or rewrite the file (appended=None) after a
        reset, a reorg or a trim."""
        try:
            if appended is None:
                tmp = CHAIN_PATH + ".tmp"
                with open(tmp, "w") as f:
                    for b in self.ordered_blocks():
                        f.write(json.dumps(b, separators=(",", ":")) + "\n")
                os.replace(tmp, CHAIN_PATH)
            else:
                with open(CHAIN_PATH, "a") as f:
                    for b in appended:
                        f.write(json.dumps(b, separators=(",", ":")) + "\n")
            self.chain_file_ok = True
        except OSError as exc:
            self.chain_file_ok = False
            if not getattr(self, "_chain_warned", False):
                log.warning("cannot write %s: %r; the chain lives in memory only", CHAIN_PATH, exc)
                self._chain_warned = True

    async def poll_cached(self, command: str, push: bool):
        msg = await self.upstream.request(command)
        if not msg or msg.get("status") != "ok":
            self._note_error(command, msg)
            return
        if command == "getmempool":
            self.track_mempool(msg.get("data") or {})
        if command == "getgovernance" and isinstance(msg.get("data"), dict):
            # served on its own at /peers; it changes with every sync and would
            # otherwise push governance to every visitor each poll
            peers = msg["data"].pop("peers", None)
            if isinstance(peers, list):
                self.note_peers(peers)
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
                state.setdefault("reorgs", [])
                return state
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s: %r; starting a new history", EVENTS_PATH, exc)
        return {"since": time.time(), "chain": None, "restarts": [], "dropped": [], "reorgs": []}

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
        # same block 1 but another block at the old tip height: not our chain either,
        # unless that height is within 3 of the current tip (a reorg, as in _other_chain)
        at_tip = next((b for b in self.blocks.values() if self._height(b) == known.get("tip")), None)
        if at_tip is None or at_tip["block_hash"] == known.get("tip_hash"):
            return True
        return known.get("tip", 0) > (self.height() or 0) - 3

    def note_chain(self):
        """Record a restart when block 1 differs from the chain seen last time.

        Covers both a reset seen live (getblocks.total dropped) and one that
        happened while the relay was down, when the cache starts empty."""
        info = self.chain_info()
        if not info:
            return
        known = self.state.get("chain")
        if known and not self._same_chain(known, info):
            self._record_restart(known, info["block1_ts"])
        self.state["chain"] = info
        self._save_state()

    def _record_reorg(self, height: int, depth: int):
        log.warning("reorg: blocks from #%s replaced (depth %s)", height, depth)
        self.state["reorgs"].append({"at": round(time.time()), "height": height, "depth": depth})
        self.state["reorgs"] = self.state["reorgs"][-EVENTS_MAX:]
        self._save_state()

    def _record_restart(self, old: dict, new_block1_ts: int | None = None):
        log.warning("chain restart recorded: old chain ended at #%s", old.get("tip"))
        self.state["restarts"].append({"detected_at": round(time.time()), "old": old, "new_block1_ts": new_block1_ts})
        self.state["restarts"] = self.state["restarts"][-EVENTS_MAX:]
        self._save_state()

    # ---------- availability history: /uptime ----------
    def _load_uptime(self) -> dict:
        state = None
        try:
            with open(UPTIME_PATH) as f:
                state = json.load(f)
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s: %r; starting a new uptime history", UPTIME_PATH, exc)
        if not isinstance(state, dict):
            state = {"since": round(time.time()), "hours": {}, "incidents": [], "last_beat": None}
        state.setdefault("hours", {})
        state.setdefault("incidents", [])
        state.setdefault("last_beat", None)
        now = round(time.time())
        last = state.get("last_beat")
        # still-open outages ended when the relay stopped; the time it was away is a relay outage
        for inc in state["incidents"]:
            if inc.get("end") is None:
                inc["end"] = last or now
        if last and now - last > 2.5 * UPTIME_SAMPLE:
            state["incidents"].append({"kind": "relay", "start": last, "end": now})
        state.pop("open", None)
        self.uptime_open: dict[str, dict] = {}  # kind -> the incident still going on
        return state

    def _save_uptime(self):
        tmp = UPTIME_PATH + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(self.uptime, f, separators=(",", ":"))
            os.replace(tmp, UPTIME_PATH)
        except OSError as exc:
            if not getattr(self, "_uptime_warned", False):
                log.warning("cannot write %s: %r; uptime lives in memory only", UPTIME_PATH, exc)
                self._uptime_warned = True

    def sample_uptime(self, now: float | None = None):
        """One availability sample: is the node connected and answering, and is
        its verified head at the network tip? Opens and closes outages."""
        now = round(now if now is not None else time.time())
        fresh = now - self.updated.get("getblocks", 0) < 3 * max(BLOCK_POLL, UPTIME_SAMPLE / 2)
        node_ok = self.upstream.connected.is_set() and fresh
        canon, tip = self.canonical_height(), self.tip_height()
        lag = (tip - canon) if node_ok and canon is not None and tip is not None else None
        synced = node_ok and canon is not None and canon > 0 and (lag is None or lag <= SYNC_LAG)
        hour = str(now - now % 3600)
        bucket = self.uptime["hours"].setdefault(hour, [0, 0, 0])
        bucket[0] += 1
        bucket[1] += node_ok
        bucket[2] += synced
        # health score of this minute: [3] sum, [4] lowest, [5] samples (hours from before the score have none)
        score = self.health(now, node_ok=node_ok, cached=False)["score"]
        bucket.extend([0, 100, 0][len(bucket) - 3:])
        bucket[4] = score if not bucket[5] else min(bucket[4], score)
        bucket[3] += score
        bucket[5] += 1
        opened = self.uptime_open
        for kind, bad, detail in (("node", not node_ok, None),
                                  ("sync", node_ok and not synced, {"canonical": canon, "tip": tip})):
            inc = opened.get(kind)
            if bad and inc is None:
                inc = opened[kind] = {"kind": kind, "start": now, "end": None}
                self.uptime["incidents"].append(inc)
            if inc is not None and detail and lag is not None:
                inc["max_lag"] = max(inc.get("max_lag", 0), lag)
            if not bad and inc is not None:
                inc["end"] = now
                del opened[kind]
        cutoff = now - UPTIME_DAYS * 86400
        self.uptime["hours"] = {h: v for h, v in self.uptime["hours"].items() if int(h) >= cutoff - 3600}
        self.uptime["incidents"] = [i for i in self.uptime["incidents"]
                                    if i.get("end") is None or i["end"] >= cutoff][-EVENTS_MAX:]
        self.uptime["last_beat"] = now
        self.uptime_text = None
        self._save_uptime()

    async def uptime_loop(self):
        while True:
            await asyncio.sleep(UPTIME_SAMPLE)
            try:
                self.sample_uptime()
            except Exception:
                log.exception("uptime sample failed")

    def chain_stalls(self, since: float) -> list[dict]:
        """Gaps between consecutive blocks of the current chain longer than
        STALL_SECONDS: the network itself produced no block for that long."""
        out, prev = [], None
        for b in self.ordered_blocks():
            ts = self._ts(b)
            if not ts or self._height(b) < 1:
                continue  # block 0 (genesis) carries timestamp 0
            if prev and ts - prev[1] > STALL_SECONDS and ts >= since:
                out.append({"after": prev[0], "start": prev[1], "end": ts})
            prev = (self._height(b), ts)
        return out[-200:]

    def uptime_json(self) -> str:
        now = time.time()
        if self.uptime_text and now - self.uptime_at < STATS_CACHE_SECONDS:
            return self.uptime_text
        cutoff = now - UPTIME_DAYS * 86400
        hours = sorted(([int(h), *v] for h, v in self.uptime["hours"].items()), key=lambda r: r[0])
        incidents = [{k: v for k, v in i.items()} for i in self.uptime["incidents"]][-500:]
        tip_block = self.ordered_blocks()[-1] if self.blocks else None
        self.uptime_text = json.dumps({
            "generated_at": round(now), "since": self.uptime.get("since"),
            "sample_seconds": UPTIME_SAMPLE, "sync_lag_blocks": SYNC_LAG, "stall_seconds": STALL_SECONDS,
            "fields": ["hour", "samples", "node_ok", "synced", "score_sum", "score_min", "score_samples"],
            "hours": hours, "incidents": incidents,
            "restarts": [{"detected_at": r.get("detected_at"), "old_tip": (r.get("old") or {}).get("tip"),
                          "old_tip_ts": (r.get("old") or {}).get("tip_ts"), "new_block1_ts": r.get("new_block1_ts")}
                         for r in self.state["restarts"] if (r.get("detected_at") or 0) >= cutoff],
            "reorgs": [r for r in self.state["reorgs"] if (r.get("at") or 0) >= cutoff],
            "stalls": self.chain_stalls(cutoff),
            "last_block_ts": self._ts(tip_block) if tip_block else None,
            "status": self.status(),
        }, separators=(",", ":"))
        self.uptime_at = now
        return self.uptime_text

    # ---------- testnet health score: /health-score ----------
    def expected_block_seconds(self) -> float:
        """Typical time between blocks: the median gap of the last 100 blocks,
        leaving out stalls, so a slow hour shows against the chain's own pace."""
        ts = [self._ts(b) for b in self.ordered_blocks()[-101:] if self._height(b) >= 1]
        ts = [t for t in ts if t]
        gaps = sorted(b - a for a, b in zip(ts, ts[1:]) if 0 < b - a <= STALL_SECONDS)
        if len(gaps) < 5:
            return HEALTH_BLOCK_SECONDS
        return float(min(600, max(5, gaps[len(gaps) // 2])))

    def health(self, now: float | None = None, node_ok: bool | None = None, cached: bool = True) -> dict:
        """Is the testnet healthy, as far as our node can tell? Seven factors,
        each worth part of 100 points; the breakdown says why."""
        now = now if now is not None else time.time()
        if cached and self.health_cache and 0 <= now - self.health_cache[0] < STATS_CACHE_SECONDS:
            return self.health_cache[1]
        if node_ok is None:
            fresh = now - self.updated.get("getblocks", 0) < 3 * max(BLOCK_POLL, UPTIME_SAMPLE / 2)
            node_ok = self.upstream.connected.is_set() and fresh
        lin = lambda x, good, bad: max(0.0, min(1.0, (x - bad) / (good - bad)))  # 1 at good, 0 at bad
        W, factors = HEALTH_WEIGHTS, []

        def add(key, label, frac, value, note=""):
            factors.append({"key": key, "label": label, "weight": W[key], "points": round(W[key] * frac, 1),
                            "value": value, "note": note})

        add("node", "Node answering", 1.0 if node_ok else 0.0, "yes" if node_ok else "no",
            "" if node_ok else "our node does not answer the relay")
        canon, tip = self.canonical_height(), self.tip_height()
        lag = (tip - canon) if canon is not None and tip is not None else None
        if not node_ok or not canon:
            add("sync", "In sync with the network", 0.0, "unknown" if not node_ok else "syncing",
                "no verified head" if node_ok else "node not answering")
        else:
            add("sync", "In sync with the network", 1.0 if lag is None else lin(lag, SYNC_LAG, 30),
                "in sync" if lag is None or lag <= 0 else f"{lag} blocks behind",
                "no peer tip known yet" if lag is None else "")
        exp = self.expected_block_seconds()
        ordered = [b for b in self.ordered_blocks() if self._height(b) >= 1 and self._ts(b)]
        last_ts = self._ts(ordered[-1]) if ordered else None
        if last_ts is None:
            add("last_block", "Time since the last block", 0.0, "no blocks", "")
        else:
            age = max(0, now - last_ts)
            add("last_block", "Time since the last block", lin(age, max(3 * exp, 180), 1800), round(age),
                f"usually {round(exp)} s between blocks")
        if ordered:
            window = max(600.0, min(3600.0, now - self._ts(ordered[0])))
            made = sum(1 for b in ordered if self._ts(b) > now - window)
            want = window / exp
            add("pace", "Blocks in the last hour", lin(made / want, 0.75, 0), made,
                f"about {round(want)} expected" + (f" in {round(window / 60)} min" if window < 3600 else ""))
        else:
            add("pace", "Blocks in the last hour", 0.0, 0, "")
        cut = now - 86400
        samples = synced = 0
        for h, v in self.uptime["hours"].items():
            if int(h) >= cut - 3599:
                samples += v[0]
                synced += v[2]
        if samples:
            add("availability", "Live and in sync, 24 h", lin(synced / samples, 0.99, 0.8), round(synced / samples, 4),
                f"{samples} checks")
        else:
            add("availability", "Live and in sync, 24 h", 1.0, None, "no record yet")
        restarts = sum(1 for r in self.state["restarts"] if (r.get("detected_at") or 0) >= cut)
        reorgs = sum(1 for r in self.state["reorgs"] if (r.get("at") or 0) >= cut)
        stalls = len(self.chain_stalls(cut))
        lost = 10 * restarts + 3 * reorgs + 4 * stalls
        add("stability", "Restarts, reorgs and stalls, 24 h", max(0.0, 1 - lost / W["stability"]),
            {"restarts": restarts, "reorgs": reorgs, "stalls": stalls},
            "a restart costs 10 points, a stall over 10 min 4, a reorg 3")
        # The mempool should list only transactions no block holds yet. IDNI #81: the node keeps
        # sealed ones listed as pending for up to an hour; every such entry costs its share.
        sealed = {i for b in self.blocks.values() for i in (b.get("tx_ids") or [])}
        pool = list(self.mempool_seen.items())
        stale = sum(1 for h, _ in pool if h in sealed)
        real = [now - i["seen"] for h, i in pool if h not in sealed and i.get("seen")]
        oldest = max(real) if real else 0
        add("mempool", "Waiting transactions", (1 - stale / len(pool) if pool else 1.0) * lin(oldest, 600, 3600),
            {"waiting": len(pool), "sealed": stale, "oldest": round(oldest)},
            "already in a block but still listed as waiting (IDNI #81)" if stale
            else "a real one waiting long costs points" if pool else "mempool empty")
        known = [{"id": "IDNI #81", "url": "https://github.com/IDNI/tau-testnet/issues/81",
                  "title": "The node lists transactions as waiting that are already in a block",
                  "count": stale, "points": round(W["mempool"] * stale / len(pool), 1)}] if stale else []
        score = round(sum(f["points"] for f in factors))
        # no answer from our node, or no block for 30 minutes, is down whatever the other factors say
        halted = factors[2]["points"] == 0
        state = "down" if not node_ok or halted or score < HEALTH_DEGRADED else "healthy" if score >= HEALTH_OK else "degraded"
        out = {"score": score, "state": state, "label": {"healthy": "Healthy", "degraded": "Degraded", "down": "Down"}[state],
               "at": round(now), "expected_block_seconds": round(exp), "factors": factors, "known_issues": known}
        self.health_cache = (now, out)
        return out

    def health_json(self) -> str:
        now = time.time()
        if self.health_text and now - self.health_at < STATS_CACHE_SECONDS:
            return self.health_text
        hours = sorted((int(h), round(v[3] / v[5], 1), v[4]) for h, v in self.uptime["hours"].items()
                       if len(v) >= 6 and v[5])
        self.health_text = json.dumps({
            "generated_at": round(now), **self.health(now),
            "thresholds": {"healthy": HEALTH_OK, "degraded": HEALTH_DEGRADED},
            "fields": ["hour", "average", "lowest"], "hours": hours,
        }, separators=(",", ":"))
        self.health_at = now
        return self.health_text

    def rule_candidates(self) -> list[str]:
        """Accounts that may hold an o5 rule: newest first, from the kept blocks."""
        seen: dict[str, int] = {}
        for b in self.ordered_blocks():
            h = self._height(b)
            for t in b.get("transactions") or []:
                if not isinstance(t, dict):
                    continue
                ops = t.get("operations") if isinstance(t.get("operations"), dict) else {}
                rule = ops.get("0") if isinstance(ops.get("0"), str) else ""
                if (t.get("tx_type") in (None, "user_tx") and "o5" in rule) or t.get("tx_type") == "rule_offer_accept":
                    who = str(t.get("sender_pubkey") or "").lower()
                    if HEX.match(who):
                        seen[who] = h
        return sorted(seen, key=lambda a: -seen[a])

    def rulewall(self) -> list[dict]:
        """Every personal (o5) rule the kept blocks hold, one entry per rule text: who wrote it first and every
        account that took the same rule since (deployed the same text, or accepted it as an offer), newest first.
        A removal (the neutral clause) is not a rule."""
        flat = lambda x: re.sub(r"\s+", "", x)
        neutral = {flat(NEUTRAL_O5), flat(NEUTRAL_O5[1:-1]), flat("always (" + NEUTRAL_O5 + ").")}
        rules: dict[str, dict] = {}
        for b in self.ordered_blocks():
            h, ts = self._height(b), (b.get("header") or {}).get("timestamp")
            for t in b.get("transactions") or []:
                if not isinstance(t, dict):
                    continue
                kind = t.get("tx_type") or "user_tx"
                ops = t.get("operations") if isinstance(t.get("operations"), dict) else {}
                text = ops.get("0") if kind == "user_tx" else t.get("rule_text") if kind == "rule_offer_accept" else None
                who = str(t.get("sender_pubkey") or "").lower()
                if not isinstance(text, str) or "o5" not in text or not HEX.match(who) or len(text) > RULEWALL_MAX_TEXT:
                    continue
                key = flat(text)
                if key in neutral:
                    continue
                r = rules.get(key)
                if r is None:
                    r = rules[key] = {"text": text.strip(), "author": who, "first": h, "first_ts": ts, "users": [], "last": h}
                if who not in r["users"]:
                    r["users"].append(who)
                r["last"] = h
        out = sorted(rules.values(), key=lambda r: (-len(r["users"]), -r["last"]))
        return out[:RULEWALL_MAX]

    def rulewall_json(self) -> str:
        now = time.time()
        if self.rulewall_text is None or now - self.rulewall_at >= 60:
            self.rulewall_at = now
            self.rulewall_text = json.dumps({"rules": self.rulewall(), "height": self.height(), "generated_at": round(now)},
                                            separators=(",", ":"))
        return self.rulewall_text

    async def poll_rules(self):
        holders = []
        for i, a in enumerate(self.rule_candidates()[:RULES_MAX_CHECKS]):
            if i:
                await asyncio.sleep(2.5)   # getruleoffers is in the node's expensive tier (0.5/s)
            msg = await self.upstream.request(f"getruleoffers {a} in")
            data = (msg or {}).get("data") if (msg or {}).get("status") == "ok" else None
            if not isinstance(data, dict):
                return   # keep the last answer rather than publish a partial one
            for c in data.get("accepted_clauses") or []:
                if str(c.get("target_stream")) in ("5", "o5") and re.sub(r"\s+", "", str(c.get("clause_body") or "")) not in (NEUTRAL_O5, NEUTRAL_O5[1:-1]):
                    holders.append(a)
                    break
        self.rules_text = json.dumps({"places": RULE_PLACES, "taken": min(len(holders), RULE_PLACES), "holders": holders,
                                      "checked_at": round(time.time())}, separators=(",", ":"))
        self.lease.set_holders(holders)
        if SLOTLEASE_ENABLED:
            await self.end_turns()

    async def end_turns(self):
        """Send the pre-signed removal of each holder whose turn is over: checked first, one at a time, after poll_rules."""
        for addr, raw in self.lease.due():
            chk = await self.upstream.request(f"checktx {raw}")
            if not chk or chk.get("status") != "ok" or (chk.get("data") or {}).get("ok") is False:
                why = str(((chk or {}).get("error") or {}).get("message") or "node not reachable")
                if chk is not None:
                    self.lease.sent(addr, False, "stale: " + why)
                log.info("turn over for %s…: removal not sent (%s)", addr[:12], why[:80])
                continue
            res = await self.upstream.request(f"sendtx {raw}")
            ok = bool(res) and res.get("status") == "ok" and (res.get("data") or {}).get("ok") is not False
            why = "" if ok else str(((res or {}).get("error") or {}).get("message") or "node not reachable")
            if res is not None:
                self.lease.sent(addr, ok, why)
            if ok:
                self.sources.note((res.get("data") or {}).get("tx_hash"), "", "relay")
            log.info("turn over for %s…: removal %s %s", addr[:12], "sent" if ok else "refused", ((res or {}).get("data") or {}).get("tx_hash") or why[:80])

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

    def head_hash(self) -> str | None:
        return self.governance().get("head_hash") or None

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
    async def answer(self, message: str, ip: str = "?", ws: ServerConnection | None = None) -> str:
        parts = message.split()
        if not parts:
            return envelope_error("", "Empty command.", "INVALID_PARAMS")
        cmd, args = parts[0].lower(), parts[1:]

        if cmd == "hello":
            fields = dict(a.split("=", 1) for a in args if "=" in a)
            version = fields.get("version", "")
            if version not in ("1", "2"):
                return f"error unsupported_version expected=1|2 got={version}"
            # "viewer=<token>" from older pages is accepted for compatibility and ignored:
            # people are told apart by address and user agent now (see handler)
            return f"ok version={version} env=testnet node=tau-hud-relay"

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

        if cmd == "chat":
            return self.chat_command(args, ws)

        if cmd == "roadmap":
            return self.roadmap_command(args, ws)

        if cmd == "report":
            return self.report(args, ip)

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

        if cmd == "islandmove":   # White Rabbit Key: a rival's move in a visitor's game, sent by the island bot (island.py)
            if len(args) != 2:
                return envelope_error(cmd, "Usage: islandmove <candidate> <kind>", "INVALID_PARAMS")
            ok, data = self.island.accept(args[0].lower(), args[1].lower(), ip)
            return envelope_ok(cmd, data) if ok else envelope_error(cmd, data, "FORBIDDEN" if "off" in data else "INVALID_PARAMS")

        if cmd == "leasetx":
            return await self.lease_deposit(message[len(parts[0]):].strip(), ip)

        if cmd == "via":   # the Tau HUD page that led this visitor to the wallet, kept with the hashes it sends
            if len(args) != 1 or not VIA.match(args[0]):
                return envelope_error(cmd, "Usage: via <page>", "INVALID_PARAMS")
            if ws:
                self.via[ws] = args[0]
            return envelope_ok(cmd, {"via": args[0]})

        if cmd in WALLET_COMMANDS:
            return await self.wallet(cmd, message[len(parts[0]):].strip(), ip, self.viewers.get(ws, (0, 0, ""))[2] if ws else "",
                                     self.via.get(ws, "") if ws else "")

        return envelope_error(cmd, "Not allowed here. Allowed: getblocks, getblockrange, getmempool, getgovernance, "
                              "gettaustate, presence, report, via, islandmove, " + ", ".join(LOOKUPS) + ", " + ", ".join(WALLET_COMMANDS)
                              + " (a transaction signed in your browser)", "FORBIDDEN")

    async def wallet(self, cmd: str, raw: str, ip: str, site: str = "", via: str = "") -> str:
        """Pass one browser-signed transaction (or its dry run) to the node."""
        tx, why = wallet_tx(raw)
        if tx is None:
            return envelope_error(cmd, why, "INVALID_PARAMS")
        if len(self.tx_per_ip) > 10000:
            self.tx_per_ip.clear()
        mine = self.tx_per_ip.setdefault(ip, TokenBucket(TX_IP_BURST, TX_IP_REFILL))
        if not mine.take():
            return envelope_error(cmd, "Too many transactions from here; wait a minute.", "RATE_LIMITED")
        if not self.tx_bucket.take():
            return envelope_error(cmd, "Relay is busy; retry shortly.", "BUSY")
        msg = await self.upstream.request(f"{cmd} {tx}")
        if msg is None:
            return envelope_error(cmd, "Node is not reachable right now.", "UPSTREAM_DOWN")
        if cmd == "sendtx" and msg.get("status") == "ok" and (msg.get("data") or {}).get("ok") is not False:
            self.sources.note((msg.get("data") or {}).get("tx_hash"), site, via)   # for "where the transactions come from"
        return json.dumps(msg, separators=(",", ":"))

    async def lease_deposit(self, raw: str, ip: str) -> str:
        """Keep a pre-signed neutral clause for the holder's turn (slotlease.py), once the node has checked it."""
        if not SLOTLEASE_ENABLED:
            return envelope_error("leasetx", "Turns on the rule places are switched off on this relay.", "FORBIDDEN")
        tx, why = self.lease.check(raw)
        if tx is None:
            return envelope_error("leasetx", why, "INVALID_PARAMS")
        mine = self.tx_per_ip.setdefault(ip, TokenBucket(TX_IP_BURST, TX_IP_REFILL))
        if not mine.take() or not self.tx_bucket.take():
            return envelope_error("leasetx", "Too many transactions from here; wait a minute.", "RATE_LIMITED")
        chk = await self.upstream.request(f"checktx {raw}")
        if chk is None:
            return envelope_error("leasetx", "Node is not reachable right now.", "UPSTREAM_DOWN")
        if chk.get("status") != "ok" or (chk.get("data") or {}).get("ok") is False:
            return json.dumps({"status": "error", "command": "leasetx", "error": (chk.get("error") or {"message": "refused by the node"})}, separators=(",", ":"))
        return json.dumps({"status": "ok", "command": "leasetx", "data": self.lease.deposit(raw, tx)}, separators=(",", ":"))

    # ---------- community nodes ----------
    def report(self, args: list[str], ip: str) -> str:
        fields = dict(a.split("=", 1) for a in args if "=" in a)
        if (len(fields) != len(args) or any(k not in REPORT_FIELDS or not REPORT_FIELDS[k].match(v) for k, v in fields.items())
                or any(k not in fields for k in REPORT_REQUIRED)):
            return envelope_error("report", "Usage: report key=<32 hex> name=<1-24 of A-Z a-z 0-9 . _ -> height=<n> "
                                  "head=<64 hex> [tip=<n>|none] [kit=<version>] [ref=<commit>] [peer=<peer id>]", "INVALID_PARAMS")
        if "tauhud" in fields["name"].lower():
            return envelope_error("report", "That name is reserved.", "INVALID_PARAMS")
        now = time.time()
        self.expire_community(now)
        node_id = hashlib.sha256(fields["key"].encode()).hexdigest()[:12]
        known = self.community.get(node_id)
        if known and now - known["last_seen"] < COMMUNITY_MIN_INTERVAL:
            return envelope_error("report", f"At most one report per {int(COMMUNITY_MIN_INTERVAL)} s.", "RATE_LIMITED")
        if not known:
            if len(self.community) >= COMMUNITY_MAX:
                return envelope_error("report", "The community list is full.", "BUSY")
            if sum(1 for n in self.community.values() if n["ip"] == ip) >= COMMUNITY_PER_IP:
                return envelope_error("report", f"At most {COMMUNITY_PER_IP} nodes per address.", "RATE_LIMITED")
        self.community[node_id] = {
            "id": node_id, "name": fields["name"], "height": int(fields["height"]),
            "tip": int(fields["tip"]) if fields.get("tip", "none") != "none" else None,
            "head": fields["head"], "kit": fields.get("kit"), "ref": fields.get("ref"), "peer": fields.get("peer"),
            # first_seen survives a silence and a relay restart through the leaderboard
            "first_seen": known["first_seen"] if known else self.board.get(node_id, {}).get("first_seen", now),
            "last_seen": now, "ip": ip,
        }
        self.community_text = None
        if not known:
            log.info("community node joined: %s (%s)", fields["name"], node_id)
        self.note_board(self.community[node_id], now)
        return envelope_ok("report", {"id": node_id, "agrees": self.agreement(self.community[node_id], self.hash_at())})

    def hash_at(self) -> dict[int, str]:
        """height -> block hash of the chain we hold (one block per height)."""
        return {self._height(b): b["block_hash"] for b in self.blocks.values()}

    def agreement(self, node: dict, hashes: dict[int, str]) -> str:
        """How a reported head compares with this relay's chain: "same" (our
        block at that height has that hash), "different", "ahead" (we have no
        block that high yet) or "unknown" (we hold no block at that height)."""
        if not hashes:
            return "unknown"
        if node["height"] > max(hashes):
            return "ahead"
        ours = hashes.get(node["height"])
        if ours is None:
            return "unknown"
        return "same" if ours == node["head"] else "different"

    def expire_community(self, now: float):
        stale = [k for k, n in self.community.items() if now - n["last_seen"] > COMMUNITY_TTL]
        for node_id in stale:
            del self.community[node_id]
        if stale:
            self.community_text = self.board_text = None

    # ---------- the network as our node sees it: /peers ----------
    def _load_peers(self) -> dict:
        try:
            with open(PEERS_PATH) as f:
                book = json.load(f)
            if isinstance(book, dict) and isinstance(book.get("peers"), dict):
                book.setdefault("since", round(time.time()))
                return book
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s: %r; starting a new peer list", PEERS_PATH, exc)
        return {"since": round(time.time()), "peers": {}}

    def _save_peers(self, now: float):
        self.peers_saved_at = now
        tmp = PEERS_PATH + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(self.peer_book, f, separators=(",", ":"))
            os.replace(tmp, PEERS_PATH)
        except OSError as exc:
            if not getattr(self, "_peers_warned", False):
                log.warning("cannot write %s: %r; the peer list lives in memory only", PEERS_PATH, exc)
                self._peers_warned = True

    def note_peers(self, peers: list, now: float | None = None):
        """Merge the node's peer book into ours: keep the earliest first sight
        and the latest contact; `connected` is whatever the node says now."""
        now = now if now is not None else time.time()
        book = self.peer_book["peers"]

        def stamp(v):
            try:
                v = float(v)
            except (TypeError, ValueError):
                return None
            return round(min(v, now)) if v > 0 else None

        new = False
        live = set()
        for p in peers[:PEERS_MAX]:
            if not isinstance(p, dict) or not PEER_ID.match(str(p.get("id", ""))):
                continue
            pid = p["id"]
            row = book.get(pid)
            if row is None:
                new = True
                row = book[pid] = {"first_seen": stamp(p.get("first_seen")) or round(now),
                                   "last_direct": None, "last_heard": None, "head": None}
            for k in ("last_direct", "last_heard"):
                v = stamp(p.get(k))
                if v and (row[k] is None or v > row[k]):
                    row[k] = v
            if isinstance(p.get("head"), int) and p["head"] >= 0:
                row["head"] = p["head"]
            if p.get("connected") is True:
                live.add(pid)
        for pid, row in book.items():
            row["connected"] = pid in live
        cutoff = now - PEERS_KEEP_DAYS * 86400
        for pid in [k for k, r in book.items() if max(r["last_direct"] or 0, r["last_heard"] or 0, r["first_seen"]) < cutoff]:
            del book[pid]
        if len(book) > PEERS_MAX:
            last = lambda k: max(book[k]["last_direct"] or 0, book[k]["last_heard"] or 0)
            for pid in sorted(book, key=last)[:len(book) - PEERS_MAX]:
                del book[pid]
        self.peers_text = None
        if new or now - self.peers_saved_at >= PEERS_SAVE_SECONDS:
            self._save_peers(now)

    def peers_json(self) -> str:
        now = time.time()
        if self.peers_text is None or now - self.peers_at >= STATS_CACHE_SECONDS:
            self.peers_at = now
            # community nodes from kit 3 on say which peer they are; the newest report wins
            named = {b["peer"]: b for b in sorted(self.board.values(), key=lambda b: b["last_seen"])
                     if b.get("peer") and b["peer"] != BOOTNODE_ID}
            rows = []
            for pid, r in self.peer_book["peers"].items():
                last = max(r["last_direct"] or 0, r["last_heard"] or 0) or None
                kit = named.get(pid)
                steady = pid == BOOTNODE_ID or (last or 0) - r["first_seen"] >= PEER_STEADY
                rows.append({"id": pid, "label": "IDNI bootnode" if pid == BOOTNODE_ID else None,
                             "community": {"id": kit["id"], "name": kit["name"]} if kit else None,
                             "steady": steady, "online": steady and now - (last or 0) < PEER_ONLINE,
                             "first_seen": r["first_seen"], "last_direct": r["last_direct"],
                             "last_heard": r["last_heard"], "last_seen": last, "head": r["head"],
                             "connected": bool(r.get("connected"))})
            rows.sort(key=lambda r: (r["label"] is None, -(r["last_seen"] or 0)))

            def within(seconds, direct_only=False):
                return sum(1 for r in rows if ((r["last_direct"] if direct_only else r["last_seen"]) or 0) >= now - seconds)

            self.peers_text = json.dumps({
                "peers": rows,
                # met = our node exchanged something with it; seen = met or listed by a peer
                "counts": {"connected": sum(r["connected"] for r in rows), "online": sum(r["online"] for r in rows),
                           "met_30m": within(1800, True), "met_24h": within(86400, True),
                           "seen_24h": within(86400), "seen_30d": len(rows)},
                "bootnode": BOOTNODE_ID, "since": self.peer_book["since"],
                "steady_seconds": PEER_STEADY, "online_seconds": PEER_ONLINE,
                # the validator keys, so a page can link a node card on to the validator profile
                "validators": list((self.governance() or {}).get("active_validators") or []),
                "keep_days": PEERS_KEEP_DAYS, "generated_at": round(now),
            }, separators=(",", ":"))
        return self.peers_text

    # ---------- leaderboard ----------
    def _load_board(self) -> dict[str, dict]:
        try:
            with open(BOARD_PATH) as f:
                rows = json.load(f)
            if isinstance(rows, dict):
                return {k: v for k, v in rows.items() if isinstance(v, dict) and v.get("first_seen")}
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s: %r; starting a new leaderboard", BOARD_PATH, exc)
        return {}

    def _save_board(self, now: float):
        self.board_saved_at = now
        tmp = BOARD_PATH + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(self.board, f, separators=(",", ":"))
            os.replace(tmp, BOARD_PATH)
        except OSError as exc:
            if not getattr(self, "_board_warned", False):
                log.warning("cannot write %s: %r; the leaderboard lives in memory only", BOARD_PATH, exc)
                self._board_warned = True

    def note_board(self, node: dict, now: float):
        row = self.board.get(node["id"])
        new = row is None
        if new:
            row = self.board[node["id"]] = {"id": node["id"], "first_seen": now, "minutes": 0, "counted_at": 0}
        # one uptime minute per minute with a report, however often it reports
        if now - row["counted_at"] >= 55:
            row["minutes"] += 1
            row["counted_at"] = now
        row.update(name=node["name"], last_seen=now, height=node["height"], kit=node["kit"], ref=node["ref"])
        if node.get("peer"):
            row["peer"] = node["peer"]
        self.board_text = None
        cutoff = now - BOARD_KEEP_DAYS * 86400
        for k in [k for k, r in self.board.items() if r["last_seen"] < cutoff]:
            del self.board[k]
        if len(self.board) > BOARD_MAX:
            for k in sorted(self.board, key=lambda k: self.board[k]["last_seen"])[:len(self.board) - BOARD_MAX]:
                del self.board[k]
        if new or now - self.board_saved_at >= BOARD_SAVE_SECONDS:
            self._save_board(now)

    @staticmethod
    def node_uptime(row: dict, now: float) -> float | None:
        """Share of the minutes since its first report in which the node
        reported; None for the first ten minutes (too few to say)."""
        span = (now - row["first_seen"]) / 60
        return None if span < 10 else round(min(1.0, row["minutes"] / span), 3)

    def board_rows(self, now: float) -> list[dict]:
        self.expire_community(now)
        hashes = self.hash_at()
        rows = []
        for r in self.board.values():
            live = self.community.get(r["id"])
            rows.append({"id": r["id"], "name": r["name"], "first_seen": round(r["first_seen"]),
                         "last_seen": round(r["last_seen"]), "online": live is not None,
                         "days": int((now - r["first_seen"]) // 86400), "uptime": self.node_uptime(r, now),
                         "height": r.get("height"), "kit": r.get("kit"), "ref": r.get("ref"),
                         "agrees": self.agreement(live, hashes) if live else None})
        # online first, then the longest running, then the steadiest
        rows.sort(key=lambda r: (not r["online"], r["first_seen"], -(r["uptime"] or 0), r["name"].lower()))
        return rows

    def board_json(self) -> str:
        """Cached like /community: the endpoint is public and the build indexes the chain."""
        now = time.time()
        self.expire_community(now)
        if self.board_text is None or now - self.board_at >= STATS_CACHE_SECONDS:
            self.board_at = now
            self.board_text = json.dumps({"nodes": self.board_rows(now), "keep_days": BOARD_KEEP_DAYS,
                                          "generated_at": round(now)}, separators=(",", ":"))
        return self.board_text

    def badge_svg(self, node_id: str, zh: bool = False) -> str:
        """A small embeddable badge: "Tau HUD node | running 12 d"."""
        now = time.time()
        self.expire_community(now)
        row = self.board.get(node_id)
        if row is None:
            right, online = "unknown node", False
        else:
            age = now - row["first_seen"]
            span = f"{int(age // 86400)} d" if age >= 86400 else f"{int(age // 3600)} h" if age >= 3600 else ""
            online = node_id in self.community
            right = (f"running {span}" if span else "new node") if online else \
                (f"offline · ran {span}" if span else "offline")
            up = self.node_uptime(row, now)
            if span and up is not None:  # days alone would flatter a node that was mostly down
                right += f" · {round(up * 100)} % up"
        return self.badge("Tau HUD node", right, online, zh)

    @staticmethod
    def badge(left: str, right: str, on: bool, zh: bool = False) -> str:
        """Shields-style two-part badge in the site's colours: black, white,
        phosphor green when the value is good news (red with ?lang=zh, as on the Chinese site)."""
        bg, fg = (("#ff3b52" if zh else "#39ff8a"), "#000") if on else ("#2a2a2e", "#ebebee")
        # Verdana 11px averages about 6.6 px per character; padding 6 px each side
        lw, rw = int(len(left) * 6.6) + 12, int(len(right) * 6.6) + 12
        esc = lambda t: t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{lw + rw}" height="20" role="img" aria-label="{esc(left)}: {esc(right)}">'
                f'<title>{esc(left)}: {esc(right)}</title>'
                f'<rect width="{lw}" height="20" fill="#09090a"/><rect x="{lw}" width="{rw}" height="20" fill="{bg}"/>'
                f'<g font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">'
                f'<text x="{lw / 2:.1f}" y="14" fill="#fff">{esc(left)}</text>'
                f'<text x="{lw + rw / 2:.1f}" y="14" fill="{fg}">{esc(right)}</text>'
                f'</g></svg>')

    # ---------- public API (/api/v1/…) ----------
    def summary(self) -> dict:
        """Everything a widget needs in one small object, cached for API_CACHE_SECONDS."""
        now = time.time()
        if self.summary_data is not None and now - self.summary_at < API_CACHE_SECONDS:
            return self.summary_data
        st = self.status()
        gov = self.governance()
        connected = st["upstream_connected"] and "getblocks" in self.updated
        canon, tip = st["canonical_height"], st["tip_height"]
        synced = bool(connected and canon and (tip is None or tip - canon <= SYNC_LAG))
        stamps = [t for t in (self._ts(b) for b in self.ordered_blocks()[-11:]) if t is not None]
        pace = round((stamps[-1] - stamps[0]) / (len(stamps) - 1), 1) if len(stamps) > 1 and stamps[-1] > stamps[0] else None
        archived = [u for u in gov.get("archival_update_details") or [] if isinstance(u, dict)]
        activated = sum(1 for u in archived if u.get("lifecycle") == "activated")
        fee = None
        m = re.search(r"o9\[t\][^=]*=\s*\{\s*#x([0-9a-fA-F]+)", str(gov.get("consensus_rules") or ""))
        if m:
            fee = int(m.group(1), 16)
        try:
            mempool = len(json.loads(self.cache["getmempool"])["data"].get("transactions") or [])
        except (KeyError, TypeError, ValueError, AttributeError):
            mempool = None
        proposals = {"waiting": len(gov.get("pending_updates") or []),
                     "agreed": len(gov.get("scheduled_updates") or []),
                     "in_force": activated, "dropped": len(archived) - activated}
        proposals["total"] = sum(proposals.values())
        self.summary_data = {
            "api": "tauhud/v1", "network": NETWORK, "generated_at": round(now),
            "status": "synced" if synced else "catching_up" if connected else "offline",
            "height": canon, "tip_height": tip,
            "last_block_ts": stamps[-1] if stamps else None,
            "last_block_age_seconds": round(now - stamps[-1]) if stamps else None,
            "pace_seconds": pace,
            "spec_revision": 1 + activated if gov else None,
            "base_fee": fee,
            "validators": len(gov.get("active_validators") or []) if gov else None,
            "proposals": proposals if gov else None,
            "mempool": mempool,
            "viewers": st["online"],
            "community_nodes": st["community_nodes"],
            "health": st.get("health"),
            "docs": "https://tauhud.com/developers/",
        }
        self.summary_at = now
        return self.summary_data

    def api_badge(self, kind: str, zh: bool = False) -> str:
        badge = lambda left, right, on: self.badge(left, right, on, zh)
        s = self.summary()
        up = s["status"] == "synced"
        p = s["proposals"] or {}
        if kind == "height":
            return badge("Tau block", f"{s['height']:,}" if s["height"] is not None else "offline", up)
        if kind == "status":
            return badge("Tau testnet", {"synced": "live", "catching_up": "catching up", "offline": "offline"}[s["status"]], up)
        if kind == "proposals":
            if not p:
                return badge("Tau rule changes", "unknown", False)
            right = f"{p['in_force']} in force"
            if p["waiting"] or p["agreed"]:
                right = f"{p['waiting'] + p['agreed']} coming up · " + right
            return badge("Tau rule changes", right, bool(p["waiting"] or p["agreed"]))
        if kind == "validators":
            n = s["validators"]
            return badge("Tau validators", "unknown" if n is None else f"{n} active", bool(n))
        h = s["health"] if isinstance(s["health"], dict) else {}
        score = h.get("score")
        return badge("Tau testnet health", "not rated yet" if score is None else f"{score} / 100",
                     score is not None and score >= HEALTH_OK)

    def community_json(self) -> str:
        """Cached like /stats: the endpoint is public, the build walks the chain once."""
        now = time.time()
        self.expire_community(now)
        if self.community_text is not None and now - self.community_at < STATS_CACHE_SECONDS:
            return self.community_text
        hashes = self.hash_at()
        nodes = [{**{k: v for k, v in n.items() if k != "ip"}, "agrees": self.agreement(n, hashes),
                  "age_seconds": round(now - n["last_seen"])}
                 for n in sorted(self.community.values(), key=lambda n: (-n["height"], n["name"].lower()))]
        self.community_at = now
        self.community_text = json.dumps({
            "reference": {"name": "tauhud.com", "height": self.canonical_height(), "head": self.head_hash(),
                          "tip": self.tip_height(), "upstream_connected": self.upstream.connected.is_set()},
            "nodes": nodes, "ttl_seconds": int(COMMUNITY_TTL), "generated_at": round(now),
        }, separators=(",", ":"))
        return self.community_text

    # ---------- presence ----------
    def online(self, site: str | None = None) -> int:
        """People, not sockets: one browser's tabs, pages and reconnects count once
        (same address and user agent, hashed with the day's salt like the visit count).
        With a site ("agorzilla"), only the people whose page came from that site."""
        people = {self.visits.person(ip, ua) for ip, ua, s in self.viewers.values() if site is None or s == site}
        return len(people) + (0 if site else sum(1 for c in self.clients if c not in self.viewers))

    def online_sites(self) -> dict:
        return {s: self.online(s) for s in SITES}

    def presence_envelope(self) -> str:
        return envelope_ok("presence", {"online": self.online(), "sites": self.online_sites(), "pushed": True})

    def chat_command(self, args: list[str], ws: ServerConnection | None) -> str:
        """The troll box over the socket: join / leave / say / report (chat.py has the rules)."""
        sub = args[0].lower() if args else ""
        ip, ua = (self.viewers.get(ws) or ("?", ""))[:2] if ws is not None else ("?", "")
        person = self.visits.person(ip, ua)
        if sub == "join":
            if ws is not None:
                self.chat_subs.add(ws)
            return envelope_ok("chat", self.chat.recent())
        if sub == "leave":
            self.chat_subs.discard(ws)
            return envelope_ok("chat", {"left": True})
        if sub == "say":
            parsed = parse_say(args[1:])
            r = self.chat.say(person, *parsed) if parsed else {"error": "bad", "message": "Usage: chat say <token> <a> <b> <c> <text>"}
            if r.get("ok"):
                broadcast(self.chat_subs - {ws} if ws is not None else self.chat_subs, envelope_ok("chat", {"new": [r["msg"]]}))
                if self.chatai.on:
                    task = asyncio.create_task(self.chat_ai_check(r["msg"]["id"], r["msg"]["text"]))
                    self.chat_checks.add(task)
                    task.add_done_callback(self.chat_checks.discard)
                return envelope_ok("chat", {"sent": r["msg"]})
            return envelope_error("chat", r["message"], r["error"].upper())
        if sub == "report" and len(args) == 3 and args[1].isdigit():
            r = self.chat.report(person, int(args[1]), args[2])
            return envelope_ok("chat", {"reported": int(args[1]), "hidden": r.get("hidden", False)}) if r.get("ok") else envelope_error("chat", r["message"], "BAD")
        return envelope_error("chat", "Usage: chat join | leave | say <token> <a> <b> <c> <text> | report <id> <token>", "INVALID_PARAMS")

    def roadmap_command(self, args: list[str], ws: ServerConnection | None) -> str:
        """Comments on the road-to-mainnet page: join / leave / get / say / report / delete / agree (roadmap.py has the rules)."""
        sub = args[0].lower() if args else ""
        ip, ua = (self.viewers.get(ws) or ("?", ""))[:2] if ws is not None else ("?", "")
        person = self.visits.person(ip, ua)
        road = self.roadmap
        if sub == "join":
            if ws is not None:
                self.road_subs.add(ws)
            return envelope_ok("roadmap", road.counts())
        if sub == "leave":
            self.road_subs.discard(ws)
            return envelope_ok("roadmap", {"left": True})
        if sub == "get" and len(args) == 2:
            return envelope_ok("roadmap", road.thread(args[1]))
        if sub == "say":
            parsed = parse_road_say(args[1:])
            r = road.say(person, *parsed) if parsed else {"error": "bad", "message": "Usage: roadmap say <token> <a> <b> <c> <item> <part> <text>"}
            if r.get("ok"):
                c = r["comment"]
                broadcast(self.road_subs - {ws} if ws is not None else self.road_subs, envelope_ok("roadmap", {"new": [c]}))
                if self.chatai.on:
                    task = asyncio.create_task(self.road_ai_check(c["id"], c["text"]))
                    self.chat_checks.add(task)
                    task.add_done_callback(self.chat_checks.discard)
                return envelope_ok("roadmap", {"sent": c})
            return envelope_error("roadmap", r["message"], r["error"].upper())
        if sub in ("report", "delete") and len(args) == 3 and args[1].isdigit():
            cid = int(args[1])
            if sub == "delete":
                return envelope_ok("roadmap", {"deleted": cid}) if road.delete(cid, args[2]) else envelope_error("roadmap", "Only the browser that wrote it can delete it.", "BAD")
            r = road.report(person, cid, args[2])
            return envelope_ok("roadmap", {"reported": cid, "hidden": r.get("hidden", False)}) if r.get("ok") else envelope_error("roadmap", r["message"], "BAD")
        if sub == "agree" and len(args) == 3:
            r = road.add_agree(person, args[1], args[2])
            if r.get("ok"):
                if r.get("counted"):
                    broadcast(self.road_subs - {ws} if ws is not None else self.road_subs, envelope_ok("roadmap", {"agree": {args[1]: r["agree"]}}))
                return envelope_ok("roadmap", {"agreed": args[1], "agree": r["agree"], "counted": r["counted"]})
            return envelope_error("roadmap", r["message"], "BAD")
        return envelope_error("roadmap", "Usage: roadmap join | leave | get <item> | say <token> <a> <b> <c> <item> <part> <text> | report <id> <token> | delete <id> <token> | agree <item> <token>", "INVALID_PARAMS")

    async def road_ai_check(self, cid: int, text: str):
        """The same live moderator reads each road-to-mainnet comment once more."""
        why = await self.chatai.verdict(text, self.roadmap.context(cid))
        if why and self.roadmap.flag(cid):
            log.info("roadmap: the AI moderator removed comment %s (%s)", cid, why)

    async def chat_ai_check(self, mid: int, text: str):
        """The live moderator's second look: a message Claude flags disappears for everyone (chat.flag pushes the hide)."""
        why = await self.chatai.verdict(text, self.chat.before(mid))
        if why and self.chat.flag(mid):
            log.info("chat: the AI moderator removed message %s (%s)", mid, why)

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
        self.expire_community(now)
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
            "online": self.online(),
            "online_sites": self.online_sites(),
            "community_nodes": len(self.community),
            # the newest chain restarts and reorgs the relay noticed (full lists on /stats)
            "restarts": [{"detected_at": r.get("detected_at"), "old_tip": (r.get("old") or {}).get("tip")}
                         for r in self.state["restarts"][-10:]],
            "reorgs": self.state["reorgs"][-10:],
            # testnet health score, full breakdown and history on /health-score
            "health": {k: v for k, v in self.health(now).items() if k in ("score", "state", "label")},
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
        path, _, query = request.path.partition("?")
        zh = "lang=zh" in query.split("&")
        if path in ("/health", "/status"):
            body = json.dumps(self.status()).encode()
            headers = Headers([("Content-Type", "application/json"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", "no-store")])
            ok = self.upstream.connected.is_set() or path == "/status"
            code = HTTPStatus.OK if ok else HTTPStatus.SERVICE_UNAVAILABLE
            return Response(code.value, code.phrase, headers, body)
        ip = self.client_ip(connection, request)
        seen = self.visits.route(path, query, ip, request.headers)
        if seen is not None:
            code = HTTPStatus(seen[0])
            headers = Headers([("Content-Type", seen[1]), ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", "no-store"), ("Referrer-Policy", "no-referrer"),
                               ("X-Robots-Tag", "noindex")])
            return Response(code.value, code.phrase, headers, seen[2])
        said = self.chat.route(path, query) if path.startswith("/chat") else self.roadmap.route(path, query) if path.startswith("/roadmap") else None
        if said is not None:
            code = HTTPStatus(said[0])
            headers = Headers([("Content-Type", said[1]), ("Access-Control-Allow-Origin", "*"), ("Cache-Control", "no-store"),
                               ("Referrer-Policy", "no-referrer"), ("X-Robots-Tag", "noindex")])
            return Response(code.value, code.phrase, headers, said[2])
        sim = self.simvotes.route(path, query, ip)
        if sim is not None and path == "/sim/votes":
            sim[1]["wallet"] = self.simwallet.count()   # pages fetch /sim/wallet only when this grows
        if sim is None:
            sim = self.simwallet.route(path, query, ip)
        if sim is None:
            prop = self.simprops.route(path, query, ip)
            sim = None if prop is None else (200, prop)
        if sim is None:
            sim = self.simpredict.route(path, query, ip)
        if sim is not None:
            code = HTTPStatus(sim[0])
            headers = Headers([("Content-Type", "application/json"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", "no-store")])
            return Response(code.value, code.phrase, headers, json.dumps(sim[1], separators=(",", ":")).encode())
        isl = self.island.route(path)
        if isl is not None:
            headers = Headers([("Content-Type", "application/json"), ("Access-Control-Allow-Origin", "*"), ("Cache-Control", "no-store")])
            return Response(HTTPStatus.OK.value, HTTPStatus.OK.phrase, headers, json.dumps(isl, separators=(",", ":")).encode())
        if path == "/stats":
            ready = "getblocks" in self.updated
            body = self.stats_json().encode() if ready else b'{"error":"relay is still syncing with the node"}'
            headers = Headers([("Content-Type", "application/json"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", f"public, max-age={int(STATS_CACHE_SECONDS)}")])
            code = HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE
            return Response(code.value, code.phrase, headers, body)
        if path == "/community/board":
            headers = Headers([("Content-Type", "application/json"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", "public, max-age=30")])
            return Response(HTTPStatus.OK.value, HTTPStatus.OK.phrase, headers, self.board_json().encode())
        badge = BADGE_PATH.match(path)
        if badge:
            headers = Headers([("Content-Type", "image/svg+xml; charset=utf-8"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", "public, max-age=300")])
            return Response(HTTPStatus.OK.value, HTTPStatus.OK.phrase, headers, self.badge_svg(badge.group(1), zh).encode())
        if path == "/uptime":
            headers = Headers([("Content-Type", "application/json"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", f"public, max-age={int(STATS_CACHE_SECONDS)}")])
            return Response(HTTPStatus.OK.value, HTTPStatus.OK.phrase, headers, self.uptime_json().encode())
        if path == "/health-score":
            headers = Headers([("Content-Type", "application/json"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", f"public, max-age={int(STATS_CACHE_SECONDS)}")])
            return Response(HTTPStatus.OK.value, HTTPStatus.OK.phrase, headers, self.health_json().encode())
        if path == "/peers":
            headers = Headers([("Content-Type", "application/json"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", "public, max-age=30")])
            return Response(HTTPStatus.OK.value, HTTPStatus.OK.phrase, headers, self.peers_json().encode())
        lease = self.lease.route(path, query, ip) if path.startswith("/lease") else None
        if lease is not None:
            headers = Headers([("Content-Type", "application/json"), ("Access-Control-Allow-Origin", "*"), ("Cache-Control", "no-store")])
            body = dict(lease[1], enabled=SLOTLEASE_ENABLED)
            code = HTTPStatus(lease[0])
            return Response(code.value, code.phrase, headers, json.dumps(body, separators=(",", ":")).encode())
        if path == "/rulewall":
            headers = Headers([("Content-Type", "application/json"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", "public, max-age=60")])
            return Response(HTTPStatus.OK.value, HTTPStatus.OK.phrase, headers, self.rulewall_json().encode())
        if path == "/rules":
            ready = self.rules_text is not None
            headers = Headers([("Content-Type", "application/json"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", "public, max-age=60")])
            code = HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE
            body = (self.rules_text or '{"error":"relay is still reading the rule places"}').encode()
            return Response(code.value, code.phrase, headers, body)
        if path == "/community":
            headers = Headers([("Content-Type", "application/json"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", "no-store")])
            return Response(HTTPStatus.OK.value, HTTPStatus.OK.phrase, headers, self.community_json().encode())
        if path in ("/api", "/api/", "/api/v1", "/api/v1/", "/api/v1/summary"):
            if path != "/api/v1/summary":
                return Response(HTTPStatus.FOUND.value, HTTPStatus.FOUND.phrase,
                                Headers([("Location", "https://tauhud.com/developers/")]), b"")
            headers = Headers([("Content-Type", "application/json"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", f"public, max-age={int(API_CACHE_SECONDS)}")])
            return Response(HTTPStatus.OK.value, HTTPStatus.OK.phrase, headers,
                            json.dumps(self.summary(), separators=(",", ":")).encode())
        if path == "/api/v1/sources":
            if self.sources_text is None or time.monotonic() - self.sources_at >= 60:
                self.sources_text = json.dumps(self.sources.by_day(self.ordered_blocks()), separators=(",", ":"))
                self.sources_at = time.monotonic()
            headers = Headers([("Content-Type", "application/json"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", f"public, max-age={int(API_CACHE_SECONDS)}")])
            return Response(HTTPStatus.OK.value, HTTPStatus.OK.phrase, headers, self.sources_text.encode())
        api_badge = API_BADGE_PATH.match(path)
        if api_badge:
            headers = Headers([("Content-Type", "image/svg+xml; charset=utf-8"),
                               ("Access-Control-Allow-Origin", "*"),
                               ("Cache-Control", "public, max-age=60")])
            return Response(HTTPStatus.OK.value, HTTPStatus.OK.phrase, headers, self.api_badge(api_badge.group(1), zh).encode())
        if request.headers.get("Upgrade", "").lower() != "websocket":
            return connection.respond(HTTPStatus.OK, "Tau HUD relay (reads, plus transactions signed in your browser). Connect with WebSocket; GET /status for health.\n")
        if not self.origin_ok(request.headers.get("Origin")):
            return connection.respond(HTTPStatus.FORBIDDEN, "origin not allowed\n")
        if len(self.clients) >= MAX_CLIENTS:
            return connection.respond(HTTPStatus.SERVICE_UNAVAILABLE, "relay at capacity\n")
        if self.per_ip.get(self.client_ip(connection, request), 0) >= MAX_PER_IP:
            log.info("refused a socket: one address already holds %s (MAX_PER_IP)", MAX_PER_IP)
            return connection.respond(HTTPStatus.TOO_MANY_REQUESTS, "too many connections from your address\n")
        return None

    async def handler(self, ws: ServerConnection):
        ip = self.client_ip(ws, ws.request)
        self.per_ip[ip] = self.per_ip.get(ip, 0) + 1
        self.clients.add(ws)
        headers = ws.request.headers if ws.request else {}
        self.viewers[ws] = (ip, headers.get("User-Agent", ""), site_of_origin(headers.get("Origin", "")))
        self.push_presence()
        bucket = TokenBucket(CLIENT_BURST, CLIENT_REFILL)
        chain_bucket = TokenBucket(CHAIN_BURST, CHAIN_REFILL)
        try:
            async for message in ws:
                if not isinstance(message, str):
                    message = message.decode("utf-8", errors="replace")
                line = message.strip()
                cmd = line.split(None, 1)[0].lower() if line else ""
                if cmd in FROM_MEMORY:
                    await chain_bucket.wait()   # slow down, never drop: the page is waiting for exactly this answer
                    reply = await self.answer(line, ip, ws)
                elif not bucket.take():
                    reply = json.dumps({"status": "error", "command": cmd or "rate_limit",
                                        "error": {"code": "RATE_LIMITED", "request": line[:120],
                                                  "message": f"Rate limit exceeded: {CLIENT_BURST:g} messages, then {CLIENT_REFILL:g}/s per connection."}},
                                       separators=(",", ":"))
                else:
                    reply = await self.answer(line, ip, ws)
                await ws.send(reply)
        except ConnectionClosed:
            pass
        finally:
            self.clients.discard(ws)
            self.chat_subs.discard(ws)
            self.road_subs.discard(ws)
            self.viewers.pop(ws, None)
            self.via.pop(ws, None)
            self.per_ip[ip] -= 1
            if self.per_ip[ip] <= 0:
                del self.per_ip[ip]
            self.push_presence()

    async def run(self):
        tasks = [
            asyncio.create_task(self.upstream.run()),
            asyncio.create_task(self.island.run(self.upstream.request, self.governance)),
            asyncio.create_task(self.poll_loop(BLOCK_POLL, self.poll_blocks)),
            asyncio.create_task(self.poll_loop(MEMPOOL_POLL, lambda: self.poll_cached("getmempool", True))),
            asyncio.create_task(self.poll_loop(GOV_POLL, lambda: self.poll_cached("getgovernance", True))),
            asyncio.create_task(self.poll_loop(STATE_POLL, lambda: self.poll_cached("gettaustate", False))),
            asyncio.create_task(self.presence_loop()),
            asyncio.create_task(self.uptime_loop()),
            asyncio.create_task(self.poll_loop(RULES_POLL, self.poll_rules)),
        ]
        async with serve(self.handler, LISTEN_HOST, LISTEN_PORT, process_request=self.process_request,
                         max_size=TX_MAX_BYTES + 64, max_queue=8, ping_interval=15, ping_timeout=15,
                         server_header="tau-hud-relay") as server:
            log.info("relay listening on %s:%s, upstream %s", LISTEN_HOST, LISTEN_PORT, self.upstream.url)
            loop = asyncio.get_running_loop()
            stop = loop.create_future()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, stop.set_result, None)
            await stop
            server.close()
        self.visits.save(force=True)
        for t in tasks:
            t.cancel()


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(Relay().run())

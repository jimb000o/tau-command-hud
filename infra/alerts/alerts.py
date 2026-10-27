"""Proposal tracker and alerts for the Tau testnet.

Reads the chain from the relay (the same read-only WebSocket protocol the
pages use), replays governance block by block exactly like history/ does
(consensus/governance.py at the pinned tau-testnet commit), and turns what
happened into news:

  proposed   a rule change was proposed
  agreed     it reached the quorum
  active     it took effect at its activation block
  dropped    its deadline passed with too few votes
  restart    the testnet started a new chain

Every event goes into /public/proposals.json (the tracker page at
tauhud.com/proposals/) and /public/feed.xml (Atom), which Caddy serves at
https://node.tauhud.com/. New events are also posted to Telegram and X when
their credentials are set in .env; without them that channel is simply off.

Nothing is posted for what the watcher finds on its very first run, and
nothing whose block is older than POST_MAX_AGE_SECONDS, so a fresh volume or
a long outage never floods the channel with old news.

  python alerts.py            run the watcher
  python alerts.py --test     send one test post to each configured channel
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import html
import json
import logging
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape

from websockets.asyncio.client import connect

try:
    from blake3 import blake3
except ImportError:  # tests on a machine without the wheel: ids then come from the node's own list
    blake3 = None

log = logging.getLogger("tau-alerts")

RELAY_URL = os.environ.get("RELAY_URL", "ws://relay:8080")
POLL_SECONDS = float(os.environ.get("POLL_SECONDS", 15))
STATE_PATH = os.environ.get("STATE_PATH", "/state/alerts.json")
PUBLIC_DIR = os.environ.get("PUBLIC_DIR", "/public")
SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
FEED_URL = os.environ.get("FEED_URL", "https://node.tauhud.com/feed.xml")
POST_MAX_AGE = float(os.environ.get("POST_MAX_AGE_SECONDS", 3 * 3600))
OPEN_ADMISSION = os.environ.get("TAU_GOVERNANCE_OPEN_ADMISSION", "true").lower() in ("1", "true", "yes")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "@tauHUDcom").strip()
X_KEYS = {k: os.environ.get(k, "").strip() for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")}
FEED_ITEMS = 100
RANGE = 100           # relay's getblockrange maximum
REFETCH_TAIL = 6      # blocks re-read every poll so a replaced tip block (reorg) is noticed
MAX_TRIES = 8

# genesis of tau-testnet-v2 (networks/tau-testnet-v2/genesis.json @ 539d1e2), as in history/
GENESIS_VALIDATORS = ["a1fe40d5e4f155a1af7cb5804ec1ecba9ee3fb1f594e8a7b398b7ed69a6b0ccfd5bb6fd6d8ff965f8e1eb98d5abe7d2b"]
GENESIS_QUORUM = "supermajority"


# ---------------- update ids: BLAKE3 over the node's canonical serialization (consensus/serialization.py) ----------------
def _u32(n: int) -> bytes:
    return int(n).to_bytes(4, "big")


def _str(s: str) -> bytes:
    b = s.encode()
    return _u32(len(b)) + b


def _patch_bytes(p: dict) -> bytes:
    pairs = []
    for k, v in p.items():
        if isinstance(v, bool):
            vb = bytes([1, 1 if v else 0])
        elif isinstance(v, int):
            vb = bytes([2]) + _u32(v)
        elif isinstance(v, str):
            vb = bytes([3]) + _str(v)
        elif isinstance(v, list):
            items = sorted(set(v)) if k in ("validator_additions", "validator_removals") else v
            vb = bytes([4]) + _u32(len(items)) + b"".join(_str(x) for x in items)
        else:
            raise ValueError(f"patch value {k}")
        pairs.append((k, _str(k) + vb))
    pairs.sort(key=lambda x: x[0])
    return _u32(len(pairs)) + b"".join(x[1] for x in pairs)


def update_id(tx: dict, gov: dict | None = None) -> str | None:
    revs, act, patch = tx.get("rule_revisions"), tx.get("activate_at_height"), tx.get("host_contract_patch")
    if blake3 is not None:
        try:
            data = (_u32(len(revs)) + b"".join(_str(r) for r in revs) + int(act).to_bytes(8, "big")
                    + (bytes([1]) + _patch_bytes(patch) if patch is not None else bytes([0])))
            return blake3(data).hexdigest()
        except (TypeError, ValueError):
            pass
    g = gov or {}
    for u in (g.get("pending_updates") or []) + (g.get("scheduled_updates") or []) + (g.get("archival_update_details") or []):
        if u.get("rule_revisions") == revs and u.get("activate_at_height") == act and u.get("host_contract_patch") == patch:
            return u.get("update_id")
    return None


# ---------------- describe things in words (same wording as history/) ----------------
def fee_of(text: str) -> int | None:
    import re
    m = re.search(r"o9\[t\][^=]*=\s*\{\s*#x([0-9a-fA-F]+)\s*\}", text or "")
    return int(m.group(1), 16) if m else None


def threshold(policy: str, n: int) -> int:
    if not n:
        return 1
    if policy == "majority":
        return n // 2 + 1
    if isinstance(policy, str) and policy.startswith("count:") and policy[6:].isdigit():
        return max(1, min(int(policy[6:]), n))
    return max(1, (2 * n + 2) // 3)


QUORUM_TXT = {"supermajority": "two thirds", "majority": "more than half"}


def quorum_txt(q: str) -> str:
    return QUORUM_TXT.get(q) or (f"a fixed {q[6:]}" if str(q).startswith("count:") else str(q))


def fmt_n(n) -> str:
    return f"{int(n):,}"


def plural(n: int, w: str, ws: str | None = None) -> str:
    return f"{fmt_n(n)} {w if n == 1 else (ws or w + 's')}"


def short(h: str) -> str:
    h = str(h or "")
    return h[:6] + "…" + h[-4:] if len(h) > 14 else (h or "—")


def title_parts(revisions: list[str], patch: dict | None) -> list[str]:
    parts, patch = [], patch or {}
    for r in revisions:
        f = fee_of(r)
        if f is not None:
            parts.append(f"Base fee → {fmt_n(f)} AGRS")
    other = sum(1 for r in revisions if fee_of(r) is None)
    if other:
        parts.append("New consensus rule text" if other == 1 else f"{other} consensus rule revisions")
    add, rem = len(patch.get("validator_additions") or []), len(patch.get("validator_removals") or [])
    if add:
        parts.append("Admit a validator" if add == 1 else f"Admit {add} validators")
    if rem:
        parts.append("Remove a validator" if rem == 1 else f"Remove {rem} validators")
    if "vote_quorum" in patch:
        parts.append(f"Quorum → {quorum_txt(patch['vote_quorum'])}")
    if "max_rule_txs_per_block" in patch:
        parts.append(f"{patch['max_rule_txs_per_block']} rule txs per block")
    if "fee_beneficiary" in patch:
        parts.append("Fees to one account" if patch["fee_beneficiary"] else "Fees to the proposer")
    if "eligibility_mode" in patch:
        parts.append(f"Proposers: {patch['eligibility_mode'] or 'default'}")
    if "approval_slots_active" in patch:
        parts.append("Turn on approval slots")
    return parts or ["Empty rule change"]


def height_of(b: dict) -> int:
    try:
        return int((b.get("header") or {}).get("block_number"))
    except (TypeError, ValueError):
        return -1


def ts_of(b: dict | None) -> int | None:
    try:
        return int((b or {}).get("header", {}).get("timestamp")) or None
    except (TypeError, ValueError):
        return None


# ---------------- replay: the node's governance lifecycle, block by block ----------------
def replay(blocks: dict[int, dict], gov: dict | None = None) -> tuple[list[dict], list[dict], dict]:
    """Returns (proposals, events, now) for the blocks held, lowest to highest.

    Mirrors history/index.html replay(): votes count once per voter while the
    change is open (any account under open admission, else validators only),
    it is agreed at the quorum of the validator set in force, and at the end
    of each block expired changes are dropped and agreed ones whose
    activation height arrived take effect, in activation-height order.
    """
    props: dict[str, dict] = {}
    order: list[dict] = []
    events: list[dict] = []
    validators, quorum, fee, rev = list(GENESIS_VALIDATORS), GENESIS_QUORUM, 10, 1
    if not blocks:
        return [], [], {}
    lo, hi = min(blocks), max(blocks)
    thr = threshold(quorum, len(validators))
    for h in range(lo, hi + 1):
        b = blocks.get(h)
        ts = ts_of(b)
        thr = threshold(quorum, len(validators))
        for i, t in enumerate((b or {}).get("transactions") or []):
            kind = t.get("tx_type") or "user_tx"
            sender = str(t.get("sender_pubkey") or "").lower()
            tx_id = ((b.get("tx_ids") or [None] * (i + 1)) + [None])[i]
            if kind == "consensus_rule_update" and isinstance(t.get("rule_revisions"), list):
                uid = update_id(t, gov) or f"unknown-{h}-{i}"
                if uid in props:
                    props[uid]["dups"].append(h)  # the node ignores a second copy
                    continue
                p = {"id": uid, "n": len(order) + 1, "proposed_at": h, "proposed_ts": ts, "proposer": sender,
                     "revisions": t["rule_revisions"], "activate_at": int(t.get("activate_at_height") or 0),
                     "patch": t.get("host_contract_patch"), "votes": [], "approved_at": None, "approved_ts": None,
                     "activated_at": None, "activated_ts": None, "expired_at": None, "expired_ts": None,
                     "thr": thr, "rev": None, "dups": [], "tx_id": tx_id}
                p["parts"] = title_parts(p["revisions"], p["patch"])
                p["title"] = " + ".join(p["parts"])
                props[uid] = p
                order.append(p)
                events.append({"kind": "proposed", "h": h, "ts": ts, "id": uid})
            elif kind == "consensus_rule_vote":
                p = props.get(str(t.get("update_id") or "").lower())
                if not p:
                    continue
                v = {"h": h, "voter": sender, "approve": str(t.get("approve", True)).lower() != "false", "counted": False}
                is_open = p["approved_at"] is None and p["expired_at"] is None and p["activated_at"] is None
                eligible = OPEN_ADMISSION or sender in validators
                if is_open and eligible and not any(x["counted"] and x["voter"] == sender for x in p["votes"]):
                    v["counted"] = True
                p["votes"].append(v)
                if v["counted"]:
                    n = sum(1 for x in p["votes"] if x["counted"])
                    if n >= thr:
                        p["approved_at"], p["approved_ts"], p["thr"] = h, ts, thr
                        events.append({"kind": "agreed", "h": h, "ts": ts, "id": p["id"]})
        # height transitions run after the block's transactions (engine._apply_block)
        for p in order:
            if p["approved_at"] is None and p["expired_at"] is None and p["activate_at"] <= h:
                p["expired_at"], p["expired_ts"], p["thr"] = h, ts, thr
                events.append({"kind": "dropped", "h": h, "ts": ts, "id": p["id"]})
        due = sorted((p for p in order if p["approved_at"] is not None and p["activated_at"] is None and p["activate_at"] <= h),
                     key=lambda p: (p["activate_at"], p["id"]))
        for p in due:
            rev += 1
            p["activated_at"], p["activated_ts"], p["rev"] = h, ts, rev
            for r in p["revisions"]:
                f = fee_of(r)
                if f is not None:
                    fee = f
            patch = p["patch"] or {}
            if patch.get("validator_additions") or patch.get("validator_removals"):
                rem = {str(x).lower() for x in patch.get("validator_removals") or []}
                validators = sorted({*(v for v in validators if v not in rem), *(str(x).lower() for x in patch.get("validator_additions") or [])})
            if "vote_quorum" in patch:
                quorum = patch["vote_quorum"]
            events.append({"kind": "active", "h": h, "ts": ts, "id": p["id"]})
    thr = threshold(quorum, len(validators))
    for p in order:
        p["status"] = ("active" if p["activated_at"] is not None else "dropped" if p["expired_at"] is not None
                       else "agreed" if p["approved_at"] is not None else "voting")
        p["counted_votes"] = sum(1 for v in p["votes"] if v["counted"])
        if p["status"] == "voting":
            p["thr"] = thr  # what it needs now
    now = {"head": hi, "first": lo, "rev": rev, "fee": fee, "validators": len(validators), "quorum": quorum, "thr": thr}
    return order, events, now


# ---------------- words for each event ----------------
def block_pace(blocks: dict[int, dict]) -> float | None:
    hs = sorted(blocks)[-11:]
    tss = [ts_of(blocks[h]) for h in hs]
    pts = [(h, t) for h, t in zip(hs, tss) if t]
    if len(pts) < 2 or pts[-1][0] == pts[0][0]:
        return None
    return max(1.0, (pts[-1][1] - pts[0][1]) / (pts[-1][0] - pts[0][0]))


def eta_txt(blocks_left: int, pace: float | None) -> str:
    if blocks_left <= 0 or not pace:
        return ""
    s = blocks_left * pace
    if s < 90:
        return " (under 2 min)"
    if s < 5400:
        return f" (~{round(s / 60)} min)"
    if s < 172800:
        return f" (~{round(s / 3600)} h)"
    return f" (~{round(s / 86400)} days)"


def describe(ev: dict, p: dict | None, head: int, pace: float | None) -> dict:
    """Headline, one-line body and link for an event."""
    k = ev["kind"]
    if k == "restart":
        old = ev.get("old_tip")
        return {"headline": "The Tau testnet restarted",
                "body": (f"The old chain ended at block #{fmt_n(old)}. " if old else "") +
                        "A new chain started; our node follows it from its first block.",
                "link": f"{SITE}/stats/"}
    title = p["title"] if p else "a rule change"
    link = f"{SITE}/proposals/#{(p or {}).get('id', '')[:16]}"
    if k == "proposed":
        left = p["activate_at"] - head
        return {"headline": f"New rule proposal: {title}",
                "body": f"Proposed at block #{fmt_n(ev['h'])} by {short(p['proposer'])}. "
                        f"Needs {plural(p['thr'], 'vote')} by block #{fmt_n(p['activate_at'])}"
                        f"{eta_txt(left, pace)}, or it is dropped.",
                "link": link}
    if k == "agreed":
        left = p["activate_at"] - head
        return {"headline": f"Agreed: {title}",
                "body": f"Reached the quorum at block #{fmt_n(ev['h'])} ({p['counted_votes']} of {p['thr']} votes). "
                        f"Takes effect at block #{fmt_n(p['activate_at'])}{eta_txt(left, pace)}.",
                "link": link}
    if k == "active":
        return {"headline": f"Now in force: {title}",
                "body": f"Took effect at block #{fmt_n(ev['h'])}. Consensus rules are at revision {p['rev']} now.",
                "link": link}
    if k == "dropped":
        return {"headline": f"Dropped: {title}",
                "body": f"Only {p['counted_votes']} of {p['thr']} votes by block #{fmt_n(ev['h'])}. The old rules stay.",
                "link": link}
    return {"headline": k, "body": "", "link": SITE}


ICONS = {"proposed": "🆕", "agreed": "✅", "active": "⚡", "dropped": "✖️", "restart": "🔄"}


def telegram_text(item: dict) -> str:
    return (f"{ICONS.get(item['kind'], '•')} <b>{html.escape(item['headline'])}</b>\n"
            f"{html.escape(item['body'])}\n\n"
            f"<a href=\"{html.escape(item['link'])}\">Open in Tau HUD</a>")


def x_text(item: dict) -> str:
    # X counts every link as 23 characters
    tail = f"\n\n{item['link']} #Tau"
    room = 280 - 23 - len(" #Tau") - 2
    text = f"{ICONS.get(item['kind'], '')} {item['headline']}\n{item['body']}".strip()
    if len(text) > room:
        text = f"{ICONS.get(item['kind'], '')} {item['headline']}".strip()
        if len(text) > room:
            text = text[: room - 1] + "…"
    return text + tail


# ---------------- outlets ----------------
class Outlet:
    name = ""

    def enabled(self) -> bool:
        raise NotImplementedError

    def send(self, item: dict) -> tuple[bool, float | None, str]:
        """(sent, retry_after_seconds or None, error text)."""
        raise NotImplementedError


class Telegram(Outlet):
    name = "telegram"

    def enabled(self) -> bool:
        return bool(TELEGRAM_TOKEN and TELEGRAM_CHAT)

    def send_text(self, text: str) -> tuple[bool, float | None, str]:
        body = json.dumps({"chat_id": TELEGRAM_CHAT, "text": text, "parse_mode": "HTML",
                           "link_preview_options": {"is_disabled": True}}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                ok = json.load(r).get("ok", False)
                return ok, None, "" if ok else "not ok"
        except urllib.error.HTTPError as e:  # never log the URL: it holds the token
            try:
                info = json.load(e)
            except ValueError:
                info = {}
            retry = (info.get("parameters") or {}).get("retry_after")
            return False, float(retry) if retry else None, f"HTTP {e.code}: {info.get('description', '')}"
        except (urllib.error.URLError, OSError) as e:
            return False, None, type(e).__name__

    def send(self, item):
        return self.send_text(telegram_text(item))


def _pct(s: str) -> str:
    return urllib.parse.quote(s, safe="-._~")


class X(Outlet):
    """POST /2/tweets with OAuth 1.0a user context (the four keys of the app's
    user, made with Read and Write permission)."""
    name = "x"
    URL = "https://api.x.com/2/tweets"

    def enabled(self) -> bool:
        return all(X_KEYS.values())

    def auth_header(self) -> str:
        oauth = {"oauth_consumer_key": X_KEYS["X_API_KEY"], "oauth_nonce": secrets.token_hex(16),
                 "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": str(int(time.time())),
                 "oauth_token": X_KEYS["X_ACCESS_TOKEN"], "oauth_version": "1.0"}
        # a JSON body is not part of the signature base
        params = "&".join(f"{_pct(k)}={_pct(v)}" for k, v in sorted(oauth.items()))
        base = "&".join(["POST", _pct(self.URL), _pct(params)])
        key = f"{_pct(X_KEYS['X_API_SECRET'])}&{_pct(X_KEYS['X_ACCESS_SECRET'])}"
        oauth["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
        return "OAuth " + ", ".join(f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(oauth.items()))

    def send_text(self, text: str) -> tuple[bool, float | None, str]:
        req = urllib.request.Request(self.URL, data=json.dumps({"text": text}).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": self.auth_header()})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return 200 <= r.status < 300, None, ""
        except urllib.error.HTTPError as e:
            retry = None
            if e.code == 429:
                reset = e.headers.get("x-rate-limit-reset")
                retry = max(60.0, float(reset) - time.time()) if reset and reset.isdigit() else 900.0
            try:
                detail = json.load(e).get("detail", "")
            except ValueError:
                detail = ""
            return False, retry, f"HTTP {e.code}: {detail}"
        except (urllib.error.URLError, OSError) as e:
            return False, None, type(e).__name__

    def send(self, item):
        return self.send_text(x_text(item))


# ---------------- feed and tracker data ----------------
def iso(ts: float | None) -> str:
    return datetime.fromtimestamp(ts or time.time(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atom(items: list[dict], updated: float) -> str:
    entries = []
    for it in items[:FEED_ITEMS]:
        entries.append(f"""  <entry>
    <id>tag:tauhud.com,2026:{xml_escape(it['key'])}</id>
    <title>{xml_escape(it['headline'])}</title>
    <link href="{xml_escape(it['link'])}"/>
    <updated>{iso(it.get('ts') or it['seen'])}</updated>
    <category term="{it['kind']}"/>
    <summary>{xml_escape(it['body'])}</summary>
  </entry>""")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>{xml_escape(FEED_URL)}</id>
  <title>Tau HUD · Tau testnet rule changes</title>
  <subtitle>Every rule proposal, agreement, activation and chain restart on the Tau Testnet Alpha, read from our own node.</subtitle>
  <link rel="self" href="{xml_escape(FEED_URL)}"/>
  <link href="{SITE}/proposals/"/>
  <icon>{SITE}/favicon-32.png</icon>
  <updated>{iso(updated)}</updated>
  <author><name>Tau HUD</name><uri>{SITE}</uri></author>
{chr(10).join(entries)}
</feed>
"""


def write_atomic(path: str, text: str):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


# ---------------- the watcher ----------------
class Watcher:
    def __init__(self, outlets: list[Outlet] | None = None):
        self.blocks: dict[int, dict] = {}
        self.gov: dict | None = None
        self.ws = None
        self.outlets = outlets if outlets is not None else [Telegram(), X()]
        self.state = self.load_state()
        self.dirty_public = True

    # state: what was seen, what was posted where; survives restarts
    def load_state(self) -> dict:
        try:
            with open(STATE_PATH) as f:
                s = json.load(f)
        except FileNotFoundError:
            s = {}
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s: %r; starting fresh", STATE_PATH, exc)
            s = {}
        s.setdefault("chain", None)     # {block1_hash, head, head_hash}
        s.setdefault("items", [])       # feed items, newest first
        s.setdefault("primed", False)   # first replay done: everything found then is history, not news
        s.setdefault("outlets", {})     # name -> {"since": ts}
        return s

    def save_state(self):
        try:
            os.makedirs(os.path.dirname(STATE_PATH) or ".", exist_ok=True)
            write_atomic(STATE_PATH, json.dumps(self.state, separators=(",", ":")))
        except OSError as exc:
            log.warning("cannot write %s: %r", STATE_PATH, exc)

    async def request(self, command: str) -> dict | None:
        await self.ws.send(command)
        while True:
            msg = json.loads(await asyncio.wait_for(self.ws.recv(), 30))
            if msg.get("data", {}).get("pushed") and msg.get("command") in ("getblocks", "getmempool", "getgovernance", "presence"):
                continue  # the relay pushes news to every client; we poll instead
            if msg.get("command") == "rate_limit":  # over the relay's per-client budget: wait and ask again
                await asyncio.sleep(2)
                await self.ws.send(command)
                continue
            if msg.get("command") == command.split()[0]:
                return msg

    async def blockrange(self, start: int, count: int) -> tuple[list[dict], int | None]:
        msg = await self.request(f"getblockrange {start} {count}")
        if not msg or msg.get("status") != "ok":
            return [], None
        d = msg.get("data") or {}
        return [b for b in d.get("blocks") or [] if isinstance(b, dict) and b.get("block_hash")], d.get("head")

    async def sync(self) -> bool:
        """Bring self.blocks up to the relay's head. True when anything changed."""
        first, head = await self.blockrange(1, 1)
        if not first or head is None:
            return False  # relay still syncing, or the chain has no block 1 yet
        b1 = first[0]["block_hash"]
        known = self.state["chain"]
        if known and known.get("block1_hash") != b1:
            self.chain_restart(known, b1)
        changed = not self.blocks
        start = max(1, (max(self.blocks) - REFETCH_TAIL) if self.blocks else 1)
        while start <= head:
            got, head2 = await self.blockrange(start, RANGE)
            for b in got:
                h = height_of(b)
                if h < 0:
                    continue
                old = self.blocks.get(h)
                if not old or old["block_hash"] != b["block_hash"]:
                    self.blocks[h] = b
                    changed = True
            if head2 is not None:
                head = head2
            start += RANGE
            await asyncio.sleep(0.6)  # stay under the relay's 2 requests/s per client
        for h in [h for h in self.blocks if h > head]:  # the relay dropped a tip block (reorg)
            del self.blocks[h]
            changed = True
        if self.blocks:
            top = max(self.blocks)
            self.state["chain"] = {"block1_hash": b1, "head": top, "head_hash": self.blocks[top]["block_hash"]}
        if changed:
            msg = await self.request("getgovernance")
            if msg and msg.get("status") == "ok":
                self.gov = msg.get("data")
        return changed

    def chain_restart(self, known: dict, new_b1: str):
        log.warning("chain restart: old chain ended at #%s", known.get("head"))
        self.blocks.clear()
        ev = {"kind": "restart", "h": 0, "ts": time.time(), "old_tip": known.get("head"),
              "key": f"restart:{known.get('block1_hash', '')[:16]}:{new_b1[:16]}"}
        self.add_item(ev, None, 0, None, chain=new_b1)

    def add_item(self, ev: dict, p: dict | None, head: int, pace: float | None, chain: str) -> bool:
        key = ev.get("key") or f"{chain[:16]}:{ev['kind']}:{ev['id']}"
        if any(it["key"] == key for it in self.state["items"]):
            return False
        d = describe(ev, p, head, pace)
        item = {"key": key, "kind": ev["kind"], "h": ev["h"], "ts": ev.get("ts"), "seen": time.time(), "chain": chain[:16],
                "id": ev.get("id"), **d,
                # the very first replay is history; later events are news unless their block is old
                "news": self.state["primed"] and (time.time() - (ev.get("ts") or time.time())) <= POST_MAX_AGE,
                "posted": {}}
        self.state["items"].insert(0, item)
        del self.state["items"][FEED_ITEMS * 3:]
        self.dirty_public = True
        log.info("event %s: %s%s", ev["kind"], d["headline"], "" if item["news"] else " (history, not posted)")
        return True

    def process(self):
        props, events, now = replay(self.blocks, self.gov)
        chain = self.state["chain"]["block1_hash"] if self.state["chain"] else ""
        by_id = {p["id"]: p for p in props}
        pace = block_pace(self.blocks)
        for ev in events:
            self.add_item(ev, by_id.get(ev["id"]), now.get("head", 0), pace, chain)
        if not self.state["primed"] and self.blocks:
            self.state["primed"] = True
        self.write_public(props, now, pace, chain)
        self.save_state()

    def write_public(self, props: list[dict], now: dict, pace: float | None, chain: str):
        os.makedirs(PUBLIC_DIR, exist_ok=True)
        head_b = self.blocks.get(now.get("head")) if now else None
        g = self.gov or {}
        data = {
            "generated_at": round(time.time()),
            "chain": {"block1_hash": chain, "head": now.get("head"), "head_ts": ts_of(head_b), "first": now.get("first"),
                      "seconds_per_block": round(pace, 1) if pace else None,
                      "node_head": g.get("head_number")},
            "rules": {"revision": now.get("rev"), "base_fee": now.get("fee"), "validators": now.get("validators"),
                      "quorum": now.get("quorum"), "votes_needed": now.get("thr"), "open_admission": OPEN_ADMISSION},
            "proposals": [{k: p[k] for k in ("id", "n", "title", "parts", "status", "proposer", "proposed_at", "proposed_ts",
                                              "activate_at", "approved_at", "approved_ts", "activated_at", "activated_ts",
                                              "expired_at", "expired_ts", "thr", "counted_votes", "rev", "revisions",
                                              "patch", "dups", "tx_id")}
                          | {"votes": [{"h": v["h"], "voter": v["voter"], "counted": v["counted"], "approve": v["approve"]} for v in p["votes"]]}
                          for p in reversed(props)],
            "events": [{k: it.get(k) for k in ("key", "kind", "h", "ts", "seen", "id", "headline", "body", "link", "chain")}
                       for it in self.state["items"][:FEED_ITEMS]],
            "channels": {"telegram": "https://t.me/" + TELEGRAM_CHAT.lstrip("@") if TELEGRAM_CHAT.startswith("@") else None,
                         "x": os.environ.get("X_PROFILE_URL") or None, "feed": FEED_URL},
        }
        try:
            write_atomic(os.path.join(PUBLIC_DIR, "proposals.json"), json.dumps(data, separators=(",", ":")))
            if self.dirty_public:
                write_atomic(os.path.join(PUBLIC_DIR, "feed.xml"), atom(self.state["items"], time.time()))
                self.dirty_public = False
        except OSError as exc:
            log.warning("cannot write public files: %r", exc)

    async def deliver(self):
        """Post news items each enabled outlet has not posted yet, oldest first."""
        for o in self.outlets:
            if not o.enabled():
                continue
            meta = self.state["outlets"].setdefault(o.name, {})
            if "since" not in meta:  # turned on just now: start from here, do not post the backlog
                meta["since"] = time.time()
                log.info("%s is on; posting news from now on", o.name)
                self.save_state()
            if meta.get("pause_until", 0) > time.time():
                continue
            for it in reversed(self.state["items"]):
                st = it["posted"].get(o.name)
                if not it["news"] or it["seen"] < meta["since"] or st == "ok" or (isinstance(st, int) and st >= MAX_TRIES):
                    continue
                ok, retry, err = await asyncio.to_thread(o.send, it)
                if ok:
                    it["posted"][o.name] = "ok"
                    log.info("posted to %s: %s", o.name, it["headline"])
                else:
                    it["posted"][o.name] = (st if isinstance(st, int) else 0) + 1
                    log.warning("%s post failed (%s), try %s of %s", o.name, err, it["posted"][o.name], MAX_TRIES)
                    meta["pause_until"] = time.time() + (retry or 60 * it["posted"][o.name])
                    self.save_state()
                    break
                self.save_state()
                await asyncio.sleep(3)  # Telegram allows ~20 posts a minute per channel

    async def run(self):
        while True:
            try:
                async with connect(RELAY_URL, max_size=64 * 2**20, open_timeout=20) as ws:
                    self.ws = ws
                    log.info("connected to %s; telegram %s, x %s", RELAY_URL,
                             "on" if Telegram().enabled() else "off", "on" if X().enabled() else "off")
                    while True:
                        if await self.sync() or self.dirty_public or not self.state["primed"]:
                            self.process()
                        await self.deliver()
                        await asyncio.sleep(POLL_SECONDS)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # relay restarting, network blip: try again shortly
                log.warning("relay connection lost (%r); retrying in 10 s", exc)
                await asyncio.sleep(10)


def send_test() -> int:
    item = {"kind": "proposed", "headline": "Tau HUD alerts are connected",
            "body": "This channel will get a post whenever a rule change is proposed, agreed or takes effect on the Tau testnet.",
            "link": f"{SITE}/proposals/"}
    code = 0
    for o in (Telegram(), X()):
        if not o.enabled():
            print(f"{o.name}: off (credentials not set in .env)")
            continue
        ok, _, err = o.send(item)
        print(f"{o.name}: {'sent' if ok else 'FAILED ' + err}")
        code |= 0 if ok else 1
    return code


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if "--test" in sys.argv:
        sys.exit(send_test())
    asyncio.run(Watcher().run())

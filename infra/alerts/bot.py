"""Ask the bot: the Tau HUD Telegram bot answers questions about the testnet.

The bot that posts alerts to @tauHUDcom (alerts.py) also answers people who
write to it. It long-polls Telegram (getUpdates, no webhook, no open port) and
answers from the same sources the pages use:

  /height              block height, block pace, age of the last block   relay /uptime + proposals.json
  /proposals           rule changes coming up, agreed, in force          proposals.json (alerts.py)
  /tx <hash>           is a transaction in a block?                       relay gettxstatus
  /address <address>   balance and pending amounts                        relay getaccountstate / getbalance
  /block <n>           when a block was made and what it holds            relay getblockrange
  /status              node online, in sync, availability, restarts       relay /uptime
  /help

Plain questions work too in a private chat: "height?", "last proposal?",
"is my tx in? <hash>", or just a hash or an address. In groups it only
answers commands (Telegram's privacy mode hides everything else anyway).

It never writes to the alerts channel: answers go only to the private chat or
group the question came from. Each person gets a few questions a minute;
past that the bot says so once and then stays quiet until the budget refills.

  python bot.py          run the bot (needs TELEGRAM_BOT_TOKEN)
  python bot.py --ask "/height"   print the answer to one question, send nothing
"""
from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request

from websockets.asyncio.client import connect

log = logging.getLogger("tau-bot")

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHANNEL = os.environ.get("TELEGRAM_CHAT_ID", "@tauHUDcom").strip()  # the alerts channel: never answered into
API = os.environ.get("TELEGRAM_API", "https://api.telegram.org").rstrip("/")
RELAY_URL = os.environ.get("RELAY_URL", "ws://relay:8080")
RELAY_HTTP = os.environ.get("RELAY_HTTP", "http://relay:8080").rstrip("/")
PUBLIC_DIR = os.environ.get("PUBLIC_DIR", "/public")
SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
POLL_TIMEOUT = int(os.environ.get("BOT_POLL_TIMEOUT", 50))      # seconds Telegram holds a getUpdates open
USER_BURST = float(os.environ.get("BOT_USER_BURST", 5))          # questions in a row per person
USER_REFILL = float(os.environ.get("BOT_USER_REFILL_SECONDS", 8))  # one more every this many seconds
MAX_AGE = float(os.environ.get("BOT_MAX_AGE_SECONDS", 120))      # older questions (bot was down) are skipped
CACHE_SECONDS = 5
LIST_MAX = 5
SYNC_LAG = 2  # as relay.py: in sync while at most this many blocks behind the network tip

ADDR = re.compile(r"\b(?:0x)?([0-9a-fA-F]{96})\b")
HASH = re.compile(r"\b(?:0x)?([0-9a-fA-F]{64})\b")

# what gettxstatus answers, in words (same as explorer/)
TX_STATUS = {
    "confirmed": ("✅", "In a block", "Sealed in a block on the chain our node follows."),
    "queued": ("⏳", "Waiting", "In our node's queue, waiting for the next block."),
    "expired": ("❌", "Expired", "It waited too long and the network let it go. It never reached a block."),
    "evicted": ("❌", "Pushed out", "The queue was full or a newer transaction from the same sender replaced it. It never reached a block."),
    "rejected": ("❌", "Refused", "The network refused it on a second check, for example because a rule said no or the balance did not cover it."),
    "unknown": ("❔", "Not known", "Our node has not seen a transaction with this hash. It may be on another chain, or not sent yet."),
}
COMMANDS = [  # command, menu text in Telegram, line in /help
    ("height", "Block height and pace", "/height  block height and pace"),
    ("proposals", "Rule changes: coming up, agreed, in force", "/proposals  rule changes coming up, agreed and in force"),
    ("tx", "Is my transaction in a block? /tx <hash>", "/tx &lt;hash&gt;  is my transaction in a block?"),
    ("address", "Balance of an address: /address <address>", "/address &lt;address&gt;  balance of an address"),
    ("block", "One block: /block <number>", "/block &lt;number&gt;  what one block holds"),
    ("status", "Is the testnet running?", "/status  is the testnet running and in sync?"),
    ("help", "What I can answer", ""),
]
e = html.escape


# ---------------- formatting (same words as the pages) ----------------
def fmt_n(n) -> str:
    return f"{int(n):,}"


def fmt_a(n) -> str:
    try:
        f = float(n)
    except (TypeError, ValueError):
        return "—"
    return f"{f:,.0f}" if f == int(f) else f"{f:,.4f}".rstrip("0").rstrip(".")


def plural(n: int, w: str) -> str:
    return f"{fmt_n(n)} {w}{'' if n == 1 else 's'}"


def short(h: str) -> str:
    h = str(h or "")
    return h[:6] + "…" + h[-4:] if len(h) > 14 else (h or "—")


def ago(ts, now: float | None = None) -> str:
    if not ts:
        return "—"
    s = max(0.0, (now or time.time()) - float(ts))
    if s < 60:
        return f"{round(s)} s ago"
    if s < 5400:
        return f"{round(s / 60)} min ago"
    if s < 172800:
        return f"{round(s / 3600)} h ago"
    return f"{round(s / 86400)} days ago"


def eta(blocks_left: int, pace: float | None) -> str:
    if blocks_left <= 0 or not pace:
        return ""
    s = blocks_left * pace
    if s < 90:
        return "under 2 min"
    if s < 5400:
        return f"~{round(s / 60)} min"
    if s < 172800:
        return f"~{round(s / 3600)} h"
    return f"~{round(s / 86400)} days"


def link(path: str, label: str) -> str:
    return f'<a href="{e(SITE + path)}">{e(label)}</a>'


# ---------------- data sources ----------------
class Sources:
    """The relay (HTTP for status, WebSocket for lookups) and alerts' proposals.json, briefly cached."""

    def __init__(self):
        self.cache: dict[str, tuple[float, object]] = {}

    def _cached(self, key: str, load):
        hit = self.cache.get(key)
        if hit and time.time() - hit[0] < CACHE_SECONDS:
            return hit[1]
        val = load()
        if val is not None:
            self.cache[key] = (time.time(), val)
        return val

    def uptime(self) -> dict | None:
        def load():
            try:
                with urllib.request.urlopen(RELAY_HTTP + "/uptime", timeout=10) as r:
                    return json.load(r)
            except (urllib.error.URLError, OSError, ValueError) as exc:
                log.warning("relay /uptime: %r", exc)
                return None
        return self._cached("uptime", load)

    def proposals(self) -> dict | None:
        def load():
            try:
                with open(os.path.join(PUBLIC_DIR, "proposals.json")) as f:
                    return json.load(f)
            except (OSError, ValueError) as exc:
                log.warning("proposals.json: %r", exc)
                return None
        return self._cached("proposals", load)

    async def lookup(self, command: str) -> dict | None:
        """One read command over the relay's WebSocket; the node's reply envelope, or None."""
        for attempt in range(2):
            try:
                async with connect(RELAY_URL, max_size=8 * 2**20, open_timeout=10) as ws:
                    await ws.send(command)
                    end = time.time() + 15
                    while time.time() < end:
                        raw = await asyncio.wait_for(ws.recv(), max(0.1, end - time.time()))
                        try:
                            msg = json.loads(raw)
                        except ValueError:
                            continue
                        if not isinstance(msg, dict) or msg.get("command") != command.split()[0]:
                            continue  # pushes to every client (blocks, presence) in between
                        if msg.get("status") != "ok" and (msg.get("error") or {}).get("code") == "BUSY" and attempt == 0:
                            break  # the relay's shared lookup budget is spent: ask once more shortly
                        return msg
            except (OSError, asyncio.TimeoutError) as exc:
                log.warning("relay %s: %r", command.split()[0], exc)
                return None
            except Exception as exc:  # websockets' own errors (closed, handshake)
                log.warning("relay %s: %r", command.split()[0], exc)
                return None
            await asyncio.sleep(1.5)
        return None


# ---------------- answers ----------------
OFFLINE = "I cannot reach our node right now. Try again in a minute, or see " + "{status}."


def offline() -> str:
    return OFFLINE.format(status=link("/status/", "the status page"))


def chain_facts(src: Sources) -> dict | None:
    """Height, tip, sync, last block time and pace from /uptime and proposals.json."""
    up = src.uptime()
    if not up:
        return None
    st = up.get("status") or {}
    pj = src.proposals() or {}
    pace = (pj.get("chain") or {}).get("seconds_per_block")
    height = st.get("canonical_height") if st.get("canonical_height") is not None else st.get("height")
    tip = st.get("tip_height")
    return {"height": height, "tip": tip, "connected": bool(st.get("upstream_connected")),
            "synced": height is not None and (tip is None or tip - height <= SYNC_LAG),
            "last_ts": up.get("last_block_ts"), "pace": pace, "status": st, "uptime": up}


def answer_height(src: Sources) -> str:
    f = chain_facts(src)
    if not f or f["height"] is None:
        return offline()
    out = [f"⛓ <b>Block #{fmt_n(f['height'])}</b>"]
    line = f"Last block {ago(f['last_ts'])}"
    if f["pace"]:
        line += f" · about one block every {round(f['pace'])} s"
    out.append(line + ".")
    if f["tip"] is not None and f["tip"] > f["height"] + SYNC_LAG:
        out.append(f"Our node is catching up: the network is at #{fmt_n(f['tip'])}.")
    out += ["", link(f"/explorer/?b={f['height']}", "Open the block in the Explorer")]
    return "\n".join(out)


def _prop_line(p: dict, head: int, pace: float | None) -> str:
    title = link(f"/proposals/#{p['id'][:16]}", p.get("title") or "A rule change")
    left = (p.get("activate_at") or 0) - head
    when = eta(left, pace)
    at = f"#{fmt_n(p['activate_at'])}" + (f" ({when})" if when else "")
    if p["status"] == "voting":
        return f"🗳️ {title}\n    {p.get('counted_votes', 0)} of {plural(int(p.get('thr') or 1), 'vote')}, deadline block {at}"
    if p["status"] == "agreed":
        return f"✅ {title}\n    Agreed. Takes effect at block {at}"
    if p["status"] == "active":
        return f"⚡ {title}\n    In force since block #{fmt_n(p.get('activated_at') or p['activate_at'])}"
    return f"❌ {title}\n    Dropped at block #{fmt_n(p.get('expired_at') or p['activate_at'])}, nothing changed"


def answer_proposals(src: Sources) -> str:
    pj = src.proposals()
    if not pj:
        return "The proposal tracker is not ready yet. Try again in a minute, or see " + link("/proposals/", "the Proposals page") + "."
    props = pj.get("proposals") or []  # newest first
    head = (pj.get("chain") or {}).get("head") or 0
    pace = (pj.get("chain") or {}).get("seconds_per_block")
    rules = pj.get("rules") or {}
    if not props:
        return ("🗳️ <b>No rule change proposed on this chain yet.</b>\n"
                f"The rules are at revision {rules.get('revision', 1)}. I post to the channel when one comes.\n\n"
                + link("/proposals/", "Proposals page"))
    coming = [p for p in props if p.get("status") in ("voting", "agreed")]
    active = [p for p in props if p.get("status") == "active"]
    dropped = [p for p in props if p.get("status") == "dropped"]
    out = []
    if coming:
        out += [f"<b>Coming up ({len(coming)})</b>"] + [_prop_line(p, head, pace) for p in coming[:LIST_MAX]]
    else:
        out += ["<b>Coming up</b>", "Nothing waiting for votes right now."]
    newest = props[0]
    if newest not in coming[:LIST_MAX]:
        out += ["", "<b>Last proposal</b>", _prop_line(newest, head, pace)]
    shown = [p for p in active[:3] if p is not newest]
    if shown:
        out += ["", f"<b>In force ({len(active)})</b>"] + [_prop_line(p, head, pace) for p in shown]
    tail = [f"Rules at revision {rules.get('revision', '—')}, base fee {fmt_a(rules.get('base_fee'))} AGRS."]
    if dropped:
        tail.append(f"{plural(len(dropped), 'proposal')} dropped.")
    out += ["", " ".join(tail), link("/proposals/", "All proposals with votes and rule text")]
    return "\n".join(x for x in out if x is not None)


async def answer_tx(src: Sources, h: str | None) -> str:
    if not h:
        return ("Send me the transaction hash: <code>/tx &lt;hash&gt;</code>\n"
                "It is 64 characters of 0–9 and a–f. Your wallet shows it after sending.")
    msg = await src.lookup(f"gettxstatus {h}")
    if not msg:
        return offline()
    d = msg.get("data") or {}
    if msg.get("status") != "ok":
        return "Our node could not answer for this hash right now. Try again in a minute."
    icon, name, words = TX_STATUS.get(str(d.get("status")), TX_STATUS["unknown"])
    out = [f"{icon} <b>{name}</b>  <code>{e(short(h))}</code>", words]
    if d.get("status") == "confirmed" and d.get("block_number") is not None:
        bn = int(d["block_number"])
        conf = d.get("confirmations")
        out.append(f"Block {link(f'/explorer/?b={bn}', '#' + fmt_n(bn))}"
                   + (f" · {plural(int(conf), 'confirmation')}" if conf is not None else "") + ".")
    out += ["", link(f"/explorer/?tx={h}", "Open in the Explorer")]
    return "\n".join(out)


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


async def answer_address(src: Sources, a: str | None) -> str:
    if not a:
        return ("Send me the address: <code>/address &lt;address&gt;</code>\n"
                "It is 96 characters of 0–9 and a–f (the account's public key).")
    msg = await src.lookup(f"getaccountstate {a}")
    d = (msg or {}).get("data") or {}
    bal = d.get("chain_balance") if msg and msg.get("status") == "ok" else None
    if bal is None:
        gb = await src.lookup(f"getbalance {a}")
        if not gb:
            return offline()
        if gb.get("status") == "ok":
            bal = (gb.get("data") or {}).get("balance")
    if bal is None:
        return "Our node could not answer for this address right now. Try again in a minute."
    out = [f"👛 <b>{fmt_a(bal)} AGRS</b>  <code>{e(short(a))}</code>", "Confirmed balance, as our node reports it."]
    out_q = _num(d.get("pending_outgoing")) + _num(d.get("pending_fees"))
    in_q = _num(d.get("pending_incoming"))
    if out_q:
        out.append(f"−{fmt_a(out_q)} sent, waiting for a block.")
    if in_q:
        out.append(f"+{fmt_a(in_q)} incoming, waiting for a block.")
    if _num(d.get("escrowed_out")):
        out.append(f"{fmt_a(d['escrowed_out'])} held for retractable transfers.")
    out += ["", link(f"/account/?a={a}", "History, rules and transfers on the Account page")]
    return "\n".join(out)


async def answer_block(src: Sources, n: int | None) -> str:
    if n is None:
        return answer_height(src)
    msg = await src.lookup(f"getblockrange {n} 1")
    if not msg or msg.get("status") != "ok":
        return offline()
    blocks = (msg.get("data") or {}).get("blocks") or []
    head = (msg.get("data") or {}).get("head")
    if not blocks:
        return (f"Block #{fmt_n(n)} does not exist yet." + (f" The chain is at #{fmt_n(head)}." if head is not None else ""))
    b = blocks[0]
    hd = b.get("header") or {}
    txs = b.get("transactions") or []
    kinds: dict[str, int] = {}
    for t in txs:
        k = str((t or {}).get("tx_type") or "transfer").replace("consensus_rule_update", "rule change proposal") \
            .replace("consensus_rule_vote", "vote").replace("user_tx", "transfer").replace("_", " ")
        kinds[k] = kinds.get(k, 0) + 1
    what = ", ".join(f"{v} {k}{'' if v == 1 else 's'}" for k, v in kinds.items()) if kinds else "no transactions"
    out = [f"⛓ <b>Block #{fmt_n(n)}</b>  <code>{e(short(b.get('block_hash')))}</code>",
           f"Made {ago(hd.get('timestamp'))}, holds {what}."]
    out += ["", link(f"/explorer/?b={n}", "Open in the Explorer")]
    return "\n".join(out)


def answer_status(src: Sources) -> str:
    f = chain_facts(src)
    if not f:
        return "🔴 <b>Our relay does not answer.</b> The HUD may show old data for now.\n\n" + link("/status/", "Status page")
    up, st = f["uptime"], f["status"]
    if not f["connected"]:
        head = "🔴 <b>Our node is offline.</b> The relay is up but cannot reach it."
    elif not f["synced"]:
        head = f"🟠 <b>Running, catching up.</b> Our node is at #{fmt_n(f['height'])}, the network at #{fmt_n(f['tip'])}."
    else:
        head = f"🟢 <b>Running and in sync</b> at block #{fmt_n(f['height'])}."
    out = [head, f"Last block {ago(f['last_ts'])}."]
    now = time.time()
    hours = [r for r in up.get("hours") or [] if isinstance(r, list) and len(r) >= 3 and r[0] >= now - 86400 - 3600]
    samples, ok = sum(r[1] for r in hours), sum(r[2] for r in hours)
    if samples:
        out.append(f"Our node was up {100 * ok / samples:.1f} % of the last 24 h.")
    week = [r for r in up.get("restarts") or [] if (r.get("detected_at") or 0) >= now - 7 * 86400]
    out.append(f"Testnet restarts in the last 7 days: {len(week)}." if week else "No testnet restart in the last 7 days.")
    stalls = [s for s in up.get("stalls") or [] if isinstance(s, dict) and (s.get("end") or 0) >= now - 86400]
    if stalls:
        out.append(f"{plural(len(stalls), 'pause')} of over {round((up.get('stall_seconds') or 600) / 60)} min between blocks in the last 24 h.")
    if st.get("online"):
        n = int(st["online"])
        out.append(f"{fmt_n(n)} {'person is' if n == 1 else 'people are'} watching Tau HUD right now.")
    out += ["", link("/status/", "Status page with the full history")]
    return "\n".join(out)


def answer_help(private: bool = True) -> str:
    out = ["<b>Ask me about the Tau testnet.</b> I read the chain from Tau HUD's own node.", ""]
    out += [h for _, _, h in COMMANDS if h]
    if private:
        out += ["", "You can also just write: <i>height?</i>, <i>last proposal?</i>, <i>is my tx in?</i>, "
                "or paste a transaction hash or an address."]
    out += ["", "Rule change alerts: " + '<a href="https://t.me/' + e(CHANNEL.lstrip("@")) + '">' + e(CHANNEL) + "</a>"
            if CHANNEL.startswith("@") else "", link("/", "tauhud.com")]
    return "\n".join(x for x in out if x is not None)


# ---------------- reading a question ----------------
def parse(text: str, bot_name: str, private: bool) -> tuple[str, str | None] | None:
    """(intent, argument) for a message, or None when it is not for the bot."""
    t = (text or "").strip()
    if not t:
        return None
    m = re.match(r"^/([A-Za-z_]+)(?:@(\w+))?\s*(.*)$", t, re.S)
    if m:
        if m.group(2) and bot_name and m.group(2).lower() != bot_name.lower():
            return None  # a command for another bot in the same group
        cmd, arg = m.group(1).lower(), m.group(3).strip()
        alias = {"start": "help", "h": "height", "height": "height", "p": "proposals", "proposal": "proposals",
                 "proposals": "proposals", "rules": "proposals", "votes": "proposals", "tx": "tx", "a": "address",
                 "address": "address", "balance": "address", "account": "address", "b": "block", "block": "block",
                 "status": "status", "health": "status", "help": "help"}
        if cmd not in alias:
            return ("help", None) if private else None
        intent = alias[cmd]
        if intent == "tx":
            h = HASH.search(arg)
            return "tx", (h.group(1).lower() if h else None)
        if intent == "address":
            a = ADDR.search(arg)
            return "address", (a.group(1).lower() if a else None)
        if intent == "block":
            n = re.search(r"\d+", arg)
            return "block", (n.group(0) if n else None)
        return intent, None
    if not private:  # in groups only commands (and only those addressed to us when named)
        if not bot_name or f"@{bot_name.lower()}" not in t.lower():
            return None
        t = re.sub(rf"@{re.escape(bot_name)}", "", t, flags=re.I).strip()
    low = t.lower()
    a = ADDR.search(t)
    if a:
        return "address", a.group(1).lower()
    h = HASH.search(t)
    if h:
        return "tx", h.group(1).lower()
    if re.search(r"\b(tx|transaction|transfer|payment)s?\b", low):
        return "tx", None
    if re.search(r"\b(balance|address|account|wallet)\b", low):
        return "address", None
    if re.search(r"\b(proposals?|propos\w*|votes?|voting|rules?|governance|agreed|in force)\b", low):
        return "proposals", None
    b = re.search(r"(?:\bblock\s*#?\s*|#)(\d{1,9})\b", low)
    if b:
        return "block", b.group(1)
    if re.search(r"\b(height|how high|blocks?|tip|pace|latest|newest)\b", low):
        return "height", None
    if re.search(r"\b(status|online|offline|up|down|running|alive|sync\w*|working|health\w*|restart\w*)\b", low):
        return "status", None
    return "help", None


async def answer(src: Sources, intent: str, arg: str | None, private: bool = True) -> str:
    if intent == "height":
        return await asyncio.to_thread(answer_height, src)
    if intent == "proposals":
        return await asyncio.to_thread(answer_proposals, src)
    if intent == "tx":
        return await answer_tx(src, arg)
    if intent == "address":
        return await answer_address(src, arg)
    if intent == "block":
        return await answer_block(src, int(arg) if arg else None)
    if intent == "status":
        return await asyncio.to_thread(answer_status, src)
    return answer_help(private)


# ---------------- Telegram ----------------
class Telegram:
    def call(self, method: str, params: dict, timeout: float = 30) -> dict:
        """Bot API call; returns the parsed reply ({"ok": False, ...} on errors). Never logs the URL (it holds the token)."""
        req = urllib.request.Request(f"{API}/bot{TOKEN}/{method}", data=json.dumps(params).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            try:
                info = json.load(exc)
            except ValueError:
                info = {}
            return {"ok": False, "error_code": exc.code, "description": info.get("description", ""),
                    "parameters": info.get("parameters") or {}}
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return {"ok": False, "description": type(exc).__name__}


class Bucket:
    def __init__(self):
        self.tokens, self.at, self.warned = USER_BURST, time.time(), False

    def take(self) -> bool:
        now = time.time()
        self.tokens = min(USER_BURST, self.tokens + (now - self.at) / USER_REFILL)
        self.at = now
        if self.tokens >= 1:
            self.tokens -= 1
            self.warned = False
            return True
        return False


class Bot:
    def __init__(self, tg: Telegram | None = None, src: Sources | None = None):
        self.tg = tg or Telegram()
        self.src = src or Sources()
        self.name = ""
        self.offset = 0
        self.buckets: dict[int, Bucket] = {}
        self.busy = asyncio.Semaphore(4)
        self.answered = 0
        self.tasks: set[asyncio.Task] = set()

    def channel_chat(self, chat: dict) -> bool:
        """True for the alerts channel (or any channel): never answered into."""
        if chat.get("type") not in ("private", "group", "supergroup"):
            return True
        un = "@" + str(chat.get("username") or "")
        return CHANNEL in (str(chat.get("id")), un) or un.lower() == CHANNEL.lower()

    async def setup(self):
        me = await asyncio.to_thread(self.tg.call, "getMe", {})
        self.name = ((me or {}).get("result") or {}).get("username") or ""
        await asyncio.to_thread(self.tg.call, "setMyCommands",
                                {"commands": [{"command": c, "description": d} for c, d, _ in COMMANDS]})
        log.info("answering questions as @%s", self.name or "?")

    async def handle(self, upd: dict):
        msg = upd.get("message") or {}
        chat, user = msg.get("chat") or {}, msg.get("from") or {}
        if not chat or user.get("is_bot") or self.channel_chat(chat):
            return
        if msg.get("is_automatic_forward") or msg.get("sender_chat"):
            return  # a channel post copied into its discussion group, or someone writing as a channel
        if time.time() - float(msg.get("date") or 0) > MAX_AGE:
            return  # asked while the bot was down: an old answer would only confuse
        private = chat.get("type") == "private"
        q = parse(msg.get("text") or "", self.name, private)
        if not q:
            return
        b = self.buckets.setdefault(int(user.get("id") or chat.get("id")), Bucket())
        if not b.take():
            if not b.warned:
                b.warned = True
                await self.reply(chat, msg, f"That is a lot of questions. Ask again in {round(USER_REFILL)} seconds.")
            return
        async with self.busy:
            try:
                text = await answer(self.src, q[0], q[1], private)
            except Exception:
                log.exception("answering %s", q[0])
                text = "Something went wrong on my side. Try again in a minute."
        await self.reply(chat, msg, text)
        self.answered += 1

    async def reply(self, chat: dict, msg: dict, text: str):
        if self.channel_chat(chat):  # belt and braces: answers never reach the alerts channel
            return
        params = {"chat_id": chat["id"], "text": text, "parse_mode": "HTML",
                  "link_preview_options": {"is_disabled": True}}
        if chat.get("type") != "private":
            params["reply_parameters"] = {"message_id": msg.get("message_id"), "allow_sending_without_reply": True}
        r = await asyncio.to_thread(self.tg.call, "sendMessage", params)
        if not r.get("ok"):
            log.warning("sendMessage failed: %s %s", r.get("error_code", ""), r.get("description", ""))

    async def poll_once(self):
        r = await asyncio.to_thread(self.tg.call, "getUpdates",
                                    {"offset": self.offset, "timeout": POLL_TIMEOUT, "allowed_updates": ["message"]},
                                    POLL_TIMEOUT + 15)
        if not r.get("ok"):
            code = r.get("error_code")
            wait = (r.get("parameters") or {}).get("retry_after") or (30 if code == 409 else 5)
            if code == 409:
                log.warning("another process reads this bot's updates (or a webhook is set); retrying in %s s", wait)
            else:
                log.warning("getUpdates failed: %s %s", code or "", r.get("description", ""))
            await asyncio.sleep(float(wait))
            return
        for upd in r.get("result") or []:
            self.offset = max(self.offset, int(upd.get("update_id", 0)) + 1)
            task = asyncio.create_task(self.handle(upd))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
        if len(self.buckets) > 5000:  # forget people who have not asked for a while
            self.buckets = {k: v for k, v in self.buckets.items() if time.time() - v.at < 600}

    async def run(self):
        if not TOKEN:
            log.info("TELEGRAM_BOT_TOKEN is not set; the bot is off")
            while True:
                await asyncio.sleep(3600)
        await self.setup()
        while True:
            try:
                await self.poll_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("poll")
                await asyncio.sleep(5)


async def ask_cli(text: str) -> int:
    q = parse(text, "", True)
    print(await answer(Sources(), *q) if q else "(not a question for the bot)")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if "--ask" in sys.argv:
        i = sys.argv.index("--ask")
        sys.exit(asyncio.run(ask_cli(" ".join(sys.argv[i + 1:]))))
    asyncio.run(Bot().run())

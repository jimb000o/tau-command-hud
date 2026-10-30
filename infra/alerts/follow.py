"""Personal alerts: the bot tells one person when something they follow happens on the chain.

Opt-in only, in a private chat with the bot (bot.py hands these commands here):

  /follow <address>          a message when this account moves: a transfer in or out, its own rule
                             sealed, a rule offer, a co-sign request, a vote; and every vote on a
                             rule change it proposed
  /follow <rule change id>   a message on each vote, and when it is agreed, takes effect or is dropped
  /unfollow <address or id>  or /unfollow all
  /following                 what this chat follows
  /stop                      forget this chat completely

Links on tauhud.com open the bot with the address already in: t.me/<bot>?start=<code>, where the code is
the 48-byte address in base64url (exactly Telegram's 64-character limit), or "p" + the 32-byte rule change
id in base64url.

What is stored (/state/follows.json): per chat only its Telegram chat id, the addresses and rule change
ids it follows and when it started. No names, no messages. /stop, blocking the bot, or 60 days without
any follow left deletes the chat. Plus the last block looked at and, per rule change, its status and
vote count, so a change is told once.

Watching: every FOLLOW_EVERY seconds the bot reads the blocks it has not seen yet from the relay (the
same getblockrange the pages use) and proposals.json from alerts. One message per chat per round, at
most FOLLOW_HOURLY messages per chat an hour; past that it says so once and pauses until the hour is up.
After a chain restart, or when it was down for more than FOLLOW_BACKLOG blocks, it starts again at the
tip without telling old news.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import html
import json
import os
import re
import time

STATE = os.environ.get("FOLLOW_STATE", "/state/follows.json")
SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
MAX_ADDRS = int(os.environ.get("FOLLOW_MAX_ADDRESSES", 10))     # per chat
MAX_PROPS = int(os.environ.get("FOLLOW_MAX_PROPOSALS", 20))     # per chat
MAX_CHATS = int(os.environ.get("FOLLOW_MAX_CHATS", 5000))
EVERY = float(os.environ.get("FOLLOW_EVERY", 20))               # seconds between rounds
HOURLY = int(os.environ.get("FOLLOW_HOURLY", 20))               # messages per chat an hour
BACKLOG = int(os.environ.get("FOLLOW_BACKLOG", 300))            # more blocks behind than this: skip to the tip
LINES = 8                                                        # lines per account in one message
RANGE = 100                                                      # relay's getblockrange maximum
ADDR = re.compile(r"^[0-9a-f]{96}$")
PID = re.compile(r"^[0-9a-f]{8,64}$")
e = html.escape


# ---------------- words ----------------
def short(h: str) -> str:
    h = str(h or "")
    return h[:6] + "…" + h[-4:] if len(h) > 14 else (h or "—")


def fmt_n(n) -> str:
    return f"{int(n):,}"


def fmt_a(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "?"
    return f"{f:,.0f}" if f == int(f) else f"{f:,.4f}".rstrip("0").rstrip(".")


def acc(a: str) -> str:
    return f'<a href="{e(SITE)}/account/?a={e(a)}">{e(short(a))}</a>'


def low(v) -> str:
    return str(v or "").lower()


def yes(v) -> bool:
    return v is not False and str(v).lower() != "false"


# ---------------- deep links ----------------
def start_code(arg: str) -> str | None:
    """The address or rule change id in a t.me/<bot>?start=<code> link, as lowercase hex; None for other start words."""
    a = (arg or "").strip()
    try:
        if len(a) == 64 and re.fullmatch(r"[A-Za-z0-9_-]+", a):
            raw = base64.urlsafe_b64decode(a)
            return raw.hex() if len(raw) == 48 else None
        if len(a) == 44 and a[0] == "p" and re.fullmatch(r"[A-Za-z0-9_-]+", a[1:]):
            raw = base64.urlsafe_b64decode(a[1:] + "=")
            return raw.hex() if len(raw) == 32 else None
    except (binascii.Error, ValueError):
        return None
    return None


def link_code(hexid: str) -> str:
    """The start code for an address (96 hex) or a rule change id (64 hex); the pages build the same in JS."""
    raw = bytes.fromhex(hexid)
    b = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return b if len(raw) == 48 else "p" + b


# ---------------- what one transaction means for one followed account ----------------
def tx_lines(t: dict, a: str) -> list[str]:
    """Plain lines, from the point of view of account a; empty when a is not in it."""
    k = t.get("tx_type") or "user_tx"
    s, to = low(t.get("sender_pubkey")), low(t.get("recipient_pubkey"))
    out: list[str] = []
    if k == "user_tx":
        ops = t.get("operations") or {}
        sent: dict[str, float] = {}
        got: dict[str, float] = {}
        rows = ops.get("1") if isinstance(ops.get("1"), list) else []
        for r in rows:
            if not isinstance(r, list) or len(r) < 3:
                continue
            f, d = low(r[0]), low(r[1])
            try:
                amt = float(r[2])
            except (TypeError, ValueError):
                continue
            if f == a and d != a:
                sent[d] = sent.get(d, 0) + amt
            elif d == a and f != a:
                got[f] = got.get(f, 0) + amt
        if len(sent) > 3:
            out.append(f"Sent {fmt_a(sum(sent.values()))} test AGRS to {len(sent)} accounts")
        else:
            out += [f"Sent {fmt_a(v)} test AGRS to {acc(d)}" for d, v in sent.items()]
        out += [f"Received {fmt_a(v)} test AGRS from {acc(f)}" for f, v in got.items()]
        if s == a and isinstance(ops.get("0"), str) and ops["0"].strip():
            rule = ops["0"].strip()
            out.append(f"Its own rule is now on the chain: <code>{e(rule[:120] + ('…' if len(rule) > 120 else ''))}</code>")
        return out
    if k == "rule_offer":
        if s == a:
            return [f"Offered a rule to {acc(to)}. It counts only if they accept"]
        if to == a:
            return [f"Got a rule offer from {acc(s)}. It counts only if accepted"]
        return []
    if k.startswith("rule_offer_") and s == a:
        return ["Accepted a rule offer. The rule now applies to it" if k == "rule_offer_accept" else "Refused a rule offer"]
    if k == "consensus_rule_update" and s == a:
        at = t.get("activate_at_height")
        return ["Proposed a change to the network's rules" + (f", deciding at block #{fmt_n(at)}" if str(at or "").isdigit() else "")
                + ". You get a message on every vote"]
    if k == "consensus_rule_vote" and s == a:
        return [f"Voted {'yes' if yes(t.get('approve', True)) else 'no'} on a rule change"]
    if k == "approval_request":
        apps = t.get("approvers")
        apps = [low(x[0] if isinstance(x, list) else x) for x in apps] if isinstance(apps, list) else \
            [low(x) for x in apps] if isinstance(apps, dict) else []
        if s == a:
            return [f"Asked {len(apps)} co-signer{'s' if len(apps) != 1 else ''} to approve {fmt_a(t.get('amount'))} test AGRS to {acc(to)}"]
        if to == a:
            return [f"{fmt_a(t.get('amount'))} test AGRS from {acc(s)} wait for co-signers"]
        if a in apps:
            return [f"{acc(s)} asks it to co-sign {fmt_a(t.get('amount'))} test AGRS"]
        return []
    if k == "transfer_vote" and s == a:
        return ["Co-signed a transfer" if yes(t.get("approve", True)) else "Refused to co-sign a transfer"]
    if k == "retractable_transfer":
        until = (f"block #{fmt_n(t['release_at_height'])}" if str(t.get("release_at_height") or "").isdigit()
                 else time.strftime("%d %b %H:%M UTC", time.gmtime(float(t["release_at_time"]))) if t.get("release_at_time") else "")
        if s == a:
            return [f"Sent {fmt_a(t.get('amount'))} test AGRS to {acc(to)}, can be pulled back" + (f" until {until}" if until else "")]
        if to == a:
            return [f"{fmt_a(t.get('amount'))} test AGRS on the way from {acc(s)}" + (f", released at {until}" if until else "")]
        return []
    if k == "retract_transfer" and s == a:
        return ["Pulled back a retractable transfer"]
    if s == a:
        return [f"Sent a {e(k.replace('_', ' '))} transaction"]
    return []


def block_events(blocks: list[dict], watched: set[str]) -> dict[str, list[tuple[int, str]]]:
    """address -> [(block, line)] for the watched addresses, oldest first."""
    out: dict[str, list[tuple[int, str]]] = {}
    for b in blocks:
        try:
            h = int((b.get("header") or {}).get("block_number"))
        except (TypeError, ValueError):
            continue
        for t in b.get("transactions") or []:
            if not isinstance(t, dict):
                continue
            blob = json.dumps(t).lower()  # cheap first look: is any watched address in it at all?
            for a in watched:
                if a in blob:
                    for line in tx_lines(t, a):
                        out.setdefault(a, []).append((h, line))
    return out


def moves_text(per_addr: dict[str, list[tuple[int, str]]]) -> str:
    one = len(per_addr) == 1
    out = ["🔔 <b>" + ("An account you follow moved" if one else "Accounts you follow moved") + "</b>"]
    for a, rows in per_addr.items():
        out += ["", f"<b>{acc(a)}</b>"]
        for h, line in rows[:LINES]:
            out.append(f"• {line} · block <a href=\"{e(SITE)}/explorer/?b={h}\">#{fmt_n(h)}</a>")
        if len(rows) > LINES:
            out.append(f"…and {len(rows) - LINES} more on " + f'<a href="{e(SITE)}/account/?a={e(a)}">its page</a>')
    out += ["", "Test AGRS have no value. /following · /stop"]
    return "\n".join(out)


# ---------------- rule changes ----------------
def prop_title(p: dict) -> str:
    return f'<a href="{e(SITE)}/proposals/#{e(p["id"][:16])}">{e(p.get("title") or "A rule change")}</a>'


def prop_news(p: dict, old: list | None) -> list[str]:
    """What changed for this rule change since the last look (old = [status, number of votes])."""
    if old is None:
        return []
    out = []
    votes = p.get("votes") or []
    for v in votes[old[1]:]:
        how = "yes" if v.get("approve", True) else "no"
        counted = "" if v.get("counted") else " (not counted: the vote was closed or it had voted already)"
        out.append(f"{acc(low(v.get('voter')))} voted {how} at block #{fmt_n(v.get('h') or 0)}{counted}. "
                   f"{p.get('counted_votes', 0)} of {p.get('thr') or 1} vote{'s' if (p.get('thr') or 1) != 1 else ''} needed")
    st = p.get("status")
    if st != old[0]:
        if st == "agreed":
            out.append(f"Agreed. It takes effect at block #{fmt_n(p.get('activate_at') or 0)}")
        elif st == "active":
            out.append(f"In force since block #{fmt_n(p.get('activated_at') or p.get('activate_at') or 0)}. The network's rules changed by agreement")
        elif st == "dropped":
            out.append(f"Dropped at block #{fmt_n(p.get('expired_at') or p.get('activate_at') or 0)}: not enough votes in time, nothing changed")
    return out


def prop_text(items: list[tuple[dict, list[str], str]]) -> str:
    out = ["🗳️ <b>" + ("News on a rule change you follow" if len(items) == 1 else "News on rule changes you follow") + "</b>"]
    for p, lines, why in items:
        out += ["", f"<b>{prop_title(p)}</b>" + (f"  <i>{e(why)}</i>" if why else "")] + [f"• {x}" for x in lines]
    out += ["", "/following · /stop"]
    return "\n".join(out)


def prop_state(p: dict) -> str:
    st = p.get("status")
    if st == "voting":
        return f"Waiting for votes: {p.get('counted_votes', 0)} of {p.get('thr') or 1}, deadline block #{fmt_n(p.get('activate_at') or 0)}."
    if st == "agreed":
        return f"Agreed, takes effect at block #{fmt_n(p.get('activate_at') or 0)}."
    if st == "active":
        return "Already in force."
    return "Already dropped."


# ---------------- the store ----------------
class Store:
    def __init__(self, path: str = STATE):
        self.path = path
        self.d = {"v": 1, "chats": {}, "head": None, "block1": None, "props": {}}
        try:
            with open(path, encoding="utf-8") as f:
                got = json.load(f)
            if isinstance(got, dict) and isinstance(got.get("chats"), dict):
                self.d.update(got)
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.d, f, separators=(",", ":"))
            os.replace(tmp, self.path)
        except OSError:
            pass

    @property
    def chats(self) -> dict:
        return self.d["chats"]

    def chat(self, cid) -> dict | None:
        return self.chats.get(str(cid))

    def add(self, cid, kind: str, x: str) -> str:
        """'added', 'already', 'full' or 'busy' (too many chats)."""
        c = self.chat(cid)
        if c is None:
            if len(self.chats) >= MAX_CHATS:
                return "busy"
            c = self.chats[str(cid)] = {"a": [], "p": [], "since": round(time.time())}
        lst, cap = (c["a"], MAX_ADDRS) if kind == "a" else (c["p"], MAX_PROPS)
        if x in lst:
            return "already"
        if len(lst) >= cap:
            return "full"
        lst.append(x)
        c["at"] = round(time.time())
        self.save()
        return "added"

    def remove(self, cid, x: str) -> bool:
        c = self.chat(cid)
        if not c:
            return False
        hit = x in c["a"] or x in c["p"]
        c["a"] = [v for v in c["a"] if v != x]
        c["p"] = [v for v in c["p"] if v != x]
        if not c["a"] and not c["p"]:
            c["empty"] = round(time.time())
        self.save()
        return hit

    def stop(self, cid) -> bool:
        hit = self.chats.pop(str(cid), None) is not None
        self.save()
        return hit

    def tidy(self, now: float):
        """Chats with nothing followed for 60 days are forgotten."""
        old = [k for k, c in self.chats.items() if not c["a"] and not c["p"] and now - c.get("empty", now) > 60 * 86400]
        for k in old:
            del self.chats[k]
        if old:
            self.save()

    def watched_addrs(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for k, c in self.chats.items():
            for a in c["a"]:
                out.setdefault(a, []).append(k)
        return out


# ---------------- the watcher ----------------
class Watcher:
    """Owned by bot.Bot: send(chat_id, text) -> 'ok' | 'gone' | 'error'; lookup(command) -> relay reply."""

    def __init__(self, store: Store, send, lookup, proposals, height):
        self.store, self.send, self.lookup, self.proposals, self.height = store, send, lookup, proposals, height
        self.sent: dict[str, list[float]] = {}     # chat -> times of messages this hour
        self.paused: dict[str, float] = {}         # chat -> paused until

    async def deliver(self, cid: str, text: str, now: float):
        if self.paused.get(cid, 0) > now:
            return
        times = [t for t in self.sent.get(cid, []) if now - t < 3600]
        if len(times) >= HOURLY:
            until = times[0] + 3600
            self.paused[cid] = until
            text = (f"⏸ That is a lot of activity: {HOURLY} messages this hour. I pause until "
                    f"{time.strftime('%H:%M UTC', time.gmtime(until))}; what happens meanwhile is on the account pages. "
                    "/following · /stop")
        r = await self.send(cid, text)
        if r == "gone":  # blocked the bot or deleted the chat: forget it
            self.store.stop(cid)
            return
        times.append(now)
        self.sent[cid] = times

    async def round(self, now: float | None = None):
        now = now or time.time()
        pj = self.proposals() or {}
        b1 = (pj.get("chain") or {}).get("block1_hash")
        head = await asyncio.to_thread(self.height)
        st = self.store.d
        if b1 and st.get("block1") and b1 != st["block1"]:  # chain restart: old heights and ids mean nothing now
            st["head"], st["props"], st["primed"] = None, {}, False
        if b1:
            st["block1"] = b1
        if head is not None:
            await self.blocks(int(head), now)
        await self.rule_changes(pj, now)
        self.store.tidy(now)
        self.store.save()

    async def blocks(self, head: int, now: float):
        st = self.store.d
        last = st.get("head")
        if last is None or head < last or head - last > BACKLOG:
            st["head"] = head  # first start, restart or a long gap: begin at the tip
            return
        watched = self.store.watched_addrs()
        if not watched or head == last:
            st["head"] = head
            return
        got: list[dict] = []
        start = last + 1
        while start <= head:
            msg = await self.lookup(f"getblockrange {start} {min(RANGE, head - start + 1)}")
            if not msg or msg.get("status") != "ok":
                return  # try the same blocks next round
            blocks = (msg.get("data") or {}).get("blocks") or []
            if not blocks:
                break
            got += blocks
            start += len(blocks)
        st["head"] = start - 1
        ev = block_events(got, set(watched))
        per_chat: dict[str, dict[str, list]] = {}
        for a, rows in ev.items():
            for cid in watched.get(a, []):
                per_chat.setdefault(cid, {})[a] = rows
        for cid, per_addr in per_chat.items():
            await self.deliver(cid, moves_text(per_addr), now)

    async def rule_changes(self, pj: dict, now: float):
        props = pj.get("proposals")
        if not isinstance(props, list):
            return
        snap = self.store.d["props"]
        primed = bool(self.store.d.get("primed"))  # the first look (and the first after a restart) only takes note
        self.store.d["primed"] = True
        chats = self.store.chats
        per_chat: dict[str, list] = {}
        for p in props:
            pid = p.get("id")
            if not pid:
                continue
            old = snap.get(pid) or (["voting", 0] if primed else None)  # new since the last look: all of it is news
            news = prop_news(p, old)
            snap[pid] = [p.get("status"), len(p.get("votes") or [])]
            if not news:
                continue
            final = p.get("status") in ("active", "dropped")
            for cid, c in list(chats.items()):
                mine = low(p.get("proposer")) in c["a"]
                if pid in c["p"] or mine:
                    why = f"proposed by {short(low(p.get('proposer')))}" if mine and pid not in c["p"] else ""
                    lines = list(news)
                    if final and pid in c["p"]:
                        lines.append("Decided, so I stop following it")
                        c["p"] = [x for x in c["p"] if x != pid]
                    per_chat.setdefault(cid, []).append((p, lines, why))
        for cid, items in per_chat.items():
            await self.deliver(cid, prop_text(items), now)


# ---------------- commands (bot.py routes /follow, /unfollow, /following, /stop here) ----------------
PRIVACY = ("I keep only this chat's id and what you follow, nothing else. /stop deletes it all. "
           f'<a href="{e(SITE)}/legal/?l=en">Privacy</a>')


def find_prop(pj: dict | None, x: str) -> dict | None:
    for p in (pj or {}).get("proposals") or []:
        if str(p.get("id", "")).startswith(x):
            return p
    return None


def command(store: Store, cid, intent: str, arg: str | None, pj: dict | None, private: bool) -> str:
    if not private:
        return "Alerts work in a private chat: write to me directly and send the same command there."
    x = low(arg).removeprefix("0x").strip()
    if intent == "stop":
        had = store.stop(cid)
        return ("🔕 Done. I forgot this chat and everything it followed. You can still ask me questions; "
                "nothing is kept for that.") if had else "Nothing to stop: this chat follows nothing and I keep nothing about it."
    if intent == "following":
        c = store.chat(cid)
        if not c or (not c["a"] and not c["p"]):
            return ("You follow nothing yet.\n<code>/follow &lt;address&gt;</code>  a message when an account moves\n"
                    "<code>/follow &lt;rule change id&gt;</code>  every vote on a rule change\n"
                    f"Or tap “Telegram alerts” on an account at {e(SITE.split('//')[-1])}/account/.\n\n" + PRIVACY)
        out = ["🔔 <b>What you follow</b>"]
        out += [f"• account {acc(a)}  <code>/unfollow {a}</code>" for a in c["a"]]
        for pid in c["p"]:
            p = find_prop(pj, pid)
            out.append(f"• rule change {prop_title(p) if p else e(short(pid))}  <code>/unfollow {pid[:16]}</code>")
        out += ["", "<code>/unfollow all</code> or /stop to end everything. " + PRIVACY]
        return "\n".join(out)
    if intent == "unfollow":
        if x in ("all", "everything"):
            store.stop(cid)
            return "🔕 You follow nothing now, and I forgot this chat."
        c = store.chat(cid) or {"a": [], "p": []}
        full = next((v for v in c["a"] + c["p"] if v == x or (len(x) >= 8 and v.startswith(x))), None)
        if not full:
            return "You do not follow that. /following lists what you do."
        store.remove(cid, full)
        return f"🔕 Stopped following {e(short(full))}. /following lists the rest."
    # follow
    if not x:
        return ("What should I follow? Send <code>/follow &lt;address&gt;</code> (96 characters, 0–9 and a–f) "
                "or <code>/follow &lt;rule change id&gt;</code>.\n\n" + PRIVACY)
    if ADDR.match(x):
        r = store.add(cid, "a", x)
        if r == "full":
            return f"You already follow {MAX_ADDRS} accounts, the most I can watch for one chat. /following to drop one."
        if r == "busy":
            return "I am watching for as many people as I can right now. Please try again in a few days."
        head = ("🔔 <b>Following</b> " + acc(x)) if r == "added" else ("You already follow " + acc(x))
        return "\n".join([head, "",
                          "I write when it sends or receives test AGRS, when its own rule lands in a block, on rule offers and "
                          "co-sign requests, when it votes, and on every vote on a rule change it proposes.", "",
                          "Test AGRS have no value. <code>/unfollow " + x[:16] + "</code> ends this one. " + PRIVACY])
    if PID.match(x):
        p = find_prop(pj, x)
        if not p:
            return "I do not know a rule change with this id on the current chain. The Proposals page shows each one's id."
        if p.get("status") in ("active", "dropped"):
            return f"{prop_title(p)} is decided: {prop_state(p)} Nothing more will happen to it."
        r = store.add(cid, "p", p["id"])
        if r == "full":
            return f"You already follow {MAX_PROPS} rule changes. /following to drop one."
        if r == "busy":
            return "I am watching for as many people as I can right now. Please try again in a few days."
        return "\n".join([("🗳️ <b>Following</b> " if r == "added" else "You already follow ") + prop_title(p),
                          prop_state(p), "", "I write on every vote and when it is agreed, takes effect or is dropped. "
                          "Then I stop following it by myself. " + PRIVACY])
    return "That is not an address (96 characters) or a rule change id. Copy it from tauhud.com and try again."

"""Proposal tracker and alerts for the Tau testnet.

Reads the chain from the relay (the same read-only WebSocket protocol the
pages use), replays governance block by block exactly like history/ does
(consensus/governance.py at the pinned tau-testnet commit), and turns what
happened into news:

  proposed   a rule change was proposed
  agreed     it reached the quorum (while one vote is enough, a proposal agreed
             within PROPOSED_HOLD_SECONDS is posted once, as "proposed and agreed")
  active     it took effect at its activation block
  dropped    its deadline passed with too few votes
  restart    the testnet started a new chain

It also watches the testnet health score (relay GET /health-score) and posts
to Telegram when the testnet goes down and when it recovers, after the new
state has held for HEALTH_CONFIRM_SECONDS, so a short blip or an update of
our own server stays quiet.

Every event goes into /public/proposals.json (the tracker page at
tauhud.com/proposals/) and /public/feed.xml (Atom), which Caddy serves at
https://node.tauhud.com/. New events are also posted to Telegram and X when
their credentials are set in .env; without them that channel is simply off.

Nothing is posted for what the watcher finds on its very first run, and
nothing whose block is older than POST_MAX_AGE_SECONDS, so a fresh volume or
a long outage never floods the channel with old news.

Once a week (Monday 09:00 UTC by default) it also posts a recap image of the
week (recap.py) and keeps a copy at https://node.tauhud.com/recap/latest.png.

  python alerts.py                  run the watcher
  python alerts.py --test           send one test post to each configured channel
  python alerts.py --preview        print how the newest rule changes would be posted, post nothing
  python alerts.py --recap-preview  draw this week's recap and save it, post nothing
  python alerts.py --recap-now      draw the recap and post it to each configured channel
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import html
import io
import json
import logging
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape as xml_escape

from websockets.asyncio.client import connect

import explain
import recap

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
# the question bot (bot.py, same token): every channel post carries buttons that open it; empty = no buttons
TELEGRAM_BOT_NAME = os.environ.get("TELEGRAM_BOT_USERNAME", "tauhud_alerts_bot").strip().lstrip("@")
X_KEYS = {k: os.environ.get(k, "").strip() for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")}
RELAY_HTTP = os.environ.get("RELAY_HTTP", "http://relay:8080")
RECAP_ON = os.environ.get("RECAP_ENABLED", "true").lower() in ("1", "true", "yes")
RECAP_WEEKDAY = int(os.environ.get("RECAP_WEEKDAY", 0))   # 0 = Monday
RECAP_HOUR = int(os.environ.get("RECAP_HOUR", 9))         # UTC
HEALTH_ON = os.environ.get("HEALTH_ALERTS", "true").lower() in ("1", "true", "yes")
HEALTH_DOWN_BELOW = float(os.environ.get("HEALTH_DOWN_BELOW", 50))   # also "down" whenever the relay says so
HEALTH_UP_AT = float(os.environ.get("HEALTH_UP_AT", 70))             # recovered at or above this
HEALTH_CONFIRM = float(os.environ.get("HEALTH_CONFIRM_SECONDS", 600))
HEALTH_EVERY = float(os.environ.get("HEALTH_POLL_SECONDS", 60))
# New nodes on the network (relay /peers and /community/board): one post per node,
# only after it stayed NEWNODE_HOLD seconds, never for one first seen more than a
# day ago, at most NEWNODE_DAILY_CAP posts a day (the rest are recorded, not posted).
NEWNODE_ON = os.environ.get("NEWNODE_ALERTS", "true").lower() in ("1", "true", "yes")
NEWNODE_HOLD = float(os.environ.get("NEWNODE_HOLD_SECONDS", 1800))
NEWNODE_DAILY_CAP = int(os.environ.get("NEWNODE_DAILY_CAP", 3))
NEWNODE_EVERY = float(os.environ.get("NEWNODE_POLL_SECONDS", 300))
FEED_ITEMS = 100
RANGE = 100           # relay's getblockrange maximum
REFETCH_TAIL = 6      # blocks re-read every poll so a replaced tip block (reorg) is noticed
MAX_TRIES = 8
# While one yes vote is enough (one validator), a proposal is usually agreed a block or two later.
# Its "proposed" post waits this long; if it is agreed meanwhile, one combined post goes out instead of two.
PROPOSED_HOLD = float(os.environ.get("PROPOSED_HOLD_SECONDS", 600))
SOLO_NOTE = ("One yes vote is enough: the testnet has one validator, and any account may vote. "
             "Tau HUD has applied to become a second validator; then a change would need two yes votes.")

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
    validators, quorum, fee, rev, mode = list(GENESIS_VALIDATORS), GENESIS_QUORUM, 10, 1, "validator_set"
    spec = explain.clauses(explain.GENESIS_RULES)   # the rules in force, stream -> clause
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
                p["explain"] = explain.explain(p["revisions"], p["patch"], spec)
                p["diff"] = explain.diff(p["revisions"], spec) if p["revisions"] else None
                p["title"] = p["explain"]["title"]
                p["parts"] = [c["topic"] + ": " + c["text"] for c in p["explain"]["changes"]] or [p["title"]]
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
            spec = explain.apply(spec, p["revisions"])
            f = fee_of(spec.get("o9", ""))
            if f is not None:
                fee = f
            patch = p["patch"] or {}
            if patch.get("validator_additions") or patch.get("validator_removals"):
                rem = {str(x).lower() for x in patch.get("validator_removals") or []}
                validators = sorted({*(v for v in validators if v not in rem), *(str(x).lower() for x in patch.get("validator_additions") or [])})
            if "vote_quorum" in patch:
                quorum = patch["vote_quorum"]
            if patch.get("eligibility_mode"):
                mode = patch["eligibility_mode"]
            events.append({"kind": "active", "h": h, "ts": ts, "id": p["id"]})
    thr = threshold(quorum, len(validators))
    for p in order:
        p["status"] = ("active" if p["activated_at"] is not None else "dropped" if p["expired_at"] is not None
                       else "agreed" if p["approved_at"] is not None else "voting")
        p["counted_votes"] = sum(1 for v in p["votes"] if v["counted"])
        if p["status"] == "voting":
            p["thr"] = thr  # what it needs now
    now = {"head": hi, "first": lo, "rev": rev, "fee": fee, "validators": len(validators), "quorum": quorum, "thr": thr, "mode": mode}
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
    """Everything a post says about an event: a headline, what changes, why it
    matters, the facts, a plain one-paragraph body (feed, page, X) and a link."""
    k = ev["kind"]
    if k == "restart":
        old = ev.get("old_tip")
        why = "The test network started over: balances, rules and history begin again from the starting state."
        facts = ([f"The old chain ended at block #{fmt_n(old)}."] if old else []) + ["Tau HUD follows the new chain from block 1."]
        return {"headline": "The Tau testnet restarted", "what": [], "why": why, "why_title": "What happened", "facts": facts,
                "body": why + " " + " ".join(facts), "link": f"{SITE}/stats/"}
    x = (p or {}).get("explain") or {"title": (p or {}).get("title", "a rule change"), "changes": [], "why": ""}
    title = x["title"]
    what = [f"{c['topic']}: {c['text']}" for c in x["changes"]]
    link = f"{SITE}/proposals/#{(p or {}).get('id', '')[:16]}"
    left = p["activate_at"] - head if p else 0
    when = f"block #{fmt_n(p['activate_at'])}{eta_txt(left, pace)}" if p else ""
    if k == "proposed":
        need = max(0, p["thr"] - p["counted_votes"]) if p.get("approved_at") is None else 0
        headline = f"New proposal: {title}"
        facts = [f"Needs {plural(p['thr'], 'yes vote')} by {when}, or it is dropped.",
                 f"Proposed at block #{fmt_n(ev['h'])} by {short(p['proposer'])}."]
        if need == 0 and p.get("approved_at") is not None:
            facts[0] = f"Already agreed. Takes effect at {when}."
    elif k == "agreed" and ev.get("combined"):
        headline = f"New rule change, agreed right away: {title}"
        facts = [f"Takes effect at {when}. Until then the current rules apply.",
                 f"Proposed at block #{fmt_n(p['proposed_at'])} by {short(p['proposer'])}, agreed at block #{fmt_n(ev['h'])} "
                 f"with {p['counted_votes']} of {p['thr']} vote{'' if p['thr'] == 1 else 's'} needed."]
    elif k == "agreed":
        headline = f"Agreed: {title}"
        facts = [f"Takes effect at {when}. Until then the current rules apply.",
                 f"Votes: {p['counted_votes']} of {p['thr']} needed, reached at block #{fmt_n(ev['h'])}."]
    elif k == "active":
        headline = f"Now in force: {title}"
        facts = [f"In force since block #{fmt_n(ev['h'])}. The consensus rules are now at revision {p['rev']}."]
    elif k == "dropped":
        headline = f"Dropped: {title}"
        facts = [f"It got {p['counted_votes']} of the {plural(p['thr'], 'vote')} it needed by its deadline, block #{fmt_n(ev['h'])}. "
                 "Nothing changes."]
    else:
        return {"headline": k, "what": [], "why": "", "facts": [], "body": "", "link": SITE}
    why = x.get("why", "") if k != "dropped" else ""
    if k == "active":  # it happened: say it in the present
        for a, b in NOW_TENSE:
            why = why.replace(a, b)
    body = " ".join(([("What changes: " + "; ".join(what) + ".")] if what else []) + ([why] if why else []) + facts)
    # the changed lines of the rule text, not for a dropped proposal (nothing changes)
    d = (p or {}).get("diff")
    rdiff = None
    if d and k != "dropped":
        rdiff = {"summary": explain.diff_summary(d), "lines": [r for r in d["lines"] if r[0] != " "][:DIFF_LINES],
                 "more": max(0, d["added"] + d["removed"] - DIFF_LINES)}
    note = SOLO_NOTE if k in ("proposed", "agreed") and p and p.get("thr") == 1 else None
    return {"headline": headline, "label": x.get("label"), "what": what, "why": why, "facts": facts, "diff": rdiff, "note": note,
            "what_title": "What changed" if k == "active" else "What it would change" if k == "dropped" else "What changes",
            "severity": x.get("severity"), "body": body, "link": link}


DIFF_LINES = 6  # changed lines shown in a post; the rest is on the page

NOW_TENSE = [("would cost", "costs"), ("would rest", "rests"), ("could no longer", "can no longer"), ("would be accepted", "are accepted"),
             ("would make", "make"), ("would follow", "follow"), ("Nothing would change", "Nothing changed"), ("If it takes effect, ", "")]
ICONS = {"proposed": "🗳️", "agreed": "✅", "active": "⚡", "dropped": "❌", "restart": "🔄"}


def telegram_text(item: dict) -> str:
    e = html.escape
    if "facts" not in item:  # posts recorded before explanations existed
        return (f"{ICONS.get(item['kind'], '•')} <b>{e(item['headline'])}</b>\n{e(item['body'])}\n\n"
                f"<a href=\"{e(item['link'])}\">Open in Tau HUD</a>")
    # order: what it means first, then what changes and the facts; the raw diff comes last, for those who want it
    out = [f"{ICONS.get(item['kind'], '•')} <b>{e(item['headline'])}</b>"]
    if item.get("label"):
        out.append(f"<i>Proposer's title: “{e(item['label'])}”</i>")
    if item.get("why"):
        warn = "⚠️ " if item.get("severity") in ("halt", "unsafe") else ""
        out += ["", f"<b>{e(item.get('why_title', 'Why it matters'))}</b>", warn + e(item["why"])]
    if item["what"]:
        out += ["", f"<b>{e(item.get('what_title', 'What changes'))}</b>"] + [f"• {e(w)}" for w in item["what"]]
    if item["facts"]:
        out += [""] + [e(f) for f in item["facts"]]
    d = item.get("diff")
    if d:  # Telegram has no colours: + and − carry the meaning
        if d["lines"]:
            code = "\n".join(("+ " if op == "+" else "- ") + t.strip() for op, t in d["lines"])
            more = f"\n… {d['more']} more on the page" if d["more"] else ""
            out += ["", f"<b>Rule text diff</b> ({e(d['summary'])})", f"<pre><code class=\"language-diff\">{e(code + more)}</code></pre>"]
        else:
            out += ["", "<b>Rule text diff</b>: none. The text equals the rules in force."]
    if item.get("note"):
        out += ["", f"<i>{e(item['note'])}</i>"]
    label = "Open in Tau HUD" if item["kind"] == "restart" else "Details and votes on Tau HUD"
    out += ["", f"<a href=\"{e(item['link'])}\">{label}</a>"]
    return "\n".join(out)


def x_text(item: dict) -> str:
    # X counts every link as 23 characters
    tail = f"\n\n{item['link']} #Tau"
    room = 280 - 23 - len(" #Tau") - 2
    icon = ICONS.get(item["kind"], "")
    for text in (f"{icon} {item['headline']}\n{item.get('why') or item['body']}",
                 f"{icon} {item['headline']}"):
        text = text.strip()
        if len(text) <= room:
            return text + tail
    return text[: room - 1] + "…" + tail


def health_problems(h: dict) -> list[str]:
    """The factors that lose the most points, in plain words, worst first."""
    out = []
    for f in sorted(h.get("factors") or [], key=lambda f: f["points"] - f["weight"]):
        if f["weight"] - f["points"] < 2:
            continue
        k, v = f["key"], f.get("value")
        if k == "node":
            out.append("Our node does not answer, so we cannot see the testnet right now")
        elif k == "sync":
            out.append(f"Our node is not in sync with the network ({v})")
        elif k == "last_block":
            out.append(f"No new block for {fmt_dur(v)}" if isinstance(v, (int, float)) else "No blocks yet")
        elif k == "pace":
            out.append(f"Only {fmt_n(v)} blocks in the last hour ({f.get('note', '')})")
        elif k == "availability" and isinstance(v, (int, float)):
            out.append(f"Live and in sync only {v * 100:.1f} % of the last 24 hours")
        elif k == "stability" and isinstance(v, dict):
            parts = [plural(v[x], x[:-1]) for x in ("restarts", "stalls", "reorgs") if v.get(x)]
            out.append("In the last 24 hours: " + ", ".join(parts))
        elif k == "mempool" and isinstance(v, dict):
            if v.get("sealed"):
                out.append(f"{plural(v['sealed'], 'transaction')} already in a block still listed as waiting (IDNI #81)")
            elif v.get("oldest"):
                out.append(f"A transaction has been waiting for {fmt_dur(v['oldest'])}")
    return out[:3]


def fmt_dur(s: float) -> str:
    s = max(0, round(s))
    if s < 90:
        return plural(s, "second")
    if s < 5400:
        return plural(round(s / 60), "minute")
    h, m = divmod(round(s / 60), 60)
    return f"{h} h {m} min" if m else plural(h, "hour")


def health_text(kind: str, h: dict | None, since: float | None = None, now: float | None = None) -> str:
    e = html.escape
    link = f"<a href=\"{SITE}/status/\">Live status on Tau HUD</a>"
    if kind == "down":
        if h is None:
            return ("🔴 <b>Tau testnet: no data</b>\nOur relay does not answer, so we cannot tell whether the testnet runs. "
                    f"We are on it.\n\n{link}")
        lines = [f"🔴 <b>Tau testnet health {h['score']}/100: {e(h['label'])}</b>"]
        lines += [f"• {e(p)}" for p in health_problems(h)]
        return "\n".join(lines + ["", "We post again when it recovers.", link])
    lines = [f"🟢 <b>Tau testnet recovered: health {h['score']}/100</b>"]
    if since:
        lines.append(f"It was down for {fmt_dur((now or time.time()) - since)}.")
    rest = health_problems(h)
    if rest:
        lines += ["Still not perfect:"] + [f"• {e(p)}" for p in rest]
    return "\n".join(lines + ["", link])


def new_nodes(peers: dict | None, board: dict | None, known: dict, now: float) -> list[dict]:
    """Nodes worth one post: a kit node that has reported for NEWNODE_HOLD, or a
    peer (not the bootnode, not a kit node) our node has known that long and
    still sees. Each comes back once: `known` holds every key ever handled."""
    out = []
    for n in (board or {}).get("nodes") or []:
        key = "kit:" + str(n.get("id"))
        if key in known or not n.get("online"):
            continue
        first, last = n.get("first_seen") or now, n.get("last_seen") or 0
        if last - first >= NEWNODE_HOLD and now - first < 86400 + NEWNODE_HOLD:
            out.append({"key": key, "kind": "kit", "name": str(n.get("name") or "node"), "for": last - first,
                        "height": n.get("height")})
    kit_peers = {p["id"] for p in (peers or {}).get("peers") or [] if p.get("community")}
    for p in (peers or {}).get("peers") or []:
        key = "peer:" + str(p.get("id"))
        if key in known or p.get("label") or p["id"] in kit_peers:
            continue
        first, last = p.get("first_seen") or now, p.get("last_seen") or 0
        if now - last < 600 and last - first >= NEWNODE_HOLD and now - first < 86400 + NEWNODE_HOLD:
            out.append({"key": key, "kind": "peer", "id": str(p["id"]), "for": last - first, "head": p.get("head")})
    return out


def nodes_online(peers: dict | None, board: dict | None) -> int:
    """Our node, the online peers and the online kit nodes that are not among them."""
    ps = (peers or {}).get("peers") or []
    named = {p["community"]["id"] for p in ps if p.get("community") and p.get("online")}
    kit = [n for n in (board or {}).get("nodes") or [] if n.get("online") and n.get("id") not in named]
    return 1 + sum(1 for p in ps if p.get("online")) + len(kit)


def newnode_text(n: dict, online: int) -> str:
    e = html.escape
    link = f"<a href=\"{SITE}/nodes/\">All nodes on Tau HUD</a>"
    if n["kind"] == "kit":
        head = f"🆕 <b>New community node: {e(n['name'])}</b>"
        body = (f"Someone started a Tau testnet node with the Tau HUD kit. It has checked every block for "
                f"{fmt_dur(n['for'])}" + (f" and is at block #{fmt_n(n['height'])}" if n.get("height") else "") + ".")
    else:
        head = "🆕 <b>A new node joined the Tau testnet</b>"
        body = (f"Our node has seen it for {fmt_dur(n['for'])}" + (f", at block #{fmt_n(n['head'])}" if n.get("head") else "")
                + f". Peer {e(n['id'][:8])}…{e(n['id'][-4:])}, no name: it does not run our kit.")
    return "\n".join([head, body, f"Nodes online now: {online}.", "", link])


# ---------------- outlets ----------------
class Outlet:
    name = ""

    def enabled(self) -> bool:
        raise NotImplementedError

    def send(self, item: dict) -> tuple[bool, float | None, str]:
        """(sent, retry_after_seconds or None, error text)."""
        raise NotImplementedError

    def send_photo(self, png: bytes, r: dict) -> tuple[bool, float | None, str]:
        """Post the weekly recap image with its caption."""
        raise NotImplementedError


def multipart(fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
    boundary = "tauhud" + secrets.token_hex(12)
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, (name, data, ctype) in files.items():
        out.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\n'
                  f"Content-Type: {ctype}\r\n\r\n".encode())
        out.write(data + b"\r\n")
    out.write(f"--{boundary}--\r\n".encode())
    return out.getvalue(), f"multipart/form-data; boundary={boundary}"


def ask_buttons() -> dict:
    """Buttons under each channel post; they open the question bot in a private chat (same as bot.buttons)."""
    b = f"https://t.me/{TELEGRAM_BOT_NAME}?start="
    return {"inline_keyboard": [[{"text": "💬 Ask the bot", "url": b + "help"},
                                 {"text": "⛓ Height", "url": b + "height"},
                                 {"text": "🟢 Status", "url": b + "status"}]]}


class Telegram(Outlet):
    name = "telegram"

    def enabled(self) -> bool:
        return bool(TELEGRAM_TOKEN and TELEGRAM_CHAT)

    def send_text(self, text: str) -> tuple[bool, float | None, str]:
        msg = {"chat_id": TELEGRAM_CHAT, "text": text, "parse_mode": "HTML", "link_preview_options": {"is_disabled": True}}
        if TELEGRAM_BOT_NAME:
            msg["reply_markup"] = ask_buttons()
        body = json.dumps(msg).encode()
        return self.call("sendMessage", body, "application/json")

    def send_photo(self, png, r):
        fields = {"chat_id": TELEGRAM_CHAT, "caption": recap.caption_html(r, SITE), "parse_mode": "HTML"}
        if TELEGRAM_BOT_NAME:
            fields["reply_markup"] = json.dumps(ask_buttons())
        body, ctype = multipart(fields,
                                {"photo": (f"tau-recap-{recap.week_key(r['end'] - 1)}.png", png, "image/png")})
        return self.call("sendPhoto", body, ctype)

    def call(self, method: str, body: bytes, ctype: str) -> tuple[bool, float | None, str]:
        req = urllib.request.Request(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}", data=body,
                                     headers={"Content-Type": ctype})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
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

    def auth_header(self, url: str | None = None) -> str:
        oauth = {"oauth_consumer_key": X_KEYS["X_API_KEY"], "oauth_nonce": secrets.token_hex(16),
                 "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": str(int(time.time())),
                 "oauth_token": X_KEYS["X_ACCESS_TOKEN"], "oauth_version": "1.0"}
        # a JSON or multipart body is not part of the signature base
        params = "&".join(f"{_pct(k)}={_pct(v)}" for k, v in sorted(oauth.items()))
        base = "&".join(["POST", _pct(url or self.URL), _pct(params)])
        key = f"{_pct(X_KEYS['X_API_SECRET'])}&{_pct(X_KEYS['X_ACCESS_SECRET'])}"
        oauth["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
        return "OAuth " + ", ".join(f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(oauth.items()))

    UPLOAD = "https://api.x.com/2/media/upload"

    def send_text(self, text: str, media_id: str | None = None) -> tuple[bool, float | None, str]:
        payload = {"text": text, **({"media": {"media_ids": [media_id]}} if media_id else {})}
        req = urllib.request.Request(self.URL, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": self.auth_header()})
        return self.call(req)

    def send_photo(self, png, r):
        body, ctype = multipart({"media_category": "tweet_image"}, {"media": ("recap.png", png, "image/png")})
        req = urllib.request.Request(self.UPLOAD, data=body,
                                     headers={"Content-Type": ctype, "Authorization": self.auth_header(self.UPLOAD)})
        ok, retry, err, reply = self.call(req, want_reply=True)
        if not ok:
            return ok, retry, "media upload " + err
        media_id = str((reply.get("data") or {}).get("id") or reply.get("media_id_string") or "")
        if not media_id:
            return False, None, "media upload: no id"
        return self.send_text(recap.caption_x(r, SITE), media_id)

    def call(self, req, want_reply=False):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                ok = 200 <= r.status < 300
                if want_reply:
                    return ok, None, "", json.load(r)
                return ok, None, ""
        except urllib.error.HTTPError as e:
            retry = None
            if e.code == 429:
                reset = e.headers.get("x-rate-limit-reset")
                retry = max(60.0, float(reset) - time.time()) if reset and reset.isdigit() else 900.0
            try:
                detail = json.load(e).get("detail", "")
            except ValueError:
                detail = ""
            res = (False, retry, f"HTTP {e.code}: {detail}")
        except (urllib.error.URLError, OSError) as e:
            res = (False, None, type(e).__name__)
        return res + ({},) if want_reply else res

    def send(self, item):
        return self.send_text(x_text(item))


# ---------------- feed and tracker data ----------------
def iso(ts: float | None) -> str:
    return datetime.fromtimestamp(ts or time.time(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atom(items: list[dict], updated: float) -> str:
    entries = []
    for it in [i for i in items if not i.get("folded")][:FEED_ITEMS]:
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
        prop = None
        if ev["kind"] == "agreed" and p and p.get("thr") == 1:
            # one vote was enough: if its "proposed" post is still waiting, post both as one
            prop = next((it for it in self.state["items"] if it["kind"] == "proposed" and it.get("id") == ev.get("id")
                         and it.get("chain") == chain[:16] and it["news"] and not it.get("folded")
                         and "ok" not in it["posted"].values()), None)
            if prop:
                ev = {**ev, "combined": True}
        d = describe(ev, p, head, pace)
        if prop:
            prop["folded"] = True
        item = {"key": key, "kind": ev["kind"], "h": ev["h"], "ts": ev.get("ts"), "seen": time.time(), "chain": chain[:16],
                "id": ev.get("id"), "thr": (p or {}).get("thr"), **d,
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
                      "quorum": now.get("quorum"), "votes_needed": now.get("thr"), "open_admission": OPEN_ADMISSION,
                      "consensus_mode": g.get("eligibility_mode") or now.get("mode")},
            "proposals": [{k: p[k] for k in ("id", "n", "title", "parts", "status", "proposer", "proposed_at", "proposed_ts",
                                              "activate_at", "approved_at", "approved_ts", "activated_at", "activated_ts",
                                              "expired_at", "expired_ts", "thr", "counted_votes", "rev", "revisions",
                                              "patch", "dups", "tx_id", "explain")}
                          | {"votes": [{"h": v["h"], "voter": v["voter"], "counted": v["counted"], "approve": v["approve"]} for v in p["votes"]]}
                          for p in reversed(props)],
            "events": [{k: it.get(k) for k in ("key", "kind", "h", "ts", "seen", "id", "headline", "body", "link", "chain")}
                       for it in [i for i in self.state["items"] if not i.get("folded")][:FEED_ITEMS]],
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
                if it.get("folded"):
                    continue
                if it["kind"] == "proposed" and it.get("thr") == 1 and time.time() - it["seen"] < PROPOSED_HOLD:
                    break  # wait: it may be agreed in a moment; keep the order of posts
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

    # ---------- testnet health ----------
    def health_now(self) -> dict | None:
        try:
            with urllib.request.urlopen(RELAY_HTTP + "/health-score", timeout=20) as r:
                return json.load(r)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            log.warning("health: cannot read /health-score (%r)", exc)
            return None

    async def maybe_health(self, now: float | None = None):
        """Post to Telegram when the testnet goes down or comes back. The new
        state must hold for HEALTH_CONFIRM seconds; between the two thresholds
        the last state stays (no flapping around one number)."""
        if not HEALTH_ON:
            return
        now = now if now is not None else time.time()
        st = self.state.setdefault("health", {})
        if now - st.get("checked", 0) < HEALTH_EVERY:
            return
        st["checked"] = now
        h = await asyncio.to_thread(self.health_now)
        if h is None or h.get("state") == "down" or h.get("score", 0) < HEALTH_DOWN_BELOW:
            seen = "down"
        elif h.get("score", 0) >= HEALTH_UP_AT:
            seen = "up"
        else:
            seen = st.get("posted") or "up"
        if h is not None:
            st["score"] = h.get("score")
        if "posted" not in st:  # first run: this is how things are, not news
            st["posted"] = seen
            self.save_state()
            return
        if seen == st["posted"]:
            st.pop("cand", None)
            self.save_state()
            return
        cand = st.get("cand")
        if not cand or cand["state"] != seen:
            st["cand"] = {"state": seen, "since": now}
            self.save_state()
            return
        if now - cand["since"] < HEALTH_CONFIRM:
            return
        text = health_text(seen, h, st.get("down_since") if seen == "up" else None, now)
        tg = [o for o in self.outlets if o.name == "telegram" and o.enabled()]
        for o in tg:
            ok, _, err = await asyncio.to_thread(o.send_text, text)
            if not ok:
                log.warning("health post to telegram failed (%s); trying again next check", err)
                return
        log.info("health: testnet %s (score %s)%s", seen, h and h.get("score"), "" if tg else ", telegram off")
        st["posted"] = seen
        st["down_since"] = cand["since"] if seen == "down" else None
        st.pop("cand", None)
        self.save_state()

    # ---------- new nodes on the network ----------
    def relay_json(self, path: str) -> dict | None:
        try:
            with urllib.request.urlopen(RELAY_HTTP + path, timeout=20) as r:
                return json.load(r)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            log.warning("newnodes: cannot read %s (%r)", path, exc)
            return None

    async def maybe_newnodes(self, now: float | None = None):
        """One Telegram post per genuinely new node (see new_nodes); nodes
        already there when this first runs are history, not news."""
        if not NEWNODE_ON:
            return
        now = now if now is not None else time.time()
        st = self.state.setdefault("newnodes", {})
        if now - st.get("checked", 0) < NEWNODE_EVERY:
            return
        st["checked"] = now
        peers, board = await asyncio.to_thread(self.relay_json, "/peers"), await asyncio.to_thread(self.relay_json, "/community/board")
        if peers is None and board is None:
            return
        known = st.setdefault("known", {})
        fresh = new_nodes(peers, board, known, now)
        if not st.get("primed"):
            for p in (peers or {}).get("peers") or []:
                known.setdefault("peer:" + p["id"], round(now))
            for n in (board or {}).get("nodes") or []:
                known.setdefault("kit:" + str(n.get("id")), round(now))
            st["primed"] = True
            self.save_state()
            return
        day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
        tg = [o for o in self.outlets if o.name == "telegram" and o.enabled()]
        for n in fresh:
            posted = st.get("day") == day and st.get("posted", 0) or 0
            if posted < NEWNODE_DAILY_CAP and tg:
                text = newnode_text(n, nodes_online(peers, board))
                for o in tg:
                    ok, _, err = await asyncio.to_thread(o.send_text, text)
                    if not ok:
                        log.warning("new node post failed (%s); trying again next check", err)
                        self.save_state()
                        return
                st["day"], st["posted"] = day, posted + 1
                log.info("newnodes: posted %s", n["key"])
            else:
                log.info("newnodes: %s recorded without a post (%s)", n["key"], "daily cap" if tg else "telegram off")
            known[n["key"]] = round(now)
        if len(known) > 5000:  # oldest first out; a key that comes back that late is not new news anyway
            for k in sorted(known, key=known.get)[:len(known) - 5000]:
                del known[k]
        self.save_state()

    # ---------- weekly recap ----------
    @staticmethod
    def recap_slot(now: float) -> float:
        """The latest scheduled recap time at or before now."""
        d = datetime.fromtimestamp(now, timezone.utc).replace(hour=RECAP_HOUR, minute=0, second=0, microsecond=0)
        d -= timedelta(days=(d.weekday() - RECAP_WEEKDAY) % 7)
        if d.timestamp() > now:
            d -= timedelta(days=7)
        return d.timestamp()

    def make_recap(self, end: float) -> tuple[dict, bytes]:
        def get(path):
            try:
                with urllib.request.urlopen(RELAY_HTTP + path, timeout=30) as r:
                    return json.load(r)
            except (urllib.error.URLError, OSError, ValueError) as exc:
                log.warning("recap: cannot read %s (%r)", path, exc)
                return None
        stats = get("/stats")
        if not stats or "blocks" not in stats:
            raise RuntimeError("relay /stats not available")
        r = recap.build(stats, get("/community"), self.state["items"], end)
        png = recap.render(r, SITE)
        d = os.path.join(PUBLIC_DIR, "recap")
        os.makedirs(d, exist_ok=True)
        name = datetime.fromtimestamp(end, timezone.utc).strftime("%Y-%m-%d") + ".png"
        for fn in (name, "latest.png"):
            tmp = os.path.join(d, fn + ".tmp")
            with open(tmp, "wb") as f:
                f.write(png)
            os.replace(tmp, os.path.join(d, fn))
        try:
            with open(os.path.join(d, "index.json")) as f:
                index = json.load(f)
        except (OSError, ValueError):
            index = []
        index = [x for x in index if x.get("file") != name]
        index.insert(0, {"file": name, "start": round(r["start"]), "end": round(r["end"]), "period": recap.period(r),
                         "lines": recap.lines(r, SITE)})
        write_atomic(os.path.join(d, "index.json"), json.dumps(index[:104], separators=(",", ":")))
        log.info("recap drawn: %s (%s)", name, recap.period(r))
        return r, png

    async def maybe_recap(self):
        if not RECAP_ON:
            return
        slot = self.recap_slot(time.time())
        st = self.state.get("recap")
        if st is None:  # first run: the first recap comes at the next slot
            self.state["recap"] = {"slot": slot, "posted": {}}
            self.save_state()
            return
        if slot > st.get("slot", 0):
            try:
                r, _ = await asyncio.to_thread(self.make_recap, slot)
            except Exception as exc:  # retried on the next poll
                log.warning("recap failed: %r", exc)
                return
            st = self.state["recap"] = {"slot": slot, "posted": {}, "r": r,
                                        "file": datetime.fromtimestamp(slot, timezone.utc).strftime("%Y-%m-%d") + ".png"}
            self.save_state()
        if "r" not in st or time.time() - st["slot"] > 86400:  # nothing drawn, or a day late: skip this week's post
            return
        for o in self.outlets:
            got = st["posted"].get(o.name)
            if not o.enabled() or got == "ok" or (isinstance(got, int) and got >= 3) or st.get("pause_until", 0) > time.time():
                continue
            try:
                with open(os.path.join(PUBLIC_DIR, "recap", st["file"]), "rb") as f:
                    png = f.read()
            except OSError:
                return
            ok, retry, err = await asyncio.to_thread(o.send_photo, png, st["r"])
            if ok:
                st["posted"][o.name] = "ok"
                log.info("recap posted to %s", o.name)
            else:
                st["posted"][o.name] = (got if isinstance(got, int) else 0) + 1
                st["pause_until"] = time.time() + (retry or 300)
                log.warning("recap post to %s failed (%s)", o.name, err)
            self.save_state()

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
                        await self.maybe_recap()
                        await self.maybe_health()
                        await self.maybe_newnodes()
                        await asyncio.sleep(POLL_SECONDS)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # relay restarting, network blip: try again shortly
                log.warning("relay connection lost (%r); retrying in 10 s", exc)
                await self.maybe_health()  # a relay that stays away is news too
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


async def preview_latest(n: int = 6) -> int:
    """Print how the newest events on the chain would be posted now; posts nothing."""
    w = Watcher([])
    async with connect(RELAY_URL, max_size=64 * 2**20, open_timeout=20) as ws:
        w.ws = ws
        await w.sync()
    props, events, now = replay(w.blocks, w.gov)
    by_id, pace = {p["id"]: p for p in props}, block_pace(w.blocks)
    if not events:
        print("No rule change on this chain yet.")
    quick = {e["id"] for e in events if e["kind"] == "agreed" and by_id.get(e["id"], {}).get("thr") == 1 and pace
             and (e["h"] - by_id[e["id"]]["proposed_at"]) * pace <= PROPOSED_HOLD}
    events = [{**e, "combined": True} if e["kind"] == "agreed" and e["id"] in quick else e
              for e in events if not (e["kind"] == "proposed" and e["id"] in quick)]
    for ev in events[-n:]:
        print(telegram_text({"kind": ev["kind"], **describe(ev, by_id.get(ev["id"]), now.get("head", 0), pace)}))
        print("-" * 60)
    return 0


def recap_cli(post: bool) -> int:
    """Draw the recap of the 7 days up to now; post it too with post=True."""
    w = Watcher()
    try:
        r, png = w.make_recap(time.time())
    except Exception as exc:
        print(f"recap: FAILED {exc}")
        return 1
    print("recap drawn: https://" + FEED_URL.split("//", 1)[-1].split("/", 1)[0] + "/recap/latest.png")
    print("\n".join("  " + x for x in recap.lines(r, SITE)))
    code = 0
    if post:
        for o in (Telegram(), X()):
            if not o.enabled():
                print(f"{o.name}: off (credentials not set in .env)")
                continue
            ok, _, err = o.send_photo(png, r)
            print(f"{o.name}: {'sent' if ok else 'FAILED ' + err}")
            code |= 0 if ok else 1
    return code


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if "--test" in sys.argv:
        sys.exit(send_test())
    if "--preview" in sys.argv:
        sys.exit(asyncio.run(preview_latest()))
    if "--recap-now" in sys.argv or "--recap-preview" in sys.argv:
        sys.exit(recap_cli("--recap-now" in sys.argv))
    asyncio.run(Watcher().run())

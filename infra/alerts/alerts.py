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

It also posts findings (findings.py): unusual things our read node sees on
the real chain, such as no new blocks, the bootnode gone, ghost transactions
(IDNI #81), a reorg, our node falling behind or the same proposal again and again. One post when an incident
starts, one when it is over, never repeated; a busy stretch is collected and
posted once afterwards instead of one by one.

Nothing is posted for what the watcher finds on its very first run, and
nothing whose block is older than POST_MAX_AGE_SECONDS, so a fresh volume or
a long outage never floods the channel with old news.

It also announces changes to Tau HUD itself, read from the site's own update
log (assets/updates.json): an entry with a "major" field gets a post of its
own (at most SITE_MAJOR_DAILY_CAP a day, SITE_MAJOR_GAP_SECONDS apart, only
between SITE_POST_HOURS UTC); every other entry waits and goes into one
digest post of the smaller changes at SITE_DIGEST_HOURS UTC, once enough
have gathered. The first run only remembers what is already in the log,
except majors from the last SITE_MAJOR_MAX_AGE_DAYS days, which are queued.

Practice votes (proposals that only repeat the rules in force) get no post
of their own; one evening summary, "Testnet today" at TESTNET_TODAY_HOUR UTC,
counts them with the day's blocks, transactions and rule changes, and is
skipped on a quiet day.

Once a week (Monday 09:00 German time by default) it also posts a recap image of the
week (recap.py) and keeps a copy at https://node.tauhud.com/recap/latest.png.
At the same time it writes that week's edition of The Daily Consensus, the
site's newspaper (gazette.py), to /recap/gazette/latest.json; the first one is
written as soon as the service starts. For it, the visitors' day in the
simulation (votes, their own proposals, the best forecaster) is noted every
ten minutes, because the relay starts those over at midnight UTC.

  python alerts.py                  run the watcher
  python alerts.py --test           send one test post to each configured channel
  python alerts.py --preview        print how the newest rule changes would be posted, post nothing
  python alerts.py --recap-preview  draw this week's recap and save it, post nothing
  python alerts.py --recap-now      draw the recap and post it to each configured channel
  python alerts.py --gazette-now    write this week's newspaper edition now (same number if one is already out today)
  python alerts.py --gazette-reprint  print the latest edition again with the current wording (same number, date and week)
  python alerts.py --sim-preview    print today's two simulation posts (the consensus switches), post nothing
  python alerts.py --today-preview  print the "Testnet today" summary as it stands now, post nothing
  python alerts.py --site-preview   print the site-update posts waiting in assets/updates.json, post nothing
  python alerts.py --findings-preview  print what the finding detectors see now and every kind of finding post, post nothing
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
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape as xml_escape

from websockets.asyncio.client import connect

import explain
import findings
import gazette
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
# X (@TauHUDcom) is paid per post since 2026: $0.015 a post, $0.20 for one with a link in it. So X gets the real chain's news
# (rule changes, new nodes, "Testnet today", new pages, the weekly recap with the paper's headline), each in a short text
# without a link (the profile carries tauhud.com), and never more than X_DAILY_CAP / X_MONTHLY_CAP posts. Not on X: practice
# votes, the smaller-updates digests, health alarms, visitor proposals; the simulation's switches only with X_SIM=true.
# Findings (findings.py) go to X only for real-chain incidents (no blocks reaching us, no peers, a reorg, a busy stretch),
# at most FINDINGS_X_DAILY_CAP a day.
X_LINKS = os.environ.get("X_LINKS", "false").lower() in ("1", "true", "yes")
X_DAILY_CAP = int(os.environ.get("X_DAILY_CAP", 8))
X_MONTHLY_CAP = int(os.environ.get("X_MONTHLY_CAP", 120))
X_SIM = os.environ.get("X_SIM", "false").lower() in ("1", "true", "yes")
# A picture under the X post where one fits: the rule change's card and the live overview from the share service (share/),
# a new page's own preview picture. Uploading it costs nothing extra; a picture that cannot be had leaves the text alone.
X_PICTURES = os.environ.get("X_PICTURES", "true").lower() in ("1", "true", "yes")
SHARE_HTTP = os.environ.get("SHARE_HTTP", "http://share:8070").rstrip("/")
RELAY_HTTP = os.environ.get("RELAY_HTTP", "http://relay:8080")
RECAP_ON = os.environ.get("RECAP_ENABLED", "true").lower() in ("1", "true", "yes")
RECAP_WEEKDAY = int(os.environ.get("RECAP_WEEKDAY", 0))   # 0 = Monday
RECAP_HOUR = int(os.environ.get("RECAP_HOUR", 9))         # local time in RECAP_TZ
RECAP_TZ = ZoneInfo(os.environ.get("RECAP_TZ", "Europe/Berlin"))   # 09:00 in Germany, summer and winter
# The weekly paper comes out for each language at RECAP_HOUR on RECAP_WEEKDAY in its readers' own time: Japanese first
# (09:00 Tokyo), then Chinese (09:00 Beijing), then English (09:00 German time). It is printed once, at the first drop;
# each language's page shows it from its own drop and the edition before until then.
DROP_TZ = {"ja": ZoneInfo("Asia/Tokyo"), "zh": ZoneInfo("Asia/Shanghai"), "en": RECAP_TZ}
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
# Simulation mode on the site runs a made-up chain in the visitor's browser (assets/sim.js), the same for everyone because it is
# generated from the clock, with a fixed day programme. Only its two consensus switches are announced here, each when its proposal
# appears, 10 minutes before it is in force; the channel reports the real testnet, so these posts are rare and marked as simulated.
# SIM_SWITCHES must equal STAKE_SLOT / FIXED_SLOT in assets/sim.js (slot k = proposed at k:20 UTC, in force at k:30 UTC).
SIM_ON = os.environ.get("SIM_ALERTS", "true").lower() in ("1", "true", "yes")
SIM_SWITCHES = (("stake", 10), ("fixed", 16))
SIM_PROPOSED_AT, SIM_IN_FORCE_AT = 20 * 60, 30 * 60
SIM_LINK = f"{SITE}/proposals/?mode=sim"
# Changes to Tau HUD itself, from the update log every release appends to. Mark an entry as worth its own post with
#   "major": {"id": "unique-slug", "title": "…", "text": "one or two plain sentences", "link": "/page/"}
# plus "image": "/assets/shots/<id>.png", a 16:9 screenshot (PNG or JPEG, at most 5 MB) that goes under the X post,
# and add "skip": "why" to a major that must not be posted (already announced by hand); it also leaves the queue.
# (text and link are optional: the entry's first two sentences and the home page). Everything else is bundled into a digest.
SITE_ON = os.environ.get("SITE_UPDATES", "true").lower() in ("1", "true", "yes")
SITE_UPDATES_URL = os.environ.get("SITE_UPDATES_URL", f"{SITE}/assets/updates.json")
SITE_EVERY = float(os.environ.get("SITE_UPDATES_POLL_SECONDS", 600))
SITE_MAJOR_DAILY_CAP = int(os.environ.get("SITE_MAJOR_DAILY_CAP", 3))
SITE_MAJOR_GAP = float(os.environ.get("SITE_MAJOR_GAP_SECONDS", 2 * 3600))
SITE_MAJOR_MAX_AGE_DAYS = int(os.environ.get("SITE_MAJOR_MAX_AGE_DAYS", 3))
SITE_POST_HOURS = tuple(int(x) for x in os.environ.get("SITE_POST_HOURS", "6-23").split("-"))  # UTC, start included, end not
SITE_DIGEST_HOURS = tuple(int(x) for x in os.environ.get("SITE_DIGEST_HOURS", "12,18").split(","))   # UTC
SITE_DIGEST_MIN = int(os.environ.get("SITE_DIGEST_MIN", 3))       # fewer smaller changes wait for the next day…
SITE_DIGEST_MAX_WAIT = float(os.environ.get("SITE_DIGEST_MAX_WAIT_DAYS", 7)) * 86400  # …but not longer than this
SITE_DIGEST_LINES = 8
SITE_CATCHUP_AT = int(os.environ.get("SITE_CATCHUP_AT", 4))  # this many majors waiting: one catch-up post with all of them
SITE_LOG_LINK = f"{SITE}/#updates"
# "Testnet today": one evening summary of the real chain's last 24 hours, only on a day with something to report.
# Practice votes (the rules in force proposed again) appear here instead of in posts of their own.
TODAY_ON = os.environ.get("TESTNET_TODAY", "true").lower() in ("1", "true", "yes")
TODAY_HOUR = int(os.environ.get("TESTNET_TODAY_HOUR", 19))   # UTC
# Visitors may propose a rule change to the simulation from the Playground and vote on it (relay/simprops.py, relay/simvotes.py).
# The channel hears only about the ones visitors voted in, with at least VISITOR_MIN_VOTES votes, at most VISITOR_DAILY_CAP a day.
VISITOR_MIN_VOTES = int(os.environ.get("SIM_VISITOR_MIN_VOTES", 3))
VISITOR_DAILY_CAP = int(os.environ.get("SIM_VISITOR_DAILY_CAP", 3))
VISITOR_EVERY = float(os.environ.get("SIM_VISITOR_POLL_SECONDS", 60))
PREDICT_LINK = f"{SITE}/?mode=sim#predict"   # the forecast sheet on the HUD (assets/predict.js)
FEED_ITEMS = 100
RANGE = 100           # relay's getblockrange maximum
REFETCH_TAIL = 6      # blocks re-read every poll so a replaced tip block (reorg) is noticed
MAX_TRIES = 8
# While one yes vote is enough (one validator), a proposal is usually agreed a block or two later.
# Its "proposed" post waits this long; if it is agreed meanwhile, one combined post goes out instead of two.
PROPOSED_HOLD = float(os.environ.get("PROPOSED_HOLD_SECONDS", 600))
# The same headline (same kind, same rule change) posted again within this window gets no post of its own.
REPEAT_WINDOW = float(os.environ.get("REPEAT_WINDOW_SECONDS", 6 * 3600))
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
        headline = f"Agreed: {title}"
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
REAL_LINE = recap.REAL_LINE
ICONS = {"proposed": "🗳️", "agreed": "✅", "active": "⚡", "dropped": "❌", "restart": "🔄"}


def telegram_text(item: dict) -> str:
    """Lead with the change and when it applies, then why it matters; block numbers, voters, the proposer's own title and
    the rule diff go into a folded part at the end (Telegram opens it with a tap)."""
    e = html.escape
    if "facts" not in item:  # posts recorded before explanations existed
        return (f"{REAL_LINE}\n{ICONS.get(item['kind'], '•')} <b>{e(item['headline'])}</b>\n{e(item['body'])}\n\n"
                f"<a href=\"{e(item['link'])}\">Open in Tau HUD</a>")
    out = [REAL_LINE, f"{ICONS.get(item['kind'], '•')} <b>{e(item['headline'])}</b>"]
    facts = list(item["facts"])
    if facts and item["kind"] != "restart":
        out.append(e(facts.pop(0)))  # when it applies, or what it still needs
    if item.get("why"):
        warn = "⚠️ " if item.get("severity") in ("halt", "unsafe") else ""
        out += ["", f"<b>{e(item.get('why_title', 'Why it matters'))}</b>", warn + e(item["why"])]
    if len(item["what"]) > 1:  # one change is already the headline
        out += ["", f"<b>{e(item.get('what_title', 'What changes'))}</b>"] + [f"• {e(w)}" for w in item["what"]]
    if item["kind"] == "restart":
        out += [""] + [e(f) for f in facts]
        facts = []
    details = []
    if item.get("label"):
        details.append(f"Proposer's title: “{e(item['label'])}”")
    details += [e(f) for f in facts]
    d = item.get("diff")
    if d:  # Telegram has no colours: + and − carry the meaning
        if d["lines"]:
            details.append(f"Rule text diff ({e(d['summary'])}):")
            details += [f"<code>{e(('+ ' if op == '+' else '- ') + t.strip())}</code>" for op, t in d["lines"]]
            if d["more"]:
                details.append(f"… {d['more']} more lines on the page")
        else:
            details.append("Rule text diff: none. The text equals the rules in force.")
    if details:
        out += ["", "<blockquote expandable>" + "\n".join(["<b>Details</b>"] + details) + "</blockquote>"]
    label = "Open in Tau HUD" if item["kind"] == "restart" else "Watch it on Tau HUD"
    out += ["", f"<a href=\"{e(item['link'])}\">{label}</a>"]
    return "\n".join(out)


# An X post: the headline first, a blank line, the text (list lines stay together), a blank line, then one quiet
# line that says where it comes from, with the hashtag. Simulation posts also open with their marker line.
X_REAL = "⛓ Live from Tau Testnet Alpha"
X_SIM_LINE = "🧪 SIMULATION · not the real testnet"
X_SIM_FOOT = "🧪 Simulation, not the real testnet"
X_SITE_NOTE = "✨ Tau HUD website update, not testnet news"
X_TAG = "#TauNet"
# Every X post carries these two, once, at the very end after the source line (29 Oct 2026); never more tags.
X_MUST = ("#TauNet", "$AGRS")


def x_len(s: str) -> int:
    """Length as X counts it: a link is 23, most Latin text 1 a character, emoji and Chinese 2."""
    s = re.sub(r"https?://\S+", "x" * 23, s)
    return sum(1 if (o := ord(c)) <= 0x10FF or 0x2000 <= o <= 0x200D or 0x2010 <= o <= 0x201F or 0x2032 <= o <= 0x2037 else 2
               for c in s)


def x_join(lines: list[str]) -> str:
    out = ""
    for i, x in enumerate(lines):
        out += x if i == 0 else ("\n" if x.startswith("• ") and lines[i - 1].startswith("• ") else "\n\n") + x
    return out


def x_post(lines: list[str], link: str | None = None, keep: int = 1, foot: str = X_REAL, tag: str = X_TAG) -> str:
    """Lines as one post of at most 280 (first line the headline): the last line loses sentences, then whole lines go
    (never the first `keep`), then it is cut. `foot` and the hashtag always close it; the link joins them only with
    X_LINKS (it makes a post 13 times dearer)."""
    tag = " ".join([tag] + [t for t in X_MUST if t not in (tag or "").split()]).strip()
    tail = "\n\n" + " · ".join(x for x in (foot, link if link and X_LINKS else None, tag) if x)
    out = [" ".join(str(x).split()) for x in lines if x and str(x).strip()]
    if not X_LINKS:
        out = [re.sub(r"\s*https?://\S+", "", x) for x in out]
    while out and x_len(x_join(out) + tail) > 280:
        n = len(re.split(r"(?<=[.!?])\s+(?=[A-Z“\"(])", out[-1]))
        if n > 1:
            out[-1] = sentences(out[-1], n - 1)
        elif len(out) > keep:
            out.pop()
        else:
            text = x_join(out)
            while text and x_len(text + "…" + tail) > 280:
                text = text[:-1]
            out = [text.rstrip(" ,;:.\n") + "…"]
    return x_join(out) + tail


def x_text(item: dict) -> str:
    """A rule change on the real chain: the line that says so, the headline, then why it matters as far as it fits."""
    icon = ICONS.get(item["kind"], "•")
    return x_post([f"{icon} {item['headline']}", item.get("why") or item.get("body")], item.get("link"))


def recap_x(r: dict) -> str:
    """The Monday recap picture's text on X: the week in three lines, and the headline of this week's paper."""
    try:
        with open(os.path.join(PUBLIC_DIR, "recap", "gazette", "latest.json")) as f:
            banner = (json.load(f).get("banner") or {}).get("en")
    except (OSError, ValueError, AttributeError):
        banner = None
    return x_post([f"📊 Tau testnet weekly recap · {recap.period(r)}"] + [f"• {x}" for x in recap.lines(r, SITE)[:3]]
                  + ([f"📰 This week's paper: {banner}"] if banner else []), f"{SITE}/stats/")


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
            return (f"{REAL_LINE}\n🔴 <b>Tau testnet: no data</b>\nOur relay does not answer, so we cannot tell whether the testnet runs. "
                    f"We are on it.\n\n{link}")
        lines = [REAL_LINE, f"🔴 <b>Tau testnet health {h['score']}/100: {e(h['label'])}</b>"]
        lines += [f"• {e(p)}" for p in health_problems(h)]
        return "\n".join(lines + ["", "We post again when it recovers.", link])
    lines = [REAL_LINE, f"🟢 <b>Tau testnet recovered: health {h['score']}/100</b>"]
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
    return "\n".join([REAL_LINE, head, body, f"Nodes online now: {online}.", "", link])


def newnode_x(n: dict, online: int) -> str:
    if n["kind"] == "kit":
        head = f"🆕 New community node: {n['name']}"
        body = f"Someone started a Tau testnet node with the Tau HUD kit and it has checked every block for {fmt_dur(n['for'])}."
    else:
        head = "🆕 A new node joined the Tau testnet"
        body = f"Our node has seen it for {fmt_dur(n['for'])}" + (f", at block #{fmt_n(n['head'])}" if n.get("head") else "") + "."
    return x_post([head, f"{body} Nodes online now: {online}."], f"{SITE}/nodes/")


# ---------- the simulation's consensus switches ----------
def sim_switches(t: float) -> list[dict]:
    """The simulated consensus switches of the UTC day that holds `t`, in order: when each is proposed, in force, and when the other one follows."""
    d0 = int(t // 86400) * 86400
    day = datetime.fromtimestamp(d0, timezone.utc).strftime("%Y-%m-%d")
    out = []
    for i, (kind, hour) in enumerate(SIM_SWITCHES):
        other = SIM_SWITCHES[(i + 1) % len(SIM_SWITCHES)]
        out.append({"kind": kind, "key": f"{day}:{kind}", "proposed": d0 + hour * 3600 + SIM_PROPOSED_AT, "in_force": d0 + hour * 3600 + SIM_IN_FORCE_AT,
                    "next": d0 + other[1] * 3600 + SIM_IN_FORCE_AT + (86400 if other[1] <= hour else 0)})
    return out


SIM_WORDS = {  # the same words as the simulation badge on the site: what happens, why it matters, where to watch it
    "stake": {"headline": "In 10 minutes the simulated chain switches to proof of stake",
              "why": ("The chain changes how it picks who seals blocks: the six richest accounts take over from the fixed validator list. "
                      "Tau treats a consensus switch like any other rule change: proposed, voted on by the validators, then in force."),
              "watch": ["Proposals: the simulated validators vote, then the switch takes effect at {in_force} UTC",
                        "Chain core on the HUD: the proposer changes from the validator list to the richest accounts"],
              "after": "the fixed validator list returns at {next} UTC"},
    "fixed": {"headline": "In 10 minutes the simulated chain returns to its fixed validator list",
              "why": ("The chain goes back to a fixed validator list: a known set seals blocks again instead of the richest accounts. "
                      "Tau treats a consensus switch like any other rule change: proposed, voted on by the validators, then in force."),
              "watch": ["Proposals: the simulated validators vote, then the switch takes effect at {in_force} UTC",
                        "Chain core on the HUD: the validator ring seals the blocks again"],
              "after": "proof of stake takes over again at {next} UTC"},
}
SIM_NOTICE = ("Simulated: a made-up chain generated in your browser from the clock, the same on every page of Tau HUD. "
              "Nothing here happens on the real Tau testnet.")


SIM_BALLOT_SECONDS = 420  # visitors vote until 7 minutes after the proposal (sim.js BALLOT_SECONDS, relay/simvotes.py)


def forecast_lines(ev: dict, today: dict | None, yesterday: dict | None) -> list[str]:
    """The visitors' forecasts under a simulation post (relay /sim/predictions, infra/relay/simpredict.py): yesterday's best
    in the morning post, today's leaders in the afternoon one, and when the next round closes. Names are the anonymous
    two-word names of the simulation; nothing else about anyone is known."""
    e = html.escape
    top = lambda rows: " · ".join(f"{i + 1}. {e(r.get('name') or 'Anonymous')} {r['points']}" for i, r in enumerate(rows[:3]))  # noqa: E731
    out = []
    if ev["kind"] == "stake" and yesterday and yesterday.get("board"):
        out.append(f"Yesterday's best forecasters: {top(yesterday['board'])}")
    if today and today.get("board"):
        out.append(f"Leading today: {top(today['board'])} ({today.get('forecasters', 0)} playing)")
    nxt = datetime.fromtimestamp(ev["proposed"] + 3600, timezone.utc).strftime("%H:%M")
    out.append(f"Next round: the visitors vote at {nxt} UTC. Guess before then whether the change comes and how many vote.")
    return ["", "🎯 <b>Forecasts</b>"] + out + [f"<a href=\"{e(PREDICT_LINK)}\">Guess the next round</a>"]


def forecasts_for(ev: dict) -> list[str]:
    """The forecast lines for a simulation post; none when the relay does not answer (the post goes out without them)."""
    try:
        with urllib.request.urlopen(RELAY_HTTP + "/sim/predictions", timeout=10) as r:
            today = json.loads(r.read())
    except (urllib.error.URLError, OSError, ValueError):
        return []
    return forecast_lines(ev, today, today.get("yesterday") if ev["kind"] == "stake" else None)


def sim_text(ev: dict, forecast: list[str] | None = None) -> str:
    """The Telegram post for a simulated consensus switch: marked as simulation first and last, then why, what to watch, the times."""
    e = html.escape
    hm = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%H:%M")  # noqa: E731
    w = SIM_WORDS[ev["kind"]]
    f = {"proposed": hm(ev["proposed"]), "in_force": hm(ev["in_force"]), "next": hm(ev["next"])}
    out = ["🧪 <b>SIMULATION · not the real testnet</b>", f"<b>{e(w['headline'])}</b>",
           "", "<b>Why it matters</b>", e(w["why"]),
           "", "<b>What to watch</b>"] + [f"• {e(x.format(**f))}" for x in w["watch"]] + [
           "", e(f"Proposed {f['proposed']} UTC · in force {f['in_force']} UTC · {w['after'].format(**f)}"),
           "", "<b>You decide</b>", e(f"Vote yes or no on tauhud.com until {hm(ev['proposed'] + SIM_BALLOT_SECONDS)} UTC: the simulated validators follow the visitors' majority. More no than yes, and the switch is dropped."),
           ] + (forecast or []) + [
           "", f"<i>{e(SIM_NOTICE)}</i>",
           "", f"<a href=\"{e(SIM_LINK)}\">Watch it in the simulation</a>"]
    return "\n".join(out)


def sim_x(ev: dict) -> str:
    """Only with X_SIM: the switch, marked as simulation first and last."""
    w, hm = SIM_WORDS[ev["kind"]], datetime.fromtimestamp(ev["in_force"], timezone.utc).strftime("%H:%M")
    return x_post([X_SIM_LINE, w["headline"], f"In force at {hm} UTC unless the visitors vote no.", w["why"]], SIM_LINK, keep=3,
                  foot=X_SIM_FOOT)


def sim_buttons() -> dict:
    """One button under a simulation post: it opens the site in Simulation mode (the real-testnet buttons would mislead here)."""
    return {"inline_keyboard": [[{"text": "🧪 Watch the simulation", "url": SIM_LINK}]]}


# ---------- "Testnet today" ----------
def is_practice(it: dict) -> bool:
    """The rules in force proposed again (nothing changes). Items stored before the flag existed still carry the title."""
    return bool(it.get("practice") or (it.get("kind") != "restart" and (it.get("severity") == "none"
                                                                      or "(no real change)" in str(it.get("headline") or ""))))


def grouped(lines: list[str]) -> list[str]:
    """Identical lines once, with how often: "3× Agreed: …" instead of three equal lines; first-seen order kept."""
    count: dict[str, int] = {}
    for x in lines:
        count[x] = count.get(x, 0) + 1
    return [f"{n}× {x}" if n > 1 else x for x, n in count.items()]


def practice_meaning(n: int, proposers: list[str]) -> str:
    """What a day's practice votes most likely were, from who proposed them."""
    if not proposers:
        return "probably people trying the Vote page"
    top = max(proposers.count(a) for a in set(proposers))
    k = len(set(proposers))
    if k == 1 and n >= 3:
        return "all from one account, which looks like a script or someone testing the vote flow"
    if top >= 3 and top * 2 > n:
        return f"{top} of them from one account, which looks like someone testing the vote flow"
    return f"from {plural(k, 'account')}, probably people trying the Vote page"


def today_numbers(stats: dict | None, items: list[dict], props: list[dict], online: int | None, end: float) -> dict:
    """The real chain's last 24 hours up to `end`: blocks, pace, transactions, practice votes, rule events, what comes next."""
    start = end - 86400
    f = {k: i for i, k in enumerate((stats or {}).get("fields") or [])}
    rows = [r for r in (stats or {}).get("blocks") or [] if "timestamp" in f and r[f["timestamp"]] and start <= r[f["timestamp"]] < end]
    ts = sorted(r[f["timestamp"]] for r in rows)
    gaps = sorted(b - a for a, b in zip(ts, ts[1:]) if b > a)
    senders = {x for r in rows for x in r[f["senders"]]} if "senders" in f else set()
    recent = [it for it in items if start <= (it.get("seen") or 0) < end and not it.get("folded")]
    practice = {it.get("id") for it in recent if is_practice(it)}
    events = grouped([it["headline"] for it in reversed(recent) if not is_practice(it) and it["kind"] in ("agreed", "active", "dropped", "restart")])
    by_id = {p.get("id"): p for p in props}
    proposers = [by_id[i]["proposer"] for i in practice if i in by_id and by_id[i].get("proposer")]
    head = (stats or {}).get("head") or 0
    pace = gaps[len(gaps) // 2] if gaps else None
    coming = [{"title": p["title"], "at": p["activate_at"], "eta": eta_txt(p["activate_at"] - head, pace) if head else ""}
              for p in props if p.get("approved_at") is not None and p.get("activated_at") is None and p.get("expired_at") is None
              and (p.get("explain") or {}).get("severity") != "none"]
    return {"end": end, "blocks": len(rows), "pace": pace, "txs": sum(r[f["txs"]] for r in rows) if "txs" in f else 0,
            "senders": len(senders), "practice": len(practice), "practice_why": practice_meaning(len(practice), proposers),
            "events": events, "online": online,
            "coming": sorted(coming, key=lambda c: c["at"])[:2]}


def today_worth_posting(r: dict) -> bool:
    return bool(r["txs"] or r["practice"] or r["events"])


def today_text(r: dict) -> str:
    e = html.escape
    day = datetime.fromtimestamp(r["end"], timezone.utc)
    out = [REAL_LINE, f"📋 <b>Testnet today, {day.day} {day.strftime('%B')}</b>", ""]
    pace = f", one every {round(r['pace'])} seconds" if r["pace"] else ""
    out.append(f"• {plural(r['blocks'], 'block')}{pace}")
    if r["txs"]:
        out.append(f"• {plural(r['txs'], 'transaction')} from {plural(r['senders'], 'account')}")
    for h in r["events"]:
        out.append(f"• {e(h)}")
    if r["practice"]:
        n = r["practice"]
        out.append(f"• {plural(n, 'practice vote')}: the rules in force were proposed again and agreed, so nothing changes"
                   + (f"; {e(r['practice_why'])}." if n > 1 and r.get("practice_why") else ".") + " You can try it on the Vote page.")
    if r["online"]:
        out.append(f"• {plural(r['online'], 'node')} online")
    for c in r["coming"]:
        out += ["", f"Coming up: {e(c['title'])} at block #{fmt_n(c['at'])}{e(c['eta'])}."]
    return "\n".join(out)


def today_x(r: dict) -> str:
    day = datetime.fromtimestamp(r["end"], timezone.utc)
    pace = f", one every {round(r['pace'])} seconds" if r["pace"] else ""
    out = [f"📋 Testnet today, {day.day} {day.strftime('%B')}", f"• {plural(r['blocks'], 'block')}{pace}"]
    if r["txs"]:
        out.append(f"• {plural(r['txs'], 'transaction')} from {plural(r['senders'], 'account')}")
    out += [f"• {h}" for h in r["events"]]
    if r["practice"]:
        out.append(f"• {plural(r['practice'], 'practice vote')}, the rules stay as they are")
    if r["online"]:
        out.append(f"• {plural(r['online'], 'node')} online")
    out += [f"Coming up: {c['title']} at block #{fmt_n(c['at'])}{c['eta']}." for c in r["coming"][:1]]
    return x_post(out, f"{SITE}/", keep=2)


def today_buttons() -> dict:
    return {"inline_keyboard": [[{"text": "⛓ Open the HUD", "url": f"{SITE}/"}, {"text": "🗳 How to vote", "url": f"{SITE}/vote/"}]]}


# ---------- changes to Tau HUD itself ----------
SITE_LINE = "✨ <b>TAU HUD · new on the site</b>"
DIGEST_LINE = "🛠 <b>TAU HUD · smaller site updates</b>"
SITE_NOTICE = "An update to the Tau HUD website, not news from the testnet."


def plain(h: str) -> str:
    """An update-log entry as plain text: tags dropped, entities resolved, spaces collapsed."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", h or "")).split())


def sentences(t: str, n: int) -> str:
    """The first n sentences of t."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z“\"(])", t)
    return " ".join(parts[:n])


def site_area(e: dict) -> str:
    tag = str(e.get("tag") or "").strip()
    return "HUD" if re.fullmatch(r"v\d+(\.\d+)*", tag) else (tag or "Tau HUD")


def site_key(e: dict) -> str:
    """Stable enough to never post an entry twice: date, tag and the start of its text (a later typo fix further on keeps it)."""
    m = e.get("major") if isinstance(e.get("major"), dict) else None
    if m and m.get("id"):
        return "major:" + str(m["id"])
    return f"{e.get('on')}|{e.get('tag')}|{plain(e.get('html'))[:60]}"


def site_link(link: str | None) -> str:
    if not link:
        return SITE + "/"
    return link if link.startswith("http") else SITE + "/" + link.lstrip("/")


def major_item(e: dict) -> dict:
    m = e["major"]
    return {"title": str(m.get("title") or site_area(e)), "text": str(m.get("text") or sentences(plain(e.get("html")), 2)),
            "link": site_link(m.get("link")), "on": e.get("on"), **({"image": site_link(m["image"])} if m.get("image") else {}),
            **({"x": False} if m.get("x") is False else {}),
            **({"lines": [{"label": str(l.get("label", "")), "text": str(l.get("text", "")), "link": site_link(l.get("link")),
                           "x": str(l.get("x") or l.get("label", ""))} for l in m["lines"] if isinstance(l, dict)]}
               if isinstance(m.get("lines"), list) else {})}


def digest_item(e: dict) -> dict:
    """One line of the digest: the area and the entry's first sentence, without the area repeated in front."""
    area, first = site_area(e), sentences(plain(e.get("html")), 1)
    if first.lower().startswith(area.lower() + ":"):
        first = first[len(area) + 1:].strip()
        first = first[:1].upper() + first[1:]
    return {"area": area, "line": first, "on": e.get("on")}


def major_text(m: dict) -> str:
    """A major's channel post; a round-up ("lines" in the log) lists each change with its link instead of one text."""
    e = html.escape
    if m.get("lines"):
        body = [e(m["text"]), ""] if m.get("text") else []
        body += [f"• <a href=\"{e(l['link'])}\">{e(l['label'])}</a>: {e(l['text'])}" for l in m["lines"]] + [""]
        return "\n".join([SITE_LINE, f"<b>{e(m['title'])}</b>", ""] + body
                         + [f"<a href=\"{e(SITE_LOG_LINK)}\">Every change in the Updates log</a>", "", f"<i>{e(SITE_NOTICE)}</i>"])
    return "\n".join([SITE_LINE, f"<b>{e(m['title'])}</b>", "", e(m["text"]), "",
                      f"<a href=\"{e(m['link'])}\">Open it on {e(link_host(m['link']))}</a>", "", f"<i>{e(SITE_NOTICE)}</i>"])


def link_host(link: str) -> str:
    """Where a link goes, as people say it: tauhud.com, or another site the log points at (agorzilla.com)."""
    host = urllib.parse.urlsplit(link).hostname or ""
    return host.removeprefix("www.") or "tauhud.com"


def major_x(m: dict) -> str:
    if m.get("lines"):  # a round-up: the title and one short line per change, as many as fit
        return x_post([m["title"]] + [f"• {l['x']}" for l in m["lines"]], m["link"], foot=X_SITE_NOTE)
    t = re.sub(r"^New:\s*", "", m["title"])
    return x_post([f"New on Tau HUD: {t[:1].upper() + t[1:]}", m["text"]], m["link"], foot=X_SITE_NOTE)


def catchup_x(majors: list[dict]) -> str:
    """One X post for a backlog: the new pages by name, as many as fit."""
    names = [re.sub(r"^New:\s*", "", m["title"]) for m in majors]
    head = f"{plural(len(majors), 'new page or feature', 'new pages and features')} on Tau HUD"
    return x_post([head] + [f"• {n[:1].upper() + n[1:]}" for n in names], SITE_LOG_LINK, foot=X_SITE_NOTE)


def major_buttons(m: dict) -> dict:
    return {"inline_keyboard": [[{"text": "✨ Open it", "url": m["link"]}, {"text": "📜 All updates", "url": SITE_LOG_LINK}]]}


def digest_text(items: list[dict], lines: int = SITE_DIGEST_LINES) -> str:
    """The digest of smaller changes, oldest first; more than `lines` are counted, not listed."""
    e = html.escape
    shown, rest = items[:lines], len(items) - lines
    since = min((i.get("on") or "" for i in items), default="")
    head = f"<b>{plural(len(items), 'smaller change')} to Tau HUD" + (f" since {e(since)}" if since else "") + "</b>"
    out = [DIGEST_LINE, head, ""] + [f"• <b>{e(i['area'])}</b>: {e(i['line'])}" for i in shown]
    if rest > 0:
        out.append(f"…and {plural(rest, 'more change')} in the Updates log.")
    out += ["", f"<a href=\"{e(SITE_LOG_LINK)}\">Read every change in the Updates log</a>", "", f"<i>{e(SITE_NOTICE)}</i>"]
    text = "\n".join(out)
    if len(text) > 3900 and lines > 1:  # Telegram's limit is 4096 characters
        return digest_text(items, lines - 1)
    return text


def catchup_text(majors: list[dict]) -> str:
    """One post for a backlog of new pages and features: a line and a link each, oldest first."""
    e = html.escape
    since = min((m.get("on") or "" for m in majors), default="")
    out = [SITE_LINE, f"<b>{plural(len(majors), 'new page or feature', 'new pages and features')} on Tau HUD"
           + (f" since {e(since)}" if since else "") + "</b>", ""]
    for m in majors:
        t = re.sub(r"^New:\s*", "", m["title"])
        out.append(f"• <a href=\"{e(m['link'])}\">{e(t[:1].upper() + t[1:])}</a>")
    out += ["", f"<a href=\"{e(SITE_LOG_LINK)}\">Every change in the Updates log</a>", "", f"<i>{e(SITE_NOTICE)}</i>"]
    text = "\n".join(out)
    return text if len(text) <= 4000 or len(majors) <= 1 else catchup_text(majors[:-1])


def digest_buttons() -> dict:
    return {"inline_keyboard": [[{"text": "📜 Updates log", "url": SITE_LOG_LINK}]]}


def in_post_hours(t: float) -> bool:
    h = datetime.fromtimestamp(t, timezone.utc).hour
    return SITE_POST_HOURS[0] <= h < SITE_POST_HOURS[1]


# ---------- rule changes visitors voted into the simulation ----------
QUORUM_WORDS = {"majority": "more than half", "supermajority": "two thirds"}


def visitor_title(meta: dict) -> str:
    """A visitor proposal in a few words, from its fixed kind and value (no free text: relay/simprops.py)."""
    k, v = meta.get("kind"), meta.get("value")
    if k == "fee":
        return f"Base fee → {v} AGRS per transaction"
    if k == "add":
        return "A new validator is admitted"
    if k == "remove":
        return f"Validator {v}… is removed"
    if k == "quorum":
        return f"Agreement threshold → {QUORUM_WORDS.get(v, v)} of the validators"
    if k == "mode":
        return "Switch consensus to proof of stake" if v == "stake" else "Back to the fixed validator list"
    return "A visitor's own network rule"


def visitor_ready(votes: dict, now: float) -> list[dict]:
    """Visitor proposals whose vote has closed with more yes than no and enough votes, and that are not in force yet."""
    out = []
    for item_id, it in (votes.get("items") or {}).items():
        meta = it.get("meta") or {}
        yes, no = int(it.get("yes") or 0), int(it.get("no") or 0)
        if (item_id.startswith("visitor:") and it.get("closes", now + 1) <= now < meta.get("activate_ts", 0)
                and yes > no and yes + no >= VISITOR_MIN_VOTES):
            out.append({"key": item_id, "yes": yes, "no": no, "meta": meta})
    return sorted(out, key=lambda x: x["meta"].get("activate_ts", 0))


def visitor_text(v: dict) -> str:
    """The Telegram post for a rule change visitors voted into the simulation: marked as simulation first and last."""
    e = html.escape
    meta = v["meta"]
    hm = datetime.fromtimestamp(meta["activate_ts"], timezone.utc).strftime("%H:%M")
    out = ["🧪 <b>SIMULATION · not the real testnet</b>", "<b>Visitors voted a rule change into the simulation</b>",
           e(visitor_title(meta)),
           "", "<b>Why it matters</b>",
           e("A visitor wrote this change in the Playground, everyone on the site could vote, and more said yes than no. "
             "The simulated validators follow the visitors and vote it in: on Tau the rules change by agreement, never by decree."),
           "", e(f"{v['yes']} yes · {v['no']} no · in force at {hm} UTC (block #{meta.get('activate_at')})"),
           "", f"<i>{e(SIM_NOTICE)}</i>",
           "", f"<a href=\"{e(SIM_LINK)}\">Watch it in the simulation</a>"]
    return "\n".join(out)


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

    def send_text(self, text: str, buttons: dict | None = None, picture: str | None = None) -> tuple[bool, float | None, str]:
        """`picture`: a public image URL shown large above the text (a link preview of it), else no preview at all."""
        preview = {"url": picture, "prefer_large_media": True, "show_above_text": True} if picture else {"is_disabled": True}
        msg = {"chat_id": TELEGRAM_CHAT, "text": text, "parse_mode": "HTML", "link_preview_options": preview}
        if buttons is not None:
            msg["reply_markup"] = buttons
        elif TELEGRAM_BOT_NAME:
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

    def __init__(self, keys: dict | None = None):
        """keys: the four values under the names X_API_KEY … X_ACCESS_SECRET; default the @TauHUDcom ones from .env."""
        self.keys = keys if keys is not None else X_KEYS

    def enabled(self) -> bool:
        return all(self.keys.values())

    def auth_header(self, url: str | None = None) -> str:
        oauth = {"oauth_consumer_key": self.keys["X_API_KEY"], "oauth_nonce": secrets.token_hex(16),
                 "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": str(int(time.time())),
                 "oauth_token": self.keys["X_ACCESS_TOKEN"], "oauth_version": "1.0"}
        # a JSON or multipart body is not part of the signature base
        params = "&".join(f"{_pct(k)}={_pct(v)}" for k, v in sorted(oauth.items()))
        base = "&".join(["POST", _pct(url or self.URL), _pct(params)])
        key = f"{_pct(self.keys['X_API_SECRET'])}&{_pct(self.keys['X_ACCESS_SECRET'])}"
        oauth["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
        return "OAuth " + ", ".join(f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(oauth.items()))

    UPLOAD = "https://api.x.com/2/media/upload"

    def send_text(self, text: str, media_id: str | None = None) -> tuple[bool, float | None, str]:
        payload = {"text": text, **({"media": {"media_ids": [media_id]}} if media_id else {})}
        req = urllib.request.Request(self.URL, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": self.auth_header()})
        return self.call(req)

    def upload(self, png: bytes, name: str = "picture.png") -> tuple[str | None, float | None, str]:
        body, ctype = multipart({"media_category": "tweet_image"}, {"media": (name, png, "image/png")})
        req = urllib.request.Request(self.UPLOAD, data=body,
                                     headers={"Content-Type": ctype, "Authorization": self.auth_header(self.UPLOAD)})
        ok, retry, err, reply = self.call(req, want_reply=True)
        if not ok:
            return None, retry, "media upload " + err
        media_id = str((reply.get("data") or {}).get("id") or reply.get("media_id_string") or "")
        return (media_id, None, "") if media_id else (None, None, "media upload: no id")

    def send_photo(self, png, r):
        media_id, retry, err = self.upload(png, "recap.png")
        if not media_id:
            return False, retry, err
        return self.send_text(recap_x(r), media_id)

    def send_with_picture(self, text: str, picture: str | None) -> tuple[bool, float | None, str]:
        """The text with the picture at `picture` (a URL) when it can be fetched and uploaded, else the text alone."""
        png = fetch_picture(picture) if picture and X_PICTURES else None
        media_id = self.upload(png)[0] if png else None
        if png and not media_id:
            log.info("x: picture %s not uploaded, posting the text alone", picture)
        return self.send_text(text, media_id)

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
        return self.send_with_picture(x_text(item), item_picture(item))


def fetch_picture(url: str) -> bytes | None:
    """A PNG or JPEG of at most 5 MB (X's limit for pictures), or None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "tauhud-alerts"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read(5 * 2**20 + 1)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        log.info("x: no picture from %s (%r)", url, exc)
        return None
    ok = data[:8] == b"\x89PNG\r\n\x1a\n" or data[:3] == b"\xff\xd8\xff"
    return data if ok and len(data) <= 5 * 2**20 else None


def item_picture(item: dict) -> str:
    """A rule change: its own card (what it does, the votes, the countdown); a restart: the live overview."""
    pid = str(item.get("id") or "")
    return f"{SHARE_HTTP}/og/proposal/{pid}.png" if item.get("kind") != "restart" and re.fullmatch(r"[0-9a-f]{8,64}", pid) \
        else f"{SHARE_HTTP}/og/hud.png"


def major_picture(m: dict) -> str:
    """The screenshot the update log names for it ("image"), else the page's own preview picture, else the site's."""
    return m.get("image") or page_picture(m["link"]) or f"{SITE}/og.png"


def page_picture(link: str) -> str | None:
    """A Tau HUD page's own preview picture (og:image), unless it is the site's general one."""
    try:
        req = urllib.request.Request(link, headers={"User-Agent": "tauhud-alerts"})
        with urllib.request.urlopen(req, timeout=20) as r:
            m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', r.read(200_000).decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    url = m.group(1) if m else None
    return url if url and not url.rstrip("/").endswith("/og.png") else None


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
        self.challenge_at = 0.0
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
                # the rules in force proposed again: a practice vote, counted in "Testnet today", never a post of its own
                "practice": ev["kind"] != "restart" and d.get("severity") == "none",
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
        self.props = props
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
                if not it["news"] or it["seen"] < meta["since"] or st in ("ok", "skip") or (isinstance(st, int) and st >= MAX_TRIES):
                    continue
                if it.get("folded") or is_practice(it):
                    continue
                if any(o2 is not it and o2["posted"].get(o.name) == "ok" and o2["kind"] == it["kind"] and o2["headline"] == it["headline"]
                       and 0 <= it["seen"] - o2["seen"] < REPEAT_WINDOW for o2 in self.state["items"]):
                    it["posted"][o.name] = "skip"  # the same news again within hours: no second post (a burst is a finding)
                    log.info("%s: same as a post of the last hours, left out: %s", o.name, it["headline"])
                    self.save_state()
                    continue
                if it["kind"] == "proposed" and it.get("thr") == 1 and time.time() - it["seen"] < PROPOSED_HOLD:
                    break  # wait: it may be agreed in a moment; keep the order of posts
                if o.name == "x" and not self.x_room():
                    it["posted"][o.name] = "skip"  # over the caps: Telegram, the feed and the page still have it
                    log.info("x: over the daily or monthly cap, left out: %s", it["headline"])
                    self.save_state()
                    continue
                ok, retry, err = await asyncio.to_thread(o.send, it)
                if ok:
                    it["posted"][o.name] = "ok"
                    if o.name == "x":
                        self.x_count()
                    log.info("posted to %s: %s", o.name, it["headline"])
                else:
                    it["posted"][o.name] = (st if isinstance(st, int) else 0) + 1
                    log.warning("%s post failed (%s), try %s of %s", o.name, err, it["posted"][o.name], MAX_TRIES)
                    meta["pause_until"] = time.time() + (retry or 60 * it["posted"][o.name])
                    self.save_state()
                    break
                self.save_state()
                await asyncio.sleep(3)  # Telegram allows ~20 posts a minute per channel

    # ---------- X: a few posts a day, paid per post ----------
    def x_on(self):
        return next((o for o in self.outlets if o.name == "x" and o.enabled()), None)

    def x_room(self, now: float | None = None) -> bool:
        """True while today's and this month's X posts are under X_DAILY_CAP and X_MONTHLY_CAP."""
        d = datetime.fromtimestamp(now if now is not None else time.time(), timezone.utc)
        st = self.state.setdefault("x", {})
        day, month = d.strftime("%Y-%m-%d"), d.strftime("%Y-%m")
        if st.get("day") != day:
            st["day"], st["today"] = day, 0
        if st.get("month") != month:
            st["month"], st["this_month"] = month, 0
        return st["today"] < X_DAILY_CAP and st["this_month"] < X_MONTHLY_CAP and st.get("pause_until", 0) <= d.timestamp()

    def x_count(self):
        st = self.state["x"]
        st["today"], st["this_month"] = st.get("today", 0) + 1, st.get("this_month", 0) + 1

    async def post_x(self, text: str, what: str, now: float | None = None, picture: str | None = None) -> bool:
        """The X copy of a post that just went to Telegram. One try: X never holds Telegram up, and a post that failed is
        not sent hours late; over the caps it is left out."""
        o = self.x_on()
        if not o:
            return False
        if not self.x_room(now):
            log.info("x: %s not posted (daily or monthly cap, or paused)", what)
            return False
        if picture and hasattr(o, "send_with_picture"):
            ok, retry, err = await asyncio.to_thread(o.send_with_picture, text, picture)
        else:
            ok, retry, err = await asyncio.to_thread(o.send_text, text)
        if ok:
            self.x_count()
            log.info("posted to x: %s", what)
        else:
            if retry:
                self.state["x"]["pause_until"] = (now if now is not None else time.time()) + retry
            log.warning("x post failed (%s): %s left out", err, what)
        self.save_state()
        return ok

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
        # a posted finding (no peers, no new blocks) already told the channel; its recovery post closes it too
        if (seen == "down" and findings.covers_outage(self.state.get("findings", {}))) or (seen == "up" and st.get("covered")):
            log.info("health: testnet %s, not posted (a finding covers it)", seen)
            st["posted"], st["covered"] = seen, seen == "down"
            st["down_since"] = cand["since"] if seen == "down" else None
            st.pop("cand", None)
            self.save_state()
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

    # ---------- findings: unusual things on the real chain ----------
    def findings_snapshot(self, now: float, with_stats: bool) -> dict:
        gov = [{"ts": p.get("proposed_ts"), "title": p.get("title"), "proposer": p.get("proposer"),
                "noop": (p.get("explain") or {}).get("severity") == "none"} for p in getattr(self, "props", None) or []]
        return {"health": self.health_now(), "peers": self.relay_json("/peers"), "status": self.relay_json("/status"),
                "stats": self.relay_json("/stats") if with_stats else None, "blocks": self.blocks,
                "gov": gov if getattr(self, "props", None) is not None else None}

    async def maybe_findings(self, now: float | None = None):
        """Run the detectors once a minute (/stats every tenth time) and send what they queued: Telegram first, then the
        X copy where the finding is one for X and today's findings on X are under FINDINGS_X_DAILY_CAP."""
        if not findings.FINDINGS_ON:
            return
        now = now if now is not None else time.time()
        st = self.state.setdefault("findings", findings.fresh_state())
        if now - st.get("checked", 0) >= findings.FINDINGS_EVERY:
            st["checked"] = now
            st["n"] = st.get("n", 0) + 1
            snap = await asyncio.to_thread(self.findings_snapshot, now, st["n"] % 10 == 1)
            for m in findings.observe(st, snap, now):
                log.info("finding: %s", m["what"])
            self.save_state()
        tg = [o for o in self.outlets if o.name == "telegram" and o.enabled()]
        while st.get("outbox") and st.get("pause_until", 0) <= now:
            m = st["outbox"][0]
            if not tg or now - m["at"] > findings.OUTBOX_MAX_AGE or m["tries"] >= MAX_TRIES:
                log.info("finding %s not posted (%s)", m["what"], "telegram off" if not tg else "too old or failed too often")
                st["outbox"].pop(0)
                continue
            for o in tg:
                ok, retry, err = await asyncio.to_thread(o.send_text, m["tg"])
                if not ok:
                    m["tries"] += 1
                    st["pause_until"] = now + (retry or 60)
                    log.warning("finding post failed (%s); trying again later", err)
                    self.save_state()
                    return
            st["outbox"].pop(0)
            day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
            if st.get("x_day") != day:
                st["x_day"], st["x_today"] = day, 0
            if m.get("x") and st["x_today"] < findings.X_DAILY:
                if await self.post_x(x_post(m["x"]), "finding " + m["what"], now):
                    st["x_today"] += 1
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
                await self.post_x(newnode_x(n, nodes_online(peers, board)), "new node " + n["key"], now, f"{SHARE_HTTP}/og/hud.png")
            else:
                log.info("newnodes: %s recorded without a post (%s)", n["key"], "daily cap" if tg else "telegram off")
            known[n["key"]] = round(now)
        if len(known) > 5000:  # oldest first out; a key that comes back that late is not new news anyway
            for k in sorted(known, key=known.get)[:len(known) - 5000]:
                del known[k]
        self.save_state()

    # ---------- the simulation's consensus switches ----------
    async def maybe_sim(self, now: float | None = None):
        """One Telegram post per simulated consensus switch, sent while its proposal is open (the 10 minutes before it is
        in force). A switch missed while the service was down is skipped, never posted late. Pure clock work: no relay needed."""
        if not SIM_ON:
            return
        now = now if now is not None else time.time()
        st = self.state.setdefault("sim", {"posted": {}})
        tg = [o for o in self.outlets if o.name == "telegram" and o.enabled()]
        if not tg or st.get("pause_until", 0) > now:
            return
        changed = False
        for ev in sim_switches(now):
            if not (ev["proposed"] <= now < ev["in_force"]) or ev["key"] in st["posted"]:
                continue
            text, buttons = sim_text(ev, await asyncio.to_thread(forecasts_for, ev)), sim_buttons()
            for o in tg:
                ok, retry, err = await asyncio.to_thread(o.send_text, text, buttons)
                if not ok:
                    st["pause_until"] = now + (retry or 60)
                    log.warning("simulation post failed (%s); trying again in a minute", err)
                    self.save_state()
                    return
            st["posted"][ev["key"]] = round(now)
            changed = True
            log.info("simulation: posted %s", ev["key"])
            if X_SIM:
                await self.post_x(sim_x(ev), "simulation " + ev["key"], now)
        for k in [k for k, t in st["posted"].items() if now - t > 7 * 86400]:
            del st["posted"][k]
            changed = True
        if changed:
            self.save_state()

    # ---------- "Testnet today" ----------
    async def maybe_today(self, now: float | None = None):
        """One evening summary of the real chain's day, at TODAY_HOUR UTC; skipped on a quiet day, never posted late."""
        if not TODAY_ON:
            return
        now = now if now is not None else time.time()
        st = self.state.setdefault("today", {})
        slot = datetime.fromtimestamp(now, timezone.utc).replace(hour=TODAY_HOUR, minute=0, second=0, microsecond=0).timestamp()
        tg = [o for o in self.outlets if o.name == "telegram" and o.enabled()]
        if not tg or now < slot or now > slot + 3 * 3600 or st.get("slot", 0) >= slot or st.get("pause_until", 0) > now:
            return
        stats = await asyncio.to_thread(self.relay_json, "/stats")
        peers, board = await asyncio.to_thread(self.relay_json, "/peers"), await asyncio.to_thread(self.relay_json, "/community/board")
        online = nodes_online(peers, board) if peers is not None or board is not None else None
        r = today_numbers(stats, self.state["items"], getattr(self, "props", []), online, slot)
        if today_worth_posting(r):
            for o in tg:
                ok, retry, err = await asyncio.to_thread(o.send_text, today_text(r), today_buttons())
                if not ok:
                    st["pause_until"] = now + (retry or 300)
                    log.warning("testnet today failed (%s); trying again later", err)
                    self.save_state()
                    return
            log.info("testnet today posted")
            st["slot"] = slot  # recorded before X: a failed X copy must not repeat the Telegram post
            await self.post_x(today_x(r), "testnet today", now, f"{SHARE_HTTP}/og/hud.png")
        else:
            log.info("testnet today: a quiet day, no post")
        st["slot"] = slot
        self.save_state()

    # ---------- changes to Tau HUD itself ----------
    def fetch_updates(self) -> list | None:
        try:
            req = urllib.request.Request(SITE_UPDATES_URL, headers={"Cache-Control": "no-cache", "User-Agent": "tauhud-alerts"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            log.warning("site updates: cannot read %s (%r)", SITE_UPDATES_URL, exc)
            return None
        return [e for e in data if isinstance(e, dict)] if isinstance(data, list) else None

    def take_updates(self, entries: list[dict], now: float):
        """New log entries into the queues: majors to post one by one, the rest into the digest. First run: history."""
        st = self.state["site"]
        seen, oldest = st["seen"], (datetime.fromtimestamp(now, timezone.utc) - timedelta(days=SITE_MAJOR_MAX_AGE_DAYS)).strftime("%Y-%m-%d")
        for e in entries:
            k = site_key(e)
            if k in seen:
                continue
            seen[k] = round(now)
            if e.get("backfill"):  # added to the log later for completeness: old news, not posted
                continue
            if isinstance(e.get("major"), dict):
                if e["major"].get("skip"):
                    log.info("site updates: major %s is marked skip, not posted", k)
                elif str(e.get("on") or "") >= oldest:
                    covers = e["major"].get("covers") or []
                    if covers:  # a round-up: the changes it names are not posted on their own, nor the digest so far
                        gone = {"major:" + str(c) for c in covers}
                        st["majors"] = [m for m in st["majors"] if m["key"] not in gone]
                        for g in gone:
                            seen.setdefault(g, round(now))
                        st["pending"] = []
                    st["majors"].append({"key": k, **major_item(e)})
                else:
                    log.info("site updates: major %s is older than %d days, not posted", k, SITE_MAJOR_MAX_AGE_DAYS)
            elif st["primed"]:
                st["pending"].append({"key": k, "at": round(now), **digest_item(e)})
        # a major marked "skip" after it was queued (posted by hand meanwhile) leaves the queue
        skip = {site_key(e) for e in entries if isinstance(e.get("major"), dict) and e["major"].get("skip")}
        st["majors"] = [m for m in st["majors"] if m["key"] not in skip]
        st["primed"] = True
        if len(seen) > 5000:
            for k in sorted(seen, key=seen.get)[:len(seen) - 5000]:
                del seen[k]

    async def maybe_site(self, now: float | None = None, entries: list | None = None):
        """Major site changes one post each, smaller ones bundled into a daily digest; see the module text."""
        if not SITE_ON:
            return
        now = now if now is not None else time.time()
        st = self.state.setdefault("site", {})
        for k, v in (("seen", {}), ("majors", []), ("pending", []), ("primed", False)):
            st.setdefault(k, v)
        if now - st.get("checked", 0) >= SITE_EVERY or entries is not None:
            st["checked"] = now
            entries = entries if entries is not None else await asyncio.to_thread(self.fetch_updates)
            if entries is not None:
                self.take_updates(entries, now)
            self.save_state()
        tg = [o for o in self.outlets if o.name == "telegram" and o.enabled()]
        if not tg or st.get("pause_until", 0) > now or not in_post_hours(now):
            return
        day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
        if st.get("day") != day:
            st["day"], st["count"] = day, 0
        if len(st["majors"]) >= SITE_CATCHUP_AT and st["count"] == 0:
            # a backlog (a long night, a busy day): one post with all of it instead of days of single posts
            batch = list(st["majors"])
            text = catchup_text(batch)
            shown = text.count("• ")
            if await self.site_send(tg, text, digest_buttons(), now):
                del st["majors"][:shown]
                st["count"] = SITE_MAJOR_DAILY_CAP
                st["last_major"] = round(now)
                log.info("site updates: catch-up post with %d new pages and features", shown)
                self.save_state()
                await self.post_x(catchup_x(batch[:shown]), "site catch-up", now, await asyncio.to_thread(major_picture, batch[0]))
            self.save_state()
            return
        if st["majors"] and st["count"] < SITE_MAJOR_DAILY_CAP and now - st.get("last_major", 0) >= SITE_MAJOR_GAP:
            m = st["majors"][0]
            if await self.site_send(tg, major_text(m), major_buttons(m), now, m.get("image")):
                st["majors"].pop(0)
                st["count"] += 1
                st["last_major"] = round(now)
                log.info("site updates: posted %s", m["key"])
                self.save_state()
                if m.get("x", True):  # "x": false in the log: announced on X by hand, with its link
                    await self.post_x(major_x(m), "site " + m["key"], now, await asyncio.to_thread(major_picture, m))
            self.save_state()
            return  # one post per check: a digest never lands on top of a major
        d0 = datetime.fromtimestamp(now, timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        slot = max((d0 + h * 3600 for h in SITE_DIGEST_HOURS if d0 + h * 3600 <= now), default=None)
        due = st["pending"] and slot is not None and st.get("last_digest", 0) < slot and now - st.get("last_major", 0) >= 1800
        if due and (len(st["pending"]) >= SITE_DIGEST_MIN or now - st["pending"][0]["at"] >= SITE_DIGEST_MAX_WAIT):
            if await self.site_send(tg, digest_text(st["pending"]), digest_buttons(), now):
                log.info("site updates: digest of %d posted", len(st["pending"]))
                st["pending"], st["last_digest"] = [], round(now)
            self.save_state()

    async def site_send(self, tg: list, text: str, buttons: dict, now: float, picture: str | None = None) -> bool:
        st = self.state["site"]
        for o in tg:
            ok, retry, err = await asyncio.to_thread(o.send_text, text, buttons, picture) if picture else \
                await asyncio.to_thread(o.send_text, text, buttons)
            if not ok:
                st["pause_until"] = now + (retry or 300)
                log.warning("site update post failed (%s); trying again later", err)
                return False
        return True

    # ---------- rule changes visitors voted into the simulation ----------
    async def maybe_visitors(self, now: float | None = None, votes: dict | None = None):
        """One Telegram post per visitor proposal that was voted in with enough votes, at most VISITOR_DAILY_CAP a day,
        sent between the close of its vote and the moment it is in force; one missed while the service was down is skipped."""
        if not SIM_ON:
            return
        now = now if now is not None else time.time()
        st = self.state.setdefault("visitors", {"posted": {}, "checked": 0})
        tg = [o for o in self.outlets if o.name == "telegram" and o.enabled()]
        if not tg or st.get("pause_until", 0) > now or (votes is None and now - st.get("checked", 0) < VISITOR_EVERY):
            return
        st["checked"] = now
        if votes is None:
            try:
                def get():
                    with urllib.request.urlopen(RELAY_HTTP + "/sim/votes", timeout=20) as r:
                        return json.loads(r.read())
                votes = await asyncio.to_thread(get)
            except Exception as exc:  # relay restarting: next minute
                log.info("visitor proposals: relay not readable (%r)", exc)
                return
        day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
        for v in visitor_ready(votes, now):
            if v["key"] in st["posted"]:
                continue
            if sum(1 for t in st["posted"].values() if datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d") == day) >= VISITOR_DAILY_CAP:
                break
            for o in tg:
                ok, retry, err = await asyncio.to_thread(o.send_text, visitor_text(v), sim_buttons())
                if not ok:
                    st["pause_until"] = now + (retry or 60)
                    log.warning("visitor proposal post failed (%s); trying again in a minute", err)
                    self.save_state()
                    return
            st["posted"][v["key"]] = round(now)
            log.info("simulation: posted visitor proposal %s", v["key"])
        for k in [k for k, t in st["posted"].items() if now - t > 7 * 86400]:
            del st["posted"][k]
        self.save_state()

    # ---------- weekly recap ----------
    @staticmethod
    def recap_slot(now: float, tz=None) -> float:
        """The latest scheduled recap time at or before now (in German time, or in tz)."""
        tz = tz or RECAP_TZ
        day = datetime.fromtimestamp(now, tz).date()
        day -= timedelta(days=(day.weekday() - RECAP_WEEKDAY) % 7)
        slot = lambda x: datetime(x.year, x.month, x.day, RECAP_HOUR, tzinfo=tz).timestamp()
        return slot(day) if slot(day) <= now else slot(day - timedelta(days=7))

    @classmethod
    def print_slot(cls, now: float) -> float:
        """The latest weekly printing at or before now: the first drop of the week, 09:00 in Tokyo, furthest east."""
        return cls.recap_slot(now, DROP_TZ["ja"])

    @classmethod
    def drops(cls, printed_at: float) -> dict:
        """When each language's readers get an edition printed at printed_at: its own drop that week, or at once
        for an edition printed outside the schedule (the first one, a reprint)."""
        out = {}
        for lang, tz in DROP_TZ.items():
            nxt = cls.recap_slot(printed_at + 7 * 86400 - 1, tz)   # the first drop in tz at or after printed_at
            while nxt - 7 * 86400 >= printed_at:
                nxt -= 7 * 86400
            out[lang] = round(nxt) if nxt - printed_at < 12 * 3600 else round(printed_at)
        return out

    def recap_numbers(self, end: float) -> dict:
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
        return recap.build(stats, get("/community"), self.state["items"], end)

    def make_recap(self, end: float) -> tuple[dict, bytes]:
        r = self.recap_numbers(end)
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

    # ---------- the weekly newspaper (gazette.py) ----------
    def make_gazette(self, r: dict, printed_at: float) -> dict:
        """Write the edition for the week in r (recap numbers) as /recap/gazette/<date>.json, latest.json and editions.json."""
        try:
            with open(os.path.join(PUBLIC_DIR, "proposals.json")) as f:
                props = json.load(f).get("proposals") or []
        except (OSError, ValueError):
            props = []
        days = [d for k, d in sorted((self.state.get("simdays") or {}).items())
                if r["start"] <= datetime.strptime(k, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() + 43200 < r["end"]]
        d = os.path.join(PUBLIC_DIR, "recap", "gazette")
        os.makedirs(d, exist_ok=True)
        try:
            with open(os.path.join(d, "editions.json")) as f:
                index = json.load(f)
        except (OSError, ValueError):
            index = []
        date = datetime.fromtimestamp(printed_at, timezone.utc).strftime("%Y-%m-%d")
        same = next((x for x in index if x.get("date") == date), None)
        no = same["no"] if same else max((x.get("no", 0) for x in index), default=0) + 1
        try:   # a Taumorrow chess round, as the chess fetcher writes it (see gazette.chess_talk)
            with open(os.path.join(PUBLIC_DIR, "recap", "chess.json")) as f:
                chess = json.load(f)
        except (OSError, ValueError):
            chess = None
        e = gazette.edition(r, props, days, no, printed_at, chess if isinstance(chess, dict) else None)
        e["drops"] = self.drops(printed_at)
        prev = next((x for x in index if x.get("date") != date), None)
        if prev:   # what each language's readers still see until their own drop
            e["prev"] = prev["date"]
        if not same:   # a new edition closes the week's rule challenge and sets the next one
            self.rotate_challenge(printed_at)
        self.attach_challenge(e)
        text = json.dumps(e, ensure_ascii=False, separators=(",", ":"))
        write_atomic(os.path.join(d, date + ".json"), text)
        write_atomic(os.path.join(d, "latest.json"), text)
        index = [gazette.summary(e)] + [x for x in index if x.get("date") != date]
        write_atomic(os.path.join(d, "editions.json"), json.dumps(index[:260], ensure_ascii=False, separators=(",", ":")))
        log.info("gazette: edition No. %s of %s written (%s)", no, date, e["banner"]["en"])
        return e

    async def maybe_gazette(self, now: float | None = None):
        """Note the visitors' day in the simulation every ten minutes, and write a first edition if none is out yet."""
        now = now if now is not None else time.time()
        st = self.state.setdefault("gazette", {"noted": 0, "tried": 0})
        if SIM_ON and now - st.get("noted", 0) >= 600:
            st["noted"] = now
            votes = await asyncio.to_thread(self.relay_json, "/sim/votes")
            preds = await asyncio.to_thread(self.relay_json, "/sim/predictions")
            day = gazette.sim_day(votes, preds)
            if day:
                days = self.state.setdefault("simdays", {})
                days[day["day"]] = day
                for k in sorted(days)[:-21]:
                    del days[k]
            self.save_state()
        if RECAP_ON and now - st.get("tried", 0) >= 600 and not os.path.exists(os.path.join(PUBLIC_DIR, "recap", "gazette", "latest.json")):
            st["tried"] = now
            try:
                r = await asyncio.to_thread(self.recap_numbers, now)
                await asyncio.to_thread(self.make_gazette, r, now)
            except Exception as exc:  # retried in ten minutes
                log.warning("gazette: first edition failed (%r)", exc)
            self.save_state()
        if RECAP_ON and st.get("cafe_v") != gazette.CAFE_V:   # once per new way of writing the talk
            st["cafe_v"] = gazette.CAFE_V
            try:
                await asyncio.to_thread(self.gazette_cafe)
            except Exception as exc:  # the café keeps its fixed talk until Monday
                log.warning("gazette: café talk for the edition out failed (%r)", exc)
            self.save_state()

    async def maybe_print(self, now: float | None = None):
        """Print the weekly edition at the week's first drop (09:00 Tokyo, Monday); each language's page shows it from
        its own 09:00 (the edition carries the three times)."""
        if not RECAP_ON:
            return
        now = now if now is not None else time.time()
        slot, st = self.print_slot(now), self.state.setdefault("printing", {})
        if not st.get("slot"):   # first run: the next printing is the next Monday's
            st["slot"] = slot
            self.save_state()
            return
        if slot <= st["slot"] or now - slot > 86400 or now - st.get("tried", 0) < 600:
            return
        st["tried"] = now
        try:
            r = await asyncio.to_thread(self.recap_numbers, slot)
            await asyncio.to_thread(self.make_gazette, r, slot)
            st["slot"] = slot
        except Exception as exc:  # retried in ten minutes
            log.warning("gazette: edition failed (%r)", exc)
        self.save_state()

    # ---------- the weekly rule challenge (gazette.py): set with each edition, answered with real rules ----------
    def challenge_ends(self, now: float) -> float:
        return self.print_slot(now + 7 * 86400)   # the next Monday edition

    def rotate_challenge(self, now: float):
        """Close the open challenge with its final answers and open the next one from now."""
        cur = self.state.get("challenge")
        if cur:
            got = gazette.challenge_answers(self.blocks, cur["id"], cur["since"], now)
            self.state["challenge_last"] = {**gazette.challenge_block(cur["id"], cur["since"], now), **got}
        nxt = gazette.next_challenge(cur and cur["id"])
        self.state["challenge"] = {"id": nxt["id"], "since": now, "ends": self.challenge_ends(now)}
        self.save_state()
        log.info("challenge: %s open until %s", nxt["id"], datetime.fromtimestamp(self.state["challenge"]["ends"], timezone.utc))

    def attach_challenge(self, e: dict):
        cur, last = self.state.get("challenge"), self.state.get("challenge_last")
        if cur:
            e["challenge"] = gazette.challenge_block(cur["id"], cur["since"], cur["ends"])
        if last:
            e["challenge_last"] = {k: last[k] for k in ("id", "title", "task", "count")} | {"answers": last["answers"][:3]}

    async def maybe_challenge(self, now: float | None = None):
        """Every two minutes: write /recap/gazette/challenge.json with the open challenge and its answers so far.
        The first time, open a challenge right away and add it to the edition already out."""
        if not RECAP_ON:
            return
        now = now if now is not None else time.time()
        if now - self.challenge_at < 120:
            return
        self.challenge_at = now
        d = os.path.join(PUBLIC_DIR, "recap", "gazette")
        if not self.state.get("challenge"):
            self.rotate_challenge(now)
            try:
                with open(os.path.join(d, "latest.json")) as f:
                    e = json.load(f)
                self.attach_challenge(e)
                text = json.dumps(e, ensure_ascii=False, separators=(",", ":"))
                write_atomic(os.path.join(d, e["date"] + ".json"), text)
                write_atomic(os.path.join(d, "latest.json"), text)
                log.info("challenge: added to edition No. %s", e.get("no"))
            except (OSError, ValueError, KeyError):
                pass
        cur = self.state["challenge"]
        out = {"now": {**gazette.challenge_block(cur["id"], cur["since"], cur["ends"]),
                       **gazette.challenge_answers(self.blocks, cur["id"], cur["since"], now + 3600, limit=24)},
               "last": self.state.get("challenge_last"), "updated": round(now)}
        os.makedirs(d, exist_ok=True)
        write_atomic(os.path.join(d, "challenge.json"), json.dumps(out, ensure_ascii=False, separators=(",", ":")))

    def gazette_cafe(self):
        """Once per CAFE_V: give the edition already out the café talk as it is written now."""
        d = os.path.join(PUBLIC_DIR, "recap", "gazette")
        try:
            with open(os.path.join(d, "latest.json")) as f:
                e = json.load(f)
        except (OSError, ValueError):
            return
        if e.get("cafe_v") == gazette.CAFE_V or not e.get("end"):
            return
        try:
            with open(os.path.join(PUBLIC_DIR, "proposals.json")) as f:
                props = json.load(f).get("proposals") or []
        except (OSError, ValueError):
            props = []
        r = self.recap_numbers(e["end"])
        days = [x for k, x in sorted((self.state.get("simdays") or {}).items())
                if r["start"] <= datetime.strptime(k, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() + 43200 < r["end"]]
        try:
            with open(os.path.join(PUBLIC_DIR, "recap", "chess.json")) as f:
                chess = json.load(f)
        except (OSError, ValueError):
            chess = None
        e["cafe"] = gazette.cafe(r, props, days, e.get("no") or 1, e["banner"], e.get("teaser") or e["lead"]["deck"], chess if isinstance(chess, dict) else None)
        e["cafe_v"] = gazette.CAFE_V
        text = json.dumps(e, ensure_ascii=False, separators=(",", ":"))
        write_atomic(os.path.join(d, e["date"] + ".json"), text)
        write_atomic(os.path.join(d, "latest.json"), text)
        log.info("gazette: café talk added to edition No. %s", e.get("no"))

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
            if o.name == "x" and not self.x_room():
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
                if o.name == "x":
                    self.x_count()
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
                        await self.maybe_print()
                        await self.maybe_gazette()
                        await self.maybe_challenge()
                        await self.maybe_findings()
                        await self.maybe_health()
                        await self.maybe_newnodes()
                        await self.maybe_sim()
                        await self.maybe_site()
                        await self.maybe_today()
                        await self.maybe_visitors()
                        await asyncio.sleep(POLL_SECONDS)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # relay restarting, network blip: try again shortly
                log.warning("relay connection lost (%r); retrying in 10 s", exc)
                await self.maybe_health()  # a relay that stays away is news too
                await self.maybe_sim()     # needs no relay
                await self.maybe_site()    # neither does this
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


def x_test() -> int:
    """One test post on X only (the Telegram channel gets nothing)."""
    o = X()
    if not o.enabled():
        print("x: off (X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN and X_ACCESS_SECRET are not all set in .env)")
        return 1
    ok, _, err = o.send_text(x_post(["✅ Tau HUD is connected to X",
                                     "This account will post when the users of the Tau testnet agree on a rule change, when a new node "
                                     "joins, and once a day what happened on the chain."]))
    hint = "\n   X refuses the same text twice: the earlier test post went out, all is well." if "duplicate" in err \
        else X_HINTS.get(err.split(":")[0], "")
    print("x: sent, look at your profile" if ok else "x: FAILED " + err + hint)
    return 0 if ok else 1


X_HINTS = {"HTTP 401": "\n   The keys do not match: copy all four again into .env (no spaces, no quotes), then rebuild.",
           "HTTP 403": "\n   No write permission: set the app to Read and Write, then REGENERATE the Access Token and Secret.",
           "HTTP 402": "\n   No credits: buy credits in the X Developer Console (Billing).",
           "HTTP 429": "\n   Too many posts right now: try again in 15 minutes."}


async def x_preview() -> int:
    """Print what X would get right now, with X's own length count; posts nothing."""
    def show(what, text):
        print(f"[{what}] {x_len(text)}/280 · {'link inside: $0.20' if 'http' in text else 'no link: $0.015'}\n{text}\n" + "-" * 60)
    w = Watcher([])
    async with connect(RELAY_URL, max_size=64 * 2**20, open_timeout=20) as ws:
        w.ws = ws
        await w.sync()
    props, events, now = replay(w.blocks, w.gov)
    by_id, pace = {p["id"]: p for p in props}, block_pace(w.blocks)
    for ev in events[-3:]:
        show(ev["kind"], x_text({"kind": ev["kind"], **describe(ev, by_id.get(ev["id"]), now.get("head", 0), pace)}))
    peers, board = w.relay_json("/peers"), w.relay_json("/community/board")
    online = nodes_online(peers, board)
    show("testnet today", today_x(today_numbers(w.relay_json("/stats"), w.state["items"], props, online, time.time())))
    show("new node (example)", newnode_x({"kind": "peer", "id": "12D3KooWexample", "for": 1800, "head": now.get("head")}, online))
    entries = w.fetch_updates() or []
    majors = [major_item(e) for e in entries if isinstance(e.get("major"), dict)][-2:]
    for m in majors:
        show("site", major_x(m))
    if majors:
        show("site catch-up", catchup_x(majors))
    print(f"Caps: {X_DAILY_CAP} a day, {X_MONTHLY_CAP} a month (X_DAILY_CAP, X_MONTHLY_CAP); links {'on' if X_LINKS else 'off'} (X_LINKS);"
          f" simulation {'on' if X_SIM else 'off'} (X_SIM). X is {'ON' if X().enabled() else 'off: keys not in .env'}.")
    return 0


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


async def today_preview() -> int:
    """Print tonight's "Testnet today" from the chain as it is now, and whether it would be posted; posts nothing."""
    w = Watcher([])
    async with connect(RELAY_URL, max_size=64 * 2**20, open_timeout=20) as ws:
        w.ws = ws
        await w.sync()
    w.props = replay(w.blocks, w.gov)[0]
    peers, board = w.relay_json("/peers"), w.relay_json("/community/board")
    r = today_numbers(w.relay_json("/stats"), w.state["items"], w.props, nodes_online(peers, board), time.time())
    print(today_text(r))
    print("-" * 60 + "\n" + ("would be posted" if today_worth_posting(r) else "a quiet day: no post"))
    return 0


def sim_preview() -> int:
    """Print today's simulation posts as they would go to Telegram; posts nothing."""
    for ev in sim_switches(time.time()):
        print(sim_text(ev, forecasts_for(ev)))
        print("-" * 60)
    return 0


def site_preview() -> int:
    """Print the site-update posts the log holds right now: the majors of the last days and a digest of the newest smaller changes."""
    entries = Watcher([]).fetch_updates()
    if entries is None:
        print(f"cannot read {SITE_UPDATES_URL}")
        return 1
    oldest = (datetime.now(timezone.utc) - timedelta(days=SITE_MAJOR_MAX_AGE_DAYS)).strftime("%Y-%m-%d")
    for e in entries:
        if isinstance(e.get("major"), dict) and str(e.get("on") or "") >= oldest:
            print(major_text(major_item(e)))
            print("-" * 60)
    small = [digest_item(e) for e in entries if not isinstance(e.get("major"), dict)][-5:]
    print(digest_text(small) if small else "No smaller changes in the log.")
    return 0


async def findings_preview() -> int:
    """What the detectors see right now, then the posts of 29 Oct 2026 (bootnode gone 12:01-15:20 UTC) replayed, then one
    example of every other finding; posts nothing."""
    def show(what, p):
        print(f"[{what}]\n{p['tg']}\n" + (f"--- X ({x_len(x_post(p['x']))}/280):\n{x_post(p['x'])}\n" if p.get("x") else "--- not on X\n")
              + "-" * 60)
    w = Watcher([])
    try:
        async with connect(RELAY_URL, max_size=64 * 2**20, open_timeout=20) as ws:
            w.ws = ws
            await w.sync()
        now = time.time()
        conds = findings.conditions(w.findings_snapshot(now, True), now, {})
        print("Now: " + ("cannot tell (our node or the relay does not answer)" if conds is None else ", ".join(
            f"{k} {'ON' if v else 'clear'}" for k, v in conds.items()) or "nothing to tell"))
        st = w.state.get("findings") or {}
        if st.get("inc"):
            print("Open incidents: " + ", ".join(f"{k} since {findings.hm(i['since'])}" for k, i in st["inc"].items()))
    except Exception as exc:
        print(f"Now: relay not reachable ({exc!r})")
    print("=" * 60 + "\nReplay of 29 Oct 2026: the IDNI bootnode stops taking peers at 12:01 UTC, back at 15:20 UTC\n" + "=" * 60)
    for m in findings_case_bootnode():
        print(f"{findings.hm(m['at'])}  ", end="")
        show(m["what"], m)
    print("=" * 60 + "\nOne of each other finding (made-up numbers)\n" + "=" * 60)
    now = time.time()
    for key, f in (("stall", {"last_ts": now - 1500, "head": 2484, "exp": 30}), ("ghost", {"sealed": 12, "waiting": 31}),
                   ("reorg", {"depth": 3, "height": 2481, "count": 1}), ("slow", {"made": 41, "want": 120, "exp": 30}),
                   ("drops", {"hour": 37, "usual": 2}), ("behind", {"lag": 42}),
                   ("peers", {"connected": 3, "boot": False, "last_ts": now - 60, "head": 2484})):
        show(key, {**findings.start_post(key, f, now), "x": findings.start_post(key, f, now)["x"]
                   if (findings.DETECTORS[key]["x"](f) if callable(findings.DETECTORS[key]["x"]) else findings.DETECTORS[key]["x"]) else None})
    held = [{"key": k, "at": now - 3600 * i} for i, k in enumerate(["stall", "stall", "reorg", "drops", "stall", "slow"])]
    show("summary of a busy stretch", findings.summary_post(held, now))
    print(f"Findings on X: at most {findings.X_DAILY} a day (FINDINGS_X_DAILY_CAP), inside X's {X_DAILY_CAP}. "
          f"Busy stretch: {findings.STORM_AT} starts in {findings.STORM_HOURS:g} h (FINDINGS_STORM_AT, FINDINGS_STORM_HOURS).")
    return 0


def findings_case_bootnode(t0: float = datetime(2026, 10, 29, 11, 50, tzinfo=timezone.utc).timestamp()) -> list[dict]:
    """29 Oct 2026, minute by minute: IDNI keeps sealing a block every 30 s, but from 12:01 to 15:20 UTC our node has no
    peer and sees none of them; then it reconnects and catches up. Returns the posts with the minute they would go out."""
    st, out, seen = findings.fresh_state(), [], {}
    chain = {h: {"header": {"timestamp": int(t0 - 3600 + 30 * h)}} for h in range(1, 1000)}  # 30 s blocks from 10:50
    off, back = t0 + 11 * 60, t0 + 210 * 60
    for minute in range(0, 240):
        now = t0 + minute * 60
        lonely = off <= now < back
        made = {h: b for h, b in chain.items() if b["header"]["timestamp"] <= now}
        if not lonely:
            seen = made
        age = now - max(b["header"]["timestamp"] for b in seen.values())
        h = {"expected_block_seconds": 30, "factors": [{"key": "node", "value": "yes"}, {"key": "last_block", "value": age},
                                                       {"key": "sync", "value": "in sync"}, {"key": "pace", "value": 120},
                                                       {"key": "mempool", "value": {"waiting": 0, "sealed": 0}}]}
        peers = {"bootnode": "boot", "counts": {"connected": 0 if lonely else 3},
                 "peers": [{"id": "boot", "label": "IDNI bootnode", "connected": not lonely}]}
        for m in findings.observe(st, {"health": h, "peers": peers, "status": {"reorgs": []}, "blocks": dict(seen)}, now):
            out.append({**m, "at": now})
    return out


def gazette_cli(reprint: bool = False) -> int:
    """Write this week's newspaper edition now, from the 7 days up to now. reprint: set the latest edition again, same
    number, date and week, e.g. after its wording changed."""
    w = Watcher()
    try:
        end = time.time()
        if reprint:
            with open(os.path.join(PUBLIC_DIR, "recap", "gazette", "latest.json")) as f:
                end = float(json.load(f)["end"])
        e = w.make_gazette(w.recap_numbers(end), end)
    except Exception as exc:
        print(f"gazette: FAILED {exc}")
        return 1
    print(f"gazette: edition No. {e['no']} of {e['date']}: {e['banner']['en']}")
    print("  https://" + FEED_URL.split("//", 1)[-1].split("/", 1)[0] + "/recap/gazette/latest.json")
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
    if "--x-test" in sys.argv:
        sys.exit(x_test())
    if "--x-preview" in sys.argv:
        sys.exit(asyncio.run(x_preview()))
    if "--preview" in sys.argv:
        sys.exit(asyncio.run(preview_latest()))
    if "--recap-now" in sys.argv or "--recap-preview" in sys.argv:
        sys.exit(recap_cli("--recap-now" in sys.argv))
    if "--gazette-now" in sys.argv or "--gazette-reprint" in sys.argv:
        sys.exit(gazette_cli("--gazette-reprint" in sys.argv))
    if "--sim-preview" in sys.argv:
        sys.exit(sim_preview())
    if "--today-preview" in sys.argv:
        sys.exit(asyncio.run(today_preview()))
    if "--site-preview" in sys.argv:
        sys.exit(site_preview())
    if "--findings-preview" in sys.argv:
        sys.exit(asyncio.run(findings_preview()))
    asyncio.run(Watcher().run())

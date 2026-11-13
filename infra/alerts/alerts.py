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

It also posts firsts (firsts.py): the first returnable, co-signed or time-locked
payment the real chain carries, once each, so the HUD's "Money with terms" card
lights up and the channels hear of it the day it happens.

It also keeps watch over the HUD's news line (tickerwatch.py): every half hour it reads the line the way a visitor's
page does and tells the owner, in a private Telegram chat and never on the channel, when nothing new has come onto it
for a week, when only a few new items are left, or when IDNI's news stopped coming in (`up owner` sets that chat).

It also posts IDNI's progress (idni_digest.py): once a day, when IDNI merged real changes into the testnet's code,
devpulse writes everything of that day up as ONE post with the combined meaning; it goes out here once, on Telegram,
and on X when the day is notable; quiet days (only tests, CI or docs) get no post. `up idni` shows the next one.

It also announces changes to Tau HUD itself, read from the site's own update
log (assets/updates.json), at the fixed SITE_SLOTS times (UTC): an entry
with a "major" field gets a post of its own, and when several are waiting
they go out together in one post, so none waits a day; every other entry
waits for a slot with no major and goes into one digest post of the smaller
changes, once enough have gathered. Each goes to Telegram and X. The first run only remembers what is already in the log,
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
  python alerts.py --test           send one test line to the owner's private chat (never the channel)
  python alerts.py --check          check the channel keys without posting: Telegram token and the bot's right to post,
                                    the X keys of Tau HUD and of Agorzilla; exit 1 when a channel cannot post
  python alerts.py --preview        print how the newest rule changes would be posted, post nothing
  python alerts.py --recap-preview  draw this week's recap and save it, post nothing
  python alerts.py --recap-now      draw the recap and post it to each configured channel
  python alerts.py --gazette-now    write this week's newspaper edition now (same number if one is already out today)
  python alerts.py --gazette-reprint  print the latest edition again with the current wording (same number, date and week)
  python alerts.py --sim-preview    print today's two simulation posts (the consensus switches), post nothing
  python alerts.py --today-preview  print the "Testnet today" summary as it stands now, post nothing
  python alerts.py --site-preview   print the site-update posts waiting in assets/updates.json, post nothing
  python alerts.py --plan-preview   print the planned posts still to come (assets/posts-plan.json), post nothing
  python alerts.py --deepdives-preview  print the closer looks still to come (assets/deepdives.json), post nothing
  python alerts.py --island-preview  print the Key Crier's report of the island's day so far (relay /isle), post nothing
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
import statistics
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
import firsts
import gazette
import ai_meter
import crewlog
import earnings
import idni_digest
import restart_brief
import fixwatch
import recap
import rulefacts
import tickerwatch

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
NODE_PUBLIC = os.environ.get("NODE_URL", "https://node.tauhud.com").rstrip("/")   # where the share pictures are public
POST_MAX_AGE = float(os.environ.get("POST_MAX_AGE_SECONDS", 3 * 3600))
OPEN_ADMISSION = os.environ.get("TAU_GOVERNANCE_OPEN_ADMISSION", "true").lower() in ("1", "true", "yes")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "@tauHUDcom").strip()
# the question bot (bot.py, same token): every channel post carries buttons that open it; empty = no buttons
TELEGRAM_BOT_NAME = os.environ.get("TELEGRAM_BOT_USERNAME", "tauhud_alerts_bot").strip().lstrip("@")
X_KEYS = {k: os.environ.get(k, "").strip() for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")}
# X (@TauHUDcom) is paid per post since 2026: $0.015 a post, $0.20 for one with a link in it. So X gets what Telegram gets
# (rule changes, new nodes, "Testnet today", the site's news and smaller changes, the weekly recap with the paper's headline,
# the simulation's switches when SIM_POSTS=true, unless X_SIM=false), each in a short text without a link (the profile carries tauhud.com), and
# never more than X_DAILY_CAP / X_MONTHLY_CAP posts (240 a month: about $3.60). The simulation and the smaller site changes
# leave the day's last X_RESERVE posts for the real chain. Not on X: practice votes, health alarms, visitor proposals.
# Findings (findings.py) go to X only for real-chain incidents (no blocks reaching us, no peers, a reorg, a busy stretch),
# at most FINDINGS_X_DAILY_CAP a day.
X_LINKS = os.environ.get("X_LINKS", "false").lower() in ("1", "true", "yes")
X_DAILY_CAP = int(os.environ.get("X_DAILY_CAP", 2))   # 12 Nov 2026: the day's best only, not 8 automatic posts
X_MONTHLY_CAP = int(os.environ.get("X_MONTHLY_CAP", 240))
X_RESERVE = int(os.environ.get("X_RESERVE", 1))
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
RECAP_LATE = float(os.environ.get("RECAP_LATE_HOURS", 3)) * 3600    # a Monday post missed by longer (a restart) is skipped
# The weekly paper comes out for each language at RECAP_HOUR on RECAP_WEEKDAY in its readers' own time: Japanese first
# (09:00 Tokyo), then Chinese (09:00 Beijing), then English (09:00 German time). It is printed once, at the first drop;
# each language's page shows it from its own drop and the edition before until then.
DROP_TZ = {"ja": ZoneInfo("Asia/Tokyo"), "zh": ZoneInfo("Asia/Shanghai"), "en": RECAP_TZ}
HEALTH_ON = os.environ.get("HEALTH_ALERTS", "true").lower() in ("1", "true", "yes")
HEALTH_DOWN_BELOW = float(os.environ.get("HEALTH_DOWN_BELOW", 50))   # also "down" whenever the relay says so
HEALTH_UP_AT = float(os.environ.get("HEALTH_UP_AT", 70))             # recovered at or above this
HEALTH_CONFIRM = float(os.environ.get("HEALTH_CONFIRM_SECONDS", 600))
HEALTH_EVERY = float(os.environ.get("HEALTH_POLL_SECONDS", 60))
# New nodes on the network (relay /peers and /community/board): one post per check, listing every node that has
# stayed NEWNODE_HOLD seconds (several at once, e.g. after a rebuild, share one post), never for one first seen more
# than a day ago, at most NEWNODE_DAILY_CAP posts a day (the rest are recorded, not posted). A post waits up to
# NEWNODE_GROUP seconds while another new node is about to qualify, so nodes that arrive together are posted together.
NEWNODE_ON = os.environ.get("NEWNODE_ALERTS", "true").lower() in ("1", "true", "yes")
# 6 h since 7 November 2026: peers that come for a few hours (often around a testnet restart) and go again made
# "9 nodes online" in the morning and "2 nodes online" the same evening; they now only raise the day's peak
NEWNODE_HOLD = float(os.environ.get("NEWNODE_HOLD_SECONDS", 21600))
NEWNODE_DAILY_CAP = int(os.environ.get("NEWNODE_DAILY_CAP", 3))
NEWNODE_EVERY = float(os.environ.get("NEWNODE_POLL_SECONDS", 300))
NEWNODE_GROUP = float(os.environ.get("NEWNODE_GROUP_SECONDS", 600))
# Simulation mode on the site runs a made-up chain in the visitor's browser (assets/sim.js), the same for everyone because it is
# generated from the clock, with a fixed day programme. Only its two consensus switches are announced here, each when its proposal
# appears, 10 minutes before it is in force; the channel reports the real testnet, so these posts are rare and marked as simulated.
# SIM_SWITCHES must equal STAKE_SLOT / FIXED_SLOT in assets/sim.js (slot k = proposed at k:20 UTC, in force at k:30 UTC).
SIM_ON = os.environ.get("SIM_ALERTS", "true").lower() in ("1", "true", "yes")
# Since 5 November 2026 the switches and the visitors' simulated rule changes no longer get posts of their own: the same
# post twice a day read like spam in a channel about the real testnet. One planned post (assets/posts-plan.json,
# "sim-schedule") explains the daily programme instead. SIM_POSTS=true brings the posts back.
SIM_POSTS = os.environ.get("SIM_POSTS", "false").lower() in ("1", "true", "yes")
SIM_SWITCHES = (("stake", 10), ("fixed", 16))
SIM_PROPOSED_AT, SIM_IN_FORCE_AT = 20 * 60, 30 * 60
SIM_LINK = f"{SITE}/proposals/?mode=sim"
# IDNI's progress of the day (idni_digest.py, written by devpulse into /state/devpulse/digests.json): posted once, within
# IDNI_DIGEST_LATE_HOURS of its window's end, at most one a UTC day; X only when the writer marks the day as notable.
IDNI_ON = os.environ.get("IDNI_DIGEST", "true").lower() in ("1", "true", "yes")
# Changes to Tau HUD itself, from the update log every release appends to. Mark an entry as worth its own post with
#   "major": {"id": "unique-slug", "title": "…", "text": "one or two plain sentences", "link": "/page/"}
# plus "image": "/assets/shots/<id>.png", a 16:9 screenshot (PNG or JPEG, at most 5 MB) that goes under the X post,
# and add "skip": "why" to a major that must not be posted (already announced by hand); it also leaves the queue.
# (text and link are optional: the entry's first two sentences and the home page). Everything else is bundled into a digest.
SITE_ON = os.environ.get("SITE_UPDATES", "true").lower() in ("1", "true", "yes")
SITE_UPDATES_URL = os.environ.get("SITE_UPDATES_URL", f"{SITE}/assets/updates.json")
SITE_EVERY = float(os.environ.get("SITE_UPDATES_POLL_SECONDS", 600))
SITE_MAJOR_MAX_AGE_DAYS = int(os.environ.get("SITE_MAJOR_MAX_AGE_DAYS", 3))
# Fixed times for the site's own news, UTC (09:00, 13:00 and 17:00 German winter time): at each, everything new since the
# last one goes out as one post on Telegram and X; one new page or feature gets its own post with its screenshot.
SITE_SLOTS = tuple(sorted(int(x) for x in os.environ.get("SITE_SLOTS", "8,12,16").split(",")))
SITE_SLOT_HOURS = float(os.environ.get("SITE_SLOT_HOURS", 4))  # a slot not used by then is over: nothing new at night
# The smaller changes go out once a week (since 6 November 2026: up to three digests a day read like a changelog), at
# SITE_DIGEST_HOUR UTC on SITE_DIGEST_WEEKDAY (Friday 17:00 German winter time), at most SITE_DIGEST_LINES of them by
# name, the rest counted; Telegram only unless SITE_DIGEST_X=true.
SITE_DIGEST_WEEKDAY = int(os.environ.get("SITE_DIGEST_WEEKDAY", 4))   # 0 = Monday
SITE_DIGEST_HOUR = int(os.environ.get("SITE_DIGEST_HOUR", 16))        # UTC
SITE_DIGEST_LINES = int(os.environ.get("SITE_DIGEST_LINES", 5))
SITE_DIGEST_X = os.environ.get("SITE_DIGEST_X", "false").lower() in ("1", "true", "yes")
SITE_LOG_LINK = f"{SITE}/#updates"
# Posts planned ahead (the month's calendar): assets/posts-plan.json on the site, each sent once at its time on Telegram
# and X, or within PLAN_WINDOW_HOURS after it (a later restart); after that it is over, never posted late.
PLAN_ON = os.environ.get("POSTS_PLAN", "true").lower() in ("1", "true", "yes")
PLAN_URL = os.environ.get("POSTS_PLAN_URL", f"{SITE}/assets/posts-plan.json")
PLAN_WINDOW = float(os.environ.get("PLAN_WINDOW_HOURS", 3)) * 3600
PLAN_FOOT = "✨ From Tau HUD"
# "Testnet today": one evening summary of the real chain's last 24 hours, only on a day with something to report.
# Practice votes (the rules in force proposed again) appear here instead of in posts of their own.
TODAY_ON = os.environ.get("TESTNET_TODAY", "true").lower() in ("1", "true", "yes")
TODAY_HOUR = int(os.environ.get("TESTNET_TODAY_HOUR", 19))   # UTC
# A closer look at one page of Tau HUD a day (assets/deepdives.json on the site, in its order, each once): Telegram at
# DEEPDIVE_HOUR UTC, the X copy for every DEEPDIVE_X_EVERY-th one, so the series stays well inside the X caps.
DEEPDIVE_ON = os.environ.get("DEEPDIVES", "true").lower() in ("1", "true", "yes")
DEEPDIVE_URL = os.environ.get("DEEPDIVES_URL", f"{SITE}/assets/deepdives.json")
DEEPDIVE_HOUR = int(os.environ.get("DEEPDIVE_HOUR", 13))     # UTC (14:00 German winter time)
DEEPDIVE_X_EVERY = max(1, int(os.environ.get("DEEPDIVE_X_EVERY", 2)))
# the days of the week a closer look goes out (0 = Monday); Monday, Wednesday and Friday since 6 November 2026
DEEPDIVE_DAYS = tuple(sorted({int(x) for x in os.environ.get("DEEPDIVE_DAYS", "0,2,4").split(",") if x.strip()}))
DEEPDIVE_LINE = "🔎 TAU HUD · a closer look"
DEEPDIVE_FOOT = "🔎 A closer look at Tau HUD"
# The Key Crier: White Rabbit Key's shared island (relay /isle) summed up every morning for the day before, at
# ISLAND_HOUR UTC; the X copy only for a day with a story (an election won or a law passed by real players), told as
# that story, at most every ISLAND_X_EVERY_DAYS days (since 7 November 2026: "1 campaign, 3 moves" read like spam; a
# day of moves alone stays on Telegram).
# On Monday the report opens with the governor's count: who governs the island this week and which laws hold (the
# relay's `last`, decided at Monday 00:00 German time), on X too.
ISLAND_ON = os.environ.get("ISLAND_CRIER", "true").lower() in ("1", "true", "yes")
ISLAND_HOUR = int(os.environ.get("ISLAND_HOUR", 7))         # UTC (08:00 German winter time: the morning paper)
ISLAND_EVERY = float(os.environ.get("ISLAND_POLL_SECONDS", 600))
ISLAND_X_EVERY_DAYS = max(1, int(os.environ.get("ISLAND_X_EVERY_DAYS", 1)))
ISLAND_DAYS = int(os.environ.get("ISLAND_DAYS", 7))         # a campaign's length; rabbit/game.js DAYS is read when reachable
ISLAND_GAME_JS = f"{SITE}/rabbit/game.js"
ISLAND_LINK = f"{SITE}/rabbit/"
ISLAND_LINE = "🐇 WHITE RABBIT KEY · the Key Crier"
ISLAND_FOOT = "🐇 White Rabbit Key, a game on Tau HUD"
# the picture under the Key Crier's X post: the island painting the game shows now (island_pic.py, from the art folder the
# painting pipeline writes, /opt/sites/rico/art), never a repo screenshot. Until 7 November 2026 the post carried
# assets/shots/rabbit.png, the drawn island of October. The same painting without a card is kept public at
# node.tauhud.com/island/today.jpg for the closer look at the game (assets/deepdives.json); none at all when there is no painting.
ISLAND_ART = os.environ.get("ISLAND_ART", "/art")
ISLAND_PIC_DIR = os.path.join(PUBLIC_DIR, "island")
ISLAND_PIC_EVERY = 6 * 3600   # a new painting (up keep) is in the public picture within hours
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
                p["meaning"] = meaning_of(p["revisions"], spec)
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


RESTART_HEADLINE = "The Tau Net testnet restarted"
# What a restart means for a reader's own test wallet, only what the chain itself makes true: the key lives in the
# browser and still signs; balance and rules lived on the old chain, which is gone.
RESTART_FOR_YOU = ("For you: a test wallet made on Tau HUD keeps its key in your browser and can sign again on the new chain, "
                   "but its test AGRS and its own rules were on the old chain and start again from zero.")


def describe(ev: dict, p: dict | None, head: int, pace: float | None) -> dict:
    """Everything a post says about an event: a headline, what changes, why it
    matters, the facts, a plain one-paragraph body (feed, page, X) and a link."""
    k = ev["kind"]
    if k == "restart":
        old = ev.get("old_tip")
        why = "The test network started over: balances, rules and history begin again from the starting state."
        facts = ([f"The old chain ended at block #{fmt_n(old)}."] if old else []) + ["Tau HUD follows the new chain from block 1.",
                 RESTART_FOR_YOU]
        return {"headline": RESTART_HEADLINE, "what": [], "why": why, "why_title": "What happened", "facts": facts,
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
    mean = (p or {}).get("meaning") if k != "dropped" else None
    return {"headline": headline, "label": x.get("label"), "what": what, "why": why, "facts": facts, "diff": rdiff, "note": note,
            "meaning": mean,
            "what_title": "What changed" if k == "active" else "What it would change" if k == "dropped" else "What changes",
            "severity": x.get("severity"), "body": body, "link": link}


DIFF_LINES = 6  # changed lines shown in a post; the rest is on the page
MEANING_LINES = 4  # lines of "what it decides differently" in a post; the rest is on the page


def meaning_of(revisions: list, spec: dict) -> dict | None:
    """What a rule change decides differently from the rules in force (spec), read for every case by rulefacts.py, the
    same reading as the box on /proposals/: {same, lines, unread}. None when it carries no rule text, its text equals
    the rules in force, or none of the outputs it changes can be read exactly."""
    if not revisions:
        return None
    try:
        m = rulefacts.meaning(spec, revisions)
    except Exception as e:  # a reading never stops a post
        log.warning("rule meaning not read: %s", e)
        return None
    if not any(s["ok"] for s in m["streams"]):
        return None
    lines = [f"{line['topic']} · {rulefacts.line_text(line)}" for line in rulefacts.meaning_lines(m)]
    unread = [(rulefacts.STREAMS.get(s["stream"]) or {}).get("topic", f"output {s['stream']}") for s in m["streams"] if not s["ok"]]
    return {"same": m["same"], "lines": lines, "unread": unread}


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
    if len(item["what"]) > 1 or (item["kind"] == "restart" and item["what"]):  # one change is already the headline (not a restart's)
        rows = [f"• {e(w)}" for w in item["what"]]   # air between them (13 Nov 2026: posts in short paragraphs)
        out += ["", f"<b>{e(item.get('what_title', 'What changes'))}</b>", rows[0]] + [x for r in rows[1:] for x in ("", r)]
    mean = item.get("meaning")
    if mean:  # exact, not sampled: the same reading as the box on /proposals/
        if mean["same"]:
            out += ["", "<b>What it decides differently</b>", "Nothing. Read for every case, the new text decides exactly as the old one."]
        else:
            rows = [f"• {e(t)}" for t in mean["lines"][:MEANING_LINES]]
            if len(mean["lines"]) > MEANING_LINES:
                rows.append(f"… {len(mean['lines']) - MEANING_LINES} more on the page")
            if not mean["lines"]:
                rows.append("No difference where it can be read.")
            if mean["unread"]:
                rows.append(e("Not read exactly: " + ", ".join(mean["unread"]) + "."))
            out += ["", "<b>What it decides differently</b> (read for every case)"] + rows
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
X_REAL = "⛓ Tau Testnet Alpha"
X_SIM_LINE = "🧪 SIMULATION · not the real testnet"
X_SIM_FOOT = "🧪 Simulation, not the real testnet"
X_SITE_NOTE = "✨ Tau HUD website update, not testnet news"
X_TAG = "#TauNet"
# Every X post carries this, once, at the very end after the source line; never more tags. $AGRS was dropped on
# 12 Nov 2026: a cashtag puts the posts into price feeds next to price bots, and Tau HUD makes no coin talk.
X_MUST = ("#TauNet",)


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


def x_post(lines: list[str], link: str | None = None, keep: int = 1, foot: str = X_REAL, tag: str = X_TAG,
           with_link: bool | None = None) -> str:
    """Lines as one post of at most 280 (first line the headline): the last line loses sentences, then whole lines go
    (never the first `keep`), then it is cut. `foot` and the hashtag always close it; the link joins them only with
    X_LINKS (it makes a post 13 times dearer), or where the caller says so for this one post (`with_link`)."""
    links = X_LINKS if with_link is None else with_link
    tag = " ".join([tag] + [t for t in X_MUST if t not in (tag or "").split()]).strip()
    tail = "\n\n" + " · ".join(x for x in (foot, link if link and links else None, tag) if x)
    out = [" ".join(str(x).split()) for x in lines if x and str(x).strip()]
    if not links:
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
    """A rule change on the real chain: the line that says so, the headline, then why it matters as far as it fits; a
    restart with its brief: what the new chain brings (restart_brief.py)."""
    icon = ICONS.get(item["kind"], "•")
    return x_post([f"{icon} {item['headline']}", item.get("x_line") or item.get("why") or item.get("body")], item.get("link"))


def paper_out(r: dict) -> dict | None:
    """This Monday's edition of The Daily Consensus (latest.json, printed earlier the same day), or None."""
    try:
        with open(os.path.join(PUBLIC_DIR, "recap", "gazette", "latest.json")) as f:
            e = json.load(f)
    except (OSError, ValueError):
        return None
    day = datetime.fromtimestamp(r["end"] - 1, timezone.utc).strftime("%Y-%m-%d")
    if not isinstance(e, dict) or e.get("date") != day or not (e.get("banner") or {}).get("en"):
        return None
    return e


def recap_x(r: dict) -> str:
    """The Monday post on X: the new Daily Consensus first (number, headline, its opening), then the week in numbers as far
    as they fit; without an edition of today, the recap alone."""
    e = paper_out(r)
    week = [f"• {x}" for x in recap.lines(r, SITE)[:3]]
    if not e:
        return x_post([f"📊 Tau testnet weekly recap · {recap.period(r)}"] + week, f"{SITE}/stats/")
    teaser = (e.get("teaser") or {}).get("en") or ""
    return x_post([f"📰 The Daily Consensus No. {e.get('no')} is out", f"“{e['banner']['en']}”", sentences(teaser, 1)] + week[:2],
                  f"{SITE}/gazette/", keep=2)


def recap_caption(r: dict) -> str:
    """The Monday post on Telegram (a photo caption, at most 1024 characters): the new edition, then the week in numbers."""
    e = paper_out(r)
    if not e:
        return recap.caption_html(r, SITE)
    q = html.escape
    teaser = (e.get("teaser") or {}).get("en") or ""
    for n in (2, 1, 0):
        text = (f"📰 <b>THE DAILY CONSENSUS · No. {q(str(e.get('no')))} is out</b>\n\n<b>{q(e['banner']['en'])}</b>\n"
                + (f"{q(sentences(teaser, n))}\n" if n else "")
                + f"\n<a href=\"{SITE}/gazette/\">Read this week's edition</a>\n\n"
                + f"📊 <b>The week on the testnet</b> · {q(recap.period(r))}\n" + "\n".join("• " + q(x) for x in recap.lines(r, SITE)[:3])
                + f"\n\n<a href=\"{SITE}/stats/\">Stats</a> · <a href=\"{SITE}/proposals/\">Rule changes</a>")
        if len(re.sub(r"<[^>]+>", "", text)) <= 1000:
            return text
    return text


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


def new_nodes(peers: dict | None, board: dict | None, known: dict, now: float, soon: float = 0) -> list[dict]:
    """Nodes worth a post: a kit node that has reported for NEWNODE_HOLD, or a
    peer (not the bootnode, not a kit node) our node has known that long and
    still sees. Each comes back once: `known` holds every key ever handled.
    With `soon`, the nodes that will qualify within that many seconds instead."""
    out, hold = [], NEWNODE_HOLD - soon
    for n in (board or {}).get("nodes") or []:
        key = "kit:" + str(n.get("id"))
        if key in known or not n.get("online"):
            continue
        first, last = n.get("first_seen") or now, n.get("last_seen") or 0
        if last - first >= hold and now - first < 86400 + NEWNODE_HOLD:
            out.append({"key": key, "kind": "kit", "name": str(n.get("name") or "node"), "for": last - first,
                        "height": n.get("height")})
    kit_peers = {p["id"] for p in (peers or {}).get("peers") or [] if p.get("community")}
    for p in (peers or {}).get("peers") or []:
        key = "peer:" + str(p.get("id"))
        if key in known or p.get("label") or p["id"] in kit_peers:
            continue
        first, last = p.get("first_seen") or now, p.get("last_seen") or 0
        if now - last < 600 and last - first >= hold and now - first < 86400 + NEWNODE_HOLD:
            out.append({"key": key, "kind": "peer", "id": str(p["id"]), "for": last - first, "head": p.get("head")})
    return out


def nodes_online(peers: dict | None, board: dict | None) -> int:
    """Our node, the online peers and the online kit nodes that are not among them."""
    ps = (peers or {}).get("peers") or []
    named = {p["community"]["id"] for p in ps if p.get("community") and p.get("online")}
    kit = [n for n in (board or {}).get("nodes") or [] if n.get("online") and n.get("id") not in named]
    return 1 + sum(1 for p in ps if p.get("online")) + len(kit)


def newnode_text(ns: dict | list[dict], online: int) -> str:
    """One Telegram post for one new node or for several that qualified together."""
    ns = [ns] if isinstance(ns, dict) else ns
    e = html.escape
    link = f"<a href=\"{SITE}/nodes/\">All nodes on Tau HUD</a>"
    if len(ns) > 1:
        lines = [REAL_LINE, f"🆕 <b>{len(ns)} new nodes joined the Tau testnet</b>"]
        for n in ns:
            if n["kind"] == "kit":
                lines.append(f"• Community node {e(n['name'])} (Tau HUD kit), checking blocks for {fmt_dur(n['for'])}"
                             + (f", at block #{fmt_n(n['height'])}" if n.get("height") else "") + ".")
            else:
                lines.append(f"• Peer {e(n['id'][:8])}…{e(n['id'][-4:])}, seen for {fmt_dur(n['for'])}"
                             + (f", at block #{fmt_n(n['head'])}" if n.get("head") else "") + ".")
        if any(n["kind"] == "peer" for n in ns):
            lines.append("Peers without a name do not run our kit.")
        return "\n".join(lines + [f"Nodes online now: {online}.", "", link])
    n = ns[0]
    if n["kind"] == "kit":
        head = f"🆕 <b>New community node: {e(n['name'])}</b>"
        body = (f"Someone started a Tau testnet node with the Tau HUD kit. It has checked every block for "
                f"{fmt_dur(n['for'])}" + (f" and is at block #{fmt_n(n['height'])}" if n.get("height") else "") + ".")
    else:
        head = "🆕 <b>A new node joined the Tau testnet</b>"
        body = (f"Our node has seen it for {fmt_dur(n['for'])}" + (f", at block #{fmt_n(n['head'])}" if n.get("head") else "")
                + f". Peer {e(n['id'][:8])}…{e(n['id'][-4:])}, no name: it does not run our kit.")
    return "\n".join([REAL_LINE, head, body, f"Nodes online now: {online}.", "", link])


def newnode_x(ns: dict | list[dict], online: int) -> str:
    ns = [ns] if isinstance(ns, dict) else ns
    if len(ns) > 1:
        kits = [n["name"] for n in ns if n["kind"] == "kit"]
        peers = len(ns) - len(kits)
        parts = ([f"community node{'s' if len(kits) > 1 else ''} {', '.join(kits)} (Tau HUD kit)"] if kits else []) + \
                ([f"{peers} peer{'s' if peers > 1 else ''} our node sees"] if peers else [])
        body = f"{' and '.join(parts)[:1].upper()}{' and '.join(parts)[1:]}, each for at least {fmt_dur(min(n['for'] for n in ns))}."
        return x_post([f"🆕 {len(ns)} new nodes joined the Tau testnet", f"{body} Nodes online now: {online}."], f"{SITE}/nodes/")
    n = ns[0]
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


def today_numbers(stats: dict | None, items: list[dict], props: list[dict], online: int | None, end: float,
                  last_block: float | None = None) -> dict:
    """The real chain's last 24 hours up to `end`: blocks, pace, transactions, practice votes, rule events, what comes next.
    `last_block`: when the newest block known was sealed, for a day without one (the stats' newest block otherwise)."""
    start = end - 86400
    f = {k: i for i, k in enumerate((stats or {}).get("fields") or [])}
    allrows = [r for r in (stats or {}).get("blocks") or [] if "timestamp" in f and r[f["timestamp"]]]
    rows = [r for r in allrows if start <= r[f["timestamp"]] < end]
    newest = max([r[f["timestamp"]] for r in allrows] + [last_block or 0]) or None
    ts = sorted(r[f["timestamp"]] for r in rows)
    gaps = sorted(b - a for a, b in zip(ts, ts[1:]) if b > a)
    senders = {x for r in rows for x in r[f["senders"]]} if "senders" in f else set()
    recent = [it for it in items if start <= (it.get("seen") or 0) < end and not it.get("folded")]
    practice = {it.get("id") for it in recent if is_practice(it)}
    events = grouped([RESTART_HEADLINE if it["kind"] == "restart" else it["headline"]   # a restart post's own title says what came with it
                      for it in reversed(recent) if not is_practice(it) and it["kind"] in ("agreed", "active", "dropped", "restart")])
    by_id = {p.get("id"): p for p in props}
    proposers = [by_id[i]["proposer"] for i in practice if i in by_id and by_id[i].get("proposer")]
    head = (stats or {}).get("head") or 0
    pace = gaps[len(gaps) // 2] if gaps else None
    slow = slowest_hour(ts, end, pace)
    coming = [{"title": p["title"], "at": p["activate_at"], "eta": eta_txt(p["activate_at"] - head, pace) if head else ""}
              for p in props if p.get("approved_at") is not None and p.get("activated_at") is None and p.get("expired_at") is None
              and (p.get("explain") or {}).get("severity") != "none"]
    return {"end": end, "blocks": len(rows), "pace": pace, "txs": sum(r[f["txs"]] for r in rows) if "txs" in f else 0,
            "senders": len(senders), "practice": len(practice), "practice_why": practice_meaning(len(practice), proposers),
            "events": events, "online": online, "last_block": newest if newest and newest < end else None,
            "coming": sorted(coming, key=lambda c: c["at"])[:2], "wallets": None, "slow": slow}


def slowest_hour(ts: list[float], end: float, pace: float | None) -> dict | None:
    """The full hour with the fewest blocks between the day's first block and `end`, when it held less than half of
    what the median pace makes usual (the median alone hides a slow stretch); None on an even day."""
    if not pace or len(ts) < 2:
        return None
    usual, best, t = 3600 / pace, None, ts[0]
    while t + 3600 <= end:
        n = sum(1 for x in ts if t <= x < t + 3600)
        if best is None or n < best["blocks"]:
            best = {"blocks": n, "at": t}
        t += 3600
    if best is None or best["blocks"] >= usual / 2:
        return None
    return {**best, "usual": round(usual)}


WALLET_WHO = {  # the relay's wallet tags (relay/walletdays.py), in words; our own wallets say so
    "idni": "IDNI's own test accounts, the ones the testnet started with",
    "bot": "our island bot's wallets (the islanders of White Rabbit Key)",
    "cruise": "simulated passengers of {ship}: our own wallets, every stop a real transaction",
    "rabbit": "White Rabbit Key players",
    "agorzilla": "wallets that fed Agorzilla",
    "tauhud": "wallets that sent from a Tau HUD page",
    "other": "other wallets, not ours and not IDNI's",
}
SHIP_NAMES = {"dryrun": "MS Dry Run", "queen": "Queen Mempool"}
USUAL_DAYS = 7


def ships_in(log: list | dict | None, start: float, end: float) -> list[str]:
    """The cruise ships that landed between start and end, by name, from the relay's logbook (/cruise/log)."""
    rows = (log or {}).get("entries") if isinstance(log, dict) else log
    names: list[str] = []
    for e in rows or []:
        if not isinstance(e, dict) or e.get("kind") != "landed" or not (start <= (e.get("t") or 0) < end):
            continue
        name = SHIP_NAMES.get(str(e.get("ship")), str(e.get("ship") or "a cruise ship"))
        if name not in names:
            names.append(name)
    return names


def today_wallets(active: dict | None, day: str, ships: list[str] | None = None) -> dict | None:
    """Who sent today, from the relay's active-wallets record (/wallets/active, the same source as the Active wallets
    chart on /stats/): the wallets active on `day` (UTC) by tag, the usual number (the mean of the USUAL_DAYS days
    before), the wallets seen for the first time today. None when the relay has no record of the day."""
    if not isinstance(active, dict) or not isinstance(active.get("days"), dict):
        return None
    tags, days = list(active.get("tags") or []), active["days"]
    row = (days.get(day) or {}).get("1")
    if not tags or not isinstance(row, list) or len(row) != len(tags):
        return None
    by = {t: int(n) for t, n in zip(tags, row) if n}
    before = sorted(d for d in days if d < day)[-USUAL_DAYS:]
    rows = [r for r in (days[d].get("1") for d in before) if isinstance(r, list) and len(r) == len(tags)]
    # the usual day: the median of the days before, without our simulated passengers (11 Nov 2026: one cruise day
    # lifted the mean from 28 to 48, and every ordinary day after it read "fewer than usual")
    past = [sum(int(n) for t, n in zip(tags, r) if t != "cruise") for r in rows]
    usual = round(statistics.median(past)) if past else None
    oi = tags.index("other") if "other" in tags else None
    other_usual = statistics.median([int(r[oi]) for r in rows]) if rows and oi is not None else 0
    new_row = (active.get("new") or {}).get(day) or []
    new = sum(int(n) for n in new_row) if isinstance(new_row, list) else 0
    other_new = int(new_row[oi]) if isinstance(new_row, list) and oi is not None and len(new_row) == len(tags) else 0
    total = sum(by.values())
    ratio = round(total / usual, 1) if usual else None
    return {"total": total, "by": by, "usual": usual, "ratio": ratio, "new": new, "ships": list(ships or []),
            "other_new": other_new, "other_usual": other_usual,
            "ours": sum(by.get(t, 0) for t in ("bot", "cruise", "agorzilla", "tauhud", "rabbit"))}


def outsiders_news(w: dict | None) -> bool:
    """Wallets that are not ours and not IDNI's are news only when one is new or there are more than usual; the same
    one wallet every day is not (11 Nov 2026: the same sentence four evenings in a row)."""
    if not w:
        return False
    n = w["by"].get("other", 0)
    return bool(n) and (w.get("other_new", 0) > 0 or n > w.get("other_usual", 0))


def outsiders_line(w: dict, short: bool = False) -> str:
    n, fresh = w["by"].get("other", 0), w.get("other_new", 0)
    if fresh:
        who = "one of them" if n > 1 and fresh == 1 else ("all of them" if fresh == n and n > 1 else f"{fresh} of them" if n > 1 else "it")
        first = f"{plural(n, 'wallet')} that {'is' if n == 1 else 'are'} not ours and not IDNI's sent today, {who} for the first time"
        return (first + ".") if short else first + ": someone new is trying the testnet on their own."
    return f"{n} wallets that are not ours and not IDNI's sent today, more than the usual {w['other_usual']:g}."


def wallets_head(w: dict, short: bool = False) -> str:
    """"77 wallets sent transactions, 3.5× the usual 22" / "about the usual" / "fewer than usual"; `short` for X."""
    head = f"{plural(w['total'], 'wallet')} sent {'today' if short else 'transactions'}"
    u, r = w.get("usual"), w.get("ratio")
    if not u or r is None:
        return head
    if r >= 1.5:
        return f"{head}, {r:g}× the usual {u}"
    if r <= 0.6:
        return f"{head}, fewer than the usual {u}"
    return f"{head}, about the usual {u}"


def wallets_lines(w: dict) -> list[str]:
    """One line per kind of wallet that sent today, our own named as ours, then the newcomers."""
    out = []
    ship = " and ".join(w.get("ships") or []) or "our cruise ships"
    for t, n in sorted(w["by"].items(), key=lambda kv: -kv[1]):
        who = WALLET_WHO.get(t, t).format(ship=ship)
        out.append(f"{n} of them: {who}" if len(w["by"]) > 1 else f"all of them: {who}")
    if w.get("new"):
        out.append(f"{plural(w['new'], 'wallet')} nobody had seen before")
    return out


PAGE_DAYS = int(os.environ.get("PAGE_REPEAT_DAYS", 30))   # a page shown in a post is not shown again for this long


def page_key(link: str | None) -> str | None:
    """The page a post points to, as its path ("/rules/"); None for the front page or another site (never blocked)."""
    if not link:
        return None
    u = urllib.parse.urlsplit(str(link))
    if u.netloc and u.netloc.split(":")[0] not in ("tauhud.com", "www.tauhud.com"):
        return None
    path = "/" + u.path.strip("/") + "/" if u.path.strip("/") else None
    return path


def page_recent(state: dict, link: str | None, now: float) -> bool:
    """True when a closer look, a planned spotlight or a site update showed this page within PAGE_DAYS days (11 Nov
    2026: the rules wall came as a new page, then again as "worth a look"; each source only knew its own posts)."""
    pages_seed(state)
    k = page_key(link)
    t = state["pages"].get(k) if k else None
    return bool(t) and now - t < PAGE_DAYS * 86400


def pages_seed(state: dict) -> None:
    """The first time: the pages the closer looks and planned posts already showed, from their own records."""
    if "pages" in state:
        return
    pages = state["pages"] = {}
    for kind in ("deepdives", "plan"):
        st = state.get(kind) or {}
        links = {q.get("id"): q.get("link") for q in st.get("posts") or [] if isinstance(q, dict)}
        for pid, t in {**(st.get("x_posted") or {}), **(st.get("posted") or {})}.items():
            k = page_key(links.get(pid))
            if k and t and t > pages.get(k, 0):
                pages[k] = t


def page_shown(state: dict, link: str | None, now: float) -> None:
    pages_seed(state)
    k = page_key(link)
    if k:
        state["pages"][k] = round(now)


SAID_DAYS, SAID_MAX = 7, 2   # a sentence the bot already said this often in this many days is left out


def said_key(text: str) -> str:
    """A sentence as a template: numbers and spacing do not make it new ("1 wallet …" and "2 wallets …" are the same)."""
    t = re.sub(r"<[^>]+>", "", html.unescape(text or "")).lower()
    t = re.sub(r"\b(are|were)\b", "is", re.sub(r"(\w{3,})s\b", r"\1", t))   # "1 wallet that is" = "3 wallets that are"
    return hashlib.sha1(re.sub(r"\s+", " ", re.sub(r"\d[\d,.]*", "#", t)).strip().encode()).hexdigest()[:16]


def said_often(state: dict, text: str, now: float) -> bool:
    """True when the bot said this sentence (as a template) SAID_MAX times in the last SAID_DAYS days (11 Nov 2026:
    the same "why it matters" four evenings in a row read as a machine). The post then says less instead."""
    seen = (state.get("said") or {}).get(said_key(text)) or []
    return sum(1 for t in seen if now - t < SAID_DAYS * 86400) >= SAID_MAX


def remember_said(state: dict, text: str, now: float) -> None:
    said = state.setdefault("said", {})
    for k in list(said):
        said[k] = [t for t in said[k] if now - t < SAID_DAYS * 86400]
        if not said[k]:
            del said[k]
    said.setdefault(said_key(text), []).append(now)


def today_why(r: dict, short: bool = False) -> str | None:
    """One sentence on what the day's numbers mean, from the facts only; None when there is nothing to say.
    `short`: the X wording."""
    if r.get("why_off"):
        return None   # said too often lately (said_often)
    w, pace = r.get("wallets"), r.get("pace")
    steady = bool(r["blocks"]) and pace is not None and pace <= 90 and not r.get("slow")
    if not r["blocks"]:
        return None   # the quiet lines say it
    rules = [h for h in r["events"] if h != RESTART_HEADLINE]
    if rules:
        return "A rule change on Tau is proposed, voted on and in force, no fork, no restart." if short else \
            "A rule change on Tau is proposed, voted on and in force without a fork or a restart; today's is above."
    if r["events"]:   # only the restart: say what it means, never the "no restart" line
        return "The testnet started over today: balances, rules and history began again from the starting state." if short else \
            "The testnet started over today: balances, rules and history began again from the starting state, so the numbers above count the new chain."
    if w and w.get("ratio") and w["ratio"] >= 1.5:
        kept = "the chain kept one block a minute" if steady else f"the chain slowed to one block every {round(pace)} seconds"
        return f"Each a real signed transaction the one validator checked; {kept}." if short else \
            f"Every one of these was a real signed transaction the single validator had to check, and {kept}."
    if outsiders_news(w):
        return outsiders_line(w, short)
    return None


def today_worth_posting(r: dict) -> bool:
    """A day with something to tell beyond the block count. Since 2 November 2026 a quiet day gets its post on Telegram
    all the same (people asked where the evening post was); see today_worth_x for X."""
    return bool(r["txs"] or r["practice"] or r["events"])


def today_worth_x(r: dict) -> bool:
    """X gets only a day worth telling: a rule event, no block at all, many more wallets than usual, or newcomers.
    An ordinary day with its usual wallets is Telegram's alone (since 6 November 2026; before, every day with a
    transaction went to X too)."""
    w = r.get("wallets")
    unusual = bool(w) and (bool(w.get("ratio")) and w["ratio"] >= 1.5 or w.get("new", 0) >= 3)
    return bool(r["events"]) or not r["blocks"] or unusual


def quiet_lines(r: dict) -> list[str]:
    """What a quiet day says instead of transactions: no block at all (since when), or blocks and nothing in them."""
    if r["blocks"]:
        return ["• no transactions: a quiet day, only empty blocks"]
    out = ["• no block in 24 hours: the testnet stood still"]
    if r.get("last_block"):
        ago = r["end"] - r["last_block"]
        when = findings.hm(r["last_block"], r["end"])
        out.append(f"• the last block was sealed {'on ' if ago >= 7200 else 'at '}{when}" + (f", {plural(int(ago // 3600), 'hour')} ago" if ago >= 7200 else ""))
    out.append("• Tau HUD keeps watching; the restart or the first new block gets a post of its own")
    return out


def today_lead(r: dict) -> str | None:
    """The one thing the day is about, told first (7 November 2026: the post read like a list of numbers); None on an
    ordinary day. Only facts the numbers below carry."""
    rules = [h for h in r["events"] if h != RESTART_HEADLINE]
    if RESTART_HEADLINE in r["events"]:
        return "The testnet started over today, and the chain runs again from block 1."
    if rules:
        return f"The day's news: {rules[0]}."
    w = r.get("wallets") or {}
    if w.get("ships"):
        return f"{' and '.join(w['ships'])} called at White Rabbit Key: simulated passengers, real transactions."
    if r.get("slow"):
        return "Blocks came slowly for a while today."
    if not r["blocks"]:
        return None
    return None


def today_text(r: dict) -> str:
    e = html.escape
    day = datetime.fromtimestamp(r["end"], timezone.utc)
    out = [REAL_LINE, f"📋 <b>Testnet today, {day.day} {day.strftime('%B')}</b>", ""]
    lead = today_lead(r)
    if lead:
        out += [e(lead), ""]
    pace = f", {'usually ' if r.get('slow') else ''}one every {round(r['pace'])} seconds" if r["pace"] else ""
    w = r.get("wallets")
    if w and w["total"]:
        out.append(f"<b>{e(wallets_head(w))}</b>")
        out.append(e(wallets_compact(w)))
        out.append("")
    if r["blocks"]:
        line = f"• {plural(r['blocks'], 'block')}{pace}"
        if r["txs"]:
            line += f", {plural(r['txs'], 'transaction')}" + ("" if w and w["total"] else f" from {plural(r['senders'], 'account')}")
        out.append(line)
    if r.get("slow"):
        sl = r["slow"]
        out.append(f"• slowest hour from {findings.hm(sl['at'])}: only {plural(sl['blocks'], 'block')}, about {sl['usual']} are usual")
    if not r["txs"] and not r["practice"]:
        out += [e(x) for x in quiet_lines(r)]
    for h in r["events"]:
        out.append(f"• {e(h)}")
    if r["practice"]:
        n = r["practice"]
        out.append(f"• {plural(n, 'practice vote')}: the rules in force were proposed again and agreed, so nothing changes"
                   + (f"; {e(r['practice_why'])}." if n > 1 and r.get("practice_why") else ".") + " You can try it on the Vote page.")
    if r["online"]:
        top = r.get("peak") or 0
        out.append(f"• {plural(r['online'], 'node')} online" + (f" now, up to {top} earlier today" if top > r["online"] else ""))
    why = today_why(r)
    if why:
        out += ["", "<b>Why it matters</b>", e(why)]
    for c in r["coming"]:
        out += ["", f"Coming up: {e(c['title'])} at block #{fmt_n(c['at'])}{e(c['eta'])}."]
    return "\n".join(out)


def today_x(r: dict) -> str:
    day = datetime.fromtimestamp(r["end"], timezone.utc)
    pace = f", one every {round(r['pace'])} seconds" if r["pace"] else ""
    w = r.get("wallets")
    out = [f"📋 Testnet today, {day.day} {day.strftime('%B')}"]
    if w and w["total"]:   # a spike names only its cause, so the meaning still fits
        spike = bool(w.get("ratio")) and w["ratio"] >= 1.5
        out.append(wallets_head(w, short=True) + ": " + ", ".join(wallets_short(w, 1 if spike else 2, new=not spike)) + ".")
    why = today_why(r, short=True)
    blocks = f"{plural(r['blocks'], 'block')}{pace}" + (f", {plural(r['txs'], 'transaction')}" if r["txs"] else "") if r["blocks"] else None
    # what fits goes in this order; the end is dropped first when room is short, so the meaning comes before the events
    # (each rule event had its own post when it happened) and, with the wallets told, before the block count
    if why and w and w["total"]:
        out += ["Why it matters: " + why] + ([blocks] if blocks else [])
    else:
        out += ([blocks] if blocks else []) + (["Why it matters: " + why] if why else [])
    if not r["txs"] and not r["practice"]:
        out += quiet_lines(r)[:2]
    out += [f"• {h}" for h in r["events"]]
    if r["practice"] and not (w and w["total"]):
        out.append(f"• {plural(r['practice'], 'practice vote')}, the rules stay as they are")
    out += [f"Coming up: {c['title']} at block #{fmt_n(c['at'])}{c['eta']}." for c in r["coming"][:1]]
    return x_post(out, f"{SITE}/", keep=2)


X_WHO = {"idni": "IDNI's test accounts", "bot": "our island bot", "cruise": "passengers of {ship} (ours, simulated)",
         "rabbit": "White Rabbit Key players", "agorzilla": "Agorzilla feeders", "tauhud": "sent from Tau HUD", "other": "not ours"}


GAMES = ("rabbit", "agorzilla", "tauhud", "bot")


def wallets_compact(w: dict) -> str:
    """Who sent, on one line (11 Nov 2026: seven bullets every evening): our simulated passengers, our games and bots,
    IDNI, everyone else, the newcomers. "38 simulated passengers of MS Dry Run (ours) · 12 in our games and bots ·
    7 IDNI test accounts · 1 from outside · 2 new"."""
    by, ship = w["by"], " and ".join(w.get("ships") or []) or "our cruise ships"
    games = sum(by.get(t, 0) for t in GAMES)
    parts = [f"{by['cruise']} simulated passengers of {ship} (ours)" if by.get("cruise") else None,
             f"{games} in our games and bots" if games else None,
             f"{by['idni']} IDNI test {'account' if by['idni'] == 1 else 'accounts'}" if by.get("idni") else None,
             f"{by['other']} from outside" if by.get("other") else None,
             f"{w['new']} new" if w.get("new") else None]
    return " · ".join(x for x in parts if x)


def wallets_short(w: dict, top: int = 3, new: bool = True) -> list[str]:
    """The `top` largest kinds for X, then the newcomers."""
    ship = " and ".join(w.get("ships") or []) or "our cruise ships"
    out = [f"{n} {X_WHO.get(t, t).format(ship=ship)}" for t, n in sorted(w["by"].items(), key=lambda kv: -kv[1])[:top]]
    if new and w.get("new"):
        out.append(f"{w['new']} new")
    return out


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
        for l in m["lines"]:   # one paragraph each, with air between them
            body += [f"• <a href=\"{e(l['link'])}\">{e(l['label'])}</a>: {e(l['text'])}", ""]
        return "\n".join([SITE_LINE, f"<b>{e(m['title'])}</b>", ""] + body
                         + [f"<a href=\"{e(SITE_LOG_LINK)}\">Every change in the Updates log</a>"])
    return "\n".join([SITE_LINE, f"<b>{e(m['title'])}</b>", "", e(m["text"]), "",
                      f"<a href=\"{e(m['link'])}\">Open it on {e(link_host(m['link']))}</a>"])


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


def digest_slot(t: float) -> float | None:
    """The latest weekly digest time (SITE_DIGEST_WEEKDAY at SITE_DIGEST_HOUR UTC) at or before t, within the last week."""
    d = datetime.fromtimestamp(t, timezone.utc).replace(hour=SITE_DIGEST_HOUR, minute=0, second=0, microsecond=0)
    d -= timedelta(days=(d.weekday() - SITE_DIGEST_WEEKDAY) % 7)
    if d.timestamp() > t:
        d -= timedelta(days=7)
    return d.timestamp()


def digest_x(items: list[dict]) -> str:
    """The smaller changes on X: how many, then a short line each, as many as fit."""
    return x_post([f"🛠 {plural(len(items), 'smaller change')} to Tau HUD"] + [f"• {i['area']}: {i['line']}" for i in items],
                  foot=X_SITE_NOTE)


def major_buttons(m: dict) -> dict:
    return {"inline_keyboard": [[{"text": "✨ Open it", "url": m["link"]}, {"text": "📜 All updates", "url": SITE_LOG_LINK}]]}


def digest_order(items: list[dict]) -> list[dict]:
    """What a visitor notices first: changes to the pages before the ones to the bot and the alerts, oldest first."""
    return sorted(items, key=lambda i: (str(i.get("area", "")).lower() in ("alerts", "bot", "infra", "server"), 0))


def digest_text(items: list[dict], lines: int | None = None) -> str:
    """The week's smaller changes, the ones a visitor notices first; more than `lines` are counted, not listed."""
    e = html.escape
    lines = SITE_DIGEST_LINES if lines is None else lines
    items, seen = digest_order(items), set()
    items = [i for i in items if not (i["line"].strip().lower() in seen or seen.add(i["line"].strip().lower()))]
    shown, rest = items[:lines], len(items) - lines
    head = f"<b>This week on Tau HUD: {plural(len(items), 'smaller change')}</b>"
    out = [DIGEST_LINE, head, ""] + [f"• <b>{e(i['area'])}</b>: {e(i['line'])}" for i in shown]
    if rest > 0:
        out.append(f"…and {rest} more in the Updates log.")
    out += ["", f"<a href=\"{e(SITE_LOG_LINK)}\">Read every change in the Updates log</a>"]
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
    out += ["", f"<a href=\"{e(SITE_LOG_LINK)}\">Every change in the Updates log</a>"]
    text = "\n".join(out)
    return text if len(text) <= 4000 or len(majors) <= 1 else catchup_text(majors[:-1])


def digest_buttons() -> dict:
    return {"inline_keyboard": [[{"text": "📜 Updates log", "url": SITE_LOG_LINK}]]}


def site_slot(t: float) -> float | None:
    """The latest SITE_SLOTS time at or before t, today or yesterday."""
    d0 = datetime.fromtimestamp(t, timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    return max((d + h * 3600 for d in (d0 - 86400, d0) for h in SITE_SLOTS if d + h * 3600 <= t), default=None)


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


# ---------------- a closer look at one page a day (assets/deepdives.json) ----------------
def deepdive_text(p: dict) -> str:
    e = html.escape
    out = [DEEPDIVE_LINE, f"<b>{e(p.get('title', ''))}</b>", ""]
    out += [e(x) for x in str(p.get("text", "")).split("\n") if x.strip()] or [""]
    if p.get("try"):
        out += ["", f"<b>Try it:</b> {e(p['try'])}"]
    return "\n".join(out)


def deepdive_buttons(p: dict) -> dict:
    return {"inline_keyboard": [[{"text": p.get("button") or f"Open {p.get('title', 'it')}", "url": site_link(p.get("link"))}]]}


def deepdive_x(p: dict) -> str:
    return x_post(list(p.get("x") or [p.get("title", ""), p.get("text", "")]), foot=DEEPDIVE_FOOT)


# ---------------- the Key Crier: the shared island's day (relay /isle) ----------------
# Names as rabbit/game.js gives them (CANDS and LAWS there; the relay keeps the keys only)
ISLAND_CANDS = {"marisol": "Marisol", "tobias": "Tobias", "baako": "Baako", "hana": "Hana"}
ISLAND_LAWS = {"night": "Night market every Friday", "quiet": "Quiet after ten in the evening",
               "reef": "Protect the reef: no big ships in the bay", "harbour": "A deep harbour for cruise ships",
               "boat": "A school boat every morning", "lunch": "Fresh fish for the school lunch",
               "concerts": "Beach concerts on Sundays", "road": "A road round the island",
               "copy": "A copy of the Book on the square", "tax": "A coconut tax for repairs"}
ISLAND_KINDS = {"talk": ("speech on the square", "speeches on the square"), "law": ("law passed", "laws passed"),
                "down": ("law voted down", "laws voted down"), "refused": ("law the Book refused", "laws the Book refused"),
                "lie": ("rumour on Radio Coco", "rumours on Radio Coco"), "fact": ("truth told on Radio Coco", "truths told on Radio Coco"),
                "deal": ("embassy envelope", "embassy envelopes"), "pact": ("pact at the bar", "pacts at the bar"),
                "broke": ("pact broken", "pacts broken")}
ISLAND_NUMBER_WORDS = {3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten", 14: "fourteen"}


def ordinal(n: int) -> str:
    return "every one" if n == 1 else f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def island_days_from(js: str | None) -> int | None:
    """The campaign's length as rabbit/game.js declares it (`const DAYS = 5`), None when not found."""
    m = re.search(r"\bDAYS\s*=\s*(\d+)", js or "")
    return int(m.group(1)) if m and 1 <= int(m.group(1)) <= 60 else None


def island_tally(d: dict | None, names: dict) -> list[tuple[str, int]]:
    out = sorted(((names.get(k, k), int(v)) for k, v in (d or {}).items() if v), key=lambda x: (-x[1], x[0]))
    return out


def island_kinds_line(kinds: dict | None, top: int = 3) -> str:
    parts = [f"{n} {ISLAND_KINDS[k][0] if n == 1 else ISLAND_KINDS[k][1]}" for k, n in
             sorted(((k, int(v)) for k, v in (kinds or {}).items() if v and k in ISLAND_KINDS), key=lambda x: (-x[1], x[0]))[:top]]
    return ", ".join(parts)


def island_week(last: dict | None, day: str) -> dict | None:
    """The governor's count for the week that ended on `day` (a Sunday), from the relay's `last`: None on any other day
    or when the relay has no verdict for that week (nobody finished a campaign: the island keeps its governor)."""
    if not isinstance(last, dict) or last.get("to") != day or last.get("governor") not in ISLAND_CANDS:
        return None
    wins = island_tally(last.get("wins"), ISLAND_CANDS)
    f, t = datetime.strptime(last["from"], "%Y-%m-%d"), datetime.strptime(day, "%Y-%m-%d")
    return {"id": last.get("id"), "governor": ISLAND_CANDS[last["governor"]], "wins": wins,
            "won": int((last.get("wins") or {}).get(last["governor"], 0)), "finished": int(last.get("finished", 0)),
            "campaigns": int(last.get("campaigns", 0)), "laws": [ISLAND_LAWS[l] for l in last.get("laws") or [] if l in ISLAND_LAWS],
            "span": f"{f.day} {f.strftime('%B')} to {t.day} {t.strftime('%B')}" if f.month != t.month else f"{f.day} to {t.day} {t.strftime('%B')}"}


def island_report(day: str, snap: dict, days: int) -> dict:
    """The lines of the Key Crier's report of one island day: `players` (that day's visitors) and `islanders`; on a
    Sunday `week` holds the governor's count that followed it (snap `last`, see island_week)."""
    p, isl = snap.get("players") or {}, snap.get("islanders") or {}
    wins, laws, played = island_tally(p.get("wins"), ISLAND_CANDS), island_tally(p.get("laws"), ISLAND_LAWS), island_tally(p.get("as"), ISLAND_CANDS)
    lines = []
    if p.get("campaigns"):
        line = f"{plural(p['campaigns'], 'campaign')} played"
        if p.get("finished"):
            line += f", {p['finished']} of them to the election" if p["finished"] < p["campaigns"] else ", every one to the election"
            if wins:
                line += ": " + ", ".join(f"{n} won {c}" for n, c in wins)
        lines.append(line)
    if p.get("moves"):
        lines.append(f"{plural(p['moves'], 'move')} by the players" + (f": {island_kinds_line(p.get('kinds'))}" if p.get("kinds") else ""))
    if laws:
        t, n = laws[0]
        lines.append(f"the law of the day: {t}" + (f", passed {plural(n, 'time')}" if n > 1 else ""))
    if played and len(played) > 1 and p.get("campaigns", 0) > 1:
        lines.append(f"most ran as {played[0][0]} ({plural(played[0][1], 'campaign')})")
    if isl.get("moves") and not p.get("moves"):   # our bot's own moves only on a day without players (11 Nov 2026: same line daily)
        ilaws = island_tally(isl.get("laws"), ISLAND_LAWS)
        lines.append(("the islanders kept their own politics going: " if not p.get("moves") else "the islanders made ")
                     + f"{plural(isl['moves'], 'move')} of their own" + (f", {plural(sum(n for _, n in ilaws), 'law')} passed" if ilaws else ""))
    d = datetime.strptime(day, "%Y-%m-%d")
    return {"day": day, "date": f"{d.day} {d.strftime('%B')}", "lines": lines, "players": bool(p.get("moves")),
            "days": days, "wins": wins, "campaigns": p.get("campaigns", 0), "finished": p.get("finished", 0),
            "moves": p.get("moves", 0), "law": laws[0][0] if laws else None, "week": island_week(snap.get("last"), day)}


def island_week_lines(w: dict) -> list[str]:
    """The governor's count as lines: who governs, on how many campaigns won, and the laws of the island this week."""
    out = [f"{w['governor']} governs the island this week: {plural(w['won'], 'campaign')} won of {w['finished']} that reached the election"
           + (f" ({w['campaigns']} played)" if w["campaigns"] > w["finished"] else "")]
    if len(w["wins"]) > 1:
        out.append("the count: " + ", ".join(f"{n} {c}" for n, c in w["wins"]))
    out.append(("laws of the island this week: " + "; ".join(w["laws"])) if w["laws"]
               else "no law of the island this week: none held at the end of enough campaigns")
    return out


def island_text(r: dict) -> str:
    e = html.escape
    w = r.get("week")
    out = [ISLAND_LINE]
    if w:
        out += [f"<b>The governor's count, {w['span']}</b>", ""] + [f"• {e(x)}" for x in island_week_lines(w)] + [""]
    out += [f"<b>{'Yesterday on the island' if r['players'] else 'A quiet day on the island'}, {r['date']}</b>", ""]
    out += [f"• {e(x)}" for x in r["lines"]]
    if not r["players"]:
        out.append("• no visitor made a move; the island waits for you")
    # one short line; how a campaign works is on the island's page (11 Nov 2026: a 90-word paragraph every Monday)
    out += ["", "<i>Every move is one real transaction on Tau Testnet Alpha, with test AGRS that have no value.</i>"]
    return "\n".join(out)


def island_buttons() -> dict:
    return {"inline_keyboard": [[{"text": "🐇 Play today's island", "url": ISLAND_LINK}]]}


def island_story(r: dict) -> str | None:
    """The day's story for X, or None: an election won by real players (who won), else a law they passed. A day of
    moves alone is no story; it stays on Telegram."""
    if r.get("wins"):
        won = sum(c for _, c in r["wins"])
        if won == 1:
            return f"{r['wins'][0][0]} won an island election"
        return f"{won} island elections won: " + ", ".join(f"{n} {c}" for n, c in r["wins"][:3])
    if r.get("law"):
        return f"New law of the island: {r['law']}"
    return None


def island_card(r: dict) -> list[str]:
    """The card on the Key Crier's picture: the same facts as the post, so the picture alone says why it matters."""
    w = r.get("week")
    if w:
        return [f"The governor's count, {w['span']}", f"{w['governor']} governs the island this week",
                f"{plural(w['won'], 'campaign')} won of {w['finished']}, every move a real transaction",
                "White Rabbit Key on Tau Testnet Alpha"]
    return [island_story(r) or f"Yesterday on the island, {r['date']}", f"{r['date']}: {plural(r['moves'], 'move')} by real players,",
            "each one a signed transaction on Tau Testnet Alpha", "White Rabbit Key · tauhud.com/rabbit"]


def island_picture(card: list[str] | None = None, name: str = "today.jpg") -> str | None:
    """The live island painting as a 1600x900 JPEG in ISLAND_PIC_DIR (with `card` when given), or None when there is no
    painting to make it from: then the post goes out without a picture rather than with an old one."""
    try:
        import island_pic
        os.makedirs(ISLAND_PIC_DIR, exist_ok=True)
        return island_pic.make(ISLAND_ART, os.path.join(ISLAND_PIC_DIR, name), card)
    except Exception as exc:  # noqa: BLE001 - no painting, a broken file: no picture, never a stale one
        log.warning("island picture: none made (%r)", exc)
        return None


def island_x(r: dict) -> str:
    w = r.get("week")
    if w:
        lines = [f"🐇 The Key Crier: the governor's count, {w['span']}",
                 f"{w['governor']} governs the island this week: {plural(w['won'], 'campaign')} won of {w['finished']} that reached the election."]
        if w["laws"]:
            lines.append("Laws of the island: " + "; ".join(w["laws"]) + ".")
        lines.append(f"Every campaign won is a ballot; every move a real transaction on Tau Testnet Alpha.")
        return x_post(lines, foot=ISLAND_FOOT)
    story = island_story(r)
    if story:   # what happened, then why it matters: the island's politics are real transactions anyone can check
        lines = [f"🐇 The Key Crier, {r['date']}: {story}.",
                 f"Every move behind it was a signed transaction on Tau Testnet Alpha ({plural(r['moves'], 'move')} by real players that day)."]
        if r.get("wins") and r.get("law"):   # the first to go when the post is too long
            lines.append(f"New law: {r['law']}.")
        return x_post(lines, keep=2, foot=ISLAND_FOOT)
    head = f"🐇 The Key Crier: yesterday on the island, {r['date']}"   # not posted on X (no story); --island-preview
    body = f"{plural(r['campaigns'], 'campaign')}. {plural(r['moves'], 'move')}, each a real transaction on Tau Testnet Alpha."
    return x_post([head, body], foot=ISLAND_FOOT)


# ---------------- outlets ----------------
# Every send records itself here, so the service can say when a channel last worked and why it last failed
# (posting.json for the site and `up`, a warning in the log after SILENCE_HOURS without a post). Found 2 November 2026:
# the channel can go quiet for days without one failure in the log when nothing is due, or when the keys are gone.
# The last good send and the last failure are kept in the state file too (KEPT), so a restart does not forget them: on
# 4 November 2026 the first check after `up` counted the silence from the service's very first start and warned
# "SILENT for 28 hours" although both channels had posted shortly before.
SENT: dict[str, dict] = {"telegram": {}, "x": {}}
SILENCE_HOURS = float(os.environ.get("SILENCE_HOURS", 26))
KEPT = ("last_ok", "last_error", "last_error_at")


def last_post(sent: dict, name: str, now: float | None = None) -> str:
    """When the alerts service last posted to a channel, in words, from the state file's record ("" when not recorded yet)."""
    t = (sent.get(name) or {}).get("last_ok")
    if not t:
        return ""
    s = max(0, (now if now is not None else time.time()) - t)
    return f"alerts service last posted {round(s / 60)} min ago" if s < 5400 else f"alerts service last posted {round(s / 3600)} h ago"


def note_send(name: str, ok: bool, err: str):
    d = SENT.setdefault(name, {})
    if ok:
        d["last_ok"] = round(time.time())
    else:
        d["last_error"], d["last_error_at"] = err, round(time.time())


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


# Every tauhud.com link the channel posts carries ?ref=tg-<kind> (7 November 2026), so the relay's visitor numbers
# (/visits/channel) show which kinds of post people open; maybe_clicks reads them each Sunday.
TG_KINDS = [("what it costs", "costs"), ("Testnet today", "today"), ("weekly recap", "recap"), ("a closer look", "deepdive"), ("worth a look", "deepdive"),
            ("new on the site", "site"), ("smaller site updates", "digest"), ("Key Crier", "island"), ("RULE CHALLENGE", "challenge"),
            ("First on the testnet", "firsts"), ("Firsts on the testnet", "firsts"), ("joined the Tau testnet", "nodes"),
            ("restarted", "restart"), ("health", "health"), ("IDNI", "idni"), ("blog", "blog"), ("Daily Consensus", "gazette"),
            ("White Rabbit Key", "rabbit"), ("TESTNET ALPHA", "chain")]
SITE_LINK_RE = re.compile(r"https://(?:www\.)?tauhud\.com(/[^\s\"'<>]*)?")


KINDS_PATH = os.environ.get("TG_KINDS_PATH", os.path.join(os.path.dirname(os.environ.get("STATE_PATH", "/state/alerts.json")) or "/state",
                                                         "tg-kinds.json"))
# Room between two posts on the same channel (13 November 2026: two blog articles went out on X twelve minutes apart):
# every post to the channel or @TauHUDcom is noted in last-posts.json (shared by the alerts and blog services), and an
# automatic post that is not urgent waits, or on X is left out, while the last one is younger than POST_GAP_MINUTES.
# Chain news (rule changes, findings), the ships' timed announcements and posts by hand never wait. 0 = no gap.
POST_GAP_MINUTES = float(os.environ.get("POST_GAP_MINUTES", 120) or 0)
LAST_POSTS_PATH = os.environ.get("LAST_POSTS_PATH", os.path.join(os.path.dirname(STATE_PATH) or "/state", "last-posts.json"))


def note_public_post(channel: str, now: float | None = None) -> None:
    """A post went out on this channel ("telegram" or "x"): its time, for post_gap_left."""
    try:
        with open(LAST_POSTS_PATH) as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d[channel] = round(now if now is not None else time.time())
    try:
        write_atomic(LAST_POSTS_PATH, json.dumps(d))
    except OSError as e:
        log.warning("last post not noted: %s", e)


def post_gap_left(channels=("telegram", "x"), now: float | None = None) -> float:
    """Seconds until the last post on any of these channels is POST_GAP_MINUTES old (0: free to post)."""
    if POST_GAP_MINUTES <= 0:
        return 0.0
    if isinstance(channels, str):
        channels = (channels,)
    try:
        with open(LAST_POSTS_PATH) as f:
            d = json.load(f)
    except (OSError, ValueError):
        return 0.0
    now = now if now is not None else time.time()
    last = max([float(d.get(c) or 0) for c in channels] or [0])
    return max(0.0, last + POST_GAP_MINUTES * 60 - now)


# Kinds that post less often by themselves when nobody opened their links for CLICKS_QUIET_DAYS (maybe_clicks); every
# change is written to the log ("tuned: …") and told to the owner privately. Chain news and the evening post never tune.
CLICKS_TUNABLE = ("deepdive", "digest")
CLICKS_QUIET_DAYS = int(os.environ.get("CLICKS_QUIET_DAYS", 28))
CLICKS_MIN_POSTS = int(os.environ.get("CLICKS_MIN_POSTS", 3))
CLICKS_WEEKDAY, CLICKS_HOUR = 6, int(os.environ.get("CLICKS_HOUR", 16))   # Sunday 16:00 UTC, a private note to the owner
POLL_ON = os.environ.get("TG_POLL", "true").lower() in ("1", "true", "yes")
POLL_WEEKDAY, POLL_HOUR = 2, int(os.environ.get("TG_POLL_HOUR", 16))       # Wednesday 16:00 UTC: which closer look comes next
POLL_OPEN = float(os.environ.get("TG_POLL_OPEN_SECONDS", 36 * 3600))        # closed at the first closer look after this
COSTS_ON = os.environ.get("COSTS_POST", "true").lower() in ("1", "true", "yes")
COSTS_HOUR = int(os.environ.get("COSTS_HOUR", 9))                           # the 1st of each month, 09:00 UTC
COSTS_URL = os.environ.get("COSTS_URL", f"{SITE}/assets/costs.json")
# the pictures painted with Google's Gemini API, measured by infra/rabbit-art/paint.py per month (tokens x list price)
GEMINI_USAGE_URL = os.environ.get("GEMINI_USAGE_URL", f"{NODE_PUBLIC}/rico/art/gemini-usage.json")
CUR = {"EUR": "€", "USD": "$"}


def note_kind(kind: str, now: float | None = None):
    """Count one channel post of this kind per UTC day (tg-kinds.json, kept 60 days), for maybe_clicks."""
    day = datetime.fromtimestamp(now or time.time(), timezone.utc).strftime("%Y-%m-%d")
    try:
        with open(KINDS_PATH) as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.setdefault(day, {})[kind] = d.get(day, {}).get(kind, 0) + 1
    for k in sorted(d)[:-60]:
        del d[k]
    try:
        write_atomic(KINDS_PATH, json.dumps(d, separators=(",", ":")))
    except OSError:
        pass


SHARED_KINDS = {"friend"}   # the wallet's "Pass it on" line (ref=friend) and its rule links (ref=preset-<id>): opens without a post of ours


def clicks_table(opens: dict, posts: dict, start: str) -> dict:
    """{kind: [posts, opens]} summed over the days from `start` (YYYY-MM-DD) on."""
    out: dict[str, list[int]] = {}
    for src, i in ((posts, 0), (opens, 1)):
        for day, kinds in src.items():
            if day >= start:
                for k, n in kinds.items():
                    out.setdefault(k, [0, 0])[i] += int(n or 0)
    return out


def clicks_text(week: dict, quiet: list[str], changes: list[str]) -> str:
    e = html.escape
    rows = sorted(week.items(), key=lambda kv: (-kv[1][1], kv[0]))
    out = ["📈 <b>Channel this week</b> (only you get this)", "Opens of tauhud.com from each kind of post, last 7 days:"]
    out += [f"• {e(k)}: {plural(o, 'open')} from a link people passed on, no post" if p == 0 and (k in SHARED_KINDS or k.startswith("preset-"))
            else f"• {e(k)}: {plural(p, 'post')}, {plural(o, 'open')}" for k, (p, o) in rows] or ["• no posts counted yet"]
    if changes:
        out += ["", "Changed by itself:"] + [f"• {e(c)}" for c in changes]
    if quiet:
        out += ["", "Posting less often now: " + ", ".join(e(q) for q in quiet)]
    return "\n".join(out)


def gemini_line(usage: dict | None, month: str) -> tuple[str, float] | None:
    """Last month's pictures from Google's Gemini API as measured by paint.py (gemini-usage.json): (line, US dollars),
    or None while nothing was measured yet (no file, or measuring began after that month)."""
    if not isinstance(usage, dict) or not usage.get("since") or usage["since"][:7] > month:
        return None
    m = (usage.get("months") or {}).get(month) or {}
    usd = round(float(m.get("usd") or 0), 2)
    name = datetime.strptime(month + "-01", "%Y-%m-%d").strftime("%B")
    since = f", measured since {int(usage['since'][8:10])} {name}" if usage["since"][:7] == month else ", measured"
    if not usd:
        return f"• Pictures (Google Gemini) in {name}: $0, nothing painted", 0.0
    n = int(m.get("pictures") or 0)
    return f"• Pictures (Google Gemini) in {name}: about ${usd:.2f} for {plural(n, 'picture')}{since}", usd


def anthropic_line(t: dict | None, month: str) -> tuple[str, float] | None:
    """Last month's answers from the Anthropic API (blog drafts, IDNI news and daily post, troll box check) as measured
    by ai_meter.py: (line, US dollars), or None while nothing was measured for that month."""
    if not t:
        return None
    name = datetime.strptime(month + "-01", "%Y-%m-%d").strftime("%B")
    since = f", measured since {int(t['since'][8:10])} {name}" if t["since"][:7] == month else ", measured"
    usd = round(float(t.get("usd") or 0), 2)
    if not t.get("answers"):
        return f"• AI writing (Anthropic API) in {name}: $0", 0.0
    return (f"• AI writing (Anthropic API: blog, IDNI news, chat check) in {name}: about ${usd:.2f} for "
            f"{plural(int(t['answers']), 'answer')}{since}"), usd


def costs_text(costs: dict | None, don: dict | None, gemini: dict | None = None, month: str = "",
               anthropic: dict | None = None) -> str | None:
    """The month's running costs as billed (assets/costs.json), last month's measured Gemini pictures (gemini-usage.json)
    and Anthropic API answers (ai_meter.totals), both for `month` (YYYY-MM), and what came in (donations.json); None
    without costs."""
    e = html.escape
    items = (costs or {}).get("items") or []
    billed = [i for i in items if isinstance(i.get("amount"), (int, float))]
    if not billed:
        return None
    by_cur: dict[str, float] = {}
    for i in billed:
        by_cur[i["cur"]] = by_cur.get(i["cur"], 0) + i["amount"]
    measured = [x for x in ((gemini_line(gemini, month), anthropic_line(anthropic, month)) if month else ()) if x]
    for _, usd in measured:
        if usd:
            by_cur["USD"] = round(by_cur.get("USD", 0) + usd, 2)
    total = " + ".join(f"{CUR.get(c, c + ' ')}{n:g}" for c, n in by_cur.items())
    out = ["💚 <b>TAU HUD · what it costs to run</b>", f"<b>About {e(total)} a month, not counting time</b>", ""]
    out += [f"• {e(i['t'])}: {CUR.get(i['cur'], i['cur'] + ' ')}{i['amount']:g}" for i in billed]
    out += [e(line) for line, _ in measured]
    open_bills = [i["t"] for i in items if i.get("amount") is None]
    if open_bills:
        out.append(f"• not in yet: {e(', '.join(open_bills))}")
    out.append("")
    if don and don.get("count"):
        tot = ", ".join(f"{v} {k}" for k, v in (don.get("totals") or {}).items())
        out.append(f"Donations so far: {plural(don['count'], 'donation')} from {plural(don.get('donors', 0), 'wallet')}"
                   + (f", {e(tot)}" if tot else "") + ". Thank you.")
    else:
        out.append("No donations yet.")
    out.append("Tau HUD is a community project, not affiliated with IDNI. Every bill is listed on the donation page.")
    return "\n".join(out)


def tg_kind(text: str) -> str:
    head = "\n".join(text.split("\n")[:3])
    return next((k for w, k in TG_KINDS if w.lower() in head.lower()), "post")


def tag_url(url: str, kind: str) -> str:
    """The same tauhud.com link with ref=tg-<kind> in its query, before any #fragment; a link already tagged stays."""
    if "ref=" in url:
        return url
    base, hash_, frag = url.partition("#")
    return f"{base}{'&' if '?' in base else '?'}ref=tg-{kind}{hash_}{frag}"


def tag_links(text: str, buttons: dict | None, kind: str) -> tuple[str, dict | None]:
    # only the targets of links (href) and buttons: a link written out as text stays as people read it
    text = re.sub(r'href="(https://(?:www\.)?tauhud\.com[^"]*)"', lambda m: f'href="{tag_url(m.group(1), kind)}"', text)
    if buttons:
        buttons = {"inline_keyboard": [[{**b, "url": tag_url(b["url"], kind)} if SITE_LINK_RE.fullmatch(b.get("url", "")) else b
                                        for b in row] for row in buttons.get("inline_keyboard", [])]}
    return text, buttons


def item_buttons(item: dict) -> dict:
    """Buttons that fit a chain event: a restart opens the wallet and the stats, a rule change its proposal and the Vote page."""
    if item.get("kind") == "restart":
        return {"inline_keyboard": [[{"text": "👛 Your wallet", "url": f"{SITE}/wallet/"}, {"text": "📊 Stats", "url": f"{SITE}/stats/"}]]}
    return {"inline_keyboard": [[{"text": "🗳 This rule change", "url": item.get("link") or f"{SITE}/proposals/"},
                                 {"text": "✋ Vote yourself", "url": f"{SITE}/vote/"}]]}


def link_buttons(*pairs: tuple[str, str]) -> dict:
    return {"inline_keyboard": [[{"text": t, "url": u} for t, u in pairs]]}


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
        if buttons is None and TELEGRAM_BOT_NAME:
            buttons = ask_buttons()
        kind = tg_kind(text)
        text, buttons = tag_links(text, buttons, kind)
        msg = {"chat_id": TELEGRAM_CHAT, "text": text, "parse_mode": "HTML", "link_preview_options": preview}
        if buttons is not None:
            msg["reply_markup"] = buttons
        body = json.dumps(msg).encode()
        res = self.call("sendMessage", body, "application/json")
        if res[0]:
            note_kind(kind)
        return res

    def send_photo(self, png, r):
        fields = {"chat_id": TELEGRAM_CHAT, "caption": recap_caption(r), "parse_mode": "HTML"}
        if TELEGRAM_BOT_NAME:
            fields["reply_markup"] = json.dumps(ask_buttons())
        body, ctype = multipart(fields,
                                {"photo": (f"tau-recap-{recap.week_key(r['end'] - 1)}.png", png, "image/png")})
        return self.call("sendPhoto", body, ctype)

    def call(self, method: str, body: bytes, ctype: str) -> tuple[bool, float | None, str]:
        res = self.call_raw(method, body, ctype)
        note_send(self.name, res[0], res[2])
        if res[0] and method.startswith("send"):
            note_public_post("telegram")
        return res[:3]

    def call_raw(self, method: str, body: bytes | None, ctype: str = "application/json") -> tuple[bool, float | None, str, dict]:
        """One Bot API call: (ok, retry_after, error text, the reply)."""
        req = urllib.request.Request(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}", data=body,
                                     headers={"Content-Type": ctype} if body else {})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                reply = json.load(r)
                ok = reply.get("ok", False)
                return ok, None, "" if ok else "not ok", reply
        except urllib.error.HTTPError as e:  # never log the URL: it holds the token
            try:
                info = json.load(e)
            except ValueError:
                info = {}
            retry = (info.get("parameters") or {}).get("retry_after")
            return False, float(retry) if retry else None, f"HTTP {e.code}: {info.get('description', '')}", info
        except (urllib.error.URLError, OSError) as e:
            return False, None, type(e).__name__, {}

    def check(self) -> tuple[bool, str]:
        """Can this bot post in the channel? Asks Telegram, posts nothing: the token (getMe), then the bot's standing in
        the channel (getChatMember), which must be administrator with the right to post."""
        if not self.enabled():
            return False, "off: TELEGRAM_BOT_TOKEN is not set in infra/.env"
        ok, _, err, me = self.call_raw("getMe", None)
        if not ok:
            hint = "; the token is wrong or revoked: make a new one with @BotFather and put it in infra/.env as TELEGRAM_BOT_TOKEN" \
                if err.startswith("HTTP 401") or err.startswith("HTTP 404") else ""
            return False, f"token refused ({err}){hint}"
        bot = me.get("result") or {}
        body = json.dumps({"chat_id": TELEGRAM_CHAT, "user_id": bot.get("id")}).encode()
        ok, _, err, m = self.call_raw("getChatMember", body)
        if not ok:
            return False, f"@{bot.get('username')} cannot see {TELEGRAM_CHAT} ({err}); add the bot to the channel as an administrator"
        r = m.get("result") or {}
        if r.get("status") == "creator" or (r.get("status") == "administrator" and r.get("can_post_messages", True)):
            return True, f"@{bot.get('username')} is an administrator of {TELEGRAM_CHAT} and may post"
        return False, f"@{bot.get('username')} is '{r.get('status')}' in {TELEGRAM_CHAT}, not an administrator who may post: " \
            "in the channel's Administrators, add the bot with Post messages"

    def send(self, item):
        return self.send_text(telegram_text(item), item_buttons(item))


def _pct(s: str) -> str:
    return urllib.parse.quote(s, safe="-._~")


class X(Outlet):
    """POST /2/tweets with OAuth 1.0a user context (the four keys of the app's
    user, made with Read and Write permission)."""
    name = "x"
    URL = "https://api.x.com/2/tweets"

    def __init__(self, keys: dict | None = None, prefix: str = ""):
        """keys: the four values under the names X_API_KEY … X_ACCESS_SECRET; default the @TauHUDcom ones from .env.
        prefix: what the names carry in .env for this account ("AGORZILLA_"), for the check's answer."""
        self.keys = keys if keys is not None else X_KEYS
        self.prefix = prefix

    def enabled(self) -> bool:
        return all(self.keys.values())

    def auth_header(self, url: str | None = None, method: str = "POST") -> str:
        oauth = {"oauth_consumer_key": self.keys["X_API_KEY"], "oauth_nonce": secrets.token_hex(16),
                 "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": str(int(time.time())),
                 "oauth_token": self.keys["X_ACCESS_TOKEN"], "oauth_version": "1.0"}
        # a JSON or multipart body is not part of the signature base
        params = "&".join(f"{_pct(k)}={_pct(v)}" for k, v in sorted(oauth.items()))
        base = "&".join([method, _pct(url or self.URL), _pct(params)])
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
        """The text with the picture at `picture` (a URL, or a file made here) when it can be read and uploaded, else the
        text alone."""
        png = (local_picture(picture) if picture.startswith("/") else fetch_picture(picture)) if picture and X_PICTURES else None
        media_id = self.upload(png)[0] if png else None
        if png and not media_id:
            log.info("x: picture %s not uploaded, posting the text alone", picture)
        return self.send_text(text, media_id)

    ME = "https://api.x.com/2/users/me"

    def check(self) -> tuple[bool, str]:
        """Do these keys open the account? GET /2/users/me, which posts nothing and is free."""
        if not self.enabled():
            p = self.prefix
            return False, f"off: {p}X_API_KEY, {p}X_API_SECRET, {p}X_ACCESS_TOKEN and {p}X_ACCESS_SECRET are not all set in infra/.env"
        req = urllib.request.Request(self.ME, headers={"Authorization": self.auth_header(self.ME, "GET")})
        ok, _, err, reply = self.call(req, want_reply=True, record=False)
        if ok:
            return True, f"keys open @{(reply.get('data') or {}).get('username', '?')}"
        return False, f"keys refused ({err})" + X_HINTS.get(err.split(":")[0], "").replace("\n   ", "; ")

    def call(self, req, want_reply=False, record=True):
        res = self.call_once(req, want_reply)
        if record:
            note_send(self.name, res[0], res[2])
            if res[0] and req.full_url == self.URL and not self.prefix:   # a post on @TauHUDcom (not Agorzilla's, not an upload)
                note_public_post("x")
        return res

    def call_once(self, req, want_reply=False):
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


def local_picture(path: str) -> bytes | None:
    """A PNG or JPEG made on this server (island_pic.py), at most 5 MB, or None."""
    try:
        with open(path, "rb") as f:
            data = f.read(5 * 2**20 + 1)
    except OSError as exc:
        log.info("x: no picture at %s (%r)", path, exc)
        return None
    ok = data[:8] == b"\x89PNG\r\n\x1a\n" or data[:3] == b"\xff\xd8\xff"
    return data if ok and len(data) <= 5 * 2**20 else None


def item_picture(item: dict) -> str:
    """A rule change: its own card (what it does, the votes, the countdown); a restart: the live overview."""
    pid = str(item.get("id") or "")
    return f"{SHARE_HTTP}/og/proposal/{pid}.png" if item.get("kind") != "restart" and re.fullmatch(r"[0-9a-f]{8,64}", pid) \
        else f"{SHARE_HTTP}/og/hud.png"


PAGESHOTS = os.path.join(PUBLIC_DIR, "pageshots")   # checked pictures of Tau HUD's pages (agorzilla-shots/site-shots.mjs)


def live_shot(link: str | None) -> str | None:
    """The checked picture of the page a post links to, as site-shots.mjs took it in Live mode after the live data came
    (green header, no "–", no simulation data), or None. 11 Nov 2026: a post carried the rules wall with a red header
    and the simulation's made-up wallets, a picture taken where our node could not be reached."""
    k = page_key(link)
    if k is None and link and urllib.parse.urlsplit(str(link)).path.strip("/") == "" and \
            urllib.parse.urlsplit(str(link)).netloc.split(":")[0] in ("", "tauhud.com", "www.tauhud.com"):
        k = "/"
    if not k:
        return None
    name = k.strip("/").replace("/", "-") or "hud"
    try:
        with open(os.path.join(PAGESHOTS, "index.json")) as f:
            e = json.load(f).get(name) or {}
    except (OSError, ValueError, AttributeError):
        return None
    if not e.get("ok") or not os.path.exists(os.path.join(PAGESHOTS, name + ".jpg")):
        return None
    return f"{NODE_PUBLIC}/pageshots/{name}.jpg?v={re.sub(r'[^0-9]', '', str(e.get('at')))[:12]}"


BLOG_IMG = os.path.join(PUBLIC_DIR, "blog", "img")   # the blog service's hero pictures (blog.py), node.tauhud.com/blog/img/
# a post about one blog article waits this long for the article's own picture, then goes without a picture
ARTICLE_WAIT_HOURS = float(os.environ.get("ARTICLE_PICTURE_WAIT_HOURS", 24))


def article_id(link: str | None) -> str | None:
    """The blog article a link opens (tauhud.com/blog/?p=<id>), or None."""
    u = urllib.parse.urlsplit(str(link or ""))
    if u.netloc and u.netloc.split(":")[0] not in ("tauhud.com", "www.tauhud.com"):
        return None
    if u.path.strip("/") != "blog":
        return None
    p = (urllib.parse.parse_qs(u.query).get("p") or [""])[0]
    return p if re.fullmatch(r"[\w-]{1,120}", p) else None


def article_picture(aid: str) -> str | None:
    """The article's own hero picture, once the blog service made it: it does so only after the article is on the site."""
    path = os.path.join(BLOG_IMG, aid + "-hero.jpg")
    if not os.path.exists(path):
        return None
    return f"{NODE_PUBLIC}/blog/img/{aid}-hero.jpg?v={int(os.path.getmtime(path))}"


def post_picture(image: str | None, link: str | None) -> str | None:
    """The picture a post about a Tau HUD page carries: the page's checked live picture; a screenshot or preview picture
    from the repo (assets/shots/, assets/og/, made without live data) never, then the post goes without one.
    Other pictures (paintings, blog pictures, cards) as they are. A post about one blog article carries that article's
    own picture or none: never the blog list's (13 Nov 2026: the personal-rules article went out with the list's picture,
    another article on it, because the site did not have the new one yet)."""
    aid = article_id(link)
    if aid:
        return article_picture(aid)
    shot = live_shot(link)
    if shot:
        return shot
    if not image or re.search(r"/assets/(shots|og)/", str(image)) or str(image).rstrip("/").endswith("/og.png"):
        return None
    return image


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
        self.started = time.time()   # a channel that never posted is silent from this start on, not from the first start ever
        for name, d in (self.state.get("sent") or {}).items():   # the last good send and failure, from before a restart
            if isinstance(d, dict):
                for k in KEPT:
                    if k in d:
                        SENT.setdefault(name, {}).setdefault(k, d[k])

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
        self.state["sent"] = {name: {k: d[k] for k in KEPT if k in d} for name, d in SENT.items()}
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
        self.note_firsts(chain)
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
            "firsts": firsts.public(self.state.get("firsts") or {}),
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
                if it["kind"] == "restart" and not self.restart_ready(it):
                    break  # wait for what the new chain brings (restart_brief.py), at most RESTART_BRIEF_WAIT_MINUTES
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

    def restart_ready(self, it: dict, now: float | None = None, brief: dict | None = None) -> bool:
        """A restart post goes out once devpulse has written what the new chain brings (restart_brief.py), with it in
        the post; after RESTART_BRIEF_WAIT_MINUTES without one, or once one outlet has posted it, as it is."""
        if it.get("brief") or any(v == "ok" for v in it["posted"].values()):
            return True
        now = now if now is not None else time.time()
        b = restart_brief.for_restart(it["seen"], brief)
        if b is None and now - it["seen"] < restart_brief.WAIT:
            return False
        it["brief"] = (b or {}).get("status") or "none"
        if b:
            it.update(restart_brief.apply(it, b))
            self.dirty_public = True
        log.info("restart post: %s", it["headline"] if it["brief"] == "ready" else f"short ({it['brief']})")
        self.save_state()
        return True

    # ---------- X: a few posts a day, paid per post ----------
    def x_on(self):
        return next((o for o in self.outlets if o.name == "x" and o.enabled()), None)

    def tg_on(self) -> list:
        return [o for o in self.outlets if o.name == "telegram" and o.enabled()]

    # At most one post a day about Tau HUD itself on Telegram (11 Nov 2026: a new-page post, a closer look, a "worth a
    # look" and a poll within eight hours read as an advert stream): a site update, a closer look or a planned spotlight
    # takes the day; the others wait (a closer look for the next day) or stay out (a spotlight). Chain news never waits.
    def promo_taken(self, now: float) -> bool:
        return self.state.get("promo_day") == datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")

    def promo_take(self, now: float) -> None:
        self.state["promo_day"] = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")

    def x_alone(self, st: dict, now: float) -> bool:
        """True when the X copy must not wait for Telegram: the channel is off, or its last send failed and it is
        pausing. Before 2 November 2026 one failing Telegram send held every X post back, and the account went quiet."""
        return not self.tg_on() or st.get("pause_until", 0) > now

    def x_room(self, now: float | None = None, spare: bool = False) -> bool:
        """True while today's and this month's X posts are under X_DAILY_CAP and X_MONTHLY_CAP; `spare` posts (the
        simulation, the smaller site changes) leave the day's last X_RESERVE for the real chain's news."""
        d = datetime.fromtimestamp(now if now is not None else time.time(), timezone.utc)
        st = self.state.setdefault("x", {})
        day, month = d.strftime("%Y-%m-%d"), d.strftime("%Y-%m")
        if st.get("day") != day:
            st["day"], st["today"] = day, 0
        if st.get("month") != month:
            st["month"], st["this_month"] = month, 0
        return st["today"] < X_DAILY_CAP - (X_RESERVE if spare else 0) and st["this_month"] < X_MONTHLY_CAP \
            and st.get("pause_until", 0) <= d.timestamp()

    def x_count(self):
        st = self.state["x"]
        st["today"], st["this_month"] = st.get("today", 0) + 1, st.get("this_month", 0) + 1

    async def post_x(self, text: str, what: str, now: float | None = None, picture: str | None = None, spare: bool = False,
                     urgent: bool = False) -> bool:
        """The X copy of a post that just went to Telegram. One try: X never holds Telegram up, and a post that failed is
        not sent hours late; over the caps, or within POST_GAP_MINUTES of the last X post (unless urgent), it is left out."""
        o = self.x_on()
        if not o:
            return False
        if not self.x_room(now, spare):
            log.info("x: %s not posted (daily or monthly cap, or paused)", what)
            return False
        gap = 0 if urgent else post_gap_left("x")
        if gap:
            log.info("x: %s left out (the last X post is younger than %g minutes)", what, POST_GAP_MINUTES)
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
            ok, _, err = await asyncio.to_thread(o.send_text, text, link_buttons(("🟢 Live status", f"{SITE}/status/"), ("💬 Ask the bot", f"https://t.me/{TELEGRAM_BOT_NAME}?start=status")))
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
        tg = self.tg_on()
        while st.get("outbox"):
            m = st["outbox"][0]
            if now - m["at"] > findings.OUTBOX_MAX_AGE or m["tries"] >= MAX_TRIES:
                log.info("finding %s not posted (%s)", m["what"], "too old or failed too often")
                st["outbox"].pop(0)
                continue
            if tg and not m.get("tg_done") and st.get("pause_until", 0) <= now:
                for o in tg:
                    ok, retry, err = await asyncio.to_thread(o.send_text, m["tg"])
                    if not ok:
                        m["tries"] += 1
                        st["pause_until"] = now + (retry or 60)
                        log.warning("finding post failed (%s); trying again later", err)
                        break
                else:
                    m["tg_done"] = True
            # the X copy once Telegram has it, or alone while Telegram is off or failing; once either way
            if m.get("x") and not m.get("x_done") and (m.get("tg_done") or self.x_alone(st, now)):
                m["x_done"] = True
                day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
                if st.get("x_day") != day:
                    st["x_day"], st["x_today"] = day, 0
                if st["x_today"] < findings.X_DAILY:
                    if await self.post_x(x_post(m["x"]), "finding " + m["what"], now, urgent=True):
                        st["x_today"] += 1
            if m.get("tg_done") or not tg:
                if not tg:
                    log.info("finding %s not posted to telegram (off)", m["what"])
                st["outbox"].pop(0)
                self.save_state()
                continue
            self.save_state()
            return  # Telegram failed just now: this finding waits, the ones behind it too

    # ---------- firsts: a kind of transaction the testnet never carried before ----------
    def note_firsts(self, chain: str):
        """Record the firsts in the blocks held (firsts.scan); new ones wait in pending for maybe_firsts. Silent on the
        first run, when what the chain holds is history."""
        if not firsts.FIRSTS_ON or not self.blocks:
            return
        st = self.state.setdefault("firsts", firsts.fresh_state())
        fresh = firsts.scan(st, self.blocks, chain)
        if not st["primed"]:
            st["primed"] = True
            return
        now = time.time()
        for f in fresh:
            log.info("first on the chain: %s in block %s", f["key"], f["h"])
            st["pending"].append({**f, "found": now})

    async def maybe_firsts(self, now: float | None = None):
        """One post for the firsts that arrived together: Telegram, then the X copy."""
        if not firsts.FIRSTS_ON:
            return
        now = now if now is not None else time.time()
        st = self.state.get("firsts")
        if not st or not st.get("pending") or st.get("pause_until", 0) > now:
            return
        tg = [o for o in self.outlets if o.name == "telegram" and o.enabled()]
        due = firsts.take(st, now, POST_MAX_AGE)
        if not due:
            self.save_state()
            return
        got = await asyncio.to_thread(self.relay_json, "/wallets/tags")
        tags = got.get("tags") if isinstance(got, dict) and isinstance(got.get("tags"), dict) else None   # unknown: claim nothing
        via = got.get("via") if isinstance(got, dict) and isinstance(got.get("via"), dict) else {}
        text = firsts.telegram_text(due, REAL_LINE, tags, via)
        first_tx = next((f["tx"] for f in due if f.get("tx")), None)
        buttons = link_buttons(("🔎 See it in the explorer", f"{SITE}/explorer/?tx={first_tx}" if first_tx else f"{SITE}/explorer/"),
                               ("📜 Rules wall", f"{SITE}/rules/"))
        pic = f"{NODE_PUBLIC}/og/block/{int(due[0]['h'])}.png"
        what = "firsts " + ", ".join(f["key"] for f in due)
        x_keys = sorted(f["key"] for f in due)
        for o in tg:
            ok, retry, err = await asyncio.to_thread(o.send_text, text, buttons, pic)
            if not ok:
                st["pending"] = due + st["pending"]
                st["tries"] = st.get("tries", 0) + 1
                if st["tries"] >= MAX_TRIES:
                    st["pending"], st["tries"] = [], 0
                    log.warning("firsts post failed %s times (%s); given up", MAX_TRIES, err)
                else:
                    st["pause_until"] = now + (retry or 60 * st["tries"])
                    log.warning("firsts post failed (%s); trying again later", err)
                if st.get("x_keys") != x_keys:   # X does not wait for a failing Telegram; once for these firsts
                    st["x_keys"] = x_keys
                    await self.post_x(x_post(firsts.x_lines(due)), what, now, f"{SHARE_HTTP}/og/hud.png")
                self.save_state()
                return
        st["tries"] = 0
        if tg:
            log.info("posted %s", what)
        else:
            log.info("%s not posted to telegram (off)", what)
        if st.get("x_keys") != x_keys:
            st["x_keys"] = x_keys
            await self.post_x(x_post(firsts.x_lines(due)), what, now, f"{SHARE_HTTP}/og/hud.png")
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
        """One Telegram post per check for the genuinely new nodes (see new_nodes); nodes
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
        day_now = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
        peak = st.setdefault("peak", {})
        peak[day_now] = max(peak.get(day_now, 0), nodes_online(peers, board))
        for d in sorted(peak)[:-3]:
            del peak[d]
        fresh = new_nodes(peers, board, known, now)
        if not st.get("primed"):
            for p in (peers or {}).get("peers") or []:
                known.setdefault("peer:" + p["id"], round(now))
            for n in (board or {}).get("nodes") or []:
                known.setdefault("kit:" + str(n.get("id")), round(now))
            st["primed"] = True
            self.save_state()
            return
        if not fresh:
            st.pop("waiting", None)
            self.save_state()
            return
        # nodes that arrive together are posted together: wait (at most NEWNODE_GROUP) while another one is about to qualify
        keys = {n["key"] for n in fresh}
        if NEWNODE_GROUP > 0 and any(n["key"] not in keys for n in new_nodes(peers, board, known, now, NEWNODE_GROUP)):
            st.setdefault("waiting", now)
            if now - st["waiting"] < NEWNODE_GROUP:
                self.save_state()
                return
        st.pop("waiting", None)
        day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
        tg = [o for o in self.outlets if o.name == "telegram" and o.enabled()]
        online = nodes_online(peers, board)
        posted = st.get("day") == day and st.get("posted", 0) or 0
        what = "new node " + " ".join(n["key"] for n in fresh)
        if posted < NEWNODE_DAILY_CAP:
            text = newnode_text(fresh, online)
            for o in tg:
                ok, _, err = await asyncio.to_thread(o.send_text, text, link_buttons(("🌐 All nodes", f"{SITE}/nodes/"), ("🛠 Run your own", "https://github.com/jimb000o/tau-command-hud/blob/main/kit/README.md")))
                if not ok:
                    log.warning("new node post failed (%s); trying again next check", err)
                    if fresh[0]["key"] not in st.setdefault("x_done", []):   # X does not wait for a failing Telegram
                        st["x_done"] = (st["x_done"] + [n["key"] for n in fresh])[-60:]
                        await self.post_x(newnode_x(fresh, online), what, now, f"{SHARE_HTTP}/og/hud.png")
                    self.save_state()
                    return
            st["day"], st["posted"] = day, posted + 1
            log.info("newnodes: posted %s%s", " ".join(keys), "" if tg else " (telegram off: X only)")
            if fresh[0]["key"] not in st.setdefault("x_done", []):
                st["x_done"] = (st["x_done"] + [n["key"] for n in fresh])[-60:]
                await self.post_x(newnode_x(fresh, online), what, now, f"{SHARE_HTTP}/og/hud.png")
        else:
            log.info("newnodes: %s recorded without a post (daily cap)", " ".join(keys))
        for n in fresh:
            known[n["key"]] = round(now)
        if len(known) > 5000:  # oldest first out; a key that comes back that late is not new news anyway
            for k in sorted(known, key=known.get)[:len(known) - 5000]:
                del known[k]
        self.save_state()

    # ---------- the simulation's consensus switches ----------
    async def maybe_sim(self, now: float | None = None):
        """One Telegram post per simulated consensus switch, sent while its proposal is open (the 10 minutes before it is
        in force). A switch missed while the service was down is skipped, never posted late. Pure clock work: no relay needed."""
        if not (SIM_ON and SIM_POSTS):
            return
        now = now if now is not None else time.time()
        st = self.state.setdefault("sim", {"posted": {}})
        st.setdefault("x_posted", {})
        tg = self.tg_on()
        changed = False
        for ev in sim_switches(now):
            if not (ev["proposed"] <= now < ev["in_force"]):
                continue
            key = ev["key"]
            if tg and key not in st["posted"] and st.get("pause_until", 0) <= now:
                text, buttons = sim_text(ev, await asyncio.to_thread(forecasts_for, ev)), sim_buttons()
                sent = True
                for o in tg:
                    ok, retry, err = await asyncio.to_thread(o.send_text, text, buttons)
                    if not ok:
                        st["pause_until"] = now + (retry or 60)
                        log.warning("simulation post failed (%s); trying again in a minute", err)
                        sent = changed = False
                        break
                if sent:
                    st["posted"][key] = round(now)
                    changed = True
                    log.info("simulation: posted %s", key)
            # the X copy with the Telegram post, or on its own while Telegram is off or failing; once either way
            if X_SIM and key not in st["x_posted"] and (key in st["posted"] or self.x_alone(st, now)):
                st["x_posted"][key] = round(now)
                changed = True
                await self.post_x(sim_x(ev), "simulation " + key, now, spare=True)
        for d in (st["posted"], st["x_posted"]):
            for k in [k for k, t in d.items() if now - t > 7 * 86400]:
                del d[k]
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
        if now < slot or now > slot + 3 * 3600:
            return
        tg = self.tg_on()
        tg_due = bool(tg) and st.get("slot", 0) < slot and st.get("pause_until", 0) <= now
        x_due = st.get("x_slot", 0) < slot and (st.get("slot", 0) >= slot or self.x_alone(st, now))
        if not tg_due and not x_due:
            return
        stats = await asyncio.to_thread(self.relay_json, "/stats")
        peers, board = await asyncio.to_thread(self.relay_json, "/peers"), await asyncio.to_thread(self.relay_json, "/community/board")
        online = nodes_online(peers, board) if peers is not None or board is not None else None
        r = today_numbers(stats, self.state["items"], getattr(self, "props", []), online, slot, self.last_block_time())
        active = await asyncio.to_thread(self.relay_json, "/wallets/active")
        ships = ships_in(await asyncio.to_thread(self.relay_json, "/cruise/log?n=300"), slot - 86400, slot) if active else []
        r["wallets"] = today_wallets(active, datetime.fromtimestamp(slot, timezone.utc).strftime("%Y-%m-%d"), ships)
        r["peak"] = (self.state.get("newnodes", {}).get("peak") or {}).get(datetime.fromtimestamp(slot - 1, timezone.utc).strftime("%Y-%m-%d"))
        why = today_why(r)
        if why and said_often(self.state, why, now):
            r["why_off"] = True
            log.info("testnet today: the why line was said too often lately, left out")
        if tg_due:
            for o in tg:
                ok, retry, err = await asyncio.to_thread(o.send_text, today_text(r), today_buttons())
                if not ok:
                    st["pause_until"] = now + (retry or 300)
                    log.warning("testnet today failed (%s); trying again later", err)
                    break
            else:
                log.info("testnet today posted%s", "" if today_worth_posting(r) else " (a quiet day)")
                if why and not r.get("why_off"):
                    remember_said(self.state, why, now)
                st["slot"] = slot  # recorded before X: a failed X copy must not repeat the Telegram post
        # the X copy once the Telegram post is out, or on its own while Telegram is off or failing; a quiet day with
        # blocks is Telegram's alone, a day without a block is news for X too
        if st.get("x_slot", 0) < slot and (st.get("slot", 0) >= slot or self.x_alone(st, now)):
            st["x_slot"] = slot
            if today_worth_x(r):
                await self.post_x(today_x(r), "testnet today", now, f"{SHARE_HTTP}/og/hud.png")
            else:
                log.info("testnet today: quiet day, Telegram only")
        self.save_state()

    # ---------- can the channels be posted to at all? ----------
    async def check_outlets(self):
        """Ask each channel, without posting, whether this service may post there; the answer goes to the log (a warning
        when not) and to posting.json next to proposals.json, where the site and `up` can read it."""
        for o in self.outlets:
            if not hasattr(o, "check"):
                continue
            ok, why = await asyncio.to_thread(o.check)
            SENT.setdefault(o.name, {})["check"] = {"ok": ok, "why": why, "at": round(time.time())}
            (log.info if ok else log.warning)("%s: %s%s", o.name, "ok, " if ok else "CANNOT POST: ", why)
        self.write_posting()

    def watch_silence(self, now: float | None = None):
        """Once an hour: a channel that is on and has not taken a post from this service for SILENCE_HOURS gets a warning in
        the log and in posting.json, so a quiet channel is noticed before someone asks. The last good send survives a
        restart (state "sent"); a channel with none recorded counts from this start. Only this service's own posts count:
        Agorzilla's evenings, the donation thanks and posts by hand (post_image.py, --test) run in processes of their own."""
        now = now if now is not None else time.time()
        st = self.state.setdefault("silence", {})
        st.pop("since", None)   # the first start ever, kept by the first version: the cause of the false warning
        if now - st.get("checked", 0) < 3600:
            return
        st["checked"] = now
        for o in self.outlets:
            if not o.enabled():
                continue
            d = SENT.setdefault(o.name, {})
            last = d.get("last_ok") or self.started
            if now - last >= SILENCE_HOURS * 3600:
                d["silent_hours"] = round((now - last) / 3600)
                log.warning("%s: silent, the alerts service has not posted here for %s hours (last error: %s)", o.name, d["silent_hours"], d.get("last_error") or "none logged")
            else:
                d.pop("silent_hours", None)
        self.write_posting()
        self.save_state()

    def write_posting(self):
        try:
            os.makedirs(PUBLIC_DIR, exist_ok=True)
            write_atomic(os.path.join(PUBLIC_DIR, "posting.json"),
                         json.dumps({"at": round(time.time()), "channels": SENT}, indent=1))
        except OSError as exc:
            log.warning("cannot write posting.json: %r", exc)

    def last_block_time(self) -> float | None:
        """When the newest block this service holds was sealed (None before the first sync)."""
        if not self.blocks:
            return None
        return ts_of(self.blocks[max(self.blocks)])


    # ---------- a closer look at one page a day (assets/deepdives.json) ----------
    def fetch_deepdives(self) -> list | None:
        try:
            req = urllib.request.Request(DEEPDIVE_URL, headers={"Cache-Control": "no-cache", "User-Agent": "tauhud-alerts"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            log.warning("deepdives: cannot read %s (%r)", DEEPDIVE_URL, exc)
            return None
        return [p for p in data.get("posts", []) if isinstance(p, dict) and p.get("id")] if isinstance(data, dict) else None

    async def maybe_deepdive(self, now: float | None = None, posts: list | None = None):
        """One closer look a day, the file's next one not yet posted, at DEEPDIVE_HOUR UTC (or within 3 h after it):
        Telegram with the page's picture and a button, X for every DEEPDIVE_X_EVERY-th one; X never waits for Telegram."""
        if not DEEPDIVE_ON:
            return
        now = now if now is not None else time.time()
        st = self.state.setdefault("deepdives", {"posted": {}, "x_posted": {}, "posts": [], "n": 0})
        if now - st.get("checked", 0) >= SITE_EVERY or posts is not None:
            st["checked"] = now
            posts = posts if posts is not None else await asyncio.to_thread(self.fetch_deepdives)
            if posts is not None:
                st["posts"] = posts
            self.save_state()
        slot = datetime.fromtimestamp(now, timezone.utc).replace(hour=DEEPDIVE_HOUR, minute=0, second=0, microsecond=0).timestamp()
        if now < slot or now > slot + 3 * 3600 or st.get("slot", 0) >= slot:
            return
        if datetime.fromtimestamp(slot, timezone.utc).weekday() not in DEEPDIVE_DAYS:
            return
        if "deepdive" in self.state.get("quiet_kinds", []) and int(slot // 86400) % 2:
            st["slot"] = slot   # nobody opened a closer look for weeks: every other one stays out (maybe_clicks)
            log.info("deepdive: skipped today, posting every other time (no opens)")
            self.save_state()
            return
        await self.close_poll(now)
        if st.get("current_slot") != slot and self.promo_taken(now):
            return   # Tau HUD had its post today; the closer look waits for the next day
        dpoll = datetime.fromtimestamp(slot, timezone.utc)
        if POLL_ON and dpoll.weekday() == POLL_WEEKDAY and (self.state.get("poll") or {}).get("week") != dpoll.strftime("%G-W%V") \
                and st.get("current_slot") != slot:
            return   # the poll day: the poll about the next closer look is the day's post
        tg = self.tg_on()
        # the day's post: the one started this slot (Telegram or X went first), else the file's next unposted one
        p = next((q for q in st["posts"] if q["id"] == st.get("current") and st.get("current_slot") == slot), None) \
            or next((q for q in st["posts"] if q["id"] == st.get("voted") and q["id"] not in st["posted"]), None) \
            or next((q for q in st["posts"] if q["id"] not in st["posted"] and q["id"] not in st["x_posted"]
                     and not page_recent(self.state, q.get("link"), now)), None)
        if not p:
            return
        pid = p["id"]
        pic = post_picture(site_link(p["image"]) if p.get("image") else None, p.get("link"))
        if tg and pid not in st["posted"] and st.get("pause_until", 0) <= now:
            text, buttons = deepdive_text(p), deepdive_buttons(p)
            for o in tg:
                ok, retry, err = await asyncio.to_thread(o.send_text, text, buttons, pic) if pic else \
                    await asyncio.to_thread(o.send_text, text, buttons)
                if not ok:
                    st["pause_until"] = now + (retry or 300)
                    log.warning("deepdive %s failed (%s); trying again later", pid, err)
                    break
            else:
                st["posted"][pid] = round(now)
                page_shown(self.state, p.get("link"), now)
                self.promo_take(now)
                st["current"], st["current_slot"] = pid, slot
                if pid not in st["x_posted"]:
                    st["n"] = st.get("n", 0) + 1
                log.info("deepdive: posted %s (%d so far)", pid, st["n"])
            self.save_state()
        if pid not in st["x_posted"] and (pid in st["posted"] or self.x_alone(st, now)):
            if pid not in st["posted"]:
                st["n"] = st.get("n", 0) + 1
                st["current"], st["current_slot"] = pid, slot
            st["x_posted"][pid] = round(now)
            self.save_state()
            if (st["n"] - 1) % DEEPDIVE_X_EVERY == 0:
                await self.post_x(deepdive_x(p), "deepdive " + pid, now, pic, spare=True)
            else:
                log.info("deepdive %s: Telegram only (X gets every %s one)", pid, ordinal(DEEPDIVE_X_EVERY))
        if pid in st["posted"] and pid in st["x_posted"]:
            st["slot"] = slot
        self.save_state()

    # ---------- IDNI's progress of the day, one post (idni_digest.py) ----------
    async def maybe_idni(self, now: float | None = None, digests: list | None = None, hold: dict | None = None):
        """The newest window devpulse wrote up and marked ready: Telegram, then X when it is notable; once each, at most
        one a UTC day, never later than IDNI_DIGEST_LATE_HOURS after the window's end; `up idni hold` keeps it back."""
        if not IDNI_ON:
            return
        now = now if now is not None else time.time()
        st = self.state.setdefault("idni", {"posted": {}, "x_posted": {}})
        if digests is None:
            if now - st.get("checked", 0) < 60:
                return
            st["checked"] = now
            digests, hold = idni_digest.load()["items"], idni_digest.held()
        hold = hold or {}
        day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
        d = next((x for x in reversed(digests) if x.get("id") == st.get("current")), None) if st.get("day") == day else None
        if d is None:
            if st.get("day") == day:
                return
            d = next((x for x in reversed(digests) if x.get("status") == "ready" and x.get("title")
                      and 0 <= now - x.get("end", 0) <= idni_digest.LATE and x["id"] not in st["posted"]
                      and x["id"] not in st["x_posted"]), None)
            if d is None:
                return
            if x_end := hold.get("until"):
                if d["end"] < x_end and not d.get("manual"):
                    return
        did = d["id"]
        tg = self.tg_on()
        if tg and did not in st["posted"] and st.get("pause_until", 0) <= now:
            text = idni_digest.tg_text(d)
            for o in tg:
                ok, retry, err = await asyncio.to_thread(o.send_text, text, None)
                if not ok:
                    st["pause_until"] = now + (retry or 300)
                    log.warning("idni digest %s failed (%s); trying again later", did, err)
                    break
            else:
                st["posted"][did] = round(now)
                st["day"], st["current"] = day, did
                log.info("idni digest: posted %s", d.get("title"))
            self.save_state()
        if did not in st["x_posted"] and (did in st["posted"] or self.x_alone(st, now)):
            st["x_posted"][did] = round(now)
            st["day"], st["current"] = day, did
            self.save_state()
            if d.get("x"):
                await self.post_x(x_post(idni_digest.x_lines(d), foot=idni_digest.X_FOOT, keep=2), "idni digest", now, spare=True)
            else:
                log.info("idni digest %s: Telegram only (a small day)", did)
        for k in ("posted", "x_posted"):
            st[k] = {i: t for i, t in st[k].items() if t >= now - 30 * 86400}
        self.save_state()

    # ---------- reported by us, solved by IDNI (fixwatch.py, written by devpulse into /state/devpulse/fixes.json) ----------
    async def maybe_fixed(self, now: float | None = None, post: dict | None = None):
        """The post fixwatch.py wrote and the owner approved (or auto mode did): Telegram, then X without a link; once
        each, not between 22:00 and 08:00 German time. Its id goes into this state, which is how fixwatch learns it went out."""
        now = now if now is not None else time.time()
        st = self.state.setdefault("fixed", {"posted": {}, "x_posted": {}})
        if post is None:
            if now - st.get("checked", 0) < 60:
                return
            st["checked"] = now
            post = fixwatch.load().get("post")
        if not post or post.get("status") != "approved" or fixwatch.quiet(now):
            return
        pid = post["id"]
        tg = self.tg_on()
        if tg and pid not in st["posted"] and st.get("pause_until", 0) <= now:
            for o in tg:
                ok, retry, err = await asyncio.to_thread(o.send_text, fixwatch.tg_text(post), None)
                if not ok:
                    st["pause_until"] = now + (retry or 300)
                    log.warning("fixed post %s failed (%s); trying again later", pid, err)
                    break
            else:
                st["posted"][pid] = round(now)
                log.info("fixed post: %s", post.get("title"))
            self.save_state()
        if pid not in st["x_posted"] and (pid in st["posted"] or self.x_alone(st, now)):
            st["x_posted"][pid] = round(now)
            st["posted"].setdefault(pid, round(now))
            self.save_state()
            await self.post_x(x_post(fixwatch.x_lines(post), foot=fixwatch.X_FOOT, keep=2), "fixed post", now, spare=True)
        self.save_state()

    # ---------- the Key Crier: White Rabbit Key's shared island, the day before (relay /isle) ----------
    async def maybe_island(self, now: float | None = None, snap: dict | None = None):
        """Keep the island's day as the relay sums it up (the last reading before midnight UTC is the day), and every
        morning at ISLAND_HOUR UTC report the day before: Telegram when a real player moved, the X copy only for a day with
        a story (island_story: an election won, a law passed) and at most every ISLAND_X_EVERY_DAYS days; X never waits for Telegram. On Monday the report
        opens with the governor's count of the week just ended (relay `last`), then goes out on X as well."""
        if not ISLAND_ON:
            return
        now = now if now is not None else time.time()
        if now - getattr(self, "island_pic_at", 0) >= ISLAND_PIC_EVERY or now < getattr(self, "island_pic_at", 0):
            self.island_pic_at = now   # the public copy (node.tauhud.com/island/today.jpg), made anew after each start
            await asyncio.to_thread(island_picture)
        st = self.state.setdefault("island", {"days": {}, "posted": {}, "x_posted": {}})
        if snap is not None or now - st.get("checked", 0) >= ISLAND_EVERY:
            st["checked"] = now
            snap = snap if snap is not None else await asyncio.to_thread(self.relay_json, "/isle")
            if isinstance(snap, dict) and snap.get("day"):
                st["days"][snap["day"]] = {"players": snap.get("players") or {}, "islanders": snap.get("islanders") or {}}
                if isinstance(snap.get("last"), dict):
                    for d in st["days"].values():   # the week's verdict, once the relay has decided it (Monday 00:00 German time)
                        d["last"] = snap["last"]
                for d in sorted(st["days"])[:-3]:
                    del st["days"][d]
            if now - st.get("length_at", 0) >= 86400:
                st["length_at"] = now
                st["length"] = await asyncio.to_thread(self.island_days) or st.get("length") or ISLAND_DAYS
            self.save_state()
        slot = datetime.fromtimestamp(now, timezone.utc).replace(hour=ISLAND_HOUR, minute=0, second=0, microsecond=0).timestamp()
        if now < slot or now > slot + 3 * 3600:
            return
        day = datetime.fromtimestamp(slot - 86400, timezone.utc).strftime("%Y-%m-%d")   # the day before, UTC like the relay
        d = st["days"].get(day)
        if not d or day in st["posted"] and day in st["x_posted"]:
            return
        r = island_report(day, d, st.get("length") or ISLAND_DAYS)
        if not r["players"] and not r["week"]:
            # nobody played: no report (since 6 November 2026; before, the islanders' own day was reported every morning)
            st["posted"][day] = st["x_posted"][day] = 0
            self.save_state()
            log.info("island %s: no visitor moved, no Key Crier", day)
            return
        tg = self.tg_on()
        if tg and day not in st["posted"] and st.get("pause_until", 0) <= now:
            for o in tg:
                ok, retry, err = await asyncio.to_thread(o.send_text, island_text(r), island_buttons())
                if not ok:
                    st["pause_until"] = now + (retry or 300)
                    log.warning("island report failed (%s); trying again later", err)
                    break
            else:
                st["posted"][day] = round(now)
                log.info("island: posted the Key Crier for %s", day)
            self.save_state()
        if day not in st["x_posted"] and (day in st["posted"] or self.x_alone(st, now)):
            last_x = max([t for t in st["x_posted"].values() if t], default=0)
            st["x_posted"][day] = round(now)
            self.save_state()
            if r["week"] or island_story(r) and (not last_x or (now - last_x) >= (ISLAND_X_EVERY_DAYS - 0.5) * 86400):
                pic = await asyncio.to_thread(island_picture, island_card(r), "crier.jpg")
                await self.post_x(island_x(r), "island " + day, now, pic, spare=True)
            else:
                st["x_posted"][day] = 0   # Telegram only: no election won and no law passed, or X had the island lately
                log.info("island %s: Telegram only", day)
        for k in ("posted", "x_posted"):
            for old in sorted(st[k])[:-14]:
                del st[k][old]
        self.save_state()

    def island_days(self) -> int | None:
        try:
            req = urllib.request.Request(ISLAND_GAME_JS, headers={"User-Agent": "tauhud-alerts"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return island_days_from(r.read(400_000).decode("utf-8", "replace"))
        except (urllib.error.URLError, OSError, ValueError):
            return None

    # ---------- posts planned ahead (assets/posts-plan.json) ----------
    def fetch_plan(self) -> list | None:
        try:
            req = urllib.request.Request(PLAN_URL, headers={"Cache-Control": "no-cache", "User-Agent": "tauhud-alerts"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            log.warning("plan: cannot read %s (%r)", PLAN_URL, exc)
            return None
        return [p for p in data.get("posts", []) if isinstance(p, dict)] if isinstance(data, dict) else None

    async def maybe_plan(self, now: float | None = None, posts: list | None = None):
        """Each planned post once, at its time: Telegram (with its picture and button), then X (one try, within the caps)."""
        if not PLAN_ON:
            return
        now = now if now is not None else time.time()
        st = self.state.setdefault("plan", {"posted": {}, "posts": []})
        if now - st.get("checked", 0) >= SITE_EVERY or posts is not None:
            st["checked"] = now
            posts = posts if posts is not None else await asyncio.to_thread(self.fetch_plan)
            if posts is not None:
                st["posts"] = posts
            self.save_state()
        tg = self.tg_on()
        st.setdefault("x_posted", {})
        for p in st["posts"]:
            try:
                at = datetime.fromisoformat(str(p["at"]).replace("Z", "+00:00")).timestamp()
            except (KeyError, ValueError):
                continue
            pid = p.get("id")
            if not pid or not (at <= now < at + PLAN_WINDOW):
                continue
            if pid not in st["posted"] and pid not in st["x_posted"] and str(pid).startswith("spot-") and p.get("link") \
                    and (page_recent(self.state, p.get("link"), now) or self.promo_taken(now)):
                st["posted"][pid] = st["x_posted"][pid] = round(now)   # the page was in a post lately: not again
                log.info("plan: %s skipped (page shown within %d days, or Tau HUD had its post today)", pid, PAGE_DAYS)
                self.save_state()
                continue
            pic = post_picture(site_link(p["image"]) if p.get("image") else None, p.get("link"))
            did = False
            if tg and p.get("tg") and pid not in st["posted"] and st.get("pause_until", 0) <= now:
                buttons = {"inline_keyboard": [[{"text": p.get("button") or "Open it", "url": site_link(p["link"])}]]} if p.get("link") else None
                if "{challenge}" in (p.get("tg") or ""):   # the week's task itself, so the post says what to write (7 Nov 2026)
                    p = {**p, "tg": p["tg"].replace("{challenge}\n\n", (self.challenge_line() + "\n\n") if self.challenge_line() else "").replace("{challenge}", "")}
                for o in tg:
                    ok, retry, err = await asyncio.to_thread(o.send_text, p["tg"], buttons, pic) if pic else \
                        await asyncio.to_thread(o.send_text, p["tg"], buttons)
                    if not ok:
                        st["pause_until"] = now + (retry or 300)
                        log.warning("plan: %s failed (%s); trying again later", pid, err)
                        break
                else:
                    st["posted"][pid] = round(now)
                    page_shown(self.state, p.get("link"), now)
                    if str(pid).startswith("spot-"):
                        self.promo_take(now)
                    did = True
                    log.info("plan: posted %s", pid)
                self.save_state()
            # the X copy with the Telegram post, or alone while Telegram is off or failing (or the post has no Telegram text)
            if p.get("x") and pid not in st["x_posted"] and (pid in st["posted"] or not p.get("tg") or self.x_alone(st, now)):
                st["x_posted"][pid] = round(now)
                did = True
                self.save_state()
                await self.post_x(x_post(p["x"], foot=p.get("foot") or PLAN_FOOT), "plan " + pid, now, pic)
            if did:
                return  # one planned post per check

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
        tg = self.tg_on()
        await self.maybe_digest(now, tg)
        slot = site_slot(now)
        if slot is None or now - slot >= SITE_SLOT_HOURS * 3600:
            return
        st.setdefault("x_done", [])   # majors X already has, so a Telegram retry never repeats them there
        tg_due = bool(tg) and st.get("pause_until", 0) <= now and st.get("slot", 0) < slot
        # Telegram off or failing: X takes this slot on its own (the Telegram post follows when the channel is back)
        x_alone = self.x_alone(st, now) and st.get("x_slot", 0) < slot
        if not tg_due and not x_alone:
            return
        if st["majors"]:
            # one post per slot: a single new page or feature on its own, several together, so none waits for another day
            batch = list(st["majors"])
            shown = 1 if len(batch) == 1 else catchup_text(batch).count("\n• ")
            if shown == 1 and not self.article_ready(st["majors"][0], now):
                return
            if tg_due:
                m = batch[0]
                sent = await self.site_send(tg, major_text(m), major_buttons(m), now, post_picture(m.get("image"), m.get("link"))) if shown == 1 else \
                    await self.site_send(tg, catchup_text(batch), digest_buttons(), now)
                if not sent:
                    return
                self.promo_take(now)
                for m in batch[:shown]:
                    page_shown(self.state, m.get("link"), now)
                del st["majors"][:shown]
                st["slot"], st["last_major"] = slot, round(now)
                log.info("site updates: posted %s", ", ".join(m["key"] for m in batch[:shown]))
            for_x = [m for m in batch[:shown] if m.get("x", True) and m["key"] not in st["x_done"]]  # "x": false: X by hand
            st["x_slot"] = slot
            self.save_state()
            if for_x:
                text_x = major_x(for_x[0]) if len(for_x) == 1 else catchup_x(for_x)
                st["x_done"] = (st["x_done"] + [m["key"] for m in for_x])[-60:]
                self.save_state()
                pic = next((p for p in (post_picture(m.get("image"), m.get("link")) for m in for_x) if p), None)
                await self.post_x(text_x, "site " + ", ".join(m["key"] for m in for_x), now, pic)
            self.save_state()
            return

    async def maybe_digest(self, now: float, tg: list):
        """The smaller changes of the week in one post at the weekly digest time (SITE_SLOT_HOURS after it, it is over
        and they wait for the next week); Telegram, and X only with SITE_DIGEST_X."""
        st = self.state["site"]
        ds = digest_slot(now)
        if not st["pending"] or ds is None or now - ds >= SITE_SLOT_HOURS * 3600:
            return
        if "digest" in self.state.get("quiet_kinds", []) and datetime.fromtimestamp(ds, timezone.utc).isocalendar()[1] % 2:
            return   # nobody opened the weekly digest for weeks: it comes every other week, the changes wait (maybe_clicks)
        tg_due = bool(tg) and st.get("pause_until", 0) <= now and st.get("digest_slot", 0) < ds
        x_due = SITE_DIGEST_X and st.get("x_digest_slot", 0) < ds and (st.get("digest_slot", 0) >= ds or self.x_alone(st, now))
        if not tg_due and not x_due:
            return
        items = list(st["pending"])
        keys = sorted(i.get("key", "") for i in items)
        if tg_due:
            if not await self.site_send(tg, digest_text(items), digest_buttons(), now):
                return
            log.info("site updates: the week's digest of %d posted", len(items))
            st["pending"], st["digest_slot"], st["last_digest"] = [], ds, round(now)
            x_due = SITE_DIGEST_X and st.get("x_digest_slot", 0) < ds
        if x_due:
            st["x_digest_slot"] = ds
            if st.get("x_digest") != keys:   # the same digest, sent alone to X earlier while Telegram failed, not again
                st["x_digest"] = keys
                self.save_state()
                await self.post_x(digest_x(items), "site digest", now, spare=True)
        self.save_state()

    def article_ready(self, m: dict, now: float) -> bool:
        """A post about one blog article waits until the article is on the site, which its own picture shows (the blog
        service makes it from the site's article list), at most ARTICLE_WAIT_HOURS; then it goes without a picture."""
        aid = article_id(m.get("link"))
        if not aid or article_picture(aid):
            return True
        if "waiting" not in m:
            m["waiting"] = round(now)
            log.info("site updates: %s waits for the article %s to be on the site", m.get("key"), aid)
            self.save_state()
        return now - m["waiting"] >= ARTICLE_WAIT_HOURS * 3600

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
    async def maybe_ticker(self):
        """The news line's watchtower (tickerwatch.py): is the HUD's news line still fresh? Tells the owner privately."""
        if not hasattr(self, "ticker_watch"):
            self.ticker_watch = tickerwatch.Watch()
        try:
            await asyncio.to_thread(self.ticker_watch.step)
        except Exception:  # noqa: BLE001 - the watchtower must never stop the alerts
            log.exception("news line watchtower")

    async def maybe_visitors(self, now: float | None = None, votes: dict | None = None):
        """One Telegram post per visitor proposal that was voted in with enough votes, at most VISITOR_DAILY_CAP a day,
        sent between the close of its vote and the moment it is in force; one missed while the service was down is skipped."""
        if not (SIM_ON and SIM_POSTS):
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
        chess = self.chess(r["end"])
        e = gazette.edition(r, props, days, no, printed_at, chess)
        e["chess"] = chess and {k: chess.get(k) for k in ("date", "played")}
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
        if RECAP_ON:
            try:
                await asyncio.to_thread(self.maybe_chess, now)
            except Exception as exc:
                log.warning("gazette: chess check failed (%r)", exc)
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

    def tell_owner(self, text: str) -> bool:
        """One message to the owner's private chat (up owner), never the channel."""
        chat, tg = tickerwatch.owner(), self.tg_on()
        if not chat or not tg:
            return False
        ok, _, err = tg[0].call("sendMessage", json.dumps({"chat_id": chat, "text": text, "parse_mode": "HTML",
                                                           "link_preview_options": {"is_disabled": True}}).encode(), "application/json")
        if not ok:
            log.warning("owner note failed (%s)", err)
        return ok

    async def maybe_clicks(self, now: float | None = None, opens: dict | None = None, posts: dict | None = None):
        """Sunday CLICKS_HOUR UTC: how often people opened tauhud.com from each kind of channel post (relay /visits/channel,
        links tagged ref=tg-<kind>), told to the owner privately. A tunable kind with CLICKS_MIN_POSTS posts and no open
        in CLICKS_QUIET_DAYS posts every other time; one open brings it back. Every change is logged ("tuned: …")."""
        now = now if now is not None else time.time()
        d = datetime.fromtimestamp(now, timezone.utc)
        st = self.state.setdefault("clicks", {})
        st.setdefault("since", now)
        week = d.strftime("%G-W%V")
        if d.weekday() != CLICKS_WEEKDAY or d.hour < CLICKS_HOUR or st.get("week") == week:
            return
        if opens is None:
            got = await asyncio.to_thread(self.relay_json, "/visits/channel")
            if not isinstance(got, dict):
                return
            opens = got.get("days") or {}
        if posts is None:
            try:
                with open(KINDS_PATH) as f:
                    posts = json.load(f)
            except (OSError, ValueError):
                posts = {}
        st["week"] = week
        day = lambda n: (d - timedelta(days=n)).strftime("%Y-%m-%d")
        seven, long = clicks_table(opens, posts, day(6)), clicks_table(opens, posts, day(CLICKS_QUIET_DAYS - 1))
        quiet, changes = list(self.state.get("quiet_kinds", [])), []
        if now - st["since"] >= CLICKS_QUIET_DAYS * 86400:   # only with data for the whole span
            for k in CLICKS_TUNABLE:
                p, o = long.get(k, [0, 0])
                if k not in quiet and p >= CLICKS_MIN_POSTS and o == 0:
                    quiet.append(k)
                    changes.append(f"{k} now every other time, because {plural(p, 'post')} in {CLICKS_QUIET_DAYS} days got no open")
                elif k in quiet and o > 0:
                    quiet.remove(k)
                    changes.append(f"{k} back to its usual pace, because people opened it {plural(o, 'time')}")
        for c in changes:
            log.info("tuned: %s", c)
        self.state["quiet_kinds"] = quiet
        self.state.setdefault("tuned", []).extend({"at": round(now), "what": c} for c in changes)
        self.state["tuned"] = self.state["tuned"][-50:]
        self.save_state()
        await asyncio.to_thread(self.tell_owner, clicks_text(seven, quiet, changes))

    async def maybe_poll(self, now: float | None = None):
        """Wednesday POLL_HOUR UTC: a native Telegram poll in the channel, which of the next closer looks comes next. The
        first closer look after POLL_OPEN closes it (close_poll) and posts the winner; no vote, the usual order."""
        if not POLL_ON or not DEEPDIVE_ON:
            return
        now = now if now is not None else time.time()
        d = datetime.fromtimestamp(now, timezone.utc)
        st = self.state.setdefault("poll", {})
        week = d.strftime("%G-W%V")
        if d.weekday() != POLL_WEEKDAY or not POLL_HOUR <= d.hour < POLL_HOUR + 3 or st.get("week") == week or st.get("open"):
            return
        dd = self.state.get("deepdives") or {}
        nxt = [q for q in dd.get("posts") or [] if q["id"] not in (dd.get("posted") or {})][:4]
        tg = self.tg_on()
        st["week"] = week
        if len(nxt) < 2 or not tg:
            self.save_state()
            return
        body = {"chat_id": TELEGRAM_CHAT, "question": "Which page of Tau HUD should get the next closer look?",
                "options": [{"text": str(q.get("title") or q["id"])[:100]} for q in nxt], "is_anonymous": True}
        ok, _, err, reply = await asyncio.to_thread(tg[0].call_raw, "sendPoll", json.dumps(body).encode())
        note_send("telegram", ok, err)
        if ok:
            st["open"] = {"msg": (reply.get("result") or {}).get("message_id"), "ids": [q["id"] for q in nxt], "at": round(now)}
            note_kind("poll", now)
            log.info("poll: asked which closer look comes next (%s)", ", ".join(st["open"]["ids"]))
        else:
            log.warning("poll failed (%s)", err)
        self.save_state()

    async def close_poll(self, now: float):
        """Close the open poll once it ran POLL_OPEN: the option with most votes (first on a tie) goes next; none, nothing."""
        st = self.state.get("poll") or {}
        op = st.get("open")
        if not op or now - op["at"] < POLL_OPEN:
            return
        tg = self.tg_on()
        st.pop("open", None)
        if not tg or not op.get("msg"):
            self.save_state()
            return
        ok, _, err, reply = await asyncio.to_thread(tg[0].call_raw, "stopPoll",
                                                    json.dumps({"chat_id": TELEGRAM_CHAT, "message_id": op["msg"]}).encode())
        counts = [o.get("voter_count", 0) for o in ((reply.get("result") or {}).get("options") or [])] if ok else []
        if counts and max(counts) > 0:
            win = op["ids"][counts.index(max(counts))]
            self.state.setdefault("deepdives", {})["voted"] = win
            log.info("poll: %s won with %s of %s votes", win, max(counts), sum(counts))
        else:
            log.info("poll: closed without votes%s", "" if ok else f" ({err})")
        self.save_state()

    async def maybe_costs(self, now: float | None = None, costs: dict | None = None, don: dict | None = None):
        """The 1st of each month at COSTS_HOUR UTC (within 3 h): the running costs as billed and the donations so far, on
        Telegram only; once a month."""
        if not COSTS_ON:
            return
        now = now if now is not None else time.time()
        d = datetime.fromtimestamp(now, timezone.utc)
        st = self.state.setdefault("costs", {})
        month = d.strftime("%Y-%m")
        if d.day != 1 or not COSTS_HOUR <= d.hour < COSTS_HOUR + 3 or st.get("month") == month:
            return
        tg = self.tg_on()
        if not tg:
            return
        if costs is None:
            costs = await asyncio.to_thread(self.fetch_json_url, COSTS_URL)
        if don is None:
            try:
                with open(os.path.join(PUBLIC_DIR, "donations.json")) as f:
                    don = json.load(f)
            except (OSError, ValueError):
                don = None
        last = (d.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        gemini = await asyncio.to_thread(self.fetch_json_url, GEMINI_USAGE_URL)
        text = costs_text(costs, don, gemini, last, await asyncio.to_thread(ai_meter.totals, last))
        st["month"] = month
        if text:
            ok, _, err = await asyncio.to_thread(tg[0].send_text, text, link_buttons(("💚 Support Tau HUD", f"{SITE}/donate/")))
            log.info("costs: %s", "posted" if ok else f"failed ({err})")
        self.save_state()

    def fetch_json_url(self, url: str):
        try:
            req = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "tauhud-alerts"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            log.warning("cannot read %s (%r)", url, exc)
            return None

    def challenge_line(self) -> str:
        """The open rule challenge in one Telegram line: its title and task; "" when none is open."""
        cur = self.state.get("challenge")
        if not cur:
            return ""
        try:
            c = gazette.challenge_block(cur["id"], cur["since"], cur["ends"])
        except (KeyError, ValueError, TypeError):
            return ""
        en = lambda v: v.get("en", "") if isinstance(v, dict) else str(v or "")
        return f"<b>This week's task, {html.escape(en(c['title']))}:</b> {html.escape(en(c['task']))}" if en(c["task"]) else ""

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

    def chess(self, end: float) -> dict | None:
        """The Taumorrow chess round of the week ending at end (gazette.CHESS_ROUNDS), with the result as last read from the records."""
        return gazette.chess_round(end, self.state.get("chess"))

    def chess_result(self, date: str) -> dict | None:
        """{date, played, engine, model, draws} of the round on date, read from the public records (a folder named …-<date>), or None."""
        api = "https://api.github.com/repos/taumorrow/taumorrow-chess-records/contents/"
        req = urllib.request.Request(api, headers={"User-Agent": "tauhud-alerts", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            dirs = [x["name"] for x in json.load(r) if x.get("type") == "dir" and x.get("name", "").endswith(date)]
        if not dirs:
            return None
        raw = f"https://raw.githubusercontent.com/taumorrow/taumorrow-chess-records/HEAD/{urllib.parse.quote(dirs[0])}/index.md"
        with urllib.request.urlopen(urllib.request.Request(raw, headers={"User-Agent": "tauhud-alerts"}), timeout=20) as r:
            score = gazette.chess_score(r.read().decode("utf-8", "replace"))
        return score and {"date": date} | score

    def maybe_chess(self, now: float):
        """Every half hour from a round's start until three days after: look for its result; when it changes, the café is told again."""
        st = self.state.setdefault("gazette", {})
        c = next((x for x in gazette.CHESS_ROUNDS if x["start"] <= now < x["start"] + 3 * 86400), None)
        if not c or now - st.get("chess_tried", 0) < 1800 or (self.state.get("chess") or {}).get("date") == c["date"] and \
                int(self.state["chess"].get("played") or 0) >= c["games"]:
            return
        st["chess_tried"] = now
        try:
            got = self.chess_result(c["date"])
        except Exception as exc:  # tried again in half an hour
            log.info("gazette: chess records not read (%r)", exc)
            return
        if got and got != self.state.get("chess"):
            self.state["chess"] = got
            log.info("gazette: chess round %s: %s", c["date"], got)
            self.gazette_cafe()
        self.save_state()

    def gazette_cafe(self):
        """Give the edition already out the café talk as it is written now: once per CAFE_V, and again when a chess result comes in."""
        d = os.path.join(PUBLIC_DIR, "recap", "gazette")
        try:
            with open(os.path.join(d, "latest.json")) as f:
                e = json.load(f)
        except (OSError, ValueError):
            return
        if not e.get("end"):
            return
        c = self.chess(e["end"])
        if e.get("cafe_v") == gazette.CAFE_V and (e.get("chess") or None) == (c and {k: c.get(k) for k in ("date", "played")}):
            return
        try:
            with open(os.path.join(PUBLIC_DIR, "proposals.json")) as f:
                props = json.load(f).get("proposals") or []
        except (OSError, ValueError):
            props = []
        r = self.recap_numbers(e["end"])
        days = [x for k, x in sorted((self.state.get("simdays") or {}).items())
                if r["start"] <= datetime.strptime(k, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() + 43200 < r["end"]]
        chess = self.chess(r["end"])
        e["cafe"] = gazette.cafe(r, props, days, e.get("no") or 1, e["banner"], e.get("teaser") or e["lead"]["deck"], chess)
        e["cafe_v"] = gazette.CAFE_V
        e["chess"] = chess and {k: chess.get(k) for k in ("date", "played")}
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
        if "r" not in st or time.time() - st["slot"] > RECAP_LATE:  # nothing drawn, or hours late: skip this week's post
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

    # ---------- the crew's ship log (crewlog.py): members-only, once a week after the recap ----------
    async def maybe_crewlog(self):
        """Post the week's ship log to the Tau HUD crew once the recap of the week is drawn (CREWLOG_ENABLED and the
        Fourthwall API user in .env); at most 3 tries a week, then it waits for the next week."""
        if not (crewlog.ON and crewlog.enabled()):
            return
        st = self.state.get("recap") or {}
        if "r" not in st or time.time() - st.get("slot", 0) > 24 * 3600:
            return
        cl = self.state.setdefault("crewlog", {})
        if cl.get("slot") == st["slot"] and (cl.get("id") or cl.get("tries", 0) >= 3 or cl.get("pause_until", 0) > time.time()):
            return
        if cl.get("slot") != st["slot"]:
            cl.clear()
            cl["slot"] = st["slot"]
        r = st["r"]
        try:
            title, desc, _ = await asyncio.to_thread(crewlog.gather, r, recap.lines(r, SITE), recap.period(r), SITE, paper_out(r))
            cl["id"] = await asyncio.to_thread(crewlog.post, title, desc, time.time()) or "posted"
            log.info("crew ship log posted (%s)", cl["id"])
        except Exception as exc:  # retried in 30 minutes
            cl["tries"] = cl.get("tries", 0) + 1
            cl["pause_until"] = time.time() + 1800
            log.warning("crew ship log failed: %s", crewlog.error_text(exc))
        self.save_state()

    async def maybe_earnings(self):
        """Our share of the shop's sales and the crew's memberships, for tauhud.com/donate/: read every 15 minutes once the
        Fourthwall API user is in .env (earnings.py); each new order and each new member is told to the owner privately."""
        if not crewlog.enabled() or not earnings.due():
            return
        try:
            names = {}
            try:
                names = {t["id"]: t["name"] for t in await asyncio.to_thread(crewlog.tiers)}
            except Exception:
                pass
            pub, _, added, lines = await asyncio.to_thread(earnings.run, None, names)
            log.info("earnings: %d day rows, %d new membership periods, %d new orders or members", len(pub["items"]), added, len(lines))
            for line in lines:
                self.tell_owner(html.escape(line))
        except Exception as exc:  # tried again on the next pass, 15 minutes later
            log.warning("earnings failed: %s", crewlog.error_text(exc))
            try:
                s = earnings.load(); s["checked"] = time.time(); earnings.write_atomic(earnings.STATE_PATH, json.dumps(s))
            except OSError:
                pass

    async def run(self):
        while True:
            try:
                async with connect(RELAY_URL, max_size=64 * 2**20, open_timeout=20) as ws:
                    self.ws = ws
                    log.info("connected to %s; telegram %s, x %s", RELAY_URL,
                             "on" if Telegram().enabled() else "off", "on" if X().enabled() else "off")
                    await self.check_outlets()
                    while True:
                        self.watch_silence()
                        if await self.sync() or self.dirty_public or not self.state["primed"]:
                            self.process()
                        await self.deliver()
                        await self.maybe_recap()
                        await self.maybe_crewlog()
                        await self.maybe_earnings()
                        await self.maybe_print()
                        await self.maybe_gazette()
                        await self.maybe_challenge()
                        await self.maybe_findings()
                        await self.maybe_firsts()
                        await self.maybe_health()
                        await self.maybe_newnodes()
                        await self.maybe_sim()
                        await self.maybe_site()
                        await self.maybe_plan()
                        await self.maybe_deepdive()
                        await self.maybe_idni()
                        await self.maybe_fixed()
                        await self.maybe_clicks()
                        await self.maybe_poll()
                        await self.maybe_costs()
                        await self.maybe_island()
                        await self.maybe_today()
                        await self.maybe_visitors()
                        await self.maybe_ticker()
                        await asyncio.sleep(POLL_SECONDS)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # relay restarting, network blip: try again shortly
                log.warning("relay connection lost (%r); retrying in 10 s", exc)
                await self.maybe_health()  # a relay that stays away is news too
                await self.maybe_sim()     # needs no relay
                await self.maybe_site()    # neither does this
                await self.maybe_plan()
                await self.maybe_deepdive()  # the site's pages are there whether the chain runs or not
                await self.maybe_idni()      # IDNI's code moves whether our relay answers or not
                await self.maybe_fixed()
                await self.maybe_clicks()
                await self.maybe_poll()
                await self.maybe_costs()
                await self.maybe_ticker()
                await asyncio.sleep(10)


def check_channels() -> int:
    """Each channel asked whether this service may post there, nothing posted: Telegram's token and the bot's right to
    post in the channel, Tau HUD's X keys, Agorzilla's X keys. Exit 1 when a channel that should post cannot."""
    code = 0
    agor = {k: os.environ.get("AGORZILLA_" + k, "").strip() for k in X_KEYS}
    try:   # when the running service last posted to each of its channels (Agorzilla's account is posted by its own service)
        with open(STATE_PATH) as f:
            sent = json.load(f).get("sent") or {}
    except (OSError, ValueError):
        sent = {}
    for key, name, o in (("telegram", "telegram", Telegram()), ("x", "x @TauHUDcom", X()), (None, "x @Agorzilla", X(agor, "AGORZILLA_"))):
        ok, why = o.check()
        last = last_post(sent, key) if key and o.enabled() else ""
        print(f"{name}: {'ok' if ok else 'CANNOT POST'}, {why}" + (f"; {last}" if last else ""))
        code |= 0 if ok else 1
    return code


def send_test() -> int:
    """One test line to the owner's private chat (up owner), never to the public channel or X: a test post on the
    channel (3 November 2026) read as a second "alerts are connected" to every follower. --check tests X without posting."""
    o = Telegram()
    if not o.enabled():
        print("telegram: off (credentials not set in .env)")
        return 1
    chat = tickerwatch.owner()
    if not chat:
        print("telegram: no private chat known yet; run up owner first (the test never goes to the channel)")
        return 1
    body = json.dumps({"chat_id": chat, "text": "✅ Tau HUD alerts can post. This test went only to you, not to the channel."}).encode()
    ok, _, err = o.call("sendMessage", body, "application/json")
    print(f"telegram (your private chat): {'sent' if ok else 'FAILED ' + err}")
    print("x: not posted; alerts.py --check tests the X keys without a post")
    return 0 if ok else 1


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


def deepdives_preview() -> int:
    """The closer looks still to come, in order, as Telegram and X would get them."""
    posts = Watcher([]).fetch_deepdives()
    if posts is None:
        print(f"cannot read {DEEPDIVE_URL}")
        return 1
    st = Watcher([]).state.get("deepdives") or {}
    for i, p in enumerate(q for q in posts if q["id"] not in (st.get("posted") or {})):
        x = deepdive_x(p)
        on_x = (st.get("n", 0) + i) % DEEPDIVE_X_EVERY == 0
        print(f"[{p['id']}]\n{deepdive_text(p)}\n" + (f"--- X ({x_len(x)}/280):\n{x}\n" if on_x else "--- Telegram only\n") + "-" * 60)
    return 0


def island_preview() -> int:
    """The Key Crier's report of the island's day so far, as Telegram and X would get it."""
    snap = Watcher([]).relay_json("/isle")
    if not isinstance(snap, dict) or not snap.get("day"):
        print(f"cannot read {RELAY_HTTP}/isle")
        return 1
    r = island_report(snap["day"], snap, Watcher([]).island_days() or ISLAND_DAYS)
    x = island_x(r)
    print(island_text(r) + f"\n--- X ({x_len(x)}/280){'' if r['players'] else ', not sent: no player moved'}:\n{x}")
    return 0


def plan_preview() -> int:
    """The planned posts still to come, as Telegram and X would get them."""
    posts = Watcher([]).fetch_plan()
    if posts is None:
        print(f"cannot read {PLAN_URL}")
        return 1
    now = time.time()
    for p in sorted(posts, key=lambda p: str(p.get("at"))):
        if datetime.fromisoformat(str(p["at"]).replace("Z", "+00:00")).timestamp() + PLAN_WINDOW < now:
            continue
        x = x_post(p["x"], foot=p.get("foot") or PLAN_FOOT) if p.get("x") else None
        print(f"[{p['at']} · {p['id']}]\n{p['tg']}\n" + (f"--- X ({x_len(x)}/280):\n{x}\n" if x else "--- not on X\n") + "-" * 60)
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
    print("--- Telegram:\n" + recap_caption(r) + "\n--- X:\n" + recap_x(r))
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


def crewlog_cli(send: bool) -> int:
    """The crew's ship log of the 7 days up to now: checks the Fourthwall API user (tiers, the newest posts as stored),
    prints the post; send=True posts it now, members only."""
    print(f"crew:    weekly post {'ON' if crewlog.ON else 'off'} (CREWLOG_ENABLED in .env), API user {'set' if crewlog.enabled() else 'NOT set (FOURTHWALL_API_USER / FOURTHWALL_API_PASS in .env)'}")
    if crewlog.enabled():
        try:
            for t in crewlog.tiers():
                print(f"tier:    {t['name']} (id {t['id']}, {t['status'] or 'status ?'}): {t['members'] if t['members'] is not None else '?'} members")
                print(f"         monthly {', '.join(f'{c} {v}' for c, v in (t.get('monthly') or {}).items()) or '?'} (as stored, before tax) · {str(t.get('description') or '')[:300]!r}")
        except Exception as exc:
            print(f"crew:    the Fourthwall API answered with an error: {crewlog.error_text(exc)}")
            return 1
        try:   # the newest posts as stored: only a look at how Fourthwall keeps the text, the draft does not need it
            for p in crewlog.posts():
                print(f"post:    {p.get('id')} {p.get('liveAt', '')} “{p.get('title', '')}” stored as: {str(p.get('description', ''))[:160]!r}")
        except Exception as exc:
            print(f"post:    the list of posts could not be read ({crewlog.error_text(exc)})")
    w = Watcher()
    try:
        r = w.recap_numbers(time.time())
    except Exception as exc:
        print(f"crew:    no recap numbers ({exc})")
        return 1
    title, desc, crew = crewlog.gather(r, recap.lines(r, SITE), recap.period(r), SITE, paper_out(r))
    shown = re.sub(r'<a href="([^"]+)">([^<]*)</a>', r"\2 (\1)", re.sub(r"<br>|</p>", "\n", desc))
    print(f"--- {title} (members only)\n" + html.unescape(re.sub(r"<[^>]+>", "", shown)))
    if not send:
        print("--- dry run: nothing posted. Post this one now: up crewlog send · weekly by itself: up crewlog on")
        return 0
    if not crewlog.enabled():
        return 1
    try:
        pid = crewlog.post(title, desc, time.time())
    except Exception as exc:
        print(f"crew:    posting FAILED: {crewlog.error_text(exc)}")
        return 1
    print(f"crew:    posted, members only (post {pid})")
    return 0


def earnings_cli() -> int:
    """Reads the shop now: every order's numbers beside the share worked out (to compare with Fourthwall's dashboard),
    the membership periods counted, and what tauhud.com/donate/ gets; writes earnings.json."""
    if not crewlog.enabled():
        print("earnings: API user NOT set (up crewlog key)")
        return 1
    print(f"fees:    card {earnings.CARD_PCT} % + {earnings.CARD_FIX:.2f} per payment, memberships {earnings.CREW_PCT} %, "
          f"shop cut {earnings.SHOP_PCT} % on top of the base cost (EARNINGS_* in .env to change)")
    try:
        try:
            names = {t["id"]: t["name"] for t in crewlog.tiers()}
        except Exception:
            names = {}
        pub, shop, added, lines = earnings.run(None, names)
    except Exception as exc:
        print(f"earnings: the Fourthwall API answered with an error: {crewlog.error_text(exc)}")
        return 1
    for o in shop:
        print(f"order:   {o['on']} {o['cur']} items {o['subtotal']:.2f} - discount {o['discount']:.2f} - cost {o['cost']:.2f}"
              f" - cut {o['cut']:.2f} + tip {o['tip']:.2f} - card fee {o['fee']:.2f} (buyer paid {o['total']:.2f}) = our share {o['share']:.2f}")
    if not shop:
        print("order:   none yet (cancelled orders, samples and giveaways do not count)")
    s = earnings.load()
    n = sum(len(v) for v in (s.get("crew") or {}).values())
    print(f"crew:    {n} membership periods counted, {added} new now")
    w = Watcher() if lines else None
    for line in lines:
        print(f"new:     {line} · your private Telegram chat: {'sent' if w.tell_owner(html.escape(line)) else 'NOT sent (up owner)'}")
    sums = {}
    for i in pub["items"]:
        k = (i["kind"], i["cur"]); sums[k] = sums.get(k, 0) + i["amount"]
    print("total:   " + (", ".join(f"{k} {c} {v:.2f}" for (k, c), v in sorted(sums.items())) or "nothing yet")
          + " · public: https://node.tauhud.com/earnings.json (per day, no names)")
    return 0


def repic_cli(args: list[str]) -> int:
    """A site-update post already on Telegram gets its right picture, in place, no new post: up idni repic <the post's
    t.me link or number> <the major's id in assets/updates.json>. 13 Nov 2026: the personal-rules article went out with
    the blog list's picture (post_picture now gives an article its own). X cannot be edited."""
    num = re.search(r"(\d+)\s*$", args[0]) if args else None
    want = args[1] if len(args) > 1 else ""
    e = next((x for x in (Watcher([]).fetch_updates() or []) if isinstance(x.get("major"), dict) and x["major"].get("id") == want), None)
    if not num or not e:
        print("usage: up idni repic <https://t.me/<channel>/<number>> <major id from assets/updates.json>"
              + ("" if not num else f"\n(no major named {want!r} in the site's update log)"))
        return 2
    m = major_item(e)
    pic = post_picture(m.get("image"), m.get("link"))
    if not pic:
        print("no right picture for it yet (an article: up blog pictures first, once the article is on the site); nothing changed")
        return 1
    text, buttons = major_text(m), major_buttons(m)
    text, buttons = tag_links(text, buttons, tg_kind(text))
    msg = {"chat_id": TELEGRAM_CHAT, "message_id": int(num.group(1)), "text": text, "parse_mode": "HTML",
           "link_preview_options": {"url": pic, "prefer_large_media": True, "show_above_text": True}, "reply_markup": buttons}
    ok, _, err = Telegram().call("editMessageText", json.dumps(msg).encode(), "application/json")
    print(f"telegram post {num.group(1)}: picture is now {pic}" if ok else f"telegram said no: {err}")
    return 0 if ok else 1


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if "--repic" in sys.argv:
        sys.exit(repic_cli(sys.argv[sys.argv.index("--repic") + 1:]))
    if "--test" in sys.argv:
        sys.exit(send_test())
    if "--earnings" in sys.argv:
        sys.exit(earnings_cli())
    if "--crewlog" in sys.argv:
        sys.exit(crewlog_cli("send" in sys.argv))
    if "--check" in sys.argv:
        sys.exit(check_channels())
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
    if "--plan-preview" in sys.argv:
        sys.exit(plan_preview())
    if "--deepdives-preview" in sys.argv:
        sys.exit(deepdives_preview())
    if "--island-preview" in sys.argv:
        sys.exit(island_preview())
    if "--site-preview" in sys.argv:
        sys.exit(site_preview())
    if "--findings-preview" in sys.argv:
        sys.exit(asyncio.run(findings_preview()))
    asyncio.run(Watcher().run())

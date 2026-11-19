"""Rules people write on the chain, told on the channels (Kilian, 19 November 2026: rules got added to the chain and the
channels barely said so).

On Tau a wallet is an account with rules the chain itself checks; that is the testnet's whole point, so a person writing
a new rule is news. The relay's /rulewall lists every personal rule in the blocks it keeps, with who wrote it ("by":
people, ours or idni, as /rules/numbers counts them) and what it checks ("kinds", ruledays.py). From it:

  Telegram, once a day at RULES_HOUR UTC, only on a day with news: every rule text people wrote that the testnet had never
          carried before, in plain words (what it stops), with its block, and how many wallets took it so far.
  X, once a week (RULES_WEEK_DAY at RULES_WEEK_HOUR UTC), only with news: why it matters first, then how many new rules
          people wrote that week and the one most taken, in plain words, with the rules wall's link.

A rule text is news once, ever: after a testnet restart people sign the same rules again, and that is no news (the same
lesson as the firsts, firsts.py). Rules our own server's wallets (cruise passengers, the island bot, the showcase
wallets) or IDNI's genesis accounts write are never told as people's; their texts count as known, so a person taking one
later is no new rule either. The first run only remembers what the wall holds: that is history.
"""
from __future__ import annotations

import hashlib
import html
import os
import re
from datetime import datetime, timezone

import gazette

SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
ON = os.environ.get("RULE_POSTS", "true").lower() in ("1", "true", "yes")
EVERY = float(os.environ.get("RULE_POSTS_POLL_SECONDS", 600))
HOUR = int(os.environ.get("RULES_HOUR", 17))                   # UTC (18:00 German winter time)
WEEK_DAY = int(os.environ.get("RULES_WEEK_DAY", 6))            # 0 = Monday: Sunday
WEEK_HOUR = int(os.environ.get("RULES_WEEK_HOUR", 16))         # UTC (17:00 German winter time)
FRESH = 2 * 86400        # a rule whose first block is older (caught up after an outage) is remembered, never told late
MAX_LINES = 4            # rules named in one Telegram post; the rest are counted
WALL = f"{SITE}/rules/"

# what a rule checks (ruledays.KINDS), for a rule the wallet's reading (gazette.read_rule) cannot put in plain words
KIND_WORDS = {"cap": "caps each payment", "only": "pays only certain addresses", "time": "waits for a time on the clock",
              "cosign": "asks a co-signer", "reserve": "keeps a reserve in the wallet", "freeze": "lets nothing leave",
              "other": "checks something of its own"}

# Why it matters: true of every rule on the testnet, one a day in turn; a line said twice in a week waits (alerts.said_often)
WHY = ["On Tau a wallet is an account with rules: the chain itself checks them, and a payment its rule refuses does not get into a block.",
       "Nobody had to ask for permission: any account on the testnet may hold a rule of its own, written in the Tau language.",
       "On the rules wall any wallet can take a rule it likes and sign it as its own; the neutral rule removes it again."]


def fresh_state() -> dict:
    return {"told": {}, "found": [], "primed": False, "day": "", "week": ""}


def key(text: str) -> str:
    return hashlib.sha1(re.sub(r"\s+", "", str(text or "")).encode()).hexdigest()[:16]


def plain(r: dict) -> str:
    """What a rule does, in plain words: the wallet's own reading where the rule has the wallet's shape, else what it
    checks (its kinds). Never the rule's free text."""
    w = gazette.read_rule(r.get("text") or "")
    if w:
        return gazette.rule_plain(w)["en"]
    kinds = [KIND_WORDS[k] for k in r.get("kinds") or [] if k in KIND_WORDS] or [KIND_WORDS["other"]]
    s = "A rule written by hand that " + (", ".join(kinds[:-1]) + " and " + kinds[-1] if len(kinds) > 1 else kinds[0]) + "."
    return s


def scan(st: dict, wall: list[dict] | None, now: float) -> list[dict]:
    """Every rule text on the wall the testnet never carried before: people's go into `found` (returned), the rest only
    count as known. The first run remembers everything as history."""
    if wall is None:
        return []
    new = []
    for r in wall:
        if not isinstance(r, dict) or not r.get("text"):
            continue
        k = key(r["text"])
        if k in st["told"]:
            for f in st["found"]:   # how many took it since: the week's post names the one most taken
                if f["key"] == k:
                    f["people"] = max(f.get("people", 0), int(r.get("people") or 0))
            continue
        st["told"][k] = round(now)
        if len(st["told"]) > 20000:   # rule texts are few; this only keeps a runaway from growing the state file
            for old in sorted(st["told"], key=st["told"].get)[:1000]:
                del st["told"][old]
        if not st["primed"] or r.get("by") != "people":
            continue
        ts = r.get("first_ts")
        if ts and now - float(ts) > FRESH:
            continue
        f = {"key": k, "at": round(now), "first": r.get("first"), "plain": plain(r), "kinds": r.get("kinds") or [],
             "people": int(r.get("people") or 1)}
        st["found"].append(f)
        new.append(f)
    st["primed"] = True
    st["found"] = [f for f in st["found"] if now - f["at"] < 8 * 86400]
    return new


def day_due(st: dict, now: float) -> list[dict]:
    """The rules found since the last daily post, when today's post time has come and passed less than 3 hours ago."""
    d = datetime.fromtimestamp(now, timezone.utc)
    if not HOUR <= d.hour < HOUR + 3 or st.get("day") == d.strftime("%Y-%m-%d"):
        return []
    since = st.get("day_at", 0)
    return [f for f in st["found"] if f["at"] > since]


def week_due(st: dict, now: float) -> list[dict]:
    d = datetime.fromtimestamp(now, timezone.utc)
    if d.weekday() != WEEK_DAY or not WEEK_HOUR <= d.hour < WEEK_HOUR + 3 or st.get("week") == d.strftime("%G-W%V"):
        return []
    return [f for f in st["found"] if now - f["at"] < 7 * 86400]


def wallets(n: int) -> str:
    return "1 wallet" if n == 1 else f"{n:,} wallets"


def telegram_text(fs: list[dict], real_line: str, why: str | None) -> str:
    e = html.escape
    n = len(fs)
    head = "A new rule on the testnet" if n == 1 else f"{n} new rules on the testnet"
    lead = ("A wallet that is not ours and not IDNI's wrote itself a rule Tau Testnet Alpha had never carried before. "
            "From now on the chain checks it on every payment that wallet sends." if n == 1 else
            f"Wallets that are not ours and not IDNI's wrote {n} rules Tau Testnet Alpha had never carried before. "
            "From now on the chain checks each one on every payment its wallet sends.")
    out = [real_line, f"📜 <b>{e(head)}</b>", "", e(lead)]
    for f in fs[:MAX_LINES]:
        where = f' (<a href="{e(SITE)}/explorer/?b={int(f["first"])}">block #{int(f["first"]):,}</a>)' if f.get("first") else ""
        took = f" Taken by {wallets(f['people'])} so far." if f.get("people", 1) > 1 else ""
        out += ["", f"• {e(f['plain'])}{where}{e(took)}"]
    if n > MAX_LINES:
        out += ["", e(f"…and {n - MAX_LINES} more on the rules wall.")]
    if why:
        out += ["", "<b>Why it matters</b>", e(why)]
    out += ["", f'<a href="{e(WALL)}">Every rule on the rules wall</a>']
    return "\n".join(out)


def x_lines(fs: list[dict]) -> list:
    """The week on X, opening with why it matters: the count, the rule most taken (or the newest) in plain words."""
    n = len(fs)
    top = max(fs, key=lambda f: (f.get("people", 1), f["at"]))
    why = "📜 On Tau a wallet can carry rules of its own, and the chain itself checks every payment against them."
    head = why + (" This week one wallet wrote a rule the testnet had never carried before." if n == 1 else
                  f" This week wallets wrote {n} rules the testnet had never carried before.")
    one = ("The rule: " if n == 1 else f"The one most taken, by {wallets(top['people'])}: " if top.get("people", 1) > 1
           else "The newest: ") + top["plain"]
    return [head, one]


def buttons() -> dict:
    return {"inline_keyboard": [[{"text": "📜 Rules wall", "url": WALL}, {"text": "🧱 Write your own", "url": f"{SITE}/builder/"}]]}

"""The Tau HUD blog (tauhud.com/blog/): learnings articles drafted from our own data, published by hand (or, with
BLOG_AUTO_PUBLISH_HOURS, a clean draft by itself after that many hours); the loop also runs the cruise ships' automatic
announcements and reports (cruise_crier.py), the hack of the week's posts (hack_crier.py) and the weekly report for
IDNI (idni_report.py).

  python blog.py loop                 every 10 minutes: a cruise ship visit that is over (and whose bookings were
                                      checked) gets one draft; nothing is published
  python blog.py drafts               the drafts waiting, with the address to read each one
  python blog.py draft <visit-id>     write the draft of that visit (anew, if there is one)
  python blog.py publish <id> [--dry] put the draft on the blog and post it once to Telegram and X (--dry: show only)
  python blog.py unpublish <id>       take a published article off the blog again (the posts stay)
  python blog.py pictures             make the hero pictures and link-preview pages of all articles anew

How a draft comes about: the relay's public cruise logbook (/cruise/log, /cruise/incidents) is counted here into a
list of facts (sent, refused, unanswered, skipped, pace, load verdicts, bookings, incidents). A language model
(NEWS_AI_KEY, the key of the IDNI news line) writes the article from that list only, in English, Chinese and
Japanese. Every number in the English text is checked against the facts; a number the facts do not hold is marked
in the draft, and such a draft is not published without --force. The draft sits at an unlisted address under
/blog/drafts/ until it is published with `up blog publish <id>`.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

import ai_meter

log = logging.getLogger("blog")

RELAY = os.environ.get("RELAY_HTTP", "http://relay:8080").rstrip("/")
PUBLIC = os.path.join(os.environ.get("PUBLIC_DIR", "/public"), "blog")
STATE = os.environ.get("BLOG_STATE", "/state/blog.json")
SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
NODE = os.environ.get("NODE_URL", "https://node.tauhud.com").rstrip("/")
AI_KEY = (os.environ.get("NEWS_AI_KEY") or os.environ.get("CHAT_AI_KEY") or "").strip()
AI_MODEL = os.environ.get("BLOG_AI_MODEL", "").strip() or os.environ.get("NEWS_AI_MODEL", "").strip() or "claude-sonnet-5-5"
ART = os.environ.get("BLOG_ART", "/art")        # the island's paintings as the game shows them (/opt/sites/rico/art)
SHIPS = os.environ.get("BLOG_SHIPS", "/ships")  # the painted ships (rabbit/art/ships)
IMG = os.path.join(PUBLIC, "img")               # hero pictures and charts, node.tauhud.com/blog/img/
SHARE = os.path.join(PUBLIC, "a")               # one small page per article for link previews, node.tauhud.com/blog/a/<id>.html
EVERY = 600
PICS_VERSION = 3   # raise when the hero picture changes: every article's picture is made anew once (2: numbers and Rico, 3: one story on refusals)
DESK_VERSION = 1   # the same for the heroes without island art (blog_pics.desk_hero): IDNI news, Q&As, testnet learnings
CHECK_WAIT = 3 * 3600      # a visit whose bookings were never checked is drafted this long after it ended
RETRY_AFTER = 2 * 3600
# a draft whose check is clean (every number in the facts, no hype or blame words) goes on the blog by itself this many
# hours after it was written, with its one post; 0 (the default) keeps publishing by hand: up blog publish <id>
# The article's X post carries its link (11 November 2026): the share page, whose card on X shows the hero picture,
# title and summary. One post with a link costs $0.20 instead of $0.015 (a few articles a month); X refuses a post with
# an uploaded picture AND a link (403, 3 November), so it goes without upload, and on a refusal once more the old way.
X_BLOG_LINK = os.environ.get("X_BLOG_LINK", "true").lower() in ("1", "true", "yes")
AUTO_PUBLISH_HOURS = float(os.environ.get("BLOG_AUTO_PUBLISH_HOURS", "0") or 0)
KINDS = ("pay", "bill", "book", "cancel")
# Our node keeps at most 254 wallet addresses; with all of them in use it answers ADMISSION_UNAVAILABLE to every
# transaction with a wallet it has not seen before (IDNI tau-testnet #108, since 11 November 2026). The ships log such a
# passenger as "new_wallet" and leave it out (relay/cruise.py NEW_WALLET_CODE); before, the answer was logged as a refusal.
NEW_WALLET = "ADMISSION_UNAVAILABLE"
NEW_WALLET_FACT = "passengers our node could not take (new wallets, not refusals)"
NEW_WALLET_WHY = ("our node answered ADMISSION_UNAVAILABLE (\"temporarily unavailable\"): it keeps at most 254 wallet addresses and "
                  "all of them are in use, so it cannot take a wallet it has not seen before, while wallets it already knows work "
                  "as before. Sending again does not help. It is not a refusal by the chain's rules. We reported it as IDNI "
                  "tau-testnet issue #108 on 11 November 2026, and it ends by itself once our node takes new wallets again")
LANGS = ("en", "zh", "ja")
ID_RE = re.compile(r"^[a-z0-9-]{3,60}$")

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Berlin")
except Exception:  # noqa: BLE001 - no tz data: UTC, and the facts say so
    TZ = None

SYSTEM = """You write the blog of Tau HUD (tauhud.com), an unofficial community dashboard for Tau Testnet Alpha, made \
by people not affiliated with IDNI, the team behind Tau. On the site, White Rabbit Key is an island game, and cruise \
ships call there by a timetable: their passengers are openly simulated, but every stop they make is a real, paced test \
transaction on the testnet. After each visit you write one short article: what happened and what we learned.

You get a list of facts counted from the ship's public logbook. Rules:
- Use ONLY these facts. Never invent numbers, causes, motives, plans, fixes, dates or effects. Every number you write \
must appear in the facts. When the facts do not show why something happened, say plainly that we do not know yet.
- "Our node" and "our relay" are Tau HUD's own, not IDNI's. Never blame the testnet or IDNI for something the facts \
show on our side. "No answer from the node" is not a refusal; a refusal is the node saying no.
- "Passengers our node could not take" are not refusals either: our node had no room for their new wallets (the facts \
say why and that it is reported). Write it as our node's limit, never as the chain refusing them, and name no culprit. \
Their sends got neither a yes nor a refusal, so when there are any, never write that every answer was a yes.
- Who reads this: the Tau community and the IDNI team, and both should be glad to read it. Choose and frame what you \
tell so each sees what it gains: for the community what works and what they can try, for IDNI what a community node \
under real traffic shows them and what held up on their testnet. Stay honest: say what went wrong on our side and own \
it, credit what the testnet and the chain did right, and never blame, mock or lecture IDNI, Tau or the testnet. Where \
something on the chain side is not yet clear, say what we will measure, not who is at fault.
- Plain words for curious readers who are not developers. No code names, file names, function names or field names.
- No hype or marketing words (huge, exciting, revolutionary, game-changing, finally), no price talk, no coin talk, no \
exclamation marks, no emoji, no names of people.
- Honest and calm, like a good engineering blog: what we saw, what it means, what is still open.
- Do not only list numbers: say what they come to. "what the numbers mean" holds shares and rates worked out from \
the facts; use them to explain cause and effect (what set the pace, what the chain did, what our side did), and say \
in one or two sentences what this one call means for the testnet as a whole and what it does not prove.
- When the facts have "the ship before": compare this call with that one in its own section, say plainly what \
improved, what did not and why (use "what we changed after that call"), and note that the two ships differ in size \
and plan where that matters. The change from the ship before is the news of the article: it belongs in the title or \
dek when it is real (for example a ship that stayed the whole time after one that left early). Where "the ship before" \
has a "note" that its unanswered sends were counted as refusals by the rule of the time, the node refused none of them: \
write "sends without an answer, counted as refusals by the old rule", never "the node refused them".
- Never write a line for a thing that did not happen or was not tried (no "0 bookings were checked" on a day without \
bookings); leave it out.
- Length: 300 to 500 English words in body.
- title: at most 70 characters, a real headline with subject and verb that reads well aloud. dek: one sentence, at \
most 160 characters, that adds to the title rather than repeating it.
- why: two or three lines, each at most 160 characters, that say at a glance why this visit matters: one for the Tau \
community, one for IDNI (what a community node under steady everyday traffic shows them), optionally one for everyone.
- body: Markdown with "## " section headings, short paragraphs and "- " lists. Sections in this order: "What happened", \
"What the logbook shows", "Compared with the ship before" (only when the facts have "the ship before"), \
"What it means for the testnet", "What is still open". No title in body, no tables, no links \
of your own: name our places as they are called (White Rabbit Key, tauhud.com, the ship's name, Tau Testnet Alpha, \
our node) and the blog links them to their pages by itself.
- When the facts have "pirate tricks": the ship is a pirate ship whose made-up pirates try, on purpose, what the \
chain must refuse. A refused trick is good news: the chain did its job. Say which tricks were refused and with which \
answer, in plain words (paying more than the wallet holds, sending the same payment twice, a payment whose time ran \
out, a payment signed with the wrong key). Never call a refused trick a failure or a problem.
- When the facts have "the ship changed for its next call": tell each change in the section "What is still open" as \
"The ship changed <what> from <from> to <to> because <because>." Nothing else changed by itself; do not suggest more.
- zh: Simplified Chinese, ja: Japanese, same meaning and the same numbers; keep Tau, IDNI, AGRS, White Rabbit Key and \
the ship names in Latin letters.
- x: one post for X, at most 200 characters, no link, no hashtags: the headline point and why it matters.
- card: the text on the article's picture, English only: "line", at most 60 characters, the one thing that changed \
or was learned, in other words than the title (never a repeat of it); "why", three points of at most 52 characters \
each that say at a glance why it matters (for the community, for IDNI, and what improved since the ship before).

Answer with JSON only, no other text:
{"title":{"en":"","zh":"","ja":""},"dek":{"en":"","zh":"","ja":""},"why":[{"en":"","zh":"","ja":""}],\
"body":{"en":"","zh":"","ja":""},"x":"","card":{"line":"","why":["","",""]}}"""


# ---------- reading ----------
def get(path: str):
    with urllib.request.urlopen(RELAY + path, timeout=30) as r:
        return json.load(r)


def local(t: float) -> dt.datetime:
    return dt.datetime.fromtimestamp(t, TZ or dt.timezone.utc)


def clock(t: float) -> str:
    return local(t).strftime("%H:%M")


def day(t: float) -> str:
    d = local(t)
    return f"{d.strftime('%A')}, {d.day} {d.strftime('%B')} {d.year}"


def facts_of(entries: list[dict], incidents: list[dict], cruise: dict | None = None) -> dict:
    """What the logbook of one visit says, in numbers. `entries`: that visit's logbook, any order."""
    rows = sorted(entries, key=lambda e: e.get("t") or 0)
    over = next((e for e in rows if e.get("kind") == "visit over"), None)
    s = (over or {}).get("summary") or {}
    landed = next((e for e in rows if e.get("kind") == "landed"), None)
    left = next((e for e in rows if e.get("kind") == "left"), None)
    checked = next((e for e in rows if e.get("kind") == "bookings checked"), None)
    sends = [e for e in rows if e.get("kind") in KINDS]
    # new wallets our node could not take (NEW_WALLET): logged so since this rule; before, as refusals: a passenger whose
    # sequence was 0 at such an answer had no transaction in a block, so every such answer it got that visit was the limit
    new_p = {e.get("p") for e in sends if e.get("ok") is False and NEW_WALLET in str(e.get("err") or "") and e.get("seq") == 0}
    nw_old = [e for e in sends if e.get("ok") is False and NEW_WALLET in str(e.get("err") or "") and e.get("p") in new_p]
    nw_ids = {id(e) for e in nw_old}
    nw = nw_old + [e for e in rows if e.get("new_wallet")]
    answered = [e for e in sends if e.get("ok") is not None]
    later = [e for e in rows if e.get("kind") == "unanswered checked"]
    f: dict = {"ship": s.get("name") or (landed or {}).get("ship"), "visit": s.get("id") or (rows[0].get("visit") if rows else None),
               "time_zone": "German time" if TZ else "UTC",
               "simulated passengers": s.get("passengers"),
               "minutes planned in port": 90}
    t0 = s.get("t0") or (landed or {}).get("t")
    if t0:
        f["date"] = day(t0)
        f["timetable time"] = clock(t0)
    if landed:
        f["landed"] = {"at": clock(landed["t"]), "testnet load then": landed.get("verdict"),
                       "transactions planned": landed.get("plan"), "new kinds tried this visit": landed.get("trial") or []}
    elif s and not s.get("landed"):
        f["landed"] = False
        f["why not landed"] = s.get("note")
    if left:
        f["left early"] = {"at": clock(left["t"]), "why": left.get("note"),
                           "minutes in port": round((left["t"] - (landed or left)["t"]) / 60)}
        f["minutes in port"] = f["left early"]["minutes in port"]
    elif landed:
        f["minutes in port"] = 90   # the whole planned call
    f["sent and accepted"] = {k: v for k, v in (s.get("sent") or {}).items() if v} or \
        dict(Counter(e["kind"] for e in sends if e.get("ok") is True))
    refused = {k: v for k, v in (s.get("refused") or {}).items() if v} or \
        dict(Counter(e["kind"] for e in sends if e.get("ok") is False))
    for e in nw_old:
        if refused.get(e["kind"]):
            refused[e["kind"]] -= 1
    f["refused by the node"] = {k: v for k, v in refused.items() if v}
    f["accepted in all"] = sum(f["sent and accepted"].values())
    f["refused in all"] = sum(f["refused by the node"].values())
    unanswered = [e for e in sends if e.get("ok") is None and "no answer" in str(e.get("note") or "")]
    # before 6 November 2026 a send without an answer was logged as refused with an empty error (written as "null" at times)
    silent = [e for e in sends if e.get("ok") is False and str(e.get("err") or "").strip().lower() in ("", "null", "none")]
    if unanswered or s.get("unanswered"):
        f["sends our node did not answer in time (not refusals)"] = s.get("unanswered") or len(unanswered)
        if later:
            f["of those, reached the chain after all"] = sum(1 for e in later if e.get("took"))
    if silent:
        f["refusals logged without any answer from the node (a timeout, counted as refusal by the old rule)"] = len(silent)
    reasons = Counter(re.sub(r"[0-9a-f]{16,}", "…", str(e.get("err")))[:120] for e in sends
                      if e.get("ok") is False and e.get("err") and id(e) not in nw_ids)
    if reasons:
        f["refusal answers"] = dict(reasons.most_common(5))
    if nw:
        f[NEW_WALLET_FACT] = {"passengers": len({e.get("p") for e in nw}), "their sends the node could not take or the ship left out": len(nw),
                              "the node's answer": "temporarily unavailable (ADMISSION_UNAVAILABLE): neither a yes nor a refusal",
                              "why": NEW_WALLET_WHY,
                              "how this call handled them": "the rule of the time counted them as refusals and sent each of their stops"
                              if nw_old else "each was left out for the rest of the call after the first answer, and is tried again on the next call"}
    if s.get("skipped") is not None:
        f["stops skipped"] = s.get("skipped")
    nw_books = {e.get("p") for e in nw if e.get("kind") == "book"}   # a withdrawal finds nothing when its booking was not taken
    skips = Counter(str(e["note"]) + (" (its booking was one of the sends our node could not take)"
                                      if e.get("kind") == "cancel" and e.get("p") in nw_books else "")
                    for e in sends if e.get("ok") is None and e.get("note") and not e.get("new_wallet")
                    and "no answer" not in str(e["note"]))   # unanswered sends have their own fact
    if skips:
        f["why stops were skipped, as logged"] = dict(skips.most_common(5))
    f["sends logged"] = len(sends)
    v = Counter(e.get("verdict") for e in sends if e.get("verdict"))
    if v:
        f["testnet load at each send"] = dict(v)
    if "half_strained" in s:   # since 6 November 2026 the ship counts why it went at half pace
        if s.get("half_strained"):
            f["sends at half pace because the testnet looked strained"] = s["half_strained"]
        if s.get("half_node"):
            f["sends at half pace because our own node had just left a send unanswered (not the testnet)"] = s["half_node"]
    elif s.get("half") is not None:   # before, every half-pace send came from the strained verdict
        f["sends at half pace because the testnet looked strained"] = s.get("half")
    ms = sorted(e["ms"] for e in sends if isinstance(e.get("ms"), int))
    if ms:   # how long our node took to answer a sendtx (logged since 6 November 2026), in seconds
        sec = lambda m: round(m / 1000, 1)  # noqa: E731
        f["our node's answer time to a send, seconds"] = {"median": sec(ms[len(ms) // 2]), "8 of 10 within": sec(ms[min(len(ms) - 1, len(ms) * 8 // 10)]),
                                                           "slowest tenth from": sec(ms[len(ms) * 9 // 10]), "slowest": sec(ms[-1]), "sends timed": len(ms)}
        a0 = min(e["t"] for e in sends)
        per: dict = {}
        for e in sends:
            if isinstance(e.get("ms"), int):
                per.setdefault((e["t"] - a0) // 600, []).append(e["ms"])
        f["median answer time per 10 minutes, seconds"] = [sec(sorted(per[k])[len(per[k]) // 2]) if per.get(k) else 0
                                                           for k in range(int(max(per)) + 1)]
    if sends:
        a = min(e["t"] for e in sends)
        tens = Counter((e["t"] - a) // 600 for e in sends)
        f["sends per 10 minutes"] = [tens.get(i, 0) for i in range(int(max(tens)) + 1)]
        f["first send"], f["last send"] = clock(a), clock(max(e["t"] for e in sends))
        hs = [e.get("height") for e in sends if e.get("height")]
        if hs:
            f["block heights"] = [min(hs), max(hs)]
    ahead = [e for e in rows if e.get("kind") in ("book ahead", "refund")]
    off = next((e for e in rows if e.get("kind") == "called off"), None)
    settled = next((e for e in rows if e.get("kind") == "escrow" and e.get("status") == "settled"), None)
    if ahead or off or settled:   # bookings ahead of the call (relay/cruise.py escrow), since 11 November 2026
        g = {"what they are": "retractable transfers of the fare from simulated passengers to the ship's till, released at the "
                              "arrival time; only the sender can take one back, so there is no third party who decides",
             "booked": sum(1 for e in ahead if e["kind"] == "book ahead" and e.get("ok") is True),
             "refused by the node": sum(1 for e in ahead if e["kind"] == "book ahead" and e.get("ok") is False),
             "not booked: wallets new to our node, which had no room for them": sum(1 for e in ahead if e["kind"] == "book ahead" and e.get("new_wallet")),
             "taken back before the arrival": sum(1 for e in ahead if e["kind"] == "refund" and e.get("ok") is True)}
        if off:
            g["call called off before the arrival"] = off.get("note")
        g["how they ended on the chain"] = (settled or {}).get("result") or "not looked up yet when this was written"
        g = {k: v for k, v in g.items() if v or not k.startswith("not booked")}
        f["bookings ahead in escrow"] = g
    if checked and checked.get("checked"):   # a day without bookings has nothing to check, and the article says nothing of it
        f["bookings checked after the visit"] = checked.get("checked")
        f["bookings the chain had not paid out"] = len(checked.get("not_released") or [])
    if s.get("tried"):
        f["new kinds now count as tried"] = {k: bool(x) for k, x in s["tried"].items()}
    mine = [i for i in incidents if i.get("visit") == f["visit"]]
    if mine:
        f["incidents"] = [{"at": clock(i["at"]), "kind": i.get("kind"), "note": i.get("note"),
                           "newest block age (s)": (i.get("chain") or {}).get("block_age"),
                           "transactions waiting": (i.get("chain") or {}).get("waiting")} for i in mine]
    nxt = (cruise or {}).get("next")
    if nxt and nxt.get("t0"):
        f["next ship"] = {"name": nxt.get("name"), "date": day(nxt["t0"]), "time": clock(nxt["t0"])}
    f["the ship's brakes"] = {"at most transactions a minute": 12,
                              "it leaves when the node refuses": "5 of the last 20 passenger transactions",
                              "strained testnet": "half pace", "stalled testnet": "it leaves at once",
                              "our node does not answer a send within 20 seconds": "no refusal: the ship waits 30 seconds, then half pace for 10 minutes",
                              "our node cannot take a passenger's new wallet": "no refusal: that passenger is left out for the rest of the call"}
    f["answered sends"] = len(answered)
    tricks = [e for e in rows if e.get("kind") == "trick" and (e.get("ok") is not None or e.get("held"))]
    if tricks or s.get("tricks"):   # the pirates (since 7 November 2026): what the chain is meant to refuse
        st = s.get("tricks") or {}
        held = sum(1 for e in tricks if e.get("held")) + sum(1 for c in st.values() if isinstance(c, dict) and c.get("held"))
        t = {"tried": sum(1 for e in tricks if e.get("ok") is not None) + held,
             "refused with the expected answer": sum(1 for e in tricks if e.get("ok") is False and e.get("right")),
             "refused with another answer": sum(1 for e in tricks if e.get("ok") is False and not e.get("right")),
             "accepted although the chain should refuse it": sum(1 for e in tricks if e.get("ok") is True)}
        if held:
            t["held back"] = held
        by = {}
        for e in tricks:
            if e.get("ok") is not None and e.get("trick"):
                b = by.setdefault(e.get("what") or e["trick"], {"tried": 0, "refused": 0})
                b["tried"] += 1
                b["refused"] += e.get("ok") is False
        if by:
            t["each trick"] = by
        codes = Counter(e.get("code") for e in tricks if e.get("ok") is False and e.get("code"))
        if codes:
            t["the chain's answers"] = dict(codes)
        f["pirate tricks"] = {k: v for k, v in t.items() if v or k == "tried"}
        f["what a trick is"] = ("a pirate sends on purpose what the chain must refuse; a refused trick is the chain working, "
                                "not a failure, and it never counts as a refusal for the ship's brakes")
    if s.get("per_min"):
        f["the ship's pace this visit, transactions a minute at most"] = s["per_min"]
    if s.get("changed"):
        f["the ship changed for its next call"] = [c if c.get("held") else {k: c.get(k) for k in ("what", "from", "to", "because")}
                                                   for c in s["changed"]]
    return f


def meaning_of(f: dict) -> dict:
    """What the counted numbers come to, worked out here so the article can say it without inventing: shares, the
    pace the node's answer time allows, the chain's movement during the call."""
    m: dict = {}
    plan = (f.get("landed") or {}).get("transactions planned") if isinstance(f.get("landed"), dict) else None
    acc, ref = f.get("accepted in all") or 0, f.get("refused in all") or 0
    old = f.get("refusals logged without any answer from the node (a timeout, counted as refusal by the old rule)") or 0
    una = (f.get("sends our node did not answer in time (not refusals)") or 0) + old
    answered = acc + ref - old
    if plan:
        m["share of the planned stops that went through"] = f"{round(100 * acc / plan)}%"
    if answered:
        m["share of the node's answers that were a yes"] = f"{round(100 * acc / answered)}%"
    if una and f.get("sends logged"):
        m["share of sends our node did not answer in time"] = f"{round(100 * una / f['sends logged'])}%"
    t = f.get("our node's answer time to a send, seconds") or {}
    if t.get("median"):
        m["sends a minute the node's answer time allows, one at a time"] = round(60 / t["median"], 1)
        m["what that means"] = ("the ship sends one transaction and waits for the answer before the next; a slow answer, not "
                                "the ship's brakes, is what sets the pace once the median goes above 5 seconds")
    if t.get("8 of 10 within"):   # the next plan follows the slow answers, not the median (cruise.py PLAN_QUANTILE)
        m["stops a minute the next plan allows for, from the time 8 of 10 sends were answered within"] = round(0.85 * min(12, 60 / t["8 of 10 within"]), 1)
    hs = f.get("block heights")
    if hs and len(hs) == 2 and hs[1] > hs[0]:
        m["blocks sealed while the ship was in port"] = hs[1] - hs[0]
        m["accepted transactions per sealed block, on average"] = round(acc / (hs[1] - hs[0]), 1)
    if f.get("minutes in port") is not None and f.get("minutes planned in port"):
        m["share of the planned time in port"] = f"{round(100 * f['minutes in port'] / f['minutes planned in port'])}%"
    return m


BEFORE_KEYS = ("ship", "date", "minutes in port", "minutes planned in port", "accepted in all", "refused in all",
               "stops skipped", "simulated passengers", "pirate tricks")


def compare_with(f: dict, before: dict | None) -> dict:
    """The ship before this one, in the same numbers, and what changed between the two calls: so the article can say
    what improved and what did not, with nothing made up."""
    if not before:
        return f
    b = {k: before[k] for k in BEFORE_KEYS if before.get(k) is not None}
    plan = (before.get("landed") or {}).get("transactions planned") if isinstance(before.get("landed"), dict) else None
    if plan:
        b["transactions planned"] = plan
    old = before.get("refusals logged without any answer from the node (a timeout, counted as refusal by the old rule)") or 0
    una = (before.get("sends our node did not answer in time (not refusals)") or 0) + old
    if una:
        b["sends our node did not answer in time"] = una
    if old:
        b["refused in all"] = (before.get("refused in all") or 0) - old
        b["note"] = f"its {old} unanswered sends were counted as refusals by the rule of the time, and that is why it left early"
    if before.get("left early"):
        why = str(before["left early"].get("why") or "")
        if old:
            why += " (sends without an answer, which the rule of the time counted as refusals; the node refused none)"
        b["left early"] = {"at": before["left early"].get("at"), "why": why}
    t = before.get("our node's answer time to a send, seconds") or {}
    if t.get("median"):
        b["our node's median answer time, seconds"] = t["median"]
    changed = []
    for c in before.get("the ship changed for its next call") or []:
        if not c.get("held"):
            changed.append(f"the ship changed {c.get('what')} from {c.get('from')} to {c.get('to')} because {c.get('because')}")
    if old:
        changed.append("a send our node does not answer within 20 seconds no longer counts as a refusal: the ship waits 30 seconds, "
                       "then sends at half pace for 10 minutes and checks whether the transaction arrived after all (rule since 6 November 2026)")
    if changed:
        b["what we changed after that call"] = changed
    f["the ship before"] = b
    f["compared with the ship before"] = {
        "minutes in port": [b.get("minutes in port"), f.get("minutes in port")],
        "accepted by the node": [b.get("accepted in all"), f.get("accepted in all")],
        "refused by the node": [b.get("refused in all"), f.get("refused in all")],
        "no answer in time": [b.get("sends our node did not answer in time", 0),
                              f.get("sends our node did not answer in time (not refusals)") or 0],
        "stops skipped": [b.get("stops skipped"), f.get("stops skipped")],
        "read as": "[the ship before, this ship]; the two ships differ in size and plan, so compare shares and causes, not raw counts alone",
    }
    return f


# ---------- checking ----------
NUM = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?(?:[:]\d\d)?")


def numbers_in(obj) -> set[str]:
    out: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            out |= numbers_in(k) | numbers_in(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out |= numbers_in(v)
    elif isinstance(obj, bool) or obj is None:
        pass
    elif isinstance(obj, (int, float)):
        out.add(str(round(obj, 1)).removesuffix(".0"))
        out.add(str(round(obj, 1)))   # "20.0" as the text may write a whole number of seconds
    else:
        out |= {n.replace(",", ".") for n in NUM.findall(str(obj))}
    return out


def unknown_numbers(text: str, facts: dict) -> list[str]:
    """Numbers in `text` that the facts do not hold (a year, one to three as words, and sums of the facts' counts
    are fine; anything else is marked for a look)."""
    known = numbers_in(facts) | {"1", "2", "3"}
    sent = facts.get("sent and accepted") or {}
    known |= {str(sum(sent.values()))} | {str(x) for x in (facts.get("accepted in all"), facts.get("refused in all"))}
    out = []
    for n in NUM.findall(text):
        n2 = n.replace(",", ".")
        if n2 not in known and n2 not in out:
            out.append(n2)
    return out


# ---------- writing ----------
def _obj(props: dict, required: list | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or list(props), "additionalProperties": False}


L3 = _obj({k: {"type": "string"} for k in LANGS})
ARTICLE_SHAPE = _obj({   # the API shapes the answer by this schema, so no quote in the text can break the JSON
    "title": L3, "dek": L3,
    "why": {"type": "array", "items": L3, "description": "2 or 3 short lines"},
    "body": L3, "x": {"type": "string"},
    "card": _obj({"line": {"type": "string"}, "why": {"type": "array", "items": {"type": "string"}, "description": "up to 3 short lines"}})})


# The model's thinking and the article (three languages) share max_tokens. On 11 November 2026 the facts of the MS Dry Run
# needed more than 8000: the answer was cut off twice and read as broken JSON. An answer cut at ROOM is asked once more
# with ROOM_MAX (only what is written is billed).
ROOM = 16000
ROOM_MAX = 32000


def ask_ai(facts: dict, tries: int = 2, shaped: bool = True, room: int = ROOM) -> dict:
    prompt = "Facts counted from the logbook of one cruise ship visit (JSON):\n\n" + json.dumps(facts, ensure_ascii=False, indent=1)
    body = {"model": AI_MODEL, "max_tokens": room, "system": SYSTEM, "messages": [{"role": "user", "content": prompt}]}
    if shaped:
        body["output_config"] = {"format": {"type": "json_schema", "schema": ARTICLE_SHAPE}}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), headers={
        "x-api-key": AI_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300 if room <= ROOM else 900) as r:
            j = urllib_json(r)
    except urllib.error.HTTPError as e:
        reason = e.read().decode("utf-8", "replace")[:600]
        log.warning("the API answered %s for model %s: %s", e.code, AI_MODEL, reason)
        if e.code == 400 and shaped:   # the model does not take the shaped answer: ask the plain way, the JSON in the text
            return ask_ai(facts, tries, shaped=False, room=room)
        raise RuntimeError(f"the API answered {e.code} for model {AI_MODEL}: {reason}") from None
    ai_meter.meter("blog", AI_MODEL, j.get("usage"))
    stop = j.get("stop_reason")
    if stop == "refusal":
        raise RuntimeError(f"the model declined to write this article ({(j.get('stop_details') or {}).get('category') or 'no reason given'})")
    if stop == "max_tokens":
        if room < ROOM_MAX:
            log.warning("the model's answer was cut off at %d tokens (its thinking counts too): asking once more with room for %d",
                        room, ROOM_MAX)
            return ask_ai(facts, tries, shaped, ROOM_MAX)
        raise RuntimeError(f"the model's answer did not fit in {room} tokens")
    text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    try:
        if not m:
            raise ValueError("no JSON in the answer: " + text[:200])
        return json.loads(m.group(0))
    except ValueError as e:
        if tries > 1:
            log.warning("the model's answer was not valid JSON (%s): asking once more", e)
            return ask_ai(facts, tries - 1, shaped, room)
        raise


def urllib_json(r):
    return json.load(r)


def three(d, cap: int) -> dict | None:
    if not isinstance(d, dict):
        return None
    out = {}
    for k in LANGS:
        v = str(d.get(k) or "").strip()
        if not v or len(v) > cap:
            return None
        out[k] = v
    return out


# blame on IDNI or the testnet is marked for a look like hype, so such a draft needs --force (rule of 6 November 2026)
BLAME = re.compile(r"\b(IDNI|Tau|the testnet|the chain)(['’]s)?\s+(is |was |were )?(at fault|to blame|fault|failed us|broke|broken|"
                   r"unreliable|unstable|buggy|bug|let us down)\b", re.I)
HYPE = re.compile(r"\b(huge|exciting|revolutionary|game[- ]chang\w*|moon|pump|to the moon|finally|incredible)\b|!", re.I)


def article(facts: dict, out: dict, now: float) -> dict:
    title, dek, body = three(out.get("title"), 90), three(out.get("dek"), 220), three(out.get("body"), 9000)
    why = [w for w in (three(x, 200) for x in (out.get("why") or [])[:3]) if w]
    if not (title and dek and body and why):
        raise ValueError("the answer misses a title, dek, why or body in one of the languages")
    en = " ".join([title["en"], dek["en"], body["en"], *[w["en"] for w in why], str(out.get("x") or "")])
    vid = facts.get("visit") or "visit"
    return {"id": f"{vid}-learnings", "on": local(now).strftime("%Y-%m-%d"), "kind": "cruise", "visit": vid,
            "title": title, "dek": dek, "why": why, "body": body, "x": " ".join(str(out.get("x") or "").split())[:240],
            "sources": [f"{NODE}/cruise/log?visit={vid}", f"{NODE}/cruise/incidents"],
            "facts": facts, "check": {"unknown_numbers": unknown_numbers(en, facts), "hype": sorted({m.group(0) for m in HYPE.finditer(en)} | {m.group(0) for m in BLAME.finditer(en)})},
            "card": card_of(out.get("card"), title["en"]), "written": int(now), "model": AI_MODEL}


def card_of(c, title: str) -> list[str]:
    """The lines on the hero picture: title, the point, "Why it matters" and up to three short points, the footer."""
    c = c if isinstance(c, dict) else {}
    def short(t, n):   # cut at a word, never in the middle of one
        t = " ".join(str(t or "").split())
        return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(" ,;:")
    lines = [short(title, 60)]
    if c.get("line"):
        lines.append(short(c["line"], 64))
    why = [short(w, 56) for w in (c.get("why") or [])[:3] if w]
    if why:
        lines += ["## Why it matters"] + ["- " + w for w in why]
    return lines + ["Tau HUD blog · community project, not affiliated with IDNI"]


# ---------- pictures ----------
def ship_of(a: dict) -> str:
    name = str((a.get("facts") or {}).get("ship") or a.get("ship") or "")
    if "black sequence" in name.lower() or a.get("ship") == "pirate":
        return "pirate"
    return "liner" if "queen" in name.lower() or a.get("ship") == "liner" else "expedition"


def island_story(a: dict) -> bool:
    """Only the island's and the ships' own articles get the island's painting (with the ship and Rico) as hero; an
    article about IDNI news, a Q&A or what the testnet taught us gets the site's own look (blog_pics.desk_hero)."""
    return a.get("kind") == "cruise" or bool(a.get("visit") or a.get("ship") or (a.get("facts") or {}).get("ship"))


def pics_version(a: dict):
    return PICS_VERSION if island_story(a) else f"desk-{DESK_VERSION}"


def kicker(a: dict) -> str:
    """The small line above the title on a desk hero: the article's kind and day, or its own `kicker`."""
    if a.get("kicker"):
        return str(a["kicker"])
    label = {"learnings": "Learnings", "news": "News"}.get(a.get("kind") or "", "Tau HUD blog")
    try:
        day = dt.date.fromisoformat(str(a.get("on")))
        return f"{label} · {day.day} {day.strftime('%B %Y')}"
    except ValueError:
        return label


def make_hero(a: dict, stats: list | None) -> bool:
    """The article's hero picture at IMG/<id>-hero.jpg: the island's painting for island and ship stories (only where
    the paintings are), the site's own look for every other article. True when it was made."""
    import blog_pics
    os.makedirs(IMG, exist_ok=True)
    out = os.path.join(IMG, a["id"] + "-hero.jpg")
    if island_story(a):
        if not os.path.exists(os.path.join(ART, "index.json")):
            return False
        blog_pics.hero(ART, SHIPS, a["card"], ship_of(a), out, stats=stats)
    else:
        blog_pics.desk_hero(a["card"], out, stats=stats, kicker=kicker(a))
    return True


def pictures(a: dict) -> dict:
    """The hero picture (the island's painting with the ship and the card, made only where the paintings are) and
    the charts of the visit's numbers; the article gets their addresses. Without paintings, no hero and no error."""
    import blog_pics
    os.makedirs(IMG, exist_ok=True)
    if a.get("card"):
        try:
            if make_hero(a, blog_pics.visit_stats(a.get("facts") or {})):
                a["image"] = f"{NODE}/blog/img/{a['id']}-hero.jpg"
        except Exception as e:  # noqa: BLE001 - an article without its picture beats no article
            log.warning("hero for %s: %s", a["id"], e)
    if a.get("facts"):
        figs = blog_pics.visit_charts(a["facts"], os.path.join(IMG, a["id"]))
        live = {"-stops.png": "/cruise/", "-pace.png": "/load/", "-before.png": "/cruise/"}   # each chart leads to the live page it was drawn from
        a["figures"] = [{"src": f"{NODE}/blog/img/{os.path.basename(p)}", "caption": cap, "after": i + 1,
                         **{"link": v for k, v in live.items() if p.endswith(k)}} for i, (p, cap) in enumerate(figs)] \
            or a.get("figures") or []   # after the first section the stops, after the second the pace
    return a


def share_page(a: dict) -> str:
    """A small page whose link preview on Telegram, X and elsewhere shows the article's picture, title and summary;
    a person who opens it goes on to the article."""
    import html as h
    url = f"{SITE}/blog/?p={a['id']}"
    img = a.get("image") or f"{SITE}/assets/shots/blog.png"
    t, dek = h.escape(a["title"]["en"]), h.escape(a["dek"]["en"])
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{t} · Tau HUD Blog</title>
<meta name="description" content="{dek}"><meta property="og:type" content="article"><meta property="og:title" content="{t}">
<meta property="og:description" content="{dek}"><meta property="og:image" content="{h.escape(img)}"><meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:site" content="@TauHUDcom"><meta name="twitter:image" content="{h.escape(img)}">
<link rel="canonical" href="{url}"><meta http-equiv="refresh" content="0; url={url}"></head>
<body style="background:#09090a;color:#ebebee;font-family:sans-serif"><p><a style="color:#fff" href="{url}">{t}</a></p></body></html>"""
    os.makedirs(SHARE, exist_ok=True)
    with open(os.path.join(SHARE, a["id"] + ".html"), "w", encoding="utf-8") as f:
        f.write(page)
    return f"{NODE}/blog/a/{a['id']}.html"


def site_pictures(force: bool = False) -> int:
    """The articles shipped with the site get their hero picture and share page here (the paintings are only on our
    server); a picture already made is kept unless forced."""
    try:
        with urllib.request.urlopen(SITE + "/assets/blog/posts.json", timeout=20) as r:
            site = json.load(r).get("posts") or []
    except Exception as e:  # noqa: BLE001
        log.warning("site posts: %s", e)
        return 0
    n = 0
    for a in site + posts()["posts"]:
        if not a.get("id") or not ID_RE.match(a["id"]):
            continue
        st = state()
        old = st.setdefault("pics", {}).get(a["id"]) != pics_version(a)
        if force or old or not os.path.exists(os.path.join(SHARE, a["id"] + ".html")) or (a.get("card") and not os.path.exists(os.path.join(IMG, a["id"] + "-hero.jpg"))):
            if a.get("card"):
                import blog_pics
                try:
                    make_hero(a, a.get("stats") or blog_pics.visit_stats(a.get("facts") or {}))
                except Exception as e:  # noqa: BLE001
                    log.warning("hero for %s: %s", a["id"], e)
            share_page(a)
            if a.get("card") and os.path.exists(os.path.join(IMG, a["id"] + "-hero.jpg")):
                st = state()
                st.setdefault("pics", {})[a["id"]] = pics_version(a)
                write_json(STATE, st)
            n += 1
    return n


# ---------- files ----------
def read_json(path: str, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def state() -> dict:
    st = read_json(STATE, {})
    st.setdefault("drafted", {})   # visit id -> draft id
    st.setdefault("drafts", {})    # draft id -> unlisted file name
    st.setdefault("failed_at", 0)
    return st


def posts() -> dict:
    return read_json(os.path.join(PUBLIC, "posts.json"), {"posts": []})


def site_ids() -> set[str]:
    """Articles shipped with the site itself (assets/blog/posts.json in the repository)."""
    try:
        with urllib.request.urlopen(SITE + "/assets/blog/posts.json", timeout=20) as r:
            return {str(p.get("id")) for p in json.load(r).get("posts") or []}
    except Exception:  # noqa: BLE001 - Pages unreachable: an unneeded draft at worst, never a post
        return set()


def draft_url(st: dict, did: str) -> str:
    return f"{SITE}/blog/?draft={st['drafts'][did]}"


def write_draft(vid: str, now: float | None = None) -> str:
    now = now or time.time()
    log_ = get(f"/cruise/log?visit={vid}&n=2000")
    entries = log_.get("entries") or []
    if not entries:
        raise ValueError(f"no logbook entries for {vid} (visits: {', '.join(log_.get('visits') or [])})")
    try:
        inc, cr = get("/cruise/incidents").get("incidents") or [], get("/cruise")
    except Exception:  # noqa: BLE001 - the article can do without them
        inc, cr = [], None
    facts = compare_with(facts_of(entries, inc, cr), before_facts(vid, log_.get("visits") or [], inc, cr))
    facts["what the numbers mean"] = meaning_of(facts)
    a = pictures(article(facts, ask_ai(facts), now))
    st = state()
    name = st["drafts"].get(a["id"]) or f"{a['id']}-{secrets.token_hex(4)}"
    st["drafts"][a["id"]], st["drafted"][vid] = name, a["id"]
    st.setdefault("drafted_at", {})[a["id"]] = round(now)
    a["status"] = "draft"
    write_json(os.path.join(PUBLIC, "drafts", name + ".json"), a)
    write_json(STATE, st)
    return a["id"]


def before_facts(vid: str, visits: list[str], inc: list, cr) -> dict | None:
    """The facts of the ship that called before this one (the relay lists visits newest first), or None."""
    try:
        i = visits.index(vid)
    except ValueError:
        return None
    for prev in visits[i + 1:i + 4]:
        try:
            rows = get(f"/cruise/log?visit={prev}&n=2000").get("entries") or []
        except Exception:  # noqa: BLE001
            return None
        if any(e.get("kind") == "visit over" for e in rows) and not any(e.get("held") for e in rows):
            return facts_of(rows, inc, cr)
    return None


def due(entries: list[dict], now: float) -> bool:
    over = next((e for e in entries if e.get("kind") == "visit over"), None)
    if not over:
        return False
    return any(e.get("kind") == "bookings checked" for e in entries) or now - over["t"] >= CHECK_WAIT


def tick(now: float | None = None) -> None:
    now = now or time.time()
    st = state()
    if not AI_KEY or now - st["failed_at"] < RETRY_AFTER:
        return
    visits = (get("/cruise/log?n=1").get("visits") or [])[:5]
    on_site = site_ids()
    for vid in visits:
        if vid in st["drafted"] or f"{vid}-learnings" in on_site:   # an article shipped with the site (the first one) is not drafted again
            continue
        entries = get(f"/cruise/log?visit={vid}&n=2000").get("entries") or []
        if not due(entries, now):
            continue
        if any(e.get("held") for e in entries):   # a finding is held back for its owner: no article until it is released
            continue
        try:
            did = write_draft(vid, now)
            log.info("draft %s written: %s", did, draft_url(state(), did))
            try:
                import cruise_crier
                cruise_crier.tell_draft(did, draft_url(state(), did))
            except Exception as e:  # noqa: BLE001 - the draft is written all the same; up blog lists it
                log.warning("draft %s not told: %s", did, e)
        except Exception as e:  # noqa: BLE001 - try again later, nothing half-written is kept
            log.warning("draft for %s: %s", vid, e)
            st = state()
            st["failed_at"] = now
            write_json(STATE, st)
        return   # one draft a round


def auto_publish(now: float | None = None) -> str | None:
    """With BLOG_AUTO_PUBLISH_HOURS: the oldest clean draft that waited that long goes on the blog, with its one post."""
    if AUTO_PUBLISH_HOURS <= 0:
        return None
    now = now or time.time()
    st = state()
    live = {p["id"] for p in posts()["posts"]} | set(st.get("announced") or [])
    for did, at in sorted((st.get("drafted_at") or {}).items(), key=lambda kv: kv[1]):
        if did in live or did not in st["drafts"] or now - at < AUTO_PUBLISH_HOURS * 3600:
            continue
        a = read_json(os.path.join(PUBLIC, "drafts", st["drafts"][did] + ".json"), {})
        chk = a.get("check") or {}
        if not a or chk.get("unknown_numbers") or chk.get("hype"):
            continue   # waits for a look and up blog publish (--force)
        publish_cli(did, False, False)
        log.info("draft %s published by itself after %.0f h", did, (now - at) / 3600)
        return did
    return None


def auto_note(st: dict, did: str, a: dict) -> str:
    """Whether this draft goes on the blog by itself (auto_publish), said plainly for the up block."""
    at = (st.get("drafted_at") or {}).get(did)
    chk = a.get("check") or {}
    if not at:
        return "never by itself: written before drafts published themselves, only by hand"
    if chk.get("unknown_numbers") or chk.get("hype"):
        return "never by itself: the check marked numbers or wording (up blog publish --force after a read)"
    return f"by itself on {day(at + AUTO_PUBLISH_HOURS * 3600)} {clock(at + AUTO_PUBLISH_HOURS * 3600)}, unless published by hand before"


def drafts_cli() -> int:
    try:
        import cruise_crier
        for line in cruise_crier.status_lines():
            print(line)
    except Exception as e:  # noqa: BLE001
        print(f"cruise:  not read ({e})")
    try:
        import hack_crier
        for line in hack_crier.status_lines():
            print(line)
    except Exception as e:  # noqa: BLE001
        print(f"hack:    not read ({e})")
    try:
        import idni_report
        for line in idni_report.status_lines():
            print(line)
    except Exception as e:  # noqa: BLE001
        print(f"report:  not read ({e})")
    st = state()
    live = {p["id"] for p in posts()["posts"]}
    waiting = [d for d in st["drafts"] if d not in live]
    if not waiting:
        print("blog:    no draft waiting" + ("" if AI_KEY else " (no NEWS_AI_KEY in infra/.env: no drafts are written)"))
    for did in waiting:
        a = read_json(os.path.join(PUBLIC, "drafts", st["drafts"][did] + ".json"), {})
        bad = (a.get("check") or {}).get("unknown_numbers") or []
        print(f"blog:    draft {did}: {(a.get('title') or {}).get('en', '?')}")
        print(f"         read it: {draft_url(st, did)}")
        print(f"         numbers to check: {', '.join(bad)}" if bad else "         every number is in the logbook facts")
        print(f"         publish: up blog publish {did}")
        if AUTO_PUBLISH_HOURS > 0:
            print("         " + auto_note(st, did, a))
    return 0


def numbers_of(f: dict) -> list[str]:
    """The visit in a few lines, straight from the facts counted off the logbook (never from the article's text)."""
    out = []
    if f.get("simulated passengers"):
        out.append(f"{f['simulated passengers']} simulated passengers, every stop a real transaction")
    # one story everywhere: a send the node never answered is a timeout, even where the old rule logged it as a refusal
    old = f.get("refusals logged without any answer from the node (a timeout, counted as refusal by the old rule)") or 0
    acc, ref = f.get("accepted in all"), (f.get("refused in all") or 0) - old
    if acc is not None:
        out.append(f"{acc} transactions accepted by the node" + (f", {ref} refused" if ref > 0 else ", none refused"))
    nw = f.get(NEW_WALLET_FACT)
    if nw:
        n = nw["passengers"]
        out.append(f"our node had no room for the new wallet{'s' if n != 1 else ''} of {n} passenger{'s' if n != 1 else ''} "
                   f"({nw['their sends the node could not take or the ship left out']} sends): not refusals, reported as IDNI #108")
    if old:
        out.append(f"{old} got no answer from our node in time, and the ship counted them as refusals")
    tr = f.get("pirate tricks") or {}
    if tr.get("tried"):
        out.append(f"{tr['tried']} pirate tricks, {tr.get('refused with the expected answer', 0)} refused by the chain with the expected answer")
    for c in f.get("the ship changed for its next call") or []:
        if not c.get("held"):
            out.append(f"the ship changed {c['what']} from {c['from']} to {c['to']}: {c['because']}")
    una = f.get("sends our node did not answer in time (not refusals)")
    if una:
        out.append(f"{una} got no answer from our node in time" + (f", {f['of those, reached the chain after all']} of them reached the chain all the same"
                                                                   if f.get("of those, reached the chain after all") else ""))
    left = f.get("left early")
    if isinstance(left, dict) and left.get("minutes in port") is not None:
        why = left.get("why") or "no reason logged"
        if old and "refus" in why and ref <= 0:
            why = "its brake took the missing answers for refusals"
        out.append(f"the ship left after {left['minutes in port']} minutes: {why}")
    elif f.get("landed") is False:
        out.append("the ship did not land" + (f": {f['why not landed']}" if f.get("why not landed") else ""))
    if f.get("incidents"):
        out.append(f"{len(f['incidents'])} incident report{'s' if len(f['incidents']) != 1 else ''} written during the visit")
    return out


def announce(a: dict, dry: bool) -> None:
    """The one post per article, on Telegram and X with the link (on X the share page, whose card shows the picture;
    X_BLOG_LINK=false posts X the old way, picture without link): the headline, the visit in numbers from the logbook,
    why it matters, the link."""
    import alerts
    link = f"{SITE}/blog/?p={a['id']}"
    nums = numbers_of(a.get("facts") or {})
    parts = [f"📝 <b>{alerts.html.escape(a['title']['en'])}</b>", alerts.html.escape(a["dek"]["en"])]
    if nums:
        parts.append("<b>In numbers</b>\n" + "\n".join("• " + alerts.html.escape(n) for n in nums))
    parts += ["<b>Why it matters</b>\n" + "\n".join("• " + alerts.html.escape(w["en"]) for w in a["why"]),
              f'<a href="{link}">Read it on the Tau HUD blog</a>']
    tg = "\n\n".join(parts)
    lines = [a["title"]["en"], a.get("x") or a["dek"]["en"], "The whole story is on the Tau HUD blog."]
    plain = alerts.x_post(lines, foot="📝 Tau HUD blog", keep=2, with_link=False)
    card = share_page(a) if X_BLOG_LINK and not dry else f"{NODE}/blog/a/{a['id']}.html"
    x = alerts.x_post(lines, card, foot="📝 Tau HUD blog", keep=2, with_link=True) if X_BLOG_LINK else plain
    pic = a.get("image") and (SITE + a["image"] if a["image"].startswith("/") else a["image"])
    if dry:
        print("--- telegram ---\n" + tg + "\n--- x ---\n" + x + f"\n--- picture: {pic or 'none'}"
              + (" (on X as the link's card, $0.20)" if X_BLOG_LINK else " ($0.015)"))
        return
    for out, text in ((alerts.Telegram(), tg), (alerts.X(), x)):
        if not out.enabled():
            print(f"{out.name}: not set up, not posted")
            continue
        if out.name == "telegram":
            ok, _, err = out.send_text(text, picture=pic)
        elif X_BLOG_LINK:
            ok, _, err = out.send_text(text)
            if not ok:   # refused with the link: the picture and the text without it, as before
                print(f"x: with the link not posted ({err}), now without it")
                ok, _, err = out.send_with_picture(plain, pic)
        else:
            ok, _, err = out.send_with_picture(text, pic)
        print(f"{out.name}: {'posted' if ok else 'not posted: ' + err}")


def publish_cli(did: str, dry: bool, force: bool) -> int:
    st = state()
    if did not in st["drafts"]:
        print(f"no draft {did}; waiting: {', '.join(st['drafts']) or 'none'}")
        return 1
    a = read_json(os.path.join(PUBLIC, "drafts", st["drafts"][did] + ".json"), None)
    if not a:
        print(f"the draft file of {did} is gone; write it anew: up blog draft {did.removesuffix('-learnings')}")
        return 1
    chk = a.get("check") or {}
    if (chk.get("unknown_numbers") or chk.get("hype")) and not force:
        print(f"not published: numbers not in the facts {chk.get('unknown_numbers')}, words {chk.get('hype')}; "
              f"read {draft_url(st, did)}, then write it anew (up blog draft {a.get('visit')}) or: up blog publish {did} --force")
        return 1
    p = posts()
    if dry:
        print(f"would publish {did} at {SITE}/blog/?p={did}")
    else:
        a = {k: v for k, v in a.items() if k not in ("status", "model", "check")}
        p["posts"] = [a] + [x for x in p["posts"] if x.get("id") != did]
        write_json(os.path.join(PUBLIC, "posts.json"), p)
        print(f"published: {SITE}/blog/?p={did}  (link preview: {share_page(a)})")
    if did in st.setdefault("announced", []):
        print("already posted to Telegram and X once: not posted again")
        return 0
    announce(a, dry)
    if not dry:
        st["announced"].append(did)
        write_json(STATE, st)
    return 0


def unpublish_cli(did: str) -> int:
    p = posts()
    keep = [x for x in p["posts"] if x.get("id") != did]
    if len(keep) == len(p["posts"]):
        print(f"{did} is not on the blog")
        return 1
    write_json(os.path.join(PUBLIC, "posts.json"), {"posts": keep})
    print(f"{did} taken off the blog")
    return 0


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    cmd = argv[0] if argv else "loop"
    args = [a for a in argv[1:] if not a.startswith("--")]
    if cmd == "drafts":
        return drafts_cli()
    if cmd == "draft" and args:
        if not AI_KEY:
            print("no NEWS_AI_KEY in infra/.env: no draft")
            return 1
        print(f"writing the article of {args[0]}: the model reads the logbook and writes it in three languages, 1 to 4 minutes, "
              "nothing is published", flush=True)
        did = write_draft(args[0])
        print(f"draft {did} written")
        return drafts_cli()
    if cmd == "publish" and args and ID_RE.match(args[0]):
        return publish_cli(args[0], "--dry" in argv, "--force" in argv)
    if cmd == "unpublish" and args and ID_RE.match(args[0]):
        return unpublish_cli(args[0])
    if cmd == "pictures":
        n = site_pictures(force=True)
        print(f"blog:    pictures and link previews made for {n} article{'s' if n != 1 else ''}"
              + ("" if os.path.exists(os.path.join(ART, "index.json")) else " (no island paintings found: no hero pictures)"))
        return 0
    if cmd == "loop":
        log.info("blog drafts: %s", "on" if AI_KEY else "off (no NEWS_AI_KEY)")
        while True:
            try:
                import cruise_crier   # the cruise ships' announcements before and reports after each call
                cruise_crier.step()
            except Exception as e:  # noqa: BLE001
                log.warning("cruise crier: %s", e)
            try:
                import kling_island   # the island painting alive on /rabbit/, and a trailer when it is new (Kling)
                kling_island.step()
            except Exception as e:  # noqa: BLE001
                log.warning("kling island: %s", e)
            try:
                import hack_crier   # the hack of the week: its post after each replay, a finding only to the owner
                hack_crier.step()
            except Exception as e:  # noqa: BLE001
                log.warning("hack crier: %s", e)
            try:
                import idni_report   # the weekly report for IDNI, Sunday 18:00 to the owner's private chat (never filed by itself)
                idni_report.step()
            except Exception as e:  # noqa: BLE001
                log.warning("idni report: %s", e)
            try:
                site_pictures()
                tick()
                auto_publish()
            except Exception as e:  # noqa: BLE001 - the relay may be restarting
                log.warning("tick: %s", e)
            time.sleep(EVERY)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

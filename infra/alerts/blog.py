"""The Tau HUD blog (tauhud.com/blog/): learnings articles drafted from our own data, published only by hand.

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
import urllib.request
from collections import Counter

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
CHECK_WAIT = 3 * 3600      # a visit whose bookings were never checked is drafted this long after it ended
RETRY_AFTER = 2 * 3600
KINDS = ("pay", "bill", "book", "cancel")
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
- Plain words for curious readers who are not developers. No code names, file names, function names or field names.
- No hype or marketing words (huge, exciting, revolutionary, game-changing, finally), no price talk, no coin talk, no \
exclamation marks, no emoji, no names of people.
- Honest and calm, like a good engineering blog: what we saw, what it means, what is still open.
- Length: 250 to 450 English words in body.
- title: at most 70 characters, a real headline with subject and verb. dek: one sentence, at most 160 characters.
- why: two or three lines, each at most 160 characters, that say at a glance why this visit matters: one for the Tau \
community, one for IDNI (what a community node under steady everyday traffic shows them), optionally one for everyone.
- body: Markdown with "## " section headings, short paragraphs and "- " lists. Sections in this order: "What happened", \
"What the logbook shows", "What is still open". No title in body, no links, no tables.
- zh: Simplified Chinese, ja: Japanese, same meaning and the same numbers; keep Tau, IDNI, AGRS, White Rabbit Key and \
the ship names in Latin letters.
- x: one post for X, at most 200 characters, no link, no hashtags: the headline point and why it matters.
- card: the text on the article's picture, English only: "line", at most 60 characters, the point in one line; \
"why", three points of at most 52 characters each that say at a glance why it matters (for the community, for IDNI).

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
    f["sent and accepted"] = {k: v for k, v in (s.get("sent") or {}).items() if v} or \
        dict(Counter(e["kind"] for e in sends if e.get("ok") is True))
    f["refused by the node"] = {k: v for k, v in (s.get("refused") or {}).items() if v} or \
        dict(Counter(e["kind"] for e in sends if e.get("ok") is False))
    f["accepted in all"] = sum(f["sent and accepted"].values())
    f["refused in all"] = sum(f["refused by the node"].values())
    unanswered = [e for e in sends if e.get("ok") is None and "no answer" in str(e.get("note") or "")]
    # before 6 November 2026 a send without an answer was logged as refused with an empty error
    silent = [e for e in sends if e.get("ok") is False and not e.get("err")]
    if unanswered or s.get("unanswered"):
        f["sends our node did not answer in time (not refusals)"] = s.get("unanswered") or len(unanswered)
        if later:
            f["of those, reached the chain after all"] = sum(1 for e in later if e.get("took"))
    if silent:
        f["refusals logged without any answer from the node (a timeout, counted as refusal by the old rule)"] = len(silent)
    reasons = Counter(re.sub(r"[0-9a-f]{16,}", "…", str(e.get("err")))[:120] for e in sends if e.get("ok") is False and e.get("err"))
    if reasons:
        f["refusal answers"] = dict(reasons.most_common(5))
    if s.get("skipped") is not None:
        f["stops skipped"] = s.get("skipped")
    f["sends logged"] = len(sends)
    v = Counter(e.get("verdict") for e in sends if e.get("verdict"))
    if v:
        f["testnet load at each send"] = dict(v)
    if s.get("half") is not None:
        f["sends at half pace because the testnet looked strained"] = s.get("half")
    if sends:
        a = min(e["t"] for e in sends)
        tens = Counter((e["t"] - a) // 600 for e in sends)
        f["sends per 10 minutes"] = [tens.get(i, 0) for i in range(int(max(tens)) + 1)]
        f["first send"], f["last send"] = clock(a), clock(max(e["t"] for e in sends))
        hs = [e.get("height") for e in sends if e.get("height")]
        if hs:
            f["block heights"] = [min(hs), max(hs)]
    if checked:
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
                              "strained testnet": "half pace", "stalled testnet": "it leaves at once"}
    f["answered sends"] = len(answered)
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
def ask_ai(facts: dict) -> dict:
    prompt = "Facts counted from the logbook of one cruise ship visit (JSON):\n\n" + json.dumps(facts, ensure_ascii=False, indent=1)
    body = json.dumps({"model": AI_MODEL, "max_tokens": 6000, "system": SYSTEM,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": AI_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        j = json.load(r)
    text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in the answer: " + text[:200])
    return json.loads(m.group(0))


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
            "facts": facts, "check": {"unknown_numbers": unknown_numbers(en, facts), "hype": sorted({m.group(0) for m in HYPE.finditer(en)})},
            "card": card_of(out.get("card"), title["en"]), "written": int(now), "model": AI_MODEL}


def card_of(c, title: str) -> list[str]:
    """The lines on the hero picture: title, the point, "Why it matters" and up to three short points, the footer."""
    c = c if isinstance(c, dict) else {}
    short = lambda t, n: " ".join(str(t or "").split())[:n]  # noqa: E731
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
    return "liner" if "queen" in name.lower() or a.get("ship") == "liner" else "expedition"


def pictures(a: dict) -> dict:
    """The hero picture (the island's painting with the ship and the card, made only where the paintings are) and
    the charts of the visit's numbers; the article gets their addresses. Without paintings, no hero and no error."""
    import blog_pics
    os.makedirs(IMG, exist_ok=True)
    if a.get("card") and os.path.exists(os.path.join(ART, "index.json")):
        try:
            blog_pics.hero(ART, SHIPS, a["card"], ship_of(a), os.path.join(IMG, a["id"] + "-hero.jpg"))
            a["image"] = f"{NODE}/blog/img/{a['id']}-hero.jpg"
        except Exception as e:  # noqa: BLE001 - an article without its picture beats no article
            log.warning("hero for %s: %s", a["id"], e)
    if a.get("facts"):
        figs = blog_pics.visit_charts(a["facts"], os.path.join(IMG, a["id"]))
        a["figures"] = [{"src": f"{NODE}/blog/img/{os.path.basename(p)}", "caption": cap, "after": i + 1} for i, (p, cap) in enumerate(figs)] \
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
        if force or not os.path.exists(os.path.join(SHARE, a["id"] + ".html")) or (a.get("card") and not os.path.exists(os.path.join(IMG, a["id"] + "-hero.jpg"))):
            if a.get("card") and os.path.exists(os.path.join(ART, "index.json")):
                import blog_pics
                try:
                    os.makedirs(IMG, exist_ok=True)
                    blog_pics.hero(ART, SHIPS, a["card"], ship_of(a), os.path.join(IMG, a["id"] + "-hero.jpg"))
                except Exception as e:  # noqa: BLE001
                    log.warning("hero for %s: %s", a["id"], e)
            share_page(a)
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
    facts = facts_of(entries, inc, cr)
    a = pictures(article(facts, ask_ai(facts), now))
    st = state()
    name = st["drafts"].get(a["id"]) or f"{a['id']}-{secrets.token_hex(4)}"
    st["drafts"][a["id"]], st["drafted"][vid] = name, a["id"]
    a["status"] = "draft"
    write_json(os.path.join(PUBLIC, "drafts", name + ".json"), a)
    write_json(STATE, st)
    return a["id"]


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
        try:
            did = write_draft(vid, now)
            log.info("draft %s written: %s", did, draft_url(state(), did))
        except Exception as e:  # noqa: BLE001 - try again later, nothing half-written is kept
            log.warning("draft for %s: %s", vid, e)
            st = state()
            st["failed_at"] = now
            write_json(STATE, st)
        return   # one draft a round


def drafts_cli() -> int:
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
    return 0


def numbers_of(f: dict) -> list[str]:
    """The visit in a few lines, straight from the facts counted off the logbook (never from the article's text)."""
    out = []
    if f.get("simulated passengers"):
        out.append(f"{f['simulated passengers']} simulated passengers, every stop a real transaction")
    acc, ref = f.get("accepted in all"), f.get("refused in all")
    if acc is not None:
        out.append(f"{acc} transactions accepted by the node" + (f", {ref} refused" if ref else ", none refused"))
    una = f.get("sends our node did not answer in time (not refusals)")
    if una:
        out.append(f"{una} got no answer from our node in time" + (f", {f['of those, reached the chain after all']} of them reached the chain all the same"
                                                                   if f.get("of those, reached the chain after all") else ""))
    left = f.get("left early")
    if isinstance(left, dict) and left.get("minutes in port") is not None:
        out.append(f"the ship left after {left['minutes in port']} minutes: {left.get('why') or 'no reason logged'}")
    elif f.get("landed") is False:
        out.append("the ship did not land" + (f": {f['why not landed']}" if f.get("why not landed") else ""))
    if f.get("incidents"):
        out.append(f"{len(f['incidents'])} incident report{'s' if len(f['incidents']) != 1 else ''} written during the visit")
    return out


def announce(a: dict, dry: bool) -> None:
    """The one post per article, on Telegram with the link and on X without (a link makes an X post 13 times dearer):
    the headline, the visit in numbers from the logbook, why it matters, the link."""
    import alerts
    link = f"{SITE}/blog/?p={a['id']}"
    nums = numbers_of(a.get("facts") or {})
    parts = [f"📝 <b>{alerts.html.escape(a['title']['en'])}</b>", alerts.html.escape(a["dek"]["en"])]
    if nums:
        parts.append("<b>In numbers</b>\n" + "\n".join("• " + alerts.html.escape(n) for n in nums))
    parts += ["<b>Why it matters</b>\n" + "\n".join("• " + alerts.html.escape(w["en"]) for w in a["why"]),
              f'<a href="{link}">Read it on the Tau HUD blog</a>']
    tg = "\n\n".join(parts)
    x = alerts.x_post([a["title"]["en"], a.get("x") or a["dek"]["en"], "The whole story is on the Tau HUD blog."], foot="📝 Tau HUD blog", keep=2)
    pic = a.get("image") and (SITE + a["image"] if a["image"].startswith("/") else a["image"])
    if dry:
        print("--- telegram ---\n" + tg + "\n--- x ---\n" + x + f"\n--- picture: {pic or 'none'}")
        return
    for out, text in ((alerts.Telegram(), tg), (alerts.X(), x)):
        if not out.enabled():
            print(f"{out.name}: not set up, not posted")
            continue
        ok, _, err = out.send_text(text, picture=pic) if out.name == "telegram" else out.send_with_picture(text, pic)
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
                site_pictures()
                tick()
            except Exception as e:  # noqa: BLE001 - the relay may be restarting
                log.warning("tick: %s", e)
            time.sleep(EVERY)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

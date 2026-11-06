"""The news line's watchtower: is the HUD's news line (assets/ticker.js) still fresh, and are its feeds alive?

The line takes old things off by itself: a headline in assets/ticker.json leaves TICKER_DAYS days after its "since"
(or at its "until"), a feature from the Updates log (assets/updates.json "major") TICKER_DAYS days after its day, a
blog article as well, IDNI's news after seven days. Standing pointers ("keep": true) stay. New things come in by
themselves (new majors, blog articles, IDNI's merges, the next cruise ship) or by hand (a headline with "since").

This module looks at the line the way a visitor's page does, every TICKER_WATCH_MINUTES, and finds:

  stale      nothing new on the line for TICKER_STALE_DAYS days
  thin       fewer than TICKER_MIN_FRESH dated items left (the line is about to be only pointers and live numbers)
  undated    a headline with neither "since" nor "keep": it would never leave
  unread     assets/ticker.json cannot be read (the line then shows live numbers only)
  idni       devpulse.json is old or its headline writer is off, so IDNI's news stops coming in

Warnings go to the owner only, in a private Telegram chat with the alerts bot, never to the channel: once when a
problem starts, again every TICKER_REMIND_HOURS while it lasts, and once when all is fresh again; nothing between
22:00 and 08:00 German time (it waits for the morning). The owner is set once with `up owner`: it prints a link
that opens the bot with a one-time code (valid 30 minutes); the bot keeps that chat id in /state/owner.json.
TICKER_OWNER_CHAT in .env sets the chat id directly instead.

  python tickerwatch.py status   what the line holds now and what is wrong, as up prints it
  python tickerwatch.py pair     a new one-time link to make the chat that opens it the owner's
  python tickerwatch.py test     one private test message to the owner
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import secrets
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo

log = logging.getLogger("tickerwatch")

SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
NODE = os.environ.get("NODE_URL", "https://node.tauhud.com").rstrip("/")
STATE_DIR = os.path.dirname(os.environ.get("STATE_PATH", "/state/alerts.json")) or "/state"
PUBLIC_DIR = os.environ.get("PUBLIC_DIR", "/public")
OWNER_PATH = os.environ.get("OWNER_PATH", os.path.join(STATE_DIR, "owner.json"))
WATCH_PATH = os.environ.get("TICKER_WATCH_PATH", os.path.join(STATE_DIR, "tickerwatch.json"))
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
OWNER_CHAT = os.environ.get("TICKER_OWNER_CHAT", "").strip()
BOT_NAME = os.environ.get("TELEGRAM_BOT_USERNAME", "tauhud_alerts_bot").strip().lstrip("@")
ON = os.environ.get("TICKER_WATCH", "true").lower() in ("1", "true", "yes")
EVERY = float(os.environ.get("TICKER_WATCH_MINUTES", 30)) * 60
DAYS = float(os.environ.get("TICKER_DAYS", 14))            # assets/ticker.json "days" wins: the page reads that one
STALE_DAYS = float(os.environ.get("TICKER_STALE_DAYS", 7))
MIN_FRESH = int(os.environ.get("TICKER_MIN_FRESH", 3))
REMIND = float(os.environ.get("TICKER_REMIND_HOURS", 48)) * 3600
PULSE_OLD = float(os.environ.get("TICKER_PULSE_HOURS", 3)) * 3600
IDNI_DAYS = 7                                              # assets/ticker.js loadIdni: a week
QUIET = (22, 8)                                            # German time: no private message from 22:00 to 08:00
BERLIN = ZoneInfo("Europe/Berlin")
PAIR_MINUTES = 30
GLOW = "rabbit/"                                           # assets/ticker.js GLOW: the island game stays on the line

DAY = 86400.0


def path(h) -> str:
    """assets/ticker.js path(): a link without its leading slash, query and hash."""
    s = str(h or "").lstrip("/")
    for c in "?#":
        s = s.split(c, 1)[0]
    return s


def day_ts(d) -> float | None:
    """'2026-11-06' (or a full ISO time) as a UTC timestamp, like Date.parse in the page."""
    s = str(d or "").strip()
    if not s:
        return None
    try:
        if len(s) == 10:
            return dt.datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp()
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


# ---------------- what the line holds ----------------

def line(cfg: dict | None, updates: list | None, blog: list | None, pulse: dict | None, now: float) -> dict:
    """The line as a visitor's page builds it (assets/ticker.js), with each dated item's age. Returns
    {"dated": [...], "standing": [...], "gone": [...], "soon": [...], "undated": [...], "days": n}; an item is
    {"what", "text", "at", "ends"} (at: when it came on the line, ends: when it leaves)."""
    cfg = cfg if isinstance(cfg, dict) else {}
    days = float(cfg.get("days") or DAYS)
    life = days * DAY
    dated, standing, gone, undated, have = [], [], [], [], set()
    for h in cfg.get("headlines") or []:
        if not isinstance(h, dict) or not h.get("text"):
            continue
        until, since = day_ts(h.get("until")), day_ts(h.get("since"))
        by_age = since + life if since is not None and not h.get("keep") else None
        ends = min((x for x in (until, by_age) if x is not None), default=None)
        it = {"what": "headline", "text": str(h["text"]), "at": since, "ends": ends}
        if it["ends"] is not None and now >= it["ends"]:
            gone.append(it)
            continue
        have.add(path(h.get("href")))
        if h.get("keep"):
            standing.append(it)
        elif since is None:
            undated.append(it)
            standing.append(it)
        else:
            dated.append(it)
    majors = [e for e in (updates or []) if isinstance(e, dict) and isinstance(e.get("major"), dict) and e["major"].get("title")
              and not str(e["major"].get("id") or "").startswith("roundup")]
    for e in majors:
        m, at = e["major"], day_ts(e.get("on"))
        if path(m.get("link")) == GLOW:
            continue
        if path(m.get("link")) in have and path(m.get("link")):
            continue
        it = {"what": "feature", "text": str(m["title"]), "at": at, "ends": at + life if at is not None else None}
        (dated if at is not None and now < at + life else gone).append(it)
    if any(path(e["major"].get("link")) == GLOW for e in majors):
        standing.append({"what": "feature", "text": next(e["major"]["title"] for e in reversed(majors) if path(e["major"].get("link")) == GLOW),
                         "at": None, "ends": None})
    for p in blog or []:
        if not isinstance(p, dict) or not p.get("title"):
            continue
        at = day_ts(p.get("on"))
        title = p["title"].get("en") if isinstance(p["title"], dict) else str(p["title"])
        it = {"what": "blog", "text": "Blog: " + str(title or ""), "at": at, "ends": at + life if at is not None else None}
        (dated if at is not None and now < at + life else gone).append(it)
    for n in (pulse or {}).get("news") or []:
        if not isinstance(n, dict) or not n.get("headline"):
            continue
        at = float(n.get("ts") or 0) or None
        it = {"what": "idni", "text": "Testnet: " + str((n["headline"] or {}).get("en") or ""), "at": at, "ends": at + IDNI_DAYS * DAY if at else None}
        (dated if at and now < at + IDNI_DAYS * DAY else gone).append(it)
    dated.sort(key=lambda i: -(i["at"] or 0))
    soon = sorted((i for i in dated if i["ends"] and i["ends"] - now < 2 * DAY), key=lambda i: i["ends"])
    return {"dated": dated, "standing": standing, "gone": gone, "soon": soon, "undated": undated, "days": days}


def problems(ln: dict | None, pulse: dict | None, now: float) -> dict:
    """{key: text} of what is wrong with the line now (empty: all fresh)."""
    out = {}
    if ln is None:
        return {"unread": "assets/ticker.json cannot be read, so the news line shows live numbers only."}
    dated = ln["dated"]
    newest = dated[0] if dated else None
    age = (now - newest["at"]) / DAY if newest and newest["at"] else None
    if newest is None or age is None or age >= STALE_DAYS:
        out["stale"] = (f"Nothing new on the news line for {int(age)} days (newest: “{newest['text']}”)." if newest and age is not None
                        else "Nothing new on the news line: every dated item has left it.")
    if len(dated) < MIN_FRESH:
        out["thin"] = f"Only {len(dated)} new item{'s' if len(dated) != 1 else ''} left on the line; the rest is pointers and live numbers."
    if ln["undated"]:
        out["undated"] = "Headline without a date, it would never leave: " + "; ".join(f"“{i['text']}”" for i in ln["undated"][:3]) + \
                         ". Give it \"since\" (or \"keep\": true) in assets/ticker.json."
    if pulse is None:
        out["idni"] = "devpulse.json does not answer, so IDNI's news no longer comes onto the line."
    else:
        gen = float(pulse.get("generated_at") or 0)
        ai = str(pulse.get("news_ai") or "")
        if now - gen > PULSE_OLD:
            out["idni"] = f"devpulse.json is {int((now - gen) // 3600)} hours old, so IDNI's news no longer comes onto the line (docker compose logs devpulse)."
        elif ai and ai != "on" and not ai.startswith("waiting"):
            out["idni"] = f"IDNI's headline writer is {ai}, so IDNI's news no longer comes onto the line."
    return out


HELP = "What helps: a headline with \"since\" in assets/ticker.json, a \"major\" in assets/updates.json, or a blog article (up blog)."


def message(probs: dict, ln: dict | None, prev: dict, now: float) -> str | None:
    """The private text for this state against the last one told, or None when nothing is to be said."""
    if not probs:
        if not prev:
            return None
        newest = ln["dated"][0]["text"] if ln and ln["dated"] else ""
        return "🗼 News line watchtower: all fresh again." + (f"\nNewest: “{newest}”" if newest else "")
    lines = ["🗼 News line watchtower"] + [f"⚠️ {t}" for t in probs.values()]
    if ln and ln["soon"]:
        lines.append("Leaving within two days: " + "; ".join(f"“{i['text']}”" for i in ln["soon"][:3]))
    if {"stale", "thin"} & set(probs):
        lines.append(HELP)
    return "\n".join(lines)


def due(probs: dict, told: dict, now: float) -> bool:
    """Tell now? A new problem, a reminder after REMIND, or the all-clear after problems."""
    keys, prev = set(probs), set(told.get("problems") or {})
    if not keys:
        return bool(prev)
    if keys - prev:
        return True
    return now - float(told.get("at") or 0) >= REMIND


def quiet(now: float) -> bool:
    h = dt.datetime.fromtimestamp(now, BERLIN).hour
    return h >= QUIET[0] or h < QUIET[1]


# ---------------- reading ----------------

def fetch_json(url: str, timeout: float = 20):
    req = urllib.request.Request(url, headers={"User-Agent": "tauhud-tickerwatch", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def read_all() -> tuple[dict | None, list | None, list, dict | None]:
    """ticker.json, updates.json and the blog from the site (what visitors get), devpulse.json from our volume."""
    def get(url):
        try:
            return fetch_json(url)
        except Exception as e:  # noqa: BLE001 - one feed down is a finding, not a crash
            log.warning("%s: %s", url, e)
            return None
    cfg = get(SITE + "/assets/ticker.json")
    updates = get(SITE + "/assets/updates.json")
    posts = {}
    for src in (get(SITE + "/assets/blog/posts.json"), read_file(os.path.join(PUBLIC_DIR, "blog", "posts.json"))):
        for p in (src or {}).get("posts") or []:
            if isinstance(p, dict) and p.get("id"):
                posts[p["id"]] = p
    pulse = read_file(os.path.join(PUBLIC_DIR, "devpulse.json"))
    if pulse is None:
        pulse = get(NODE + "/devpulse.json")
    return (cfg if isinstance(cfg, dict) else None), (updates if isinstance(updates, list) else None), list(posts.values()), pulse


def read_file(p: str):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_file(p: str, data):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, p)


# ---------------- the owner's private chat ----------------

def owner() -> str:
    return OWNER_CHAT or str((read_file(OWNER_PATH) or {}).get("chat_id") or "")


def tg(method: str, body: dict) -> dict:
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception as e:  # noqa: BLE001 - never log the URL: it holds the token
        return {"ok": False, "description": type(e).__name__}


def tell(text: str) -> tuple[bool, str]:
    """One private message to the owner; never the channel."""
    chat = owner()
    if not TOKEN:
        return False, "no TELEGRAM_BOT_TOKEN"
    if not chat:
        return False, "no owner yet (up owner)"
    r = tg("sendMessage", {"chat_id": chat, "text": text, "link_preview_options": {"is_disabled": True}})
    return bool(r.get("ok")), str(r.get("description") or "")


def pair(now: float | None = None) -> str:
    """A one-time code for the owner link, valid PAIR_MINUTES; the bot checks it (claim)."""
    now = time.time() if now is None else now
    o = read_file(OWNER_PATH) or {}
    o.update(code=secrets.token_urlsafe(12).replace("-", "x").replace("_", "y"), code_until=now + PAIR_MINUTES * 60)
    write_file(OWNER_PATH, o)
    return o["code"]


def claim(chat_id, code: str, now: float | None = None) -> bool:
    """The bot got /start owner-<code> in a private chat: that chat is the owner's if the code is the current one."""
    now = time.time() if now is None else now
    o = read_file(OWNER_PATH) or {}
    want = str(o.get("code") or "")
    if not want or not secrets.compare_digest(want, str(code or "")) or now > float(o.get("code_until") or 0):
        return False
    o.update(chat_id=chat_id, paired_at=now)
    o.pop("code", None)
    o.pop("code_until", None)
    write_file(OWNER_PATH, o)
    return True


# ---------------- the loop step (alerts.py calls it) ----------------

class Watch:
    def __init__(self):
        self.next_at = 0.0

    def step(self, now: float | None = None, data=None) -> dict:
        """Look once (at most every EVERY); tell the owner when due. Returns the problems found."""
        now = time.time() if now is None else now
        if not ON or now < self.next_at:
            return {}
        self.next_at = now + EVERY
        cfg, updates, blog, pulse = data if data is not None else read_all()
        ln = line(cfg, updates, blog, pulse, now) if cfg is not None else None
        probs = problems(ln, pulse, now)
        told = read_file(WATCH_PATH) or {}
        if due(probs, told, now) and not quiet(now):
            text = message(probs, ln, told.get("problems") or {}, now)
            if text:
                ok, why = tell(text)
                if ok:
                    told = {"problems": probs, "at": now}
                    log.info("news line watchtower: told the owner (%s)", ", ".join(probs) or "all fresh")
                elif now - getattr(self, "warned_at", 0) >= DAY:   # no owner yet: in the log once a day, not every half hour
                    self.warned_at = now
                    log.warning("news line watchtower: %s; not told: %s", why, "; ".join(probs.values()) or "all fresh")
        if not probs and not told.get("problems"):
            told = {"problems": {}, "at": told.get("at") or 0}
        told["seen"] = {"at": now, "problems": probs, "dated": len(ln["dated"]) if ln else 0}
        try:
            write_file(WATCH_PATH, told)
        except OSError as e:
            log.warning("news line watchtower: %s", e)
        return probs


# ---------------- command line ----------------

def status(now: float | None = None, data=None) -> list[str]:
    now = time.time() if now is None else now
    cfg, updates, blog, pulse = data if data is not None else read_all()
    ln = line(cfg, updates, blog, pulse, now) if cfg is not None else None
    probs = problems(ln, pulse, now)
    out = []
    if ln:
        newest = ln["dated"][0] if ln["dated"] else None
        age = f"{(now - newest['at']) / DAY:.0f} days old" if newest and newest["at"] else ""
        out.append(f"ticker:  {len(ln['dated'])} new items (leave after {ln['days']:g} days), {len(ln['standing'])} standing, "
                   f"{len(ln['gone'])} gone by age" + (f"; newest {age}: {newest['text']}" if newest else ""))
        for i in ln["soon"][:3]:
            out.append(f"         leaving {dt.datetime.fromtimestamp(i['ends'], BERLIN):%a %d.%m.}: {i['text']}")
    for t in probs.values():
        out.append(f"         ⚠️ {t}")
    if not probs and ln:
        out.append("         fresh")
    who = owner()
    out.append("         watchtower warnings: " + ("to the owner's private Telegram chat" if who and TOKEN else
                                                    "nobody gets them yet, run: up owner" if TOKEN else "off (no TELEGRAM_BOT_TOKEN)"))
    return out


def bot_name() -> str:
    r = tg("getMe", {}) if TOKEN else {}
    return ((r or {}).get("result") or {}).get("username") or BOT_NAME


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    cmd = argv[1] if len(argv) > 1 else "status"
    if cmd == "status":
        print("\n".join(status()))
        return 0
    if cmd == "pair":
        if not TOKEN:
            print("owner:   no TELEGRAM_BOT_TOKEN in infra/.env, the bot cannot write to you")
            return 1
        code = pair()
        print(f"owner:   open this link on the phone with your Telegram and press Start (valid {PAIR_MINUTES} minutes, once):")
        print(f"         https://t.me/{bot_name()}?start=owner-{code}")
        print("         then test it: up owner test")
        return 0
    if cmd == "test":
        ok, why = tell("🗼 News line watchtower: connected. Warnings about a stale news line come here, only to you.")
        print("owner:   test message sent" if ok else f"owner:   NOT sent: {why}")
        return 0 if ok else 1
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

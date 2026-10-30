"""Visitor numbers for the site owner: which pages people open, stay on and come from. No cookies, nothing personal kept.

Every page's header (assets/nav.js) sends one GET /v when it opens and, if the page stayed visible for 30 seconds,
one more with e=1. The relay keeps only counts per UTC day: views, visitors and engaged views per page, where people
came from (the other site's host name, a ?ref= / utm_source tag, or the previous Tau HUD page), language, sim or live
view and hour of day (screen class only from requests that still carry w=; the pages no longer send it). When the page
is left or hidden, one more GET with t=<seconds the page was visible> adds one to a time step per page (under 10 s,
10-30 s, 30 s-1 min, 1-3 min, 3-10 min, longer); the seconds themselves are not kept.

A "visitor" is counted with a hash of a random daily salt, the address and the browser's user agent. The salt lives in
memory only and is replaced at 00:00 UTC, so a hash cannot be traced back or linked across days, and the addresses
themselves are never stored. Nothing is stored in the visitor's browser. Requests with Do Not Track or Global Privacy
Control, and bots by user agent, are not counted.

GET /v?p=<page>&r=<referrer>&s=<tag>&l=en|zh&m=sim|live&w=<width>[&e=1]   count (204, empty)
GET /v?p=<page>&t=<seconds>                                               time on that page, as a step
GET /visits?key=<key>                                                     the owner's report page (visits.html)
GET /visits.json?key=<key>[&days=<n>]                                     the counts behind it
GET /visits/public                                                        totals anyone may see (tauhud.com/meta/): per day
                                                                          visitors, views, stayed, visitors per page, language
                                                                          and screen, time steps per page, visitors and views
                                                                          per hour for the last
                                                                          two days; no referrers or tags

Agorzilla (agorzilla.com, our second site) sends the same requests with p=agorzilla. Its numbers are kept apart, under
"sites" -> "agorzilla" in each day, with the same fields, so Tau HUD's own numbers do not change; /visits/public lists
them under "sites" for the switch on tauhud.com/meta/.

The key comes from VISITS_KEY or, if that is empty, is made once and kept in /data/visits.key.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from urllib.parse import unquote

log = logging.getLogger("relay.visits")

DAY = 86400
KEEP_DAYS = 400
HOUR_DAYS = 31     # days whose hour-by-hour counts /visits/public shows (24H, 7D and 30D on /meta/)
ENGAGED_SECONDS = 30          # nav.js sends e=1 after this much visible time
MAX_KEYS = {"views": 150, "refs": 300, "sources": 100, "flows": 400}   # distinct keys per day; the rest goes to "(other)"
PAGE = re.compile(r"^[a-z0-9][a-z0-9/_-]{0,47}$")
HOST = re.compile(r"^[a-z0-9.-]{1,80}\.[a-z]{2,24}$")
TAG = re.compile(r"^[a-z0-9._-]{1,40}$")
BOT = re.compile(r"bot|crawl|spider|slurp|headless|preview|fetch|curl|wget|python|httpx|go-http|java/|monitor|lighthouse|pingdom|facebookexternalhit|embedly", re.I)
OWN_HOSTS = {"": ("tauhud.com", "www.tauhud.com", "jimb000o.github.io"), "agorzilla": ("agorzilla.com", "www.agorzilla.com")}
SITES = ("agorzilla",)   # other sites we run: a page named like the site, or below it, is counted for that site
BURST, REFILL = 20.0, 0.5
TIME_STEPS = (10, 30, 60, 180, 600)   # seconds; a visible time falls into one of len + 1 steps


def screen(width: str) -> str:
    try:
        w = int(width)
    except ValueError:
        return "?"
    return "phone" if w < 700 else "tablet" if w < 1280 else "laptop" if w < 1600 else "desktop" if w < 2400 else "wide"


def _day_str(day: int) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(day * DAY))


def _bump(d: dict, key: str, cap: int | None = None, n: int = 1):
    if cap is not None and key not in d and len(d) >= cap:
        key = "(other)"
    d[key] = d.get(key, 0) + n


class Visits:
    def __init__(self, path: str | None = None, key_path: str | None = None, clock=time.time):
        self.path = path if path is not None else os.environ.get("VISITS_PATH", "/data/visits.json")
        self.clock = clock
        self.days: dict[str, dict] = {}
        self.day = -1
        self.salt = b""
        self.seen: set[str] = set()                   # today's visitor hashes, memory only
        self.seen_page: set[tuple[str, str]] = set()  # (hash, page), memory only
        self.seen_hour: set[tuple[str, int]] = set()  # (hash, hour), memory only
        self.buckets: dict[str, list] = {}            # address -> [tokens, last], memory only
        self.dirty_since = 0.0
        self.key = os.environ.get("VISITS_KEY", "").strip() or self._load_key(
            key_path if key_path is not None else os.environ.get("VISITS_KEY_PATH", "/data/visits.key"))
        self._load()
        self._roll()

    # ---------- storage ----------
    @staticmethod
    def _load_key(path: str) -> str:
        try:
            with open(path) as f:
                k = f.read().strip()
            if len(k) >= 16:
                return k
        except FileNotFoundError:
            pass
        except OSError as exc:
            log.warning("cannot read %s: %r", path, exc)
        k = secrets.token_hex(16)
        try:
            with open(path, "w") as f:
                f.write(k + "\n")
            os.chmod(path, 0o600)
        except OSError as exc:
            log.warning("cannot write %s: %r; the report key lasts until the next restart", path, exc)
        return k

    def _load(self):
        try:
            with open(self.path) as f:
                st = json.load(f)
            if isinstance(st, dict) and isinstance(st.get("days"), dict):
                self.days = st["days"]
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s: %r; counting afresh", self.path, exc)

    def save(self, force: bool = False):
        """Writes at most every 30 s while counts change; force on shutdown."""
        if not self.dirty_since or (not force and self.clock() - self.dirty_since < 30):
            return
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"days": self.days}, f, separators=(",", ":"))
            os.replace(tmp, self.path)
            self.dirty_since = 0.0
        except OSError as exc:
            if not getattr(self, "_warned", False):
                log.warning("cannot write %s: %r; visitor numbers live in memory only", self.path, exc)
                self._warned = True

    def _roll(self):
        d = int(self.clock() // DAY)
        if d != self.day:
            self.day, self.salt = d, secrets.token_bytes(32)
            self.seen, self.seen_page, self.seen_hour = set(), set(), set()
            for old in [k for k in self.days if k < _day_str(d - KEEP_DAYS)]:
                del self.days[old]

    def _today(self, site: str = "") -> dict:
        t = self.days.setdefault(_day_str(self.day), self._fresh())
        return t.setdefault("sites", {}).setdefault(site, self._fresh()) if site else t

    @staticmethod
    def _fresh() -> dict:
        return {
            "visitors": 0, "views": {}, "uniques": {}, "engaged": {}, "refs": {}, "sources": {},
            "flows": {}, "lang": {}, "mode": {}, "screen": {}, "hours": [0] * 24, "hvis": [0] * 24, "time": {}}

    def _take(self, ip: str) -> bool:
        now = self.clock()
        b = self.buckets.get(ip) or [BURST, now]
        b[0] = min(BURST, b[0] + (now - b[1]) * REFILL)
        b[1] = now
        self.buckets[ip] = b
        if len(self.buckets) > 20000:
            self.buckets = {ip: b}
        if b[0] < 1:
            return False
        b[0] -= 1
        return True

    # ---------- counting ----------
    def person(self, ip: str, ua: str) -> str:
        """The in-memory key one browser gets today: the daily salt hashed with its address
        and user agent. Also tells the relay's online counter which sockets belong to one
        person (tabs, pages, reconnects), without anything stored in the browser."""
        self._roll()
        return hashlib.sha256(self.salt + ip.encode() + b"|" + ua.encode()).hexdigest()[:20]

    def count(self, q: dict, ip: str, ua: str, dnt: bool = False) -> bool:
        """True if the hit was counted."""
        page = q.get("p", "")
        if dnt or not ua or BOT.search(ua) or not PAGE.match(page) or not self._take(ip):
            return False
        self._roll()
        site = page.split("/")[0] if page.split("/")[0] in SITES else ""
        t = self._today(site)
        visitor = site + self.person(ip, ua)   # one person on both sites is one visitor on each
        if q.get("t"):
            try:
                secs = int(q["t"])
            except ValueError:
                return False
            if (visitor, page) not in self.seen_page or not 0 <= secs <= DAY:
                return False
            tm = t.setdefault("time", {})
            if page not in tm and len(tm) >= MAX_KEYS["views"]:
                page = "(other)"
            row = tm.setdefault(page, [0] * (len(TIME_STEPS) + 1))
            row[sum(secs >= s for s in TIME_STEPS)] += 1
        elif q.get("e") == "1":
            if (visitor, page) not in self.seen_page:
                return False
            _bump(t["engaged"], page, MAX_KEYS["views"])
        else:
            _bump(t["views"], page, MAX_KEYS["views"])
            if visitor not in self.seen:
                self.seen.add(visitor)
                t["visitors"] += 1
                _bump(t["lang"], q.get("l") if q.get("l") in ("zh", "ja") else "en")
                if q.get("w"):   # older pages only: the site stopped reading the window width (TDDDG § 25)
                    _bump(t["screen"], screen(q["w"]))
            if (visitor, page) not in self.seen_page:
                self.seen_page.add((visitor, page))
                _bump(t["uniques"], page, MAX_KEYS["views"])
            _bump(t["mode"], "live" if q.get("m") == "live" else "sim")
            hour = int(self.clock() % DAY // 3600)
            t["hours"][hour] += 1
            if (visitor, hour) not in self.seen_hour:   # different people in this hour (same daily hash)
                self.seen_hour.add((visitor, hour))
                t.setdefault("hvis", [0] * 24)[hour] += 1
            ref = q.get("r", "").lower()
            if ref.startswith("/"):
                src = ref[1:] or "hud"
                if PAGE.match(src) and src != page:
                    _bump(t["flows"], f"{src}>{page}", MAX_KEYS["flows"])
            else:
                host = ref[4:] if ref.startswith("www.") else ref
                if HOST.match(host) and host not in OWN_HOSTS[site]:
                    _bump(t["refs"], host, MAX_KEYS["refs"])
                elif not ref:
                    _bump(t["refs"], "(direct)", MAX_KEYS["refs"])
            tag = q.get("s", "").lower()
            if TAG.match(tag):
                _bump(t["sources"], tag, MAX_KEYS["sources"])
        if not self.dirty_since:
            self.dirty_since = self.clock()
        self.save()
        return True

    def report(self, days: int = 90) -> dict:
        self._roll()
        self.save()
        first = _day_str(self.day - max(1, min(days, KEEP_DAYS)) + 1)
        return {"now": round(self.clock()), "today": _day_str(self.day), "engaged_seconds": ENGAGED_SECONDS,
                "days": {k: v for k, v in sorted(self.days.items()) if k >= first}}

    def public(self) -> dict:
        """Per day [visitors, views, stayed, {page: visitors}, {lang: visitors}, {screen: visitors}, {page: time steps},
        pages opened from our other site], plus for the last HOUR_DAYS days [visitors per hour, views per hour] (the 24H,
        7D and 30D charts on /meta/); the same again per other site under "sites";
        cached for a minute."""
        now = self.clock()
        if getattr(self, "_pub", None) and now - self._pub[0] < 60:
            return self._pub[1]
        self._roll()
        recent = [_day_str(self.day - i) for i in range(HOUR_DAYS - 1, -1, -1)]

        def totals(days: dict, site: str = "") -> dict:
            # the last field: pages opened from a link on our other site (agorzilla.com <-> tauhud.com)
            other = {h[4:] if h.startswith("www.") else h for s_, hs in OWN_HOSTS.items() if s_ != site for h in hs}
            return {"days": {k: [d.get("visitors", 0), sum(d.get("views", {}).values()), sum(d.get("engaged", {}).values()),
                                 d.get("uniques", {}), d.get("lang", {}), d.get("screen", {}), d.get("time", {}),
                                 sum(n for h, n in d.get("refs", {}).items() if h in other)]
                             for k, d in sorted(days.items())},
                    "hours": {k: [days[k].get("hvis", [0] * 24), days[k].get("hours", [0] * 24)] for k in recent if k in days}}
        out = {"now": round(now), "today": _day_str(self.day), "engaged_seconds": ENGAGED_SECONDS, "time_steps": TIME_STEPS,
               **totals(self.days),
               "sites": {s: totals({k: d["sites"][s] for k, d in self.days.items() if s in d.get("sites", {})}, s) for s in SITES}}
        self._pub = (now, out)
        return out

    # ---------- HTTP ----------
    def key_ok(self, q: dict) -> bool:
        return bool(self.key) and hmac.compare_digest(q.get("key", ""), self.key)

    def route(self, path: str, query: str, ip: str, headers) -> tuple[int, str, bytes] | None:
        """(status, content type, body) for /v, /visits, /visits.json and /visits/public; None for any other path."""
        if path not in ("/v", "/visits", "/visits.json", "/visits/public"):
            return None
        if path == "/visits/public":
            return 200, "application/json", json.dumps(self.public(), separators=(",", ":")).encode()
        q = {}
        for part in query.split("&"):
            k, _, v = part.partition("=")
            if k:
                q[unquote(k)] = unquote(v)[:100]
        if path == "/v":
            dnt = headers.get("DNT") == "1" or headers.get("Sec-GPC") == "1"
            self.count(q, ip, headers.get("User-Agent", ""), dnt)
            return 204, "text/plain", b""
        if not self.key_ok(q):
            return 404, "text/plain", b"not found\n"
        if path == "/visits.json":
            try:
                days = int(q.get("days", "90"))
            except ValueError:
                days = 90
            return 200, "application/json", json.dumps(self.report(days), separators=(",", ":")).encode()
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "visits.html"), "rb") as f:
                return 200, "text/html; charset=utf-8", f.read()
        except OSError:
            return 500, "text/plain", b"report page missing\n"

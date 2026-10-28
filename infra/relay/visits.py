"""Visitor numbers for the site owner: which pages people open, stay on and come from. No cookies, nothing personal kept.

Every page's header (assets/nav.js) sends one GET /v when it opens and, if the page stayed visible for 30 seconds,
one more with e=1. The relay keeps only counts per UTC day: views, visitors and engaged views per page, where people
came from (the other site's host name, a ?ref= / utm_source tag, or the previous Tau HUD page), language, sim or live
view, screen class and hour of day.

A "visitor" is counted with a hash of a random daily salt, the address and the browser's user agent. The salt lives in
memory only and is replaced at 00:00 UTC, so a hash cannot be traced back or linked across days, and the addresses
themselves are never stored. Nothing is stored in the visitor's browser. Requests with Do Not Track or Global Privacy
Control, and bots by user agent, are not counted.

GET /v?p=<page>&r=<referrer>&s=<tag>&l=en|zh&m=sim|live&w=<width>[&e=1]   count (204, empty)
GET /visits?key=<key>                                                     the owner's report page (visits.html)
GET /visits.json?key=<key>[&days=<n>]                                     the counts behind it
GET /visits/public                                                        totals anyone may see (tauhud.com/meta/): per day
                                                                          visitors, views, stayed, visitors per page, language
                                                                          and screen; no referrers, tags or hours

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
ENGAGED_SECONDS = 30          # nav.js sends e=1 after this much visible time
MAX_KEYS = {"views": 150, "refs": 300, "sources": 100, "flows": 400}   # distinct keys per day; the rest goes to "(other)"
PAGE = re.compile(r"^[a-z0-9][a-z0-9/_-]{0,47}$")
HOST = re.compile(r"^[a-z0-9.-]{1,80}\.[a-z]{2,24}$")
TAG = re.compile(r"^[a-z0-9._-]{1,40}$")
BOT = re.compile(r"bot|crawl|spider|slurp|headless|preview|fetch|curl|wget|python|httpx|go-http|java/|monitor|lighthouse|pingdom|facebookexternalhit|embedly", re.I)
OWN_HOSTS = ("tauhud.com", "www.tauhud.com", "jimb000o.github.io")
BURST, REFILL = 20.0, 0.5


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
            self.seen, self.seen_page = set(), set()
            for old in [k for k in self.days if k < _day_str(d - KEEP_DAYS)]:
                del self.days[old]

    def _today(self) -> dict:
        return self.days.setdefault(_day_str(self.day), {
            "visitors": 0, "views": {}, "uniques": {}, "engaged": {}, "refs": {}, "sources": {},
            "flows": {}, "lang": {}, "mode": {}, "screen": {}, "hours": [0] * 24})

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
    def count(self, q: dict, ip: str, ua: str, dnt: bool = False) -> bool:
        """True if the hit was counted."""
        page = q.get("p", "")
        if dnt or not ua or BOT.search(ua) or not PAGE.match(page) or not self._take(ip):
            return False
        self._roll()
        t = self._today()
        visitor = hashlib.sha256(self.salt + ip.encode() + b"|" + ua.encode()).hexdigest()[:20]
        if q.get("e") == "1":
            if (visitor, page) not in self.seen_page:
                return False
            _bump(t["engaged"], page, MAX_KEYS["views"])
        else:
            _bump(t["views"], page, MAX_KEYS["views"])
            if visitor not in self.seen:
                self.seen.add(visitor)
                t["visitors"] += 1
                _bump(t["lang"], "zh" if q.get("l") == "zh" else "en")
                _bump(t["screen"], screen(q.get("w", "")))
            if (visitor, page) not in self.seen_page:
                self.seen_page.add((visitor, page))
                _bump(t["uniques"], page, MAX_KEYS["views"])
            _bump(t["mode"], "live" if q.get("m") == "live" else "sim")
            t["hours"][int(self.clock() % DAY // 3600)] += 1
            ref = q.get("r", "").lower()
            if ref.startswith("/"):
                src = ref[1:] or "hud"
                if PAGE.match(src) and src != page:
                    _bump(t["flows"], f"{src}>{page}", MAX_KEYS["flows"])
            else:
                host = ref[4:] if ref.startswith("www.") else ref
                if HOST.match(host) and host not in OWN_HOSTS:
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
        """Per day [visitors, views, stayed, {page: visitors}, {lang: visitors}, {screen: visitors}], cached for a minute."""
        now = self.clock()
        if getattr(self, "_pub", None) and now - self._pub[0] < 60:
            return self._pub[1]
        self._roll()
        out = {"now": round(now), "today": _day_str(self.day), "engaged_seconds": ENGAGED_SECONDS,
               "days": {k: [d.get("visitors", 0), sum(d.get("views", {}).values()), sum(d.get("engaged", {}).values()),
                            d.get("uniques", {}), d.get("lang", {}), d.get("screen", {})]
                        for k, d in sorted(self.days.items())}}
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

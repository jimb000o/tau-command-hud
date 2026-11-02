"""White Rabbit Key's shared island: every campaign played today, added up, the same for everyone.

Each visitor still plays their own five days against the three rivals in their browser (rabbit/game.js), and
nobody waits for anybody. What makes it one island: each move a visitor makes in their own campaign is also told
to this relay as a few short words (no free text), and the relay adds them up for the UTC day. Every page on the
island gets the same small summary pushed every PUSH seconds, whether one person plays today or thousands: the
message does not grow with the number of players, only the numbers in it do.

When few people play, the islanders keep their own politics going: every HOUSE_EVERY seconds without enough
players' moves, the four candidates make one move of their own here (a law proposed, a talk on the square, a line
on the radio, an embassy's money, a pact), chosen from the clock so a restart picks up the same day. They are
counted apart from the players' moves (`islanders`) and the game labels them as the islanders', never as players.

WebSocket commands (relay.py hands them over; replies and pushes have command "isle"):
  isle join                                   the day so far, and a push on this socket whenever it changes
  isle leave                                  no more pushes
  isle move <game> <as> <kind> <what> <place> one of the visitor's own moves in their campaign <game>
  isle end <game> <as> <winner> [laws]        the campaign's election result, and the laws in force at its end (a,b,c)
GET /isle                                     the day so far as JSON

The week (Monday to Sunday, Europe/Berlin, the island's clock): the candidate who won the most finished campaigns
in a week governs the island the week after, and the laws most often in force at the end of those campaigns are in
force on the island that week: the game starts every new campaign with them (`last`), and the islanders too.
The running week is `week`; both are kept in ISLE_PATH with the day.

Limits, so a page left open or a script cannot inflate the island: a few moves per address per minute, at most
GAMES_PER_IP campaigns and MOVES_PER_IP moves per address per day; a campaign counts once, its result once.
The day is kept in ISLE_PATH (the relay's data volume) so a restart does not empty it.
"""
from __future__ import annotations

import asyncio
import calendar
import datetime as dt
import json
import logging
import os
import random
import re
import time
from collections import deque

log = logging.getLogger("isle")

CANDS = {   # rabbit/game.js CANDS: what each cares about and how they campaign
    "marisol": (("fish", "roads"), "rumours"),
    "tobias": (("visitors", "music"), "money"),
    "baako": (("visitors", "roads"), "people"),
    "hana": (("school", "quiet"), "laws"),
}
TOPICS = ("fish", "school", "music", "quiet", "visitors", "roads")
LAWS = {   # rabbit/game.js LAWS: what a law does for each topic, and which laws it cannot stand beside
    "night": ({"music": 1, "visitors": 1, "quiet": -1}, ("quiet",)),
    "quiet": ({"quiet": 2, "music": -1}, ("night", "concerts")),
    "reef": ({"fish": 2, "visitors": -1}, ("harbour",)),
    "harbour": ({"visitors": 2, "roads": 1, "fish": -2}, ("reef",)),
    "boat": ({"school": 2, "roads": 1}, ()),
    "lunch": ({"school": 1, "fish": 1}, ()),
    "concerts": ({"music": 2, "visitors": 1, "quiet": -1}, ("quiet",)),
    "road": ({"roads": 2, "visitors": 1, "quiet": -1}, ()),
    "copy": ({}, ()),
    "tax": ({"roads": 2, "visitors": -1}, ()),
}
EMB = {"north": "harbour", "south": "road"}   # what each embassy pays for
KINDS = ("law", "down", "refused", "talk", "lie", "fact", "deal", "pact", "broke", "gift")
BUILDS = ("roof", "lamp", "stone")   # what a visitor's savings can buy for the island; the island keeps the count
PLACES = ("hall", "market", "radio", "north", "south", "bar", "book", "pier", "school", "dive", "works", "camp", "ship",
          "ama", "canoe", "stone", "drums", "circle", "grotto")
WHAT = set(LAWS) | set(TOPICS) | set(CANDS) | set(EMB) | set(BUILDS) | {"-"}
GAME = re.compile(r"^[a-z0-9]{6,16}$")
LAWLIST = re.compile(r"^[a-z,-]{1,120}$")

PUSH = 10                 # seconds between two pushes, at most
HOUSE_EVERY = 180         # the islanders make a move of their own this often while few people play
FLOOR = 10                # "few": fewer players' moves than this in the last FLOOR_WINDOW seconds
FLOOR_WINDOW = 900
RECENT = 12
GAMES_PER_IP, MOVES_PER_IP = 30, 900
IP_BURST, IP_REFILL = 20, 1 / 3
KEEP_GAMES = 200_000      # campaigns remembered for the day (beyond, they are still counted, once per move)


def score(law: str, cares) -> int:
    return sum(LAWS[law][0].get(c, 0) for c in cares)


def day_of(t: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(t))


def berlin(t: float) -> dt.date:
    """The island's calendar day (Europe/Berlin) at the moment t, with or without the system's zone files."""
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.fromtimestamp(t, ZoneInfo("Europe/Berlin")).date()
    except Exception:   # no tzdata: central European time, summer time from the last Sunday of March to the last of October, 01:00 UTC
        y = time.gmtime(t).tm_year
        last_sun = lambda m: max(d for d in range(25, 32) if calendar.weekday(y, m, d) == 6)   # noqa: E731
        on, off = calendar.timegm((y, 3, last_sun(3), 1, 0, 0)), calendar.timegm((y, 10, last_sun(10), 1, 0, 0))
        return (dt.datetime.fromtimestamp(t, dt.timezone.utc) + dt.timedelta(hours=2 if on <= t < off else 1)).date()


def week_of(t: float) -> dict:
    """A blank week: its id, Monday and Sunday, and empty counts."""
    d = berlin(t)
    mon = d - dt.timedelta(days=d.weekday())
    y, w, _ = d.isocalendar()
    return {"id": f"{y}-W{w:02d}", "from": mon.isoformat(), "to": (mon + dt.timedelta(days=6)).isoformat(),
            "campaigns": 0, "finished": 0, "wins": {}, "laws": {}}


def verdict(week: dict) -> dict | None:
    """What a finished week decides: the governor (most wins) and the laws of the week (the most often in force at the
    end of finished campaigns, at most three, none contradicting a stronger one). None when nobody finished a campaign."""
    if not week.get("finished"):
        return None
    wins = week["wins"]
    governor = max(sorted(wins), key=lambda c: wins[c])
    laws: list[str] = []
    for law in sorted(week["laws"], key=lambda l: (-week["laws"][l], l)):
        if law in LAWS and not any(law in LAWS[l][1] or l in LAWS[law][1] for l in laws):
            laws.append(law)
        if len(laws) == 3:
            break
    return {"id": week["id"], "from": week["from"], "to": week["to"], "campaigns": week["campaigns"], "finished": week["finished"],
            "wins": wins, "governor": governor, "laws": laws}


class Bucket:
    def __init__(self, burst: float, refill: float, now: float):
        self.burst, self.refill, self.tokens, self.at = burst, refill, burst, now

    def take(self, now: float) -> bool:
        self.tokens = min(self.burst, self.tokens + (now - self.at) * self.refill)
        self.at = now
        if self.tokens < 1:
            return False
        self.tokens -= 1
        return True


def blank() -> dict:
    return {"campaigns": 0, "finished": 0, "moves": 0, "as": {}, "wins": {}, "laws": {}, "kinds": {}}


class Isle:
    def __init__(self, path: str | None = None, clock=time.time, house: bool = True):
        self.path = path if path is not None else os.environ.get("ISLE_PATH", "/data/isle.json")
        self.clock = clock
        self.house_on = house
        self.subs = set()
        self.week = week_of(clock())
        self.last: dict | None = None
        self.reset(day_of(clock()))
        self.load()
        self.pushed = -1
        self.dirty = False

    # ---------- the day ----------
    def reset(self, day: str):
        self.day = day
        self.players = blank()
        self.islanders = {"moves": 0, "laws": {}, "kinds": {}, "inforce": list(self.last["laws"]) if self.last else []}
        self.built: dict[str, int] = {}   # what the players bought for the island, all time, never reset
        self.recent: deque = deque(maxlen=RECENT)
        self.games: dict[str, list] = {}    # campaign -> [as, ended]
        self.ips: dict[str, list] = {}      # address -> [bucket, campaigns, moves]
        self.times: deque = deque(maxlen=200_000)       # when the last players' moves came, for the floor
        self.last_house = 0.0
        self.v = 0

    def roll(self, now: float):
        d = day_of(now)
        if week_of(now)["id"] != self.week["id"]:
            self.last = verdict(self.week) or self.last   # a week nobody finished changes nothing
            self.week = week_of(now)
            self.dirty = True
            if d == self.day:
                self.islanders["inforce"] = list(self.last["laws"]) if self.last else []
        if d != self.day:
            self.reset(d)
            self.v += 1

    def load(self):
        try:
            with open(self.path) as f:
                s = json.load(f)
        except (OSError, ValueError):
            return
        if not isinstance(s, dict):
            return
        self.built = {k: int(v) for k, v in s.get("built", {}).items() if k in BUILDS}
        w = s.get("week")
        if isinstance(w, dict) and w.get("id") and all(k in w for k in week_of(0)):
            self.week = w
        if isinstance(s.get("last"), dict) and s["last"].get("governor") in CANDS:
            self.last = s["last"]
        if week_of(self.clock())["id"] != self.week["id"]:
            self.last = verdict(self.week) or self.last
            self.week = week_of(self.clock())
            self.dirty = True
        self.islanders["inforce"] = list(self.last["laws"]) if self.last else []
        if s.get("day") != self.day:
            return
        self.players.update({k: s["players"][k] for k in blank() if k in s.get("players", {})})
        for k in ("moves", "laws", "kinds", "inforce"):
            if k in s.get("islanders", {}):
                self.islanders[k] = s["islanders"][k]
        self.recent.extend(s.get("recent", [])[:RECENT][::-1])

    def save(self):
        if not self.path or not self.dirty:
            return
        self.dirty = False
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"day": self.day, "players": self.players, "islanders": self.islanders, "recent": list(self.recent), "built": self.built,
                           "week": self.week, "last": self.last}, f)
            os.replace(tmp, self.path)
        except OSError as exc:
            log.warning("cannot write %s: %r; the island's day lives in memory only", self.path, exc)

    def changed(self, ev: dict | None = None):
        if ev:
            self.recent.appendleft(ev)
        self.v += 1
        self.dirty = True

    # ---------- what the pages tell ----------
    def limit(self, ip: str, now: float, game: str | None = None) -> str | None:
        if len(self.ips) > 50_000:
            self.ips.clear()
        r = self.ips.setdefault(ip, [Bucket(IP_BURST, IP_REFILL, now), set(), 0])
        if not r[0].take(now):
            return "busy"
        if game is not None and game not in r[1]:
            if len(r[1]) >= GAMES_PER_IP:
                return "enough"
            r[1].add(game)
        if r[2] >= MOVES_PER_IP:
            return "enough"
        r[2] += 1
        return None

    def campaign(self, game: str, who: str) -> list:
        g = self.games.get(game)
        if g is None:
            g = [who, False]
            if len(self.games) < KEEP_GAMES:
                self.games[game] = g
            self.players["campaigns"] += 1
            self.players["as"][who] = self.players["as"].get(who, 0) + 1
            self.week["campaigns"] += 1
        return g

    def move(self, ip: str, game: str, who: str, kind: str, what: str, place: str) -> tuple[bool, dict | str]:
        if not GAME.match(game) or who not in CANDS or kind not in KINDS or what not in WHAT or place not in PLACES:
            return False, "Usage: isle move <game> <" + "|".join(CANDS) + "> <" + "|".join(KINDS) + "> <what> <place>"
        now = self.clock()
        self.roll(now)
        why = self.limit(ip, now, game)
        if why:
            return True, {"counted": False, "why": why}
        self.campaign(game, who)
        p = self.players
        p["moves"] += 1
        p["kinds"][kind] = p["kinds"].get(kind, 0) + 1
        if kind == "law" and what in LAWS:
            p["laws"][what] = p["laws"].get(what, 0) + 1
        if kind == "gift" and what in BUILDS:
            self.built[what] = self.built.get(what, 0) + 1
            self.dirty = True
        self.times.append(now)
        self.changed({"t": int(now), "k": kind, "c": who, "x": what, "at": place, "h": 0})
        return True, {"counted": True}

    def end(self, ip: str, game: str, who: str, winner: str, laws: str = "-") -> tuple[bool, dict | str]:
        if not GAME.match(game) or who not in CANDS or winner not in CANDS or not LAWLIST.match(laws):
            return False, "Usage: isle end <game> <as> <winner> [law,law,...]"
        now = self.clock()
        self.roll(now)
        why = self.limit(ip, now, game)
        if why:
            return True, {"counted": False, "why": why}
        g = self.campaign(game, who)
        if g[1]:
            return True, {"counted": False, "why": "once"}
        g[1] = True
        p = self.players
        p["finished"] += 1
        p["wins"][winner] = p["wins"].get(winner, 0) + 1
        w = self.week
        w["finished"] += 1
        w["wins"][winner] = w["wins"].get(winner, 0) + 1
        for law in dict.fromkeys(laws.split(",")):
            if law in LAWS:
                w["laws"][law] = w["laws"].get(law, 0) + 1
        self.changed({"t": int(now), "k": "won", "c": winner, "x": who, "at": "hall", "h": 0})
        return True, {"counted": True}

    # ---------- the islanders, when few people play ----------
    def busy(self, now: float) -> bool:
        while self.times and self.times[0] < now - 3600:
            self.times.popleft()
        n = 0
        for t in reversed(self.times):
            if t < now - FLOOR_WINDOW or n >= FLOOR:
                break
            n += 1
        return n >= FLOOR

    def house(self, now: float | None = None) -> dict | None:
        """One move of the islanders' own, if it is time and few people play; the same move for the same moment."""
        now = self.clock() if now is None else now
        self.roll(now)
        if not self.house_on or now - self.last_house < HOUSE_EVERY or self.busy(now):
            return None
        self.last_house = now
        slot = int(now // HOUSE_EVERY)
        R = random.Random(f"{self.day}:{slot}")
        who = sorted(CANDS)[slot % 4] if R.random() < 0.5 else R.choice(sorted(CANDS))
        cares, way = CANDS[who]
        inforce = self.islanders["inforce"]
        kind, what, place = "talk", R.choice(cares), "market"
        roll = R.random()
        if way == "rumours" and roll < 0.5:
            about = R.choice([c for c in CANDS if c != who])
            kind, what, place = ("lie" if R.random() < 0.55 else "fact"), about, "radio"
        elif way == "money" and roll < 0.35:
            emb = R.choice(sorted(EMB))
            kind, what, place = "deal", emb, emb
        elif way == "people" and roll < 0.25:
            kind, what, place = "pact", R.choice([c for c in CANDS if c != who]), "bar"
        elif roll < 0.7:
            free = [l for l in LAWS if l not in inforce] or list(LAWS)
            law = max(free, key=lambda l: (score(l, cares), R.random()))
            clash = [l for l in inforce if law in LAWS[l][1] or l in LAWS[law][1]]
            if clash:
                kind, what, place = "refused", law, "hall"
            else:
                yes = sum(1 for c in CANDS if c != who and (score(law, CANDS[c][0]) > 0 or (score(law, CANDS[c][0]) == 0 and R.random() < 0.55)))
                kind, what, place = ("law" if yes >= 2 else "down"), law, "hall"
                if yes >= 2:
                    inforce.append(law)
                    if len(inforce) > 6:   # an old law lapses so the islanders' day keeps moving
                        inforce.pop(0)
        isl = self.islanders
        isl["moves"] += 1
        isl["kinds"][kind] = isl["kinds"].get(kind, 0) + 1
        if kind == "law":
            isl["laws"][what] = isl["laws"].get(what, 0) + 1
        ev = {"t": int(now), "k": kind, "c": who, "x": what, "at": place, "h": 1}
        self.changed(ev)
        return ev

    # ---------- what everyone gets ----------
    def snapshot(self) -> dict:
        now = self.clock()
        self.roll(now)
        self.busy(now)
        isl = {k: v for k, v in self.islanders.items() if k != "inforce"}
        return {"day": self.day, "v": self.v, "players": self.players, "islanders": isl, "recent": list(self.recent), "built": self.built,
                "week": self.week, "last": self.last, "lastHour": sum(1 for t in self.times if t >= now - 3600), "here": len(self.subs), "push": PUSH}

    def route(self, path: str) -> dict | None:
        return self.snapshot() if path == "/isle" else None

    async def run(self, push):
        """push(snapshot) sends it to every page that joined; called only when something changed."""
        saved = self.clock()
        while True:
            await asyncio.sleep(PUSH)
            try:
                self.house()
                if self.v != self.pushed and self.subs:
                    self.pushed = self.v
                    push(self.snapshot())
                if self.clock() - saved >= 60:
                    saved = self.clock()
                    await asyncio.to_thread(self.save)
            except Exception as exc:   # the island's day must never stop the relay
                log.warning("isle tick failed: %r", exc)

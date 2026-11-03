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
  isle end <game> <as> <winner> [laws] [wallet] [votes] [goal]
                                              the campaign's election result, the laws in force at its end (a,b,c), and
                                              for the players' board: the visitor's test wallet, the votes their
                                              candidate got (0-10), the ambition reached ("-" for none)
  isle board [wallet]                         the players' board, longer, with this wallet's own places
GET /isle                                     the day so far as JSON
GET /isle/board                               the players' board

The players' board: the players are test wallets, never people or names. A move or a result counts for a wallet only
when that wallet signed a transaction through this relay from the same address in the last SEEN_FOR seconds (every
move in the game is one), so nobody can put their numbers on someone else's wallet. For each wallet the week keeps
its first finished campaign (one campaign per week and browser is the game's rule; a replay does not improve it) and
every move it made; all time keeps elections won, campaigns finished, ambitions reached and moves. The week starts
empty with the governor's count, Monday 00:00 German time; last week's best results stay readable as `prev`.

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
WALLET = re.compile(r"^[0-9a-f]{96}$")
AMBS = ("fortune", "reform", "kingmaker", "clean")   # rabbit/game.js AMB

PUSH = 10                 # seconds between two pushes, at most
HOUSE_EVERY = 180         # the islanders make a move of their own this often while few people play
FLOOR = 10                # "few": fewer players' moves than this in the last FLOOR_WINDOW seconds
FLOOR_WINDOW = 900
RECENT = 12
GAMES_PER_IP, MOVES_PER_IP = 30, 900
IP_BURST, IP_REFILL = 20, 1 / 3
KEEP_GAMES = 200_000      # campaigns remembered for the day (beyond, they are still counted, once per move)
SEEN_FOR = 6 * 3600       # a wallet counts for an address this long after it signed a transaction from there
KEEP_WALLETS = 50_000     # wallets on the board, per week and all time (beyond, new wallets are not listed)
TOP, TOP_LONG = 5, 10     # rows in the pushed summary, and in `isle board`


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


def short(pk: str) -> str:
    """How the board shows a wallet: enough to recognise your own, the same as the wallet page's short form."""
    return pk[:6] + "…" + pk[-4:]


def ranked(rows: dict, key) -> list:
    return sorted(rows.items(), key=lambda kv: key(kv[1]) + (kv[0],))


def row(pk: str, r: dict, n: int) -> dict:
    return dict(r, id=short(pk), n=n)


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
        self.seen: dict[str, dict[str, float]] = {}   # address -> wallet -> when it last signed a transaction from there
        self.board = {"week": self.week["id"], "w": {}, "all": {}, "prev": None}
        self._board = (-1, None)
        self._order = (None, ([], [], []))
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
        self.games: dict[str, list] = {}    # campaign -> [as, ended, wallet, moves not yet on the board, laws not yet on it]
        self.ips: dict[str, list] = {}      # address -> [bucket, campaigns, moves]
        self.times: deque = deque(maxlen=200_000)       # when the last players' moves came, for the floor
        self.last_house = 0.0
        self.v = 0

    def roll(self, now: float):
        d = day_of(now)
        if week_of(now)["id"] != self.week["id"]:
            self.last = verdict(self.week) or self.last   # a week nobody finished changes nothing
            self.week = week_of(now)
            self.new_board_week()
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
        b = s.get("board")
        if isinstance(b, dict) and isinstance(b.get("w"), dict) and isinstance(b.get("all"), dict):
            self.board = {"week": b.get("week") or self.week["id"], "w": b["w"], "all": b["all"], "prev": b.get("prev")}
        if week_of(self.clock())["id"] != self.week["id"]:
            self.last = verdict(self.week) or self.last
            self.week = week_of(self.clock())
            self.dirty = True
        if self.board["week"] != self.week["id"]:
            self.new_board_week()
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
                           "week": self.week, "last": self.last, "board": self.board}, f)
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
            g = [who, False, None, 0, 0]
            if len(self.games) < KEEP_GAMES:
                self.games[game] = g
            self.players["campaigns"] += 1
            self.players["as"][who] = self.players["as"].get(who, 0) + 1
            self.week["campaigns"] += 1
        return g

    def move(self, ip: str, game: str, who: str, kind: str, what: str, place: str, wallet: str = "-") -> tuple[bool, dict | str]:
        if (not GAME.match(game) or who not in CANDS or kind not in KINDS or what not in WHAT or place not in PLACES
                or not (wallet == "-" or WALLET.match(wallet))):
            return False, "Usage: isle move <game> <" + "|".join(CANDS) + "> <" + "|".join(KINDS) + "> <what> <place>"
        now = self.clock()
        self.roll(now)
        why = self.limit(ip, now, game)
        if why:
            return True, {"counted": False, "why": why}
        g = self.campaign(game, who)
        g[3] += 1
        g[4] += kind == "law" and what in LAWS
        mine = self.credit(ip, g, wallet, now)
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
        return True, {"counted": True, "listed": mine}

    def end(self, ip: str, game: str, who: str, winner: str, laws: str = "-", wallet: str = "-", votes: str = "-",
            goal: str = "-") -> tuple[bool, dict | str]:
        if (not GAME.match(game) or who not in CANDS or winner not in CANDS or not LAWLIST.match(laws)
                or not (wallet == "-" or WALLET.match(wallet)) or not (votes == "-" or re.match(r"^(10|[0-9])$", votes))
                or not (goal == "-" or goal in AMBS)):
            return False, "Usage: isle end <game> <as> <winner> [law,law,...] [wallet] [votes 0-10] [ambition reached or -]"
        now = self.clock()
        self.roll(now)
        why = self.limit(ip, now, game)
        if why:
            return True, {"counted": False, "why": why}
        g = self.campaign(game, who)
        if g[1]:
            return True, {"counted": False, "why": "once"}
        g[1] = True
        mine = self.credit(ip, g, wallet, now)
        if mine:
            self.result(g[2], who, winner, int(votes) if votes != "-" else 0, goal, now)
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
        return True, {"counted": True, "listed": mine}

    # ---------- the players' board: test wallets, never names ----------
    def saw(self, ip: str, wallet: str):
        """The relay passed a signed transaction from this wallet, sent from this address (relay.py sendtx)."""
        if not WALLET.match(wallet or ""):
            return
        if len(self.seen) > 50_000:
            self.seen.clear()
        w = self.seen.setdefault(ip, {})
        if len(w) > 20:   # an address with many wallets (a café, a school): keep the most recent ones
            for k in sorted(w, key=w.get)[:len(w) - 20]:
                del w[k]
        w[wallet] = self.clock()

    def signed(self, ip: str, wallet: str, now: float) -> bool:
        return now - self.seen.get(ip, {}).get(wallet, -SEEN_FOR) < SEEN_FOR

    def rec(self, wallet: str, now: float) -> tuple[dict | None, dict | None]:
        b = self.board
        if wallet not in b["w"] and len(b["w"]) >= KEEP_WALLETS:
            w = None
        else:
            w = b["w"].setdefault(wallet, {"as": "", "moves": 0, "laws": 0, "done": 0, "won": 0, "votes": 0, "goal": "", "t": int(now)})
        if wallet not in b["all"] and len(b["all"]) >= KEEP_WALLETS:
            a = None
        else:
            a = b["all"].setdefault(wallet, {"played": 0, "won": 0, "goals": 0, "moves": 0, "t": int(now)})
        return w, a

    def credit(self, ip: str, g: list, wallet: str, now: float) -> bool:
        """Put the campaign's moves so far on its wallet's line, once the wallet has signed from this address."""
        if wallet == "-" or not self.signed(ip, wallet, now):
            return False
        if g[2] not in (None, wallet):   # a campaign belongs to the first wallet it was seen with
            return False
        g[2] = wallet
        if g[3]:
            w, a = self.rec(wallet, now)
            for r in (w, a):
                if r is not None:
                    r["moves"] += g[3]
                    r["t"] = int(now)
            if w is not None:
                w["as"] = w["as"] or g[0]
                w["laws"] += g[4]
            g[3] = g[4] = 0
            self.changed()
        return True

    def result(self, wallet: str, who: str, winner: str, votes: int, goal: str, now: float):
        w, a = self.rec(wallet, now)
        if w is not None and not w["done"]:   # the week keeps a wallet's first finished campaign
            w.update({"as": who, "done": 1, "won": int(winner == who), "votes": votes, "goal": goal if goal != "-" else "", "t": int(now)})
            if a is not None:
                a["played"] += 1
                a["won"] += winner == who
                a["goals"] += goal != "-"
        self.changed()

    def new_board_week(self):
        b = self.board
        best = self.lists(TOP)["best"] if b["w"] else []
        b["prev"] = {"week": b["week"], "best": best} if best else b.get("prev")
        b["week"], b["w"] = self.week["id"], {}
        self._board = (-1, None)
        self._order = (None, ([], [], []))

    def lists(self, n: int) -> dict:
        """The three lists, sorted once per change of the island (a page asking again and again costs nothing)."""
        if self._order[0] != (self.v, self.board["week"]):
            w, a = self.board["w"], self.board["all"]
            self._order = ((self.v, self.board["week"]), (
                ranked({k: r for k, r in w.items() if r["done"]}, lambda r: (-r["won"], -r["votes"], -bool(r["goal"]), r["t"])),
                ranked({k: r for k, r in w.items() if r["moves"]}, lambda r: (-r["moves"], r["t"])),
                ranked({k: r for k, r in a.items() if r["played"]}, lambda r: (-r["won"], -r["goals"], -r["played"], r["t"]))))
        best, busy, ever = self._order[1]
        w, a = self.board["w"], self.board["all"]
        done = best
        return {"best": [row(k, r, i + 1) for i, (k, r) in enumerate(best[:n])],
                "busy": [row(k, r, i + 1) for i, (k, r) in enumerate(busy[:n])],
                "ever": [row(k, r, i + 1) for i, (k, r) in enumerate(ever[:n])],
                "wallets": len(w), "finished": len(done), "everWallets": len(ever),
                "_order": (best, busy, ever)}

    def summary(self) -> dict:
        """The board as it goes out with every push: a few rows each, the same size for one player or thousands."""
        if self._board[0] != self.v:
            L = self.lists(TOP)
            L.pop("_order")
            self._board = (self.v, dict(L, week=self.board["week"], prev=self.board.get("prev")))
        return self._board[1]

    def standing(self, wallet: str = "-") -> dict:
        """The longer board, and where this wallet stands in each list (None where it is not in it)."""
        self.roll(self.clock())
        L = self.lists(TOP_LONG)
        order = L.pop("_order")
        me = None
        if WALLET.match(wallet or ""):
            pos = [next((i + 1 for i, (k, _) in enumerate(o) if k == wallet), None) for o in order]
            me = {"id": short(wallet), "best": pos[0], "busy": pos[1], "ever": pos[2],
                  "week": self.board["w"].get(wallet), "all": self.board["all"].get(wallet)}
        return {"board": dict(L, week=self.board["week"], prev=self.board.get("prev"), me=me)}

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
                "week": self.week, "last": self.last, "board": self.summary(), "lastHour": sum(1 for t in self.times if t >= now - 3600), "here": len(self.subs), "push": PUSH}

    def route(self, path: str) -> dict | None:
        if path == "/isle/board":
            return self.standing()
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

"""Forecasts for the simulation (GET /sim/predict, GET /sim/predictions).

Before each hourly rule change of the simulated chain (slot k, proposed at hh:20:00 UTC) a visitor guesses two things:
does the change come into force at hh:30, and how many visitors vote on it in the ballot (simvotes.py). Guesses close
the moment the ballot opens, so nobody guesses with the tally in front of them. The relay scores every round from its
own tally once the ballot has closed: the right yes/no is worth 2 points, the right number of voters 3, the bucket next
to it 1. Points add up per UTC day, like the simulated chain itself, which starts over at midnight.

Identity is the simulation's anonymous browser identity: a random token that only this browser knows, plus three small
numbers that pick a name and a colour from fixed lists. No free text is stored or shown; tokens never leave the relay.
"""
from __future__ import annotations

import calendar
import json
import os
import re
import time

DAY = 86400
SLOT_AT, SLOT_LEN, PACE, SLOTS = 150, 450, 8, 24        # sim.js: slot k proposed at block 150 + 450k, 8 s per block
BUCKETS = ((0, 0), (1, 2), (3, 5), (6, 10), (11, 20), (21, None))   # how many visitors vote: none, 1-2, 3-5, 6-10, 11-20, 21+
POINTS_COME, POINTS_EXACT, POINTS_NEAR = 2, 3, 1
TOKENS_PER_IP = 10       # forecasters one address may bring onto a day's board
BOARD_SIZE = 20
ITEM = re.compile(r"^slot:(\d{1,2})$")
TOKEN = re.compile(r"^[0-9a-f]{32}$")


def day_key(t: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(t))


def slot_open(day_start: float, k: int) -> float:
    """the moment slot k is proposed and its ballot opens: hh:20:00 UTC"""
    return day_start + (SLOT_AT + SLOT_LEN * k) * PACE


def bucket_of(n: int) -> int:
    for i, (lo, hi) in enumerate(BUCKETS):
        if n >= lo and (hi is None or n <= hi):
            return i
    return len(BUCKETS) - 1


def score(guess: dict, come: bool, voters: int) -> int:
    pts = POINTS_COME if bool(guess["come"]) == come else 0
    d = abs(int(guess["n"]) - bucket_of(voters))
    return pts + (POINTS_EXACT if d == 0 else POINTS_NEAR if d == 1 else 0)


class SimPredict:
    def __init__(self, path: str = "/data/simpredict.json", votes=None, clock=time.time, names=None):
        self.path, self.votes, self.clock = path, votes, clock
        self.names = names            # optional (a, b) -> "Quiet Otter", for the Telegram line
        self.state = {"day": day_key(clock()), "guesses": {}, "ips": {}, "results": {}, "yesterday": None}
        self.hits: dict[str, list] = {}   # ip -> [tokens, last refill] for a small token bucket
        self.settled = 0.0
        try:
            with open(path) as f:
                saved = json.load(f)
            if isinstance(saved, dict) and isinstance(saved.get("guesses"), dict):
                self.state.update(saved)
        except (OSError, ValueError):
            pass
        self.roll(clock())

    # ---------- the day ----------
    def roll(self, now: float):
        today = day_key(now)
        if self.state["day"] == today:
            return
        self.settle(now)
        old = self.state
        self.state = {"day": today, "guesses": {}, "ips": {}, "results": {},
                      "yesterday": {"day": old["day"], "board": self.board(old)}}
        self.save()

    def save(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.state, f, separators=(",", ":"))
            os.replace(tmp, self.path)
        except OSError:
            pass

    def day_start(self) -> float:
        y, m, d = (int(x) for x in self.state["day"].split("-"))
        return float(calendar.timegm((y, m, d, 0, 0, 0)))

    def next_slot(self, now: float) -> int | None:
        """the round open for guesses: the next slot whose ballot has not opened yet"""
        start = self.day_start()
        for k in range(SLOTS):
            if slot_open(start, k) > now:
                return k
        return None

    # ---------- results from the ballot ----------
    def settle(self, now: float):
        """score every round whose ballot closed with an outcome; a round is scored once"""
        if self.votes is None:
            return
        try:
            items = (self.votes.snapshot() or {}).get("items") or {}
        except Exception:
            return
        changed = False
        for item in self.state["guesses"]:
            if item in self.state["results"]:
                continue
            it = items.get(item)
            if not it or it.get("outcome") is None or (it.get("closes") or now + 1) > now:
                continue
            come = it["outcome"] != "no"          # "none": nobody decided, the rule comes as planned
            voters = int(it.get("yes") or 0) + int(it.get("no") or 0)
            self.state["results"][item] = {"come": come, "voters": voters, "bucket": bucket_of(voters), "outcome": it["outcome"]}
            changed = True
        if changed:
            self.save()

    # ---------- the board ----------
    def board(self, st: dict | None = None, voter: str | None = None):
        st = st or self.state
        people: dict[str, dict] = {}
        for item, gs in st["guesses"].items():
            res = st["results"].get(item)
            for tok, g in gs.items():
                p = people.setdefault(tok, {"a": g["a"], "b": g["b"], "c": g["c"], "points": 0, "rounds": 0, "scored": 0, "perfect": 0, "first": g["at"]})
                p["rounds"] += 1
                p["first"] = min(p["first"], g["at"])
                if res:
                    pts = score(g, res["come"], res["voters"])
                    p["points"] += pts
                    p["scored"] += 1
                    p["perfect"] += pts == POINTS_COME + POINTS_EXACT
        ranked = sorted(people.items(), key=lambda kv: (-kv[1]["points"], -kv[1]["perfect"], kv[1]["first"]))
        rows, me = [], None
        for i, (tok, p) in enumerate(ranked):
            row = {"rank": i + 1, "a": p["a"], "b": p["b"], "c": p["c"], "points": p["points"], "rounds": p["rounds"], "scored": p["scored"], "perfect": p["perfect"]}
            if self.names:
                row["name"] = self.names(p["a"], p["b"])
            if tok == voter:
                me = row
            if i < BOARD_SIZE:
                rows.append(row)
        return (rows, me) if voter is not None else rows

    def summary(self, voter: str | None = None) -> dict:
        now = self.clock()
        self.roll(now)
        self.settle(now)
        start, k = self.day_start(), self.next_slot(now)
        rows, me = self.board(voter=voter or "")
        rounds = []
        for item in sorted(set(self.state["guesses"]) | ({f"slot:{k}"} if k is not None else set()), key=lambda s: int(s[5:])):
            n = int(item[5:])
            gs = self.state["guesses"].get(item, {})
            res = self.state["results"].get(item)
            mine = gs.get(voter) if voter else None
            r = {"item": item, "closes": slot_open(start, n), "guesses": len(gs), "result": res,
                 "come_yes": sum(1 for g in gs.values() if g["come"]), "buckets": [sum(1 for g in gs.values() if g["n"] == i) for i in range(len(BUCKETS))]}
            if mine:
                r["mine"] = {"come": mine["come"], "n": mine["n"], "points": score(mine, res["come"], res["voters"]) if res else None}
            rounds.append(r)
        return {"day": self.state["day"], "now": now, "open": f"slot:{k}" if k is not None else None,
                "closes": slot_open(start, k) if k is not None else None,
                "buckets": [[lo, hi] for lo, hi in BUCKETS], "points": {"come": POINTS_COME, "exact": POINTS_EXACT, "near": POINTS_NEAR},
                "board": rows, "me": me, "forecasters": len({t for gs in self.state["guesses"].values() for t in gs}),
                "rounds": rounds, "yesterday": self.state.get("yesterday")}

    # ---------- a guess ----------
    def allow(self, ip: str, now: float) -> bool:
        tokens, last = self.hits.get(ip, [10.0, now])
        tokens = min(10.0, tokens + (now - last) * 0.5)
        if tokens < 1:
            self.hits[ip] = [tokens, now]
            return False
        self.hits[ip] = [tokens - 1, now]
        if len(self.hits) > 5000:
            self.hits = {k: v for k, v in self.hits.items() if now - v[1] < 60}
        return True

    def guess(self, q: dict, ip: str) -> tuple[int, dict]:
        now = self.clock()
        self.roll(now)
        if not self.allow(ip, now):
            return 429, {"error": "too many guesses from your address, try again in a moment"}
        item, voter = q.get("item", ""), q.get("voter", "")
        m = ITEM.match(item)
        if not m or not TOKEN.match(voter):
            return 400, {"error": "item must be slot:<0-23> and voter a 32-character hex token"}
        try:
            a, b, c, n = (int(q.get(x, "")) for x in ("a", "b", "c", "n"))
            come = q.get("come")
            if come not in ("0", "1") or not (0 <= n < len(BUCKETS)) or min(a, b, c) < 0 or max(a, b, c) > 999:
                raise ValueError
        except ValueError:
            return 400, {"error": "come must be 1 or 0, n a bucket 0-5, a/b/c small numbers"}
        k = int(m.group(1))
        if k != self.next_slot(now):
            return 409, {"error": "guesses for this round are closed: they close when the ballot opens at hh:20", "open": self.summary(voter)["open"]}
        seen = self.state["ips"].setdefault(ip, [])
        if voter not in seen:
            if len(seen) >= TOKENS_PER_IP:
                return 429, {"error": "this address already brought enough forecasters today"}
            seen.append(voter)
        gs = self.state["guesses"].setdefault(item, {})
        old = gs.get(voter)
        gs[voter] = {"a": a, "b": b, "c": c, "come": come == "1", "n": n, "at": old["at"] if old else now}
        self.save()
        return 200, self.summary(voter)

    # ---------- relay hook ----------
    def route(self, path: str, query: str, ip: str):
        """called for every HTTP request the relay gets; scores closed rounds now and then even when nobody looks"""
        now = self.clock()
        if now - self.settled > 20:
            self.settled = now
            self.roll(now)
            self.settle(now)
        if path not in ("/sim/predict", "/sim/predictions"):
            return None
        q = {}
        for part in query.split("&"):
            k, _, v = part.partition("=")
            if k:
                q[k] = v
        if path == "/sim/predict":
            return self.guess(q, ip)
        voter = q.get("voter", "")
        day = q.get("day")
        if day and day != day_key(self.clock()):
            y = self.state.get("yesterday")
            if y and y.get("day") == day:
                return 200, {"day": day, "board": y["board"], "final": True}
            return 404, {"error": "only today and yesterday are kept"}
        return 200, self.summary(voter if TOKEN.match(voter) else None)

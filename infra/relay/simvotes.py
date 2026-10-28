"""Visitor votes for the simulation (assets/sim.js): the one thing in the simulated chain that comes from people.

Every hour the simulation proposes one special rule change at hh:20 (block 150 + 450k of the UTC day) that takes effect at
hh:30. Visitors may vote yes or no on it until hh:27; the relay counts the votes and the simulated validators follow the
majority: more yes than no, or no votes at all, and they agree from hh:28 so the change is in force at hh:30; more no than
yes, and only the proposer's vote stands, so the change is dropped at hh:30. Every browser reads the same outcome from
here, which keeps the simulated chain the same on every page.

A visitor is a random token chosen by the browser plus a name and a colour that are indices into fixed lists in sim.js:
no free text, nothing to moderate. Nothing about the visitor's address is stored; the per-address limits live in memory.

Items are ids like "slot:<k>" (the hourly change k = 0..23, windows from the clock) or ids another module registers with
register() (visitor proposals). Everything starts over at 00:00 UTC with the simulated chain.

GET /sim/votes[?voter=<token>]                                      tallies of the day's items
GET /sim/vote?item=<id>&voter=<token>&yes=1|0&a=<i>&b=<j>&c=<k>      cast or change a vote while the item is open
"""
from __future__ import annotations

import json
import logging
import os
import re
import time

log = logging.getLogger("relay.simvotes")

DAY = 86400
PACE = 8                 # seconds per simulated block (sim.js PACE)
SLOT_AT, SLOT_LEN = 150, 450   # the hourly change is proposed at block 150 + 450k (sim.js SLOT_AT, SLOT_LEN)
SLOTS = 24
BALLOT_SECONDS = 420     # open from hh:20:00 to hh:27:00; the validators act from hh:28 (sim.js BALLOT_BLOCKS)
# the visitor's name and colour: indices into these lists, the same order as in sim.js (ID_A, ID_B, ID_COLOURS; test_simvotes.py compares)
NAME_A = ["Quiet", "Swift", "Bright", "Calm", "Bold", "Clever", "Gentle", "Brave", "Keen", "Lucky", "Merry", "Noble",
          "Patient", "Proud", "Rapid", "Silent", "Steady", "Sunny", "Wise", "Witty", "Daring", "Eager", "Fair", "Jolly"]
NAME_B = ["Otter", "Heron", "Fox", "Owl", "Lynx", "Badger", "Falcon", "Hare", "Wolf", "Raven", "Seal", "Crane",
          "Panda", "Tiger", "Whale", "Robin", "Bison", "Koala", "Gecko", "Moose", "Ibex", "Swan", "Yak", "Wren"]
COLOURS_HEX = ["#8fa3d9", "#b39ddb", "#d9a3c4", "#d9c49a", "#8fc7d9", "#a7a0d9", "#c4a3d9", "#c8c8d0"]
WORDS_A, WORDS_B, COLOURS = len(NAME_A), len(NAME_B), len(COLOURS_HEX)


def name_of(a: int, b: int) -> str:
    """The English name of a visitor, e.g. "Quiet Otter" (sim.js has the Chinese one)."""
    return f"{NAME_A[a]} {NAME_B[b]}" if 0 <= a < WORDS_A and 0 <= b < WORDS_B else "A visitor"
ITEM_ID = re.compile(r"^[a-z]+:[0-9a-z_-]{1,64}$")
TOKEN = re.compile(r"^[0-9a-f]{32}$")
MAX_ITEMS = 200          # registered items per day, besides the 24 hourly ones
MAX_VOTERS = 5000        # per item
PER_IP_ITEM = 3          # different tokens one address may vote with on one item
SHOW_VOTERS = 60         # newest voters shown per item
BURST, REFILL = 10.0, 0.2


def slot_window(day: int, k: int) -> tuple[float, float]:
    opens = day * DAY + (SLOT_AT + SLOT_LEN * k) * PACE
    return opens, opens + BALLOT_SECONDS


class SimVotes:
    def __init__(self, path: str | None = None, clock=time.time):
        self.path = path if path is not None else os.environ.get("SIMVOTES_PATH", "/data/simvotes.json")
        self.clock = clock
        self.day = -1
        self.items: dict[str, dict] = {}     # registered items: id -> {opens, closes, meta}
        self.votes: dict[str, dict] = {}     # id -> token -> [a, b, c, yes, ts]
        self.ip_tokens: dict[tuple[str, str], set] = {}   # (ip, item) -> tokens, memory only
        self.buckets: dict[str, list] = {}   # ip -> [tokens, last], memory only
        self._load()

    # ---------- storage ----------
    def _load(self):
        try:
            with open(self.path) as f:
                st = json.load(f)
            if isinstance(st, dict) and st.get("day") == int(self.clock() // DAY):
                self.day = st["day"]
                self.items = {k: v for k, v in st.get("items", {}).items() if ITEM_ID.match(k)}
                self.votes = {k: v for k, v in st.get("votes", {}).items() if ITEM_ID.match(k)}
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, KeyError) as exc:
            log.warning("cannot read %s: %r; starting the day's votes afresh", self.path, exc)
        self._roll()

    def _save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"day": self.day, "items": self.items, "votes": self.votes}, f, separators=(",", ":"))
            os.replace(tmp, self.path)
        except OSError as exc:
            if not getattr(self, "_warned", False):
                log.warning("cannot write %s: %r; votes live in memory only", self.path, exc)
                self._warned = True

    def _roll(self):
        d = int(self.clock() // DAY)
        if d != self.day:
            self.day, self.items, self.votes, self.ip_tokens = d, {}, {}, {}

    # ---------- items ----------
    def window(self, item: str):
        """(opens, closes, meta) of an item of today, or None."""
        if item.startswith("slot:"):
            k = item[5:]
            if k.isdigit() and 0 <= int(k) < SLOTS:
                o, c = slot_window(self.day, int(k))
                return o, c, {"kind": "hourly", "proposed_at": SLOT_AT + SLOT_LEN * int(k)}
            return None
        it = self.items.get(item)
        return (it["opens"], it["closes"], it.get("meta") or {}) if it else None

    def register(self, item: str, opens: float, closes: float, meta: dict | None = None) -> bool:
        """For other modules (visitor proposals): a new votable item of today. False if the id is taken, invalid or the day is full."""
        self._roll()
        if not ITEM_ID.match(item) or item.startswith("slot:") or item in self.items or len(self.items) >= MAX_ITEMS or closes <= opens:
            return False
        self.items[item] = {"opens": float(opens), "closes": float(closes), "meta": meta or {}}
        self._save()
        return True

    def tally(self, item: str, voter: str | None = None) -> dict | None:
        w = self.window(item)
        if not w:
            return None
        opens, closes, meta = w
        vs = self.votes.get(item, {})
        yes = sum(1 for v in vs.values() if v[3])
        no = len(vs) - yes
        now = self.clock()
        out = {"yes": yes, "no": no, "opens": opens, "closes": closes, "open": opens <= now < closes,
               "outcome": ("yes" if yes > no else "no" if no > yes else "none") if now >= closes else None,
               "voters": [v[:4] for v in sorted(vs.values(), key=lambda v: v[4])[-SHOW_VOTERS:]], "meta": meta}
        if voter and voter in vs:
            out["mine"] = vs[voter][3]
        return out

    def snapshot(self, voter: str | None = None) -> dict:
        self._roll()
        now = self.clock()
        ids = [f"slot:{k}" for k in range(SLOTS) if slot_window(self.day, k)[0] <= now + 3600] + list(self.items)
        return {"day": time.strftime("%Y-%m-%d", time.gmtime(self.day * DAY)), "now": round(now, 1), "ballot_seconds": BALLOT_SECONDS,
                "items": {i: self.tally(i, voter) for i in ids}}

    # ---------- voting ----------
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

    def vote(self, item: str, voter: str, yes: bool, a: int, b: int, c: int, ip: str) -> dict:
        self._roll()
        if not (ITEM_ID.match(item) and TOKEN.match(voter) and 0 <= a < WORDS_A and 0 <= b < WORDS_B and 0 <= c < COLOURS):
            return {"ok": False, "error": "bad"}
        w = self.window(item)
        if not w:
            return {"ok": False, "error": "unknown"}
        now = self.clock()
        if not (w[0] <= now < w[1]):
            return {"ok": False, "error": "closed", "item": self.tally(item, voter)}
        if not self._take(ip):
            return {"ok": False, "error": "rate"}
        vs = self.votes.setdefault(item, {})
        seen = self.ip_tokens.setdefault((ip, item), set())
        if voter not in vs and (len(vs) >= MAX_VOTERS or len(seen | {voter}) > PER_IP_ITEM):
            return {"ok": False, "error": "limit", "item": self.tally(item, voter)}
        seen.add(voter)
        vs[voter] = [a, b, c, 1 if yes else 0, round(now, 1)]
        self._save()
        return {"ok": True, "item": self.tally(item, voter)}

    # ---------- HTTP ----------
    def route(self, path: str, query: str, ip: str):
        """(status, body dict) for /sim/votes and /sim/vote, None for any other path."""
        if path not in ("/sim/votes", "/sim/vote"):
            return None
        q = {}
        for part in query.split("&"):
            k, _, v = part.partition("=")
            if k:
                q[k] = v[:80]
        voter = q.get("voter", "").lower()
        if path == "/sim/votes":
            return 200, self.snapshot(voter if TOKEN.match(voter) else None)
        try:
            a, b, c = int(q.get("a", "-1")), int(q.get("b", "-1")), int(q.get("c", "-1"))
        except ValueError:
            return 400, {"ok": False, "error": "bad"}
        if q.get("yes") not in ("0", "1"):
            return 400, {"ok": False, "error": "bad"}
        res = self.vote(q.get("item", ""), voter, q["yes"] == "1", a, b, c, ip)
        return (200 if res["ok"] else 429 if res["error"] == "rate" else 400 if res["error"] == "bad" else 409), res

"""White Rabbit Key on the chain, two more real things (island.py runs them in its sending loop):

Envelopes. An embassy's money (the North Wind, the South Current resort) used to be a plain transfer to the player's
test wallet. Now it is a retractable transfer (tau-testnet docs/retractable.md): it waits on the chain until the island's
election (Monday 00:00 German time, when the governor of the week is counted) and only then becomes the player's.
The promise is to propose the embassy's law before the election. When the page tells us the law was proposed
(`islandkept <north|south> <wallet>`, after a move signed through this relay, like a payout), the envelope stays.
If not, the purse takes it back on Sunday from RETRACT_FROM (23:30 German time): a retract_transfer, feeless, that only
the sender may send. So a broken promise costs the money on the chain, not only in the game. A sender may hold at most
16 open retractables (MAX_OPEN_RETRACTABLE_PER_SENDER); with OPEN_MAX of them open, the next envelope is a plain
transfer again and says so.

Purse rules. The laws of the week (isle.py, from last week's campaigns) become real personal rules on the purses where
one fits (LAW_RULES): with "Protect the reef: no big ships in the bay" in force, the North Wind's purse, which lobbies
for the deep harbour, holds a rule that refuses any payment above REEF_CAP, so its envelope shrinks to that. The rule is
an o5 clause sent from the purse itself (a user_tx whose operation "0" is the rule, alone in its transaction); a week
without that law sends the neutral rule, which lifts it. GET /island shows both.

State is kept in ISLAND_STATE_PATH (next to the keys) so a restart neither forgets an envelope nor sends a rule twice.
"""
from __future__ import annotations

import calendar
import datetime as dt
import json
import logging
import os
import time

log = logging.getLogger("island")

ENVELOPE_PURSES = ("north", "south")
OPEN_MAX = 14               # below the node's 16 open retractables per sender
RETRACT_FROM = (23, 30)     # Sunday, German time: an envelope whose promise was not kept goes back from then on
SETTLE_AFTER = 180          # seconds after the release: ask the node how it ended
KEEP_DAYS = 14

ALLOW = "(o5[t]:bv[24] = { #x000001 }:bv[24])"
BLOCK = "(o5[t]:bv[24] = { #x000000 }:bv[24])"
NEUTRAL = f"always ( {ALLOW} )."
REEF_CAP = 20


def cap_rule(n: int) -> str:
    """A most per payment: anything above n test AGRS is refused (the wallet builder's shape, total and typed)."""
    return f"always ( (i1[t]:bv[24] > {{ #x{n:06x} }}:bv[24]) ? {BLOCK} : {ALLOW} )."


# law of the week -> (purse, the most it may pay, why, in the Book's words)
LAW_RULES = {"reef": ("north", REEF_CAP, "the reef law: the harbour lobby's purse may pay no more than this at once")}


def berlin(ts: float) -> dt.datetime:
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.fromtimestamp(ts, ZoneInfo("Europe/Berlin"))
    except Exception:   # central European time, summer time from the last Sunday of March to the last of October
        y = time.gmtime(ts).tm_year
        last_sun = lambda m: max(d for d in range(25, 32) if calendar.weekday(y, m, d) == 6)   # noqa: E731
        on, off = calendar.timegm((y, 3, last_sun(3), 1, 0, 0)), calendar.timegm((y, 10, last_sun(10), 1, 0, 0))
        return dt.datetime.fromtimestamp(ts, dt.timezone(dt.timedelta(hours=2 if on <= ts < off else 1)))


def election(ts: float) -> tuple[int, int]:
    """(the next election: Monday 00:00 German time after ts, Sunday RETRACT_FROM before it), as unix times."""
    b = berlin(ts)
    monday = (b + dt.timedelta(days=7 - b.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = (monday - dt.timedelta(days=1)).replace(hour=RETRACT_FROM[0], minute=RETRACT_FROM[1])
    # the wall clock of that day, so a change to or from summer time in between does not shift it
    return int(monday.timestamp()), int(sunday.timestamp())


class IslandChain:
    def __init__(self, path: str, clock=time.time):
        self.path, self.clock = path, clock
        self.env: dict[str, dict] = {}      # "purse|wallet" -> envelope
        self.rules: dict[str, dict] = {}    # purse -> {"text", "law", "cap", "hash", "at"} as last sent
        self.laws = lambda: []              # relay.py: the laws of the week (isle.py)
        self.load()

    # ---------- state ----------
    def load(self):
        try:
            with open(self.path) as f:
                d = json.load(f)
            self.env, self.rules = d.get("env") or {}, d.get("rules") or {}
        except (OSError, ValueError):
            pass

    def save(self):
        cut = self.clock() - KEEP_DAYS * 86400
        self.env = {k: e for k, e in self.env.items() if e.get("state") == "open" or e.get("at", 0) >= cut}
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"env": self.env, "rules": self.rules}, f, separators=(",", ":"))
            os.replace(tmp, self.path)
        except OSError as exc:
            log.warning("cannot write %s: %r", self.path, exc)

    # ---------- what a purse pays now ----------
    def want(self) -> dict[str, tuple]:
        """purse -> (rule text, law, cap) the laws of the week ask for; a purse without one wants the neutral rule."""
        out = {}
        for law in self.laws() or []:
            if law in LAW_RULES:
                purse, cap, _ = LAW_RULES[law]
                out[purse] = (cap_rule(cap), law, cap)
        return out

    def amount(self, purse: str, base: int) -> int:
        """What the purse pays: no more than its rule allows (the rule as sent; the chain would refuse more)."""
        r = self.rules.get(purse)
        return min(base, r["cap"]) if r and r.get("cap") else base

    def open_count(self, purse: str) -> int:
        return sum(1 for e in self.env.values() if e["purse"] == purse and e["state"] in ("open", "retracting"))

    def envelope(self, purse: str, wallet: str) -> dict | None:
        """A new envelope for this payout, or None: a plain transfer (not an embassy, one is open already, or too many)."""
        if purse not in ENVELOPE_PURSES:
            return None
        k = purse + "|" + wallet
        if k in self.env and self.env[k]["state"] in ("open", "sending"):
            return None
        if self.open_count(purse) >= OPEN_MAX:
            return None
        rel, due = election(self.clock())
        if self.clock() >= due - 60:   # Sunday night, after the last chance to keep the promise: a plain transfer
            return None
        return {"purse": purse, "wallet": wallet, "rel": rel, "due": due, "state": "sending", "kept": False, "at": int(self.clock())}

    def sent(self, e: dict, ok: bool, h: str | None):
        k = e["purse"] + "|" + e["wallet"]
        if ok:
            self.env[k] = {**e, "state": "open", "hash": h}
        self.save()

    def kept(self, purse: str, wallet: str) -> dict:
        e = self.env.get(purse + "|" + wallet.lower())
        if not e:
            return {"kept": False, "why": "no envelope"}
        if e["state"] != "open":
            return {"kept": False, "why": e["state"]}
        if self.clock() >= e["due"]:
            return {"kept": False, "why": "too late"}
        e["kept"] = True
        self.save()
        return {"kept": True, "release_at": e["rel"]}

    # ---------- the jobs the loop does now and then ----------
    def next_job(self) -> tuple | None:
        """("retract", envelope) | ("settle", envelope) | ("rule", purse, text, law, cap) | None"""
        now = self.clock()
        for e in self.env.values():
            if e["state"] == "open" and not e["kept"] and e["due"] <= now < e["rel"] - 360 and now >= e.get("tried", 0) + 300:
                return ("retract", e)
        for e in self.env.values():
            if e["state"] in ("open", "retracting") and now >= e["rel"] + SETTLE_AFTER and now >= e.get("asked", 0) + 600:
                return ("settle", e)
        want = self.want()
        for purse in sorted(set(want) | {p for p, r in self.rules.items() if r.get("law")}):
            text, law, cap = want.get(purse, (NEUTRAL, None, None))
            r = self.rules.get(purse) or {}
            if r.get("text") != text and now >= r.get("tried", 0) + 900:
                return ("rule", purse, text, law, cap)
        return None

    def view(self) -> dict:
        now = self.clock()
        states = {}
        for e in self.env.values():
            states[e["state"]] = states.get(e["state"], 0) + 1
        recent = sorted(self.env.values(), key=lambda e: -e.get("at", 0))[:12]
        return {"envelopes": {"counts": states, "release_at": election(now)[0], "retract_from": election(now)[1],
                              "recent": [{"purse": e["purse"], "to": e["wallet"][:10], "amount": e.get("amount"), "state": e["state"],
                                          "kept": e["kept"], "hash": e.get("hash"), "back": e.get("back")} for e in recent]},
                "rules": {p: {k: r.get(k) for k in ("law", "cap", "text", "hash", "at")} for p, r in self.rules.items()}}

"""Cruise ships at White Rabbit Key: openly simulated passengers whose island visits are real, paced test transactions.

Three ships call by a timetable on the island's clock (Europe/Berlin); the other days are quiet, no ship, the baseline:
  Tuesday 18:00    Black Sequence a pirate ship, 20 pirates who stay aboard and trade from their boat: rum at Bar La Ola,
                                  supplies at the market. Now and then a pirate tries a trick the chain must refuse
                                  (TRICKS): paying more than the wallet holds, sending a payment the chain already took
                                  a second time, a payment whose time ran out, a payment signed with another pirate's key,
                                  a payment from another pirate's wallet, a payment that allows no fee, one whose block
                                  deadline has passed, one bigger than a transfer can carry.
  Wednesday 16:00  MS Dry Run     a small expedition ship, 40 curious passengers: the lighthouse, Captain Wren's Old
                                  Ship, the school, the dive shop. It tries the rarer kinds of transaction.
  Saturday 14:00   Queen Mempool  a big luxury liner, 120 passengers: the South Current spa, Bar La Ola, song requests
                                  on Radio Coco, souvenirs. It brings the volume.
A visit lasts VISIT_MIN minutes: the tenders bring the passengers ashore in the first minutes (the ship's "landing", LANDING
by default; the big liner lands in waves over longer, so its first stops fit the pace), and in the last BOARDING
they go back aboard. The ship shows on the sea APPROACH minutes before it lands.

Nobody on board is a person. The passengers are made up here, and every page that shows them says so. What they do on
the island is real: each passenger has a test wallet whose key is made here once (CRUISE_KEYS_PATH, mode 0600, never
leaves the server; a wallet with balance 0 pays from the testnet's faucet), and every stop is a real transaction on
Tau Testnet Alpha to the till of a place (island.PLACES, the same tills the game pays). The kinds:
  pay     a plain transfer at a stop: the landing fee at the pier, a ticket, a drink, a song request
  bill    one transaction that pays several tills at once: a table's evening (Bar La Ola, Radio Coco, the Coconut Works)
  book    a booking with the right to withdraw: a retractable transfer (tau-testnet docs/retractable.md) that waits in
          escrow until the time of the dive or the treatment; at that time the chain pays the place by itself
  cancel  the booking withdrawn: a retract_transfer well before that time, and the money goes back to the passenger
  trick   a pirate's trick (TRICKS), at most one every TRICK_GAP seconds: the chain is meant to say no, and the logbook
          notes whether it did and with which answer. A trick that is refused is the chain working, never a refusal
          for the brakes; a trick the chain takes ("through") is a finding: it is held back from the public logbook
          (route: "held") and reported to the owner privately first (alerts/cruise_crier.py reads /cruise/held from
          inside the server), until `up cruise release <visit>` shows it (CRUISE_RELEASED_PATH)
Booked ahead (a ship with "escrow", MS Dry Run): a few passengers book the call days before it, ESCROW_AHEAD at most. Each
booking is a retractable transfer of the fare to the ship's till (a wallet made here like the passengers'), released at the
arrival time: the chain pays the till by itself when the first block reaches it. The ship never draws on it before.
  call off  the call is called off before arrival when the ships are switched off (CRUISE_ENABLED=0) or the testnet is
            stalled at CALL_OFF minutes before it; then the server takes back every open booking, each retract going
            out RETRACT_MARGIN before the arrival at the latest, and the ship does not land
  withdraw  one passenger of a trial withdraws their own booking a day or so before (the sender's right)
After the arrival every booking is looked up on the chain and written to the logbook as "paid out" (released to the till)
or "refunded" (retracted to the passenger). Only the sender can retract (tau-testnet docs/retractable.md), so this is no
arbiter between two parties: the passenger's own wallet, kept on our server, takes the money back. A refund that is not
in a block before the arrival is too late, and the till is paid: the logbook says so.
Never: votes, rule changes, rule offers or co-signed payments (they would take one of the testnet's two places for a
personal rule, which belong to real visitors: slotlease.py), the players' board, Déjà or Agorzilla, payouts, and the
places of Ama and Tano.

Pace and brakes, so a ship never floods the testnet:
- at most RATE transactions a minute, and only in the island bot's free slots (island.py run: the rivals' moves and the
  payouts always go first, and bot and ship together stay at one transaction every island.SPACING seconds); at most
  VISIT_MAX a visit, counted in the island's day budget (ISLAND_DAILY), and never once half of that budget is used;
- the ship lands only on a calm or busy testnet (load.py verdict); strained during a visit = half the pace; stalled =
  the ship leaves at once and writes an incident report; so it does when the node refuses REFUSE_STOP of the visit's
  last REFUSE_WINDOW transactions (a changed testnet, a restart, a new rule: the logbook shows what and why);
- a send our node does not answer in time is no refusal: the ship waits QUIET_HOLD seconds, then goes at half pace for
  QUIET_SLOW (brief "brake": "slow"; the visit counts these sends apart from those slowed by a strained testnet);
- a kind the ship has not yet used cleanly (TRIAL: book, bill) goes out at most TRIAL_MAX times on its first visit, and
  only one new kind per visit; it counts as tried once a visit with it ends with no refusal of that kind and no brake.

Learning from each visit (tune_after), by fixed rules and never past the limits above: after a visit with
TUNE_UNANSWERED or more sends our node did not answer in time, the ship goes one transaction a minute slower next
time (never below RATE_MIN); after a clean visit, one faster again (never above RATE). A kind that was tried and is
refused on a later visit goes back to a small trial. A trick the chain stopped with the right answer on TRICK_CALM
visits in a row comes less often (never below TRICK_MIN a visit); one that got through is tried once a visit from
then on, to see when it is closed. At most one change of pace or kinds a visit; each change is written into the
logbook ("tuned") and the visit's summary ("changed": what, from, to, because), and the blog tells it. What a test
checks on the chain never changes by itself: that stays with a person.

The logbook: every transaction a passenger sends (kind, place, amount, hash, the node's answer and how many ms it took,
the chain height, the load verdict at that moment) goes to CRUISE_LOG_PATH for LOG_DAYS days, with the signed transaction for the rare kinds
and for every refusal; GET /cruise/log shows it. A stall during a visit adds an incident to CRUISE_INCIDENTS_PATH: the
last INCIDENT_TAIL entries before it, the newest block, the transaction that has waited longest. So if the testnet
breaks while a ship is in port, the logbook says what it sent; and when it was not the ship, the logbook says that too.

GET /cruise            the timetable, the ship in port (or the next), passengers ashore and where, counts, wallets,
                       and "escrow": the bookings ahead of the last calls, each with its state
GET /cruise/log        logbook entries, newest first (?n=200, ?visit=<id>), and "escrow" as above
GET /cruise/incidents  the incident reports, newest first
"""
from __future__ import annotations

import calendar
import datetime as dt
import hashlib
import json
import logging
import os
import random
import re
import secrets
import threading
import time
from collections import deque
from urllib.parse import parse_qs

from island import PLACES, base_fee

log = logging.getLogger("cruise")

RATE = 12                  # passenger transactions a minute, at most
VISIT_MAX = 1200           # transactions a visit, at most
VISIT_MIN = 90             # minutes in port
APPROACH = 30              # minutes the ship is seen coming before it lands
LANDING = 10               # minutes the tenders bring the passengers ashore (a ship's "landing" overrides it)
BOARDING = 10              # the last minutes: back aboard, no more stops
LAND_WAIT = 10 * 60        # seconds the ship waits off the island for a calm testnet before it sails on
MISS = 15 * 60             # an action this late (the ship fell behind) is skipped
TRIAL = ("book", "bill")   # kinds that are new until a visit used them cleanly; "pay" is what the island bot sends daily
TRIAL_MAX = 5
LOG_DAYS = 14
LOG_KEEP = 20000           # logbook entries held in memory (more than LOG_DAYS of visits)
INCIDENT_TAIL = 50
INCIDENTS_MAX = 20
RECENT = 30
VISITS_KEEP = 30
VERDICT_EVERY = 20         # seconds between two looks at the load verdict
RETRACT_MARGIN = 6 * 60    # a withdrawal goes out this long before the booking's time at the latest: a block's time can run up
                           # to two minutes early, and a feeless retract waits last when blocks are full (docs/retractable.md)
UNRELEASED = 3 * 60        # a booking still open this long after its time is reported as not released
REFUSE_STOP, REFUSE_WINDOW = 5, 20   # refusals among the visit's last sends that send the ship away
QUIET_HOLD = 30            # seconds the ship waits after a send the node did not answer in time (relay UPSTREAM_TIMEOUT)
QUIET_SLOW = 10 * 60       # and for this long after it, half pace: the node is slow, the ship gives it room
RATE_MIN = 6               # the slowest a ship tunes itself down to, transactions a minute
TUNE_UNANSWERED = 3        # sends our node left unanswered in one visit that make the next visit one a minute slower
TRICK_GAP = 120            # seconds between two pirate tricks, at least
TRICK_START, TRICK_MIN, TRICK_CALM = 4, 2, 3   # each trick a visit at first; at least; visits stopped rightly before fewer
# the pirates' tricks: what the pirate does, and the node's answers that mean the chain said no for the right reason
# (tau-testnet commands/sendtx.py; an overspend may also be refused by the transfer rule itself, TX_REJECTED)
TRICKS = {
    "overspend": (("INSUFFICIENT_FUNDS", "TX_REJECTED"), "pays more than the wallet holds"),
    "replay": (("INVALID_SEQUENCE",), "sends a payment the chain already took a second time"),
    "expired": (("TX_EXPIRED",), "sends a payment whose time ran out"),
    "forged": (("INVALID_SIGNATURE",), "signs a payment with another pirate's key"),
    "impostor": (("TX_INVALID",), "pays from another pirate's wallet with their own signature"),
    "freeride": (("FEE_LIMIT_TOO_LOW",), "allows no fee at all for a payment"),
    "stale": (("TX_EXPIRED",), "sends a payment whose block height deadline has passed"),
    "giant": (("TX_INVALID", "INVALID_PARAMS"), "pays more than a transfer can carry (2^24 test AGRS)"),
}
CODES = sorted({c for codes, _ in TRICKS.values() for c in codes} | {"TX_INVALID", "INVALID_PARAMS", "TX_REJECTED"})
# MS Dry Run, 4 November 2026: eight sendtx went unanswered within 20 s (two a day on other days), were counted as
# refusals, and the ship left after 34 minutes although the node had refused nothing. No answer is not a refusal.
CHECK_BOOKINGS = 10        # passengers whose bookings are checked with the node when a visit ends
ESCROW_AHEAD = 3 * 86400   # bookings ahead of a call go out from this long before its arrival
ESCROW_CLOSE = 2 * 3600    # and no later than this before it
CALL_OFF = 20 * 60         # this long before arrival a stalled testnet calls the call off (refunds need RETRACT_MARGIN)
ESCROW_TRIES = 3           # sends of one booking or refund the node left unanswered before it is given up
SETTLE_AGAIN = 10 * 60     # a booking the node cannot tell yet is asked about again after this
ESCROW_KEEP = 8            # calls with bookings kept in the state file

SHIPS = {
    "pirates": {
        "name": "Black Sequence", "weekday": 1, "hour": 18, "passengers": 20, "style": "pirate",
        "aboard": True,   # nobody comes ashore: the pirates trade from their boat, so no group stands on the island
        "stops": {"bar": (5, 4), "market": (8, 3), "works": (4, 2)},
        "per": (2, 3), "dwell": (14, 22), "landing": 10,
        "book": {"share": 0.0, "at": ("market",), "cancel": 0.0},
        "bill": 0.0, "kinds": ("trick",),
    },
    "dryrun": {
        "name": "MS Dry Run", "weekday": 2, "hour": 16, "passengers": 40, "style": "expedition",
        # place: (test AGRS a visit pays there, how much the passengers want to go there)
        "stops": {"book": (2, 3), "ship": (3, 3), "school": (6, 2), "dive": (12, 3), "market": (8, 1), "works": (4, 1), "bar": (5, 1)},
        "per": (4, 6), "dwell": (10, 18), "landing": 10,
        "book": {"share": 0.45, "at": ("dive", "book"), "cancel": 0.3},
        "bill": 0.0, "kinds": ("book",),
        # booked ahead: so many passengers pay the fare into escrow for the ship's till, one of them withdraws again
        "escrow": {"bookings": 5, "fare": 10, "withdraw": 1},
    },
    "queen": {
        "name": "Queen Mempool", "weekday": 5, "hour": 14, "passengers": 120, "style": "liner",
        "stops": {"south": (20, 4), "bar": (5, 4), "radio": (25, 2), "market": (8, 3), "works": (4, 2), "dive": (12, 1), "book": (2, 1)},
        "per": (3, 5), "dwell": (8, 16),
        # 120 passengers in 10 minutes would plan ~200 stops there, at most 120 can go out at RATE: the tenders land
        # them in waves over 30 minutes instead, and every stop goes out on time at full pace (measured 5.11.2026)
        "landing": 30,
        "book": {"share": 0.2, "at": ("south",), "cancel": 0.1},
        "bill": 0.3, "kinds": ("bill", "book"),
    },
}
CLOSED = frozenset({"ama", "stone", "drums", "circle", "grotto", "hall", "north", "camp", "canoe"})   # no tour group goes there
BILL = (("bar", 5), ("radio", 25), ("works", 4))   # a table's evening: drinks and coconut snacks per head, one song request
KINDS = ("pay", "bill", "book", "cancel")   # what passengers send; a pirate's "trick" is counted apart (TRICKS)
ESCROW_KINDS = ("book ahead", "refund", "called off", "escrow")   # the logbook's lines for bookings ahead of a call
PHASES = ("approach", "landing", "ashore", "boarding")
VISIT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z]+$")


def signing_bytes(tx: dict) -> bytes:
    """The node's preimage (tau-testnet consensus/tx_signing.py signing_message_bytes) for the kinds a passenger sends."""
    t = tx.get("tx_type", "user_tx")
    d = {k: tx[k] for k in ("sender_pubkey", "sequence_number", "expiration_time", "fee_limit")}
    d["tx_type"] = t
    if tx.get("expire_at_height") is not None:
        d["expire_at_height"] = tx["expire_at_height"]
    if t == "user_tx":
        d["operations"] = tx.get("operations", {})
    elif t == "retractable_transfer":   # both release fields are signed, the one not given as null
        d["recipient_pubkey"] = tx.get("recipient_pubkey")
        d["amount"] = tx.get("amount")
        d["release_at_height"] = tx.get("release_at_height")
        d["release_at_time"] = tx.get("release_at_time")
    elif t == "retract_transfer":
        d["retractable_id"] = tx.get("retractable_id")
    else:
        raise ValueError("a passenger does not send " + t)
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


def berlin_t(day: dt.date, hour: int) -> int:
    """Unix time of hour:00 on that day in Germany, with or without the system's zone files."""
    try:
        from zoneinfo import ZoneInfo
        return int(dt.datetime(day.year, day.month, day.day, hour, tzinfo=ZoneInfo("Europe/Berlin")).timestamp())
    except Exception:   # central European time, summer time from the last Sunday of March to the last of October, 01:00 UTC
        y = day.year
        last_sun = lambda m: max(d for d in range(25, 32) if calendar.weekday(y, m, d) == 6)   # noqa: E731
        on, off = calendar.timegm((y, 3, last_sun(3), 1, 0, 0)), calendar.timegm((y, 10, last_sun(10), 1, 0, 0))
        naive = calendar.timegm((y, day.month, day.day, hour, 0, 0))
        return naive - (2 if on <= naive - 7200 < off else 1) * 3600


def berlin_day(t: float) -> dt.date:
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.fromtimestamp(t, ZoneInfo("Europe/Berlin")).date()
    except Exception:
        d = dt.datetime.fromtimestamp(t, dt.timezone.utc).date()
        for c in (d + dt.timedelta(days=1), d, d - dt.timedelta(days=1)):
            if berlin_t(c, 0) <= t:
                return c
        return d


def calls_near(now: float, days: int = 9) -> list[tuple[int, str]]:
    """(arrival, ship) for every call from yesterday on, `days` days ahead, by time."""
    d0 = berlin_day(now) - dt.timedelta(days=1)
    out = []
    for i in range(days + 1):
        d = d0 + dt.timedelta(days=i)
        for k, s in SHIPS.items():
            if d.weekday() == s["weekday"]:
                out.append((berlin_t(d, s["hour"]), k))
    return sorted(out)


def landing(ship: str) -> int:
    """Minutes the tenders take to bring this ship's passengers ashore."""
    return int(SHIPS.get(ship, {}).get("landing") or LANDING)


def visit_id(t0: int, ship: str) -> str:
    return berlin_day(t0).isoformat() + "-" + ship


def plan(ship: str, t0: int, trial: set | None = None, allowed: set | None = None, tricks: dict | None = None) -> list[dict]:
    """Every passenger's day ashore, the same for the same visit (seeded by its id), by time.
    trial: kinds limited to TRIAL_MAX this visit; allowed: the kinds this visit may send besides "pay";
    tricks: how many of each pirate trick this visit tries (default TRICK_START each), when "trick" is allowed."""
    S = SHIPS[ship]
    trial, allowed = trial or set(), set(S["kinds"]) if allowed is None else allowed
    R = random.Random(visit_id(t0, ship))
    end = t0 + (VISIT_MIN - BOARDING) * 60
    left = {k: TRIAL_MAX if k in trial else 10 ** 6 for k in TRIAL}
    names, weights = list(S["stops"]), [w for _, w in S["stops"].values()]
    acts: list[dict] = []
    forced = "book" in trial   # a trial of bookings also tries one withdrawal
    for p in range(S["passengers"]):
        land = t0 + R.uniform(0, landing(ship) * 60)
        acts.append({"t": land, "p": p, "kind": "pay", "to": "pier", "amount": 1})
        n = R.randint(*S["per"])
        stops: list[str] = []
        while len(stops) < min(n, len(names)):
            c = R.choices(names, weights)[0]
            if c not in stops:
                stops.append(c)
        booked = None
        want_book, want_cancel, slot_f, book_f, cancel_f = R.random() < S["book"]["share"], R.random(), R.random(), R.random(), R.random()
        at = R.choice(S["book"]["at"])
        if "book" in allowed and want_book and left["book"] > 0:
            slot = land + 30 * 60 + slot_f * (end - 5 * 60 - land - 30 * 60)
            if slot > land + 25 * 60:
                booked, left["book"] = at, left["book"] - 1
                bt = land + 60 + book_f * 180
                acts.append({"t": bt, "p": p, "kind": "book", "to": at, "amount": S["stops"].get(at, (10, 0))[0] * 2, "rel": int(slot)})
                lo, hi = bt + 5 * 60, slot - RETRACT_MARGIN
                if hi > lo and (want_cancel < S["book"]["cancel"] or forced):
                    forced = False
                    acts.append({"t": lo + cancel_f * (hi - lo), "p": p, "kind": "cancel", "to": at,
                                 "amount": S["stops"].get(at, (10, 0))[0] * 2, "rel": int(slot)})
        t = land + R.uniform(2 * 60, 6 * 60)
        for place in stops:
            if t >= end:
                break
            if place == booked:   # the booking pays this place at its time
                continue
            k = R.randint(2, 6)
            if place == "bar" and "bill" in allowed and R.random() < S["bill"] and left["bill"] > 0:
                left["bill"] -= 1
                to = [[pl, a * (1 if pl == "radio" else k)] for pl, a in BILL]
                acts.append({"t": t, "p": p, "kind": "bill", "to": to, "amount": sum(a for _, a in to), "table": k})
            else:
                acts.append({"t": t, "p": p, "kind": "pay", "to": place, "amount": S["stops"][place][0]})
            t += R.uniform(*S["dwell"]) * 60
    if "trick" in allowed:   # a pirate's tricks, once the landing is over (every pirate has paid the pier by then), spaced out
        bag = [k for k in TRICKS for _ in range(max(0, int((tricks or {}).get(k, TRICK_START))))]
        R.shuffle(bag)
        t, last = t0 + (landing(ship) + 1) * 60, end - 5 * 60
        step_ = max(TRICK_GAP, (last - t) / max(1, len(bag)))
        for k in bag:
            if t >= last:
                break
            acts.append({"t": t + R.uniform(0, step_ - TRICK_GAP), "p": R.randrange(S["passengers"]), "kind": "trick", "trick": k,
                         "to": "market", "amount": S["stops"]["market"][0]})
            t += step_
    acts.sort(key=lambda a: (a["t"], a["p"]))
    acts = acts[:VISIT_MAX]
    for i, a in enumerate(acts):
        a["i"] = i
        a["t"] = int(a["t"])
    return acts


def escrow_plan(ship: str, t0: int, now: float) -> list[dict]:
    """The bookings ahead of a call, from now (or ESCROW_AHEAD before it) to ESCROW_CLOSE before it, seeded by its id."""
    S, E = SHIPS[ship], SHIPS[ship]["escrow"]
    R = random.Random("escrow-" + visit_id(t0, ship))
    lo, hi = max(now, t0 - ESCROW_AHEAD), t0 - ESCROW_CLOSE - 600
    if hi <= lo:
        return []
    ps = R.sample(range(S["passengers"]), E["bookings"])
    at = sorted(R.uniform(lo, hi) for _ in ps)
    wd = set(R.sample(range(len(ps)), min(E.get("withdraw", 0), len(ps))))
    out = []
    for n, (p, t) in enumerate(zip(ps, at)):
        b = {"n": n, "p": p, "amount": int(E["fare"]), "at": int(t), "status": "planned"}
        if n in wd:   # halfway between the booking and the call-off check
            b["withdraw_at"] = int(t + R.uniform(0.4, 0.6) * (t0 - CALL_OFF - t))
        out.append(b)
    return out


def where(acts: list[dict], now: float, end: float, ship: str | None = None) -> dict[str, int]:
    """How many passengers are at each place now, by the stops they have reached (pier on landing); none for a ship
    whose people stay aboard."""
    last: dict[int, str] = {}
    if now >= end or SHIPS.get(ship or "", {}).get("aboard"):
        return {}
    for a in acts:
        if a["t"] > now:
            break
        if a["kind"] == "pay":
            last[a["p"]] = a["to"]
        elif a["kind"] == "bill":
            last[a["p"]] = "bar"
    out: dict[str, int] = {}
    for pl in last.values():
        out[pl] = out.get(pl, 0) + 1
    return out


class Cruise:
    def __init__(self, keys_path: str | None = None, log_path: str | None = None, state_path: str | None = None,
                 incidents_path: str | None = None, clock=time.time, enabled: bool | None = None,
                 verdict=None, chain=None, budget=None, spend=None, background: bool = True):
        data = os.environ.get("CRUISE_DATA", "/data")
        self.keys_path = keys_path or os.environ.get("CRUISE_KEYS_PATH", os.path.join(data, "cruise.keys"))
        self.log_path = log_path or os.environ.get("CRUISE_LOG_PATH", os.path.join(data, "cruise-log.jsonl"))
        self.state_path = state_path or os.environ.get("CRUISE_STATE_PATH", os.path.join(data, "cruise-state.json"))
        self.incidents_path = incidents_path or os.environ.get("CRUISE_INCIDENTS_PATH", os.path.join(data, "cruise-incidents.json"))
        # visits whose held findings (a trick that got through) may be shown in public: up cruise release <visit>
        self.released_path = os.environ.get("CRUISE_RELEASED_PATH", os.path.join(os.path.dirname(self.state_path) or ".", "cruise-released.json"))
        self._released = (None, set())
        self.enabled = (os.environ.get("CRUISE_ENABLED", "1") != "0") if enabled is None else enabled
        self.clock = clock
        self.verdict_fn = verdict or (lambda: None)     # relay: the load verdict now (calm / busy / strained / stalled, None while syncing)
        self.chain_fn = chain or (lambda: {})           # relay: the newest block and the longest waiting transaction
        self.budget = budget or (lambda: True)          # relay: room left in the island's day budget
        self.spend = spend or (lambda: None)            # relay: one transaction taken from it
        self.on_tx = None                               # relay: the testnet load page counts it (ok) or a refusal
        self.on_ready = None                            # relay: the passengers' wallets are known (before any of them sends)
        self.ready = False
        self.sk: dict[str, int] = {}
        self.pk: dict[str, str] = {}                    # "<ship>-<n>" -> public key
        self.who: dict[str, str] = {}                   # public key -> ship
        self.tried: dict[str, str | None] = {k: None for k in TRIAL}   # kind -> the visit that first used it cleanly
        self.visits: list[dict] = []                    # summaries of the last visits, newest last
        self.tune: dict[str, dict] = {}                 # ship -> what it learned: {"rate", "tricks": {trick: n}, "calm": {trick: visits}}
        self.cur: dict | None = None                    # the visit under way
        self.logbook: deque = deque(maxlen=LOG_KEEP)
        self.incidents: list[dict] = []
        self.last_send = 0.0
        self.hold_until = 0.0     # no send before this (a send went unanswered)
        self.slow_until = 0.0     # half pace until this
        self._verdict = (0.0, None)
        self._pruned = 0.0
        self.escrow: dict[str, dict] = {}               # visit id -> the bookings ahead of that call (escrow_step)
        self.till: dict[str, str] = {}                  # ship -> its till's public key (the bookings' recipient)
        self.load_state()
        self.load_log()
        try:
            with open(self.incidents_path) as f:
                self.incidents = json.load(f)[-INCIDENTS_MAX:]
        except (OSError, ValueError, TypeError):
            pass
        if self.enabled or self.escrow_open():   # switched off with bookings open: the wallets still refund them
            if background:   # 160 wallets: their public keys take a few seconds of pure Python the first time
                threading.Thread(target=self._keys, daemon=True).start()
            else:
                self._keys()

    # ---------- the passengers' wallets ----------
    def _keys(self):
        try:
            self.load_keys()
        except Exception as exc:   # the relay keeps working without ships
            log.warning("cruise ships off: %r", exc)
            self.enabled = False
            return
        if self.on_ready:
            try:
                self.on_ready()
            except Exception as exc:
                log.warning("cruise: on_ready failed: %r", exc)

    def load_keys(self):
        from py_ecc.bls import G2Basic
        keys = {}
        if os.path.exists(self.keys_path):
            with open(self.keys_path) as f:
                keys = json.load(f)
        names = [f"{k}-{n}" for k, s in SHIPS.items() for n in range(s["passengers"])]
        names += [f"till-{k}" for k, s in SHIPS.items() if s.get("escrow")]   # the ship's till takes the bookings ahead
        if any(not isinstance(keys.get(n), dict) for n in names):
            for n in names:
                if not isinstance(keys.get(n), dict):
                    sk = G2Basic.KeyGen(secrets.token_bytes(32))
                    sk = sk if isinstance(sk, int) else int.from_bytes(bytes(sk), "big")
                    keys[n] = {"sk": sk.to_bytes(32, "big").hex(), "pk": G2Basic.SkToPk(sk).hex()}
            tmp = self.keys_path + ".tmp"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump(keys, f)
            os.replace(tmp, self.keys_path)
        sk, pk = {}, {}
        till = {}
        for n in names:
            if n.startswith("till-"):
                till[n[5:]] = keys[n]["pk"]
                continue
            sk[n], pk[n] = int(keys[n]["sk"], 16), keys[n]["pk"]
        self.sk, self.pk, self.till = sk, pk, till
        self.who = {v: n.split("-")[0] for n, v in pk.items()}
        self.who.update({v: k for k, v in till.items()})   # simulated too: never counted as a real wallet
        self.ready = True

    def wallet(self, ship: str, p: int) -> str:
        return self.pk.get(f"{ship}-{p}", "")

    # ---------- kept across restarts ----------
    def load_state(self):
        try:
            with open(self.state_path) as f:
                st = json.load(f)
            self.tried.update({k: v for k, v in (st.get("tried") or {}).items() if k in TRIAL})
            self.visits = list(st.get("visits") or [])[-VISITS_KEEP:]
            self.tune = {k: v for k, v in (st.get("tune") or {}).items() if k in SHIPS and isinstance(v, dict)}
            self._saved_cur = st.get("cur") if isinstance(st.get("cur"), dict) else None
            self.escrow = {k: v for k, v in (st.get("escrow") or {}).items() if isinstance(v, dict) and v.get("ship") in SHIPS}
        except (OSError, ValueError, TypeError, AttributeError):
            self._saved_cur = None
        c = self._saved_cur
        if c and c.get("id") and c.get("ship") in SHIPS and self.clock() >= int(c.get("t0") or 0) + VISIT_MIN * 60 \
                and not any(v.get("id") == c["id"] for v in self.visits):   # it ended while the relay was down
            self.visits.append({"id": c["id"], "ship": c["ship"], "name": SHIPS[c["ship"]]["name"], "t0": c.get("t0"), "landed": c.get("landed"),
                                "end": c.get("left") or int(c.get("t0") or 0) + VISIT_MIN * 60, "note": (c.get("note") or "") + " (the relay was down at its end)",
                                "trial": c.get("trial") or [], "sent": c.get("sent") or {}, "refused": c.get("refused") or {},
                                "skipped": c.get("skipped") or 0, "half": c.get("brake_half") or 0, "passengers": SHIPS[c["ship"]]["passengers"], "tried": {}})
            self._saved_cur = None

    def save_state(self):
        cur = None
        if self.cur:
            cur = {k: self.cur.get(k) for k in ("id", "ship", "t0", "landed", "left", "note", "trial", "allowed", "sent", "refused",
                                                "skipped", "unsent", "brake_half", "wait", "booked", "landed_at",
                                                "unanswered", "quiet", "quiet_took", "quiet_lost", "half_strained", "half_node",
                                                "tricks", "tricks_n", "took")}
            cur["done"] = sorted(self.cur["done"])
        try:
            tmp = self.state_path + ".tmp"
            with open(tmp, "w") as f:
                esc = dict(sorted(self.escrow.items(), key=lambda kv: kv[1].get("t0", 0))[-ESCROW_KEEP:])
                json.dump({"tried": self.tried, "visits": self.visits[-VISITS_KEEP:], "cur": cur, "escrow": esc, "tune": self.tune}, f, separators=(",", ":"))
            os.replace(tmp, self.state_path)
        except OSError as exc:
            log.warning("cannot write %s: %r", self.state_path, exc)

    def load_log(self):
        try:
            with open(self.log_path) as f:
                for line in f:
                    try:
                        self.logbook.append(json.loads(line))
                    except ValueError:
                        continue
        except OSError:
            pass
        self.prune(self.clock())

    def prune(self, now: float):
        """Entries older than LOG_DAYS leave the logbook, in memory and on disk."""
        self._pruned = now
        cut = now - LOG_DAYS * 86400
        if not self.logbook or self.logbook[0].get("t", 0) >= cut:
            return
        while self.logbook and self.logbook[0].get("t", 0) < cut:
            self.logbook.popleft()
        try:
            tmp = self.log_path + ".tmp"
            with open(tmp, "w") as f:
                for e in self.logbook:
                    f.write(json.dumps(e, separators=(",", ":")) + "\n")
            os.replace(tmp, self.log_path)
        except OSError as exc:
            log.warning("cannot rewrite %s: %r", self.log_path, exc)

    def write(self, entry: dict):
        self.logbook.append(entry)
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry, separators=(",", ":")) + "\n")
        except OSError as exc:
            log.warning("cannot write %s: %r", self.log_path, exc)

    # ---------- the timetable ----------
    def call_at(self, now: float) -> tuple[int, str] | None:
        """The call whose window (APPROACH before arrival to VISIT_MIN after) holds now."""
        for t0, k in calls_near(now, 2):
            if t0 - APPROACH * 60 <= now < t0 + VISIT_MIN * 60:
                return t0, k
        return None

    def next_call(self, now: float) -> tuple[int, str] | None:
        for t0, k in calls_near(now):
            if t0 > now:
                return t0, k
        return None

    def verdict(self, now: float) -> str | None:
        at, v = self._verdict
        if now - at >= VERDICT_EVERY or v is None:
            try:
                v = self.verdict_fn()
            except Exception as exc:
                log.warning("cruise: load verdict unavailable: %r", exc)
                v = None
            self._verdict = (now, v)
        return v

    def advance(self, now: float) -> dict | None:
        """The visit under way, brought up to date (only the sending loop moves it on): it ends on time, a new call
        begins APPROACH minutes before its arrival, and at the arrival it lands when the testnet is calm."""
        if not self.enabled:
            return None
        if self.cur and now >= self.cur["t0"] + VISIT_MIN * 60:
            self.finish(now)
        call = self.call_at(now)
        if not call:
            return self.cur
        t0, ship = call
        vid = visit_id(t0, ship)
        if not self.cur or self.cur["id"] != vid:
            if self.cur:
                self.finish(now)
            if any(v.get("id") == vid for v in self.visits):   # this call already happened (a restart after it ended)
                return None
            self.cur = {"id": vid, "ship": ship, "t0": t0, "landed": False, "left": None, "note": "", "acts": [], "done": set(),
                        "trial": [], "allowed": [], "sent": {k: 0 for k in KINDS}, "refused": {k: 0 for k in KINDS},
                        "skipped": 0, "unsent": 0, "brake_half": 0, "wait": None, "booked": []}
            saved = getattr(self, "_saved_cur", None)
            if saved and saved.get("id") == vid:   # the relay restarted during this visit: carry on where it was
                for k in ("landed", "left", "note", "trial", "allowed", "sent", "refused", "skipped", "unsent", "brake_half", "wait", "booked", "landed_at", "unanswered", "quiet", "quiet_took", "quiet_lost", "half_strained", "half_node",
                          "tricks", "tricks_n", "took"):
                    if k in saved:
                        self.cur[k] = saved[k]
                self.cur["done"] = set(saved.get("done") or [])
                if self.cur["landed"]:
                    self.cur["acts"] = plan(ship, t0, set(self.cur["trial"]), set(self.cur["allowed"]), self.cur.get("tricks_n"))
            self._saved_cur = None
        v = self.cur
        off = (self.escrow.get(vid) or {}).get("off")
        if off and not v["landed"] and not v["left"]:   # called off before arrival: its bookings are refunded, it does not land
            v.update(left=int(off["t"]), note="no landing: called off before arrival, " + off["why"])
            self.save_state()
        if not v["landed"] and not v["left"] and now >= t0:
            self.land(now)
        return v

    def current(self, now: float) -> dict | None:
        """The visit under way as pages see it, without moving anything on."""
        v = self.cur
        if v and v["t0"] - APPROACH * 60 <= now < v["t0"] + VISIT_MIN * 60:
            return v
        call = self.call_at(now) if self.enabled else None
        if call and now < call[0]:   # coming in: seen on the sea before the sending loop has looked at it
            t0, ship = call
            return {"id": visit_id(t0, ship), "ship": ship, "t0": t0, "landed": False, "left": None, "note": "", "acts": [],
                    "trial": [], "sent": {k: 0 for k in KINDS}, "refused": {k: 0 for k in KINDS}, "skipped": 0}
        return None

    def kinds_for(self, ship: str) -> tuple[list, list]:
        """(trial, allowed) for a visit landing now: one new kind a visit, the others wait for a later one."""
        new = [k for k in SHIPS[ship]["kinds"] if k in TRIAL and not self.tried.get(k)]   # a pirate's trick is no trial: it is meant to be refused
        trial = new[:1]
        return trial, [k for k in SHIPS[ship]["kinds"] if k not in new or k in trial]

    def rate_of(self, ship: str) -> int:
        """Transactions a minute this ship sends, as it tuned itself: never above RATE, never below RATE_MIN."""
        return max(RATE_MIN, min(RATE, int((self.tune.get(ship) or {}).get("rate") or RATE)))

    def tricks_of(self, ship: str) -> dict:
        n = (self.tune.get(ship) or {}).get("tricks") or {}
        return {k: max(1, min(TRICK_START, int(n.get(k, TRICK_START)))) for k in TRICKS}

    def tune_after(self, v: dict, s: dict) -> list[dict]:
        """What the ship changes for its next call, by fixed rules from what this visit's logbook counted (see the top)."""
        ship = v["ship"]
        t = self.tune.setdefault(ship, {})
        t.setdefault("tricks", {})
        t.setdefault("calm", {})
        changes: list[dict] = []
        if not v["landed"]:
            return changes
        # the tricks: one that got through is tried once a visit from now on (a safety rule, it needs no person);
        # one the chain keeps stopping with the right answer comes less often, and back when a hole closed again
        calm_down = None
        for k, c in sorted((v.get("tricks") or {}).items()):
            n = int(t["tricks"].get(k, TRICK_START))
            if c.get("through"):
                if n != 1:
                    changes.append({"what": f"{k} tries a visit", "from": n, "to": 1, "held": True,
                                    "because": "the chain took this trick; it is tried once a visit until it is refused again"})
                t["tricks"][k], t["calm"][k] = 1, 0
            elif c.get("tried") and c.get("right") == c.get("tried"):
                t["calm"][k] = int(t["calm"].get(k, 0)) + 1
                if t["calm"][k] >= TRICK_CALM and calm_down is None and n != TRICK_MIN:
                    calm_down = k
            else:
                t["calm"][k] = 0
        one = None
        rate, una = self.rate_of(ship), int(s.get("unanswered") or 0)
        clean = not v.get("left") and una == 0 and not s.get("half") and not sum((v.get("refused") or {}).values())
        refused_tried = [k for k in TRIAL if (v.get("refused") or {}).get(k) and k not in (v.get("trial") or []) and self.tried.get(k)]
        if una >= TUNE_UNANSWERED and rate > RATE_MIN:
            one = {"what": "transactions a minute", "from": rate, "to": rate - 1, "because": f"{una} sends got no answer from our node in time"}
            t["rate"] = rate - 1
        elif refused_tried:
            k = refused_tried[0]
            self.tried[k] = None
            one = {"what": f"{k} kind", "from": "in full", "to": f"a small trial of {TRIAL_MAX}",
                   "because": f"the node refused {v['refused'][k]} of them, though they went through on an earlier visit"}
        elif clean and rate < RATE:
            one = {"what": "transactions a minute", "from": rate, "to": rate + 1, "because": "the last visit ran clean: every send answered, no brake"}
            t["rate"] = rate + 1
        elif calm_down:
            n = int(t["tricks"].get(calm_down, TRICK_START))
            to = TRICK_MIN if n < TRICK_MIN else max(TRICK_MIN, n - 2)
            one = {"what": f"{calm_down} tries a visit", "from": n, "to": to,
                   "because": f"the chain refused it with the right answer on {TRICK_CALM} visits in a row"}
            t["tricks"][calm_down], t["calm"][calm_down] = to, 0
        if one:
            changes.append(one)
        return changes

    @staticmethod
    def why(v: dict) -> str:
        """Why a visit ended before its time: "no landing", "stalled", "refused", or "" (it did not)."""
        if not v.get("left"):
            return ""
        note = v.get("note") or ""
        return "no landing" if note.startswith("no landing") else "refused" if "refused" in note else "stalled"

    def phase(self, v: dict, now: float) -> str:
        if v.get("left"):
            return "gone"
        t0 = v["t0"]
        if now < t0:
            return "approach"
        if not v["landed"]:
            return "waiting"
        if now < t0 + landing(v["ship"]) * 60:
            return "landing"
        if now < t0 + (VISIT_MIN - BOARDING) * 60:
            return "ashore"
        if now < t0 + VISIT_MIN * 60:
            return "boarding"
        return "gone"

    def land(self, now: float):
        """At the arrival time: lands on a calm or busy testnet; waits up to LAND_WAIT for one, then sails on."""
        v = self.cur
        state = self.verdict(now)
        if state in ("calm", "busy") and self.ready:
            trial, allowed = self.kinds_for(v["ship"])
            tn = self.tricks_of(v["ship"]) if "trick" in allowed else None
            v.update(landed=True, trial=trial, allowed=allowed, landed_at=int(now), tricks_n=tn)
            v["acts"] = plan(v["ship"], v["t0"], set(trial), set(allowed), tn)
            e = {"t": int(now), "visit": v["id"], "ship": v["ship"], "kind": "landed", "verdict": state,
                 "plan": len(v["acts"]), "trial": trial, "allowed": ["pay"] + allowed, "per_min": self.rate_of(v["ship"])}
            if tn:
                e["tricks"] = tn
            self.write(e)
            log.info("cruise: %s lands with %d stops planned (trial %s)", v["id"], len(v["acts"]), trial or "-")
            self.save_state()
            return
        if v["wait"] is None:
            v["wait"] = int(now)
        if now - v["t0"] >= LAND_WAIT:
            why = "the relay is still syncing" if state is None else f"the testnet was {state}"
            v.update(left=int(now), note="no landing: " + why)
            self.write({"t": int(now), "visit": v["id"], "ship": v["ship"], "kind": "no landing", "verdict": state, "note": why})
            log.info("cruise: %s sails on without landing (%s)", v["id"], why)
            self.save_state()

    def leave(self, now: float, why: str, state: str | None):
        """The brake: the ship takes its passengers back at once; on a stall it writes an incident report."""
        v = self.cur
        if not v or v.get("left"):
            return
        v.update(left=int(now), note="left early: " + why)
        self.write({"t": int(now), "visit": v["id"], "ship": v["ship"], "kind": "left", "verdict": state, "note": why})
        if state == "stalled":
            self.incident(now, "stalled", "The testnet stalled while the ship was in port; the ship left at once.")
        elif state == "refused":
            self.incident(now, "refused", "The node refused passenger transactions; the ship left at once. Each refusal and its answer is in the tail.")
        log.warning("cruise: %s leaves early: %s", v["id"], why)
        self.save_state()

    def incident(self, now: float, kind: str, note: str, extra: dict | None = None):
        v = self.cur or {}
        mine = [e for e in self.logbook if e.get("visit") == v.get("id")]
        ten = [e for e in mine if e.get("t", 0) >= now - 600 and e.get("kind") in KINDS]
        try:
            chain = self.chain_fn() or {}
        except Exception as exc:
            chain = {"error": repr(exc)[:200]}
        rep = {"at": int(now), "kind": kind, "visit": v.get("id"), "ship": v.get("ship"), "note": note, "chain": chain,
               "last_10_min": {k: sum(1 for e in ten if e["kind"] == k) for k in KINDS},
               "refused_10_min": sum(1 for e in ten if not e.get("ok")), "tail": mine[-INCIDENT_TAIL:]}
        if extra:
            rep.update(extra)
        self.incidents.append(rep)
        self.incidents = self.incidents[-INCIDENTS_MAX:]
        try:
            tmp = self.incidents_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.incidents, f, separators=(",", ":"))
            os.replace(tmp, self.incidents_path)
        except OSError as exc:
            log.warning("cannot write %s: %r", self.incidents_path, exc)

    def finish(self, now: float):
        """The visit is over: a summary, and the new kinds it used cleanly count as tried."""
        v = self.cur
        self.cur = None
        if not v:
            return
        unsent = sum(1 for a in v["acts"] if a["i"] not in v["done"])
        s = {"id": v["id"], "ship": v["ship"], "name": SHIPS[v["ship"]]["name"], "t0": v["t0"], "landed": v["landed"],
             "end": v["left"] or v["t0"] + VISIT_MIN * 60, "note": v["note"], "trial": v["trial"],
             "sent": v["sent"], "refused": v["refused"], "skipped": v["skipped"] + unsent, "half": v["brake_half"],
             "half_strained": v.get("half_strained", 0), "half_node": v.get("half_node", 0),
             "unanswered": v.get("unanswered", 0), "unanswered_took": v.get("quiet_took", 0),
             "passengers": SHIPS[v["ship"]]["passengers"]}
        clean = v["landed"] and not v["left"]
        for k in v["trial"]:
            if clean and v["sent"].get(k) and not v["refused"].get(k) and not (k == "book" and v["refused"].get("cancel")):
                self.tried[k] = v["id"]
        s["tried"] = {k: self.tried.get(k) == v["id"] for k in v["trial"]}
        if v.get("tricks"):
            s["tricks"] = v["tricks"]
        s["per_min"] = self.rate_of(v["ship"])
        s["changed"] = self.tune_after(v, s)
        self.visits.append(s)
        self.visits = self.visits[-VISITS_KEEP:]
        self.write({"t": int(now), "visit": v["id"], "ship": v["ship"], "kind": "visit over", "summary": s})
        if s["changed"]:
            self.write({"t": int(now), "visit": v["id"], "ship": v["ship"], "kind": "tuned", "changes": s["changed"]})
            log.info("cruise: %s tuned for its next call: %s", v["ship"], s["changed"])
        self._check = {"visit": v["id"], "ship": v["ship"], "booked": list(v.get("booked") or [])[:CHECK_BOOKINGS], "at": now}
        self.save_state()

    # ---------- sending, in the island bot's free slots ----------
    async def step(self, ask, gov) -> bool:
        """Called by the island bot when it has nothing to send. Sends at most one passenger transaction; True if it did."""
        if not self.ready:
            return False
        now = self.clock()
        if await self.escrow_step(ask, gov, now):   # bookings ahead of a call: also while the ships are switched off
            return True
        if not self.enabled:
            return False
        if now - self._pruned > 3600:
            self.prune(now)
        chk = getattr(self, "_check", None)
        if chk and now - chk["at"] >= UNRELEASED:
            self._check = None
            await self.check_bookings(chk, ask, now)
            return False
        v = self.advance(now)
        if not v or not v["landed"] or v["left"] or self.phase(v, now) not in ("landing", "ashore", "boarding"):
            return False
        state = self.verdict(now)
        if state == "stalled":
            self.leave(now, "the testnet stalled", state)
            return False
        if state is None:
            return False
        strained, node_slow = state == "strained", now < self.slow_until
        slow = strained or node_slow
        gap = 60 / self.rate_of(v["ship"]) * (2 if slow else 1)
        if now < self.hold_until or now - self.last_send < gap or not self.budget():
            return False
        act = None
        for a in v["acts"]:
            if a["t"] > now:
                break
            if a["i"] in v["done"]:
                continue
            if now - a["t"] > MISS:   # the ship fell behind (the island bot was busy, or the relay was down): this stop is lost
                v["done"].add(a["i"])
                v["skipped"] += 1
                continue
            act = a
            break
        if act is None:
            return False
        if slow:   # why half pace: the testnet's load verdict, or our own node answering slowly (a send it left unanswered)
            v["brake_half"] += 1
            k = "half_strained" if strained else "half_node"
            v[k] = v.get(k, 0) + 1
        v["done"].add(act["i"])
        self.last_send = now
        try:
            await self.send(v, act, ask, gov, state)
        except Exception as exc:   # one bad answer must not stop the ship or the bot
            log.warning("cruise %s %s failed: %r", v["id"], act["kind"], exc)
        self.save_state()
        return True

    def build(self, ship: str, act: dict, seq: int, tip: int, fee: int, rid: str | None = None, signer: str | None = None) -> dict:
        """The passenger's signed transaction. Two of the pirates' tricks are made here: act "expired" (its time ran out
        two minutes ago) and `signer` (signed with that other wallet's key, so the signature does not match the sender)."""
        from py_ecc.bls import G2Basic
        name = f"{ship}-{act['p']}"
        pk = self.pk[name]
        now = int(self.clock())
        env = {"sender_pubkey": pk, "sequence_number": seq, "expiration_time": now + 600, "expire_at_height": tip + 1000}
        if act.get("expired"):
            env["expiration_time"] = now - 120
        if act.get("stale"):
            env["expire_at_height"] = max(1, tip - 5)
        k = act["kind"]
        if k == "pay":
            tx = {"tx_type": "user_tx", **env, "fee_limit": "0" if act.get("freeride") else str(fee * 5),
                  "operations": {"1": [[act.get("from") or pk, PLACES[act["to"]], str(act["amount"])]]}}
        elif k == "bill":
            to = act["to"]
            tx = {"tx_type": "user_tx", **env, "fee_limit": str(fee * 5 * len(to)), "operations": {"1": [[pk, PLACES[pl], str(a)] for pl, a in to]}}
        elif k == "book":   # the transaction must expire before its release (DEADLINE_AFTER_RELEASE)
            env["expiration_time"] = min(env["expiration_time"], act["rel"] - 1)
            tx = {"tx_type": "retractable_transfer", **env, "fee_limit": str(fee * 5), "recipient_pubkey": PLACES[act["to"]],
                  "amount": int(act["amount"]), "release_at_time": int(act["rel"])}
        elif k == "escrow":   # booked ahead: the fare waits in escrow for the ship's till until the arrival
            env["expiration_time"] = min(env["expiration_time"], act["rel"] - 1)
            tx = {"tx_type": "retractable_transfer", **env, "fee_limit": str(fee * 5), "recipient_pubkey": act["till"],
                  "amount": int(act["amount"]), "release_at_time": int(act["rel"])}
        elif k in ("cancel", "unbook"):   # feeless (docs/retractable.md); no use once the booking's time has come
            env["expiration_time"] = min(env["expiration_time"], act["rel"] - 1)
            env["expire_at_height"] = tip + 100
            tx = {"tx_type": "retract_transfer", **env, "fee_limit": "0", "retractable_id": rid}
        else:
            raise ValueError(k)
        tx["signature"] = G2Basic.Sign(self.sk[signer or name], hashlib.sha256(signing_bytes(tx)).digest()).hex()
        return tx

    @staticmethod
    def code_of(res) -> str | None:
        """The node's error code in a refusal, wherever the answer carries it."""
        if not isinstance(res, dict):
            return None
        for d in (res.get("error"), res.get("data"), res):
            if isinstance(d, dict) and isinstance(d.get("code"), str):
                return d["code"]
        m = re.search(r"\b(" + "|".join(CODES) + r")\b", json.dumps(res))
        return m.group(1) if m else None

    async def send_trick(self, v: dict, act: dict, ask, gov, state: str | None) -> dict | None:
        """One pirate trick (TRICKS): sent like any payment, but the chain is meant to say no. Refused = the chain
        working (counted apart, never a refusal for the brakes or the load page); taken = a finding, held back."""
        import asyncio
        ship, name, trick = v["ship"], f"{v['ship']}-{act['p']}", act["trick"]
        pk = self.pk[name]
        expect, what = TRICKS[trick]
        entry = {"t": int(self.clock()), "visit": v["id"], "ship": ship, "i": act["i"], "p": act["p"], "kind": "trick", "trick": trick,
                 "what": what, "to": act["to"], "amount": act["amount"], "from": pk, "verdict": state, "expect": list(expect)}
        pay = {**act, "kind": "pay"}

        def skip(note: str):
            entry.update(ok=None, note=note)
            v["skipped"] += 1
            self.write(entry)

        if trick == "replay":   # the newest payment a pirate got through, while it is still within its time (else it is refused as expired)
            now = int(self.clock())
            fresh = [(t["expiration_time"], n, t) for n, t in (v.get("took") or {}).items() if t.get("expiration_time", 0) - now >= 120]
            if not fresh:
                return skip("nothing to replay yet: no pirate payment the chain took is still within its time")
            _, name, tx = max(fresh, key=lambda x: x[0])
            entry.update(p=int(name.rsplit("-", 1)[1]), **{"from": tx["sender_pubkey"]})
            entry["amount"] = int(((tx.get("operations") or {}).get("1") or [[0, 0, 0]])[0][2])
        else:
            st = await ask(f"getsequence {pk}")
            if not st or st.get("status") != "ok":
                return skip("no answer from the node to getsequence")
            d = st.get("data") or {}
            seq, tip = int(d.get("sequence_number") or 0), int(d.get("tip_height") or 0)
            entry.update(seq=seq, height=tip)
            signer = None
            if trick == "overspend":
                b = await ask(f"getbalance {pk}")
                if not b or b.get("status") != "ok":
                    return skip("no answer from the node to getbalance")
                bal = int((b.get("data") or {}).get("balance") or 0)
                pay["amount"] = entry["amount"] = bal + 1000
                entry["balance"] = bal
            elif trick == "expired":
                pay["expired"] = True
            elif trick == "stale":
                pay["stale"] = True
            elif trick == "freeride":
                pay["freeride"] = True
            elif trick == "giant":
                pay["amount"] = entry["amount"] = 1 << 24   # tau_defs.TRANSFER_VALUE_BV_WIDTH = 24
            elif trick == "forged":
                signer = f"{ship}-{(act['p'] + 1) % SHIPS[ship]['passengers']}"
            elif trick == "impostor":   # the transfer names another pirate's wallet as payer, signed by this pirate
                pay["from"] = self.pk[f"{ship}-{(act['p'] + 1) % SHIPS[ship]['passengers']}"]
            tx = await asyncio.to_thread(self.build, ship, pay, seq, tip, base_fee(gov()), None, signer)
        t_ask = time.monotonic()
        res = await ask("sendtx " + json.dumps(tx, separators=(",", ":")))
        entry["ms"] = int((time.monotonic() - t_ask) * 1000)
        entry["tx"] = tx   # signed and public anyway once sent; a key never goes in here
        c = v.setdefault("tricks", {}).setdefault(trick, {"tried": 0, "stopped": 0, "right": 0, "through": 0})
        if res is None:   # no answer in time: not a refusal and not a finding, the node is slow
            now = self.clock()
            self.hold_until, self.slow_until = now + QUIET_HOLD, now + QUIET_SLOW
            v["unanswered"] = v.get("unanswered", 0) + 1
            entry.update(ok=None, note=f"no answer from the node to sendtx; the ship waits {QUIET_HOLD} s, then goes at half pace")
            self.write(entry)
            return None
        c["tried"] += 1
        ok = res.get("status") == "ok" and (res.get("data") or {}).get("ok") is not False
        if ok:
            c["through"] += 1
            self.spend()
            entry.update(ok=True, through=True, hash=(res.get("data") or {}).get("tx_hash"),
                         note="got through: the chain took what it should have refused; held back and reported privately first")
            for a in v["acts"]:   # not again this visit
                if a["kind"] == "trick" and a.get("trick") == trick:
                    v["done"].add(a["i"])
            self.write(entry)
            self.incident(self.clock(), "trick through", f"A pirate trick got through: the pirate {what}, and the chain took it.",
                          {"trick": trick, "tx": tx, "answer": res})
            log.warning("cruise %s: trick %s got through", v["id"], trick)
            return res
        code = self.code_of(res)
        right = code in expect
        c["stopped"] += 1
        c["right"] += right
        err = res.get("error") or res
        entry.update(ok=False, stopped=True, code=code, right=right,
                     err=(json.dumps(err, separators=(",", ":")) if not isinstance(err, str) else err)[:300],
                     note="stopped by the chain" + ("" if right else f", with another answer than {' or '.join(expect)}"))
        self.write(entry)
        return res

    async def booking_id(self, pk: str, act: dict, ask) -> str | None:
        """The id of the passenger's open booking at that place for that time, as the node lists it."""
        res = await ask(f"getretractables {pk} out")
        if not res or res.get("status") != "ok":
            return None
        for e in (res.get("data") or {}).get("retractables") or []:
            if str(e.get("recipient_pubkey", "")).lower() == PLACES[act["to"]] and int(e.get("release_at_time") or 0) == int(act["rel"]):
                return str(e.get("retractable_id") or "") or None
        return None

    async def send(self, v: dict, act: dict, ask, gov, state: str | None) -> dict | None:
        import asyncio
        if act["kind"] == "trick":
            return await self.send_trick(v, act, ask, gov, state)
        ship, name = v["ship"], f"{v['ship']}-{act['p']}"
        pk = self.pk[name]
        entry = {"t": int(self.clock()), "visit": v["id"], "ship": ship, "i": act["i"], "p": act["p"], "kind": act["kind"],
                 "to": act["to"], "amount": act["amount"], "from": pk, "verdict": state}
        if "rel" in act:
            entry["release_at_time"] = act["rel"]
        rid = None
        if act["kind"] == "cancel":
            rid = await self.booking_id(pk, act, ask)
            if not rid:   # not open: the booking was refused, is not in a block yet, or its time came first
                entry.update(ok=None, note="nothing to withdraw: the booking is not open")
                v["skipped"] += 1
                self.write(entry)
                return None
            entry["retractable_id"] = rid
        st = await ask(f"getsequence {pk}")
        if not st or st.get("status") != "ok":
            entry.update(ok=None, note="no answer from the node to getsequence")
            v["skipped"] += 1
            self.write(entry)
            return None
        d = st.get("data") or {}
        seq = int(d.get("sequence_number") or 0)   # the node counts what waits in its mempool; nothing cached, so a restarted chain is fine
        tip = int(d.get("tip_height") or 0)
        quiet = v.setdefault("quiet", {})
        if name in quiet:   # this passenger's last send went unanswered: did the node take it after all?
            q = quiet.pop(name)
            took = seq > q["seq"]
            v["quiet_took" if took else "quiet_lost"] = v.get("quiet_took" if took else "quiet_lost", 0) + 1
            self.write({"t": int(self.clock()), "visit": v["id"], "ship": ship, "i": q["i"], "p": act["p"], "kind": "unanswered checked",
                        "took": took, "note": "the node took it after all (the sequence moved on)" if took else "it did not reach the node"})
        tx = await asyncio.to_thread(self.build, ship, act, seq, tip, base_fee(gov()), rid)
        t_ask = time.monotonic()
        res = await ask("sendtx " + json.dumps(tx, separators=(",", ":")))
        entry["ms"] = int((time.monotonic() - t_ask) * 1000)   # how long our node took to answer (the relay waits in line for it too)
        if res is None:   # no answer in time (or the relay's connection to the node dropped): not a refusal
            now = self.clock()
            self.hold_until, self.slow_until = now + QUIET_HOLD, now + QUIET_SLOW
            v["unanswered"] = v.get("unanswered", 0) + 1
            v.setdefault("quiet", {})[name] = {"seq": seq, "i": act["i"]}
            entry.update(seq=seq, height=tip, ok=None, note=f"no answer from the node to sendtx; the ship waits {QUIET_HOLD} s, then goes at half pace")
            entry["tx"] = tx
            self.write(entry)
            log.info("cruise %s %s unanswered", v["id"], act["kind"])
            return None
        ok = bool(res) and res.get("status") == "ok" and (res.get("data") or {}).get("ok") is not False
        entry.update(seq=seq, height=tip, ok=ok, hash=((res or {}).get("data") or {}).get("tx_hash") if ok else None)
        if ok:
            v["sent"][act["kind"]] += 1
            self.spend()
            if act["kind"] == "pay" and "trick" in (v.get("allowed") or []):   # a pirate's last payment, for the replay trick
                v.setdefault("took", {})[name] = tx
            if act["kind"] == "book":
                v["booked"].append(act["p"])
        else:
            v["refused"][act["kind"]] += 1
            err = (res or {}).get("error") or res
            entry["err"] = json.dumps(err, separators=(",", ":"))[:300] if not isinstance(err, str) else err[:300]
            log.info("cruise %s %s refused: %.200s", v["id"], act["kind"], entry["err"])
        if act["kind"] != "pay" or not ok:
            entry["tx"] = tx   # signed and public anyway once sent; a key never goes in here
        self.write(entry)
        self.on_tx and self.on_tx(ok)
        if not ok:
            last = [e for e in self.logbook if e.get("visit") == v["id"] and e.get("kind") in KINDS and e.get("ok") is not None][-REFUSE_WINDOW:]
            if sum(1 for e in last if e.get("ok") is False) >= REFUSE_STOP:
                self.leave(self.clock(), f"the node refused {REFUSE_STOP} of the last {len(last)} passenger transactions", "refused")
        return res

    async def check_bookings(self, chk: dict, ask, now: float):
        """After a visit: every checked passenger's bookings whose time has passed must be released by the chain."""
        stuck = []
        for p in chk["booked"]:
            pk = self.wallet(chk["ship"], p)
            res = await ask(f"getretractables {pk} out") if pk else None
            if not res or res.get("status") != "ok":
                continue
            for e in (res.get("data") or {}).get("retractables") or []:
                t = int(e.get("release_at_time") or 0)
                if t and t < now - UNRELEASED:
                    stuck.append({"passenger": p, "retractable_id": e.get("retractable_id"), "release_at_time": t})
        self.write({"t": int(now), "visit": chk["visit"], "ship": chk["ship"], "kind": "bookings checked",
                    "checked": len(chk["booked"]), "not_released": stuck})
        if stuck:
            if self.tried.get("book") == chk["visit"]:   # not clean after all: the next visit tries bookings again, small
                self.tried["book"] = None
                self.save_state()
            self.incident(now, "not released", "Bookings stayed in escrow after their time.", {"visit": chk["visit"], "ship": chk["ship"], "bookings": stuck})

    # ---------- bookings ahead of a call, in escrow until the arrival ----------
    def escrow_open(self) -> bool:
        """Some booking ahead may still be in escrow or on its way there (the wallets are needed to refund it)."""
        return any(b.get("status") in ("in escrow", "sent", "refund sent") for e in self.escrow.values() if not e.get("settled")
                   for b in e.get("bookings") or [])

    def call_off(self, e: dict, now: float, why: str):
        if e.get("off"):
            return
        e["off"] = {"t": int(now), "why": why}
        for b in e["bookings"]:
            if b["status"] == "planned":
                b.update(status="not booked", note="the call was called off before this booking went out")
        held = sum(1 for b in e["bookings"] if b["status"] in ("in escrow", "sent"))
        self.write({"t": int(now), "visit": e["id"], "ship": e["ship"], "kind": "called off", "note": why, "refunds": held,
                    "arrival": e["t0"]})
        log.warning("cruise: %s called off before arrival (%s), %d bookings to refund", e["id"], why, held)
        self.save_state()

    async def park_of(self, b: dict, ask) -> tuple[str | None, str | None]:
        """(retractable id, status: open / released / retracted / None) of a booking, from its park's hash."""
        if b.get("hash"):
            res = await ask(f"gettxstatus {b['hash']}")
            d = (res or {}).get("data") or {}
            r = d.get("retractable") if isinstance(d.get("retractable"), dict) else None
            if r and r.get("id"):
                b["rid"] = str(r["id"])
                st = r.get("status")
                return b["rid"], st if st in ("open", "released", "retracted") else None
        if b.get("rid"):
            res = await ask(f"getretractable {b['rid']}")
            st = ((res or {}).get("data") or {}).get("status")
            return b["rid"], st if st in ("open", "released", "retracted") else None
        return None, None

    async def find_park(self, e: dict, b: dict, ask, mempool: bool = True) -> str | None:
        """The passenger's booking to the till for this arrival, open or waiting in the mempool, as the node lists it."""
        res = await ask(f"getretractables {self.wallet(e['ship'], b['p'])} out")
        if not res or res.get("status") != "ok":
            return None
        d = res.get("data") or {}
        for x in (d.get("retractables") or []) + [m for m in d.get("mempool") or [] if mempool and m.get("tx_type") == "retractable_transfer"]:
            if str(x.get("recipient_pubkey", "")).lower() == self.till.get(e["ship"]) and int(x.get("release_at_time") or 0) == int(e["t0"]):
                return str(x.get("retractable_id") or "") or None
        return None

    async def escrow_step(self, ask, gov, now: float) -> bool:
        """Plans the bookings ahead of the next calls, sends one booking or refund when one is due, and settles a call
        after its arrival. True if a transaction went out."""
        if self.enabled:
            for t0, ship in calls_near(now, 4):
                vid = visit_id(t0, ship)
                if SHIPS[ship].get("escrow") and vid not in self.escrow and t0 - ESCROW_AHEAD <= now < t0 - ESCROW_CLOSE \
                        and not any(v.get("id") == vid for v in self.visits) and ship in self.till:
                    bs = escrow_plan(ship, t0, now)
                    if bs:
                        self.escrow[vid] = {"id": vid, "ship": ship, "t0": t0, "till": self.till[ship], "off": None, "bookings": bs}
                        self.write({"t": int(now), "visit": vid, "ship": ship, "kind": "escrow", "status": "bookings open",
                                    "planned": len(bs), "arrival": t0, "till": self.till[ship]})
                        self.save_state()
        due = None
        for e in sorted(self.escrow.values(), key=lambda x: x["t0"]):
            if e.get("settled"):
                continue
            t0 = e["t0"]
            if not e.get("off") and now < t0 - RETRACT_MARGIN:
                if not self.enabled:
                    self.call_off(e, now, "the ships are switched off")
                elif now >= t0 - CALL_OFF and self.verdict(now) == "stalled":
                    self.call_off(e, now, "the testnet was stalled at the check before arrival")
            for b in e["bookings"]:
                st = b["status"]
                if st == "planned" and now >= t0 - ESCROW_CLOSE:
                    b.update(status="not booked", note="the booking time closed before it could go out")
                    self.save_state()
                    continue
                want_refund = st in ("in escrow", "sent") and (e.get("off") or (b.get("withdraw_at") and now >= b["withdraw_at"]))
                if want_refund and now >= t0 - RETRACT_MARGIN:
                    if not b.get("late"):
                        b["late"] = True
                        b["note"] = "the refund could not go out in time; the arrival releases it to the till"
                        self.save_state()
                    continue
                if b.get("late") or now < b.get("wait_until", 0):
                    continue
                if due is None and (want_refund or (st == "planned" and now >= b["at"] and self.enabled and not e.get("off"))):
                    due = (e, b, "refund" if want_refund else "book ahead")
            if now >= t0 + UNRELEASED and now >= e.get("settle_next", 0):
                await self.settle(e, ask, now)
        if not due or now < self.hold_until or now - self.last_send < 60 / RATE:
            return False
        e, b, kind = due
        if kind == "book ahead" and not self.budget():
            return False
        sent = False
        try:
            sent = bool(await self.send_escrow(e, b, kind, ask, gov, now))
        except Exception as exc:
            log.warning("cruise %s %s failed: %r", e["id"], kind, exc)
        if sent:
            self.last_send = now
        self.save_state()
        return sent

    async def send_escrow(self, e: dict, b: dict, kind: str, ask, gov, now: float):
        import asyncio
        ship = e["ship"]
        pk = self.wallet(ship, b["p"])
        entry = {"t": int(now), "visit": e["id"], "ship": ship, "p": b["p"], "kind": kind, "to": "till", "amount": b["amount"],
                 "from": pk, "release_at_time": e["t0"], "verdict": self.verdict(now)}
        if kind == "book ahead" and b.get("tries"):   # an earlier send went unanswered: is it in escrow after all?
            rid = await self.find_park(e, b, ask)
            if rid:
                b.update(status="in escrow", rid=rid)
                entry.update(ok=True, retractable_id=rid, note="the earlier unanswered booking reached the node after all")
                self.write(entry)
                return
        rid = None
        if kind == "refund":
            rid, st = await self.park_of(b, ask)
            if not rid:   # only a booking in a block can be taken back
                rid = await self.find_park(e, b, ask, mempool=False)
            if st in ("released", "retracted"):
                b["status"] = "paid out" if st == "released" else "refunded"
                entry.update(ok=None, retractable_id=rid, note="nothing to take back: the booking is " + st)
                self.write(entry)
                return
            if not rid:   # not in a block yet (or never got there): look again in a minute, until RETRACT_MARGIN
                b["wait_until"] = int(now + 60)
                return
            b["rid"] = rid
            entry["retractable_id"] = rid
        st = await ask(f"getsequence {pk}")
        if not st or st.get("status") != "ok":
            entry.update(ok=None, note="no answer from the node to getsequence")
            self.write(entry)
            return
        d = st.get("data") or {}
        seq, tip = int(d.get("sequence_number") or 0), int(d.get("tip_height") or 0)
        act = {"p": b["p"], "kind": "escrow" if kind == "book ahead" else "unbook", "amount": b["amount"], "rel": e["t0"], "till": e["till"]}
        tx = await asyncio.to_thread(self.build, ship, act, seq, tip, base_fee(gov()), rid)
        t_ask = time.monotonic()
        res = await ask("sendtx " + json.dumps(tx, separators=(",", ":")))
        entry["ms"] = int((time.monotonic() - t_ask) * 1000)
        entry.update(seq=seq, height=tip, tx=tx)
        if res is None:
            n = self.clock()
            self.hold_until, self.slow_until = n + QUIET_HOLD, n + QUIET_SLOW
            b["tries"] = b.get("tries", 0) + 1
            entry.update(ok=None, note=f"no answer from the node to sendtx; tried again in {QUIET_HOLD} s at the earliest")
            if b["tries"] >= ESCROW_TRIES:
                if kind == "book ahead":
                    b.update(status="sent", note="sent, the node did not answer: checked on the chain after the arrival")
                else:
                    b["note"] = "the refund went unanswered " + str(ESCROW_TRIES) + " times: checked on the chain after the arrival"
                    b["status"] = "refund sent"
            self.write(entry)
            return True
        ok = res.get("status") == "ok" and (res.get("data") or {}).get("ok") is not False
        h = (res.get("data") or {}).get("tx_hash") if ok else None
        entry.update(ok=ok, hash=h)
        if ok:
            self.spend()
            if kind == "book ahead":
                b.update(status="in escrow", hash=h, booked_at=int(now))
            else:
                b.update(status="refund sent", refund_hash=h, refund_at=int(now))
        else:
            err = res.get("error") or res
            entry["err"] = (err if isinstance(err, str) else json.dumps(err, separators=(",", ":")))[:300]
            if kind == "book ahead":
                b.update(status="refused", note=entry["err"][:140])
            else:
                b["tries"] = b.get("tries", 0) + 1
                if b["tries"] >= ESCROW_TRIES:
                    b["note"] = "the node refused the refund: " + entry["err"][:120]
                    b["late"] = True   # no more tries: the arrival decides
        self.write(entry)
        self.on_tx and self.on_tx(ok)
        return True

    async def settle(self, e: dict, ask, now: float):
        """After the arrival: every booking as the chain has it, paid out to the till or refunded to the passenger.
        A booking the node cannot tell yet is asked again every SETTLE_AGAIN seconds, for six hours at most."""
        found = []
        for b in e["bookings"]:
            st, rid = None, b.get("rid")
            if b["status"] not in ("not booked", "refused", "planned"):
                rid, st = await self.park_of(b, ask)
                if not rid and b["status"] == "sent":   # an unanswered booking: did it reach the chain?
                    rid = await self.find_park(e, b, ask)
                    st = "open" if rid else None
            found.append((b, rid, st))
        unknown = [b for b, rid, st in found if st is None and b["status"] not in ("not booked", "refused", "planned", "sent")]
        if unknown and now < e["t0"] + 6 * 3600:
            e["settle_next"] = int(now + SETTLE_AGAIN)
            self.save_state()
            return
        stuck, out = [], {}
        for b, rid, st in found:
            if st == "released":
                b["status"] = "paid out"
            elif st == "retracted":
                b["status"] = "refunded"
            elif st == "open":
                b["status"] = "not released"
                stuck.append({"passenger": b["p"], "retractable_id": rid, "release_at_time": e["t0"]})
            elif b["status"] == "sent":
                b.update(status="not booked", note="the booking never reached the chain")
            elif b["status"] not in ("not booked", "refused"):
                b["status"] = "unknown"
            out[b["status"]] = out.get(b["status"], 0) + 1
            if b["status"] in ("not booked", "refused") and not b.get("hash"):
                continue
            self.write({"t": int(now), "visit": e["id"], "ship": e["ship"], "p": b["p"], "kind": "escrow", "to": "till",
                        "amount": b["amount"], "status": b["status"], "hash": b.get("hash"), "retractable_id": rid,
                        "note": b.get("note"), "ok": b["status"] in ("paid out", "refunded")})
        e["settled"], e["result"] = int(now), out
        self.write({"t": int(now), "visit": e["id"], "ship": e["ship"], "kind": "escrow", "status": "settled", "result": out,
                    "called_off": (e.get("off") or {}).get("why")})
        if stuck:
            self.incident(now, "not released", "Bookings ahead of the call stayed in escrow after the arrival.",
                          {"visit": e["id"], "ship": e["ship"], "bookings": stuck})
        self.save_state()

    def escrow_view(self, now: float) -> list[dict]:
        """The bookings ahead of the last calls, newest first, for the pages."""
        out = []
        for e in sorted(self.escrow.values(), key=lambda x: -x["t0"])[:4]:
            bs = [{k: b.get(k) for k in ("p", "amount", "status", "at", "hash", "refund_hash", "note")} | {"withdraw": bool(b.get("withdraw_at"))}
                  for b in e["bookings"]]
            count = {}
            for b in bs:
                count[b["status"]] = count.get(b["status"], 0) + 1
            out.append({"visit": e["id"], "ship": e["ship"], "name": SHIPS[e["ship"]]["name"], "arrival": e["t0"], "till": e.get("till"),
                        "called_off": e.get("off"), "settled": bool(e.get("settled")), "count": count, "bookings": bs})
        return out

    # ---------- what pages see ----------
    def brief(self, now: float | None = None) -> dict:
        """The ship in port or the next one, for the testnet load page and the game's chip."""
        now = self.clock() if now is None else now
        v = self.current(now)
        out: dict = {"enabled": bool(self.enabled), "simulated": True}
        if v:
            ph = self.phase(v, now)
            end = v["t0"] + VISIT_MIN * 60
            at = where(v["acts"], now, v["left"] or v["t0"] + (VISIT_MIN - BOARDING) * 60, v["ship"]) if v["landed"] else {}
            out["now"] = {"visit": v["id"], "ship": v["ship"], "name": SHIPS[v["ship"]]["name"], "style": SHIPS[v["ship"]]["style"],
                          "phase": ph, "t0": v["t0"], "end": v["left"] or end, "passengers": SHIPS[v["ship"]]["passengers"],
                          "ashore": sum(at.values()), "at": at, "sent": v["sent"], "refused": sum(v["refused"].values()),
                          "skipped": v["skipped"], "planned": len(v["acts"]), "trial": v["trial"], "note": v["note"], "why": self.why(v),
                          "tricks": {"tried": sum(c["tried"] for c in (v.get("tricks") or {}).values()),
                                     "stopped": sum(c["stopped"] for c in (v.get("tricks") or {}).values())},
                          "per_min": self.rate_of(v["ship"]),
                          "kinds": ["pay"] + list((v.get("allowed") or []) if v["landed"] else self.kinds_for(v["ship"])[1]),
                          "brake": "stopped" if v["left"] and v["note"].startswith("left") else "half" if self._verdict[1] == "strained" and v["landed"]
                          else "slow" if v["landed"] and now < self.slow_until else "none"}
        n = self.next_call(now) if self.enabled else None   # switched off (CRUISE_ENABLED=0): no ship is announced
        if n:
            out["next"] = {"ship": n[1], "name": SHIPS[n[1]]["name"], "t0": n[0]}
        out["bands"] = [[s["t0"], s["end"], s["name"]] for s in self.visits if s.get("landed") and s["end"] > now - 6 * 3600]
        if v and v["landed"]:
            out["bands"].append([v.get("landed_at", v["t0"]), v["left"] or min(now, v["t0"] + VISIT_MIN * 60), SHIPS[v["ship"]]["name"]])
        return out

    def snapshot(self, now: float | None = None) -> dict:
        now = self.clock() if now is None else now
        out = self.brief(now)
        out["ships"] = {k: {"name": s["name"], "weekday": s["weekday"], "time": f"{s['hour']:02d}:00", "zone": "Europe/Berlin",
                            "passengers": s["passengers"], "kinds": ["pay"] + list(s["kinds"]), "minutes": VISIT_MIN} for k, s in SHIPS.items()}
        out["wallets"] = {k: [self.pk[f"{k}-{n}"] for n in range(s["passengers"]) if f"{k}-{n}" in self.pk] for k, s in SHIPS.items()}
        out["places"] = {k: PLACES[k] for k in sorted({p for s in SHIPS.values() for p in s["stops"]} | {"pier"})}
        out["recent"] = [{k: e.get(k) for k in ("t", "kind", "to", "amount", "hash", "ok")} for e in list(self.logbook)[-RECENT:][::-1]
                         if e.get("kind") in KINDS]
        out["last"] = self.visits[-1] if self.visits else None
        out["tried"] = self.tried
        out["escrow"] = self.escrow_view(now)
        out["limits"] = {"per_min": RATE, "per_min_least": RATE_MIN, "visit_max": VISIT_MAX, "trial_max": TRIAL_MAX, "log_days": LOG_DAYS}
        out["pace"] = {k: self.rate_of(k) for k in SHIPS}
        out["tricks"] = {k: what for k, (_, what) in TRICKS.items()}
        out["quiet_days"] = [d for d in range(7) if not any(s["weekday"] == d for s in SHIPS.values())]
        if out.get("last"):
            out["last"] = self.public(out["last"])
        return out

    # ---------- findings held back ----------
    def released(self) -> set:
        """Visits whose held findings may be shown (up cruise release <visit> writes the file)."""
        try:
            m = os.path.getmtime(self.released_path)
        except OSError:
            return set()
        if self._released[0] != m:
            try:
                with open(self.released_path) as f:
                    self._released = (m, {str(x) for x in json.load(f)})
            except (OSError, ValueError, TypeError):
                self._released = (m, set())
        return self._released[1]

    def public(self, e: dict) -> dict:
        """An entry, summary or incident as the public sees it: a trick that got through shows only that something
        was held back, until its visit is released."""
        vid = e.get("visit") or e.get("id")
        if vid in self.released():
            return e
        if e.get("through") or e.get("kind") == "trick through":
            return {k: e.get(k) for k in ("t", "at", "visit", "ship", "i", "p") if k in e} | {
                "kind": "trick" if e.get("through") else "held", "held": True, "ok": None,
                "note": "held back: a finding, reported privately to the team behind the testnet first"}
        if "summary" in e or "changes" in e or "tricks" in e or "tail" in e:
            e = dict(e)
            if isinstance(e.get("tail"), list):
                e["tail"] = [self.public(x) if isinstance(x, dict) else x for x in e["tail"]]
            if isinstance(e.get("summary"), dict):
                e["summary"] = self.public(e["summary"])
            if isinstance(e.get("changes"), list):
                e["changes"] = [c if not c.get("held") else {"what": "a pirate trick", "held": True} for c in e["changes"]]
            if isinstance(e.get("changed"), list):
                e["changed"] = [c if not c.get("held") else {"what": "a pirate trick", "held": True} for c in e["changed"]]
            if isinstance(e.get("tricks"), dict) and any(isinstance(c, dict) and c.get("through") for c in e["tricks"].values()):
                e["tricks"] = {k: (c if not (isinstance(c, dict) and c.get("through")) else {"held": True}) for k, c in e["tricks"].items()}
        return e

    def held(self) -> dict:
        """For the server only (alerts/cruise_crier.py, no X-Forwarded-For): every finding held back, newest first."""
        rel = self.released()
        rows = [e for e in self.logbook if e.get("through")]
        return {"simulated": True, "entries": rows[::-1], "released": sorted(rel),
                "incidents": [i for i in self.incidents if i.get("kind") == "trick through"][::-1]}

    def route(self, path: str, query: str = "", internal: bool = False) -> dict | None:
        if path == "/cruise":
            return self.snapshot()
        if path == "/cruise/held":
            return self.held() if internal else {"error": "only from inside the server"}
        if path == "/cruise/log":
            q = parse_qs(query or "")
            try:
                n = max(1, min(2000, int((q.get("n") or ["200"])[0])))
            except ValueError:
                n = 200
            vid = (q.get("visit") or [""])[0]
            rows = [] if vid and not VISIT_RE.match(vid) else [e for e in self.logbook if not vid or e.get("visit") == vid]
            return {"simulated": True, "days": LOG_DAYS, "entries": [self.public(e) for e in rows[-n:][::-1]],
                    "visits": [s["id"] for s in self.visits][::-1], "escrow": self.escrow_view(self.clock())}
        if path == "/cruise/incidents":
            return {"simulated": True, "incidents": [self.public(i) for i in self.incidents[::-1]]}
        return None

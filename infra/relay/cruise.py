"""Cruise ships at White Rabbit Key: openly simulated passengers whose island visits are real, paced test transactions.

Two ships call by a timetable on the island's clock (Europe/Berlin):
  Wednesday 16:00  MS Dry Run     a small expedition ship, 40 curious passengers: the lighthouse, Captain Wren's Old
                                  Ship, the school, the dive shop. It tries the rarer kinds of transaction.
  Saturday 14:00   Queen Mempool  a big luxury liner, 120 passengers: the South Current spa, Bar La Ola, song requests
                                  on Radio Coco, souvenirs. It brings the volume.
A visit lasts VISIT_MIN minutes: the tenders bring the passengers ashore in the first LANDING, and in the last BOARDING
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
- a kind the ship has not yet used cleanly (TRIAL: book, bill) goes out at most TRIAL_MAX times on its first visit, and
  only one new kind per visit; it counts as tried once a visit with it ends with no refusal of that kind and no brake.

The logbook: every transaction a passenger sends (kind, place, amount, hash, the node's answer, the chain height, the
load verdict at that moment) goes to CRUISE_LOG_PATH for LOG_DAYS days, with the signed transaction for the rare kinds
and for every refusal; GET /cruise/log shows it. A stall during a visit adds an incident to CRUISE_INCIDENTS_PATH: the
last INCIDENT_TAIL entries before it, the newest block, the transaction that has waited longest. So if the testnet
breaks while a ship is in port, the logbook says what it sent; and when it was not the ship, the logbook says that too.

GET /cruise            the timetable, the ship in port (or the next), passengers ashore and where, counts, wallets
GET /cruise/log        logbook entries, newest first (?n=200, ?visit=<id>)
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
LANDING = 10               # minutes the tenders bring the passengers ashore
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
CHECK_BOOKINGS = 10        # passengers whose bookings are checked with the node when a visit ends

SHIPS = {
    "dryrun": {
        "name": "MS Dry Run", "weekday": 2, "hour": 16, "passengers": 40, "style": "expedition",
        # place: (test AGRS a visit pays there, how much the passengers want to go there)
        "stops": {"book": (2, 3), "ship": (3, 3), "school": (6, 2), "dive": (12, 3), "market": (8, 1), "works": (4, 1), "bar": (5, 1)},
        "per": (4, 6), "dwell": (10, 18),
        "book": {"share": 0.45, "at": ("dive", "book"), "cancel": 0.3},
        "bill": 0.0, "kinds": ("book",),
    },
    "queen": {
        "name": "Queen Mempool", "weekday": 5, "hour": 14, "passengers": 120, "style": "liner",
        "stops": {"south": (20, 4), "bar": (5, 4), "radio": (25, 2), "market": (8, 3), "works": (4, 2), "dive": (12, 1), "book": (2, 1)},
        "per": (3, 5), "dwell": (8, 16),
        "book": {"share": 0.2, "at": ("south",), "cancel": 0.1},
        "bill": 0.3, "kinds": ("bill", "book"),
    },
}
CLOSED = frozenset({"ama", "stone", "drums", "circle", "grotto", "hall", "north", "camp", "canoe"})   # no tour group goes there
BILL = (("bar", 5), ("radio", 25), ("works", 4))   # a table's evening: drinks and coconut snacks per head, one song request
KINDS = ("pay", "bill", "book", "cancel")
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


def visit_id(t0: int, ship: str) -> str:
    return berlin_day(t0).isoformat() + "-" + ship


def plan(ship: str, t0: int, trial: set | None = None, allowed: set | None = None) -> list[dict]:
    """Every passenger's day ashore, the same for the same visit (seeded by its id), by time.
    trial: kinds limited to TRIAL_MAX this visit; allowed: the kinds this visit may send besides "pay"."""
    S = SHIPS[ship]
    trial, allowed = trial or set(), set(S["kinds"]) if allowed is None else allowed
    R = random.Random(visit_id(t0, ship))
    end = t0 + (VISIT_MIN - BOARDING) * 60
    left = {k: TRIAL_MAX if k in trial else 10 ** 6 for k in TRIAL}
    names, weights = list(S["stops"]), [w for _, w in S["stops"].values()]
    acts: list[dict] = []
    forced = "book" in trial   # a trial of bookings also tries one withdrawal
    for p in range(S["passengers"]):
        land = t0 + R.uniform(0, LANDING * 60)
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
    acts.sort(key=lambda a: (a["t"], a["p"]))
    acts = acts[:VISIT_MAX]
    for i, a in enumerate(acts):
        a["i"] = i
        a["t"] = int(a["t"])
    return acts


def where(acts: list[dict], now: float, end: float) -> dict[str, int]:
    """How many passengers are at each place now, by the stops they have reached (pier on landing)."""
    last: dict[int, str] = {}
    if now >= end:
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
        self.enabled = (os.environ.get("CRUISE_ENABLED", "1") != "0") if enabled is None else enabled
        self.clock = clock
        self.verdict_fn = verdict or (lambda: None)     # relay: the load verdict now (calm / busy / strained / stalled, None while syncing)
        self.chain_fn = chain or (lambda: {})           # relay: the newest block and the longest waiting transaction
        self.budget = budget or (lambda: True)          # relay: room left in the island's day budget
        self.spend = spend or (lambda: None)            # relay: one transaction taken from it
        self.on_tx = None                               # relay: the testnet load page counts it (ok) or a refusal
        self.ready = False
        self.sk: dict[str, int] = {}
        self.pk: dict[str, str] = {}                    # "<ship>-<n>" -> public key
        self.who: dict[str, str] = {}                   # public key -> ship
        self.tried: dict[str, str | None] = {k: None for k in TRIAL}   # kind -> the visit that first used it cleanly
        self.visits: list[dict] = []                    # summaries of the last visits, newest last
        self.cur: dict | None = None                    # the visit under way
        self.logbook: deque = deque(maxlen=LOG_KEEP)
        self.incidents: list[dict] = []
        self.last_send = 0.0
        self._verdict = (0.0, None)
        self._pruned = 0.0
        self.load_state()
        self.load_log()
        try:
            with open(self.incidents_path) as f:
                self.incidents = json.load(f)[-INCIDENTS_MAX:]
        except (OSError, ValueError, TypeError):
            pass
        if self.enabled:
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

    def load_keys(self):
        from py_ecc.bls import G2Basic
        keys = {}
        if os.path.exists(self.keys_path):
            with open(self.keys_path) as f:
                keys = json.load(f)
        names = [f"{k}-{n}" for k, s in SHIPS.items() for n in range(s["passengers"])]
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
        for n in names:
            sk[n], pk[n] = int(keys[n]["sk"], 16), keys[n]["pk"]
        self.sk, self.pk = sk, pk
        self.who = {v: n.split("-")[0] for n, v in pk.items()}
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
            self._saved_cur = st.get("cur") if isinstance(st.get("cur"), dict) else None
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
                                                "skipped", "unsent", "brake_half", "wait", "booked", "landed_at")}
            cur["done"] = sorted(self.cur["done"])
        try:
            tmp = self.state_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"tried": self.tried, "visits": self.visits[-VISITS_KEEP:], "cur": cur}, f, separators=(",", ":"))
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
                for k in ("landed", "left", "note", "trial", "allowed", "sent", "refused", "skipped", "unsent", "brake_half", "wait", "booked", "landed_at"):
                    if k in saved:
                        self.cur[k] = saved[k]
                self.cur["done"] = set(saved.get("done") or [])
                if self.cur["landed"]:
                    self.cur["acts"] = plan(ship, t0, set(self.cur["trial"]), set(self.cur["allowed"]))
            self._saved_cur = None
        v = self.cur
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
        new = [k for k in SHIPS[ship]["kinds"] if not self.tried.get(k)]
        trial = new[:1]
        return trial, [k for k in SHIPS[ship]["kinds"] if k not in new or k in trial]

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
        if now < t0 + LANDING * 60:
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
            v.update(landed=True, trial=trial, allowed=allowed, landed_at=int(now))
            v["acts"] = plan(v["ship"], v["t0"], set(trial), set(allowed))
            self.write({"t": int(now), "visit": v["id"], "ship": v["ship"], "kind": "landed", "verdict": state,
                        "plan": len(v["acts"]), "trial": trial, "allowed": ["pay"] + allowed})
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
             "passengers": SHIPS[v["ship"]]["passengers"]}
        clean = v["landed"] and not v["left"]
        for k in v["trial"]:
            if clean and v["sent"].get(k) and not v["refused"].get(k) and not (k == "book" and v["refused"].get("cancel")):
                self.tried[k] = v["id"]
        s["tried"] = {k: self.tried.get(k) == v["id"] for k in v["trial"]}
        self.visits.append(s)
        self.visits = self.visits[-VISITS_KEEP:]
        self.write({"t": int(now), "visit": v["id"], "ship": v["ship"], "kind": "visit over", "summary": s})
        self._check = {"visit": v["id"], "ship": v["ship"], "booked": list(v.get("booked") or [])[:CHECK_BOOKINGS], "at": now}
        self.save_state()

    # ---------- sending, in the island bot's free slots ----------
    async def step(self, ask, gov) -> bool:
        """Called by the island bot when it has nothing to send. Sends at most one passenger transaction; True if it did."""
        if not self.enabled or not self.ready:
            return False
        now = self.clock()
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
        gap = 60 / RATE * (2 if state == "strained" else 1)
        if now - self.last_send < gap or not self.budget():
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
        if state == "strained":
            v["brake_half"] += 1
        v["done"].add(act["i"])
        self.last_send = now
        try:
            await self.send(v, act, ask, gov, state)
        except Exception as exc:   # one bad answer must not stop the ship or the bot
            log.warning("cruise %s %s failed: %r", v["id"], act["kind"], exc)
        self.save_state()
        return True

    def build(self, ship: str, act: dict, seq: int, tip: int, fee: int, rid: str | None = None) -> dict:
        from py_ecc.bls import G2Basic
        name = f"{ship}-{act['p']}"
        pk = self.pk[name]
        now = int(self.clock())
        env = {"sender_pubkey": pk, "sequence_number": seq, "expiration_time": now + 600, "expire_at_height": tip + 1000}
        k = act["kind"]
        if k == "pay":
            tx = {"tx_type": "user_tx", **env, "fee_limit": str(fee * 5), "operations": {"1": [[pk, PLACES[act["to"]], str(act["amount"])]]}}
        elif k == "bill":
            to = act["to"]
            tx = {"tx_type": "user_tx", **env, "fee_limit": str(fee * 5 * len(to)), "operations": {"1": [[pk, PLACES[pl], str(a)] for pl, a in to]}}
        elif k == "book":   # the transaction must expire before its release (DEADLINE_AFTER_RELEASE)
            env["expiration_time"] = min(env["expiration_time"], act["rel"] - 1)
            tx = {"tx_type": "retractable_transfer", **env, "fee_limit": str(fee * 5), "recipient_pubkey": PLACES[act["to"]],
                  "amount": int(act["amount"]), "release_at_time": int(act["rel"])}
        elif k == "cancel":   # feeless (docs/retractable.md); no use once the booking's time has come
            env["expiration_time"] = min(env["expiration_time"], act["rel"] - 1)
            env["expire_at_height"] = tip + 100
            tx = {"tx_type": "retract_transfer", **env, "fee_limit": "0", "retractable_id": rid}
        else:
            raise ValueError(k)
        tx["signature"] = G2Basic.Sign(self.sk[name], hashlib.sha256(signing_bytes(tx)).digest()).hex()
        return tx

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
        tx = await asyncio.to_thread(self.build, ship, act, seq, tip, base_fee(gov()), rid)
        res = await ask("sendtx " + json.dumps(tx, separators=(",", ":")))
        ok = bool(res) and res.get("status") == "ok" and (res.get("data") or {}).get("ok") is not False
        entry.update(seq=seq, height=tip, ok=ok, hash=((res or {}).get("data") or {}).get("tx_hash") if ok else None)
        if ok:
            v["sent"][act["kind"]] += 1
            self.spend()
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

    # ---------- what pages see ----------
    def brief(self, now: float | None = None) -> dict:
        """The ship in port or the next one, for the testnet load page and the game's chip."""
        now = self.clock() if now is None else now
        v = self.current(now)
        out: dict = {"enabled": bool(self.enabled), "simulated": True}
        if v:
            ph = self.phase(v, now)
            end = v["t0"] + VISIT_MIN * 60
            at = where(v["acts"], now, v["left"] or v["t0"] + (VISIT_MIN - BOARDING) * 60) if v["landed"] else {}
            out["now"] = {"visit": v["id"], "ship": v["ship"], "name": SHIPS[v["ship"]]["name"], "style": SHIPS[v["ship"]]["style"],
                          "phase": ph, "t0": v["t0"], "end": v["left"] or end, "passengers": SHIPS[v["ship"]]["passengers"],
                          "ashore": sum(at.values()), "at": at, "sent": v["sent"], "refused": sum(v["refused"].values()),
                          "skipped": v["skipped"], "planned": len(v["acts"]), "trial": v["trial"], "note": v["note"], "why": self.why(v),
                          "kinds": ["pay"] + list((v.get("allowed") or []) if v["landed"] else self.kinds_for(v["ship"])[1]),
                          "brake": "stopped" if v["left"] and v["note"].startswith("left") else "half" if self._verdict[1] == "strained" and v["landed"] else "none"}
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
        out["limits"] = {"per_min": RATE, "visit_max": VISIT_MAX, "trial_max": TRIAL_MAX, "log_days": LOG_DAYS}
        return out

    def route(self, path: str, query: str = "") -> dict | None:
        if path == "/cruise":
            return self.snapshot()
        if path == "/cruise/log":
            q = parse_qs(query or "")
            try:
                n = max(1, min(2000, int((q.get("n") or ["200"])[0])))
            except ValueError:
                n = 200
            vid = (q.get("visit") or [""])[0]
            rows = [] if vid and not VISIT_RE.match(vid) else [e for e in self.logbook if not vid or e.get("visit") == vid]
            return {"simulated": True, "days": LOG_DAYS, "entries": rows[-n:][::-1], "visits": [s["id"] for s in self.visits][::-1]}
        if path == "/cruise/incidents":
            return {"simulated": True, "incidents": self.incidents[::-1]}
        return None

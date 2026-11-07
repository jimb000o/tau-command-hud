"""The hack of the week, replayed: a real kind of attack from the news, played once a week on Tau Testnet Alpha against
a wallet safety setting, with our own simulated wallets. Every step is a real, paced test transaction; the logbook
says what each one did, and the alerts service posts the outcome (alerts/hack_crier.py).

The run: Thursday 11:00 German time (SLOT), never near a cruise ship's call (cruise.SHIPS: one ship at a time), only on a
calm or busy testnet (load.py verdict, waited for up to START_WAIT), about a dozen transactions in 40 minutes, at most
one every GAP seconds and only in the island bot's free slots (island.py idle, after the cruise ships).

The first hack is ADDRESS POISONING. The attacker makes an address that starts and ends like one the victim pays often,
sends the victim a tiny amount from it so it shows in the victim's history, and waits for the victim to copy the wrong
one. Four wallets, made here once (HACK_KEYS_PATH, mode 0600, never leave the server; balance 0 pays from the faucet):
  victim    pays with the take-back window on: a payment to an address it never paid goes out as a retractable
            transfer (tau-testnet docs/retractable.md) that waits WINDOW seconds in escrow, and can be taken back
  twin      the same person without the setting: plain payments
  friend    the address both pay every week
  poisoner  the lookalike: its address shows the same first 6 and last 4 characters as the friend's (the way wallets,
            explorers and our own pages shorten an address). The pair is found once, here, by trying keys in a
            separate low-priority process (grind); real attackers do the same with graphics cards
Steps (seconds after the start):
  habit       0  victim and twin each pay the friend 10 test AGRS: the payment the poisoner copies
  poison    120  the poisoner sends each of them 1 test AGRS: now the lookalike stands in their history
  slip      300  both copy the wrong address and pay 50: the victim's goes into escrow for WINDOW, the twin's arrives
  impostor  780  CHECK: the poisoner tries to take back the victim's payment itself; the chain must refuse it
                 (NOT_RETRACTABLE_SENDER: only the sender may retract)
  peek      840  CHECK: the payment is still open in escrow, not paid out before its time
  catch     900  the victim notices (the friend says nothing arrived) and takes it back: a feeless retract
  settle    release + 3 min: the victim's payment as the chain has it, and the twin's
Outcome: "held" (the payment came back), "missed" (it went to the poisoner after all: told honestly, with why),
"incomplete" (a step could not go out: no post, the owner is told), or "finding": the chain did something it must
not (CHECK failed, a payment released before its time, or one released although our retract was in an earlier block).
A finding is never shown or posted: the public sees "held back", the owner gets a private message with a ready issue
for IDNI (alerts/hack_crier.py reads /hack/held from inside the server), until `up hack release <run>`.

What it does NOT protect against is part of every post (HACKS "not"): the setting is the wallet's, not a chain rule.

GET /hack        the catalogue, the next run, the last runs (findings masked), the four wallets
GET /hack/held   only from inside the server: runs with a finding, in full
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
import secrets
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs

log = logging.getLogger("hackweek")

SLOT = (3, 11)              # Thursday (Monday 0), 11:00 German time
WINDOW = 30 * 60            # seconds a payment to a new address waits in escrow (the take-back window)
START_WAIT = 20 * 60        # the run waits this long for a calm testnet, then waits for next week
GAP = 20                    # seconds between two of our sends, at least (well below 12 a minute)
QUIET = 30                  # after a send our node did not answer: wait, then look whether it got through
TRIES = 3                   # sends of one step the node left unanswered before the step counts as failed
SHIP_CLEAR = 2 * 3600       # no run within this long of a cruise ship's call (before its approach, after its visit)
RETRACT_MARGIN = 6 * 60     # the take-back goes out this long before the release at the latest
SETTLE_AFTER = 3 * 60       # the outcome is read this long after the release
SETTLE_GIVE_UP = 6 * 3600
RUNS_KEEP = 12
TAG = (6, 4)                # characters an address is shortened to: first 6 … last 4
HABIT, DUST, SLIP = 10, 1, 50

HACKS = {
    "poisoning": {
        "name": "Address poisoning",
        "news": ("In May 2024 one wallet lost 1,155 WBTC, about $68 million, to a poisoned lookalike address (CoinDesk); "
                 "the attacker later returned almost all of it."),
        "how": ("The attacker makes an address that starts and ends like one you pay often, sends you a tiny amount from it, "
                "and waits for you to copy the wrong one from your history."),
        "rule": "take-back window",
        "rule_what": "Payments to an address you never paid wait 30 minutes in escrow and can be taken back.",
        "not": [
            "It only helps if you notice within the 30 minutes.",
            "It is a wallet setting, not a chain rule: whoever holds your key can pay without it.",
            "An address you paid once is not held again, so never send a lookalike a test payment.",
        ],
        "steps": [("habit", 0), ("habit_twin", 0), ("poison", 120), ("poison_twin", 120), ("slip", 300), ("slip_twin", 300),
                  ("impostor", 780), ("peek", 840), ("catch", 900)],
    },
}
NEEDED = ("habit", "poison", "slip", "catch")   # without these the replay says nothing


def short(pk: str) -> str:
    return f"{pk[:TAG[0]]}…{pk[-TAG[1]:]}" if pk else ""


def berlin_t(day: dt.date, hour: int) -> int:
    from cruise import berlin_t as bt
    return bt(day, hour)


def week_slot(now: float) -> int:
    """This week's run start (Monday to Sunday, German time); it may be past."""
    from cruise import berlin_day
    d = berlin_day(now)
    return berlin_t(d - dt.timedelta(days=d.weekday() - SLOT[0]), SLOT[1])


def next_slot(now: float) -> int:
    """The start of the run that is due or comes next."""
    t = week_slot(now)
    return t if now < t + START_WAIT else week_slot(now + 7 * 86400)


def ship_near(t: float) -> str | None:
    """The cruise ship whose call lies within SHIP_CLEAR of a run starting at t, if any."""
    from cruise import APPROACH, SHIPS, VISIT_MIN, calls_near
    for t0, k in calls_near(t - 86400, 3):
        if t0 - APPROACH * 60 - SHIP_CLEAR < t + 3600 and t < t0 + VISIT_MIN * 60 + SHIP_CLEAR:
            return SHIPS[k]["name"]
    return None


def run_id(t0: int, hack: str) -> str:
    from cruise import berlin_day
    return berlin_day(t0).isoformat() + "-" + hack


def hack_of(t0: int) -> str:
    """The hack a week replays: the catalogue in turn (one hack so far)."""
    keys = sorted(HACKS)
    return keys[(t0 // (7 * 86400)) % len(keys)]


# ---------- the lookalike pair, found once ----------
def tag_of(pk_hex: str) -> int:
    return int(pk_hex[:TAG[0]] + pk_hex[-TAG[1]:], 16)


def grind(limit: int = 3_000_000, tag=tag_of) -> tuple[int, int] | None:
    """Two keys whose addresses show the same first and last characters: consecutive secret keys, each public key one
    point addition from the last, until two tags meet (about a million keys for 6 + 4 hex characters)."""
    from py_ecc.bls.point_compression import compress_G1
    from py_ecc.optimized_bls12_381 import G1, add, multiply
    from py_ecc.optimized_bls12_381 import curve_order as R
    s = secrets.randbelow(R - limit - 2) + 1
    P = multiply(G1, s)
    seen: dict[int, int] = {}
    for i in range(limit):
        t = tag(format(compress_G1(P), "096x"))
        if t in seen:
            return s + seen[t], s + i
        seen[t] = i
        P = add(P, G1)
    return None


def make_keys(path: str) -> None:
    """The four wallets, written once (0600). Runs as its own process: the search takes minutes of pure Python."""
    from py_ecc.bls import G2Basic
    pair = grind()
    if not pair:
        raise SystemExit("no lookalike pair found")
    keys = {}
    for name, sk in (("friend", pair[0]), ("poisoner", pair[1]), ("victim", None), ("twin", None)):
        if sk is None:
            sk = G2Basic.KeyGen(secrets.token_bytes(32))
            sk = sk if isinstance(sk, int) else int.from_bytes(bytes(sk), "big")
        keys[name] = {"sk": sk.to_bytes(32, "big").hex(), "pk": G2Basic.SkToPk(sk).hex()}
    assert short(keys["friend"]["pk"]) == short(keys["poisoner"]["pk"]) and keys["friend"]["pk"] != keys["poisoner"]["pk"]
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(keys, f)
    os.replace(tmp, path)


class HackWeek:
    def __init__(self, keys_path: str | None = None, state_path: str | None = None, clock=time.time,
                 enabled: bool | None = None, verdict=None, background: bool = True, keys: dict | None = None):
        data = os.environ.get("CRUISE_DATA", "/data")
        self.keys_path = keys_path or os.environ.get("HACK_KEYS_PATH", os.path.join(data, "hack.keys"))
        self.state_path = state_path or os.environ.get("HACK_STATE_PATH", os.path.join(data, "hack-state.json"))
        self.released_path = os.path.join(os.path.dirname(self.state_path) or ".", "hack-released.json")
        self.enabled = (os.environ.get("HACK_ENABLED", "1") != "0") if enabled is None else enabled
        self.clock = clock
        self.verdict_fn = verdict or (lambda: None)
        self.on_tx = None
        self.on_ready = None
        self.sk: dict[str, int] = {}
        self.pk: dict[str, str] = {}
        self.who: dict[str, str] = {}
        self.ready = False
        self.runs: list[dict] = []
        self.last_send = 0.0
        self.hold_until = 0.0
        self.making = False
        self.load_state()
        if keys:
            self.use_keys(keys)
        elif self.enabled:
            if background:
                threading.Thread(target=self._keys, daemon=True).start()
            else:
                self._keys()

    # ---------- wallets ----------
    def _keys(self):
        try:
            if not os.path.exists(self.keys_path):
                if not os.access(os.path.dirname(os.path.abspath(self.keys_path)), os.W_OK):
                    raise OSError("no place to keep the wallets: " + self.keys_path)
                self.making = True
                log.info("hack of the week: looking for a lookalike address pair (a few minutes, low priority)")
                subprocess.run([sys.executable, os.path.abspath(__file__), "keys", self.keys_path], check=True,
                               preexec_fn=lambda: os.nice(19), timeout=6 * 3600)
            with open(self.keys_path) as f:
                self.use_keys(json.load(f))
        except Exception as exc:   # the relay keeps working without it
            log.warning("hack of the week off: %r", exc)
            self.enabled = False
        finally:
            self.making = False

    def use_keys(self, keys: dict):
        self.sk = {n: int(k["sk"], 16) for n, k in keys.items()}
        self.pk = {n: k["pk"] for n, k in keys.items()}
        self.who = {pk: "hack" for pk in self.pk.values()}
        self.ready = True
        if self.on_ready:
            try:
                self.on_ready()
            except Exception as exc:
                log.warning("hack: on_ready failed: %r", exc)

    # ---------- state ----------
    def load_state(self):
        try:
            with open(self.state_path) as f:
                self.runs = [r for r in (json.load(f).get("runs") or []) if isinstance(r, dict)][-RUNS_KEEP:]
        except (OSError, ValueError, TypeError, AttributeError):
            self.runs = []

    def save_state(self):
        try:
            tmp = self.state_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"runs": self.runs[-RUNS_KEEP:]}, f, separators=(",", ":"))
            os.replace(tmp, self.state_path)
        except OSError as exc:
            log.warning("cannot write %s: %r", self.state_path, exc)

    def run_of(self, rid: str) -> dict | None:
        return next((r for r in self.runs if r["id"] == rid), None)

    def note(self, r: dict, text: str):
        r.setdefault("log", []).append({"t": int(self.clock()), "note": text})
        log.info("hack %s: %s", r["id"], text)

    # ---------- the transactions ----------
    def build(self, who: str, kind: str, seq: int, tip: int, fee: int, to: str | None = None, amount: int = 0,
              rel: int | None = None, rid: str | None = None) -> dict:
        from py_ecc.bls import G2Basic
        from cruise import signing_bytes
        pk = self.pk[who]
        now = int(self.clock())
        env = {"sender_pubkey": pk, "sequence_number": seq, "expiration_time": now + 600, "expire_at_height": tip + 1000}
        if kind == "pay":
            tx = {"tx_type": "user_tx", **env, "fee_limit": str(fee * 5), "operations": {"1": [[pk, self.pk[to], str(amount)]]}}
        elif kind == "park":   # must expire before its release (DEADLINE_AFTER_RELEASE)
            env["expiration_time"] = min(env["expiration_time"], rel - 1)
            tx = {"tx_type": "retractable_transfer", **env, "fee_limit": str(fee * 5), "recipient_pubkey": self.pk[to],
                  "amount": int(amount), "release_at_time": int(rel)}
        elif kind == "retract":   # feeless (docs/retractable.md)
            env["expiration_time"] = min(env["expiration_time"], (rel or now + 600) - 1)
            env["expire_at_height"] = tip + 100
            tx = {"tx_type": "retract_transfer", **env, "fee_limit": "0", "retractable_id": rid}
        else:
            raise ValueError(kind)
        tx["signature"] = G2Basic.Sign(self.sk[who], hashlib.sha256(signing_bytes(tx)).digest()).hex()
        return tx

    def plan_of(self, r: dict, step: str) -> tuple[str, str, dict] | None:
        """(sender, kind, fields) of a step's transaction; None for a step that sends nothing."""
        p = r.get("park") or {}
        return {
            "habit": ("victim", "pay", {"to": "friend", "amount": HABIT}),
            "habit_twin": ("twin", "pay", {"to": "friend", "amount": HABIT}),
            "poison": ("poisoner", "pay", {"to": "victim", "amount": DUST}),
            "poison_twin": ("poisoner", "pay", {"to": "twin", "amount": DUST}),
            "slip": ("victim", "park", {"to": "poisoner", "amount": SLIP}),
            "slip_twin": ("twin", "pay", {"to": "poisoner", "amount": SLIP}),
            "impostor": ("poisoner", "retract", {"rid": p.get("rid"), "rel": p.get("release_at")}),
            "catch": ("victim", "retract", {"rid": p.get("rid"), "rel": p.get("release_at")}),
        }.get(step)

    async def park_id(self, r: dict, ask) -> str | None:
        """The victim's payment to the poisoner as the node lists it, once it is in a block."""
        p = r.get("park") or {}
        if p.get("rid"):
            return p["rid"]
        res = await ask(f"getretractables {self.pk['victim']} out")
        if not res or res.get("status") != "ok":
            return None
        for e in (res.get("data") or {}).get("retractables") or []:
            if str(e.get("recipient_pubkey", "")).lower() == self.pk["poisoner"] and int(e.get("release_at_time") or 0) == int(p.get("release_at") or -1):
                p["rid"] = str(e.get("retractable_id") or "") or None
                return p["rid"]
        return None

    async def status_of(self, rid: str, ask) -> tuple[str | None, int | None]:
        res = await ask(f"getretractable {rid}")
        d = (res or {}).get("data") or {}
        st = d.get("status")
        return (st if st in ("open", "released", "retracted") else None), d.get("resolved_at_height")

    def finding(self, r: dict, what: str, extra: dict | None = None):
        r.setdefault("findings", []).append({"t": int(self.clock()), "what": what, **(extra or {})})
        self.note(r, "FINDING: " + what)

    async def send_step(self, r: dict, step: str, ask, gov) -> bool:
        """One step's transaction; True when something went out (the pace counts it)."""
        import asyncio
        from cruise import Cruise
        from island import base_fee
        s = r["steps"].setdefault(step, {})
        who, kind, f = self.plan_of(r, step)
        if kind == "retract" and not f.get("rid"):
            rid = await self.park_id(r, ask)
            if not rid:
                s["wait"] = int(self.clock()) + QUIET
                s["looked"] = s.get("looked", 0) + 1
                return False
            f["rid"] = rid
        st = await ask(f"getsequence {self.pk[who]}")
        if not st or st.get("status") != "ok":
            s["wait"] = int(self.clock()) + QUIET
            return False
        d = st.get("data") or {}
        seq, tip = int(d.get("sequence_number") or 0), int(d.get("tip_height") or 0)
        if s.get("seq") is not None and seq > s["seq"]:   # the unanswered send reached the node after all
            s.update(ok=True, done=True, note="the node took it after all (the sequence moved on)")
            return False
        rel = None
        if kind == "park":
            rel = int(self.clock()) + WINDOW
            r["park"] = {"release_at": rel}
        tx = await asyncio.to_thread(self.build, who, kind, seq, tip, base_fee(gov()), f.get("to"), f.get("amount", 0),
                                     rel or f.get("rel"), f.get("rid"))
        t = time.monotonic()
        res = await ask("sendtx " + json.dumps(tx, separators=(",", ":")))
        s.update(t=int(self.clock()), ms=int((time.monotonic() - t) * 1000), seq=seq, height=tip, tx=tx)
        if res is None:
            s["tries"] = s.get("tries", 0) + 1
            self.hold_until = self.clock() + QUIET
            s["wait"] = int(self.clock()) + QUIET
            if s["tries"] >= TRIES:
                s.update(done=True, ok=None, note=f"our node did not answer {TRIES} times")
            return True
        ok = res.get("status") == "ok" and (res.get("data") or {}).get("ok") is not False
        h = (res.get("data") or {}).get("tx_hash") if ok else None
        s.update(done=True, ok=ok, hash=h)
        if kind == "park" and ok:
            r["park"]["hash"] = h
        if not ok:
            s["code"] = Cruise.code_of(res)
            err = res.get("error") or res
            s["err"] = (err if isinstance(err, str) else json.dumps(err, separators=(",", ":")))[:300]
        if step == "impostor":
            s["expect"] = "NOT_RETRACTABLE_SENDER"
            if ok:
                self.finding(r, "the chain took a take-back from a wallet that did not send the payment",
                             {"step": step, "tx": tx, "answer": res})
            else:
                s["right"] = s["code"] == "NOT_RETRACTABLE_SENDER"
        elif not ok:
            self.note(r, f"{step} refused: {s['err'][:120]}")
        self.on_tx and self.on_tx(ok)
        return True

    # ---------- the run ----------
    def due(self, now: float) -> dict | None:
        """The run under way, or this week's when its time has come (made once)."""
        t0 = week_slot(now)
        rid = run_id(t0, hack_of(t0))
        r = self.run_of(rid)
        if r is None and t0 <= now < t0 + START_WAIT:
            r = {"id": rid, "hack": hack_of(t0), "t0": t0, "status": "waiting", "steps": {}, "result": None}
            self.runs.append(r)
            self.runs = self.runs[-RUNS_KEEP:]
            ship = ship_near(t0)
            if ship:
                r.update(status="done", result="skipped", why=f"{ship} calls near this time: one ship at a time")
                self.note(r, r["why"])
            self.save_state()
        return r if r and r["status"] != "done" else next((x for x in self.runs if x["status"] != "done"), None)

    async def step(self, ask, gov) -> bool:
        """Called in the island bot's free slots (after the cruise ships). Sends at most one transaction; True if it did."""
        if not self.enabled or not self.ready:
            return False
        now = self.clock()
        r = self.due(now)
        if not r:
            return False
        if r["status"] == "waiting":
            v = self.verdict_fn()
            if v in ("calm", "busy"):
                r.update(status="running", started=int(now), verdict=v)
                self.note(r, f"started on a {v} testnet")
                self.save_state()
            elif now >= r["t0"] + START_WAIT:
                r.update(status="done", result="skipped", why="the testnet was not calm enough to start; next week again")
                self.note(r, r["why"])
                self.save_state()
                return False
            else:
                return False
        if r["status"] == "running":
            sent = await self.advance(r, ask, gov, now)
            self.save_state()
            return sent
        if r["status"] == "settling" and now >= r.get("settle_at", 0):
            await self.settle(r, ask, now)
            self.save_state()
        return False

    async def advance(self, r: dict, ask, gov, now: float) -> bool:
        base = r["started"]
        steps = HACKS[r["hack"]]["steps"]
        rel = (r.get("park") or {}).get("release_at")
        for name, off in steps:
            s = r["steps"].setdefault(name, {})
            if s.get("done"):
                continue
            if now < base + off or now < s.get("wait", 0):
                return False
            if name in ("impostor", "peek", "catch") and not (r["steps"].get("slip") or {}).get("ok"):
                s.update(done=True, ok=None, note="no payment in escrow to work with")
                continue
            late = rel and now >= rel - RETRACT_MARGIN
            if name in ("impostor", "peek") and (late or s.get("looked", 0) >= 6):
                s.update(done=True, ok=None, note="the payment was not in a block in time for this check")
                continue
            if name == "catch" and late:
                s.update(done=True, ok=None, note="too close to the release for a take-back with margin")
                continue
            if name == "peek":
                rid = await self.park_id(r, ask)
                if not rid:
                    s["wait"], s["looked"] = int(now) + QUIET, s.get("looked", 0) + 1
                    return False
                st, _ = await self.status_of(rid, ask)
                s.update(done=True, status=st, t=int(now), ok=st == "open")
                if st == "released":
                    self.finding(r, "the payment was paid out of escrow before its release time",
                                 {"step": name, "retractable_id": rid, "release_at_time": rel})
                continue
            if now < self.hold_until or now - self.last_send < GAP:
                return False
            sent = await self.send_step(r, name, ask, gov)
            if sent:
                self.last_send = now
            return sent
        r["status"] = "settling"
        r["settle_at"] = int((rel or now) + SETTLE_AFTER)
        self.note(r, "every step done; the outcome is read after the release")
        return False

    async def settle(self, r: dict, ask, now: float):
        out: dict = {}
        rid = await self.park_id(r, ask) if (r["steps"].get("slip") or {}).get("ok") else None
        if rid:
            st, at = await self.status_of(rid, ask)
            if st in (None, "open") and now < r["settle_at"] + SETTLE_GIVE_UP:
                r["settle_at"] = int(now + 600)
                return
            out["victim"] = {"status": st, "resolved_at_height": at}
            c = r["steps"].get("catch") or {}
            if st == "released" and c.get("hash"):
                res = await ask(f"gettxstatus {c['hash']}")
                d = (res or {}).get("data") or {}
                b = d.get("block_number")
                out["catch_block"] = b
                if d.get("status") == "confirmed" and at is not None and b is not None and int(b) < int(at):
                    self.finding(r, "the payment was paid out although our take-back was in an earlier block",
                                 {"retractable_id": rid, "catch_block": b, "released_at_height": at})
        tw = r["steps"].get("slip_twin") or {}
        if tw.get("hash"):
            res = await ask(f"gettxstatus {tw['hash']}")
            out["twin"] = ((res or {}).get("data") or {}).get("status")
        r["outcome"] = out
        missing = [k for k in NEEDED if not (r["steps"].get(k) or {}).get("ok")]
        if r.get("findings"):
            res, why = "finding", r["findings"][0]["what"]
        elif missing:
            res, why = "incomplete", "these steps did not go through: " + ", ".join(missing)
        elif (out.get("victim") or {}).get("status") == "retracted":
            res, why = "held", "the payment came back to the victim"
        elif (out.get("victim") or {}).get("status") == "released":
            res, why = "missed", "the take-back was not in a block before the release, so the poisoner was paid"
        else:
            res, why = "incomplete", "the chain did not tell what became of the payment"
        r.update(status="done", result=res, why=why, settled=int(now))
        self.note(r, f"outcome: {res} ({why})")

    # ---------- what pages see ----------
    def released(self) -> set:
        try:
            with open(self.released_path) as f:
                return {str(x) for x in json.load(f)}
        except (OSError, ValueError, TypeError):
            return set()

    def public(self, r: dict) -> dict:
        r = {k: v for k, v in r.items() if k != "log"}
        if r.get("findings") and r["id"] not in self.released():
            return {k: r.get(k) for k in ("id", "hack", "t0", "status")} | {
                "result": "held back", "held": True,
                "why": "held back: a finding, reported privately to the team behind the testnet first"}
        return r

    def snapshot(self) -> dict:
        now = self.clock()
        t = next_slot(now)
        return {"simulated": True, "enabled": bool(self.enabled), "ready": self.ready, "making_wallets": self.making,
                "slot": {"weekday": SLOT[0], "time": f"{SLOT[1]:02d}:00", "zone": "Europe/Berlin"},
                "next": {"t0": t, "hack": hack_of(t), "ship_near": ship_near(t)},
                "hacks": {k: {x: v[x] for x in ("name", "news", "how", "rule", "rule_what", "not")} for k, v in HACKS.items()},
                "window_minutes": WINDOW // 60,
                "wallets": {k: {"address": v, "short": short(v)} for k, v in self.pk.items()},
                "runs": [self.public(r) for r in self.runs[::-1]]}

    def held(self) -> dict:
        rel = self.released()
        return {"simulated": True, "released": sorted(rel), "runs": [r for r in self.runs[::-1] if r.get("findings")],
                "wallets": dict(self.pk)}

    def route(self, path: str, query: str = "", internal: bool = False) -> dict | None:
        if path == "/hack":
            q = parse_qs(query or "")
            snap = self.snapshot()
            if (q.get("run") or [""])[0]:
                snap["runs"] = [x for x in snap["runs"] if x["id"] == q["run"][0]]
            return snap
        if path == "/hack/held":
            return self.held() if internal else {"error": "only from inside the server"}
        return None


if __name__ == "__main__":
    if sys.argv[1:2] == ["keys"] and len(sys.argv) > 2:
        logging.basicConfig(level=logging.INFO)
        make_keys(sys.argv[2])
        sys.exit(0)
    print(__doc__)
    sys.exit(2)

"""Three showcase wallets on Tau Testnet Alpha, each with one personal rule (an o5 clause) that the HUD reads in words,
and once a day each one deliberately tries a payment its own rule forbids, so the HUD's feed shows "Stopped by the
sender's own rule" with a real refusal from the node.

  piggy     Tau HUD's piggy bank: cannot send anything until New Year (1 January, 00:00 German time). A time-lock on
            i5, the block time: a clause may not read the block height (i6), so the lock is by the clock.
            Daily try: 10 test AGRS to the feeding fund.
  foureyes  Tau HUD's four-eyes wallet: above COSIGN_ABOVE test AGRS a payment needs a second signature from Tau
            HUD's co-signer (approval slot i18, tau-testnet docs/approvals.md), and so does EVERY payment once the
            balance (i2) is below FLOOR: many small payments cannot empty it. Daily try: 250 to the piggy bank as a
            plain payment, without the co-signer's vote.
  feeding   Tau HUD's Agorzilla feeding fund: may only pay Agorzilla's bowl (i4, the recipient), at most MEAL_MAX
            a payment (i1), and nothing once the balance (i2) is below FLOOR. Daily try: 5 test AGRS to the piggy
            bank instead.
  cosigner  Tau HUD's co-signer: never sends; it is the second signature the four-eyes wallet names.

The keys are made here once (SHOWCASE_KEYS_PATH, mode 0600, they never leave the server). The faucet funds each wallet
at its first transaction, which is the rule itself. Every RECHECK seconds (and right after a testnet restart) the relay
asks the node which rule each wallet has in force (getruleoffers): a wallet without its rule, a new chain included, gets
it again. The daily try goes out only while the rule is in force. A refused transaction never enters a block, so it
costs nothing: no fee, no sequence number used. The node's refusal is handed to the relay (on_refused), which lists it
with the dropped transactions of GET /stats, where the HUD's feed reads them; nothing else in this module reaches a page.

A try the node TOOK is the opposite of the point: it is kept as a finding (the rule did not hold) and never retried
that day. After New Year the piggy bank's lock has opened by itself: its try stops, its rule stays as it is.

Paced like the hack of the week: in the island bot's free slots, at most one transaction every GAP seconds.

GET /showcase   the four wallets with their names, each rule in words and whether it is in force, the last tries
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
import secrets
import time

log = logging.getLogger("showcase")

BOWL = "947c2b8988769f9fb7ada19021e27c51f5d855e4e05ad258d2ca2322821987dbff93e0425f281edded5c372b97e6a108"
COSIGN_ABOVE = 100
FLOOR = 90_000        # below this balance (i2, the balance at the parent block) the small-payment way is closed: many
                      # payments under a limit cannot empty the wallet (a daily limit needs IDNI's i16, switched off)
MEAL_MAX = 20         # the feeding fund pays Agorzilla's bowl at most this much per payment
GAP = 20              # seconds between two of our sends, at least
RECHECK = 30 * 60     # how often each wallet's rule is looked up on the node
LOOK_GAP = 10         # seconds between two lookups (getruleoffers is costly for the node)
RULE_WAIT = 10 * 60   # a rule sent and not yet in force: wait this long before sending it again
QUIET = 60            # after a send the node did not answer: wait this long
TRIES_PER_DAY = 3     # unanswered tries of one wallet before its day is given up
LOG_KEEP = 40

BLOCK = "(o5[t]:bv[24] = { #x000000 }:bv[24])"
ALLOW = "(o5[t]:bv[24] = { #x000001 }:bv[24])"

# name, German hour of the daily try, the try (to, amount), what the try is, in words
WALLETS = {
    "piggy": {"name": "Tau HUD's piggy bank", "at": 11, "to": "feeding", "amount": 10},
    "foureyes": {"name": "Tau HUD's four-eyes wallet", "at": 15, "to": "piggy", "amount": 250},
    "feeding": {"name": "Tau HUD's Agorzilla feeding fund", "at": 19, "to": "piggy", "amount": 5},
}
COSIGNER = {"name": "Tau HUD's co-signer"}


def berlin_t(day: dt.date, hour: int) -> int:
    from cruise import berlin_t as bt
    return bt(day, hour)


def berlin_day(t: float) -> dt.date:
    from cruise import berlin_day as bd
    return bd(t)


def piggy_until() -> int:
    """When the piggy bank opens: SHOWCASE_PIGGY_UNTIL (unix seconds) or New Year 2027, 00:00 German time."""
    v = os.environ.get("SHOWCASE_PIGGY_UNTIL", "").strip()
    return int(v) if v.isdigit() else berlin_t(dt.date(2027, 1, 1), 0)


def norm(body: str) -> str:
    """A rule's text compared without spaces (the node may space it differently)."""
    return "".join(str(body or "").split()).lower()


def make_keys(path: str) -> dict:
    from py_ecc.bls import G2Basic
    keys = {}
    for name in (*WALLETS, "cosigner"):
        sk = G2Basic.KeyGen(secrets.token_bytes(32))
        sk = sk if isinstance(sk, int) else int.from_bytes(bytes(sk), "big")
        keys[name] = {"sk": sk.to_bytes(32, "big").hex(), "pk": G2Basic.SkToPk(sk).hex()}
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(keys, f)
    os.replace(tmp, path)
    return keys


class Showcase:
    def __init__(self, keys_path: str | None = None, state_path: str | None = None, clock=time.time,
                 enabled: bool | None = None, keys: dict | None = None):
        data = os.environ.get("CRUISE_DATA", "/data")
        self.keys_path = keys_path or os.environ.get("SHOWCASE_KEYS_PATH", os.path.join(data, "showcase.keys"))
        self.state_path = state_path or os.environ.get("SHOWCASE_STATE_PATH", os.path.join(data, "showcase-state.json"))
        self.enabled = (os.environ.get("SHOWCASE_ENABLED", "1") != "0") if enabled is None else enabled
        self.clock = clock
        self.on_tx = None        # (ok) for the load page
        self.on_refused = None   # (entry) the relay lists it with the dropped transactions of /stats
        self.on_ready = None
        self.sk: dict[str, int] = {}
        self.pk: dict[str, str] = {}
        self.who: dict[str, str] = {}
        self.ready = False
        self.last_send = 0.0
        self.last_look = 0.0
        self.hold_until = 0.0
        self.st: dict = {"wallets": {}, "log": []}
        self.load_state()
        if not self.enabled:
            return
        try:
            if keys is None:
                if os.path.exists(self.keys_path):
                    with open(self.keys_path) as f:
                        keys = json.load(f)
                else:
                    keys = make_keys(self.keys_path)
            self.use_keys(keys)
        except Exception as exc:   # the relay keeps working without it
            log.warning("showcase off: %r", exc)
            self.enabled = False

    def use_keys(self, keys: dict):
        self.sk = {n: int(k["sk"], 16) for n, k in keys.items()}
        self.pk = {n: k["pk"].lower() for n, k in keys.items()}
        self.who = {pk: "showcase" for pk in self.pk.values()}
        self.ready = all(n in self.pk for n in (*WALLETS, "cosigner"))
        if self.ready and self.on_ready:
            try:
                self.on_ready()
            except Exception as exc:
                log.warning("showcase: on_ready failed: %r", exc)

    # ---------- state ----------
    def load_state(self):
        try:
            with open(self.state_path) as f:
                st = json.load(f)
            if isinstance(st, dict) and isinstance(st.get("wallets"), dict):
                self.st = {"wallets": st["wallets"], "log": [x for x in st.get("log") or [] if isinstance(x, dict)][-LOG_KEEP:]}
        except (OSError, ValueError, TypeError):
            pass

    def save_state(self):
        try:
            tmp = self.state_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.st, f, separators=(",", ":"))
            os.replace(tmp, self.state_path)
        except OSError as exc:
            log.warning("cannot write %s: %r", self.state_path, exc)

    def w(self, name: str) -> dict:
        return self.st["wallets"].setdefault(name, {})

    def note(self, name: str, text: str, **extra):
        self.st["log"].append({"t": int(self.clock()), "wallet": name, "note": text, **extra})
        self.st["log"] = self.st["log"][-LOG_KEEP:]
        log.info("showcase %s: %s", name, text)

    def recheck(self):
        """The testnet restarted (or the relay saw another chain): look at every rule again right away."""
        for name in WALLETS:
            self.w(name)["checked"] = 0
            self.w(name)["in_force"] = False

    # ---------- the rules ----------
    def rule(self, name: str) -> str:
        return f"always ( {self.body(name)} )."

    def body(self, name: str) -> str:
        if name == "piggy":
            body = f"(i5[t]:bv[64] < {{ {piggy_until()} }}:bv[64]) ? {BLOCK} : {ALLOW}"
        elif name == "foureyes":
            body = (f"((i1[t]:bv[24] > {{ #x{COSIGN_ABOVE:06x} }}:bv[24] || i2[t]:bv[24] < {{ #x{FLOOR:06x} }}:bv[24])"
                    f" && !(i18[t]:bv[384] = {{ #x{self.pk['cosigner']} }}:bv[384])) ? {BLOCK} : {ALLOW}")
        elif name == "feeding":
            body = (f"(i4[t]:bv[384] = {{ #x{BOWL} }}:bv[384] && !(i1[t]:bv[24] > {{ #x{MEAL_MAX:06x} }}:bv[24])"
                    f" && !(i2[t]:bv[24] < {{ #x{FLOOR:06x} }}:bv[24])) ? {ALLOW} : {BLOCK}")
        else:
            raise ValueError(name)
        return body

    def words(self, name: str) -> str:
        if name == "piggy":
            return "cannot send anything until New Year (1 January, 00:00 German time)"
        if name == "foureyes":
            return (f"needs a second signature from {COSIGNER['name']} above {COSIGN_ABOVE} test AGRS, "
                    f"and for every payment once it holds less than {FLOOR:,}")
        return f"may only pay Agorzilla's bowl, at most {MEAL_MAX} test AGRS a meal, and nothing once it holds less than {FLOOR:,}"

    def try_words(self, name: str) -> str:
        c = WALLETS[name]
        to = WALLETS[c["to"]]["name"]
        if name == "piggy":
            return f"{c['amount']} test AGRS to {to} before New Year"
        if name == "foureyes":
            return f"{c['amount']} test AGRS to {to} without the co-signer's signature"
        return f"{c['amount']} test AGRS to {to}, not to Agorzilla's bowl"

    def opened(self, name: str, now: float) -> bool:
        """The piggy bank's lock has opened by itself: no more tries."""
        return name == "piggy" and now >= piggy_until()

    async def look(self, name: str, ask) -> None:
        """Ask the node which o5 rule the wallet has in force now."""
        res = await ask(f"getruleoffers {self.pk[name]} all")
        if not res or res.get("status") != "ok":
            return
        d = res.get("data") or {}
        body = None
        for c in d.get("accepted_clauses") or []:
            if isinstance(c, dict) and str(c.get("target_stream", "")).lstrip("o") == "5" and c.get("clause_body"):
                body = c["clause_body"]
        inner = self.body(name)
        want = {norm(self.rule(name)), norm(inner), norm(f"({inner})")}
        w = self.w(name)
        was = w.get("in_force")
        w["checked"] = int(self.clock())
        w["in_force"] = bool(body) and norm(body) in want
        if w["in_force"] and not was:
            self.note(name, "rule in force: " + self.words(name))
            w.pop("sent_rule", None)

    # ---------- the transactions ----------
    def build(self, name: str, seq: int, tip: int, fee: int, rule: str | None = None, to: str | None = None,
              amount: int = 0) -> dict:
        from py_ecc.bls import G2Basic
        from cruise import signing_bytes
        pk = self.pk[name]
        now = int(self.clock())
        ops = {"0": rule} if rule is not None else {"1": [[pk, to, str(amount)]]}
        tx = {"tx_type": "user_tx", "sender_pubkey": pk, "sequence_number": seq, "expiration_time": now + 600,
              "expire_at_height": tip + 1000, "fee_limit": str(fee * 5), "operations": ops}
        tx["signature"] = G2Basic.Sign(self.sk[name], hashlib.sha256(signing_bytes(tx)).digest()).hex()
        return tx

    async def send(self, name: str, ask, gov, **kw):
        """(answer or None, the transaction)."""
        import asyncio
        from island import base_fee
        st = await ask(f"getsequence {self.pk[name]}")
        if not st or st.get("status") != "ok":
            return None, None
        d = st.get("data") or {}
        seq, tip = int(d.get("sequence_number") or 0), int(d.get("tip_height") or 0)
        tx = await asyncio.to_thread(self.build, name, seq, tip, base_fee(gov()), **kw)
        res = await ask("sendtx " + json.dumps(tx, separators=(",", ":")))
        self.last_send = self.clock()
        if res is None:
            self.hold_until = self.clock() + QUIET
        return res, tx

    @staticmethod
    def took(res) -> bool:
        return isinstance(res, dict) and res.get("status") == "ok" and (res.get("data") or {}).get("ok") is not False

    @staticmethod
    def said(res) -> str:
        err = (res or {}).get("error") or (res or {}).get("data") or res
        if isinstance(err, dict):
            err = err.get("message") or json.dumps(err, separators=(",", ":"))
        return str(err)[:400]

    async def set_rule(self, name: str, ask, gov) -> bool:
        res, tx = await self.send(name, ask, gov, rule=self.rule(name))
        if res is None:
            return tx is not None
        w = self.w(name)
        if self.took(res):
            w["rule_tx"] = (res.get("data") or {}).get("tx_hash")
            self.note(name, "rule sent: " + self.words(name))
            w["checked"] = int(self.clock()) - RECHECK + RULE_WAIT // 2   # look again in about five minutes
        else:
            self.note(name, "the node refused the rule: " + self.said(res))
        w["sent_rule"] = int(self.clock())   # no second attempt within RULE_WAIT
        self.on_tx and self.on_tx(self.took(res))
        return True

    async def try_forbidden(self, name: str, ask, gov, day: str) -> bool:
        c = WALLETS[name]
        w = self.w(name)
        res, tx = await self.send(name, ask, gov, to=self.pk[c["to"]], amount=c["amount"])
        if tx is None:
            return False
        if res is None:
            w["tries"] = w.get("tries", 0) + 1
            if w["tries"] >= TRIES_PER_DAY:
                w["tried"] = day
                self.note(name, f"daily try given up: our node did not answer {TRIES_PER_DAY} times")
            return True
        w["tried"], w["tries"] = day, 0
        now = int(self.clock())
        h = hashlib.sha256(json.dumps(tx, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if self.took(res):
            w["last"] = {"t": now, "outcome": "took", "what": self.try_words(name), "tx": (res.get("data") or {}).get("tx_hash")}
            self.note(name, "FINDING: the node took a payment the wallet's own rule forbids: " + self.try_words(name),
                      answer=res)
        else:
            said = self.said(res)
            own = "own policy" in said or "o5" in said
            w["last"] = {"t": now, "outcome": "stopped" if own else "refused", "what": self.try_words(name), "node_said": said}
            self.note(name, ("stopped by its own rule: " if own else "refused for another reason: ") + self.try_words(name))
            if own and self.on_refused:
                self.on_refused({"tx_hash": h, "type": "user_tx", "sender": self.pk[name], "seen": now, "left": now,
                                 "reason": f"o5 = 0 · its own rule said no: {self.try_words(name)} (a daily test of the rule)",
                                 "showcase": name})
        self.on_tx and self.on_tx(self.took(res))
        return True

    # ---------- the loop ----------
    async def step(self, ask, gov) -> bool:
        """Called in the island bot's free slots. Sends at most one transaction; True if it did."""
        if not self.enabled or not self.ready:
            return False
        now = self.clock()
        if now < self.hold_until:
            return False
        # 1. look up a rule that was not looked at for a while (one lookup at a time, spaced)
        if now - self.last_look >= LOOK_GAP:
            for name in WALLETS:
                if now - self.w(name).get("checked", 0) >= RECHECK:
                    self.last_look = now
                    await self.look(name, ask)
                    self.save_state()
                    return False
        if now - self.last_send < GAP:
            return False
        day = berlin_day(now).isoformat()
        for name, c in WALLETS.items():
            w = self.w(name)
            if not w.get("checked"):
                continue
            # 2. a wallet without its rule gets it (a new chain included); after New Year the piggy bank is left open
            if not w.get("in_force"):
                if self.opened(name, now) or now - w.get("sent_rule", 0) < RULE_WAIT:
                    continue
                sent = await self.set_rule(name, ask, gov)
                self.save_state()
                return sent
            # 3. the daily try, from its German hour on
            if w.get("tried") == day or self.opened(name, now) or now < berlin_t(berlin_day(now), c["at"]):
                continue
            sent = await self.try_forbidden(name, ask, gov, day)
            self.save_state()
            return sent
        return False

    # ---------- GET /showcase ----------
    def snapshot(self) -> dict:
        if not self.ready:
            return {"enabled": self.enabled, "ready": False}
        out = {}
        for name, c in WALLETS.items():
            w = self.w(name)
            out[name] = {"pk": self.pk[name], "name": c["name"], "rule": self.words(name), "rule_text": self.rule(name),
                         "in_force": bool(w.get("in_force")), "checked": w.get("checked") or None,
                         "daily_try": {"german_hour": c["at"], "what": self.try_words(name),
                                       "stopped": self.opened(name, self.clock())},
                         "last_try": w.get("last")}
        return {"enabled": self.enabled, "ready": True, "wallets": out,
                "cosigner": {"pk": self.pk["cosigner"], "name": COSIGNER["name"]},
                "piggy_until": piggy_until(),
                "log": [{k: v for k, v in x.items() if k != "answer"} for x in self.st["log"][-20:]]}

    def route(self, path: str) -> dict | None:
        return self.snapshot() if path == "/showcase" else None

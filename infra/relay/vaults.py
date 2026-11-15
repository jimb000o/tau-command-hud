"""No Memo's vaults (tauhud.com/nomemo/, commands vaults, drain, crack): wallets Tau HUD runs on the testnet that a player
can empty, if they read or write the right rule.

On Tau Net nobody moves money without the key, and a personal rule (an o5 clause) binds only the sends of the wallet
that holds it. So the vaults are played as a LEAKED KEY: this server holds each vault's key and signs EVERY plain
payment a player asks for (drain <vault> <amount>), never a change of the rule. What stands between the player and the
money is the vault's rule, checked by the node like any wallet's. What is real: the rule on the chain, the node's yes
or no, the payment in a block. What is game: that our server signs for anyone who asks. (A real thief with a real key
could also replace the rule; this server never does that for a player.) A payment the rule refuses is refused at the
node's door, before the mempool, so it costs no fee.

The row: four vaults, each with a rule dealt anew every Monday 00:00 UTC (from VAULT_SECRET, kept in the state file):
  till      passes at most CAP a payment (CAP in hex): drained in many small payments
  reserve   passes at most RESERVE_STEP a payment and none that leaves less than the floor (i2, the balance before the
            payment): drained down to the floor. i2 is the balance at the PARENT block (IDNI tau-testnet issue #20), so
            this server never sends a vault's next payment before its last one is in a block: each payment sees a fresh
            balance, and the floor holds
  window    passes only amounts from A to B, a narrow window (hex)
  clock     passes only inside a half hour of the week, the block time i5 in seconds, and at most CLOCK_MAX a payment
Each is filled to TARGET when the week turns, by the No Memo drop (nomemo.py), which its own bank keeps filled.

The keeper (crack <level> <rule>): a vault whose keeper takes a rule a player writes FOR the vault, if it passes the
keeper's checklist: test payments the real Tau engine on this server judges with that rule (infra/checker, POST
/check), all of which must be blocked. A rule that passes goes on the chain as the keeper's own rule; for LEASE
seconds after it is in force, the player who wrote it may drain up to the level's cap; then the keeper locks again
(the rule that blocks every amount above 0). The lesson: a checklist of test payments never proves a rule has no
hole. The levels:
  1 sleepy    blocks three payments to a stranger
  2 careful   also blocks the player's own wallet at 1, 10, 100, 500, 1,000 and the cap
  3 paranoid  four strangers and four amounts to the player, all dealt at random and not shown; a rule that names the
              player's own address is refused before any test
The player's rule is the keeper's rule only while the lease lasts, and only the lease holder's payments are signed.

GET /vaults                                     the vaults: rule text, in force, balance, the week's top wallets, the keeper
GET /vaults/drain?vault=<k>&to=<address>&amount=<n>   asks for one payment to that wallet; answers {"id"}
GET /vaults/crack?level=<1-3>&to=<address>&rule=<text> asks the keeper; answers {"id"}
GET /vaults/req?id=<id>                         what became of a drain or a crack
Only wallets that have paid the No Memo drop at least once are served (they are on our node already, IDNI #108).

VAULTS_ENABLED=0 switches them off. State: VAULTS_STATE_PATH, keys: VAULTS_KEYS_PATH (0600, never leave the server).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
import urllib.error
import urllib.request

log = logging.getLogger("vaults")

ROW = ("till", "reserve", "window", "clock")
KEYS = (*ROW, "keeper")
NAMES = {"till": "The till", "reserve": "The reserve", "window": "The window", "clock": "The clock", "keeper": "The keeper"}

BLOCK = "(o5[t]:bv[24] = { #x000000 }:bv[24])"
ALLOW = "(o5[t]:bv[24] = { #x000001 }:bv[24])"
LOCK = f"(i1[t]:bv[24] > {{ #x000000 }}:bv[24]) ? {BLOCK} : {ALLOW}"   # the keeper at rest: nothing above 0 leaves

TARGET = {"till": 40_000, "reserve": None, "window": 40_000, "clock": 40_000, "keeper": 30_000}   # reserve: floor + RESERVE_POT
RESERVE_POT = 30_000
RESERVE_STEP = 5_000      # the reserve passes at most this a payment
CLOCK_MAX = 4_000         # the clock passes at most this a payment
FILL_MAX = 50_000         # the drop sends a vault at most this at once
FILL_BELOW = 10_000       # the keeper is filled again when it holds less than this
LEVELS = {1: {"name": "sleepy", "cap": 500}, 2: {"name": "careful", "cap": 1_500}, 3: {"name": "paranoid", "cap": 4_000}}
L2_MINE = (1, 10, 100, 500, 1_000)   # level 2 also tests the player's own wallet at these and at the cap
LEASE = 10 * 60           # seconds the cracked keeper stays the player's after its rule is in force
LEASE_SET_WAIT = 15 * 60  # a player's rule not in force after this: the lease is given up and the keeper locks
GAP = 15                  # seconds between two of our sends, at least
LOOK_GAP = 8              # seconds between two lookups
RECHECK = 30 * 60         # each vault's rule and balance looked up at least this often
RULE_WAIT = 10 * 60       # a rule sent and not in force: wait this long before sending it again
QUIET = 20                # seconds before asking again whether a payment is in a block
SEAL_TRIES = 30
DAILY = int(os.environ.get("VAULTS_DAILY", "600"))   # payments the vaults send a day, all together (refusals not counted)
PER_WALLET_DAY = 60       # drains a wallet may ask for a day
CRACKS_PER_DAY = 8        # cracks a wallet may ask for a day
ASK_GAP = 10              # seconds between two requests of one wallet
QUEUE_MAX = 40            # requests waiting, all together
KEEP = 400                # requests kept for /vaults/req
FEED_GAP = 10 * 60        # a vault's own refusal goes to the HUD's feed at most this often
SLACK = 100              # what a vault keeps for fees still counts as drained
FILL_WAIT = 10 * 60       # after the drop sent a vault money: no second fill before this
HEX96 = re.compile(r"^[0-9a-f]{96}$")
STRANGER = hashlib.sha384(b"tauhud no memo vaults: a stranger").hexdigest()   # 96 hex: the sleepy and careful keepers' stranger


def week_of(t: float) -> int:
    from nomemo import week_of as w
    return w(t)


def short(pk: str) -> str:
    return f"{pk[:6]}…{pk[-4:]}" if pk else ""


def norm(body: str) -> str:
    return "".join(str(body or "").split()).lower()


def hx(n: int) -> str:
    return f"{{ #x{n:06x} }}:bv[24]"


def i5v(n: int) -> str:
    return f"{{ {n} }}:bv[64]"


def full(body: str) -> str:
    return f"always ( {body} )."


def inner(rule: str) -> str:
    """The body of an `always ( … ).` rule, as the node keeps it."""
    m = re.match(r"^\s*always\s*\((.*)\)\s*\.\s*$", rule or "", re.S)
    return m.group(1).strip() if m else str(rule or "").strip()


def make_keys(path: str, keys: dict | None = None) -> dict:
    from py_ecc.bls import G2Basic
    keys = dict(keys or {})
    for name in KEYS:
        if name in keys:
            continue
        sk = G2Basic.KeyGen(secrets.token_bytes(32))
        sk = sk if isinstance(sk, int) else int.from_bytes(bytes(sk), "big")
        keys[name] = {"sk": sk.to_bytes(32, "big").hex(), "pk": G2Basic.SkToPk(sk).hex()}
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(keys, f)
    os.replace(tmp, path)
    return keys


def deal(secret: str, week: int, name: str, week_start: int) -> dict:
    """This week's numbers for one vault of the row."""
    r = int.from_bytes(hmac.new(secret.encode(), f"{week}:{name}".encode(), hashlib.sha256).digest(), "big")
    if name == "till":
        return {"cap": 100 * (3 + r % 18)}                          # 300 to 2,000
    if name == "reserve":
        return {"floor": 5_000 * (8 + r % 9), "step": RESERVE_STEP}   # 40,000 to 80,000
    if name == "window":
        a = 1_000 + (r % 8_000) * 1 + 7 * ((r >> 20) % 100)            # an odd-looking number from 1,000 up
        return {"a": a, "b": a + 10 * (2 + (r >> 40) % 7)}              # 20 to 80 wide
    if name == "clock":
        day = r % 7                                                     # Monday to Sunday of this week (UTC)
        hour = 9 + (r >> 8) % 12                                        # 9:00 to 20:30 UTC
        half = (r >> 16) % 2
        start = week_start + day * 86400 + hour * 3600 + half * 1800
        return {"from": start, "to": start + 1800, "max": CLOCK_MAX}
    raise ValueError(name)


def body_of(name: str, d: dict) -> str:
    if name == "till":
        return f"(i1[t]:bv[24] > {hx(d['cap'])}) ? {BLOCK} : {ALLOW}"
    if name == "reserve":
        return (f"(i1[t]:bv[24] > {hx(d['step'])} || i1[t]:bv[24] > i2[t]:bv[24] || "
                f"(i2[t]:bv[24] - i1[t]:bv[24]) < {hx(d['floor'])}) ? {BLOCK} : {ALLOW}")
    if name == "window":
        return f"(i1[t]:bv[24] >= {hx(d['a'])} && i1[t]:bv[24] <= {hx(d['b'])}) ? {ALLOW} : {BLOCK}"
    if name == "clock":
        return (f"(i5[t]:bv[64] >= {i5v(d['from'])} && i5[t]:bv[64] < {i5v(d['to'])} && "
                f"!(i1[t]:bv[24] > {hx(d['max'])})) ? {ALLOW} : {BLOCK}")
    raise ValueError(name)


def passes(name: str, d: dict, amount: int, balance: int, t: int) -> bool:
    """What the rule says, read here (only for the page's words and the tests; the node decides)."""
    if name == "till":
        return amount <= d["cap"]
    if name == "reserve":
        return amount <= d["step"] and amount <= balance and balance - amount >= d["floor"]
    if name == "window":
        return d["a"] <= amount <= d["b"]
    if name == "clock":
        return d["from"] <= t < d["to"] and amount <= d["max"]
    return False


def drained(name: str, d: dict, balance: int) -> bool:
    """Nothing the rule lets through is left to take (fees aside)."""
    if name == "reserve":
        return balance - d["floor"] < SLACK
    if name == "window":
        return balance < d["a"] + SLACK
    return balance < SLACK


def checklist(level: int, me: str, seed: str, t: int, balance: int) -> list:
    """The keeper's test payments (all must be blocked), at most 8, as POST /check takes them (from = the keeper,
    filled in by the caller)."""
    cap = LEVELS[level]["cap"]
    row = lambda to, amount: {"to": to, "amount": amount, "time": t, "balance": balance}   # noqa: E731
    if level == 1:
        return [row(STRANGER, 1), row(STRANGER, 5_000), row(STRANGER, 100_000)]
    if level == 2:
        return [row(STRANGER, 1), row(STRANGER, 5_000)] + [row(me, a) for a in (*L2_MINE, cap)]
    r = hashlib.sha512(f"{seed}:{me}".encode()).digest()
    strangers = [hashlib.sha384(r + bytes([k])).hexdigest() for k in range(4)]
    amounts = [1 + int.from_bytes(r[4 * k:4 * k + 4], "big") % cap for k in range(4)]
    return [row(s, amounts[k]) for k, s in enumerate(strangers)] + [row(me, a) for a in amounts]


class Vaults:
    def __init__(self, nomemo=None, keys_path: str | None = None, state_path: str | None = None, clock=time.time,
                 enabled: bool | None = None, keys: dict | None = None, checker=None):
        data = os.environ.get("CRUISE_DATA", "/data")
        self.keys_path = keys_path or os.environ.get("VAULTS_KEYS_PATH", os.path.join(data, "vaults.keys"))
        self.state_path = state_path or os.environ.get("VAULTS_STATE_PATH", os.path.join(data, "vaults-state.json"))
        self.enabled = (os.environ.get("VAULTS_ENABLED", "1") != "0") if enabled is None else enabled
        self.checker_url = os.environ.get("CHECKER_URL", "http://checker:8090").rstrip("/")
        self.check = checker or self._check_http   # (rule, sender, tests) -> the checker's answer, or None
        self.nomemo = nomemo
        self.clock = clock
        self.on_tx = None        # (ok) for the load page
        self.on_refused = None   # (entry) the relay lists it with the dropped transactions of /stats
        self.sk: dict[str, int] = {}
        self.pk: dict[str, str] = {}
        self.who: dict[str, str] = {}
        self.ready = False
        self.last_send = 0.0
        self.last_look = 0.0
        self.st: dict = {"secret": "", "vaults": {}, "reqs": {}, "order": [], "day": "", "today": 0, "lease": None, "log": []}
        self.load_state()
        if not self.st["secret"]:
            self.st["secret"] = os.environ.get("VAULT_SECRET") or secrets.token_hex(32)
            self.save_state()
        if not self.enabled:
            return
        try:
            if keys is None:
                if os.path.exists(self.keys_path):
                    with open(self.keys_path) as f:
                        keys = json.load(f)
                if not keys or any(n not in keys for n in KEYS):
                    keys = make_keys(self.keys_path, keys)
            self.use_keys(keys)
        except Exception as exc:   # the relay keeps working without them
            log.warning("vaults off: %r", exc)
            self.enabled = False

    def use_keys(self, keys: dict):
        self.sk = {n: int(k["sk"], 16) for n, k in keys.items() if n in KEYS}
        self.pk = {n: k["pk"].lower() for n, k in keys.items() if n in KEYS}
        self.who = {pk: "nomemo" for pk in self.pk.values()}
        self.ready = all(n in self.pk for n in KEYS)

    # ---------- state ----------
    def load_state(self):
        try:
            with open(self.state_path) as f:
                st = json.load(f)
            if isinstance(st, dict):
                for k in self.st:
                    if k in st and isinstance(st[k], type(self.st[k])) or k == "lease" and isinstance(st.get(k), dict):
                        self.st[k] = st[k]
        except (OSError, ValueError, TypeError):
            pass

    def save_state(self):
        try:
            order = self.st["order"]
            if len(order) > KEEP:
                for rid in order[:len(order) - KEEP]:
                    self.st["reqs"].pop(rid, None)
                self.st["order"] = order[-KEEP:]
            tmp = self.state_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.st, f, separators=(",", ":"))
            os.replace(tmp, self.state_path)
        except OSError as exc:
            log.warning("cannot write %s: %r", self.state_path, exc)

    def v(self, name: str) -> dict:
        return self.st["vaults"].setdefault(name, {})

    def note(self, name: str, text: str):
        self.st["log"] = (self.st["log"] + [{"t": int(self.clock()), "vault": name, "note": text}])[-60:]
        log.info("vault %s: %s", name, text)

    def recheck(self):
        """The testnet restarted: every rule is gone with the old chain; a lease ends, the keeper locks again."""
        for name in KEYS:
            self.v(name).update(checked=0, in_force=False)
            self.v(name).pop("sent_rule", None)
            self.v(name).pop("paying", None)
        ls = self.st.get("lease")
        if ls:
            self.end_lease("the testnet restarted")

    # ---------- the rules ----------
    def week_start(self, t: float) -> int:
        return int((week_of(t) * 7 - 3) * 86400)

    def dealt(self, name: str, t: float | None = None) -> dict:
        t = self.clock() if t is None else t
        return deal(self.st["secret"], week_of(t), name, self.week_start(t))

    def body(self, name: str) -> str:
        """The rule this vault should hold now."""
        if name == "keeper":
            ls = self.st.get("lease")
            return inner(ls["rule"]) if ls and ls.get("state") in ("setting", "open") else LOCK
        return body_of(name, self.dealt(name))

    def words(self, name: str) -> str:
        if name == "keeper":
            return "locked: blocks every amount above 0" if self.body("keeper") == LOCK else "the rule a player wrote, for that player's lease"
        d = self.dealt(name)
        if name == "till":
            return f"passes at most {d['cap']:,} a payment"
        if name == "reserve":
            return f"passes at most {d['step']:,} a payment, and none that leaves less than {d['floor']:,}"
        if name == "window":
            return f"passes only amounts from {d['a']:,} to {d['b']:,}"
        return f"passes at most {d['max']:,} a payment, and only in one half hour of the week"

    async def look(self, name: str, ask) -> None:
        """Which rule the vault has in force now, and its balance."""
        res = await ask(f"getruleoffers {self.pk[name]} all")
        if not res or res.get("status") != "ok":
            return
        body = None
        for c in (res.get("data") or {}).get("accepted_clauses") or []:
            if isinstance(c, dict) and str(c.get("target_stream", "")).lstrip("o") == "5" and c.get("clause_body"):
                body = c["clause_body"]
        want = self.body(name)
        v = self.v(name)
        was = v.get("in_force")
        v["checked"] = int(self.clock())
        v["in_force"] = bool(body) and norm(body) in {norm(want), norm(full(want)), norm(f"({want})")}
        v["holds"] = norm(body) if body else ""
        if v["in_force"] and not was:
            self.note(name, "rule in force: " + self.words(name))
            v.pop("sent_rule", None)
        b = await self.balance(name, ask)
        if b is not None:
            v["balance"] = b

    async def balance(self, name: str, ask) -> int | None:
        m = await ask(f"getbalance {self.pk[name]}")
        if not m or m.get("status") != "ok":
            return None
        try:
            return int((m.get("data") or {}).get("balance") or 0)
        except (TypeError, ValueError):
            return None

    # ---------- the transactions ----------
    def build(self, name: str, seq: int, tip: int, fee: int, rule: str | None = None, to: str | None = None, amount: int = 0) -> dict:
        from py_ecc.bls import G2Basic
        from showcase import signing_bytes
        pk = self.pk[name]
        tx = {"tx_type": "user_tx", "sender_pubkey": pk, "sequence_number": seq, "expiration_time": int(self.clock()) + 600,
              "expire_at_height": tip + 1000, "fee_limit": str(fee * 5),
              "operations": {"0": rule} if rule is not None else {"1": [[pk, to, str(amount)]]}}
        tx["signature"] = G2Basic.Sign(self.sk[name], hashlib.sha256(signing_bytes(tx)).digest()).hex()
        return tx

    async def send(self, name: str, ask, gov, **kw):
        from island import base_fee
        st = await ask(f"getsequence {self.pk[name]}")
        if not st or st.get("status") != "ok":
            return None, None
        d = st.get("data") or {}
        tx = await asyncio.to_thread(self.build, name, int(d.get("sequence_number") or 0), int(d.get("tip_height") or 0), base_fee(gov()), **kw)
        res = await ask("sendtx " + json.dumps(tx, separators=(",", ":")))
        self.last_send = self.clock()
        return res, tx

    @staticmethod
    def took(res) -> bool:
        return isinstance(res, dict) and res.get("status") == "ok" and (res.get("data") or {}).get("ok") is not False

    @staticmethod
    def said(res) -> str:
        err = (res or {}).get("error") or (res or {}).get("data") or res
        if isinstance(err, dict):
            err = err.get("message") or json.dumps(err, separators=(",", ":"))
        return str(err)[:300]

    async def sealed(self, tx_hash: str, ask) -> bool | None:
        m = await ask(f"gettxstatus {tx_hash}")
        if not m or m.get("status") != "ok":
            return None
        d = m.get("data") or {}
        s = str(d.get("status") or d.get("state") or "").lower()
        if d.get("block_number") is not None or any(x in s for x in ("confirmed", "included", "mined", "sealed", "applied")):
            return True
        if any(x in s for x in ("reject", "fail", "dropped", "expired", "invalid", "unknown", "not_found")):
            return False
        return None

    async def set_rule(self, name: str, ask, gov) -> bool:
        body = self.body(name)
        res, tx = await self.send(name, ask, gov, rule=full(body))
        if tx is None:
            return False
        v = self.v(name)
        v["sent_rule"] = int(self.clock())
        if self.took(res):
            self.note(name, "rule sent: " + self.words(name))
            v["checked"] = int(self.clock()) - RECHECK + 90   # look again in a minute and a half
        else:
            self.note(name, "the node refused the rule: " + self.said(res))
            ls = self.st.get("lease")
            if name == "keeper" and ls and ls.get("state") == "setting":
                self.req_done(ls["req"], "refused", f"the node refused your rule: {self.said(res)}")
                self.end_lease("the node refused the rule", lock=False)
        self.on_tx and self.on_tx(self.took(res))
        return True

    def budget(self) -> bool:
        d = dt.datetime.utcfromtimestamp(self.clock()).strftime("%Y-%m-%d")
        if d != self.st["day"]:
            self.st["day"], self.st["today"] = d, 0
        return self.st["today"] < DAILY

    # ---------- requests ----------
    def known(self, pk: str) -> bool:
        return bool(self.nomemo is not None and pk in getattr(self.nomemo, "wallets", {}))

    def mine_today(self, pk: str, kind: str) -> int:
        day = int(self.clock()) - 86400
        return sum(1 for r in self.st["reqs"].values() if r.get("to") == pk and r.get("kind") == kind and r.get("at", 0) >= day)

    def waiting(self) -> list:
        return [self.st["reqs"][i] for i in self.st["order"] if self.st["reqs"].get(i, {}).get("state") == "waiting"]

    def new_req(self, **r) -> dict:
        rid = secrets.token_hex(6)
        r.update(id=rid, at=int(self.clock()), state="waiting")
        self.st["reqs"][rid] = r
        self.st["order"].append(rid)
        self.save_state()
        return r

    def req_done(self, rid: str, state: str, said: str, **extra):
        r = self.st["reqs"].get(rid)
        if r:
            r.update(state=state, said=said, done=int(self.clock()), **extra)

    def gate(self, to: str, kind: str) -> str | None:
        if not self.enabled or not self.ready:
            return "the vaults are closed just now"
        if not HEX96.match(to):
            return "not an address"
        if not self.known(to):
            return "the vaults serve wallets that have paid the No Memo drop at least once: play one contract first"
        if any(r.get("to") == to for r in self.waiting()) or (self.st.get("lease") or {}).get("to") == to and kind == "crack":
            return "you already have a request under way: wait for its answer"
        mine = [r for r in self.st["reqs"].values() if r.get("to") == to]
        if mine and self.clock() - max(r.get("at", 0) for r in mine) < ASK_GAP:
            return f"one request every {ASK_GAP} seconds"
        if kind == "drain" and self.mine_today(to, "drain") >= PER_WALLET_DAY:
            return f"{PER_WALLET_DAY} drains a day per wallet; more tomorrow"
        if kind == "crack" and self.mine_today(to, "crack") >= CRACKS_PER_DAY:
            return f"{CRACKS_PER_DAY} cracks a day per wallet; more tomorrow"
        if len(self.waiting()) >= QUEUE_MAX:
            return "too many requests waiting; try again in a minute"
        return None

    def ask_drain(self, vault: str, to: str, amount: str) -> dict:
        to = str(to or "").lower()
        if vault not in KEYS:
            return {"error": "no such vault: " + ", ".join(KEYS)}
        if not re.fullmatch(r"\d{1,8}", str(amount or "")) or not 1 <= int(amount) < (1 << 24):
            return {"error": "an amount is a whole number from 1 to 16,777,215"}
        why = self.gate(to, "drain")
        if why:
            return {"error": why}
        if vault == "keeper":
            ls = self.st.get("lease")
            if not ls or ls.get("to") != to or ls.get("state") != "open":
                return {"error": "the keeper is not yours: crack it first (crack <level> <rule>), then drain it while your lease lasts"}
            if int(amount) > ls["left"]:
                return {"error": f"your lease allows {ls['left']:,} more at most"}
        return {"id": self.new_req(kind="drain", vault=vault, to=to, amount=int(amount))["id"]}

    def ask_crack(self, level: str, to: str, rule: str) -> dict:
        to = str(to or "").lower()
        if not re.fullmatch(r"[123]", str(level or "")):
            return {"error": "the levels are 1, 2 and 3"}
        rule = str(rule or "").strip()
        if not rule or len(rule.encode()) > 8192:
            return {"error": "a rule is 1 to 8,192 bytes of Tau"}
        why = self.gate(to, "crack")
        if why:
            return {"error": why}
        if self.st.get("lease") or any(r.get("kind") == "crack" for r in self.waiting()):
            return {"error": "the keeper is busy with another player's rule; try again in a few minutes"}
        if not re.match(r"^\s*always\s*\(", rule):
            rule = full(rule)
        return {"id": self.new_req(kind="crack", level=int(level), to=to, rule=rule)["id"]}

    def req_view(self, rid: str) -> dict:
        r = self.st["reqs"].get(str(rid or ""))
        if not r:
            return {"error": "unknown request"}
        out = {k: r.get(k) for k in ("id", "kind", "vault", "level", "amount", "state", "said", "tx", "tests", "block") if r.get(k) is not None}
        ls = self.st.get("lease")
        if r.get("kind") == "crack" and ls and ls.get("req") == r["id"]:
            out["lease"] = {"state": ls["state"], "until": ls.get("until"), "left": ls.get("left"), "cap": LEVELS[ls["level"]]["cap"]}
        if r.get("state") == "waiting":
            w = self.waiting()
            out["place"] = 1 + next((i for i, x in enumerate(w) if x["id"] == r["id"]), 0)
        return out

    # ---------- the keeper ----------
    def _check_http(self, rule: str, sender: str, tests: list):
        body = json.dumps({"rule": rule, "sender": sender, "tests": tests}).encode()
        rq = urllib.request.Request(self.checker_url + "/check", data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(rq, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as exc:
            try:
                return json.loads(exc.read())
            except Exception:
                return {"error": f"checker answered {exc.code}"}
        except Exception as exc:
            log.warning("vaults: checker unreachable: %r", exc)
            return None

    async def judge(self, r: dict) -> None:
        """The keeper's checklist for one crack: every test payment must be blocked."""
        level, me, rule = r["level"], r["to"], r["rule"]
        if level == 3 and me in rule.lower():
            self.req_done(r["id"], "caught", "the paranoid keeper reads every rule first: yours names your own address")
            return
        now = int(self.clock())
        tests = checklist(level, me, r["id"], now, int(self.v("keeper").get("balance") or 100_000))
        res = await asyncio.to_thread(self.check, rule, self.pk["keeper"], [{**t, "from": self.pk["keeper"]} for t in tests])
        if not isinstance(res, dict) or res.get("accepted") is None:
            why = (res or {}).get("error") or (res or {}).get("reason") or "no answer"
            self.req_done(r["id"], "refused", f"the Tau checker could not judge it just now ({why}); try again in a minute")
            return
        if not res.get("accepted"):
            self.req_done(r["id"], "refused", f"the node would refuse this rule ({res.get('stage')}): {res.get('reason')}")
            return
        runs = res.get("tests") or []
        shown = []
        for t, run in zip(tests, runs):
            hidden = level == 3
            shown.append({"to": "you" if t["to"] == me else "a stranger" if t["to"] == STRANGER else "a stranger (dealt)",
                          "amount": None if hidden else t["amount"], "passed": run.get("o5") != 0})
        if len(runs) != len(tests):
            self.req_done(r["id"], "refused", "the Tau checker gave an incomplete answer; try again in a minute")
            return
        if any(x["passed"] for x in shown):
            self.req_done(r["id"], "caught", "the keeper's checklist caught your rule: a test payment it must block got through", tests=shown)
            return
        r.update(state="setting", tests=shown, said="your rule passed the keeper's checklist; it goes on the chain as the keeper's own rule")
        self.st["lease"] = {"req": r["id"], "to": me, "level": level, "rule": rule, "state": "setting", "since": now,
                            "left": LEVELS[level]["cap"], "until": None}
        self.v("keeper").update(in_force=False, checked=int(self.clock()))
        self.v("keeper").pop("sent_rule", None)
        self.note("keeper", f"level {level} cracked by {short(me)}: their rule goes on the chain")

    def end_lease(self, why: str, lock: bool = True):
        ls = self.st.get("lease")
        if not ls:
            return
        r = self.st["reqs"].get(ls["req"])
        if r and r.get("state") in ("setting", "open"):
            r.update(state="over", said=why)
        self.st["lease"] = None
        self.v("keeper").update(in_force=False, checked=int(self.clock()) if lock else 0)
        self.v("keeper").pop("sent_rule", None)
        self.note("keeper", f"lease of {short(ls['to'])} over: {why}; the keeper locks again")

    # ---------- the loop ----------
    async def step(self, ask, gov) -> bool:
        """Called in the island bot's free slots. Sends at most one transaction; True if it did."""
        if not self.enabled or not self.ready:
            return False
        now = self.clock()
        # 0. a crack waiting: the checker judges it (no transaction)
        for r in self.waiting():
            if r["kind"] == "crack" and not self.st.get("lease"):
                r["state"] = "checking"
                await self.judge(r)
                self.save_state()
                return False
        ls = self.st.get("lease")
        if ls:
            if ls["state"] == "setting" and self.v("keeper").get("in_force"):
                ls.update(state="open", until=int(now) + LEASE)
                self.req_done(ls["req"], "open", "your rule is the keeper's rule on the chain now: drain keeper <amount>")
                self.st["reqs"][ls["req"]]["state"] = "open"
            elif ls["state"] == "setting" and now - ls["since"] > LEASE_SET_WAIT:
                self.end_lease("your rule did not reach the chain in time")
            elif ls["state"] == "open" and (now > ls["until"] or ls["left"] <= 0) and not self.v("keeper").get("paying"):
                self.end_lease("the lease is over" if ls["left"] > 0 else "you took the level's whole cap")
        # 1. lookups: a rule not looked at for a while, a new week's rule, a payment waiting for its block
        if now - self.last_look >= LOOK_GAP:
            for name in KEYS:
                v = self.v(name)
                p = v.get("paying")
                if p and now >= p.get("next", 0):
                    self.last_look = now
                    await self.follow(name, p, ask)
                    self.save_state()
                    return False
            for name in KEYS:
                v = self.v(name)
                stale = name != "keeper" and v.get("week") != week_of(now)
                if now - v.get("checked", 0) >= RECHECK or stale or (name == "keeper" and ls and ls["state"] == "setting" and now - v.get("checked", 0) >= 30):
                    self.last_look = now
                    if stale:
                        v.update(week=week_of(now), in_force=False, top={}, drained=None, filled=None)
                        v.pop("sent_rule", None)
                    await self.look(name, ask)
                    self.save_state()
                    return False
        if now - self.last_send < GAP:
            return False
        # 2. a vault without the rule it should hold gets it
        for name in KEYS:
            v = self.v(name)
            if not v.get("checked") or v.get("in_force") or v.get("paying"):
                continue
            if now - v.get("sent_rule", 0) < RULE_WAIT:
                continue
            sent = await self.set_rule(name, ask, gov)
            self.save_state()
            if sent:
                return True
        # 3. a drain waiting, for a vault with no payment in flight
        for r in self.waiting():
            if r["kind"] != "drain":
                continue
            v = self.v(r["vault"])
            if v.get("paying"):
                continue
            if not v.get("in_force"):
                if now - r["at"] > 20 * 60:
                    self.req_done(r["id"], "refused", "the vault's rule was not in force on the chain for 20 minutes; nothing was sent")
                    self.save_state()
                continue
            if not self.budget():
                self.req_done(r["id"], "refused", "the vaults have sent all they may today; more tomorrow")
                self.save_state()
                continue
            if r["vault"] == "keeper":
                ls = self.st.get("lease")
                if not ls or ls["state"] != "open" or ls["to"] != r["to"] or r["amount"] > ls["left"]:
                    self.req_done(r["id"], "refused", "your lease is over; nothing was sent")
                    self.save_state()
                    continue
            return await self.pay(r, ask, gov)
        # 4. a vault low on money is filled by the drop (once a week for the row, when low for the keeper)
        return await self.fill(ask, gov)

    async def pay(self, r: dict, ask, gov) -> bool:
        name = r["vault"]
        res, tx = await self.send(name, ask, gov, to=r["to"], amount=r["amount"])
        if tx is None:
            return False
        now = int(self.clock())
        if self.took(res):
            h = (res.get("data") or {}).get("tx_hash") or ""
            self.st["today"] += 1
            r.update(state="sent", tx=h, said="the node took it; waiting for a block")
            self.v(name)["paying"] = {"req": r["id"], "tx": h, "next": now + QUIET, "asked": 0}
            if name == "keeper" and self.st.get("lease"):
                self.st["lease"]["left"] -= r["amount"]
        else:
            said = self.said(res)
            own = "own policy" in said or "o5" in said
            self.req_done(r["id"], "stopped" if own else "refused",
                          ("the vault's own rule said no (o5 = 0): " if own else "the node said no: ") + said)
            if own and self.on_refused and now - self.v(name).get("fed", 0) >= FEED_GAP:
                self.v(name)["fed"] = now
                hsh = hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest()
                self.on_refused({"tx_hash": hsh, "type": "user_tx", "sender": self.pk[name], "seen": now, "left": now,
                                 "reason": f"o5 = 0 · its own rule said no: a No Memo player asked {NAMES[name]} for {r['amount']:,} "
                                           "(the vault's key is played as leaked; its rule is the only lock)", "vault": name})
        self.on_tx and self.on_tx(self.took(res))
        self.save_state()
        return True

    async def follow(self, name: str, p: dict, ask) -> None:
        """A vault's payment in flight: in a block yet?"""
        ok = await self.sealed(p["tx"], ask) if p.get("tx") else False
        r = self.st["reqs"].get(p["req"]) or {}
        now = int(self.clock())
        if ok is None:
            p["asked"] = p.get("asked", 0) + 1
            p["next"] = now + QUIET
            if p["asked"] <= SEAL_TRIES:
                return
            ok = False
        v = self.v(name)
        v.pop("paying", None)
        if ok:
            r.update(state="paid", said=f"in a block: {r.get('amount', 0):,} test AGRS from {NAMES[name]} to your wallet")
            top = v.setdefault("top", {})
            top[r["to"]] = top.get(r["to"], 0) + int(r.get("amount") or 0)
            v["last"] = {"t": now, "to": short(r["to"]), "amount": r.get("amount")}
            b = await self.balance(name, ask)
            if b is not None:
                v["balance"] = b
                if name in ROW and not v.get("drained") and drained(name, self.dealt(name), b):
                    v["drained"] = {"t": now, "by": short(r["to"])}
                    self.note(name, f"drained by {short(r['to'])}")
        else:
            r.update(state="refused", said="the node took it but it never reached a block; nothing moved")
            if name == "keeper" and self.st.get("lease") and self.st["lease"].get("req"):
                self.st["lease"]["left"] += int(r.get("amount") or 0)

    async def fill(self, ask, gov) -> bool:
        nm = self.nomemo
        if nm is None or not getattr(nm, "ready", False) or not nm.pk.get("drop"):
            return False
        now = self.clock()
        for name in KEYS:
            v = self.v(name)
            if v.get("paying") or v.get("balance") is None or not v.get("in_force") or now - v.get("fill_at", 0) < FILL_WAIT:
                continue
            if name == "keeper":
                if self.st.get("lease") or v["balance"] >= FILL_BELOW:
                    continue
                want = TARGET["keeper"] - v["balance"]
            else:
                if v.get("filled") == week_of(now):
                    continue
                target = (self.dealt(name)["floor"] + RESERVE_POT) if name == "reserve" else TARGET[name]
                want = target - v["balance"]
                if want <= 0:
                    v["filled"] = week_of(now)
                    continue
            want = min(FILL_MAX, want)
            ready = await nm.drop_ready(want, ask, gov)
            if ready is not True:
                return ready == "filled"
            h = await nm.send("drop", self.pk[name], want, ask, gov)
            v["fill_at"] = int(now)
            if h:
                if name != "keeper" and want < FILL_MAX:
                    v["filled"] = week_of(now)
                v["checked"] = int(now) - RECHECK + 120   # its balance looked at again in two minutes
                self.note(name, f"the drop fills it with {want:,}")
            self.save_state()
            return bool(h)
        return False

    # ---------- what pages see ----------
    def snapshot(self) -> dict:
        now = int(self.clock())
        out = {}
        for name in KEYS:
            v = self.v(name)
            body = self.body(name)
            # the rule as Tau only: reading it (hex amounts, i5 seconds) is the player's work; its words are for `up vaults`
            row = {"name": NAMES[name], "pk": self.pk.get(name), "rule_text": full(body),
                   "in_force": bool(v.get("in_force")), "balance": v.get("balance"), "busy": bool(v.get("paying")),
                   "top": [[short(k), n] for k, n in sorted((v.get("top") or {}).items(), key=lambda x: -x[1])[:5]],
                   "last": v.get("last"), "drained": v.get("drained")}
            if name == "keeper":
                row["words"] = self.words(name)
            out[name] = row
        ls = self.st.get("lease")
        return {"enabled": bool(self.enabled), "ready": self.ready, "week": week_of(now), "next_week": self.week_start(now) + 7 * 86400,
                "vaults": out, "stranger": STRANGER,
                "keeper": {"levels": {str(k): {**x, "tests": "hidden" if k == 3 else [{"to": "a stranger", "amount": a} for a in (1, 5_000, 100_000)] if k == 1 else
                                               [{"to": "a stranger", "amount": a} for a in (1, 5_000)] + [{"to": "you", "amount": a} for a in (*L2_MINE, x["cap"])]}
                                      for k, x in LEVELS.items()},
                           "lease": {"to": short(ls["to"]), "level": ls["level"], "state": ls["state"], "until": ls.get("until")} if ls else None,
                           "lease_seconds": LEASE},
                "waiting": len(self.waiting()), "today": self.st["today"],
                "limits": {"daily": DAILY, "per_wallet": PER_WALLET_DAY, "cracks": CRACKS_PER_DAY, "gap": ASK_GAP},
                "log": self.st["log"][-8:], "now": now}

    def status(self) -> dict:
        """For `up vaults` (from inside the server only): the snapshot with each rule in words."""
        s = self.snapshot()
        for name in KEYS:
            s["vaults"][name]["words"] = self.words(name)
        return s

    def route(self, path: str, query: str = "", internal: bool = False) -> dict | None:
        from urllib.parse import parse_qs
        q = {k: v[0] for k, v in parse_qs(query or "", keep_blank_values=True).items()}
        if path == "/vaults":
            return self.status() if internal and q.get("words") == "1" else self.snapshot()
        if path == "/vaults/drain":
            r = self.ask_drain(q.get("vault", ""), q.get("to", ""), q.get("amount", ""))
        elif path == "/vaults/crack":
            r = self.ask_crack(q.get("level", ""), q.get("to", ""), q.get("rule", ""))
        elif path == "/vaults/req":
            return self.req_view(q.get("id", ""))
        else:
            return None
        return r

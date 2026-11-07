"""No Memo's crew purse: the server side of the terminal game on tauhud.com/nomemo/ (nomemo/game.js).

The game's twelve contracts are the visitor's own test transactions to the crew's drop. The drop is a wallet made here
once, together with its lookalike (a second key whose address shows the same first 6 and last 4 characters, found the
way hackweek.py finds its poisoner); both keys stay in NOMEMO_KEYS_PATH (mode 0600) and never leave the server.
The game reads the drop's address from GET /nomemo.

What the purse does, in the island bot's free slots (relay.py idle_step, after the cruise ships and the hack of the
week), at most one transaction every GAP seconds and DAILY a day:
  claim     a player closes a chapter by paying the drop 100 + the chapter's number (101, 102, 103: the amount is the
            message, there is no memo). The relay sees the payment go through (saw), the purse waits for its block
            (gettxstatus), then pays the SHARE back to that wallet, once per wallet and chapter
  mark      with the first chapter's share, once per wallet: 1 test AGRS from the drop, the crew's mark
  dust      the Tracer (NOMEMO_TRACER=1): a few minutes after the first share, the lookalike sends the wallet 1 test
            AGRS, so a wallet that reads only the ends of an address sees the drop twice. The game's hunt is to tell
            them apart by the whole address. Once per wallet, never to a wallet that did not claim
Everything is test AGRS without value; the point is a real handshake on the chain and a real lookalike in a real
wallet history. Nothing here is posted anywhere.

GET /nomemo                   the drop's address, whether the purse and the Tracer are on, the players' board (wallets
                              by chapter, never names), the limits
GET /nomemo/wallet/<address>  that wallet's claims, what was paid back (hashes), the dust it got

State: NOMEMO_STATE_PATH (wallets, the day's count). NOMEMO_ENABLED=0 switches the purse off (the game still plays;
claims stay on the chain and are paid when it is on again, within CLAIM_DAYS).
"""
from __future__ import annotations

import asyncio
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

log = logging.getLogger("nomemo")

CHAPTERS = 3
CLAIM_BASE = 100           # a claim pays 100 + chapter to the drop
SHARE = 500                # test AGRS paid back per chapter
MARK = 1                   # the crew's mark, once
DUST = 1                   # the Tracer's dust, once
GAP = 20                   # seconds between two of our sends, at least
DAILY = int(os.environ.get("NOMEMO_DAILY", "300"))   # payouts a day, all kinds
DUST_AFTER = 180           # seconds after the first share before the Tracer's dust goes out
CLAIM_DAYS = 14            # a claim older than this is forgotten unpaid
QUIET = 20                 # seconds to wait before asking the chain again whether a claim is sealed
TRIES = 40                 # gettxstatus asks per claim before it counts as not sealed
TOPUP = 99_000             # what the bank sends the drop when the drop runs low (the faucet gives a wallet with balance 0 100,000 when it first pays)
TOPUP_WAIT = 600           # seconds a top-up may stay unsealed before the drop is checked again
TAG = (6, 4)
WALLETS_KEEP = 5000
RANKS = (("aboard", 0), ("deckhand", 1), ("navigator", 2), ("quartermaster’s mate", 3))   # by chapters claimed


def short(pk: str) -> str:
    return f"{pk[:TAG[0]]}…{pk[-TAG[1]:]}" if pk else ""


def signing_bytes(tx: dict) -> bytes:
    from island import signing_bytes as sb
    return sb(tx)


def base_fee_of(gov) -> int:
    from island import base_fee
    return base_fee(gov())


def make_keys(path: str) -> None:
    """The drop and its lookalike, written once (0600). Its own process: the search takes minutes of pure Python."""
    from py_ecc.bls import G2Basic
    from hackweek import grind
    pair = grind()
    if not pair:
        raise SystemExit("no lookalike pair found")
    keys = {name: {"sk": sk.to_bytes(32, "big").hex(), "pk": G2Basic.SkToPk(sk).hex()} for name, sk in (("drop", pair[0]), ("shadow", pair[1]))}
    assert short(keys["drop"]["pk"]) == short(keys["shadow"]["pk"]) and keys["drop"]["pk"] != keys["shadow"]["pk"]
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(keys, f)
    os.replace(tmp, path)


class NoMemo:
    def __init__(self, keys_path: str | None = None, state_path: str | None = None, clock=time.time, enabled: bool | None = None,
                 tracer: bool | None = None, background: bool = True, keys: dict | None = None):
        data = os.environ.get("CRUISE_DATA", "/data")
        self.keys_path = keys_path or os.environ.get("NOMEMO_KEYS_PATH", os.path.join(data, "nomemo.keys"))
        self.state_path = state_path or os.environ.get("NOMEMO_STATE_PATH", os.path.join(data, "nomemo-state.json"))
        self.enabled = (os.environ.get("NOMEMO_ENABLED", "1") != "0") if enabled is None else enabled
        self.tracer = (os.environ.get("NOMEMO_TRACER", "1") != "0") if tracer is None else tracer
        self.clock = clock
        self.on_tx = None
        self.on_ready = None
        self.sk: dict[str, int] = {}
        self.pk: dict[str, str] = {}
        self.who: dict[str, str] = {}
        self.ready = False
        self.making = False
        self.wallets: dict[str, dict] = {}
        self.jobs: list[dict] = []        # what waits to go out: {"kind", "to", "ch", "claim", "not_before", "asked"}
        self.day = ""
        self.today = 0
        self.next_seq: dict[str, int] = {}
        self.last_send = 0.0
        self.topup: dict | None = None    # {"hash", "at"}: the bank's last payment to the drop, until it is sealed
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
                log.info("no memo: looking for the drop and its lookalike (a few minutes, low priority)")
                subprocess.run([sys.executable, os.path.abspath(__file__), "keys", self.keys_path], check=True,
                               preexec_fn=lambda: os.nice(19), timeout=6 * 3600)
            with open(self.keys_path) as f:
                self.use_keys(json.load(f))
        except Exception as exc:   # the relay keeps working without it
            log.warning("no memo purse off: %r", exc)
            self.enabled = False
        finally:
            self.making = False

    def use_keys(self, keys: dict):
        self.sk = {n: int(k["sk"], 16) for n, k in keys.items()}
        self.pk = {n: k["pk"] for n, k in keys.items()}
        self.who = {pk: "nomemo" for pk in self.pk.values()}
        self.ready = True
        if self.on_ready:
            try:
                self.on_ready()
            except Exception as exc:
                log.warning("no memo: on_ready failed: %r", exc)

    # ---------- state ----------
    def load_state(self):
        try:
            with open(self.state_path) as f:
                s = json.load(f)
            self.wallets = {k: v for k, v in (s.get("wallets") or {}).items() if isinstance(v, dict)}
            self.jobs = [j for j in (s.get("jobs") or []) if isinstance(j, dict)]
            self.day, self.today = str(s.get("day") or ""), int(s.get("today") or 0)
        except (OSError, ValueError, TypeError, AttributeError):
            self.wallets, self.jobs = {}, []

    def save_state(self):
        try:
            if len(self.wallets) > WALLETS_KEEP:   # the oldest wallets without a claim go first
                for k in sorted(self.wallets, key=lambda k: (bool(self.wallets[k].get("claims")), self.wallets[k].get("first", 0)))[:len(self.wallets) - WALLETS_KEEP]:
                    del self.wallets[k]
            tmp = self.state_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"wallets": self.wallets, "jobs": self.jobs, "day": self.day, "today": self.today}, f, separators=(",", ":"))
            os.replace(tmp, self.state_path)
        except OSError as exc:
            log.warning("cannot write %s: %r", self.state_path, exc)

    def wallet(self, pk: str) -> dict:
        w = self.wallets.get(pk)
        if w is None:
            w = self.wallets[pk] = {"first": int(self.clock()), "claims": {}, "dust": []}
        return w

    def budget(self) -> bool:
        d = dt.datetime.utcfromtimestamp(self.clock()).strftime("%Y-%m-%d")
        if d != self.day:
            self.day, self.today = d, 0
        return self.today < DAILY

    # ---------- what the relay saw ----------
    def saw(self, tx: dict, tx_hash: str | None):
        """A signed transaction went through the relay to the node (relay.py wallet). A claim is a user_tx paying the
        drop 100 + chapter; other payments to the drop only put the wallet on the board."""
        if not self.ready or not isinstance(tx, dict) or tx.get("tx_type", "user_tx") != "user_tx":
            return
        drop = self.pk.get("drop")
        sender = str(tx.get("sender_pubkey") or "").lower()
        if sender in self.who or not sender:
            return
        for op in (tx.get("operations") or {}).get("1") or []:
            try:
                frm, to, amount = str(op[0]).lower(), str(op[1]).lower(), int(op[2])
            except (TypeError, ValueError, IndexError):
                continue
            if to != drop or frm != sender:
                continue
            w = self.wallet(sender)
            ch = amount - CLAIM_BASE
            if 1 <= ch <= CHAPTERS and str(ch) not in w["claims"] and tx_hash:
                w["claims"][str(ch)] = {"hash": tx_hash, "at": int(self.clock()), "paid": None}
                self.jobs.append({"kind": "share", "to": sender, "ch": ch, "claim": tx_hash, "not_before": 0, "asked": 0})
                if ch == 1:
                    self.jobs.append({"kind": "mark", "to": sender, "ch": 1, "claim": tx_hash, "not_before": 0, "asked": 0})
                log.info("no memo: claim chapter %d from %s", ch, short(sender))
            self.save_state()

    # ---------- sending ----------
    def build_pay(self, key: str, wallet: str, amount: int, seq: int, tip: int, fee: int) -> dict:
        from py_ecc.bls import G2Basic
        pk = self.pk[key]
        tx = {"tx_type": "user_tx", "sender_pubkey": pk, "sequence_number": seq,
              "expiration_time": int(self.clock()) + 600, "expire_at_height": tip + 1000,
              "fee_limit": str(fee * 5), "operations": {"1": [[pk, wallet, str(amount)]]}}
        tx["signature"] = G2Basic.Sign(self.sk[key], hashlib.sha256(signing_bytes(tx)).digest()).hex()
        return tx

    async def send(self, key: str, wallet: str, amount: int, ask, gov) -> str | None:
        """One payment from the drop (or the lookalike) to the wallet; the hash when the node took it."""
        from island import base_fee
        pk = self.pk[key]
        st = await ask(f"getsequence {pk}")
        if not st or st.get("status") != "ok":
            return None
        d = st.get("data") or {}
        seq = max(int(d.get("sequence_number") or 0), self.next_seq.get(key, 0))
        tx = await asyncio.to_thread(self.build_pay, key, wallet, amount, seq, int(d.get("tip_height") or 0), base_fee(gov()))
        res = await ask("sendtx " + json.dumps(tx, separators=(",", ":")))
        self.last_send = self.clock()
        if bool(res) and res.get("status") == "ok" and (res.get("data") or {}).get("ok") is not False:
            self.next_seq[key] = seq + 1
            self.today += 1
            if self.on_tx:
                self.on_tx()
            return (res.get("data") or {}).get("tx_hash") or "sent"
        self.next_seq.pop(key, None)
        why = json.dumps((res or {}).get("error") or res)
        log.info("no memo %s to %s refused: %.160s", key, short(wallet), why)
        if key == "drop" and "FUNDS" in why.upper():
            await self.fill_drop(ask, gov)
        return None

    async def balance(self, key: str, ask) -> int | None:
        """The wallet's balance on the chain; None when the node did not say."""
        m = await ask(f"getbalance {self.pk[key]}")
        if not m or m.get("status") != "ok":
            return None
        try:
            return int((m.get("data") or {}).get("balance") or 0)
        except (TypeError, ValueError):
            return None

    async def fill_drop(self, ask, gov) -> bool:
        """The drop pays shares, so its balance is never 0 and the testnet's faucet never fills it (a wallet with
        balance 0 pays from the faucet; one that received before it ever sent does not). A bank wallet does instead:
        a fresh key each time, its first payment comes from the faucet and goes to the drop. True when it was sent."""
        from py_ecc.bls import G2Basic
        from py_ecc.optimized_bls12_381 import curve_order
        sk = secrets.randbelow(curve_order - 2) + 1
        self.sk["bank"], self.pk["bank"] = sk, G2Basic.SkToPk(sk).hex()
        self.who[self.pk["bank"]] = "nomemo"
        self.next_seq.pop("bank", None)
        if self.on_ready:
            try:
                self.on_ready()
            except Exception as exc:
                log.warning("no memo: on_ready failed: %r", exc)
        h = await self.send("bank", self.pk["drop"], TOPUP, ask, gov)
        if h:
            self.topup = {"hash": h, "at": int(self.clock())}
            log.info("no memo: the bank fills the drop with %d (%s)", TOPUP, h[:12])
        return bool(h)

    async def drop_ready(self, amount: int, ask, gov):
        """True when the drop can pay amount now, "filled" when the bank just sent it money (one top-up at a time),
        False while a top-up is still unsealed."""
        now = self.clock()
        if self.topup:
            if now - self.topup["at"] < TOPUP_WAIT and await self.sealed(self.topup["hash"], ask) is not True:
                return False
            self.topup = None
        bal = await self.balance("drop", ask)
        if bal is None or bal >= amount + 2 * base_fee_of(gov):
            return True
        return "filled" if await self.fill_drop(ask, gov) else False

    async def sealed(self, tx_hash: str, ask) -> bool | None:
        """True once the chain has the claim in a block, False when it never will, None while it is pending."""
        m = await ask(f"gettxstatus {tx_hash}")
        if not m or m.get("status") != "ok":
            return None
        d = m.get("data") or {}
        st = str(d.get("status") or d.get("state") or "").lower()
        if d.get("block_number") is not None or any(x in st for x in ("confirmed", "included", "mined", "sealed", "applied")):
            return True
        if any(x in st for x in ("reject", "fail", "dropped", "expired", "invalid", "unknown", "not_found")):
            return False
        return None

    async def step(self, ask, gov) -> bool:
        """Called in the island bot's free slots. Sends at most one transaction; True if it did."""
        if not self.enabled or not self.ready or not self.jobs:
            return False
        now = self.clock()
        if now - self.last_send < GAP or not self.budget():
            return False
        for j in list(self.jobs):
            if j.get("not_before", 0) > now:
                continue
            w = self.wallet(j["to"])
            c = w["claims"].get(str(j["ch"]))
            if j["kind"] in ("share", "mark"):
                if not c or now - c["at"] > CLAIM_DAYS * 86400:
                    self.jobs.remove(j)
                    continue
                ok = await self.sealed(j["claim"], ask)
                if ok is None:
                    j["asked"] = j.get("asked", 0) + 1
                    j["not_before"] = now + QUIET
                    if j["asked"] > TRIES:
                        self.jobs.remove(j)
                        log.info("no memo: claim %s never sealed; forgotten", j["claim"][:12])
                    self.save_state()
                    return False
                if ok is False:
                    self.jobs.remove(j)
                    w["claims"].pop(str(j["ch"]), None)
                    self.save_state()
                    continue
                amount = SHARE if j["kind"] == "share" else MARK
                ready = await self.drop_ready(amount, ask, gov)
                if ready is not True:
                    self.save_state()
                    return ready == "filled"
                h = await self.send("drop", j["to"], amount, ask, gov)
                self.jobs.remove(j)
                if h:
                    c["paid"] = c.get("paid") or {}
                    c["paid"][j["kind"]] = {"amount": amount, "hash": h, "at": int(now)}
                    if j["kind"] == "share" and j["ch"] == 1 and self.tracer and not w["dust"] and "shadow" in self.pk:
                        self.jobs.append({"kind": "dust", "to": j["to"], "ch": 1, "claim": j["claim"], "not_before": now + DUST_AFTER, "asked": 0})
                else:   # the node said no (or nothing): once more in a while
                    j["asked"] = j.get("asked", 0) + 1
                    j["not_before"] = now + 120
                    if j["asked"] <= TRIES:
                        self.jobs.append(j)
                self.save_state()
                return bool(h)
            if j["kind"] == "dust":
                self.jobs.remove(j)
                if w["dust"] or not self.tracer:
                    self.save_state()
                    continue
                h = await self.send("shadow", j["to"], DUST, ask, gov)
                if h:
                    w["dust"].append({"from": self.pk["shadow"], "amount": DUST, "hash": h, "at": int(now)})
                elif j.get("asked", 0) < 3:
                    j["asked"] = j.get("asked", 0) + 1
                    j["not_before"] = now + 300
                    self.jobs.append(j)
                self.save_state()
                return bool(h)
        return False

    # ---------- what pages see ----------
    def board(self) -> dict:
        ranks = {name: 0 for name, _ in RANKS}
        claims = [0] * CHAPTERS
        for w in self.wallets.values():
            n = sum(1 for c in w.get("claims", {}).values() if c.get("paid"))
            for name, need in RANKS:
                if n >= need:
                    rank = name
            ranks[rank] += 1
            for ch, c in w.get("claims", {}).items():
                if c.get("paid") and ch.isdigit() and 1 <= int(ch) <= CHAPTERS:
                    claims[int(ch) - 1] += 1
        return {"wallets": len(self.wallets), "ranks": ranks, "claims": claims}

    def snapshot(self) -> dict:
        return {"simulated": True, "enabled": bool(self.enabled), "ready": self.ready, "making_wallets": self.making, "tracer": bool(self.tracer),
                "drop": self.pk.get("drop"), "drop_short": short(self.pk.get("drop", "")), "share": SHARE, "mark": MARK, "claim_base": CLAIM_BASE,
                "board": self.board(), "waiting": len(self.jobs), "filling": bool(self.topup), "today": self.today, "limits": {"daily": DAILY, "gap": GAP, "claim_days": CLAIM_DAYS}}

    def wallet_view(self, pk: str) -> dict:
        w = self.wallets.get(pk) or {"claims": {}, "dust": []}
        return {"wallet": pk, "claims": w.get("claims", {}), "dust": w.get("dust", []), "drop": self.pk.get("drop"), "enabled": bool(self.enabled)}

    def route(self, path: str, query: str = "") -> dict | None:
        if path == "/nomemo":
            return self.snapshot()
        if path.startswith("/nomemo/wallet/"):
            pk = path[len("/nomemo/wallet/"):].lower()
            if len(pk) != 96 or any(c not in "0123456789abcdef" for c in pk):
                return {"error": "not an address"}
            return self.wallet_view(pk)
        return None


if __name__ == "__main__":
    if sys.argv[1:2] == ["keys"] and len(sys.argv) > 2:
        logging.basicConfig(level=logging.INFO)
        make_keys(sys.argv[2])
        sys.exit(0)
    print(__doc__)
    sys.exit(2)

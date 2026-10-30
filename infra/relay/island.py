"""White Rabbit Key's island bot: the rival candidates' moves as real test transactions.

The game (tauhud.com/rabbit/) runs in the visitor's browser. The visitor's own moves can be signed by
their own test wallet in that browser. The three rivals they play against have no browser: when one of
them makes a move that goes into the island's Book (a law proposed, a pact, a line bought on the radio,
an embassy's money taken, a vote), the page asks this relay with `islandmove <candidate> <kind>`, and
this module sends 1 test AGRS from that candidate's campaign wallet to the island council's address on
Tau Testnet Alpha. Test AGRS have no value.

The four campaign wallets are made here, once, on first start: their keys are written to
ISLAND_KEYS_PATH (inside the relay's data volume, mode 0600) and never leave the server. They are not
the ballot boxes the visitors vote into (rabbit/game.js ADDR), so the bot never changes the visitors'
count. A wallet whose balance on the chain is 0 pays from the testnet's faucet, so they need no funding.

Limits, so a page that is left open or a script cannot flood the testnet: a few moves per address per
minute, a queue of at most QUEUE_MAX, at most ISLAND_DAILY transactions per UTC day, one every SPACING
seconds. Moves over a limit are not sent, and the answer says so. GET /island shows the wallets, the
day's count and the last transactions, so anyone can follow them on the chain.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import secrets
import time
from collections import deque

log = logging.getLogger("island")

COUNCIL = "96179f47d33ab65d9922c5652d7686f9e6be9d36ef4b9e9e04bdaac25b6e30d01928182c16da7aaa6dc954cccb88b62b"
CANDIDATES = ("marisol", "tobias", "baako", "hana")
KINDS = ("law", "down", "refused", "talk", "lie", "fact", "deal", "pact", "broke", "vote")
QUEUE_MAX = 60
SPACING = 2.5            # seconds between two transactions
IP_BURST, IP_REFILL = 12, 1 / 5   # per address: 12 at once, then one every 5 s
FEE_RE = re.compile(r"o9\[t\]:bv\[24\]\s*=\s*\{\s*#x([0-9a-fA-F]+)")


def signing_bytes(tx: dict) -> bytes:
    """The node's preimage for a user_tx (tau-testnet consensus/tx_signing.py, signing_message_bytes)."""
    d = {k: tx[k] for k in ("sender_pubkey", "sequence_number", "expiration_time", "fee_limit")}
    d["tx_type"] = tx.get("tx_type", "user_tx")
    if tx.get("expire_at_height") is not None:
        d["expire_at_height"] = tx["expire_at_height"]
    d["operations"] = tx.get("operations", {})
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


def base_fee(gov: dict) -> int:
    m = FEE_RE.search(str((gov or {}).get("consensus_rules") or ""))
    return int(m.group(1), 16) if m else 10


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


class Island:
    def __init__(self, path: str | None = None, daily: int | None = None, clock=time.time, enabled: bool | None = None):
        self.path = path or os.environ.get("ISLAND_KEYS_PATH", "/data/island.keys")
        self.daily = int(daily if daily is not None else os.environ.get("ISLAND_DAILY", "1500"))
        self.enabled = (os.environ.get("ISLAND_ENABLED", "1") != "0") if enabled is None else enabled
        self.clock = clock
        self.sk: dict[str, int] = {}
        self.pk: dict[str, str] = {}
        self.queue: deque = deque()
        self.ips: dict[str, Bucket] = {}
        self.day = int(clock() // 86400)
        self.today = 0
        self.recent: deque = deque(maxlen=30)
        self.next_seq: dict[str, int] = {}
        if self.enabled:
            try:
                self.load()
            except Exception as exc:   # the relay keeps working without the bot
                log.warning("island bot off: %r", exc)
                self.enabled = False

    # ---------- the campaign wallets ----------
    def load(self):
        from py_ecc.bls import G2Basic
        keys = {}
        if os.path.exists(self.path):
            with open(self.path) as f:
                keys = json.load(f)
        if any(c not in keys for c in CANDIDATES):
            for c in CANDIDATES:
                if c not in keys:
                    sk = G2Basic.KeyGen(secrets.token_bytes(32))
                    sk = sk if isinstance(sk, int) else int.from_bytes(bytes(sk), "big")
                    keys[c] = sk.to_bytes(32, "big").hex()
            tmp = self.path + ".tmp"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump(keys, f)
            os.replace(tmp, self.path)
        for c in CANDIDATES:
            self.sk[c] = int(keys[c], 16)
            self.pk[c] = G2Basic.SkToPk(self.sk[c]).hex()

    # ---------- a move asked for by a page ----------
    def accept(self, who: str, kind: str, ip: str) -> tuple[bool, dict | str]:
        if not self.enabled:
            return False, "The island bot is switched off on this relay."
        if who not in CANDIDATES or kind not in KINDS:
            return False, "Usage: islandmove <marisol|tobias|baako|hana> <" + "|".join(KINDS) + ">"
        now = self.clock()
        self.roll(now)
        if len(self.ips) > 5000:
            self.ips.clear()
        b = self.ips.setdefault(ip, Bucket(IP_BURST, IP_REFILL, now))
        if not b.take(now):
            return True, {"queued": False, "why": "busy", "wallet": self.pk[who]}
        if self.today + len(self.queue) >= self.daily:
            return True, {"queued": False, "why": "daily", "wallet": self.pk[who]}
        if len(self.queue) >= QUEUE_MAX:
            return True, {"queued": False, "why": "full", "wallet": self.pk[who]}
        self.queue.append((who, kind, now))
        return True, {"queued": True, "ahead": len(self.queue) - 1, "wallet": self.pk[who]}

    def roll(self, now: float):
        d = int(now // 86400)
        if d != self.day:
            self.day, self.today = d, 0

    def build(self, who: str, seq: int, tip: int, fee: int) -> dict:
        """One signed transfer of 1 test AGRS from the candidate's campaign wallet to the council."""
        from py_ecc.bls import G2Basic
        pk = self.pk[who]
        tx = {"tx_type": "user_tx", "sender_pubkey": pk, "sequence_number": seq,
              "expiration_time": int(self.clock()) + 600, "expire_at_height": tip + 1000,
              "fee_limit": str(fee * 5), "operations": {"1": [[pk, COUNCIL, "1"]]}}
        tx["signature"] = G2Basic.Sign(self.sk[who], hashlib.sha256(signing_bytes(tx)).digest()).hex()
        return tx

    # ---------- sending, one at a time ----------
    async def run(self, ask, gov):
        """ask(command) -> envelope dict or None (the relay's upstream); gov() -> the cached governance data."""
        if not self.enabled:
            return
        while True:
            if not self.queue:
                await asyncio.sleep(1)
                continue
            who, kind, at = self.queue.popleft()
            try:
                await self.send(who, kind, ask, gov)
            except Exception as exc:   # one bad answer must not stop the bot
                log.warning("island move %s %s failed: %r", who, kind, exc)
            await asyncio.sleep(SPACING)

    async def send(self, who: str, kind: str, ask, gov) -> dict | None:
        pk = self.pk[who]
        st = await ask(f"getsequence {pk}")
        if not st or st.get("status") != "ok":
            return None
        d = st.get("data") or {}
        seq = max(int(d.get("sequence_number") or 0), self.next_seq.get(who, 0))
        tip = int(d.get("tip_height") or 0)
        tx = await asyncio.to_thread(self.build, who, seq, tip, base_fee(gov()))
        res = await ask("sendtx " + json.dumps(tx, separators=(",", ":")))
        ok = bool(res) and res.get("status") == "ok" and (res.get("data") or {}).get("ok") is not False
        if ok:
            self.next_seq[who] = seq + 1
            self.today += 1
            self.recent.appendleft({"by": who, "kind": kind, "hash": (res.get("data") or {}).get("tx_hash"), "at": int(self.clock())})
        else:
            self.next_seq.pop(who, None)   # read the sequence from the node again next time
            log.info("island move %s %s refused: %.160s", who, kind, json.dumps((res or {}).get("error") or res))
        return res

    # ---------- GET /island ----------
    def route(self, path: str) -> dict | None:
        if path != "/island":
            return None
        self.roll(self.clock())
        return {"enabled": self.enabled, "council": COUNCIL, "wallets": self.pk, "today": self.today, "daily": self.daily,
                "queued": len(self.queue), "recent": list(self.recent)}

"""White Rabbit Key's island bot: the rival candidates' moves as real test transactions.

The game (tauhud.com/rabbit/) runs in the visitor's browser. The visitor's own moves can be signed by
their own test wallet in that browser. The three rivals they play against have no browser: when one of
them makes a move that goes into the island's Book (a law proposed, a pact, a line bought on the radio,
an embassy's money taken, a vote), the page asks this relay with `islandmove <candidate> <kind>`, and
this module sends 1 test AGRS from that candidate's campaign wallet on Tau Testnet Alpha to the till of the
place where the move happened (PLACES: the council's chest for laws, pacts and votes, the market for a talk,
the station for a radio line, which costs 25, an embassy for its money). Test AGRS have no value.

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
# each place's till (rabbit/game.js TILL): a move pays the place it happens at; "hall" is the council itself
PLACES = {
    "hall": COUNCIL,
    "market": "89798ff443b446b8392097e50bb61f383f24ed60f45b4f592e6b9d5356056e90698e7114f17692bdd2539bce24d73ac2",
    "radio": "b6ef83b962c9e8be7345050bc34de31bc8996cfc3782947db4509f48750b53640b19d7211c591bc2e4e16d2b148bf945",
    "north": "b3909c612e07036be9504e3be10eef3b1483e0c1c7be4d05950ccb373f06292f186709c7344e5aa7b83501ce7f1d48af",
    "south": "a752d4269c95abd44c6ec855ce3513f6ce8b3a8c94f58621ee1596ceb728a69aa329a541a9f75a188fdfff92ad6c045d",
    "bar": "87208cfd4313f66ec1baa2021ff0fdd5667285be5396a4a83480efc18d80ba3c2e41504d2bcd2b01a8d37a6cab54cd05",
    "book": "98e2aa832d79c1689b6b3190d45e0c2319838c0f58293e6a837d606548f2c1e797b20550e0c5230a7cebbc13f74e849f",
    "pier": "8ed60ef9cc93ec996d7eeac725539e720f86b701bdb7ac646434d177690e48869dbfdedc759c930dc88f1e3cd315c58b",
    "school": "98e8a33fa10f0dca59bb6fe8c9d14fb2e9b6be5cbeb95d862fc4eb9ad2d5957617f8b998757f9947065cd76c05a82578",
    "dive": "899220e0128f24e1666fdaf53809c16854bc37cfcac3aa9a887e7e0205fff14de93c5b1272e1c5204ad4c1f1ee7c11de",
    "works": "816cdcda9accef093332ca8356f87fb1a40aa612d999b55d8cc7229865508ad09bd1214ba6f4b16a6dc8b64d03fa852d",
    "camp": "81a080eed60d737f73623b80d3b1dcad85d37b5a5a4d5b0ba60c3c2379b995d470c8c2d3db2f92b803b7feb215091d16",
    "ship": "83546df43205836667fc104c6a56549b2b0c0cd5fd0bc188ad55e96ce656c8220991325fdd49ef8a5549bb7ca9d1cb3e",
    "ama": "8ffb79523db95c885e3267633767246dda76cc9378804b02328835ba45667d7012be8b79f32e497d1822d1df96726d3d",
    "canoe": "96e0c6d33c1848fa6a2355ababc5f66a7a8121c81a05f923c3e60d645f0110fe28a81db5176f750adec25b26b8746bf9",
    "stone": "897178ec1333edd5d3cb27f5746976e6cb8fd0d07360a8dcdfccd1f0a90d15f5a2f8b24616acb5ebfa360b86bc025175",
    "drums": "82a45ff8fd1bbba834c5c9f89e8ebb712935f83aa2709cdda051deebec517483e73fc6eeb997ebbaf2dc582a2eea56dc",
    "circle": "a974149276f73fa2021068c89521bc68e8877cbfdb7d75b348951269bc3ab6c0677997f31bdbb1d28c95dc3aacacd34e",
    "grotto": "9266b7dbca59d06c60517e815e32169aaba70056101d394c6ab851a99925f18e23da324cf0c73ab5fe27c951c8bb024e",
}
RADIO_LINE = 25          # a line bought on Radio Coco costs what it costs in the game (rabbit/game.js RUMOUR)
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
    def accept(self, who: str, kind: str, ip: str, at: str = "hall") -> tuple[bool, dict | str]:
        if not self.enabled:
            return False, "The island bot is switched off on this relay."
        if who not in CANDIDATES or kind not in KINDS or at not in PLACES:
            return False, "Usage: islandmove <marisol|tobias|baako|hana> <" + "|".join(KINDS) + "> [place]"
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
        self.queue.append((who, kind, now, at))
        return True, {"queued": True, "ahead": len(self.queue) - 1, "wallet": self.pk[who]}

    def roll(self, now: float):
        d = int(now // 86400)
        if d != self.day:
            self.day, self.today = d, 0

    def build(self, who: str, seq: int, tip: int, fee: int, at: str = "hall") -> dict:
        """One signed transfer from the candidate's campaign wallet to the place's till: 1 test AGRS, a radio line 25."""
        from py_ecc.bls import G2Basic
        pk = self.pk[who]
        amount = RADIO_LINE if at == "radio" else 1
        tx = {"tx_type": "user_tx", "sender_pubkey": pk, "sequence_number": seq,
              "expiration_time": int(self.clock()) + 600, "expire_at_height": tip + 1000,
              "fee_limit": str(fee * 5), "operations": {"1": [[pk, PLACES.get(at, COUNCIL), str(amount)]]}}
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
            who, kind, _, at = self.queue.popleft()
            try:
                await self.send(who, kind, ask, gov, at)
            except Exception as exc:   # one bad answer must not stop the bot
                log.warning("island move %s %s failed: %r", who, kind, exc)
            await asyncio.sleep(SPACING)

    async def send(self, who: str, kind: str, ask, gov, at: str = "hall") -> dict | None:
        pk = self.pk[who]
        st = await ask(f"getsequence {pk}")
        if not st or st.get("status") != "ok":
            return None
        d = st.get("data") or {}
        seq = max(int(d.get("sequence_number") or 0), self.next_seq.get(who, 0))
        tip = int(d.get("tip_height") or 0)
        tx = await asyncio.to_thread(self.build, who, seq, tip, base_fee(gov()), at)
        res = await ask("sendtx " + json.dumps(tx, separators=(",", ":")))
        ok = bool(res) and res.get("status") == "ok" and (res.get("data") or {}).get("ok") is not False
        if ok:
            self.next_seq[who] = seq + 1
            self.today += 1
            self.recent.appendleft({"by": who, "kind": kind, "place": at, "hash": (res.get("data") or {}).get("tx_hash"), "at": int(self.clock())})
        else:
            self.next_seq.pop(who, None)   # read the sequence from the node again next time
            log.info("island move %s %s refused: %.160s", who, kind, json.dumps((res or {}).get("error") or res))
        return res

    # ---------- GET /island ----------
    def route(self, path: str) -> dict | None:
        if path != "/island":
            return None
        self.roll(self.clock())
        return {"enabled": self.enabled, "council": COUNCIL, "places": PLACES, "wallets": self.pk, "today": self.today, "daily": self.daily,
                "queued": len(self.queue), "recent": list(self.recent)}

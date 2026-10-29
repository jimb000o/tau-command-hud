"""Wallet transactions for the simulation (GET /sim/tx, GET /sim/wallet).

In simulation mode the testnet wallet (/wallet/) signs its transactions exactly as for Tau Testnet Alpha, and sends them
here instead of to the node: payments, splits, a way back, co-signing, rules, rule offers, votes. Each one gets the block
of the simulated chain it lands in, a few blocks ahead, and every browser reads the day's list (GET /sim/wallet) and puts
it into its own copy of the chain (assets/sim.js) at that block. So a payment from one visitor's wallet shows in another
visitor's Explorer, their wallet sees it arrive, and a rule offered to them waits in their Activity.

Nothing here touches the real testnet. The transaction's shape is checked strictly and nothing else is kept: hex keys and
hashes, whole amounts, fixed transaction types, a rule text of Tau tokens only, no free text. The signature is not stored.
The chain itself decides what lands (enough balance, a real offer to accept); this module only fixes when.

GET /sim/tx?tx=<json>&voter=<token>&a=<i>&b=<j>&c=<k>   take one signed transaction: {ok, i, hash, h} or {ok: false, error, why}
GET /sim/wallet?from=<i>                                the day's transactions from index i on: {day, count, txs: [{i, h, ts, hash, by, tx}]}

Everything starts over at 00:00 UTC with the simulated chain.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from urllib.parse import parse_qs

log = logging.getLogger("relay.simwallet")

DAY = 86400
PACE = 8                 # seconds per simulated block (assets/sim.js PACE)
LEAD = 6                 # a transaction lands six blocks (about 48 s) after it was sent, so every page learns of it first
DAY_MAX = int(os.environ.get("SIM_WALLET_PER_DAY", 1500))
PER_SENDER_DAY = int(os.environ.get("SIM_WALLET_PER_SENDER", 80))
PER_IP_DAY = int(os.environ.get("SIM_WALLET_PER_IP", 200))
SENDERS_PER_IP = 5       # different wallet accounts one address may send from in a day
PAGE = 200               # transactions per answer of /sim/wallet
BURST, REFILL = 6.0, 0.1
TX_MAX = 7000            # characters of the transaction's JSON
MAX_AMOUNT = 2 ** 24 - 1
MAX_SPLIT = 6

HEX = lambda n: re.compile(rf"^[0-9a-f]{{{n}}}$")  # noqa: E731
KEY, HASH, SIG, TOKEN = HEX(96), HEX(64), HEX(192), HEX(32)
INDEX = re.compile(r"^\d{1,3}$")
RULE_MAX = 3000
# a rule may hold Tau tokens only, so nothing but a rule reaches other visitors (simprops.py has the network-rule twin)
RULE_TOKEN = re.compile(r"\s+|always\b|bv\b|t\b|[io]\d{1,2}\b|#x[0-9a-fA-F]{1,96}\b|#b[01]{1,64}\b|\d{1,20}\b"
                        r"|<->|->|&&|\|\||!=|<=|>=|<<|>>|[=<>!&|^+\-*/%'(){}\[\]:?.]")
COMMON = {"tx_type", "sender_pubkey", "sequence_number", "expiration_time", "fee_limit", "expire_at_height", "signature"}
# the fields each type may carry besides COMMON: the signed fields of /wallet/ (SIGNED there), nothing more
FIELDS = {
    "user_tx": {"operations"},
    "consensus_rule_vote": {"update_id", "approve"},
    "rule_offer": {"recipient_pubkey", "rule_text"},
    "rule_offer_accept": {"offer_id", "rule_text"},
    "rule_offer_reject": {"offer_id"},
    "approval_request": {"recipient_pubkey", "amount", "approvers", "custom_inputs"},
    "transfer_vote": {"request_id", "approve", "reason"},
    "retractable_transfer": {"recipient_pubkey", "amount", "release_at_height", "release_at_time"},
    "retract_transfer": {"retractable_id"},
}


def rule_ok(text) -> str | None:
    """None if `text` is a personal rule (o5) made of Tau tokens, else the reason."""
    if not isinstance(text, str) or not text or len(text) > RULE_MAX:
        return f"a rule of 1 to {RULE_MAX} characters"
    pos = 0
    while pos < len(text):
        m = RULE_TOKEN.match(text, pos)
        if not m or m.end() == pos:
            return "only Tau rule tokens"
        pos = m.end()
    body = " ".join(text.split())
    if not re.match(r"^always\s*\(.*\)\s*\.$", body) or body.count("always") != 1:
        return "one unit: always ( … )."
    if not re.search(r"\bo5\[t\]", body) or re.search(r"\bo(?!5\b)\d{1,2}\[", body):
        return "a personal rule sets o5 and nothing else"
    return None


def whole(v, lo=0, hi=10 ** 12) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi


def amount_ok(v) -> bool:
    """Amounts travel as whole numbers or as their decimal strings (user_tx keeps them as strings)."""
    if isinstance(v, str):
        return bool(re.fullmatch(r"[1-9]\d{0,7}", v)) and int(v) <= MAX_AMOUNT
    return whole(v, 1, MAX_AMOUNT)


def check_tx(tx) -> str | None:
    """None if `tx` is a wallet transaction the simulation takes, else the reason."""
    if not isinstance(tx, dict):
        return "a JSON object"
    kind = tx.get("tx_type")
    if kind not in FIELDS:
        return "an unknown transaction type"
    extra = set(tx) - COMMON - FIELDS[kind]
    if extra:
        return "unexpected fields: " + ", ".join(sorted(extra))[:80]
    sender = tx.get("sender_pubkey")
    if not (isinstance(sender, str) and KEY.match(sender)):
        return "sender_pubkey: 96 hex digits"
    if not (whole(tx.get("sequence_number"), 0, 10 ** 6) and whole(tx.get("expiration_time"))):
        return "sequence_number and expiration_time: whole numbers"
    if "expire_at_height" in tx and not whole(tx["expire_at_height"], 0, 10 ** 7):
        return "expire_at_height: a whole number"
    if not (isinstance(tx.get("fee_limit"), str) and re.fullmatch(r"\d{1,7}", tx["fee_limit"])):
        return "fee_limit: a number as text"
    if not (isinstance(tx.get("signature"), str) and SIG.match(tx["signature"])):
        return "signature: 192 hex digits"
    key = lambda f: isinstance(tx.get(f), str) and bool(KEY.match(tx[f]))  # noqa: E731
    h64 = lambda f: isinstance(tx.get(f), str) and bool(HASH.match(tx[f]))  # noqa: E731
    if kind == "user_tx":
        ops = tx.get("operations")
        if not isinstance(ops, dict) or not ops or set(ops) - {"0", "1"}:
            return "operations: a rule (\"0\") and/or transfers (\"1\")"
        if "0" in ops and rule_ok(ops["0"]):
            return "rule: " + rule_ok(ops["0"])
        if "1" in ops:
            tr = ops["1"]
            if not isinstance(tr, list) or not 1 <= len(tr) <= MAX_SPLIT:
                return f"1 to {MAX_SPLIT} transfers"
            for t in tr:
                if not (isinstance(t, list) and len(t) == 3 and t[0] == sender and isinstance(t[1], str) and KEY.match(t[1]) and amount_ok(t[2])):
                    return "a transfer is [sender, recipient, amount]"
    elif kind == "consensus_rule_vote":
        if not (h64("update_id") and isinstance(tx.get("approve"), bool)):
            return "update_id and approve"
    elif kind == "rule_offer":
        if not key("recipient_pubkey") or rule_ok(tx.get("rule_text")):
            return "recipient_pubkey and a rule"
    elif kind == "rule_offer_accept":
        if not h64("offer_id") or rule_ok(tx.get("rule_text")):
            return "offer_id and the rule"
    elif kind == "rule_offer_reject":
        if not h64("offer_id"):
            return "offer_id"
    elif kind == "approval_request":
        ap = tx.get("approvers")
        if not (key("recipient_pubkey") and amount_ok(tx.get("amount")) and isinstance(ap, dict) and 1 <= len(ap) <= 8
                and all(isinstance(s, str) and re.fullmatch(r"1[89]|2[0-5]", s) and isinstance(p, str) and KEY.match(p) for s, p in ap.items())
                and tx.get("custom_inputs", {}) == {}):
            return "recipient, amount and 1 to 8 co-signers in slots 18 to 25"
    elif kind == "transfer_vote":
        if not (h64("request_id") and isinstance(tx.get("approve"), bool) and tx.get("reason", "") == ""):
            return "request_id and approve, no reason text"
    elif kind == "retractable_transfer":
        rt = tx.get("release_at_time")
        if not (key("recipient_pubkey") and amount_ok(tx.get("amount")) and whole(tx.get("release_at_height"), 0, 10 ** 7) and (rt is None or whole(rt))):
            return "recipient, amount and a release block"
    elif kind == "retract_transfer":
        if not h64("retractable_id"):
            return "retractable_id"
    return None


def head_at(t: float) -> int:
    """The simulated chain's height at time t (assets/sim.js seals block n at day start + 8 n)."""
    return int((t - (t // DAY) * DAY) // PACE)


class SimWallet:
    def __init__(self, path: str | None = None, clock=time.time):
        self.path = path if path is not None else os.environ.get("SIMWALLET_PATH", "/data/simwallet.json")
        self.clock = clock
        self.day = -1
        self.txs: list[dict] = []
        self.hashes: set[str] = set()
        self.by_sender: dict[str, int] = {}
        self.by_ip: dict[str, int] = {}           # memory only
        self.ip_senders: dict[str, set] = {}      # memory only
        self.buckets: dict[str, list] = {}        # memory only, apart from the socket's and the votes' buckets
        self._load()

    # ---------- storage ----------
    def _load(self):
        try:
            with open(self.path) as f:
                st = json.load(f)
            if isinstance(st, dict) and st.get("day") == int(self.clock() // DAY) and isinstance(st.get("txs"), list):
                self.day, self.txs = st["day"], st["txs"]
                self.hashes = {x["hash"] for x in self.txs}
                for x in self.txs:
                    s = x["tx"]["sender_pubkey"]
                    self.by_sender[s] = self.by_sender.get(s, 0) + 1
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, KeyError) as exc:
            log.warning("cannot read %s: %r; starting the day's wallet transactions afresh", self.path, exc)
            self.txs, self.hashes, self.by_sender = [], set(), {}
        self._roll()

    def _save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"day": self.day, "txs": self.txs}, f, separators=(",", ":"))
            os.replace(tmp, self.path)
        except OSError as exc:
            if not getattr(self, "_warned", False):
                log.warning("cannot write %s: %r; wallet transactions live in memory only", self.path, exc)
                self._warned = True

    def _roll(self):
        d = int(self.clock() // DAY)
        if d != self.day:
            self.day, self.txs, self.hashes, self.by_sender, self.by_ip, self.ip_senders = d, [], set(), {}, {}, {}

    def count(self) -> int:
        self._roll()
        return len(self.txs)

    # ---------- taking a transaction ----------
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

    def take(self, raw: str, q: dict[str, str], ip: str) -> dict:
        self._roll()
        bad = lambda code, why: {"ok": False, "error": code, "why": why}  # noqa: E731
        if not raw or len(raw) > TX_MAX:
            return bad("bad", f"a transaction of up to {TX_MAX} characters")
        try:
            tx = json.loads(raw)
        except ValueError:
            return bad("bad", "a JSON object")
        why = check_tx(tx)
        if why:
            return bad("bad", why)
        by = [q.get(k, "") for k in ("a", "b", "c")]
        by = [int(x) for x in by] if all(INDEX.match(x) for x in by) else None
        digest = hashlib.sha256(raw.encode()).hexdigest()
        if digest in self.hashes:
            x = next(x for x in self.txs if x["hash"] == digest)
            return {"ok": True, "i": x["i"], "hash": digest, "h": x["h"], "again": True}
        sender = tx["sender_pubkey"]
        now = self.clock()
        h = head_at(now) + LEAD
        if (self.day * DAY) + h * PACE > (self.day + 1) * DAY - 60:
            return bad("late", "too close to midnight UTC, when the simulated chain starts over")
        if len(self.txs) >= DAY_MAX:
            return bad("full", "the simulation takes no more wallet transactions today; it starts over at 00:00 UTC")
        seen = self.ip_senders.setdefault(ip, set())
        if (self.by_sender.get(sender, 0) >= PER_SENDER_DAY or self.by_ip.get(ip, 0) >= PER_IP_DAY
                or (sender not in seen and len(seen) >= SENDERS_PER_IP)):
            return bad("limit", f"{PER_SENDER_DAY} simulated transactions a day per account; the count starts over at 00:00 UTC")
        if not self._take(ip):
            return bad("rate", "a few seconds between transactions, please")
        tx = {k: v for k, v in tx.items() if k != "signature"}
        x = {"i": len(self.txs), "h": h, "ts": round(now, 1), "hash": digest, "by": by, "tx": tx}
        self.txs.append(x)
        self.hashes.add(digest)
        seen.add(sender)
        self.by_sender[sender] = self.by_sender.get(sender, 0) + 1
        self.by_ip[ip] = self.by_ip.get(ip, 0) + 1
        self._save()
        return {"ok": True, "i": x["i"], "hash": digest, "h": h}

    def page(self, start: int) -> dict:
        self._roll()
        start = max(0, start)
        return {"day": time.strftime("%Y-%m-%d", time.gmtime(self.day * DAY)), "count": len(self.txs), "txs": self.txs[start:start + PAGE]}

    # ---------- HTTP ----------
    def route(self, path: str, query: str, ip: str):
        """(status, body dict) for /sim/tx and /sim/wallet, None for any other path."""
        if path not in ("/sim/tx", "/sim/wallet"):
            return None
        q = {k: v[0] for k, v in parse_qs(query, keep_blank_values=True).items() if v}
        if path == "/sim/wallet":
            start = q.get("from", "0")
            return 200, self.page(int(start) if start.isdigit() else 0)
        res = self.take(q.get("tx", ""), q, ip)
        return (200 if res["ok"] else 429 if res["error"] == "rate" else 400 if res["error"] == "bad" else 409), res

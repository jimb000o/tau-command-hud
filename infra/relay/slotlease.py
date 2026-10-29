"""Fair turns on the testnet's personal-rule places (GET /lease, the socket command `leasetx`).

Tau Testnet Alpha lets only MAX_TIER_AUTHORS = 2 accounts hold a personal o5 rule at once (consensus/approvals.py in
tau-testnet 539d1e2). Whoever takes a place keeps it until they send the neutral clause, which frees it. So that a
visitor of the wallet (/wallet/) cannot hold a place for good, the wallet signs that neutral clause in advance, for the
account's next sequence number, right after the rule goes out, and leaves it here (`leasetx <json>`). The relay checks it
with the node once (checktx) and keeps it. When the turn is over it sends it (sendtx): 30 minutes after the turn began
when somebody is waiting for a place, otherwise after a day. A signed transaction carries no "valid from"; it stays
valid while its sequence number fits and its expire_at_height is ahead, so the wallet signs a fresh one whenever it sends
anything else. A holder who set a rule elsewhere has nothing deposited here and cannot be freed by us: the list says so.

Waiting: a visitor joins with their public key (GET /lease/wait?pk=…) and sees their place in line; nothing else is
kept. Entries leave when the account holds a place, on /lease/leave, or after three hours.

GET /lease[?pk=<96 hex>]   {places, taken, holders: [{addr, managed, until, status}], waiting, position, lease_s}
GET /lease/wait?pk=…       join the line           GET /lease/leave?pk=…   leave it
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from urllib.parse import parse_qs

log = logging.getLogger("relay.slotlease")

LEASE = int(os.environ.get("LEASE_SECONDS", 30 * 60))          # a turn while somebody waits
LEASE_MAX = int(os.environ.get("LEASE_MAX_SECONDS", 24 * 3600))   # a turn while nobody waits
WAIT_KEEP = 3 * 3600
WAIT_MAX = 500
PER_IP = 3                 # accounts one address may put in line
LEASES_MAX = 50
UNSEEN_DROP = 30 * 60      # a deposit whose account never shows as a holder is dropped after this
NEUTRAL = "always((o5[t]:bv[24]={#x000001}:bv[24]))."
KEY = re.compile(r"^[0-9a-f]{96}$")
SIG = re.compile(r"^[0-9a-f]{192}$")
FIELDS = {"tx_type", "sender_pubkey", "sequence_number", "expiration_time", "fee_limit", "expire_at_height", "signature", "operations"}


def whole(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def removal(raw: str, now: float) -> tuple[dict | None, str]:
    """The neutral-clause transaction in `raw`, or None and the reason."""
    if not raw or len(raw) > 4096:
        return None, "a transaction of up to 4096 characters"
    try:
        tx = json.loads(raw)
    except ValueError:
        return None, "a JSON object"
    if not isinstance(tx, dict) or set(tx) != FIELDS:
        return None, "exactly the fields of a signed user_tx"
    if tx["tx_type"] != "user_tx" or not isinstance(tx["operations"], dict) or set(tx["operations"]) != {"0"}:
        return None, "a user_tx whose only operation is a rule"
    if not isinstance(tx["operations"]["0"], str) or re.sub(r"\s+", "", tx["operations"]["0"]) != NEUTRAL:
        return None, "the neutral clause, which frees the place"
    if not (isinstance(tx["sender_pubkey"], str) and KEY.match(tx["sender_pubkey"]) and isinstance(tx["signature"], str) and SIG.match(tx["signature"])):
        return None, "sender_pubkey and signature in hex"
    if not (whole(tx["sequence_number"]) and whole(tx["expiration_time"]) and whole(tx["expire_at_height"])):
        return None, "whole numbers for sequence_number, expiration_time and expire_at_height"
    if not (isinstance(tx["fee_limit"], str) and re.fullmatch(r"\d{1,7}", tx["fee_limit"])):
        return None, "fee_limit: a number as text"
    if tx["expiration_time"] < now + LEASE_MAX + 3600:
        return None, "an expiration_time beyond the longest turn"
    return tx, ""


class SlotLease:
    def __init__(self, path: str | None = None, clock=time.time, places: int = 2):
        self.path = path if path is not None else os.environ.get("SLOTLEASE_PATH", "/data/slotlease.json")
        self.clock = clock
        self.places = places
        self.holders: list[str] = []
        self.seen = False                        # a first list of holders has come in
        self.leases: dict[str, dict] = {}        # addr -> {tx, seq, start, deposited, status, why, seen}
        self.waiting: dict[str, float] = {}      # pk -> joined
        self.by_ip: dict[str, set] = {}          # memory only: accounts one address put in line
        self._load()

    # ---------- storage ----------
    def _load(self):
        try:
            with open(self.path) as f:
                st = json.load(f)
            if isinstance(st, dict):
                self.leases = {a: v for a, v in (st.get("leases") or {}).items() if KEY.match(a) and isinstance(v, dict)}
                self.waiting = {a: float(t) for a, t in (st.get("waiting") or {}).items() if KEY.match(a)}
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError) as exc:
            log.warning("cannot read %s: %r; starting with no turns", self.path, exc)

    def _save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"leases": self.leases, "waiting": self.waiting}, f, separators=(",", ":"))
            os.replace(tmp, self.path)
        except OSError as exc:
            if not getattr(self, "_warned", False):
                log.warning("cannot write %s: %r; turns live in memory only", self.path, exc)
                self._warned = True

    # ---------- the chain's side ----------
    def set_holders(self, holders: list[str]):
        """Called after each read of the rule places: who holds one now."""
        now = self.clock()
        self.holders, self.seen = list(holders), True
        changed = False
        for a in list(self.leases):
            l = self.leases[a]
            if a in holders:
                if not l.get("seen"):
                    l["seen"], changed = now, True
            elif l.get("seen") or now - l["deposited"] > UNSEEN_DROP:
                del self.leases[a]   # the place is free again (by our removal or the holder's own), or the rule never came
                changed = True
        for pk in [p for p in self.waiting if p in holders or now - self.waiting[p] > WAIT_KEEP]:
            del self.waiting[pk]
            changed = True
        if changed:
            self._save()

    def until(self, l: dict, addr: str) -> float:
        others = any(p != addr for p in self.waiting)
        return l["start"] + (LEASE if others else LEASE_MAX)

    def due(self) -> list[tuple[str, str]]:
        """(addr, transaction) for each turn that is over and whose removal has not been sent yet."""
        now = self.clock()
        return [(a, l["tx"]) for a, l in self.leases.items()
                if l["status"] == "held" and a in self.holders and now >= self.until(l, a)]

    def sent(self, addr: str, ok: bool, why: str = ""):
        l = self.leases.get(addr)
        if not l:
            return
        l["status"], l["why"], l["sent"] = ("sent" if ok else "failed"), why[:200], self.clock()
        self._save()

    # ---------- the wallet's side ----------
    def check(self, raw: str) -> tuple[dict | None, str]:
        tx, why = removal(raw, self.clock())
        if tx and tx["sender_pubkey"] not in self.leases and len(self.leases) >= LEASES_MAX:
            return None, "too many turns are open; try again later"
        return tx, why

    def deposit(self, raw: str, tx: dict) -> dict:
        """Keep a removal the node has checked. A newer one replaces the older; the turn keeps its start."""
        now = self.clock()
        a = tx["sender_pubkey"]
        old = self.leases.get(a)
        start = old["start"] if old else now   # a fresh deposit never restarts a turn; only leaving the place does
        self.leases[a] = {"tx": raw, "seq": tx["sequence_number"], "start": start, "deposited": now, "status": "held", "why": "",
                          "seen": (old or {}).get("seen") or (now if a in self.holders else None)}
        self.waiting.pop(a, None)
        self._save()
        return {"ok": True, "until": round(self.until(self.leases[a], a)), "lease_s": LEASE, "max_s": LEASE_MAX}

    def wait(self, pk: str, ip: str = "") -> dict:
        if not KEY.match(pk):
            return {"ok": False, "error": "bad"}
        mine = self.by_ip.setdefault(ip, set())
        if pk not in mine and len(mine) >= PER_IP:
            return {"ok": False, "error": "limit"}
        if pk in self.holders:
            return {"ok": False, "error": "holder"}
        if pk not in self.waiting:
            if len(self.waiting) >= WAIT_MAX:
                return {"ok": False, "error": "full"}
            self.waiting[pk] = self.clock()
            mine.add(pk)
            if len(self.by_ip) > 10000:
                self.by_ip = {ip: mine}
            self._save()
        return {"ok": True, **self.status(pk)}

    def leave(self, pk: str) -> dict:
        if self.waiting.pop(pk, None) is not None:
            self._save()
        return {"ok": True, **self.status(pk)}

    def status(self, pk: str | None = None) -> dict:
        line = sorted(self.waiting, key=lambda p: self.waiting[p])
        rows = []
        for a in self.holders:
            l = self.leases.get(a)
            rows.append({"addr": a, "managed": bool(l), "until": round(self.until(l, a)) if l else None,
                         "status": l["status"] if l else None, "why": (l or {}).get("why") or None})
        out = {"places": self.places, "taken": min(len(self.holders), self.places), "holders": rows, "waiting": len(line),
               "lease_s": LEASE, "max_s": LEASE_MAX, "ready": self.seen}
        if pk and KEY.match(pk):
            out["position"] = line.index(pk) + 1 if pk in line else None
            l = self.leases.get(pk)
            if l:
                out["mine"] = {"until": round(self.until(l, pk)), "status": l["status"], "seq": l["seq"], "why": l.get("why") or None}
        return out

    # ---------- HTTP ----------
    def route(self, path: str, query: str, ip: str = ""):
        """(status, body) for /lease, /lease/wait and /lease/leave, None for any other path."""
        if path not in ("/lease", "/lease/wait", "/lease/leave"):
            return None
        q = {k: v[0] for k, v in parse_qs(query).items() if v}
        pk = q.get("pk", "").lower()
        if path == "/lease":
            return 200, self.status(pk or None)
        res = self.wait(pk, ip) if path == "/lease/wait" else self.leave(pk) if KEY.match(pk) else {"ok": False, "error": "bad"}
        return (200 if res["ok"] else 400), res

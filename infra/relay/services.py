"""Services on the testnet (tauhud.com/services/): accounts that do something for other wallets, found in the blocks alone.

Nobody signs up and nobody keeps a list. The relay reads every block it holds (the current chain since its start) and
lists an account when the chain shows it serving other wallets in one of four ways:

  cosign   a co-signer: other wallets name it as approver of their payments (approval_request "approvers"), it signs
           or declines them (transfer_vote, feeless), or an account's own rule waits for it (an o5 rule that compares
           an approval slot i18-i25 with its key). The Guardian on tauhud.com/guardian/ is one; anybody's approver bot
           shows up the same way.
  rules    a rule giver: it offers a personal rule to other wallets (rule_offer) and at least one takes it
           (rule_offer_accept with the same text).
  terms    paid with terms: at least TERMS_MIN different wallets pay it with retractable transfers (money that waits
           until a block height or a time and can be taken back until then).
  paid     paid by many: at least PAID_MIN different wallets pay it with plain transfers. The accounts the testnet started
           with (IDNI's) and our own server wallets (island bot, purses, cruise passengers) do not count as payers here,
           because their traffic is scripted.

Our own server wallets never count as served wallets anywhere. A few addresses are named, because their app is public:
Agorzilla's (agorzilla.com) and White Rabbit Key's (tauhud.com/rabbit/) addresses, one row per app, and the Guardian.
Everything else is listed by its key only. A listing says what the chain shows, never who runs an account or whether
it is safe to use.

What cannot be read from the blocks is left out: whether a co-signed payment ran in the end (the node keeps that, not
the block), whether a retractable payment was taken back (retract_transfer names only an id), and who stands behind a key.

GET /services
  services   rows, most wallets served first: {"address", "app" (agorzilla|rabbit|guardian|null), "ours", "idni",
             "addresses" (how many addresses the row joins), "kinds", "wallets" (different wallets served),
             "first", "last" (block times), and per kind:
               cosign {"named_by", "requests", "votes", "approved", "declined", "rules"}
               rules  {"offers", "offered_to", "taken_by"}
               terms  {"payers", "payments", "agrs"}
               paid   {"payers", "payments", "agrs", "days"}}
  totals     {"services", "cosign", "rules", "terms", "paid", "wallets" (different wallets served by any row)}
  rules      {"terms_min", "paid_min"}
  height, since (first block time held), generated_at
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import urllib.request

from txsources import AGORZILLA, GENESIS, RABBIT_BOXES, RABBIT_COUNCIL, RABBIT_TILLS

log = logging.getLogger("relay.services")

TERMS_MIN = int(os.environ.get("SERVICES_TERMS_MIN", "2"))
PAID_MIN = int(os.environ.get("SERVICES_PAID_MIN", "3"))
SERVICES_MAX = int(os.environ.get("SERVICES_MAX", "60"))
GUARDIAN_INFO = os.environ.get("GUARDIAN_INFO_URL", "http://guardian:8075/guardian/info")
KEY = re.compile(r"^[0-9a-f]{96}$")
# an approval slot compared with a key inside a rule: i18[t]:bv[384] = { #x<96 hex> }:bv[384]
SLOT_KEY = re.compile(r"i(1[89]|2[0-5])\[t\](?::bv\[\d+\])?\s*=\s*\{\s*#x([0-9a-fA-F]{96})\s*\}")
NEUTRAL = {"(o5[t]:bv[24]={#x000001}:bv[24])", "o5[t]:bv[24]={#x000001}:bv[24]", "always((o5[t]:bv[24]={#x000001}:bv[24])).",
           "always(o5[t]:bv[24]={#x000001}:bv[24])."}
RABBIT = {RABBIT_COUNCIL, *RABBIT_TILLS, *RABBIT_BOXES}


def _flat(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _int(v) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return 0


class Services:
    def __init__(self):
        self.bots: set[str] = set()                 # our island bot's and purses' keys (relay.py fills it)
        self.passengers = lambda: {}                # the cruise ships' simulated passengers {key: ship}
        self.guardian = ""                          # the Guardian's key, asked from its door now and then
        self._guardian_at = 0.0

    # ---------- the Guardian's key, from its own door (never needed for the rest) ----------
    def refresh_guardian(self):
        if not GUARDIAN_INFO or time.monotonic() - self._guardian_at < 600:
            return
        self._guardian_at = time.monotonic()

        def ask():
            try:
                with urllib.request.urlopen(GUARDIAN_INFO, timeout=5) as r:
                    pk = str(json.loads(r.read().decode()).get("pubkey") or "").lower()
                if KEY.match(pk):
                    self.guardian = pk
            except Exception as exc:   # the Guardian may be off; the list works without its name
                log.debug("guardian info: %r", exc)
        threading.Thread(target=ask, daemon=True).start()

    def app_of(self, address: str) -> str | None:
        if address in AGORZILLA:
            return "agorzilla"
        if address in RABBIT:
            return "rabbit"
        if self.guardian and address == self.guardian:
            return "guardian"
        return None

    # ---------- reading the blocks ----------
    def scan(self, blocks: list[dict]) -> dict:
        ours = {k.lower() for k in self.bots} | {k.lower() for k in (self.passengers() or {})}
        acc: dict[str, dict] = {}
        offers: dict[tuple[str, str], str] = {}     # (recipient, rule text) -> who offered it
        policy: dict[str, str] = {}                 # author -> their latest personal rule (flat text)
        since = None

        def row(addr: str, ts) -> dict:
            r = acc.get(addr)
            if r is None:
                r = acc[addr] = {"named_by": set(), "requests": 0, "votes": 0, "approved": 0, "declined": 0,
                                 "offers": 0, "offered_to": set(), "taken_by": set(),
                                 "terms_payers": set(), "terms_n": 0, "terms_agrs": 0,
                                 "paid_payers": set(), "paid_n": 0, "paid_agrs": 0, "paid_days": set(),
                                 "first": ts, "last": ts}
            if isinstance(ts, (int, float)):
                r["first"] = ts if not isinstance(r["first"], (int, float)) else min(r["first"], ts)
                r["last"] = ts if not isinstance(r["last"], (int, float)) else max(r["last"], ts)
            return r

        for b in blocks:
            ts = (b.get("header") or {}).get("timestamp")
            ts = ts if isinstance(ts, (int, float)) and ts > 0 else None
            if ts and since is None:
                since = ts
            for t in b.get("transactions") or []:
                if not isinstance(t, dict):
                    continue
                kind = t.get("tx_type") or "user_tx"
                who = str(t.get("sender_pubkey") or "").lower()
                if not KEY.match(who) or who in ours:
                    continue
                if kind == "approval_request":
                    for pk in (t.get("approvers") or {}).values() if isinstance(t.get("approvers"), dict) else ():
                        pk = str(pk).lower()
                        if KEY.match(pk) and pk != who:
                            r = row(pk, ts)
                            r["named_by"].add(who)
                            r["requests"] += 1
                elif kind == "transfer_vote":
                    r = row(who, ts)
                    r["votes"] += 1
                    r["approved" if t.get("approve") is not False else "declined"] += 1
                elif kind == "rule_offer":
                    to, text = str(t.get("recipient_pubkey") or "").lower(), t.get("rule_text")
                    if KEY.match(to) and isinstance(text, str) and to != who:
                        r = row(who, ts)
                        r["offers"] += 1
                        r["offered_to"].add(to)
                        offers[(to, _flat(text))] = who
                elif kind == "rule_offer_accept":
                    text = t.get("rule_text")
                    if isinstance(text, str):
                        giver = offers.get((who, _flat(text)))
                        if giver:
                            row(giver, ts)["taken_by"].add(who)
                        if "o5" in text:
                            policy[who] = _flat(text)
                elif kind == "retractable_transfer":
                    to, n = str(t.get("recipient_pubkey") or "").lower(), _int(t.get("amount"))
                    if KEY.match(to) and to != who and n:
                        r = row(to, ts)
                        r["terms_payers"].add(who)
                        r["terms_n"] += 1
                        r["terms_agrs"] += n
                elif kind == "user_tx":
                    ops = t.get("operations") if isinstance(t.get("operations"), dict) else {}
                    text = ops.get("0")
                    if isinstance(text, str) and "o5" in text:
                        policy[who] = _flat(text)
                    if who in GENESIS:
                        continue
                    for op in ops.get("1") or []:
                        if not isinstance(op, (list, tuple)) or len(op) < 3 or str(op[0]).lower() != who:
                            continue
                        to, n = str(op[1]).lower(), _int(op[2])
                        if not KEY.match(to) or to == who or not n:
                            continue
                        r = row(to, ts)
                        r["paid_payers"].add(who)
                        r["paid_n"] += 1
                        r["paid_agrs"] += n
                        if ts:
                            r["paid_days"].add(int(ts // 86400))

        # accounts whose own rule (the latest one each author wrote) waits for an approver's key
        rules_for: dict[str, set] = {}
        for author, text in policy.items():
            if text in NEUTRAL:
                continue
            for _slot, pk in SLOT_KEY.findall(text):
                pk = pk.lower()
                if pk != author:
                    rules_for.setdefault(pk, set()).add(author)
        for pk, authors in rules_for.items():
            if pk in acc:
                acc[pk]["rules_for"] = authors
            else:
                row(pk, None)["rules_for"] = authors

        # one row per named app, one per other address
        groups: dict[str, list[str]] = {}
        for addr in acc:
            groups.setdefault(self.app_of(addr) or addr, []).append(addr)
        out = []
        for key, addrs in groups.items():
            rs = [acc[a] for a in addrs]
            u = lambda f: set().union(*(r.get(f) or set() for r in rs))
            s = lambda f: sum(r[f] for r in rs)
            named, rule_authors = u("named_by"), u("rules_for")
            offered, taken = u("offered_to"), u("taken_by")
            tp, pp = u("terms_payers"), u("paid_payers")
            kinds, item = [], {}
            if named or rule_authors or s("votes"):
                kinds.append("cosign")
                item["cosign"] = {"named_by": len(named), "requests": s("requests"), "votes": s("votes"),
                                  "approved": s("approved"), "declined": s("declined"), "rules": len(rule_authors)}
            if taken:
                kinds.append("rules")
                item["rules"] = {"offers": s("offers"), "offered_to": len(offered), "taken_by": len(taken)}
            if len(tp) >= TERMS_MIN:
                kinds.append("terms")
                item["terms"] = {"payers": len(tp), "payments": s("terms_n"), "agrs": s("terms_agrs")}
            if len(pp) >= PAID_MIN:
                kinds.append("paid")
                item["paid"] = {"payers": len(pp), "payments": s("paid_n"), "agrs": s("paid_agrs"),
                                "days": len(u("paid_days"))}
            if not kinds:
                continue
            served = named | rule_authors | taken | (tp if "terms" in kinds else set()) | (pp if "paid" in kinds else set())
            times = [r[f] for r in rs for f in ("first", "last") if isinstance(r[f], (int, float))]
            app = self.app_of(addrs[0])
            main = max(addrs, key=lambda a: (len(acc[a]["paid_payers"]) + len(acc[a]["named_by"]), a))
            out.append({"address": main, "app": app, "ours": app is not None, "idni": main in GENESIS,
                        "addresses": len(addrs), "kinds": kinds, "wallets": len(served),
                        "first": round(min(times)) if times else None, "last": round(max(times)) if times else None,
                        **item, "_served": served})
        out.sort(key=lambda r: (-r["wallets"], -(r["last"] or 0), r["address"]))
        out = out[:SERVICES_MAX]
        everyone = set().union(*(r.pop("_served") for r in out))
        totals = {k: sum(1 for r in out if k in r["kinds"]) for k in ("cosign", "rules", "terms", "paid")}
        return {"services": out, "totals": {"services": len(out), **totals, "wallets": len(everyone)},
                "rules": {"terms_min": TERMS_MIN, "paid_min": PAID_MIN}, "since": round(since) if since else None}

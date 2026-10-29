"""Unit test of the wallet's transactions in the simulation (GET /sim/tx, GET /sim/wallet): the strict shape per type,
no free text, the block six ahead, the hash of the exact text, limits per account and address, paging, the day's reset.

Run: python test_simwallet.py
"""
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simwallet  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T = [datetime(2026, 10, 29, 16, 0, 4, tzinfo=timezone.utc).timestamp()]
A, B, C = "a" * 96, "b" * 96, "c" * 96
RULE = "always ( (!(i4[t]:bv[384] = { #x" + B + " }:bv[384])) ? (o5[t]:bv[24] = { #x000000 }:bv[24]) : (o5[t]:bv[24] = { #x000001 }:bv[24]) )."


def tx(kind, seq=0, sender=A, **extra):
    return {"tx_type": kind, "sender_pubkey": sender, "sequence_number": seq, "expiration_time": 1800000000, "fee_limit": "50",
            "expire_at_height": 5000, "signature": "f" * 192, **extra}


path = os.path.join(tempfile.mkdtemp(), "simwallet.json")
w = simwallet.SimWallet(path, clock=lambda: T[0])
send = lambda t, ip="1.1.1.1": w.route("/sim/tx", "tx=" + quote(json.dumps(t)) + "&a=1&b=2&c=3", ip)  # noqa: E731

code, r = send(tx("user_tx", operations={"1": [[A, B, "120"], [A, C, "30"]]}))
check(code == 200 and r["ok"], f"a split payment is taken {r}")
check(r["h"] == simwallet.head_at(T[0]) + simwallet.LEAD, "it lands six blocks ahead")
check(r["hash"] == hashlib.sha256(json.dumps(tx("user_tx", operations={"1": [[A, B, "120"], [A, C, "30"]]})).encode()).hexdigest(), "the hash is sha256 of the exact text")
check("signature" not in w.txs[0]["tx"] and w.txs[0]["by"] == [1, 2, 3], "the signature is not kept, the identity indices are")
code, again = send(tx("user_tx", operations={"1": [[A, B, "120"], [A, C, "30"]]}))
check(again.get("again") and again["i"] == 0 and len(w.txs) == 1, "the same transaction twice is kept once")

good = [
    tx("user_tx", 1, operations={"0": RULE}),
    tx("consensus_rule_vote", 2, update_id="1" * 64, approve=True, fee_limit="0"),
    tx("rule_offer", 3, recipient_pubkey=B, rule_text=RULE),
    tx("rule_offer_accept", 4, offer_id="2" * 64, rule_text=RULE),
    tx("rule_offer_reject", 5, offer_id="3" * 64),
    tx("approval_request", 6, recipient_pubkey=B, amount=900, approvers={"18": C}, custom_inputs={}),
    tx("transfer_vote", 7, request_id="4" * 64, approve=True, reason="", fee_limit="0"),
    tx("retractable_transfer", 8, recipient_pubkey=B, amount=40, release_at_height=900, release_at_time=None),
    tx("retract_transfer", 9, retractable_id="5" * 64, fee_limit="0"),
]
for i, t in enumerate(good):
    T[0] += 11
    code, r = send(t)
    check(r["ok"], f"{t['tx_type']} is taken {r.get('why', '')}")

bad = {
    "free text in a vote": tx("transfer_vote", request_id="4" * 64, approve=True, reason="hello there"),
    "an unknown type": tx("mint", amount=5),
    "an extra field": tx("user_tx", operations={"1": [[A, B, "1"]]}, note="hi"),
    "a short key": tx("user_tx", sender="ab" * 10, operations={"1": [["ab" * 10, B, "1"]]}),
    "someone else's money": tx("user_tx", operations={"1": [[B, C, "1"]]}),
    "seven transfers": tx("user_tx", operations={"1": [[A, B, "1"]] * 7}),
    "a zero amount": tx("user_tx", operations={"1": [[A, B, "0"]]}),
    "a word in a rule": tx("user_tx", operations={"0": "always ( hello )."}),
    "a network stream in a rule": tx("user_tx", operations={"0": "always ( (o9[t]:bv[24] = { #x00000c }:bv[24]) )."}),
    "a slot outside 18 to 25": tx("approval_request", recipient_pubkey=B, amount=5, approvers={"3": C}, custom_inputs={}),
    "no signature": {k: v for k, v in tx("rule_offer_reject", offer_id="3" * 64).items() if k != "signature"},
}
for label, t in bad.items():
    T[0] += 11
    code, r = send(t)
    check(code == 400 and not r["ok"], f"refused: {label} ({r.get('why')})")
code, r = w.route("/sim/tx", "tx=" + quote("{nope"), "1.1.1.1")
check(code == 400, "refused: not JSON")

# limits
T[0] += 60
sender = "d" * 96
oks = 0
for i in range(10):
    code, r = send(tx("user_tx", i, sender=sender, operations={"1": [[sender, B, str(i + 1)]]}), "2.2.2.2")
    oks += r["ok"]
check(oks == 6 and r["error"] == "rate", f"one address gets a burst of six, then waits ({oks})")
T[0] += 3600
for n in range(6):
    s = "%02x" % n * 48
    code, r = send(tx("user_tx", 0, sender=s, operations={"1": [[s, B, "1"]]}), "3.3.3.3")
    T[0] += 11
check(not r["ok"] and r["error"] == "limit", "five accounts per address and day, not six")

# the list, paged and persisted
code, page = w.route("/sim/wallet", "from=1", "9.9.9.9")
check(code == 200 and page["txs"][0]["i"] == 1 and page["count"] == len(w.txs), "GET /sim/wallet pages from an index")
w2 = simwallet.SimWallet(path, clock=lambda: T[0])
check(w2.count() == w.count() and w2.txs[-1]["hash"] == w.txs[-1]["hash"], "the day's list survives a restart")
check(w.route("/sim/votes", "", "1.1.1.1") is None, "other paths are not this module's")

# midnight
T[0] = datetime(2026, 10, 29, 23, 59, 30, tzinfo=timezone.utc).timestamp()
code, r = send(tx("user_tx", 99, operations={"1": [[A, B, "1"]]}), "4.4.4.4")
check(r["error"] == "late", "nothing lands across midnight")
T[0] += 60
check(w.count() == 0, "the list starts over with the new day")

print("\n" + ("all good" if not failed else f"{failed} failed"))
sys.exit(1 if failed else 0)

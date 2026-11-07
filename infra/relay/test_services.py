"""Unit test of the services found in the blocks (services.py), no network.

Run: python test_services.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["GUARDIAN_INFO_URL"] = ""
import services  # noqa: E402
from txsources import BOWL, RABBIT_COUNCIL  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


A, B, C, D, E = ("a1" * 48, "b2" * 48, "c3" * 48, "d4" * 48, "e5" * 48)
BOT = "f0" * 48          # an approver bot somebody runs
GUARD = "9e" * 48        # the Guardian
SHOP = "5a" * 48         # takes retractable payments
GIVER = "6b" * 48        # offers a rule
OURBOT = "7c" * 48       # our island bot
PASS = "8d" * 48         # a simulated cruise passenger
G = "8a39b9d9498535492290c52b44959b5a6e9177dc85ae6a1d97f54462f03c15a38052a85c7ace5cd81858e343a3b789d0"   # IDNI genesis

RULE = "always ( (i1[t]:bv[24] > { #x0003e8 }:bv[24] && !(i18[t]:bv[384] = { #x%s }:bv[384])) ? (o5[t]:bv[24] = { #x000000 }:bv[24]) : (o5[t]:bv[24] = { #x000001 }:bv[24]) )." % GUARD
NEUTRAL = "always ( (o5[t]:bv[24] = { #x000001 }:bv[24]) )."
OFFER = "always ( (o5[t]:bv[24] = { #x000001 }:bv[24]) || (i1[t]:bv[24] < { #x000010 }:bv[24]) )."


def pay(sender, to, n=5):
    return {"tx_type": "user_tx", "sender_pubkey": sender, "operations": {"1": [[sender, to, str(n)]]}}


day = 1_793_145_600
blocks = [
    {"header": {"timestamp": 0}, "transactions": []},
    {"header": {"timestamp": day + 60}, "transactions": [
        {"tx_type": "approval_request", "sender_pubkey": A, "recipient_pubkey": B, "amount": 50000, "approvers": {"18": BOT}},
        {"tx_type": "approval_request", "sender_pubkey": B, "recipient_pubkey": A, "amount": 9000, "approvers": {"18": BOT}},
        {"tx_type": "approval_request", "sender_pubkey": A, "recipient_pubkey": C, "amount": 7000, "approvers": {"18": BOT}},
        {"tx_type": "transfer_vote", "sender_pubkey": BOT, "request_id": "00" * 32, "approve": True},
        {"tx_type": "transfer_vote", "sender_pubkey": BOT, "request_id": "01" * 32, "approve": False},
        {"tx_type": "user_tx", "sender_pubkey": C, "operations": {"0": RULE}},
        {"tx_type": "user_tx", "sender_pubkey": D, "operations": {"0": RULE}},
        {"tx_type": "approval_request", "sender_pubkey": OURBOT, "recipient_pubkey": A, "amount": 9, "approvers": {"19": E}},
    ]},
    {"header": {"timestamp": day + 120}, "transactions": [
        {"tx_type": "user_tx", "sender_pubkey": D, "operations": {"0": NEUTRAL}},   # D took its rule away again
        {"tx_type": "retractable_transfer", "sender_pubkey": A, "recipient_pubkey": SHOP, "amount": 10, "release_at_height": 99},
        {"tx_type": "retractable_transfer", "sender_pubkey": B, "recipient_pubkey": SHOP, "amount": 15, "release_at_time": day + 999},
        {"tx_type": "retractable_transfer", "sender_pubkey": A, "recipient_pubkey": E, "amount": 3, "release_at_height": 99},  # one payer only
        {"tx_type": "rule_offer", "sender_pubkey": GIVER, "recipient_pubkey": A, "rule_text": OFFER, "expire_at_height": 50},
        {"tx_type": "rule_offer", "sender_pubkey": GIVER, "recipient_pubkey": B, "rule_text": OFFER, "expire_at_height": 50},
        {"tx_type": "rule_offer_accept", "sender_pubkey": A, "offer_id": "aa" * 32, "rule_text": " " + OFFER},
        {"tx_type": "rule_offer", "sender_pubkey": E, "recipient_pubkey": C, "rule_text": OFFER, "expire_at_height": 50},  # never taken
    ]},
    {"header": {"timestamp": day + 86400}, "transactions": [
        pay(A, BOWL), pay(B, BOWL), pay(C, BOWL), pay(D, RABBIT_COUNCIL),
        pay(A, E), pay(B, E), pay(G, E), pay(OURBOT, E), pay(PASS, E),   # E: only 2 real payers -> not "paid by many"
    ]},
]

s = services.Services()
s.bots = {OURBOT}
s.passengers = lambda: {PASS: "queen"}
s.guardian = GUARD
out = s.scan(blocks)
rows = {r["app"] or r["address"]: r for r in out["services"]}

bot = rows.get(BOT)
check(bot and bot["kinds"] == ["cosign"], "an approver bot others name is a co-signer")
check(bot and bot["cosign"] == {"named_by": 2, "requests": 3, "votes": 2, "approved": 1, "declined": 1, "rules": 0},
      "co-signer numbers: 2 wallets, 3 requests, 1 signed, 1 declined")
g = rows.get("guardian")
check(g and g["kinds"] == ["cosign"] and g["cosign"]["rules"] == 1 and g["ours"], "the Guardian: named in C's rule only (D removed it)")
check(rows.get(SHOP, {}).get("terms") == {"payers": 2, "payments": 2, "agrs": 25}, "paid with terms by two wallets")
check(rows.get(GIVER, {}).get("rules") == {"offers": 2, "offered_to": 2, "taken_by": 1}, "a rule giver: offered to 2, taken by 1")
check(E not in rows, "E: one retractable payer, an offer nobody took, 2 real payers, named only by our own bot -> not listed")
agz = rows.get("agorzilla")
check(agz and agz["kinds"] == ["paid"] and agz["paid"]["payers"] == 3 and agz["ours"], "Agorzilla's bowl: paid by 3 wallets")
check("rabbit" not in rows, "White Rabbit Key with one payer is not listed")
check(out["totals"]["services"] == len(out["services"]) == 5, "five services")
check(out["totals"]["wallets"] == 3, "different wallets served across all rows: A B C")
check(out["since"] == day + 60, "since = first real block time")
check(out["services"][0]["wallets"] >= out["services"][-1]["wallets"], "most wallets served first")
check(all(isinstance(r["address"], str) and len(r["address"]) == 96 for r in out["services"]), "every row has a key")
check(s.scan([])["services"] == [], "no blocks, no rows")

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

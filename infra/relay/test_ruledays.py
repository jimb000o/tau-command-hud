"""ruledays.py: rule kinds (the same answers as assets/rulekinds.js), the day record across chain restarts, rule offers."""
import json
import os
import sys
import tempfile

import ruledays

fails = 0


def check(ok, what):
    global fails
    print(("PASS " if ok else "FAIL ") + what)
    fails += 0 if ok else 1


here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "..", "..", "tests", "rulekinds-cases.json")) as f:
    for c in json.load(f):
        k = ruledays.kinds(c["text"])
        check(k == {"kinds": c["kinds"], "size": c["size"]}, f"{c['name']}: {k}")

CAP = "always ( (i1[t]:bv[24] >= { #x001389 }:bv[24]) ? (o5[t]:bv[24] = { #x000000 }:bv[24]) : (o5[t]:bv[24] = { #x000001 }:bv[24]) )."
TIME = "always ( (i5[t]:bv[64] < {1798761600}:bv[64]) ? (o5[t]:bv[24] = { #x000000 }:bv[24]) : (o5[t]:bv[24] = { #x000001 }:bv[24]) )."
A, B, OURS = "aa" * 48, "bb" * 48, "cc" * 48
who = lambda pk: "ours" if pk == OURS else "people"
day1, day2 = 1794700000, 1794700000 + 86400

with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "ruledays.json")
    r = ruledays.RuleDays(path)
    r.record({A: CAP, OURS: TIME}, {A, B, OURS}, who, now=day1)
    r.record({A: CAP, OURS: TIME}, {A, B, OURS}, who, now=day1 + 60)   # the same check again counts nothing new
    t = r.days[ruledays.day_of(day1)]
    check(t["new"] == {"people": 1, "ours": 1, "idni": 0} and t["holders"]["people"] == 1 and t["kinds"]["people"]["cap"] == 1
          and t["kinds"]["ours"]["time"] == 1, f"day one: two new rules, sorted by kind and holder {t}")
    r.save(now=day1)
    r = ruledays.RuleDays(path)   # relay restart: read back from disk
    r.record({A: TIME}, {A, OURS}, who, now=day2)   # A changed its rule, ours removed, B not asked this time
    t = r.days[ruledays.day_of(day2)]
    check(t["new"]["people"] == 1 and t["gone"]["ours"] == 1 and t["kinds"]["people"]["time"] == 1 and t["kinds"]["people"]["cap"] == 0,
          f"day two: a changed rule is new, a removed one gone {t}")
    r.restart(now=day2)
    r.record({A: TIME}, {A}, who, now=day2 + 60)
    t = r.days[ruledays.day_of(day2)]
    check(t.get("restart") is True and t["new"]["people"] == 2 and t["gone"]["people"] == 0,
          f"after a chain restart a rule set again counts as new, nothing as gone {t}")
    check(r.history()["since"] == ruledays.day_of(day1) and len(r.history()["days"]) == 2, "history from the first day")

# offers: made, accepted, rejected, expired, open; matched by the chain's offer id
ids = iter(["01" * 32, "02" * 32, "03" * 32, "04" * 32])
oid = lambda *a: next(ids)
blocks = [{"transactions": [
    {"tx_type": "rule_offer", "sender_pubkey": OURS, "recipient_pubkey": A, "rule_text": CAP, "expire_at_height": 50},
    {"tx_type": "rule_offer", "sender_pubkey": A, "recipient_pubkey": B, "rule_text": CAP, "expire_at_height": 50},
    {"tx_type": "rule_offer", "sender_pubkey": A, "recipient_pubkey": B, "rule_text": TIME, "expire_at_height": 50},
    {"tx_type": "rule_offer", "sender_pubkey": A, "recipient_pubkey": B, "rule_text": TIME, "expire_at_height": 500}]},
    {"transactions": [{"tx_type": "rule_offer_accept", "sender_pubkey": A, "offer_id": "01" * 32, "rule_text": CAP},
                      {"tx_type": "rule_offer_reject", "sender_pubkey": B, "offer_id": "02" * 32}]}]
o = ruledays.offers(blocks, 100, oid, who)
check(o["matched"] and o["by"]["ours"] == {"made": 1, "accepted": 1, "rejected": 0, "expired": 0, "open": 0}
      and o["by"]["people"] == {"made": 3, "accepted": 0, "rejected": 1, "expired": 1, "open": 1}, f"offers by outcome {o}")
o = ruledays.offers(blocks, 100, lambda *a: None, who)
check(not o["matched"] and o["by"]["people"]["made"] == 3 and o["by"]["people"]["expired"] == 0, "without offer ids only made is sure")

print("all ruledays checks passed" if not fails else f"{fails} ruledays checks failed")
sys.exit(1 if fails else 0)

"""Unit test of fair turns on the personal-rule places (slotlease.py): only the neutral clause is kept, a turn lasts a day
while nobody waits and 30 minutes while somebody does, a newer deposit never restarts a turn, the line and its limits,
and what happens when the place frees or the rule never comes.

Run: python test_slotlease.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slotlease  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T = [1_800_000_000.0]
A, B, C, D = "a" * 96, "b" * 96, "c" * 96, "d" * 96
NEUTRAL = "always ( (o5[t]:bv[24] = { #x000001 }:bv[24]) )."


def tx(sender=A, seq=3, rule=NEUTRAL, **extra):
    return {"tx_type": "user_tx", "sender_pubkey": sender, "sequence_number": seq, "expiration_time": int(T[0]) + 3 * 86400,
            "fee_limit": "50", "expire_at_height": 9000, "operations": {"0": rule}, "signature": "f" * 192, **extra}


path = os.path.join(tempfile.mkdtemp(), "lease.json")
s = slotlease.SlotLease(path, clock=lambda: T[0])

for label, t in (("a real rule", tx(rule="always ( (o5[t]:bv[24] = { #x000000 }:bv[24]) ).")), ("a transfer too", {**tx(), "operations": {"0": NEUTRAL, "1": [[A, B, "1"]]}}),
                 ("an extra field", tx(note="x")), ("a short expiry", {**tx(), "expiration_time": int(T[0]) + 600}), ("no signature", {**tx(), "signature": "x"})):
    got, why = s.check(json.dumps(t))
    check(got is None and why, f"refused: {label} ({why})")
got, why = s.check(json.dumps(tx()))
check(got is not None, "the neutral clause is taken")

s.set_holders([A])
r = s.deposit(json.dumps(tx()), tx())
check(r["until"] == T[0] + slotlease.LEASE_MAX, "nobody waits: the turn lasts a day")
check(s.due() == [], "not due yet")
s.wait(B, "1.1.1.1")
check(s.status(A)["mine"]["until"] == T[0] + slotlease.LEASE, "somebody waits: 30 minutes")
T[0] += 20 * 60
s.deposit(json.dumps(tx(seq=4)), tx(seq=4))
check(s.leases[A]["start"] == T[0] - 20 * 60 and s.leases[A]["seq"] == 4, "a newer removal replaces the older, the turn keeps its start")
T[0] += 11 * 60
d = s.due()
check(len(d) == 1 and json.loads(d[0][1])["sequence_number"] == 4, "after 30 minutes the newest removal is due")
s.sent(A, True)
check(s.due() == [], "sent once, not again")
s.set_holders([])
check(A not in s.leases, "the place is free: the turn is over")
s.set_holders([B])
check(s.status(B)["position"] is None and s.status()["waiting"] == 0, "the next one in line now holds a place and leaves the line")

# the line
for pk in (C, D, "e" * 96):
    s.wait(pk, "2.2.2.2")
check(not s.wait("f" * 96, "2.2.2.2")["ok"], "three accounts per address in line")
check(s.status(D)["position"] == 2, "the line keeps its order")
s.leave(C)
check(s.status(D)["position"] == 1, "leaving moves the others up")
check(not s.wait(B, "3.3.3.3")["ok"], "a holder cannot queue")

# a deposit for a rule that never comes
s.deposit(json.dumps(tx(sender=C)), tx(sender=C))
T[0] += 31 * 60
s.set_holders([B])
check(C not in s.leases, "a removal for a rule that never came is dropped")

# survives a restart
s2 = slotlease.SlotLease(path, clock=lambda: T[0])
check(set(s2.waiting) == set(s.waiting), "the line survives a restart")
check(s.route("/rules", "") is None and s.route("/lease", "pk=" + D)[1]["position"] == 1, "routes")

print("\n" + ("all good" if not failed else f"{failed} failed"))
sys.exit(1 if failed else 0)

"""Unit test of White Rabbit Key's envelopes and purse rules (islandrules.py, run by island.py), no network.

Run: python test_islandrules.py
"""
import asyncio
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import island  # noqa: E402
import islandrules  # noqa: E402
from py_ecc.bls import G2Basic  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T = [1_794_000_000.0]   # Sun 2026-11-08 ~00:40 German time... set below
clock = lambda: T[0]  # noqa: E731
# Wednesday 18 November 2026, 12:00 German time (UTC+1)
T[0] = 1_795_518_000.0
rel, due = islandrules.election(T[0])
check(rel == 1_795_993_200 and due == rel - 1800, "the envelope waits until Monday 00:00 German time, the promise until Sunday 23:30")

d = tempfile.mkdtemp()
I = island.Island(path=os.path.join(d, "island.keys"), daily=500, clock=clock, enabled=True)
I.seen["1.2.3.4"] = T[0]
W = "ab" * 48
sent = []


async def ask(cmd):
    name = cmd.split(" ", 1)[0]
    if name == "getsequence":
        return {"status": "ok", "data": {"sequence_number": 3, "tip_height": 100}}
    if name == "sendtx":
        tx = json.loads(cmd[7:])
        sent.append(tx)
        return {"status": "ok", "data": {"tx_hash": "h%d" % len(sent)}}
    if name == "gettxstatus":
        return {"status": "ok", "data": {"retractable": {"id": "r1", "status": "open"}}}
    if name == "getretractable":
        return {"status": "ok", "data": {"status": "retracted"}}
    return None

gov = lambda: {}  # noqa: E731

ok, r = I.accept_pay("north", W, "1.2.3.4")
check(ok and r["queued"], "the North Wind's money is queued after a move")
asyncio.run(I.send_pay("north", W, ask, gov))
tx = sent[-1]
check(tx["tx_type"] == "retractable_transfer" and tx["recipient_pubkey"] == W and tx["amount"] == 40 and tx["release_at_time"] == rel,
      "the envelope is a retractable transfer of 40, released at the election")
pre = island.signing_bytes(tx)
check(set(json.loads(pre)) >= {"recipient_pubkey", "amount", "release_at_height", "release_at_time"} and "operations" not in json.loads(pre),
      "the signed fields of a retractable transfer, as the node reads them")
check(G2Basic.Verify(bytes.fromhex(tx["sender_pubkey"]), hashlib.sha256(pre).digest(), bytes.fromhex(tx["signature"])), "its signature verifies")
check(tx["expiration_time"] < rel, "the transaction expires before its release")
check(I.chain.env["north|" + W]["state"] == "open" and I.chain.next_job() is None, "an open envelope, nothing to do before Sunday night")

asyncio.run(I.send_pay("works", W, ask, gov))
check(sent[-1]["tx_type"] == "user_tx" and sent[-1]["operations"]["1"][0][2] == "10", "a wage stays a plain transfer")

# the south's envelope: promise kept
asyncio.run(I.send_pay("south", W, ask, gov))
ok, r = I.accept_kept("south", W, "1.2.3.4")
check(ok and r["kept"], "the player proposed the road: the resort's envelope stays")
ok, r = I.accept_kept("south", W, "9.9.9.9")
check(ok and not r["kept"] and r["why"] == "no move", "only after a move from the same address")

# Sunday 23:31: the North's promise was not kept, the South's was
T[0] = due + 60
job = I.chain.next_job()
check(job and job[0] == "retract" and job[1]["purse"] == "north", "Sunday night: the broken promise's envelope is taken back")
asyncio.run(I.chain_job(job, ask, gov))
rt = sent[-1]
check(rt["tx_type"] == "retract_transfer" and rt["retractable_id"] == "r1" and rt["fee_limit"] == "0" and rt["expiration_time"] < rel,
      "a feeless retract of that envelope, expiring before the release")
check(G2Basic.Verify(bytes.fromhex(rt["sender_pubkey"]), hashlib.sha256(island.signing_bytes(rt)).digest(), bytes.fromhex(rt["signature"])),
      "the retract's signature verifies")
check(I.chain.next_job() is None, "the kept one is left alone")
ok, r = I.accept_kept("north", W, "1.2.3.4")
check(not r["kept"], "too late to keep it once it is being taken back")

T[0] = rel + 400
job = I.chain.next_job()
check(job and job[0] == "settle", "after the release the node is asked how each ended")
asyncio.run(I.chain_job(job, ask, gov))
check(I.chain.env[job[1]["purse"] + "|" + W]["state"] in ("retracted", "released"), "and the answer is kept")

# the laws of the week: the reef law caps the North Wind's purse
I.chain.laws = lambda: ["boat", "reef"]
job = I.chain.next_job()
while job and job[0] == "settle":
    asyncio.run(I.chain_job(job, ask, gov))
    job = I.chain.next_job()
check(job and job[0] == "rule" and job[1] == "north" and job[3] == "reef", "the reef law asks for a rule on the North Wind's purse")
asyncio.run(I.chain_job(job, ask, gov))
rule = sent[-1]
check(rule["operations"] == {"0": islandrules.cap_rule(20)} and "#x000014" in rule["operations"]["0"], "its rule: no payment above 20")
check(I.chain.amount("north", 40) == 20 and I.route("/island")["pay"]["north"] == 20, "the North Wind pays 20 while the rule holds")
check(I.chain.next_job() is None, "a rule is sent once")
again = island.Island(path=os.path.join(d, "island.keys"), clock=clock, enabled=True)
check(again.chain.rules["north"]["law"] == "reef" and again.chain.env, "the rules and envelopes survive a restart")
I.chain.laws = lambda: ["boat"]
job = I.chain.next_job()
check(job and job[0] == "rule" and job[2] == islandrules.NEUTRAL, "a week without the reef law lifts it")
asyncio.run(I.chain_job(job, ask, gov))
check(I.chain.amount("north", 40) == 40 and I.chain.next_job() is None, "and the North Wind pays 40 again")

# full: a plain transfer
I.chain.env = {f"north|{i:096x}": {"purse": "north", "wallet": f"{i:096x}", "state": "open", "kept": True, "rel": 2e9, "due": 2e9, "at": T[0]}
               for i in range(islandrules.OPEN_MAX)}
check(I.chain.envelope("north", W) is None, "with OPEN_MAX open envelopes the next one is a plain transfer")
T[0] = due - 30
I.chain.env = {}
check(I.chain.envelope("south", W) is None, "after the last chance to keep a promise, a plain transfer")

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

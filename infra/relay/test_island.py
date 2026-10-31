"""Unit test of White Rabbit Key's island bot (island.py), no network.

Run: python test_island.py
"""
import asyncio
import hashlib
import json
import re
import os
import stat
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import island  # noqa: E402
from py_ecc.bls import G2Basic  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T = [1_793_232_000.0]  # 2026-10-30 00:00 UTC
clock = lambda: T[0]  # noqa: E731
path = os.path.join(tempfile.mkdtemp(), "island.keys")
I = island.Island(path=path, daily=20, clock=clock, enabled=True)
check(I.enabled and set(I.pk) == set(island.CANDIDATES), "four campaign wallets are made on first start")
check(stat.S_IMODE(os.stat(path).st_mode) == 0o600, "their keys are kept readable by the relay only")
check(island.COUNCIL not in I.pk.values(), "no campaign wallet is the council")
again = island.Island(path=path, clock=clock, enabled=True)
check(again.pk == I.pk, "the same wallets after a restart")

ok, d = I.accept("tobias", "law", "1.2.3.4")
check(ok and d["queued"] and d["wallet"] == I.pk["tobias"], "a rival's law is queued")
check(I.accept("rico", "law", "1.2.3.4")[0] is False, "only the four candidates have wallets")
check(I.accept("hana", "steal", "1.2.3.4")[0] is False, "only moves the game knows")
for _ in range(15):
    I.accept("baako", "talk", "5.6.7.8")
ok, d = I.accept("baako", "talk", "5.6.7.8")
check(ok and not d["queued"] and d["why"] == "busy", "one address cannot flood the queue")
for i in range(10):
    I.accept("marisol", "pact", f"9.9.9.{i}")
ok, d = I.accept("marisol", "pact", "10.0.0.1")
check(not d["queued"] and d["why"] == "daily", "at most ISLAND_DAILY a day")

tx = I.build("hana", 7, 1000, 10)
pre = island.signing_bytes(tx)
check(json.loads(pre) == {"sender_pubkey": I.pk["hana"], "sequence_number": 7, "expiration_time": tx["expiration_time"], "fee_limit": "50",
                          "tx_type": "user_tx", "expire_at_height": 2000, "operations": {"1": [[I.pk["hana"], island.COUNCIL, "1"]]}},
      "1 test AGRS to the council, fee five times the base fee, signed fields as the node reads them")
check(G2Basic.Verify(bytes.fromhex(tx["sender_pubkey"]), hashlib.sha256(pre).digest(), bytes.fromhex(tx["signature"])), "the BLS signature verifies")
check(island.base_fee({"consensus_rules": "o9[t]:bv[24] = { #x0c }"}) == 12 and island.base_fee({}) == 10, "base fee from the rules in force")

tx = I.build("baako", 1, 10, 10, "radio")
check(tx["operations"]["1"][0][1:] == [island.PLACES["radio"], str(island.RADIO_LINE)], "a radio line pays the station 25")
check(I.build("baako", 1, 10, 10, "north")["operations"]["1"][0][1:] == [island.PLACES["north"], "1"], "an embassy's money: 1 to the embassy")
check(I.accept("baako", "talk", "7.7.7.7", "moon")[0] is False, "only the island's places")
game = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "rabbit", "game.js"), encoding="utf-8").read()
till = dict(re.findall(r'^    (\w+): "([0-9a-f]{96})"', game[game.index("const TILL = {"):game.index("const TILL_AT")], re.M))
check(till == {k: v for k, v in island.PLACES.items() if k != "hall"} and island.PLACES["hall"] == island.COUNCIL, "the same tills as the game")
import txsources  # noqa: E402
check(set(till.values()) == txsources.RABBIT_TILLS, "In numbers counts the same tills")
check(txsources.rabbit({"sender_pubkey": "ab", "operations": {"1": [["ab", island.PLACES["radio"], "25"]]}}, {}) == ("line", ""), "a move paid to a till is a Book line")

sent = []


async def ask(cmd):
    c, _, rest = cmd.partition(" ")
    if c == "getsequence":
        return {"status": "ok", "command": c, "data": {"sequence_number": 4, "tip_height": 500}}
    sent.append(json.loads(rest))
    return {"status": "ok", "command": c, "data": {"ok": True, "tx_hash": "h%d" % len(sent)}}


async def go():
    await I.send("tobias", "law", ask, lambda: {})
    await I.send("tobias", "vote", ask, lambda: {})
asyncio.run(go())
check([t["sequence_number"] for t in sent] == [4, 5], "two moves before the next block take consecutive numbers")
r = I.route("/island")
check(r["today"] == 2 and r["recent"][0]["hash"] == "h2" and r["wallets"] == I.pk, "GET /island shows the wallets and the last transactions")
T[0] += 86400
check(I.route("/island")["today"] == 0, "the count starts again each UTC day")
off = island.Island(path=path, enabled=False)
check(off.accept("hana", "law", "1.1.1.1")[0] is False, "switched off: nothing is queued")

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

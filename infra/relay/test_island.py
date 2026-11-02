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
ok, d = I.accept("baako", "talk", "5.6.7.9")
check(ok and d["queued"] and d.get("with") == 12 and len(I.queue) == 2, "the same move from many games waits as one transaction")
for i, k in enumerate(["pact", "deal", "lie", "fact", "broke", "down", "refused", "vote", "talk"]):
    I.accept("marisol", k, f"9.9.9.{i}")
for i, at in enumerate(["market", "radio", "north", "south", "bar", "book", "pier", "school", "dive"]):
    I.accept("hana", "law", f"9.9.8.{i}", at)
ok, d = I.accept("marisol", "law", "10.0.0.1")
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
tx = I.build("baako", 1, 10, 10, "radio", 4)
check(tx["operations"]["1"][0][2] == "100", "four radio lines from four games: one transaction of 4 x 25")
check(I.build("hana", 1, 10, 10, "hall", 999)["operations"]["1"][0][2] == str(island.BATCH_MAX), "one transaction stands for at most BATCH_MAX moves")
import txsources as _tx  # noqa: E402
check(_tx.rival_moves(tx) == 4 and _tx.rival_moves(I.build("hana", 1, 10, 10, "market", 7)) == 7, "In numbers reads the moves back from the amount")
P = island.Island(path=path, daily=1000, clock=clock, enabled=True)
check(P.pace() == island.SPACING, "plenty of the day's budget left: one transaction every SPACING seconds")
P.today = 900
check(P.pace() > island.SPACING, "past half the budget: the rest is spread over the hours left")
game = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "rabbit", "game.js"), encoding="utf-8").read()
till = dict(re.findall(r'^    (\w+): "([0-9a-f]{96})"', game[game.index("const TILL = {"):game.index("const TILL_AT")], re.M))
check(till == {k: v for k, v in island.PLACES.items() if k != "hall"} and island.PLACES["hall"] == island.COUNCIL, "the same tills as the game")
import txsources  # noqa: E402
check(set(till.values()) == txsources.RABBIT_TILLS, "In numbers counts the same tills")
check(txsources.rabbit({"sender_pubkey": "ab", "operations": {"1": [["ab", island.PLACES["radio"], "25"]]}}, {}) == ("line", ""), "a move paid to a till is a Book line")

P = island.Island(path=os.path.join(tempfile.mkdtemp(), "k"), daily=50, clock=clock, enabled=True)
me = "ab" * 48
check(set(P.ppk) == set(island.PURSES) and not set(P.ppk.values()) & set(P.pk.values()), "the purses have their own keys")
ok, d = P.accept_pay("works", me.upper(), "3.3.3.3")
check(ok and d["queued"] and d["amount"] == 10 and d["from"] == P.ppk["works"], "a shift's wage is queued for the visitor")
check(P.accept_pay("bank", me, "3.3.3.3")[0] is False and P.accept_pay("works", "xyz", "3.3.3.3")[0] is False, "only the purses, only a wallet")
check(P.accept_pay("works", P.pk["hana"], "3.3.3.3")[0] is False, "never to the bot's own wallets")
for i in range(island.PAY_PER_WALLET - 1):
    P.accept_pay("north", me, f"4.4.{i}.1")
check(P.accept_pay("south", me, "5.5.5.5")[1]["why"] == "enough today", "a few payouts per wallet a day")
tx = P.build_pay("north", me, 3, 10, 10, 2)
check(tx["operations"]["1"][0] == [P.ppk["north"], me, "80"], "two waiting embassy payments ride together")
check(G2Basic.Verify(bytes.fromhex(tx["sender_pubkey"]), hashlib.sha256(island.signing_bytes(tx)).digest(), bytes.fromhex(tx["signature"])), "signed by the purse")
check(P.route("/island")["purses"] == P.ppk, "GET /island shows the purses")

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

"""Unit test of No Memo's crew purse (nomemo.py), no network: a claim seen on the relay, the share and the mark paid
once the claim is sealed, the Tracer's dust from the lookalike after a while, once per wallet, the board, the limits.

Run: python test_nomemo.py
"""
import asyncio
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hackweek  # noqa: E402
import nomemo  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


# a quick lookalike pair for the test (3 + 1 characters; the real one is 6 + 4)
pair = hackweek.grind(limit=20000, tag=lambda h: int(h[:3] + h[-1:], 16))
from py_ecc.bls import G2Basic  # noqa: E402
KEYS = {name: {"sk": sk.to_bytes(32, "big").hex(), "pk": G2Basic.SkToPk(sk).hex()} for name, sk in (("drop", pair[0]), ("shadow", pair[1]))}
PLAYER = "a" * 96
T = [1_700_000_000.0]
clock = lambda: T[0]   # noqa: E731


class Node:
    def __init__(self):
        self.sent, self.status, self.balance = [], {}, {}

    async def ask(self, cmd):
        c, *args = cmd.split(" ", 1)
        if c == "getsequence":
            return {"status": "ok", "data": {"sequence_number": 0, "tip_height": 500}}
        if c == "getbalance":
            return {"status": "ok", "data": {"address": args[0], "balance": self.balance.get(args[0], 100000)}}
        if c == "gettxstatus":
            return {"status": "ok", "data": self.status.get(args[0], {"status": "pending"})}
        if c == "sendtx":
            tx = json.loads(args[0])
            self.sent.append(tx)
            return {"status": "ok", "data": {"ok": True, "tx_hash": "h%d" % len(self.sent)}}
        return None


node = Node()
gov = lambda: {"consensus_rules": "(o9[t]:bv[24] = {#x00000a}:bv[24])"}   # noqa: E731
d = tempfile.mkdtemp()
m = nomemo.NoMemo(keys_path=os.path.join(d, "k"), state_path=os.path.join(d, "s.json"), clock=clock, enabled=True, tracer=True, keys=KEYS)
check(m.ready and m.pk["drop"] != m.pk["shadow"] and m.pk["drop"][:3] == m.pk["shadow"][:3], "the drop and its lookalike are known")
check(m.route("/nomemo")["drop"] == m.pk["drop"] and m.route("/nomemo")["board"]["wallets"] == 0, "GET /nomemo names the drop; the board is empty")


def claim(ch, h):
    return {"tx_type": "user_tx", "sender_pubkey": PLAYER, "operations": {"1": [[PLAYER, m.pk["drop"], str(100 + ch)]]}}, h


m.saw(*claim(1, "c1"))
check("1" in m.wallets[PLAYER]["claims"] and [j["kind"] for j in m.jobs] == ["share", "mark"], "a claim of chapter 1 queues the share and the mark")
m.saw(*claim(1, "c1b"))
check(len(m.jobs) == 2 and m.wallets[PLAYER]["claims"]["1"]["hash"] == "c1", "a second claim of the same chapter changes nothing")
m.saw({"tx_type": "user_tx", "sender_pubkey": PLAYER, "operations": {"1": [[PLAYER, m.pk["drop"], "7"]]}}, "p7")
check(len(m.jobs) == 2 and len(m.wallets) == 1, "an ordinary payment to the drop only puts the wallet on the board")
sent = asyncio.run(m.step(node.ask, gov))
check(sent is False and node.sent == [] and m.jobs[0]["asked"] == 1, "nothing is paid while the claim is pending")
node.status["c1"] = {"status": "confirmed", "block_number": 501}
node.balance[m.pk["drop"]] = 102   # the drop only ever received: the faucet will not fill it
T[0] += 30
sent = asyncio.run(m.step(node.ask, gov))
check(sent and len(node.sent) == 1 and node.sent[0]["operations"]["1"][0][1:] == [m.pk["drop"], str(nomemo.TOPUP)] and node.sent[0]["sender_pubkey"] == m.pk["bank"] and node.sent[0]["sender_pubkey"] != m.pk["drop"], "a drop too poor for the share is filled by a bank wallet first")
check(m.topup and m.topup["hash"] == "h1" and len(m.jobs) == 2, "the top-up is remembered until sealed; the share waits")
T[0] += 30
sent = asyncio.run(m.step(node.ask, gov))
check(sent is False and len(node.sent) == 1, "nothing goes out while the top-up is unsealed")
node.status["h1"] = {"status": "confirmed", "block_number": 502}
node.balance[m.pk["drop"]] = 102 + nomemo.TOPUP
T[0] += 30
sent = asyncio.run(m.step(node.ask, gov))
check(sent and len(node.sent) == 2 and node.sent[1]["operations"]["1"][0][1:] == [PLAYER, "500"] and node.sent[1]["sender_pubkey"] == m.pk["drop"] and m.topup is None, "the share of 500 goes out from the drop once the claim is sealed and the drop is filled")
node.sent.pop(0)   # the checks below count the drop's payments
check(m.wallets[PLAYER]["claims"]["1"]["paid"]["share"]["hash"] == "h2", "the share's hash is kept with the claim")
check([j["kind"] for j in m.jobs] == ["mark", "dust"], "the mark waits, and the Tracer's dust is queued")
sent = asyncio.run(m.step(node.ask, gov))
check(sent is False, "no two sends within the gap")
T[0] += 30
sent = asyncio.run(m.step(node.ask, gov))
check(sent and node.sent[-1]["operations"]["1"][0][2] == "1" and m.wallets[PLAYER]["claims"]["1"]["paid"]["mark"]["hash"] == "h2", "the mark: 1 test AGRS from the drop")
T[0] += 30
sent = asyncio.run(m.step(node.ask, gov))
check(sent is False and node.sent[-1]["operations"]["1"][0][2] == "1", "the dust waits its minutes")
T[0] += nomemo.DUST_AFTER
sent = asyncio.run(m.step(node.ask, gov))
check(sent and node.sent[-1]["sender_pubkey"] == m.pk["shadow"] and m.wallets[PLAYER]["dust"][0]["from"] == m.pk["shadow"], "the Tracer's dust comes from the lookalike")
w = m.route("/nomemo/wallet/" + PLAYER)
check(w["claims"]["1"]["paid"]["share"]["amount"] == 500 and len(w["dust"]) == 1 and w["drop"] == m.pk["drop"], "GET /nomemo/wallet/<address> shows the claim, what was paid and the dust")
b = m.route("/nomemo")["board"]
check(b["wallets"] == 1 and b["ranks"]["deckhand"] == 1 and b["claims"] == [1, 0, 0], "the board: one wallet, deckhand, one chapter claimed")
m.saw(*claim(2, "c2"))
node.status["c2"] = {"status": "confirmed", "block_number": 502}
T[0] += 30
asyncio.run(m.step(node.ask, gov))
check(node.sent[-1]["operations"]["1"][0][2] == "500" and not any(j["kind"] in ("mark", "dust") for j in m.jobs), "chapter 2: the share again, no second mark, no second dust")
check(m.route("/nomemo")["board"]["ranks"]["navigator"] == 1, "two chapters claimed: navigator")
m.saw(*claim(3, "c3"))
node.status["c3"] = {"status": "rejected"}
T[0] += 30
asyncio.run(m.step(node.ask, gov))
check("3" not in m.wallets[PLAYER]["claims"] and not m.jobs, "a claim the chain refused is forgotten, nothing paid")
OTHER = "b" * 96
T[0] += 10
m.saw({"tx_type": "user_tx", "sender_pubkey": OTHER, "operations": {"1": [[OTHER, m.pk["drop"], "1"]]}}, "o1")
b = m.route("/nomemo")["board"]
check(b["wallets"] == 2 and b["day"] == 2 and b["hour"] == 2 and b["last_move"] == int(T[0]), "the board counts the wallets of the last day and hour and the last move")
check(m.route("/nomemo/wallet/" + PLAYER)["nth"] == 1 and m.route("/nomemo/wallet/" + OTHER)["nth"] == 2 and m.route("/nomemo/wallet/" + "c" * 96)["nth"] is None, "nth: the how-many-th wallet to pay the drop")
T[0] += 7200
b = m.route("/nomemo")["board"]
check(b["day"] == 2 and b["hour"] == 0, "after two quiet hours: two today, none this hour")
m2 = nomemo.NoMemo(keys_path=os.path.join(d, "k"), state_path=os.path.join(d, "s.json"), clock=clock, enabled=True, keys=KEYS)
check(m2.wallets[PLAYER]["claims"]["1"]["paid"]["share"]["hash"] == "h2", "the state survives a restart")
check(m.route("/nomemo/wallet/zz") == {"error": "not an address"} and m.route("/other") is None, "bad paths")
off = nomemo.NoMemo(keys_path=os.path.join(d, "k2"), state_path=os.path.join(d, "s2.json"), clock=clock, enabled=False, background=False)
check(not off.ready and off.route("/nomemo")["enabled"] is False, "switched off: no keys made, the page is told")
print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

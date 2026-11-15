"""Walkers: who walks on White Rabbit Key, what the chain says about them, read once, our own wallets never."""
import os
import tempfile

from hearts import BOX
from txsources import BOWL, DEJA, GENESIS
from walkers import LOOK, Walkers, rule_parts

A, B, C, BOT = "aa" * 48, "bb" * 48, "cc" * 48, "dd" * 48
IDNI = sorted(GENESIS)[0]
NOW = 1_800_000_000


def blk(ts, h, *txs):
    return {"header": {"timestamp": ts, "block_number": h}, "transactions": [
        {"tx_type": "user_tx", "sender_pubkey": s, "operations": {"1": [[s, to, str(n)]]}} for s, to, n in txs]}


def rule(ts, h, s, text):
    return {"header": {"timestamp": ts, "block_number": h}, "transactions": [
        {"tx_type": "user_tx", "sender_pubkey": s, "operations": {"0": text}}]}


assert rule_parts("always ( (i1[t]:bv[24] > { #x0003e8 }:bv[24] && !(i18[t]:bv[384] = { #xab }:bv[384])) ? (o5[t]:bv[24] = { #x000000 }:bv[24]) : (o5[t]:bv[24] = { #x000001 }:bv[24]) ).") == ["co", "cap"]
assert rule_parts("always ( (o5[t]:bv[24] = { #x000000 }:bv[24]) ).") == ["freeze"]
assert rule_parts("always ( (i5[t]:bv[64] < {1800000000}:bv[64]) ? (o5[t]:bv[24] = { #x000000 }:bv[24]) : (o5[t]:bv[24] = { #x000001 }:bv[24]) ).") == ["from"]

path = os.path.join(tempfile.mkdtemp(), "walkers.json")
w = Walkers(path)
blocks = [
    blk(NOW - 3600, 10, (A, BOWL, 5), (B, C, 50), (BOT, A, 1)),
    blk(NOW - 3000, 11, (A, DEJA, 1), (A, BOX, 101), (A, BOX, 102), (A, BOX, LOOK + 77), (IDNI, B, 1000)),
    rule(NOW - 2000, 12, B, "always ( (i4[t]:bv[384] = { #x" + "ab" * 48 + " }:bv[384]) ? (o5[t]:bv[24] = { #x000001 }:bv[24]) : (o5[t]:bv[24] = { #x000000 }:bv[24]) )."),
    blk(NOW - 90000, 9, (C, A, 3)),
]
assert w.add_blocks(blocks, {BOT})
# reading the same blocks again (a relay restart) changes nothing
assert not w.add_blocks(blocks, {BOT})
assert w.w[A]["n"] == 5 and w.w[A]["meal"] == 1 and w.w[A]["deja"] == 1 and w.w[A]["heart"] == 2 and w.w[A]["look"] == 77
assert BOT not in w.w

act = w.active(NOW, ours={BOT})
keys = [x["a"] for x in act["walkers"]]
assert A in keys and B in keys and IDNI in keys and C not in keys, keys   # C was last active more than a day ago
assert act["total"] == 2 and act["idni"] == 1
a = next(x for x in act["walkers"] if x["a"] == A)
assert a["look"] == 77 and "feeder" in a["traits"] and "catfriend" in a["traits"] and "hearts" in a["traits"], a
b = next(x for x in act["walkers"] if x["a"] == B)
assert "lawmaker" in b["traits"] and "picky" in b["traits"] and b["home"] == "book", b
assert next(x for x in act["walkers"] if x["a"] == IDNI)["idni"]

# a wallet that becomes ours later (a passenger key learnt after its transactions) walks no more
assert A not in [x["a"] for x in w.active(NOW, ours={BOT, A})["walkers"]]

card = w.card(A, NOW, rabbit={"played": 2, "won": 1, "moves": 9, "fav": "hana"}, nomemo={"claims": {"1": {}, "2": {}}, "nth": 4})
tr = dict((k, n) for k, n in card["traits"])
assert tr["winner"] == 1 and tr["hacker"] == 2 and tr["politician"] == 9 and tr["allrounder"] >= 3, card["traits"]
assert card["traits"][0][0] == "winner"
assert card["rabbit"]["won"] == 1 and card["nomemo"]["chapters"] == 2
assert w.card("ee" * 48, NOW) is None

# night owl: most transactions between 22:00 and 05:00 German time (23:30 UTC in winter = 00:30)
n = Walkers(os.path.join(tempfile.mkdtemp(), "w.json"))
night = 1_800_000_000 - (1_800_000_000 % 86400) + 23 * 3600 + 1800
n.add_blocks([blk(night + k, 100 + k, (C, A, 1)) for k in range(8)])
assert "nightowl" in [k for k, _ in n.card(C, night + 100)["traits"]]

w.save(force=True)
again = Walkers(path)
assert again.active(NOW, ours={BOT}) == w.active(NOW, ours={BOT})
print("walkers ok")

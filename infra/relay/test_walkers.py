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
w.since = NOW - 10 * 86400   # a record that began long ago
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
# a record begun today calls nobody a newcomer: the blocks it read first may be old wallets
fresh = Walkers(os.path.join(tempfile.mkdtemp(), "f.json"))
fresh.add_blocks([blk(NOW - 100, 5, (A, C, 1))])
fresh.since = NOW - 3600
assert "newcomer" not in [k for k, _ in fresh.card(A, NOW)["traits"]]
fresh.since = NOW - 3 * 86400
assert "newcomer" in [k for k, _ in fresh.card(A, NOW)["traits"]]
print("walkers ok")

# ---------- the islander, part by part ----------
from walkers import PART, STRIDE, NS, face_sig, key_part, parts_of

P = "ee" * 48
w2 = Walkers(os.path.join(tempfile.mkdtemp(), "walkers.json"))
w2.since = NOW - 10 * 86400
# one transaction, three parts: eyes 3, mouth 6, earned piece 1 (a rule writer's sash); an amount past a part's choices is ignored
w2.add_blocks([{"header": {"timestamp": NOW - 500, "block_number": 50}, "transactions": [
    {"tx_type": "user_tx", "sender_pubkey": P, "operations": {"1": [[P, BOX, str(PART + 9 * STRIDE + 3)], [P, BOX, str(PART + 12 * STRIDE + 6)],
                                                                  [P, BOX, str(PART + 16 * STRIDE + 1)], [P, BOX, str(PART + 0 * STRIDE + 7)]]}}]}])
r = w2.w[P]
assert r["pt"][9] == 3 and r["pt"][12] == 6 and r["pt"][16] == 1 and r["pt"][0] is None, r["pt"]
assert r["heart"] == 0   # part payments are not hearts
row = next(x for x in w2.active(NOW)["walkers"] if x["a"] == P)
assert row["pt"][9] == 3 and row["pt"][0] == key_part(P, 0)
assert row["pt"][16] == 0, "the sash is shown only to a rule writer"
assert row.get("first") is True   # the first wallet to choose this face
sig = face_sig(parts_of(P, r["pt"]))
assert w2.face(sig)["first"] == P
# a later wallet choosing the same face is not the first; an older look payment still sets four parts
Q = "ef" * 48
same = [[Q, BOX, str(PART + i * STRIDE + v)] for i, v in enumerate(parts_of(P, r["pt"])) if i != 16]
w2.add_blocks([{"header": {"timestamp": NOW - 400, "block_number": 51}, "transactions": [
    {"tx_type": "user_tx", "sender_pubkey": Q, "operations": {"1": same}}]}])
assert w2.face(sig)["first"] == P and not next(x for x in w2.active(NOW)["walkers"] if x["a"] == Q).get("first")
w2.add_blocks([{"header": {"timestamp": NOW - 300, "block_number": 52}, "transactions": [
    {"tx_type": "user_tx", "sender_pubkey": Q, "operations": {"1": [[Q, BOX, str(LOOK + 2 * 64 + 3 * 8 + 5)]]}}]}])
assert w2.w[Q]["pt"][1] == 4 and w2.w[Q]["pt"][2] == 3 and w2.w[Q]["pt"][5] == 5 and w2.w[Q]["look"] == 2 * 64 + 29
# the cheap way (16.11): MARK + part, then PICK + choice; a PICK without a MARK, or past the part's choices, changes nothing
from walkers import MARK, PICK
Z = "ab" * 48
w2.add_blocks([{"header": {"timestamp": NOW - 250, "block_number": 52}, "transactions": [
    {"tx_type": "user_tx", "sender_pubkey": Z, "operations": {"1": [[Z, BOX, str(PICK + 2)], [Z, BOX, str(MARK + 9)], [Z, BOX, str(PICK + 4)],
                                                                  [Z, BOX, str(MARK + 0)], [Z, BOX, str(PICK + 9)], [Z, BOX, str(MARK + 2)], [Z, BOX, str(PICK + 15)]]}}]}])
assert w2.w[Z]["pt"][9] == 4 and w2.w[Z]["pt"][0] is None and w2.w[Z]["pt"][2] == 15 and w2.w[Z]["heart"] == 0, w2.w[Z]["pt"]
assert sum(1 for v in w2.w[Z]["pt"] if v is not None) == 2
# a rule writer may wear the sash
w2.add_blocks([rule(NOW - 200, 53, P, "always ( (o5[t]:bv[24] = { #x000001 }:bv[24]) ).")])
assert next(x for x in w2.active(NOW)["walkers"] if x["a"] == P)["pt"][16] == 1
card = w2.card(P, NOW)
assert card["face"]["mine"] and 1 in card["earned"] and card["pt"][16] == 1
# the chain: the newest block, a restart (newer, far lower), a refusal by the wallet's own rule
assert w2.active(NOW)["chain"]["height"] == 53
w2.add_blocks([blk(NOW - 100, 2, (P, C, 1))])
ch = w2.active(NOW)["chain"]
assert ch["restart"] == NOW - 100 and ch["height"] == 2
w2.held(P, NOW - 60)
assert next(x for x in w2.active(NOW)["walkers"] if x["a"] == P)["held"] == NOW - 60
# kept across a relay restart
w2.save(force=True)
w3 = Walkers(w2.path)
assert w3.faces == w2.faces and w3.restart == NOW - 100 and w3.w[P]["pt"][9] == 3
print("walkers parts ok")

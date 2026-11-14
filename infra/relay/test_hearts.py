"""Hearts: one heart per wallet and part, the newest mark wins, reading twice changes nothing, kept on disk."""
import os
import tempfile

from hearts import BOX, Hearts, decode, decode_level

A, B = "aa" * 48, "bb" * 48


def blk(ts, *txs):
    return {"header": {"timestamp": ts}, "transactions": [
        {"tx_type": "user_tx", "sender_pubkey": s, "operations": {"1": [[s, to, str(n)]]}} for s, to, n in txs]}


assert decode(101) == (1, True) and decode(205) == (5, False)
assert decode(100) is None and decode(200) is None and decode(300) is None and decode(12) is None and decode("x") is None

path = os.path.join(tempfile.mkdtemp(), "hearts.json")
h = Hearts(path)
assert h.add_blocks([blk(10, (A, BOX, 101), (B, BOX, 101), (A, BOX, 102))])
assert h.summary()["parts"] == {"1": 2, "2": 1} and h.summary()["wallets"] == 2
# a hundred clicks: on, off, on … in one block and across blocks; the last one stands, one heart at most
assert h.add_blocks([blk(20, *[(A, BOX, 201 if k % 2 == 0 else 101) for k in range(100)])])
assert h.summary()["parts"]["1"] == 2   # the 100th (k = 99) is a heart
h.add_blocks([blk(30, (A, BOX, 201))])
assert h.summary()["parts"] == {"1": 1, "2": 1}
# the same block read again, and an older block read late, change nothing
assert not h.add_blocks([blk(30, (A, BOX, 201))])
assert not h.add_blocks([blk(5, (A, BOX, 101))])
assert h.summary()["parts"]["1"] == 1
# other addresses, other amounts, other kinds of transactions are not hearts
assert not h.add_blocks([blk(40, (A, "cc" * 48, 101), (B, BOX, 50)), {"header": {"timestamp": 41}, "transactions": [{"tx_type": "rule_deploy", "sender_pubkey": A}]}])
h.save(force=True)
again = Hearts(path)
assert again.summary() == h.summary(), (again.summary(), h.summary())
# the level rides on top: 300 × (1 Beginner, 2 Intermediate, 3 Expert); a heart counts for its newest mark's level
assert decode_level(101) == (1, True, 0) and decode_level(401) == (1, True, 1) and decode_level(805) == (5, False, 2) and decode_level(1099) == (99, True, 3) and decode_level(1199) == (99, False, 3)
assert decode(401) == (1, True) and decode_level(400) is None and decode_level(1300) is None and decode_level(1401) is None
L = Hearts(os.path.join(tempfile.mkdtemp(), "hearts.json"))
L.add_blocks([blk(10, (A, BOX, 401), (B, BOX, 1001), (A, BOX, 102))])
lv = L.summary()["levels"]
assert L.summary()["parts"] == {"1": 2, "2": 1}
assert lv["new"] == {"1": 1} and lv["pro"] == {"1": 1} and lv["none"] == {"2": 1} and lv["mid"] == {}, lv
L.add_blocks([blk(20, (A, BOX, 701))])   # the same wallet, now Intermediate: its heart moves to that level
assert L.summary()["levels"]["new"] == {} and L.summary()["levels"]["mid"] == {"1": 1}
L.add_blocks([blk(30, (A, BOX, 1101))])  # taken back as an Expert: gone from every level
assert L.summary()["parts"] == {"1": 1, "2": 1} and L.summary()["levels"]["mid"] == {}
L.save(force=True)
assert Hearts(L.path).summary() == L.summary()
print("hearts ok")

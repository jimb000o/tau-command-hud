"""Hearts: one heart per wallet and part, the newest mark wins, reading twice changes nothing, kept on disk."""
import os
import tempfile

from hearts import BOX, Hearts, decode

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
print("hearts ok")

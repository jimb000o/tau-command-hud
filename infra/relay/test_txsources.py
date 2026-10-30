"""Unit test of where the testnet's transactions come from (txsources.py), no network.

Run: python test_txsources.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import txsources  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


BOWL = "947c2b8988769f9fb7ada19021e27c51f5d855e4e05ad258d2ca2322821987dbff93e0425f281edded5c372b97e6a108"
A, B, C = "aa" * 48, "bb" * 48, "cc" * 48
G = "8a39b9d9498535492290c52b44959b5a6e9177dc85ae6a1d97f54462f03c15a38052a85c7ace5cd81858e343a3b789d0"


def tx(sender, to):
    return {"sender_pubkey": sender, "operations": {"1": [[sender, to, "5"]]}}


path = os.path.join(tempfile.mkdtemp(), "sent.json")
s = txsources.TxSources(path)
s.note("H2")
s.note("h5", "agorzilla")
s.note(None)
check(json.load(open(path))["sent"] == {"h2": "", "h5": "agorzilla"}, "only hashes and a site name are written")
check(txsources.TxSources(path).sent == s.sent, "remembered after a restart")
day1, day2 = 1_793_145_600, 1_793_232_000   # 2026-10-28, 2026-10-29
blocks = [
    {"header": {"timestamp": 0}, "tx_ids": [], "transactions": []},
    {"header": {"timestamp": day1 + 60}, "tx_ids": ["h1", "h2", "h3"],
     "transactions": [tx(A, BOWL), tx(B, C), tx(C, A)]},
    {"header": {"timestamp": day1 + 120}, "tx_ids": ["h4"], "transactions": [tx(A, BOWL.upper())]},
    {"header": {"timestamp": day2 + 60}, "tx_ids": ["h5", "h6"], "transactions": [tx(B, C), tx(A, B)]},
    {"header": {"timestamp": day2 + 90}, "tx_ids": ["h8", "h9"], "transactions": [tx(G, B), tx(G, C)]},
    {"header": {}, "tx_ids": ["h7"], "transactions": [tx(A, B)]},
]
out = s.by_day(blocks)
check(out["days"]["2026-10-28"] == {"agorzilla": [2, 1], "tauhud": [1, 1], "idni": [0, 0], "other": [1, 1]},
      "a meal is Agorzilla's, a relay send Tau HUD's, the rest other; wallets counted once a day")
check(out["days"]["2026-10-29"] == {"agorzilla": [1, 1], "tauhud": [0, 0], "idni": [2, 1], "other": [1, 1]},
      "a send from agorzilla.com through the relay counts for Agorzilla, a genesis account for IDNI")
check(out["since"] == day1 + 60 and len(out["days"]) == 2, "blocks without a time are left out")
for i in range(txsources.SENT_MAX + 5):
    s.sent[f"x{i}"] = ""
s.note("last")
check(len(s.sent) == txsources.SENT_MAX and "last" in s.sent and "h2" not in s.sent, "the oldest hashes go first")
print("\n" + ("all ok" if not failed else f"{failed} failed"))
sys.exit(1 if failed else 0)

"""Unit test of active wallets over time (walletdays.py), no network.

Run: python test_walletdays.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import walletdays  # noqa: E402
from txsources import AGORZILLA, GENESIS, RABBIT_COUNCIL  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


DAY = 86400
D0 = 1_793_491_200   # 2026-11-01 00:00 UTC
IDNI = sorted(GENESIS)[0]
BOT, PLAYER, FEEDER, HUD, STRANGER = ("b0" * 48, "a1" * 48, "c2" * 48, "d3" * 48, "e4" * 48)
BOWL = sorted(AGORZILLA)[0]


def tx(sender, to="99" * 48, h=""):
    return {"sender_pubkey": sender, "operations": {"1": [[sender, to, "1"]]}, "tx_hash": h}


def block(ts, *txs):
    return {"header": {"timestamp": ts}, "transactions": list(txs), "tx_ids": [t.get("tx_hash") or "" for t in txs]}


path = os.path.join(tempfile.mkdtemp(), "walletdays.json")
w = walletdays.WalletDays(path)
w.bots = {BOT}
chain1 = [
    block(0),   # genesis: no time, nothing counted
    block(D0 + 100, tx(IDNI), tx(BOT, RABBIT_COUNCIL), tx(PLAYER, RABBIT_COUNCIL)),
    block(D0 + DAY + 50, tx(FEEDER, BOWL), tx(HUD, h="h1"), tx(STRANGER)),
]
check(w.add_blocks(chain1, {"h1": ""}), "new blocks are learnt")
check(not w.add_blocks(chain1, {"h1": ""}), "the same blocks again change nothing")
tags = dict(zip(w.keys, w.tag))
check(tags == {IDNI: "idni", BOT: "bot", PLAYER: "rabbit", FEEDER: "agorzilla", HUD: "tauhud", STRANGER: "other"},
      "each wallet gets its tag: genesis, island bot, player, feeder, Tau HUD wallet, other")

# the testnet restarts: a new chain from block 1 a few days later; the player comes back, the stranger does not
chain2 = [block(D0 + 3 * DAY + 10, tx(PLAYER, "77" * 48), tx(IDNI))]
w.add_blocks(chain2)
check(w.tag[w.index[PLAYER]] == "rabbit", "a wallet keeps its strongest tag")
w.save(D0 + 3 * DAY + 20, force=True)

# a new relay reads the file back
w2 = walletdays.WalletDays(path)
out = w2.history(D0 + 4 * DAY + 60)
T = out["tags"]
at = lambda d, win, tag: out["days"][d][str(win)][T.index(tag)]
check(out["since"] == "2026-11-01" and list(out["days"]) == ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"],
      "every day from the first recorded one to today, empty days included")
check(at("2026-11-02", 1, "other") == 1 and at("2026-11-03", 1, "other") == 0, "one-day window: only that day's senders")
check(at("2026-11-05", 7, "other") == 1 and at("2026-11-05", 7, "rabbit") == 1, "seven-day window reaches back across the restart")
check(at("2026-11-04", 90, "idni") == 1 and at("2026-11-04", 1, "idni") == 1, "IDNI counts once though it sent on both chains")
check(sum(out["days"]["2026-11-05"]["90"]) == 6, "90 days: all six wallets, each once")
check(out["new"]["2026-11-02"][T.index("agorzilla")] == 1 and "2026-11-04" not in out["new"], "new wallets by first day")
check(out["totals"][T.index("bot")] == 1, "totals per tag")

# passengers become known after their transactions were written down
PAX = "f5" * 48
w2.add_blocks([block(D0 + 4 * DAY, tx(PAX, "88" * 48))])
check(w2.tag[w2.index[PAX]] == "other", "an unknown passenger counts as other at first")
w2.cruise = {PAX}
w2.retag()
check(w2.tag[w2.index[PAX]] == "cruise", "and moves to cruise once the relay knows the passengers")

# nothing older than KEEP_DAYS stays in the file
w2.add_blocks([block(D0 - 500 * DAY, tx(STRANGER))])
w2.save(D0 + 4 * DAY, force=True)
with open(path) as f:
    check(min(json.load(f)["days"]) == "2026-11-01", "days older than KEEP_DAYS are dropped")

k = w2.known()
check(k.get(PLAYER) == "rabbit" and k.get(PAX) == "cruise" and HUD not in k and STRANGER not in k,
      "public tags: players and passengers yes, Tau HUD wallet and others never")

check(walletdays.WalletDays(os.path.join(tempfile.mkdtemp(), "none.json")).history(D0)["days"] == {}, "no file: empty history")

sys.exit(1 if failed else 0)

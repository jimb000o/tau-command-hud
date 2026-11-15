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

# White Rabbit Key players over time: rabbit wallets from their first move on the island, cumulative
PL2 = "a7" * 48
w3 = walletdays.WalletDays(os.path.join(tempfile.mkdtemp(), "p.json"))
w3.bots = {BOT}
w3.add_blocks([block(D0 + 10, tx(PL2, "55" * 48), tx(BOT, RABBIT_COUNCIL)),          # PL2 active, but not playing yet
               block(D0 + 2 * DAY, tx(PLAYER, RABBIT_COUNCIL), tx(PL2, RABBIT_COUNCIL), tx(IDNI, RABBIT_COUNCIL))])
w3.save(D0 + 2 * DAY, force=True)
pl = walletdays.WalletDays(w3.path).history(D0 + 3 * DAY)["players"]
check(pl["since"] == "2026-11-03" and pl["days"] == {"2026-11-03": [2, 2], "2026-11-04": [2, 0]},
      "players: counted from their first move, never the bot or IDNI, kept in the file, today included")
check(w.history(D0)["players"]["days"].get("2026-11-01") == [1, 1], "the first player of chain 1 counts on its day")

check(walletdays.WalletDays(os.path.join(tempfile.mkdtemp(), "none.json")).history(D0)["days"] == {}, "no file: empty history")

# which of our apps a visitor's wallet came from (GET /wallets/tags "apps")
from txsources import DEJA  # noqa: E402
NEWHUD, NEWNM, NEWCAT, OLDHUD, ELSE = "f1" * 48, "f2" * 48, "f3" * 48, "f4" * 48, "f5" * 48
w4 = walletdays.WalletDays(os.path.join(tempfile.mkdtemp(), "a.json"))
w4.bots = {BOT}
sent = {"x1": "", "x2": "|nomemo", "x3": "|wallet", "x4": "|start", "x5": "", "x6": "agorzilla"}
w4.add_blocks([block(D0 + 10, tx(OLDHUD, h="x1"), tx(BOT, h="x5"), tx(IDNI, BOWL))], sent)   # the record's first day
w4.add_blocks([block(D0 + DAY, tx(NEWHUD, h="x3"), tx(NEWNM, h="x2"), tx(NEWCAT, DEJA), tx(ELSE)),
               block(D0 + DAY + 60, tx(NEWHUD, BOWL), tx(NEWHUD, RABBIT_COUNCIL, h="x4"), tx(ELSE, h="x6"))], sent)
ap = w4.app_list()
check(ap.get(NEWHUD) == {"b": "tauhud", "d": "2026-11-02", "u": ["tauhud", "agorzilla", "rabbit"]},
      "a wallet new to the record: started in Tau HUD, then fed Agorzilla and played White Rabbit Key")
check(ap.get(NEWNM, {}).get("b") == "nomemo" and ap.get(NEWCAT, {}).get("b") == "deja", "No Memo and Déjà start a wallet too")
check(ap.get(OLDHUD) == {"u": ["tauhud"]}, "a wallet from the record's first day used Tau HUD, but no start is claimed")
check(ap.get(ELSE) == {"u": ["agorzilla"]}, "a wallet that started elsewhere: no start, then a send from agorzilla.com")
check(BOT not in ap and IDNI not in ap, "never our own server's wallets or IDNI's")
w4.save(D0 + 2 * DAY, force=True)
check(walletdays.WalletDays(w4.path).app_list() == ap, "apps kept in the file")
with open(w4.path) as f:
    old = json.load(f)
del old["apps"], old["born"]
with open(w4.path, "w") as f:
    json.dump(old, f)
back = walletdays.WalletDays(w4.path).app_list()
check(back.get(OLDHUD) == {"u": ["tauhud"]} and back.get(NEWHUD) == {"u": ["rabbit"]} and "b" not in back.get(NEWCAT, {}),
      "an older file: the app its tag names, no start claimed")

sys.exit(1 if failed else 0)

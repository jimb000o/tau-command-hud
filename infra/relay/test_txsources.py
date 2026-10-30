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
    {"header": {"timestamp": day2 + 7200}, "tx_ids": ["h10", "h11"], "transactions": [tx(A, BOWL), tx(C, BOWL)]},
    {"header": {}, "tx_ids": ["h7"], "transactions": [tx(A, B)]},
]
out = s.by_day(blocks)
check(out["days"]["2026-10-28"] == {"agorzilla": [2, 1, 1, 0, 10], "tauhud": [1, 1, 1, 0, 5], "idni": [0, 0, 0, 0, 0], "other": [1, 1, 1, 0, 5]},
      "a meal is Agorzilla's, a relay send Tau HUD's, the rest other; wallets counted once a day")
check(out["days"]["2026-10-29"] == {"agorzilla": [3, 3, 2, 1, 15], "tauhud": [0, 0, 0, 0, 0], "idni": [2, 1, 1, 0, 10], "other": [1, 1, 1, 0, 5]},
      "a send from agorzilla.com through the relay counts for Agorzilla, a genesis account for IDNI")
z = out["agorzilla"]["2026-10-28"]
check(z["meals"] == 2 and z["snacks"] == 1 and z["agrs"] == 10 and z["wallets"] == 1 and z["new"] == 1 and z["hours"][0] == 2,
      "Agorzilla per day: meals, a second meal within the hour is a snack, test AGRS fed, wallets")
z = out["agorzilla"]["2026-10-29"]
check(z["meals"] == 2 and z["new"] == 1 and z["snacks"] == 0, "a wallet's first meal counts as new, a meal hours later is no snack")
check(out["ours"]["2026-10-28"] == [3, 2, 2, 0, 15] and out["ours"]["2026-10-29"] == [3, 3, 1, 2, 15],
      "our two sites together: a wallet on both counts once; returning wallets")
check(out["totals"]["ours"] == {"7": 3, "30": 3, "all": 3} and out["totals"]["tauhud"]["all"] == 1, "distinct wallets over 7 / 30 days / all")
check(out["hours"]["2026-10-29"][0] == 1 and out["hours"]["2026-10-29"][2] == 2, "our transactions per hour")
check(out["since"] == day1 + 60 and len(out["days"]) == 2, "blocks without a time are left out")
check(out["starts"]["2026-10-28"] == {"agorzilla": {"meal": 2}, "tauhud:": {"send": 1}} and out["starts"]["2026-10-29"] == {"agorzilla": {"other": 1, "meal": 2}},
      "where our transactions started: Agorzilla meals (a plain send from agorzilla.com is other); a Tau HUD send from before pages were kept has no page")
DEJA = txsources.DEJA
s.note("v1", "", "start")
s.note("v2", "", "relay")
s.note("v3", "agorzilla")
check(s.sent["v1"] == "|start" and s.sent["v3"] == "agorzilla", "the page is kept next to the site, only when there is one")
out = s.by_day([{"header": {"timestamp": day2 + 60}, "tx_ids": ["v1", "v2", "v3"],
                 "transactions": [{"tx_type": "user_tx", "sender_pubkey": A, "operations": {"0": "always o5 = 1."}},
                                  {"tx_type": "consensus_rule_vote", "sender_pubkey": B},
                                  tx(C, DEJA)]}])
check(out["starts"]["2026-10-29"] == {"tauhud:start": {"rule": 1}, "tauhud:relay": {"vote": 1}, "deja": {"meal": 1}},
      "a rule sent from the wallet opened from /start/, the relay's own send, a meal for Déjà")
check(out["days"]["2026-10-29"]["tauhud"][0] == 2 and out["days"]["2026-10-29"]["agorzilla"][0] == 1, "the page does not change the site")
# White Rabbit Key: the rivals' moves from the island bot, a visitor's Book line and ballots
CO, MAR, HAN = txsources.RABBIT_COUNCIL, "b44a202e884682b8677daf5f2685b5775f3c9ea9443a89651013bc455bc66061f2cf8d092897893bad3311e598f2cb11", \
    "adf1b27a6cfe88b1c73f12ed38eaaef535f892ee2f2b695030427ecaef7d4e43deb89f7849f2f5550cc5eec711652174"
BOT = "dd" * 48
s.bots = {BOT.upper(): "tobias"}
out = s.by_day([{"header": {"timestamp": day1 + 3600}, "tx_ids": ["r1", "r2", "r3"], "transactions": [tx(BOT, CO), tx(BOT, CO), tx(A, CO)]},
                {"header": {"timestamp": day2 + 7200}, "tx_ids": ["r4", "r5", "r6"], "transactions": [tx(A, MAR), tx(B, HAN), tx(B, BOWL)]}])
r1, r2 = out["rabbit"]["2026-10-28"], out["rabbit"]["2026-10-29"]
check(r1["moves"] == 3 and r1["rivals"] == 2 and r1["by"] == {"tobias": 2} and r1["lines"] == 1 and r1["wallets"] == 1 and r1["new"] == 1 and r1["hours"][1] == 3,
      "White Rabbit Key: the bot's moves are the rivals', a visitor's line to the council is theirs; the bot is no visitor wallet")
check(r2["votes"] == 2 and r2["cands"] == {"marisol": 1, "hana": 1} and r2["wallets"] == 2 and r2["new"] == 1 and r2["agrs"] == 10,
      "ballots per candidate; a wallet that played before is not new; a meal for Agorzilla is not a move")
check(out["totals"]["rabbit"] == {"7": 2, "30": 2, "all": 2}, "visitor wallets on the island over 7 / 30 days / all")
s.bots = {}
for i in range(txsources.SENT_MAX + 5):
    s.sent[f"x{i}"] = ""
s.note("last")
check(len(s.sent) == txsources.SENT_MAX and "last" in s.sent and "h2" not in s.sent, "the oldest hashes go first")
print("\n" + ("all ok" if not failed else f"{failed} failed"))
sys.exit(1 if failed else 0)

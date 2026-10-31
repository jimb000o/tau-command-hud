"""Unit test of the firsts (no network): what the chain holds at the first run is history, each kind is posted once,
firsts close together go out as one post, a first in an old block is shown on the HUD but never posted, the HUD gets
them in proposals.json, removing a rule with the neutral clause is no first.

Run: python test_firsts.py   (needs websockets==15.0.1)
"""
import asyncio
import json
import os
import sys
import tempfile
import time

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="",
                  FIRSTS_QUIET_SECONDS="600", FIRSTS_HOLD_SECONDS="2700")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402
import firsts  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


class Fake(alerts.Outlet):
    def __init__(self, name):
        self.name, self.sent = name, []

    def enabled(self):
        return True

    def send_text(self, text):
        self.sent.append(text)
        return True, None, ""

    def send_with_picture(self, text, picture):
        return self.send_text(text)


A, B, C = "a" * 96, "b" * 96, "c" * 96
NOW = time.time()


def block(h, txs, ts=None):
    return {"block_hash": f"{h:064x}", "header": {"block_number": h, "timestamp": int(ts or NOW)},
            "transactions": txs, "tx_ids": [f"{h:02x}{i:062x}" for i in range(len(txs))]}


def pay(**kw):
    return {"sender_pubkey": A, "tx_type": "user_tx", "operations": {"1": [[A, B, "5"]]}, **kw}


POLICY = ("always ( ( (i1[t]:bv[24] > { #x0003e8 }:bv[24] && i5[t]:bv[64] < { 1800000000 }:bv[64]) "
          "|| (i1[t]:bv[24] > { #x000064 }:bv[24] && !(i18[t]:bv[384] = { #x" + C + " }:bv[384])) ) "
          "? (o5[t]:bv[24] = { #x000000 }:bv[24]) : (o5[t]:bv[24] = { #x000001 }:bv[24]) ).")


async def main():
    tg, x = Fake("telegram"), Fake("x")
    w = alerts.Watcher([tg, x])
    w.state["x"] = {}

    # first run: an old returnable payment is history
    w.blocks = {1: block(1, [pay()]), 2: block(2, [{"sender_pubkey": A, "tx_type": "retractable_transfer"}], NOW - 99999)}
    w.state["chain"] = {"block1_hash": w.blocks[1]["block_hash"]}
    w.process()
    st = w.state["firsts"]
    check(st["primed"] and "returnable" in st["seen"] and not st["pending"], "first run records, posts nothing")
    pub = json.load(open(os.path.join(TMP, "proposals.json")))
    check(pub["firsts"]["returnable"]["h"] == 2, "the HUD gets the first in proposals.json")

    # the neutral clause frees a place; it sets no rule, so it is no first
    w.blocks[3] = block(3, [pay(operations={"0": "always ( (o5[t]:bv[24] = { #x000001 }:bv[24]) )."})])
    w.process()
    check(not st["pending"], "removing a rule is no first")

    # the demo: a policy with clock and co-signer, a request, a vote, a take-back, in quick succession
    w.blocks[4] = block(4, [pay(operations={"0": POLICY})])
    w.blocks[5] = block(5, [{"sender_pubkey": A, "tx_type": "approval_request"}, {"sender_pubkey": C, "tx_type": "transfer_vote", "approve": True}])
    w.blocks[6] = block(6, [{"sender_pubkey": A, "tx_type": "retract_transfer"}, {"sender_pubkey": A, "tx_type": "retractable_transfer"}])
    w.process()
    keys = [f["key"] for f in st["pending"]]
    check(sorted(keys) == sorted(["time_lock", "cosign_rule", "cosign_request", "cosign_vote", "taken_back"]),
          "five new firsts pending, the returnable one not again")

    await w.maybe_firsts(time.time() + 60)
    check(not tg.sent, "waits while firsts keep coming")
    await w.maybe_firsts(time.time() + 700)
    check(len(tg.sent) == 1 and "money with terms" in tg.sent[0] and tg.sent[0].count("•") == 5, "one post for all five")
    check("explorer/?tx=" in tg.sent[0] and "block #6" in tg.sent[0], "each first links its transaction")
    check(len(x.sent) == 1 and "http" not in x.sent[0] and len(x.sent[0]) <= 280, "the X copy: one post, no link, fits")
    check(tg.sent[0].index("A payment taken back") < tg.sent[0].index("A rule that follows the clock")
          < tg.sent[0].index("A co-signer approved"), "told in the order of KINDS")

    # nothing twice
    w.blocks[7] = block(7, [{"sender_pubkey": A, "tx_type": "retract_transfer"}])
    w.process()
    await w.maybe_firsts(time.time() + 5000)
    check(len(tg.sent) == 1, "a kind is posted once")

    # a first from a block older than POST_MAX_AGE (caught up after an outage) is shown, not posted
    st["seen"].pop("cosign_vote")
    w.blocks[5]["transactions"].pop()
    w.blocks[8] = block(8, [{"sender_pubkey": C, "tx_type": "transfer_vote", "approve": True}], NOW - alerts.POST_MAX_AGE - 600)
    w.process()
    await w.maybe_firsts(time.time() + 9000)
    check(len(tg.sent) == 1 and "cosign_vote" in st["seen"], "an old first is recorded, not posted late")

    # a new chain starts the record over
    w.blocks = {1: block(1, [{"sender_pubkey": A, "tx_type": "retractable_transfer"}])}
    w.blocks[1]["block_hash"] = "f" * 64
    w.state["chain"] = {"block1_hash": "f" * 64}
    w.process()
    check(list(st["seen"]) == ["returnable"] and [f["key"] for f in st["pending"]] == ["returnable"], "a new chain has its own firsts")
    check(firsts.headline(st["pending"]) == "First on the testnet: a returnable payment", "one first has its own headline")
    sys.exit(1 if failed else 0)


asyncio.run(main())

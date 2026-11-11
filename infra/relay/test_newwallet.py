"""Unit test, no network: our node has no room for a new wallet (IDNI tau-testnet #108, since 11 November 2026). The
relay's answer to a visitor says why (relay.py explain_new_wallet), only while that is the cause, so the text ends by
itself once the node takes new wallets again; and the load counter knows when the node last took a transaction.

Run: python test_newwallet.py
"""
import asyncio
import json
import os
import sys
import tempfile
import time
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import relay  # noqa: E402
from load import Load  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


NEW, OLD, OTHER = "ee" * 48, "ab" * 48, "cd" * 48
BAL = {NEW: 0, OLD: 100000, OTHER: 100000}
asked: list[str] = []


class Way:
    async def request(self, cmd, timeout=None):
        asked.append(cmd)
        c, _, a = cmd.partition(" ")
        if c == "getbalance":
            return {"status": "ok", "data": {"address": a, "balance": BAL.get(a, 0)}}
        return None


class Mute(Way):
    async def request(self, cmd, timeout=None):
        return None


NODE = {"status": "error", "command": "sendtx",
        "error": {"code": "ADMISSION_UNAVAILABLE", "message": "Transaction validation is temporarily unavailable; please resubmit."}}
me = types.SimpleNamespace(load=types.SimpleNamespace(last_ok=time.time()))


def pay(sender, to):
    return json.dumps({"tx_type": "user_tx", "sender_pubkey": sender, "operations": {"1": [[sender, to, "5"]]}})


def explain(tx, way=None, node=None):
    return asyncio.run(relay.Relay.explain_new_wallet(me, node or NODE, tx, way or Way()))


m = explain(pay(NEW, OTHER))
e = m.get("error") or {}
check(m["status"] == "error" and e.get("code") == "ADMISSION_UNAVAILABLE" and e.get("message") == relay.NEW_WALLET_MESSAGE
      and "resubmit" in (e.get("node_message") or "") and e.get("issue", "").endswith("/issues/108") and e.get("reason") == "new_wallet",
      "a new wallet sends: the answer says our node has no room for it, the node's own words kept")
check(NODE["error"]["message"].endswith("please resubmit."), "the node's answer itself is left as it was")
check("254" in relay.NEW_WALLET_MESSAGE and "still work" in relay.NEW_WALLET_MESSAGE and "Nothing was sent" in relay.NEW_WALLET_MESSAGE,
      "the text says the limit, that known wallets work, and that nothing was sent")
check(explain(pay(OLD, NEW))["error"]["message"] == relay.NEW_WALLET_MESSAGE, "a payment to a new wallet: the same")
check(explain(json.dumps({"tx_type": "retractable_transfer", "sender_pubkey": OLD, "recipient_pubkey": NEW, "amount": 5}))["error"]["message"]
      == relay.NEW_WALLET_MESSAGE, "a booking (retractable transfer) to a new wallet: the same")
check(explain(pay(OLD, OTHER)) is NODE, "only wallets the chain knows (balance above 0): the node's own answer, untouched")
me.load.last_ok = time.time() - relay.NEW_WALLET_OK - 1
n = len(asked)
check(explain(pay(NEW, OTHER)) is NODE and len(asked) == n,
      "nothing taken through the relay lately: the node's own trouble, its answer stays and nothing is asked")
me.load.last_ok = time.time()
check(explain(pay(NEW, OTHER), Mute()) is NODE, "no answer to the balance question: the node's answer stays")
check(explain("not json") is NODE, "not JSON: unchanged")
RULE = {"status": "error", "command": "sendtx",
        "error": {"code": "ADMISSION_UNAVAILABLE", "message": "Rule validation is temporarily unavailable; please resubmit."}}
n = len(asked)
check(explain(pay(NEW, OTHER), node=RULE) is RULE and len(asked) == n,
      "the same code for a rule the node could not check: the node's own answer, nothing asked")

L = Load(path=os.path.join(tempfile.mkdtemp(), "load.json"), clock=lambda: 1000.0)
L.sent("refused")
check(L.last_ok == 0, "a refusal is no sign the node takes transactions")
L.sent("bot")
check(L.last_ok == 1000.0, "a transaction the node took is")

print()
print("all ok" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)

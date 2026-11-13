"""Unit test of the showcase wallets (showcase.py), no network: the three rules in the words the HUD reads, set on a fake
node, each wallet's daily try refused by its own rule and handed to the relay, one try a day, the rules set again after
a testnet restart, a try the node takes kept as a finding, and the piggy bank left alone after New Year.

Run: python test_showcase.py
"""
import asyncio
import datetime as dt
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cruise  # noqa: E402
import showcase  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


class Node:
    """Takes a rule into force at once; refuses a transfer its sender's rule forbids, the way tau-testnet words it."""
    def __init__(self, obey=True):
        self.clauses, self.seq, self.sent, self.obey = {}, {}, [], obey

    async def ask(self, cmd):
        verb, _, rest = cmd.partition(" ")
        if verb == "getsequence":
            return {"status": "ok", "data": {"sequence_number": self.seq.get(rest, 0), "tip_height": 50}}
        if verb == "getruleoffers":
            pk = rest.split()[0]
            c = self.clauses.get(pk)
            return {"status": "ok", "data": {"accepted_clauses": [{"target_stream": "o5", "clause_body": c}] if c else [], "offers": []}}
        if verb == "sendtx":
            tx = json.loads(rest)
            self.sent.append(tx)
            pk, ops = tx["sender_pubkey"], tx["operations"]
            if "0" in ops:
                self.clauses[pk] = ops["0"]
                self.seq[pk] = self.seq.get(pk, 0) + 1
                return {"status": "ok", "data": {"ok": True, "tx_hash": "r%d" % len(self.sent)}}
            if self.obey and self.clauses.get(pk):
                return {"status": "error", "error": {"code": "TX_REJECTED", "message":
                        "Transaction rejected: the sender's own policy clause blocked transfer #1 (...). Policy output: 0"}}
            self.seq[pk] = self.seq.get(pk, 0) + 1
            return {"status": "ok", "data": {"ok": True, "tx_hash": "t%d" % len(self.sent)}}
        return None


def gov():
    return {"consensus_rules": "o9[t]:bv[24] = { #x00000a }"}


async def run(sc, node, clock, until, step=5):
    while clock.t < until:
        await sc.step(node.ask, gov)
        clock.t += step


tmp = tempfile.mkdtemp()
DAY = dt.date(2026, 11, 14)
clock = Clock(cruise.berlin_t(DAY, 9))
sc = showcase.Showcase(keys_path=os.path.join(tmp, "k"), state_path=os.path.join(tmp, "s.json"), clock=clock, enabled=True)
check(sc.ready and len(sc.pk) == 4 and len(set(sc.pk.values())) == 4, "four fresh keys: three wallets and the co-signer")
check(oct(os.stat(os.path.join(tmp, "k")).st_mode & 0o777) == "0o600", "the keys file is readable by its owner only")
refused = []
sc.on_refused = refused.append

# the rule texts as the HUD's policyFromText reads them (index.html): which stream, which number
pig, four, feed = sc.rule("piggy"), sc.rule("foureyes"), sc.rule("feeding")
check(re.search(r"i5\[t\][^<>]*[<>]=?\s*\{\s*(\d+)", pig).group(1) == str(cruise.berlin_t(dt.date(2027, 1, 1), 0)),
      "piggy bank: a time-lock on i5 until New Year, 00:00 German time (the HUD reads the number)")
check("i6" not in pig, "no block height in the piggy bank's rule: a clause may not read i6")
check(re.search(r"i18\[t\][^=]*=\s*\{\s*#x([0-9a-fA-F]{8,})", four).group(1) == sc.pk["cosigner"]
      and re.search(r"i[12]\[t\][^<>]*[<>]=?\s*\{\s*(#x[0-9a-fA-F]+|\d+)", four).group(1) == "#x000064",
      "four-eyes wallet: above 100 the co-signer's vote in slot i18")
check(re.search(r"i4\[t\][^=]*=\s*\{\s*#x([0-9a-fA-F]{8,})", feed).group(1) == showcase.BOWL and "i1[t]" not in feed,
      "feeding fund: only Agorzilla's bowl (i4), no amount in it, so the HUD reads it as a whitelist")
for r in (pig, four, feed):
    check(r.startswith("always ( ") and r.endswith(" ).") and "o5[t]:bv[24]" in r and "i12" not in r and r.count("(") == r.count(")"),
          "one always unit writing o5, no i12, balanced: " + r[:40] + "…")

node = Node()
asyncio.run(run(sc, node, clock, cruise.berlin_t(DAY, 10)))
rules = [t for t in node.sent if "0" in t["operations"]]
check(len(rules) == 3 and all(sc.w(n).get("in_force") for n in showcase.WALLETS), "the three rules are set and seen in force")
check(not any("1" in t["operations"] for t in node.sent), "no try before its German hour")
check(all(t["fee_limit"] == "50" and t["signature"] for t in node.sent), "signed, fee limit five times the base fee")

asyncio.run(run(sc, node, clock, cruise.berlin_t(DAY, 20)))
tries = [t for t in node.sent if "1" in t["operations"]]
check(len(tries) == 3, "one try per wallet on the day")
check([sc.pk.get(n) for n in ("piggy", "foureyes", "feeding")] == [t["sender_pubkey"] for t in tries], "at 11, 15 and 19 German time, in that order")
check(tries[1]["operations"]["1"][0][2] == "250" and tries[2]["operations"]["1"][0][1] == sc.pk["piggy"],
      "four-eyes tries 250 without a co-signature, the feeding fund pays the piggy bank instead of the bowl")
check(len(refused) == 3 and all(e["reason"].startswith("o5 = 0") and e["left"] and len(e["tx_hash"]) == 64 for e in refused),
      "each refusal goes to the relay's dropped list with an o5 reason, so the HUD says: stopped by the sender's own rule")
check(all(sc.w(n)["last"]["outcome"] == "stopped" for n in showcase.WALLETS), "/showcase shows each last try as stopped")

asyncio.run(run(sc, node, clock, cruise.berlin_t(DAY, 23)))
check(len([t for t in node.sent if "1" in t["operations"]]) == 3, "no second try the same day")

# a testnet restart: the node forgets everything, the relay calls recheck(); the rules come back, the next day's tries follow
node.clauses.clear()
node.seq.clear()
sc.recheck()
asyncio.run(run(sc, node, clock, cruise.berlin_t(DAY + dt.timedelta(days=1), 10)))
check(len([t for t in node.sent if "0" in t["operations"]]) == 6, "after a restart the three rules are set again")
asyncio.run(run(sc, node, clock, cruise.berlin_t(DAY + dt.timedelta(days=1), 20)))
check(len(refused) == 6, "and the next day's three tries are refused again")

# state across a relay restart: the same keys, the same day's tries remembered
sc2 = showcase.Showcase(keys_path=os.path.join(tmp, "k"), state_path=os.path.join(tmp, "s.json"), clock=clock, enabled=True)
check(sc2.pk == sc.pk and sc2.w("piggy").get("tried") == (DAY + dt.timedelta(days=1)).isoformat(), "keys and the day's tries survive a relay restart")
snap = sc2.snapshot()
check(snap["wallets"]["feeding"]["name"] == "Tau HUD's Agorzilla feeding fund" and snap["cosigner"]["pk"] == sc.pk["cosigner"]
      and "sk" not in json.dumps(snap), "GET /showcase: names, rules in words, the co-signer, never a secret key")

# a node that takes a forbidden payment: a finding, not retried, nothing to the feed
tmp2 = tempfile.mkdtemp()
clock2 = Clock(cruise.berlin_t(DAY, 9))
bad = showcase.Showcase(keys_path=os.path.join(tmp2, "k"), state_path=os.path.join(tmp2, "s.json"), clock=clock2, enabled=True)
out = []
bad.on_refused = out.append
loose = Node(obey=False)
asyncio.run(run(bad, loose, clock2, cruise.berlin_t(DAY, 23)))
check(not out and all(bad.w(n)["last"]["outcome"] == "took" for n in showcase.WALLETS)
      and sum("FINDING" in x["note"] for x in bad.st["log"]) == 3, "a payment the node took against the rule is a finding, not a feed line")

# after New Year the piggy bank's lock is open by itself: no more tries from it
clock2.t = cruise.berlin_t(dt.date(2027, 1, 2), 9)
n = len(loose.sent)
asyncio.run(run(bad, loose, clock2, cruise.berlin_t(dt.date(2027, 1, 2), 23)))
late = [t["sender_pubkey"] for t in loose.sent[n:] if "1" in t["operations"]]
check(bad.pk["piggy"] not in late and len(late) == 2, "after New Year the piggy bank no longer tries; the other two do")

print("all ok" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)

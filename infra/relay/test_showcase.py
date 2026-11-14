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
        self.clauses, self.seq, self.sent, self.obey, self.offers = {}, {}, [], obey, {}

    async def ask(self, cmd):
        verb, _, rest = cmd.partition(" ")
        if verb == "getsequence":
            return {"status": "ok", "data": {"sequence_number": self.seq.get(rest, 0), "tip_height": 50}}
        if verb == "getruleoffers":
            pk = rest.split()[0]
            c = self.clauses.get(pk)
            inc = [{k: v for k, v in o.items() if k != "rule_text"} for o in self.offers.values() if o["recipient_pubkey"] == pk]
            return {"status": "ok", "data": {"accepted_clauses": [{"target_stream": "o5", "clause_body": c}] if c else [], "incoming": inc}}
        if verb == "getruleoffer":
            return {"status": "ok", "data": self.offers.get(rest.strip())}
        if verb == "sendtx":
            tx = json.loads(rest)
            self.sent.append(tx)
            pk = tx["sender_pubkey"]
            if tx["tx_type"] == "rule_offer":
                oid = "o%d" % len(self.offers)
                self.offers[oid] = {"offer_id": oid, "offerer_pubkey": pk, "recipient_pubkey": tx["recipient_pubkey"], "rule_text": tx["rule_text"],
                                    "expire_at_height": tx["expire_at_height"], "status": "offered"}
                return {"status": "ok", "data": {"ok": True, "tx_hash": "x%d" % len(self.sent)}}
            if tx["tx_type"] == "rule_offer_accept":
                o = self.offers[tx["offer_id"]]
                assert o["recipient_pubkey"] == pk and o["rule_text"] == tx["rule_text"]
                o["status"] = "accepted"
                self.clauses[pk] = tx["rule_text"]
                return {"status": "ok", "data": {"ok": True, "tx_hash": "a%d" % len(self.sent)}}
            if tx["tx_type"] == "rule_offer_reject":
                self.offers[tx["offer_id"]]["status"] = "rejected"
                return {"status": "ok", "data": {"ok": True, "tx_hash": "j%d" % len(self.sent)}}
            ops = tx["operations"]
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
check(sc.ready and len(sc.pk) == 7 and len(set(sc.pk.values())) == 7, "seven fresh keys: three wallets, the co-signer, the apprentice, the stranger, the rule desk")
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
check(re.search(r"i4\[t\][^=]*=\s*\{\s*#x([0-9a-fA-F]{8,})", feed).group(1) == showcase.BOWL
      and "i1[t]:bv[24] > { #x000014 }" in feed and "i2[t]:bv[24] < { #x015f90 }" in feed,
      "feeding fund: only Agorzilla's bowl (i4), at most 20 a meal (i1), nothing below 90,000 (i2)")
check("i2[t]:bv[24] < { #x015f90 }" in four and four.count("i18[t]") == 1,
      "four-eyes: below 90,000 every payment needs the co-signer too (one co-signer guard, far from IDNI #111's 10)")
for r in (pig, four, feed):
    check(r.startswith("always ( ") and r.endswith(" ).") and "o5[t]:bv[24]" in r and "i12" not in r and r.count("(") == r.count(")"),
          "one always unit writing o5, no i12, balanced: " + r[:40] + "…")

node = Node()
asyncio.run(run(sc, node, clock, cruise.berlin_t(DAY, 10)))
rules = [t for t in node.sent if "0" in t.get("operations", {})]
check(len(rules) == 3 and all(sc.w(n).get("in_force") for n in showcase.WALLETS), "the three rules are set and seen in force")
check(not any("1" in t.get("operations", {}) for t in node.sent), "no try before its German hour")
check(all(t["fee_limit"] == "50" and t["signature"] for t in node.sent), "signed, fee limit five times the base fee")

asyncio.run(run(sc, node, clock, cruise.berlin_t(DAY, 20)))
tries = [t for t in node.sent if "1" in t.get("operations", {})]
check(len(tries) == 3, "one try per wallet on the day")
check([sc.pk.get(n) for n in ("piggy", "foureyes", "feeding")] == [t["sender_pubkey"] for t in tries], "at 11, 15 and 19 German time, in that order")
check(tries[1]["operations"]["1"][0][2] == "250" and tries[2]["operations"]["1"][0][1] == sc.pk["piggy"],
      "four-eyes tries 250 without a co-signature, the feeding fund pays the piggy bank instead of the bowl")
check(len(refused) == 3 and all(e["reason"].startswith("o5 = 0") and e["left"] and len(e["tx_hash"]) == 64 for e in refused),
      "each refusal goes to the relay's dropped list with an o5 reason, so the HUD says: stopped by the sender's own rule")
check(all(sc.w(n)["last"]["outcome"] == "stopped" for n in showcase.WALLETS), "/showcase shows each last try as stopped")

asyncio.run(run(sc, node, clock, cruise.berlin_t(DAY, 23)))
check(len([t for t in node.sent if "1" in t.get("operations", {})]) == 3, "no second try the same day")

# a testnet restart: the node forgets everything, the relay calls recheck(); the rules come back, the next day's tries follow
node.clauses.clear()
node.seq.clear()
sc.recheck()
asyncio.run(run(sc, node, clock, cruise.berlin_t(DAY + dt.timedelta(days=1), 10)))
check(len([t for t in node.sent if "0" in t.get("operations", {})]) == 6, "after a restart the three rules are set again")
asyncio.run(run(sc, node, clock, cruise.berlin_t(DAY + dt.timedelta(days=1), 20)))
check(len(refused) == 6, "and the next day's three tries are refused again")

# state across a relay restart: the same keys, the same day's tries remembered
sc2 = showcase.Showcase(keys_path=os.path.join(tmp, "k"), state_path=os.path.join(tmp, "s.json"), clock=clock, enabled=True)
check(sc2.pk == sc.pk and sc2.w("piggy").get("tried") == (DAY + dt.timedelta(days=1)).isoformat(), "keys and the day's tries survive a relay restart")
snap = sc2.snapshot()
check(snap["wallets"]["feeding"]["name"] == "Tau HUD's Agorzilla feeding fund" and snap["cosigner"]["pk"] == sc.pk["cosigner"]
      and not any(k["sk"] in json.dumps(snap) for k in json.load(open(os.path.join(tmp, "k"))).values()), "GET /showcase: names, rules in words, the co-signer, never a secret key")

# rule sharing: the day's three stories ran between 12 and 14 German time (on DAY and the day after)
offers = list(node.offers.values())
by = {}
for o in offers:
    by.setdefault((o["offerer_pubkey"], o["recipient_pubkey"]), o)   # the first day's
g = by.get((sc.pk["piggy"], sc.pk["apprentice"]))
check(g and g["status"] == "accepted" and node.clauses.get(sc.pk["apprentice"]) == sc.rule("piggy"),
      "gift: the piggy bank offers its rule, the apprentice accepts it and holds it as its own")
sm = by.get((sc.pk["stranger"], sc.pk["foureyes"]))
check(sm and sm["status"] == "rejected" and node.clauses.get(sc.pk["foureyes"]) == sc.rule("foureyes"),
      "scam: the stranger's pay-only-me rule is declined, the four-eyes wallet keeps its own rule")
ig = by.get((sc.pk["stranger"], sc.pk["feeding"]))
check(ig and ig["status"] == "offered" and ig["expire_at_height"] == 50 + showcase.IGNORED_WINDOW, "ignored: an offer nobody answers, open for 15 blocks")
check([o["status"] for o in offers if o["offerer_pubkey"] == sc.pk["piggy"]] == ["accepted", "accepted"], "one gift a day, two days, both accepted")
check(sc.review(sc.story_rule("scam"), sc.pk["stranger"]) and not sc.review(sc.rule("feeding"), sc.pk["stranger"]),
      "the review catches a rule that pays only its offerer, not a whitelist naming someone else")
check(all(t["tx_type"] != "rule_offer" or t["expire_at_height"] - 50 in (showcase.OFFER_WINDOW, showcase.IGNORED_WINDOW) for t in node.sent),
      "an offer's expiry is its height deadline")

# the desk: a visitor's wallet asks, gets one starter offer; limits per wallet, per address and per day
vis = "ab" * 48
a = sc.ask_offer(vis, "1.2.3.4")
check(a["ok"] and a.get("queued") and sc.ask_offer(vis, "1.2.3.4").get("already"), "a visitor's wallet asks once; asking again changes nothing")
check(not sc.ask_offer("xyz", "1.2.3.4")["ok"] and not sc.ask_offer(sc.pk["piggy"], "1.2.3.4")["ok"], "no offer to a bad address or to our own wallets")
for i in range(3):
    sc.ask_offer("%096x" % (i + 1), "5.6.7.8")
check(not sc.ask_offer("%096x" % 9, "5.6.7.8")["ok"], "three a day from one address")
n = len(node.sent)
asyncio.run(run(sc, node, clock, clock.t + 600))
desk = [t for t in node.sent[n:] if t["tx_type"] == "rule_offer" and t["sender_pubkey"] == sc.pk["desk"]]
check(len(desk) == 4 and desk[0]["recipient_pubkey"] == vis and desk[0]["rule_text"] == sc.starter_rule()
      and desk[0]["expire_at_height"] == 50 + showcase.VISITOR_WINDOW, "the desk sends the four starter offers: at most 1,000 per payment, open ~1000 blocks")
check("sharers" in sc.snapshot() and sc.snapshot()["stories"]["scam"]["result"] == "rejected", "GET /showcase shows the sharing wallets and the stories")
check(sc.route("/showcase/offer", "to=" + "cd" * 48, "9.9.9.9")["ok"], "GET /showcase/offer?to=… asks the desk")

# old keys file with four keys: the sharing wallets are added, the old ones kept
tmp3 = tempfile.mkdtemp()
old = {k: v for k, v in json.load(open(os.path.join(tmp, "k"))).items() if k in ("piggy", "foureyes", "feeding", "cosigner")}
json.dump(old, open(os.path.join(tmp3, "k"), "w"))
sc3 = showcase.Showcase(keys_path=os.path.join(tmp3, "k"), state_path=os.path.join(tmp3, "s.json"), clock=clock, enabled=True)
check(sc3.ready and sc3.pk["piggy"] == sc.pk["piggy"] and len(json.load(open(os.path.join(tmp3, "k")))) == 7, "an older keys file gets the three new keys, the old ones stay")

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
late = [t["sender_pubkey"] for t in loose.sent[n:] if "1" in t.get("operations", {})]
check(bad.pk["piggy"] not in late and len(late) == 2, "after New Year the piggy bank no longer tries; the other two do")

# the co-signer for No Memo's Four eyes, two keys: signs an open request from the asking address, up to COSIGN_MAX
class Inbox(Node):
    def __init__(self, cosigner, rows):
        super().__init__()
        self.cosigner, self.rows = cosigner, rows

    async def ask(self, cmd):
        if cmd == f"getapprovalrequests {self.cosigner} in":
            return {"status": "ok", "data": {"incoming": self.rows}}
        if cmd.startswith("sendtx "):
            tx = json.loads(cmd[7:])
            self.sent.append(tx)
            return {"status": "ok", "data": {"ok": True, "tx_hash": "v%d" % len(self.sent)}}
        return await super().ask(cmd)


tmp4 = tempfile.mkdtemp()
clock4 = Clock(cruise.berlin_t(DAY, 9))
co = showcase.Showcase(keys_path=os.path.join(tmp4, "k"), state_path=os.path.join(tmp4, "s.json"), clock=clock4, enabled=True)
P, Q = "ab" * 48, "ef" * 48
good, big, other = "11" * 32, "22" * 32, "33" * 32
rows = [{"request_id": good, "sender_pubkey": P, "amount": 600, "status": "open"},
        {"request_id": big, "sender_pubkey": P, "amount": showcase.COSIGN_MAX + 1, "status": "open"},
        {"request_id": other, "sender_pubkey": Q, "amount": 600, "status": "open"}]
inbox = Inbox(co.pk["cosigner"], rows)
for bad_q, why in (("id=zz&from=" + P, "a request id that is no hex"), ("id=" + good + "&from=12", "an address that is no key")):
    check(co.route("/showcase/cosign", bad_q, "1.1.1.1")["ok"] is False, "refused: " + why)
check(co.route("/showcase/cosign", f"id={good}&from={P}", "1.1.1.1").get("queued") and co.route("/showcase/cosign", f"id={good}&from={P}", "1.1.1.1").get("already"),
      "GET /showcase/cosign queues a request once")
co.route("/showcase/cosign", f"id={big}&from={P}", "1.1.1.1")
co.route("/showcase/cosign", f"id={other}&from={P}", "1.1.1.1")
co.route("/showcase/cosign", f"id={'44' * 32}&from={P}", "1.1.1.1")
for st in co.st["wallets"].values():   # the wallets' rules are in force and tried today: the slots go to the votes
    st.update(checked=int(clock4.t), in_force=True, tried=showcase.berlin_day(clock4.t).isoformat())
asyncio.run(run(co, inbox, clock4, clock4.t + 400))
votes = [t for t in inbox.sent if t["tx_type"] == "transfer_vote"]
check(len(votes) == 1 and votes[0]["request_id"] == good and votes[0]["approve"] is True and votes[0]["fee_limit"] == "0"
      and votes[0]["sender_pubkey"] == co.pk["cosigner"] and votes[0]["signature"],
      "the co-signer signs only the open request from that address within the limit: feeless, approve")
check(b'"request_id":"' + good.encode() in showcase.signing_bytes(votes[0]) and b'"reason"' in showcase.signing_bytes(votes[0]),
      "the vote's preimage carries request_id, approve and reason, as the node signs it")
notes = " ".join(x["note"] for x in co.st["log"])
check("more than 5,000" in notes and "from another address" in notes, "too big or from another address: not signed, noted")
check(not co.votes, "a request never seen in the inbox is dropped after five minutes")
for i in range(showcase.COSIGN_PER_IP):
    co.route("/showcase/cosign", f"id={i:064x}&from={P}", "2.2.2.2")
check(co.route("/showcase/cosign", f"id={'55' * 32}&from={P}", "2.2.2.2")["ok"] is False, "at most ten a day from one address")

print("all ok" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)

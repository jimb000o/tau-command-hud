"""Unit test of No Memo's vaults (vaults.py), no network: the four rules of the row set on a fake node that judges each
payment by the rule's own reading, a drain the rule allows paid and one it forbids stopped, one payment at a time per
vault, the keeper's checklist (a rule that lets a stranger through caught, a hole for the player passed and put on the
chain, the lease paid and closed, the keeper locked again), level 3 refusing a rule that names the player, the gates
(unknown wallet, one request at a time), a new week dealing new rules, and a testnet restart.

Run: python test_vaults.py
"""
import asyncio
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vaults  # noqa: E402

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


def judge(body: str, amount: int, balance: int, to: str, t: int) -> bool:
    """A tiny reader for the rule shapes of this test (the real judge is the node)."""
    b = vaults.norm(vaults.inner(body))
    if vaults.norm(vaults.BLOCK) not in b:
        return True
    nums = [int(x, 16) for x in re.findall(r"#x([0-9a-f]{6})\}:bv\[24\]", b)]
    if b == vaults.norm(vaults.LOCK):
        return amount == 0
    if b.startswith("(i1[t]:bv[24]>") and "i2" not in b:
        return amount <= nums[0]
    if "i2" in b:
        return amount <= nums[0] and amount <= balance and balance - amount >= nums[1]
    if b.startswith("(i1[t]:bv[24]>=") and "i5" not in b:
        return nums[0] <= amount <= nums[1]
    if "i5" in b:
        lo, hi = [int(x) for x in re.findall(r"\{(\d+)\}:bv\[64\]", b)]
        return lo <= t < hi and amount <= nums[0]
    m = re.search(r"i4\[t\]:bv\[384\]=\{#x([0-9a-f]{96})\}", b)
    if m:   # the player's hole: pays only to that address, and only this amount
        n = re.search(r"i1\[t\]:bv\[24\]=\{#x([0-9a-f]{6})\}", b)
        return to == m.group(1) and (not n or amount == int(n.group(1), 16))
    n = re.search(r"i1\[t\]:bv\[24\]=\{#x([0-9a-f]{6})\}", b)
    if n:
        return amount == int(n.group(1), 16)
    return True


class Node:
    def __init__(self, clock):
        self.clock, self.clauses, self.bal, self.seq, self.sent, self.status = clock, {}, {}, {}, [], {}

    async def ask(self, cmd):
        verb, _, rest = cmd.partition(" ")
        if verb == "getsequence":
            return {"status": "ok", "data": {"sequence_number": self.seq.get(rest, 0), "tip_height": 50}}
        if verb == "getbalance":
            return {"status": "ok", "data": {"balance": self.bal.get(rest, 0)}}
        if verb == "getruleoffers":
            c = self.clauses.get(rest.split()[0])
            return {"status": "ok", "data": {"accepted_clauses": [{"target_stream": "o5", "clause_body": c}] if c else []}}
        if verb == "gettxstatus":
            return {"status": "ok", "data": {"status": self.status.get(rest, "confirmed")}}
        if verb == "sendtx":
            tx = json.loads(rest)
            self.sent.append(tx)
            pk = tx["sender_pubkey"]
            ops = tx["operations"]
            if "0" in ops:
                if pk not in self.seq and not self.bal.get(pk):
                    self.bal[pk] = 100_000   # the faucet, at a new wallet's first transaction
                self.clauses[pk] = vaults.inner(ops["0"])
                self.seq[pk] = self.seq.get(pk, 0) + 1
                return {"status": "ok", "data": {"ok": True, "tx_hash": "r%d" % len(self.sent)}}
            frm, to, amount = ops["1"][0]
            amount = int(amount)
            c = self.clauses.get(pk)
            if c and not judge(c, amount, self.bal.get(pk, 0), to, int(self.clock())):
                return {"status": "error", "error": {"code": "TX_REJECTED", "message":
                        "Transaction rejected: the sender's own policy clause blocked transfer #1. Policy output: 0"}}
            self.bal[pk] = self.bal.get(pk, 0) - amount
            self.bal[to] = self.bal.get(to, 0) + amount
            self.seq[pk] = self.seq.get(pk, 0) + 1
            return {"status": "ok", "data": {"ok": True, "tx_hash": "p%d" % len(self.sent)}}
        return None


class NoMemo:
    def __init__(self, players):
        self.wallets = {p: {} for p in players}
        self.ready = True
        self.pk = {"drop": "d" * 96}
        self.paid = []

    async def drop_ready(self, amount, ask, gov):
        return True

    async def send(self, key, wallet, amount, ask, gov):
        self.paid.append((wallet, amount))
        return "fill%d" % len(self.paid)


class Checker:
    """POST /check stand-in: judges each test with the same tiny reader."""
    def __init__(self, clock):
        self.clock, self.asked = clock, []

    def __call__(self, rule, sender, tests):
        self.asked.append((rule, tests))
        if "constant" in rule:
            return {"accepted": False, "stage": "shape", "reason": "a clause must read an input"}
        return {"accepted": True, "tests": [{"ok": True, "o5": 1 if judge(rule, t["amount"], t["balance"], t["to"], t["time"]) else 0} for t in tests]}


ME, OTHER, STRANGER_PLAYER = "a" * 96, "b" * 96, "c" * 96
KEYS = {n: {"sk": format(i + 11, "064x"), "pk": format(i + 1, "x") * 96} for i, n in enumerate(vaults.KEYS)}
gov = lambda: {}   # noqa: E731


async def run(vs, node, n=60):
    for _ in range(n):
        vs.clock.t += 20
        await vs.step(node.ask, gov)


async def main():
    tmp = tempfile.mkdtemp()
    clock = Clock(1_795_000_000)   # a Thursday in November 2026
    node = Node(clock)
    nm = NoMemo([ME, OTHER])
    ck = Checker(clock)
    vs = vaults.Vaults(nm, keys_path=os.path.join(tmp, "k"), state_path=os.path.join(tmp, "s"), clock=clock, enabled=True,
                       keys=KEYS, checker=ck)
    vs.build = lambda name, seq, tip, fee, rule=None, to=None, amount=0: {   # no BLS here: the fake node reads only these
        "tx_type": "user_tx", "sender_pubkey": vs.pk[name], "sequence_number": seq,
        "operations": {"0": rule} if rule is not None else {"1": [[vs.pk[name], to, str(amount)]]}}
    await run(vs, node, 40)
    snap = vs.snapshot()
    check(all(snap["vaults"][k]["in_force"] for k in vaults.KEYS), "every vault's rule is in force on the node")
    check(snap["vaults"]["keeper"]["rule_text"] == vaults.full(vaults.LOCK), "the keeper rests locked")
    check("words" not in snap["vaults"]["till"] and "dealt" not in snap["vaults"]["till"], "the page gets the rule as Tau only, no words")
    check("i2[t]" in snap["vaults"]["reserve"]["rule_text"] and "i5[t]" in snap["vaults"]["clock"]["rule_text"], "reserve reads i2, clock reads i5")

    # the till: within its cap paid, above it stopped by its own rule
    cap = vs.dealt("till")["cap"]
    check("error" in vs.route("/vaults/drain", f"vault=till&to={STRANGER_PLAYER}&amount=5"), "a wallet that never paid the drop is not served")
    r1 = vs.route("/vaults/drain", f"vault=till&to={ME}&amount={cap}")
    check("id" in r1, "a drain is taken")
    check("error" in vs.route("/vaults/drain", f"vault=till&to={ME}&amount=1"), "one request at a time per wallet")
    await run(vs, node, 6)
    check(vs.req_view(r1["id"])["state"] == "paid" and node.bal.get(ME) == cap, f"{cap} out of the till, in a block")
    clock.t += 30
    r2 = vs.route("/vaults/drain", f"vault=till&to={ME}&amount={cap + 1}")
    refused = []
    vs.on_refused = refused.append
    await run(vs, node, 4)
    v2 = vs.req_view(r2["id"])
    check(v2["state"] == "stopped" and "own rule" in v2["said"], "one above the cap: stopped by the vault's own rule")
    check(len(refused) == 1 and refused[0]["reason"].startswith("o5 = 0"), "the refusal goes to the HUD's feed")

    # one payment in flight per vault: the second waits for the first's block
    node.status = {}
    clock.t += 30
    a = vs.route("/vaults/drain", f"vault=till&to={ME}&amount=1")
    b = vs.route("/vaults/drain", f"vault=till&to={OTHER}&amount=1")
    node.status["p%d" % (len(node.sent) + 1)] = "pending"
    vs.clock.t += 20
    await vs.step(node.ask, gov)
    vs.clock.t += 20
    await vs.step(node.ask, gov)
    check(vs.req_view(a["id"])["state"] == "sent" and vs.req_view(b["id"])["state"] == "waiting", "the next payment waits for the last one's block (i2 stays fresh)")
    node.status.clear()
    await run(vs, node, 8)
    check(vs.req_view(b["id"])["state"] == "paid", "then it goes")

    # the reserve: nothing that leaves less than the floor
    d = vs.dealt("reserve")
    pk = vs.pk["reserve"]
    node.bal[pk] = d["floor"] + 3_000
    clock.t += 30
    r = vs.route("/vaults/drain", f"vault=reserve&to={ME}&amount=3001")
    await run(vs, node, 4)
    check(vs.req_view(r["id"])["state"] == "stopped", "the reserve: one more than above the floor is stopped")
    clock.t += 30
    r = vs.route("/vaults/drain", f"vault=reserve&to={ME}&amount=3000")
    await run(vs, node, 6)
    check(vs.req_view(r["id"])["state"] == "paid" and vs.v("reserve")["drained"], "down to the floor: the reserve is drained, and by whom")

    # the keeper, level 1: a rule that lets a stranger through is caught; one for the player only passes
    clock.t += 30
    lock_all = "always ( (i1[t]:bv[24] > { #x000000 }:bv[24]) ? (o5[t]:bv[24] = { #x000001 }:bv[24]) : (o5[t]:bv[24] = { #x000001 }:bv[24]) )."
    c1 = vs.route("/vaults/crack", "level=1&to=%s&rule=%s" % (ME, lock_all.replace(" ", "%20")))
    await run(vs, node, 2)
    check(vs.req_view(c1["id"])["state"] == "caught", "a rule that lets everything through is caught by the checklist")
    clock.t += 30
    hole = f"(i4[t]:bv[384] = {{ #x{ME} }}:bv[384]) ? (o5[t]:bv[24] = {{ #x000001 }}:bv[24]) : (o5[t]:bv[24] = {{ #x000000 }}:bv[24])"
    from urllib.parse import quote
    c2 = vs.route("/vaults/crack", f"level=1&to={ME}&rule={quote(hole)}")
    check("error" in vs.route("/vaults/crack", f"level=1&to={OTHER}&rule={quote(hole)}"), "one crack at a time")
    await run(vs, node, 30)
    v = vs.req_view(c2["id"])
    check(v["state"] == "open" and v["lease"]["left"] == 500, "a hole for the player only passes; on the chain, the lease is open")
    check(vaults.norm(node.clauses[vs.pk["keeper"]]) == vaults.norm(hole), "the player's rule is the keeper's rule on the node")
    check("error" in vs.route("/vaults/drain", f"vault=keeper&to={OTHER}&amount=10"), "nobody else may drain the keeper")
    check("error" in vs.route("/vaults/drain", f"vault=keeper&to={ME}&amount=501"), "not more than the level's cap")
    clock.t += 30
    k = vs.route("/vaults/drain", f"vault=keeper&to={ME}&amount=500")
    await run(vs, node, 40)
    check(vs.req_view(k["id"])["state"] == "paid", "the player drains the keeper")
    check(vaults.norm(node.clauses[vs.pk["keeper"]]) == vaults.norm(vaults.LOCK) and vs.st["lease"] is None, "the whole cap taken: the keeper locks again")

    # level 2: the player's own wallet is tested at a few amounts; another amount is the hole
    clock.t += 30
    hole2 = (f"(i4[t]:bv[384] = {{ #x{ME} }}:bv[384] && i1[t]:bv[24] = {{ #x000309 }}:bv[24]) ? "
             "(o5[t]:bv[24] = { #x000001 }:bv[24]) : (o5[t]:bv[24] = { #x000000 }:bv[24])")
    c3 = vs.route("/vaults/crack", f"level=2&to={ME}&rule={quote(hole)}")
    await run(vs, node, 2)
    check(vs.req_view(c3["id"])["state"] == "caught" and any(t["to"] == "you" and t["passed"] for t in vs.req_view(c3["id"])["tests"]),
          "level 2: 'pays only me' is caught at the player's own wallet")
    clock.t += 30
    c4 = vs.route("/vaults/crack", f"level=2&to={ME}&rule={quote(hole2)}")
    await run(vs, node, 30)
    check(vs.req_view(c4["id"])["state"] == "open", "level 2: an amount the checklist never tries gets through")
    clock.t += vaults.LEASE + 60
    await run(vs, node, 20)
    check(vs.st["lease"] is None and vs.req_view(c4["id"])["state"] == "over", "the lease runs out unused: over, locked again")

    # level 3: a rule that names the player is refused before any test
    clock.t += 30
    n = len(ck.asked)
    c5 = vs.route("/vaults/crack", f"level=3&to={ME}&rule={quote(hole2)}")
    await run(vs, node, 2)
    check(vs.req_view(c5["id"])["state"] == "caught" and len(ck.asked) == n, "level 3 refuses a rule naming the player, no engine run")
    t3 = vaults.checklist(3, ME, "x", 0, 1)
    check(len(t3) == 8 and all(x["amount"] <= 4000 for x in t3), "level 3: eight dealt tests within the cap")
    check(all(len(x) <= 8 for x in (vaults.checklist(1, ME, "x", 0, 1), vaults.checklist(2, ME, "x", 0, 1))), "every checklist fits the checker's 8 tests")
    clock.t += 30
    c6 = vs.route("/vaults/crack", f"level=3&to={ME}&rule={quote('constant')}")
    await run(vs, node, 2)
    check(vs.req_view(c6["id"])["state"] == "refused" and "refuse" in vs.req_view(c6["id"])["said"], "a rule the node would refuse is said so")

    # a new week: new rules, the row filled by the drop
    clock.t += 7 * 86400
    await run(vs, node, 40)
    snap = vs.snapshot()
    check(snap["vaults"]["till"]["rule_text"] == vaults.full(vaults.body_of("till", vs.dealt("till"))), "a new week deals the till anew")
    check(snap["vaults"]["till"]["in_force"] and vaults.norm(node.clauses[vs.pk["till"]]) == vaults.norm(vaults.inner(snap["vaults"]["till"]["rule_text"])),
          "the new week's rule is in force")
    check(any(w == vs.pk["reserve"] for w, _ in nm.paid), "the drop fills the drained reserve")

    # a testnet restart: rules gone, set again
    node.clauses.clear()
    vs.recheck()
    await run(vs, node, 40)
    check(all(vs.v(k).get("in_force") for k in vaults.KEYS), "after a restart every rule is set again")

    # the clock: numbers within the week
    for w in range(2900, 2910):
        dd = vaults.deal("s", w, "clock", int((w * 7 - 3) * 86400))
        if not ((w * 7 - 3) * 86400 <= dd["from"] < dd["to"] <= (w * 7 + 4) * 86400):
            check(False, "the clock's half hour lies inside its week")
            break
    else:
        check(True, "the clock's half hour lies inside its week")


asyncio.run(main())
print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

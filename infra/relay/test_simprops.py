"""Unit test of visitor proposals for the simulation (GET /sim/propose): fixed kinds and values, Tau tokens only in a rule,
limits per visitor, per address and at once, the timeline in simulated blocks, the ballot registered in the vote store.

Run: python test_simprops.py
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simprops  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


class Votes:   # stands in for simvotes.SimVotes: register() and the items it holds
    def __init__(self):
        self.items = {}

    def register(self, item_id, opens, closes, meta):
        if item_id in self.items:
            return False
        self.items[item_id] = {"yes": 0, "no": 0, "opens": opens, "closes": closes, "meta": meta}
        return True


T = datetime(2026, 10, 28, 20, 0, 4, tzinfo=timezone.utc).timestamp()
V1, V2 = "a" * 32, "b" * 32
q = lambda **k: {"voter": V1, "a": "1", "b": "2", "c": "3", **k}  # noqa: E731
s = simprops.SimProps(Votes())

r = s.propose(q(kind="fee", value="8"), "1.1.1.1", T)
check(r["ok"] and r["id"].startswith("visitor:"), f"a fee proposal is taken {r}")
m = r.get("meta", {})
h = simprops.head_at(T)
check(h == 9000, f"head from the clock: 20:00:04 UTC is block 9000 ({h})")
check(m.get("proposed_at") == 9004 and m.get("close_at") == 9049 and m.get("activate_at") == 9079, "enters 4 blocks ahead, vote 45 blocks, in force 75 after")
it = s.votes.items[r["id"]]
check(it["opens"] == T and it["closes"] == m["activate_ts"] - 30 * 8, "the ballot opens at once and closes 30 blocks before it is in force")
check(m["value"] == 8 and m["by"] == [1, 2, 3] and m["kind"] == "fee", "meta carries kind, value and the word-list identity")

for kv, label in [(dict(kind="fee", value="0"), "fee 0"), (dict(kind="fee", value="1001"), "fee over 1000"), (dict(kind="fee", value="x"), "fee not a number"),
                  (dict(kind="remove", value="zz"), "remove without a key"), (dict(kind="quorum", value="all"), "unknown quorum"),
                  (dict(kind="mode", value="pow"), "unknown mode"), (dict(kind="poem", value="x"), "unknown kind"),
                  (dict(kind="rule", value="always (o9[t]:bv[24] = { #x00000c }:bv[24]). # buy now"), "a comment in a rule"),
                  (dict(kind="rule", value="always (o9[t] = hello)."), "a word in a rule"),
                  (dict(kind="rule", value="always (o5[t] = { 1 }:bv[64])."), "o5 as a network rule"),
                  (dict(kind="rule", value="always (o9[t-1] = { 1 }:bv[24])."), "a past step"),
                  (dict(kind="rule", value="always ((o9[t] = { 1 }:bv[24])."), "unbalanced brackets"),
                  (dict(kind="rule", value="o9[t] = { 1 }:bv[24]"), "no always unit"),
                  (dict(kind="fee", value="8", voter="nothex"), "a bad voter token"),
                  (dict(kind="fee", value="8", a="x"), "no identity")]:
    r = s.propose(q(**kv), "1.1.1.1", T)
    check(not r["ok"] and r["error"] == "bad" and r["why"], f"refused: {label}")

ok = s.propose(q(kind="rule", value="always (o9[t]:bv[24] = { #x00000c }:bv[24] && o7[t]:bv[16] = { 1 }:bv[16])."), "1.1.1.1", T)
check(ok["ok"], "a rule of Tau tokens is taken")
ok = s.propose(q(kind="quorum", value="majority"), "1.1.1.1", T)
check(ok["ok"], "a threshold change is taken")
r = s.propose(q(kind="mode", value="stake", voter=V2), "2.2.2.2", T)
check(not r["ok"] and r["error"] == "busy", f"three open at once, the fourth waits {r.get('error')}")
r = s.propose(q(kind="add"), "1.1.1.1", T + 700)
check(not r["ok"] and r["error"] == "rate", "three a day per visitor")
r = s.propose(q(kind="add", voter=V2), "2.2.2.2", T + 700)
check(r["ok"], "once the first ones are in force, the next visitor may propose")
check(s.route("/sim/other", "", "x") is None, "other paths are not ours")
r = s.route("/sim/propose", "voter=" + V2 + "&kind=remove&value=0123456789ab&a=1&b=1&c=1", "2.2.2.2")
check(isinstance(r, dict) and "ok" in r, "the route reads the query string")

late = datetime(2026, 10, 28, 23, 55, tzinfo=timezone.utc).timestamp()
r = simprops.SimProps(Votes()).propose(q(kind="add"), "1.1.1.1", late)
check(not r["ok"] and r["error"] == "late", "not in the last minutes before the chain starts over")
s2 = simprops.SimProps(Votes())
for i in range(3):
    s2.propose(q(kind="fee", value=str(5 + i)), "9.9.9.9", T + i * 700)
r = s2.propose(q(kind="fee", value="20"), "9.9.9.9", T + 86400)
check(r["ok"], "a new day, new allowances")

print("all passed" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

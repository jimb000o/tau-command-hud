"""Unit test of the visitors' votes for the simulation (simvotes.py), no network.

Run: python test_simvotes.py
"""
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simvotes  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T = [1_793_145_600.0]  # 2026-10-28 00:00 UTC
clock = lambda: T[0]  # noqa: E731
path = os.path.join(tempfile.mkdtemp(), "v.json")
sv = simvotes.SimVotes(path, clock)
opens, closes = simvotes.slot_window(int(T[0] // 86400), 3)
check(opens == T[0] + (150 + 450 * 3) * 8 and closes - opens == 420, "slot 3 opens at 03:20:00 UTC for seven minutes")
tok = lambda i: f"{i:032x}"  # noqa: E731

T[0] = opens - 5
check(sv.vote("slot:3", tok(1), True, 0, 0, 0, "ip1")["error"] == "closed", "no vote before the ballot opens")
T[0] = opens + 10
check(sv.vote("slot:3", tok(1), True, 0, 1, 2, "ip1")["ok"], "a yes vote")
r = sv.vote("slot:3", tok(1), False, 0, 1, 2, "ip1")
check(r["ok"] and r["item"]["yes"] == 0 and r["item"]["no"] == 1 and r["item"]["mine"] == 0, "a visitor may change the vote, counted once")
check(sv.vote("slot:3", tok(2), True, 3, 4, 5, "ip2")["ok"] and sv.vote("slot:3", tok(3), True, 3, 4, 5, "ip3")["ok"], "two more yes")
check(sv.vote("slot:3", tok(4), True, 24, 0, 0, "ip4")["error"] == "bad", "a name outside the lists is refused")
check(sv.vote("slot:3", "xyz", True, 0, 0, 0, "ip4")["error"] == "bad", "a malformed token is refused")
check(sv.vote("slot:99", tok(4), True, 0, 0, 0, "ip4")["error"] == "unknown", "an unknown item is refused")
for i in range(10, 13):
    sv.vote("slot:3", tok(i), False, 0, 0, 0, "ipX")
check(sv.vote("slot:3", tok(13), False, 0, 0, 0, "ipX")["error"] == "limit", "one address votes with at most three tokens per item")
snap = sv.snapshot(tok(2))
it = snap["items"]["slot:3"]
check(it["yes"] == 2 and it["no"] == 4 and it["outcome"] is None and it["open"] and it["mine"] == 1, f"tally while open {it['yes']}/{it['no']}")
check(all(len(v) == 4 for v in it["voters"]) and tok(2) not in json.dumps(snap), "voters show name and colour, never the token")
check(snap["day"] == "2026-10-28" and "slot:4" not in snap["items"] or snap["items"]["slot:4"]["opens"] <= T[0] + 3600, "day key and the items of the next hour")

T[0] = closes + 1
check(sv.snapshot()["items"]["slot:3"]["outcome"] == "no", "more no than yes: the outcome is no")
check(sv.vote("slot:3", tok(20), True, 0, 0, 0, "ip9")["error"] == "closed", "no vote after the close")
o4, c4 = simvotes.slot_window(int(T[0] // 86400), 4)
T[0] = c4 + 1
check(sv.snapshot()["items"]["slot:4"]["outcome"] == "none", "no votes: outcome none (the change comes as planned)")

check(sv.register("visitor:abc", T[0], T[0] + 600, {"title": "x"}) and not sv.register("visitor:abc", T[0], T[0] + 600), "register an item once")
check(not sv.register("slot:5", T[0], T[0] + 60), "slot ids cannot be registered")
check(sv.vote("visitor:abc", tok(30), True, 1, 1, 1, "ip30")["ok"], "a vote on a registered item")
check(sv.tally("visitor:abc")["meta"] == {"title": "x"}, "tally carries the meta")

sv2 = simvotes.SimVotes(path, clock)
check(sv2.tally("slot:3")["no"] == 4 and sv2.tally("visitor:abc")["yes"] == 1, "votes survive a relay restart")
T[0] += 86400
check(sv2.snapshot()["items"].get("slot:3", {}).get("yes", 0) == 0 and sv2.tally("visitor:abc") is None, "a new day starts with no votes")

st, body = sv2.route("/sim/vote", f"item=slot%3A3&voter={tok(40)}&yes=1&a=0&b=0&c=0", "ip40")
check(st == 409 and body["error"] == "closed", f"route answers a closed ballot with 409 ({st})")
check(sv2.route("/sim/votes", "", "ip") [0] == 200 and sv2.route("/status", "", "ip") is None, "route handles only its paths")
check(simvotes.name_of(0, 0) == "Quiet Otter", "name_of")

# the word lists and colours are the same, in the same order, as in sim.js
js = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "sim.js"), encoding="utf-8").read()
arr = lambda name: re.findall(r'"([^"]+)"', re.search(r"const " + name + r" = \[(.*?)\];", js, re.S).group(1))  # noqa: E731
check(arr("ID_A") == simvotes.NAME_A and arr("ID_B") == simvotes.NAME_B and arr("ID_COLOURS") == simvotes.COLOURS_HEX, "lists equal sim.js")
check(len(arr("ID_A_ZH")) == len(simvotes.NAME_A) and len(arr("ID_B_ZH")) == len(simvotes.NAME_B), "Chinese lists as long")
check(re.search(r"BALLOT_SECONDS = (\d+)", js).group(1) == str(simvotes.BALLOT_SECONDS) and "SLOT_AT = 150, SLOT_LEN = 450" in js, "ballot window equals sim.js")

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

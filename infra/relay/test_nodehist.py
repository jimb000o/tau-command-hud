"""Unit test of the node history (nodehist.py), no network.

Run: python test_nodehist.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nodehist  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


D = 1_793_145_600   # 2026-10-28 00:00 UTC
H = 3600
path = os.path.join(tempfile.mkdtemp(), "nodehist.json")
n = nodehist.NodeHistory(path)
steady = lambda pid, r: True
book = {"since": D, "peers": {
    "boot": {"first_seen": D, "last_direct": D + 30 * H, "last_heard": None},
    "a": {"first_seen": D + 2 * H, "last_direct": D + 5 * H, "last_heard": None},      # gone before recording began
    "c": {"first_seen": D + 26 * H, "last_direct": D + 26 * H + 900, "last_heard": None},
}}
# recording begins on the second day at 01:10
n.note(["boot", "c"], {"c"}, D + 25 * H + 600)
n.note(["boot"], set(), D + 25 * H + 1200)
n.note(["boot", "c"], {"c"}, D + 26 * H + 60)
out = n.history(book, {"c"}, steady, D + 26 * H + 120)
h1, h2 = out["hours"]["2026-10-28"], out["hours"]["2026-10-29"]
check(h1[0] == 2 and h1[3] == 3 and h1[6] == 2, "estimated hours: a peer counts between its first and last sighting, our node too")
check(h2[1] == 3 and h2[2] == 3 and out["recorded"] == D + 25 * H, "recorded hours count the peers seen in that hour, plus our node")
check(out["days"]["2026-10-28"] == [3, 3, 0, 1], "an estimated day: most at once, different nodes, marked estimated")
check(out["days"]["2026-10-29"][0] == 3 and out["days"]["2026-10-29"][3] == 1, "the day recording began is partly estimated")
check("boot" not in json.dumps(out), "no peer IDs in the answer")
n2 = nodehist.NodeHistory(path)
check(n2.st["recorded"] == D + 25 * H and n2.st["hours"]["%d" % (D + 25 * H)] == 3, "kept across a restart")
n2.note(["boot"], set(), D + 2 * 86400 + 60)
check(n2.st["days"]["2026-10-29"] == [3, 1], "a finished day keeps only its counts")
out = n2.history(book, set(), steady, D + 2 * 86400 + 120)
check(out["days"]["2026-10-30"][3] == 0 and out["days"]["2026-10-30"][0] == 2, "a fully recorded day is not marked estimated")
print("\n" + ("all ok" if not failed else f"{failed} failed"))
sys.exit(1 if failed else 0)

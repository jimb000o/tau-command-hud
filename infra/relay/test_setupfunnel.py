"""Unit test of the node setup funnel (setupfunnel.py), no network.

Run: python test_setupfunnel.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import setupfunnel  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


D = 1_793_145_600   # 2026-10-28
path = os.path.join(tempfile.mkdtemp(), "setup.json")
f = setupfunnel.SetupFunnel(path)
A, B = "0123456789abcdef", "fedcba9876543210"
check(f.note({"s": "copied"}, "1.2.3.4", D), "a copied command counts")
for s, t in (("start", 0), ("packages", 60), ("docker", 120), ("kit", 150), ("build", 160)):
    f.note({"i": A, "s": s, "t": str(t)}, "1.2.3.4", D + t)
f.note({"i": A, "s": "fail", "at": "build"}, "1.2.3.4", D + 3000)
f.note({"i": B, "s": "start"}, "5.6.7.8", D)
f.note({"i": B, "s": "start"}, "5.6.7.8", D + 10)
check(not f.note({"i": "nope", "s": "start"}, "5.6.7.8", D), "an install id must be 16 hex")
check(not f.note({"i": B, "s": "rm -rf"}, "5.6.7.8", D), "only known steps")
st = f.stats()
check(st["installs"]["reached"]["start"] == 2 and st["installs"]["reached"]["build"] == 1 and st["installs"]["reached"]["up"] == 0,
      "steps reached per install; a repeated step counts once")
check(st["installs"]["failed"]["build"] == 1 and st["installs"]["minutes"]["docker"] == 2, "where it stopped, minutes to each step")
check(st["days"]["2026-10-28"]["copied"] == 1 and st["days"]["2026-10-28"]["start"] == 2, "counts per day")
check("1.2.3.4" not in open(path).read(), "no address is written")
f.note({"i": A, "s": "up", "t": "6000"}, "1.2.3.4", D + 6000)
check(setupfunnel.SetupFunnel(path).stats()["installs"]["failed"]["build"] == 0, "a re-run that gets further is no longer stuck; kept across a restart")
g = setupfunnel.SetupFunnel(os.path.join(tempfile.mkdtemp(), "s.json"))
check(sum(g.note({"s": "copied"}, "9.9.9.9", D) for _ in range(30)) == 20, "an address cannot flood the counts")
print("\n" + ("all ok" if not failed else f"{failed} failed"))
sys.exit(1 if failed else 0)

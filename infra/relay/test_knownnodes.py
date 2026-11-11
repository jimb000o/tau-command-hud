"""Unit test of the named nodes (knownnodes.py), no network.

Run: python test_knownnodes.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knownnodes as kn  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


AOC = "12D3KooWEafLrs7GSJjuBbrRtGXeCzMZcJZowHvpCcFXLyetuzTc"
IP = "2.29.161.201"
OTHER = "12D3KooWDpWEYxBy8y84AssrPSLaq9DxC7Lncmn5wERJnAWZFnYC"
check(kn.KNOWN[AOC]["name"] == "Age of Chains" and kn.KNOWN[AOC]["report_name"] == "Age-of-Chains", "Age of Chains is listed")

# reports: the name and the peer ID only from the node's own address
check(kn.check_report("Age-of-Chains", AOC, IP) == (AOC, None), "own address, own name and peer: known")
check(kn.check_report("Age-of-Chains", None, IP) == (AOC, None), "own address, name only (no peer ID from the node): known")
check(kn.check_report("aoc-box", AOC, IP) == (AOC, None), "own address, own peer under another name: still known")
check(kn.check_report("age_of.chains", None, "198.51.100.1")[1] == "That name is reserved.", "the name from elsewhere: refused")
check(kn.check_report("someone", AOC, "198.51.100.1")[1] == "That name is reserved.", "the peer ID from elsewhere: refused")
check(kn.check_report("someone", OTHER, "198.51.100.1") == (None, None), "anyone else: not known, not refused")

NOW, ONLINE, LAG = 10_000_000.0, 1800, 2
st = lambda **kw: kn.state(AOC, kw.get("peer"), kw.get("report"), kw.get("board"), kw.get("probe"), kw.get("agrees"),
                           kw.get("ours", 7496), NOW, online_seconds=ONLINE, lag=LAG)

s = st()
check(s["reach"] == "unknown" and s["sync"]["state"] == "unknown" and s["first_seen"] is None, "no data: unknown, unknown")

s = st(probe={"ok": True, "at": NOW - 60, "last_ok": NOW - 60, "error": None})
check(s["reach"] == "online" and s["port"]["open"] is True and s["sync"]["state"] == "unknown",
      "port open: reachable, but nothing said about sync")
s = st(probe={"ok": False, "at": NOW - 60, "last_ok": None, "error": "timeout"})
check(s["reach"] == "offline" and s["port"]["open"] is False, "port closed: offline")
s = st(probe={"ok": True, "at": NOW - 3 * kn.PROBE_FRESH, "last_ok": NOW - 3 * kn.PROBE_FRESH, "error": None})
check(s["port"]["open"] is None and s["reach"] == "unknown", "an old probe says nothing about now")

peer = {"first_seen": NOW - 3600, "last_direct": NOW - 120, "last_heard": None, "head": 2712, "connected": True}
s = st(peer=peer)
check(s["reach"] == "online" and s["p2p"]["online"] and s["sync"] == {"state": "catching_up", "height": 2712, "ours": 7496,
      "behind": 4784, "source": "p2p"}, f"peer contact: online, catching up by height {s['sync']}")
s = st(peer=dict(peer, head=7495))
check(s["sync"]["state"] == "at_height", "at our height by the peer book: never called synced without a hash")
s = st(peer=dict(peer, last_direct=None, last_heard=NOW - 60, connected=False))
check(s["reach"] == "offline" and s["sync"]["state"] == "unknown", "only heard of from another peer: not reached, no sync data")

rep = {"height": 7495, "head": "ab" * 32}
board = {"first_seen": NOW - 7200, "last_seen": NOW - 30}
s = st(report=rep, board=board, agrees="same")
check(s["reach"] == "online" and s["sync"]["state"] == "synced" and s["sync"]["source"] == "report", "report, same hash, at our head: synced")
s = st(report=dict(rep, height=2712), board=board, agrees="same")
check(s["sync"]["state"] == "catching_up" and s["sync"]["behind"] == 4784, "report, same chain, far behind: catching up")
s = st(report=rep, board=board, agrees="different")
check(s["sync"]["state"] == "other_chain", "report, other hash: other chain")
s = st(report=dict(rep, height=7600), board=board, agrees="ahead")
check(s["sync"]["state"] == "ahead", "report above our head: ahead")
s = st(report=None, board=board)
check(s["reach"] == "offline" and s["report"]["live"] is False and s["sync"]["state"] == "unknown", "silent heartbeat: offline, sync unknown")
check(st(peer=peer, board=board)["first_seen"] == round(NOW - 7200), "first seen: the earliest evidence")

print("all ok" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)

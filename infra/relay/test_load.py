"""Checks for load.py (GET /load, the testnet load page). Run: python3 test_load.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import load  # noqa: E402

fails = 0


def check(cond, what):
    global fails
    print(("ok   " if cond else "FAIL ") + what)
    fails += 0 if cond else 1


t = [1_800_000_000.0]
clock = lambda: t[0]  # noqa: E731
path = os.path.join(tempfile.mkdtemp(), "load.json")
L = load.Load(path=path, clock=clock)
s = L.snapshot([], 0)
check(len(s["sealed"]) == load.WINDOW and s["state"] == "calm", "an empty chain is calm, six hours of minutes")

t[0] += 10
L.pool(4)
L.pool(2)
L.sent("sent")
L.sent("bot")
L.sent("bot")
L.sealed_after(12)
L.sealed_after(30)
now = t[0]
blocks = [(now - 3700, 1), (now - 70, 3), (now - 40, 5), (now - 5, 2)]
t[0] += 6
s = L.snapshot(blocks, 2)
check(s["pool"][-1] == 4, "the most transactions seen waiting in the minute")
check(s["sent"][-1] == 1 and s["bot"][-1] == 2, "visitors' and the island bot's sends counted apart")
check(s["wait_avg"][-1] == 21 and s["wait_max"][-1] == 30, "time from the mempool into a block, average and longest")
check(s["now"]["sealed_hour"] == 10 and s["now"]["blocks_hour"] == 3, "the last hour leaves out the block from before it")
check(s["records"]["per_block"] == 5 and s["records"]["pool"] == 4, "records since tracking began")
check(s["now"]["last_block_age"] == 11, "seconds since the last block")

t[0] += 6
for _ in range(7):
    L.sent("refused")
L._cache = (0, None)
check(L.snapshot(blocks, 2)["state"] == "strained", "refused sends make it strained")

t[0] += 700
L._cache = (0, None)
check(L.snapshot(blocks, 9)["state"] == "stalled", "transactions waiting and no block for ten minutes: stalled")

L.saved_at = 0
L.pool(1)
M = load.Load(path=path, clock=clock)
check(M.top["pool"] == 4 and any(r["sent"] == 1 for r in M.mins.values()), "minutes and records survive a restart")

t[0] += 60 * (load.WINDOW + 5)
L.pool(1)
check(min(L.mins) > load._minute(t[0]) - load.WINDOW, "minutes older than the window are dropped")

print("all ok" if not fails else f"{fails} failed")
sys.exit(1 if fails else 0)

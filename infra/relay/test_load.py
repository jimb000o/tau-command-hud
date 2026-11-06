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

# a testnet whose blocks come every 80 s: one ordinary block of waiting is not strain (MS Dry Run, 4 November 2026)
S = load.Load(path=os.path.join(tempfile.mkdtemp(), "l2.json"), clock=clock)
end = t[0]
slow_blocks = [(end - 80 * k, 1) for k in range(45, 0, -1)]
S.sealed_after(85)
st = S.snapshot(slow_blocks, 2)
check(st["thresholds"]["usual_gap"] == 80 and st["thresholds"]["wait"] == 240, "strain is measured against the usual block gap (three times 80 s)")
check(st["state"] == "calm", "a wait of one 80-second block is calm, not strained")
S._cache = (0, None)
S.sealed_after(300)
check(S.snapshot(slow_blocks, 2)["state"] == "strained", "a wait of nearly four blocks is strain")
F = load.Load(path=os.path.join(tempfile.mkdtemp(), "l3.json"), clock=clock)
F.sealed_after(61)
check(F.snapshot([(end - 10 * k, 1) for k in range(60, 0, -1)], 2)["state"] == "strained", "on fast blocks the 60 s floor still holds")

L.saved_at = 0
L.pool(1)
M = load.Load(path=path, clock=clock)
check(M.top["pool"] == 4 and any(r["sent"] == 1 for r in M.mins.values()), "minutes and records survive a restart")

t[0] += 60 * (load.WINDOW + 5)
L.pool(1)
check(min(L.mins) > load._minute(t[0]) - load.WINDOW, "minutes older than the window are dropped")

# a version 1 file (ghosts counted as waiting) loses its waiting numbers, keeps its sends
import json as _json  # noqa: E402
old = os.path.join(tempfile.mkdtemp(), "old.json")
with open(old, "w") as f:
    _json.dump({"mins": {"100": {"pool": 30, "sent": 2, "bot": 0, "refused": 0, "wait": [3600, 1, 3600]}}, "top": {"pool": 49, "wait": 3660, "per_min": 17}}, f)
O = load.Load(path=old, clock=clock)
check(O.top["wait"] == 0 and O.top["pool"] == 0 and O.top["per_min"] == 17 and O.mins[100]["sent"] == 2 and O.mins[100]["wait"] == [0, 0, 0],
      "numbers from the first version, which counted ghosts, are dropped")

# the relay: a ghost (sealed, still listed) is not waiting, and its wait ends at the block, not when the list drops it
TMP = os.path.join(tempfile.mkdtemp(), "r")
os.environ.update(UPTIME_PATH=TMP + ".uptime", EVENTS_PATH=TMP + ".events", CHAIN_PATH=TMP + ".chain", LOAD_PATH=TMP + ".load",
                  ISLAND_KEYS_PATH=TMP + ".keys", VISITS_KEY="x", CHAT_KEY="x")
import time as _time  # noqa: E402
import relay  # noqa: E402
r = relay.Relay()
real = _time.time
base = real()
relay.time.time = lambda: base
r.track_mempool({"transactions": [{"tx_hash": "aa"}, {"tx_hash": "bb"}]})
check(r.mempool_waiting == 2, "two listed, none sealed: two waiting")
r.blocks["h1"] = {"block_hash": "h1", "header": {"block_number": 1, "timestamp": int(base) + 9}, "tx_ids": ["aa"]}
relay.time.time = lambda: base + 9
r.track_mempool({"transactions": [{"tx_hash": "aa"}, {"tx_hash": "bb"}]})
check(r.mempool_waiting == 1, "a sealed transaction still listed (a ghost) is not waiting")
relay.time.time = lambda: base + 1800
r.track_mempool({"transactions": [{"tx_hash": "bb"}]})
w = [v for v in r.load.mins.values() if v["wait"][1]]
check(len(w) == 1 and w[0]["wait"][1] == 1 and w[0]["wait"][2] == 9, "its wait is 9 s, until the block, not 30 min until the list dropped it")
relay.time.time = real

print("all ok" if not fails else f"{fails} failed")
sys.exit(1 if fails else 0)

"""Unit test of the availability history behind GET /uptime (no network).

Run: python test_uptime.py   (needs websockets==15.0.1)
"""
import json
import os
import sys
import tempfile

UPTIME = os.path.join(tempfile.mkdtemp(), "uptime.json")
os.environ.update(UPTIME_PATH=UPTIME, EVENTS_PATH=UPTIME + ".events", CHAIN_PATH=UPTIME + ".chain",
                  UPTIME_SAMPLE_SECONDS="60", STATS_CACHE_SECONDS="0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import relay  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


def gov(canon, tip):
    relay_.cache["getgovernance"] = json.dumps({"status": "ok", "data": {"head_number": canon, "network_tip": {"number": tip}}})


T0 = 1_800_000_000 - 1_800_000_000 % 3600
relay_ = relay.Relay()
relay_.upstream.connected.set()
for i in range(10):                      # 10 healthy minutes
    relay_.updated["getblocks"] = T0 + i * 60
    gov(100 + i, 100 + i)
    relay_.sample_uptime(T0 + i * 60)
for i in range(10, 15):                  # 5 minutes 6 blocks behind
    relay_.updated["getblocks"] = T0 + i * 60
    gov(100, 106)
    relay_.sample_uptime(T0 + i * 60)
relay_.upstream.connected.clear()        # node gone for 3 minutes
for i in range(15, 18):
    relay_.sample_uptime(T0 + i * 60)
relay_.upstream.connected.set()
for i in range(18, 20):
    relay_.updated["getblocks"] = T0 + i * 60
    gov(110, 110)
    relay_.sample_uptime(T0 + i * 60)
h = relay_.uptime["hours"][str(T0)]
check(h[:3] == [20, 17, 12] and h[5] == 20, f"hour bucket samples/node_ok/synced/score samples {h}")
inc = relay_.uptime["incidents"]
kinds = [(i["kind"], i["start"] - T0, i["end"] - T0) for i in inc]
check(kinds == [("sync", 600, 900), ("node", 900, 1080)], f"incidents {kinds}")
check(inc[0].get("max_lag") == 6, f"sync gap keeps its worst lag {inc[0]}")

# relay away for 10 minutes while the node was out: the open outage closes at the
# last beat, the time away becomes a relay outage
relay_.upstream.connected.clear()
relay_.sample_uptime(T0 + 20 * 60)
check(relay_.uptime["incidents"][-1]["end"] is None, "node outage open")
relay.time.time = lambda: T0 + 30 * 60
again = relay.Relay()
last = again.uptime["incidents"][-2:]
check(last[0]["kind"] == "node" and last[0]["end"] == T0 + 1200, f"open outage closed at the last beat {last[0]}")
check(last[1] == {"kind": "relay", "start": T0 + 1200, "end": T0 + 1800}, f"relay downtime recorded {last[1]}")
data = json.loads(again.uptime_json())
check(data["hours"][0][:4] == [T0, 21, 17, 12] and data["fields"][0] == "hour", f"/uptime hours {data['hours']}")
check("status" in data and data["sync_lag_blocks"] == relay.SYNC_LAG, "/uptime carries the current status")

# stalls: blocks 1..5 a minute apart, then 20 minutes of nothing
again.blocks["0" * 64] = {"block_hash": "0" * 64, "header": {"block_number": 0, "timestamp": 0}}
for n in range(1, 7):
    ts = T0 + n * 60 + (1200 if n == 6 else 0)
    again.blocks[f"{n:064x}"] = {"block_hash": f"{n:064x}", "header": {"block_number": n, "timestamp": ts}}
st = again.chain_stalls(0)
check(st == [{"after": 5, "start": T0 + 300, "end": T0 + 1560}], f"chain stall, genesis ignored {st}")

# a month later the old hours are gone
relay.time.time = lambda: T0 + 40 * 86400
again.upstream.connected.set()
again.updated["getblocks"] = T0 + 40 * 86400
again.sample_uptime(T0 + 40 * 86400)
check(str(T0) not in again.uptime["hours"] and len(again.uptime["hours"]) == 1, "hours older than 31 days trimmed")
check(all(i["end"] >= T0 + 9 * 86400 for i in again.uptime["incidents"] if i["end"]), "old incidents trimmed")
sys.exit(1 if failed else 0)

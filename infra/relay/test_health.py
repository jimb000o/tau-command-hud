"""Unit test of the testnet health score behind GET /health-score (no network).

Run: python test_health.py   (needs websockets==15.0.1)
"""
import json
import os
import sys
import tempfile

TMP = os.path.join(tempfile.mkdtemp(), "h")
os.environ.update(UPTIME_PATH=TMP + ".uptime", EVENTS_PATH=TMP + ".events", CHAIN_PATH=TMP + ".chain",
                  UPTIME_SAMPLE_SECONDS="60", STATS_CACHE_SECONDS="0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import relay  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T0 = 1_800_000_000 - 1_800_000_000 % 3600
r = relay.Relay()
r.upstream.connected.set()
for n in range(0, 121):                  # two hours of blocks, one a minute
    r.blocks[f"{n:064x}"] = {"block_hash": f"{n:064x}", "header": {"block_number": n, "timestamp": T0 + n * 60 if n else 0}}
now = T0 + 120 * 60 + 30
r.updated["getblocks"] = now
r.cache["getgovernance"] = json.dumps({"status": "ok", "data": {"head_number": 120, "network_tip": {"number": 120}}})
h = r.health(now)
f = {x["key"]: x for x in h["factors"]}
check(sum(x["weight"] for x in h["factors"]) == 100, "weights add up to 100")
check(h["expected_block_seconds"] == 60, f"expected block time from the chain {h['expected_block_seconds']}")
check(h["score"] == 100 and h["state"] == "healthy", f"healthy chain scores 100 {h['score']} {h['state']}")

# 12 minutes without a block, an old waiting transaction: degraded, not down
r.mempool_seen["aa"] = {"seen": now - 40 * 60}
r.updated["getblocks"] = now + 12 * 60
h = r.health(now + 12 * 60)
f = {x["key"]: x for x in h["factors"]}
check(f["last_block"]["points"] < 20 and f["mempool"]["points"] < 5, f"slow block and old tx cost points {h['score']}")
check(h["state"] in ("healthy", "degraded"), f"short slowdown is not down {h['state']}")

# 40 minutes without a block: the testnet stalls
r.updated["getblocks"] = now + 40 * 60
h = r.health(now + 40 * 60)
check(h["state"] == "down" and h["score"] < 80, f"no block for 40 minutes is down {h['score']} {h['state']}")

# node gone: down whatever the rest says
r.updated["getblocks"] = now
r.upstream.connected.clear()
h = r.health(now)
check(h["state"] == "down" and h["factors"][0]["points"] == 0, f"node unreachable is down {h['score']}")
r.upstream.connected.set()

# 10 blocks behind the network tip
r.cache["getgovernance"] = json.dumps({"status": "ok", "data": {"head_number": 110, "network_tip": {"number": 120}}})
f = {x["key"]: x for x in r.health(now)["factors"]}
check(0 < f["sync"]["points"] < 15 and f["sync"]["value"] == "10 blocks behind", f"lag costs part of sync {f['sync']}")
r.cache["getgovernance"] = json.dumps({"status": "ok", "data": {"head_number": 120, "network_tip": {"number": 120}}})

# a restart in the last day costs stability points
r.state["restarts"].append({"detected_at": now - 3600, "old": {"tip": 50}})
f = {x["key"]: x for x in r.health(now)["factors"]}
check(f["stability"]["points"] == 5 and f["stability"]["value"]["restarts"] == 1, f"restart costs 10 {f['stability']}")

# samples record the score per hour; /health-score serves average and lowest, /status the short form
r.mempool_seen.clear()
r.sample_uptime(now)
r.upstream.connected.clear()
r.sample_uptime(now + 60)
data = json.loads(r.health_json())
row = data["hours"][-1]
check(row[0] == now - now % 3600 and row[2] < row[1], f"/health-score hour row {row}")
check(data["state"] == "down" and data["thresholds"] == {"healthy": 80, "degraded": 50}, "/health-score current state")
st = r.status()["health"]
check(set(st) == {"score", "state", "label"} and st["state"] == "down", f"/status carries the score {st}")
sys.exit(1 if failed else 0)

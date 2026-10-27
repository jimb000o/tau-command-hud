"""Unit test of the public API behind GET /api/v1/summary and the badges (no network).

Run: python test_api.py   (needs websockets==15.0.1)
"""
import json
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ.update(UPTIME_PATH=os.path.join(TMP, "u.json"), EVENTS_PATH=os.path.join(TMP, "e.json"),
                  CHAIN_PATH=os.path.join(TMP, "c.jsonl"), BOARD_PATH=os.path.join(TMP, "b.json"), API_CACHE_SECONDS="0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import relay  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


r = relay.Relay()
s = r.summary()
check(s["status"] == "offline" and s["height"] is None and s["proposals"] is None, f"empty relay reads offline {s['status']}")
check("offline" in r.api_badge("height") and "#2a2a2e" in r.api_badge("status"), "badges grey while offline")

r.upstream.connected.set()
r.updated["getblocks"] = 1
for n in range(1, 21):
    r.blocks[f"h{n}"] = {"header": {"block_number": n, "timestamp": 1_800_000_000 + 12 * n}}
r.cache["getgovernance"] = json.dumps({"status": "ok", "data": {
    "head_number": 20, "network_tip": {"number": 21}, "active_validators": ["aa"],
    "pending_updates": [{}], "scheduled_updates": [],
    "archival_update_details": [{"lifecycle": "activated"}, {"lifecycle": "activated"}, {"lifecycle": "expired"}],
    "consensus_rules": "o9[t] = { #x3 }:bv[64]"}})
r.cache["getmempool"] = json.dumps({"status": "ok", "data": {"transactions": [{"tx_hash": "x"}]}})
s = r.summary()
check(s["status"] == "synced" and s["height"] == 20 and s["tip_height"] == 21, "synced within SYNC_LAG")
check(s["pace_seconds"] == 12.0, f"pace from the last 10 intervals {s['pace_seconds']}")
check(s["proposals"] == {"waiting": 1, "agreed": 0, "in_force": 2, "dropped": 1, "total": 4}, f"proposal counts {s['proposals']}")
check(s["spec_revision"] == 3 and s["base_fee"] == 3 and s["validators"] == 1 and s["mempool"] == 1, "revision, fee, validators, mempool")
check(json.loads(json.dumps(s)) == s, "summary is plain JSON")
check(">20<" in r.api_badge("height") and "#39ff8a" in r.api_badge("height"), "height badge green when synced")
check("1 coming up · 2 in force" in r.api_badge("proposals"), "proposals badge")
check("1 active" in r.api_badge("validators"), "validators badge")
check("not rated yet" in r.api_badge("health"), "health badge before a score exists")

r.cache["getgovernance"] = r.cache["getgovernance"].replace('"number": 21', '"number": 40')
check(r.summary()["status"] == "catching_up", "far behind the tip reads catching_up")

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

"""Unit test of the node-log reader for the weekly IDNI report (no network, no Docker): the tau-node container's log
is found among others, only sync and peering warnings of the week are kept, other nodes' addresses are masked (IDNI's
bootnode and ours stay), one kind of failure is one group with its traceback, the state file round-trips, and the
report's section shrinks until the issue link fits.

Run: python test_node_logs.py
"""
import json
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ.update(PUBLIC_DIR=TMP, BLOG_STATE=os.path.join(TMP, "blog.json"), NODE_LOG_STATE=os.path.join(TMP, "node-log.json"),
                  NEWS_AI_KEY="", CHAT_AI_KEY="", TELEGRAM_BOT_TOKEN="")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import node_logs as nl  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


ROOT = os.path.join(TMP, "containers")
PEER_A = "12D3KooWDpWEYxBy8y84AssrPSLaq9DxC7Lncmn5wERJnAWZFnYC"
PEER_B = "12D3KooWQ1x2y3z4A5b6C7d8E9f1G2h3J4k5L6m7N8p9Q1r2S3t4"


def container(cid, service, lines):
    d = os.path.join(ROOT, cid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "config.v2.json"), "w") as f:
        json.dump({"Name": f"/infra-{service}-1", "Config": {"Labels": {"com.docker.compose.service": service}}}, f)
    with open(os.path.join(d, cid + "-json.log"), "w") as f:
        for l in lines:
            f.write(json.dumps({"log": l + "\n", "stream": "stderr", "time": "2026-11-10T12:00:00Z"}) + "\n")


container("aaa", "relay", ["2026-11-10 10:00:00 WARNING [network.host] Failed to sync headers from " + PEER_A])
container("bbb", "tau-node", [
    "2026-11-01 09:00:00 WARNING [network.host] Failed to sync headers from " + PEER_A,          # before the week
    "2026-11-10 10:00:00 WARNING [network.host] Failed to sync headers from " + PEER_A,
    "Traceback (most recent call last):",
    '  File "/app/network/host.py", line 1810, in _sync',
    "TimeoutError: dial 5.6.7.8:4001 timed out",
    "2026-11-10 10:05:00 INFO [network.host] connected to 34.251.82.246",
    "2026-11-10 10:06:00 WARNING [network.host] Failed to sync headers from " + PEER_B,
    "2026-11-10 10:07:00 WARNING [network.host] Handshake failed with " + PEER_B + " after 3 attempts",
    "2026-11-10 10:08:00 WARNING [commands.sendtx] fee limit too low for tx 42",                # not sync or peers
    "2026-11-10 10:08:30 ERROR [tau.server] WS connection task crashed; dropping client",       # a WebSocket client, not a peer
    "  + Exception Group Traceback (most recent call last):",
    "2026-11-10 10:09:00 ERROR [network.host] libp2p could not dial /ip4/9.9.9.9/tcp/4001 and /ip4/34.251.82.246/tcp/4001",
])

T0, T1 = 1793574000, 1793574000 + 9 * 86400     # Monday 2 November 2026 00:00 German time, nine days
files = nl.find_logs(ROOT)
check(len(files) == 1 and "/bbb/" in files[0], "the tau-node container's log is found, not the relay's")
s = nl.summary(T0, T1, ROOT)
check(s is not None and s["lines"] == 4, f"four sync or peering lines in the week (got {s and s['lines']})")
gs = s["groups"]
top = gs[0]
check(top["count"] == 2 and "Failed to sync headers" in top["key"], "two peers failing the same way are one group of 2")
check(top["example"]["trace"] and "TimeoutError" in top["example"]["trace"][-1], "the group's example carries its traceback")
check(all("INFO" not in x for x in top["example"]["trace"]), "the INFO line after the traceback ends it")
text = "\n".join(nl.section(s))
check("5.6.7.8" not in text and "9.9.9.9" not in text and "x.x.x.x" in text, "other nodes' addresses are masked")
check("34.251.82.246" in text, "IDNI's bootnode address stays")
check(PEER_A not in text and PEER_A[:12] + "…" in text, "peer ids are shortened")
check("fee limit" not in text, "a line about something else is left out")
check("WS connection" not in text, "a WebSocket client hanging up is not a peering failure")
check(nl.section(None) == [], "no node log readable: no section at all")
check(any("No warning or error" in x for x in nl.section({"lines": 0, "groups": []})), "a quiet week says so")
short = "\n".join(nl.section(s, 3))
check("```" not in short and len(short) < len(text), "the shortest section has no tracebacks")

# the nodelog service's file, read by the report
n = nl.keep(now=T0 + 9 * 86400, root=ROOT, path=os.environ["NODE_LOG_STATE"])
check(n == 4, f"kept the four watched lines of the last nine days (got {n})")
raw = json.load(open(os.environ["NODE_LOG_STATE"]))
check("5.6.7.8" not in json.dumps(raw) and PEER_B not in json.dumps(raw), "the state file holds masked lines only")
import time  # noqa: E402
real = time.time
time.time = lambda: T0 + 9 * 86400
try:
    got = nl.from_state(T0, T1)
finally:
    time.time = real
check(got is not None and got["lines"] == 4 and got["groups"][0]["count"] == 2, "the report's week from the file, grouped the same way")
time.time = lambda: T0 + 30 * 86400
try:
    check(nl.from_state(T0, T1) is None, "a file older than three days is not used")
finally:
    time.time = real
check(nl.from_state(T0, T1, os.path.join(TMP, "none.json")) is None, "no file: no section")

print("\nall ok" if not failed else f"\n{failed} failed")
sys.exit(1 if failed else 0)

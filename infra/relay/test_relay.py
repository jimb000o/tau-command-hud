"""End-to-end test of the relay against a mock Tau node.

The mock speaks the node's WebSocket protocol, mints a block every second and
enforces the node's real per-connection limits (heavy reads: burst 2, 0.5/s),
so the test also proves the relay's polling schedule never trips them.

Run: python test_relay.py   (needs websockets==15.0.1)
"""
import asyncio
import json
import os
import sys
import tempfile
import time
import urllib.request

EVENTS = os.path.join(tempfile.mkdtemp(), "events.json")
# history from a previous relay run: a chain that is gone by now
with open(EVENTS, "w") as f:
    json.dump({"since": 1000, "chain": {"block1_hash": "dead", "block1_ts": 1000, "tip": 40, "tip_hash": "beef", "tip_ts": 4000},
               "restarts": [], "dropped": []}, f)
os.environ.update(EVENTS_PATH=EVENTS, DROP_GRACE_SECONDS="1", STATS_CACHE_SECONDS="0")
os.environ.update(UPSTREAM_URL="ws://127.0.0.1:18765", LISTEN_HOST="127.0.0.1", LISTEN_PORT="18766",
                  TRUST_PROXY="1", MAX_PER_IP="3", CLIENT_BURST="20", LOOKUP_CACHE_SECONDS="10", GOV_POLL_SECONDS="4", TAU_GOVERNANCE_OPEN_ADMISSION="true")
sys.path.insert(0, os.path.dirname(__file__))

from websockets.asyncio.client import connect  # noqa: E402
from websockets.asyncio.server import serve  # noqa: E402
from websockets.exceptions import InvalidStatus  # noqa: E402

import relay  # noqa: E402

HEAVY = {"getblocks", "getgovernance", "gettaustate"}
mock = {"blocks": [], "heavy_violations": 0, "commands": [], "connections": 0, "mempool": []}
ALICE, BOB = "ef" * 48, "12" * 48


def block(n, chain=0):
    txs = [{"tx_type": "user_tx", "sender_pubkey": ALICE, "operations": {"1": [[ALICE, BOB, "5"]]}}] if n % 3 == 1 else []
    return {"block_hash": f"{chain:04x}{n:060x}", "header": {"block_number": n, "timestamp": 1_700_000_000 + 70 * n,
            "proposer_pubkey": "ab" * 48, "state_hash": "cd" * 32}, "tx_ids": [f"{chain:04x}{n:060x}"[::-1]] * len(txs),
            "transactions": txs}


# the chain is already longer than one getblocks window when the relay starts
mock["blocks"] = [block(n) for n in range(60)]


def _stats():
    with urllib.request.urlopen("http://127.0.0.1:18766/stats", timeout=5) as r:
        return r.headers.get("Access-Control-Allow-Origin"), json.loads(r.read())


def stats():  # blocking client; run it off the event loop the relay lives on
    return asyncio.to_thread(_stats)


async def mock_node(ws):
    mock["connections"] += 1
    heavy = relay.TokenBucket(2, 0.5)
    async for msg in ws:
        parts = msg.split()
        cmd = parts[0]
        mock["commands"].append(msg)
        if cmd == "hello":
            await ws.send("ok version=1 env=test node=tau-node")
            continue
        if cmd in HEAVY and not heavy.take():
            mock["heavy_violations"] += 1
            await ws.send(relay.envelope_error("rate_limit", "Rate limit exceeded", "RATE_LIMITED"))
            continue
        if cmd == "getblocks":
            n = int(parts[1]) if len(parts) > 1 else len(mock["blocks"])  # no limit: every block
            bs = mock["blocks"][-n:]
            await ws.send(relay.envelope_ok(cmd, {"blocks": bs, "total": len(mock["blocks"]), "truncated": len(bs) < len(mock["blocks"])}))
        elif cmd == "getmempool":
            await ws.send(relay.envelope_ok(cmd, {"count": len(mock["mempool"]), "transactions": mock["mempool"]}))
        elif cmd == "getgovernance":
            await ws.send(relay.envelope_ok(cmd, {"active_validators": ["ab" * 48], "vote_quorum": 1, "consensus_rules": "o6[t] = 1",
                                                   "head_number": len(mock["blocks"]) - 1,
                                                   "network_tip": {"number": len(mock["blocks"]) + 4, "seen": time.time()}}))
        elif cmd == "gettaustate":
            await ws.send(relay.envelope_ok(cmd, {"rules_state": "always o1[t] = i1[t]."}))
        elif cmd == "getbalance":
            await ws.send(relay.envelope_ok(cmd, {"address": parts[1], "balance": 100000}))
        else:
            await ws.send(relay.envelope_error(cmd, "should never reach the node", "UNKNOWN_COMMAND"))


async def mint():
    while True:
        if mock.get("mint", True):
            mock["blocks"].append(block(len(mock["blocks"])))
        await asyncio.sleep(1)


async def ask(ws, cmd):
    await ws.send(cmd)
    while True:  # skip pushed messages
        msg = json.loads(await ws.recv())
        if (not msg.get("data", {}).get("pushed") or cmd == "presence") and msg.get("command") in (cmd.split()[0], "rate_limit"):
            return msg


def check(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        check.failed = True


check.failed = False


async def main():
    async with serve(mock_node, "127.0.0.1", 18765):
        minter = asyncio.create_task(mint())
        r = relay.Relay()
        runner = asyncio.create_task(r.run())
        await asyncio.sleep(1.5)
        url = "ws://127.0.0.1:18766"
        origin = {"Origin": "https://tauhud.com"}

        async with connect(url, additional_headers=origin) as ws:
            first = json.loads(await ws.recv())
            check(first.get("command") == "presence" and first["data"]["online"] == 1, "presence pushed on connect")
            await ws.send("hello version=1")
            check((await ws.recv()).startswith("ok version=1"), "handshake")
            m = await ask(ws, "getblocks 12")
            check(m["status"] == "ok" and len(m["data"]["blocks"]) >= 1, "getblocks served from cache")
            hs = [b["header"]["block_number"] for b in m["data"]["blocks"]]
            check(hs == sorted(hs), "blocks in ascending order")
            check((await ask(ws, "getgovernance"))["status"] == "ok", "getgovernance")
            check((await ask(ws, "getmempool"))["data"]["count"] == 0, "getmempool")

            # the whole chain is held, not just one window
            m = await ask(ws, "getblockrange 0 10")
            check(m["status"] == "ok" and [b["header"]["block_number"] for b in m["data"]["blocks"]] == list(range(10))
                  and m["data"]["head"] >= 59, "getblockrange serves the start of the chain")
            check((await ask(ws, "getblockrange 0 101"))["status"] == "error", "getblockrange caps count at 100")
            check((await ask(ws, "getblockrange 5"))["status"] == "error", "getblockrange needs two numbers")
            check(len((await ask(ws, "getblocks 99"))["data"]["blocks"]) == 50, "getblocks still capped at 50")
            cors, st = await stats()
            hs = [r[0] for r in st["blocks"]]
            check(cors == "*" and hs[0] == 0 and hs == list(range(hs[0], hs[-1] + 1)) and len(hs) >= 60, "/stats holds every block")
            row = st["blocks"][1]
            check(row[2] == 1 and row[3] == 1 and row[4] == 5 and row[6] == {"user_tx": 1}
                  and st["accounts"][row[7][0]] == ALICE, f"/stats block summary {row}")
            check(len(st["restarts"]) == 1 and st["restarts"][0]["old"]["tip"] == 40, "restart found at relay start")

            # a tx that leaves the mempool without reaching a block is counted as dropped
            mock["mempool"] = [{"tx_hash": "77" * 32, "sender": BOB, "tx_type": "user_tx"}]
            await asyncio.sleep(4)
            mock["mempool"] = []
            await asyncio.sleep(9)  # two mempool polls plus the grace period
            _, st = await stats()
            check(st["dropped_total"] == 1 and st["dropped"][0]["tx_hash"] == "77" * 32 and st["dropped"][0]["sender"] == BOB,
                  "dropped tx recorded")
            for _ in range(10):  # heavy reads are paced at startup; NOT_READY until the first poll
                ts = await ask(ws, "gettaustate")
                if ts["status"] == "ok" or ts["error"]["code"] != "NOT_READY":
                    break
                await asyncio.sleep(0.5)
            check(ts["status"] == "ok", "gettaustate")
            check((await ask(ws, "getbalance " + "ab" * 48))["data"]["balance"] == 100000, "account lookup passes through")
            before = len(mock["commands"])
            await ask(ws, "getbalance " + "ab" * 48)
            check(not any(c.startswith("getbalance") for c in mock["commands"][before:]), "lookup cached")
            for bad in ("sendtx {}", "createblock", "getbalance ../../etc", "getblocks -1", "getallaccounts", "history x"):
                reply = await ask(ws, bad)
                check(reply["status"] == "error", f"refused: {bad}")
            check(not any(c.split()[0] in ("sendtx", "createblock", "getallaccounts", "history") for c in mock["commands"]),
                  "no write/heavy command ever reached the node")

            # push: a new block arrives without asking
            pushed = None
            deadline = time.monotonic() + 6
            while time.monotonic() < deadline:
                msg = json.loads(await asyncio.wait_for(ws.recv(), 6))
                if msg.get("command") == "getblocks" and msg["data"].get("pushed"):
                    pushed = msg
                    break
            check(pushed is not None and len(pushed["data"]["blocks"]) >= 1, "new block pushed to visitor")

            # per-client rate limit
            for _ in range(25):
                await ws.send("getmempool")
            replies = [json.loads(await ws.recv()) for _ in range(25)]
            check(any(x.get("error", {}).get("code") == "RATE_LIMITED" for x in replies), "visitor rate limit")

        # chain reset: the node comes back with a shorter chain of other blocks
        # (testnet restarted on the same genesis); the relay drops the dead chain
        async with connect(url, additional_headers=origin) as ws:
            json.loads(await ws.recv())
            mock["mint"] = False  # a restarted chain grows slowly; keep the mock still
            mock["blocks"] = [block(n, chain=1) for n in range(3)]
            pushed = None
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                msg = json.loads(await asyncio.wait_for(ws.recv(), 8))
                if msg.get("command") == "getblocks" and msg["data"].get("reset"):
                    pushed = msg
                    break
            check(pushed is not None, "chain reset pushed to visitor")
            m = await ask(ws, "getblocks 50")
            hs = sorted(b["header"]["block_number"] for b in m["data"]["blocks"])
            check(hs == [0, 1, 2] and all(b["block_hash"].startswith("0001") for b in m["data"]["blocks"]),
                  f"cache holds only the new chain {hs}")
            _, st = await stats()
            check(len(st["restarts"]) == 2 and st["restarts"][1]["old"]["tip"] >= 60 and [r[0] for r in st["blocks"]] == [0, 1, 2],
                  "live restart recorded, /stats follows the new chain")
            with open(EVENTS) as f:
                check(len(json.load(f)["restarts"]) == 2, "restarts persisted to the events file")
        reader, writer = await asyncio.open_connection("127.0.0.1", 18766)
        writer.write(b"GET /health HTTP/1.1\r\nHost: x\r\n\r\n")
        body = json.loads((await reader.read(4096)).decode().split("\r\n\r\n", 1)[1])
        writer.close()
        check(body["height"] == 2 and body["total_blocks"] == 3, f"/health height follows the reset {body}")
        mock["mint"] = True

        # presence: a second visitor raises the count for both, leaving lowers it
        async with connect(url, additional_headers=origin) as a:
            json.loads(await a.recv())
            async with connect(url, additional_headers=origin) as b:
                seen = json.loads(await asyncio.wait_for(a.recv(), 3))
                check(seen["command"] == "presence" and seen["data"]["online"] == 2, "presence pushed on join")
                check((await ask(b, "presence"))["data"]["online"] == 2, "presence on request")
            seen = json.loads(await asyncio.wait_for(a.recv(), 3))
            check(seen["command"] == "presence" and seen["data"]["online"] == 1, "presence pushed on leave")

        # origin check
        try:
            async with connect(url, additional_headers={"Origin": "https://evil.example"}):
                check(False, "foreign origin refused")
        except InvalidStatus as e:
            check(e.response.status_code == 403, "foreign origin refused")

        # per-IP cap (3 in this test)
        hdr = {**origin, "X-Forwarded-For": "203.0.113.9"}
        conns = [await connect(url, additional_headers=hdr) for _ in range(3)]
        try:
            await connect(url, additional_headers=hdr)
            check(False, "per-IP connection cap")
        except InvalidStatus as e:
            check(e.response.status_code == 429, "per-IP connection cap")
        for c in conns:
            await c.close()

        # oversized message closes the socket
        async with connect(url, additional_headers=origin) as ws:
            json.loads(await ws.recv())  # presence push
            await ws.send("getblocks " + "1" * 2000)
            try:
                await ws.recv()
                check(False, "oversized message rejected")
            except Exception:
                check(True, "oversized message rejected")

        # health endpoint (getgovernance, which carries the canonical head, is re-polled every GOV_POLL_SECONDS)
        for _ in range(12):
            reader, writer = await asyncio.open_connection("127.0.0.1", 18766)
            writer.write(b"GET /health HTTP/1.1\r\nHost: x\r\n\r\n")
            raw = (await reader.read(4096)).decode()
            writer.close()
            body = json.loads(raw.split("\r\n\r\n", 1)[1])
            if body.get("live_default"):
                break
            await asyncio.sleep(1)
        check(raw.startswith("HTTP/1.1 200") and body["upstream_connected"] and body["height"] >= 1 and body["online"] == 0, f"/health {body}")
        check(body["canonical_height"] >= 1 and body["live_default"] is True, f"/health live_default follows canonical head {body}")
        check(body["tip_height"] == body["canonical_height"] + 5, f"/health tip_height from network_tip {body}")
        check(body["open_governance_admission"] is True, f"/health open_governance_admission from env {body}")

        # keep polling for a while; the node's heavy limit must never trip
        await asyncio.sleep(8)
        check(mock["heavy_violations"] == 0, f"never tripped node rate limit ({mock['heavy_violations']} violations)")
        check(mock["connections"] == 1, "single upstream connection")

        minter.cancel()
        runner.cancel()
    sys.exit(1 if check.failed else 0)


asyncio.run(main())

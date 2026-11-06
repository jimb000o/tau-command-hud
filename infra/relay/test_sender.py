"""The island bot and cruise ships have their own node connection: a send the node takes long to answer must not
hold the visitors' requests. Run: python3 infra/relay/test_sender.py"""
import asyncio
import json
import os
import sys
import time
import types

os.environ.setdefault("UPSTREAM_TIMEOUT_SECONDS", "2")
sys.path.insert(0, os.path.dirname(__file__))

from websockets.asyncio.server import serve  # noqa: E402

import relay  # noqa: E402

PORT = 18791
FAILED = []


def check(ok, what):
    print(("PASS " if ok else "FAIL ") + what)
    if not ok:
        FAILED.append(what)


async def node(ws):
    """A mock node: answers at once, except sendtx, which hangs longer than the relay waits."""
    async for msg in ws:
        if msg.startswith("hello"):
            await ws.send("ok version=1")
        elif msg.startswith("sendtx"):
            await asyncio.sleep(5)
        else:
            await ws.send(json.dumps({"status": "ok", "data": {"cmd": msg.split()[0]}}))


async def main():
    async with serve(node, "127.0.0.1", PORT):
        url = f"ws://127.0.0.1:{PORT}"
        visitors, sender = relay.Upstream(url), relay.Upstream(url, "sender")
        tasks = [asyncio.create_task(visitors.run()), asyncio.create_task(sender.run())]
        await asyncio.wait_for(asyncio.gather(visitors.connected.wait(), sender.connected.wait()), 5)
        r = types.SimpleNamespace(upstream=visitors, sender=sender)

        # a ship's send hangs on the sender connection; a visitor's request meanwhile answers at once
        hang = asyncio.create_task(relay.Relay.ask_sender(r, "sendtx {}"))
        await asyncio.sleep(0.1)
        t0 = time.monotonic()
        msg = await visitors.request("getmempool")
        took = time.monotonic() - t0
        check(msg and msg["data"]["cmd"] == "getmempool" and took < 0.5, f"visitor answered during a hanging send ({took:.2f} s)")
        check(await hang is None, "the hanging send gives up after UPSTREAM_TIMEOUT")
        check(visitors.connected.is_set(), "the visitors' connection stays open when the sender's send times out")

        # the sender reconnects by itself
        await asyncio.wait_for(sender.connected.wait(), 5)
        msg = await relay.Relay.ask_sender(r, "getsequence abc")
        check(bool(msg) and msg["data"]["cmd"] == "getsequence", "the bot asks through its own connection again")

        # sender briefly down: no borrowing (the bot waits rather than block visitors)
        lost = types.SimpleNamespace(ws=None, down_since=time.time(), request=None)

        async def nothing(cmd):
            return None
        lost.request = nothing
        r2 = types.SimpleNamespace(upstream=visitors, sender=lost)
        check(await relay.Relay.ask_sender(r2, "getsequence abc") is None, "sender just lost: no borrowing yet")
        # sender down for long: borrow the visitors' connection so the bot never goes silent
        lost.down_since = time.time() - relay.SENDER_FALLBACK - 1
        msg = await relay.Relay.ask_sender(r2, "getsequence abc")
        check(bool(msg) and msg["data"]["cmd"] == "getsequence", "sender down long: the bot borrows the visitors' connection")
        # switched off (SENDER_CONNECTION=0): everything goes the old shared way
        r3 = types.SimpleNamespace(upstream=visitors, sender=None)
        msg = await relay.Relay.ask_sender(r3, "getsequence abc")
        check(bool(msg) and msg["data"]["cmd"] == "getsequence", "switched off: the shared connection as before")

        for t in tasks:
            t.cancel()
    print("ALL PASS" if not FAILED else f"{len(FAILED)} FAILED")
    sys.exit(1 if FAILED else 0)


asyncio.run(main())

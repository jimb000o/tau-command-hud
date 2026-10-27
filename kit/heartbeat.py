"""Status line for a kit node, and its opt-in report to tauhud.com.

Once a minute: ask the local node (its WebSocket, internal to Docker) for its
canonical head and the highest network tip it has heard of, and log one line.
If NODE_NAME is set, also send that head to the Tau HUD relay, which lists the
node under "community nodes" on tauhud.com/stats and says whether it is on the
same chain as tauhud.com's own node.

Sent: the name, canonical height and head hash, network tip, kit version and
tau-testnet commit. Not sent: addresses, keys, peer IDs. The `key` is a random
secret kept in /data/report.key; the relay shows only its hash, so nobody else
can report under this node's row.

Run: python -I heartbeat.py [--once]   (needs websockets==15.0.1)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
import sys
import time

from websockets.asyncio.client import connect

log = logging.getLogger("tau-kit")

KIT_VERSION = "2"
NODE_URL = os.environ.get("NODE_URL", "ws://tau-node:65433")
NODE_NAME = os.environ.get("NODE_NAME", "").strip()
REPORT_URL = os.environ.get("REPORT_URL", "wss://node.tauhud.com")
TAU_TESTNET_REF = os.environ.get("TAU_TESTNET_REF", "")[:12]
KEY_PATH = os.environ.get("KEY_PATH", "/data/report.key")
EVERY = float(os.environ.get("HEARTBEAT_SECONDS", 60))
NAME_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,23}$")


async def ask(url: str, *commands: str) -> list:
    """Open a connection, say hello, send each command, return the replies."""
    async with connect(url, open_timeout=10, max_size=2**20) as ws:
        await ws.send("hello version=1")
        hello = await asyncio.wait_for(ws.recv(), 20)
        while str(hello).startswith("{"):  # the relay pushes presence on connect
            hello = await asyncio.wait_for(ws.recv(), 20)
        if not str(hello).startswith("ok"):
            raise RuntimeError(f"handshake refused: {hello}")
        replies = []
        for cmd in commands:
            await ws.send(cmd)
            while True:  # a relay may push other messages in between
                msg = json.loads(await asyncio.wait_for(ws.recv(), 20))
                if msg.get("command") in (cmd.split()[0], "rate_limit") and not (msg.get("data") or {}).get("pushed"):
                    break
            replies.append(msg)
        return replies


async def node_status() -> dict:
    (gov,) = await ask(NODE_URL, "getgovernance")
    if gov.get("status") != "ok":
        raise RuntimeError(f"getgovernance: {gov.get('error')}")
    data = gov["data"]
    tip = (data.get("network_tip") or {}).get("number")
    return {"height": int(data.get("head_number") or 0), "head": data.get("head_hash") or "",
            "tip": int(tip) if tip is not None else None}


def report_key() -> str:
    try:
        with open(KEY_PATH) as f:
            key = f.read().strip()
        if re.fullmatch(r"[0-9a-f]{32}", key):
            return key
    except FileNotFoundError:
        pass
    key = secrets.token_hex(16)
    fd = os.open(KEY_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(key + "\n")
    return key


async def send_report(st: dict) -> dict:
    parts = [f"key={report_key()}", f"name={NODE_NAME}", f"height={st['height']}", f"head={st['head']}",
             f"tip={st['tip'] if st['tip'] is not None else 'none'}", f"kit={KIT_VERSION}"]
    if re.fullmatch(r"[0-9a-f]{7,40}", TAU_TESTNET_REF):
        parts.append(f"ref={TAU_TESTNET_REF}")
    (reply,) = await ask(REPORT_URL, "report " + " ".join(parts))
    return reply


def describe(st: dict) -> str:
    if st["tip"] is None:
        sync = "no peer seen yet"
    elif st["height"] >= st["tip"]:
        sync = "in sync"
    else:
        sync = f"catching up, {st['tip'] - st['height']} behind"
    return f"height {st['height']} · network tip {st['tip'] if st['tip'] is not None else '?'} · {sync}"


def badge_lines(node_id: str) -> str:
    """Where the operator finds the node on the leaderboard, and its badge."""
    base = REPORT_URL.replace("wss://", "https://", 1).replace("ws://", "http://", 1).rstrip("/")
    badge = f"{base}/community/badge/{node_id}.svg"
    page = f"https://tauhud.com/nodes/#{node_id}"
    return (f"leaderboard: {page}\n"
            f"badge for a README or website (Markdown): [![Tau HUD node]({badge})]({page})")


AGREES = {"same": "same chain as tauhud.com", "different": "DIFFERENT chain from tauhud.com",
          "ahead": "ahead of tauhud.com", "unknown": "tauhud.com cannot compare yet"}


async def beat():
    try:
        st = await node_status()
    except Exception as exc:  # node still starting, building or restarting
        log.info("node not reachable yet (%s)", exc or exc.__class__.__name__)
        return
    line = describe(st)
    if NODE_NAME:
        try:
            reply = await send_report(st)
            if reply.get("status") == "ok":
                line += f" · reported as {NODE_NAME} ({AGREES.get(reply['data'].get('agrees'), '?')})"
                if not beat.shown_badge and reply["data"].get("id"):
                    log.info("%s", badge_lines(reply["data"]["id"]))
                    beat.shown_badge = True
            else:
                line += f" · report refused: {(reply.get('error') or {}).get('message')}"
        except Exception as exc:
            line += f" · report failed: {exc!r}"
    else:
        line += " · not reporting (NODE_NAME empty)"
    log.info("%s", line)


beat.shown_badge = False  # the leaderboard and badge links are logged once per start


async def main(once: bool):
    global NODE_NAME
    if NODE_NAME and not NAME_OK.match(NODE_NAME):
        log.error("NODE_NAME %r: use 1-24 of A-Z a-z 0-9 . _ - (starting with a letter or digit); not reporting", NODE_NAME)
        NODE_NAME = ""
    while True:
        started = time.monotonic()
        await beat()
        if once:
            return
        await asyncio.sleep(max(5.0, EVERY - (time.monotonic() - started)))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    asyncio.run(main("--once" in sys.argv))

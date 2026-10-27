"""Test of the share service against a mock relay.

The mock serves getblockrange / getgovernance / getaccountstate like relay.py
(with a pushed presence frame first) and GET /status. The test checks that the
chain is read in pages, that a changed chain is reloaded, that every card is a
1200×630 PNG, that the link pages carry og:/twitter: tags and send people on to
tauhud.com, and that bad paths get 404.

Run: python test_share.py   (needs websockets==15.0.1 and pillow; writes the
cards to $OUT if set, to look at them)
"""
import asyncio
import io
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp()
os.environ.update(RELAY_URL="ws://127.0.0.1:18781", RELAY_HTTP="http://127.0.0.1:18781", PORT="18782", POLL_SECONDS="0.3",
                  PROPOSALS_PATH=os.path.join(TMP, "proposals.json"), FONTS_DIR=os.path.join(HERE, "..", "alerts", "fonts"))
sys.path.insert(0, HERE)

from http import HTTPStatus  # noqa: E402

from PIL import Image  # noqa: E402
from websockets.asyncio.server import serve  # noqa: E402
from websockets.datastructures import Headers  # noqa: E402
from websockets.http11 import Response  # noqa: E402

import share  # noqa: E402

VAL = "80ad4a20" + "1" * 84 + "536b8"[:4]
A, B2, C3 = "a1f3" + "2" * 88 + "9c20", "7be0" + "3" * 88 + "41d2", "c4a8" + "4" * 88 + "0e17"
PID = "30" + "ab" * 31
T0 = 1793130000


def blk(n, txs, salt=""):
    return {"header": {"block_number": n, "timestamp": T0 + 12 * n, "proposer_pubkey": VAL if n else "0" * 96},
            "transactions": txs, "tx_ids": ["%064x" % (n * 10 + i) for i in range(len(txs))], "block_hash": "%062x%s" % (n, salt or "00")}


CHAINS = {"a": [blk(n, []) for n in range(330)]}
CHAINS["a"][5] = blk(5, [{"sender_pubkey": A, "operations": {"0": "o5[t] = 1"}}])
CHAINS["a"][322] = blk(322, [
    {"sender_pubkey": A, "operations": {"1": [[A, B2, "50"]]}},
    {"sender_pubkey": B2, "operations": {"1": [[B2, C3, "12"]]}},
    {"sender_pubkey": VAL, "tx_type": "consensus_rule_vote", "update_id": PID, "approve": True},
])
CHAINS["b"] = [blk(n, [], "ff") for n in range(40)]
CUR = {"chain": "a"}


async def ws_handler(ws):
    await ws.send(json.dumps({"status": "ok", "command": "presence", "data": {"online": 1, "pushed": True}}))
    async for m in ws:
        p = m.split()
        chain = CHAINS[CUR["chain"]]
        if p[0] == "hello":
            await ws.send("ok version=1 env=testnet node=tau-hud-relay")
        elif p[0] == "getblockrange":
            s, c = int(p[1]), int(p[2])
            await ws.send(json.dumps({"status": "ok", "command": "presence", "data": {"online": 2, "pushed": True}}))
            await ws.send(json.dumps({"status": "ok", "command": "getblockrange",
                                      "data": {"blocks": chain[s:s + c], "from": s, "total": len(chain), "head": len(chain) - 1}}))
        elif p[0] == "getgovernance":
            await ws.send(json.dumps({"status": "ok", "command": "getgovernance", "data": {"active_validators": [VAL]}}))
        elif p[0] == "getaccountstate":
            await ws.send(json.dumps({"status": "ok", "command": "getaccountstate", "data": {"address": p[1], "chain_balance": "1250"}}))


def http_status(connection, request):
    if request.path == "/status":
        body = json.dumps({"upstream_connected": True, "canonical_height": 329, "tip_height": 329}).encode()
        return Response(200, "OK", Headers([("Content-Type", "application/json")]), body)
    return None


def run_relay():
    async def main():
        async with serve(ws_handler, "127.0.0.1", 18781, process_request=http_status):
            await asyncio.Future()
    asyncio.run(main())


def get(path):
    try:
        with urllib.request.urlopen("http://127.0.0.1:18782" + path, timeout=20) as r:
            return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, None, b""


def wait(cond, what, t=15):
    end = time.time() + t
    while time.time() < end:
        if cond():
            return
        time.sleep(0.1)
    raise AssertionError("timed out: " + what)


def main():
    with open(os.environ["PROPOSALS_PATH"], "w") as f:
        json.dump({"rules": {"revision": 1, "validators": 1}, "proposals": [
            {"id": PID, "n": 30, "title": "New rule for valid blocks", "status": "agreed", "counted_votes": 1, "thr": 1,
             "votes": [{"h": 322, "voter": VAL, "counted": True, "approve": True}], "proposed_at": 300, "approved_at": 322,
             "activate_at": 5030, "explain": {"title": "New rule for valid blocks", "why": "Blocks that break the new check would be refused by every node.",
                                              "changes": [{"topic": "Valid blocks", "text": "a block only counts if it follows the new check"}]}},
            {"id": "99" + "cd" * 31, "n": 31, "title": "Base fee 1 → 2 AGRS", "status": "active", "counted_votes": 1, "thr": 1, "votes": [],
             "proposed_at": 10, "approved_at": 11, "activate_at": 20, "activated_at": 20, "activated_ts": T0 + 240, "rev": 1,
             "explain": {"title": "Base fee 1 → 2 AGRS", "why": "Every transaction would cost 2 AGRS instead of 1.", "changes": [{"topic": "Base fee", "text": "1 → 2 AGRS"}]}},
        ]}, f)
    threading.Thread(target=run_relay, daemon=True).start()
    time.sleep(0.3)
    threading.Thread(target=share.main, daemon=True).start()
    wait(lambda: share.CHAIN.head == 329, "chain read in pages")
    assert len(share.CHAIN.blocks) == 330

    out = os.environ.get("OUT")
    for name, path in [("hud", "/og/hud.png"), ("block", "/og/block/322.png"), ("block0", "/og/block/0.png"),
                       ("proposal", f"/og/proposal/{PID[:16]}.png"), ("active", "/og/proposal/99cdcdcd.png"),
                       ("address", f"/og/address/{A}.png"), ("validator", f"/og/address/{VAL}.png"), ("missing", "/og/block/99999.png")]:
        code, ctype, body = get(path)
        assert code == 200 and ctype == "image/png", (path, code, ctype)
        assert Image.open(io.BytesIO(body)).size == (1200, 630), path
        if out:
            os.makedirs(out, exist_ok=True)
            open(os.path.join(out, name + ".png"), "wb").write(body)

    a = share.address_numbers(A)
    assert (a["sent"], a["received"], a["balance"], a["last_h"]) == (2, 0, 1250, 322), a
    assert share.address_numbers(B2)["received"] == 1 and share.address_numbers(VAL)["sealed"] == 329
    n = share.block_numbers(322)
    assert [t["amt"] for t in n["txs"]] == [50, 12, None] and n["txs"][2]["tag"] == "yes" and n["validator"]

    code, ctype, body = get(f"/s/proposal/{PID[:16]}")
    page = body.decode()
    assert code == 200 and ctype.startswith("text/html")
    for want in ['property="og:image" content="https://node.tauhud.com/og/proposal/', 'name="twitter:card" content="summary_large_image"',
                 "New rule for valid blocks · Tau HUD", "Agreed with 1 of 1 votes. Takes effect in 4,701 blocks, about 16 h.",
                 f'location.replace("https://tauhud.com/proposals/#{PID[:16]}")']:
        assert want in page, (want, page)
    assert "https://tauhud.com/explorer/?b=322" in get("/s/block/322")[2].decode()
    assert "3 transactions" in get("/s/block/322")[2].decode()
    assert f"https://tauhud.com/explorer/?a={A}" in get(f"/s/address/{A}")[2].decode()
    assert "live at block #329" in get("/s/")[2].decode()
    for bad in ["/og/block/abc.png", "/og/address/1234.png", "/s/proposal/xyz", "/og/", "/og/nothing.png", "/s/block/1234567890", "/etc/passwd"]:
        assert get(bad)[0] == 404, bad

    CUR["chain"] = "b"   # the testnet restarted: a shorter chain with other hashes
    wait(lambda: share.CHAIN.head == 39 and share.CHAIN.blocks[39]["block_hash"].endswith("ff"), "reload after a chain restart")
    assert len(share.CHAIN.blocks) == 40
    print("ok")


if __name__ == "__main__":
    main()

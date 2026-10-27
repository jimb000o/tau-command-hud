"""End-to-end test of the question bot against a mock relay and a mock Telegram.

The mock relay serves /uptime and the read commands bot.py uses; the mock
Telegram hands out updates through getUpdates and records every sendMessage.
Checks: each question type gets the right answer with tauhud.com links, plain
questions work in private chats, groups only get answers to commands meant for
this bot, nothing ever goes to the alerts channel, old questions are skipped,
and the per-person limit holds.

Run: python test_bot.py   (needs websockets==15.0.1)
"""
import asyncio
import json
import os
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TMP = tempfile.mkdtemp()
os.environ.update(TELEGRAM_BOT_TOKEN="123:test", TELEGRAM_CHAT_ID="@tauHUDcom", TELEGRAM_API="http://127.0.0.1:18811",
                  RELAY_URL="ws://127.0.0.1:18810", RELAY_HTTP="http://127.0.0.1:18810", PUBLIC_DIR=TMP,
                  BOT_POLL_TIMEOUT="1", BOT_USER_BURST="5", BOT_USER_REFILL_SECONDS="30")
sys.path.insert(0, os.path.dirname(__file__))

from websockets.asyncio.server import serve  # noqa: E402
from websockets.datastructures import Headers  # noqa: E402
from websockets.http11 import Response  # noqa: E402

import bot  # noqa: E402

NOW = time.time()
TX_IN, TX_UNKNOWN = "ab" * 32, "cd" * 32
ADDR = "a1fe40d5e4f155a1af7cb5804ec1ecba9ee3fb1f594e8a7b398b7ed69a6b0ccfd5bb6fd6d8ff965f8e1eb98d5abe7d2b"
PID = "f00d" * 16


# ---------------- mock relay ----------------
async def mock_relay(ws):
    await ws.send("presence 3")  # the real relay's first frame is not JSON
    async for m in ws:
        p = m.split()
        await ws.send(json.dumps({"status": "ok", "command": "getblocks", "data": {"pushed": True, "blocks": []}}))
        if p[0] == "gettxstatus":
            st = {"tx_hash": p[1], "status": "confirmed", "block_number": 370, "confirmations": 3} if p[1] == TX_IN \
                else {"tx_hash": p[1], "status": "unknown"}
            await ws.send(json.dumps({"status": "ok", "command": "gettxstatus", "data": st}))
        elif p[0] == "getaccountstate":
            await ws.send(json.dumps({"status": "ok", "command": "getaccountstate",
                                      "data": {"address": p[1], "chain_balance": 99990, "pending_outgoing": 10, "pending_fees": 1}}))
        elif p[0] == "getblockrange":
            n = int(p[1])
            blocks = [{"block_hash": "9" * 64, "header": {"block_number": n, "timestamp": int(NOW) - 120},
                       "transactions": [{"tx_type": "consensus_rule_vote"}, {"tx_type": "user_tx"}, {}]}] if n <= 372 else []
            await ws.send(json.dumps({"status": "ok", "command": "getblockrange", "data": {"blocks": blocks, "head": 372}}))


def mock_http(connection, request):
    if request.path != "/uptime":
        return None
    hour = NOW - NOW % 3600
    body = {"last_block_ts": NOW - 14, "stall_seconds": 600,
            "hours": [[hour - 3600, 60, 60, 60], [hour, 40, 38, 38]],
            "restarts": [{"detected_at": NOW - 86400}], "stalls": [],
            "status": {"upstream_connected": True, "height": 372, "canonical_height": 372, "tip_height": 372, "online": 4}}
    return Response(200, "OK", Headers([("Content-Type", "application/json")]), json.dumps(body).encode())


def write_proposals():
    p = lambda n, status, title, **kw: {"id": f"{n:x}" * 64 if n > 1 else PID, "n": n, "title": title, "status": status,  # noqa: E731
                                        "activate_at": 5300, "thr": 1, "counted_votes": 0, **kw}
    data = {"chain": {"head": 372, "seconds_per_block": 72.0},
            "rules": {"revision": 2, "base_fee": 10},
            "proposals": [p(3, "voting", "Base fee 10 → 20 AGRS"), p(2, "agreed", "Same rules as now (no real change)", approved_at=341),
                          p(1, "active", "Which blocks count as valid", activated_at=60)]}
    json.dump(data, open(os.path.join(TMP, "proposals.json"), "w"))


# ---------------- mock Telegram ----------------
TG = {"updates": [], "sent": [], "next": 1, "lock": threading.Lock()}


class Api(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        method = self.path.rsplit("/", 1)[-1]
        assert self.path.startswith("/bot123:test/"), self.path
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        if method == "getMe":
            out = {"ok": True, "result": {"id": 1, "is_bot": True, "username": "TauHUDbot"}}
        elif method == "setMyCommands":
            TG["commands"] = body["commands"]
            out = {"ok": True, "result": True}
        elif method == "getUpdates":
            with TG["lock"]:
                res = [u for u in TG["updates"] if u["update_id"] >= body.get("offset", 0)]
            if not res:
                time.sleep(0.2)
            out = {"ok": True, "result": res}
        elif method == "sendMessage":
            TG["sent"].append(body)
            out = {"ok": True, "result": {"message_id": 1}}
        else:
            out = {"ok": False, "description": "unknown method"}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def say(text, chat_id=1001, ctype="private", user=7, date=None, username=None):
    with TG["lock"]:
        uid = TG["next"]
        TG["next"] += 1
        chat = {"id": chat_id, "type": ctype}
        if username:
            chat["username"] = username
        TG["updates"].append({"update_id": uid, "message": {"message_id": uid, "date": int(date or time.time()), "text": text,
                                                             "chat": chat, "from": {"id": user, "is_bot": False}}})


async def until(cond, what, timeout=8):
    end = time.time() + timeout
    while not cond():
        if time.time() > end:
            raise AssertionError("timed out waiting for " + what + f"; sent: {[s['text'][:60] for s in TG['sent']]}")
        await asyncio.sleep(0.05)


async def ask(text, **kw):
    n = len(TG["sent"])
    say(text, **kw)
    await until(lambda: len(TG["sent"]) > n, repr(text))
    await asyncio.sleep(0.1)
    return TG["sent"][n]


async def nothing_for(text, **kw):
    n = len(TG["sent"])
    say(text, **kw)
    await asyncio.sleep(1.2)
    assert len(TG["sent"]) == n, (text, TG["sent"][n:])


def test_parse():
    P = lambda t, private=True: bot.parse(t, "TauHUDbot", private)  # noqa: E731
    assert P("/height") == ("height", None)
    assert P("/start") == ("help", None)
    assert P("height?") == ("height", None)
    assert P("last proposal?") == ("proposals", None)
    assert P("is my tx in?") == ("tx", None)
    assert P(f"is my tx in? {TX_IN}") == ("tx", TX_IN)
    assert P(f"0x{ADDR.upper()}") == ("address", ADDR)
    assert P("/tx@TauHUDbot " + TX_IN) == ("tx", TX_IN)
    assert P("what happened in block 12?") == ("block", "12")
    assert P("is the testnet down?") == ("status", None)
    assert P("hello") == ("help", None)
    assert P("hello", private=False) is None
    assert P("/height@OtherBot", private=False) is None
    assert P("@TauHUDbot height?", private=False) == ("height", None)


async def main():
    write_proposals()
    srv = ThreadingHTTPServer(("127.0.0.1", 18811), Api)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    async with serve(mock_relay, "127.0.0.1", 18810, process_request=mock_http):
        b = bot.Bot()
        task = asyncio.create_task(b.run())
        await until(lambda: "commands" in TG, "setMyCommands")
        assert [c["command"] for c in TG["commands"]][:3] == ["height", "proposals", "tx"]

        r = await ask("/height")
        assert "Block #372" in r["text"] and "14 s ago" in r["text"] and "every 72 s" in r["text"], r["text"]
        assert "https://tauhud.com/explorer/?b=372" in r["text"] and r["parse_mode"] == "HTML" and r["chat_id"] == 1001

        r = await ask("last proposal?")
        t = r["text"]
        assert "Coming up (2)" in t and "Base fee 10 → 20 AGRS" in t and "0 of 1 vote," in t and "(~4 days)" in t, t
        assert "Agreed. Takes effect at block #5,300" in t and "In force (1)" in t and "Which blocks count as valid" in t, t
        assert f"/proposals/#{PID[:16]}" in t and "revision 2" in t, t

        r = await ask(f"is my tx in? {TX_IN}")
        assert "In a block" in r["text"] and "/explorer/?b=370" in r["text"] and "3 confirmations" in r["text"], r["text"]
        assert f"/explorer/?tx={TX_IN}" in r["text"]
        r = await ask(f"/tx {TX_UNKNOWN}")
        assert "Not known" in r["text"], r["text"]
        r = await ask("/tx")
        assert "transaction hash" in r["text"], r["text"]

        b.buckets.clear()  # the same person asked 5 times already
        r = await ask(ADDR)
        assert "99,990 AGRS" in r["text"] and "−11 sent" in r["text"] and f"/account/?a={ADDR}" in r["text"], r["text"]

        b.buckets.clear()
        r = await ask("/block 5")
        assert "Block #5" in r["text"] and "1 vote, 2 transfers" in r["text"] and "2 min ago" in r["text"], r["text"]
        r = await ask("/block 999")
        assert "does not exist yet" in r["text"] and "#372" in r["text"], r["text"]

        b.buckets.clear()
        r = await ask("is it running?")
        t = r["text"]
        assert "Running and in sync" in t and "up 98.0 %" in t and "restarts in the last 7 days: 1" in t and "4 people" in t, t

        r = await ask("hi there")
        assert "/height" in r["text"] and "t.me/tauHUDcom" in r["text"], r["text"]

        # groups: only commands, only ours; answers quote the question
        await nothing_for("height?", chat_id=-50, ctype="supergroup", user=8)
        await nothing_for("/height@OtherBot", chat_id=-50, ctype="supergroup", user=8)
        r = await ask("/status@TauHUDbot", chat_id=-50, ctype="supergroup", user=8)
        assert r["chat_id"] == -50 and "reply_parameters" in r, r

        # the alerts channel and old questions: never answered
        await nothing_for("/height", chat_id=-100123, ctype="channel", username="tauHUDcom")
        await nothing_for("/height", chat_id=-100123, ctype="supergroup", username="tauHUDcom")
        await nothing_for("/height", date=time.time() - 3600)
        assert not any(str(s["chat_id"]).startswith("-100") for s in TG["sent"])

        # per person: 5 questions in a row, then one notice, then quiet
        n = len(TG["sent"])
        for _ in range(8):
            say("/height", user=99, chat_id=99)
        await asyncio.sleep(1.5)
        got = [s["text"] for s in TG["sent"][n:]]
        assert len(got) == 6 and sum("lot of questions" in g for g in got) == 1, got
        r = await ask("/height", user=100, chat_id=100)  # someone else is not affected
        assert "Block #372" in r["text"]
        task.cancel()
    srv.shutdown()
    if "-v" in sys.argv:
        print("\n----\n".join(s["text"] for s in TG["sent"][:12]))
    print("all bot tests passed")


test_parse()
asyncio.run(main())

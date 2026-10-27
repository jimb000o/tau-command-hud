"""End-to-end test of the alerts watcher against a mock relay.

The mock serves getblockrange/getgovernance like relay.py. The test checks
that the first run records history without posting it, that a proposal, its
votes, agreement, activation and a dropped proposal become news and are posted
once each, that the Atom feed and proposals.json are written, and that a chain
restart is reported.

Run: python test_alerts.py   (needs websockets==15.0.1 and blake3==1.0.5)
"""
import asyncio
import json
import os
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

TMP = tempfile.mkdtemp()
os.environ.update(RELAY_URL="ws://127.0.0.1:18799", RELAY_HTTP="http://127.0.0.1:18799", STATE_PATH=os.path.join(TMP, "state", "alerts.json"),
                  PUBLIC_DIR=os.path.join(TMP, "public"), POLL_SECONDS="0.3", TELEGRAM_BOT_TOKEN="", TAU_GOVERNANCE_OPEN_ADMISSION="true")
_now = time.gmtime()
os.environ.update(RECAP_WEEKDAY=str(_now.tm_wday), RECAP_HOUR=str(_now.tm_hour))  # a recap slot that just passed
sys.path.insert(0, os.path.dirname(__file__))

from websockets.asyncio.server import serve  # noqa: E402
from websockets.datastructures import Headers  # noqa: E402
from websockets.http11 import Response  # noqa: E402

import alerts  # noqa: E402

V1 = alerts.GENESIS_VALIDATORS[0]
FEE_RULE = "always (o9[t]:bv[24] = { #x000014 }:bv[24])"
chain = {"id": "a", "blocks": []}


def block(h, txs=()):
    return {"block_hash": f"{chain['id']}{h:063x}", "header": {"block_number": h, "timestamp": int(time.time()) - 600 + h},
            "transactions": list(txs), "tx_ids": [f"tx{h}-{i}" for i in range(len(txs))]}


def propose(act, revs=(FEE_RULE,), patch=None):
    t = {"tx_type": "consensus_rule_update", "sender_pubkey": V1, "rule_revisions": list(revs), "activate_at_height": act}
    if patch:
        t["host_contract_patch"] = patch
    return t


def vote(uid, who=V1):
    return {"tx_type": "consensus_rule_vote", "sender_pubkey": who, "update_id": uid, "approve": True}


def add(*bs):
    chain["blocks"].extend(bs)


async def mock_relay(ws):
    async for m in ws:
        p = m.split()
        if p[0] == "getblockrange":
            s, n = int(p[1]), int(p[2])
            got = [b for b in chain["blocks"] if s <= b["header"]["block_number"] < s + n]
            head = chain["blocks"][-1]["header"]["block_number"] if chain["blocks"] else None
            await ws.send(json.dumps({"status": "ok", "command": "getblockrange", "data": {"blocks": got, "from": s, "head": head}}))
            # a push in between, as the real relay does
            await ws.send(json.dumps({"status": "ok", "command": "presence", "data": {"online": 1, "pushed": True}}))
        elif p[0] == "getgovernance":
            await ws.send(json.dumps({"status": "ok", "command": "getgovernance", "data": {"head_number": len(chain["blocks"])}}))


def mock_http(connection, request):
    """/stats and /community as relay.py serves them."""
    if request.path == "/stats":
        rows = [[b["header"]["block_number"], b["header"]["timestamp"], len(b["transactions"]), 0, 0, 0, {}, [0] if b["transactions"] else []]
                for b in chain["blocks"]]
        body = {"fields": ["height", "timestamp", "txs", "transfers", "volume", "proposer", "types", "senders"], "blocks": rows,
                "accounts": [V1], "head": len(chain["blocks"]), "restarts": []}
    elif request.path == "/community":
        body = {"nodes": [{"first_seen": time.time() - 60}]}
    else:
        return None
    return Response(200, "OK", Headers([("Content-Type", "application/json")]), json.dumps(body).encode())


class FakeOutlet(alerts.Outlet):
    def __init__(self, name):
        self.name, self.sent, self.fail_once = name, [], name == "x"

    def enabled(self):
        return True

    def send(self, item):
        if self.fail_once:
            self.fail_once = False
            return False, 0.01, "HTTP 503"
        self.sent.append(item["kind"] + ":" + item["headline"])
        return True, None, ""

    def send_photo(self, png, r):
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        self.sent.append(f"recap:{r['blocks']}")
        return True, None, ""


async def until(cond, what, timeout=10):
    end = time.time() + timeout
    while not cond():
        if time.time() > end:
            raise AssertionError("timed out waiting for " + what)
        await asyncio.sleep(0.1)


async def main():
    alerts.asyncio.sleep = _fast_sleep(alerts.asyncio.sleep)
    old_uid = alerts.update_id(propose(5))
    # history: a proposal agreed and active before the watcher ever ran
    add(*(block(h) for h in range(1, 3)), block(3, [propose(5)]), block(4, [vote(old_uid)]), block(5), block(6))
    tg, x = FakeOutlet("telegram"), FakeOutlet("x")
    w = alerts.Watcher([tg, x])
    async with serve(mock_relay, "127.0.0.1", 18799, process_request=mock_http):
        task = asyncio.create_task(w.run())
        await until(lambda: w.state["primed"] and len(w.state["items"]) == 3, "first replay")
        assert all(not it["news"] for it in w.state["items"]), "first run must be history"
        await asyncio.sleep(0.8)
        assert tg.sent == [] and x.sent == [], (tg.sent, x.sent)

        # news: a fee change proposed, voted, agreed and active; another one dropped
        uid = alerts.update_id(propose(12, (FEE_RULE.replace("14", "1e"),)))
        add(block(7, [propose(12, (FEE_RULE.replace("14", "1e"),)), propose(9, ("always (o5[t] = 1)",))]))
        await until(lambda: len(tg.sent) == 2, "proposals posted")
        add(block(8, [vote(uid)]), block(9), block(10), block(11), block(12))
        await until(lambda: len(tg.sent) == 5, "agree, drop, activate posted")
        kinds = [s.split(":")[0] for s in tg.sent]
        assert kinds == ["proposed", "proposed", "agreed", "dropped", "active"], kinds
        assert "Base fee 20 → 30 AGRS" in tg.sent[0], tg.sent[0]
        await until(lambda: len(x.sent) == 5, "x catches up after its failure")

        data = json.load(open(os.path.join(os.environ["PUBLIC_DIR"], "proposals.json")))
        st = {p["title"]: p["status"] for p in data["proposals"]}
        assert st == {"Base fee 10 → 20 AGRS": "active", "Base fee 20 → 30 AGRS": "active", "New definition of o5": "dropped"}, st
        assert data["rules"]["revision"] == 3 and data["rules"]["base_fee"] == 30, data["rules"]
        feed = ET.parse(os.path.join(os.environ["PUBLIC_DIR"], "feed.xml")).getroot()
        assert len(feed.findall("{http://www.w3.org/2005/Atom}entry")) == 8

        # --preview reads the chain on its own and posts nothing
        assert await alerts.preview_latest(2) == 0

        # weekly recap: the first run only notes the slot; a passed slot draws and posts once
        assert w.state["recap"]["slot"] == alerts.Watcher.recap_slot(time.time()) and not any(x.startswith("recap") for x in tg.sent)
        w.state["recap"]["slot"] -= 7 * 86400
        recaps = lambda o: [s for s in o.sent if s.startswith("recap:")]  # noqa: E731
        await until(lambda: recaps(tg) and recaps(x), "recap posted")
        idx = json.load(open(os.path.join(os.environ["PUBLIC_DIR"], "recap", "index.json")))
        assert len(idx) == 1 and os.path.getsize(os.path.join(os.environ["PUBLIC_DIR"], "recap", "latest.png")) > 10000, idx
        await asyncio.sleep(1)
        assert len(recaps(tg)) == 1, tg.sent

        # a restart of the testnet: new block 1
        chain["id"], chain["blocks"] = "b", []
        add(block(1), block(2))
        await until(lambda: any(s.startswith("restart:") for s in tg.sent), "restart posted")
        assert len(w.blocks) == 2

        # state survives a watcher restart: nothing is posted twice
        task.cancel()
        w2 = alerts.Watcher([tg2 := FakeOutlet("telegram")])
        w2.state["outlets"] = w.state["outlets"]
        task2 = asyncio.create_task(w2.run())
        await asyncio.sleep(1.5)
        assert tg2.sent == [], tg2.sent
        task2.cancel()
    print("text sample:\n" + alerts.telegram_text(w.state["items"][-4]) + "\n\n" + alerts.x_text(w.state["items"][-4]))
    print("all alerts tests passed")


def _fast_sleep(real):
    async def sleep(s):
        await real(min(s, 0.2))
    return sleep



def test_rule_diff():
    """The rule text diff: changed lines, an added stream, and no difference for the same text."""
    spec = alerts.explain.clauses(alerts.explain.GENESIS_RULES)
    d = alerts.explain.diff([FEE_RULE], spec)
    assert (d["added"], d["removed"], d["streams"]) == (1, 1, ["o9"]), d
    assert [r[0] for r in d["lines"] if r[0] != " "] == ["-", "+"] and "#x000014" in d["lines"][-2][1], d
    d = alerts.explain.diff(["always (o10[t]:bv[16] = i15[t]:bv[16])"], spec)
    assert (d["added"], d["removed"]) == (1, 0), d   # the clause before it keeps its line, only && is added
    d = alerts.explain.diff([alerts.explain.GENESIS_RULES.replace("    ", "  ")], spec)
    assert alerts.explain.diff_summary(d) == "no difference", d
    item = {"kind": "proposed", "headline": "x", "what": [], "why": "", "facts": [], "link": "https://tauhud.com",
            "diff": {"summary": "no difference", "lines": [], "more": 0}}
    assert "Rule text diff</b>: none" in alerts.telegram_text(item)


test_rule_diff()
asyncio.run(main())

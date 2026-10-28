"""Unit test of the new-node alerts (no network): nodes already there at the
first run are not news, a node must stay NEWNODE_HOLD_SECONDS, each node is
posted once, peers that come and go are never posted, a daily cap holds.

Run: python test_newnode_alerts.py   (needs websockets==15.0.1)
"""
import asyncio
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, NEWNODE_HOLD_SECONDS="1800",
                  NEWNODE_POLL_SECONDS="60", NEWNODE_DAILY_CAP="2", TELEGRAM_BOT_TOKEN="")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


class Fake(alerts.Outlet):
    name = "telegram"

    def __init__(self):
        self.sent = []

    def enabled(self):
        return True

    def send_text(self, text):
        self.sent.append(text)
        return True, None, ""


BOOT = "12D3KooWDpWEYxBy8y84AssrPSLaq9DxC7Lncmn5wERJnAWZFnYC"
T0 = 1_800_000_000.0
world = {"peers": [], "nodes": []}


def peer(pid, first, last, **kw):
    return {"id": pid, "label": None, "community": None, "first_seen": first, "last_seen": last,
            "head": 1200, "online": last - first >= 600, **kw}


async def main():
    tg = Fake()
    w = alerts.Watcher([tg])
    w.relay_json = lambda path: {"peers": world["peers"]} if path == "/peers" else {"nodes": world["nodes"]}

    async def at(t):
        await w.maybe_newnodes(t)

    # first run: what is there is history
    world["peers"] = [peer(BOOT, T0 - 86400, T0, label="IDNI bootnode"), peer("12D3KooWOld" + "a" * 30, T0 - 9000, T0)]
    await at(T0)
    check(not tg.sent and w.state["newnodes"]["primed"], "first run posts nothing")

    # a tester that comes for 5 minutes and goes: never posted
    world["peers"].append(peer("12D3KooWFlicker" + "b" * 30, T0 + 60, T0 + 360))
    for k in range(1, 40):
        await at(T0 + k * 120)
    check(not tg.sent, "a peer that came and went is not posted")

    # a peer that stays: posted once, after 30 min
    stay = "12D3KooWStays" + "c" * 30
    world["peers"].append(peer(stay, T0 + 5000, T0 + 5000))
    await at(T0 + 5100)
    world["peers"][-1]["last_seen"] = T0 + 6000
    await at(T0 + 6000)
    check(not tg.sent, "not posted before it stayed 30 min")
    world["peers"][-1]["last_seen"] = T0 + 6900
    await at(T0 + 6900)
    check(len(tg.sent) == 1 and "joined the Tau testnet" in tg.sent[0] and "Nodes online now" in tg.sent[0], "posted after 30 min")
    world["peers"][-1]["last_seen"] = T0 + 7200
    await at(T0 + 7200)
    check(len(tg.sent) == 1, "never posted twice")

    # a kit node with a name; its peer ID is not posted again
    world["nodes"] = [{"id": "a1b2c3d4e5f6", "name": "berlin-arm", "online": True, "first_seen": T0 + 7000, "last_seen": T0 + 9000, "height": 1300}]
    world["peers"].append(peer("12D3KooWKit" + "d" * 30, T0 + 7000, T0 + 9000, community={"id": "a1b2c3d4e5f6", "name": "berlin-arm"}))
    await at(T0 + 9000)
    check(len(tg.sent) == 2 and "New community node: berlin-arm" in tg.sent[1], "kit node posted by name")
    check(sum("joined" in t for t in tg.sent) == 1, "its peer ID is not posted as a second node")

    # daily cap: the third new node that day is recorded, not posted
    world["peers"].append(peer("12D3KooWThird" + "e" * 30, T0 + 7000, T0 + 9300))
    await at(T0 + 9300)
    check(len(tg.sent) == 2 and "peer:12D3KooWThird" + "e" * 30 in w.state["newnodes"]["known"], "daily cap holds")

    # a node first seen days ago that comes back is not new
    world["peers"].append(peer("12D3KooWBack" + "f" * 30, T0 - 5 * 86400, T0 + 200000))
    await at(T0 + 200000)
    check(len(tg.sent) == 2, "an old node coming back is not news")
    sys.exit(1 if failed else 0)


asyncio.run(main())

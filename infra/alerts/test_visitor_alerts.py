"""Unit test of the posts for rule changes visitors voted into the simulation (no network): only voted in, with enough
votes, after the vote closed and before it is in force, once each, at most three a day, marked as simulation.

Run: python test_visitor_alerts.py   (needs websockets==15.0.1)
"""
import asyncio
import os
import sys
import tempfile
from datetime import datetime, timezone

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="", SITE_URL="https://tauhud.com")
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

    def send_text(self, text, buttons=None):
        self.sent.append((text, buttons))
        return True, None, ""


T = datetime(2026, 10, 28, 20, 0, tzinfo=timezone.utc).timestamp()


def item(yes, no, closes, act, kind="fee", value=8):
    return {"yes": yes, "no": no, "opens": closes - 360, "closes": closes,
            "meta": {"kind": kind, "value": value, "activate_ts": act, "activate_at": 9075, "proposed_at": 9000}}


votes = {"items": {
    "visitor:aaa": item(3, 1, T - 60, T + 180),                   # voted in, 4 votes: posted
    "visitor:bbb": item(1, 0, T - 60, T + 180),                   # voted in, 1 vote: too few
    "visitor:ccc": item(2, 2, T - 60, T + 180),                   # a tie is a no
    "visitor:ddd": item(5, 0, T + 60, T + 300),                   # still open
    "visitor:eee": item(5, 0, T - 600, T - 10),                   # already in force: too late
    "slot:5": item(9, 0, T - 60, T + 180),                        # the hourly ballots are not ours
}}
tg = Fake()
w = alerts.Watcher([tg])
asyncio.run(w.maybe_visitors(T, votes))
check(len(tg.sent) == 1, f"one post: only the voted-in proposal with enough votes ({len(tg.sent)})")
text = tg.sent[0][0] if tg.sent else ""
check(text.startswith("🧪 <b>SIMULATION · not the real testnet</b>"), "first line marks the simulation")
check("Base fee → 8 AGRS" in text and "3 yes · 1 no" in text and "20:03 UTC" in text, "says what changes, the votes and when it is in force")
check("not the real Tau testnet" in text.replace("Nothing here happens on the real Tau testnet", "not the real Tau testnet"), "ends with the simulation notice")
check(tg.sent and tg.sent[0][1]["inline_keyboard"][0][0]["url"].endswith("?mode=sim"), "the button opens the simulation")
asyncio.run(w.maybe_visitors(T + 30, votes))
check(len(tg.sent) == 1, "never twice")

many = {"items": {f"visitor:{i}": item(4, 0, T - 60, T + 100 + i) for i in range(6)}}
tg2 = Fake()
w2 = alerts.Watcher([tg2])
w2.state.pop("visitors", None)   # the state file is shared with the first watcher
asyncio.run(w2.maybe_visitors(T, many))
check(len(tg2.sent) == 3, f"at most three a day ({len(tg2.sent)})")
asyncio.run(w2.maybe_visitors(T + 86400, {"items": {"visitor:new": item(4, 0, T + 86400 - 60, T + 86400 + 100)}}))
check(len(tg2.sent) == 4, "a new day, a new allowance")

check(alerts.visitor_title({"kind": "quorum", "value": "majority"}) == "Agreement threshold → more than half of the validators", "quorum in words")
check(alerts.visitor_title({"kind": "mode", "value": "stake"}) == "Switch consensus to proof of stake", "consensus switch in words")

alerts.SIM_ON = False
tg3 = Fake()
asyncio.run(alerts.Watcher([tg3]).maybe_visitors(T, votes))
check(not tg3.sent, "SIM_ALERTS=false turns them off")

print("all passed" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

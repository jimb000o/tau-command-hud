"""Unit test of the testnet health alerts (no network): the first state is not
news, a drop must hold for HEALTH_CONFIRM_SECONDS, a score between the two
thresholds keeps the last state, recovery is posted with the time it was down.

Run: python test_health_alerts.py   (needs websockets==15.0.1)
"""
import asyncio
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, HEALTH_CONFIRM_SECONDS="600",
                  HEALTH_POLL_SECONDS="60", TELEGRAM_BOT_TOKEN="")
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


def score(n, state=None, stalled=0):
    f = [{"key": "node", "weight": 20, "points": 20, "value": "yes"},
         {"key": "last_block", "weight": 20, "points": 0 if stalled else 20, "value": stalled}]
    return {"score": n, "state": state or ("healthy" if n >= 80 else "degraded" if n >= 50 else "down"),
            "label": (state or "x").title(), "factors": f}


tg = Fake()
w = alerts.Watcher([tg])
feed = []
w.health_now = lambda: feed[0]
T = 1_800_000_000


async def at(t, h):
    feed[:] = [h]
    await w.maybe_health(T + t)


async def main():
    await at(0, score(95))
    check(w.state["health"]["posted"] == "up" and not tg.sent, "first run records the state, posts nothing")
    await at(60, score(30, "down", stalled=1900))
    await at(120, score(30, "down", stalled=1960))
    check(not tg.sent, "a drop is not posted before it held 10 minutes")
    await at(300, score(95))
    await at(360, score(30, "down", stalled=2000))
    await at(700, score(30, "down", stalled=2400))
    check(not tg.sent, "the clock restarts after a recovery in between")
    await at(980, score(30, "down", stalled=2600))
    check(len(tg.sent) == 1 and "🔴" in tg.sent[0] and "No new block for 43 minutes" in tg.sent[0], f"down posted with its reason {tg.sent}")
    await at(1100, score(60))
    await at(1800, score(60))
    check(len(tg.sent) == 1, "a score between the thresholds keeps the down state")
    await at(1900, score(92))
    await at(2600, score(92))
    check(len(tg.sent) == 2 and "recovered" in tg.sent[1] and "down for 37 minutes" in tg.sent[1], f"recovery posted {tg.sent[-1:]}")
    await at(2700, None)  # relay gone
    await at(3400, None)
    check(len(tg.sent) == 3 and "no data" in tg.sent[2], "a relay that stays away is posted")
    await at(3410, score(95))
    check(len(tg.sent) == 3, "checks at most once a minute")


asyncio.run(main())
sys.exit(1 if failed else 0)

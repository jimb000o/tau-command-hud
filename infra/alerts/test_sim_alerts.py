"""Unit test of the simulation posts (no network): the day's two consensus
switches are announced while their proposal is open, once each, never late,
only on Telegram, marked as simulation; a failed post is retried after a pause.

Run: python test_sim_alerts.py   (needs websockets==15.0.1)
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

    def __init__(self, fail=0):
        self.sent, self.fail = [], fail

    def enabled(self):
        return True

    def send_text(self, text, buttons=None):
        if self.fail:
            self.fail -= 1
            return False, 120.0, "HTTP 429"
        self.sent.append((text, buttons))
        return True, None, ""


def at(day: str, hm: str) -> float:
    return datetime.strptime(f"{day} {hm}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()


def run(w, t):
    asyncio.run(w.maybe_sim(t))


# the schedule, from the clock alone
sw = alerts.sim_switches(at("2026-10-28", "15:07"))
check([s["kind"] for s in sw] == ["stake", "fixed"], "two switches a day: proof of stake, then the fixed list")
check(sw[0]["proposed"] == at("2026-10-28", "10:20") and sw[0]["in_force"] == at("2026-10-28", "10:30"), "proof of stake proposed 10:20 UTC, in force 10:30 UTC")
check(sw[1]["proposed"] == at("2026-10-28", "16:20") and sw[1]["in_force"] == at("2026-10-28", "16:30"), "fixed list proposed 16:20 UTC, in force 16:30 UTC")
check(sw[0]["next"] == at("2026-10-28", "16:30") and sw[1]["next"] == at("2026-10-29", "10:30"), "each post knows when the other switch follows")
check(sw[0]["key"] == "2026-10-28:stake", "state key is day and kind")

# the text
txt = alerts.sim_text(sw[0])
check(txt.startswith("🧪 <b>SIMULATION · not the real testnet</b>"), "first line says SIMULATION")
check("Nothing here happens on the real Tau testnet" in txt and txt.rstrip().endswith("Watch it in the simulation</a>"), "last lines: the simulated notice and the link")
check("proof of stake" in txt and "10:30 UTC" in txt and "16:30 UTC" in txt, "says what, when, and when it turns back")
check("?mode=sim" in txt, "links the site in Simulation mode")
check("Why it matters" in txt and "What to watch" in txt, "why and what to watch, like every post")
check("until 10:27 UTC" in alerts.sim_text(sw[0]) and "majority" in alerts.sim_text(sw[0]), "the post asks visitors to vote until the ballot closes")
check("fixed validator list" in alerts.sim_text(sw[1]) and "10:30 UTC" in alerts.sim_text(sw[1]), "the return post names the list and tomorrow's switch")
check(alerts.sim_buttons()["inline_keyboard"][0][0]["url"].endswith("/proposals/?mode=sim"), "the one button opens the simulation")

# posting: only while the proposal is open, once
tg = Fake()
w = alerts.Watcher([tg])
run(w, at("2026-10-28", "10:19"))
check(tg.sent == [], "nothing before the proposal appears")
run(w, at("2026-10-28", "10:20"))
check(len(tg.sent) == 1 and "proof of stake" in tg.sent[0][0], "posted when proof of stake is proposed")
check(tg.sent[0][1] == alerts.sim_buttons(), "with the simulation button instead of the testnet buttons")
run(w, at("2026-10-28", "10:25"))
run(w, at("2026-10-28", "10:29"))
check(len(tg.sent) == 1, "posted once")
run(w, at("2026-10-28", "12:00"))
check(len(tg.sent) == 1, "nothing between the switches")
run(w, at("2026-10-28", "16:21"))
check(len(tg.sent) == 2 and "fixed validator list" in tg.sent[1][0], "posted when the fixed list is proposed")
run(w, at("2026-10-29", "10:20"))
check(len(tg.sent) == 3, "the next day posts again")
check(w.state["sim"]["posted"].get("2026-10-28:stake") and os.path.exists(os.environ["STATE_PATH"]), "what was posted is in the state file")

# restarted after the window: never late
tg2 = Fake()
w2 = alerts.Watcher([tg2])
w2.state["sim"] = {"posted": {}}
run(w2, at("2026-10-28", "10:31"))
run(w2, at("2026-10-28", "16:30"))
check(tg2.sent == [], "a switch missed while down is not posted late")

# telegram off, or only X: nothing
w3 = alerts.Watcher([])
w3.state["sim"] = {"posted": {}}
run(w3, at("2026-10-28", "10:22"))
check(w3.state["sim"]["posted"] == {}, "no Telegram, no post")

# a failed post is retried after the pause, still inside the window
tg4 = Fake(fail=1)
w4 = alerts.Watcher([tg4])
w4.state["sim"] = {"posted": {}}
run(w4, at("2026-10-28", "10:20"))
check(tg4.sent == [] and w4.state["sim"]["pause_until"] == at("2026-10-28", "10:22"), "429: paused for retry_after")
run(w4, at("2026-10-28", "10:21"))
check(tg4.sent == [], "not retried during the pause")
run(w4, at("2026-10-28", "10:23"))
check(len(tg4.sent) == 1, "retried after the pause")

# the old keys are trimmed
w4.state["sim"]["posted"]["2026-10-01:stake"] = at("2026-10-01", "10:20")
run(w4, at("2026-10-28", "16:25"))
check("2026-10-01:stake" not in w4.state["sim"]["posted"] and "2026-10-28:fixed" in w4.state["sim"]["posted"], "keys older than a week are dropped")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

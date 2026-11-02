"""Unit test of the Key Crier (no network): the island's day kept from the relay's readings, one report the next morning
at 07:00 UTC, X only for a day real players moved and at most every second day, X never waiting for Telegram.

Run: python test_island_alerts.py   (needs websockets==15.0.1)
"""
import asyncio
import os
import sys
import tempfile
from datetime import datetime, timezone

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="", X_API_KEY="")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


class Fake(alerts.Outlet):
    def __init__(self, name, fail=False):
        self.name, self.sent, self.fail = name, [], fail

    def enabled(self):
        return True

    def send_text(self, text, *rest):
        if self.fail:
            return False, None, "HTTP 401: Unauthorized"
        self.sent.append((text, rest))
        return True, None, ""


def at(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


alerts.X_PICTURES = False
alerts.Watcher.island_days = lambda self: 5
alerts.Watcher.relay_json = lambda self, path: None

DAY = {"day": "2026-11-03", "v": 0,
       "players": {"campaigns": 12, "finished": 7, "moves": 38, "as": {"hana": 6, "marisol": 4, "tobias": 2},
                   "wins": {"hana": 4, "marisol": 2, "tobias": 1}, "laws": {"night": 5, "reef": 2}, "kinds": {"talk": 15, "law": 9, "lie": 4, "fact": 2, "pact": 3, "deal": 5}},
       "islanders": {"moves": 120, "laws": {"boat": 4, "road": 3}, "kinds": {"talk": 60, "law": 7}}}
QUIET = {"day": "2026-11-04", "v": 1, "players": {"campaigns": 0, "finished": 0, "moves": 0, "as": {}, "wins": {}, "laws": {}, "kinds": {}},
         "islanders": {"moves": 200, "laws": {"lunch": 6}, "kinds": {"talk": 100, "law": 6}}}

r = alerts.island_report("2026-11-03", DAY, 5)
t = alerts.island_text(r)
check(t.startswith(alerts.ISLAND_LINE) and "<b>Yesterday on the island, 3 November</b>" in t, "the report's head")
check("12 campaigns played, 7 of them to the election: Hana won 4, Marisol won 2, Tobias won 1" in t, "campaigns and the elections")
check("38 moves by the players: 15 speeches on the square, 9 laws passed, 5 embassy envelopes" in t, "the moves, the three most used kinds")
check("the law of the day: Night market every Friday, passed 5 times" in t, "the law of the day by its name")
check("most ran as Hana (6 campaigns)" in t, "who most people ran as")
check("the islanders made 120 moves of their own, 7 laws passed" in t, "the islanders' own moves")
check("lasts five days" in t and "real transaction on Tau Testnet Alpha" in t and "no value" in t, "the standing explanation of the cycle")
x = alerts.island_x(r)
check(x.startswith("🐇 The Key Crier: yesterday on the island, 3 November") and "12 campaigns, 7 elections: Hana 4, Marisol 2, Tobias 1. 38 moves" in x
      and "Law of the day: Night market every Friday." in x and x.endswith("#TauNet $AGRS") and alerts.x_len(x) <= 280 and "…" not in x, "the X copy fits")
q = alerts.island_report("2026-11-04", QUIET, 7)
qt = alerts.island_text(q)
check("A quiet day on the island" in qt and "the islanders kept their own politics going: 200 moves of their own, 6 laws passed" in qt
      and "no visitor made a move" in qt and "lasts seven days" in qt, "a day without players: the islanders' day, with the cycle length read from the game")
check(alerts.island_days_from("  const DAYS = 7, MOVES = 3;") == 7 and alerts.island_days_from("nothing") is None, "the campaign length read from game.js")
check(not alerts.island_report("2026-11-05", {"players": {}, "islanders": {}}, 5)["lines"], "an empty day has no lines")

tg, x = Fake("telegram"), Fake("x")
w = alerts.Watcher([tg, x])
w.state.pop("island", None)
w.state.pop("x", None)
asyncio.run(w.maybe_island(at("2026-11-03T23:50:00Z"), DAY))
check(tg.sent == [] and w.state["island"]["days"]["2026-11-03"]["players"]["moves"] == 38, "the day's last reading is kept, nothing posted at night")
asyncio.run(w.maybe_island(at("2026-11-04T06:59:00Z"), QUIET))
check(tg.sent == [], "nothing before 07:00 UTC")
asyncio.run(w.maybe_island(at("2026-11-04T07:00:30Z"), QUIET))
check(len(tg.sent) == 1 and "Yesterday on the island, 3 November" in tg.sent[0][0] and tg.sent[0][1][0]["inline_keyboard"][0][0]["url"].endswith("/rabbit/"),
      "the report of the day before at 07:00, with the button to the island")
check(len(x.sent) == 1 and "3 November" in x.sent[0][0], "on X: real players moved")
asyncio.run(w.maybe_island(at("2026-11-04T08:00:00Z"), QUIET))
check(len(tg.sent) == 1, "once")
asyncio.run(w.maybe_island(at("2026-11-05T07:01:00Z"), dict(DAY, day="2026-11-05")))
check(len(tg.sent) == 2 and "A quiet day on the island, 4 November" in tg.sent[1][0] and len(x.sent) == 1, "the quiet day on Telegram only")
asyncio.run(w.maybe_island(at("2026-11-06T07:01:00Z"), dict(DAY, day="2026-11-06")))
check(len(tg.sent) == 3 and len(x.sent) == 2, "a day with players two days after the last X copy: on X again")
asyncio.run(w.maybe_island(at("2026-11-07T07:01:00Z"), dict(DAY, day="2026-11-07")))
check(len(tg.sent) == 4 and len(x.sent) == 2, "the next day with players: Telegram only, X had the island yesterday")
asyncio.run(w.maybe_island(at("2026-11-08T12:00:00Z"), dict(DAY, day="2026-11-08")))
check(len(tg.sent) == 4, "a morning missed is not posted at noon")

# Telegram failing: X goes alone, the Telegram retry later does not repeat it on X
tg2, x2 = Fake("telegram", fail=True), Fake("x")
w2 = alerts.Watcher([tg2, x2])
w2.state.pop("island", None)
w2.state.pop("x", None)
asyncio.run(w2.maybe_island(at("2026-11-03T23:50:00Z"), DAY))
asyncio.run(w2.maybe_island(at("2026-11-04T07:00:00Z"), QUIET))
check(tg2.sent == [] and len(x2.sent) == 1, "Telegram fails: the X copy goes alone")
tg2.fail = False
asyncio.run(w2.maybe_island(at("2026-11-04T07:06:00Z"), QUIET))
check(len(tg2.sent) == 1 and len(x2.sent) == 1, "Telegram back: its post goes out, X not again")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

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
check("A campaign is the week" not in t and t.rstrip().endswith("<i>Every move is one real transaction on Tau Testnet Alpha, with test AGRS that have no value.</i>"),
      "a weekday says only what is real about it, not the whole cycle")
x = alerts.island_x(r)
check(x.startswith("🐇 The Key Crier: yesterday on the island, 3 November") and "12 campaigns, 7 elections: Hana 4, Marisol 2, Tobias 1. 38 moves" in x
      and "Law of the day: Night market every Friday." in x and x.endswith("#TauNet $AGRS") and alerts.x_len(x) <= 280 and "…" not in x, "the X copy fits")
q = alerts.island_report("2026-11-04", QUIET, 7)
qt = alerts.island_text(q)
check("A quiet day on the island" in qt and "the islanders kept their own politics going: 200 moves of their own, 6 laws passed" in qt
      and "no visitor made a move" in qt and "A campaign is the week" not in qt and "The governor's count" not in qt,
      "a day without players: the islanders' day, no governor's count on a weekday")
LAST = {"id": "2026-W44", "from": "2026-10-26", "to": "2026-11-01", "campaigns": 9, "finished": 6,
        "wins": {"hana": 3, "marisol": 2, "tobias": 1}, "governor": "hana", "laws": ["boat", "reef"]}
m = alerts.island_report("2026-11-01", dict(DAY, last=LAST), 7)
mt = alerts.island_text(m)
check(m["week"] and m["week"]["governor"] == "Hana" and m["week"]["span"] == "26 October to 1 November", "the governor's count read from the relay's last week")
check("A campaign is the week" in mt and "governor's count on Monday 00:00 German time" in mt, "Monday: the standing explanation of the cycle, with the count")
check("<b>The governor's count, 26 October to 1 November</b>" in mt and "• Hana governs the island this week: 3 campaigns won of 6 that reached the election (9 played)" in mt
      and "• the count: Hana 3, Marisol 2, Tobias 1" in mt and "• laws of the island this week: A school boat every morning; Protect the reef: no big ships in the bay" in mt
      and mt.index("governor's count") < mt.index("Yesterday on the island, 1 November"), "Monday's report opens with the count, then Sunday's day")
mx = alerts.island_x(m)
check(mx.startswith("🐇 The Key Crier: the governor's count, 26 October to 1 November") and "Hana governs the island this week" in mx and alerts.x_len(mx) <= 280, "the count on X")
check(alerts.island_report("2026-11-01", dict(DAY, last=dict(LAST, to="2026-10-25")), 7)["week"] is None, "an older verdict (nobody finished this week) is not the count")
check("no law of the island this week" in alerts.island_text(alerts.island_report("2026-11-01", dict(QUIET, last=dict(LAST, laws=[])), 7)), "a week without laws says so")
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
check(len(tg.sent) == 1 and len(x.sent) == 1 and w.state["island"]["posted"]["2026-11-04"] == 0, "a day nobody played gets no Key Crier")
asyncio.run(w.maybe_island(at("2026-11-06T07:01:00Z"), dict(DAY, day="2026-11-06")))
check(len(tg.sent) == 2 and len(x.sent) == 2, "a day with players two days after the last X copy: on X again")
asyncio.run(w.maybe_island(at("2026-11-07T07:01:00Z"), dict(DAY, day="2026-11-07")))
check(len(tg.sent) == 3 and len(x.sent) == 2, "the next day with players: Telegram only, X had the island yesterday")
asyncio.run(w.maybe_island(at("2026-11-08T12:00:00Z"), dict(DAY, day="2026-11-08")))
check(len(tg.sent) == 3, "a morning missed is not posted at noon")

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

# Monday: the week's verdict arrives with the relay's reading after midnight; a quiet Sunday is still reported, with the count, on X too
tg3, x3 = Fake("telegram"), Fake("x")
w3 = alerts.Watcher([tg3, x3])
w3.state.pop("island", None)
w3.state.pop("x", None)
asyncio.run(w3.maybe_island(at("2026-11-01T23:50:00Z"), dict(QUIET, day="2026-11-01")))
asyncio.run(w3.maybe_island(at("2026-11-02T00:10:00Z"), dict(QUIET, day="2026-11-02", last=LAST)))
asyncio.run(w3.maybe_island(at("2026-11-02T07:00:30Z"), dict(QUIET, day="2026-11-02", last=LAST)))
check(len(tg3.sent) == 1 and "The governor's count, 26 October to 1 November" in tg3.sent[0][0] and "A quiet day on the island, 1 November" in tg3.sent[0][0]
      and len(x3.sent) == 1 and "governor's count" in x3.sent[0][0], "Monday: the count opens the report of a quiet Sunday, on X too")
asyncio.run(w3.maybe_island(at("2026-11-03T07:00:30Z"), dict(QUIET, day="2026-11-03", last=LAST)))
check(len(tg3.sent) == 1 and len(x3.sent) == 1, "Tuesday: Monday was quiet, so no report and the count is not repeated")

# the X picture: the island painting the game shows now (index.json "scenes" "island"), never the old repo screenshot
from PIL import Image  # noqa: E402

art = os.path.join(TMP, "art")
os.makedirs(art)
alerts.ISLAND_ART, alerts.ISLAND_PIC_DIR = art, os.path.join(TMP, "island")
check(alerts.island_picture() is None, "no painting: no picture at all (the post goes out with its text alone)")
Image.new("RGB", (3200, 1800), (40, 120, 90)).save(os.path.join(art, "island-30.jpg"))
open(os.path.join(art, "index.json"), "w").write('{"scenes": {"island": "island-30.jpg"}}')
pic = alerts.island_picture(alerts.island_card({"date": "6 November", "campaigns": 1, "moves": 3}), "crier.jpg")
data = alerts.local_picture(pic) if pic else None
check(bool(data) and Image.open(pic).size == (1600, 900) and Image.open(pic).getpixel((1500, 100))[1] > 100,
      "the Key Crier's picture is made from the live painting, 1600x900, a JPEG X takes")
check("{SITE}/assets/shots/rabbit.png" not in open(alerts.__file__).read(), "the old screenshot is not named any more")


class XPic(Fake):
    def send_with_picture(self, text, picture):
        self.sent.append((text, (picture,)))
        return True, None, ""


tg4, x4 = Fake("telegram"), XPic("x")
w4 = alerts.Watcher([tg4, x4])
w4.state.pop("island", None)
w4.state.pop("x", None)
asyncio.run(w4.maybe_island(at("2026-11-06T23:50:00Z"), dict(DAY, day="2026-11-06")))
asyncio.run(w4.maybe_island(at("2026-11-07T07:00:30Z"), dict(DAY, day="2026-11-07")))
check(len(x4.sent) == 1 and x4.sent[0][1][0] == os.path.join(TMP, "island", "crier.jpg"), "X gets the picture made from the painting")
check(os.path.exists(os.path.join(TMP, "island", "today.jpg")), "the public copy for the closer look is made too")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

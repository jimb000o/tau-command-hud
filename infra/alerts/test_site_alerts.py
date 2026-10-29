"""Unit test of the site-update posts (no network): majors from the update log get a post each, inside the posting
hours, capped and spaced; smaller changes wait for one digest; the first run is history; nothing is posted twice.

Run: python test_site_alerts.py   (needs websockets==15.0.1)
"""
import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="", SITE_URL="https://tauhud.com")
# the schedule this test walks through (the defaults are wider: 06-23 UTC, three a day, two hours apart, digests at 12 and 18)
os.environ.update(SITE_POST_HOURS="8-20", SITE_MAJOR_DAILY_CAP="2", SITE_MAJOR_GAP_SECONDS="10800", SITE_DIGEST_HOURS="17", SITE_CATCHUP_AT="99")
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


alerts.Watcher.fetch_updates = lambda self: None  # no network in the test: entries are handed in


def run(w, t, entries=None):
    asyncio.run(w.maybe_site(t, entries))


def small(on, tag, text):
    return {"tag": tag, "on": on, "html": text}


def major(on, tag, text, mid, **m):
    return {"tag": tag, "on": on, "html": text, "major": {"id": mid, **m}}


old = [small("2026-10-20", "v17.1", "Chain core: an old change."), major("2026-10-20", "Story", "New page: an old story.", "story", title="Story")]
log = old + [small("2026-10-28", "Stats", "Stats: the chart is calmer. More text here."),
             major("2026-10-28", "Newspaper", "New page: <a href=\"gazette/\">The Daily Consensus</a> &amp; more. Second. Third.", "gazette",
                   title="The Daily Consensus", link="/gazette/"),
             major("2026-10-28", "Missions", "Missions: six tasks. Second sentence.", "missions", title="Missions")]

# the texts
m = alerts.major_item(log[3])
check(m["text"] == "New page: The Daily Consensus & more. Second." and m["link"] == "https://tauhud.com/gazette/", "major: text from the entry's first two sentences, link made absolute")
t = alerts.major_text(m)
check(t.startswith("✨ <b>TAU HUD · new on the site</b>") and "not news from the testnet" in t, "first line marks a site update, last says it is not chain news")
check(alerts.major_buttons(m)["inline_keyboard"][0][0]["url"] == "https://tauhud.com/gazette/", "button opens the page")
d = alerts.digest_item(log[2])
check(d == {"area": "Stats", "line": "The chart is calmer.", "on": "2026-10-28"}, "digest line: area once, first sentence")
check(alerts.digest_item(log[0])["area"] == "HUD", "a version tag counts as the HUD")
many = [{"area": "HUD", "line": f"Change {i}.", "on": "2026-10-2" + str(i % 9)} for i in range(11)]
dt = alerts.digest_text(many)
check(dt.startswith("🛠 <b>TAU HUD · smaller site updates</b>") and "11 smaller changes to Tau HUD since 2026-10-20" in dt, "digest headline counts and dates")
check(dt.count("• ") == 8 and "…and 3 more changes" in dt, "eight lines, the rest counted")
check(len(alerts.digest_text([{"area": "HUD", "line": "x" * 900, "on": "2026-10-28"}] * 8)) <= 4096, "a long digest stays under Telegram's limit")

# first run: history, except recent majors
tg = Fake()
w = alerts.Watcher([tg])
run(w, at("2026-10-28", "22:05"), log)
st = w.state["site"]
check([x["key"] for x in st["majors"]] == ["major:gazette", "major:missions"], "first run queues only the majors of the last days")
check(st["pending"] == [], "first run: smaller changes are history")
check(tg.sent == [], "nothing posted at night")

# posting hours, cap and gap
run(w, at("2026-10-29", "08:00"))
check(len(tg.sent) == 1 and "The Daily Consensus" in tg.sent[0][0], "08:00 UTC: the first major, oldest first")
run(w, at("2026-10-29", "09:00"))
check(len(tg.sent) == 1, "the next one waits for the gap")
run(w, at("2026-10-29", "11:00"))
check(len(tg.sent) == 2 and "Missions" in tg.sent[1][0], "three hours later: the second")
log2 = log + [major("2026-10-29", "Vote", "New page: vote.", "vote", title="Vote"),
              small("2026-10-29", "v17.48", "Chain core: one."), small("2026-10-29", "Stats", "Stats: two.")]
run(w, at("2026-10-29", "14:30"), log2)
check(len(tg.sent) == 2, "daily cap of two")
check(len(st["pending"]) == 2, "new smaller changes wait for the digest")
run(w, at("2026-10-29", "17:05"))
check(len(tg.sent) == 2, "two smaller changes are not enough for a digest")
log3 = log2 + [small("2026-10-29", "Press", "Press: three.")]
run(w, at("2026-10-29", "20:30"), log3)
check(len(tg.sent) == 2, "nothing after the posting hours")
run(w, at("2026-10-30", "08:00"))
check(len(tg.sent) == 3 and "Vote" in tg.sent[2][0], "next day: the capped major")
run(w, at("2026-10-30", "17:00"))
check(len(tg.sent) == 4 and "3 smaller changes" in tg.sent[3][0] and "<b>Press</b>: Three." in tg.sent[3][0], "17:00 UTC: one digest of the three")
run(w, at("2026-10-30", "18:00"), log3)
check(len(tg.sent) == 4 and st["pending"] == [] and st["majors"] == [], "never twice")

# a single small change is posted after a week of waiting
log4 = log3 + [small("2026-10-30", "Stats", "Stats: lonely.")]
run(w, at("2026-10-30", "19:00"), log4)
run(w, at("2026-11-06", "17:00"))
check(len(tg.sent) == 4, "one change waits")
run(w, at("2026-11-07", "17:00"))
check(len(tg.sent) == 5 and "1 smaller change " in tg.sent[4][0], "after a week it goes out alone")

# a failed post pauses and is retried
tg2 = Fake(fail=1)
w2 = alerts.Watcher([tg2])
w2.state.pop("site", None)
run(w2, at("2026-10-28", "12:00"), log)
check(tg2.sent == [] and w2.state["site"]["pause_until"] == at("2026-10-28", "12:02"), "429: paused")
run(w2, at("2026-10-28", "12:03"))
check(len(tg2.sent) == 1 and len(w2.state["site"]["majors"]) == 1, "retried after the pause, the queue moves on")

# no Telegram: queued, not lost
w3 = alerts.Watcher([])
w3.state.pop("site", None)
run(w3, at("2026-10-28", "12:00"), log)
check(len(w3.state["site"]["majors"]) == 2, "without Telegram the majors stay queued")

# a major marked skip is never posted, and leaves the queue if it was already waiting
w5 = alerts.Watcher([tg5 := Fake()])
w5.state.pop("site", None)
run(w5, at("2026-10-28", "22:00"), log)
check([m["key"] for m in w5.state["site"]["majors"]] == ["major:gazette", "major:missions"], "both queued before the mark")
marked = [dict(e, major=dict(e["major"], skip="posted by hand")) if e.get("major", {}).get("id") == "gazette" else e for e in log]
run(w5, at("2026-10-28", "23:00"), marked)
run(w5, at("2026-10-29", "08:00"))
check(len(tg5.sent) == 1 and "Missions" in tg5.sent[0][0], "the skipped major leaves the queue, the next one goes out")
w6 = alerts.Watcher([])
w6.state.pop("site", None)
run(w6, at("2026-10-28", "22:00"), marked)
check([m["key"] for m in w6.state["site"]["majors"]] == ["major:missions"], "a major marked skip is never queued")

# a backlog of majors: one catch-up post at the start of the posting hours, then the daily rhythm
alerts.SITE_CATCHUP_AT = 4
tg9 = Fake()
w9 = alerts.Watcher([tg9])
w9.state.pop("site", None)
many = [major("2026-10-28", "X", f"New page {i}.", f"m{i}", title=f"New: page {i}", link=f"/p{i}/") for i in range(5)]
run(w9, at("2026-10-28", "22:00"), many)
check(tg9.sent == [] and len(w9.state["site"]["majors"]) == 5, "queued at night")
run(w9, at("2026-10-29", "08:00"))
check(len(tg9.sent) == 1 and "5 new pages and features on Tau HUD since 2026-10-28" in tg9.sent[0][0], "one catch-up post with all five")
check('<a href="https://tauhud.com/p0/">Page 0</a>' in tg9.sent[0][0] and w9.state["site"]["majors"] == [], "a line and a link each, the queue is empty")
run(w9, at("2026-10-29", "08:00"), many + [major("2026-10-29", "Y", "New page 9.", "m9", title="New: nine")])
run(w9, at("2026-10-29", "14:00"))
check(len(tg9.sent) == 1, "the day's quota is used by the catch-up post")
run(w9, at("2026-10-30", "08:00"))
check(len(tg9.sent) == 2 and "nine" in tg9.sent[1][0] and "TAU HUD · new on the site" in tg9.sent[1][0], "next day single posts again")
alerts.SITE_CATCHUP_AT = 99

# a backfilled entry is logged, never posted
w7 = alerts.Watcher([])
w7.state.pop("site", None)
run(w7, at("2026-10-29", "09:00"), [])
run(w7, at("2026-10-29", "09:30"), [dict(small("2026-10-26", "Relay", "Relay: an old change."), backfill=True),
                                    dict(major("2026-10-29", "Node", "New: old.", "old-major", title="Old"), backfill=True)])
check(w7.state["site"]["pending"] == [] and w7.state["site"]["majors"] == [], "backfilled entries are never posted")

# two digest slots a day
os.environ["SITE_DIGEST_HOURS"] = "12,18"
import importlib  # noqa: E402
alerts2 = importlib.reload(alerts)
alerts2.Watcher.fetch_updates = lambda self: None
tg8 = Fake()
w8 = alerts2.Watcher([tg8])
w8.state["site"] = {"seen": {}, "majors": [], "primed": True, "pending": [{"key": str(i), "at": at("2026-10-29", "09:00"), "area": "HUD", "line": "x.", "on": "2026-10-29"} for i in range(3)]}
asyncio.run(w8.maybe_site(at("2026-10-29", "11:59")))
asyncio.run(w8.maybe_site(at("2026-10-29", "12:01")))
check(len(tg8.sent) == 1, "the 12:00 UTC digest")
w8.state["site"]["pending"] = [{"key": str(i), "at": at("2026-10-29", "13:00"), "area": "HUD", "line": "y.", "on": "2026-10-29"} for i in range(3)]
asyncio.run(w8.maybe_site(at("2026-10-29", "17:00")))
asyncio.run(w8.maybe_site(at("2026-10-29", "18:05")))
check(len(tg8.sent) == 2, "and the 18:00 UTC digest the same day")

# the real log parses and its majors are complete
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "updates.json")) as f:
    real = json.load(f)
ms = [e for e in real if "major" in e]
check(ms and all(e["major"].get("id") and e["major"].get("title") for e in ms), "every major in assets/updates.json has an id and a title")
check(len({e["major"]["id"] for e in ms}) == len(ms), "major ids are unique")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

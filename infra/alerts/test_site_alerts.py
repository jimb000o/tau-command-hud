"""Unit test of the site-update posts (no network): majors from the update log get a post each, inside the posting
fixed times, several waiting go together in one post; smaller changes wait for one digest in a slot with no major; the
first run is history; nothing is posted twice; nothing at night.

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
os.environ.update(SITE_SLOTS="8,12,16", SITE_SLOT_HOURS="4", X_API_KEY="")
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
check("Open it on tauhud.com</a>" in t, "the link names tauhud.com for a page of its own")
ext = alerts.major_item(major("2026-10-29", "Agorzilla", "New: Agorzilla.", "agorzilla", title="New: Agorzilla", link="https://agorzilla.com", x=False))
check("Open it on agorzilla.com</a>" in alerts.major_text(ext) and ext["x"] is False, "another site is named as itself; \"x\": false is kept")
check("x" not in m, "a major goes to X unless the log says otherwise")
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

# fixed times: 08:00, 12:00 and 16:00 UTC; a slot is used once and is over four hours after its time
run(w, at("2026-10-29", "07:59"))
check(tg.sent == [], "nothing before the first slot")
run(w, at("2026-10-29", "08:00"))
check(len(tg.sent) == 1 and "2 new pages and features on Tau HUD since 2026-10-28" in tg.sent[0][0]
      and "The Daily Consensus" in tg.sent[0][0] and "Missions" in tg.sent[0][0], "08:00 UTC: both waiting majors in one post")
check(st["majors"] == [], "the queue is empty")
log2 = log + [major("2026-10-29", "Vote", "New page: vote.", "vote", title="Vote"),
              small("2026-10-29", "v17.48", "Chain core: one."), small("2026-10-29", "Stats", "Stats: two.")]
run(w, at("2026-10-29", "09:00"), log2)
check(len(tg.sent) == 1, "the 08:00 slot is used: the next major waits")
run(w, at("2026-10-29", "12:05"))
check(len(tg.sent) == 2 and "Vote" in tg.sent[1][0] and "TAU HUD · new on the site" in tg.sent[1][0], "12:00: one major, its own post")
check(len(st["pending"]) == 2, "smaller changes wait for the digest")
run(w, at("2026-10-29", "16:05"))
check(len(tg.sent) == 2, "two smaller changes are not enough for a digest")
log3 = log2 + [small("2026-10-29", "Press", "Press: three.")]
run(w, at("2026-10-29", "20:30"), log3)
check(len(tg.sent) == 2, "the 16:00 slot is over by 20:00: nothing at night")
run(w, at("2026-10-30", "03:00"))
check(len(tg.sent) == 2, "still nothing at night")
run(w, at("2026-10-30", "08:01"))
check(len(tg.sent) == 3 and "3 smaller changes" in tg.sent[2][0] and "<b>Press</b>: Three." in tg.sent[2][0], "08:00: one digest of the three")
run(w, at("2026-10-30", "12:00"), log3)
check(len(tg.sent) == 3 and st["pending"] == [] and st["majors"] == [], "never twice")
log3b = log3 + [major("2026-10-30", "Late", "New page: late.", "late", title="Late")]
run(w, at("2026-10-30", "13:30"), log3b)
check(len(tg.sent) == 4 and "Late" in tg.sent[3][0], "a slot no one used yet: a new major goes out as soon as it is seen")

# a single small change is posted after a week of waiting
log4 = log3b + [small("2026-10-30", "Stats", "Stats: lonely.")]
run(w, at("2026-10-30", "14:00"), log4)
run(w, at("2026-11-06", "08:00"))
check(len(tg.sent) == 4, "one change waits")
run(w, at("2026-11-06", "16:00"))
check(len(tg.sent) == 5 and "1 smaller change " in tg.sent[4][0], "after a week it goes out alone")

# a failed post pauses and is retried
tg2 = Fake(fail=1)
w2 = alerts.Watcher([tg2])
w2.state.pop("site", None)
run(w2, at("2026-10-28", "12:00"), log)
check(tg2.sent == [] and w2.state["site"]["pause_until"] == at("2026-10-28", "12:02"), "429: paused")
run(w2, at("2026-10-28", "12:03"))
check(len(tg2.sent) == 1 and w2.state["site"]["majors"] == [], "retried after the pause, the queue moves on")

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
check(len(tg5.sent) == 1 and "Missions" in tg5.sent[0][0] and "Daily Consensus" not in tg5.sent[0][0],
      "the skipped major leaves the queue, the next one goes out")
w6 = alerts.Watcher([])
w6.state.pop("site", None)
run(w6, at("2026-10-28", "22:00"), marked)
check([m["key"] for m in w6.state["site"]["majors"]] == ["major:missions"], "a major marked skip is never queued")

# a backlog of majors: one post at the next slot with all of them, never a day's quota used up
tg9 = Fake()
w9 = alerts.Watcher([tg9])
w9.state.pop("site", None)
many = [major("2026-10-28", "X", f"New page {i}.", f"m{i}", title=f"New: page {i}", link=f"/p{i}/") for i in range(5)]
run(w9, at("2026-10-28", "22:00"), many)
check(tg9.sent == [] and len(w9.state["site"]["majors"]) == 5, "queued at night")
run(w9, at("2026-10-29", "08:00"))
check(len(tg9.sent) == 1 and "5 new pages and features on Tau HUD since 2026-10-28" in tg9.sent[0][0], "one post with all five")
check('<a href="https://tauhud.com/p0/">Page 0</a>' in tg9.sent[0][0] and w9.state["site"]["majors"] == [], "a line and a link each, the queue is empty")
run(w9, at("2026-10-29", "08:30"), many + [major("2026-10-29", "Y", "New page 9.", "m9", title="New: nine")])
run(w9, at("2026-10-29", "12:00"))
check(len(tg9.sent) == 2 and "nine" in tg9.sent[1][0] and "TAU HUD · new on the site" in tg9.sent[1][0], "the same day's next slot: the next one")

# X gets the same: one post per slot, the bundle as one post, the digest only with room to spare
class FakeX(alerts.Outlet):
    name = "x"

    def __init__(self):
        self.sent = []

    def enabled(self):
        return True

    def send_text(self, text, media_id=None):
        self.sent.append(text)
        return True, None, ""


tgx, xx = Fake(), FakeX()
wx = alerts.Watcher([tgx, xx])
wx.state.pop("site", None)
wx.state.pop("x", None)
alerts.X_PICTURES = False
run(wx, at("2026-10-28", "22:00"), log)
run(wx, at("2026-10-29", "08:00"))
check(len(xx.sent) == 1 and xx.sent[0].startswith("2 new pages and features on Tau HUD") and "• The Daily Consensus" in xx.sent[0]
      and "http" not in xx.sent[0], "X: the two together, by name, no link")
skipx = log + [major("2026-10-29", "A", "New: a.", "a", title="New: Alpha", x=False), major("2026-10-29", "B", "New: b.", "b", title="New: Beta")]
run(wx, at("2026-10-29", "09:00"), skipx)
run(wx, at("2026-10-29", "12:00"))
check(len(tgx.sent) == 2 and "Alpha" in tgx.sent[1][0] and len(xx.sent) == 2 and "Alpha" not in xx.sent[1]
      and xx.sent[1].startswith("New on Tau HUD: Beta"), "X: a major marked \"x\": false stays off X, the other gets its own post")
wx.state["site"]["pending"] = [{"key": str(i), "at": at("2026-10-29", "09:00"), "area": "HUD", "line": f"Change {i}.", "on": "2026-10-29"}
                               for i in range(3)]
wx.state["x"]["today"] = alerts.X_DAILY_CAP - alerts.X_RESERVE
run(wx, at("2026-10-29", "16:00"))
check(len(tgx.sent) == 3 and len(xx.sent) == 2, "X: the digest leaves the day's last posts for the real chain")
wx.state["site"]["pending"] = wx.state["site"]["pending"] or [{"key": "z" + str(i), "at": at("2026-10-30", "07:00"), "area": "Stats",
                                                               "line": "Calmer.", "on": "2026-10-30"} for i in range(3)]
wx.state["x"]["today"] = 0
run(wx, at("2026-10-30", "08:00"))
check(len(xx.sent) == 3 and xx.sent[2].startswith("🛠 3 smaller changes to Tau HUD") and xx.sent[2].endswith("#TauNet $AGRS"),
      "X: the digest, a line each, with room")

# a round-up: one post with a line and a link per change; the majors it covers and the digest so far are not posted
class FakePic(Fake):
    def send_text(self, text, buttons=None, picture=None):
        self.sent.append((text, buttons, picture))
        return True, None, ""


tgr = FakePic()
wr = alerts.Watcher([tgr])
wr.state.pop("site", None)
run(wr, at("2026-10-29", "05:00"), [])
covered = [major("2026-10-29", "HUD", "Troll box: a chat.", "trollbox", title="New: Troll box"),
           major("2026-10-29", "Japanese", "Japanese.", "japanese", title="New: Japanese"), small("2026-10-29", "HUD", "HUD: he walks.")]
run(wr, at("2026-10-29", "05:10"), covered)
check(len(wr.state["site"]["majors"]) == 2 and len(wr.state["site"]["pending"]) == 1, "two majors and a small change wait")
ru = major("2026-10-30", "Round-up", "Round-up.", "roundup-1", title="What's new on Tau HUD", link="/",
           image="/assets/shots/roundup-1.png", covers=["trollbox", "japanese", "never-seen"],
           lines=[{"label": "Troll box", "text": "a live chat on the HUD.", "link": "/", "x": "Troll box, a live chat"},
                  {"label": "Agorzilla", "text": "one creature everyone feeds.", "link": "https://agorzilla.com"}])
ru["major"]["text"] = "A busy few days."
run(wr, at("2026-10-29", "05:20"), covered + [ru])
check([m["key"] for m in wr.state["site"]["majors"]] == ["major:roundup-1"] and wr.state["site"]["pending"] == [],
      "the round-up replaces the majors it covers and the digest so far")
run(wr, at("2026-10-29", "08:00"))
t, _, pic = tgr.sent[0]
check(len(tgr.sent) == 1 and '• <a href="https://tauhud.com/">Troll box</a>: a live chat on the HUD.' in t
      and '<a href="https://agorzilla.com">Agorzilla</a>' in t and "A busy few days." in t, "one post, a line and a link per change")
check(pic == "https://tauhud.com/assets/shots/roundup-1.png", "its screenshot shows above the text")
x = alerts.major_x(alerts.major_item(ru))
check(x.startswith("What's new on Tau HUD\n\n• Troll box, a live chat\n• Agorzilla") and "http" not in x and x.endswith("#TauNet $AGRS"),
      "X: the title and a short line per change, no links")
run(wr, at("2026-10-29", "12:00"), covered + [ru])
check(len(tgr.sent) == 1, "the covered majors never come back")

w7 = alerts.Watcher([])
w7.state.pop("site", None)
run(w7, at("2026-10-29", "09:00"), [])
run(w7, at("2026-10-29", "09:30"), [dict(small("2026-10-26", "Relay", "Relay: an old change."), backfill=True),
                                    dict(major("2026-10-29", "Node", "New: old.", "old-major", title="Old"), backfill=True)])
check(w7.state["site"]["pending"] == [] and w7.state["site"]["majors"] == [], "backfilled entries are never posted")

# the real log parses and its majors are complete
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "updates.json")) as f:
    real = json.load(f)
ms = [e for e in real if "major" in e]
check(ms and all(e["major"].get("id") and e["major"].get("title") for e in ms), "every major in assets/updates.json has an id and a title")
check(len({e["major"]["id"] for e in ms}) == len(ms), "major ids are unique")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

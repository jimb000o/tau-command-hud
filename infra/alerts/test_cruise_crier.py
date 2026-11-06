"""Unit test of the cruise ships' automatic announcements and reports (no network): the texts written from the
timetable and the last call (MS Dry Run of 4 November 2026: 122 accepted, 8 timeouts logged as refusals by the old
rule, left after 34 minutes), the announcement window, one post per call (also after a crash or a hand-posted one),
the hand-written file only on its own date, one report per visit to the owner's chat, nothing while ships are off.

Run: python test_cruise_crier.py
"""
import json
import os
import re
import sys
import tempfile

TMP = tempfile.mkdtemp()
ART = os.path.join(TMP, "art")
os.makedirs(ART)
from PIL import Image  # noqa: E402
Image.new("RGB", (1600, 900), (40, 120, 160)).save(os.path.join(ART, "isle.jpg"))
json.dump({"scenes": {"island": "isle.jpg"}}, open(os.path.join(ART, "index.json"), "w"))
SHIPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "rabbit", "art", "ships")
os.environ.update(BLOG_ART=ART, BLOG_SHIPS=SHIPS, PUBLIC_DIR=TMP, BLOG_STATE=os.path.join(TMP, "blog.json"), NEWS_AI_KEY="",
                  CHAT_AI_KEY="", TELEGRAM_BOT_TOKEN="", X_API_KEY="", CRUISE_CRIER="true", CRUISE_ANNOUNCE_MINUTES="150")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog  # noqa: E402
import cruise_crier as cc  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T0 = 1793804400   # Wednesday 4 November 2026, 16:00 German time
V = "2026-11-04-dryrun"
log = [{"t": T0, "visit": V, "ship": "dryrun", "kind": "landed", "verdict": "calm", "plan": 247, "trial": ["book"]}]
for i in range(122):
    log.append({"t": T0 + 10 + i * 16, "visit": V, "kind": "pay", "ok": True, "verdict": "calm", "height": 5500 + i, "ms": 900})
for i in range(8):
    log.append({"t": T0 + 700 + i * 160, "visit": V, "kind": "pay", "ok": False, "err": None, "verdict": "calm"})
log.append({"t": T0 + 2041, "visit": V, "kind": "left", "verdict": "refused", "note": "the node refused 5 of the last 20 passenger transactions"})
summary = {"id": V, "ship": "dryrun", "name": "MS Dry Run", "t0": T0, "landed": True, "end": T0 + 2041,
           "sent": {"pay": 122}, "refused": {"pay": 8}, "skipped": 117, "half": 0, "passengers": 40}
log.append({"t": T0 + 5400, "visit": V, "kind": "visit over", "summary": summary})
NEXT_DRY = T0 + 7 * 86400                    # Wednesday 11 November, 16:00
QUEEN = 1794056400                           # Saturday 7 November, 14:00 German time
check(blog.clock(QUEEN) == "14:00" and blog.local(QUEEN).weekday() == 5, "Saturday 7 November 14:00 German time")

# ---------- the texts ----------
f = blog.facts_of(log, [])
tg, card, x = cc.last_lines(f)
check("accepted 122" in tg and "refused none" in tg and "8 got no answer from our node in time" in tg, "last call: 122 accepted, none refused, 8 timeouts")
check("left after 34 minutes" in tg and "no longer" in tg, "left after 34 minutes, the old brake named as ours")
check(card == "- Last call: 122 accepted, none refused", "card point")
t = cc.texts("dryrun", NEXT_DRY, f)
check(t["date"] == "2026-11-11" and t["card"][0] == "MS Dry Run · today 16:00 German time", "card title with the day's time")
check("from 15:30" in t["telegram"].lower() and "https://node.tauhud.com/cruise/log" in t["telegram"] and "made up" in t["telegram"], "Telegram: horizon time, logbook, honest note")
check("http" not in t["x"] and blog.re.search(r"\.com\b", t["x"]) is None, "X: no link")
import alerts  # noqa: E402
check(alerts.x_len(t["x"]) <= 280 and "made up" in t["x"] and "Wed 11 Nov" in t["x"], "X: within 280, honest, dated (X refuses a repeated text)")
for ship, t0, last in (("dryrun", NEXT_DRY, f), ("queen", QUEEN, None), ("queen", QUEEN + 7 * 86400, f)):
    tt = cc.texts(ship, t0, last)
    words = tt["telegram"] + tt["x"] + " ".join(tt["card"])
    check(not blog.HYPE.search(words) and not blog.BLAME.search(words), f"{ship}: no hype or blame words")
    check(alerts.x_len(tt["x"]) <= 280 and "#TauNet" in tt["x"], f"{ship}: X {alerts.x_len(tt['x'])} of 280 with the tag")
    nums = set(re.findall(r"\d+", re.sub(r"https?://\S+", "", words)))
    allowed = {"12", "90", "40", "120", "122", "8", "34", "11", "4", "7", "14", "13", "15", "16", "30", "00", "2026"}
    check(nums <= allowed, f"{ship}: every number is the timetable's or the logbook's ({sorted(nums - allowed)})")
q = cc.texts("queen", QUEEN, None)
check("first call" in q["telegram"] and q["card"][-2] == "- Every transaction logged with the node's answer, open to all", "first call: said so, no numbers")
check(cc.last_call("dryrun", "2026-11-11-dryrun", ["2026-11-07-queen", V], lambda v: log if v == V else [], []) is not None
      and cc.last_call("dryrun", V, [V], lambda v: log, []) is None, "last call: the same ship's visit before this one")
picture = cc.picture(t, os.path.join(TMP, "p.jpg"))
check(Image.open(picture).size == (1600, 900), "the picture is made (1600x900)")

# ---------- the window ----------
cruise = {"next": {"ship": "queen", "name": "Queen Mempool", "t0": QUEEN}}
check(cc.due_call(cruise, QUEEN - 151 * 60) is None, "not before 11:30")
check(cc.due_call(cruise, QUEEN - 150 * 60) == ("queen", QUEEN), "due at 11:30")
check(cc.due_call(cruise, QUEEN - 29 * 60) is None, "not once she is on the horizon")
check(cc.due_call({"enabled": False}, QUEEN - 60 * 60) is None, "ships switched off: no next call, nothing announced")

# ---------- one post per call ----------
posted, told = [], []
cc.post = lambda tx, pic: posted.append(tx) or ["telegram: posted", "x: posted"]
cc.tell = lambda text: told.append(text) or (True, "")
hand = {"date": "2026-11-07", "telegram": "hand", "x": "hand x", "card": ["a", "b"], "ship": "liner"}
cc.hand_written = lambda ship, t0: {**hand, "written": "by hand"} if blog.local(t0).date().isoformat() == hand["date"] else None
blog.get = lambda path: cruise if path == "/cruise" else ({"incidents": []} if "incidents" in path else {"entries": log, "visits": [V]})
st = cc.state()
check(cc.announce(QUEEN - 2 * 3600, cruise, st) == "2026-11-07-queen" and posted[-1]["telegram"] == "hand", "Saturday 7.11: the hand-written texts go out")
check(cc.announce(QUEEN - 3600, cruise, cc.state()) is None and len(posted) == 1, "and only once")
nxt = {"next": {"ship": "queen", "name": "Queen Mempool", "t0": QUEEN + 7 * 86400}}
cc.announce(QUEEN + 7 * 86400 - 2 * 3600, nxt, cc.state())
check(len(posted) == 2 and posted[-1]["written"] == "auto" and posted[-1]["date"] == "2026-11-14", "a week later: written anew, by itself")
st = cc.state()
st["announced"].pop("2026-11-14-queen")
st["announced"]["2026-11-14-queen"] = {"result": "posting"}
cc.save(st)
check(cc.announce(QUEEN + 7 * 86400 - 3600, nxt, cc.state()) is None, "a crash while posting: never a second post")

# up post … send by hand marks the day
cc.dt = __import__("datetime")
old = cc.dt.datetime


class Fixed(old):
    @classmethod
    def now(cls, tz=None):
        return old.fromtimestamp(NEXT_DRY - 4 * 3600, tz)


cc.dt.datetime = Fixed
cc.main(["mark", "cruise-dry-run"])
cc.dt.datetime = old
dcall = {"next": {"ship": "dryrun", "name": "MS Dry Run", "t0": NEXT_DRY}}
check(cc.announce(NEXT_DRY - 2 * 3600, dcall, cc.state()) is None and len(posted) == 2, "posted by hand that day: not posted again")

# ---------- one report per visit ----------
check(cc.report(T0 + 5400 + 600, cc.state()) == V and len(told) == 1, "the visit over: reported once")
check("MS Dry Run" in told[0] and "122 transactions accepted" in told[0] and "up.sh cruise 2026-11-04-dryrun" in told[0], "report: numbers and the full command")
check(os.path.exists(os.path.join(cc.REPORTS, V + ".json")), "report kept in /state/cruise-reports")
check(cc.report(T0 + 5400 + 1200, cc.state()) is None and len(told) == 1, "not twice")
st = cc.state(); st["reported"] = {}; cc.save(st)
check(cc.report(T0 + 5 * 86400, cc.state()) is None and not told[1:], "first run days later: an old visit is not told")
cc.tell_draft("2026-11-04-dryrun-learnings", "https://tauhud.com/blog/?draft=x")
cc.tell_draft("2026-11-04-dryrun-learnings", "https://tauhud.com/blog/?draft=x")
check(len(told) == 2 and 'up.sh blog publish 2026-11-04-dryrun-learnings"' in told[1], "draft told once with the publish line")
check(any("announced by itself" in s for s in cc.status_lines(QUEEN - 5 * 3600)), "up block names the next announcement")

print("all ok" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)

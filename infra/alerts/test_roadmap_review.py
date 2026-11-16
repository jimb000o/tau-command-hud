"""Unit test of roadmap_review.py (no network): the weekly Road to mainnet check reads the real page, flags an item
that still calls a closed issue open, a state change since last week, a restart the page does not name and our open
issue the page misses, sends one note a week (Monday after 10:00 German time), also when all is well, and names a
waiting fix pull request.

Run: python test_roadmap_review.py
"""
import os
import sys
import tempfile
from datetime import datetime, timezone

TMP = tempfile.mkdtemp()
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["ROADMAP_PAGE"] = os.path.join(HERE, "..", "..", "roadmap", "index.html")
os.environ["ROADMAP_REVIEW_PATH"] = os.path.join(TMP, "devpulse", "roadmap-review.json")
os.environ["FINDINGS_PAGE"] = os.path.join(HERE, "..", "..", "findings", "index.html")
sys.path.insert(0, HERE)
import roadmap_review as rr  # noqa: E402
import roadmap_watch as rw  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


def utc(s: str) -> float:
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()


with open(rw.PAGE, encoding="utf-8") as f:
    page = f.read()
its = rw.items(page)
nums = sorted({n for it in its for n in set(it["refs"]) | set(it["links"])})
states = {str(n): {"state": "open", "pr": False} for n in nums}

# ---------------- the checks, on the real page ----------------
r = rr.check(page, set(), states, states, [], [], [], [], utc("2026-11-23 09:30"))
check(not r["flags"] and not r["missing"], "nothing changed: no flag")
check("All" in rr.note(r) and "Nothing to do" in rr.note(r), "... and the note says so")

fake = page.replace("The testnet restarted on that code.", "The testnet restarted on that code. The issue is still open.", 1)
st2 = dict(states, **{"85": {"state": "closed", "pr": False}})
r = rr.check(fake, set(), st2, states, [], [], [], [], utc("2026-11-23 09:30"))
check("rule-places" in r["flags"] and any("still open" in w for w in r["flags"]["rule-places"]), "an item calls a closed issue still open")
check(any("#85 is now closed" in w for w in r["flags"]["rule-places"]), "... and #85 changed state since last week")

r = rr.check(page, set(), states, states, [{"n": 999, "title": "a new report"}, {"n": 108, "title": "known"}],
             [utc("2026-11-21 08:00"), utc("2026-11-14 12:00")], [], [], utc("2026-11-23 09:30"))
check([m["n"] for m in r["missing"]] == [999], "our open issue the page does not name, not one it names")
check("upgrades" in r["flags"] and "21 November" in r["flags"]["upgrades"][0], "a restart this week the page does not name")
check(len(r["restarts"]) == 1, "... a restart older than a week is left out")

r = rr.check(page, set(), states, states, [], [utc("2026-11-14 12:00")], [], [], utc("2026-11-16 09:30"))
check("upgrades" not in r["flags"], "a restart the page already names (14 November)")

r = rr.check(page, set(), states, states, [{"n": 999, "title": "x"}], [], [{"ts": utc("2026-11-20 10:00"), "headline": {"en": "Faster sync"}}],
             [{"n": 900, "url": "https://github.com/x/y/pull/900"}], utc("2026-11-23 09:30"))
n = rr.note(r)
check("Faster sync" in n and "pull/900" in n and "#999" in n, "the note lists IDNI's week, our missing issue and the fix to merge")

# ---------------- once a week ----------------
check(not rr.due(utc("2026-11-23 08:30"), {}), "Monday 09:30 German time: not yet")
check(rr.due(utc("2026-11-23 09:30"), {}), "Monday 10:30 German time: due")
check(not rr.due(utc("2026-11-24 09:30"), {}), "Tuesday: not due")
check(not rr.due(utc("2026-11-23 12:00"), {"last": {"at": utc("2026-11-23 09:30")}}), "only once that Monday")

told = []


def get(url):
    if "creator=" in url:
        return [{"number": 777, "title": "our new one"}, {"number": 778, "title": "a pr", "pull_request": {}}]
    if "/pulls" in url:
        return [{"number": 5, "state": "open", "html_url": "https://github.com/x/y/pull/5", "title": "Road to mainnet: weekly fixes"},
                {"number": 6, "state": "open", "html_url": "https://github.com/x/y/pull/6", "title": "Something else"},
                {"number": 4, "state": "closed", "merged_at": "2026-11-23T07:50:00Z", "html_url": "https://github.com/x/y/pull/4", "title": "Road to mainnet: older fix"},
                {"number": 3, "state": "closed", "merged_at": "2026-11-10T07:50:00Z", "html_url": "https://github.com/x/y/pull/3", "title": "Road to mainnet: last week"}]
    return []


out = rr.step(utc("2026-11-22 09:30"), states, [], [], get=get, tell=lambda t: told.append(t) or (True, ""))
check(not told and out is None, "Sunday: no check, nothing to show yet")
out = rr.step(utc("2026-11-23 09:30"), states, [], [], get=get, tell=lambda t: told.append(t) or (True, ""))
check("pull/4" in told[0] and "Already merged" in told[0] and "pull/3" not in told[0], "... and this morning's merged fix, not last week's")
check(len(told) == 1 and "#777" in told[0] and "#778" not in told[0] and "pull/5" in told[0] and "pull/6" not in told[0],
      "Monday: one note, our open issue (not a pull request) and the waiting fix")
check(out and out["at"] == int(utc("2026-11-23 09:30")) and out["flag"] == [], "the page gets the date of the check")
rr.step(utc("2026-11-23 15:30"), states, [], [], get=get, tell=lambda t: told.append(t) or (True, ""))
check(len(told) == 1, "no second note the same day")

st = rr.load()
st["last"]["flags"] = {"sync": ["x"]}
check(rr.public(st, page)["flag"] == ["sync"], "a flag shows while the page is unchanged")
check(rr.public(st, page + " ")["flag"] == [], "... and goes once the page's text changes")

# ---------------- findings but no fix pull request yet: the note waits for one ----------------
os.remove(rr.STATE)
told.clear()
nopr = lambda url: [{"number": 777, "title": "our new one"}] if "creator=" in url else []
rr.step(utc("2026-11-23 09:30"), states, [], [], get=nopr, tell=lambda t: told.append(t) or (True, ""))
check(not told, "10:30 with a finding and no fix pull request: the note waits")
rr.step(utc("2026-11-23 09:45"), states, [], [], get=nopr, tell=lambda t: told.append(t) or (True, ""))
check(not told, "... and does not look again for half an hour")
rr.step(utc("2026-11-23 10:05"), states, [], [], get=get, tell=lambda t: told.append(t) or (True, ""))
check(len(told) == 1 and "pull/5" in told[0], "the fix pull request is there: the note goes out with its link")
os.remove(rr.STATE)
told.clear()
rr.step(utc("2026-11-23 17:05"), states, [], [], get=nopr, tell=lambda t: told.append(t) or (True, ""))
check(len(told) == 1 and "No fix pull request came today" in told[0], "18:05: the note goes out without one and says so")
os.remove(rr.STATE)
told.clear()
rr.step(utc("2026-11-23 03:05"), states, [], [], force=True, get=nopr, tell=lambda t: told.append(t) or (True, ""))
check(len(told) == 1, "up idni roadmap now: right away")

print("all ok" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)

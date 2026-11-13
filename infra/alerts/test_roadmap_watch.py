"""Unit test of roadmap_watch.py (no network): it reads the real Road to mainnet page, finds the IDNI issues and pull
requests each item links, takes their state from GitHub's list (faked here), and tells the owner once when one changes,
never at night and never on the first pass.

Run: python test_roadmap_watch.py
"""
import os
import sys
import tempfile
from datetime import datetime, timezone

TMP = tempfile.mkdtemp()
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["ROADMAP_PAGE"] = os.path.join(HERE, "..", "..", "roadmap", "index.html")
os.environ["ROADMAP_WATCH_PATH"] = os.path.join(TMP, "devpulse", "roadmap-links.json")
sys.path.insert(0, HERE)
import roadmap_watch as rw  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


def utc(s: str) -> float:
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()


# ---------------- the page ----------------
with open(rw.PAGE, encoding="utf-8") as f:
    its = rw.items(f.read())
by = {it["id"]: it for it in its}
check(len(its) >= 10 and "upgrades" in by and "rule-places" in by, f"the page's items are read ({len(its)})")
check(by["upgrades"]["refs"] == [82] and 93 in by["upgrades"]["links"], "an item's refs and the IDNI pull request its proof links")
check(by["rule-places"]["title"].startswith("Only two personal rules"), "... with its title")
check(by["language"]["refs"] == [], "an item without refs has none")
w = rw.wanted(its)
check(93 in w and [x["id"] for x in w[93]] == ["upgrades"], "#93 is linked by the restarts item only")
check(82 in w and {"upgrades", "join"} <= {x["id"] for x in w[82]}, "#82 is named by two items")
check(all(isinstance(n, int) for n in w), "numbers are numbers")


# ---------------- GitHub, faked ----------------
class GitHub:
    def __init__(self, states=None, fail=False):
        self.states = dict(states or {})
        self.fail, self.calls = fail, []

    def get(self, url):
        self.calls.append(url)
        if self.fail:
            raise OSError("rate limited")
        page = int(url.rsplit("page=", 1)[1])
        nums = list(range(120, 0, -1))[(page - 1) * 100: page * 100]
        out = []
        for n in nums:
            s = self.states.get(n, "open")
            j = {"number": n, "state": "closed" if s in ("closed", "merged", "not_planned") else "open"}
            if s == "not_planned":
                j["state_reason"] = "not_planned"
            if n in (86, 88, 93):
                j["pull_request"] = {"merged_at": "2026-11-12T06:57:33Z" if s == "merged" else None}
            out.append(j)
        return out


class Owner:
    def __init__(self, ok=True):
        self.ok, self.notes = ok, []

    def tell(self, text):
        self.notes.append(text)
        return self.ok, "" if self.ok else "no owner yet"


got = rw.fetch({85, 93, 78}, GitHub({93: "merged", 78: "closed"}).get)
check(got[93] == {"state": "merged", "pr": True} and got[78]["state"] == "closed" and got[85]["state"] == "open",
      "merged pull request, closed issue, open issue")
g = GitHub()
rw.fetch({85, 110}, g.get)
check(len(g.calls) == 1, "one list call when every number is on the first page")
g = GitHub()
rw.fetch({5, 110}, g.get)
check(len(g.calls) == 2, "the next page only while a number is still missing")
check(rw.fetch({93}, GitHub({93: "not_planned"}).get)[93]["state"] == "not_planned", "closed as not planned is its own state")

# ---------------- passes ----------------
DAY = utc("2026-11-12 13:00")   # 14:00 German time
NIGHT = utc("2026-11-12 22:30")  # 23:30 German time
gh, me = GitHub({78: "closed", 79: "closed"}), Owner()
st = rw.step(DAY, gh.get, me.tell)
check(st and st["93"]["state"] == "open" and st["78"]["state"] == "closed", "first pass: states for devpulse.json")
check(not me.notes, "... and nobody is told on the first pass")

gh.states[93] = "merged"
st = rw.step(DAY + 3600, gh.get, me.tell)
check(st["93"] == {"state": "merged", "pr": True}, "IDNI merged #93: the state moves")
check(len(me.notes) == 1 and "#93 is now merged (was open)" in me.notes[0], "... the owner is told: " + (me.notes[0].splitlines()[1] if me.notes else ""))
check("https://tauhud.com/roadmap/#upgrades" in me.notes[0] and "Restarts from block 0" in me.notes[0], "... with the item and its link")
rw.step(DAY + 7200, gh.get, me.tell)
check(len(me.notes) == 1, "... once, not again an hour later")

gh.states[85] = "closed"
rw.step(NIGHT, gh.get, me.tell)
check(len(me.notes) == 1 and rw.load()["pending"][0]["n"] == 85, "a change at night waits for the morning")
rw.step(NIGHT + 9 * 3600, gh.get, me.tell)
check(len(me.notes) == 2 and "#85 is now closed" in me.notes[1] and not rw.load()["pending"], "... and is told in the morning")

gh.states[80] = "closed"
rw.step(NIGHT + 24 * 3600, gh.get, me.tell)
gh.states[80] = "open"
rw.step(NIGHT + 25 * 3600, gh.get, me.tell)
rw.step(NIGHT + 33 * 3600, gh.get, me.tell)
check(len(me.notes) == 2 and not rw.load()["pending"], "closed at night and reopened before morning: nothing to say")

gh.states[82] = "closed"
down = Owner(ok=False)
rw.step(DAY + 5 * 86400, gh.get, down.tell)
check(len(down.notes) == 1 and rw.load()["pending"], "a note the bot could not send stays pending")
rw.step(DAY + 5 * 86400 + 3600, gh.get, me.tell)
check(len(me.notes) == 3 and "#82" in me.notes[2] and "#join" in me.notes[2] and "#upgrades" in me.notes[2],
      "... and goes out on the next pass, naming both items that link #82")

before = rw.load()
check(rw.step(DAY + 6 * 86400, GitHub(fail=True).get, me.tell) is None and rw.load() == before, "GitHub unreachable: nothing changes, nobody told")

print("all ok" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)

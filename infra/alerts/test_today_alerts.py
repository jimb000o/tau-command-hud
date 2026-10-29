"""Unit test of practice votes and "Testnet today" (no network): a proposal that only repeats the rules in force gets no
post of its own; one evening summary counts it with the day's numbers, once, only on a day with something to report.

Run: python test_today_alerts.py   (needs websockets==15.0.1)
"""
import asyncio
import os
import sys
import tempfile
import time
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

    def send(self, item):
        self.sent.append((alerts.telegram_text(item), None))
        return True, None, ""

    def send_text(self, text, buttons=None):
        self.sent.append((text, buttons))
        return True, None, ""


def at(day: str, hm: str) -> float:
    return datetime.strptime(f"{day} {hm}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()


T = at("2026-10-28", "19:00")
STATS = {"fields": ["height", "timestamp", "txs", "transfers", "volume", "proposer", "types", "senders"], "head": 1800,
         "blocks": [[h, T - 86400 + h * 40, 1 if h % 100 == 0 else 0, 0, 0, 0, [], [h % 3] if h % 100 == 0 else []] for h in range(1, 2160)]}
same = {"title": "Same rules as now (no real change)", "changes": [], "why": "Nothing would change.", "severity": "none"}
fee = {"title": "Base fee 20 → 30 AGRS", "changes": [{"topic": "Fee", "text": "30 AGRS", "why": "Every transfer pays more."}],
       "why": "Every transfer pays more.", "severity": "normal"}
PROPS = [{"id": "a", "title": fee["title"], "explain": fee, "approved_at": 1700, "activated_at": None, "expired_at": None, "activate_at": 5030},
         {"id": "b", "title": same["title"], "explain": same, "approved_at": 1711, "activated_at": None, "expired_at": None, "activate_at": 6707}]


def item(kind, pid, practice, seen, headline):
    return {"key": f"c:{kind}:{pid}", "kind": kind, "id": pid, "practice": practice, "seen": seen, "news": True, "posted": {},
            "headline": headline, "what": [], "why": "", "facts": ["x"], "link": "https://tauhud.com/proposals/"}


# practice votes: never a post of their own
tg = Fake()
w = alerts.Watcher([tg])
w.state["outlets"] = {"telegram": {"since": 0}}
now = time.time()
w.state["items"] = [item("agreed", "b", True, now, "Agreed: Same rules as now (no real change)"),
                    item("agreed", "a", False, now, "Agreed: Base fee 20 → 30 AGRS")]
asyncio.run(w.deliver())
check(len(tg.sent) == 1 and "Base fee" in tg.sent[0][0], "a real change is posted, the practice vote is not")
w.state["items"].insert(0, item("agreed", "a2", False, now + 60, "Agreed: Base fee 20 → 30 AGRS"))
w.state["items"][0]["key"] = "c:agreed:a2"
asyncio.run(w.deliver())
check(len(tg.sent) == 1 and w.state["items"][0]["posted"]["telegram"] == "skip", "the same news an hour later is not posted again")

# the evening summary
items = [item("agreed", "b", True, T - 3600, "Agreed: Same rules as now (no real change)"),
         item("proposed", "b", True, T - 3700, "New proposal: Same rules as now (no real change)"),
         item("agreed", "c", True, T - 1800, "Agreed: Same rules as now (no real change)"),
         item("agreed", "a", False, T - 7200, "Agreed: Base fee 20 → 30 AGRS"),
         item("agreed", "z", True, T - 90000, "Agreed: Same rules as now (no real change)")]
r = alerts.today_numbers(STATS, items, PROPS, 2, T)
check(r["blocks"] == 2159 and r["pace"] == 40 and r["txs"] == 21 and r["senders"] == 3, "blocks, pace, transactions, accounts of the last 24 h")
check(r["practice"] == 2 and r["events"] == ["Agreed: Base fee 20 → 30 AGRS"], "practice votes counted once each, real events listed")
check([c["title"] for c in r["coming"]] == ["Base fee 20 → 30 AGRS"], "coming up: real changes only")
t = alerts.today_text(r)
check(t.startswith(alerts.REAL_LINE + "\n📋 <b>Testnet today, 28 October</b>"), "real-chain first line, then the date")
check("2,159 blocks, one every 40 seconds" in t and "2 practice votes" in t and "nothing changes" in t, "plain lines")
# stored before practice votes had their flag (the 29 Oct summary listed four of them as rule changes): still practice
old = [item("agreed", f"o{i}", False, T - 600 * i, "New rule change, agreed right away: Same rules as now (no real change)")
       for i in range(1, 5)] + [item("agreed", "a", False, T - 7200, "Agreed: Base fee 20 → 30 AGRS"),
                                item("active", "d", False, T - 500, "Now in force: Base fee 20 → 30 AGRS"),
                                item("active", "e", False, T - 400, "Now in force: Base fee 20 → 30 AGRS")]
props = PROPS + [{"id": f"o{i}", "title": "x", "proposer": "acct1" if i < 4 else "acct2"} for i in range(1, 5)]
r = alerts.today_numbers(STATS, old, props, 2, T)
check(r["practice"] == 4 and "New rule change" not in " ".join(r["events"]), f"old no-change items count as practice {r['events']}")
check(sorted(r["events"]) == ["2× Now in force: Base fee 20 → 30 AGRS", "Agreed: Base fee 20 → 30 AGRS"], f"equal lines grouped {r['events']}")
t = alerts.today_text(r)
check("4 practice votes" in t and "3 of them from one account" in t and t.count("Same rules as now") == 0, "practice votes explained, not listed")
check(alerts.practice_meaning(5, ["a"] * 5).startswith("all from one account"), "one account: looks like a test")
check("probably people trying the Vote page" in alerts.practice_meaning(4, ["a", "b", "c", "d"]), "many accounts: the Vote page")
check("Coming up: Base fee 20 → 30 AGRS at block #5,030" in t, "what comes next")
check(alerts.today_buttons()["inline_keyboard"][0][1]["url"].endswith("/vote/"), "a button to the Vote page")
quiet = alerts.today_numbers({"fields": STATS["fields"], "blocks": STATS["blocks"][:5]}, [], [], 2, T)
check(not alerts.today_worth_posting(quiet), "a quiet day is not worth a post")

# the slot: once at 19:00 UTC, not late, not twice
tg2 = Fake()
w2 = alerts.Watcher([tg2])
w2.state["items"], w2.props = items, PROPS
w2.relay_json = lambda path: STATS if path == "/stats" else None
asyncio.run(w2.maybe_today(at("2026-10-28", "18:59")))
check(tg2.sent == [], "nothing before 19:00 UTC")
asyncio.run(w2.maybe_today(at("2026-10-28", "19:01")))
check(len(tg2.sent) == 1 and "Testnet today" in tg2.sent[0][0], "posted at 19:00 UTC")
asyncio.run(w2.maybe_today(at("2026-10-28", "20:00")))
check(len(tg2.sent) == 1, "once a day")
asyncio.run(w2.maybe_today(at("2026-10-29", "23:00")))
check(len(tg2.sent) == 1, "a missed evening is not posted late")
w3 = alerts.Watcher([tg3 := Fake()])
w3.state.pop("today", None)
w3.state["items"], w3.props = [], []
w3.relay_json = lambda path: {"fields": STATS["fields"], "blocks": STATS["blocks"][:5]} if path == "/stats" else None
asyncio.run(w3.maybe_today(at("2026-10-28", "19:05")))
check(tg3.sent == [] and w3.state["today"]["slot"] == T, "a quiet day is marked done without a post")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

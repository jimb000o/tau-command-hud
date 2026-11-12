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
check(len(tg3.sent) == 1 and "quiet day, only empty blocks" in tg3.sent[0][0] and w3.state["today"]["slot"] == T,
      "a quiet day still gets its Telegram post, saying it was quiet")
check(not alerts.today_worth_x(quiet), "a quiet day with blocks is not for X")
still = alerts.today_numbers({"fields": STATS["fields"], "blocks": []}, [], [], 2, T, T - 30 * 3600)
check(alerts.today_worth_x(still) and "stood still" in alerts.today_text(still) and "30 hours ago" in alerts.today_text(still),
      "a day without a block says so, with the last block's time, and goes to X")
check("no block in 24 hours" in alerts.today_x(still), "the X copy of a day without a block")

# X does not wait for a failing Telegram: the X copy goes alone, and the Telegram retry does not repeat it on X
class Failing(Fake):
    def send_text(self, text, buttons=None):
        self.sent.append((text, buttons))
        return False, None, "HTTP 401: Unauthorized"


class FakeX(Fake):
    name = "x"


w4 = alerts.Watcher([tg4 := Failing(), x4 := FakeX()])
w4.state.pop("today", None)
w4.state.pop("x", None)
w4.state["items"], w4.props = items, PROPS
w4.relay_json = lambda path: STATS if path == "/stats" else None
asyncio.run(w4.maybe_today(at("2026-10-28", "19:01")))
check(len(tg4.sent) == 1 and len(x4.sent) == 1 and "Testnet today" in x4.sent[0][0], "Telegram fails: X goes alone")
asyncio.run(w4.maybe_today(at("2026-10-28", "19:02")))
check(len(tg4.sent) == 1 and len(x4.sent) == 1, "while Telegram pauses nothing repeats")
tg4.send_text = lambda text, buttons=None: (tg4.sent.append((text, buttons)), (True, None, ""))[1]
asyncio.run(w4.maybe_today(at("2026-10-28", "19:07")))
check(len(tg4.sent) == 2 and len(x4.sent) == 1, "Telegram back: its post goes out, X not again")


# who sent today (relay /wallets/active, the Active wallets chart's source), the usual number, the newcomers, the ship
TAGS = ["idni", "bot", "cruise", "rabbit", "agorzilla", "tauhud", "other"]
ACTIVE = {"tags": TAGS, "windows": [1, 7, 30, 90], "new": {"2026-11-04": [0, 0, 52, 1, 0, 2, 6]},
          "days": {f"2026-10-{d:02d}": {"1": [11, 3, 0, 2, 1, 2, 3]} for d in range(28, 32)}}
ACTIVE["days"].update({"2026-11-01": {"1": [11, 3, 0, 2, 1, 2, 3]}, "2026-11-02": {"1": [11, 3, 0, 2, 1, 2, 3]},
                       "2026-11-03": {"1": [11, 3, 0, 2, 1, 2, 3]}, "2026-11-04": {"1": [11, 3, 52, 2, 0, 2, 7]}})
LOG = [{"t": at("2026-11-04", "15:02"), "kind": "landed", "ship": "dryrun", "visit": "v1"}, {"t": at("2026-11-04", "16:30"), "kind": "left", "ship": "dryrun"}]
ships = alerts.ships_in(LOG, at("2026-11-03", "19:00"), at("2026-11-04", "19:00"))
check(ships == ["MS Dry Run"], f"the ship that landed in the window, by name {ships}")
check(alerts.ships_in(LOG, at("2026-11-05", "19:00"), at("2026-11-06", "19:00")) == [], "no ship on another day")
w = alerts.today_wallets(ACTIVE, "2026-11-04", ships)
check(w["total"] == 77 and w["usual"] == 22 and w["ratio"] == 3.5 and w["new"] == 61 and w["by"]["cruise"] == 52, f"77 wallets, 3.5× the usual 22 {w}")
check(alerts.wallets_head(w) == "77 wallets sent transactions, 3.5× the usual 22", "the head line of a spike")
lines = alerts.wallets_lines(w)
check(lines[0] == "52 of them: simulated passengers of MS Dry Run: our own wallets, every stop a real transaction", f"the passengers first, named as ours {lines[0]}")
check("11 of them: IDNI's own test accounts, the ones the testnet started with" in lines and "7 of them: other wallets, not ours and not IDNI's" in lines
      and lines[-1] == "61 wallets nobody had seen before", f"IDNI, strangers, newcomers {lines}")
w3 = alerts.today_wallets(ACTIVE, "2026-11-03")
check(w3["total"] == 22 and alerts.wallets_head(w3) == "22 wallets sent transactions, about the usual 22", "an ordinary day: about the usual")
check(alerts.today_wallets(ACTIVE, "2026-11-09") is None and alerts.today_wallets(None, "2026-11-04") is None, "no record of the day: no wallet lines")
check(alerts.today_wallets({"tags": TAGS, "days": {"2026-11-04": {"1": [1, 0, 0, 0, 0, 0, 0]}}}, "2026-11-04")["usual"] is None, "the first day has no usual")
T4 = at("2026-11-04", "19:00")
STATS4 = {"fields": STATS["fields"], "head": 1800, "blocks": [[h, T4 - 86400 + h * 60, 1, 0, 0, 0, [], [h % 3]] for h in range(1, 1440)]}
r4 = alerts.today_numbers(STATS4, [], PROPS, 2, T4)
r4["wallets"] = w
t4 = alerts.today_text(r4)
check("<b>77 wallets sent transactions, 3.5× the usual 22</b>\n52 simulated passengers of MS Dry Run (ours) · 7 in our games and bots · 11 IDNI test accounts · 7 from outside · 61 new" in t4
      and "from 3 accounts" not in t4, "Testnet today leads with who sent, the stats' account count is not repeated")
check("<b>Why it matters</b>\nEvery one of these was a real signed transaction the single validator had to check, and the chain kept one block a minute." in t4,
      f"a spike says why it matters, from the facts {t4}")
x4 = alerts.today_x(r4)
check(x4.startswith("📋 Testnet today, 4 November\n\n77 wallets sent today, 3.5× the usual 22: 52 passengers of MS Dry Run (ours, simulated).")
      and "Why it matters: Each a real signed transaction the one validator checked; the chain kept one block a minute." in x4
      and alerts.x_len(x4) <= 280, f"the X copy names the passengers as ours and says why it matters {x4}")
check(alerts.today_worth_x(r4), "a spike goes to X")
r3 = dict(r4, wallets=w3, events=[])
check(not alerts.today_worth_x(r3), "an ordinary day with the usual wallets is Telegram's alone")
check("Why it matters" not in alerts.today_text(r3) and "People outside" not in alerts.today_text(r3),
      "the usual outside wallets again: no sentence about them (11 Nov 2026: the same line four evenings in a row)")
r3n = dict(r3, wallets=dict(w3, other_new=1))
check("Why it matters</b>\n3 wallets that are not ours and not IDNI&#x27;s sent today, one of them for the first time: someone new" in alerts.today_text(r3n),
      f"a new outside wallet says so {alerts.today_text(r3n)}")
r3m = dict(r3, wallets=dict(w3, by=dict(w3["by"], other=6)))
check("6 wallets that are not ours and not IDNI&#x27;s sent today, more than the usual 3." in alerts.today_text(r3m), "more outside wallets than usual")
A2 = {"tags": TAGS, "days": {**ACTIVE["days"], "2026-11-05": {"1": [11, 3, 0, 2, 1, 2, 3]}}}
check(alerts.today_wallets(A2, "2026-11-05")["usual"] == 22, "a cruise day before does not lift the usual number")
r5 = dict(r3, wallets=alerts.today_wallets(dict(ACTIVE, new={}), "2026-11-02"))
r5["wallets"]["by"] = {"idni": 11, "bot": 3}
check("Why it matters" not in alerts.today_text(r5) and not alerts.today_worth_x(r5), "only our own and IDNI's wallets: no generic why")
slow = dict(r4, pace=140)
check("the chain slowed to one block every 140 seconds" in alerts.today_text(slow), "a spike on a slow chain says so, no praise")
check(alerts.today_worth_x(dict(r3, wallets=dict(w3, new=3))), "three newcomers are news for X")

# the same sentence over and over (11 Nov 2026): a template said twice in 7 days is left out the third time
S, N0 = {}, at("2026-11-08", "19:00")
a, b = "1 wallet that is not ours sent today.", "3 wallets that are not ours sent today."
check(alerts.said_key(a) == alerts.said_key(b), "numbers do not make a sentence new")
alerts.remember_said(S, a, N0)
check(not alerts.said_often(S, b, N0 + 86400), "once: may be said again")
alerts.remember_said(S, b, N0 + 86400)
check(alerts.said_often(S, a, N0 + 2 * 86400), "twice in a week: left out")
alerts.remember_said(S, "other", N0 + 9 * 86400)
check(not alerts.said_often(S, a, N0 + 9 * 86400) and len(S["said"]) == 1, f"old entries are forgotten {S}")
check(alerts.today_why(dict(r4, why_off=True)) is None, "why_off: no why")
print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

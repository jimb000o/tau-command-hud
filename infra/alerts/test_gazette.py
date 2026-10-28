"""Unit test of the weekly newspaper edition (no network): the visitors' day, the headline for each kind of week, both
languages on every line, careful words, the files and their numbering, and the first edition on start.

Run: python test_gazette.py   (needs websockets==15.0.1)
"""
import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="", SITE_URL="https://tauhud.com")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402
import gazette  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


END = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc).timestamp()


def week(**kw):
    r = {"start": END - 7 * 86400, "end": END, "head": 12000, "blocks": 10500, "old_blocks": 0, "pace": 8.1, "txs": 640, "transfers": 410,
         "volume": 0, "accounts": 23, "top": [], "per_day": [1500] * 7, "days": ["Mon"] * 7, "proposed": 0, "agreed": 0, "active": 0,
         "dropped": 0, "active_titles": [], "restarts": 0, "nodes": 2, "new_nodes": 0}
    r.update(kw)
    return r


def texts(x):
    """every {en, zh} pair anywhere in an edition"""
    if isinstance(x, dict):
        if set(x) == {"en", "zh"}:
            yield x
        else:
            for v in x.values():
                yield from texts(v)
    elif isinstance(x, list):
        for v in x:
            yield from texts(v)


# ---- the visitors' day ----
votes = {"day": "2026-10-30", "items": {
    "slot:0": {"yes": 3, "no": 1, "outcome": "yes"}, "slot:1": {"yes": 0, "no": 2, "outcome": "no"},
    "slot:2": {"yes": 0, "no": 0, "outcome": "none"}, "slot:3": {"yes": 1, "no": 0, "outcome": None},
    "visitor:ab": {"yes": 4, "no": 1, "outcome": "yes"}, "visitor:cd": {"yes": 0, "no": 0, "outcome": "none"}}}
preds = {"day": "2026-10-30", "forecasters": 5, "board": [{"name": "Quiet Otter", "points": 17}]}
d = gazette.sim_day(votes, preds)
check(d["ballots"] == 2 and d["carried"] == 1 and d["turned"] == 1, f"closed hourly ballots with votes are counted ({d})")
check(d["votes"] == 3 + 1 + 2 + 4 + 1 and d["visitor_props"] == 2 and d["visitor_carried"] == 1, "votes and visitors' own proposals are counted")
check(d["best"] == {"name": "Quiet Otter", "points": 17} and d["forecasters"] == 5, "the day's best forecaster is kept by name and points")
check(gazette.sim_day(votes, {**preds, "day": "2026-10-29"})["best"] is None, "a forecast board of another day is not mixed in")
check(gazette.sim_day(None, None) is None and gazette.sim_day({}, None) is None, "nothing from the relay, nothing noted")

# ---- headlines for each kind of week ----
props = [{"title": "Base fee 6", "status": "agreed", "activate_at": 12450}, {"title": "x", "status": "voting", "activate_at": 13000},
         {"title": "old", "status": "active", "activate_at": 9000}]
cases = [("active", week(active=1, agreed=1, proposed=1, active_titles=["Base fee 7"])), ("agreed", week(agreed=1, proposed=1)),
         ("restart", week(restarts=1, old_blocks=300)), ("proposed", week(proposed=2)), ("nodes", week(new_nodes=1, nodes=3)), ("steady", week())]
BANNED = ["price", "buy", "invest", "profit", "moon", "coin comes", "market of tomorrow", "real agoras", "guarantee"]
for kind, r in cases:
    e = gazette.edition(r, props, [d], 3, END)
    check(e["kind"] == kind, f"{kind}: the headline follows the week ({e['banner']['en']})")
    pairs = list(texts(e))
    check(all(p["en"].strip() and p["zh"].strip() for p in pairs), f"{kind}: every line has English and Chinese ({len(pairs)} lines)")
    words = json.dumps(e, ensure_ascii=False).lower()
    check(not any(b in words for b in BANNED), f"{kind}: no promotional or promising words")
e = gazette.edition(cases[0][1], props, [d], 3, END)
check("Base fee 7" in e["lead"]["h"]["en"] and "「Base fee 7」" in e["lead"]["h"]["zh"], "the rule now in force is named in the lead")
up = json.dumps(e["stories"][0], ensure_ascii=False)
check("Base fee 6" in up and "#12,450" in up and "1 more proposal is open" in up, "coming up: the agreed change with its block, then the open votes")
check("Quiet Otter" in json.dumps(e["stories"][1]) and "not on the real testnet" in json.dumps(e["stories"][1]), "the rehearsal hall names the best forecaster and says it is the simulation")
check(e["printed"]["en"] == "Monday, November 2, 2026" and e["printed"]["zh"] == "2026年11月2日 星期一", "printing date in both languages")
check(e["period"]["en"] == "26 October – 2 November 2026", f"the week covered ({e['period']['en']})")
check(gazette.rehearsal([])["body"][0]["en"].startswith("In the simulation the visitors decide"), "no noted days: an invitation instead of numbers")
check("No rule change is waiting" in gazette.coming_up([], 1, 8)["body"][0]["en"], "nothing waiting: says so and where to learn to vote")


# ---- files, numbering, first edition ----
class Relay(alerts.Watcher):
    def relay_json(self, path):
        return {"/sim/votes": votes, "/sim/predictions": preds}.get(path)

    def recap_numbers(self, end):
        return week(end=end, start=end - 7 * 86400, active=1, active_titles=["Base fee 7"])


w = Relay(outlets=[])
with open(os.path.join(TMP, "proposals.json"), "w") as f:
    json.dump({"proposals": props}, f)
NOW = datetime(2026, 10, 30, 22, 0, tzinfo=timezone.utc).timestamp()
asyncio.run(w.maybe_gazette(NOW))
g = os.path.join(TMP, "recap", "gazette")
latest = json.load(open(os.path.join(g, "latest.json")))
check(latest["no"] == 1 and latest["date"] == "2026-10-30", "the first edition is written on start, No. 1")
check("2026-10-30" in w.state["simdays"], "the visitors' day is noted")
check(os.path.exists(os.path.join(g, "2026-10-30.json")), "each edition is kept under its date")
asyncio.run(w.maybe_gazette(NOW + 60))
check(len(json.load(open(os.path.join(g, "editions.json")))) == 1, "no second edition while one is out")
e2 = w.make_gazette(w.recap_numbers(END), END)
e3 = w.make_gazette(w.recap_numbers(END), END + 300)
idx = json.load(open(os.path.join(g, "editions.json")))
check(e2["no"] == 2 and e3["no"] == 2 and [x["no"] for x in idx] == [2, 1], "the Monday edition is No. 2; written again the same day it keeps its number")
check(set(idx[0]) >= {"no", "date", "banner", "teaser", "url"}, "the archive lists number, date, headline, teaser and link")
check(e2["stories"][1]["body"][0]["en"].startswith("In the simulation, where the visitors decide, 2 hourly"), "the week's noted day goes into the rehearsal hall")

print("\n" + ("all ok" if not failed else f"{failed} FAILED"))
sys.exit(1 if failed else 0)

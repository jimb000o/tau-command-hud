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


END = datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc).timestamp()


def week(**kw):
    r = {"start": END - 7 * 86400, "end": END, "head": 12000, "blocks": 10500, "old_blocks": 0, "pace": 8.1, "txs": 640, "transfers": 410,
         "volume": 0, "accounts": 23, "top": [], "per_day": [1500] * 7, "days": ["Mon"] * 7, "proposed": 0, "agreed": 0, "active": 0,
         "dropped": 0, "active_titles": [], "restarts": 0, "nodes": 2, "new_nodes": 0}
    r.update(kw)
    return r


def texts(x):
    """every {en, zh, ja} text anywhere in an edition"""
    if isinstance(x, dict):
        if set(x) == {"en", "zh", "ja"}:
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
    check(pairs and all(p["en"].strip() and p["zh"].strip() and p["ja"].strip() for p in pairs), f"{kind}: every line has English, Chinese and Japanese ({len(pairs)} lines)")
    words = json.dumps(e, ensure_ascii=False).lower()
    check(not any(b in words for b in BANNED), f"{kind}: no promotional or promising words")
e = gazette.edition(cases[0][1], props, [d], 3, END)
check(e["lead"]["h"]["en"] == "A Base Fee of 7 Takes Effect at the Appointed Block" and "基本手续费定为 7" in e["lead"]["h"]["zh"] and "基本手数料を 7 とする定め" in e["lead"]["h"]["ja"], f"the rule now in force is named in the lead, in the paper's words ({e['lead']['h']['en']})")
up = json.dumps(e["stories"][0], ensure_ascii=False)
check("A Base Fee of 6." in up and "#12,450" in up and "One more proposal is open" in up, "coming up: the carried change with its block, then the open votes")

# ---- the paper's voice: no brackets, arrows or tracker titles in what is printed ----
for ti, en in [("Same rules as now (no real change)", None), ("Base fee 6 → 7 AGRS", "a base fee of 7"), ("New rule for valid blocks", "a new rule on valid blocks"),
               ("Base fee 7 AGRS + Admit validator ab12cd…ef90", "a base fee of 7 and one more amendment"),
               ("Base fee 7 AGRS + Every validator may make blocks + 2 more", "a base fee of 7 and three more amendments"), ("Something new", "an amendment to the rules")]:
    ph = gazette.phrase(ti)
    check((ph and ph["en"]) == en, f"phrase: {ti} -> {en}")
same = "Same rules as now (no real change)"
props2 = [{"title": same, "status": "agreed", "activate_at": 5295, "proposed_ts": END - 3600}, {"title": "New rule for valid blocks", "status": "agreed", "activate_at": 5028, "proposed_ts": END - 7200},
          {"title": same, "status": "agreed", "activate_at": 5338, "proposed_ts": END - 600}]
e = gazette.edition(week(agreed=3, proposed=3, head=4900), props2, [], 1, END)
check(e["lead"]["h"]["en"] == "Vote Carries for a New Rule on Valid Blocks, in Force from Block #5,028", f"agreed: the real change leads, not a ballot that keeps the rules ({e['lead']['h']['en']})")
up = json.dumps(e["stories"][0], ensure_ascii=False)
check(up.count("The rules as they stand") == 1 and "Two carried ballots to keep them unchanged fall due from block #5,295 onward." in up, "coming up: ballots that keep the rules are told once")
check(any("Two further ballots only kept the rules as they stand: practice" in p["en"] for p in e["lead"]["body"]), "ballots that keep the rules get one short line")
only = gazette.edition(week(agreed=1, proposed=1, head=4900), props2[:1], [], 1, END)
check(only["banner"]["en"] == "Practice ballots, and the rules hold" and only["lead"]["h"]["en"] == "One Ballot Keeps the Rules as They Stand", f"only a ballot that keeps the rules: no big news ({only['lead']['h']['en']})")
for kind, r in cases + [("agreed", week(agreed=3, proposed=3, head=4900))]:
    e = gazette.edition(r, props2 + props, [d], 3, END)
    printed_ = [e["banner"], e["lead"]["h"], e["lead"]["deck"], e["lead"]["kick"], *e["lead"]["body"], *e["stories"][0]["body"]]
    bad = [x for p in printed_ for x in (p["en"], p["zh"], p["ja"]) if any(c in x for c in ("(", "→", " + ", "「", "Same rules as now"))]
    check(not bad, f"{kind}: no brackets, arrows or tracker titles in print {bad[:1]}")
    check(len(e["banner"]["en"]) <= 52, f"{kind}: the banner fits two balanced lines ({e['banner']['en']})")
    check(len(e["big"]["en"].split()) <= 5 and 40 < len(e["line"]["en"]) < 150, f"{kind}: a big banner of few words and one line under it ({e['big']['en']})")
    check(e["weather"]["en"].startswith(("Fair.", "Calm.")) and e["caption"]["en"].startswith("<b>The week at the core.</b>"), f"{kind}: weather ear and photo caption")
check("Quiet Otter" in json.dumps(e["stories"][1]) and "not on the real testnet" in json.dumps(e["stories"][1]), "the rehearsal hall names the best forecaster and says it is the simulation")
check(e["printed"]["en"] == "Monday, November 9, 2026" and e["printed"]["zh"] == "2026年11月9日 星期一" and e["printed"]["ja"] == "2026年11月9日 月曜日", "printing date in all three languages")
check(e["period"]["en"] == "2–9 November 2026", f"the week covered ({e['period']['en']})")
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
w.state["simdays"]["2026-11-05"] = {**d, "day": "2026-11-05"}
e2 = w.make_gazette(w.recap_numbers(END), END)
e3 = w.make_gazette(w.recap_numbers(END), END + 300)
idx = json.load(open(os.path.join(g, "editions.json")))
check(e2["no"] == 2 and e3["no"] == 2 and [x["no"] for x in idx] == [2, 1], "the Monday edition is No. 2; written again the same day it keeps its number")
check(set(idx[0]) >= {"no", "date", "banner", "teaser", "url"}, "the archive lists number, date, headline, teaser and link")
check(e2["stories"][1]["body"][0]["en"].startswith("Across town from the real testnet") and "In the simulation, where the visitors decide, two hourly" in json.dumps(e2["stories"][1]), "the week's noted day goes into the rehearsal hall")
alerts.PUBLIC_DIR, w0 = TMP, alerts.Watcher
alerts.Watcher = Relay
code = alerts.gazette_cli(reprint=True)
alerts.Watcher = w0
idx = json.load(open(os.path.join(g, "editions.json")))
check(code == 0 and [x["no"] for x in idx] == [2, 1] and json.load(open(os.path.join(g, "latest.json")))["date"] == "2026-11-09", "a reprint keeps the latest edition's number, date and week")


# ---- the café walk's talk of the week ----
c = e2["cafe"]
check(set(c) == {"mae", "elias", "prof", "sully"} and all(v["greet"]["en"] and v["q"]["en"] and v["a"] for v in c.values()), "each regular has a line, a question and an answer for the week")
check("Friday's pie" in c["mae"]["greet"]["en"] and "practice votes in the simulation" in json.dumps(c["mae"]), "Mae: the pie of the week, and the visitors' practice votes called practice")
check("10,500 blocks" in c["elias"]["greet"]["en"] and "front page" in c["sully"]["greet"]["en"] and e2["banner"]["en"].rstrip(".!") in c["sully"]["greet"]["en"], "Elias counts the week's blocks, Sully calls the headline")
check(gazette.cafe(week(), [], [], 1, e2["banner"], e2["teaser"])["mae"]["greet"] != gazette.cafe(week(), [], [], 2, e2["banner"], e2["teaser"])["mae"]["greet"], "the running jokes turn with the edition")
check(len(json.dumps(c, ensure_ascii=False).encode()) < 9000, "the café block stays small (a few KB a week)")
q = gazette.cafe(week(restarts=1, dropped=2), [], [], 3, e2["banner"], e2["teaser"])
check("fresh start" in json.dumps(q) and "dropped at the deadline" in json.dumps(q), "a fresh chain and dropped proposals are told")
old = json.load(open(os.path.join(g, "latest.json"))); old.pop("cafe")
json.dump(old, open(os.path.join(g, "latest.json"), "w"))
w.state["gazette"].pop("cafe", None)
asyncio.run(w.maybe_gazette(NOW + 120))
back = json.load(open(os.path.join(g, "latest.json")))
check(back.get("cafe", {}).get("mae") and back["no"] == old["no"] and json.load(open(os.path.join(g, old["date"] + ".json"))).get("cafe"), "an edition printed before the café talk gets it once, number and date unchanged")

print("\n" + ("all ok" if not failed else f"{failed} FAILED"))
sys.exit(1 if failed else 0)

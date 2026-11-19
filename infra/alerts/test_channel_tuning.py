"""Unit test of the channel's self-tuning parts (7 November 2026, no network): links carry ref=tg-<kind>, the Sunday
note counts opens per kind and makes a kind nobody opens post every other time, the weekly poll picks the next closer
look, the monthly costs post adds up only the bills that are in, plus last month's measured Gemini pictures.

Run: python test_channel_tuning.py   (needs websockets==15.0.1)
"""
import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="", SITE_URL="https://tauhud.com",
                  TICKER_OWNER_CHAT="")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


# links
t, b = alerts.tag_links('🔎 <b>TAU HUD · a closer look</b>\n<a href="https://tauhud.com/rules/#new">r</a> see https://tauhud.com/',
                        {"inline_keyboard": [[{"text": "x", "url": "https://tauhud.com/?mode=sim"}, {"text": "t", "url": "https://t.me/a"}]]},
                        "deepdive")
check('href="https://tauhud.com/rules/?ref=tg-deepdive#new"' in t, "href tagged before the fragment")
check("see https://tauhud.com/" in t and "see https://tauhud.com/?ref" not in t, "a link written as text stays as written")
check(b["inline_keyboard"][0][0]["url"] == "https://tauhud.com/?mode=sim&ref=tg-deepdive" and b["inline_keyboard"][0][1]["url"] == "https://t.me/a",
      "buttons: ours tagged, others untouched")
check(alerts.tg_kind("⛓ <b>TESTNET ALPHA · live chain</b>\n📋 <b>Testnet today, 6 November</b>") == "today", "kind: evening post")
check(alerts.tg_kind("💚 <b>TAU HUD · what it costs to run</b>") == "costs", "kind: costs post")

# Sunday note and tuning
SUN = datetime(2026, 12, 6, 17, 0, tzinfo=timezone.utc).timestamp()
w = alerts.Watcher.__new__(alerts.Watcher)
w.state, w.outlets = {"clicks": {"since": SUN - 40 * 86400}}, []
w.save_state = lambda: None
posts = {"2026-11-20": {"deepdive": 2, "today": 1}, "2026-12-02": {"deepdive": 2, "digest": 1}, "2026-12-05": {"today": 1}}
opens = {"2026-12-05": {"today": 4}}
asyncio.run(w.maybe_clicks(SUN, opens, posts))
check(w.state["quiet_kinds"] == ["deepdive"], f"deep dives with 4 posts and no open go quiet: {w.state['quiet_kinds']}")
check(any("tuned" not in x["what"] and "deepdive" in x["what"] for x in w.state["tuned"]), "the change is recorded with its reason")
asyncio.run(w.maybe_clicks(SUN + 600, {"2026-12-06": {"deepdive": 1}}, posts))
check(w.state["quiet_kinds"] == ["deepdive"], "once a week only")
asyncio.run(w.maybe_clicks(SUN + 7 * 86400, {"2026-12-12": {"deepdive": 1}}, posts))
check(w.state["quiet_kinds"] == [], "one open brings it back")
w2 = alerts.Watcher.__new__(alerts.Watcher)
w2.state, w2.outlets, w2.save_state = {"clicks": {"since": SUN - 5 * 86400}}, [], (lambda: None)
asyncio.run(w2.maybe_clicks(SUN, opens, posts))
check(w2.state["quiet_kinds"] == [], "no tuning before 28 days of data")
txt = alerts.clicks_text(alerts.clicks_table(opens, posts, "2026-11-30"), ["deepdive"], [])
check("today: 1 post, 4 opens" in txt and "only you" in txt, "the owner's note lists posts and opens")

# poll closing picks the winner
class FakeTG:
    name = "telegram"
    def enabled(self): return True
    def call_raw(self, method, body, ctype="application/json"):
        self.method = method
        return True, None, "", {"result": {"options": [{"voter_count": 1}, {"voter_count": 3}, {"voter_count": 0}]}}
w3 = alerts.Watcher.__new__(alerts.Watcher)
w3.outlets, w3.save_state = [FakeTG()], (lambda: None)
w3.state = {"poll": {"open": {"msg": 5, "ids": ["a", "b", "c"], "at": 0}}, "deepdives": {}}
asyncio.run(w3.close_poll(alerts.POLL_OPEN + 1))
check(w3.state["deepdives"]["voted"] == "b" and "open" not in w3.state["poll"], "poll: most votes goes next")

# the poll rotates (Kilian, 19 Nov 2026: the same pages again while the site kept growing)
class PollTG(FakeTG):
    def __init__(self):
        self.asked = []
    def call_raw(self, method, body, ctype="application/json"):
        if method == "stopPoll":
            return True, None, "", {"result": {"options": [{"voter_count": 0}] * 4}}
        self.asked.append([o["text"] for o in json.loads(body)["options"]])
        return True, None, "", {"result": {"message_id": 7}}
pages = [{"id": c, "title": c.upper(), "link": f"/{c}/"} for c in "abcdefghij"]
w4 = alerts.Watcher.__new__(alerts.Watcher)
tg4 = PollTG()
w4.outlets, w4.save_state = [tg4], (lambda: None)
WED = datetime(2026, 11, 25, 16, 5, tzinfo=timezone.utc).timestamp()
w4.state = {"poll": {"open": {"ids": ["a", "b"], "at": WED - 7 * 86400}}, "pages": {"/c/": WED - 3600},
            "deepdives": {"posts": pages[:8], "posted": {"d": 1}, "x_posted": {}, "voted": "e",
                          "extra": [{"id": "page-k", "title": "K", "link": "/k/", "auto": True},
                                    {"id": "page-a", "title": "A again", "link": "/a/", "auto": True}]}}
w4.state["poll"].pop("open")
w4.state["poll"]["offered"] = {"a": WED - 7 * 86400, "b": WED - 7 * 86400}
asyncio.run(w4.maybe_poll(WED))
check(tg4.asked == [["F", "G", "H", "K"]],
      f"poll: offered pages, the posted one, the voted one and one shown an hour ago stay out; a new page joins: {tg4.asked}")
for wk in range(1, 3):
    w4.state["poll"].pop("open", None)
    w4.state["pages"] = {}
    asyncio.run(w4.maybe_poll(WED + wk * 7 * 86400))
check(tg4.asked[1] == ["C", "A", "B", "F"],
      f"poll: one page left, so a new round: the page never offered first, then the ones offered longest ago: {tg4.asked[1]}")
check(tg4.asked[2] == ["G", "H", "K"], f"poll: the next week asks the pages this round has not offered yet: {tg4.asked[2]}")
# the poll open at the deploy (18 Nov 2026): closing it marks its options as offered
first = alerts.Watcher.__new__(alerts.Watcher)
tg5 = PollTG()
first.outlets, first.save_state = [tg5], (lambda: None)
first.state = {"poll": {"open": {"ids": ["a", "b", "c", "d"], "at": WED - 7 * 86400, "msg": 3}}, "deepdives": {"posts": pages}}
asyncio.run(first.close_poll(WED - 5 * 86400))
asyncio.run(first.maybe_poll(WED))
check(tg5.asked == [["E", "F", "G", "H"]], f"poll: the options of the poll open at the deploy are not asked again: {tg5.asked}")
cands = alerts.page_candidates([{"on": "x", "tag": "Load", "html": "x", "major": {"id": "load", "title": "New: Testnet load", "text": "How hard.", "link": "/load/"}},
                                {"on": "x", "tag": "Blog", "html": "x", "major": {"id": "b", "title": "An article", "link": "/blog/?p=x"}},
                                {"on": "x", "tag": "Sim", "html": "x", "major": {"id": "s", "title": "Sim", "link": "/?mode=sim"}},
                                {"on": "x", "tag": "Gazette", "html": "x", "major": {"id": "g", "title": "New: paper", "link": "/gazette/", "skip": "by hand"}},
                                {"on": "x", "tag": "Load", "html": "x", "major": {"id": "load2", "title": "Load again", "link": "/load/"}}])
check([(c["id"], c["title"]) for c in cands] == [("page-load", "Testnet load")],
      f"new pages from the log: one per page, its first announcement, no article, no front page, nothing skipped: {cands}")

# costs
# a fixed list (the real assets/costs.json changes with every bill): one euro bill, one dollar bill, one not in yet
costs = {"items": [{"t": "Server", "amount": 6, "cur": "EUR"}, {"t": "AI assistant", "amount": 200, "cur": "USD"},
                   {"t": "Voices", "amount": None, "cur": "USD"}]}
c = alerts.costs_text(costs, {"count": 1, "donors": 1, "totals": {"AGRS": "50"}})
check("About €6 + $200 a month" in c and "not in yet: Voices" in c and "50 AGRS" in c and "not run by IDNI" in c,
      "costs: billed items summed per currency, open bills named, donations")
check(alerts.costs_text({"items": [{"t": "x", "amount": None, "cur": "EUR"}]}, None) is None, "no bill in: no post")
usage = {"since": "2026-11-07", "months": {"2026-11": {"pictures": 12, "looks": 3, "usd": 1.234}}}
c = alerts.costs_text(costs, None, usage, "2026-11")
check("Pictures (Google Gemini) in November: about $1.23 for 12 pictures, measured since 7 November" in c and "$201.23" in c,
      "costs: last month's measured Gemini pictures listed and added to the dollars")
c = alerts.costs_text(costs, None, {"since": "2026-11-07", "months": {}}, "2026-12")
check("Pictures (Google Gemini) in December: $0, nothing painted" in c and "$200 a month" in c, "costs: a month without painting says $0")
c = alerts.costs_text(costs, None, None, "2026-11")
check("Gemini" not in c, "costs: no usage file, no Gemini line")
check("Gemini" not in alerts.costs_text(costs, None, usage, "2026-10"), "costs: no line for a month before measuring began")
c = alerts.costs_text(costs, None, usage, "2026-11", {"usd": 2.5, "answers": 40, "since": "2026-11-07", "by": {}})
check("AI writing (Anthropic API: blog, IDNI news, chat check) in November: about $2.50 for 40 answers, measured since 7 November" in c
      and "$203.73" in c, "costs: last month's measured Anthropic answers listed and added to the dollars")
check("Anthropic" not in alerts.costs_text(costs, None, None, "2026-11", None), "costs: nothing measured, no Anthropic line")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

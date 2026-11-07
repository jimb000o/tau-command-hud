"""Unit test of the channel's self-tuning parts (7 November 2026, no network): links carry ref=tg-<kind>, the Sunday
note counts opens per kind and makes a kind nobody opens post every other time, the weekly poll picks the next closer
look, the monthly costs post adds up only the bills that are in.

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

# costs
costs = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "costs.json")))
c = alerts.costs_text(costs, {"count": 1, "donors": 1, "totals": {"AGRS": "50"}})
check("About €6 + $200 a month" in c and "not in yet: Voices" in c and "50 AGRS" in c and "not affiliated with IDNI" in c,
      "costs: billed items summed per currency, open bills named, donations")
check(alerts.costs_text({"items": [{"t": "x", "amount": None, "cur": "EUR"}]}, None) is None, "no bill in: no post")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

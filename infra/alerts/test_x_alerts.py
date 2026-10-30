"""Unit test of the X side (no network): every X text fits 280 as X counts it, carries no link unless X_LINKS, the
daily cap holds, and an X failure never holds up or repeats a Telegram post.

Run: python test_x_alerts.py   (needs websockets==15.0.1)
"""
import asyncio
import os
import re
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="", X_DAILY_CAP="2",
                  X_MONTHLY_CAP="100")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


class Fake(alerts.Outlet):
    def __init__(self, name, fail=False):
        self.name, self.sent, self.fail = name, [], fail

    def enabled(self):
        return True

    def send_text(self, text, *_):
        if self.fail:
            return False, None, "HTTP 503"
        self.sent.append(text)
        return True, None, ""


long_why = "This is a long sentence about why the change matters to everyone who uses the chain. " * 8
texts = {
    "rule": alerts.x_text({"kind": "agreed", "headline": "Users agreed: the base fee goes from 20 to 30", "why": long_why,
                           "link": "https://tauhud.com/proposals/"}),
    "node": alerts.newnode_x({"kind": "peer", "id": "12D3KooWabcdef", "for": 5400, "head": 123456}, 3),
    "kit": alerts.newnode_x({"kind": "kit", "name": "Lisbon", "for": 3600}, 4),
    "today": alerts.today_x({"end": 1_800_000_000, "blocks": 10800, "pace": 8, "txs": 12, "senders": 3, "practice": 2,
                             "events": ["Users agreed: " + "a very long rule title " * 10], "online": 2,
                             "coming": [{"title": "Fee change", "at": 130000, "eta": " (in about 2 hours)"}]}),
    "major": alerts.major_x({"title": "New: The Daily Consensus", "text": long_why, "link": "/gazette/"}),
    "catchup": alerts.catchup_x([{"title": f"New: page number {i} with a fairly long name"} for i in range(20)]),
    "sim": alerts.sim_x(alerts.sim_switches(1_800_000_000)[0]),
    "zh": alerts.x_post(["⛓ 测试网" * 40, "第二行"]),
}
# the Monday post: the new Daily Consensus first, the week's numbers after it
alerts.recap.lines = lambda r, site: ["10,800 blocks, one every 8 seconds", "12 transactions from 3 accounts", "2 rule changes"]
alerts.recap.period = lambda r: "26 Oct – 2 Nov"
week = {"end": 1793606400}   # Mon 2 Nov 2026 08:00 UTC
os.makedirs(os.path.join(TMP, "recap", "gazette"))
texts["recap"] = alerts.recap_x(week)
check(texts["recap"].startswith("📊 Tau testnet weekly recap") and alerts.recap_caption(week).startswith("⛓"), "no edition today: the recap alone")
with open(os.path.join(TMP, "recap", "gazette", "latest.json"), "w") as f:
    import json
    json.dump({"no": 2, "date": "2026-11-02", "banner": {"en": "A vote of the users becomes law"},
               "teaser": {"en": long_why}}, f)
texts["paper"] = alerts.recap_x(week)
cap = alerts.recap_caption(week)
check(texts["paper"].startswith("📰 The Daily Consensus No. 2 is out\n\n“A vote of the users becomes law”"), "Monday on X: the paper first")
check(cap.startswith("📰 <b>THE DAILY CONSENSUS · No. 2 is out</b>") and "/gazette/" in cap and "• 12 transactions" in cap
      and len(re.sub(r"<[^>]+>", "", cap)) <= 1024, "Monday on Telegram: the paper, its link, the week, within a photo caption")
for k, t in texts.items():
    check(alerts.x_len(t) <= 280, f"{k}: {alerts.x_len(t)} of 280 as X counts it")
    check("http" not in t and "tauhud.com/" not in t, f"{k}: no link (a link costs $0.20 instead of $0.015)")
    check(t.endswith("#TauNet $AGRS") and re.findall(r"#[A-Za-z]\w*", t) == ["#TauNet"] and t.count("$AGRS") == 1, f"{k}: ends with #TauNet $AGRS, once, no other tags")
    check("\n\n" in t and not t.startswith(alerts.X_REAL), f"{k}: headline first, parts apart")
check(texts["rule"].startswith("✅ Users agreed: the base fee goes from 20 to 30\n\n"), "rule: headline first, then a blank line")
check(texts["rule"].endswith(alerts.X_REAL + " · #TauNet $AGRS"), "rule: closes with where it comes from and the hashtag")
check("• 10,800 blocks, one every 8 seconds\n• 12 transactions" in texts["today"], "today: list lines stay together")
check("…" not in texts["rule"].split("\n")[2] or texts["rule"].count(".") >= 1, "rule: why shortened by sentences")
check(texts["sim"].startswith(alerts.X_SIM_LINE), "sim: marked as simulation first")
check(alerts.X_SITE_NOTE in texts["major"], "major: says it is a website update, not testnet news")
check(texts["sim"].endswith(alerts.X_SIM_FOOT + " · #TauNet $AGRS"), "sim: marked as simulation last too")
check(alerts.item_picture({"kind": "agreed", "id": "ab12cd34ef"}).endswith("/og/proposal/ab12cd34ef.png"), "rule change: its own card")
check(alerts.item_picture({"kind": "restart", "id": None}).endswith("/og/hud.png"), "restart: the live overview")
check(alerts.x_len("🧪 a https://example.com/very/long/path") == 2 + 3 + 23, "x_len: emoji 2, link 23")

m = alerts.major_item({"on": "2026-10-30", "html": "x", "major": {"id": "a", "title": "New: A", "link": "/a/", "image": "/assets/shots/a.png"}})
check(alerts.major_picture(m) == alerts.SITE + "/assets/shots/a.png", "major: its screenshot from the update log goes under the X post")
alerts.page_picture = lambda link: None
check(alerts.major_picture(alerts.major_item({"on": "x", "html": "x", "major": {"id": "b", "link": "/b/"}})) == alerts.SITE + "/og.png",
      "major without a screenshot: the site's picture")

alerts.X_LINKS = True
t = alerts.x_text({"kind": "agreed", "headline": "h", "why": "w", "link": "https://tauhud.com/proposals/"})
check(t.endswith("https://tauhud.com/proposals/ · #TauNet $AGRS"), "X_LINKS=true puts the link back")
alerts.X_LINKS = False


async def main():
    tg, x = Fake("telegram"), Fake("x")
    w = alerts.Watcher([tg, x])
    now = 1_800_000_000.0
    for i in range(3):
        await w.post_x(f"post {i}", f"test {i}", now)
    check(x.sent == ["post 0", "post 1"], "daily cap of 2 holds")
    await w.post_x("next day", "test", now + 86400)
    check(x.sent[-1] == "next day", "a new day opens the cap again")

    # deliver: an item over the cap is marked skip on X and still posted on Telegram
    w.x_room()  # today's counters, as deliver sees them
    w.state["x"]["today"] = 99
    w.state["outlets"] = {"telegram": {"since": 0}, "x": {"since": 0}}
    w.state["items"] = [{"key": "k", "kind": "agreed", "headline": "h", "why": "w", "body": "b", "link": alerts.SITE,
                         "seen": now, "news": True, "posted": {}}]
    tg.send = lambda it: (tg.sent.append("item"), (True, None, ""))[1]
    x.send = lambda it: (x.sent.append("item"), (True, None, ""))[1]
    await w.deliver()
    check(w.state["items"][0]["posted"] == {"telegram": "ok", "x": "skip"}, "over the cap: Telegram posts, X skips")

    # a failing X never stops "Testnet today" on Telegram nor repeats it
    tg2, xbad = Fake("telegram"), Fake("x", fail=True)
    w2 = alerts.Watcher([tg2, xbad])
    w2.relay_json = lambda path: None
    w2.state["items"] = [{"seen": now - 10, "kind": "agreed", "headline": "Users agreed: fee 30", "id": "a"}]
    slot = now - now % 86400 + alerts.TODAY_HOUR * 3600
    await w2.maybe_today(slot + 60)
    await w2.maybe_today(slot + 120)
    check(len(tg2.sent) == 1, "testnet today: once on Telegram although X failed")


asyncio.run(main())
print("FAILED" if failed else "all X tests passed")
sys.exit(1 if failed else 0)

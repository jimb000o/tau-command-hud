"""Unit test of the news line's watchtower (no network): what leaves the line by age, what counts as new, which
problems it finds, when it tells the owner (new problem, reminder, all clear, never at night), the owner link's code.

Run: python test_tickerwatch.py
"""
import os
import sys
import tempfile
from datetime import datetime, timezone

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="123:test", TICKER_OWNER_CHAT="")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tickerwatch as tw  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


def at(day: str, hm: str = "12:00") -> float:
    return datetime.strptime(f"{day} {hm}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()


NOW = at("2026-11-20")
cfg = {"days": 14, "headlines": [
    {"text": "Old news", "href": "card/", "since": "2026-10-30"},
    {"text": "Fresh news", "href": "rules/", "since": "2026-11-18"},
    {"text": "Pointer", "href": "start/", "keep": True},
    {"text": "Over", "href": "x/", "since": "2026-11-19", "until": "2026-11-19T00:00:00Z"},
    {"text": "No date", "href": "y/"},
]}
updates = [{"on": "2026-10-30", "major": {"id": "a", "title": "Old feature", "link": "/a/"}},
           {"on": "2026-11-19", "major": {"id": "b", "title": "New feature", "link": "/b/"}},
           {"on": "2026-11-19", "major": {"id": "c", "title": "Same as a headline", "link": "/rules/"}},
           {"on": "2026-10-30", "major": {"id": "rabbit", "title": "The game", "link": "/rabbit/"}},
           {"on": "2026-11-19", "major": {"id": "roundup-1", "title": "Round-up", "link": "/"}}]
blog = [{"id": "p1", "on": "2026-11-07", "title": {"en": "Leaves soon"}}, {"id": "p2", "on": "2026-10-01", "title": {"en": "Long gone"}}]
pulse = {"generated_at": NOW - 600, "news_ai": "on", "news": [{"ts": NOW - 3 * 86400, "headline": {"en": "IDNI fix"}},
                                                             {"ts": NOW - 9 * 86400, "headline": {"en": "IDNI old"}}]}

ln = tw.line(cfg, updates, blog, pulse, NOW)
texts = lambda xs: [i["text"] for i in xs]
check(texts(ln["dated"])[0] in ("New feature",) and "Fresh news" in texts(ln["dated"]), "new items are on the line, newest first")
check("Old news" in texts(ln["gone"]) and "Old feature" in texts(ln["gone"]) and "Blog: Long gone" in texts(ln["gone"]), "older than 14 days: gone")
check("Over" in texts(ln["gone"]), "until passed: gone even when young")
check("Pointer" in texts(ln["standing"]) and "The game" in texts(ln["standing"]), "keep and the island game stay")
check(texts(ln["undated"]) == ["No date"], "a headline without since is undated")
check("Same as a headline" not in texts(ln["dated"]), "a feature with a headline's link is left out, as on the page")
check("Round-up" not in texts(ln["dated"] + ln["gone"]), "round-ups never go on the line")
check("Testnet: IDNI fix" in texts(ln["dated"]) and "Testnet: IDNI old" in texts(ln["gone"]), "IDNI news stays a week")
check(texts(ln["soon"]) == ["Blog: Leaves soon"], "what leaves within two days is named")

p = tw.problems(ln, pulse, NOW)
check(set(p) == {"undated"}, f"fresh line: only the undated headline is a problem ({sorted(p)})")
check(set(tw.problems(None, pulse, NOW)) == {"unread"}, "ticker.json unreadable")

later = at("2026-12-10")
ln2 = tw.line(cfg, updates, blog, pulse, later)
p2 = tw.problems(ln2, pulse, later)
check({"stale", "thin", "idni"} <= set(p2), f"three weeks on: stale, thin and IDNI's feed old ({sorted(p2)})")
check("every dated item has left" in p2["stale"], "stale says the line ran empty")
p3 = tw.problems(ln, {**pulse, "news_ai": "no key (NEWS_AI_KEY or CHAT_AI_KEY in infra/.env)"}, NOW)
check("idni" in p3 and "no key" in p3["idni"], "headline writer without key is a problem")
check("idni" not in tw.problems(ln, {**pulse, "news_ai": "waiting to retry after a failed try"}, NOW), "a retry wait is not")
check("idni" in tw.problems(ln, None, NOW), "devpulse.json missing")
stale_cfg = {"headlines": [{"text": "A", "since": "2026-11-01"}, {"text": "B", "since": "2026-11-02"}, {"text": "C", "since": "2026-11-03"}]}
ps = tw.problems(tw.line(stale_cfg, [], [], {**pulse, "news": []}, at("2026-11-11")), pulse, at("2026-11-11"))
check(set(ps) == {"stale"} and "8 days" in ps["stale"] and "“C”" in ps["stale"], f"nothing new for 8 days: stale, names the newest ({ps})")

# when to tell
check(tw.due({"stale": "x"}, {}, NOW), "a new problem is told")
check(not tw.due({"stale": "x"}, {"problems": {"stale": "x"}, "at": NOW - 3600}, NOW), "the same problem is not told again soon")
check(tw.due({"stale": "x"}, {"problems": {"stale": "x"}, "at": NOW - 49 * 3600}, NOW), "reminded after 48 hours")
check(tw.due({"stale": "x", "thin": "y"}, {"problems": {"stale": "x"}, "at": NOW - 60}, NOW), "a further problem is told at once")
check(tw.due({}, {"problems": {"stale": "x"}, "at": NOW}, NOW) and not tw.due({}, {"problems": {}}, NOW), "all clear once, after problems only")
check(tw.quiet(at("2026-11-20", "22:30")) and tw.quiet(at("2026-11-20", "05:00")) and not tw.quiet(at("2026-11-20", "09:00")),
      "quiet from 22:00 to 08:00 German time")
m = tw.message(p2, ln2, {}, later)
check(m.startswith("🗼 News line watchtower") and "⚠️" in m and "What helps" in m, "the warning says what helps")
check(tw.message({}, ln, {"stale": "x"}, NOW).startswith("🗼 News line watchtower: all fresh again"), "all clear message")
check(tw.message({}, ln, {}, NOW) is None, "nothing to say on a fresh line")

# the loop step tells the owner privately, once, and never without an owner
sent = []
tw.tg = lambda method, body: (sent.append((method, body)), {"ok": True})[1]
w = tw.Watch()
w.step(later, (cfg, updates, blog, pulse))
check(sent == [], "no owner yet: nothing sent")
tw.write_file(tw.OWNER_PATH, {"chat_id": 4242})
w = tw.Watch()
w.step(later, (cfg, updates, blog, pulse))
check(len(sent) == 1 and str(sent[0][1]["chat_id"]) == "4242" and sent[0][0] == "sendMessage", "told the owner's chat, not the channel")
w.step(later + 3600, (cfg, updates, blog, pulse))
check(len(sent) == 1, "not again an hour later")
night = at("2026-12-10", "23:00")
w2 = tw.Watch()
tw.write_file(tw.WATCH_PATH, {})
w2.step(night, (cfg, updates, blog, pulse))
check(len(sent) == 1, "nothing at night")
w2.next_at = 0
w2.step(at("2026-12-11", "08:30"), (cfg, updates, blog, pulse))
check(len(sent) == 2, "told in the morning instead")

# the owner link
o = tw.read_file(tw.OWNER_PATH)
code = tw.pair(NOW)
check(code and all(c.isalnum() for c in code), "the code fits a Telegram start link")
check(not tw.claim(99, "wrong", NOW) and not tw.claim(99, code, NOW + 31 * 60), "a wrong or late code is refused")
check(tw.claim(77, code, NOW + 60) and tw.owner() == "77", "the right code makes that chat the owner's")
check(not tw.claim(88, code, NOW + 120), "a code works once")

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

"""Unit test of the weekly testnet post (no network): numbers from the data handed in, blocks over every chain of the
week, a restart said with its cause unknown and, near a ship visit, that our own traffic is not ruled out; our automated
senders never counted as users; a draft that never publishes itself; one message a week to the owner from Sunday 18:00;
a translation with a number the English does not hold is left out.

Run: python test_testnet_week.py
"""
import os
import json
import re
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ.update(PUBLIC_DIR=TMP, BLOG_STATE=os.path.join(TMP, "blog.json"), NEWS_AI_KEY="", CHAT_AI_KEY="",
                  TELEGRAM_BOT_TOKEN="", TESTNET_WEEK="true", IDNI_REPORT_WEEKDAY="6", IDNI_REPORT_HOUR="18",
                  BLOG_AUTO_PUBLISH_HOURS="24", BLOG_ART=os.path.join(TMP, "no-art"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog  # noqa: E402
import testnet_week as w  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


MON = 1793574000                     # Monday 2 November 2026, 00:00 German time
SUN18 = MON + 6 * 86400 + 18 * 3600  # Sunday 8 November, 18:00
V = "2026-11-07-queen"
T0 = MON + 5 * 86400 + 13 * 3600     # Saturday 14:00 German time
log = [{"t": T0, "visit": V, "ship": "liner", "kind": "landed", "verdict": "calm", "plan": 300}]
log += [{"t": T0 + 10 + i * 16, "visit": V, "kind": "pay", "ok": True, "verdict": "calm", "height": 900 + i, "ms": 900} for i in range(200)]
log += [{"t": T0 + 3300 + i * 60, "visit": V, "kind": "pay", "ok": False, "err": None, "verdict": "calm"} for i in range(4)]
log.append({"t": T0 + 5400, "visit": V, "kind": "visit over", "summary": {"id": V, "name": "Queen Mempool", "t0": T0, "landed": True,
                                                                         "sent": {"pay": 200}, "refused": {"pay": 4}, "passengers": 80}})
hours = [[MON + i * 3600, 60, 60, 60 if i != 30 else 30] for i in range(6 * 24 + 18)]
uptime = {"hours": hours, "stall_seconds": 600, "incidents": [{"kind": "sync", "start": MON + 30 * 3600, "end": MON + 30 * 3600 + 1800, "max_lag": 9}],
          "restarts": [{"detected_at": T0 + 1000, "old_tip": 1457, "old_tip_ts": T0 + 900, "new_block1_ts": T0 + 1100},
                       {"detected_at": MON + 2 * 86400, "old_tip": 3000, "old_tip_ts": MON + 2 * 86400 - 60}],
          "reorgs": [], "stalls": []}
stats = {"blocks": [[1 + i, T0 + 1100 + i * 60, 1] for i in range(100)]}   # the current chain: only since the restart
fields = ["blocks", "txs", "transfer", "rule", "gov", "transfers", "volume", "gap_sum", "gap_n", "gap_max"]
hist = {"fields": fields, "hours": [[MON + i * 3600, 1 if i < 48 else (2 if i < 133 else 3), 60, 2, 0, 0, 0, 0, 0, 0, 0, 0]
                                    for i in range(6 * 24 + 18)] + [[MON - 3600, 1, 60, 99] + [0] * 8]}
src = {"days": {"2026-11-0%d" % d: {"agorzilla": [3, 1, 0, 1, 3], "tauhud": [2, 1, 0, 1, 2], "nomemo": [1, 1, 1, 0, 0],
                                    "idni": [100, 2, 0, 2, 0], "cruise": [30, 30, 0, 0, 0], "bot": [5, 1, 0, 1, 0]} for d in range(2, 9)}
       | {"2026-11-01": {"agorzilla": [999, 1, 0, 0, 0]}}}
raw = {"missing": [], "uptime": uptime, "health": {"expected_block_seconds": 60}, "stats": stats, "incidents": {"incidents": []},
       "visits": {V: log}, "pulse": None, "posts": [{"id": "testnet-week-2026-w44", "on": "2026-11-01", "title": {"en": "Last week"}},
                                                     {"id": "2026-11-07-queen-learnings", "on": "2026-11-07", "title": {"en": "The Queen stayed"}}],
       "node_log": {"lines": 3, "groups": [{}, {}]}, "history": hist, "sources": src, "cruise": {"enabled": False},
       "x": [{"account": "tauhud", "handle": "TauHUDcom", "headline": "Wallet walkers [live]", "url": "https://x.com/TauHUDcom/status/123", "at": T0},
             {"account": "tauhud", "handle": "TauHUDcom", "headline": "bad link", "url": "https://evil.example/x", "at": T0}]}

f = w.week_facts(raw, MON, SUN18)
e = w.text(f)
b = e["body"]
print(b)
check(f["week"] == {"blocks": 162 * 60, "txs": 162 * 2, "chains": 3}, "blocks and transactions over every chain of the week (history), not the current chain only")
check("9,720 blocks with 324 transactions, across 3 chains" in b and e["title"] == "Two restarts on the Tau Net testnet, 2–8 Nov 2026", "chain line and title")
check("2 chain restarts" in e["dek"] and "Counted from our public logs" in e["dek"], "dek")
check("## Chain restarts" in b and "we do not know what caused them" in b, "restarts: cause unknown")
check("1 of them came while one of our cruise ships was sending" in b and "not ruled out that our own traffic plays a part" in b,
      "a restart during a visit: our own traffic not ruled out")
check("ended at block 1457, during or shortly after the visit of our cruise ship Queen Mempool" in b, "the restart next to its visit")
check(b.count("during or shortly after") == 1, "the other restart is not tied to a ship")
check("Our cruise ships are paused for now." in b, "ships paused said")
check("- Users of [Agorzilla](https://agorzilla.com/): 21" in b and "- Users of [Tau HUD](/): 14" in b and "- Players in [No Memo](/nomemo/): 7" in b
      and "IDNI uses for testing (not counted as users): 700" in b and "999" not in b,
      "sources of this week's days only, labels as on the site")
check("Our own server sent 245 more" in b and "simulated passengers: 210" in b and "the island bot: 35" in b, "our automated senders counted apart")
check("Users of our apps sent 42 transactions" in e["why"][1] and e["stats"][2][:2] == ["42", "transactions by users of our apps"],
      "users: only our apps' users, never IDNI's testing or our own traffic; the tile reads as plain English")
check("Queen Mempool: 200 accepted, 0 refused, 4 sends our own node did not answer in time" in b and "cruise/log?visit=2026-11-07-queen" in b, "ship visit")
check("in sync 99.7%" in b and "fell more than 2 blocks behind 1 time, 30 min" in b and "3 warnings about syncing or peers, in 2 kinds" in b, "on our side")
check("The Queen stayed" in b and "Last week" not in b, "written up: this week's articles, not last week's post")
check("## On X this week" in b and "- @TauHUDcom: [Wallet walkers (live)](https://x.com/TauHUDcom/status/123)" in b and "evil" not in b,
      "On X this week: the week's posts linked, only x.com post addresses")
check("not run by IDNI" in b and "coins have no value" in b, "not affiliated, testnet note")
full = " ".join([e["title"], e["dek"], b, *e["why"], e["x"]])
check(not re.search(r"\b(fault|blame|broke|failed us|huge|exciting|finally|revolutionary|unstable|unreliable|matrix|uplink)\b|!", full, re.I), "no blame, hype or exclamation")
check("Kilian" not in full, "no names")
check(all(len(c) <= 64 for c in e["card"][:2]) and e["card"][0] == e["title"], "card fits")

quiet = dict(raw, uptime=dict(uptime, restarts=[]), cruise={"enabled": True})
q = w.text(w.week_facts(quiet, MON, SUN18))
check("On X" not in w.text(w.week_facts(dict(quiet, x=[]), MON, SUN18))["body"], "no X posts: no section")
check("## Chain restarts" not in q["body"] and "No chain restart this week" in q["why"][0] and "paused" not in q["body"], "a week without restarts")

tones = {t[1]: t[2] for t in e["stats"]}
check(tones == {"blocks this week": "ok", "chain restarts, cause not clear yet": "amber", "transactions by users of our apps": "amber", "our node in sync": "ok"},
      f"each tile's tone fits its number ({tones})")
check(w.text(w.week_facts(quiet, MON, SUN18))["stats"][1][2] == "ok", "no restart: a green tile")
check(f["visits"][0]["ship"] == "Queen Mempool" and f["visits"][0]["day"] == "Sat 7 Nov", "ship by its own name, day of the call")
raw_q = dict(raw, visits={V: log, "2026-11-01-dryrun": log})
check([v["id"] for v in w.week_facts(raw_q, MON, SUN18)["visits"]] == [V], "a call of the week before is left out")
w.CONTEXT["2026-w45"] = ["On 7 November IDNI said that an update is under way."]
fc = w.week_facts(raw, MON, SUN18)
check("IDNI said that an update is under way" in w.text(fc)["body"] and w.model_facts(fc)["said this week (by IDNI or by us, written down by hand)"],
      "what IDNI said this week, as said")
del w.CONTEXT["2026-w45"]
import blog_rules  # noqa: E402
check(all(blog.HYPE.search(t) for t in ("You cannot lose anything", "a risk-free way", "completely safe", "funds cannot be stolen", "guaranteed"))
      and not blog.HYPE.search("free test coins with no value; there is no guarantee"), "bold safety promises are marked, plain limits are not")
check("No bold safety promises" in blog_rules.RULES, "the rule is in the house rules")
check(blog_rules.RULES in w.WEEK_SYSTEM and blog_rules.RULES in blog.SYSTEM and "Natural spoken English" in blog_rules.RULES, "every writer gets the house rules")

# ---------- translations ----------
good = {lang: {"title": "T 2–8 Nov 2026", "dek": "D 9,720", "why": ["a", "b", "c"], "body": "B 42"} for lang in ("zh", "ja")}
bad = dict(good, ja={"title": "T 4242", "dek": "D", "why": ["a", "b", "c"], "body": "B"})
w.blog.AI_KEY = "k"
import json as _j  # noqa: E402


class R:
    def __init__(self, d):
        self.d = _j.dumps({"content": [{"type": "text", "text": _j.dumps(d, ensure_ascii=False)}], "usage": None}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, *a):
        return self.d


w.urllib.request.urlopen = lambda req, timeout=0: R(bad)
tr = w.translate(e)
check(set(tr) == {"zh"}, "a translation with a number the English does not hold is left out")
w.blog.AI_KEY = ""
check(w.translate(e) == {}, "no key: English only")

# ---------- the draft ----------
did = w.write_draft(f, "2026-w45", SUN18 + 60, tr)
st = blog.state()
a = blog.read_json(os.path.join(TMP, "blog", "drafts", st["drafts"][did] + ".json"), {})
check(did == "testnet-week-2026-w45" and blog.ID_RE.match(did), "stable id, one up blog publish takes")
check(a["status"] == "draft" and a["by_hand"] and a["kind"] == "week" and a["title"]["zh"] == "T 2–8 Nov 2026" and "ja" not in a["title"], "draft with zh, English for ja")
check(a["on"] == "2026-11-08" and a["kicker"].startswith("Testnet week"), "dated Sunday, its own kicker")
check(not blog.island_story(a), "the site's own picture, no island")
check(os.path.exists(os.path.join(TMP, "blog", "img", did + "-hero.jpg")) and a.get("image", "").endswith(did + "-hero.jpg"), "hero picture made")
check(blog.auto_publish(SUN18 + 3 * 86400) is None and not blog.posts()["posts"], "never on the blog by itself, even days later")
check("waits for your OK" in blog.auto_note(blog.state(), did, a), "up blog says it waits for the OK")
name = st["drafts"][did]
check(w.write_draft(f, "2026-w45", SUN18 + 600, {}) == did and blog.state()["drafts"][did] == name, "written anew: same address")

# publish by hand: on the blog, and the post carries the week's own numbers
sent = []
blog.announce = lambda a_, dry: sent.append(a_)
check(blog.publish_cli(did, False, False, now=SUN18 + 3600) == 0 and blog.posts()["posts"][0]["id"] == did, "published by hand")
check(sent and sent[0]["numbers"][0].startswith("9,720 blocks") and "cause unknown" in sent[0]["numbers"][1], "the post's numbers")
pub = blog.posts()["posts"][0]
check("by_hand" in pub and "status" not in pub and "check" not in pub, "published without draft fields")

# ---------- the model writes from the counted facts ----------
mf = w.model_facts(f)
mm = mf["what the numbers mean"]
check(mf["transactions by users of our apps, in all"] == 42 and mf["transactions by IDNI's genesis accounts (IDNI tests with them; not users)"] == 700,
      "facts for the writer: users apart from IDNI's testing")
check(mm["blocks the testnet's own pace would give in these hours"] == 9720 and mm["share of those blocks that were made"] == "100%", "meaning: blocks against the testnet's pace")
check(mm["restarts during or within an hour after one of our ship visits"] == 1 and mm["longest stretch without a restart, hours"] > 0, "meaning: restarts")
check(mm["share of all counted transactions by users of our apps"] == "4%", "meaning: users' share")
raw_b = dict(raw, history=dict(hist, hours=hist["hours"] + [[MON - 7 * 86400 + i * 3600, 1, 30, 1] + [0] * 8 for i in range(168)],
                               chains=[{"n": 1, "start": MON - 9 * 86400}, {"n": 2, "start": MON - 3 * 86400}]),
             sources=dict(src, days=dict(src["days"], **{"2026-10-28": {"agorzilla": [10, 1, 0, 0, 0]}})))
fb = w.week_facts(raw_b, MON, SUN18)
check(fb["before"] == {"blocks": 5100, "txs": 267, "hours": 169, "restarts": 1, "app txs": 1009}, "the week before: blocks, transactions, restarts, app users")
cb = w.model_facts(fb)["what the numbers mean"]["change against the week before"]
check(cb["blocks"] == "+4,620 (+91%)" and cb["chain restarts"] == "2 after 1" and cb["transactions by users of our apps"] == "-967 (-96%)", "change against the week before")
L3 = lambda t: {"en": t, "zh": t, "ja": t}
answer = {"title": L3("Two restarts reset the testnet this week"), "dek": L3("Balances went back to zero twice; users of our apps sent 42 transactions."),
          "why": [L3("Every wallet started again at zero."), L3("42 transactions by users of our apps."), L3("Cause unknown.")],
          "body": L3("## What the week meant\n\nThe chain started over 2 times and made 9,720 blocks, 100% of its pace. 77 more."),
          "x": "Two restarts this week.", "card": {"line": "Balances went back to zero twice", "why": ["a", "b", "c"]}}
seen = []
did2 = w.write_draft(fb, "2026-w45", SUN18 + 900, ask_=lambda facts: (seen.append(facts) or answer))
a2 = blog.read_json(os.path.join(TMP, "blog", "drafts", blog.state()["drafts"][did2] + ".json"), {})
check(seen and "what the numbers mean" in seen[0], "the model gets the facts with their meaning")
check(a2["title"]["en"] == "Two restarts reset the testnet this week" and a2["model"] != "script", "the model's article")
check(a2["check"]["unknown_numbers"] == ["77"], f"a number not in the facts is marked ({a2['check']['unknown_numbers']})")
check("## On X this week" in a2["body"]["en"] and "## 本周在 X 上" in a2["body"]["zh"] and "not run by IDNI" in a2["body"]["en"], "link lists and the closing line in every language")
check(a2["stats"][2][:2] == ["42", "transactions by users of our apps"] and a2["numbers"][0].startswith("9,720 blocks"), "tiles and post numbers stay the script's")
figs = {os.path.basename(x["src"]): x for x in a2.get("figures") or []}
check(set(figs) == {did2 + "-days.png", did2 + "-sources.png", did2 + "-before.png"} and all(os.path.exists(os.path.join(TMP, "blog", "img", k)) for k in figs),
      "three charts: blocks per day, where transactions came from, the week before")
check(figs[did2 + "-sources.png"]["link"] == "/meta/" and figs[did2 + "-days.png"]["after"] == 99 and figs[did2 + "-days.png"]["caption"]["zh"], "charts link their live page, captions in three languages")
w.blog.AI_KEY = ""
check(w.write_draft(fb, "2026-w45", SUN18 + 950, ask_=lambda facts: {"title": {}}) == did2
      and "Every Sunday we write down" in blog.read_json(os.path.join(TMP, "blog", "drafts", blog.state()["drafts"][did2] + ".json"), {})["body"]["en"],
      "a broken answer: the script's text instead")

# ---------- the second read against our rules ----------
import editor  # noqa: E402
reply = {"content": [{"type": "text", "text": json.dumps({"notes": [{"quote": "transactions, our test traffic not counted", "rule": 8,
                                                                     "fix": "transactions by users of our apps"}, {"quote": "x", "fix": ""}]})}]}
notes = editor.review(a2, post=lambda body: (check("Tau Net" in body["system"] and "TITLE: " in body["messages"][0]["content"], "editor reads the draft with our rules") or reply))
check(notes == [{"quote": "transactions, our test traffic not counted", "rule": 8, "fix": "transactions by users of our apps"}], "editor: notes kept, empty ones dropped")
check(editor.lines({"editor": notes})[1].startswith("Second read against our rules, 1 note") and editor.lines({"editor": []})[1].endswith("nothing to change.")
      and editor.lines({}) == [], "editor lines for the owner")
check(editor.review(a2) == [], "no key: no notes")
st_ = blog.state()
p2 = os.path.join(TMP, "blog", "drafts", st_["drafts"][did2] + ".json")
ship = dict(blog.read_json(p2, {}), id="2026-11-07-queen-learnings", by_hand=False, editor=notes)
st_["drafts"]["2026-11-07-queen-learnings"] = "q-1"
st_["drafted_at"]["2026-11-07-queen-learnings"] = SUN18 - 3 * 86400
blog.write_json(os.path.join(TMP, "blog", "drafts", "q-1.json"), ship)
blog.write_json(blog.STATE, st_)
check(blog.auto_publish(SUN18) is None and "second read" in blog.auto_note(blog.state(), "2026-11-07-queen-learnings", ship), "a draft with editor notes never publishes itself")

# ---------- once a week to the owner ----------
told = []
import tickerwatch  # noqa: E402
tickerwatch.tell = lambda text: (told.append(text) or (True, ""))
w.gather = lambda a_, b_: raw
check(w.step(SUN18 - 3600) is None and not told, "not before Sunday 18:00")
check(w.step(SUN18 + 60) == "testnet-week-2026-w45" and len(told) == 1, "Sunday 18:01: draft and one message")
m = told[0]
check("/blog/?draft=testnet-week-2026-w45-" in m and 'git pull && sh infra/up.sh blog publish testnet-week-2026-w45"' in m
      and m.count("ssh root@node.tauhud.com \"cd /opt/tau-command-hud && git pull") == 2, "message: read link and the full publish line")
check("https://tauhud.com/blog/?p=testnet-week-2026-w45" in m and "github.com/IDNI" not in m and len(m) < 4000, "message: the address, no issue link")
check(w.step(SUN18 + 1200) is None and len(told) == 1, "not twice")
check(w.step(SUN18 + 7 * 86400 + 60) == "testnet-week-2026-w46" and len(told) == 2, "next Sunday again")
check(w.status_lines(SUN18 + 7 * 86400 + 120)[0].startswith("week:    weekly testnet post as a draft for you Sun 22.11. 18:00"), "status: next one a week later")
check(w.main(["bogus"]) == 2, "unknown argument: usage")

# ---------- only the picture made anew; the owner's time to publish ----------
W46 = "testnet-week-2026-w46"
pw = os.path.join(TMP, "blog", "drafts", blog.state()["drafts"][W46] + ".json")
d0 = blog.read_json(pw, {})
d0["stats"] = [list(x) for x in d0.get("stats") or []] + [["3", "chain restarts, cause not clear yet", "bad"]]   # as drafted before the amber rule
blog.write_json(pw, d0)
check(w.main(["repaint"]) == 0, "repaint: the last week drafted")
d1 = blog.read_json(pw, {})
check([x for x in d1["stats"] if "restart" in x[1]][-1][2] == "amber" and d1["body"] == d0["body"] and d1["title"] == d0["title"]
      and os.path.exists(os.path.join(TMP, "blog", "img", W46 + "-hero.jpg")), "repaint: restarts amber, the text word for word as before")
check(w.restart_tone(0) == "ok" and w.restart_tone(3) == "amber", "restarts: green with none, amber with any, never red")
NOW = SUN18 + 7 * 86400 + 300
AT = blog.publish_at("2026-11-23T08:00Z")
check(AT == 1795420800 and blog.publish_at("2026-11-23 08:00") == AT and blog.publish_at("tomorrow") is None, "--at reads a UTC time")
check(blog.schedule_cli(W46, "2026-11-01T08:00Z", now=NOW) == 1 and blog.schedule_cli("testnet-week-2026-w99", "2026-11-23T08:00Z", now=NOW) == 1,
      "no time in the past, no unknown draft")
check(blog.schedule_cli(W46, "2026-11-23T08:00Z", now=NOW) == 0 and blog.state()["publish_at"][W46] == AT, "the time is kept")
check("goes up by itself Mon 23.11. 08:00 UTC" in blog.auto_note(blog.state(), W46, d1), "the drafts list says when")
sent = []
blog.announce = lambda a, dry: sent.append(a["id"])
told.clear()
check(blog.scheduled_publish(AT - 60) == [] and not sent and W46 not in {x["id"] for x in blog.posts()["posts"]}, "not before its time")
check(blog.scheduled_publish(AT + 30) == [W46] and sent == [W46] and W46 in {x["id"] for x in blog.posts()["posts"]}
      and told and told[-1].startswith("Published at the set time: " + W46), "at its time: on the blog, its one post, the owner told")
check(blog.scheduled_publish(AT + 700) == [] and sent == [W46] and not blog.state()["publish_at"], "once")
check(blog.schedule_cli(did2, "2026-12-01T08:00Z", now=NOW) == 0 and blog.schedule_cli(did2, "off", now=NOW) == 0
      and did2 not in blog.state()["publish_at"], "--at=off takes the time back")

print("\n" + ("all ok" if not failed else f"{failed} failed"))
sys.exit(1 if failed else 0)

"""Unit test of the weekly testnet post (no network): numbers from the data handed in, blocks over every chain of the
week, a restart said with its cause unknown and, near a ship visit, that our own traffic is not ruled out; our automated
senders never counted as users; a draft that never publishes itself; one message a week to the owner from Sunday 18:00;
a translation with a number the English does not hold is left out.

Run: python test_testnet_week.py
"""
import os
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
       "node_log": {"lines": 3, "groups": [{}, {}]}, "history": hist, "sources": src, "cruise": {"enabled": False}}

f = w.week_facts(raw, MON, SUN18)
e = w.text(f)
b = e["body"]
print(b)
check(f["week"] == {"blocks": 162 * 60, "txs": 162 * 2, "chains": 3}, "blocks and transactions over every chain of the week (history), not the current chain only")
check("9,720 blocks with 324 transactions, across 3 chains" in b and e["title"] == "The Tau Net testnet this week, 2–8 Nov 2026", "chain line and title")
check("2 chain restarts" in e["dek"] and "Counted from our public logs" in e["dek"], "dek")
check("## Chain restarts" in b and "we do not know what caused them" in b, "restarts: cause unknown")
check("1 of them came while one of our cruise ships was sending" in b and "not ruled out that our own traffic plays a part" in b,
      "a restart during a visit: our own traffic not ruled out")
check("ended at block 1457, during or shortly after the visit of our cruise ship Queen Mempool" in b, "the restart next to its visit")
check(b.count("during or shortly after") == 1, "the other restart is not tied to a ship")
check("Our cruise ships are paused for now." in b, "ships paused said")
check("- Agorzilla: 21" in b and "- Tau HUD: 14" in b and "- players in No Memo: 7" in b and "IDNI): 700" in b and "999" not in b,
      "sources of this week's days only, labels as on the site")
check("Our own server sent 245 more" in b and "simulated passengers: 210" in b and "the island bot: 35" in b, "our automated senders counted apart")
check("742 transactions came from wallets" in e["why"][1] and "our test traffic not counted" in e["stats"][2][1], "users never include our own traffic")
check("Queen Mempool: 200 accepted, 0 refused, 4 sends our own node did not answer in time" in b and "cruise/log?visit=2026-11-07-queen" in b, "ship visit")
check("in sync 99.7%" in b and "fell more than 2 blocks behind 1 time, 30 min" in b and "3 warnings about syncing or peers, in 2 kinds" in b, "on our side")
check("The Queen stayed" in b and "Last week" not in b, "written up: this week's articles, not last week's post")
check("not affiliated with IDNI" in b and "coins have no value" in b, "not affiliated, testnet note")
full = " ".join([e["title"], e["dek"], b, *e["why"], e["x"]])
check(not re.search(r"\b(fault|blame|broke|failed us|huge|exciting|finally|revolutionary|unstable|unreliable|matrix|uplink)\b|!", full, re.I), "no blame, hype or exclamation")
check("Kilian" not in full, "no names")
check(all(len(c) <= 64 for c in e["card"][:2]) and e["card"][0] == e["title"], "card fits")

quiet = dict(raw, uptime=dict(uptime, restarts=[]), cruise={"enabled": True})
q = w.text(w.week_facts(quiet, MON, SUN18))
check("## Chain restarts" not in q["body"] and "No chain restart this week" in q["why"][0] and "paused" not in q["body"], "a week without restarts")

# ---------- translations ----------
good = {lang: {"title": "T 2–8 Nov 2026", "dek": "D 9,720", "why": ["a", "b", "c"], "body": "B 742"} for lang in ("zh", "ja")}
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

print("\n" + ("all ok" if not failed else f"{failed} failed"))
sys.exit(1 if failed else 0)

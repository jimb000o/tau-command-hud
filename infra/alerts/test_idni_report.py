"""Unit test of the weekly report for IDNI (no network): every number from the data handed in, our own trouble under
"On our side", no blame or hype words, the not-affiliated line, the pre-filled link fits and carries the text, the
page, one message a week to the owner from Sunday 18:00 German time, nothing filed.

Run: python test_idni_report.py
"""
import json
import os
import re
import sys
import tempfile
import urllib.parse

TMP = tempfile.mkdtemp()
os.environ.update(PUBLIC_DIR=TMP, BLOG_STATE=os.path.join(TMP, "blog.json"), NEWS_AI_KEY="", CHAT_AI_KEY="",
                  TELEGRAM_BOT_TOKEN="", IDNI_REPORT="true", IDNI_REPORT_WEEKDAY="6", IDNI_REPORT_HOUR="18")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog  # noqa: E402
import idni_report as r  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


MON = 1793574000                     # Monday 2 November 2026, 00:00 German time
SUN18 = MON + 6 * 86400 + 18 * 3600  # Sunday 8 November, 18:00
check(blog.local(MON).strftime("%a %H:%M") == "Mon 00:00" and blog.local(SUN18).strftime("%a %H:%M") == "Sun 18:00", "week bounds in German time")
t0, t1, wid = r.week_of(SUN18)
check((t0, t1, wid) == (MON, SUN18, "2026-w45"), "this week: Monday 00:00 to now, id 2026-w45")
check(r.week_of(SUN18 + 86400, last=True)[:2] == (MON, MON + 7 * 86400), "last week: Monday to Monday")

# ---------- a week of data ----------
hours = [[MON + i * 3600, 60, 60 if i != 30 else 40, 60 if i not in (30, 31) else 20] for i in range(6 * 24)]
uptime = {"hours": hours, "stall_seconds": 600,
          "incidents": [{"kind": "node", "start": MON + 30 * 3600, "end": MON + 30 * 3600 + 1200},
                        {"kind": "sync", "start": MON + 31 * 3600, "end": MON + 31 * 3600 + 2400, "max_lag": 1609},
                        {"kind": "node", "start": MON - 5 * 86400, "end": MON - 5 * 86400 + 60}],     # the week before: left out
          "restarts": [{"detected_at": MON + 4 * 86400 + 19 * 3600, "old_tip": 6123}],
          "reorgs": [], "stalls": [{"after": 5028, "start": MON + 3600, "end": MON + 3600 + 1500}]}
health = {"expected_block_seconds": 60, "hours": [[MON + i * 3600, 86.0, 68 if i == 100 else 80] for i in range(144)],
          "known_issues": [{"id": "IDNI #81", "count": 3, "url": "https://github.com/IDNI/tau-testnet/issues/81"}]}
stats = {"blocks": [[5000 + i, MON + 600 + i * 60, 2 if i % 3 else 0] for i in range(2000)] + [[1, MON - 10, 9]],
         "dropped": [{"left": MON + 7200}, {"left": MON - 100}]}
V = "2026-11-04-dryrun"
T0 = 1793804400
log = [{"t": T0, "visit": V, "ship": "dryrun", "kind": "landed", "verdict": "calm", "plan": 247}]
log += [{"t": T0 + 10 + i * 16, "visit": V, "kind": "pay", "ok": True, "verdict": "calm", "height": 5500 + i, "ms": 900} for i in range(122)]
log += [{"t": T0 + 700 + i * 160, "visit": V, "kind": "pay", "ok": False, "err": None, "verdict": "calm"} for i in range(8)]
log += [{"t": T0 + 900, "visit": V, "kind": "bill", "ok": False, "err": "insufficient balance for 0123456789abcdef0123", "verdict": "calm"}]
log.append({"t": T0 + 2041, "visit": V, "kind": "left", "verdict": "refused", "note": "the node refused 5 of the last 20 passenger transactions"})
log.append({"t": T0 + 5400, "visit": V, "kind": "visit over", "summary": {"id": V, "name": "MS Dry Run", "t0": T0, "landed": True,
                                                                         "sent": {"pay": 122}, "refused": {"pay": 8, "bill": 1}, "passengers": 40}})
raw = {"missing": [], "uptime": uptime, "health": health, "stats": stats, "incidents": {"incidents": []}, "visits": {V: log, "2026-10-31-queen": []},
       "pulse": {"sync": {"testnet": {"pin": "64ceb4046253", "head": "668fbf4aaaa", "ahead": 18},
                          "patches": {"ok": True, "sha": "668fbf4aaa", "results": [{"ok": True}] * 7}}},
       "posts": [{"id": "2026-11-04-dryrun-learnings", "on": "2026-11-06", "title": {"en": "The MS Dry Run left early. Here is what we learned."}},
                 {"id": "old", "on": "2026-10-20", "title": {"en": "Old"}}]}
f = r.facts(raw, MON, SUN18)
b = r.body(f)
print(b)
check(f["blocks"]["count"] == 2000 and f["blocks"]["txs"] == sum(2 for i in range(2000) if i % 3), "blocks and transactions of the week only")
check("2,000 blocks (#5000 to #6999)" in b and "typically 60 s" in b, "blocks line")
check("1 pause of more than 10 minutes" in b and "after #5028" in b and "25 min" in b, "the pause, with height and length")
check("Chain restarts seen (a new block 1): 1" in b and "old tip #6123" in b, "the restart")
check("Reorgs seen: 0" in b and "No reorg seen." in b, "no reorgs, credited")
check("still listed as waiting" in b and ": 3 (#81)" in b, "IDNI #81 ghosts")
check("average 86, lowest 68" in b, "health score")
check("The node accepted 122 of our test transactions and refused 1." in b, "credit: accepted, the real refusal")
on = b.split("### On our side")[1].split("###")[0]
check("did not answer our relay 1 time, 20 min" in on, "our node outage under our side (only this week's)")
check("more than 2 blocks behind the network 1 time, 40 min in all, at most 1609 blocks" in on, "behind, with the relay's count")
check("8 of our ships' sends got no answer from our own node" in on and "not refusals" in on, "timeouts named as ours")
check("answered 99.8%" in on and "in sync 99.1%" in on and "8,640 checks" in on, "availability from the minute checks")
check("MS Dry Run: 122 accepted, 1 refused, 8 timeouts on our side" in b and "median 0.9 s" in b and "left after 34 of 90" in b, "the ship visit")
check("refused 1x: `insufficient balance for …`" in b, "the node's refusal answer, ids shortened")
check("Queen" not in b, "an empty visit is left out")
check("tau-testnet 64ceb40 plus 7 small patches" in b and "18 commits ahead (668fbf4), and all our patches apply" in b, "our node's version")
check("The MS Dry Run left early" in b and "Old" not in b.split("### Written up")[1], "this week's article only")
check(b.startswith(r.NOT_AFFILIATED) and b.rstrip().endswith("_" + r.NOT_AFFILIATED + "_"), "not affiliated, first and last")
check(not re.search(r"\b(fault|blame|broke|failed us|huge|exciting|finally|revolutionary|matrix)\b|!", b, re.I), "no blame, hype or exclamation")
check("Kilian" not in b and "manksi" not in b, "no names")
check(r.title(f) == "Weekly report from a community node, 2–8 Nov 2026", "title")

# ---------- the link and the page ----------
t, body, url = r.fitted(f)
q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
check(url.startswith("https://github.com/IDNI/tau-testnet/issues/new?") and q["title"] == [t] and q["body"] == [body], "pre-filled link carries title and text")
check(len(url) <= r.URL_MAX, f"link fits ({len(url)} characters)")
big = dict(f, visits=f["visits"] * 30, stalls=f["stalls"] * 40)
t2, b2, u2 = r.fitted(big)
check(len(u2) <= r.URL_MAX and "refused 1x" not in b2, "a long week is shortened until the link fits")
st = r.state()
out = r.write(f, wid, st)
page = open(os.path.join(TMP, "idni-report", os.path.basename(out["page"]))).read()
check(out["page"].startswith("https://node.tauhud.com/idni-report/2026-w45-") and "noindex" in page and "Open the pre-filled issue" in page, "unlisted page with the button")
check("Not filed yet" in page and "&lt;" not in body, "page says nothing is filed")
check(r.write(f, wid, r.state())["page"] == out["page"], "same page address for the same week")

# ---------- once a week to the owner ----------
told = []
import tickerwatch  # noqa: E402
tickerwatch.tell = lambda text: (told.append(text) or (True, ""))
r.gather = lambda a, b: raw
check(r.step(SUN18 - 3600) is None and not told, "not before Sunday 18:00")
check(r.step(SUN18 + 60) == "2026-w45" and len(told) == 1, "Sunday 18:01: told once")
check("https://node.tauhud.com/idni-report/2026-w45-" in told[0] and 'up.sh report"' in told[0] and "ssh root@node.tauhud.com" in told[0], "message: page and the full command")
check(len(told[0]) < 4000 and "github.com/IDNI" not in told[0], "message is short, the long link stays on the page")
check(r.step(SUN18 + 1200) is None and len(told) == 1, "not twice")
check(r.step(SUN18 + 7 * 86400 + 60) == "2026-w46" and len(told) == 2, "next Sunday again")
check(r.status_lines(SUN18 + 7 * 86400 + 120)[0].startswith("report:  weekly IDNI report to your Telegram Sun 22.11. 18:00"), "status: next one a week later")
check(r.main(["bogus"]) == 2, "unknown argument: usage")

print("\n" + ("all ok" if not failed else f"{failed} failed"))
sys.exit(1 if failed else 0)

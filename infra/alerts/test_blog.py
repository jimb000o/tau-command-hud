"""Unit test of the blog drafts (no network): a logbook like the MS Dry Run's of 4 November 2026 is counted into facts,
a made-up model answer becomes a draft, numbers the facts do not hold are marked, nothing is published by itself, and
publishing puts the article on the blog once without the internal check fields.

Run: python test_blog.py
"""
import json
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ.update(PUBLIC_DIR=TMP, BLOG_STATE=os.path.join(TMP, "state.json"), NEWS_AI_KEY="test", CHAT_AI_KEY="",
                  TELEGRAM_BOT_TOKEN="", X_API_KEY="")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T0 = 1793804400   # Wednesday 4 November 2026, 16:00 German time
V = "2026-11-04-dryrun"
log = [{"t": T0, "visit": V, "ship": "dryrun", "kind": "landed", "verdict": "calm", "plan": 247, "trial": ["book"]}]
for i in range(122):
    log.append({"t": T0 + 10 + i * 16, "visit": V, "kind": "pay" if i % 25 else "book", "ok": True, "verdict": "strained" if i > 7 else "calm", "height": 5500 + i})
for i in range(8):
    log.append({"t": T0 + 700 + i * 160, "visit": V, "kind": "pay", "ok": False, "err": None, "verdict": "strained"})
log.append({"t": T0 + 2041, "visit": V, "kind": "left", "verdict": "refused", "note": "the node refused 5 of the last 20 passenger transactions"})
summary = {"id": V, "ship": "dryrun", "name": "MS Dry Run", "t0": T0, "landed": True, "end": T0 + 2041,
           "sent": {"pay": 116, "bill": 0, "book": 5, "cancel": 1}, "refused": {"pay": 8, "bill": 0, "book": 0, "cancel": 0},
           "skipped": 117, "half": 123, "passengers": 40, "tried": {"book": False}}
log.append({"t": T0 + 5400, "visit": V, "kind": "visit over", "summary": summary})
inc = [{"at": T0 + 2041, "kind": "refused", "visit": V, "note": "left", "chain": {"block_age": 93, "waiting": 2}}]

f = blog.facts_of(log[::-1], inc)
check(f["ship"] == "MS Dry Run" and f["simulated passengers"] == 40, "ship and passengers")
check(f["accepted in all"] == 122 and f["refused in all"] == 8, "122 accepted, 8 refused")
check(f["left early"]["minutes in port"] == 34 and f["left early"]["at"] == "16:34", "left after 34 minutes at 16:34 German time")
check(any("timeout" in k and v == 8 for k, v in f.items()), "the 8 empty refusals are named as timeouts")
check(f["stops skipped"] == 117 and f["sends at half pace because the testnet looked strained"] == 123, "skipped and half pace")
check(f["incidents"][0]["newest block age (s)"] == 93, "incident block age")
check(f["date"].startswith("Wednesday, 4 November 2026"), "date in words")
check(not blog.due(log[:-1], T0 + 6000) and blog.due(log, T0 + 5400 + blog.CHECK_WAIT), "due only after the visit, after the check wait")
check(blog.due(log + [{"t": T0 + 5600, "kind": "bookings checked", "checked": 5, "not_released": []}], T0 + 5600), "due once the bookings are checked")

three = lambda s: {"en": s, "zh": s, "ja": s}  # noqa: E731
answer = {"title": three("The MS Dry Run left after 34 minutes"), "dek": three("8 sends got no answer from our node."),
          "why": [three("The brakes work."), three("A community node under steady traffic.")],
          "body": three("## What happened\n\n122 transactions went through, 117 stops were skipped.\n\n## What is still open\n\nWhy our node slowed."), "x": "x"}
a = blog.article(f, answer, T0 + 6000)
check(a["check"]["unknown_numbers"] == [], "every number of a faithful answer is in the facts")
bad = dict(answer, body=three("## What happened\n\n150 transactions went through, wow!"))
b = blog.article(f, bad, T0 + 6000)
check(b["check"]["unknown_numbers"] == ["150"] and b["check"]["hype"], "an invented number and an exclamation are marked")
try:
    blog.article(f, dict(answer, title={"en": "only English"}), T0)
    check(False, "a missing language is refused")
except ValueError:
    check(True, "a missing language is refused")

# a draft, then publish: by hand only, and the marked one needs --force
blog.site_ids = lambda: set()
blog.get = lambda path: {"entries": log, "visits": [V]} if path.startswith("/cruise/log") else ({"incidents": inc} if "incidents" in path else {})
blog.ask_ai = lambda facts: answer
blog.tick(T0 + 5400 + blog.CHECK_WAIT)
st = blog.state()
did = f"{V}-learnings"
check(st["drafted"].get(V) == did and len(st["drafts"][did]) > len(did) + 4, "the loop wrote one draft under an unlisted name")
check(blog.posts()["posts"] == [], "nothing is published by the loop")
blog.tick(T0 + 5400 + blog.CHECK_WAIT + 600)
check(len(os.listdir(os.path.join(TMP, "blog", "drafts"))) == 1, "a visit is drafted once")
check(blog.publish_cli(did, dry=False, force=False) == 0, "publish")
p = blog.posts()["posts"]
check(len(p) == 1 and p[0]["id"] == did and "check" not in p[0] and "status" not in p[0], "published once, without the check fields")
check(blog.publish_cli(did, dry=False, force=False) == 0 and len(blog.posts()["posts"]) == 1, "publishing again keeps one copy")
check(blog.state()["announced"] == [did], "posted to the channels once")
blog.ask_ai = lambda facts: bad
blog.write_draft(V, T0 + 9000)
check(blog.publish_cli(did, dry=False, force=False) == 1, "a draft with an invented number is not published without --force")
check(blog.unpublish_cli(did) == 0 and blog.posts()["posts"] == [], "unpublish")
json.dumps(a)

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

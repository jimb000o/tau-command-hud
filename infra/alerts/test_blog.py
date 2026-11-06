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
ART = os.path.join(TMP, "art")
os.makedirs(ART)
from PIL import Image  # noqa: E402
Image.new("RGB", (1600, 900), (40, 120, 160)).save(os.path.join(ART, "isle.jpg"))
json.dump({"scenes": {"island": "isle.jpg"}}, open(os.path.join(ART, "index.json"), "w"))
SHIPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "rabbit", "art", "ships")
os.environ.update(BLOG_ART=ART, BLOG_SHIPS=SHIPS, PUBLIC_DIR=TMP, BLOG_STATE=os.path.join(TMP, "state.json"), NEWS_AI_KEY="test", CHAT_AI_KEY="",
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
blame = dict(answer, body=three("## What happened\n\nThe testnet was unreliable, IDNI is to blame."))
check(blog.article(f, blame, T0 + 6000)["check"]["hype"] != [] and a["check"]["hype"] == [], "blame on the testnet or IDNI is marked, a fair answer is not")
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
import contextlib
import io
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    blog.announce(p[0], dry=True)
ann = buf.getvalue()
tg_part, x_part = ann.split("--- x ---")[0], ann.split("--- x ---")[1].split("--- picture")[0]
check("<b>In numbers</b>" in tg_part and f"• {f['simulated passengers']} simulated passengers" in tg_part
      and f"• {f['accepted in all']} transactions accepted by the node" in tg_part and "<b>Why it matters</b>" in tg_part and "/blog/?p=" in tg_part,
      f"the announcement carries the logbook's numbers and the link {tg_part}")
check("http" not in x_part and "Tau HUD blog" in x_part and __import__("alerts").x_len(x_part.strip()) <= 280, f"the X copy names the blog without a link {x_part}")
nums = blog.numbers_of({"simulated passengers": 40, "accepted in all": 122, "refused in all": 0, "sends our node did not answer in time (not refusals)": 8,
                        "of those, reached the chain after all": 5, "left early": {"minutes in port": 61, "why": "the node refused 5 of the last 20"}})
check(nums == ["40 simulated passengers, every stop a real transaction", "122 transactions accepted by the node, none refused",
               "8 got no answer from our node in time, 5 of them reached the chain all the same",
               "the ship left after 61 minutes: the node refused 5 of the last 20"], f"the numbers, as the logbook counts them {nums}")
blog.ask_ai = lambda facts: bad
blog.write_draft(V, T0 + 9000)
check(blog.publish_cli(did, dry=False, force=False) == 1, "a draft with an invented number is not published without --force")
d = json.load(open(os.path.join(TMP, "blog", "drafts", st["drafts"][did] + ".json")))
check(d["image"].endswith(f"/blog/img/{did}-hero.jpg") and os.path.exists(os.path.join(TMP, "blog", "img", f"{did}-hero.jpg")), "the draft has its hero picture")
check(len(d["figures"]) == 2 and all(os.path.exists(os.path.join(TMP, "blog", "img", os.path.basename(f["src"]))) for f in d["figures"]), "and two charts of the visit")
import blog_pics  # noqa: E402
check(blog_pics.visit_stats(f) == [("34/90", "minutes in port"), ("122", "accepted by the node"), ("8", "timeouts, counted as refusals")],
      "the numbers on the picture come from the facts")
check(d["card"][0] == "The MS Dry Run left after 34 minutes" and d["card"][-1].startswith("Tau HUD blog"), "the card on the picture")
share = open(os.path.join(TMP, "blog", "a", did + ".html")).read()
check('og:image" content="https://node.tauhud.com/blog/img/' in share and "summary_large_image" in share, "publishing writes the link-preview page with the picture")
check(blog.unpublish_cli(did) == 0 and blog.posts()["posts"] == [], "unpublish")
json.dumps(a)

# Queen Mempool style (6 November 2026 on): half pace split by why, and the node's answer times
Q, TQ = "2026-11-07-queen", 1793970000
ql = [{"t": TQ, "visit": Q, "ship": "queen", "kind": "landed", "verdict": "calm", "plan": 581, "trial": ["bill"]}]
for i in range(60):
    ql.append({"t": TQ + 10 + i * 30, "visit": Q, "kind": "pay", "ok": True, "verdict": "calm", "ms": 400 + i * 100})
ql.append({"t": TQ + 5400, "visit": Q, "kind": "visit over", "summary": {"id": Q, "ship": "queen", "name": "Queen Mempool", "t0": TQ, "landed": True,
           "end": TQ + 5400, "sent": {"pay": 60}, "refused": {}, "skipped": 0, "half": 40, "half_strained": 0, "half_node": 40, "passengers": 120,
           "unanswered": 3}})
fq = blog.facts_of(ql, [])
check("sends at half pace because the testnet looked strained" not in fq
      and fq["sends at half pace because our own node had just left a send unanswered (not the testnet)"] == 40,
      "half pace after our node's timeouts is not put on the testnet")
check(fq["our node's answer time to a send, seconds"]["slowest"] == 6.3 and len(fq["median answer time per 10 minutes, seconds"]) == 3,
      "the node's answer times, overall and per 10 minutes")
import blog_pics  # noqa: E402
qf = blog_pics.visit_charts(fq, os.path.join(TMP, "q"))
check(any(p.endswith("-answer.png") for p, _ in qf), "a chart of the node's answer times")

# up block: an old draft (no drafted_at) and a marked one never go out by themselves; a clean new one says when
blog.AUTO_PUBLISH_HOURS = 24
check(blog.auto_note({"drafted_at": {}}, "old", {}).startswith("never by itself: written before"), "old draft: only by hand")
check(blog.auto_note({"drafted_at": {"x": T0}}, "x", {"check": {"unknown_numbers": ["9"]}}).startswith("never by itself: the check"), "marked draft: only by hand")
check(blog.auto_note({"drafted_at": {"x": T0}}, "x", {"check": {}}).startswith("by itself on Thursday, 5 November 2026"), "clean new draft: the day and time it goes out")
st0 = {"drafts": {"old": "old-1"}, "drafted": {}, "failed_at": 0}
blog.write_json(blog.STATE, st0)
blog.write_json(os.path.join(TMP, "blog", "drafts", "old-1.json"), {"id": "old", "check": {}})
check(blog.auto_publish(T0 + 10 * 86400) is None, "an old draft is never published by itself")
blog.AUTO_PUBLISH_HOURS = 0

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

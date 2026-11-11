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
    log.append({"t": T0 + 700 + i * 160, "visit": V, "kind": "pay", "ok": False, "err": None if i % 2 else "null", "verdict": "strained"})
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

# the model's answer is shaped by the API (valid JSON by itself); a broken text answer is asked once more;
# a 400 on the shaped request falls back to the plain request, and the API's reason is shown
import io as _io
import urllib.error as _ue
answers = []
sent_bodies = []
class _R(_io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False
def fake_open(req, timeout=0):
    sent = json.loads(req.data)
    sent_bodies.append(sent)
    nxt = answers.pop(0)
    if nxt == 400:
        raise _ue.HTTPError(req.full_url, 400, "Bad Request", {}, _io.BytesIO(b'{"error": {"message": "no shaped answers here"}}'))
    return _R(json.dumps(nxt).encode())
blog.urllib.request.urlopen = fake_open
answers = [{"content": [{"type": "text", "text": json.dumps(answer)}], "usage": {}}]
check(blog.ask_ai(f) == answer, "a shaped answer is the article")
fmt = sent_bodies[-1]["output_config"]["format"]
check(fmt["type"] == "json_schema" and fmt["schema"]["additionalProperties"] is False and "tools" not in sent_bodies[-1]
      and "tool_choice" not in sent_bodies[-1] and fmt["schema"]["properties"]["card"]["additionalProperties"] is False,
      "the article is asked for as a shaped answer, not a forced tool call")
answers = [{"content": [{"type": "text", "text": '{"title": {"en": "the "bill" kind"}'}], "usage": {}},
           {"content": [{"type": "text", "text": "here: " + json.dumps(answer)}], "usage": {}}]
check(blog.ask_ai(f) == answer and not answers, "a text answer with a stray quote is asked once more, then read from the text")
answers = [400, {"content": [{"type": "text", "text": json.dumps(answer)}], "usage": {}}]
sent_bodies.clear()
check(blog.ask_ai(f) == answer and "output_config" not in sent_bodies[-1], "a 400 on the shaped request is asked again the plain way")
answers = [400, 400]
try:
    blog.ask_ai(f)
    check(False, "two 400s stop with the API's reason")
except RuntimeError as e:
    check("no shaped answers here" in str(e) and "400" in str(e), "two 400s stop with the API's reason")
# 11 November 2026: thinking and the article share max_tokens; an answer cut off there read as broken JSON, twice
cut = json.dumps(answer)[:200]
answers = [{"content": [{"type": "text", "text": cut}], "stop_reason": "max_tokens", "usage": {}},
           {"content": [{"type": "text", "text": json.dumps(answer)}], "stop_reason": "end_turn", "usage": {}}]
sent_bodies.clear()
check(blog.ask_ai(f) == answer and [b["max_tokens"] for b in sent_bodies] == [blog.ROOM, blog.ROOM_MAX] and blog.ROOM >= 16000,
      "an answer cut off at max_tokens is asked once more with more room, not read as broken JSON")
answers = [{"content": [{"type": "text", "text": cut}], "stop_reason": "max_tokens", "usage": {}},
           {"content": [{"type": "text", "text": cut}], "stop_reason": "max_tokens", "usage": {}}]
try:
    blog.ask_ai(f)
    check(False, "cut off with the most room too: it says so")
except RuntimeError as e:
    check("did not fit" in str(e) and not answers, "cut off with the most room too: it says so, after two asks")
answers = [{"content": [], "stop_reason": "refusal", "stop_details": {"type": "refusal", "category": "cyber"}, "usage": {}}]
try:
    blog.ask_ai(f)
    check(False, "a refusal says so")
except RuntimeError as e:
    check("declined" in str(e) and "cyber" in str(e) and not answers, "a refusal says so, nothing asked again")

card = blog.card_of({"line": "x", "why": []}, "Queen Mempool stays its full 90 minutes; our node slowed down")
check(card[0] == "Queen Mempool stays its full 90 minutes; our node slowed", f"a long title is cut at a word on the card {card[0]!r}")

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
check(f"/blog/a/{did}.html" in x_part and x_part.count("http") == 1 and "Tau HUD blog" in x_part and __import__("alerts").x_len(x_part.strip()) <= 280,
      f"the X copy carries the share page's link, once, and fits {x_part}")
check("as the link's card, $0.20" in ann, "the dry run says the picture comes as the card and what the post costs")
blog.X_BLOG_LINK = False
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    blog.announce(p[0], dry=True)
x_old = buf.getvalue().split("--- x ---")[1].split("--- picture")[0]
check("http" not in x_old and "Tau HUD blog" in x_old, f"X_BLOG_LINK=false: the X copy without a link, as before {x_old}")
blog.X_BLOG_LINK = True
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
check(blog_pics.visit_stats(f) == [("34/90", "minutes in port"), ("122", "accepted by the node"), ("8", "timeouts, counted as refusals"), ("117", "stops skipped")],
      "the numbers on the picture come from the facts")
check(d["card"][0] == "The MS Dry Run left after 34 minutes" and d["card"][-1].startswith("Tau HUD blog"), "the card on the picture")

# the Queen Mempool after the MS Dry Run: the article gets the ship before, what changed, and what the numbers mean
Q = "2026-11-07-queen"
qlog = [{"t": T0 + 3 * 86400, "visit": Q, "ship": "queen", "kind": "landed", "verdict": "calm", "plan": 581, "trial": ["bill"]}]
for i in range(409):
    qlog.append({"t": T0 + 3 * 86400 + 5 + i * 13, "visit": Q, "kind": "bill" if i % 100 == 99 else "pay", "ok": True, "verdict": "calm", "height": 1497 + i // 3, "ms": 6800})
for i in range(10):
    qlog.append({"t": T0 + 3 * 86400 + 600 + i * 400, "visit": Q, "kind": "pay", "ok": None, "note": "no answer in 20 s", "verdict": "calm", "ms": 20000})
qsum = {"id": Q, "ship": "queen", "name": "Queen Mempool", "t0": T0 + 3 * 86400, "landed": True, "end": T0 + 3 * 86400 + 5400,
        "sent": {"pay": 405, "bill": 4}, "refused": {}, "unanswered": 10, "skipped": 162, "passengers": 120,
        "changed": [{"what": "its pace", "from": "12 a minute", "to": "11 a minute", "because": "10 sends got no answer in time"}]}
qlog.append({"t": T0 + 3 * 86400 + 5400, "visit": Q, "kind": "visit over", "summary": qsum})
qlog.append({"t": T0 + 3 * 86400 + 5500, "visit": Q, "kind": "bookings checked", "checked": 0, "not_released": []})
qf = blog.facts_of(qlog[::-1], [])
check(qf["minutes in port"] == 90 and "bookings checked after the visit" not in qf, "a ship that stayed: 90 minutes, and no line for bookings that were never made")
blog.get = lambda path: ({"entries": log, "visits": [Q, V]} if f"visit={V}" in path else {"entries": qlog, "visits": [Q, V]}) if path.startswith("/cruise/log") else {}
bf = blog.before_facts(Q, [Q, V], [], None)
qf = blog.compare_with(qf, bf)
qf["what the numbers mean"] = blog.meaning_of(qf)
b = qf["the ship before"]
check(b["ship"] == "MS Dry Run" and b["minutes in port"] == 34 and b["refused in all"] == 0 and b["sends our node did not answer in time"] == 8,
      f"the ship before in the same numbers, its timeouts no longer refusals {b}")
check("the node refused none" in b["left early"]["why"], "why the ship before left is told with the old rule")
check(any("no longer counts as a refusal" in c for c in b["what we changed after that call"]), "what we changed after the Dry Run")
check(qf["compared with the ship before"]["minutes in port"] == [34, 90], "side by side: 34 against 90 minutes")
m = qf["what the numbers mean"]
check(m["share of the planned stops that went through"] == "70%" and m["sends a minute the node's answer time allows, one at a time"] == 8.8
      and m["share of the planned time in port"] == "100%", f"what the numbers mean {m}")
check(blog.unknown_numbers("the slowest answer took 20.0 seconds, the median 6.8", qf) == [], "20.0 seconds is a known number")
check(blog_pics.visit_stats(qf)[0] == ("90/90", "minutes in port (ship before: 34)"), f"the first tile reads against the ship before {blog_pics.visit_stats(qf)[0]}")
qfigs = blog_pics.visit_charts(qf, os.path.join(TMP, "queen"))
check(any(p.endswith("-before.png") for p, _ in qfigs) and all(os.path.exists(p) for p, _ in qfigs), f"a chart against the ship before {[p for p, _ in qfigs]}")
check("Compared with the ship before" in blog.SYSTEM and "What it means for the testnet" in blog.SYSTEM, "the drafting rules ask for the comparison and the meaning")
blog.get = lambda path: {"entries": log, "visits": [V]} if path.startswith("/cruise/log") else ({"incidents": inc} if "incidents" in path else {})
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

# ---------- our node had no room for new wallets (IDNI tau-testnet #108; MS Dry Run, 11 November 2026) ----------
T11 = 1794409200   # Wednesday 11 November 2026, 16:00 German time
V11 = "2026-11-11-dryrun"
AU = '{"code":"ADMISSION_UNAVAILABLE","message":"Transaction validation is temporarily unavailable; please resubmit."}'
nlog = [{"t": T11, "visit": V11, "ship": "dryrun", "kind": "landed", "verdict": "calm", "plan": 232, "trial": []}]
for i in range(222):
    nlog.append({"t": T11 + 30 + i * 20, "visit": V11, "kind": "pay", "p": 40 + i % 30, "ok": True, "seq": 3, "verdict": "calm", "height": 7100 + i // 4})
# as it was logged that day: two passengers' first sends were still waiting (sequence 1), their later ones at 0
for i, (p, seq, k) in enumerate([(7, 1, "book"), (7, 1, "pay"), (25, 1, "pay"), (7, 0, "pay"), (25, 0, "pay"), (7, 0, "pay"),
                                 (25, 0, "pay"), (7, 0, "pay"), (25, 0, "pay")]):
    nlog.append({"t": T11 + 759 + i * 300, "visit": V11, "kind": k, "p": p, "ok": False, "seq": seq, "err": AU, "verdict": "calm"})
nlog.append({"t": T11 + 5500, "visit": V11, "kind": "visit over", "summary": {"id": V11, "name": "MS Dry Run", "t0": T11, "landed": True,
             "passengers": 40, "sent": {"pay": 217, "book": 4, "cancel": 1}, "refused": {"pay": 8, "book": 1}, "skipped": 1}})
nf = blog.facts_of(nlog[::-1], [])
nw = nf.get(blog.NEW_WALLET_FACT) or {}
check(nf["refused in all"] == 0 and not nf.get("refused by the node") and not nf.get("refusal answers"),
      "the nine answers of 11 November are no refusals: our node had no room for two new wallets")
check(nw.get("passengers") == 2 and nw.get("their sends the node could not take or the ship left out") == 9 and "#108" in nw.get("why", "")
      and "254" in nw.get("why", "") and "counted them as refusals" in nw.get("how this call handled them", ""),
      "they are counted apart: two passengers, nine sends, why, and how that call still handled them")
nn = blog.numbers_of(nf)
check(any(x.endswith("none refused") for x in nn) and any("no room for the new wallets of 2 passengers (9 sends)" in x and "IDNI #108" in x for x in nn),
      "the visit in numbers: none refused, and one line on the two new wallets")
check(not blog.unknown_numbers("Our node had no room for the new wallets of 2 passengers: it keeps 254 wallet addresses (IDNI tau-testnet issue #108, "
                                "11 November 2026); 9 sends.", nf), "the article may name 254, #108 and the date: they are in the facts")
# since the ship leaves such a passenger out (relay/cruise.py), the logbook says so itself
slog = [e for e in nlog if e.get("ok") is not False and e.get("kind") != "visit over"]
slog += [{"t": T11 + 800, "visit": V11, "kind": "pay", "p": 7, "ok": None, "new_wallet": True, "code": "ADMISSION_UNAVAILABLE", "err": AU, "seq": 0},
         {"t": T11 + 1400, "visit": V11, "kind": "pay", "p": 7, "ok": None, "new_wallet": True, "note": "left out"},
         {"t": T11 - 3 * 86400, "visit": V11, "kind": "book ahead", "p": 9, "ok": None, "new_wallet": True},
         {"t": T11 + 5500, "visit": V11, "kind": "visit over", "summary": {"id": V11, "name": "MS Dry Run", "t0": T11, "landed": True, "passengers": 40,
                                                                           "sent": {"pay": 222}, "refused": {}, "skipped": 0, "left_out": {"passengers": 1, "stops": 2}}}]
sf = blog.facts_of(slog, [])
sw = sf.get(blog.NEW_WALLET_FACT) or {}
check(sf["refused in all"] == 0 and sw.get("passengers") == 2 and sw.get("their sends the node could not take or the ship left out") == 3
      and "left out" in sw.get("how this call handled them", ""), "logged the new way: counted apart the same, with how the ship left them out")
check(sf["bookings ahead in escrow"].get("not booked: wallets new to our node, which had no room for them") == 1
      and sf["bookings ahead in escrow"]["refused by the node"] == 0, "a booking ahead from a new wallet: not booked, not refused")
# a wallet the chain knows that gets the same answer is a refusal as before
klog = nlog[:1] + [{"t": T11 + 60, "visit": V11, "kind": "pay", "p": 5, "ok": False, "seq": 7, "err": AU, "verdict": "calm"}]
kf = blog.facts_of(klog, [])
check(kf["refused in all"] == 1 and not kf.get(blog.NEW_WALLET_FACT) and kf.get("refusal answers"), "the same answer to a wallet with transactions in blocks stays a refusal")
check(blog.NEW_WALLET_FACT not in blog.facts_of(log[::-1], inc), "a visit without new wallets says nothing of them")

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

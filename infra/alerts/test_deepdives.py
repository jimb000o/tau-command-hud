"""Unit test of the closer looks (no network): one a day at 13:00 UTC in the file's order, each once, X for every second
one, X never waiting for a failing Telegram; and the real assets/deepdives.json is complete and fits X.

Run: python test_deepdives.py   (needs websockets==15.0.1)
"""
import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="", X_API_KEY="", DEEPDIVE_DAYS="0,1,2,3,4,5,6")
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

    def send_text(self, text, *rest):
        if self.fail:
            return False, None, "HTTP 401: Unauthorized"
        self.sent.append((text, rest))
        return True, None, ""


def at(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


alerts.X_PICTURES = False
alerts.POLL_ON = False   # the poll day is tested at the end
alerts.Watcher.fetch_deepdives = lambda self: None
POSTS = [{"id": "a", "title": "A", "text": "About A.", "x": ["Head A", "Text A."], "link": "/a/", "image": "/assets/og/a.png"},
         {"id": "b", "title": "B", "text": "About B.\nMore B.", "try": "do B", "x": ["Head B"], "link": "/b/"},
         {"id": "c", "title": "C", "text": "About C.", "x": ["Head C"], "link": "/c/"}]

tg, x = Fake("telegram"), Fake("x")
w = alerts.Watcher([tg, x])
w.state.pop("deepdives", None)
w.state.pop("pages", None)
w.state.pop("x", None)
asyncio.run(w.maybe_deepdive(at("2026-11-03T12:59:00Z"), POSTS))
check(tg.sent == [], "nothing before 13:00 UTC")
asyncio.run(w.maybe_deepdive(at("2026-11-03T13:00:30Z")))
check(len(tg.sent) == 1 and "<b>A</b>" in tg.sent[0][0] and tg.sent[0][0].startswith(alerts.DEEPDIVE_LINE), "the first one on Telegram at 13:00")
check(tg.sent[0][1][0]["inline_keyboard"][0][0]["url"] == "https://tauhud.com/a/" and len(tg.sent[0][1]) == 1,
      "with its button, and no repo preview picture (made in Simulation mode)")
check(len(x.sent) == 1 and x.sent[0][0].startswith("Head A") and x.sent[0][0].endswith("#TauNet"), "the first one on X too")
asyncio.run(w.maybe_deepdive(at("2026-11-03T14:00:00Z")))
check(len(tg.sent) == 1, "one a day")
asyncio.run(w.maybe_deepdive(at("2026-11-04T13:01:00Z")))
check(len(tg.sent) == 2 and "<b>B</b>" in tg.sent[1][0] and "<b>Try it:</b> do B" in tg.sent[1][0] and "More B." in tg.sent[1][0],
      "the second the next day, with its Try it line")
check(len(x.sent) == 1, "the second is Telegram only (X gets every second one)")
asyncio.run(w.maybe_deepdive(at("2026-11-05T17:00:00Z")))
check(len(tg.sent) == 2, "a day missed is not posted late")
asyncio.run(w.maybe_deepdive(at("2026-11-06T13:00:00Z")))
check(len(tg.sent) == 3 and "<b>C</b>" in tg.sent[2][0] and len(x.sent) == 2, "the third, on X again")
asyncio.run(w.maybe_deepdive(at("2026-11-07T13:00:00Z")))
check(len(tg.sent) == 3, "the file is used up: nothing until a new one is added")
asyncio.run(w.maybe_deepdive(at("2026-11-07T13:05:00Z"), POSTS + [{"id": "d", "title": "D", "text": "About D.", "x": ["Head D"], "link": "/d/"}]))
check(len(tg.sent) == 4 and "<b>D</b>" in tg.sent[3][0], "a new entry in the file goes out the same day")

# only on some days of the week (Monday, Wednesday, Friday by default)
alerts.DEEPDIVE_DAYS = (0, 2, 4)
tgd, xd = Fake("telegram"), Fake("x")
wd = alerts.Watcher([tgd, xd])
wd.state.pop("deepdives", None)
wd.state.pop("pages", None)
wd.state.pop("x", None)
asyncio.run(wd.maybe_deepdive(at("2026-11-03T13:00:00Z"), POSTS))
check(tgd.sent == [], "Tuesday: no closer look")
asyncio.run(wd.maybe_deepdive(at("2026-11-04T13:00:00Z")))
check(len(tgd.sent) == 1 and "<b>A</b>" in tgd.sent[0][0], "Wednesday: the first one")
asyncio.run(wd.maybe_deepdive(at("2026-11-05T13:00:00Z")))
check(len(tgd.sent) == 1, "Thursday: none")
asyncio.run(wd.maybe_deepdive(at("2026-11-06T13:00:00Z")))
check(len(tgd.sent) == 2 and "<b>B</b>" in tgd.sent[1][0], "Friday: the second")
alerts.DEEPDIVE_DAYS = tuple(range(7))

# Telegram failing: X goes alone, once; the Telegram retry later does not repeat it on X
tg2, x2 = Fake("telegram", fail=True), Fake("x")
w2 = alerts.Watcher([tg2, x2])
w2.state.pop("deepdives", None)
w2.state.pop("pages", None)
w2.state.pop("x", None)
asyncio.run(w2.maybe_deepdive(at("2026-11-03T13:00:00Z"), POSTS))
check(tg2.sent == [] and len(x2.sent) == 1 and x2.sent[0][0].startswith("Head A"), "Telegram fails: X posts the first one alone")
asyncio.run(w2.maybe_deepdive(at("2026-11-03T13:01:00Z")))
check(len(x2.sent) == 1, "not again while Telegram pauses")
tg2.fail = False
asyncio.run(w2.maybe_deepdive(at("2026-11-03T13:06:00Z")))
check(len(tg2.sent) == 1 and "<b>A</b>" in tg2.sent[0][0] and len(x2.sent) == 1, "Telegram back: the same one goes out there, X not again")
asyncio.run(w2.maybe_deepdive(at("2026-11-04T13:00:00Z")))
check(len(tg2.sent) == 2 and "<b>B</b>" in tg2.sent[1][0] and len(x2.sent) == 1, "next day the second, Telegram only")


# a page shown in the last 30 days is not shown again, whichever kind of post showed it (11 Nov 2026: the rules wall)
tg3, x3 = Fake("telegram"), Fake("x")
w3 = alerts.Watcher([tg3, x3])
w3.state.pop("deepdives", None)
w3.state["pages"] = {"/a/": at("2026-11-01T10:00:00Z")}
asyncio.run(w3.maybe_deepdive(at("2026-11-03T13:00:00Z"), POSTS))
check(len(tg3.sent) == 1 and "<b>B</b>" in tg3.sent[0][0] and w3.state["pages"].get("/b/"), "a page shown 2 days ago is passed over")
check(alerts.page_key("https://tauhud.com/rules/?ref=x") == "/rules/" and alerts.page_key("/") is None
      and alerts.page_key("https://chess.taumorrow.com") is None, "page keys: the path, never the front page or another site")
s4 = {"plan": {"posted": {"spot-rules": at("2026-11-11T14:00:00Z")}, "posts": [{"id": "spot-rules", "link": "/rules/"}]}}
check(alerts.page_recent(s4, "/rules/", at("2026-11-20T00:00:00Z")) and not alerts.page_recent(s4, "/rules/", at("2026-12-12T00:00:00Z")),
      "the first time, the ledger is seeded from what was already posted")


# the page's checked live picture (site-shots.mjs) is the one a post carries
shots = os.path.join(alerts.PUBLIC_DIR, "pageshots")
os.makedirs(shots, exist_ok=True)
with open(os.path.join(shots, "index.json"), "w") as f:
    json.dump({"rules": {"path": "/rules/", "at": "2026-11-12T06:00:00Z", "ok": True}, "status": {"ok": False, "why": "mode chip not green"},
               "hud": {"path": "/", "at": "2026-11-12T06:00:00Z", "ok": True}}, f)
for n in ("rules", "status", "hud"):
    open(os.path.join(shots, n + ".jpg"), "wb").close()
check(alerts.post_picture("https://tauhud.com/assets/og/rules.png", "/rules/") == alerts.NODE_PUBLIC + "/pageshots/rules.jpg?v=202611120600",
      "a checked live picture replaces the repo's preview picture")
check(alerts.post_picture("https://tauhud.com/assets/shots/status.png", "https://tauhud.com/status/?ref=x") is None, "a page that failed its check: no picture")
check(alerts.live_shot("https://tauhud.com/") and alerts.live_shot("https://chess.taumorrow.com") is None, "the front page has one, another site none")
check(alerts.post_picture("https://node.tauhud.com/blog/img/x.jpg", "/blog/") == "https://node.tauhud.com/blog/img/x.jpg", "other pictures stay")


# one post a day about Tau HUD itself: after a site update the closer look waits a day; on the poll day the poll is the post
tg5, x5 = Fake("telegram"), Fake("x")
w5 = alerts.Watcher([tg5, x5])
for k in ("deepdives", "pages", "x", "poll"):
    w5.state.pop(k, None)
w5.promo_take(at("2026-11-02T08:00:00Z"))
asyncio.run(w5.maybe_deepdive(at("2026-11-02T13:00:00Z"), POSTS))
check(tg5.sent == [], "a site update this morning: no closer look today")
asyncio.run(w5.maybe_deepdive(at("2026-11-03T13:00:00Z")))
check(len(tg5.sent) == 1 and "<b>A</b>" in tg5.sent[0][0], "the next day it goes out")
alerts.POLL_ON = True
asyncio.run(w5.maybe_deepdive(at("2026-11-04T13:00:00Z")))
check(len(tg5.sent) == 1, "Wednesday: the poll's day, no closer look")
w5.state["poll"] = {"week": "2026-W45"}
asyncio.run(w5.maybe_deepdive(at("2026-11-05T13:00:00Z")))
check(len(tg5.sent) == 2, "Thursday the closer looks go on")
alerts.POLL_ON = False

# the real file
with open(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "deepdives.json")) as f:
    real = json.load(f)["posts"]
ids = [p["id"] for p in real]
check(len(ids) == len(set(ids)) and len(real) >= 20, f"assets/deepdives.json: {len(real)} closer looks, ids unique")
for p in real:
    xt = alerts.deepdive_x(p)
    ok = all(p.get(k) for k in ("id", "title", "text", "x", "link", "button", "image")) and alerts.x_len(xt) <= 280 and "…" not in xt \
        and len(alerts.deepdive_text(p)) < 1500
    if not ok:
        check(False, f"{p['id']}: fields, X fits (now {alerts.x_len(xt)}), Telegram short enough")
check(all("http" not in " ".join(p["x"]) for p in real), "X texts carry no links (X_LINKS is off)")
import re  # noqa: E402
bad = [p["id"] for p in real if re.search(r"\b(red pill|tau island|matrix|moon|price|pump)\b", (p["text"] + " ".join(p["x"])).lower())]
check(not bad, f"no words the site keeps off: {bad}")
check("…" not in alerts.deepdive_x(real[0]) and alerts.x_len(alerts.deepdive_x(real[0])) <= 280, "the first X post fits")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

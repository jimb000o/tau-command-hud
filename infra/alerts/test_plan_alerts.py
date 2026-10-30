"""Unit test of the posts planned ahead (no network): each goes out once at its time on Telegram and then X, a missed one
is never posted late, and the real assets/posts-plan.json is complete and fits X.

Run: python test_plan_alerts.py   (needs websockets==15.0.1)
"""
import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="", X_API_KEY="")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


class Fake(alerts.Outlet):
    def __init__(self, name):
        self.name, self.sent = name, []

    def enabled(self):
        return True

    def send_text(self, text, *rest):
        self.sent.append((text, rest))
        return True, None, ""


def at(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


alerts.X_PICTURES = False
alerts.Watcher.fetch_plan = lambda self: None
tg, x = Fake("telegram"), Fake("x")
w = alerts.Watcher([tg, x])
w.state.pop("plan", None)
w.state.pop("x", None)
posts = [{"id": "a", "at": "2026-11-01T10:00:00Z", "tg": "<b>A</b>", "x": ["Head A", "Text A."], "link": "/start/", "button": "Go"},
         {"id": "b", "at": "2026-11-01T10:00:00Z", "tg": "<b>B</b>"},
         {"id": "late", "at": "2026-10-31T10:00:00Z", "tg": "late", "x": ["late"]}]
asyncio.run(w.maybe_plan(at("2026-11-01T09:59:00Z"), posts))
check(tg.sent == [], "nothing before its time")
asyncio.run(w.maybe_plan(at("2026-11-01T10:00:30Z")))
check(len(tg.sent) == 1 and tg.sent[0][0] == "<b>A</b>" and tg.sent[0][1][0]["inline_keyboard"][0][0]["url"] == "https://tauhud.com/start/",
      "at its time: Telegram with its button")
check(len(x.sent) == 1 and x.sent[0][0].startswith("Head A\n\nText A.") and x.sent[0][0].endswith(alerts.PLAN_FOOT + " · #TauNet $AGRS"),
      "then X, with the source line and the tags")
asyncio.run(w.maybe_plan(at("2026-11-01T10:01:00Z")))
check(len(tg.sent) == 2 and tg.sent[1][0] == "<b>B</b>" and len(x.sent) == 1, "one per check; a post without x stays off X")
asyncio.run(w.maybe_plan(at("2026-11-01T10:02:00Z")))
asyncio.run(w.maybe_plan(at("2026-11-01T12:00:00Z"), posts))
check(len(tg.sent) == 2, "never twice, and one missed by a day is not posted late")

# the real plan
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "posts-plan.json")) as f:
    real = json.load(f)["posts"]
ids = [p["id"] for p in real]
check(len(ids) == len(set(ids)), "ids are unique")
for p in real:
    ok = bool(p.get("tg")) and len(p["tg"]) <= 4000 and at(p["at"]) > 0
    xt = alerts.x_post(p["x"], foot=p.get("foot") or alerts.PLAN_FOOT) if p.get("x") else ""
    check(ok and (not xt or (alerts.x_len(xt) <= 280 and "http" not in xt and "…" not in xt)), f"{p['id']}: complete, X fits whole")
    if p.get("image"):
        check(os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", p["image"].lstrip("/"))), f"{p['id']}: picture exists")
xs = [tuple(p["x"]) for p in real if p.get("x")]
check(len(xs) == len(set(xs)), "no two X texts alike (X refuses a repeat)")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

"""Unit test of the room between posts (no network): a post on Telegram or @TauHUDcom is noted in last-posts.json; within
POST_GAP_MINUTES the X copy of a non-urgent post is left out, an urgent one goes, and the blog's article waits.

Run: python test_post_gap.py   (needs websockets==15.0.1)
"""
import asyncio
import os
import sys
import tempfile
import time

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="", X_DAILY_CAP="8",
                  X_MONTHLY_CAP="100", POST_GAP_MINUTES="120", BLOG_STATE=os.path.join(TMP, "blog.json"),
                  BLOG_AUTO_PUBLISH_HOURS="24", BLOG_POST_MAX_HOURS="30", NEWS_AI_KEY="", CHAT_AI_KEY="", X_API_KEY="")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402
import blog  # noqa: E402

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

    def send_text(self, text, *_):
        self.sent.append(text)
        alerts.note_public_post(self.name)
        return True, None, ""


now = time.time()
check(alerts.post_gap_left() == 0, "nothing posted yet: free")
alerts.note_public_post("x", now - 30 * 60)
check(abs(alerts.post_gap_left("x", now) - 90 * 60) < 2, "an X post 30 minutes ago: 90 minutes to wait on X")
check(alerts.post_gap_left("telegram", now) == 0, "Telegram is counted apart")
check(alerts.post_gap_left(("telegram", "x"), now) > 0, "both channels: wait for the busier one")

x = Fake("x")
w = alerts.Watcher(outlets=[x])
check(asyncio.run(w.post_x("second post", "test", now)) is False and not x.sent, "an X copy within the gap is left out")
check(asyncio.run(w.post_x("chain news", "finding", now, urgent=True)) is True and x.sent == ["chain news"], "an urgent one goes")
alerts.note_public_post("x", now - 3 * 3600)
check(asyncio.run(w.post_x("later post", "test", now)) is True, "after the gap the next one goes")

# the blog: a clean article due by itself waits while a channel posted lately, and goes once there is room
blog.AUTO_PUBLISH_HOURS, blog.POST_MAX_HOURS = 24, 30
did = "2026-11-10-pirates-learnings"
t0 = now - 26 * 3600
blog.write_json(blog.STATE, {"drafts": {did: did + "-1"}, "drafted": {}, "failed_at": 0, "drafted_at": {did: t0 + 2 * 3600}})
three = {"en": "t", "zh": "t", "ja": "t"}
blog.write_json(os.path.join(TMP, "blog", "drafts", did + "-1.json"),
                {"id": did, "visit": "2026-11-10-pirates", "t0": t0, "title": three, "dek": three, "why": [three], "check": {}})
told = []
blog.announce = lambda a, dry: told.append(a["id"])
alerts.note_public_post("telegram", now - 10 * 60)
check(blog.auto_publish(now) is None and not told and not blog.posts()["posts"], "the article waits while Telegram posted 10 minutes ago")
alerts.note_public_post("telegram", now - 3 * 3600)
alerts.note_public_post("x", now - 3 * 3600)
check(blog.auto_publish(now) == did and told == [did], "with room it goes, with its one post")

alerts.POST_GAP_MINUTES = 0
check(alerts.post_gap_left("x", now) == 0, "POST_GAP_MINUTES=0: no gap")

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

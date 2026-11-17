"""Unit test of the X gate (no network): without a posting plan every automatic X post goes as before; a mounted plan
is asked with the kind and the account's recent posts, keeps what it says no to off X (Telegram still posts), is read
again when its file changes, and a broken plan never stops a post.

Run: python test_xgate.py   (needs websockets==15.0.1)
"""
import asyncio
import os
import sys
import tempfile
import time

TMP = tempfile.mkdtemp()
PLAN = os.path.join(TMP, "xp")
os.makedirs(PLAN)
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="", X_DAILY_CAP="8",
                  X_MONTHLY_CAP="100", POST_GAP_MINUTES="0", NEWS_AI_KEY="", CHAT_AI_KEY="", X_API_KEY="",
                  XPLAN_DIR=PLAN, X_LINKS="false")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402
import xgate  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


def plan(src: str, bump: float):
    with open(xgate.PATH, "w") as f:
        f.write(src)
    t = time.time() + bump   # a new mtime, so the gate reads it again
    os.utime(xgate.PATH, (t, t))


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
check(xgate.allow("restart") == (True, "") and xgate.links() is None and xgate.text_problems("x") == [],
      "no plan mounted: everything as before")

x = Fake("x")
w = alerts.Watcher(outlets=[x])
check(asyncio.run(w.post_x("a restart", "restart", now, kind="restart")) is True, "no plan: the post goes")

plan('''
seen = []
def allow(kind, account, now, recent):
    seen.append((kind, account, len(recent)))
    return kind != "restart", "plan says no"
def links(now):
    return True
def text_problems(text, account):
    return ["insider word"] if "Mempool" in text.split("\\n")[0] else []
''', 1)
check(asyncio.run(w.post_x("another restart", "restart", now, kind="restart")) is False and len(x.sent) == 1,
      "the plan keeps a restart off X")
check(asyncio.run(w.post_x("a first", "firsts", now, kind="first")) is True and len(x.sent) == 2, "a first still goes")
seen = xgate.plan().seen
check(seen[-1] == ("first", "hud", 1), f"the plan is asked with kind, account and the recent posts ({seen[-1]})")
check(alerts.recent_posts("x") and len(alerts.recent_posts("x")) == 2, "note_public_post keeps the recent times")
check(xgate.links() is True and "https://tauhud.com/nodes/" in alerts.x_post(["Head", "Body"], "https://tauhud.com/nodes/"),
      "the plan turns links on for x_post")
check(alerts.SITE + "/" in alerts.x_post(["Head", "Body"]), "a post without a link of its own carries the site's")
check("http" not in alerts.x_post(["Head", "Body"], "https://tauhud.com/nodes/", with_link=False), "a caller's no stays no")
check(xgate.text_problems("Mempool full\n\nwords") == ["insider word"], "the plan's text check is asked")
check(asyncio.run(w.post_x("untyped", "something", now)) is True, "a post without a kind is never asked")

plan("def allow(kind, account, now, recent):\n    raise ValueError('oops')\n", 2)
check(xgate.allow("restart") == (True, ""), "a plan that fails: the post goes")
plan("this is not python (\n", 3)
check(xgate.allow("restart") == (True, "") and xgate.links() is None, "a plan that does not load: the post goes")
os.remove(xgate.PATH)
check(xgate.plan() is None and xgate.allow("restart")[0], "plan removed: as before")

alerts.note_public_post("x_agorzilla", now)
check(len(xgate.recent("x_agorzilla")) == 1 and len(alerts.recent_posts("x")) == 3, "Agorzilla's posts are counted apart")
check(alerts.post_gap_left("x", now + 10) == 0, "the times list leaves the room between posts alone")

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

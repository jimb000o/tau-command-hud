"""Unit test of Tau HUD's one Telegram group (tgnews.py), no network: posts to the group land in its News topic (JSON
and multipart alike), anything else stays as it is, and setup makes a closed News topic once.

Run: python test_tgnews.py
"""
import json
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), TELEGRAM_CHAT_ID="@tauHUDcom")
os.environ.pop("TELEGRAM_NEWS_TOPIC", None)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tgnews  # noqa: E402

failed = 0


def check(name, ok):
    global failed
    print(("ok   " if ok else "FAIL ") + name)
    failed += 0 if ok else 1


def js(d):
    return json.dumps(d).encode()


# before setup: nothing added (a channel, or a group not ready yet)
b = js({"chat_id": "@tauHUDcom", "text": "hi"})
check("no topic yet: body unchanged", tgnews.into("sendMessage", b, "application/json") == b)

# setup on a group with topics
calls = []


def fake(reply_chat):
    def call(method, d):
        calls.append((method, d))
        if method == "getChat":
            return True, "", {"result": reply_chat}
        if method == "createForumTopic":
            return True, "", {"result": {"message_thread_id": 42, "name": d["name"]}}
        return True, "", {"result": True}
    return call


out = tgnews.setup(fake({"id": -1001234, "type": "supergroup", "is_forum": True, "title": "Tau HUD"}))
check("setup made the topic", any("News topic made: 42" in o for o in out))
check("News closed", ("closeForumTopic", {"chat_id": "@tauHUDcom", "message_thread_id": 42}) in calls)
check("General renamed", any(m == "editGeneralForumTopic" for m, _ in calls))
check("topic remembered", tgnews.topic() == 42)

calls.clear()
out = tgnews.setup(fake({"id": -1001234, "type": "supergroup", "is_forum": True, "title": "Tau HUD"}))
check("second setup keeps the topic", not any(m == "createForumTopic" for m, _ in calls) and tgnews.topic() == 42)

# posts to the group get the topic; other chats and other methods do not
m = json.loads(tgnews.into("sendMessage", b, "application/json"))
check("json post into News", m.get("message_thread_id") == 42 and m["text"] == "hi")
m = json.loads(tgnews.into("sendPoll", js({"chat_id": "@TAUHUDcom", "question": "?"}), "application/json"))
check("poll into News, @name case-insensitive", m.get("message_thread_id") == 42)
p = js({"chat_id": 98765, "text": "private"})
check("private note untouched", tgnews.into("sendMessage", p, "application/json") == p)
e = js({"chat_id": "@tauHUDcom", "message_id": 5, "text": "x"})
check("edit untouched", tgnews.into("editMessageText", e, "application/json") == e)
k = js({"chat_id": "@tauHUDcom", "text": "x", "message_thread_id": 7})
check("explicit thread kept", tgnews.into("sendMessage", k, "application/json") == k)

import alerts  # noqa: E402
body, ctype = alerts.multipart({"chat_id": "@tauHUDcom", "caption": "Pic"}, {"photo": ("a.png", b"PNG", "image/png")})
nb = tgnews.into("sendPhoto", body, ctype)
check("multipart post into News", b'name="message_thread_id"\r\n\r\n42\r\n' in nb and nb.endswith(body) and nb.startswith(b"--tauhud"))
body2, ctype2 = alerts.multipart({"chat_id": "123", "caption": "Pic"}, {"photo": ("a.png", b"PNG", "image/png")})
check("multipart to another chat untouched", tgnews.into("sendPhoto", body2, ctype2) == body2)
check("fields helper", tgnews.fields("@tauHUDcom") == {"message_thread_id": 42} and tgnews.fields("@other") == {})

# the env setting wins; 0 means General (no thread id)
os.environ["TELEGRAM_NEWS_TOPIC"] = "0"
check("TELEGRAM_NEWS_TOPIC=0: General", tgnews.topic() is None and tgnews.into("sendMessage", b, "application/json") == b)
os.environ["TELEGRAM_NEWS_TOPIC"] = "77"
check("TELEGRAM_NEWS_TOPIC=77 wins", tgnews.topic() == 77)
os.environ.pop("TELEGRAM_NEWS_TOPIC")

# a topic made for another group is not used after TELEGRAM_CHAT_ID changed
tgnews.CHAT = "@newgroup"
check("other group's topic ignored", tgnews.topic() is None)
tgnews.CHAT = "@tauHUDcom"

# a channel and a group without topics: setup changes nothing
os.remove(tgnews.PATH)
calls.clear()
out = tgnews.setup(fake({"id": -100, "type": "channel", "title": "Tau HUD"}))
check("channel: no topic made", not any(m == "createForumTopic" for m, _ in calls) and tgnews.topic() is None)
out = tgnews.setup(fake({"id": -100, "type": "supergroup", "is_forum": False, "title": "Tau HUD"}))
check("no topics: says to switch them on", any("topics are OFF" in o for o in out) and tgnews.topic() is None)

print("all passed" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

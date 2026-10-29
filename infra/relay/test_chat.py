"""Unit test of the troll box (chat.py), no network.

Run: python test_chat.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chat  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T = [1_793_145_600.0]
clock = lambda: T[0]  # noqa: E731
d = tempfile.mkdtemp()
path, key = os.path.join(d, "c.json"), os.path.join(d, "c.key")
c = chat.Chat(path, key, clock)
tok = lambda i: f"{i:032x}"  # noqa: E731

r = c.say("p1", tok(1), 0, 1, 2, "hello Tau")
check(r.get("ok") and r["msg"]["name"] == "Quiet Heron" and r["msg"]["text"] == "hello Tau", "a message with the animal name")
check(c.say("p1", tok(1), 0, 1, 2, "again")["error"] == "slow", "a second message within the gap is refused")
T[0] += 10
check(c.say("p1", tok(1), 0, 1, 2, "hello tau")["error"] == "repeat", "the same text again is refused")
for text, why in [("see https://x.y", "link"), ("join t.me/abc", "link"), ("tau.io rocks", "link"), ("ping @someone", "link"),
                  ("wen moon", "talk"), ("price of AGRS?", "talk"), ("buy now", "talk"), ("100x soon", "talk"), ("send your seed phrase", "talk"),
                  ("价格多少", "talk"), ("爆上げ", "talk"), ("n i g g e r", "slur"), ("x" * 201, "long"), ("   ", "empty")]:
    check(c.say("p1", tok(1), 0, 1, 2, text)["error"] == why, f"refused ({why}): {text[:30]}")
for text in ["That is it. Me too", "investigate the spec", "block 88 sealed", "spicy raccoon", "fork? no fork, ever", "o5 = 0 for all"]:
    check(chat.refusal(chat.clean(text)) is None, f"allowed: {text}")
check(c.say("p1", "nope", 0, 1, 2, "hi")["error"] == "bad" and c.say("p1", tok(1), 99, 1, 2, "hi")["error"] == "bad", "a bad token or name is refused")
check(chat.clean("a​‮b\n\n c") == "ab c", "invisible and control characters go, spaces fold")
check(chat.parse_say([tok(1), "0", "1", "2", "hi%20there%21"]) == (tok(1), 0, 1, 2, "hi there!"), "a %-encoded text is read")

# reports: three different people hide a message; the writer's own report does not count
hidden = []
c.on_hide = hidden.append
m = c.say("p2", tok(2), 3, 4, 5, "rude words")["msg"]
c.report("p2", m["id"], tok(2))
c.report("p3", m["id"], tok(3)); c.report("p3", m["id"], tok(3)); c.report("p4", m["id"], tok(4))
check(not hidden, "two different reporters do not hide it")
check(c.report("p5", m["id"], tok(5))["hidden"] and hidden == [m["id"]], "the third hides it and the pages are told")
check(all(x["id"] != m["id"] for x in c.recent()["messages"]), "a hidden message is not shown")
T[0] += 10
m2 = c.say("p2", tok(2), 3, 4, 5, "more rude words")["msg"]
for p in ("p3", "p4", "p5"):
    c.report(p, m2["id"], tok(9))
T[0] += 10
check(c.say("p2", tok(2), 3, 4, 5, "hi")["error"] == "muted", "two hidden messages mute the writer for the day")

# owner page and hide
check(c.route("/chat/admin", "key=wrong")[0] == 403, "the admin page needs the key")
k = open(key).read().strip()
page = c.route("/chat/admin", "key=" + k)
check(page[0] == 200 and b"hello Tau" in page[2], "the admin page lists the messages")
T[0] += 10
m3 = c.say("p6", tok(6), 1, 1, 1, "spam spam")["msg"]
check(c.route("/chat/hide", f"key={k}&id={m3['id']}")[0] == 200 and hidden[-1] == m3["id"], "the owner hides a message")
T[0] += 10
check(c.say("p6", tok(6), 1, 1, 1, "hi")["error"] == "muted", "and its writer is muted")

# storage: no address or person on disk, 24 hours kept, a restart keeps the day
st = json.load(open(path))
check("p1" not in json.dumps(st) and all(set(x) <= {"id", "ts", "a", "b", "c", "text", "hidden"} for x in st["msgs"]), "nothing about the writer is stored")
c2 = chat.Chat(path, key, clock)
check([x["text"] for x in c2.recent()["messages"]] == ["hello Tau"], "a restart keeps the shown messages")
T[0] += 86400
check(c2.recent()["messages"] == [] and json.load(open(path))["msgs"] == [], "after 24 hours everything is gone, also on disk")

# slow mode and the off switch
c3 = chat.Chat(os.path.join(d, "c3.json"), key, clock)
oks = sum(bool(c3.say(f"q{i}", tok(i), 0, 0, 0, f"msg {i}").get("ok")) for i in range(40))
check(oks == chat.ROOM_PER_MIN, "the room takes at most ROOM_PER_MIN messages a minute")
os.environ["CHAT_ENABLED"] = "0"
c4 = chat.Chat(os.path.join(d, "c4.json"), key, clock)
check(c4.say("z", tok(1), 0, 0, 0, "hi")["error"] == "closed" and c4.recent()["enabled"] is False, "CHAT_ENABLED=0 closes the room")

sys.exit(1 if failed else 0)

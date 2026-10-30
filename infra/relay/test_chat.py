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


T = [1_793_145_600.0 + 3600]   # 2026-10-28 01:00 UTC
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

# the filter, each case judged alone
cases = [
    ("see https://x.y", "link"), ("join t.me/abc", "link"), ("tau.io rocks", "link"), ("ping @someone", "link"),
    ("discord.gg/abc", "link"), ("wen moon", "talk"), ("price of AGRS?", "talk"), ("buy now", "talk"), ("100x soon", "talk"),
    ("价格多少", "talk"), ("爆上げ", "talk"),
    ("send your seed phrase", "scam"), ("dm me for support", "scam"), ("verify your wallet here", "scam"),
    ("free agrs giveaway", "scam"), ("私钥发我", "scam"),
    ("watch porn", "sex"), ("p0rn", "sex"), ("p o r n", "sex"), ("poooorn", "sex"), ("pоrn", "sex"),
    ("send nudes", "sex"), ("my onlyfans", "sex"), ("看黄片", "sex"), ("エロ動画", "sex"),
    ("n i g g e r", "slur"), ("n1gg3r", "slur"), ("you retard", "slur"),
    ("kill yourself", "harm"), ("kys", "slur"), ("fuck you", "harm"), ("fuuuck off", "harm"), ("i will find you", "harm"),
    ("du wichser", "harm"), ("去死吧", "harm"),
    ("0x" + "ab" * 20, "addr"), ("THIS IS SO GREAT EVERYONE", "shout"),
    ("🔥" * 9, "spam"), ("aaaaaaaaaaaa", "spam"), ("spam spam spam spam spam", "spam"), ("lolololololol", "spam"),
    ("x" * 201, "long"), ("   ", "empty"),
]
for text, why in cases:
    got = chat.judge(chat.clean(text))
    check(got == why, f"refused ({why}): {text[:30]} -> {got}")
for text in ["That is it. Me too", "investigate the spec", "block 88 sealed", "spicy raccoon", "fork? no fork, ever",
             "o5 = 0 for all", "I sent 50 AGRS to my other test wallet", "Essex is nice", "the cocktail party",
             "assess the classic pass", "Scunthorpe", "who is the validator of block 12?", "NASA and the ESA",
             "gm everyone", "我喜欢这个规则", "ルールが変わった", "can you analyse this", "shiitake", "Dickens"]:
    check(chat.judge(chat.clean(text)) is None, f"allowed: {text}")
check(c.say("p1", "nope", 0, 1, 2, "hi")["error"] == "bad" and c.say("p1", tok(1), 99, 1, 2, "hi")["error"] == "bad", "a bad token or name is refused")
check(chat.clean("a​‮b\n\n c") == "ab c", "invisible and control characters go, spaces fold")
check(chat.parse_say([tok(1), "0", "1", "2", "hi%20there%21"]) == (tok(1), 0, 1, 2, "hi there!"), "a %-encoded text is read")

# strikes: a hard refusal is a strike; 1 warns, 2 mutes 10 min, 3 mutes 1 h, 4 bans until 00:00 UTC
hidden = []
c.on_hide = hidden.append
ok = c.say("s1", tok(5), 2, 2, 2, "first, a normal hello")
r1 = c.say("s1", tok(5), 2, 2, 2, "watch porn")
check(r1["error"] == "sex" and "warning" in r1["message"], f"strike 1 is a warning: {r1['message']}")
r2 = c.say("s1", tok(5), 2, 2, 2, "fuck you")
check(r2["error"] == "harm" and "muted for 10 minutes" in r2["message"], f"strike 2 mutes 10 minutes: {r2['message']}")
r = c.say("s1", tok(5), 2, 2, 2, "hello")
check(r["error"] == "muted" and "10 more minutes" in r["message"], f"a muted visitor is told how long: {r['message']}")
T[0] += 601
r3 = c.say("s1", tok(5), 2, 2, 2, "kill yourself")
check("muted for 60 minutes" in r3["message"], f"strike 3 mutes an hour: {r3['message']}")
T[0] += 3601
r4 = c.say("s1", tok(5), 2, 2, 2, "send nudes")
check("out of the troll box until 00:00 UTC" in r4["message"], f"strike 4 bans for the day: {r4['message']}")
check(ok["msg"]["id"] in hidden, "the live moderator removes all of a banned visitor's messages for everyone")
T[0] += 3600
check(c.say("s1", tok(5), 2, 2, 2, "hello again")["error"] == "banned", "still out later that day")
check(c.say("s2", tok(6), 2, 2, 2, "a different visitor")["ok"], "others can still write")

# soft refusals: every third is a strike
T[0] += 10
c.say("s3", tok(7), 1, 1, 1, "wen moon")
c.say("s3", tok(7), 1, 1, 1, "price?")
r = c.say("s3", tok(7), 1, 1, 1, "buy buy")
check(c.strikes.get("s3") == 1 and "warning" in r["message"], "three soft refusals make one strike")
# flooding the slow mode is a soft refusal
for _ in range(2):
    T[0] += 70
    c.say("s4", tok(8), 1, 1, 1, f"note {T[0]}")
    for _ in range(5):
        c.say("s4", tok(8), 1, 1, 1, "again and again")
check(c.softs.get("s4") == 2, f"hammering the slow mode counts as spam ({c.softs.get('s4')})")
# copy-paste bots: someone else's text within five minutes
T[0] += 10
c.say("b1", tok(9), 1, 1, 1, "Visit my tau channel now friends")
check(c.say("b2", tok(10), 1, 1, 1, "visit my TAU channel now friends!")["error"] == "repeat", "the same text from another visitor is refused")

# reports: three different people hide a message and strike its writer; the writer's own report does not count
T[0] += 10
m = c.say("r1", tok(11), 3, 4, 5, "rude words")["msg"]
c.report("r1", m["id"], tok(11))
c.report("q3", m["id"], tok(3)); c.report("q3", m["id"], tok(3)); c.report("q4", m["id"], tok(4))
check(m["id"] not in hidden, "two different reporters do not hide it")
check(c.report("q5", m["id"], tok(5))["hidden"] and hidden[-1] == m["id"], "the third hides it and the pages are told")
check(all(x["id"] != m["id"] for x in c.recent()["messages"]), "a hidden message is not shown")
check(c.strikes.get("r1") == 1, "and its writer gets a strike")

# owner page, hide, unban
check(c.route("/chat/admin", "key=wrong")[0] == 403, "the admin page needs the key")
k = open(key).read().strip()
page = c.route("/chat/admin", "key=" + k)
check(page[0] == 200 and b"hello Tau" in page[2] and b"Strikes today" in page[2] and b"out until 00:00 UTC" in page[2], "the admin page lists messages and strikes")
T[0] += 10
m3 = c.say("o1", tok(12), 1, 1, 1, "spam spam and more")["msg"]
check(c.route("/chat/hide", f"key={k}&id={m3['id']}")[0] == 200 and hidden[-1] == m3["id"], "the owner hides a message")
T[0] += 10
check(c.say("o1", tok(12), 1, 1, 1, "hi")["error"] == "banned", "and its writer is out for the day")
short = next(p for p in c.banned if p == "o1")[:8]
check(c.route("/chat/unban", f"key={k}&p=o1zzzzzz")[0] == 404, "an unknown visitor id is refused")
c.banned["0123abcd99"] = c.banned.pop("o1"); c.strikes["0123abcd99"] = c.strikes.pop("o1")
check(c.route("/chat/unban", f"key={k}&p=0123abcd")[0] == 200 and c.say("0123abcd99", tok(12), 1, 1, 1, "back again")["ok"], "the owner can clear a visitor")

# the day change forgets strikes, as the person hash changes then too
T[0] = (T[0] // 86400 + 1) * 86400 + 5
check(c.say("s1", tok(5), 2, 2, 2, "a new day")["ok"] and not c.strikes, "after 00:00 UTC the ban and the strikes are gone")

# storage: no address or person on disk, 24 hours kept, a restart keeps the day
st = json.load(open(path))
check(all(set(x) <= {"id", "ts", "a", "b", "c", "text", "hidden"} for x in st["msgs"]) and "s1" not in json.dumps(st), "nothing about the writer is stored")
c2 = chat.Chat(path, key, clock)
check("a new day" in [x["text"] for x in c2.recent()["messages"]], "a restart keeps the shown messages")
T[0] += 86400
check(c2.recent()["messages"] == [] and json.load(open(path))["msgs"] == [], "after 24 hours everything is gone, also on disk")

# slow mode and the off switch
c3 = chat.Chat(os.path.join(d, "c3.json"), key, clock)
oks = sum(bool(c3.say(f"q{i}", tok(i), 0, 0, 0, f"message number {i} here").get("ok")) for i in range(40))
check(oks == chat.ROOM_PER_MIN, f"the room takes at most ROOM_PER_MIN messages a minute ({oks})")
os.environ["CHAT_ENABLED"] = "0"
c4 = chat.Chat(os.path.join(d, "c4.json"), key, clock)
check(c4.say("z", tok(1), 0, 0, 0, "hi")["error"] == "closed" and c4.recent()["enabled"] is False, "CHAT_ENABLED=0 closes the room")

sys.exit(1 if failed else 0)

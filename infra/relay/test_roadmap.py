"""Unit test of the road-to-mainnet comments (roadmap.py), no network.

Run: python test_roadmap.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chat  # noqa: E402
import roadmap  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T = [1_793_145_600.0 + 3600]   # 2026-10-28 01:00 UTC
clock = lambda: T[0]  # noqa: E731
d = tempfile.mkdtemp()
c = chat.Chat(os.path.join(d, "c.json"), os.path.join(d, "c.key"), clock)
path = os.path.join(d, "r.json")
r = roadmap.Roadmap(c, path, clock)
tok = lambda i: f"{i:032x}"  # noqa: E731
hidden = []
r.on_hide = hidden.append

ok = r.say("p1", tok(1), 0, 1, 2, "rule-places", "problem", "Two places for the whole network is too few for a wallet product.")
check(ok.get("ok") and ok["comment"]["name"] == "Quiet Heron" and ok["comment"]["part"] == "problem", "a comment with the animal name and part")
check(r.say("p1", tok(1), 0, 1, 2, "rule-places", "path", "And another thought right after the first.")["error"] == "slow", "one comment a minute")
T[0] += 61
check(r.say("p1", tok(1), 0, 1, 2, "rule-places", "path", "ok")["error"] == "short", "too short")
check(r.say("p1", tok(1), 0, 1, 2, "rule-places", "path", "x" * 601)["error"] == "long", "too long")
check(r.say("p1", tok(1), 0, 1, 2, "Bad Item", "path", "a fine comment text here")["error"] == "bad", "a bad item id")
check(r.say("p1", tok(1), 0, 1, 2, "rule-places", "other", "a fine comment text here")["error"] == "bad", "a bad part")
gh = r.say("p1", tok(1), 0, 1, 2, "rule-places", "path", "See https://github.com/IDNI/tau-testnet/issues/85 for the measured cap.")
check(gh.get("ok") and "github.com" in gh["comment"]["text"], "a GitHub link is allowed")
T[0] += 61
check(r.say("p1", tok(1), 0, 1, 2, "rule-places", "path", "Look at https://evil.example.com/x for more")["error"] == "link", "other links are refused")
T[0] += 61
check(r.say("p1", tok(1), 0, 1, 2, "rule-places", "path", "Only a link https://youtu.be/S6ggPxF1o5g")["error"] == "short", "a bare link is too short")
check(r.say("p2", tok(2), 1, 1, 1, "rule-places", "-", "Two places for the whole network is too few for a wallet product.")["error"] == "repeat", "a copy of another comment is refused")

# one strike ladder with the troll box
s = r.say("p3", tok(3), 2, 2, 2, "sync-bugs", "-", "you are a retard and so is this page")
check(s["error"] == "slur" and "warning" in s["message"], "a slur is a strike, told as a warning")
check(c.strikes.get("p3") == 1, "the strike lands on the troll box's ladder")
c.strike("p3", 3)
check(r.say("p3", tok(3), 2, 2, 2, "sync-bugs", "-", "a perfectly polite comment now")["error"] == "banned", "out of the troll box = out of the comments")

# a ban in the troll box sweeps today's comments
T[0] += 61
p4 = r.say("p4", tok(4), 3, 3, 3, "mempool", "path", "Drop sealed transactions from the mempool when a block is applied.")
check(p4.get("ok"), "p4 comments")
c.strike("p4", 4)
check(p4["comment"]["id"] in hidden and not r.thread("mempool")["comments"], "a day ban hides the writer's comments")

# reports, own delete, owner hide
T[0] += 61
p5 = r.say("p5", tok(5), 4, 4, 4, "mempool", "-", "I see sealed transactions as pending on my node too.")["comment"]
for i, who in enumerate(["p6", "p7"]):
    r.report(who, p5["id"], tok(10 + i))
check(r.thread("mempool")["comments"], "two reports keep it")
r.report("p5", p5["id"], tok(5))
check(r.thread("mempool")["comments"], "the writer's own report does not count")
r.report("p8", p5["id"], tok(12))
check(not r.thread("mempool")["comments"] and c.strikes.get("p5") == 1, "three reports hide it and strike its writer")
T[0] += 61
p9 = r.say("p9", tok(9), 5, 5, 5, "mempool", "-", "Would a reorg put them back into the mempool?")["comment"]
check(not r.delete(p9["id"], tok(8)), "someone else's token cannot delete")
check(r.delete(p9["id"], tok(9)) and not r.thread("mempool")["comments"] and not c.strikes.get("p9"), "the writer deletes their own, no strike")
T[0] += 61
p10 = r.say("p10", tok(20), 6, 6, 6, "mempool", "-", "Spammy but passed the filter somehow, owner hides.")["comment"]
check(r.owner_hide(p10["id"]) and c.banned.get("p10"), "owner hide puts the writer out for the day")

# agree
check(r.add_agree("p1", "mempool", tok(1))["agree"] == 1, "agree counts")
check(r.add_agree("p1", "mempool", tok(1))["agree"] == 1, "the same browser counts once")
check(r.add_agree("p2", "mempool", tok(2))["agree"] == 2, "another browser counts")

# limits per hour
T[0] += 86400
for i in range(6):
    T[0] += 61
    r.say("p11", tok(11), 0, 0, 0, "limits", "-", f"Comment number {i} about the limits, all different words {i * 7}.")
T[0] += 61
check(r.say("p11", tok(11), 0, 0, 0, "limits", "-", "One more comment within the same hour.")["error"] == "hour", "six an hour")

# HTTP and storage
st, ct, body = r.route("/roadmap", "")
got = json.loads(body)
check(st == 200 and got["comments"].get("rule-places") == 2 and got["agree"]["mempool"] == 2, "GET /roadmap counts")
st, ct, body = r.route("/roadmap", "item=rule-places")
check(len(json.loads(body)["comments"]) == 2 and "tok" not in json.loads(body)["comments"][0], "GET /roadmap?item= without the token hash")
check(r.route("/roadmap/admin", "key=wrong")[0] == 403, "admin needs the key")
check(r.route("/roadmap/admin", "key=" + c.key)[0] == 200, "admin with the chat key")
again = roadmap.Roadmap(chat.Chat(os.path.join(d, "c.json"), os.path.join(d, "c.key"), clock), path, clock)
check(len(again.thread("rule-places")["comments"]) == 2 and again.counts()["agree"]["mempool"] == 2, "comments and agrees survive a restart")
check(roadmap.parse_say([tok(1), "0", "1", "2", "mempool", "path", "a%20b"]) == (tok(1), 0, 1, 2, "mempool", "path", "a b"), "parse_say")

print("\n" + ("all ok" if not failed else f"{failed} failed"))
sys.exit(1 if failed else 0)

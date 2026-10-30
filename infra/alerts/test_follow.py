"""Personal alerts (follow.py): deep link codes, what a transaction means for a followed account, rule change
news, the commands, and whole watcher rounds against a fake relay and a fake Telegram.

Run: python test_follow.py
"""
import asyncio
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ.update(FOLLOW_STATE=os.path.join(TMP, "follows.json"), FOLLOW_HOURLY="3", FOLLOW_MAX_ADDRESSES="2")
sys.path.insert(0, os.path.dirname(__file__))

import follow  # noqa: E402

A = "a1" * 48
B = "b2" * 48
C = "c3" * 48
PID = "f00d" * 16
fails = []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        fails.append(what)


# ---------------- deep links ----------------
code = follow.link_code(A)
check(len(code) == 64 and follow.start_code(code) == A, "address start code is 64 characters and reads back")
pcode = follow.link_code(PID)
check(len(pcode) == 44 and pcode[0] == "p" and follow.start_code(pcode) == PID, "rule change start code reads back")
check(follow.start_code("height") is None and follow.start_code("help") is None, "button words are not codes")
check(follow.start_code("!" * 64) is None, "junk is not a code")

# ---------------- transactions ----------------
t = {"tx_type": "user_tx", "sender_pubkey": A, "operations": {"1": [[A, B, "25"], [A, C, "5"]], "0": "o5[t] = { #b1 }:sbf."}}
la, lb = follow.tx_lines(t, A), follow.tx_lines(t, B)
check(any("Sent 25 test AGRS" in x for x in la) and any("own rule is now on the chain" in x for x in la), "sender sees its transfer and its rule")
check(len(lb) == 1 and "Received 25 test AGRS" in lb[0], "recipient sees only what it received")
check(follow.tx_lines(t, "d4" * 48) == [], "an outsider sees nothing")
check("Got a rule offer" in follow.tx_lines({"tx_type": "rule_offer", "sender_pubkey": B, "recipient_pubkey": A}, A)[0], "rule offer to it")
check("Voted no" in follow.tx_lines({"tx_type": "consensus_rule_vote", "sender_pubkey": A, "approve": False}, A)[0], "its vote")
check("co-sign" in follow.tx_lines({"tx_type": "approval_request", "sender_pubkey": B, "recipient_pubkey": C, "amount": 9, "approvers": [A]}, A)[0],
      "asked to co-sign")
check("pulled back until block #90" in follow.tx_lines({"tx_type": "retractable_transfer", "sender_pubkey": A, "recipient_pubkey": B,
                                                         "amount": "7", "release_at_height": 90}, A)[0], "retractable transfer")
blocks = [{"header": {"block_number": 41}, "transactions": [t, {"tx_type": "user_tx", "sender_pubkey": C, "operations": {"1": [[C, B, "1"]]}}]}]
ev = follow.block_events(blocks, {A, B})
check(len(ev[A]) == 3 and len(ev[B]) == 2 and all(h == 41 for h, _ in ev[B]), "block events per watched address")
txt = follow.moves_text({A: ev[A]})
check("An account you follow moved" in txt and "/explorer/?b=41" in txt and "/stop" in txt and "no value" in txt, "moves message")

# ---------------- rule change news ----------------
p = {"id": PID, "title": "Lower the fee", "status": "agreed", "thr": 2, "counted_votes": 2, "activate_at": 99, "proposer": A,
     "votes": [{"voter": B, "approve": True, "counted": True, "h": 50}, {"voter": C, "approve": True, "counted": True, "h": 51}]}
news = follow.prop_news(p, ["voting", 1])
check(len(news) == 2 and "voted yes at block #51" in news[0] and "Agreed" in news[1], "one new vote and agreed")
check(follow.prop_news(p, None) == [], "first look tells nothing")

# ---------------- commands ----------------
st = follow.Store()
pj = {"proposals": [p], "chain": {"block1_hash": "11" * 32}}
check("private chat" in follow.command(st, 7, "follow", A, pj, False), "groups are sent to a private chat")
r = follow.command(st, 7, "follow", A, pj, True)
check("Following" in r and "/stop" in r and st.chat(7)["a"] == [A], "follow an address")
check("/donate/" in r and "voluntary" in r, "the very first follow mentions donations once")
check("already" in follow.command(st, 7, "follow", A.upper(), pj, True), "following twice")
check("/donate/" not in follow.command(st, 7, "follow", B, pj, True), "later follows do not")
check("most I can watch" in follow.command(st, 7, "follow", C, pj, True), "cap per chat")
check("is decided" not in follow.command(st, 7, "follow", PID[:16], pj, True) and st.chat(7)["p"] == [PID], "follow a rule change by its short id")
check("do not know" in follow.command(st, 7, "follow", "ab" * 32, pj, True), "unknown rule change")
lst = follow.command(st, 7, "following", None, pj, True)
check("Lower the fee" in lst and "/unfollow" in lst, "following lists both kinds")
check("Stopped following" in follow.command(st, 7, "unfollow", B[:16], pj, True) and st.chat(7)["a"] == [A], "unfollow by prefix")
saved = follow.Store()
check(saved.chat(7)["a"] == [A] and saved.chat(7)["p"] == [PID], "the store survives a restart")
check("forgot this chat" in follow.command(st, 7, "stop", None, pj, True) and st.chat(7) is None and follow.Store().chat(7) is None, "/stop deletes the chat")


# ---------------- whole rounds ----------------
class Fake:
    def __init__(self):
        self.head, self.sent, self.blocks, self.pj, self.gone = 40, [], {}, {"chain": {"block1_hash": "11" * 32}, "proposals": []}, set()

    async def send(self, cid, text):
        if cid in self.gone:
            return "gone"
        self.sent.append((cid, text))
        return "ok"

    async def lookup(self, cmd):
        _, s, n = cmd.split()
        got = [self.blocks.get(h, {"header": {"block_number": h}, "transactions": []}) for h in range(int(s), min(int(s) + int(n), self.head + 1))]
        return {"status": "ok", "command": "getblockrange", "data": {"blocks": got, "head": self.head}}


async def rounds():
    os.remove(follow.STATE) if os.path.exists(follow.STATE) else None
    f = Fake()
    st = follow.Store()
    w = follow.Watcher(st, f.send, f.lookup, lambda: f.pj, lambda: f.head)
    st.add("7", "a", A)
    st.add("8", "a", B)
    await w.round(1000)
    check(st.d["head"] == 40 and not f.sent, "first round starts at the tip and says nothing")
    f.head = 41
    f.blocks[41] = blocks[0]
    await w.round(1001)
    check(len(f.sent) == 2 and {c for c, _ in f.sent} == {"7", "8"}, "one message for each chat whose account moved")
    f.sent.clear()
    # a rule change by A appears with one vote already: news for chat 7 (its proposer)
    q = dict(p, status="voting", counted_votes=1, votes=p["votes"][:1])
    f.pj = {"chain": {"block1_hash": "11" * 32}, "proposals": [q]}
    await w.round(1002)
    check(len(f.sent) == 1 and f.sent[0][0] == "7" and "proposed by" in f.sent[0][1] and "voted yes" in f.sent[0][1], "votes on a rule change its account proposed")
    f.sent.clear()
    st.add("9", "p", PID)
    f.pj = {"chain": {"block1_hash": "11" * 32}, "proposals": [dict(p, status="active", activated_at=99)]}
    await w.round(1003)
    nine = [t for c, t in f.sent if c == "9"]
    check(nine and "In force" in nine[0] and "stop following it" in nine[0] and "9" in st.chats and st.chat("9")["p"] == [], "decided: told, then unfollowed")
    f.sent.clear()
    # the hourly cap: chat 7 has had 2 messages; the 3rd is replaced by the pause note, then quiet
    for i in range(3):
        f.head += 1
        f.blocks[f.head] = {"header": {"block_number": f.head}, "transactions": [t]}
        await w.round(1004 + i)
    seven = [x for c, x in f.sent if c == "7"]
    check(len(seven) == 1 and "pause" in seven[0], "hourly cap: one pause note, then quiet")
    # a person who blocked the bot is forgotten
    st.add("10", "a", B)
    f.gone.add("10")
    f.head += 1
    f.blocks[f.head] = {"header": {"block_number": f.head}, "transactions": [t]}
    await w.round(1010)
    check(st.chat("10") is None, "blocked the bot: chat forgotten")
    # chain restart: no old news
    f.sent.clear()
    f.pj = {"chain": {"block1_hash": "22" * 32}, "proposals": []}
    f.head = 5
    await w.round(5000)
    check(st.d["head"] == 5 and not f.sent and st.d["props"] == {}, "chain restart starts again at the tip")
    # far behind: skip to the tip
    f.head = 5 + follow.BACKLOG + 50
    await w.round(5001)
    check(st.d["head"] == f.head and not f.sent, "long gap: skip to the tip")


asyncio.run(rounds())

# ---------------- bot.py reads the commands ----------------
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
import bot  # noqa: E402
check(bot.parse("/start " + code, "tauhud_alerts_bot", True) == ("follow", A), "deep link from an account page")
check(bot.parse("/start " + pcode, "tauhud_alerts_bot", True) == ("follow", PID), "deep link from a proposal")
check(bot.parse("/start height", "tauhud_alerts_bot", True) == ("height", None), "old start buttons still work")
check(bot.parse("/follow " + A, "", True) == ("follow", A) and bot.parse("follow " + A, "", True) == ("follow", A), "follow as command and as words")
check(bot.parse("/stop", "", True) == ("stop", None) and bot.parse("/following", "", True) == ("following", None), "stop and following")
check(bot.parse("stop", "", True) == ("stop", None) and bot.parse("/unfollow all", "", True) == ("unfollow", "all"), "stop in words, unfollow all")
print()
print("all ok" if not fails else f"{len(fails)} failed")
sys.exit(1 if fails else 0)

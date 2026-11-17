"""Unit test of the room's line (roomline.py) with a stand-in for the API, no network.

Run: python test_roomline.py
"""
import asyncio
import json
import os
import sys
import tempfile
import urllib.parse
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.pop("CHAT_AI_KEY", None)
os.environ.pop("ROOM_AI_KEY", None)
os.environ["AI_USAGE_DIR"] = tempfile.mkdtemp()
import roomline  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


class Fake:
    def __init__(self, answer, fail=False):
        self.answer, self.fail, self.sent = answer, fail, []
        self.messages = self

    async def create(self, **kw):
        self.sent.append(kw)
        if self.fail:
            raise RuntimeError("down")
        return NS(stop_reason="end_turn", content=[NS(type="text", text=self.answer)], usage=None)


def q(text, facts="height 12 · validators 5", hist=None):
    return urllib.parse.quote(json.dumps({"q": text, "f": facts, "h": hist or []}))


async def main():
    T = [1_793_149_200.0]
    r = roomline.RoomLine(lambda: T[0])
    check(not r.on and (await r.ask("1", q("hi there")))["why"] == "off", "off without a key: the script answers")
    r.client = Fake('{"lines": ["it is a page of the record.", "ask: who seals them?"]}')
    a = await r.ask("1", q("what's the meaning of a merkle root", hist=[["what is a block", "one page of the record."]]))
    check(a["lines"] == ["it is a page of the record.", "ask: who seals them?"], "an answer comes back as its lines")
    sent = r.client.sent[-1]
    check(sent["messages"][-1]["content"].startswith("CHAIN FACTS") and "merkle" in sent["messages"][-1]["content"]
          and sent["messages"][0]["content"] == "what is a block" and sent["messages"][1]["role"] == "assistant",
          "the facts, the question and the last exchange are sent")
    check((await r.ask("1", q("again")))["why"] == "wait", "two questions within two seconds: wait")
    T[0] += 3
    check((await r.ask("1", "%7Bbroken"))["why"] == "bad", "a broken request is refused")
    check((await r.ask("1", q("x")))["why"] == "bad", "a one-letter question is not sent")
    r.client = Fake("", fail=True)
    check((await r.ask("2", q("hello?")))["why"] == "error", "an API error: the script answers")
    r.client = Fake('{"lines": ["' + "a" * 400 + '", "b", "c", "d"]}')
    a = await r.ask("3", q("long"))
    check(len(a["lines"]) == 3 and len(a["lines"][0]) == 260, "at most three lines of 260 characters")
    r.client, r.used = Fake('{"lines": ["x"]}'), r.daily
    check((await r.ask("4", q("cap?")))["why"] == "cap" and not r.client.sent, "past the day's cap nothing is sent")
    T[0] += 86400
    r.client = Fake('{"lines": ["new day"]}')
    for i in range(roomline.PER_IP_DAY):
        T[0] += 3
        await r.ask("5", q(f"question {i}"))
    T[0] += 3
    check((await r.ask("5", q("one more")))["why"] == "cap", "one visitor's own cap per day")


asyncio.run(main())
print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

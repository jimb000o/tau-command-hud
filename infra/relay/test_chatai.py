"""Unit test of the troll box's AI moderator (chatai.py) with a stand-in for the API, no network.

Run: python test_chatai.py
"""
import asyncio
import os
import sys
import tempfile
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.pop("CHAT_AI_KEY", None)
import chat  # noqa: E402
import chatai  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


class Fake:
    """Answers like messages.create; remembers what it was sent."""
    def __init__(self, answer, fail=False):
        self.answer, self.fail, self.sent = answer, fail, []
        self.messages = self

    async def create(self, **kw):
        self.sent.append(kw)
        if self.fail:
            raise RuntimeError("down")
        return NS(stop_reason="end_turn", content=[NS(type="text", text=self.answer)])


async def main():
    ai = chatai.ChatAI()
    check(not ai.on and await ai.verdict("hi", []) is None, "off without CHAT_AI_KEY: every message stays")
    ai.client = Fake('{"remove": true, "category": "sexual"}')
    check(await ai.verdict("something sly", ["a", "b"]) == "sexual", "a flagged message gives its category")
    sent = ai.client.sent[-1]
    check("something sly" in sent["messages"][0]["content"] and "earlier" in sent["messages"][0]["content"]
          and sent["output_config"]["format"]["type"] == "json_schema", "only the texts are sent, as structured output")
    ai.client = Fake('{"remove": false, "category": "none"}')
    check(await ai.verdict("gm", []) is None, "a fine message stays")
    ai.client = Fake("", fail=True)
    check(await ai.verdict("gm", []) is None, "an API error keeps the message")
    ai.client, ai.daily, ai.used = Fake('{"remove": true, "category": "spam"}'), 2, 2
    check(await ai.verdict("x", []) is None and not ai.client.sent, "past the day's cap nothing is sent")

    # chat.flag: hidden for everyone, a strike for the writer
    T = [1_793_149_200.0]
    c = chat.Chat(os.path.join(tempfile.mkdtemp(), "c.json"), os.path.join(tempfile.mkdtemp(), "k"), lambda: T[0])
    hidden = []
    c.on_hide = hidden.append
    m = c.say("w1", "ab" * 16, 1, 1, 1, "an innocent looking line")["msg"]
    check(c.before(m["id"] + 1) == ["an innocent looking line"], "the context is the shown texts before")
    check(c.flag(m["id"]) and hidden == [m["id"]] and c.strikes["w1"] == 1, "a flagged message is hidden and strikes its writer")


asyncio.run(main())
sys.exit(1 if failed else 0)

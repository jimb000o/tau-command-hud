"""Unit test of the repeats Kilian saw in the channel (19 Nov 2026), no network: one restart is one post even when the
new chain's first block changes before our node read it, a second restart within a week says the count instead of the
same paragraph again, a Telegram post whose answer got lost is never sent a second time, and what a restart brings
with it (dropped transactions, slow first blocks, the bootnode coming back) is no finding and no busy stretch.

Run: python test_post_repeats.py   (needs websockets==15.0.1)
"""
import os
import sys
import tempfile
import time

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="t", TELEGRAM_CHAT="@x")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402
import findings  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


# 1. one restart, one item: the new chain's block 1 changed before the old chain's record was replaced (18 Nov 2026)
w = alerts.Watcher.__new__(alerts.Watcher)
w.state = {"items": [], "primed": True}
w.blocks, w.dirty_public = {}, False
old = {"block1_hash": "a" * 64, "head": 1372}
w.chain_restart(old, "b" * 64)
w.chain_restart(old, "c" * 64)
rs = [it for it in w.state["items"] if it["kind"] == "restart"]
check(len(rs) == 1 and "#1,372" in " ".join(rs[0]["facts"]), f"one restart of one chain is one post: {len(rs)}")
check(w.state["findings"].get("restart_at"), "the findings learn when the restart was")
first = alerts.telegram_text(rs[0])
check(alerts.RESTART_FOR_YOU in first and "in 7 days" not in first, "the first restart in a week tells what it means for a wallet")

# 2. the next restart of the week: the count is the news, the wallet paragraph was said
w.chain_restart({"block1_hash": "c" * 64, "head": 107}, "d" * 64)
rs = [it for it in w.state["items"] if it["kind"] == "restart"]
second = alerts.telegram_text(rs[0])
check(len(rs) == 2 and "the second time in 7 days" in second and alerts.RESTART_FOR_YOU not in second and "#107" in second,
      f"a second restart within 7 days is shorter and counts: {second}")
for it in w.state["items"]:
    it["seen"] -= 8 * 86400
w.chain_restart({"block1_hash": "d" * 64, "head": 900}, "e" * 64)
third = alerts.telegram_text(w.state["items"][0])
check(alerts.RESTART_FOR_YOU in third and "in 7 days" not in third, "after a quiet week the full post again")


# 3. Telegram: the request went out, the answer got lost -> counted as posted, never a second post
class Lost(alerts.Telegram):
    def __init__(self, err):
        self.err, self.calls = err, 0

    def call_raw(self, method, body, ctype="application/json"):
        self.calls += 1
        return False, None, self.err, {}


lost = Lost("TimeoutError")
check(lost.call("sendMessage", b'{"chat_id": "@x", "text": "hi"}', "application/json")[0], "a read timeout counts as posted")
check(Lost("RemoteDisconnected").call("sendPhoto", b"x", "multipart/form-data")[0], "a dropped connection after sending too")
check(not Lost("URLError").call("sendMessage", b"{}", "application/json")[0], "a request that never went out is tried again")
check(not Lost("HTTP 429: Too Many Requests").call("sendMessage", b"{}", "application/json")[0], "Telegram's own refusal is a failure")
check(not Lost("TimeoutError").call("getMe", b"", "application/json")[0], "only posts are counted as sent")

# 4. what a restart brings is no finding: dropped transactions in the hour after it give no post, no busy stretch
T = 1_800_000_000 - 1_800_000_000 % 86400 + 8 * 3600


def health(sealed=0, waiting=0, pace=60):
    return {"expected_block_seconds": 60, "factors": [
        {"key": "node", "value": "yes"}, {"key": "last_block", "value": 10}, {"key": "sync", "value": "in sync"},
        {"key": "pace", "value": pace}, {"key": "mempool", "value": {"waiting": waiting, "sealed": sealed}}]}


def snap(h):
    return {"health": h, "peers": {"bootnode": "b", "counts": {"connected": 3}, "peers": [{"id": "b", "connected": True}]},
            "status": {"reorgs": []}, "blocks": {1: {"header": {"timestamp": T}}}}


st = findings.fresh_state()
findings.observe(st, snap(health()), T)
st["restart_at"] = T + 60
got = []
for i in range(2, 60):   # ghosts right after the restart
    got += findings.observe(st, snap(health(sealed=7, waiting=12)), T + 60 * i)
check(got == [] and not st["held"], f"a finding in the restart's first 90 minutes is part of the restart: {[g['what'] for g in got]}")
st2 = findings.fresh_state()
findings.observe(st2, snap(health()), T)
st2["restart_at"] = T - 3 * 3600
got2 = []
for i in range(2, 60):
    got2 += findings.observe(st2, snap(health(sealed=7, waiting=12)), T + 60 * i)
check([g["what"] for g in got2] == ["ghost start"], "hours after a restart a finding is news again")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

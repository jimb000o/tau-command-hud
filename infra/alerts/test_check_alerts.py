"""Unit test of the channel check and the silence watch (no network): the check names the reason a channel cannot be
posted to, the watch warns after SILENCE_HOURS without a good send, and posting.json is written.

Run: python test_check_alerts.py   (needs websockets==15.0.1)
"""
import asyncio
import json
import os
import sys
import tempfile
import time

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_CHAT_ID="@tauHUDcom",
                  X_API_KEY="k", X_API_SECRET="s", X_ACCESS_TOKEN="t", X_ACCESS_SECRET="u")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


# Telegram: the token, then the bot's standing in the channel
replies = {}


def fake_raw(self, method, body, ctype="application/json"):
    return replies[method]


alerts.Telegram.call_raw = fake_raw
tg = alerts.Telegram()
replies["getMe"] = (False, None, "HTTP 401: Unauthorized", {})
ok, why = tg.check()
check(not ok and "token refused" in why and "BotFather" in why, "a refused token says so, with the way out")
replies["getMe"] = (True, None, "", {"ok": True, "result": {"id": 42, "username": "tauhud_alerts_bot"}})
replies["getChatMember"] = (True, None, "", {"ok": True, "result": {"status": "member"}})
ok, why = tg.check()
check(not ok and "not an administrator" in why and "Post messages" in why, "a bot that is only a member cannot post, and the fix is named")
replies["getChatMember"] = (False, None, "HTTP 400: Bad Request: chat not found", {})
ok, why = tg.check()
check(not ok and "cannot see @tauHUDcom" in why, "a channel the bot cannot see")
replies["getChatMember"] = (True, None, "", {"ok": True, "result": {"status": "administrator", "can_post_messages": True}})
ok, why = tg.check()
check(ok and "may post" in why, "an administrator who may post: ok")

# X: GET /2/users/me, with a GET signature
calls = []


def fake_once(self, req, want_reply=False):
    calls.append((req.get_method(), req.full_url, req.get_header("Authorization")))
    return (False, None, "HTTP 401: Unauthorized", {}) if want_reply else (False, None, "HTTP 401: Unauthorized")


alerts.X.call_once = fake_once
x = alerts.X()
ok, why = x.check()
check(not ok and "keys refused" in why and "copy all four" in why, "refused X keys name the fix")
check(calls[-1][0] == "GET" and calls[-1][1] == alerts.X.ME and 'oauth_signature="' in calls[-1][2], "the check is a signed GET of users/me")
check(not alerts.SENT["x"].get("last_error"), "the check is not counted as a failed post")
alerts.X.call_once = lambda self, req, want_reply=False: (True, None, "", {"data": {"username": "TauHUDcom"}}) if want_reply else (True, None, "")
check(x.check() == (True, "keys open @TauHUDcom"), "good keys name the account")
check(not alerts.X({"X_API_KEY": "", "X_API_SECRET": "", "X_ACCESS_TOKEN": "", "X_ACCESS_SECRET": ""}).check()[0], "off without keys")

# sends record themselves; the silence watch warns after SILENCE_HOURS and posting.json tells
alerts.note_send("telegram", False, "HTTP 401: Unauthorized")
check(alerts.SENT["telegram"]["last_error"] == "HTTP 401: Unauthorized", "a failed send is remembered")
w = alerts.Watcher([tg, x])
now = time.time()
w.watch_silence(now)
check(not alerts.SENT["telegram"].get("silent_hours"), "the first hour is not silence")
w.watch_silence(now + 10 * 3600)
check(not alerts.SENT["telegram"].get("silent_hours"), "ten hours are not silence")
w.watch_silence(now + 27 * 3600)
check(alerts.SENT["telegram"].get("silent_hours") == 27 and alerts.SENT["x"].get("silent_hours") == 27, "27 hours without a good send: silent")
alerts.SENT["x"]["last_ok"] = now + 28 * 3600   # a good send at hour 28
w.watch_silence(now + 29 * 3600)
check(not alerts.SENT["x"].get("silent_hours") and alerts.SENT["telegram"].get("silent_hours") == 29, "a good send ends the silence for that channel")
with open(os.path.join(TMP, "posting.json")) as f:
    pj = json.load(f)
check(pj["channels"]["telegram"]["last_error"] == "HTTP 401: Unauthorized" and pj["channels"]["x"]["last_ok"], "posting.json carries it")
asyncio.run(w.check_outlets())
check(pj := json.load(open(os.path.join(TMP, "posting.json"))), "posting.json after the start check")
check(pj["channels"]["telegram"]["check"]["ok"] and pj["channels"]["x"]["check"]["ok"], "the start check's answers are in posting.json")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

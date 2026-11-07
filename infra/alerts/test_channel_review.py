"""Unit test of the channel review fixes of 7 November 2026 (no network): a restart day is not told as a rule change,
the slowest hour shows beside the median pace, the day's node peak, one way to write a time, the weekly digest drops
repeated lines, firsts say whose wallet, chain posts get buttons that fit, the challenge reminder names its task.

Run: python test_channel_review.py   (needs websockets==15.0.1)
"""
import os
import sys
import tempfile
from datetime import datetime, timezone

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="", SITE_URL="https://tauhud.com",
                  TICKER_OWNER_CHAT="")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402
import findings  # noqa: E402
import firsts  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


END = datetime(2026, 11, 6, 19, 0, tzinfo=timezone.utc).timestamp()


def day(events=(), slow=None, blocks=499, peak=None, online=2, wallets=None):
    return {"end": END, "blocks": blocks, "pace": 60.0, "txs": 572, "senders": 16, "practice": 0, "practice_why": "",
            "events": list(events), "online": online, "last_block": None, "coming": [], "wallets": wallets, "slow": slow,
            "peak": peak}


# a restart day: no "without a fork or a restart" line, a restart lead instead
r = day([alerts.RESTART_HEADLINE])
t = alerts.today_text(r)
check("without a fork or a restart" not in t and "started over today" in t, "restart day: no rule-change sentence, says it started over")
check("today's is above" not in alerts.today_why(r), "restart alone is not 'today's [rule change] is above'")
r = day([alerts.RESTART_HEADLINE, "Now in force: New fee rule"])
check("without a fork or a restart" in alerts.today_why(r), "a real rule change on a restart day keeps the rule-change sentence")

# slowest hour
ts = [END - 9 * 3600 + i * 60 for i in range(9 * 60)]
ts = [x for x in ts if not (END - 8 * 3600 <= x < END - 7 * 3600)] + [END - 8 * 3600 + i * 257 for i in range(14)]
ts.sort()
sl = alerts.slowest_hour(ts, END, 60.0)
check(sl is not None and sl["blocks"] <= 15 and sl["usual"] == 60, f"slowest hour found: {sl}")
check(alerts.slowest_hour([END - 3 * 3600 + i * 60 for i in range(180)], END, 60.0) is None, "an even day has no slowest hour")
t = alerts.today_text(day(slow=sl))
check("usually one every 60 seconds" in t and "slowest hour from" in t and " DE (" in t, "pace says 'usually', slowest hour in DE (UTC)")
check("kept one block a minute" not in (alerts.today_why(day(slow=sl)) or ""), "a slow day is not called steady")

# node peak
t = alerts.today_text(day(peak=9))
check("2 nodes online now, up to 9 earlier today" in t, "evening count carries the day's peak")
check("earlier today" not in alerts.today_text(day(peak=2)), "no peak line when the count stayed")
check(alerts.NEWNODE_HOLD == 21600 or os.environ.get("NEWNODE_HOLD_SECONDS"), "a peer must stay 6 h before it gets a post")

# one way to write a time
ts1 = datetime(2026, 11, 6, 15, 0, tzinfo=timezone.utc).timestamp()
check(findings.hm(ts1) == "16:00 DE (15:00 UTC)", f"time format: {findings.hm(ts1)}")

# digest drops a line told twice under two areas
items = [{"area": "Rabbit", "line": "Cruise ships, after MS Dry Run's first call.", "on": "2026-11-06"},
         {"area": "White Rabbit Key", "line": "Cruise ships, after MS Dry Run's first call.", "on": "2026-11-06"},
         {"area": "HUD", "line": "Ghosts mark only ghosts.", "on": "2026-11-06"}]
d = alerts.digest_text(items, 5)
check(d.count("first call") == 1 and "2 smaller changes" in d, "digest: a repeated line counts once")
check("not news from the testnet" not in d, "digest: no footer line")

# firsts say whose wallet
f = {"key": "time_lock", "h": 104, "tx": "ab" * 32, "from": "k1"}
check("sent by one of our simulated cruise passengers" in firsts.telegram_text([f], "X", {"k1": "cruise"}), "first: our wallet named")
check("sent by a wallet that is not ours and not IDNI" in firsts.telegram_text([f], "X", {}), "first: unknown wallet = not ours")
check("sent by" not in firsts.telegram_text([f], "X", None), "first: no tags known, nothing claimed")

# buttons that fit
b = alerts.item_buttons({"kind": "restart"})
check("wallet" in str(b) and "Ask the bot" not in str(b), "restart post: wallet + stats buttons")
b = alerts.item_buttons({"kind": "agreed", "link": "https://tauhud.com/proposals/#abc"})
check("proposals/#abc" in str(b) and "/vote/" in str(b), "rule change: its proposal + vote buttons")
rs = alerts.describe({"kind": "restart", "old_tip": 4528}, None, 0, None)
check(alerts.RESTART_FOR_YOU in rs["facts"] and rs["headline"] == alerts.RESTART_HEADLINE, "restart post says what it means for your wallet")

# --test never posts to the channel: no owner chat → refuses
check(alerts.send_test() == 1, "--test without a private chat posts nothing")

# challenge reminder names the task
w = alerts.Watcher.__new__(alerts.Watcher)
w.state = {"challenge": {"id": alerts.gazette.CHALLENGES[0]["id"], "since": END - 86400, "ends": END + 86400}}
line = w.challenge_line()
check(line.startswith("<b>This week's task") and "Write a rule" in line, f"challenge line: {line[:80]}")
w.state = {}
check(w.challenge_line() == "", "no open challenge: empty line")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

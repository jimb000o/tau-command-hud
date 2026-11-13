"""Unit test of the restart post's brief (no network): a small local git repository stands in for IDNI's; the brief
reads the news line's headlines since the chain before and how the starting state differs, a clean answer makes the
restart post say what the new chain brings (Telegram and X), a number the input does not hold keeps the short post,
and the alerts service waits for the brief at most RESTART_BRIEF_WAIT_MINUTES.

Run: python test_restart_brief.py   (needs git and websockets==15.0.1)
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime

TMP = tempfile.mkdtemp()
SRC = os.path.join(TMP, "src")
os.environ.update(PUBLIC_DIR=TMP, STATE_PATH=os.path.join(TMP, "alerts.json"), RESTART_BRIEF_PATH=os.path.join(TMP, "restart.json"),
                  TELEGRAM_BOT_TOKEN="", X_API_KEY="", NEWS_AI_KEY="test", DEVPULSE_CLONES=os.path.join(TMP, "clones"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402
import restart_brief as rb  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


def at(s: str) -> int:
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def run(*a, ts=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="Dev", GIT_AUTHOR_EMAIL="dev@example.org", GIT_COMMITTER_NAME="Dev",
               GIT_COMMITTER_EMAIL="dev@example.org")
    if ts:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"@{ts} +0000"
    return subprocess.run(["git", "-C", SRC, *a], check=True, capture_output=True, text=True, env=env).stdout.strip()


def genesis(ts, accounts, meta, rules, msg):
    os.makedirs(os.path.join(SRC, "networks", "tau-testnet-v2"), exist_ok=True)
    with open(os.path.join(SRC, "networks", "tau-testnet-v2", "genesis.json"), "w") as f:
        json.dump({"network_id": "tau-testnet-v2", "block_0": {"hash": f"{ts:064x}"}, "accounts_state": accounts,
                   "consensus_meta": meta, "application_rules": rules}, f)
    run("add", "-A")
    run("commit", "-q", "-m", msg, ts=ts)


os.makedirs(SRC)
run("init", "-q", "-b", "main")
genesis(at("2026-11-01T08:00:00Z"), {"a": 1000000, "b": 100000}, {"approval_slots_active": True, "faucet_amount": 0},
        "o0[t] = 1\n", "genesis for the restart of 1 November")
genesis(at("2026-11-12T12:00:00Z"), {"a": 1000000, "b": 100000, "c": 100000}, {"approval_slots_active": True, "faucet_amount": 100000},
        "o0[t] = 1\nu[t] = i0[t]\n", "feat(genesis): faucet in genesis, regenerate")

gen = rb.genesis_lines(SRC, "main", at("2026-11-02T00:00:00Z"))
text = "\n".join(gen)
check("accounts at the start: 2 -> 3" in text and "consensus_meta.faucet_amount: 0 -> 100000" in text
      and "+u[t] = i0[t]" in text and "approval_slots_active" not in text and "block_0" not in text,
      "the starting state: accounts, changed settings and the rule text diff, unchanged settings and block 0 left out")
check(rb.genesis_lines(SRC, "main", at("2026-11-13T00:00:00Z")) == [], "no difference: nothing to say")

news = {"items": [
    {"ts": at("2026-10-30T10:00:00Z"), "headline": {"en": "Older change before the last chain"}, "tip": {"en": "x"}},
    {"ts": at("2026-11-11T19:38:00Z"), "headline": {"en": "Every account can hold its own payment rule"},
     "tip": {"en": "Each payment is judged by its sender's own rule; nothing limits how many accounts hold one."}},
    {"ts": at("2026-11-12T06:57:00Z"), "headline": {"en": "New accounts get 100,000 test coins at their first payment"},
     "tip": {"en": "The faucet is part of the starting state."}}]}
heads = rb.heads_of(news, at("2026-11-01T08:00:00Z"), at("2026-11-13T09:00:00Z"))
check([h["headline"]["en"][:5] for h in heads] == ["Every", "New a"], "only the headlines since the chain before, oldest first")
check(rb.newest([{"at": at("2026-11-01T08:00:00Z")}, {"at": at("2026-11-13T08:30:00Z")}]) == ({"at": at("2026-11-13T08:30:00Z")}, at("2026-11-01T08:00:00Z")),
      "the newest restart and when the chain before began")

asked = []
GOOD = {"post": True, "title": "The Tau Net testnet restarted with a personal rule for every account",
        "points": ["Every account can now hold its own payment rule; before, two accounts on the whole network could.",
                   "New accounts get 100,000 test coins at their first payment."],
        "why": "Anyone can now try a spending limit or a co-signer on the live test network, not only in a simulation.",
        "x_text": "IDNI restarted the Tau Net testnet with a personal payment rule for every account and test coins for new accounts.",
        "reason": "new capability"}


def fake(answer):
    def f(prompt):
        asked.append(prompt)
        return dict(answer)
    return f


now = at("2026-11-13T08:40:00Z")
d = rb.write(heads, gen, at("2026-11-13T08:30:00Z"), at("2026-11-01T08:00:00Z"), now, fake(GOOD))
check(len(asked) == 1 and "Every account can hold its own payment rule" in asked[0] and "faucet_amount: 0 -> 100000" in asked[0]
      and "Older change" not in asked[0], "the model reads the headlines since then and the starting state")
check(d["status"] == "ready" and d["title"].startswith("The Tau Net testnet restarted with") and len(d["points"]) == 2, "a clean answer: ready")
d2 = rb.write(heads, gen, at("2026-11-13T08:30:00Z"), None, now, fake(dict(GOOD, why="It is 40 times faster now.")))
check(d2["status"] == "check" and "40" in d2["check"]["unknown_numbers"], "a number the input does not hold: held back")
d3 = rb.write(heads, gen, at("2026-11-13T08:30:00Z"), None, now, fake(dict(GOOD, title="Big news for Tau")))
check(d3["status"] == "plain", "a title that does not say the testnet restarted: the short post")
check(rb.write([], [], at("2026-11-13T08:30:00Z"), None, now, fake(GOOD))["status"] == "plain" and len(asked) == 3,
      "nothing to read: no model call, the short post")

# step: once per restart, only shortly after it
rb.save({})
asked.clear()
s = rb.step([{"at": at("2026-11-01T08:00:00Z")}, {"at": at("2026-11-13T08:30:00Z")}], SRC, "main", news, now, fake(GOOD))
check(s["status"] == "ready" and len(asked) == 1 and rb.load()["at"] == at("2026-11-13T08:30:00Z"), "the newest restart gets its brief")
rb.step([{"at": at("2026-11-01T08:00:00Z")}, {"at": at("2026-11-13T08:30:00Z")}], SRC, "main", news, now + 1800, fake(GOOD))
check(len(asked) == 1, "and only once")
rb.save({})
rb.step([{"at": at("2026-11-01T08:00:00Z")}], SRC, "main", news, now, fake(GOOD))
check(len(asked) == 1 and rb.load() == {}, "a restart days ago (or the first start): no brief")

# the alerts service: the restart post waits for the brief, then says what the new chain brings
w = alerts.Watcher([])
it = {"key": "restart:a:b", "kind": "restart", "h": 0, "seen": at("2026-11-13T08:31:00Z"), "posted": {}, "news": True,
      **alerts.describe({"kind": "restart", "old_tip": 8898}, None, 0, None)}
check(not w.restart_ready(it, at("2026-11-13T08:35:00Z"), {}), "no brief yet: the restart post waits")
check(w.restart_ready(it, at("2026-11-13T08:41:00Z"), dict(d, at=at("2026-11-13T08:30:00Z"))) and it["brief"] == "ready"
      and it["headline"].startswith("The Tau Net testnet restarted with"), "the brief arrives: the post carries it")
tg = alerts.telegram_text(it)
check("<b>New on the new chain</b>" in tg and "• Every account can now hold its own payment rule" in tg and "<b>Why it matters</b>" in tg
      and "The old chain ended at block #8,898." in tg and alerts.RESTART_FOR_YOU in tg, "Telegram: what is new, why, then the old chain and your wallet")
x = alerts.x_text(it)
check(x.startswith("🔄 The Tau Net testnet restarted with") and "IDNI restarted the Tau Net testnet" in x and alerts.x_len(x) <= 280, "X: the title and the brief's X line")
it2 = {"key": "restart:c:d", "kind": "restart", "h": 0, "seen": at("2026-11-13T08:31:00Z"), "posted": {}, "news": True,
       **alerts.describe({"kind": "restart", "old_tip": 10}, None, 0, None)}
check(w.restart_ready(it2, at("2026-11-13T08:31:00Z") + rb.WAIT + 1, {}) and it2["brief"] == "none"
      and it2["headline"] == alerts.RESTART_HEADLINE, "no brief after the wait: the short post goes out")
it3 = dict(it2, brief=None, posted={"telegram": "ok"})
check(w.restart_ready(it3, at("2026-11-13T08:32:00Z"), {}), "already posted on one outlet: the others never wait")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

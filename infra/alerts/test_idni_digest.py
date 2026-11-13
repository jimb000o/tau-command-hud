"""Unit test of IDNI's progress of the day as one post (no network): a small local git repository stands in for
IDNI's; a window with only tests stays quiet, a window with real changes becomes ONE post with the combined meaning,
numbers the commits do not hold or blame wording hold it back, a hold keeps the commits for the next window, and the
alerts service posts it once on Telegram (with links) and on X (no link, under 280) only on a notable day.

Run: python test_idni_digest.py   (needs git and websockets==15.0.1)
"""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

TMP = tempfile.mkdtemp()
SRC = os.path.join(TMP, "src")
os.environ.update(DEVPULSE_CLONES=os.path.join(TMP, "clones"), PUBLIC_DIR=TMP, DEVPULSE_REPOS="IDNI/tau-testnet",
                  DEVPULSE_PINS_FILE=os.path.join(TMP, "Dockerfile"), RELAY_HTTP="", STATE_PATH=os.path.join(TMP, "alerts.json"),
                  TELEGRAM_BOT_TOKEN="", X_API_KEY="", NEWS_AI_KEY="test")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import devpulse as dp  # noqa: E402
import idni_digest as idg  # noqa: E402
import alerts  # noqa: E402

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


def commit(path, msg, ts):
    full = os.path.join(SRC, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "a") as f:
        f.write(msg + "\n")
    run("add", "-A")
    run("commit", "-q", "-m", msg, ts=ts)
    return run("rev-parse", "HEAD")


os.makedirs(SRC)
run("init", "-q", "-b", "main")
pin = commit("consensus/engine.py", "start", at("2026-11-03T12:00:00Z"))
t1 = commit("tests/test_a.py", "test: a steadier test", at("2026-11-04T09:00:00Z"))        # housekeeping
f1 = commit("commands/createblock.py", "fix(createblock): let the fallback miner proposal respawn its evaluator",
            at("2026-11-05T13:45:00Z"))
f2 = commit("tau_advisory.py", "fix(advisory): feed input values bare (#71)", at("2026-11-05T14:00:00Z"))
c1 = commit("ci/x.yml", "ci: give the test environment its miner identity", at("2026-11-05T14:05:00Z"))
path = os.path.join(TMP, "clones", "x.git")
subprocess.run(["git", "clone", "-q", "--bare", SRC, path], check=True)
paths, branches = {dp.TESTNET: path}, {dp.TESTNET: "main"}

# the news writer has judged the commits: two are news, the CI one was passed over
dp.HEADLINES = os.path.join(TMP, "headlines.json")
with open(dp.HEADLINES, "w") as f:
    json.dump({"version": dp.NEWS_VERSION, "failed_at": 0,
               "seen": {s: 1 for s in (f1, f2, t1, c1)},
               "items": [{"id": f1, "shas": [f1], "ts": at("2026-11-05T13:45:00Z"), "kind": "fix",
                          "headline": {"en": "Block makers can make rule-changing blocks again", "zh": "z", "ja": "j"},
                          "tip": {"en": "A fallback proposal now restarts its checker.", "zh": "z", "ja": "j"}},
                         {"id": f2, "shas": [f2], "ts": at("2026-11-05T14:00:00Z"), "kind": "fix",
                          "headline": {"en": "Multi-validator checks read inputs the same way", "zh": "z", "ja": "j"},
                          "tip": {"en": "Advisory checks now get values as the main checker does.", "zh": "z", "ja": "j"}}]}, f)

check(idg.slot_at(at("2026-11-07T10:05:00Z")) == at("2026-11-07T10:00:00Z")
      and idg.slot_at(at("2026-11-07T09:59:00Z")) == at("2026-11-06T10:00:00Z"), "the slot is the day's 10:00 UTC, or yesterday's")
check(idg.day_label([at("2026-11-04T09:00:00Z"), at("2026-11-05T14:00:00Z")]) == "4–5 Nov"
      and idg.day_label([at("2026-11-05T09:00:00Z")]) == "5 Nov", "the days a post covers")

g = idg.gather(paths, branches, at("2026-11-04T00:00:00Z"), at("2026-11-07T10:00:00Z"), pin, dp.load_headlines())
check([c["sha"] for c in g["changes"]] == [f1, f2] and {c["sha"] for c in g["house"]} == {t1, c1} and not g["pending"],
      "gather: the news writer's changes, oldest first; tests and CI as housekeeping")
check(g["changes"][0]["headline"].startswith("Block makers") and g["changes"][0]["runs"] is False, "with their headline; our node does not run them")

asked = []
GOOD = {"post": True, "x": True, "title": "Block makers can again make blocks that change the rules",
        "points": ["A fallback block proposal now restarts its rule checker, so blocks that turn on governance can be made.",
                   "Advisory checks with several validators read input values the same way as the main check (#71).",
                   "More of the test suite runs the same way every time."],
        "why": "Blocks that change the testnet's rules can be made by the fallback path too, so rule changes do not wait on one route.",
        "x_text": "IDNI merged a fix so the fallback block maker can make blocks that change the rules, plus a multi-validator fix.",
        "reason": "block-making fix"}


def fake(answer):
    def f(prompt):
        asked.append(prompt)
        return dict(answer)
    return f


# a window with only housekeeping: no model call, quiet
d = idg.write(idg.gather(paths, branches, at("2026-11-04T00:00:00Z"), at("2026-11-05T00:00:00Z"), pin, dp.load_headlines()),
              paths, at("2026-11-04T00:00:00Z"), at("2026-11-05T00:00:00Z"), None, at("2026-11-05T00:00:00Z"), fake(GOOD))
check(d["status"] == "quiet" and not asked, "a day with only tests and CI: quiet, no model call, no post")

d = idg.write(g, paths, at("2026-11-04T00:00:00Z"), at("2026-11-07T10:00:00Z"), at("2026-11-03T12:00:00Z"), at("2026-11-07T10:01:00Z"), fake(GOOD))
check(len(asked) == 1 and "respawn its evaluator" in asked[0] and "Diff" in asked[0] and "Our news line shows: Block makers" in asked[0]
      and "- ci: give the test environment" in asked[0], "the writer reads every change with its diff and headline, housekeeping by title")
check(d["status"] == "ready" and d["shas"] == [f1, f2] and d["days"] == "5 Nov" and d["runs"] == "none", "two merges, ONE post, ready")
tg = idg.tg_text(d)
check(tg.startswith("🛠 <b>IDNI testnet progress · 5 Nov</b>") and "<b>Why it matters:</b> " in tg and "not affiliated with IDNI" in tg
      and all(f"\n\n• {p}" in tg for p in d["points"])
      and "Our node does not run it yet; its code is from 3 Nov." in tg and "github.com/IDNI/tau-testnet/commits/main" in tg,
      "Telegram: the day, the points, why it matters, what our node runs, the links, not affiliated")
x = alerts.x_post(idg.x_lines(d), foot=idg.X_FOOT, keep=2)
check(alerts.x_len(x) <= 280 and "http" not in x and x.startswith("🛠 IDNI testnet: Block makers") and x.endswith("#TauNet"),
      "X: no link, under 280, the headline first, the tags last")

bad = dict(GOOD, why="IDNI finally fixed what was broken for 12 days!")
d2 = idg.write(g, paths, at("2026-11-04T00:00:00Z"), at("2026-11-07T10:00:00Z"), None, at("2026-11-07T10:01:00Z"), fake(bad))
check(d2["status"] == "check" and "12" in d2["check"]["unknown_numbers"] and d2["check"]["wording"],
      "a number the commits do not hold, or hype and blame: held for a look")
d3 = idg.write(g, paths, at("2026-11-04T00:00:00Z"), at("2026-11-07T10:00:00Z"), None, at("2026-11-07T10:01:00Z"), fake(dict(GOOD, post=False)))
check(d3["status"] == "skip", "the writer sees nothing worth a post: skip")

# the service's pass: the first window reaches back three days from midnight, closes at the slot once
idg.ask = fake(GOOD)
asked.clear()
s = idg.step(paths, branches, pin, at("2026-11-07T09:00:00Z"))
check(s["state"] == "waiting for the slot" and not asked, "before the slot: nothing written")
s = idg.step(paths, branches, pin, at("2026-11-07T10:20:00Z"))
st = idg.load()
check(len(asked) == 1 and s["state"] == "ready" and st["last_end"] == at("2026-11-07T10:00:00Z")
      and st["items"][-1]["start"] == at("2026-11-04T00:00:00Z"), "at the slot: the first window from 4 Nov 00:00 to 7 Nov 10:00, ready")
idg.step(paths, branches, pin, at("2026-11-07T10:50:00Z"))
check(len(asked) == 1, "a window is written once")

# hold: the 8 Nov window is not closed, its commits wait for 9 Nov
f3 = commit("network/peers.py", "fix(network): re-dial bootstrap peers", at("2026-11-07T20:00:00Z"))
subprocess.run(["git", "-C", path, "fetch", "-q", SRC, "+refs/heads/*:refs/heads/*"], check=True)
dp.write_atomic(idg.files()[1], json.dumps({"until": at("2026-11-08T10:00:01Z")}))
s = idg.step(paths, branches, pin, at("2026-11-08T10:20:00Z"))
check(s["state"].startswith("held") and len(asked) == 1, "held: nothing written")
dp.write_atomic(idg.files()[1], json.dumps({}))
s = idg.step(paths, branches, pin, at("2026-11-09T10:20:00Z"))
check(s["state"] == "waiting for the news writer", "a change the news writer has not judged yet: wait for it")
idg.ask = fake(dict(GOOD, points=["Nodes dial their bootstrap peers again after losing them."]))   # no "#71" in this window
s = idg.step(paths, branches, pin, at("2026-11-09T12:30:00Z"))
check(s["state"] == "ready" and idg.load()["items"][-1]["start"] == at("2026-11-07T10:00:00Z")
      and idg.load()["items"][-1]["shas"] == [f3], "after two hours it is read anyway; the held day's commit came along")

# the text `up idni` showed is the text that goes out, unless something new came in
f4 = commit("network/sync.py", "fix(sync): keep syncing after a gap", at("2026-11-09T20:00:00Z"))
subprocess.run(["git", "-C", path, "fetch", "-q", SRC, "+refs/heads/*:refs/heads/*"], check=True)
st = idg.load()
st["draft"] = dict(d, title="Previewed title", start=st["last_end"], shas=[f4])
idg.save(st)
asked.clear()
s = idg.step(paths, branches, pin, at("2026-11-10T12:30:00Z"))
last = idg.load()["items"][-1]
check(not asked and last["title"] == "Previewed title" and last["end"] == at("2026-11-10T10:00:00Z") and "draft" not in idg.load(),
      "the previewed text goes out as it was shown, no new model call")

# a change written before the last post but pushed after it (its own window had closed) joins the next post;
# housekeeping from back then and changes earlier posts already read stay out
f5 = commit("consensus/rules.py", "feat(rules): judge each payment by its sender's own rule", at("2026-11-09T22:00:00Z"))
t5 = commit("tests/test_rules.py", "test: per-account rules", at("2026-11-09T23:00:00Z"))
subprocess.run(["git", "-C", path, "fetch", "-q", SRC, "+refs/heads/*:refs/heads/*"], check=True)
with open(dp.HEADLINES) as fh:
    hl = json.load(fh)
hl["seen"].update({f3: 1, f4: 1, f5: 1, t5: 1})
hl["items"].append({"id": f5, "shas": [f5], "ts": at("2026-11-09T22:00:00Z"), "kind": "feature",
                    "headline": {"en": "Every account can hold its own rule", "zh": "z", "ja": "j"},
                    "tip": {"en": "Each payment is judged by its sender's rule.", "zh": "z", "ja": "j"}})
dp.write_atomic(dp.HEADLINES, json.dumps(hl))
check(idg.late_from(idg.load(), at("2026-11-10T10:00:00Z")) == at("2026-11-04T00:00:00Z")
      and idg.late_from({"items": []}, at("2026-11-10T10:00:00Z")) == at("2026-11-10T10:00:00Z"),
      "late commits are looked for back to the first post at most, and not at all before it")
asked.clear()
s = idg.step(paths, branches, pin, at("2026-11-11T10:20:00Z"))
last = idg.load()["items"][-1]
check(s["state"] == "ready" and last["shas"] == [f5] and last["start"] == at("2026-11-10T10:00:00Z") and len(asked) == 1
      and "reached main after our last post" in asked[0] and "judge each payment" in asked[0]
      and "fix(sync)" not in asked[0] and "steadier test" not in asked[0] and "test: per-account" not in asked[0],
      "pushed late: the change joins the next post; read changes and housekeeping from back then stay out")
asked.clear()
s = idg.step(paths, branches, pin, at("2026-11-12T10:20:00Z"))
check(s["state"] == "quiet" and not asked, "and it is read once")

# ---------- the alerts service posts it ----------


class Fake(alerts.Outlet):
    def __init__(self, name):
        self.name, self.sent = name, []

    def enabled(self):
        return True

    def send_text(self, text, *rest):
        self.sent.append(text)
        return True, None, ""


tgo, xo = Fake("telegram"), Fake("x")
w = alerts.Watcher([tgo, xo])
w.state.pop("idni", None)
w.state.pop("x", None)
items = [dict(d, id="a", end=at("2026-11-07T10:00:00Z")), dict(d, id="b", end=at("2026-11-08T10:00:00Z"), x=False)]
asyncio.run(w.maybe_idni(at("2026-11-07T09:59:00Z"), items, {}))
check(not tgo.sent and not xo.sent, "nothing before its window has closed")
asyncio.run(w.maybe_idni(at("2026-11-07T10:30:00Z"), items, {}))
check(len(tgo.sent) == 1 and "IDNI testnet progress" in tgo.sent[0] and len(xo.sent) == 1 and "http" not in xo.sent[0],
      "posted: Telegram, then X without a link")
asyncio.run(w.maybe_idni(at("2026-11-07T11:00:00Z"), items + [dict(d, id="c", end=at("2026-11-07T10:40:00Z"), manual=True)], {}))
check(len(tgo.sent) == 1 and len(xo.sent) == 1, "never twice, and at most one IDNI post a UTC day")
asyncio.run(w.maybe_idni(at("2026-11-08T10:10:00Z"), items, {}))
check(len(tgo.sent) == 2 and len(xo.sent) == 1, "a small day: Telegram only")
asyncio.run(w.maybe_idni(at("2026-11-09T16:00:00Z"), items + [dict(d, id="late", end=at("2026-11-09T10:00:00Z"))], {}))
check(len(tgo.sent) == 2, "a post missed by more than three hours is not sent late")
asyncio.run(w.maybe_idni(at("2026-11-10T10:10:00Z"), [dict(d, id="h", end=at("2026-11-10T10:00:00Z"))], {"until": at("2026-11-10T10:00:01Z")}))
check(len(tgo.sent) == 2, "held: not posted")
asyncio.run(w.maybe_idni(at("2026-11-11T10:10:00Z"), [dict(d, id="chk", end=at("2026-11-11T10:00:00Z"), status="check")], {}))
check(len(tgo.sent) == 2, "a post held for a look is never sent by itself")

chk = idg.check_text(["New accounts get 100,000 test coins and 64 KiB.", "1,500 blocks"], "faucet_amount: 0 -> 100000, 64 KiB")
check(chk["unknown_numbers"] == ["1,500"], "100,000 in the post is 100000 in the code; a number the input lacks still holds the post")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

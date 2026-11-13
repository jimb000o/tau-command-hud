"""Unit test of "reported by us, solved by IDNI" (no network): our reports come from the Findings page's own list; a
change on IDNI's main is read once against the reports still open, and a verdict counts only with a quote that is
really in the change; GitHub closing our issue counts too; the owner hears of each one (not at night) and can take it
back; everything solved goes into ONE post after a quiet spell, first as a draft, and the alerts service posts it only
once it is approved.

Run: python test_fixwatch.py   (needs git and websockets==15.0.1)
"""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime

TMP = tempfile.mkdtemp()
SRC = os.path.join(TMP, "src")
os.environ.update(PUBLIC_DIR=TMP, STATE_PATH=os.path.join(TMP, "alerts.json"), FIXWATCH_PATH=os.path.join(TMP, "fixes.json"),
                  FINDINGS_PAGE=os.path.join(TMP, "findings.html"), TELEGRAM_BOT_TOKEN="", X_API_KEY="", NEWS_AI_KEY="test",
                  DEVPULSE_CLONES=os.path.join(TMP, "clones"), RESTART_BRIEF_PATH=os.path.join(TMP, "restart.json"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402
import fixwatch as fw  # noqa: E402

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


def commit(path, text, msg, ts):
    full = os.path.join(SRC, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(text)
    run("add", "-A")
    run("commit", "-q", "-m", msg, ts=ts)
    return run("rev-parse", "HEAD")


PAGE = '''<script>
const FINDINGS = [
  {
    n: 111, title: "[bug] long co-signer clause crashes the engine worker",
    brief: "A long co-signer rule crashed the Tau engine's worker.",
    found: "With two accounts each holding a co-signer rule of ten conditions, the worker crashed while the block was built.",
    impact: "One long personal rule could hold up its author's payments.",
  },
  {
    n: 108, title: "New addresses refused once a node has interned 254 addresses",
    brief: "After 254 different addresses our node refused every payment to or from a new wallet.",
    found: "At 254 addresses the 8-bit numbers ran out, and from then on the node refused every payment with a new wallet.",
    impact: "A busy node would stop taking new users.",
  },
  {
    n: 86, kind: "fix", title: "fix(network): re-dial bootstrap peers",
    brief: "Our first code fix sent to IDNI: a node that lost every peer finds its way back.",
    found: "Nodes dial their bootstrap peers only once.", impact: "A node sits still.",
  },
  {
    n: 85, kind: "request", title: "could one of the two o5 policy slots be freed?",
    brief: "Not a bug: only two accounts on the whole testnet could hold a personal rule.",
    idni: "done", idniBrief: "since 12 November every account can hold its own rule.", fixedOn: "2026-11-12",
    found: "Not a bug: the testnet allows two personal rules at a time.", impact: "Nobody else can try a rule.",
  },
  {
    n: 81, title: "Mempool keeps transactions that are already sealed",
    brief: "Sealed transactions stayed in the mempool.", found: "The mempool kept sealed transactions.", impact: "Ghost transactions.",
  },
];
</script>'''
with open(os.environ["FINDINGS_PAGE"], "w") as f:
    f.write(PAGE)
reps = fw.read_reports()
check([r["n"] for r in reps] == [111, 108, 86, 85, 81] and reps[3]["idni"] == "done" and reps[3]["fixedOn"] == "2026-11-12"
      and reps[2]["kind"] == "fix" and fw.numbers() == {111, 108, 86, 85, 81}, "the reports come from the Findings page itself")
check([r["n"] for r in fw.still_open(reps, {}, {"81": {"state": "closed"}}, {})] == [111, 108],
      "still open: not our pull requests, not solved by hand, not closed on GitHub")

os.makedirs(SRC)
run("init", "-q", "-b", "main")
commit("network/intern.py", "CAP = 254\nif len(ids) >= CAP:\n    raise Unavailable\n", "start", at("2026-11-10T10:00:00Z"))
fix = commit("network/intern.py", "# the table grows: bv[16] once 254 is reached\nCAP = 65534\n",
             "fix(admission): widen the address table when 254 addresses are in use", at("2026-11-13T09:00:00Z"))
other = commit("ui/colours.py", "GREEN = 1\n", "feat(ui): new colours", at("2026-11-13T09:30:00Z"))
news = [{"id": fix, "shas": [fix], "ts": at("2026-11-13T09:00:00Z"), "headline": {"en": "Nodes take new wallets past 254 addresses"}},
        {"id": other, "shas": [other], "ts": at("2026-11-13T09:30:00Z"), "headline": {"en": "New colours"}},
        {"id": "old", "shas": ["old"], "ts": at("2026-11-01T09:00:00Z"), "headline": {"en": "Old"}}]

asked, told = [], []


def fake(answers):
    def f(prompt):
        asked.append(prompt)
        return answers.pop(0) if answers else {"verdicts": []}
    return f


def tell(text):
    told.append(text)
    return True, ""


GOOD = {"n": 108, "level": "done", "evidence": "the table grows: bv[16] once 254 is reached",
        "line": "IDNI's change lets a node take new wallets after 254 addresses.", "zh": "z", "ja": "j"}
answers = [{"verdicts": [GOOD,
                         {"n": 111, "level": "partly", "evidence": "the engine no longer crashes on long rules", "line": "Invented.", "zh": "", "ja": ""},
                         {"n": 85, "level": "done", "evidence": "the table grows: bv[16] once 254 is reached", "line": "Not open any more.", "zh": "", "ja": ""}]},
           {"verdicts": []}]
now = at("2026-11-13T10:00:00Z")   # 11:00 in Germany
fx = fw.step(news, {"108": {"state": "open"}, "111": {"state": "open"}, "81": {"state": "open"}, "86": {"state": "open"}},
             SRC, now, fake(answers), tell)
st = fw.load()
check(len(asked) == 2 and "Report #108" in asked[0] and "Report #85" not in asked[0] and "Report #86" not in asked[0]
      and "the table grows" in asked[0], "each new change read once, against the reports still open, with its diff")
check(st["judged"].get("old") and len(st["judged"]) == 3, "the first pass reads the last three days only")
check(list(fx) == ["108"] and fx["108"]["level"] == "done" and fx["108"]["sha"] == fix and fx["108"]["line"]["en"].startswith("IDNI's change"),
      "a verdict with its quote in the change counts; an invented quote and a report already solved do not")
check(len(told) == 1 and "#108 solved by IDNI" in told[0] and "up idni fixed no 108" in told[0] and "the table grows" in told[0],
      "the owner hears of it privately, with the quote and how to take it back")
check("85" not in fx and st["fixed"]["85"]["by"] == "page", "#85, marked done by hand on 12 November: not on the pages again, but in the next post")

# the post: after a quiet spell, one draft for both, never at night
fw.step(news, None, SRC, now + 600, fake([]), tell)
check(not fw.load().get("post"), "no post while the newest one is fresh")
post_answer = {"title": "Two reports solved by IDNI", "items": ["Every account can hold its own payment rule.",
                                                                   "A node takes new wallets after 254 addresses."],
               "x_text": "Two things we reported to IDNI are solved: personal rules for every account, and new wallets past 254 addresses."}
fw.step(news, None, SRC, at("2026-11-13T21:30:00Z"), lambda p: dict(post_answer), tell)   # 22:30 in Germany
check(not fw.load().get("post"), "not at night")
told.clear()
fw.step(news, None, SRC, at("2026-11-14T08:00:00Z"), lambda p: dict(post_answer), tell)   # 09:00 in Germany
p = fw.load()["post"]
check(p["status"] == "draft" and p["ns"] == [85, 108] and p["by"] == "model" and len(told) == 1 and "up idni fixed send" in told[0]
      and "Two reports solved by IDNI" in told[0], "one post for both, as a draft to the owner first")
tg = fw.tg_text(p)
check(tg.startswith("🎉 <b>Two reports solved by IDNI</b>") and "• <b>#85</b> Every account" in tg and "not affiliated with IDNI" in tg
      and "tauhud.com/findings/" in tg, "Telegram: what is solved now, thanks, the Findings page, not affiliated")
x = alerts.x_post(fw.x_lines(p), foot=fw.X_FOOT, keep=2)
check("http" not in x and alerts.x_len(x) <= 280 and x.startswith("🎉 Two reports"), "X: no link, under 280")
bad = fw.write_post([85, 108], fw.load()["fixed"], {r["n"]: r for r in reps},
                    lambda pr: dict(post_answer, x_text="IDNI finally fixed 3 things!"))
check(bad["by"] == "plain" and bad["title"] == "Reported by us, solved by IDNI" and bad["items"][0].startswith("Since 12 November"),
      "hype or a number the input does not hold: the plain text from the reports instead")

# the alerts service posts only an approved one
tgo_sent, x_sent = [], []


class Fake(alerts.Outlet):
    def __init__(self, name, box):
        self.name, self.box = name, box

    def enabled(self):
        return True

    def send_text(self, text, *rest):
        self.box.append(text)
        return True, None, ""


w = alerts.Watcher([Fake("telegram", tgo_sent), Fake("x", x_sent)])
asyncio.run(w.maybe_fixed(at("2026-11-14T08:05:00Z"), p))
check(not tgo_sent and not x_sent, "a draft is never posted")
check(fw.cli(["send"]) == 0 and fw.load()["post"]["status"] == "approved", "up idni fixed send approves it")
asyncio.run(w.maybe_fixed(at("2026-11-14T08:06:00Z"), fw.load()["post"]))
check(len(tgo_sent) == 1 and "#108" in tgo_sent[0] and len(x_sent) == 1 and "http" not in x_sent[0], "approved: Telegram, then X")
asyncio.run(w.maybe_fixed(at("2026-11-14T08:07:00Z"), fw.load()["post"]))
check(len(tgo_sent) == 1 and len(x_sent) == 1, "once")
fw.step(news, None, SRC, at("2026-11-14T08:10:00Z"), fake([]), tell)
check(fw.load()["post"]["status"] == "posted" and fw.load()["posted"] == [85, 108], "fixwatch learns it went out")

# GitHub closes our issue as completed: solved too; a not-planned close is not
told.clear()
fw.step(news, {"111": {"state": "open"}, "81": {"state": "open"}}, SRC, at("2026-11-14T09:00:00Z"), fake([]), tell)
fw.step(news, {"111": {"state": "closed"}, "81": {"state": "not_planned"}}, SRC, at("2026-11-14T10:00:00Z"), fake([]), tell)
fx = fw.public(fw.load())
check(fx["111"]["by"] == "closed" and "81" not in fx and any("#111 solved" in t for t in told), "closed as completed counts, not planned does not")

# taken back by the owner: off the pages and out of the waiting post, and that change is not read for it again
check(fw.cli(["no", "108"]) == 0 and "108" not in fw.public(fw.load()) and fw.load()["no"]["108"] == [fix], "up idni fixed no 108")
check(fw.cli(["auto"]) == 0 and fw.load()["mode"] == "auto", "up idni fixed auto")

# a change judged again after the owner's no: the same commit cannot bring it back
st = fw.load()
st["judged"].pop(fix)
fw.save(st)
fw.step([news[0]], {"108": {"state": "open"}}, SRC, at("2026-11-14T11:00:00Z"), fake([{"verdicts": [GOOD]}]), tell)
check("108" not in fw.public(fw.load()), "the commit the owner rejected does not mark it solved again")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

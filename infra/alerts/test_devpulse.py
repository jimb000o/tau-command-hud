"""Unit test of the build pulse (no network): a small local git repository
stands in for IDNI's; weeks, days, code areas, tags, the pinned commit and how
far main is ahead of it are counted right, and author addresses never reach the
published file.

Run: python test_devpulse.py   (needs git)
"""
import json
import os
import subprocess
import sys
import tempfile
import time

TMP = tempfile.mkdtemp()
SRC = os.path.join(TMP, "src")
os.environ.update(DEVPULSE_CLONES=os.path.join(TMP, "clones"), PUBLIC_DIR=TMP, DEVPULSE_REPOS="IDNI/tau-testnet",
                  DEVPULSE_PINS_FILE=os.path.join(TMP, "Dockerfile"), RELAY_HTTP="")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import devpulse as dp  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


NOW = int(time.time())
DAY = 86400


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
commit("README.md", "start", NOW - 200 * DAY)
pin = commit("consensus/engine.py", "consensus work", NOW - 40 * DAY)
run("tag", "v0.1", ts=NOW - 40 * DAY)
commit("tests/unit/test_a.py", "add a test", NOW - 10 * DAY)
commit("src/core/x.cpp", "core change", NOW - 1)   # now: in this week even in the first hour of a Monday
with open(os.environ["DEVPULSE_PINS_FILE"], "w") as f:
    f.write(f"ARG TAU_TESTNET_REF={pin}\nARG TAU_LANG_REF=c3ea334cd1e6612930ea9f404933211858f0009f\n")

# the clone comes from the local folder instead of GitHub
path = os.path.join(TMP, "clones", "x.git")
subprocess.run(["git", "clone", "-q", "--bare", SRC, path], check=True)
dp.sync = lambda repo: path

check(dp.area("README.md") == "root files", "a file at the top counts as root files")
check(dp.area("src/core/x.cpp") == "src/core", "src is counted one level deeper")
check(dp.area("consensus/engine.py") == "consensus", "other folders by their first name")
check(dp.pins()["IDNI/tau-testnet"] == pin, "the pinned commit is read from the node Dockerfile")

data = dp.build(NOW, {"IDNI/tau-testnet": {"issues_open": 3}})
r = data["repos"][0]
check(r["commits_52w"] == 4 and r["commits_4w"] == 2 and r["commits_12w"] == 3, "commits per 4, 12 and 52 weeks")
check(sum(r["weeks"]) == 4 and len(r["weeks"]) == 52 and r["weeks"][-1] >= 1, "52 weekly counts, this week last")
check(sum(r["days"]) == 3 and len(r["days"]) == 90, "90 daily counts")
check(r["runs"]["sha"] == pin and r["runs"]["ahead"] == 2, "main is 2 commits ahead of the pinned commit")
check([t["name"] for t in r["tags"]] == ["v0.1"], "tags listed")
check(r["recent"][0]["title"] == "core change" and r["recent"][0]["areas"] == ["src/core"], "newest commit first, with its area")
areas = {a["path"]: a for a in r["areas"]}
check(areas["consensus"]["c12"] == 1 and areas["consensus"]["c4"] == 0, "an area changed 40 days ago counts in 12 weeks, not in 4")
check(r["tracker"] == {"issues_open": 3}, "GitHub numbers are passed through")
text = json.dumps(data)
check("dev@example.org" not in text and '"author"' not in text, "no author address in the published file")
check(r["people_12w"] == 1, "people are counted, not named")

# ---------- news and sync ----------
check(dp.headline("merge: fix(#78) header sync into main") == {"kind": "fix", "text": "Header sync", "issues": [78]},
      "IDNI's merge title becomes a plain fix line with its issue")
check(dp.headline("merge: verify every transaction signature at apply")["text"] == "Verify every transaction signature at apply",
      "a merge without a type is a change")
check(dp.headline("Fix crash on start") == {"kind": "fix", "text": "Crash on start", "issues": []}, "a plain 'Fix …' title drops the word")
check(dp.headline("docs(retractable): guide") is None and dp.headline("merge: main into retractable transfers") is None
      and dp.headline("ci: cache") is None, "docs, CI and merging main into a branch never make news")

PATCHES = os.path.join(TMP, "patches")
os.makedirs(PATCHES)
with open(os.path.join(PATCHES, "good.py"), "w") as f:
    f.write("import pathlib, sys\nassert (pathlib.Path(sys.argv[1]) / 'consensus/engine.py').exists(), 'engine.py anchor not found'\n")
with open(os.path.join(PATCHES, "picky.py"), "w") as f:
    f.write("import pathlib, sys\nassert 'old line' in (pathlib.Path(sys.argv[1]) / 'consensus/engine.py').read_text(), 'old line anchor not found exactly once'\n")
with open(os.path.join(PATCHES, "late.py"), "w") as f:
    f.write("pass\n")
dp.PATCHES_DIR = PATCHES
dp.REMOTE = "file://" + SRC
commit("docs/guide.md", "merge: the operator guide", NOW - 1800)            # docs only: no news
commit("Dockerfile.standalone", "ARG TAU_LANG_REF=1111111111111111111111111111111111111111", NOW - 1700)
run("commit", "-q", "--amend", "-m", "merge: fix(#81) drop sealed txs from the waiting list", ts=NOW - 1700)
with open(os.environ["DEVPULSE_PINS_FILE"], "w") as f:
    f.write(f"ARG TAU_TESTNET_REF={pin}\nARG TAU_LANG_REF=c3ea334cd1e6612930ea9f404933211858f0009f\n"
            "RUN python3 -I /patches/good.py /src\nRUN python3 -I /patches/picky.py /src\nRUN python3 -I /patches/late.py /src\n")
subprocess.run(["git", "-C", path, "fetch", "-q", SRC, "+refs/heads/*:refs/heads/*"], check=True)
# the headline writer: no key, no news (a raw commit title is not news)
dp.HEADLINES = os.path.join(TMP, "headlines.json")
dp.NEWS_AI_KEY = ""
data = dp.build(NOW, {})
check(data["news"] == [] and data["news_ai"].startswith("no key"), "without an AI key no IDNI news is published")
cands = dp.candidates("IDNI/tau-testnet", path, "main", NOW, None)
check([c["sha"] for c in cands][:1] == [run("rev-parse", "HEAD")]
      and not any(c["text"] == "The operator guide" for c in cands) and not any(c["text"] == "Add a test" for c in cands),
      "candidates: newest first, docs- and test-only commits left out")
asked = []
fix_sha = run("rev-parse", "HEAD")[:7]
core_sha = run("rev-parse", "HEAD~2")[:7]


def fake_ai(prompt):
    asked.append(prompt)
    return {"items": [{"commits": [fix_sha], "kind": "fix",
                       "headline": {"en": "Sealed transactions leave the waiting list", "zh": "已封存的交易离开等候列表", "ja": "封印済みの取引が待ちリストから消える"},
                       "tip": {"en": "Nodes no longer list transactions that a block already sealed.", "zh": "节点不再列出已被区块封存的交易。", "ja": "ノードはブロックに封印済みの取引を表示しなくなります。"}},
                      {"commits": ["zzzzzzz"], "kind": "change", "headline": {"en": "Invented"}, "tip": {}}],
            "skip": [core_sha]}


dp.ask_ai = fake_ai
dp.NEWS_AI_KEY = "test"
data = dp.build(NOW, {})
news = data["news"]
check(len(asked) == 1 and "drop sealed txs" in asked[0] and "Diff" in asked[0], "the writer gets each new commit with its message and diff")
check(len(news) == 1 and news[0]["headline"]["en"] == "Sealed transactions leave the waiting list" and news[0]["kind"] == "fix"
      and news[0]["shas"] == [run("rev-parse", "HEAD")] and set(news[0]["tip"]) == {"en", "zh", "ja"},
      "news: the written headline in three languages; an item naming unknown commits is dropped")
check(news[0]["runs"] is False, "a commit after our pin: our node does not run it yet")
dp.build(NOW, {})
check(len(asked) == 1, "each commit goes to the writer once, kept in headlines.json")
dp.NEWS_VERSION += 1
dp.build(NOW, {})
check(len(asked) == 2, "new writing instructions: the kept headlines are written anew once")
y = data["sync"]
check(y["testnet"]["ahead"] == 4 and y["testnet"]["behind"][0]["text"] == "Drop sealed txs from the waiting list",
      "sync: main is 4 commits ahead, newest listed first")
check(y["tau_lang"] == {"ours": "c3ea334cd1e6612930ea9f404933211858f0009f", "idni": "1111111111111111111111111111111111111111", "same": False},
      "sync: IDNI's own tau-lang pin is read from Dockerfile.standalone on main")
res = {r["name"]: r for r in y["patches"]["results"]}
check(res["good.py"]["ok"] and res["picky.py"]["ok"] is False and "anchor not found" in res["picky.py"]["error"]
      and res["late.py"]["ok"] is None, "patches: a failing one is named with its reason, the ones after it are not tried")
check(y["ok"] is False and y["patches"]["sha"] == run("rev-parse", "HEAD"), "sync is not ok; the patch check ran on the newest main")
check(dp.check_patches("IDNI/tau-testnet", "main", y["patches"]["sha"]) is y["patches"], "the patch check runs once per upstream commit")

# ---------- refs: IDNI's own work on an issue moves the Road to mainnet badge ----------
rf = data["refs"]["items"]
check([m["sha"] for m in rf["81"]["main"]] == [run("rev-parse", "HEAD")] and rf["81"]["main"][0]["kind"] == "fix"
      and rf["81"]["main"][0]["runs"] is False, "refs: a fix on main that names #81 is listed, our node does not run it yet")
check(dp._mentions("docs(#85): explain the cap", "") is None and dp._mentions("test(#85): measure", "") is None,
      "refs: docs or tests naming an issue never count")
check(dp._mentions("Merge pull request #86 from x/redial", "fix(network): re-dial bootstrap peers") == ([86], "merged"),
      "refs: GitHub's merge title names the pull request itself")
run("checkout", "-q", "-b", "issue/85-90-more-places")
commit("consensus/approvals.py", "feat: three tier authors", NOW - 600)
run("checkout", "-q", "-b", "fix/mempool")
commit("consensus/mempool.py", "fix(#81): drop on apply, keep on reorg", NOW - 500)
run("checkout", "-q", "main")
run("checkout", "-q", "-b", "old-work")
run("checkout", "-q", "main")
subprocess.run(["git", "-C", path, "fetch", "-q", SRC, "+refs/heads/*:refs/heads/*"], check=True)
rf = dp.refs_state("IDNI/tau-testnet", path, "main", NOW, None)["items"]
check([w["branch"] for w in rf["85"]["work"]] == ["issue/85-90-more-places"] and "90" in rf,
      "refs: a branch named issue/85-90-… is work on #85 and #90")
check([w["branch"] for w in rf["81"]["work"]] == ["fix/mempool"] and rf["81"]["work"][0]["url"].endswith("/tree/fix/mempool"),
      "refs: a branch whose own commit names #81 is work on it")
check(not any(w["branch"] == "old-work" for v in rf.values() for w in v["work"]), "refs: a branch with nothing beyond main is not work")

sys.exit(1 if failed else 0)

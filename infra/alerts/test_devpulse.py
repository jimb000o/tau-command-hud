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
commit("src/core/x.cpp", "core change", NOW - 3600)   # today: in this week whatever the weekday
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
data = dp.build(NOW, {})
news = data["news"]
check([n["text"] for n in news] == ["Drop sealed txs from the waiting list", "Core change"] and
      news[0]["kind"] == "fix" and news[0]["issues"] == [81], "news: newest first, docs- and test-only commits left out")
check(not any(n["text"] == "The operator guide" for n in news), "a docs-only change never makes news")
check(all(n["runs"] is False for n in news), "commits after our pin: our node does not run them yet")
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

sys.exit(1 if failed else 0)

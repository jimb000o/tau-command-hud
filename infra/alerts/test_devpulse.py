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
commit("src/core/x.cpp", "core change", NOW - 2 * DAY)
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

sys.exit(1 if failed else 0)

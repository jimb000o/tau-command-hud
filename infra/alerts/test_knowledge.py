"""Unit test of Tau today (knowledge.py, no network) and of the hand-checked facts behind it (facts/facts.json):

  - every fact has its English, Chinese and Japanese text, a known topic and at least one source; every source of IDNI's
    repositories points at the very commit the list was checked against, and its file is in the list of watched files
  - a fact whose IDNI file changed on main since that commit is marked "check again", the others are not (a small local
    git repository stands in for IDNI's)
  - the Markdown carries the live numbers, IDNI's newest commits with links, only the progress posts that went out,
    every fact with its source, and says plainly when the node could not be read

Run: python test_knowledge.py   (needs git)
"""
import json
import re
import os
import subprocess
import sys
import tempfile

TMP = tempfile.mkdtemp()
HERE = os.path.dirname(os.path.abspath(__file__))
FACTS_PATH = os.path.join(HERE, "..", "..", "facts", "facts.json")
os.environ.update(PUBLIC_DIR=TMP, FACTS_FILE=FACTS_PATH, RELAY_HTTP="", DEVPULSE_CLONES=os.path.join(TMP, "clones"),
                  STATE_PATH=os.path.join(TMP, "alerts.json"))
sys.path.insert(0, HERE)
import knowledge as kn  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


# ---------- the facts file itself ----------
facts = json.load(open(FACTS_PATH, encoding="utf-8"))
topics = {t["id"] for t in facts["topics"]}
check(all(t.get(k) for t in facts["topics"] for k in ("en", "zh", "ja")), "every topic has en, zh and ja")
ids = [f["id"] for f in facts["facts"]]
check(len(ids) == len(set(ids)) and len(ids) >= 15, f"{len(ids)} facts, each id once")
bad = [f["id"] for f in facts["facts"] if not all((f.get(k) or "").strip() for k in ("en", "zh", "ja"))]
check(not bad, f"every fact has en, zh and ja {bad or ''}")
check(all(f.get("topic") in topics for f in facts["facts"]), "every fact has a known topic")
check(all(f.get("src") for f in facts["facts"]), "every fact has a source")
pinned, unwatched = [], []
for f in facts["facts"]:
    for _, url in f["src"]:
        for repo, ref in facts["checked_against"].items():
            if url.startswith(f"https://github.com/{repo}/"):
                if f"/{ref['sha']}/" not in url and not re.search(r"/(?:blob|tree)/[0-9a-f]{40}/", url):
                    pinned.append(f["id"])   # the checked commit, or a later full commit the fact was read at anew
                p = kn.src_file(url, repo)
                if p and p not in facts["files"].get(repo, []):
                    unwatched.append(f"{f['id']}: {p}")
check(not pinned, f"every IDNI source is pinned to a full commit {pinned or ''}")
check(not unwatched, f"every source file is watched for changes {unwatched or ''}")
check(all(not any(w in f["en"].lower() for w in ("soon", "will launch", "moon", "price")) for f in facts["facts"]),
      "no promises or prices in the facts")

# ---------- a stand-in for IDNI's repository ----------
src = os.path.join(TMP, "src")
os.makedirs(src)


def git(*a, cwd=src):
    env = dict(os.environ, GIT_AUTHOR_NAME="Dev", GIT_AUTHOR_EMAIL="dev@example.org", GIT_COMMITTER_NAME="Dev",
               GIT_COMMITTER_EMAIL="dev@example.org")
    return subprocess.run(["git", *a], cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout.strip()


git("init", "-q", "-b", "main")
for f in ("README.md", "docs/retractable.md", "docs/approvals.md"):
    os.makedirs(os.path.join(src, os.path.dirname(f)), exist_ok=True)
    open(os.path.join(src, f), "w").write("v1\n")
git("add", "-A")
git("commit", "-q", "-m", "start")
base = git("rev-parse", "HEAD")
open(os.path.join(src, "docs/approvals.md"), "w").write("v2\n")
git("commit", "-qam", "docs(approvals): new limits")
bare = os.path.join(TMP, "clone.git")
git("clone", "-q", "--bare", src, bare, cwd=TMP)

local = json.loads(json.dumps(facts))
local["checked_against"] = {"IDNI/tau-testnet": {"sha": base, "date": "2026-11-05"}}
local["files"] = {"IDNI/tau-testnet": ["README.md", "docs/retractable.md", "docs/approvals.md"]}
for f in local["facts"]:
    f["src"] = [[lab, url.replace(facts["checked_against"]["IDNI/tau-testnet"]["sha"], base)] for lab, url in f["src"]]
st = kn.facts_state(local, {"IDNI/tau-testnet": bare}, {"IDNI/tau-testnet": "main"})
check(st["changed"]["IDNI/tau-testnet"] == {"docs/approvals.md": 1}, f"the changed IDNI file is found: {st['changed']}")
check(set(st["stale"]) == {"approvals"}, f"only the fact read from that file is marked, not one read at its own later commit: {sorted(st['stale'])}")
later = json.loads(json.dumps(local))
for f in later["facts"]:
    if f["id"] == "o5-slots":
        f["src"] = [[lab, url.split("/blob/")[0] + "/blob/" + base + "/" + url.split("/blob/")[1].split("/", 1)[1]] for lab, url in f["src"]]
st2 = kn.facts_state(later, {"IDNI/tau-testnet": bare}, {"IDNI/tau-testnet": "main"})
check(set(st2["stale"]) == {"approvals", "o5-slots"}, f"a fact at its own commit is marked when the file changed after it: {sorted(st2['stale'])}")

# ---------- the file ----------
NOW = 1793980800   # 2026-11-07 00:00 UTC
pulse = {"repos": [{"repo": "IDNI/tau-testnet", "url": "https://github.com/IDNI/tau-testnet", "branch": "main",
                    "head": {"sha": "a" * 40, "ts": NOW - 3600, "title": "fix(createblock): respawn the evaluator"},
                    "runs": {"sha": "b" * 40, "ts": NOW - 86400 * 2, "ahead": 2}, "commits_4w": 41, "people_12w": 5,
                    "recent": [{"sha": "a" * 40, "ts": NOW - 3600, "title": "fix(createblock): respawn the evaluator"},
                               {"sha": "c" * 40, "ts": NOW - 86400 * 30, "title": "too old to list"}]}]}
live = {"api": "tauhud/v1", "network": "tau-testnet-v2", "generated_at": NOW, "status": "synced", "height": 1693,
        "last_block_age_seconds": 9, "pace_seconds": 8.1, "validators": 3, "base_fee": 10,
        "proposals": {"waiting": 0, "agreed": 0, "in_force": 1, "dropped": 2}, "community_nodes": 4,
        "health": {"score": 82, "label": "Healthy"}, "viewers": 12}
posts = [{"days": "5 Nov", "end": NOW - 80000, "title": "Fallback miner can respawn its evaluator", "points": ["x"],
          "why": "Blocks that activate governance no longer fail.", "commits": ["https://github.com/IDNI/tau-testnet/commit/" + "a" * 40]}]
d = kn.build(pulse, {"IDNI/tau-testnet": bare}, NOW, live, posts, local)
m = kn.md(d)
check("Block height: 1693" in m and "Active validators: 3" in m, "the live numbers are in the Markdown")
check("viewers" not in json.dumps(d["live"]), "visitor numbers are left out")
check("[aaaaaaa](https://github.com/IDNI/tau-testnet/commit/" + "a" * 40 + ")" in m and "2 commits behind" in m,
      "IDNI's newest commit with its link, and how far our node is behind")
check("too old to list" not in m, "commits older than 14 days are left out")
check("Fallback miner can respawn its evaluator" in m and "Commits: [aaaaaaa]" in m, "the posted progress with its commits")
check(m.count("Source: [") == len(local["facts"]), "every fact with its source")
check("**Check again:** IDNI changed tau-testnet/docs/approvals.md" in m, "the changed fact says so")
check("not affiliated with IDNI" in m, "says it is not affiliated with IDNI")
d2 = kn.build(pulse, {}, NOW, None, [], local)
m2 = kn.md(d2)
check("could not be read" in m2 and "Block height" not in m2, "no live numbers: says so, invents none")

# only posts that went out, written from IDNI's commits and checked
os.makedirs(os.path.join(TMP, "clones"), exist_ok=True)
json.dump({"version": 1, "items": [
    {"id": "idni-1", "status": "ready", "title": "Went out", "why": "w", "end": NOW - 100, "shas": ["d" * 40]},
    {"id": "idni-2", "status": "check", "title": "Held for a look", "why": "w", "end": NOW - 50, "shas": []},
    {"id": "idni-3", "status": "ready", "title": "Not posted yet", "why": "w", "end": NOW - 10, "shas": []}]},
    open(os.path.join(TMP, "clones", "digests.json"), "w"))
json.dump({"idni": {"posted": {"idni-1": NOW - 90}}}, open(os.environ["STATE_PATH"], "w"))
got = [p["title"] for p in kn.digests()]
check(got == ["Went out"], f"only the posted, checked progress posts: {got}")

# writing: both files land in the public folder
kn.RELAY_HTTP = ""
out = kn.write(pulse, {"IDNI/tau-testnet": bare}, NOW)
check(os.path.exists(os.path.join(TMP, "tau-today.md")) and json.load(open(os.path.join(TMP, "tau-today.json")))["v"] == 1,
      "tau-today.md and tau-today.json written")
check(kn.status_line(out).startswith(f"knowledge: {len(facts['facts'])} facts"), "the up line: " + kn.status_line(out))

print("all passed" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

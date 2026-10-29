"""Development pulse of the Tau software, for tauhud.com/devpulse/.

Keeps a bare, blob-less clone of each public IDNI repository below (git only,
no GitHub API needed for the history) and writes /public/devpulse.json, served
by Caddy at https://node.tauhud.com/devpulse.json:

  - the newest commits with the code areas they touched
  - commits per week for a year, per day for 90 days
  - which code areas moved in the last 4 and 12 weeks
  - tags, and how far each repo's main is ahead of the commit our node runs
  - chain restarts our relay saw, so the page can lay commits beside them
  - open issues and pull requests, from the public GitHub search API (no token;
    a few requests an hour, far below its limit; left out when it refuses)

Only public data and neutral numbers: no ranking of people, author names are
counted (how many people committed) but not published.

  python devpulse.py                 run, refresh every DEVPULSE_SECONDS (default 30 min)
  python devpulse.py --once OUT      one pass into OUT (used for the page's built-in snapshot)
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

log = logging.getLogger("tau-devpulse")

REPOS = [r.strip() for r in os.environ.get("DEVPULSE_REPOS", "IDNI/tau-testnet,IDNI/tau-lang").split(",") if r.strip()]
CLONES = os.environ.get("DEVPULSE_CLONES", "/state/devpulse")
PUBLIC_PATH = os.path.join(os.environ.get("PUBLIC_DIR", "/public"), "devpulse.json")
EVERY = float(os.environ.get("DEVPULSE_SECONDS", 1800))
API_EVERY = float(os.environ.get("DEVPULSE_API_SECONDS", 3600))
RELAY_HTTP = os.environ.get("RELAY_HTTP", "").rstrip("/")
PINS_FILE = os.environ.get("DEVPULSE_PINS_FILE", "/pins/Dockerfile")   # infra/node/Dockerfile: the commits our node is built from
RECENT = 30          # newest commits listed per repo
WEEKS = 52
DAYS = 90
UA = {"User-Agent": "tauhud-devpulse/1 (+https://tauhud.com)", "Accept": "application/vnd.github+json"}
# areas below these folders are counted one level deeper (src/boolean_algebras rather than src)
DEEP = {"src", "tests", "bindings", "scripts", "networks"}


def git(repo_dir: str, *args: str) -> str:
    return subprocess.run(["git", "-C", repo_dir, *args], check=True, capture_output=True, text=True, timeout=600).stdout


def sync(repo: str) -> str:
    """Clone once (history and file names only, no file contents), then fetch."""
    path = os.path.join(CLONES, repo.replace("/", "__") + ".git")
    if not os.path.isdir(path):
        os.makedirs(CLONES, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", "--bare", "--filter=blob:none", f"https://github.com/{repo}.git", path],
                       check=True, capture_output=True, text=True, timeout=900)
    else:
        git(path, "fetch", "--quiet", "--prune", "--tags", "origin", "+refs/heads/*:refs/heads/*")
    return path


def area(path: str) -> str:
    parts = path.split("/")
    if len(parts) == 1:
        return "root files"
    if parts[0] in DEEP and len(parts) > 2:
        return parts[0] + "/" + parts[1]
    return parts[0]


def default_branch(path: str) -> str:
    try:
        return git(path, "symbolic-ref", "--short", "HEAD").strip()
    except subprocess.CalledProcessError:
        return "main"


def read_log(path: str, branch: str, since: int) -> list[dict]:
    """Commits on the default branch since a time, newest first: sha, time, subject, author (kept local), areas."""
    out = git(path, "log", branch, f"--since=@{since}", "--no-renames", "--name-only",
              "--format=%x1e%H%x1f%ct%x1f%ae%x1f%s")
    commits = []
    for chunk in out.split("\x1e"):
        if not chunk.strip():
            continue
        head, _, files = chunk.partition("\n")
        sha, ct, author, subject = (head.split("\x1f") + ["", "", "", ""])[:4]
        names = [f for f in files.split("\n") if f.strip()]
        areas = Counter(area(f) for f in names)
        commits.append({"sha": sha, "ts": int(ct), "author": author.lower(), "title": subject.strip(),
                        "areas": [a for a, _ in areas.most_common()]})
    return commits


def monday(ts: int) -> int:
    d = datetime.fromtimestamp(ts, timezone.utc).date()
    d -= timedelta(days=d.weekday())
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


def day0(ts: int) -> int:
    return ts - ts % 86400


def pins() -> dict:
    """The tau-testnet and tau-lang commits our node is built from."""
    found = {}
    try:
        with open(PINS_FILE, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"\s*ARG\s+(TAU_TESTNET_REF|TAU_LANG_REF)=([0-9a-f]{7,40})", line)
                if m:
                    found[m.group(1)] = m.group(2)
    except OSError:
        pass
    env = os.environ.get("TAU_TESTNET_REF", "").strip()
    if re.fullmatch(r"[0-9a-f]{7,40}", env):
        found["TAU_TESTNET_REF"] = env
    return {"IDNI/tau-testnet": found.get("TAU_TESTNET_REF"), "IDNI/tau-lang": found.get("TAU_LANG_REF")}


def repo_pulse(repo: str, path: str, now: int, pin: str | None) -> dict:
    branch = default_branch(path)
    week_start = monday(now) - (WEEKS - 1) * 7 * 86400
    year = read_log(path, branch, week_start)
    weeks = [0] * WEEKS
    days = [0] * DAYS
    first_day = day0(now) - (DAYS - 1) * 86400
    for c in year:
        w = (monday(c["ts"]) - week_start) // (7 * 86400)
        if 0 <= w < WEEKS:
            weeks[w] += 1
        d = (day0(c["ts"]) - first_day) // 86400
        if 0 <= d < DAYS:
            days[d] += 1
    c4 = Counter()
    c12 = Counter()
    last = {}
    for c in year:
        for a in c["areas"]:
            last[a] = max(last.get(a, 0), c["ts"])
            if c["ts"] >= now - 28 * 86400:
                c4[a] += 1
            if c["ts"] >= now - 84 * 86400:
                c12[a] += 1
    areas = sorted(({"path": a, "c4": c4[a], "c12": n, "last": last[a]} for a, n in c12.items()),
                   key=lambda r: (-r["c12"], r["path"]))[:24]
    head_line = git(path, "log", "-1", branch, "--format=%H%x1f%ct%x1f%s").strip().split("\x1f")
    head = {"sha": head_line[0], "ts": int(head_line[1]), "title": head_line[2]}
    tags = []
    for line in git(path, "for-each-ref", "--sort=-creatordate", "--count=12", "refs/tags",
                    "--format=%(refname:short)%1f%(creatordate:unix)%1f%(objectname)").splitlines():
        name, ts, sha = (line.split("\x1f") + ["", "", ""])[:3]
        if name:
            tags.append({"name": name, "ts": int(ts or 0), "sha": sha})
    runs = None
    if pin:
        try:
            full = git(path, "rev-parse", "--verify", "--quiet", pin + "^{commit}").strip()
            ts, title = git(path, "log", "-1", full, "--format=%ct%x1f%s").strip().split("\x1f", 1)
            ahead = int(git(path, "rev-list", "--count", f"{full}..{branch}").strip())
            runs = {"sha": full, "ts": int(ts), "title": title, "ahead": ahead}
        except (subprocess.CalledProcessError, ValueError):
            runs = {"sha": pin, "ts": None, "title": "", "ahead": None}
    recent = [{k: c[k] for k in ("sha", "ts", "title", "areas")} for c in year[:RECENT]]
    for c in recent:
        c["areas"] = c["areas"][:3]
    return {
        "repo": repo, "url": f"https://github.com/{repo}", "branch": branch, "head": head, "runs": runs,
        "weeks": weeks, "week0": week_start, "days": days, "day0": first_day,
        "commits_4w": sum(1 for c in year if c["ts"] >= now - 28 * 86400),
        "commits_12w": sum(1 for c in year if c["ts"] >= now - 84 * 86400),
        "commits_52w": len(year),
        "people_12w": len({c["author"] for c in year if c["ts"] >= now - 84 * 86400}),
        "active_weeks_12": sum(1 for n in weeks[-12:] if n),
        "areas": areas, "tags": tags, "recent": recent,
    }


def search_count(q: str) -> int | None:
    url = "https://api.github.com/search/issues?per_page=1&q=" + urllib.parse.quote(q)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            return int(json.load(r)["total_count"])
    except Exception as e:  # noqa: BLE001 - rate limit or network: leave the number out
        log.info("GitHub search %s: %s", q, e)
        return None


def tracker(repo: str, now: int) -> dict:
    since = datetime.fromtimestamp(now - 30 * 86400, timezone.utc).strftime("%Y-%m-%d")
    out = {
        "issues_open": search_count(f"repo:{repo} is:issue is:open"),
        "prs_open": search_count(f"repo:{repo} is:pr is:open"),
        "closed_30d": search_count(f"repo:{repo} is:closed closed:>={since}"),
        "opened_30d": search_count(f"repo:{repo} created:>={since}"),
        "at": now,
    }
    return out if any(v is not None for k, v in out.items() if k != "at") else {}


def restarts() -> list[dict]:
    if not RELAY_HTTP:
        return []
    try:
        with urllib.request.urlopen(RELAY_HTTP + "/uptime", timeout=20) as r:
            j = json.load(r)
        return [{"at": x.get("new_block1_ts") or x.get("detected_at"), "old_tip": x.get("old_tip")} for x in j.get("restarts", [])]
    except Exception as e:  # noqa: BLE001
        log.info("relay /uptime: %s", e)
        return []


def build(now: int | None = None, trackers: dict | None = None) -> dict:
    now = int(now or time.time())
    pin = pins()
    repos = []
    for repo in REPOS:
        try:
            repos.append(repo_pulse(repo, sync(repo), now, pin.get(repo)))
        except Exception as e:  # noqa: BLE001 - one repo failing must not hide the other
            log.warning("%s: %s", repo, e)
    for r in repos:
        r["tracker"] = (trackers or {}).get(r["repo"], {})
    return {"v": 1, "generated_at": now, "source": "git", "repos": repos, "restarts": restarts()}


def write_atomic(path: str, text: str):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if len(sys.argv) == 3 and sys.argv[1] == "--once":
        now = int(time.time())
        data = build(now, {r: tracker(r, now) for r in REPOS})
        write_atomic(sys.argv[2], json.dumps(data, separators=(",", ":")))
        print(f"wrote {sys.argv[2]}: {', '.join(r['repo'] for r in data['repos'])}")
        return
    trackers, api_at = {}, 0.0
    while True:
        started = time.time()
        try:
            if started - api_at >= API_EVERY:
                fresh = {r: tracker(r, int(started)) for r in REPOS}
                trackers.update({r: v for r, v in fresh.items() if v})
                api_at = started
            data = build(int(started), trackers)
            if data["repos"]:
                write_atomic(PUBLIC_PATH, json.dumps(data, separators=(",", ":")))
                log.info("devpulse.json: %s", ", ".join(f"{r['repo']} {r['head']['sha'][:7]}" for r in data["repos"]))
        except Exception as e:  # noqa: BLE001
            log.warning("pass failed: %s", e)
        time.sleep(max(60.0, EVERY - (time.time() - started)))


if __name__ == "__main__":
    main()

"""Unit test of the build cache clean-up (no docker): reading `docker buildx du --verbose`, what goes and what stays
(never the tau-lang stage), once a day, and the status lines.

Run: python test_buildcache.py
"""
import json
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ.update(BUILDCACHE_DIR=os.path.join(TMP, "state"), BUILDCACHE_INFRA=TMP)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import buildcache as b  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


def entry(i, size, desc, used, kind="regular", reclaimable="true", parent=""):
    return (f"ID:\t\tid{i:02d}xxxxxxxxxxxxxxxxxxxx\nParent:\t\t{parent}\nCreated at:\t2026-11-01 09:04:11.52 +0000 UTC\n"
            f"Mutable:\tfalse\nReclaimable:\t{reclaimable}\nShared:\t\tfalse\nSize:\t\t{size}\nDescription:\t{desc}\n"
            f"Usage count:\t1\nLast used:\t{used}\nType:\t\t{kind}\n")


DU = "\n".join([
    entry(1, "1.54GB", "mount / from exec /bin/sh -c set -eux;     ./dev build Release       -DTAU_BUILD_JOBS=1", "3 weeks ago"),
    entry(2, "1.226GB", 'cached mount /root/.tau from exec /bin/sh -c set -eux; ./dev build Release with id "/tau-store"',
          "3 weeks ago", "exec.cachemount"),
    entry(3, "68.16MB", 'cached mount /root/.ccache from exec /bin/sh -c ./dev build Release with id "/tau-ccache"',
          "3 weeks ago", "exec.cachemount"),
    entry(4, "1.634GB", "[runtime  9/16] COPY --from=tau-builder /tau-store /root/.tau", "3 weeks ago"),
    entry(5, "350MB", "[tau-builder 6/9] RUN set -eux; git clone --filter=blob:none tau-lang", "2 months ago"),
    entry(6, "2.1GB", "[alerts 3/5] RUN apt-get update && apt-get install -y ffmpeg", "2 weeks ago"),
    entry(7, "1.9GB", "[alerts 4/5] RUN pip install --no-cache-dir -r requirements.txt", "5 days ago"),
    entry(8, "1.2GB", "[relay 3/4] RUN pip install --no-cache-dir -r requirements.txt", "4 days ago"),
    entry(9, "900MB", "[blog 3/5] RUN pip install", "26 hours ago"),
    entry(10, "800MB", "[share 2/4] RUN npm ci", "About an hour ago"),
    entry(11, "700MB", "[bot 3/5] RUN pip install", "3 weeks ago", reclaimable="false"),
    entry(12, "4.452kB", "local source for context", "6 days ago", "source.local"),
    "Shared:\t\t1.2GB\nPrivate:\t11GB\nReclaimable:\t10.26GB\nTotal:\t\t12.47GB\n",
])

# ---------------- reading docker's words ----------------
check(b.size_bytes("1.54GB") == 1540000000 and b.size_bytes("68.16MB") == 68160000 and b.size_bytes("0B") == 0
      and b.size_bytes("4.452kB") == 4452, "sizes in docker's decimal units")
check(b.age_seconds("26 hours ago") == 26 * 3600 and b.age_seconds("About an hour ago") == 3600
      and b.age_seconds("3 weeks ago") == 21 * 86400 and b.age_seconds("Less than a second ago") == 0
      and b.age_seconds("") is None, "ages in docker's words")
recs = b.records(DU)
check(len(recs) == 12, "twelve entries, the summary block is not one")
check(recs[-1]["id"].startswith("id12") and recs[-1].get("reclaimable") == "true",
      "the summary's Reclaimable line does not leak into the last entry")
check([r["id"][:4] for r in recs if r["protected"]] == ["id01", "id02", "id03", "id04", "id05"],
      "the tau-lang stage is recognised: its compile run, tau-store, ccache, the node image's copy, its own steps")

# ---------------- what goes ----------------
plan = b.plan(recs, keep_bytes=6e9, min_age_s=3 * 86400)
ids = [r["id"][:4] for r in plan]
check(not any(r["protected"] for r in plan), "never an entry of the tau-lang stage")
check("id11" not in ids and "id09" not in ids and "id10" not in ids, "never an entry in use or used in the last 3 days")
check(ids[:2] == ["id06", "id12"], "oldest first")
check(ids == ["id06", "id12", "id07", "id08"], "every old entry when the cache stays above the keep size")
check([r["id"][:4] for r in b.plan(recs, keep_bytes=9e9, min_age_s=3 * 86400)] == ["id06", "id12", "id07"],
      "stops once the cache is below the keep size")
check(b.plan(recs, keep_bytes=20e9, min_age_s=3 * 86400) == [], "nothing goes while the cache is below the keep size")

# ---------------- once a day, then docker asked per entry ----------------
ran, free = [], {"n": 2e9}


def fake_sh(cmd, timeout=600):
    ran.append(cmd)
    if cmd[:3] == ["docker", "buildx", "du"]:
        return 0, DU
    if cmd[:3] == ["docker", "buildx", "prune"]:
        free["n"] += 1e9
        return 0, "Total: 1GB"
    return 1, "?"


b.sh, b.disk_free = fake_sh, (lambda: free["n"])
line = b.run()
prunes = [c for c in ran if c[:3] == ["docker", "buildx", "prune"]]
check(len(prunes) == len(plan) and all("--all" in c and "--force" in c for c in prunes)
      and prunes[0][-1] == "id=" + recs[5]["id"], "each entry dropped on its own by its id")
check(f"dropped {len(plan)} of 12" in line and "tau-lang stage kept" in line, "the clean-up says what it did: " + line)
ran.clear()
check(b.run() == "build cache: looked at today already" and not ran, "at most once a day")
b.now = lambda: __import__("time").time() + 2 * 86400
check("dropped" in b.run(), "the next day again")
check("dropped" in b.run(force=True), "up cache now: at once")
with open(os.path.join(TMP, ".env"), "w") as f:
    f.write("BUILDCACHE_KEEP_GB=50\n")
check("nothing dropped" in b.run(force=True), "BUILDCACHE_KEEP_GB in .env sets the keep size")
os.remove(os.path.join(TMP, ".env"))

# ---------------- status ----------------
lines = b.status()
check(lines[0].startswith("cache:   12.4 GB in 12 entries, tau-lang stage 4.8 GB in 5"), "status: sizes, " + lines[0])
check(any("last clean-up" in x for x in lines), "status: the last clean-up")
b.sh = lambda cmd, timeout=600: (0, entry(1, "1GB", "[alerts 3/5] RUN pip install", "2 days ago"))
check(any("compiles tau-lang" in x for x in b.status()), "status warns when the tau-lang stage is gone")
b.sh = lambda cmd, timeout=600: (1, "no buildx")
check("did not answer" in b.run(force=True), "without buildx nothing is dropped")

print("all ok" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)

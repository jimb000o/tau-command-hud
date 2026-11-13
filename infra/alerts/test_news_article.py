"""Unit test of big IDNI news as a blog draft (no network): only a window the daily IDNI post marked as worth an
article gets one, once, while it is fresh; the writer reads the changes with IDNI's own docs, the draft waits unlisted
like a ship's article, and a number the changes do not hold keeps it from going out by itself.

Run: python test_news_article.py   (needs git)
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime

TMP = tempfile.mkdtemp()
SRC = os.path.join(TMP, "src")
os.environ.update(PUBLIC_DIR=TMP, BLOG_STATE=os.path.join(TMP, "blog.json"), DEVPULSE_CLONES=os.path.join(TMP, "clones"),
                  NEWS_AI_KEY="test", TELEGRAM_BOT_TOKEN="", X_API_KEY="", BLOG_ART=os.path.join(TMP, "no-art"),
                  STATE_PATH=os.path.join(TMP, "alerts.json"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog  # noqa: E402
import idni_digest as idg  # noqa: E402
import news_article as na  # noqa: E402

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


def commit(files, msg, ts):
    for path, text in files.items():
        full = os.path.join(SRC, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(text)
    run("add", "-A")
    run("commit", "-q", "-m", msg, ts=ts)
    return run("rev-parse", "HEAD")


os.makedirs(SRC)
run("init", "-q", "-b", "main")
commit({"consensus/rules.py": "LIMIT = 2\n", "docs/rules.md": "Two accounts at a time.\n"}, "start", at("2026-11-14T08:00:00Z"))
sha = commit({"consensus/rules.py": "LIMIT = None\n", "docs/rules.md": "Nothing limits how many accounts hold a rule. At most 32 comparisons.\n"},
             "feat(policy): judge each payment by its sender's own rule", at("2026-11-14T09:00:00Z"))
text = na.change_text(SRC, sha)
check("judge each payment" in text and "LIMIT = None" in text and "Nothing limits how many accounts hold a rule" in text,
      "the writer reads the change: message, code diff and IDNI's docs")

end = at("2026-11-15T10:00:00Z")
big = {"id": f"idni-{end}", "end": end, "status": "ready", "article": True, "shas": [sha], "title": "Every account can hold its own rule",
       "points": ["Each payment is judged by its sender's own rule."], "why": "Anyone can try a rule on the live testnet."}
small = dict(big, id="small", article=False)
old = dict(big, id="old", end=at("2026-11-13T10:00:00Z"))
check([d["id"] for d in na.due([small, big, old], {}, end + 3600)] == [big["id"]],
      "only a window marked as worth an article, from 14 November on (the 12 November rules have their own)")
check(na.due([big], {big["id"]: "x"}, end + 3600) == [] and na.due([big], {}, end + 4 * 86400) == [], "once, and only while fresh")

asked = []
GOOD = {"title": {"en": "Every account can now hold its own rule", "zh": "z", "ja": "j"},
        "dek": {"en": "The Tau Net testnet judges each payment by its sender's own rule.", "zh": "z", "ja": "j"},
        "why": [{"en": "For you: a limit or a co-signer on your own account.", "zh": "z", "ja": "j"},
                {"en": "For Tau Net: rules for everyone, not two accounts.", "zh": "z", "ja": "j"},
                {"en": "Limit: a rule holds at most 32 comparisons.", "zh": "z", "ja": "j"}],
        "body": {"en": "## What changed\nNothing limits how many accounts hold a rule.\n## What it gives you\nA limit.\n## Where it stops\n32 comparisons.\n## What is still open\nMore.", "zh": "z", "ja": "j"},
        "x": "Every account on the Tau Net testnet can now hold its own payment rule.", "card": {"line": "Rules for every account", "why": ["a", "b", "c"]}}


def fake(answer):
    def f(facts):
        asked.append(facts)
        return json.loads(json.dumps(answer))
    return f


# the daily post's file, where the blog service reads it
os.makedirs(os.path.dirname(idg.files()[0]), exist_ok=True)
with open(idg.files()[0], "w") as f:
    json.dump({"version": idg.VERSION, "items": [small, big]}, f)
os.makedirs(os.path.join(TMP, "clones"), exist_ok=True)
subprocess.run(["git", "clone", "-q", "--bare", SRC, os.path.join(TMP, "clones", "IDNI__tau-testnet.git")], check=True)
did = na.tick(end + 3600, fake(GOOD))
st = blog.state()
a = json.load(open(os.path.join(TMP, "blog", "drafts", st["drafts"][did] + ".json")))
check(did == "2026-11-15-idni-news" and a["kind"] == "news" and a["status"] == "draft" and a["t0"] == end
      and st["news_drafted"] == {big["id"]: did} and did in st["drafted_at"], "one draft, unlisted like a ship's article, remembered")
check(len(asked) == 1 and "Every account can hold its own rule" in json.dumps(asked[0]) and a["sources"] == [f"https://github.com/IDNI/tau-testnet/commit/{sha}"],
      "written from the daily post and the changes, with the changes as sources")
check(a["check"] == {"unknown_numbers": [], "hype": []}, "every number is in the changes: clean, may go out by itself")
check(na.tick(end + 7200, fake(GOOD)) is None and len(asked) == 1, "never twice")

bad = dict(GOOD, body=dict(GOOD["body"], en=GOOD["body"]["en"] + "\nIt is 40 times faster, finally."))
a2 = na.article(big, na.facts_of(big, SRC), bad, end)
check("40" in a2["check"]["unknown_numbers"] and a2["check"]["hype"], "a number not in the changes, or hype: marked, waits for a look")
check(blog.ID_RE.match(did) and blog.kicker(a).startswith("News · 15 November 2026") and not blog.island_story(a),
      "an id up blog publish takes, the News kicker and the site's own picture")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

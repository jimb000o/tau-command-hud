"""Unit test of No Memo's feedback box (nomemo_feedback.py): kept as one JSON line, cleaned, limited, no IP stored.

Run: python test_nomemo_feedback.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nomemo_feedback as nf  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


d = tempfile.mkdtemp()
T = [1_700_000_000.0]
f = nf.Feedback(path=os.path.join(d, "fb.jsonl"), clock=lambda: T[0], enabled=True)
W = "ab" * 48
r = f.route("/nomemo/feedback", "t=Claim%20took%20too%20long%0A%1b[31m&w=" + W + "&d=5&c=1&l=zh", "1.2.3.4")
check(r == {"ok": True}, "a remark is taken")
rows = [json.loads(x) for x in open(os.path.join(d, "fb.jsonl"), encoding="utf-8")]
check(len(rows) == 1 and rows[0]["text"] == "Claim took too long [31m" and rows[0]["wallet"] == W and rows[0]["d"] == 5 and rows[0]["c"] == 1 and rows[0]["l"] == "zh",
      "kept with wallet, progress and language; control characters gone")
check("1.2.3.4" not in open(os.path.join(d, "fb.jsonl")).read() and set(rows[0]) == {"at", "text", "wallet", "d", "c", "l"}, "no IP address, nothing else kept")
check(f.add("1.2.3.4", "again")["error"] == "wait", "one remark every 30 s per visitor")
check(f.add("5.6.7.8", "hi") == {"error": "short"} and f.add("5.6.7.8", "x" * 601) == {"error": "long"}, "too short, too long")
r = f.add("5.6.7.8", "nice game", wallet="not-a-wallet", done="abc", lang="de")
rows = [json.loads(x) for x in open(os.path.join(d, "fb.jsonl"), encoding="utf-8")]
check(r == {"ok": True} and rows[1]["wallet"] is None and rows[1]["d"] is None and rows[1]["l"] is None, "bad wallet, progress and language are dropped")
for i in range(nf.PER_DAY - 1):
    T[0] += nf.GAP
    f.add("1.2.3.4", f"remark {i}")
T[0] += nf.GAP
check(f.add("1.2.3.4", "one too many") == {"error": "today"}, "ten a day per visitor")
T[0] += 86400
check(f.add("1.2.3.4", "next day") == {"ok": True}, "the limits are gone the next UTC day")
off = nf.Feedback(path=os.path.join(d, "off.jsonl"), enabled=False)
check(off.add("1.1.1.1", "hello there") == {"error": "off"} and not os.path.exists(os.path.join(d, "off.jsonl")), "switched off: nothing kept")
check(f.route("/nomemo", "", "1.1.1.1") is None, "other paths are not ours")

print("all good" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

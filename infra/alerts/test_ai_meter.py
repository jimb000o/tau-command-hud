"""ai_meter.py: the Anthropic API's costs per answer and per month, without network (7 November 2026).

Run: python test_ai_meter.py
"""
import os
import sys
import tempfile

D = tempfile.mkdtemp()
os.environ["AI_USAGE_DIR"] = D
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ai_meter  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


NOV = 1794000000   # 6 November 2026
check(ai_meter.month(NOV) == "2026-11", "month in UTC")
check(abs(ai_meter.cost("claude-sonnet-5-5", {"input_tokens": 10_000, "output_tokens": 2_000}) - 0.04) < 1e-9,
      "sonnet 5.5: 10k in, 2k out = 4 cents")
check(abs(ai_meter.cost("claude-haiku-5-5", {"input_tokens": 1_000, "output_tokens": 100}) - 0.00015) < 1e-12, "haiku 5.5: a chat check")
check(abs(ai_meter.cost("claude-sonnet-5-5", {"cache_creation_input_tokens": 1_000_000}) - 2.5) < 1e-9, "cache writes 1.25 x input")
check(abs(ai_meter.cost("claude-sonnet-5-5", {"cache_read_input_tokens": 1_000_000}) - 0.2) < 1e-9, "cache reads")
check(ai_meter.cost("claude-new-model", {"input_tokens": 1_000_000}) == 10.0, "unknown model: the dearest price")
check(ai_meter.cost("claude-haiku-5-5", {"input_tokens": 200_000}) == 0.1, "haiku over 100k tokens: the higher price")
check(ai_meter.totals("2026-11") is None and "nothing measured yet" in ai_meter.line(NOV), "nothing measured: no total")

ai_meter.meter("blog", "claude-sonnet-5-5", {"input_tokens": 10_000, "output_tokens": 2_000}, NOV)
ai_meter.meter("news", "claude-sonnet-5-5", {"input_tokens": 50_000, "output_tokens": 1_000}, NOV)


class Usage:   # the SDK's object, as chatai.py gets it
    input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens = 1_000, 100, 0, None


ai_meter.meter("chat", "claude-haiku-5-5", Usage(), NOV)
check(ai_meter.meter("chat", "claude-haiku-5-5", None, NOV) == 0.0, "no usage block: nothing counted")
t = ai_meter.totals("2026-11")
check(t["answers"] == 3 and abs(t["usd"] - 0.15015) < 1e-4 and t["since"] == "2026-11-06" and set(t["by"]) == {"blog", "news", "chat"},
      f"three writers summed: {t}")
check(ai_meter.totals("2026-10") is None, "a month before measuring began: no total")
check(ai_meter.totals("2026-12")["answers"] == 0, "a later month without answers: zero")
check("3 answers, about $0.15" in ai_meter.line(NOV) and "billing" in ai_meter.line(NOV), "the up line")
check(not any("prompt" in open(os.path.join(D, n)).read() for n in os.listdir(D)), "numbers only in the files")

ai_meter.DIR = "/proc/no-such-dir"
check(ai_meter.meter("blog", "claude-sonnet-5-5", {"input_tokens": 1}, NOV) > 0, "an unwritable folder never raises")
check(open(os.path.join(HERE, "ai_meter.py")).read() == open(os.path.join(HERE, "..", "relay", "ai_meter.py")).read(),
      "relay/ai_meter.py is the same file")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)

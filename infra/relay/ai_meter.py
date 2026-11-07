"""What the Anthropic API costs us, measured at every answer: the blog drafts (blog.py), the IDNI news line and the
daily IDNI post (devpulse.py, idni_digest.py) and the troll box's AI check (relay/chatai.py) each add the tokens of
every answer (its usage block) times Anthropic's list price to this month's totals. One file per writer in
AI_USAGE_DIR (the ai_usage volume, /ai-usage), numbers only, never a prompt or a text. Read by the monthly costs post
(alerts.py) and by `up` (the "anthropic:" line). The bill itself: https://platform.claude.com/settings/billing

The same file sits in infra/relay/ (the relay is built from its own folder); test_ai_meter.py checks both are equal.

Run: python ai_meter.py line   (this month in one line)
"""
import json
import os
import sys
import time

DIR = os.environ.get("AI_USAGE_DIR", "/ai-usage")
# US dollars per million tokens: (input, output, cache read); cache writes cost 1.25 x input.
# Anthropic's list prices on 7 November 2026; change them here when Anthropic does.
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50, 0.01),     # prompts over 100k tokens: 0.50 / 2.50 (see cost())
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-sonnet-5": (2.00, 10.00, 0.20),
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-opus-5": (5.00, 25.00, 0.50),
    "claude-fable-5-1": (10.00, 50.00, 0.25),
}
UNKNOWN = (10.00, 50.00, 1.00)   # a model not in the list: the dearest prices, so the estimate is never too low


def month(now: float | None = None) -> str:
    return time.strftime("%Y-%m", time.gmtime(time.time() if now is None else now))


def cost(model: str, usage: dict) -> float:
    """US dollars for one answer, from its usage block (input, output, cache write and cache read tokens)."""
    u = usage or {}
    tin, tout = int(u.get("input_tokens") or 0), int(u.get("output_tokens") or 0)
    tw, tr = int(u.get("cache_creation_input_tokens") or 0), int(u.get("cache_read_input_tokens") or 0)
    pin, pout, pread = PRICES.get(model) or UNKNOWN
    if model == "claude-haiku-5-5" and tin + tw + tr > 100_000:
        pin, pout, pread = 0.50, 2.50, 0.05
    return (tin * pin + tout * pout + tw * pin * 1.25 + tr * pread) / 1e6


def meter(writer: str, model: str, usage, now: float | None = None) -> float:
    """Adds one answer to this month's totals of `writer` (blog, news, digest, chat); returns its cost. Never raises:
    a full disk or a missing folder must not stop a post or the chat."""
    if usage is None:   # no usage block (a stand-in in a test): nothing to count
        return 0.0
    if not isinstance(usage, dict):   # the SDK's Usage object (chatai.py)
        usage = {k: getattr(usage, k, 0) or 0 for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")}
    usd = cost(model, usage)
    try:
        path = os.path.join(DIR, f"{writer}.json")
        try:
            with open(path) as f:
                j = json.load(f)
        except (OSError, ValueError):
            j = {}
        j.setdefault("since", time.strftime("%Y-%m-%d", time.gmtime(time.time() if now is None else now)))
        m = j.setdefault("months", {}).setdefault(month(now), {"answers": 0, "usd": 0, "models": {}})
        m["answers"] += 1
        m["usd"] = round(m["usd"] + usd, 6)
        mm = m["models"].setdefault(model, {"answers": 0, "usd": 0})
        mm["answers"] += 1
        mm["usd"] = round(mm["usd"] + usd, 6)
        os.makedirs(DIR, exist_ok=True)
        with open(path + ".tmp", "w") as f:
            json.dump(j, f, indent=1)
        os.replace(path + ".tmp", path)
    except OSError:
        pass
    return usd


def totals(mon: str) -> dict | None:
    """All writers together for one month: {"usd", "answers", "since", "by": {writer: usd}}; None while nothing was
    measured yet, or when measuring began after that month."""
    try:
        names = sorted(n for n in os.listdir(DIR) if n.endswith(".json"))
    except OSError:
        return None
    out = {"usd": 0.0, "answers": 0, "since": "", "by": {}}
    for n in names:
        try:
            with open(os.path.join(DIR, n)) as f:
                j = json.load(f)
        except (OSError, ValueError):
            continue
        s = j.get("since") or ""
        if s and (not out["since"] or s < out["since"]):
            out["since"] = s
        m = (j.get("months") or {}).get(mon) or {}
        out["usd"] += float(m.get("usd") or 0)
        out["answers"] += int(m.get("answers") or 0)
        if m.get("answers"):
            out["by"][n[:-5]] = round(float(m.get("usd") or 0), 4)
    if not out["since"] or out["since"][:7] > mon:
        return None
    out["usd"] = round(out["usd"], 4)
    return out


def line(now: float | None = None) -> str:
    t = totals(month(now))
    if not t:
        return "anthropic: nothing measured yet (from the next blog draft, IDNI post or chat check on)"
    by = ", ".join(f"{k} ${v:.2f}" for k, v in t["by"].items()) or "nothing yet"
    return (f"anthropic: this month {t['answers']} answers, about ${t['usd']:.2f} ({by}; measured since {t['since']}); "
            "the bill: https://platform.claude.com/settings/billing")


if __name__ == "__main__":
    if sys.argv[1:] == ["line"]:
        print(line())
    else:
        sys.exit("usage: python ai_meter.py line")

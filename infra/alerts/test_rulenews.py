"""Unit test of the rule posts (19 Nov 2026: rules got added to the chain and the channels barely said so), no network:
a rule text a person writes is told once, ever (a restart that brings the same text back is no news, nor a person taking
one of our own server's rules); our wallets' and IDNI's rules are never told as people's; the first run is history;
Telegram gets one post a day at most, in plain words with the block, and X one a week with the count.

Run: python test_rulenews.py   (needs websockets==15.0.1)
"""
import asyncio
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="", XPLAN_DIR=TMP)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402
import rulenews  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


def rule(cap):   # the wallet's own shape (wallet/index.html): no payment above cap
    return (f"always ( (i1[t]:bv[24] >= {{ #x{cap + 1:06x} }}:bv[24]) ? (o5[t]:bv[24] = {{ #x000000 }}:bv[24]) : "
            f"(o5[t]:bv[24] = {{ #x000001 }}:bv[24]) ).")


HAND = "always ( (i1[t]:bv[24] > { #x0003e8 }:bv[24]) ? (o5[t]:bv[24] = { #x000000 }:bv[24]) : (o5[t]:bv[24] = { #x000001 }:bv[24]) )."
SUN = 1_800_000_000 - 1_800_000_000 % 86400   # a UTC midnight
while alerts.datetime.fromtimestamp(SUN, alerts.timezone.utc).weekday() != rulenews.WEEK_DAY:
    SUN += 86400
T = SUN - 2 * 86400 + 10 * 3600    # Friday 10:00 UTC


def entry(text, by="people", first=100, ts=None, people=1, kinds=("cap",)):
    return {"text": text, "by": by, "first": first, "first_ts": ts if ts is not None else T, "people": people, "kinds": list(kinds)}


# 1. the first run is history; then a person's new text is news, ours and IDNI's are not
st = rulenews.fresh_state()
check(rulenews.scan(st, [entry(rule(500))], T) == [] and st["primed"], "first run: what the wall holds is history")
got = rulenews.scan(st, [entry(rule(500)), entry(rule(1000), first=120), entry(rule(7), by="ours"), entry(rule(9), by="idni")], T + 60)
check([g["first"] for g in got] == [120], f"only the person's new rule is news: {got}")
check(got[0]["plain"] == "No payment above 1,000 test AGRS.", f"in plain words, as the wallet reads it: {got[0]['plain']}")
check(rulenews.plain({"text": HAND, "kinds": ["cap"]}) == "A rule written by hand that caps each payment.", "a hand-written rule by what it checks")

# 2. once, ever: the testnet restarts and people sign the same rules again; a person takes one of ours
again = rulenews.scan(st, [entry(rule(1000), first=3, ts=T + 86400), entry(rule(7), first=4, ts=T + 86400)], T + 86400)
check(again == [], "the same rule text after a restart, or a person taking our rule, is no news")
rulenews.scan(st, [entry(rule(1000), first=3, people=5)], T + 86400 + 60)
check(st["found"][0]["people"] == 5, "how many took it since is kept for the week's post")
old = rulenews.scan(st, [entry(rule(42), ts=T - 3 * 86400)], T + 86400 + 120)
check(old == [] and rulenews.key(rule(42)) in st["told"], "a rule caught up after an outage is remembered, never told late")
check(rulenews.key(rule(42)) == rulenews.key(rule(42).replace(" ", "\n  ")), "spacing does not make a rule new")

# 3. Telegram: the day's post, in plain words, with its block and why it matters
txt = rulenews.telegram_text(st["found"], alerts.REAL_LINE, rulenews.WHY[0])
check("A new rule on the testnet" in txt and "No payment above 1,000 test AGRS." in txt and "?b=120" in txt, txt)
check("Taken by 5 wallets so far." in txt and "Why it matters" in txt and rulenews.WALL in txt, "how many took it, why, the wall")
check(alerts.tg_kind(txt) == "rules", "counted as a rule post in the channel's clicks")
many = [{**st["found"][0], "key": str(i), "first": 100 + i} for i in range(6)]
check("6 new rules on the testnet" in rulenews.telegram_text(many, "", None) and "…and 2 more on the rules wall." in
      rulenews.telegram_text(many, "", None), "many rules: counted, four named, the rest on the wall")
x = alerts.x_post(rulenews.x_lines(st["found"]), rulenews.WALL, keep=2)
check(alerts.x_len(x) <= 280 and "No payment above 1,000 test AGRS." in x and x.rstrip().endswith("#TauNet"), f"X: {x}")


# 4. the watcher: one Telegram post a day at RULES_HOUR, one X post a week; nothing on a day without a new rule
class Fake(alerts.Outlet):
    def __init__(self, name):
        self.name, self.sent = name, []

    def enabled(self):
        return True

    def send_text(self, text, *a):
        self.sent.append(text)
        return True, None, ""


async def main():
    tg, xo = Fake("telegram"), Fake("x")
    w = alerts.Watcher([tg, xo])
    w.save_state = lambda: None
    wall = [entry(rule(500))]
    await w.maybe_rules(T, wall)                                    # first run
    wall.append(entry(rule(2000), first=300, ts=T + 3600))
    await w.maybe_rules(T + 3600, wall)                             # Friday 11:00: found, not yet the hour
    check(tg.sent == [], "no post before the day's hour")
    day = T - 10 * 3600 + rulenews.HOUR * 3600
    await w.maybe_rules(day + 60, wall)
    check(len(tg.sent) == 1 and "No payment above 2,000 test AGRS." in tg.sent[0], f"the day's post at its hour: {tg.sent}")
    await w.maybe_rules(day + 900, wall)
    check(len(tg.sent) == 1, "once a day")
    await w.maybe_rules(day + 86400 + 60, wall)
    check(len(tg.sent) == 1, "a day without a new rule: no post")
    wall.append(entry(rule(3000), first=400, ts=day + 86400 + 120))
    await w.maybe_rules(day + 86400 + 180, wall)
    check(len(tg.sent) == 2 and "3,000" in tg.sent[1] and "2,000" not in tg.sent[1], "the next day only the next day's rules")
    check(rulenews.WHY[0] not in tg.sent[1] or rulenews.WHY[0] not in tg.sent[0], "why it matters is not the same line twice running")
    wk = SUN + rulenews.WEEK_HOUR * 3600 + 60
    await w.maybe_rules(wk, wall)
    check(len(xo.sent) == 1 and xo.sent[0].startswith("📜 On Tau a wallet can carry rules of its own") and
          "wallets wrote 2 rules the testnet had never carried before" in xo.sent[0] and "The newest: No payment above 3,000" in xo.sent[0], f"the week on X: {xo.sent}")
    await w.maybe_rules(wk + 600, wall)
    check(len(xo.sent) == 1, "once a week")
    check(len(tg.sent) == 2, "the X week is no Telegram post")


asyncio.run(main())
print("\n" + ("all ok" if not failed else f"{failed} FAILED"))
sys.exit(1 if failed else 0)

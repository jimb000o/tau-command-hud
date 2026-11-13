"""Unit test of the crew's ship log (no network): the week's numbers, the site's log of the same seven days and the
monthly bills become one members-only post; entries of other weeks stay out, nothing personal goes in, and the
Fourthwall body asks for members only.

Run: python test_crewlog.py
"""
import sys
from datetime import datetime, timezone

import crewlog

fails = 0


def check(ok, what):
    global fails
    print(("ok   " if ok else "FAIL ") + what)
    fails += 0 if ok else 1


end = datetime(2026, 11, 16, 8, 0, tzinfo=timezone.utc).timestamp()
r = {"start": end - 7 * 86400, "end": end}
updates = [{"tag": "Blog", "on": "2026-11-08", "html": "old week"},
           {"tag": "Crew", "on": "2026-11-13", "link": "/crew/", "html": "Crew: the paid membership has its <b>own</b> page."},
           {"tag": "Agorzilla", "on": "2026-11-14", "link": "https://agorzilla.com", "html": "Agorzilla &amp; friends"}]
costs = {"items": [{"amount": 6, "cur": "EUR"}, {"amount": 200, "cur": "USD"}, {"amount": 19.34, "cur": "EUR"}, {"amount": None, "cur": "USD"}]}
title, d = crewlog.compose(r, ["1,234 blocks, one every 30 s", "5 transactions <from> 3 accounts"], "9–15 Nov 2026", updates, costs, 4)
check(title == "Ship log · 9–15 Nov 2026", "title names the week")
check("old week" not in d and "Crew: the paid" not in d and "Agorzilla &amp; friends" in d, "only this week's log entries, the money pages left out, text escaped")
check('href="https://agorzilla.com"' in d, "each entry links to its page")
check("&lt;from&gt;" in d, "the recap lines are escaped")
check("€25.34" in d and "$200.00" in d, "bills summed per currency, unknown amounts left out, no exchange rate")
check("one of 4 in the crew" in d, "the crew counted, no names")
check("not affiliated with IDNI" in d, "the IDNI line")
_, d1 = crewlog.compose(r, [], "x", [], {}, None)
check("No changes to the site this week" in d1 and "What it costs" not in d1 and "in the crew" not in d1, "an empty week still reads well")
b = crewlog.body(title, d, end)
check(b["access"] == {"type": "MembersOnly"} and b["attributes"]["core"]["liveAt"] == "2026-11-16T08:00:00Z", "members only, live now")
check(crewlog.members([{"members": 3}, {"members": 1}, {"members": None}]) == 4 and crewlog.members([{"members": None}]) is None, "members summed over tiers")
many = [{"on": "2026-11-12", "html": f"change {i}"} for i in range(11)]
_, d2 = crewlog.compose(r, [], "x", many, {}, 0)
check("and 3 smaller changes" in d2, "long weeks shortened with a link to the full log")
print("\nall ok" if not fails else f"\n{fails} failed")
sys.exit(1 if fails else 0)

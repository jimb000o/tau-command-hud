"""Unit test of our share of the shop and the crew (no network): an order counts with Fourthwall's cost, the member
discount and the card fee taken off, tax and shipping left out; cancelled orders and samples do not count; a membership
counts once per billing day while it is active and keeps what was paid after it ends; the public file names nobody.

Run: python test_earnings.py
"""
import json
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ["EARNINGS_STATE_PATH"] = os.path.join(TMP, "state.json")
os.environ["PUBLIC_DIR"] = TMP
import earnings  # noqa: E402

fails = 0


def check(ok, what):
    global fails
    print(("ok   " if ok else "FAIL ") + what)
    fails += 0 if ok else 1


M = lambda v: {"value": v, "currency": "USD"}
order = {"id": "o1", "email": "buyer@example.com", "status": "SHIPPED", "createdAt": "2026-11-14T10:00:00Z", "source": {"type": "ORDER"},
         "amounts": {"subtotal": M(35), "discount": M(3.5), "shipping": M(6), "tax": M(6.6), "donation": M(0), "total": M(44.1)},
         "offers": [{"quantity": 1, "variant": {"unitPrice": M(35), "unitCost": M(11.75), "cost": M(11.75)}}]}
s = earnings.order_share(order)
fee = round(44.1 * 0.039 + 0.30, 2)
check(s and s["share"] == round(35 - 3.5 - 11.75 - fee, 2), f"a tee: 35 - 3.50 discount - 11.75 cost - {fee} card fee = {s and s['share']}")
check(s["on"] == "2026-11-14" and s["cur"] == "USD", "day and currency of the order")
two = dict(order, offers=[{"quantity": 2, "variant": {"unitCost": M(5.95), "cost": M(11.9)}}])
check(abs(earnings.item_cost(two) - 11.9) < 1e-9, "two mugs cost 2 x 5.95")
check(earnings.order_share(dict(order, status="CANCELLED")) is None, "a cancelled order does not count")
check(earnings.order_share(dict(order, source={"type": "SAMPLES_ORDER"})) is None, "a sample does not count")

days = earnings.periods("2026-01-31T09:00:00Z", "MONTHLY", earnings.datetime(2026, 4, 1, tzinfo=earnings.timezone.utc).timestamp())
check(days == ["2026-01-31", "2026-02-28", "2026-03-31"], f"monthly from the 31st: {days}")
check(earnings.periods("2026-01-10T00:00:00Z", "ANNUAL", earnings.datetime(2027, 3, 1, tzinfo=earnings.timezone.utc).timestamp()) == ["2026-01-10", "2027-01-10"], "yearly")

st = {}
member = {"id": 7, "email": "member@example.com", "nickname": "M", "createdAt": "2026-11-13T12:00:00Z",
          "subscription": {"type": "ACTIVE", "variant": {"interval": "MONTHLY", "amount": M(3.5)}}}
now = earnings.datetime(2026, 12, 20, tzinfo=earnings.timezone.utc).timestamp()
check(earnings.note_members(st, [member], now) == 2, "an active member: two billing days by 20 December")
check(earnings.note_members(st, [member], now) == 0, "the same days are not counted twice")
gone = dict(member, subscription={"type": "CANCELLED", "variant": member["subscription"]["variant"]})
later = earnings.datetime(2027, 2, 20, tzinfo=earnings.timezone.utc).timestamp()
check(earnings.note_members(st, [gone], later) == 0 and len(st["crew"]["7"]) == 2, "after cancelling: what was paid stays, nothing new")
check(earnings.crew_share(3.5) == round(3.5 - 0.175 - (3.5 * 0.039 + 0.30), 2), "a Deckhand month after the 5 % fee and the card fee")

pub = earnings.public([s], st, now)
text = json.dumps(pub)
check("@" not in text and "o1" not in text and '"M"' not in text, "the public file names no buyer, member or order")
kinds = {(i["on"], i["kind"]) for i in pub["items"]}
check(("2026-11-14", "shop") in kinds and ("2026-11-13", "crew") in kinds and ("2026-12-13", "crew") in kinds, "shop and crew per day")

check("members" not in pub and earnings.public([s], st, now, earnings.active([member, gone]))["members"] == 1, "the public file counts active members only")

ns = {}
check(earnings.news(ns, [order], [member]) == [], "the first read only learns what is there")
o2 = dict(order, id="o2", offers=[{"name": "No Memo tee", "quantity": 1, "variant": {"unitCost": M(11.75)}}])
m2 = dict(member, id=8, subscription={"type": "ACTIVE", "variant": {"tierId": 51606, "interval": "MONTHLY", "amount": M(9)}})
lines = earnings.news(ns, [order, o2], [member, m2], {51606: "Navigator"})
check(len(lines) == 2 and "No Memo tee" in lines[0] and "Navigator" in lines[1] and "Active members now: 2" in lines[1], f"one line per new order and member: {lines}")
check(not any("@" in x for x in lines), "no e-mail address in the owner's note")
check(earnings.news(ns, [order, o2], [member, m2]) == [], "nothing told twice")

sys.exit(1 if fails else 0)

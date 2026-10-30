"""Unit test of the donation thank-yous (no network): only AGRS of the real
contract and ETH count, dust and own wallets do not, each donation is thanked
once, old history on the first run stays quiet, the post has no dashes.

Run: python test_donations.py   (needs websockets==15.0.1)
"""
import os
import sys
import tempfile
import time
from decimal import Decimal

TMP = tempfile.mkdtemp()
os.environ.update(DONATION_STATE_PATH=os.path.join(TMP, "donations.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="",
                  DONATION_IGNORE_FROM="0x00000000000000000000000000000000000000aa")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import donations as dn  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


class Fake:
    name = "telegram"

    def __init__(self):
        self.sent = []

    def enabled(self):
        return True

    def send_text(self, text):
        self.sent.append(text)
        return True, None, ""


ME = dn.ADDRESS.lower()
DONOR = "0x1234567890abcdef1234567890abcdef12345678"
NOW = time.time()


def tr(tx, amount, asset="AGRS", contract=dn.AGRS_CONTRACT, frm=DONOR, age=60, symbol="AGRS"):
    return {"tx": tx, "from": frm, "to": ME, "contract": contract if asset == "AGRS" else "", "asset": asset,
            "amount": Decimal(amount), "ts": NOW - age, "block": 1, "ok": True, "log": 0 if asset == "AGRS" else None,
            "symbol": symbol}


old = tr("0xold", "20", age=30 * 86400)
first = tr("0xfirst", "50", age=3600)
spam = [tr("0xspam", "1000", contract="0xdeadbeef", symbol="AGRS"), tr("0xdust", "0.000001", asset="ETH"),
        tr("0xzero", "0"), tr("0xself", "5", frm="0x00000000000000000000000000000000000000aa")]

f = Fake()
w = dn.Donations([f])
news = w.update([old, first] + spam, NOW)
check([d["tx"] for d in news] == ["0xfirst"], "first run: only the recent donation is news, old history and spam stay quiet")
check(len(w.state["donations"]) == 2, "fake AGRS token, dust, zero and own wallet are not donations")
w.thank(news)
check(len(f.sent) == 1 and "Thank you, 0x1234…5678" in f.sent[0], "thank-you names the sender by short address")
check("50 AGRS" in f.sent[0] and "first donation" not in f.sent[0], "amount shown; the 30-day-old one was first")
check("–" not in f.sent[0] and "—" not in f.sent[0], "no dashes in the post")
check("2 people" not in f.sent[0] and "1 person has" in f.sent[0], "same sender twice counts as one person")

news = w.update([old, first] + spam, NOW + 60)
w.thank(news)
check(news == [] and len(f.sent) == 1, "a donation is thanked only once")

eth = tr("0xeth", "0.01", asset="ETH", frm="0x9999999999999999999999999999999999999999", age=0)
news = w.update([old, first, eth], NOW + 120)
w.thank(news)
check(len(f.sent) == 2 and "0.01 ETH" in f.sent[1] and "2 people have" in f.sent[1], "later ETH donation thanked, two people")

s = dn.summary(w.state["donations"])
check(s["donors"] == 2 and s["count"] == 3 and s["totals"] == {"AGRS": "70", "ETH": "0.01"}, "public summary totals")
check(s["items"][0]["tx"] == "0xeth", "public list newest first")

w2 = dn.Donations([Fake()])
check(w2.state["primed"] and len(w2.state["donations"]) == 3, "state survives a restart")

fresh = dn.Donations([f])
fresh.state = {"primed": False, "donations": [], "posted": {}}
check(fresh.update([old], NOW) == [], "fresh volume: a month-old donation is not posted again")

check(dn.fmt_amount(Decimal("50.000000000000000000")) == "50" and dn.fmt_amount(Decimal("1234.5")) == "1,235",
      "amounts read cleanly")

# value in money: the price service is faked; "now" within the hour, the day's price for older ones
calls = []


def fake_json(url):
    calls.append(url)
    if "/contract/" in url:
        return {"id": "agoras"}
    if "/simple/price" in url:
        return {"agoras": {"eur": 0.2, "usd": 0.25, "cny": 1.8, "jpy": 38}, "ethereum": {"eur": 3000, "usd": 3500, "cny": 25000, "jpy": 500000}}
    if "/history" in url:
        return {"market_data": {"current_price": {"eur": 0.1, "usd": 0.12, "cny": 0.9, "jpy": 19}}}
    raise ValueError(url)


dn.get_json, dn.time.sleep = fake_json, lambda s: None
w.add_fiat(NOW + 180)
by = {d["tx"]: d for d in w.state["donations"]}
check(by["0xeth"]["fiat"] == {"eur": 30.0, "usd": 35.0, "cny": 250.0, "jpy": 5000.0} and by["0xeth"]["fiat_at"] == "now",
      "fresh ETH donation valued at the current price")
check(by["0xold"]["fiat"]["eur"] == 2.0 and by["0xold"]["fiat_at"] == "day", "old donation valued at that day's price")
n = len(calls)
w.add_fiat(NOW + 240)
check(len(calls) == n, "a value is looked up only once")
s = dn.summary(w.state["donations"])
check(s["totals_fiat"]["eur"] == 30.0 + 2.0 + 5.0 and s["items"][0]["fiat"]["jpy"] == 5000.0, "public file carries values and their sum")
dn.get_json = lambda url: (_ for _ in ()).throw(OSError("down"))
w.state["donations"].append({"key": "x", "tx": "0xx", "from": DONOR, "asset": "AGRS", "amount": "1", "ts": NOW, "block": 2})
for _ in range(7):
    w.add_fiat(NOW + 300)
check(w.state["donations"][-1].get("fiat_tries") == dn.FIAT_TRIES, "price service down: tried a few times, then left alone")
check("totals_fiat" not in dn.summary(w.state["donations"]), "no sum while one donation has no value")

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

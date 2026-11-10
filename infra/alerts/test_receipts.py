"""Unit test of the receipts reader (no network): the amount and day come out of each kind of receipt, other mails are
not touched, a payment added by hand and its receipt count once, a payment taken off stays off, the public list holds
nothing but tool, amount, currency and day.

Run: python test_receipts.py
"""
import json
import os
import sys
import tempfile
from email.message import EmailMessage

TMP = tempfile.mkdtemp()
os.environ.update(COSTS_STATE_PATH=os.path.join(TMP, "state.json"), PUBLIC_DIR=TMP, COSTS_IMAP_USER="", COSTS_IMAP_PASSWORD="")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import receipts as R  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


def mail(frm, subject, body, when="Sun, 08 Nov 2026 02:23:16 +0000", mid="<a1@x>", html=False):
    m = EmailMessage()
    m["From"], m["Subject"], m["Date"], m["Message-ID"] = frm, subject, when, mid
    m.set_content(body, subtype="html" if html else "plain")
    return m.as_bytes()


google = mail("Google Payments <payments-noreply@google.com>",
              "Google Cloud Platform & APIs: We've received your payment for 00AA00-000000-000000",
              "Google Cloud Platform & APIs\n\nPayment received\n\nYour payment of €10.00 (reference CLOUD abc on Mastercard  • • • • 0000)\n"
              "was applied to Google Cloud Platform & APIs on 7 Nov 2026.\n\nGoogle Cloud Platform customer ID: 00AA00\n")
p = R.receipt(google)
check(p and p["key"] == "gemini" and p["amount"] == 10.0 and p["cur"] == "EUR", "Google AI Studio prepay: €10")
check(p and p["on"] == "2026-11-08", "the day is the mail's day in UTC")

eleven = mail("Eleven Labs Inc. <invoice+statements+acct_x@stripe.com>", "Your receipt from Eleven Labs Inc. #2716-0000-0000",
              "Receipt from Eleven Labs Inc. $13.09 Paid on October 31, 2026 with - 0000 Receipt #2716 Creator Qty 1 $22.00 "
              "Subtotal $22.00 VAT - Germany (19%) $2.09 (€1.87) Total $13.09 Amount paid $13.09 Charged €12.20",
              when="Sat, 31 Oct 2026 03:44:12 +0000", mid="<a2@x>")
p = R.receipt(eleven)
check(p and p["key"] == "elevenlabs" and p["amount"] == 13.09 and p["cur"] == "USD", "ElevenLabs Stripe receipt: $13.09 as billed")

xdev = mail("X Developer Platform <invoice+statements+acct_y@stripe.com>", "Your receipt from X Developer Platform #2519-4055",
            "<p>Receipt from X Developer Platform</p><p>US$5.00</p><p>Paid on October 29, 2026</p><td>Amount paid</td><td>$5.00</td>",
            html=True, mid="<a3@x>")
p = R.receipt(xdev)
check(p and p["key"] == "x" and p["amount"] == 5.0, "X API receipt (HTML only): $5")

kling = mail("billing@klingai.com", "Kling AI payment receipt", "Thank you. Total: 9,90 €", mid="<a4@x>")
p = R.receipt(kling)
check(p and p["key"] == "kling" and p["amount"] == 9.9 and p["cur"] == "EUR", "a Kling receipt, comma decimals: €9.90")

check(R.receipt(mail("PayPal <service@paypal.de>", "Beleg für Ihre Zahlung an Google", "Sie haben 2,99 € EUR an Google gezahlt")) is None,
      "a private payment to Google through PayPal is not a tool receipt")
check(R.receipt(mail("someone@stripe.com", "Your receipt from Some Shop", "Amount paid $40.00")) is None,
      "another shop's Stripe receipt is not read")
check(R.rule_for("payments-noreply@google.com", "Your Google Play order receipt") is None, "a Google Play receipt is not read")
check(R.number("1.234,56") == 1234.56 and R.number("1,234.56") == 1234.56 and R.number("10") == 10, "number formats")

# by hand first, then the receipt: one payment, the receipt's
s = R.load()
h = R.add_by_hand(s, "gemini", 10, None, "2026-11-08")
check(h["cur"] == "EUR" and h["via"] == "by hand", "up cost gemini 10: euros by default")
check(R.merge(s, R.receipt(google)) and len(s["items"]) == 1 and s["items"][0]["via"] == "receipt", "its receipt replaces it")
check(not R.merge(s, R.receipt(google)), "a receipt read twice counts once")
check(R.add_by_hand(s, "google", 10, "eur", "2026-11-07")["via"] == "receipt" and len(s["items"]) == 1,
      "by hand after the receipt: nothing added twice")
R.merge(s, R.receipt(eleven))
gone = R.receipt(eleven)["id"]
s["items"] = [i for i in s["items"] if i["id"] != gone]
s["dropped"].append(gone)
check(not R.merge(s, R.receipt(eleven)), "a payment taken off is not read in again")
try:
    R.add_by_hand(s, "netflix", 10)
    check(False, "an unknown tool is refused")
except ValueError:
    check(True, "an unknown tool is refused")

R.save(s)
pub = json.load(open(os.path.join(TMP, "costs-paid.json")))
keys = set().union(*(i.keys() for i in pub["items"]))
check(keys == {"id", "t", "d", "tool", "amount", "cur", "on", "via"}, "the public list holds tool, amount, currency, day only")
text = json.dumps(pub)
check("0000" not in text and "CLOUD" not in text and "@" not in text, "no card digits, reference or address in public")
check(any("paid so far" in line and "€10" in line for line in R.lines(s)), "up shows the total: " + R.lines(s)[1].strip())
check("OFF" in R.lines(s)[0], "without a mailbox set up, up says how to set it up")

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)

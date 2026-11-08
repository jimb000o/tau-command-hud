"""What the site's tools were paid, read from their receipts by mail, for tauhud.com/donate/.

Every top-up or bill of the tools the site runs on sends a receipt by mail (Google AI Studio credits for the
paintings, ElevenLabs for the voices, Kling for the clips, the X API for the bot, the Anthropic API for the writing).
This service reads the mailbox they go to every 30 minutes, READ-ONLY (IMAP EXAMINE, BODY.PEEK: nothing is marked read,
moved or deleted), looks only at mails whose sender and subject match a rule below, and keeps one line per payment:
the tool, the amount and currency as billed, the day. Nothing else of a mail is kept or shown: no card digits, no
customer number, no address, no name. The public list is /public/costs-paid.json (Caddy serves it at
https://node.tauhud.com/costs-paid.json); the donation page shows it beside assets/costs.json.

The mailbox: COSTS_IMAP_USER and COSTS_IMAP_PASSWORD in infra/.env (for Gmail an app password,
https://myaccount.google.com/apppasswords; `up cost mail` asks for both and writes them). Without them nothing is
read, and payments can still be added by hand.

  python receipts.py loop                      the service (reads the mail every COSTS_POLL_SECONDS, default 1800)
  python receipts.py check                     one read now, prints what it found
  python receipts.py add gemini 10 [EUR] [YYYY-MM-DD]   a payment by hand (a receipt read later replaces it)
  python receipts.py drop <id>                 takes one off the list (a wrong one); it is never read in again
  python receipts.py line                      the `costs:` lines for `up`
"""
from __future__ import annotations

import email
import email.header
import email.utils
import hashlib
import html
import imaplib
import json
import logging
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone

log = logging.getLogger("tau-costs")

STATE_PATH = os.environ.get("COSTS_STATE_PATH", "/state/costs-paid.json")
PUBLIC_PATH = os.path.join(os.environ.get("PUBLIC_DIR", "/public"), "costs-paid.json")
IMAP_HOST = os.environ.get("COSTS_IMAP_HOST", "imap.gmail.com").strip()
IMAP_USER = os.environ.get("COSTS_IMAP_USER", "").strip()
IMAP_PASSWORD = os.environ.get("COSTS_IMAP_PASSWORD", "").replace(" ", "").strip()
POLL = float(os.environ.get("COSTS_POLL_SECONDS", 1800))
# receipts older than this are not read in on the first run (the site's tools were all bought after it)
SINCE = os.environ.get("COSTS_SINCE", "2026-10-25").strip()
MATCH_DAYS = 3   # a payment added by hand and a receipt with the same tool and amount this close are the same payment

# The tools, as the donation page names them. cur: the currency a payment by hand gets when none is given.
TOOLS = {
    "gemini": {"t": "Image credits", "d": "Google AI Studio credits for the drawings on the site", "cur": "EUR"},
    "elevenlabs": {"t": "Voices", "d": "ElevenLabs, for the voices on the site", "cur": "USD"},
    "kling": {"t": "Video clips", "d": "Kling API credits for the island and ship clips", "cur": "USD"},
    "x": {"t": "X account", "d": "X API, for the bot that posts on X", "cur": "USD"},
    "anthropic": {"t": "AI writing", "d": "Anthropic API, for the blog drafts and the daily IDNI news", "cur": "USD"},
    "hetzner": {"t": "Server", "d": "Hetzner, the server at node.tauhud.com", "cur": "EUR"},
    "domains": {"t": "Domains", "d": "tauhud.com and agorzilla.com", "cur": "USD"},
}
ALIASES = {"google": "gemini", "aistudio": "gemini", "eleven": "elevenlabs", "11labs": "elevenlabs", "twitter": "x",
           "claude": "anthropic", "server": "hetzner", "domain": "domains", "namecheap": "domains"}

# Which mails are receipts of which tool: the sender's address and the subject must both match. Only these are opened.
# gemini: Google Payments, "Google Cloud Platform & APIs: We've received your payment for …" (the AI Studio prepay);
# the others are Stripe receipts, "Your receipt from <company> #…". Kling's sender is not known yet: any receipt
# or invoice mail whose subject names Kling.
RULES = [
    ("gemini", r"payments-noreply@google\.com", r"Google Cloud Platform & APIs: .*received your payment"),
    ("elevenlabs", r"@stripe\.com|elevenlabs", r"receipt from Eleven ?Labs"),
    ("x", r"@stripe\.com", r"receipt from X Developer Platform"),
    ("anthropic", r"@stripe\.com|anthropic", r"receipt from Anthropic"),
    ("kling", r".", r"kling.*(receipt|invoice|payment|order)|(receipt|invoice|payment|order).*kling"),
]

SYMBOL = {"€": "EUR", "$": "USD", "£": "GBP", "US$": "USD"}
MONEY = re.compile(r"(?P<sym>US\$|[€$£])\s?(?P<a>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|\d+(?:[.,]\d{2})?)"
                   r"|(?P<b>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|\d+(?:[.,]\d{2})?)\s?(?P<sym2>€|EUR|USD|\$)")


def number(s: str) -> float:
    """1,234.56 / 1.234,56 / 10,00 / 10.00 → float."""
    if re.search(r"[.,]\d{2}$", s):
        whole, cents = s[:-3], s[-2:]
        return float(re.sub(r"[.,]", "", whole) + "." + cents)
    return float(re.sub(r"[.,]", "", s))


def money(text: str) -> tuple[float, str] | None:
    m = MONEY.search(text)
    if not m:
        return None
    if m.group("sym"):
        return number(m.group("a")), SYMBOL[m.group("sym")]
    sym = m.group("sym2")
    return number(m.group("b")), SYMBOL.get(sym, sym)


def amount_of(key: str, body: str) -> tuple[float, str] | None:
    """The amount paid, as billed, from the receipt's text."""
    flat = re.sub(r"\s+", " ", body)
    if key == "gemini":
        m = re.search(r"Your payment of (.{1,20}?) \(", flat) or re.search(r"payment of (.{1,20}?) (?:was|has)", flat)
        return money(m.group(1)) if m else money(flat)
    # Stripe: "Receipt from Eleven Labs Inc. $13.09 Paid on October 31, 2026", later "Amount paid $13.09"
    for pat in (r"Amount paid (\S{1,16})", r"Receipt from [^$€£]{1,60}?((?:US)?[$€£]\s?[\d.,]+) Paid", r"Total (\S{1,16})"):
        m = re.search(pat, flat)
        if m and money(m.group(1)):
            return money(m.group(1))
    return money(flat)


def text_of(msg: email.message.Message) -> str:
    """The receipt's text: the plain part, else the HTML part with its tags taken out."""
    plain, rich = [], []
    for part in msg.walk():
        if part.get_content_maintype() != "text" or part.get("Content-Disposition", "").startswith("attachment"):
            continue
        try:
            s = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
        except Exception:
            continue
        (plain if part.get_content_subtype() == "plain" else rich).append(s)
    if plain:
        return "\n".join(plain)
    s = re.sub(r"(?is)<(style|script)[^>]*>.*?</\1>", " ", "\n".join(rich))
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def header(msg: email.message.Message, name: str) -> str:
    return str(email.header.make_header(email.header.decode_header(msg.get(name, "") or "")))


def rule_for(sender: str, subject: str) -> str | None:
    for key, frm, subj in RULES:
        if re.search(frm, sender, re.I) and re.search(subj, subject, re.I):
            return key
    return None


def receipt(raw: bytes) -> dict | None:
    """One mail → one payment {id, key, amount, cur, on, via: "receipt"}, or None when it is not a receipt of a tool."""
    msg = email.message_from_bytes(raw)
    key = rule_for(header(msg, "From"), header(msg, "Subject"))
    if not key:
        return None
    paid = amount_of(key, text_of(msg))
    if not paid or paid[0] <= 0:
        log.warning("a %s receipt without an amount found (%s)", key, header(msg, "Subject")[:60])
        return None
    try:
        on = email.utils.parsedate_to_datetime(msg.get("Date")).astimezone(timezone.utc).date().isoformat()
    except Exception:
        on = date.today().isoformat()
    mid = (msg.get("Message-ID") or header(msg, "Subject") + on).strip()
    return {"id": hashlib.sha1(mid.encode()).hexdigest()[:10], "key": key, "amount": round(paid[0], 2), "cur": paid[1],
            "on": on, "via": "receipt"}


# ---------------- the list ----------------
def load() -> dict:
    try:
        with open(STATE_PATH) as f:
            s = json.load(f)
    except Exception:
        s = {}
    s.setdefault("items", [])
    s.setdefault("dropped", [])
    return s


def write_atomic(path: str, text: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def save(s: dict):
    s["items"].sort(key=lambda i: (i["on"], i["id"]), reverse=True)
    write_atomic(STATE_PATH, json.dumps(s, indent=1))
    pub = [{"id": i["id"], "t": TOOLS[i["key"]]["t"], "d": TOOLS[i["key"]]["d"], "tool": i["key"], "amount": i["amount"],
            "cur": i["cur"], "on": i["on"], "via": i["via"]} for i in s["items"] if i["key"] in TOOLS]
    write_atomic(PUBLIC_PATH, json.dumps({
        "about": "What the site's tools were paid, as billed, read from their receipts (via: receipt) or added by hand. "
                 "Single payments, newest first; the monthly bills are in tauhud.com/assets/costs.json.",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "items": pub}, indent=1))


def near(a: str, b: str) -> bool:
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days) <= MATCH_DAYS


def merge(s: dict, p: dict) -> bool:
    """Adds a payment read from a receipt; True when the list changed. A receipt read before or taken off stays as it
    is; one added by hand with the same tool and amount a few days around is the same payment, the receipt replaces it."""
    if p["id"] in s["dropped"] or any(i["id"] == p["id"] for i in s["items"]):
        return False
    for i in s["items"]:
        if i["via"] == "by hand" and i["key"] == p["key"] and i["cur"] == p["cur"] and abs(i["amount"] - p["amount"]) < 0.01 \
                and near(i["on"], p["on"]):
            s["items"].remove(i)
            break
    s["items"].append(p)
    return True


def add_by_hand(s: dict, key: str, amount: float, cur: str | None = None, on: str | None = None) -> dict:
    key = ALIASES.get(key.lower(), key.lower())
    if key not in TOOLS:
        raise ValueError("unknown tool %r, one of: %s" % (key, ", ".join(TOOLS)))
    cur = (cur or TOOLS[key]["cur"]).upper()
    on = on or date.today().isoformat()
    date.fromisoformat(on)
    if not re.fullmatch(r"[A-Z]{3}", cur) or not 0 < amount < 100000:
        raise ValueError("amount or currency look wrong: %s %s" % (amount, cur))
    # a receipt for it may already be in: then nothing is added twice
    for i in s["items"]:
        if i["key"] == key and i["cur"] == cur and abs(i["amount"] - amount) < 0.01 and near(i["on"], on):
            return i
    p = {"id": "h" + hashlib.sha1(f"{key}{amount}{cur}{on}{time.time()}".encode()).hexdigest()[:9], "key": key,
         "amount": round(amount, 2), "cur": cur, "on": on, "via": "by hand"}
    s["items"].append(p)
    return p


# ---------------- the mailbox ----------------
def all_mail(box: imaplib.IMAP4_SSL) -> str:
    """Gmail's "All Mail" whatever its language (the \\All folder), so archived receipts count too; else the inbox."""
    typ, rows = box.list()
    for r in rows or []:
        line = r.decode("utf-8", "replace") if isinstance(r, bytes) else str(r)
        if "\\All" in line:
            m = re.search(r'"([^"]+)"\s*$', line) or re.search(r"(\S+)\s*$", line)
            if m:
                return '"%s"' % m.group(1)
    return "INBOX"


def read_mail(since: date) -> list[dict]:
    """Every receipt of a tool since that day, read-only."""
    box = imaplib.IMAP4_SSL(IMAP_HOST, timeout=60)
    try:
        box.login(IMAP_USER, IMAP_PASSWORD)
        box.select(all_mail(box), readonly=True)
        typ, data = box.search(None, "SINCE", since.strftime("%d-%b-%Y"))
        ids = (data[0] or b"").split()
        found = []
        for n in range(0, len(ids), 200):   # the senders and subjects first, in batches; only matching mails are opened
            chunk = b",".join(ids[n:n + 200])
            typ, rows = box.fetch(chunk, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
            for r in rows or []:
                if not isinstance(r, tuple):
                    continue
                h = email.message_from_bytes(r[1])
                if rule_for(header(h, "From"), header(h, "Subject")):
                    found.append(r[0].split()[0])
        out = []
        for num in found:
            typ, rows = box.fetch(num, "(BODY.PEEK[])")
            raw = next((r[1] for r in rows or [] if isinstance(r, tuple)), None)
            p = receipt(raw) if raw else None
            if p:
                out.append(p)
        return out
    finally:
        try:
            box.logout()
        except Exception:
            pass


def check(s: dict) -> list[dict]:
    """One read of the mailbox; returns the payments new to the list."""
    if not (IMAP_USER and IMAP_PASSWORD):
        s["mail"] = {"on": False}
        return []
    last = s.get("mail", {}).get("ok_since")
    since = date.fromisoformat(SINCE) if not last else date.fromisoformat(last) - timedelta(days=3)
    try:
        got = read_mail(since)
    except Exception as e:   # a wrong password or Gmail away: said in `up cost`, tried again next time
        s["mail"] = {**s.get("mail", {}), "on": True, "error": str(e)[:160], "at": int(time.time())}
        log.warning("mail not read: %s", e)
        return []
    new = [p for p in got if merge(s, p)]
    s["mail"] = {"on": True, "at": int(time.time()), "ok_since": date.today().isoformat(), "seen": len(got)}
    return new


# ---------------- what `up` shows ----------------
def fmt(amount: float, cur: str) -> str:
    sym = {"EUR": "€", "USD": "$", "GBP": "£"}.get(cur)
    n = f"{amount:.2f}".rstrip("0").rstrip(".") if amount % 1 else f"{amount:g}"
    return f"{sym}{n}" if sym else f"{n} {cur}"


def lines(s: dict) -> list[str]:
    m = s.get("mail") or {}
    if not m.get("on"):
        head = "receipts by mail OFF (set up once: up cost mail); by hand: up cost gemini 10"
    elif m.get("error"):
        head = "receipts by mail: NOT READ, " + m["error"][:90] + " (up cost mail to set the password again)"
    else:
        ago = int((time.time() - m.get("at", 0)) / 60)
        head = f"receipts by mail on, read {ago} min ago"
    out = ["costs:   " + head]
    items = s["items"]
    if items:
        tot: dict[str, float] = {}
        for i in items:
            tot[i["cur"]] = round(tot.get(i["cur"], 0) + i["amount"], 2)
        out.append("         paid so far (tauhud.com/donate/): " + " + ".join(fmt(v, c) for c, v in tot.items())
                   + f" in {len(items)} payment" + ("s" if len(items) != 1 else ""))
        for i in items[:4]:
            out.append(f"         {i['on']}  {TOOLS.get(i['key'], {}).get('t', i['key'])} {fmt(i['amount'], i['cur'])}"
                       f"  ({i['via']}, id {i['id']})")
    else:
        out.append("         no payment listed yet")
    return out


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cmd = argv[1] if len(argv) > 1 else "loop"
    s = load()
    if cmd == "add":
        try:
            amount = number(argv[3].replace("€", "").replace("$", ""))
            p = add_by_hand(s, argv[2], amount, *(a for a in argv[4:6]))
        except (IndexError, ValueError) as e:
            print("usage: up cost gemini 10 [EUR] [2026-11-08]   tools: " + ", ".join(TOOLS) + (f"\n{e}" if str(e) else ""))
            return 2
        save(s)
        print(f"added: {p['on']} {TOOLS[p['key']]['t']} {fmt(p['amount'], p['cur'])} ({p['via']}, id {p['id']})")
        return 0
    if cmd == "drop":
        ids = argv[2:]
        before = len(s["items"])
        s["items"] = [i for i in s["items"] if i["id"] not in ids]
        s["dropped"] = sorted(set(s["dropped"]) | set(ids))
        save(s)
        print(f"taken off: {before - len(s['items'])}")
        return 0
    if cmd == "check":
        new = check(s)
        save(s)
        for p in new:
            print(f"new: {p['on']} {TOOLS[p['key']]['t']} {fmt(p['amount'], p['cur'])}")
        print("\n".join(lines(s)))
        return 0
    if cmd == "line":
        print("\n".join(lines(s)))
        return 0
    if cmd == "loop":
        while True:
            s = load()
            for p in check(s):
                log.info("paid: %s %s %s", p["on"], p["key"], fmt(p["amount"], p["cur"]))
            save(s)
            time.sleep(POLL)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))

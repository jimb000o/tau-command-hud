"""Donation thank-yous for Tau HUD.

Watches the donation address shown in the HUD's About section on Ethereum
mainnet and keeps /public/donations.json (served by Caddy at
https://node.tauhud.com/donations.json, read by the About section). Every new
donation gets one plain thank-you post in the Telegram channel (and on X once
its keys are set), naming the sender only by their shortened address.

Counted: AGRS (the ERC-20 contract below, nothing else, so spam tokens and
look-alike "AGRS" tokens are ignored) and plain ETH, sent TO the address by
someone else, above a small minimum so dust and address-poisoning transfers
stay out.

Data comes from the public Blockscout API of Ethereum mainnet (no key). With
ETHERSCAN_API_KEY in .env it reads Etherscan instead.

No spam: a donation is posted once (its tx hash is remembered in the state
volume); on the very first run, what is found is history and only donations
younger than DONATION_POST_MAX_AGE_SECONDS (default 3 days) are thanked.

  python donations.py              run the watcher
  python donations.py --preview    print what was found and the post the newest would get, post nothing
"""
from __future__ import annotations

import html
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from alerts import SITE, Telegram, X, write_atomic, x_post

log = logging.getLogger("tau-donations")

ADDRESS = os.environ.get("DONATION_ADDRESS", "0x23fB76A33A8d70f5c51aB558b85e4b93040003eb").strip()
AGRS_CONTRACT = os.environ.get("AGRS_CONTRACT", "0x738865301a9b7dd80dc3666dd48cf034ec42bdda").strip().lower()
MIN = {"AGRS": Decimal(os.environ.get("DONATION_MIN_AGRS", "1")), "ETH": Decimal(os.environ.get("DONATION_MIN_ETH", "0.0005"))}
IGNORE_FROM = {a.strip().lower() for a in os.environ.get("DONATION_IGNORE_FROM", "").split(",") if a.strip()}
POLL = float(os.environ.get("DONATION_POLL_SECONDS", 300))
POST_MAX_AGE = float(os.environ.get("DONATION_POST_MAX_AGE_SECONDS", 3 * 86400))
STATE_PATH = os.environ.get("DONATION_STATE_PATH", "/state/donations.json")
PUBLIC_PATH = os.path.join(os.environ.get("PUBLIC_DIR", "/public"), "donations.json")
BLOCKSCOUT = os.environ.get("BLOCKSCOUT_API", "https://eth.blockscout.com/api/v2").rstrip("/")
ETHERSCAN_KEY = os.environ.get("ETHERSCAN_API_KEY", "").strip()
TX_URL = "https://etherscan.io/tx/"
# value of each donation in money, read once when it comes in (CoinGecko, no key needed; COINGECKO_API_KEY for the demo plan):
# the price at that moment if it is found within an hour, else the price of that day. Shown on tauhud.com/donate/ in the
# reader's currency: euros and dollars in English, yuan in Chinese, yen in Japanese.
COINGECKO = os.environ.get("COINGECKO_API", "https://api.coingecko.com/api/v3").rstrip("/")
COINGECKO_KEY = os.environ.get("COINGECKO_API_KEY", "").strip()
FIAT = ("eur", "usd", "cny", "jpy")
COIN_ID = {"ETH": "ethereum", "AGRS": os.environ.get("AGRS_COINGECKO_ID", "").strip()}
FIAT_TRIES = 5
UA = {"User-Agent": "tauhud-donations/1 (+https://tauhud.com)", "Accept": "application/json"}


def short(a: str) -> str:
    return a[:6] + "…" + a[-4:] if a and len(a) > 12 else a


def fmt_amount(v: Decimal) -> str:
    step = Decimal("1") if v >= 100 else Decimal("0.01") if v >= 1 else Decimal("0.0001")
    q = v.quantize(step, rounding=ROUND_HALF_UP)
    s = f"{q:,f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def get_json(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _addr(v) -> str:
    if isinstance(v, dict):
        v = v.get("hash") or v.get("address_hash") or v.get("address")
    return (v or "").lower()


def _ts(v) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) or str(v).isdigit():
        return float(v)
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def blockscout_pages(path: str, pages: int = 5) -> list[dict]:
    out, params = [], None
    for _ in range(pages):
        url = f"{BLOCKSCOUT}{path}" + ("&" + urllib.parse.urlencode(params) if params else "")
        d = get_json(url)
        out += d.get("items") or []
        params = d.get("next_page_params")
        if not params:
            break
        time.sleep(0.5)
    return out


def fetch_blockscout() -> list[dict]:
    me, found = ADDRESS.lower(), []
    for it in blockscout_pages(f"/addresses/{ADDRESS}/token-transfers?type=ERC-20"):
        tok = it.get("token") or {}
        total = it.get("total") or {}
        try:
            v = Decimal(str(total.get("value") or "0")).scaleb(-int(total.get("decimals") or tok.get("decimals") or 18))
        except (ArithmeticError, ValueError):
            continue
        found.append({"tx": it.get("transaction_hash") or it.get("tx_hash") or "", "from": _addr(it.get("from")),
                      "to": _addr(it.get("to")), "contract": _addr(tok.get("address_hash") or tok.get("address")),
                      "asset": "AGRS", "amount": v, "ts": _ts(it.get("timestamp")),
                      "block": it.get("block_number") or it.get("block"), "ok": True,
                      "log": it.get("log_index"), "symbol": tok.get("symbol") or "?"})
    for it in blockscout_pages(f"/addresses/{ADDRESS}/transactions?filter=to"):
        try:
            v = Decimal(str(it.get("value") or "0")).scaleb(-18)
        except ArithmeticError:
            continue
        found.append({"tx": it.get("hash") or "", "from": _addr(it.get("from")), "to": _addr(it.get("to")),
                      "contract": "", "asset": "ETH", "amount": v, "ts": _ts(it.get("timestamp")),
                      "block": it.get("block_number") or it.get("block"), "ok": it.get("status") in (None, "ok"),
                      "log": None, "symbol": "ETH"})
    return [f for f in found if f["to"] == me]


def fetch_etherscan() -> list[dict]:
    base = "https://api.etherscan.io/v2/api?chainid=1&module=account&sort=desc&page=1&offset=200&apikey=" + ETHERSCAN_KEY
    me, found = ADDRESS.lower(), []
    for it in get_json(f"{base}&action=tokentx&address={ADDRESS}").get("result") or []:
        if not isinstance(it, dict):
            continue
        found.append({"tx": it.get("hash", ""), "from": _addr(it.get("from")), "to": _addr(it.get("to")),
                      "contract": _addr(it.get("contractAddress")), "asset": "AGRS",
                      "amount": Decimal(it.get("value") or "0").scaleb(-int(it.get("tokenDecimal") or 18)),
                      "ts": _ts(it.get("timeStamp")), "block": int(it.get("blockNumber") or 0), "ok": True,
                      "log": it.get("logIndex"), "symbol": it.get("tokenSymbol") or "?"})
    for it in get_json(f"{base}&action=txlist&address={ADDRESS}").get("result") or []:
        if not isinstance(it, dict):
            continue
        found.append({"tx": it.get("hash", ""), "from": _addr(it.get("from")), "to": _addr(it.get("to")),
                      "contract": "", "asset": "ETH", "amount": Decimal(it.get("value") or "0").scaleb(-18),
                      "ts": _ts(it.get("timeStamp")), "block": int(it.get("blockNumber") or 0),
                      "ok": it.get("isError") == "0", "log": None, "symbol": "ETH"})
    return [f for f in found if f["to"] == me]


def coin_id(asset: str) -> str:
    if not COIN_ID.get(asset) and asset == "AGRS":
        COIN_ID["AGRS"] = get_json(f"{COINGECKO}/coins/ethereum/contract/{AGRS_CONTRACT}" + _cg_key("?")).get("id") or ""
    return COIN_ID.get(asset) or ""


def _cg_key(sep: str) -> str:
    return f"{sep}x_cg_demo_api_key={urllib.parse.quote(COINGECKO_KEY)}" if COINGECKO_KEY else ""


def price_of(asset: str, ts: float, now: float | None = None) -> tuple[dict, str] | None:
    """Price of one coin in each currency of FIAT, and how it was taken: "now" (within the hour) or "day"."""
    cid = coin_id(asset)
    if not cid:
        return None
    now = now or time.time()
    if now - ts < 3600:
        got, how = get_json(f"{COINGECKO}/simple/price?ids={cid}&vs_currencies={','.join(FIAT)}" + _cg_key("&")).get(cid) or {}, "now"
    else:
        day = datetime.fromtimestamp(ts, timezone.utc).strftime("%d-%m-%Y")
        got = ((get_json(f"{COINGECKO}/coins/{cid}/history?date={day}&localization=false" + _cg_key("&"))
                .get("market_data") or {}).get("current_price") or {})
        how = "day"
    if not all(isinstance(got.get(c), (int, float)) and got[c] > 0 for c in FIAT):
        return None
    return {c: Decimal(str(got[c])) for c in FIAT}, how


def fiat_value(amount: Decimal, price: dict) -> dict:
    return {c: float((amount * price[c]).quantize(Decimal("1") if c == "jpy" else Decimal("0.01"), rounding=ROUND_HALF_UP))
            for c in FIAT}


def why_not(f: dict) -> str | None:
    """None when this transfer counts as a donation, else the reason it does not."""
    if not f["tx"] or not f["ok"]:
        return "failed"
    if f["asset"] == "AGRS" and f["contract"] != AGRS_CONTRACT:
        return f"other token {f['symbol']} ({f['contract']})"
    if f["from"] == ADDRESS.lower() or f["from"] in IGNORE_FROM:
        return "own wallet"
    if f["amount"] < MIN[f["asset"]]:
        return f"below minimum ({fmt_amount(f['amount'])} {f['asset']})"
    return None


def key_of(f: dict) -> str:
    return f"{f['tx']}:{f['log'] if f['log'] is not None else f['asset']}"


def summary(donations: list[dict]) -> dict:
    """The public file: newest first, totals per asset, number of different senders."""
    totals: dict[str, Decimal] = {}
    for d in donations:
        totals[d["asset"]] = totals.get(d["asset"], Decimal(0)) + Decimal(d["amount"])
    out = {"address": ADDRESS, "updated": int(time.time()), "donors": len({d["from"] for d in donations}),
           "count": len(donations), "totals": {k: fmt_amount(v) for k, v in totals.items()},
           "items": [dict({"tx": d["tx"], "from": d["from"], "asset": d["asset"], "amount": d["amount"],
                           "ts": d["ts"], "block": d["block"]}, **({"fiat": d["fiat"], "fiat_at": d.get("fiat_at", "day")}
                                                                if d.get("fiat") else {})) for d in donations[:50]]}
    if donations and all(d.get("fiat") for d in donations):   # a sum only when every donation has its value
        out["totals_fiat"] = {c: round(sum(d["fiat"][c] for d in donations), 0 if c == "jpy" else 2) for c in FIAT}
    return out


def thanks_text(d: dict, donors: int, nth: int) -> str:
    """One plain thank-you; no dashes, the sender only as a shortened address."""
    amt = f"{fmt_amount(Decimal(d['amount']))} {d['asset']}"
    first = ", the first donation to Tau HUD" if nth == 1 else " for Tau HUD"
    who = ("1 person has" if donors == 1 else f"{donors} people have")
    return (f"💚 <b>Thank you, {html.escape(short(d['from']))}</b>\n\n"
            f"{amt} just came in{first}. A voluntary gift, nothing is owed in return.\n\n"
            f"{who} donated so far. <a href=\"{TX_URL}{d['tx']}\">Transaction</a> · "
            f"<a href=\"{SITE}/#donate\">About</a>")


def thanks_x(d: dict, donors: int) -> str:
    amt = f"{fmt_amount(Decimal(d['amount']))} {d['asset']}"
    who = "1 person has" if donors == 1 else f"{donors} people have"
    return x_post([f"💚 Thank you, {short(d['from'])}: {amt} just came in for Tau HUD.",
                   f"A voluntary gift, nothing is owed in return. {who} donated so far."],
                  f"{SITE}/#donate")


class Donations:
    def __init__(self, outlets=None):
        self.outlets = outlets if outlets is not None else [Telegram(), X()]
        try:
            with open(STATE_PATH) as f:
                self.state = json.load(f)
        except (OSError, ValueError):
            self.state = {}
        self.state.setdefault("primed", False)
        self.state.setdefault("donations", [])  # newest first, amounts as strings
        self.state.setdefault("posted", {})      # key -> {outlet: "ok" | tries}

    def save(self):
        try:
            os.makedirs(os.path.dirname(STATE_PATH) or ".", exist_ok=True)
            write_atomic(STATE_PATH, json.dumps(self.state, separators=(",", ":")))
        except OSError as exc:
            log.warning("cannot write %s: %r", STATE_PATH, exc)

    def fetch(self) -> list[dict]:
        return fetch_etherscan() if ETHERSCAN_KEY else fetch_blockscout()

    def update(self, found: list[dict], now: float | None = None) -> list[dict]:
        """Merge what the chain shows; return the donations that are news (to be thanked)."""
        now = now or time.time()
        known = {d["key"] for d in self.state["donations"]}
        news = []
        for f in found:
            if why_not(f) or key_of(f) in known:
                continue
            d = {"key": key_of(f), "tx": f["tx"], "from": f["from"], "asset": f["asset"], "amount": str(f["amount"]),
                 "ts": f["ts"] or now, "block": f["block"]}
            known.add(d["key"])
            self.state["donations"].append(d)
            if self.state["primed"] or now - d["ts"] <= POST_MAX_AGE:
                news.append(d)
        self.state["donations"].sort(key=lambda d: (d["ts"] or 0, d["block"] or 0), reverse=True)
        self.state["primed"] = True
        news.sort(key=lambda d: d["ts"])
        return news

    def add_fiat(self, now: float | None = None):
        """Give each donation its value in money once; a failed lookup is tried again on the next rounds, at most FIAT_TRIES times."""
        for d in self.state["donations"]:
            if d.get("fiat") or d.get("fiat_tries", 0) >= FIAT_TRIES:
                continue
            try:
                got = price_of(d["asset"], d["ts"], now)
            except (urllib.error.URLError, OSError, ValueError) as exc:
                log.info("no price for %s yet (%r)", d["key"][:14], exc)
                got = None
            if got:
                d["fiat"], d["fiat_at"] = fiat_value(Decimal(d["amount"]), got[0]), got[1]
            else:
                d["fiat_tries"] = d.get("fiat_tries", 0) + 1
            time.sleep(1.5)   # the free price service allows a few calls a minute

    def write_public(self):
        try:
            os.makedirs(os.path.dirname(PUBLIC_PATH) or ".", exist_ok=True)
            write_atomic(PUBLIC_PATH, json.dumps(summary(self.state["donations"]), separators=(",", ":")))
        except OSError as exc:
            log.warning("cannot write %s: %r", PUBLIC_PATH, exc)

    def thank(self, news: list[dict]):
        order = sorted(self.state["donations"], key=lambda d: (d["ts"] or 0, d["block"] or 0))
        for d in news:
            nth = order.index(d) + 1
            donors = len({x["from"] for x in order[:nth]})
            posted = self.state["posted"].setdefault(d["key"], {})
            for o in self.outlets:
                got = posted.get(o.name)
                if not o.enabled() or got == "ok" or (isinstance(got, int) and got >= 3):
                    continue
                text = thanks_text(d, donors, nth) if o.name == "telegram" else thanks_x(d, donors)
                ok, _, err = o.send_text(text)
                posted[o.name] = "ok" if ok else (got if isinstance(got, int) else 0) + 1
                log.info("thanked %s on %s", short(d["from"]), o.name) if ok else \
                    log.warning("thank-you to %s failed (%s)", o.name, err)
            self.save()

    def pending(self) -> list[dict]:
        """Donations whose thank-you failed earlier and may be tried again."""
        return [d for d in self.state["donations"] if any(isinstance(v, int) and v < 3 for v in self.state["posted"].get(d["key"], {}).values())]

    def step(self):
        news = self.update(self.fetch())
        self.add_fiat()
        self.write_public()
        self.save()
        self.thank(news + [d for d in self.pending() if d not in news])

    def run(self):
        log.info("watching %s for AGRS (%s) and ETH donations every %d s via %s", ADDRESS, AGRS_CONTRACT, POLL,
                 "etherscan" if ETHERSCAN_KEY else "blockscout")
        while True:
            try:
                self.step()
            except (urllib.error.URLError, OSError, ValueError) as exc:
                log.warning("cannot read donations (%r); trying again later", exc)
            time.sleep(POLL)


def preview() -> int:
    found = Donations([]).fetch()
    if not found:
        print(f"No incoming transfers to {ADDRESS} found.")
    for f in sorted(found, key=lambda f: f["ts"] or 0):
        when = datetime.fromtimestamp(f["ts"] or 0, timezone.utc).strftime("%Y-%m-%d %H:%M")
        print(f"{when}  {short(f['from'])}  {fmt_amount(f['amount'])} {f['symbol']:<6}  "
              f"{why_not(f) or 'DONATION'}  {f['tx'][:14]}…")
    w = Donations([])
    w.state = {"primed": True, "donations": [], "posted": {}}
    news = w.update(found)
    if news:
        d = news[-1]
        print("-" * 60 + "\nThe newest donation would be thanked like this:\n")
        print(thanks_text(d, len({x["from"] for x in news}), len(news)))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if "--preview" in sys.argv:
        sys.exit(preview())
    Donations().run()

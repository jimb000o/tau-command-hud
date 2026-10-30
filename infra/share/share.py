"""Share previews: per-page pictures and link cards for X, Telegram and WhatsApp.

tauhud.com is static (GitHub Pages), so every page has the same og:image and
the crawlers of X and Telegram never run the page's JavaScript. This service
fills the gap on node.tauhud.com:

  GET /og/hud.png                    the live overview (height, rules, votes)
  GET /og/block/<n>.png              one block: transactions, who sealed it
  GET /og/proposal/<id>.png          one rule change: what it does, votes, countdown
  GET /og/address/<96 hex>.png       one account: balance, activity
  GET /og/card/<96 hex>.png?c=<0-4>  "My Tau card": one wallet's rules, votes,
                                     Agorzilla meals and café stamps (the stamps
                                     live in the visitor's browser, so the link
                                     carries them as c)
  GET /og/card/<96 hex>.json         the same numbers, for the card page
  GET /s/  /s/block/<n>  /s/proposal/<id>  /s/address/<hex>  /s/card/<hex>
                                     a tiny page with og:/twitter: tags for that
                                     picture that sends people on to the real page

It reads the chain from the relay like any visitor (getblockrange, cached
lookups) and proposals from the alerts watcher's proposals.json. It holds no
keys and writes nothing.
"""
from __future__ import annotations

import html
import json
import logging
import os
import re
import threading
import time
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from websockets.sync.client import connect

import cards

log = logging.getLogger("share")

RELAY_URL = os.environ.get("RELAY_URL", "ws://relay:8080")
RELAY_HTTP = os.environ.get("RELAY_HTTP", "http://relay:8080")
PROPOSALS_PATH = os.environ.get("PROPOSALS_PATH", "/public/proposals.json")
SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
PUBLIC = os.environ.get("PUBLIC_URL", "https://node.tauhud.com").rstrip("/")
PORT = int(os.environ.get("PORT", "8070"))
POLL = float(os.environ.get("POLL_SECONDS", "10"))
RANGE = 100
CACHE_MAX = 400

ADDR = re.compile(r"^[0-9a-f]{96}$")
PROP = re.compile(r"^[0-9a-f]{8,64}$")
ROUTE = re.compile(r"^/(og|s)(?:/(block|proposal|address|card)/([0-9a-z]+?))?(?:\.png)?/?$")
CARD_JSON = re.compile(r"^/og/card/([0-9a-f]{96})\.json$")

TRANSFERISH = {"user_tx", "retractable_transfer", "approval_request"}

# Agorzilla (agorzilla.com, its assets/core.js): a meal is a transaction that pays the bowl at least 1 test AGRS,
# and counts once an hour per wallet; paying ballot box k in the same transaction votes for option k that evening.
# Nobody holds a key for these addresses.
BOWL = "947c2b8988769f9fb7ada19021e27c51f5d855e4e05ad258d2ca2322821987dbff93e0425f281edded5c372b97e6a108"
BOXES = ("931c4e3b949dd5a77c226e2409f617aa9603f15075f20902c849855f24fb5439113afa3869fc415a3786fe5f30321392",
         "92cfce4449523a48ab02f88d5acfa85b74860c87eaf501c48320c99a8a142191ba022199c3b20474ff19f7b72f4563a4",
         "afbdeb43eb62d4a95f2f679686488a14a033cbddb45dec0ac7181d40a668f4af3c8b1c9df05b3b2bc33e664a2a8dd98b")
AGZ_BORN, MEAL_COOLDOWN = 1793296800, 3600   # 29 Oct 2026 18:00 UTC


def low(v) -> str:
    return str(v or "").strip().lower()


def num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def height(b: dict) -> int:
    return int(num((b.get("header") or {}).get("block_number")))


def ts_of(b: dict | None) -> float | None:
    return num(((b or {}).get("header") or {}).get("timestamp")) or None


def kind_of(t: dict) -> str:
    if (t.get("tx_type") or "user_tx") == "user_tx" and (t.get("operations") or {}).get("0"):
        return "rule_deploy"
    return t.get("tx_type") or "user_tx"


def transfers(t: dict) -> list:
    ops = (t.get("operations") or {}).get("1")
    return [x for x in ops if isinstance(x, list) and len(x) >= 3] if isinstance(ops, list) else []


def amount(t: dict) -> float | None:
    tr = transfers(t)
    if tr:
        return sum(num(x[2]) for x in tr)
    return num(t["amount"]) if t.get("amount") is not None else None


# ---------------- the chain, as the relay serves it ----------------
class Chain:
    def __init__(self):
        self.blocks: dict[int, dict] = {}
        self.head = -1
        self.gov: dict = {}
        self.ws = None
        self.lock = threading.Lock()   # one request at a time on the relay socket
        self.ready = False
        self.lookups: dict[str, tuple[float, dict | None]] = {}

    def _request(self, cmd: str, timeout: float = 15) -> dict | None:
        """Send one command and wait for its answer; pushed frames in between are skipped."""
        with self.lock:
            try:
                if self.ws is None:
                    self.ws = connect(RELAY_URL, open_timeout=10, max_size=64 * 2**20)
                    self.ws.send("hello version=1")
                self.ws.send(cmd)
                name = cmd.split()[0]
                end = time.monotonic() + timeout
                while time.monotonic() < end:
                    raw = self.ws.recv(timeout=max(0.1, end - time.monotonic()))
                    try:
                        msg = json.loads(raw)
                    except (TypeError, ValueError):
                        continue
                    if isinstance(msg, dict) and msg.get("command") == name:
                        return msg
            except Exception as e:  # noqa: BLE001 - any socket trouble: reconnect next time
                log.warning("relay: %s (%s)", e, cmd.split()[0])
                try:
                    self.ws and self.ws.close()
                except Exception:  # noqa: BLE001
                    pass
                self.ws = None
        return None

    def poll(self):
        start = max(0, self.head - 2)
        while True:
            msg = self._request(f"getblockrange {start} {RANGE}")
            if not msg or msg.get("status") != "ok":
                return
            d = msg.get("data") or {}
            got = d.get("blocks") or []
            relay_head = d.get("head")
            # the relay holds fewer blocks than we do, or an overlapping block changed: a new chain
            changed = any(height(b) in self.blocks and self.blocks[height(b)].get("block_hash") != b.get("block_hash") for b in got)
            if changed or (isinstance(relay_head, int) and relay_head < self.head):
                log.info("chain changed under us; reloading from block 0")
                self.blocks.clear()
                self.head = -1
                start = 0
                continue
            for b in got:
                self.blocks[height(b)] = b
                self.head = max(self.head, height(b))
            if not got or not isinstance(relay_head, int) or start + RANGE > relay_head:
                break
            start += RANGE
        g = self._request("getgovernance")
        if g and g.get("status") == "ok":
            self.gov = g.get("data") or {}
        self.ready = self.head >= 0

    def run(self):
        while True:
            try:
                self.poll()
            except Exception:  # noqa: BLE001
                log.exception("poll failed")
            time.sleep(POLL)

    def lookup(self, cmd: str) -> dict | None:
        hit = self.lookups.get(cmd)
        if hit and time.monotonic() - hit[0] < 30:
            return hit[1]
        msg = self._request(cmd, timeout=10)
        data = msg.get("data") if msg and msg.get("status") == "ok" else None
        if len(self.lookups) > 2000:
            self.lookups.clear()
        self.lookups[cmd] = (time.monotonic(), data)
        return data

    def validators(self) -> set[str]:
        return {low(v if isinstance(v, str) else (v or {}).get("pubkey")) for v in self.gov.get("active_validators") or []}

    def pace(self) -> float | None:
        pts = [(h, ts_of(self.blocks.get(h))) for h in range(max(1, self.head - 10), self.head + 1)]
        pts = [p for p in pts if p[1]]
        if len(pts) < 2 or pts[-1][0] == pts[0][0]:
            return None
        return max(1.0, (pts[-1][1] - pts[0][1]) / (pts[-1][0] - pts[0][0]))


CHAIN = Chain()


def proposals() -> dict:
    try:
        with open(PROPOSALS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def relay_status() -> dict:
    try:
        with urllib.request.urlopen(RELAY_HTTP + "/status", timeout=4) as r:
            return json.load(r)
    except Exception:  # noqa: BLE001
        return {}


def find_proposal(pid: str) -> tuple[dict | None, dict]:
    data = proposals()
    for p in data.get("proposals") or []:
        if low(p.get("id")).startswith(pid):
            return p, data
    return None, data


# ---------------- numbers for each card ----------------
def hud_numbers() -> dict:
    c = CHAIN
    data = proposals()
    st = relay_status()
    tip, h = st.get("tip_height"), st.get("canonical_height")
    synced = bool(st.get("upstream_connected")) and (tip is None or h is None or tip - h <= 2)
    props = data.get("proposals") or []
    txs = sum(len(b.get("transactions") or []) for b in c.blocks.values())
    return {"head": c.head, "synced": synced, "pace": c.pace(),
            "validators": (data.get("rules") or {}).get("validators") or len(c.validators()) or None,
            "rev": (data.get("rules") or {}).get("revision") or 0,
            "voting": sum(1 for p in props if p.get("status") == "voting"),
            "agreed": sum(1 for p in props if p.get("status") == "agreed"),
            "txs": txs, "last_txs": len((c.blocks.get(c.head) or {}).get("transactions") or [])}


def block_numbers(h: int) -> dict | None:
    b = CHAIN.blocks.get(h)
    if not b:
        return None
    rows = []
    for t in b.get("transactions") or []:
        if not isinstance(t, dict):
            continue
        k = kind_of(t)
        s = low(t.get("sender_pubkey") or t.get("sender"))
        tr = transfers(t)
        to = low(tr[0][1]) if len(tr) == 1 else low(t.get("recipient_pubkey"))
        tag = None
        if k == "consensus_rule_vote":
            line = f"{cards.short(s)} on a rule change"
            tag = "yes" if str(t.get("approve", True)).lower() != "false" else "no"
        elif k == "consensus_rule_update":
            line = f"by {cards.short(s)}"
        elif to:
            line = f"{cards.short(s)} → {cards.short(to)}"
        elif len(tr) > 1:
            line = f"{cards.short(s)} → {len(tr)} accounts"
        else:
            line = f"by {cards.short(s)}"
        rows.append({"kind": k, "line": line, "amt": amount(t) if k in TRANSFERISH or tr else None, "tag": tag})
    prop = low((b.get("header") or {}).get("proposer_pubkey"))
    prev = ts_of(CHAIN.blocks.get(h - 1))
    return {"h": h, "ts": ts_of(b), "gap": ts_of(b) - prev if prev and ts_of(b) else None, "proposer": prop,
            "validator": prop in CHAIN.validators(), "head": CHAIN.head, "txs": rows}


def address_numbers(a: str) -> dict:
    c = {"addr": a, "sent": 0, "received": 0, "in_sum": 0.0, "out_sum": 0.0, "last_h": None, "sealed": 0, "recent": []}
    for h in range(CHAIN.head, -1, -1):
        b = CHAIN.blocks.get(h) or {}
        if low((b.get("header") or {}).get("proposer_pubkey")) == a:
            c["sealed"] += 1
        for t in reversed(b.get("transactions") or []):
            if not isinstance(t, dict):
                continue
            s = low(t.get("sender_pubkey"))
            touched, d, amt, other = s == a, "out" if s == a else "", None, None
            if s == a:
                c["sent"] += 1
            for f, to, v in (x[:3] for x in transfers(t)):
                if low(f) == a:
                    c["out_sum"] += num(v)
                    amt, other, d, touched = (amt or 0) + num(v), low(to), "out", True
                if low(to) == a and low(f) != a:
                    c["received"] += 1
                    c["in_sum"] += num(v)
                    amt, other, d, touched = (amt or 0) + num(v), low(f), "in", True
            if not touched and low(t.get("recipient_pubkey")) == a:
                touched, d, other = True, "in", s
            if not touched:
                continue
            if c["last_h"] is None:
                c["last_h"] = h
            if len(c["recent"]) < 2:
                c["recent"].append({"h": h, "kind": kind_of(t), "dir": d, "amt": amt, "other": other})
    st = CHAIN.lookup(f"getaccountstate {a}")
    c["balance"] = num(st["chain_balance"]) if st and st.get("chain_balance") is not None else None
    c["validator"] = a in CHAIN.validators()
    return c


def card_numbers(a: str) -> dict:
    """What one wallet has done on this chain: rules written, votes, Agorzilla meals. No balance: nothing is priced."""
    c = {"addr": a, "own": 0, "offered": 0, "proposed": 0, "rule_votes": 0, "agz_votes": 0, "meals": 0,
         "first_h": None, "first_ts": None, "txs": 0, "head": CHAIN.head}
    last_meal = None
    for h in range(0, CHAIN.head + 1):
        b = CHAIN.blocks.get(h) or {}
        for t in b.get("transactions") or []:
            if not isinstance(t, dict) or low(t.get("sender_pubkey")) != a:
                continue
            c["txs"] += 1
            if c["first_h"] is None:
                c["first_h"], c["first_ts"] = h, ts_of(b)
            k = kind_of(t)
            if k == "rule_deploy":
                c["own"] += 1
            elif k == "rule_offer":
                c["offered"] += 1
            elif k == "consensus_rule_update":
                c["proposed"] += 1
            elif k == "consensus_rule_vote":
                c["rule_votes"] += 1
            fed, box = 0, 0
            for f, to, v in (x[:3] for x in transfers(t)):
                if low(f) != a or num(v) < 1:
                    continue
                if low(to) == BOWL:
                    fed += num(v)
                elif not box and low(to) in BOXES:
                    box = BOXES.index(low(to)) + 1
            ts = ts_of(b) or 0
            if fed >= 1 and ts >= AGZ_BORN:
                if last_meal is None or ts - last_meal >= MEAL_COOLDOWN:
                    c["meals"] += 1
                    last_meal = ts
                if box:
                    c["agz_votes"] += 1
    c["rules"] = c["own"] + c["offered"] + c["proposed"]
    c["votes"] = c["rule_votes"] + c["agz_votes"]
    return c


def stamps_of(query: str) -> int:
    """Café stamps from ?c=0..4 (they are kept in the visitor's browser, not on the chain)."""
    m = re.search(r"(?:^|&)c=([0-4])(?:&|$)", query or "")
    return int(m.group(1)) if m else 0


# ---------------- pictures, cached ----------------
_cache: dict[str, tuple[float, bytes]] = {}
_render = threading.Semaphore(2)


def picture(kind: str | None, arg: str | None, stamps: int = 0) -> tuple[bytes, int]:
    """PNG bytes and how long they may be cached (seconds)."""
    key = f"{kind}:{arg}:{stamps}:{CHAIN.head}"
    hit = _cache.get(key)
    if hit and hit[0] > time.monotonic():
        return hit[1], 60
    with _render:
        try:
            ttl = 60
            if not CHAIN.ready:
                img, ttl = cards.generic(), 30
            elif kind is None:
                img = cards.hud(hud_numbers())
            elif kind == "block":
                n = block_numbers(int(arg))
                img = cards.block(n) if n else cards.generic()
                ttl = 3600 if n and CHAIN.head - n["h"] > 10 else 60
            elif kind == "proposal":
                p, data = find_proposal(arg)
                img = cards.proposal(p, CHAIN.head, CHAIN.pace()) if p else cards.generic()
            elif kind == "card":
                img = cards.my_card(card_numbers(arg), stamps)
            else:
                img = cards.address(address_numbers(arg))
        except Exception:  # noqa: BLE001 - a broken card must still give the crawler a picture
            log.exception("render %s %s", kind, arg)
            img, ttl = cards.generic(), 30
    if len(_cache) > CACHE_MAX:
        _cache.clear()
    _cache[key] = (time.monotonic() + ttl, img)
    return img, ttl


# ---------------- link pages ----------------
def page(kind: str | None, arg: str | None, stamps: int = 0) -> str:
    if kind is None:
        target, title = SITE + "/", f"Tau HUD · live at block #{cards.fmt_n(CHAIN.head)}" if CHAIN.ready else "Tau HUD"
        desc = "Where the rules change by agreement. The Tau Testnet Alpha, live: blocks, rule changes, votes, validators."
        img = f"{PUBLIC}/og/hud.png?h={CHAIN.head}"
    elif kind == "block":
        n = block_numbers(int(arg))
        target, title = f"{SITE}/explorer/?b={int(arg)}", f"Block #{cards.fmt_n(int(arg))} · Tau HUD"
        desc = (f"{cards.plural(len(n['txs']), 'transaction')}, sealed {cards.when(n['ts'])}" + (f" by {cards.short(n['proposer'])}." if arg != "0" else ".")
                if n else "A block of the Tau Testnet Alpha.")
        img = f"{PUBLIC}/og/block/{int(arg)}.png"
    elif kind == "proposal":
        p, _ = find_proposal(arg)
        target = f"{SITE}/proposals/#{arg[:16]}"
        title = f"{p['title']} · Tau HUD" if p else "Rule change · Tau HUD"
        desc = proposal_line(p) if p else "A proposed rule change on the Tau Testnet Alpha."
        img = f"{PUBLIC}/og/proposal/{arg}.png?h={CHAIN.head}"
    elif kind == "card":
        n = card_numbers(arg)
        q = f"?a={arg}" + (f"&c={stamps}" if stamps else "")
        target, title = f"{SITE}/card/{q}", f"{cards.words(arg)} · My Tau card"
        desc = cards.card_line(n) + " Test AGRS only, nothing priced or promised."
        img = f"{PUBLIC}/og/card/{arg}.png?c={stamps}&h={CHAIN.head}"
    else:
        target, title = f"{SITE}/explorer/?a={arg}", f"Address {cards.short(arg)} · Tau HUD"
        desc = "Balance, transactions and rules of an account on the Tau Testnet Alpha."
        img = f"{PUBLIC}/og/address/{arg}.png?h={CHAIN.head}"
    e = lambda s: html.escape(str(s), quote=True)  # noqa: E731
    url = PUBLIC + "/s/" + (f"{kind}/{arg}" if kind else "") + (f"?c={stamps}" if kind == "card" and stamps else "")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="noindex">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Tau HUD">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(img)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{e(img)}">
<meta http-equiv="refresh" content="0; url={e(target)}">
</head><body style="background:#09090a;color:#ebebee;font-family:system-ui,sans-serif">
<p><a style="color:#39ff8a" href="{e(target)}">{e(title)}</a></p>
<script>location.replace({json.dumps(target)})</script>
</body></html>"""


def proposal_line(p: dict) -> str:
    v, need, s = p.get("counted_votes") or 0, p.get("thr") or 1, p.get("status")
    if s == "active":
        return f"In force since block #{cards.fmt_n(p.get('activated_at'))}, agreed by vote."
    if s == "dropped":
        return f"Dropped at block #{cards.fmt_n(p.get('expired_at'))}: {v} of {need} votes by the deadline."
    left = max(0, (p.get("activate_at") or 0) - CHAIN.head)
    pace = CHAIN.pace()
    eta = f", about {cards.dur(left * pace)}" if pace and left else ""
    if s == "agreed":
        return f"Agreed with {v} of {need} votes. Takes effect in {cards.plural(left, 'block')}{eta}."
    return f"Waiting for votes: {v} of {need}. Deadline in {cards.plural(left, 'block')}{eta}."


def parse(path: str):
    """(og|s, kind, arg) for a valid path, else None."""
    path = path.lower()
    if path == "/og/hud.png":
        return "og", None, None
    m = ROUTE.match(path)
    if not m:
        return None
    what, kind, arg = m.groups()
    if what == "og" and (kind is None or not path.endswith(".png")):
        return None
    if kind == "block" and not (arg.isdigit() and len(arg) <= 9):
        return None
    if kind == "proposal" and not PROP.match(arg):
        return None
    if kind in ("address", "card") and not ADDR.match(arg):
        return None
    return what, kind, arg


class Handler(BaseHTTPRequestHandler):
    server_version = "tau-hud-share"

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/og/health":
            return self.send(HTTPStatus.OK, b"ok\n" if CHAIN.ready else b"waiting for the relay\n", "text/plain", 0)
        j = CARD_JSON.match(path.lower())
        if j:
            if not CHAIN.ready:
                return self.send(HTTPStatus.SERVICE_UNAVAILABLE, b'{"error":"reading the chain"}', "application/json", 0)
            return self.send(HTTPStatus.OK, json.dumps(card_numbers(j.group(1))).encode(), "application/json", 20)
        r = parse(path)
        if not r:
            return self.send(HTTPStatus.NOT_FOUND, b"not found\n", "text/plain", 300)
        what, kind, arg = r
        if what == "og":
            body, ttl = picture(kind, arg, stamps_of(query))
            return self.send(HTTPStatus.OK, body, "image/png", ttl)
        return self.send(HTTPStatus.OK, page(kind, arg, stamps_of(query)).encode(), "text/html; charset=utf-8", 60)

    do_HEAD = do_GET

    def send(self, code, body: bytes, ctype: str, ttl: int):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", f"public, max-age={ttl}" if ttl else "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        log.debug(fmt, *args)


def main():
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    threading.Thread(target=CHAIN.run, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    srv.daemon_threads = True
    log.info("share previews on :%s, relay %s", PORT, RELAY_URL)
    srv.serve_forever()


if __name__ == "__main__":
    main()

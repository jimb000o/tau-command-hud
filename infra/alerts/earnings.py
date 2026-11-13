"""What the Tau HUD shop and the crew bring in for the site: our share, not what buyers paid.

tauhud.com/donate/ draws what the site cost against what came in. Besides donations, money now comes from the shop at
Fourthwall (merchandise made to order) and from the crew (paid monthly memberships). Neither counts in full: Fourthwall
keeps the base cost of each product it makes and its fees, and the tax goes to the state. This module works out our
share from the shop's Open API and writes it, summed per day, to /public/earnings.json (Caddy serves it at
https://node.tauhud.com/earnings.json). No names, no e-mail addresses, no order numbers leave the server.

Fourthwall Open API (docs.fourthwall.com, read 13 November 2026), Basic auth with the shop's API user:
GET /open-api/v1.0/order?page&size  orders with amounts {subtotal, shipping, tax, donation, discount, total} (Money
{value, currency}) and per item offers[].variant {unitPrice, unitCost, price, cost} and quantity; status CANCELLED for a
cancelled order; source.type ORDER for a real sale (SAMPLES_ORDER, GIVEAWAY_LINKS, TWITCH_GIFT_REDEMPTION are not).
GET /open-api/v1.0/memberships/members?page&size  each member's subscription {type ACTIVE|CANCELLED|SUSPENDED|NONE,
variant {interval MONTHLY|ANNUAL, amount}} and createdAt.
The API has no profit field, no payout list and no membership payment history, so:
- a shop order's share = items sold (subtotal) - member discount - Fourthwall's cost for the items + a tip if any
  - a card fee on what the buyer paid; shipping and tax pass through Fourthwall and are not ours;
- a membership's share = its price - Fourthwall's membership fee - a card fee, once per billing period while it is
  active. The server notes each period the moment it sees it (state in /state/earnings.json), so a member who cancels
  keeps the periods already paid and adds no new one.
The fees are Fourthwall's published rates as we read them (13 November 2026); the card fee is the higher foreign-card
rate, so the figure leans low rather than high. Each can be set in .env if Fourthwall's own statement says otherwise.
Each new order and each new member is told to the owner in the private Telegram chat (up owner), without a name.
`up earnings` prints every order's numbers next to the share worked out, to compare with the shop's dashboard.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

import crewlog

STATE_PATH = os.environ.get("EARNINGS_STATE_PATH", "/state/earnings.json")
PUBLIC_PATH = os.path.join(os.environ.get("PUBLIC_DIR", "/public"), "earnings.json")
API0 = os.environ.get("FOURTHWALL_API_V10", "https://api.fourthwall.com/open-api/v1.0")
CARD_PCT = float(os.environ.get("EARNINGS_CARD_PCT", "3.9"))      # % of what the buyer paid
CARD_FIX = float(os.environ.get("EARNINGS_CARD_FIXED", "0.30"))   # per payment, in the order's currency
CREW_PCT = float(os.environ.get("EARNINGS_CREW_PCT", "5"))         # Fourthwall's fee on memberships
SHOP_PCT = float(os.environ.get("EARNINGS_SHOP_PCT", "0"))         # Fourthwall's own cut of product sales, on top of the base cost
EVERY = int(os.environ.get("EARNINGS_EVERY_SECONDS", 900))   # also how soon the owner hears of a new order or member
REAL = {"ORDER"}


def _get(path: str):
    return crewlog._req("GET", path, base=API0)


def pages(path: str, limit: int = 50) -> list[dict]:
    out = []
    for page in range(limit):
        d = _get(f"{path}{'&' if '?' in path else '?'}page={page}&size=100") or {}
        rows = d.get("results") or []
        out += [r for r in rows if isinstance(r, dict)]
        if not rows or page + 1 >= int(d.get("totalPages") or 0):
            break
    return out


def _v(m) -> float:
    try:
        return float((m or {}).get("value") or 0)
    except (TypeError, ValueError, AttributeError):
        return 0.0


def _cur(*ms) -> str:
    for m in ms:
        if isinstance(m, dict) and m.get("currency"):
            return str(m["currency"]).upper()
    return "USD"


def _day(s: str) -> str:
    return str(s or "")[:10]


def item_cost(o: dict) -> float:
    """Fourthwall's cost for the items of an order: unitCost x quantity where the item has one, else its cost."""
    c = 0.0
    for it in o.get("offers") or []:
        v, q = it.get("variant") or {}, it.get("quantity") or 1
        try:
            q = int(q)
        except (TypeError, ValueError):
            q = 1
        c += _v(v.get("unitCost")) * q if v.get("unitCost") else _v(v.get("cost"))
    return c


def order_share(o: dict) -> dict | None:
    """Our share of one order, or None when it is not a sale (cancelled, a sample, a giveaway)."""
    if str(o.get("status", "")).upper() == "CANCELLED" or str((o.get("source") or {}).get("type", "ORDER")).upper() not in REAL:
        return None
    a = o.get("amounts") or {}
    sub, disc, tip, total = _v(a.get("subtotal")), abs(_v(a.get("discount"))), _v(a.get("donation")), _v(a.get("total"))
    cost = item_cost(o)
    fee = round(total * CARD_PCT / 100 + CARD_FIX, 2) if total > 0 else 0.0
    cut = round((sub - disc) * SHOP_PCT / 100, 2)
    share = round(sub - disc - cost - cut + tip - fee, 2)
    return {"on": _day(o.get("createdAt")), "cur": _cur(a.get("total"), a.get("subtotal")), "share": share,
            "subtotal": sub, "discount": disc, "cost": round(cost, 2), "tip": tip, "fee": fee, "cut": cut, "total": total}


def periods(created: str, interval: str, until: float) -> list[str]:
    """The days a membership was billed: its start, then every month (or year) on the same day, up to `until`."""
    try:
        t0 = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
    except ValueError:
        return []
    step = 12 if str(interval).upper() == "ANNUAL" else 1
    out = []
    for k in range(0, 600, step):
        y, m = t0.year + (t0.month - 1 + k) // 12, (t0.month - 1 + k) % 12 + 1
        last = (datetime(y + (m == 12), m % 12 + 1, 1, tzinfo=timezone.utc) - datetime(y, m, 1, tzinfo=timezone.utc)).days
        t = t0.replace(year=y, month=m, day=min(t0.day, last))
        if t.timestamp() > until:
            break
        out.append(t.strftime("%Y-%m-%d"))
    return out


def crew_share(amount: float) -> float:
    return round(amount - amount * CREW_PCT / 100 - (amount * CARD_PCT / 100 + CARD_FIX), 2)


def load() -> dict:
    try:
        with open(STATE_PATH) as f:
            s = json.load(f)
        return s if isinstance(s, dict) else {}
    except (OSError, ValueError):
        return {}


def write_atomic(path: str, text: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def note_members(s: dict, members: list[dict], now: float) -> int:
    """Adds each active member's billing days up to now to the state (kept by an id that stays on the server); returns
    how many new ones were added."""
    paid = s.setdefault("crew", {})
    n = 0
    for m in members:
        sub = m.get("subscription") or {}
        if str(sub.get("type", "")).upper() != "ACTIVE":
            continue
        v = sub.get("variant") or {}
        amount = _v(v.get("amount"))
        if amount <= 0 or m.get("id") is None:
            continue
        rec = paid.setdefault(str(m["id"]), {})
        for d in periods(m.get("createdAt", ""), v.get("interval", "MONTHLY"), now):
            if d not in rec:
                rec[d] = {"share": crew_share(amount), "cur": _cur(v.get("amount"))}
                n += 1
    return n


def public(shop: list[dict], s: dict, now: float) -> dict:
    """Summed per day and kind (shop, crew) in each currency; nothing that names a buyer or a member."""
    days = {}
    for o in shop:
        k = (o["on"], "shop", o["cur"])
        days[k] = days.get(k, 0) + o["share"]
    for rec in (s.get("crew") or {}).values():
        for d, p in rec.items():
            k = (d, "crew", p.get("cur", "USD"))
            days[k] = days.get(k, 0) + float(p.get("share") or 0)
    items = [{"on": d, "kind": kind, "amount": round(v, 2), "cur": c} for (d, kind, c), v in sorted(days.items()) if abs(v) >= 0.005]
    return {"updated": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "how": "Our share after Fourthwall's costs and fees, estimated from the shop's API; tax and shipping not counted.",
            "items": items}


def _items(o: dict) -> str:
    out = []
    for it in o.get("offers") or []:
        name = str(it.get("name") or (it.get("variant") or {}).get("name") or "an item")[:60]
        q = it.get("quantity") or 1
        out.append(f"{name} ×{q}" if str(q) != "1" else name)
    return ", ".join(out) or "an order"


def news(s: dict, orders: list[dict], members: list[dict], tier_names: dict | None = None) -> list[str]:
    """One line for the owner per order and per member not seen before (no buyer, no e-mail: what was bought, the price,
    our share). The first read only learns what is there, so nothing old is announced."""
    seen_o, seen_m = set(s.get("orders_seen") or []), set(s.get("members_seen") or [])
    out = []
    for o in orders:
        oid = str(o.get("id") or "")
        if not oid or oid in seen_o:
            continue
        seen_o.add(oid)
        x = order_share(o)
        if x and s.get("primed"):
            out.append(f"🛒 New order in the Tau HUD shop: {_items(o)}. Paid {x['cur']} {x['total']:.2f} incl. tax and shipping, "
                       f"our share about {x['cur']} {x['share']:.2f}.")
    for m in members:
        mid, sub = str(m.get("id") or ""), m.get("subscription") or {}
        if not mid or mid in seen_m or str(sub.get("type", "")).upper() != "ACTIVE":
            continue
        seen_m.add(mid)
        if s.get("primed"):
            v = sub.get("variant") or {}
            tier = (tier_names or {}).get(v.get("tierId")) or (tier_names or {}).get(str(v.get("tierId"))) or "a tier"
            n = sum(1 for k in members if str((k.get("subscription") or {}).get("type", "")).upper() == "ACTIVE")
            out.append(f"⚓ New member in the Tau HUD crew: {tier}, {_cur(v.get('amount'))} {_v(v.get('amount')):.2f} a "
                       f"{'year' if str(v.get('interval')).upper() == 'ANNUAL' else 'month'} before tax, our share about "
                       f"{crew_share(_v(v.get('amount'))):.2f}. Active members now: {n}.")
    s["orders_seen"], s["members_seen"], s["primed"] = sorted(seen_o), sorted(seen_m), True
    return out


def run(now: float | None = None, tier_names: dict | None = None) -> tuple[dict, list[dict], int, list[str]]:
    """One read of the shop: (public file, the orders with their numbers, new membership periods, lines for the owner);
    writes both files."""
    now = now or time.time()
    s = load()
    orders, members = pages("/order"), pages("/memberships/members")
    shop = [x for x in (order_share(o) for o in orders) if x]
    added = note_members(s, members, now)
    lines = news(s, orders, members, tier_names)
    s["checked"] = now
    write_atomic(STATE_PATH, json.dumps(s, separators=(",", ":")))
    pub = public(shop, s, now)
    write_atomic(PUBLIC_PATH, json.dumps(pub, separators=(",", ":")))
    return pub, shop, added, lines


def due(s: dict | None = None, now: float | None = None) -> bool:
    s = load() if s is None else s
    return (now or time.time()) - float(s.get("checked") or 0) >= EVERY

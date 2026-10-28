"""Weekly recap: one image of the Tau testnet's week, in the Tau HUD look.

build() turns the relay's /stats and /community and the watcher's own event
log into the numbers for one week; render() draws them as a 1200×675 PNG
(16:9, the size Telegram and X show uncropped); caption() is the text that
goes with it. alerts.py decides when to post.
"""
from __future__ import annotations

import io
import os
import time
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw, ImageFont

WEEK = 7 * 86400
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

# Same tokens as the pages: black and white, phosphor green as the one accent.
VOID, DECK, LINE, HAIR = (9, 9, 10), (18, 18, 20), (38, 38, 42), (60, 60, 66)
WHITE, TEXT, DIM, OK = (255, 255, 255), (235, 235, 238), (138, 138, 148), (57, 255, 138)


def fmt_n(n) -> str:
    return f"{int(round(n)):,}"


def short(h: str) -> str:
    h = str(h or "")
    return h[:6] + "…" + h[-4:] if len(h) > 14 else (h or "—")


def pace_txt(s: float | None) -> str:
    if not s:
        return "—"
    return f"{s:.0f} s" if s < 120 else f"{s / 60:.1f} min"


# ---------------- the numbers ----------------
def build(stats: dict, community: dict | None, items: list[dict], end: float | None = None) -> dict:
    """Numbers for the 7 days that end at `end` (default: now)."""
    end = end or time.time()
    start = end - WEEK
    f = {k: i for i, k in enumerate(stats.get("fields") or [])}
    rows = [r for r in stats.get("blocks") or [] if r[f["timestamp"]] and start <= r[f["timestamp"]] < end]
    accounts = stats.get("accounts") or []

    # blocks per UTC day, oldest first
    day0 = datetime.fromtimestamp(start, timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    days = [day0 + timedelta(days=i) for i in range(8)]
    days = [d for d in days if d.timestamp() < end][-7:]
    per_day = [0] * len(days)
    for r in rows:
        t = r[f["timestamp"]]
        for i in range(len(days) - 1, -1, -1):
            if t >= days[i].timestamp():
                per_day[i] += 1
                break

    ts = sorted(r[f["timestamp"]] for r in rows)
    gaps = [b - a for a, b in zip(ts, ts[1:]) if b > a]
    pace = sum(gaps) / len(gaps) if gaps else None

    txs = sum(r[f["txs"]] for r in rows)
    transfers = sum(r[f["transfers"]] for r in rows)
    volume = sum(r[f["volume"]] for r in rows)
    by_sender: dict[int, int] = {}
    for r in rows:
        for s in r[f["senders"]]:
            by_sender[s] = by_sender.get(s, 0) + 1
    top = sorted(by_sender.items(), key=lambda kv: (-kv[1], kv[0]))[:3]

    # blocks of chains that ended this week (the relay only holds the current chain)
    restarts = [x for x in stats.get("restarts") or [] if start <= (x.get("detected_at") or 0) < end]
    old_blocks = 0
    for x in restarts:
        o = x.get("old") or {}
        b1, tip_ts, tip = o.get("block1_ts"), o.get("tip_ts"), o.get("tip") or 0
        if b1 and tip_ts and tip_ts > b1:
            overlap = max(0, min(tip_ts, end) - max(b1, start))
            old_blocks += round(tip * overlap / (tip_ts - b1))

    ev = [it for it in items if start <= (it.get("ts") or it.get("seen") or 0) < end]
    count = lambda k: sum(1 for it in ev if it["kind"] == k)  # noqa: E731
    active_titles = [it["headline"].split(": ", 1)[-1] for it in ev if it["kind"] == "active"]

    nodes = (community or {}).get("nodes") or []
    new_nodes = [n for n in nodes if (n.get("first_seen") or 0) >= start]

    return {
        "start": start, "end": end, "head": stats.get("head"),
        "blocks": len(rows), "old_blocks": old_blocks, "pace": pace, "txs": txs, "transfers": transfers, "volume": volume,
        "accounts": len(by_sender), "top": [(accounts[i] if i < len(accounts) else "?", n) for i, n in top],
        "per_day": per_day, "days": [d.strftime("%a") for d in days],
        "proposed": count("proposed"), "agreed": count("agreed"), "active": count("active"), "dropped": count("dropped"),
        "active_titles": active_titles,
        "restarts": max(len(restarts), count("restart")),
        "nodes": len(nodes), "new_nodes": len(new_nodes),
    }


def period(r: dict) -> str:
    a = datetime.fromtimestamp(r["start"], timezone.utc)
    b = datetime.fromtimestamp(r["end"] - 1, timezone.utc)
    if a.month == b.month:
        return f"{a.day}–{b.day} {b.strftime('%b %Y')}"
    return f"{a.day} {a.strftime('%b')} – {b.day} {b.strftime('%b %Y')}"


def week_key(ts: float) -> str:
    y, w, _ = datetime.fromtimestamp(ts, timezone.utc).isocalendar()
    return f"{y}-W{w:02d}"


# ---------------- the words ----------------
def lines(r: dict, site: str) -> list[str]:
    blocks = fmt_n(r["blocks"] + r["old_blocks"])
    out = [f"{'≈' if r['old_blocks'] else ''}{blocks} blocks, one every {pace_txt(r['pace'])}",
           f"{fmt_n(r['txs'])} transactions from {fmt_n(r['accounts'])} accounts"]
    rules = [f"{r[k]} {w}" for k, w in (("proposed", "proposed"), ("agreed", "agreed"), ("active", "in force"), ("dropped", "dropped")) if r[k]]
    out.append("Rule changes: " + (", ".join(rules) if rules else "none this week"))
    if r["restarts"]:
        out.append(f"Chain restarts: {r['restarts']}")
    if r["nodes"]:
        out.append(f"Community nodes: {r['nodes']}" + (f" ({r['new_nodes']} new)" if r["new_nodes"] else ""))
    return out


# first line of every post about the real chain; the simulation's posts start with their own line instead
REAL_LINE = "⛓ <b>TESTNET ALPHA · live chain</b>"


def caption_html(r: dict, site: str) -> str:
    import html
    body = "\n".join("• " + html.escape(x) for x in lines(r, site))
    return (f"{REAL_LINE}\n📊 <b>Tau testnet weekly recap</b> · {html.escape(period(r))}\n{body}\n\n"
            f"<a href=\"{site}/stats/\">Stats</a> · <a href=\"{site}/proposals/\">Rule changes</a> · <a href=\"{site}/history/\">Time travel</a>")


def caption_x(r: dict, site: str) -> str:
    ls = lines(r, site)
    text = f"📊 Tau testnet weekly recap · {period(r)}\n" + "\n".join(ls[:3])
    return text[:250] + f"\n\n{site}/stats/ #Tau"


# ---------------- the picture ----------------
def _font(name: str, size: int, weight: int):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    try:
        f.set_variation_by_axes([weight])
    except (OSError, AttributeError):
        pass
    return f


# Sora has no arrows or ≈; those few characters come from JetBrains Mono.
FALLBACK = set("→←≈…✓")


def _runs(text: str, font):
    if not str(getattr(font, "path", "")).endswith("Sora.ttf"):
        return [(text, font)]
    mono = _font("JetBrainsMono.ttf", int(font.size), 500)
    runs: list[tuple[str, object]] = []
    for ch in text:
        f = mono if ch in FALLBACK else font
        if runs and runs[-1][1] is f:
            runs[-1] = (runs[-1][0] + ch, f)
        else:
            runs.append((ch, f))
    return runs


def _len(d: ImageDraw.ImageDraw, text: str, font) -> float:
    return sum(d.textlength(t, font=f) for t, f in _runs(text, font))


def _text(d: ImageDraw.ImageDraw, xy, text: str, font, fill):
    x, y = xy
    for t, f in _runs(text, font):
        d.text((x, y), t, font=f, fill=fill)
        x += d.textlength(t, font=f)


def _fit(d: ImageDraw.ImageDraw, text: str, name: str, size: int, weight: int, width: int):
    """The font at `size` or smaller so that text fits in `width` (never cut a word)."""
    while size > 9:
        f = _font(name, size, weight)
        if _len(d, text, f) <= width:
            return f
        size -= 1
    return _font(name, size, weight)


def _mark(d: ImageDraw.ImageDraw, x: int, y: int, s: int):
    """The Pulse logo: a ring and a heartbeat line (64-unit viewBox as in favicon.svg)."""
    k = s / 64
    w = max(2, round(3.2 * k))
    d.ellipse([x + 7 * k, y + 7 * k, x + 57 * k, y + 57 * k], outline=WHITE, width=w)
    pts = [(13, 33), (23, 33), (27.5, 24), (34.5, 43), (39, 33), (51, 33)]
    d.line([(x + px * k, y + py * k) for px, py in pts], fill=OK, width=w, joint="curve")


def _panel(d, box, title=None, f_title=None, s=2):
    d.rounded_rectangle(box, radius=10 * s, fill=DECK, outline=LINE, width=s)
    if title:
        d.text((box[0] + 18 * s, box[1] + 14 * s), title.upper(), font=f_title, fill=DIM)


def render(r: dict, site: str = "https://tauhud.com") -> bytes:
    W, H, S = 1200, 675, 2          # drawn at 2× and scaled down: crisp text and lines
    img = Image.new("RGB", (W * S, H * S), VOID)
    d = ImageDraw.Draw(img)
    sc = lambda v: int(round(v * S))  # noqa: E731
    B = lambda x0, y0, x1, y1: [sc(x0), sc(y0), sc(x1), sc(y1)]  # noqa: E731

    # faint grid like the pages' background
    for gx in range(0, W, 96):
        d.line([sc(gx), 0, sc(gx), sc(H)], fill=(16, 16, 18), width=S)
    for gy in range(0, H, 96):
        d.line([0, sc(gy), sc(W), sc(gy)], fill=(16, 16, 18), width=S)

    f_h1 = _font("Sora.ttf", sc(26), 700)
    f_sub = _font("JetBrainsMono.ttf", sc(15), 400)
    f_lab = _font("Sora.ttf", sc(11.5), 600)
    f_big = _font("Sora.ttf", sc(40), 600)
    f_unit = _font("Sora.ttf", sc(15), 500)
    f_txt = _font("JetBrainsMono.ttf", sc(14), 400)
    f_txtb = _font("Sora.ttf", sc(15), 600)
    f_small = _font("JetBrainsMono.ttf", sc(12), 400)

    # header
    _mark(d, sc(40), sc(30), sc(46))
    d.text((sc(100), sc(30)), "Tau HUD", font=f_h1, fill=WHITE)
    d.text((sc(100), sc(62)), "Weekly recap of the Tau Testnet Alpha", font=f_sub, fill=DIM)
    per = period(r)
    f_per = _font("Sora.ttf", sc(22), 600)
    d.text((sc(W - 40) - d.textlength(per, font=f_per), sc(32)), per, font=f_per, fill=WHITE)
    tag = "tau-testnet-v2 · UTC"
    d.text((sc(W - 40) - d.textlength(tag, font=f_sub), sc(64)), tag, font=f_sub, fill=DIM)
    d.line(B(40, 100, W - 40, 100), fill=LINE, width=S)

    # four tiles
    blocks = r["blocks"] + r["old_blocks"]
    tiles = [("Blocks", ("≈" if r["old_blocks"] else "") + fmt_n(blocks), "",
              f"≈{fmt_n(r['old_blocks'])} of them before a restart" if r["old_blocks"] else (f"head #{fmt_n(r['head'])}" if r.get("head") else "")),
             ("Block time", pace_txt(r["pace"]).split(" ")[0], pace_txt(r["pace"]).split(" ")[-1] if r["pace"] else "", "average"),
             ("Transactions", fmt_n(r["txs"]), "", f"{fmt_n(r['transfers'])} transfers"),
             ("Active accounts", fmt_n(r["accounts"]), "", "sent at least one tx")]
    tw = (W - 80 - 3 * 16) / 4
    for i, (lab, val, unit, note) in enumerate(tiles):
        x0 = 40 + i * (tw + 16)
        _panel(d, B(x0, 118, x0 + tw, 232), lab, f_lab)
        _text(d, (sc(x0 + 18), sc(150)), val, f_big, WHITE)
        if unit:
            d.text((sc(x0 + 18) + _len(d, val, f_big) + sc(6), sc(172)), unit, font=f_unit, fill=DIM)
        d.text((sc(x0 + 18), sc(204)), note, font=f_small, fill=DIM)

    # blocks per day
    cx0, cy0, cx1, cy1 = 40, 250, 620, 470
    _panel(d, B(cx0, cy0, cx1, cy1), "Blocks per day", f_lab)
    pd = r["per_day"] or [0]
    top = max(pd) or 1
    n = len(pd)
    bw = (cx1 - cx0 - 36 - (n - 1) * 12) / n
    base = cy1 - 34
    # a steady chain gives seven near-equal bars: the average is written once, a bar is labelled only where it deviates
    days_with = [v for v in pd if v]
    avg = sum(days_with) / len(days_with) if days_with else 0
    if avg:
        note_avg = f"about {fmt_n(round(avg))} a day"
        d.text((sc(cx0 + 18) + d.textlength("Blocks per day".upper(), font=f_lab) + sc(14), sc(cy0 + 15)), note_avg, font=f_small, fill=DIM)
        ya = base - (base - (cy0 + 64)) * avg / top   # the average as a thin dashed line across the bars
        for xx in range(cx0 + 18, cx1 - 18, 8):
            d.line([sc(xx), sc(ya), sc(xx + 4), sc(ya)], fill=(120, 120, 128), width=sc(1))
    for i, v in enumerate(pd):
        x = cx0 + 18 + i * (bw + 12)
        h = (base - (cy0 + 64)) * v / top
        fill = OK if i == n - 1 else (200, 200, 205)
        if v:
            d.rounded_rectangle(B(x, base - max(h, 2), x + bw, base), radius=sc(3), fill=fill)
        off = (v - avg) / avg if avg else 0
        if not v or abs(off) >= 0.03 or i == n - 1:
            lbl = fmt_n(v) if not v or i == n - 1 else f"{'+' if off > 0 else '−'}{abs(off) * 100:.0f} %"
            inside = v and h > 40   # label inside the bar, clear of the average line
            d.text((sc(x + bw / 2) - d.textlength(lbl, font=f_small) / 2, sc(base - h + 8) if inside else sc(base - max(h, 2) - 18)), lbl, font=f_small, fill=(20, 20, 24) if inside else TEXT)
        day = r["days"][i] if i < len(r["days"]) else ""
        d.text((sc(x + bw / 2) - d.textlength(day, font=f_small) / 2, sc(base + 8)), day, font=f_small, fill=DIM)
    if r["old_blocks"]:
        note = "current chain only"
        d.text((sc(cx1 - 18) - d.textlength(note, font=f_small), sc(cy0 + 15)), note, font=f_small, fill=DIM)

    # rule changes
    rx0, rx1 = 636, W - 40
    _panel(d, B(rx0, cy0, rx1, cy1), "Rule changes by agreement", f_lab)
    cells = [("proposed", r["proposed"]), ("agreed", r["agreed"]), ("in force", r["active"]), ("dropped", r["dropped"])]
    cw = (rx1 - rx0 - 36) / 4
    for i, (lab, v) in enumerate(cells):
        x = rx0 + 18 + i * cw
        col = OK if lab in ("agreed", "in force") and v else (WHITE if v else DIM)
        d.text((sc(x), sc(cy0 + 40)), str(v), font=f_big, fill=col)
        d.text((sc(x), sc(cy0 + 92)), lab, font=f_txt, fill=DIM)
    y = cy0 + 128
    titles = r["active_titles"][:3]
    if titles:
        d.text((sc(rx0 + 18), sc(y)), "NOW IN FORCE", font=f_lab, fill=DIM)
        y += 22
        for t in titles:
            d.ellipse(B(rx0 + 18, y + 7, rx0 + 26, y + 15), fill=OK)
            _text(d, (sc(rx0 + 36), sc(y)), t, _fit(d, t, "Sora.ttf", sc(15), 600, sc(rx1 - rx0 - 54)), WHITE)
            y += 26
    else:
        msg = "No rule change took effect this week." if not r["proposed"] else "Nothing took effect yet; see the open votes."
        d.text((sc(rx0 + 18), sc(y + 4)), msg, font=_fit(d, msg, "JetBrainsMono.ttf", sc(14), 400, sc(rx1 - rx0 - 36)), fill=TEXT)

    # bottom row: restarts, community nodes, top accounts
    by0, by1 = 486, 604
    bw3 = (W - 80 - 2 * 16) / 3
    boxes = [B(40 + i * (bw3 + 16), by0, 40 + i * (bw3 + 16) + bw3, by1) for i in range(3)]
    _panel(d, boxes[0], "Chain restarts", f_lab)
    d.text((boxes[0][0] + sc(18), sc(by0 + 42)), str(r["restarts"]), font=f_big, fill=WHITE if r["restarts"] else DIM)
    d.text((boxes[0][0] + sc(18), sc(by0 + 92)), "testnet started a new chain" if r["restarts"] else "the chain ran without a restart",
           font=f_small, fill=DIM)
    _panel(d, boxes[1], "Community nodes", f_lab)
    d.text((boxes[1][0] + sc(18), sc(by0 + 42)), str(r["nodes"]), font=f_big, fill=WHITE if r["nodes"] else DIM)
    if r["new_nodes"]:
        nn = f"+{r['new_nodes']} new"
        d.text((boxes[1][0] + sc(18) + d.textlength(str(r["nodes"]), font=f_big) + sc(10), sc(by0 + 64)), nn, font=f_txtb, fill=OK)
    d.text((boxes[1][0] + sc(18), sc(by0 + 92)), "online now, run with the operator kit", font=f_small, fill=DIM)
    _panel(d, boxes[2], "Most active accounts", f_lab)
    if r["top"]:
        for i, (acc, c) in enumerate(r["top"]):
            yy = by0 + 44 + i * 21
            d.text((boxes[2][0] + sc(18), sc(yy)), f"{i + 1}  {short(acc)}", font=f_txt, fill=TEXT)
            ct = f"in {fmt_n(c)} blocks"
            d.text((boxes[2][2] - sc(18) - d.textlength(ct, font=f_small), sc(yy + 2)), ct, font=f_small, fill=DIM)
    else:
        d.text((boxes[2][0] + sc(18), sc(by0 + 44)), "no transactions this week", font=f_txt, fill=DIM)

    # footer
    d.line(B(40, 620, W - 40, 620), fill=LINE, width=S)
    host = site.split("//", 1)[-1]
    d.text((sc(40), sc(634)), host, font=_font("Sora.ttf", sc(16), 700), fill=WHITE)
    right = "Read from our own node · t.me/tauHUDcom"
    d.text((sc(W - 40) - d.textlength(right, font=f_small), sc(637)), right, font=f_small, fill=DIM)

    out = io.BytesIO()
    img.resize((W, H), Image.LANCZOS).save(out, "PNG", optimize=True)
    return out.getvalue()

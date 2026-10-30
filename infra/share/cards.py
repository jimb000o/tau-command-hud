"""Share cards: the 1200×630 pictures X, Telegram and WhatsApp show under a
tauhud.com link (og:image), in the Tau HUD look of the weekly recap.

Each card() function takes plain numbers (share.py reads them from the relay
and proposals.json) and returns PNG bytes. Nothing here talks to the network.
"""
from __future__ import annotations

import hashlib
import io
import os
import time

from PIL import Image, ImageDraw, ImageFont

FONTS = os.environ.get("FONTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"))
SORA, MONO = "Sora.ttf", "JetBrainsMono.ttf"

# Same tokens as the pages and the recap: black and white, phosphor green as the one accent.
VOID, DECK, LINE, HAIR = (9, 9, 10), (18, 18, 20), (38, 38, 42), (60, 60, 66)
WHITE, TEXT, DIM, OK, BAR = (255, 255, 255), (235, 235, 238), (138, 138, 148), (57, 255, 138), (150, 150, 158)

W, H, S = 1200, 630, 2   # drawn at 2× and scaled down: crisp text and lines

TX_NAMES = {
    "user_tx": "Transfer", "rule_deploy": "Own rule set", "retractable_transfer": "Retractable transfer",
    "retract_transfer": "Transfer pulled back", "approval_request": "Co-signed transfer", "transfer_vote": "Co-sign vote",
    "rule_offer": "Rule offered", "rule_offer_accept": "Rule offer accepted", "rule_offer_reject": "Rule offer refused",
    "consensus_rule_update": "Rule change proposed", "consensus_rule_vote": "Rule change vote",
}


def sc(v: float) -> int:
    return int(round(v * S))


def B(x0, y0, x1, y1):
    return [sc(x0), sc(y0), sc(x1), sc(y1)]


_cache: dict[tuple, ImageFont.FreeTypeFont] = {}


def font(name: str, size: float, weight: int = 400):
    key = (name, size, weight)
    if key not in _cache:
        f = ImageFont.truetype(os.path.join(FONTS, name), sc(size))
        try:
            f.set_variation_by_axes([weight])
        except (OSError, AttributeError):
            pass
        _cache[key] = f
    return _cache[key]


# Sora has no arrows or ≈; those few characters come from JetBrains Mono.
FALLBACK = set("→←≈…✓−")


def runs(text: str, f):
    if not str(getattr(f, "path", "")).endswith(SORA):
        return [(text, f)]
    mono = ImageFont.truetype(os.path.join(FONTS, MONO), int(f.size))
    out: list[list] = []
    for ch in text:
        g = mono if ch in FALLBACK else f
        if out and out[-1][1] is g:
            out[-1][0] += ch
        else:
            out.append([ch, g])
    return out


def tlen(d, text: str, f) -> float:
    """Width in card pixels (1×)."""
    return sum(d.textlength(t, font=g) for t, g in runs(text, f)) / S


def text(d, x: float, y: float, s: str, f, fill=TEXT, right: bool = False):
    if right:
        x -= tlen(d, s, f)
    x = sc(x)
    for t, g in runs(s, f):
        d.text((x, sc(y)), t, font=g, fill=fill)
        x += d.textlength(t, font=g)
    return tlen(d, s, f)


def fit(d, s: str, name: str, size: float, weight: int, width: float):
    """The font at `size` or smaller so that s fits in `width` (never cut a word)."""
    while size > 10:
        f = font(name, size, weight)
        if tlen(d, s, f) <= width:
            return f
        size -= 1
    return font(name, size, weight)


def wrap(d, s: str, f, width: float) -> list[str]:
    lines, cur = [], ""
    for w in s.split():
        t = (cur + " " + w).strip()
        if cur and tlen(d, t, f) > width:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def wrap_fit(d, s: str, name: str, size: float, weight: int, width: float, max_lines: int):
    """Wrapped lines and the largest font (down to 12 px) that keeps them within max_lines."""
    while True:
        f = font(name, size, weight)
        lines = wrap(d, s, f, width)
        if len(lines) <= max_lines or size <= 12:
            return lines[:max_lines], f
        size -= 1


def fmt_n(n) -> str:
    return "—" if n is None else f"{round(n):,}"


def fmt_a(n) -> str:
    if n is None:
        return "—"
    return f"{n:,.0f}" if float(n).is_integer() else f"{n:,.2f}".rstrip("0").rstrip(".")


def short(h: str | None) -> str:
    return f"{h[:6]}…{h[-4:]}" if h and len(h) > 12 else (h or "—")


def plural(n: int, w: str) -> str:
    return f"{fmt_n(n)} {w}{'' if n == 1 else 's'}"


def dur(s: float | None) -> str:
    if s is None:
        return ""
    if s < 90:
        return f"{round(s)} s"
    if s < 5400:
        return f"{round(s / 60)} min"
    if s < 172800:
        return f"{s / 3600:.0f} h"
    return f"{s / 86400:.0f} days"


def when(ts: float | None) -> str:
    return time.strftime("%d %b %Y, %H:%M UTC", time.gmtime(ts)).lstrip("0") if ts else "genesis"


# ---------------- frame ----------------
def frame(kind: str, path: str):
    img = Image.new("RGB", (W * S, H * S), VOID)
    d = ImageDraw.Draw(img)
    for gx in range(0, W, 96):
        d.line([sc(gx), 0, sc(gx), sc(H)], fill=(16, 16, 18), width=S)
    for gy in range(0, H, 96):
        d.line([0, sc(gy), sc(W), sc(gy)], fill=(16, 16, 18), width=S)
    mark(d, 40, 30, 52)
    text(d, 104, 36, "Tau HUD", font(SORA, 24, 700), WHITE)
    text(d, 104, 66, "Tau Testnet Alpha, live", font(MONO, 14), DIM)
    fk = font(SORA, 13, 600)
    tw = tlen(d, kind, fk)
    d.rounded_rectangle(B(W - 40 - tw - 32, 42, W - 40, 74), radius=sc(16), outline=HAIR, width=S)
    text(d, W - 56, 49, kind, fk, TEXT, right=True)
    d.line(B(40, 104, W - 40, 104), fill=LINE, width=S)
    d.line(B(40, 576, W - 40, 576), fill=LINE, width=S)
    fh = font(SORA, 16, 700)
    x = 40 + text(d, 40, 590, "tauhud.com", fh, WHITE)
    fp = fit(d, path, SORA, 16, 500, 640)
    text(d, x, 590, path, fp, DIM)
    text(d, W - 40, 593, "unofficial community view", font(MONO, 13), DIM, right=True)
    return img, d


def mark(d, x: float, y: float, s: float):
    """The Pulse logo: a ring and a heartbeat line (64-unit viewBox as in favicon.svg)."""
    k = s / 64
    w = max(2, sc(3.2 * k))
    d.ellipse(B(x + 7 * k, y + 7 * k, x + 57 * k, y + 57 * k), outline=WHITE, width=w)
    pts = [(13, 33), (23, 33), (27.5, 24), (34.5, 43), (39, 33), (51, 33)]
    d.line([(sc(x + px * k), sc(y + py * k)) for px, py in pts], fill=OK, width=w, joint="curve")


def panel(d, box, title: str | None = None):
    d.rounded_rectangle(B(*box), radius=sc(10), fill=DECK, outline=LINE, width=S)
    if title:
        text(d, box[0] + 20, box[1] + 16, title.upper(), font(SORA, 12, 600), DIM)


def stat(d, box, title: str, val: str, unit: str | None, note: str, col=WHITE):
    panel(d, box, title)
    fb = font(SORA, 40, 600)
    w = text(d, box[0] + 20, box[1] + 38, val, fb, col)
    if unit:
        text(d, box[0] + 28 + w, box[1] + 60, unit, font(SORA, 15, 500), DIM)
    if note:
        text(d, box[0] + 20, box[1] + 102, note, fit(d, note, MONO, 13, 400, box[2] - box[0] - 40), DIM)


def dot(d, x: float, y: float, r: float = 7, col=OK):
    d.ellipse(B(x - r, y - r, x + r, y + r), fill=col)


def check(d, x: float, y: float):
    d.line([(sc(x), sc(y + 8)), (sc(x + 8), sc(y + 16)), (sc(x + 22), sc(y))], fill=OK, width=sc(3), joint="curve")


def bar(d, x0, y, x1, frac: float, col):
    d.rounded_rectangle(B(x0, y, x1, y + 14), radius=sc(7), fill=LINE)
    if frac > 0:
        d.rounded_rectangle(B(x0, y, max(x0 + 14, x0 + (x1 - x0) * min(frac, 1)), y + 14), radius=sc(7), fill=col)


def png(img) -> bytes:
    buf = io.BytesIO()
    img.resize((W, H), Image.LANCZOS).save(buf, "PNG", optimize=True)
    return buf.getvalue()


# ---------------- cards ----------------
def generic() -> bytes:
    """When the chain cannot be read: the logo and the claim, like og.png."""
    img, d = frame("TAU TESTNET ALPHA", "/")
    mark(d, 120, 210, 210)
    text(d, 400, 210, "Tau HUD", font(SORA, 84, 700), WHITE)
    text(d, 404, 320, "Where the rules change by agreement.", font(SORA, 26, 600), TEXT)
    text(d, 404, 362, "Blocks, rule changes, votes and validators,", font(MONO, 17), DIM)
    text(d, 404, 388, "live from our own verifying node.", font(MONO, 17), DIM)
    return png(img)


def hud(c: dict) -> bytes:
    """c: head, synced, pace, validators, rev, voting, agreed, txs, last_txs."""
    img, d = frame("LIVE OVERVIEW", "/")
    text(d, 40, 128, "Block height", font(SORA, 16, 500), DIM)
    text(d, 40, 146, "#" + fmt_n(c["head"]), fit(d, "#" + fmt_n(c["head"]), SORA, 110, 700, 560), WHITE)
    state = "Live node · synced" if c.get("synced") else "Live node · catching up"
    if c.get("pace"):
        state += f" · a block every {dur(c['pace'])}"
    dot(d, 52, 312, 7, OK if c.get("synced") else BAR)
    text(d, 68, 301, state, fit(d, state, MONO, 16, 400, 500), TEXT)
    pts, x = [], 40
    while x < 560:
        pts += [(x, 380), (x + 30, 380), (x + 38, 350), (x + 48, 410), (x + 56, 380)]
        x += 76
    d.line([(sc(a), sc(b)) for a, b in pts], fill=OK, width=sc(3), joint="curve")
    text(d, 40, 430, "Where the rules change by agreement.", font(SORA, 26, 600), WHITE)
    text(d, 40, 474, "Blocks, rule changes, votes and validators", font(MONO, 16), DIM)
    text(d, 40, 500, "of the Tau Testnet Alpha, as they happen.", font(MONO, 16), DIM)
    rev = c.get("rev") or 0
    stat(d, (640, 128, 900, 268), "Rule changes", fmt_n(rev), "in force", "agreed by vote" if rev else "genesis rules only")
    stat(d, (920, 128, 1160, 268), "Validators", fmt_n(c.get("validators")), None, "agree on every block")
    coming = (c.get("voting") or 0) + (c.get("agreed") or 0)
    note = (f"{c['voting']} waiting for votes" if c.get("voting") else "") + \
           (" · " if c.get("voting") and c.get("agreed") else "") + (f"{c['agreed']} agreed" if c.get("agreed") else "")
    stat(d, (640, 288, 900, 428), "Coming up", fmt_n(coming), "rule" if coming == 1 else "rules",
         note or "nothing proposed right now", OK if coming else WHITE)
    stat(d, (920, 288, 1160, 428), "Transactions", fmt_n(c.get("txs")), None, "on this chain")
    panel(d, (640, 448, 1160, 552), "Newest block")
    line = f"#{fmt_n(c['head'])}  ·  {plural(c.get('last_txs') or 0, 'transaction')}  ·  checked"
    text(d, 660, 484, line, fit(d, line, MONO, 17, 400, 440), TEXT)
    dot(d, 1134, 494)
    return png(img)


def block(c: dict) -> bytes:
    """c: h, ts, gap, proposer, validator, head, txs: [{kind, line, amt}]"""
    h = c["h"]
    img, d = frame("BLOCK", f"/explorer/?b={h}")
    text(d, 40, 124, f"Block #{fmt_n(h)}", fit(d, f"Block #{fmt_n(h)}", SORA, 64, 700, 700), WHITE)
    n = len(c["txs"])
    head = "Genesis · the first block" if h == 0 else f"In the chain · {plural(n, 'transaction')} · {plural(c['head'] - h + 1, 'block')} deep"
    dot(d, 52, 236)
    text(d, 68, 225, head, fit(d, head, MONO, 17, 400, 680), TEXT)
    panel(d, (40, 272, 760, 552), "Transactions")
    rows = c["txs"][:3] if n <= 3 else c["txs"][:2]
    if not rows:
        text(d, 60, 316, "No transactions. An empty block still", font(SORA, 19, 500), TEXT)
        text(d, 60, 346, "moves the chain forward and counts", font(SORA, 19, 500), TEXT)
        text(d, 60, 376, "toward rule activations.", font(SORA, 19, 500), TEXT)
    for i, t in enumerate(rows):
        y = 314 + i * 76
        text(d, 60, y, TX_NAMES.get(t["kind"], t["kind"]), font(SORA, 14, 600), DIM)
        amt = f"{fmt_a(t['amt'])} AGRS" if t.get("amt") is not None else t.get("tag") or ""
        aw = text(d, 740, y + 20, amt, font(SORA, 17, 600), WHITE, right=True) if amt else 0
        text(d, 60, y + 22, t["line"], fit(d, t["line"], MONO, 17, 400, 660 - aw), TEXT)
        if i < 2:
            d.line(B(60, y + 60, 740, y + 60), fill=LINE, width=S)
    if n > 3:
        text(d, 60, 314 + 2 * 76 + 10, f"+ {n - 2} more transactions", font(SORA, 18, 600), TEXT)
    panel(d, (780, 128, 1160, 400), "Checked by our node")
    checks = ["sealed by a validator", "every transaction allowed", "same state everywhere"] if h else \
        ["starting balances", "starting rules", "same genesis everywhere"]
    for i, s in enumerate(checks):
        check(d, 802, 176 + i * 50)
        text(d, 836, 172 + i * 50, s, font(MONO, 16), TEXT)
    note = ("The rules in force said yes,", "so the block is part of the chain.") if h else \
        ("Every node starts from this block,", "so they all agree from the start.")
    text(d, 800, 336, note[0], font(SORA, 15, 500), DIM)
    text(d, 800, 358, note[1], font(SORA, 15, 500), DIM)
    panel(d, (780, 420, 1160, 552), "Sealed")
    text(d, 800, 456, when(c.get("ts")), font(MONO, 17), TEXT)
    if h:
        by = f"by {short(c.get('proposer'))}" + (" · validator" if c.get("validator") else "")
        text(d, 800, 486, by, font(MONO, 15), DIM)
        if c.get("gap") is not None:
            text(d, 800, 510, f"{dur(c['gap'])} after block #{fmt_n(h - 1)}", font(MONO, 15), DIM)
    return png(img)


STATUS = {"voting": ("Waiting for votes", OK), "agreed": ("Agreed, takes effect soon", OK),
          "active": ("In force", OK), "dropped": ("Dropped, the old rules stay", DIM)}


def proposal(p: dict, head: int | None, pace: float | None) -> bytes:
    """p: one entry of proposals.json."""
    img, d = frame("RULE PROPOSAL", f"/proposals/#{p['id'][:16]}")
    text(d, 40, 122, f"Proposal {p.get('n', '')}".strip(), font(SORA, 16, 500), DIM)
    title = p.get("title") or "A rule change"
    tl, tf = wrap_fit(d, title, SORA, 54, 700, 650, 2)
    if len(tl) == 2:
        tl, tf = wrap_fit(d, title, SORA, 40, 700, 650, 2)
    y = 142
    for ln in tl:
        text(d, 40, y, ln, tf, WHITE)
        y += tf.size / S * 1.15
    st, col = STATUS.get(p.get("status"), (p.get("status", ""), DIM))
    dot(d, 52, y + 26, 7, col)
    text(d, 68, y + 15, st, font(SORA, 19, 600), col)
    top = max(272, y + 60)
    panel(d, (40, top, 700, 552), "What changes")
    x = p.get("explain") or {}
    changes = [f"{c['topic']}: {c['text']}" for c in x.get("changes") or []] or (
        ["Nothing: the text equals the rules already in force."] if x else p.get("parts") or [])
    lines, f = wrap_fit(d, " · ".join(changes), SORA, 21, 500, 620, 3 if top <= 272 else 2)
    yy = top + 40
    for ln in lines:
        text(d, 60, yy, ln, f, TEXT)
        yy += f.size / S * 1.6
    why = x.get("why") or ""
    if why:
        text(d, 60, yy + 14, "WHY IT MATTERS", font(SORA, 12, 600), DIM)
        wl, wf = wrap_fit(d, why, MONO, 16, 400, 620, max(1, int((552 - (yy + 40) - 10) // 28)))
        for i, ln in enumerate(wl):
            text(d, 60, yy + 40 + i * 28, ln, wf, DIM)
    v, need = p.get("counted_votes") or 0, p.get("thr") or 1
    panel(d, (720, 128, 1160, 330), "Votes")
    fb = font(SORA, 46, 600)
    w = text(d, 740, 164, f"{v} / {need}", fb, WHITE)
    text(d, 750 + w, 188, "votes needed" if v < need else "enough votes", font(SORA, 15, 500), DIM)
    bar(d, 740, 250, 1140, v / need if need else 1, OK)
    text(d, 740, 280, f"{plural(v, 'vote')} counted · {need} needed", font(MONO, 14), DIM)
    s = p.get("status")
    if s == "active":
        panel(d, (720, 350, 1160, 552), "In force since")
        text(d, 740, 386, "#" + fmt_n(p.get("activated_at")), font(SORA, 46, 600), WHITE)
        text(d, 740, 460, f"rules revision {p.get('rev')}", font(MONO, 15), DIM)
        text(d, 740, 486, when(p.get("activated_ts")), font(MONO, 15), DIM)
    elif s == "dropped":
        panel(d, (720, 350, 1160, 552), "Dropped at")
        text(d, 740, 386, "#" + fmt_n(p.get("expired_at")), font(SORA, 46, 600), WHITE)
        text(d, 740, 460, "not enough votes by the deadline", font(MONO, 15), DIM)
    else:
        left = max(0, (p.get("activate_at") or 0) - (head or 0))
        panel(d, (720, 350, 1160, 552), "Takes effect in" if s == "agreed" else "Deadline in")
        w = text(d, 740, 386, fmt_n(left), font(SORA, 46, 600), WHITE)
        eta = f"blocks  ≈ {dur(left * pace)}" if pace and left else "blocks"
        text(d, 750 + w, 410, eta, font(SORA, 15, 500), DIM)
        start = p.get("approved_at") if s == "agreed" else p.get("proposed_at")
        span = max(1, (p.get("activate_at") or 0) - (start or 0))
        bar(d, 740, 472, 1140, 1 - left / span, BAR)
        text(d, 740, 502, f"at block #{fmt_n(p.get('activate_at'))} · now #{fmt_n(head)}", font(MONO, 14), DIM)
    return png(img)


def address(c: dict) -> bytes:
    """c: addr, balance, sent, received, in_sum, out_sum, last_h, validator, sealed, recent: [{h, kind, dir, amt, other}]"""
    a = c["addr"]
    img, d = frame("ADDRESS", f"/explorer/?a={short(a)}")
    text(d, 40, 122, "Address" + (" · validator" if c.get("validator") else ""), font(SORA, 16, 500), OK if c.get("validator") else DIM)
    text(d, 40, 142, short(a), font(MONO, 56, 700), WHITE)
    seen = f"Last active in block #{fmt_n(c['last_h'])}" if c.get("last_h") is not None else "No transactions on this chain yet"
    text(d, 40, 226, seen, font(MONO, 17), TEXT)
    stat(d, (40, 272, 400, 412), "Balance", fmt_a(c.get("balance")) if c.get("balance") is not None else "—", "AGRS", "after the newest block")
    stat(d, (420, 272, 780, 412), "Transactions", fmt_n((c.get("sent") or 0) + (c.get("received") or 0)), None,
         f"{c.get('sent') or 0} sent · {c.get('received') or 0} received")
    if c.get("sealed"):
        stat(d, (800, 272, 1160, 412), "Blocks sealed", fmt_n(c["sealed"]), None, "as a validator")
    else:
        stat(d, (800, 272, 1160, 412), "Moved", fmt_a((c.get("in_sum") or 0) + (c.get("out_sum") or 0)), "AGRS",
             f"{fmt_a(c.get('in_sum') or 0)} in · {fmt_a(c.get('out_sum') or 0)} out")
    panel(d, (40, 432, 1160, 552), "Latest activity")
    rec = c.get("recent") or []
    if not rec:
        text(d, 60, 476, "Nothing yet. Activity shows up here after the first transaction.", font(MONO, 16), DIM)
    for i, r in enumerate(rec[:2]):
        y = 466 + i * 38
        text(d, 60, y, f"#{fmt_n(r['h'])}", font(MONO, 16), DIM)
        text(d, 160, y, TX_NAMES.get(r["kind"], r["kind"]), font(SORA, 16, 600), TEXT)
        if r.get("other"):
            text(d, 460, y, ("from " if r["dir"] == "in" else "to ") + short(r["other"]), font(MONO, 16), DIM)
        if r.get("amt") is not None:
            sign = "+" if r["dir"] == "in" else "−"
            text(d, 1140, y, f"{sign}{fmt_a(r['amt'])} AGRS", font(SORA, 16, 600), OK if r["dir"] == "in" else TEXT, right=True)
    return png(img)


# ---------------- My Tau card ----------------
# The wallet's three check words (wallet/index.html: sha256 of the address text, bytes 8 to 10): a name people can say.
WORDS = (
    'acorn amber anchor apple arrow atlas badge baker bamboo banjo barley basil beacon beaver berry bison blade '
    'blossom bonnet bottle bramble breeze brick bridge bronze brook bucket bugle cabin cactus camel candle canoe '
    'canyon carbon carrot castle cedar cello chalk cherry chess cider cinder circus clover cobalt comet copper '
    'coral cotton cougar crane crater cricket crystal cupola dahlia daisy delta denim desert dingo dolphin dragon '
    'drum eagle easel ember emerald engine falcon feather fennel fern fiddle flint forest fossil fox galaxy '
    'garden garnet gecko geyser ginger glacier goblet granite grape gravel guitar hammer harbor harp hazel heron '
    'hickory honey hornet husky iceberg igloo indigo iris island ivory jackal jade jaguar jasmine jelly jigsaw '
    'jungle kayak kernel kettle kiwi koala ladder lagoon lantern laurel lemon lilac lily linen lizard lobster '
    'locket lotus magnet mango maple marble meadow melon meteor mint mitten mosaic moss muffin nectar needle '
    'nickel nutmeg oak oasis olive onyx orbit orchid otter oyster paddle panda papaya parrot pebble pecan pelican '
    'pepper piano pine planet plum pollen poppy prism puffin pumpkin quartz quill rabbit radish raven reef ribbon '
    'river robin rocket rose ruby saddle saffron salmon sapphire satin shell sierra silver sparrow spruce squid '
    'statue stone summit sunset swan tango teapot thistle thunder tiger timber toucan tractor trumpet tulip '
    'tundra turtle umbrella valley velvet violet volcano walnut walrus willow window winter wizard yarrow yogurt '
    'zebra zenith zinc basket beetle bobcat cocoa cobra dune elm glove gopher jasper lark mammoth marsh opal '
    'osprey parsley quail rhubarb sable sequoia stork tapir topaz trout vanilla wombat yak nomad '
).split()


def words(a: str) -> str:
    h = hashlib.sha256(a.encode()).digest()
    return " · ".join(WORDS[x] for x in h[8:11])


def card_line(c: dict) -> str:
    parts = []
    if c.get("rules"):
        parts.append(f"wrote {plural(c['rules'], 'rule')}")
    if c.get("votes"):
        parts.append(f"cast {plural(c['votes'], 'vote')}")
    if c.get("meals"):
        parts.append("fed Agorzilla " + ("once" if c['meals'] == 1 else f"{c['meals']} times"))
    if not parts:
        return "Just arrived on Tau Testnet Alpha."
    return "This wallet " + ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1] + "."


def stamp(d, x: float, y: float, r: float, on: bool, letter: str):
    if on:
        d.ellipse(B(x - r, y - r, x + r, y + r), outline=OK, width=sc(2.5))
        d.ellipse(B(x - r + 5, y - r + 5, x + r - 5, y + r - 5), outline=(30, 120, 70), width=S)
        f = font(SORA, 20, 700)
        text(d, x - tlen(d, letter, f) / 2, y - 13, letter, f, OK)
    else:
        for i in range(0, 360, 30):   # a dashed ring: the empty place on the ticket
            d.arc(B(x - r, y - r, x + r, y + r), i, i + 16, fill=HAIR, width=S)


def my_card(c: dict, stamps: int = 0) -> bytes:
    """c: share.card_numbers() (addr, rules, own, offered, proposed, votes, rule_votes, agz_votes, meals, first_ts); stamps 0..4."""
    a = c["addr"]
    img, d = frame("MY TAU CARD", "/card/")
    h = hashlib.sha256(a.encode()).digest()
    for i, x in enumerate(h[:8]):   # the address print, as in the wallet: bars from the address's hash
        bh, g = 18 + (x % 10) * 5, int(255 * (.45 + (x >> 4) / 30))
        d.rounded_rectangle(B(40 + i * 13, 196 - bh, 48 + i * 13, 196), radius=sc(2), fill=(g, g, g))
    name = words(a)
    text(d, 160, 124, name, fit(d, name, SORA, 46, 700, 1000), WHITE)
    since = (" · on the testnet since " + time.strftime("%d %b %Y", time.gmtime(c["first_ts"])).lstrip("0")) if c.get("first_ts") else " · new on the testnet"
    text(d, 162, 186, short(a) + since, font(MONO, 16), DIM)

    y0, y1, gap = 232, 392, 20
    w = (W - 80 - 3 * gap) / 4
    xs = [40 + i * (w + gap) for i in range(4)]
    rn = [f"{c[k]} {k}" for k in ("own", "offered", "proposed") if c.get(k)]
    stat(d, (xs[0], y0, xs[0] + w, y1), "Rules written", fmt_n(c.get("rules") or 0), None, " · ".join(rn) or "own rules, offers, changes")
    stat(d, (xs[1], y0, xs[1] + w, y1), "Votes cast", fmt_n(c.get("votes") or 0), None,
         f"{c.get('rule_votes') or 0} on rules · {c.get('agz_votes') or 0} for Agorzilla")
    stat(d, (xs[2], y0, xs[2] + w, y1), "Agorzilla meals", fmt_n(c.get("meals") or 0), None, "one counts per hour")
    panel(d, (xs[3], y0, xs[3] + w, y1), "Café stamps")
    step = (w - 40 - 56) / 3
    for i, k in enumerate("ACLT"):   # Agreement, Chain, Logic, Testnet: the café ticket
        stamp(d, xs[3] + 48 + i * step, y0 + 74, 26, i < stamps, k)
    text(d, xs[3] + 20, y0 + 120, f"{stamps} of 4 · the café walk", font(MONO, 13), DIM)

    panel(d, (40, 412, W - 40, 552))
    line = card_line(c)
    text(d, 64, 436, line, fit(d, line, SORA, 26, 600, W - 130), WHITE)
    text(d, 64, 482, "Helping test the rules of Tau Testnet Alpha, where rules change by agreement.", font(MONO, 15), TEXT)
    text(d, 64, 510, "Test AGRS have no value. Nothing on this card is priced or promised.", font(MONO, 14), DIM)
    return png(img)

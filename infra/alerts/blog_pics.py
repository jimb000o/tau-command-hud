"""Pictures for the Tau HUD blog: a hero picture made from the island's own painting (cruise_pic.py, the painting the
game shows, with the painted ship and a card that says at a glance why the article matters) and charts drawn from
the numbers the article was written from, in the site's look (near-black, white, one green accent).

  python blog_pics.py hero <art dir> <ships dir> <card.json> <out.jpg>
  python blog_pics.py desk <card.json> <out.jpg>   the hero of an article not about the island (IDNI news, a Q&A)
  python blog_pics.py demo <out dir>        the charts of the MS Dry Run article, from its logbook numbers

Every chart says its point in its title, so a picture shared alone still tells why it matters."""
from __future__ import annotations

import json
import os
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 900
BG, DECK, LINE, DIM, TEXT, OK, AMBER = (9, 9, 10), (18, 18, 20), (44, 44, 50), (138, 138, 148), (235, 235, 238), (57, 255, 138), (255, 177, 59)
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def font(size: int, weight: int = 600, mono: bool = False):
    name = "JetBrainsMono.ttf" if mono else "Sora.ttf"
    for p in (os.path.join(FONTS, name), os.path.join("/app/fonts", name)):
        if os.path.exists(p):
            f = ImageFont.truetype(p, size)
            try:
                f.set_variation_by_axes([weight])
            except Exception:  # noqa: BLE001 - a static font: its own weight
                pass
            return f
    return ImageFont.load_default(size)


def frame(title: str, sub: str = "") -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    for x in range(0, W, 96):
        d.line([(x, 0), (x, H)], fill=(16, 16, 18))
    for y in range(0, H, 96):
        d.line([(0, y), (W, y)], fill=(16, 16, 18))
    d.text((80, 70), title, font=font(52, 700), fill=TEXT)
    if sub:
        d.text((80, 146), sub, font=font(28, 400), fill=DIM)
    d.text((80, H - 64), "tauhud.com/blog · community project, not affiliated with IDNI", font=font(22, 400, mono=True), fill=DIM)
    return im, d


def bars(values: list[float], labels: list[str], title: str, sub: str = "", note: str = "", accent: list[int] | None = None,
         unit: str = "", cap: float | None = None, cap_label: str = "") -> Image.Image:
    """Vertical bars, the value on top of each, `accent` the indices drawn green (the point of the chart), the rest grey."""
    im, d = frame(title, sub)
    x0, x1, y0, y1 = 120, W - 120, 250, H - 170
    top = max(values + ([cap] if cap else [])) or 1
    n = len(values)
    gap = (x1 - x0) / n
    bw = min(220, gap * 0.62)
    d.line([(x0, y1), (x1, y1)], fill=LINE, width=2)
    for i, (v, lab) in enumerate(zip(values, labels)):
        cx = x0 + gap * (i + 0.5)
        h = (y1 - y0) * v / top
        col = OK if accent is None or i in accent else (92, 92, 100)
        d.rounded_rectangle([cx - bw / 2, y1 - h, cx + bw / 2, y1], radius=8, fill=col)
        txt = f"{v:g}{unit}"
        f = font(40, 700)
        d.text((cx - d.textlength(txt, font=f) / 2, y1 - h - 54), txt, font=f, fill=TEXT)
        f2 = font(24, 500)
        for j, part in enumerate(lab.split("\n")):
            d.text((cx - d.textlength(part, font=f2) / 2, y1 + 16 + j * 32), part, font=f2, fill=DIM if col != OK else TEXT)
    if cap:
        cy = y1 - (y1 - y0) * cap / top
        for xx in range(x0, x1, 24):
            d.line([(xx, cy), (xx + 12, cy)], fill=DIM, width=2)
        d.text((x1 - d.textlength(cap_label, font=font(24, 500)), cy - 36), cap_label, font=font(24, 500), fill=DIM)
    if note:
        d.text((x1 - d.textlength(note, font=font(24, 500)), 160), note, font=font(24, 500), fill=OK)
    return im


def split(parts: list[tuple[str, float, tuple]], title: str, sub: str = "") -> Image.Image:
    """One row per part (name, bar, count), bars to one scale: where the planned stops went."""
    im, d = frame(title, sub)
    x0, x1, y = 470, W - 220, 270
    top = max(v for _, v, _ in parts) or 1
    step = min(130, (H - 200 - y) / max(1, len(parts)))
    for name, v, col in parts:
        d.text((80, y + 14), name, font=font(32, 500), fill=TEXT)
        w = max(6, (x1 - x0) * v / top)
        d.rounded_rectangle([x0, y, x0 + w, y + 70], radius=8, fill=col)
        d.text((x0 + w + 24, y + 6), f"{v:g}", font=font(48, 700), fill=TEXT)
        y += step
    return im


def hero(art: str, ships: str, card: list[str], ship: str, out: str, stats: list | None = None, host: str | None = "rico") -> str:
    """The island's painting with the ship and the card (cruise_pic.py, the same picture as the ship's announcement),
    then the article's hard numbers as tiles in the free water on the left, and the island's own radio host, painted
    as in the game, looking on from the sea beside the card: the game's art and the data in one picture."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import cruise_pic
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"ship": ship, "ship_scale": 3, "card": card}, f)
    try:
        cruise_pic.main(art, ships, f.name, out)
    finally:
        os.unlink(f.name)
    if not stats and not host:
        return out
    pic = Image.open(out).convert("RGBA")
    d = ImageDraw.Draw(pic)
    # where the card ends: the first dark row under its top-left corner
    card_bottom = 470
    for y in range(90, 700, 4):
        if sum(pic.getpixel((70, y))[:3]) > 120:
            card_bottom = y
            break
    if host:
        bust = portrait(art, host)
        if bust is not None:
            h = 430
            bust = bust.resize((round(bust.width * h / bust.height), h), Image.LANCZOS)
            x = W - bust.width - 24
            pic.alpha_composite(bust, (x, 18))
            tag = "Rico · Radio Coco" if host == "rico" else host.title()
            ft = font(22, 600)
            tw = d.textlength(tag, font=ft)
            d.rounded_rectangle([x + bust.width / 2 - tw / 2 - 14, 18 + h - 6, x + bust.width / 2 + tw / 2 + 14, 18 + h + 30], radius=14, fill=(8, 12, 24, 230))
            d.text((x + bust.width / 2 - tw / 2, 18 + h - 1), tag, font=ft, fill=(235, 235, 238, 255))
    if stats:
        over = Image.new("RGBA", pic.size)
        od = ImageDraw.Draw(over)
        tiles = stats[:4]
        tw, th, gap = 214, 150, 14
        x0, y0 = 56, max(card_bottom + 24, H - 56 - 2 * th - gap)
        for i, (num, label) in enumerate(tiles):
            x, y = x0 + (i % 2) * (tw + gap), y0 + (i // 2) * (th + gap)
            od.rounded_rectangle([x, y, x + tw, y + th], radius=16, fill=(8, 12, 24, 228), outline=(57, 255, 138, 110), width=2)
            fn = font(54 if len(str(num)) <= 5 else 40, 700)
            od.text((x + 20, y + 18), str(num), font=fn, fill=(57, 255, 138, 255) if i == 0 else (242, 242, 242, 255))
            size, lines = 21, wrap(od, str(label), font(21, 500), tw - 36)
            if len(lines) > 2:   # a longer label gets a smaller type rather than losing its last word
                size, lines = 18, wrap(od, str(label), font(18, 500), tw - 36)
            for j, part in enumerate(lines[:2 if size == 21 else 3]):
                od.text((x + 20, y + (88 if size == 21 else 84) + j * (size + 5)), part, font=font(size, 500), fill=(190, 196, 204, 255))
        pic = Image.alpha_composite(pic, over)
    pic.convert("RGB").save(out, quality=90)
    return out


def desk_hero(card: list[str], out: str, stats: list | None = None, kicker: str = "") -> str:
    """The hero of an article that is not about the island or a ship (IDNI news, a Q&A, testnet learnings): no island,
    no ship, no radio host, only the site's own look. The card on the left in large type, the article's hard numbers
    as tiles on the right, a row of blocks along the foot (the last one lit) so a picture shared alone still reads as
    the testnet. Island art stays with the island's and the ships' own articles."""
    im = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=(15, 15, 17))
    for y in range(0, H, 64):
        d.line([(0, y), (W, y)], fill=(15, 15, 17))
    glow = Image.new("RGBA", (W, H))
    gd = ImageDraw.Draw(glow)
    for r in range(520, 0, -20):   # a faint green light from the upper left, the site's one accent
        gd.ellipse([180 - r, 120 - r, 180 + r, 120 + r], fill=(57, 255, 138, max(0, 7 - r // 80)))
    im = Image.alpha_composite(im, glow)
    d = ImageDraw.Draw(im)
    lines = [str(c) for c in (card or []) if c]
    foot = lines.pop() if lines and "not affiliated" in lines[-1] else "Tau HUD blog · community project, not affiliated with IDNI"
    title = lines.pop(0) if lines else ""
    sub = lines.pop(0) if lines and not lines[0].startswith(("#", "-")) else ""
    why = [c[1:].strip() for c in lines if c.startswith("-")]
    head = next((c.lstrip("# ").strip() for c in lines if c.startswith("#")), "Why it matters")
    x0, col = 80, 860 if stats else 1440
    y = 78
    if kicker:
        d.text((x0, y), kicker.upper(), font=font(24, 600, mono=True), fill=OK)
        y += 56
    f, size = font(72, 700), 72
    tl = wrap(d, title, f, col - x0)
    if len(tl) > 2:
        size = 58
        f = font(size, 700)
        tl = wrap(d, title, f, col - x0)
    for part in tl[:3]:
        d.text((x0, y), part, font=f, fill=TEXT)
        y += round(size * 1.14)
    if sub:
        y += 10
        for part in wrap(d, sub, font(32, 400), col - x0)[:2]:
            d.text((x0, y), part, font=font(32, 400), fill=(190, 196, 204))
            y += 44
    if why:
        y += 30
        d.text((x0, y), head.upper(), font=font(22, 600, mono=True), fill=OK)
        y += 44
        for w in why[:3]:
            d.ellipse([x0 + 2, y + 13, x0 + 14, y + 25], fill=OK)
            d.text((x0 + 32, y), w, font=font(30, 500), fill=TEXT)
            y += 48
    if stats:
        tw, th, gap = 300, 196, 20
        sx, sy = W - 80 - 2 * tw - gap, 120
        for i, (num, label) in enumerate(stats[:4]):
            tx, ty = sx + (i % 2) * (tw + gap), sy + (i // 2) * (th + gap)
            d.rounded_rectangle([tx, ty, tx + tw, ty + th], radius=18, fill=(14, 18, 22), outline=(57, 255, 138) if i == 0 else LINE, width=2)
            fn = font(76 if len(str(num)) <= 4 else 54, 700)
            d.text((tx + 26, ty + 20), str(num), font=fn, fill=OK if i == 0 else TEXT)
            for j, part in enumerate(wrap(d, str(label), font(24, 500), tw - 52)[:2]):
                d.text((tx + 26, ty + 120 + j * 31), part, font=font(24, 500), fill=(190, 196, 204))
    # the chain along the foot: blocks linked left to right, the newest one lit
    by, bs, bg_ = H - 150, 46, 30
    n = (W - 2 * x0 + bg_) // (bs + bg_)
    for i in range(n):
        bx = x0 + i * (bs + bg_)
        last = i == n - 1
        fade = 40 + round(110 * i / max(1, n - 1))
        col_ = OK if last else (fade, fade, fade + 6)
        d.rounded_rectangle([bx, by, bx + bs, by + bs], radius=8, outline=col_, width=3, fill=(16, 40, 26) if last else None)
        if i:
            d.line([(bx - bg_ + 4, by + bs // 2), (bx - 4, by + bs // 2)], fill=(fade, fade, fade + 6), width=3)
    d.text((x0, H - 72), foot, font=font(22, 400, mono=True), fill=DIM)
    im.convert("RGB").save(out, quality=90)
    return out


def wrap(d, text: str, f, width: float) -> list[str]:
    out, line = [], ""
    for w in text.split():
        t = (line + " " + w).strip()
        if d.textlength(t, font=f) <= width or not line:
            line = t
        else:
            out.append(line)
            line = w
    return out + ([line] if line else [])


def portrait(art: str, who: str):
    """The painted portrait the game shows (paint.py busts: index.json scenes "bust-<who>", cut out), or None."""
    try:
        idx = json.load(open(os.path.join(art, "index.json")))
        name = (idx.get("scenes") or {}).get("bust-" + who)
        return Image.open(os.path.join(art, name)).convert("RGBA") if name else None
    except Exception:  # noqa: BLE001 - no portrait: the picture without it
        return None


def visit_stats(facts: dict) -> list[tuple[str, str]]:
    """Four numbers for the hero picture, straight from the facts."""
    out = []
    left = facts.get("left early")
    mins = facts.get("minutes in port", left.get("minutes in port") if isinstance(left, dict) else None)
    if mins is not None:   # the first tile is the same for every ship, so one call reads against the next
        b = facts.get("the ship before") or {}
        before = f" (ship before: {b['minutes in port']})" if b.get("minutes in port") is not None else ""
        out.append((f"{mins}/{facts.get('minutes planned in port', 90)}", "minutes in port" + before))
    acc = facts.get("accepted in all")
    if acc is not None:
        out.append((str(acc), "accepted by the node"))
    old = facts.get("refusals logged without any answer from the node (a timeout, counted as refusal by the old rule)") or 0
    una = (facts.get("sends our node did not answer in time (not refusals)") or 0) + old
    if una:
        # one story with the article: these were timeouts; say so when the ship's brake counted them as refusals
        out.append((str(una), "timeouts, counted as refusals" if old else "no answer in time"))
    ref = (facts.get("refused in all") or 0) - old
    if ref > 0:
        out.append((str(ref), "refused by the node"))
    port = facts.get("bookings made in port (not the bookings ahead)") or {}   # blog.IN_PORT
    due = (port.get("made") or 0) - (port.get("withdrawn by their passenger during the call") or 0)
    if due > 0:   # a booking its passenger withdrew is not paid out, and not owed either
        out.append((f"{port.get('paid out to the place by the chain at their time', 0)}/{due}", "bookings in port paid out by the chain"))
    if len(out) < 4 and facts.get("stops skipped") is not None:   # the same four tiles on every ship's picture
        out.append((str(facts["stops skipped"]), "stops skipped"))
    return out[:4]


def pairs(rows: list[tuple[str, float, float]], title: str, sub: str = "", note: str = "") -> Image.Image:
    """One row per measure, two bars to that row's own scale: the ship before in grey, this ship in green."""
    im, d = frame(title, sub)
    if note:
        d.text((80, 188), note, font=font(24, 400), fill=DIM)
    x0, x1, y = 470, W - 220, 250
    step = min(124, (H - 190 - y) / max(1, len(rows)))
    for name, before, now in rows:
        d.text((80, y + 22), name, font=font(30, 500), fill=TEXT)
        top = max(before, now) or 1
        for k, (v, col) in enumerate(((before, (92, 92, 100)), (now, OK))):
            yy = y + k * 38
            w = max(6, (x1 - x0) * v / top)
            d.rounded_rectangle([x0, yy, x0 + w, yy + 30], radius=6, fill=col)
            d.text((x0 + w + 18, yy - 4), f"{v:g}", font=font(32, 700), fill=TEXT if k else DIM)
        y += step
    return im


def visit_charts(facts: dict, base: str) -> list[tuple[str, dict]]:
    """Charts for a cruise visit, from the facts the article was written from: where the planned stops went, and
    the pace per 10 minutes. Returns [(file, caption by language)]."""
    out = []
    acc = facts.get("accepted in all") or 0
    ref = facts.get("refused in all") or 0
    una = facts.get("sends our node did not answer in time (not refusals)") or 0
    old = facts.get("refusals logged without any answer from the node (a timeout, counted as refusal by the old rule)") or 0
    skip = facts.get("stops skipped") or 0
    plan = (facts.get("landed") or {}).get("transactions planned") if isinstance(facts.get("landed"), dict) else None
    if acc or skip:
        parts = [("accepted by the node", acc, OK), ("timeout, no answer", una + old, AMBER),
                 ("refused by the node", ref - old, (255, 77, 109)), ("skipped", skip, (92, 92, 100))]
        t = f"{acc} of {plan} planned stops went through" if plan else f"{acc} stops went through"
        out.append((base + "-stops.png", split([p for p in parts if p[1] > 0], t, f"{facts.get('ship') or 'The ship'}, {facts.get('date', '')}"
                                                         + (f" · the ship counted the {old} timeouts as refusals" if old else "")),
                    {"en": "Where the planned stops went, from the ship's logbook.", "zh": "计划的停靠去了哪里，来自游轮日志。",
                     "ja": "計画された立ち寄りの行方（船のログブックより）。"}))
    per = facts.get("sends per 10 minutes") or []
    if len(per) > 1:
        labels = [f"{i * 10}–{i * 10 + 10}\nmin" for i in range(len(per))]
        logged = facts.get("sends logged")
        half = facts.get("sends at half pace because the testnet looked strained")
        node = facts.get("sends at half pace because our own node had just left a send unanswered (not the testnet)")
        why = [w for w in ((half, "testnet marked strained"), (node, "our node slow to answer")) if w[0]]
        sub = (f"{sum(n for n, _ in why)} of {logged} sends went out at half pace (" + ", ".join(f"{n} {w}" for n, w in why) + ")"
               if why and logged else f"first send {facts.get('first send', '')}, last {facts.get('last send', '')}")
        out.append((base + "-pace.png", bars(per, labels, f"At most {max(per)} sends per 10 minutes, of 120 allowed", sub,
                                             cap=120, cap_label="allowed: 120 per 10 minutes"),
                    {"en": "The ship's pace in port, sends per 10 minutes.", "zh": "游轮在港口的速度：每 10 分钟的发送数。",
                     "ja": "港での船のペース：10 分ごとの送信数。"}))
    b = facts.get("the ship before") or {}
    if b.get("ship") and (b.get("accepted in all") is not None or b.get("minutes in port") is not None):
        rows = [("minutes in port", b.get("minutes in port") or 0, facts.get("minutes in port") or 0),
                ("accepted by the node", b.get("accepted in all") or 0, acc),
                ("no answer in time", b.get("sends our node did not answer in time") or 0, una + old),
                ("refused by the node", b.get("refused in all") or 0, ref - old),
                ("stops skipped", b.get("stops skipped") or 0, skip)]
        rows = [r for r in rows if r[1] or r[2]]
        short = lambda d: " ".join(str(d or "").split(",")[1:2]).strip() or str(d or "")  # noqa: E731 - "4 November 2026"
        out.append((base + "-before.png", pairs(rows, f"{facts.get('ship') or 'This ship'} against the {b['ship']}",
                                                f"grey: {b['ship']}, {short(b.get('date'))} · green: {facts.get('ship') or 'this ship'}, {short(facts.get('date'))}",
                                                "different ships, different plans: read the shares, not the counts alone"),
                    {"en": "This call against the ship before it, from both logbooks.", "zh": "本次停靠与前一艘游轮的对比，来自两本日志。",
                     "ja": "今回の寄港と前の船との比較（両方のログブックより）。"}))
    secs = facts.get("median answer time per 10 minutes, seconds") or []
    if len(secs) > 1 and any(secs):
        labels = [f"{i * 10}–{i * 10 + 10}\nmin" for i in range(len(secs))]
        t = facts.get("our node's answer time to a send, seconds") or {}
        out.append((base + "-answer.png", bars(secs, labels, "How long our node took to answer a send",
                                               f"median per 10 minutes · slowest {t.get('slowest', 0):g} s · the relay gives up at 20 s",
                                               unit=" s", cap=20, cap_label="no answer after 20 s"),
                    {"en": "Our node's answer time to the ship's sends, from the logbook.", "zh": "我们的节点回应游轮发送所用的时间，来自日志。",
                     "ja": "船の送信に対する私たちのノードの応答時間（ログブックより）。"}))
    files = []
    for path, im, cap in out:
        im.save(path, optimize=True)
        files.append((path, cap))
    return files


def demo(outdir: str) -> None:
    """The charts of the first article (MS Dry Run, 4 November 2026), from its logbook and the relay's log."""
    os.makedirs(outdir, exist_ok=True)
    facts = {"ship": "MS Dry Run", "date": "Wednesday, 4 November 2026", "accepted in all": 122, "refused in all": 8,
             "refusals logged without any answer from the node (a timeout, counted as refusal by the old rule)": 8,
             "stops skipped": 117, "landed": {"transactions planned": 247}, "sends per 10 minutes": [44, 39, 36, 12],
             "first send": "16:00", "last send": "16:33",
             "sends at half pace because the testnet looked strained": 123, "sends logged": 131}
    for path, _ in visit_charts(facts, os.path.join(outdir, "dryrun")):
        print("made", path)
    im = bars([2, 8, 2], ["4 Nov\n10:00", "4 Nov 16:00\nship in port", "5 Nov\n10:00"],
              "Our node slows down when the ship sends", "sends our node did not answer within 20 s, per hour, German time (all other hours: 0)",
              accent=[1])
    p = os.path.join(outdir, "dryrun-timeouts.png")
    im.save(p, optimize=True)
    print("made", p)


if __name__ == "__main__":
    if sys.argv[1:2] == ["hero"] and len(sys.argv) == 6:
        hero(sys.argv[2], sys.argv[3], json.load(open(sys.argv[4])).get("card"), json.load(open(sys.argv[4])).get("ship", "expedition"), sys.argv[5])
    elif sys.argv[1:2] == ["desk"] and len(sys.argv) == 4:
        c = json.load(open(sys.argv[2]))
        desk_hero(c.get("card"), sys.argv[3], stats=c.get("stats"), kicker=c.get("kicker", ""))
    elif sys.argv[1:2] == ["demo"] and len(sys.argv) == 3:
        demo(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(2)

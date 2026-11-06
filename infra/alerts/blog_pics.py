"""Pictures for the Tau HUD blog: a hero picture made from the island's own painting (cruise_pic.py, the painting the
game shows, with the painted ship and a card that says at a glance why the article matters) and charts drawn from
the numbers the article was written from, in the site's look (near-black, white, one green accent).

  python blog_pics.py hero <art dir> <ships dir> <card.json> <out.jpg>
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
            for j, part in enumerate(wrap(od, str(label), font(21, 500), tw - 36)[:2]):
                od.text((x + 20, y + 88 + j * 26), part, font=font(21, 500), fill=(190, 196, 204, 255))
        pic = Image.alpha_composite(pic, over)
    pic.convert("RGB").save(out, quality=90)
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
    if isinstance(left, dict) and left.get("minutes in port") is not None:
        out.append((f"{left['minutes in port']}/{facts.get('minutes planned in port', 90)}", "minutes in port"))
    acc = facts.get("accepted in all")
    if acc is not None:
        out.append((str(acc), "accepted by the node"))
    una = (facts.get("sends our node did not answer in time (not refusals)") or 0) + \
        (facts.get("refusals logged without any answer from the node (a timeout, counted as refusal by the old rule)") or 0)
    if una:
        out.append((str(una), "no answer in time"))
    ref = (facts.get("refused in all") or 0) - (facts.get("refusals logged without any answer from the node (a timeout, counted as refusal by the old rule)") or 0)
    out.append((str(max(0, ref)), "refused by the node"))
    if facts.get("bookings checked after the visit") and len(out) < 4:
        out.append((str(facts["bookings checked after the visit"] - (facts.get("bookings the chain had not paid out") or 0)), "bookings paid out"))
    return out[:4]


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
        parts = [("accepted by the node", acc, OK), ("no answer in time", una + old, AMBER),
                 ("refused by the node", ref - old, (255, 77, 109)), ("skipped", skip, (92, 92, 100))]
        t = f"{acc} of {plan} planned stops went through" if plan else f"{acc} stops went through"
        sub = "refused by the node: none" if ref - old <= 0 else f"refused by the node: {ref - old}"
        out.append((base + "-stops.png", split([p for p in parts if p[1] > 0], t, f"{facts.get('ship') or 'The ship'}, {facts.get('date', '')} · {sub}"),
                    {"en": "Where the planned stops went, from the ship's logbook.", "zh": "计划的停靠去了哪里，来自游轮日志。",
                     "ja": "計画された立ち寄りの行方（船のログブックより）。"}))
    per = facts.get("sends per 10 minutes") or []
    if len(per) > 1:
        labels = [f"{i * 10}–{i * 10 + 10}\nmin" for i in range(len(per))]
        half, logged = facts.get("sends at half pace because the testnet looked strained"), facts.get("sends logged")
        sub = (f"{half} of {logged} sends went out at half pace (testnet marked strained)" if half and logged
               else f"first send {facts.get('first send', '')}, last {facts.get('last send', '')}")
        out.append((base + "-pace.png", bars(per, labels, f"At most {max(per)} sends per 10 minutes, of 120 allowed", sub,
                                             cap=120, cap_label="allowed: 120 per 10 minutes"),
                    {"en": "The ship's pace in port, sends per 10 minutes.", "zh": "游轮在港口的速度：每 10 分钟的发送数。",
                     "ja": "港での船のペース：10 分ごとの送信数。"}))
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
    elif sys.argv[1:2] == ["demo"] and len(sys.argv) == 3:
        demo(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(2)

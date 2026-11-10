"""The White Rabbit Key island as the game shows it right now, for the posts: the live painting (index.json "scenes"
"island" in the art folder, the very file tauhud.com/rabbit/ loads), framed as the game frames its whole world, 1600x900.

  python island_pic.py <art dir with index.json> <out.jpg> [card.json]

Never the drawn plates of the first days or a screenshot in the repo (assets/shots/rabbit.png showed the drawn island
of October on X until 7 November 2026). card.json: {"card": [title, line, ..., accent line]} as in cruise_pic.py."""
from __future__ import annotations

import json
import os
import sys

from PIL import Image, ImageDraw

import cruise_pic


def painting(art: str) -> str:
    """The path of the island painting the game shows now; FileNotFoundError when there is none."""
    sc = json.load(open(os.path.join(art, "index.json"))).get("scenes", {})
    if not sc.get("island"):
        raise FileNotFoundError("no painted island in " + art)
    path = os.path.join(art, sc["island"])
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return path


def wrap(d: ImageDraw.ImageDraw, text: str, f, width: float) -> list[str]:
    out, line = [], ""
    for w in text.split():
        t = (line + " " + w).strip()
        if line and d.textlength(t, font=f) > width:
            out.append(line); line = w
        else:
            line = t
    return out + ([line] if line else [])


def small_card(pic: Image.Image, lines: list[str]) -> Image.Image:
    """The story big (title, up to two lines, readable on a phone), then the lines, accent line last, in a dark card in
    the lower left corner (sea in every painting so far), the island itself in view; the site's card colours."""
    title, *rest = lines
    body, accent = (rest[:-1], rest[-1]) if rest else ([], "")
    ft, fb, fa = cruise_pic.font(64), cruise_pic.font(30, 500), cruise_pic.font(28)
    d0 = ImageDraw.Draw(pic)
    heads = wrap(d0, title, ft, 1000)[:2]
    wid = max([d0.textlength(t, font=ft) for t in heads] + [d0.textlength(t, font=fb) for t in body] + [d0.textlength(accent, font=fa)])
    hgt = 28 + 76 * len(heads) + 10 + 42 * len(body) + (48 if accent else 0) + 22
    x0, y1 = 40, pic.height - 40
    y0 = y1 - hgt
    over = Image.new("RGBA", pic.size); d = ImageDraw.Draw(over)
    d.rounded_rectangle([x0, y0, x0 + wid + 64, y1], radius=18, fill=(8, 12, 24, 230))
    y = y0 + 24
    for t in heads:
        d.text((x0 + 32, y), t, font=ft, fill=(245, 245, 245, 255)); y += 76
    y += 10
    for t in body:
        d.text((x0 + 32, y), t, font=fb, fill=(205, 214, 222, 255)); y += 42
    if accent:
        d.text((x0 + 32, y + 8), accent, font=fa, fill=(120, 220, 140, 255))
    return Image.alpha_composite(pic, over)


def make(art: str, out: str, card: list[str] | None = None) -> str:
    """The whole island (the game's 1600x900 world window, a wide painting cropped in the middle as scene.js does),
    a small card in the lower left when given; a JPEG under 1 MB, well within X's 5 MB."""
    im = Image.open(painting(art)).convert("RGB")
    pic = cruise_pic.island_view(im, 0, 0, 1).convert("RGBA")
    if card:
        pic = small_card(pic, card)
    tmp = out + ".part"
    pic.convert("RGB").save(tmp, "JPEG", quality=88, optimize=True)
    os.replace(tmp, out)   # a reader (Caddy) never sees half a picture
    return out


if __name__ == "__main__":
    lines = json.load(open(sys.argv[3])).get("card") if len(sys.argv) > 3 else None
    print("made", make(sys.argv[1], sys.argv[2], lines), "from", painting(sys.argv[1]))

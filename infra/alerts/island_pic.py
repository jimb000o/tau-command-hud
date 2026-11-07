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


def small_card(pic: Image.Image, lines: list[str]) -> Image.Image:
    """Title, lines, accent line last, in a compact dark card in the lower left corner (sea in every painting so far),
    so the island itself stays in view; the site's card colours (cruise_pic.card)."""
    title, *rest = lines
    body, accent = (rest[:-1], rest[-1]) if rest else ([], "")
    ft, fb, fa = cruise_pic.font(36), cruise_pic.font(24, 500), cruise_pic.font(22)
    d0 = ImageDraw.Draw(pic)
    wid = max([d0.textlength(title, font=ft)] + [d0.textlength(t, font=fb) for t in body] + [d0.textlength(accent, font=fa)])
    hgt = 26 + 50 + 34 * len(body) + (40 if accent else 0) + 18
    x0, y1 = 40, pic.height - 40
    y0 = y1 - hgt
    over = Image.new("RGBA", pic.size); d = ImageDraw.Draw(over)
    d.rounded_rectangle([x0, y0, x0 + wid + 56, y1], radius=16, fill=(8, 12, 24, 225))
    y = y0 + 22
    d.text((x0 + 28, y), title, font=ft, fill=(242, 242, 242, 255)); y += 52
    for t in body:
        d.text((x0 + 28, y), t, font=fb, fill=(205, 214, 222, 255)); y += 34
    if accent:
        d.text((x0 + 28, y + 6), accent, font=fa, fill=(120, 220, 140, 255))
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

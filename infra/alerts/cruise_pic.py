"""A cruise ship announcement picture, made from the island's own painting (the one the game shows) and the painted
ship of rabbit/art/ships, placed where the game anchors it:

  python cruise_pic.py <art dir with index.json> <ships dir> <texts.json> <out.jpg>

The ship sits at the layout's anchor exactly as rabbit/scene.js draws it at anchor (bow to the west, mirrored, the same
waterline transform), the view is a close crop of the island around it, and a card with the json's "card" lines
(title, line, line, accent line) sits in the upper left. "ship_scale" draws the ship that many times larger than the
game does (3 = 200% larger), still at the anchor. "ship" in the json picks the painting (expedition, liner or pirate;
the pirate ship is MS Dry Run's painting darkened with a black flag until a pirate.webp of its own exists, as in the game)."""
import json, math, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1600, 900            # the picture
WW, WH = 1600, 900          # the game's world (scene.js)
ANCHOR = (1395, 780)        # scene.js SPOT.anchor, when the layout has none
ZOOM = 2.3                  # world units to the picture: the island's eastern shore and the ship
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def font(size, weight=700):
    for p in [os.path.join(FONTS, "Sora.ttf"), "/app/fonts/Sora.ttf"]:
        if os.path.exists(p):
            f = ImageFont.truetype(p, size)
            try:
                f.set_variation_by_axes([weight])
            except Exception:
                pass
            return f
    return ImageFont.load_default(size)


def island_view(im, x0, y0, z):
    """The world window [x0, x0+W/z] x [y0, y0+H/z], drawn as scene.js draws the painting: a wide one (ratio over 1.9)
    at the world's height reaching past its sides, any other one covering the world, cropped in the middle."""
    ar = im.width / im.height
    if ar > 1.9:
        k = im.height / WH; e = (WH * ar - WW) / 2; ox, oy = -e, 0.0
    else:
        k = max(im.width / WW, im.height / WH); ox = (WW - im.width / k) / 2; oy = (WH - im.height / k) / 2
    box = ((x0 - ox) * k, (y0 - oy) * k, (x0 + W / z - ox) * k, (y0 + H / z - oy) * k)
    return im.resize((W, H), Image.LANCZOS, box=box)


def world_bounds(im):
    ar = im.width / im.height
    e = (WH * ar - WW) / 2 if ar > 1.9 else 0
    return -e, WW + e


def place_ship(pic, ship, m, anchor, x0, y0, z, big=1.0):
    """scene.js boatTransform at anchor: translate to the anchor, mirror (bow west), scale to m.length world units along
    the stern-bow line, turn that line level, centre on its middle."""
    (sx, sy), (bx, by) = m["stern"], m["bow"]
    dx, dy = bx - sx, by - sy
    s = big * m["length"] / math.hypot(dx, dy)
    cx, cy = (sx + bx) / 2, (sy + by) / 2
    phi = -math.atan2(dy, dx)
    c, n = math.cos(phi), math.sin(phi)
    # forward, ship pixel p -> picture pixel: z * (anchor + diag(-1,1) * s * R(phi) * (p - c) - (x0, y0))
    a, b = -z * s * c, z * s * n
    d, e = z * s * n, z * s * c
    tx, ty = z * (anchor[0] - x0), z * (anchor[1] - y0)
    # the inverse, picture pixel -> ship pixel, which PIL wants
    det = a * e - b * d
    ia, ib, id_, ie = e / det, -b / det, -d / det, a / det
    coeffs = (ia, ib, -(ia * tx + ib * ty) + cx, id_, ie, -(id_ * tx + ie * ty) + cy)
    shadow = Image.new("RGBA", (W, H)); sd = ImageDraw.Draw(shadow)
    L = m["length"] * z * big
    ax, ay = tx + 4 * z * big, ty + 4 * z * big
    sd.ellipse([ax - L * 0.56, ay - 7 * z * big, ax + L * 0.56, ay + 7 * z * big], fill=(10, 30, 45, 56))
    pic = Image.alpha_composite(pic, shadow.filter(ImageFilter.GaussianBlur(3 * z)))
    layer = ship.transform((W, H), Image.AFFINE, coeffs, resample=Image.BICUBIC)
    return Image.alpha_composite(pic, layer)


def crew_aboard(ship, m, ships, frame="a"):
    """The painted crew on the ship's deck, as the game stands them (scene.js crew): the sheet named by the ship's
    "crew" entry of ships/crew-<kind>.json, one figure for each "deck" point of the ship's manifest and the captain
    at "captain", each with a soft shadow under the feet, sorted by their feet so the nearer stand in front. The
    ship comes back as it was when there is no crew."""
    deck = m.get("deck")
    try:
        cm = json.load(open(os.path.join(ships, "crew-%s.json" % m.get("crew", "pirate"))))
        sheet = Image.open(os.path.join(ships, cm["src"])).convert("RGBA")
    except (OSError, ValueError, KeyError):
        return ship
    if not deck or not cm.get("figures"):
        return ship
    (sx, sy), (bx, by) = m["stern"], m["bow"]
    k = math.hypot(bx - sx, by - sy) / m["length"] / cm["unit"]   # sheet pixels -> ship pixels
    cw, ch = cm["cell"]
    who = [(pt, cm["figures"][i % len(cm["figures"])]) for i, pt in enumerate(deck)]
    cap = (cm.get("guides") or {}).get(m.get("crew", "pirate"))
    if cap and m.get("captain"):
        who.append((m["captain"], cap))
    out = ship.copy()
    for (x, y), f in sorted(who, key=lambda w: w[0][1]):
        c = f[frame]
        cell = sheet.crop(((c % cm["cols"]) * cw, (c // cm["cols"]) * ch, (c % cm["cols"] + 1) * cw, (c // cm["cols"] + 1) * ch))
        w, h = max(1, round(cw * k)), max(1, round(ch * k))
        fig = cell.convert("RGBa").resize((w, h), Image.LANCZOS).convert("RGBA")
        sw = (f.get("sw") or 3) * k * cm["unit"]
        shadow = Image.new("RGBA", out.size); ImageDraw.Draw(shadow).ellipse([x + sw * 0.15 - sw, y - sw * 0.34, x + sw * 0.15 + sw, y + sw * 0.34], fill=(20, 34, 40, 60))
        out.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(1)))
        out.alpha_composite(fig, (round(x - f["foot"][0] * k), round(y - f["foot"][1] * k)))
    return out


def pirate_stand_in(m, ship):
    """MS Dry Run's painting as the pirates' Black Sequence: darkened like tarred wood, a black flag with three white
    chain links on a pole above the funnel (rabbit/scene.js standIn and blackFlag); the manifest moved with the canvas."""
    from PIL import ImageEnhance
    k = math.hypot(m["bow"][0] - m["stern"][0], m["bow"][1] - m["stern"][1]) / m["length"]   # sprite pixels per world unit
    top = int(26 * k)
    dark = ImageEnhance.Contrast(ImageEnhance.Color(ImageEnhance.Brightness(ship).enhance(0.42)).enhance(0.45)).enhance(1.15)
    dark.putalpha(ship.getchannel("A"))
    im = Image.new("RGBA", (ship.width, ship.height + top), (0, 0, 0, 0))
    im.paste(dark, (0, top), dark)
    x, y = m["funnel"][0], m["funnel"][1] + top
    d = ImageDraw.Draw(im)
    h, w, f = 15 * k, 13 * k, 8 * k
    d.line([(x, y), (x, y - h - f)], fill=(34, 48, 58, 255), width=max(2, int(1.2 * k)))
    d.polygon([(x, y - h - f), (x + w, y - h - f), (x + w, y - h), (x, y - h)], fill=(18, 20, 22, 255), outline=(34, 48, 58, 255))
    for i in range(3):
        cx, cy = x + w * (0.26 + i * 0.24), y - h - f / 2
        d.ellipse([cx - 2.1 * k, cy - 1.3 * k, cx + 2.1 * k, cy + 1.3 * k], outline=(242, 239, 230, 255), width=max(1, int(0.9 * k)))
    mm = {**m, "stern": [m["stern"][0], m["stern"][1] + top], "bow": [m["bow"][0], m["bow"][1] + top]}
    mm.pop("funnel", None)
    return mm, im


def card(pic, lines):
    """Title, body lines, accent line last. A body line starting with "## " is a small heading (a gap above it),
    one starting with "- " a point under it."""
    title, *rest = lines
    body, accent = (rest[:-1], rest[-1]) if rest else ([], "")
    ft, fb, fh, fa = font(46), font(26, 500), font(22), font(26)
    d0 = ImageDraw.Draw(pic)
    show = lambda t: "•  " + t[2:] if t.startswith("- ") else t[3:].upper() if t.startswith("## ") else t
    fnt = lambda t: fh if t.startswith("## ") else fb
    step = lambda t: 54 if t.startswith("## ") else 40
    wid = max([d0.textlength(title, font=ft)] + [d0.textlength(show(t), font=fnt(t)) for t in body] + [d0.textlength(accent, font=fa)])
    hgt = 34 + 64 + sum(step(t) for t in body) + (50 if accent else 0) + 18
    over = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(over)
    d.rounded_rectangle([56, 56, 56 + wid + 72, 56 + hgt], radius=18, fill=(8, 12, 24, 225))
    y = 56 + 30
    d.text((92, y), title, font=ft, fill=(242, 242, 242, 255)); y += 66
    for t in body:
        if t.startswith("## "):
            y += 14; d.text((92, y), show(t), font=fh, fill=(120, 220, 140, 255)); y += 40
        else:
            d.text((92, y), show(t), font=fb, fill=(205, 214, 222, 255)); y += 40
    if accent:
        d.text((92, y + 10), accent, font=fa, fill=(150, 160, 170, 255))
    return Image.alpha_composite(pic, over)


def main(art, ships, texts, out):
    idx = json.load(open(os.path.join(art, "index.json")))
    sc = idx.get("scenes", {})
    if "island" not in sc:
        sys.exit("no painted island in " + art)
    t = json.load(open(texts))
    kind = t.get("ship", "expedition")
    man = json.load(open(os.path.join(ships, "ships.json")))
    if kind == "pirate" and "pirate" not in man:
        m, ship = pirate_stand_in(man["expedition"], Image.open(os.path.join(ships, man["expedition"]["src"])).convert("RGBA"))
    else:
        m = man[kind]
        ship = crew_aboard(Image.open(os.path.join(ships, m["src"])).convert("RGBA"), m, ships)
    im = Image.open(os.path.join(art, sc["island"])).convert("RGB")
    anchor = tuple((idx.get("layout") or {}).get("anchor") or ANCHOR)
    lo, hi = world_bounds(im)
    vw, vh = W / ZOOM, H / ZOOM
    big = float(t.get("ship_scale", 1))   # the ship larger than the game draws it, so it reads on a phone
    x0 = min(max(anchor[0] - (0.68 if big <= 1 else 0.6) * vw, lo), hi - vw)
    y0 = min(max(anchor[1] - 0.72 * vh, 0), WH - vh)
    pic = island_view(im, x0, y0, ZOOM).convert("RGBA")
    at = anchor
    if big > 1:   # a larger ship stays whole in the frame and lies a little further out at sea, off the beach
        L = m["length"] * ZOOM * big
        px = min(ZOOM * (anchor[0] - x0), W - L / 2 - 30)
        py = max(ZOOM * (anchor[1] - y0), H - 100)
        at = (x0 + px / ZOOM, y0 + py / ZOOM)
    pic = place_ship(pic, ship, m, at, x0, y0, ZOOM, big)
    if t.get("card"):
        pic = card(pic, t["card"])
    pic.convert("RGB").save(out, quality=90)
    print("made", out, "from", sc["island"], "and", m["src"], "at", anchor)


if __name__ == "__main__":
    main(*sys.argv[1:5])

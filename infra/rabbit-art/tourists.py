"""White Rabbit Key's cruise passengers on the island (rabbit/scene.js crowdItems): the painted figures, two frames
each, scaled to the island and laid out as one sheet with its manifest.

    python3 infra/rabbit-art/tourists.py FOLDER_OR_ZIP [--out rabbit/art/tourists] [--still p05 ...] [--size p03=0.95 ...]
                                         [--raw] [--partial]
    python3 infra/rabbit-art/tourists.py pirates.zip --set pirates     # the Black Sequence's crew -> rabbit/art/ships/crew-pirate.*

The folder (or the zip, anywhere in it) holds <id>-a and <id>-b for every figure below, as WebP or PNG, each on the
full painted canvas (1024 x 1536, the soles on the baseline y=1456, the figure round x=512), and metrics.json with each
figure's bodyHeight there (soles to the top of the head). Both frames of a figure are scaled as whole canvases by one
factor, its height on the island over its bodyHeight, so they line up to the pixel: nothing is trimmed or fitted on its
own. At the island painting's own resolution a grown-up is 38 px tall, p03 in his wheelchair and the girl p12 28 px,
the boy p04 26 px (TARGET); the guides' bodyHeight is smaller than the passengers', to leave room for their flags.
Frames come cut out on transparent, or still on their flat background, which is keyed out here as paint.py does; what
the cut left of the magenta key goes either way, also where the painter shaded it towards hot pink (between an arm and
the body). --raw takes the magenta originals in raw/ instead of the cut-outs. --still names figures whose second frame
jumps at the game's size: they stand still on their first until the pair is repaired. --partial builds without
missing figures. Where each figure touches the ground (soles, wheels, the tip of a stick) is measured for its contact
shadows. The sheet holds UNIT pixels to the world unit, sharp on a 4K screen zoomed in."""
import argparse
import io
import json
import os
import re
import sys
import zipfile

from PIL import Image, ImageChops, ImageFilter

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "rabbit", "art", "tourists")
UNIT = 5                    # sheet pixels to the world unit
PX_PER_UNIT = 2138 / 900    # the island painting's pixels to the world unit
ADULT_TARGET = 38           # a grown-up at the painting's resolution, soles to the top of the head (16 world units)
TARGET = {"p03": 28, "p04": 26, "p12": 28}
CANVAS, ANCHOR = (1024, 1536), (512, 1456)
BODY = {"p03": 950, "p04": 900, "p12": 960, "guide-dryrun": 1067, "guide-queen": 1066}   # if metrics.json is not there
ADULT_BODY = 1300
COLS = 12
MAGENTA = (255, 0, 255)
# the passengers as they are painted: how each is seen, and which way they look (-1 left, 1 right)
FIGURES = [("p01", "back", -1), ("p02", "back", -1), ("p03", "side", -1), ("p04", "back", -1),
           ("p05", "back", 1), ("p06", "back", 1), ("p07", "back", 1), ("p08", "back", 1),
           ("p09", "front", -1), ("p10", "front", -1), ("p11", "front", 1), ("p12", "front", 1),
           ("p13", "side", -1), ("p14", "side", -1), ("p15", "side", 1), ("p16", "side", 1)]
GUIDES = {"expedition": ("guide-dryrun", "front", 1), "liner": ("guide-queen", "front", -1)}   # MS Dry Run, Queen Mempool
# the pirates of the Black Sequence (--set pirates): they never land, the game stands them on their ship's deck
# (ships.json "pirate" deck points) and their captain at her place; one pirate for each trick the ship tries
CREW = [("k01", "back", -1), ("k02", "back", -1), ("k03", "back", 1), ("k04", "back", 1),
        ("k05", "front", -1), ("k06", "front", -1), ("k07", "front", 1), ("k08", "front", 1)]
CAPTAINS = {"pirate": ("captain-pirates", "front", -1)}
SETS = {"tourists": (FIGURES, GUIDES, "tourists", OUT),
        "pirates": (CREW, CAPTAINS, "crew-pirate", os.path.join(REPO, "rabbit", "art", "ships"))}


def key(name):
    """A picture's file name as the frame it holds, however it is spelt: p01-a.webp, P01_A.png, p1a.webp and
    p01-a-magenta.webp are all p1a."""
    n = re.sub(r"\.(webp|png)$", "", name.lower())
    n = re.sub(r"[^a-z0-9]", "", re.sub(r"magenta|original|cutout", "", n))
    return re.sub(r"(?<![0-9])0+(?=[0-9])", "", n)


def files(src, raw=False):
    """frame -> (where it lies, bytes) for every picture in the folder or the zip, wherever it lies in it (the cut-outs,
    or with raw the magenta originals in raw/; never the check pictures), and metrics.json if it is there."""
    out, metrics = {}, {}

    def take(path, read):
        parts = path.replace("\\", "/").lower().split("/")
        b, dirs = parts[-1], parts[:-1]
        if "__macosx" in dirs or "check" in dirs or b.startswith("."):
            return
        if b == "metrics.json" and "raw" not in dirs:
            metrics.update(json.loads(read()))
        elif b.endswith((".webp", ".png")) and ("raw" in dirs) == raw and key(b) not in out:
            out[key(b)] = (path, read())
    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as z:
            for n in sorted(z.namelist()):
                if not n.endswith("/"):
                    take(n, lambda n=n: z.read(n))
    else:
        for d, dirs, fs in os.walk(src):
            dirs.sort()
            for b in sorted(fs):
                p = os.path.join(d, b)
                take(os.path.relpath(p, src), lambda p=p: open(p, "rb").read())
    return out, metrics


def keyed(im, col):
    """How far each pixel is from the colour col, as alpha: 0 on it, 255 from a clear distance on (as paint.py)."""
    dr, dg, db = ImageChops.difference(im.convert("RGB"), Image.new("RGB", im.size, col)).split()
    d = ImageChops.add(ImageChops.add(dr, dg), db)   # it saturates at 255, which is past the edge anyway
    return d.point(lambda v: 0 if v < 90 else 255 if v > 170 else (v - 90) * 255 // 80)


def pink(im, a):
    """Hot pink the cut left in: saturated magenta-to-rose (295-345 degrees) in patches larger than a speck, and the
    pixel round them; crimson, coral and pink skin are other hues or far less saturated."""
    H, S, V = im.convert("RGB").convert("HSV").split()
    core = ImageChops.multiply(ImageChops.multiply(H.point(lambda v: 255 if 209 <= v <= 244 else 0), S.point(lambda v: 255 if v > 178 else 0)),
                               ImageChops.multiply(V.point(lambda v: 255 if v > 166 else 0), a.point(lambda v: 255 if v > 128 else 0)))
    core = core.filter(ImageFilter.BoxBlur(2)).point(lambda v: 255 if v >= 254 else 0)   # specks go ...
    return core.filter(ImageFilter.BoxBlur(3)).point(lambda v: 255 if v else 0)   # ... and the rest grows back, one pixel wider


def rgba(data):
    """The picture on transparent, and the share of the figure that was key colour left in: as it comes if it is cut
    out, else its flat background keyed out; magenta and its hot pink go either way, and the edge loses their tint."""
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    r, g, b, a = im.split()
    if a.getextrema()[0] == 255:
        W, H = im.size
        px = im.load()
        edge = sorted([px[x, 2][:3] for x in range(0, W, 7)] + [px[x, H - 3][:3] for x in range(0, W, 7)] +
                      [px[2, y][:3] for y in range(0, H, 7)] + [px[W - 3, y][:3] for y in range(0, H, 7)])
        a = keyed(im, edge[len(edge) // 2])
    solid = a.point(lambda v: 255 if v > 128 else 0)
    gone = ImageChops.lighter(keyed(im, MAGENTA).point(lambda v: 255 if v < 128 else 0), pink(im, a))
    held = ImageChops.multiply(solid, gone).histogram()[255] / max(1, solid.histogram()[255])
    a = ImageChops.darker(ImageChops.darker(a, keyed(im, MAGENTA)), ImageChops.invert(gone))
    # within a few pixels of the edge, a magenta tint turns grey; no other colour changes
    near = a.point(lambda v: 0 if v == 255 else 255).filter(ImageFilter.BoxBlur(3)).point(lambda v: 255 if v else 0)
    band = ImageChops.multiply(a.point(lambda v: 255 if v else 0), near)
    tint = ImageChops.darker(ImageChops.subtract(r, g).point(lambda v: 255 if v > 30 else 0),
                             ImageChops.subtract(b, g).point(lambda v: 255 if v > 30 else 0))
    g = Image.composite(ImageChops.lighter(g, ImageChops.add(r, b, 2.0, -40)), g, ImageChops.darker(band, tint))
    return Image.merge("RGBA", (r, g, b, a)), held


def contacts(im, body):
    """Where the figure touches the ground on its canvas: runs of columns whose lowest opaque pixel lies near the
    baseline (soles, also of a foot set further back, wheels, the tip of a stick; not a bag that hangs above it), each
    as [middle, lowest row, half its width]."""
    A = im.getchannel("A").point(lambda v: 255 if v > 128 else 0)
    top, tol, gap = int(ANCHOR[1] - 0.06 * body), max(4, round(0.05 * body)), max(3, round(0.015 * body))
    band = A.crop((0, top, A.width, min(A.height, ANCHOR[1] + 6)))
    w, h, data = band.width, band.height, band.tobytes()
    low = [max((y for y in range(h) if data[y * w + x]), default=-1) for x in range(w)]
    bottom = max(low)
    if bottom < 0:
        return []
    runs = []
    for x in range(w):
        if low[x] >= 0 and low[x] >= bottom - tol:
            if runs and x - runs[-1][1] <= gap:
                runs[-1][1] = x
                runs[-1][2] = max(runs[-1][2], low[x])
            else:
                runs.append([x, x, low[x]])
    return [[(x0 + x1) / 2, top + y, (x1 - x0 + 1) / 2] for x0, x1, y in runs]


def scaled(im, k):
    """The whole canvas scaled by k, premultiplied (so no dark halo), and the factors it came out with per axis."""
    w, h = max(1, round(im.width * k)), max(1, round(im.height * k))
    return im.convert("RGBa").resize((w, h), Image.LANCZOS).convert("RGBA"), w / im.width, h / im.height


def pair_change(a, b, legs):
    """How much changes between the two frames at the game's size: the share of the figure's pixels that change
    clearly, and the share of those below the row legs (the legs, which should stand still)."""
    d = ImageChops.difference(a.convert("RGBa"), b.convert("RGBa")).split()
    m = d[0]
    for c in d[1:]:
        m = ImageChops.lighter(m, c)
    m = m.point(lambda v: 255 if v > 40 else 0)
    fig = ImageChops.lighter(a.getchannel("A"), b.getchannel("A")).point(lambda v: 255 if v > 128 else 0)
    n = m.histogram()[255]
    low = m.crop((0, round(legs), m.width, m.height)).histogram()[255]
    return n / max(1, fig.histogram()[255]), low / max(1, n)


def build(src, out=None, still=(), size=None, partial=False, raw=False, what="tourists"):
    """The sheet and its manifest; returns the manifest, notes on what looks wrong, and per figure how tall it stands
    on the island (world units) and how much changes between its frames at that size."""
    size = size or {}
    figures, guides, sheet_name, out0 = SETS[what]
    out = out or out0
    pics, metrics = files(src, raw)
    if not metrics:
        print("note: no metrics.json, so the bodyHeights are the ones the prompt asked for")
    todo = [(i, v, f, None) for i, v, f in figures] + [(n, v, f, s) for s, (n, v, f) in guides.items()]
    got, notes, used, info = [], [], set(), {}
    for name, view, face, ship in todo:
        fr = {}
        for x in "ab":
            k = key(f"{name}-{x}")
            if k in pics:
                used.add(k)
                fr[x], held = rgba(pics[k][1])
                if fr[x].size != CANVAS:
                    sys.exit(f"{name}-{x}: {fr[x].size[0]}x{fr[x].size[1]}, not the full {CANVAS[0]}x{CANVAS[1]} canvas")
                if held > 0.002:
                    notes.append(f"{name}-{x}: {held:.1%} of the figure was key colour the cut left in, now keyed out")
        if len(fr) < 2:
            miss = f"{name}-a and {name}-b" if not fr else f"{name}-{'b' if 'a' in fr else 'a'}"
            if not partial:
                sys.exit(f"missing: {miss} (.webp or .png); --partial builds without")
            if not fr:
                notes.append(f"{name}: missing, left out")
                continue
            notes.append(f"{miss}: missing, so {name} stands still")
        m = metrics.get(name) or {}
        if m and (tuple(m.get("canvas", CANVAS)) != CANVAS or tuple(m.get("anchor", ANCHOR)) != ANCHOR):
            sys.exit(f"{name}: metrics.json puts it on another canvas or anchor ({m.get('canvas')}, {m.get('anchor')})")
        body = float(m.get("bodyHeight") or BODY.get(name, ADULT_BODY))
        px = TARGET.get(name, ADULT_TARGET) * size.get(name, 1.0)   # at the painting's resolution
        k = UNIT * px / PX_PER_UNIT / body
        a, kx, ky = scaled(fr.get("a", fr.get("b")), k)
        b = a if name in still or len(fr) < 2 else scaled(fr["b"], k)[0]
        change, low = pair_change(a, b, (ANCHOR[1] - 0.45 * body) * ky)
        if b is not a and low > 0.1:
            notes.append(f"{name}: {low:.0%} of what changes between -a and -b is in the legs, so it may jump")
        info[name] = {"tall": round(px / PX_PER_UNIT, 1), "change": round(change, 3), "low": round(low, 3), "still": b is a}
        cs = [[round(x * kx, 1), round(y * ky, 1), round(max(0.5, hw * kx), 1)] for x, y, hw in contacts(fr.get("a", fr.get("b")), body)]
        if not cs:
            sys.exit(f"{name}: nothing touches the ground")
        got.append((name, view, face, ship, a, b, [ANCHOR[0] * kx, ANCHOR[1] * ky], cs))
    if sum(1 for g in got if not g[3]) < min(6, len(figures)):
        sys.exit("too few figures for a group")
    cw = max(g[4].width for g in got) + 2
    ch = max(g[4].height for g in got) + 2
    cells = [c for g in got for c in ((g[4],) if g[5] is g[4] else (g[4], g[5]))]
    rows = -(-len(cells) // COLS)
    sheet = Image.new("RGBA", (cw * COLS, ch * rows), (0, 0, 0, 0))
    man = {"src": sheet_name + ".webp", "cols": COLS, "cell": [cw, ch], "unit": UNIT, "figures": [], "guides": {}}
    c = 0
    for name, view, face, ship, a, b, ft, cs in got:
        ia = c
        for im in (a,) if b is a else (a, b):
            sheet.paste(im, ((c % COLS) * cw + 1, (c // COLS) * ch + 1))   # cells never overlap: as they are, alpha and all
            c += 1
        entry = {"id": name, "view": view, "face": face, "a": ia, "b": ia if b is a else ia + 1,
                 "foot": [round(ft[0] + 1, 1), round(ft[1] + 1, 1)], "contacts": [[x + 1, y + 1, hw] for x, y, hw in cs]}
        if ship:
            man["guides"][ship] = entry
        else:
            man["figures"].append(entry)
    left = sorted(p for k, (p, _) in pics.items() if k not in used)
    if left:
        notes.append("not used: " + ", ".join(left))
    os.makedirs(out, exist_ok=True)
    buf = io.BytesIO()
    sheet.save(buf, "WEBP", lossless=True, quality=100, method=6)   # lossless: the two frames of a figure match to the pixel
    open(os.path.join(out, sheet_name + ".webp"), "wb").write(buf.getvalue())
    with open(os.path.join(out, sheet_name + ".json"), "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=1)
        fh.write("\n")
    return man, notes, info


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("src", help="the folder or zip with p01-a.webp ... guide-queen-b.webp and metrics.json")
    p.add_argument("--out", default=None, help="where the sheet goes (default: rabbit/art/tourists, or rabbit/art/ships for the pirates)")
    p.add_argument("--set", default="tourists", choices=sorted(SETS), help="tourists (default) or pirates: the crew of the Black Sequence, k01..k08 and captain-pirates")
    p.add_argument("--still", nargs="*", default=[], help="figures that stand still on their first frame")
    p.add_argument("--size", nargs="*", default=[], help="id=factor, e.g. p03=0.95")
    p.add_argument("--partial", action="store_true", help="leave out the figures that are missing")
    p.add_argument("--raw", action="store_true", help="take the magenta originals in raw/ instead of the cut-outs")
    a = p.parse_args(argv)
    size = {k: float(v) for k, v in (s.split("=", 1) for s in a.size)}
    man, notes, info = build(a.src, a.out, set(a.still), size, a.partial, a.raw, a.set)
    for n in notes:
        print("note:", n)
    for n, i in info.items():
        print(f"{n:13} {i['tall']:5} units  changes {i['change']:.1%} of the figure ({i['low']:.0%} of it in the legs)" + ("  still" if i["still"] else ""))
    print(f"{len(man['figures'])} figures and {len(man['guides'])} guides, cells {man['cell'][0]}x{man['cell'][1]} -> {a.out or SETS[a.set][3]}")


if __name__ == "__main__":
    main()

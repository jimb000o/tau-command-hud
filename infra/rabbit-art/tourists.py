"""White Rabbit Key's cruise passengers on the island (rabbit/scene.js crowdItems): the painted figures, two frames
each, cut out, brought to the island's scale and laid out as one sheet with its manifest.

    python3 infra/rabbit-art/tourists.py FOLDER_OR_ZIP [--out rabbit/art/tourists] [--size p03=0.95 ...] [--partial] [--raw]

The folder (or the zip, anywhere inside it) holds <id>-a and <id>-b for every figure below, as WebP or PNG (P01_A.png
or p1a.webp will do too): cut out on transparent, or still on their flat background, which is then keyed out here as
paint.py does with its figures; magenta that the cut left in goes either way, and the edge loses its tint. --raw takes
the magenta originals in raw/ instead of the cut-outs. The two frames of a figure share one canvas (if not, they are
lined up by their soles), and the second may differ from the first only where the gesture is: only what changed is
taken from the second, so a figure never jumps when it gestures. Everyone is painted at one scale (a grown-up about
ADULT_PX from the soles to the top of the head), which becomes ADULT_UNITS world units on the island, as the painting
measures it (loungers, doors and umbrellas: about 8.5 units to the metre). If the passengers came out larger or smaller
than asked, all are scaled to fit; one who is far off the others is named, for --size to correct. --partial builds
without the figures that are missing (a figure with one frame stands still). The sheet holds UNIT pixels to the world
unit, sharp on a 4K screen zoomed in; a thin ink edge round each figure keeps the painting's outline at the small size."""
import argparse
import io
import json
import os
import re
import statistics
import sys
import zipfile

from PIL import Image, ImageChops, ImageFilter

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "rabbit", "art", "tourists")
UNIT = 5                 # sheet pixels to the world unit: a grown-up is 80 px on the sheet
ADULT_PX = 1300          # a grown-up on the painted canvas, soles to the top of the head
ADULT_UNITS = 16         # ... and on the island
EXPECT = {"p03": 950, "p04": 900, "p12": 960}   # the others on the canvas: in his wheelchair, the boy of eight, the girl of ten
INK = (34, 48, 58)       # the painting's ink (#22303a)
EDGE = 0.55              # how dark the ink edge round a figure is
COLS = 12
MAGENTA = (255, 0, 255)
# the passengers as the prompt asks for them: how each is seen, and which way they look (-1 left, 1 right)
FIGURES = [("p01", "back", -1), ("p02", "back", -1), ("p03", "back", -1), ("p04", "back", -1),
           ("p05", "back", 1), ("p06", "back", 1), ("p07", "back", 1), ("p08", "back", 1),
           ("p09", "front", -1), ("p10", "front", -1), ("p11", "front", 1), ("p12", "front", 1),
           ("p13", "side", -1), ("p14", "side", -1), ("p15", "side", 1), ("p16", "side", 1)]
GUIDES = {"expedition": ("guide-dryrun", "front", -1), "liner": ("guide-queen", "front", -1)}   # MS Dry Run, Queen Mempool


def key(name):
    """A picture's file name as the frame it holds, however it is spelt: p01-a.webp, P01_A.png, p1a.webp and
    p01-a-magenta.webp are all p1a."""
    n = re.sub(r"\.(webp|png)$", "", name.lower())
    n = re.sub(r"[^a-z0-9]", "", re.sub(r"magenta|original|cutout", "", n))
    return re.sub(r"(?<![0-9])0+(?=[0-9])", "", n)


def files(src, raw=False):
    """frame -> (where it lies, bytes) for every picture in the folder or the zip, wherever it lies in it: the cut-outs,
    or with raw the magenta originals in raw/; never the check pictures."""
    out = {}

    def take(path, read):
        parts = path.replace("\\", "/").lower().split("/")
        b, dirs = parts[-1], parts[:-1]
        if b.endswith((".webp", ".png")) and not b.startswith(".") and "__macosx" not in dirs and "check" not in dirs \
                and ("raw" in dirs) == raw and key(b) not in out:
            out[key(b)] = (path, read())
    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as z:
            for n in sorted(z.namelist()):
                take(n, lambda n=n: z.read(n))
    else:
        for d, dirs, fs in os.walk(src):
            dirs.sort()
            for b in sorted(fs):
                p = os.path.join(d, b)
                take(os.path.relpath(p, src), lambda p=p: open(p, "rb").read())
    return out


def keyed(im, col):
    """How far each pixel is from the colour col, as alpha: 0 on it, 255 from a clear distance on (as paint.py)."""
    dr, dg, db = ImageChops.difference(im.convert("RGB"), Image.new("RGB", im.size, col)).split()
    d = ImageChops.add(ImageChops.add(dr, dg), db)   # it saturates at 255, which is past the edge anyway
    return d.point(lambda v: 0 if v < 90 else 255 if v > 170 else (v - 90) * 255 // 80)


def rgba(data):
    """The picture on transparent, and the share of the figure that was magenta left in: as it comes if it is cut
    out, else its flat background keyed out; magenta goes either way, and the edge loses the background's tint."""
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    r, g, b, a = im.split()
    if a.getextrema()[0] == 255:
        W, H = im.size
        px = im.load()
        edge = sorted([px[x, 2][:3] for x in range(0, W, 7)] + [px[x, H - 3][:3] for x in range(0, W, 7)] +
                      [px[2, y][:3] for y in range(0, H, 7)] + [px[W - 3, y][:3] for y in range(0, H, 7)])
        a = keyed(im, edge[len(edge) // 2])
    m = keyed(im, MAGENTA)
    solid = a.point(lambda v: 255 if v > 128 else 0)
    held = ImageChops.multiply(solid, m.point(lambda v: 255 if v < 128 else 0)).histogram()[255] / max(1, solid.histogram()[255])
    a = ImageChops.darker(a, m)
    # within a few pixels of the edge, a magenta tint turns grey; no other colour changes
    near = a.point(lambda v: 0 if v == 255 else 255).filter(ImageFilter.BoxBlur(3)).point(lambda v: 255 if v else 0)   # 3 px round what is not opaque
    band = ImageChops.multiply(a.point(lambda v: 255 if v else 0), near)
    tint = ImageChops.darker(ImageChops.subtract(r, g).point(lambda v: 255 if v > 30 else 0),
                             ImageChops.subtract(b, g).point(lambda v: 255 if v > 30 else 0))
    g = Image.composite(ImageChops.lighter(g, ImageChops.add(r, b, 2.0, -40)), g, ImageChops.darker(band, tint))
    return Image.merge("RGBA", (r, g, b, a)), held


def sole(im):
    """Where a figure stands, in its own pixels: the middle of its lowest opaque rows (soles, wheels), and how wide
    those rows are."""
    a = im.getchannel("A").point(lambda v: 255 if v > 128 else 0)
    bb = a.getbbox()
    if not bb:
        return None
    rows = max(2, (bb[3] - bb[1]) // 25)
    strip = a.crop((bb[0], bb[3] - rows, bb[2], bb[3]))
    xs = [i % strip.width for i, v in enumerate(strip.tobytes()) if v]
    return bb[0] + sum(xs) / len(xs), bb[3] - 1, max(xs) - min(xs) + 1


def align(a, b):
    """a and b on one canvas with their soles on the same point, and how far b had to move."""
    fa, fb = sole(a), sole(b)
    dx, dy = round(fa[0] - fb[0]), fa[1] - fb[1]
    if a.size == b.size and not dx and not dy:
        return a, b, (0, 0)
    L, T = min(0, dx), min(0, dy)
    size = (max(a.width, b.width + dx) - L, max(a.height, b.height + dy) - T)
    A, B = Image.new("RGBA", size, (0, 0, 0, 0)), Image.new("RGBA", size, (0, 0, 0, 0))
    A.paste(a, (-L, -T))
    B.paste(b, (dx - L, dy - T))
    return A, B, (dx, dy)


def gesture(a, b):
    """a and b with only what changed taken from b: the changed pixels, a little widened and with a soft edge, both
    through the same premultiplied round, so that what did not change is the same to the pixel. Also how much
    changed: the share of the figure, and the share of its box that the box round the changes takes."""
    pa, pb = a.convert("RGBa"), b.convert("RGBa")   # premultiplied: a colour under full transparency is no change
    bands = ImageChops.difference(pa, pb).split()
    m = bands[0]
    for c in bands[1:]:
        m = ImageChops.lighter(m, c)
    m = m.point(lambda v: 255 if v > 48 else 0).filter(ImageFilter.BoxBlur(2)).point(lambda v: 255 if v >= 254 else 0)   # specks of noise are no gesture
    a2 = pa.convert("RGBA")
    box = m.getbbox()
    if not box:
        return a2, a2.copy(), 0.0, 0.0
    fig = ImageChops.lighter(a.getchannel("A"), b.getchannel("A")).point(lambda v: 255 if v > 128 else 0)
    fb = fig.getbbox() or (0, 0, a.width, a.height)
    share = m.histogram()[255] / max(1, fig.histogram()[255])
    span = (box[2] - box[0]) * (box[3] - box[1]) / max(1, (fb[2] - fb[0]) * (fb[3] - fb[1]))
    r = max(3, a.height // 100)
    soft = m.filter(ImageFilter.BoxBlur(r)).point(lambda v: 255 if v else 0).filter(ImageFilter.GaussianBlur(r / 3))
    return a2, Image.composite(pb, pa, soft).convert("RGBA"), share, span


def small(im, k):
    """Scaled down by k (premultiplied, so no dark halo), with a thin ink edge round the silhouette."""
    w, h = max(1, round(im.width * k)), max(1, round(im.height * k))
    s = im.convert("RGBa").resize((w, h), Image.LANCZOS).convert("RGBA")
    alpha = s.getchannel("A")
    edge = Image.eval(alpha.filter(ImageFilter.MaxFilter(3)), lambda v: int(v * EDGE))
    out = Image.new("RGBA", s.size, INK + (0,))
    out.putalpha(edge)
    out.alpha_composite(s)
    return out


def foot(im):
    """Where the figure stands on the sheet, and half the width of its base in world units for the shadow."""
    s = sole(im)
    if not s:
        sys.exit("an empty figure")
    return [round(s[0], 1), s[1]], round(min(6.0, max(2.0, s[2] / 2 / UNIT * 1.25)), 2)


def tall(im):
    bb = im.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox()
    return bb[3] - bb[1] if bb else 0


def build(src, out=OUT, size=None, partial=False, raw=False):
    """The sheet and its manifest from the painted frames; returns the manifest, notes on what looks wrong, and how
    tall each figure stands on the island (world units)."""
    size = size or {}
    pics = files(src, raw)
    todo = [(i, v, f, None) for i, v, f in FIGURES] + [(n, v, f, s) for s, (n, v, f) in GUIDES.items()]
    got, notes, used = [], [], set()
    for name, view, face, ship in todo:
        fr = {}
        for x in "ab":
            k = key(f"{name}-{x}")
            if k in pics:
                used.add(k)
                fr[x], held = rgba(pics[k][1])
                if held > 0.005:
                    notes.append(f"{name}-{x}: {held:.1%} of the figure was magenta, now keyed out (holes the cut left, or magenta clothes?)")
        if len(fr) < 2:
            miss = f"{name}-a and {name}-b" if not fr else f"{name}-{'b' if 'a' in fr else 'a'}"
            if not partial:
                sys.exit(f"missing: {miss} (.webp or .png); --partial builds without")
            if not fr:
                notes.append(f"{name}: missing, left out")
                continue
            notes.append(f"{miss}: missing, so {name} stands still")
            fr["a"] = fr["b"] = fr.get("a", fr.get("b"))
        a, b = fr["a"], fr["b"]
        if a.size != b.size:
            a, b, d = align(a, b)
            notes.append(f"{name}: -a and -b are not on one canvas, lined up by the soles")
        a2, b2, share, span = gesture(a, b)
        if not share and fr["a"] is not fr["b"]:
            notes.append(f"{name}: no gesture found in -b")
        elif share > 0.45 or span > 0.7:
            A, B, d = align(a, b)
            if d != (0, 0):
                a3, b3, s3, sp3 = gesture(A, B)
                if s3 <= 0.45 and sp3 <= 0.7:
                    notes.append(f"{name}: -b stood {d[0]},{d[1]} px off -a, lined up by the soles")
                    a2, b2, share = a3, b3, 0
            if share:
                notes.append(f"{name}: -b differs almost everywhere ({share:.0%} of the figure), so it may jump when it gestures")
        got.append((name, view, face, ship, a2, b2))
    ratio = {n: tall(a) / EXPECT.get(n, ADULT_PX) for n, _, _, ship, a, _ in got if not ship}
    if len(ratio) < 6:
        sys.exit(f"only {len(ratio)} passengers: too few for a group")
    R = statistics.median(ratio.values())
    fit = 1.0
    if abs(R - 1) > 0.1:
        fit = 1 / R
        notes.append(f"the passengers came out {R:.2f} times the asked size (a grown-up {R * ADULT_PX:.0f} px), so all are scaled to fit")
    for n, q in ratio.items():
        if n not in size and not 0.87 < q / R < 1.15:
            notes.append(f"{n}: {q / R:.2f} times the size of the others; unless that is its hat or its pose, --size {n}={R / q:.2f}")
    frames, heights = [], {}
    for name, view, face, ship, a, b in got:
        bb = a.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
        bb2 = b.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
        if not bb:
            sys.exit(f"{name}: nothing on the picture")
        if bb2:
            bb = (min(bb[0], bb2[0]), min(bb[1], bb2[1]), max(bb[2], bb2[2]), max(bb[3], bb2[3]))
        k = UNIT * ADULT_UNITS / ADULT_PX * fit * size.get(name, 1.0)
        m = 8
        crop = (max(0, bb[0] - m), max(0, bb[1] - m), min(a.width, bb[2] + m), min(a.height, bb[3] + m))
        sa, sb = small(a.crop(crop), k), small(b.crop(crop), k)
        ft, sw = foot(sa)
        heights[name] = round(tall(a) * k / UNIT, 1)
        frames.append((name, view, face, ship, sa, sb, ft, sw))
    cw = max(max(f[4].width, f[5].width) for f in frames) + 2
    ch = max(max(f[4].height, f[5].height) for f in frames) + 2
    rows = -(-2 * len(frames) // COLS)
    sheet = Image.new("RGBA", (cw * COLS, ch * rows), (0, 0, 0, 0))
    man = {"src": "tourists.webp", "cols": COLS, "cell": [cw, ch], "unit": UNIT, "figures": [], "guides": {}}
    for i, (name, view, face, ship, sa, sb, ft, sw) in enumerate(frames):
        for j, im in enumerate((sa, sb)):
            c = 2 * i + j
            sheet.paste(im, ((c % COLS) * cw + 1, (c // COLS) * ch + 1))   # cells never overlap: as they are, alpha and all
        entry = {"id": name, "view": view, "face": face, "a": 2 * i, "b": 2 * i + 1, "foot": [ft[0] + 1, ft[1] + 1], "sw": sw}
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
    open(os.path.join(out, "tourists.webp"), "wb").write(buf.getvalue())
    with open(os.path.join(out, "tourists.json"), "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=1)
        fh.write("\n")
    return man, notes, heights


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("src", help="the folder or zip with p01-a.webp ... guide-queen-b.webp")
    p.add_argument("--out", default=OUT)
    p.add_argument("--size", nargs="*", default=[], help="id=factor, e.g. p03=0.95")
    p.add_argument("--partial", action="store_true", help="leave out the figures that are missing")
    p.add_argument("--raw", action="store_true", help="take the magenta originals in raw/ instead of the cut-outs")
    a = p.parse_args(argv)
    size = {k: float(v) for k, v in (s.split("=", 1) for s in a.size)}
    man, notes, heights = build(a.src, a.out, size, a.partial, a.raw)
    for n in notes:
        print("note:", n)
    print("tall on the island (units; a grown-up is %d):" % ADULT_UNITS, " ".join(f"{k} {v}" for k, v in heights.items()))
    print(f"{len(man['figures'])} passengers and {len(man['guides'])} guides, cells {man['cell'][0]}x{man['cell'][1]} -> {a.out}")


if __name__ == "__main__":
    main()

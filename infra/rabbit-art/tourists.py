"""White Rabbit Key's cruise passengers on the island (rabbit/scene.js crowdItems): the painted figures, two frames
each, cut out, brought to the island's scale and laid out as one sheet with its manifest.

    python3 infra/rabbit-art/tourists.py FOLDER_OR_ZIP [--out rabbit/art/tourists] [--size p03=0.95 ...]

The folder (or the zip, anywhere inside it) holds <id>-a and <id>-b for every figure below, as WebP or PNG: cut out
on transparent, or still on their flat magenta, which is then keyed out here as paint.py does with its figures. The
two frames of a figure share one canvas, and the second may differ from the first only where the gesture is: what
else moved is put back from the first, so a figure never jumps when it gestures. Everyone is painted at one scale (a
grown-up about ADULT_PX from the soles to the top of the head), which becomes ADULT_UNITS world units on the island,
as the painting measures it (loungers, doors and umbrellas: about 8.5 units to the metre). --size corrects one
figure that came out too large or too small. The sheet holds UNIT pixels to the world unit, sharp on a 4K screen
zoomed in; a thin ink edge round each figure keeps the painting's outline at the small size."""
import argparse
import io
import json
import os
import sys
import zipfile

from PIL import Image, ImageChops, ImageFilter

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "rabbit", "art", "tourists")
UNIT = 5                 # sheet pixels to the world unit: a grown-up is 80 px on the sheet
ADULT_PX = 1300          # a grown-up on the painted canvas, soles to the top of the head
ADULT_UNITS = 16         # ... and on the island
INK = (34, 48, 58)       # the painting's ink (#22303a)
EDGE = 0.55              # how dark the ink edge round a figure is
COLS = 12
# the passengers as the prompt asks for them: how each is seen, and which way they look (-1 left, 1 right)
FIGURES = [("p01", "back", -1), ("p02", "back", -1), ("p03", "back", -1), ("p04", "back", -1),
           ("p05", "back", 1), ("p06", "back", 1), ("p07", "back", 1), ("p08", "back", 1),
           ("p09", "front", -1), ("p10", "front", -1), ("p11", "front", 1), ("p12", "front", 1),
           ("p13", "side", -1), ("p14", "side", -1), ("p15", "side", 1), ("p16", "side", 1)]
GUIDES = {"expedition": ("guide-dryrun", "front", -1), "liner": ("guide-queen", "front", -1)}   # MS Dry Run, Queen Mempool


def files(src):
    """name -> bytes for every picture in the folder or the zip, by its file name without the folder."""
    out = {}
    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as z:
            for n in z.namelist():
                b = os.path.basename(n)
                if "/raw/" not in "/" + n and b.lower().endswith((".webp", ".png")) and not b.startswith("."):
                    out.setdefault(b.lower(), z.read(n))
    else:
        for d, dirs, fs in os.walk(src):
            dirs[:] = [x for x in dirs if x != "raw"]
            for b in fs:
                if b.lower().endswith((".webp", ".png")):
                    out.setdefault(b.lower(), open(os.path.join(d, b), "rb").read())
    return out


def frame(pics, name):
    for ext in (".webp", ".png"):
        if name + ext in pics:
            return rgba(pics[name + ext])
    sys.exit(f"missing: {name}.webp (or .png)")


def rgba(data):
    """The picture with a transparent background: as it comes if it has one, else its flat background keyed out."""
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    if im.getchannel("A").getextrema()[0] < 255:
        return im
    W, H = im.size
    px = im.load()
    edge = sorted([px[x, 2][:3] for x in range(0, W, 7)] + [px[x, H - 3][:3] for x in range(0, W, 7)] +
                  [px[2, y][:3] for y in range(0, H, 7)] + [px[W - 3, y][:3] for y in range(0, H, 7)])
    bg = edge[len(edge) // 2]
    for y in range(H):
        for x in range(W):
            r, g, b, _ = px[x, y]
            d = abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2])
            a = 0 if d < 90 else 255 if d > 170 else (d - 90) * 255 // 80
            if 0 < a < 255:   # the fringe: take the background's tint out of it
                g = max(g, (r + b) // 2 - 40)
            px[x, y] = (r, g, b, a)
    return im


def gesture(a, b):
    """The second frame as the first with only the gesture from the second: the box round what changed, widened a
    little, is taken from b, everything else from a. None when nothing changed."""
    if a.size != b.size:
        b = b.resize(a.size, Image.LANCZOS)
    pa, pb = a.convert("RGBa"), b.convert("RGBa")   # premultiplied: a colour under full transparency is no change
    bands = ImageChops.difference(pa, pb).split()
    m = Image.eval(bands[0], lambda v: 255 if v > 48 else 0)
    for c in bands[1:]:
        m = ImageChops.lighter(m, Image.eval(c, lambda v: 255 if v > 48 else 0))
    m = m.filter(ImageFilter.MinFilter(5))   # specks of noise are not a gesture
    box = m.getbbox()
    if not box:
        return a.copy(), None
    pad = a.height // 60
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(a.width, box[2] + pad), min(a.height, box[3] + pad))
    out = a.copy()
    out.paste(b.crop(box), box[:2])
    return out, box


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
    """Where the figure stands: the middle of its lowest opaque rows (soles, wheels), in its own pixels, and half the
    width of its base in world units for the shadow."""
    a = im.getchannel("A")
    bb = a.point(lambda v: 255 if v > 128 else 0).getbbox()
    if not bb:
        sys.exit("an empty figure")
    rows = max(2, (bb[3] - bb[1]) // 25)
    xs = [x for y in range(bb[3] - rows, bb[3]) for x in range(bb[0], bb[2]) if a.getpixel((x, y)) > 128]
    base = (max(xs) - min(xs) + 1) / 2 / UNIT
    return [round(sum(xs) / len(xs), 1), bb[3] - 1], round(min(6.0, max(2.0, base * 1.25)), 2)


def build(src, out=OUT, size=None):
    size = size or {}
    pics = files(src)
    todo = [(i, v, f, None) for i, v, f in FIGURES] + [(n, v, f, k) for k, (n, v, f) in GUIDES.items()]
    frames, notes = [], []
    for name, view, face, ship in todo:
        a, b = frame(pics, name + "-a"), frame(pics, name + "-b")
        b, box = gesture(a, b)
        if not box:
            notes.append(f"{name}: no gesture found in -b")
        else:
            fig = a.getchannel("A").getbbox() or (0, 0, a.width, a.height)
            if (box[2] - box[0]) * (box[3] - box[1]) > 0.7 * (fig[2] - fig[0]) * (fig[3] - fig[1]):
                notes.append(f"{name}: -b differs almost everywhere, so the figure may jump when it gestures")
        bb = a.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
        bb2 = b.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
        if not bb:
            sys.exit(f"{name}: nothing on the picture")
        if bb2:
            bb = (min(bb[0], bb2[0]), min(bb[1], bb2[1]), max(bb[2], bb2[2]), max(bb[3], bb2[3]))
        k = UNIT * ADULT_UNITS / ADULT_PX * size.get(name, 1.0)
        m = 8
        crop = (max(0, bb[0] - m), max(0, bb[1] - m), min(a.width, bb[2] + m), min(a.height, bb[3] + m))
        sa, sb = small(a.crop(crop), k), small(b.crop(crop), k)
        ft, sw = foot(sa)
        frames.append((name, view, face, ship, sa, sb, ft, sw))
    cw = max(max(f[4].width, f[5].width) for f in frames) + 2
    ch = max(max(f[4].height, f[5].height) for f in frames) + 2
    cells = [c for f in frames for c in (f[4], f[5])]
    rows = -(-len(cells) // COLS)
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
    os.makedirs(out, exist_ok=True)
    buf = io.BytesIO()
    sheet.save(buf, "WEBP", lossless=True, quality=100, method=6)   # lossless: the two frames of a figure match to the pixel
    open(os.path.join(out, "tourists.webp"), "wb").write(buf.getvalue())
    with open(os.path.join(out, "tourists.json"), "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=1)
        fh.write("\n")
    return man, notes


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("src", help="the folder or zip with p01-a.webp ... guide-queen-b.webp")
    p.add_argument("--out", default=OUT)
    p.add_argument("--size", nargs="*", default=[], help="id=factor, e.g. p03=0.95")
    a = p.parse_args(argv)
    size = {k: float(v) for k, v in (s.split("=", 1) for s in a.size)}
    man, notes = build(a.src, a.out, size)
    for n in notes:
        print("note:", n)
    print(f"{len(man['figures'])} passengers and {len(man['guides'])} guides, cells {man['cell'][0]}x{man['cell'][1]} -> {a.out}")


if __name__ == "__main__":
    main()

"""The cruise passengers' sheet (tourists.py), from stand-in figures: two frames each, one of them on magenta, one
whose second frame moved, from a folder and from a zip with other spellings; the magenta originals, too small, with
frames missing; and the sheet in the repo, if there is one."""
import io
import json
import os
import tempfile
import zipfile

from PIL import Image, ImageDraw

import tourists

NAMES = [n for n, _, _ in tourists.FIGURES] + [n for n, _, _ in tourists.GUIDES.values()]
assert len(NAMES) == 18 and len(set(NAMES)) == 18
assert "Caribbean Disaster" not in open(tourists.__file__).read()
assert {tourists.key(n) for n in ("p01-a.webp", "P01_A.PNG", "p1a.webp", "p01-a-magenta.webp")} == {"p1a"}
assert tourists.key("p10-b.webp") == "p10b" and tourists.key("guide-dryrun-a.webp") == "guidedryruna"
TALL = {"p03": 950, "p04": 900, "p12": 960}
INK = (34, 48, 58)


def person(arm_up, h=1300, magenta=False, shift=0):
    """A stand-in figure on the prompt's canvas, h px from the soles (80 px above the bottom) to the top of the head."""
    im = Image.new("RGB" if magenta else "RGBA", (1024, 1536), (255, 0, 255) if magenta else (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S = lambda v: round(v * h / 1300)
    fy, cx = 1456, 512 + shift
    top = fy - h
    d.rectangle((cx - S(110), top + S(200), cx + S(110), fy - S(560)), fill=(40, 130, 120), outline=INK, width=S(12))   # body
    d.rectangle((cx - S(90), fy - S(560), cx - S(20), fy), fill=(60, 60, 70))   # legs, standing on the ground line
    d.rectangle((cx + S(20), fy - S(560), cx + S(90), fy), fill=(60, 60, 70))
    d.ellipse((cx - S(80), top, cx + S(80), top + S(190)), fill=(200, 150, 110), outline=INK, width=S(12))   # head
    if arm_up:
        d.rectangle((cx + S(110), top - S(120), cx + S(170), top + S(260)), fill=(200, 150, 110))
    else:
        d.rectangle((cx + S(110), top + S(220), cx + S(170), top + S(600)), fill=(40, 130, 120))
    return im


def save(im, path):
    buf = io.BytesIO(); im.save(buf, "WEBP", quality=95, lossless=True); open(path, "wb").write(buf.getvalue())


def check(out, man, scale=1.0, still=()):
    sheet = Image.open(os.path.join(out, "tourists.webp"))
    cw, ch = man["cell"]
    n = len(man["figures"]) + len(man["guides"])
    assert sheet.mode == "RGBA" and sheet.size == (cw * tourists.COLS, ch * -(-2 * n // tourists.COLS)), sheet.size
    assert man["unit"] == tourists.UNIT and man["cols"] == tourists.COLS
    k = tourists.UNIT * tourists.ADULT_UNITS / tourists.ADULT_PX

    def cell(i):
        return sheet.crop(((i % tourists.COLS) * cw, (i // tourists.COLS) * ch, (i % tourists.COLS + 1) * cw, (i // tourists.COLS + 1) * ch))
    for f in man["figures"] + list(man["guides"].values()):
        a, b = cell(f["a"]), cell(f["b"])
        bb = a.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox()
        assert bb and abs(f["foot"][1] - (bb[3] - 1)) <= 1, (f["id"], f["foot"], bb)   # feet on the lowest row
        assert bb[0] <= f["foot"][0] <= bb[2]
        tall = (bb[3] - bb[1]) / tourists.UNIT   # world units, soles to the top of the head, whatever the painted size
        want = TALL.get(f["id"], 1300) * k / tourists.UNIT
        assert abs(tall - want) < 1.2, (f["id"], tall, want)
        assert 2 <= f["sw"] <= 6
        # the second frame is the first but for the raised arm: the legs are the same pixels
        legs = (0, bb[3] - int(2 * tourists.UNIT), cw, bb[3])
        assert a.crop(legs).tobytes() == b.crop(legs).tobytes(), f["id"]
        assert (a.tobytes() == b.tobytes()) == (f["id"] in still), f["id"]
        # no magenta left round the figure keyed out here, nor a dark halo inside the ink edge
        raw = a.tobytes(); px = [raw[i:i + 4] for i in range(0, len(raw), 4) if raw[i + 3] > 40]
        assert not [p for p in px if p[0] > 200 and p[2] > 200 and p[1] < 80], f["id"]


with tempfile.TemporaryDirectory() as tmp:
    src = os.path.join(tmp, "tourists")
    os.makedirs(os.path.join(src, "raw"))
    os.makedirs(os.path.join(src, "check"))
    for n in NAMES:
        h, mag = TALL.get(n, 1300), n == "p07"
        save(person(False, h, mag), os.path.join(src, f"{n}-a.webp"))
        save(person(True, h, mag, shift=40 if n == "p09" else 0), os.path.join(src, f"{n}-b.webp"))
    save(Image.new("RGB", (8, 8), (255, 0, 255)), os.path.join(src, "raw", "p01-a.webp"))   # raw/ is left alone
    save(Image.new("RGB", (8, 8), (255, 0, 255)), os.path.join(src, "check", "p02-a.webp"))   # and so is check/
    save(Image.new("RGB", (8, 8), (255, 0, 255)), os.path.join(src, "notes.png"))
    out = os.path.join(tmp, "out")
    man, notes, heights = tourists.build(src, out)
    assert [f["id"] for f in man["figures"]] == [n for n, _, _ in tourists.FIGURES]
    assert set(man["guides"]) == {"expedition", "liner"} and man["guides"]["liner"]["id"] == "guide-queen"
    assert notes == ["p09: -b stood -40,0 px off -a, lined up by the soles", "not used: notes.png"], notes
    assert abs(heights["p01"] - 16) < 0.3 and abs(heights["p04"] - 900 / 1300 * 16) < 0.3, heights
    check(out, man)
    adult = man["figures"][0]
    assert adult["view"] == "back" and adult["face"] == -1 and man["figures"][15]["face"] == 1
    # the same from a zip, with the folder anywhere inside it and the names spelt otherwise
    z = os.path.join(tmp, "tourists.zip")
    with zipfile.ZipFile(z, "w") as zf:
        for i, b in enumerate(sorted(os.listdir(src))):
            p = os.path.join(src, b)
            if os.path.isfile(p) and b != "notes.png":
                zf.write(p, "handoff/tourists/" + (b.upper().replace("-", "_") if i % 2 else b))
    man2, _, _ = tourists.build(z, os.path.join(tmp, "out2"))
    assert man2 == man
    os.remove(os.path.join(src, "p05-b.webp"))
    try:
        tourists.build(src, os.path.join(tmp, "out3"))
        raise AssertionError("a missing frame must stop the build")
    except SystemExit as e:
        assert "p05-b" in str(e)
    # the magenta originals, painted smaller than asked, one frame and one figure missing, the second frames trimmed
    for n in NAMES:
        h = TALL.get(n, 1300) * 0.8
        if n != "p06":
            save(person(False, h, True), os.path.join(src, "raw", f"{n}-a-magenta.webp"))
        if n not in ("p05", "p06"):
            save(person(True, h, True).crop((0, 20, 1000, 1536)), os.path.join(src, "raw", f"{n}-b-magenta.webp"))
    man3, notes3, _ = tourists.build(src, os.path.join(tmp, "out4"), partial=True, raw=True)
    assert [f["id"] for f in man3["figures"]] == [n for n, _, _ in tourists.FIGURES if n != "p06"]
    assert "p05-b: missing, so p05 stands still" in notes3 and "p06: missing, left out" in notes3, notes3
    assert [n for n in notes3 if n.startswith("the passengers came out 0.80 times the asked size (a grown-up 104")], notes3
    assert "p01: -a and -b are not on one canvas, lined up by the soles" in notes3, notes3
    check(os.path.join(tmp, "out4"), man3, still=("p05",))

# the sheet in the repo, once it is there: what the game reads (scene.js crowdOk) and what the sheet holds
art = os.path.join(tourists.OUT, "tourists.json")
if os.path.exists(art):
    m = json.load(open(art))
    im = Image.open(os.path.join(tourists.OUT, m["src"]))
    assert im.mode == "RGBA" and os.path.getsize(os.path.join(tourists.OUT, m["src"])) < 1024 * 1024
    cw, ch = m["cell"]
    n = len(m["figures"]) + len(m.get("guides", {}))
    assert im.size[0] == cw * m["cols"] and im.size[1] >= ch * -(-2 * n // m["cols"])
    ids = [f["id"] for f in m["figures"]]
    assert len(ids) >= 6 and len(set(ids)) == len(ids) and set(ids) <= {n for n, _, _ in tourists.FIGURES}, ids
    for f in m["figures"] + list(m.get("guides", {}).values()):
        assert f["view"] in ("back", "front", "side") and f["face"] in (-1, 1)
        assert 0 <= f["a"] < 2 * n and 0 <= f["b"] < 2 * n and 0 <= f["foot"][0] <= cw and 0 <= f["foot"][1] <= ch
print("ok: sheet, frames, feet, scale, keying, spellings, zip, raw, partial; repo art", "checked" if os.path.exists(art) else "not there yet")

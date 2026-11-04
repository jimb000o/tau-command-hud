"""The cruise passengers' sheet (tourists.py), from stand-in figures: two frames each, one of them on magenta, one
whose second frame moved more than its gesture, from a folder and from a zip; and the sheet in the repo, if there is one."""
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


def person(arm_up, kid=False, magenta=False, shift=0):
    """A stand-in figure on the prompt's canvas: a grown-up 1300 px from the soles (80 px above the bottom) up."""
    im = Image.new("RGBA" if not magenta else "RGB", (1024, 1536), (0, 0, 0, 0) if not magenta else (255, 0, 255))
    d = ImageDraw.Draw(im)
    h = 900 if kid else 1300
    top, fy, cx = 1456 - h, 1456, 512 + shift
    d.rectangle((cx - 110, top + 200, cx + 110, fy - 560), fill=(40, 130, 120), outline=(34, 48, 58), width=12)   # body
    d.rectangle((cx - 90, fy - 560, cx - 20, fy), fill=(60, 60, 70))   # legs, standing on the ground line
    d.rectangle((cx + 20, fy - 560, cx + 90, fy), fill=(60, 60, 70))
    d.ellipse((cx - 80, top, cx + 80, top + 190), fill=(200, 150, 110), outline=(34, 48, 58), width=12)   # head
    if arm_up:
        d.rectangle((cx + 110, top - 120, cx + 170, top + 260), fill=(200, 150, 110))
    else:
        d.rectangle((cx + 110, top + 220, cx + 170, top + 600), fill=(40, 130, 120))
    return im


def save(im, path):
    buf = io.BytesIO(); im.save(buf, "WEBP", quality=95, lossless=True); open(path, "wb").write(buf.getvalue())


with tempfile.TemporaryDirectory() as tmp:
    src = os.path.join(tmp, "tourists")
    os.makedirs(os.path.join(src, "raw"))
    for n in NAMES:
        kid, mag = n in ("p04", "p12"), n == "p07"
        save(person(False, kid, mag), os.path.join(src, f"{n}-a.webp"))
        save(person(True, kid, mag, shift=40 if n == "p09" else 0), os.path.join(src, f"{n}-b.webp"))
    save(Image.new("RGB", (8, 8), (255, 0, 255)), os.path.join(src, "raw", "p01-a.webp"))   # raw/ is left alone
    out = os.path.join(tmp, "out")
    man, notes = tourists.build(src, out)
    assert [f["id"] for f in man["figures"]] == [n for n, _, _ in tourists.FIGURES]
    assert set(man["guides"]) == {"expedition", "liner"} and man["guides"]["liner"]["id"] == "guide-queen"
    assert notes == ["p09: -b differs almost everywhere, so the figure may jump when it gestures"], notes
    sheet = Image.open(os.path.join(out, "tourists.webp"))
    cw, ch = man["cell"]
    assert sheet.mode == "RGBA" and sheet.size == (cw * tourists.COLS, ch * 3), sheet.size
    assert man["unit"] == tourists.UNIT and man["cols"] == tourists.COLS
    k = tourists.UNIT * tourists.ADULT_UNITS / tourists.ADULT_PX

    def cell(i):
        return sheet.crop(((i % tourists.COLS) * cw, (i // tourists.COLS) * ch, (i % tourists.COLS + 1) * cw, (i // tourists.COLS + 1) * ch))
    for f in man["figures"] + list(man["guides"].values()):
        a, b = cell(f["a"]), cell(f["b"])
        bb = a.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox()
        assert bb and abs(f["foot"][1] - (bb[3] - 1)) <= 1, (f["id"], f["foot"], bb)   # feet on the lowest row
        assert bb[0] <= f["foot"][0] <= bb[2]
        tall = (bb[3] - bb[1]) / tourists.UNIT   # world units, soles to the top of the head
        want = (900 if f["id"] in ("p04", "p12") else 1300) * k / tourists.UNIT
        assert abs(tall - want) < 1.2, (f["id"], tall, want)
        assert 2 <= f["sw"] <= 6
        # the second frame is the first but for the raised arm: the legs are the same pixels
        legs = (0, bb[3] - int(2 * tourists.UNIT), cw, bb[3])
        if f["id"] != "p09":
            assert a.crop(legs).tobytes() == b.crop(legs).tobytes(), f["id"]
        assert a.tobytes() != b.tobytes(), f["id"]
        # no magenta left round the figure keyed out here, nor a dark halo inside the ink edge
        raw = a.tobytes(); px = [raw[i:i + 4] for i in range(0, len(raw), 4) if raw[i + 3] > 40]
        assert not [p for p in px if p[0] > 200 and p[2] > 200 and p[1] < 80], f["id"]
    adult, kid = man["figures"][0], man["figures"][3]
    assert adult["view"] == "back" and adult["face"] == -1 and man["figures"][15]["face"] == 1
    # the same from a zip, with the folder anywhere inside it
    z = os.path.join(tmp, "tourists.zip")
    with zipfile.ZipFile(z, "w") as zf:
        for b in os.listdir(src):
            p = os.path.join(src, b)
            if os.path.isfile(p):
                zf.write(p, "handoff/tourists/" + b)
    man2, _ = tourists.build(z, os.path.join(tmp, "out2"))
    assert man2 == man
    os.remove(os.path.join(src, "p05-b.webp"))
    try:
        tourists.build(src, os.path.join(tmp, "out3"))
        raise AssertionError("a missing frame must stop the build")
    except SystemExit as e:
        assert "p05-b" in str(e)

# the sheet in the repo, once it is there: what the game reads (scene.js crowdOk) and what the sheet holds
art = os.path.join(tourists.OUT, "tourists.json")
if os.path.exists(art):
    m = json.load(open(art))
    im = Image.open(os.path.join(tourists.OUT, m["src"]))
    assert im.mode == "RGBA" and os.path.getsize(os.path.join(tourists.OUT, m["src"])) < 1024 * 1024
    cw, ch = m["cell"]
    n = len(m["figures"]) + len(m.get("guides", {}))
    assert im.size[0] == cw * m["cols"] and im.size[1] >= ch * -(-2 * n // m["cols"])
    ids = {f["id"] for f in m["figures"]}
    assert ids == {n for n, _, _ in tourists.FIGURES}, ids
    for f in m["figures"] + list(m.get("guides", {}).values()):
        assert f["view"] in ("back", "front", "side") and f["face"] in (-1, 1)
        assert 0 <= f["a"] < 2 * n and 0 <= f["b"] < 2 * n and 0 <= f["foot"][0] <= cw and 0 <= f["foot"][1] <= ch
print("ok: sheet, frames, feet, scale, keying, zip; repo art", "checked" if os.path.exists(art) else "not there yet")

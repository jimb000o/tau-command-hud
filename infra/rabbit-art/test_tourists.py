"""The cruise passengers' sheet (tourists.py), from stand-in figures on the painted canvas: both frames scaled as one,
the feet and what else touches the ground measured, a figure that stands still, hot pink and magenta keyed out, the
bodyHeights from metrics.json, a second frame whose legs move, other spellings and a zip, frames missing or on the wrong
canvas, the magenta originals; and the sheet in the repo, if there is one."""
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
BODY = {"p03": 950, "p04": 900, "p12": 960, "guide-dryrun": 1067, "guide-queen": 1066}
INK = (34, 48, 58)
HOT = (231, 15, 111)   # the pink the cut can leave between an arm and the body


def person(arm_up, h=1300, magenta=False, legs=0, pink=False, canvas=tourists.CANVAS):
    """A stand-in figure on the painted canvas, h px from the soles (on the baseline) to the top of the head, two legs
    apart on the ground; legs shifts them sideways (a second frame that jumps); pink leaves a hot-pink patch inside."""
    im = Image.new("RGB" if magenta else "RGBA", canvas, (255, 0, 255) if magenta else (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S = lambda v: round(v * h / 1300)
    cx, fy = tourists.ANCHOR
    top = fy - h
    d.rectangle((cx - S(110), top + S(200), cx + S(110), fy - S(560)), fill=(40, 130, 120), outline=INK, width=S(12))   # body
    d.rectangle((cx - S(90) + legs, fy - S(560), cx - S(20) + legs, fy), fill=(60, 60, 70))   # legs, standing on the ground line
    d.rectangle((cx + S(20) + legs, fy - S(560), cx + S(90) + legs, fy), fill=(60, 60, 70))
    d.ellipse((cx - S(80), top, cx + S(80), top + S(190)), fill=(200, 150, 110), outline=INK, width=S(12))   # head
    if arm_up:
        d.rectangle((cx + S(110), top - S(120), cx + S(170), top + S(260)), fill=(200, 150, 110))
    else:
        d.rectangle((cx + S(110), top + S(220), cx + S(170), top + S(600)), fill=(40, 130, 120))
    if pink:
        d.rectangle((cx + S(112), top + S(300), cx + S(140), top + S(420)), fill=HOT)   # between the arm and the body
    return im


def save(im, path):
    buf = io.BytesIO(); im.save(buf, "WEBP", quality=95, lossless=True); open(path, "wb").write(buf.getvalue())


def check(out, man, still=(), legs=()):
    sheet = Image.open(os.path.join(out, "tourists.webp"))
    cw, ch = man["cell"]
    every = man["figures"] + list(man["guides"].values())
    assert man["unit"] == tourists.UNIT and man["cols"] == tourists.COLS and sheet.mode == "RGBA"
    cells = sum(1 if f["a"] == f["b"] else 2 for f in every)
    assert sheet.size == (cw * tourists.COLS, ch * -(-cells // tourists.COLS)), sheet.size
    assert sorted(c for f in every for c in {f["a"], f["b"]}) == list(range(cells)), "every cell once, in order"

    def cell(i):
        return sheet.crop(((i % tourists.COLS) * cw, (i // tourists.COLS) * ch, (i % tourists.COLS + 1) * cw, (i // tourists.COLS + 1) * ch))
    for f in every:
        a, b = cell(f["a"]), cell(f["b"])
        bb = a.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox()
        assert bb and abs(f["foot"][1] - bb[3]) <= 1.5, (f["id"], f["foot"], bb)   # the baseline is where the soles are
        assert bb[0] <= f["foot"][0] <= bb[2]
        tall = (bb[3] - bb[1]) / tourists.UNIT   # world units, soles to the top of the head
        want = tourists.TARGET.get(f["id"], tourists.ADULT_TARGET) / tourists.PX_PER_UNIT
        assert abs(tall - want) < 0.4, (f["id"], tall, want)
        # the two legs touch the ground, each under itself; the arm, the body and the head do not
        cs = f["contacts"]
        assert len(cs) == 2 and all(abs(y - f["foot"][1]) <= 1.5 and 1 <= hw < 6 for _, y, hw in cs), (f["id"], cs)
        assert cs[0][0] < f["foot"][0] < cs[1][0] and all(bb[0] <= x <= bb[2] for x, _, _ in cs), (f["id"], cs)
        assert (a.tobytes() == b.tobytes()) == (f["id"] in still), f["id"]
        if f["id"] not in still and f["id"] not in legs:   # the second frame is the first but for the arm: the legs are the same pixels
            low = (0, bb[3] - int(2 * tourists.UNIT), cw, bb[3])
            assert a.crop(low).tobytes() == b.crop(low).tobytes(), f["id"]
        # no magenta or hot pink left inside the figure
        raw = a.tobytes(); px = [raw[i:i + 4] for i in range(0, len(raw), 4) if raw[i + 3] > 40]
        assert not [p for p in px if p[0] > 200 and p[2] > 90 and p[1] < 80], f["id"]


with tempfile.TemporaryDirectory() as tmp:
    src = os.path.join(tmp, "tourists")
    os.makedirs(os.path.join(src, "raw"))
    os.makedirs(os.path.join(src, "check"))
    for n in NAMES:
        h = BODY.get(n, 1300)
        save(person(False, h, magenta=n == "p07", pink=n == "p04"), os.path.join(src, f"{n}-a.webp"))
        save(person(True, h, magenta=n == "p07", legs=40 if n == "p09" else 0), os.path.join(src, f"{n}-b.webp"))
    json.dump({n: {"bodyHeight": BODY.get(n, 1300), "canvas": [1024, 1536], "anchor": [512, 1456]} for n in NAMES}, open(os.path.join(src, "metrics.json"), "w"))
    save(Image.new("RGB", (8, 8), (255, 0, 255)), os.path.join(src, "raw", "p01-a.webp"))   # raw/ is left alone
    save(Image.new("RGB", (8, 8), (255, 0, 255)), os.path.join(src, "check", "p02-a.webp"))   # and so is check/
    save(Image.new("RGB", (8, 8), (255, 0, 255)), os.path.join(src, "notes.png"))
    out = os.path.join(tmp, "out")
    man, notes, info = tourists.build(src, out, still={"p05"})
    assert [f["id"] for f in man["figures"]] == [n for n, _, _ in tourists.FIGURES]
    assert set(man["guides"]) == {"expedition", "liner"} and man["guides"]["liner"]["id"] == "guide-queen"
    assert [n for n in notes if n.startswith("p04-a: ") and n.endswith("of the figure was key colour the cut left in, now keyed out")], notes
    assert [n for n in notes if n.startswith("p09: ") and n.endswith("of what changes between -a and -b is in the legs, so it may jump")], notes
    assert notes[-1] == "not used: notes.png" and len(notes) == 3, notes
    assert info["p01"]["tall"] == 16.0 and info["p04"]["tall"] == round(26 / tourists.PX_PER_UNIT, 1) and info["p05"]["still"] and not info["p06"]["still"], info
    assert info["p09"]["low"] > 0.1 and info["p01"]["low"] < 0.05 and 0 < info["p01"]["change"] < 0.5, info
    check(out, man, still=("p05",), legs=("p09",))
    p05, p06 = man["figures"][4], man["figures"][5]
    assert p05["a"] == p05["b"] and p06["a"] == p05["a"] + 1 and p06["b"] == p06["a"] + 1, "a still figure takes one cell"
    adult = man["figures"][0]
    assert adult["view"] == "back" and adult["face"] == -1 and man["figures"][15]["face"] == 1
    assert man["guides"]["expedition"]["face"] == 1 and man["guides"]["liner"]["face"] == -1
    # the same from a zip, with the folder anywhere inside it and the names spelt otherwise
    z = os.path.join(tmp, "tourists.zip")
    with zipfile.ZipFile(z, "w") as zf:
        for i, b in enumerate(sorted(os.listdir(src))):
            p = os.path.join(src, b)
            if os.path.isfile(p) and b != "notes.png":
                zf.write(p, "handoff/tourists/" + (b.upper().replace("-", "_") if i % 2 and b != "metrics.json" else b))
    man2, _, _ = tourists.build(z, os.path.join(tmp, "out2"), still={"p05"})
    assert man2 == man
    # a frame that is not on the full canvas stops the build, and so does a missing frame
    save(person(True).crop((0, 20, 1000, 1536)), os.path.join(src, "p02-b.webp"))
    try:
        tourists.build(src, os.path.join(tmp, "out3"))
        raise AssertionError("a trimmed frame must stop the build")
    except SystemExit as e:
        assert "p02-b" in str(e) and "1000x1516" in str(e), e
    save(person(True), os.path.join(src, "p02-b.webp"))
    os.remove(os.path.join(src, "p05-b.webp"))
    try:
        tourists.build(src, os.path.join(tmp, "out3"))
        raise AssertionError("a missing frame must stop the build")
    except SystemExit as e:
        assert "p05-b" in str(e)
    # the magenta originals, one frame and one figure missing
    for n in NAMES:
        h = BODY.get(n, 1300)
        if n != "p06":
            save(person(False, h, True), os.path.join(src, "raw", f"{n}-a-magenta.webp"))
        if n not in ("p05", "p06"):
            save(person(True, h, True, legs=40 if n == "p09" else 0), os.path.join(src, "raw", f"{n}-b-magenta.webp"))
    man3, notes3, info3 = tourists.build(src, os.path.join(tmp, "out4"), partial=True, raw=True)
    assert [f["id"] for f in man3["figures"]] == [n for n, _, _ in tourists.FIGURES if n != "p06"]
    assert "p05-b: missing, so p05 stands still" in notes3 and "p06: missing, left out" in notes3, notes3
    assert info3["p05"]["still"] and "p06" not in info3
    check(os.path.join(tmp, "out4"), man3, still=("p05",), legs=("p09",))

# the sheet in the repo, once it is there: what the game reads (scene.js crowdOk) and what the sheet holds
art = os.path.join(tourists.OUT, "tourists.json")
if os.path.exists(art):
    m = json.load(open(art))
    im = Image.open(os.path.join(tourists.OUT, m["src"]))
    assert im.mode == "RGBA" and os.path.getsize(os.path.join(tourists.OUT, m["src"])) < 1024 * 1024
    cw, ch = m["cell"]
    every = m["figures"] + list(m.get("guides", {}).values())
    cells = sum(1 if f["a"] == f["b"] else 2 for f in every)
    assert im.size[0] == cw * m["cols"] and im.size[1] >= ch * -(-cells // m["cols"])
    ids = [f["id"] for f in m["figures"]]
    assert len(ids) >= 6 and len(set(ids)) == len(ids) and set(ids) <= {n for n, _, _ in tourists.FIGURES}, ids
    for f in every:
        assert f["view"] in ("back", "front", "side") and f["face"] in (-1, 1)
        assert 0 <= f["a"] < cells and 0 <= f["b"] < cells and 0 <= f["foot"][0] <= cw and 0 <= f["foot"][1] <= ch
        assert f["contacts"] and all(0 <= x <= cw and 0 <= y <= ch and hw > 0 for x, y, hw in f["contacts"]), f["id"]
print("ok: sheet, frames as one, feet and contacts, still, pink and magenta, metrics, legs, spellings, zip, canvas, raw, partial; repo art",
      "checked" if os.path.exists(art) else "not there yet")

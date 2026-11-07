"""Taking over a set painted elsewhere (paint.py isle): the island with a few spots changed, the places by day and their
painted nights; what does not fit is refused with the reason and the rest still taken over. No network, nothing painted."""
import io
import json
import os
import random
import shutil
import tempfile
import types

import paint
from PIL import Image, ImageDraw

paint.USAGE = os.path.join(tempfile.mkdtemp(), "gemini-usage.json")   # never the server's art folder


def scene(w, h, seed):
    """A picture with outlines to line up: boxes and lines in ink on a coloured ground."""
    R = random.Random(seed)
    im = Image.new("RGB", (w, h), (R.randrange(90, 200), R.randrange(90, 200), R.randrange(90, 200)))
    d = ImageDraw.Draw(im)
    for _ in range(60):
        x, y = R.randrange(w), R.randrange(h)
        d.rectangle([x, y, x + R.randrange(20, w // 5), y + R.randrange(20, h // 4)], fill=tuple(R.randrange(256) for _ in range(3)), outline=(20, 20, 20), width=4)
    for _ in range(30):
        d.line([R.randrange(w), R.randrange(h), R.randrange(w), R.randrange(h)], fill=(20, 20, 20), width=5)
    return im


def at_night(im):
    """The same picture at night: darker and bluer, a lamp lit in it (what the night painter does, pixel for pixel)."""
    n = Image.eval(im, lambda v: int(v * 0.55))
    r, g, b = n.split(); n = Image.merge("RGB", (r.point(lambda v: int(v * 0.85)), g, b.point(lambda v: min(255, int(v * 1.15) + 8))))
    ImageDraw.Draw(n).ellipse([im.width // 3, im.height // 4, im.width // 3 + 80, im.height // 4 + 80], fill=(255, 210, 140))
    return n


def save(im, path, **kw):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, **kw)


out, src = tempfile.mkdtemp(), tempfile.mkdtemp()
try:
    # the server's art folder as it is: island 36 live (and the market painted by day, its lights found)
    island = scene(1000, 424, 36)
    save(island, os.path.join(out, "island-36-090df65a.webp"), format="WEBP", quality=80)
    old_market = scene(2600, 1114, 2)
    save(old_market, os.path.join(out, "market-old.webp"), format="WEBP", quality=80)
    json.dump({"scenes": {"island": "island-36-090df65a.webp", "market": "market-old.webp", "bar-night": "bar-night-old.webp"},
               "orig": {"market": "market-older.webp"}, "layout": {"places": {"market": {"x": 1}}},
               "lights": {"market": {"of": "market-old.webp", "outside": True, "l": []}}},
              open(os.path.join(out, "index.json"), "w"))

    # the set painted elsewhere: the island without its people (two small spots changed), four places
    live = Image.open(os.path.join(out, "island-36-090df65a.webp")).convert("RGB")
    clean = live.copy(); d = ImageDraw.Draw(clean)
    d.rectangle([400, 250, 412, 270], fill=(150, 140, 120)); d.rectangle([520, 260, 530, 278], fill=(150, 140, 120))
    save(clean, os.path.join(src, "island.webp"), format="WEBP", lossless=True)
    market = scene(3360, 1440, 7)
    save(market, os.path.join(src, "rooms", "market.webp"), format="WEBP", quality=88)
    save(at_night(market), os.path.join(src, "rooms", "market-night.webp"), format="WEBP", quality=88)
    bar = scene(2800, 1200, 8)
    save(bar, os.path.join(src, "rooms", "bar.png"))
    save(scene(2800, 1200, 99), os.path.join(src, "rooms", "bar-night.png"))   # painted anew, not from the day picture
    save(scene(1600, 900, 9), os.path.join(src, "rooms", "radio.webp"), format="WEBP")   # 16:9 and small: not a place picture
    cafe = scene(3360, 1440, 10)
    save(cafe, os.path.join(src, "rooms", "cafe.webp"), format="WEBP", quality=88)
    save(at_night(cafe).resize((3000, 1286)), os.path.join(src, "rooms", "cafe-night.webp"), format="WEBP", quality=88)   # the wrong size

    # a dry run checks and tells, and writes nothing
    before = open(os.path.join(out, "index.json")).read(), sorted(os.listdir(out))
    paint.cmd_isle(types.SimpleNamespace(src=src, out=out, only=None, dry=True))
    assert (open(os.path.join(out, "index.json")).read(), sorted(os.listdir(out))) == before

    paint.cmd_isle(types.SimpleNamespace(src=src, out=out, only=None, dry=False))
    idx = json.load(open(os.path.join(out, "index.json"))); sc = idx["scenes"]
    # the island keeps its name (layout and living clip stay with it), its people gone
    assert sc["island"].startswith("island-36-090df65a-clean-") and sc["island"].endswith(".webp"), sc["island"]
    assert idx["layout"] == {"places": {"market": {"x": 1}}}
    got = Image.open(os.path.join(out, sc["island"])).convert("RGB")
    assert got.size == (1000, 424) and abs(got.getpixel((405, 260))[0] - 150) < 30
    # the market by day and at night, as they came (a WebP is not made worse by a second compression)
    assert sc["market"].startswith("market-codex-") and sc["market-night"].startswith("market-night-codex-")
    assert open(os.path.join(out, sc["market"]), "rb").read() == open(os.path.join(src, "rooms", "market.webp"), "rb").read()
    assert open(os.path.join(out, sc["market-night"]), "rb").read() == open(os.path.join(src, "rooms", "market-night.webp"), "rb").read()
    assert "market" not in idx.get("orig", {})   # no sharper copy to go back to: this is the picture now
    # a night painted anew instead of from the day picture is refused, its day taken over, an older night gone
    assert sc["bar"].startswith("bar-codex-") and "bar-night" not in sc
    assert Image.open(os.path.join(out, sc["bar"])).format == "WEBP"
    # the wrong size: the radio not at all, the café's night not (its day yes)
    assert "radio" not in sc and sc["cafe"].startswith("cafe-codex-") and "cafe-night" not in sc

    # the set again: the same names, nothing doubled; the island compared with the island that was kept
    paint.cmd_isle(types.SimpleNamespace(src=src, out=out, only=["island", "market"], dry=False))
    sc2 = json.load(open(os.path.join(out, "index.json")))["scenes"]
    assert sc2["island"] == sc["island"] and sc2["market"] == sc["market"]

    # a repainted island is not a few spots changed: refused, the live one stays
    save(scene(1000, 424, 77), os.path.join(src, "island.webp"), format="WEBP", lossless=True)
    paint.cmd_isle(types.SimpleNamespace(src=src, out=out, only=["island"], dry=False))
    assert json.load(open(os.path.join(out, "index.json")))["scenes"]["island"] == sc["island"]
    save(scene(900, 424, 36), os.path.join(src, "island.webp"), format="WEBP", lossless=True)   # another size
    paint.cmd_isle(types.SimpleNamespace(src=src, out=out, only=["island"], dry=False))
    assert json.load(open(os.path.join(out, "index.json")))["scenes"]["island"] == sc["island"]

    # a night lines up with its own day picture, not with another, and a few pixels off still counts
    assert paint.lines_up(market, at_night(market)) > 0.85
    assert paint.lines_up(market, scene(3360, 1440, 70)) < 0.5
    shifted = Image.new("RGB", market.size); shifted.paste(market, (6, 0))
    assert paint.lines_up(market, at_night(shifted)) > 0.85

    # a new day picture kept or the place dropped: its painted night goes with it (it was made from the picture before)
    os.makedirs(os.path.join(out, "drafts"), exist_ok=True)
    shutil.copyfile(os.path.join(out, sc["bar"]), os.path.join(out, "drafts", "market-new.webp"))
    json.dump({"market": ["market-new.webp"]}, open(os.path.join(out, "drafts", "drafts.json"), "w"))
    paint.cmd_keep(types.SimpleNamespace(out=out, picks=["market=1"], layout=None))
    sc3 = json.load(open(os.path.join(out, "index.json")))["scenes"]
    assert sc3["market"] == "market-new.webp" and "market-night" not in sc3
    paint.cmd_isle(types.SimpleNamespace(src=src, out=out, only=["market"], dry=False))
    assert "market-night" in json.load(open(os.path.join(out, "index.json")))["scenes"]
    paint.cmd_drop(types.SimpleNamespace(out=out, places=["market"]))
    sc4 = json.load(open(os.path.join(out, "index.json")))["scenes"]
    assert "market" not in sc4 and "market-night" not in sc4

    # the newest set in imports/codex when none is named
    assert paint.isle_dir(None).startswith(paint.IMPORTS) if os.path.isdir(paint.IMPORTS) and any(x.startswith("isle-") for x in os.listdir(paint.IMPORTS)) else True

    # the game: a painted night fades in from the evening, fetched only then, and the rooms' light keeps them lit
    game = open(os.path.join(paint.REPO, "rabbit", "scene.js"), encoding="utf-8").read()
    assert "function paintedNight(" in game and 'ART.later[id] = f' in game and "nightPics(sky)" in game
    assert 'roomImage(S.room + "-night")' in game
    print("isle: ok")
finally:
    shutil.rmtree(out, ignore_errors=True); shutil.rmtree(src, ignore_errors=True)

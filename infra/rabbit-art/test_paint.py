"""The painter for White Rabbit Key, against a stand-in for the image model: drafts, the page to pick from, keep and drop."""
import base64
import io
import json
import os
import tempfile
import types

import paint

assert set(paint.SCENE) == set(paint.PLACES)
DRAWN = paint.PLACES[:9]   # the others have no drawn picture and are painted from the island itself
for id in DRAWN:
    assert os.path.exists(os.path.join(paint.PLATES, id + ".jpg")), f"no plate for {id}: run node infra/rabbit-art/plates.mjs"
game = open(os.path.join(paint.REPO, "rabbit", "scene.js"), encoding="utf-8").read()
for id in DRAWN[1:]:
    assert f"    {id}: " in game or f"    {id}:" in game, id
assert "Caribbean Disaster" not in open(paint.__file__).read()

try:
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (1536, 1024), (200, 120, 60)).save(buf, "PNG"); PIC = buf.getvalue()
except ImportError:
    Image, PIC = None, b"\x89PNG fake"
calls = []
prompts, bodies = [], []
def fake(url, data, headers, timeout=240):
    calls.append(url); bodies.append(data.decode("latin-1"))
    prompts.append(json.loads(data)["contents"][0]["parts"][0]["text"] if "generativelanguage" in url else data.decode("latin-1"))
    if "generativelanguage" in url:
        body = json.loads(data)
        if "style references only" in body["contents"][0]["parts"][0]["text"]:
            assert len(body["contents"][0]["parts"]) == 3
        if "ink line drawing on white paper" in body["contents"][0]["parts"][0]["text"]:
            assert len(body["contents"][0]["parts"]) == 2
        if "same artist" in body["contents"][0]["parts"][0]["text"]:
            assert len(body["contents"][0]["parts"]) == 4 and ("high hill" in body["contents"][0]["parts"][0]["text"] or "rough sketch" in body["contents"][0]["parts"][0]["text"])
        assert body["generationConfig"]["imageConfig"]["aspectRatio"] in ("16:9", "21:9", "1:1", "9:16", "3:4") and ("Keep the composition" in body["contents"][0]["parts"][0]["text"] or "Style: " in body["contents"][0]["parts"][0]["text"] or "ink line drawing" in body["contents"][0]["parts"][0]["text"] or "close view of one place" in body["contents"][0]["parts"][0]["text"] or "Repaint this exact island" in body["contents"][0]["parts"][0]["text"] or "much higher resolution" in body["contents"][0]["parts"][0]["text"] or "empty grey" in body["contents"][0]["parts"][0]["text"] or "wide panoramic" in body["contents"][0]["parts"][0]["text"] or "magenta" in body["contents"][0]["parts"][0]["text"] or "Repaint exactly this" in body["contents"][0]["parts"][0]["text"])
        pic = PIC
        if Image and "magenta" in body["contents"][0]["parts"][0]["text"]:   # a bust or a creature on magenta
            from PIL import ImageDraw
            im = Image.new("RGB", (1024, 1024), (255, 0, 255)); ImageDraw.Draw(im).ellipse((300, 200, 724, 1100), fill=(160, 110, 80))
            b = io.BytesIO(); im.save(b, "PNG"); pic = b.getvalue()
        return {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": base64.b64encode(pic).decode()}}]}}]}
    if "openai" in url:
        assert b'name="input_fidelity"' in data and b'filename="plate.jpg"' in data
        if b"like-1" in data:
            assert data.count(b'name="image[]"') >= 2
        return {"data": [{"b64_json": base64.b64encode(PIC).decode()}] * 3}
    raise AssertionError(url)
paint.post = fake
for prov in ("gemini", "openai"):
    os.environ.pop("GEMINI_API_KEY", None); os.environ.pop("OPENAI_API_KEY", None)
    os.environ[{"gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}[prov]] = "test"
    with tempfile.TemporaryDirectory() as out:
        paint.cmd_draft(types.SimpleNamespace(out=out, places=["island", "bar"], n=3, model=None))
        drafts = json.load(open(os.path.join(out, "drafts", "drafts.json")))
        assert len(drafts["island"]) == 3 and "bar=3" in open(os.path.join(out, "drafts", "index.html")).read()
        if Image:
            im = Image.open(os.path.join(out, "drafts", drafts["bar"][0])); assert im.size == (1600, 900) and im.format == "WEBP"
        paint.cmd_keep(types.SimpleNamespace(out=out, picks=["island=2", "bar=1"]))
        paint.cmd_draft(types.SimpleNamespace(out=out, places=["island"], n=3, model=None, like=["island=1", "bar"]))
        more = json.load(open(os.path.join(out, "drafts", "drafts.json")))
        assert more["island"][:3] == drafts["island"] and len(more["island"]) == 6 and "island=6" in open(os.path.join(out, "drafts", "index.html")).read()
        idx = json.load(open(os.path.join(out, "index.json")))
        assert idx["scenes"]["island"] == drafts["island"][1] and os.path.exists(os.path.join(out, idx["scenes"]["bar"]))
        paint.cmd_keep(types.SimpleNamespace(out=out, picks=["bar=last"]))   # the newest draft of a place
        assert json.load(open(os.path.join(out, "index.json")))["scenes"]["bar"] == more["bar"][-1]
        paint.cmd_draft(types.SimpleNamespace(out=out, places=["island"], n=3, model=None, sketch="bay", like=["island=1", "bar"]))
        paint.cmd_keep(types.SimpleNamespace(out=out, picks=["island=9"]))
        idx = json.load(open(os.path.join(out, "index.json")))
        lay = idx["layout"]
        assert set(DRAWN[1:]) <= set(lay["places"]) <= set(paint.PLACES[1:]) and lay["fx"] and lay["windows"] and lay["walk"]
        for id, p in lay["places"].items():
            bx, by, bw, bh = p["box"]; assert bx <= p["x"] <= bx + bw and by <= p["y"] <= by + bh + 20, id
        dj = os.path.join(out, "drafts", "drafts.json"); dd = json.load(open(dj)); dd["sketch"][dd["island"][0]] = "bay"; json.dump(dd, open(dj, "w"))
        paint.cmd_keep(types.SimpleNamespace(out=out, picks=["island=1"]))   # an early painting: the first layout
        assert json.load(open(os.path.join(out, "index.json")))["layout"]["places"]["hall"]["x"] == 1090
        paint.cmd_keep(types.SimpleNamespace(out=out, picks=["island=2"], layout="island-14"))
        assert json.load(open(os.path.join(out, "index.json")))["layout"]["view"] == "whole"
        paint.cmd_keep(types.SimpleNamespace(out=out, picks=["island=2"]))
        assert "layout" not in json.load(open(os.path.join(out, "index.json")))
        paint.REFS = os.path.join(out, "refs"); os.makedirs(os.path.join(paint.REFS, "2"))
        open(os.path.join(paint.REFS, "2", "a.png"), "wb").write(PIC)
        assert len(paint.style_refs(2)) == 1 and paint.style_refs(1) == [] and paint.style_refs(None) == []
        paint.cmd_looks(types.SimpleNamespace(out=out, model=None))
        dd = json.load(open(os.path.join(out, "drafts", "drafts.json")))
        assert set(dd["look"].values()) == {1, 2, 3} and "style 3" in open(os.path.join(out, "drafts", "index.html")).read()
        before = len(json.load(open(os.path.join(out, "drafts", "drafts.json")))["island"])
        paint.cmd_ideas(types.SimpleNamespace(out=out, src="island=1", n=1, model=None))
        dd = json.load(open(os.path.join(out, "drafts", "drafts.json")))
        assert len(dd["island"]) >= before + 3 and set(dd["idea"].values()) == set(paint.IDEAS) and "idea mist" in open(os.path.join(out, "drafts", "index.html")).read()
        paint.cmd_ideas(types.SimpleNamespace(out=out, src="island=1", n=1, model=None, idea="districts"))
        dd = json.load(open(os.path.join(out, "drafts", "drafts.json")))
        assert "districts" in dd["idea"].values() and "coconut works" in prompts[-1]
        paint.cmd_draft(types.SimpleNamespace(out=out, places=["school"], n=1, model=None))   # from the kept island
        assert "close view of one place" in prompts[-1] and json.load(open(os.path.join(out, "drafts", "drafts.json")))["school"]
        paint.cmd_rework(types.SimpleNamespace(out=out, src=None, n=1, model=None))
        assert "Radio Coco" in prompts[-1] and "rework" in json.load(open(os.path.join(out, "drafts", "drafts.json")))["idea"].values()
        if prov == "gemini":   # a sharp copy: asked at 4K, kept wide
            paint.cmd_sharp(types.SimpleNamespace(out=out, src=None, size="4K", model="gemini-3-pro-image-preview"))
            dd = json.load(open(os.path.join(out, "drafts", "drafts.json")))
            assert "sharp 4K" in dd["idea"].values() and "much higher resolution" in prompts[-1] and '"imageSize": "4K"' in bodies[-1]
        if prov == "gemini" and Image:   # high resolution and wide: the middle is the kept picture itself, the sides painted
            paint.cmd_keep(types.SimpleNamespace(out=out, picks=["island=2", "bar=1"], layout="island-21"))
            kept = Image.open(os.path.join(out, json.load(open(os.path.join(out, "index.json")))["scenes"]["island"])).convert("RGB")
            n0 = len(calls)
            for _ in range(2):   # twice: the second starts again from the kept picture
                paint.cmd_hires(types.SimpleNamespace(out=out, places=["all"], no_sharp=True, wide=True, model="gemini-3-pro-image-preview"))
            assert len(calls) - n0 == 8 and "Leave the left half" in prompts[-1] and '"imageSize": "2K"' in bodies[-1]
            idx = json.load(open(os.path.join(out, "index.json")))
            wide = Image.open(os.path.join(out, idx["scenes"]["island"])).convert("RGB")
            assert wide.size == (kept.size[0] * 2, kept.size[1]) and idx["orig"]["island"] != idx["scenes"]["island"]
            assert Image.open(os.path.join(out, idx["scenes"]["bar"])).size == (1600 * 3 // 2, 900)
            assert max(abs(p - q) for p, q in zip(wide.getpixel((kept.size[0], 450)), kept.getpixel((kept.size[0] // 2, 450)))) < 12
            paint.cmd_narrow(types.SimpleNamespace(out=out))   # back to the sharp middle
            idx = json.load(open(os.path.join(out, "index.json")))
            assert Image.open(os.path.join(out, idx["scenes"]["island"])).size == kept.size and Image.open(os.path.join(out, idx["scenes"]["bar"])).size == (1600, 900)
            paint.cmd_hires(types.SimpleNamespace(out=out, places=["island"], no_sharp=False, wide=False, model="gemini-3-pro-image-preview"))
            assert "much higher resolution" in prompts[-1] and '"imageSize": "4K"' in bodies[-1]
            assert Image.open(os.path.join(out, json.load(open(os.path.join(out, "index.json")))["scenes"]["island"])).size == (1600, 900)   # sharp only; the stand-in paints small
            paint.cmd_draft(types.SimpleNamespace(out=out, places=["works"], n=1, model=None, wide=True))   # a wide room
            assert '"aspectRatio": "21:9"' in bodies[-1] and "21:9" in prompts[-1] and "keep it exactly so" in prompts[-1]
            paint.cmd_busts(types.SimpleNamespace(out=out, who=["rico"], model="gemini-2.5-flash-image", src=None, still=False))
            sc = json.load(open(os.path.join(out, "index.json")))["scenes"]
            assert '"aspectRatio": "3:4"' in bodies[-3] and "never a caricature" in prompts[-3] and "half figure" in prompts[-3]
            assert "mouth open" in prompts[-2] and "eyes closed" in prompts[-1] and Image.open(os.path.join(out, sc["bust-rico"])).size == (800, 800)
            assert {"bust-rico-talk", "bust-rico-blink"} <= set(sc)
            from PIL import ImageDraw
            src = os.path.join(out, "codex"); os.makedirs(src)   # pictures painted elsewhere
            for f in ("bust-kai", "bust-kai-talk"):
                im = Image.new("RGB", (600, 900), (255, 0, 255)); ImageDraw.Draw(im).ellipse((150, 200, 450, 1000), fill=(235, 90, 215))
                if f.endswith("talk"):
                    ImageDraw.Draw(im).rectangle((280, 300, 320, 320), fill=(40, 10, 10))
                im.save(os.path.join(src, f + ".png"))
            n1 = len(calls)
            paint.cmd_busts(types.SimpleNamespace(out=out, who=["all"], model="gemini-2.5-flash-image", src=src, still=False))
            idx = json.load(open(os.path.join(out, "index.json")))
            assert len(calls) == n1 and {"bust-kai", "bust-kai-talk"} <= set(idx["scenes"]) and "bust-kai-blink" not in idx["scenes"]
            k = Image.open(os.path.join(out, idx["scenes"]["bust-kai"]))
            assert k.getpixel((400, 500))[3] == 255 and k.getpixel((10, 10))[3] == 0   # a pink face stays solid, the background goes
            x, y, w, h = idx["boxes"]["bust-kai-talk"]; assert w < 0.3 and h < 0.3
            assert set(paint.BUSTS) >= {"marisol", "tobias", "baako", "hana", "rico", "lola", "sam", "frost", "salado"}
            paint.cmd_creatures(types.SimpleNamespace(out=out, what=["all"], model="gemini-2.5-flash-image"))
            sc = json.load(open(os.path.join(out, "index.json")))["scenes"]
            assert {"deja", "agorzilla", "fronds"} <= set(sc) and '"aspectRatio": "9:16"' in bodies[-1] and Image.open(os.path.join(out, sc["deja"])).mode == "RGBA"
            paint.cmd_panorama(types.SimpleNamespace(out=out, src=None, n=1, model="gemini-3-pro-image-preview"))
            assert '"aspectRatio": "21:9"' in bodies[-1] and "No leaves" in prompts[-1] and "panorama" in json.load(open(os.path.join(out, "drafts", "drafts.json")))["idea"].values()
            paint.cmd_touch(types.SimpleNamespace(out=out, src=None, n=1, model="gemini-3-pro-image-preview", what=[]))
            assert "water wheel" in prompts[-1] and "touched" in json.load(open(os.path.join(out, "drafts", "drafts.json")))["idea"].values()
            paint.cmd_keep(types.SimpleNamespace(out=out, picks=["bar=1"])); assert "bar" not in json.load(open(os.path.join(out, "index.json")))["orig"]
        paint.cmd_drop(types.SimpleNamespace(out=out, places=["bar"]))
        assert [k for k in json.load(open(os.path.join(out, "index.json")))["scenes"] if not k.startswith("bust-") and k not in paint.CREATURES] == ["island"]
if Image:   # a sheet of eight figures on magenta comes out as a strip of eight cut-out cells, feet down
    from PIL import ImageDraw
    sheet = Image.new("RGB", (1600, 900), (255, 0, 255)); d = ImageDraw.Draw(sheet)
    for k in range(8):
        cx, cy = 200 + (k % 4) * 400, 225 + (k // 4) * 450
        d.ellipse((cx - 40, cy - 160, cx + 40, cy + 160), fill=(30 + k * 20, 90, 60), outline=(20, 20, 20), width=6)
    buf = io.BytesIO(); sheet.save(buf, "PNG")
    cast = Image.new("RGB", (1600, 900), (255, 0, 255)); d = ImageDraw.Draw(cast)
    for k in range(10):
        cx, cy = 160 + (k % 5) * 320, 225 + (k // 5) * 450
        d.ellipse((cx - 40, cy - 160, cx + 40, cy + 160), fill=(90, 30 + k * 20, 60), outline=(20, 20, 20), width=6)
    cbuf = io.BytesIO(); cast.save(cbuf, "PNG")
    assert paint.cut(buf.getvalue(), cbuf.getvalue())[1] == 18   # eight townspeople and the ten of the cast
    data, n = paint.cut(buf.getvalue())
    strip = Image.open(io.BytesIO(data))
    assert n == 8 and strip.size == (80 * 8, 120) and strip.mode == "RGBA"
    assert strip.getpixel((2, 2))[3] == 0 and strip.getpixel((40, 60))[3] == 255 and strip.getpixel((40, 117))[3] > 0
    with tempfile.TemporaryDirectory() as out:
        os.makedirs(os.path.join(out, "drafts")); open(os.path.join(out, "drafts", "island-1.webp"), "wb").write(PIC)
        json.dump({"island": ["island-1.webp"]}, open(os.path.join(out, "drafts", "drafts.json"), "w"))
        paint.paint_gemini = lambda plate, prompt, *a, **k: [(cbuf if "ten small" in prompt else buf).getvalue()]
        os.environ["GEMINI_API_KEY"] = "test"; os.environ.pop("OPENAI_API_KEY", None)
        paint.cmd_folk(types.SimpleNamespace(out=out, like=["island=1"], n=1, model=None))
        paint.cmd_keep(types.SimpleNamespace(out=out, picks=["folk=last"]))
        f = json.load(open(os.path.join(out, "index.json")))["scenes"]["folk"]
        assert Image.open(os.path.join(out, f)).size == (80 * 18, 120)
        assert f.startswith("folk-1-") and os.path.exists(os.path.join(out, f)) and "folk=1" in open(os.path.join(out, "drafts", "index.html")).read()
print("ok", len(calls), "calls")

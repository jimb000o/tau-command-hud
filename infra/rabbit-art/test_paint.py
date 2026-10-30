"""The painter for White Rabbit Key, against a stand-in for the image model: drafts, the page to pick from, keep and drop."""
import base64
import io
import json
import os
import tempfile
import types

import paint

assert set(paint.SCENE) == set(paint.PLACES)
for id in paint.PLACES:
    assert os.path.exists(os.path.join(paint.PLATES, id + ".jpg")), f"no plate for {id}: run node infra/rabbit-art/plates.mjs"
game = open(os.path.join(paint.REPO, "rabbit", "scene.js"), encoding="utf-8").read()
for id in paint.PLACES[1:]:
    assert f"    {id}: " in game or f"    {id}:" in game, id
assert "Caribbean Disaster" not in open(paint.__file__).read()

try:
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (1536, 1024), (200, 120, 60)).save(buf, "PNG"); PIC = buf.getvalue()
except ImportError:
    Image, PIC = None, b"\x89PNG fake"
calls = []
def fake(url, data, headers, timeout=240):
    calls.append(url)
    if "generativelanguage" in url:
        body = json.loads(data)
        if "same artist" in body["contents"][0]["parts"][0]["text"]:
            assert len(body["contents"][0]["parts"]) == 4 and "high hill" in body["contents"][0]["parts"][0]["text"]
        assert body["generationConfig"]["imageConfig"]["aspectRatio"] == "16:9" and "Keep the composition" in body["contents"][0]["parts"][0]["text"]
        return {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": base64.b64encode(PIC).decode()}}]}}]}
    if "openai" in url:
        assert b'name="input_fidelity"' in data and b'filename="plate.jpg"' in data
        if b"like-1" in data:
            assert data.count(b'name="image[]"') == 3
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
        paint.cmd_draft(types.SimpleNamespace(out=out, places=["island"], n=3, model=None, sketch="bay", like=["island=1", "bar"]))
        paint.cmd_keep(types.SimpleNamespace(out=out, picks=["island=9"]))
        idx = json.load(open(os.path.join(out, "index.json")))
        lay = idx["layout"]
        assert set(lay["places"]) == set(paint.PLACES[1:]) and lay["fx"] and lay["windows"] and lay["walk"]
        for id, p in lay["places"].items():
            bx, by, bw, bh = p["box"]; assert bx <= p["x"] <= bx + bw and by <= p["y"] <= by + bh + 20, id
        paint.cmd_keep(types.SimpleNamespace(out=out, picks=["island=2"]))
        assert "layout" not in json.load(open(os.path.join(out, "index.json")))
        paint.cmd_drop(types.SimpleNamespace(out=out, places=["bar"]))
        assert list(json.load(open(os.path.join(out, "index.json")))["scenes"]) == ["island"]
print("ok", len(calls), "calls")

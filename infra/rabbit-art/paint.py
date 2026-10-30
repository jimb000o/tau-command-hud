#!/usr/bin/env python3
"""Painted pictures for White Rabbit Key: the island and its eight rooms, repainted once by an image model from the
bare pictures the game draws itself (infra/rabbit-art/plates/, made by plates.mjs), so every place stays where the
game expects it. The game shows them when https://node.tauhud.com/rico/art/index.json lists them, and draws its own
pictures otherwise; smoke, fire, water, light, people and the hour are still drawn on top by rabbit/scene.js.

One key in infra/.env (never in the repository), whichever you have:
  GEMINI_API_KEY   Google AI Studio (about 4 cents a picture)      https://aistudio.google.com/apikey
  OPENAI_API_KEY   OpenAI (about 6 cents a picture)                https://platform.openai.com/api-keys

  infra/rabbit-art/paint.sh draft all            three paintings of each place -> https://node.tauhud.com/rico/art/drafts/
  infra/rabbit-art/paint.sh draft hall bar       three new ones for some places (again if none is right)
  infra/rabbit-art/paint.sh keep island=2 hall=1 ...   puts those on the island; the game shows them at once
  infra/rabbit-art/paint.sh draft island --like island=1 market=2 bar=2   three more, painted like those drafts
  infra/rabbit-art/paint.sh draft island --sketch bay --like ...   the new harbour island (sketch.py); keeping one of
      these moves the places, streets and lights in the game to match it
  infra/rabbit-art/paint.sh drop hall            back to the drawn picture for that place
paint.sh runs this file with the server's python3; with Pillow (apt-get install -y python3-pil) the pictures are small WebP files.
"""
import argparse
import base64
import hashlib
import html
import io
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PLATES = os.path.join(HERE, "plates")
OUT = "/opt/sites/rico/art"
PLACES = ["island", "hall", "market", "radio", "north", "south", "bar", "book", "pier"]

STYLE = ("Repaint this picture as a lush, hand-painted background for a classic 2D point-and-click adventure game from "
         "the late 1990s: gouache and ink on paper, confident dark outlines, rich surface texture, wear and weathering, "
         "warm Caribbean sunlight with deep cool shadows and soft bounced light, atmospheric depth, a lived-in place with "
         "love for small details. Keep the composition, the camera angle and the position, size and shape of every "
         "building, path, window, door, piece of furniture and object exactly as in the input picture; only the "
         "painting changes. No people, no animals in the foreground, no text, no letters, no numbers, no logos, no "
         "signatures, no frame, no user interface.")
LIKE = ("The first picture is the layout to repaint. The other pictures are finished paintings from the same game, "
        "chosen as the best: paint in exactly their style, palette, brushwork, outlines, light and richness of detail, so "
        "that it looks painted by the same artist on the same day, and take what is good in them further.")
DETAIL = {
    "island": "Paint it like a hand-painted adventure game background seen from a high hill: crisp fine ink lines, smooth "
              "painted colour gradients, clean readable shapes, every roof tiled and every wall weathered, winding sandy "
              "paths with fences, steps and little bridges, washing lines, crates, rowing boats on the beach, flowers on "
              "the window sills, fishing nets, birds over the sea, sunlit leaves with bright highlights and deep shadows "
              "under the trees, foam on the reef, clear water showing the sand below. Rich in small things to discover, "
              "but calm and readable at a glance.",
}
# new sketches of the island (sketch.py writes plates/<name>.jpg and plates/<name>.json, where everything stands)
SKETCH = {
    "bay": "The whole island as the map screen of a classic cartoon adventure game, seen from the sea at a high angle: "
           "a big, wild, deeply tropical island, diverse and full of secrets, not a tidy town. A smoking green peak "
           "in the middle with a waterfall into a jungle pool; dense rainforest with huge leaves, banana plants and "
           "palms hides most of the island, so places peek out of the green instead of all being in plain view, and "
           "only a few sandy tracks link them. On the right a ramshackle harbour: wooden shacks on stilts over the "
           "water, a fishing village of palm-thatched huts, a wooden pier, nets, canoes and a small sailing boat; a "
           "market of bamboo stalls under a huge flaming red flamboyant tree; shacks of planks and rusty corrugated "
           "tin painted in bright Caribbean colours, laundry lines, hammocks, chickens. A weathered colonial council "
           "house with a small bell tower and palm-frond awnings is the one official building in town. In a jungle "
           "clearing a ramshackle bamboo radio shack with a tin roof and a mast made of a tall pole and wires. Deep in "
           "the jungle a rebels' camp with tents and a campfire. A banana plantation in rows on the east slope. On "
           "two separate green hills on the left, each behind its own garden wall, the two embassies: the only "
           "buildings that look foreign, a cool blue Georgian house and a warm terracotta villa. A lagoon with "
           "mangroves bitten into the west coast, and alone on a rocky islet in its mouth a red and white lighthouse. "
           "Far out on a sandy point on the right a bamboo beach bar with a palm-thatch roof and torches. A wreck on "
           "the reef, rocks in the surf, a turquoise reef round it all. Nothing European about the island apart from "
           "the embassies and the council house: wood, bamboo, palm thatch, stilts, tin and bright paint. Style: "
           "bright, saturated, comic-like painted adventure art, exaggerated organic shapes, rich painterly brushwork, "
           "curling spiral clouds, deep glowing turquoise water, warm light, humour and a sense of adventure; its own "
           "island, nothing copied. The input is a rough sketch: keep where every building, the lagoon, the harbour, "
           "the pier, the peak and the lighthouse stand and how big they are, but paint it all far richer, with many "
           "more small details of island life.",
}
SCENE = {
    "island": "A small tropical island seen from above at an angle, in the open sea under a clear blue sky: a white "
              "domed council hall with columns in the middle, a round market square with a fountain and striped stalls, "
              "a red and white lighthouse on the left point, two embassy villas, a yellow radio house with a mast, a "
              "beach bar with a thatched roof on the right, a red brick coconut works with a chimney, a rebels' camp "
              "with tents and a lookout, a volcano with a waterfall and a stream, palm trees, jungle, banana plants, "
              "cottages, huts on stilts, a wooden pier with a sailing boat, turquoise shallows, a reef and surf.",
    "hall": "Inside the island's council hall: tall arched windows onto the sea, white columns, a chequered floor, a low "
            "curved dais with three chairs, a lectern with a small bell, sunbeams falling in, old paintings and a few "
            "potted palms, worn wood and plaster.",
    "market": "The island's market square: three stalls with striped awnings full of fruit, crates and baskets, bunting "
              "overhead, green hills and the sea behind, sandy ground with footprints, sacks, a barrow, flowers.",
    "radio": "Inside a small island radio station: a teal wall with a checkered pattern, a shelf of records, a microphone "
             "on an arm, a mixing desk with faders and a turntable, a window onto the sea, posters, cables, a "
             "spinning fan, a coffee mug, a lamp with warm light, clutter of a DJ who loves his job.",
    "north": "Inside the North Wind Embassy: cool blue striped wallpaper, heavy blue curtains at a big window onto the "
             "sea, a long polished desk with a green banker's lamp, papers and a globe, a framed map, a blue flag on "
             "a pole, a stiff, expensive, slightly cold room.",
    "south": "Inside the South Current Embassy: warm terracotta walls, arched windows, a large aquarium with orange fish, "
             "a ceiling fan, a low table with a small cake, wicker chairs, a tiled floor, potted agaves, a warm and "
             "flattering room.",
    "bar": "Inside a beach bar on the island: a wooden wall with long shelves of colourful bottles, a plain green sign "
           "without letters, a counter with stools, cocktails with little umbrellas, a ceiling fan, a string of warm "
           "light bulbs, an open side onto the beach and the sea, driftwood, shells, a cosy and lively place.",
    "book": "Inside the lighthouse: rough stone walls, a stone stair winding up, a small arched window, a lamp hanging "
            "from above throwing a cone of green-tinted light onto a big open book on a wooden lectern, ropes, a "
            "brass telescope, sea charts, an old keeper's chair, quiet and solemn.",
    "pier": "A wooden pier running out into the sea, seen from its start on the beach: planks, rope railings on posts, "
            "a lamp post with a square lantern, a small sailing boat on the water, bright sky with clouds, gulls far "
            "away, sand in the foreground, barrels and coiled ropes.",
}


def api_key(name):
    k = os.environ.get(name, "").strip()
    env = os.path.join(REPO, "infra", ".env")
    if not k and os.path.exists(env):
        for row in open(env, encoding="utf-8"):
            if row.startswith(name + "="):
                k = row.split("=", 1)[1].strip().strip("'\"")
    return k


def provider():
    if api_key("GEMINI_API_KEY"):
        return "gemini"
    if api_key("OPENAI_API_KEY"):
        return "openai"
    sys.exit("No GEMINI_API_KEY or OPENAI_API_KEY in infra/.env. Add one with:\n"
             "  echo 'GEMINI_API_KEY=YOUR_KEY' >> /opt/tau-command-hud/infra/.env")


def post(url, data, headers, timeout=150):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:400]
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(8 * (attempt + 1))
                continue
            sys.exit(f"The painter said {e.code}: {msg}")
        except urllib.error.URLError as e:
            if attempt < 3:
                time.sleep(4)
                continue
            sys.exit(f"The painter could not be reached: {e}")


def mime(raw):
    return "image/png" if raw[:4] == b"\x89PNG" else "image/jpeg" if raw[:2] == b"\xff\xd8" else "image/webp"


def paint_gemini(plate, prompt, n, model, refs=()):
    out = []
    pics = [{"inline_data": {"mime_type": mime(r), "data": base64.b64encode(r).decode()}} for r in (plate, *refs)]
    for i in range(n):   # one picture per call
        print(f"    painting {i + 1} of {n} ...", flush=True)
        body = {"contents": [{"parts": [{"text": prompt}, *pics]}],
                "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9"}}}
        r = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                 json.dumps(body).encode(), {"Content-Type": "application/json", "x-goog-api-key": api_key("GEMINI_API_KEY")})
        parts = ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        img = [p for p in parts if (p.get("inlineData") or p.get("inline_data"))]
        if not img:
            sys.exit("The painter sent no picture back: " + json.dumps(r)[:300])
        out.append(base64.b64decode((img[0].get("inlineData") or img[0].get("inline_data"))["data"]))
    return out


def paint_openai(plate, prompt, n, model, refs=()):
    b = "----rabbit" + hashlib.sha1(plate).hexdigest()[:12]
    fields = {"model": model, "prompt": prompt, "n": str(n), "size": "1536x1024", "quality": "medium", "input_fidelity": "high"}
    body = b"".join(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode() for k, v in fields.items())
    name = "image[]" if refs else "image"
    for i, raw in enumerate((plate, *refs)):
        f = "plate.jpg" if i == 0 else f"like-{i}.{mime(raw)[6:]}"
        body += f"--{b}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{f}\"\r\nContent-Type: {mime(raw)}\r\n\r\n".encode() + raw + b"\r\n"
    body += f"--{b}--\r\n".encode()
    r = post("https://api.openai.com/v1/images/edits", body,
             {"Content-Type": f"multipart/form-data; boundary={b}", "Authorization": "Bearer " + api_key("OPENAI_API_KEY")})
    return [base64.b64decode(d["b64_json"]) for d in r.get("data", [])]


def small(raw):
    """A 1600 x 900 WebP (cropped to 16:9) when Pillow is there, else the picture as it came."""
    try:
        from PIL import Image
    except ImportError:
        kind = "png" if raw[:4] == b"\x89PNG" else "jpg" if raw[:2] == b"\xff\xd8" else "webp"
        return raw, kind
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = im.size
    if w / h > 16 / 9:
        c = int(h * 16 / 9); im = im.crop(((w - c) // 2, 0, (w - c) // 2 + c, h))
    else:
        c = int(w * 9 / 16); im = im.crop((0, (h - c) // 2, w, (h - c) // 2 + c))
    buf = io.BytesIO(); im.resize((1600, 900), Image.LANCZOS).save(buf, "WEBP", quality=80, method=5)
    return buf.getvalue(), "webp"


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "wb") as f:
        f.write(data)
    os.replace(path + ".tmp", path)


def load(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return {}


def page(a):
    drafts = load(os.path.join(a.out, "drafts", "drafts.json"))
    rows = []
    for id in PLACES:
        if id not in drafts:
            continue
        rows.append(f"<h2>{id}</h2><div class=row>")
        for i, f in enumerate(drafts[id], 1):
            rows.append(f"<figure><a href='{f}'><img src='{f}' loading=lazy></a><figcaption><code>{id}={i}</code></figcaption></figure>")
        rows.append("</div>")
    keep = " ".join(f"{id}=1" for id in PLACES if id in drafts)
    write(os.path.join(a.out, "drafts", "index.html"), (
        "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'><title>White Rabbit Key: paintings</title>"
        "<style>body{font:16px system-ui;background:#111;color:#eee;margin:2em auto;max-width:1400px;padding:0 16px}"
        ".row{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}img{width:100%;border-radius:6px}"
        "code{color:#7f7}figure{margin:0}</style><h1>White Rabbit Key: pick a painting for each place</h1>"
        f"<p>Then on the server: <code>infra/rabbit-art/paint.sh keep {keep}</code> (with the numbers you like)</p>{''.join(rows)}").encode())


def cmd_draft(a):
    who = PLACES if "all" in a.places else a.places
    for id in who:
        if id not in SCENE:
            sys.exit(f"No place {id!r}. They are: {', '.join(PLACES)}")
    p = provider()
    model = a.model or ("gemini-2.5-flash-image" if p == "gemini" else "gpt-image-1")
    path = os.path.join(a.out, "drafts", "drafts.json")
    drafts = load(path)
    sketch = getattr(a, "sketch", None)
    if sketch and (who != ["island"] or sketch not in SKETCH):
        sys.exit(f"A sketch is for the island only: draft island --sketch {' | '.join(SKETCH)}")
    refs = [open(f, "rb").read() for f in liked(a, drafts)]
    print(f"{len(who)} places, {a.n} paintings each, with {model}" + (f", painted like {len(refs)} chosen pictures." if refs else "."))
    for id in who:
        plate = open(os.path.join(PLATES, (sketch or id) + ".jpg"), "rb").read()
        prompt = STYLE + " The picture: " + (SKETCH[sketch] if sketch else SCENE[id]) + (" " + DETAIL[id] if id in DETAIL else "") + (" " + LIKE if refs else "")
        raws = (paint_gemini if p == "gemini" else paint_openai)(plate, prompt, a.n, model, refs)
        names = drafts.get(id, []) if refs or sketch else []   # these join the earlier ones, so those stay pickable
        for i, raw in enumerate(raws, len(names) + 1):
            data, kind = small(raw)
            f = f"{id}-{i}-{hashlib.sha1(data).hexdigest()[:8]}.{kind}"
            write(os.path.join(a.out, "drafts", f), data)
            names.append(f)
            if sketch:   # the layout as it was for this painting, so a later sketch cannot move its places
                lay = open(os.path.join(PLATES, sketch + ".json"), "rb").read()
                name = f"layout-{hashlib.sha1(lay).hexdigest()[:8]}.json"
                write(os.path.join(a.out, "drafts", name), lay)
                drafts.setdefault("sketch", {})[f] = name
        drafts[id] = list(names)
        write(path, json.dumps(drafts, indent=1).encode())
        page(a)
        print(f"  {id}: {len(names)} paintings")
    print("Look: https://node.tauhud.com/rico/art/drafts/")


def liked(a, drafts):
    """--like hall=3 market=2 (drafts) or --like hall (the painting kept for it) -> paths of those pictures."""
    kept = load(os.path.join(a.out, "index.json")).get("scenes", {})
    out = []
    for pick in getattr(a, "like", None) or []:
        id, _, n = pick.partition("=")
        try:
            out.append(os.path.join(a.out, "drafts", drafts[id][int(n) - 1]) if n else os.path.join(a.out, kept[id]))
        except (KeyError, ValueError, IndexError):
            sys.exit(f"No painting {pick!r} to paint like.")
    if len(out) > 5:
        sys.exit("At most 5 pictures to paint like; the painter loses the thread with more.")
    return out


def cmd_keep(a):
    drafts = load(os.path.join(a.out, "drafts", "drafts.json"))
    path = os.path.join(a.out, "index.json")
    idx = load(path)
    idx.setdefault("scenes", {})
    for pick in a.picks:
        id, _, n = pick.partition("=")
        try:
            f = drafts[id][int(n) - 1]
        except (KeyError, ValueError, IndexError):
            sys.exit(f"No painting {pick!r}. Run: infra/rabbit-art/paint.sh draft {id if id in SCENE else 'all'}")
        shutil.copyfile(os.path.join(a.out, "drafts", f), os.path.join(a.out, f))
        idx["scenes"][id] = f
        if id == "island":   # a painting of a new sketch brings where everything stands on it
            sk = drafts.get("sketch", {}).get(f)
            if sk:   # paintings of the first harbour sketch (before layouts were stored with them) use plates/bay-1.json
                idx["layout"] = json.load(open(os.path.join(a.out, "drafts", sk) if sk.endswith(".json") else os.path.join(PLATES, sk + "-1.json")))
            else:
                idx.pop("layout", None)
        print(f"{id}: {f}")
    write(path, json.dumps(idx, indent=1).encode())
    print("Done. The island shows them now: https://tauhud.com/rabbit/ (reload)")


def cmd_drop(a):
    path = os.path.join(a.out, "index.json")
    idx = load(path)
    for id in a.places:
        idx.get("scenes", {}).pop(id, None)
        if id == "island":
            idx.pop("layout", None)
    write(path, json.dumps(idx, indent=1).encode())
    print("Back to the drawn pictures for: " + ", ".join(a.places))


def main():
    p = argparse.ArgumentParser(description="Painted pictures for White Rabbit Key")
    p.add_argument("--out", default=OUT)
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft")
    d.add_argument("places", nargs="+", help="all, or some of: " + " ".join(PLACES))
    d.add_argument("--n", type=int, default=3)
    d.add_argument("--model", default=None)
    d.add_argument("--sketch", default=None, help="island only: paint a new sketch instead, e.g. bay")
    d.add_argument("--like", nargs="+", metavar="PLACE=N", help="paint in the style of these drafts, e.g. island=1 market=2")
    k = sub.add_parser("keep")
    k.add_argument("picks", nargs="+", help="place=N, e.g. island=2 hall=1")
    r = sub.add_parser("drop")
    r.add_argument("places", nargs="+")
    a = p.parse_args()
    {"draft": cmd_draft, "keep": cmd_keep, "drop": cmd_drop}[a.cmd](a)


if __name__ == "__main__":
    main()

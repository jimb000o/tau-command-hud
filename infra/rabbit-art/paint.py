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
  infra/rabbit-art/paint.sh ideas --from island=14   three new, bigger islands grown from that one
  infra/rabbit-art/paint.sh looks                the island in each of the three styles, to choose one
  infra/rabbit-art/paint.sh draft hall --look 2  paint in one of those styles
  infra/rabbit-art/paint.sh draft island --sketch bay --like ...   the new harbour island (sketch.py); keeping one of
      these moves the places, streets and lights in the game to match it
  infra/rabbit-art/paint.sh keep island=14 --layout island-14   with places set by hand on that painting
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
# style references for each look, kept on the server only (never in the repository, never published): /opt/rabbit-refs/1, 2, 3
REFS = "/opt/rabbit-refs"
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
           "the embassies and the council house: wood, bamboo, palm thatch, stilts, tin and bright paint. Its own "
           "island, nothing copied. The input is a rough sketch: keep where every building, the lagoon, the harbour, "
           "the pier, the peak and the lighthouse stand and how big they are, but paint it all far richer, with many "
           "more small details of island life.",
}
# new island ideas grown from a painting the owner liked (paint.sh ideas --from island=14): the same style and the
# same front, but a bigger island with secluded, mysterious places that are not all connected
GROW = ("Paint a new, larger version of the island in the first picture, in exactly its style, line and colours. Keep "
        "its harbour front (the wooden stilt houses, the pier, the red flamboyant tree with the market, the lighthouse on "
        "its rock, the radio shack with its mast, the round beach bar, the two embassies on their hill) but make the "
        "island much larger and wilder, so that the harbour is only one part of it. Add these places, each hidden or "
        "far from the others, reached only by a narrow jungle path, a rope bridge, a cave or a canoe, so that the "
        "island feels mysterious and full of wonder: a grotto behind a second, hidden waterfall, glowing softly from "
        "inside; three hills with large drums under small palm roofs, one on each summit; a funny, ramshackle "
        "coconut mint, a crooked factory of planks and tin with pipes, a conveyor belt and a chimney that puffs out "
        "coins; the crumbling ruin of an old colonial fort on a sea cliff, overgrown, with a gigantic rusty key "
        "hanging over its gate; a smugglers' cove with a wreck and caves under the cliffs; and, in a green valley of "
        "their own, the village of the island's first people: round houses of wood and palm thatch, dug-out canoes on "
        "a river, terraced gardens on the slopes, a circle of carved standing stones where their council meets, "
        "painted with dignity and care, a living village, nothing exotic or stereotyped. No people, no text. ")
IDEAS = {
    "valley": "Layout: the harbour town stays in front; the peak rises behind it, and over a high pass, half hidden by "
              "the ridge and clouds, a second, wild valley opens on the far side with the first people's village, the "
              "drum hills and the hidden grotto. The fort ruin and the smugglers' cove sit on the far cliffs.",
    "isles": "Layout: an archipelago. The main island with the harbour in the middle, and around it several smaller "
             "islands, each with its own secret: the first people's island with its village and stone circle, a rocky "
             "islet with the fort ruin, a crescent island with the smugglers' cove, a tiny island with the coconut "
             "mint, linked only by a sandbank, a rope bridge or the sea.",
    "mist": "Layout: one big island; the harbour in front is bright and sunny, while most of the inner island lies "
            "under drifting mist and jungle: the drum hills, the grotto, the fort ruin and the first people's valley "
            "only peek out of the mist here and there, waiting to be discovered.",
}
# three ways to paint the whole game (paint.sh looks paints the island once in each, to choose from)
LOOK_BASE = ("Turn this drawing into a finished background for a 2D adventure game, painted the way the classic ones were: "
             "a confident ink line drawing first, colour painted over it. One clear colour key for the whole picture, "
             "warm light against cool shadows, values grouped into a few big masses, the strongest contrast and the "
             "brightest light where the places are, distance fading into haze, foreground leaves framing the view and "
             "leading the eye inwards. No people, no text, no letters, no numbers, no logos, no signatures, no frame, "
             "no user interface. Style: ")
# the first pass of a look: the sketch turned into the kind of line drawing the old background painters started from
INK = ("Redraw this rough sketch as a confident black ink line drawing on white paper, a background layout drawing for an "
       "animated film or an adventure game: lively hand-drawn lines that swell and taper, organic and slightly "
       "exaggerated shapes, lots of small details (planks, thatch, leaves, ropes, crates, laundry, rocks), no colour, no "
       "shading except a little hatching, no text. Keep where every building, the water, the peak and the lighthouse "
       "stand and how big they are. ")
LOOKS = {
    1: "a lush hand-painted background from a late-1990s point-and-click adventure: gouache and watercolour on paper "
       "with fine, confident dark ink outlines, soft painted colour gradients, near-realistic proportions, a huge "
       "amount of hand-placed detail (worn wood, cracked plaster, moss, laundry, crates, ropes), warm cinematic sunlight "
       "with deep cool shadows and soft bounced light, atmospheric haze in the distance, calm and elegant.",
    2: "a cartoon adventure game painting: strongly exaggerated, bulging organic shapes, nothing straight, buildings "
       "leaning and crooked, knobbly mountains, curling spiral clouds with painted swirls, huge leaves and palms framing "
       "the foreground, deep glowing turquoise and teal water with bright shallows, saturated jungle greens, thick "
       "visible painterly brushstrokes, dark outlines that swell and taper, warm glowing windows, playful, humorous and "
       "a little mysterious, like a hand-painted animated film background.",
    3: "early-1990s Amiga point-and-click adventure pixel art, upscaled: thick black comic outlines, flat saturated "
       "colours in a limited palette with ordered dithering for shading, chunky visible pixels, cartoon caricature "
       "shapes, bold tropical colours (bright turquoise sea, vivid greens, red and yellow accents), jungle leaves "
       "framing the foreground, cheerful comic-book humour.",
}
STYLE_REFS = ("The pictures after the sketch are style references only: match how they are painted (line, colour, light, "
              "brushwork or pixels, level of detail, humour), but never copy their places, buildings, characters, objects "
              "or composition; everything in the picture comes from the sketch and the description.")
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


def small(raw, pixel=False):
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
    if pixel:   # real pixels: 400 x 225 in 48 colours, blown up four times without smoothing
        im = im.resize((400, 225), Image.LANCZOS).quantize(48, dither=Image.Dither.NONE).convert("RGB").resize((1600, 900), Image.NEAREST)
    buf = io.BytesIO(); im.resize((1600, 900), Image.LANCZOS).save(buf, "WEBP", quality=80 if not pixel else 90, method=5)
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
            look = drafts.get("look", {}).get(f)
            idea = drafts.get("idea", {}).get(f)
            tag = (f" &middot; style {look}" if look else "") + (f" &middot; idea {idea}" if idea else "")
            rows.append(f"<figure><a href='{f}'><img src='{f}' loading=lazy></a><figcaption><code>{id}={i}</code>{tag}</figcaption></figure>")
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
    look = getattr(a, "look", None)
    styled = style_refs(look)
    if styled:
        print(f"Style {look}: {len(styled)} reference pictures from {os.path.join(REFS, str(look))}")
    print(f"{len(who)} places, {a.n} paintings each, with {model}" + (f", painted like {len(refs)} chosen pictures." if refs else "."))
    for id in who:
        plate = open(os.path.join(PLATES, (sketch or id) + ".jpg"), "rb").read()
        what = SKETCH[sketch] if sketch else SCENE[id] + (" " + DETAIL[id] if id in DETAIL else "")
        prompt = (LOOK_BASE + LOOKS[look] + " The picture: " + what if look else STYLE + " The picture: " + what) + (" " + LIKE if refs else "") + (" " + STYLE_REFS if styled else "")
        if getattr(a, "ink", False):   # two passes: line drawing, then paint over it
            print("    ink drawing first ...", flush=True)
            line = (paint_gemini if p == "gemini" else paint_openai)(plate, INK + "The picture: " + what, 1, model, [])[0]
            write(os.path.join(a.out, "drafts", f"{id}-ink-{hashlib.sha1(line).hexdigest()[:8]}.png"), line)
            plate = line
        raws = (paint_gemini if p == "gemini" else paint_openai)(plate, prompt, a.n, model, refs + styled)
        names = drafts.get(id, []) if refs or sketch or look else []   # these join the earlier ones, so those stay pickable
        for i, raw in enumerate(raws, len(names) + 1):
            data, kind = small(raw, pixel=look == 3)
            f = f"{id}-{i}-{hashlib.sha1(data).hexdigest()[:8]}.{kind}"
            write(os.path.join(a.out, "drafts", f), data)
            names.append(f)
            if look:
                drafts.setdefault("look", {})[f] = look
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


def style_refs(look):
    """Up to three pictures from REFS/<look>/ (png, jpg, webp), sent along to show how that style is painted."""
    d = os.path.join(REFS, str(look)) if look else None
    if not d or not os.path.isdir(d):
        return []
    fs = sorted(f for f in os.listdir(d) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")))[:3]
    out = []
    for f in fs:
        raw = open(os.path.join(d, f), "rb").read()
        try:   # the painter wants png, jpeg or webp of a sensible size
            from PIL import Image
            im = Image.open(io.BytesIO(raw)).convert("RGB"); im.thumbnail((1280, 1280))
            buf = io.BytesIO(); im.save(buf, "JPEG", quality=88); raw = buf.getvalue()
        except ImportError:
            pass
        out.append(raw)
    return out


def cmd_ideas(a):
    """Three new island ideas grown from a liked painting (--from island=N), in style 2, each with its own layout."""
    drafts = load(os.path.join(a.out, "drafts", "drafts.json"))
    src = liked(argparse.Namespace(out=a.out, like=[a.src]), drafts)[0]
    p = provider()
    model = a.model or ("gemini-2.5-flash-image" if p == "gemini" else "gpt-image-1")
    base = open(src, "rb").read()
    path = os.path.join(a.out, "drafts", "drafts.json")
    for name, how in IDEAS.items():
        print(f"Idea {name}:", flush=True)
        raws = (paint_gemini if p == "gemini" else paint_openai)(base, LOOK_BASE + LOOKS[2] + " " + GROW + how, a.n, model, style_refs(2))
        drafts = load(path)
        names = drafts.get("island", [])
        for raw in raws:
            data, kind = small(raw)
            f = f"island-{len(names) + 1}-{hashlib.sha1(data).hexdigest()[:8]}.{kind}"
            write(os.path.join(a.out, "drafts", f), data)
            names.append(f)
            drafts.setdefault("look", {})[f] = 2
            drafts.setdefault("idea", {})[f] = name
        drafts["island"] = names
        write(path, json.dumps(drafts, indent=1).encode())
        page(a)
        print(f"  island: {len(names)} paintings")
    print("Look: https://node.tauhud.com/rico/art/drafts/")


def cmd_looks(a):
    """The island from the newest sketch, once in each of the three styles."""
    for n in LOOKS:
        print(f"Style {n}:")
        cmd_draft(argparse.Namespace(out=a.out, places=["island"], n=1, model=a.model, sketch="bay", like=None, look=n, ink=True))


def cmd_keep(a):
    drafts = load(os.path.join(a.out, "drafts", "drafts.json"))
    path = os.path.join(a.out, "index.json")
    idx = load(path)
    idx.setdefault("scenes", {})
    for pick in a.picks:
        id, _, n = pick.partition("=")
        try:
            f = drafts[id][-1 if n == "last" else int(n) - 1]   # last: the newest draft of that place
        except (KeyError, ValueError, IndexError):
            sys.exit(f"No painting {pick!r}. Run: infra/rabbit-art/paint.sh draft {id if id in SCENE else 'all'}")
        shutil.copyfile(os.path.join(a.out, "drafts", f), os.path.join(a.out, f))
        idx["scenes"][id] = f
        if id == "island":   # a painting of a new sketch brings where everything stands on it
            sk = drafts.get("sketch", {}).get(f)
            if getattr(a, "layout", None):   # a layout drawn by hand over this very painting (plates/<name>.json)
                idx["layout"] = json.load(open(os.path.join(PLATES, a.layout + ".json")))
            elif sk:   # paintings of the first harbour sketch (before layouts were stored with them) use plates/bay-1.json
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
    d.add_argument("--ink", action="store_true", help="draw it in ink first, then paint over the drawing (twice the cost)")
    d.add_argument("--look", type=int, choices=sorted(LOOKS), default=None, help="paint in style 1, 2 or 3 (see LOOKS)")
    ia = sub.add_parser("ideas")
    ia.add_argument("--from", dest="src", required=True, help="the painting to grow from, e.g. island=14")
    ia.add_argument("--n", type=int, default=1)
    ia.add_argument("--model", default=None)
    lk = sub.add_parser("looks")
    lk.add_argument("--model", default=None)
    k = sub.add_parser("keep")
    k.add_argument("picks", nargs="+", help="place=N or place=last, e.g. island=2 hall=1 bar=last")
    k.add_argument("--layout", default=None, help="island only: where everything stands on that painting, plates/<name>.json")
    r = sub.add_parser("drop")
    r.add_argument("places", nargs="+")
    a = p.parse_args()
    {"draft": cmd_draft, "keep": cmd_keep, "drop": cmd_drop, "looks": cmd_looks, "ideas": cmd_ideas}[a.cmd](a)


if __name__ == "__main__":
    main()

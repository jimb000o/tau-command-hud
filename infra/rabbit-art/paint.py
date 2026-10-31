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
import re
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
PLACES = ["island", "hall", "market", "radio", "north", "south", "bar", "book", "pier",
          "school", "dive", "works", "camp", "ship", "ama", "canoe", "stone", "drums", "circle", "grotto"]
# places whose drawn picture no longer fits what they are now (the Council Tree, the Kettle, the radio on its cliff,
# the embassies in the fort and the villa, the bar on the pier): painted from the island like the new ones
RETHOUGHT = {"hall", "market", "radio", "north", "south", "bar"}
# the places that have no drawn picture to repaint (plates/<id>.jpg): they are painted from the island itself
FROM_ISLAND = ("The first picture is the whole island of this game. Paint, in exactly its style, ink line, colours and light, "
               "a close view of one place on it, as a background for the scene where the player stands there, wide, "
               "with room in the middle and on one side for a person to stand. Look closely at how this place looks on "
               "the island and keep it exactly so: the same building, materials, colours, roof, windows and surroundings, "
               "now seen from inside or close up. Through windows and openings show what one really sees from this very spot on "
               "the island, at eye level, not from above: the neighbouring places, the sea, the hills and mountains, in the "
               "directions where they lie on the island. Spacious and calm, the middle and the front kept open and uncluttered. "
               "No people, no text. The place: ")

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
# the whole game on one large island (paint.sh ideas --from island=18 --idea districts): every place has its own
# quarter, joined only where it makes sense, so each has room, a reason to be where it is and a way to get there
WHOLE = ("Paint a much larger version of the island in the first picture, in exactly its style, ink line and colours, "
         "seen from the same high angle, filling the whole picture, so that every place of the game has its own quarter "
         "with room around it, joined to the others only where it makes sense: a beach road along the harbour, a river, "
         "a rope bridge, a jungle path, a causeway. Keep from the picture: the fortress on the sea cliff with the giant "
         "rusty key, the waterfall and its cave, the red flamboyant tree, the lighthouse on its rock, the radio hut with "
         "its tall wooden mast, the stilt houses and the pier, the old ship at anchor, the round thatched houses on the "
         "hills and the stone circle. The quarters: "
         "1) The harbour town in front, the busiest part: the pier with fishing boats, the harbour master's office with "
         "a flagpole, a net shed with nets drying on poles, a beach bar on stilts over the water, and the market under "
         "the red flamboyant tree with awnings and stalls. "
         "2) The council hall on a small rise above the town: a dignified wooden building with a wide veranda and steps, "
         "the town square in front of it. "
         "3) The school: a cheerful wooden schoolhouse with a bell and a small playing field, near the town but quieter. "
         "4) Radio Coco: the radio hut with its tall mast on a hill of its own, a winding path up. "
         "5) The lighthouse on its rocky islet, reached by a narrow causeway that floods at high tide. "
         "6) The coconut plantation on the gentle slopes: neat rows of coconut palms, drying racks, a farmhouse. "
         "7) The coconut works: a funny, ramshackle factory of planks and tin with crooked pipes, a conveyor belt, a "
         "water wheel on the river and a chimney puffing white smoke. "
         "8) The North Wind Embassy: the fortress on its own cliff, apart, across a rope bridge. "
         "9) The South Current Embassy: the old ship at anchor in its own cove, with a gangway and a jetty. "
         "10) The first people's valley, apart behind the river: their round houses of wood and palm thatch, terraced "
         "gardens, dug-out canoes on the river, the circle of carved standing stones where their council meets, painted "
         "with dignity and care, a living village, nothing exotic or stereotyped. "
         "11) A surveyors' camp of outsiders in a clearing: a few white tents, tripods and measuring poles, crates. "
         "12) Wild places for wonder: the waterfall and its cave, a hidden lagoon, the mountains behind. "
         "Every building clearly readable and separate, with clear paths in front of it. No people, no text, no labels. ")
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
    "hall": "The Council Tree: a huge red flamboyant tree in full bloom on the town's rise, its roots like benches, a ring of "
            "old wooden benches and stools in its shade, a slate board with chalked laws hung on the trunk, a small bell on "
            "a branch, red petals on the ground, the harbour and the sea glittering below, dignified and warm.",
    "market": "The Parasol Café: a small open-air café on a wooden terrace by a little turquoise pool, red and white "
              "parasols, mismatched chairs, a battered tin kettle, a long table where everybody talks, a noticeboard "
              "covered in notes, the harbour and the red tree below, cosy, noisy and friendly.",
    "radio": "Inside Radio Coco, the small wooden radio hut on stilts beside the lattice radio mast on the cliff top, "
             "wooden all through, no concrete, no metal studio: rough plank walls, plank floor, a thatched roof on beams, the painted Radio Coco sign seen backwards through the open front, a microphone on an arm, a mixing desk, a turntable, "
             "shelves of records, a window showing the waterfall and the sea far below, cables, a fan, a coffee mug, "
             "warm lamp light, the clutter of a host who loves the job.",
    "north": "Inside the North Wind Embassy, an imperial hall in the restored fortress: polished pale marble, tall columns, "
             "a long red carpet to a huge desk on a raised dais, a giant map of the island with pins in it, cool blue banners, "
             "gilded frames, a chandelier, the giant key visible through a tall arched window, the same intact palace of pale "
             "stone that the island shows on its cliff, no ruin, no moss, cold, grand, spotless and "
             "far too expensive for an island this size.",
    "south": "The South Current Embassy, a sunny terracotta villa on the jungle slope, as on the island: a cool salon "
             "opening onto the terrace with the turquoise pool (the same pool the island shows beside the villa), "
             "parasols and loungers, a wellness corner with smoothies, a laptop on a rattan table, potted palms, the "
             "jungle and the sea behind, warm, flattering and a little too comfortable.",
    "bar": "Inside Bar La Ola, a wooden bar on stilts at the pier: long shelves of colourful bottles, a counter with stools, "
           "a ceiling fan, a string of warm light bulbs, an open side onto the water and the boats, driftwood and shells, "
           "a ledger and a pencil on the counter, cosy and lively.",
    "book": "Inside the lighthouse: rough stone walls, a stone stair winding up, a small arched window, a lamp hanging "
            "from above throwing a cone of green-tinted light onto a big open book on a wooden lectern, ropes, a "
            "brass telescope, sea charts, an old keeper's chair, quiet and solemn.",
    "pier": "A wooden pier running out into the sea, seen from its start on the beach: planks, rope railings on posts, "
            "a lamp post with a square lantern, a small sailing boat on the water, bright sky with clouds, gulls far "
            "away, sand in the foreground, barrels and coiled ropes.",
    "school": "Inside the island's school, a blue wooden house on stilts: a blackboard with chalk drawings of blocks and "
              "arrows, small desks, exercise books, a globe, children's paintings of the island on the walls, open "
              "shutters onto the red tree and the sea, cheerful and a little chaotic.",
    "dive": "Inside the Reef Proof dive centre, a stilt house over the water: wetsuits and fins on hooks, tanks, a trapdoor "
            "straight into the turquoise water, and odd futuristic diving gear: glowing sensor buoys, a sleek underwater "
            "drone, a screen showing reef readings as a chain of small linked blocks, all hand-made and a bit improvised.",
    "works": "Inside the Coconut Works, a roomy wooden factory hall with a tall brick chimney: at the back a crooked machine "
             "made of bicycles and a church organ, one conveyor belt of coconuts, a few pipes, shelves of oil bottles, "
             "rope and soap at the sides, through a big window the small pond by the stream with the big wooden water wheel "
             "turning in it, exactly as the island shows it beside the works; a wide open plank floor in front, "
             "light through the roof, cheerful but not crowded.",
    "camp": "The surveyors' camp in a clearing: a few white canvas tents, tripods and measuring poles, a folding table with "
            "big plans and maps held down by stones, crates with embassy stamps, a campfire, the jungle all around.",
    "ship": "The deck and cabin of an old wooden ship at anchor, now a museum of things the sea gave back: shelves of "
            "labelled finds (odd shoes, bottles, a piano key, ship's bells), glass cases, an old chart pinned to a table, "
            "brass instruments, portholes onto the cove, warm and curious.",
    "ama": "Inside Ama's house in the first people's village: a round house of wood and palm thatch, woven mats, carved "
           "posts, baskets, a hearth, family photographs next to carved wooden figures, a window onto the stone circle "
           "and the hills, calm and dignified, a living home, nothing exotic or stereotyped.",
    "canoe": "The canoe house by the river: a long open shed of wood and thatch, a dug-out canoe being carved, tools on the "
             "wall, wood shavings, paddles, the river glittering outside.",
    "stone": "The Tide Stone: a tall ancient standing stone on a green hill top above the sea, covered in carved marks in "
             "rows, a few stones around it, wind in the grass, a sweeping view over the island, solemn and mysterious.",
    "drums": "On the summit of a green hill: a small round open hut with a palm-thatch roof sheltering a large carved "
             "drum, two more hills with huts in the distance, the island far below, clouds close by, quiet and awe-filling.",
    "circle": "The Consensus Circle: a wide spiral circle of carved stones in the village green, the round houses around it, "
              "a few benches, the river and the hills behind, evening light, dignified and peaceful.",
    "grotto": "Behind the waterfall: a hidden cave, the curtain of falling water glowing turquoise in front, wet rocks, a "
              "soft light from inside, a stone ledge with an old book and a small keyhole carved in the rock, magical and quiet.",
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


def paint_gemini(plate, prompt, n, model, refs=(), size=None, aspect="16:9"):
    out = []
    pics = [{"inline_data": {"mime_type": mime(r), "data": base64.b64encode(r).decode()}} for r in (plate, *refs)]
    for i in range(n):   # one picture per call
        print(f"    painting {i + 1} of {n} ...", flush=True)
        body = {"contents": [{"parts": [{"text": prompt}, *pics]}],
                "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect, **({"imageSize": size} if size else {})}}}
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


def small(raw, pixel=False, width=1600):
    """A 1600 x 900 WebP (or wider, for a sharp copy) cropped to 16:9 when Pillow is there, else the picture as it came."""
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
    w = min(width, max(1600, im.width))
    buf = io.BytesIO(); im.resize((w, w * 9 // 16), Image.LANCZOS).save(buf, "WEBP", quality=80 if not pixel and w == 1600 else 88, method=5)
    return buf.getvalue(), "webp"


WIDE_ROOM = (" Compose it as one wide panorama for a very wide cinema screen (21:9): the place spreads across the whole width, "
             "nothing important at the far left and right edges, no frame.")


def keep_wide(raw, width=3360):
    """A wide painting as it came (no 16:9 crop), at most `width` pixels wide, as WebP."""
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(width * im.height / im.width)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "WEBP", quality=84, method=5)
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
    for id in PLACES + ["folk"]:
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
        drawn = os.path.join(PLATES, (sketch or id) + ".jpg")
        what = SKETCH[sketch] if sketch else SCENE[id] + (" " + DETAIL[id] if id in DETAIL else "")
        kept = load(os.path.join(a.out, "index.json")).get("scenes", {}).get("island")
        if os.path.exists(drawn) and (sketch or id not in RETHOUGHT or not kept):
            plate = open(drawn, "rb").read()
            prompt = (LOOK_BASE + LOOKS[look] + " The picture: " + what if look else STYLE + " The picture: " + what) + (" " + LIKE if refs else "") + (" " + STYLE_REFS if styled else "")
        else:   # a place with no drawn picture: painted from the island as it is now
            if not kept:
                sys.exit(f"{id} has no drawn picture; keep an island first (paint.sh keep island=N).")
            plate = open(os.path.join(a.out, kept), "rb").read()
            prompt = FROM_ISLAND + what + (" " + LIKE if refs else "") + (" " + STYLE_REFS if styled else "")
        if getattr(a, "ink", False):   # two passes: line drawing, then paint over it
            print("    ink drawing first ...", flush=True)
            line = (paint_gemini if p == "gemini" else paint_openai)(plate, INK + "The picture: " + what, 1, model, [])[0]
            write(os.path.join(a.out, "drafts", f"{id}-ink-{hashlib.sha1(line).hexdigest()[:8]}.png"), line)
            plate = line
        wide = getattr(a, "wide", False) and id != "island"
        if wide and p != "gemini":
            sys.exit("Wide rooms need GEMINI_API_KEY.")
        raws = (paint_gemini(plate, prompt + WIDE_ROOM, a.n, a.model or "gemini-3-pro-image-preview", refs + styled, size="2K", aspect="21:9")
                if wide else (paint_gemini if p == "gemini" else paint_openai)(plate, prompt, a.n, model, refs + styled))
        names = drafts.get(id, []) if refs or sketch or look else []   # these join the earlier ones, so those stay pickable
        for i, raw in enumerate(raws, len(names) + 1):
            data, kind = keep_wide(raw) if wide else small(raw, pixel=look == 3)
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
    ideas = {"districts": WHOLE} if getattr(a, "idea", None) == "districts" else IDEAS
    for name, how in ideas.items():
        print(f"Idea {name}:", flush=True)
        prompt = LOOK_BASE + LOOKS[2] + " " + (how if name == "districts" else GROW + how)
        raws = (paint_gemini if p == "gemini" else paint_openai)(base, prompt, a.n, model, style_refs(2))
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


FOLK_SIZE = (80, 120)   # one figure per cell of the strip the game reads, feet at the bottom middle
FOLK = ("Paint a sheet of eight small full-body townspeople for this game, in exactly the style of the picture: its ink "
        "line, its colours, its light. Two rows of four, evenly spaced, each figure whole and standing well apart from the "
        "others, all the same size, seen from the side in mid-stride, walking to the right, on a plain flat magenta "
        "background (#FF00FF) with no ground, no shadows, no scenery and no text. They live in a small island town of today "
        "and are of mixed ancestry: varied ages, bodies and skin tones, in everyday clothes of now. A fisher woman with a "
        "rolled net over her shoulder; an old man with a walking stick and a newspaper; a farmer carrying a basket of "
        "coconuts; a teacher with a stack of exercise books; a girl with a kite; a carpenter with a plank; a musician with "
        "a small guitar on his back; a woman in a sun hat with a clipboard. No costumes, no grass skirts, no caricature, "
        "no exaggerated features: ordinary, likeable neighbours, drawn with the same care as the island.")


CAST = ("Paint a sheet of ten small full-body characters for this game, in exactly the style of the picture: its ink "
        "line, its colours, its light. Two rows of four, evenly spaced, each figure whole and standing well apart from the "
        "others, all the same size, seen from the side in mid-stride, walking to the right, on a plain flat magenta "
        "background (#FF00FF) with no ground, no shadows, no scenery and no text, in two rows of five. People of a small island town of today, of "
        "mixed ancestry, drawn with care and humour, no caricature, no costumes: "
        "Marisol, a wiry fisher woman in her forties with a teal shirt, a red scarf and a coil of rope; "
        "Tobias, a pale, grey-haired harbour master in a white shirt and navy cap, holding a pair of ceremonial scissors; "
        "Baako, a dark-skinned coconut farmer in his forties in a mustard shirt and straw hat, reading glasses on his nose, "
        "a contract and a red pen in his hand; "
        "Hana, a young schoolteacher with a black bob, glasses and a blue cardigan, a stack of exercise books under her arm; "
        "Rico, a radio host in his thirties with short locs, big headphones round his neck and a pink shirt, a microphone in hand; "
        "Lola, who runs the beach bar, with curly dark red hair, a cream apron, a pencil behind her ear and a ledger; "
        "Old Sam, the bald, white-bearded lighthouse keeper in a dark knitted sweater, carrying a huge old book; "
        "Ambassador Frost, a tall, thin diplomat in a pale blue suit with a lanyard and a tablet; "
        "Ambassador Salado, a sunburnt, round investor in a creased linen suit, sandals and a panama hat, with a laptop bag; "
        "Ama, an elder of the first people's council, a grey-haired woman in her seventies in a cardigan and a skirt with "
        "a woven pattern of her people, walking upright with a carved staff, dignified and kind.")


def cut(raw, more=None):
    """The sheet of townspeople (4 x 2) and, after them, the sheet of the cast (5 x 2) as a strip of cells with transparent backgrounds: the background colour is read off the
    border and keyed out (soft at the edge), each figure is cropped from its part of the 4 x 2 grid and set feet down."""
    from PIL import Image
    cells = []
    for r, cols in ((raw, 4), (more, 5)):
        if r:
            cells += figures(r, cols)
    if not cells:
        sys.exit("No figures found on the sheet; paint it again.")
    cw, ch = FOLK_SIZE
    strip = Image.new("RGBA", (cw * len(cells), ch))
    for i, c in enumerate(cells):
        strip.paste(c, (i * cw, 0))
    buf = io.BytesIO(); strip.save(buf, "WEBP", quality=90, method=5)
    return buf.getvalue(), len(cells)


def figures(raw, cols=4):
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im = im.resize((1200, int(1200 * im.height / im.width)), Image.LANCZOS)
    W, H = im.size
    px = im.load()
    edge = sorted([px[x, 2] for x in range(0, W, 7)] + [px[x, H - 3] for x in range(0, W, 7)] + [px[2, y] for y in range(0, H, 7)])
    bg = edge[len(edge) // 2]
    out = Image.new("RGBA", (W, H))
    o = out.load()
    for y in range(H):
        for x in range(W):
            r, g, b = px[x, y]
            d = abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2])
            a = 0 if d < 90 else 255 if d > 170 else (d - 90) * 255 // 80
            if 0 < a < 255:   # the fringe: take the background's tint out of it
                g = max(g, (r + b) // 2 - 40)
            o[x, y] = (r, g, b, a)
    cw, ch = FOLK_SIZE
    cells = []
    for row in range(2):
        for col in range(cols):
            box = (col * W // cols, row * H // 2, (col + 1) * W // cols, (row + 1) * H // 2)
            part = out.crop(box)
            bb = part.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox()
            if not bb or (bb[3] - bb[1]) < H // 10:
                continue
            fig = part.crop(bb)
            k = min((cw - 4) / fig.width, (ch - 4) / fig.height)
            fig = fig.resize((max(1, int(fig.width * k)), max(1, int(fig.height * k))), Image.LANCZOS)
            cell = Image.new("RGBA", (cw, ch))
            cell.paste(fig, ((cw - fig.width) // 2, ch - fig.height - 1), fig)
            cells.append(cell)
    return cells


# the people you talk to, as the game shows them (rabbit/game.js CANDS and FOLK): looks only, no caricature
BUSTS = {
    "marisol": 'Marisol: runs the Parasol Café on the terrace. Thirties, sturdy. Warm brown skin, black hair in a messy bun stuck through with a pencil, a red scarf, sun-crinkled eyes. Teal shirt with rolled sleeves, a striped apron, a coffee pot in one hand. Direct, friendly grin. Ex-fisherwoman: talks straight, pours strong coffee, still mends nets between orders.',
    "tobias": "Tobias: harbour master at the pier. Sixties, round and proud. Fair, pink-cheeked skin, grey hair parted with a ruler, bushy grey sideburns. Navy captain's cap with gold braid (too big for him), a crisp white uniform shirt with polished brass buttons and a whistle on a chain, a clipboard. Chest puffed out, self-important smile. Loves a ceremony, a rule and a ribbon to cut.",
    "baako": 'Baako: coconut farmer at the Coconut Works. Forties, big and strong. Deep brown skin, short black hair, a short beard, laugh lines. Frayed straw hat pushed back, mustard-yellow work shirt, a coconut in one big hand, a machete-free tool belt with twine. Broad easy smile. Relaxed, generous, measures time in harvests.',
    "hana": 'Hana: the schoolteacher. Thirties, slim. Golden-tan skin, a sharp black bob, big round glasses, a pencil behind her ear, a chalk smudge on her cheek. Blue blouse with a white collar, a stack of exercise books. Calm, attentive, one eyebrow ready for a question. Patient, precise, can silence a room by lowering her glasses.',
    "rico": 'Rico: host of Radio Coco, the island station. Mid thirties, lanky and always moving. Warm brown skin, a huge round afro, a gap-toothed laugh, eyebrows up like he just heard the best news. Big padded studio headphones round his neck with one cable dangling, a microphone held up like a trophy. Loud coral-pink shirt with a white palm-leaf print, unbuttoned at the collar, a shell necklace. Mid-sentence, mouth open, eyes sparkling. The most extroverted person on the island: talks to everyone as if they were live on air.',
    "lola": 'Lola: runs Bar La Ola on the beach. About thirty, strong shoulders. Brown skin, big dark-red curls held back with a bright yellow hibiscus flower, gold hoop earrings, a beauty mark. Cream off-shoulder blouse, a striped bar towel over one shoulder, a cocktail shaker in hand. One eyebrow raised, a teasing half-smile. Knows every secret on the island and tells none of them for free.',
    "sam": "Old Sam: Old Sam, the lighthouse keeper. Seventies, broad and slow. Deep-tanned, wrinkled skin, bald head, a full bushy white beard, kind sleepy eyes under heavy brows. Dark navy knitted fisherman's jumper with a darned elbow, a brass pocket telescope on a cord, an old pipe (unlit) in the corner of his mouth. Gentle, tired smile. Says little, has seen every storm, keeps the light on for everyone.",
    "frost": 'Ambassador Frost: Ambassador Frost of the North Wind Embassy. Fifties, tall and stiff. Pale skin, neat silver-white hair combed flat, a thin pencil moustache, a polished monocle in one eye. Ice-blue tailored suit with a high collar, a silver snowflake pin, white gloves. Thin polite smile that never reaches the eyes. Cold, correct, generous only with paperwork.',
    "salado": "Ambassador Salado: Ambassador Salado of the South Current Embassy. Fifties, tanned and comfortable. Lightly sunburnt skin, dark hair slicked back, a big glossy curled moustache he is clearly proud of, gold tooth. Open coral linen shirt, gold chain, sunglasses pushed up on his head, a cocktail with an umbrella. Smooth salesman's smile, one finger raised as if making a deal. Warm, charming and selling something every minute.",
    "ama": 'Ama: elder of the first people, keeper of the Book. Seventies, small and upright. Dark brown skin, grey hair in a bun with a carved wooden pin, small round glasses on a bead cord. Green woven shawl with a fine pattern, a worn leather-bound book held to her chest. Wise patient look with a hint of mischief. Remembers how everything began and lets others find it out themselves.',
    "wren": 'Captain Wren: Captain Wren, retired marine archaeologist, lives on her old ship. Sixties, wiry. Fair freckled weather-beaten skin, copper hair in a short bob, laugh lines. Faded navy cap, teal shirt with rolled sleeves, a compass and a magnifying glass on cords, a tiny parrot feather tucked in her cap. Amused eyes, crooked grin. Has found three wrecks and lost two hats; tells stories that may be true.',
    "kai": 'Kai: runs Reef Proof, the dive centre. Late twenties, athletic. Brown skin, short black hair still wet, sun-bleached tips. Diving mask pushed up on his forehead, turquoise wetsuit top half unzipped, a shark-tooth necklace, a waterproof watch. Big cheerful grin, thumbs-up energy. Optimist, explains everything with fish.',
    "pim": 'Pim: surveyor working for the embassies. Forties, thin and nervous. Pale skin pink from the sun, sandy hair sticking out under a too-small straw hat, thick glasses slipping down his nose. White shirt with sweat patches and a breast pocket full of pencils, a tape measure, a rolled map under his arm. Worried careful look, mid-gulp. Measures twice, apologises three times.',
    "noor": 'Noor: foreman of the Coconut Works. Forties, compact and capable. Warm brown skin, black curls tied up in a red bandana, round goggles pushed up on her forehead, a smudge of soot on her nose. Yellow work shirt with rolled sleeves, a wrench over her shoulder. Dry knowing half-smile. Fixes anything, believes nothing until she has tested it.',
    "kiko": "Kiko: young canoe builder at the canoe house. Twenties, lean. Brown skin, short black hair, a carpenter's pencil behind his ear, wood shavings in his hair. Red shirt dusted with sawdust, a carved wooden paddle over his shoulder. Calm small smile, quiet eyes. Shy, patient, and the only one who swears he has seen the creature in the jungle.",
}
BUST = ("Paint one character for this game, in exactly the style of the picture: its ink line, painted colours, texture "
        "and warm light, as if painted by the same hand for the same adventure game. {who}. A half figure: from the top of "
        "the head, with a little space above the hair or hat, down to the hips; both arms and hands in the picture, holding "
        "their things; facing us, turned very slightly, standing upright in the middle. The body runs on out of the bottom "
        "edge, which cuts straight across the hips: no rounded or faded bottom, no oval, no vignette. Nothing else in the "
        "picture, on a plain flat magenta (#ff00ff) background with no shadow, no floor and no frame; no magenta in the "
        "person's own colours. Mouth closed in a natural expression. Characterful and funny like a classic adventure game "
        "cast, with real emotion, but never a caricature of anyone's ethnicity, body or age. No text.")
# the frames that make them talk and blink: the same picture changed in one place only, so it can be swapped in
FRAMES = {"talk": "Repaint exactly this picture, identical in every way (pose, size, position, colours, background), with only "
                  "the mouth open, in the middle of saying a word. No text.",
          "blink": "Repaint exactly this picture, identical in every way (pose, size, position, colours, background), with only "
                   "the eyes closed, in a blink. No text."}


def cutout(im):
    """An RGBA copy of a picture painted on a flat background, the background taken away: only what reaches the top and
    the sides, filled from the edges, so a face or a shirt in a colour near the background stays solid."""
    from PIL import Image, ImageDraw, ImageFilter
    W, H = im.size
    px = im.load()
    edge = sorted([px[x, 2] for x in range(0, W, 7)] + [px[2, y] for y in range(0, H, 7)] + [px[W - 3, y] for y in range(0, H, 7)])
    bg = edge[len(edge) // 2]
    dist = lambda c: abs(c[0] - bg[0]) + abs(c[1] - bg[1]) + abs(c[2] - bg[2])
    work, SENT = im.copy(), (1, 254, 3)
    wp = work.load()
    seeds = [(x, 0) for x in range(0, W, 5)] + [(0, y) for y in range(0, H, 5)] + [(W - 1, y) for y in range(0, H, 5)]
    for xy in seeds:
        if wp[xy] != SENT and dist(px[xy]) < 120:
            ImageDraw.floodfill(work, xy, SENT, thresh=110)
    mask = Image.new("L", (W, H), 255); m = mask.load()
    pocket = Image.new("L", (W, H), 0); q = pocket.load()
    for y in range(H):
        for x in range(W):
            if wp[x, y] == SENT:
                m[x, y] = 0
            elif dist(px[x, y]) < 75:
                q[x, y] = 255
    # the background also shows through gaps the fill cannot reach (between an arm and the body): take those too, but
    # only patches of some size, not a pink speck in a shirt
    pocket = pocket.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(7))
    q = pocket.load()
    for y in range(H):
        for x in range(W):
            if q[x, y] and dist(px[x, y]) < 110:
                m[x, y] = 0
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))   # a soft edge, no fringe
    m = mask.load()
    out = Image.new("RGBA", (W, H)); o = out.load()
    for y in range(H):
        for x in range(W):
            r, g, b = px[x, y]
            a = m[x, y]
            if a < 255 and dist((r, g, b)) < 170:   # the rim still tinted by the background: take the tint out
                g = max(g, (r + b) // 2 - 40)
            o[x, y] = (r, g, b, a)
    return out


def unpocket(im, bg=(255, 0, 255)):
    """A cut-out picture with the background colour left in gaps inside the figure: those gaps made clear."""
    from PIL import Image, ImageFilter
    W, H = im.size
    px = im.load()
    dist = lambda c: abs(c[0] - bg[0]) + abs(c[1] - bg[1]) + abs(c[2] - bg[2])
    pocket = Image.new("L", (W, H), 0); q = pocket.load()
    for y in range(H):
        for x in range(W):
            if px[x, y][3] and dist(px[x, y]) < 75:
                q[x, y] = 255
    pocket = pocket.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(7))
    q = pocket.load()
    n = 0
    for y in range(H):
        for x in range(W):
            r, g, b, a = px[x, y]
            if a and q[x, y] and dist((r, g, b)) < 110:
                px[x, y] = (r, max(g, (r + b) // 2 - 40), b, 0); n += 1
    return n


def webp(im):
    buf = io.BytesIO(); im.save(buf, "WEBP", quality=88, method=5)
    return buf.getvalue()


def keyed(raw, size=600, bottom=True):
    """A portrait on a flat background as a square RGBA picture, the background keyed out, the bust standing on the bottom edge."""
    return keyed_set([raw], size, bottom)[0][0]


def keyed_set(raws, size=600, bottom=True):
    """Like keyed, for a picture and its frames (talking, blinking): all cut the same way, so they lie exactly on top of
    each other. Returns the pictures and, for each frame after the first, the box where it differs from the first
    ([x, y, w, h] as parts of the square), or None when it differs all over."""
    from PIL import Image, ImageChops
    ims = []
    for raw in raws:
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        if ims and im.size != ims[0].size:
            im = im.resize(ims[0].size, Image.LANCZOS)
        elif not ims:
            im = im.resize((800, int(800 * im.height / im.width)), Image.LANCZOS)
        ims.append(im)
    outs = [cutout(im) for im in ims]
    bb = outs[0].getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox()
    if not bb:
        sys.exit("No portrait found on the picture; paint it again.")
    W, H = outs[0].size
    if not bottom:   # a creature or leaves: just what was painted, as large as it comes, up to `size` on its long side
        fig = outs[0].crop(bb)
        k = min(1, size / max(fig.size))
        return [webp(fig.resize((max(1, int(fig.width * k)), max(1, int(fig.height * k))), Image.LANCZOS))], []
    box = (bb[0], bb[1], bb[2], H)   # down to the bottom edge, where the body is cut off
    k = min((size - 8) / (box[2] - box[0]), (size - 8) / (box[3] - box[1]))
    cells = []
    for out in outs:
        fig = out.crop(box)
        fig = fig.resize((max(1, int(fig.width * k)), max(1, int(fig.height * k))), Image.LANCZOS)
        cell = Image.new("RGBA", (size, size)); cell.paste(fig, ((size - fig.width) // 2, size - fig.height), fig)
        cells.append(cell)
    boxes = []
    for cell in cells[1:]:
        d = ImageChops.difference(cells[0].convert("RGB"), cell.convert("RGB")).convert("L").point(lambda v: 255 if v > 60 else 0)
        db = d.getbbox()
        if db and (db[2] - db[0]) * (db[3] - db[1]) < 0.12 * size * size:
            pad = size * 0.02
            boxes.append([round(max(0, db[0] - pad) / size, 4), round(max(0, db[1] - pad) / size, 4),
                          round(min(size, db[2] - db[0] + 2 * pad) / size, 4), round(min(size, db[3] - db[1] + 2 * pad) / size, 4)])
        else:
            boxes.append(None)
    return [webp(c) for c in cells], boxes



def cmd_busts(a):
    """Painted half figures of the people you talk to, in the style of the kept island, each with a talking and a blinking
    frame; each is kept at once (bust-<who>, bust-<who>-talk, bust-<who>-blink) and the game shows them instead of the
    drawn face. Run it again for one person to paint them anew. --from DIR (or a .zip) takes pictures painted elsewhere
    instead, named bust-<who>.png with bust-<who>-talk.png and bust-<who>-blink.png beside it."""
    who = list(BUSTS) if "all" in a.who else a.who
    for w in who:
        if w not in BUSTS:
            sys.exit(f"No one called {w!r}. They are: {', '.join(BUSTS)}")
    path = os.path.join(a.out, "index.json")
    idx = load(path)
    if getattr(a, "rekey", False):   # the kept portraits, gaps of background inside them cut out, nothing painted
        from PIL import Image
        sc = idx.get("scenes", {})
        for id in [k for k in sc if k.startswith("bust-") and k.split("-")[1] in who]:
            im = Image.open(os.path.join(a.out, sc[id])).convert("RGBA")
            n = unpocket(im)
            if n:
                data = webp(im); name = f"{id}-{hashlib.sha1(data).hexdigest()[:8]}.webp"
                write(os.path.join(a.out, name), data); sc[id] = name
            print(f"{id}: {n} pixels cut out")
        write(path, json.dumps(idx, indent=1).encode())
        print("Done. Live: https://tauhud.com/rabbit/ (Ctrl+F5)")
        return
    given = {}
    if getattr(a, "src", None):
        import zipfile
        files = {}
        if zipfile.is_zipfile(a.src):
            with zipfile.ZipFile(a.src) as z:
                for n in z.namelist():
                    files[os.path.basename(n)] = z.read(n)
        else:
            for root, _, fs in os.walk(a.src):
                for n in fs:
                    files[n] = open(os.path.join(root, n), "rb").read()
        for n, data in files.items():
            m = re.match(r"bust-([a-z]+)(?:-(talk|blink))?\.(png|webp|jpe?g)$", n.lower())
            if m and m.group(1) in BUSTS:
                given.setdefault(m.group(1), {})[m.group(2) or ""] = data
        who = [w for w in who if "" in given.get(w, {})]
        if not who:
            sys.exit(f"No bust-<name>.png in {a.src}. Names: {', '.join(BUSTS)}")
    else:
        if provider() != "gemini":
            sys.exit("Portraits need GEMINI_API_KEY.")
        kept = idx.get("scenes", {}).get("island")
        if not kept:
            sys.exit("Keep an island first: paint.sh keep island=N")
        plate = open(os.path.join(a.out, idx.get("orig", {}).get("island", kept)), "rb").read()
    for w in who:
        print(f"{w}:", flush=True)
        if w in given:
            raws = given[w]
        else:
            base = paint_gemini(plate, BUST.format(who=BUSTS[w]), 1, a.model, aspect="3:4")[0]
            raws = {"": base}
            if not a.still:
                for f, prompt in FRAMES.items():
                    raws[f] = paint_gemini(base, prompt, 1, a.model, aspect="3:4")[0]
        names = [""] + [f for f in FRAMES if f in raws]
        pics, boxes = keyed_set([raws[f] for f in names], 800)
        idx = load(path); sc = idx.setdefault("scenes", {}); bx = idx.setdefault("boxes", {})
        for f in FRAMES:   # frames of an older picture would not fit the new one
            sc.pop(f"bust-{w}-{f}", None); bx.pop(f"bust-{w}-{f}", None)
        for f, data, box in zip(names, pics, [None] + boxes):
            id = f"bust-{w}" + (f"-{f}" if f else "")
            name = f"{id}-{hashlib.sha1(data).hexdigest()[:8]}.webp"
            write(os.path.join(a.out, name), data)
            sc[id] = name
            if box:
                bx[id] = box
        write(path, json.dumps(idx, indent=1).encode())
    print("Done. Live: https://tauhud.com/rabbit/ (Ctrl+F5)")


CREATURES = {
    "deja": ("1:1", 500, "Paint Déjà, the island's black cat, for this game, in exactly the style of the first picture: its ink line, "
             "painted colours and warm light. A small sleek black cat with bright green eyes, sitting upright, the tail curled "
             "round her paws, looking at us calmly as if she has seen us before. The whole cat and nothing else, on a plain flat "
             "magenta (#ff00ff) background, no ground, no shadow, no text."),
    "agorzilla": ("1:1", 520, "Paint, in exactly the style of the first picture (its ink line, painted colours and light), a glimpse "
                  "of the island's legend in the jungle: the young furry dark-brown ape-like creature from the second picture, "
                  "with big round eyes and a collar of small green lights with a round golden medallion, half hidden behind a "
                  "few big jungle leaves, peeking out shyly: only the head, one shoulder and one hand on a leaf can be seen. "
                  "The leaves and the creature only, on a plain flat magenta (#ff00ff) background, no ground, no shadow, no text."),
    "fronds": ("9:16", 1800, "Paint the nearest foreground of this game's island, in exactly the style of the first picture (its ink "
               "line, painted colours and light): one tall cluster of big tropical leaves growing in from the left edge of the "
               "picture, from the bottom to the top, banana leaves, a palm frond and one curled fern, slightly darker than the "
               "island as the nearest things are, the leaves touching the left edge, open on the right. The leaves only, on a "
               "plain flat magenta (#ff00ff) background, no ground, no sky, no text."),
}
ZILLA_REF = "/opt/sites/agorilla/assets/agorilla.webp"   # how the creature looks (the agorzilla.com checkout on the server)


def cmd_creatures(a):
    """Déjà the cat, the glimpse of Agorzilla in the jungle and the leaves in front, painted like the kept island and
    kept at once (scenes deja, agorzilla, fronds); the game shows them as they arrive. Name some to paint them again."""
    what = list(CREATURES) if "all" in a.what else a.what
    for w in what:
        if w not in CREATURES:
            sys.exit(f"No {w!r}. There are: {', '.join(CREATURES)}")
    if provider() != "gemini":
        sys.exit("Creatures need GEMINI_API_KEY.")
    path = os.path.join(a.out, "index.json")
    idx = load(path)
    kept = idx.get("scenes", {}).get("island")
    if not kept:
        sys.exit("Keep an island first: paint.sh keep island=N")
    plate = open(os.path.join(a.out, idx.get("orig", {}).get("island", kept)), "rb").read()
    for w in what:
        aspect, size, prompt = CREATURES[w]
        refs = [open(ZILLA_REF, "rb").read()] if w == "agorzilla" and os.path.exists(ZILLA_REF) else []
        print(f"{w}:", flush=True)
        data = keyed(paint_gemini(plate, prompt, 1, a.model, refs, aspect=aspect)[0], size, bottom=False)
        f = f"{w}-{hashlib.sha1(data).hexdigest()[:8]}.webp"
        write(os.path.join(a.out, f), data)
        idx = load(path); idx.setdefault("scenes", {})[w] = f
        write(path, json.dumps(idx, indent=1).encode())
    print("Done. Live: https://tauhud.com/rabbit/ (Ctrl+F5)")


def cmd_folk(a):
    """The people who walk about the island, painted in the style of the island as it is now (or --like island=N)."""
    drafts = load(os.path.join(a.out, "drafts", "drafts.json"))
    src = liked(argparse.Namespace(out=a.out, like=a.like), drafts)[0]
    p = provider()
    model = a.model or ("gemini-2.5-flash-image" if p == "gemini" else "gpt-image-1")
    paint = paint_gemini if p == "gemini" else paint_openai
    plate = open(src, "rb").read()
    raws = paint(plate, FOLK, a.n, model)
    cast = paint(plate, CAST, a.n, model) if getattr(a, "cast", True) else []
    path = os.path.join(a.out, "drafts", "drafts.json")
    drafts = load(path)
    names = drafts.get("folk", [])
    for i, raw in enumerate(raws):
        data, n = cut(raw, cast[i] if i < len(cast) else None)
        f = f"folk-{len(names) + 1}-{hashlib.sha1(data).hexdigest()[:8]}.webp"
        write(os.path.join(a.out, "drafts", f), data)
        names.append(f)
        print(f"  folk={len(names)}: {n} figures")
    drafts["folk"] = names
    write(path, json.dumps(drafts, indent=1).encode())
    page(a)
    print("Look: https://node.tauhud.com/rico/art/drafts/  then: infra/rabbit-art/paint.sh keep folk=last")


REWORK = ("Repaint this exact island in exactly its style, ink line, colours, light and composition, keeping everything "
          "where it is, with only these changes: "
          "1) On the cliff top just left of the big waterfall, add Radio Coco: a small wooden radio shack with a tall "
          "wooden mast with a red light on top, a winding path up to it, and give that cliff area more varied landscape: "
          "rocks, a small meadow, flowering bushes, a lookout. "
          "2) The small wooden hut with the radio mast in the middle of the island loses its mast and becomes the "
          "Coconut Works: a funny, crooked little factory of planks and tin with pipes, a chimney puffing white smoke "
          "and a conveyor of coconuts. "
          "3) On the jungle slope below the mountains, between the middle of the island and the waterfall, add the South "
          "Current Embassy: a sunny terracotta villa with a turquoise pool, parasols and a flag, clearly visible. "
          "4) Inside the walls of the old fortress on the right cliff, add a neat modern embassy building with glass "
          "windows and a pale blue flag, so the North Wind Embassy has moved into the old fort; keep the giant rusty key. "
          "5) Keep the old ship at anchor, the red flamboyant tree, the blue house, the stilt houses, the pier, the "
          "lighthouse, the tents, the village with its round houses, the stone circle, the three hills with their huts "
          "and the ancient tower on the left hill exactly as they are. No people, no text. ")


def cmd_rework(a):
    """The kept island (or --from island=N) repainted with the changes in REWORK, everything else where it was."""
    drafts = load(os.path.join(a.out, "drafts", "drafts.json"))
    src = liked(argparse.Namespace(out=a.out, like=[a.src] if a.src else ["island"]), drafts)[0]
    p = provider()
    model = a.model or ("gemini-2.5-flash-image" if p == "gemini" else "gpt-image-1")
    raws = (paint_gemini if p == "gemini" else paint_openai)(open(src, "rb").read(), REWORK, a.n, model)
    path = os.path.join(a.out, "drafts", "drafts.json")
    drafts = load(path)
    names = drafts.get("island", [])
    for raw in raws:
        data, kind = small(raw)
        f = f"island-{len(names) + 1}-{hashlib.sha1(data).hexdigest()[:8]}.{kind}"
        write(os.path.join(a.out, "drafts", f), data)
        names.append(f)
        drafts.setdefault("idea", {})[f] = "rework"
        print(f"  island={len(names)}")
    drafts["island"] = names
    write(path, json.dumps(drafts, indent=1).encode())
    page(a)
    print("Look: https://node.tauhud.com/rico/art/drafts/")


SHARP = ("Reproduce this exact picture at a much higher resolution: the same composition, every building, path, rock, "
         "tree, boat and object in exactly the same place and size, the same colours, ink lines and light. Only add the fine "
         "detail and crisp edges a large print would show. Change nothing else, add nothing, remove nothing, no text.")


def cmd_sharp(a):
    """A sharp, large copy (4K) of the kept island, or of --from island=N, by a model that paints at that size; the layout
    stays valid because everything stays where it was. It joins the island drafts as a new number."""
    drafts = load(os.path.join(a.out, "drafts", "drafts.json"))
    src = liked(argparse.Namespace(out=a.out, like=[a.src] if a.src else ["island"]), drafts)[0]
    if provider() != "gemini":
        sys.exit("A sharp copy needs GEMINI_API_KEY (the model paints at 4K).")
    raw = paint_gemini(open(src, "rb").read(), SHARP, 1, a.model, size=a.size)[0]
    data, kind = small(raw, width=3840)
    path = os.path.join(a.out, "drafts", "drafts.json")
    drafts = load(path)
    names = drafts.get("island", [])
    f = f"island-{len(names) + 1}-{hashlib.sha1(data).hexdigest()[:8]}.{kind}"
    write(os.path.join(a.out, "drafts", f), data)
    names.append(f)
    drafts["island"] = names
    drafts.setdefault("idea", {})[f] = "sharp " + a.size
    write(path, json.dumps(drafts, indent=1).encode())
    page(a)
    try:
        from PIL import Image
        print(f"  island={len(names)}: {Image.open(io.BytesIO(data)).size[0]} pixels wide")
    except ImportError:
        print(f"  island={len(names)}")


WIDE = ("The {done} half of this picture is a finished painting. The {blank} half is empty grey: paint it, carrying the "
        "scene on outward without a seam, in exactly the same style, ink line, colours and light: the same sea, sky, far "
        "mountains and clouds; where land or jungle touches the edge, its coast, rocks, reef and leaves go on a little and "
        "end in open water. Add only quiet things: a few small rocky islets, reefs, sandbanks, a far sail, seabirds. No "
        "buildings, no people, no text. Leave the {done} half exactly as it is.")


def cmd_hires(a):
    """Every kept picture (or the places named) in high resolution and wide: first repainted sharp and large with the
    same composition (the island at 4K, the rooms at 2K, so the page stays light enough), then carried on past its left
    and right edges, so a wide screen shows the painting from edge to edge. The island grows by half its width on each
    side, a room by a quarter. The middle stays the sharp copy of the kept picture: it is laid back over the painted
    sides, blended over a narrow seam, so the layout's click areas still fit. Run it again after keeping a new picture."""
    from PIL import Image, ImageDraw
    path = os.path.join(a.out, "index.json")
    idx = load(path)
    sc, orig = idx.get("scenes", {}), idx.setdefault("orig", {})
    ids = [i for i in (sc if "all" in a.places else a.places) if i in SCENE]
    if not ids:
        sys.exit("Nothing kept to sharpen yet. Run: infra/rabbit-art/paint.sh keep island=N")
    if provider() != "gemini":
        sys.exit("High resolution needs GEMINI_API_KEY.")
    def png(x):
        b = io.BytesIO(); x.save(b, "PNG"); return b.getvalue()
    for id in ids:
        src = orig.get(id, sc[id])   # always from the picture that was kept, never from an earlier wide copy
        size = "4K" if id == "island" else "2K"
        print(f"{id}: {src}", flush=True)
        im = Image.open(os.path.join(a.out, src)).convert("RGB")
        if im.width / im.height > 1.9:   # a panorama is painted large and wide already
            print("  already wide, left as it is"); continue
        if not a.no_sharp:
            data, _ = small(paint_gemini(png(im), SHARP, 1, a.model, size=size)[0], width=3840 if id == "island" else 2560)
            im = Image.open(io.BytesIO(data)).convert("RGB")
        W, H = im.size; e = (W // 2 if id == "island" else W // 4) if getattr(a, "wide", False) else 0; f = max(8, W // 40)
        side = {}   # f: the seam blends over f pixels
        for done, blank in ((("right", "left"), ("left", "right")) if e else ()):
            h = W // 2; c = Image.new("RGB", (W, H), (128, 128, 128))
            c.paste(im.crop((0, 0, h, H)) if blank == "left" else im.crop((W - h, 0, W, H)), (W - h, 0) if blank == "left" else (0, 0))
            r = Image.open(io.BytesIO(paint_gemini(png(c), WIDE.format(done=done, blank=blank), 1, a.model, size=size)[0])).convert("RGB").resize((W, H), Image.LANCZOS)
            side[blank] = r.crop((h - e, 0, h + f, H)) if blank == "left" else r.crop((h - f, 0, h + e, H))
        out = Image.new("RGB", (W + 2 * e, H))
        if e:
            out.paste(side["left"], (0, 0)); out.paste(side["right"], (W + e - f, 0))
        mask = Image.new("L", (W, H), 255); d = ImageDraw.Draw(mask)
        for i in range(f):
            v = int(255 * (i + 0.5) / f); d.line([(i, 0), (i, H)], fill=v); d.line([(W - 1 - i, 0), (W - 1 - i, H)], fill=v)
        out.paste(im, (e, 0), mask)
        buf = io.BytesIO(); out.save(buf, "WEBP", quality=84, method=5); data = buf.getvalue()
        name = f"{id}-hd-{hashlib.sha1(data).hexdigest()[:8]}.webp"
        write(os.path.join(a.out, name), data)
        orig[id] = src; sc[id] = name
        write(path, json.dumps(idx, indent=1).encode())   # after each picture, so a stop half way keeps what is done
        print(f"  {name}: {out.size[0]} x {out.size[1]} pixels", flush=True)
    print("Done. Live: https://tauhud.com/rabbit/ (Ctrl+F5)")


def cmd_narrow(a):
    """Undo the painted sides: every kept wide copy (hires --wide) is cut back to its sharp 16:9 middle, nothing is painted."""
    from PIL import Image
    path = os.path.join(a.out, "index.json")
    idx = load(path)
    sc, orig = idx.get("scenes", {}), idx.get("orig", {})
    for id, f in list(sc.items()):
        if id not in orig or f == orig[id]:
            continue
        im = Image.open(os.path.join(a.out, f)).convert("RGB")
        w = round(im.height * 16 / 9)
        if im.width <= w + 4:
            continue
        x = (im.width - w) // 2
        buf = io.BytesIO(); im.crop((x, 0, x + w, im.height)).save(buf, "WEBP", quality=84, method=5); data = buf.getvalue()
        name = f"{id}-hd-{hashlib.sha1(data).hexdigest()[:8]}.webp"
        write(os.path.join(a.out, name), data)
        sc[id] = name
        print(f"{id}: {name}, {w} x {im.height}")
    write(path, json.dumps(idx, indent=1).encode())
    print("Done. Live: https://tauhud.com/rabbit/ (Ctrl+F5)")


PANORAMA = ("Repaint the island in this picture as one wide panoramic painting, composed for a very wide cinema screen, in "
            "exactly its style, ink line, colours and light. The same island with every place in the same arrangement: the "
            "hills with the round huts and the stone circle on the left, the radio mast on its cliff, the coconut works with "
            "its chimney and a water wheel on the stream beside it, the café terrace with the little pool and parasols, the red council tree, the stilt houses and the "
            "pier, the lighthouse on its rock at the front, the old ship in the bay, the waterfall with the cave behind it, "
            "on the right cliff the North Wind Embassy with the big key: no ruin, but an intact, imposing imperial seat, "
            "a restored fortress turned palace of power, clean pale stone, tall walls, a grand gate and stair, a domed hall, "
            "rows of tall windows, banners and a big flag in the north wind, polished cannons as decoration, everything "
            "spotless, cold and expensive, looking down on the island; the terracotta villa of the South Current Embassy on "
            "the jungle slope with its terrace, turquoise pool and parasols; the mountains behind. "
            "The island sits in the middle with open sea, reefs and a few small rocky islets around it, so that it can be "
            "seen whole on a wide screen; calm sea at the very top corners and the bottom edge. No leaves, palms or "
            "branches in the foreground and nothing framing the picture: the view is clear from edge to edge. No text.")


TOUCH = ("Repaint exactly this island picture, identical in every way (the same composition, every place where it is, "
         "the style, ink line, colours and light, the sea and the sky), changing only these details so that each place "
         "looks from outside the way it does inside: {what} No leaves or palms in the foreground. No text.")
TOUCH_PLACES = ("beside the Coconut Works with its brick chimney, a small round pond fed by the stream with a big wooden "
                "water wheel turning in it; at the terracotta villa of the South Current Embassy on the jungle slope, a "
                "clearly visible terrace with a bright turquoise swimming pool, parasols and loungers; Radio Coco a small "
                "wooden hut of planks on stilts at the foot of the radio mast; the North Wind Embassy an intact imperial "
                "palace of clean pale stone with a dome, banners and the big key, no ruin.")


def cmd_touch(a):
    """Island drafts that keep the picture and change a few details (default: the places outside as they are inside:
    pond and water wheel at the Coconut Works, the villa's pool, the wooden radio hut, the imperial North Wind)."""
    a.prompt = TOUCH.format(what=" ".join(a.what) if a.what else TOUCH_PLACES)
    a.idea = "touched"
    cmd_panorama(a)


def cmd_panorama(a):
    """New island drafts in one wide piece (21:9, painted at 4K), from the kept island or --from island=N: the same
    places, more sea around them, no leaves framing the view. Pick one, then its click areas are set by hand."""
    drafts = load(os.path.join(a.out, "drafts", "drafts.json"))
    src = liked(argparse.Namespace(out=a.out, like=[a.src] if a.src else ["island"]), drafts)[0]
    if provider() != "gemini":
        sys.exit("A panorama needs GEMINI_API_KEY.")
    from PIL import Image
    path = os.path.join(a.out, "drafts", "drafts.json")
    for raw in paint_gemini(open(src, "rb").read(), getattr(a, "prompt", PANORAMA), a.n, a.model, size="4K", aspect="21:9"):
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        if im.width > 5040:
            im = im.resize((5040, round(5040 * im.height / im.width)), Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, "WEBP", quality=84, method=5); data = buf.getvalue()
        drafts = load(path)
        names = drafts.get("island", [])
        f = f"island-{len(names) + 1}-{hashlib.sha1(data).hexdigest()[:8]}.webp"
        write(os.path.join(a.out, "drafts", f), data)
        names.append(f)
        drafts["island"] = names
        drafts.setdefault("idea", {})[f] = getattr(a, "idea", "panorama")
        write(path, json.dumps(drafts, indent=1).encode())
        print(f"  island={len(names)}: {im.width} x {im.height}")
    page(a)
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
        idx.get("orig", {}).pop(id, None)   # a new pick: its sharp wide copy is made again by hires
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
        idx.get("orig", {}).pop(id, None)
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
    d.add_argument("--wide", action="store_true", help="rooms: one wide 21:9 picture at 2K (Gemini 3), not cropped to 16:9")
    d.add_argument("--look", type=int, choices=sorted(LOOKS), default=None, help="paint in style 1, 2 or 3 (see LOOKS)")
    ia = sub.add_parser("ideas")
    ia.add_argument("--from", dest="src", required=True, help="the painting to grow from, e.g. island=14")
    ia.add_argument("--n", type=int, default=1)
    ia.add_argument("--idea", default=None, choices=["districts"], help="districts: every place of the game in its own quarter (WHOLE)")
    ia.add_argument("--model", default=None)
    lk = sub.add_parser("looks")
    lk.add_argument("--model", default=None)
    k = sub.add_parser("keep")
    k.add_argument("picks", nargs="+", help="place=N or place=last, e.g. island=2 hall=1 bar=last")
    k.add_argument("--layout", default=None, help="island only: where everything stands on that painting, plates/<name>.json")
    hr = sub.add_parser("hires")
    hr.add_argument("places", nargs="*", default=["all"], help="all (default), or some of: " + " ".join(PLACES))
    hr.add_argument("--no-sharp", action="store_true", help="keep the resolution")
    hr.add_argument("--wide", action="store_true", help="also paint on past the left and right edges (shows a seam)")
    sub.add_parser("narrow")
    cr = sub.add_parser("creatures")
    cr.add_argument("what", nargs="*", default=["all"], help="all (default), or some of: " + " ".join(CREATURES))
    cr.add_argument("--model", default="gemini-2.5-flash-image")
    bu = sub.add_parser("busts")
    bu.add_argument("who", nargs="*", default=["all"], help="all (default), or some of: " + " ".join(BUSTS))
    bu.add_argument("--model", default="gemini-2.5-flash-image")
    bu.add_argument("--from", dest="src", default=None, help="a folder or .zip of pictures painted elsewhere (bust-<name>.png, -talk.png, -blink.png)")
    bu.add_argument("--still", action="store_true", help="no talking and blinking frames")
    bu.add_argument("--rekey", action="store_true", help="paint nothing: cut gaps of background out of the kept portraits")
    to = sub.add_parser("touch")
    to.add_argument("what", nargs="*", help="what to change (default: the places outside as they are inside)")
    to.add_argument("--from", dest="src", default=None, help="the painting, e.g. island=22 (default: the kept island)")
    to.add_argument("--n", type=int, default=2)
    to.add_argument("--model", default="gemini-3-pro-image-preview")
    pa = sub.add_parser("panorama")
    pa.add_argument("--from", dest="src", default=None, help="the painting, e.g. island=21 (default: the kept island)")
    pa.add_argument("--n", type=int, default=3)
    pa.add_argument("--model", default="gemini-3-pro-image-preview")
    hr.add_argument("--model", default="gemini-3-pro-image-preview")
    sh = sub.add_parser("sharp")
    sh.add_argument("--from", dest="src", default=None, help="the painting, e.g. island=21 (default: the kept island)")
    sh.add_argument("--size", default="4K", choices=["2K", "4K"])
    sh.add_argument("--model", default="gemini-3-pro-image-preview")
    rw = sub.add_parser("rework")
    rw.add_argument("--from", dest="src", default=None, help="the painting to rework, e.g. island=18 (default: the kept island)")
    rw.add_argument("--n", type=int, default=2)
    rw.add_argument("--model", default=None)
    fo = sub.add_parser("folk")
    fo.add_argument("--like", nargs="+", default=["island"], metavar="PLACE=N", help="the painting whose style they take")
    fo.add_argument("--n", type=int, default=1)
    fo.add_argument("--no-cast", dest="cast", action="store_false", help="only the townspeople, not the named cast")
    fo.add_argument("--model", default=None)
    r = sub.add_parser("drop")
    r.add_argument("places", nargs="+")
    a = p.parse_args()
    {"draft": cmd_draft, "keep": cmd_keep, "drop": cmd_drop, "looks": cmd_looks, "ideas": cmd_ideas, "folk": cmd_folk, "rework": cmd_rework, "sharp": cmd_sharp, "hires": cmd_hires, "panorama": cmd_panorama, "touch": cmd_touch, "narrow": cmd_narrow, "busts": cmd_busts, "creatures": cmd_creatures}[a.cmd](a)


if __name__ == "__main__":
    main()

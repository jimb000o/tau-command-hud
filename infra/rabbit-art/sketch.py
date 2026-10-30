#!/usr/bin/env python3
"""A new island for White Rabbit Key, drawn as a rough sketch for the painter: a big, wild tropical island. A smoking
peak in the middle under dense jungle, a shanty harbour of wooden and tin shacks round a market, a fishing village of
huts on stilts at the pier, a bamboo radio shack hidden in a jungle clearing, a rebels' camp, a banana plantation,
mangroves and a lagoon, the embassies on their own hills, the lighthouse alone on a rocky islet, the beach bar far out
on a sandy point. Not everything is joined by a road, and not everything is seen at a glance. It writes the sketch (plates/bay.jpg) and, from the same numbers, where everything stands
on it (plates/bay.json): the places a click finds, the streets people walk, windows that light up at night, smoke,
torches, the waterfall, the lighthouse beam, the radio mast and the coast the surf runs along. When a painting of this
sketch is kept, paint.py puts that layout next to it in index.json and rabbit/scene.js follows it.

  python3 infra/rabbit-art/sketch.py        (needs Pillow; run again after changing a number here)
"""
import json
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, HZ = 1600, 900, 250
R = random.Random(7)

# where the places stand: ground point and the box a click finds them in (world = 1600 x 900, as in scene.js);
# all inside what the game shows of the world at once (about x 200 to 1400, y 110 to 790)
PLACES = {
    "hall":   {"x": 1010, "y": 520, "box": [945, 420, 130, 110], "name": "Council Hall"},
    "market": {"x": 1090, "y": 640, "box": [1000, 600, 180, 70], "name": "Market square"},
    "radio":  {"x": 760, "y": 575, "box": [705, 420, 110, 165], "name": "Radio Coco"},
    "north":  {"x": 420, "y": 420, "box": [355, 345, 130, 85], "name": "North Wind Embassy"},
    "south":  {"x": 600, "y": 470, "box": [548, 405, 104, 75], "name": "South Current Embassy"},
    "bar":    {"x": 1345, "y": 690, "box": [1278, 632, 134, 72], "name": "Bar La Ola"},
    "book":   {"x": 262, "y": 712, "box": [228, 500, 70, 220], "name": "The Lighthouse"},
    "pier":   {"x": 1190, "y": 752, "box": [1135, 705, 110, 100], "name": "The pier"},
}
# only a few roads: the harbour streets, the embassy road, a jungle trail to the radio, the beach to the bar
WALK = [[[1010, 530], [1050, 590], [1090, 630]], [[1090, 650], [1150, 700], [1190, 715]], [[1170, 660], [1250, 690], [1330, 700]],
        [[420, 430], [500, 450], [600, 478]], [[600, 478], [660, 540], [760, 585]], [[940, 640], [1000, 650], [1060, 645]],
        [[880, 760], [1000, 770], [1120, 760]]]


def coast():
    """The island's outline: big and ragged, a lagoon bitten out of the left, a sandy point far out on the right."""
    pts = []
    for i in range(160):
        a = i / 160 * math.pi * 2
        r = 1 + 0.07 * math.sin(a * 3 + 0.4) + 0.05 * math.sin(a * 5 + 2) + 0.03 * math.sin(a * 11) + (R.random() - 0.5) * 0.04
        r += max(0, math.cos(a)) ** 8 * max(0, math.sin(a) + 0.4) * 0.12      # the bar's sandy point
        pts.append([round(820 + math.cos(a) * 660 * r), round(540 + math.sin(a) * 260 * r)])
    return pts


def poly(d, pts, fill, outline="#22303a", width=2):
    d.polygon([tuple(p) for p in pts], fill=fill)
    if outline:
        d.line([tuple(p) for p in pts] + [tuple(pts[0])], fill=outline, width=width, joint="curve")


def house(d, x, y, w, h, wall, roof, win, roof_h=None, door="#3a6b4e", shutters="#2f7d5b", porch=False):
    """A clapboard house with a tin or tiled roof, standing on (x, y); its windows go into win for the night."""
    rh = roof_h or h * 0.6
    poly(d, [[x - w / 2, y], [x + w / 2, y], [x + w / 2, y - h], [x - w / 2, y - h]], wall)
    for k in range(int(h // 5)):   # the boards
        d.line([(x - w / 2 + 2, y - 3 - k * 5), (x + w / 2 - 2, y - 3 - k * 5)], fill=(0, 0, 0, 30), width=1)
    poly(d, [[x - w / 2 - 6, y - h], [x + w / 2 + 6, y - h], [x + w / 4, y - h - rh], [x - w / 4, y - h - rh]], roof)
    n = max(1, int(w // 26))
    for k in range(n):
        wx = x - w / 2 + (k + 0.5) * w / n - 4
        wy = y - h * 0.72
        if porch or n < 2 or k != n // 2:
            poly(d, [[wx, wy], [wx + 8, wy], [wx + 8, wy + 11], [wx, wy + 11]], "#24323c", None)
            d.rectangle([wx - 4, wy, wx - 1, wy + 11], fill=shutters)
            d.rectangle([wx + 9, wy, wx + 12, wy + 11], fill=shutters)
            win.append([round(wx), round(wy), 8, 11])
    d.rectangle([x - 5, y - 15, x + 5, y], fill=door, outline="#22303a")
    if porch:
        d.rectangle([x - w / 2, y - h * 0.38, x + w / 2, y - h * 0.34], fill="#fbf3df")
        for k in range(int(w // 14) + 1):
            px = x - w / 2 + k * 14
            d.line([(px, y), (px, y - h * 0.36)], fill="#fbf3df", width=2)


def facade(d, x, y, w, h, wall, win):
    """A tall harbour house with a curved gable, as along a Caribbean waterfront: two floors, a balcony, shutters."""
    poly(d, [[x - w / 2, y], [x + w / 2, y], [x + w / 2, y - h], [x + w / 4, y - h - 8], [x, y - h - 16], [x - w / 4, y - h - 8], [x - w / 2, y - h]], wall)
    d.rectangle([x - w / 2 - 2, y - h - 2, x + w / 2 + 2, y - h + 2], fill="#fbf3df")
    for row in (0.28, 0.66):
        for k in (-1, 1):
            wx, wy = x + k * w / 4 - 4, y - h * (1 - row) - 6
            d.rectangle([wx, wy, wx + 8, wy + 12], fill="#24323c")
            d.rectangle([wx - 3, wy, wx - 1, wy + 12], fill="#fbf3df")
            d.rectangle([wx + 9, wy, wx + 11, wy + 12], fill="#fbf3df")
            win.append([round(wx), round(wy), 8, 12])
    d.line([(x - w / 2 + 2, y - h * 0.45), (x + w / 2 - 2, y - h * 0.45)], fill="#22303a", width=2)
    d.rectangle([x - 5, y - 16, x + 5, y], fill="#2f5d4a", outline="#22303a")


def palm(d, x, y, h, lean):
    tx, ty = x + lean, y - h
    d.line([(x, y), (x + lean * 0.4, y - h * 0.5), (tx, ty)], fill="#8a6a44", width=5, joint="curve")
    for k in range(7):
        a = -math.pi / 2 + (k - 3) * 0.55 + (R.random() - 0.5) * 0.2
        L = 30 + R.random() * 10
        ex, ey = tx + math.cos(a) * L * 1.2, ty + math.sin(a) * L * 0.55 + 14
        d.line([(tx, ty), ((tx + ex) / 2, (ty + ey) / 2 - 8), (ex, ey)], fill=("#3f8a3a" if k % 2 else "#5fae46"), width=6, joint="curve")
    d.ellipse([tx - 4, ty - 2, tx + 4, ty + 6], fill="#6b4a2a")


def tree(d, x, y, r, c0="#2f7a3c", c1="#4f9e48"):
    d.ellipse([x - r, y - r * 0.9, x + r, y + r * 0.9], fill=c0, outline="#1f4a30", width=2)
    d.ellipse([x - r * 0.6, y - r * 0.75, x + r * 0.2, y - r * 0.1], fill=c1)


def swirl(d, x, y, r, turns, col, width):
    """A curled cloud: a spiral drawn in one stroke, the painter makes a rolling cloud of it."""
    pts = [(x + math.cos(t) * r * (1 - t / (turns * 6.3)) * 1.8, y + math.sin(t) * r * (1 - t / (turns * 6.3)) * 0.7) for t in [k * 0.12 for k in range(int(turns * 52))]]
    d.line(pts, fill=col, width=width, joint="curve")


def hut(d, x, y, w, h, wall, win, stilts=0, roof="#c9a24a", tin=False):
    """A wooden or bamboo hut with a palm-thatch (or rusty tin) roof, on stilts when it stands in water or a swamp."""
    if stilts:
        for sx in (x - w / 2 + 3, x, x + w / 2 - 3):
            d.line([(sx, y), (sx, y + stilts)], fill="#6b4422", width=3)
    poly(d, [[x - w / 2, y], [x + w / 2, y], [x + w / 2, y - h], [x - w / 2, y - h]], wall)
    for k in range(int(w // 5)):   # planks or bamboo
        d.line([(x - w / 2 + 2 + k * 5, y - 1), (x - w / 2 + 2 + k * 5, y - h + 1)], fill=(60, 30, 10, 60), width=1)
    rh = h * 0.75
    if tin:
        poly(d, [[x - w / 2 - 5, y - h], [x + w / 2 + 5, y - h + 4], [x + w / 2 + 2, y - h - rh * 0.6], [x - w / 2 - 2, y - h - rh * 0.5]], "#a8643a")
    else:
        poly(d, [[x - w / 2 - 8, y - h + 3], [x + w / 2 + 8, y - h + 3], [x, y - h - rh]], roof)
        for k in range(5):
            f = k / 4
            d.line([(x, y - h - rh), (x - w / 2 - 8 + f * (w + 16), y - h + 3)], fill=(110, 70, 20, 120), width=1)
    wx, wy = x + w / 5, y - h * 0.7
    d.rectangle([wx - 3, wy, wx + 4, wy + 7], fill="#24323c")
    win.append([round(wx - 3), round(wy), 7, 7])
    d.rectangle([x - w / 4 - 4, y - h * 0.6, x - w / 4 + 4, y], fill="#3a2a1a")


def tent(d, x, y, w, c="#5f6b3a"):
    poly(d, [[x - w / 2, y], [x + w / 2, y], [x, y - w * 0.6]], c)
    d.polygon([(x - 4, y), (x + 4, y), (x, y - w * 0.3)], fill="#22303a")


def main():
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im, "RGBA")
    for y in range(H):   # sky and sea
        if y < HZ:
            f = y / HZ
            c = (round(70 + 100 * f), round(160 + 60 * f), round(220 + 20 * f))
        else:
            f = (y - HZ) / (H - HZ)
            c = (round(30 - 14 * f), round(165 - 70 * f), round(200 - 60 * f))
        d.line([(0, y), (W, y)], fill=c)
    for x, y, r in [(240, 80, 60), (1180, 70, 70), (1470, 150, 50), (560, 50, 40)]:
        for k in range(3):
            swirl(d, x + k * 28, y + k * 7, r - k * 11, 1.4, (240, 248, 252), 15 - k * 4)
    win, fx = [], []
    shore = coast()
    poly(d, [[820 + (x - 820) * 1.06, 540 + (y - 540) * 1.13] for x, y in shore], (110, 212, 205, 255), None)
    poly(d, [[820 + (x - 820) * 1.02, 540 + (y - 540) * 1.05] for x, y in shore], (165, 230, 218, 255), None)
    poly(d, shore, "#efd49c")
    poly(d, [[820 + (x - 820) * 0.95, 528 + (y - 540) * 0.86] for x, y in shore], "#4f9a46", None)
    # the lagoon bitten into the west coast, mangroves round it
    d.ellipse([130, 510, 430, 790], fill=(120, 214, 200))   # it opens to the sea in the south-west
    d.ellipse([170, 640, 400, 800], fill=(150, 225, 212))
    for k in range(22):
        a = math.pi * 1.05 + k / 21 * math.pi * 1.15
        mx, my = 280 + math.cos(a) * 150, 650 + math.sin(a) * 140
        tree(d, mx, my, 9, "#2d6a3a", "#4a8c44")
        d.line([(mx - 6, my + 6), (mx - 9, my + 14)], fill="#5a4030", width=2)
        d.line([(mx + 6, my + 6), (mx + 9, my + 14)], fill="#5a4030", width=2)
    # the lighthouse alone on its rocky islet off the south-west, a rowing boat tied up below
    poly(d, [[212, 722], [236, 696], [290, 694], [318, 718], [292, 740], [228, 740]], "#7a8f98")
    poly(d, [[244, 712], [282, 712], [275, 545], [251, 545]], "#fbf3df")
    for k in range(3):
        y0 = 702 - k * 52
        poly(d, [[244 + k * 2, y0], [282 - k * 2, y0], [281 - k * 2, y0 - 22], [245 + k * 2, y0 - 22]], "#d8483a", None)
    poly(d, [[246, 545], [280, 545], [276, 528], [250, 528]], "#22303a")
    poly(d, [[250, 528], [276, 528], [263, 508]], "#d8483a")
    win.append([259, 640, 7, 10])
    poly(d, [[300, 752], [326, 752], [322, 758], [304, 758]], "#e2674f")
    # the smoking peak, jungle up its flanks, a waterfall into a pool
    ridge = []
    for k in range(41):
        f = k / 40
        x = 560 + f * 600
        top = 110 + (abs(f - 0.5) / 0.5) ** 1.3 * 340
        ridge.append([x, top + math.sin(f * 19) * 12])
    poly(d, ridge + [[1160, 470], [560, 470]], "#3b7a44")
    poly(d, [[830, 118], [860, 104], [890, 112], [900, 140], [820, 146]], "#7d7466")
    fx.append({"k": "smoke", "x": 862, "y": 106, "s": 2.0, "c": "#d8d2c6"})
    d.polygon([(930, 300), (940, 300), (946, 420), (934, 420)], fill="#e8f6fa")
    d.ellipse([910, 420, 970, 446], fill=(110, 210, 210))
    fx += [{"k": "falls", "x": 930, "y": 300, "w": 10, "h": 120}, {"k": "splash", "x": 940, "y": 430}]
    # dense jungle everywhere between the places, big leaves, banana plants
    clear = [(p["x"], p["y"], 80) for p in PLACES.values()] + [(1090, 600, 120), (280, 650, 170), (620, 640, 50)]
    for k in range(520):
        x, y = 260 + R.random() * 1160, 300 + R.random() * 470
        inside = (x - 820) ** 2 / 620 ** 2 + (y - 540) ** 2 / 240 ** 2 < 0.85
        if inside and all((x - cx) ** 2 + ((y - cy) * 1.6) ** 2 > cr ** 2 for cx, cy, cr in clear):
            tree(d, x, y, 9 + R.random() * 14, R.choice(["#2f6a38", "#356f3e", "#2b6034", "#3f8048"]), R.choice(["#4f9a48", "#5fae46", "#6fbf4a"]))
    for k in range(18):   # the banana plantation in rows on the east slope
        bx, by = 1180 + (k % 6) * 26, 470 + (k // 6) * 24
        d.line([(bx, by), (bx, by - 16)], fill="#6b7a3a", width=2)
        for a in (-0.9, -0.3, 0.3, 0.9):
            d.line([(bx, by - 16), (bx + math.sin(a) * 14, by - 16 + abs(a) * 8)], fill="#8fc04e", width=4)
    # the embassies, each on its own hill with a garden wall: the only buildings that look like they come from elsewhere
    d.ellipse([340, 400, 500, 450], fill="#6fae50")
    house(d, 420, 420, 104, 46, "#cfe1ec", "#284b63", win, roof_h=24, shutters="#284b63", porch=True)
    d.line([(468, 420), (468, 352)], fill="#22303a", width=2)
    d.ellipse([540, 450, 660, 494], fill="#7cb658")
    house(d, 600, 470, 80, 38, "#f0b48a", "#c0533f", win, roof_h=18, shutters="#8a3b2a")
    # Radio Coco: a bamboo shack with a rusty tin roof in a jungle clearing, a mast made of a tall pole and wire
    d.ellipse([700, 545, 830, 600], fill="#7cb658")
    hut(d, 760, 578, 60, 34, "#c99a5a", win, tin=True)
    d.line([(785, 560), (778, 426)], fill="#5a4030", width=4)
    d.line([(752, 572), (778, 426), (808, 572)], fill="#22303a", width=1)
    # the rebels' camp: tents, a fire, crates, deep in the jungle
    for tx, tc in [(600, 650, ), (640, 640)] if False else [(600, "#5f6b3a"), (640, "#6b7444")]:
        tent(d, tx, 650, 30, tc)
    fx += [{"k": "fire", "x": 622, "y": 660, "s": 0.8}, {"k": "smoke", "x": 622, "y": 650, "s": 0.6, "c": "#d9d2c4"}]
    # the council hall: colonial, but weathered, with palm-frond awnings and a bell tower; the town round it is
    # wooden shacks, tin roofs and bright paint, laundry lines between them
    d.ellipse([930, 500, 1090, 545], fill="#d9c79a")
    house(d, 1010, 520, 112, 50, "#f3ead2", "#7c4b2a", win, roof_h=22, shutters="#2c8c88", porch=True)
    poly(d, [[996, 448], [1024, 448], [1024, 420], [996, 420]], "#f3ead2")
    poly(d, [[992, 420], [1028, 420], [1010, 400]], "#7c4b2a")
    fx.append({"k": "flag", "x": 1010, "y": 400, "c0": "#2c8c88", "c1": "#fbf3df", "h": 16})
    for k, (x, y) in enumerate([(930, 600), (960, 630), (1180, 600), (1220, 625), (1140, 560), (1080, 575), (900, 650), (1250, 660)]):
        hut(d, x, y, 34, 24, ["#e2674f", "#f2b134", "#3aa6a0", "#e86fa0", "#6fa8ff", "#a3e05a", "#ffe066", "#ff9f40"][k], win, tin=k % 2 == 0)
    d.line([(930, 586), (960, 614)], fill="#fbf3df", width=1)
    # the market: stalls under a huge flamboyant tree on the harbour front
    d.ellipse([1000, 615, 1180, 668], fill="#e8d3a6", outline="#b89a6a", width=2)
    for k, sx in enumerate([1030, 1060, 1120, 1150]):
        sy = 652 if k in (1, 2) else 638
        d.rectangle([sx - 12, sy - 10, sx + 12, sy], fill="#b98a52", outline="#22303a")
        for j in range(3):
            d.rectangle([sx - 14 + j * 9, sy - 18, sx - 5 + j * 9, sy - 10], fill=("#e2674f" if (j + k) % 2 else "#f2b134"))
    d.line([(1090, 644), (1090, 610)], fill="#6b4422", width=5)
    d.ellipse([1052, 580, 1128, 616], fill="#e2432f", outline="#7a2a1e", width=2)
    # the harbour water, the fishing village of huts on stilts, the pier, boats
    d.ellipse([1060, 700, 1320, 840], fill=(95, 205, 200))
    for x in (1090, 1130, 1250, 1290):
        hut(d, x, 728, 30, 20, "#c99a5a", win, stilts=22)
    poly(d, [[1176, 700], [1200, 700], [1218, 800], [1190, 802]], "#a8794a")
    d.line([(1214, 796), (1214, 772)], fill="#22303a", width=2)
    win.append([1210, 766, 7, 6])
    for sx, sy in [(1110, 800), (1270, 790), (1160, 830)]:
        poly(d, [[sx - 16, sy - 3], [sx + 16, sy - 3], [sx + 11, sy + 5], [sx - 12, sy + 5]], R.choice(["#e2674f", "#3aa6a0", "#f2b134"]))
    poly(d, [[1290, 818], [1360, 818], [1350, 834], [1298, 834]], "#6b4422")
    d.line([(1325, 818), (1325, 760)], fill="#22303a", width=3)
    d.polygon([(1327, 762), (1356, 812), (1327, 812)], fill="#fbf3df", outline="#22303a")
    # Bar La Ola: a bamboo beach bar with a palm-thatch roof far out on the sandy point, torches, a string of bulbs
    hut(d, 1345, 690, 96, 30, "#c98c55", win, roof="#d9bf6a")
    for k in range(8):
        f = k / 7
        fx.append({"k": "bulb", "x": round(1300 + f * 90), "y": round(648 + math.sin(f * math.pi * 2) ** 2 * 6), "c": k % 3})
    for tx in (1290, 1402):
        d.line([(tx, 692), (tx, 670)], fill="#6b4422", width=3)
        fx.append({"k": "torch", "x": tx, "y": 668})
    # a wreck on the reef, canoes on the front beach, hammocks between palms
    poly(d, [[560, 820], [620, 806], [650, 830], [600, 842]], "#5a4030")
    d.line([(600, 820), (612, 772)], fill="#3a2a1a", width=3)
    for cx in (880, 930, 990):
        poly(d, [[cx - 16, 766], [cx + 16, 766], [cx + 10, 772], [cx - 10, 772]], R.choice(["#e2674f", "#3aa6a0", "#f2b134"]))
    palms = [(860, 740), (1030, 740), (1400, 650), (1430, 600), (1260, 600), (480, 470), (690, 520), (1040, 470), (380, 650),
             (450, 700), (520, 740), (1440, 700), (900, 560)]
    for i, (x, y) in enumerate(palms):
        palm(d, x, y, 44 + (i * 7) % 18, ((i * 13) % 9 - 4) * 2)
    d.line([(450, 690), (520, 730)], fill="#e2674f", width=3)   # a hammock
    im = im.filter(ImageFilter.SMOOTH)
    im.save(os.path.join(HERE, "plates", "bay.jpg"), quality=90)
    layout = {"places": PLACES, "walk": WALK, "windows": win, "fx": fx,
              "beam": [263, 536], "blink": [778, 426], "gather": [1090, 648], "rabbit": [960, 660], "cat": [880, 770, 1120, 762]}
    with open(os.path.join(HERE, "plates", "bay.json"), "w") as f:
        json.dump(layout, f, separators=(",", ":"))
    print("plates/bay.jpg and plates/bay.json")


if __name__ == "__main__":
    main()

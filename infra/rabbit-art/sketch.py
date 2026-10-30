#!/usr/bin/env python3
"""A new island for White Rabbit Key, drawn as a rough sketch for the painter: a Caribbean harbour town round a turquoise
bay under two green peaks. It writes the sketch (plates/bay.jpg) and, from the same numbers, where everything stands
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

# where the places stand: ground point and the box a click finds them in (world = 1600 x 900, as in scene.js)
PLACES = {
    "hall":   {"x": 880, "y": 482, "box": [792, 318, 176, 176], "name": "Council Hall"},
    "market": {"x": 700, "y": 650, "box": [590, 600, 220, 84], "name": "Market square"},
    "radio":  {"x": 1186, "y": 440, "box": [1122, 262, 128, 190], "name": "Radio Coco"},
    "north":  {"x": 470, "y": 482, "box": [394, 386, 152, 108], "name": "North Wind Embassy"},
    "south":  {"x": 640, "y": 430, "box": [584, 356, 112, 86], "name": "South Current Embassy"},
    "bar":    {"x": 1316, "y": 700, "box": [1232, 636, 170, 96], "name": "Bar La Ola"},
    "book":   {"x": 214, "y": 690, "box": [166, 440, 96, 262], "name": "The Lighthouse"},
    "pier":   {"x": 980, "y": 752, "box": [924, 690, 120, 130], "name": "The pier"},
}
WALK = [[[300, 690], [450, 668], [600, 660]], [[800, 664], [1000, 676], [1160, 694], [1240, 700]], [[880, 492], [860, 560], [800, 640]],
        [[1186, 450], [1100, 560], [1000, 660]], [[470, 490], [560, 580], [640, 650]], [[960, 676], [976, 724]],
        [[640, 438], [700, 540], [720, 630]]]
BAY = (900, 790, 330, 118)   # the harbour: centre and radii of the water the town wraps round


def coast():
    """The island's outline: wide, a rocky arm on the left for the lighthouse, a beach arm on the right."""
    pts = []
    for i in range(120):
        a = i / 120 * math.pi * 2
        r = 1 + 0.035 * math.sin(a * 3 + 0.7) + 0.022 * math.sin(a * 8 + 2) + 0.012 * math.sin(a * 17) + (R.random() - 0.5) * 0.02
        r += max(0, -math.cos(a)) ** 6 * max(0, math.sin(a) + 0.3) * 0.18           # the lighthouse arm
        r += max(0, math.cos(a)) ** 6 * max(0, math.sin(a) + 0.2) * 0.1              # the beach arm
        pts.append([round(800 + math.cos(a) * 660 * r), round(560 + math.sin(a) * 236 * r)])
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


def main():
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im, "RGBA")
    for y in range(H):   # sky and sea
        if y < HZ:
            f = y / HZ
            c = (round(40 + 120 * f), round(130 + 84 * f), round(220 + 25 * f))
        else:
            f = (y - HZ) / (H - HZ)
            c = (round(24 - 10 * f), round(150 - 60 * f), round(190 - 50 * f))
        d.line([(0, y), (W, y)], fill=c)
    for cx, cy, s in [(260, 120, 1.0), (560, 80, 0.7), (1240, 110, 1.1), (1450, 170, 0.6)]:
        for dx, dy, r in [(0, 0, 30), (30, -12, 26), (58, -2, 28), (-24, 8, 20), (82, 8, 18)]:
            d.ellipse([cx + (dx - r) * s, cy + (dy - r) * s, cx + (dx + r) * s, cy + (dy + r) * s], fill=(252, 246, 232))
    win, fx = [], []
    shore = coast()
    bx, by, brx, bry = BAY
    # the reef and the shallows, then the beach and the land, terraced up the hills
    poly(d, [[800 + (x - 800) * 1.07, 560 + (y - 560) * 1.15] for x, y in shore], (120, 214, 205, 255), None)
    poly(d, [[800 + (x - 800) * 1.025, 560 + (y - 560) * 1.06] for x, y in shore], (168, 232, 220, 255), None)
    poly(d, shore, "#efd49c")
    poly(d, [[800 + (x - 800) * 0.95, 548 + (y - 560) * 0.84] for x, y in shore], "#6fae50", None)
    for k, c in enumerate(["#64a44a", "#5a9a46", "#518f42"]):   # terraces up the slope
        poly(d, [[300 + k * 60, 520 - k * 40], [1300 - k * 60, 520 - k * 40], [1240 - k * 60, 470 - k * 40], [360 + k * 60, 470 - k * 40]], c, None)
    # the two green peaks behind the town, rainforest on their slopes, a waterfall between them
    poly(d, [[430, 430], [600, 200], [640, 150], [690, 205], [880, 410]], "#3f7d45")
    poly(d, [[800, 420], [980, 230], [1030, 170], [1080, 230], [1290, 430]], "#356f3e")
    for k in range(80):
        x = 460 + R.random() * 800
        y = 300 + R.random() * 150
        if (y > 210 + abs(x - 640) * 1.0) or (y > 220 + abs(x - 1030) * 0.95):
            tree(d, x, y, 10 + R.random() * 10, "#2f6a38", "#478e44")
    d.polygon([(732, 300), (744, 300), (752, 392), (738, 392)], fill="#e8f6fa")
    fx += [{"k": "falls", "x": 732, "y": 300, "w": 12, "h": 92}, {"k": "splash", "x": 742, "y": 396}]
    stream = [[744, 400], [760, 450], [752, 500], [790, 560], [820, 620], [834, 676]]
    d.line([tuple(p) for p in stream], fill="#7fd0e2", width=6, joint="curve")
    fx.append({"k": "stream", "pts": stream})
    # the harbour: turquoise water in the bay, a stone quay round its back, the beach on its far side
    sea = Image.new("L", (W, H), 0)   # the bay opens to the sea at the front: water only inside the land and below it
    ImageDraw.Draw(sea).ellipse([bx - brx, by - bry, bx + brx, by + bry], fill=255)
    im.paste((96, 206, 200), (0, 0), sea)
    d.arc([bx - brx - 7, by - bry - 7, bx + brx + 7, by + bry + 7], 180, 360, fill="#efd49c", width=14)
    d.arc([bx - brx - 14, by - bry - 14, bx + brx + 14, by + bry + 14], 200, 300, fill="#9a8f80", width=8)
    inner = Image.new("L", (W, H), 0)
    ImageDraw.Draw(inner).ellipse([bx - brx + 60, by - bry + 40, bx + brx - 60, by + bry + 60], fill=255)
    im.paste((52, 170, 190), (0, 0), inner)
    # streets of sand
    for p in WALK + [[[300, 690], [214, 700]], [[1240, 700], [1350, 600], [1360, 520]]]:
        d.line([tuple(q) for q in p], fill="#d9b67e", width=12, joint="curve")
    # the lighthouse on the rocky arm, with the keeper's cottage
    poly(d, [[140, 712], [176, 678], [250, 680], [282, 710], [240, 728], [160, 726]], "#8b7a66")
    house(d, 252, 712, 44, 22, "#fbf3df", "#6a6a72", win)
    poly(d, [[192, 690], [236, 690], [228, 466], [200, 466]], "#fbf3df")
    for k in range(4):
        y0 = 680 - k * 56
        poly(d, [[192 + k * 2, y0], [236 - k * 2, y0], [235 - k * 2, y0 - 24], [193 + k * 2, y0 - 24]], "#d8483a", None)
    poly(d, [[194, 466], [234, 466], [230, 446], [198, 446]], "#22303a")
    poly(d, [[198, 446], [230, 446], [214, 426]], "#d8483a")
    win.append([208, 606, 8, 12])
    # the embassies: a cool Georgian house with a veranda, a warm terracotta villa with arches
    house(d, 470, 482, 140, 60, "#cfe1ec", "#284b63", win, roof_h=30, shutters="#284b63", porch=True)
    d.line([(542, 482), (542, 394)], fill="#22303a", width=2)
    house(d, 640, 430, 104, 48, "#f0b48a", "#c0533f", win, roof_h=22, shutters="#8a3b2a")
    for k in range(3):
        ax = 612 + k * 28
        d.pieslice([ax - 8, 396, ax + 8, 412], 180, 360, fill="#24323c")
        d.rectangle([ax - 8, 404, ax + 8, 420], fill="#24323c")
    # the council hall up on its terrace: white colonial front, green shutters, a clock tower, steps down to town
    d.rectangle([786, 482, 974, 498], fill="#d9cdb0", outline="#22303a")
    for k in range(5):
        d.line([(852 + k * 2, 500 + k * 7), (908 - k * 2, 500 + k * 7)], fill="#e6d8b8", width=5)
    house(d, 880, 482, 168, 76, "#fbf3df", "#2c8c88", win, roof_h=30, porch=True)
    poly(d, [[862, 376], [898, 376], [898, 338], [862, 338]], "#fbf3df")
    d.ellipse([870, 344, 890, 364], fill="#fbf3df", outline="#22303a", width=2)
    poly(d, [[858, 338], [902, 338], [880, 312]], "#2c8c88")
    fx.append({"k": "flag", "x": 880, "y": 312, "c0": "#2c8c88", "c1": "#fbf3df", "h": 20})
    # little pastel houses stacked up the hill
    for x, y, wall, roof in [(560, 560, "#f2b134", "#c0533f"), (380, 590, "#6fa8ff", "#c0533f"), (440, 620, "#f6dcc0", "#2c8c88"),
                             (990, 520, "#a3e05a", "#6a6a72"), (1050, 560, "#ffe066", "#2c8c88"), (1090, 610, "#c9a0ff", "#c0533f"),
                             (720, 520, "#e86fa0", "#6a6a72"), (1270, 560, "#e85d4a", "#6a6a72"), (330, 640, "#7fd0c2", "#c0533f")]:
        house(d, x, y, 40, 24, wall, roof, win, roof_h=14)
    # the waterfront: a row of tall gabled houses in bright colours along the quay
    for k, wall in enumerate(["#e2674f", "#f2b134", "#3aa6a0", "#e86fa0", "#6fa8ff", "#a3e05a", "#ffe066", "#ff9f40"]):
        a = math.radians(206 + k * 11.5)
        fx_, fy_ = bx + math.cos(a) * (brx + 40), by + math.sin(a) * (bry + 40)
        if 590 < fx_ < 820:
            continue   # the market takes this part of the quay
        facade(d, fx_, fy_, 40, 54, wall, win)
    # the market square on the quay: a big flame tree in the middle, stalls with striped awnings round it
    d.ellipse([590, 616, 810, 684], fill="#e8d3a6", outline="#b89a6a", width=2)
    for k, (sx, sy) in enumerate([(622, 646), (652, 672), (748, 672), (778, 646)]):
        d.rectangle([sx - 16, sy - 14, sx + 16, sy], fill="#b98a52", outline="#22303a")
        for j in range(4):
            d.rectangle([sx - 18 + j * 9, sy - 24, sx - 9 + j * 9, sy - 14], fill=("#e2674f" if (j + k) % 2 else "#fbf3df"))
    d.line([(700, 650), (700, 604)], fill="#6b4422", width=6)
    d.ellipse([652, 572, 748, 616], fill="#e2432f", outline="#7a2a1e", width=2)
    d.ellipse([670, 566, 722, 594], fill="#f26a3a")
    # Radio Coco: a yellow shack on a green knoll, its mast with a red light on top
    d.ellipse([1110, 420, 1260, 470], fill="#5f9e48")
    house(d, 1186, 444, 78, 40, "#e9b44c", "#7c4b2a", win, roof_h=18, shutters="#c0533f")
    d.line([(1214, 404), (1200, 264)], fill="#22303a", width=3)
    d.line([(1186, 404), (1200, 264), (1234, 404)], fill="#22303a", width=1)
    # the rum distillery on the east slope: stone, a tall chimney, barrels
    house(d, 1370, 540, 90, 40, "#b5694a", "#6a6a72", win, roof_h=16, shutters="#4c3a2a")
    d.rectangle([1396, 442, 1408, 512], fill="#9a5038", outline="#22303a")
    fx.append({"k": "smoke", "x": 1402, "y": 440, "s": 1.2, "c": "#c8c2b8"})
    for k in range(4):
        cx = 1310 + k * 12
        d.ellipse([cx - 5, 536, cx + 5, 550], fill="#8a5a32", outline="#22303a")
    # Bar La Ola on the beach arm: thatched roof, string of bulbs, two torches
    house(d, 1316, 700, 110, 36, "#c98c55", "#d9bf6a", win, roof_h=26, shutters="#2c8c88", porch=True)
    for k in range(9):
        f = k / 8
        fx.append({"k": "bulb", "x": round(1258 + f * 116), "y": round(652 + math.sin(f * math.pi * 2) ** 2 * 8), "c": k % 3})
    for tx in (1238, 1394):
        d.line([(tx, 700), (tx, 674)], fill="#6b4422", width=3)
        fx.append({"k": "torch", "x": tx, "y": 672})
    # the pier out into the harbour, a lamp at its end, boats at anchor
    poly(d, [[962, 690], [990, 690], [1014, 812], [978, 814]], "#a8794a")
    for k in range(13):
        y0 = 694 + k * 9
        d.line([(962 + k * 1.3, y0), (990 + k * 1.9, y0)], fill="#7a5530", width=1)
    d.line([(1010, 806), (1010, 778)], fill="#22303a", width=2)
    win.append([1006, 772, 7, 6])
    for sx, sy, sail in [(1110, 800, "#fbf3df"), (840, 820, "#e9b44c"), (1180, 760, None), (760, 770, None), (1240, 850, "#fbf3df")]:
        poly(d, [[sx - 30, sy - 4], [sx + 30, sy - 4], [sx + 22, sy + 7], [sx - 24, sy + 7]], "#2c8c88" if sail else "#e2674f")
        if sail:
            d.line([(sx, sy - 4), (sx, sy - 50)], fill="#22303a", width=2)
            d.polygon([(sx + 2, sy - 48), (sx + 26, sy - 8), (sx + 2, sy - 8)], fill=sail, outline="#22303a")
    # fishing boats pulled up on the beach by the lighthouse, huts on stilts in the shallows
    for fx0 in (330, 380):
        poly(d, [[fx0 - 18, 748], [fx0 + 18, 748], [fx0 + 12, 756], [fx0 - 12, 756]], R.choice(["#e2674f", "#3aa6a0", "#f2b134"]))
    for hx in (470, 515):
        d.line([(hx - 10, 800), (hx - 10, 770), (hx + 10, 770), (hx + 10, 800)], fill="#6b4422", width=2)
        house(d, hx, 772, 30, 18, "#c98c55", "#d9bf6a", win, roof_h=12)
    # palms along the beaches and round the town
    palms = [(290, 700), (340, 730), (560, 710), (820, 690), (1150, 700), (1200, 720), (1440, 650), (1420, 580), (1460, 520),
             (300, 560), (330, 500), (1290, 470), (1060, 480), (560, 470), (1000, 610), (420, 700)]
    for i, (x, y) in enumerate(palms):
        palm(d, x, y, 60 + (i * 7) % 22, ((i * 13) % 9 - 4) * 2.4)
    im = im.filter(ImageFilter.SMOOTH)
    im.save(os.path.join(HERE, "plates", "bay.jpg"), quality=90)
    layout = {"places": PLACES, "walk": WALK, "windows": win, "fx": fx,
              "beam": [214, 446], "blink": [1200, 264], "gather": [700, 656], "rabbit": [860, 676], "cat": [300, 694, 1240, 704]}
    with open(os.path.join(HERE, "plates", "bay.json"), "w") as f:
        json.dump(layout, f, separators=(",", ":"))
    print("plates/bay.jpg and plates/bay.json")


if __name__ == "__main__":
    main()

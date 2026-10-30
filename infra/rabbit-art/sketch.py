#!/usr/bin/env python3
"""A new island for White Rabbit Key, drawn as a rough sketch for the painter: one great green peak rising out of the
sea, cliffs and rocks along the front, a harbour town glowing in a bay on the right, a little village of the embassies
on a plateau on the left, the lighthouse on a cliff point, swirling clouds. It writes the sketch (plates/bay.jpg) and, from the same numbers, where everything stands
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
    "hall":   {"x": 1090, "y": 520, "box": [1020, 410, 140, 120], "name": "Council Hall"},
    "market": {"x": 1080, "y": 640, "box": [990, 600, 180, 70], "name": "Market square"},
    "radio":  {"x": 1300, "y": 430, "box": [1250, 270, 110, 170], "name": "Radio Coco"},
    "north":  {"x": 380, "y": 470, "box": [320, 390, 120, 90], "name": "North Wind Embassy"},
    "south":  {"x": 520, "y": 420, "box": [470, 355, 100, 75], "name": "South Current Embassy"},
    "bar":    {"x": 1320, "y": 690, "box": [1255, 640, 130, 70], "name": "Bar La Ola"},
    "book":   {"x": 270, "y": 640, "box": [235, 450, 75, 200], "name": "The Lighthouse"},
    "pier":   {"x": 1190, "y": 745, "box": [1140, 700, 110, 100], "name": "The pier"},
}
WALK = [[[270, 650], [330, 560], [380, 480]], [[380, 480], [520, 430]], [[520, 430], [640, 520], [800, 610], [990, 640]],
        [[1090, 530], [1080, 610]], [[1170, 650], [1250, 690], [1320, 700]], [[1300, 440], [1220, 540], [1160, 620]],
        [[1100, 660], [1180, 712]]]
BAY = (1240, 820, 230, 120)   # the harbour: centre and radii of the water in front of the town


def coast():
    """The island's outline: wide, a cliff point on the left for the lighthouse, the harbour cut in on the right."""
    pts = []
    for i in range(140):
        a = i / 140 * math.pi * 2
        r = 1 + 0.06 * math.sin(a * 3 + 0.4) + 0.035 * math.sin(a * 7 + 2) + 0.02 * math.sin(a * 13) + (R.random() - 0.5) * 0.03
        r += max(0, -math.cos(a)) ** 6 * max(0, math.sin(a) + 0.2) * 0.12
        pts.append([round(800 + math.cos(a) * 700 * r), round(560 + math.sin(a) * 250 * r)])
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


def main():
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im, "RGBA")
    for y in range(H):   # sky and sea
        if y < HZ:
            f = y / HZ
            c = (round(60 + 110 * f), round(150 + 70 * f), round(215 + 25 * f))
        else:
            f = (y - HZ) / (H - HZ)
            c = (round(30 - 14 * f), round(160 - 70 * f), round(195 - 60 * f))
        d.line([(0, y), (W, y)], fill=c)
    for x, y, r, col in [(260, 90, 70, (235, 245, 250)), (520, 60, 46, (225, 240, 248)), (1180, 80, 80, (240, 248, 252)),
                         (1460, 150, 54, (225, 240, 248)), (880, 40, 40, (230, 244, 250))]:
        for k in range(3):
            swirl(d, x + k * 30, y + k * 8, r - k * 12, 1.4, col, 16 - k * 4)
    d.ellipse([1330, 40, 1420, 130], fill=(255, 248, 225))   # the sun
    win, fx = [], []
    shore = coast()
    # reef and shallows, a ring of rocks, then the land
    poly(d, [[800 + (x - 800) * 1.06, 560 + (y - 560) * 1.14] for x, y in shore], (110, 210, 205, 255), None)
    poly(d, [[800 + (x - 800) * 1.02, 560 + (y - 560) * 1.05] for x, y in shore], (160, 228, 218, 255), None)
    poly(d, shore, "#4e8a46")
    for k in range(60):   # rocks in the surf
        a = R.random() * math.pi + 0.05
        x, y = 800 + math.cos(a) * 720 * (1.02 + R.random() * 0.05), 560 + math.sin(a) * 262 * (1.02 + R.random() * 0.08)
        s = 6 + R.random() * 12
        poly(d, [[x - s, y + s * 0.4], [x - s * 0.3, y - s * 0.8], [x + s * 0.7, y - s * 0.5], [x + s, y + s * 0.4]], "#5d7a86")
    # the cliffs along the front: steep rock faces under the grass
    front = [p for p in shore if p[1] > 600 and p[0] < 1060]
    for i in range(len(front) - 1):
        (x0, y0), (x1, y1) = front[i], front[i + 1]
        poly(d, [[x0, y0 - 46], [x1, y1 - 46], [x1, y1], [x0, y0]], "#7a8f98" if i % 2 else "#6a808a", None)
        d.line([(x0, y0 - 44), (x0 + (R.random() - 0.5) * 8, y0)], fill="#4a5e68", width=2)
    poly(d, [[800 + (x - 800) * 0.96, 540 + (y - 560) * 0.86] for x, y in shore], "#5f9e4a", None)
    # the great peak: rainforest to the top, a bald rock crown, a waterfall down its front into the cliffs
    ridge = []   # a lumpy, leaning silhouette rather than a cone
    for k in range(41):
        f = k / 40
        x = 360 + f * 760
        top = 70 + (abs(f - 0.55) / 0.55) ** 1.4 * 530
        ridge.append([x, top + math.sin(f * 23) * 14 + math.sin(f * 9 + 1) * 18 * (1 - abs(f - 0.55))])
    poly(d, ridge + [[1120, 600], [360, 600]], "#3b7a44")
    for k in range(6):   # big rounded shoulders of forest on the flanks
        cx, cy, r = [(520, 470, 90), (640, 330, 80), (950, 330, 70), (1040, 470, 90), (780, 520, 110), (860, 230, 60)][k]
        d.ellipse([cx - r, cy - r * 0.8, cx + r, cy + r * 0.8], fill=["#357540", "#3f8048", "#326e3c", "#3a7a44", "#2f6a38", "#3d7c46"][k])
    poly(d, [[700, 150], [740, 90], [800, 70], [850, 110], [820, 160], [760, 170]], "#8a8f7a")
    for k in range(140):
        x = 420 + R.random() * 680
        y = 160 + R.random() * 460
        edge = 600 - (y - 70) * 0.0
        if abs(x - 790) < (y - 70) * 0.62 and y < 600:
            tree(d, x, y, 9 + R.random() * 12, R.choice(["#2f6a38", "#356f3e", "#2b6034"]), "#4f9a48")
    d.polygon([(742, 420), (754, 420), (772, 700), (756, 700)], fill="#e8f6fa")
    fx += [{"k": "falls", "x": 742, "y": 420, "w": 12, "h": 280}, {"k": "splash", "x": 762, "y": 760}]
    # the plateau on the left with the embassies' little village, the lighthouse on the cliff point
    d.ellipse([290, 400, 600, 520], fill="#6fae50")
    poly(d, [[220, 660], [250, 630], [300, 632], [330, 664], [300, 690], [236, 690]], "#7a8f98")
    poly(d, [[252, 640], [292, 640], [284, 470], [260, 470]], "#fbf3df")
    for k in range(3):
        y0 = 630 - k * 56
        poly(d, [[252 + k * 2, y0], [292 - k * 2, y0], [291 - k * 2, y0 - 24], [253 + k * 2, y0 - 24]], "#d8483a", None)
    poly(d, [[254, 470], [290, 470], [286, 452], [258, 452]], "#22303a")
    poly(d, [[258, 452], [286, 452], [272, 432]], "#d8483a")
    win.append([268, 560, 7, 10])
    # streets: sand paths winding from the plateau round the foot of the peak down to the town
    for p in WALK:
        d.line([tuple(q) for q in p], fill="#d9b67e", width=9, joint="curve")
    house(d, 380, 470, 110, 50, "#cfe1ec", "#284b63", win, roof_h=26, shutters="#284b63", porch=True)
    d.line([(436, 470), (436, 396)], fill="#22303a", width=2)
    house(d, 520, 420, 84, 40, "#f0b48a", "#c0533f", win, roof_h=20, shutters="#8a3b2a")
    for x, y, wall, roof in [(310, 520, "#f2b134", "#c0533f"), (460, 510, "#7fd0c2", "#6a6a72"), (580, 480, "#e86fa0", "#c0533f")]:
        house(d, x, y, 30, 20, wall, roof, win, roof_h=12)
    # the harbour on the right: the bay, the town climbing the slope above it, the hall on top, the radio on the hill
    sea = Image.new("L", (W, H), 0)
    bx, by, brx, bry = BAY
    ImageDraw.Draw(sea).ellipse([bx - brx, by - bry, bx + brx, by + bry], fill=255)
    im.paste((90, 200, 200), (0, 0), sea)
    d.arc([bx - brx - 8, by - bry - 8, bx + brx + 8, by + bry + 8], 190, 350, fill="#efd49c", width=14)
    d.arc([bx - brx - 14, by - bry - 14, bx + brx + 14, by + bry + 14], 200, 290, fill="#9a8f80", width=8)
    for k, (x, y) in enumerate([(1000, 560), (1040, 590), (1150, 570), (1190, 600), (1230, 630), (960, 610), (1150, 480), (1200, 520),
                                (1010, 470), (980, 520)]):
        facade(d, x, y, 30, 40, ["#e2674f", "#f2b134", "#3aa6a0", "#e86fa0", "#6fa8ff", "#a3e05a", "#ffe066", "#ff9f40", "#c9a0ff", "#fbf3df"][k], win)
    d.rectangle([1024, 520, 1156, 530], fill="#d9cdb0", outline="#22303a")
    house(d, 1090, 520, 124, 58, "#fbf3df", "#2c8c88", win, roof_h=24, porch=True)
    poly(d, [[1076, 438], [1104, 438], [1104, 408], [1076, 408]], "#fbf3df")
    d.ellipse([1082, 412, 1098, 428], fill="#fbf3df", outline="#22303a", width=2)
    poly(d, [[1072, 408], [1108, 408], [1090, 388]], "#2c8c88")
    fx.append({"k": "flag", "x": 1090, "y": 388, "c0": "#2c8c88", "c1": "#fbf3df", "h": 18})
    d.ellipse([990, 612, 1170, 668], fill="#e8d3a6", outline="#b89a6a", width=2)
    for k, sx in enumerate([1020, 1050, 1110, 1140]):
        sy = 650 if k in (1, 2) else 636
        d.rectangle([sx - 12, sy - 10, sx + 12, sy], fill="#b98a52", outline="#22303a")
        for j in range(3):
            d.rectangle([sx - 14 + j * 9, sy - 18, sx - 5 + j * 9, sy - 10], fill=("#e2674f" if (j + k) % 2 else "#fbf3df"))
    d.line([(1080, 642), (1080, 610)], fill="#6b4422", width=5)
    d.ellipse([1046, 580, 1114, 614], fill="#e2432f", outline="#7a2a1e", width=2)
    d.ellipse([1240, 400, 1360, 450], fill="#5f9e48")
    house(d, 1300, 432, 64, 34, "#e9b44c", "#7c4b2a", win, roof_h=16, shutters="#c0533f")
    d.line([(1322, 398), (1312, 272)], fill="#22303a", width=3)
    d.line([(1296, 398), (1312, 272), (1340, 398)], fill="#22303a", width=1)
    house(d, 1420, 560, 70, 32, "#b5694a", "#6a6a72", win, roof_h=14, shutters="#4c3a2a")
    d.rectangle([1440, 480, 1450, 536], fill="#9a5038", outline="#22303a")
    fx.append({"k": "smoke", "x": 1445, "y": 478, "s": 1.0, "c": "#c8c2b8"})
    house(d, 1320, 692, 92, 30, "#c98c55", "#d9bf6a", win, roof_h=22, shutters="#2c8c88", porch=True)
    for k in range(8):
        f = k / 7
        fx.append({"k": "bulb", "x": round(1276 + f * 88), "y": round(652 + math.sin(f * math.pi * 2) ** 2 * 6), "c": k % 3})
    for tx in (1262, 1380):
        d.line([(tx, 692), (tx, 670)], fill="#6b4422", width=3)
        fx.append({"k": "torch", "x": tx, "y": 668})
    poly(d, [[1172, 700], [1196, 700], [1214, 800], [1186, 802]], "#a8794a")
    for k in range(11):
        d.line([(1172 + k * 1.4, 704 + k * 9), (1196 + k * 1.7, 704 + k * 9)], fill="#7a5530", width=1)
    d.line([(1210, 796), (1210, 772)], fill="#22303a", width=2)
    win.append([1206, 766, 7, 6])
    # a tall ship at anchor in the harbour, small boats, a wreck on the rocks below the cliffs
    poly(d, [[1300, 800], [1400, 800], [1386, 822], [1312, 822]], "#6b4422")
    for mx, mh in [(1325, 90), (1350, 110), (1375, 84)]:
        d.line([(mx, 800), (mx, 800 - mh)], fill="#22303a", width=3)
        for k in range(3):
            y0 = 800 - mh + 8 + k * 26
            poly(d, [[mx - 20 + k * 2, y0], [mx + 20 - k * 2, y0], [mx + 22 - k * 2, y0 + 20], [mx - 22 + k * 2, y0 + 20]], "#fbf3df")
    for sx, sy in [(1110, 790), (1260, 770), (1150, 840)]:
        poly(d, [[sx - 18, sy - 3], [sx + 18, sy - 3], [sx + 12, sy + 5], [sx - 14, sy + 5]], R.choice(["#e2674f", "#3aa6a0", "#f2b134"]))
    poly(d, [[560, 830], [620, 816], [650, 840], [600, 852]], "#5a4030")
    d.line([(600, 830), (612, 780)], fill="#3a2a1a", width=3)
    # palms along the shore and round the town
    palms = [(330, 600), (350, 650), (450, 560), (600, 520), (940, 640), (1180, 660), (1400, 680), (1440, 620), (1240, 470),
             (960, 450), (1380, 470), (320, 440), (620, 440)]
    for i, (x, y) in enumerate(palms):
        palm(d, x, y, 44 + (i * 7) % 18, ((i * 13) % 9 - 4) * 2)
    im = im.filter(ImageFilter.SMOOTH)
    im.save(os.path.join(HERE, "plates", "bay.jpg"), quality=90)
    layout = {"places": PLACES, "walk": WALK, "windows": win, "fx": fx,
              "beam": [272, 462], "blink": [1312, 272], "gather": [1080, 645], "rabbit": [940, 640], "cat": [960, 690, 1300, 712]}
    with open(os.path.join(HERE, "plates", "bay.json"), "w") as f:
        json.dump(layout, f, separators=(",", ":"))
    print("plates/bay.jpg and plates/bay.json")


if __name__ == "__main__":
    main()

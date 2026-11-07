"""Agorzilla grown up, for every Agorzilla on Tau HUD: one set of pictures per growth stage.

agorzilla.com reshapes the same painting with its age (its assets/rig.js "growing up"): the eyes get smaller under a lower,
heavier brow, the muzzle and nostrils bigger, the lower face broader, the crown taller, the face skin darker; the back
rises and the shoulders broaden. This bakes the same fields into pictures, so the HUD's puppets need no WebGL for it:

  assets/rig/age/<stage>/      the header puppet: agz-head, agz-body, agz-brow-l/r (266x400, as tools/agz/rig_hud.py) and agz-moves
  assets/rig/hi/age/<stage>/   the My Tau card's puppet: head, body, brow-l/r (760x1140, as agorzilla.com's tools/rig.py)
  assets/age/agorzilla-<stage>.webp   the small flat picture (/start/, menus, services)

Eyes and lids stay the baby's: the page scales them like agorzilla.com does (assets/agz-look.js). The head's lift on the
risen back and its smaller size on the bigger body are CSS too, so eyes, lids and brows follow the head.

Run: python3 tools/agz/stages.py <agorzilla.com checkout>/assets/agorilla.webp   (needs Pillow and numpy)
"""
import pathlib, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
HERE = pathlib.Path(__file__).resolve().parent
SRC = sys.argv[1]
AGE = {"kid": .18, "young": .38, "grown": .62, "elder": .82, "ancient": 1}
AHS = {"kid": .985, "young": .97, "grown": .95, "elder": .935, "ancient": .925}   # agorzilla.com style.css --ahs
EYES_PX = [(399.5, 377, 52), (588.5, 323.5, 46)]
SHRINK, DARK = .3, .55
NECK = [(0, .50), (.15, .50), (.30, .505), (.45, .495), (.60, .49), (.75, .468), (.90, .432), (1, .41)]
F = .012
EYES = {"l": dict(cx=.526, cy=.331, rx=.066, ry=.045), "r": dict(cx=.775, cy=.284, rx=.059, ry=.043)}
OW, OH = 266, 400

im = Image.open(SRC).convert("RGBA"); W, H = im.size
A0 = np.asarray(im).astype(np.float32) / 255
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def smooth(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def gauss(x, y, cx, cy, r): return np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (r * r))


def age_face(x, y, a):   # rig.js ageFace
    dx = np.zeros_like(x); dy = np.zeros_like(x)
    for cx, cy, r in EYES_PX:
        dist = np.hypot(x - cx, y - cy); k = SHRINK * a * (1 - smooth(r * 1.05, r * 2.4, dist))
        dx -= (x - cx) * k; dy -= (y - cy) * k
        dy += 15 * a * gauss(x, y, cx, cy - r * 1.45, r * 1.1) * smooth(r * 1.05, r * 1.7, dist)
    g = gauss(x, y, 515, 432, 100) * .15 * a; dx += (x - 515) * g; dy += (y - 432) * g * .8
    g = gauss(x, y, 510, 396, 34) * .25 * a; dx += (x - 510) * g
    dx += (x - 500) * .08 * a * smooth(390, 480, y) * (1 - smooth(560, 640, y))
    dy -= 30 * a * gauss(x, 0, 470, 0, 150) * smooth(300, 40, y)
    return dx, dy


def age_trunk(x, y, a):   # rig.js ageTrunk
    on = y <= 960
    dy = -a * (34 * smooth(940, 600, y) + 20 * (gauss(x, y, 250, 600, 120) + gauss(x, y, 700, 580, 110)) * smooth(940, 700, y))
    dx = (x - 480) * .14 * a * smooth(470, 620, y) * smooth(960, 780, y)
    return dx * on, dy * on


def sample(P, sx, sy):   # bilinear, P premultiplied
    x0 = np.clip(np.floor(sx).astype(int), 0, W - 2); y0 = np.clip(np.floor(sy).astype(int), 0, H - 2)
    fx = np.clip(sx - x0, 0, 1)[..., None]; fy = np.clip(sy - y0, 0, 1)[..., None]
    v = (P[y0, x0] * (1 - fx) + P[y0, x0 + 1] * fx) * (1 - fy) + (P[y0 + 1, x0] * (1 - fx) + P[y0 + 1, x0 + 1] * fx) * fy
    out = (sx >= 0) & (sy >= 0) & (sx <= W - 1) & (sy <= H - 1)
    return v * out[..., None]


def pre(A): return np.concatenate([A[..., :3] * A[..., 3:], A[..., 3:]], -1)
def unpre(P): a = P[..., 3:]; return np.concatenate([np.where(a > 1e-4, P[..., :3] / np.maximum(a, 1e-4), 0), a], -1)


def warp(A, field, a):
    """The page moves each picture point p by d(p); here every output pixel finds the point that landed on it."""
    sx, sy = xx.copy(), yy.copy()
    for _ in range(4):
        dx, dy = field(sx, sy, a); sx, sy = xx - dx, yy - dy
    return unpre(sample(pre(A), sx, sy))


def skin_mask(A):   # rig.js skinMask: light skin inside the face and the ears
    def e(px, py, rx, ry, rot):
        c, s = np.cos(rot), np.sin(rot); u = ((xx - px) * c + (yy - py) * s) / rx; v = (-(xx - px) * s + (yy - py) * c) / ry
        return 1 - smooth(.8, 1.05, np.hypot(u, v))
    inside = np.maximum.reduce([e(497, 372, 205, 140, -.22), e(520, 455, 120, 70, -.2), e(212, 492, 62, 70, 0), e(700, 390, 30, 60, 0)])
    L = A[..., :3] @ np.array([.3, .59, .11], np.float32)
    m = inside * smooth(.2, .34, L) * A[..., 3] * (yy < 640)
    return np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255


def older_skin(A, a):   # rig.js shader: darker, greyer skin
    s = skin_mask(A)[..., None] * DARK * a
    rgb = A[..., :3]; lum = rgb @ np.array([.3, .59, .11], np.float32)
    rgb = (rgb * (1 - s * .5) + lum[..., None] * s * .5) * (1 - s)
    return np.concatenate([rgb, A[..., 3:]], -1)


neck = np.interp(xx[0] / W, [p[0] for p in NECK], [p[1] for p in NECK])[None, :]
hmask = (1 - smooth(neck - F, neck + F, yy / H))[..., None]
fillw = (1 - smooth(neck - F - .03, neck - F, yy / H))[..., None]


def body_of(A):   # rig.py body_and_head: above the neck the head's own dark fur, a shade deeper
    alpha = np.asarray(Image.fromarray((A[..., 3] * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(41)).filter(ImageFilter.GaussianBlur(8))).astype(np.float32)[..., None] / 255
    lum = A[..., :3] @ np.array([.3, .59, .11], np.float32)
    fur = np.median(A[..., :3][(A[..., 3] > .9) & (lum < .22) & (yy < H / 2)], 0) * .85
    return np.concatenate([A[..., :3] * (1 - fillw) + fur * fillw, A[..., 3:] * (1 - fillw) + alpha * fillw], -1)


def head_of(A): return np.concatenate([A[..., :3], A[..., 3:] * hmask], -1)


def brow_of(A, e):
    bx0, bx1 = int((e["cx"] - e["rx"] * 1.9) * W), int((e["cx"] + e["rx"] * 1.9) * W)
    by0, by1 = int((e["cy"] - e["ry"] * 3.1) * H), int((e["cy"] - e["ry"] * .2) * H)
    by, bx = np.mgrid[by0:by1, bx0:bx1].astype(np.float32)
    ddx, ddy = (bx / W - e["cx"]) / e["rx"], (by / H - e["cy"]) / e["ry"]
    rr = np.sqrt(ddx ** 2 + ddy ** 2)
    am = smooth(1.08, 1.4, rr) * (1 - smooth(2.2, 2.9, rr)) * smooth(.1, -.6, ddy)
    return np.concatenate([A[by0:by1, bx0:bx1, :3], A[by0:by1, bx0:bx1, 3:] * am[..., None]], -1), (bx1 - bx0, by1 - by0)


def img(A): return Image.fromarray((np.clip(A, 0, 1) * 255).astype(np.uint8), "RGBA")


def placed_head(Hd, a, st):
    """The head as the page shows it: lifted with the risen back (rig.js --nx/--ny at the neck), a little smaller (--ahs)."""
    dx, dy = age_trunk(np.float32(520), np.float32(560), a)
    s = AHS[st]; ox, oy = .56 * W, .48 * H
    sx = (xx - dx - ox) / s + ox; sy = (yy - dy - oy) / s + oy
    return unpre(sample(pre(Hd), sx, sy))


def over(top, bot):
    t, b = pre(top), pre(bot)
    return unpre(t + b * (1 - t[..., 3:]))


for st, a in AGE.items():
    faceA = warp(older_skin(A0, a), age_face, a)
    head = head_of(faceA)
    body = body_of(warp(A0, age_trunk, a))
    lo = ROOT / "assets" / "rig" / "age" / st; hi = ROOT / "assets" / "rig" / "hi" / "age" / st
    lo.mkdir(parents=True, exist_ok=True); hi.mkdir(parents=True, exist_ok=True)
    img(head).save(hi / "head.webp", quality=90, method=6); img(body).save(hi / "body.webp", quality=88, method=6)
    img(head).resize((OW, OH), Image.LANCZOS).save(lo / "agz-head.webp", quality=88, method=6)
    img(body).resize((OW, OH), Image.LANCZOS).save(lo / "agz-body.webp", quality=88, method=6)
    for k, e in EYES.items():
        b, (bw, bh) = brow_of(faceA, e)
        img(b).save(hi / f"brow-{k}.webp", quality=90, method=6)
        img(b).resize((round(bw * OW / W), round(bh * OH / H)), Image.LANCZOS).save(lo / f"agz-brow-{k}.webp", quality=90, method=6)
    # the whole creature as the page shows it at rest: its painted eyes already got smaller with the face
    flat = over(placed_head(head, a, st), body)
    full = img(flat)
    (ROOT / "assets" / "age").mkdir(exist_ok=True)
    full.resize((133, 200), Image.LANCZOS).save(ROOT / "assets" / "age" / f"agorzilla-{st}.webp", quality=88, method=6)
    # the seven move frames (yaw.py turns, ball.py tucks), strip as assets/rig/agz-moves.webp
    with tempfile.TemporaryDirectory() as t:
        full.save(f"{t}/full.png")
        subprocess.run([sys.executable, str(HERE / "yaw.py"), f"{t}/full.png", t, "-6", "-12", "-18", "-24"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([sys.executable, str(HERE / "ball.py"), f"{t}/yaw-24.png", t, ".33", ".66", "1"], check=True, stdout=subprocess.DEVNULL)
        strip = Image.new("RGBA", (OW * 7, OH))
        for i, f in enumerate(["yaw-6", "yaw-12", "yaw-18", "yaw-24", "ball033", "ball066", "ball100"]):
            strip.paste(Image.open(f"{t}/{f}.png").resize((OW, OH), Image.LANCZOS), (OW * i, 0))
        strip.resize((1396, 300), Image.LANCZOS).save(lo / "agz-moves.webp", quality=86, method=6)
    print(st, "done")

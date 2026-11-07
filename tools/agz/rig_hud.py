"""Builds the header puppet's layers (assets/rig/) from the full-size Agorzilla picture.
body: the creature with its head area filled by soft dark fur; head: everything above the neck, ears included, feathered at the neck;
eyes: each eye's inside extended outward; lids: upper and lower lid skin taken from the skin right above / below each eye;
brows: the brow arch above each eye as its own piece. At rest the layers line up pixel for pixel with the picture."""
import sys, numpy as np
from PIL import Image, ImageFilter
SRC, OUT = sys.argv[1], sys.argv[2]
im = Image.open(SRC).convert("RGBA"); W, H = im.size
OW, OH = 266, 400                      # 2x of the 133x200 header picture
A = np.asarray(im).astype(np.float32) / 255
def smooth(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
ys, xs = np.mgrid[0:H, 0:W].astype(np.float32); X, Y = xs / W, ys / H
NECK = [(0, .50), (.15, .50), (.30, .505), (.45, .495), (.60, .49), (.75, .468), (.90, .432), (1, .41)]
neck = np.interp(X[0], [p[0] for p in NECK], [p[1] for p in NECK])[None, :]
F = .012
hmask = 1 - smooth(neck - F, neck + F, Y)                  # 1 above the neck, 0 below
fillw = 1 - smooth(neck - F - .03, neck - F, Y)            # where the body shows fur instead of the head: only well above the feather
def save(arr, name, size=(OW, OH)):
    m = "RGBA" if arr.shape[-1] == 4 else "RGB"
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), m).resize(size, Image.LANCZOS).save(f"{OUT}/{name}", quality=88, method=6)
# head
save(np.concatenate([A[..., :3], A[..., 3:] * hmask[..., None]], -1), "agz-head.webp")
# body
alpha = im.getchannel("A").filter(ImageFilter.MinFilter(41)).filter(ImageFilter.GaussianBlur(8))
pre = Image.fromarray((A[..., :3] * A[..., 3:] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(26))
acov = np.asarray(im.getchannel("A").filter(ImageFilter.GaussianBlur(26))).astype(np.float32)[..., None] / 255
lum = A[..., :3] @ np.array([.3, .59, .11], np.float32)
fur = (A[..., 3] > .9) & (lum < .22) & (Y < .5)
furc = np.median(A[..., :3][fur], 0) * .85                 # the head's own dark fur, a shade deeper: it reads as the shadow under the head
fill = np.broadcast_to(furc, A[..., :3].shape)
fa = np.asarray(alpha).astype(np.float32)[..., None] / 255
w = fillw[..., None]
save(np.concatenate([A[..., :3] * (1 - w) + fill * w, A[..., 3:] * (1 - w) + fa * w], -1), "agz-body.webp")
# eyes, lids, brows
EYES = {"l": dict(cx=.526, cy=.331, rx=.066, ry=.045), "r": dict(cx=.775, cy=.284, rx=.059, ry=.043)}
PAD = 1.6
rgb = A[..., :3]
for k, e in EYES.items():
    x0, x1 = int((e["cx"] - e["rx"] * PAD) * W), int((e["cx"] + e["rx"] * PAD) * W)
    y0, y1 = int((e["cy"] - e["ry"] * PAD) * H), int((e["cy"] + e["ry"] * PAD) * H)
    sy, sx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = (sx / W - e["cx"]) / e["rx"], (sy / H - e["cy"]) / e["ry"]
    r = np.sqrt(dx * dx + dy * dy)
    q = np.minimum(1, .86 / np.maximum(r, 1e-6))
    px = np.clip(((dx * q) * e["rx"] + e["cx"]) * W, 0, W - 1).astype(int); py = np.clip(((dy * q) * e["ry"] + e["cy"]) * H, 0, H - 1).astype(int)
    size = (round((x1 - x0) * OW / W), round((y1 - y0) * OH / H))
    Image.fromarray((rgb[py, px] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)).resize(size, Image.LANCZOS).save(f"{OUT}/agz-eye-{k}.webp", quality=90)
    # lids: one skin tone per eye, the median of the light skin ring around it, shaded like a curved lid with a darker lash edge
    ring = (r > 1.25) & (r < 1.7)
    ring_rgb = rgb[sy[ring].astype(int), sx[ring].astype(int)]
    lum = ring_rgb @ np.array([.3, .59, .11], np.float32)
    tone = np.median(ring_rgb[(lum > np.percentile(lum, 45)) & (lum < np.percentile(lum, 85))], 0)
    rng = np.random.default_rng(7)
    for part in ("up", "lo"):
        f = (sy - y0) / max(1, y1 - y0 - 1)                   # the lid image's own row: 0 at the top, 1 at the bottom
        t = f if part == "up" else 1 - f                       # 0 at the lid's root, 1 at its free edge
        shade = .9 + .14 * np.exp(-((t - .5) / .26) ** 2) - .14 * smooth(.2, 0, t) - .12 * smooth(.9, 1, t)   # lit across the middle, a crease at the root
        shade *= 1 - .22 * smooth(.55, 1.05, r)                # rounder: darker toward the rim, like a closed eyeball under skin
        if part == "lo": shade *= .96
        tex = rng.normal(0, .025, shade.shape).astype(np.float32)
        lid = np.clip(tone[None, None, :] * (shade + tex)[..., None], 0, 1)
        Image.fromarray((lid * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)).resize(size, Image.LANCZOS).save(f"{OUT}/agz-lid-{k}-{part}.webp", quality=90)
    print(k, "lid tone #%02x%02x%02x" % tuple((tone * 255).astype(int)))
    # brow: the arch of skin and fur above the eye, as its own piece in the picture's coordinates
    bx0, bx1 = int((e["cx"] - e["rx"] * 1.9) * W), int((e["cx"] + e["rx"] * 1.9) * W)
    by0, by1 = int((e["cy"] - e["ry"] * 3.1) * H), int((e["cy"] - e["ry"] * .2) * H)
    by, bx = np.mgrid[by0:by1, bx0:bx1].astype(np.float32)
    ddx, ddy = (bx / W - e["cx"]) / e["rx"], (by / H - e["cy"]) / e["ry"]
    rr = np.sqrt(ddx ** 2 + ddy ** 2)
    am = smooth(1.08, 1.4, rr) * (1 - smooth(2.2, 2.9, rr)) * smooth(.1, -.6, ddy)
    crop = np.concatenate([rgb[by0:by1, bx0:bx1], A[by0:by1, bx0:bx1, 3:] * am[..., None]], -1)
    bsize = (round((bx1 - bx0) * OW / W), round((by1 - by0) * OH / H))
    Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8), "RGBA").resize(bsize, Image.LANCZOS).save(f"{OUT}/agz-brow-{k}.webp", quality=90)
    print(k, "eye box %", [round(v, 2) for v in (x0 / W * 100, y0 / H * 100, (x1 - x0) / W * 100, (y1 - y0) / H * 100)], "brow box %", [round(v, 2) for v in (bx0 / W * 100, by0 / H * 100, (bx1 - bx0) / W * 100, (by1 - by0) / H * 100)])

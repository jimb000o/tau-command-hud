import sys, numpy as np
from PIL import Image, ImageFilter
SRC, OUT = sys.argv[1], sys.argv[2]
im = Image.open(SRC).convert("RGBA"); W, H = im.size
A = np.asarray(im).astype(np.float32) / 255
ys, xs = np.mgrid[0:H, 0:W].astype(np.float32); X, Y = xs / W, ys / H
def smooth(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
# no rock: keep everything above 85.4 %, plus the paws (same ellipses as the CSS leg mask)
keep = 1 - smooth(.854, .864, Y)
for cx, cy, rx, ry in [(.515, .874, .125, .034), (.80, .874, .14, .034), (.23, .854, .09, .019)]:
    d = np.sqrt(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2); keep = np.maximum(keep, 1 - smooth(.72, 1, d))
A = A.copy(); A[..., 3] *= keep
A[..., 3] *= smooth(.05, .15, A[..., 3])   # no faint halo: it would smear into streaks
alpha = A[..., 3]
# a cylinder per row, its axis on the figure's middle, smoothed over rows so the outline stays calm
rows = []
for y in range(H):
    xs_ = np.where(alpha[y] > .35)[0]
    rows.append((xs_[0], xs_[-1]) if len(xs_) > 8 else (np.nan, np.nan))
r = np.array(rows, float)
for k in range(2):
    v = r[:, k]; ok = ~np.isnan(v); r[:, k] = np.interp(np.arange(H), np.where(ok)[0], v[ok])
k = np.exp(-.5 * (np.arange(-75, 76) / 25) ** 2); k /= k.sum()
r = np.stack([np.convolve(np.pad(r[:, i], 75, mode='edge'), k, 'valid') for i in range(2)], 1)
c = (r[:, 0] + r[:, 1]) / 2; R = (r[:, 1] - r[:, 0]) / 2 * 1.04
def yaw(deg):
    d = np.radians(deg); out = np.zeros_like(A)
    u = np.clip((xs - c[:, None]) / R[:, None], -1, 1); phi = np.arcsin(u)
    src = phi - d
    vis = np.abs(src) <= np.pi / 2
    sx = c[:, None] + R[:, None] * np.sin(np.clip(src, -np.pi / 2, np.pi / 2))
    x0 = np.clip(np.floor(sx).astype(int), 0, W - 2); f = (sx - x0)[..., None]; yy = ys.astype(int)
    pm = A[..., :3] * A[..., 3:]
    P = np.concatenate([pm, A[..., 3:]], -1)
    s = P[yy, x0] * (1 - f) + P[yy, x0 + 1] * f
    # the side turning away gets darker (light from the front), the outside of the cylinder stays outside
    shade = .62 + .38 * np.cos(np.clip(phi, -np.pi / 2, np.pi / 2)) ** .7
    s[..., :3] *= shade[..., None]
    s *= smooth(np.pi / 2, np.pi / 2 - np.radians(10), np.abs(src))[..., None]   # the back of the cylinder is out of sight
    s *= (np.abs((xs - c[:, None]) / R[:, None]) <= 1)[..., None]   # and nothing outside it
    a = s[..., 3:]; rgb = np.where(a > 1e-4, s[..., :3] / np.maximum(a, 1e-4), 0)
    return np.concatenate([rgb, a], -1)
frames = []
for deg in map(float, sys.argv[3:]):
    f = yaw(deg); frames.append(f)
    Image.fromarray((np.clip(f, 0, 1) * 255).astype(np.uint8)).save(f"{OUT}/yaw{int(deg):+d}.png")

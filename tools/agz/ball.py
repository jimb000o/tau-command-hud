import sys, numpy as np
from PIL import Image
SRC, OUT = sys.argv[1], sys.argv[2]
F = np.asarray(Image.open(SRC).convert("RGBA")).astype(np.float32) / 255   # the front view frame (yaw -24)
H, W = F.shape[:2]
a = F[..., 3]
ys, xs = np.nonzero(a > .5)
C = np.array([xs.mean(), ys.mean()])
# boundary distance per direction
N = 720; th = np.linspace(-np.pi, np.pi, N, endpoint=False)
B = np.zeros(N)
for i, t in enumerate(th):
    d = np.array([np.cos(t), np.sin(t)]); last = 0
    for rr in range(0, 900, 2):
        x, y = (C + d * rr).astype(int)
        if x < 0 or y < 0 or x >= W or y >= H: break
        if a[y, x] > .5: last = rr
    B[i] = last
k = np.exp(-.5 * (np.arange(-15, 16) / 6) ** 2); k /= k.sum()
B = np.convolve(np.r_[B[-15:], B, B[:15]], k, "valid")
GROUND = .864 * H
Rb = .30 * H; Cb = np.array([C[0] - .02 * W, GROUND - Rb]); print("ball", Cb[0] / W, Cb[1] / H, Rb / W, Rb / H)
pm = np.concatenate([F[..., :3] * F[..., 3:], F[..., 3:]], -1)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def frame(t):
    Ct = C * (1 - t) + Cb * t
    dx, dy = xx - Ct[0], yy - Ct[1]; rho = np.hypot(dx, dy); ang = np.arctan2(dy, dx)
    idx = ((ang + np.pi) / (2 * np.pi) * N).astype(int) % N
    Bs = B[idx]; Bt = Bs * (1 - t) + Rb * t
    s = rho / np.maximum(Bt, 1) * Bs
    sx = C[0] + np.cos(ang) * s; sy = C[1] + np.sin(ang) * s
    ok = (rho <= Bt * 1.12) & (sx >= 0) & (sy >= 0) & (sx < W - 1) & (sy < H - 1)
    x0 = np.clip(sx.astype(int), 0, W - 2); y0 = np.clip(sy.astype(int), 0, H - 2); fx = (sx - x0)[..., None]; fy = (sy - y0)[..., None]
    v = (pm[y0, x0] * (1 - fx) + pm[y0, x0 + 1] * fx) * (1 - fy) + (pm[y0 + 1, x0] * (1 - fx) + pm[y0 + 1, x0 + 1] * fx) * fy
    v *= ok[..., None]
    al = v[..., 3:]; rgb = np.where(al > 1e-4, v[..., :3] / np.maximum(al, 1e-4), 0)
    return np.concatenate([rgb, al], -1)
for t in map(float, sys.argv[3:]):
    Image.fromarray((np.clip(frame(t), 0, 1) * 255).astype(np.uint8)).save(f"{OUT}/ball{int(t*100):03d}.png")

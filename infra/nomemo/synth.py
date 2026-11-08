#!/usr/bin/env python3
"""No Memo: the game's sounds, drawn from numbers (no samples, no service), written to nomemo/sfx/ as small mono MP3s.

    python3 infra/nomemo/synth.py            every sound in nomemo/sfx/list.json
    python3 infra/nomemo/synth.py seal paid  only these

Needs numpy and ffmpeg (not on the server; run it where they are). The same seed gives the same files.
infra/nomemo/sfx.py on the server can make richer versions of the ambience and foley with ElevenLabs;
the game takes those over these when they exist.
"""
import json, os, subprocess, sys, tempfile, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "nomemo", "sfx")
SR = 44100
rng = np.random.default_rng(1720)


# ---------- building blocks ----------
def t_(sec):
    return np.arange(int(sec * SR)) / SR


def env(n, a=0.002, d=0.1, curve=1.0):
    """attack, then exponential decay with time constant d (seconds)."""
    t = np.arange(n) / SR
    e = np.exp(-t / max(d, 1e-4)) ** curve
    na = max(1, int(a * SR))
    e[:na] *= np.linspace(0, 1, na)
    return e


def fades(x, a=0.003, r=0.01):
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    x = x.copy()
    x[:na] *= np.linspace(0, 1, na)
    x[-nr:] *= np.linspace(1, 0, nr)
    return x


def noise(sec, color="white"):
    n = int(sec * SR)
    w = rng.standard_normal(n)
    if color == "white":
        return w
    f = np.fft.rfft(w)
    k = np.arange(len(f)); k[0] = 1
    f = f / (np.sqrt(k) if color == "pink" else k)
    x = np.fft.irfft(f, n)
    return x / (np.abs(x).max() + 1e-9)


def biquad(x, kind, f0, q=0.707):
    """RBJ cookbook biquad, plain loop-free via lfilter-like recursion in numpy (small files, fine)."""
    w0 = 2 * np.pi * f0 / SR
    al = np.sin(w0) / (2 * q)
    c = np.cos(w0)
    if kind == "lp":
        b = [(1 - c) / 2, 1 - c, (1 - c) / 2]
    elif kind == "hp":
        b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]
    else:  # band-pass, 0 dB peak
        b = [al, 0, -al]
    a = [1 + al, -2 * c, 1 - al]
    return lfilter(np.array(b) / a[0], np.array(a) / a[0], x)


def lfilter(b, a, x):
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    b0, b1, b2 = b
    _, a1, a2 = a
    for i in range(len(x)):
        xi = x[i]
        yi = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, xi, y1, yi
        y[i] = yi
    return y


def onepole_lp(x, fc):
    """a one-pole low-pass whose corner may move per sample (fc array or number)."""
    fc = np.broadcast_to(np.asarray(fc, float), x.shape)
    k = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.zeros_like(x); s = 0.0
    for i in range(len(x)):
        s += k[i] * (x[i] - s); y[i] = s
    return y


def osc(freq, sec, kind="sine", phase=0.0):
    freq = np.broadcast_to(np.asarray(freq, float), (int(sec * SR),))
    ph = 2 * np.pi * np.cumsum(freq) / SR + phase
    if kind == "sine":
        return np.sin(ph)
    if kind == "tri":
        return 2 / np.pi * np.arcsin(np.sin(ph))
    if kind == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1) - 1
    if kind == "square":
        return np.sign(np.sin(ph))
    raise ValueError(kind)


def bell(f, sec, d=0.6, bright=1.0):
    """an inharmonic struck-metal tone (ship's bell, chime)."""
    t = t_(sec); x = np.zeros_like(t)
    for ratio, amp, dd in ((0.5, 0.35, 1.4), (1.0, 1.0, 1.0), (1.19, 0.4, 0.7), (1.56, 0.3, 0.5), (2.0, 0.5 * bright, 0.45),
                           (2.74, 0.25 * bright, 0.3), (3.76, 0.15 * bright, 0.2), (5.4, 0.08 * bright, 0.12)):
        x += amp * np.sin(2 * np.pi * f * ratio * t + rng.uniform(0, 6)) * np.exp(-t / (d * dd))
    x[:int(0.001 * SR)] *= np.linspace(0, 1, int(0.001 * SR))
    return fades(x, 0.0001, min(0.3, sec / 4))


def pluck(f, sec, damp=0.996):
    """Karplus-Strong: a plucked string, a little dull (like gut on a ship's fiddle)."""
    n = int(sec * SR); p = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, p); y = np.zeros(n)
    for i in range(n):
        y[i] = buf[i % p]
        buf[i % p] = damp * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return fades(y, 0.0005, min(0.3, sec / 4))


def thump(f0=120, f1=45, sec=0.3, d=0.09):
    t = t_(sec)
    f = f1 + (f0 - f1) * np.exp(-t / 0.03)
    return fades(osc(f, sec) * env(len(t), 0.001, d), 0.0001, sec / 3)


def click(sec=0.03, f=3500, q=1.2, d=0.006):
    x = noise(sec) * env(int(sec * SR), 0.0003, d)
    return biquad(x, "bp", f, q)


def place(dst, src, at, gain=1.0):
    i = int(at * SR); j = min(len(dst), i + len(src))
    if i < len(dst):
        dst[i:j] += gain * src[:j - i]
    return dst


def room(x, mix=0.25, size=0.6):
    """a small dark wooden room: a few combs and all-passes (Schroeder), damped."""
    out = np.zeros(len(x) + int(size * 1.6 * SR)); out[:len(x)] = fades(x, 0.0001, 0.03)
    wet = np.zeros_like(out)
    for dl, g in ((0.0297, 0.77), (0.0371, 0.75), (0.0411, 0.73), (0.0437, 0.71)):
        d = int(dl * SR * (0.6 + size)); y = out.copy()
        for i in range(d, len(y)):
            y[i] += g * y[i - d]
        wet += y
    wet = onepole_lp(wet, 2800)
    for dl in (0.005, 0.0017):
        d = int(dl * SR); y = np.zeros_like(wet); g = 0.6
        for i in range(len(wet)):
            y[i] = -g * wet[i] + (wet[i - d] if i >= d else 0) + g * (y[i - d] if i >= d else 0)
        wet = y
    wet /= np.abs(wet).max() + 1e-9
    dry = out / (np.abs(out).max() + 1e-9)
    return (1 - mix) * dry + mix * wet


def soft(x, drive=1.5):
    return np.tanh(drive * x) / np.tanh(drive)


def loopable(x, xf=1.5):
    """fold the tail over the head so the file loops without a seam."""
    n = int(xf * SR)
    head, tail = x[:n].copy(), x[-n:]
    r = np.linspace(0, 1, n)
    x = x[:-n].copy()
    x[:n] = head * np.sqrt(r) + tail * np.sqrt(1 - r)
    return x


# ---------- the sounds ----------
def key(v):
    f = [3200, 3700, 2900, 4100][v]
    x = click(0.05, f, 1.4, 0.005) * 0.7 + click(0.05, 900 + 120 * v, 2.0, 0.01) * 0.6
    x = place(x, thump(260 + 25 * v, 140, 0.05, 0.012) * 0.5, 0.0)
    return x


def enter():
    x = np.zeros(int(0.32 * SR))
    place(x, click(0.06, 2600, 1.2, 0.008), 0.0, 0.8)
    place(x, thump(170, 70, 0.2, 0.05), 0.004, 0.9)
    place(x, click(0.05, 3400, 1.5, 0.006), 0.075, 0.45)   # the key coming back up
    place(x, bell(2400, 0.2, 0.05, 0.4), 0.09, 0.06)        # a margin bell, faint
    return x


def send():
    sec = 0.55; x = np.zeros(int(sec * SR))
    bits = rng.integers(0, 2, 28)
    step = 0.014
    for i, b in enumerate(bits):
        place(x, osc(1270 if b else 2070, step, "sine") * np.hanning(int(step * SR)), 0.02 + i * step, 0.5)
    x = biquad(x, "bp", 1700, 0.8) * 1.6
    sweep = osc(np.linspace(400, 2600, int(0.08 * SR)), 0.08, "tri") * env(int(0.08 * SR), 0.002, 0.04)
    place(x, sweep, 0.0, 0.35)
    return room(x * env(len(x), 0.001, 0.35, 0.4), 0.15, 0.3)


def accepted():
    x = np.zeros(int(0.7 * SR))
    for f, at in ((659.3, 0.0), (987.8, 0.085)):
        n = osc(f, 0.45, "tri") * 0.6 + osc(f * 2, 0.45, "sine") * 0.15
        place(x, n * env(len(n), 0.004, 0.12), at)
    return room(x, 0.25, 0.4)


def refused():
    sec = 0.5; t = t_(sec)
    f = 110 - 25 * t / sec
    x = osc(f, sec, "square") * 0.5 + osc(f * 1.01, sec, "saw") * 0.4
    x = onepole_lp(x, 900) * env(len(t), 0.003, 0.18)
    x = place(x, thump(90, 40, 0.3, 0.08), 0.0, 0.9)
    return soft(x * 1.6, 2.0)


def seal():
    """contract sealed: the wax stamp comes down, then a bell."""
    x = np.zeros(int(1.9 * SR))
    place(x, thump(140, 42, 0.45, 0.13), 0.0, 1.0)
    place(x, biquad(noise(0.08) * env(int(0.08 * SR), 0.0005, 0.012), "lp", 1800), 0.0, 0.7)
    place(x, biquad(noise(0.25) * env(int(0.25 * SR), 0.01, 0.06), "bp", 600, 0.7), 0.05, 0.25)  # wax squash
    place(x, bell(880, 1.6, 0.55), 0.17, 0.32)
    return room(x, 0.3, 0.6)


def paid():
    """the share is paid: coins onto a wooden table, then two bright notes."""
    x = np.zeros(int(1.6 * SR))
    at = 0.0
    for i in range(9):
        f = rng.uniform(2600, 5200)
        c = bell(f, 0.35, 0.06 + rng.uniform(0, 0.05), 1.2)
        place(x, c, at, 0.35 * (1 - i / 14))
        place(x, click(0.02, 1200, 1.0, 0.004), at, 0.25)
        at += rng.uniform(0.035, 0.11) * (1 + i / 10)
    for f, a in ((1046.5, 0.82), (1568, 0.92)):
        place(x, osc(f, 0.5, "tri") * env(int(0.5 * SR), 0.004, 0.14), a, 0.28)
    return room(x, 0.22, 0.5)


def dust():
    """the Tracer: a ping out of the dark, and its echo, a little off."""
    sec = 2.6; x = np.zeros(int(sec * SR))
    for i, (g, det) in enumerate(((1.0, 1.0), (0.45, 1.006), (0.22, 0.994), (0.11, 1.012))):
        p = osc(1180 * det, 1.4, "sine") * env(int(1.4 * SR), 0.003, 0.32)
        p += 0.3 * osc(1180 * det * 1.5, 1.4, "sine") * env(int(1.4 * SR), 0.003, 0.15)
        place(x, p, i * 0.42, g)
    t = t_(sec)
    drone = osc(55 + 1.5 * np.sin(2 * np.pi * 0.7 * t), sec, "saw")
    drone = biquad(biquad(drone, "lp", 260), "lp", 260) * np.minimum(1, t / 0.4) * np.exp(-t / 1.4) * 0.3
    return room(x + drone, 0.35, 0.8)


def hunt():
    """the hunt solved: a minor figure that resolves to major."""
    x = np.zeros(int(2.3 * SR))
    notes = ((220.0, 0.0), (261.6, 0.12), (329.6, 0.24), (440.0, 0.4), (277.2, 0.7), (329.6, 0.74), (440.0, 0.78), (554.4, 0.82))
    for f, at in notes:
        place(x, pluck(f, 1.4, 0.9965), at, 0.45)
    return room(x, 0.3, 0.6)


def chapter():
    """a chapter opens: a low horn swells, a bell on top."""
    sec = 3.0; t = t_(sec)
    shape = np.minimum(1, t / 0.9) * np.exp(-np.maximum(0, t - 1.3) / 0.6)
    x = np.zeros_like(t)
    for f, g in ((55, 0.6), (82.4, 0.45), (110, 0.4), (164.8, 0.25)):
        x += g * osc(f * (1 + 0.002 * np.sin(2 * np.pi * 4.5 * t)), sec, "saw")
    x = onepole_lp(x, 120 + 1400 * shape) * shape
    x = place(x, bell(659.3, 2.0, 0.7), 0.85, 0.35)
    x = place(x, bell(987.8, 1.8, 0.6), 1.05, 0.2)
    return room(soft(x, 1.2), 0.35, 0.8)


def mail():
    """mail aboard: the telegraph key, dit-dit, a small bell."""
    x = np.zeros(int(0.9 * SR))
    for at, ln in ((0.0, 0.05), (0.09, 0.05), (0.2, 0.12)):
        place(x, click(0.03, 2200, 1.2, 0.004), at, 0.6)
        tone = osc(720, ln, "square") * 0.5
        place(x, onepole_lp(fades(tone, 0.003, 0.006), 2500), at, 0.4)
    place(x, bell(1760, 0.6, 0.2, 0.6), 0.38, 0.22)
    return room(x, 0.15, 0.3)


def mark():
    """the crew's mark: a blade cut into the rail, a drum below."""
    sec = 1.1; x = np.zeros(int(sec * SR))
    n = int(0.42 * SR); s = noise(0.42)
    fc = np.linspace(2600, 1100, n)
    cut = np.zeros(n)
    for a, b in ((0, n // 2), (n // 2, n)):
        cut[a:b] = biquad(s[a:b], "bp", float(fc[(a + b) // 2]), 3.0)
    cut *= (np.sin(np.linspace(0, np.pi, n)) ** 0.6) * (0.6 + 0.4 * np.sin(2 * np.pi * 23 * np.arange(n) / SR))
    place(x, cut, 0.0, 0.5)
    place(x, thump(110, 50, 0.6, 0.18), 0.4, 1.0)
    place(x, click(0.04, 1500, 1.0, 0.01), 0.4, 0.4)
    return room(x, 0.3, 0.6)


def board():
    """the players' board: a ledger opened, pages."""
    sec = 0.8; x = np.zeros(int(sec * SR))
    for at in (0.0, 0.18, 0.31):
        n = int(0.22 * SR); r = noise(0.22, "pink")
        fl = 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * rng.uniform(18, 35) * np.arange(n) / SR))
        r = biquad(r * fl * np.sin(np.linspace(0, np.pi, n)) ** 2, "hp", 900)
        place(x, r, at, 0.9 if at == 0 else 0.55)
    place(x, thump(160, 90, 0.12, 0.03), 0.0, 0.35)
    return x


def out():
    """the trace completes: a falling klaxon, the line drops."""
    sec = 1.6; t = t_(sec)
    f = 520 * np.exp(-t * 0.9)
    x = (osc(f, sec, "saw") + osc(f * 1.5, sec, "saw") * 0.5)
    x = soft(onepole_lp(x, 2200) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 3.2 * t))) * 0.6, 2.5)
    x *= np.exp(-t / 0.8)
    st = biquad(noise(0.5), "bp", 3000, 0.6) * 0.25 * env(int(0.5 * SR), 0.01, 0.2)
    x = place(x, st, 1.1, 1.0)
    return room(x, 0.2, 0.5)


def boot():
    """the terminal comes on: the relay clunks, the tube warms up, a hum settles."""
    sec = 2.2; t = t_(sec)
    x = np.zeros_like(t)
    place(x, thump(90, 35, 0.4, 0.1), 0.0, 1.0)
    place(x, click(0.05, 1800, 1.0, 0.01), 0.0, 0.5)
    whine = osc(300 + 7400 * (1 - np.exp(-t / 0.5)), sec, "sine") * 0.05 * np.exp(-t / 0.9)
    hum = (osc(50, sec) + 0.5 * osc(100, sec) + 0.25 * osc(150, sec)) * 0.18 * np.minimum(1, t / 1.2)
    crackle = biquad(noise(sec) * (rng.random(len(t)) > 0.9985), "hp", 2000) * 0.8 * np.exp(-t / 0.7)
    x += whine + hum + crackle
    place(x, osc(440, 0.15, "tri") * env(int(0.15 * SR), 0.004, 0.05), 1.55, 0.3)
    place(x, osc(880, 0.2, "tri") * env(int(0.2 * SR), 0.004, 0.06), 1.65, 0.25)
    return fades(x, 0.002, 0.3)


def block():
    """a new block: two strokes of a muffled ship's bell, far off."""
    x = np.zeros(int(1.6 * SR))
    for at in (0.0, 0.32):
        place(x, onepole_lp(bell(523.3, 1.2, 0.45, 0.5), 1800), at, 0.6)
    return room(x, 0.5, 0.9)


def tick():
    """the trace clock, when it runs short."""
    x = click(0.04, 2400, 3.0, 0.004) * 0.8
    return place(x, thump(300, 200, 0.03, 0.008), 0.0, 0.4)


def amb_sea():
    """the sea round the hull, below decks: a slow swell, water slapping the planks."""
    sec = 20.0; t = t_(sec)
    swell = 0.55 + 0.25 * np.sin(2 * np.pi * t / 5.0) + 0.2 * np.sin(2 * np.pi * t / 10.0 + 1.3)   # periods divide 20 s: loops clean
    body = onepole_lp(noise(sec, "brown"), 220 + 260 * swell) * swell
    hiss = biquad(noise(sec, "pink"), "bp", 700, 0.5) * 0.12 * np.clip(swell - 0.45, 0, 1)
    x = body * 1.2 + hiss
    for at in np.arange(0.7, sec - 1, 2.5) + rng.uniform(-0.4, 0.4, len(np.arange(0.7, sec - 1, 2.5))):
        n = int(0.35 * SR)
        slap = biquad(biquad(noise(0.35) * env(n, 0.03, 0.09), "lp", 520), "lp", 520)
        place(x, slap, at, 0.5 * rng.uniform(0.4, 1))
    x = x / (np.abs(x).max() + 1e-9)
    return loopable(np.concatenate([x, x[:int(1.5 * SR)]]))


def amb_hum():
    """the lamp and the tube: mains hum with a lantern's flicker, a crackle now and then."""
    sec = 10.0; t = t_(sec)
    flick = 1 + 0.08 * np.sin(2 * np.pi * 0.3 * t) + 0.04 * np.sin(2 * np.pi * 1.7 * t)
    x = (osc(50, sec) + 0.6 * osc(100, sec) + 0.3 * osc(150, sec) + 0.15 * osc(250, sec)) * flick
    x += 0.15 * biquad(noise(sec, "pink"), "bp", 120, 2.0) * flick
    for at in rng.uniform(0.5, sec - 0.5, 9):
        place(x, biquad(noise(0.012), "hp", 3000) * env(int(0.012 * SR), 0.0002, 0.002), at, 0.6)
    x = x / (np.abs(x).max() + 1e-9)
    return loopable(np.concatenate([x, x[:int(1.0 * SR)]]), 1.0)


def amb_tension():
    """when the trace runs short: a low pulse, like a heart under the deck."""
    sec = 4.0; t = t_(sec)
    x = np.zeros_like(t)
    for beat in np.arange(0, sec, 1.0):
        place(x, thump(75, 38, 0.4, 0.09), beat, 1.0)
        place(x, thump(70, 36, 0.35, 0.08), beat + 0.24, 0.6)
    drone = onepole_lp(osc(41.2, sec, "saw") + osc(41.6, sec, "saw"), 160) * 0.2
    return fades(x + drone, 0.002, 0.002)


def creak(v):
    """the hull: wood rubbing on wood, stick and slip."""
    sec = [1.5, 2.1, 1.2][v]; n = int(sec * SR); t = t_(sec)
    rate = [55, 38, 80][v] * (1 + 0.5 * np.sin(np.pi * t / sec) ** 2) * (1 + 0.1 * np.sin(2 * np.pi * 3 * t))
    ph = np.cumsum(rate) / SR
    imp = np.zeros(n); idx = np.nonzero(np.diff(np.floor(ph)) > 0)[0]
    imp[idx] = rng.uniform(0.5, 1, len(idx))
    x = np.zeros(n)
    for f, q, g in ((210 + 30 * v, 6, 1.0), (520, 5, 0.6), (1150, 4, 0.3), (2300, 3, 0.12)):
        x += g * biquad(imp, "bp", f, q)
    x *= np.sin(np.pi * t / sec) ** 1.5
    return room(x, 0.35, 0.7)


SOUNDS = {
    "key-1": lambda: key(0), "key-2": lambda: key(1), "key-3": lambda: key(2), "key-4": lambda: key(3),
    "enter": enter, "send": send, "accepted": accepted, "refused": refused, "seal": seal, "paid": paid, "dust": dust,
    "hunt": hunt, "chapter": chapter, "mail": mail, "mark": mark, "board": board, "out": out, "boot": boot,
    "block": block, "tick": tick, "amb-sea": amb_sea, "amb-hum": amb_hum, "amb-tension": amb_tension,
    "creak-1": lambda: creak(0), "creak-2": lambda: creak(1), "creak-3": lambda: creak(2),
}


def write_mp3(name, x, kbps):
    x = x - x.mean()
    x = x / (np.abs(x).max() + 1e-9) * 0.89   # every file peaks at -1 dB; the game sets the loudness
    if not name.startswith("amb-"):   # the room's tail ends where it can no longer be heard (-60 dB), with a short fade
        loud = np.nonzero(np.abs(x) > 0.001)[0]
        end = min(len(x), (loud[-1] if len(loud) else len(x)) + int(0.02 * SR))
        x = fades(x[:end], 0.0005, min(0.08, end / SR / 4))
    pcm = (x * 32767).astype(np.int16)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    dst = os.path.join(OUT, name + ".mp3")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-ac", "1", "-ar", "44100", "-codec:a", "libmp3lame",
                    "-b:a", f"{kbps}k", "-map_metadata", "-1", "-id3v2_version", "0", "-write_xing", "0", dst], check=True)
    os.unlink(tmp)
    return os.path.getsize(dst)


def main():
    only = sys.argv[1:]
    lj = json.load(open(os.path.join(OUT, "list.json")))
    listed = {s["name"]: s for s in lj["sounds"]}
    total = 0
    for name, fn in SOUNDS.items():
        if only and name not in only:
            continue
        if name not in listed:
            sys.exit(f"{name} is not in nomemo/sfx/list.json")
        x = fn()
        size = write_mp3(name, x, 48 if name.startswith("amb-") else 64)
        total += size
        listed[name]["sec"] = round(len(x) / SR, 2) if name.startswith("amb-") else round(min(len(x) / SR, sec_of(name)), 2)
        print(f"  {name:<12} {len(x) / SR:5.2f} s  {size / 1024:6.1f} KB")
    with open(os.path.join(OUT, "list.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(lj, indent=1, ensure_ascii=False) + "\n")
    print(f"{total / 1024:.0f} KB")


def sec_of(name):
    """the length of the written file (its quiet tail is trimmed)."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                        os.path.join(OUT, name + ".mp3")], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 99.0


if __name__ == "__main__":
    main()

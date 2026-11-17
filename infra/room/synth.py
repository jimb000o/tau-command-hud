#!/usr/bin/env python3
"""The room, 1999: its sounds, drawn from numbers (no samples, no service), written to assets/room/sfx/ as small mono MP3s.

    python3 infra/room/synth.py              every sound in assets/room/sfx/list.json
    python3 infra/room/synth.py amb-rain     only these

Borrows the building blocks of infra/nomemo/synth.py (needs numpy and ffmpeg, not on the server). infra/room/sfx.py on
the server makes ElevenLabs versions from the "eleven" prompts in list.json; the room takes those where they exist.
The music is not here: it is played live in the browser (assets/room-sound.js).
"""
import importlib.util, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("nm", os.path.join(REPO, "infra", "nomemo", "synth.py"))
nm = importlib.util.module_from_spec(spec); spec.loader.exec_module(nm)
nm.OUT = OUT = os.path.join(REPO, "assets", "room", "sfx")
SR, rng = nm.SR, np.random.default_rng(1999)
t_, env, fades, noise, biquad, onepole_lp, osc, place, room, loopable, thump, click, bell = (
    nm.t_, nm.env, nm.fades, nm.noise, nm.biquad, nm.onepole_lp, nm.osc, nm.place, nm.room, nm.loopable, nm.thump, nm.click, nm.bell)
norm = lambda x: x / (np.abs(x).max() + 1e-9)


def amb_rain():
    """rain on the window glass and the sill, a gutter dripping, the hiss of the street behind it."""
    sec = 20.0; t = t_(sec)
    gust = 0.75 + 0.2 * np.sin(2 * np.pi * t / 10) + 0.1 * np.sin(2 * np.pi * t / 4 + 1)   # periods divide 20 s
    hiss = biquad(noise(sec, "pink"), "bp", 2600, 0.45) * 0.5 * gust + onepole_lp(noise(sec, "brown"), 300) * 0.35
    x = hiss
    for at in rng.uniform(0, sec - 0.05, 2600):   # drops on the glass: tiny bright ticks
        place(x, biquad(noise(0.012), "bp", rng.uniform(2500, 6500), 3) * env(int(0.012 * SR), 0.0001, 0.0016), at, rng.uniform(0.05, 0.3))
    for at in np.arange(0.4, sec - 0.5, 0.83):    # the gutter: a slow drip onto tin
        place(x, bell(rng.uniform(1700, 1900), 0.25, 0.05, 0.4), at + rng.uniform(-0.05, 0.05), 0.12)
    return loopable(np.concatenate([norm(x), norm(x)[:int(1.5 * SR)]]))


def amb_room():
    """the room itself: mains hum, the tubes' faint whine, an old fridge somewhere behind the wall."""
    sec = 10.0; t = t_(sec)
    hum = osc(60, sec) * 0.5 + osc(120, sec) * 0.3 + osc(180, sec) * 0.12
    fridge = onepole_lp(noise(sec, "brown"), 90) * (0.8 + 0.2 * np.sin(2 * np.pi * t / 5))
    whine = osc(15734, sec) * 0.012
    return loopable(np.concatenate([norm(hum * 0.35 + fridge * 0.9 + whine)] * 2)[: int((sec + 1) * SR)], 1.0)


def amb_neon():
    """the sign outside: a neon buzz through the glass, with a stutter now and then."""
    sec = 8.0; t = t_(sec)
    buzz = sum(a * osc(120 * k, sec, "square" if k == 1 else "sine") for k, a in ((1, 0.25), (2, 0.4), (3, 0.3), (5, 0.15), (7, 0.08)))
    flick = np.ones_like(t)
    for at in rng.uniform(0.5, sec - 1, 4):
        i = int(at * SR); n = int(rng.uniform(0.05, 0.25) * SR); flick[i:i + n] *= rng.uniform(0.1, 0.5)
    x = biquad(buzz * flick, "lp", 1800) + biquad(noise(sec), "hp", 4000) * 0.03 * (flick < 0.9)
    return loopable(np.concatenate([norm(x), norm(x)[:SR]]), 1.0)


def amb_street():
    """down on the wet street: a car now and then, tyres on water, far off."""
    sec = 24.0; x = onepole_lp(noise(sec, "brown"), 120) * 0.25
    for at in (1.5, 7.8, 12.2, 18.9):
        d = rng.uniform(3.5, 5.5); n = int(d * SR); tt = np.arange(n) / SR
        shape = np.exp(-((tt - d / 2) / (d / 5)) ** 2)
        swish = biquad(onepole_lp(noise(d, "pink"), 700 + 1500 * shape), "hp", 250) * shape
        place(x, swish, at, rng.uniform(0.6, 1.0))
    return loopable(np.concatenate([norm(x), norm(x)[:int(1.5 * SR)]]))


def foghorn():
    """the bay: a foghorn, far away, two low tones."""
    sec = 7.0; x = np.zeros(int(sec * SR))
    for at, f, d in ((0.0, 98, 2.6), (3.0, 87.3, 3.0)):
        n = int(d * SR); e = np.minimum(1, np.arange(n) / (0.4 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.8 * SR))
        tone = sum(a * osc(f * k, d, "saw") for k, a in ((1, 1), (1.005, 0.6))) * e
        place(x, onepole_lp(tone, 400), at, 1)
    return room(x, 0.6, 1.4)


def radiator(v):
    """the old radiator: a metal tick and knock as it warms."""
    x = np.zeros(int(0.9 * SR))
    for k in range(2 + v):
        at, g = k * rng.uniform(0.12, 0.25), rng.uniform(0.5, 1)
        place(x, bell(rng.uniform(380, 620), 0.4, 0.06, 0.6), at, g); place(x, click(0.02, 1800, 2, 0.003), at, g)
    return room(x, 0.3, 0.5)


def thunder():
    sec = 6.0; t = t_(sec)
    crack = biquad(noise(0.3), "hp", 300) * env(int(0.3 * SR), 0.005, 0.08)
    roll = onepole_lp(noise(sec, "brown"), 160) * np.exp(-t / 2.2) * (1 + 0.5 * np.sin(2 * np.pi * 1.3 * t) ** 2)
    x = place(roll, onepole_lp(crack, 2200), 0.0, 0.22)
    return room(x, 0.5, 1.2)


def purr():
    sec = 2.4; t = t_(sec)
    am = (0.5 + 0.5 * np.sin(2 * np.pi * 25 * t)) ** 2 * (0.6 + 0.4 * np.sin(np.pi * t / sec))
    breath = 0.65 + 0.35 * np.sign(np.sin(2 * np.pi * t / 1.2))
    return fades(onepole_lp(noise(sec, "brown"), 180) * am * breath, 0.05, 0.3)


def ring():
    """the phone, made friendly: a warm, rounded double purr in A (a major third, A4 and C#5), soft on, soft off,
    heard from across a small carpeted room. No square waves, nothing above 2 kHz worth hearing: it calls, it never startles."""
    x = np.zeros(int(1.9 * SR))
    for at in (0.0, 0.62):
        d = 0.42; tt = t_(d)
        trem = 0.72 + 0.28 * np.sin(2 * np.pi * 16 * tt)                 # a gentle flutter, never on/off
        tone_ = (np.sin(2 * np.pi * 440 * tt) + 0.75 * np.sin(2 * np.pi * 554.37 * tt)
                 + 0.12 * np.sin(2 * np.pi * 880 * tt) + 0.08 * np.sin(2 * np.pi * 1108.7 * tt))
        e = np.minimum(1, tt / 0.07) * np.minimum(1, (d - tt) / 0.16)       # 70 ms in, 160 ms out
        place(x, onepole_lp(tone_ * trem * e, 1800), at)
        place(x, bell(880, 1.1, 0.5, 0.15) * 0.12, at + d - 0.05)          # a small bell-like afterglow
    return room(x, 0.3, 0.7)


def pager():
    """the pager on the wooden desk: two short, soft hums against the wood, no beep (the music answers a block)."""
    x = np.zeros(int(0.75 * SR))
    for at in (0.0, 0.3):
        d = 0.17; tt = t_(d)
        hum = np.tanh(1.6 * np.sin(2 * np.pi * 118 * tt))                  # the motor, rounded
        wood = biquad(noise(d), "bp", 700, 1.2) * (0.5 + 0.5 * np.sin(2 * np.pi * 59 * tt)) * 0.25
        e = np.minimum(1, tt / 0.025) * np.minimum(1, (d - tt) / 0.05)
        place(x, onepole_lp((hum + wood) * e, 450), at)
    return room(x, 0.15, 0.4)


def disk():
    """the tower's hard disk: a quick seek, crunch and tick."""
    x = np.zeros(int(0.8 * SR))
    for k in range(9):
        place(x, click(0.012, rng.uniform(1500, 4000), 2.5, 0.002), k * 0.07 + rng.uniform(0, 0.03), rng.uniform(0.4, 1))
    return x + onepole_lp(noise(0.8), 500)[:len(x)] * 0.05


def crt():
    """a tube switching on: a soft degauss thunk and a low warm hum settling in (no high whine)."""
    sec = 1.4; t = t_(sec)
    thunk = thump(90, 40, 0.5, 0.15) + onepole_lp(noise(0.5, "brown"), 200) * env(int(0.5 * SR), 0.002, 0.1)
    hum = (np.sin(2 * np.pi * 60 * t) + 0.3 * np.sin(2 * np.pi * 120 * t)) * 0.12 * np.minimum(1, t / 0.4) * np.exp(-t / 0.9)
    static = onepole_lp(noise(sec), 2500) * 0.03 * np.exp(-t / 0.3)
    return place(hum + static, thunk, 0.0, 1.0)


def key(v):
    """the keyboard: a heavy 90s board, each key a little different."""
    x = click(0.05, [1900, 2300, 2100, 1700][v], 2.5, 0.006) * 0.8
    place(x, thump(260, 140, 0.04, 0.01), 0.004, 0.5)
    return place(x, click(0.02, 3500, 2, 0.003), 0.03, 0.25)


SOUNDS = {
    "amb-rain": amb_rain, "amb-room": amb_room, "amb-neon": amb_neon, "amb-street": amb_street,
    "foghorn": foghorn, "radiator-1": lambda: radiator(0), "radiator-2": lambda: radiator(1), "thunder": thunder,
    "purr": purr, "ring": ring, "pager": pager, "disk": disk, "crt": crt,
    "key-1": lambda: key(0), "key-2": lambda: key(1), "key-3": lambda: key(2), "key-4": lambda: key(3),
}


def main():
    only = sys.argv[1:]
    lj = json.load(open(os.path.join(OUT, "list.json")))
    listed = {s["name"]: s for s in lj["sounds"]}
    for name, fn in SOUNDS.items():
        if only and name not in only:
            continue
        if name not in listed:
            sys.exit(f"{name} is not in assets/room/sfx/list.json")
        x = fn()
        size = nm.write_mp3(name, x, 48 if name.startswith("amb-") else 64)
        print(f"  {name:<12} {len(x) / SR:5.2f} s  {size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()

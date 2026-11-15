"""The cut of a YouTube video (yt.py): the film service's pictures of each scene become one film, the camera moves in
where a scene's zoom step points, the voice comes in after the picture, a short's words run along as subtitles, and
the pulse mark moves once after the opening scene and on the end card. Pillow draws, ffmpeg does the rest.

  scene_clip()   one scene's pictures (taken a few times a second, each with its time) to a 30 fps clip; a zoom step
                 eases the frame towards its target over EASE seconds and stays there until the next zoom step
  sting()        the pulse mark drawing itself, 1.6 s (after the first scene of a long video: the hook comes first)
  end_card()     the pulse, the site, what to watch next, "not affiliated with IDNI", 5 s
  assemble()     everything in order with voice, room tone, captions; loudness evened out to -16 LUFS
  thumbnail()    1280x720: a dimmed picture from the film, Agorzilla, at most four words and one number

The camera rule comes from the cut, not from a clock: it moves when the scene's step says something is there to see.
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.environ.get("YT_FONTS", os.path.join(HERE, "fonts"))
FPS = 30
EASE = 0.9
SIZE = {"wide": (1920, 1080), "tall": (1080, 1920)}
ZMAX = {"wide": 1.8, "tall": 1.5}
BG, GREEN, GREY, WHITE = (9, 9, 10), (57, 255, 138), (150, 152, 150), (255, 255, 255)
STING = 1.6
END = 5.0
CRF = os.environ.get("YT_CRF", "19")
PRESET = os.environ.get("YT_PRESET", "veryfast")     # the node shares this machine: quick and light before small
THREADS = os.environ.get("YT_THREADS", "2")


class CutError(RuntimeError):
    pass


def ff(*args: str, timeout: int = 3600) -> None:
    p = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-threads", THREADS, *args], capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise CutError("ffmpeg: " + (p.stderr or "")[-600:])


def font(name: str, size: int, weight: int | None = None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if weight:
        try:
            f.set_variation_by_axes([weight])
        except Exception:  # noqa: BLE001  a font file without that axis
            pass
    return f


# ---------- the camera ----------
def camera(steps: list[dict], w: int, h: int, fmt: str = "wide") -> list[tuple[float, float, float, float]]:
    """(time, zoom, centre x, centre y) for each zoom step that found its target, or that goes back to the whole
    page; the frame the camera shows always stays inside the picture."""
    out = []
    for s in sorted(steps or [], key=lambda s: s.get("at", 0)):
        if s.get("do") != "zoom" or not s.get("ok"):
            continue
        r = s.get("rect")
        if not r:
            out.append((float(s["at"]), 1.0, w / 2, h / 2))
            continue
        x, y, rw, rh = (float(v) for v in r)
        rh = min(rh, h - max(0.0, y))                   # a tall list: only what is in the window counts
        z = max(1.12, min(ZMAX.get(fmt, 1.8), 0.86 * w / max(rw, 1), 0.86 * h / max(rh, 1)))
        cx = min(max(x + rw / 2, w / (2 * z)), w - w / (2 * z))
        cy = min(max(y + rh / 2, h / (2 * z)), h - h / (2 * z))
        out.append((float(s["at"]), round(z, 4), round(cx, 1), round(cy, 1)))
    return out


def _expr(keys: list[tuple[float, float]], start: float) -> str:
    """A value over time for ffmpeg: `start` until the first key, then eased to each key's value over EASE seconds."""
    e = f"{start:.4f}"
    prev = start
    for t, v in keys:
        p = f"clip((t-{t:.3f})/{EASE},0,1)"
        e = f"if(lt(t,{t:.3f}),{e},{prev:.4f}+({v:.4f}-{prev:.4f})*({p}*{p}*(3-2*{p})))"
        prev = v
    return e


def at(keys: list[tuple[float, float]], start: float, t: float) -> float:
    """The same value in Python (the tests check the camera with it)."""
    v = prev = start
    for kt, kv in keys:
        if t >= kt:
            p = min(1.0, max(0.0, (t - kt) / EASE))
            v = prev + (kv - prev) * (p * p * (3 - 2 * p))
        prev = kv
    return v


def scene_clip(frames_dir: str, frames: list, steps: list[dict], seconds: float, dst: str, fmt: str = "wide",
               src_size: tuple[int, int] | None = None) -> str:
    """One scene: its pictures held for as long as each stood on the screen, the camera moved by its zoom steps."""
    W, H = SIZE[fmt]
    sw, sh = src_size or (W, H)
    lst = dst + ".txt"
    with open(lst, "w") as f:
        for i, (name, t) in enumerate(frames):
            nxt = frames[i + 1][1] if i + 1 < len(frames) else seconds
            f.write(f"file '{os.path.join(frames_dir, name)}'\nduration {max(0.02, nxt - t):.3f}\n")
        f.write(f"file '{os.path.join(frames_dir, frames[-1][0])}'\n")
    cam = camera(steps, sw, sh, fmt)
    k = W / sw
    z = _expr([(t, zz) for t, zz, _, _ in cam], 1.0)
    cx = _expr([(t, x) for t, _, x, _ in cam], sw / 2)
    cy = _expr([(t, y) for t, _, _, y in cam], sh / 2)
    if cam:
        vf = (f"fps={FPS},scale=w='trunc({sw}*{k:.5f}*({z})/2)*2':h='trunc({sh}*{k:.5f}*({z})/2)*2':eval=frame:flags=bicubic,"
              f"crop={W}:{H}:x='max(0,min(iw-{W},({cx})*{k:.5f}*({z})-{W}/2))':y='max(0,min(ih-{H},({cy})*{k:.5f}*({z})-{H}/2))',format=yuv420p")
    else:
        vf = f"fps={FPS},scale={W}:{H}:flags=bicubic,format=yuv420p"
    ff("-f", "concat", "-safe", "0", "-i", lst, "-t", f"{seconds:.3f}", "-vf", vf, "-an", "-c:v", "libx264", "-preset", PRESET,
       "-crf", "16", "-r", str(FPS), dst)
    os.remove(lst)
    return dst


# ---------- the pulse mark, moving ----------
PULSE = [(13, 33), (23, 33), (27.5, 24), (34.5, 43), (39, 33), (50, 33)]   # the mark's own path (favicon.svg, 64 units)


def _along(pts: list[tuple[float, float]], share: float) -> list[tuple[float, float]]:
    """The first `share` (0..1) of a line through these points."""
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    left = sum(seg) * min(1.0, max(0.0, share))
    out = [pts[0]]
    for (a, b), d in zip(zip(pts, pts[1:]), seg):
        if left >= d:
            out.append(b)
            left -= d
        else:
            if d and left > 0:
                out.append((a[0] + (b[0] - a[0]) * left / d, a[1] + (b[1] - a[1]) * left / d))
            break
    return out


def _grid(im: Image.Image, step: int, a: int = 9) -> None:
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x in range(0, im.width, step):
        d.line([(x, 0), (x, im.height)], fill=(255, 255, 255, a))
    for y in range(0, im.height, step):
        d.line([(0, y), (im.width, y)], fill=(255, 255, 255, a))
    im.alpha_composite(layer)


def mark_frame(size: tuple[int, int], share: float, ring: float = 1.0, lines: list[tuple[str, str, int, tuple]] | None = None,
               text_alpha: float = 1.0, y_mark: float = 0.5, scale: float = 1.0) -> Image.Image:
    """One picture of the mark: the ring `ring` (0..1) there, the pulse drawn up to `share`, lines of text under it."""
    W, H = size
    im = Image.new("RGBA", size, BG + (255,))
    _grid(im, max(48, W // 40))
    c = (W / 2, H * y_mark)
    R = min(W, H) * 0.115 * scale
    d = ImageDraw.Draw(im)
    if ring > 0:
        g = int(150 * ring)
        d.ellipse([c[0] - R, c[1] - R, c[0] + R, c[1] + R], outline=(g, g + 2, g, 255), width=max(3, int(R * 0.075)))
    u = R / 23 * 0.96
    pts = [(c[0] + (x - 31.5) * u, c[1] + (y - 33.5) * u) for x, y in _along(PULSE, share)]   # the pulse's own middle on the ring's middle
    if len(pts) > 1:
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        wd = max(4, int(u * 4.2))
        ld.line(pts, fill=GREEN + (255,), width=wd, joint="curve")
        for p in (pts[0], pts[-1]):
            ld.ellipse([p[0] - wd / 2, p[1] - wd / 2, p[0] + wd / 2, p[1] + wd / 2], fill=GREEN + (255,))
        glow = layer.filter(ImageFilter.GaussianBlur(u * 3.5))
        glow.putalpha(glow.getchannel("A").point(lambda v: int(v * 0.5)))
        im.alpha_composite(glow)
        im.alpha_composite(layer)
        e, rr = pts[-1], u * 1.8
        ImageDraw.Draw(im).ellipse([e[0] - rr, e[1] - rr, e[0] + rr, e[1] + rr], fill=WHITE + (255,))
    if lines and text_alpha > 0:
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        y = c[1] + R * 1.45
        for text, face, px, col in lines:
            f = font(face, px, 700 if face == "Sora.ttf" and px >= 60 else None)
            for part in wrap(ld, text, f, int(W * 0.84)):
                tw = ld.textlength(part, font=f)
                ld.text(((W - tw) / 2, y), part, font=f, fill=tuple(col) + (int(255 * text_alpha),))
                y += px * 1.3
            y += px * 0.25
        im.alpha_composite(layer)
    return im.convert("RGB")


def wrap(d: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if cur and d.textlength(t, font=f) > width:
            out.append(cur)
            cur = w
        else:
            cur = t
    return out + ([cur] if cur else [])


def _pipe(frames, size: tuple[int, int], dst: str) -> str:
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}", "-r", str(FPS),
                          "-i", "-", "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", "16", "-pix_fmt", "yuv420p", "-threads", THREADS, dst],
                         stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for im in frames:
            p.stdin.write(im.tobytes())
        p.stdin.close()
    except BrokenPipeError:
        pass
    err = p.stderr.read().decode("utf-8", "replace")
    if p.wait():
        raise CutError("ffmpeg: " + err[-400:])
    return dst


def _smooth(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


def sting(dst: str, fmt: str = "wide") -> str:
    size = SIZE[fmt]
    px = 92 if fmt == "wide" else 84
    n = int(STING * FPS)

    def frames():
        for i in range(n):
            t = i / FPS
            yield mark_frame(size, _smooth(t / 0.9), ring=_smooth(t / 0.4), text_alpha=_smooth((t - 0.7) / 0.4),
                             lines=[("Tau HUD", "Sora.ttf", px, WHITE)], y_mark=0.44)
    return _pipe(frames(), size, dst)


def end_card(dst: str, fmt: str = "wide", nxt: str = "") -> str:
    size = SIZE[fmt]
    big, mid, small = (84, 40, 28) if fmt == "wide" else (80, 40, 28)
    lines = [("Tau HUD", "Sora.ttf", big, WHITE), ("See it live: tauhud.com", "JetBrainsMono.ttf", mid, GREEN)]
    if nxt:
        lines.append(("Next: " + nxt, "Sora.ttf", mid, (200, 202, 200)))
    lines.append(("A community project, not affiliated with IDNI. Test network, test coins without value.", "Sora.ttf", small, (120, 122, 120)))
    n = int(END * FPS)

    def frames():
        last = None
        for i in range(n):
            t = i / FPS
            if t < 1.4 or last is None:
                last = mark_frame(size, _smooth(t / 0.9), ring=_smooth(t / 0.4), text_alpha=_smooth((t - 0.5) / 0.6), lines=lines,
                                  y_mark=0.3 if fmt == "wide" else 0.34)
            yield last
    return _pipe(frames(), size, dst)


# ---------- words on the picture ----------
def _ass_time(t: float) -> str:
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def _ass_text(s: str) -> str:
    return s.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def chunks(words: list, most: int = 3, gap: float = 0.45) -> list[tuple[str, float, float]]:
    """A voice's words in groups of at most `most`, each shown while it is spoken; a pause starts a new group."""
    out, cur = [], []
    for w, a, b in words:
        if cur and (len(cur) >= most or a - cur[-1][2] > gap or cur[-1][0][-1:] in ".!?"):
            out.append((" ".join(x[0] for x in cur), cur[0][1], cur[-1][2]))
            cur = []
        cur.append((w, a, b))
    if cur:
        out.append((" ".join(x[0] for x in cur), cur[0][1], cur[-1][2]))
    return out


def ass(path: str, fmt: str, labels: list[tuple[str, float, float]], subs: list[tuple[str, float, float]]) -> str:
    """labels: a scene's caption (small, lower left; on a short: top), subs: spoken words (a short only, large)."""
    W, H = SIZE[fmt]
    tall = fmt == "tall"
    head = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Label,JetBrains Mono,{34 if not tall else 38},&H008AFF39,&H008AFF39,&H280A0909,&H280A0909,0,0,0,0,100,100,0,0,3,10,0,"
            f"{1 if not tall else 8},{56 if not tall else 60},56,{56 if not tall else 150},1\n"
            f"Style: Sub,Sora,{78 if tall else 52},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,0,0,1,{6 if tall else 4},2,2,80,80,"
            f"{430 if tall else 70},1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    rows = [f"Dialogue: 0,{_ass_time(a)},{_ass_time(b)},Label,,0,0,0,,{{\\fad(250,250)}}{_ass_text(t)}" for t, a, b in labels if t]
    rows += [f"Dialogue: 1,{_ass_time(a)},{_ass_time(max(b, a + 0.25))},Sub,,0,0,0,,{_ass_text(t)}" for t, a, b in subs if t]
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(rows) + "\n")
    return path


def crew_card(path: str, fmt: str = "wide") -> str:
    """The one short word about the crew, as a strip for the lower third (shown once, in the middle, never at the end
    alone: viewers leave at an outro)."""
    W, H = SIZE[fmt]
    w, h = (1040, 150) if fmt == "wide" else (960, 190)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=22, fill=(9, 9, 10, 235), outline=GREEN + (255,), width=2)
    d.text((34, 26), "Tau HUD is free and has no ads of its own.", font=font("Sora.ttf", 34 if fmt == "wide" else 32, 600), fill=WHITE + (255,))
    d.text((34, h - 64), "Its crew carries the costs: tauhud.com/crew", font=font("JetBrainsMono.ttf", 28), fill=GREEN + (255,))
    im.save(path)
    return path


# ---------- the whole film ----------
def assemble(dst: str, fmt: str, parts: list[dict], voices: list[dict], labels: list, subs: list, work: str, crew_at: float | None = None,
             bed: bool = True) -> dict:
    """parts: [{"path": clip, "seconds": s}] in order. voices: [{"path": mp3, "at": seconds from the film's start}].
    Returns {"seconds": the film's length}."""
    W, H = SIZE[fmt]
    total = sum(p["seconds"] for p in parts)
    lst = os.path.join(work, "parts.txt")
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{p['path']}'\n")
    sub = ass(os.path.join(work, "words.ass"), fmt, labels, subs)
    args = ["-f", "concat", "-safe", "0", "-i", lst]
    n = 1
    crew_in = None
    if crew_at is not None:
        card = crew_card(os.path.join(work, "crew.png"), fmt)
        args += ["-loop", "1", "-t", f"{total:.2f}", "-i", card]
        crew_in = n
        n += 1
    first_voice = n
    for v in voices:
        args += ["-i", v["path"]]
    n += len(voices)
    bed_in = None
    if bed:
        args += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anoisesrc=color=pink:amplitude=0.012:sample_rate=44100"]
        bed_in = n
        n += 1
    esc = sub.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    fonts = FONTS.replace("\\", "/").replace(":", "\\:")
    fc = [f"[0:v]subtitles='{esc}':fontsdir='{fonts}'[v0]"]
    vout = "v0"
    if crew_in is not None:
        y = H - (150 if fmt == "wide" else 190) - (120 if fmt == "wide" else 520)
        a, b = crew_at, crew_at + 6.0
        fc.append(f"[{crew_in}:v]format=rgba,fade=t=in:st={a:.2f}:d=0.4:alpha=1,fade=t=out:st={b - 0.4:.2f}:d=0.4:alpha=1[cw]")
        fc.append(f"[{vout}][cw]overlay=x=(W-w)/2:y={y}:enable='between(t,{a:.2f},{b:.2f})'[v1]")
        vout = "v1"
    mix = []
    for i, v in enumerate(voices):
        ms = int(round(v["at"] * 1000))
        fc.append(f"[{first_voice + i}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{i}]")
        mix.append(f"[a{i}]")
    if bed_in is not None:
        fc.append(f"[{bed_in}:a]lowpass=f=380,aformat=channel_layouts=stereo,afade=t=in:d=1.5,afade=t=out:st={max(0.0, total - 2):.2f}:d=2[bed]")
        mix.append("[bed]")
    if not mix:
        args += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]
        fc.append(f"[{n}:a]anull[aout]")
    else:
        fc.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=longest,apad,atrim=0:{total:.2f},loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
    script = os.path.join(work, "graph.txt")
    with open(script, "w") as f:
        f.write(";\n".join(fc))
    ff(*args, "-filter_complex_script", script, "-map", f"[{vout}]", "-map", "[aout]", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", PRESET,
       "-crf", CRF, "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", dst)
    return {"seconds": round(total, 2)}


def still(video: str, t: float, dst: str) -> str:
    ff("-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-q:v", "2", dst)
    return dst


def thumbnail(dst: str, back: str | None, words: str, number: str = "", agorzilla: str | None = None) -> str:
    """The preview picture: a dimmed picture from the film, our own creature's face on the right, few large words."""
    W, H = 1280, 720
    im = Image.new("RGBA", (W, H), BG + (255,))
    if back and os.path.exists(back):
        b = Image.open(back).convert("RGB")
        k = max(W / b.width, H / b.height)
        b = b.resize((int(b.width * k) + 1, int(b.height * k) + 1), Image.LANCZOS).crop((0, 0, W, H)).filter(ImageFilter.GaussianBlur(3))
        im.paste(Image.blend(Image.new("RGB", (W, H), BG), b, 0.38), (0, 0))
    d = ImageDraw.Draw(im)
    right = W - 60
    if agorzilla and os.path.exists(agorzilla):
        a = Image.open(agorzilla).convert("RGBA")
        k = (H * 0.92) / a.height
        a = a.resize((int(a.width * k), int(a.height * k)), Image.LANCZOS)
        im.alpha_composite(a, (W - a.width - 40, H - a.height))
        right = W - a.width - 70
    room = right - 70
    px = 150
    f = font("Sora.ttf", px, 800)
    words = words.strip().upper()
    while px > 60 and max((d.textlength(p, font=f) for p in wrap(d, words, f, room)), default=0) > room or len(wrap(d, words, f, room)) > 3:
        px -= 8
        f = font("Sora.ttf", px, 800)
    y = 70
    if number:
        nf = font("Sora.ttf", int(px * 1.25), 800)
        d.text((70, y), number, font=nf, fill=GREEN + (255,), stroke_width=6, stroke_fill=(0, 0, 0, 255))
        y += int(px * 1.45)
    for part in wrap(d, words, f, room):
        d.text((70, y), part, font=f, fill=WHITE + (255,), stroke_width=6, stroke_fill=(0, 0, 0, 255))
        y += int(px * 1.12)
    d.rectangle([0, H - 10, W, H], fill=GREEN + (255,))
    im.convert("RGB").save(dst, quality=90)
    return dst


def clean(work: str) -> None:
    shutil.rmtree(work, ignore_errors=True)

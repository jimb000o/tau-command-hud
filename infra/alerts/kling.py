"""Kling, the AI video maker: a still picture in, a few seconds of quiet motion out. Used by itself, never by hand:

  island    the island painting the game shows, alive: sea, smoke, lights (kling_island.py; on tauhud.com/rabbit/)
  trailer   a new island painting, once, as a short trailer for Telegram and X (kling_island.py)
  ship      a cruise ship's announcement as a video: the ship at anchor, then the card fades in (cruise_crier.py)
  pirate    the pirates' clip on a living sea instead of a still one (trick_clip.py)
  agorzilla Agorzilla's new growth stage as a short video on its own X account (agorzilla.py)

Each use asks for a clip when its event comes near, goes on with its work and picks the clip up on a later pass (a
clip takes one to ten minutes); a clip that is not there in time, a failed one or no key at all means the post goes out
as before, with its still picture. Nothing waits on Kling.

Honest by construction:
  - KLING_MONTH_CAP (default 30) clips a month for all uses together; then no more are asked for until the next month
  - the first KLING_REVIEW (default 2) clips of every public use are drafts: the post goes out as before, the clip goes
    to node.tauhud.com/kling/drafts/ and the owner hears about it privately with one line that posts it
    (up kling send <key>); from the third on, that use posts by itself
  - a failed clip is not asked for again (no credits spent in a loop)

Keys in infra/.env: KLING_API_KEY (sent as it is, "Authorization: Bearer <key>"), or KLING_ACCESS_KEY and
KLING_SECRET_KEY (Kling's own pair: a JWT signed with the secret, made here every 25 minutes). KLING_API_BASE when the
key comes from another address than Kling's own (default: Kling's Singapore address, then its older global one).
KLING_USES (default island,trailer,ship,pirate,agorzilla) switches uses off by leaving them out; KLING=false stops all.

One state file per service (/state/kling-<service>.json): the blog and agorzilla services never write the same file;
the month's count adds them all up.

  python kling.py line            this month in one line (the `up` block)
  python kling.py test            one 5 s clip of the live island, waited for (up to 10 min), to look at in drafts/
  python kling.py list            every clip asked for, newest first
  python kling.py send <key>      post a draft now (its texts were kept with it)
  python kling.py off island      the living island off again (the still painting shows), until the next painting
"""
from __future__ import annotations

import base64
import glob
import hashlib
import hmac
import io
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, "/app")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

log = logging.getLogger("kling")

API_KEY = os.environ.get("KLING_API_KEY", "").strip()
ACCESS = os.environ.get("KLING_ACCESS_KEY", "").strip()
SECRET = os.environ.get("KLING_SECRET_KEY", "").strip()
BASES = [b.rstrip("/") for b in (os.environ.get("KLING_API_BASE", "").strip() or
                                 "https://api-singapore.klingai.com https://api.klingai.com").split() if b]
# the models tried in this order until Kling takes one (it retires models: kling-v2-1 answered "discontinued" on
# 7 November 2026); the first that works is remembered (state "model") and asked first from then on
MODELS = (os.environ.get("KLING_MODEL", "").strip() or "kling-v2-6 kling-v2-5-turbo kling-v2-1-master kling-v1-6").split()
MODEL = MODELS[0]
CAP = int(os.environ.get("KLING_MONTH_CAP", "30") or 0)
REVIEW = int(os.environ.get("KLING_REVIEW", "2") or 0)
USES = {u.strip() for u in os.environ.get("KLING_USES", "island,trailer,ship,pirate,agorzilla").split(",") if u.strip()}
ON = os.environ.get("KLING", "true").lower() in ("1", "true", "yes")
WHO = os.environ.get("KLING_WHO", "blog")
STATE_DIR = os.environ.get("KLING_STATE_DIR", "/state")
OUT = os.environ.get("KLING_OUT", "/public/kling")   # what Caddy serves: the living island, drafts/
RAW = os.environ.get("KLING_RAW", os.path.join(STATE_DIR, "kling-raw"))   # Kling's clips as they came, never served
NODE = os.environ.get("NODE_URL", "https://node.tauhud.com").rstrip("/")
PUBLIC = f"{NODE}/kling"
LATE = 2 * 3600          # a clip not done after this long is given up (Kling's queue can be slow, never this slow)
NEG = ("camera shake, zoom, pan, morphing, warping buildings, melting, new objects, extra people, text, letters, logo, "
       "watermark, flicker, blur, low quality")
PUBLIC_USES = ("trailer", "ship", "pirate", "agorzilla")   # posted to a channel: the first REVIEW are drafts


def enabled(use: str | None = None) -> bool:
    """A key, Kling on, and that use not left out of KLING_USES (`up kling test` is no use: always on with a key)."""
    return ON and bool(API_KEY or (ACCESS and SECRET)) and (use is None or use == "test" or use in USES)


# ---------- the key ----------
_tok = {"t": "", "until": 0}


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def jwt(ak: str, sk: str, now: float | None = None) -> str:
    """Kling's token from its access and secret key: HS256, iss = access key, valid 30 minutes from 5 s ago."""
    now = int(time.time() if now is None else now)
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64(json.dumps({"iss": ak, "exp": now + 1800, "nbf": now - 5}, separators=(",", ":")).encode())
    sig = _b64(hmac.new(sk.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
    return f"{head}.{body}.{sig}"


def bearer() -> str:
    if API_KEY:
        return API_KEY
    if time.time() > _tok["until"]:
        _tok.update(t=jwt(ACCESS, SECRET), until=time.time() + 1500)
    return _tok["t"]


# ---------- the API ----------
def _call(method: str, path: str, body: dict | None = None) -> dict:
    """One call, to the first address that answers; Kling's own error ("code" not 0) raised with its message."""
    last = None
    for base in BASES:
        req = urllib.request.Request(base + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": "Bearer " + bearer(), "Content-Type": "application/json",
                                              "User-Agent": "tauhud-kling/1 (+https://tauhud.com)"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                j = json.load(r)
        except urllib.error.HTTPError as e:
            raw = e.read()[:400]
            try:
                j = json.loads(raw)
            except ValueError:
                raise RuntimeError(f"kling {path}: HTTP {e.code} {raw!r}") from None
            raise RuntimeError(f"kling {path}: HTTP {e.code} code {j.get('code')} {j.get('message')}") from None
        except (urllib.error.URLError, OSError) as e:   # this address does not answer: the next one
            last = e
            continue
        if j.get("code") not in (0, None):
            raise RuntimeError(f"kling {path}: code {j.get('code')} {j.get('message')}")
        return j.get("data") or {}
    raise RuntimeError(f"kling {path}: no address answered ({last})")


def jpeg(image) -> bytes:
    """A path, PIL image or bytes as a JPEG of at most 1920 px on its long side (Kling takes up to 10 MB)."""
    from PIL import Image
    if isinstance(image, (bytes, bytearray)):
        image = Image.open(io.BytesIO(image))
    elif isinstance(image, str):
        image = Image.open(image)
    im = image.convert("RGB")
    k = 1920 / max(im.size)
    if k < 1:
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=92)
    return b.getvalue()


def model_gone(e: Exception) -> bool:
    """Kling's answer for a model it does not offer (any more): code 1203, or words to that effect."""
    t = str(e).lower()
    return "code 1203" in t or "discontinued" in t or ("model" in t and ("not support" in t or "not exist" in t or "invalid" in t))


def submit(img: bytes, prompt: str, negative: str = NEG, duration: str = "5", mode: str = "std", tail: bool = False) -> tuple[str, bool]:
    """A new clip from the picture; (task id, whether the last frame is the picture again). A model Kling no longer
    offers: the next one of MODELS. A model that takes no last frame is asked once more without it: the use then
    makes the loop itself (loop())."""
    global MODEL
    b = base64.b64encode(img).decode()
    st = state()
    order = ([st["model"]] if st.get("model") in MODELS else []) + [m for m in MODELS if m != st.get("model")]
    last = None
    for model in order:
        body = {"model_name": model, "image": b, "prompt": prompt[:2500], "negative_prompt": negative[:2500],
                "mode": mode, "duration": str(duration)}
        for with_tail in ([True, False] if tail else [False]):
            try:
                task = str(_call("POST", "/v1/videos/image2video", {**body, "image_tail": b} if with_tail else body)["task_id"])
            except RuntimeError as e:
                if "HTTP 401" in str(e) or "HTTP 429" in str(e) or "no address" in str(e):
                    raise
                last = e
                if model_gone(e):
                    log.info("model %s not offered (%s): the next one", model, e)
                    break
                if with_tail:
                    log.info("no last frame with %s/%s (%s): asked without it", model, mode, e)
                    continue
                raise
            MODEL = model
            if st.get("model") != model:
                st = state(); st["model"] = model; save(st)
            return task, with_tail
    raise RuntimeError(f"no model of {' '.join(MODELS)} is offered (KLING_MODEL in .env): {last}")


def query(task: str) -> dict:
    return _call("GET", f"/v1/videos/image2video/{task}")


# ---------- the state ----------
def _path(who: str = WHO) -> str:
    return os.path.join(STATE_DIR, f"kling-{who}.json")


def state() -> dict:
    try:
        with open(_path()) as f:
            st = json.load(f)
    except (OSError, ValueError):
        st = {}
    st.setdefault("jobs", {})
    st.setdefault("off", {})
    return st


def save(st: dict) -> None:
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(_path() + ".tmp", "w") as f:
            json.dump(st, f, indent=1)
        os.replace(_path() + ".tmp", _path())
    except OSError as e:
        log.warning("state not saved: %s", e)


def month(t: float | None = None) -> str:
    return time.strftime("%Y-%m", time.gmtime(time.time() if t is None else t))


def all_jobs() -> list[dict]:
    """Every clip of every service, newest first (for the month's count and `up kling`)."""
    out = []
    for p in glob.glob(os.path.join(STATE_DIR, "kling-*.json")):
        try:
            with open(p) as f:
                out += [{"key": k, **j} for k, j in (json.load(f).get("jobs") or {}).items()]
        except (OSError, ValueError):
            pass
    return sorted(out, key=lambda j: j.get("at") or 0, reverse=True)


def this_month(now: float | None = None) -> int:
    m = month(now)
    return sum(1 for j in all_jobs() if j.get("task") and month(j.get("at")) == m)


def asked_of(kind: str) -> int:
    return sum(1 for j in all_jobs() if j.get("kind") == kind and j.get("task") and j.get("status") != "failed")


# ---------- asking, picking up ----------
def ask(key: str, kind: str, image, prompt: str, *, duration: str = "5", mode: str = "std", tail: bool = False,
        negative: str = NEG, now: float | None = None) -> dict:
    """The clip `key`: asked for once (when this use is on and the month leaves room), afterwards picked up. Never
    raises: {"status": "off" | "capped" | "error" | "submitted" | "processing" | "succeed" | "failed", "file": ...}."""
    now = time.time() if now is None else now
    if not enabled(kind):
        return {"status": "off"}
    st = state()
    j = st["jobs"].get(key)
    if j:
        return poll(key, st, now)
    if CAP and this_month(now) >= CAP:
        return {"status": "capped", "why": f"{CAP} clips this month (KLING_MONTH_CAP)"}
    try:
        img = image() if callable(image) else image
        task, tl = submit(jpeg(img), prompt, negative, duration, mode, tail)
    except Exception as e:  # noqa: BLE001 - no clip this time; asked again on a later pass
        log.warning("%s: not asked (%s)", key, e)
        return {"status": "error", "why": str(e)[:300]}
    draft = kind in PUBLIC_USES and asked_of(kind) < REVIEW
    st = state()   # submit() may have written the model that worked
    st["jobs"][key] = {"kind": kind, "task": task, "at": round(now), "status": "submitted", "tail": tl, "draft": draft,
                       "duration": str(duration), "mode": mode, "model": MODEL}
    save(st)
    log.info("%s: asked (%s %s s %s%s)", key, kind, duration, mode, ", a draft" if draft else "")
    return dict(st["jobs"][key])


def poll(key: str, st: dict | None = None, now: float | None = None) -> dict:
    """Looks once whether the clip is done; a done one is fetched into RAW/<key>.mp4 (Kling's link expires)."""
    now = time.time() if now is None else now
    st = st or state()
    j = st["jobs"].get(key)
    if not j:
        return {"status": "none"}
    if j.get("status") in ("succeed", "failed") or not j.get("task"):
        return dict(j)
    try:
        d = query(j["task"])
    except Exception as e:  # noqa: BLE001
        if now - j["at"] > LATE:
            j.update(status="failed", why=f"not done after {LATE // 3600} h ({e})"[:300]); save(st)
        return {**j, "why": str(e)[:300]}
    s = d.get("task_status") or j["status"]
    if s == "succeed":
        vids = ((d.get("task_result") or {}).get("videos") or [])
        if not vids:
            j.update(status="failed", why="done without a video")
        else:
            f = os.path.join(RAW, key + ".mp4")
            try:
                fetch(vids[0]["url"], f)
                j.update(status="succeed", file=f, seconds=float(vids[0].get("duration") or j.get("duration") or 5), done=round(now))
            except Exception as e:  # noqa: BLE001 - fetched on the next pass
                return {**j, "why": f"download: {e}"[:300]}
    elif s == "failed":
        j.update(status="failed", why=str(d.get("task_status_msg") or "failed")[:300])
    elif now - j["at"] > LATE:
        j.update(status="failed", why=f"still {s} after {LATE // 3600} h")
    else:
        j["status"] = s
    save(st)
    return dict(j)


def fetch(url: str, dst: str) -> str:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "tauhud-kling/1 (+https://tauhud.com)"})
    with urllib.request.urlopen(req, timeout=180) as r, open(dst + ".part", "wb") as f:
        shutil.copyfileobj(r, f)
    os.replace(dst + ".part", dst)
    return dst


def ready(key: str) -> dict | None:
    """The finished clip (its job, "file" the local mp4), or None."""
    j = poll(key)
    return j if j.get("status") == "succeed" and j.get("file") and os.path.exists(j["file"]) else None


def mark(key: str, **kw) -> None:
    st = state()
    if key in st["jobs"]:
        st["jobs"][key].update(kw)
        save(st)


# ---------- video helpers (ffmpeg) ----------
def ff(*args: str) -> None:
    p = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError("ffmpeg: " + (p.stderr or "")[-400:])


def loop(src: str, dst: str, seconds: float, fade: float = 1.0) -> str:
    """A clip that loops without a seam: its end crossfaded into its start (a clip whose last frame is its first
    already loops; this is for one that does not). The result is `fade` seconds shorter."""
    d = max(2 * fade + 0.5, seconds)
    ff("-i", src, "-filter_complex",
       f"[0:v]split[a][b];[a]trim={fade}:{d},setpts=PTS-STARTPTS[x];[b]trim=0:{fade},setpts=PTS-STARTPTS[y];"
       f"[x][y]xfade=transition=fade:duration={fade}:offset={d - 2 * fade},format=yuv420p[v]",
       "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-threads", "2", "-movflags", "+faststart", dst)
    return dst


def web(src: str, dst: str, w: int = 1600, h: int = 900, crf: int = 22) -> str:
    """H.264, yuv420p, faststart, no sound, the size given (-2, -2: the clip's own, even): plays in every browser, on
    Telegram and on X."""
    if w < 0:
        w, h = "trunc(iw/2)*2", "trunc(ih/2)*2"
    ff("-i", src, "-vf", f"scale={w}:{h}:flags=lanczos,fps=25,format=yuv420p", "-an", "-c:v", "libx264", "-preset", "veryfast",
       "-crf", str(crf), "-threads", "2", "-movflags", "+faststart", dst)
    return dst


def then_card(clip: str, card: str, dst: str, seconds: float, hold: float = 4.0, fade: float = 0.8, w: int = 1600, h: int = 900) -> str:
    """The clip, then the still picture with its card fading in over its last frame and held (the clip's last frame
    is the picture without the card, so only the card appears)."""
    off = max(0.5, seconds - fade)
    ff("-i", clip, "-loop", "1", "-t", str(hold + fade), "-i", card, "-filter_complex",
       f"[0:v]scale={w}:{h}:flags=lanczos,fps=25,format=yuv420p,setsar=1[a];[1:v]scale={w}:{h},fps=25,format=yuv420p,setsar=1[b];"
       f"[a][b]xfade=transition=fade:duration={fade}:offset={off}[v]",
       "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-threads", "2", "-movflags", "+faststart", dst)
    return dst


# ---------- drafts and posting ----------
def draft(key: str, video: str, post: dict | None = None) -> str:
    """The clip in OUT/drafts/ to look at; its post (texts, account) kept with the job for `up kling send`."""
    os.makedirs(os.path.join(OUT, "drafts"), exist_ok=True)
    dst = os.path.join(OUT, "drafts", key + ".mp4")
    shutil.copyfile(video, dst + ".part")
    os.replace(dst + ".part", dst)
    mark(key, video=dst, post=post or {}, drafted=round(time.time()))
    return f"{PUBLIC}/drafts/{key}.mp4"


def draft_note(key: str, kind: str, url: str, what: str) -> str:
    left = max(0, REVIEW - asked_of(kind))
    return (f"Kling clip, a draft ({what}): {url}\n"
            "The post went out as before, with the still picture." +
            (f" {left} more draft{'s' if left != 1 else ''} of this kind, then it posts by itself." if left else
             " From the next one on, this kind posts by itself.") +
            "\nPost this clip now instead:\n" + f'ssh root@node.tauhud.com "sh /opt/tau-command-hud/infra/up.sh kling send {key}"'
            + "\nNot good? Switch the kind off: leave it out of KLING_USES in infra/.env")


def post_video(path: str, post: dict) -> list[str]:
    """Telegram (caption, HTML) and X (text without link) as the post says; X on Agorzilla's own account when
    post["account"] == "agorzilla". Returns what each said."""
    import alerts
    import post_video as pv
    said = []
    acc = post.get("account", "tauhud")
    if post.get("telegram") and acc == "tauhud":
        if alerts.Telegram().enabled():
            try:
                pv.telegram_video(path, post["telegram"], *post.get("size", (1600, 900))); said.append("telegram: posted")
            except Exception as e:  # noqa: BLE001
                said.append(f"telegram: {e}")
        else:
            said.append("telegram: not set up")
    if post.get("x"):
        keys = ({k: os.environ.get("AGORZILLA_" + k, "").strip() for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")}
                if acc == "agorzilla" else None)
        if not all((keys or alerts.X_KEYS).values()):
            said.append("x: not set up")
        else:
            try:
                said.append(("x: https://x.com/Agorzilla/status/" if acc == "agorzilla" else "x: https://x.com/TauHUDcom/status/")
                            + pv.x_video(path, post["x"], keys))
            except Exception as e:  # noqa: BLE001
                said.append(f"x: {e}")
    return said


def tell(text: str) -> tuple[bool, str]:
    try:
        import tickerwatch
        return tickerwatch.tell(text[:4000])
    except Exception as e:  # noqa: BLE001
        return False, str(e)


# ---------- the `up` block ----------
def line(now: float | None = None) -> str:
    if not ON:
        return "kling:   off (KLING=false)"
    if not enabled():
        return "kling:   no key yet (KLING_API_KEY in infra/.env), every post goes out with its still picture"
    n = this_month(now)
    jobs = all_jobs()
    last = jobs[0] if jobs else None
    s = f"kling:   {n} of {CAP or 'unlimited'} clips this month (KLING_MONTH_CAP)"
    if last:
        s += f"; last {last['key']}: {last.get('status')}" + (", a draft" if last.get("draft") else "") + (
            f" ({last['why'][:80]})" if last.get("status") == "failed" and last.get("why") else "")
    try:
        with open(os.path.join(OUT, "island.json")) as f:
            s += f"; living island: {json.load(f).get('of')}"
    except (OSError, ValueError):
        pass
    return s


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    cmd = argv[0] if argv else ""
    if cmd == "line":
        print(line()); return 0
    if cmd == "list":
        for j in all_jobs():
            print(f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(j.get('at') or 0))}  {j['key']}  {j.get('status')}"
                  + (" draft" if j.get("draft") else "") + (f"  {j.get('why')}" if j.get("why") else ""))
        return 0
    if cmd == "test":
        if not enabled():
            print(line()); return 1
        import island_pic
        art = os.environ.get("ART_DIR", "/art")
        from PIL import Image
        import cruise_pic
        im = cruise_pic.island_view(Image.open(island_pic.painting(art)).convert("RGB"), 0, 0, 1)
        key = "test-" + time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        j = ask(key, "test", im, "Calm hand-painted island, camera completely still. Only the sea ripples softly and "
                "smoke drifts slowly from the chimneys.", duration="5", mode="std")
        if j.get("status") in ("off", "capped", "error"):
            print(f"kling:   test not asked: {j.get('why') or j.get('status')}"); return 1
        print(f"kling:   asked ({j.get('task')}), waiting up to 10 minutes ...", flush=True)
        t0 = time.time()
        while time.time() - t0 < 600:
            time.sleep(15)
            j = poll(key)
            if j.get("status") in ("succeed", "failed"):
                break
        if j.get("status") != "succeed":
            print(f"kling:   test {j.get('status')}: {j.get('why') or 'not done in 10 minutes (up kling list shows it later)'}"); return 1
        os.makedirs(os.path.join(OUT, "drafts"), exist_ok=True)
        web(j["file"], os.path.join(OUT, "drafts", "test.mp4"))
        print(f"kling:   test clip made in {time.time() - t0:.0f} s, look: {PUBLIC}/drafts/test.mp4"); return 0
    if cmd == "send" and len(argv) > 1:
        st = state()
        j = st["jobs"].get(argv[1])
        if not j or not j.get("video") or not j.get("post"):
            print(f"kling:   {argv[1]}: no draft with a post to send"); return 1
        if j.get("sent") and "--again" not in argv:
            print(f"kling:   {argv[1]}: already sent ({j['sent']}); --again sends it a second time"); return 1
        said = post_video(j["video"], j["post"])
        mark(argv[1], sent="; ".join(said))
        print("kling:   " + "; ".join(said)); return 0
    if cmd == "off" and argv[1:2] == ["island"]:
        p = os.path.join(OUT, "island.json")
        try:
            with open(p) as f:
                of = json.load(f).get("of")
            os.remove(p)
        except (OSError, ValueError):
            of = None
        st = state()
        st["off"]["island"] = of or True
        save(st)
        print(f"kling:   living island off ({of or 'none was on'}); the next island painting gets one again"); return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

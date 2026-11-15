"""YouTube for the video service (yt.py): the one-time sign-in, an upload as a private draft, the release, the preview
picture, and the numbers the channel's own analytics give. Plain urllib, nothing to install.

Sign-in (once, `up yt login`): a Google "Desktop app" OAuth client (YT_CLIENT_ID, YT_CLIENT_SECRET in infra/.env). The
owner opens the printed link, allows the channel, and the browser then tries to open http://127.0.0.1:8765/?code=...
which shows an error page: that address, copied from the browser's address line and pasted back here, carries the
code. The refresh token is kept in YT_TOKEN_PATH (the state volume), never in the repository, never printed.
  The Google project's OAuth consent screen must be "In production": in "Testing" Google lets a refresh token live
  seven days only (developers.google.com/identity/protocols/oauth2, read 15 November 2026).
Scopes: youtube.upload (videos, preview pictures), youtube.readonly and yt-analytics.readonly (the numbers).

What the API does not give (read on Google's pages the same day): the preview picture's click rate, and pinning a
comment. Both stay in YouTube Studio; yt.py says so instead of guessing.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

CLIENT_ID = os.environ.get("YT_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("YT_CLIENT_SECRET", "").strip()
TOKEN_PATH = os.environ.get("YT_TOKEN_PATH", "/state/yt-token.json")
REDIRECT = os.environ.get("YT_REDIRECT", "http://127.0.0.1:8765")
AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3"
ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"
SCOPES = ("https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly "
          "https://www.googleapis.com/auth/yt-analytics.readonly")
CHUNK = 8 * 2**20      # a multiple of 256 KB, as the resumable protocol asks

_opener = urllib.request.urlopen      # the tests put their own here
_access: dict = {}


class YtError(RuntimeError):
    pass


def configured() -> bool:
    return bool(CLIENT_ID)


def signed_in() -> bool:
    return bool(_token().get("refresh_token"))


def _token() -> dict:
    try:
        with open(TOKEN_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_token(t: dict) -> None:
    tmp = TOKEN_PATH + ".part"
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        json.dump(t, f)
    os.replace(tmp, TOKEN_PATH)


def _http(req: urllib.request.Request, timeout: int = 120):
    """(status, headers, body bytes); an HTTP error status comes back the same way instead of being raised."""
    try:
        with _opener(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


def _why(body: bytes) -> str:
    try:
        j = json.loads(body.decode("utf-8", "replace"))
        e = j.get("error")
        if isinstance(e, dict):
            return str(e.get("message") or e)[:300]
        return f"{e}: {j.get('error_description', '')}"[:300]
    except ValueError:
        return body.decode("utf-8", "replace")[:300]


# ---------- sign-in ----------
def login_link() -> tuple[str, str]:
    """(the link to open, the verifier to keep until the code comes back)."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    q = {"client_id": CLIENT_ID, "redirect_uri": REDIRECT, "response_type": "code", "scope": SCOPES,
         "code_challenge": challenge, "code_challenge_method": "S256", "access_type": "offline", "prompt": "consent"}
    return AUTH + "?" + urllib.parse.urlencode(q), verifier


def code_of(pasted: str) -> str:
    """The code from what the owner pasted: the whole address from the browser's address line, or the code alone."""
    pasted = pasted.strip().strip('"').strip("'")
    if "code=" in pasted or "error=" in pasted:
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(pasted).query)
        if q.get("error"):
            raise YtError(f"Google said: {q['error'][0]}")
        return (q.get("code") or [""])[0]
    return pasted


def login_finish(pasted: str, verifier: str) -> str:
    code = code_of(pasted)
    if not code:
        raise YtError("no code in what was pasted: copy the whole address from the browser's address line")
    body = {"client_id": CLIENT_ID, "code": code, "code_verifier": verifier, "grant_type": "authorization_code", "redirect_uri": REDIRECT}
    if CLIENT_SECRET:
        body["client_secret"] = CLIENT_SECRET
    st, _, raw = _http(urllib.request.Request(TOKEN, data=urllib.parse.urlencode(body).encode(), method="POST"))
    if st != 200:
        raise YtError(f"Google did not take the code ({st}): {_why(raw)}")
    j = json.loads(raw)
    if not j.get("refresh_token"):
        raise YtError("Google gave no lasting token; run the sign-in once more")
    _save_token({"refresh_token": j["refresh_token"], "at": round(time.time())})
    _access.update(token=j.get("access_token"), until=time.time() + int(j.get("expires_in") or 0) - 60)
    ch = channel()
    return ch.get("title") or "(a channel without a name)"


def access() -> str:
    if _access.get("token") and _access.get("until", 0) > time.time():
        return _access["token"]
    rt = _token().get("refresh_token")
    if not rt:
        raise YtError("not signed in to YouTube yet (up yt login)")
    body = {"client_id": CLIENT_ID, "refresh_token": rt, "grant_type": "refresh_token"}
    if CLIENT_SECRET:
        body["client_secret"] = CLIENT_SECRET
    st, _, raw = _http(urllib.request.Request(TOKEN, data=urllib.parse.urlencode(body).encode(), method="POST"))
    if st != 200:
        why = _why(raw)
        if "invalid_grant" in why:
            why += " (the sign-in ran out or was taken back: up yt login; a Google project still in \"Testing\" loses it after 7 days)"
        raise YtError(f"YouTube sign-in failed ({st}): {why}")
    j = json.loads(raw)
    _access.update(token=j["access_token"], until=time.time() + int(j.get("expires_in") or 3000) - 60)
    return _access["token"]


def _call(method: str, url: str, query: dict | None = None, body: dict | None = None, timeout: int = 120) -> dict:
    full = url + ("?" + urllib.parse.urlencode(query) if query else "")
    headers = {"Authorization": "Bearer " + access()}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json; charset=UTF-8"
    st, _, raw = _http(urllib.request.Request(full, data=data, method=method, headers=headers), timeout)
    if st not in (200, 201, 204):
        raise YtError(f"YouTube answered {st}: {_why(raw)}")
    return json.loads(raw) if raw else {}


def channel() -> dict:
    j = _call("GET", API + "/channels", {"part": "snippet,statistics", "mine": "true"})
    it = (j.get("items") or [{}])[0]
    s, n = it.get("snippet") or {}, it.get("statistics") or {}
    return {"id": it.get("id"), "title": s.get("title"), "subscribers": int(n.get("subscriberCount") or 0),
            "views": int(n.get("viewCount") or 0), "videos": int(n.get("videoCount") or 0)}


# ---------- upload ----------
def resource(title: str, description: str, tags: list[str], privacy: str = "private", synthetic: bool = False) -> dict:
    """The video as YouTube wants it: never for kids, science & technology, and the AI label only when asked for
    (the owner's own cloned voice needs none by YouTube's rules; another synthetic voice gets it, to be safe)."""
    return {"snippet": {"title": title[:100], "description": description, "tags": tags, "categoryId": "28",
                        "defaultLanguage": "en", "defaultAudioLanguage": "en"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False, "containsSyntheticMedia": bool(synthetic),
                       "embeddable": True}}


def upload(path: str, res: dict, tries: int = 6) -> str:
    """The file to YouTube in pieces, picked up where it stopped after a break. Returns the video's id."""
    size = os.path.getsize(path)
    st, hd, raw = _http(urllib.request.Request(
        UPLOAD + "/videos?" + urllib.parse.urlencode({"uploadType": "resumable", "part": "snippet,status"}),
        data=json.dumps(res).encode(), method="POST",
        headers={"Authorization": "Bearer " + access(), "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"}))
    loc = {k.lower(): v for k, v in hd.items()}.get("location")
    if st != 200 or not loc:
        raise YtError(f"YouTube did not open the upload ({st}): {_why(raw)}")
    sent, fails = 0, 0
    with open(path, "rb") as f:
        while True:
            f.seek(sent)
            piece = f.read(CHUNK)
            if not piece:
                raise YtError("YouTube asked for more than the file holds; the upload is started again at the next turn")
            end = sent + len(piece) - 1
            st, hd, raw = _http(urllib.request.Request(loc, data=piece, method="PUT", headers={
                "Authorization": "Bearer " + access(), "Content-Type": "video/mp4", "Content-Length": str(len(piece)),
                "Content-Range": f"bytes {sent}-{end}/{size}"}), timeout=600)
            if st in (200, 201):
                return json.loads(raw)["id"]
            if st == 308:
                rng = {k.lower(): v for k, v in hd.items()}.get("range")
                sent = int(rng.rsplit("-", 1)[1]) + 1 if rng else 0
                fails = 0
                continue
            if st in (500, 502, 503, 504) and fails < tries:
                fails += 1
                time.sleep(min(60, 2 ** fails))
                st2, hd2, _ = _http(urllib.request.Request(loc, data=b"", method="PUT", headers={
                    "Authorization": "Bearer " + access(), "Content-Length": "0", "Content-Range": f"bytes */{size}"}))
                rng = {k.lower(): v for k, v in hd2.items()}.get("range") if st2 == 308 else None
                sent = int(rng.rsplit("-", 1)[1]) + 1 if rng else (sent if st2 != 308 else 0)
                continue
            raise YtError(f"the upload stopped ({st}): {_why(raw)}")


def set_thumbnail(video_id: str, jpg: str) -> None:
    with open(jpg, "rb") as f:
        data = f.read()
    st, _, raw = _http(urllib.request.Request(
        UPLOAD + "/thumbnails/set?" + urllib.parse.urlencode({"videoId": video_id, "uploadType": "media"}), data=data, method="POST",
        headers={"Authorization": "Bearer " + access(), "Content-Type": "image/jpeg", "Content-Length": str(len(data))}))
    if st not in (200, 201):
        raise YtError(f"the preview picture was not taken ({st}): {_why(raw)}")


def video(video_id: str) -> dict:
    j = _call("GET", API + "/videos", {"part": "snippet,status,statistics,processingDetails", "id": video_id})
    return (j.get("items") or [{}])[0]


def publish(video_id: str, privacy: str = "public") -> None:
    """The draft made public: only the status changes (a videos.update of the status part must send the whole part)."""
    st = (video(video_id).get("status") or {})
    if not st:
        raise YtError(f"YouTube knows no video {video_id} on this channel")
    st["privacyStatus"] = privacy
    st.pop("publishAt", None)
    keep = {k: st[k] for k in ("privacyStatus", "selfDeclaredMadeForKids", "containsSyntheticMedia", "embeddable", "license",
                               "publicStatsViewable") if k in st}
    _call("PUT", API + "/videos", {"part": "status"}, {"id": video_id, "status": keep})


def set_description(video_id: str, description: str) -> None:
    sn = (video(video_id).get("snippet") or {})
    if not sn:
        raise YtError(f"YouTube knows no video {video_id} on this channel")
    keep = {k: sn[k] for k in ("title", "categoryId", "tags", "defaultLanguage", "defaultAudioLanguage") if k in sn}
    keep["description"] = description
    _call("PUT", API + "/videos", {"part": "snippet"}, {"id": video_id, "snippet": keep})


# ---------- the numbers ----------
def numbers(video_id: str, since: str, until: str) -> dict:
    """Views, minutes watched, the average time and share watched, subscribers won: one video, a span of days."""
    j = _call("GET", ANALYTICS, {"ids": "channel==MINE", "startDate": since, "endDate": until,
                                 "metrics": "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained",
                                 "filters": f"video=={video_id}"})
    row = (j.get("rows") or [[0, 0, 0, 0, 0]])[0]
    return {"views": int(row[0]), "minutes": float(row[1]), "avg_seconds": float(row[2]), "avg_share": float(row[3]) / 100.0,
            "subscribers": int(row[4])}


def retention(video_id: str, since: str, until: str) -> list[tuple[float, float]]:
    """(how far into the video 0..1, the share of viewers still watching there), a hundred points."""
    j = _call("GET", ANALYTICS, {"ids": "channel==MINE", "startDate": since, "endDate": until, "metrics": "audienceWatchRatio",
                                 "dimensions": "elapsedVideoTimeRatio", "filters": f"video=={video_id}", "sort": "elapsedVideoTimeRatio"})
    return [(float(a), float(b)) for a, b in (j.get("rows") or [])]

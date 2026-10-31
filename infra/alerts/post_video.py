"""Post one short video by hand to the channels the alerts service writes to: Telegram (@tauHUDcom) and X (@TauHUDcom).

  docker compose run --rm -v /opt/tau-command-hud:/repo:ro alerts python /repo/infra/alerts/post_video.py \
      /repo/assets/share/<file>.mp4 /repo/assets/share/<file>.json [--dry] [--only telegram|x]

The JSON holds {"telegram": "<HTML caption>", "x": "<post text, no links>"}. X takes the video in chunks
(initialize, append, finalize, then wait while it is processed); Telegram takes the file in one sendVideo.
"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error

sys.path.insert(0, "/app")
import alerts  # noqa: E402  (the keys, OAuth signing and the multipart helper of the running service)

CHUNK = 4 * 2**20


def signed(method: str, url: str, query: dict | None = None) -> str:
    """OAuth 1.0a header; query parameters are part of the signature, a JSON or multipart body is not."""
    k = alerts.X_KEYS
    oauth = {"oauth_consumer_key": k["X_API_KEY"], "oauth_nonce": os.urandom(16).hex(), "oauth_signature_method": "HMAC-SHA1",
             "oauth_timestamp": str(int(time.time())), "oauth_token": k["X_ACCESS_TOKEN"], "oauth_version": "1.0"}
    p = alerts._pct
    params = "&".join(f"{p(a)}={p(b)}" for a, b in sorted({**oauth, **(query or {})}.items()))
    base = "&".join([method, p(url), p(params)])
    key = f"{p(k['X_API_SECRET'])}&{p(k['X_ACCESS_SECRET'])}"
    oauth["oauth_signature"] = alerts.base64.b64encode(alerts.hmac.new(key.encode(), base.encode(), alerts.hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join(f'{p(a)}="{p(b)}"' for a, b in sorted(oauth.items()))


def call(method: str, url: str, body: bytes | None = None, ctype: str | None = None, query: dict | None = None) -> dict:
    full = url + ("?" + urllib.parse.urlencode(query) if query else "")
    headers = {"Authorization": signed(method, url, query)}
    if ctype:
        headers["Content-Type"] = ctype
    req = urllib.request.Request(full, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url}: HTTP {e.code} {e.read()[:400]!r}") from None


def x_video(path: str, text: str) -> str:
    data = open(path, "rb").read()
    up = "https://api.x.com/2/media/upload"
    init = call("POST", up + "/initialize", json.dumps({"media_type": "video/mp4", "total_bytes": len(data),
                                                        "media_category": "tweet_video"}).encode(), "application/json")
    mid = str((init.get("data") or {}).get("id") or "")
    if not mid:
        raise RuntimeError(f"x: no media id in {init}")
    for i in range(0, len(data), CHUNK):
        body, ctype = alerts.multipart({"segment_index": str(i // CHUNK)}, {"media": ("video.mp4", data[i:i + CHUNK], "application/octet-stream")})
        call("POST", f"{up}/{mid}/append", body, ctype)
    info = (call("POST", f"{up}/{mid}/finalize").get("data") or {}).get("processing_info")
    while info and info.get("state") in ("pending", "in_progress"):
        time.sleep(max(1, int(info.get("check_after_secs") or 3)))
        info = (call("GET", up, query={"command": "STATUS", "media_id": mid}).get("data") or {}).get("processing_info")
    if info and info.get("state") == "failed":
        raise RuntimeError(f"x: video processing failed {info}")
    out = call("POST", "https://api.x.com/2/tweets", json.dumps({"text": text, "media": {"media_ids": [mid]}}).encode(), "application/json")
    return str((out.get("data") or {}).get("id"))


def telegram_video(path: str, caption: str) -> None:
    fields = {"chat_id": alerts.TELEGRAM_CHAT, "caption": caption, "parse_mode": "HTML", "supports_streaming": "true",
              "width": "1280", "height": "720"}
    body, ctype = alerts.multipart(fields, {"video": (os.path.basename(path), open(path, "rb").read(), "video/mp4")})
    ok, _, err = alerts.Telegram().call("sendVideo", body, ctype)
    if not ok:
        raise RuntimeError(f"telegram: {err}")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    if only:
        args.remove(only)
    video, texts = args[0], json.load(open(args[1]))
    print(f"video {video}: {os.path.getsize(video) / 2**20:.1f} MB")
    print(f"--- telegram\n{texts['telegram']}\n--- x ({alerts.x_len(texts['x'])} of 280)\n{texts['x']}\n---")
    if alerts.x_len(texts["x"]) > 280:
        print("x: text too long"); return 1
    if "--dry" in sys.argv:
        return 0
    failed = 0
    if only in (None, "telegram"):
        try:
            telegram_video(video, texts["telegram"]); print("telegram: posted")
        except Exception as e:  # noqa: BLE001
            failed = 1; print(e)
    if only in (None, "x"):
        try:
            print("x: posted https://x.com/TauHUDcom/status/" + x_video(video, texts["x"]))
        except Exception as e:  # noqa: BLE001
            failed = 1; print(e)
    return failed


if __name__ == "__main__":
    sys.exit(main())

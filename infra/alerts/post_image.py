"""Post one picture by hand to the channels the alerts service writes to: Telegram (@tauHUDcom) and X (@TauHUDcom).

  docker compose run --rm -v /opt/tau-command-hud:/repo:ro alerts python /repo/infra/alerts/post_image.py \
      /repo/assets/share/<file>.jpg /repo/assets/share/<file>.json [--x-image <file>.jpg] [--dry] [--only telegram|x]

The JSON holds {"telegram": "<HTML caption>", "x": "<post text, no links>"}. Telegram takes the picture in one
sendPhoto (a tall one is fine, the chat shows it whole); X gets the picture named with --x-image when there is one
(a 16:9 copy, so the timeline does not crop it), else the same file.
"""
import json, os, sys

sys.path.insert(0, "/app")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402  (the keys, OAuth signing and the multipart helper of the running service)


def telegram_photo(path: str, caption: str) -> None:
    fields = {"chat_id": alerts.TELEGRAM_CHAT, "caption": caption, "parse_mode": "HTML"}
    body, ctype = alerts.multipart(fields, {"photo": (os.path.basename(path), open(path, "rb").read(), "image/jpeg")})
    ok, _, err = alerts.Telegram().call("sendPhoto", body, ctype)
    if not ok:
        raise RuntimeError(f"telegram: {err}")


def x_photo(path: str, text: str) -> str:
    """The chunked upload that post_video.py uses (initialize, append, finalize): the one-shot picture upload of the
    running service answered HTTP 403 for a hand-posted picture on 3 November 2026, the chunked one is known to work."""
    import post_video
    data = open(path, "rb").read()
    mtype = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    up = "https://api.x.com/2/media/upload"
    init = post_video.call("POST", up + "/initialize", json.dumps({"media_type": mtype, "total_bytes": len(data),
                                                                   "media_category": "tweet_image"}).encode(), "application/json")
    mid = str((init.get("data") or {}).get("id") or "")
    if not mid:
        raise RuntimeError(f"x: no media id in {init}")
    for i in range(0, len(data), post_video.CHUNK):
        body, ctype = alerts.multipart({"segment_index": str(i // post_video.CHUNK)},
                                       {"media": (os.path.basename(path), data[i:i + post_video.CHUNK], "application/octet-stream")})
        post_video.call("POST", f"{up}/{mid}/append", body, ctype)
    post_video.call("POST", f"{up}/{mid}/finalize")
    out = post_video.call("POST", "https://api.x.com/2/tweets", json.dumps({"text": text, "media": {"media_ids": [mid]}}).encode(), "application/json")
    return "posted https://x.com/TauHUDcom/status/" + str((out.get("data") or {}).get("id"))


def main() -> int:
    argv = sys.argv[1:]
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    x_image = argv[argv.index("--x-image") + 1] if "--x-image" in argv else None
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] not in ("--only", "--x-image"))]
    image, texts = args[0], json.load(open(args[1]))
    print(f"image {image}: {os.path.getsize(image) / 2**20:.1f} MB" + (f", x: {x_image}" if x_image else ""))
    print(f"--- telegram\n{texts['telegram']}\n--- x ({alerts.x_len(texts['x'])} of 280)\n{texts['x']}\n---")
    if alerts.x_len(texts["x"]) > 280:
        print("x: text too long"); return 1
    if "--dry" in argv:
        return 0
    failed = 0
    if only in (None, "telegram"):
        try:
            telegram_photo(image, texts["telegram"]); print("telegram: posted")
        except Exception as e:  # noqa: BLE001
            failed = 1; print(e)
    if only in (None, "x"):
        try:
            print("x: " + x_photo(x_image or image, texts["x"]))
        except Exception as e:  # noqa: BLE001
            failed = 1; print(e)
    return failed


if __name__ == "__main__":
    sys.exit(main())

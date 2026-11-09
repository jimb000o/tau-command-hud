#!/usr/bin/env python3
"""Listen to the No Memo crew as the game plays them, before and after a change of the screen filter, next to the ship's
computer. The game filters the crew in the browser (screenVoice in nomemo/game.js); this does the same in ffmpeg on the
server's own clips, so nothing is spent and nothing in the game changes.

  python3 infra/nomemo/crew_listen.py      →  https://node.tauhud.com/rico/nomemo-sfx/try/crew/
"""
import hashlib, html, json, os, shutil, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLIPS = "/opt/sites/rico"
OUT = os.path.join(CLIPS, "nomemo-sfx", "try", "crew")
FF = shutil.which("ffmpeg") or sys.exit("No ffmpeg on the server: apt-get install -y ffmpeg")
TUBE = "highpass=f=380,lowpass=f=3400,aeval=tanh(2.2*val(0))/tanh(2.2)*0.95:c=same"   # the ship's speaking tube in the browser
CHAINS = {
    "before": "highpass=f=340,lowpass=f=3300,aeval=round(tanh(1.8*clip(1.6*val(0)\\,-1\\,1))/tanh(1.8)*28)/28*(0.72+0.3*sin(2*PI*62*t))*0.95:c=same",
    "after": "highpass=f=250,lowpass=f=5200,acrusher=bits=10:mode=log:aa=1:samples=2,aecho=0.8:0.6:7:0.35,alimiter=limit=0.9," + TUBE + ",volume=1.6dB",   # as loud as the browser plays it
}
PICK = [("qm", "r-fee"), ("look", "p-race"), ("bosun", "r-seq")]
NAME = {"qm": "Quartermaster", "look": "Lookout", "bosun": "Bosun"}


def ff(src, dst, chain):
    r = subprocess.run([FF, "-y", "-loglevel", "error", "-i", src, "-af", chain, "-ac", "1", "-b:a", "112k", dst])
    return r.returncode == 0


def main():
    os.makedirs(OUT, exist_ok=True)
    kinds = json.load(open(os.path.join(REPO, "nomemo", "transmissions.json"), encoding="utf-8"))["kinds"]
    rows = []
    ship = os.path.join(CLIPS, "nomemo-sfx", "v-online.mp3")
    if os.path.exists(ship) and ff(ship, os.path.join(OUT, "ship.mp3"), TUBE):
        rows.append("<li><b>Ship computer (as now, the reference)</b><br><audio controls preload=none src='ship.mp3'></audio></li>")
    for who, k in PICK:
        text = kinds[k]["say"]
        src = os.path.join(CLIPS, hashlib.sha1(f"{who}|{text}".encode()).hexdigest()[:16] + ".mp3")
        if not os.path.exists(src):
            print(f"{NAME[who]}: no clip yet ({os.path.basename(src)}), skipped"); continue
        cells = []
        for tag, chain in CHAINS.items():
            if ff(src, os.path.join(OUT, f"{who}-{tag}.mp3"), chain):
                cells.append(f"{tag}<br><audio controls preload=none src='{who}-{tag}.mp3'></audio>")
        rows.append(f"<li><b>{NAME[who]}</b> <small>{html.escape(text[:90])}…</small><br>" + "<br>".join(cells) + "</li>")
        print(f"{NAME[who]}: before and after made")
    page = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'><title>No Memo crew voices</title>"
            "<style>body{background:#050806;color:#b9ffd6;font:15px/1.5 monospace;max-width:720px;margin:24px auto;padding:0 16px}"
            "li{margin:0 0 22px}small{color:#6fa384}audio{width:100%;margin:4px 0}</style>"
            "<h1>No Memo: crew voices through the screen</h1><p>before = live now · after = the new filter, the same as the ship computer's</p><ul>"
            + "".join(rows) + "</ul>")
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)
    print("\nListen: https://node.tauhud.com/rico/nomemo-sfx/try/crew/")


if __name__ == "__main__":
    main()

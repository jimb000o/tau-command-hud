#!/usr/bin/env python3
"""The room, 1999: richer sounds from ElevenLabs, kept where Caddy serves them (/opt/sites/rico/room-sfx,
https://node.tauhud.com/rico/room-sfx/). The room plays these instead of its drawn files (assets/room/sfx/) where they
exist, so nothing here is needed for the room to sound. Same key, retries and credit check as No Memo's sounds.

    python3 infra/room/sfx.py make             every sound in assets/room/sfx/list.json that has an "eleven" prompt
    python3 infra/room/sfx.py make amb-rain    only these (made again)
    python3 infra/room/sfx.py drop amb-rain    back to the drawn one
    python3 infra/room/sfx.py list             what is made, and the credits left
Listen and compare: https://node.tauhud.com/rico/room-sfx/   Plain Python 3, no packages, no restart.
"""
import argparse, importlib.util, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("nomemo_sfx", os.path.join(REPO, "infra", "nomemo", "sfx.py"))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
base.LIST = os.path.join(REPO, "assets", "room", "sfx", "list.json")
base.OUT = os.path.join(base.rico.OUT, "room-sfx")
base.DRAWN = "https://tauhud.com/assets/room/sfx/"
base.listing = lambda: dict(base.json.load(open(base.LIST, encoding="utf-8")), voice=[])
_page = base.page
def page(idx):   # the same compare page, with the room's name on it
    real = base.rico.page
    base.rico.page = lambda rows, title, note: real(rows, "The room, 1999: the sounds", note.replace("infra/nomemo/sfx.py", "infra/room/sfx.py"))
    try:
        _page(idx)
    finally:
        base.rico.page = real
base.page = page


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make"); m.add_argument("names", nargs="*")
    d = sub.add_parser("drop"); d.add_argument("names", nargs="+")
    sub.add_parser("list")
    a = p.parse_args()
    {"make": base.cmd_make, "drop": base.cmd_drop, "list": base.cmd_list}[a.cmd](a)


if __name__ == "__main__":
    main()

"""The cruise announcement picture: made from an island painting and the painted ship, the ship at the layout's anchor,
bow to the west as the game draws it at anchor. Uses the drawn plate as a stand-in painting (the real ones live only on
the server).  Run: python test_cruise_pic.py"""
import json, os, sys, tempfile
from PIL import Image

here = os.path.dirname(os.path.abspath(__file__))
repo = os.path.dirname(os.path.dirname(here))
sys.path.insert(0, here)
import cruise_pic  # noqa: E402

fails = []
with tempfile.TemporaryDirectory() as d:
    Image.open(os.path.join(repo, "infra/rabbit-art/plates/island.jpg")).save(os.path.join(d, "island.jpg"))
    layout = json.load(open(os.path.join(repo, "infra/rabbit-art/plates/island-22.json")))
    json.dump({"scenes": {"island": "island.jpg"}, "layout": layout}, open(os.path.join(d, "index.json"), "w"))
    for name in sorted(f for f in os.listdir(os.path.join(repo, "assets/share")) if f.startswith("cruise-") and f.endswith(".json")):
        t = json.load(open(os.path.join(repo, "assets/share", name)))
        if "http" in t["x"] or len(t["x"]) > 280:
            fails.append(f"{name}: X text has a link or is over 280")
        out = os.path.join(d, name + ".jpg")
        cruise_pic.main(d, os.path.join(repo, "rabbit/art/ships"), os.path.join(repo, "assets/share", name), out)
        im = Image.open(out)
        if im.size != (1600, 900):
            fails.append(f"{name}: picture is {im.size}")
for f in fails:
    print("FAIL " + f)
print("ok   cruise pictures" if not fails else "FAILED")
sys.exit(1 if fails else 0)

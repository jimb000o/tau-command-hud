"""Unit test of the cookie-free visitor numbers (visits.py), no network.

Run: python test_visits.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import visits  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T = [1_793_145_600.0 + 10 * 3600]  # 2026-10-28 10:00 UTC
clock = lambda: T[0]  # noqa: E731
d = tempfile.mkdtemp()
path, key_path = os.path.join(d, "visits.json"), os.path.join(d, "visits.key")
os.environ.pop("VISITS_KEY", None)
v = visits.Visits(path, key_path, clock)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0 Safari/537.36"
H = {"User-Agent": UA}


def hit(query, ip="1.2.3.4", headers=H):
    return v.route("/v", query, ip, headers)


check(len(v.key) == 32 and open(key_path).read().strip() == v.key, "a report key is made once and kept")
check(visits.Visits(path, key_path, clock).key == v.key, "the same key after a restart")
check(hit("p=explorer&r=t.me&l=en&m=sim&w=2560")[0] == 204, "a hit answers 204")
hit("p=explorer&r=%2Fhud&l=en&m=sim&w=2560")
hit("p=stats&r=%2Fexplorer&l=zh&m=live&w=390", ip="5.6.7.8")
hit("p=stats&r=&s=telegram&l=en&m=live&w=1400", ip="9.9.9.9")
t = v.report(1)["days"]["2026-10-28"]
check(t["visitors"] == 3, "three people (address + browser) are three visitors")
check(t["views"] == {"explorer": 2, "stats": 2} and t["uniques"] == {"explorer": 1, "stats": 2}, "views and visitors per page")
check(t["refs"] == {"t.me": 1, "(direct)": 1}, "other sites by host name, own pages are not referrers")
check(t["flows"] == {"hud>explorer": 1, "explorer>stats": 1}, "the previous Tau HUD page becomes a flow")
check(t["sources"] == {"telegram": 1} and t["lang"] == {"en": 2, "zh": 1}, "link tags and language")
check(t["screen"] == {"wide": 1, "phone": 1, "laptop": 1} and t["hours"][10] == 4, "screen class and hour")
hit("p=explorer&e=1")
hit("p=nodes&e=1")
t = v.report(1)["days"]["2026-10-28"]
check(t["engaged"] == {"explorer": 1}, "an engaged ping counts only for a page the visitor opened")
hit("p=explorer&t=95")
hit("p=explorer&t=4")
hit("p=nodes&t=50")
hit("p=explorer&t=abc")
t = v.report(1)["days"]["2026-10-28"]
check(t["time"] == {"explorer": [1, 0, 0, 1, 0, 0]}, "time on a page as steps, only for a page the visitor opened")
hit("p=agorzilla&r=t.me&l=en&m=live")
hit("p=agorzilla&r=tauhud.com&l=en&m=live", ip="5.6.7.8")
hit("p=agorzilla&e=1")
hit("p=agorzilla&t=200")
t = v.report(1)["days"]["2026-10-28"]
a = t["sites"]["agorzilla"]
check(t["visitors"] == 3 and "agorzilla" not in t["views"], "Agorzilla is counted apart: Tau HUD's numbers stay the same")
check(a["visitors"] == 2 and a["uniques"] == {"agorzilla": 2} and a["engaged"] == {"agorzilla": 1}, "Agorzilla's own visitors and stayed views")
check(a["refs"] == {"t.me": 1, "tauhud.com": 1} and a["time"] == {"agorzilla": [0, 0, 0, 0, 1, 0]}, "Agorzilla's referrers and time steps")
pub = v.public()
check(pub["sites"]["agorzilla"]["days"]["2026-10-28"][0] == 2 and pub["days"]["2026-10-28"][0] == 3, "public numbers per site")
v._pub = None
before = json.dumps(v.report(1))
hit("p=hud", headers={"User-Agent": UA, "DNT": "1"})
hit("p=hud", headers={"User-Agent": UA, "Sec-GPC": "1"})
hit("p=hud", headers={"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"})
hit("p=hud", headers={"User-Agent": "Mozilla/5.0 HeadlessChrome/130"})
hit("p=hud", headers={})
hit("p=../etc")
hit("p=")
check(json.dumps(v.report(1)) == before, "Do Not Track, GPC, bots, no browser and odd pages are not counted")
for _ in range(40):
    hit("p=hud", ip="7.7.7.7")
check(v.report(1)["days"]["2026-10-28"]["views"]["hud"] == 20, "one address is rate limited")
v.save(force=True)
raw = open(path).read()
check("1.2.3.4" not in raw and "5.6.7.8" not in raw and UA not in raw, "no address or browser is written to disk")
w = visits.Visits(path, key_path, clock).report(1)
check(w["days"]["2026-10-28"]["visitors"] == 4, "counts survive a restart")
check(v.route("/visits", "key=wrong", "1.1.1.1", H)[0] == 404 and v.route("/visits.json", "", "1.1.1.1", H)[0] == 404, "the report needs the key")
r = v.route("/visits.json", "key=" + v.key, "1.1.1.1", H)
check(r[0] == 200 and "2026-10-28" in json.loads(r[2])["days"], "the report with the key")
r = v.route("/visits", "key=" + v.key, "1.1.1.1", H)
check(r[0] == 200 and r[1].startswith("text/html") and b"Tau HUD" in r[2], "the report page")
r = v.route("/visits/public", "", "1.1.1.1", H)
pub = json.loads(r[2])["days"]["2026-10-28"]
check(r[0] == 200 and pub[0] == 4 and pub[1] == 24 and pub[2] == 1 and pub[3]["stats"] == 2, "public totals without a key")
check("t.me" not in r[2].decode() and "telegram" not in r[2].decode(), "no referrers or tags in public")
hrs = json.loads(r[2])["hours"]["2026-10-28"]
check(pub[6] == {"explorer": [1, 0, 0, 1, 0, 0]}, "time steps per page are public")
check(hrs[0][10] == 4 and hrs[1][10] == 24, "visitors and views per hour for the 24-hour chart")
check(v.route("/other", "", "1.1.1.1", H) is None, "other paths are left to the relay")
T[0] += 86400
hit("p=explorer&r=t.me&l=en&m=sim&w=2560")
t2 = v.report(2)["days"]
check(t2["2026-10-29"]["visitors"] == 1 and t2["2026-10-29"]["uniques"] == {"explorer": 1}, "a new day with a new salt counts the same person again")
v2 = visits.Visits(os.path.join(d, "x.json"), os.path.join(d, "x.key"), clock)
v2.days = {"2025-01-01": {}, "2026-10-29": {}}
v2._roll()
v2.day = -1
v2._roll()
check(list(v2.days) == ["2026-10-29"], "days older than the retention are dropped")

print("\nall ok" if not failed else f"\n{failed} failed")
sys.exit(1 if failed else 0)

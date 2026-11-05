"""A short report of a cruise ship visit, read in the relay container (read only, sends nothing).

  docker compose cp cruise-report.py relay:/tmp/cr.py && docker compose exec -T relay python /tmp/cr.py [visit-id]
  docker compose logs --since 72h alerts | docker compose exec -T relay python /tmp/cr.py --posts

The first prints the visit's logbook in numbers (sent, refused and why, skipped, pace per 10 minutes, how late the
stops went out against the plan, load verdicts, bookings), its summary and the incident reports. The second counts
the alerts bot's posts per day and kind from its log, for a look at how much the channels get.
"""
import collections
import json
import os
import re
import sys
import time

DATA = os.environ.get("CRUISE_DATA", "/data")


def hm(t):
    return time.strftime("%H:%M:%S", time.gmtime(t)) + "Z"


def posts():
    per = collections.defaultdict(collections.Counter)
    for line in sys.stdin:
        m = re.search(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}):\d{2}.*?(posted.*|not posted.*|left out.*)", line)
        if not m:
            continue
        what = re.sub(r"[0-9a-f]{8,}|\d{4}-\d{2}-\d{2}\S*|#?\d+", "#", m.group(3))[:90]
        per[m.group(1)][what] += 1
    for day in sorted(per):
        print(f"== {day}: {sum(per[day].values())} lines")
        for what, n in per[day].most_common():
            print(f"  {n:3d}  {what}")


def report(vid):
    rows = []
    with open(os.path.join(DATA, "cruise-log.jsonl")) as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    visits = sorted({r.get("visit") for r in rows if r.get("visit")})
    print("visits in the logbook:", ", ".join(visits) or "none")
    vid = vid or (visits[-1] if visits else "")
    mine = [r for r in rows if r.get("visit") == vid]
    print("== visit", vid, "entries", len(mine))
    sends = [r for r in mine if r.get("kind") in ("pay", "bill", "book", "cancel")]
    for r in mine:
        if r.get("kind") not in ("pay", "bill", "book", "cancel"):
            r2 = {k: v for k, v in r.items() if k not in ("visit", "ship")}
            print(" ", hm(r["t"]), json.dumps(r2, separators=(",", ":"))[:700])
    c = collections.Counter((r["kind"], {True: "ok", False: "refused", None: "not sent"}[r.get("ok")]) for r in sends)
    print("sends by kind:", dict(sorted(c.items())))
    errs = collections.Counter(re.sub(r"[0-9a-f]{16,}|\d+", "#", str(r.get("err") or r.get("note")))[:160] for r in sends if r.get("ok") is not True)
    for e, n in errs.most_common(12):
        print(f"  {n:4d}x {e}")
    print("verdicts:", dict(collections.Counter(r.get("verdict") for r in sends)))
    if sends:
        t0 = min(r["t"] for r in sends)
        print("first", hm(t0), "last", hm(max(r["t"] for r in sends)), "heights", min(r.get("height") or 0 for r in sends), "-", max(r.get("height") or 0 for r in sends))
        tens = collections.Counter((r["t"] - t0) // 600 for r in sends)
        print("per 10 min:", [tens.get(i, 0) for i in range(max(tens) + 1)])
        mins = collections.Counter((r["t"] - t0) // 60 for r in sends)
        print("busiest minute:", max(mins.values()), "| minutes with a send:", len(mins))
    landed = next((r for r in mine if r.get("kind") == "landed"), None)
    try:
        sys.path.insert(0, "/app")
        import cruise
        if landed:
            s = cruise.SHIPS[landed["ship"]]
            day = time.strftime("%Y-%m-%d", time.gmtime(landed["t"]))
            import datetime as dt
            t0 = cruise.berlin_t(dt.date.fromisoformat(day), s["hour"])
            acts = {a["i"]: a for a in cruise.plan(landed["ship"], t0, set(landed.get("trial") or []), set(a for a in landed.get("allowed") or [] if a != "pay"))}
            lag = sorted(r["t"] - acts[r["i"]]["t"] for r in sends if r.get("i") in acts)
            if lag:
                q = lambda p: round(lag[min(len(lag) - 1, int(p * len(lag)))] / 60, 1)  # noqa: E731
                print(f"late against the plan (min): median {q(.5)} p90 {q(.9)} max {q(1)}; planned {len(acts)}, logged {len(sends)}")
    except Exception as exc:
        print("plan not compared:", repr(exc)[:200])
    try:
        st = json.load(open(os.path.join(DATA, "cruise-state.json")))
        print("tried:", st.get("tried"))
        for v in st.get("visits") or []:
            print("visit summary:", json.dumps(v, separators=(",", ":"))[:600])
    except Exception as exc:
        print("state not read:", repr(exc)[:200])
    try:
        inc = json.load(open(os.path.join(DATA, "cruise-incidents.json")))
        print("incidents:", len(inc))
        for i in inc[-5:]:
            print(" ", hm(i["at"]), i.get("kind"), i.get("visit"), i.get("note"), json.dumps(i.get("chain"))[:300], i.get("last_10_min"), i.get("bookings"))
    except FileNotFoundError:
        print("incidents: none")


if __name__ == "__main__":
    if "--posts" in sys.argv:
        posts()
    else:
        report(next((a for a in sys.argv[1:] if not a.startswith("-")), ""))

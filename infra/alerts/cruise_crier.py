"""The cruise ships' posts without anyone at the server: every week, for every call of the timetable (relay/cruise.py,
Wednesday 16:00 MS Dry Run, Saturday 14:00 Queen Mempool, German time), the blog service (blog.py loop) does by itself
what `up post cruise-… send` and `up cruise` did by hand:

  before the call   ANNOUNCE minutes before the ship is due (CRUISE_ANNOUNCE_MINUTES, 150 = Saturday 11:30 and
                    Wednesday 13:30), and never later than LATEST minutes before it: the announcement picture made
                    from the live island painting with the painted ship at anchor, posted once to Telegram and X
                    (the same picture and helpers as `up post`). The texts: a hand-written file on the site,
                    assets/share/cruise-<ship>.json, when its "date" is that day; else written here from the timetable
                    and the ship's last call as the public logbook counts it (blog.facts_of), so each week's post is
                    new and every number in it comes from the logbook.
  after the call    the visit in numbers (the same facts the blog draft is written from) once to the owner's private
                    Telegram chat (tickerwatch.tell; `up owner` sets it), never to the channel, and kept in
                    /state/cruise-reports/<visit>.json; the blog draft, once written, is told there too, with the
                    command that publishes it.

Nothing is announced while the ships are switched off (CRUISE_ENABLED=0: the relay then names no next call), and
CRUISE_CRIER=false stops these posts and reports. Each call is announced once and each visit reported once
(/state/cruise-crier.json); `up post cruise-queen send` by hand marks that day's call as announced too.

  python cruise_crier.py preview [ship]   the next announcement's texts and picture (/tmp/cruise-<ship>.jpg), posts nothing
  python cruise_crier.py mark <json name> that day's call counts as announced (up.sh after a hand-posted announcement)
"""
from __future__ import annotations

import datetime as dt
import html
import json
import logging
import os
import sys
import time
import urllib.request

sys.path.insert(0, "/app")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog  # noqa: E402  (relay access, the logbook's facts, local time, the owner's chat via tickerwatch)

log = logging.getLogger("cruise-crier")

ON = os.environ.get("CRUISE_CRIER", "true").lower() in ("1", "true", "yes")
ANNOUNCE = int(os.environ.get("CRUISE_ANNOUNCE_MINUTES", "150"))
LATEST = 30            # minutes before the call: she is on the horizon then, "today at 14:00" comes too late
STATE = os.environ.get("CRUISE_CRIER_STATE", os.path.join(os.path.dirname(blog.STATE), "cruise-crier.json"))
REPORTS = os.path.join(os.path.dirname(STATE), "cruise-reports")
LOGBOOK = f"{blog.NODE}/cruise/log"
GAME = f"{blog.SITE}/rabbit/"
UP = 'ssh root@node.tauhud.com "sh /opt/tau-command-hud/infra/up.sh {}"'
FOOT = "White Rabbit Key · community project, not affiliated with IDNI"

# what each ship is, as the timetable has it (relay/cruise.py SHIPS); the words of the posts of 4 and 7 November 2026
SHIPS = {
    "pirates": {
        "name": "Black Sequence", "file": "cruise-pirates", "art": "pirate", "hour": 18, "passengers": 20, "emoji": "🏴",
        "on_x": False,   # a new ship is announced on Telegram only; on X it gets its one post when the blog tells the visit
        "head": "Pirates off White Rabbit Key: Black Sequence drops anchor today at {hh}:00",
        "story": ("From {hz}:30 German time her dark sails are on the horizon, at {hh}:00 she anchors off the island. "
                  "Her 20 pirates stay aboard and trade from their boat: rum at Bar La Ola, supplies at the market. And "
                  "now and then one of them tries a trick: paying more than the wallet holds, sending a payment the chain "
                  "already took a second time, a payment whose time ran out, a payment signed with another pirate's key, a payment "
                  "from another pirate's wallet, one that allows no fee, one past its block deadline, one too big to carry. "
                  "Tau Testnet Alpha is meant to refuse every one, and the logbook shows what it answered."),
        "x": "",
        "why": ["- Tests what the chain must refuse: overspends, replays, expired and forged payments",
                "- Gentle on the testnet: at most 12 a minute, slower when the node is slow"],
    },
    "dryrun": {
        "name": "MS Dry Run", "file": "cruise-dry-run", "art": "expedition", "hour": 16, "passengers": 40, "emoji": "🚢",
        "head": "Ship ahoy: MS Dry Run drops anchor at White Rabbit Key today at {hh}:00",
        "story": ("From {hz}:30 German time you can see her on the horizon, at {hh}:00 she anchors off the island and the "
                  "tenders bring 40 curious passengers to the pier. For 90 minutes they walk the island with notebooks: "
                  "Captain Wren's Old Ship, Hana's school, the dive shop on the reef. Some of them book a dive and change "
                  "their minds again, on purpose: a booking on Tau Testnet Alpha can be taken back, and the lagoon "
                  "practises giving coins back."),
        "x": "MS Dry Run anchors at White Rabbit Key today, {day}, {hh}:00 German time. 40 passengers ashore for 90 minutes: the Old Ship, the school, a dive booked and taken back.",
        "why": ["- Tests rarer features: bookings that can be taken back",
                "- Gentle on the testnet: at most 12 a minute, slower when the node is slow"],
    },
    "queen": {
        "name": "Queen Mempool", "file": "cruise-queen", "art": "liner", "hour": 14, "passengers": 120, "emoji": "🛳",
        "head": "Queen Mempool calls at White Rabbit Key today at {hh}:00",
        "story": ("From {hz}:30 German time she is on the horizon, at {hh}:00 she anchors and the tenders bring 120 "
                  "passengers ashore in waves. For 90 minutes they fill the island: the South Current spa, Bar La Ola, "
                  "song requests on Radio Coco, souvenirs at the market. Some tables settle their evening with one bill "
                  "that pays the bar, the radio and the Coconut Works in a single transaction."),
        "x": "Queen Mempool anchors at White Rabbit Key today, {day}, {hh}:00 German time. 120 passengers for 90 minutes: spa, bar, radio requests, souvenirs.",
        "why": ["- The volume test: hundreds of real transactions in 90 minutes",
                "- Gentle on the testnet: at most 12 a minute, slower when the node is slow"],
    },
}


# ---------- state ----------
def state() -> dict:
    st = blog.read_json(STATE, {})
    for k in ("announced", "reported", "drafts_told"):
        st.setdefault(k, {})
    return st


def save(st: dict) -> None:
    blog.write_json(STATE, st)


def visit_id(t0: float, ship: str) -> str:
    return blog.local(t0).date().isoformat() + "-" + ship


def short_day(t: float) -> str:
    d = blog.local(t)
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b')}"


# ---------- the texts ----------
def last_call(ship: str, before: str, visits: list[str], entries_of, incidents: list[dict]) -> dict | None:
    """The facts of this ship's newest visit in the logbook before `before` (a visit id), or None (first call)."""
    for vid in visits:   # newest first
        if vid.endswith("-" + ship) and vid < before:
            entries = entries_of(vid)
            if entries:
                return blog.facts_of(entries, incidents)
    return None


def last_lines(f: dict | None) -> tuple[str, str, str]:
    """(Telegram sentence, card point, X sentence) about the last call, every number from the logbook's facts."""
    if not f:
        return "This is her first call.", "- Every transaction logged with the node's answer, open to all", ""
    date = (f.get("date") or "").rsplit(" ", 1)[0]   # "Saturday, 7 November"
    if f.get("landed") is False:
        why = str(f.get("why not landed") or "").removeprefix("no landing: ")
        return (f"On her last call, {date}, she did not land" + (f": {why}." if why else "."),
                "- Last call: no landing, she waits for a calm testnet", "")
    tricks = f.get("pirate tricks") or {}
    if tricks.get("tried"):   # the pirates: what the chain refused, never what got through (that waits for the owner)
        tg = (f"On her last call, {date}, the chain refused {tricks.get('refused with the expected answer', 0)} of her pirates' "
              f"{tricks['tried']} tricks with the answer it should give.")
        card = f"- Last call: {tricks.get('refused with the expected answer', 0)} of {tricks['tried']} tricks refused"
        return tg + changed_line(f), card, ""
    old = f.get("refusals logged without any answer from the node (a timeout, counted as refusal by the old rule)") or 0
    una = (f.get("sends our node did not answer in time (not refusals)") or 0) + old
    acc, ref = f.get("accepted in all") or 0, (f.get("refused in all") or 0) - old
    tg = f"On her last call, {date}, our node accepted {acc} of her passengers' transactions" + (f", {ref} were refused" if ref > 0 else " and refused none")
    if una:
        tg += f"; {una} got no answer from our node in time"
    tg += "."
    left = f.get("left early")
    if isinstance(left, dict) and left.get("minutes in port") is not None:
        why = str(left.get("why") or "")
        if old and "refus" in why and ref <= 0:
            why = "her brake took our node's missing answers for refusals, which it no longer does"
        tg += f" She left after {left['minutes in port']} minutes" + (f" ({why})." if why else ".")
    elif f.get("landed"):
        tg += " She stayed the full 90 minutes."
    card = f"- Last call: {acc} accepted" + (f", {ref} refused" if ref > 0 else ", none refused")
    x = f"Last call: {acc} real transactions accepted."
    return tg + changed_line(f), card, x


def changed_line(f: dict) -> str:
    """What the ship changed after its last call, by its own rules, and why ("" when nothing)."""
    ch = [c for c in (f.get("the ship changed for its next call") or []) if not c.get("held")]
    if not ch:
        return ""
    return " Since then she changed " + "; ".join(f"{c['what']} from {c['from']} to {c['to']}, because {c['because']}" for c in ch) + "."


def texts(ship: str, t0: float, last: dict | None) -> dict:
    """The announcement written from the timetable and the last call: Telegram (HTML), X (no link), the picture's card."""
    import alerts
    s = SHIPS[ship]
    hh = blog.local(t0).hour
    fill = {"hh": f"{hh:02d}", "hz": f"{hh - 1:02d}", "day": short_day(t0)}
    tg_last, card_last, x_last = last_lines(last)
    tg = "\n\n".join([
        f"{s['emoji']} <b>{html.escape(s['head'].format(**fill), quote=False)}</b>",
        html.escape(s["story"].format(**fill), quote=False),
        html.escape(tg_last, quote=False),
        "Honest note: the passengers are made up. Their transactions are real, on Tau Testnet Alpha: never more than 12 "
        "a minute, fewer when the node is slow, and she only lands when the testnet is calm. Every transaction goes into "
        f"the logbook: {LOGBOOK}",
        f"Watch from the pier in your browser, sound on: {GAME}",
    ])
    # the honest note stays, the last call goes first when the post is too long
    x = alerts.x_post([s["x"].format(**fill), "The passengers are made up. Their transactions are real, on Tau Testnet Alpha.", x_last],
                      foot="", keep=2) if s.get("on_x", True) else ""
    card = [f"{s['name']} · today {fill['hh']}:00 German time", f"{s['passengers']} made-up passengers, real transactions on Tau Testnet Alpha",
            "## Why it matters", *s["why"], card_last, FOOT]
    return {"ship": s["art"], "ship_scale": 3, "card": card, "telegram": tg, "x": x, "date": blog.local(t0).date().isoformat(), "written": "auto",
            "on_x": s.get("on_x", True)}


def hand_written(ship: str, t0: float) -> dict | None:
    """assets/share/cruise-<ship>.json on the site, when it was written for that very day ("date")."""
    try:
        req = urllib.request.Request(f"{blog.SITE}/assets/share/{SHIPS[ship]['file']}.json",
                                     headers={"Cache-Control": "no-cache", "User-Agent": "tauhud-blog"})
        with urllib.request.urlopen(req, timeout=20) as r:
            t = json.load(r)
    except Exception:  # noqa: BLE001 - Pages unreachable: the written texts go out
        return None
    if isinstance(t, dict) and t.get("date") == blog.local(t0).date().isoformat() and t.get("telegram") and (t.get("x") or not SHIPS[ship].get("on_x", True)):
        return {**t, "written": "by hand", "on_x": SHIPS[ship].get("on_x", True)}
    return None


# ---------- announcing ----------
def due_call(cruise: dict | None, now: float) -> tuple[str, int] | None:
    """(ship, arrival) when the next call's announcement is due now."""
    nxt = (cruise or {}).get("next") or {}
    ship, t0 = nxt.get("ship"), nxt.get("t0")
    if ship not in SHIPS or not t0:
        return None
    return (ship, int(t0)) if t0 - ANNOUNCE * 60 <= now < t0 - LATEST * 60 else None


def picture(t: dict, out: str) -> str:
    import cruise_pic
    tmp = out + ".json"
    blog.write_json(tmp, t)
    cruise_pic.main(blog.ART, blog.SHIPS, tmp, out)
    return out


def post(t: dict, pic: str) -> list[str]:
    """Telegram, then X, as `up post … send` does (post_image.py); returns what each said."""
    import alerts
    import post_image
    said = []
    if alerts.Telegram().enabled():
        try:
            post_image.telegram_photo(pic, t["telegram"]); said.append("telegram: posted")
        except Exception as e:  # noqa: BLE001
            said.append(f"telegram: {e}")
    else:
        said.append("telegram: not set up")
    if t.get("on_x") is False or not t.get("x"):
        said.append("x: not for this ship (its one X post is the blog's)")
    elif alerts.X().enabled():
        try:
            said.append("x: " + post_image.x_photo(pic, t["x"]))
        except Exception as e:  # noqa: BLE001
            said.append(f"x: {e}")
    else:
        said.append("x: not set up")
    return said


def compose(ship: str, t0: int) -> dict:
    vid = visit_id(t0, ship)
    t = hand_written(ship, t0)
    if not t:
        try:
            visits = blog.get("/cruise/log?n=1").get("visits") or []
            inc = blog.get("/cruise/incidents").get("incidents") or []
            last = last_call(ship, vid, visits, lambda v: blog.get(f"/cruise/log?visit={v}&n=2000").get("entries") or [], inc)
        except Exception as e:  # noqa: BLE001 - without the logbook the post says nothing about the last call
            log.warning("last call of %s not read: %s", ship, e)
            last = None
        t = texts(ship, t0, last)
    return t


def announce(now: float, cruise: dict | None, st: dict) -> str | None:
    call = due_call(cruise, now)
    if not call:
        return None
    ship, t0 = call
    vid = visit_id(t0, ship)
    if vid in st["announced"]:
        return None
    t = compose(ship, t0)
    pic = picture(t, f"/tmp/cruise-{ship}.jpg")   # a failure here is tried again in 10 minutes
    st["announced"][vid] = {"at": round(now), "result": "posting"}
    save(st)   # before posting: a crash while posting never posts twice
    said = post(t, pic)
    st["announced"][vid] = {"at": round(now), "texts": t.get("written"), "result": said}
    save(st)
    log.info("announced %s (%s texts): %s", vid, t.get("written"), "; ".join(said))
    return vid


# ---------- the report after the visit ----------
def report_text(f: dict) -> str:
    lines = [f"{f.get('ship')}, {f.get('date')}: the visit is over"] + ["• " + n for n in blog.numbers_of(f)]
    if isinstance(f.get("landed"), dict):
        lines.append(f"• planned {f['landed'].get('transactions planned')}, skipped {f.get('stops skipped', 0)}, first send {f.get('first send')}, last {f.get('last send')}")
    a = f.get("our node's answer time to a send, seconds")
    if a:
        lines.append(f"• our node's answer time: median {a['median']} s, slowest tenth from {a['slowest tenth from']} s, slowest {a['slowest']} s")
    if f.get("sends per 10 minutes"):
        lines.append("• sends per 10 minutes: " + " ".join(str(x) for x in f["sends per 10 minutes"]))
    if f.get("testnet load at each send"):
        lines.append("• testnet load at the sends: " + ", ".join(f"{k} {v}" for k, v in f["testnet load at each send"].items()))
    for k, v in (f.get("refusal answers") or {}).items():
        lines.append(f"• refused {v}x: {k}")
    tr = f.get("pirate tricks") or {}
    if tr.get("tried"):
        lines.append(f"• pirate tricks: {tr['tried']} tried, {tr.get('refused with the expected answer', 0)} refused with the expected answer"
                     + (f", {tr['refused with another answer']} with another answer" if tr.get("refused with another answer") else "")
                     + (f", {tr['held back']} HELD BACK (see the separate message)" if tr.get("held back") else ""))
    for c in f.get("the ship changed for its next call") or []:
        lines.append("• learned: " + ("a pirate trick, held back" if c.get("held") else f"{c['what']} {c['from']} → {c['to']} ({c['because']})"))
    lines += [f"Logbook: {LOGBOOK}?visit={f.get('visit')}",
              "The blog draft follows within 3 hours, I tell you here.",
              "All numbers: " + UP.format(f"cruise {f.get('visit')}")]
    return "\n".join(lines)


def tell(text: str) -> tuple[bool, str]:
    import tickerwatch
    return tickerwatch.tell(text[:4000])


def report(now: float, st: dict) -> str | None:
    """Once per visit, right after it is over: its facts into /state/cruise-reports and to the owner's chat."""
    visits = (blog.get("/cruise/log?n=1").get("visits") or [])[:3]
    for vid in visits:
        if vid in st["reported"]:
            continue
        entries = blog.get(f"/cruise/log?visit={vid}&n=2000").get("entries") or []
        over = next((e for e in entries if e.get("kind") == "visit over"), None)
        if not over:
            continue
        if now - over["t"] > 2 * 86400:   # older visits (the first run after this was added): kept, not told
            st["reported"][vid] = {"at": round(now), "told": "too old, not told"}
            continue
        f = blog.facts_of(entries, blog.get("/cruise/incidents").get("incidents") or [])
        blog.write_json(os.path.join(REPORTS, vid + ".json"), f)
        ok, err = tell(report_text(f))
        st["reported"][vid] = {"at": round(now), "told": "sent to you on Telegram" if ok else f"not sent ({err})"}
        save(st)
        log.info("report %s: %s", vid, st["reported"][vid]["told"])
        return vid
    save(st)
    return None


# ---------- a finding held back: only to the owner, never posted ----------
IDNI_REPO = "IDNI/tau-testnet"


def held_text(e: dict, inc: dict | None) -> str:
    """The private message about a pirate trick the chain took, with a ready issue for IDNI."""
    import urllib.parse
    what = e.get("what") or e.get("trick")
    tx = json.dumps(e.get("tx") or {}, indent=1)[:2500]
    title = f"Testnet accepted a transaction it should refuse: a payment that {what}"
    body = "\n".join([
        "While testing Tau Testnet Alpha with simulated wallets (a community dashboard, not affiliated with IDNI), our node accepted a",
        f"transaction it should have refused: the sender {what}. We expected one of: {', '.join(e.get('expect') or [])}.",
        "", f"- when: {blog.day(e['t'])} {blog.clock(e['t'])} German time, chain height about {e.get('height', '?')}",
        f"- tx hash: {e.get('hash') or '?'}", "", "Signed transaction as sent:", "```json", tx, "```",
        "", "We have not published this. Happy to help reproduce it."])
    url = f"https://github.com/{IDNI_REPO}/issues/new?" + urllib.parse.urlencode({"title": title, "body": body})
    return "\n".join([
        f"⚠ A pirate trick got through on {e.get('visit')}: the pirate {what}, and the chain took it (tx {str(e.get('hash') or '?')[:16]}…).",
        "Nothing about it is public: the logbook shows only 'held back', no post goes out, the blog waits.",
        "Tell IDNI first. Their issues are public; a private note in the Tau Telegram may be the better first step.",
        f"Ready issue (public once you submit it):\n{url}",
        f"Private advisory instead: https://github.com/{IDNI_REPO}/security/advisories/new",
        "When it may be public, show it in the logbook and let the blog write the visit:",
        UP.format(f"cruise release {e.get('visit')}")])


def held(now: float, st: dict) -> int:
    """Each finding once to the owner's chat (read from inside the server: /cruise/held answers nobody outside)."""
    h = blog.get("/cruise/held")
    told = st.setdefault("held_told", {})
    n = 0
    for e in h.get("entries") or []:
        key = f"{e.get('visit')}#{e.get('i')}"
        if key in told or e.get("visit") in (h.get("released") or []):
            continue
        ok, err = tell(held_text(e, None))
        told[key] = {"at": round(now), "told": "sent" if ok else f"not sent ({err})"}
        save(st)
        n += 1
    return n


def tell_draft(did: str, url: str) -> None:
    """A new blog draft, to the owner: where to read it and the one line that publishes it."""
    st = state()
    if did in st["drafts_told"]:
        return
    hours = float(os.environ.get("BLOG_AUTO_PUBLISH_HOURS", "0") or 0)
    msg = f"Blog draft ready: {did}\nRead it: {url}\n" + (
        f"It goes on the blog by itself in {hours:g} hours (with one post on Telegram and X) if its numbers and wording check out.\n"
        "If it is not good, tell a thread before then. Publish it now instead:\n" if hours > 0 else
        "Publish it (blog + one post on Telegram and X):\n") + UP.format(f"blog publish {did}")
    ok, err = tell(msg)
    st["drafts_told"][did] = {"at": round(time.time()), "told": "sent" if ok else f"not sent ({err})"}
    save(st)


def step(now: float | None = None) -> None:
    """One round of the blog loop: the announcement when due, the report of a visit that just ended."""
    if not ON:
        return
    now = now or time.time()
    st = state()
    try:
        cruise = blog.get("/cruise")
    except Exception as e:  # noqa: BLE001 - the relay may be restarting
        log.warning("cruise not read: %s", e)
        return
    try:
        announce(now, cruise, st)
    except Exception as e:  # noqa: BLE001 - marked as tried: never a second post of the same call
        log.warning("announcement: %s", e)
    try:
        report(now, st)
    except Exception as e:  # noqa: BLE001
        log.warning("report: %s", e)
    try:
        held(now, st)
    except Exception as e:  # noqa: BLE001
        log.warning("held findings: %s", e)


def status_lines(now: float | None = None) -> list[str]:
    """For the `up` block: the next announcement and the last report."""
    now = now or time.time()
    if not ON:
        return ["cruise:  automatic posts and reports off (CRUISE_CRIER=false)"]
    st = state()
    out = []
    try:
        nxt = (blog.get("/cruise").get("next") or {})
    except Exception:  # noqa: BLE001
        nxt = {}
    if nxt.get("ship") in SHIPS:
        at = nxt["t0"] - ANNOUNCE * 60
        out.append(f"cruise:  {nxt.get('name')} {blog.day(nxt['t0'])} {blog.clock(nxt['t0'])}: announced by itself at {blog.clock(at)}"
                   + (" (done)" if visit_id(nxt["t0"], nxt["ship"]) in st["announced"] else ""))
    else:
        out.append("cruise:  no call ahead (ships switched off?), nothing to announce")
    if st["reported"]:
        vid = max(st["reported"])
        out.append(f"         last report {vid}: {st['reported'][vid].get('told')}")
    return out


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if argv[:1] == ["mark"] and len(argv) > 1:
        ship = next((k for k, s in SHIPS.items() if s["file"] == argv[1]), None)
        if not ship:
            return 0
        st = state()
        vid = dt.datetime.now(blog.TZ or dt.timezone.utc).date().isoformat() + "-" + ship
        st["announced"].setdefault(vid, {"at": round(time.time()), "result": "posted by hand (up post)"})
        save(st)
        print(f"cruise:  {vid} counts as announced (no automatic post today)")
        return 0
    if argv[:1] == ["preview"]:
        cruise = blog.get("/cruise")
        nxt = cruise.get("next") or {}
        ship = argv[1] if len(argv) > 1 else nxt.get("ship")
        if ship not in SHIPS:
            print("no call ahead"); return 1
        t0 = nxt["t0"] if nxt.get("ship") == ship else None
        if not t0:
            print(f"{ship} is not the next call"); return 1
        t = compose(ship, t0)
        print(f"--- {t.get('written')} texts for {visit_id(t0, ship)}, posted by itself at {blog.clock(t0 - ANNOUNCE * 60)}")
        print(f"--- telegram\n{t['telegram']}\n--- x\n{t['x']}\n--- card\n" + "\n".join(t["card"]))
        print("picture: " + picture(t, f"/tmp/cruise-{ship}.jpg"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

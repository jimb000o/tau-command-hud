"""The hack of the week's posts without anyone at the server (relay/hackweek.py runs it, Thursdays 11:00 German time).
The blog service's loop (blog.py) calls step() every 10 minutes:

  held / missed   once, right after the run: a picture (the friend's and the poisoner's address, alike when shortened,
                  and what became of the 50 test AGRS with and without the take-back window) to Telegram and X. Every
                  post says what the setting does NOT protect against. "missed" is told as plainly as "held".
  finding         never posted: the chain did something it must not. The owner gets a private Telegram message with a
                  ready, pre-filled issue for IDNI; the public sees "held back" until `up hack release <run>`.
  skipped /       no post; one private line to the owner (why).
  incomplete

HACK_CRIER=false stops posts and private notes. Each run is handled once (/state/hack-crier.json).

  python hack_crier.py preview [run]   the texts and picture (/tmp/hack.jpg) of the newest finished run, posts nothing
  python hack_crier.py status          one line for the `up` block
"""
from __future__ import annotations

import html
import json
import logging
import os
import sys
import time
import urllib.parse

sys.path.insert(0, "/app")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog  # noqa: E402  (relay access, local time, the owner's chat via tickerwatch)

log = logging.getLogger("hack-crier")

ON = os.environ.get("HACK_CRIER", "true").lower() in ("1", "true", "yes")
STATE = os.environ.get("HACK_CRIER_STATE", os.path.join(os.path.dirname(blog.STATE), "hack-crier.json"))
PAGE = f"{blog.NODE}/hack"
UP = 'ssh root@node.tauhud.com "sh /opt/tau-command-hud/infra/up.sh {}"'
IDNI_REPO = "IDNI/tau-testnet"
FOOT = "simulated wallets, real test transactions · community project, not affiliated with IDNI"


def state() -> dict:
    st = blog.read_json(STATE, {})
    st.setdefault("done", {})
    return st


def save(st: dict) -> None:
    blog.write_json(STATE, st)


def minutes(a, b) -> int | None:
    try:
        return max(1, round((int(b) - int(a)) / 60))
    except (TypeError, ValueError):
        return None


# ---------- the texts ----------
def texts(run: dict, snap: dict) -> dict:
    """Telegram caption (HTML, under 1024), X (no link) and the picture's lines, every fact from the run."""
    import alerts
    h = (snap.get("hacks") or {}).get(run["hack"]) or {}
    w = snap.get("wallets") or {}
    win = snap.get("window_minutes") or 30
    st = run.get("steps") or {}
    look = (w.get("friend") or {}).get("short") or "?"
    took = minutes((st.get("slip") or {}).get("t"), (st.get("catch") or {}).get("t"))
    held = run["result"] == "held"
    imp = st.get("impostor") or {}
    twin_ok = (run.get("outcome") or {}).get("twin") == "confirmed"
    with_line = (f"With the {win}-minute take-back window: the 50 sat in escrow and came back"
                 + (f" after {took} minutes." if took else ".")) if held else \
        (f"With the {win}-minute take-back window: this time our take-back was not in a block before the release, so the "
         "poisoner got the 50 anyway. That is on our timing; the next run takes back earlier.")
    without = "Without it: the 50 went straight to the poisoner." if twin_ok else "Without it: a plain payment, nothing to take back."
    imp_line = ("The poisoner also tried to take that payment back for itself: the chain refused, only the sender may."
                if imp.get("right") else "")
    parts = [
        f"🧪 <b>Hack of the week, replayed on Tau Testnet Alpha: {html.escape(h.get('name', run['hack']).lower(), quote=False)}</b>",
        html.escape(h.get("news", ""), quote=False),
        "How it works: " + html.escape(h.get("how", ""), quote=False),
        html.escape(f"Our replay: a lookalike of an address our test wallets pay weekly ({look}, same first 6 and last 4 "
                    "characters) sent them 1 test AGRS; two of them then paid it 50 by mistake.", quote=False),
        "• " + html.escape(with_line, quote=False) + ("\n• " + html.escape(without, quote=False)),
        html.escape(imp_line, quote=False),
        "What the window does NOT protect: " + html.escape(" ".join(h.get("not") or []), quote=False),
        f"Simulated wallets, real test transactions: {PAGE}",
    ]
    parts = [x for x in parts if x]
    for drop in ("How it works: ", imp_line):   # a photo caption's limit is 1024: these go first, the news stays
        if len("\n\n".join(parts)) <= 1024:
            break
        parts = [x for x in parts if not (drop and x.startswith(html.escape(drop, quote=False)[:30]))]
    tg = "\n\n".join(parts)[:1024]
    x = alerts.x_post([
        f"Hack of the week, replayed on Tau Testnet Alpha: {h.get('name', run['hack']).lower()}.",
        "A lookalike address, 50 test AGRS sent to it by mistake. "
        + (f"With a {win}-minute take-back window: back. Without: gone." if held else
           f"With a {win}-minute take-back window: our take-back came too late this time. Without: gone."),
        "It only helps if you notice in time.",
    ], foot="", keep=2)
    card = {"title": f"Hack of the week: {h.get('name', run['hack']).lower()}", "look": look,
            "friend": (w.get("friend") or {}).get("address", ""), "poisoner": (w.get("poisoner") or {}).get("address", ""),
            "with": f"{win}-min take-back window: 50 back" if held else f"{win}-min take-back window: too late this time",
            "without": "No window: 50 gone" if twin_ok else "No window: nothing to take back",
            "held": held, "not": (h.get("not") or [""])[0]}
    return {"telegram": tg, "x": x, "card": card}


def picture(card: dict, out: str) -> str:
    """1600x900 in the site's look: the two addresses (alike when shortened), then the two outcomes side by side."""
    import blog_pics as bp
    im, d = bp.frame(card["title"], "Replayed with our own test wallets on Tau Testnet Alpha")
    f_lab, f_mono, f_big = bp.font(26, 500), bp.font(30, 500, mono=True), bp.font(44, 700)
    y = 230
    for who, addr in (("Your friend", card["friend"]), ("The poisoner", card["poisoner"])):
        d.text((80, y), who, font=f_lab, fill=bp.DIM)
        s = f"{addr[:6]}…{addr[-4:]}"
        d.text((360, y - 8), s, font=bp.font(44, 700, mono=True), fill=bp.TEXT)
        d.text((80, y + 44), f"{addr[:30]}…{addr[-14:]}", font=f_mono, fill=(92, 92, 100))
        y += 120
    d.text((80, y), "Shortened, the two look the same. That is the whole trick.", font=bp.font(28, 600), fill=bp.TEXT)
    y += 80
    for i, (txt, good) in enumerate(((card["with"], card["held"]), (card["without"], False))):
        x0 = 80 + i * 740
        d.rounded_rectangle([x0, y, x0 + 700, y + 130], radius=14, fill=bp.DECK, outline=bp.OK if good else bp.LINE, width=3)
        lines = bp.wrap(d, txt, f_big, 640)
        for j, line in enumerate(lines[:2]):
            d.text((x0 + 30, y + 18 + j * 54), line, font=f_big if len(lines) == 1 else bp.font(36, 700), fill=bp.OK if good else bp.TEXT)
    lim = card["not"][:1].lower() + card["not"][1:]
    d.text((80, y + 160), "Limit: " + lim, font=bp.font(24, 400), fill=bp.DIM)
    d.rectangle([0, bp.H - 90, bp.W, bp.H], fill=bp.BG)   # the blog's own footer, replaced by this post's
    d.text((80, bp.H - 64), FOOT, font=bp.font(22, 400, mono=True), fill=bp.DIM)
    im.save(out, "JPEG", quality=90)
    return out


def post(t: dict, pic: str) -> list[str]:
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
    if alerts.X().enabled():
        try:
            said.append("x: " + post_image.x_photo(pic, t["x"]))
        except Exception as e:  # noqa: BLE001
            said.append(f"x: {e}")
    else:
        said.append("x: not set up")
    return said


def tell(text: str) -> tuple[bool, str]:
    import tickerwatch
    return tickerwatch.tell(text[:4000])


# ---------- a finding: only to the owner ----------
def finding_text(run: dict, snap_held: dict) -> str:
    f = (run.get("findings") or [{}])[0]
    what = f.get("what") or "the chain did something it must not"
    tx = json.dumps(f.get("tx") or (run.get("steps") or {}).get(f.get("step") or "", {}).get("tx") or {}, indent=1)[:2000]
    title = f"Testnet: {what}"
    body = "\n".join([
        "While replaying an address poisoning attack on Tau Testnet Alpha with our own simulated wallets (a community dashboard,",
        f"not affiliated with IDNI), we saw this: {what}.", "",
        f"- when: {blog.day(f.get('t') or run.get('t0') or time.time())} {blog.clock(f.get('t') or run.get('t0') or time.time())} German time",
        f"- details: {json.dumps({k: v for k, v in f.items() if k not in ('tx', 'answer', 'what')})[:600]}",
        f"- node answer: {json.dumps(f.get('answer'))[:400]}" if f.get("answer") else "",
        "", "Transaction as sent:", "```json", tx, "```", "", "We have not published this. Happy to help reproduce it."])
    url = f"https://github.com/{IDNI_REPO}/issues/new?" + urllib.parse.urlencode({"title": title, "body": body})
    return "\n".join([
        f"⚠ Hack of the week {run['id']}: {what}.",
        "Nothing about it is public: /hack shows only 'held back', no post goes out.",
        "Tell IDNI first. Their issues are public; a private note in the Tau Telegram may be the better first step.",
        f"Ready issue (public once you submit it):\n{url}",
        f"Private advisory instead: https://github.com/{IDNI_REPO}/security/advisories/new",
        "When it may be public:", UP.format(f"hack release {run['id']}")])


# ---------- the loop ----------
def handle(run: dict, snap: dict, st: dict, now: float) -> str | None:
    rid = run["id"]
    if rid in st["done"] or run.get("status") != "done":
        return None
    res = run.get("result")
    if now - (run.get("settled") or run.get("t0") or now) > 2 * 86400:   # older runs (first start): kept, not told
        st["done"][rid] = {"at": round(now), "result": res, "said": "too old, not told"}
        save(st)
        return None
    if res in ("held", "missed"):
        if blog.gap_left(now):   # the channels posted lately: the post waits for the room (alerts.POST_GAP_MINUTES)
            return None
        t = texts(run, snap)
        pic = picture(t["card"], "/tmp/hack.jpg")
        st["done"][rid] = {"at": round(now), "result": res, "said": "posting"}
        save(st)   # before posting: a crash never posts twice
        said = post(t, pic)
        ok, err = tell(f"Hack of the week {rid}: {res} ({run.get('why')}). Posted: " + "; ".join(said))
        st["done"][rid] = {"at": round(now), "result": res, "said": said}
    elif res == "held back" or run.get("held"):
        return None   # the finding is told from /hack/held
    else:
        ok, err = tell(f"Hack of the week {rid}: {res}, nothing posted. Why: {run.get('why')}\nAll steps: {UP.format('hack')}")
        st["done"][rid] = {"at": round(now), "result": res, "said": "told you" if ok else f"not told ({err})"}
    save(st)
    log.info("hack %s: %s", rid, st["done"][rid])
    return rid


def step(now: float | None = None) -> None:
    if not ON:
        return
    now = now or time.time()
    st = state()
    try:
        snap = blog.get("/hack")
    except Exception as e:  # noqa: BLE001 - the relay may be restarting
        log.warning("hack not read: %s", e)
        return
    for run in (snap.get("runs") or [])[:3]:
        try:
            handle(run, snap, st, now)
        except Exception as e:  # noqa: BLE001 - marked as tried: never a second post of the same run
            log.warning("hack %s: %s", run.get("id"), e)
    try:
        h = blog.get("/hack/held")
        told = st.setdefault("findings_told", {})
        for run in h.get("runs") or []:
            if run["id"] in told or run["id"] in (h.get("released") or []):
                continue
            ok, err = tell(finding_text(run, h))
            told[run["id"]] = {"at": round(now), "told": "sent" if ok else f"not sent ({err})"}
            st["done"].setdefault(run["id"], {"at": round(now), "result": "finding", "said": "held back, told privately"})
            save(st)
    except Exception as e:  # noqa: BLE001
        log.warning("hack findings: %s", e)


def status_lines() -> list[str]:
    if not ON:
        return ["hack:    posts off (HACK_CRIER=false)"]
    try:
        s = blog.get("/hack")
    except Exception as e:  # noqa: BLE001
        return [f"hack:    not read ({e})"]
    if not s.get("enabled"):
        return ["hack:    switched off (HACK_ENABLED=0)"]
    n = s.get("next") or {}
    out = [f"hack:    next replay {blog.day(n['t0'])} {blog.clock(n['t0'])}: {n.get('hack')}"
           + (f" (skipped: {n['ship_near']} calls near)" if n.get("ship_near") else "")
           + ("" if s.get("ready") else ", wallets " + ("being made (a few minutes)" if s.get("making_wallets") else "NOT ready"))]
    r = (s.get("runs") or [None])[0]
    if r:
        out.append(f"         last {r['id']}: {r.get('result')}" + (f" ({r.get('why')})" if r.get("why") else ""))
    return out


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if argv[:1] == ["status"]:
        print("\n".join(status_lines()))
        return 0
    if argv[:1] == ["preview"]:
        snap = blog.get("/hack")
        runs = [r for r in snap.get("runs") or [] if r.get("result") in ("held", "missed") and (len(argv) < 2 or r["id"] == argv[1])]
        if not runs:
            print("no finished replay to show yet")
            return 1
        t = texts(runs[0], snap)
        print(f"--- telegram ({len(t['telegram'])} characters)\n{t['telegram']}\n--- x\n{t['x']}")
        print("picture: " + picture(t["card"], "/tmp/hack.jpg"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

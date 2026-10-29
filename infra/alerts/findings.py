"""Findings: unusual things our read node sees on the real Tau testnet, posted once per incident.

alerts.py reads the relay every FINDINGS_POLL_SECONDS (/health-score, /peers, /status, now and then /stats) and hands
the answers to observe(), together with the blocks it holds. Each detector below says whether its condition is on,
off, or cannot be told right now; the engine turns that into incidents:

  start    the condition held for the detector's `hold`: one post (why, what, facts; the IDNI issue when one is known)
  end      it stayed clear for `end_hold`: one recovery post, only for an incident whose start was posted
  summary  a busy stretch (see below), in one post afterwards

No repeats: an incident is posted once however long it lasts, and the same detector stays quiet for its `cooldown`
after one ended. The first run is silent: what is already going on then is how things are, not news.

Spam guard: when FINDINGS_STORM_AT starts come within FINDINGS_STORM_HOURS (someone testing hard, which is what a
testnet is for), the bot stops posting them one by one. It keeps a list and posts it once, when things have been calm
for FINDINGS_CALM_SECONDS, or at FINDINGS_SUMMARY_HOUR UTC if it is still going on. Starts held back by a cooldown join
that list too (posted only once three or more have gathered). Recoveries of incidents that were posted still go out.

Wording: we say what our node sees. Without peers, "no new blocks reach us" is not "the testnet stopped"; the recovery
post then says which one it was, from the timestamps of the blocks caught up afterwards.
"""
from __future__ import annotations

import html
import os
import re
import time
from datetime import datetime, timezone

REAL_LINE = "⛓ <b>TESTNET ALPHA · live chain</b>"
SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
FINDINGS_ON = os.environ.get("FINDINGS", "true").lower() in ("1", "true", "yes")
FINDINGS_EVERY = float(os.environ.get("FINDINGS_POLL_SECONDS", 60))
X_DAILY = int(os.environ.get("FINDINGS_X_DAILY_CAP", 3))       # findings on X a day, inside X_DAILY_CAP
STORM_AT = int(os.environ.get("FINDINGS_STORM_AT", 4))          # this many starts…
STORM_HOURS = float(os.environ.get("FINDINGS_STORM_HOURS", 6))  # …within this many hours: collect instead of posting
CALM = float(os.environ.get("FINDINGS_CALM_SECONDS", 2 * 3600))
SUMMARY_HOUR = int(os.environ.get("FINDINGS_SUMMARY_HOUR", 21))  # UTC
STALL_MIN = float(os.environ.get("FINDINGS_STALL_SECONDS", 1200))
VOTES_BURST = int(os.environ.get("FINDINGS_VOTES_BURST", 5))  # the same proposal this often within an hour
OUTBOX_MAX_AGE = 2 * 3600
ISSUE = "https://github.com/IDNI/tau-testnet/issues/"
FOOT = "🔎 Seen by the Tau HUD read node. We share findings because they help the testnet."

# hold / end_hold / cooldown in seconds; x: the start may go to X (a function of the facts, or a bool);
# recovery: the end gets a post of its own. Events (reorg) have no duration and no end.
DETECTORS = {
    "peers":  {"hold": 600, "end_hold": 120, "cooldown": 7200, "x": lambda f: f["connected"] == 0, "recovery": True,
               "label": "our node without the IDNI bootnode"},
    "stall":  {"hold": 0, "end_hold": 0, "cooldown": 7200, "x": True, "recovery": True,
               "label": "no new block for 20+ minutes"},
    "ghost":  {"hold": 900, "end_hold": 1800, "cooldown": 86400, "x": False, "recovery": False,
               "label": "ghost transactions (IDNI #81)"},
    "reorg":  {"event": True, "cooldown": 1800, "x": True, "label": "blocks replaced (reorg)"},
    "slow":   {"hold": 900, "end_hold": 900, "cooldown": 10800, "x": False, "recovery": True,
               "label": "blocks much slower than usual"},
    "drops":  {"hold": 0, "end_hold": 3600, "cooldown": 21600, "x": False, "recovery": False,
               "label": "many transactions dropped"},
    "votes":  {"hold": 0, "end_hold": 3600, "cooldown": 21600, "x": False, "recovery": False,
               "label": "the same proposal again and again"},
    "behind": {"hold": 900, "end_hold": 300, "cooldown": 10800, "x": False, "recovery": True,
               "label": "our node behind the network"},
}


def plural(n: int, w: str, ws: str | None = None) -> str:
    return f"{int(n):,} {w if n == 1 else (ws or w + 's')}"


def fmt_dur(s: float) -> str:
    s = max(0, round(s))
    if s < 90:
        return plural(s, "second")
    if s < 5400:
        return plural(round(s / 60), "minute")
    h, m = divmod(round(s / 60), 60)
    return f"{h} h {m} min" if m else plural(h, "hour")


def hm(t: float, now: float | None = None) -> str:
    d = datetime.fromtimestamp(t, timezone.utc)
    same = now is None or d.date() == datetime.fromtimestamp(now, timezone.utc).date()
    return d.strftime("%H:%M UTC") if same else d.strftime("%-d %b %H:%M UTC")


def block_ts(b: dict) -> int | None:
    try:
        return int((b.get("header") or {}).get("timestamp")) or None
    except (TypeError, ValueError):
        return None


def factor(h: dict, key: str) -> dict:
    return next((f for f in h.get("factors") or [] if f.get("key") == key), {})


# ---------------- detectors: facts (on), False (clear), missing (cannot tell now) ----------------
def conditions(snap: dict, now: float, st: dict) -> dict | None:
    h = snap.get("health")
    if not h or factor(h, "node").get("value") != "yes":
        return None  # our node or the relay does not answer: the health alarm speaks, findings keep their state
    out: dict = {}
    exp = float(h.get("expected_block_seconds") or 60)
    age = factor(h, "last_block").get("value")
    age = float(age) if isinstance(age, (int, float)) else None
    last_ts = now - age if age is not None else None
    blocks = snap.get("blocks") or {}
    head = max(blocks) if blocks else None
    flowing = age is not None and age < max(600, 3 * exp)

    peers = snap.get("peers")
    lonely = None
    if peers is not None:
        rows = peers.get("peers") or []
        boot = next((r for r in rows if r.get("id") == peers.get("bootnode") or r.get("label")), None)
        connected = int((peers.get("counts") or {}).get("connected") or 0)
        boot_ok = bool(boot and boot.get("connected"))
        lonely = connected == 0
        if not boot_ok or lonely:
            out["peers"] = {"connected": connected, "boot": boot_ok, "last_ts": last_ts, "head": head}
        elif flowing:
            out["peers"] = False
        # connected again, blocks not caught up yet: still on, nothing changes

    stall_at = max(STALL_MIN, 6 * exp)
    if age is not None:
        if age >= stall_at and lonely is False:
            out["stall"] = {"last_ts": last_ts, "head": head, "exp": exp}
        elif age < stall_at:
            out["stall"] = False

    mem = factor(h, "mempool").get("value")
    if isinstance(mem, dict):
        sealed = int(mem.get("sealed") or 0)
        if sealed >= 5:
            out["ghost"] = {"sealed": sealed, "waiting": int(mem.get("waiting") or 0)}
        elif sealed <= 1:
            out["ghost"] = False

    pace = factor(h, "pace").get("value")
    if isinstance(pace, (int, float)) and flowing and lonely is not True:
        want = 3600 / exp
        if pace / want < 0.5:
            out["slow"] = {"made": int(pace), "want": round(want), "exp": exp}
        elif pace / want >= 0.75:
            out["slow"] = False

    sync = str(factor(h, "sync").get("value") or "")
    m = re.match(r"(\d+) blocks behind", sync)
    if lonely is not True and (m or sync == "in sync"):
        lag = int(m.group(1)) if m else 0
        if lag >= 30:
            out["behind"] = {"lag": lag}
        elif lag <= 3:
            out["behind"] = False

    stats = snap.get("stats")
    if stats is not None:
        left = [d.get("left") or 0 for d in stats.get("dropped") or []]
        hour = sum(1 for t in left if t >= now - 3600)
        usual = sum(1 for t in left if now - 86400 <= t < now - 3600) / 23
        if hour >= max(10, 4 * usual):
            out["drops"] = {"hour": hour, "usual": usual}
        elif hour < 5:
            out["drops"] = False

    gov = snap.get("gov")
    if gov is not None:
        groups: dict = {}
        for p in gov:
            if isinstance(p.get("ts"), (int, float)) and p["ts"] >= now - 3600:
                groups.setdefault((p.get("title"), p.get("noop")), []).append(p)
        big = max(groups.values(), key=len, default=[])
        if len(big) >= VOTES_BURST:
            who = [p.get("proposer") for p in big]
            out["votes"] = {"n": len(big), "title": str(big[0].get("title") or "a rule change"), "noop": bool(big[0].get("noop")),
                            "accounts": len(set(who)), "top": max(who.count(a) for a in set(who)),
                            "span": max(p["ts"] for p in big) - min(p["ts"] for p in big)}
        elif len(big) < 2:
            out["votes"] = False

    status = snap.get("status")
    if status is not None:
        seen = st.get("reorg_seen")
        rs = [r for r in status.get("reorgs") or [] if isinstance(r.get("at"), (int, float))]
        if seen is None:
            st["reorg_seen"] = max((r["at"] for r in rs), default=0)
        else:
            new = [r for r in rs if r["at"] > seen and int(r.get("depth") or 0) >= 2]
            if rs:
                st["reorg_seen"] = max(seen, max(r["at"] for r in rs))
            if new:
                out["reorg"] = {"depth": max(int(r["depth"]) for r in new), "height": min(int(r["height"]) for r in new),
                                "count": len(new)}
    return out


# ---------------- what the posts say ----------------
def caught_up(blocks: dict, since: float | None, now: float) -> dict:
    """The blocks made after `since`, from their own timestamps: did the network keep going while we saw nothing?"""
    ts = sorted(t for t in (block_ts(b) for b in blocks.values()) if t and since and t > since)
    if not ts:
        return {"n": 0, "gap": now - (since or now)}
    gaps = [b - a for a, b in zip([since] + ts, ts)]
    return {"n": len(ts), "gap": max(gaps)}


def start_post(key: str, f: dict, now: float) -> dict:
    """{"tg": Telegram HTML, "x": [headline, body]} for the start of an incident."""
    e = html.escape
    issue = None
    link = (f"{SITE}/status/", "Live status on Tau HUD")
    if key == "peers":
        if f["connected"] == 0:
            head = "🔌 Our node lost the IDNI bootnode"
            what = ("Our read node has no connection to the IDNI bootnode and no other peer, so no new blocks reach us. "
                    "That is about the connection: it does not prove the testnet itself stopped.")
            xb = "Our read node has no peers, so no new blocks reach us. We post again when it is back."
        else:
            head = "🔌 The IDNI bootnode does not answer our node"
            what = (f"We still get blocks from {plural(f['connected'], 'other node')}. New nodes join through the bootnode, "
                    "so for now they may have trouble connecting.")
            xb = what
        facts = [f"Last block we saw: #{f['head']:,} at {hm(f['last_ts'], now)}" if f.get("head") and f.get("last_ts") else None,
                 f"Connected peers: {f['connected']}"]
    elif key == "stall":
        head = "⏸ No new block on the testnet"
        quiet = fmt_dur(now - f["last_ts"])
        what = (f"Our node is connected to the network but no block has come for {quiet}. "
                f"Usually one comes every {fmt_dur(f['exp'])}.")
        xb = f"No block for {quiet} while our node is connected; usually one every {fmt_dur(f['exp'])}. We post again when blocks resume."
        facts = [f"Last block: #{f['head']:,} at {hm(f['last_ts'], now)}" if f.get("head") else None]
    elif key == "ghost":
        head = "👻 Ghost transactions in the waiting list"
        what = (f"{plural(f['sealed'], 'transaction')} already in a block {'are' if f['sealed'] != 1 else 'is'} still listed "
                "as waiting, so they look pending when they are already in. A known node bug; nothing is lost.")
        xb = what
        facts = [f"Listed as waiting: {f['waiting']}, of them already sealed: {f['sealed']}"]
        issue, link = 81, (f"{SITE}/explorer/", "See them on the Tau HUD explorer")
    elif key == "reorg":
        head = "🔀 Blocks were replaced (reorg)"
        what = (f"The network replaced {plural(f['depth'], 'block')} from #{f['height']:,} on with a different version. "
                "Transactions in them may sit in other blocks now.")
        xb = what
        facts = [f"Reorgs just now: {f['count']}" if f["count"] > 1 else None]
    elif key == "slow":
        head = "🐢 Blocks are coming much slower than usual"
        what = f"Only {f['made']} blocks in the last hour, where about {f['want']} are usual."
        xb = what
        facts = []
    elif key == "drops":
        head = "🗑 Many transactions dropped"
        what = (f"{plural(f['hour'], 'transaction')} left the waiting list in the last hour without ever reaching a block "
                "(refused on re-check, expired or replaced). Maybe someone is testing hard.")
        xb = what
        facts = [f"Usually about {f['usual']:.0f} an hour"]
    elif key == "votes":
        n, k, span = f["n"], f["accounts"], fmt_dur(max(60, f["span"]))
        if f["noop"] and k == 1:
            head = "🗳 One account repeats the same vote"
            what = (f"One account proposed the rules in force again {n} times within {span}. Nothing changes; it looks like a "
                    "script or someone testing the vote flow, not a real rule change.")
        elif f["noop"]:
            head = "🗳 Many practice votes at once"
            what = (f"{n} proposals within {span} restate the rules in force, from {plural(k, 'account')}"
                    + (f" ({f['top']} from one of them)" if f["top"] * 2 > n else "")
                    + ". Nothing changes; probably people trying the Vote page" + (" or one of them testing the flow." if f["top"] * 2 > n else "."))
        else:
            head = f"🗳 The same rule change proposed {n} times"
            what = (f"“{f['title']}” was proposed {n} times within {span} by {plural(k, 'account')}. "
                    "Only one copy can take effect; the rest look like retries or a test.")
        xb = what
        facts = []
        link = (f"{SITE}/proposals/", "All proposals on Tau HUD")
    else:  # behind
        head = "🐌 Our node fell behind the network"
        what = f"Our read node is {plural(f['lag'], 'block')} behind the newest block its peers report, so Tau HUD shows older data for now."
        xb = what
        facts = []
        issue = 78
    lines = [REAL_LINE, f"<b>{e(head)}</b>", e(what)] + [f"• {e(x)}" for x in facts if x]
    if issue:
        lines.append(f"Known issue: <a href=\"{ISSUE}{issue}\">IDNI #{issue}</a>")
    lines += ["", f"<i>{e(FOOT)}</i>", f"<a href=\"{link[0]}\">{link[1]}</a>"]
    return {"tg": "\n".join(lines), "x": [head, xb + (f" Known issue IDNI #{issue}." if issue else "")]}


def end_post(key: str, inc: dict, now: float, blocks: dict) -> dict:
    e = html.escape
    lasted = fmt_dur((inc.get("clear_since") or now) - inc["since"])
    f = inc["facts"]
    facts = []
    if key in ("peers", "stall"):
        c = caught_up(blocks, f.get("last_ts"), now)
        kept = c["n"] and c["gap"] < STALL_MIN
        if key == "peers":
            head = "✅ Back: the IDNI bootnode answers our node again"
            what = f"Blocks reach us again after {lasted}."
        else:
            head = "✅ Blocks resumed"
            what = f"New blocks again after {fmt_dur(now - f['last_ts'])}."
        if kept:
            what += f" The testnet kept making blocks the whole time; our node only missed them and has caught up on {plural(c['n'], 'block')}."
        elif c["n"] and key == "stall":
            what = f"New blocks again: the testnet made no block for {fmt_dur(c['gap'])}."
        elif c["n"]:
            what += f" The testnet itself made no block for {fmt_dur(c['gap'])}."
        xb = what
    elif key == "slow":
        head, what = "✅ Block pace is back to normal", f"After {lasted} of slow blocks."
        xb = what
    else:  # behind
        head, what = "✅ Our node is in sync again", f"It was behind for {lasted}; Tau HUD shows the newest blocks again."
        xb = what
    lines = [REAL_LINE, f"<b>{e(head)}</b>", e(what)] + [f"• {e(x)}" for x in facts]
    lines += ["", f"<a href=\"{SITE}/status/\">Live status on Tau HUD</a>"]
    return {"tg": "\n".join(lines), "x": [head, xb]}


def summary_post(held: list[dict], now: float) -> dict:
    e = html.escape
    first, last = min(h["at"] for h in held), max(h["at"] for h in held)
    count: dict[str, int] = {}
    for h in held:
        count[h["key"]] = count.get(h["key"], 0) + 1
    rows = [f"{n}× {DETECTORS[k]['label']}" for k, n in sorted(count.items(), key=lambda kv: -kv[1])]
    head = "🌀 A busy stretch on the testnet"
    what = (f"Between {hm(first, now)} and {hm(last, now)} our node saw {plural(len(held), 'unusual thing')}, more than we post "
            "one by one. Maybe someone is testing hard, which is what a testnet is for. All of it in one post:")
    lines = [REAL_LINE, f"<b>{e(head)}</b>", e(what)] + [f"• {e(r)}" for r in rows]
    lines += ["", f"<i>{e(FOOT)}</i>", f"<a href=\"{SITE}/status/\">Live status on Tau HUD</a>"]
    return {"tg": "\n".join(lines), "x": [head, f"Between {hm(first, now)} and {hm(last, now)} our node saw {len(held)} unusual things:"]
            + [f"• {r}" for r in rows[:4]]}


# ---------------- the engine ----------------
def fresh_state() -> dict:
    return {"inc": {}, "last_end": {}, "log": [], "held": [], "storm": None, "outbox": [], "primed": False}


def observe(st: dict, snap: dict, now: float) -> list[dict]:
    """Advance the incidents by one check; the posts it makes are queued in st["outbox"] and returned."""
    for k, v in fresh_state().items():
        st.setdefault(k, v)
    conds = conditions(snap, now, st)
    if conds is None:
        return []
    made: list[dict] = []
    blocks = snap.get("blocks") or {}
    st["log"] = [t for t in st["log"] if now - t < STORM_HOURS * 3600]

    def begin(key: str, inc: dict):
        d = DETECTORS[key]
        inc["start"] = now
        if not st["primed"] or inc.get("old"):
            inc["quiet"] = True
            return
        st["log"].append(now)
        cooled = now - st["last_end"].get(key, -1e12) < d["cooldown"]
        if st["storm"] is None and len(st["log"]) >= STORM_AT:
            st["storm"] = {"since": now}
        if cooled or st["storm"]:
            inc["quiet"] = True
            st["held"].append({"key": key, "at": now, "storm": bool(st["storm"])})
            return
        p = start_post(key, inc["facts"], now)
        x = d["x"](inc["facts"]) if callable(d["x"]) else d["x"]
        inc["posted"], inc["x"] = True, x
        made.append({"what": key + " start", "tg": p["tg"], "x": p["x"] if x else None})

    for key, d in DETECTORS.items():
        c = conds.get(key)
        if d.get("event"):
            if c:
                inc = {"facts": c}
                begin(key, inc)
                st["last_end"][key] = now
            continue
        if c is None:
            continue
        inc = st["inc"].get(key)
        if c:
            if not inc:
                # already on at the first run: how things are, not news, also once its hold has passed
                inc = st["inc"][key] = {"since": now, "start": None, "facts": c, **({} if st["primed"] else {"old": True})}
            inc["facts"] = {**inc["facts"], **{k: v for k, v in c.items() if k not in ("last_ts", "head") or inc["start"] is None}}
            inc["clear_since"] = None
            if inc["start"] is None and now - inc["since"] >= d["hold"]:
                begin(key, inc)
        elif inc:
            if inc["start"] is None:
                del st["inc"][key]
                continue
            inc["clear_since"] = inc.get("clear_since") or now
            if now - inc["clear_since"] < d["end_hold"]:
                continue
            if inc.get("posted") and d["recovery"]:
                p = end_post(key, inc, now, blocks)
                made.append({"what": key + " end", "tg": p["tg"], "x": p["x"] if inc.get("x") else None})
            st["last_end"][key] = now
            del st["inc"][key]

    # the summary of a busy stretch
    held = st["held"]
    calm = not any(i["start"] is not None for i in st["inc"].values()) and (not st["log"] or now - max(st["log"]) >= CALM)
    day_end = datetime.fromtimestamp(now, timezone.utc).hour >= SUMMARY_HOUR and \
        st.get("summary_day") != datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
    if held and (calm or day_end):
        stormy = st["storm"] is not None or any(h.get("storm") for h in held)
        if stormy or len(held) >= 3:
            p = summary_post(held, now)
            made.append({"what": "summary", "tg": p["tg"], "x": p["x"] if stormy else None})
            st["summary_day"] = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
            st["held"] = []
        elif calm:
            st["held"] = []  # one or two repeats within a cooldown: not worth a post of their own
        if calm:
            st["storm"] = None
    elif calm and not held:
        st["storm"] = None
    st["primed"] = True
    for m in made:
        st["outbox"].append({**m, "at": now, "tries": 0})
    return made


def covers_outage(st: dict) -> bool:
    """True while a posted peers or stall incident already tells the channel that no new blocks come."""
    return any(st.get("inc", {}).get(k, {}).get("posted") for k in ("peers", "stall"))

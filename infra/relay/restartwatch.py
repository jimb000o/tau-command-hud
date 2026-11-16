"""After a testnet restart: no step left for the owner (Kilian 16.11.2026: "that shouldn't be the case in the future").

The relay already follows a restart by itself (relay.poll_blocks: the old chain's blocks are kept, the showcase wallets
and No Memo's vaults set their rules again, the rule numbers start a new day). What used to need the owner was the
report for IDNI (`up restarts`). Now, once per restart:

  1. right away: when this restart came during a ship call and it is the PAUSE_AFTER-th such restart in PAUSE_DAYS
     days (counted from the owner's last `up ships on`), the cruise ships pause until the owner turns them on again
     (our test load stops; a restart is never IDNI's fault in what we write, only a fact);
  2. once the rules are back (all in force) or NOTE_MAX minutes passed: one note for the owner's private Telegram chat
     (alerts.maybe_restart_note reads GET /restarts/notes and sends it): what re-set itself and what not yet, and a
     short English reply for IDNI made only of facts (restart_report.brief), with the link to the full timeline.

  GET /restarts/report.txt   the full timeline with tx hashes (restart_report.report), to send IDNI
  GET /restarts/notes        (internal) the notes, newest last
  GET /restarts/status       (internal) pause state and what is waiting
  GET /restarts/resume       (internal) the ships sail again (`up ships on`)
"""
import json
import logging
import os
import time

import restart_report

log = logging.getLogger("relay.restartwatch")

DATA = os.environ.get("CRUISE_DATA", "/data")
STATE = os.environ.get("RESTARTWATCH_PATH", os.path.join(DATA, "restartwatch.json"))
NOTE_MIN = float(os.environ.get("RESTART_NOTE_MIN_MINUTES", 8)) * 60     # the rules get a few minutes to come back
NOTE_MAX = float(os.environ.get("RESTART_NOTE_MAX_MINUTES", 40)) * 60    # then the note goes anyway, with what is missing
NOTE_AGE = 24 * 3600                                                     # a restart older than this (relay was away) gets no note
PAUSE_AFTER = int(os.environ.get("RESTART_SHIP_PAUSE_AFTER", 3))          # 0 = the ships never pause by themselves
PAUSE_DAYS = float(os.environ.get("RESTART_SHIP_PAUSE_DAYS", 7))
REPORT_DAYS = int(os.environ.get("RESTART_REPORT_DAYS", 14))
REPORT_CACHE = 120
PUBLIC = os.environ.get("RESTART_REPORT_URL", "https://" + os.environ.get("RELAY_DOMAIN", "node.tauhud.com") + "/restarts/report.txt")
KEEP = 20


class RestartWatch:
    def __init__(self, path: str = STATE, clock=time.time, rows_fn=None):
        self.path, self.clock = path, clock
        self.rows_fn = rows_fn or restart_report.load_log
        self.st = {"noted": [], "notes": [], "paused": None, "resumed_at": None, "paused_for": []}
        try:
            with open(path) as f:
                got = json.load(f)
            if isinstance(got, dict):
                self.st.update(got)
        except (OSError, ValueError):
            pass
        self._report = (0.0, "")

    def save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(self.st, f, separators=(",", ":"))
            os.replace(tmp, self.path)
        except OSError as exc:
            log.warning("cannot write %s: %r", self.path, exc)

    # ---------- 1. the ships ----------
    def apply_pause(self, cruise):
        """At relay start: ships paused before stay paused."""
        if self.st.get("paused") and cruise is not None:
            cruise.enabled = False

    def on_restart(self, restarts: list, cruise=None, now: float | None = None) -> bool:
        """Called right after relay._record_restart. True when the ships were paused now."""
        now = now if now is not None else self.clock()
        if PAUSE_AFTER <= 0 or cruise is None or self.st.get("paused") or not restarts:
            return False
        rows = self.rows_fn()
        since = max(now - PAUSE_DAYS * 86400, self.st.get("resumed_at") or 0)
        r = restarts[-1]
        tip_ts = (r.get("old") or {}).get("tip_ts")
        if not tip_ts or not restart_report.in_call(rows, tip_ts):
            return False
        during = [x for x in restarts if (x.get("detected_at") or 0) >= since and (x.get("old") or {}).get("tip_ts")
                  and restart_report.in_call(rows, x["old"]["tip_ts"])]
        if len(during) < PAUSE_AFTER:
            return False
        why = (f"{len(during)} testnet restarts during our ship calls in {PAUSE_DAYS:.0f} days; "
               f"the ships wait for the owner (up ships on)")
        v = getattr(cruise, "cur", None)
        if v and not v.get("left"):
            try:
                cruise.leave(now, "the testnet restarted during this call again; the ships pause for now", None)
            except Exception as exc:  # noqa: BLE001 - the pause holds all the same
                log.warning("restartwatch: ship leave: %r", exc)
        cruise.enabled = False
        self.st["paused"] = {"at": int(now), "why": why, "restarts": len(during)}
        self.st["paused_for"] = [str(r.get("detected_at"))]
        self.save()
        log.warning("restartwatch: ships paused: %s", why)
        return True

    def resume(self, cruise=None, now: float | None = None) -> dict:
        now = now if now is not None else self.clock()
        was = self.st.get("paused")
        self.st.update(paused=None, resumed_at=int(now))
        self.save()
        if cruise is not None and os.environ.get("CRUISE_ENABLED", "1") != "0":
            cruise.enabled = True
        log.warning("restartwatch: ships on again (were paused: %s)", bool(was))
        return {"ships": "on" if cruise is None or cruise.enabled else "off (CRUISE_ENABLED=0 in .env)", "was_paused": bool(was)}

    # ---------- 2. the note ----------
    def tick(self, restarts: list, rules: dict, height, now: float | None = None) -> dict | None:
        """Called every minute. rules = {group: {name: in force (bool)}}; height = the new chain's head on our node.
        Writes at most one note; returns it."""
        now = now if now is not None else self.clock()
        if not restarts:
            return None
        r = restarts[-1]
        key, at = str(r.get("detected_at")), r.get("detected_at") or 0
        if key in self.st["noted"] or now - at > NOTE_AGE:
            return None
        missing = [f"{g}: {n}" for g, ws in rules.items() for n, ok in ws.items() if not ok]
        age = now - at
        if not height or age < NOTE_MIN or (missing and age < NOTE_MAX):
            return None   # no block on the new chain yet, or the rules still coming back (at most NOTE_MAX)
        b = restart_report.brief(restarts, self.rows_fn(), now, days=int(PAUSE_DAYS), link=PUBLIC) or {}
        note = {"key": key, "at": int(now), "detected_at": at, "height": height, "brief": b,
                "rules": {g: {"in_force": sum(1 for ok in ws.values() if ok), "of": len(ws)} for g, ws in rules.items()},
                "missing": missing, "paused": self.st.get("paused") if key in (self.st.get("paused_for") or []) else None,
                "report": PUBLIC}
        note["text"] = owner_text(note)
        self.st["noted"] = (self.st["noted"] + [key])[-KEEP:]
        self.st["notes"] = (self.st["notes"] + [note])[-KEEP:]
        self.save()
        log.warning("restartwatch: note for the restart noticed %s ready", restart_report.hm(at))
        return note

    # ---------- routes ----------
    def report(self, now: float | None = None) -> str:
        now = now if now is not None else self.clock()
        if now - self._report[0] > REPORT_CACHE:
            try:
                txt = restart_report.report(REPORT_DAYS, now)
            except Exception as exc:  # noqa: BLE001
                log.warning("restartwatch: report failed: %r", exc)
                txt = "The report could not be made just now; try again in a minute.\n"
            self._report = (now, f"Tau HUD (tauhud.com), made {time.strftime('%Y-%m-%d %H:%M', time.gmtime(now))} UTC\n\n" + txt)
        return self._report[1]

    def route(self, path: str, internal: bool, cruise=None):
        """(code, content type, body) or None."""
        if path == "/restarts/report.txt":
            return 200, "text/plain; charset=utf-8", self.report().encode()
        if path in ("/restarts/notes", "/restarts/status", "/restarts/resume"):
            if not internal:
                return 404, "application/json", b'{"error":"not here"}'
            if path == "/restarts/notes":
                body = {"notes": self.st["notes"]}
            elif path == "/restarts/resume":
                body = self.resume(cruise)
            else:
                body = {"paused": self.st.get("paused"), "resumed_at": self.st.get("resumed_at"), "pause_after": PAUSE_AFTER,
                        "pause_days": PAUSE_DAYS, "noted": self.st["noted"][-5:], "report": PUBLIC,
                        "ships": None if cruise is None else ("on" if cruise.enabled else "off")}
            return 200, "application/json", json.dumps(body, separators=(",", ":")).encode()
        return None


def owner_text(n: dict) -> str:
    """The owner's private note (German, Telegram HTML); the reply for IDNI stays English, in a copy block."""
    from html import escape
    b = n.get("brief") or {}
    hm = restart_report.hm
    lines = [f"🟠 <b>Testnet-Neustart</b>: alte Kette endete bei #{b.get('tip', '?')} um {hm(b.get('tip_ts'))}, "
             f"unser Node ist auf der neuen Kette (Block #{n.get('height')})."]
    if b.get("calls"):
        lines.append(f"Während eines Anlaufs ({', '.join(restart_report.ship_name(v) for v in b['calls'])}). "
                     f"{b.get('during', 0)} von {b.get('recent', 0)} Neustarts in 7 Tagen kamen während eines Anlaufs.")
    for g, c in (n.get("rules") or {}).items():
        lines.append(f"{'✅' if c['in_force'] == c['of'] else '⏳'} {escape(g)}: {c['in_force']}/{c['of']} Regeln wieder in Kraft")
    if n.get("missing"):
        lines.append("Noch nicht: " + escape(", ".join(n["missing"])) + " (setzt sich weiter von selbst)")
    if n.get("paused"):
        lines.append("⏸ <b>Schiffe pausiert</b> (" + str(n["paused"].get("restarts")) + " Neustarts während Anläufen). "
                     "Wieder an: <code>" + escape('ssh root@node.tauhud.com "cd /opt/tau-command-hud && sh infra/up.sh ships on"') + "</code>")
    lines.append("")
    lines.append("Antwort für Andrei zum Kopieren (nichts wurde an IDNI geschickt):")
    lines.append("<pre>" + escape(b.get("reply") or "") + "</pre>")
    lines.append(f"Volle Zeitleiste: {escape(n.get('report') or '')}")
    return "\n".join(lines)

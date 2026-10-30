"""Comments on the road-to-mainnet page (tauhud.com/roadmap/): visitors say what they think of a problem we list and of the
path we propose for it. Kept by the same live moderator as the troll box (chat.py), so it feels the same and costs nothing
extra to look after.

Who writes: the same as in the troll box, no account and no captcha. The name is the simulation's animal name and colour
(two indices into the lists in simvotes.py), and a random browser token lets the writer delete their own comment later
(only a hash of it is stored). Who wrote a comment is known only in memory, as the daily person hash (visits.person()),
so limits and strikes work and are gone at 00:00 UTC.

One moderation for both rooms: the filter is chat.judge() (with longer texts allowed), every refusal counts on the troll
box's strike ladder (warn, 10 min, 1 h, out until 00:00 UTC), a visitor muted or out in the troll box cannot comment
either, and once someone is out all their comments of the day disappear for everyone (Chat.on_ban). REPORTS_TO_HIDE
reports hide a comment; the AI moderator (chatai.py, when CHAT_AI_KEY is set) reads each comment once more. Links are
allowed only to the places proof lives: GitHub, tauhud.com and YouTube.

The limits, made to be unnoticeable for someone writing a real comment: one comment per GAP seconds, PER_HOUR an hour,
PER_DAY a day, ITEM_PER_HOUR on one item from everyone, MIN_LEN to MAX_LEN characters. Comments stay (they are the
record of the discussion) until hidden; MAX_PER_ITEM per item at most. ROADMAP_ENABLED=0 in infra/.env closes the
comments (reading stays).

"I see this too": one per browser token per item, kept as a hash; one person can add at most AGREE_PER_DAY a day.

WebSocket commands (relay.py hands them over; replies and pushes have command "roadmap"):
  roadmap join                                               counts for every item, and live pushes from now on
  roadmap leave                                              no more pushes
  roadmap get <item>                                         the comments on one item
  roadmap say <token> <a> <b> <c> <item> <part> <text, %-encoded>   post; part is problem, path or - (general)
  roadmap report <id> <token>                                report a comment
  roadmap delete <id> <token>                                delete your own comment
  roadmap agree <item> <token>                               "I see this too"
HTTP:
  GET /roadmap                                               counts as JSON
  GET /roadmap?item=<item>                                   the comments on one item as JSON
  GET /roadmap/admin?key=<chat key>                          the owner's page: every comment with Hide buttons
  GET /roadmap/hide?key=<chat key>&id=<id>                   hide a comment and put its writer out for the day
"""
from __future__ import annotations

import hashlib
import hmac
import html
import json
import logging
import os
import re
import time
from urllib.parse import parse_qs, unquote

from chat import REASONS, TOKEN, Chat, clean, judge, same
from simvotes import COLOURS, WORDS_A, WORDS_B, name_of

log = logging.getLogger("relay.roadmap")

MIN_LEN = 12
MAX_LEN = 600
GAP = 60                # seconds between two comments of one person
PER_HOUR = 6
PER_DAY = 20
ITEM_PER_HOUR = 30      # comments on one item from everyone
REPORTS_TO_HIDE = 3
MAX_PER_ITEM = 300
MAX_ITEMS = 60          # distinct item ids accepted (the page has about a dozen)
AGREE_PER_DAY = 40
ITEM = re.compile(r"^[a-z0-9][a-z0-9-]{1,39}$")
PARTS = {"problem", "path", "-"}
# the places proof lives; these links are kept, every other link is refused like in the troll box
ALLOWED = re.compile(r"https?://(?:www\.)?(?:github\.com|tauhud\.com|node\.tauhud\.com|agorzilla\.com|youtube\.com|youtu\.be)(?:/[^\s<>\"']*)?", re.I)

SAYS = {
    "long": f"At most {MAX_LEN} characters, please.",
    "short": "A little more, please: what do you see, or what would you change?",
    "slow": "One comment a minute, please.",
    "hour": "That is a lot of comments for one hour; take a break.",
    "day": "That is today's comments; more tomorrow.",
    "busy": "This item is busy right now; try again in a few minutes.",
    "full": "This item has as many comments as it can show.",
    "closed": "Comments are closed right now; reading still works.",
    "link": "Links only to GitHub, tauhud.com or YouTube here.",
}


def _h(token: str) -> str:
    return hashlib.sha256(("roadmap:" + token).encode()).hexdigest()[:16]


class Roadmap:
    def __init__(self, chat: Chat, path: str | None = None, clock=time.time):
        self.chat = chat
        self.path = path if path is not None else os.environ.get("ROADMAP_PATH", "/data/roadmap.json")
        self.enabled = os.environ.get("ROADMAP_ENABLED", "1") not in ("0", "false", "no", "")
        self.clock = clock
        self.comments: list[dict] = []        # {id, item, part, ts, a, b, c, text, tok, hidden?}; stored
        self.agree: dict[str, list] = {}       # item -> token hashes; stored
        self.writer: dict[int, str] = {}       # comment id -> person, memory only
        self.reports: dict[int, set] = {}
        self.sent: dict[str, list] = {}        # person -> send times today
        self.item_sent: dict[str, list] = {}
        self.agreed_today: dict[str, int] = {}
        self.next_id = 1
        self.on_new = None                     # relay.py: pushes to the open pages
        self.on_hide = None
        self._day = int(clock() // 86400)
        self._load()
        chat.on_ban = self.sweep

    # ---------- storage ----------
    def _load(self):
        try:
            with open(self.path) as f:
                st = json.load(f)
            self.comments = [c for c in st.get("comments", []) if isinstance(c, dict) and ITEM.match(str(c.get("item", "")))]
            self.agree = {k: list(v) for k, v in (st.get("agree") or {}).items() if ITEM.match(k) and isinstance(v, list)}
            self.next_id = max([int(st.get("next", 1))] + [c["id"] + 1 for c in self.comments])
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, KeyError) as exc:
            log.warning("cannot read %s: %r; the roadmap comments start empty", self.path, exc)

    def _save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"next": self.next_id, "comments": self.comments, "agree": self.agree}, f,
                          separators=(",", ":"), ensure_ascii=False)
            os.replace(tmp, self.path)
        except OSError as exc:
            if not getattr(self, "_warned", False):
                log.warning("cannot write %s: %r; roadmap comments live in memory only", self.path, exc)
                self._warned = True

    def _tick(self, now: float):
        day = int(now // 86400)
        if day != self._day:   # the person hash changes at 00:00 UTC
            self.sent, self.agreed_today, self.writer, self.reports = {}, {}, {}, {}
            self._day = day

    # ---------- views ----------
    @staticmethod
    def public(c: dict) -> dict:
        return {"id": c["id"], "item": c["item"], "part": c["part"], "ts": round(c["ts"]), "a": c["a"], "b": c["b"],
                "c": c["c"], "name": name_of(c["a"], c["b"]), "text": c["text"]}

    def counts(self) -> dict:
        n: dict[str, int] = {}
        for c in self.comments:
            if not c.get("hidden"):
                n[c["item"]] = n.get(c["item"], 0) + 1
        return {"enabled": self.enabled, "comments": n, "agree": {k: len(v) for k, v in self.agree.items()},
                "min_len": MIN_LEN, "max_len": MAX_LEN, "gap": GAP}

    def thread(self, item: str) -> dict:
        shown = [self.public(c) for c in self.comments if c["item"] == item and not c.get("hidden")]
        return {"item": item, "comments": shown, "agree": len(self.agree.get(item, []))}

    def _known(self, item: str) -> bool:
        items = {c["item"] for c in self.comments} | set(self.agree)
        return item in items or len(items) < MAX_ITEMS

    # ---------- actions ----------
    def _refuse(self, person: str, code: str) -> dict:
        r = self.chat._refuse(person, code)   # the troll box's strike ladder
        if code in SAYS:
            r["message"] = SAYS[code] + r["message"][len(REASONS[code]):]
        return r

    def say(self, person: str, token: str, a: int, b: int, c: int, item: str, part: str, raw: str) -> dict:
        """{"ok": True, "comment": {...}} or {"error": <code>, "message": <why, and what follows>}."""
        no = lambda code: {"error": code, "message": SAYS.get(code) or REASONS[code]}  # noqa: E731
        if not self.enabled:
            return no("closed")
        if (not TOKEN.match(token or "") or not ITEM.match(item or "") or part not in PARTS
                or not (0 <= a < WORDS_A and 0 <= b < WORDS_B and 0 <= c < COLOURS)):
            return no("bad")
        now = self.clock()
        self._tick(now)
        self.chat._expire(now)
        self.chat.seen_as[person] = name_of(a, b)
        stop = self.chat.out(person)   # muted or out in the troll box: here too
        if stop:
            return stop
        text = clean(raw)
        if len(text) > MAX_LEN:
            return no("long")
        rest = re.sub(r" +", " ", ALLOWED.sub(" ", text)).strip()   # the allowed links are not judged, the words are
        why = judge(rest, self.chat.extra, MAX_LEN)
        if why and why not in ("empty", "long"):
            return self._refuse(person, why)
        if len(rest) < MIN_LEN:
            return no("short")
        times = self.sent.get(person, [])
        if times and now - times[-1] < GAP:
            return no("slow")
        if sum(1 for t in times if now - t < 3600) >= PER_HOUR:
            return no("hour")
        if len(times) >= PER_DAY:
            return no("day")
        key = same(text)
        if any(same(x["text"]) == key for x in self.comments[-300:] if not x.get("hidden")):
            return self._refuse(person, "repeat")
        busy = [t for t in self.item_sent.get(item, []) if now - t < 3600]
        if len(busy) >= ITEM_PER_HOUR:
            return no("busy")
        if not self._known(item) or sum(1 for x in self.comments if x["item"] == item) >= MAX_PER_ITEM:
            return no("full")
        m = {"id": self.next_id, "item": item, "part": part, "ts": now, "a": a, "b": b, "c": c, "text": text, "tok": _h(token)}
        self.next_id += 1
        self.comments.append(m)
        self.writer[m["id"]] = person
        self.sent[person] = times + [now]
        self.item_sent[item] = busy + [now]
        self._save()
        return {"ok": True, "comment": self.public(m)}

    def _find(self, cid: int) -> dict | None:
        return next((c for c in self.comments if c["id"] == cid and not c.get("hidden")), None)

    def _hide(self, c: dict, strike: int = 0):
        c["hidden"] = True
        writer = self.writer.get(c["id"])
        if writer and strike:
            self.chat.strike(writer, strike)
        self._save()
        if self.on_hide:
            self.on_hide(c["id"])

    def report(self, person: str, cid: int, token: str) -> dict:
        if not TOKEN.match(token or ""):
            return {"error": "bad", "message": REASONS["bad"]}
        c = self._find(cid)
        if c is None:
            return {"ok": True, "hidden": True}
        if self.writer.get(cid) == person or c.get("tok") == _h(token):
            return {"ok": True, "hidden": False}
        who = self.reports.setdefault(cid, set())
        who.add(person)
        if len(who) >= REPORTS_TO_HIDE:
            self._hide(c, 1)
            return {"ok": True, "hidden": True}
        return {"ok": True, "hidden": False}

    def delete(self, cid: int, token: str) -> bool:
        """The writer takes their own comment back (the browser token they wrote it with)."""
        c = self._find(cid)
        if c is None or not TOKEN.match(token or "") or not hmac.compare_digest(c.get("tok", ""), _h(token)):
            return False
        self._hide(c)
        return True

    def owner_hide(self, cid: int) -> bool:
        c = self._find(cid)
        if c is None:
            return False
        self._hide(c, 4)
        return True

    def flag(self, cid: int) -> bool:
        """The AI moderator found a comment unfit: hide it for everyone and strike its writer."""
        c = self._find(cid)
        if c is None:
            return False
        c["flagged"] = True
        self._hide(c, 1)
        return True

    def sweep(self, person: str):
        """Someone is out of the troll box for the day: their comments of today disappear too."""
        hit = False
        for c in self.comments:
            if not c.get("hidden") and self.writer.get(c["id"]) == person:
                c["hidden"] = hit = True
                if self.on_hide:
                    self.on_hide(c["id"])
        if hit:
            self._save()

    def add_agree(self, person: str, item: str, token: str) -> dict:
        if not TOKEN.match(token or "") or not ITEM.match(item or ""):
            return {"error": "bad", "message": REASONS["bad"]}
        self._tick(self.clock())
        if self.chat.out(person):
            return {"ok": True, "agree": len(self.agree.get(item, [])), "counted": False}
        got = self.agree.get(item, [])
        h = _h(token)
        if h in got or self.agreed_today.get(person, 0) >= AGREE_PER_DAY or not self._known(item):
            return {"ok": True, "agree": len(got), "counted": h in got}
        self.agree[item] = got + [h]
        self.agreed_today[person] = self.agreed_today.get(person, 0) + 1
        self._save()
        return {"ok": True, "agree": len(self.agree[item]), "counted": True}

    def context(self, cid: int, n: int = 3) -> list[str]:
        """The texts before comment cid on the same item (context for the AI moderator)."""
        c = next((x for x in self.comments if x["id"] == cid), None)
        if c is None:
            return []
        return [f"(road-to-mainnet comment on item {c['item']})"] + [
            x["text"] for x in self.comments if x["item"] == c["item"] and x["id"] < cid and not x.get("hidden")][-n:]

    # ---------- HTTP ----------
    def route(self, path: str, query: str):
        """(status, content type, body bytes) for /roadmap paths, else None."""
        q = {k: v[0] for k, v in parse_qs(query).items()}
        if path == "/roadmap":
            item = q.get("item", "")
            body = self.thread(item) if ITEM.match(item) else self.counts()
            return 200, "application/json", json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
        if path not in ("/roadmap/admin", "/roadmap/hide"):
            return None
        if not hmac.compare_digest(q.get("key", ""), self.chat.key):
            return 403, "text/plain; charset=utf-8", b"wrong key\n"
        back = html.escape(f"/roadmap/admin?key={q['key']}", quote=True)
        if path == "/roadmap/hide":
            ok = q.get("id", "").isdigit() and self.owner_hide(int(q["id"]))
            return ((200 if ok else 404), "text/html; charset=utf-8", (
                f"<!doctype html><meta charset=utf-8><meta http-equiv=refresh content='1;url={back}'>"
                f"{'Hidden; the writer is out until 00:00 UTC.' if ok else 'No such comment.'} <a href='{back}'>Back</a>").encode())
        key = html.escape(q["key"], quote=True)
        rows = "".join(
            f"<tr{' class=h' if c.get('hidden') else ''}><td>{time.strftime('%d.%m. %H:%M', time.gmtime(c['ts']))}</td>"
            f"<td>{html.escape(c['item'])}<br>{html.escape(c['part'])}</td><td>{html.escape(name_of(c['a'], c['b']))}</td>"
            f"<td>{html.escape(c['text'])}</td><td>"
            + ("hidden" if c.get("hidden") else f"<a href='/roadmap/hide?key={key}&id={c['id']}'>Hide + mute</a>")
            + f" · {len(self.reports.get(c['id'], ()))} reports</td></tr>"
            for c in reversed(self.comments[-500:]))
        page = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'><meta name=robots content=noindex>"
                "<title>Road to mainnet · comments</title><style>body{background:#0b0b0d;color:#ddd;font:13px/1.5 monospace;margin:16px}"
                "td{padding:6px 8px;border-bottom:1px solid #222;vertical-align:top}tr.h{opacity:.4}a{color:#39ff8a}</style>"
                f"<h1>Road to mainnet · comments</h1><p>Comments {'open' if self.enabled else 'closed (ROADMAP_ENABLED=0)'} · "
                f"{sum(1 for c in self.comments if not c.get('hidden'))} shown · Hide also puts the writer out of the troll box "
                f"and the comments until 00:00 UTC · <a href='/chat/admin?key={key}'>Troll box admin and today's strikes</a></p>"
                f"<table>{rows or '<tr><td>no comments yet</td></tr>'}</table>")
        return 200, "text/html; charset=utf-8", page.encode()


def parse_say(args: list[str]):
    """(token, a, b, c, item, part, text) from the words after "roadmap say", or None."""
    if len(args) < 7 or not all(x.isdigit() for x in args[1:4]):
        return None
    try:
        text = unquote(" ".join(args[6:]), errors="strict")
    except UnicodeDecodeError:
        return None
    return args[0], int(args[1]), int(args[2]), int(args[3]), args[4], args[5], text

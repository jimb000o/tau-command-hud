"""The troll box: one public live chat room on the HUD (assets/chat.js), kept tidy by rules instead of a moderator.

A visitor has no account: the name is the simulation's random animal name (two indices into the lists in simvotes.py) and
a colour, chosen in the browser with a random token. The relay stores each message for 24 hours with that name, the
colour, the text and the time; never an address. Who wrote a message is known only in memory, as the daily salted hash
visits.person() makes from address and user agent, so the limits and the mute work and are gone with the next restart.

The rules, all automatic:
- one message per CHAT_GAP seconds per person, at most PER_HOUR an hour, no repeat of one's own last text; the whole room
  at most ROOM_PER_MIN messages a minute (slow mode)
- at most MAX_LEN characters; no links, web addresses, @handles or e-mail addresses
- no price or trading talk, no hype, no giveaway or "send me your key" bait, no slurs; CHAT_BLOCK_WORDS in .env adds more
- REPORTS_TO_HIDE reports from different people hide a message for everyone; a person with HIDES_TO_MUTE hidden messages
  is muted for the rest of the day
- the owner hides any message with /chat/admin?key=<key>, which also mutes its writer for the day
- CHAT_ENABLED=0 closes the room: the panel says so and nothing is accepted

WebSocket commands (relay.py hands them over; replies and pushes have command "chat"):
  chat join                                     the last messages, the rules, and live pushes on this socket from now on
  chat leave                                    no more pushes
  chat say <token> <a> <b> <c> <text, %-encoded> post a message
  chat report <id> <token>                      report a message
HTTP:
  GET /chat                                     the last messages as JSON (read only)
  GET /chat/admin?key=<key>                     the owner's page: every message of the last 24 hours with a Hide button
  GET /chat/hide?key=<key>&id=<id>              hide a message and mute its writer for the day
The key comes from CHAT_KEY or, if that is empty, is made once and kept in /data/chat.key.
"""
from __future__ import annotations

import html
import hmac
import json
import logging
import os
import re
import secrets
import time
import unicodedata
from urllib.parse import parse_qs, unquote

from simvotes import COLOURS, WORDS_A, WORDS_B, name_of

log = logging.getLogger("relay.chat")

KEEP = 86400            # seconds a message is kept
SHOW = 80               # messages a joining page receives
MAX_KEEP = 2000         # messages stored at most
MAX_LEN = 200
CHAT_GAP = 8            # seconds between two messages of one person
PER_HOUR = 40
ROOM_PER_MIN = 30
REPORTS_TO_HIDE = 3
HIDES_TO_MUTE = 2
TOKEN = re.compile(r"^[0-9a-f]{32}$")

# no links: a scheme, www., or a word.tld with a common top level domain, t.me/ invites, @handles, e-mail addresses
LINK = re.compile(r"(https?:|ftp:|www\.|\b[\w-]+(\.|\s*\(dot\)\s*|\s*\[dot\]\s*)(com|net|org|io|xyz|app|me|gg|co|cc|ru|cn|info|biz|site|online|link|ly|to|finance|money|exchange|top|club|vip|pro|live|fun|tk|ml)\b|t\.me/|\bt\s*\.\s*me\b|@\w{3,}|\b[\w.+-]+@[\w-]+\.\w+)", re.I)
# price, trading and hype talk (testnet AGRS has no value; the site never talks prices), giveaway and key bait
TALK = [
    r"\$", r"€", r"£", r"¥", r"\busdt?\b", r"\busdc\b", r"\beur\b", r"\bbtc\b", r"\beth\b", r"\bsats?\b",
    r"\bprices?\b", r"\bpump\w*", r"\bdump\w*", r"\bmoon\w*", r"\blambo\w*", r"\bto the moon\b", r"\bwen\b",
    r"\bbuy\w*", r"\bsell\w*", r"\bshill\w*", r"\bhodl\w*", r"\bbag(s|holder)?\b", r"\bpresale\b", r"\bico\b", r"\bido\b",
    r"\blisting\b", r"\blisted\b", r"\bmarket ?cap\b", r"\bmcap\b", r"\bprofits?\b", r"\binvest(ing|ment|ments|or|ors|ed|s)?\b", r"\broi\b",
    r"\b\d+\s*x\b", r"\bx\s*\d+\b", r"\bairdrops?\b", r"\bgiveaway\b", r"\bfree (coins?|tokens?|agrs)\b",
    r"\bseed ?phrase\b", r"\bprivate ?key\b", r"\bmnemonic\b", r"\bdm me\b", r"\bwhats ?app\b", r"\btelegram me\b",
    r"\bbinance\b", r"\bcoinbase\b", r"\bkraken\b", r"\bmexc\b", r"\bkucoin\b", r"\bbybit\b", r"\buniswap\b",
    r"价格", r"价钱", r"买入", r"卖出", r"拉盘", r"砸盘", r"暴涨", r"暴跌", r"百倍", r"千倍", r"上所", r"空投", r"私钥", r"助记词", r"投资",
    r"価格", r"値段", r"買い", r"売り", r"爆上げ", r"暴落", r"上場", r"エアドロ", r"秘密鍵", r"投資",
]
# slurs and the worst insults: the long ones also hidden inside letters ("n.i.g.g…", "f a g g o t"), the short ones as words
SLURS = ["nigger", "nigga", "faggot", "kanake", "schwuchtel", "heilhitler", "siegheil", "untermensch", "tranny", "wetback"]
SLUR_WORDS = ["retard", "retards", "kike", "spic", "chink", "coon", "gook", "neger", "zigeuner", "fag", "fags", "1488"]
LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i", "|": "i"})

REASONS = {
    "link": "No links or handles here.",
    "talk": "No price, trading or giveaway talk: testnet AGRS has no value.",
    "slur": "That word is not welcome here.",
    "long": f"At most {MAX_LEN} characters.",
    "empty": "Nothing to send.",
    "slow": "One message every few seconds, please.",
    "hour": "That is a lot for one hour; take a break.",
    "repeat": "You just said that.",
    "busy": "The room is busy; try again in a minute.",
    "muted": "You are muted for today.",
    "closed": "The troll box is closed right now.",
    "bad": "That did not look like a message.",
}


def clean(text: str) -> str:
    """The text as shown: normalized, without control or invisible characters, single spaces."""
    t = unicodedata.normalize("NFKC", text)
    t = "".join(ch for ch in t if unicodedata.category(ch)[0] != "C" or ch == " ")
    return re.sub(r"\s+", " ", t).strip()


def refusal(text: str, extra: list[str] | None = None) -> str | None:
    """Why a cleaned text is not posted ("link", "talk", "slur", "long", "empty"), or None."""
    if not text:
        return "empty"
    if len(text) > MAX_LEN:
        return "long"
    if LINK.search(text):
        return "link"
    low = text.lower()
    if any(re.search(p, low) for p in TALK):
        return "talk"
    letters = re.sub(r"[^a-z]", "", low.translate(LEET))
    words = set(re.findall(r"\w+", low)) | set(re.findall(r"\w+", low.translate(LEET)))
    if any(w in letters for w in SLURS) or words & set(SLUR_WORDS) or any(w in low for w in extra or []):
        return "slur"
    return None


class Chat:
    def __init__(self, path: str | None = None, key_path: str | None = None, clock=time.time):
        self.path = path if path is not None else os.environ.get("CHAT_PATH", "/data/chat.json")
        self.enabled = os.environ.get("CHAT_ENABLED", "1") not in ("0", "false", "no", "")
        self.extra = [w.strip().lower() for w in os.environ.get("CHAT_BLOCK_WORDS", "").split(",") if w.strip()]
        self.clock = clock
        self.key = os.environ.get("CHAT_KEY", "").strip() or self._load_key(
            key_path if key_path is not None else os.environ.get("CHAT_KEY_PATH", "/data/chat.key"))
        self.msgs: list[dict] = []          # {id, ts, a, b, c, text}; stored
        self.writer: dict[int, str] = {}    # message id -> person, memory only
        self.reports: dict[int, set] = {}   # message id -> persons who reported it, memory only
        self.sent: dict[str, list] = {}     # person -> recent send times, memory only
        self.last_text: dict[str, str] = {}
        self.hidden_of: dict[str, int] = {}  # person -> hidden messages today, memory only
        self.muted: dict[str, float] = {}    # person -> muted until
        self.room: list[float] = []
        self.next_id = 1
        self.on_hide = None                  # relay.py: tells the open pages to drop a hidden message
        self._load()

    # ---------- storage ----------
    @staticmethod
    def _load_key(path: str) -> str:
        try:
            with open(path) as f:
                k = f.read().strip()
            if k:
                return k
        except OSError:
            pass
        k = secrets.token_urlsafe(18)
        try:
            with open(path, "w") as f:
                f.write(k + "\n")
        except OSError as exc:
            log.warning("cannot write %s: %r; the chat admin key lasts until the next restart", path, exc)
        return k

    def _load(self):
        try:
            with open(self.path) as f:
                st = json.load(f)
            now = self.clock()
            self.msgs = [m for m in st.get("msgs", []) if isinstance(m, dict) and now - m.get("ts", 0) < KEEP][-MAX_KEEP:]
            self.next_id = max([int(st.get("next", 1))] + [m["id"] + 1 for m in self.msgs])
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, KeyError) as exc:
            log.warning("cannot read %s: %r; the troll box starts empty", self.path, exc)

    def _save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"next": self.next_id, "msgs": self.msgs}, f, separators=(",", ":"), ensure_ascii=False)
            os.replace(tmp, self.path)
        except OSError as exc:
            if not getattr(self, "_warned", False):
                log.warning("cannot write %s: %r; chat lives in memory only", self.path, exc)
                self._warned = True

    def _expire(self, now: float):
        old = len(self.msgs)
        self.msgs = [m for m in self.msgs if now - m["ts"] < KEEP][-MAX_KEEP:]
        if len(self.msgs) != old:
            live = {m["id"] for m in self.msgs}
            self.writer = {k: v for k, v in self.writer.items() if k in live}
            self.reports = {k: v for k, v in self.reports.items() if k in live}
            self._save()
        self.muted = {p: t for p, t in self.muted.items() if t > now}

    # ---------- views ----------
    @staticmethod
    def public(m: dict) -> dict:
        return {"id": m["id"], "ts": round(m["ts"]), "a": m["a"], "b": m["b"], "c": m["c"], "name": name_of(m["a"], m["b"]), "text": m["text"]}

    def recent(self) -> dict:
        now = self.clock()
        self._expire(now)
        return {"enabled": self.enabled, "messages": [self.public(m) for m in self.msgs if not m.get("hidden")][-SHOW:],
                "max_len": MAX_LEN, "gap": CHAT_GAP, "keep_hours": KEEP // 3600}

    # ---------- actions ----------
    def say(self, person: str, token: str, a: int, b: int, c: int, raw: str) -> dict:
        """{"ok": True, "msg": {...}} or {"error": <reason code>, "message": <why>}."""
        no = lambda code: {"error": code, "message": REASONS[code]}  # noqa: E731
        if not self.enabled:
            return no("closed")
        if not TOKEN.match(token or "") or not (0 <= a < WORDS_A and 0 <= b < WORDS_B and 0 <= c < COLOURS):
            return no("bad")
        now = self.clock()
        self._expire(now)
        if self.muted.get(person, 0) > now:
            return no("muted")
        text = clean(raw)
        why = refusal(text, self.extra)
        if why:
            return no(why)
        times = [t for t in self.sent.get(person, []) if now - t < 3600]
        if times and now - times[-1] < CHAT_GAP:
            return no("slow")
        if len(times) >= PER_HOUR:
            return no("hour")
        if self.last_text.get(person) == text.lower():
            return no("repeat")
        self.room = [t for t in self.room if now - t < 60]
        if len(self.room) >= ROOM_PER_MIN:
            return no("busy")
        m = {"id": self.next_id, "ts": now, "a": a, "b": b, "c": c, "text": text}
        self.next_id += 1
        self.msgs.append(m)
        self.writer[m["id"]] = person
        self.sent[person] = times + [now]
        self.last_text[person] = text.lower()
        self.room.append(now)
        if len(self.sent) > 20000:
            self.sent = {p: v for p, v in self.sent.items() if now - v[-1] < 3600}
            self.last_text = {p: v for p, v in self.last_text.items() if p in self.sent}
        self._save()
        return {"ok": True, "msg": self.public(m)}

    def _find(self, mid: int) -> dict | None:
        return next((m for m in self.msgs if m["id"] == mid and not m.get("hidden")), None)

    def _hide(self, m: dict, mute: bool):
        m["hidden"] = True
        writer = self.writer.get(m["id"])
        if writer:
            self.hidden_of[writer] = self.hidden_of.get(writer, 0) + 1
            if mute or self.hidden_of[writer] >= HIDES_TO_MUTE:
                self.muted[writer] = self.clock() + KEEP
        self._save()
        if self.on_hide:
            self.on_hide(m["id"])

    def report(self, person: str, mid: int, token: str) -> dict:
        """{"ok": True, "hidden": bool}; a message hides once REPORTS_TO_HIDE different people reported it."""
        if not TOKEN.match(token or ""):
            return {"error": "bad", "message": REASONS["bad"]}
        m = self._find(mid)
        if m is None:
            return {"ok": True, "hidden": True}
        if self.writer.get(mid) == person:
            return {"ok": True, "hidden": False}
        who = self.reports.setdefault(mid, set())
        who.add(person)
        if len(who) >= REPORTS_TO_HIDE:
            self._hide(m, mute=False)
            return {"ok": True, "hidden": True}
        return {"ok": True, "hidden": False}

    def owner_hide(self, mid: int) -> bool:
        m = self._find(mid)
        if m is None:
            return False
        self._hide(m, mute=True)
        return True

    # ---------- HTTP ----------
    def route(self, path: str, query: str):
        """(status, content type, body bytes) for /chat paths, else None."""
        if path == "/chat":
            return 200, "application/json", json.dumps(self.recent(), separators=(",", ":"), ensure_ascii=False).encode()
        if path not in ("/chat/admin", "/chat/hide"):
            return None
        q = {k: v[0] for k, v in parse_qs(query).items()}
        if not hmac.compare_digest(q.get("key", ""), self.key):
            return 403, "text/plain; charset=utf-8", b"wrong key\n"
        if path == "/chat/hide":
            ok = q.get("id", "").isdigit() and self.owner_hide(int(q["id"]))
            back = html.escape(f"/chat/admin?key={q['key']}", quote=True)
            return (200 if ok else 404), "text/html; charset=utf-8", (
                f"<!doctype html><meta charset=utf-8><meta http-equiv=refresh content='1;url={back}'>"
                f"{'Hidden, writer muted until tomorrow.' if ok else 'No such message.'} <a href='{back}'>Back</a>").encode()
        self._expire(self.clock())
        key = html.escape(q["key"], quote=True)
        rows = "".join(
            f"<tr{' class=h' if m.get('hidden') else ''}><td>{time.strftime('%d.%m. %H:%M', time.gmtime(m['ts']))}</td>"
            f"<td>{html.escape(name_of(m['a'], m['b']))}</td><td>{html.escape(m['text'])}</td><td>"
            + ("hidden" if m.get("hidden") else f"<a href='/chat/hide?key={key}&id={m['id']}'>Hide + mute</a>")
            + f" · {len(self.reports.get(m['id'], ()))} reports</td></tr>"
            for m in reversed(self.msgs))
        page = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'><meta name=robots content=noindex>"
                "<title>Troll box · admin</title><style>body{background:#0b0b0d;color:#ddd;font:13px/1.5 monospace;margin:16px}"
                "td{padding:6px 8px;border-bottom:1px solid #222;vertical-align:top}tr.h{opacity:.4}a{color:#39ff8a}</style>"
                f"<h1>Troll box · last 24 h</h1><p>Room {'open' if self.enabled else 'closed (CHAT_ENABLED=0)'} · "
                f"{len(self.msgs)} messages · Hide also mutes the writer until tomorrow.</p><table>{rows}</table>")
        return 200, "text/html; charset=utf-8", page.encode()


def parse_say(args: list[str]):
    """(token, a, b, c, text) from the words after "chat say", or None."""
    if len(args) < 5 or not all(x.isdigit() for x in args[1:4]):
        return None
    try:
        text = unquote(" ".join(args[4:]), errors="strict")
    except UnicodeDecodeError:
        return None
    return args[0], int(args[1]), int(args[2]), int(args[3]), text

"""The troll box: one public live chat room on the HUD (assets/chat.js), kept tidy by rules instead of a moderator.

A visitor has no account: the name is the simulation's random animal name (two indices into the lists in simvotes.py) and
a colour, chosen in the browser with a random token. The relay stores each message for 24 hours with that name, the
colour, the text and the time; never an address. Who wrote a message is known only in memory, as the daily salted hash
visits.person() makes from address and user agent, so the limits, strikes and bans work and are gone at the day change
(00:00 UTC, when the salt changes) or with the next restart.

The filter, all automatic (judge()): the text is folded first (NFKC, invisible characters out, look-alike Cyrillic and
Greek letters and leetspeak to Latin, stretched letters squeezed), so "p0rn", "pоrn" with a Cyrillic o, "p o r n" and
"poooorn" all read "porn".
- hard, one strike: sexual content, slurs, threats and abuse aimed at someone, scams (seed phrase, "send me", fake support)
- soft, a strike every SOFT_PER_STRIKE times: links and handles, price and trading talk, wallet addresses, shouting in
  capitals, emoji or letter floods, the same text again (also someone else's text within REPEAT_WINDOW: copy-paste bots),
  flooding the slow mode
- not counted: too long, empty, the slow mode itself
Strikes escalate (STEPS): 1 a warning, 2 muted 10 minutes, 3 muted 1 hour, 4 out of the troll box for the rest of the day.
A message hidden by REPORTS_TO_HIDE reports is one strike for its writer; a message the owner hides bans its writer for
the day. The visitor always sees why and for how long. CHAT_BLOCK_WORDS in .env adds hard words; CHAT_ENABLED=0 closes
the room. The rate limits: one message per CHAT_GAP seconds, PER_HOUR an hour, the room ROOM_PER_MIN a minute.

WebSocket commands (relay.py hands them over; replies and pushes have command "chat"):
  chat join                                     the last messages, the rules, and live pushes on this socket from now on
  chat leave                                    no more pushes
  chat say <token> <a> <b> <c> <text, %-encoded> post a message
  chat report <id> <token>                      report a message
HTTP:
  GET /chat                                     the last messages as JSON (read only)
  GET /chat/admin?key=<key>                     the owner's page: the last 24 hours with Hide buttons, and today's strikes
  GET /chat/hide?key=<key>&id=<id>              hide a message and ban its writer for the day
  GET /chat/unban?key=<key>&p=<short id>        clear a visitor's strikes, mute and ban
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
REPEAT_WINDOW = 300     # seconds in which the same text from anyone is refused
REPORTS_TO_HIDE = 3
SOFT_PER_STRIKE = 3     # soft refusals that make one strike
FLOOD_SLOW = 5          # slow-mode refusals within a minute that count as one soft refusal
# strike -> (seconds out, what the visitor is told); None = until the day changes
STEPS = {1: (0, "warn"), 2: (600, "mute"), 3: (3600, "mute"), 4: (None, "ban")}
TOKEN = re.compile(r"^[0-9a-f]{32}$")

# no links: a scheme, www., or a word.tld with a common top level domain, t.me/ invites, @handles, e-mail addresses
LINK = re.compile(r"(https?:|ftp:|www\.|\b[\w-]+(\.|\s*\(dot\)\s*|\s*\[dot\]\s*)(com|net|org|io|xyz|app|me|gg|co|cc|ru|cn|info|biz|site|online|link|ly|to|finance|money|exchange|top|club|vip|pro|live|fun|tk|ml|xxx|porn|sex|cam|tv)\b|t\.me/|\bt\s*\.\s*me\b|discord\s*\.?\s*gg|@\w{3,}|\b[\w.+-]+@[\w-]+\.\w+)", re.I)
# price, trading and hype talk (testnet AGRS has no value; the site never talks prices)
TALK = [
    r"\$", r"€", r"£", r"¥", r"\busdt?\b", r"\busdc\b", r"\beur\b", r"\bbtc\b", r"\beth\b", r"\bsats?\b",
    r"\bprices?\b", r"\bpump\w*", r"\bdump\w*", r"\bmoon\w*", r"\blambo\w*", r"\bwen\b",
    r"\bbuy\w*", r"\bsell\w*", r"\bshill\w*", r"\bhodl\w*", r"\bbag(s|holder)?\b", r"\bpresale\b", r"\bico\b", r"\bido\b",
    r"\blisting\b", r"\blisted\b", r"\bmarket ?cap\b", r"\bmcap\b", r"\bprofits?\b", r"\binvest(ing|ment|ments|or|ors|ed|s)?\b", r"\broi\b",
    r"\b\d+\s*x\b", r"\bx\s*\d+\b",
    r"\bbinance\b", r"\bcoinbase\b", r"\bkraken\b", r"\bmexc\b", r"\bkucoin\b", r"\bbybit\b", r"\buniswap\b",
    r"价格", r"价钱", r"买入", r"卖出", r"拉盘", r"砸盘", r"暴涨", r"暴跌", r"百倍", r"千倍", r"上所", r"投资",
    r"価格", r"値段", r"買い", r"売り", r"爆上げ", r"暴落", r"上場", r"投資",
]
# wallet addresses and keys: long hex runs, bitcoin bech32
ADDR = re.compile(r"\b(0x)?[0-9a-f]{32,}\b|\bbc1[a-z0-9]{20,}\b", re.I)
# scams: key bait, "send me", fake support, giveaways (checked on the folded text)
SCAM = [
    r"\bseed ?phrases?\b", r"\brecovery ?phrases?\b", r"\bprivate ?keys?\b", r"\bmnemonics?\b", r"\bpass ?phrases?\b",
    r"\bsend (me|us|it to)\b", r"\bsend your\b", r"\b(dm|pm|inbox|message) me\b", r"\bcontact me\b", r"\bwhats ?app\b",
    r"\btelegram me\b", r"\badd me on\b", r"\bverify (your|ur) wallet\b", r"\bconnect (your|ur) wallet\b", r"\bwallet ?connect\b",
    r"\bclaim (your|ur|now|free)\b", r"\bdouble (your|ur)\b", r"\b(official )?support team\b", r"\badmin here\b",
    r"\bgiveaways?\b", r"\bairdrops?\b", r"\bfree (coins?|tokens?|agrs|money|crypto)\b", r"\bguaranteed\b",
    r"私钥", r"助记词", r"空投", r"秘密鍵", r"エアドロ",
]
# sexual content: words (folded), and longer ones also hidden inside letters
SEX_WORDS = {"porn", "porno", "porns", "xxx", "nude", "nudes", "naked", "nsfw", "hentai", "sex", "sexy", "sexting", "horny",
             "dick", "dicks", "cock", "cocks", "pussy", "pussies", "boob", "boobs", "tit", "tits", "titties", "cum", "cumming",
             "milf", "escort", "escorts", "hooker", "hookers", "rape", "raped", "rapist", "dildo", "anal", "orgasm", "fap",
             "wank", "slut", "sluts", "whore", "whores", "penis", "vagina", "jizz", "bdsm", "fetish", "erotic", "camgirl",
             "camgirls", "onlyfans", "nudity", "stripper", "blowjob", "handjob", "deepthroat", "creampie", "gangbang",
             "ficken", "fick", "titten", "muschi", "schwanz", "nackt", "nutte"}
SEX_SUB = ["pornhub", "onlyfans", "blowjob", "handjob", "masturbat", "xvideos", "xhamster", "camgirl", "sexcam", "deepthroat",
           "creampie", "gangbang", "pornograph", "chaturbate", "brazzers", "youporn", "redtube"]
SEX_CJK = ["色情", "黄片", "约炮", "性交", "做爱", "裸照", "成人视频", "援交", "エロ", "セックス", "アダルト", "裸", "ポルノ", "風俗"]
# slurs: long ones also inside letters ("n.i.g.g…"), short ones as words
SLURS = ["nigger", "nigga", "faggot", "kanake", "schwuchtel", "heilhitler", "siegheil", "untermensch", "tranny", "wetback",
         "hurensohn", "missgeburt"]
SLUR_WORDS = {"retard", "retards", "retarded", "kike", "kikes", "spic", "spics", "chink", "chinks", "coon", "coons", "gook",
              "neger", "zigeuner", "fag", "fags", "1488", "nazi", "nazis", "kys"}
# abuse aimed at someone, and threats (checked on the folded text with single spaces)
HARM = [
    r"\bkill (your ?self|ur ?self|yourselves)\b", r"\bgo die\b", r"\b(i ?will|i'?ll|ill|gonna) (kill|hurt|find|rape) (you|u)\b",
    r"\bdie in a fire\b", r"\bhope (you|u) die\b", r"\b(neck|hang) (your|ur) ?self\b", r"\bfuck (you|u|off|ur|your)\b",
    r"\bstfu\b", r"\bcunts?\b", r"\bmother ?fuck\w*", r"\bass ?holes?\b", r"\bbitch\w*", r"\bdickhead\w*", r"\bsuck my\b",
    r"\bfick dich\b", r"\bverpiss dich\b", r"\bwichser\b", r"\bfotze\b", r"\barschloch\b", r"\bdrecks\w*",
    r"去死", r"傻逼", r"操你", r"死ね", r"殺す",
]
LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "@": "a", "$": "s", "!": "i",
                      "|": "i", "+": "t", "€": "e", "(": "c"})
# letters that look Latin but are not (Cyrillic, Greek)
LOOK = str.maketrans({"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "к": "k", "м": "m", "т": "t",
                      "н": "h", "в": "b", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "ɡ": "g", "α": "a", "ο": "o", "ρ": "p",
                      "ν": "v", "τ": "t", "ι": "i", "κ": "k", "χ": "x", "ε": "e", "υ": "u", "η": "n"})
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️]")

REASONS = {
    "link": "No links or handles here.",
    "talk": "No price or trading talk: testnet AGRS has no value.",
    "addr": "No wallet addresses or keys here.",
    "scam": "That looks like a scam, so it is not posted.",
    "sex": "No sexual content here.",
    "slur": "That word is not welcome here.",
    "harm": "No insults or threats here.",
    "shout": "Please don't shout in capitals.",
    "spam": "That looks like spam.",
    "long": f"At most {MAX_LEN} characters.",
    "empty": "Nothing to send.",
    "slow": "One message every few seconds, please.",
    "hour": "That is a lot for one hour; take a break.",
    "repeat": "That was just said.",
    "busy": "The room is busy; try again in a minute.",
    "muted": "You are muted for {n} more minutes.",
    "banned": "You are out of the troll box until 00:00 UTC.",
    "closed": "The troll box is closed right now.",
    "bad": "That did not look like a message.",
}
HARD = {"sex", "slur", "harm", "scam"}
SOFT = {"link", "talk", "addr", "shout", "spam", "repeat"}
STEP_TEXT = {"warn": "This is a warning; the next strike mutes you for 10 minutes.",
             "mute": "You are muted for {n} minutes.",
             "ban": "You are out of the troll box until 00:00 UTC."}


def clean(text: str) -> str:
    """The text as shown: normalized, without control or invisible characters, single spaces."""
    t = unicodedata.normalize("NFKC", text)
    t = re.sub(r"\s", " ", t)
    t = "".join(ch for ch in t if unicodedata.category(ch)[0] != "C")
    return re.sub(r" +", " ", t).strip()


def fold(text: str) -> str:
    """The text as the filter reads it: lower case, look-alike letters and leetspeak to Latin, accents off,
    stretched letters squeezed ("fuuuck" -> "fuck"), punctuation to spaces."""
    t = text.lower().translate(LOOK).translate(LEET)
    t = "".join(ch for ch in unicodedata.normalize("NFKD", t) if not unicodedata.combining(ch))
    t = re.sub(r"(.)\1{2,}", r"\1", t)
    t = re.sub(r"[^\w\s']", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def same(text: str) -> str:
    """What two texts share when they count as the same message: letters and digits, lower case."""
    return re.sub(r"[\W_]+", "", text.lower())


def judge(text: str, extra: list[str] | None = None) -> str | None:
    """Why a cleaned text is not posted (a REASONS code), or None."""
    if not text:
        return "empty"
    if len(text) > MAX_LEN:
        return "long"
    low, f = text.lower(), fold(text)
    spaced = re.sub(r"\b(\w) (?=\w\b)", r"\1", f)   # "p o r n" -> "porn"
    words = set(f.split()) | set(re.sub(r"(.)\1", r"\1", f).split()) | set(spaced.split())
    letters = re.sub(r"[^a-z]", "", f)
    dense = re.sub(r"\s", "", text)
    # hard: sexual, slurs, abuse, scams
    if words & SEX_WORDS or any(w in letters for w in SEX_SUB) or any(w in dense for w in SEX_CJK):
        return "sex"
    if any(w in letters for w in SLURS) or words & SLUR_WORDS or "1488" in low or any(w in low or w in f for w in extra or []):
        return "slur"
    if any(re.search(p, f) or re.search(p, low) for p in HARM):
        return "harm"
    if any(re.search(p, f) or re.search(p, low) for p in SCAM):
        return "scam"
    # soft: links, addresses, price talk, shouting, floods
    if LINK.search(text) or LINK.search(text.translate(LOOK)):
        return "link"
    if ADDR.search(text):
        return "addr"
    if any(re.search(p, low) for p in TALK):
        return "talk"
    caps = [ch for ch in text if ch.isalpha() and ch.isascii()]
    if len(caps) >= 12 and sum(ch.isupper() for ch in caps) / len(caps) > 0.7:
        return "shout"
    toks = f.split()
    if (len(EMOJI.findall(text)) >= 8 or re.search(r"(\S)\1{7,}", dense)
            or (len(toks) >= 5 and max(toks.count(w) for w in set(toks)) / len(toks) > 0.6)
            or re.search(r"(\S{2,6})\1{4,}", dense)):
        return "spam"
    return None


refusal = judge   # the older name


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
        # moderation, memory only and keyed by the daily person hash: strikes, soft refusals, mutes, bans, last name used
        self.strikes: dict[str, int] = {}
        self.softs: dict[str, int] = {}
        self.slows: dict[str, list] = {}
        self.muted: dict[str, float] = {}    # person -> muted until
        self.banned: dict[str, float] = {}   # person -> out until (the next 00:00 UTC)
        self.seen_as: dict[str, str] = {}
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
        if any(t <= now for t in self.banned.values()):
            self.banned = {p: t for p, t in self.banned.items() if t > now}
        day = int(now // 86400)
        if day != getattr(self, "_day", day):   # the person hash changes at 00:00 UTC; yesterday's strikes mean nothing
            self.strikes, self.softs, self.slows, self.seen_as = {}, {}, {}, {}
        self._day = day

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
    def strike(self, person: str, n: int = 1) -> str:
        """Add n strikes and apply the step reached; the sentence the visitor is told."""
        now = self.clock()
        k = min(4, self.strikes.get(person, 0) + n)
        self.strikes[person] = k
        secs, kind = STEPS[k]
        if kind == "ban":
            self.banned[person] = (now // 86400 + 1) * 86400
            self.sweep(person)
        elif kind == "mute":
            self.muted[person] = now + secs
        return STEP_TEXT[kind].replace("{n}", str((secs or 0) // 60))

    def sweep(self, person: str):
        """The live moderator's clean-up: once someone is out, all their messages of today disappear for everyone."""
        for m in self.msgs:
            if not m.get("hidden") and self.writer.get(m["id"]) == person:
                m["hidden"] = True
                if self.on_hide:
                    self.on_hide(m["id"])
        self._save()

    def _refuse(self, person: str, code: str) -> dict:
        msg = REASONS[code]
        if code in HARD:
            msg += " " + self.strike(person)
        elif code in SOFT:
            self.softs[person] = self.softs.get(person, 0) + 1
            if self.softs[person] % SOFT_PER_STRIKE == 0:
                msg += " " + self.strike(person)
        return {"error": code, "message": msg}

    def out(self, person: str) -> dict | None:
        """The refusal for a muted or banned person, else None."""
        now = self.clock()
        if self.banned.get(person, 0) > now:
            return {"error": "banned", "message": REASONS["banned"]}
        if self.muted.get(person, 0) > now:
            mins = max(1, int((self.muted[person] - now + 59) // 60))
            return {"error": "muted", "message": REASONS["muted"].replace("{n}", str(mins))}
        return None

    def say(self, person: str, token: str, a: int, b: int, c: int, raw: str) -> dict:
        """{"ok": True, "msg": {...}} or {"error": <reason code>, "message": <why, and what follows>}."""
        no = lambda code: {"error": code, "message": REASONS[code]}  # noqa: E731
        if not self.enabled:
            return no("closed")
        if not TOKEN.match(token or "") or not (0 <= a < WORDS_A and 0 <= b < WORDS_B and 0 <= c < COLOURS):
            return no("bad")
        now = self.clock()
        self._expire(now)
        self.seen_as[person] = name_of(a, b)
        stop = self.out(person)
        if stop:
            return stop
        text = clean(raw)
        why = judge(text, self.extra)
        if why:
            return self._refuse(person, why)
        times = [t for t in self.sent.get(person, []) if now - t < 3600]
        if times and now - times[-1] < CHAT_GAP:
            slows = [t for t in self.slows.get(person, []) if now - t < 60] + [now]
            self.slows[person] = slows
            if len(slows) >= FLOOD_SLOW:
                self.slows[person] = []
                return self._refuse(person, "spam")
            return no("slow")
        if len(times) >= PER_HOUR:
            return no("hour")
        key = same(text)
        if self.last_text.get(person) == key or any(now - m["ts"] < REPEAT_WINDOW and same(m["text"]) == key for m in self.msgs[-60:]):
            return self._refuse(person, "repeat")
        self.room = [t for t in self.room if now - t < 60]
        if len(self.room) >= ROOM_PER_MIN:
            return no("busy")
        m = {"id": self.next_id, "ts": now, "a": a, "b": b, "c": c, "text": text}
        self.next_id += 1
        self.msgs.append(m)
        self.writer[m["id"]] = person
        self.sent[person] = times + [now]
        self.last_text[person] = key
        self.room.append(now)
        if len(self.sent) > 20000:
            self.sent = {p: v for p, v in self.sent.items() if now - v[-1] < 3600}
            self.last_text = {p: v for p, v in self.last_text.items() if p in self.sent}
        self._save()
        return {"ok": True, "msg": self.public(m)}

    def _find(self, mid: int) -> dict | None:
        return next((m for m in self.msgs if m["id"] == mid and not m.get("hidden")), None)

    def _hide(self, m: dict, ban: bool):
        """Hide a message: one strike for its writer, or the day's ban when the owner hid it."""
        m["hidden"] = True
        writer = self.writer.get(m["id"])
        if writer:
            self.strike(writer, 4 if ban else 1)
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
            self._hide(m, ban=False)
            return {"ok": True, "hidden": True}
        return {"ok": True, "hidden": False}

    def owner_hide(self, mid: int) -> bool:
        m = self._find(mid)
        if m is None:
            return False
        self._hide(m, ban=True)
        return True

    def flag(self, mid: int) -> bool:
        """The AI moderator (chatai.py) found a posted message unfit: hide it for everyone and strike its writer."""
        m = self._find(mid)
        if m is None:
            return False
        m["flagged"] = True
        self._hide(m, ban=False)
        return True

    def before(self, mid: int, n: int = 4) -> list[str]:
        """The texts of the n shown messages before message mid (context for the AI moderator)."""
        return [m["text"] for m in self.msgs if m["id"] < mid and not m.get("hidden")][-n:]

    def unban(self, short: str) -> bool:
        """Clear the strikes, mute and ban of the visitor whose person hash starts with short (the admin page shows it)."""
        hits = [p for p in set(self.strikes) | set(self.muted) | set(self.banned) if short and p.startswith(short)]
        for p in hits:
            for d in (self.strikes, self.softs, self.muted, self.banned, self.slows):
                d.pop(p, None)
        return bool(hits)

    # ---------- HTTP ----------
    def route(self, path: str, query: str):
        """(status, content type, body bytes) for /chat paths, else None."""
        if path == "/chat":
            return 200, "application/json", json.dumps(self.recent(), separators=(",", ":"), ensure_ascii=False).encode()
        if path not in ("/chat/admin", "/chat/hide", "/chat/unban"):
            return None
        q = {k: v[0] for k, v in parse_qs(query).items()}
        if not hmac.compare_digest(q.get("key", ""), self.key):
            return 403, "text/plain; charset=utf-8", b"wrong key\n"
        back = html.escape(f"/chat/admin?key={q['key']}", quote=True)
        done = lambda ok, yes, no: ((200 if ok else 404), "text/html; charset=utf-8", (  # noqa: E731
            f"<!doctype html><meta charset=utf-8><meta http-equiv=refresh content='1;url={back}'>"
            f"{yes if ok else no} <a href='{back}'>Back</a>").encode())
        if path == "/chat/hide":
            ok = q.get("id", "").isdigit() and self.owner_hide(int(q["id"]))
            return done(ok, "Hidden; the writer is out until 00:00 UTC.", "No such message.")
        if path == "/chat/unban":
            return done(re.fullmatch(r"[0-9a-f]{6,20}", q.get("p", "")) is not None and self.unban(q["p"]), "Cleared.", "No such visitor.")
        self._expire(self.clock())
        key = html.escape(q["key"], quote=True)
        now = self.clock()
        people = sorted(set(self.strikes) | set(self.muted) | set(self.banned), key=lambda p: -self.strikes.get(p, 0))
        state = lambda p: ("out until 00:00 UTC" if self.banned.get(p, 0) > now else  # noqa: E731
                           f"muted {int((self.muted[p] - now) // 60) + 1} min" if self.muted.get(p, 0) > now else "can write")
        srows = "".join(
            f"<tr><td>#{p[:8]}</td><td>{html.escape(self.seen_as.get(p, '?'))}</td><td>{self.strikes.get(p, 0)} strikes · "
            f"{self.softs.get(p, 0)} soft</td><td>{state(p)}</td><td><a href='/chat/unban?key={key}&p={p[:8]}'>Clear</a></td></tr>"
            for p in people) or "<tr><td>nobody today</td></tr>"
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
                f"{len(self.msgs)} messages · Hide also puts the writer out until 00:00 UTC.</p><table>{rows}</table>"
                f"<h2>Strikes today</h2><p>1 warning · 2 muted 10 min · 3 muted 1 h · 4 out until 00:00 UTC. "
                f"Kept in memory only, gone at the day change or a restart.</p><table>{srows}</table>")
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

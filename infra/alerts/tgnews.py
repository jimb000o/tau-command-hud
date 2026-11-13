"""The Telegram group's News topic: where every Tau HUD post lands when the chat is a group with topics.

Since 13 November 2026 Tau HUD can live in ONE Telegram group instead of a channel plus its discussion group: a
supergroup with Topics switched on, a "News" topic only the bot writes in (it is closed, so only admins post there)
and the group's General topic, renamed "Chat", for everyone. TELEGRAM_CHAT_ID names the group (its @username, or its
-100… id); the news topic is found without anyone looking up a number:

  TELEGRAM_NEWS_TOPIC=<n>   in infra/.env wins, when set (0 = no topic: posts land in General)
  /state/telegram.json      otherwise: the topic `alerts.py --telegram-setup` (up telegram) made in the group

`setup()` asks Telegram what the chat is (getChat). A group with topics and no News topic yet gets one (createForumTopic),
closed at once (closeForumTopic: only admins write there), and General is renamed "Chat" (editGeneralForumTopic);
the id is kept in /state/telegram.json for every service (alerts, blog, donations, agorzilla, bot) on the same volume.
A channel, or a group without topics, keeps posting as before: no message_thread_id is ever added then.

`into(body, ctype)` adds message_thread_id to a send* call aimed at TELEGRAM_CHAT, JSON or multipart alike, so each
poster stays as it is (a private note to the owner, or an answer in someone's chat, is never touched).
"""
from __future__ import annotations

import json
import os
import re

CHAT = os.environ.get("TELEGRAM_CHAT_ID", "@tauHUDchat").strip()
STATE_DIR = os.path.dirname(os.environ.get("STATE_PATH", "/state/alerts.json")) or "/state"
PATH = os.environ.get("TELEGRAM_STATE_PATH", os.path.join(STATE_DIR, "telegram.json"))
NEWS_NAME = os.environ.get("TELEGRAM_NEWS_NAME", "📰 News")
CHAT_NAME = os.environ.get("TELEGRAM_CHAT_NAME", "💬 Chat")
NEWS_COLOR = 0x6FB9F0   # one of the six colours Telegram allows for a topic's icon


def same_chat(a, b: str = "") -> bool:
    a, b = str(a or "").strip(), str(b or CHAT).strip()
    return bool(a) and (a == b or (a.startswith("@") and a.lower() == b.lower()))


def load() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save(d: dict) -> None:
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, PATH)


def topic() -> int | None:
    """The News topic's message_thread_id, or None (a channel, a group without topics, not set up yet)."""
    env = os.environ.get("TELEGRAM_NEWS_TOPIC", "").strip()
    if env:
        try:
            n = int(env)
        except ValueError:
            return None
        return n if n > 1 else None   # 0/1: General, which takes no thread id
    d = load()
    if not same_chat(d.get("chat")):
        return None   # a topic made for another group (TELEGRAM_CHAT_ID changed): not ours
    n = d.get("news_topic")
    return int(n) if isinstance(n, int) and n > 1 else None


def fields(chat) -> dict:
    """{"message_thread_id": n} for a post to the Tau HUD group when it has a News topic, else {}."""
    n = topic() if same_chat(chat) else None
    return {"message_thread_id": n} if n else {}


_MP_CHAT = re.compile(rb'name="chat_id"\r\n\r\n([^\r]*)\r\n')


def into(method: str, body: bytes | None, ctype: str) -> bytes | None:
    """A send* call to TELEGRAM_CHAT with the News topic added; anything else unchanged."""
    if not body or not method.startswith("send"):
        return body
    if ctype.startswith("application/json"):
        try:
            msg = json.loads(body)
        except (TypeError, ValueError):
            return body
        if not isinstance(msg, dict) or "message_thread_id" in msg:
            return body
        extra = fields(msg.get("chat_id"))
        return json.dumps({**msg, **extra}).encode() if extra else body
    m = re.search(r"boundary=([^;\s]+)", ctype)
    if not m or b'name="message_thread_id"' in body:
        return body
    c = _MP_CHAT.search(body)
    extra = fields(c.group(1).decode("utf-8", "replace")) if c else {}
    if not extra:
        return body
    part = f'--{m.group(1)}\r\nContent-Disposition: form-data; name="message_thread_id"\r\n\r\n{extra["message_thread_id"]}\r\n'
    return part.encode() + body


def setup(call) -> list[str]:
    """Make the group ready (News topic, closed; General renamed Chat) and say what was found; `call(method, dict)`
    returns (ok, error text, reply dict). Safe to run again: an existing topic is kept."""
    out = []
    ok, err, r = call("getChat", {"chat_id": CHAT})
    if not ok:
        return [f"cannot see {CHAT} ({err}): is the bot a member/admin of the group, and is its public link {CHAT}?"]
    c = r.get("result") or {}
    kind, forum = c.get("type"), bool(c.get("is_forum"))
    out.append(f"{CHAT} is a {kind}" + (" with topics" if forum else "") + f", id {c.get('id')}, title \"{c.get('title', '')}\"")
    if kind == "channel":
        return out + ["a channel: posts go there as before (no topics)"]
    if not forum:
        return out + ["topics are OFF in this group: posts land in the group itself. Switch on Topics in the group's settings and run up telegram again"]
    d = load()
    if os.environ.get("TELEGRAM_NEWS_TOPIC", "").strip():
        return out + [f"News topic {topic()} set by hand in infra/.env (TELEGRAM_NEWS_TOPIC)"]
    if same_chat(d.get("chat")) and isinstance(d.get("news_topic"), int):
        out.append(f"News topic already there: {d['news_topic']}")
    else:
        ok, err, r = call("createForumTopic", {"chat_id": CHAT, "name": NEWS_NAME, "icon_color": NEWS_COLOR})
        if not ok:
            return out + [f"could NOT make the News topic ({err}): give the bot the admin right 'Manage topics' and run up telegram again"]
        n = (r.get("result") or {}).get("message_thread_id")
        d = {"chat": CHAT, "chat_id": c.get("id"), "news_topic": n}
        save(d)
        out.append(f"News topic made: {n}")
    if not d.get("closed"):
        ok, err, _ = call("closeForumTopic", {"chat_id": CHAT, "message_thread_id": d["news_topic"]})
        out.append("News closed: only admins (and the bot) write there" if ok or "TOPIC_NOT_MODIFIED" in err else
                   f"News NOT closed ({err}): close it by hand (long press on the topic, Close)")
        if ok or "TOPIC_NOT_MODIFIED" in err:
            d["closed"] = True
    if not d.get("general"):
        ok, err, _ = call("editGeneralForumTopic", {"chat_id": CHAT, "name": CHAT_NAME})
        out.append(f"General renamed \"{CHAT_NAME}\": everyone talks there" if ok or "TOPIC_NOT_MODIFIED" in err else
                   f"General not renamed ({err}); harmless")
        d["general"] = True
    save(d)
    return out

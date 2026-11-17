"""Whether an automatic post goes to X now (17 Nov 2026).

The rules for what goes to X, and when, are an owner's posting plan and are kept outside this repository. When a plan is
mounted (XPLAN_DIR, default /xp, with an xplan.py in it), the posters ask it before each automatic X post; without one,
every post goes out as before. Telegram is never asked about: these are X's rules only. Posts the owner sends by hand
(up x send, up post …) are not asked either.

What a plan module may define (each optional; anything missing or failing counts as "as before"):
  allow(kind, account, now, recent) -> (bool, str)   account "hud" (@TauHUDcom) or "agorzilla"; recent = the times of
                                                    that account's recent X posts, newest last
  links(now) -> bool | None                         True: X posts carry their link; None: X_LINKS decides
  text_problems(text, account) -> list[str]         what the plan does not want in a hand-written post's words

Kinds the posters pass: chain (a rule change), finding, restart, newnode, first, today, deepdive, idni, fixed, island,
plan, site, digest, sim, recap, article, idni_feature, ship, hack, donation, agorzilla_evening, agorzilla_growth.
"""
import importlib.util
import logging
import os
import time

log = logging.getLogger("xgate")

DIR = os.environ.get("XPLAN_DIR", "/xp")
PATH = os.path.join(DIR, "xplan.py")
_mod = {"mtime": None, "m": None}


def plan():
    """The mounted plan module, loaded again when its file changes; None when there is none or it does not load."""
    try:
        mtime = os.path.getmtime(PATH)
    except OSError:
        _mod.update(mtime=None, m=None)
        return None
    if mtime != _mod["mtime"]:
        try:
            spec = importlib.util.spec_from_file_location("xplan", PATH)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            _mod.update(mtime=mtime, m=m)
        except Exception as e:  # noqa: BLE001 - a broken plan never stops a post
            log.warning("x plan at %s not loaded (%r); posting as before", PATH, e)
            _mod.update(mtime=mtime, m=None)
    return _mod["m"]


def recent(channel: str = "x") -> list[float]:
    """Times of the recent posts on this channel, as note_public_post keeps them in last-posts.json."""
    try:
        import alerts
        return alerts.recent_posts(channel)
    except Exception:  # noqa: BLE001
        return []


def allow(kind: str, account: str = "hud", now: float | None = None) -> tuple[bool, str]:
    m = plan()
    if not m or not hasattr(m, "allow"):
        return True, ""
    try:
        ok, why = m.allow(kind, account, now if now is not None else time.time(),
                          recent("x" if account == "hud" else "x_" + account))
        if not ok:
            log.info("x: %s (%s) not posted: %s", kind, account, why)
        return bool(ok), str(why or "")
    except Exception as e:  # noqa: BLE001
        log.warning("x plan failed on %s (%r); posting as before", kind, e)
        return True, ""


def links(now: float | None = None) -> bool | None:
    m = plan()
    if not m or not hasattr(m, "links"):
        return None
    try:
        return m.links(now if now is not None else time.time())
    except Exception:  # noqa: BLE001
        return None


def text_problems(text: str, account: str = "hud") -> list[str]:
    m = plan()
    if not m or not hasattr(m, "text_problems"):
        return []
    try:
        return list(m.text_problems(text, account) or [])
    except Exception:  # noqa: BLE001
        return []

"""The Daily Consensus, weekly edition: the week on the Tau testnet as a newspaper front page (gazette/ on the site).

sim_day() keeps what the visitors did in the simulation on one UTC day (relay /sim/votes and /sim/predictions start over
at midnight, so alerts.py notes the day shortly before). edition() turns the weekly recap numbers (recap.build), the rule
changes still waiting (proposals.json) and the noted simulation days into one edition: every line in English and in
Chinese. alerts.py writes it next to the recap image every Monday as /recap/gazette/<date>.json and
/recap/gazette/latest.json; gazette/index.html sets it as the front page and the HUD shows a small notice of it.

The words stay careful: what happened is read from the chain; plans are IDNI's; testnet AGRS have no value; nothing is
offered or sold. Visitor names are the anonymous two-word names of the simulation, nothing else about anyone is known.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

ZH_WEEKDAY = "一二三四五六日"


def fmt_n(n) -> str:
    return f"{int(round(n or 0)):,}"


def t(en: str, zh: str) -> dict:
    return {"en": en, "zh": zh}


def _d(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, timezone.utc)


def period(start: float, end: float) -> dict:
    a, b = _d(start), _d(end - 1)
    en = f"{a.day}–{b.day} {b.strftime('%B %Y')}" if a.month == b.month else f"{a.day} {a.strftime('%B')} – {b.day} {b.strftime('%B %Y')}"
    zh = f"{a.year}年{a.month}月{a.day}日至{b.month}月{b.day}日" if a.year == b.year else f"{a.year}年{a.month}月{a.day}日至{b.year}年{b.month}月{b.day}日"
    return t(en, zh)


def printed(ts: float) -> dict:
    d = _d(ts)
    return t(f"{d.strftime('%A')}, {d.strftime('%B')} {d.day}, {d.year}", f"{d.year}年{d.month}月{d.day}日 星期{ZH_WEEKDAY[d.weekday()]}")


def pace(s: float | None) -> dict:
    if not s:
        return t("—", "—")
    if s < 120:
        return t(f"{s:.0f} seconds", f"{s:.0f} 秒")
    return t(f"{s / 60:.1f} minutes", f"{s / 60:.1f} 分钟")


def eta(blocks: int, s: float | None) -> dict:
    """About how long until a block, in words."""
    if not s or blocks <= 0:
        return t("soon", "很快")
    sec = blocks * s
    if sec < 3600:
        m = max(1, round(sec / 60))
        return t(f"in about {m} minute{'s' if m != 1 else ''}", f"约 {m} 分钟后")
    if sec < 172800:
        h = round(sec / 3600)
        return t(f"in about {h} hour{'s' if h != 1 else ''}", f"约 {h} 小时后")
    d = round(sec / 86400)
    return t(f"in about {d} days", f"约 {d} 天后")


# ---------------- one day of the simulation ----------------
def sim_day(votes: dict | None, predictions: dict | None) -> dict | None:
    """What the visitors did in the simulation today: the hourly ballots, their own proposals and the best forecaster."""
    if not votes or not votes.get("day"):
        return None
    ballots = carried = turned = cast = vprops = vcarried = 0
    for item, it in (votes.get("items") or {}).items():
        if not it or it.get("outcome") is None:   # still open or not yet proposed
            continue
        n = int(it.get("yes") or 0) + int(it.get("no") or 0)
        if item.startswith("visitor:"):
            vprops += 1
            vcarried += it["outcome"] == "yes"
        elif n:
            ballots += 1
            carried += it["outcome"] == "yes"
            turned += it["outcome"] == "no"
        cast += n
    out = {"day": votes["day"], "ballots": ballots, "carried": carried, "turned": turned, "votes": cast,
           "visitor_props": vprops, "visitor_carried": vcarried, "forecasters": 0, "best": None,
           # the two consensus switches of the day (slots 10 and 16, see SIM_SWITCH_SLOTS): outcome and votes once closed
           "switches": {kind: {"outcome": it.get("outcome"), "votes": int(it.get("yes") or 0) + int(it.get("no") or 0)}
                        for kind, k in SIM_SWITCH_SLOTS for it in [(votes.get("items") or {}).get(f"slot:{k}")]
                        if it and it.get("outcome") is not None}}
    if predictions and predictions.get("day") == votes["day"]:
        out["forecasters"] = int(predictions.get("forecasters") or 0)
        board = predictions.get("board") or []
        if board and board[0].get("points"):
            out["best"] = {"name": board[0].get("name") or "Anonymous", "points": int(board[0]["points"])}
    return out


# ---------------- the words of the paper ----------------
NUM_EN = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen",
          "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
NUM_ZH = "零一两三四五六七八九十"


def word(n: int, big: bool = False) -> dict:
    """A small count in words, as a paper of the day would set it: 'three', '三'; larger ones in figures."""
    en = NUM_EN[n] if 0 <= n < len(NUM_EN) else fmt_n(n)
    zh = (NUM_ZH[n] if n <= 10 else ("十" + NUM_ZH[n - 10] if n < 20 else fmt_n(n))) if n >= 0 else str(n)
    return t(en.capitalize() if big else en, zh)


def _fee(m) -> str:
    return m.group(1).replace(",", "")


# The proposal titles (explain.py) are written for the tracker and the alerts: "Base fee 6 → 7 AGRS", "Same rules as now
# (no real change)". The paper says the same thing the way a newspaper of the 1920s would: as a noun phrase that fits a
# headline ("a base fee of 7", "一项新的手续费公式"), with no brackets and no arrows. None means the rules stay as they are.
_PHRASES = [
    (r"^Same rules as now", None),
    (r"^Base fee [\d,]+ → ([\d,]+)(?: AGRS)?$", lambda m: t(f"a base fee of {_fee(m)}", f"基本手续费改为 {_fee(m)}")),
    (r"^Base fee ([\d,]+)(?: AGRS)?$", lambda m: t(f"a base fee of {_fee(m)}", f"基本手续费定为 {_fee(m)}")),
    (r"^New fee formula", lambda m: t("a new formula for fees", "新的手续费公式")),
    (r"^Every validator may make blocks", lambda m: t("an open door for every validator", "所有验证者均可出块")),
    (r"^Stop all block making", lambda m: t("a halt to all block making", "停止一切出块")),
    (r"^Only one validator may make blocks", lambda m: t("a single maker of blocks", "仅由一位验证者出块")),
    (r"^New rule for who makes blocks", lambda m: t("a new rule on who makes blocks", "关于谁来出块的新规则")),
    (r"^Blocks need a valid signature", lambda m: t("signed blocks only", "只认签名有效的区块")),
    (r"^Accept blocks without signature check", lambda m: t("blocks without a signature check", "免验签名的区块")),
    (r"^Reject all blocks", lambda m: t("the refusal of every block", "拒绝一切区块")),
    (r"^New rule for valid blocks", lambda m: t("a new rule on valid blocks", "关于有效区块的新规则")),
    (r"^Admit validator", lambda m: t("a new validator", "接纳一位新验证者")),
    (r"^Remove validator", lambda m: t("the retirement of a validator", "撤下一位验证者")),
    (r"^Votes needed: (.+)$", lambda m: t(f"a vote of {m.group(1)} for every change", f"每项变更须获 {'三分之二' if 'two' in m.group(1) else '过半'} 票数")),
    (r"^(\d+) rule transactions per block", lambda m: t(f"{m.group(1)} rule changes to a block", f"每个区块至多 {m.group(1)} 项规则变更")),
    (r"^Fees go to", lambda m: t("a new hand to receive the fees", "手续费改由新的接收者领取")),
    (r"^Consensus switches to proof of stake", lambda m: t("a turn to proof of stake", "改行权益证明")),
    (r"^Consensus switches to proof of authority", lambda m: t("a return to proof of authority", "回到权威证明")),
    (r"^Consensus switches to", lambda m: t("a new way of agreeing on blocks", "新的出块共识方式")),
    (r"^Co-signed transfers on", lambda m: t("co-signed transfers", "联署转账")),
    (r"^Co-signed transfers off", lambda m: t("an end to co-signed transfers", "停用联署转账")),
]


def phrase(title: str | None) -> dict | None:
    """The proposal title as a headline phrase {en, zh}, or None when the rules would stay as they are."""
    title = (title or "").strip()
    parts = [p for p in re.split(r" \+ (?!\d+ more$)", title) if p]
    more = sum(int(m) for m in re.findall(r" \+ (\d+) more$", title))
    out = []
    for part in parts:
        part = re.sub(r" \+ \d+ more$", "", part)
        for pat, fn in _PHRASES:
            m = re.search(pat, part)
            if m:
                if fn:
                    out.append(fn(m))
                break
        else:
            out.append(t("an amendment to the rules", "一项规则修订"))
    if not out:
        return None
    if len(out) == 1 and not more:
        return out[0]
    rest = len(out) - 1 + more
    return t(f"{out[0]['en']} and {word(rest)['en']} more amendment{'s' if rest != 1 else ''}", f"{out[0]['zh']}等 {rest + 1} 项修订")


def cap(s: str, first: bool = True) -> str:
    """Headline case for an English phrase: every word but the small ones capitalised."""
    small = {"a", "an", "the", "of", "on", "to", "for", "and", "or", "in", "by", "at", "as", "who"}
    w = s.split(" ")
    return " ".join(x if ((i or not first) and x in small) or not x[:1].isalpha() else x[:1].upper() + x[1:] for i, x in enumerate(w))


# ---------------- the edition ----------------
def _sorted(ps: list[dict]) -> list[dict]:
    return sorted(ps, key=lambda p: p.get("activate_at") or 0)


def _pick(titles: list[str]) -> dict | None:
    """The first title that changes something, as a phrase (None if all of them keep the rules as they are)."""
    return next((ph for ph in map(phrase, titles) if ph), None)


# ---------------- the week's news, ranked ----------------
# One-time events that no counter on the chain records. Each is front-page news in the week it falls in.
MILESTONES = [
    {"at": datetime(2026, 10, 26, tzinfo=timezone.utc).timestamp(), "kind": "launch",
     "banner": t("Tau HUD goes live on Testnet Alpha", "Tau HUD 在 Testnet Alpha 上线"),
     "h2": t("A Community Instrument Opens, with a Node of Its Own Beside the Founders'", "社区观测台开张，自有节点与创始团队的节点并肩运行"),
     "deck": t("Since 26 October anyone can watch every block, vote and rule change of the Tau testnet at tauhud.com. "
               "Tau HUD is an unofficial community project, not part of IDNI.",
               "自 10 月 26 日起，任何人都可以在 tauhud.com 观看 Tau 测试网的每一个区块、每一次投票和每一项规则变更。Tau HUD 是非官方社区项目，不隶属于 IDNI。"),
     "para": t("On 26 October Tau HUD opened at tauhud.com, a live view of the Tau testnet read from a node of its own. That node runs beside "
               "the founders' bootnode, the first on Testnet Alpha outside IDNI's own as far as the network shows. It reads and checks every "
               "block; it seals none.",
               "10 月 26 日，Tau HUD 在 tauhud.com 开张：它从自己的节点读取 Tau 测试网的实时情况。这个节点与创始团队的引导节点并肩运行，"
               "就网络所见，是 Testnet Alpha 上第一个 IDNI 之外的节点。它读取并检查每一个区块，但不封存区块。")},
]
# The simulation switches consensus twice a day since 28 October 15:28 UTC (assets/sim.js STAKE_SLOT / FIXED_SLOT):
# proof of stake at 10:30 UTC, the fixed validator list again at 16:30 UTC, each put to the visitors' vote at hh:20.
SIM_SWITCH_SINCE = datetime(2026, 10, 28, 15, 28, tzinfo=timezone.utc).timestamp()
SIM_SWITCH_SLOTS = (("stake", 10), ("fixed", 16))


def sim_switches(start: float, end: float, days: list[dict]) -> list[dict]:
    """The simulated consensus switches that came due in the week; down: the visitors voted it down."""
    by_day = {d["day"]: d for d in days}
    out = []
    day = _d(max(start, SIM_SWITCH_SINCE)).replace(hour=0, minute=0, second=0, microsecond=0)
    while day.timestamp() < end:
        for kind, hour in SIM_SWITCH_SLOTS:
            at = day.timestamp() + hour * 3600 + 30 * 60
            if max(start, SIM_SWITCH_SINCE) <= at < end:
                v = ((by_day.get(day.strftime("%Y-%m-%d")) or {}).get("switches") or {}).get(kind) or {}
                out.append({"kind": kind, "at": at, "votes": int(v.get("votes") or 0), "down": v.get("outcome") == "no"})
        day = _d(day.timestamp() + 86400)
    return out


def news(r: dict, waiting: list[dict], days: list[dict] | None = None, props: list[dict] | None = None) -> list[dict]:
    """Every story of the week worth printing, most newsworthy first: {kind, score, banner, h2, deck, para}. A milestone
    leads, then a real rule change in force, the simulation's consensus switches, new nodes, a real change agreed, a
    fresh chain, new proposals; ballots that only keep the rules come last, and a quiet week when there is nothing else."""
    blocks = fmt_n(r["blocks"] + r["old_blocks"])
    out = []
    for m in MILESTONES:
        if r["start"] <= m["at"] < r["end"]:
            out.append({**m, "score": 100})
    if r["active"]:
        n, ph = r["active"], _pick(r["active_titles"])
        out.append({"kind": "active", "score": 90 if ph else 8,
                    "banner": (t("A vote of the users becomes law", "用户的投票成为规则") if n == 1 else
                               t(f"{word(n, True)['en']} votes of the users become law", f"用户的{word(n)['zh']}项投票成为规则")),
                    "h2": (t(f"{cap(ph['en'])} Takes Effect at the Appointed Block", f"{ph['zh']}，于约定区块生效") if ph else
                           t("The Users Reaffirm Their Rules at the Appointed Block", "用户在约定区块重申现行规则")),
                    "deck": t("Agreed by vote on Testnet Alpha and switched on at the block named in advance. No node was reinstalled and the chain did not split.",
                              "在 Testnet Alpha 上经投票达成一致，并在事先约定的区块启用。没有节点需要重装，链也没有分裂。"),
                    "para": (t(f"On the real testnet {ph['en']} took effect at the block the users had named, with no node reinstalled.",
                               f"在真实的测试网上，{ph['zh']}在用户约定的区块生效，没有节点需要重装。") if ph else None)})
    due = sim_switches(r["start"], r["end"], days or [])
    sw, down = [s for s in due if not s["down"]], sum(s["down"] for s in due)
    # news in the week the switching began, or when the visitors turned one down; a routine week's switches are only a line
    first = r["start"] <= SIM_SWITCH_SINCE < r["end"]
    if sw:
        n, kinds, votes = len(sw), {s["kind"] for s in sw}, sum(s["votes"] for s in due)
        h2 = (t("On the Rehearsal Chain, Proof of Stake by Morning and the Validator List by Evening", "排练链上：上午改行权益证明，傍晚回到验证者名单") if kinds == {"stake", "fixed"} else
              t("On the Rehearsal Chain, Proof of Stake Takes the Seal by Vote", "排练链上：权益证明经投票接掌出块") if kinds == {"stake"} else
              t("On the Rehearsal Chain, the Validator List Returns by Vote", "排练链上：验证者名单经投票回归"))
        s0 = sw[0]
        when = {"stake": t("half past ten in the morning", "上午十点半"), "fixed": t("half past four in the afternoon", "下午四点半")}[s0["kind"]]
        wd = _d(s0["at"])
        to = {"stake": t("from a fixed list of validators to proof of stake, where the largest holders take turns", "从固定的验证者名单改为权益证明，由持有最多的账户轮流出块"),
              "fixed": t("from proof of stake back to its fixed list of validators", "从权益证明回到固定的验证者名单")}[s0["kind"]]
        # the lead story when the switching is new or the visitors turned one down (Kilian 2026-10-29: the consensus switch is the
        # title story); a routine week's switches are told in the Rehearsal Hall
        out.append({"kind": "simswitch", "score": 110 if first else 75 if down else -1,
                    "banner": t("Users vote; the chain changes how it agrees", "用户投票，链改变了达成一致的方式"),
                    "h2": h2,
                    "deck": t("No fork, no restart, not one machine reinstalled. In the simulation that runs in every visitor's browser the visitors voted "
                              "and the simulated validators followed. On Tau, how blocks are made is a rule like any other.",
                              "没有分叉，没有重启，没有一台机器重装。在每位访客浏览器里运行的模拟中，访客投票，模拟验证者照办。在 Tau 上，怎样出块也只是一条规则。"),
                    "para": t(f"At {when['en']} on {wd.strftime('%A')}, UTC, the rehearsal chain changed the way it chooses who seals its blocks: {to['en']}. "
                              "The question went to the floor at twenty past, the visitors of tauhud.com cast their votes, and ten minutes later every simulated node "
                              "switched at the same agreed block. Nobody had to install a thing"
                              + (f"; it happened {word(n)['en']} times this week" if n > 1 else "")
                              + (f", {fmt_n(votes)} vote{'s' if votes != 1 else ''} were cast" if votes else "")
                              + (f", and the visitors turned down {word(down)['en']} switch{'es' if down != 1 else ''}" if down else "")
                              + ". On most chains such a change means a hard fork. On Tau it is a rule change like any other, and this was its rehearsal: "
                              "it happened in the simulation, not on the real testnet.",
                              f"{wd.month}月{wd.day}日 星期{ZH_WEEKDAY[wd.weekday()]}{when['zh']}（UTC），排练链改变了它挑选出块者的方式：{to['zh']}。"
                              "二十分时问题提上台面，tauhud.com 的访客投下选票，十分钟后，每一个模拟节点都在同一个约定的区块切换。没有人需要安装任何东西"
                              + (f"；本周共切换了{word(n)['zh']}次" if n > 1 else "")
                              + (f"，共投出 {fmt_n(votes)} 票" if votes else "")
                              + (f"，访客否决了{word(down)['zh']}次切换" if down else "")
                              + "。在大多数链上，这样的变更意味着一次硬分叉；在 Tau 上，它和其他规则变更一样，而这正是它的排练：它发生在模拟中，而不是真实的测试网上。")})
    if r["new_nodes"]:
        n = r["new_nodes"]
        out.append({"kind": "nodes", "score": 70,
                    "banner": t(f"{word(n, True)['en']} more node{'s take' if n != 1 else ' takes'} up the watch", f"又有{word(n)['zh']}个节点加入守望"),
                    "h2": t("More Machines Keep Watch over the Chain", "更多机器守望这条链"),
                    "deck": t("Every node checks every block against the rules in force. The more there are, the more eyes on the chain.",
                              "每个节点都会按照现行规则检查每一个区块。节点越多，盯着这条链的眼睛就越多。"),
                    "para": t(f"{word(n, True)['en']} new node{'s' if n != 1 else ''} joined Testnet Alpha this week, {word(r['nodes'])['en']} community node{'s' if r['nodes'] != 1 else ''} in all.",
                              f"本周有{word(n)['zh']}个新节点加入 Testnet Alpha，社区节点共{word(r['nodes'])['zh']}个。")})
    if r["agreed"]:
        n = r["agreed"]
        w = next((p for p in _sorted(waiting) if phrase(p.get("title"))), None)
        if w:
            ph, at = phrase(w["title"]), fmt_n(w.get("activate_at"))
            out.append({"kind": "agreed", "score": 60,
                        "banner": (t("The users settle a question of law", "用户以投票议定一项规则") if n == 1 else
                                   t(f"The users settle {word(n)['en']} questions of law", f"用户以投票议定{word(n)['zh']}项规则")),
                        "h2": t(f"Vote Carries for {cap(ph['en'], False)}, in Force from Block #{at}", f"投票通过：{ph['zh']}，自第 {at} 号区块起生效"),
                        "deck": t("The votes are counted. The change waits for the block named in advance, and until then the rules in force apply.",
                                  "票已点清。变更等待事先约定的区块，在此之前现行规则继续适用。"),
                        "para": t(f"On the real testnet the users carried {ph['en']}; it takes effect at block #{at}.",
                                  f"在真实的测试网上，用户投票通过了{ph['zh']}，将自第 {at} 号区块起生效。")})
        else:
            out.append({"kind": "agreed", "score": 5,
                        "banner": t("Practice ballots, and the rules hold", "练习投票，规则如常"),
                        "h2": t(f"{word(n, True)['en']} Ballot{'s' if n != 1 else ''} Keep{'s' if n == 1 else ''} the Rules as They Stand", f"{word(n)['zh']}次投票维持现行规则"),
                        "deck": t("The users voted, and the vote changed nothing, as it was meant to: a ballot that keeps the rules tests the voting itself.",
                                  "用户投了票，而投票如预期般没有改变任何东西：维持规则的投票检验的是投票本身。"),
                        "para": None})
    if r["restarts"]:
        out.append({"kind": "restart", "score": 50,
                    "banner": t("The testnet begins anew from its first block", "测试网从第一个区块重新开始"),
                    "h2": t("A Clean Slate for Testnet Alpha", "Testnet Alpha 从头开始"),
                    "deck": t("The test network began again from its starting state. Tau HUD follows the new chain from its first block.",
                              "测试网从初始状态重新开始。Tau HUD 从新链的第一个区块起继续跟踪。"),
                    "para": None})
    week = [p for p in props or [] if r["start"] <= (p.get("proposed_ts") or 0) < r["end"]]
    n = r["proposed"] - sum(1 for p in week if not phrase(p.get("title")))
    if n > 0 and not r["agreed"]:
        out.append({"kind": "proposed", "score": 30,
                    "banner": t(f"{word(n, True)['en']} amendment{'s' if n != 1 else ''} laid before the users", f"{word(n)['zh']}项修订提交用户表决"),
                    "h2": t("The Ballot Box Is Open on Testnet Alpha", "Testnet Alpha 的投票箱已经打开"),
                    "deck": t("A proposal is checked by logic first; only then do the votes decide. Nothing changes unless the vote agrees.",
                              "提案先经过逻辑检查，然后由投票决定。投票不通过，什么都不会改变。"),
                    "para": None})
    out.append({"kind": "steady", "score": 0,
                "banner": t("A quiet week, and the rules hold", "平静的一周，规则如常"),
                "h2": t(f"{blocks} Blocks, Each Sealed by the Rules in Force", f"{blocks} 个区块，每一个都按现行规则封存"),
                "deck": t("No rule changed this week. The chain kept time and kept its law, which is what a rulebook on a chain is for.",
                          "本周没有规则改变。链按时出块、守住它的规则，这正是写在链上的规则手册的用处。"),
                "para": None})
    return sorted(out, key=lambda s: -s["score"])


def headline(r: dict, waiting: list[dict], days: list[dict] | None = None) -> tuple[dict, dict, dict, str]:
    """(banner, lead heading, deck, kicker key) of the week's most newsworthy story."""
    s = news(r, waiting, days)[0]
    return s["banner"], s["h2"], s["deck"], s["kind"]


def weather(r: dict) -> dict:
    """The ear on the left of the masthead: the week's chain told as a weather report."""
    pc = pace(r["pace"])
    sky = t("Fair", "晴") if r["pace"] and r["pace"] <= 20 else t("Calm", "平静")
    n = r.get("nodes") or 0
    watch = (t(f"{word(n, True)['en']} community node{'s keep' if n != 1 else ' keeps'} watch.", f"{word(n)['zh']}个社区节点守望。") if n else
             t("The founders' node and Tau HUD keep watch.", "创始团队的节点与 Tau HUD 守望。"))
    return t(f"{sky['en']}. A block about every {pc['en']}. {watch['en']} Outlook: the climate may change by vote.",
             f"{sky['zh']}。大约每 {pc['zh']}一个区块。{watch['zh']}展望：气候可经投票改变。")


def caption(r: dict) -> dict:
    blocks = ("about " if r["old_blocks"] else "") + fmt_n(r["blocks"] + r["old_blocks"])
    per = period(r["start"], r["end"])
    return t(f"<b>The week at the core.</b> In the week of {per['en']}, {blocks} blocks were sealed on the testnet, each one photographed as it passed "
             "through the Tau HUD. Every point on the orbit is a node; the ring closes when the validators agree.",
             f"<b>本周的核心。</b>{per['zh']}，测试网封存了 {blocks} 个区块，每一个经过 Tau HUD 时都被摄下。轨道上的每个点都是一个节点；验证者达成一致时，圆环便合上。")


def lead_body(r: dict, props: list[dict] | None = None, stories: list[dict] | None = None) -> list[dict]:
    """The lead story: the top story told first, then the week on the chain, the other news, ballots that keep the
    rules in one short line."""
    stories = stories or []
    blocks = fmt_n(r["blocks"] + r["old_blocks"])
    pc = pace(r["pace"])
    per = period(r["start"], r["end"])
    out = [stories[0]["para"]] if stories and stories[0].get("para") else []
    out.append(t(f"From {per['en']} the Tau testnet sealed {'about ' if r['old_blocks'] else ''}{blocks} blocks, one about every {pc['en']}. "
                 f"{fmt_n(r['txs'])} transactions came from {fmt_n(r['accounts'])} accounts"
                 + (f", {fmt_n(r['transfers'])} of them transfers." if r["transfers"] else "."),
                 f"Tau 测试网在{per['zh']}封存了{'约 ' if r['old_blocks'] else ' '}{blocks} 个区块，大约每 {pc['zh']}一个。"
                 f"{fmt_n(r['accounts'])} 个账户发出了 {fmt_n(r['txs'])} 笔交易"
                 + (f"，其中 {fmt_n(r['transfers'])} 笔是转账。" if r["transfers"] else "。")))
    week = [p for p in props or [] if r["start"] <= (p.get("proposed_ts") or 0) < r["end"]]
    keep = sum(1 for p in week if not phrase(p.get("title")))
    real = max(0, r["proposed"] - keep)
    if real:
        carried = max(0, min(real, r["agreed"] - keep))
        parts_en = [f"{word(real)['en']} proposed"] + ([f"{word(carried)['en']} carried"] if carried else [])
        parts_zh = [f"提出{word(real)['zh']}项"] + ([f"通过{word(carried)['zh']}项"] if carried else [])
        for k, en, zh in (("active", "put in force", "生效"), ("dropped", "dropped", "被放弃")):
            if r[k]:
                parts_en.append(f"{word(r[k])['en']} {en}")
                parts_zh.append(f"{zh}{word(r[k])['zh']}项")
        out.append(t(f"On the rules themselves: {', '.join(parts_en)}. On Tau a rule change is a transaction like any other. "
                     "It is checked by logic, voted on, and switched on at a block named in advance.",
                     f"在规则本身上：{'，'.join(parts_zh)}。在 Tau 上，规则变更和其他交易一样是一笔交易，先经逻辑检查，再经投票，然后在事先约定的区块启用。"))
    if keep:
        out.append(t(f"{word(keep, True)['en']} {'further ' if real else ''}ballot{'s' if keep != 1 else ''} only kept the rules as they stand: practice for the voting itself.",
                     f"另有{word(keep)['zh']}次投票只是维持现行规则，是对投票本身的练习。" if real else f"本周有{word(keep)['zh']}次投票只是维持现行规则，是对投票本身的练习。"))
    elif not real:
        out.append(t("No rule change was proposed on the real testnet this week. Anyone with an account may propose the next one.",
                     "本周真实的测试网上没有人提出规则变更。任何拥有账户的人都可以提出下一项。"))
    also = [ph for ph in map(phrase, r["active_titles"][1:4]) if ph]
    if also:
        out.append(t("Also put in force this week: " + "; ".join(x["en"] for x in also) + ".", "本周同样生效的还有：" + "；".join(x["zh"] for x in also) + "。"))
    more = [s["para"] for s in stories[1:] if s.get("para") and s["score"] > 0]
    for i, p in enumerate(more[:3]):
        out.append(t(("<b>Also this week.</b> " if not i else "") + p["en"], ("<b>本周另讯。</b>" if not i else "") + p["zh"]))
    if r["restarts"]:
        out.append(t(f"The testnet started a new chain {'once' if r['restarts'] == 1 else word(r['restarts'])['en'] + ' times'} this week; balances and history began again from the starting state.",
                     f"本周测试网重新开始了{word(r['restarts'])['zh']}次新链，余额和历史从初始状态重新开始。"))
    if not more:
        out.append(t("Nothing of this needed a new version of the software. Every node read the rules from the chain and followed them, "
                     "which is the whole idea: the users decide, and the machines keep the minutes.",
                     "这一切都不需要新版本的软件。每个节点都从链上读取规则并照办，这正是全部的用意：用户做决定，机器记录在案。"))
    return out


def figures(r: dict) -> list[dict]:
    blocks = ("≈" if r["old_blocks"] else "") + fmt_n(r["blocks"] + r["old_blocks"])
    pc = pace(r["pace"])
    rows = [(t("Blocks sealed", "封存的区块"), t(blocks, blocks)),
            (t("One block about every", "大约每隔"), pc),
            (t("Transactions", "交易"), t(fmt_n(r["txs"]), fmt_n(r["txs"]))),
            (t("Accounts that sent one", "发出交易的账户"), t(fmt_n(r["accounts"]), fmt_n(r["accounts"]))),
            (t("Rule changes proposed", "提出的规则变更"), t(str(r["proposed"]), str(r["proposed"]))),
            (t("Agreed by vote", "投票达成一致"), t(str(r["agreed"]), str(r["agreed"]))),
            (t("Taken effect", "已经生效"), t(str(r["active"]), str(r["active"]))),
            (t("Community nodes online", "在线社区节点"), t(str(r["nodes"]) + (f" (+{r['new_nodes']})" if r["new_nodes"] else ""),
                                                          str(r["nodes"]) + (f"（新增 {r['new_nodes']}）" if r["new_nodes"] else "")))]
    if r["restarts"]:
        rows.append((t("Fresh chains", "新链"), t(str(r["restarts"]), str(r["restarts"]))))
    return [{"label": a, "value": b} for a, b in rows]


def coming_up(props: list[dict], head: int | None, s: float | None) -> dict:
    """The rule changes still waiting: carried ones with their block, then the open votes. Ballots that keep the rules as
    they stand are told in one line, not one by one."""
    head = head or 0
    agreed = _sorted([p for p in props if p.get("status") == "agreed" and (p.get("activate_at") or 0) > head])
    voting = [p for p in props if p.get("status") == "voting"]
    lines = []
    for p in [p for p in agreed if phrase(p.get("title"))][:3]:
        ph, w = phrase(p["title"]), eta(p["activate_at"] - head, s)
        lines.append(t(f"<b>{cap(ph['en'])}.</b> Carried by vote; in force from block #{fmt_n(p['activate_at'])}, {w['en']}.",
                       f"<b>{ph['zh']}。</b>已经投票通过，自第 {fmt_n(p['activate_at'])} 号区块起生效，{w['zh']}。"))
    keep = [p for p in agreed if not phrase(p.get("title"))]
    if keep:
        n, first = len(keep), fmt_n(keep[0]["activate_at"])
        lines.append(t(f"<b>The rules as they stand.</b> {word(n, True)['en']} carried ballot{'s' if n != 1 else ''} to keep them unchanged "
                       + (f"falls due at block #{first}." if n == 1 else f"fall due from block #{first} onward."),
                       f"<b>维持现行规则。</b>另有{word(n)['zh']}项已通过的维持原状投票，" + (f"将在第 {first} 号区块到期。" if n == 1 else f"自第 {first} 号区块起陆续到期。")))
    if voting:
        n = len(voting)
        lines.append(t(f"{word(n, True)['en']} more proposal{'s are' if n != 1 else ' is'} open for votes. Each needs its yes votes before its deadline block, or it is dropped and nothing changes.",
                       f"另有{word(n)['zh']}项提案正在投票。每一项都必须在截止区块之前获得足够的赞成票，否则会被放弃，什么也不会改变。"))
    if not lines:
        lines.append(t("No rule change is waiting for its block. The next one starts with a proposal; how to vote is explained at tauhud.com/vote.",
                       "目前没有等待生效的规则变更。下一项从一份提案开始；如何投票，请看 tauhud.com/vote。"))
    return {"h": t("Coming Up on the Testnet", "测试网接下来"), "body": lines}


def riddle(r: dict, props: list[dict]) -> dict | None:
    """An inside story when the week's ballots only kept the rules: told as a small mystery, honest that the chain is still quiet."""
    week = [p for p in props if r["start"] <= (p.get("proposed_ts") or 0) < r["end"]]
    keep = sum(1 for p in week if not phrase(p.get("title")))
    if keep < 3:
        return None
    n, N = word(keep), word(keep, True)
    return {"h": t("The Riddle of the Unchanging Ballots", "不变投票之谜"), "body": [
        t(f"{N['en']} times this week the users of Testnet Alpha went to the ballot box, and {n['en']} times the question was the same: "
          "shall the rules stay as they are? Each time the answer was yes. When the votes were counted, not one rule had moved.",
          f"本周，Testnet Alpha 的用户{n['zh']}次走向投票箱，问题{n['zh']}次都一样：规则是否维持原样？每一次的回答都是赞成。点完票后，没有一条规则挪动过。"),
        t("What, then, were they voting for? Our correspondent offers a theory. A ballot that keeps the rules is a rehearsal: it proves that a vote "
          "can be cast, counted and carried, block by block, before a question that matters is put.",
          "那么，他们究竟在为什么投票？本报记者提出一个推测：维持规则的投票是一场排练。它证明一张选票可以被投出、清点并通过，一个区块接一个区块，好在真正要紧的问题提出之前做好准备。"),
        t(f"The chain is young and its days are still quiet. But a ballot box tried {n['en']} times is ready for the day the question is a real one.",
          f"这条链还年轻，日子仍然平静。但一个试过{n['zh']}次的投票箱，已经为真正提问的那一天做好了准备。"),
    ]}


# the simulation runs on every page since 28 October 13:11 UTC (assets/sim.js): every hour a special rule change at hh:20,
# a contradicting proposal refused at the door at hh:40, a contested one dropped at its deadline at hh:58; a new chain at midnight
SIM_SINCE = datetime(2026, 10, 28, 13, 11, tzinfo=timezone.utc).timestamp()


def rehearsal(days: list[dict], r: dict | None = None, switches: bool = True) -> dict:
    """The week in the simulation as a feature in the paper's voice: the programme the clock ran, the visitors' votes,
    their own proposals, the consensus switches, the refusals at the door and the best tipster. Always marked as the
    simulation."""
    h = t("From the Rehearsal Hall", "排练厅来稿")
    body = []
    a = max(r["start"], SIM_SINCE) if r else 0
    hours = int((r["end"] - a) // 3600) if r and r["end"] > a else 0
    midnights = int(r["end"] // 86400 - a // 86400) if r and r["end"] > a else 0
    if hours:
        body.append(t(f"Across town from the real testnet stands a rehearsal hall: the simulation, a practice chain that runs in every visitor's browser "
                      f"and where the visitors of tauhud.com hold the gavel. This week the house played {word(hours)['en'] if hours <= 20 else fmt_n(hours)} hour{'s' if hours != 1 else ''} of its programme, "
                      "a rule change on the floor every hour at twenty past.",
                      f"在真实测试网的对街，有一座排练厅：模拟。它是一条在每位访客浏览器里运行的练习链，由 tauhud.com 的访客执槌。"
                      f"本周这座剧院上演了 {fmt_n(hours)} 个小时的节目，每小时二十分都有一项规则变更提上台面。"))
    ballots = sum(d["ballots"] for d in days)
    carried = sum(d["carried"] for d in days)
    turned = sum(d["turned"] for d in days)
    votes = sum(d["votes"] for d in days)
    vprops = sum(d["visitor_props"] for d in days)
    vcarried = sum(d["visitor_carried"] for d in days)
    if ballots:
        vw = word(votes)["en"] if votes <= 20 else fmt_n(votes)
        verdict = ([f"let {word(carried)['en']} pass"] if carried else []) + ([f"sent {word(turned)['en']} home"] if turned else [])
        body.append(t(f"In the simulation, where the visitors decide, {word(ballots)['en']} hourly rule change{'s' if ballots != 1 else ''} went to a vote of the visitors. "
                      f"They cast {vw} vote{'s' if votes != 1 else ''}" + (f" and {' and '.join(verdict)}." if verdict else ".")
                      + " When nobody votes, the simulated validators carry the motion themselves.",
                      f"在由访客做主的模拟中，共有{word(ballots)['zh']}项每小时的规则变更交由访客投票。他们投出 {fmt_n(votes)} 票"
                      + "".join(f"，{x}" for x in ([f"放行{word(carried)['zh']}项"] if carried else []) + ([f"否决{word(turned)['zh']}项"] if turned else []))
                      + "。无人投票时，模拟验证者自行通过动议。"))
    elif not hours:
        body.append(t("In the simulation the visitors decide: every hour one rule change goes to their vote, and the simulated validators follow the majority. "
                      "Try it at tauhud.com in Simulation mode.",
                      "在模拟中由访客做主：每小时有一项规则变更交由他们投票，模拟验证者跟随多数。在 tauhud.com 切换到模拟模式即可参与。"))
    sw = [x for x in sim_switches(r["start"], r["end"], days) if not x["down"]] if r and switches else []
    if sw:
        n = len(sw)
        body.append(t(f"Twice a day the hall rewrites its own constitution. Proof of stake takes the stage at half past ten, the fixed validator list returns at half past four; "
                      f"{word(n)['en']} such change{'s' if n != 1 else ''} came into force this week, and not one machine was reinstalled.",
                      f"这座排练厅每天两次改写自己的宪章：十点半由权益证明登台，四点半固定验证者名单回归。本周共有{word(n)['zh']}次这样的切换生效，没有一台机器需要重装。"))
    if vprops:
        body.append(t(f"Visitors also brought motions of their own: {word(vprops)['en']} rule change{'s' if vprops != 1 else ''} written in the Playground, "
                      f"{word(vcarried)['en']} of them voted in.",
                      f"访客还提出了自己的动议：在试验场写成的{word(vprops)['zh']}项规则变更，其中{word(vcarried)['zh']}项获得通过。"))
    if hours:
        body.append(t(f"The doorkeeper had a busy week. {word(hours, True)['en'] if hours <= 20 else fmt_n(hours)} proposal{'s' if hours != 1 else ''} that contradicted the rules in force were turned away at the door before a single vote, "
                      f"because Tau checks a rule by logic first; {word(hours)['en'] if hours <= 20 else fmt_n(hours)} contested motions, backed by their proposer alone, expired at their deadline"
                      + (f"; and {word(midnights)['en']} time{'s' if midnights != 1 else ''} at midnight the stage was swept and the chain began anew." if midnights else "."),
                      f"守门人这一周很忙。{fmt_n(hours)} 项与现行规则相矛盾的提案还没投票就被拒之门外，因为 Tau 先用逻辑检查规则；"
                      f"{fmt_n(hours)} 项只有提案人支持的争议动议在截止时失效"
                      + (f"；午夜时分舞台清扫了{word(midnights)['zh']}次，链重新开始。" if midnights else "。")))
    best = max((d for d in days if d.get("best")), key=lambda d: d["best"]["points"], default=None)
    if best:
        wd = datetime.strptime(best["day"], "%Y-%m-%d")
        body.append(t(f"The sharpest forecaster of the week was {best['best']['name']}, with {best['best']['points']} points on {wd.strftime('%A')}.",
                      f"本周最准的预测者是 {best['best']['name']}，星期{ZH_WEEKDAY[wd.weekday()]}拿下 {best['best']['points']} 分。"))
    body.append(t("All of this happened in the simulation, not on the real testnet.", "以上都发生在模拟中，而不是真实的测试网上。"))
    return {"h": h, "body": body}


def edition(r: dict, props: list[dict], days: list[dict], no: int, printed_at: float) -> dict:
    """One weekly edition. r: recap.build(); props: proposals.json "proposals"; days: sim_day() of the week."""
    waiting = [p for p in props if p.get("status") == "agreed" and (p.get("activate_at") or 0) > (r.get("head") or 0)]
    ranked = news(r, waiting, days, props)
    top = ranked[0]
    banner, h2, deck, kind = top["banner"], top["h2"], top["deck"], top["kind"]
    kick = {"active": t("Testnet Alpha · rule change", "Testnet Alpha · 规则变更"), "agreed": t("Testnet Alpha · the ballot is counted", "Testnet Alpha · 计票完毕"),
            "restart": t("Testnet Alpha · a fresh start", "Testnet Alpha · 重新开始"), "proposed": t("Testnet Alpha · put to the vote", "Testnet Alpha · 付诸投票"),
            "nodes": t("Testnet Alpha · the network", "Testnet Alpha · 网络"), "steady": t("Testnet Alpha · the week", "Testnet Alpha · 本周"),
            "launch": t("Testnet Alpha · a new instrument", "Testnet Alpha · 新的观测台"), "simswitch": t("Simulation · not the real testnet", "模拟 · 不是真实的测试网")}[kind]
    return {
        "v": 1, "no": no, "date": _d(printed_at).strftime("%Y-%m-%d"), "printed": printed(printed_at),
        "start": round(r["start"]), "end": round(r["end"]), "period": period(r["start"], r["end"]),
        "head": r.get("head"), "kind": kind, "banner": banner, "teaser": deck,
        "lead": {"kick": kick, "h": h2, "deck": deck, "body": lead_body(r, props, ranked)},
        "weather": weather(r), "caption": caption(r),
        "figures": figures(r),
        "stories": [coming_up(props, r.get("head"), r["pace"]), rehearsal(days, r, not any(x["kind"] == "simswitch" and x["score"] > 0 for x in ranked))] + ([m] if (m := riddle(r, props)) else []),
        "url": "https://tauhud.com/gazette/",
        # flat copies for the HUD's notice of the paper (index.html)
        "number": no, "headline": banner["en"], "headline_zh": banner["zh"], "deck": deck["en"], "deck_zh": deck["zh"],
    }


def summary(e: dict) -> dict:
    """The few fields the HUD's notice and the archive list need."""
    return {"no": e["no"], "date": e["date"], "printed": e["printed"], "period": e["period"], "banner": e["banner"], "teaser": e["teaser"],
            "kind": e["kind"], "url": e["url"], "number": e["no"], "headline": e["banner"]["en"], "headline_zh": e["banner"]["zh"],
            "deck": e["teaser"]["en"], "deck_zh": e["teaser"]["zh"]}

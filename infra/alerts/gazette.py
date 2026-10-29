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
           "visitor_props": vprops, "visitor_carried": vcarried, "forecasters": 0, "best": None}
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


def headline(r: dict, waiting: list[dict]) -> tuple[dict, dict, dict, str]:
    """(banner, lead heading, deck, kicker key) from the most newsworthy thing of the week, in the paper's own voice."""
    blocks = fmt_n(r["blocks"] + r["old_blocks"])
    if r["active"]:
        n = r["active"]
        banner = (t("A vote of the users becomes law", "用户的投票成为规则") if n == 1 else
                  t(f"{word(n, True)['en']} votes of the users become law", f"用户的{word(n)['zh']}项投票成为规则"))
        ph = _pick(r["active_titles"])
        h2 = (t(f"{cap(ph['en'])} Takes Effect at the Appointed Block", f"{ph['zh']}，于约定区块生效") if ph else
              t("The Users Reaffirm Their Rules at the Appointed Block", "用户在约定区块重申现行规则"))
        deck = t("Agreed by vote on Testnet Alpha and switched on at the block named in advance. No node was reinstalled and the chain did not split.",
                 "在 Testnet Alpha 上经投票达成一致，并在事先约定的区块启用。没有节点需要重装，链也没有分裂。")
        return banner, h2, deck, "active"
    if r["agreed"]:
        n = r["agreed"]
        banner = (t("The users settle a question of law", "用户以投票议定一项规则") if n == 1 else
                  t(f"The users settle {word(n)['en']} questions of law", f"用户以投票议定{word(n)['zh']}项规则"))
        w = next((p for p in _sorted(waiting) if phrase(p.get("title"))), None)
        if w:
            ph, at = phrase(w["title"]), fmt_n(w.get("activate_at"))
            h2 = t(f"Vote Carries for {cap(ph['en'], False)}, in Force from Block #{at}", f"投票通过：{ph['zh']}，自第 {at} 号区块起生效")
        elif waiting:
            h2 = t("The Ballot Keeps the Rules as They Stand", "投票维持现行规则不变")
        else:
            h2 = t("The Ballot Box Has Spoken on Testnet Alpha", "Testnet Alpha 的投票已有结果")
        deck = t("The votes are counted. Each change waits for the block named in advance, and until then the rules in force apply.",
                 "票已点清。每项变更都等待事先约定的区块，在此之前现行规则继续适用。")
        return banner, h2, deck, "agreed"
    if r["restarts"]:
        banner = t("The testnet begins anew from its first block", "测试网从第一个区块重新开始")
        h2 = t("A Clean Slate for Testnet Alpha", "Testnet Alpha 从头开始")
        deck = t("The test network began again from its starting state. Tau HUD follows the new chain from its first block.",
                 "测试网从初始状态重新开始。Tau HUD 从新链的第一个区块起继续跟踪。")
        return banner, h2, deck, "restart"
    if r["proposed"]:
        n = r["proposed"]
        banner = t(f"{word(n, True)['en']} amendment{'s' if n != 1 else ''} laid before the users", f"{word(n)['zh']}项修订提交用户表决")
        h2 = t("The Ballot Box Is Open on Testnet Alpha", "Testnet Alpha 的投票箱已经打开")
        deck = t("A proposal is checked by logic first; only then do the votes decide. Nothing changes unless the vote agrees.",
                 "提案先经过逻辑检查，然后由投票决定。投票不通过，什么都不会改变。")
        return banner, h2, deck, "proposed"
    if r["new_nodes"]:
        n = r["new_nodes"]
        banner = t(f"{word(n, True)['en']} more node{'s take' if n != 1 else ' takes'} up the watch", f"又有{word(n)['zh']}个节点加入守望")
        h2 = t("More Machines Keep Watch over the Chain", "更多机器守望这条链")
        deck = t("Every node checks every block against the rules in force. The more there are, the more eyes on the chain.",
                 "每个节点都会按照现行规则检查每一个区块。节点越多，盯着这条链的眼睛就越多。")
        return banner, h2, deck, "nodes"
    banner = t("A quiet week, and the rules hold", "平静的一周，规则如常")
    h2 = t(f"{blocks} Blocks, Each Sealed by the Rules in Force", f"{blocks} 个区块，每一个都按现行规则封存")
    deck = t("No rule changed this week. The chain kept time and kept its law, which is what a rulebook on a chain is for.",
             "本周没有规则改变。链按时出块、守住它的规则，这正是写在链上的规则手册的用处。")
    return banner, h2, deck, "steady"


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


def lead_body(r: dict, props: list[dict] | None = None) -> list[dict]:
    blocks = fmt_n(r["blocks"] + r["old_blocks"])
    pc = pace(r["pace"])
    per = period(r["start"], r["end"])
    out = [t(f"From {per['en']} the Tau testnet sealed {'about ' if r['old_blocks'] else ''}{blocks} blocks, one about every {pc['en']}. "
             f"{fmt_n(r['txs'])} transactions came from {fmt_n(r['accounts'])} accounts"
             + (f", {fmt_n(r['transfers'])} of them transfers." if r["transfers"] else "."),
             f"Tau 测试网在{per['zh']}封存了{'约 ' if r['old_blocks'] else ' '}{blocks} 个区块，大约每 {pc['zh']}一个。"
             f"{fmt_n(r['accounts'])} 个账户发出了 {fmt_n(r['txs'])} 笔交易"
             + (f"，其中 {fmt_n(r['transfers'])} 笔是转账。" if r["transfers"] else "。"))]
    parts_en, parts_zh = [], []
    for k, en, zh in (("proposed", "proposed", "提出"), ("agreed", "carried", "通过"), ("active", "put in force", "生效"), ("dropped", "dropped", "被放弃")):
        if r[k]:
            parts_en.append(f"{word(r[k])['en']} {en}")
            parts_zh.append(f"{zh}{word(r[k])['zh']}项")
    if parts_en:
        out.append(t(f"On the rules themselves the users were busy: {', '.join(parts_en)}. On Tau a rule change is a transaction like any other. "
                     "It is checked by logic, voted on, and switched on at a block named in advance.",
                     f"在规则本身上，用户们并不清闲：{'，'.join(parts_zh)}。在 Tau 上，规则变更和其他交易一样是一笔交易，"
                     "先经逻辑检查，再经投票，然后在事先约定的区块启用。"))
    else:
        out.append(t("No rule change was proposed this week. The rules in force stay as the users last agreed them. "
                     "Anyone with an account may propose the next one.",
                     "本周没有人提出规则变更，现行规则仍是用户上次商定的样子。任何拥有账户的人都可以提出下一项。"))
    week = [p for p in props or [] if r["start"] <= (p.get("proposed_ts") or 0) < r["end"]]
    keep = sum(1 for p in week if not phrase(p.get("title")))
    if keep:
        out.append(t(f"{word(keep, True)['en']} of the week's ballots asked only whether to keep the rules as they stand. Such a vote changes nothing; "
                     "it tries the ballot box itself, the way a club tests its voting before an election.",
                     f"本周有{word(keep)['zh']}次投票只问是否维持现行规则。这样的投票不改变任何东西，它检验的是投票本身，就像俱乐部在选举前先试一试投票箱。"))
    also = [ph for ph in map(phrase, r["active_titles"][1:4]) if ph]
    if also:
        out.append(t("Also put in force this week: " + "; ".join(x["en"] for x in also) + ".", "本周同样生效的还有：" + "；".join(x["zh"] for x in also) + "。"))
    if r["restarts"]:
        out.append(t(f"The testnet started a new chain {'once' if r['restarts'] == 1 else word(r['restarts'])['en'] + ' times'} this week; balances and history began again from the starting state.",
                     f"本周测试网重新开始了{word(r['restarts'])['zh']}次新链，余额和历史从初始状态重新开始。"))
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


def rehearsal(days: list[dict]) -> dict:
    """The visitors' week in the simulation."""
    h = t("From the Rehearsal Hall", "排练厅来稿")
    if not days:
        return {"h": h, "body": [t("In the simulation the visitors decide: every hour one rule change goes to their vote, and the simulated validators follow the majority. "
                                   "Try it at tauhud.com in Simulation mode.",
                                   "在模拟中由访客做主：每小时有一项规则变更交由他们投票，模拟验证者跟随多数。在 tauhud.com 切换到模拟模式即可参与。")]}
    ballots = sum(d["ballots"] for d in days)
    carried = sum(d["carried"] for d in days)
    turned = sum(d["turned"] for d in days)
    votes = sum(d["votes"] for d in days)
    vprops = sum(d["visitor_props"] for d in days)
    vcarried = sum(d["visitor_carried"] for d in days)
    nd = len(days)
    vw = word(votes)["en"] if votes <= 20 else fmt_n(votes)
    verdict = ([f"let {word(carried)['en']} through"] if carried else []) + ([f"turned down {word(turned)['en']}"] if turned else [])
    body = [t(f"In the simulation, where the visitors decide, {word(ballots)['en']} hourly rule change{'s' if ballots != 1 else ''} went to a vote of the visitors "
              f"over {word(nd)['en']} day{'s' if nd != 1 else ''}. They cast {vw} vote{'s' if votes != 1 else ''}"
              + (f" and {' and '.join(verdict)}." if verdict else "."),
              f"在由访客做主的模拟中，{word(nd)['zh']}天里共有{word(ballots)['zh']}项每小时的规则变更交由访客投票。"
              f"他们投出 {fmt_n(votes)} 票" + "".join(f"，{x}" for x in ([f"放行{word(carried)['zh']}项"] if carried else []) + ([f"否决{word(turned)['zh']}项"] if turned else [])) + "。")]
    if vprops:
        body.append(t(f"Visitors also wrote {word(vprops)['en']} rule change{'s' if vprops != 1 else ''} of their own, and {word(vcarried)['en']} {'was' if vcarried == 1 else 'were'} voted in.",
                      f"访客还亲手写了{word(vprops)['zh']}项规则变更，其中{word(vcarried)['zh']}项获得通过。"))
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
    banner, h2, deck, kind = headline(r, waiting)
    kick = {"active": t("Testnet Alpha · rule change", "Testnet Alpha · 规则变更"), "agreed": t("Testnet Alpha · the ballot is counted", "Testnet Alpha · 计票完毕"),
            "restart": t("Testnet Alpha · a fresh start", "Testnet Alpha · 重新开始"), "proposed": t("Testnet Alpha · put to the vote", "Testnet Alpha · 付诸投票"),
            "nodes": t("Testnet Alpha · the network", "Testnet Alpha · 网络"), "steady": t("Testnet Alpha · the week", "Testnet Alpha · 本周")}[kind]
    return {
        "v": 1, "no": no, "date": _d(printed_at).strftime("%Y-%m-%d"), "printed": printed(printed_at),
        "start": round(r["start"]), "end": round(r["end"]), "period": period(r["start"], r["end"]),
        "head": r.get("head"), "kind": kind, "banner": banner, "teaser": deck,
        "lead": {"kick": kick, "h": h2, "deck": deck, "body": lead_body(r, props)},
        "weather": weather(r), "caption": caption(r),
        "figures": figures(r),
        "stories": [coming_up(props, r.get("head"), r["pace"]), rehearsal(days)],
        "url": "https://tauhud.com/gazette/",
        # flat copies for the HUD's notice of the paper (index.html)
        "number": no, "headline": banner["en"], "headline_zh": banner["zh"], "deck": deck["en"], "deck_zh": deck["zh"],
    }


def summary(e: dict) -> dict:
    """The few fields the HUD's notice and the archive list need."""
    return {"no": e["no"], "date": e["date"], "printed": e["printed"], "period": e["period"], "banner": e["banner"], "teaser": e["teaser"],
            "kind": e["kind"], "url": e["url"], "number": e["no"], "headline": e["banner"]["en"], "headline_zh": e["banner"]["zh"],
            "deck": e["teaser"]["en"], "deck_zh": e["teaser"]["zh"]}

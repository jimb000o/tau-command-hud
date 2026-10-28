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


# ---------------- the edition ----------------
def _title(it: str) -> str:
    return it.split(": ", 1)[-1]


def headline(r: dict, waiting: list[dict]) -> tuple[dict, dict, dict, str]:
    """(banner, lead heading, deck, kicker key) from the most newsworthy thing of the week."""
    blocks = fmt_n(r["blocks"] + r["old_blocks"])
    if r["active"]:
        ti = r["active_titles"][0] if r["active_titles"] else "a rule change"
        if r["active"] == 1:
            banner = t("A rule change voted by the users takes effect", "用户投票通过的规则变更正式生效")
        else:
            banner = t(f"{r['active']} rule changes voted by the users take effect", f"{r['active']} 项用户投票通过的规则变更正式生效")
        h2 = t(f"Now in Force: {ti}", f"现已生效：「{ti}」")
        deck = t("Agreed by vote on Testnet Alpha and switched on at the agreed block. No node was reinstalled and the chain did not split.",
                 "在 Testnet Alpha 上经投票达成一致，并在约定的区块启用。没有节点需要重装，链也没有分裂。")
        return banner, h2, deck, "active"
    if r["agreed"]:
        ti = (waiting[0]["title"] if waiting else "a rule change")
        banner = t("The users agree on a rule change", "用户就一项规则变更达成一致")
        h2 = t(f"Agreed: {ti}", f"已达成一致：「{ti}」")
        deck = t("The vote is in. The change waits for the block named in advance, and until then the current rules apply.",
                 "投票已有结果。变更等待事先约定的区块，在此之前现行规则继续适用。")
        return banner, h2, deck, "agreed"
    if r["restarts"]:
        banner = t("The testnet starts a fresh chain", "测试网开始了一条新链")
        h2 = t("A Clean Slate for Testnet Alpha", "Testnet Alpha 从头开始")
        deck = t("The test network began again from its starting state. Tau HUD follows the new chain from its first block.",
                 "测试网从初始状态重新开始。Tau HUD 从新链的第一个区块起继续跟踪。")
        return banner, h2, deck, "restart"
    if r["proposed"]:
        n = r["proposed"]
        banner = t(f"{n} new rule change{'s' if n != 1 else ''} put to the vote", f"{n} 项新的规则变更付诸投票")
        h2 = t("The Ballot Box Is Open on Testnet Alpha", "Testnet Alpha 的投票箱已经打开")
        deck = t("A proposal is checked by logic first; only then do the votes decide. Nothing changes unless the vote agrees.",
                 "提案先经过逻辑检查，然后由投票决定。投票不通过，什么都不会改变。")
        return banner, h2, deck, "proposed"
    if r["new_nodes"]:
        n = r["new_nodes"]
        banner = t(f"{n} new node{'s join' if n != 1 else ' joins'} the testnet", f"{n} 个新节点加入测试网")
        h2 = t("More Machines Keep Watch", "更多机器加入守望")
        deck = t("Every node checks every block against the rules in force. The more there are, the more eyes on the chain.",
                 "每个节点都会按照现行规则检查每一个区块。节点越多，盯着这条链的眼睛就越多。")
        return banner, h2, deck, "nodes"
    banner = t("A steady week on Testnet Alpha", "Testnet Alpha 平稳的一周")
    h2 = t(f"{blocks} Blocks, Each Sealed by the Rules in Force", f"{blocks} 个区块，每一个都按现行规则封存")
    deck = t("No rule changed this week. The chain kept time and kept its law, which is what a rulebook on a chain is for.",
             "本周没有规则改变。链按时出块、守住它的规则，这正是写在链上的规则手册的用处。")
    return banner, h2, deck, "steady"


def lead_body(r: dict) -> list[dict]:
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
    for k, en, zh in (("proposed", "proposed", "提出"), ("agreed", "agreed", "达成一致"), ("active", "put in force", "生效"), ("dropped", "dropped", "被放弃")):
        if r[k]:
            parts_en.append(f"{r[k]} {en}")
            parts_zh.append(f"{zh} {r[k]} 项")
    if parts_en:
        out.append(t(f"On the rules themselves the users were busy: {', '.join(parts_en)}. On Tau a rule change is a transaction like any other. "
                     "It is checked by logic, voted on, and switched on at a block named in advance.",
                     f"在规则本身上，用户们并不清闲：{'，'.join(parts_zh)}。在 Tau 上，规则变更和其他交易一样是一笔交易，"
                     "先经逻辑检查，再经投票，然后在事先约定的区块启用。"))
    else:
        out.append(t("No rule change was proposed this week. The rules in force stay as the users last agreed them. "
                     "Anyone with an account may propose the next one.",
                     "本周没有人提出规则变更，现行规则仍是用户上次商定的样子。任何拥有账户的人都可以提出下一项。"))
    if r["active_titles"][1:]:
        rest = r["active_titles"][1:4]
        out.append(t("Also in force: " + "; ".join(rest) + ".", "同样已经生效：" + "；".join(f"「{x}」" for x in rest) + "。"))
    if r["restarts"]:
        out.append(t(f"The testnet started a new chain {'once' if r['restarts'] == 1 else str(r['restarts']) + ' times'} this week; balances and history began again from the starting state.",
                     f"本周测试网重新开始了 {r['restarts']} 次新链，余额和历史从初始状态重新开始。"))
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
    """The rule changes still waiting: agreed ones with their block, then the open votes."""
    head = head or 0
    agreed = [p for p in props if p.get("status") == "agreed" and (p.get("activate_at") or 0) > head]
    voting = [p for p in props if p.get("status") == "voting"]
    lines = []
    for p in sorted(agreed, key=lambda p: p["activate_at"])[:3]:
        w = eta(p["activate_at"] - head, s)
        lines.append(t(f"<b>{p['title']}.</b> Agreed; in force from block #{fmt_n(p['activate_at'])}, {w['en']}.",
                       f"<b>「{p['title']}」</b>已达成一致，自第 {fmt_n(p['activate_at'])} 号区块起生效，{w['zh']}。"))
    if voting:
        n = len(voting)
        lines.append(t(f"{n} more proposal{'s are' if n != 1 else ' is'} open for votes. Each needs its yes votes before its deadline block, or it is dropped and nothing changes.",
                       f"另有 {n} 项提案正在投票。每一项都必须在截止区块之前获得足够的赞成票，否则会被放弃，什么也不会改变。"))
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
    body = [t(f"In the simulation, where the visitors decide, {ballots} hourly rule change{'s' if ballots != 1 else ''} went to a vote of the visitors over {nd} day{'s' if nd != 1 else ''}. "
              f"They cast {fmt_n(votes)} votes, let {carried} through and turned down {turned}.",
              f"在由访客做主的模拟中，{nd} 天里共有 {ballots} 项每小时的规则变更交由访客投票。"
              f"他们投出 {fmt_n(votes)} 票，放行 {carried} 项，否决 {turned} 项。")]
    if vprops:
        body.append(t(f"Visitors also wrote {vprops} rule change{'s' if vprops != 1 else ''} of their own, and {vcarried} {'was' if vcarried == 1 else 'were'} voted in.",
                      f"访客还亲手写了 {vprops} 项规则变更，其中 {vcarried} 项获得通过。"))
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
    kick = {"active": t("Testnet Alpha · rule change", "Testnet Alpha · 规则变更"), "agreed": t("Testnet Alpha · the vote is in", "Testnet Alpha · 投票结果"),
            "restart": t("Testnet Alpha · a fresh start", "Testnet Alpha · 重新开始"), "proposed": t("Testnet Alpha · put to the vote", "Testnet Alpha · 付诸投票"),
            "nodes": t("Testnet Alpha · the network", "Testnet Alpha · 网络"), "steady": t("Testnet Alpha · the week", "Testnet Alpha · 本周")}[kind]
    return {
        "v": 1, "no": no, "date": _d(printed_at).strftime("%Y-%m-%d"), "printed": printed(printed_at),
        "start": round(r["start"]), "end": round(r["end"]), "period": period(r["start"], r["end"]),
        "head": r.get("head"), "kind": kind, "banner": banner, "teaser": deck,
        "lead": {"kick": kick, "h": h2, "deck": deck, "body": lead_body(r)},
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

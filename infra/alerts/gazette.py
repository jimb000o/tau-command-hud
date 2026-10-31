"""The Daily Consensus, weekly edition: the week on the Tau testnet as a newspaper front page (gazette/ on the site).

sim_day() keeps what the visitors did in the simulation on one UTC day (relay /sim/votes and /sim/predictions start over
at midnight, so alerts.py notes the day shortly before). edition() turns the weekly recap numbers (recap.build), the rule
changes still waiting (proposals.json) and the noted simulation days into one edition: every line in English, Chinese
and Japanese. alerts.py writes it next to the recap image every Monday as /recap/gazette/<date>.json and
/recap/gazette/latest.json; gazette/index.html sets it as the front page and the HUD shows a small notice of it.

The words stay careful: what happened is read from the chain; plans are IDNI's; testnet AGRS have no value; nothing is
offered or sold. Visitor names are the anonymous two-word names of the simulation, nothing else about anyone is known.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

ZH_WEEKDAY = "一二三四五六日"
JA_WEEKDAY = "月火水木金土日"


def fmt_n(n) -> str:
    return f"{int(round(n or 0)):,}"


def t(en: str, zh: str, ja: str) -> dict:
    return {"en": en, "zh": zh, "ja": ja}


def _d(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, timezone.utc)


def period(start: float, end: float) -> dict:
    a, b = _d(start), _d(end - 1)
    en = f"{a.day}–{b.day} {b.strftime('%B %Y')}" if a.month == b.month else f"{a.day} {a.strftime('%B')} – {b.day} {b.strftime('%B %Y')}"
    zh = f"{a.year}年{a.month}月{a.day}日至{b.month}月{b.day}日" if a.year == b.year else f"{a.year}年{a.month}月{a.day}日至{b.year}年{b.month}月{b.day}日"
    ja = f"{a.year}年{a.month}月{a.day}日〜{b.month}月{b.day}日" if a.year == b.year else f"{a.year}年{a.month}月{a.day}日〜{b.year}年{b.month}月{b.day}日"
    return t(en, zh, ja)


def printed(ts: float) -> dict:
    d = _d(ts)
    return t(f"{d.strftime('%A')}, {d.strftime('%B')} {d.day}, {d.year}", f"{d.year}年{d.month}月{d.day}日 星期{ZH_WEEKDAY[d.weekday()]}",
             f"{d.year}年{d.month}月{d.day}日 {JA_WEEKDAY[d.weekday()]}曜日")


def pace(s: float | None) -> dict:
    if not s:
        return t("—", "—", "—")
    if s < 120:
        return t(f"{s:.0f} seconds", f"{s:.0f} 秒", f"{s:.0f} 秒")
    return t(f"{s / 60:.1f} minutes", f"{s / 60:.1f} 分钟", f"{s / 60:.1f} 分")


def eta(blocks: int, s: float | None) -> dict:
    """About how long until a block, in words."""
    if not s or blocks <= 0:
        return t("soon", "很快", "まもなく")
    sec = blocks * s
    if sec < 3600:
        m = max(1, round(sec / 60))
        return t(f"in about {m} minute{'s' if m != 1 else ''}", f"约 {m} 分钟后", f"およそ {m} 分後")
    if sec < 172800:
        h = round(sec / 3600)
        return t(f"in about {h} hour{'s' if h != 1 else ''}", f"约 {h} 小时后", f"およそ {h} 時間後")
    d = round(sec / 86400)
    return t(f"in about {d} days", f"约 {d} 天后", f"およそ {d} 日後")


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
    """A small count in words, as a paper of the day would set it: 'three', '三'; larger ones in figures. Japanese papers
    set counts in figures."""
    en = NUM_EN[n] if 0 <= n < len(NUM_EN) else fmt_n(n)
    zh = (NUM_ZH[n] if n <= 10 else ("十" + NUM_ZH[n - 10] if n < 20 else fmt_n(n))) if n >= 0 else str(n)
    return t(en.capitalize() if big else en, zh, fmt_n(n))


def _fee(m) -> str:
    return m.group(1).replace(",", "")


# The proposal titles (explain.py) are written for the tracker and the alerts: "Base fee 6 → 7 AGRS", "Same rules as now
# (no real change)". The paper says the same thing the way a newspaper of the 1920s would: as a noun phrase that fits a
# headline ("a base fee of 7", "一项新的手续费公式"), with no brackets and no arrows. None means the rules stay as they are.
_PHRASES = [
    (r"^Same rules as now", None),
    (r"^Base fee [\d,]+ → ([\d,]+)(?: AGRS)?$", lambda m: t(f"a base fee of {_fee(m)}", f"基本手续费改为 {_fee(m)}", f"基本手数料 {_fee(m)} への変更")),
    (r"^Base fee ([\d,]+)(?: AGRS)?$", lambda m: t(f"a base fee of {_fee(m)}", f"基本手续费定为 {_fee(m)}", f"基本手数料を {_fee(m)} とする定め")),
    (r"^New fee formula", lambda m: t("a new formula for fees", "新的手续费公式", "新しい手数料の計算式")),
    (r"^Every validator may make blocks", lambda m: t("an open door for every validator", "所有验证者均可出块", "全バリデーターへの門戸開放")),
    (r"^Stop all block making", lambda m: t("a halt to all block making", "停止一切出块", "全ブロック生成の停止")),
    (r"^Only one validator may make blocks", lambda m: t("a single maker of blocks", "仅由一位验证者出块", "ただ一人のブロック生成者")),
    (r"^New rule for who makes blocks", lambda m: t("a new rule on who makes blocks", "关于谁来出块的新规则", "誰がブロックを生成するかの新ルール")),
    (r"^Blocks need a valid signature", lambda m: t("signed blocks only", "只认签名有效的区块", "有効な署名のあるブロックに限る定め")),
    (r"^Accept blocks without signature check", lambda m: t("blocks without a signature check", "免验签名的区块", "署名検査なしのブロック")),
    (r"^Reject all blocks", lambda m: t("the refusal of every block", "拒绝一切区块", "全ブロックの拒否")),
    (r"^New rule for valid blocks", lambda m: t("a new rule on valid blocks", "关于有效区块的新规则", "有効なブロックの新ルール")),
    (r"^Admit validator", lambda m: t("a new validator", "接纳一位新验证者", "新しいバリデーターの受け入れ")),
    (r"^Remove validator", lambda m: t("the retirement of a validator", "撤下一位验证者", "バリデーター一名の退任")),
    (r"^Votes needed: (.+)$", lambda m: t(f"a vote of {m.group(1)} for every change", f"每项变更须获 {'三分之二' if 'two' in m.group(1) else '过半'} 票数",
                                          f"すべての変更に{'3 分の 2' if 'two' in m.group(1) else '過半数'}の賛成を要する定め")),
    (r"^(\d+) rule transactions per block", lambda m: t(f"{m.group(1)} rule changes to a block", f"每个区块至多 {m.group(1)} 项规则变更", f"1 ブロックあたりルール変更 {m.group(1)} 件")),
    (r"^Fees go to", lambda m: t("a new hand to receive the fees", "手续费改由新的接收者领取", "手数料の新しい受取人")),
    (r"^Consensus switches to proof of stake", lambda m: t("a turn to proof of stake", "改行权益证明", "プルーフ・オブ・ステークへの転換")),
    (r"^Consensus switches to proof of authority", lambda m: t("a return to proof of authority", "回到权威证明", "プルーフ・オブ・オーソリティへの復帰")),
    (r"^Consensus switches to", lambda m: t("a new way of agreeing on blocks", "新的出块共识方式", "ブロックの新しい合意方式")),
    (r"^Co-signed transfers on", lambda m: t("co-signed transfers", "联署转账", "共同署名付きの送金")),
    (r"^Co-signed transfers off", lambda m: t("an end to co-signed transfers", "停用联署转账", "共同署名付き送金の廃止")),
]


def phrase(title: str | None) -> dict | None:
    """The proposal title as a headline phrase {en, zh, ja}, or None when the rules would stay as they are."""
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
            out.append(t("an amendment to the rules", "一项规则修订", "ルールの改正"))
    if not out:
        return None
    if len(out) == 1 and not more:
        return out[0]
    rest = len(out) - 1 + more
    return t(f"{out[0]['en']} and {word(rest)['en']} more amendment{'s' if rest != 1 else ''}", f"{out[0]['zh']}等 {rest + 1} 项修订",
             f"{out[0]['ja']}ほか計 {rest + 1} 件の改正")


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
     "big": t("Tau HUD Opens", "Tau HUD 开张", "Tau HUD 開業"),
     "line": t("A community instrument with a node of its own beside the founders' now shows every block, vote and rule change of Testnet Alpha.",
               "一座拥有自有节点、与创始团队节点并肩的社区观测台，如今展示 Testnet Alpha 的每一个区块、每一次投票和每一项规则变更。",
               "創設チームのノードの隣に自前のノードを持つコミュニティの観測器が、テストネット Alpha のすべてのブロック、投票、ルール変更を見せ始めた。"),
     "banner": t("Tau HUD goes live on Testnet Alpha", "Tau HUD 在 Testnet Alpha 上线", "Tau HUD、テストネット Alpha で始動"),
     "h2": t("A Community Instrument Opens, with a Node of Its Own Beside the Founders'", "社区观测台开张，自有节点与创始团队的节点并肩运行",
             "コミュニティの観測器が開業、創設チームの隣に自前のノード"),
     "deck": t("Since 26 October anyone can watch every block, vote and rule change of the Tau testnet at tauhud.com. "
               "Tau HUD is an unofficial community project, not part of IDNI.",
               "自 10 月 26 日起，任何人都可以在 tauhud.com 观看 Tau 测试网的每一个区块、每一次投票和每一项规则变更。Tau HUD 是非官方社区项目，不隶属于 IDNI。",
               "10 月 26 日から、誰でも tauhud.com で Tau テストネットのすべてのブロック、投票、ルール変更を見られるようになった。Tau HUD は非公式のコミュニティプロジェクトで、IDNI の一部ではない。"),
     "paras": [t("On 26 October a new instrument opened at tauhud.com. Tau HUD reads Testnet Alpha from a node of its own, the first beside the "
                 "founders' bootnode as far as the network shows, and lays every block, vote and rule change before anyone who cares to look. "
                 "It seals nothing and sells nothing; it is an unofficial community project, and the paper in your hands is printed on its presses.",
                 "10 月 26 日，一座新的观测台在 tauhud.com 开张。Tau HUD 从自己的节点读取 Testnet Alpha，就网络所见，这是创始团队引导节点之外的第一个节点；"
                 "它把每一个区块、每一次投票和每一项规则变更摆在任何愿意看的人面前。它不封存区块，也不出售任何东西；它是非官方社区项目，而您手中这份报纸正是在它的印刷机上印出来的。",
                 "10 月 26 日、tauhud.com に新しい観測器が開業した。Tau HUD は自前のノードからテストネット Alpha を読み取る。ネットワークで見るかぎり、創設チームのブートノードの隣に立つ最初のノードであり、"
                 "すべてのブロック、投票、ルール変更を、見たいと思う誰の前にも並べる。ブロックを生成することも、何かを売ることもない。非公式のコミュニティプロジェクトであり、あなたの手にあるこの新聞もその印刷機で刷られている。")]},
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
                    "big": t("The Vote Becomes Law", "投票成为法则", "投票、法となる"),
                    "line": (t(f"{cap(ph['en'], False)} takes effect at the appointed block; no node reinstalled, and the chain did not split.",
                               f"{ph['zh']}于约定区块生效；没有节点重装，链也没有分裂。",
                               f"{ph['ja']}が約束のブロックで施行。入れ直したノードはなく、チェーンも割れなかった。") if ph else
                             t("The users reaffirm their rules at the appointed block; no node reinstalled, and the chain did not split.",
                               "用户在约定区块重申现行规则；没有节点重装，链也没有分裂。",
                               "利用者が約束のブロックで現行ルールを再確認。入れ直したノードはなく、チェーンも割れなかった。")),
                    "banner": (t("A vote of the users becomes law", "用户的投票成为规则", "利用者の投票、法となる") if n == 1 else
                               t(f"{word(n, True)['en']} votes of the users become law", f"用户的{word(n)['zh']}项投票成为规则", f"利用者の投票 {word(n)['ja']} 件、法となる")),
                    "h2": (t(f"{cap(ph['en'])} Takes Effect at the Appointed Block", f"{ph['zh']}，于约定区块生效", f"{ph['ja']}、約束のブロックで施行") if ph else
                           t("The Users Reaffirm Their Rules at the Appointed Block", "用户在约定区块重申现行规则", "利用者、約束のブロックで現行ルールを再確認")),
                    "deck": t("Agreed by vote on Testnet Alpha and switched on at the block named in advance. No node was reinstalled and the chain did not split.",
                              "在 Testnet Alpha 上经投票达成一致，并在事先约定的区块启用。没有节点需要重装，链也没有分裂。",
                              "テストネット Alpha で投票により合意され、前もって決めたブロックで有効になった。入れ直したノードはなく、チェーンも割れなかった。"),
                    "para": (t(f"On the real testnet {ph['en']} took effect at the block the users had named, with no node reinstalled.",
                               f"在真实的测试网上，{ph['zh']}在用户约定的区块生效，没有节点需要重装。",
                               f"本物のテストネットでは、{ph['ja']}が利用者の決めたブロックで施行された。入れ直したノードはない。") if ph else None)})
    due = sim_switches(r["start"], r["end"], days or [])
    sw, down = [s for s in due if not s["down"]], sum(s["down"] for s in due)
    # news in the week the switching began, or when the visitors turned one down; a routine week's switches are only a line
    first = r["start"] <= SIM_SWITCH_SINCE < r["end"]
    if sw:
        n, kinds, votes = len(sw), {s["kind"] for s in sw}, sum(s["votes"] for s in due)
        h2 = (t("Proof of Stake by Morning, the Validator List by Evening, and Every Node Obeys", "上午权益证明，傍晚验证者名单，每个节点都照办",
                "朝はプルーフ・オブ・ステーク、夕はバリデーターリスト、全ノードが従う") if kinds == {"stake", "fixed"} else
              t("The Visitors Vote, and the Rehearsal Chain Hands the Seal to Proof of Stake", "访客投票，排练链把出块之权交给权益证明",
                "訪問者が投票、リハーサルのチェーンは生成の権をプルーフ・オブ・ステークへ") if kinds == {"stake"} else
              t("The Visitors Vote, and the Rehearsal Chain Changes Who Seals Its Blocks", "访客投票，排练链改变了由谁封存区块",
                "訪問者が投票、リハーサルのチェーンはブロックの生成者を変える"))
        s0 = sw[0]
        when = {"stake": t("half past ten on {d} morning", "{d}上午十点半", "{d}午前 10 時半"),
                "fixed": t("half past four on {d} afternoon", "{d}下午四点半", "{d}午後 4 時半")}[s0["kind"]]
        # the Chinese and Japanese open with the weekday, not a figure (the drop cap)
        wd = _d(s0["at"])
        when = t(when["en"].format(d=wd.strftime("%A")), when["zh"].format(d=f"星期{ZH_WEEKDAY[wd.weekday()]}（{wd.month}月{wd.day}日）"),
                 when["ja"].format(d=f"{JA_WEEKDAY[wd.weekday()]}曜日、{wd.month}月{wd.day}日の"))
        to = {"stake": t("from the fixed list of validators to proof of stake, where the largest holders take turns", "从固定的验证者名单转到权益证明，由持有最多的账户轮流出块",
                         "固定のバリデーターリストから、最大の保有者が交代で生成するプルーフ・オブ・ステークへ"),
              "fixed": t("from proof of stake back to the fixed list of validators", "从权益证明回到固定的验证者名单", "プルーフ・オブ・ステークから固定のバリデーターリストへ")}[s0["kind"]]
        times = (t("once", "一次", "1 回") if n == 1 else t(f"{word(n)['en']} times", f"{word(n)['zh']}次", f"{word(n)['ja']} 回"))
        answer = (t(f"the visitors answered with {fmt_n(votes)} vote{'s' if votes != 1 else ''}", f"访客以 {fmt_n(votes)} 票作答", f"訪問者は {fmt_n(votes)} 票で答え") if votes else
                  t("no visitor voted, so the simulated validators carried it themselves", "没有访客投票，于是模拟验证者自行通过",
                    "投票した訪問者はなく、シミュレーションのバリデーターが自ら可決し"))
        turned = (t(f" and turned down {word(down)['en']} of them", f"，并否决了其中{word(down)['zh']}次", f"、うち {word(down)['ja']} 回を否決し") if down else t("", "", ""))
        # the lead story when the switching is new or the visitors turned one down (2026-10-29: the consensus switch is the
        # title story); a routine week's switches are told in the Rehearsal Hall
        out.append({"kind": "simswitch", "score": 110 if first else 75 if down else -1,
                    "big": t("No Fork, No Restart", "不分叉，不重启", "フォークなし、再起動なし"),
                    "line": t("In the simulation, the visitors vote to change who seals the blocks and every simulated node obeys at the named block. "
                              "On the real testnet the rules held.",
                              "在模拟中，访客投票改变由谁封存区块，每个模拟节点都在约定的区块照办。真实的测试网上规则如常。",
                              "シミュレーションで訪問者がブロックの生成者を変える投票をし、すべてのシミュレーションのノードが約束のブロックで従った。本物のテストネットのルールは変わらず。"),
                    "banner": t("Users rewrite the chain’s law; no fork, no restart", "用户投票改写链的法则：不分叉，不重启",
                                "利用者がチェーンの法を書き換え、フォークも再起動もなし"), "extra": True,
                    "h2": h2,
                    "deck": t("On a practice chain that runs in every visitor's browser, the question of who may seal blocks went to the floor at twenty past the hour "
                              "and was law by half past. Nobody shipped software and nobody switched a machine off: Tau treats consensus as a rule like any other.",
                              "在一条于每位访客浏览器里运行的练习链上，由谁封存区块这个问题于二十分提上台面，半点即成法则。没有人发布软件，没有人关掉任何机器：在 Tau 上，共识只是一条普通的规则。",
                              "訪問者それぞれのブラウザーで動く練習用のチェーンで、誰がブロックを生成できるかという問いが毎時 20 分に議場へ上がり、30 分には法となった。ソフトウェアを配った者も、マシンを止めた者もいない。Tau にとって合意は、ほかと同じ一つのルールである。"),
                    "paras": [
                        t(f"At {when['en']}, UTC, a chain changed the law of who may seal its blocks, and nothing happened. Not the real Testnet Alpha, "
                          "whose week is told below, but its rehearsal: the simulation that runs on tauhud.com. No operator ran to a terminal, "
                          "no new software was shipped, no machine was switched off and on again. The nodes read the new rule at the agreed block and went on sealing "
                          "as before. That is the whole story, and it is why it stands at the top of this page.",
                          f"{when['zh']}（UTC），一条链改变了由谁封存区块的法则，而什么也没有发生。这不是真实的 Testnet Alpha（它这一周的情况见下文），"
                          "而是它的排练：在 tauhud.com 上运行的模拟。没有操作员奔向终端，没有新软件发布，没有机器关机重启。"
                          "节点在约定的区块读到新规则，照旧封存。这就是全部的故事，也是它登上本版之首的原因。",
                          f"{when['ja']}（UTC）、あるチェーンが誰がブロックを生成できるかの法を変えた。そして何も起きなかった。本物のテストネット Alpha（その一週間は下に記す）ではなく、"
                          "そのリハーサル、tauhud.com で動くシミュレーションでのことだ。端末へ駆けつけた運用者も、新しいソフトウェアの配布も、マシンの再起動もなかった。"
                          "ノードは約束のブロックで新しいルールを読み、これまでどおり生成を続けた。話はそれで全部であり、だからこそこの面の頭に置かれている。"),
                        t(f"The simulation is a practice copy of the testnet that runs in every visitor's browser, where the visitors hold the gavel. Twice a day it puts to them the largest question a chain can ask. This week the question was put {times['en']}; "
                          f"{answer['en']}{turned['en']}; and at the named block the seal passed {to['en']}.",
                          f"模拟是一份在每位访客浏览器里运行的测试网练习副本，由访客执槌。它每天两次向他们提出一条链所能提出的最大问题。"
                          f"本周这个问题被提出了{times['zh']}；{answer['zh']}{turned['zh']}；在约定的区块，出块之权{to['zh']}。",
                          f"シミュレーションは、訪問者それぞれのブラウザーで動くテストネットの練習用の写しで、議長の木槌を握るのは訪問者だ。1 日に 2 回、チェーンが問いうる最大の問いを彼らに投げかける。今週この問いが出されたのは {times['ja']}。"
                          f"{answer['ja']}{turned['ja']}、約束のブロックで生成の権は{to['ja']}移った。"),
                        t("On most chains that change is a hard fork: new software for every machine, and the danger that some refuse and the chain splits in two. "
                          "On Tau it is a transaction, checked by logic, carried by vote, in force at a block named in advance. The rehearsal hall runs the same law as "
                          "Testnet Alpha; the real chain only waits for its users to ask the same question.",
                          "在大多数链上，这样的变更意味着硬分叉：每台机器都要换新软件，还有人拒绝、链一分为二的危险。在 Tau 上，它只是一笔交易：经逻辑检查，经投票通过，"
                          "在事先约定的区块生效。排练厅运行的法则与 Testnet Alpha 相同；真实的链只等它的用户提出同样的问题。",
                          "たいていのチェーンでは、この変更はハードフォークになる。すべてのマシンに新しいソフトウェアを入れ、拒む者が出てチェーンが二つに割れる危険を伴う。"
                          "Tau ではそれはトランザクションであり、論理で検査され、投票で可決され、前もって決めたブロックで施行される。リハーサルの館はテストネット Alpha と同じ法で動いている。本物のチェーンは、利用者が同じ問いを投げかけるのを待つばかりだ。")]})
    if r["new_nodes"]:
        n = r["new_nodes"]
        out.append({"kind": "nodes", "score": 70,
                    "big": t("More Eyes on the Chain", "更多眼睛盯着链", "チェーンを見守る目が増える"),
                    "line": t(f"{word(n, True)['en']} more node{'s take' if n != 1 else ' takes'} up the watch; every node checks every block against the rules in force.",
                              f"又有{word(n)['zh']}个节点加入守望；每个节点都按现行规则检查每一个区块。",
                              f"見張りに加わるノードがさらに {word(n)['ja']} 台。どのノードもすべてのブロックを施行中のルールと照らして検査する。"),
                    "banner": t(f"{word(n, True)['en']} more node{'s take' if n != 1 else ' takes'} up the watch", f"又有{word(n)['zh']}个节点加入守望",
                                f"見張りのノード、さらに {word(n)['ja']} 台"),
                    "h2": t("More Machines Keep Watch over the Chain", "更多机器守望这条链", "チェーンを見守るマシンが増える"),
                    "deck": t("Every node checks every block against the rules in force. The more there are, the more eyes on the chain.",
                              "每个节点都会按照现行规则检查每一个区块。节点越多，盯着这条链的眼睛就越多。",
                              "どのノードもすべてのブロックを施行中のルールと照らして検査する。数が増えるほど、チェーンを見守る目が増える。"),
                    "para": t(f"{word(n, True)['en']} new node{'s' if n != 1 else ''} joined Testnet Alpha this week, {word(r['nodes'])['en']} community node{'s' if r['nodes'] != 1 else ''} in all.",
                              f"本周有{word(n)['zh']}个新节点加入 Testnet Alpha，社区节点共{word(r['nodes'])['zh']}个。",
                              f"今週、新しいノード {word(n)['ja']} 台がテストネット Alpha に加わり、コミュニティノードは計 {word(r['nodes'])['ja']} 台になった。")})
    if r["agreed"]:
        n = r["agreed"]
        w = next((p for p in _sorted(waiting) if phrase(p.get("title"))), None)
        if w:
            ph, at = phrase(w["title"]), fmt_n(w.get("activate_at"))
            out.append({"kind": "agreed", "score": 60,
                        "big": t("The Vote Is In", "票已点清", "開票終わる"),
                        "line": t(f"The users carry {ph['en']}; in force from block #{at}, and until then the rules in force apply.",
                                  f"用户投票通过{ph['zh']}；自第 {at} 号区块起生效，在此之前现行规则继续适用。",
                                  f"利用者が{ph['ja']}を可決。ブロック #{at} から施行され、それまでは現行ルールが適用される。"),
                        "banner": (t("The users settle a question of law", "用户以投票议定一项规则", "利用者、法の問いを一つ決する") if n == 1 else
                                   t(f"The users settle {word(n)['en']} questions of law", f"用户以投票议定{word(n)['zh']}项规则", f"利用者、法の問いを {word(n)['ja']} 件決する")),
                        "h2": t(f"Vote Carries for {cap(ph['en'], False)}, in Force from Block #{at}", f"投票通过：{ph['zh']}，自第 {at} 号区块起生效",
                                f"{ph['ja']}を可決、ブロック #{at} から施行"),
                        "deck": t("The votes are counted. The change waits for the block named in advance, and until then the rules in force apply.",
                                  "票已点清。变更等待事先约定的区块，在此之前现行规则继续适用。",
                                  "開票は終わった。変更は前もって決めたブロックを待ち、それまでは現行ルールが適用される。"),
                        "lead_only": True,
                        "para": t(f"On the real testnet the users carried {ph['en']}; it takes effect at block #{at}.",
                                  f"在真实的测试网上，用户投票通过了{ph['zh']}，将自第 {at} 号区块起生效。",
                                  f"本物のテストネットでは、利用者が{ph['ja']}を可決した。ブロック #{at} で施行される。")})
        else:
            out.append({"kind": "agreed", "score": 5,
                        "big": t("The Rules Hold", "规则如常", "ルールは変わらず"),
                        "line": t(f"{word(n, True)['en']} ballot{'s' if n != 1 else ''} keep{'s' if n == 1 else ''} the rules as they stand: practice for the voting itself.",
                                  f"{word(n)['zh']}次投票维持现行规则：这是对投票本身的练习。",
                                  f"{word(n)['ja']} 件の投票が現行ルールを維持。投票そのものの練習である。"),
                        "banner": t("Practice ballots, and the rules hold", "练习投票，规则如常", "練習の投票、ルールは変わらず"),
                        "h2": t(f"{word(n, True)['en']} Ballot{'s' if n != 1 else ''} Keep{'s' if n == 1 else ''} the Rules as They Stand", f"{word(n)['zh']}次投票维持现行规则",
                                f"{word(n)['ja']} 件の投票、現行ルールを維持"),
                        "deck": t("The users voted, and the vote changed nothing, as it was meant to: a ballot that keeps the rules tests the voting itself.",
                                  "用户投了票，而投票如预期般没有改变任何东西：维持规则的投票检验的是投票本身。",
                                  "利用者は投票し、狙いどおり何も変わらなかった。ルールを維持する投票は、投票そのものを試すものだ。"),
                        "para": None})
    if r["restarts"]:
        out.append({"kind": "restart", "score": 50,
                    "big": t("A Clean Slate", "从头开始", "一からの出直し"),
                    "line": t("The testnet begins anew from its first block; Tau HUD follows the new chain from the start.", "测试网从第一个区块重新开始；Tau HUD 从头跟踪新链。",
                              "テストネットが最初のブロックからやり直し。Tau HUD は新しいチェーンを最初から追う。"),
                    "banner": t("The testnet begins anew from its first block", "测试网从第一个区块重新开始", "テストネット、最初のブロックからやり直し"),
                    "h2": t("A Clean Slate for Testnet Alpha", "Testnet Alpha 从头开始", "テストネット Alpha、一から出直し"),
                    "deck": t("The test network began again from its starting state. Tau HUD follows the new chain from its first block.",
                              "测试网从初始状态重新开始。Tau HUD 从新链的第一个区块起继续跟踪。",
                              "テストネットワークは初期状態から再出発した。Tau HUD は新しいチェーンを最初のブロックから追っている。"),
                    "para": None})
    week = [p for p in props or [] if r["start"] <= (p.get("proposed_ts") or 0) < r["end"]]
    n = r["proposed"] - sum(1 for p in week if not phrase(p.get("title")))
    if n > 0 and not r["agreed"]:
        out.append({"kind": "proposed", "score": 30,
                    "big": t("To the Ballot Box", "付诸投票", "投票箱へ"),
                    "line": t(f"{word(n, True)['en']} amendment{'s' if n != 1 else ''} laid before the users; checked by logic first, then the votes decide.",
                              f"{word(n)['zh']}项修订提交用户表决；先经逻辑检查，再由投票决定。",
                              f"改正案 {word(n)['ja']} 件が利用者に諮られた。まず論理で検査され、そのあと票が決める。"),
                    "banner": t(f"{word(n, True)['en']} amendment{'s' if n != 1 else ''} laid before the users", f"{word(n)['zh']}项修订提交用户表决",
                                f"改正案 {word(n)['ja']} 件、利用者に諮られる"),
                    "h2": t("The Ballot Box Is Open on Testnet Alpha", "Testnet Alpha 的投票箱已经打开", "テストネット Alpha の投票箱が開く"),
                    "deck": t("A proposal is checked by logic first; only then do the votes decide. Nothing changes unless the vote agrees.",
                              "提案先经过逻辑检查，然后由投票决定。投票不通过，什么都不会改变。",
                              "提案はまず論理で検査され、それから票が決める。投票で合意されないかぎり、何も変わらない。"),
                    "para": None})
    out.append({"kind": "steady", "score": 0,
                "big": t("A Quiet Week", "平静的一周", "静かな一週間"),
                "line": t(f"{blocks} blocks, each sealed by the rules in force; no rule changed, and the chain kept its law.",
                          f"{blocks} 个区块，每一个都按现行规则封存；没有规则改变，链守住了它的法则。",
                          f"{blocks} ブロック、どれも施行中のルールで生成。ルールは変わらず、チェーンはその法を守った。"),
                "banner": t("A quiet week, and the rules hold", "平静的一周，规则如常", "静かな一週間、ルールは変わらず"),
                "h2": t(f"{blocks} Blocks, Each Sealed by the Rules in Force", f"{blocks} 个区块，每一个都按现行规则封存", f"{blocks} ブロック、どれも施行中のルールで生成"),
                "deck": t("No rule changed this week. The chain kept time and kept its law, which is what a rulebook on a chain is for.",
                          "本周没有规则改变。链按时出块、守住它的规则，这正是写在链上的规则手册的用处。",
                          "今週、ルールは何も変わらなかった。チェーンは時を刻み、法を守った。チェーン上の規則集とはそのためにある。"),
                "para": None})
    return sorted(out, key=lambda s: -s["score"])


def headline(r: dict, waiting: list[dict], days: list[dict] | None = None) -> tuple[dict, dict, dict, str]:
    """(banner, lead heading, deck, kicker key) of the week's most newsworthy story."""
    s = news(r, waiting, days)[0]
    return s["banner"], s["h2"], s["deck"], s["kind"]


def weather(r: dict) -> dict:
    """The ear on the left of the masthead: the week's chain told as a weather report."""
    pc = pace(r["pace"])
    sky = t("Fair", "晴", "晴れ") if r["pace"] and r["pace"] <= 20 else t("Calm", "平静", "穏やか")
    n = r.get("nodes") or 0
    watch = (t(f"{word(n, True)['en']} community node{'s keep' if n != 1 else ' keeps'} watch.", f"{word(n)['zh']}个社区节点守望。", f"コミュニティノード {word(n)['ja']} 台が見張る。") if n else
             t("The founders' node and Tau HUD keep watch.", "创始团队的节点与 Tau HUD 守望。", "創設チームのノードと Tau HUD が見張る。"))
    return t(f"{sky['en']}. A block about every {pc['en']}. {watch['en']} Outlook: the climate may change by vote.",
             f"{sky['zh']}。大约每 {pc['zh']}一个区块。{watch['zh']}展望：气候可经投票改变。",
             f"{sky['ja']}。およそ {pc['ja']}ごとにブロック。{watch['ja']}見通し：気候は投票で変更可能。")


def caption(r: dict) -> dict:
    blocks = ("about " if r["old_blocks"] else "") + fmt_n(r["blocks"] + r["old_blocks"])
    blocks_ja = ("約 " if r["old_blocks"] else "") + fmt_n(r["blocks"] + r["old_blocks"])
    per = period(r["start"], r["end"])
    return t(f"<b>The week at the core.</b> In the week of {per['en']}, {blocks} blocks were sealed on the testnet, each one photographed as it passed "
             "through the Tau HUD. Every point on the orbit is a node; the ring closes when the validators agree.",
             f"<b>本周的核心。</b>{per['zh']}，测试网封存了 {blocks} 个区块，每一个经过 Tau HUD 时都被摄下。轨道上的每个点都是一个节点；验证者达成一致时，圆环便合上。",
             f"<b>今週の中核。</b>{per['ja']}の一週間に、テストネットでは {blocks_ja} ブロックが生成され、どれも Tau HUD を通るときに撮影された。軌道上の点はそれぞれノード。バリデーターが合意すると輪が閉じる。")


def lead_body(r: dict, props: list[dict] | None = None, stories: list[dict] | None = None) -> list[dict]:
    """The lead story: the top story's paragraphs, the other news as 'Also this week', then the week on the chain itself."""
    stories = stories or []
    paras = lambda st: st.get("paras") or ([st["para"]] if st.get("para") else [])  # noqa: E731
    out = list(paras(stories[0])) if stories else []
    more = [p for st in stories[1:] if st["score"] > 0 and not st.get("lead_only") for p in paras(st)][:3]
    for i, p in enumerate(more):
        out.append(t(("<b>Also this week.</b> " if not i else "") + p["en"], ("<b>本周另讯。</b>" if not i else "") + p["zh"], ("<b>今週はほかにも。</b>" if not i else "") + p["ja"]))
    blocks = fmt_n(r["blocks"] + r["old_blocks"])
    pc = pace(r["pace"])
    week = [p for p in props or [] if r["start"] <= (p.get("proposed_ts") or 0) < r["end"]]
    keep = sum(1 for p in week if not phrase(p.get("title")))
    real = max(0, r["proposed"] - keep)
    carried = max(0, min(real, r["agreed"] - keep))
    quiet = not real and not r["active"] and not r["restarts"]
    en = (f"On the real chain, Testnet Alpha, the week was {'quiet and ' if quiet else ''}orderly: {'about ' if r['old_blocks'] else ''}{blocks} blocks sealed, one about every {pc['en']}, "
          f"{fmt_n(r['txs'])} transactions from {fmt_n(r['accounts'])} accounts.")
    zh = (f"真实的链 Testnet Alpha 这一周{'平静而' if quiet else ''}有序：封存{'约 ' if r['old_blocks'] else ' '}{blocks} 个区块，大约每 {pc['zh']}一个，"
          f"{fmt_n(r['accounts'])} 个账户发出 {fmt_n(r['txs'])} 笔交易。")
    ja = (f"本物のチェーン、テストネット Alpha の一週間は{'静かで' if quiet else ''}整然としていた。生成されたブロックは{'約 ' if r['old_blocks'] else ' '}{blocks}、およそ {pc['ja']}に 1 つ。"
          f"{fmt_n(r['accounts'])} のアカウントから {fmt_n(r['txs'])} 件のトランザクション。")
    nxt = next((p for p in _sorted(props or []) if p.get("status") == "agreed" and phrase(p.get("title")) and (p.get("activate_at") or 0) > (r.get("head") or 0)), None)
    at = t(f", {phrase(nxt['title'])['en']} in force from block #{fmt_n(nxt['activate_at'])}", f"，{phrase(nxt['title'])['zh']}自第 {fmt_n(nxt['activate_at'])} 号区块起生效",
           f"（{phrase(nxt['title'])['ja']}はブロック #{fmt_n(nxt['activate_at'])} から施行）") if nxt else t("", "", "")
    if real:
        en += (f" {word(real, True)['en']} rule change{'s were' if real != 1 else ' was'} proposed" + (f" and {word(carried)['en']} carried{at['en']}" if carried else "")
               + (f", {word(r['active'])['en']} put in force" if r["active"] else "") + (f", {word(r['dropped'])['en']} dropped" if r["dropped"] else "") + ".")
        zh += f"提出{word(real)['zh']}项规则变更" + (f"，通过{word(carried)['zh']}项{at['zh']}" if carried else "") + (f"，生效{word(r['active'])['zh']}项" if r["active"] else "") + (f"，放弃{word(r['dropped'])['zh']}项" if r["dropped"] else "") + "。"
        ja += f"ルール変更の提案は {word(real)['ja']} 件" + (f"、可決 {word(carried)['ja']} 件{at['ja']}" if carried else "") + (f"、施行 {word(r['active'])['ja']} 件" if r["active"] else "") + (f"、取り下げ {word(r['dropped'])['ja']} 件" if r["dropped"] else "") + "。"
    if keep:
        en += (f" {word(keep, True)['en']} {'further ' if real else ''}ballot{'s' if keep != 1 else ''} only kept the rules as they stand"
               + (": see <i>The Riddle of the Unchanging Ballots</i>." if keep >= 3 else ": practice for the voting itself."))
        zh += f"{'另有' if real else '本周有'}{word(keep)['zh']}次投票只是维持现行规则" + ("，详见《不变投票之谜》。" if keep >= 3 else "，是对投票本身的练习。")
        ja += f"{'ほかに' if real else '今週は'} {word(keep)['ja']} 件の投票が現行ルールを維持しただけだった" + ("。詳しくは<i>変わらない投票の謎</i>を。" if keep >= 3 else "。投票そのものの練習である。")
    elif not real:
        en += " No rule change was proposed; anyone with an account may propose the next one."
        zh += "没有人提出规则变更；任何拥有账户的人都可以提出下一项。"
        ja += "ルール変更の提案はなかった。アカウントを持つ人なら誰でも次の提案ができる。"
    also = [ph for ph in map(phrase, r["active_titles"][1:4]) if ph]
    if also:
        en += " Also put in force: " + "; ".join(x["en"] for x in also) + "."
        zh += "同样生效的还有：" + "；".join(x["zh"] for x in also) + "。"
        ja += "ほかに施行されたもの：" + "、".join(x["ja"] for x in also) + "。"
    if r["restarts"]:
        en += f" The testnet started a new chain {'once' if r['restarts'] == 1 else word(r['restarts'])['en'] + ' times'}; balances and history began again from the starting state."
        zh += f"测试网重新开始了{word(r['restarts'])['zh']}次新链，余额和历史从初始状态重新开始。"
        ja += f"テストネットは新しいチェーンを {word(r['restarts'])['ja']} 回始め、残高と履歴は初期状態からやり直しになった。"
    out.append(t(en, zh, ja))
    if len(out) == 1:
        out.append(t("Nothing of this needed a new version of the software. Every node read the rules from the chain and followed them, "
                     "which is the whole idea: the users decide, and the machines keep the minutes.",
                     "这一切都不需要新版本的软件。每个节点都从链上读取规则并照办，这正是全部的用意：用户做决定，机器记录在案。",
                     "このどれにも新しい版のソフトウェアは要らなかった。どのノードもチェーンからルールを読み、それに従った。それこそが肝心な点だ。利用者が決め、機械が議事録をつける。"))
    return out


def figures(r: dict) -> list[dict]:
    blocks = ("≈" if r["old_blocks"] else "") + fmt_n(r["blocks"] + r["old_blocks"])
    pc = pace(r["pace"])
    same = lambda s: t(s, s, s)  # noqa: E731
    rows = [(t("Blocks sealed", "封存的区块", "生成されたブロック"), same(blocks)),
            (t("One block about every", "大约每隔", "ブロックの間隔、およそ"), pc),
            (t("Transactions", "交易", "トランザクション"), same(fmt_n(r["txs"]))),
            (t("Accounts that sent one", "发出交易的账户", "送信したアカウント"), same(fmt_n(r["accounts"]))),
            (t("Rule changes proposed", "提出的规则变更", "提案されたルール変更"), same(str(r["proposed"]))),
            (t("Agreed by vote", "投票达成一致", "投票で合意"), same(str(r["agreed"]))),
            (t("Taken effect", "已经生效", "施行済み"), same(str(r["active"]))),
            (t("Community nodes online", "在线社区节点", "オンラインのコミュニティノード"), t(str(r["nodes"]) + (f" (+{r['new_nodes']})" if r["new_nodes"] else ""),
                                                                              str(r["nodes"]) + (f"（新增 {r['new_nodes']}）" if r["new_nodes"] else ""),
                                                                              str(r["nodes"]) + (f"（新規 {r['new_nodes']}）" if r["new_nodes"] else "")))]
    if r["restarts"]:
        rows.append((t("Fresh chains", "新链", "新しいチェーン"), same(str(r["restarts"]))))
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
                       f"<b>{ph['zh']}。</b>已经投票通过，自第 {fmt_n(p['activate_at'])} 号区块起生效，{w['zh']}。",
                       f"<b>{ph['ja']}。</b>投票で可決。ブロック #{fmt_n(p['activate_at'])} から施行、{w['ja']}。"))
    keep = [p for p in agreed if not phrase(p.get("title"))]
    if keep:
        n, first = len(keep), fmt_n(keep[0]["activate_at"])
        lines.append(t(f"<b>The rules as they stand.</b> {word(n, True)['en']} carried ballot{'s' if n != 1 else ''} to keep them unchanged "
                       + (f"falls due at block #{first}." if n == 1 else f"fall due from block #{first} onward."),
                       f"<b>维持现行规则。</b>另有{word(n)['zh']}项已通过的维持原状投票，" + (f"将在第 {first} 号区块到期。" if n == 1 else f"自第 {first} 号区块起陆续到期。"),
                       f"<b>現行ルールのまま。</b>ルールを変えずに保つ可決済みの投票 {word(n)['ja']} 件が、" + (f"ブロック #{first} で期日を迎える。" if n == 1 else f"ブロック #{first} から順に期日を迎える。")))
    if voting:
        n = len(voting)
        lines.append(t(f"{word(n, True)['en']} more proposal{'s are' if n != 1 else ' is'} open for votes. Each needs its yes votes before its deadline block, or it is dropped and nothing changes.",
                       f"另有{word(n)['zh']}项提案正在投票。每一项都必须在截止区块之前获得足够的赞成票，否则会被放弃，什么也不会改变。",
                       f"ほかに {word(n)['ja']} 件の提案が投票受付中。どれも期限のブロックまでに賛成票を集めなければ取り下げとなり、何も変わらない。"))
    if not lines:
        lines.append(t("No rule change is waiting for its block. The next one starts with a proposal; how to vote is explained at tauhud.com/vote.",
                       "目前没有等待生效的规则变更。下一项从一份提案开始；如何投票，请看 tauhud.com/vote。",
                       "施行のブロックを待っているルール変更はない。次の変更は提案から始まる。投票のしかたは tauhud.com/vote で。"))
    return {"h": t("Coming Up on the Testnet", "测试网接下来", "テストネットのこれから"), "body": lines}


def riddle(r: dict, props: list[dict]) -> dict | None:
    """An inside story when the week's ballots only kept the rules: told as a small mystery, honest that the chain is still quiet."""
    week = [p for p in props if r["start"] <= (p.get("proposed_ts") or 0) < r["end"]]
    keep = sum(1 for p in week if not phrase(p.get("title")))
    if keep < 3:
        return None
    n, N = word(keep), word(keep, True)
    return {"h": t("The Riddle of the Unchanging Ballots", "不变投票之谜", "変わらない投票の謎"), "body": [
        t(f"{N['en']} times this week a rule change went through the ballot box of Testnet Alpha, and {n['en']} times its new text "
          "decided exactly like the rules in force. The votes were counted, the blocks were sealed, and not one rule had moved.",
          f"本周，Testnet Alpha 的投票箱{n['zh']}次通过了规则变更，{n['zh']}次新文本的判定都和现行规则一模一样。票点清了，区块封存了，没有一条规则挪动过。",
          f"今週、テストネット Alpha の投票箱を {n['ja']} 回ルール変更が通り、{n['ja']} 回とも新しい文面は現行のルールとまったく同じ判定をした。票は数えられ、ブロックは生成され、ルールは一つも動かなかった。"),
        t("A paper could call that a dull week. Our correspondent calls it something else. Before a chain changes a rule that matters, someone must show that "
          "the machinery of changing one works at all: that a proposal can be written, admitted by the logic that checks it, carried by vote and sealed at the "
          f"block named in advance. {N['en']} times that machinery was wound and run, and {n['en']} times it ran true.",
          "一份报纸大可称之为乏味的一周。本报记者却另有看法。在一条链改变一项要紧的规则之前，得有人证明改变规则的机器确实能转：提案可以写出来，"
          f"能通过检查它的逻辑，能经投票通过，并在事先约定的区块封存。这台机器被上了{n['zh']}次发条、转了{n['zh']}次，{n['zh']}次都转得准。",
          "退屈な一週間と呼ぶ新聞もあるだろう。本紙の記者の見方は違う。チェーンが大事なルールを変える前に、ルールを変える仕掛けがそもそも動くことを、誰かが示さねばならない。"
          f"提案が書け、それを検査する論理に通され、投票で可決され、前もって決めたブロックで生成されること。その仕掛けは {n['ja']} 回ねじを巻かれて動き、{n['ja']} 回とも正確に動いた。"),
        t("The chain is young and its days are quiet. But the ballot box has been tried, and the first question worth asking will find it ready.",
          "这条链还年轻，日子仍然平静。但投票箱已经试过了，第一个值得一问的问题到来时，它已准备停当。",
          "チェーンはまだ若く、日々は静かだ。だが投票箱は試された。問うに値する最初の問いが来たとき、それは準備を整えて待っている。"),
    ]}


# the simulation runs on every page since 28 October 13:11 UTC (assets/sim.js): every hour a special rule change at hh:20,
# a contradicting proposal refused at the door at hh:40, a contested one dropped at its deadline at hh:58; a new chain at midnight
SIM_SINCE = datetime(2026, 10, 28, 13, 11, tzinfo=timezone.utc).timestamp()


def rehearsal(days: list[dict], r: dict | None = None, switches: bool = True) -> dict:
    """The week in the simulation as a feature in the paper's voice: the programme the clock ran, the visitors' votes,
    their own proposals, the consensus switches, the refusals at the door and the best tipster. Always marked as the
    simulation."""
    h = t("From the Rehearsal Hall", "排练厅来稿", "リハーサルの館より")
    body = []
    a = max(r["start"], SIM_SINCE) if r else 0
    hours = int((r["end"] - a) // 3600) if r and r["end"] > a else 0
    midnights = int(r["end"] // 86400 - a // 86400) if r and r["end"] > a else 0
    if hours:
        body.append(t(f"Across town from the real testnet stands a rehearsal hall: the simulation, a practice chain that runs in every visitor's browser "
                      f"and where the visitors of tauhud.com hold the gavel. This week the house played {word(hours)['en'] if hours <= 20 else fmt_n(hours)} hour{'s' if hours != 1 else ''} of its programme: "
                      "a motion on the floor every hour at twenty past, law by half past, and the visitors' verdict in between.",
                      f"在真实测试网的对街，有一座排练厅：模拟。它是一条在每位访客浏览器里运行的练习链，由 tauhud.com 的访客执槌。"
                      f"本周这座剧院上演了 {fmt_n(hours)} 个小时的节目：每小时二十分一项动议提上台面，半点即成法则，其间由访客裁决。",
                      f"本物のテストネットの向かいに、リハーサルの館が建っている。シミュレーション、すなわち訪問者それぞれのブラウザーで動く練習用のチェーンで、木槌を握るのは tauhud.com の訪問者だ。"
                      f"今週この館は {fmt_n(hours)} 時間の演目を上演した。毎時 20 分に動議が議場に上がり、30 分には法となり、その間に訪問者が裁定を下す。"))
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
                      + "。无人投票时，模拟验证者自行通过动议。",
                      f"訪問者が決めるシミュレーションでは、毎時のルール変更 {word(ballots)['ja']} 件が訪問者の投票にかけられた。投じられた票は {fmt_n(votes)}"
                      + "".join(f"、{x}" for x in ([f"可決 {word(carried)['ja']} 件"] if carried else []) + ([f"否決 {word(turned)['ja']} 件"] if turned else []))
                      + "。誰も投票しないときは、シミュレーションのバリデーターが自ら動議を可決する。"))
    elif not hours:
        body.append(t("In the simulation the visitors decide: every hour one rule change goes to their vote, and the simulated validators follow the majority. "
                      "Try it at tauhud.com in Simulation mode.",
                      "在模拟中由访客做主：每小时有一项规则变更交由他们投票，模拟验证者跟随多数。在 tauhud.com 切换到模拟模式即可参与。",
                      "シミュレーションでは訪問者が決める。毎時ルール変更が 1 件投票にかけられ、シミュレーションのバリデーターは多数に従う。tauhud.com のシミュレーションモードでお試しを。"))
    sw = [x for x in sim_switches(r["start"], r["end"], days) if not x["down"]] if r and switches else []
    if sw:
        n = len(sw)
        body.append(t(f"Twice a day the hall rewrites its own constitution. Proof of stake takes the stage at half past ten, the fixed validator list returns at half past four; "
                      f"{word(n)['en']} such change{'s' if n != 1 else ''} came into force this week, and not one machine was reinstalled.",
                      f"这座排练厅每天两次改写自己的宪章：十点半由权益证明登台，四点半固定验证者名单回归。本周共有{word(n)['zh']}次这样的切换生效，没有一台机器需要重装。",
                      f"館は 1 日に 2 回、自らの憲章を書き換える。10 時半にプルーフ・オブ・ステークが舞台に上がり、4 時半に固定のバリデーターリストが戻る。今週こうした変更が {word(n)['ja']} 回施行され、入れ直したマシンは 1 台もなかった。"))
    if vprops:
        body.append(t(f"Visitors also brought motions of their own: {word(vprops)['en']} rule change{'s' if vprops != 1 else ''} written in the Playground, "
                      f"{word(vcarried)['en']} of them voted in.",
                      f"访客还提出了自己的动议：在试验场写成的{word(vprops)['zh']}项规则变更，其中{word(vcarried)['zh']}项获得通过。",
                      f"訪問者は自分たちの動議も持ち込んだ。プレイグラウンドで書かれたルール変更 {word(vprops)['ja']} 件のうち、{word(vcarried)['ja']} 件が可決された。"))
    if hours:
        body.append(t(f"The doorkeeper had a busy week. {word(hours, True)['en'] if hours <= 20 else fmt_n(hours)} proposal{'s' if hours != 1 else ''} that contradicted the rules in force were turned away at the door before a single vote, "
                      f"because Tau checks a rule by logic first; {word(hours)['en'] if hours <= 20 else fmt_n(hours)} contested motions, backed by their proposer alone, expired at their deadline"
                      + (f"; and {word(midnights)['en']} time{'s' if midnights != 1 else ''} at midnight the stage was swept and the chain began anew." if midnights else "."),
                      f"守门人这一周很忙。{fmt_n(hours)} 项与现行规则相矛盾的提案还没投票就被拒之门外，因为 Tau 先用逻辑检查规则；"
                      f"{fmt_n(hours)} 项只有提案人支持的争议动议在截止时失效"
                      + (f"；午夜时分舞台清扫了{word(midnights)['zh']}次，链重新开始。" if midnights else "。"),
                      f"門番は忙しい一週間だった。施行中のルールと矛盾する提案 {fmt_n(hours)} 件が、1 票も投じられないうちに入口で追い返された。Tau はまず論理でルールを検査するからだ。"
                      f"提案者だけが支持する争いのある動議 {fmt_n(hours)} 件は期限で失効した"
                      + (f"。そして深夜 0 時に {word(midnights)['ja']} 回、舞台が掃き清められ、チェーンは最初からやり直した。" if midnights else "。")))
    best = max((d for d in days if d.get("best")), key=lambda d: d["best"]["points"], default=None)
    if best:
        wd = datetime.strptime(best["day"], "%Y-%m-%d")
        body.append(t(f"The sharpest forecaster of the week was {best['best']['name']}, with {best['best']['points']} points on {wd.strftime('%A')}.",
                      f"本周最准的预测者是 {best['best']['name']}，星期{ZH_WEEKDAY[wd.weekday()]}拿下 {best['best']['points']} 分。",
                      f"今週いちばん鋭い予想者は {best['best']['name']}。{JA_WEEKDAY[wd.weekday()]}曜日に {best['best']['points']} ポイントを挙げた。"))
    body.append(t("All of this happened in the simulation, not on the real testnet.", "以上都发生在模拟中，而不是真实的测试网上。",
                  "以上はすべてシミュレーションでの出来事で、本物のテストネットのことではない。"))
    return {"h": h, "body": body}


# ---------------- the café behind the paper: what the regulars talk about this week ----------------
# gazette/cafe.js adds these to the café walk: each regular says one more line on greeting and has a "this week" question.
# The facts come from the week (the same numbers as the paper); the running jokes turn with the edition number, so two quiet
# weeks still sound different. Warm and a little funny, and every answer teaches one small thing.
PIES = [t("apple", "苹果", "アップル"), t("cherry", "樱桃", "チェリー"), t("rhubarb", "大黄", "ルバーブ"), t("pecan", "山核桃", "ピーカン"),
        t("plum", "李子", "プラム"), t("pumpkin", "南瓜", "かぼちゃ"), t("blueberry", "蓝莓", "ブルーベリー"), t("peach", "桃子", "ピーチ")]
CHESS = [t("I played myself four times this week. Won twice, lost twice. I still cannot say which of us is better.",
           "这周我跟自己下了四盘。赢两盘，输两盘。到现在我也说不清我们俩谁更强。",
           "今週は自分と四局指した。二勝二敗。どちらの私が強いのか、いまだに分からん。"),
         t("On Tuesday I resigned to myself. Very gracious of me, I thought.",
           "星期二我向自己认输了。我觉得自己相当有风度。",
           "火曜日、私は自分に投了した。我ながら潔かったと思う。"),
         t("A draw again. Logic is a stern opponent when it is also you.",
           "又是和棋。当对手也是你自己时，逻辑是个严厉的对手。",
           "また引き分けだ。相手も自分となると、論理は手ごわい。"),
         t("I lost the bishop again. I suspect myself.",
           "我又丢了那个象。我怀疑是我自己干的。",
           "またビショップをなくした。犯人は私だと睨んでいる。")]
LESSONS = [t("A small lesson for your pocket: a rule and its opposite cannot both stand. One of them must go before anyone votes.",
             "给你一句随身带着的小道理：一条规则和它的反面不能同时成立。在投票之前，其中一条必须退场。",
             "ポケットに入れておく小さな教訓だ。ルールとその反対は両立しない。投票の前に、どちらかが去らねばならない。"),
           t("Here is a pretty one: if every change needs a vote, then changing how many votes are needed also needs a vote. Delightful, isn't it?",
             "这个很漂亮：如果每项变更都需要投票，那么改变需要多少票，也需要投票。妙吧？",
             "きれいな話をひとつ。どの変更にも投票が要るなら、必要な票数を変えることにも投票が要る。愉快だろう？"),
           t("Remember: the check does not say whether a rule is wise, only whether it is possible. Wisdom is still your job.",
             "记住：检查不会告诉你一条规则是否明智，只告诉你它是否可能。明智与否，仍是你的事。",
             "覚えておきなさい。検査はルールが賢いかどうかは言わない。可能かどうかだけだ。賢さは、今もあなたの仕事だ。")]
ASIDES = [t("My granddad used to say the wire is just people agreeing on what they heard. He would have liked this.",
            "我爷爷常说，电报线不过是人们对听到的东西达成一致。他会喜欢这个的。",
            "じいさんがよく言っていた。電信なんて、聞いたことについて皆が合意するだけのことだって。じいさんならこれを気に入っただろう。"),
          t("Every station on the line keeps its own copy. That is the whole trick: nobody has to trust me.",
            "线上每个站都留着自己的一份。全部的诀窍就在这儿：谁都不必信我。",
            "線上の局はどこも自分の写しを持っている。からくりはそれだけさ。誰も私を信じなくていい。"),
          t("I dream in dots and dashes some nights. Mae says that is not normal. Mae has never sat this wire.",
            "有些晚上我做梦都是点和划。梅说这不正常。梅可从没守过这条线。",
            "夜によってはトンツーの夢を見る。メイは普通じゃないと言う。メイはこの線についたことがないからな。")]
STREET = [t("My ma read it twice. She says she still don't get the blockchain part, but she likes the part where folks vote.",
            "我妈读了两遍。她说区块链那部分她还是不懂，但她喜欢大家投票的那部分。",
            "うちのおふくろは二回読んだ。ブロックチェーンのところはまだ分からないけど、みんなで投票するところは好きだってさ。"),
          t("A fella asked me if it makes you rich. I says no, mister, it's a testnet: test AGRS are for learning, not for spending. He took a paper anyway.",
            "有个家伙问我这能不能让人发财。我说不能，先生，这是测试网：测试 AGRS 是用来学习的，不是用来花的。他还是拿了一份报纸。",
            "ある旦那に、これで金持ちになれるのかって聞かれた。いいや旦那、テストネットだよ、テスト用の AGRS は学ぶためのもので、使うためじゃない。それでも旦那は一部持ってった。"),
          t("Even the cop on the corner stopped to read the headline. Then he told me to quit shouting. Then he asked for a copy.",
            "连街角的警察都停下来看标题。然后他叫我别嚷嚷了。然后他要了一份。",
            "角のお巡りまで足を止めて見出しを読んでた。それから怒鳴るなって言って、それから一部くれって。")]


# Taumorrow chess rounds (chess.taumorrow.com, an independent community project: a chess engine written in Tau, not on the testnet
# chain). The result is read from the public records (alerts.py chess_result) once they are out; until then the café says it is not in.
CHESS_ROUNDS = [{"date": "2026-11-01", "opponent": "Claude Opus 5.5", "start": datetime(2026, 11, 1, 12, tzinfo=timezone.utc).timestamp(), "games": 10,
                 "last": t("Last time, against Claude Sonnet 5.5, the engine won nine of ten, every one by checkmate.",
                           "上一次对 Claude Sonnet 5.5，引擎十盘赢了九盘，盘盘都是将死。",
                           "前回、Claude Sonnet 5.5 との対戦では、エンジンが十局中九局を勝った。どれもチェックメイトだった。")}]
CHESS_RECORDS = "https://github.com/taumorrow/taumorrow-chess-records"


def chess_score(index_md: str) -> dict | None:
    """{played, engine, model, draws} from a round's index.md in the records (one table row per game, footer "Score: engine 9 : 1 model")."""
    rows = [ln for ln in index_md.splitlines() if re.match(r"\|\s*\[P\d+\]", ln)]
    m = re.search(r"Score:\s*engine\s*([\d.½]+)\s*:\s*([\d.½]+)\s*model", index_md)
    if not rows or not m:
        return None
    draws = sum(1 for ln in rows if re.search(r"\|\s*(1/2-1/2|½-½)\s*\|", ln))
    num = lambda x: float(x.replace("½", ".5"))  # noqa: E731
    return {"played": len(rows), "engine": round(num(m.group(1)) - draws / 2), "model": round(num(m.group(2)) - draws / 2), "draws": draws}


def chess_round(end: float, found: dict | None = None) -> dict | None:
    """The round to talk about in the week ending at end (or the coming week), with the result in found merged in."""
    c = next((x for x in CHESS_ROUNDS if end - 7 * 86400 <= x["start"] < end + 7 * 86400), None)
    if not c:
        return None
    c = dict(c)
    if found and found.get("date") == c["date"]:
        c.update({k: found[k] for k in ("played", "engine", "model", "draws") if k in found})
        c["done"] = int(c.get("played") or 0) >= c["games"]
    return c

CAFE_V = 4   # raise when the talk is written differently: the edition already out is rewritten once


def chess_talk(c: dict | None, end: float) -> list[dict] | None:
    """The Professor's lines on a Taumorrow chess round: a chess engine written in Tau (an independent community project, not on the
    testnet chain) against a language model. c: {opponent, start, games, played, engine, model, draws, done, url}; None when no round
    falls in this week or the coming one."""
    if not c or not c.get("opponent") or not c.get("start") or not c.get("games"):
        return None
    start, opp, g = float(c["start"]), str(c["opponent"]), int(c["games"])
    if not (end - 7 * 86400 <= start < end + 7 * 86400):
        return None
    e, m, d, played = int(c.get("engine") or 0), int(c.get("model") or 0), int(c.get("draws") or 0), int(c.get("played") or 0)
    dr = t(f", drew {word(d)['en']}" if d else "", f"，和{word(d)['zh']}盘" if d else "", f"、引き分け {d}" if d else "")
    day = _d(start)
    wd = (day.strftime("%A"), "一二三四五六日"[day.weekday()], "月火水木金土日"[day.weekday()])
    if start >= end:
        head = t(f"On {wd[0]} a chess engine written in Tau sits down for {word(g)['en']} games against {opp}. I have already cleared my table.",
                 f"星期{wd[1]}，一个用 Tau 写的国际象棋引擎要和 {opp} 下{word(g)['zh']}盘。我已经把桌子收拾好了。",
                 f"{wd[2]}曜日、Tau で書かれたチェスエンジンが {opp} と {g} 局指す。私はもう自分の卓を片づけておいた。")
    elif not c.get("played"):
        head = t(f"On {wd[0]} a chess engine written in Tau sat down for {word(g)['en']} games against {opp}. The result is not in yet; it will be on chess.taumorrow.com.",
                 f"星期{wd[1]}，一个用 Tau 写的国际象棋引擎坐下来和 {opp} 下{word(g)['zh']}盘。结果还没出来，会公布在 chess.taumorrow.com。",
                 f"{wd[2]}曜日、Tau で書かれたチェスエンジンが {opp} と {g} 局の対戦に臨んだ。結果はまだ出ていない。chess.taumorrow.com に載るそうだ。")
    elif c.get("done") or played >= g:
        head = t(f"Did you hear? A chess engine written in Tau played {word(g)['en']} games against {opp}. It won {word(e)['en']}, lost {word(m)['en']}{dr['en']}. I have lost more than that to myself this week.",
                 f"听说了吗？一个用 Tau 写的国际象棋引擎和 {opp} 下了{word(g)['zh']}盘。赢{word(e)['zh']}盘，输{word(m)['zh']}盘{dr['zh']}。这周我输给自己的都比这多。",
                 f"聞いたかね？Tau で書かれたチェスエンジンが {opp} と {g} 局指した。{e} 勝 {m} 敗{dr['ja']}。今週、私が自分に負けた数のほうが多い。")
    else:
        head = t(f"A chess engine written in Tau is playing {word(g)['en']} games against {opp}. {word(played, True)['en']} done so far: {e} to {m}{dr['en']}. I have put my own board aside to watch.",
                 f"一个用 Tau 写的国际象棋引擎正在和 {opp} 下{word(g)['zh']}盘。目前下完{word(played)['zh']}盘：{e} 比 {m}{dr['zh']}。我把自己的棋盘放到一边看着。",
                 f"Tau で書かれたチェスエンジンが {opp} と {g} 局を指している。ここまで {played} 局で {e} 対 {m}{dr['ja']}。私は自分の盤をわきに置いて見ている。")
    return [head] + ([c["last"]] if c.get("last") and not played else []) + [
            t("The mastermind is Logix, the mind behind Taumorrow: an independent project, not something on the testnet chain. What I like: it is built on Tau, the same language the testnet writes its rules in. My hat is off to Logix.",
              "幕后主谋是 Logix，Taumorrow 背后的那个头脑：一个独立项目，不是测试网链上的东西。我喜欢的是：它建立在 Tau 之上，测试网的规则也是用这门语言写的。我向 Logix 脱帽致敬。",
              "黒幕は Logix、Taumorrow の頭脳だ。独立したプロジェクトで、テストネットのチェーンの上のものではない。私が気に入っているのは、テストネットがルールを書くのと同じ Tau という言語の上に作られていることだ。Logix には脱帽だよ。"),
            t("Its earlier games are all published move by move, so anyone can replay them and check. That is the only kind of chess I respect: the kind you do not have to take on trust.",
              "而且它以前的每一盘都一步一步公开了，谁都可以重放、核对。我只尊重这样的棋：不必凭信任去接受的那种。",
              "しかもこれまでの対局はすべて一手ずつ公開されていて、誰でも並べ直して確かめられる。私が敬意を払うのはそういうチェスだけだ。信用で受け取らなくていいチェスだ。")]


def cafe(r: dict, props: list[dict], days: list[dict], no: int, banner: dict, deck: dict, chess: dict | None = None) -> dict:
    """What the four regulars of the café walk talk about this week: {who: {greet, q, a: [...]}}, every line in three languages.
    Each answer tells one real thing of the week, why it matters to the reader, and a small lesson about exactly that thing;
    the humour comes from the regular's own corner of the café. Facts only from r and props: nothing here is made up."""
    n = max(0, int(no or 0))
    v = n % 2   # two wordings of most lines, so the same kind of week does not sound the same twice in a row
    waiting = [p for p in props if p.get("status") == "agreed" and (p.get("activate_at") or 0) > (r.get("head") or 0)]
    week_props = [p for p in props if r["start"] <= (p.get("proposed_ts") or 0) < r["end"]]
    tests = [p for p in week_props if not phrase(p.get("title"))]
    testers = len({p.get("proposer") for p in tests if p.get("proposer")})
    ph_active, ph_wait = _pick(r.get("active_titles") or []), _pick([p.get("title") for p in _sorted(waiting)])
    sim_votes = sum(int(d.get("votes") or 0) for d in days)
    pie = PIES[n % len(PIES)]
    k_t = len(tests)

    # Mae: the rules, and how they change. Her pie vote is the café's own little ballot, and the Professor always loses it.
    if r.get("active") and ph_active:
        greet_mae = t(f"Oh, and Friday's pie this week is {pie['en']}. The Professor voted lemon and lost. He says the count was fair, though. That's the whole point, isn't it?",
                      f"对了，这周五的馅饼是{pie['zh']}的。教授投了柠檬，输了。不过他说计票很公道。重点不就在这儿吗？",
                      f"そうそう、今週の金曜のパイは{pie['ja']}よ。教授はレモンに入れて負けたの。でも数え方は公正だったって。肝心なのはそこでしょ？")
        mae = [t(f"Big week, love. {cap(ph_active['en'])} took effect on Testnet Alpha, at the very block they named beforehand.",
                 f"大日子啊，亲爱的。{ph_active['zh']}在 Testnet Alpha 上生效了，就在事先说好的那个区块。",
                 f"大きな週だったわよ。{ph_active['ja']}がテストネット Alpha で施行されたの。前もって決めた、まさにそのブロックで。"),
               t("Nobody closed the shop and nobody reinstalled a thing. Enough of them said yes, and from that block on the rule was simply different.",
                 "谁也没关店，谁也没重装什么。说“同意”的人够多，从那个区块起，规则就这么不一样了。",
                 "誰も店を閉めなかったし、何も入れ直さなかった。賛成が足りて、そのブロックからルールがただ変わったの。"),
               t("Here's the bit people miss: it didn't change when they voted. It changed when they said it would. So nobody finds a surprise in their coffee.",
                 "大家常漏掉的一点是：规则不是在投票那一刻变的，而是在他们说好的那一刻变的。所以谁的咖啡里都不会冒出意外。",
                 "見落としがちなのはここ。投票した瞬間に変わったんじゃない。変わると言っておいた時に変わったの。だから誰のコーヒーにも驚きは入らない。")]
    else:
        greet_mae = [t(f"Oh, and Friday's pie this week is {pie['en']}. The Professor voted lemon again, lost again, and asked for a recount. I gave him a second slice instead.",
                       f"对了，这周五的馅饼是{pie['zh']}的。教授又投了柠檬，又输了，还要求重新计票。我干脆多给了他一块。",
                       f"そうそう、今週の金曜のパイは{pie['ja']}よ。教授はまたレモンに入れて、また負けて、数え直しを求めたの。代わりにもう一切れあげたわ。"),
                     t(f"Oh, and Friday's pie this week is {pie['en']}. Seven votes to one. Guess who the one was. He wants lemon written into the rules.",
                       f"对了，这周五的馅饼是{pie['zh']}的。七票对一票。猜猜那一票是谁投的。他想把柠檬写进规则里。",
                       f"そうそう、今週の金曜のパイは{pie['ja']}よ。七対一。その一票が誰かは分かるでしょ。レモンをルールに書き込みたいんですって。")][v]
        if ph_wait:
            mae = [t(f"They agreed on {ph_wait['en']}. It is not in force yet: it switches on at a block they named in advance.",
                     f"他们就{ph_wait['zh']}达成了一致。它还没生效：要到事先约定的那个区块才启用。",
                     f"{ph_wait['ja']}で合意したの。まだ効いてはいない。前もって決めたブロックで切り替わるのよ。"),
                   t("Same as my menu: you vote on Monday, the new pie comes on Friday. Everybody knows when, so the baker isn't the only one who's ready.",
                     "就像我的菜单：周一投票，新馅饼周五才上。大家都知道是什么时候，所以准备好的不只是烤馅饼的人。",
                     "うちのメニューと同じ。月曜に投票して、新しいパイは金曜から。いつか皆が知ってるから、準備ができてるのはパン屋だけじゃないの。")]
        elif k_t:
            who = (t("all from one wallet", "全都来自同一个钱包", "全部ひとつのウォレットから") if testers == 1 else
                   t(f"from {word(testers)['en']} wallets", f"来自{word(testers)['zh']}个钱包", f"{word(testers)['ja']} つのウォレットから")) if testers else t("", "", "")
            mae = [t(f"{word(k_t, True)['en']} rule change{'s' if k_t != 1 else ''} went through this week{', ' + who['en'] if who['en'] else ''}, and not one of them changed a thing. On purpose.",
                     f"这周通过了{word(k_t)['zh']}项规则变更{'，' + who['zh'] if who['zh'] else ''}，可没有一项真的改变了什么。是故意的。",
                     f"今週は {word(k_t)['ja']} 件のルール変更が通ったの{'、' + who['ja'] if who['ja'] else ''}。でもどれも何ひとつ変えていない。わざとよ。"),
                   [t("They're testing the voting machine, not the rules. Like me ringing the till with nothing in it, just to hear the bell.",
                      "他们测试的是投票机器，不是规则。就像我在空着的收银机上按一下，只为了听听那声铃响。",
                      "試しているのは投票の仕組みで、ルールじゃない。空っぽのレジを鳴らして、ベルの音だけ確かめるようなものね。"),
                    t("It's a fire drill. Everybody files out, counts heads, files back in, and the kitchen is exactly as it was.",
                      "这是消防演习。大家排队出去，点名，再排队回来，厨房还是原来的样子。",
                      "避難訓練よ。みんな列になって出て、人数を数えて、また戻る。厨房は元のまま。")][v],
                   t("You'll know a real one when it comes: it says what changes, and from which block. That's the first thing to read on any proposal.",
                     "真正的变更来了你会认得：它会写明改什么、从哪个区块开始。看任何提议，先看这两样。",
                     "本物が来たら分かるわ。何が変わるのか、どのブロックからか、ちゃんと書いてある。どの提案も、まずそこを読むのよ。")]
        elif r.get("proposed"):
            mae = [t(f"{word(r['proposed'], True)['en']} new proposal{'s' if r['proposed'] != 1 else ''} went up on the board this week. The regulars are still chewing.",
                     f"这周板子上贴出了{word(r['proposed'])['zh']}项新提议。常客们还在琢磨。",
                     f"今週は新しい提案が {word(r['proposed'])['ja']} 件、板に上がったわ。常連さんたちはまだ噛みしめてるところ。"),
                   t("Nobody rushes a vote in my café. A rule you will live with deserves a second cup.",
                     "在我的咖啡馆里，谁也不催着投票。一条你要跟它过日子的规则，值得再来一杯。",
                     "うちの店では誰も投票を急かさない。一緒に暮らすルールには、もう一杯の価値があるの。")]
        else:
            mae = [t("Not one proposal this week, love. The board was so empty I wrote the specials on it.",
                     "这周一项提议都没有，亲爱的。板子空得我都把今日特价写上去了。",
                     "今週は提案がひとつもなかったわ。板があんまり空いてたから、日替わりメニューを書いちゃった。"),
                   t("Quiet is fine. A good café isn't the one with the most rules. It's the one where you could change them if you wanted to.",
                     "安静也挺好。好咖啡馆不是规矩最多的那家，而是你想改规矩时就能改的那家。",
                     "静かでいいの。いい喫茶店はルールがいちばん多い店じゃない。変えたいときに変えられる店よ。")]
    if sim_votes:
        mae.append(t(f"Mind you, the visitors on the HUD cast {fmt_n(sim_votes)} practice votes in the simulation. Practice, like rehearsing a toast: nobody's actually married yet.",
                     f"对了，HUD 上的访客在模拟里投了 {fmt_n(sim_votes)} 张练习票。只是练习，就像排练祝酒词：还没有谁真的结婚。",
                     f"それにね、HUD の訪問者たちはシミュレーションで {fmt_n(sim_votes)} 票の練習投票をしたの。練習よ、乾杯の挨拶のリハーサル。まだ誰も結婚してないわ。"))

    # Elias: the wire, the blocks, the stations that keep a copy
    blocks = r["blocks"] + r.get("old_blocks", 0)
    if r.get("restarts"):
        elias = [t("We had a fresh start this week: the testnet began a new chain from block one.",
                   "这周我们重新开始了：测试网从第一个区块起了一条新链。", "今週は出直しがあった。テストネットがブロック一から新しいチェーンを始めたんだ。"),
                 t("On a test line that happens. Better it snaps here, where it's practice, than later, where it counts.",
                   "在试验线路上，这种事会发生。在这儿断，总比以后在要紧的时候断好。",
                   "試験線ではそういうこともある。切れるならここで、練習のうちに。本番で切れるよりずっといい。")]
    else:
        elias = [t(f"Steady as a clock: about one block every {pace(r.get('pace'))['en']}. Nobody winds it. The stations just keep agreeing on what comes next.",
                   f"稳得像钟一样：大约每 {pace(r.get('pace'))['zh']}一个区块。没人给它上发条，各个站只是一直对下一块达成一致。",
                   f"時計のように正確さ。だいたい {pace(r.get('pace'))['ja']}ごとにブロックがひとつ。誰もねじを巻かない。局どうしが次は何かで合意し続けてるだけだ。")]
    if r.get("new_nodes"):
        k = r["new_nodes"]
        elias.append(t(f"And {word(k)['en']} new station{'s' if k != 1 else ''} joined the line. Every station keeps its own copy of the tape.",
                       f"还有{word(k)['zh']}个新站接入了线路。每个站都保存着自己的一份纸带。",
                       f"それに新しい局が {word(k)['ja']} つ線に加わった。どの局も紙テープの写しを自分で持っている。"))
        elias.append(t("Why that matters to you: to fake a block, you'd have to fool every copy at once. Each new one makes that harder.",
                       "这对你意味着什么：想伪造一个区块，就得同时骗过每一份副本。每多一份，就更难一分。",
                       "あなたにとっての意味はこうだ。ブロックを偽るには、すべての写しを一度にだまさなきゃならない。写しが増えるほど難しくなる。"))
    elif r.get("txs"):
        elias.append(t(f"{fmt_n(r['txs'])} transactions rode along, from {fmt_n(r.get('accounts') or 0)} wallets.",
                       f"一共搭载了 {fmt_n(r['txs'])} 笔交易，来自 {fmt_n(r.get('accounts') or 0)} 个钱包。",
                       f"{fmt_n(r.get('accounts') or 0)} のウォレットから、{fmt_n(r['txs'])} 件の取引が乗ってきた。") if r.get("accounts") else
                     t(f"{fmt_n(r['txs'])} transactions rode along in them.", f"里面一共搭载了 {fmt_n(r['txs'])} 笔交易。", f"そこに {fmt_n(r['txs'])} 件の取引が乗っていた。"))
        elias.append(t("Wallets, mind, not people. One person can hold ten wallets. I only count what comes down the wire.",
                       "注意，是钱包，不是人。一个人可以有十个钱包。我只数线上过来的东西。",
                       "いいかい、ウォレットであって人じゃない。一人で十個持つこともできる。私は線を通ってきたものだけを数える。"))
    else:
        elias.append(t("Mostly empty, rolling along like a streetcar at night: nobody on board, still on time.",
                       "大多是空的，像夜里的电车一样往前开：车上没人，照样准点。", "ほとんど空っぽで、夜の路面電車みたいに走ってる。誰も乗ってないのに、時間どおりだ。"))
    elias.append(ASIDES[n % len(ASIDES)])

    # the Professor: logic. When the week gives him something to think about, his lesson is about that.
    if r.get("dropped"):
        k = r["dropped"]
        prof = [t(f"{word(k, True)['en']} proposal{'s' if k != 1 else ''} ran out of time and {'were' if k != 1 else 'was'} dropped at the deadline. Not refused: simply not enough hands.",
                  f"有{word(k)['zh']}项提议到了期限没能通过，就此作罢。不是被拒绝，只是举手的人不够。",
                  f"{word(k)['ja']} 件の提案が期限切れで取り下げられた。拒まれたのではない。手が足りなかっただけだ。"),
                t("Notice: nobody had to vote against it. Silence was enough. So no rule slips in while everyone is asleep.",
                  "注意：根本不需要有人投反对票。沉默就够了。所以没有哪条规则能趁大家睡着时溜进来。",
                  "いいかね、誰も反対票を入れる必要はなかった。沈黙で足りたのだ。だから皆が眠っている間にルールが忍び込むことはない。")]
    elif k_t:
        prof = [t(f"Those {word(k_t)['en']} changes Mae told you about? Each one, in effect, says: the rules are the rules. Perfectly true, and perfectly empty.",
                  f"梅跟你说的那{word(k_t)['zh']}项变更？每一项实际上都在说：规则就是规则。完全正确，也完全空洞。",
                  f"メイが話した {word(k_t)['ja']} 件の変更かね？どれも要するに「ルールはルールだ」と言っている。完璧に正しく、完璧に空っぽだ。"),
                t("Logicians call that a tautology: a sentence that is always true because it says nothing. Splendid for testing the machine. Useless for running a café.",
                  "逻辑学家管这叫重言式：一句因为什么都没说而永远为真的话。拿来测试机器再好不过，拿来经营咖啡馆毫无用处。",
                  "論理学者はこれをトートロジーと呼ぶ。何も言っていないから常に真である文だ。仕組みの試験には見事、喫茶店の切り盛りには役立たずだ。")]
    else:
        prof = [t("On the real chain nobody tried anything foolish this week. A pity for me, good for everyone else.",
                  "这周在真正的链上，没人试图干什么蠢事。对我来说可惜，对别人来说是好事。",
                  "今週、本物のチェーンでは誰も馬鹿な真似をしなかった。私には残念、皆には幸いだ。"),
                LESSONS[n % len(LESSONS)]]
    greet_prof = CHESS[n % len(CHESS)]
    if (c := chess_talk(chess, r["end"])):
        greet_prof, prof = c[0], (c[1:] if len(prof) < 2 else c[1:-1]) + prof   # at most four lines: the replay line goes in a busy week
    if not c:
        prof.append(t("Meanwhile, in the simulation, a contradicting proposal knocks every hour, and every hour the check sends it home before anyone votes. It never learns. I admire that, a little.",
                  "与此同时，在模拟里，每小时都有一项自相矛盾的提议来敲门，而每小时检查都会在任何人投票之前把它打发回家。它从不长记性。我有点佩服它。",
                  "一方シミュレーションでは、毎時、矛盾した提案が戸を叩き、毎時、誰かが投票する前に検査がそれを家に帰す。懲りない奴だ。少し感心している。"))

    # Sully: the headline, and what the street made of it
    head = {k: banner[k].rstrip(".!") for k in ("en", "zh", "ja")}
    if r.get("active") and ph_active:
        street = t("A fella asked me who changed the rule. I says, everybody who voted, mister. He looked at me like I'd sold him the wrong paper.",
                   "有个家伙问我是谁改的规则。我说，先生，是每个投了票的人。他看我的眼神，好像我卖错了报纸给他。",
                   "ある旦那に、誰がルールを変えたのかって聞かれた。投票した皆さんですよ、旦那って言ったら、違う新聞をつかまされたみたいな顔をしてた。")
    elif r.get("new_nodes"):
        street = t("I shout 'new station on the line!' and nobody knows what it means. Then I say 'one more witness'. That they get.",
                   "我喊“线路上来了新站！”，没人懂是什么意思。然后我说“又多了一个证人”，这下他们懂了。",
                   "「線に新しい局が来たよ！」って叫んでも誰も分からない。「証人がもう一人増えた」って言うと、それは分かってくれる。")
    else:
        street = STREET[n % len(STREET)]
    sully = [deck, street]

    q = t("What's new this week?", "这周有什么新鲜事？", "今週は何か新しいことは？")
    return {
        "mae": {"greet": greet_mae,
                "q": t("What did they vote on this week, out on the real chain?", "这周，真正的链上大家投了什么票？", "今週、本物のチェーンでは何に投票したの？"),
                "a": mae},
        "elias": {"greet": t(f"{fmt_n(blocks)} blocks came down the wire this week. My fingers know every one of them.",
                             f"这周有 {fmt_n(blocks)} 个区块从线上过来。我的手指认得每一个。",
                             f"今週は {fmt_n(blocks)} のブロックが線を通ってきた。指が一つ残らず覚えてる。"),
                  "q": t("Anything odd on the wire this week?", "这周线上有什么怪事吗？", "今週、線に何か変わったことは？"), "a": elias},
        "prof": {"greet": greet_prof, "q": t("Did the logic catch anything this week?", "这周逻辑抓到什么了吗？", "今週、論理は何か捕まえましたか？"), "a": prof},
        "sully": {"greet": t(f"This week's front page: {head['en']}. Hot off the press!", f"本周头版：{head['zh']}。刚印出来的！", f"今週の一面は「{head['ja']}」。刷りたてだよ！"),
                  "q": q, "a": sully},
    }


def edition(r: dict, props: list[dict], days: list[dict], no: int, printed_at: float, chess: dict | None = None) -> dict:
    """One weekly edition. r: recap.build(); props: proposals.json "proposals"; days: sim_day() of the week."""
    waiting = [p for p in props if p.get("status") == "agreed" and (p.get("activate_at") or 0) > (r.get("head") or 0)]
    ranked = news(r, waiting, days, props)
    top = ranked[0]
    banner, h2, deck, kind = top["banner"], top["h2"], top["deck"], top["kind"]
    kick = {"active": t("Testnet Alpha · rule change", "Testnet Alpha · 规则变更", "テストネット Alpha · ルール変更"),
            "agreed": t("Testnet Alpha · the ballot is counted", "Testnet Alpha · 计票完毕", "テストネット Alpha · 開票終了"),
            "restart": t("Testnet Alpha · a fresh start", "Testnet Alpha · 重新开始", "テストネット Alpha · 再出発"),
            "proposed": t("Testnet Alpha · put to the vote", "Testnet Alpha · 付诸投票", "テストネット Alpha · 投票へ"),
            "nodes": t("Testnet Alpha · the network", "Testnet Alpha · 网络", "テストネット Alpha · ネットワーク"),
            "steady": t("Testnet Alpha · the week", "Testnet Alpha · 本周", "テストネット Alpha · 今週"),
            "launch": t("Testnet Alpha · a new instrument", "Testnet Alpha · 新的观测台", "テストネット Alpha · 新しい観測器"),
            "simswitch": t("Simulation · not the real testnet", "模拟 · 不是真实的测试网", "シミュレーション · 本物のテストネットではない")}[kind]
    return {
        "v": 1, "no": no, "date": _d(printed_at).strftime("%Y-%m-%d"), "printed": printed(printed_at),
        "start": round(r["start"]), "end": round(r["end"]), "period": period(r["start"], r["end"]),
        "head": r.get("head"), "kind": kind, "extra": bool(top.get("extra")), "banner": banner, "teaser": deck,
        "big": top["big"], "line": top["line"],
        "lead": {"kick": kick, "h": h2, "deck": deck, "body": lead_body(r, props, ranked)},
        "weather": weather(r), "caption": caption(r),
        "figures": figures(r),
        "stories": [coming_up(props, r.get("head"), r["pace"]), rehearsal(days, r, not any(x["kind"] == "simswitch" and x["score"] > 0 for x in ranked))] + ([m] if (m := riddle(r, props)) else []),
        "cafe": cafe(r, props, days, no, banner, deck, chess), "cafe_v": CAFE_V,
        "url": "https://tauhud.com/gazette/",
        # flat copies for the HUD's notice of the paper (index.html)
        "number": no, "headline": banner["en"], "headline_zh": banner["zh"], "headline_ja": banner["ja"],
        "deck": deck["en"], "deck_zh": deck["zh"], "deck_ja": deck["ja"],
    }


def summary(e: dict) -> dict:
    """The few fields the HUD's notice and the archive list need."""
    return {"no": e["no"], "date": e["date"], "printed": e["printed"], "period": e["period"], "banner": e["banner"], "teaser": e["teaser"],
            "kind": e["kind"], "url": e["url"], "drops": e.get("drops"), "number": e["no"], "headline": e["banner"]["en"], "headline_zh": e["banner"]["zh"],
            "headline_ja": e["banner"].get("ja", ""), "deck": e["teaser"]["en"], "deck_zh": e["teaser"]["zh"], "deck_ja": e["teaser"].get("ja", "")}


# ---------------- the rule challenge: a small task each Monday, answered with a real rule in the wallet ----------------
# Answers are read from the chain: a personal rule (user_tx with operations "0") sealed while the challenge is open that
# does what the task asks. Good answers are shown on /challenge/ and in the next edition. There are no prizes.
NEUTRAL = "always((o5[t]:bv[24]={#x000001}:bv[24]))."
FREEZE = "always((o5[t]:bv[24]={#x000000}:bv[24]))."


def read_rule(text: str) -> dict | None:
    """A personal rule as the wallet writes it (wallet/index.html readRule): the conditions that stop a payment."""
    if not isinstance(text, str) or not text.strip():
        return None
    flat = re.sub(r"\s+", "", text)
    if flat == NEUTRAL:
        return None
    r = {"freeze": flat == FREEZE, "only": [], "cap": None, "from": None, "co": None}
    if r["freeze"]:
        return r
    r["only"] = list(dict.fromkeys(m.lower() for m in re.findall(r"i4\[t\]:bv\[384\]\s*=\s*\{\s*#x([0-9a-f]{96})", text, re.I)))
    if m := re.search(r"i1\[t\]:bv\[24\]\s*>=\s*\{\s*#x([0-9a-f]+)", text, re.I):
        r["cap"] = int(m.group(1), 16) - 1
    if m := re.search(r"i5\[t\]:bv\[64\]\s*<\s*\{\s*(\d+)\s*\}", text, re.I):
        r["from"] = int(m.group(1))
    lim = re.search(r"i1\[t\]:bv\[24\]\s*>\s*\{\s*#x([0-9a-f]+)", text, re.I)
    who = list(dict.fromkeys(m.lower() for m in re.findall(r"i(?:1[89]|2[0-5])\[t\]:bv\[384\]\s*=\s*\{\s*#x([0-9a-f]{96})", text, re.I)))
    if lim and who:
        r["co"] = {"limit": int(lim.group(1), 16), "who": len(who), "all": len(re.findall(r"i1\[t\]:bv\[24\]\s*>\s*\{", text)) > 1}
    if not (r["only"] or r["cap"] is not None or r["from"] is not None or r["co"]):
        return None   # not a rule shaped like the wallet's: nothing we can say about it in plain words
    return r


def parts(r: dict) -> int:
    return bool(r["only"]) + (r["cap"] is not None) + (r["from"] is not None) + bool(r["co"])


def rule_plain(r: dict) -> dict:
    """What a rule does, in plain words, three languages. Built from the parsed rule only, never from free text."""
    if r["freeze"]:
        return t("Freezes the wallet: no payment goes out.", "冻结钱包：任何付款都发不出去。", "ウォレットを凍結：支払いは一切出ない。")
    en, zh, ja = [], [], []
    if r["cap"] is not None:
        en.append(f"no payment above {fmt_n(r['cap'])} test AGRS"); zh.append(f"单笔不超过 {fmt_n(r['cap'])} 测试 AGRS"); ja.append(f"1 回 {fmt_n(r['cap'])} テスト AGRS まで")
    if r["only"]:
        n = len(r["only"])
        en.append(f"pays only {n} address{'es' if n != 1 else ''}"); zh.append(f"只付给 {n} 个地址"); ja.append(f"支払い先は {n} 件のアドレスだけ")
    if r["from"] is not None:
        d = _d(r["from"])
        en.append(f"nothing goes out before {d.day} {d.strftime('%b %Y')}"); zh.append(f"{d.year}年{d.month}月{d.day}日前不付款"); ja.append(f"{d.year}年{d.month}月{d.day}日まで支払わない")
    if r["co"]:
        c, lim = r["co"], fmt_n(r["co"]["limit"])
        if c["all"] and c["who"] > 1:
            en.append(f"above {lim} test AGRS all {c['who']} co-signers must sign"); zh.append(f"超过 {lim} AGRS 需 {c['who']} 位共同签名人全部签名"); ja.append(f"{lim} AGRS を超えると共同署名者 {c['who']} 人全員の署名が必要")
        else:
            en.append(f"above {lim} test AGRS a co-signer must sign"); zh.append(f"超过 {lim} AGRS 需一位共同签名人签名"); ja.append(f"{lim} AGRS を超えると共同署名者の署名が必要")
    s = "; ".join(en)
    return t(s[:1].upper() + s[1:] + ".", "；".join(zh) + "。", "、".join(ja) + "。")


CHALLENGES = [
    {"id": "ceiling", "fits": lambda r, ts: r["cap"] is not None and not r["freeze"],
     "title": t("A ceiling for every payment", "给每笔付款设上限", "支払いごとに上限を"),
     "task": t("Write a rule that stops any single payment above a limit you choose.", "写一条规则：任何一笔超过你所选上限的付款都会被拦下。", "自分で決めた上限を超える支払いを、1 回ごとに止めるルールを書こう。"),
     "why": t("A limit per payment is the simplest guard there is: one mistyped zero cannot empty the wallet.",
              "单笔上限是最简单的防护：多打一个零也掏不空钱包。", "1 回ごとの上限は、いちばん簡単な守り。ゼロを 1 つ打ち間違えても、ウォレットは空にならない。")},
    {"id": "friends", "fits": lambda r, ts: 1 <= len(r["only"]) <= 3,
     "title": t("Only to friends", "只付给朋友", "友だちにだけ"),
     "task": t("Write a rule that lets your wallet pay one, two or three addresses, and no one else.", "写一条规则：钱包只能付给一个、两个或三个地址，别人一概不行。", "1 つ、2 つ、または 3 つのアドレスにだけ支払えて、ほかには払えないルールを書こう。"),
     "why": t("A short list of who may be paid is how a thief's address is stopped before the money moves.",
              "一张简短的收款名单，能在钱动之前就拦住小偷的地址。", "払ってよい相手の短いリストがあれば、お金が動く前に泥棒のアドレスを止められる。")},
    {"id": "twokeys", "fits": lambda r, ts: bool(r["co"]),
     "title": t("Two keys for big payments", "大额付款要两把钥匙", "大きな支払いには鍵を 2 本"),
     "task": t("Write a rule that holds payments above a limit until another wallet co-signs them.", "写一条规则：超过上限的付款要等另一个钱包共同签名才放行。", "上限を超える支払いは、別のウォレットが共同署名するまで止めておくルールを書こう。"),
     "why": t("A second signature is how a company or a family keeps one mistaken or pressured click from moving everything.",
              "第二个签名，是公司或家庭防止一次失误或被逼迫的操作转走一切的办法。", "2 つめの署名があれば、1 回の間違いや強いられた操作ですべてを動かされずに済む。会社や家族が使うやり方だ。")},
    {"id": "until", "fits": lambda r, ts: r["from"] is not None and r["from"] > ts,
     "title": t("Hold it until a date", "到日子再说", "その日まで待つ"),
     "task": t("Write a rule that stops every payment until a date in the future you pick.", "写一条规则：在你选定的未来某天之前，所有付款都被拦下。", "自分で選んだ未来の日付まで、すべての支払いを止めるルールを書こう。"),
     "why": t("A lock with a date is a savings jar: the chain itself keeps you from spending early.",
              "带日期的锁就像存钱罐：链本身让你没法提前花掉。", "日付つきの鍵は貯金箱。早く使ってしまわないよう、チェーンそのものが見張ってくれる。")},
    {"id": "both", "fits": lambda r, ts: not r["freeze"] and parts(r) >= 2,
     "title": t("Belt and braces", "双保险", "二重の備え"),
     "task": t("Write one rule with at least two conditions, for example a limit and a list of who may be paid.", "写一条至少含两个条件的规则，比如一个上限加一张收款名单。", "条件が 2 つ以上あるルールを 1 つ書こう。たとえば上限と、払ってよい相手のリスト。"),
     "why": t("Rules combine: each condition you add closes one more way for a payment to go wrong.",
              "规则可以组合：每多加一个条件，付款出错的路就少一条。", "ルールは組み合わせられる。条件を 1 つ足すごとに、支払いが間違う道が 1 つ閉じる。")},
    {"id": "allsign", "fits": lambda r, ts: bool(r["co"]) and r["co"]["all"] and r["co"]["who"] >= 2,
     "title": t("Everyone must agree", "全体同意", "全員の同意"),
     "task": t("Write a rule where payments above a limit need the signature of every one of two or more co-signers.", "写一条规则：超过上限的付款，需要两位或更多共同签名人全部签名。", "上限を超える支払いには、2 人以上の共同署名者全員の署名が要るルールを書こう。"),
     "why": t("Agreement of all is the strictest form of the idea Tau is built on: nothing changes unless everyone says yes.",
              "全体同意是 Tau 核心理念最严格的形式：除非人人点头，否则什么都不变。", "全員の同意は、Tau の土台にある考えのいちばん厳しい形。全員が賛成しない限り、何も変わらない。")},
]
CHALLENGE_IDS = [c["id"] for c in CHALLENGES]


def challenge_of(cid: str) -> dict:
    return next((c for c in CHALLENGES if c["id"] == cid), CHALLENGES[0])


def next_challenge(cid: str | None) -> dict:
    return CHALLENGES[(CHALLENGE_IDS.index(cid) + 1) % len(CHALLENGES)] if cid in CHALLENGE_IDS else CHALLENGES[0]


def challenge_answers(blocks: dict, cid: str, since: float, until: float, limit: int = 12) -> dict:
    """The good answers: each wallet's first rule sealed in [since, until) that does what the task asks, in order."""
    c, seen, out = challenge_of(cid), set(), []
    for h in sorted(blocks):
        b = blocks[h] or {}
        ts = float((b.get("header") or {}).get("timestamp") or 0)
        if not (since <= ts < until):
            continue
        for tx in b.get("transactions") or []:
            if not isinstance(tx, dict):
                continue
            a = str(tx.get("sender_pubkey") or "").lower()
            ops = tx.get("operations") or {}
            r = read_rule(ops.get("0")) if isinstance(ops, dict) else None
            if not r or a in seen or not re.fullmatch(r"[0-9a-f]{96}", a) or not c["fits"](r, ts):
                continue
            seen.add(a)
            out.append({"addr": a, "h": h, "ts": round(ts), "plain": rule_plain(r)})
    return {"count": len(out), "answers": out[:limit]}


def challenge_block(cid: str, since: float, ends: float) -> dict:
    """The challenge as an edition and /challenge/ show it."""
    c = challenge_of(cid)
    return {"id": c["id"], "title": c["title"], "task": c["task"], "why": c["why"], "since": round(since), "ends": round(ends),
            "url": "https://tauhud.com/challenge/"}

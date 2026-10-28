/* 《共识日报》简体中文版。结构与 index.html 里的英文版一一对应：每个 class="u" 是一篇稿件。 */
window.GAZETTE_ZH = {
  name: "共识日报",
  motto: "规则经由共识而改变",
  ui: { rOut: "显示网站菜单", rIn: "全屏阅读", rFull: "全屏", rLarge: "大字版，一次一篇", rWhole: "整版", hintZoom: "<b>轻触</b>翻页 · <b>双击</b>或双指放大细读", week: "本周", weekNo: n => `周刊 · 第 ${n} 期`, weekEar: "本期所载", figures: "一周数字", founding: "创刊特稿", foundingP: "Tau 的十二年：从 2014 年的一篇论坛帖子，到一条由用户投票修改规则的链。请翻页。", weekNote: "由非官方社区项目 Tau HUD 读取公开测试网与模拟写成。测试网 AGRS 仅供练习，没有价值。每周一出版新一期；完整的“读者须知”见末版。", free: "免费赠阅", freeP: "由 Tau HUD 印行，非官方社区项目。", coverLine: "Tau 的十二年，以及一条能修改自身规则的链：十版新闻、来信、讣告与谜题。", cont: "续前", stop: "最新电讯", front: "头版", pageN: n => `第 ${n} 版`, pagesN: (a, b) => `第 ${a}–${b} 版`, of: "/ 共", tocN: n => `第 ${n} 版`, back: "‹ 上一页", turn: "翻页 ›", contents: "目录", pocket: "袖珍版", broad: "大报版", sOn: "声音 开", sOff: "声音 关", hint: "<b>点击版面</b>即可翻页 · 方向键亦可", hintTouch: "<b>轻触版面</b>即可翻页 · 也可滑动", wireWait: "正在接通节点电报线", wireOff: "节点电报线暂时无声；完整消息请见 tauhud.com", wire: (h, age) => `截至付印之时，测试网位于区块 <span class="live">#${h}</span>${age != null ? `，最近一个区块在本行排版前 ${age} 秒封存` : ""}。实时动态请见 tauhud.com。` },
  date: d => d.toLocaleDateString("zh-CN", { weekday: "long", year: "numeric", month: "long", day: "numeric", timeZone: "UTC" }),
  toc: ["头版：用户改写链的法则", "从 Zennet 出发的漫长道路", "硬分叉是什么", "沉寂四年与一个伟大方程", "一门谈论自身的语言", "工地来电：2025", "用户接过方向盘的一年", "法律如何制定 · 读者来信", "今日测试网 · 分类广告", "游艺 · 剪下收藏"],
  pages: [
/* ---------------- 1 头版 ---------------- */
`<div class="pg front">
  <div class="mast">
    <div class="ear"><b>链上天气</b>晴。约每八秒一个区块。由一位验证者值守。展望：气候可经投票改变。</div>
    <div><div class="title">{{NAME}}</div><div class="motto">{{MOTTO}}</div></div>
    <div class="ear r"><b>免费赠阅</b>由 Tau HUD 印行，非官方社区项目。测试网 AGRS 仅供练习。</div>
  </div>
  <div class="dateline"><span>第十三卷 · No. {{HEIGHT}}</span><span>{{DATE}}</span><span>tauhud.com</span></div>
  <div class="center"><span class="extra">号外</span></div>
  <div class="banner">用户投票改写链的法则：不分叉，不重启</div>
  <div class="grid">
    <div class="u s4">
      <div class="kick">Testnet Alpha · 特别报道</div>
      <h2>用户投票改变链的共识方式，所有节点自行遵从</h2>
      <div class="deck">共识从固定验证者名单切换到权益证明，又切换回来，没有重装任何一台机器。工程师称之为第一次真正展示一条由用户自己治理的区块链。</div>
      <figure class="photo"><img src="img/hud-wide.jpg" width="1100" height="450" style="height:auto;aspect-ratio:1100/450" alt="Tau HUD 屏幕的网点照片"><figcaption><b>本报镜头对准核心。</b>Tau HUD 是 tauhud.com 上的社区观测仪，测试网每封存一个区块，它都跟着记录。轨道上的每个点是一个节点；验证者同意时，圆环闭合。</figcaption></figure>
      <div class="c2"><p class="dc ni">每条区块链都有一本规则手册。在大多数链上，它被刻进软件本身，改动一行就意味着一次<i>硬分叉</i>：新软件发往每台机器，由每位运营者安装，而且始终存在有人拒绝、链一分为二的危险。</p>
      <p>Tau 网络走了另一条路。团队在八月的开发报告中介绍了几次演示，用他们的话说，社区可以<i>“修改网络法则中的某一条款，并在下一个区块生效”</i>，无需修改或重新部署任何节点。</p>
      <p>这一条款可不是小事，它就是共识本身：谁可以封存区块。用户投票从固定验证者名单转向权益证明，随后又投票转回。每一次，所有节点都在约定的区块自行切换。</p>
      <p>之所以可行，是因为规则手册就在链上。自一月起，每个区块都记录它所依据的规则快照；自五月起，共识逻辑用 Tau 语言而不是 Python 编写，所以改规则只是又一笔交易。<i>详见第 7 版。</i></p></div>
    </div>
    <div class="u s2 rl">
      <h3>十二年磨一剑</h3>
      <p class="ni">故事始于 2014 年一个名为 Zennet 的共享超级计算机，以及网络论坛上的一次谈话。2015 年它成为 Tau-Chain 与 Agoras，2017 年成为“新 Tau”，2024 年成为一门语言，2025 年成为一个运行中的测试网。<i>全文见第 2 至 7 版。</i></p>
      <hr class="rule2">
      <h3>人人皆可旁观</h3>
      <p class="ni">测试网是公开的。Tau HUD 在创始团队的引导节点旁运行自己的节点，实时展示每个区块、每次投票和每项规则变更，冷清时段另有模拟。<i>见第 9 版。</i></p>
      <hr class="rule2">
      <div class="idx"><h3>本期要目</h3>
        <p>从 Zennet 出发<span></span>2</p>
        <p>别的链为何必须分叉<span></span>3</p>
        <p>讣告<span></span>4</p>
        <p>谈论自身的语言<span></span>5</p>
        <p>2025 年的电报<span></span>6</p>
        <p>投票站里的机器<span></span>7</p>
        <p>读者来信<span></span>8</p>
        <p>分类广告<span></span>9</p>
        <p>谜题<span></span>10</p>
      </div>
      <div class="ad inv"><div class="t">不分叉！</div><p>唯一一条像俱乐部修改章程那样修改规则的链：投票、记录在案、下次会议起生效。</p></div>
    </div>
  </div>
  <div class="stop"><b>最新电讯</b><span id="wire0">{{WIRE}}</span></div>
</div>`,
/* ---------------- 2 起源 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 2 版</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">一台超级计算机、一位论坛陌生人，和一个挥之不去的想法</div>
  <div class="grid">
    <div class="u s4">
      <div class="kick">起源 · 2014 至 2017</div>
      <h2>从 Zennet 出发的漫长道路</h2>
      <div class="by">本报历史部</div>
      <div class="c2"><p class="dc ni">2014 年 8 月，一位名叫 Ohad Asor 的软件开发者在 bitcointalk 论坛上发布了 Zennet：一台公开、去中心化的超级计算机，任何人都可以出租闲置算力，并通过区块链获得报酬。</p>
      <p>Zennet 并没有一直唱主角。Asor 与一位署名 <i>HunterMinerCrafter</i> 的论坛成员讨论它时，听说了一个大得多的想法：一条规则可以由使用者自己修改的链。他从未把这个想法据为己有。</p>
      <div class="q">“Tau 的想法不是我的。我想出了 Zennet，之后遇到了 ‘Hunter Miner Crafter’……某个时候，他告诉了我关于 Tau 的想法。”<small>Ohad Asor，2016 年访谈</small></div>
      <p>2015 年 2 月，计划以 Tau-Chain（平台）和 Agoras（建于其上的市场）之名公开。Zennet 的算力市场成为 Agoras 中的一种市场。</p>
      <p>2016 年 8 月，第一支讲解影片问世。影片说，Tau 是一门自带区块链的语言，每个区块都包含接受下一个区块的条件。换句话说，网络的规则可以改变。</p>
      <p>随后是一段停顿。在一年没有博客文章之后，Asor 于 2017 年最后一天发表了《新 Tau》。目标变大了：不仅是一条规则可变的链，还要让非常大的群体在理解语义的机器帮助下讨论并达成一致。</p>
      <div class="q">“在一定假设下，我们可以实现真正高效扩展的讨论。”<small>《新 Tau》，2017 年 12 月</small></div></div>
    </div>
    <div class="u s2 rl">
      <h3>百万人的对话</h3>
      <p class="ni">让十个人就一条规则达成一致，是一场会议；让一百万人这样做，是一场骚乱。Tau 的答案是：让每位参与者用机器能读懂、能推理的语言表达自己的意愿，这样机器就能分辨谁同意谁、哪些意见互相矛盾，以及大家合起来到底说了什么。</p>
      <p>团队在 2016 年的访谈中谈到区块链的价值，答案来自中本聪：<i>“一个人人都能写入、谁也无法作弊的公共共享数据库”</i>。Tau 要为规则和知识做同样的事。</p>
      <div class="box small"><p><b>AGORAS 是什么？</b>IDNI 自 2015 年起描述的一个市场，作为日后建在 Tau 之上的一层：交易算力、经规格检验的代码和专家咨询。它仍是日后的计划，还不是产品。今天测试网上的 AGRS 仅供练习。</p></div>
      <div class="box small"><p><b>Ohad Asor 是谁？</b>IDNI 的创始人，Tau 背后的公司。一位有数学背景的开发者，据他自己说，是在开始做 Tau 之后才深入逻辑学的。</p></div>
    </div>
  </div>
</div>`,
/* ---------------- 3 硬分叉 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 3 版</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="kick">给忙碌的读者</div>
  <div class="banner sm">硬分叉是什么，以及 Tau 为何用不着它</div>
  <div class="grid">
    <div class="u full diag">
      <svg viewBox="0 0 760 250" aria-label="修改规则的两种方式">
        <defs><pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="5" stroke="#1b1813" stroke-width="1.2"/></pattern>
        <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10z" fill="#1b1813"/></marker></defs>
        <text x="0" y="22" font-size="17" font-weight="700" letter-spacing="2">老办法</text>
        <text x="0" y="40" font-size="13" font-style="italic">大多数区块链：耗时数月，还可能分裂</text>
        <g font-size="13" text-anchor="middle">
          <rect x="0" y="54" width="120" height="44" fill="none" stroke="#1b1813" stroke-width="1.5"/><text x="60" y="81">提案</text>
          <rect x="150" y="54" width="130" height="44" fill="url(#hatch)" opacity=".35"/><rect x="150" y="54" width="130" height="44" fill="none" stroke="#1b1813" stroke-width="1.5"/><text x="215" y="81" font-weight="700">数月争论</text>
          <rect x="310" y="54" width="120" height="44" fill="none" stroke="#1b1813" stroke-width="1.5"/><text x="370" y="81">新软件</text>
          <rect x="460" y="54" width="130" height="44" fill="none" stroke="#1b1813" stroke-width="1.5"/><text x="525" y="81">人人都得升级</text>
          <line x1="120" y1="76" x2="148" y2="76" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/><line x1="280" y1="76" x2="308" y2="76" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/><line x1="430" y1="76" x2="458" y2="76" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/>
          <line x1="590" y1="76" x2="625" y2="60" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/><line x1="590" y1="76" x2="625" y2="94" stroke="#1b1813" stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#ar)"/>
          <text x="694" y="64" font-weight="700">链 A</text><text x="694" y="100" font-style="italic">链 B？</text>
        </g>
        <line x1="0" y1="126" x2="760" y2="126" stroke="#1b1813" stroke-width=".8"/>
        <text x="0" y="152" font-size="17" font-weight="700" letter-spacing="2">TAU 的办法</text>
        <text x="0" y="170" font-size="13" font-style="italic">改规则只是一笔交易；链始终只有一条</text>
        <g font-size="13" text-anchor="middle">
          <rect x="0" y="184" width="120" height="44" fill="none" stroke="#1b1813" stroke-width="1.5"/><text x="60" y="211">提案</text>
          <rect x="150" y="184" width="130" height="44" fill="none" stroke="#1b1813" stroke-width="1.5"/><text x="215" y="204">逻辑检查</text><text x="215" y="220" font-size="11" font-style="italic">有矛盾？拒绝</text>
          <rect x="310" y="184" width="120" height="44" fill="none" stroke="#1b1813" stroke-width="1.5"/><text x="370" y="204">通过</text><text x="370" y="220" font-size="11" font-style="italic">经用户投票</text>
          <rect x="460" y="184" width="130" height="44" fill="#1b1813"/><text x="525" y="204" fill="#efe5cf" font-weight="700">法律</text><text x="525" y="220" font-size="11" fill="#efe5cf" font-style="italic">于预定区块生效</text>
          <line x1="120" y1="206" x2="148" y2="206" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/><line x1="280" y1="206" x2="308" y2="206" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/><line x1="430" y1="206" x2="458" y2="206" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/>
          <line x1="590" y1="206" x2="625" y2="206" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/><text x="694" y="203" font-weight="700">一条链</text><text x="694" y="219" font-size="11" font-style="italic">所有节点一起切换</text>
        </g>
      </svg>
      <div class="cap"><b>图一。</b>修改区块链规则的两种方式。本报依 Tau HUD 上“规则如何改变”一栏绘制。</div>
    </div>
    <div class="u s4 rt">
      <h2 class="l">在别的链上，代码即法律；在 Tau 上，共识即法律</h2>
      <div class="c2"><p class="ni dc">用软件写成的规则手册，麻烦在于只有程序员能打开它，而且只能靠给每个人发一份新副本。硬分叉就是这份副本的客气说法。如果拒绝的人够多，链就会分裂，两种货币从此分道扬镳，好比宣读遗嘱后反目的兄弟。</p>
      <p>Tau 把规则手册放在链里。用户用 Tau 语言（一门逻辑语言）编写规则，并像其他交易一样提交提案。提案生效之前，会先被编译，并与已生效的规则逐一比对。与它们矛盾的，在门口就被拒绝，永远到不了链上。</p>
      <p>通过检查的提案交付表决。赞成票足够时，它在事先指定的区块对所有节点同时成为法律。没有管理员密钥，也没有创始人手里的紧急开关。表决不通过，什么都不会改变。</p>
      <p>今年早些时候，一位 Tau 团队成员说得很直白：治理非常灵活，<i>“系统会按照期望的规格自行更新。”</i></p></div>
    </div>
    <div class="u s2 rl rt">
      <h3>为何要逻辑，而不只是投票？</h3>
      <p class="ni">投票可能通过荒唐的东西。两条规则各自看似合理，合在一起却可能让所有交易都无法进行。由于 Tau 语言是<i>可判定的</i>，机器总能在有限时间内回答新规则能否与旧规则并存。投票决定人们想要什么；逻辑确保它做得到。</p>
      <div class="ad"><div class="t">受够了分叉？</div><p>试试<b>逐点修订</b>，摩登新法。程序运行之时，规则同步更新。无需重装，不必在升级柜台前排队。</p><div class="fine">Tau 团队 2025 年 3 月演示。</div></div>
    </div>
  </div>
</div>`,
/* ---------------- 4 沉寂之年 + 讣告 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 4 版</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">工坊纪事：沉寂四年与一个伟大方程</div>
  <div class="grid">
    <div class="u s4">
      <div class="kick">2019 至 2022</div>
      <h2>清苦的岁月，艰深的数学</h2>
      <div class="c2"><p class="dc ni">2019 年 5 月起，月度进展报告开始发布，而且相当坦率。团队说，旧影片已经过时：“新的 Tau 非常不同”。工作转向了 TML（一门基于决策图的逻辑语言）和一个最简的讨论平台。</p>
      <p>并非每个季节都顺遂。2019 年 9 月，交易所 OpenLedger 因交易量低将 AGRS 下架，团队开始寻找别的交易场所。一款视频咨询应用 Agoras Live 宣布、延期、更名为 Tau Live，并于 2023 年 8 月暂停，好让所有人手专注核心。</p>
      <p>与此同时，地基正在浇筑。2020 年 8 月，Ohad Asor 与 Avishai Carmi 教授发表白皮书，指导了此后数年的工作。2021 年 8 月，Asor 宣布找到在任意布尔代数上求解布尔方程组的完整方法。读来像个脚注，却是今日 Tau 语言的根。</p>
      <p>2022 年 6 月，网站从 idni.org 迁到 tau.net，团队把作为工具的 TML 与新的 Tau 语言分开。后者能谈论自身的语句，也能谈论时间。一门能描述自身规则的语言，正是一条链安全修改规则所需要的。</p></div>
      <div class="box"><p><b>来信摘录，2021 年 2 月。</b>一位名叫 Victor 的读者问，Agoras 的安全是否需要权益证明。回答是：Tau 是否运行在权益证明上，<i>“将由用户决定，所以共识可以随时间按用户的意愿改变。”</i>五年半之后，在 Testnet Alpha 上，用户正是这么做的。<i>见第 1 版。</i></p></div>
    </div>
    <div class="u s2 rl obit">
      <h3>讣告</h3>
      <p class="center small" style="text-indent:0"><i>本报谨向下列各项计划致意，它们都曾尽其职守。</i></p>
      <p><b>独立项目 Zennet</b> 2014 至 2015。共享超级计算机。由 Agoras 承继，作为其中一种市场延续。</p>
      <p><b>Agoras Live，后名 Tau Live</b> 2020 至 2023。以加密货币付费的视频咨询。为让核心成长而暂停。</p>
      <p><b>作为基础的 TML</b> 至 2022 年。由更能干的继承者 Tau 语言接班。</p>
      <p><b>以 Qtum、Solana、Polkadot 为底座</b> 2023 至 2024 年间曾被考虑，最终婉拒。Tau 自建了节点。</p>
      <p><b>Z3 求解器</b> 2025 年 7 月退役，由更敏捷的 CVC5 接替。</p>
      <p><b>语言互联网</b> 让用户添加新语言的计划。2026 年 8 月安息：Tau 语言做得更好。</p>
      <p class="center small"><i>谢绝花圈。请以节点的形式捐给测试网。</i></p>
    </div>
  </div>
</div>`,
/* ---------------- 5 语言 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 5 版</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">一门谈论自身的语言在 GitHub 上放出</div>
  <div class="grid">
    <div class="u s4">
      <div class="kick">2023 至 2024</div>
      <h2>Tau 语言 Alpha 版公开发布</h2>
      <div class="deck">作者表示，它的第一个真正演示将是测试网本身</div>
      <div class="c2"><p class="dc ni">2024 年 11 月 15 日，Tau 语言以 Alpha 版在 GitHub 上公开发布。这是一门不寻常的语言。大多数编程语言告诉计算机该做什么；Tau 语言描述的是此刻以及未来每一步必须为真的东西，由求解器去找出做法。</p>
      <p>基础在前一年就已打下。2023 年 6 月，Tau 自己的链开始动工，目标是区块链的任何部分都用逻辑写成，并能随每个新区块而改变。2023 年 11 月，测试网计划定稿：从最简开始，让用户来定义什么是有效区块。</p>
      <p>团队先考虑基于 Qtum 构建，2024 年又评估了 Solana、Aptos 和 Polkadot SDK，最终决定自建节点。其间还有关于唯一用户识别的临时专利、Tau 解析器的发布，以及 2023 年 12 月加入英伟达 Inception 计划。</p>
      <p>2024 年 5 月，Asor 录制了八讲关于无原子布尔代数的课程，那是这门语言底下的逻辑。数学爱好者可在 Tau 频道找到。其余读者请注意，测试网是更友好的入门。</p></div>
    </div>
    <div class="u s2 rl">
      <h3>请教逻辑学家</h3>
      <p class="ni"><b>问：</b>“可判定”是什么意思，我为何要在意？</p>
      <p class="ni"><b>答：</b>意思是，关于你的规则的问题，机器总能给出是或否，绝不会永远卡住。这就是为什么一条 Tau 链能在每条新规则生效之前，把它与所有现行规则比对，每次都能。</p>
      <p class="ni"><b>问：</b>那“谈论自身”呢？</p>
      <p class="ni"><b>答：</b>这门语言能把自己的语句当作推理的对象。一条规则可以关于其他规则，包括关于“如何修改规则”的规则。</p>
      <div class="ad"><div class="t">Alpha 版问世</div><p>TAU 语言。说清什么必须为真，让求解器找出路径。来者皆可免费使用。</p><div class="fine">github.com/IDNI/tau-lang</div></div>
    </div>
    <div class="u full rt">
      <div class="box"><h3>新式立法文书样本</h3>
        <div class="grid" style="grid-template-columns:3fr 2fr">
          <div class="u"><p class="ni wire" style="white-space:pre-line">always (
  o6[t] = i10[t]  &amp;&amp;
  o7[t] = { 1 }
)</p></div>
          <div class="u rl"><p class="ni small">摘自测试网共识规则的最简形式。读作：<i>每一步，区块有效当且仅当其签名验证通过，且每位获授权的提议者都可以封存区块。</i>经投票修改这几行，网络就改变了达成共识的方式。</p></div>
        </div>
      </div>
    </div>
  </div>
</div>`,
/* ---------------- 6 2025 电报 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 6 版</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">十二个月，一个网络：来自建设工地的电报</div>
  <div class="grid">
    <div class="u s3 wire">
      <div class="kick">专电 · 2025 年</div>
      <p><b>一月</b> 测试网核心规则已用 TAU 规格写成 完 约三成测试网以 TAU 编写 完 相同输入得出相同输出 完</p>
      <p><b>三月</b> 逐点修订成功 完 运行中的程序接收更新并一致地并入下一步 完 规则从此这样改变 完</p>
      <p><b>四月</b> 美国专利获批 完 节点设计确定 完 外壳只通过输入输出流与 TAU 通话 完</p>
      <p><b>五月</b> 每笔交易改由 TAU 裁决 完 有效交易进入内存池等候 完</p>
      <p><b>六月</b> 十二个里程碑路线图 完 控制台钱包 完 一笔交易可同时携带规则与转账 完</p>
      <p><b>七月</b> 区块产出并存储 完 哈希相链 默克尔根 完 求解器由 Z3 换为 CVC5 完</p>
    </div>
    <div class="u s3 rl wire">
      <div class="kick">续</div>
      <p><b>八月</b> 节点启动时从历史重建状态 完 支持任意位宽的数 完</p>
      <p><b>九月</b> 采用 LIBP2P 点对点联网 完 安卓钱包可发送 TAU 规则 完</p>
      <p><b>十月</b> 从单节点到网络 完 六项 TAU 协议 完 同步依次为握手 区块头 区块 状态 然后广播 完</p>
      <p><b>十一月</b> 测试网代码对公众开放 完 仓库 TAU-TESTNET 完 节点保有身份 完</p>
      <p><b>十二月</b> 首批权威证明区块 完 BLS 签名 完 每个区块附状态哈希签名 完 新年快乐 完</p>
      <p class="center" style="margin-top:.8em">· · ·</p>
    </div>
    <div class="u s4 rt">
      <h2 class="l">使这一切成为可能的诀窍</h2>
      <div class="c2"><p class="ni dc">这一年的电报里，三月那封最值得裱起来。逐点修订是一种方法：运行中的 Tau 程序接收一串更新，并把其中写下的内容一致地并入下一步的程序。</p>
      <p>想象一列火车，时刻表可以在行驶途中修订，而它到达下一站时已经按新时刻表运行：不停车，不重造，也不会有两节车厢各按各的时刻表走。这就是 Tau 上的一次规则变更。</p>
      <p>2025 年的其余工作，都是围绕这列火车修铁路：交易、区块、存储、联网、签名。到十二月，各部分已在一个公开网络上协同运行。</p></div>
    </div>
    <div class="u s2 rl rt">
      <figure class="photo"><img src="img/hud-core.jpg" width="700" height="574" style="height:auto;aspect-ratio:700/574" alt="Tau HUD 上链核心的网点照片"><figcaption><b>核心夜景。</b>封存的区块在中央发光；验证者和节点沿圆环运行。摄于 Tau HUD。</figcaption></figure>
    </div>
  </div>
</div>`,
/* ---------------- 7 2026 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 7 版</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">用户接过方向盘的一年</div>
  <div class="grid">
    <div class="u s4">
      <div class="kick">2026 · 编年</div>
      <h2>从“演示”到可编程货币</h2>
      <div class="c2"><p class="dc ni">一月以兑现承诺开场：每个区块现在都记录它所依据的确切规则快照，新加入的节点可以核对状态哈希，而不必重放全部历史。二月，团队为这一年定下格言：Testnet Alpha <i>就是</i>演示。</p>
      <p>四月带来了分叉选择与链重组、唯一的规范链，以及与内置检查并列的用户自定义策略检查。五月迈出决定性一步：共识从 Python 移入 Tau 逻辑，用户可以用规则修改它；同时推出了管理节点、密钥和投票的开发者命令行。</p>
      <p>八月，用户真的改了它。他们通过投票从固定验证者名单切换到权益证明再切回，没有重新部署任何节点。验证者名单本身如今也存在于 Tau 逻辑中。</p>
      <p>九月宣布进入产品阶段：带规则模板与分享功能的简易钱包模式，另有两项专利获批。十月，联署转账上线：大额支付需要多方批准，期限以任何时钟都伪造不了的区块数计算。一个常用规格的加载时间从 68 秒降到 2.4 秒。</p>
      <p>主网和 Agoras 仍是团队路线图上的计划。难得的是，这一次路看得见。</p></div>
    </div>
    <div class="u s2 rl">
      <h3>说白话，链来记下</h3>
      <p class="ni">七月展示的钱包构建模式，让用户用日常英语描述一条规则。代理把它写成 Tau，用户签名，然后像其他规则一样提交并被接受。</p>
      <div class="q">“它把你用白话说的内容转成 Tau 语言，剩下的交给 Tau。”<small>Tau 团队，2026 年 7 月问答</small></div>
    </div>
    <div class="u full rt">
      <div class="kick">科学</div>
      <h2>投票站里的机器</h2>
      <div class="c3"><p class="ni dc">六月，测试网经受了一场不寻常的考验。用团队的话说，他们搭建了<i>“一个完整的代理群，每个代理都有自己的身份、护栏和目标”</i>，让它们以用户和验证者的身份在网络上活动。</p>
      <p>代理们提出规则、对规则投票、互相转账，尽可能贴近真实。一个守卫代理在提案继续推进前先行审查。</p>
      <p>结果有两点。网络顶住了压力；治理也变得可追责：链上的每条规则如今都能追溯到是谁提出、如何被批准。</p>
      <p>这让人一窥 Tau 一直以来的初衷：人们以及为人们工作的机器，用一种可以被检验的语言说明自己想要什么。</p>
      <p>无论将来的投票者是男是女还是机器，规则手册只有一本，链也只有一条。</p></div>
    </div>
  </div>
</div>`,
/* ---------------- 8 公民课 + 来信 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 8 版</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">Tau 上的法律是如何制定的</div>
  <div class="grid">
    <div class="u full diag">
      <svg viewBox="0 0 760 150" aria-label="提议、检查、同意、成法">
        <defs><marker id="ar2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10z" fill="#1b1813"/></marker></defs>
        <g font-size="14" text-anchor="middle">
          <circle cx="80" cy="56" r="40" fill="none" stroke="#1b1813" stroke-width="1.6"/><text x="80" y="52" font-size="26" font-weight="700">壹</text><text x="80" y="74" font-size="13">提议</text>
          <circle cx="280" cy="56" r="40" fill="none" stroke="#1b1813" stroke-width="1.6"/><text x="280" y="52" font-size="26" font-weight="700">贰</text><text x="280" y="74" font-size="13">检查</text>
          <circle cx="480" cy="56" r="40" fill="none" stroke="#1b1813" stroke-width="1.6"/><text x="480" y="52" font-size="26" font-weight="700">叁</text><text x="480" y="74" font-size="13">同意</text>
          <circle cx="680" cy="56" r="40" fill="#1b1813"/><text x="680" y="52" font-size="26" font-weight="700" fill="#efe5cf">肆</text><text x="680" y="74" font-size="13" fill="#efe5cf">成法</text>
          <line x1="124" y1="56" x2="234" y2="56" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar2)"/><line x1="324" y1="56" x2="434" y2="56" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar2)"/><line x1="524" y1="56" x2="634" y2="56" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar2)"/>
          <text x="80" y="118" font-size="13">用 Tau 写一条规则，</text><text x="80" y="134" font-size="13">作为交易发出</text>
          <text x="280" y="118" font-size="13">与现行法律一起编译；</text><text x="280" y="134" font-size="13">有矛盾者出局</text>
          <text x="480" y="118" font-size="13">用户投票；赞成票</text><text x="480" y="134" font-size="13">足够即获通过</text>
          <text x="680" y="118" font-size="13">在预先指定的区块</text><text x="680" y="134" font-size="13">对所有节点生效</text>
        </g>
      </svg>
    </div>
    <div class="u full rt"><div class="kick">通信</div><h2>读者来信</h2><p class="center small" style="text-indent:0"><i>摘自读者向 Tau 团队月度问答提出的问题及团队答复，略有删节。</i></p></div>
    <div class="u s3">
      <p class="ni"><b>编辑先生：</b>链上治理是私密的吗？网络运转需要可信第三方吗？<i>Levan</i></p>
      <p class="ni small"><b>答复：</b>起初不是私密的，但用户愿意的话可以让它私密。可信第三方并非必需。“治理非常灵活，用户可以规定系统该如何运作，系统会自行更新。”<i>（2026 年 1 月）</i></p>
      <hr class="rule2">
      <p class="ni"><b>编辑先生：</b>Tau 区块链必须使用单一的全局账户状态吗？还是可以采用扩展性更好的分片模型？<i>Phillip</i></p>
      <p class="ni small"><b>答复：</b>“我们会从全局账户状态开始，但原则上，用户要改它应该没有任何问题。”<i>（2026 年 1 月）</i></p>
    </div>
    <div class="u s3 rl">
      <p class="ni"><b>编辑先生：</b>目前的工作只是愿景中受限的一部分吗？主网之前还剩什么？<i>Kurosawa</i></p>
      <p class="ni small"><b>答复：</b>“核心愿景已经在 Tau 语言中实现，也已在区块链中实现。当然还有很多要改进，但它已经在那里，已经在运行。”<i>（2026 年 8 月）</i></p>
      <hr class="rule2">
      <p class="ni"><b>编辑先生：</b>Tau 语言何时能推出带表格和算术、足以供真正开发者使用的 1.0 版？<i>Kudo Sara</i></p>
      <p class="ni small"><b>答复：</b>核心功能已近完备，算术已经上线。接下来是完整的时序逻辑量词，然后是表格。<i>（2026 年 7 月）</i></p>
    </div>
    <div class="u s2 rt">
      <p class="ni"><b>编辑先生：</b>像 Tau 这样的系统有可能审查吗？<i>Bobby</i></p>
      <p class="ni small"><b>答复：</b>“如果用户决定某件事会发生，那它就会发生。这正是全部意义所在。”<i>（2023 年 1 月）</i></p>
    </div>
    <div class="u s2 rl rt">
      <p class="ni"><b>编辑先生：</b>报上满是量子计算机破解密钥的消息。Tau 如何应对？<i>Agoras Tau</i></p>
      <p class="ni small"><b>答复：</b>短期内不重复使用地址和密钥；长期则把签名迁移到后量子方案。<i>（2026 年 6 月）</i></p>
    </div>
    <div class="u s2 rl rt">
      <p class="ni"><b>编辑先生：</b>Tau 能否成为 AI 代理网络的通信层？<i>Smick</i></p>
      <p class="ni small"><b>答复：</b>可以，“但不是作为传递闲聊的电线，而是作为代理们就何为真实、何为允许达成一致的那一层。”<i>（2026 年 6 月）</i></p>
    </div>
  </div>
</div>`,
/* ---------------- 9 今日 + 分类广告 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 9 版</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">今日测试网</div>
  <div class="grid">
    <div class="u s4">
      <div class="kick">本报驻节点记者</div>
      <h2>一条公开的链，向所有旁观者开放</h2>
      <div class="c2"><p class="dc ni">Testnet Alpha 公开运行，本报记者在旁听席上有个座位。Tau HUD 在 IDNI（Tau 背后的公司）的引导节点旁运行着自己的节点，并把所见付印。</p>
      <p>目前由 IDNI 运营的唯一一位验证者封存每个区块，大约每八秒一个。用户以交易形式提出规则变更，提案收集投票，一旦通过便等待生效的那个区块。HUD 会提前显示、倒数计时，并在生效时点亮圆环。</p>
      <p>冷清时段另有一个遵循同一协议的模拟，每小时安排一次事件，每天两次切换共识。它出现的地方都标成琥珀色，免得有人把彩排当成正戏。</p>
      <div class="box wire"><p class="ni" id="wire1">{{WIRE}}</p></div></div>
    </div>
    <div class="u s2 rl">
      <h3>观看指南</h3>
      <div class="watch">
        <p><a href="/?lang=zh" data-noflip>链核心，实时</a> <i>tauhud.com</i></p>
        <p><a href="/proposals/" data-noflip>规则变更与投票</a> <i>/proposals</i></p>
        <p><a href="/explorer/" data-noflip>每个区块和交易</a> <i>/explorer</i></p>
        <p><a href="/history/" data-noflip>逐块时间旅行</a> <i>/history</i></p>
        <p><a href="/playground/" data-noflip>亲手写一条规则</a> <i>/playground</i></p>
        <p><a href="/chronicle/" data-noflip>完整编年史</a> <i>/chronicle</i></p>
      </div>
      <div class="ad inv"><div class="t">电报服务</div><p>每项通过的规则变更、每次生效、每个新节点，发生的那一刻就送到你的口袋里。</p><p><a href="https://t.me/tauHUDcom" target="_blank" rel="noopener" data-noflip>t.me/tauHUDcom</a></p></div>
    </div>
    <div class="u full rt"><h3 style="text-align:left;border-bottom:1px solid;padding-bottom:.2em">分类广告</h3></div>
    <div class="u s2 cls">
      <p><b>招聘。</b>诚招作风稳健的节点运营者。运行一个 Tau 节点，三十分钟内出现在本报轨道上。工具包及说明见 <a href="/nodes/" data-noflip>tauhud.com/nodes</a>。</p>
      <p><b>求职。</b>验证者，守时，每块必签，求一席位。网络通过的任何规则一概遵守。</p>
    </div>
    <div class="u s2 rl cls">
      <p><b>失物。</b>硬分叉一个。无人想念。拾得者可自行留用。</p>
      <p><b>告示。</b>测试网 AGRS 毫无价值。它们只用于试用测试网，本报既不提供也不出售。</p>
      <p><b>致好奇者。</b>在<a href="/playground/" data-noflip>试验场</a>提交一条规则，安全地看着链接受或拒绝它。</p>
    </div>
    <div class="u s2 rl cls">
      <p><b>寻人。</b>致论坛成员 HunterMinerCrafter：您 2014 年提出的那个想法已经走了很远。今天运行的是一套不同的设计，但它始于那次讨论。欢迎来看看。</p>
      <p><b>建设者。</b>测试网代码已公开。可通过 GitHub 联系团队；仅十月就合并了四个社区拉取请求。</p>
    </div>
    <div class="u full rt"><div class="box"><div class="grid" style="grid-template-columns:repeat(3,minmax(0,1fr))">
      <div class="u"><h3>历书</h3><p class="ni small">按每块八秒计，测试网每小时封存约 450 个区块，每天约 10,800 个。今天通过的规则通常设定在若干区块之后生效，所以大家都能提前知道时辰。</p></div>
      <div class="u rl"><h3>彩排时刻表</h3><p class="ni small">在模拟中，每小时二十分提出一项特别规则变更，半点生效。共识在 UTC 10:30 切换为权益证明，UTC 16:30 切回固定名单。彩排在午夜从头开始。</p></div>
      <div class="u rl"><h3>敬告读者</h3><p class="ni small">Tau HUD 是非官方社区项目，与 IDNI 无关。它读取公开测试网并报道所见。两者不一致时，以链为准，本报为误。</p></div>
    </div></div></div>
  </div>
</div>`,
/* ---------------- 10 游艺 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 10 版</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">逻辑头脑的消遣</div>
  <div class="grid">
    <div class="u s3">
      <h3>三位验证者之谜</h3>
      <p class="ni">某条链上，规则变更需要三位验证者中<i>过半数</i>同意。Ada 投赞成。Cleo 总是跟 Ada 投得一样。Bram 出于原则，总是跟 Cleo 唱反调。变更能通过吗？</p>
      <div class="ups"><p><b>答案：</b>能。Ada 和 Cleo 赞成，Bram 反对：三票中两票，过半。建议 Bram 另找一条原则。</p></div>
    </div>
    <div class="u s3 rl">
      <h3>矛盾角</h3>
      <p class="ni">同一天有三项提案送到一条 Tau 链。哪一项会在门口被拒绝？</p>
      <p class="ni small">（甲）超过 1,000 AGRS 的转账需要两个签名。<br>（乙）基础手续费恒为 6。<br>（丙）在（乙）生效期间，基础手续费恒为 7。</p>
      <div class="ups"><p><b>答案：</b>（丙）。它与（乙）矛盾，所以在任何投票之前就被编译检查拒绝。（甲）和（乙）可以共存。</p></div>
    </div>
    <div class="u full rt gl"><h3 style="text-align:left">新读者词汇表</h3>
      <div class="c3"><p><b>Agoras。</b>IDNI 计划日后建在 Tau 之上的市场。在测试网上，AGRS 只是没有价值的测试单位。</p>
      <p><b>区块。</b>链上账本封存的一页。在 Tau 上，每个区块记录其依据的规则。</p>
      <p><b>引导节点。</b>新节点用来寻找网络其余部分的第一个节点。</p>
      <p><b>共识。</b>谁可以封存区块、何时算数的规则。在 Tau 上，它本身也是一条规则。</p>
      <p><b>硬分叉。</b>靠新软件实现的规则变更。若有人拒绝，链就分裂。</p>
      <p><b>内存池。</b>尚未进入区块的交易的候车室。</p>
      <p><b>逐点修订。</b>把规则更新并入运行中程序的下一步。</p>
      <p><b>提案。</b>以交易形式发出的规则变更，待检查和表决。</p>
      <p><b>验证者。</b>受托封存区块并对提案投票的节点。</p></div>
    </div>
    <div class="u s4 rt">
      <h2 class="l">近期预告</h2>
      <div class="c2"><p class="ni dc">团队公布的后续节目：为语言加入表格和抽象数据类型；在下一次发布前合并开发分支；一个用白话写规则的简易钱包；以及更远一些的主网和 Agoras，即团队长期描述的算力、知识和专家咨询市场。</p>
      <p>本报无法承诺日期，团队也不承诺。但本报可以承诺：Testnet Alpha 上下一次规则变更时，Tau HUD 会在现场，你也可以。</p></div>
      <div class="coupon"><div class="t">剪下收藏</div><p>实时观看：<b>tauhud.com</b> · 提醒：<b>t.me/tauHUDcom</b> · 试写规则：<b>tauhud.com/playground</b> · Tau 官方：<b>tau.net</b></p></div>
    </div>
    <div class="u s2 rl rt">
      <div class="ad"><div class="t">Tau HUD</div><p>十二件仪器，观看一条能修改自身规则的链。免费。开源。</p><div class="fine">靠时间、工具和一台朴素的服务器维持运转。</div></div>
      <div class="box small notice" style="margin-top:.6em"><p class="ni"><b>读者须知。</b>《{{NAME}}》是社区项目 Tau HUD 制作的一份友好的非官方报纸，与 IDNI 无关。它为传递资讯、带来乐趣而写，不是财务建议，报中也没有任何东西出售。测试网 AGRS 仅供练习，没有价值。文中谈到的计划，转述的是 IDNI 自己说过的话，计划可能改变。事实取自 Tau 团队公开的视频、文章与论文；字幕引文略经整理。谜题与天气仅供一乐。</p></div>
    </div>
  </div>
</div>`
  ]
};

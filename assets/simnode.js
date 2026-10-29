/* Tau HUD: your own node in the simulation. One click starts a simulated node in this browser; it catches up from block #0,
   follows the chain, joins the node orbit after 10 minutes, and under proof of stake its stake can win it a seat among the
   six that seal blocks. The node itself lives in assets/sim.js (TauSim.node: its runs, its presence, its seat), so every
   page draws the same node; this file is its panel and the small status card on the HUD.

   TauSimNode.open()        opens the panel (also: any page URL with #node)
   TauSimNode.card(el)      fills el with a one-glance status that opens the panel, updated every second
   TauSimNode.state()       TauSim.node.state() or null
   Pages hear "tau-simnode" on window when the node starts, stops or changes. */
(() => {
  "use strict";
  if (!window.TauSim || !TauSim.node) return;
  const N = TauSim.node, SIM = TauSim.on, NAME_OK = /^[A-Za-z0-9._-]{1,24}$/;
  const ROOT = (() => { const me = document.currentScript; try { return me && me.src ? new URL("..", me.src).pathname : "/"; } catch (e) { return "/"; } })();
  const lang = () => (window.TauI18n && TauI18n.lang) || "en";
  const T = s => (window.TauI18n && TauI18n.t ? TauI18n.t(s) : s);
  const fmt = n => Number(n || 0).toLocaleString("en-US");
  const clock = t => new Date(t * 1000).toISOString().slice(11, 16) + " UTC";
  const dur = s => { s = Math.max(0, Math.round(s)); const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60; return h ? `${h} h ${m} min` : m >= 10 ? `${m} min` : `${m}:${String(x).padStart(2, "0")}`; };
  const now = () => Date.now() / 1000;
  const el = (tag, attrs, ...kids) => { const e = document.createElement(tag); for (const k in attrs || {}) { if (k === "text") e.textContent = attrs[k]; else if (k === "html") e.innerHTML = attrs[k]; else if (attrs[k] != null && attrs[k] !== false) e.setAttribute(k, attrs[k]); } kids.flat().forEach(c => c != null && e.append(c)); return e; };
  const fire = () => { try { dispatchEvent(new CustomEvent("tau-simnode")); } catch (e) {} };

  /* ---------- the panel's look: the site's monochrome, green the one accent, amber marks the simulation ---------- */
  const css = `
.sn-back { position: fixed; inset: 0; z-index: 90; background: rgba(0,0,0,.66); display: flex; align-items: center; justify-content: center; padding: 16px; }
.sn-back[hidden] { display: none; }
.sn { --sn-ok: #39ff8a; --sn-amber: #ffb13b; --sn-dim: #8a8a94; --sn-line: rgba(255,255,255,.09); --sn-hair: rgba(255,255,255,.18);
  width: min(1180px, 100%); max-height: calc(100vh - 32px); overflow: auto; background: #0f0f11; border: 1px solid var(--sn-hair); border-radius: 10px; box-shadow: 0 30px 80px -20px rgba(0,0,0,.95);
  color: #ebebee; font: 13px/1.5 "JetBrains Mono", ui-monospace, Menlo, monospace; padding: 20px 24px 22px; position: relative; }
.sn h2 { margin: 0; font: 600 12px "Sora", "Segoe UI", sans-serif; letter-spacing: .2em; text-transform: uppercase; color: var(--sn-ok); display: flex; align-items: center; gap: 12px; }
.sn h2 .sn-simtag { font: 600 11px "JetBrains Mono", monospace; letter-spacing: .08em; color: #fff; border: 1px solid rgba(255,177,59,.7); border-radius: 999px; padding: 2px 9px; background: repeating-linear-gradient(135deg, rgba(255,177,59,.16) 0 8px, rgba(255,177,59,.04) 8px 16px); }
.sn .sn-big { margin: 8px 0 14px; font: 600 22px/1.3 "Sora", "Segoe UI", sans-serif; color: #fff; max-width: 76ch; }
.sn .sn-x { position: absolute; top: 12px; right: 12px; width: 44px; height: 44px; border: 1px solid var(--sn-hair); border-radius: 50%; background: transparent; color: #fff; font: 18px/1 sans-serif; cursor: pointer; }
.sn .sn-x:hover { border-color: #fff; }
.sn .sn-cols { display: grid; grid-template-columns: minmax(250px, .9fr) minmax(330px, 1.35fr) minmax(250px, .9fr); gap: 16px; align-items: stretch; }
.sn .sn-col { border: 1px solid var(--sn-line); border-radius: 8px; padding: 14px 16px; min-width: 0; background: rgba(255,255,255,.015); }
.sn .sn-col h3 { margin: 0 0 10px; font: 600 11px "Sora", "Segoe UI", sans-serif; letter-spacing: .2em; text-transform: uppercase; color: var(--sn-dim); }
.sn label { display: block; margin: 10px 0 4px; color: var(--sn-dim); font-size: 12px; }
.sn input[type=text] { width: 100%; box-sizing: border-box; background: rgba(0,0,0,.4); border: 1px solid var(--sn-hair); border-radius: 6px; color: #fff; font: 14px "JetBrains Mono", monospace; padding: 9px 10px; min-height: 44px; }
.sn input[type=text]:focus { outline: none; border-color: var(--sn-ok); }
.sn input[type=range] { width: 100%; accent-color: #39ff8a; min-height: 32px; }
.sn .sn-stake { display: flex; align-items: baseline; gap: 8px; } .sn .sn-stake .sn-note { margin: 0; }
.sn .sn-stake b { font-size: 18px; color: #fff; font-weight: 600; }
.sn .sn-note { color: var(--sn-dim); font-size: 12px; margin: 6px 0 0; }
.sn .sn-btns { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.sn button.sn-b, .sn a.sn-b { display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 0 18px; border-radius: 999px; border: 1px solid var(--sn-hair); background: transparent; color: #fff;
  font: 600 12px "Sora", "Segoe UI", sans-serif; letter-spacing: .14em; text-transform: uppercase; cursor: pointer; text-decoration: none; }
.sn .sn-b.go { background: var(--sn-ok); border-color: var(--sn-ok); color: #000; }
.sn .sn-b.go:hover { box-shadow: 0 0 18px rgba(57,255,138,.5); }
.sn .sn-b:not(.go):hover { border-color: #fff; }
.sn .sn-b.quiet { color: var(--sn-dim); border-color: var(--sn-line); }
.sn .sn-who { display: flex; align-items: center; gap: 10px; margin: 2px 0 6px; }
.sn .sn-who b { font-size: 18px; color: #fff; font-weight: 600; overflow-wrap: anywhere; }
.sn .sn-state { display: inline-block; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; border: 1px solid var(--sn-hair); border-radius: 999px; padding: 2px 9px; color: var(--sn-dim); white-space: nowrap; }
.sn .sn-state.ok { color: var(--sn-ok); border-color: rgba(57,255,138,.55); }
.sn .sn-state.wait { color: var(--sn-amber); border-color: rgba(255,177,59,.6); }
.sn .sn-kv { display: grid; grid-template-columns: auto 1fr; gap: 3px 12px; margin: 8px 0 0; font-size: 12px; }
.sn .sn-kv dt { color: var(--sn-dim); } .sn .sn-kv dd { margin: 0; text-align: right; color: #fff; overflow-wrap: anywhere; }
.sn ol.sn-steps { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.sn .sn-steps li { display: grid; grid-template-columns: 30px 1fr; gap: 10px; padding: 10px 12px; border: 1px solid var(--sn-line); border-radius: 8px; }
.sn .sn-steps li.now { border-color: rgba(57,255,138,.55); background: rgba(57,255,138,.04); }
.sn .sn-steps li.done .sn-n { background: var(--sn-ok); color: #000; border-color: var(--sn-ok); }
.sn .sn-steps li.now .sn-n { border-color: var(--sn-ok); color: var(--sn-ok); }
.sn .sn-n { width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--sn-hair); display: flex; align-items: center; justify-content: center; font-weight: 600; color: var(--sn-dim); }
.sn .sn-steps h4 { margin: 2px 0 2px; font: 600 14px "Sora", "Segoe UI", sans-serif; color: #fff; display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
.sn .sn-steps h4 small { font: 12px "JetBrains Mono", monospace; color: var(--sn-dim); }
.sn .sn-steps li.now h4 small, .sn .sn-steps li.done h4 small { color: var(--sn-ok); }
.sn .sn-steps p { margin: 0; color: var(--sn-dim); font-size: 12px; }
.sn .sn-bar { height: 6px; border-radius: 3px; background: rgba(255,255,255,.08); margin-top: 6px; overflow: hidden; }
.sn .sn-bar i { display: block; height: 100%; background: var(--sn-ok); width: 0; transition: width .4s; }
.sn .sn-real { border-color: rgba(57,255,138,.45); box-shadow: 0 18px 40px -24px rgba(57,255,138,.35); display: flex; flex-direction: column; }
.sn .sn-real h3 { color: var(--sn-ok); }
.sn .sn-real p { margin: 0 0 10px; }
.sn .sn-real ul { margin: 0 0 12px; padding: 0 0 0 18px; color: var(--sn-dim); font-size: 12px; }
.sn .sn-real .sn-btns { margin-top: auto; }
.sn .sn-fine { margin: 14px 0 0; color: var(--sn-dim); font-size: 12px; max-width: 120ch; }
@media (max-width: 1000px) { .sn .sn-cols { grid-template-columns: 1fr; } .sn { padding: 18px 16px; } .sn .sn-big { font-size: 18px; padding-right: 48px; } .sn-back { align-items: flex-start; padding: 8px; overflow: auto; } .sn { max-height: none; } }
/* the HUD's small card */
.sn-card { display: inline-flex; flex-direction: column; gap: 2px; text-align: left; max-width: 250px; min-height: 44px; padding: 6px 11px; border-radius: 8px; border: 1px solid rgba(57,255,138,.45); background: rgba(10,10,12,.82);
  color: #ebebee; font: 12px/1.4 "JetBrains Mono", ui-monospace, monospace; cursor: pointer; }
.sn-card:hover { border-color: #39ff8a; box-shadow: 0 0 14px rgba(57,255,138,.35); }
.sn-card b { font: 600 11px "Sora", "Segoe UI", sans-serif; letter-spacing: .16em; text-transform: uppercase; color: #39ff8a; }
.sn-card span { color: #c9c9d0; } .sn-card .sn-top { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; } .sn-card strong { color: #fff; font-weight: 600; font-size: 13px; overflow-wrap: anywhere; }
.sn-card .sn-bar { height: 4px; border-radius: 2px; background: rgba(255,255,255,.08); overflow: hidden; margin-top: 3px; } .sn-card .sn-bar i { display: block; height: 100%; background: #39ff8a; }
.sn-card.idle { border-style: dashed; }
`;
  document.head.append(el("style", { id: "simnode-css", text: css }));

  /* ---------- Chinese: the dictionary travels with the panel, so no page file has to carry it ---------- */
  if (lang() === "zh" && window.TauI18n) TauI18n.add({ strings: {
    "Your node": "你的节点", "Simulation": "模拟", "Run your own node in the simulation": "在模拟中运行你自己的节点",
    "Start your node": "启动你的节点", "Stop": "停止", "Start again": "再次启动", "Forget it": "删除它", "Close": "关闭",
    "Name": "名字", "Stake it brings": "它带来的质押", "AGRS (made up)": "AGRS（虚构）",
    "1 to 24 letters, digits, dots, dashes or underscores.": "1 到 24 个字母、数字、点、短横线或下划线。",
    "What it lives through": "它会经历什么", "Make it real": "变成真的",
    "Catch up": "追上链", "Follow the chain": "跟随链", "Join the node orbit": "进入节点轨道", "Seal blocks by stake": "凭质押出块",
    "Downloads every block from #0 and checks each against the rules in force.": "从 #0 开始下载每个区块，并按现行规则逐一检查。",
    "Checks each new block as it is sealed, one about every 8 seconds, and keeps its own copy of the chain.": "每个新区块封装时就检查它（大约每 8 秒一个），并保留自己的一份链。",
    "Listed after 10 min on the network, kept for 30 min after its last contact, so short tests don’t make the count flicker.": "在网络上 10 分钟后列出，最后一次联系后保留 30 分钟，这样短暂测试不会让数量闪烁。",
    "Under proof of stake the six largest stakes take turns sealing blocks. The simulation runs proof of stake from 10:30 to 16:30 UTC every day.": "在权益证明下，质押最多的六个轮流出块。模拟每天 10:30 到 16:30 UTC 运行权益证明。",
    "Status": "状态", "Height": "高度", "Stake": "质押", "Rank by stake": "质押排名", "Sealed today": "今天出块",
    "Syncing": "同步中", "Following": "跟随中", "On the orbit": "在轨道上", "Sealing": "出块中", "Stopped": "已停止",
    "done": "完成", "waiting": "等待", "now": "现在",
    "This node lives only in your browser. It runs while a Tau HUD page in simulation is open, other visitors don’t see it, and its stake is made up.": "这个节点只存在于你的浏览器中。只要有一个模拟模式的 Tau HUD 页面开着，它就在运行；其他访客看不到它，它的质押是虚构的。",
    "A real node does the same on the real testnet:": "真正的节点在真实测试网上做同样的事：",
    "it checks every block for itself": "它亲自检查每个区块", "it gets a row on the Nodes board and a badge": "它在节点榜上有一行，还有徽章",
    "it is the first step toward a validator seat": "它是迈向验证者席位的第一步",
    "A small server, one command, about €6 a month.": "一台小服务器，一条命令，每月约 6 欧元。",
    "Run a real node": "运行真正的节点", "Watch it on the HUD": "在 HUD 上观看",
    "Simulated node": "模拟节点", "Run a node here": "在这里运行节点", "simulated, in your browser": "模拟的，在你的浏览器里",
    "Watch it in the Chain core: the node orbit, and the validator orbit once it seals.": "在链核心中观看：节点轨道，以及它出块后的验证者轨道。",
    "catching up · {n} of {m}": "追赶中 · {n} / {m}", "following {n} · on the orbit in {x}": "跟随 {n} · {x} 后进入轨道",
    "sealing by stake · {n} blocks today": "凭质押出块 · 今天 {n} 个区块", "sealing by stake · {n} block today": "凭质押出块 · 今天 {n} 个区块",
    "on the orbit · stake rank {n}, the top {m} seal": "在轨道上 · 质押排名 {n}，前 {m} 名出块", "on the orbit · proof of stake at {x}": "在轨道上 · {x} 开始权益证明",
    "stopped · leaves the orbit at {x}": "已停止 · {x} 离开轨道", "stopped": "已停止",
    "{n} of {m}": "{n} / {m}", "{n} · same chain": "{n} · 同一条链", "in {x}": "{x} 后", "until {x}": "直到 {x}", "about {n} s": "约 {n} 秒", "after 10 min": "10 分钟后",
    "on the orbit": "在轨道上", "{n} sealed": "已出块 {n} 个", "proof of stake now": "现在是权益证明", "10:30–16:30 UTC": "10:30–16:30 UTC",
    "{n} h {m} min": "{n} 小时 {m} 分钟", "{n} min": "{n} 分钟",
    "With this stake: rank {n} of all accounts, a seat under proof of stake.": "按这个质押：在所有账户中排名 {n}，权益证明下有席位。",
    "With this stake: rank {n} of all accounts, no seat: the top {m} start above {a} AGRS.": "按这个质押：在所有账户中排名 {n}，没有席位：前 {m} 名在 {a} AGRS 以上。",
    "Now the fixed validator list seals. Proof of stake starts at {x}, in {y}; keep a page open then and your stake would rank {n}: a seat.": "现在由固定验证者名单出块。权益证明在 {x} 开始（{y} 后）；届时保持一个页面打开，你的质押将排名 {n}：一个席位。",
    "Now the fixed validator list seals. Proof of stake starts at {x}, in {y}; keep a page open then and your stake needs more than {n} AGRS for a seat.": "现在由固定验证者名单出块。权益证明在 {x} 开始（{y} 后）；届时保持一个页面打开，你的质押需要超过 {n} AGRS 才有席位。",
    "Proof of stake is on, but a stopped node seals nothing.": "权益证明已开启，但停止的节点不会出块。",
    "Proof of stake is on. Once caught up, your stake competes for one of the six seats.": "权益证明已开启。追上链之后，你的质押会争夺六个席位之一。",
    "Proof of stake is on until {x}. Your stake ranks {n}: your node takes its turn about every {m} s. {a} sealed today, last {b}.": "权益证明持续到 {x}。你的质押排名 {n}：你的节点大约每 {m} 秒轮到一次。今天已出块 {a} 个，最近 {b}。",
    "Proof of stake is on until {x}. Your stake ranks {n}: your node takes its turn about every {m} s. {a} sealed today.": "权益证明持续到 {x}。你的质押排名 {n}：你的节点大约每 {m} 秒轮到一次。今天已出块 {a} 个。",
    "Proof of stake is on until {x}. Your stake ranks {n}: more than {m} AGRS wins a seat.": "权益证明持续到 {x}。你的质押排名 {n}：超过 {m} AGRS 才能赢得席位。",
    "Under proof of stake the six largest stakes take turns sealing blocks.": "在权益证明下，质押最多的六个轮流出块。",
    "No server yet?": "还没有服务器？", "Try a simulated node in your browser first.": "先在浏览器里试一个模拟节点。", "Try it": "试一试", "you · simulated": "你 · 模拟",
    "It catches up from block #0, joins the node orbit after 10 min and, under proof of stake, can seal blocks. Only in your browser.": "它从区块 #0 开始追上链，10 分钟后进入节点轨道，在权益证明下可以出块。只在你的浏览器里。",
    "You": "你", "You · {x}": "你 · {x}", "your node": "你的节点", "by your node": "由你的节点",
    "Your node “{x}”, simulated in your browser, at {n}.": "你的节点“{x}”，在你的浏览器中模拟，位于 {n}。",
    "It checks every block for itself and made the node orbit after 10 min on the network; it stays 30 min after its last contact.": "它亲自检查每个区块，在网络上 10 分钟后进入了节点轨道；最后一次联系后保留 30 分钟。",
    "Under proof of stake its stake can win a seat among the validators.": "在权益证明下，它的质押可以在验证者中赢得一个席位。",
    "Click to open your node.": "点击打开你的节点。",
    "Your node “{x}”, sealing by stake.": "你的节点“{x}”，正在凭质押出块。",
    "Under proof of stake the six largest stakes take turns sealing, and yours ranks {n}: {m} blocks sealed today.": "在权益证明下，质押最多的六个轮流出块，你的排名 {n}：今天已出块 {m} 个。",
    "Under proof of stake the six largest stakes take turns sealing, and yours ranks {n}: {m} block sealed today.": "在权益证明下，质押最多的六个轮流出块，你的排名 {n}：今天已出块 {m} 个。",
    "Green: it sealed the newest block.": "高亮：最新的区块是它封装的。",
    "Your node, sealing by stake: under proof of stake the six largest stakes take turns, and yours is one of them.": "你的节点，正在凭质押出块：在权益证明下，质押最多的六个轮流出块，你的是其中之一。",
    "Your simulated node {x}: {y}. Open its panel.": "你的模拟节点 {x}：{y}。打开它的面板。", "Start a simulated node in your browser": "在浏览器中启动一个模拟节点",
  }, patterns: [] });
  /* Japanese, the same way */
  if (lang() === "ja" && window.TauI18n) TauI18n.add({ strings: {
    "Your node": "あなたのノード",
    "Simulation": "シミュレーション",
    "Run your own node in the simulation": "シミュレーションで自分のノードを動かす",
    "Start your node": "ノードを起動",
    "Stop": "停止",
    "Start again": "もう一度起動",
    "Forget it": "削除する",
    "Close": "閉じる",
    "Name": "名前",
    "Stake it brings": "持ち込むステーク",
    "AGRS (made up)": "AGRS（架空）",
    "1 to 24 letters, digits, dots, dashes or underscores.": "1〜24 文字の英字、数字、ドット、ダッシュ、アンダースコア。",
    "What it lives through": "体験すること",
    "Make it real": "本物にする",
    "Catch up": "追いつく",
    "Follow the chain": "チェーンを追う",
    "Join the node orbit": "ノード軌道に加わる",
    "Seal blocks by stake": "ステークでブロックを生成",
    "Downloads every block from #0 and checks each against the rules in force.": "ブロック #0 からすべてを取得し、それぞれを施行中のルールと照らして検査します。",
    "Checks each new block as it is sealed, one about every 8 seconds, and keeps its own copy of the chain.": "新しいブロックが生成されるたびに検査し（約 8 秒に 1 つ）、自分のチェーンのコピーを保ちます。",
    "Listed after 10 min on the network, kept for 30 min after its last contact, so short tests don’t make the count flicker.": "ネットワーク上で 10 分たつと一覧に載り、最後の通信から 30 分は残ります。短いテストで数がちらつかないようにするためです。",
    "Under proof of stake the six largest stakes take turns sealing blocks. The simulation runs proof of stake from 10:30 to 16:30 UTC every day.": "プルーフ・オブ・ステークでは、ステークの大きい上位 6 つが交代でブロックを生成します。シミュレーションでは毎日 UTC 10:30〜16:30 にプルーフ・オブ・ステークが動きます。",
    "Status": "状態",
    "Height": "高さ",
    "Stake": "ステーク",
    "Rank by stake": "ステークの順位",
    "Sealed today": "今日生成",
    "Syncing": "同期中",
    "Following": "追跡中",
    "On the orbit": "軌道上",
    "Sealing": "生成中",
    "Stopped": "停止",
    "done": "完了",
    "waiting": "待機",
    "now": "いま",
    "This node lives only in your browser. It runs while a Tau HUD page in simulation is open, other visitors don’t see it, and its stake is made up.": "このノードはあなたのブラウザーの中にだけ存在します。シミュレーション中の Tau HUD のページが開いている間だけ動き、ほかの訪問者には見えず、ステークは架空です。",
    "A real node does the same on the real testnet:": "本物のノードは本物のテストネットで同じことをします：",
    "it checks every block for itself": "すべてのブロックを自分で検査する",
    "it gets a row on the Nodes board and a badge": "ノードのボードに行とバッジが付く",
    "it is the first step toward a validator seat": "バリデーター席への第一歩になる",
    "A small server, one command, about €6 a month.": "小さなサーバー、コマンド 1 つ、月約 6 ユーロ。",
    "Run a real node": "本物のノードを動かす",
    "Watch it on the HUD": "HUD で見る",
    "Simulated node": "シミュレーションのノード",
    "Run a node here": "ここでノードを動かす",
    "simulated, in your browser": "シミュレーション、あなたのブラウザー内",
    "Watch it in the Chain core: the node orbit, and the validator orbit once it seals.": "チェーンコアで見る：ノード軌道、そして生成を始めたらバリデーター軌道。",
    "catching up · {n} of {m}": "追いつき中 · {m} 中 {n}",
    "following {n} · on the orbit in {x}": "追跡中 {n} · 軌道まで {x}",
    "sealing by stake · {n} blocks today": "ステークで生成中 · 今日 {n} ブロック",
    "sealing by stake · {n} block today": "ステークで生成中 · 今日 {n} ブロック",
    "on the orbit · stake rank {n}, the top {m} seal": "軌道上 · ステーク順位 {n}、上位 {m} が生成",
    "on the orbit · proof of stake at {x}": "軌道上 · プルーフ・オブ・ステークは {x} に",
    "stopped · leaves the orbit at {x}": "停止 · {x} に軌道を離れる",
    "stopped": "停止",
    "{n} of {m}": "{m} 中 {n}",
    "{n} · same chain": "{n} · 同じチェーン",
    "in {x}": "{x} 後",
    "until {x}": "{x} まで",
    "about {n} s": "約 {n} 秒",
    "after 10 min": "10 分後",
    "on the orbit": "軌道上",
    "{n} sealed": "{n} 生成",
    "proof of stake now": "いまプルーフ・オブ・ステーク",
    "10:30–16:30 UTC": "UTC 10:30〜16:30",
    "{n} h {m} min": "{n} 時間 {m} 分",
    "{n} min": "{n} 分",
    "With this stake: rank {n} of all accounts, a seat under proof of stake.": "このステークなら：全アカウント中 {n} 位、プルーフ・オブ・ステークで席あり。",
    "With this stake: rank {n} of all accounts, no seat: the top {m} start above {a} AGRS.": "このステークなら：全アカウント中 {n} 位、席なし：上位 {m} は {a} AGRS 以上です。",
    "Now the fixed validator list seals. Proof of stake starts at {x}, in {y}; keep a page open then and your stake would rank {n}: a seat.": "いまは固定のバリデーターリストが生成しています。プルーフ・オブ・ステークは {x} に始まります（{y} 後）。そのときページを開いておけば、あなたのステークは {n} 位：席があります。",
    "Now the fixed validator list seals. Proof of stake starts at {x}, in {y}; keep a page open then and your stake needs more than {n} AGRS for a seat.": "いまは固定のバリデーターリストが生成しています。プルーフ・オブ・ステークは {x} に始まります（{y} 後）。そのときページを開いておくなら、席には {n} AGRS より多いステークが必要です。",
    "Proof of stake is on, but a stopped node seals nothing.": "プルーフ・オブ・ステークは稼働中ですが、停止したノードは何も生成しません。",
    "Proof of stake is on. Once caught up, your stake competes for one of the six seats.": "プルーフ・オブ・ステークは稼働中です。追いついたら、あなたのステークが 6 つの席の 1 つを争います。",
    "Proof of stake is on until {x}. Your stake ranks {n}: your node takes its turn about every {m} s. {a} sealed today, last {b}.": "プルーフ・オブ・ステークは {x} まで稼働中。あなたのステークは {n} 位：約 {m} 秒ごとにあなたのノードの番が来ます。今日 {a} 生成、最新 {b}。",
    "Proof of stake is on until {x}. Your stake ranks {n}: your node takes its turn about every {m} s. {a} sealed today.": "プルーフ・オブ・ステークは {x} まで稼働中。あなたのステークは {n} 位：約 {m} 秒ごとにあなたのノードの番が来ます。今日 {a} 生成。",
    "Proof of stake is on until {x}. Your stake ranks {n}: more than {m} AGRS wins a seat.": "プルーフ・オブ・ステークは {x} まで稼働中。あなたのステークは {n} 位：{m} AGRS より多ければ席を得られます。",
    "Under proof of stake the six largest stakes take turns sealing blocks.": "プルーフ・オブ・ステークでは、ステークの大きい上位 6 つが交代でブロックを生成します。",
    "No server yet?": "まだサーバーがない？",
    "Try a simulated node in your browser first.": "まずはブラウザーでシミュレーションのノードを試しましょう。",
    "Try it": "試してみる",
    "you · simulated": "あなた · シミュレーション",
    "It catches up from block #0, joins the node orbit after 10 min and, under proof of stake, can seal blocks. Only in your browser.": "ブロック #0 から追いつき、10 分後にノード軌道に加わり、プルーフ・オブ・ステークではブロックを生成できます。あなたのブラウザーの中だけで。",
    "You": "あなた",
    "You · {x}": "あなた · {x}",
    "your node": "あなたのノード",
    "by your node": "あなたのノードが生成",
    "Your node “{x}”, simulated in your browser, at {n}.": "あなたのノード「{x}」、ブラウザー内のシミュレーション、高さ {n}。",
    "It checks every block for itself and made the node orbit after 10 min on the network; it stays 30 min after its last contact.": "すべてのブロックを自分で検査し、ネットワーク上で 10 分たってノード軌道に入りました。最後の通信から 30 分は残ります。",
    "Under proof of stake its stake can win a seat among the validators.": "プルーフ・オブ・ステークでは、そのステークでバリデーターの席を得られます。",
    "Click to open your node.": "クリックであなたのノードを開く。",
    "Your node “{x}”, sealing by stake.": "あなたのノード「{x}」、ステークで生成中。",
    "Under proof of stake the six largest stakes take turns sealing, and yours ranks {n}: {m} blocks sealed today.": "プルーフ・オブ・ステークでは、ステークの大きい上位 6 つが交代で生成し、あなたのものは {n} 位：今日 {m} ブロック生成。",
    "Under proof of stake the six largest stakes take turns sealing, and yours ranks {n}: {m} block sealed today.": "プルーフ・オブ・ステークでは、ステークの大きい上位 6 つが交代で生成し、あなたのものは {n} 位：今日 {m} ブロック生成。",
    "Green: it sealed the newest block.": "緑：最新のブロックを生成しました。",
    "Your node, sealing by stake: under proof of stake the six largest stakes take turns, and yours is one of them.": "あなたのノード、ステークで生成中：プルーフ・オブ・ステークではステークの大きい上位 6 つが交代し、あなたのものはその 1 つです。",
    "Your simulated node {x}: {y}. Open its panel.": "あなたのシミュレーションのノード {x}：{y}。パネルを開く。",
    "Start a simulated node in your browser": "ブラウザーでシミュレーションのノードを起動"
  } });

  /* ---------- what the node is doing, in words ---------- */
  function words(s) {
    if (!s) return null;
    const t = now();
    if (s.stopped || !s.on) return { tag: "Stopped", cls: "", line: s.listed ? `stopped · leaves the orbit at ${clock(s.leaveAt)}` : "stopped" };
    if (!s.synced) return { tag: "Syncing", cls: "wait", line: `catching up · #${fmt(s.height)} of #${fmt(s.head)}`, bar: s.progress };
    if (s.seat) return { tag: "Sealing", cls: "ok", line: `sealing by stake · ${fmt(s.sealed)} block${s.sealed === 1 ? "" : "s"} today` };
    if (!s.listed) return { tag: "Following", cls: "wait", line: `following #${fmt(s.head)} · on the orbit in ${dur(s.listAt - t)}`, bar: Math.min(1, 1 - (s.listAt - t) / N.listAfter) };
    return { tag: "On the orbit", cls: "ok", line: s.mode === "stake" ? `on the orbit · stake rank #${s.rank}, the top ${N.seats} seal` : `on the orbit · proof of stake at ${clock(s.pos.from)}` };
  }
  function sealText(s) {
    const t = now();
    if (!s) return "Under proof of stake the six largest stakes take turns sealing blocks.";
    if (s.mode !== "stake") return `Now the fixed validator list seals. Proof of stake starts at ${clock(s.pos.from)}, in ${dur(s.pos.from - t)}; keep a page open then and your stake ${s.stake > s.sixth ? "would rank #" + s.rank + ": a seat" : "needs more than " + fmt(s.sixth) + " AGRS for a seat"}.`;
    if (!s.on) return "Proof of stake is on, but a stopped node seals nothing.";
    if (!s.synced) return "Proof of stake is on. Once caught up, your stake competes for one of the six seats.";
    if (s.seat) return `Proof of stake is on until ${clock(s.pos.to)}. Your stake ranks #${s.rank}: your node takes its turn about every ${N.seats * 8} s. ${fmt(s.sealed)} sealed today${s.lastSeal ? ", last #" + fmt(s.lastSeal) : ""}.`;
    return `Proof of stake is on until ${clock(s.pos.to)}. Your stake ranks #${s.rank}: more than ${fmt(s.sixth)} AGRS wins a seat.`;
  }

  /* ---------- the panel ---------- */
  let back = null, timer = null, draft = { name: "", stake: 200000 };
  function build() {
    back = el("div", { class: "sn-back", hidden: "", role: "dialog", "aria-modal": "true", "aria-labelledby": "snTitle" });
    back.addEventListener("click", e => { if (e.target === back) close(); });
    addEventListener("keydown", e => { if (e.key === "Escape" && back && !back.hidden) close(); });
    document.body.append(back);
  }
  function render() {
    const s = N.state(), w = words(s), t = now();
    if (!draft.name) draft.name = s ? s.name : "visitor-" + Math.random().toString(36).slice(2, 6);
    const box = el("div", { class: "sn" });
    box.append(el("button", { class: "sn-x", type: "button", "aria-label": T("Close"), text: "✕" }));
    box.append(el("h2", { id: "snTitle" }, el("span", { text: "Your node" }), el("span", { class: "sn-simtag", text: "Simulation" })));
    box.append(el("p", { class: "sn-big", text: "Run your own node in the simulation" }));
    // column 1: the node itself
    const c1 = el("section", { class: "sn-col" }, el("h3", { text: "Your node" }));
    const name = el("input", { type: "text", id: "snName", value: s ? s.name : draft.name, maxlength: "24", spellcheck: "false", autocomplete: "off" });
    const stakeVal = el("b", { text: fmt(s ? s.stake : draft.stake) });
    const range = el("input", { type: "range", id: "snStake", min: "0", max: "300000", step: "5000", value: String(s ? s.stake : draft.stake), "aria-label": "Stake it brings" });
    const rankNote = el("p", { class: "sn-note", id: "snRank" });
    if (s) {
      c1.append(el("div", { class: "sn-who" }, el("b", { text: s.name }), el("span", { class: "sn-state " + w.cls, text: w.tag })));
      c1.append(el("dl", { class: "sn-kv" },
        el("dt", { text: "Height" }), el("dd", { text: `#${fmt(s.height)}` }),
        el("dt", { text: "Stake" }), el("dd", { text: `${fmt(s.stake)} AGRS` }),
        el("dt", { text: "Rank by stake" }), el("dd", { text: `#${s.rank}` }),
        el("dt", { text: "Sealed today" }), el("dd", { text: fmt(s.sealed) })));
    } else {
      c1.append(el("label", { for: "snName", text: "Name" }), name, el("p", { class: "sn-note", text: "1 to 24 letters, digits, dots, dashes or underscores." }));
    }
    c1.append(el("label", { for: "snStake", text: "Stake it brings" }), el("div", { class: "sn-stake" }, stakeVal, el("span", { class: "sn-note", text: "AGRS (made up)" })), range, rankNote);
    const btns = el("div", { class: "sn-btns" });
    if (!s) btns.append(el("button", { class: "sn-b go", type: "button", "data-act": "start", text: "Start your node" }));
    else if (s.stopped || !s.on) btns.append(el("button", { class: "sn-b go", type: "button", "data-act": "start", text: "Start again" }), el("button", { class: "sn-b quiet", type: "button", "data-act": "forget", text: "Forget it" }));
    else btns.append(el("button", { class: "sn-b", type: "button", "data-act": "stop", text: "Stop" }));
    c1.append(btns);
    // column 2: the four things it lives through
    const steps = el("ol", { class: "sn-steps" }), cur = !s || s.stopped || !s.on ? 0 : !s.synced ? 1 : !s.listed ? 2 : s.seat ? 4 : s.mode === "stake" ? 4 : 3;
    const done = i => s && (s.on ? i < cur || (i === 3 && s.listed) || (i === 4 && s.seat) : (i === 1 && s.height > 0) || (i === 3 && s.listed));
    const step = (i, title, state, text, bar) => steps.append(el("li", { class: done(i) ? "done" : i === cur ? "now" : "" },
      el("span", { class: "sn-n", text: done(i) ? "✓" : String(i) }),
      el("div", null, el("h4", null, el("span", { text: title }), el("small", { text: state })), el("p", { text }), bar != null ? el("div", { class: "sn-bar" }, el("i", { style: `width:${Math.round(bar * 100)}%` })) : null)));
    step(1, "Catch up", !s ? "about " + Math.max(4, Math.round(TauSim.head() / 300) + 3) + " s" : s.synced ? "done" : s.on ? `#${fmt(s.height)} of #${fmt(s.head)}` : "waiting", "Downloads every block from #0 and checks each against the rules in force.", s && s.on && !s.synced ? s.progress : null);
    step(2, "Follow the chain", !s || !s.on ? "waiting" : s.synced ? `#${fmt(s.head)} · same chain` : "waiting", "Checks each new block as it is sealed, one about every 8 seconds, and keeps its own copy of the chain.");
    step(3, "Join the node orbit", !s ? "after 10 min" : s.listed ? (s.on ? "on the orbit" : `until ${clock(s.leaveAt)}`) : s.on ? `in ${dur(s.listAt - t)}` : "waiting", "Listed after 10 min on the network, kept for 30 min after its last contact, so short tests don’t make the count flicker.", s && s.on && !s.listed ? Math.max(0, Math.min(1, 1 - (s.listAt - t) / N.listAfter)) : null);
    step(4, "Seal blocks by stake", !s ? "10:30–16:30 UTC" : s.seat ? `${fmt(s.sealed)} sealed` : s.mode === "stake" ? "proof of stake now" : `in ${dur(s.pos.from - t)}`, sealText(s));
    const c2 = el("section", { class: "sn-col" }, el("h3", { text: "What it lives through" }), steps);
    // column 3: from here to a real node
    const nodes = ROOT + "nodes/" + (lang() !== "en" ? "?lang=" + lang() : "") + "#join", onHud = !!document.getElementById("core");
    const c3 = el("section", { class: "sn-col sn-real" }, el("h3", { text: "Make it real" }),
      el("p", { text: "This node lives only in your browser. It runs while a Tau HUD page in simulation is open, other visitors don’t see it, and its stake is made up." }),
      el("p", { text: "A real node does the same on the real testnet:" }),
      el("ul", null, el("li", { text: "it checks every block for itself" }), el("li", { text: "it gets a row on the Nodes board and a badge" }), el("li", { text: "it is the first step toward a validator seat" })),
      el("p", { class: "sn-note", text: "A small server, one command, about €6 a month." }),
      el("div", { class: "sn-btns" }, el("a", { class: "sn-b go", href: nodes, text: "Run a real node" }), onHud ? null : el("a", { class: "sn-b", href: ROOT + (lang() !== "en" ? "?lang=" + lang() : ""), text: "Watch it on the HUD" })));
    box.append(el("div", { class: "sn-cols" }, c1, c2, c3));
    box.append(el("p", { class: "sn-fine", text: "Watch it in the Chain core: the node orbit, and the validator orbit once it seals." }));
    // wiring
    const showRank = v => { stakeVal.textContent = fmt(v | 0); rankNote.textContent = rankLine(v | 0); };
    range.addEventListener("input", () => showRank(range.value));
    range.addEventListener("change", () => { draft.stake = range.value | 0; if (s && s.on && !s.stopped) { N.stake(draft.stake); fire(); paint(); } });
    name.addEventListener("input", () => { draft.name = name.value.trim(); name.style.borderColor = NAME_OK.test(draft.name) ? "" : "#ffb13b"; });
    box.querySelector(".sn-x").addEventListener("click", close);
    btns.addEventListener("click", e => {
      const act = e.target.closest("[data-act]"); if (!act) return;
      const a = act.dataset.act;
      if (a === "start") { const nm = s ? s.name : draft.name; if (!NAME_OK.test(nm)) { name.focus(); return; } N.start(nm, range.value | 0); }
      else if (a === "stop") N.stop();
      else if (a === "forget") { N.forget(); draft.name = ""; }
      fire(); paint();
    });
    showRank(range.value);
    return box;
  }
  /* the rank against the chain's balances at the head: judged the way the next block judges it */
  function rankLine(stake) {
    const r = N.rank(stake);
    return `With this stake: rank #${r.rank} of all accounts${r.rank <= N.seats ? ", a seat under proof of stake" : `, no seat: the top ${N.seats} start above ${fmt(r.sixth)} AGRS`}.`;
  }
  function paint() {
    if (!back) build();
    const focus = document.activeElement && document.activeElement.id;
    back.replaceChildren(render());
    if (focus && document.getElementById(focus)) document.getElementById(focus).focus();
  }
  function open() {
    if (!SIM) { TauSim.set("sim"); return; }
    paint(); back.hidden = false; document.documentElement.style.overflow = "hidden";
    clearInterval(timer); timer = setInterval(() => { const a = document.activeElement; if (a && (a.id === "snName" || a.id === "snStake")) return; paint(); }, 1000);
    setTimeout(() => { const b = back.querySelector(".sn-b.go") || back.querySelector(".sn-x"); if (b) b.focus(); }, 0);
  }
  function close() {
    if (!back) return; back.hidden = true; clearInterval(timer); document.documentElement.style.overflow = "";
    if (location.hash === "#node") try { history.replaceState(history.state, "", location.pathname + location.search); } catch (e) {}
  }

  /* ---------- the HUD's card ---------- */
  function card(host) {
    if (!host) return;
    const b = el("button", { type: "button", class: "sn-card" });
    b.addEventListener("click", open);
    host.replaceChildren(b);
    const tick = () => {
      if (!SIM) { host.hidden = true; return; }
      host.hidden = false;
      const s = N.state(), w = words(s);
      b.classList.toggle("idle", !s);
      b.replaceChildren(...(s ? [el("div", { class: "sn-top" }, el("b", { text: "Your node" }), el("strong", { text: s.name })), el("span", { text: w.line }), w.bar != null ? el("div", { class: "sn-bar" }, el("i", { style: `width:${Math.round(w.bar * 100)}%` })) : null].filter(Boolean)
        : [el("b", { text: "Run a node here" }), el("span", { text: "simulated, in your browser" })]));
      b.setAttribute("aria-label", s ? `Your simulated node ${s.name}: ${w.line}. Open its panel.` : "Start a simulated node in your browser");
    };
    tick(); setInterval(tick, 1000); addEventListener("tau-simnode", tick);
  }

  window.TauSimNode = { open, close, card, state: () => N.state() };
  const hash = () => { if (location.hash === "#node") open(); };
  if (document.readyState === "loading") addEventListener("DOMContentLoaded", hash); else hash();
  addEventListener("hashchange", hash);
})();

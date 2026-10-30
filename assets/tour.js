/* Tau HUD guided tours for the subpages: the same card as the HUD's tour, one short tour per page.
   Loaded by assets/nav.js. A step spotlights one part of the page and says what it shows and why it matters;
   the card sits next to it with a pointer (below, else beside or above), on phones it is a sheet at the bottom.
   Offered once on a page's first visit (“Not now” and finishing are remembered per page), started any time from
   “Tour” in the header, from the gear or with ?tour=1. Arrow keys step, Escape ends. Chinese: assets/i18n/zh/tour.js. */
(() => {
  "use strict";
  const me = document.currentScript, ROOT = me && me.src ? new URL("..", me.src).href : "/";
  const nav = document.querySelector("nav.tnav"), PAGE = nav ? nav.dataset.page : "";
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };

  /* one entry per page: intro for the first-visit card, then steps { s: selector or list (first visible wins), t: title, x: text,
     go: element clicked first, when: the step belongs to a view of the page that must be showing when the tour starts } */
  const TOURS = {
    playground: { name: "the playground", intro: "Write a rule for your own money, run the testnet’s checks on it, then take a validator seat and vote a network rule into law.", steps: [
      { s: "#viewPolicy > .panel:nth-child(1)", go: "#tabPolicy", t: "Write a rule for your own money", x: "Pick an example or type your own. A personal rule decides on your outgoing transfers: 1 lets a transfer through, 0 stops it. It binds the account, not the key, so even a stolen key has to obey it." },
      { s: "#btnCheck", t: "Run the testnet’s own checks", x: "“Check rule” runs the same checks the Tau Testnet Alpha runs before it accepts a personal rule, and the real Tau engine on our node when it is reachable. Nothing is sent to the chain." },
      { s: "#viewPolicy > .panel:nth-child(2)", t: "See what the testnet does with it", x: "Seven checks, one per row: size, shape, time, streams, widths, your address guard and the Tau engine. Hover a row for a short answer, click it for why it passed or how to fix it." },
      { s: "#viewPolicy > .ptests", t: "Try transfers against it", x: "Each row is a transfer from, to, amount and time. The result updates as you type, so you see at once which payments your rule allows and which it blocks." },
      { s: "#viewSeat > .panel:nth-child(1)", go: "#tabSeat", t: "Take a validator seat", x: "The rules of the whole network change by vote. Pick a proposal, or write your own, and you sit in one of the validator seats of a simulated chain." },
      { s: "#viewSeat > .pprop", t: "Vote it into law", x: "Once a vote runs, the bar fills with every yes. When enough validators agree, the change gets an activation block and becomes law for everyone at once: no fork, no upgrade." },
      { s: "#viewSeat > .pchain", t: "Watch the chain take it", x: "The simulated chain shows its height, base fee and validators. When your change takes effect, they change on that block, and every block after it is judged by the new rule." },
    ] },
    explorer: { name: "the Explorer", intro: "Look up any transaction, block or address and see in plain words what happened to it.", steps: [
      { s: "#find", t: "Look anything up", x: "Paste a transaction hash, a block number or an address. The page says what happened to it: sealed in a block, still waiting, or refused, and why." },
      { s: "#qcheck", t: "Is anything stuck?", x: "Our node’s waiting list, checked against the chain. Really waiting, stuck for over ten minutes and already in a block are counted apart, so nothing looks lost that is not." },
      { s: "#trail", t: "The trail of the chain", x: "Newest first. Switch between the latest blocks, the waiting queue, rule changes and votes, and refused transactions. Click a line to open it on the right." },
      { s: "#detail", t: "Every detail in one place", x: "What a block or transaction changed: balances, own rules, rule offers, fees. Addresses and hashes are links, so you can follow money and rules from one account to the next." },
    ] },
    account: { name: "Accounts", intro: "Every account on Tau keeps its own rules. See them next to its money, its offers and what its rules refused.", steps: [
      { s: "#find", t: "Find an account", x: "Type an address or part of one, or open the list of all accounts. AGRS on the testnet are test tokens with no value." },
      { s: "#dir .panel.rich", when: "#dir:not([hidden])", t: "Every account, ranked", x: "All accounts by balance, with how the coins are spread. Click a row for a quick look on the right; click the address to open the account." },
      { s: "#prev", when: "#dir:not([hidden])", t: "A quick look first", x: "Balance, own rules and latest activity of the row you picked, before you open it." },
      { s: "#acct .panel.ident", when: "#acct:not([hidden])", t: "Whose account this is", x: "The full address, its roles on the chain (validator, rule owner) and buttons to copy or share it." },
      { s: "#tiles", when: "#acct:not([hidden])", t: "The numbers that matter", x: "Balance, received, sent, transactions, rules in force and refusals of this account at a glance. Hover a tile for what it counts." },
      { s: "#acct section.panel:has(#rules)", when: "#acct:not([hidden])", t: "Its own rules", x: "The rules this account set for its own money, in force on every transfer it sends. They bind the account, not the key." },
      { s: "#acct section.panel:has(#refusals)", when: "#acct:not([hidden])", t: "What its rules refused", x: "Transfers that its own rules or the network rules stopped, each with the reason. This is Tau saying no, in public." },
    ] },
    history: { name: "Time travel", intro: "Scrub through the whole chain and see the rules that were in force at any block.", steps: [
      { s: "#pTl", t: "The whole chain on one line", x: "From the first block to now. The lanes show transactions per block, rule changes and the rule revision in force. Click anywhere to jump there; the wheel or + and − zoom in." },
      { s: "#pTl .controls", t: "Step, play or jump", x: "Go block by block, play the chain forward, or jump straight to the next rule event. Arrow keys work too, with Shift they jump between rule events." },
      { s: "#pRules", t: "The rules in force at that block", x: "Tau judges every block by the rules in force at its height. Here they are for the block you picked: revision, fee, validators and votes needed." },
      { s: "#pAgree", t: "Agreement in progress", x: "Which rule changes were waiting for votes at that block, how many yes votes they had and how many they needed." },
      { s: "#pBlock", t: "The block itself", x: "Who made it, when, its hash and what it held." },
    ] },
    stats: { name: "Stats", intro: "How the testnet is doing, block by block: pace, transactions, accounts, refusals and restarts.", steps: [
      { s: ".top .filters", t: "Pick a range", x: "This chain since its last restart, or the last 24, 6 or 1 hours. Every number and chart below follows it." },
      { s: "#tiles", t: "The chain at a glance", x: "Height, block time, transactions, active accounts, dropped transactions, restarts and rule changes. Hover a tile for what it counts." },
      { s: ".p-blocks", t: "Block time", x: "Seconds between one block and the next. The band shows the usual range and slow blocks stand out as dots, so a hiccup is easy to spot." },
      { s: ".p-types", t: "What people do on the chain", x: "Transfers, own rules, rule offers and votes, counted by type. “Table” on any chart shows the numbers behind it." },
      { s: ".p-drop", t: "Dropped transactions", x: "Transactions that left our node’s waiting list without a block, newest first, with the reason when the node gives one." },
      { s: ".p-rs", t: "Restarts", x: "The testnet starts over from time to time. Each restart is listed, so numbers from different chains never get mixed." },
    ] },
    proposals: { name: "Proposals", intro: "Every rule change from proposal to law, and how to hear about the next one the moment it happens.", steps: [
      { s: "#tiles", t: "The rules in force, in six numbers", x: "Rule revision, base fee, validators, votes needed to agree, proposals so far and the newest block. Each one is part of the chain state." },
      { s: ".p-rules", t: "Rules over time", x: "Every rule change on one line: a short mark where it went to a vote, a diamond where it became law. Each block is judged by the rules in force at its height." },
      { s: ".p-open", t: "Coming up", x: "Proposals waiting for votes or for their activation block. Click one for its rule text, its votes and when it applies." },
      { s: ".p-all", t: "Everything decided", x: "Every proposal on this chain, in force or dropped, with filters. Nothing here can be changed quietly." },
      { s: [".p-news", "#follow"], t: "Never miss one", x: "News shows exactly what our Telegram channel and RSS feed post. Follow either and you hear about every rule change as it happens." },
    ] },
    nodes: { name: "Nodes", intro: "The community nodes that check the chain themselves, and how to put your own on the board.", steps: [
      { s: ".intro .kpis", t: "How many are watching", x: "Nodes online, nodes on our chain and community nodes. Every node that checks the chain itself makes it harder to fake." },
      { s: ".panel.board", t: "Leaderboard", x: "Online nodes first, then the longest running, then the steadiest. Hover the column titles for what each one means." },
      { s: ".panel.badge", t: "A badge for your node", x: "Pick your node and copy a live badge for your README or website. It shows uptime and sync as they are." },
      { s: "#join", t: "Run a node", x: "Three steps and about an hour and a half on a small server. No server yet? Try a simulated node in your browser first." },
      { s: ".panel.gets", t: "What you get", x: "Your name on the board, a live badge, a chain you checked yourself and a head start for a validator seat." },
    ] },
    meta: { name: "In numbers", intro: "How much our two sites move the testnet, and how many people visit them. Counted without cookies; a wallet is a key, not a person.", steps: [
      { s: ".intro .sites", t: "Three views", x: "On the testnet shows what our sites move on Tau Testnet Alpha. Tau HUD and Agorzilla show each site's visitors." },
      { s: ".intro .kpis", t: "The short version", x: "The four numbers that matter most for the view you picked." },
      { s: "#pDaily", t: "Day by day", x: "Wallets acting through our sites each day, or visitors in the visitor views. Pick 24H up to All, line or bars; hover for the numbers, click a day for details." },
      { s: "#dayPanel", t: "One day up close", x: "Everything about the day you clicked: wallets, new and returning ones and each site's part, or visitors and their pages." },
      { s: "#pGrowth", t: "The climb", x: "Wallets reached, or visits, added up over time." },
      { s: "#pPages", t: "Agorzilla and pages", x: "On the testnet: what Agorzilla's meals and votes add up to. In the visitor views: the most visited pages." },
    ] },
    status: { name: "Status", intro: "Is our node up and in sync, how healthy is the testnet, and what happened in the last 30 days.", steps: [
      { s: "#lead", t: "The answer first", x: "One line says whether our node is up and in sync with the testnet. Everything below backs it up." },
      { s: "#health", t: "Testnet health", x: "A score out of 100, the points lost and why, and the last 30 days as a small line." },
      { s: "#tiles", t: "From the testnet to your screen", x: "Relay, node, sync, newest verified block and last block: each tile is one link in the chain that brings the testnet to this site." },
      { s: ".p-days", t: "Last 30 days", x: "One bar per day for each part. Click a day for what happened." },
      { s: ".p-inc", t: "Incidents", x: "Restarts, outages and sync gaps, each with when it happened and what it meant." },
      { s: ".p-known", t: "Known issues", x: "Testnet bugs that change what you see on this site, with a link to every finding we reported." },
    ] },
    findings: { name: "Findings", intro: "What broke while we ran a node for this site, what we reported to IDNI and what got fixed.", steps: [
      { s: "#tiles", t: "Filed, fixed, patched", x: "Issues filed with IDNI, bugs still open, fixes by IDNI and patches running in our node today." },
      { s: ".p-issues", t: "Filed with IDNI", x: "Every issue we reported, with its status live from GitHub. Click a finding for what broke, how we found it and what changed since." },
      { s: ".p-report", t: "Found a bug yourself?", x: "IDNI has no official bounty program, but now and then gives ad hoc community rewards for useful findings and effort. Here is where to report a bug and what a report needs so it gets fixed." },
      { s: ".p-fixes", t: "Also patched in our node", x: "Fixes we run that have no IDNI issue of their own, each with what it does." },
    ] },
    chronicle: { name: "the Chronicle", intro: "Twelve years of Tau on one page, from Zennet in 2014 to a testnet that changes its own rules.", steps: [
      { s: "section.strip", t: "Twelve years on one line", x: "Each band is an era, each dot a moment. Click a dot for its story and the video it comes from." },
      { s: "#eras", t: "Five eras, every moment", x: "From the first vision to a chain that changes itself. Click any moment to read it above." },
      { s: ".p-gone", t: "Dropped along the way", x: "Ideas and tools the project tried and left behind. They make today’s design easier to understand." },
    ] },
    story: { cta: false, name: "Tau in 60 seconds", intro: "How Tau changes its rules without a fork, in six short steps you scroll through.", steps: [
      { s: ".stage", t: "The picture plays the story", x: "The drawing follows the text: first the usual hard fork, then how a rule change on Tau is proposed, checked, agreed and made law." },
      { s: "#step-1", t: "Scroll to play", x: "Scroll down and each step takes over the picture. At the end you can watch it live, try it in the Playground or follow the alerts." },
    ] },
    developers: { name: "Developers", intro: "Put the live testnet on your own site: a widget, a badge or the JSON API.", steps: [
      { s: "main.main > section.panel:nth-of-type(1)", t: "A widget for any page", x: "Live numbers in three sizes, dark, light or clear. Pick the boxes, copy one line, paste it into your page." },
      { s: "main.main > section.panel:nth-of-type(2)", t: "Badges that stay current", x: "Small images for a README or a forum signature, refreshed every minute." },
      { s: "main.main > section.panel:nth-of-type(3)", t: "A free JSON API", x: "Everything this site reads is open to you, from any origin, without a key. The example below shows the live answer." },
    ] },
    press: { name: "the press kit", intro: "Films, a ready paragraph, the facts, the logo and screenshots, free to use with credit.", steps: [
      { s: ".films-panel", t: "Films first", x: "Tau in 60 seconds and eight short feature films, in English and Chinese, with sound. Each one can be downloaded." },
      { s: ".cT > section.panel:nth-of-type(1)", t: "A ready paragraph", x: "One paragraph that says what Tau HUD is. Copy it as it is." },
      { s: ".cT > section.panel:nth-of-type(2)", t: "The facts", x: "Name, what, who, where and the numbers, checked and short." },
      { s: ".cL", t: "The logo", x: "“Pulse”: a heartbeat inside a ring, as SVG and PNG." },
      { s: ".cS > section.panel:nth-of-type(1)", t: "Screenshots", x: "Desktop and phone, full size on click, or all of them as one download." },
    ] },
    missions: { name: "Missions", intro: "Six short tasks on a practice chain of your own: pass a rule, get one refused, switch to proof of stake.", steps: [
      { s: ".pmis", t: "Six missions", x: "Each one is a short task with a clear goal. Your progress stays in this browser." },
      { s: "#brief", t: "Your mission", x: "What to do, step by step, with a hint. “On the real testnet” shows that the same thing happens on Tau." },
      { s: ".pchain", t: "Your practice chain", x: "You hold one validator seat. The rules, the blocks and every seat update live as you play." },
      { s: "#prop", t: "Propose and vote", x: "Put a change to a vote and win the others over. When enough agree, it becomes law on your chain." },
    ] },
    whatif: { name: "What if", intro: "Move block time, validators and votes needed, and watch a sandbox chain react.", steps: [
      { s: ".levers", t: "Move a lever", x: "Block time, validators, votes needed, validators offline and network delay. Or start from a preset such as “Real testnet today”." },
      { s: ".stage", t: "The chain reacts at once", x: "Newest block on the right. When a block arrives too late, two blocks land at one height: a short split that the next block settles. It is not the fork Tau avoids, changing the rules never needs one. Hover a block, click it for its story." },
      { s: "#agree", t: "Rule changes need votes", x: "Every rule change needs yes votes from the validators before its deadline. Raise the bar or take validators offline and see what passes." },
      { s: ".side > section.panel:nth-of-type(1)", t: "What happens, in plain words", x: "One verdict for your settings, in plain words. The panel below counts what changed since your last move." },
    ] },
    wallet: { name: "the wallet", intro: "A testnet account with its own rules: send, take back, co-sign, and give your account a rule the chain enforces.", steps: [
      { s: "#acct", go: "#acctTabs button[data-atab=acct]", t: "Your account, in this browser", x: "A key is drawn here and never leaves it. Its public half is your address; the balance is in test AGRS, which have no value." },
      { s: "#acct", go: "#tabBook", t: "Names, not hex", x: "Put the people you pay in your address book. You pick a name, the page shows the full address with its print, and a lookalike that copies the first and last characters stands out." },
      { s: "#act", go: "#tabSend", t: "Send, take back, split, vote", x: "Send a payment, send one with a way back that you can take back until it is released, pay several people at once, or say yes to a rule change of the chain." },
      { s: "#sign", t: "Before you sign", x: "The amount and the recipient in large type, then what your rule says, the fee and whether there is a way back. If your rule would stop it, nothing is sent." },
      { s: "#build", go: "#ruleTabs button[data-rtab=mine]", t: "Give your account a rule", x: "Tick the blocks you want: only to people in your book, a limit per payment, a date before which nothing leaves, a co-signer for larger payments. The chain checks it on every payment, even one signed with a stolen key." },
      { s: "#probes", t: "Test it before you sign", x: "Example payments run against the rule on the screen: to a friend, to a lookalike, to someone new and a large one. You see what goes through before anything is signed." },
      { s: "#slots", t: "Two rule places", x: "Tau Testnet Alpha holds personal rules for 2 accounts at a time. This shows how many are taken and whether one is yours." },
      { s: "#activity", t: "What waits for you", x: "Rules offered to you, with the node's own check, requests to co-sign, payments you can still take back and everything you sent. On a first visit it shows the first steps." },
    ] },
    vote: { name: "Vote for real", intro: "Vote on the real testnet yourself, after practising the same commands here first.", steps: [
      { s: ".intro .kpis", t: "Open now", x: "Proposals waiting for votes, yes votes needed and who may vote, read from the chain." },
      { s: "#real", t: "Step by step on the real testnet", x: "From running your own node to the ready command for your vote. Every step says how long it takes." },
      { s: "#practice", t: "Practise first", x: "The same commands in a practice terminal. Nothing leaves your browser, so try as often as you like." },
      { s: ".follow", t: "Follow your vote", x: "Paste your public key and this page shows when your vote reaches the chain." },
      { s: ".facts", t: "Good to know", x: "Any account may vote, two thirds decide, a vote is free and counts once, and nothing changes at once." },
    ] },
    card: { name: "your Tau card", intro: "One picture of what your test wallet did on Tau Testnet Alpha, with Agorzilla reading it beside you.", steps: [
      { s: "#card", t: "Your card", x: "Read straight from the testnet: rules written, votes cast, Agorzilla meals and café stamps. A tile lights up once something is in it. Nothing on it is priced or promised." },
      { s: "#agz", t: "Agorzilla reads it with you", x: "His mood is your card. An empty card makes him cry; every rule, vote, meal and stamp cheers him up, and a full card makes him beam. Tap him." },
      { s: "#paper", t: "Stamps from the café", x: "This week's Daily Consensus lies at his feet, your café ticket on top. In the paper's café four regulars each stamp the ticket. Click it to walk in." },
      { s: "#pFill", t: "Fill your card", x: "What is still open, each with the page where you do it." },
      { s: "#pShare", t: "Pass it on", x: "Post it on X or copy the link: the link shows this card as its preview on X, Telegram and WhatsApp." },
    ] },
    gazette: { cta: false, name: "The Daily Consensus", intro: "Twelve years of Tau as a 1920s newspaper.", steps: [
      { s: "#stage", t: "Turn the pages", x: "Click or tap the page to turn it. The arrow keys work too." },
      { s: "#ctl", t: "Contents and pocket edition", x: "Jump to any story from the contents, switch to the pocket edition for small screens, or turn the sound on." },
    ] },
  };
  const T = TOURS[PAGE];
  if (!T) { window.TauTour = { has: false, start() {} }; return; }
  const KEY = "tau-tour-" + PAGE;

  const css = document.createElement("style");
  css.textContent = `
.tt-card { position: fixed; left: 50%; bottom: 18px; transform: translateX(-50%); z-index: 95; width: min(560px, calc(100% - 32px)); box-sizing: border-box; background: #121214; border: 1px solid rgba(57,255,138,.55); border-radius: 8px; padding: 12px 12px 8px; box-shadow: 0 30px 80px -20px rgba(0,0,0,.95), 0 0 0 1px rgba(0,0,0,.6); font-family: "Sora", "Manrope", "Segoe UI", sans-serif; text-align: left; letter-spacing: 0; text-transform: none; }
.tt-card[hidden], .tt-ring[hidden] { display: none; }
.tt-card, .tt-card * { text-align: left; text-indent: 0; float: none; }
.tt-card.anchored { left: 0; top: 0; bottom: auto; transform: none; width: min(440px, calc(100% - 32px)); }
.tt-card.anchored:is(.side-top, .side-bottom, .side-left, .side-right)::before { content: ""; position: absolute; width: 12px; height: 12px; background: #121214; border: 1px solid rgba(57,255,138,.55); transform: rotate(45deg); }
.tt-card.anchored.side-top::before { top: -7px; left: calc(var(--ax) - 6px); border-right: 0; border-bottom: 0; }
.tt-card.anchored.side-bottom::before { bottom: -7px; left: calc(var(--ax) - 6px); border-left: 0; border-top: 0; }
.tt-card.anchored.side-left::before { left: -7px; top: calc(var(--ay) - 6px); border-top: 0; border-right: 0; }
.tt-card.anchored.side-right::before { right: -7px; top: calc(var(--ay) - 6px); border-bottom: 0; border-left: 0; }
.tt-card .t1 { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; font: 600 11px "Sora", "Segoe UI", sans-serif; letter-spacing: .22em; text-transform: uppercase; color: #39ff8a; }
.tt-card .t1 button { background: transparent; border: 0; color: #7f7f8a; font-size: 13px; cursor: pointer; padding: 2px 4px; letter-spacing: 0; }
.tt-card .t1 button:hover { color: #fff; }
.tt-card h3 { margin: 4px 0 2px; padding: 0; border: 0; font: 600 15px/1.35 "Sora", "Segoe UI", sans-serif; color: #fff; letter-spacing: 0; text-transform: none; }
.tt-card p { margin: 0 0 8px; font: 400 13px/1.5 "Sora", "Segoe UI", sans-serif; color: #ebebee; max-width: 76ch; }
.tt-card .bar { height: 2px; background: rgba(255,255,255,.1); margin: 8px 0; border-radius: 1px; overflow: hidden; }
.tt-card .bar i { display: block; height: 100%; width: 0; background: #39ff8a; transition: width .3s; }
.tt-card .t3 { display: flex; gap: 8px; justify-content: flex-end; }
.tt-card .t3 button { font: 600 11px "Sora", "Segoe UI", sans-serif; letter-spacing: .14em; text-transform: uppercase; border-radius: 999px; padding: 6px 12px; min-height: 30px; cursor: pointer; border: 1px solid rgba(255,255,255,.18); background: transparent; color: #7f7f8a; }
.tt-card .t3 button.primary { background: #fff; color: #000; border-color: #fff; }
.tt-card .t3 button:hover { color: #fff; border-color: #fff; }
.tt-card .t3 button.primary:hover { background: #39ff8a; border-color: #39ff8a; color: #000; }
.tt-card .t3 button:disabled { opacity: .35; cursor: default; }
.tt-ring { position: fixed; z-index: 94; pointer-events: none; border: 1px solid #39ff8a; border-radius: 8px; box-shadow: 0 0 0 1px rgba(57,255,138,.5), 0 0 40px -6px rgba(57,255,138,.55), 0 0 0 200vmax rgba(0,0,0,.55); transition: left .25s, top .25s, width .25s, height .25s; }
@media (prefers-reduced-motion: reduce) { .tt-ring, .tt-card .bar i { transition: none; } }
.tt-cta { display: inline-flex; align-items: center; gap: 7px; margin: 0 0 0 16px; padding: 5px 13px 5px 11px; vertical-align: .2em; border: 1px solid rgba(57,255,138,.6); border-radius: 999px; background: transparent; color: #39ff8a; font: 600 11px/1.2 "Sora", "Segoe UI", sans-serif; letter-spacing: .14em; text-transform: uppercase; white-space: nowrap; cursor: pointer; }
.tt-cta:hover, .tt-cta:focus-visible { background: #39ff8a; border-color: #39ff8a; color: #000; outline: none; }
.tt-cta i { font-style: normal; font-size: 10px; letter-spacing: 0; }
@media (max-width: 899px) { .tt-card { bottom: 72px; } .tt-card .t3 button { min-height: 44px; } .tt-cta { min-height: 44px; margin: 6px 0 0; } }`;
  document.head.append(css);

  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const card = el("aside", "tt-card", `<div class="t1"><span class="tt-step">Guided tour</span><button type="button" class="tt-x" aria-label="End tour">✕</button></div><h3></h3><p></p><div class="bar"><i></i></div><div class="t3"><button type="button" class="tt-back">Back</button><button type="button" class="primary tt-next">Next</button></div>`);
  card.hidden = true; card.setAttribute("aria-live", "polite"); card.setAttribute("role", "dialog"); card.setAttribute("aria-label", "Guided tour");
  const ring = el("div", "tt-ring"); ring.hidden = true;
  document.body.append(ring, card);
  const q = s => card.querySelector(s);

  const visible = e => { if (!e) return false; const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== "hidden"; };
  const find = s => { for (const one of [].concat(s)) { let list = []; try { list = document.querySelectorAll(one); } catch (e) {} for (const n of list) if (visible(n)) return n; } return null; };
  let i = -1, offered = false, target = null, raf = 0, last = "", L = T.steps;
  /* the steps this visit can show: parts in the view that is open, or behind a tab a step opens; empty panels of an offline page are left out */
  const steps = () => T.steps.filter((st, n) => (!st.when || find(st.when)) && (find(st.s) || T.steps.slice(0, n + 1).some(x => x.go)));

  function end(done) {
    if (i >= 0 || offered) store.set(KEY, done ? "done" : "dismissed");
    i = -1; offered = false; target = null; card.hidden = ring.hidden = true; cancelAnimationFrame(raf); raf = 0;
  }
  function show(n, dir, from) {
    if (n < 0 || n >= L.length) return end(n >= L.length);
    const st = L[n];
    if (st.go) { const g = document.querySelector(st.go); if (g && g.getAttribute("aria-selected") !== "true") g.click(); }
    const t = find(st.s);
    if (!t) return show(n + (dir || 1), dir || 1, from);   // a part this page is not showing right now (another view) is skipped
    i = n; offered = false; target = t; last = "";
    t.scrollIntoView({ block: "nearest", behavior: "auto" });
    q(".tt-step").textContent = `Step ${n + 1} of ${L.length}`; q("h3").textContent = st.t; q("p").textContent = st.x;
    q(".bar i").style.width = `${(n + 1) / L.length * 100}%`;
    q(".tt-back").textContent = "Back"; q(".tt-back").disabled = n === 0 || !L.slice(0, n).some(s => find(s.s) || s.go);
    q(".tt-next").textContent = n === L.length - 1 ? "Done" : "Next";
    card.hidden = ring.hidden = false;
    place(true);
    if (!raf) raf = requestAnimationFrame(follow);
    if (from !== "key") q(".tt-next").focus({ preventScroll: true });
  }
  /* the card scales with big screens like the HUD's (between 1 and 1.7) */
  const zoom = () => Math.max(1, Math.min(1.7, innerWidth / 1800, innerHeight / 900));
  /* the ring and the card follow the spotlighted part when the page moves or re-renders */
  function follow() {
    raf = 0; if (i < 0 || !target) return;
    if (!target.isConnected || !visible(target)) { const t = find(L[i].s); if (t) target = t; }
    place(false); raf = requestAnimationFrame(follow);
  }
  function place(force) {
    const r = target.getBoundingClientRect(), key = [r.left, r.top, r.width, r.height, innerWidth, innerHeight].map(Math.round).join();
    if (!force && key === last) return; last = key;
    const pad = 6; Object.assign(ring.style, { left: r.left - pad + "px", top: r.top - pad + "px", width: r.width + 2 * pad + "px", height: r.height + 2 * pad + "px" });
    const z = innerWidth >= 900 ? zoom() : 1; card.style.zoom = z === 1 ? "" : String(z);
    card.classList.remove("side-top", "side-bottom", "side-left", "side-right");
    if (innerWidth < 900) { card.classList.remove("anchored"); card.style.left = card.style.top = ""; return; }   // phones: a sheet at the bottom
    card.classList.add("anchored"); card.style.left = card.style.top = "0px";
    const cr = card.getBoundingClientRect(), cw = cr.width, ch = cr.height, vw = document.documentElement.clientWidth, vh = innerHeight, m = 14 + pad, g = 12;
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const fits = c => c[1] >= g && c[2] >= g && c[1] + cw <= vw - g && c[2] + ch <= vh - g;
    const sideY = Math.min(Math.max(r.top, g), vh - ch - g);
    const cands = [["side-top", cx - cw / 2, r.bottom + m], ["side-left", r.right + m, sideY], ["side-right", r.left - m - cw, sideY], ["side-bottom", cx - cw / 2, r.top - m - ch]];
    const pick = cands.find(fits) || [null, vw - cw - g, vh - ch - g];   // a part as big as the window: the card sits in its lower right corner, over it
    const l = Math.min(Math.max(pick[1], g), vw - cw - g), tp = Math.min(Math.max(pick[2], g), vh - ch - g);
    if (pick[0]) card.classList.add(pick[0]);
    card.style.left = l / z + "px"; card.style.top = tp / z + "px";
    card.style.setProperty("--ax", Math.min(Math.max(cx - l, 18), cw - 18) / z + "px");
    card.style.setProperty("--ay", Math.min(Math.max(cy - tp, 18), ch - 18) / z + "px");
  }
  /* first visit: offer this page's tour once */
  function offer() {
    if (i >= 0 || store.get(KEY) || innerWidth < 900 || document.querySelector(".modal:not([hidden]), .tn-modal:not([hidden])")) return;
    offered = true; target = null; ring.hidden = true;
    card.classList.remove("anchored", "side-top", "side-bottom", "side-left", "side-right"); card.style.left = card.style.top = ""; card.style.zoom = zoom() === 1 ? "" : String(zoom());
    q(".tt-step").textContent = "New here?"; q("h3").textContent = `A short tour of ${T.name}`;
    q("p").innerHTML = ""; q("p").append(el("span", "", ""), " ", el("span", "", ""));
    q("p").firstChild.textContent = T.intro; q("p").lastChild.textContent = `${steps().length} short steps, you can stop at any time.`;
    q(".bar i").style.width = "0"; q(".tt-back").textContent = "Not now"; q(".tt-back").disabled = false; q(".tt-next").textContent = "Start the tour";
    card.hidden = false;
  }
  function start() { if (window.TauNav && TauNav.closeAll) TauNav.closeAll(); L = steps(); show(0); }

  q(".tt-next").onclick = () => offered ? start() : show(i + 1, 1);
  q(".tt-back").onclick = () => offered ? end(false) : show(i - 1, -1);
  q(".tt-x").onclick = () => end(false);
  document.addEventListener("keydown", e => {
    if (card.hidden) return;
    if (e.key === "Escape") return end(false);
    if (i < 0 || e.target.closest("input, textarea, select, [contenteditable]")) return;
    if (e.key === "ArrowRight" || e.key === "Enter") { e.preventDefault(); e.stopImmediatePropagation(); show(i + 1, 1, "key"); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); e.stopImmediatePropagation(); show(i - 1, -1, "key"); }
  }, true);
  window.TauTour = { has: true, start, end: () => end(false) };
  /* a “Take the tour” button at the end of the page's opening line, so the tour is found where reading starts.
     Pages that redraw their opening line (Status) get it back on the next check. */
  const cta = el("button", "tt-cta", "<i>▸</i>Take the tour"); cta.type = "button"; cta.dataset.tnt = "A short guided tour of this page: what each part shows and why it matters. Arrow keys step, Esc ends.";
  cta.addEventListener("click", start);
  const placeCta = () => { const lead = T.cta !== false && document.querySelector("p.lead"); if (lead && !lead.contains(cta)) lead.append(cta); };
  placeCta(); setInterval(placeCta, 2000);
  const params = new URLSearchParams(location.search);
  if (params.get("tour") || location.hash === "#tour") {   // a link with ?tour=1 or #tour starts the tour; the address bar drops it
    params.delete("tour"); try { history.replaceState(history.state, "", location.pathname + (params.toString() ? "?" + params : "") + (location.hash === "#tour" ? "" : location.hash)); } catch (e) {}
    setTimeout(start, 900);
  } else if (!params.has("embed")) setTimeout(offer, 2500);
})();

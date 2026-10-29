/* Tau HUD shared header bar: the same row of sections and utilities on every page.
   A page puts <nav class="tnav" data-page="stats"></nav> under its brand row and loads this file.
   Host elements inside the nav with data-slot="source|state|updates|view|gear" are kept and placed;
   anything missing is generated as a link to the HUD. */
(() => {
  "use strict";
  const TELEGRAM = "https://t.me/tauHUDcom";
  const LATEST = "v17.69"; // fallback only: the green dot keys on the newest entry of assets/updates.json (tag|date), read below
  let LATEST_ID = LATEST;
  const SEEN_KEY = "tauhud-updates-seen", VIEW_KEY = "tau-view", VIEWER_KEY = "tauhud-viewer";
  const RELAY = "node.tauhud.com", NET = "tau-testnet-v2";
  const MARK = '<svg class="mark" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="25"/><path class="pulse" d="M13 33 H23 L27.5 24 L34.5 43 L39 33 H51"/></svg>';
  const src = document.currentScript && document.currentScript.src;
  const ROOT = src ? new URL("..", src).pathname : "/";
  const P = {
    hud:        { t: "HUD", d: "The chain core live: blocks, rules and agreement as they happen", i: "◉", h: "" },
    explorer:   { t: "Explorer", d: "Find any block, transaction or address", i: "⌕", h: "explorer/", view: true },
    stats:      { t: "Stats", d: "Block pace, transactions, validators and rule changes over the whole chain", i: "≋", h: "stats/", view: true },
    history:    { t: "Time travel", d: "Step through the chain block by block and see the rules at any height", i: "⟲", h: "history/" },
    account:    { t: "Accounts", d: "Balance, own rules, offers and refusals of any address", i: "@", h: "account/", view: true },
    nodes:      { t: "Nodes", d: "Community nodes that follow the chain, with badges for uptime and sync", i: "◎", h: "nodes/" },
    proposals:  { t: "Proposals", d: "Every rule change from proposal to law, with Telegram and RSS alerts", i: "§", h: "proposals/" },
    story:      { t: "Tau in 60 seconds", d: "Propose, check, agree, law: how Tau changes its rules without a fork", i: "▶", h: "story/" },
    tour:       { t: "Guided tour", d: "One minute, eight steps: how rules change by agreement", i: "▸", h: "?tour=1", act: "tour" },
    gazette:    { t: "The Daily Consensus", d: "Tau as a 1920s newspaper, a new edition every Monday: turn the pages with a click or a tap", i: "❡", h: "gazette/" },
    chronicle:  { t: "Chronicle", d: "Tau from the first videos in 2014 to the testnet alpha", i: "◷", h: "chronicle/" },
    findings:   { t: "Findings", d: "Issues we reported to IDNI, with their live GitHub status", i: "!", h: "findings/" },
    status:     { t: "Status", d: "Uptime, outages, sync gaps and restarts of the community node", i: "◍", h: "status/" },
    meta:       { t: "Tau HUD in numbers", d: "How many people use this site: visitors per day, growth and the most visited pages", i: "∑", h: "meta/" },
    developers: { t: "Developers", d: "Widgets, badges and a free JSON API for your own site", i: "{}", h: "developers/" },
    press:      { t: "Press kit", d: "Video, logo, screenshots, facts and a ready paragraph, free to use", i: "↓", h: "press/" },
    tau:        { t: "What is Tau?", d: "tau.net, the project behind the testnet", i: "τ", h: "https://tau.net", ext: true },
    legal:      { t: "Privacy", d: "Privacy notice: exactly what this site processes (no cookies, no tracking)", i: "§", h: "legal/" },
    about:      { t: "About Tau HUD", d: "Who built this page, sources, how to support it", i: "i", h: "#about", act: "about" },
    playground: { t: "Playground", d: "Write a transfer rule and run the testnet's own checks on it", i: "◇", h: "playground/" },
    seat:       { t: "Validator seat", d: "Take a simulated seat and vote a rule change into law", i: "✓", h: "playground/#seat" },
    whatif:     { t: "What if", d: "Move block time, validators and votes needed, and watch the chain react", i: "≈", h: "whatif/" },
    vote:       { t: "Vote for real", d: "Vote on the real testnet yourself: node, key, ready commands, practised first", i: "✔", h: "vote/" },
    missions:   { t: "Missions", d: "Six short tasks on a practice chain: pass a rule, fail one, survive an outage, switch to proof of stake", i: "★", h: "missions/" },
  };
  const SECTIONS = [
    { k: "hud", t: "HUD", single: true, tab: "◉" },
    /* grouped by what a visitor came to do (Kilian, 29 Oct): watch the chain, understand Tau, try it, and who runs this site; five to seven entries each */
    { k: "explore", t: "Explore", items: ["explorer", "proposals", "account", "nodes", "stats", "history"], tab: "≋" },
    { k: "learn", t: "Learn", items: ["tour", "story", "gazette", "chronicle", "tau"], tab: "▸" },
    { k: "play", t: "Playground", items: ["playground", "seat", "missions", "whatif", "vote"], id: "btnPlayground", tab: "◇", short: "Play" },
    { k: "about", t: "About", util: true, items: ["about", "status", "findings", "meta", "developers", "press", "legal"], tab: "i" },
  ];
  const SECTION_OF = { hud: "hud", explorer: "explore", stats: "explore", nodes: "explore", history: "explore", account: "explore", proposals: "explore", story: "learn", gazette: "learn", chronicle: "learn", findings: "about", status: "about", meta: "about", legal: "about", developers: "about", press: "about", playground: "play", missions: "play", vote: "play", whatif: "play" };
  const TIPS = {
    state: "Every rule in force right now: spec revision, fee, agreement threshold, validators, agreed changes, personal rules.",
    feedback: "What would you like to see, what is broken? Opens the feedback form right here. Ideas with the most agreement get built first.",
    telegram: "Join @tauHUDcom on Telegram: every new proposal, agreement, activation and chain restart the moment it happens, a weekly recap picture, every HUD update. Questions (height, proposals, your transaction or address): write to @tauhud_alerts_bot. Opens Telegram.",
    updates: "What changed on this page and when, built from your feedback. Also where to leave feedback.",
    gear: "Settings: node address and Connect, background rain.",
    gearSub: "Settings: which node this page reads, guided tour, about.",
    live: "Live node: this page reads the real testnet through the community relay at node.tauhud.com. The choice holds on every page.",
    sim: "Simulation: invented activity that follows the documented protocol, generated in your browser. The same made-up chain on every page, eight seconds per block, a fresh start every day at 00:00 UTC. No real chain data. The choice holds on every page.",
    simMode: "Simulation: this page shows a made-up chain generated in your browser, the same on every page. No real chain data. Switch to Live node for the real testnet.",
    simBadge: "Everything on this page is simulated: invented but protocol-true activity, generated in your browser. Nothing here happened on the real testnet. Opens the full notice.",
    simple: "Simple view: plain words, fewer numbers, no stream names.",
    tech: "Technical view: stream names (i10, o5, o9), hashes and rule text everywhere.",
    unoff: "Built by Tau community members, not by IDNI or the Tau team. No claim of accuracy. Opens the full notice.",
    mode: "Live: this page reads the real testnet through the community relay at node.tauhud.com.",
    online: "People looking at Tau HUD right now, counted by the community relay; no cookies, no analytics, nobody is identified. “—” means the relay has not answered yet.",
    net: "Network id " + "tau-testnet-v2" + ": the chain every page shows, read from the community node.",
    height: "Newest block the community node has verified.",
    rev: "Spec revision: 1 plus every rule change that was agreed and took effect. Opens the chain state in the HUD.",
    fee: "Base fee in AGRS that every transaction pays, set by the consensus rule o9.",
    cons: "Consensus: who may seal the next block. Tau has no proof of work. The mechanism is part of the chain state: a fixed validator list (proof of authority), a validator list kept in the Tau rules, or proof of stake. It switches only through an agreed rule change. Opens the chain state in the HUD.",
    hud: "The chain core live: blocks, rules and agreement as they happen.",
    explore: "Chain data pages: Explorer, Stats, Time travel, Accounts, Nodes, Proposals.",
    learn: "Tau in 60 seconds, Guided tour, Chronicle, Findings, Status, Developers, Press kit, What is Tau?, About.",
    play: "Write your own transfer rule and run the testnet’s own checks on it, take a simulated validator seat, play six short missions on a practice chain, move the levers of a sandbox chain, or vote on the real testnet yourself.",
  };
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  /* simulation mode (assets/sim.js): the header reads the simulated chain and says so; the people-online count stays real */
  const SIM = !!(window.TauSim && TauSim.on);
  if (SIM) document.documentElement.classList.add("tau-sim");
  const BUBBLE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 3h16a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H9l-5 4v-4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zm3 5v2h10V8H7zm0 4v2h7v-2H7z"/></svg>';
  const PLANE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21.9 3.3 2.6 10.8c-1 .4-1 1 0 1.3l4.9 1.5 11.4-7.2c.5-.3 1-.1.6.2l-9.2 8.3-.4 5.1c.5 0 .7-.2 1-.5l2.4-2.3 5 3.7c.9.5 1.6.2 1.8-.9l3.3-15.5c.3-1.3-.5-1.9-1.5-1.5z"/></svg>';
  /* the site version: every release counts, on any page. Entries up to v17.53 keep what they showed (a HUD number or a page name);
     after it every entry adds one to the minor number, an entry with a "major" (a new page or big feature) starts the next whole number,
     and a backfilled entry (written later about an earlier day) adds nothing. Computed while rendering, so parallel releases never fight over numbers. */
  const SITE_BASE = [17, 53];
  function siteVersions(list) {
    let on = false, [M, m] = SITE_BASE;
    return list.map(e => {
      const tag = String(e && e.tag || "");
      if (!on) { if (tag === `v${SITE_BASE[0]}.${SITE_BASE[1]}`) on = true; return null; }
      if (e.backfill) return null;
      if (e.major) { M += 1; m = 0; } else m += 1;
      return `v${M}.${m}`;
    });
  }
  let SITE_VER = null;
  const emit = action => document.dispatchEvent(new CustomEvent("tau-nav", { detail: action }));
  const markSeen = () => { store.set(SEEN_KEY, LATEST_ID); document.querySelectorAll(".tn-upd.new, .tabbar .new").forEach(e => e.classList.remove("new")); };
  /* the shared update log: newest entry = highest date, then the later line in the file; the dot shows until that entry was seen */
  const checkLog = () => fetch(ROOT + "assets/updates.json", { cache: "no-cache" }).then(r => r.json()).then(list => {
    if (!Array.isArray(list) || !list.length) return;
    SITE_VER = siteVersions(list).filter(Boolean).pop() || null;
    const top = list.map((e, i) => ({ ...e, i })).sort((x, y) => String(y.on || "").localeCompare(String(x.on || "")) || y.i - x.i)[0];
    LATEST_ID = `${top.tag}|${top.on}`;
    const fresh = store.get(SEEN_KEY) !== LATEST_ID;
    document.querySelectorAll(".tn-upd, .tabbar .tb-upd").forEach(e => e.classList.toggle("new", fresh));
  }).catch(() => { const fresh = store.get(SEEN_KEY) !== LATEST; document.querySelectorAll(".tn-upd, .tabbar .tb-upd").forEach(e => e.classList.toggle("new", fresh)); });

  /* ---------- the Updates overlay, in place on every page but the HUD (which has its own, with the feedback box that needs no account) ---------- */
  const DONATE = { addr: "0x23fB76A33A8d70f5c51aB558b85e4b93040003eb", donors: "https://node.tauhud.com/donations.json", qr: `<svg class="tn-qr" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 33 33" shape-rendering="crispEdges" role="img" aria-label="QR code of the donation address"><rect width="33" height="33" fill="#fff"/><path d="M2 2h7v1h-7zM11 2h2v1h-2zM16 2h1v1h-1zM20 2h1v1h-1zM22 2h1v1h-1zM24 2h7v1h-7zM2 3h1v1h-1zM8 3h1v1h-1zM11 3h1v1h-1zM14 3h1v1h-1zM17 3h1v1h-1zM19 3h2v1h-2zM22 3h1v1h-1zM24 3h1v1h-1zM30 3h1v1h-1zM2 4h1v1h-1zM4 4h3v1h-3zM8 4h1v1h-1zM10 4h1v1h-1zM13 4h1v1h-1zM17 4h2v1h-2zM20 4h1v1h-1zM24 4h1v1h-1zM26 4h3v1h-3zM30 4h1v1h-1zM2 5h1v1h-1zM4 5h3v1h-3zM8 5h1v1h-1zM10 5h1v1h-1zM12 5h1v1h-1zM14 5h2v1h-2zM17 5h4v1h-4zM24 5h1v1h-1zM26 5h3v1h-3zM30 5h1v1h-1zM2 6h1v1h-1zM4 6h3v1h-3zM8 6h1v1h-1zM10 6h1v1h-1zM12 6h1v1h-1zM16 6h1v1h-1zM21 6h2v1h-2zM24 6h1v1h-1zM26 6h3v1h-3zM30 6h1v1h-1zM2 7h1v1h-1zM8 7h1v1h-1zM10 7h1v1h-1zM13 7h2v1h-2zM17 7h1v1h-1zM22 7h1v1h-1zM24 7h1v1h-1zM30 7h1v1h-1zM2 8h7v1h-7zM10 8h1v1h-1zM12 8h1v1h-1zM14 8h1v1h-1zM16 8h1v1h-1zM18 8h1v1h-1zM20 8h1v1h-1zM22 8h1v1h-1zM24 8h7v1h-7zM10 9h1v1h-1zM14 9h1v1h-1zM17 9h1v1h-1zM2 10h1v1h-1zM4 10h5v1h-5zM12 10h1v1h-1zM15 10h1v1h-1zM17 10h4v1h-4zM22 10h1v1h-1zM24 10h5v1h-5zM2 11h4v1h-4zM11 11h3v1h-3zM16 11h1v1h-1zM21 11h1v1h-1zM24 11h1v1h-1zM26 11h1v1h-1zM30 11h1v1h-1zM2 12h4v1h-4zM7 12h2v1h-2zM12 12h2v1h-2zM17 12h2v1h-2zM22 12h8v1h-8zM2 13h1v1h-1zM6 13h1v1h-1zM9 13h1v1h-1zM11 13h2v1h-2zM22 13h2v1h-2zM26 13h2v1h-2zM29 13h2v1h-2zM3 14h1v1h-1zM8 14h3v1h-3zM12 14h2v1h-2zM15 14h1v1h-1zM17 14h4v1h-4zM22 14h1v1h-1zM26 14h1v1h-1zM28 14h2v1h-2zM2 15h1v1h-1zM4 15h1v1h-1zM6 15h1v1h-1zM13 15h1v1h-1zM16 15h1v1h-1zM19 15h1v1h-1zM21 15h1v1h-1zM23 15h5v1h-5zM30 15h1v1h-1zM2 16h4v1h-4zM7 16h2v1h-2zM13 16h3v1h-3zM17 16h2v1h-2zM20 16h1v1h-1zM22 16h1v1h-1zM25 16h1v1h-1zM28 16h2v1h-2zM3 17h1v1h-1zM5 17h1v1h-1zM7 17h1v1h-1zM9 17h2v1h-2zM13 17h2v1h-2zM16 17h2v1h-2zM20 17h2v1h-2zM23 17h1v1h-1zM26 17h2v1h-2zM29 17h1v1h-1zM2 18h1v1h-1zM4 18h1v1h-1zM6 18h4v1h-4zM11 18h1v1h-1zM13 18h4v1h-4zM18 18h2v1h-2zM23 18h1v1h-1zM25 18h1v1h-1zM29 18h2v1h-2zM2 19h3v1h-3zM9 19h2v1h-2zM12 19h2v1h-2zM20 19h3v1h-3zM24 19h1v1h-1zM26 19h1v1h-1zM30 19h1v1h-1zM2 20h1v1h-1zM4 20h1v1h-1zM7 20h3v1h-3zM12 20h3v1h-3zM16 20h2v1h-2zM19 20h2v1h-2zM22 20h1v1h-1zM25 20h1v1h-1zM28 20h1v1h-1zM2 21h1v1h-1zM4 21h4v1h-4zM9 21h1v1h-1zM11 21h1v1h-1zM16 21h1v1h-1zM20 21h1v1h-1zM22 21h1v1h-1zM24 21h1v1h-1zM26 21h1v1h-1zM29 21h1v1h-1zM2 22h1v1h-1zM4 22h2v1h-2zM8 22h6v1h-6zM15 22h3v1h-3zM19 22h2v1h-2zM22 22h8v1h-8zM10 23h4v1h-4zM18 23h2v1h-2zM21 23h2v1h-2zM26 23h2v1h-2zM30 23h1v1h-1zM2 24h7v1h-7zM11 24h5v1h-5zM17 24h1v1h-1zM20 24h3v1h-3zM24 24h1v1h-1zM26 24h4v1h-4zM2 25h1v1h-1zM8 25h1v1h-1zM10 25h1v1h-1zM17 25h2v1h-2zM20 25h1v1h-1zM22 25h1v1h-1zM26 25h1v1h-1zM29 25h2v1h-2zM2 26h1v1h-1zM4 26h3v1h-3zM8 26h1v1h-1zM10 26h2v1h-2zM13 26h1v1h-1zM17 26h4v1h-4zM22 26h9v1h-9zM2 27h1v1h-1zM4 27h3v1h-3zM8 27h1v1h-1zM10 27h3v1h-3zM14 27h1v1h-1zM22 27h2v1h-2zM25 27h1v1h-1zM27 27h1v1h-1zM29 27h2v1h-2zM2 28h1v1h-1zM4 28h3v1h-3zM8 28h1v1h-1zM10 28h1v1h-1zM15 28h4v1h-4zM21 28h1v1h-1zM24 28h1v1h-1zM26 28h1v1h-1zM28 28h2v1h-2zM2 29h1v1h-1zM8 29h1v1h-1zM11 29h2v1h-2zM17 29h2v1h-2zM22 29h2v1h-2zM25 29h3v1h-3zM29 29h1v1h-1zM2 30h7v1h-7zM10 30h2v1h-2zM13 30h2v1h-2zM17 30h1v1h-1zM19 30h1v1h-1zM21 30h1v1h-1zM23 30h1v1h-1zM26 30h1v1h-1z" fill="#000"/></svg>` };
  const UPD = { el: null, loaded: false, donorsAt: 0 };
  const logDate = iso => { const d = new Date(iso + "T00:00:00Z"); return isNaN(d) ? iso : `${d.getUTCDate()} ${"Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(" ")[d.getUTCMonth()]} ${d.getUTCFullYear()}`; };
  function buildUpdates(page) {
    const lang = new URLSearchParams(location.search).get("lang"), q = lang ? "?lang=" + encodeURIComponent(lang) : "";
    const title = (P[page] && P[page].t) || page || "Page";
    const m = el("div", "tn-modal"); m.id = "tnUpdates"; m.hidden = true;
    /* the same markup as the HUD's own overlay, so both look alike; the feedback form opens a pre-filled GitHub issue, as on the public HUD */
    m.innerHTML = `<div class="tn-sheet" role="dialog" aria-modal="true" aria-labelledby="tnUpdTitle"><button class="tn-close" type="button" aria-label="Close">✕</button>
      <section class="tn-community">
      <p class="tn-tgstrip"><a href="${TELEGRAM}" target="_blank" rel="noopener">Telegram @tauHUDcom ↗</a> sends every rule change, chain restart, a weekly recap and each HUD update to your phone, so you do not need to check this page. Ask <a href="https://t.me/tauhud_alerts_bot" target="_blank" rel="noopener">@tauhud_alerts_bot ↗</a> for the height, proposals, your transaction or address.</p>
      <div class="tn-col">
      <article class="tn-panel tn-fb">
        <h2 id="tnUpdTitle">Your feedback <small>shapes the next version</small><button class="tn-info" type="button" aria-label="What is this?" data-tip="Tell us what you would like to see. Ideas with the most agreement get built first, which is rather in the spirit of the thing.">i</button></h2>
        <form class="tn-form" novalidate>
          <fieldset class="tn-cats">
            <legend>What is it about?</legend>
            <label><input type="radio" name="tncat" value="idea" checked><span>Feature idea</span></label>
            <label><input type="radio" name="tncat" value="data"><span>Chain data</span></label>
            <label><input type="radio" name="tncat" value="design"><span>Look &amp; feel</span></label>
            <label><input type="radio" name="tncat" value="bug"><span>Something broken</span></label>
          </fieldset>
          <label class="f">What would you like to see on this HUD?
            <textarea class="tn-text" maxlength="2000" placeholder="e.g. show account balances as orbits, add a governance vote timeline, a sound when a block seals…"></textarea>
          </label>
          <label class="f">Name or handle (optional)
            <input type="text" class="tn-name" maxlength="80" placeholder="@yourhandle">
          </label>
          <div class="row">
            <a class="tn-btn tn-send" href="#updates" target="_blank" rel="noopener" aria-disabled="true">Send via GitHub</a>
            <a class="tn-fblink" href="https://github.com/jimb000o/tau-command-hud/issues?q=is%3Aissue+label%3Afeedback" target="_blank" rel="noopener">See all feedback</a>
            <span class="tn-status" aria-live="polite">Feedback becomes a public GitHub issue (free account needed). Upvote ideas you like with 👍.</span>
          </div>
        </form>
        <p class="tn-follow"><a href="${TELEGRAM}" rel="noopener" data-full="A Telegram channel that posts every new proposal, agreement and activation on the testnet. Opens Telegram.">Follow rule changes on Telegram ›</a> <span>· <a href="${ROOT}proposals/${q}">proposal tracker</a></span></p>
      </article>
      <article class="tn-panel tn-keep">
        <h2>Keep it running <small>one person, free time</small><button class="tn-info" type="button" aria-label="What is this?" data-tip="Tau HUD is an independent community project, built and maintained by one person in their free time. The address and the QR code are the same as in About; the numbers above show what the time goes into.">i</button></h2>
        <p class="lead small">Most of what Tau HUD costs is time: following a testnet that changes by agreement and keeping the HUD, the alerts and the bot in step with it. The development tools behind that work are not free either. The server is the smallest part. Donations help cover these costs and are received with thanks.</p>
        <p class="small">AGRS or ETH, one address for both · What it helps pay for: time · tools · server · domain</p>
        <div class="tn-donate">${DONATE.qr}<div class="tn-addr"><code>${DONATE.addr}</code><button class="tn-btn" type="button">Copy</button></div></div>
        <p class="small tn-thanks" hidden></p>
        <p class="small tn-copymsg" aria-live="polite">Check the address against this page before sending; never trust a copy of it from elsewhere.</p>
      </article>
      </div>
      <article class="tn-panel tn-log">
        <h2>Update log <small>built from your feedback</small><button class="tn-info" type="button" aria-label="What is this?" data-tip="What changed and when, newest first. The green number is the site version: it goes up one step with every release on any page, and a new page or big feature starts the next whole number. The name beside it says which part of the site changed and opens it. Before v17.54 only the HUD had numbers.">i</button></h2>
        <div class="tn-effort" hidden><div><b data-n="commits">—</b><span>changes</span></div><div><b data-n="days">—</b><span>days</span></div><div><b data-n="releases">—</b><span>releases</span></div><em data-n="since"></em></div>
        <p class="tn-legend"><i class="ver"></i>Site version, one step per release · <i></i>Part of the site that changed (the name opens it) · Newest first</p>
        <ul class="tn-changes"><li class="day">Loading…</li></ul>
      </article>
      </section></div>`;
    m.querySelector(".tn-close").addEventListener("click", closeUpdates);
    m.addEventListener("click", e => { if (e.target === m) closeUpdates(); });
    m.querySelectorAll(".tn-info").forEach(b => b.addEventListener("click", e => { e.stopPropagation(); const was = b.classList.contains("open"); m.querySelectorAll(".tn-info.open").forEach(x => x.classList.remove("open")); if (!was) b.classList.add("open"); }));
    m.addEventListener("click", () => m.querySelectorAll(".tn-info.open").forEach(x => x.classList.remove("open")));
    /* feedback: the text becomes a pre-filled GitHub issue, with the page and the mode noted at the end */
    const form = m.querySelector(".tn-form"), text = form.querySelector(".tn-text"), name = form.querySelector(".tn-name"), send = form.querySelector(".tn-send"), st = form.querySelector(".tn-status");
    const CAT = { idea: "Feature idea", data: "Chain data", design: "Look & feel", bug: "Something broken" };
    const say = (t, c = "") => { st.textContent = t; st.className = "tn-status " + c; };
    const build = () => {
      const t = text.value.trim(), cat = (form.querySelector('input[name="tncat"]:checked') || {}).value || "idea";
      const ttl = `[${CAT[cat]}] ${t.split("\n")[0].slice(0, 70) || "Feedback"}`;
      const body = `### What would you like to see?\n\n${t}\n\n---\nCategory: ${CAT[cat]}\nFrom: ${name.value.trim() || "anonymous"}\nPage: ${title} · mode: ${SIM ? "sim" : "live"} · version ${SITE_VER || LATEST}`;
      const labels = "feedback," + (cat === "bug" ? "bug" : "enhancement");
      return `https://github.com/jimb000o/tau-command-hud/issues/new?labels=${encodeURIComponent(labels)}&title=${encodeURIComponent(ttl)}&body=${encodeURIComponent(body)}`;
    };
    const sync = () => { const ok = text.value.trim().length >= 3; send.href = ok ? build() : "#updates"; send.setAttribute("aria-disabled", String(!ok)); };
    ["input", "change"].forEach(ev => form.addEventListener(ev, sync)); sync();
    send.addEventListener("click", e => { if (send.getAttribute("aria-disabled") === "true") { e.preventDefault(); say("Write a few words first.", "err"); text.focus(); return; } say("GitHub opens in a new tab with your text filled in. Press “Create” there to send it.", "ok"); });
    form.addEventListener("submit", e => { e.preventDefault(); send.click(); });
    const code = m.querySelector(".tn-addr code"), msg = m.querySelector(".tn-copymsg");
    m.querySelector(".tn-addr button").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(code.textContent); msg.textContent = "Address copied."; }
      catch (e) { const r = document.createRange(); r.selectNodeContents(code); const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r); msg.textContent = "Copy blocked by the browser; the address is selected, press Ctrl/Cmd+C."; }
    });
    document.body.append(m);
    return m;
  }
  function closeUpdates() { if (UPD.el && !UPD.el.hidden) { UPD.el.hidden = true; try { if (location.hash === "#updates") history.replaceState(null, "", location.pathname + location.search); } catch (e) {} } }
  async function openUpdates(page, focusForm) {
    if (!UPD.el) UPD.el = buildUpdates(page);
    UPD.el.hidden = false; markSeen();
    if (focusForm) { UPD.el.querySelector(".tn-sheet").scrollTop = 0; setTimeout(() => { const t = UPD.el.querySelector(".tn-text"); if (t) t.focus({ preventScroll: true }); }, 60); }
    if (!UPD.loaded) { UPD.loaded = true; await updDict(); loadUpdLog(); }
    loadUpdDonors();
  }
  document.addEventListener("keydown", e => { if (e.key === "Escape") closeUpdates(); });
  /* the entries are worded in English and translated with the HUD's dictionary; in Chinese it is fetched once, when the overlay opens */
  const updDict = () => new Promise(res => { if (!document.documentElement.classList.contains("i18n-zh") || !window.TauI18n) return res(); const sc = document.createElement("script"); sc.src = ROOT + "assets/i18n/zh/hud.js"; sc.onload = sc.onerror = res; document.head.append(sc); });
  async function loadUpdLog() {
    const ul = UPD.el.querySelector(".tn-changes"); let list;
    try { list = await (await fetch(ROOT + "assets/updates.json", { cache: "no-cache" })).json(); if (!Array.isArray(list)) throw new Error("not a list"); }
    catch (e) { ul.innerHTML = `<li class="day">Could not load the log (assets/updates.json).</li>`; return; }
    const vers = siteVersions(list); SITE_VER = vers.filter(Boolean).pop() || SITE_VER;
    const order = list.map((e, i) => ({ ...e, i, sv: vers[i] })).sort((x, y) => String(y.on || "").localeCompare(String(x.on || "")) || y.i - x.i);
    const PAGE = { Nodes: "nodes/", Accounts: "account/", Explorer: "explorer/", Proposals: "proposals/", Alerts: "proposals/", Chronicle: "chronicle/", Story: "story/", Newspaper: "gazette/", "Daily Consensus": "gazette/", "Time travel": "history/", Playground: "playground/", "What if": "whatif/", Findings: "findings/", Status: "status/", Stats: "stats/", Developers: "developers/", Press: "press/", Chinese: "?lang=zh", "Guided tour": "playground/#tour" };
    let day = null, html = "";
    for (const e of order) {
      const tag = String(e.tag || ""), on = String(e.on || ""), ver = /^v\d/i.test(tag);
      if (on !== day) { day = on; html += `<li class="day">${logDate(on)}</li>`; }
      const area = e.sv && (ver || tag === "HUD") ? `<a class="tag" href="${ROOT}">HUD</a>` : PAGE[tag] ? `<a class="tag" href="${ROOT}${PAGE[tag]}">${esc(tag)}</a>` : `<b class="tag">${esc(tag)}</b>`;
      const t = e.sv ? `<span class="tags"><b class="tag ver">${esc(e.sv)}</b>${area}</span>` : ver ? `<a class="tag ver" href="${ROOT}">${esc(tag)}</a>` : area;
      html += `<li data-tag="${esc(e.sv && ver ? "HUD" : tag)}">${t}<span class="body">${e.html || esc(e.text || "")}</span></li>`;
    }
    ul.innerHTML = html;
    foldUpdLog(ul);
    loadUpdEffort(list);
  }
  /* the first clause of every entry is the headline, the rest folds away behind it; newest twelve first, twelve more as the bottom comes into view */
  function foldUpdLog(ul) {
    ul.querySelectorAll("li:not(.day)").forEach(li => {
      const b = li.querySelector(".tag"), body = li.querySelector(".body"); if (!b || !body) return;
      const tr = x => window.TauI18n ? TauI18n.t(x) : x, tag = tr(li.dataset.tag || "");
      let text = tr(body.textContent.trim());
      const lead = text.search(/[:：]\s*/), tags = [tag, li.dataset.tag || ""].map(x => x.toLowerCase()).filter(Boolean);
      if (lead > 0 && lead <= 28 && tags.length && !/^v\d/i.test(tag)) { const first = text.slice(0, lead).toLowerCase(); if (tags.some(x => first.includes(x) || x.includes(first))) { text = text.slice(lead).replace(/^[:：]\s*/, ""); text = text.charAt(0).toUpperCase() + text.slice(1); } }
      let cut = text.search(/[:.;]\s|[：。；]/); if (cut < 0 || cut > 90) { const c2 = text.slice(0, 90).search(/,\s|\s\(/); cut = c2 > 20 ? c2 : cut < 0 ? -1 : cut; }
      if (cut > 90 || (cut < 0 && text.length > 90)) { const sp = text.slice(0, 84).lastIndexOf(" "); cut = sp > 20 ? sp : cut; }
      const head = cut > 0 ? text.slice(0, cut).replace(/[:.;,]$/, "") + (/[:.;,]\s|[：。；，]/.test(text.slice(cut, cut + 2)) ? "" : " …") : text, rest = cut > 0 ? text.slice(cut).replace(/^[:.;,：。；，]?\s*/, "") : "";
      body.remove();
      if (rest) { const d = document.createElement("details"), sm = document.createElement("summary"), pr = document.createElement("p"); sm.textContent = head; pr.textContent = rest; d.append(sm, pr); li.append(d); }
      else { const o = document.createElement("div"); o.className = "one"; o.textContent = head; li.append(o); }
    });
    const all = [...ul.querySelectorAll("li:not(.day)")], days = [...ul.querySelectorAll("li.day")];
    let shown = 12;
    const reveal = () => {
      all.forEach((li, i) => { li.hidden = i >= shown; });
      days.forEach(d => { let n = d.nextElementSibling, any = false; while (n && !n.classList.contains("day")) { if (!n.hidden && !n.classList.contains("sentinel")) any = true; n = n.nextElementSibling; } d.hidden = !any; });
    };
    reveal();
    if (all.length > shown) {
      const tail = document.createElement("li"); tail.className = "sentinel"; tail.setAttribute("aria-hidden", "true"); ul.append(tail);
      const more = () => { shown += 12; reveal(); if (shown >= all.length) { io.disconnect(); tail.remove(); } };
      const io = "IntersectionObserver" in window ? new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) more(); }, { root: ul, rootMargin: "0px 0px 160px 0px" }) : null;
      if (io) io.observe(tail); else { shown = all.length; reveal(); tail.remove(); }
    }
  }
  /* effort, counted rather than claimed: changes pushed to the public repository and days since its first commit (GitHub API, cached an hour in this browser), releases from the log */
  async function loadUpdEffort(list) {
    const releases = list.length; let git = null;
    try { const c = JSON.parse(store.get("tau-effort") || "null"); if (c && Date.now() - c.at < 3600000) git = c.git; } catch (e) {}
    if (!git) {
      try {
        const h = { headers: { Accept: "application/vnd.github+json" } }, base = "https://api.github.com/repos/jimb000o/tau-command-hud";
        const repo = await (await fetch(base, h)).json();
        const r = await fetch(`${base}/commits?per_page=1`, h), m = /page=(\d+)>;\s*rel="last"/.exec(r.headers.get("Link") || "");
        git = { since: String(repo.created_at || "").slice(0, 10), commits: m ? Number(m[1]) : 1 };
        if (git.since && git.commits > 1) store.set("tau-effort", JSON.stringify({ at: Date.now(), git })); else git = null;
      } catch (e) { git = null; }
    }
    if (!git) return;
    const days = Math.max(1, Math.floor((Date.now() - new Date(git.since + "T00:00:00Z")) / 86400000) + 1), e = UPD.el.querySelector(".tn-effort");
    e.querySelector('[data-n="commits"]').textContent = fmt(git.commits); e.querySelector('[data-n="days"]').textContent = String(days); e.querySelector('[data-n="releases"]').textContent = String(releases); e.querySelector('[data-n="since"]').textContent = `since ${logDate(git.since)}`; e.hidden = false;
  }
  async function loadUpdDonors() {
    if (Date.now() - UPD.donorsAt < 120000) return; UPD.donorsAt = Date.now();
    try {
      const d = await (await fetch(DONATE.donors, { cache: "no-store" })).json(), line = UPD.el.querySelector(".tn-thanks");
      const items = (d.items || []).filter(x => /^0x[0-9a-f]{40}$/i.test(x.from) && /^0x[0-9a-f]{64}$/i.test(x.tx) && (x.asset === "AGRS" || x.asset === "ETH") && isFinite(x.amount));
      if (!items.length) { line.hidden = true; return; }
      const short = a => a.slice(0, 6) + "…" + a.slice(-4);
      const amt = x => { const n = Number(x.amount); return (n >= 100 ? Math.round(n).toLocaleString("en-US") : String(+n.toFixed(n >= 1 ? 2 : 4))) + " " + x.asset; };
      const day = x => new Date(x.ts * 1000).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
      const one = x => `<a href="https://etherscan.io/tx/${encodeURIComponent(x.tx)}" target="_blank" rel="noopener">${short(x.from)}</a> (${amt(x)}, ${day(x)})`;
      const n = Math.max(1, parseInt(d.donors, 10) || 1);
      line.innerHTML = (n === 1 ? "Supported by 1 person so far. Thank you, " : `Supported by ${n} people so far. Thank you, `) + items.slice(0, 3).map(one).join(", ") + (items.length > 3 ? " and everyone before." : ".");
      line.hidden = false;
    } catch (e) { UPD.donorsAt = 0; }
  }

  function item(k, page, isHud, tip) {
    const p = P[k], a = el(p.soon ? "div" : "a", "mi" + (k === page ? " here" : "") + (p.soon ? " soon" : ""));
    a.setAttribute("role", "menuitem");
    a.innerHTML = `<span class="ic">${p.i}</span><b>${esc(p.t)}${p.ext ? ' <span class="ext">↗</span>' : ""}</b><span>${esc(p.d)}</span>`;
    if (p.soon) { a.setAttribute("aria-disabled", "true"); a.title = "This page is not online yet"; }
    else if (p.ext) { a.href = p.h; a.target = "_blank"; a.rel = "noopener"; }
    else if (p.act && isHud) { a.href = "#"; a.addEventListener("click", e => { e.preventDefault(); closeAll(); emit(p.act); }); }
    else a.href = ROOT + p.h;
    if (k === page) a.setAttribute("aria-current", "page");
    return a;
  }

  /* ---------- row 1 on subpages: the HUD's brand row with the page title where the tagline sits, and the same chips fed by the relay ---------- */
  function mountRail(nav, page) {
    const old = nav.previousElementSibling && nav.previousElementSibling.tagName === "HEADER" ? nav.previousElementSibling : null;
    const tEl = old && old.querySelector(".brand span");
    const title = (tEl && tEl.textContent.trim()) || (P[page] && P[page].t) || "";
    const own = old && old.querySelector("#state");
    const rail = el("header", "trail");
    const brand = el("a", "brand", `${MARK}<span class="bn">Tau HUD</span><h1 class="bt">${esc(title)}</h1>`);  // the page title is the heading, the logo is not
    const lang = new URLSearchParams(location.search).get("lang"); brand.href = ROOT + (lang ? "?lang=" + encodeURIComponent(lang) : ""); brand.dataset.tnt = "Back to the HUD";
    const unoff = el("a", "chip unoff" + (SIM ? " sim" : ""), SIM ? "Simulation · no real chain data" : "Unofficial community project · not affiliated with IDNI"); unoff.href = ROOT + "#about"; unoff.dataset.tnt = SIM ? TIPS.simBadge : TIPS.unoff;
    const chips = el("div", "chips");
    const chip = (tag, id, cls, html, t) => { const c = el(tag, "chip" + (cls ? " " + cls : ""), html); c.id = id; c.dataset.tnt = t; return c; };
    chips.append(
      chip("div", "tnMode", "v", SIM ? '<span class="dot sim"></span><b>Simulation</b>' : '<span class="dot none"></span><b>Live · Connecting</b>', SIM ? TIPS.simMode : TIPS.mode),
      chip("div", "tnOnline", "", '<span class="dot none"></span><b class="n">—</b>online', TIPS.online),
      chip("a", "tnCons", "v", '<b><span class="lg">—</span><span class="sh">—</span></b>', TIPS.cons),
      chip("div", "tnNet", "v", `<b>${NET}</b>`, TIPS.net),
      chip("div", "tnHeight", "v", "<b>—</b>", TIPS.height),
      chip("a", "tnRev", "v", "<b>—</b>", TIPS.rev),
      chip("div", "tnFee", "v", "<b>—</b>", TIPS.fee));
    chips.querySelectorAll(".chip.v > b").forEach(b => { b.style.marginLeft = "0"; });   // value-only chips: the name lives in the hover text
    chips.querySelector("#tnRev").href = chips.querySelector("#tnCons").href = ROOT + "#chain-state";
    if (!SIM) {   // coming up on the live chain: an agreed rule change that is not yet in force, counted down from the relay's proposals file
      const nx = el("a", "chip next", "<b></b>"); nx.id = "tnNext"; nx.hidden = true; nx.href = ROOT + "proposals/" + (lang ? "?lang=" + encodeURIComponent(lang) : ""); chips.append(nx);
    }
    if (own) chips.append(own);
    rail.append(brand, unoff, chips);
    if (old) old.replaceWith(rail); else nav.before(rail);
    feedChips(rail);
    return rail;
  }
  function viewerId() {   // one random id per page view, in memory only: nothing about the visitor is stored in the browser
    try {
      if (!window.__tauViewer) window.__tauViewer = Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, "0")).join("");
      try { localStorage.removeItem(VIEWER_KEY); } catch (e) {}   // the id older versions kept in the browser
      return window.__tauViewer;
    } catch (e) { return ""; }
  }
  const fmt = n => Number(n).toLocaleString("en-US");
  const CHAIN = { st: null, polled: false, wsUp: false, online: null, rev: null, fee: null, elig: null, vals: null, switches: 0 };
  /* consensus mechanism as the node reports it (eligibility_mode); the genesis spec's constant o7 = 1 also means the fixed list */
  const CONS = { validator_set: ["Proof of authority", "PoA", "a fixed validator list (proof of authority): the listed validators take turns sealing blocks, each seal signed with BLS and checked by the Tau rules"],
    tau_validator_set: ["Validator list in Tau", "Tau list", "a validator list kept in the Tau rules themselves: rule o7 decides who may seal"],
    stake: ["Proof of stake", "PoS", "proof of stake: the Tau rules (o7) judge who may seal by stake"] };
  const consTip = () => {
    const c = CONS[CHAIN.elig], v = CHAIN.vals;
    if (!c) return TIPS.cons;
    return `Consensus right now: ${c[2]}.` + (v != null ? ` ${v} active validator${v === 1 ? "" : "s"}.` : "") +
      ` Tau has no proof of work. The mechanism is chain state and switches (fixed list, list in Tau, stake) only through an agreed rule change; ${CHAIN.switches ? CHAIN.switches + " switch" + (CHAIN.switches === 1 ? "" : "es") + " so far" : "no switch so far"}. Opens the chain state in the HUD.`;
  };
  function feedChips(rail) {
    const q = s => rail.querySelector(s);
    const mode = q("#tnMode"), modeB = mode.querySelector("b"), modeDot = mode.querySelector(".dot");
    const onChip = q("#tnOnline"), onB = onChip.querySelector("b"), onDot = onChip.querySelector(".dot");
    const hB = q("#tnHeight b"), revB = q("#tnRev b"), feeB = q("#tnFee b"), cons = q("#tnCons");
    const render = () => {
      const st = CHAIN.st, health = st && st.health && typeof st.health.state === "string" ? st.health.state : null;
      const up = !!(st && st.upstream_connected && Number(st.height) > 0) && health !== "down", degraded = up && health === "degraded";
      const hlabel = st && st.health && st.health.label ? String(st.health.label) : "";
      const synced = up && st.live_default === true;
      const catching = synced && Number(st.tip_height) > 0 && st.canonical_height != null && Number(st.canonical_height) < Number(st.tip_height) - 2;
      const wait = !CHAIN.polled;
      const good = synced && !catching && !degraded;
      modeB.textContent = SIM ? "Simulation" : wait ? "Live · Connecting" : !up ? "Live · Offline" : degraded ? "Live · Degraded" : !synced ? "Live · Not synced" : catching ? `Verified to #${fmt(st.canonical_height)} of ${fmt(st.tip_height)}` : "Live · Connected";
      modeDot.className = "dot " + (SIM ? "sim" : wait ? "none" : !up ? "off" : good ? "" : "behind");
      mode.className = "chip v " + (SIM ? "sim" : wait || !up ? "" : good ? "live" : "behind");   // offline: the red dot is the one signal, the text stays plain
      document.querySelectorAll(".tnav [data-livedot]").forEach(d => {
        if (SIM) { d.className = "dot none"; return; }
        d.className = "dot " + (wait ? "none" : !up ? "off" : good ? "" : "behind");
        const a = d.closest("a"); if (a) a.dataset.tnt = (wait ? "Checking the community node…" : !up ? (CHAIN.stale ? "Red: no answer from the relay for over a minute." : health === "down" ? `Red: the testnet is down (${hlabel || "health score"}).` : "Red: the community node is offline, the relay is not answering.") : degraded ? `Amber: ${hlabel || "the testnet health score is degraded"}.` : !synced ? "Amber: the community node is online but not synced with the real chain yet." : catching ? `Amber: the node is catching up, verified to #${fmt(st.canonical_height)} of ${fmt(st.tip_height)}.` : "Green: the community node is online and follows the real testnet chain.") + " Opens the HUD in Live mode.";
      });
      const n = CHAIN.online; onB.textContent = n == null ? "—" : String(n); onDot.className = "dot " + (n == null ? "none" : n > 0 ? "" : "off"); onChip.classList.toggle("live", n != null && n > 0);
      hB.textContent = st && Number(st.height) > 0 ? "#" + fmt(st.height) : "—";
      revB.textContent = CHAIN.rev == null ? "—" : "rev " + CHAIN.rev;
      feeB.textContent = CHAIN.fee == null ? "—" : CHAIN.fee + " AGRS";
      const c = CONS[CHAIN.elig], v = CHAIN.vals;
      cons.querySelector(".lg").textContent = c ? c[0] + (v != null ? ` · ${v} validator${v === 1 ? "" : "s"}` : "") : "—";
      cons.querySelector(".sh").textContent = c ? c[1] + (v != null ? ` · ${v}` : "") : "—";
      cons.dataset.tnt = consTip();
    };
    render();
    const govFrom = d => {
      CHAIN.rev = 1 + (d.archival_update_details || []).filter(u => u.lifecycle === "activated").length;
      const f = typeof d.consensus_rules === "string" && /o9\[t\][^=]*=\s*\{\s*#x([0-9a-fA-F]+)/.exec(d.consensus_rules); if (f) CHAIN.fee = parseInt(f[1], 16);
      CHAIN.elig = typeof d.eligibility_mode === "string" && d.eligibility_mode ? d.eligibility_mode
        : typeof d.consensus_rules === "string" && /o7\[t\][^=]*=\s*\{\s*1\s*\}/.test(d.consensus_rules) ? "validator_set" : CHAIN.elig;
      if (Array.isArray(d.active_validators)) CHAIN.vals = d.active_validators.length; else if (Number.isFinite(d.active_validator_count)) CHAIN.vals = d.active_validator_count;
      CHAIN.switches = (d.archival_update_details || []).filter(u => u && u.lifecycle === "activated" && u.host_contract_patch && typeof u.host_contract_patch.eligibility_mode === "string").length;
    };
    if (SIM) {   // the simulated chain: height, revision, fee and consensus from the generator, every second; the badge counts down to the day's programme
      let badgeText = "";
      /* each event of the programme in plain words: what happens, why it matters, where to watch it (the same words as the HUD's bar) */
      const EVENT = {
        stake: { what: "proof of stake takes over", why: "The chain changes how it picks who seals blocks: the six richest accounts take over from the fixed list.", watch: "Watch the proposer change in the Chain core." },
        fixed: { what: "the fixed validator list returns", why: "The chain goes back to a fixed validator list: a known set seals blocks again instead of the richest accounts.", watch: "Watch the validator ring in the Chain core." },
        admit: { what: "a new validator joins", why: "One more party seals blocks and votes on rule changes.", watch: "Watch a new diamond appear on the validator orbit." },
        remove: { what: "a validator leaves", why: "One party fewer seals blocks and votes on rule changes.", watch: "Watch a diamond vanish from the validator orbit." },
        super: { what: "two thirds must agree", why: "Changing the rules gets harder: two thirds of the validators must agree instead of more than half.", watch: "Watch the agreement arc need more votes." },
        major: { what: "more than half must agree", why: "Changing the rules gets easier: more than half of the validators is enough.", watch: "Watch the agreement arc fill sooner." },
        restart: { what: "the simulated chain starts over", why: "At midnight UTC the simulated chain starts again from block 0, as the real alpha testnet did more than once.", watch: "Watch the height reset." },
      };
      const localTime = new Date().getTimezoneOffset() !== 0, when = x => { const d = new Date(x * 1000), loc = d.toTimeString().slice(0, 5), utc = d.toISOString().slice(11, 16); return localTime ? `${loc} (${utc})` : utc; };   // no word in the time itself: the heading says which clock
      const badge = () => {
        const b = document.querySelector("header.trail .chip.unoff.sim"); if (!b || !TauSim.upcoming) return;
        const list = TauSim.upcoming(), u = list[0], left = u ? Math.ceil((u.at_ts - Date.now() / 1000) / 60) : 999;
        const ev = u && (EVENT[u.kind] || { what: u.short, why: u.title, watch: "" }), soon = !!u && left <= 60, bal = u && u.ballot;
        const text = !soon ? "Simulation · no real chain data"
          : left <= 0 ? `Simulation · now: ${ev.what}`
          : bal && bal.open ? `Simulation · vote now: ${ev.what} in ${left} min?`
          : bal && bal.outcome === "no" ? "Simulation · the visitors said no: the rules stay as they are"
          : u.status === "voting" ? `Simulation · validators are voting: ${ev.what} in ${left} min`
          : u.status === "agreed" ? `Simulation · agreed: ${ev.what} in ${left} min`
          : `Simulation · in ${left} min: ${ev.what}`;
        b.classList.toggle("soon", soon && left <= 5);
        if (text === badgeText) return; badgeText = text;
        b.textContent = text; b.dataset.short = soon ? `Simulation · ${left <= 0 ? "now" : `in ${left} min`}: ${u.short}` : text;   // the phone header has room for the short label only
        b.dataset.tnt = (soon ? `${ev.why} ${ev.watch}\n` : "") + (bal && bal.open ? "Vote yes or no on the HUD or in Proposals: the simulated validators follow the visitors’ majority.\n" : "") + "Every change is proposed 10 minutes ahead and put to the visitors until 7 minutes in: the simulated validators follow the majority, then it is in force, the path a real rule change takes on Tau.\n" + (localTime ? "Next in the simulation (your time, UTC in brackets):" : "Next in the simulation (UTC):") + "\n" + list.map(x => `${when(x.at_ts)} · ${(EVENT[x.kind] || {}).what || x.title}`).join("\n") + "\nSimulated: generated in your browser from the clock, the same on every page. Nothing here happened on the real testnet. Opens the full notice.";
      };
      const tick = () => { CHAIN.st = TauSim.status(); govFrom(TauSim.governance()); CHAIN.polled = true; CHAIN.at = Date.now(); render(); badge(); };
      tick(); setInterval(() => { if (!document.hidden) tick(); }, 1000);
    }
    const poll = async () => {
      if (SIM) return;
      const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), 8000);   // a stalled request must not freeze the light at its last colour
      try {
        const r = await fetch(`https://${RELAY}/status`, { cache: "no-store", signal: ctl.signal }); if (!r.ok) throw new Error(r.status);
        const j = await r.json(); CHAIN.st = j; CHAIN.stale = false; const n = Number(j.online ?? j.clients); if (Number.isFinite(n)) CHAIN.online = n;
      } catch (e) { CHAIN.st = null; CHAIN.online = null; CHAIN.err = e && e.message || String(e); }
      clearTimeout(t); CHAIN.polled = true; CHAIN.at = Date.now(); render();
    };
    poll(); setInterval(() => { if (!document.hidden) poll(); }, 20000);
    /* the "coming up" chip: agreed rule changes waiting for their activation block, with a countdown from the relay's block pace */
    const NEXT = { rows: [], chain: null, text: "" };
    /* the proposal titles and reasons are worded on the Proposals page; in Chinese its dictionary is borrowed so the chip reads the same here */
    const dict = new Promise(res => { if (!document.documentElement.classList.contains("i18n-zh") || /\/proposals\/?$/.test(location.pathname) || !window.TauI18n) return res(); const sc = document.createElement("script"); sc.src = ROOT + "assets/i18n/zh/proposals.js"; sc.onload = sc.onerror = res; document.head.append(sc); });
    const span = sec => { const m = Math.max(0, Math.round(sec / 60)); if (m < 60) return m <= 0 ? "now" : `in ${m} min`; const h = Math.floor(m / 60); if (h < 24) return `in ~${h} h ${m % 60} min`; return `in ~${Math.floor(h / 24)} d ${h % 24} h`; };
    const renderNext = () => {
      const nx = rail.querySelector("#tnNext"); if (!nx) return;
      const c = NEXT.chain, now = Date.now() / 1000;
      const rows = c ? NEXT.rows.map(p => ({ ...p, eta: Number(c.head_ts) + (Number(p.activate_at) - Number(c.head)) * Number(c.seconds_per_block || 8) })).filter(p => Number.isFinite(p.eta)).sort((a, b) => a.eta - b.eta) : [];
      const u = rows[0]; if (!u) { nx.hidden = true; NEXT.text = ""; return; }
      const left = u.eta - now, text = left <= 30 ? `Coming up · now: ${u.title}` : `Coming up · ${span(left)}: ${u.title}`;
      nx.hidden = false; nx.classList.toggle("soon", left <= 300);
      if (text === NEXT.text) return; NEXT.text = text;
      nx.querySelector("b").textContent = text;
      const when = x => new Date(x * 1000).toISOString().slice(0, 16).replace("T", " ");
      nx.dataset.tnt = (u.why ? u.why + "\n" : "") + `Agreed by the validators; takes effect at block #${fmt(u.activate_at)}, about ${when(u.eta)} UTC, that is ${span(left)}. The time is an estimate from the current block pace.\nNext activations on the live chain (UTC):\n` + rows.slice(0, 3).map(p => `#${fmt(p.activate_at)} · ${when(p.eta)} · ${p.title} · ${span(p.eta - now)}`).join("\n") + "\nWatch it in Proposals.";
    };
    const pollNext = async () => {
      const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), 8000);
      try {
        const r = await fetch(`https://${RELAY}/proposals.json`, { cache: "no-store", signal: ctl.signal }); if (!r.ok) throw new Error(r.status);
        const j = await r.json(); NEXT.chain = j.chain || null;
        NEXT.rows = (Array.isArray(j.proposals) ? j.proposals : []).filter(p => p && p.status === "agreed" && Number(p.activate_at) > 0).map(p => ({ title: String(p.title || "Rule change"), why: p.explain && p.explain.why ? String(p.explain.why) : "", activate_at: Number(p.activate_at) }));
      } catch (e) { /* keep the last answer; a missing file just leaves the chip as it was */ }
      clearTimeout(t); await dict; renderNext();
    };
    pollNext(); setInterval(() => { if (!document.hidden) pollNext(); }, 60000); setInterval(() => { if (!document.hidden) renderNext(); }, 15000);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) poll(); });
    /* watchdog: a visible tab that has heard nothing from the relay for over a minute shows red, whatever the last colour was */
    setInterval(() => { if (!SIM && !document.hidden && CHAIN.at && Date.now() - CHAIN.at > 70000 && !CHAIN.stale) { CHAIN.stale = true; CHAIN.st = null; render(); } }, 5000);
    let wait = 5000;
    const open = () => {
      let ws; try { ws = new WebSocket(`wss://${RELAY}`); } catch (e) { return; }
      ws.onopen = () => { wait = 5000; CHAIN.wsUp = true; const v = viewerId(); ws.send("hello version=1" + (v ? " viewer=" + v : "")); ws.send("presence"); ws.send("getgovernance"); };
      ws.onmessage = ev => {
        let m; try { m = JSON.parse(String(ev.data)); } catch (e) { return; }
        if (!m || m.status !== "ok") return;
        const d = m.data || {};
        if (m.command === "presence") { const n = Number(d.online ?? d.clients); if (Number.isFinite(n)) CHAIN.online = n; }
        if (m.command === "getgovernance" && !SIM) govFrom(d);   // in simulation the chain numbers come from the generator; this socket only counts people
        render();
      };
      ws.onclose = ws.onerror = () => { if (ws._dead) return; ws._dead = true; CHAIN.wsUp = false; render(); setTimeout(open, wait); wait = Math.min(60000, wait * 2); };
    };
    open();
  }

  /* subpages keep their own content column; the header rows span the full width like the HUD's (same 16px / 12px gutter).
     A page that scales its column to the screen (zoom or transform) keeps the header at the HUD's size instead. */
  function breakout(els) {
    let t = null;
    const fit = () => {
      const vw = document.documentElement.clientWidth, pad = vw <= 720 ? 12 : 16;
      els.forEach(e => {
        e.style.width = e.style.maxWidth = e.style.marginLeft = e.style.zoom = "";
        const r = e.getBoundingClientRect(), scale = e.offsetWidth ? r.width / e.offsetWidth : 1;
        if (scale > 1.02 || scale < 0.98) { e.style.zoom = String(1 / scale); return; }
        if (r.width >= vw - 2 * pad - 60) return;
        e.style.width = e.style.maxWidth = (vw - 2 * pad) + "px"; e.style.marginLeft = (pad - r.left) + "px";
      });
    };
    const later = () => { clearTimeout(t); t = setTimeout(fit, 60); };
    fit(); addEventListener("resize", later); addEventListener("load", later);
    new MutationObserver(later).observe(document.documentElement, { attributes: true, attributeFilter: ["class", "style"] });
  }

  /* ---------- row 2 controls on subpages: the HUD's source toggle, view switch and gear, with the same look ---------- */
  function subControls(tip) {
    const src = el("div", "seg tn-src"); src.setAttribute("role", "group"); src.setAttribute("aria-label", "Data source");
    const live = el("button", "", '<span class="dot none" data-livedot></span>Live node'); live.type = "button"; live.setAttribute("aria-pressed", String(!SIM)); tip(live, TIPS.live);
    const sim = el("button", "", "Simulation"); sim.type = "button"; sim.setAttribute("aria-pressed", String(SIM)); tip(sim, TIPS.sim);
    // the choice is remembered for every page (tau-mode, the HUD reads it too); this page reloads with the other source
    const go = m => { if (window.TauSim) TauSim.set(m); else { store.set("tau-mode", m); location.href = ROOT + "?mode=" + m; } };
    live.addEventListener("click", () => { if (SIM) go("live"); }); sim.addEventListener("click", () => { if (!SIM) go("sim"); });
    src.append(live, sim);
    const view = el("div", "seg"); view.setAttribute("role", "group"); view.setAttribute("aria-label", "Detail level");
    const bS = el("button", "", "Simple"), bT = el("button", "", "Technical"); bS.type = bT.type = "button"; tip(bS, TIPS.simple); tip(bT, TIPS.tech);
    const setView = v => { document.body.dataset.view = v; bS.setAttribute("aria-pressed", String(v === "simple")); bT.setAttribute("aria-pressed", String(v === "tech")); store.set(VIEW_KEY, v); };
    bS.addEventListener("click", () => setView("simple")); bT.addEventListener("click", () => setView("tech"));
    setView(store.get(VIEW_KEY) === "tech" ? "tech" : "simple");
    view.append(bS, bT);
    const gear = el("div", "gearbody", `<h4>Node</h4><div class="row"><code>wss://${RELAY}</code><span class="hint">Community relay in front of a Tau testnet node run for this site. To read your own node, open the HUD and put its address under the gear there.</span></div><h4>Look</h4><div class="row"></div>`);
    const row = gear.querySelector(".row:last-child");
    const tour = el("a", "pill", "Tour of this page"); tour.href = "#tour"; tour.addEventListener("click", e => { e.preventDefault(); closeAll(); startTour(false); });
    const hudTour = el("a", "pill", "HUD tour"); hudTour.href = ROOT + "?tour=1"; const about = el("a", "pill", "About"); about.href = ROOT + "#about"; const legal = el("a", "pill", "Privacy"); legal.href = ROOT + "legal/"; row.append(tour, hudTour, about, legal);
    return { src, view, gear };
  }

  /* guided tours: the HUD keeps its own; a subpage loads assets/tour.js (and its Chinese texts first) */
  function loadTour() {
    if (document.querySelector("script[data-tour]")) return;
    const files = (window.TauI18n && TauI18n.lang === "zh" ? ["i18n/zh/tour.js"] : []).concat("tour.js");
    files.forEach(f => { const s = el("script"); s.src = ROOT + "assets/" + f; s.async = false; s.dataset.tour = f; document.head.append(s); });
  }
  function startTour(isHud) {
    if (isHud) { document.dispatchEvent(new CustomEvent("tau-nav", { detail: "tour" })); return; }
    if (window.TauTour) TauTour.start(); else { loadTour(); setTimeout(() => window.TauTour && TauTour.start(), 600); }
  }

  let openEl = null;
  function closeAll() {
    document.querySelectorAll(".tnav .menu:not([hidden]), .tnav-pop:not([hidden])").forEach(m => { m.hidden = true; });
    document.querySelectorAll('.tnav [aria-expanded="true"]').forEach(b => b.setAttribute("aria-expanded", "false"));
    document.querySelectorAll(".tsheet:not([hidden]), .tsheet-bg:not([hidden])").forEach(s => { s.hidden = true; });
    openEl = null;
  }
  function toggle(btn, panel) {
    const open = panel.hidden;
    closeAll();
    if (open) { panel.hidden = false; btn.setAttribute("aria-expanded", "true"); openEl = panel; }
  }

  function mount(nav) {
    if (nav.dataset.mounted) return;
    nav.dataset.mounted = "1";
    const page = nav.dataset.page || "hud", isHud = page === "hud", here = SECTION_OF[page];
    if (!isHud && location.hash === "#updates") setTimeout(() => openUpdates(page), 50);   // the deep link lands in the overlay, not on the HUD
    const tip = (e, txt) => { if (!txt) return; if (isHud) e.dataset.full = txt; else e.dataset.tnt = txt; };
    const slots = {}; nav.querySelectorAll("[data-slot]").forEach(e => { slots[e.dataset.slot] = e; });
    // the Simple/Technical switch appears only where it changes something (`view: true` in P); the stored choice stays global
    if (!isHud) { const c = subControls(tip); slots.source = slots.source || c.src; slots.view = slots.view || (P[page] && P[page].view ? c.view : null); slots.gear = slots.gear || c.gear; mountRail(nav, page); if (!tipsOn) { tipsOn = true; hoverTips(); } }
    const left = el("div", "tnav-l"), right = el("div", "tnav-r"), bar = el("div", "tnav-nav");
    if (slots.source) { left.append(slots.source); left.append(el("span", "tnav-sep")); }
    SECTIONS.forEach(sec => {
      if (sec.single) {
        const a = el("a", "ni" + (here === sec.k ? " here" : ""), `<span class="lbl">${esc(sec.t)}</span>`); a.href = ROOT; if (here === sec.k) a.setAttribute("aria-current", "page"); tip(a, TIPS.hud); bar.append(a); return;
      }
      const w = el("div", "ni-wrap"), b = el("button", "ni" + (sec.util ? " util" : "") + (here === sec.k ? " here" : ""), `<span class="lbl">${esc(sec.t)}</span><span class="caret">▾</span>`);
      b.type = "button"; b.setAttribute("aria-haspopup", "true"); b.setAttribute("aria-expanded", "false"); if (sec.id) b.id = sec.id;
      const m = el("div", "menu"); m.hidden = true; m.setAttribute("role", "menu"); m.setAttribute("aria-label", sec.t);
      if (sec.k === "learn" && !isHud) { const t = el("a", "mi", `<span class="ic">?</span><b>Tour of this page</b><span>What each part of this page shows and why it matters, in a few short steps</span>`); t.href = "#tour"; t.setAttribute("role", "menuitem"); t.addEventListener("click", e => { e.preventDefault(); closeAll(); startTour(false); }); m.append(t); }
      sec.items.forEach(k => m.append(item(k, page, isHud)));
      b.addEventListener("click", () => toggle(b, m));
      w.append(b, m); bar.append(w);
    });
    left.append(bar);
    let state = slots.state;
    if (!state) { state = el("a", "pill primary", "Chain state"); state.href = ROOT + "#chain-state"; }
    state.classList.add("pill", "primary"); tip(state, TIPS.state);
    left.append(state);
    const tg = el("a", "pill tg", `${PLANE}<span>Telegram alerts</span>`); tg.href = TELEGRAM; tg.target = "_blank"; tg.rel = "noopener"; tg.setAttribute("aria-label", "Telegram channel tauHUDcom"); tip(tg, TIPS.telegram);
    /* feedback, impossible to miss: opens the feedback form in place, the HUD's own on the start page */
    const fbk = el("button", "pill fbk", `${BUBBLE}<span>Feedback</span>`); fbk.type = "button"; fbk.setAttribute("aria-label", "Give feedback"); tip(fbk, TIPS.feedback);
    fbk.addEventListener("click", () => { closeAll(); if (isHud && slots.updates) { slots.updates.click(); setTimeout(() => { const t = document.getElementById("fbText"); if (t) t.focus({ preventScroll: true }); }, 60); } else openUpdates(page, true); });
    right.append(fbk, tg);
    let upd = slots.updates;
    if (!upd) { upd = el("a", "", "Updates"); upd.href = "#updates"; upd.addEventListener("click", e => { e.preventDefault(); openUpdates(page); }); }   // opens in place; the HUD keeps its own overlay with the feedback box
    upd.classList.add("tl"); tip(upd, TIPS.updates);
    const updWrap = el("span", "tn-upd"); updWrap.append(upd);
    upd.addEventListener("click", markSeen);
    if (page !== "explorer" && page !== "account") {   // every page can look something up: block number, hash or address go to the Explorer
      const sf = el("form", "tn-search"); sf.action = ROOT + "explorer/"; sf.method = "get"; sf.setAttribute("role", "search");
      const si = el("input"); si.name = "q"; si.type = "search"; si.placeholder = "Search  ⌘K"; si.setAttribute("aria-label", "Search a block number, transaction hash or address"); si.autocomplete = "off"; si.spellcheck = false;
      tip(sf, "Block number, transaction hash or address: opens the Explorer with the result. Ctrl+K or ⌘K focuses this field.");
      sf.append(si); right.append(sf);
      document.addEventListener("keydown", e => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); si.focus(); si.select(); } });
      const css = el("style"); css.textContent = `.tnav .tn-search { display: flex; align-items: center; margin: 0; } .tnav .tn-search input { width: 150px; box-sizing: border-box; padding: 4px 8px; font: 12px var(--tn-mono); color: #fff; background: rgba(255,255,255,.04); border: 1px solid var(--tn-hair); border-radius: 999px; outline: none; } .tnav .tn-search input::placeholder { color: var(--tn-dim); } .tnav .tn-search input:focus { border-color: #fff; width: 220px; } .tnav .tn-search input::-webkit-search-cancel-button { display: none; } @media (max-width: 700px) { .tnav .tn-search { display: none; } }`; document.head.append(css);
    }
    /* every page has a short guided tour of its own (assets/tour.js); on the HUD this starts the HUD's tour */
    /* at most four or five utilities on the line (Feedback, Telegram, Search, Updates); the tour starts from Learn and, on the HUD, from its own buttons */
    right.append(updWrap);
    if (!isHud) loadTour();
    const I = window.TauI18n;
    right.append(el("span", "tnav-sep"));   // text links on the left of the line, the two switches on the right
    if (I) {   // language switch: a two-way pill like Simple/Technical, each language in its own script; the choice is remembered
      const lg = el("div", "seg tn-lang"); lg.setAttribute("role", "group"); lg.setAttribute("aria-label", "Language · 语言"); lg.setAttribute("translate", "no");
      [["en", "EN", "en", "Read this site in English · 切换到英文"], ["zh", "中文", "zh-CN", "阅读中文版 · Read this site in Chinese"]].forEach(([code, label, tag, t]) => {
        const lb = el("button", "", label); lb.type = "button"; lb.lang = tag; lb.setAttribute("aria-pressed", String(I.lang === code)); tip(lb, t);
        lb.addEventListener("click", () => { if (I.lang !== code) I.set(code); }); lg.append(lb);
      });
      right.append(lg);
    }
    if (slots.view) { tip(slots.view, "View: Simple says what each thing means; Technical adds keys, hashes, heights and stream names."); right.append(slots.view); }
    if (slots.gear) {
      const gw = el("div", "tnav-gearwrap"), gb = el("button", "tnav-gear", "⚙"), pop = el("div", "tnav-pop");
      gb.type = "button"; gb.setAttribute("aria-label", isHud ? "Settings: node address, background rain" : "Settings: node, guided tour, about"); gb.setAttribute("aria-haspopup", "true"); gb.setAttribute("aria-expanded", "false"); tip(gb, isHud ? TIPS.gear : TIPS.gearSub);
      pop.hidden = true; pop.append(slots.gear);
      gb.addEventListener("click", () => toggle(gb, pop));
      gw.append(gb, pop); right.append(gw);
    }
    nav.innerHTML = ""; nav.append(left, right);
    mountPhone(nav, page, isHud, here, upd);
    checkLog();
    if (!isHud) breakout([nav.previousElementSibling, nav].filter(e => e && (e.classList.contains("trail") || e === nav)));
  }

  function mountPhone(nav, page, isHud, here, upd) {
    const bar = el("nav", "tabbar"); bar.setAttribute("aria-label", "Pages");
    const sheets = [];
    SECTIONS.forEach(sec => {
      const on = here === sec.k ? " on" : "";
      if (sec.single) { const a = el("a", on.trim(), `<em>${sec.tab}</em>${esc(sec.t)}`); a.href = ROOT; bar.append(a); return; }
      const b = el("button", on.trim(), `<em>${sec.tab}</em>${esc(sec.short || sec.t)}`); b.type = "button"; b.setAttribute("aria-expanded", "false");
      const bg = el("div", "tsheet-bg"), sh = el("div", "tsheet"); bg.hidden = sh.hidden = true;
      sh.setAttribute("role", "dialog"); sh.setAttribute("aria-label", sec.t);
      sh.append(el("div", "grab"), el("h4", "", esc(sec.t)));
      sec.items.forEach(k => sh.append(item(k, page, isHud)));
      if (sec.k === "learn" && window.TauI18n) { const I = window.TauI18n, other = I.lang === "zh" ? "en" : "zh", l = el("a", "mi", `<span class="ic">文</span><b>${other === "zh" ? "中文" : "English"}</b><span>${other === "zh" ? "阅读中文版 · Read this site in Chinese" : "Read this site in English"}</span>`); l.href = "#"; l.setAttribute("translate", "no"); l.addEventListener("click", e => { e.preventDefault(); I.set(other); }); sh.append(l); }
      if (sec.k === "learn" && !isHud) { const t = el("a", "mi", `<span class="ic">?</span><b>Tour of this page</b><span>What each part of this page shows and why it matters, in a few short steps</span>`); t.href = "#tour"; t.addEventListener("click", e => { e.preventDefault(); closeAll(); startTour(false); }); sh.append(t); }
      if (sec.k === "learn") { const t = el("a", "mi", `<span class="ic">➤</span><b>Telegram alerts <span class="ext">↗</span></b><span>@tauHUDcom: every rule change and chain restart as it happens, a weekly recap, HUD updates</span>`); t.href = TELEGRAM; t.target = "_blank"; t.rel = "noopener"; sh.append(t); }
      bg.addEventListener("click", closeAll);
      b.addEventListener("click", () => { const open = sh.hidden; closeAll(); if (open) { bg.hidden = sh.hidden = false; b.setAttribute("aria-expanded", "true"); openEl = sh; } });
      bar.append(b); sheets.push(bg, sh);
    });
    const u = el(isHud ? "button" : "a", "tb-upd", "<em>•</em>Updates");
    if (isHud) { u.type = "button"; u.addEventListener("click", () => { markSeen(); closeAll(); upd.click(); }); } else { u.href = "#updates"; u.addEventListener("click", e => { e.preventDefault(); closeAll(); openUpdates(page); }); }
    bar.append(u);
    document.body.append(el("div", "tnav-spacer"), ...sheets, bar);
  }

  /* subpages: header chips and controls explain themselves on hover (tap on touch), in the same box as the HUD's */
  function hoverTips() {
    const css = el("style"); css.textContent = `header.trail .chip[data-tnt] { cursor: help; } header.trail a.chip[data-tnt] { cursor: pointer; } header.trail div.chip[data-tnt]:hover { border-color: rgba(255,255,255,.45); color: #d6d6dc; }
      header.trail .chip .sh { display: none; } @media (max-width: 1899px) { header.trail .chip .lg { display: none; } header.trail .chip .sh { display: inline; } }
      .tn-tip { position: fixed; z-index: 90; max-width: min(420px, 90vw); padding: 8px 11px; background: #151517; border: 1px solid rgba(255,255,255,.16); border-radius: 6px; font: 12px/1.5 "JetBrains Mono", ui-monospace, Menlo, monospace; color: #ececf0; white-space: pre-wrap; overflow-wrap: anywhere; box-shadow: 0 16px 40px -10px rgba(0,0,0,.9); pointer-events: none; letter-spacing: 0; text-transform: none; } .tn-tip[hidden] { display: none; }`; document.head.append(css);
    const box = el("div", "tn-tip"); box.hidden = true; box.setAttribute("role", "tooltip"); document.body.append(box);
    let cur = null, touch = matchMedia("(hover: none)").matches;
    const find = t => t instanceof Element ? t.closest("[data-tnt]") : null;
    const place = (x, y) => { const w = box.offsetWidth, h = box.offsetHeight; box.style.left = Math.max(8, Math.min(innerWidth - w - 8, x + 14)) + "px"; box.style.top = (y + 18 + h > innerHeight ? Math.max(8, y - h - 10) : y + 18) + "px"; };
    const show = (t, x, y) => { cur = t; box.textContent = t.dataset.tnt; box.hidden = false; place(x, y); };
    const hide = () => { cur = null; box.hidden = true; };
    document.addEventListener("pointerdown", e => { touch = e.pointerType === "touch"; }, true);
    document.addEventListener("mouseover", e => { if (touch) return; const t = find(e.target); if (t) show(t, e.clientX, e.clientY); else if (cur) hide(); });
    document.addEventListener("mousemove", e => { if (cur && !touch) place(e.clientX, e.clientY); });
    document.addEventListener("focusin", e => { const t = find(e.target); if (t) { const r = t.getBoundingClientRect(); show(t, r.left, r.bottom - 8); } else if (cur) hide(); });
    document.addEventListener("focusout", hide);
    document.addEventListener("scroll", hide, true);
    /* touch: a chip that is not a link shows its explanation on tap; a second tap or a tap elsewhere closes it */
    document.addEventListener("click", e => { if (!touch) return; const t = find(e.target); if (t && t !== cur && !t.closest("a, button")) show(t, e.clientX, e.clientY); else hide(); }, true);
  }
  let tipsOn = false;

  document.addEventListener("click", e => { if (openEl && !e.target.closest(".tnav .ni-wrap, .tnav-gearwrap, .tsheet, .tabbar")) closeAll(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && openEl) closeAll(); });
  /* cookie-free visitor numbers (infra/relay/visits.py): one ping when a page opens, one more after 30 s visible,
     one with the visible seconds when the page is hidden or left.
     Nothing is stored in the browser; ?nostats=1 leaves this browser out of the count (?nostats=0 undoes it). */
  function countVisit() {
    try {
      const q = new URLSearchParams(location.search);
      if (q.has("nostats")) { if (q.get("nostats") === "0") localStorage.removeItem("tauhud-nostats"); else localStorage.setItem("tauhud-nostats", "1"); }
      if (localStorage.getItem("tauhud-nostats") === "1") return;
    } catch (e) {}
    if (!/^(www\.)?tauhud\.com$|\.github\.io$/.test(location.hostname) || navigator.doNotTrack === "1" || navigator.globalPrivacyControl || navigator.webdriver) return;
    const pageOf = path => path.slice(ROOT.length).replace(/index\.html$/, "").replace(/\/+$/, "").toLowerCase() || "hud";
    const page = pageOf(location.pathname);
    let ref = "";
    try { const r = new URL(document.referrer); ref = r.host === location.host ? "/" + (r.pathname.startsWith(ROOT) ? pageOf(r.pathname) : "") : r.hostname; } catch (e) {}
    const q = new URLSearchParams(location.search), zh = /^zh/i.test(document.documentElement.lang) || q.get("lang") === "zh";
    const base = `https://${RELAY}/v?p=${encodeURIComponent(page)}`;
    const send = extra => { try { fetch(base + extra, { mode: "no-cors", keepalive: true, credentials: "omit", referrerPolicy: "no-referrer" }).catch(() => {}); } catch (e) {} };
    send(`&r=${encodeURIComponent(ref)}&s=${encodeURIComponent(q.get("utm_source") || q.get("ref") || "")}&l=${zh ? "zh" : "en"}&m=${SIM ? "sim" : "live"}`);
    // seconds the page was visible; sent once, when the page is first hidden or left (the relay keeps only a time step)
    let shown = 0, timed = false;
    setInterval(() => { if (document.visibilityState === "visible" && ++shown === 30) send("&e=1"); }, 1000);
    const leave = () => { if (!timed && shown > 0 && document.visibilityState !== "visible") { timed = true; send(`&t=${shown}`); } };
    document.addEventListener("visibilitychange", leave);
    addEventListener("pagehide", () => { if (!timed && shown > 0) { timed = true; send(`&t=${shown}`); } });
  }
  /* the About menu once more at the end of every page's footer line (Kilian, 29 Oct); a page without a footer has it in the header only */
  function mountFootLinks() {
    if (!document.querySelector("nav.tnav") || document.querySelector(".tn-foot")) return;
    const f = [...document.querySelectorAll("footer")].find(x => !x.closest("nav, .tn-modal"));
    const here = location.pathname.slice(ROOT.length).replace(/index\.html$/, "").replace(/\/+$/, "");
    if (!f) return;
    const links = [["About", "#about"], ["Status", "status"], ["Findings", "findings"], ["In numbers", "meta"], ["Developers", "developers"], ["Press", "press"], ["Privacy", "legal"]]
      .filter(([, h]) => h !== here && !f.querySelector(h[0] === "#" ? `a[href$="${h}"]` : `a[href$="${h}/"], a[href$="/${h}"]`));
    if (!links.length) return;
    const as = links.map(([t, h]) => { const a = el("a", "tn-foot", t); a.href = ROOT + (h[0] === "#" ? h : h + "/"); return a; });
    const host = f.querySelector("p:last-of-type") || f; as.forEach(a => host.append(" · ", a));
  }
  const init = () => { document.querySelectorAll("nav.tnav").forEach(mount); mountFootLinks(); countVisit(); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
  window.TauNav = { LATEST, version: () => SITE_VER || LATEST, TELEGRAM, markSeen, closeAll, chain: CHAIN, sim: SIM };
})();

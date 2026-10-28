/* Tau HUD shared header bar: the same row of sections and utilities on every page.
   A page puts <nav class="tnav" data-page="stats"></nav> under its brand row and loads this file.
   Host elements inside the nav with data-slot="source|state|updates|view|gear" are kept and placed;
   anything missing is generated as a link to the HUD. */
(() => {
  "use strict";
  const TELEGRAM = "https://t.me/tauHUDcom";
  const LATEST = "v17.31"; // fallback only: the green dot keys on the newest entry of assets/updates.json (tag|date), read below
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
    chronicle:  { t: "Chronicle", d: "Tau from the first videos in 2014 to the testnet alpha", i: "◷", h: "chronicle/" },
    findings:   { t: "Findings", d: "Issues we reported to IDNI, with their live GitHub status", i: "!", h: "findings/" },
    status:     { t: "Status", d: "Uptime, outages, sync gaps and restarts of the community node", i: "◍", h: "status/" },
    developers: { t: "Developers", d: "Widgets, badges and a free JSON API for your own site", i: "{}", h: "developers/" },
    press:      { t: "Press kit", d: "Video, logo, screenshots, facts and a ready paragraph, free to use", i: "↓", h: "press/" },
    tau:        { t: "What is Tau?", d: "tau.net, the project behind the testnet", i: "τ", h: "https://tau.net", ext: true },
    about:      { t: "About", d: "Who built this page, sources, how to support it", i: "i", h: "#about", act: "about" },
    playground: { t: "Playground", d: "Write a transfer rule and run the testnet's own checks on it", i: "◇", h: "playground/" },
    seat:       { t: "Validator seat", d: "Take a simulated seat and vote a rule change into law", i: "✓", h: "playground/#seat" },
  };
  const SECTIONS = [
    { k: "hud", t: "HUD", single: true, tab: "◉" },
    { k: "explore", t: "Explore", items: ["explorer", "stats", "history", "account", "nodes", "proposals"], tab: "≋" },
    { k: "learn", t: "Learn", items: ["story", "tour", "chronicle", "findings", "status", "developers", "press", "tau", "about"], tab: "▸" },
    { k: "play", t: "Playground", items: ["playground", "seat"], id: "btnPlayground", tab: "◇", short: "Play" },
  ];
  const SECTION_OF = { hud: "hud", explorer: "explore", stats: "explore", nodes: "explore", history: "explore", account: "explore", proposals: "explore", story: "learn", chronicle: "learn", findings: "learn", status: "learn", developers: "learn", press: "learn", playground: "play" };
  const TIPS = {
    state: "Every rule in force right now: spec revision, fee, agreement threshold, validators, agreed changes, personal rules.",
    telegram: "Join @tauHUDcom on Telegram: every new proposal, agreement, activation and chain restart the moment it happens, a weekly recap picture, every HUD update. Questions (height, proposals, your transaction or address): write to @tauhud_alerts_bot. Opens Telegram.",
    updates: "What changed on this page and when, built from your feedback. Also where to leave feedback.",
    gear: "Settings: node address and Connect, background rain.",
    gearSub: "Settings: which node this page reads, guided tour, about.",
    live: "This page reads the real testnet through the community relay. Opens the HUD in Live mode.",
    sim: "Simulation: invented activity that follows the documented protocol, generated in your browser. It runs only in the HUD, so this opens the HUD; this page always shows the live chain.",
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
    play: "Write your own transfer rule and run the testnet’s own checks on it, or take a simulated validator seat and vote a rule change into law.",
  };
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const PLANE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21.9 3.3 2.6 10.8c-1 .4-1 1 0 1.3l4.9 1.5 11.4-7.2c.5-.3 1-.1.6.2l-9.2 8.3-.4 5.1c.5 0 .7-.2 1-.5l2.4-2.3 5 3.7c.9.5 1.6.2 1.8-.9l3.3-15.5c.3-1.3-.5-1.9-1.5-1.5z"/></svg>';
  const emit = action => document.dispatchEvent(new CustomEvent("tau-nav", { detail: action }));
  const markSeen = () => { store.set(SEEN_KEY, LATEST_ID); document.querySelectorAll(".tn-upd.new, .tabbar .new").forEach(e => e.classList.remove("new")); };
  /* the shared update log: newest entry = highest date, then the later line in the file; the dot shows until that entry was seen */
  const checkLog = () => fetch(ROOT + "assets/updates.json", { cache: "no-cache" }).then(r => r.json()).then(list => {
    if (!Array.isArray(list) || !list.length) return;
    const top = list.map((e, i) => ({ ...e, i })).sort((x, y) => String(y.on || "").localeCompare(String(x.on || "")) || y.i - x.i)[0];
    LATEST_ID = `${top.tag}|${top.on}`;
    const fresh = store.get(SEEN_KEY) !== LATEST_ID;
    document.querySelectorAll(".tn-upd, .tabbar .tb-upd").forEach(e => e.classList.toggle("new", fresh));
  }).catch(() => { const fresh = store.get(SEEN_KEY) !== LATEST; document.querySelectorAll(".tn-upd, .tabbar .tb-upd").forEach(e => e.classList.toggle("new", fresh)); });

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
    const unoff = el("a", "chip unoff", "Unofficial community project · not affiliated with IDNI"); unoff.href = ROOT + "#about"; unoff.dataset.tnt = TIPS.unoff;
    const chips = el("div", "chips");
    const chip = (tag, id, cls, html, t) => { const c = el(tag, "chip" + (cls ? " " + cls : ""), html); c.id = id; c.dataset.tnt = t; return c; };
    chips.append(
      chip("div", "tnMode", "v", '<span class="dot none"></span><b>Live · Connecting</b>', TIPS.mode),
      chip("div", "tnOnline", "", '<span class="dot none"></span><b class="n">—</b>online', TIPS.online),
      chip("a", "tnCons", "v", '<b><span class="lg">—</span><span class="sh">—</span></b>', TIPS.cons),
      chip("div", "tnNet", "v", `<b>${NET}</b>`, TIPS.net),
      chip("div", "tnHeight", "v", "<b>—</b>", TIPS.height),
      chip("a", "tnRev", "v", "<b>—</b>", TIPS.rev),
      chip("div", "tnFee", "v", "<b>—</b>", TIPS.fee));
    chips.querySelectorAll(".chip.v > b").forEach(b => { b.style.marginLeft = "0"; });   // value-only chips: the name lives in the hover text
    chips.querySelector("#tnRev").href = chips.querySelector("#tnCons").href = ROOT + "#chain-state";
    if (own) chips.append(own);
    rail.append(brand, unoff, chips);
    if (old) old.replaceWith(rail); else nav.before(rail);
    feedChips(rail);
    return rail;
  }
  function viewerId() {
    try {
      let v = localStorage.getItem(VIEWER_KEY);
      if (!/^[0-9a-f]{32}$/.test(v || "")) { v = Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, "0")).join(""); localStorage.setItem(VIEWER_KEY, v); }
      return v;
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
      modeB.textContent = wait ? "Live · Connecting" : !up ? "Live · Offline" : degraded ? "Live · Degraded" : !synced ? "Live · Not synced" : catching ? `Verified to #${fmt(st.canonical_height)} of ${fmt(st.tip_height)}` : "Live · Connected";
      modeDot.className = "dot " + (wait ? "none" : !up ? "off" : good ? "" : "behind");
      mode.className = "chip v " + (wait || !up ? "" : good ? "live" : "behind");   // offline: the red dot is the one signal, the text stays plain
      document.querySelectorAll(".tnav [data-livedot]").forEach(d => {
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
    const poll = async () => {
      const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), 8000);   // a stalled request must not freeze the light at its last colour
      try {
        const r = await fetch(`https://${RELAY}/status`, { cache: "no-store", signal: ctl.signal }); if (!r.ok) throw new Error(r.status);
        const j = await r.json(); CHAIN.st = j; CHAIN.stale = false; const n = Number(j.online ?? j.clients); if (Number.isFinite(n)) CHAIN.online = n;
      } catch (e) { CHAIN.st = null; CHAIN.online = null; CHAIN.err = e && e.message || String(e); }
      clearTimeout(t); CHAIN.polled = true; CHAIN.at = Date.now(); render();
    };
    poll(); setInterval(() => { if (!document.hidden) poll(); }, 20000);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) poll(); });
    /* watchdog: a visible tab that has heard nothing from the relay for over a minute shows red, whatever the last colour was */
    setInterval(() => { if (!document.hidden && CHAIN.at && Date.now() - CHAIN.at > 70000 && !CHAIN.stale) { CHAIN.stale = true; CHAIN.st = null; render(); } }, 5000);
    let wait = 5000;
    const open = () => {
      let ws; try { ws = new WebSocket(`wss://${RELAY}`); } catch (e) { return; }
      ws.onopen = () => { wait = 5000; CHAIN.wsUp = true; const v = viewerId(); ws.send("hello version=1" + (v ? " viewer=" + v : "")); ws.send("presence"); ws.send("getgovernance"); };
      ws.onmessage = ev => {
        let m; try { m = JSON.parse(String(ev.data)); } catch (e) { return; }
        if (!m || m.status !== "ok") return;
        const d = m.data || {};
        if (m.command === "presence") { const n = Number(d.online ?? d.clients); if (Number.isFinite(n)) CHAIN.online = n; }
        if (m.command === "getgovernance") {
          CHAIN.rev = 1 + (d.archival_update_details || []).filter(u => u.lifecycle === "activated").length;
          const f = typeof d.consensus_rules === "string" && /o9\[t\][^=]*=\s*\{\s*#x([0-9a-fA-F]+)/.exec(d.consensus_rules); if (f) CHAIN.fee = parseInt(f[1], 16);
          CHAIN.elig = typeof d.eligibility_mode === "string" && d.eligibility_mode ? d.eligibility_mode
            : typeof d.consensus_rules === "string" && /o7\[t\][^=]*=\s*\{\s*1\s*\}/.test(d.consensus_rules) ? "validator_set" : CHAIN.elig;
          if (Array.isArray(d.active_validators)) CHAIN.vals = d.active_validators.length; else if (Number.isFinite(d.active_validator_count)) CHAIN.vals = d.active_validator_count;
          CHAIN.switches = (d.archival_update_details || []).filter(u => u && u.lifecycle === "activated" && u.host_contract_patch && typeof u.host_contract_patch.eligibility_mode === "string").length;
        }
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
    const src = el("div", "seg"); src.setAttribute("role", "group"); src.setAttribute("aria-label", "Data source");
    const live = el("a", "", '<span class="dot none" data-livedot></span>Live node'); live.href = ROOT + "?mode=live"; live.setAttribute("aria-pressed", "true"); tip(live, TIPS.live);
    const sim = el("a", "", "Simulation ↗"); sim.href = ROOT + "?mode=sim";  // leaves this page: simulation only runs in the HUD
    sim.setAttribute("aria-pressed", "false"); tip(sim, TIPS.sim);
    src.append(live, sim);
    const view = el("div", "seg"); view.setAttribute("role", "group"); view.setAttribute("aria-label", "Detail level");
    const bS = el("button", "", "Simple"), bT = el("button", "", "Technical"); bS.type = bT.type = "button"; tip(bS, TIPS.simple); tip(bT, TIPS.tech);
    const setView = v => { document.body.dataset.view = v; bS.setAttribute("aria-pressed", String(v === "simple")); bT.setAttribute("aria-pressed", String(v === "tech")); store.set(VIEW_KEY, v); };
    bS.addEventListener("click", () => setView("simple")); bT.addEventListener("click", () => setView("tech"));
    setView(store.get(VIEW_KEY) === "tech" ? "tech" : "simple");
    view.append(bS, bT);
    const gear = el("div", "gearbody", `<h4>Node</h4><div class="row"><code>wss://${RELAY}</code><span class="hint">Community relay in front of a Tau testnet node run for this site. To read your own node, open the HUD and put its address under the gear there.</span></div><h4>Look</h4><div class="row"></div>`);
    const row = gear.querySelector(".row:last-child");
    const tour = el("a", "pill", "Guided tour"); tour.href = ROOT + "?tour=1"; const about = el("a", "pill", "About"); about.href = ROOT + "#about"; row.append(tour, about);
    return { src, view, gear };
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
      const w = el("div", "ni-wrap"), b = el("button", "ni" + (here === sec.k ? " here" : ""), `<span class="lbl">${esc(sec.t)}</span><span class="caret">▾</span>`);
      b.type = "button"; b.setAttribute("aria-haspopup", "true"); b.setAttribute("aria-expanded", "false"); if (sec.id) b.id = sec.id;
      const m = el("div", "menu"); m.hidden = true; m.setAttribute("role", "menu"); m.setAttribute("aria-label", sec.t);
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
    right.append(tg);
    let upd = slots.updates;
    if (!upd) { upd = el("a", "", "Updates"); upd.href = ROOT + "#updates"; }
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
    right.append(updWrap);
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
      if (sec.k === "learn") { const t = el("a", "mi", `<span class="ic">➤</span><b>Telegram alerts <span class="ext">↗</span></b><span>@tauHUDcom: every rule change and chain restart as it happens, a weekly recap, HUD updates</span>`); t.href = TELEGRAM; t.target = "_blank"; t.rel = "noopener"; sh.append(t); }
      bg.addEventListener("click", closeAll);
      b.addEventListener("click", () => { const open = sh.hidden; closeAll(); if (open) { bg.hidden = sh.hidden = false; b.setAttribute("aria-expanded", "true"); openEl = sh; } });
      bar.append(b); sheets.push(bg, sh);
    });
    const u = el(isHud ? "button" : "a", "tb-upd", "<em>•</em>Updates");
    if (isHud) { u.type = "button"; u.addEventListener("click", () => { markSeen(); closeAll(); upd.click(); }); } else { u.href = ROOT + "#updates"; u.addEventListener("click", markSeen); }
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
  const init = () => document.querySelectorAll("nav.tnav").forEach(mount);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
  window.TauNav = { LATEST, TELEGRAM, markSeen, closeAll, chain: CHAIN };
})();

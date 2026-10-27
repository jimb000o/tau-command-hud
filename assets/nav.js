/* Tau HUD shared header bar: the same row of sections and utilities on every page.
   A page puts <nav class="tnav" data-page="stats"></nav> under its brand row and loads this file.
   Host elements inside the nav with data-slot="source|state|updates|view|gear" are kept and placed;
   anything missing is generated as a link to the HUD. */
(() => {
  "use strict";
  const TELEGRAM = "https://t.me/tauHUDcom";
  const LATEST = "v17.12"; // newest entry of the HUD update log; bump with every release so the green dot appears once
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
    tau:        { t: "What is Tau?", d: "tau.net, the project behind the testnet", i: "τ", h: "https://tau.net", ext: true },
    about:      { t: "About", d: "Who built this page, sources, how to support it", i: "i", h: "#about", act: "about" },
    playground: { t: "Playground", d: "Write a transfer rule and run the testnet's own checks on it", i: "◇", h: "playground/" },
    seat:       { t: "Validator seat", d: "Take a simulated seat and vote a rule change into law", i: "✓", h: "playground/#seat" },
  };
  const SECTIONS = [
    { k: "hud", t: "HUD", single: true, tab: "◉" },
    { k: "explore", t: "Explore", items: ["explorer", "stats", "history", "account", "nodes", "proposals"], tab: "≋" },
    { k: "learn", t: "Learn", items: ["story", "tour", "chronicle", "findings", "status", "tau", "about"], tab: "▸" },
    { k: "play", t: "Playground", items: ["playground", "seat"], id: "btnPlayground", tab: "◇", short: "Play" },
  ];
  const SECTION_OF = { hud: "hud", explorer: "explore", stats: "explore", nodes: "explore", history: "explore", account: "explore", proposals: "explore", story: "learn", chronicle: "learn", findings: "learn", status: "learn", playground: "play" };
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
    hud: "The chain core live: blocks, rules and agreement as they happen.",
    explore: "Chain data pages: Explorer, Stats, Time travel, Accounts, Nodes, Proposals.",
    learn: "Tau in 60 seconds, Guided tour, Chronicle, Findings, Status, What is Tau?, About.",
    play: "Write your own transfer rule and run the testnet’s own checks on it, or take a simulated validator seat and vote a rule change into law.",
  };
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const PLANE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21.9 3.3 2.6 10.8c-1 .4-1 1 0 1.3l4.9 1.5 11.4-7.2c.5-.3 1-.1.6.2l-9.2 8.3-.4 5.1c.5 0 .7-.2 1-.5l2.4-2.3 5 3.7c.9.5 1.6.2 1.8-.9l3.3-15.5c.3-1.3-.5-1.9-1.5-1.5z"/></svg>';
  const emit = action => document.dispatchEvent(new CustomEvent("tau-nav", { detail: action }));
  const markSeen = () => { store.set(SEEN_KEY, LATEST); document.querySelectorAll(".upd.new, .tabbar .new").forEach(e => e.classList.remove("new")); };

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
    const brand = el("a", "brand", `${MARK}<span class="bn">Tau HUD</span><h1 class="bt">${esc(title)}</h1>`);  // the page title is the heading, the logo is not brand.href = ROOT; brand.title = "Back to the HUD";
    const unoff = el("a", "chip unoff", "Unofficial community project · not affiliated with IDNI"); unoff.href = ROOT + "#about"; unoff.title = TIPS.unoff;
    const chips = el("div", "chips");
    const chip = (tag, id, cls, html, t) => { const c = el(tag, "chip" + (cls ? " " + cls : ""), html); c.id = id; c.title = t; return c; };
    chips.append(
      chip("div", "tnMode", "warn", '<span class="dot none"></span>Mode<b>Live · Connecting</b>', TIPS.mode),
      chip("div", "tnOnline", "", '<span class="dot none"></span><b class="n">—</b>online', TIPS.online),
      chip("div", "tnNet", "", `Network<b>${NET}</b>`, TIPS.net),
      chip("div", "tnHeight", "", "Height<b>—</b>", TIPS.height),
      chip("a", "tnRev", "", "Spec revision<b>—</b>", TIPS.rev),
      chip("div", "tnFee", "", "Base fee<b>—</b>", TIPS.fee));
    chips.querySelector("#tnRev").href = ROOT + "#chain-state";
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
  const CHAIN = { st: null, polled: false, wsUp: false, online: null, rev: null, fee: null };
  function feedChips(rail) {
    const q = s => rail.querySelector(s);
    const mode = q("#tnMode"), modeB = mode.querySelector("b"), modeDot = mode.querySelector(".dot");
    const onChip = q("#tnOnline"), onB = onChip.querySelector("b"), onDot = onChip.querySelector(".dot");
    const hB = q("#tnHeight b"), revB = q("#tnRev b"), feeB = q("#tnFee b");
    const render = () => {
      const st = CHAIN.st, up = !!(st && st.upstream_connected && Number(st.height) > 0);
      const synced = up && st.live_default === true;
      const catching = synced && Number(st.tip_height) > 0 && st.canonical_height != null && Number(st.canonical_height) < Number(st.tip_height) - 2;
      const wait = !CHAIN.polled;
      modeB.textContent = wait ? "Live · Connecting" : !up ? "Live · Offline" : !synced ? "Live · Not synced" : catching ? `Verified to #${fmt(st.canonical_height)} of ${fmt(st.tip_height)}` : "Live · Connected";
      modeDot.className = "dot " + (wait ? "none" : !up ? "off" : synced && !catching ? "" : "behind");
      mode.className = "chip " + (wait ? "warn" : !up ? "warn" : synced && !catching ? "live" : "behind");
      document.querySelectorAll(".tnav [data-livedot]").forEach(d => {
        d.className = "dot " + (wait ? "none" : !up ? "off" : synced && !catching ? "" : "behind");
        const a = d.closest("a"); if (a) a.title = (wait ? "Checking the community node…" : !up ? "Red: the community node is offline, the relay is not answering." : !synced ? "Amber: the community node is online but not synced with the real chain yet." : catching ? `Amber: the node is catching up, verified to #${fmt(st.canonical_height)} of ${fmt(st.tip_height)}.` : "Green: the community node is online and follows the real testnet chain.") + " Opens the HUD in Live mode.";
      });
      const n = CHAIN.online; onB.textContent = n == null ? "—" : String(n); onDot.className = "dot " + (n == null ? "none" : n > 0 ? "" : "off"); onChip.classList.toggle("live", n != null && n > 0);
      hB.textContent = st && Number(st.height) > 0 ? fmt(st.height) : "—";
      revB.textContent = CHAIN.rev == null ? "—" : String(CHAIN.rev);
      feeB.textContent = CHAIN.fee == null ? "—" : String(CHAIN.fee);
    };
    render();
    const poll = async () => {
      try {
        const r = await fetch(`https://${RELAY}/status`, { cache: "no-store" }); if (!r.ok) throw new Error(r.status);
        const j = await r.json(); CHAIN.st = j; const n = Number(j.online ?? j.clients); if (Number.isFinite(n)) CHAIN.online = n;
      } catch (e) { CHAIN.st = null; CHAIN.online = null; }
      CHAIN.polled = true; render();
    };
    poll(); setInterval(() => { if (!document.hidden) poll(); }, 20000);
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
    const sim = el("a", "", "Simulation ↗"); sim.href = ROOT + "?mode=sim";  // leaves this page: simulation only runs in the HUD sim.setAttribute("aria-pressed", "false"); tip(sim, TIPS.sim);
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
    const tip = (e, txt) => { if (!txt) return; if (isHud) e.dataset.full = txt; else e.title = txt; };
    const slots = {}; nav.querySelectorAll("[data-slot]").forEach(e => { slots[e.dataset.slot] = e; });
    // the Simple/Technical switch appears only where it changes something (`view: true` in P); the stored choice stays global
    if (!isHud) { const c = subControls(tip); slots.source = slots.source || c.src; slots.view = slots.view || (P[page] && P[page].view ? c.view : null); slots.gear = slots.gear || c.gear; mountRail(nav, page); }
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
    const updWrap = el("span", "upd" + (store.get(SEEN_KEY) !== LATEST ? " new" : "")); updWrap.append(upd);
    upd.addEventListener("click", markSeen);
    right.append(updWrap);
    if (slots.view) { const lab = el("span", "vlab", "View"); right.append(lab, slots.view); }
    if (slots.gear) {
      const gw = el("div", "tnav-gearwrap"), gb = el("button", "tnav-gear", "⚙"), pop = el("div", "tnav-pop");
      gb.type = "button"; gb.setAttribute("aria-label", isHud ? "Settings: node address, background rain" : "Settings: node, guided tour, about"); gb.setAttribute("aria-haspopup", "true"); gb.setAttribute("aria-expanded", "false"); tip(gb, isHud ? TIPS.gear : TIPS.gearSub);
      pop.hidden = true; pop.append(slots.gear);
      gb.addEventListener("click", () => toggle(gb, pop));
      gw.append(gb, pop); right.append(gw);
    }
    nav.innerHTML = ""; nav.append(left, right);
    mountPhone(nav, page, isHud, here, upd);
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
      if (sec.k === "learn") { const t = el("a", "mi", `<span class="ic">➤</span><b>Telegram alerts <span class="ext">↗</span></b><span>@tauHUDcom: every rule change and chain restart as it happens, a weekly recap, HUD updates</span>`); t.href = TELEGRAM; t.target = "_blank"; t.rel = "noopener"; sh.append(t); }
      bg.addEventListener("click", closeAll);
      b.addEventListener("click", () => { const open = sh.hidden; closeAll(); if (open) { bg.hidden = sh.hidden = false; b.setAttribute("aria-expanded", "true"); openEl = sh; } });
      bar.append(b); sheets.push(bg, sh);
    });
    const u = el(isHud ? "button" : "a", store.get(SEEN_KEY) !== LATEST ? "new" : "", "<em>•</em>Updates");
    if (isHud) { u.type = "button"; u.addEventListener("click", () => { markSeen(); closeAll(); upd.click(); }); } else { u.href = ROOT + "#updates"; u.addEventListener("click", markSeen); }
    bar.append(u);
    document.body.append(el("div", "tnav-spacer"), ...sheets, bar);
  }

  document.addEventListener("click", e => { if (openEl && !e.target.closest(".tnav .ni-wrap, .tnav-gearwrap, .tsheet, .tabbar")) closeAll(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && openEl) closeAll(); });
  const init = () => document.querySelectorAll("nav.tnav").forEach(mount);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
  window.TauNav = { LATEST, TELEGRAM, markSeen, closeAll, chain: CHAIN };
})();

/* Tau HUD shared header bar: the same row of sections and utilities on every page.
   A page puts <nav class="tnav" data-page="stats"></nav> under its brand row and loads this file.
   Host elements inside the nav with data-slot="source|state|updates|view|gear" are kept and placed;
   anything missing is generated as a link to the HUD. */
(() => {
  "use strict";
  const TELEGRAM = "https://t.me/tauHUDcom";
  const LATEST = "v17.0"; // newest entry of the HUD update log; bump with every release so the green dot appears once
  const SEEN_KEY = "tauhud-updates-seen";
  const src = document.currentScript && document.currentScript.src;
  const ROOT = src ? new URL("..", src).pathname : "/";
  const P = {
    hud:        { t: "HUD", d: "The chain core live: blocks, rules and agreement as they happen", i: "◉", h: "" },
    explorer:   { t: "Explorer", d: "Find any block, transaction or address", i: "⌕", h: "explorer/" },
    stats:      { t: "Stats", d: "Block pace, transactions, validators and rule changes over the whole chain", i: "≋", h: "stats/" },
    history:    { t: "Time travel", d: "Step through the chain block by block and see the rules at any height", i: "⟲", h: "history/" },
    account:    { t: "Accounts", d: "Balance, own rules, offers and refusals of any address", i: "@", h: "account/" },
    nodes:      { t: "Nodes", d: "Community nodes that follow the chain, with badges for uptime and sync", i: "◎", h: "nodes/" },
    proposals:  { t: "Proposals", d: "Every rule change from proposal to law, with Telegram and RSS alerts", i: "§", h: "proposals/" },
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
    { k: "learn", t: "Learn", items: ["tour", "chronicle", "findings", "status", "tau", "about"], tab: "▸" },
    { k: "play", t: "Playground", items: ["playground", "seat"], id: "btnPlayground", tab: "◇", short: "Play" },
  ];
  const SECTION_OF = { hud: "hud", explorer: "explore", stats: "explore", nodes: "explore", history: "explore", account: "explore", proposals: "explore", chronicle: "learn", findings: "learn", status: "learn", playground: "play" };
  const TIPS = {
    state: "Every rule in force right now: spec revision, fee, agreement threshold, validators, agreed changes, personal rules.",
    telegram: "Telegram channel @tauHUDcom: every new proposal, agreement and activation on the testnet, plus HUD updates. Opens Telegram.",
    updates: "What changed on this page and when, built from your feedback. Also where to leave feedback.",
    gear: "Settings: node address and Connect, background rain.",
    hud: "The chain core live: blocks, rules and agreement as they happen.",
    explore: "Chain data pages: Explorer, Stats, Time travel, Accounts, Nodes, Proposals.",
    learn: "Guided tour, Chronicle, Findings, Status, What is Tau?, About.",
    play: "Write your own transfer rule and run the testnet’s own checks on it, or take a simulated validator seat and vote a rule change into law.",
  };
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const PLANE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21.9 3.3 2.6 10.8c-1 .4-1 1 0 1.3l4.9 1.5 11.4-7.2c.5-.3 1-.1.6.2l-9.2 8.3-.4 5.1c.5 0 .7-.2 1-.5l2.4-2.3 5 3.7c.9.5 1.6.2 1.8-.9l3.3-15.5c.3-1.3-.5-1.9-1.5-1.5z"/></svg>';
  const emit = action => document.dispatchEvent(new CustomEvent("tau-nav", { detail: action }));
  const markSeen = () => { store.set(SEEN_KEY, LATEST); document.querySelectorAll(".upd.new, .tabbar .new").forEach(e => e.classList.remove("new")); };

  function item(k, page, isHud, tip) {
    const p = P[k], a = el("a", "mi" + (k === page ? " here" : ""));
    a.setAttribute("role", "menuitem");
    a.innerHTML = `<span class="ic">${p.i}</span><b>${esc(p.t)}${p.ext ? ' <span class="ext">↗</span>' : ""}</b><span>${esc(p.d)}</span>`;
    if (p.ext) { a.href = p.h; a.target = "_blank"; a.rel = "noopener"; }
    else if (p.act && isHud) { a.href = "#"; a.addEventListener("click", e => { e.preventDefault(); closeAll(); emit(p.act); }); }
    else a.href = ROOT + p.h;
    if (k === page) a.setAttribute("aria-current", "page");
    return a;
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
    const left = el("div", "tnav-l"), right = el("div", "tnav-r"), bar = el("div", "tnav-nav");
    if (slots.source) { left.append(slots.source); left.append(el("span", "tnav-sep")); }
    SECTIONS.forEach(sec => {
      if (sec.single) {
        const a = el("a", "ni" + (here === sec.k ? " here" : ""), esc(sec.t)); a.href = ROOT; if (here === sec.k) a.setAttribute("aria-current", "page"); tip(a, TIPS.hud); bar.append(a); return;
      }
      const w = el("div", "ni-wrap"), b = el("button", "ni" + (here === sec.k ? " here" : ""), `${esc(sec.t)}<span class="caret">▾</span>`);
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
    const tg = el("a", "pill tg", `${PLANE}<span>Telegram</span>`); tg.href = TELEGRAM; tg.target = "_blank"; tg.rel = "noopener"; tg.setAttribute("aria-label", "Telegram channel tauHUDcom"); tip(tg, TIPS.telegram);
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
      gb.type = "button"; gb.setAttribute("aria-label", "Settings: node address, background rain"); gb.setAttribute("aria-haspopup", "true"); gb.setAttribute("aria-expanded", "false"); tip(gb, TIPS.gear);
      pop.hidden = true; pop.append(slots.gear);
      gb.addEventListener("click", () => toggle(gb, pop));
      gw.append(gb, pop); right.append(gw);
    }
    nav.innerHTML = ""; nav.append(left, right);
    mountPhone(nav, page, isHud, here, upd);
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
      if (sec.k === "learn") { const t = el("a", "mi", `<span class="ic">➤</span><b>Telegram <span class="ext">↗</span></b><span>Channel @tauHUDcom: proposals, agreements, activations and HUD updates</span>`); t.href = TELEGRAM; t.target = "_blank"; t.rel = "noopener"; sh.append(t); }
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
  window.TauNav = { LATEST, TELEGRAM, markSeen, closeAll };
})();

/* The HUD's news line under the four principles: live facts read off this page, the newest entries of the Updates log,
   hand-picked posts of ours and a few useful pointers, mixed so most of what scrolls by helps the visitor.
   Hand-picked content lives in assets/ticker.json (picks: our X posts worth reposting; notes: pointers on the site;
   invites: Telegram and X). Each item decodes out of falling glyphs where it enters the line, then reads as plain text.
   Hover or focus pauses it; with reduced motion the items change in place instead of moving. */
(() => {
  "use strict";
  const box = document.getElementById("tick"); if (!box) return;
  const view = box.querySelector(".tk-view"), track = box.querySelector(".tk-track");
  const I18N = window.TauI18n, lang = I18N ? I18N.lang : "en";
  const tr = s => { try { return I18N ? I18N.t(s) : s; } catch (e) { return s; } };
  const translated = s => lang === "en" || tr(s) !== s;   // in Chinese or Japanese an item without its translation is left out
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const GLYPHS = "ｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾂﾃﾅﾆﾇﾈﾊﾋﾎﾏﾐﾑﾒﾓﾔﾕﾗﾘﾜ012345789Z:.=*+<>¦";
  const glyph = () => GLYPHS[Math.random() * GLYPHS.length | 0];
  const ICON = {
    x: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17.8 3h3.1l-6.8 7.7L22 21h-6.2l-4.9-6.4L5.3 21H2.2l7.2-8.3L2 3h6.4l4.4 5.8L17.8 3zm-1.1 16.2h1.7L7.4 4.7H5.6l11.1 14.5z" fill="currentColor"/></svg>',
    tg: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21.5 4.2 18.4 19c-.2 1-.8 1.3-1.7.8l-4.6-3.4-2.2 2.1c-.3.3-.5.5-1 .5l.3-4.7 8.6-7.8c.4-.3-.1-.5-.6-.2L6.6 12.9 2 11.5c-1-.3-1-1 .2-1.5l18-6.9c.8-.3 1.6.2 1.3 1.1z" fill="currentColor"/></svg>',
  };
  let CFG = { picks: [], notes: [], invites: [], move: {} };

  /* ---------- live facts, read from what this page already shows ---------- */
  const txt = id => { const e = document.getElementById(id); return e ? e.textContent.trim() : ""; };
  const num = s => /^[\d.,]+$/.test(s) && s !== "0" ? s : "";
  const sim = () => document.body.dataset.mode !== "live";
  const FACTS = [
    () => { const h = num(txt("rH")); return h && { text: `Newest block #${h}, checked against the rules in force`, href: "explorer/" }; },
    () => { const n = txt("rM"); return /^\d+$/.test(n) && { text: n === "1" ? "1 transaction waiting for the next block" : `${n} transactions waiting for the next block`, href: "explorer/" }; },
    () => { const n = txt("rR"); return /^\d+$/.test(n) && n !== "0" && { text: n === "1" ? "1 personal money rule in force on the chain" : `${n} personal money rules in force on the chain`, href: "rules/" }; },
    () => { const e = document.querySelector("#tnOnline .n, #chipOnline b"), n = e ? e.textContent.trim() : ""; return /^\d+$/.test(n) && +n > 1 && { text: `${n} people watching Tau HUD right now`, href: "" }; },
  ];
  let factAt = 0;
  const fact = () => {
    for (let i = 0; i < FACTS.length; i++) {
      const f = FACTS[factAt++ % FACTS.length](); if (!f) continue;
      return { kind: "live", sim: sim(), text: f.text, href: f.href };
    }
    return null;
  };

  /* ---------- the newest Updates log entries, first sentence ---------- */
  let NEWS = [], newsAt = 0;
  const firstSentence = s => { const m = /^(.{12,150}?(?:\.(?=\s|$)|。))/.exec(s); return m ? m[1] : s.length > 150 ? s.slice(0, 147) + "…" : s; };
  const loadNews = () => fetch("assets/updates.json", { cache: "no-cache" }).then(r => r.json()).then(list => {
    NEWS = (Array.isArray(list) ? list : []).slice(-3).reverse().map(e => {
      const plain = String(e.html || "").replace(/<[^>]*>/g, "").replace(/\s+/g, " ").trim();
      if (!plain || !translated(plain)) return null;
      return { kind: "news", text: firstSentence(tr(plain)), raw: true, href: e.major && e.major.link ? String(e.major.link).replace(/^\//, "") : "" };
    }).filter(Boolean);
  }).catch(() => {});

  /* ---------- the rotation: facts carry the line, the rest is mixed in ---------- */
  const SLOTS = ["live", "note", "live", "news", "live", "pick", "live", "invite"];
  let slot = 0, noteAt = 0, pickAt = 0, inviteAt = 0;
  const from = (list, at) => list.length ? list[at % list.length] : null;
  const next = () => {
    for (let tries = 0; tries < SLOTS.length * 2; tries++) {
      const k = SLOTS[slot++ % SLOTS.length]; let it = null;
      if (k === "live") it = fact();
      else if (k === "news") it = NEWS.length ? NEWS[newsAt++ % NEWS.length] : null;
      else if (k === "note") { const n = from(CFG.notes, noteAt++); it = n && { kind: "note", text: n.text, href: n.href }; }
      else if (k === "pick") { const p = from(CFG.picks, pickAt++); it = p && { kind: "x", text: p.text, href: p.href, quote: true }; }
      else if (k === "invite") { const v = from(CFG.invites, inviteAt++); it = v && { kind: v.kind === "tg" ? "tg" : "x", text: v.text, href: v.href }; }
      if (it && it.text && (it.raw || translated(it.text))) return it;
    }
    return { kind: "note", text: "Rules on Tau change only by agreement", href: "start/" };
  };

  /* ---------- one item on the line ---------- */
  function build(it) {
    const a = document.createElement(it.href ? "a" : "span"); a.className = "tk-it k-" + it.kind;
    if (it.href) { a.href = it.href; if (/^https?:/.test(it.href)) { a.target = "_blank"; a.rel = "noopener"; } }
    const mark = document.createElement("i"); mark.className = "tk-mk";
    if (ICON[it.kind]) mark.innerHTML = ICON[it.kind]; else mark.textContent = it.kind === "live" ? "" : it.kind === "news" ? "+" : "›";
    a.append(mark);
    if (it.sim) { const s = document.createElement("em"); s.textContent = tr("Simulation"); a.append(s); }
    let text = it.raw ? it.text : tr(it.text); if (it.quote) text = (lang === "en" ? "“" : "「") + text + (lang === "en" ? "”" : "」");
    const body = document.createElement("span"); body.className = "tk-tx";
    for (const ch of Array.from(text)) { const c = document.createElement("b"); c.textContent = ch; c.dataset.c = ch; body.append(c); }
    a.append(body);
    return a;
  }
  /* letters get a fixed width once laid out, so a glyph in their place never shifts the line */
  function measure(el) {
    el._chars = Array.from(el.querySelectorAll(".tk-tx b")).map(c => { const w = c.getBoundingClientRect().width; c.style.width = w + "px"; return { c, x: c.offsetLeft, w, st: 0 }; });
    el._w = el.getBoundingClientRect().width;
  }

  /* ---------- motion ---------- */
  const SPEED = 46, ZONE = 150, GAP = 56;   // px per second; how far in from the edge a letter is still a glyph; space between items
  let items = [], last = 0, paused = false, W = 0, dir = -1, tick = 0;
  const add = () => {
    const el = build(next()); track.append(el); measure(el);
    const prev = items[items.length - 1];
    el._x = dir < 0 ? (prev ? Math.max(W, prev._x + prev._w + GAP) : W * .55) : (prev ? Math.min(-el._w, prev._x - el._w - GAP) : W * .45 - el._w);
    items.push(el);
  };
  function frame(t) {
    const dt = Math.min(.1, (t - (last || t)) / 1000); last = t;
    if (!paused) for (const el of items) el._x += dir * SPEED * dt;
    items = items.filter(el => { const gone = dir < 0 ? el._x + el._w < -20 : el._x > W + 20; if (gone) el.remove(); return !gone; });
    const tail = items[items.length - 1];
    if (!tail || (dir < 0 ? tail._x + tail._w < W + 400 : tail._x > -400)) add();
    const scramble = (tick = (tick + 1) % 4) === 0;
    for (const el of items) {
      el.style.transform = `translate3d(${el._x.toFixed(1)}px,0,0)`;
      const base = el._x + (el._chars.length ? el._chars[0].c.parentNode.offsetLeft : 0);
      for (const ch of el._chars) {
        const x = base + ch.x, depth = dir < 0 ? W - x : x + ch.w;   // distance from the entering edge
        const st = depth < 0 ? 0 : depth < ZONE * .85 ? 1 : depth < ZONE ? 2 : 3;   // outside, glyph, head, read
        if (st !== ch.st) { ch.c.className = st === 1 ? "g" : st === 2 ? "hd" : ""; if (st >= 2) ch.c.textContent = ch.c.dataset.c; ch.st = st; }
        if (st === 1 && scramble && ch.c.dataset.c.trim()) ch.c.textContent = glyph();
        if (st === 1) ch.c.style.opacity = (.25 + .75 * depth / ZONE).toFixed(2);
        else if (ch.c.style.opacity) ch.c.style.opacity = "";
      }
    }
    requestAnimationFrame(frame);
  }

  /* reduced motion: one item at a time, changed in place */
  function still() {
    const show = () => { track.textContent = ""; const el = build(next()); el.classList.add("still"); track.append(el); };
    show(); setInterval(() => { if (!paused && !document.hidden) show(); }, 7000);
  }

  const lab = box.querySelector(".tk-lab b"); if (lab) lab.textContent = tr(lab.textContent);
  box.setAttribute("aria-label", tr(box.getAttribute("aria-label") || ""));
  for (const ev of ["mouseenter", "focusin"]) view.addEventListener(ev, () => { paused = true; box.classList.add("held"); });
  for (const ev of ["mouseleave", "focusout"]) view.addEventListener(ev, () => { paused = false; box.classList.remove("held"); });
  addEventListener("resize", () => { W = view.clientWidth; });

  Promise.all([
    fetch("assets/ticker.json", { cache: "no-cache" }).then(r => r.json()).then(j => { if (j && typeof j === "object") CFG = { ...CFG, ...j }; }).catch(() => {}),
    loadNews(),
  ]).then(() => {
    const m = (CFG.move || {})[lang] || "left"; dir = m === "right" ? 1 : -1; box.classList.toggle("rtl", dir > 0);
    W = view.clientWidth;
    /* the facts need the page's first readings; give the chain a moment */
    setTimeout(() => { if (reduced) still(); else requestAnimationFrame(frame); }, 1200);
    setInterval(loadNews, 15 * 60 * 1000);
  });
})();

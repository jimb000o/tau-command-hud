/* The HUD's news line under the four principles: short headlines about what is new on the testnet and on Tau HUD,
   live facts read off this page, the headlines of new features from the Updates log, hand-picked posts of ours and
   now and then Telegram and X. Hand-picked content lives in assets/ticker.json (headlines; picks: our X posts worth
   reposting; invites). Each item decodes out of falling glyphs where it enters the line, then reads as plain text.
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
    () => { const h = num(txt("rH")); return h && { text: `Chain at block #${h}`, href: "explorer/" }; },
    () => { const n = txt("rM"); return /^\d+$/.test(n) && { text: n === "1" ? "1 transaction waiting for the next block" : `${n} transactions waiting for the next block`, href: "explorer/" }; },
    () => { const n = txt("rR"); return /^\d+$/.test(n) && n !== "0" && { text: n === "1" ? "1 personal money rule in force" : `${n} personal money rules in force`, href: "rules/" }; },
    () => { const e = document.querySelector("#tnOnline .n, #chipOnline b"), n = e ? e.textContent.trim() : ""; return /^\d+$/.test(n) && +n > 1 && { text: `${n} people on Tau HUD right now`, href: "" }; },
  ];
  let factAt = 0;
  const fact = () => {
    for (let i = 0; i < FACTS.length; i++) {
      const f = FACTS[factAt++ % FACTS.length](); if (!f) continue;
      return { kind: "live", sim: sim(), text: f.text, href: f.href };
    }
    return null;
  };

  /* ---------- new features: the headline of each "major" Updates log entry (the one the channels post), never the
     long log text; a feature already among the hand-written headlines, and round-ups, are left out ---------- */
  let NEWS = [], newsAt = 0;
  const path = h => String(h || "").replace(/^\//, "").replace(/[?#].*$/, "");
  /* the first read shares the page's one download of the log (nav.js TauLog); the 15-minute refresh fetches it anew */
  const loadNews = first => (first && window.TauLog ? Promise.resolve(TauLog()) : fetch("assets/updates.json", { cache: "no-cache" }).then(r => r.json())).then(list => {
    const have = new Set((CFG.headlines || []).map(h => path(h.href)));
    NEWS = (Array.isArray(list) ? list : []).filter(e => e && e.major && e.major.title && !/^roundup/.test(e.major.id || "")).slice(-6).reverse()
      .filter(e => !have.has(path(e.major.link))).slice(0, 4)
      .map(e => ({ kind: "news", text: String(e.major.title), href: path(e.major.link) === "" ? "" : String(e.major.link).replace(/^\//, "") }));
  }).catch(() => {});

  /* ---------- when the Daily Consensus comes out, in the reader's own time: German time in English, China time in
     Chinese, Japan time in Japanese (ticker.json "gazette" per language; the server writes the edition every Monday) ---------- */
  const GZ = { en: { tz: "Europe/Berlin", day: 1, hour: 9 }, zh: { tz: "Asia/Shanghai", day: 1, hour: 9 }, ja: { tz: "Asia/Tokyo", day: 1, hour: 9 } };
  const GZT = {
    en: { next: "Next Daily Consensus: {d} {t} German time", out: "New Daily Consensus out today", today: "today", tomorrow: "tomorrow", days: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"] },
    zh: { next: "下一期《共识日报》：{d} {t}（北京时间）", out: "新一期《共识日报》今天出刊", today: "今天", tomorrow: "明天", days: ["周日", "周一", "周二", "周三", "周四", "周五", "周六"] },
    ja: { next: "次のコンセンサス日報：{d} {t}（日本時間）", out: "今週のコンセンサス日報、本日発行", today: "今日", tomorrow: "明日", days: ["日曜", "月曜", "火曜", "水曜", "木曜", "金曜", "土曜"] },
  };
  const gazette = () => {
    const g = { ...GZ[lang], ...((CFG.gazette || {})[lang] || {}) }, w = GZT[lang] || GZT.en;
    let wd, mins;
    try {
      const parts = new Intl.DateTimeFormat("en-US", { timeZone: g.tz, weekday: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date());
      const v = k => (parts.find(x => x.type === k) || {}).value;
      wd = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(v("weekday")); mins = +v("hour") * 60 + +v("minute");
    } catch (e) { return null; }
    if (wd < 0) return null;
    const since = (wd * 1440 + mins - g.day * 1440 - g.hour * 60 + 10080) % 10080;   // minutes since the last edition
    if (since < 1440) return { kind: "note", text: w.out, href: "gazette/", raw: true };
    let off = (g.day - wd + 7) % 7; if (off === 0 && mins >= g.hour * 60) off = 7;
    const d = off === 0 ? w.today : off === 1 ? w.tomorrow : w.days[g.day];
    return { kind: "note", text: w.next.replace("{d}", d).replace("{t}", String(g.hour).padStart(2, "0") + ":00"), href: "gazette/", raw: true };
  };

  /* ---------- the rotation: facts carry the line, the rest is mixed in ---------- */
  const SLOTS = ["head", "live", "gazette", "news", "live", "head", "pick", "live", "head", "invite"];
  let slot = 0, headAt = 0, pickAt = 0, inviteAt = 0;
  const from = (list, at) => list.length ? list[at % list.length] : null;
  const next = () => {
    for (let tries = 0; tries < SLOTS.length * 2; tries++) {
      const k = SLOTS[slot++ % SLOTS.length]; let it = null;
      if (k === "live") it = fact();
      else if (k === "news") it = NEWS.length ? NEWS[newsAt++ % NEWS.length] : null;
      else if (k === "gazette") it = gazette();
      else if (k === "head") { const n = from(CFG.headlines || [], headAt++); it = n && { kind: "note", text: n.text, href: n.href }; }
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
  /* letters get a fixed width once laid out, so a glyph in their place never shifts the line. Layout sizes, not screen
     sizes: on wide screens the HUD is scaled up as a whole (html.wide), and a scaled width would spread letters and items apart */
  const lw = e => { const r = e.getBoundingClientRect(), z = e.offsetWidth ? r.width / e.offsetWidth : 1; return r.width / (z || 1); };
  function measure(el) {
    el._chars = Array.from(el.querySelectorAll(".tk-tx b")).map(c => { const w = lw(c); c.style.width = w + "px"; return { c, x: c.offsetLeft, w, st: 0 }; });
    el._w = lw(el);
  }

  /* ---------- motion ---------- */
  const SPEED = 46, ZONE = 150, GAP = 44;   // px per second; how far in from the edge a letter is still a glyph; space between items
  let items = [], last = 0, paused = false, W = 0, dir = -1, tick = 0;
  const add = () => {
    const el = build(next()); track.append(el); measure(el);
    const prev = items[items.length - 1];
    /* one fixed gap after the item before; the first items start inside the line and decode where they stand */
    el._x = dir < 0 ? (prev ? prev._x + prev._w + GAP : W * .3) : (prev ? prev._x - el._w - GAP : W * .7 - el._w);
    if (dir < 0 ? el._x < W : el._x + el._w > 0) el._born = performance.now();
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
      const age = el._born ? t - el._born : 1e9; if (el._born && age > 400 + el._chars.length * 22) el._born = 0;
      el._chars.forEach((ch, i) => {
        const x = base + ch.x, depth = dir < 0 ? W - x : x + ch.w;   // distance from the entering edge
        const born = age - 300 - i * 22;   // an item that starts inside the line decodes letter by letter
        const st = depth < 0 ? 0 : depth < ZONE * .85 || born < 0 ? 1 : depth < ZONE || born < 80 ? 2 : 3;   // outside, glyph, head, read
        if (st !== ch.st) { ch.c.className = st === 1 ? "g" : st === 2 ? "hd" : ""; if (st >= 2) ch.c.textContent = ch.c.dataset.c; ch.st = st; }
        if (st === 1 && scramble && ch.c.dataset.c.trim()) ch.c.textContent = glyph();
        if (st === 1) ch.c.style.opacity = (.25 + .75 * Math.min(1, depth / ZONE)).toFixed(2);
        else if (ch.c.style.opacity) ch.c.style.opacity = "";
      });
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
    fetch("assets/ticker.json", { cache: "no-cache" }).then(r => r.json()).then(j => { if (j && typeof j === "object") CFG = { ...CFG, ...j }; }).catch(() => {}).then(() => loadNews(true)),
    /* letters are measured once, so wait for the page's monospace font: measured in a fallback font they keep its wider spacing */
    Promise.race([document.fonts ? document.fonts.ready : Promise.resolve(), new Promise(r => setTimeout(r, 4000))]),
  ]).then(() => {
    const m = (CFG.move || {})[lang] || "left"; dir = m === "right" ? 1 : -1; box.classList.toggle("rtl", dir > 0);
    W = view.clientWidth;
    /* the facts need the page's first readings; give the chain a moment */
    setTimeout(() => { if (reduced) still(); else requestAnimationFrame(frame); }, 1200);
    setInterval(() => loadNews(false), 15 * 60 * 1000);
  });
})();

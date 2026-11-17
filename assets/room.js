/* The room, 1999: an immersive mode for the HUD. You sit at a late-90s desk at night; the chain runs on three tube
   monitors, and the things on the desk answer to it.

   - Main screen: the HUD's own node log (the lines under the Chain core), as a terminal tail. Left screen: the block
     height in big digits and the last blocks. Right screen: the rules in force (validators, votes needed, fee, spec
     revision, personal rules, what waits) and the open rule changes with their votes. Everything comes from the HUD on
     this page (window.TauRoom in index.html), read only; with the simulation on, every screen says SIMULATION in amber.
   - The pager on the desk shows the height and buzzes at each block. The phone rings when a rule change is proposed;
     pick it up and the main screen reads it out. The modem's lights follow the connection (CD = the live node), and a
     click on it prints the line state. The lamp switches on and off. Click a screen to lean in, again or Esc to sit back.
   - Way in: the ▣ button beside the settings, Explore → "The room · 1999", or ?room=1. Esc or "Stand up" leaves it.
     It needs a window 900 px wide and wider than tall; below that the button is hidden.
   - Start: the whole room shows at once, lights low; the main screen boots (a short POST, then it dials the node and says CONNECT or NO
     CARRIER for what the HUD really shows), then the lights come up and the other two tubes switch on. Return visits are shorter; a
     click or key skips it; no boot with prefers-reduced-motion.
   - Sound (dial tone and handshake at the start, the phone's ring) only after a click and only while "Sound" is on;
     remembered in localStorage (tauhud-room-sound).
   - The room is a painting (assets/room/room.json: a 16:9 picture and a 21:9 one for ultrawide windows, with the
     screens, the pager's display, the modem's lamps and the things you can click as fractions of the picture). The
     window flashes with lightning, the cat purrs, the lava lamp wakes, the tower's disk works. Without room.json the
     drawn room-1999.svg is the room. room.json's "live" will hold the moving clips laid over the painting. */
(() => {
  const root = document.documentElement, $ = id => document.getElementById(id);
  const q = new URLSearchParams(location.search);
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const BASE = (document.querySelector('script[src*="assets/room.js"]') || {}).src ? new URL("room/", document.querySelector('script[src*="assets/room.js"]').src).href : "assets/room/";
  const get = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const put = (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} };

  /* the room's few words in Chinese and Japanese, so the page's dictionaries stay untouched */
  const L = {
    zh: { "Stand up": "起身", "Sound on": "声音 开", "Sound off": "声音 关", "Full screen": "全屏",
      "Click a screen to lean in. The phone rings when someone proposes a rule change; the pager buzzes at every block.": "点击屏幕凑近看。有人提出规则变更时电话会响；每出一个区块，寻呼机就会震动。",
      "click or any key: skip": "点击或按任意键跳过", "Type help and press Enter. Click a screen to lean in; the phone rings at each rule change, the pager buzzes at every block.": "输入 help 并按回车。点击屏幕凑近看；每次规则变更电话会响，每出一个区块寻呼机就会震动。", "The room, 1999": "1999 年的房间", "The room needs a wider window (900 px and up, wider than tall).": "这个房间需要更宽的窗口（900 px 以上，横向）。" },
    ja: { "Stand up": "立ち上がる", "Sound on": "音 オン", "Sound off": "音 オフ", "Full screen": "全画面",
      "Click a screen to lean in. The phone rings when someone proposes a rule change; the pager buzzes at every block.": "画面をクリックすると近づきます。ルール変更が提案されると電話が鳴り、ブロックごとにポケベルが震えます。",
      "click or any key: skip": "クリックまたは任意のキーでスキップ", "Type help and press Enter. Click a screen to lean in; the phone rings at each rule change, the pager buzzes at every block.": "help と入力して Enter を押してください。画面をクリックすると近づきます。ルール変更のたびに電話が鳴り、ブロックごとにポケベルが震えます。", "The room, 1999": "1999 年の部屋", "The room needs a wider window (900 px and up, wider than tall).": "この部屋には広い画面が必要です（幅 900 px 以上、横長）。" },
  };
  const T = s => ((L[window.TauI18n && TauI18n.lang] || {})[s] || s);

  /* where things are, in room px (1600 × 900) */
  const GEO = {
    art: "room-1999.svg", w: 1600, h: 900, frame: [110, 150, 1490, 850],
    scr: { main: [568, 266, 464, 348], left: [222, 402, 256, 192], right: [1122, 402, 256, 192] },
    spots: { lamp: [30, 500, 170, 300], phone: [1170, 720, 210, 105], pager: [484, 786, 92, 48], modem: [288, 708, 196, 58] },
  };
  /* the painted room: room.json, one picture per window shape */
  let PAINT = null, VAR = null;
  const loadPaint = () => PAINT !== null ? Promise.resolve(PAINT) : fetch(BASE + "room.json", { cache: "no-cache" })
    .then(r => r.ok ? r.json() : null).catch(() => null).then(j => (PAINT = j && Array.isArray(j.variants) && j.variants.length ? j : false));
  function pick() {
    if (!PAINT) return null;
    const a = innerWidth / innerHeight; let best = PAINT.variants[0];
    for (const v of PAINT.variants) if (a >= (v.minAspect || 0) && (v.minAspect || 0) >= (best.minAspect || 0)) best = v;
    return best;
  }
  function useVariant(v) {
    VAR = v; const W = 1600, H = Math.round(W * v.h / v.w);
    const bx = f => [f[0] * W, f[1] * H, (f[2] - f[0]) * W, (f[3] - f[1]) * H].map(Math.round);
    const spots = {}; for (const k in v.spots || {}) spots[k] = bx(v.spots[k]);
    Object.assign(GEO, { art: v.src, w: W, h: H, frame: [0, 0, W, H], spots, scr: { main: bx(v.screens.main), left: bx(v.screens.left), right: bx(v.screens.right) },
      lcd: v.lcd ? bx(v.lcd) : null, rain: v.rain ? bx(v.rain) : null, leds: v.leds || null, pc: v.pc ? [v.pc[0] * W, v.pc[1] * H] : null });
  }
  const LABEL = { lamp: "Desk lamp", phone: "Telephone", pager: "Pager: the block height", modem: "Modem: the line to the node", window: "The window",
    cat: "The cat", lava: "Lava lamp", tower: "The PC", mug: "Coffee", picture: "The picture", cables: "Cables" };
  const fits = () => innerWidth >= 900 && innerHeight >= 480 && innerWidth / innerHeight >= 1.2;

  let el = null, cam = null, scr = {}, view = null, on = false, booting = false, R = null, timer = null, hintT = null;
  const st = { h: 0, mem: 0, lastLog: null, seenU: null, ring: null, ringT: null, typing: [], sound: get("tauhud-room-sound") !== "off", gesture: false };

  const mk = (tag, cls, html) => { const n = document.createElement(tag); if (cls) n.className = cls; if (html != null) n.innerHTML = html; return n; };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const tpl = document.createElement("template");
  const plain = h => { tpl.innerHTML = String(h); return tpl.content.textContent; };   // a template parses without running anything
  const place = (n, r) => Object.assign(n.style, { left: r[0] + "px", top: r[1] + "px", width: r[2] + "px", height: r[3] + "px" });
  const num = n => R && R.fmt ? R.fmt(n) : String(n);

  function status() {
    if (!R) return "wait";
    if (!R.liveChain()) return "sim";
    return R.offline() ? "off" : "live";
  }
  const TAG = { live: '<b class="st-live">● LIVE</b>', sim: '<b class="st-sim">● SIMULATION</b>', off: '<b class="st-off">● OFFLINE</b>', wait: '<b class="muted">● …</b>' };

  /* ---------------- building the room ---------------- */
  function build() {
    el = mk("div"); el.id = "room"; el.setAttribute("role", "dialog"); el.setAttribute("aria-label", T("The room, 1999"));
    cam = mk("div", "rm-cam");
    const art = mk("img", "rm-art"); art.alt = ""; art.decoding = "async"; art.src = BASE + GEO.art;
    cam.append(art);
    if (VAR) el.classList.add("painted");
    cam.append(mk("i", "rm-dark"));
    cam.append(mk("i", "rm-glow main"), mk("i", "rm-glow left"), mk("i", "rm-glow right"));
    for (const k of ["main", "left", "right"]) {
      const s = mk("div", "rm-scr off " + (k === "main" ? "main" : "side"), '<div class="rm-in"></div>');
      s.dataset.k = k; place(s, GEO.scr[k]); s.addEventListener("click", e => { e.stopPropagation(); lean(k); }); cam.append(s); scr[k] = s;
    }
    cam.append(mk("i", "rm-light"));
    if (!VAR) {
    /* the calendar: this month, laid out as it fell in 1999, today ringed */
    const now = new Date(), m = now.getMonth(), first = (new Date(1999, m, 1).getDay() + 6) % 7, days = new Date(1999, m + 1, 0).getDate();
    const MON = "JANUARY FEBRUARY MARCH APRIL MAY JUNE JULY AUGUST SEPTEMBER OCTOBER NOVEMBER DECEMBER".split(" ")[m];
    let g = "MTWTFSS".split("").map(d => `<b>${d}</b>`).join("") + "<i></i>".repeat(first);
    for (let d = 1; d <= days; d++) g += `<b${d === now.getDate() ? ' class="today"' : ""}>${d}</b>`;
    cam.append(mk("div", "rm-cal", `<div class="pic"></div><div class="mo">${MON} 1999</div><div class="g">${g}</div>`));
    cam.append(mk("div", "rm-note", ""));
    }
    const pc = mk("div", "rm-pc", '<i class="pw on"></i><i class="hdd"></i>'); cam.append(pc);
    /* the things you can touch */
    /* in the painting each one is cut from the picture itself, so it can shake, ring and light up on hover */
    const DO = { lamp: () => { el.classList.toggle("lamp-off"); click(); }, phone: () => answer(), pager: () => lean("left"), modem: () => modemSays(),
      window: () => thunder(), cat: () => purr(), lava: () => lava(), tower: () => disk() };
    const svgImg = f => `<img alt="" src="${BASE}${f}" style="width:100%;height:100%;display:block">`;
    for (const k of ["window", "lava", "tower", "cat", "lamp", "modem", "pager", "phone"]) {
      if (!VAR && !["lamp", "phone", "pager", "modem"].includes(k)) continue;
      const b = mk("button", "rm-hot rm-" + k + (VAR ? " cut" : ""), VAR ? "" : k === "phone" ? svgImg("phone.svg") : k === "pager" ? svgImg("pager.svg") : "");
      b.type = "button"; b.dataset.k = k; b.setAttribute("aria-label", LABEL[k]); b.title = LABEL[k];
      b.addEventListener("click", e => { e.stopPropagation(); st.gesture = true; DO[k](); }); cam.append(b);
    }
    cam.append(mk("i", "rm-bell", "RING"));
    cam.append(mk("div", "rm-lcd"));
    cam.append(mk("div", "rm-leds", "MR HS AA CD OH RD SD TR".split(" ").map(k => `<i data-l="${k}"></i>`).join("")));
    cam.append(mk("i", "rm-rain"), mk("i", "rm-flash"), mk("i", "rm-lavaglow"), mk("i", "rm-purr", "prrr"));
    cam.append(mk("i", "rm-vig"));
    el.append(cam);
    /* page px */
    const ui = mk("div", "rm-ui");
    const bs = mk("button", "", ""); bs.type = "button"; const sl = () => { bs.textContent = T(st.sound ? "Sound on" : "Sound off"); bs.setAttribute("aria-pressed", st.sound); };
    sl(); bs.addEventListener("click", e => { e.stopPropagation(); st.sound = !st.sound; put("tauhud-room-sound", st.sound ? "on" : "off"); sl(); if (!st.sound) hush(); });
    const bf = mk("button", "", "⛶"); bf.type = "button"; bf.title = T("Full screen"); bf.setAttribute("aria-label", T("Full screen"));
    bf.addEventListener("click", e => { e.stopPropagation(); if (document.fullscreenElement) document.exitFullscreen().catch(() => {}); else if (root.requestFullscreen) root.requestFullscreen().catch(() => {}); });
    if (!(document.fullscreenEnabled && root.requestFullscreen)) bf.hidden = true;
    const bx = mk("button", "", T("Stand up") + " ✕"); bx.type = "button"; bx.addEventListener("click", e => { e.stopPropagation(); leave(); });
    ui.append(bs, bf, bx); el.append(ui);
    el.append(mk("div", "rm-hint gone", esc(T("Type help and press Enter. Click a screen to lean in; the phone rings at each rule change, the pager buzzes at every block."))));
    el.append(mk("div", "rm-skip", esc(T("click or any key: skip"))));
    el.addEventListener("click", () => { if (view) lean(null); });
    el.addEventListener("pointerdown", () => { st.gesture = true; }, true);
    document.body.append(el);
    layout();
  }
  /* everything in room px follows GEO: the SVG room keeps its CSS places, the painting sets them here */
  function layout() {
    if (!cam) return;
    const art = cam.querySelector(".rm-art"); if (!art.src.endsWith("/" + GEO.art)) art.src = BASE + GEO.art;
    Object.assign(cam.style, { width: GEO.w + "px", height: GEO.h + "px" }); Object.assign(art.style, { width: GEO.w + "px", height: GEO.h + "px" });
    for (const k in scr) place(scr[k], GEO.scr[k]);
    for (const b of cam.querySelectorAll(".rm-hot")) {
      const r = GEO.spots[b.dataset.k]; b.hidden = !r; if (!r) continue;
      place(b, r);
      if (!VAR) continue;
      /* where a thing stands in front of a screen, its mask lets the screen's glass through */
      /* and a soft edge, so a lit or shaking thing never shows the corners of its cut */
      const m = (VAR.masks || {})[b.dataset.k], soft = "radial-gradient(ellipse 50% 50% at 50% 50%, #000 62%, transparent 100%)";
      const mu = m ? `url("${BASE + m}"), ${soft}` : soft;
      Object.assign(b.style, { backgroundImage: `url("${BASE + GEO.art}")`, backgroundSize: `${GEO.w}px ${GEO.h}px`, backgroundPosition: `${-r[0]}px ${-r[1]}px`,
        maskImage: mu, webkitMaskImage: mu, maskSize: "100% 100%", webkitMaskSize: "100% 100%", maskComposite: "intersect", webkitMaskComposite: "source-in" });
    }
    if (!VAR) return;
    /* each screen takes the exact shape of its painted glass (glass-*.png, traced from the picture) */
    for (const k in scr) {
      const g = (VAR.glass || {})[k], gu = g ? `url("${BASE + g}")` : "";
      Object.assign(scr[k].style, { maskImage: gu, webkitMaskImage: gu, maskSize: "100% 100%", webkitMaskSize: "100% 100%", borderRadius: g ? "0" : "" });
    }
    for (const k of ["main", "left", "right"]) {
      const [x, y, w, h] = GEO.scr[k], f = k === "main" ? 1.9 : 2.1;
      place(cam.querySelector(".rm-glow." + k), [x + w / 2 - w * f / 2, y + h / 2 - h * f * .55, w * f, h * f * 1.15]);
    }
    const hide = (sel, r) => { const n = cam.querySelector(sel); n.hidden = !r; if (r) place(n, r); return n; };
    hide(".rm-rain", GEO.rain);
    const fl = hide(".rm-flash", GEO.spots.window), fm = (VAR.masks || {}).window ? `url("${BASE + VAR.masks.window}")` : "";
    Object.assign(fl.style, { maskImage: fm, webkitMaskImage: fm, maskSize: "100% 100%", webkitMaskSize: "100% 100%" }); hide(".rm-lavaglow", GEO.spots.lava);
    const c = GEO.spots.cat; hide(".rm-purr", c && [c[0] + c[2] * .2, c[1] - c[3] * .2, c[2] * .6, c[3] * .4]);
    const p = GEO.spots.phone; hide(".rm-bell", p && [p[0] + p[2] * .2, p[1] - 22, p[2] * .6, 18]);
    const lcd = hide(".rm-lcd", GEO.lcd); if (GEO.lcd) lcd.style.fontSize = (GEO.lcd[3] * .78).toFixed(1) + "px";
    const L = GEO.leds, d = L ? L.d * GEO.w : 0;
    const leds = hide(".rm-leds", L && [L.x0 * GEO.w - d / 2, L.y * GEO.h - d / 2, (L.x1 - L.x0) * GEO.w + d, d]); if (L) leds.style.setProperty("--d", d.toFixed(1) + "px");
    hide(".rm-pc", GEO.pc && [GEO.pc[0] - 3.5, GEO.pc[1] - 3.5, 8, 22]);
    place(cam.querySelector(".rm-vig"), [-40, -40, GEO.w + 80, GEO.h + 80]);
    place(cam.querySelector(".rm-dark"), [0, 0, GEO.w, GEO.h]);
  }

  /* ---------------- the camera ---------------- */
  function fitBox() {
    const W = innerWidth, H = innerHeight, [x0, y0, x1, y1] = GEO.frame;
    const cover = Math.max(W / GEO.w, H / GEO.h), want = Math.min(W / (x1 - x0), H / (y1 - y0));
    const s = Math.max(cover, want);
    let tx = W / 2 - (x0 + x1) / 2 * s, ty = H / 2 - (y0 + y1) / 2 * s;
    tx = Math.min(0, Math.max(W - GEO.w * s, tx)); ty = Math.min(0, Math.max(H - GEO.h * s, ty));
    return { s, tx, ty };
  }
  function onScreen(k, fill) {
    const W = innerWidth, H = innerHeight, [x, y, w, h] = GEO.scr[k];
    const s = fill ? Math.min(W / w, H / h) * 1.06 : Math.min(W * .9 / w, H * .84 / h);
    return { s, tx: W / 2 - (x + w / 2) * s, ty: H / 2 - (y + h / 2) * s };
  }
  function shoot(p, move, quick) {
    cam.classList.toggle("moving", !!move && !REDUCED); cam.classList.toggle("quick", !!quick);
    cam.style.transform = `translate(${p.tx.toFixed(1)}px, ${p.ty.toFixed(1)}px) scale(${p.s.toFixed(4)})`;
    if (move) setTimeout(() => cam.classList.remove("moving", "quick"), 1300);   // crisp text once it stands still
  }
  function lean(k) {
    if (booting) return;
    if (k && view === k) k = null;
    view = k;
    for (const n of Object.values(scr)) n.classList.toggle("big", n.dataset.k === k);
    shoot(k ? onScreen(k) : fitBox(), true, true);
  }
  function frame() { if (!on || booting) return; shoot(view ? onScreen(view) : fitBox(), false); }

  /* ---------------- sound: made here, nothing to load ---------------- */
  let ac = null, out = null;
  function audio() {
    if (!st.sound || !st.gesture) return null;
    try { if (!ac) { ac = new (window.AudioContext || window.webkitAudioContext)(); out = ac.createGain(); out.gain.value = .14; out.connect(ac.destination); }
      if (ac.state === "suspended") ac.resume(); return ac; } catch (e) { return null; }
  }
  function hush() { if (ac) { try { ac.close(); } catch (e) {} ac = null; out = null; } }
  function tone(fs, t0, dur, vol = 1, type = "sine") {
    const a = audio(); if (!a) return;
    const g = a.createGain(); g.gain.setValueAtTime(0, a.currentTime + t0); g.gain.linearRampToValueAtTime(vol, a.currentTime + t0 + .01);
    g.gain.setValueAtTime(vol, a.currentTime + t0 + dur - .02); g.gain.linearRampToValueAtTime(0, a.currentTime + t0 + dur); g.connect(out);
    for (const f of fs) { const o = a.createOscillator(); o.type = type; o.frequency.value = f; o.connect(g); o.start(a.currentTime + t0); o.stop(a.currentTime + t0 + dur + .02); }
  }
  function noise(t0, dur, vol) {
    const a = audio(); if (!a) return;
    const b = a.createBuffer(1, Math.floor(a.sampleRate * dur), a.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    const s = a.createBufferSource(), f = a.createBiquadFilter(), g = a.createGain(); s.buffer = b; f.type = "bandpass"; f.frequency.value = 1800; f.Q.value = .8;
    g.gain.value = vol; s.connect(f); f.connect(g); g.connect(out); s.start(a.currentTime + t0);
  }
  /* the dial: tone, the number, then the two modems agreeing (short; skipped without a click) */
  function dialSound() {
    if (!audio()) return;
    tone([350, 440], 0, .55, .5);
    const D = { 1: [697, 1209], 2: [697, 1336], 3: [697, 1477], 4: [770, 1209], 5: [770, 1336], 6: [770, 1477], 7: [852, 1209], 8: [852, 1336], 9: [852, 1477], 0: [941, 1336] };
    "5550199".split("").forEach((c, i) => tone(D[c], .65 + i * .1, .07, .5));
    const t = 1.5; tone([2100], t, .45, .35); tone([1650, 1850], t + .5, .35, .3, "square"); noise(t + .5, .9, .5); tone([980, 1180], t + .9, .45, .25, "sawtooth");
  }
  const ringSound = () => { for (let i = 0; i < 2; i++) tone([440, 480], i * .5, .4, .45); };
  const click = () => tone([2400], 0, .02, .25, "square");
  function rumble(t0, dur, vol, freq) {
    const a = audio(); if (!a) return;
    const b = a.createBuffer(1, Math.floor(a.sampleRate * dur), a.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / d.length, 1.6);
    const s = a.createBufferSource(), f = a.createBiquadFilter(), g = a.createGain(); s.buffer = b; f.type = "lowpass"; f.frequency.value = freq || 160;
    g.gain.value = vol; s.connect(f); f.connect(g); g.connect(out); s.start(a.currentTime + t0); return { s, g };
  }

  /* ---------------- the things in the room ---------------- */
  function poke(n, cls, ms) { if (!n) return; n.classList.remove(cls); void n.offsetWidth; n.classList.add(cls); clearTimeout(n._t); n._t = setTimeout(() => n.classList.remove(cls), ms); }
  function thunder() {
    poke(cam.querySelector(".rm-flash"), "go", 1600);
    if (REDUCED) return;
    setTimeout(() => rumble(0, 2.6, 1.6, 140), 450);
  }
  function purr() {
    poke(cam.querySelector(".rm-purr"), "go", 2400);
    const a = audio(); if (!a) return;
    const r = rumble(0, 2.2, 1.1, 110); if (!r) return;
    const lfo = a.createOscillator(), lg = a.createGain(); lfo.frequency.value = 24; lg.gain.value = .9; lfo.connect(lg); lg.connect(r.g.gain);
    lfo.start(); lfo.stop(a.currentTime + 2.2);
  }
  function lava() { el.classList.toggle("lava-on"); click(); }
  function disk() {
    for (let i = 0; i < 7; i++) setTimeout(() => { blink(".rm-pc .hdd", 70); tone([90 + Math.random() * 60], 0, .03, .5, "square"); }, i * 110 + Math.random() * 60);
    const S = R ? R.S : null; if (!S) return;
    say(`C:\\> mem · ${S.blocks.length} blocks kept on this page · ${S.mempool.length} tx waiting · ${S.validators.length || "?"} validators`);
  }

  /* ---------------- the boot ---------------- */
  const sleep = ms => new Promise(r => { const t0 = performance.now(), tick = () => (st.skip || performance.now() - t0 >= ms) ? r() : setTimeout(tick, 16); tick(); });
  async function boot() {
    const seen = get("tauhud-room-seen") === "1", main = scr.main, box = main.querySelector(".rm-in");
    booting = true; el.classList.add("booting"); st.skip = false;
    const skip = e => { if (e.type === "keydown" && e.key === "Escape") return; st.skip = true; };
    addEventListener("keydown", skip, true); el.addEventListener("pointerdown", skip, true);
    /* the whole room from the first frame, lights low, only the main tube awake; nothing zooms */
    shoot(fitBox(), false);
    const art = cam.querySelector(".rm-art"); try { if (!art.complete) await Promise.race([art.decode(), new Promise(r => setTimeout(r, 2500))]); } catch (e) {}
    main.classList.remove("off"); main.classList.add("on");
    box.innerHTML = '<div class="rm-term rm-post"></div>'; const term = box.firstChild;
    const line = (t, cls) => { const p = mk("p", cls || "", esc(t)); term.append(p); return p; };
    const dots = (k, v) => (k + " ").padEnd(22, ".") + " " + v;
    await sleep(380);
    if (!st.skip) {
      line("TAU-99 BIOS v4.51 · (C) 1999", "sys");
      line("night shift workstation", "muted"); await sleep(seen ? 120 : 300);
      if (!seen) {
        line(dots("CPU", "450 MHz")); await sleep(140);
        const mem = line(dots("MEMORY", "0K"));
        for (let k = 0; k <= 131072 && !st.skip; k += 8192) { mem.textContent = dots("MEMORY", k + "K" + (k === 131072 ? " OK" : "")); await sleep(22); }
        line(dots("IDE PRIMARY MASTER", "13.6 GB")); await sleep(140);
        line(dots("YEAR 2000 CHECK", "PASSED")); await sleep(260);
      }
      line(""); line("C:\\> dial node.tauhud.com", "sys"); await sleep(seen ? 160 : 320);
      dialSound();
      const at = line("ATDT node.tauhud.com ");
      const cur = mk("span", "rm-cur"); at.append(cur);
      /* the HUD starts on the simulation and switches to the live node within a few seconds when it answers */
      const t0 = performance.now();
      while (!st.skip && status() !== "live" && performance.now() - t0 < (seen ? 2600 : 3600)) await sleep(120);
      if (!st.skip) await sleep(Math.max(0, 1500 - (performance.now() - t0)));
      cur.remove();
    }
    const s = status();
    line(s === "live" ? "CONNECT 56000 · Tau Testnet Alpha · the live chain" : s === "off" ? "NO CARRIER · the live node does not answer right now" : "NO CARRIER · these screens show the simulation in this browser", s === "live" ? "" : s === "off" ? "bad" : "warn");
    await sleep(st.skip ? 120 : 520);
    main.classList.add("glitch"); setTimeout(() => main.classList.remove("glitch"), 360);
    removeEventListener("keydown", skip, true); el.removeEventListener("pointerdown", skip, true);
    put("tauhud-room-seen", "1");
    booting = false; el.classList.add("waking"); el.classList.remove("booting"); setTimeout(() => el.classList.remove("waking"), 1800);
    st.lastLog = null; st.term = null;
    render(true);
    shoot(fitBox(), false);
    setTimeout(() => powerOn("left"), 650); setTimeout(() => powerOn("right"), 900);
    hint(); welcome();
  }
  function welcome() { setTimeout(() => { if (on) { say("type help and press Enter · this shell only reads the chain, nothing you type can break anything", "sys"); sh.last = performance.now() - 45000; } }, 1200); }
  function powerOn(k) { const s = scr[k]; if (!s || !on) return; s.classList.remove("off"); s.classList.add("on"); render(true); }
  function hint() {
    const h = el.querySelector(".rm-hint"); if (!h || get("tauhud-room-hint") === "3") return;
    put("tauhud-room-hint", String((+get("tauhud-room-hint") || 0) + 1));
    setTimeout(() => h.classList.remove("gone"), 1400); clearTimeout(hintT); hintT = setTimeout(() => h.classList.add("gone"), 9500);
  }

  /* ---------------- the screens ---------------- */
  const DIG = { 0: ["███", "█ █", "█ █", "█ █", "███"], 1: ["██ ", " █ ", " █ ", " █ ", "███"], 2: ["███", "  █", "███", "█  ", "███"], 3: ["███", "  █", "███", "  █", "███"],
    4: ["█ █", "█ █", "███", "  █", "  █"], 5: ["███", "█  ", "███", "  █", "███"], 6: ["███", "█  ", "███", "█ █", "███"], 7: ["███", "  █", "  █", "  █", "  █"],
    8: ["███", "█ █", "███", "█ █", "███"], 9: ["███", "█ █", "███", "  █", "███"] };
  const bigDigits = n => { const d = String(n).split(""); return [0, 1, 2, 3, 4].map(r => d.map(c => (DIG[c] || ["   ", "   ", "   ", "   ", "   "])[r]).join(" ")).join("\n"); };
  const ago = b => { const t = Number(b && b.ts); if (!(t > 1.5e9)) return ""; const s = Math.max(0, Date.now() / 1000 - t); return s < 90 ? Math.round(s) + "s" : s < 5400 ? Math.round(s / 60) + "m" : (s / 3600).toFixed(1) + "h"; };
  const head = (title, s) => `<div class="h"><span>${title}</span>${TAG[s]}</div>`;
  const CLS = c => /warn/.test(c) ? "warn" : /err|bad|fail|refus/.test(c) ? "bad" : "";

  function feedTerm(force) {
    const S = R.S, LOG = R.LOG;
    if (!st.term || force) { st.term = []; st.lastLog = null; }
    let i = st.lastLog ? LOG.lastIndexOf(st.lastLog) : -1, add;
    add = i >= 0 ? LOG.slice(i + 1) : LOG.slice(-14);
    if (LOG.length) st.lastLog = LOG[LOG.length - 1];
    if (!force && sh.busy()) return;   // while you type, the node log waits; it comes back after a minute of quiet
    for (const e of add) st.term.push({ t: e.t, txt: plain(e.msg), cls: CLS(e.cls || ""), fresh: !force && i >= 0 });
    if (st.term.length > 40) st.term.splice(0, st.term.length - 40);
  }
  function say(txt, cls) { if (!st.term) st.term = []; st.term.push({ t: clock(), txt, cls: cls || "sys", fresh: true }); renderMain(); }
  const clock = () => new Date().toTimeString().slice(0, 8);

  function renderMain() {
    const s = status(), box = scr.main.querySelector(".rm-in");
    let term = box.querySelector(".rm-term");
    if (!term || !box.querySelector(".h")) {
      box.innerHTML = head("TAU TESTNET ALPHA · node log", s) + '<div class="rm-term"></div><p class="rm-prompt">root@tau:~# <span class="rm-typed"></span><span class="rm-cur"></span></p>';
      term = box.querySelector(".rm-term"); term.dataset.n = "0";
    }
    const hd = box.querySelector(".h"), want = `<span>TAU TESTNET ALPHA · #${num(R.S.height || 0)}</span>${TAG[s]}`;
    if (hd.innerHTML !== want) hd.innerHTML = want;
    const typed = box.querySelector(".rm-typed"); if (typed && typed.textContent !== sh.line) typed.textContent = sh.line;
    const have = +term.dataset.n || 0, list = st.term || [];
    if (have > list.length) { term.innerHTML = ""; term.dataset.n = "0"; return renderMain(); }
    for (let k = have; k < list.length; k++) {
      const e = list[k], p = mk("p", e.cls, `<span class="t">${esc(e.t)}</span>`), span = mk("span", "", "");
      p.append(span); term.append(p);
      if (e.fresh && !REDUCED) type(span, e.txt); else span.textContent = e.txt;
    }
    term.dataset.n = String(list.length);
    while (term.children.length > 40) { term.firstChild.remove(); }
  }
  function type(span, txt) {
    let n = 0; const step = Math.max(2, Math.ceil(txt.length / 28));
    const go = () => { n = Math.min(txt.length, n + step); span.textContent = txt.slice(0, n); if (n < txt.length) setTimeout(go, 22); };
    go();
  }

  function renderLeft() {
    const S = R.S, s = status(), box = scr.left.querySelector(".rm-in");
    const h = S.height || 0, digits = String(h).length, fs = Math.min(6.2, 88 / (digits * 4 - 1) / .6);
    const rows = S.blocks.slice(-4).reverse().map((b, i) => {
      const tx = (b.txs || []).length;
      return `<div${i === 0 && st.newBlock ? ' class="new"' : ""}>#${String(b.n).padEnd(7)} ${String(tx).padStart(2)} tx  ${esc(R.short(b.proposer || "")).padEnd(11)} ${ago(b).padStart(4)}</div>`;
    }).join("");
    const html = head("BLOCKS", s) + `<pre class="rm-big" style="font-size:${fs.toFixed(2)}cqw">${bigDigits(h)}</pre><div class="rm-rows">${rows || '<div class="muted">waiting for the first block…</div>'}</div>`;
    if (box.dataset.k !== html) { box.innerHTML = html; box.dataset.k = html; }
  }

  function bar(v, n) { n = Math.max(1, n); const k = Math.min(10, Math.round(v / n * 10)); return "█".repeat(k) + "░".repeat(10 - k); }
  function renderRight() {
    const S = R.S, s = status(), box = scr.right.querySelector(".rm-in");
    const N = S.validators.length, thr = N ? R.threshold() : "—";
    const open = S.updates.filter(u => u.status === "voting" || u.status === "scheduled").slice(-2).reverse();
    const kv = [["validators", N || "—"], ["votes needed", thr], ["fee / step", S.fee], ["spec revision", S.specRev], ["personal rules", S.clauses.size], ["waiting", S.mempool.length + " tx"]]
      .map(([k, v]) => `<span class="muted">${k}</span><span>${esc(v)}</span>`).join("");
    const ch = open.length ? open.map(u => `<div>${esc(String(u.title || "rule change").slice(0, 30))}</div><div class="muted"><span class="rm-bar">${bar(u.votes.size, N ? R.threshold() : 1)}</span> ${u.votes.size}/${thr} ${u.status === "scheduled" ? "agreed" : "voting"}</div>`).join("")
      : '<div class="muted">no open rule change</div>';
    const html = head("RULES IN FORCE", s) + `<div class="rm-kv">${kv}</div><div style="margin-top:.5em">RULE CHANGES</div>${ch}`;
    if (box.dataset.k !== html) { box.innerHTML = html; box.dataset.k = html; }
  }

  function render(force) {
    if (!on || booting || !R) return;
    const S = R.S, s = status();
    el.classList.toggle("st-sim", s === "sim");
    feedTerm(force); if (!scr.main.classList.contains("off")) renderMain();
    if (!scr.left.classList.contains("off")) renderLeft();
    if (!scr.right.classList.contains("off")) renderRight();
    /* desk */
    const lcd = el.querySelector(".rm-lcd"), ht = S.height ? "#" + String(S.height).slice(-6) : "----";
    if (lcd.textContent !== ht) { lcd.textContent = ht; if (GEO.lcd) lcd.style.fontSize = Math.min(GEO.lcd[3] * .78, GEO.lcd[2] / (ht.length * .62)).toFixed(1) + "px"; }
    const note = el.querySelector(".rm-note"), nt = `node.tauhud.com\nfee ${S.fee}/step\n${S.validators.length || "?"} validators`;
    if (note && note.textContent !== nt) { note.textContent = nt; note.style.whiteSpace = "pre"; }
    const led = (k, v) => { const i = el.querySelector(`.rm-leds [data-l="${k}"]`); if (i) i.classList.toggle("on", !!v); };
    led("MR", true); led("TR", true); led("HS", s === "live"); led("CD", s === "live"); led("OH", s !== "sim"); led("AA", false);
  }
  function blink(sel, ms) { const i = el.querySelector(sel); if (!i) return; i.classList.add("on"); setTimeout(() => i.classList.remove("on"), ms || 160); }

  /* ---------------- the heartbeat: blocks, waiting txs, rule changes ---------------- */
  function tick() {
    if (!on) return;
    if (!R) { R = window.TauRoom || null; if (!R) return; }
    const S = R.S;
    if (st.seenU == null) st.seenU = new Set(S.updates.map(u => u.id));
    if (S.height !== st.h) {
      const first = !st.h; st.h = S.height; st.newBlock = !first;
      if (!first && !booting && sh.watch) { const b = S.blocks[S.blocks.length - 1]; if (b) say(`#${b.n} ${ts(b)} · ${(b.txs || []).length} tx · sealed by ${R.short(b.proposer || "") || "?"}`, ""); }
      if (!first && !booting) {
        for (const k of ["left"]) { scr[k].classList.remove("flash"); void scr[k].offsetWidth; scr[k].classList.add("flash"); }
        const p = el.querySelector(".rm-lcd"), pb = el.querySelector(".rm-hot.rm-pager");
        p.classList.add("lit"); setTimeout(() => p.classList.remove("lit"), 1800);
        if (!REDUCED) for (const n of [p, pb]) { n.classList.remove("buzz"); void n.offsetWidth; n.classList.add("buzz"); }
        blink('.rm-leds [data-l="RD"]', 420); blink(".rm-pc .hdd", 260); setTimeout(() => blink(".rm-pc .hdd", 180), 340);
        const g = el.querySelector(".rm-glow.left"); g.classList.remove("pulse"); void g.offsetWidth; g.classList.add("pulse");
      }
    } else st.newBlock = false;
    if (S.mempool.length > st.mem) { blink('.rm-leds [data-l="SD"]', 260); blink(".rm-pc .hdd", 120); }
    st.mem = S.mempool.length;
    for (const u of S.updates) {
      if (st.seenU.has(u.id)) continue;
      st.seenU.add(u.id);
      if (u.status === "voting" && !booting) ring(u);
    }
    render(false);
  }

  function ring(u) {
    st.ring = u; el.classList.add("ringing"); const ph = el.querySelector(".rm-hot.rm-phone"); if (!REDUCED) ph.classList.add("ring");
    clearInterval(st.ringT); let n = 0; ringSound();
    st.ringT = setInterval(() => { if (++n >= 4 || !on) { stopRing(); return; } ringSound(); }, 2600);
  }
  function stopRing() { clearInterval(st.ringT); st.ringT = null; el.classList.remove("ringing"); el.querySelector(".rm-hot.rm-phone").classList.remove("ring"); }
  function answer() {
    const S = R ? R.S : null; if (!S) return;
    const u = st.ring || S.updates.filter(x => x.status === "voting" || x.status === "scheduled").slice(-1)[0];
    const was = !!st.ring; stopRing(); st.ring = null; click();
    if (!u) { say("☎ dial tone. No rule change is open right now."); return; }
    const N = S.validators.length, thr = N ? R.threshold() : "—";
    say(`☎ ${was ? "incoming" : "last call"}: rule change ${u.status === "scheduled" ? "agreed" : "proposed"} · "${String(u.title || "").slice(0, 60)}"`);
    say(`   ${u.votes.size} of ${thr} votes${u.activateAt ? " · takes effect at #" + num(u.activateAt) : ""}${status() === "sim" ? " · SIMULATION" : ""}`, status() === "sim" ? "warn" : "sys");
  }
  function modemSays() {
    click(); const s = status(), S = R ? R.S : null; if (!S) return;
    if (s === "live") say(`ATI · CONNECT · node.tauhud.com · the live chain · block #${num(S.height)}`);
    else if (s === "off") say("ATI · NO CARRIER · the live node does not answer right now; the HUD keeps trying", "bad");
    else say("ATI · NO CARRIER · this browser runs the simulation (see Live / Simulation in the HUD's header)", "warn");
  }


  /* ---------------- the shell: you type, the chain answers ----------------
     A small 1999 shell on the main screen. Every answer is read from the HUD on this page (read only: nothing typed
     here is signed or sent). The node log pauses while you type and comes back after a minute of quiet. */
  const sh = {
    line: "", hist: [], hi: 0, last: 0, n: 0, watch: false, call: null,
    busy() { return performance.now() - this.last < 60000 || this.watch; },
  };
  const pad = (v, n) => String(v).padEnd(n);
  const ts = b => { const t = Number(b && b.ts); return t > 1.5e9 ? new Date(t * 1000).toTimeString().slice(0, 8) : "--:--:--"; };
  const amt = t => t.amount ? ` ${num(t.amount)} AGRS` : (t.transfers && t.transfers.length ? ` ${t.transfers.length} transfer${t.transfers.length > 1 ? "s" : ""}` : "");
  const txLine = t => `  ${pad(R.short(t.id || ""), 13)} ${pad(t.type || "tx", 22)} from ${R.short(t.sender || "") || "?"}${amt(t)}`;
  const wr = (txt, cls) => say(txt, cls || "");
  const why = txt => say("  › " + txt, "muted");   // the plain-words line for beginners
  const CMDS = {
    help() {
      wr("commands (read only, nothing is sent):", "sys");
      wr("  block [n]    trace a block: hash, state, proposer, its transactions");
      wr("  blocks       the last blocks · pending   what waits to be sealed");
      wr("  tx <id>      find a transaction by the start of its id");
      wr("  rules        the rules in force · changes   open rule changes");
      wr("  validators   who seals the blocks · status   the line to the node");
      wr("  watch        follow the chain block by block (any key stops)");
      wr("  whoami · lamp · clear · exit");
      why("new here? start with: blocks, then block, then rules. Each answer says in plain words what it means.");
    },
    status() { modemSays(); },
    whoami() { wr("guest@node.tauhud.com · you read the chain, you sign nothing. Real moves are made with a wallet, in No Memo for one."); },
    blocks() { const b = R.S.blocks.slice(-8).reverse(); if (!b.length) return wr("no blocks yet", "warn"); b.forEach(x => wr(`#${pad(x.n, 7)} ${ts(x)}  ${pad((x.txs || []).length + " tx", 6)} sealed by ${R.short(x.proposer || "") || "?"}`));
      why("a block is one page of the shared record. Every few seconds a validator seals the next page; nobody can change a sealed page."); },
    block(a) {
      const S = R.S, n = a ? Number(String(a).replace("#", "")) : S.height, b = S.byHeight.get(n) || S.blocks.find(x => x.n === n);
      if (!b) return wr(`#${a} is not on this page (it keeps the last ${S.blocks.length} blocks; ${S.blocks[0] ? "#" + S.blocks[0].n + " to #" + S.height : "none yet"})`, "warn");
      trace(`block #${b.n}`, () => {
        wr(`#${b.n} · sealed ${ts(b)} by ${R.short(b.proposer || "") || "?"}`, "sys");
        wr(`  hash  ${b.hash || "?"}`); wr(`  prev  ${b.prev || (S.byHeight.get(b.n - 1) || {}).hash || "?"}`); wr(`  state ${b.state || "?"}`);
        const t = b.txs || []; wr(`  ${t.length} transaction${t.length === 1 ? "" : "s"}`); t.slice(0, 6).forEach(x => wr(txLine(x))); if (t.length > 6) wr(`  … ${t.length - 6} more`, "muted");
        why("hash = this page's fingerprint, prev = the page before it, so the pages form a chain. state = the fingerprint of every balance and rule after this page.");
      });
    },
    pending() { const m = R.S.mempool; if (!m.length) wr("nothing waits · every sent transaction is sealed"); else { wr(`${m.length} waiting:`, "sys"); m.slice(-8).forEach(x => wr(txLine(x))); }
      why("a sent transaction first passes the rules at the door, then waits here until a validator seals it into the next block."); },
    tx(a) {
      if (!a || a.length < 4) return wr("tx <first 4+ characters of the id>", "warn");
      const k = a.toLowerCase(); let hit = null, where = "";
      for (const b of R.S.blocks.slice().reverse()) { const t = (b.txs || []).find(x => String(x.id || "").toLowerCase().startsWith(k)); if (t) { hit = t; where = "sealed in #" + b.n; break; } }
      if (!hit) { hit = R.S.mempool.find(x => String(x.id || "").toLowerCase().startsWith(k)); where = hit ? "waiting, not sealed yet" : ""; }
      if (!hit) return wr(`no transaction ${a}… on this page`, "warn");
      trace("tx " + a, () => { wr(`${hit.id}`, "sys"); wr(`  ${hit.type} · ${where}`); wr(`  from ${hit.sender || "?"}`); if (hit.to) wr(`  to   ${hit.to}`); if (hit.amount) wr(`  amount ${num(hit.amount)} AGRS`); wr(`  fee ${hit.fee}`); });
    },
    rules() {
      const S = R.S, N = S.validators.length;
      wr(`validators ${N || "?"} · votes needed ${N ? R.threshold() : "?"} · fee ${S.fee} per step · spec revision ${S.specRev} · personal rules ${S.clauses.size}`);
      why("on Tau Net the rules themselves live on the chain, written in the Tau language. Validators change them by vote; anyone can add a personal rule for their own wallet.");
    },
    changes() {
      const u = R.S.updates.filter(x => x.status === "voting" || x.status === "scheduled").slice(-4);
      why("a rule change is a proposal to rewrite part of the network's rules. It takes effect only when enough validators vote for it.");
      if (!u.length) return wr("no open rule change");
      u.forEach(x => wr(`"${String(x.title || "rule change").slice(0, 50)}" · ${x.votes.size}/${R.threshold()} ${x.status === "scheduled" ? "agreed, takes effect at #" + num(x.activateAt) : "voting"}`));
    },
    validators() { const v = R.S.validators; if (!v.length) return wr("no validator list yet", "warn"); v.forEach((x, i) => wr(`  ${i + 1}. ${R.short(x)}`));
      why("validators take turns sealing blocks and vote on rule changes. Each one is a wallet, shown by the start of its key."); },
    watch() { sh.watch = true; wr("watching the chain · any key stops", "sys"); },
    lamp() { el.classList.toggle("lamp-off"); click(); },
    clear() { st.term = []; const t = scr.main.querySelector(".rm-term"); if (t) { t.innerHTML = ""; t.dataset.n = "0"; } },
    exit() { leave(); },
  };
  CMDS["?"] = CMDS.help; CMDS.ls = CMDS.help; CMDS.mempool = CMDS.pending; CMDS.wait = CMDS.pending; CMDS.cls = CMDS.clear; CMDS.quit = CMDS.exit;
  /* a trace prints a short search before the answer: the feeling of finding it yourself */
  function trace(what, done) {
    if (REDUCED) return done();
    wr(`tracing ${what} `, "muted"); let k = 0;
    const hex = () => Array.from({ length: 24 }, () => "0123456789abcdef"[Math.random() * 16 | 0]).join("");
    const t = setInterval(() => { if (!on) return clearInterval(t); if (++k > 4) { clearInterval(t); done(); return; } wr(`  ${hex()} … ${k * 25}%`, "muted"); tone([900 + k * 120], 0, .03, .2, "square"); }, 140);
  }
  function run(cmd) {
    const [c, ...a] = cmd.trim().split(/\s+/); if (!c) return;
    wr(`root@tau:~# ${cmd}`, "sys");
    sh.hist.push(cmd); sh.hi = sh.hist.length; sh.n++;
    blink(".rm-pc .hdd", 120);
    if (!R) return wr("no carrier", "bad");
    const f = CMDS[c.toLowerCase()];
    if (sh.call && sh.call.wait) return callAnswer(cmd);
    if (f) f(a.join(" ")); else wr(`${c}: not a command here · type help`, "warn");
    if (sh.n === 3 && !get("tauhud-room-call")) setTimeout(nightCall, 2400);
  }
  function key(e) {
    if (!on || booting || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.target && e.target.closest && e.target.closest("input, textarea, [contenteditable]")) return;
    const k = e.key;
    if (sh.watch && k !== "Escape") { sh.watch = false; wr("stopped watching", "muted"); e.preventDefault(); return; }
    if (k === "Enter") { const c = sh.line; sh.line = ""; run(c); }
    else if (k === "Backspace") sh.line = sh.line.slice(0, -1);
    else if (k === "ArrowUp") { sh.hi = Math.max(0, sh.hi - 1); sh.line = sh.hist[sh.hi] || ""; }
    else if (k === "ArrowDown") { sh.hi = Math.min(sh.hist.length, sh.hi + 1); sh.line = sh.hist[sh.hi] || ""; }
    else if (k === "Tab") { const m = Object.keys(CMDS).filter(x => x.startsWith(sh.line.toLowerCase())); if (m.length === 1) sh.line = m[0] + " "; }
    else if (k.length === 1 && sh.line.length < 60) sh.line += k;
    else return;
    e.preventDefault(); sh.last = performance.now();
    if (k.length === 1 || k === "Backspace" || k === "Enter") tone([180 + Math.random() * 80], 0, .018, .35, "square");
    if (view && view !== "main" && k === "Enter") lean("main");
    renderMain();
  }
  addEventListener("keydown", key);

  /* ---------------- the night call: someone on the line tests whether you can read the chain ----------------
     Three questions, answered from the live screens. Right answers light the room; it happens once per browser. */
  function nightCall() {
    if (!on || booting || !R) return;
    const S = R.S, N = S.validators.length;
    const Q = [
      { q: "how many validators seal the blocks right now? (right screen)", a: () => String(N) },
      { q: "what does one step cost, the fee? (same screen)", a: () => String(S.fee) },
      { q: "and the newest block, its number? (left screen, the big digits)", a: () => String(S.height), near: 2 },
    ];
    sh.call = { Q, i: 0, wait: true, ok: 0 };
    ringSound(); el.classList.add("ringing"); setTimeout(() => el.classList.remove("ringing"), 1600);
    wr("", ""); wr("*** talk request from nobody@0.0.0.0 ***", "warn");
    wr("nobody: you're up late. reading the chain by hand?", "warn");
    wr("nobody: let's see if you can. answer here.", "warn");
    setTimeout(() => wr("nobody: " + Q[0].q, "warn"), 900);
  }
  function callAnswer(txt) {
    const c = sh.call, q = c.Q[c.i], want = q.a(), got = txt.trim().replace(/[#,.\s]/g, "");
    const ok = q.near ? Math.abs(Number(got) - Number(want)) <= q.near : got === want;
    if (ok) { c.ok++; wr("nobody: right.", "warn"); } else wr(`nobody: no. ${want}. look at the screens.`, "warn");
    c.i++;
    if (c.i < c.Q.length) { setTimeout(() => wr("nobody: " + c.Q[c.i].q, "warn"), 700); return; }
    c.wait = false; sh.call = null; put("tauhud-room-call", "1");
    if (c.ok === c.Q.length) {
      setTimeout(() => { wr("nobody: you read it like plain text. most people only see the lights.", "warn"); wr("nobody: the rest is on the chain. *** connection closed ***", "warn"); awaken(); }, 800);
    } else setTimeout(() => { wr(`nobody: ${c.ok} of 3. come back when you can read it. *** connection closed ***`, "warn"); }, 800);
  }
  function awaken() {
    for (const k in scr) { scr[k].classList.remove("flash"); void scr[k].offsetWidth; scr[k].classList.add("flash"); }
    thunder(); el.classList.add("lava-on");
    el.classList.add("waking", "booting"); setTimeout(() => el.classList.remove("booting"), 260); setTimeout(() => el.classList.remove("waking"), 2000);
  }

  /* ---------------- in and out ---------------- */
  function enter(withClick) {
    if (on) return;
    if (!fits()) { flash(T("The room needs a wider window (900 px and up, wider than tall).")); return; }
    if (withClick) st.gesture = true;
    if (PAINT === null) { loadPaint().then(() => enter(withClick)); return; }
    const v = pick(); if (v && v !== VAR) { useVariant(v); layout(); }
    if (!el) build();
    on = true; root.classList.add("room-on"); el.hidden = false; view = null;
    R = window.TauRoom || null;
    if (!q.has("room")) { try { const u = new URL(location.href); u.searchParams.set("room", "1"); history.replaceState(history.state, "", u); } catch (e) {} }
    for (const k in scr) { scr[k].classList.add("off"); scr[k].classList.remove("on", "big"); scr[k].querySelector(".rm-in").innerHTML = ""; delete scr[k].querySelector(".rm-in").dataset.k; }
    st.h = R ? R.S.height : 0; st.mem = R ? R.S.mempool.length : 0; st.seenU = null;
    clearInterval(timer); timer = setInterval(tick, 400); tick();
    if (REDUCED || q.get("intro") === "0" || navigator.webdriver && q.get("intro") !== "1") {
      booting = false; el.classList.remove("booting"); for (const k in scr) { scr[k].classList.remove("off"); }
      render(true); shoot(fitBox(), false); hint(); welcome();
    } else boot();
    el.tabIndex = -1; el.focus({ preventScroll: true });   // keys go to the shell, not to a button
  }
  function leave() {
    if (!on) return;
    on = false; st.skip = true; clearInterval(timer); stopRing(); hush();
    el.hidden = true; root.classList.remove("room-on");
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    try { const u = new URL(location.href); u.searchParams.delete("room"); history.replaceState(history.state, "", u); } catch (e) {}
    const b = document.querySelector(".tn-room"); if (b) b.focus({ preventScroll: true });
  }
  function flash(msg) {
    const n = mk("div", "rm-hint", esc(msg)); Object.assign(n.style, { position: "fixed", zIndex: 2147483001 }); document.body.append(n);
    setTimeout(() => n.classList.add("gone"), 3200); setTimeout(() => n.remove(), 4200);
  }

  addEventListener("keydown", e => {
    if (!on || e.key !== "Escape") return;
    e.preventDefault(); if (booting) { st.skip = true; return; }
    if (view) lean(null); else leave();
  });
  addEventListener("resize", () => {
    if (!on) return; if (!fits()) { leave(); return; }
    const v = pick(); if (v && v !== VAR) { useVariant(v); layout(); }
    frame();
  });
  document.addEventListener("visibilitychange", () => { if (on && !document.hidden) render(false); });

  /* the way in: a button beside the settings, the menu entry (no reload on this page), and ?room=1 */
  const ICON = '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1.5" y="2" width="13" height="9.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M5 14h6M8 11.5V14" stroke="currentColor" stroke-width="1.4"/><path d="M4.5 5.5l2 1.5-2 1.5M8 8.5h3" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>';
  function door() {
    const r = document.querySelector('nav.tnav[data-page="hud"] .tnav-r');
    if (!r) return false;
    if (r.querySelector(".tn-room")) return true;
    const b = mk("button", "tn-room", ICON + "<span>1999</span>"); b.type = "button";
    const lbl = T("The room, 1999"); b.setAttribute("aria-label", lbl); b.dataset.full = lbl + ": the HUD on three tube monitors in a late-90s room. The phone rings at each rule change, the pager buzzes at each block.";
    b.addEventListener("click", () => enter(true));
    const gear = r.querySelector(".tn-gear, [data-slot=gear], .gear") || r.lastElementChild;
    if (gear && gear.parentNode === r) r.insertBefore(b, gear); else r.append(b);
    return true;
  }
  document.addEventListener("click", e => {
    const a = e.target.closest && e.target.closest("a[href]"); if (!a) return;
    try { const u = new URL(a.href, location.href); if (u.pathname === location.pathname && u.searchParams.get("room") === "1") { e.preventDefault(); enter(true); } } catch (x) {}
  }, true);
  function init() {
    let n = 0; const t = setInterval(() => { if (door() || ++n > 40) clearInterval(t); }, 250);
    if (q.get("room") === "1") {
      let k = 0; const w = setInterval(() => { if (window.TauRoom || ++k > 40) { clearInterval(w); enter(false); } }, 100);
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true }); else init();
  window.TauRoomMode = { enter: () => enter(true), leave };
})();

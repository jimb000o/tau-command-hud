/* The cabin of the Black Sequence around No Memo (see scene.css). You sit at the ship's terminal desk; the game is
   what its screen shows.

   - nomemo/art/cabin/cabin.json lists the paintings (16:9 and 21:9) with the black screen, the lantern and the windows
     as fractions of the picture. Until it is there, nothing changes.
   - The painting that fits the window is drawn so the screen is at least about 1040 × 520 px (the camera comes close on
     a laptop) and covers the window where it can (the whole cabin on a big monitor). Below 900 px wide or on a tall
     window the page stays the plain terminal.
   - Living cabin: the lantern flickers, the cabin rocks a hair, moonlight moves on the water, the screen lights the desk
     and glows brighter while the terminal writes; a refused transaction flashes red, an accepted one brightens the
     lantern, a chapter card turns it gold; Tuesday 18:00–20:00 German time (the pirate op) a red alarm lamp turns.
   - Living paintings: `live` in cabin.json lists short painted loops (sea, moon, lantern flame, hourglass sand) cut
     from the painting and played over it through a soft mask, so only what moves changes; during the Tuesday op the
     sea runs rough where a `rough` loop exists. No loops with reduced motion or Save-Data; paused in a hidden tab.
   - Sitting down: on load the cabin shows whole, then the camera comes to the screen (a click skips it).
   - `scene off` / `stand up` and `scene on` / `sit down` in the terminal, or the ⌂ button in the top bar; remembered in
     localStorage (tauhud-nomemo-scene). prefers-reduced-motion: no rocking, no flicker, no camera move. */
(() => {
  const root = document.documentElement, $ = id => document.getElementById(id);
  const KEY = "tauhud-nomemo-scene", BASE = "art/cabin/";
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const LIVE = !REDUCED && !(navigator.connection && navigator.connection.saveData);
  const get = () => { try { return localStorage.getItem(KEY); } catch (e) { return null; } };
  const put = v => { try { localStorage.setItem(KEY, v); } catch (e) {} };
  let meta = null, cur = null, el = null, want = get() !== "off", shown = false, introDone = false, last = null;

  /* its few lines in Chinese and Japanese here, so the page's dictionaries stay untouched */
  const L = {
    zh: { "stand up (scene off)": "起身（scene off）", "sit down at the ship's terminal (scene on)": "在船上的终端前坐下（scene on）",
      "The cabin is still being painted. The terminal works the same.": "船舱还在绘制中。终端照常工作。",
      "You stand up from the desk. scene on sits you down again.": "你从桌前站起来。输入 scene on 再坐下。",
      "The cabin needs a wider window (900 px and up). The terminal works the same.": "船舱需要更宽的窗口（900 px 以上）。终端照常工作。",
      "You sit down at the ship's terminal. scene off stands you up.": "你在船上的终端前坐下。输入 scene off 起身。" },
    ja: { "stand up (scene off)": "立ち上がる（scene off）", "sit down at the ship's terminal (scene on)": "船の端末の前に座る（scene on）",
      "The cabin is still being painted. The terminal works the same.": "船室はまだ描いている途中です。端末はいつも通り使えます。",
      "You stand up from the desk. scene on sits you down again.": "机から立ち上がった。scene on でまた座る。",
      "The cabin needs a wider window (900 px and up). The terminal works the same.": "船室には広い画面（900 px 以上）が必要です。端末はいつも通り使えます。",
      "You sit down at the ship's terminal. scene off stands you up.": "船の端末の前に座った。scene off で立ち上がる。" },
  };
  const T = s => ((L[window.TauI18n && TauI18n.lang] || {})[s] || s);

  function build() {
    el = document.createElement("div"); el.className = "cabin"; el.setAttribute("aria-hidden", "true");
    el.innerHTML = '<div class="cab-room"><div class="cab-sway"><img alt="" decoding="async"><i class="cab-spill"></i><i class="cab-lamp"></i><i class="cab-alarm"></i></div></div><div class="cab-shade"></div><div class="cab-glass"></div>';
    document.body.prepend(el);
  }

  function fits(W, H) { return W >= 900 && H >= 520 && W / H >= 1.15; }

  function pick(AW, AH) {
    const r = AW / AH;
    return meta.variants.slice().sort((a, b) => Math.abs(Math.log(a.w / a.h / r)) - Math.abs(Math.log(b.w / b.h / r)))[0];
  }

  /* where the header ends: the scene uses the window below it */
  function headerBottom() {
    let y = 0;
    for (const n of document.querySelectorAll(".wrap > header, .tnav, #mtabs")) {
      const r = n.getBoundingClientRect(); if (r.height && getComputedStyle(n).display !== "none") y = Math.max(y, r.bottom);
    }
    return Math.round(y);
  }

  function place(v, W, H, Y0) {
    const AW = W, AH = H - Y0, [x0, y0, x1, y1] = v.screen, sw = (x1 - x0) * v.w, sh = (y1 - y0) * v.h;
    const cover = Math.max(W / v.w, H / v.h);
    const need = Math.max(Math.min(1040, AW - 24) / sw, Math.min(520, AH - 24) / sh);
    const most = Math.min((AW - 8) / sw, (AH - 8) / sh);
    const s = Math.min(Math.max(cover, need), most), iw = v.w * s, ih = v.h * s;
    let left = AW / 2 - (x0 + x1) / 2 * iw, top = Y0 + AH / 2 - (y0 + y1) / 2 * ih;
    if (iw >= W) left = Math.min(0, Math.max(W - iw, left)); else left = (W - iw) / 2;
    if (ih >= H) top = Math.min(0, Math.max(H - ih, top));
    const gy = top + y0 * ih;                          // the screen must stay below the header and inside the window
    if (gy < Y0 + 4) top += Y0 + 4 - gy;
    const gb = top + y1 * ih; if (gb > H - 4) top -= gb - (H - 4);
    return { s, iw, ih, left, top, g: [left + x0 * iw, top + y0 * ih, sw * s, sh * s] };
  }

  function layout(intro) {
    const W = innerWidth, H = innerHeight;
    if (!want || !meta || !fits(W, H)) { off(); return; }
    const Y0 = headerBottom();
    const v = pick(W, H - Y0);
    const img = el.querySelector("img");
    if (cur !== v) { cur = v; img.src = BASE + v.src; place_items(v); }
    const p = place(v, W, H, Y0); last = { p, v, W, H };
    const room = el.querySelector(".cab-room");
    room.style.width = p.iw + "px"; room.style.height = p.ih + "px";
    room.style.left = p.left + "px"; room.style.top = p.top + "px";
    const inset = Math.max(3, Math.round(Math.min(p.g[2], p.g[3]) * 0.006));
    const set = (k, n) => root.style.setProperty(k, Math.round(n) + "px");
    set("--gx", p.g[0] + inset); set("--gy", p.g[1] + inset); set("--gw", p.g[2] - 2 * inset); set("--gh", p.g[3] - 2 * inset);
    set("--gp", Math.max(6, Math.min(14, p.g[2] * 0.008))); set("--hdr", Y0 + 30);
    const top = $("top"); set("--toph", top ? top.offsetHeight : 36);
    if (!shown) { root.classList.add("scene"); shown = true; btn(); playing(true); }
    if (intro && !introDone && !REDUCED) sitDown(); else introDone = true;
  }

  function place_items(v) {
    const sway = el.querySelector(".cab-sway");
    sway.querySelectorAll(".cab-port").forEach(n => n.remove());
    for (const w of v.windows || []) {
      const i = document.createElement("i"); i.className = "cab-port";
      Object.assign(i.style, { left: w[0] * 100 + "%", top: w[1] * 100 + "%", width: (w[2] - w[0]) * 100 + "%", height: (w[3] - w[1]) * 100 + "%" });
      sway.append(i);
    }
    const lamp = el.querySelector(".cab-lamp");
    lamp.style.left = v.lamp[0] * 100 + "%"; lamp.style.top = v.lamp[1] * 100 + "%";
    lamp.style.width = 36 * v.h / v.w + "%";
    live(v);
  }

  /* the painted loops over the painting; each fades in once it can play, so a slow line shows the still picture */
  function live(v) {
    const sway = el.querySelector(".cab-sway");
    sway.querySelectorAll(".cab-live").forEach(n => n.remove());
    root.classList.remove("cab-alive");
    if (!LIVE) return;
    const img = sway.querySelector("img");
    for (const c of v.live || []) {
      const [x0, y0, x1, y1] = c.box, m = "url(" + BASE + c.mask + ")";
      const vid = document.createElement("video");
      vid.className = "cab-live"; vid.muted = true; vid.loop = true; vid.playsInline = true; vid.preload = "auto";
      vid.setAttribute("muted", ""); vid.setAttribute("playsinline", ""); vid.setAttribute("aria-hidden", "true");
      Object.assign(vid.style, { left: x0 * 100 + "%", top: y0 * 100 + "%", width: (x1 - x0) * 100 + "%", height: (y1 - y0) * 100 + "%",
        webkitMaskImage: m, maskImage: m });
      vid.dataset.calm = BASE + c.src; if (c.rough) vid.dataset.rough = BASE + c.rough;
      vid.addEventListener("playing", () => { vid.classList.add("on"); root.classList.add("cab-alive"); });
      img.after(vid);
      seen.observe(vid);   // loaded only once it is in view: on a laptop the camera sits close and most loops stay outside
    }
  }
  const seen = "IntersectionObserver" in window ? new IntersectionObserver(es => {
    for (const e of es) { e.target.inView = e.isIntersecting; wake(e.target); }
  }) : { observe: v => { v.inView = true; wake(v); } };
  function wake(vid) {
    if (vid.inView && shown && !document.hidden) { if (!vid.getAttribute("src")) vid.src = sea(vid); vid.play().catch(() => {}); }
    else vid.pause();
  }
  /* each loop is there as .webm (VP9, smaller) and .mp4 (H.264); the browser gets the one it plays */
  const WEBM = (() => { try { return !!document.createElement("video").canPlayType('video/webm; codecs="vp9"'); } catch (e) { return false; } })();
  function sea(vid) { const s = root.classList.contains("cab-op") && vid.dataset.rough || vid.dataset.calm; return WEBM ? s.replace(/\.mp4$/, ".webm") : s; }
  function swapSea() {
    if (!el) return;
    for (const vid of el.querySelectorAll(".cab-live[data-rough]")) {
      if (!vid.getAttribute("src")) continue;
      const want = sea(vid); if (vid.src.endsWith(want)) continue;
      vid.classList.remove("on"); vid.src = want; wake(vid);
    }
  }
  function playing(on) {
    if (!el) return;
    for (const vid of el.querySelectorAll(".cab-live")) on ? wake(vid) : vid.pause();
  }
  document.addEventListener("visibilitychange", () => playing(true));

  /* the camera from standing at the door to the chair */
  function from(p, W, H) {
    const s0 = Math.min(W / p.iw, H / p.ih, 0.82);
    const tx = (W - p.iw * s0) / 2 - p.left, ty = (H - p.ih * s0) / 2 + H * 0.04 - p.top;
    return `translate(${tx}px, ${ty}px) scale(${s0})`;
  }
  function sitDown() {
    introDone = true;
    const room = el.querySelector(".cab-room"), { p, W, H } = last;
    root.classList.add("cab-intro"); room.style.transform = from(p, W, H);
    void room.offsetWidth;
    const go = () => { root.classList.add("cab-move"); room.style.transform = ""; setTimeout(() => root.classList.remove("cab-intro"), 1100); setTimeout(() => root.classList.remove("cab-move"), 1600); };
    const t = setTimeout(go, 700);
    const skip = () => { clearTimeout(t); root.classList.remove("cab-move"); room.style.transform = ""; root.classList.remove("cab-intro"); };
    addEventListener("pointerdown", skip, { once: true }); addEventListener("keydown", skip, { once: true });
  }
  function standUp(done) {
    if (REDUCED || !shown || !last) { done(); return; }
    const room = el.querySelector(".cab-room"), { p, W, H } = last;
    root.classList.add("cab-move", "cab-intro"); room.style.transform = from(p, W, H);
    setTimeout(() => { root.classList.remove("cab-move", "cab-intro"); room.style.transform = ""; done(); }, 1300);
  }

  function off() {
    if (!shown) return;
    shown = false; root.classList.remove("scene", "cab-intro", "cab-move");
    playing(false);
    for (const k of ["--gx", "--gy", "--gw", "--gh", "--gp", "--hdr", "--toph"]) root.style.removeProperty(k);
    btn();
  }

  /* the ⌂ button next to sound and full screen */
  function btn() {
    let b = $("sceneBtn");
    if (!b) {
      const fs = $("fsBtn"); if (!fs) return;
      b = document.createElement("button"); b.type = "button"; b.id = "sceneBtn"; b.textContent = "⌂";
      b.addEventListener("click", () => toggle(!want, false));
      fs.before(b);
    }
    b.hidden = !meta || !fits(innerWidth, innerHeight);
    b.classList.toggle("has", false);
    b.title = want ? T("stand up (scene off)") : T("sit down at the ship's terminal (scene on)");
  }

  function toggle(on, quiet) {
    want = on; put(on ? "on" : "off");
    if (on) { introDone = false; layout(true); }
    else standUp(off);
    btn();
    return on && !(meta && fits(innerWidth, innerHeight)) ? "narrow" : "ok";
  }

  /* `scene on|off`, `sit down`, `stand up` in the terminal, before the game reads the line */
  function print(cmd, text) {
    const s = $("screen"); if (!s) return;
    const a = document.createElement("p"); a.className = "you"; a.textContent = cmd;
    const b = document.createElement("p"); b.className = "sys"; b.textContent = text;
    s.append(a, b); const w = $("screenWrap"); if (w) w.scrollTop = w.scrollHeight;
  }
  document.addEventListener("submit", e => {
    if (!e.target || e.target.id !== "cmdForm") return;
    const input = $("cmd"), raw = (input && input.value || "").trim(), v = raw.toLowerCase().replace(/\s+/g, " ");
    let on = null;
    if (v === "scene on" || v === "sit down") on = true;
    else if (v === "scene off" || v === "stand up") on = false;
    else if (v === "scene") on = !want;
    else return;
    e.preventDefault(); e.stopImmediatePropagation(); input.value = "";
    if (!meta) return print(raw, T("The cabin is still being painted. The terminal works the same."));
    const r = toggle(on, false);
    print(raw, !on ? T("You stand up from the desk. scene on sits you down again.")
      : r === "narrow" ? T("The cabin needs a wider window (900 px and up). The terminal works the same.")
      : T("You sit down at the ship's terminal. scene off stands you up."));
  }, true);

  /* the cabin reacts to the game */
  function pulse(cls, ms) { root.classList.remove(cls); void root.offsetWidth; root.classList.add(cls); clearTimeout(pulse[cls]); pulse[cls] = setTimeout(() => root.classList.remove(cls), ms); }
  function watch() {
    const term = document.querySelector(".term");
    if (term) new MutationObserver(() => {
      if (term.classList.contains("flash-bad")) pulse("cab-bad", 700);
      if (term.classList.contains("flash-ok")) pulse("cab-ok", 1400);
    }).observe(term, { attributes: true, attributeFilter: ["class"] });
    const screen = $("screen");
    if (screen) new MutationObserver(() => pulse("cab-busy", 260)).observe(screen, { childList: true });
    const card = $("card");
    if (card) new MutationObserver(() => { if (card.classList.contains("show")) pulse("cab-gold", 2600); }).observe(card, { attributes: true, attributeFilter: ["class"] });
  }
  function op() {   // Tuesday 18:00–20:00 in Germany: the Black Sequence runs its op at White Rabbit Key
    let d = "", h = 0;
    try { const f = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Berlin", weekday: "short", hour: "2-digit", hour12: false }).formatToParts(new Date());
      d = (f.find(x => x.type === "weekday") || {}).value; h = +(f.find(x => x.type === "hour") || {}).value; } catch (e) {}
    const was = root.classList.contains("cab-op");
    root.classList.toggle("cab-op", d === "Tue" && h >= 18 && h < 20);
    if (was !== root.classList.contains("cab-op")) swapSea();
  }

  let rt = 0;
  addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => layout(false), 120); });
  document.addEventListener("fullscreenchange", () => setTimeout(() => layout(false), 60));
  let full = root.classList.contains("nm-full");   // full screen hides the header: the scene gets the whole window
  new MutationObserver(() => { const f = root.classList.contains("nm-full"); if (f !== full) { full = f; setTimeout(() => layout(false), 30); } }).observe(root, { attributes: true, attributeFilter: ["class"] });

  async function start() {
    build(); watch(); op(); setInterval(op, 60000);
    try {
      const r = await fetch(BASE + "cabin.json", { cache: "no-cache" });
      if (!r.ok) return;
      const j = await r.json();
      if (!j || !Array.isArray(j.variants) || !j.variants.length) return;
      meta = j;
    } catch (e) { return; }
    btn();
    if (!want || !fits(innerWidth, innerHeight)) return;
    const v = pick(innerWidth, innerHeight - headerBottom()), img = el.querySelector("img");
    cur = v; img.src = BASE + v.src; place_items(v);
    try { await img.decode(); } catch (e) { return; }
    layout(true);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();

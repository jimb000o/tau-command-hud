/* No Memo: a contract arrives as a transmission. When the game opens a contract's brief (read j…, take N), it sends the
   event "nomemo:transmission" (game.js transmit()); this file takes it over: the sender's painted face, big, in the
   terminal's green, as a weak, glitchy picture on a bad line, while they read the contract out in their own voice.
   - The picture: the portrait (nomemo/art/crew/<who>-<mood>.webp) drawn small and blown up (soft), turned to phosphor
     green, with noise, scanlines, a rolling bar, jitter and now and then a torn line. The mouth opens with the voice's
     loudness (a stretch of the jaw, a darker mouth; transmissions.json "mouth" says where it is in each portrait).
   - The voice: the server's clip of that line (infra/rico/make.py, node.tauhud.com/rico/<key>.mp3, the same key as the
     crew's other lines), through a narrow radio band. Inbox contracts have one spoken message per kind
     (transmissions.json); the numbers stay on the screen. No clip, voice off, sound off or the practice node: the
     picture still talks, without sound, for as long as the text takes to read.
   - Esc, a click or the next command skips it; the line stays in the log as always. transmission off|on in the
     terminal; off gives the plain crew line back. Narrow screens get a small card at the top of the terminal. */
(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const T = s => (window.TauI18n ? TauI18n.t(s) : s);
  const F = (s, v) => T(s).replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m));
  const CLIPS = "https://node.tauhud.com/rico/", PREF = "tauhud-nomemo-tx";
  const REDUCED = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
  const fx = () => { if (REDUCED) return false; try { const s = JSON.parse(store.get("tauhud-nomemo") || "null"); return !s || s.fx !== false; } catch (e) { return true; } };
  let on = store.get(PREF) !== "off";

  /* what they say, and which clips the server has */
  let data = null, dataP = null;
  const lines = () => dataP || (dataP = fetch("transmissions.json", { cache: "no-cache" }).then(r => (r.ok ? r.json() : null)).catch(() => null).then(j => (data = j)));
  let have = null, haveAt = 0;
  async function clips() {
    if (have && Date.now() - haveAt < 120000) return have;
    haveAt = Date.now();
    try { const r = await fetch(CLIPS + "index.json", { cache: "no-cache" }); const j = r.ok ? await r.json() : null; have = new Set((j && j.clips) || []); } catch (e) { have = have || new Set(); }
    return have;
  }
  async function key(who, text) {   // the same key as make.py: sha1("who|text"), 16 hex
    const d = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(who + "|" + text));
    return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
  }

  /* sound: one context, the radio band, a burst of static at the start and the end */
  let ac = null;
  function audio() {
    if (!ac) { const C = window.AudioContext || window.webkitAudioContext; if (!C) return null; try { ac = new C(); } catch (e) { return null; } }
    if (ac.state === "suspended") ac.resume().catch(() => {});
    return ac;
  }
  function radio(c) {   // the voice as through a bad set: a narrow band and a little drive
    const hp = c.createBiquadFilter(); hp.type = "highpass"; hp.frequency.value = 320;
    const lp = c.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 3300;
    const sh = c.createWaveShaper(); const k = 2.2, n = 512, curve = new Float32Array(n);
    for (let i = 0; i < n; i++) { const x = i * 2 / n - 1; curve[i] = Math.tanh(k * x) / Math.tanh(k); }
    sh.curve = curve;
    const g = c.createGain(); g.gain.value = 0.95;
    hp.connect(lp); lp.connect(sh); sh.connect(g); g.connect(c.destination);
    return { input: hp, out: g };
  }
  function crackle(c, secs, vol) {
    if (!c) return;
    const len = Math.floor(c.sampleRate * secs), b = c.createBuffer(1, len, c.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (Math.random() < 0.06 ? 1 : 0.25) * (1 - i / len);
    const s = c.createBufferSource(); s.buffer = b;
    const f = c.createBiquadFilter(); f.type = "bandpass"; f.frequency.value = 1800; f.Q.value = 0.7;
    const g = c.createGain(); g.gain.value = vol;
    s.connect(f); f.connect(g); g.connect(c.destination); s.start();
  }
  function envelope(buf) {   // loudness every 1/50 s, 0..1
    const d = buf.getChannelData(0), step = Math.floor(buf.sampleRate / 50), out = [];
    let peak = 0;
    for (let i = 0; i < d.length; i += step) { let s = 0; for (let j = i; j < Math.min(d.length, i + step); j++) s += d[j] * d[j]; const v = Math.sqrt(s / step); out.push(v); if (v > peak) peak = v; }
    return out.map(v => Math.min(1, v / (peak * 0.7 || 1)));
  }

  /* the window */
  let cur = null;
  function build(d) {
    const pane = $("paneTerm"); if (!pane) return null;
    const box = document.createElement("div"); box.className = "txm"; box.setAttribute("role", "dialog"); box.setAttribute("aria-label", T("Transmission"));
    box.innerHTML = '<div class="txm-win"><div class="txm-top"><span class="txm-rec"></span><span class="txm-in"></span><span class="txm-sig"></span></div>'
      + '<div class="txm-body"><div class="txm-pic"><canvas width="336" height="336"></canvas><i class="txm-bar"></i></div>'
      + '<div class="txm-text"><b class="txm-from"></b><p class="txm-sub"></p><p class="txm-end"></p></div></div>'
      + '<div class="txm-foot"></div></div>';
    box.querySelector(".txm-in").textContent = F("incoming · {x}", { x: d.from || d.who });
    box.querySelector(".txm-from").textContent = d.from || d.who;
    box.querySelector(".txm-foot").textContent = T("Esc or click: skip · transmission off");
    box.addEventListener("click", () => stop(true));
    pane.append(box);
    const fit = () => {   // over the screen only (the command line and the chips stay free); the face as big as that allows
      const wrap = $("screenWrap");
      if (wrap && wrap.offsetParent === pane) { box.style.top = wrap.offsetTop + "px"; box.style.bottom = Math.max(0, pane.clientHeight - wrap.offsetTop - wrap.offsetHeight) + "px"; }
      if (matchMedia("(max-width: 760px)").matches) { box.style.removeProperty("--pic"); box.style.bottom = "auto"; return; }   // a card at the top
      const h = box.clientHeight - 28 - 74, side = box.clientWidth - 28 - 24 - 260;
      const cap = side < Math.min(h, 300);   // a narrow terminal (the cabin's screen): one big picture, the words over its foot like a film's
      box.classList.toggle("cap", cap);
      const text = box.querySelector(".txm-text"), pic = box.querySelector(".txm-pic"), body = box.querySelector(".txm-body");
      if (cap && text.parentNode !== pic) pic.append(text); else if (!cap && text.parentNode !== body) body.append(text);
      box.style.setProperty("--pic", Math.max(120, Math.min(480, h, cap ? box.clientWidth - 28 - 24 : side)) + "px");
    };
    fit(); box.fit = fit;
    requestAnimationFrame(() => box.classList.add("show"));
    return box;
  }

  async function play(d) {
    stop(false);
    const me = { d, box: build(d), alive: true, src: null, t0: 0, dur: 0, env: null, img: null, level: 0, glitch: 0, sig: 55 + Math.random() * 20 };
    if (!me.box) return;
    cur = me;
    const shown = d.shown || d.text || "";
    const sub = me.box.querySelector(".txm-sub");
    const c = d.voice && !d.sim ? audio() : null;
    if (c) crackle(c, 0.35, 0.18);
    me.glitch = 1;

    /* the picture */
    const img = new Image(); img.decoding = "async";
    img.onload = () => { me.img = img; };
    img.onerror = () => { if (d.mood !== "calm") { img.onerror = null; img.src = "art/crew/" + d.who + "-calm.webp"; } };
    img.src = "art/crew/" + d.who + "-" + (d.mood || "calm") + ".webp";
    loop(me, sub, shown);   // the picture runs while the voice is fetched

    /* the voice, if the server has it */
    let buf = null;
    try {
      const r = await (async () => {
        if (!c || !window.crypto || !crypto.subtle) return null;
        await lines();
        const k = d.job && d.job.k && data && data.kinds && data.kinds[d.job.k];
        const text = k && k.who === d.who ? k.say : d.text;
        const set = await clips(); if (!me.alive) return null;
        const id = await key(d.who, text); if (!set.has(id) || !me.alive) return null;
        const res = await fetch(CLIPS + id + ".mp3"); if (!res.ok || !me.alive) return null;
        const ab = await res.arrayBuffer();
        return await new Promise((ok, no) => { const p = c.decodeAudioData(ab, ok, no); if (p && p.then) p.then(ok, no); });
      })();
      buf = r;
    } catch (e) { buf = null; }
    if (!me.alive) return;
    await new Promise(r => setTimeout(r, 380));   // the line opens
    if (!me.alive) return;
    if (buf && c) {
      const s = c.createBufferSource(); s.buffer = buf; s.connect(radio(c).input);
      me.src = s; me.env = envelope(buf); me.dur = buf.duration; me.t0 = c.currentTime; me.clock = () => c.currentTime - me.t0;
      s.onended = () => { if (cur === me) finish(me); };
      s.start();
    } else {
      me.dur = Math.max(3.2, shown.length / 26); const t0 = performance.now(); me.clock = () => (performance.now() - t0) / 1000;
      me.fake = setTimeout(() => { if (cur === me) finish(me); }, me.dur * 1000);
    }
  }

  function finish(me) {
    if (!me.alive || me.ending) return;
    me.ending = true; me.speaking = false;
    const end = me.box.querySelector(".txm-end"); end.textContent = T("— transmission ends —");
    const sub = me.box.querySelector(".txm-sub"); sub.textContent = me.d.shown || me.d.text || ""; sub.scrollTop = sub.scrollHeight;
    if (me.d.voice && !me.d.sim && ac) crackle(ac, 0.25, 0.14);
    me.glitch = 1;
    me.close = setTimeout(() => { if (cur === me) stop(true); }, 1500);
  }

  function stop(fade) {
    const me = cur; if (!me) return;
    cur = null; me.alive = false;
    clearTimeout(me.fake); clearTimeout(me.close);
    try { if (me.src) { me.src.onended = null; me.src.stop(); } } catch (e) {}
    const b = me.box; if (!b) return;
    if (fade) { b.classList.remove("show"); b.classList.add("gone"); setTimeout(() => b.remove(), 320); } else b.remove();
    const inp = $("cmd"); if (inp && fade && matchMedia("(pointer: fine)").matches) inp.focus({ preventScroll: true });
  }

  /* the picture, drawn about 30 times a second */
  const low = document.createElement("canvas"); low.width = low.height = 132;
  const lx = low.getContext("2d", { willReadFrequently: true });
  function loop(me, sub, shown) {
    const cv = me.box.querySelector("canvas"), cx = cv.getContext("2d"), bar = me.box.querySelector(".txm-bar"), sig = me.box.querySelector(".txm-sig");
    const mouth = (data && data.mouth && data.mouth[me.d.who]) || [0.52, 0.4, 0.11, 0.06];
    const moving = fx();
    let last = 0, typed = -1, phase = Math.random() * 10;
    const frame = now => {
      if (!me.alive) return;
      requestAnimationFrame(frame);
      if (now - last < 33) return;
      last = now;
      const t = me.clock ? me.clock() : 0, p = me.dur ? Math.min(1, t / me.dur) : 0;
      /* how loud they are now */
      let lv = 0;
      if (me.env && !me.ending) lv = me.env[Math.min(me.env.length - 1, Math.max(0, Math.floor(t * 50)))] || 0;
      else if (me.clock && !me.ending) { phase += 0.33; lv = Math.max(0, Math.sin(phase * 2.1) * 0.5 + Math.sin(phase * 3.7) * 0.35 + 0.25); if ((t * 2.3) % 3 > 2.6) lv *= 0.15; }
      me.level += (lv - me.level) * 0.55;
      me.glitch = Math.max(0, me.glitch - 0.06);
      if (moving && Math.random() < 0.012) me.glitch = 0.7 + Math.random() * 0.3;
      /* the subtitle keeps pace with the voice */
      if (!me.ending) { const n = Math.round(shown.length * Math.min(1, p * 1.04)); if (n !== typed) { typed = n; sub.textContent = shown.slice(0, n); sub.classList.toggle("caret", n < shown.length); sub.scrollTop = sub.scrollHeight; } }
      /* the signal */
      if (moving && Math.random() < 0.1) { me.sig = Math.max(31, Math.min(88, me.sig + (Math.random() - 0.5) * 9 - me.glitch * 6)); }
      if (sig) sig.textContent = F("signal {n}%", { n: Math.round(me.sig) });
      draw(me, cx, cv, mouth, moving, now);
      if (bar) bar.style.transform = "translateY(" + (((now / 22) % 140) - 20) + "%)";
    };
    requestAnimationFrame(frame);
  }
  function draw(me, cx, cv, mouth, moving, now) {
    const W = low.width, H = low.height, g = me.glitch, lv = me.level;
    lx.fillStyle = "#000"; lx.fillRect(0, 0, W, H);
    if (me.img) {
      const z = 1.02 + lv * 0.012 + (moving ? Math.sin(now / 1900) * 0.006 : 0);
      const jx = moving ? (Math.random() - 0.5) * (0.6 + g * 5) : 0, jy = moving ? (Math.random() - 0.5) * (0.4 + g * 2) : 0;
      const dw = W * z, dh = H * z, ox = (W - dw) / 2 + jx, oy = (H - dh) / 2 + jy;
      lx.drawImage(me.img, ox, oy, dw, dh);
      /* the mouth: the jaw drops a little and the mouth darkens with the voice */
      if (lv > 0.04) {
        const iw = me.img.naturalWidth, ih = me.img.naturalHeight;
        const [mx, my, mw, mh] = mouth;
        const sx = (mx - mw / 2) * iw, sy = (my - mh * 0.15) * ih, sw = mw * iw, sh = mh * 1.15 * ih;
        const dx = ox + (mx - mw / 2) * dw, dy = oy + (my - mh * 0.15) * dh, ddw = mw * dw, ddh = mh * 1.15 * dh * (1 + lv * 0.32);
        lx.drawImage(me.img, sx, sy, sw, sh, dx, dy, ddw, ddh);
        lx.fillStyle = "rgba(0,0,0," + (0.25 + lv * 0.45).toFixed(3) + ")";
        lx.beginPath(); lx.ellipse(ox + mx * dw, oy + (my + mh * 0.18) * dh, mw * dw * 0.24, Math.max(0.3, mh * dh * 0.32 * lv), 0, 0, Math.PI * 2); lx.fill();
      }
    }
    /* phosphor green, noise, scanlines, torn lines */
    const im = lx.getImageData(0, 0, W, H), px = im.data, nz = 14 + g * 46;
    const tear = moving && (g > 0.35 || Math.random() < 0.03) ? { y: Math.floor(Math.random() * H), h: 2 + Math.floor(Math.random() * (4 + g * 18)), dx: Math.round((Math.random() - 0.5) * (6 + g * 26)) } : null;
    const row = new Uint8ClampedArray(W * 4);
    for (let y = 0; y < H; y++) {
      if (tear && y >= tear.y && y < tear.y + tear.h) { row.set(px.subarray(y * W * 4, (y + 1) * W * 4)); for (let x = 0; x < W; x++) { const s = Math.min(W - 1, Math.max(0, x - tear.dx)); px[(y * W + x) * 4] = row[s * 4]; px[(y * W + x) * 4 + 1] = row[s * 4 + 1]; px[(y * W + x) * 4 + 2] = row[s * 4 + 2]; } }
      const scan = y % 2 ? 0.74 : 1;
      for (let x = 0; x < W; x++) {
        const i = (y * W + x) * 4;
        let l = px[i] * 0.3 + px[i + 1] * 0.59 + px[i + 2] * 0.11;
        l = Math.max(0, Math.min(255, (l - 18) * 1.25 + (Math.random() - 0.5) * nz)) * scan;
        px[i] = l * 0.22; px[i + 1] = Math.min(255, l * 1.02 + 6); px[i + 2] = l * 0.5; px[i + 3] = 255;
      }
    }
    lx.putImageData(im, 0, 0);
    /* blown up, soft; a little sharper while they speak, blurred when the line breaks */
    cx.imageSmoothingEnabled = true;
    const blur = moving ? 0.9 + g * 2.6 + (Math.random() < 0.02 ? 1.4 : 0) : 0.5;
    if ("filter" in cx) cx.filter = "blur(" + blur.toFixed(2) + "px) brightness(" + (1.05 + lv * 0.12 - g * 0.15).toFixed(3) + ")";
    cx.drawImage(low, 0, 0, cv.width, cv.height);
    if ("filter" in cx) cx.filter = "none";
    if (moving && g > 0.5) { cx.fillStyle = "rgba(185,255,214," + (g * 0.08).toFixed(3) + ")"; cx.fillRect(0, Math.random() * cv.height, cv.width, 2 + Math.random() * 6); }
  }

  /* the game hands a brief over */
  document.addEventListener("nomemo:transmission", e => {
    const d = e.detail || {};
    if (!on || !d.who) return;
    e.preventDefault();
    lines();
    play(d);
  });
  addEventListener("resize", () => { if (cur && cur.box && cur.box.fit) cur.box.fit(); });
  /* skip: Esc, or the next command */
  addEventListener("keydown", e => { if (cur && e.key === "Escape") { e.preventDefault(); stop(true); } });
  document.addEventListener("submit", e => {
    if (!e.target || e.target.id !== "cmdForm") return;
    const input = $("cmd"), raw = (input && input.value || "").trim(), v = raw.toLowerCase().replace(/\s+/g, " ");
    if (cur) stop(true);
    let want = null;
    if (v === "transmission on" || v === "transmissions on") want = true;
    else if (v === "transmission off" || v === "transmissions off") want = false;
    else if (v === "transmission" || v === "transmissions") want = !on;
    else return;
    e.preventDefault(); e.stopImmediatePropagation(); input.value = "";
    on = want; store.set(PREF, on ? "on" : "off");
    const s = $("screen"); if (!s) return;
    const a = document.createElement("p"); a.className = "you"; a.textContent = raw;
    const b = document.createElement("p"); b.className = "sys";
    b.textContent = on ? T("Transmissions on: a contract's sender appears and reads it out. transmission off for the plain line.") : T("Transmissions off: contracts come as plain lines. transmission on brings the crew back on screen.");
    s.append(a, b); const w = $("screenWrap"); if (w) w.scrollTop = w.scrollHeight;
  }, true);
  window.NoMemoTransmission = { play: d => play(d), stop: () => stop(true), get on() { return on; } };
})();

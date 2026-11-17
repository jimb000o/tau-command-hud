/* The ship's bell: what you see, hear and feel when it rings. game.js sends the transaction; this file plays it.

   - The bell hangs in the cabin painting (scene.js cuts bell and rope out of it, cabin.json bell). Clicking it, the bell
     button in the top bar, or the command `bell` all ring the same bell.
   - game.js tells each step with   document.dispatchEvent(new CustomEvent("nomemo:bell-fx", { detail: { stage } }))
       pull    the lanyard is pulled: one strike, at once (before the network, so it never feels slow)
       node    the node took the transaction: a soft shimmer
       sealed  in a block: the ship's double strike, rings of light, the lantern flares
       refused the chain said no: a dull clank
       far     another player's ring landed: the same bell, quieter and further away
       idle    rung again too soon: the bell swings and sounds, nothing is sent
   - A click asks game.js to ring with   document.dispatchEvent(new CustomEvent("nomemo:bell"))
   - Sound is drawn with Web Audio (struck-bell partials, a small wooden room), no files; it follows the game's sound
     switch (localStorage tauhud-nomemo .snd). prefers-reduced-motion: no swinging, no rings, a glow only. A phone buzzes. */
(() => {
  const root = document.documentElement, $ = id => document.getElementById(id);
  const REDUCED = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const soundOn = () => { try { const s = JSON.parse(localStorage.getItem("tauhud-nomemo") || "null"); return !s || s.snd !== false; } catch (e) { return true; } };

  /* ---------- sound: a small brass ship's bell in a wooden cabin ---------- */
  let ac = null, out = null, room = null;
  function audio() {
    if (ac) { if (ac.state === "suspended") ac.resume().catch(() => {}); return ac; }
    const C = window.AudioContext || window.webkitAudioContext; if (!C) return null;
    ac = new C(); out = ac.createDynamicsCompressor(); out.threshold.value = -14; out.ratio.value = 3; out.connect(ac.destination);
    room = ac.createConvolver(); const len = ac.sampleRate * 2.6, ir = ac.createBuffer(2, len, ac.sampleRate);
    for (let c = 0; c < 2; c++) { const d = ir.getChannelData(c); for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 3.2) * (i < 900 ? i / 900 : 1); }
    room.buffer = ir; const wet = ac.createGain(); wet.gain.value = .32; room.connect(wet); wet.connect(out);
    return ac;
  }
  /* a struck bell: the hum, the prime, the minor third, the fifth, the nominal and its upper partials, each with its own
     decay (low ones ring longest), each a hair detuned against a twin so the tone beats and shimmers like brass */
  const PARTIALS = [[.5, .30, 3.6], [1, .55, 2.6], [1.183, .30, 2.0], [1.506, .18, 1.6], [2, .42, 1.9], [2.51, .14, 1.0], [2.66, .16, .9], [3.01, .10, .7], [4.17, .07, .45], [5.43, .05, .3]];
  function strike(t, f0, gain, far) {
    const a = audio(); if (!a) return;
    const bus = a.createGain(); bus.gain.value = gain;
    const tone = far ? a.createBiquadFilter() : null;
    if (tone) { tone.type = "lowpass"; tone.frequency.value = 1700; bus.connect(tone); tone.connect(room); tone.connect(out); } else { bus.connect(out); bus.connect(room); }
    const pan = a.createStereoPanner ? a.createStereoPanner() : null; if (pan) { pan.pan.value = far ? -.35 : .38; pan.connect(bus); }
    const into = pan || bus;
    for (const [r, g, d] of PARTIALS) for (const det of [-0.9, 0.9]) {
      const o = a.createOscillator(), v = a.createGain();
      o.type = "sine"; o.frequency.value = f0 * r + det * r * .6;
      v.gain.setValueAtTime(0, t); v.gain.linearRampToValueAtTime(g / 2, t + .003); v.gain.exponentialRampToValueAtTime(.0005, t + d * (far ? 1.3 : 1));
      o.connect(v); v.connect(into); o.start(t); o.stop(t + d * 1.4 + .1);
    }
    /* the clapper's knock: a short bright click */
    const n = a.createBufferSource(), nb = a.createBuffer(1, a.sampleRate * .03, a.sampleRate), d = nb.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / d.length, 4);
    const bp = a.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 3800; bp.Q.value = 1.2;
    const ng = a.createGain(); ng.gain.value = far ? .08 : .5; n.buffer = nb; n.connect(bp); bp.connect(ng); ng.connect(into); n.start(t);
  }
  function clank(t) {   // the chain said no: a muffled knock, the bell held by a hand
    const a = audio(); if (!a) return;
    const o = a.createOscillator(), v = a.createGain(), lp = a.createBiquadFilter();
    o.type = "triangle"; o.frequency.setValueAtTime(330, t); o.frequency.exponentialRampToValueAtTime(180, t + .25);
    lp.type = "lowpass"; lp.frequency.value = 700; v.gain.setValueAtTime(.5, t); v.gain.exponentialRampToValueAtTime(.001, t + .35);
    o.connect(lp); lp.connect(v); v.connect(out); o.start(t); o.stop(t + .4);
  }
  function shimmer(t) {   // the node took it: a quiet glint of the same bell, high up
    const a = audio(); if (!a) return;
    for (const [i, r] of [2, 3.01, 4.17].entries()) {
      const o = a.createOscillator(), v = a.createGain(); o.frequency.value = 1046 * r / 2; o.type = "sine";
      v.gain.setValueAtTime(0, t + i * .06); v.gain.linearRampToValueAtTime(.05, t + i * .06 + .01); v.gain.exponentialRampToValueAtTime(.0005, t + i * .06 + .7);
      o.connect(v); v.connect(room); v.connect(out); o.start(t + i * .06); o.stop(t + i * .06 + .8);
    }
  }
  function sound(stage) {
    if (!soundOn()) return; const a = audio(); if (!a) return; const t = a.currentTime + .01;
    if (stage === "pull" || stage === "idle") strike(t, 1046, .5);
    else if (stage === "node") shimmer(t);
    else if (stage === "sealed") { strike(t, 1046, .55); strike(t + .42, 1046, .5); }   // the ship's way: strokes in pairs
    else if (stage === "refused") clank(t);
    else if (stage === "far") strike(t, 1046, .16, true);
  }

  /* ---------- sight: the bell swings, rings of light leave it ---------- */
  function retrigger(cls, ms) { root.classList.remove(cls); void root.offsetWidth; root.classList.add(cls); clearTimeout(retrigger[cls]); retrigger[cls] = setTimeout(() => root.classList.remove(cls), ms); }
  function visibleBell() {
    if (!root.classList.contains("scene")) return null;
    const b = document.querySelector(".cab-bell"); if (!b) return null;
    const r = b.getBoundingClientRect();
    return r.width > 8 && r.right > 0 && r.left < innerWidth && r.bottom > 0 && r.top < innerHeight - 20 ? r : null;
  }
  function rings(color, n) {
    if (REDUCED) return;
    const r = visibleBell(), btn = $("bellBtn"), at = r || (btn && btn.offsetParent ? btn.getBoundingClientRect() : null); if (!at) return;
    const x = at.left + at.width / 2, y = r ? at.top + at.height * .82 : at.top + at.height / 2, size = r ? Math.max(at.width * 1.2, 90) : 46;
    for (let i = 0; i < n; i++) {
      const o = document.createElement("i"); o.className = "bell-ring " + color; o.setAttribute("aria-hidden", "true");
      Object.assign(o.style, { left: x + "px", top: y + "px", width: size + "px", height: size + "px", animationDelay: i * .16 + "s" });
      document.body.append(o); setTimeout(() => o.remove(), 1700 + i * 160);
    }
  }
  function fx(stage) {
    sound(stage);
    if (stage === "pull" || stage === "idle") { retrigger("bell-strike", 2600); rings("gold", 2); if (navigator.vibrate) try { navigator.vibrate(14); } catch (e) { } }
    else if (stage === "node") retrigger("bell-node", 900);
    else if (stage === "sealed") { retrigger("bell-strike", 2600); retrigger("bell-sealed", 2200); rings("gold", 2); setTimeout(() => rings("green", 3), 420); if (navigator.vibrate) try { navigator.vibrate([14, 380, 14]); } catch (e) { } }
    else if (stage === "refused") retrigger("bell-dud", 700);
    else if (stage === "far") { retrigger("bell-far", 2200); rings("far", 1); }
  }
  document.addEventListener("nomemo:bell-fx", e => fx(e.detail && e.detail.stage));

  /* ---------- the hotspot over the painted bell (the cabin itself lets clicks through to nothing) ---------- */
  let hot = null;
  function place() {
    const r = visibleBell();
    if (!r) { if (hot) hot.hidden = true; return; }
    if (!hot) {
      hot = document.createElement("button"); hot.type = "button"; hot.id = "bellHot"; hot.title = (window.TauI18n ? TauI18n.t("ring the ship’s bell: a real transaction") : "ring the ship’s bell: a real transaction");
      hot.setAttribute("aria-label", hot.title); hot.addEventListener("click", () => { audio(); document.dispatchEvent(new CustomEvent("nomemo:bell")); });
      document.body.append(hot);
    }
    hot.hidden = false;
    Object.assign(hot.style, { left: r.left + "px", top: r.top + "px", width: r.width + "px", height: r.height * 1.9 + "px" });
  }
  function start() {
    const b = $("bellBtn"); if (b) b.addEventListener("click", () => { audio(); document.dispatchEvent(new CustomEvent("nomemo:bell")); });
    addEventListener("resize", () => setTimeout(place, 200));
    new MutationObserver(() => setTimeout(place, 50)).observe(root, { attributes: true, attributeFilter: ["class"] });
    setInterval(place, 1500);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();

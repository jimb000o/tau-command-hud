/* The room, 1999: what you hear. Used by assets/room.js through window.TauRoomSound.

   - The room: rain on the glass, the room's hum, the neon sign, cars on the wet street (loops), and now and then a
     foghorn on the bay or the radiator. Files in assets/room/sfx/ (drawn by infra/room/synth.py); the ElevenLabs
     versions made on the server by infra/room/sfx.py (node.tauhud.com/rico/room-sfx/) play instead where they exist.
   - The music: an original score played live here, nothing recorded. Electric piano, upright bass, brushes and a
     little vinyl dust, 72 beats a minute, content and warm: the feeling of a late shift that is going well. It follows
     the room: "night" while you sit, "call" when someone is on the line or a rule change rings, "awake" when you read
     the chain right, then back to night. Every key you type plays a soft note in the current chord; every block
     rings a small chime in it. With the lamp off the music sounds further away.
   - Nothing plays before a click or key (browser rule) or with sound off; music has its own switch.
   window.TauRoomSound = { start, stop, ctx, bus, play, mood, key, block, good, bad, lamp, set } */
(() => {
  const LOCAL = new URL("room/sfx/", (document.querySelector('script[src*="assets/room-sound.js"]') || { src: location.href }).src.replace(/room-sound\.js.*$/, "")).href;
  const SERVER = "https://node.tauhud.com/rico/room-sfx/";
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let ctx = null, master = null, bed = null, sfx = null, mus = null, muf = null, verb = null, running = false, musicOn = true;
  let meta = null, server = [], metaP = null;
  const buf = {}, wait = {}, layers = {}, timers = [];

  function ac() {
    try {
      if (!ctx) {
        ctx = new (window.AudioContext || window.webkitAudioContext)();
        const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -16; comp.ratio.value = 3;
        master = ctx.createGain(); master.gain.value = 0.38; master.connect(comp).connect(ctx.destination);   // a room in the background, never loud
        bed = ctx.createGain(); bed.gain.value = 0.8; bed.connect(master);
        sfx = ctx.createGain(); sfx.gain.value = 0.9; sfx.connect(master);
        /* the music: through a low-pass (the lamp) and a soft room */
        muf = ctx.createBiquadFilter(); muf.type = "lowpass"; muf.frequency.value = 9000; muf.Q.value = 0.4;
        mus = ctx.createGain(); mus.gain.value = 0; mus.connect(muf); muf.connect(master);
        verb = ctx.createConvolver(); verb.buffer = impulse(2.4); const vg = ctx.createGain(); vg.gain.value = 0.32; mus.connect(vg).connect(verb).connect(muf);
      }
      if (ctx.state === "suspended") ctx.resume();
      return ctx;
    } catch (e) { return null; }
  }
  function impulse(sec) {
    const n = Math.floor(ctx.sampleRate * sec), b = ctx.createBuffer(2, n, ctx.sampleRate);
    for (let c = 0; c < 2; c++) { const d = b.getChannelData(c); for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, 2.6); }
    return b;
  }

  /* ---------------- samples ---------------- */
  function info() {
    if (metaP) return metaP;
    metaP = (async () => {
      try { const j = await (await fetch(LOCAL + "list.json")).json(); meta = {}; for (const s of j.sounds) meta[s.name] = s; } catch (e) { meta = {}; }
      try { const r = await fetch(SERVER + "index.json", { cache: "no-cache" }); if (r.ok) server = (await r.json()).sounds || []; } catch (e) {}
    })();
    return metaP;
  }
  const decode = ab => new Promise((ok, no) => { const p = ctx.decodeAudioData(ab, ok, no); if (p && p.then) p.then(ok, no); });
  function load(name) {
    if (buf[name]) return Promise.resolve(buf[name]);
    if (wait[name]) return wait[name];
    return (wait[name] = (async () => {
      await info();
      for (const u of (server.includes(name) ? [SERVER, LOCAL] : [LOCAL])) {
        try { const r = await fetch(u + name + ".mp3"); if (!r.ok) continue; return (buf[name] = await decode(await r.arrayBuffer())); } catch (e) {}
      }
      return null;
    })());
  }
  const gainOf = n => (meta && meta[n] && meta[n].gain) || 0.4;
  function play(name, o = {}) {
    if (!running) return false;
    const b = buf[name]; if (!b) { load(name).then(x => x && o.late && play(name, Object.assign({}, o, { late: false }))); return false; }
    const s = ctx.createBufferSource(), g = ctx.createGain(); s.buffer = b; if (o.rate) s.playbackRate.value = o.rate;
    g.gain.value = gainOf(name) * (o.gain == null ? 1 : o.gain);
    let out = g; if (o.pan && ctx.createStereoPanner) { const p = ctx.createStereoPanner(); p.pan.value = o.pan; g.connect(p); out = p; }
    s.connect(g); out.connect(o.bus || sfx); s.start(ctx.currentTime + (o.delay || 0));
    return true;
  }
  function layer(name, pan) {
    const b = buf[name]; if (!b || layers[name]) return;
    const d = b.getChannelData(0); let a = 0, z = d.length - 1; while (a < d.length && Math.abs(d[a]) < 2e-4) a++; while (z > a && Math.abs(d[z]) < 2e-4) z--;
    const s = ctx.createBufferSource(), g = ctx.createGain(); s.buffer = b; s.loop = true; s.loopStart = a / b.sampleRate; s.loopEnd = (z + 1) / b.sampleRate;
    g.gain.setValueAtTime(0.0001, ctx.currentTime); g.gain.exponentialRampToValueAtTime(gainOf(name), ctx.currentTime + 3);
    let out = g; if (pan && ctx.createStereoPanner) { const p = ctx.createStereoPanner(); p.pan.value = pan; g.connect(p); out = p; }
    s.connect(g); out.connect(bed); s.start(ctx.currentTime, s.loopStart); layers[name] = { s, g };
  }
  function every(fn, lo, hi) { const go = () => { timers.push(setTimeout(() => { if (running && !document.hidden) fn(); if (running) go(); }, (lo + Math.random() * (hi - lo)) * 1000)); }; go(); }

  /* ---------------- the score ---------------- */
  const mtof = m => 440 * Math.pow(2, (m - 69) / 12);
  /* chords: [bass root, e-piano voicing], one bar each; the scale for typed notes */
  const C = {
    Dmaj9: [38, [54, 57, 61, 64]], Bm9: [35, [50, 54, 57, 61]], Gmaj9: [43, [54, 57, 59, 62]], A13s: [33, [55, 59, 62, 66]],
    Em9: [40, [50, 54, 55, 59]], A13: [45, [55, 59, 61, 66]], Fsm7: [42, [52, 57, 61, 64]], Gm6: [43, [52, 55, 58, 62]],
    Gmaj7s11: [43, [54, 59, 61, 66]], Fs7b9: [42, [52, 55, 58, 64]], Bm: [47, [50, 54, 59, 62]],
  };
  const MOODS = {
    night: { prog: ["Dmaj9", "Bm9", "Gmaj9", "A13s", "Dmaj9", "Bm9", "Em9", "A13", "Fsm7", "Bm9", "Gmaj9", "Gm6", "Dmaj9", "Fsm7", "Em9", "A13s"], drums: 1, bass: "walk", lead: 0.55 },
    call: { prog: ["Bm9", "Gmaj7s11", "Em9", "Fs7b9"], drums: 0, bass: "hold", lead: 0.25, pad: 1 },
    ring: { prog: ["Bm9", "Gmaj7s11", "Em9", "Fs7b9"], drums: 0.5, bass: "pulse", lead: 0, pad: 1 },
    awake: { prog: ["Gmaj9", "A13", "Dmaj9", "Dmaj9"], drums: 0, bass: "hold", lead: 0.9, pad: 1, then: "night" },
  };
  const SCALE = [62, 64, 66, 69, 71, 74, 76, 78, 81, 83];   // D major pentatonic, over two octaves
  const BEAT = 60 / 72, SW = 0.62;   // a lazy swing: the off-beat eighth falls late
  let mood = "night", nextMood = null, bar = 0, nextT = 0, tick = null, motif = null, typed = 0, lampOff = false;

  function note(f, t, dur, vel, kind) {
    const o = ctx.createOscillator(), g = ctx.createGain(); o.frequency.value = f;
    if (kind === "ep") {   // electric piano: a sine bent by a sine (FM), a bright tine on top, a slow tremolo
      const m = ctx.createOscillator(), mg = ctx.createGain(); m.frequency.value = f; mg.gain.setValueAtTime(f * 1.6 * vel, t); mg.gain.exponentialRampToValueAtTime(f * 0.15, t + 0.9);
      m.connect(mg).connect(o.frequency); m.start(t); m.stop(t + dur + 1.6);
      const tn = ctx.createOscillator(), tg = ctx.createGain(); tn.frequency.value = f * 7.02; tg.gain.setValueAtTime(0.05 * vel, t); tg.gain.exponentialRampToValueAtTime(0.0001, t + 0.12);
      tn.connect(tg).connect(mus); tn.start(t); tn.stop(t + 0.15);
    }
    if (kind === "bass") o.type = "triangle";
    if (kind === "pad") { o.type = "sawtooth"; o.detune.value = (Math.random() - 0.5) * 14; }
    const peak = vel * (kind === "bass" ? 0.32 : kind === "pad" ? 0.035 : kind === "chime" ? 0.06 : 0.09);
    const a = kind === "pad" ? 1.2 : 0.006, rel = kind === "pad" ? 1.6 : kind === "bass" ? 0.25 : 1.3;
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(peak, t + a);
    if (kind === "pad") g.gain.setValueAtTime(peak, t + dur); else g.gain.exponentialRampToValueAtTime(peak * (kind === "bass" ? 0.35 : 0.3), t + Math.min(dur, 1.4));
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur + rel);
    let out = g;
    if (kind === "pad" || kind === "bass") { const lp = ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = kind === "pad" ? 900 : 700; g.connect(lp); out = lp; }
    o.connect(g); out.connect(mus); o.start(t); o.stop(t + dur + rel + 0.05);
  }
  function noiseHit(t, dur, f, q, vel) {
    const n = Math.floor(ctx.sampleRate * dur), b = ctx.createBuffer(1, n, ctx.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, 2);
    const s = ctx.createBufferSource(), bp = ctx.createBiquadFilter(), g = ctx.createGain(); s.buffer = b; bp.type = "bandpass"; bp.frequency.value = f; bp.Q.value = q; g.gain.value = vel;
    s.connect(bp).connect(g).connect(mus); s.start(t);
  }
  function kick(t, vel) { const o = ctx.createOscillator(), g = ctx.createGain(); o.frequency.setValueAtTime(90, t); o.frequency.exponentialRampToValueAtTime(42, t + 0.12); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.35 * vel, t + 0.005); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.3); o.connect(g).connect(mus); o.start(t); o.stop(t + 0.32); }
  const at8 = (t0, i) => t0 + Math.floor(i / 2) * BEAT + (i % 2 ? BEAT * SW : 0);   // eighth i of the bar, swung

  function newMotif() {   // four bars of melody, made once per lap and repeated with a small change: it sounds written
    const m = []; let p = 3 + Math.floor(Math.random() * 3);
    for (let b = 0; b < 4; b++) { const bm = []; for (let i = 0; i < 8; i++) if (Math.random() < (i % 2 ? 0.18 : 0.38)) { p = Math.max(0, Math.min(SCALE.length - 1, p + [-2, -1, -1, 1, 1, 2][Math.random() * 6 | 0])); bm.push([i, SCALE[p] + 12, Math.random() < 0.3 ? 3 : 1]); } m.push(bm); }
    return m;
  }
  function playBar(t0) {
    const M = MOODS[mood], name = M.prog[bar % M.prog.length], [root, voic] = C[name];
    if (bar % M.prog.length === 0) motif = newMotif();
    /* e-piano: the chord on one and a push on the "and" of two or three */
    const comp = [[0, 1.0, 3], [3, 0.7, 1.5], [5, 0.75, 2.5]][Math.random() * 3 | 0];
    voic.forEach((m, k) => note(mtof(m), t0 + k * 0.012, BEAT * 1.9, 0.55, "ep"));
    voic.forEach((m, k) => note(mtof(m), at8(t0, comp[0] + 2) + k * 0.01, BEAT * comp[2] * 0.5, 0.42 * comp[1], "ep"));
    /* bass */
    if (M.bass === "walk") { const steps = [0, 7, 12, 10]; steps.forEach((s, i) => note(mtof(root + (i === 3 && Math.random() < 0.5 ? 11 : s)), t0 + i * BEAT, BEAT * 0.9, i ? 0.75 : 1, "bass")); }
    else if (M.bass === "pulse") for (let i = 0; i < 8; i++) note(mtof(root), at8(t0, i), BEAT * 0.4, i % 2 ? 0.5 : 0.8, "bass");
    else note(mtof(root), t0, BEAT * 3.8, 0.9, "bass");
    /* pad */
    if (M.pad) voic.forEach(m => note(mtof(m), t0, BEAT * 4, 0.9, "pad"));
    /* brushes: a swish on every beat, a tap on two and four, a soft kick on one */
    if (M.drums) for (let i = 0; i < 8; i++) {
      const t = at8(t0, i);
      if (i % 2 === 0) noiseHit(t, 0.22, 5200, 0.6, 0.05 * M.drums);
      if (i === 2 || i === 6) noiseHit(t, 0.12, 2400, 1.1, 0.14 * M.drums);
      if (i === 0 || (i === 5 && Math.random() < 0.4)) kick(t, 0.7 * M.drums);
      if (typed > 0 && i % 2) noiseHit(t, 0.05, 8000, 1, 0.05);   // while you type, a hi-hat joins
    }
    /* the melody, now and then */
    if (M.lead && motif && Math.random() < M.lead + 0.3) for (const [i, m, len] of motif[bar % 4]) note(mtof(m + (bar % 8 >= 4 && i === 0 ? 2 : 0)), at8(t0, i), BEAT * 0.5 * len, 0.5, "ep");
    typed = Math.max(0, typed - 1);
    bar++;
    if (nextMood && bar % 2 === 0) { mood = nextMood; nextMood = null; bar = 0; }
    else if (M.then && bar >= M.prog.length) { mood = M.then; bar = 0; }
  }
  function crackle() {   // the record's dust, under everything
    const n = ctx.sampleRate * 4, b = ctx.createBuffer(1, n, ctx.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = Math.random() < 0.0006 ? (Math.random() * 2 - 1) : (Math.random() * 2 - 1) * 0.004;
    const s = ctx.createBufferSource(), hp = ctx.createBiquadFilter(), g = ctx.createGain(); s.buffer = b; s.loop = true; hp.type = "highpass"; hp.frequency.value = 1200; g.gain.value = 0.18;
    s.connect(hp).connect(g).connect(mus); s.start(); return s;
  }
  let dust = null;
  function music(onOff) {
    if (!ctx) return;
    const t = ctx.currentTime; mus.gain.cancelScheduledValues(t); mus.gain.setValueAtTime(mus.gain.value, t);
    if (onOff) {
      mus.gain.linearRampToValueAtTime(0.5, t + 4);
      if (!tick) { nextT = ctx.currentTime + 0.3; bar = 0; tick = setInterval(() => { while (nextT < ctx.currentTime + 0.6) { playBar(nextT); nextT += BEAT * 4; } }, 120); }
      if (!dust) dust = crackle();
    } else {
      mus.gain.linearRampToValueAtTime(0, t + 1.2);
      setTimeout(() => { if (!musicOn || !running) { clearInterval(tick); tick = null; if (dust) { try { dust.stop(); } catch (e) {} dust = null; } } }, 1400);
    }
  }

  /* ---------------- what the room calls ---------------- */
  async function start() {
    if (running) return; if (!ac()) return; running = true;
    await info();
    const amb = ["amb-rain", "amb-room", "amb-neon", "amb-street"];
    Promise.all(amb.map(load)).then(() => { if (!running) return; layer("amb-rain", -0.35); layer("amb-room"); layer("amb-neon", -0.5); layer("amb-street", -0.2); });
    for (const n of Object.keys(meta || {})) if (!n.startsWith("amb-")) load(n);
    every(() => play("foghorn", { bus: bed, pan: -0.6, gain: 0.7 + Math.random() * 0.3 }), 90, 260);
    every(() => play("radiator-" + (1 + (Math.random() * 2 | 0)), { bus: bed, pan: -0.8, rate: 0.9 + Math.random() * 0.2 }), 35, 110);
    if (musicOn) music(true);
  }
  function stop() {
    running = false; timers.splice(0).forEach(clearTimeout);
    for (const k of Object.keys(layers)) { const l = layers[k]; delete layers[k]; try { l.g.gain.setTargetAtTime(0.0001, ctx.currentTime, 0.4); l.s.stop(ctx.currentTime + 1.5); } catch (e) {} }
    music(false);
  }
  function key(k) {
    if (!running) return;
    play("key-" + (k === "Enter" || k === " " ? 4 : 1 + (Math.random() * 3 | 0)), { rate: 0.95 + Math.random() * 0.1, gain: 0.8 });
    if (!musicOn || REDUCED) return;
    typed = 2;
    if (k === "Enter") { const [, v] = C[MOODS[mood].prog[(bar + MOODS[mood].prog.length - 1) % MOODS[mood].prog.length]]; v.forEach((m, i) => note(mtof(m + 12), ctx.currentTime + i * 0.04, 0.6, 0.35, "ep")); return; }
    if (k.length === 1) { const i = (key.n = ((key.n || 0) + (Math.random() < 0.7 ? 1 : -1) + SCALE.length) % SCALE.length); note(mtof(SCALE[i]), ctx.currentTime, 0.25, 0.22, "ep"); }
  }
  function chime(ms) { if (!running || !musicOn) return; ms.forEach((m, i) => note(mtof(m), ctx.currentTime + i * 0.11, 1.2, 0.8, "chime")); }
  window.TauRoomSound = {
    start, stop, key, play: (n, o) => play(n, Object.assign({ late: true }, o)),
    ctx: () => ac(), bus: () => (ac(), sfx),
    mood(m) { if (MOODS[m] && m !== mood) nextMood = m; },
    block() { const [, v] = C[MOODS[mood].prog[Math.max(0, bar - 1) % MOODS[mood].prog.length]]; chime(v.slice(-3).map(x => x + 24)); },
    good() { chime([74, 78, 81, 86]); }, bad() { chime([62, 61]); },
    lamp(off) { lampOff = off; if (muf) muf.frequency.setTargetAtTime(off ? 1400 : 9000, ctx.currentTime, 0.4); },
    set(o) { if ("music" in o) { musicOn = !!o.music; if (running) music(musicOn); } },
    get running() { return running; },
  };
  document.addEventListener("visibilitychange", () => { if (!ctx) return; if (document.hidden) ctx.suspend(); else if (running) ctx.resume(); });
})();

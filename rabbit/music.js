/* The island's sound: an original calypso for steel pan, marimba, bass and hand drums, played live in the
   visitor's browser (no recordings), plus the sea, gulls and small sounds for the game. On by default;
   browsers only allow sound after a first tap, so the page shows "♪ Tap for sound" until then.
   window.COVE_SOUND = { start, on, set({ music, radio, tense, place }), sfx(name), speak(clips), hush(), toggle() }
   Each place on the island plays the tune in its own arrangement (STYLES). */
(() => {
  const BPM = 104, STEP = 60 / BPM / 4, SWING = 0.16;   // sixteenth notes, the off sixteenths a little late
  /* the tune: 16 bars, A then B; each note is [sixteenth in the bar, midi note, length in sixteenths] */
  const A = [
    [[0, 72, 2], [2, 69, 1], [3, 72, 2], [6, 74, 2], [8, 72, 3], [11, 69, 1], [12, 65, 4]],
    [[0, 70, 2], [2, 74, 1], [3, 77, 2], [6, 74, 2], [8, 77, 3], [11, 74, 1], [12, 70, 4]],
    [[0, 76, 2], [2, 74, 1], [3, 72, 2], [6, 70, 2], [8, 67, 3], [11, 70, 1], [12, 72, 4]],
    [[0, 69, 3], [3, 72, 3], [6, 77, 6], [12, 76, 2], [14, 74, 2]],
    [[0, 72, 2], [2, 69, 1], [3, 72, 2], [6, 74, 2], [8, 77, 3], [11, 79, 1], [12, 81, 4]],
    [[0, 79, 2], [2, 77, 1], [3, 74, 2], [6, 77, 2], [8, 74, 3], [11, 72, 1], [12, 69, 4]],
    [[0, 70, 2], [2, 74, 2], [4, 79, 2], [6, 77, 2], [8, 76, 2], [10, 74, 2], [12, 72, 2], [14, 70, 2]],
    [[0, 69, 4], [4, 65, 2], [6, 69, 2], [8, 72, 8]],
  ];
  const B = [
    [[2, 74, 2], [4, 74, 2], [6, 77, 4], [12, 74, 2], [14, 72, 2]],
    [[0, 69, 6], [8, 72, 2], [10, 69, 2], [12, 65, 4]],
    [[2, 70, 2], [4, 70, 2], [6, 74, 4], [12, 72, 2], [14, 70, 2]],
    [[0, 69, 8], [10, 72, 2], [12, 74, 2], [14, 76, 2]],
    [[0, 77, 3], [3, 74, 3], [6, 69, 2], [8, 74, 3], [11, 77, 1], [12, 81, 4]],
    [[0, 79, 3], [3, 74, 3], [6, 70, 2], [8, 74, 4], [12, 79, 4]],
    [[0, 76, 2], [2, 79, 2], [4, 76, 2], [6, 72, 2], [8, 70, 2], [10, 67, 2], [12, 64, 4]],
    [[0, 65, 4], [4, 69, 2], [6, 72, 2], [8, 77, 8]],
  ];
  const TUNE = [...A, ...B];
  /* chords and bass roots per bar (two per bar where the harmony moves on beat 3) */
  const CH = { F: [[53, 57, 60], 41, 48], Bb: [[58, 62, 65], 46, 53], C7: [[55, 58, 60, 64], 48, 43], Dm: [[57, 62, 65], 50, 45], Gm: [[55, 58, 62], 43, 50] };
  const HARM = ["F", "Bb", "C7", "F", "F", "Dm", ["Gm", "C7"], "F", "Bb", "F", "C7", "F", "Dm", "Gm", "C7", "F"];
  const hz = m => 440 * Math.pow(2, (m - 69) / 12);

  const S = { place: "island", placeT: "island", ctx: null, on: false, want: true, master: null, music: null, amb: null, rev: null, radio: null, mvol: 1, tense: false, bar: 0, step: 0, next: 0, timer: 0, noise: null, sea: null };
  try { S.want = localStorage.getItem("tauhud-rabbit-sound") !== "off"; } catch (e) {}

  function build() {
    const c = S.ctx = new (window.AudioContext || window.webkitAudioContext)();
    S.master = c.createGain(); S.master.gain.value = 0.8; S.master.connect(c.destination);
    /* a small room of reverb, made from decaying noise */
    const len = c.sampleRate * 1.8, ir = c.createBuffer(2, len, c.sampleRate);
    for (let ch = 0; ch < 2; ch++) { const d = ir.getChannelData(ch); for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 3); }
    S.rev = c.createConvolver(); S.rev.buffer = ir; const rg = c.createGain(); rg.gain.value = 0.22; S.rev.connect(rg); rg.connect(S.master);
    /* the music bus; at the radio it goes through a small speaker (a band-pass) */
    S.music = c.createGain(); S.music.gain.value = 0;
    S.radio = c.createBiquadFilter(); S.radio.type = "allpass";
    S.music.connect(S.radio); S.radio.connect(S.master); S.radio.connect(S.rev);
    S.amb = c.createGain(); S.amb.gain.value = 0; S.amb.connect(S.master);
    const nb = c.createBuffer(1, c.sampleRate * 2, c.sampleRate), nd = nb.getChannelData(0); for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1; S.noise = nb;
    /* the sea: noise through a low filter that breathes like waves on a beach */
    const sea = c.createBufferSource(); sea.buffer = nb; sea.loop = true;
    const lp = c.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 420;
    const sg = c.createGain(); sg.gain.value = 0.18;
    const lfo = c.createOscillator(), lg = c.createGain(); lfo.frequency.value = 0.11; lg.gain.value = 0.14; lfo.connect(lg); lg.connect(sg.gain);
    const lfo2 = c.createOscillator(), lg2 = c.createGain(); lfo2.frequency.value = 0.07; lg2.gain.value = 260; lfo2.connect(lg2); lg2.connect(lp.frequency);
    sea.connect(lp); lp.connect(sg); sg.connect(S.amb); sea.start(); lfo.start(); lfo2.start();
    S.next = c.currentTime + 0.1;
    S.timer = setInterval(tick, 25);
    setInterval(() => { if (S.on && Math.random() < 0.35) gull(); }, 7000);
  }
  /* ---------- the instruments ---------- */
  function env(g, t, a, peak, d) { g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(peak, t + a); g.gain.exponentialRampToValueAtTime(0.0001, t + a + d); }
  function pan(t, m, dur, v = 0.22) {   // steel pan: a bright fundamental, its octave and twelfth, a slight shimmer
    const c = S.ctx, out = c.createGain(); out.connect(S.music);
    [[1, 1], [2, 0.5], [3, 0.2], [4.02, 0.08]].forEach(([r, a], i) => {
      const o = c.createOscillator(), g = c.createGain(); o.frequency.value = hz(m) * r; o.detune.value = (i ? 4 : 0);
      env(g, t, 0.006, v * a, Math.min(1.4, 0.35 + dur * 0.9) / (1 + i * 0.6)); o.connect(g); g.connect(out); o.start(t); o.stop(t + 2);
    });
    const vib = c.createOscillator(), vg = c.createGain(); vib.frequency.value = 5.5; vg.gain.value = 0.05; vib.connect(vg); vg.connect(out.gain); vib.start(t); vib.stop(t + 2);
  }
  function marimba(t, m, v = 0.08) {
    const c = S.ctx;
    [[1, 1, 0.28], [3.93, 0.25, 0.06]].forEach(([r, a, d]) => { const o = c.createOscillator(), g = c.createGain(); o.frequency.value = hz(m) * r; env(g, t, 0.004, v * a, d); o.connect(g); g.connect(S.music); o.start(t); o.stop(t + 0.5); });
  }
  function bass(t, m, dur, v = 1) {
    const c = S.ctx, o = c.createOscillator(), o2 = c.createOscillator(), f = c.createBiquadFilter(), g = c.createGain();
    o.type = "triangle"; o.frequency.value = hz(m); o2.frequency.value = hz(m) / 2; f.type = "lowpass"; f.frequency.value = 700;
    env(g, t, 0.01, 0.32 * v, Math.max(0.18, dur * STEP * 1.2)); o.connect(f); o2.connect(f); f.connect(g); g.connect(S.music); o.start(t); o2.start(t); o.stop(t + 1); o2.stop(t + 1);
  }
  function hit(t, type, v = 1) {
    const c = S.ctx, g = c.createGain(); g.connect(S.music);
    if (type === "shaker") { const n = c.createBufferSource(), f = c.createBiquadFilter(); n.buffer = S.noise; f.type = "highpass"; f.frequency.value = 6500; env(g, t, 0.004, 0.05 * v, 0.045); n.connect(f); f.connect(g); n.start(t, Math.random()); n.stop(t + 0.1); }
    if (type === "conga" || type === "congaHi") { const o = c.createOscillator(); const f0 = type === "conga" ? 190 : 285; o.frequency.setValueAtTime(f0 * 1.3, t); o.frequency.exponentialRampToValueAtTime(f0, t + 0.05); env(g, t, 0.003, 0.22 * v, 0.22); o.connect(g); o.start(t); o.stop(t + 0.4); }
    if (type === "clave") { const o = c.createOscillator(); o.frequency.value = 2400; env(g, t, 0.002, 0.07 * v, 0.05); o.connect(g); o.start(t); o.stop(t + 0.1); }
    if (type === "rim") { const o = c.createOscillator(); o.type = "square"; o.frequency.value = 1700; env(g, t, 0.001, 0.035 * v, 0.03); o.connect(g); o.start(t); o.stop(t + 0.06); }
    if (type === "hat") { const n = c.createBufferSource(), f = c.createBiquadFilter(); n.buffer = S.noise; f.type = "highpass"; f.frequency.value = 9000; env(g, t, 0.002, 0.04 * v, 0.03); n.connect(f); f.connect(g); n.start(t, Math.random()); n.stop(t + 0.06); }
    if (type === "agogo" || type === "agogoLo") { [1, 2.7].forEach((r, i) => { const o = c.createOscillator(); o.frequency.value = (type === "agogo" ? 880 : 660) * r; const gg = c.createGain(); env(gg, t, 0.002, (i ? 0.02 : 0.06) * v, 0.18); o.connect(gg); gg.connect(g); o.start(t); o.stop(t + 0.3); }); g.gain.value = 1; }
    if (type === "timp") { const o = c.createOscillator(); o.frequency.setValueAtTime(98, t); o.frequency.exponentialRampToValueAtTime(87, t + 0.4); env(g, t, 0.005, 0.3 * v, 0.7); o.connect(g); o.start(t); o.stop(t + 0.9); }
    if (type === "snare") { const n = c.createBufferSource(), f = c.createBiquadFilter(); n.buffer = S.noise; f.type = "bandpass"; f.frequency.value = 2200; f.Q.value = 0.8; env(g, t, 0.002, 0.08 * v, 0.12); n.connect(f); f.connect(g); n.start(t, Math.random()); n.stop(t + 0.2); }
    if (type === "kick") { const o = c.createOscillator(); o.frequency.setValueAtTime(120, t); o.frequency.exponentialRampToValueAtTime(48, t + 0.12); env(g, t, 0.004, 0.35 * v, 0.2); o.connect(g); o.start(t); o.stop(t + 0.3); }
  }
  function gull() {
    const c = S.ctx, t = c.currentTime, o = c.createOscillator(), g = c.createGain(); o.type = "sawtooth";
    const f = c.createBiquadFilter(); f.type = "bandpass"; f.frequency.value = 2200; f.Q.value = 6;
    for (let i = 0; i < 3; i++) { o.frequency.setValueAtTime(1500, t + i * 0.22); o.frequency.exponentialRampToValueAtTime(900, t + i * 0.22 + 0.18); }
    g.gain.setValueAtTime(0.0001, t); for (let i = 0; i < 3; i++) { g.gain.exponentialRampToValueAtTime(0.025, t + i * 0.22 + 0.03); g.gain.exponentialRampToValueAtTime(0.0001, t + i * 0.22 + 0.19); }
    o.connect(f); f.connect(g); g.connect(S.amb); o.start(t); o.stop(t + 0.8);
  }
  /* ---------- the band ---------- */
  const CLAVE = [[0, 6, 12], [4, 8]];   // two bars, three then two
  /* every place on the island has its own arrangement of the same tune:
     k tempo, drums (full, soft, bossa or none), bass, marimba, the tune's voice, and something only that place has */
  const STYLES = {
    island: { k: 1, drums: "full", bass: 1, mar: 1, lead: "pan" },
    hall:   { k: 0.78, drums: "march", bass: 0.8, mar: 0, lead: "brass", pad: 1 },                // the council: a small brass anthem over an organ
    radio:  { k: 1.14, drums: "full", bass: 1.1, mar: 1, lead: "pan", hat: 1 },                    // on air: faster, with a hi-hat, through the speaker
    north:  { k: 0.84, drums: "none", bass: 0.5, mar: 0, lead: "bell", arp: 1, pad: 0.6 },         // the North Wind: cool bells and a slow harp
    south:  { k: 0.9, drums: "bossa", bass: 0.9, mar: 1, lead: "pan", soft: 1 },                   // the South Current: an easy bossa
    bar:    { k: 1.06, drums: "full", bass: 1.1, mar: 0, lead: "pan", strum: 1, conga: 1 },        // La Ola: the whole band and a guitar
    book:   { k: 0.6, drums: "none", bass: 0, mar: 0, lead: "bell", pad: 0.8, sparse: 1 },        // the lighthouse: almost silence, a few bells
    market: { k: 1.1, drums: "full", bass: 1, mar: 1, lead: "pan", agogo: 1, conga: 1 },           // the square: busy, a cowbell
    pier:   { k: 0.74, drums: "soft", bass: 0.6, mar: 0, lead: "flute", arp: 1 },                  // the pier: a slow flute over the water
  };
  function play(bar, st, t) {
    const y = STYLES[S.place] || STYLES.island, b = bar % 16, h = HARM[b], ch = CH[Array.isArray(h) ? (st < 8 ? h[0] : h[1]) : h], dt = STEP / y.k;
    /* drums */
    if (y.drums === "full") {
      hit(t, "shaker", st % 2 ? 0.6 : (st % 4 === 2 ? 1.2 : 0.8));
      if (st === 0 || st === 8) hit(t, "kick", 0.8);
      if (st === 6 || st === 14) hit(t, "conga", 0.9); if (st === 7 || st === 15 || st === 3) hit(t, "congaHi", 0.6);
      if (y.conga && (st === 10 || st === 11)) hit(t, "congaHi", 0.5);
      if (CLAVE[bar % 2].includes(st)) hit(t, "clave");
    }
    if (y.drums === "soft" && st % 4 === 2) hit(t, "shaker", 0.7);
    if (y.drums === "bossa") { if (st === 0 || st === 8) hit(t, "kick", 0.55); if ([0, 3, 6, 10, 13].includes(st) && bar % 2 === 0 || [2, 6, 10].includes(st) && bar % 2) hit(t, "rim", 0.8); if (st % 2 === 0) hit(t, "shaker", 0.5); }
    if (y.drums === "march") { if (st === 0) hit(t, "timp", 1); if (st === 8) hit(t, "timp", 0.7); if (st === 12 || st === 14) hit(t, "snare", st === 12 ? 0.6 : 0.4); }
    if (y.hat && st % 2 === 0) hit(t, "hat", st % 4 ? 0.6 : 1);
    if (y.agogo && [0, 3, 6, 8, 10].includes(st)) hit(t, st === 3 || st === 10 ? "agogoLo" : "agogo", 0.8);
    /* bass: root and fifth, the calypso bounce (only the roots where the place is quiet) */
    const BASS = y.drums === "full" ? { 0: [1, 3], 3: [1, 1], 6: [2, 2], 8: [1, 3], 11: [1, 1], 14: [2, 2] } : { 0: [1, 6], 8: [2, 6] };
    if (y.bass && BASS[st]) bass(t, ch[BASS[st][0]], BASS[st][1], y.bass);
    if (S.tense) return;   // a tense moment: drums and bass only
    if (y.pad && st === 0) pad(t, ch[0], dt * 16, y.pad);
    if (y.pad && st === 8 && Array.isArray(h)) pad(t, ch[0], dt * 8, y.pad);
    if (y.mar && st % 4 === 2) ch[0].forEach((m, i) => marimba(t + i * 0.008, m + 12, y.soft ? 0.035 : 0.05));
    if (y.arp && st % 2 === 0) { const n = ch[0][(st / 2) % ch[0].length]; marimba(t, n + (st >= 8 ? 24 : 12), 0.045); }
    if (y.strum && (st === 2 || st === 6 || st === 10 || st === 14)) strum(t, ch[0]);
    /* the tune, on the voice of the place; the second time round lower, with a harmony a third under */
    for (const [s, m, d] of TUNE[b]) if (s === st) {
      if (y.sparse && d < 3) continue;
      const lap = Math.floor(bar / 16) % 2, mm = lap ? m - 12 : m;
      if (y.lead === "pan") { pan(t, mm, d * dt, y.soft ? 0.14 : 0.2); if (lap) pan(t + 0.01, m - 15 - (m % 12 === 9 ? 1 : 0), d * dt, 0.08); }
      if (y.lead === "bell") bell(t, m + 12, d * dt);
      if (y.lead === "brass") brass(t, m - 12, d * dt);
      if (y.lead === "flute") flute(t, m, d * dt);
    }
  }
  function pad(t, notes, dur, v) {   // a soft organ: two detuned sines per note, slow in and out
    const c = S.ctx;
    notes.forEach(m => [0, 7].forEach(dn => { const o = c.createOscillator(), g = c.createGain(); o.frequency.value = hz(m); o.detune.value = dn; g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.03 * v, t + 0.4); g.gain.setValueAtTime(0.03 * v, t + Math.max(0.5, dur - 0.4)); g.gain.exponentialRampToValueAtTime(0.0001, t + dur + 0.3); o.connect(g); g.connect(S.music); o.start(t); o.stop(t + dur + 0.4); }));
  }
  function bell(t, m, dur) {   // a glass bell: inharmonic partials, a long ring
    const c = S.ctx;
    [[1, 0.12, 2.2], [2.76, 0.05, 1.2], [5.4, 0.025, 0.6]].forEach(([r, a, d]) => { const o = c.createOscillator(), g = c.createGain(); o.frequency.value = hz(m) * r; env(g, t, 0.003, a, d + dur * 0.4); o.connect(g); g.connect(S.music); o.start(t); o.stop(t + d + dur + 0.2); });
  }
  function brass(t, m, dur) {   // a small brass band: a filtered saw that opens as it speaks
    const c = S.ctx, o = c.createOscillator(), o2 = c.createOscillator(), f = c.createBiquadFilter(), g = c.createGain();
    o.type = o2.type = "sawtooth"; o.frequency.value = hz(m); o2.frequency.value = hz(m); o2.detune.value = 8;
    f.type = "lowpass"; f.frequency.setValueAtTime(500, t); f.frequency.linearRampToValueAtTime(1800, t + 0.08); f.frequency.linearRampToValueAtTime(1100, t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.07, t + 0.04); g.gain.setValueAtTime(0.06, t + Math.max(0.05, dur - 0.05)); g.gain.exponentialRampToValueAtTime(0.0001, t + dur + 0.15);
    o.connect(f); o2.connect(f); f.connect(g); g.connect(S.music); o.start(t); o2.start(t); o.stop(t + dur + 0.2); o2.stop(t + dur + 0.2);
  }
  function flute(t, m, dur) {   // a wooden flute: a sine with breath and a late vibrato
    const c = S.ctx, o = c.createOscillator(), g = c.createGain(), vib = c.createOscillator(), vg = c.createGain();
    o.frequency.value = hz(m); vib.frequency.value = 5; vg.gain.setValueAtTime(0, t); vg.gain.linearRampToValueAtTime(5, t + Math.min(0.5, dur)); vib.connect(vg); vg.connect(o.frequency);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.09, t + 0.06); g.gain.setValueAtTime(0.08, t + Math.max(0.07, dur - 0.05)); g.gain.exponentialRampToValueAtTime(0.0001, t + dur + 0.25);
    o.connect(g); g.connect(S.music); o.start(t); vib.start(t); o.stop(t + dur + 0.3); vib.stop(t + dur + 0.3);
    const n = c.createBufferSource(), nf = c.createBiquadFilter(), ng = c.createGain(); n.buffer = S.noise; nf.type = "bandpass"; nf.frequency.value = hz(m) * 2; nf.Q.value = 2; env(ng, t, 0.02, 0.012, 0.12); n.connect(nf); nf.connect(ng); ng.connect(S.music); n.start(t, Math.random()); n.stop(t + 0.2);
  }
  function strum(t, notes) {   // a nylon guitar, strummed down
    const c = S.ctx;
    [...notes, notes[0] + 12].forEach((m, i) => { const o = c.createOscillator(), f = c.createBiquadFilter(), g = c.createGain(); o.type = "sawtooth"; o.frequency.value = hz(m); f.type = "lowpass"; f.frequency.value = 1400; env(g, t + i * 0.012, 0.003, 0.028, 0.3); o.connect(f); f.connect(g); g.connect(S.music); o.start(t + i * 0.012); o.stop(t + i * 0.012 + 0.45); });
  }
  function tick() {
    if (!S.ctx || !S.on) return;
    while (S.next < S.ctx.currentTime + 0.12) {
      const t = S.next + (S.step % 2 ? STEP / (STYLES[S.place] || STYLES.island).k * SWING : 0);
      play(S.bar, S.step, t);
      const y = STYLES[S.place] || STYLES.island;
      S.next += STEP / y.k; S.step++; if (S.step === 16) { S.step = 0; S.bar++; if (S.placeT !== S.place) { S.place = S.placeT; S.bar -= S.bar % 4; } }
    }
  }
  /* ---------- small sounds for the game ---------- */
  function sfx(name) {
    if (!S.ctx || !S.on) return;
    const c = S.ctx, t = c.currentTime;
    const tone = (f, at, d, v = 0.12, type = "sine") => { const o = c.createOscillator(), g = c.createGain(); o.type = type; o.frequency.value = f; env(g, t + at, 0.005, v, d); o.connect(g); g.connect(S.master); o.start(t + at); o.stop(t + at + d + 0.1); };
    if (name === "tap") tone(1320, 0, 0.06, 0.05);
    if (name === "open") { tone(784, 0, 0.12, 0.06); tone(1175, 0.06, 0.16, 0.05); }
    if (name === "coin") { tone(1568, 0, 0.08, 0.08, "square"); tone(2093, 0.07, 0.2, 0.06, "square"); }
    if (name === "yes") { tone(523, 0, 0.18, 0.1); tone(659, 0.09, 0.18, 0.1); tone(784, 0.18, 0.4, 0.1); }
    if (name === "no") { tone(220, 0, 0.3, 0.14, "triangle"); tone(185, 0.12, 0.4, 0.12, "triangle"); }
    if (name === "stamp") { const n = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain(); n.buffer = S.noise; f.type = "lowpass"; f.frequency.value = 900; env(g, t, 0.002, 0.5, 0.12); n.connect(f); f.connect(g); g.connect(S.master); n.start(t); n.stop(t + 0.2); }
    if (name === "cheer") { for (let i = 0; i < 4; i++) { const n = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain(); n.buffer = S.noise; f.type = "bandpass"; f.frequency.value = 900 + i * 500; f.Q.value = 1.4; g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.06, t + 0.3 + i * 0.1); g.gain.exponentialRampToValueAtTime(0.0001, t + 2.4); n.connect(f); f.connect(g); g.connect(S.master); n.start(t, i * 0.3); n.stop(t + 2.6); } [0, 0.15, 0.3].forEach((a, i) => pan(t + a, [77, 81, 84][i], 0.5, 0.18)); }
    if (name === "glitch") { for (let i = 0; i < 6; i++) tone(200 + Math.random() * 1800, i * 0.035, 0.03, 0.05, "square"); }
    if (name === "jingle") { [[0, 77], [0.11, 81], [0.22, 84], [0.4, 89]].forEach(([a, m], i) => pan(t + a, m, i === 3 ? 0.5 : 0.12, 0.1)); }
    if (name === "meow") { const o = c.createOscillator(), g = c.createGain(), f = c.createBiquadFilter(); o.type = "sawtooth"; f.type = "bandpass"; f.frequency.value = 1100; f.Q.value = 3; o.frequency.setValueAtTime(520, t); o.frequency.linearRampToValueAtTime(780, t + 0.18); o.frequency.linearRampToValueAtTime(420, t + 0.5); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.07, t + 0.06); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.55); o.connect(f); f.connect(g); g.connect(S.master); o.start(t); o.stop(t + 0.6); }
  }
  /* ---------- the mix ---------- */
  const want = { music: 1, radio: false, tense: false, amb: 1, place: null };
  function apply() {
    if (!S.ctx) return;
    const t = S.ctx.currentTime;
    S.music.gain.setTargetAtTime(S.on ? 0.55 * want.music * (S.duck ? 0.3 : 1) : 0, t, S.duck ? 0.15 : 0.4);
    S.amb.gain.setTargetAtTime(S.on ? want.amb : 0, t, 0.6);
    S.radio.type = want.radio ? "bandpass" : "allpass"; S.radio.frequency.value = 1400; S.radio.Q.value = want.radio ? 0.9 : 0.0001;
    S.tense = want.tense;
    /* a new place: the band changes at the next bar; when the change comes from far, it starts within half a bar */
    const pl = want.place && STYLES[want.place] ? want.place : "island";
    if (pl !== S.placeT) { S.placeT = pl; if (S.step >= 8 || S.place === "island" || pl === "island") { S.step = 15; } }
  }
  function start() {
    if (!S.want) return false;
    try {
      if (!S.ctx) { build(); S.ctx.onstatechange = () => S.cb && S.cb(); }
      S.on = true; apply();
      if (S.ctx.state !== "running") S.ctx.resume().then(() => S.cb && S.cb(), () => {});
      return S.ctx.state === "running";
    } catch (e) { return false; }
  }
  /* a voice (rico.js): the clips one after the other, after the jingle, through a small-radio colour; the music
     steps back while someone talks. Resolves with how many seconds they will talk. */
  async function speak(bufs) {
    if (!S.ctx || !S.on) return false;
    const c = S.ctx, list = [];
    for (const b of bufs) { try { list.push(await c.decodeAudioData(b)); } catch (e) { return false; } }
    if (!S.voice) {
      const hp = c.createBiquadFilter(), pk = c.createBiquadFilter(), g = c.createGain(), comp = c.createDynamicsCompressor();
      hp.type = "highpass"; hp.frequency.value = 160; pk.type = "peaking"; pk.frequency.value = 2600; pk.Q.value = 0.8; pk.gain.value = 3;
      comp.threshold.value = -20; comp.ratio.value = 3; g.gain.value = 1.1;
      hp.connect(pk); pk.connect(comp); comp.connect(g); g.connect(S.master); S.voice = hp;
    }
    if (S.talking) S.talking.forEach(n => { try { n.stop(); } catch (e) {} });
    let at = c.currentTime + 0.55; S.talking = [];
    for (const buf of list) { const n = c.createBufferSource(); n.buffer = buf; n.connect(S.voice); n.start(at); S.talking.push(n); at += buf.duration + 0.18; }
    S.duck = true; apply();
    const mine = S.talking;
    const secs = at - c.currentTime;
    setTimeout(() => { if (S.talking === mine) { S.duck = false; S.talking = null; apply(); } }, secs * 1000);
    return secs;
  }
  /* whoever is talking stops (a card closed) */
  function hush() {
    if (S.talking) S.talking.forEach(n => { try { n.stop(); } catch (e) {} });
    S.talking = null; if (S.duck) { S.duck = false; apply(); }
  }
  window.COVE_SOUND = {
    start, sfx, speak, hush,
    /* on: the music is really playing (a browser lets it start only after the first click, tap or key) */
    get on() { return S.on && !!S.ctx && S.ctx.state === "running"; }, get wanted() { return S.want; },
    set onchange(f) { S.cb = f; },
    set(o) { Object.assign(want, o); apply(); },
    toggle() {
      S.want = !S.want; try { localStorage.setItem("tauhud-rabbit-sound", S.want ? "on" : "off"); } catch (e) {}
      if (S.want) start(); else { S.on = false; if (S.talking) S.talking.forEach(n => { try { n.stop(); } catch (e) {} }); S.talking = null; S.duck = false; apply(); }
      return S.want;
    },
  };
})();

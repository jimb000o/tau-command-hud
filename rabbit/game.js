/* White Rabbit Key: a small island politics game. Four candidates, five days, one election.
   Each day you have three moves (morning, noon, evening): propose a law at the Council Hall, talk to people on the
   market square, buy a rumour on Radio Coco, take an embassy's money for a promise, make a pact at Bar La Ola.
   Every move, yours and your rivals', is written into the Book in the lighthouse, and anyone on the island can read it.
   A law that contradicts one in force is refused before anyone votes. A law needs two of the other three candidates.
   Optional: a law you pass and your vote at the end can go to Tau Testnet Alpha as real test transactions (1 test AGRS). */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  /* every translated text remembers its English, so a line shown in Chinese or Japanese is still spoken in English */
  const ENG = new Map();
  const T = s => { const r = window.TauI18n ? TauI18n.t(s) : s; if (r !== s) ENG.set(r, s); return r; };
  const F = (s, v) => T(s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m)));
  const EN = s => ENG.get(s) || s;
  const SC = window.COVE_SCENE, SND = window.COVE_SOUND, RICO = window.RICO;
  /* a part of what Rico says: spoken aloud when the server has his clip (rico.js), or only shown */
  const V = (k, v) => ({ t: v ? F(RICO.L[k], v) : T(RICO.L[k]), v: v ? RICO.fill(RICO.L[k], v) : RICO.L[k] });
  const Q = (s, v) => ({ t: v ? F(s, v) : T(s), v: null });
  /* a part anyone says in a place: shown in the visitor's language, spoken in English (RICO.CAST has the clips) */
  const S = s => ({ t: T(s), v: s });
  const join = parts => parts.map(p => p.t).join(window.TauI18n && /^(zh|ja)$/.test(TauI18n.lang) ? "" : " ");
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} }, del: k => { try { localStorage.removeItem(k); } catch (e) {} } };
  function el(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) { if (v == null || v === false) continue; if (k === "class") e.className = v; else if (k === "text") e.textContent = v; else if (k.startsWith("on")) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v === true ? "" : v); }
    for (const k of kids.flat()) if (k != null && k !== false) e.append(k);
    return e;
  }

  /* ---------- who lives on the island ---------- */
  const TOPICS = { fish: "fishing", school: "the school", music: "music", quiet: "quiet nights", visitors: "visitors", roads: "roads" };
  const CANDS = {
    marisol: { name: "Marisol", role: "Fisher, runs the net shed", skin: "#a8693f", hair: "#1d1410", style: "bun", acc: "scarf", accC: "#e8574a", shirt: "#2fb0a8", cares: ["fish", "roads"], way: "people",
      pitch: "Talks to everyone, forgets no one." },
    tobias: { name: "Tobias", role: "Harbour master, loves a ceremony", skin: "#e0b08a", hair: "#9a9aa0", style: "side", acc: "cap", accC: "#1f3550", shirt: "#f4f1ea", cares: ["visitors", "music"], way: "rumours",
      pitch: "Has a microphone and a theory about everyone." },
    baako: { name: "Baako", role: "Coconut farmer, friend of every embassy", skin: "#5a3620", hair: "#111", style: "short", acc: "straw", accC: "#d9b45a", shirt: "#f2b134", cares: ["visitors", "roads"], way: "money",
      pitch: "Shakes every hand, especially the ones holding envelopes." },
    hana: { name: "Hana", role: "Schoolteacher, writes everything down", skin: "#f0cfa8", hair: "#222", style: "bob", acc: "glasses", accC: "#333", shirt: "#6f8cff", cares: ["school", "quiet"], way: "laws",
      pitch: "Believes a good law beats a good speech." },
  };
  const FOLK = {
    rico: { name: "Rico", role: "DJ on Radio Coco", skin: "#7a4a2a", hair: "#111", style: "afro", acc: "phones", accC: "#e8574a", shirt: "#e86fa0" },
    frost: { name: "Ambassador Frost", role: "North Wind Embassy", skin: "#f3d6c0", hair: "#e0e0e0", style: "side", acc: "monocle", accC: "#d9b44a", shirt: "#3b5f8a" },
    salado: { name: "Ambassador Salado", role: "South Current Embassy", skin: "#c68642", hair: "#3a2a1a", style: "side", acc: "mustache", accC: "#3a2a1a", shirt: "#c0533f" },
    lola: { name: "Lola", role: "Runs Bar La Ola", skin: "#8d5524", hair: "#5a1a1a", style: "curls", acc: "flower", accC: "#ff6f91", shirt: "#fff6e6" },
    sam: { name: "Old Sam", role: "Keeper of the lighthouse and the Book", skin: "#c9a27a", hair: "#eee", style: "bald", acc: "beard", accC: "#eee", shirt: "#2a2a30" },
    /* the people of the island's other quarters (a painted island with a layout that has them, infra/rabbit-art) */
    ama: { name: "Ama", role: "Elder of the first people", skin: "#5a3620", hair: "#dcdcdc", style: "bun", acc: "glasses", accC: "#333", shirt: "#2f6440" },
    wren: { name: "Captain Wren", role: "Marine archaeologist, retired", skin: "#e0b08a", hair: "#b0502a", style: "bob", acc: "cap", accC: "#1f3550", shirt: "#3aa6a0" },
    kai: { name: "Kai", role: "Runs the Reef Proof dive centre", skin: "#c68642", hair: "#111", style: "short", acc: "glasses", accC: "#333", shirt: "#4fd1c5" },
    pim: { name: "Pim", role: "Surveyor, measures for the embassies", skin: "#f3d6c0", hair: "#c9a46a", style: "side", acc: "straw", accC: "#d9b45a", shirt: "#f4f1ea" },
    noor: { name: "Noor", role: "Foreman of the Coconut Works", skin: "#a8693f", hair: "#1d1410", style: "curls", acc: "glasses", accC: "#333", shirt: "#e9b44c" },
    kiko: { name: "Kiko", role: "Builds canoes", skin: "#8d5524", hair: "#111", style: "short", acc: "none", shirt: "#e85d4a" },
  };
  /* the ten who vote; each cares about two things (Sam also cares a great deal about what is true) */
  const PEOPLE = [
    { id: "rosa", name: "Rosa", cares: ["quiet", "school"] }, { id: "kiko", name: "Kiko", cares: ["fish", "music"] },
    { id: "ines", name: "Inés", cares: ["school", "quiet"] }, { id: "pia", name: "Pía", cares: ["visitors", "roads"] },
    { id: "sam", name: "Old Sam", cares: ["fish", "quiet"], reads: 1 }, { id: "nadia", name: "Nadia", cares: ["fish", "roads"] },
    { id: "teo", name: "Teo", cares: ["music", "school"] }, { id: "ama", name: "Ama", cares: ["visitors", "quiet"] },
    { id: "javi", name: "Javi", cares: ["visitors", "roads"] }, { id: "lola", name: "Lola", cares: ["music", "visitors"] },
  ];
  /* the laws one can propose: what they do for each topic, and which laws they cannot stand beside */
  const LAWS = {
    night:    { t: "Night market every Friday", fx: { music: 1, visitors: 1, quiet: -1 }, no: ["quiet"] },
    quiet:    { t: "Quiet after ten in the evening", fx: { quiet: 2, music: -1 }, no: ["night", "concerts"] },
    reef:     { t: "Protect the reef: no big ships in the bay", fx: { fish: 2, visitors: -1 }, no: ["harbour"] },
    harbour:  { t: "A deep harbour for cruise ships", fx: { visitors: 2, roads: 1, fish: -2 }, no: ["reef"] },
    boat:     { t: "A school boat every morning", fx: { school: 2, roads: 1 }, no: [] },
    lunch:    { t: "Fresh fish for the school lunch", fx: { school: 1, fish: 1 }, no: [] },
    concerts: { t: "Beach concerts on Sundays", fx: { music: 2, visitors: 1, quiet: -1 }, no: ["quiet"] },
    road:     { t: "A road round the island", fx: { roads: 2, visitors: 1, quiet: -1 }, no: [] },
    copy:     { t: "A copy of the Book on the square", fx: {}, no: [], open: true },
    tax:      { t: "A coconut tax for repairs", fx: { roads: 2, visitors: -1 }, no: [] },
  };
  /* the rumours Rico can play that are simply not true */
  const LIES = { marisol: "Marisol fishes inside the reef at night", tobias: "Tobias wants to sell the lighthouse", baako: "Baako’s coconuts are imported", hana: "Hana wants school on Sundays" };
  const EMB = {
    north: { who: "frost", name: "North Wind Embassy", wants: "harbour", coins: 40 },
    south: { who: "salado", name: "South Current Embassy", wants: "road", coins: 35 },
  };
  const DAYS = 5, MOVES = 3, RUMOUR = 25, GIFT = 20;
  const HOURS = ["Morning", "Noon", "Evening"];
  /* real test transactions: four ballot boxes and the council's chest, addresses with no owner behind them */
  const ADDR = {
    council: "96179f47d33ab65d9922c5652d7686f9e6be9d36ef4b9e9e04bdaac25b6e30d01928182c16da7aaa6dc954cccb88b62b",
    marisol: "b44a202e884682b8677daf5f2685b5775f3c9ea9443a89651013bc455bc66061f2cf8d092897893bad3311e598f2cb11",
    tobias: "96bf03fb7c34b84f916d928cf82bd332cd9558ab3c55e9a717381fe5c8cc6d4ec1e694e39855a680ea8f29351d6a2aea",
    baako: "981bfa68b487e86991cbd70d3c1c8ed4b151715031580976f0942610958a16e29d71c15ea4accdb3750db225f35c3f50",
    hana: "adf1b27a6cfe88b1c73f12ed38eaaef535f892ee2f2b695030427ecaef7d4e43deb89f7849f2f5550cc5eec711652174",
  };

  const looks = id => CANDS[id] || FOLK[id] || { skin: "#c68642", hair: "#222", style: "short", shirt: "#ddd" };
  /* ---------- portraits: painted like the island, in flat inks with a hand-drawn line ----------
     every islander has their own head, nose and posture; one side of the face is shaded in printed dots */
  const INK = "#22303a";
  const HEADS = {   // w, h: half-width and half-height of the head; jaw: how wide the chin is (0 narrow, 1 square); nose; bg: the colour of their print
    marisol: { w: 21, h: 27, jaw: 0.35, nose: "straight", bg: "#2c8c88" }, tobias: { w: 24, h: 30, jaw: 0.9, nose: "long", bg: "#284b63" },
    baako: { w: 27, h: 26, jaw: 0.7, nose: "round", bg: "#e9b44c" }, hana: { w: 21, h: 25, jaw: 0.25, nose: "button", bg: "#e2674f" },
    rico: { w: 23, h: 27, jaw: 0.55, nose: "round", bg: "#e889a6" }, frost: { w: 19, h: 31, jaw: 0.3, nose: "hook", bg: "#7fb2d0" },
    salado: { w: 27, h: 27, jaw: 0.8, nose: "round", bg: "#d9653f" }, lola: { w: 22, h: 26, jaw: 0.35, nose: "button", bg: "#2c8c88" },
    sam: { w: 24, h: 28, jaw: 0.6, nose: "long", bg: "#5c9a4c" },
  };
  /* a painted portrait (infra/rabbit-art paint.py busts) in place of the drawn face: it breathes, blinks, and its mouth
     moves while it talks (the -talk and -blink frames, laid over the still picture where they differ) */
  const bustOf = id => !/[?&]art=drawn/.test(location.search) && SC.art && SC.art.img["bust-" + id];
  const MOUTH = {};
  function frame(id, t, talk) {
    const img = SC.art.img, k = "bust-" + id;
    if (talk && img[k + "-talk"]) {   // open and shut in syllables of uneven length
      const m = MOUTH[id] || (MOUTH[id] = { at: 0, open: false });
      if (t >= m.at) { m.open = !m.open; m.at = t + (m.open ? 90 + Math.random() * 110 : 60 + Math.random() * 90); }
      if (m.open) return k + "-talk";
    }
    if (img[k + "-blink"] && (t + id.length * 997) % 4200 < 130) return k + "-blink";
    return null;
  }
  function paintedFace(g, B, id, t, talk, bare) {
    const W = g.canvas.width, br = 1 + 0.006 * Math.sin(t * 0.0021);
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, W, W); g.imageSmoothingQuality = "high";
    const f = frame(id, t, talk), F = f && SC.art.img[f], box = f && (SC.art.box || {})[f];
    const draw = (x, y, w) => {
      g.drawImage(B, x, y, w, w);
      if (!F) return;
      if (!box) { g.drawImage(F, x, y, w, w); return; }   // a frame that differs all over: shown whole
      const [bx, by, bw, bh] = box, sw = F.naturalWidth;
      g.drawImage(F, bx * sw, by * sw, bw * sw, bh * sw, x + bx * w, y + by * w, bw * w, bh * w);
    };
    if (bare) { const w = W * br; draw((W - w) / 2, W - w, w); return; }
    g.save(); g.beginPath(); g.arc(W / 2, W / 2, W / 2 - 1, 0, Math.PI * 2); g.fillStyle = (HEADS[id] || {}).bg || "#2c8c88"; g.fill(); g.clip();
    const h = B._h || (B._h = headZoom(B)), w = W * h.z * br;
    draw((W - w) / 2, W * h.y, w); g.restore();   // the head and shoulders, close
  }
  /* how close the round portrait comes: a bust as before, a half figure (narrower than its square) closer, from its hair down */
  function headZoom(B) {
    try {
      const n = 64, c = document.createElement("canvas"); c.width = c.height = n; const x = c.getContext("2d"); x.drawImage(B, 0, 0, n, n);
      const d = x.getImageData(0, 0, n, n).data; let top = n, l = n, r = 0;
      for (let i = 0; i < n * n; i++) if (d[i * 4 + 3] > 128) { const px = i % n; top = Math.min(top, Math.floor(i / n)); l = Math.min(l, px); r = Math.max(r, px); }
      return (r - l) / n < 0.85 ? { z: 2.3, y: 0.04 - (top / n) * 2.3 } : { z: 1.55, y: -0.12 };
    } catch (e) { return { z: 1.55, y: -0.12 }; }
  }
  function face(g, id, t, talk, mood = 0, bare = false) {
    const B = bustOf(id); if (B) return paintedFace(g, B, id, t, talk, bare);
    const L = looks(id), H0 = HEADS[id] || { w: 22, h: 27, jaw: 0.5, nose: "straight", bg: "#2c8c88" }, W = g.canvas.width, s = W / 120;
    g.setTransform(s, 0, 0, s, 0, 0); g.clearRect(0, 0, 120, 120);
    g.lineJoin = "round"; g.lineCap = "round";
    const ink = (w = 2) => { g.strokeStyle = INK; g.lineWidth = w; g.stroke(); };
    /* the print behind them: a disc in their colour with a few rays */
    if (!bare) {
      g.fillStyle = H0.bg; g.globalAlpha = 0.9; g.beginPath(); g.arc(60, 56, 50, 0, Math.PI * 2); g.fill(); g.globalAlpha = 1;
      g.save(); g.beginPath(); g.arc(60, 56, 50, 0, Math.PI * 2); g.clip();
      g.fillStyle = "rgba(251,243,223,.14)"; for (let k = 0; k < 12; k++) { const a = k * Math.PI / 6 + t * 0.00005; g.beginPath(); g.moveTo(60, 56); g.arc(60, 56, 60, a, a + 0.18); g.closePath(); g.fill(); }
      g.restore();
    }
    const bob = Math.sin(t * 0.002 + id.length) * 0.8, tilt = Math.sin(t * 0.0009 + id.length * 2) * 0.025 + (talk ? Math.sin(t * 0.006) * 0.02 : 0);
    g.translate(0, bob);
    const cx = 60, cy = 54, hw = H0.w, hh = H0.h;
    /* the torso: a flat shape with its collar, outlined */
    g.fillStyle = L.shirt; g.beginPath(); g.moveTo(10, 122); g.bezierCurveTo(12, 96, 30, 86, 60, 85); g.bezierCurveTo(90, 86, 108, 96, 110, 122); g.closePath(); g.fill(); ink(2.2);
    g.save(); g.clip(); dotsIn(g, 70, 84, 112, 122, 4, 1.3, "rgba(34,48,58,.35)"); g.restore();
    torso(g, id, L, ink);
    /* neck */
    g.fillStyle = L.skin; g.beginPath(); g.moveTo(cx - 8, cy + hh - 8); g.lineTo(cx - 9, 88); g.quadraticCurveTo(cx, 92, cx + 9, 88); g.lineTo(cx + 8, cy + hh - 8); g.closePath(); g.fill(); ink(1.8);
    g.save(); g.translate(cx, cy + hh); g.rotate(tilt); g.translate(-cx, -(cy + hh));
    /* hair behind the head */
    g.fillStyle = L.hair;
    if (L.style === "afro") { g.beginPath(); for (let k = 0; k <= 18; k++) { const a = Math.PI * (0.85 + k / 18 * 1.3), r = 34 + (k % 2) * 4; k ? g.lineTo(cx + Math.cos(a) * r, cy - 8 + Math.sin(a) * r) : g.moveTo(cx + Math.cos(a) * r, cy - 8 + Math.sin(a) * r); } g.closePath(); g.fill(); ink(2); }
    if (L.style === "curls") { for (let k = 0; k < 13; k++) { const a = Math.PI * (0.8 + k / 12 * 1.4); g.beginPath(); g.arc(cx + Math.cos(a) * (hw + 6), cy + 2 + Math.sin(a) * (hh + 4), 8, 0, Math.PI * 2); g.fill(); ink(1.6); } }
    if (L.style === "bob") { g.beginPath(); g.moveTo(cx - hw - 6, cy + 16); g.lineTo(cx - hw - 4, cy - 10); g.quadraticCurveTo(cx, cy - hh - 16, cx + hw + 4, cy - 10); g.lineTo(cx + hw + 6, cy + 16); g.closePath(); g.fill(); ink(2); }
    if (L.style === "bun") { g.beginPath(); g.ellipse(cx + 2, cy - hh - 4, 16, 10, 0.1, 0, Math.PI * 2); g.fill(); ink(2); }
    /* the head */
    const head = () => { g.beginPath(); g.moveTo(cx, cy - hh); g.bezierCurveTo(cx + hw * 1.15, cy - hh, cx + hw, cy + hh * 0.2, cx + hw * (0.55 + H0.jaw * 0.35), cy + hh * 0.75); g.quadraticCurveTo(cx + hw * 0.3, cy + hh * 1.02, cx, cy + hh); g.quadraticCurveTo(cx - hw * 0.3, cy + hh * 1.02, cx - hw * (0.55 + H0.jaw * 0.35), cy + hh * 0.75); g.bezierCurveTo(cx - hw, cy + hh * 0.2, cx - hw * 1.15, cy - hh, cx, cy - hh); g.closePath(); };
    g.fillStyle = L.skin; [-1, 1].forEach(d => { g.beginPath(); g.ellipse(cx + d * (hw + 1), cy + 2, 4.5, 7, 0, 0, Math.PI * 2); g.fill(); ink(1.8); });
    head(); g.fill(); ink(2.2);
    g.save(); head(); g.clip();
    g.fillStyle = shade(L.skin, -0.14); g.beginPath(); g.ellipse(cx + hw * 0.85, cy + 6, hw * 0.55, hh * 1.2, 0, 0, Math.PI * 2); g.fill();
    dotsIn(g, cx + 2, cy - hh, cx + hw + 2, cy + hh, 3.4, 1.1, "rgba(34,48,58,.28)");
    g.fillStyle = "rgba(226,103,79,.38)"; [-1, 1].forEach(d => { for (let k = 0; k < 7; k++) { const a = k / 7 * Math.PI * 2; g.beginPath(); g.arc(cx + d * hw * 0.55 + Math.cos(a) * 3.2, cy + 10 + Math.sin(a) * 2, 0.9, 0, Math.PI * 2); g.fill(); } });
    g.restore();
    /* hair on top */
    g.fillStyle = L.hair;
    const top = (pts) => { g.beginPath(); pts(); g.closePath(); g.fill(); ink(2); };
    if (L.style === "short") top(() => { g.moveTo(cx - hw - 1, cy - 6); g.quadraticCurveTo(cx - hw, cy - hh - 6, cx, cy - hh - 5); g.quadraticCurveTo(cx + hw, cy - hh - 6, cx + hw + 1, cy - 6); g.quadraticCurveTo(cx + hw * 0.4, cy - hh + 4, cx, cy - hh + 6); g.quadraticCurveTo(cx - hw * 0.5, cy - hh + 4, cx - hw - 1, cy - 6); });
    if (L.style === "side") top(() => { g.moveTo(cx - hw - 2, cy - 2); g.quadraticCurveTo(cx - hw - 4, cy - hh - 8, cx + 4, cy - hh - 7); g.quadraticCurveTo(cx + hw + 6, cy - hh - 4, cx + hw + 2, cy - 4); g.quadraticCurveTo(cx + hw * 0.2, cy - hh + 2, cx - hw * 0.5, cy - hh + 10); g.quadraticCurveTo(cx - hw + 2, cy - 10, cx - hw - 2, cy - 2); });
    if (L.style === "bob") top(() => { g.moveTo(cx - hw - 3, cy + 4); g.quadraticCurveTo(cx - hw - 2, cy - hh - 6, cx, cy - hh - 6); g.quadraticCurveTo(cx + hw + 2, cy - hh - 6, cx + hw + 3, cy + 4); g.lineTo(cx + hw - 3, cy - 4); g.lineTo(cx + 6, cy - hh + 10); g.lineTo(cx - hw + 3, cy - 6); });
    if (L.style === "bun" || L.style === "curls") top(() => { g.moveTo(cx - hw - 1, cy - 2); g.quadraticCurveTo(cx - hw - 2, cy - hh - 6, cx, cy - hh - 5); g.quadraticCurveTo(cx + hw + 2, cy - hh - 6, cx + hw + 1, cy - 2); g.quadraticCurveTo(cx + hw * 0.6, cy - hh + 6, cx, cy - hh + 5); g.quadraticCurveTo(cx - hw * 0.6, cy - hh + 6, cx - hw - 1, cy - 2); });
    if (L.style === "afro") top(() => { g.moveTo(cx - hw - 2, cy - 4); g.quadraticCurveTo(cx, cy - hh - 2, cx + hw + 2, cy - 4); g.quadraticCurveTo(cx, cy - hh + 8, cx - hw - 2, cy - 4); });
    if (L.style !== "bald") { g.strokeStyle = "rgba(251,243,223,.25)"; g.lineWidth = 1; for (let k = 0; k < 4; k++) { g.beginPath(); g.moveTo(cx - 10 + k * 6, cy - hh - 3); g.quadraticCurveTo(cx - 6 + k * 6, cy - hh, cx - 4 + k * 7, cy - hh + 4); g.stroke(); } }
    /* eyes: almond shapes under a heavy ink lid; they blink and glance */
    const blink = (t + id.length * 900) % 4100 < 130 ? 0.08 : 1, look = Math.sin(t * 0.0007 + id.length) * 1.4, ey = cy + 1;
    for (const d of [-1, 1]) {
      const ex = cx + d * hw * 0.42;
      g.fillStyle = "#fbf6ea"; g.beginPath(); g.moveTo(ex - 6, ey); g.quadraticCurveTo(ex, ey - 5 * blink, ex + 6, ey); g.quadraticCurveTo(ex, ey + 3.6 * blink, ex - 6, ey); g.fill();
      if (blink > 0.5) { g.save(); g.clip(); g.fillStyle = "#3a2412"; g.beginPath(); g.arc(ex + look, ey, 3, 0, Math.PI * 2); g.fill(); g.fillStyle = INK; g.beginPath(); g.arc(ex + look, ey, 1.5, 0, Math.PI * 2); g.fill(); g.fillStyle = "#fff"; g.fillRect(ex + look + 0.6, ey - 1.8, 1.3, 1.3); g.restore(); }
      g.strokeStyle = INK; g.lineWidth = 2.4; g.beginPath(); g.moveTo(ex - 6.5, ey + 0.4); g.quadraticCurveTo(ex, ey - 5.6 * blink, ex + 6.5, ey - 0.4); g.stroke();
      g.lineWidth = 1; g.beginPath(); g.moveTo(ex - 4, ey + 3.4 * blink); g.quadraticCurveTo(ex, ey + 4.2 * blink, ex + 4, ey + 3 * blink); g.stroke();
      /* brows: the mood lives here */
      const br = mood < 0 ? 2.4 : mood > 0 ? -2 : 0, talkUp = talk ? Math.abs(Math.sin(t * 0.004)) * 1.2 : 0;
      g.strokeStyle = L.hair === "#eee" || L.hair === "#e0e0e0" || L.hair === "#9a9aa0" ? "#6a6a70" : L.hair; g.lineWidth = id === "frost" || id === "salado" || id === "sam" ? 3.4 : 2.6;
      g.beginPath(); g.moveTo(ex - 7 * d * -1, ey - 8 - talkUp + (d < 0 ? 0 : 0)); g.quadraticCurveTo(ex, ey - 11 - talkUp - br * 0.3, ex + 7 * d, ey - 8 + br - talkUp); g.stroke();
    }
    /* the nose, each one different */
    g.strokeStyle = INK; g.lineWidth = 1.8; g.beginPath();
    const ny = cy + 3;
    if (H0.nose === "long") { g.moveTo(cx - 1, ny - 4); g.quadraticCurveTo(cx + 5, ny + 6, cx + 3, ny + 11); g.quadraticCurveTo(cx, ny + 13, cx - 3, ny + 11); }
    else if (H0.nose === "hook") { g.moveTo(cx, ny - 5); g.quadraticCurveTo(cx + 7, ny + 2, cx + 4, ny + 10); g.lineTo(cx - 1, ny + 9); }
    else if (H0.nose === "round") { g.moveTo(cx - 2, ny - 2); g.quadraticCurveTo(cx - 1, ny + 4, cx - 5, ny + 7); g.quadraticCurveTo(cx, ny + 12, cx + 5, ny + 7); g.quadraticCurveTo(cx + 2, ny + 4, cx + 2, ny - 2); }
    else if (H0.nose === "button") { g.moveTo(cx - 3, ny + 7); g.quadraticCurveTo(cx, ny + 10, cx + 3, ny + 7); }
    else { g.moveTo(cx + 1, ny - 3); g.lineTo(cx + 3, ny + 8); g.lineTo(cx - 2, ny + 9); }
    g.stroke();
    /* the mouth: an ink line when quiet, open and moving while the line is said */
    const my = cy + hh * 0.62, open = talk ? Math.abs(Math.sin(t * 0.025)) * 3.6 + Math.abs(Math.sin(t * 0.011)) * 2 : 0, mw = 7 + (id === "baako" || id === "rico" ? 2 : 0);
    if (open > 0.6) { g.fillStyle = "#5a1f22"; g.beginPath(); g.moveTo(cx - mw, my); g.quadraticCurveTo(cx, my - 1.5, cx + mw, my); g.quadraticCurveTo(cx, my + open * 2, cx - mw, my); g.fill(); ink(1.8); g.fillStyle = "#e2674f"; g.beginPath(); g.ellipse(cx, my + open * 0.9, mw * 0.45, open * 0.45, 0, 0, Math.PI); g.fill(); }
    else { g.strokeStyle = INK; g.lineWidth = 2; g.beginPath(); g.moveTo(cx - mw, my - mood); g.quadraticCurveTo(cx, my + 3.4 + mood * 3, cx + mw, my - mood); g.stroke(); g.lineWidth = 1.2; g.beginPath(); g.moveTo(cx + mw + 1, my - 2 - mood); g.lineTo(cx + mw - 1, my + 1); g.stroke(); }
    accessories(g, id, L, cx, cy, hw, hh, t, ink);
    g.restore();
    g.setTransform(1, 0, 0, 1, 0, 0);
  }
  function dotsIn(g, x0, y0, x1, y1, step, r, c) { g.fillStyle = c; for (let y = y0; y < y1; y += step) for (let x = x0 + ((y / step) % 2 ? step / 2 : 0); x < x1; x += step) { const k = (x - x0) / (x1 - x0); g.beginPath(); g.arc(x, y, r * k + 0.2, 0, Math.PI * 2); g.fill(); } }
  function torso(g, id, L, ink) {
    if (id === "tobias") { g.fillStyle = "#1f3550"; g.beginPath(); g.moveTo(10, 122); g.bezierCurveTo(12, 96, 30, 86, 52, 85); g.lineTo(60, 104); g.lineTo(68, 85); g.bezierCurveTo(90, 86, 108, 96, 110, 122); g.closePath(); g.fill(); ink(2.2); g.fillStyle = "#e9b44c"; [[60, 110], [60, 118]].forEach(([x, y]) => { g.beginPath(); g.arc(x, y, 2.4, 0, Math.PI * 2); g.fill(); ink(1); }); [[22, 96], [98, 96]].forEach(([x, y]) => { g.beginPath(); g.ellipse(x, y, 12, 4, x < 60 ? 0.4 : -0.4, 0, Math.PI * 2); g.fill(); ink(1.4); }); }
    if (id === "frost" || id === "salado") { const suit = id === "frost" ? "#2a3f66" : "#c0533f"; g.fillStyle = suit; g.beginPath(); g.moveTo(10, 122); g.bezierCurveTo(12, 96, 30, 86, 50, 85); g.lineTo(60, 120); g.lineTo(70, 85); g.bezierCurveTo(90, 86, 108, 96, 110, 122); g.closePath(); g.fill(); ink(2.2); g.fillStyle = id === "frost" ? "#7fb2d0" : "#e9b44c"; g.beginPath(); g.moveTo(57, 92); g.lineTo(63, 92); g.lineTo(64, 116); g.lineTo(60, 120); g.lineTo(56, 116); g.closePath(); g.fill(); ink(1.4); if (id === "salado") { g.fillStyle = "#fbf3df"; g.beginPath(); g.moveTo(32, 100); g.lineTo(38, 96); g.lineTo(40, 103); g.closePath(); g.fill(); ink(1.2); } }
    if (id === "rico" || id === "baako") { g.fillStyle = id === "rico" ? "#fbf3df" : "#2f6440"; for (let k = 0; k < 9; k++) { const x = 22 + (k * 37) % 78, y = 96 + (k * 13) % 22; for (let p = 0; p < 5; p++) { const a = p / 5 * Math.PI * 2; g.beginPath(); g.ellipse(x + Math.cos(a) * 2.4, y + Math.sin(a) * 2.4, 2.2, 1.3, a, 0, Math.PI * 2); g.fill(); } g.fillStyle = id === "rico" ? "#e9b44c" : "#fbf3df"; g.beginPath(); g.arc(x, y, 1.2, 0, Math.PI * 2); g.fill(); g.fillStyle = id === "rico" ? "#fbf3df" : "#2f6440"; } g.fillStyle = L.shirt; g.beginPath(); g.moveTo(48, 86); g.lineTo(60, 102); g.lineTo(72, 86); g.lineTo(66, 85); g.lineTo(60, 94); g.lineTo(54, 85); g.closePath(); g.fill(); ink(1.6); }
    if (id === "hana") { g.fillStyle = "#fbf3df"; g.beginPath(); g.moveTo(46, 86); g.lineTo(60, 96); g.lineTo(74, 86); g.lineTo(70, 98); g.lineTo(60, 100); g.lineTo(50, 98); g.closePath(); g.fill(); ink(1.6); g.fillStyle = "#e9b44c"; g.fillRect(84, 100, 4, 16); g.beginPath(); g.rect(84, 100, 4, 16); ink(1); }
    if (id === "sam") { g.strokeStyle = "rgba(251,243,223,.25)"; g.lineWidth = 1.4; for (let x = 16; x < 106; x += 6) { g.beginPath(); g.moveTo(x, 96); g.lineTo(x + 2, 122); g.stroke(); } g.fillStyle = L.shirt; g.beginPath(); g.ellipse(60, 88, 20, 6, 0, 0, Math.PI * 2); g.fill(); ink(1.8); }
    if (id === "lola") { g.fillStyle = "#e2674f"; g.beginPath(); g.moveTo(40, 122); g.lineTo(44, 98); g.lineTo(76, 98); g.lineTo(80, 122); g.closePath(); g.fill(); ink(1.8); g.strokeStyle = "#e2674f"; g.lineWidth = 3; g.beginPath(); g.moveTo(44, 98); g.lineTo(50, 86); g.moveTo(76, 98); g.lineTo(70, 86); g.stroke(); }
    if (L.acc === "scarf") { g.fillStyle = L.accC; g.beginPath(); g.moveTo(40, 88); g.quadraticCurveTo(60, 98, 80, 88); g.quadraticCurveTo(82, 94, 76, 96); g.lineTo(82, 116); g.lineTo(72, 114); g.lineTo(70, 98); g.quadraticCurveTo(54, 100, 40, 94); g.closePath(); g.fill(); ink(1.8); g.fillStyle = "rgba(251,243,223,.7)"; for (let k = 0; k < 5; k++) { g.beginPath(); g.arc(46 + k * 7, 93 + Math.sin(k) * 1.5, 1.2, 0, Math.PI * 2); g.fill(); } }
  }
  function accessories(g, id, L, cx, cy, hw, hh, t, ink) {
    const A = L.acc;
    if (A === "glasses") { g.strokeStyle = INK; g.lineWidth = 2; [-1, 1].forEach(d => { g.beginPath(); g.rect(cx + d * hw * 0.42 - 7.5, cy - 5, 15, 11); g.stroke(); }); g.beginPath(); g.moveTo(cx - 3, cy - 1); g.lineTo(cx + 3, cy - 1); g.stroke(); g.fillStyle = "rgba(255,255,255,.35)"; [-1, 1].forEach(d => { g.beginPath(); g.moveTo(cx + d * hw * 0.42 - 5, cy + 4); g.lineTo(cx + d * hw * 0.42, cy - 4); g.lineTo(cx + d * hw * 0.42 + 2, cy - 4); g.lineTo(cx + d * hw * 0.42 - 3, cy + 4); g.fill(); }); }
    if (A === "monocle") { g.strokeStyle = "#e9b44c"; g.lineWidth = 2.2; g.beginPath(); g.arc(cx + hw * 0.42, cy + 1, 8, 0, Math.PI * 2); g.stroke(); g.strokeStyle = INK; g.lineWidth = 1; g.stroke(); g.strokeStyle = "#e9b44c"; g.lineWidth = 1.2; g.beginPath(); g.moveTo(cx + hw * 0.42 + 7, cy + 5); g.quadraticCurveTo(cx + hw + 6, cy + 24, cx + hw - 2, cy + 36); g.stroke(); }
    if (A === "mustache") { g.fillStyle = L.accC; g.beginPath(); g.moveTo(cx, cy + 12); g.bezierCurveTo(cx - 6, cy + 9, cx - 16, cy + 10, cx - 20, cy + 6); g.bezierCurveTo(cx - 18, cy + 16, cx - 6, cy + 18, cx, cy + 15); g.bezierCurveTo(cx + 6, cy + 18, cx + 18, cy + 16, cx + 20, cy + 6); g.bezierCurveTo(cx + 16, cy + 10, cx + 6, cy + 9, cx, cy + 12); g.fill(); ink(1.6); }
    if (A === "beard") { g.fillStyle = "#f4efe4"; g.beginPath(); g.moveTo(cx - hw - 1, cy + 2); g.bezierCurveTo(cx - hw, cy + hh + 18, cx - 6, cy + hh + 26, cx, cy + hh + 24); g.bezierCurveTo(cx + 6, cy + hh + 26, cx + hw, cy + hh + 18, cx + hw + 1, cy + 2); g.bezierCurveTo(cx + hw * 0.6, cy + 14, cx + 8, cy + 10, cx, cy + 14); g.bezierCurveTo(cx - 8, cy + 10, cx - hw * 0.6, cy + 14, cx - hw - 1, cy + 2); g.fill(); ink(2); g.strokeStyle = "rgba(34,48,58,.3)"; g.lineWidth = 1; for (let k = -3; k <= 3; k++) { g.beginPath(); g.moveTo(cx + k * 5, cy + 18); g.quadraticCurveTo(cx + k * 6, cy + hh + 6, cx + k * 3, cy + hh + 18); g.stroke(); } g.fillStyle = "#5a1f22"; g.beginPath(); g.ellipse(cx, cy + hh * 0.62, 5, 1.6 + (L.talking || 0), 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = "#1f2a3a"; g.beginPath(); g.moveTo(cx - hw - 6, cy - hh + 8); g.quadraticCurveTo(cx, cy - hh - 18, cx + hw + 6, cy - hh + 8); g.closePath(); g.fill(); ink(2); g.fillStyle = "#1f2a3a"; g.beginPath(); g.ellipse(cx, cy - hh + 8, hw + 10, 4, 0, 0, Math.PI * 2); g.fill(); ink(2); g.fillStyle = "#e9b44c"; g.beginPath(); g.arc(cx, cy - hh, 3, 0, Math.PI * 2); g.fill(); ink(1); }
    if (A === "cap") { g.fillStyle = L.accC; g.beginPath(); g.moveTo(cx - hw - 3, cy - hh + 8); g.quadraticCurveTo(cx - hw - 4, cy - hh - 12, cx + 4, cy - hh - 12); g.quadraticCurveTo(cx + hw + 6, cy - hh - 10, cx + hw + 3, cy - hh + 8); g.closePath(); g.fill(); ink(2); g.fillStyle = INK; g.beginPath(); g.moveTo(cx - hw - 4, cy - hh + 8); g.lineTo(cx + hw + 4, cy - hh + 8); g.quadraticCurveTo(cx + hw + 2, cy - hh + 14, cx, cy - hh + 14); g.quadraticCurveTo(cx - hw - 2, cy - hh + 14, cx - hw - 4, cy - hh + 8); g.fill(); g.fillStyle = "#fbf3df"; g.fillRect(cx - hw - 2, cy - hh + 2, hw * 2 + 4, 4); g.fillStyle = "#e9b44c"; g.beginPath(); g.moveTo(cx, cy - hh - 8); g.lineTo(cx + 4, cy - hh - 2); g.lineTo(cx, cy - hh + 3); g.lineTo(cx - 4, cy - hh - 2); g.closePath(); g.fill(); ink(1); }
    if (A === "straw") { g.fillStyle = "#e9c46a"; g.beginPath(); g.ellipse(cx, cy - hh + 6, hw + 20, 7, 0, 0, Math.PI * 2); g.fill(); ink(2); g.beginPath(); g.moveTo(cx - hw + 2, cy - hh + 5); g.quadraticCurveTo(cx - hw, cy - hh - 16, cx, cy - hh - 16); g.quadraticCurveTo(cx + hw, cy - hh - 16, cx + hw - 2, cy - hh + 5); g.closePath(); g.fill(); ink(2); g.fillStyle = "#e2674f"; g.fillRect(cx - hw + 2, cy - hh - 1, hw * 2 - 4, 5); g.strokeStyle = "rgba(34,48,58,.35)"; g.lineWidth = 1; for (let k = -5; k <= 5; k++) { g.beginPath(); g.moveTo(cx + k * 4, cy - hh - 14); g.lineTo(cx + k * 5, cy - hh + 4); g.stroke(); } }
    if (A === "phones") { g.strokeStyle = INK; g.lineWidth = 5; g.beginPath(); g.arc(cx, cy - 6, hw + 12, Math.PI * 1.08, Math.PI * 1.92); g.stroke(); g.strokeStyle = "#e9b44c"; g.lineWidth = 2.5; g.stroke(); [-1, 1].forEach(d => { g.fillStyle = L.accC; g.beginPath(); g.ellipse(cx + d * (hw + 5), cy + 2, 7, 11, 0, 0, Math.PI * 2); g.fill(); ink(2); g.fillStyle = INK; g.beginPath(); g.ellipse(cx + d * (hw + 6), cy + 2, 3, 6, 0, 0, Math.PI * 2); g.fill(); });
      g.fillStyle = INK; [-1, 1].forEach(d => { g.beginPath(); g.moveTo(cx + d * 2, cy - 4); g.lineTo(cx + d * (hw * 0.42 + 9), cy - 5); g.quadraticCurveTo(cx + d * (hw * 0.42 + 8), cy + 6, cx + d * hw * 0.42, cy + 5); g.quadraticCurveTo(cx + d * 3, cy + 4, cx + d * 2, cy - 4); g.fill(); }); g.fillRect(cx - 3, cy - 4, 6, 2); g.fillStyle = "rgba(127,208,194,.7)"; [-1, 1].forEach(d => { g.beginPath(); g.moveTo(cx + d * (hw * 0.42 + 5), cy - 3); g.lineTo(cx + d * (hw * 0.42 + 2), cy + 2); g.lineTo(cx + d * (hw * 0.42), cy + 2); g.lineTo(cx + d * (hw * 0.42 + 3), cy - 3); g.fill(); }); }
    if (A === "flower") { [["#e889a6", 0], ["#e9b44c", 1]].forEach(([c, j]) => { const fx = cx + hw + 2 - j * 8, fy = cy - hh + 6 + j * 4; g.fillStyle = c; for (let i = 0; i < 5; i++) { const a = i / 5 * Math.PI * 2 + j; g.beginPath(); g.ellipse(fx + Math.cos(a) * 5, fy + Math.sin(a) * 5, 4.5, 3, a, 0, Math.PI * 2); g.fill(); ink(1.2); } g.fillStyle = "#e2674f"; g.beginPath(); g.arc(fx, fy, 2.4, 0, Math.PI * 2); g.fill(); }); g.fillStyle = "#e9b44c"; g.beginPath(); g.arc(cx - hw - 1, cy + 12, 2.6, 0, Math.PI * 2); g.fill(); ink(1); }
    if (A === "scarf") { g.fillStyle = L.accC; g.beginPath(); g.moveTo(cx - hw - 3, cy - 2); g.quadraticCurveTo(cx - hw - 4, cy - hh - 14, cx + 2, cy - hh - 16); g.quadraticCurveTo(cx + hw + 6, cy - hh - 12, cx + hw + 3, cy - 2); g.quadraticCurveTo(cx + hw * 0.5, cy - hh + 2, cx, cy - hh + 3); g.quadraticCurveTo(cx - hw * 0.5, cy - hh + 2, cx - hw - 3, cy - 2); g.fill(); ink(2); g.fillStyle = "rgba(251,243,223,.75)"; for (let k = 0; k < 6; k++) { g.beginPath(); g.arc(cx - 14 + k * 6, cy - hh - 6 + Math.sin(k * 1.3) * 3, 1.3, 0, Math.PI * 2); g.fill(); } g.beginPath(); g.moveTo(cx + hw + 1, cy - hh - 4); g.quadraticCurveTo(cx + hw + 14, cy - hh - 10 + Math.sin(t * 0.003) * 2, cx + hw + 12, cy - hh + 6); g.strokeStyle = L.accC; g.lineWidth = 4; g.stroke(); }
  }
  function shade(hex, k) {
    const n = parseInt(hex.slice(1).padEnd(6, hex.slice(1)), 16), c = [n >> 16 & 255, n >> 8 & 255, n & 255].map(v => Math.max(0, Math.min(255, Math.round(v + (k > 0 ? (255 - v) * k : v * k)))));
    return `rgb(${c[0]},${c[1]},${c[2]})`;
  }
  /* every portrait on screen is redrawn each frame while visible */
  const FACES = new Set();
  function portrait(id, size = 96, mood = 0) {
    const c = el("canvas", { class: "face", width: size * 2, height: size * 2, "aria-hidden": "true" });
    c.style.width = c.style.height = size + "px";
    const f = { c, g: c.getContext("2d"), id, talk: 0, mood }; c._f = f; FACES.add(f); return c;
  }
  SC.onFrame(t => { for (const f of FACES) { if (!f.c.isConnected) { FACES.delete(f); continue; } face(f.g, f.id, t, t < f.talk, f.mood); } });
  const say = (c, ms) => { if (c && c._f) c._f.talk = performance.now() + ms; };

  /* ---------- the game state, kept in this browser ---------- */
  const KEY = "tauhud-rabbit";
  const seeded = s => () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  let G = null;
  function fresh(me) {
    const R = seeded(Date.now() & 0xffffff), sup = {};
    for (const c in CANDS) { sup[c] = {}; PEOPLE.forEach(p => { sup[c][p.id] = 42 + Math.round(R() * 14) + (CANDS[c].cares.some(x => p.cares.includes(x)) ? 6 : 0); }); }
    const trust = {}; for (const c in CANDS) trust[c] = 45;
    return { v: 1, me, day: 1, move: 0, coins: { marisol: 30, tobias: 40, baako: 30, hana: 30 }, sup, trust, laws: [], book: [], pacts: [], deals: [], lies: [], pending: [], news: [], seed: Math.floor(R() * 1e9), onchain: store.get("tauhud-rabbit-chain") === "on", sent: {}, over: null, said: {} };
  }
  const save = () => { if (G) store.set(KEY, JSON.stringify(G)); };
  function load() { try { const g = JSON.parse(store.get(KEY) || "null"); if (g && g.v === 1 && CANDS[g.me]) return g; } catch (e) {} return null; }
  const others = c => Object.keys(CANDS).filter(x => x !== c);
  const nm = c => (CANDS[c] || FOLK[c] || {}).name || c;
  const inForce = id => G.laws.some(l => l.id === id);
  const conflict = id => G.laws.find(l => LAWS[id].no.includes(l.id) || LAWS[l.id].no.includes(id));
  const lawScore = (id, cares) => cares.reduce((s, c) => s + (LAWS[id].fx[c] || 0), 0);
  const pact = (a, b) => G.pacts.some(p => !p.broken && ((p.a === a && p.b === b) || (p.a === b && p.b === a)));
  const total = c => PEOPLE.reduce((s, p) => s + G.sup[c][p.id], 0);
  const leader = () => Object.keys(CANDS).sort((a, b) => total(b) - total(a))[0];
  const bump = (c, who, d) => { PEOPLE.forEach(p => { if (!who || who(p)) G.sup[c][p.id] = Math.max(0, Math.min(100, G.sup[c][p.id] + d)); }); };
  /* the Book: every move signed with the name of whoever made it */
  /* every line in the Book is also a transaction on Tau Testnet Alpha: the visitor's own (signed in their test wallet,
     once they tick the box) and the rivals' (sent by the island bot on the relay, from the rivals' campaign wallets) */
  const write = (who, text, kind) => { const b = { day: G.day, hour: Math.min(2, G.move), who, text, kind }; G.book.push(b); onChain(b); return b; };

  /* ---------- the moves ---------- */
  /* propose a law: the Book checks it against the laws in force first, then the other three vote */
  function propose(by, id) {
    const L = LAWS[id], c = conflict(id);
    G.deals.forEach(d => { if (d.by === by && d.law === id) d.kept = true; });
    if (c) { write(by, F("proposed “{x}”: refused, it contradicts “{y}”, in force since day {n}", { x: T(L.t), y: T(LAWS[c.id].t), n: c.day }), "refused"); return { refused: c }; }
    const votes = {};
    others(by).forEach(v => { votes[v] = v === G.me ? null : aiVote(v, by, id); });
    return { votes };
  }
  function aiVote(v, by, id) {
    if (pact(v, by)) return true;
    const s = lawScore(id, CANDS[v].cares), R = seeded(G.seed + G.day * 31 + id.length * 7 + v.length);
    if (LAWS[id].open) return v !== "tobias" || R() < 0.3;   // more people reading the Book suits everyone except the man with the microphone
    if (s > 0) return true; if (s < 0) return false;
    return leader() !== by && R() < 0.55;
  }
  function settle(by, id, votes) {
    const yes = Object.values(votes).filter(Boolean).length, L = LAWS[id];
    for (const v in votes) { if (v !== G.me && votes[v] != null) { if (pact(v, by) && !votes[v]) breakPact(v, by); } }
    if (yes >= 2) {
      G.laws.push({ id, by, day: G.day });
      PEOPLE.forEach(p => { const d = lawScore(id, p.cares); G.sup[by][p.id] = Math.max(0, Math.min(100, G.sup[by][p.id] + d * 5 + (L.open ? 2 : 0))); for (const v in votes) if (votes[v]) G.sup[v][p.id] = Math.max(0, Math.min(100, G.sup[v][p.id] + d)); });
      write(by, F("passed “{x}”, {n} of 3 in favour", { x: T(L.t), n: yes }), "law");
      return true;
    }
    write(by, F("proposed “{x}”: voted down, {n} of 3 in favour", { x: T(L.t), n: yes }), "down");
    return false;
  }
  function campaign(by, topic, k = 1) {
    const backed = G.laws.some(l => l.by === by && (LAWS[l.id].fx[topic] || 0) > 0);
    bump(by, p => p.cares.includes(topic), Math.round((backed ? 9 : 6) * k));
    write(by, F("spoke on the market square about {x}", { x: T(TOPICS[topic]) }), "talk");
  }
  function rumour(by, about, claim, lie) {
    G.coins[by] -= RUMOUR;
    bump(about, null, lie ? -8 : -6);
    if (!lie) bump(by, p => p.reads, 3);
    G.lies.push({ by, about, claim, lie, day: G.day, seen: [] });
    G.trust[about] = by === G.me ? Math.max(0, G.trust[about] - 30) : G.trust[about];
    write(by, F("paid Radio Coco {n} coins to say: “{x}”", { n: RUMOUR, x: claim }), lie ? "lie" : "fact");
  }
  function deal(by, emb) {
    const E = EMB[emb]; G.coins[by] += E.coins;
    G.deals.push({ by, emb, law: E.wants, day: G.day, kept: false });
    write(by, F("took {n} coins from the {x} and promised to propose “{y}”", { n: E.coins, x: T(E.name), y: T(LAWS[E.wants].t) }), "deal");
  }
  function makePact(a, b, gift) {
    if (gift) { G.coins[a] -= GIFT; G.coins[b] += GIFT; }
    G.pacts.push({ a, b, day: G.day });
    write(a, F("made a pact with {x}: each votes for the other’s laws", { x: nm(b) }) + (gift ? " " + F("({n} coins changed hands)", { n: GIFT }) : ""), "pact");
  }
  function breakPact(a, b) {
    const p = G.pacts.find(p => !p.broken && ((p.a === a && p.b === b) || (p.a === b && p.b === a))); if (!p) return;
    p.broken = true; bump(a, null, -5); if (b === G.me || a === G.me) G.trust[a === G.me ? b : a] = 10;
    write(a, F("broke the pact with {x}", { x: nm(b) }), "broke");
  }
  /* the rumours fade, the Book does not: each morning some people read it (Sam always, more with a copy on the square) */
  function readers() {
    const R = seeded(G.seed + G.day * 977), p = inForce("copy") ? 0.6 : 0.2, out = [];
    PEOPLE.forEach(x => { if (x.reads || R() < p) out.push(x.id); });
    G.lies.forEach(l => {
      if (!l.lie) return;
      out.forEach(id => { if (l.seen.includes(id)) return; l.seen.push(id); G.sup[l.by][id] = Math.max(0, G.sup[l.by][id] - 14); G.sup[l.about][id] = Math.min(100, G.sup[l.about][id] + 6); });
      if (l.seen.length >= 4 && !l.out) { l.out = true; bump(l.by, null, -6); news(F("The Book shows who paid for “{x}”: {y}", { x: l.claim, y: nm(l.by) })); }
    });
    return out.length;
  }
  const news = s => G.news.push({ day: G.day, s });

  /* ---------- the rivals, at night ---------- */
  function night() {
    const R = seeded(G.seed + G.day * 4241);
    for (const c of others(G.me)) {
      const w = CANDS[c].way, lead = leader() === c ? others(c).sort((a, b) => total(b) - total(a))[0] : leader();
      if (w === "rumours" && G.coins[c] >= RUMOUR && R() < 0.8) {
        const lie = R() < 0.65, about = lead === c ? others(c)[0] : lead;
        const claim = lie ? LIES[about] : factAbout(about) || LIES[about];
        rumour(c, about, claim, lie && claim === LIES[about] || !factAbout(about));
        news(F("Radio Coco tonight: “{x}”", { x: claim }));
      } else if (w === "money" && !G.deals.some(d => d.by === c) && R() < 0.9) {
        const e = R() < 0.5 ? "north" : "south"; deal(c, e);
      } else if ((w === "money" || w === "laws") && R() < 0.85) {
        const promised = G.deals.find(d => d.by === c && !d.kept);
        const pick = promised ? promised.law : Object.keys(LAWS).filter(id => !inForce(id) && !conflict(id) && !G.pending.some(p => p.id === id)).sort((a, b) => lawScore(b, CANDS[c].cares) - lawScore(a, CANDS[c].cares))[0];
        if (pick) { G.deals.forEach(d => { if (d.by === c && d.law === pick) d.kept = true; }); G.pending.push({ by: c, id: pick }); }
      } else if (w === "people" || R() < 0.5) {
        campaign(c, CANDS[c].cares[Math.floor(R() * 2)], 0.8);
      }
      if (R() < 0.35 && w !== "rumours") { const p = others(c).filter(x => x !== G.me && !pact(c, x))[0]; if (p && R() < 0.5) makePact(c, p, false); }
      campaign(c, CANDS[c].cares[0], 0.4);
    }
    /* promises due: whoever took embassy money and never proposed the law is found out on the last morning */
    if (G.day === DAYS) G.deals.forEach(d => { if (!d.kept && !d.told) { d.told = true; bump(d.by, null, -8); write(d.emb === "north" ? "frost" : "salado", F("says {x} took the money and never proposed “{y}”", { x: nm(d.by), y: T(LAWS[d.law].t) }), "broke"); news(F("{x}: “{y} took our money and forgot us.”", { x: T(EMB[d.emb].name), y: nm(d.by) })); } });
  }
  /* a true thing one can say about a rival, straight from the Book */
  function factAbout(c) {
    const d = G.deals.find(d => d.by === c); if (d) return F("{x} took {n} coins from the {y}", { x: nm(c), n: EMB[d.emb].coins, y: EMB[d.emb].name });   // the dictionary translates the filling too
    const l = G.lies.find(l => l.by === c && l.lie); if (l) return F("{x} paid for the rumour about {y}", { x: nm(c), y: nm(l.about) });
    const b = G.pacts.find(p => p.broken && p.a === c); if (b) return F("{x} broke a pact", { x: nm(c) });
    return null;
  }

  /* ---------- the screen ---------- */
  const UI = { card: null, cardFace: null, hover: null };
  function hud() {
    $("cvStage").classList.toggle("pre", !G);
    if (!G) return;
    locks();
    $("cvDay").textContent = F("Day {n} of {m}", { n: G.day, m: DAYS });
    $("cvHour").textContent = T(G.move >= MOVES ? "Night" : HOURS[G.move]);
    $("cvMoves").replaceChildren(...Array.from({ length: MOVES }, (_, i) => el("i", { class: i < MOVES - G.move ? "on" : "" })));
    $("cvMoves").setAttribute("aria-label", F("{n} moves left today", { n: Math.max(0, MOVES - G.move) }));
    $("cvCoins").textContent = F("{n} coins", { n: G.coins[G.me] });
    $("cvMe").replaceChildren(portrait(G.me, 30), el("span", { text: nm(G.me) }));
    const last = G.news[G.news.length - 1];
    if (last && last !== DJ.said) { DJ.said = last; onAir([V("book"), Q(last.s)], 1); }
    else if (!DJ.text) $("cvNews").textContent = last ? last.s : T("The Key Crier: five days to the election. Everything anyone does is written in the Book.");
    SC.setHour(G.over ? 2.4 : G.move >= MOVES ? 3 : G.move * 0.9);
    SC.rabbit(G.over || G.move >= MOVES ? null : hint()[0]);
  }
  /* where the white rabbit would go next, and what it would say */
  function hint() {
    if (G.day === 1 && G.move === 0) return ["market", T("Follow me. On the square you hear what people care about.")];
    const opened = unlocks().find(id => !(G.seen || {})[id]);   // a quarter that has just opened
    if (opened) return [opened, F("Something has opened: {x}. This way.", { x: T(SC.places[opened].name) })];
    if (G.book.length > (G.said.book || 0) && G.book.some(b => b.who !== G.me && b.day >= G.day - 1)) return ["book", T("Something new is in the Book. Worth a look; reading costs nothing.")];
    if (!G.laws.some(l => l.by === G.me)) return ["hall", T("You have no law of your own yet. The hall is this way.")];
    if (G.coins[G.me] < RUMOUR && !G.deals.some(d => d.by === G.me)) return ["north", T("Short of coins? The embassies pay, for a promise.")];
    if (!G.pacts.some(p => !p.broken && (p.a === G.me || p.b === G.me))) return ["bar", T("A pact or two would help your laws pass.")];
    return ["market", T("The square again: people forget what they are not reminded of.")];
  }
  function openCard(place, build) {
    closeCard(true);
    if (G && place) { G.seen = G.seen || {}; if (!G.seen[place]) { G.seen[place] = 1; save(); } setTimeout(locks, 0); }
    /* the conversation always sits in the same place: a plate at the bottom middle, the person standing above it */
    const side = 0;
    if (place) { SC.focus(place, side); SND.set({ place, amb: place === "pier" || place === "book" ? 1.7 : place === "market" || place === "bar" ? 1 : 0.6 }); } SC.glow(place);
    const box = el("section", { class: "cv-card talk", role: "dialog", "aria-modal": "false" });
    const close = el("button", { type: "button", class: "cv-x", "aria-label": T("Back to the island"), onclick: () => closeCard(), text: "✕" });
    box.append(close);
    build(box);
    $("cvStage").append(box); UI.card = box; $("cvStage").classList.add("carded");
    SC.hostAt(innerWidth < 760 ? box.offsetTop : null);   // on a phone the one you talk to stands above the sheet
    SND.sfx("open");
    setTimeout(() => { const b = box.querySelector(".cv-acts button:not([disabled])"); if (b && !matchMedia("(pointer: coarse)").matches) b.focus({ preventScroll: true }); }, 50);
  }
  function closeCard(keep) {
    if (UI.card) { UI.card.remove(); UI.card = null; } $("cvStage").classList.remove("carded"); SC.host(null);
    if (!keep) { SC.focus(null); SC.glow(null); SND.set({ radio: false, tense: false, place: null, amb: 1 }); SND.hush(); }
  }
  /* a card: who speaks, what they say (aloud, in their own voice, when the server has the clip), what you can do;
     the buttons are never read out. A line is text, or a list of parts as RICO.speak takes them. */
  function scene(box, who, title, line, acts, extra) {
    const parts = !line ? null : typeof line === "string" ? [{ t: line, v: EN(line) }] : line;
    if (parts) line = join(parts);
    const f = portrait(who, innerWidth < 760 ? 64 : 92, 0);
    SC.host((g, t) => face(g, who, t, t < f._f.talk, f._f.mood, true), !!bustOf(who));   // the one you talk to stands in the room, life-size
    box.append(el("div", { class: "cv-who" }, f, el("div", null, el("b", { translate: "no", text: nm(who) }), el("small", { text: T((CANDS[who] || FOLK[who] || {}).role || "") }))));
    if (title) box.append(el("h3", { text: title }));
    if (line) {
      box.append(el("p", { class: "cv-line", text: line })); say(f, Math.min(4200, 600 + line.length * 38));
      RICO.speak(parts, who).then(secs => { if (secs && UI.card === box) { say(f, secs * 1000); DJ.next = Math.max(DJ.next, performance.now() + secs * 1000 + 20000); } }, () => {});
    }
    if (extra) box.append(extra);
    if (acts) box.append(el("div", { class: "cv-acts" }, acts));
    return f;
  }
  const btn = (text, on, o = {}) => el("button", { type: "button", class: "cv-b" + (o.go ? " go" : "") + (o.warn ? " warn" : ""), disabled: o.off || null, title: o.tip || null, onclick: e => { SND.sfx("tap"); on(e); } }, el("span", { text }), o.sub ? el("small", { text: o.sub }) : null);
  const movesLeft = () => G.move < MOVES && !G.over;
  /* a move is spent: the sun goes on, and after the evening the night comes */
  function spend() {
    G.move++; save(); hud();
    if (G.move >= MOVES) setTimeout(() => { closeCard(); endDay(); }, 900);
  }
  const noMoves = box => box.append(el("p", { class: "cv-note", text: T("That was your last move today. The night comes.") }));

  /* ---------- the places ---------- */
  const PLACE = {
    hall(box) {
      const lines = G.laws.length ? G.laws.map(l => el("li", null, el("b", { text: T(LAWS[l.id].t) }), " ", el("small", { text: F("by {x}, day {n}", { x: nm(l.by), n: l.day }) }))) : [el("li", { class: "dim", text: T("No laws yet. The island runs on habit.") })];
      const list = el("div", { class: "cv-laws" }, el("h4", { text: T("In force") }), el("ul", null, lines));
      const acts = Object.keys(LAWS).filter(id => !inForce(id)).map(id => {
        const c = conflict(id), s = lawScore(id, CANDS[G.me].cares);
        return btn(T(LAWS[id].t), () => doPropose(id), { off: !movesLeft(), sub: c ? F("contradicts “{x}”", { x: T(LAWS[c.id].t) }) : effects(id), warn: !!c });
      });
      scene(box, "ama", T(SC.places.hall.name), T("Pick a law. The other three candidates vote; two yes and it is law. The Book checks it against the laws in force first."), [el("p", { class: "cv-h", text: T("Propose a law (one move)") }), ...acts], list);
    },
    market(box) {
      const rows = PEOPLE.map(p => {
        const mine = G.sup[G.me][p.id], best = Object.keys(CANDS).sort((a, b) => G.sup[b][p.id] - G.sup[a][p.id])[0];
        return el("li", null, el("span", { class: "nm", translate: "no", text: p.name }), el("small", { text: p.cares.map(c => T(TOPICS[c])).join(" · ") }), el("i", { class: "bar" + (best === G.me ? " lead" : ""), style: `--v:${mine}%`, title: F("leans to {x}", { x: nm(best) }) }));
      });
      const acts = Object.keys(TOPICS).map(t => btn(F("Talk about {x}", { x: T(TOPICS[t]) }), () => { campaign(G.me, t); SND.sfx("yes"); SC.gather(1); setTimeout(() => SC.gather(0), 2600); toast(F("People who care about {x} listened.", { x: T(TOPICS[t]) })); spend(); if (UI.card) openCard("market", PLACE.market); }, { off: !movesLeft() }));
      scene(box, G.me === "marisol" ? "lola" : "marisol", T(SC.places.market.name), T("Everyone passes through here. Talk about what people care about; it counts double if you already passed a law for it."), [el("p", { class: "cv-h", text: T("Speak to the square (one move)") }), ...acts], el("ul", { class: "cv-folk" }, rows));
    },
    radio(box) {
      SND.set({ radio: true });
      const acts = [];
      others(G.me).forEach(c => {
        const fact = factAbout(c);
        if (fact) acts.push(btn(fact, () => doRumour(c, fact, false), { off: !movesLeft() || G.coins[G.me] < RUMOUR, sub: T("True: it is in the Book"), go: true }));
        acts.push(btn(LIES[c], () => doRumour(c, LIES[c], true), { off: !movesLeft() || G.coins[G.me] < RUMOUR, sub: T("Not true"), warn: true }));
      });
      scene(box, "rico", T("Radio Coco"), [S("Twenty-five coins and I play anything, baby. I don’t check, I just spin. But the Book writes down who paid me, every time."), Q("You have {n} coins.", { n: G.coins[G.me] })], [el("p", { class: "cv-h", text: F("Put a line on air ({n} coins, one move)", { n: RUMOUR }) }), ...acts]);
    },
    north(box) { embassy(box, "north"); },
    south(box) { embassy(box, "south"); },
    bar(box) {
      const acts = others(G.me).map(c => {
        if (pact(G.me, c)) return btn(F("Pact with {x}", { x: nm(c) }), () => {}, { off: true, sub: T("Already agreed") });
        const t = G.trust[c];
        return btn(F("Offer {x} a pact", { x: nm(c) }), () => doPact(c, false), { off: !movesLeft(), sub: t >= 50 ? T("Likes you") : t >= 30 ? T("Not sure about you") : T("Does not trust you") });
      });
      const gifts = others(G.me).filter(c => !pact(G.me, c)).map(c => btn(F("Offer {x} a pact and {n} coins", { x: nm(c), n: GIFT }), () => doPact(c, true), { off: !movesLeft() || G.coins[G.me] < GIFT }));
      scene(box, "lola", T("Bar La Ola"), T("A pact means you vote for each other’s laws. Break one and the whole island knows by breakfast. Lemonade’s on the house."), [el("p", { class: "cv-h", text: T("Make a pact (one move)") }), ...acts, ...gifts]);
    },
    book(box) {
      G.said.book = G.book.length; save();
      const rows = G.book.slice().reverse().map(b => el("li", { class: "k-" + b.kind }, el("small", { text: F("Day {n}", { n: b.day }) + " · " + T(HOURS[b.hour] || "Night") }), el("span", null, el("b", { translate: "no", text: nm(b.who) }), " ", el("span", { text: b.text }), b.tx && !/^\d+$/.test(b.tx) ? el("a", { class: "cv-tx", href: "/explorer/?tx=" + b.tx, target: "_blank", rel: "noopener", title: T("This line on Tau Testnet Alpha"), text: " ⛓" }) : b.tx || b.bot ? el("span", { class: "cv-tx", title: T("This line went to Tau Testnet Alpha as a transaction"), text: " ⛓" }) : null)));
      scene(box, "sam", T("The Book in the lighthouse"), T(G.book.length ? "Every move on the island is written here with the name of whoever made it. Nobody can tear out a page, not even me. Reading costs nothing." : "Empty, for now. Every move on the island will be written here, with the name of whoever made it. Nobody can tear out a page."), null,
        el("ol", { class: "cv-book" }, rows.length ? rows : [el("li", { class: "dim", text: T("Nothing yet.") })]));
    },
    pier(box) {
      scene(box, G.me === "tobias" ? "sam" : "tobias", T("The pier"), T("Boats, gulls and a black cat that sometimes walks past twice. Nothing to do here but think. Tau Testnet Alpha is out there too: the Book on this island works a lot like its blocks."), [
        btn(T("Watch the sea"), () => { SC.cat(Math.random() < 0.5); setTimeout(() => SND.sfx("meow"), 1200); closeCard(); }),
        btn(T("Read how it works"), () => help()),
      ]);
    },
    /* ---- the other quarters of the painted island ---- */
    school(box) {
      const who = G.me === "hana" ? "sam" : "hana", top = Object.keys(TOPICS).sort((a, b) => PEOPLE.filter(p => p.cares.includes(b)).length - PEOPLE.filter(p => p.cares.includes(a)).length)[0];
      scene(box, who, T(SC.places.school.name), T("Today’s lesson: a promise written where everyone can read it is worth more than one shouted on the radio. The children check the Book before they believe a rumour. Their parents are working on it."), [
        btn(T("Sit in on the lesson"), () => lesson()),
        btn(T("Ask the class what their families care about"), () => { campaign(G.me, top, 0.7); toast(F("Most families here care about {x}. The children will tell them you asked.", { x: T(TOPICS[top]) })); spend(); if (UI.card) openCard("school", PLACE.school); }, { off: !movesLeft(), sub: T("one move") }),
      ]);
    },
    dive(box) {
      const harbour = inForce("harbour");
      scene(box, "kai", T(SC.places.dive.name), T("We dive with Tau sensors. Every reading is signed the moment it is taken, so nobody can say the reef is fine when it is not. Or the other way round. Wetsuits are in the back, sizes small, medium and optimistic."), [
        btn(T("Dive the reef with Kai"), () => { write(G.me, T(harbour ? "dove with Reef Proof: the signed readings show the reef suffering since the deep harbour" : "dove with Reef Proof: the signed readings show a healthy reef, right where the cruise harbour would go"), "fact"); campaign(G.me, "fish", 0.8); toast(T("The readings are in the Book, signed. People who fish took note.")); spend(); if (UI.card) openCard("dive", PLACE.dive); }, { off: !movesLeft(), sub: T("one move") }),
      ]);
    },
    works(box) {
      scene(box, G.me === "baako" ? "noor" : "baako", T(SC.places.works.name), T("Coconuts in, everything out: oil, rope, soap, charcoal and once, by accident, a rather good jazz record. The machine is three bicycles and a church organ. Do not touch the organ."), [
        btn(T("Work a shift (10 coins)"), () => { G.coins[G.me] += 10; write(G.me, T("worked a shift at the Coconut Works: 10 coins, honestly earned"), "talk"); SND.sfx("coin"); toast(T("Ten coins, and you smell of coconut for the rest of the day.")); spend(); if (UI.card) openCard("works", PLACE.works); }, { off: !movesLeft(), sub: T("one move") }),
      ]);
    },
    camp(box) {
      const took = G.deals.filter(d => d.by !== G.me);
      scene(box, "pim", T(SC.places.camp.name), T("We are only measuring. For whom? The embassies. For what? Something deep. We measure, others decide. That is the arrangement, and it pays by the metre."), [
        btn(T("Look at the plans on the table"), () => {
          const line = took.length ? F("saw the surveyors’ plans, paid for by the embassies, with notes from {x}", { x: [...new Set(took.map(d => nm(d.by)))].join(", ") }) : T("saw the surveyors’ plans: nobody has signed for them yet");
          write(G.me, line, "fact"); toast(took.length ? T("The plans show who has been talking to the embassies. It is in the Book now.") : T("Nobody has signed yet. The surveyors look disappointed.")); spend(); if (UI.card) openCard("camp", PLACE.camp);
        }, { off: !movesLeft(), sub: T("one move") }),
      ]);
    },
    ship(box) {
      G.seen = G.seen || {};
      const ready = G.day >= 2;
      scene(box, "wren", T(SC.places.ship.name), T(G.chart ? "The chart is yours now. Mind the waterfall: it is not as solid as it looks." : "Not a pirate, dear. Marine archaeologist, retired. Everything the sea gives back ends up here, labelled: odd socks, a piano key, and a chart nobody can read."), G.chart ? null : [
        btn(T("Ask about the chart"), () => { if (ready) { G.chart = true; save(); toast(T("Wren gives you the chart. It shows a door behind the waterfall.")); } else toast(T("“Come back tomorrow, I am still drying it.”")); if (UI.card) openCard("ship", PLACE.ship); }),
      ]);
    },
    ama(box) {
      scene(box, "ama", T(SC.places.ama.name), T("My grandmother’s grandmother kept the island’s agreements on a stone, long before anyone wrote a Book. People think a record everyone can read is something new. It is the oldest thing we have."), [
        btn(T("Ask about the stone"), () => toast(T(G.day >= 2 ? "“Go to the Tide Stone. It is low tide, it will let you read.”" : "“Tomorrow, at low tide. The stone does not hurry, and neither should you.”"))),
      ]);
    },
    canoe(box) {
      scene(box, "kiko", T(SC.places.canoe.name), T("A canoe is a promise kept by thirty planks. If one of them lies, the sea tells everyone. Same as your Book, really, only wetter."), [
        btn(T("Watch him work"), () => { toast(T("Plank by plank. Nobody hurries a canoe.")); closeCard(); }),
      ]);
    },
    stone(box) {
      scene(box, "ama", T(SC.places.stone.name), T("Each mark is an agreement. Nobody ever chiselled one away, because everyone would see the scar. Your Book in the lighthouse is this stone, made of paper."), [
        btn(T("Read the oldest mark"), () => toast(T("“No new rule may contradict an older one, unless the older one is undone first.” The Book checks every law the same way."))),
      ]);
    },
    drums(box) {
      const lies = G.lies.filter(l => l.lie && !l.out);
      scene(box, "kiko", T(SC.places.drums.name), T("Before Radio Coco, the news went from hill to hill on these drums. They have one rule: they only carry what the stone confirms. That is why nobody ever bribed a drummer."), G.drummed ? null : [
        btn(T("Drum the truth across the island"), () => {
          G.drummed = true; lies.forEach(l => { l.out = true; bump(l.by, null, -8); news(F("The Book shows who paid for “{x}”: {y}", { x: l.claim, y: nm(l.by) })); });
          write(G.me, F("drummed the truth from the three hills: {n} rumours answered", { n: lies.length }), "fact"); SND.sfx("yes"); toast(lies.length ? T("Every rumour still on air has been answered from the hills.") : T("No rumours to answer. The drums play anyway; it is a fine evening.")); spend(); if (UI.card) openCard("drums", PLACE.drums);
        }, { off: !movesLeft(), sub: T("once in the game, one move") }),
      ]);
    },
    circle(box) {
      scene(box, "ama", T(SC.places.circle.name), T("Here a decision stands when nobody in the circle can show that it contradicts what we already agreed. Not when the loudest agrees. Your chain does the same with its rules, I am told."), G.circled ? null : [
        btn(T("Sit in the circle"), () => { G.circled = true; others(G.me).forEach(c => { G.trust[c] = Math.min(100, G.trust[c] + 12); }); save(); toast(T("You listened more than you spoke. The other candidates trust you a little more.")); if (UI.card) openCard("circle", PLACE.circle); }),
      ]);
    },
    grotto(box) {
      scene(box, "ama", T(SC.places.grotto.name), T("So you found it. The key on the old fort opens nothing; it never did. The real key was always this: everyone keeps a copy of what was agreed, so nobody can change it alone."), G.key ? null : [
        btn(T("Take a copy of the Book"), () => { G.key = true; write(G.me, T("found the cave behind the waterfall and took a copy of the Book"), "fact"); bump(G.me, p => p.reads, 6); save(); SND.sfx("yes"); toast(T("You hold the White Rabbit Key.")); if (UI.card) openCard("grotto", PLACE.grotto); }),
      ]);
    },
  };
  /* the quarters that open with time: some only after a visit, none before their day; until then they cannot be clicked */
  const LOCKS = {
    stone: () => G.day >= 2 && (G.seen || {}).ama,
    drums: () => G.day >= 3 && (G.seen || {}).stone,
    circle: () => G.day >= 4 && (G.seen || {}).drums,
    grotto: () => G.day >= 4 && G.chart && (G.seen || {}).circle,
  };
  const unlocks = () => Object.keys(LOCKS).filter(id => SC.places[id] && LOCKS[id]());
  function locks() {
    if (!G) return;
    const shut = Object.keys(LOCKS).filter(id => !LOCKS[id]());
    SC.lock(shut);
    const was = G.opened || [], now = unlocks().filter(id => !was.includes(id));
    if (now.length) { G.opened = was.concat(now); save(); setTimeout(() => toast(F("Something has opened: {x}", { x: now.map(id => T(SC.places[id].name)).join(", ") })), 1200); }
    placeKeys();
  }
  /* places by keyboard: the list under the scene, one button each, for the places this island has and are open */
  function placeKeys() {
    const keys = $("cvPlaces"); if (!keys) return;
    const ids = Object.keys(PLACE).filter(id => SC.places[id] && !SC.locked(id)), sig = ids.join();
    if (keys.dataset.sig === sig) return; keys.dataset.sig = sig; keys.textContent = "";
    ids.forEach(id => keys.append(el("button", { type: "button", onclick: () => { wake(); if (G && !UI.card) openCard(id, PLACE[id]); } }, el("span", { text: T(SC.places[id].name) }))));
  }
  function lesson() {
    const b = $("cvStage").querySelector(".cv-card"); if (!b) return;
    if (b.querySelector(".cv-lesson")) return;
    b.append(el("div", { class: "cv-lesson" }, el("h4", { text: T("On the blackboard") }), el("ul", null,
      el("li", { text: T("The Book is a ledger: every move, with the name of whoever made it, in order.") }),
      el("li", { text: T("A new law is checked against the laws in force; two that cannot both hold are refused.") }),
      el("li", { text: T("Tau Testnet Alpha works the same way with its rules. The test coins have no value: it is a classroom too.") }))));
  }
  function effects(id) {
    const fx = LAWS[id].fx, parts = Object.keys(fx).map(k => (fx[k] > 0 ? "+" : "−") + " " + T(TOPICS[k]));
    return LAWS[id].open ? T("everyone reads the Book more often") : parts.join("  ");
  }
  function embassy(box, e) {
    const E = EMB[e], took = G.deals.find(d => d.by === G.me && d.emb === e);
    const line = took ? F("We are counting on you for “{x}”. We would hate to remind the island in public.", { x: LAWS[E.wants].t }) : F("{n} coins, today. All we ask is that you propose “{x}” before the election. A small thing between friends.", { n: E.coins, x: LAWS[E.wants].t });
    scene(box, E.who, T(E.name), line, took ? [btn(T("Leave"), () => closeCard())] : [
      btn(F("Take the {n} coins and promise", { n: E.coins }), () => { deal(G.me, e); SND.sfx("coin"); toast(T("The promise is in the Book now.")); spend(); if (UI.card) openCard(e, PLACE[e]); }, { off: !movesLeft(), sub: F("people who care about {x} will not like it", { x: Object.keys(LAWS[E.wants].fx).filter(k => LAWS[E.wants].fx[k] < 0).map(k => T(TOPICS[k])).join(", ") }) }),
      btn(T("Politely decline"), () => closeCard()),
    ]);
  }
  function doPropose(id) {
    const r = propose(G.me, id);
    if (r.refused) {
      SND.sfx("no");
      openCard("hall", box => scene(box, "sam", T("Refused before any vote"), [Q("“{x}” contradicts “{y}”, which is in force.", { x: T(LAWS[id].t), y: T(LAWS[r.refused.id].t) }), S("Two laws that cannot both hold would leave the island not knowing what is allowed, so the Book will not take it. Repeal the old one first, or pick another law.")], [btn(F("Propose repealing “{x}”", { x: T(LAWS[r.refused.id].t) }), () => doRepeal(r.refused.id), { off: G.move + 1 >= MOVES + 1 }), btn(T("Back to the hall"), () => openCard("hall", PLACE.hall))]));
      spend(); return;
    }
    vote(G.me, id, r.votes);
  }
  function doRepeal(id) {
    const ys = others(G.me).filter(v => pact(v, G.me) || lawScore(id, CANDS[v].cares) <= 0).length;
    if (ys >= 2) { G.laws = G.laws.filter(l => l.id !== id); write(G.me, F("repealed “{x}”, {n} of 3 in favour", { x: T(LAWS[id].t), n: ys }), "law"); SND.sfx("yes"); toast(T("Repealed.")); }
    else { write(G.me, F("tried to repeal “{x}”: voted down", { x: T(LAWS[id].t) }), "down"); SND.sfx("no"); toast(T("The council kept it.")); }
    spend(); if (UI.card && G.move < MOVES) openCard("hall", PLACE.hall);
  }
  /* the vote: three faces, three thumbs, one by one */
  function vote(by, id, votes, after) {
    SND.set({ tense: true });
    openCard("hall", box => {
      box.classList.add("locked");
      box.append(el("h3", { text: T("The council votes") }), el("p", { class: "cv-line", text: T(LAWS[id].t) }), el("p", { class: "cv-note", text: F("Proposed by {x}. Two of three make it law.", { x: nm(by) }) }));
      const row = el("div", { class: "cv-votes" });
      const vs = Object.keys(votes);
      vs.forEach(v => row.append(el("figure", { id: "vt-" + v }, portrait(v, 64), el("figcaption", { translate: "no", text: nm(v) }), el("b", { class: "th", text: "…" }))));
      box.append(row);
      const acts = el("div", { class: "cv-acts" }); box.append(acts);
      let i = 0;
      const next = () => {
        if (i >= vs.length) return finish();
        const v = vs[i++];
        if (votes[v] == null) {   // the player's own vote on a rival's law
          acts.replaceChildren(el("p", { class: "cv-h", text: pact(v, by) ? F("You have a pact with {x}.", { x: nm(by) }) : T("Your vote") }), btn(T("Yes"), () => { votes[v] = true; mark(v, true); acts.replaceChildren(); setTimeout(next, 500); }, { go: true }), btn(T("No"), () => { votes[v] = false; mark(v, false); acts.replaceChildren(); setTimeout(next, 500); }));
          return;
        }
        mark(v, votes[v]); setTimeout(next, 700);
      };
      const mark = (v, y) => { const f = $("vt-" + v); if (!f) return; f.classList.add(y ? "yes" : "no"); f.querySelector(".th").textContent = y ? "✓" : "✕"; SND.sfx(y ? "yes" : "no"); const c = f.querySelector("canvas"); if (c && c._f) c._f.mood = y ? 1 : -1; };
      const finish = () => {
        const ok = settle(by, id, votes);
        for (const v in votes) if (votes[v] != null) onChain({ who: v, kind: "vote", text: F("voted {x} on “{y}”", { x: T(votes[v] ? "yes" : "no"), y: T(LAWS[id].t) }) });
        if (by !== G.me) { for (const v in votes) if (v === G.me) G.trust[by] = Math.max(0, Math.min(100, G.trust[by] + (votes[v] ? 15 : -10))); if (pact(G.me, by) && !votes[G.me]) breakPact(G.me, by); }
        SND.set({ tense: false }); save(); hud();
        box.classList.remove("locked");
        acts.replaceChildren(el("p", { class: "cv-result " + (ok ? "ok" : "bad"), text: ok ? T("It is law.") : T("Voted down.") }));
        acts.append(btn(T("Continue"), () => { if (after) after(); else if (G.move >= MOVES) { closeCard(); endDay(); } else closeCard(); }, { go: true }));
        if (by === G.me) { G.move++; save(); hud(); }
      };
      setTimeout(next, 600);
    });
  }
  function doRumour(c, claim, lie) {
    rumour(G.me, c, claim, lie); SND.sfx("coin");
    news(F("Radio Coco: “{x}”", { x: claim }));
    /* Rico calls it out on air, loud and happy, then tells you what you bought */
    const aired = [S("This just in on Radio Coco, ninety-seven point three!"), { t: "“" + T(claim) + "”", v: EN(claim) + "!" },
      S(lie ? "Done, it’s out there. Half the island is talking. The other half will read the Book tomorrow, and the Book says you paid me." : "Done. And this one’s true, so let them check. The Book backs you up.")];
    openCard("radio", box => scene(box, "rico", T("On air"), aired, [btn(T("Continue"), () => closeCard())]));
    spend();
  }
  function doPact(c, gift) {
    const ok = gift ? G.trust[c] >= 25 : G.trust[c] >= 50;
    if (ok) { makePact(G.me, c, gift); SND.sfx("yes"); G.trust[c] = Math.min(100, G.trust[c] + 10); }
    else { G.trust[c] = Math.max(0, G.trust[c] - 3); write(G.me, F("offered {x} a pact: turned down", { x: nm(c) }), "down"); SND.sfx("no"); }
    openCard("bar", box => scene(box, c, ok ? T("A pact") : T("No pact"), ok ? T("Fine. I vote for yours, you vote for mine. Lola is our witness, and the Book is our memory.") : T(G.trust[c] < 20 ? "After what you did? Buy yourself a lemonade." : "Not today. Show me how you vote first."), [btn(T("Continue"), () => closeCard())]));
    spend();
  }

  /* ---------- day and night ---------- */
  function endDay() {
    if (!G || G.over || G.move < MOVES || G.counting) return;   // once per night, however many ways lead here
    hud();
    night();
    if (G.day >= DAYS) { save(); return election(); }
    G.day++; G.move = 0;
    const n = readers(); save();
    morning(n);
  }
  function morning(n) {
    hud();
    const today = G.news.filter(x => x.day >= G.day - 1).slice(-4);
    const R = seeded(G.seed + G.day), joke = T(JOKES[Math.floor(R() * JOKES.length)]);
    const box = el("div", { class: "cv-paper" },
      el("p", { class: "mast", text: T("The Key Crier") }), el("p", { class: "date", text: F("Day {n} of {m}", { n: G.day, m: DAYS }) + " · " + F("{n} people read the Book last night", { n }) }),
      el("ul", null, today.length ? today.map(x => el("li", { text: x.s })) : [el("li", { text: T("A quiet night. The fish report no news.") })]),
      el("p", { class: "joke", text: joke }));
    openCard(null, b => { b.classList.add("paper"); b.append(box); const pend = G.pending.splice(0); b.append(el("div", { class: "cv-acts" }, btn(pend.length ? (pend.length === 1 ? T("To the council: one law to vote on") : F("To the council: {n} laws to vote on", { n: pend.length })) : T("Start the day"), () => { if (pend.length) councilQueue(pend); else closeCard(); }, { go: true }))); });
    save();
  }
  /* the rivals' laws come to the council in the morning; you vote on each */
  function councilQueue(list) {
    if (!list.length) { closeCard(); return; }
    const p = list.shift(), r = propose(p.by, p.id);
    if (r.refused) { news(F("{x}’s law “{y}” was refused: it contradicts a law in force", { x: nm(p.by), y: T(LAWS[p.id].t) })); return councilQueue(list); }
    vote(p.by, p.id, r.votes, () => councilQueue(list));
  }
  const JOKES = [
    "Weather: sunny, with a chance of promises.", "Lost: one coconut, answers to nothing.", "The gulls have formed a party. Their programme: more fish.",
    "Rico says he only plays hits. The Book says he plays whatever is paid for.", "Old Sam reminds readers that the Book is open every day and has never once been wrong about who did what.",
    "Classified: honest candidate wanted. Must not mind being written down.", "The black cat was seen crossing the square. Twice. Sam says it is nothing.",
  ];

  /* ---------- Radio Coco: Rico at the microphone, now and then, about what is going on ---------- */
  const DJ = { said: null, text: "", face: null, next: performance.now() + 9000, last: -1 };
  if ($("cvDJ")) { DJ.face = portrait("rico", 40); $("cvDJ").append(DJ.face); }   // Rico is at the microphone from the start, not only once he first speaks
  function onAir(line, urgent) {
    const box = $("cvRadio"); if (!box) return;
    if (!DJ.face) { DJ.face = portrait("rico", 40); $("cvDJ").append(DJ.face); }
    const parts = typeof line === "string" ? [{ t: line, v: null }] : line;
    line = join(parts);
    DJ.text = line; box.classList.add("live");
    const out = $("cvNews"); out.textContent = ""; let i = 0;
    clearInterval(DJ.type); DJ.type = setInterval(() => { i = Math.min(line.length, i + 2); out.textContent = line.slice(0, i); if (i >= line.length) { clearInterval(DJ.type); } }, 28);
    say(DJ.face, Math.min(6000, 700 + line.length * 45));
    if (!urgent) SND.sfx("jingle");
    clearTimeout(DJ.off); DJ.off = setTimeout(() => box.classList.remove("live"), Math.min(9000, 2500 + line.length * 60));
    DJ.next = performance.now() + 38000 + Math.random() * 30000;
    /* his voice, when the clips are there: the mouth and the on-air light follow it */
    const said = DJ.text;
    if (UI.card) return;   // someone in the open card is talking to you; the strip only shows it
    RICO.speak(parts).then(secs => {
      if (!secs || DJ.text !== said) return;
      say(DJ.face, secs * 1000);
      clearTimeout(DJ.off); DJ.off = setTimeout(() => box.classList.remove("live"), secs * 1000 + 800);
      DJ.next = Math.max(DJ.next, performance.now() + secs * 1000 + 30000);
    }, () => {});
  }
  /* Rico does not repeat himself: the lines he said lately are remembered in this browser, across visits, and he picks
     from the ones he has not said. A set is a group of lines that can stand in for each other (rico.js SETS). */
  const SAID = (() => { try { const a = JSON.parse(store.get("rabbit-dj-said") || "[]"); return Array.isArray(a) ? a : []; } catch (e) { return []; } })();
  const unsaid = keys => { const k = keys.filter(x => !SAID.includes(x)); return k.length ? k : [keys.slice().sort((a, b) => SAID.indexOf(a) - SAID.indexOf(b))[0]]; };
  const pickLine = keys => { const k = unsaid(keys); return k[Math.floor(Math.random() * k.length)]; };
  const markSaid = k => { const i = SAID.indexOf(k); if (i >= 0) SAID.splice(i, 1); SAID.push(k); SAID.splice(0, Math.max(0, SAID.length - 120)); store.set("rabbit-dj-said", JSON.stringify(SAID)); };
  const one = (set, ...more) => { const k = pickLine(RICO.SETS[set]); return { k, parts: [V(k), ...more] }; };
  /* what Rico can say about the game as it stands, and a few lines from the island's habits */
  function djLines() {
    if (!G) return [];
    const L = [], laws = G.laws, by = {}; laws.forEach(l => (by[l.by] = (by[l.by] || 0) + 1));
    const top = Object.keys(by).sort((a, b) => by[b] - by[a])[0], liesOut = G.lies.filter(l => l.out).length;
    const add = (k, v, ...more) => L.push({ k, parts: [V(k, v), ...more] });
    if (!laws.length) add("noLaws");
    if (top && by[top] >= 2) add("topLaws", { x: nm(top) });
    if (G.pacts.some(p => !p.broken)) { const p = G.pacts.filter(p => !p.broken).slice(-1)[0]; add("pact", { x: nm(p.a), y: nm(p.b) }); }
    if (G.pacts.some(p => p.broken)) add("broken");
    if (G.deals.length) add("envelope");
    if (G.lies.length) add("rumours", null, Q("({n} on air, {m} shown up)", { n: G.lies.length, m: liesOut }));
    ["quiet", "reef", "harbour", "night", "concerts", "copy"].forEach(k => inForce(k) && add(k));
    if (G.move >= MOVES) add("night5");
    add("day", { n: G.day, m: DAYS });
    ["fact", "dedicate", "song", "warm", "sam"].forEach(k => add(k));
    L.push({ k: "tips", parts: [Q("{x}, you have {n} coins.", { x: nm(G.me), n: G.coins[G.me] }), V("tips")] });
    return L;
  }
  /* Rico reads the real testnet (or the simulation, in simulation mode) every minute and a half: the newest blocks and
     the waiting list. From them come the chain weather and the news: what kind of transactions the new blocks hold,
     ghosts (live only: sealed transactions the node still lists as waiting, IDNI #81, counted by the relay), and in
     the simulation the refusals, a consensus switch voted on or in force, and the restart at midnight UTC. */
  const RADAR = { snap: null, busy: false, seen: 0, mode: null, rules: null, ghosts: 0, ghostAt: 0, flagged: {}, news: [] };
  const RANK = ["nowStake", "nowFixed", "toStake", "toFixed", "restart", "midnight", "valIn", "valOut", "feeUp", "feeDown", "rev", "refusedLaw", "whale", "ghost", "ghostHalloween", "ghostAfter", "law", "lawSim", "back", "cosign", "lock", "offerYes", "offer", "refusedOwn", "rule", "cosvote", "lawVote", "burst", "refused"];
  const KIND = { rule_deploy: "rule", approval_request: "cosign", transfer_vote: "cosvote", retractable_transfer: "lock", retract_transfer: "back", rule_offer: "offer", rule_offer_accept: "offerYes", consensus_rule_vote: "lawVote" };
  const txKind = tx => { const t = tx.tx_type || "user_tx"; return t === "user_tx" && tx.operations && tx.operations["0"] ? "rule_deploy" : t; };
  /* the ghosts by the visitor's calendar: fitting in Halloween week, a nuisance in the first week of November, ordinary news otherwise */
  const ghostSeason = () => { const d = new Date(), m = d.getMonth(), day = d.getDate(); return m === 9 && day >= 24 ? "ghostHalloween" : m === 10 && day <= 7 ? "ghostAfter" : "ghost"; };
  function heard(set, h) {
    if (!set) return;
    if (RADAR.news.some(n => n.set === set)) return;
    RADAR.news.push({ set, h, at: performance.now() });
    RADAR.news.sort((a, b) => RANK.indexOf(a.set) - RANK.indexOf(b.set)); RADAR.news.length = Math.min(RADAR.news.length, 6);
  }
  function readChain(done) {
    if (RADAR.busy) return done && done(RADAR.snap);
    const sim = !!(window.TauSim && TauSim.on);
    let ws; try { ws = sim ? TauSim.socket() : new WebSocket("wss://node.tauhud.com"); } catch (e) { return done && done(null); }
    RADAR.busy = true;
    const blocks = new Map(); let pool = null, fin = false;
    const finish = () => {
      if (fin) return; fin = true; RADAR.busy = false; try { ws.close(); } catch (e) {}
      const bs = [...blocks.values()].sort((a, b) => a.header.block_number - b.header.block_number).slice(-12);
      if (!bs.length) return done && done(null);
      const last = bs[bs.length - 1], h = last.header.block_number, ts = Number(last.header.timestamp) || 0;
      const age = ts ? Math.max(0, Date.now() / 1000 - (ts > 1e12 ? ts / 1000 : ts)) / 60 : 0;
      const wait = Array.isArray(pool) ? pool.length : pool && Array.isArray(pool.transactions) ? pool.transactions.length : pool && Array.isArray(pool.mempool) ? pool.mempool.length : 0;
      RADAR.snap = { bs, h, age, wait, sim, at: performance.now() };
      notice(RADAR.snap);
      done && done(RADAR.snap);
    };
    const stop = setTimeout(finish, 7000);
    ws.onopen = () => { ws.send("hello version=1"); setTimeout(() => { try { ws.send("getmempool"); ws.send("getblocks"); } catch (e) {} }, 200); };
    ws.onmessage = ev => {
      let m; try { m = JSON.parse(String(ev.data)); } catch (e) { return; }
      if (m.status !== "ok") return;
      if (m.command === "getmempool") pool = m.data;
      if ((m.command === "getblocks" || m.command === "getblockrange") && m.data && Array.isArray(m.data.blocks)) m.data.blocks.forEach(b => b && b.header && blocks.set(b.header.block_number, b));
      if (pool !== null && blocks.size) { clearTimeout(stop); setTimeout(finish, 300); }
    };
    ws.onerror = () => { clearTimeout(stop); finish(); };
    if (!sim) fetch("https://node.tauhud.com/health-score", { cache: "no-store" }).then(r => (r.ok ? r.json() : null)).then(j => {
      const f = j && (j.factors || []).find(x => x && x.key === "mempool"), n = f && f.value ? +f.value.sealed || 0 : 0;
      // the ghosts make news when they appear; around Halloween, again every twenty minutes while they stay
      if (n > 0 && (!RADAR.ghosts || (ghostSeason() !== "ghost" && performance.now() - RADAR.ghostAt > 1200000))) { RADAR.ghostAt = performance.now(); heard(ghostSeason(), null); }
      RADAR.ghosts = n;
    }, () => {});
  }
  function notice(s) {
    const first = !RADAR.seen;
    if (RADAR.seen && s.h < RADAR.seen - 5) { heard("restart", null); RADAR.seen = 0; }
    const nb = s.bs.filter(b => b.header.block_number > RADAR.seen);
    RADAR.seen = Math.max(RADAR.seen, s.h);
    for (const b of nb) {
      const n = b.header.block_number, txs = b.transactions || [];
      if (txs.length >= 10) heard("burst", n);
      for (const tx of txs) {
        const k = txKind(tx), paid = k === "user_tx" ? ((tx.operations || {})["1"] || []).reduce((a, x) => a + (Number(x && x[2]) || 0), 0) : Number(tx.amount) || 0;
        if (paid >= 100000) heard("whale", n);
        if (KIND[k]) heard(KIND[k], n);
        else if (k === "consensus_rule_update") heard(s.sim ? "lawSim" : "law", n);
      }
      if (s.sim) for (const d of TauSim.chain.dropped(n) || []) heard(d.type === "consensus_rule_update" ? "refusedLaw" : /o5|own rule|its rule/i.test(d.why || "") ? "refusedOwn" : "refused", n);
    }
    if (!s.sim) return;
    /* the simulation's big moments: a consensus switch put to the vote, and the moment it comes into force */
    /* a validator in or out, the base fee up or down, or another rule revision in force */
    const ru = TauSim.chain.rulesAt(s.h), was = RADAR.rules;
    if (was && ru.rev > was.rev) heard(ru.validators.length > was.n ? "valIn" : ru.validators.length < was.n ? "valOut" : ru.fee > was.fee ? "feeUp" : ru.fee < was.fee ? "feeDown" : ru.elig !== was.elig ? null : "rev", s.h);
    RADAR.rules = { rev: ru.rev, n: ru.validators.length, fee: ru.fee, elig: ru.elig };
    const mode = ru.elig;
    if (RADAR.mode && mode !== RADAR.mode) heard(mode === "stake" ? "nowStake" : "nowFixed", s.h);
    RADAR.mode = mode;
    const now = Date.now() / 1000;
    for (const u of TauSim.upcoming() || []) {
      const id = u.kind + ":" + u.at_ts;
      if (RADAR.flagged[id]) continue;
      if ((u.kind === "stake" || u.kind === "fixed") && u.proposed_ts != null && u.proposed_ts <= now && now < u.at_ts) { RADAR.flagged[id] = 1; heard(u.kind === "stake" ? "toStake" : "toFixed", u.proposed_at); }
      if (u.kind === "restart" && u.at_ts - now < 600 && now < u.at_ts) { RADAR.flagged[id] = 1; heard("midnight", null); }
    }
    if (RADAR.news.some(n => /^to/.test(n.set))) RADAR.news = RADAR.news.filter(n => n.set !== "lawSim");   // the switch is that rule change
    if (first) RADAR.news = RADAR.news.filter(n => !/^(now|restart|val|fee|rev)/.test(n.set));   // nothing switched while we were not listening
  }
  /* the chain weather: the newest blocks turned into a forecast, the numbers shown beside it */
  function weather(s) {
    const at = String(s.h), txs = s.bs.reduce((n, b) => n + (b.transactions || []).length, 0);
    const w = [V(s.sim ? "wxSim" : "wxChain")], band = set => { const k = pickLine(RICO.SETS[set]); markSaid(k); w.push(V(k)); };
    if (s.age > 10) { band("fog"); w.push(Q("(last block {y}, {n} minutes ago)", { y: at, n: Math.round(s.age) })); }
    else if (!txs) { band("calm"); w.push(Q("({n} empty blocks, up to block {y})", { n: s.bs.length, y: at })); }
    else { band(txs <= s.bs.length / 2 ? "breeze" : "choppy"); w.push(Q("({n} transactions in the last {m} blocks, up to block {y})", { n: txs, m: s.bs.length, y: at })); }
    const rules = s.bs.filter(b => (b.transactions || []).some(tx => txKind(tx) === "rule_deploy")).map(b => b.header.block_number);
    if (rules.length) w.push(V("rule"), Q("(block {y})", { y: String(rules[rules.length - 1]) }));
    band(s.wait ? "showers" : "clear"); if (s.wait) w.push(Q("({n} waiting)", { n: s.wait }));
    return w;
  }
  /* what comes next on air: first a hello, then news from the chain when there is some (every other line at most),
     the weather every fourth line, and in between the game and the island, never the same line twice in a row */
  const ROT = { n: 0, newsLast: false };
  /* a listener phones in: Rico picks up, the caller asks in their own voice (through the telephone), Rico answers */
  function phoneIn() {
    const keys = RICO.CALLS.map((c, i) => "call:" + i), k = pickLine(keys), [who, q, a] = RICO.CALLS[keys.indexOf(k)];
    const ring = pickLine(RICO.SETS.ring); markSaid(ring);
    return { k, parts: [V(ring), { t: T(q), v: q, who }, { t: T(a), v: a }] };
  }
  /* chain news as a host tells it: big moments with a sting before and a word after, small ones now and then */
  function story(n) {
    const big = /^(now|to|restart|midnight|val|fee|rev|whale)/.test(n.set), l = one(n.set, ...(n.h != null ? [Q("(block {y})", { y: String(n.h) })] : []));
    const bit = set => { const k = pickLine(RICO.SETS[set]); markSaid(k); return V(k); };
    if (big || Math.random() < 0.4) l.parts.unshift(bit("flash"));
    if (big || Math.random() < 0.3) l.parts.push(bit("tag"));
    return l;
  }
  function nextLine() {
    ROT.n++;
    if (ROT.n === 1) { const hr = new Date().getHours(); return one(Math.random() < 0.5 ? "open" : hr >= 5 && hr < 11 ? "morning" : hr < 17 && hr >= 11 ? "afternoon" : hr >= 17 && hr < 22 ? "evening" : "night"); }
    const big = RADAR.news.some(n => /^(now|to|restart|midnight)/.test(n.set));
    if (ROT.n % 4 === 3 && !big && RADAR.snap && performance.now() - RADAR.snap.at < 180000) { ROT.newsLast = false; return { k: null, parts: weather(RADAR.snap) }; }
    RADAR.news = RADAR.news.filter(n => performance.now() - n.at < 600000);
    /* the big moments always go on air; small news only while Rico has not just used up all its lines */
    const recent = SAID.slice(-20), i = RADAR.news.findIndex(n => /^(now|to|restart|midnight)/.test(n.set) || RICO.SETS[n.set].some(k => !recent.includes(k)));
    if (i >= 0 && (!ROT.newsLast || big)) { ROT.newsLast = true; return story(RADAR.news.splice(i, 1)[0]); }
    ROT.newsLast = false;
    /* in between: the game, a joke now and then, the phone-in, Tau corner, a word between songs, the jungle legend, the island's habits */
    const r = Math.random();
    if (r < 0.35) { const L = djLines(), c = unsaid(L.map(l => l.k)), k = c[Math.floor(Math.random() * c.length)]; const l = L.find(x => x.k === k); if (l) return l; }
    const set = r < 0.58 ? "joke" : r < 0.67 ? "call" : r < 0.73 ? "corner" : r < 0.79 ? "segue" : r < 0.86 ? "legend" : "general";
    if (set === "call" && Math.random() < 0.7) return phoneIn();
    return one(set);
  }
  readChain(); setInterval(() => { if (!document.hidden) readChain(); }, 90000);
  setInterval(() => {
    if (!G || G.over || G.counting || document.hidden || performance.now() < DJ.next) return;
    const l = nextLine(); if (!l) return;
    if (l.k) markSaid(l.k);
    onAir(l.parts);
  }, 2000);

  /* ---------- election night ---------- */
  function election() {
    G.counting = true; G.move = MOVES; hud(); SC.setHour(2.6); SC.gather(1);
    SND.set({ tense: true });
    const R = seeded(G.seed + 99), ballots = PEOPLE.map(p => {
      const sc = Object.keys(CANDS).map(c => [c, G.sup[c][p.id] + R() * 4]); sc.sort((a, b) => b[1] - a[1]); return [p, sc[0][0]];
    });
    /* the eleventh ballot belongs to the visitors: it goes to whoever leads the island ballot on the real testnet */
    const vp = visitorsPick(); if (vp) ballots.push([{ name: T("The visitors, by their votes on the testnet") }, vp]);
    const count = {}; Object.keys(CANDS).forEach(c => (count[c] = 0));
    openCard("market", box => {
      box.classList.add("locked");
      box.append(el("h3", { text: T("Election night") }), el("p", { class: "cv-note", text: T(vp ? "Ten ballots from the islanders and one from the visitors of the testnet, counted on the square by Old Sam." : "Ten ballots, counted on the square by Old Sam.") }));
      const row = el("div", { class: "cv-votes four" });
      Object.keys(CANDS).forEach(c => row.append(el("figure", { id: "el-" + c }, portrait(c, 56), el("figcaption", { translate: "no", text: nm(c) }), el("b", { class: "th", text: "0" }))));
      const tape = el("p", { class: "cv-tape", "aria-live": "polite" });
      box.append(row, tape);
      let i = 0;
      const next = () => {
        if (!box.isConnected) return;
        if (i >= ballots.length) return done();
        const [p, c] = ballots[i++]; count[c]++;
        $("el-" + c).querySelector(".th").textContent = String(count[c]); $("el-" + c).classList.add("bump"); setTimeout(() => $("el-" + c) && $("el-" + c).classList.remove("bump"), 300);
        tape.textContent = F("{x} votes for {y}", { x: p.name, y: nm(c) }); SND.sfx("stamp");
        setTimeout(next, 650);
      };
      const done = () => {
        const max = Math.max(...Object.values(count)), top = Object.keys(count).filter(c => count[c] === max);
        let win = top[0];
        if (top.length > 1) { win = top[Math.floor(R() * top.length)]; tape.textContent = F("A tie. The black cat walks past the ballot box of {x}, twice. Sam says that settles it.", { x: nm(win) }); SC.cat(true); SND.sfx("glitch"); setTimeout(() => SND.sfx("meow"), 900); }
        G.over = { win, count, lies: G.lies.filter(l => l.by === G.me && l.lie).length };
        write("sam", F("counted the ballots: {x} is governor of the island", { x: nm(win) }), "law");
        save(); SND.set({ tense: false }); SND.sfx("cheer");
        setTimeout(ending, top.length > 1 ? 4200 : 1600);
      };
      setTimeout(next, 900);
    });
  }
  function ending() {
    const o = G.over, me = G.me, won = o.win === me;
    const [title, text] = won && !o.lies ? [T("Governor of the island"), T("You won on what was true. Everything you did is in the Book, and none of it needs explaining.")]
      : won ? [T("Governor, with a footnote"), T("You won, and the Book shows every rumour you paid for. Nobody can tear out a page, so your term starts with questions.")]
      : [T("Back to the hammock"), F("{x} is governor. Read the Book to see how; every move is there, yours too.", { x: nm(o.win) })];
    SC.gather(0); SC.focus(null);
    openCard(null, box => {
      box.classList.add("end");
      box.append(el("div", { class: "cv-who" }, portrait(o.win, 92, 1), el("div", null, el("small", { text: T("Governor of the island") }), el("b", { translate: "no", text: nm(o.win) }))));
      box.append(el("h3", { text: title }), el("p", { class: "cv-line", text }));
      box.append(el("div", { class: "cv-lesson" }, el("h4", { text: T("What this has to do with Tau") }), el("ul", null,
        el("li", { text: T("Every move here is signed with a name and kept in a Book nobody can edit. Blocks on Tau Testnet Alpha work like that.") }),
        el("li", { text: T("A law that contradicts one in force is refused before anyone votes. Tau checks a new rule against the rules in force in the same way.") }),
        el("li", { text: T("Laws change only when enough people agree. On Tau the users vote on the chain’s rules.") }))));
      const acts = el("div", { class: "cv-acts" });
      acts.append(el("p", { class: "cv-h", text: T("Cast a real vote on the testnet: who should govern the island? 1 test AGRS, no value; every visitor’s vote is counted.") }));
      Object.keys(CANDS).forEach(c => acts.append(chainBtn(c, F("Vote {x}", { x: nm(c) }), F("Key ballot: {x}", { x: nm(c) }))));
      acts.append(ballotEl());
      acts.append(btn(T("Play again"), () => { store.del(KEY); G = null; closeCard(); start(); }, { go: true }), btn(T("Read the Book"), () => openCard("book", PLACE.book)));
      box.append(acts);
    });
  }

  /* ---------- real test transactions, signed in the visitor's own wallet ---------- */
  const BOOK_LIVE = "tauhud-wallet-book-live", WKEY = "tauhud-wallet-key";
  const BOOKNAME = { council: "Key council", marisol: "Key ballot · Marisol", tobias: "Key ballot · Tobias", baako: "Key ballot · Baako", hana: "Key ballot · Hana" };
  function chainBtn(to, label, what) {
    const sent = G && G.sent[to + ":" + G.day];
    const go = e => {
      if (!G.onchain) return openWallet(to, what);
      const b = e.currentTarget; b.disabled = true;
      mySend(ADDR[to], what, h => { if (h) { G.sent[to + ":" + G.day] = true; save(); b.querySelector("span").textContent = T("Sent to the testnet ✓"); setTimeout(readBallot, 75000); } else b.disabled = false; });
    };
    return btn(sent ? T("Sent to the testnet ✓") : label, go, { off: !!sent, sub: T("1 test AGRS from your test wallet, signed by you") });
  }
  /* ---------- the Book on the chain ---------- */
  const CHAIN = { ws: null, wait: new Map(), q: [], busy: false, next: 0, fee: null, made: false };
  function relay() {
    return new Promise(res => {
      if (CHAIN.ws && CHAIN.ws.readyState === 1) return res(CHAIN.ws);
      let ws; try { ws = new WebSocket("wss://node.tauhud.com"); } catch (e) { return res(null); }
      ws.onopen = () => { ws.send("hello version=1"); CHAIN.ws = ws; setTimeout(() => res(ws), 150); };
      ws.onmessage = ev => { let m; try { m = JSON.parse(String(ev.data)); } catch (e) { return; } const q = CHAIN.wait.get(m.command); if (q && q.length) q.shift()(m); };
      ws.onerror = ws.onclose = () => { if (CHAIN.ws === ws) CHAIN.ws = null; res(null); };
    });
  }
  async function ask(cmd, ms = 12000) {
    const ws = await relay(); if (!ws) return null;
    return new Promise(res => {
      const c = cmd.split(" ")[0]; if (!CHAIN.wait.has(c)) CHAIN.wait.set(c, []); const q = CHAIN.wait.get(c); q.push(res);
      try { ws.send(cmd); } catch (e) { res(null); }
      setTimeout(() => { const i = q.indexOf(res); if (i >= 0) { q.splice(i, 1); res(null); } }, ms);
    });
  }
  /* a move made: the visitor's own goes from their wallet when they said so, a rival's to the island bot */
  function onChain(b) {
    if (!G || !CANDS[b.who]) return;
    if (b.who !== G.me) { ask("islandmove " + b.who + " " + b.kind, 8000).then(m => { if (m && m.status === "ok" && m.data && m.data.queued) { b.bot = true; save(); } }); return; }
    if (G.onchain) mySend(ADDR.council, nm(b.who) + " " + b.text, h => { if (h) { b.tx = h; save(); } });
  }
  /* the visitor's test wallet in this browser (the same key /wallet/ uses); made here if there is none yet */
  function myKey() {
    const B = window.TauBLS; if (!B) return null;
    try { const k = JSON.parse(store.get(WKEY) || "null"); if (k && /^[0-9a-f]{64}$/.test(k.sk)) return { sk: B.hexToBytes(k.sk), pk: k.pk || B.bytesToHex(B.pubOf(B.hexToBytes(k.sk))) }; } catch (e) {}
    const skHex = B.bytesToHex(B.keygen()), pk = B.bytesToHex(B.pubOf(B.hexToBytes(skHex)));
    store.set(WKEY, JSON.stringify({ sk: skHex, pk })); CHAIN.made = true;
    toast(T("A test wallet was made for you in this browser. You find it at tauhud.com/wallet/."));
    return { sk: B.hexToBytes(skHex), pk };
  }
  /* Python's json.dumps(sort_keys=True, separators=(",", ":")), what the node signs over */
  const canon = o => Array.isArray(o) ? "[" + o.map(canon).join(",") + "]" : o === null || typeof o !== "object" ? JSON.stringify(o).replace(/[\u007f-\uffff]/g, c => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0")) : "{" + Object.keys(o).sort().map(k => JSON.stringify(k) + ":" + canon(o[k])).join(",") + "}";
  function mySend(to, label, done) { CHAIN.q.push({ to, label, done }); pump(); }
  async function pump() {
    if (CHAIN.busy || !CHAIN.q.length) return;
    CHAIN.busy = true;
    const { to, label, done } = CHAIN.q.shift();
    let hash = null;
    try {
      const k = myKey(); if (!k) throw 0;
      if (CHAIN.fee == null) { const g = await ask("getgovernance"); const m = /o9\[t\]:bv\[24\]\s*=\s*\{\s*#x([0-9a-fA-F]+)/.exec((g && g.data && g.data.consensus_rules) || ""); CHAIN.fee = m ? parseInt(m[1], 16) : 10; }
      const st = await ask("getsequence " + k.pk); if (!st || st.status !== "ok") throw 0;
      const seq = Math.max(st.data.sequence_number || 0, CHAIN.next), tip = st.data.tip_height || 0;
      const tx = { tx_type: "user_tx", sender_pubkey: k.pk, sequence_number: seq, expiration_time: Math.floor(Date.now() / 1000) + 600, expire_at_height: tip + 1000, fee_limit: String(CHAIN.fee * 5), operations: { "1": [[k.pk, to, "1"]] } };
      const d = { sender_pubkey: tx.sender_pubkey, sequence_number: tx.sequence_number, expiration_time: tx.expiration_time, fee_limit: tx.fee_limit, tx_type: tx.tx_type, expire_at_height: tx.expire_at_height, operations: tx.operations };
      tx.signature = window.TauBLS.bytesToHex(window.TauBLS.sign(new TextEncoder().encode(canon(d)), k.sk));
      await ask("via rabbit");
      const r = await ask("sendtx " + JSON.stringify(tx));
      if (r && r.status === "ok" && !(r.data && r.data.ok === false)) {
        hash = (r.data && r.data.tx_hash) || String(Date.now()); CHAIN.next = seq + 1;
        try { const lk = "tauhud-wallet-log-live-" + k.pk, logs = JSON.parse(store.get(lk) || "[]"); logs.unshift({ hash, kind: "pay", label: T("White Rabbit Key") + ": " + label, at: Date.now(), status: "queued", seq, paid: true }); store.set(lk, JSON.stringify(logs.slice(0, 40))); } catch (e) {}
        toast(T("Signed into the testnet: 1 test AGRS from your wallet."));
      } else { CHAIN.next = 0; toast(T("The testnet did not take this move just now; the game goes on.")); }
    } catch (e) { if (G && G.onchain) toast(T("The testnet is out of reach just now; the game goes on.")); }
    CHAIN.busy = false; done && done(hash);
    if (CHAIN.q.length) setTimeout(pump, 400);
  }
  let drawer = null;
  function openWallet(to, what) {
    try { const b = JSON.parse(store.get(BOOK_LIVE) || "[]"); if (Array.isArray(b) && !b.some(c => c && c.addr === ADDR[to])) { b.push({ name: BOOKNAME[to], addr: ADDR[to] }); store.set(BOOK_LIVE, JSON.stringify(b)); } } catch (e) {}
    closeWallet();
    const lang = window.TauI18n && TauI18n.lang !== "en" ? "&lang=" + TauI18n.lang : "";
    const url = "/wallet/?focus=feed&from=rabbit&mode=live&to=" + ADDR[to] + "&amount=1" + lang;
    const before = lastTx();
    const d = el("div", { class: "cv-drawer", role: "dialog", "aria-label": T("Your test wallet") },
      el("div", { class: "dh" }, el("b", { text: what }), el("button", { type: "button", "aria-label": T("Close"), onclick: closeWallet, text: "✕" })),
      el("iframe", { src: url, title: T("Your test wallet") }),
      el("div", { class: "df", text: T("Tau Testnet Alpha. Test AGRS only, they have no value. Nothing is sent until you sign.") }));
    document.body.append(d);
    drawer = { d, t: setInterval(() => { const x = lastTx(); if (x && x !== before) { G.sent[to + ":" + G.day] = true; save(); setTimeout(readBallot, 75000); d.classList.add("ok"); d.append(el("div", { class: "doneflash" }, el("i", { text: "✓" }), el("span", { text: T("Signed and sent. It lands in the next block.") }))); SND.sfx("yes"); setTimeout(closeWallet, 1800); } }, 700) };
  }
  function lastTx() { try { const k = JSON.parse(store.get(WKEY) || "null"); if (!k || !k.pk) return null; const log = JSON.parse(store.get(`tauhud-wallet-log-live-${k.pk}`) || "[]"); return log[0] ? log[0].hash || String(log[0].at) : null; } catch (e) { return null; } }
  function closeWallet() { if (!drawer) return; clearInterval(drawer.t); drawer.d.remove(); drawer = null; if (UI.card && G && G.over) { const o = UI.card; closeCard(true); ending(); } }

  /* ---------- the island ballot on the real testnet: what each ballot box holds, read through the relay ---------- */
  const BAL = { n: {}, state: "wait" };
  function readBallot() {
    let ws; try { ws = new WebSocket("wss://node.tauhud.com"); } catch (e) { BAL.state = "off"; return; }
    const todo = Object.keys(CANDS), stop = setTimeout(() => { try { ws.close(); } catch (e) {} if (BAL.state === "wait") { BAL.state = "off"; ballotLine(); } }, 15000);
    const ask = () => { const c = todo[0]; if (c && ws.readyState === 1) ws.send("getbalance " + ADDR[c]); };
    ws.onopen = () => { ws.send("hello version=1"); setTimeout(ask, 200); };
    ws.onmessage = ev => {
      let m; try { m = JSON.parse(String(ev.data)); } catch (e) { return; }
      if (m.command !== "getbalance") return;
      const d = m.data || {}, c = Object.keys(CANDS).find(k => ADDR[k] === String(d.address || "").toLowerCase());
      if (m.status === "ok" && c) { BAL.n[c] = Math.floor(Number(d.balance) || 0); todo.splice(todo.indexOf(c), 1); }
      if (!todo.length) { BAL.state = "ok"; clearTimeout(stop); try { ws.close(); } catch (e) {} ballotLine(); return; }
      setTimeout(ask, m.status === "ok" ? 300 : 1500);
    };
    ws.onerror = () => { BAL.state = "off"; ballotLine(); };
  }
  /* the visitors' choice: the candidate whose box holds the most, if one leads */
  const visitorsPick = () => { if (BAL.state !== "ok") return null; const s = Object.keys(CANDS).sort((a, b) => (BAL.n[b] || 0) - (BAL.n[a] || 0)); return (BAL.n[s[0]] || 0) > (BAL.n[s[1]] || 0) ? s[0] : null; };
  function ballotLine() {
    document.querySelectorAll(".cv-ballot").forEach(p => {
      if (BAL.state === "wait") { p.textContent = T("Reading the island ballot on the testnet…"); return; }
      if (BAL.state === "off") { p.textContent = T("The testnet is out of reach just now; the island ballot shows here once it answers."); return; }
      p.replaceChildren(el("b", { text: T("Island ballot on the testnet so far:") }), " ", Object.keys(CANDS).map(c => nm(c) + " " + (BAL.n[c] || 0)).join(" · "));
    });
  }
  const ballotEl = () => { const p = el("p", { class: "cv-ballot", "aria-live": "polite" }); setTimeout(ballotLine, 0); return p; };

  /* ---------- the start: pick your candidate ---------- */
  function start() {
    G = load();
    if (G) { hud(); if (G.over) return ending(); if (G.counting) { G.counting = false; return election(); } if (G.move >= MOVES) return endDay(); return; }
    SC.setHour(0, true); hud();
    openCard(null, box => {
      box.classList.add("intro");
      box.append(el("p", { class: "kick", text: T("An island election in five days") }), el("h2", { text: T("White Rabbit Key") }),
        el("p", { class: "cv-line", text: T("Four candidates want to govern the island. Each day you have three moves: propose laws, talk to people, buy a line on the radio, take an embassy’s money, make pacts. Everything anyone does is written into the Book in the lighthouse, where anyone can read it.") }));
      const pick = el("div", { class: "cv-pick" });
      Object.keys(CANDS).forEach(c => pick.append(el("button", { type: "button", class: "cv-cand", onclick: () => begin(c) }, portrait(c, innerWidth < 760 ? 52 : 74), el("b", { translate: "no", text: nm(c) }), el("small", { text: T(CANDS[c].role) }), el("em", { text: T(CANDS[c].pitch) }))));
      box.append(el("p", { class: "cv-h", text: T("Play as") }), pick);
      const chk = el("input", { type: "checkbox", id: "cvChain" }); chk.checked = store.get("tauhud-rabbit-chain") === "on";
      chk.addEventListener("change", () => store.set("tauhud-rabbit-chain", chk.checked ? "on" : "off"));
      box.append(ballotEl());
      box.append(el("label", { class: "cv-chain", for: "cvChain" }, chk, el("span", { text: T("Sign my moves into Tau Testnet Alpha as I make them: 1 test AGRS each from my test wallet in this browser (made for me if I have none). The rivals’ moves go there anyway, from their own campaign wallets.") })));
    });
  }
  function begin(c) {
    G = fresh(c); save();
    news(T("The Key Crier: five days to the election. Everything anyone does is written in the Book."));
    closeCard(); hud();
    toast(T("Tap a place on the island to begin."));
  }
  function help() {
    openCard("pier", box => scene(box, "sam", T("How it works"), T("Three moves a day, five days, then the island votes. Each of the ten islanders cares about two things; laws and talk about those win them over. Rumours work for a day, until people read the Book."), [btn(T("Back to the island"), () => closeCard(), { go: true })],
      el("ul", { class: "cv-help" }, el("li", { text: T("Council Hall: propose a law. Two of the other three candidates must vote yes. A law that contradicts one in force is refused first.") }),
        el("li", { text: T("Market square: talk about a topic. People who care about it move toward you.") }), el("li", { text: T("Radio Coco: pay for a line on air. True lines are safe. Lies come back when people read the Book.") }),
        el("li", { text: T("Embassies: coins now, for a promise to propose their law. Forget it and they tell everyone.") }), el("li", { text: T("Bar La Ola: pacts. Partners vote for each other’s laws.") }),
        el("li", { text: T("The lighthouse: the Book. Free to read, and nobody can change it.") }),
        el("li", { text: T("Election night: the visitors of the site cast an eleventh ballot, for whoever leads the island ballot on the real testnet.") }),
        el("li", { text: T("On the chain: every line in the Book is also a transaction on Tau Testnet Alpha, 1 test AGRS to the island council. The rivals send theirs from their own campaign wallets; yours go from your test wallet if you ticked the box. A ⛓ in the Book marks them.") }))));
  }
  let toastT = 0;
  function toast(s) { const t = $("cvToast"); t.textContent = s; t.classList.add("on"); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("on"), 2600); }

  /* ---------- the cat and the legend ---------- */
  /* Déjà cannot be fed by one person: she eats only on days when at least three wallets agree (agorzilla.com/cat/) */
  function deja() { SND.sfx("meow"); toast(T("Déjà, the café cat, looks at you as if she has seen you before. Nobody can feed her alone: she eats only on days when at least three wallets agree.")); }
  function legend() {
    SND.sfx("tap");
    openCard("canoe", box => scene(box, "kiko", T("A shape in the jungle"), T("You saw him too? The old ones call him Agorzilla. He lives deep in the jungle and grows only in the ways the island votes for. Nobody has a clear photo, everybody has a theory, and the bananas keep disappearing."), [
      btn(T("Follow the footprints"), () => window.open("https://agorzilla.com/", "_blank", "noopener")),
      btn(T("Back to the island"), () => closeCard(), { go: true }),
    ]));
  }

  /* ---------- pointer, keys and sound ---------- */
  function wire() {
    const cv = $("cvScene"), tip = $("cvTip");
    SC.mount(cv);
    const where = e => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    cv.addEventListener("pointermove", e => {
      if (UI.card) { tip.hidden = true; cv.style.cursor = SC.hit(...where(e)) === "deja" ? "pointer" : "default"; return; }
      const id = SC.hit(...where(e)); SC.glow(SC.places[id] ? id : null); cv.style.cursor = id ? "pointer" : "default";
      if (!id) { tip.hidden = true; return; }
      tip.hidden = false; tip.textContent = id === "rabbit" ? T("The white rabbit: follow it") : id === "agorzilla" ? T("Something moves in the jungle") : id === "deja" ? T("Déjà, the café cat") : T(SC.places[id].name);
      const r = $("cvStage").getBoundingClientRect(); tip.style.left = Math.min(r.width - 180, e.clientX - r.left + 14) + "px"; tip.style.top = (e.clientY - r.top + 14) + "px";
    });
    cv.addEventListener("pointerleave", () => { tip.hidden = true; if (!UI.card) SC.glow(null); });
    cv.addEventListener("click", e => {
      wake();
      if (!G) return;
      if (SC.hit(...where(e)) === "deja") { deja(); return; }   // she may sit in a room while its card is open
      if (UI.card) { if (!UI.card.classList.contains("intro") && !UI.card.classList.contains("paper") && !UI.card.classList.contains("end") && !UI.card.classList.contains("locked")) closeCard(); return; }
      const id = SC.hit(...where(e)); tip.hidden = true;
      if (id === "rabbit") { if (G.over || G.move >= MOVES) return; const [to, line] = hint(); toast(line); SND.sfx("tap"); setTimeout(() => openCard(to, PLACE[to]), 700); return; }
      if (id === "agorzilla") { legend(); return; }
      if (id && PLACE[id]) openCard(id, PLACE[id]);
    });
    /* places by keyboard: the list under the scene, one button each */
    placeKeys();
    addEventListener("keydown", e => { if (e.key === "Escape" && UI.card && !UI.card.classList.contains("intro") && !UI.card.classList.contains("locked")) closeCard(); });
    /* the day's last move is spent and nothing is open any more: the night comes, however the last card was left */
    setInterval(() => { if (G && !G.over && G.move >= MOVES && !UI.card && !drawer) { if (G.counting) { G.counting = false; election(); } else endDay(); } }, 1200);
    $("cvHelp").onclick = () => { wake(); help(); };
    $("cvBookBtn").onclick = () => { wake(); if (G) openCard("book", PLACE.book); };
    const sb = $("cvSound");
    const showSound = () => { sb.textContent = SND.on ? "♪ " + T("Sound on") : SND.wanted ? "♪ " + T("Tap for sound") : "♪ " + T("Sound off"); sb.setAttribute("aria-pressed", SND.on ? "true" : "false"); };
    let woke = 0;   // the press that just started the music must not also switch it off
    sb.onclick = e => { e.stopPropagation(); if (Date.now() - woke < 800) return showSound(); if (!SND.on && SND.wanted) SND.start(); else SND.toggle(); showSound(); };
    /* the music starts as the page opens; where the browser holds it back, it starts on the first click, tap or key anywhere */
    const GESTURES = ["pointerdown", "touchstart", "keydown", "click"];
    const wake = () => { if (!SND.on && SND.wanted) { SND.start(); woke = Date.now(); } showSound(); if (SND.on || !SND.wanted) GESTURES.forEach(n => removeEventListener(n, wake, true)); };
    GESTURES.forEach(n => addEventListener(n, wake, true));
    SND.onchange = showSound;
    if (SND.wanted) SND.start();
    showSound();
    const fs = $("cvFull");
    if (document.fullscreenEnabled) fs.onclick = () => { if (document.fullscreenElement) document.exitFullscreen().catch(() => {}); else $("cvStage").requestFullscreen({ navigationUI: "hide" }).catch(() => {}); };
    else fs.hidden = true;
    $("cvReset").onclick = () => { if (confirm(T("Start a new election? This game will be lost."))) { store.del(KEY); G = null; closeCard(); start(); } };
    /* debug: ?rabbit=<place> opens a place, &day= and &move= set the day */
    const q = new URLSearchParams(location.search);
    start();
    if (q.get("rabbit") === "end" && G) { G.over = { win: G.me, count: {}, lies: 0 }; ending(); }
    else if (q.get("rabbit") && G && PLACE[q.get("rabbit")]) openCard(q.get("rabbit"), PLACE[q.get("rabbit")]);
    else if (q.get("rabbit") === "paper" && G) morning(3);
  }
  setTimeout(readBallot, 1200);
  window.COVE_GAME = { get state() { return G; }, begin, endDay, face, open: p => openCard(p, PLACE[p]) };
  wire();
})();

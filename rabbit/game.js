/* White Rabbit Key: a small island politics game. Four candidates, five days, one election.
   Each day you have three moves (morning, noon, evening): propose a law at the Council Hall, talk to people on the
   market square, buy a rumour on Radio Coco, take an embassy's money for a promise, make a pact at Bar La Ola.
   Every move, yours and your rivals', is written into the Book in the lighthouse, and anyone on the island can read it.
   A law that contradicts one in force is refused before anyone votes. A law needs two of the other three candidates.
   Optional: a law you pass and your vote at the end can go to Tau Testnet Alpha as real test transactions (1 test AGRS). */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const T = s => (window.TauI18n ? TauI18n.t(s) : s);
  const F = (s, v) => T(s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m)));
  const SC = window.COVE_SCENE, SND = window.COVE_SOUND;
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

  /* ---------- portraits: painted faces that blink and talk ---------- */
  const looks = id => CANDS[id] || FOLK[id] || { skin: "#c68642", hair: "#222", style: "short", shirt: "#ddd" };
  function face(g, id, t, talk, mood = 0) {
    const L = looks(id), W = g.canvas.width, H = g.canvas.height, s = W / 120;
    g.setTransform(s, 0, 0, s, 0, 0); g.clearRect(0, 0, 120, 120);
    let gr = g.createRadialGradient(60, 40, 10, 60, 60, 80); gr.addColorStop(0, "rgba(255,240,210,.22)"); gr.addColorStop(1, "rgba(255,240,210,0)"); g.fillStyle = gr; g.fillRect(0, 0, 120, 120);
    const bob = Math.sin(t * 0.002) * 0.8;
    g.translate(0, bob);
    /* shoulders */
    g.fillStyle = L.shirt; g.beginPath(); g.moveTo(14, 120); g.quadraticCurveTo(20, 88, 60, 86); g.quadraticCurveTo(100, 88, 106, 120); g.fill();
    g.fillStyle = "rgba(0,0,0,.12)"; g.beginPath(); g.moveTo(60, 86); g.quadraticCurveTo(100, 88, 106, 120); g.lineTo(84, 120); g.quadraticCurveTo(80, 96, 60, 92); g.fill();
    if (L.acc === "scarf") { g.fillStyle = L.accC; g.beginPath(); g.ellipse(60, 90, 22, 7, 0, 0, Math.PI * 2); g.fill(); }
    /* neck and head */
    g.fillStyle = L.skin; g.fillRect(52, 74, 16, 16);
    if (L.style === "curls" || L.style === "bob" || L.style === "bun") { g.fillStyle = L.hair; g.beginPath(); g.ellipse(60, 52, 30, 33, 0, 0, Math.PI * 2); g.fill(); }
    if (L.style === "curls") for (let i = 0; i < 12; i++) { const a = Math.PI * (0.9 + i / 11 * 1.2); g.beginPath(); g.arc(60 + Math.cos(a) * 31, 54 + Math.sin(a) * 33, 7, 0, Math.PI * 2); g.fill(); }
    if (L.style === "afro") { g.fillStyle = L.hair; g.beginPath(); g.arc(60, 42, 32, 0, Math.PI * 2); g.fill(); }
    gr = g.createLinearGradient(36, 0, 84, 0); gr.addColorStop(0, L.skin); gr.addColorStop(1, shade(L.skin, -0.18));
    g.fillStyle = gr; g.beginPath(); g.ellipse(60, 54, 23, 27, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = shade(L.skin, -0.1); g.beginPath(); g.ellipse(37, 56, 4, 6, 0, 0, Math.PI * 2); g.ellipse(83, 56, 4, 6, 0, 0, Math.PI * 2); g.fill();
    /* hair on top */
    g.fillStyle = L.hair;
    if (L.style === "short") { g.beginPath(); g.ellipse(60, 34, 23, 12, 0, Math.PI, 0); g.fill(); }
    if (L.style === "side") { g.beginPath(); g.moveTo(37, 46); g.quadraticCurveTo(40, 24, 64, 26); g.quadraticCurveTo(84, 28, 83, 46); g.quadraticCurveTo(70, 34, 37, 46); g.fill(); }
    if (L.style === "bob") { g.beginPath(); g.moveTo(36, 62); g.quadraticCurveTo(34, 26, 60, 26); g.quadraticCurveTo(86, 26, 84, 62); g.lineTo(80, 62); g.quadraticCurveTo(78, 38, 56, 36); g.quadraticCurveTo(42, 40, 40, 62); g.fill(); }
    if (L.style === "bun") { g.beginPath(); g.arc(60, 22, 9, 0, Math.PI * 2); g.fill(); g.beginPath(); g.ellipse(60, 36, 24, 12, 0, Math.PI, 0); g.fill(); }
    if (L.style === "curls") { g.beginPath(); g.ellipse(60, 33, 24, 11, 0, Math.PI, 0); g.fill(); }
    /* eyes: blink every few seconds, look toward the reader */
    const blink = (t % 3700) < 120 ? 0.1 : 1, look = Math.sin(t * 0.0007) * 1.2;
    for (const x of [51, 69]) {
      g.fillStyle = "#fff"; g.beginPath(); g.ellipse(x, 54, 5, 3.6 * blink, 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = "#2a1a10"; g.beginPath(); g.arc(x + look, 54.5, 2.3 * Math.max(blink, 0.3), 0, Math.PI * 2); g.fill();
      g.fillStyle = "rgba(255,255,255,.8)"; g.fillRect(x + look + 0.6, 53, 1, 1);
    }
    g.strokeStyle = shade(L.hair === "#eee" || L.hair === "#e0e0e0" ? "#999" : L.hair, 0); g.lineWidth = 1.8; g.lineCap = "round";
    const br = mood < 0 ? 2 : mood > 0 ? -1.5 : 0;
    g.beginPath(); g.moveTo(45, 47 + br); g.lineTo(56, 46 - br * 0.5); g.moveTo(64, 46 - br * 0.5); g.lineTo(75, 47 + br); g.stroke();
    /* nose and mouth: the mouth moves while the line is being said */
    g.strokeStyle = shade(L.skin, -0.3); g.lineWidth = 1.4; g.beginPath(); g.moveTo(60, 56); g.quadraticCurveTo(57, 63, 61, 64); g.stroke();
    const open = talk ? Math.abs(Math.sin(t * 0.025)) * 4 + Math.abs(Math.sin(t * 0.011)) * 2 : 0;
    g.fillStyle = "#5a2a2a"; g.beginPath(); g.ellipse(60, 70 + open * 0.2, 7, 1.2 + open, 0, 0, Math.PI * 2); g.fill();
    if (!talk) { g.strokeStyle = shade(L.skin, -0.35); g.lineWidth = 1.6; g.beginPath(); g.moveTo(53, 69); g.quadraticCurveTo(60, 69 + mood * 3 + 1, 67, 69); g.stroke(); }
    /* what they wear */
    if (L.acc === "glasses") { g.strokeStyle = L.accC; g.lineWidth = 1.5; g.strokeRect(44, 50, 13, 9); g.strokeRect(63, 50, 13, 9); g.beginPath(); g.moveTo(57, 54); g.lineTo(63, 54); g.stroke(); }
    if (L.acc === "monocle") { g.strokeStyle = L.accC; g.lineWidth = 1.5; g.beginPath(); g.arc(69, 54, 6.5, 0, Math.PI * 2); g.stroke(); g.beginPath(); g.moveTo(75, 56); g.quadraticCurveTo(80, 70, 76, 84); g.stroke(); }
    if (L.acc === "mustache") { g.fillStyle = L.accC; g.beginPath(); g.ellipse(55, 66, 6, 2.6, 0.2, 0, Math.PI * 2); g.ellipse(65, 66, 6, 2.6, -0.2, 0, Math.PI * 2); g.fill(); }
    if (L.acc === "beard") { g.fillStyle = L.accC; g.beginPath(); g.moveTo(38, 60); g.quadraticCurveTo(42, 92, 60, 92); g.quadraticCurveTo(78, 92, 82, 60); g.quadraticCurveTo(70, 76, 60, 74); g.quadraticCurveTo(50, 76, 38, 60); g.fill(); }
    if (L.acc === "cap") { g.fillStyle = L.accC; g.beginPath(); g.ellipse(60, 33, 26, 10, 0, Math.PI, 0); g.fill(); g.fillRect(34, 32, 52, 5); g.fillStyle = "#111"; g.fillRect(36, 36, 48, 3); g.fillStyle = "#d9b44a"; g.beginPath(); g.arc(60, 28, 3, 0, Math.PI * 2); g.fill(); }
    if (L.acc === "straw") { g.fillStyle = L.accC; g.beginPath(); g.ellipse(60, 34, 36, 7, 0, 0, Math.PI * 2); g.fill(); g.beginPath(); g.ellipse(60, 30, 19, 11, 0, Math.PI, 0); g.fill(); g.fillStyle = "#8a5a2a"; g.fillRect(41, 29, 38, 3); }
    if (L.acc === "phones") { g.strokeStyle = "#222"; g.lineWidth = 4; g.beginPath(); g.arc(60, 50, 27, Math.PI * 1.05, Math.PI * 1.95); g.stroke(); g.fillStyle = L.accC; g.fillRect(31, 46, 8, 14); g.fillRect(81, 46, 8, 14); }
    if (L.acc === "flower") { g.fillStyle = L.accC; for (let i = 0; i < 5; i++) { const a = i / 5 * Math.PI * 2; g.beginPath(); g.arc(80 + Math.cos(a) * 4, 34 + Math.sin(a) * 4, 3.4, 0, Math.PI * 2); g.fill(); } g.fillStyle = "#ffd84a"; g.beginPath(); g.arc(80, 34, 2.4, 0, Math.PI * 2); g.fill(); }
    if (L.acc === "beard" || L.style === "bald") { g.fillStyle = "rgba(255,255,255,.12)"; g.beginPath(); g.ellipse(54, 36, 8, 4, -0.3, 0, Math.PI * 2); g.fill(); }
    g.setTransform(1, 0, 0, 1, 0, 0);
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
  const write = (who, text, kind) => G.book.push({ day: G.day, hour: Math.min(2, G.move), who, text, kind });

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
    const d = G.deals.find(d => d.by === c); if (d) return F("{x} took {n} coins from the {y}", { x: nm(c), n: EMB[d.emb].coins, y: T(EMB[d.emb].name) });
    const l = G.lies.find(l => l.by === c && l.lie); if (l) return F("{x} paid for the rumour about {y}", { x: nm(c), y: nm(l.about) });
    const b = G.pacts.find(p => p.broken && p.a === c); if (b) return F("{x} broke a pact", { x: nm(c) });
    return null;
  }

  /* ---------- the screen ---------- */
  const UI = { card: null, cardFace: null, hover: null };
  function hud() {
    $("cvStage").classList.toggle("pre", !G);
    if (!G) return;
    $("cvDay").textContent = F("Day {n} of {m}", { n: G.day, m: DAYS });
    $("cvHour").textContent = T(G.move >= MOVES ? "Night" : HOURS[G.move]);
    $("cvMoves").replaceChildren(...Array.from({ length: MOVES }, (_, i) => el("i", { class: i < MOVES - G.move ? "on" : "" })));
    $("cvMoves").setAttribute("aria-label", F("{n} moves left today", { n: Math.max(0, MOVES - G.move) }));
    $("cvCoins").textContent = F("{n} coins", { n: G.coins[G.me] });
    $("cvMe").replaceChildren(portrait(G.me, 30), el("span", { text: nm(G.me) }));
    const last = G.news[G.news.length - 1];
    $("cvNews").textContent = last ? last.s : T("The Key Crier: five days to the election. Everything anyone does is written in the Book.");
    SC.setHour(G.over ? 2.4 : G.move >= MOVES ? 3 : G.move * 0.9);
    SC.rabbit(G.over || G.move >= MOVES ? null : hint()[0]);
  }
  /* where the white rabbit would go next, and what it would say */
  function hint() {
    if (G.day === 1 && G.move === 0) return ["market", T("Follow me. On the square you hear what people care about.")];
    if (G.book.length > (G.said.book || 0) && G.book.some(b => b.who !== G.me && b.day >= G.day - 1)) return ["book", T("Something new is in the Book. Worth a look; reading costs nothing.")];
    if (!G.laws.some(l => l.by === G.me)) return ["hall", T("You have no law of your own yet. The hall is this way.")];
    if (G.coins[G.me] < RUMOUR && !G.deals.some(d => d.by === G.me)) return ["north", T("Short of coins? The embassies pay, for a promise.")];
    if (!G.pacts.some(p => !p.broken && (p.a === G.me || p.b === G.me))) return ["bar", T("A pact or two would help your laws pass.")];
    return ["market", T("The square again: people forget what they are not reminded of.")];
  }
  function openCard(place, build) {
    closeCard(true);
    const side = innerWidth < 760 ? 0 : (SC.places[place] && SC.places[place].x > 820 ? -1 : 1);
    if (place) SC.focus(place, side); SC.glow(place);
    const box = el("section", { class: "cv-card" + (side < 0 ? " left" : ""), role: "dialog", "aria-modal": "false" });
    const close = el("button", { type: "button", class: "cv-x", "aria-label": T("Back to the island"), onclick: () => closeCard(), text: "✕" });
    box.append(close);
    build(box);
    $("cvStage").append(box); UI.card = box; $("cvStage").classList.add("carded");
    SND.sfx("open");
    setTimeout(() => { const b = box.querySelector(".cv-acts button:not([disabled])"); if (b && !matchMedia("(pointer: coarse)").matches) b.focus({ preventScroll: true }); }, 50);
  }
  function closeCard(keep) {
    if (UI.card) { UI.card.remove(); UI.card = null; } $("cvStage").classList.remove("carded");
    if (!keep) { SC.focus(null); SC.glow(null); SND.set({ radio: false, tense: false }); }
  }
  /* a card: who speaks, what they say, what you can do */
  function scene(box, who, title, line, acts, extra) {
    const f = portrait(who, innerWidth < 760 ? 64 : 92, 0);
    box.append(el("div", { class: "cv-who" }, f, el("div", null, el("b", { translate: "no", text: nm(who) }), el("small", { text: T((CANDS[who] || FOLK[who] || {}).role || "") }))));
    if (title) box.append(el("h3", { text: title }));
    if (line) { const q = el("p", { class: "cv-line", text: line }); box.append(q); say(f, Math.min(4200, 600 + line.length * 38)); }
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
      scene(box, "hana" === G.me ? "sam" : "hana", T("Council Hall"), T(G.me === "hana" ? "Sam keeps the minutes today. Pick a law; the other three candidates vote, two yes and it is law." : "Pick a law. The other three candidates vote; two yes and it is law. The Book checks it against the laws in force first."), [el("p", { class: "cv-h", text: T("Propose a law (one move)") }), ...acts], list);
    },
    market(box) {
      const rows = PEOPLE.map(p => {
        const mine = G.sup[G.me][p.id], best = Object.keys(CANDS).sort((a, b) => G.sup[b][p.id] - G.sup[a][p.id])[0];
        return el("li", null, el("span", { class: "nm", translate: "no", text: p.name }), el("small", { text: p.cares.map(c => T(TOPICS[c])).join(" · ") }), el("i", { class: "bar" + (best === G.me ? " lead" : ""), style: `--v:${mine}%`, title: F("leans to {x}", { x: nm(best) }) }));
      });
      const acts = Object.keys(TOPICS).map(t => btn(F("Talk about {x}", { x: T(TOPICS[t]) }), () => { campaign(G.me, t); SND.sfx("yes"); SC.gather(1); setTimeout(() => SC.gather(0), 2600); toast(F("People who care about {x} listened.", { x: T(TOPICS[t]) })); spend(); if (UI.card) openCard("market", PLACE.market); }, { off: !movesLeft() }));
      scene(box, "lola", T("Market square"), T("Everyone passes through here. Talk about what people care about; it counts double if you already passed a law for it."), [el("p", { class: "cv-h", text: T("Speak to the square (one move)") }), ...acts], el("ul", { class: "cv-folk" }, rows));
    },
    radio(box) {
      SND.set({ radio: true });
      const acts = [];
      others(G.me).forEach(c => {
        const fact = factAbout(c);
        if (fact) acts.push(btn(fact, () => doRumour(c, fact, false), { off: !movesLeft() || G.coins[G.me] < RUMOUR, sub: T("True: it is in the Book"), go: true }));
        acts.push(btn(LIES[c], () => doRumour(c, LIES[c], true), { off: !movesLeft() || G.coins[G.me] < RUMOUR, sub: T("Not true"), warn: true }));
      });
      scene(box, "rico", T("Radio Coco"), F("Twenty-five coins and I play anything, baby. I don’t check, I just spin. But the Book writes down who paid me, every time. You have {n} coins.", { n: G.coins[G.me] }), [el("p", { class: "cv-h", text: F("Put a line on air ({n} coins, one move)", { n: RUMOUR }) }), ...acts]);
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
      const rows = G.book.slice().reverse().map(b => el("li", { class: "k-" + b.kind }, el("small", { text: F("Day {n}", { n: b.day }) + " · " + T(HOURS[b.hour] || "Night") }), el("span", null, el("b", { translate: "no", text: nm(b.who) }), " ", el("span", { text: b.text }))));
      scene(box, "sam", T("The Book in the lighthouse"), T(G.book.length ? "Every move on the island is written here with the name of whoever made it. Nobody can tear out a page, not even me. Reading costs nothing." : "Empty, for now. Every move on the island will be written here, with the name of whoever made it. Nobody can tear out a page."), null,
        el("ol", { class: "cv-book" }, rows.length ? rows : [el("li", { class: "dim", text: T("Nothing yet.") })]));
    },
    pier(box) {
      scene(box, "sam", T("The pier"), T("Boats, gulls and a black cat that sometimes walks past twice. Nothing to do here but think. Tau Testnet Alpha is out there too: the Book on this island works a lot like its blocks."), [
        btn(T("Watch the sea"), () => { SC.cat(Math.random() < 0.5); setTimeout(() => SND.sfx("meow"), 1200); closeCard(); }),
        btn(T("Read how it works"), () => help()),
      ]);
    },
  };
  function effects(id) {
    const fx = LAWS[id].fx, parts = Object.keys(fx).map(k => (fx[k] > 0 ? "+" : "−") + " " + T(TOPICS[k]));
    return LAWS[id].open ? T("everyone reads the Book more often") : parts.join("  ");
  }
  function embassy(box, e) {
    const E = EMB[e], took = G.deals.find(d => d.by === G.me && d.emb === e);
    const line = took ? F("We are counting on you for “{x}”. We would hate to remind the island in public.", { x: T(LAWS[E.wants].t) }) : F("{n} coins, today. All we ask is that you propose “{x}” before the election. A small thing between friends.", { n: E.coins, x: T(LAWS[E.wants].t) });
    scene(box, E.who, T(E.name), line, took ? [btn(T("Leave"), () => closeCard())] : [
      btn(F("Take the {n} coins and promise", { n: E.coins }), () => { deal(G.me, e); SND.sfx("coin"); toast(T("The promise is in the Book now.")); spend(); if (UI.card) openCard(e, PLACE[e]); }, { off: !movesLeft(), sub: F("people who care about {x} will not like it", { x: Object.keys(LAWS[E.wants].fx).filter(k => LAWS[E.wants].fx[k] < 0).map(k => T(TOPICS[k])).join(", ") }) }),
      btn(T("Politely decline"), () => closeCard()),
    ]);
  }
  function doPropose(id) {
    const r = propose(G.me, id);
    if (r.refused) {
      SND.sfx("no");
      openCard("hall", box => scene(box, "sam", T("Refused before any vote"), F("“{x}” contradicts “{y}”, which is in force. Two laws that cannot both hold would leave the island not knowing what is allowed, so the Book will not take it. Repeal the old one first, or pick another law.", { x: T(LAWS[id].t), y: T(LAWS[r.refused.id].t) }), [btn(F("Propose repealing “{x}”", { x: T(LAWS[r.refused.id].t) }), () => doRepeal(r.refused.id), { off: G.move + 1 >= MOVES + 1 }), btn(T("Back to the hall"), () => openCard("hall", PLACE.hall))]));
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
        if (by !== G.me) { for (const v in votes) if (v === G.me) G.trust[by] = Math.max(0, Math.min(100, G.trust[by] + (votes[v] ? 15 : -10))); if (pact(G.me, by) && !votes[G.me]) breakPact(G.me, by); }
        SND.set({ tense: false }); save(); hud();
        box.classList.remove("locked");
        acts.replaceChildren(el("p", { class: "cv-result " + (ok ? "ok" : "bad"), text: ok ? T("It is law.") : T("Voted down.") }));
        if (ok && by === G.me && G.onchain) acts.append(chainBtn("council", T("Sign it into the testnet too"), F("Law passed on the island: {x}", { x: T(LAWS[id].t) })));
        acts.append(btn(T("Continue"), () => { if (after) after(); else if (G.move >= MOVES) { closeCard(); endDay(); } else closeCard(); }, { go: true }));
        if (by === G.me) { G.move++; save(); hud(); }
      };
      setTimeout(next, 600);
    });
  }
  function doRumour(c, claim, lie) {
    rumour(G.me, c, claim, lie); SND.sfx("coin");
    news(F("Radio Coco: “{x}”", { x: claim }));
    openCard("radio", box => scene(box, "rico", T("On air"), lie ? T("Done, it’s out there. Half the island is talking. The other half will read the Book tomorrow, and the Book says you paid me.") : T("Done. And this one’s true, so let them check. The Book backs you up."), [btn(T("Continue"), () => closeCard())]));
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
    return btn(sent ? T("Sent to the testnet ✓") : label, () => openWallet(to, what), { off: !!sent, sub: T("1 test AGRS from your test wallet, signed by you") });
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
      box.append(el("label", { class: "cv-chain", for: "cvChain" }, chk, el("span", { text: T("Also sign my laws and my final vote on Tau Testnet Alpha (1 test AGRS each, from my test wallet in this browser)") })));
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
        el("li", { text: T("Election night: the visitors of the site cast an eleventh ballot, for whoever leads the island ballot on the real testnet.") }))));
  }
  let toastT = 0;
  function toast(s) { const t = $("cvToast"); t.textContent = s; t.classList.add("on"); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("on"), 2600); }

  /* ---------- pointer, keys and sound ---------- */
  function wire() {
    const cv = $("cvScene"), tip = $("cvTip");
    SC.mount(cv);
    const where = e => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    cv.addEventListener("pointermove", e => {
      if (UI.card) { tip.hidden = true; return; }
      const id = SC.hit(...where(e)); SC.glow(id === "rabbit" ? null : id); cv.style.cursor = id ? "pointer" : "default";
      if (!id) { tip.hidden = true; return; }
      tip.hidden = false; tip.textContent = id === "rabbit" ? T("The white rabbit: follow it") : T(SC.places[id].name);
      const r = $("cvStage").getBoundingClientRect(); tip.style.left = Math.min(r.width - 180, e.clientX - r.left + 14) + "px"; tip.style.top = (e.clientY - r.top + 14) + "px";
    });
    cv.addEventListener("pointerleave", () => { tip.hidden = true; if (!UI.card) SC.glow(null); });
    cv.addEventListener("click", e => {
      wake();
      if (!G) return;
      if (UI.card) { if (!UI.card.classList.contains("intro") && !UI.card.classList.contains("paper") && !UI.card.classList.contains("end") && !UI.card.classList.contains("locked")) closeCard(); return; }
      const id = SC.hit(...where(e)); tip.hidden = true;
      if (id === "rabbit") { if (G.over || G.move >= MOVES) return; const [to, line] = hint(); toast(line); SND.sfx("tap"); setTimeout(() => openCard(to, PLACE[to]), 700); return; }
      if (id && PLACE[id]) openCard(id, PLACE[id]);
    });
    /* places by keyboard: the list under the scene, one button each */
    const keys = $("cvPlaces");
    Object.keys(PLACE).forEach(id => keys.append(el("button", { type: "button", onclick: () => { wake(); if (G && !UI.card) openCard(id, PLACE[id]); } }, el("span", { text: T(SC.places[id].name) }))));
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
  window.COVE_GAME = { get state() { return G; }, begin, endDay };
  wire();
})();

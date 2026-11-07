/* White Rabbit Key: a small island politics game. Four candidates, one island week, one election on Sunday.
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
    marisol: { name: "Marisol", role: "Runs the Parasol Café, hears everything first", skin: "#a8693f", hair: "#1d1410", style: "bun", acc: "scarf", accC: "#e8574a", shirt: "#2fb0a8", cares: ["fish", "roads"], way: "rumours",
      pitch: "Talks to everyone, and about everyone." },
    tobias: { name: "Tobias", role: "Harbour master, friend of every embassy", skin: "#e0b08a", hair: "#9a9aa0", style: "side", acc: "cap", accC: "#1f3550", shirt: "#f4f1ea", cares: ["visitors", "music"], way: "money",
      pitch: "Gives every ambassador a ceremony, and every envelope a warm welcome." },
    baako: { name: "Baako", role: "Founder of the coconut co-op, counts everything", skin: "#5a3620", hair: "#111", style: "short", acc: "straw", accC: "#d9b45a", shirt: "#f2b134", cares: ["visitors", "roads"], way: "people",
      pitch: "Knows the price of every coconut and every promise." },
    hana: { name: "Hana", role: "Schoolteacher, writes everything down", skin: "#f0cfa8", hair: "#222", style: "bob", acc: "glasses", accC: "#333", shirt: "#6f8cff", cares: ["school", "quiet"], way: "laws",
      pitch: "Believes a good law beats a good speech." },
  };
  const FOLK = {
    rico: { name: "Rico", role: "DJ on Radio Coco", skin: "#7a4a2a", hair: "#111", style: "afro", acc: "phones", accC: "#e8574a", shirt: "#e86fa0" },
    frost: { name: "Ambassador Frost", role: "North Wind Embassy", skin: "#f3d6c0", hair: "#e0e0e0", style: "side", acc: "monocle", accC: "#d9b44a", shirt: "#3b5f8a" },
    salado: { name: "Salado", role: "South Current Wellness Resort, investor", skin: "#c68642", hair: "#3a2a1a", style: "side", acc: "mustache", accC: "#3a2a1a", shirt: "#c0533f" },
    lola: { name: "Lola", role: "Runs Bar La Ola", skin: "#8d5524", hair: "#5a1a1a", style: "curls", acc: "flower", accC: "#ff6f91", shirt: "#fff6e6" },
    sam: { name: "Old Sam", role: "Keeper of the lighthouse and the Book", skin: "#c9a27a", hair: "#eee", style: "bald", acc: "beard", accC: "#eee", shirt: "#2a2a30" },
    /* the people of the island's other quarters (a painted island with a layout that has them, infra/rabbit-art) */
    ama: { name: "Ama", role: "Elder of the first people", skin: "#5a3620", hair: "#dcdcdc", style: "bun", acc: "glasses", accC: "#333", shirt: "#2f6440" },
    wren: { name: "Captain Wren", role: "Marine archaeologist, retired", skin: "#e0b08a", hair: "#b0502a", style: "bob", acc: "cap", accC: "#1f3550", shirt: "#3aa6a0" },
    kai: { name: "Kai", role: "Runs the Reef Proof dive centre", skin: "#c68642", hair: "#111", style: "short", acc: "glasses", accC: "#333", shirt: "#4fd1c5" },
    pim: { name: "Pim", role: "Surveyor, measures for the embassies", skin: "#f3d6c0", hair: "#c9a46a", style: "side", acc: "straw", accC: "#d9b45a", shirt: "#f4f1ea" },
    noor: { name: "Noor", role: "Runs the Coconut Works; Baako’s co-op brings the coconuts", skin: "#a8693f", hair: "#1d1410", style: "curls", acc: "glasses", accC: "#333", shirt: "#e9b44c" },
    kiko: { name: "Kiko", role: "Builds canoes", skin: "#8d5524", hair: "#111", style: "short", acc: "none", shirt: "#e85d4a" },
    tano: { name: "Tano", role: "Keeps the drums and the circle", skin: "#4a2c1a", hair: "#9a9a9a", style: "short", acc: "beard", accC: "#bdbdbd", shirt: "#c9772e" },
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
    south: { who: "salado", name: "South Current Wellness Resort", wants: "road", coins: 35,
      offer: "Sit, sit, the lounger is free. So, straight to business: {n} coins, today, and you propose “{x}” before the election. Right now my guests drag their suitcases uphill from the pier, and last week a yoga teacher cried.",
      remind: "My investors call me every morning at six and ask the same thing: has our candidate proposed “{x}” yet? Please. Give me something to tell them.",
      done: "No business today, my friend: “{x}” is law already, and there’s nothing left for me to buy. My investors will think I’m on holiday. Sit anyway, the loungers are free." },   // his own words (and talk.js, when you come back); the North Wind keeps the diplomat's
  };
  const DAYS = 7, MOVES = 3, RUMOUR = 25, GIFT = 20;   // a campaign is one island week, Monday to Sunday; the election is Sunday night
  const FIRST_EXTRA = 3;   // the first day of a campaign has six moves, so a first visit is a real game and not three taps; from then on three a day
  /* the island's calendar is the real one: an island day is a real day (Europe/Berlin), three moves each, and the week's
     days not yet played are played in one go. ?today=N pretends it is weekday N (1 Monday … 7 Sunday); ?clock=free lifts
     the lock, so the whole week can be played at once (the sim, and anyone who wants to) */
  const QS = new URLSearchParams(location.search), FREE = QS.get("clock") === "free";
  const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  function berlin() {
    try {
      const P = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Berlin", weekday: "short", hour: "numeric", minute: "numeric", hour12: false, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date()), g = t => (P.find(x => x.type === t) || {}).value;
      const dow = DOW.indexOf(g("weekday")) + 1; if (!dow) throw 0;
      return { dow, h: +g("hour") % 24, m: +g("minute"), y: +g("year"), mo: +g("month"), d: +g("day") };
    } catch (e) { const d = new Date(); return { dow: (d.getDay() + 6) % 7 + 1, h: d.getHours(), m: d.getMinutes(), y: d.getFullYear(), mo: d.getMonth() + 1, d: d.getDate() }; }
  }
  const todayIdx = () => { const f = +QS.get("today"); return f >= 1 && f <= 7 ? f : FREE ? DAYS : berlin().dow; };
  const weekId = () => { const b = berlin(), mon = new Date(Date.UTC(b.y, b.mo - 1, b.d) - (b.dow - 1) * 86400000); return mon.toISOString().slice(0, 10); };
  /* until the next island day, and until the governor's count (Monday 00:00), as "in 2 d 9 h" */
  const untilMidnight = () => { const b = berlin(); return 86400 - (b.h * 3600 + b.m * 60); };
  const spanText = sec => { const d = Math.floor(sec / 86400), h = Math.floor((sec % 86400) / 3600); return d ? Fd("in {n} d {m} h", { n: d, m: h }) : h ? Fd("in {n} h", { n: h }) : T("within the hour"); };
  const HOURS = ["Morning", "Noon", "Evening"], WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  const dayName = d => T(WEEKDAYS[Math.min(DAYS, Math.max(1, d)) - 1]);
  /* real test transactions: four ballot boxes and the council's chest, addresses with no owner behind them */
  const ADDR = {
    council: "96179f47d33ab65d9922c5652d7686f9e6be9d36ef4b9e9e04bdaac25b6e30d01928182c16da7aaa6dc954cccb88b62b",
    marisol: "b44a202e884682b8677daf5f2685b5775f3c9ea9443a89651013bc455bc66061f2cf8d092897893bad3311e598f2cb11",
    tobias: "96bf03fb7c34b84f916d928cf82bd332cd9558ab3c55e9a717381fe5c8cc6d4ec1e694e39855a680ea8f29351d6a2aea",
    baako: "981bfa68b487e86991cbd70d3c1c8ed4b151715031580976f0942610958a16e29d71c15ea4accdb3750db225f35c3f50",
    hana: "adf1b27a6cfe88b1c73f12ed38eaaef535f892ee2f2b695030427ecaef7d4e43deb89f7849f2f5550cc5eec711652174",
  };
  /* each place has its own till on the chain (made like the ballot boxes: no key behind them), so a move pays the place it
     happens at: a line bought on Radio Coco pays the station, a talk on the square the market, an embassy's paper the
     embassy; the Council Hall is the council's chest (infra/relay/island.py PLACES holds the same list) */
  const TILL = {
    market: "89798ff443b446b8392097e50bb61f383f24ed60f45b4f592e6b9d5356056e90698e7114f17692bdd2539bce24d73ac2",
    radio: "b6ef83b962c9e8be7345050bc34de31bc8996cfc3782947db4509f48750b53640b19d7211c591bc2e4e16d2b148bf945",
    north: "b3909c612e07036be9504e3be10eef3b1483e0c1c7be4d05950ccb373f06292f186709c7344e5aa7b83501ce7f1d48af",
    south: "a752d4269c95abd44c6ec855ce3513f6ce8b3a8c94f58621ee1596ceb728a69aa329a541a9f75a188fdfff92ad6c045d",
    bar: "87208cfd4313f66ec1baa2021ff0fdd5667285be5396a4a83480efc18d80ba3c2e41504d2bcd2b01a8d37a6cab54cd05",
    book: "98e2aa832d79c1689b6b3190d45e0c2319838c0f58293e6a837d606548f2c1e797b20550e0c5230a7cebbc13f74e849f",
    pier: "8ed60ef9cc93ec996d7eeac725539e720f86b701bdb7ac646434d177690e48869dbfdedc759c930dc88f1e3cd315c58b",
    school: "98e8a33fa10f0dca59bb6fe8c9d14fb2e9b6be5cbeb95d862fc4eb9ad2d5957617f8b998757f9947065cd76c05a82578",
    dive: "899220e0128f24e1666fdaf53809c16854bc37cfcac3aa9a887e7e0205fff14de93c5b1272e1c5204ad4c1f1ee7c11de",
    works: "816cdcda9accef093332ca8356f87fb1a40aa612d999b55d8cc7229865508ad09bd1214ba6f4b16a6dc8b64d03fa852d",
    camp: "81a080eed60d737f73623b80d3b1dcad85d37b5a5a4d5b0ba60c3c2379b995d470c8c2d3db2f92b803b7feb215091d16",
    ship: "83546df43205836667fc104c6a56549b2b0c0cd5fd0bc188ad55e96ce656c8220991325fdd49ef8a5549bb7ca9d1cb3e",
    ama: "8ffb79523db95c885e3267633767246dda76cc9378804b02328835ba45667d7012be8b79f32e497d1822d1df96726d3d",
    canoe: "96e0c6d33c1848fa6a2355ababc5f66a7a8121c81a05f923c3e60d645f0110fe28a81db5176f750adec25b26b8746bf9",
    stone: "897178ec1333edd5d3cb27f5746976e6cb8fd0d07360a8dcdfccd1f0a90d15f5a2f8b24616acb5ebfa360b86bc025175",
    drums: "82a45ff8fd1bbba834c5c9f89e8ebb712935f83aa2709cdda051deebec517483e73fc6eeb997ebbaf2dc582a2eea56dc",
    circle: "a974149276f73fa2021068c89521bc68e8877cbfdb7d75b348951269bc3ab6c0677997f31bdbb1d28c95dc3aacacd34e",
    grotto: "9266b7dbca59d06c60517e815e32169aaba70056101d394c6ab851a99925f18e23da324cf0c73ab5fe27c951c8bb024e"
  };
  const TILL_AT = { talk: "market", lie: "radio", fact: "book" };   // a rival's move, when it says nothing more
  /* Déjà, the café cat (agorzilla.com/cat/): her bowl has no key behind it; she eats on a day only when three wallets
     pay it at least 1 test AGRS, and her day runs 18:00 to 18:00 UTC (agorilla assets/cat.js). Agreeing from here is one
     real transaction from the player's test wallet: no move, no coins. The relay counts her day (GET /deja). */
  const DEJA = { bowl: "8dbae75034a8cdc776e462f004dd686c8d0a32dbedd400483a026a01db4ce1f78b9d6450d2c832d8116d47a315fd8973", born: 1793383200, need: 3 };
  const tillOf = at => TILL[at] || ADDR.council;

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
  /* how open the mouth is while they talk: from their voice as it is heard (shut in its pauses), or, with no clip
     playing (sound off, a line not voiced yet), null and the face makes its own syllables */
  const lip = (id, talk) => (talk && SND && SND.lip ? SND.lip(id) : null);
  function frame(id, t, talk) {
    const img = SC.art.img, k = "bust-" + id;
    if (talk && img[k + "-talk"]) {
      const m = MOUTH[id] || (MOUTH[id] = { at: 0, open: false }), v = lip(id, talk);
      if (v != null) {   // open on the loud part of a syllable, shut in the gaps; held a few frames so it does not flicker
        if (t >= m.at && (m.open ? v < 0.22 : v > 0.38)) { m.open = !m.open; m.at = t + (m.open ? 70 : 50); }
      } else if (t >= m.at) { m.open = !m.open; m.at = t + (m.open ? 90 + Math.random() * 110 : 60 + Math.random() * 90); }   // syllables of uneven length
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
    const my = cy + hh * 0.62, v = lip(id, talk), open = !talk ? 0 : v != null ? v * 5.6 : Math.abs(Math.sin(t * 0.025)) * 3.6 + Math.abs(Math.sin(t * 0.011)) * 2, mw = 7 + (id === "baako" || id === "rico" ? 2 : 0);
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
  /* bare: the whole figure as it stands in a room (no disc behind it), sized by the page's CSS */
  function portrait(id, size = 96, mood = 0, bare = false) {
    const c = el("canvas", { class: "face", width: size * 2, height: size * 2, "aria-hidden": "true" });
    if (!bare) c.style.width = c.style.height = size + "px";
    const f = { c, g: c.getContext("2d"), id, talk: 0, mood, bare }; c._f = f; FACES.add(f); return c;
  }
  SC.onFrame(t => { for (const f of FACES) { if (!f.c.isConnected) { FACES.delete(f); continue; } face(f.g, f.id, t, t < f.talk, f.mood, f.bare); } });
  const say = (c, ms) => { if (c && c._f) c._f.talk = performance.now() + ms; };

  /* ---------- the game state, kept in this browser ---------- */
  const KEY = "tauhud-rabbit";
  const seeded = s => () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  let G = null;
  function fresh(me) {
    const R = seeded(Date.now() & 0xffffff), sup = {};
    for (const c in CANDS) { sup[c] = {}; PEOPLE.forEach(p => { sup[c][p.id] = 42 + Math.round(R() * 14) + (CANDS[c].cares.some(x => p.cares.includes(x)) ? 6 : 0); }); }
    const trust = {}; for (const c in CANDS) trust[c] = 45;
    return { v: 1, me, day: 1, move: 0, coins: { marisol: 40, tobias: 30, baako: 30, hana: 30 }, sup, trust, laws: [], book: [], pacts: [], deals: [], lies: [], pending: [], news: [], seed: Math.floor(R() * 1e9), onchain: true, sent: {}, over: null, said: {}, amb: null, declined: [], week: weekId(), waiting: false, spare: FIRST_EXTRA };
  }
  const save = () => { if (G) store.set(KEY, JSON.stringify(G)); };
  function load() { try { const g = JSON.parse(store.get(KEY) || "null"); if (g && g.v === 1 && CANDS[g.me]) return g; } catch (e) {} return null; }
  const others = c => Object.keys(CANDS).filter(x => x !== c);
  const nm = c => (CANDS[c] || FOLK[c] || {}).name || c;
  const ISLE_BY = "isle";   // the holder of a law the island brought into the campaign (the laws of the week)
  const holder = c => c === ISLE_BY ? T("the island") : nm(c);
  const inForce = id => G.laws.some(l => l.id === id);
  const conflict = id => G.laws.find(l => LAWS[id].no.includes(l.id) || LAWS[l.id].no.includes(id));
  const lawScore = (id, cares) => cares.reduce((s, c) => s + (LAWS[id].fx[c] || 0), 0) + (hot() && (LAWS[id].fx[hot()] || 0) > 0 ? 1 : 0);   // the talk of the island (EVENTS) helps a law for it
  const pact = (a, b) => G.pacts.some(p => !p.broken && ((p.a === a && p.b === b) || (p.a === b && p.b === a)));
  const total = c => PEOPLE.reduce((s, p) => s + G.sup[c][p.id], 0);
  const leader = () => Object.keys(CANDS).sort((a, b) => total(b) - total(a))[0];
  const bump = (c, who, d) => { PEOPLE.forEach(p => { if (!who || who(p)) G.sup[c][p.id] = Math.max(0, Math.min(100, G.sup[c][p.id] + d)); }); };
  /* the Book: every move signed with the name of whoever made it */
  /* every line in the Book is also a transaction on Tau Testnet Alpha: the visitor's own (signed in their test wallet) and the rivals' (sent by the island bot on the relay, from the rivals' campaign wallets) */
  const write = (who, text, kind, at, pay, x) => {
    at = (who === G.me && UI.at) || at || TILL_AT[kind] || "hall";   // the visitor pays where they stand
    const b = { day: G.day, hour: Math.min(2, G.move), who, text, kind, at, pay: pay || 1 }; G.book.push(b); onChain(b);
    if (who === G.me) isleMove(kind, x, at);   // the shared island counts the visitor's own moves, never the rivals'
    return b;
  };

  /* ---------- the moves ---------- */
  /* propose a law: the Book checks it against the laws in force first, then the other three vote */
  function propose(by, id) {
    const L = LAWS[id], c = conflict(id);
    G.deals.forEach(d => { if (d.by === by && d.law === id) d.kept = true; });
    if (c) { write(by, c.by === ISLE_BY ? F("proposed “{x}”: refused, it contradicts “{y}”, the island’s law this week", { x: T(L.t), y: T(LAWS[c.id].t) }) : F("proposed “{x}”: refused, it contradicts “{y}”, in force since day {n}", { x: T(L.t), y: T(LAWS[c.id].t), n: c.day }), "refused", null, 1, id); return { refused: c }; }
    const votes = {};
    others(by).forEach(v => { votes[v] = v === G.me ? null : aiVote(v, by, id); });
    return { votes };
  }
  function aiVote(v, by, id) {
    if (pact(v, by)) return true;
    const s = lawScore(id, CANDS[v].cares), R = seeded(G.seed + G.day * 31 + id.length * 7 + v.length);
    if (LAWS[id].open) return v !== "marisol" || R() < 0.3;   // more people reading the Book suits everyone except the café that lives on gossip
    if (s > 0) return true; if (s < 0) return false;
    return leader() !== by && R() < 0.55;
  }
  function settle(by, id, votes) {
    const yes = Object.values(votes).filter(Boolean).length, L = LAWS[id];
    for (const v in votes) { if (v !== G.me && votes[v] != null) { if (pact(v, by) && !votes[v]) breakPact(v, by); } }
    if (yes >= 2) {
      G.laws.push({ id, by, day: G.day });
      /* a law an embassy paid for wins its proposer less goodwill: the envelope is in the Book next to it */
      const paid = G.deals.some(d => d.by === by && d.law === id), k = paid ? 3 : 5;
      PEOPLE.forEach(p => { const d = lawScore(id, p.cares); G.sup[by][p.id] = Math.max(0, Math.min(100, G.sup[by][p.id] + Math.min(9, d * (d > 0 ? k : 5)) + (L.open ? 2 : 0)));   /* one law wins a person over only so far */ for (const v in votes) if (votes[v]) G.sup[v][p.id] = Math.max(0, Math.min(100, G.sup[v][p.id] + d)); });
      write(by, F("passed “{x}”, {n} of 3 in favour", { x: T(L.t), n: yes }), "law", null, 1, id);
      return true;
    }
    write(by, F("proposed “{x}”: voted down, {n} of 3 in favour", { x: T(L.t), n: yes }), "down", null, 1, id);
    return false;
  }
  function campaign(by, topic, k = 1) {
    const backed = G.laws.some(l => l.by === by && (LAWS[l.id].fx[topic] || 0) > 0);
    bump(by, p => p.cares.includes(topic), Math.round((backed ? 9 : 6) * k * (hot() === topic ? 1.5 : 1)));
    write(by, F("spoke on the market square about {x}", { x: T(TOPICS[topic]) }), "talk", "market", 1, topic);
  }
  function rumour(by, about, claim, lie) {
    G.coins[by] -= RUMOUR;
    bump(about, null, lie ? -8 : -6);
    if (!lie) bump(by, p => p.reads, 3);
    G.lies.push({ by, about, claim, lie, day: G.day, seen: [] });
    G.trust[about] = by === G.me ? Math.max(0, G.trust[about] - 30) : G.trust[about];
    write(by, F("paid Radio Coco {n} coins to say: “{x}”", { n: RUMOUR, x: claim }), lie ? "lie" : "fact", "radio", RUMOUR, about);
  }
  function deal(by, emb) {
    const E = EMB[emb]; G.coins[by] += E.coins;
    G.deals.push({ by, emb, law: E.wants, day: G.day, kept: false });
    write(by, F("took {n} coins from the {x} and promised to propose “{y}”", { n: E.coins, x: T(E.name), y: T(LAWS[E.wants].t) }), "deal", emb, 1, emb);
    if (by === G.me) payMe(emb, T(E.name));
  }
  function makePact(a, b, gift) {
    if (gift) { G.coins[a] -= GIFT; G.coins[b] += GIFT; }
    G.pacts.push({ a, b, day: G.day });
    write(a, F("made a pact with {x}: each votes for the other’s laws", { x: nm(b) }) + (gift ? " " + F("({n} coins changed hands)", { n: GIFT }) : ""), "pact", null, 1, b);
  }
  function breakPact(a, b) {
    const p = G.pacts.find(p => !p.broken && ((p.a === a && p.b === b) || (p.a === b && p.b === a))); if (!p) return;
    p.broken = true; bump(a, null, -5); if (b === G.me || a === G.me) G.trust[a === G.me ? b : a] = 10;
    write(a, F("broke the pact with {x}", { x: nm(b) }), "broke", null, 1, b);
  }
  /* the rumours fade, the Book does not: each morning some people read it (Sam always, more with a copy on the square) */
  function readers() {
    const R = seeded(G.seed + G.day * 977), p = (inForce("copy") ? 0.6 : 0.2) + (G.lamp ? 0.2 : 0), out = [];
    PEOPLE.forEach(x => { if (x.reads || R() < p) out.push(x.id); });
    G.lies.forEach(l => {
      if (!l.lie) return;
      out.forEach(id => { if (l.seen.includes(id)) return; l.seen.push(id); G.sup[l.by][id] = Math.max(0, G.sup[l.by][id] - 14); G.sup[l.about][id] = Math.min(100, G.sup[l.about][id] + 6); });
      if (l.seen.length >= 4 && !l.out) { l.out = true; bump(l.by, null, -6); news(F("The Book shows who paid for “{x}”: {y}", { x: l.claim, y: nm(l.by) }), RICO.L.bkExposed); }
    });
    return out.length;
  }
  const news = (s, v) => G.news.push(v ? { day: G.day, s, v } : { day: G.day, s });   // v: what Rico says aloud about it (a fixed line with a clip)

  /* ---------- the rivals, at night ---------- */
  function night() {
    const R = seeded(G.seed + G.day * 4241);
    for (const c of others(G.me)) {
      const w = CANDS[c].way, lead = leader() === c ? others(c).sort((a, b) => total(b) - total(a))[0] : leader();
      if (w === "rumours" && G.coins[c] >= RUMOUR && R() < 0.8) {
        const lie = R() < (factAbout(lead === c ? others(c)[0] : lead) ? 0.4 : 0.65), about = lead === c ? others(c)[0] : lead;
        const claim = lie ? LIES[about] : factAbout(about) || LIES[about];
        rumour(c, about, claim, lie && claim === LIES[about] || !factAbout(about));
        news(F("Radio Coco tonight: “{x}”", { x: claim }), RICO.L.bkRumour);
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
      if (w === "rumours") campaign(c, CANDS[c].cares[1], 0.5);   // the café owner also just talks
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
  const UI = { card: null, cardFace: null, hover: null, air: false, airUntil: 0 };
  let wake = () => {};   // the first tap starts the music (set in wire())
  function hud() {
    $("cvStage").classList.toggle("pre", !G);
    if (!G) return;
    locks();
    $("cvDay").textContent = dayName(G.day); $("cvDay").title = F("Day {n} of {m}", { n: G.day, m: DAYS }) + " · " + (G.day < todayIdx() ? Fd("catching up: it is {x} already", { x: dayName(todayIdx()) }) : T("today, on the island as in the world"));
    $("cvHour").textContent = T(G.move >= MOVES ? "Night" : HOURS[G.move]);
    const left = Math.max(0, MOVES - G.move) + (G.spare || 0);   // extra moves (the first day, the evening bell, a pact, the key) show as more green dots
    $("cvMoves").replaceChildren(...Array.from({ length: G.move + left }, (_, i) => el("i", { class: i < left ? "on" : "" })));
    $("cvMoves").setAttribute("aria-label", F("{n} moves left today", { n: left }));
    $("cvMoves").parentElement.title = F("{n} moves left today", { n: left }) + " · " + T("Three moves a day, six on your first day. Reading, talking and visiting cost nothing; the evening bell at eight, your first pact and the key in the grotto give one more.");
    $("cvCoins").textContent = F("{n} coins", { n: G.coins[G.me] }); $("cvCoins").title = Fd("{n} coins saved from earlier campaigns", { n: savings().coins });
    if ($("cvAmb")) { $("cvAmb").hidden = !G.amb; if (G.amb) { $("cvAmb").textContent = T(AMB[G.amb.id].name); $("cvAmb").title = ambGoal(); } }
    $("cvMe").replaceChildren(portrait(G.me, 30), el("span", { text: nm(G.me) }));
    chainChip();
    const last = G.news[G.news.length - 1];
    if (last && last !== DJ.said) { DJ.said = last; const np = [V("book"), last.v ? { t: last.s, v: last.v } : Q(last.s)]; if (DJ.opened) onAir(np, 1); else { DJ.after = np; $("cvNews").textContent = last.s; } }   // before the show opens, the news waits for Rico's opener
    else if (!DJ.text) $("cvNews").textContent = last ? last.s : T("The Key Crier: a week to the election, Sunday night. Everything anyone does is written in the Book.");
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
    /* a new card interrupts whoever is talking on the old one (a line on air still finishes): the next one may have no clip of their own */
    if (performance.now() > UI.airUntil) { SND.hush(); if (RICO.stop) RICO.stop(); }
    closeCard(true);
    UI.at = place || null;
    if (G && place) { G.seen = G.seen || {}; if (!G.seen[place]) { G.seen[place] = 1; save(); } setTimeout(locks, 0); }
    /* the conversation always sits in the same place: a plate at the bottom middle, the person standing above it */
    const side = 0;
    if (place) { SC.focus(place, side); SND.set({ place, amb: place === "pier" || place === "book" ? 1.7 : place === "market" || place === "bar" ? 1 : 0.6 }); }
    const box = el("section", { class: "cv-card talk", "data-place": place || "", role: "dialog", "aria-modal": "false" });
    box._visit = place && build === PLACE[place] ? place : null;   // a visit to a place, not the card after a move
    const close = el("button", { type: "button", class: "cv-x", "aria-label": T("Back to the island"), onclick: () => closeCard(), text: "✕" });
    box.append(close);
    build(box);
    if (box._visit && box._who) asks(box, box._who);
    $("cvStage").append(box); UI.card = box; $("cvStage").classList.add("carded");
    placeHost(); watchFit(box);
    SND.sfx("open");
    setTimeout(() => { const b = box.querySelector(".cv-acts button:not([disabled])"); if (b && !matchMedia("(pointer: coarse)").matches) b.focus({ preventScroll: true }); }, 50);
  }
  /* on a phone the one you talk to stands above the sheet; held sideways, beside the plate. On a laptop or desktop
     the stage is a wide strip under the site's header: a plate in the middle would cover the person from the chin
     down, so the plate stands on the right, as tall as the stage, and the person in the free room on its left.
     Measured again whenever the phone turns or the window changes size, so a card never hides them */
  const LAND = matchMedia("(orientation: landscape) and (max-height: 520px) and (pointer: coarse)");
  function placeHost() {
    const st = $("cvStage"), box = UI.card, bar = st.querySelector(".bar");
    const w = st.clientWidth, h = st.clientHeight, side = !LAND.matches && innerWidth >= 760 && (w / h >= 1.5 || h < 720);
    st.classList.toggle("side", side);
    if (side && bar) st.style.setProperty("--below-bar", bar.offsetTop + bar.offsetHeight + 10 + "px");
    if (!box) return;
    SC.hostAt(innerWidth < 760 ? box.offsetTop : null, innerWidth >= 760 && (innerHeight < 520 || side) ? box.offsetLeft : null);
  }
  /* the plate never scrolls. What does not fit is tightened first; then the plate turns into pages with tabs on top
     (what is said, the list, what you can do), and a list longer than its page gets ‹ › to leaf through it.
     Fitted again when the window changes size and when the plate's content changes (an answer, a new step). */
  const FIT = { busy: false };
  function fitCard(box) {
    if (!box || !box.isConnected || FIT.busy) return;
    FIT.busy = true;
    try {
      box.classList.remove("tight", "tight2", "tight3", "paged", "tall"); box.style.removeProperty("--fz");
      /* the start card turned between wide and narrow (a window resized, a tablet turned): built again for its new shape */
      if (box.matches(".intro") && box._wide != null && box._wide !== wideIntro()) { setTimeout(() => { if (UI.card === box) openCard(null, introCard); }, 0); return; }
      /* wide, the figures take the room that is left (CSS): only the strip of facts tightens, and the pitches go last */
      if (box.matches(".intro.wide")) { box.classList.toggle("low", $("cvStage").clientHeight < 760); const over = () => box.scrollHeight > box.clientHeight + 3; if (over()) box.classList.add("tight"); if (over()) box.classList.add("tight2"); return; }
      if (innerWidth >= 760) box._tall = false;
      if (box._tall) box.classList.add("tall");
      box.querySelectorAll(".cv-tabs, .cv-pager").forEach(e => e.remove());
      box.querySelectorAll(".pg-off").forEach(e => e.classList.remove("pg-off"));
      const over = () => box.scrollHeight > box.clientHeight + 3;
      /* last resort: everything on the plate a little smaller, never under 11 px on a phone */
      const minFont = () => Math.min(16, ...[...box.querySelectorAll("p, span, b, small, em, button, li, h3, h4, label")].filter(e => e.offsetParent && e.textContent.trim()).map(e => parseFloat(getComputedStyle(e).fontSize) || 16));
      const shrink = () => { if (!over()) return; const lo = matchMedia("(pointer: coarse)").matches ? Math.max(0.8, 11 / minFont()) : 0.78; for (let z = 0.96; over() && z >= lo - 0.001; z -= 0.03) box.style.setProperty("--fz", z.toFixed(2)); };
      if (!over()) return;
      box.classList.add("tight"); if (!over()) return;
      /* the start, the morning paper and the ending are one page each: the choice must stay in sight */
      const special = box.matches(".intro, .end, .paper");
      if (special) { box.classList.add("tight2"); shrink(); if (over()) box.classList.add("tight3"); if (!over() || box.matches(".intro")) return; box.style.removeProperty("--fz"); }
      else { box.classList.add("tight2"); if (!over()) return; }
      const kids = [...box.children].filter(e => !e.matches(".cv-x, .cv-who, h2, h3"));
      const G3 = { talk: [], info: [], acts: [] };
      kids.forEach(e => (e.matches(".cv-acts, .cv-votes") ? G3.acts : e.matches(".cv-line, .cv-ask, .cv-you, .cv-note") ? G3.talk : G3.info).push(e));   // a vote: the faces stay with the buttons
      const show = list => kids.forEach(e => e.classList.toggle("pg-off", !list.includes(e)));
      /* what is said and the list together, if they fit beside the tab bar; otherwise each on its own page */
      let tabs = [["talk", T("Talk"), G3.talk], ["info", (G3.info.map(e => e.querySelector("h4")).find(Boolean) || {}).textContent || T("More"), G3.info], ["acts", T("What you can do"), G3.acts]].filter(t => t[2].length);
      if (tabs.length > 1 && !special) {
        box.classList.add("paged");
        const bar = el("div", { class: "cv-tabs", role: "tablist" });
        kids[0].before(bar);
        const tryTabs = list => { bar.replaceChildren(...list.map(t => el("button", { type: "button", role: "tab", text: t[1] }))); };
        const talkInfo = tabs.find(t => t[0] === "talk") && tabs.find(t => t[0] === "info");
        if (talkInfo) { tryTabs(tabs); show([...G3.talk, ...G3.info]); if (!over()) tabs = [["talk", T("Talk"), [...G3.talk, ...G3.info]], ...tabs.filter(t => t[0] === "acts")]; }
        if (tabs.length > 1) {
          const cur = tabs.find(t => t[0] === box._tab) || tabs[0];
          bar.replaceChildren(...tabs.map(t => el("button", { type: "button", role: "tab", class: t[0] === "acts" ? "do" : null, "aria-selected": t === cur ? "true" : "false", text: t[1],
            onclick: e => { e.stopPropagation(); box._tab = t[0]; box._page = 0; fitCard(box); } })));
          show(cur[2]);
        } else { bar.remove(); box.classList.remove("paged"); show(kids); }
      }
      if (!over()) return;
      /* still too long: leaf through the longest list of the page shown */
      const shown = kids.filter(e => !e.classList.contains("pg-off"));
      const lists = shown.flatMap(e => [e, ...e.querySelectorAll("ul, .cv-acts, .cv-ask")]).filter(e => e.matches("ul, .cv-acts, .cv-ask"));
      const L = lists.sort((a, b) => b.children.length - a.children.length)[0];
      const items = L ? [...L.children].filter(e => !e.matches(".cv-h, h4")) : [];
      if (items.length < 2) { shrink(); if (over() && innerWidth < 760 && !box._tall) box._tall = "again"; return; }
      const pager = el("div", { class: "cv-pager" }), tabBar = box.querySelector(".cv-tabs");
      if (tabBar) tabBar.append(pager); else L.after(pager);   // beside the tabs when there are tabs: no extra row
      const prev = el("button", { type: "button", "aria-label": T("Previous page"), text: "‹" }), next = el("button", { type: "button", "aria-label": T("Next page"), text: "›" }), lab = el("span");
      pager.append(prev, lab, next);
      const pages = []; let i = 0;
      while (i < items.length) {
        items.forEach(e => e.classList.add("pg-off"));
        let j = i; items[j].classList.remove("pg-off"); j++;
        while (j < items.length) { items[j].classList.remove("pg-off"); if (over()) { items[j].classList.add("pg-off"); break; } j++; }
        pages.push([i, j]); i = j;
      }
      const n = Math.min(box._page || 0, pages.length - 1), [a, b] = pages[n];
      items.forEach((e, k) => e.classList.toggle("pg-off", k < a || k >= b));
      if (pages.length < 2) { pager.remove(); shrink(); if (over() && innerWidth < 760 && !box._tall) box._tall = "again"; return; }
      lab.textContent = `${n + 1} / ${pages.length}`;
      prev.disabled = n === 0; next.disabled = n === pages.length - 1;
      prev.onclick = e => { e.stopPropagation(); box._page = n - 1; fitCard(box); };
      next.onclick = e => { e.stopPropagation(); box._page = n + 1; fitCard(box); };
      shrink();
      if (over() && innerWidth < 760 && !box._tall) box._tall = "again";   // an upright phone: the plate may grow over the room
    } finally {
      placeHost();   // the plate may have grown or shrunk: the person stands above or beside it again
      FIT.busy = false;
      if (box._fitObs) box._fitObs.takeRecords();   // our own changes are not a change of content
    }
    if (box._tall === "again") { box._tall = true; fitCard(box); }
  }
  function watchFit(box) {
    fitCard(box);
    if (!window.MutationObserver) return;
    let queued = false;
    box._fitObs = new MutationObserver(() => { if (FIT.busy || queued) return; queued = true; requestAnimationFrame(() => { queued = false; fitCard(box); }); });
    box._fitObs.observe(box, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["class", "hidden", "style"] });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => fitCard(box));
    [300, 1200].forEach(ms => setTimeout(() => fitCard(box), ms));   // a plate's fonts and pictures can arrive late
    /* and a watch: whatever made the plate longer (a vote coming in, a late font), it is fitted again */
    let sig = "";
    const tick = setInterval(() => {
      if (!box.isConnected) return clearInterval(tick);
      const now = box.innerText.length + ":" + box.clientHeight + ":" + box.clientWidth;
      if (now !== sig && box.scrollHeight > box.clientHeight + 3) fitCard(box);
      sig = box.innerText.length + ":" + box.clientHeight + ":" + box.clientWidth;
    }, 400);
  }
  if (document.fonts && document.fonts.addEventListener) document.fonts.addEventListener("loadingdone", () => fitCard(UI.card));
  const replaceHost = () => { placeHost(); fitCard(UI.card); requestAnimationFrame(() => { placeHost(); fitCard(UI.card); }); setTimeout(() => { placeHost(); fitCard(UI.card); }, 250); };   // some phones report the new size a moment late
  addEventListener("resize", replaceHost); addEventListener("orientationchange", replaceHost);
  if (window.screen && screen.orientation && screen.orientation.addEventListener) screen.orientation.addEventListener("change", replaceHost);
  function closeCard(keep) {
    if (UI.card) { UI.card.remove(); UI.card = null; } UI.at = null; $("cvStage").classList.remove("carded"); SC.host(null);
    if (!keep) { SC.focus(null); SND.set({ radio: false, tense: false, place: null, amb: 1 }); if (performance.now() > UI.airUntil) { SND.hush(); if (RICO.stop) RICO.stop(); } }   // a line on air is heard to its end
  }
  /* a card: who speaks, what they say (aloud, in their own voice, when the server has the clip), what you can do;
     the buttons are never read out. A line is text, or a list of parts as RICO.speak takes them. */
  function scene(box, who, title, line, acts, extra) {
    let parts = !line ? null : typeof line === "string" ? [{ t: line, v: EN(line) }] : line;
    if (parts && box._visit) parts = greet(box._visit, who, parts);
    if (parts) line = join(parts);
    const f = portrait(who, innerHeight < 520 ? 44 : innerWidth < 760 ? 64 : 92, 0);
    SC.host((g, t) => face(g, who, t, t < f._f.talk, f._f.mood, true), !!bustOf(who));   // the one you talk to stands in the room, life-size
    box.append(el("div", { class: "cv-who" }, f, el("div", null, el("b", { translate: "no", text: nm(who) }), el("small", { text: T((CANDS[who] || FOLK[who] || {}).role || "") }))));
    if (title) box.append(el("h3", { text: title }));
    box._who = who; box._f = f;
    if (line) {
      box.append(box._line = el("p", { class: "cv-line", text: line })); say(f, Math.min(4200, 600 + line.length * 38));
      const air = UI.air;
      talks(box, parts, who, { air }).then(secs => { if (secs && air) UI.airUntil = performance.now() + secs * 1000; if (secs && UI.card === box) { say(f, secs * 1000); DJ.next = Math.max(DJ.next, performance.now() + secs * 1000 + 20000); } }, () => {});
    }
    if (extra) box.append(extra);
    if (acts) box.append(el("div", { class: "cv-acts" }, acts));
    return f;
  }
  /* how long the one in front of you is still talking: to the end of their clip when it plays, else for as long as
     it takes to read the line. Whatever closes a card by itself (the night after the last move) waits for it */
  const readMs = s => Math.min(8000, 1500 + s.length * 40);
  function talks(box, parts, who, o) {
    box._talkEnd = performance.now() + readMs(join(parts));
    const w = box._talkWait = RICO.speak(parts, who, Object.assign({ still: () => UI.card === box || (o && o.air) }, o)).then(secs => { if (secs) box._talkEnd = performance.now() + secs * 1000; return secs; }, () => false);
    w.then(() => { if (box._talkWait === w) box._talkWait = null; });
    return w;
  }
  function whenQuiet(fn, t0 = performance.now()) {
    const b = UI.card, now = performance.now();
    if (b && b._talkWait && now - t0 < 6000) return setTimeout(() => whenQuiet(fn, t0), 250);   // the clip is still on its way
    if (b && b._talkEnd > now) return setTimeout(() => whenQuiet(fn, t0), b._talkEnd - now + 500);   // a question asked meanwhile is waited for too
    fn();
  }
  /* ---------- talking: what someone says when you come back, and what they answer when you ask (talk.js) ----------
     Asking is free: no move, nothing in the Book. What you have heard is kept with the game, so they do not repeat themselves. */
  const TALK = window.RABBIT_TALK || {};
  function facts() {
    const mine = G.book.filter(b => b.who === G.me), did = G.did || {}, f = {
      "": true, early: G.day <= 2, mid: G.day >= 3 && G.day < DAYS, last: G.day >= DAYS,
      myLaw: G.laws.some(l => l.by === G.me), noLaw: G.day >= 2 && !G.laws.some(l => l.by === G.me),
      pact: G.pacts.some(p => !p.broken && (p.a === G.me || p.b === G.me)), broke: mine.some(b => b.kind === "broke"),
      deal: G.deals.some(d => d.by === G.me), lied: G.lies.some(l => l.by === G.me && l.lie), caught: G.lies.some(l => l.by === G.me && l.lie && l.out),
      truth: G.lies.some(l => l.by === G.me && !l.lie), smeared: G.lies.some(l => l.about === G.me && l.lie),
      lead: G.day >= 2 && leader() === G.me, poor: G.coins[G.me] < RUMOUR, chart: !!G.chart, key: !!G.key, drummed: !!G.drummed, circled: !!G.circled,
      dove: !!did.dive, worked: !!did.works, plans: !!did.camp, rich: G.coins[G.me] >= 60, amb: !!G.amb, roof: !!(G.built && G.built.roof), lamp: !!(G.built && G.built.lamp), stoneSet: !!(G.built && G.built.stone) };
    if (G.amb) f["amb" + G.amb.id[0].toUpperCase() + G.amb.id.slice(1)] = true;
    for (const id in LAWS) f[id] = inForce(id);
    /* your dealings with each embassy: southOffer (not taken), southDeal (taken), southOwed (taken, the law not proposed yet), southKept (proposed); north the same */
    for (const e in EMB) { const d = G.deals.find(d => d.by === G.me && d.emb === e); f[e + "Offer"] = !d; f[e + "Deal"] = !!d; f[e + "Owed"] = !!d && !d.kept; f[e + "Kept"] = !!d && d.kept; }
    /* what has happened to the island this campaign: eventBoiler, eventStorm, eventCoup, eventCatch, eventRoof */
    events().forEach(e => { if (e.day <= G.day) f["event" + e.id[0].toUpperCase() + e.id.slice(1)] = true; });
    /* a cruise ship near: which one, and whether it comes in a few days, tomorrow, today, is here or has left (shipFacts) */
    return Object.assign(f, shipFacts());
  }
  /* of a list of [when, line]: the first that holds and has not been heard yet, else they take turns.
     A "when" of "a+b" holds when both hold, "!a" when a does not */
  const holds = (f, w) => w.split("+").every(k => k[0] === "!" ? !f[k.slice(1)] : f[k]);
  function pick(who, list) {
    const f = facts(), ok = list.filter(([w]) => holds(f, w)); if (!ok.length) return null;
    G.heard = G.heard || {};
    const fresh = ok.find(([, s]) => !G.heard[who + "|" + s]);
    const s = fresh ? fresh[1] : ok[(G.heard["#" + who] = (G.heard["#" + who] || 0) + 1) % ok.length][1];
    G.heard[who + "|" + s] = 1; save();
    return s;
  }
  function greet(place, who, parts) {
    G.heard = G.heard || {};
    const k = "@" + place + "|" + who, t = TALK[who];
    if (!G.heard[k] || !t || !t.back) { G.heard[k] = 1; save(); return parts; }
    const s = pick(who, t.back);
    return s ? [S(s), ...parts.filter(p => !p.v)] : parts;   // what is only shown (coins and such) stays
  }
  function asks(box, who) {
    const t = TALK[who]; if (!t || !t.ask) return;
    const wrap = el("div", { class: "cv-ask" }), asked = new Set();
    const draw = () => {
      const qs = [], f = facts();
      t.ask.forEach((a, i) => {
        if (a.when && !holds(f, a.when)) return;   // a question of the moment (a cruise ship near) only while it holds
        if (!asked.has(i)) qs.push([a, i]); else if (a.more && !asked.has(i + "+")) qs.push([a.more, i + "+"]);
      });
      wrap.replaceChildren(...(qs.length ? [el("p", { class: "cv-h", text: T("Ask (free, no move)") }), ...qs.map(([a, k]) => btn(T(a.q), () => { asked.add(k); answer(box, who, a); draw(); }, { ask: true }))] : []));
    };
    draw(); if (box._line) box._line.after(wrap); else box.append(wrap);   // right under what they said, above the moves
  }
  function answer(box, who, a) {
    const s = pick(who, a.a); if (!s || !box._line) return;
    let you = box.querySelector(".cv-you");
    if (!you) { you = el("p", { class: "cv-you" }); box._line.before(you); }
    you.textContent = "“" + T(a.q) + "”";
    const parts = [S(s)], line = join(parts);
    box._line.textContent = line; say(box._f, Math.min(5200, 600 + line.length * 38));
    talks(box, parts, who).then(secs => { if (secs && UI.card === box) { say(box._f, secs * 1000); DJ.next = Math.max(DJ.next, performance.now() + secs * 1000 + 20000); } }, () => {});
  }
  const btn = (text, on, o = {}) => el("button", { type: "button", class: "cv-b" + (o.go ? " go" : "") + (o.warn ? " warn" : "") + (o.ask ? " ask" : ""), disabled: o.off || null, title: o.tip || null, onclick: e => { SND.sfx("tap"); on(e); } }, el("span", { text }), o.sub ? el("small", { text: o.sub }) : null);
  const did = k => { G.did = G.did || {}; G.did[k] = 1; };
  const movesLeft = () => G.move < MOVES && !G.over;
  /* a move is used up, unless the evening bell kept one for the visitor (BELL) */
  const useMove = () => { if (G.spare) G.spare--; else G.move++; if (!store.get(SIGNED)) { store.set(SIGNED, "1"); signsOff(); } };
  /* a move is spent: the sun goes on, and after the evening the night comes */
  function spend() {
    useMove(); save(); hud();
    if (G.move >= MOVES) setTimeout(() => whenQuiet(() => { closeCard(); endDay(); }), 900);   // what they answer is heard to its end before the night
  }
  /* small treats that cost coins, not a move, and do something real: a tip for Lola, a round of coffee on the square,
     exercise books for Hana's class. Once a day each; paid as a real transaction to the place's till, like every line in the Book */
  const treated = k => !!(G.treats && G.treats[k] === G.day);
  function treat(k, n, at, line, fx, msg) {
    if (treated(k) || G.coins[G.me] < n) return;
    G.coins[G.me] -= n; G.treats = G.treats || {}; G.treats[k] = G.day;
    fx(); write(G.me, line, "gift", at, n);
    SND.sfx("coin"); save(); hud(); toast(msg);
    if (UI.card) openCard(at, PLACE[at]);
  }
  const treatBtn = (k, label, n, at, line, fx, msg) => btn(label, () => treat(k, n, at, line, fx, msg), { off: treated(k) || G.coins[G.me] < n, sub: treated(k) ? T("Done for today") : F("{n} coins, no move, written in the Book", { n }) });
  const noMoves = box => box.append(el("p", { class: "cv-note", text: T("That was your last move today. The island stays open: reading, talking and visiting cost nothing.") }));

  /* ---------- the places ---------- */
  const PLACE = {
    hall(box) {
      const lines = G.laws.length ? G.laws.map(l => el("li", null, el("b", { text: T(LAWS[l.id].t) }), " ", el("small", { text: l.by === ISLE_BY ? T("the island’s law this week, from last week’s campaigns") : F("by {x}, day {n}", { x: nm(l.by), n: l.day }) }))) : [el("li", { class: "dim", text: T("No laws yet. The island runs on habit.") })];
      const list = el("div", { class: "cv-laws" }, el("h4", { text: T("In force") }), el("ul", null, lines));
      const acts = Object.keys(LAWS).filter(id => !inForce(id)).map(id => {
        const c = conflict(id), s = lawScore(id, CANDS[G.me].cares);
        return btn(T(LAWS[id].t), () => doPropose(id), { off: !movesLeft(), sub: c ? Fd("contradicts “{x}”", { x: T(LAWS[c.id].t) }) : effects(id), warn: !!c });
      });
      scene(box, "ama", T(SC.places.hall.name), T("Pick a law. The other three candidates vote; two yes and it is law. The Book checks it against the laws in force first."), [el("p", { class: "cv-h", text: T("Propose a law (one move)") }), ...acts], list);
    },
    market(box) {
      const rows = PEOPLE.map(p => {
        const mine = G.sup[G.me][p.id], best = Object.keys(CANDS).sort((a, b) => G.sup[b][p.id] - G.sup[a][p.id])[0];
        return el("li", null, el("span", { class: "nm", translate: "no", text: p.name }), el("small", { text: p.cares.map(c => T(TOPICS[c])).join(" · ") }), el("i", { class: "bar" + (best === G.me ? " lead" : ""), style: `--v:${mine}%`, title: F("leans to {x}", { x: nm(best) }) }));
      });
      const acts = Object.keys(TOPICS).map(t => btn(F("Talk about {x}", { x: T(TOPICS[t]) }) + (hot() === t ? " ★" : ""), () => { campaign(G.me, t); SND.sfx("yes"); SC.gather(1); setTimeout(() => SC.gather(0), 2600); toast(F("People who care about {x} listened.", { x: T(TOPICS[t]) })); spend(); if (UI.card) openCard("market", PLACE.market); }, { off: !movesLeft() }));
      const round = treatBtn("coffee", T("Buy the square a round of coconut coffee"), 8, "market", T("bought the whole square a round of coconut coffee: 8 coins"), () => bump(G.me, null, 2), T("Everyone on the square raises a cup to you. A little warmer towards you, all of them."));
      scene(box, G.me === "marisol" ? "lola" : "marisol", T(SC.places.market.name), T("Everyone passes through here. Talk about what people care about; it counts double if you already passed a law for it."), [el("p", { class: "cv-h", text: T("Speak to the square (one move)") }), ...acts, round], el("ul", { class: "cv-folk" }, rows));
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
      const tipLola = treatBtn("lola", T("Tip Lola; she puts in a good word for you"), 5, "bar", T("tipped Lola 5 coins at Bar La Ola"), () => others(G.me).forEach(c => { G.trust[c] = Math.min(100, G.trust[c] + 8); }), T("Lola leans over to the other candidates’ table. They trust you a little more."));
      scene(box, "lola", T("Bar La Ola"), T("A pact means you vote for each other’s laws. Break one and the whole island knows by breakfast. Lemonade’s on the house."), [el("p", { class: "cv-h", text: T("Make a pact (one move)") }), ...acts, ...gifts, tipLola]);
    },
    book(box) {
      G.said.book = G.book.length; save();
      const rows = G.book.slice().reverse().map(b => el("li", { class: "k-" + b.kind }, el("small", { text: F("Day {n}", { n: b.day }) + " · " + T(HOURS[b.hour] || "Night") }), el("span", null, el("b", { translate: "no", text: nm(b.who) }), " ", el("span", { text: b.text }), b.tx && !/^\d+$/.test(b.tx) ? el("a", { class: "cv-tx", href: "/explorer/?tx=" + b.tx, target: "_blank", rel: "noopener", title: T("This line on Tau Testnet Alpha"), text: " ⛓" }) : b.tx || b.bot ? el("span", { class: "cv-tx", title: T("This line went to Tau Testnet Alpha as a transaction"), text: " ⛓" }) : null)));
      scene(box, "sam", T("The Book in the lighthouse"), T(G.book.length ? "Every move on the island is written here with the name of whoever made it. Nobody can tear out a page, not even me. Reading costs nothing." : "Empty, for now. Every move on the island will be written here, with the name of whoever made it. Nobody can tear out a page."), [btn(T("The island today"), () => openIsle(), { sub: T("every campaign played today, added up") }), buildBtn("lamp")],
        el("ol", { class: "cv-book" }, rows.length ? rows : [el("li", { class: "dim", text: T("Nothing yet.") })]),
        el("p", { class: "cv-old", text: T("The Book is the oldest custom of the island’s first people: for three hundred years every agreement was copied by hand into many books, so nobody alone could change one. The testnet is only its newest copy.") }));
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
        treatBtn("books", T("Buy exercise books for the class"), 6, "school", T("bought exercise books for Hana’s class: 6 coins"), () => bump(G.me, p => p.cares.includes("school"), 4), T("The children carry the new books home. Families who care about the school noticed.")),
        buildBtn("roof"),
      ]);
    },
    dive(box) {
      const harbour = inForce("harbour");
      scene(box, "kai", T(SC.places.dive.name), T("We dive with Tau sensors. Every reading is signed the moment it is taken, so nobody can say the reef is fine when it is not. Or the other way round. Wetsuits are in the back, sizes small, medium and optimistic."), [
        btn(T("Dive the reef with Kai"), () => { did("dive"); write(G.me, T(harbour ? "dove with Reef Proof: the signed readings show the reef suffering since the deep harbour" : "dove with Reef Proof: the signed readings show a healthy reef, right where the cruise harbour would go"), "fact"); campaign(G.me, "fish", 0.8); toast(T("The readings are in the Book, signed. People who fish took note.")); spend(); if (UI.card) openCard("dive", PLACE.dive); }, { off: !movesLeft(), sub: T("one move") }),
      ]);
    },
    works(box) {
      /* Noor runs the Coconut Works and Baako's co-op supplies it; she is the one you meet when you are Baako yourself, and she is the boss here */
      scene(box, G.me === "baako" ? "noor" : "baako", T(SC.places.works.name), G.me === "baako" ? T("Baako. Candidate or not, your co-op’s coconuts still come through my gate, and my press still starts at six. Coconuts in, everything out: oil, rope, soap, charcoal. You want a shift, you pedal. And nobody touches the organ. Not even someone on the ballot.") : T("Coconuts in, everything out: oil, rope, soap, charcoal and once, by accident, a rather good jazz record. The machine is three bicycles and a church organ. Do not touch the organ."), [
        btn(T("Work a shift (10 coins)"), () => { did("works"); G.coins[G.me] += 10; write(G.me, T("worked a shift at the Coconut Works: 10 coins, honestly earned"), "talk"); payMe("works", T("The Coconut Works")); SND.sfx("coin"); toast(T("Ten coins, and you smell of coconut for the rest of the day.")); spend(); if (UI.card) openCard("works", PLACE.works); }, { off: !movesLeft(), sub: T("one move") }),
      ]);
    },
    camp(box) {
      const took = G.deals.filter(d => d.by !== G.me);
      scene(box, "pim", T(SC.places.camp.name), T("We are only measuring. For whom? The embassies. For what? Something deep. We measure, others decide. That is the arrangement, and it pays by the metre."), [
        btn(T("Look at the plans on the table"), () => {
          const line = took.length ? F("saw the surveyors’ plans, paid for by the embassies, with notes from {x}", { x: [...new Set(took.map(d => nm(d.by)))].join(", ") }) : T("saw the surveyors’ plans: nobody has signed for them yet");
          did("camp"); write(G.me, line, "fact"); toast(took.length ? T("The plans show who has been talking to the embassies. It is in the Book now.") : T("Nobody has signed yet. The surveyors look disappointed.")); spend(); if (UI.card) openCard("camp", PLACE.camp);
        }, { off: !movesLeft(), sub: T("one move") }),
      ]);
    },
    ship(box) {
      G.seen = G.seen || {};
      const ready = G.day >= 2;
      scene(box, "wren", T(SC.places.ship.name), T(G.chart ? "The chart is yours now. Mind the waterfall: it is not as solid as it looks." : "Not a pirate, dear. Marine archaeologist, retired. Everything the sea gives back ends up here, labelled: odd socks, a piano key, and a chart nobody can read."), G.chart ? null : [
        btn(T("Ask about the chart"), () => { if (ready) { G.chart = true; save(); toast(T("Wren gives you the chart. It shows a door behind the waterfall.")); } else { toast(T("“Come back tomorrow, I am still drying it.”")); closeCard(); return; } if (UI.card) openCard("ship", PLACE.ship); }),
      ]);
    },
    ama(box) {
      scene(box, "ama", T(SC.places.ama.name), T("My grandmother’s grandmother kept the island’s agreements on a stone, long before anyone wrote a Book. People think a record everyone can read is something new. It is the oldest thing we have."), [
        btn(T("Ask about the stone"), () => { toast(T(G.day >= 2 ? "“Go to the Tide Stone. It is low tide, it will let you read.”" : "“Tomorrow, at low tide. The stone does not hurry, and neither should you.”")); closeCard(); }),
      ]);
    },
    canoe(box) {
      scene(box, "kiko", T(SC.places.canoe.name), T("A canoe is a promise kept by thirty planks. If one of them lies, the sea tells everyone. Same as your Book, really, only wetter."), [
        btn(T("Watch him work"), () => { toast(T("Plank by plank. Nobody hurries a canoe.")); closeCard(); }),
      ]);
    },
    stone(box) {
      scene(box, "ama", T(SC.places.stone.name), T("Each mark is an agreement. Nobody ever chiselled one away, because everyone would see the scar. Your Book in the lighthouse is this stone, made of paper."), [
        btn(T("Read the oldest mark"), () => { toast(T("“No new rule may contradict an older one, unless the older one is undone first.” The Book checks every law the same way.")); closeCard(); }),
      ]);
    },
    drums(box) {
      const lies = G.lies.filter(l => l.lie && !l.out);
      scene(box, "tano", T(SC.places.drums.name), T("Before Radio Coco, the news went from hill to hill on these drums. They have one rule: they only carry what the stone confirms. That is why nobody ever bribed a drummer."), G.drummed ? null : [
        btn(T("Drum the truth across the island"), () => {
          G.drummed = true; lies.forEach(l => { l.out = true; bump(l.by, null, -8); news(F("The Book shows who paid for “{x}”: {y}", { x: l.claim, y: nm(l.by) }), RICO.L.bkExposed); });
          write(G.me, F("drummed the truth from the three hills: {n} rumours answered", { n: lies.length }), "fact"); SND.sfx("yes"); toast(lies.length ? T("Every rumour still on air has been answered from the hills.") : T("No rumours to answer. The drums play anyway; it is a fine evening.")); spend(); if (UI.card) openCard("drums", PLACE.drums);
        }, { off: !movesLeft(), sub: T("once in the game, one move") }),
      ]);
    },
    circle(box) {
      scene(box, "tano", T(SC.places.circle.name), T("Here a decision stands when nobody in the circle can show that it contradicts what we already agreed. Not when the loudest agrees. Your chain does the same with its rules, I am told."), [
        ...(G.circled ? [] : [btn(T("Sit in the circle"), () => { G.circled = true; others(G.me).forEach(c => { G.trust[c] = Math.min(100, G.trust[c] + 12); }); save(); toast(T("You listened more than you spoke. The other candidates trust you a little more.")); if (UI.card) openCard("circle", PLACE.circle); })]),
        buildBtn("stone"),
      ]);
    },
    grotto(box) {
      scene(box, "ama", T(SC.places.grotto.name), T("So you found it. The key on the old fort opens nothing; it never did. The real key was always this: everyone keeps a copy of what was agreed, so nobody can change it alone."), G.key ? null : [
        btn(T("Take a copy of the Book"), () => { G.key = true; write(G.me, T("found the cave behind the waterfall and took a copy of the Book"), "fact"); bump(G.me, p => p.reads, 6); save(); SND.sfx("yes"); toast(T("You hold the White Rabbit Key.")); setTimeout(() => extraMove(T("the key in the grotto")), 2800); if (UI.card) openCard("grotto", PLACE.grotto); }),
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
  const MOVE_AT = new Set(["hall", "market", "radio", "north", "south", "bar"]);   // where a move is made; everywhere else a visit costs nothing
  function placeKeys() {
    const keys = $("cvPlaces"); if (!keys) return;
    const ids = Object.keys(PLACE).filter(id => SC.places[id] && !SC.locked(id)), sig = ids.join();
    if (keys.dataset.sig === sig) return; keys.dataset.sig = sig; keys.textContent = "";
    ids.forEach(id => keys.append(el("button", { type: "button", onclick: () => { wake(); if (G && !UI.card) openCard(id, PLACE[id]); } }, el("span", { text: T(SC.places[id].name) }), MOVE_AT.has(id) ? null : el("small", { text: T("free, no move") }))));
    /* what the bar leaves out on a small screen */
    keys.append(el("button", { type: "button", class: "more", onclick: () => { wake(); help(); } }, el("span", { text: T("How it works") })),
      el("button", { type: "button", class: "more", onclick: () => { wake(); $("cvReset").click(); } }, el("span", { text: T("New game") })));
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
    /* what they pay for is law already (last week's island law, or passed this week): there is nothing left to promise, so no coins */
    if (!took && inForce(E.wants)) return scene(box, E.who, T(E.name), F(E.done || "“{x}” is law already, so we have nothing to ask of you today. An unusual feeling. We do not care for it.", { x: LAWS[E.wants].t }), [btn(T("Leave"), () => closeCard())]);
    const line = took ? F(E.remind || "We are counting on you for “{x}”. We would hate to remind the island in public.", { x: LAWS[E.wants].t }) : F(E.offer || "{n} coins, today. All we ask is that you propose “{x}” before the election. A small thing between friends.", { n: E.coins, x: LAWS[E.wants].t });
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
        if (by === G.me) { useMove(); save(); hud(); }
      };
      setTimeout(next, 600);
    });
  }
  function doRumour(c, claim, lie) {
    rumour(G.me, c, claim, lie); SND.sfx("coin");
    news(F("Radio Coco: “{x}”", { x: claim }), RICO.L.bkRumour);
    /* Rico calls it out on air, loud and happy, then tells you what you bought */
    const aired = [S("This just in on Radio Coco, ninety-seven point three!"), { t: "“" + T(claim) + "”", v: EN(claim) + "!" },
      S(lie ? "Done, it’s out there. Half the island is talking. The other half will read the Book tomorrow, and the Book says you paid me." : "Done. And this one’s true, so let them check. The Book backs you up.")];
    /* what you paid for goes out whole: closing the card or the night coming does not cut Rico off */
    UI.air = true; UI.airUntil = performance.now() + 60000;   // until the clip's length is known
    openCard("radio", box => scene(box, "rico", T("On air"), aired, [btn(T("Continue"), () => closeCard())]));
    UI.air = false;
    spend();
  }
  function doPact(c, gift) {
    const ok = gift ? G.trust[c] >= 25 : G.trust[c] >= 50;
    if (ok) { makePact(G.me, c, gift); SND.sfx("yes"); G.trust[c] = Math.min(100, G.trust[c] + 10); if (!G.pactMove) { G.pactMove = 1; setTimeout(() => extraMove(T("your first pact")), 1200); } }
    else { G.trust[c] = Math.max(0, G.trust[c] - 3); write(G.me, F("offered {x} a pact: turned down", { x: nm(c) }), "down"); SND.sfx("no"); }
    openCard("bar", box => scene(box, c, ok ? T("A pact") : T("No pact"), ok ? T("Fine. I vote for yours, you vote for mine. Lola is our witness, and the Book is our memory.") : T(G.trust[c] < 20 ? "After what you did? Buy yourself a lemonade." : "Not today. Show me how you vote first."), [btn(T("Continue"), () => closeCard())]));
    spend();
  }

  /* ---------- day and night ---------- */
  function endDay() {
    if (!G || G.over || G.move < MOVES || G.counting || G.waiting) return;   // once per night, however many ways lead here; a campaign already waiting for tomorrow has had its card
    hud();
    night();
    if (G.day >= DAYS) { save(); return election(); }
    if (!FREE && G.day >= todayIdx()) { G.waiting = true; save(); return nightCard(); }
    nextDay();
  }
  function nextDay() { G.waiting = false; G.day++; G.move = briefDay() ? MOVES - 1 : 0; const n = readers(); save(); morning(n); }
  /* the day is done and so is the real one: the next island day comes after midnight, German time */
  function nightCard() {
    openCard(null, box => {
      box.classList.add("paper");
      box.append(el("p", { class: "mast", text: T("The Key Crier") }), el("p", { class: "date", text: dayName(G.day) + " · " + T("Night") }),
        el("p", { class: "lead", text: Fd("{x} is done on the island. The next day begins with the real one, after midnight German time ({y}). Your campaign waits here; the rivals sleep too.", { x: dayName(G.day), y: spanText(untilMidnight()) }) }),
        el("ul", null, el("li", { text: T("Until then: read the Book, talk to people, look at The island today, visit the school, the dive centre, the works and the stone circle. None of it costs a move.") }),
          el("li", { text: T("At eight in the evening Tobias rings the pier bell: ring back within two minutes and you have one more move that day.") }),
          el("li", { text: G.day >= DAYS - 1 ? T("Tomorrow is Sunday: three last moves, then the islanders vote.") : Fd("Governor’s count {x}, Monday 00:00 German time.", { x: countIn() }) })),
        el("div", { class: "cv-acts" }, btn(T("Good night"), () => closeCard(), { go: true })));
    });
  }
  /* on a new real day the waiting campaign goes on; a campaign whose week has passed was decided without you */
  function resume() {
    if (!G || G.over) return;
    if (!FREE && G.week && G.week !== weekId()) return decideLate();
    if (G.waiting) { if (FREE || todayIdx() > G.day) nextDay(); else nightCard(); }
  }
  function decideLate() {
    const t = tally();
    G.over = { win: t.win, count: t.count, lies: G.lies.filter(l => l.by === G.me && l.lie).length, late: true };
    write("sam", F("counted the ballots: {x} is governor of the island", { x: nm(t.win) }), "law");
    save(); ending();
  }
  setInterval(() => { if (G && G.waiting && !UI.card && !document.hidden && todayIdx() > G.day) resume(); }, 60000);
  function morning(n) {
    hud();
    isleMorning();
    const ev = events().find(e => e.day === G.day), E = ev && EVENTS[ev.id];
    const today = G.news.filter(x => x.day >= G.day - 1 && !(E && x.s === T(E.lead))).slice(-4);
    const R = seeded(G.seed + G.day), joke = T(JOKES[Math.floor(R() * JOKES.length)]);
    const box = el("div", { class: "cv-paper" },
      el("p", { class: "mast", text: T("The Key Crier") }), el("p", { class: "date", text: dayName(G.day) + " · " + F("Day {n} of {m}", { n: G.day, m: DAYS }) + " · " + F("{n} people read the Book last night", { n }) }),
      E ? el("p", { class: "lead", text: T(E.lead) }) : false,
      el("ul", null, today.length ? today.map(x => el("li", { text: x.s })) : [el("li", { text: T("A quiet night. The fish report no news.") })]),
      el("p", { class: "joke", text: joke }));
    openCard(null, b => {
      b.classList.add("paper"); b.append(box); const pend = G.pending.splice(0);
      const after = () => { if (E) setTimeout(() => onAir([S(E.rico)], true), 600); offerAmbition(); };
      const start = btn(pend.length ? (pend.length === 1 ? T("To the council: one law to vote on") : F("To the council: {n} laws to vote on", { n: pend.length })) : T("Start the day"), () => { if (pend.length) councilQueue(pend, after); else { closeCard(); after(); } }, { go: true });
      const acts = el("div", { class: "cv-acts" }, start); b.append(acts);
      if (ev) eventMorning(ev, b, acts, start);
    });
    save();
  }
  /* the rivals' laws come to the council in the morning; you vote on each */
  function councilQueue(list, then) {
    if (!list.length) { closeCard(); then && then(); return; }
    const p = list.shift(), r = propose(p.by, p.id);
    if (r.refused) { news(F("{x}’s law “{y}” was refused: it contradicts a law in force", { x: nm(p.by), y: T(LAWS[p.id].t) }), RICO.L.bkRefused); return councilQueue(list, then); }
    vote(p.by, p.id, r.votes, () => councilQueue(list, then));
  }
  const JOKES = [
    "Weather: sunny, with a chance of promises.", "Lost: one coconut, answers to nothing.", "The gulls have formed a party. Their programme: more fish.",
    "Rico says he only plays hits. The Book says he plays whatever is paid for.", "Old Sam reminds readers that the Book is open every day and has never once been wrong about who did what.",
    "Classified: honest candidate wanted. Must not mind being written down.", "The black cat was seen crossing the square. Twice. Sam says it is nothing.",
  ];

  /* ---------- sudden events: once or twice a campaign something happens to the island, and the week is not the same ----------
     the Key Crier leads with it, the player gets one choice on the morning paper (real coins, a real transaction to the place's
     till), the topic becomes the talk of the island for the rest of the week: speeches about it count more, laws for it pass
     more easily, and the rivals pick their laws by it too */
  const EVENTS = {
    boiler: { hot: "roads", lead: "The Coconut Works boiler burst at dawn. Nobody hurt, coconut everywhere, and the road to the Works is a river of oil.",
      rico: "Rico here, and I can smell it from the studio. The Coconut Works boiler went off like a drum solo. Noor says the road is the problem now, so expect everybody to care about roads today.",
      act: { t: "Send 15 coins to the repair fund", n: 15, at: "works", line: "sent 15 coins to the Coconut Works repair fund", d: 5 } },
    storm: { hot: "visitors", lead: "A storm closed the pier overnight. No ferry today, no visitors, and three stranded travellers sleep on the bar’s floor.",
      rico: "Morning, island. The pier is closed, the ferry is not coming, and three visitors are stranded on Lola’s floor. Whoever looks after visitors today will be remembered.",
      act: { t: "Open your kitchen for the stranded (10 coins)", n: 10, at: "bar", line: "fed the stranded visitors at the bar: 10 coins", d: 4 } },
    coup: { hot: "quiet", lead: "In the night Salado’s investors tried to buy the council tree. Ama sat on its roots until sunrise and the paper was never signed.",
      rico: "Big news, and it is not good. Someone tried to buy the council tree in the dark. Ama sat on it. The island wants quiet nights again, and everyone who took embassy money is being looked at.",
      act: { t: "Sign Ama’s letter: the tree is not for sale", n: 0, at: "hall", line: "signed Ama’s letter: the council tree is not for sale", d: 3 }, hit: true },
    catch: { hot: "fish", lead: "A record catch. The bay is full of fish and so is every doorstep, and Old Sam says the reef has not looked like this in forty years.",
      rico: "Fish! Fish everywhere! The bay is silver, Sam is crying, and today the whole island cares about one thing. Whoever talks fish, wins ears.",
      act: { t: "Throw a fish fry on the square (10 coins)", n: 10, at: "market", line: "threw a fish fry on the square: 10 coins", d: 4 } },
    roof: { hot: "school", lead: "The school roof gave way in the night rain. Lessons under the council tree until further notice; Hana has borrowed every parasol on the island.",
      rico: "Rain in the night, and the school roof is on the floor. Lessons under the tree. Parents are listening today, so whatever you say about the school, say it well.",
      act: { t: "Pay for tarpaulins for the school (10 coins)", n: 10, at: "school", line: "paid 10 coins for tarpaulins for the school", d: 4 } },
  };
  const EVENT_NAMES = { boiler: "burst boiler", storm: "storm", coup: "night at the council tree", catch: "record catch", roof: "fallen school roof" };
  /* which ones happen this campaign: one on day 2, 3 or 4, sometimes a second on another day; fixed by the campaign's seed */
  function planEvents(seed) {
    const R = seeded(seed + 777), ids = Object.keys(EVENTS).sort(() => R() - 0.5), days = [2, 3, 4, 5, 6].sort(() => R() - 0.5);
    const out = [{ id: ids[0], day: days[0] }];
    if (R() < 0.6) out.push({ id: ids[1], day: days[1] });
    return out.sort((a, b) => a.day - b.day);
  }
  const events = () => G.events || (G.events = planEvents(G.seed));
  /* the talk of the island: the latest event's topic, from its morning to the election */
  const hot = () => { if (!G) return null; const e = events().filter(e => e.day <= G.day).pop(); return e ? EVENTS[e.id].hot : null; };
  function eventMorning(ev, box, acts, start) {
    const E = EVENTS[ev.id];
    if (!ev.done) {
      ev.done = true;
      news(T(E.lead), E.lead);
      if (E.hit) G.deals.forEach(d => { if (!d.seen) { d.seen = true; bump(d.by, null, -6); } });
      save();
    }
    const act = btn(T(E.act.t), () => {
      if (E.act.n) G.coins[G.me] -= E.act.n;
      bump(G.me, p => p.cares.includes(E.hot), E.act.d);
      write(G.me, T(E.act.line), "talk", E.act.at, Math.max(1, E.act.n), E.hot);
      SND.sfx(E.act.n ? "coin" : "yes"); save(); hud();
      acts.replaceChildren(el("p", { class: "cv-result ok", text: Fd("Done. People who care about {x} noticed.", { x: T(TOPICS[E.hot]) }) }), start);
    }, { off: G.coins[G.me] < E.act.n, sub: E.act.n ? F("{n} coins, written in the Book", { n: E.act.n }) : T("free, written in the Book") });
    acts.prepend(act);
  }

  /* ---------- the evening bell: at eight o'clock German time Tobias rings the pier bell, and for two minutes everyone who is
     playing can ring back. Answering is a real transaction to the pier's till, at the same moment as everyone else's, so the
     island's busiest minute is a real burst on the testnet (tauhud.com/load/ shows it). It keeps one more move for today. ---------- */
  const BELL = { at: 20 * 60, open: 2, soon: 5 };
  let berlinDay = null;
  const today = () => { try { berlinDay = berlinDay || new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Berlin" }); return berlinDay.format(new Date()); } catch (e) { return new Date().toISOString().slice(0, 10); } };
  function bellState() {
    if (!G || G.over || G.bell === today()) return null;
    const [h, m] = String(SC.clock ? SC.clock() : "").split(":").map(Number);
    if (!(h >= 0)) return null;
    const d = h * 60 + m - BELL.at;
    return d >= 0 && d < BELL.open ? "open" : d >= -BELL.soon && d < 0 ? "soon" : null;
  }
  function bellChip() {
    const b = $("cvBell"); if (!b) return;
    const s = bellState();
    b.hidden = !s; b.classList.toggle("go", s === "open"); b.disabled = s !== "open";
    b.textContent = s === "open" ? T("🔔 Answer the evening bell") : T("🔔 The evening bell at eight");
  }
  /* one more move today, earned in the game: like the bell, it first gives back a move spent, so a day that was over goes on */
  function extraMove(why) {
    if (!G || G.over) return;
    if (G.move > 0) G.move--; else G.spare = (G.spare || 0) + 1;
    save(); hud(); toast(F("One more move today: {x}", { x: why }));
  }
  function answerBell() {
    if (bellState() !== "open") return bellChip();
    G.bell = today();
    if (G.move > 0) G.move--; else G.spare = (G.spare || 0) + 1;
    write(G.me, T("rang back when Tobias rang the evening bell on the pier"), "gift", "pier", 1);
    SND.sfx("yes"); save(); hud(); bellChip();
    toast(T("The whole island rings back at once. The evening tide gives you one more move today."));
  }

  /* ---------- savings and what they buy: the coins left at the end of a campaign are kept in this browser, and at three
     places they pay for something the island keeps: a roof for the school, a lamp for the lighthouse, a stone in Tano's
     circle. Each is a real transaction of that many test AGRS to the place's till, and the relay counts it for everyone
     (The island today). Bought once per campaign; the count is the island's, for good. ---------- */
  const SAVE_KEY = "tauhud-rabbit-savings";
  const savings = () => { try { const v = JSON.parse(store.get(SAVE_KEY) || "null"); if (v && typeof v.coins === "number") return v; } catch (e) {} return { coins: 0, built: {}, campaigns: 0 }; };
  const saveSavings = v => store.set(SAVE_KEY, JSON.stringify(v));
  const BUILDS = {
    roof: { at: "school", n: 60, t: "Pay for a new roof for the school", line: "paid for a new school roof: 60 coins", done: "The new roof is on by evening. Families who care about the school will remember who paid.", fx: () => bump(G.me, p => p.cares.includes("school"), 6) },
    lamp: { at: "book", n: 80, t: "Pay for a new lamp for the lighthouse", line: "paid for a new lighthouse lamp: 80 coins", done: "The new lamp lights the whole bay. More people find their way to the Book at night.", fx: () => { G.lamp = true; } },
    stone: { at: "circle", n: 50, t: "Pay for a stone in Tano’s circle", line: "paid for a stone in Tano’s circle: 50 coins", done: "Tano sets the stone before sunset. Whoever sits on it is listened to a little longer.", fx: () => others(G.me).forEach(c => { G.trust[c] = Math.min(100, G.trust[c] + 10); }) },
  };
  /* the price comes from the savings first and the rest from this campaign's purse, so coins won this week can pay too
     (otherwise a full purse sat next to a greyed-out button). After the campaign the purse is already banked. */
  const purse = () => (G.over ? 0 : Math.max(0, G.coins[G.me] || 0));
  function buildBtn(k) {
    const B = BUILDS[k], v = savings(), done = !!(G.built && G.built[k]), have = v.coins + purse();
    return btn(T(B.t), () => {
      const v = savings(); if (v.coins + purse() < B.n || (G.built && G.built[k])) return;
      const fromSaved = Math.min(v.coins, B.n), fromPurse = B.n - fromSaved;
      v.coins -= fromSaved; v.built[k] = (v.built[k] || 0) + 1; saveSavings(v);
      if (fromPurse) G.coins[G.me] -= fromPurse;
      G.built = G.built || {}; G.built[k] = G.day; B.fx();
      write(G.me, T(B.line), "gift", B.at, B.n, k);
      SND.sfx("coin"); save(); hud(); toast(T(B.done));
      if (UI.card) openCard(B.at, PLACE[B.at]);
    }, { off: done || have < B.n, sub: done ? T("Done this campaign") : have >= B.n ? Fd("{n} coins, from your savings first ({m} saved), then from this campaign ({c}); no move, the island keeps it", { n: B.n, m: v.coins, c: purse() }) : Fd("{n} coins; you have {c} in this campaign and {m} saved. The coins left at the end of a campaign are saved.", { n: B.n, m: v.coins, c: purse() }) });
  }
  /* the coins left when the campaign is over go to the savings, once */
  function bank() {
    if (!G || !G.over || G.banked) return;
    const v = savings(); v.coins += Math.max(0, G.coins[G.me]); v.campaigns++; saveSavings(v); G.banked = true; save();
  }

  /* ---------- ambitions: on day 2 or 3 someone has read what the Book says about you and makes you an offer ----------
     a goal of your own beside the election, with its own ending in the special edition: reached, missed, or betrayed */
  const AMB = {
    fortune: { who: "tobias", at: "pier", name: "The house on the hill", fits: f => f.deal || f.worked || f.rich,
      goal: "Have 150 coins on election day, and the house on the hill is yours, whoever wins.",
      offer: "I read the Book. You like an envelope, and you count. Good. There is a house on the hill nobody has bought since the old governor left. A hundred and fifty coins by election day and it is yours, whoever wins. Governors change. Houses stay.",
      yes: "Then not one coin to Rico. Every shift, every envelope, into the jar. I will keep the key dry.",
      no: "Suit yourself. The hill will still be there. So will I.",
      won: "A hundred and fifty, counted twice. The key is yours. Governors change, houses stay.",
      lost: "Not enough in the jar. The house stays empty, like most promises on this island.",
      check: () => G.coins[G.me] >= 150 },
    reform: { who: "hana", at: "school", name: "The blackboard list", fits: f => f.myLaw || f.boat || f.lunch || f.copy,
      goal: "Have three laws of your own in force by election day.",
      offer: "I keep a list on the blackboard of laws this island needs and never gets. You passed one. Pass two more of your own and the children will learn your name for the right reasons, governor or not.",
      yes: "Good. Three laws. Not promises, laws. I erase one line for every one that passes.",
      no: "Then I leave the list for the next candidate. It is a patient list.",
      won: "Three of yours in force. I erased the list and wrote your name instead. The children asked who you were. I told them.",
      lost: "The blackboard is as full as on day one. The children drew a crab on it. It is a good crab.",
      check: () => G.laws.filter(l => l.by === G.me).length >= 3 },
    kingmaker: { who: "marisol", at: "market", name: "The kingmaker", fits: f => f.pact || f.truth || !f.lead, pick: () => others(G.me).sort((a, b) => total(a) - total(b))[0],
      goal: "Make {x} governor: a pact with {x}, and {x} wins the election.",
      offer: "Everyone wants to win. Boring. Nobody on this island has ever made someone else governor on purpose. The one at the bottom of every count: get them the chair, and I will tell everyone who really did it. That is the only kind of power that lasts.",
      yes: "A pact with them, your vote for their laws, your speeches where it helps them, and your mouth shut. I do the talking later.",
      no: "Pity. It would have been the best story this café ever had.",
      won: "They sit in the chair and have no idea why. I know. Now everyone knows. Coffee is on the house.",
      lost: "Your candidate lost, and the story is just a rumour now. I will still tell it. Badly.",
      betrayed: "You broke the pact with your own candidate. Even for this café, that is a strange story.",
      check: () => pact(G.me, G.amb.x) && G.over.win === G.amb.x, broke: () => G.pacts.some(p => p.broken && p.a === G.me && p.b === G.amb.x) },
    clean: { who: "sam", at: "book", name: "Clean hands", fits: f => !f.lied && !f.deal && !f.broke,
      goal: "Win the election with no rumour paid for, no embassy envelope and no pact broken.",
      offer: "Two days, and not one line in the Book I would be ashamed to read aloud. Rare. Win it like that, no rumours, no envelopes, no pact broken, and I will write the count so that it is read for fifty years.",
      yes: "Then it is simple. Say only what is true, promise only what you will do, and let them shout.",
      no: "As you like. The Book takes every kind of governor. It only reads differently.",
      won: "Governor, and not one line to explain. I wrote the count slowly. It will be read.",
      lost: "Clean to the end, and the island chose someone else. The Book is kinder to you than the ballot was.",
      betrayed: "You slipped. One rumour, one envelope, one pact. The Book does not shout about it. It does not need to.",
      check: () => G.over.win === G.me && !dirty(), broke: () => dirty() },
  };
  const dirty = () => G.lies.some(l => l.by === G.me && l.lie) || G.deals.some(d => d.by === G.me) || G.pacts.some(p => p.broken && p.a === G.me);
  const ambGoal = () => Fd(AMB[G.amb.id].goal, { x: nm(G.amb.x) });
  /* after the morning paper on day 2 and 3: the first offer that fits what the Book has seen, each one made only once */
  function offerAmbition() {
    if (!G || G.over || G.amb || G.day < 2 || G.day > 4) return;
    const f = facts(), id = ["fortune", "reform", "clean", "kingmaker"].find(k => AMB[k].who !== G.me && !(G.declined || []).includes(k) && AMB[k].fits(f));
    if (!id) return;
    const A = AMB[id], x = A.pick ? A.pick() : null;
    openCard(A.at, box => scene(box, A.who, T("An offer"), [S(A.offer)], [
      btn(T("Yes, I want that"), () => { G.amb = { id, x, day: G.day }; G.declined = (G.declined || []).filter(k => k !== id); write(G.me, Fd("took {x}’s offer: {y}", { x: nm(A.who), y: T(A.name) }), "talk", A.at); save(); hud(); openCard(A.at, b => scene(b, A.who, T(A.name), [S(A.yes)], [btn(T("Continue"), () => closeCard(), { go: true })], el("p", { class: "cv-note", text: ambGoal() }))); }, { go: true }),
      btn(T("No, thank you"), () => { (G.declined = G.declined || []).push(id); save(); openCard(A.at, b => scene(b, A.who, T("No offer"), [S(A.no)], [btn(T("Continue"), () => closeCard(), { go: true })])); }),
    ], el("p", { class: "cv-note", text: Fd(A.goal, { x: nm(x) }) })));
  }
  /* how it ended: reached, betrayed or missed, and the house on the hill is really bought */
  function ambOutcome() {
    if (!G.amb) return null;
    const A = AMB[G.amb.id];
    const how = A.check() ? "won" : A.broke && A.broke() && A.betrayed ? "betrayed" : "lost";
    if (how === "won" && G.amb.id === "fortune" && !G.amb.paid) { G.amb.paid = true; G.coins[G.me] -= 150; write(G.me, T("bought the house on the hill: 150 coins to the island"), "deal", "hall", 150); save(); hud(); }
    return { A, how, line: T(A[how]) };
  }

  /* ---------- Radio Coco: Rico at the microphone, now and then, about what is going on ---------- */
  const DJ = { said: null, text: "", face: null, next: performance.now() + 2500, last: -1 };
  if ($("cvDJ")) { DJ.face = portrait("rico", 40); $("cvDJ").append(DJ.face); }   // Rico is at the microphone from the start, not only once he first speaks
  /* a phone call on the strip: one turn at a time, with who is speaking, each for its share of the time they talk */
  const TURN = { timers: [] };
  function turns(parts, secs) {
    TURN.timers.forEach(clearTimeout); TURN.timers = [];
    const said = parts.filter(p => p.v), total = said.reduce((n, p) => n + p.v.length, 0) || 1, out = $("cvNews");
    let at = 0;
    said.forEach(p => {
      const name = p.who ? p.who[0].toUpperCase() + p.who.slice(1) : "Rico";
      TURN.timers.push(setTimeout(() => { if (out) linkBlocks(out, name + ": " + p.t); }, at * 1000));
      at += (secs ? secs * p.v.length / total : Math.max(2.5, p.t.length * 0.06));
    });
    return at;
  }
  /* "block 4639" in what Rico says opens that block in the explorer, in a new tab */
  function linkBlocks(el, text) {
    el.textContent = ""; const re = /(\bblock\s+|区块\s*|ブロック\s*)(\d+(?:,\d{3})*)/gi; let last = 0, m;
    while ((m = re.exec(text))) {
      el.append(text.slice(last, m.index));
      const a = document.createElement("a"); a.className = "blk"; a.href = "../explorer/?b=" + m[2].replace(/,/g, ""); a.target = "_blank"; a.rel = "noopener";
      a.title = T("Open this block in the explorer"); a.textContent = m[0]; a.addEventListener("click", e => e.stopPropagation()); el.append(a); last = re.lastIndex;
    }
    el.append(text.slice(last));
  }
  /* resolves with the seconds he talks (false when only shown) */
  function onAir(line, urgent, call) {
    const box = $("cvRadio"); if (!box) return Promise.resolve(false);
    if (!DJ.face) { DJ.face = portrait("rico", 40); $("cvDJ").append(DJ.face); }
    const parts = typeof line === "string" ? [{ t: line, v: null }] : line;
    line = join(parts);
    DJ.text = line; box.classList.add("live");
    const out = $("cvNews"); out.textContent = ""; let i = 0;
    clearInterval(DJ.type); TURN.timers.forEach(clearTimeout); TURN.timers = [];
    if (call) { const t = turns(parts, 0); clearTimeout(DJ.off); DJ.off = setTimeout(() => box.classList.remove("live"), t * 1000 + 800); DJ.next = performance.now() + t * 1000 + 30000; }
    else DJ.type = setInterval(() => { i = Math.min(line.length, i + 2); out.textContent = line.slice(0, i); if (i >= line.length) { clearInterval(DJ.type); linkBlocks(out, line); } }, 28);
    say(DJ.face, Math.min(6000, 700 + line.length * 45));
    if (!urgent) SND.sfx("jingle");
    if (!call) { clearTimeout(DJ.off); DJ.off = setTimeout(() => box.classList.remove("live"), Math.min(9000, 2500 + line.length * 60)); DJ.next = performance.now() + 38000 + Math.random() * 30000; }
    /* his voice, when the clips are there: the mouth and the on-air light follow it */
    const said = DJ.text;
    /* in a place the strip only shows it, so nobody talks over the one in front of you; at Radio Coco itself Rico
       says it on air whenever he is not talking to you, and you see him say it */
    const atRico = () => UI.card && UI.at === "radio" && UI.card._who === "rico" ? UI.card : null;
    if (UI.card && !(atRico() && !SND.talking)) return Promise.resolve(false);
    return RICO.speak(parts).then(secs => {
      if (!secs || DJ.text !== said) return secs;
      const here = atRico(); if (here && here._f) say(here._f, secs * 1000);
      if (call) turns(parts, secs);
      say(DJ.face, secs * 1000);
      clearTimeout(DJ.off); DJ.off = setTimeout(() => box.classList.remove("live"), secs * 1000 + 800);
      DJ.next = Math.max(DJ.next, performance.now() + secs * 1000 + 30000);
      return secs;
    }, () => false);
  }
  /* Rico does not repeat himself: the lines he said lately are remembered in this browser, across visits, and he picks
     from the ones he has not said. A set is a group of lines that can stand in for each other (rico.js SETS). */
  const SAID = (() => { try { const a = JSON.parse(store.get("rabbit-dj-said") || "[]"); return Array.isArray(a) ? a : []; } catch (e) { return []; } })();
  const unsaid = keys => { const k = keys.filter(x => !SAID.includes(x)); return k.length ? k : [keys.slice().sort((a, b) => SAID.indexOf(a) - SAID.indexOf(b))[0]]; };
  /* with the sound on, Rico picks among the lines that already have his voice (new lines wait for theirs, shown as text only otherwise) */
  const pickLine = keys => { const v = SND.on && RICO.voiced ? keys.filter(x => RICO.voiced(x) !== false) : keys, k = unsaid(v.length ? v : keys); return k[Math.floor(Math.random() * k.length)]; };
  const markSaid = k => { const i = SAID.indexOf(k); if (i >= 0) SAID.splice(i, 1); SAID.push(k); SAID.splice(0, Math.max(0, SAID.length - 120)); store.set("rabbit-dj-said", JSON.stringify(SAID)); };
  const one = (set, ...more) => { const k = pickLine(RICO.SETS[set]); return { k, parts: [V(k), ...more] }; };
  /* what Rico can say about the game as it stands, and a few lines from the island's habits */
  function djLines() {
    if (!G) return [];
    const L = [], laws = G.laws, by = {}; laws.forEach(l => { if (l.by !== ISLE_BY) by[l.by] = (by[l.by] || 0) + 1; });
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
    isleLines().forEach(l => L.push(l));
    dejaLines().forEach(l => L.push(l));
    return L;
  }
  /* Rico reads the real testnet (or the simulation, in simulation mode) every minute and a half: the newest blocks and
     the waiting list. From them come the chain weather and the news: what kind of transactions the new blocks hold,
     ghosts (live only: sealed transactions the node still lists as waiting, IDNI #81, counted by the relay), and in
     the simulation the refusals, a consensus switch voted on or in force, and the restart at midnight UTC. */
  const RADAR = { snap: null, busy: false, seen: 0, mode: null, rules: null, ghosts: 0, ghostAt: 0, flagged: {}, news: [] };
  const DJ_S = { s: null, at: 0 };   // Déjà's day as the relay last told it (GET /deja)
  const RANK = ["nowStake", "nowFixed", "toStake", "toFixed", "restart", "midnight", "valIn", "valOut", "nodeMany", "nodeNew", "nodeGoneMany", "nodeGone", "feeUp", "feeDown", "rev", "refusedLaw", "whale", "deja", "place", "rival", "cafe", "founders", "unknown", "first", "mixed", "relay", "ghost", "ghostHalloween", "ghostAfter", "law", "lawSim", "back", "cosign", "lock", "offerYes", "offer", "refusedOwn", "rule", "cosvote", "lawVote", "burst", "refused", "duet", "record", "solo", "postman", "fresh"];
  const KIND = { rule_deploy: "rule", approval_request: "cosign", transfer_vote: "cosvote", retractable_transfer: "lock", retract_transfer: "back", rule_offer: "offer", rule_offer_accept: "offerYes", consensus_rule_vote: "lawVote" };
  const txKind = tx => { const t = tx.tx_type || "user_tx"; return t === "user_tx" && tx.operations && tx.operations["0"] ? "rule_deploy" : t; };
  /* the ghosts by the visitor's calendar: fitting in Halloween week, a nuisance in the first week of November, ordinary news otherwise */
  const ghostSeason = () => { const d = new Date(), m = d.getMonth(), day = d.getDate(); return m === 9 && day >= 24 ? "ghostHalloween" : m === 10 && day <= 7 ? "ghostAfter" : "ghost"; };
  /* x, for a wave: keys (the lines of the set that fit), v (the numbers shown), s (the bands spoken), more (parts shown after) */
  function heard(set, h, x) {
    if (!set) return;
    if (RADAR.news.some(n => n.set === set)) return;
    RADAR.news.push({ set, h, at: performance.now(), ...(x || {}) });
    RADAR.news.sort((a, b) => RANK.indexOf(a.set) - RANK.indexOf(b.set)); RADAR.news.length = Math.min(RADAR.news.length, 6);
  }
  /* ---------- where a wave comes from, as far as the blocks show it ----------
     A transaction names a sender, a receiver and an amount, nothing else. Rico knows the island's own addresses (the jars,
     the council's chest, the four ballot boxes, Déjà's bowl), Agorzilla's bowl and boxes across the bay, the rivals'
     campaign wallets (the island bot's, relay GET /island) and the eleven wallets the lagoon started with (IDNI's genesis
     accounts, infra/relay/txsources.py GENESIS). Every other sender is a wallet he has never seen. A source makes news
     when it carries more than its share of a block: three times the lagoon's average per block over the last six hours
     (relay GET /load, the strain page), at least one more than usual; while the average is nought, as it mostly is, the
     first transaction after a quiet hour is the news. One call per source an hour; a mixed wave with no leader gets its
     own line; the rivals and the pier bell are counted over the reading (up to two minutes), not the block. The relay's
     own refusals (our door, not the chain's) come from the same page. Live chain only: the simulation's addresses mean
     nothing. The lines are rico.js SETS founders, place, rival, cafe, unknown, relay, first and mixed. */
  const GENESIS = new Set(["f427fbf4cb8cc5ebcfc50add98ba574b94c03b1e32626e2e50cf60ba5e0a6d0c42d3ed702c2e0eeef7fae29bc4f3d2f9", "838d089401687e4ba5fe844f1241b2f6cf63cf73a7f8fb6aa0e45b3c6b85454f4e7ca19960b71d847655486495b64cb4",
    "93da919aed3b83e517190b8362528b35cbd51beb754289c5d99db12a306ac7f4980fbb96108a9cb812a46aede0c5f9ca", "8a39b9d9498535492290c52b44959b5a6e9177dc85ae6a1d97f54462f03c15a38052a85c7ace5cd81858e343a3b789d0",
    "b1337fcdf8d713a53518f0d6289c70bec2a09a7d6ec84548aac208988391cd66a9b627d03c07d922cd6ad15ebecf3ad7", "b3566dd294833030380d74b39fdb0bf214e9c64906b175f8822c3d4386602b1a9340231e553f9c299d6d8a82b9d441da",
    "af1d997703d7c0a86a5988762bb9ac2642890b5f0599f9821372684487d580a5f211ec160c038c073cda604c3c646487", "9689f5f8ffe6b73bb549e4058e54a3fc6a96ef2e784c415adeffd83d9488c9b435f075b59a778308f86226074f8b09b0",
    "916b92be0561ee21d042d033cabdf58d1c2f9ed110b2e173ab9cdd2a585442bec6232ffe0d97b779976a1dfd6a9d38fc", "b9e4b8fbe06a12f4702617f71ef031206426c4205ca0bc3436d2e0cb047fd18473ad125ceefc7ef18b851a19af2f370b",
    "8df32da800ad4b0657e333774889e6b08f768ab055ffb964d5935bbc8460aa8f91fa60a6a042f64ec144c7ec18ae02a3"]);
  const AGZ = {   // agorzilla.com (agorilla assets/core.js): the bowl, the three ballot boxes, the five question boxes
    bowl: "947c2b8988769f9fb7ada19021e27c51f5d855e4e05ad258d2ca2322821987dbff93e0425f281edded5c372b97e6a108",
    boxes: new Set(["931c4e3b949dd5a77c226e2409f617aa9603f15075f20902c849855f24fb5439113afa3869fc415a3786fe5f30321392", "92cfce4449523a48ab02f88d5acfa85b74860c87eaf501c48320c99a8a142191ba022199c3b20474ff19f7b72f4563a4", "afbdeb43eb62d4a95f2f679686488a14a033cbddb45dec0ac7181d40a668f4af3c8b1c9df05b3b2bc33e664a2a8dd98b"]),
    asks: new Set(["ad628e861687c726aa780c4af1d4e10df4e16c169772686ada8ed81e430ec7bd70214bb732d9b7a75fb4d968136cec86", "940bad7f401e65b0ddfd2b891251cdb3f027dc96bbe4d64b5ea5547900338107186cc23d500c1888598ccc4343f6df2e", "b6bdcade83f317c5a3e0402466a4f6c93a1b9018a3dd61026143c8284741fad2deeffda9a7fd3db587e86f4f44de3418", "992d87e93030634c581fc3e6c574af0da06c70798d49f82135d8231147b79c071e277616d84fb6175dbeae2264377071", "b09ad0b1742efd5a4a4e7fa93a52b9f5954466ca2f694db9dfda4d593d9c15a73dfdd9055ad286e8f11f76b0f69395cf"]),
  };
  const BALLOT = new Set([ADDR.marisol, ADDR.tobias, ADDR.baako, ADDR.hana]);
  const SRC = { bots: {}, ship: new Set(), avg: 0, title: "", at: {}, pairs: {}, hour: -1, known: null, gerald: null, fed: null, lastTx: null };
  const lc = x => String(x || "").toLowerCase();
  const jarName = pk => pk === ADDR.council ? "council" : Object.keys(TILL).find(k => TILL[k] === pk) || null;
  const placeName = at => at === "council" ? "the council hall" : at === "ballot" ? "the ballot boxes" : (SC.places[at] || {}).name || at;   // English: the line around it is translated whole
  const share = () => SRC.avg < 0.25 ? 1 : Math.ceil(Math.max(3 * SRC.avg, SRC.avg + 1));   // a source's share of a block before Rico calls it
  const band = n => RICO.BANDS.count[n < 4 ? 0 : n < 10 ? 1 : n < 20 ? 2 : n < 100 ? 3 : 4];
  const coinBand = a => RICO.BANDS.coins[a < 1000 ? 0 : a < 10000 ? 1 : a < 100000 ? 2 : 3];
  /* a wave's numbers: shown exactly, spoken as the band (rico.js BANDS), the block ({where}) as "block 1234" and "the latest block" */
  const wave = (n, h, spoken) => ({ v: { n, where: "block " + h }, s: { n: spoken || band(n), ...RICO.BLOCK } });   // English: the line is translated whole, the block with it
  /* one call per source an hour */
  const call = (src, set, h, x) => { const now = performance.now(); if (now - (SRC.at[src] || -1e9) < 3600000) return false; SRC.at[src] = now; heard(set, h, x); return true; };
  function sources(nb, s) {
    if (s.sim || !nb.length || !window.RICO || !RICO.BANDS) return;
    const T0 = share(), hour = Math.floor(Date.now() / 3600000), nowS = Date.now() / 1000;
    if (hour !== SRC.hour) { SRC.hour = hour; SRC.pairs = {}; }
    const rival = {}, pier = { n: 0, h: null }, b0 = berlin(), bell = b0.h === 20 && b0.m < 5, RV = { marisol: "rv1", tobias: "rv2", baako: "rv3", hana: "rv4" };
    const stamp = b => { const t = Number(b.header.timestamp) || 0; return t > 1e12 ? t / 1000 : t; };
    /* the wallets Rico has seen: on the first reading, the senders in the blocks from before the page opened */
    if (!SRC.known) SRC.known = new Set(s.bs.filter(b => !stamp(b) || nowS - stamp(b) > 900).flatMap(b => (b.transactions || []).map(tx => lc(tx.sender_pubkey)).filter(Boolean)));
    const fire = (c, h) => {
      if (c.coins) return call(c.src, c.set, null, { keys: c.keys, ...wave(c.n, h, coinBand(c.n)) });
      if (c.set === "founders") {
        const keys = c.triple ? ["fw1"] : c.topN >= 2 ? ["fw4"].concat(SRC.gerald === c.top && SAID.includes("fw4") ? ["fw5"] : []) : ["fw2", "fw3"].concat(SAID.includes("fw4") ? ["fw6"] : []);
        if (c.topN >= 2) SRC.gerald = c.top;
        return call(c.src, c.set, h, { keys, ...wave(Math.max(c.topN, 2), h) });
      }
      if (c.n < 2) {   // one transaction after a quiet hour (one such call an hour, whatever the source)
        if (SRC.lastTx == null || c.ts - SRC.lastTx < 3600) return false;
        return call("first", "first", null, { keys: c.set === "place" ? ["fs1", "fs2", "fs3"] : ["fs2", "fs3"], more: [c.at ? Q("({x}, block {y})", { x: placeName(c.at), y: String(h) }) : Q("(block {y})", { y: String(h) })] });
      }
      return call(c.src, c.set, h, { keys: c.keys, ...wave(c.n, h), more: c.at && c.keys[0] === "pl7" ? [Q("({x})", { x: placeName(c.at) })] : [] });
    };
    for (const b of nb) {
      const h = b.header.block_number, txs = b.transactions || [], ts = stamp(b);
      const place = {}, founders = {}, agz = { bowl: 0, box: 0 }, fresh = new Set(), big = [], newBig = [], senders = new Set();
      let triple = false;
      for (const tx of txs) {
        if (txKind(tx) !== "user_tx") continue;
        const from = lc(tx.sender_pubkey); if (SRC.ship.has(from)) continue;   // a cruise ship's simulated passengers are nobody's wave
        if (from) senders.add(from);
        for (const op of (tx.operations || {})["1"] || []) {
          if (!op) continue;
          const to = lc(op[1]), amt = Number(op[2]) || 0, bot = SRC.bots[from], jar = jarName(to);
          if (bot) rival[bot] = (rival[bot] || 0) + 1;
          else if (jar) place[jar] = (place[jar] || 0) + 1;
          else if (BALLOT.has(to)) place.ballot = (place.ballot || 0) + 1;
          else if (to === DEJA.bowl) continue;   // her meals are their own news (notice)
          else if (to === AGZ.bowl) agz.bowl++;
          else if (AGZ.boxes.has(to)) agz.box++;
          else if (AGZ.asks.has(to)) continue;
          else if (GENESIS.has(from)) { founders[from] = (founders[from] || 0) + 1; const k = from + "|" + to + "|" + amt; SRC.pairs[k] = (SRC.pairs[k] || 0) + 1; if (SRC.pairs[k] === 3) triple = true; }
          else { const seen = SRC.known.has(from); if (!seen) fresh.add(from); if (!seen && amt >= 1000) newBig.push(amt); else if (amt >= 10000) big.push(amt); }
        }
      }
      pier.n += place.pier || 0; pier.h = h;
      if (SRC.known) senders.forEach(k => SRC.known.add(k));
      const old = !ts || nowS - ts > 900;   // blocks from before the page opened are weather, not news
      if (!old) {
        const cands = [];
        for (const p in place) if (place[p] >= T0) cands.push({ n: place[p], src: "place:" + p, set: "place", at: p, keys: { pier: ["pl1"], market: ["pl3"], council: ["pl4"], radio: ["pl5"], ballot: ["pl6"] }[p] || ["pl7"] });
        const fk = Object.keys(founders), fTop = fk.sort((a, b) => founders[b] - founders[a])[0], fSum = fk.reduce((a, k) => a + founders[k], 0);
        if (fSum >= T0) cands.push({ n: fSum, src: "founders", set: "founders", top: fTop, topN: founders[fTop] || 0, triple });
        if (agz.bowl >= T0) cands.push({ n: agz.bowl, src: "cafe", set: "cafe", keys: ["cz1"] });
        if (agz.box >= T0) cands.push({ n: agz.box, src: "cafe", set: "cafe", keys: ["cz2"] });
        if (fresh.size >= Math.max(2, T0)) cands.push({ n: fresh.size, src: "unknown", set: "unknown", keys: ["un2"] });
        if (newBig.length) cands.push({ n: Math.max(...newBig), src: "unknown", set: "unknown", keys: ["un1", "un4"], coins: true });
        else if (big.length) cands.push({ n: Math.max(...big), src: "unknown", set: "unknown", keys: ["un3"], coins: true });
        cands.sort((a, b) => b.n - a.n);
        const lead = cands[0];
        if (lead) fire({ ...lead, ts }, h);
        else if (senders.size >= 3 && txs.length >= Math.max(3, T0)) call("mixed", "mixed", h, { keys: ["dk3"], ...wave(senders.size, h) });
      }
      if (txs.length) SRC.lastTx = ts || SRC.lastTx;
    }
    const top = nb[nb.length - 1].header.block_number, fresh = !(!stamp(nb[nb.length - 1]) || nowS - stamp(nb[nb.length - 1]) > 900);
    if (fresh) for (const who in rival) if (rival[who] >= Math.max(2, T0) && RV[who]) call("rival:" + who, "rival", top, { keys: [RV[who]], ...wave(rival[who], top) });
    if (fresh && bell && pier.n >= 2) call("bell", "place", null, { keys: ["pl2"], ...wave(pier.n, pier.h) });
  }
  /* what the relay knows that the blocks do not: the rivals' wallets, the lagoon's average per block and the refusals of
     the last hour, and the title of the builders' latest change (node.tauhud.com/devpulse.json), read every ten minutes */
  /* nodes joining and leaving (the relay's /peers: only nodes our node has known for ten minutes, so a test that comes
     and goes in a minute stays out). This browser remembers the nodes it has seen, so a node that joined while you were
     away is still news when you come back the same day; the very first look only learns them. Several at once are one
     line; a community node's name is shown beside it. */
  const NODES = { seen: null, online: null, KEY: "rabbit-nodes-seen" };
  function nodesRead(j) {
    if (!j || !Array.isArray(j.peers)) return;
    const now = Date.now() / 1000, steady = j.peers.filter(p => p && p.id && p.steady), online = new Set(steady.filter(p => p.online).map(p => p.id));
    if (!NODES.seen) { try { const o = JSON.parse(store.get(NODES.KEY) || "null"); NODES.seen = o && typeof o === "object" ? o : null; } catch (e) { NODES.seen = null; } }
    const first = !NODES.seen; NODES.seen = NODES.seen || {};
    const fresh = steady.filter(p => p.online && !NODES.seen[p.id] && now - (Number(p.first_seen) || 0) < 43200);
    steady.forEach(p => { NODES.seen[p.id] = Math.round(now); });
    for (const id in NODES.seen) if (now - NODES.seen[id] > 30 * 86400) delete NODES.seen[id];
    store.set(NODES.KEY, JSON.stringify(NODES.seen));
    const count = Q("({n} nodes online now)", { n: online.size + 1 });   // and ours
    if (!first && fresh.length) {
      const names = fresh.map(p => p.community && p.community.name).filter(Boolean).slice(0, 3), more = [...names.map(x => Q("“{x}”", { x: String(x).slice(0, 40) })), count];
      if (fresh.length === 1) call("nodeNew", "nodeNew", null, { more });
      else call("nodeNew", "nodeMany", null, { v: { n: fresh.length }, s: { n: band(fresh.length) }, more });
    }
    if (NODES.online) {
      const gone = [...NODES.online].filter(id => !online.has(id) && id !== j.bootnode);
      if (gone.length === 1) call("nodeGone", "nodeGone", null, { more: [count] });
      else if (gone.length > 1) call("nodeGone", "nodeGoneMany", null, { v: { n: gone.length }, s: { n: band(gone.length) }, more: [count] });
    }
    NODES.online = online;
  }
  function srcFetch() {
    if (window.TauSim && TauSim.on) return;
    const get = u => fetch("https://node.tauhud.com/" + u, { cache: "no-store" }).then(r => (r.ok ? r.json() : null));
    get("peers").then(nodesRead, () => {});
    get("island").then(j => { if (j && j.wallets) { SRC.bots = {}; Object.keys(j.wallets).forEach(k => { SRC.bots[lc(j.wallets[k])] = k; }); } }, () => {});
    get("load").then(j => {
      if (!j || !Array.isArray(j.sealed)) return;
      const sum = a => (a || []).reduce((x, y) => x + (Number(y) || 0), 0), blocks = sum(j.blocks);
      SRC.avg = blocks ? sum(j.sealed) / blocks : 0;
      const r = j.refused || [], m = Math.max(Number(r[r.length - 1]) || 0, Number(r[r.length - 2]) || 0), hr = Number((j.now || {}).refused_hour) || 0;
      if (m >= 3) call("relay", "relay", null, { keys: ["rf1"], v: { n: m }, s: { n: band(m) } });
      else if (hr >= 10) call("relay", "relay", null, { keys: ["rf2"], v: { n: hr }, s: { n: band(hr) } });
    }, () => {});
    get("devpulse.json").then(j => { const t = String((((j || {}).repos || [])[0] || {}).head && j.repos[0].head.title || "").trim(); SRC.title = t.length >= 8 && t.length <= 70 && !/\n/.test(t) ? t : ""; }, () => {});
  }
  /* ---------- cruise ships (relay cruise.py): MS Dry Run on Wednesdays at four, Queen Mempool on Saturdays at two, German time.
     The passengers are simulated, and the chip and the card say so; what they do ashore is real: every stop is a test
     transaction to the place's till, at most twelve a minute, sent by our relay when the island bot has nothing to send,
     half as many while the testnet strains, and the ship leaves at once if it stalls or the node refuses its passengers'
     transactions (the card says which). The island shows the ship, its tenders, a guide's pennant where a
     group is, and a ring at a place whenever one of their transactions is sealed in a block.
     ?ship=dryrun or ?ship=queen shows a made-up visit, marked as a preview; it sends nothing. ---------- */
  const SHIPV = { v: null, next: null, last: null };
  const SHIPAT = { works: "The Coconut Works", school: "The School", dive: "Reef Proof Dive Centre", ship: "The Old Ship" };   // places only a painted island's layout brings
  const berlinHM = s => { try { return new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Berlin", hour: "2-digit", minute: "2-digit" }).format(new Date(s * 1000)); } catch (e) { return new Date(s * 1000).toISOString().slice(11, 16); } };
  /* &phase=soon, tomorrow, today or close (two hours or less): no ship on the sea yet, only the islanders and Rico
     talking about it (shipFacts); approach, wait (off the reef, for a calm lagoon), land (the tenders), turn (back aboard),
     gone; cut: it sailed on without landing (&why=stalled or refused: it left early) */
  function shipPreview(k) {
    const now = Math.floor(Date.now() / 1000), q = k === "queen", qs = new URLSearchParams(location.search), phase = qs.get("phase");
    if (phase === "soon" || phase === "tomorrow" || phase === "today" || phase === "close") return null;
    const why = phase === "cut" ? (/^(stalled|refused)$/.test(qs.get("why") || "") ? qs.get("why") : "no landing") : "";
    if (k === "pirates") return { ship: k, name: "Black Sequence", style: "pirate", why,   // the pirates stay aboard: nobody ashore
      phase: phase === "approach" || phase === "gone" ? phase : phase === "cut" ? "gone" : phase === "turn" ? "boarding" : phase === "wait" ? "waiting" : phase === "land" ? "landing" : "ashore",
      t0: phase === "approach" ? now + 90 : phase === "wait" ? now - 120 : phase === "land" ? now - 240 : now - 1800,
      end: phase === "gone" || phase === "cut" ? now : phase === "turn" ? now + 90 : now + 3600, passengers: 20, ashore: 0, at: {},
      sent: { pay: 38, bill: 0, book: 0, cancel: 0 }, refused: 0, tricks: { tried: 9, stopped: 9 }, kinds: ["pay", "trick"], preview: true };
    return { ship: k, name: q ? "Queen Mempool" : "MS Dry Run", style: q ? "liner" : "expedition",
      phase: phase === "approach" || phase === "gone" ? phase : phase === "cut" ? "gone" : phase === "turn" ? "boarding" : phase === "wait" ? "waiting" : phase === "land" ? "landing" : "ashore",
      why, t0: phase === "approach" ? now + 90 : phase === "wait" ? now - 120 : phase === "land" ? now - 240 : now - 1800,
      end: phase === "gone" || phase === "cut" ? now : phase === "turn" ? now + 90 : now + 3600, passengers: q ? 120 : 40,
      ashore: q ? 96 : 34, at: q ? { south: 30, bar: 26, radio: 12, market: 18, works: 6, pier: 4 } : { book: 8, ship: 9, school: 6, dive: 8, pier: 3 },
      sent: { pay: q ? 214 : 96, bill: q ? 5 : 0, book: q ? 21 : 5, cancel: q ? 2 : 1 }, refused: 0, kinds: q ? ["pay", "bill", "book"] : ["pay", "book"], preview: true };
  }
  function shipFetch() {
    const k = new URLSearchParams(location.search).get("ship");
    if (k === "dryrun" || k === "queen" || k === "pirates") { if (!SHIPV.v?.preview) SHIPV.v = shipPreview(k); return shipShow(); }
    if (window.TauSim && TauSim.on) return;
    fetch("https://node.tauhud.com/cruise", { cache: "no-store" }).then(r => (r.ok ? r.json() : null)).then(j => {
      if (!j) return;
      SRC.ship = new Set([].concat(...Object.values(j.wallets || {})).map(lc));
      SHIPV.v = j.now || null; SHIPV.next = j.next || null; SHIPV.last = j.last || null;
      shipShow(); shipNews(SHIPV.v); shipLoad();
    }, () => {});
  }
  /* the ships' week as the islanders and Rico talk about it (talk.js RABBIT_SHIP_WHEN): from the relay's timetable, or
     from the preview (?ship=queen or dryrun, &phase=soon, tomorrow, today, approach, turn, gone or cut; none: ashore) */
  const SHIP_SAY = { soon: "shipSoon", tomorrow: "shipTomorrow", today: "shipToday", close: "shipToday", approach: "shipToday", wait: "shipToday", land: "shipHere", turn: "shipHere", gone: "shipGone", cut: "shipCut" };
  function shipFacts() {
    const W = window.RABBIT_SHIP_WHEN, k = QS.get("ship"); if (!W) return {};
    if (k === "dryrun" || k === "queen") return W.mark(k, SHIP_SAY[QS.get("phase")] || "shipHere");
    return W({ now: SHIPV.v, next: SHIPV.next, last: SHIPV.last }, Date.now() / 1000);
  }
  /* ---------- Rico on the ships: the nearer a ship, the more he talks about it (rico.js SETS ship*) ----------
     shipStage says where the week stands: soon (in two or three days), tomorrow, today, close (two hours or less), then
     the visit (approach: in sight; wait: off the reef until the lagoon is calm or busy; land: the tenders; here: ashore;
     board: the last ten minutes) and the rest of that day (gone, or cut, with the logbook's reason). shipOdds makes that
     the share of Rico's lines about the ship: about one in twenty-five two or three days before, more and more through
     the last day, four or five in ten while she is in, fading over the evening after. Before she lands he never says two
     in a row, in port two at most; now and then a listener calls about her instead.
     In port he says what the testnet shows, the numbers shown exactly and spoken as a band (rico.js NUMERIC): the
     passengers' transactions the node has taken so far and those in the newest block, a booking, a withdrawal, a group
     bill or a refusal since the last look (relay GET /cruise every minute, shipNews), the brakes, how the lagoon copes
     (GET /load every two minutes while she is in) and where most of the passengers are. A preview (?ship=) has made-up
     numbers, and every line of it says preview. */
  const SHIPLIVE = { visit: null, sent: null, refused: 0, brake: "none", ev: [], block: null, load: null, loadAt: 0, top: null, said: {}, recap: null };
  const SHIP_P = { approach: 0.4, wait: 0.45, land: 0.45, here: 0.4, board: 0.45 };
  const shipOdds = st => !st ? 0 : SHIP_P[st.stage] != null ? SHIP_P[st.stage]
    : st.after != null ? 0.05 + 0.3 * Math.exp(-st.after / 1.5) : Math.min(0.35, 0.04 + 0.45 * Math.exp(-st.h / 8));
  const shipWhy = note => /^no landing/.test(note || "") ? "no landing" : /^left early/.test(note || "") ? (/refused/.test(note) ? "refused" : "stalled") : "";
  function shipStage() {
    const f = shipFacts(); if (!f.ship) return null;
    const now = Date.now() / 1000, ship = f.queen ? "queen" : "dryrun", v = SHIPV.v, pv = QS.get("ship") === ship;
    const st = { ship, q: ship === "queen", preview: pv }, PH = { approach: "approach", waiting: "wait", landing: "land", ashore: "here", boarding: "board" };
    if (v && PH[v.phase]) return Object.assign(st, { stage: PH[v.phase], v, h: Math.max(0, (v.t0 - now) / 3600) });
    if (v && v.phase === "gone") return Object.assign(st, { stage: v.why ? "cut" : "gone", why: v.why || "", v, after: Math.max(0, (now - v.end) / 3600) });
    if (f.shipAfter) { const l = SHIPV.last || {}; return Object.assign(st, { stage: f.shipCut ? "cut" : "gone", why: shipWhy(l.note), v: SHIPV.last, after: Math.max(0, (now - (l.end || now)) / 3600) }); }
    const n = SHIPV.next, h = pv ? { soon: 52, tomorrow: 26, today: 5, close: 1.2 }[QS.get("phase")] || 5 : n && n.t0 ? Math.max(0, (n.t0 - now) / 3600) : null;
    if (h == null) return null;
    return Object.assign(st, { stage: f.shipToday ? (h <= 2 ? "close" : "today") : f.shipTomorrow ? "tomorrow" : "soon", h, t0: pv ? null : n.t0 });
  }
  /* what changed since the last look at the ship in port: bookings, withdrawals, group bills, refusals, the brakes
     (the first look at a visit only sets the counts, so nobody hears old news) */
  function shipNews(v) {
    if (!v || v.preview || !v.visit) return;
    const L = SHIPLIVE, S = v.sent || {};
    if (L.visit !== v.visit) { Object.assign(L, { visit: v.visit, sent: { ...S }, refused: v.refused || 0, brake: v.brake || "none", ev: [], block: null, top: null, said: {} }); return; }
    const was = L.sent || {}, add = k => { if (!L.ev.some(e => e.k === k)) L.ev.push({ k, at: Date.now() }); };
    if ((S.book || 0) > (was.book || 0)) add("book");
    if ((S.cancel || 0) > (was.cancel || 0)) add("cancel");
    if ((S.bill || 0) > (was.bill || 0)) add("bill");
    if ((v.refused || 0) > L.refused) add(v.refused >= 3 ? "ref3" : "ref1");
    if (v.brake === "half" && L.brake !== "half") add("half");
    if (L.brake === "half" && v.brake === "none") add("full");
    L.sent = { ...S }; L.refused = v.refused || 0; L.brake = v.brake || "none";
  }
  /* how the testnet copes while the passengers are ashore (relay GET /load: the verdict of the last ten minutes) */
  function shipLoad() {
    const v = SHIPV.v; if (!v || v.preview || !/^(landing|ashore|boarding)$/.test(v.phase) || Date.now() - SHIPLIVE.loadAt < 110000) return;
    SHIPLIVE.loadAt = Date.now();
    fetch("https://node.tauhud.com/load", { cache: "no-store" }).then(r => (r.ok ? r.json() : null)).then(j => {
      if (!j || !j.now || !/^(calm|busy|strained)$/.test(j.state)) return;
      const was = SHIPLIVE.load && SHIPLIVE.load.state;
      SHIPLIVE.load = { state: j.state, waiting: Number(j.now.waiting) || 0, sealed: Number(j.now.sealed_hour) || 0, cruise: Number(j.now.cruise_hour) || 0, at: Date.now(), changed: !!was && was !== j.state };
    }, () => {});
  }
  /* the passengers' transactions so far, shown beside the spoken band (and on the ship's card) */
  function shipSoFar(S, K, card) {
    const book = K.includes("book") || S.book > 0, bill = K.includes("bill") || S.bill > 0, c = { n: S.pay || 0, m: S.bill || 0, a: S.book || 0, b: S.cancel || 0 };
    return F(card ? (book && bill ? "So far: {n} payments, {m} group bills, {a} bookings, {b} withdrawn." : book ? "So far: {n} payments, {a} bookings, {b} withdrawn." : bill ? "So far: {n} payments, {m} group bills." : "So far: {n} payments.")
      : book && bill ? "({n} payments, {m} group bills, {a} bookings, {b} withdrawn)" : book ? "({n} payments, {a} bookings, {b} withdrawn)" : bill ? "({n} payments, {m} group bills)" : "({n} payments)", c);
  }
  /* the weekday in Germany, in English: a shown line is translated whole, its weekday and place name with it (a filled-in
     word already in Chinese or Japanese would stop the translation of the line) */
  const shipDay = t => { try { return new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Berlin", weekday: "long" }).format(new Date(t * 1000)); } catch (e) { return ""; } };
  const shipName = st => st.q ? "Queen Mempool" : "MS Dry Run";
  const LOADQ = { calm: "(testnet calm: {n} waiting, {m} sealed in the last hour, {a} sent for the ship)", busy: "(testnet busy: {n} waiting, {m} sealed in the last hour, {a} sent for the ship)",
    strained: "(testnet strained: {n} waiting, {m} sealed in the last hour, {a} sent for the ship)" };
  const LOGQ = "(the logbook: tauhud.com/cruise)";
  /* whether Rico can say a line aloud (with the sound on: its clips are there; a line with a band, every band's clip) */
  const sayable = k => !(SND.on && RICO.voiced) || RICO.voiced(k) !== false;
  /* a line with a number: shown exactly, spoken as a band ({where}: shown as the block, spoken as the latest block) */
  const banded = (k, n, h) => ({ t: F(RICO.L[k], h != null ? { n, where: "block " + h } : { n }), v: RICO.fill(RICO.L[k], { n: band(n), ...RICO.BLOCK }) });
  function shipLine() {
    const st = shipStage(), p = shipOdds(st); if (!p) return null;
    const run = ROT.shipAt === ROT.n - 1 ? ROT.shipRun || 0 : 0, port = /^(land|here|board)$/.test(st.stage);
    if (run >= (port ? 2 : 1) || Math.random() >= p) return null;
    const l = shipPick(st); if (!l) return null;
    ROT.shipRun = run + 1; ROT.shipAt = ROT.n; ROT.callLast = !!l.call;
    if (st.preview && !l.call) l.parts.push(Q("(preview)"));
    return l;
  }
  function shipPick(st) {
    const stage = st.stage, v = st.v || {}, r = Math.random(), port = /^(land|here|board)$/.test(stage);
    const line = (keys, ...more) => { keys = (keys || []).filter(k => RICO.L[k]); if (!keys.some(sayable)) return null; const k = pickLine(keys); return { k, parts: [V(k), ...more] }; };
    const why = () => { const l = line(RICO.SETS.shipWhy); if (l && l.k === "sw5") l.parts.push(Q(LOGQ)); return l; };
    const pool = n => RICO.SETS[n + (st.q ? "Q" : "D")] || RICO.SETS[n];
    if (port) { const l = shipPort(st, line); if (l) return l; }
    /* after the visit: her day in numbers, once */
    if ((stage === "gone" || stage === "cut") && v.sent) {
      const S = v.sent, n = Object.values(S).reduce((a, b) => a + (Number(b) || 0), 0), id = v.visit || v.id || v.t0;
      const rf = typeof v.refused === "number" ? v.refused : Object.values(v.refused || {}).reduce((a, b) => a + (Number(b) || 0), 0);
      if (n >= 2 && SHIPLIVE.recap !== id && sayable("sl_recap")) {
        SHIPLIVE.recap = id;
        return { k: "sl_recap", parts: [banded("sl_recap", n), { t: shipSoFar(S, v.kinds || Object.keys(S).filter(x => S[x] > 0), false), v: null }, ...(rf ? [Q("({n} refused by the node)", { n: rf })] : [])] };
      }
    }
    const CALL = { soon: 0.15, tomorrow: 0.15, today: 0.15, close: 0.15, approach: 0.1, here: 0.2, gone: 0.15, cut: 0.1 }[stage] || 0;
    const WHY = { soon: 0.35, tomorrow: 0.35, today: 0.35, close: 0.3, approach: 0.2, wait: 0.25, land: 0.15, here: 0.35, gone: 0.15 }[stage] || 0;
    const when = /^(soon|tomorrow|today|close)$/.test(stage) ? [Q("({x}: {y}, {t} German time)", st.t0 ? { x: shipName(st), y: shipDay(st.t0), t: berlinHM(st.t0) }
        : { x: shipName(st), y: shipDay(Date.UTC(2026, 10, st.q ? 7 : 4, 12) / 1000), t: st.q ? "14:00" : "16:00" })]   // a preview: the ship's weekday and hour
      : stage === "approach" ? [Q("Lands at {t}, German time, with {n} simulated passengers.", { t: berlinHM(v.t0), n: v.passengers })]
      : port && v.passengers ? [Q("{a} of {n} passengers ashore, in port until {t}.", { a: v.ashore || 0, n: v.passengers, t: berlinHM(v.end) })] : [];
    const own = () => stage === "cut" ? line(RICO.SETS[{ "no landing": "shipCutLand", stalled: "shipCutStall", refused: "shipCutRefused" }[st.why] || "shipCut"], Q(LOGQ))
      : line(pool({ soon: "shipSoon", tomorrow: "shipTomorrow", today: "shipToday", close: "shipClose", approach: "shipApproach", wait: "shipWait", land: "shipLand", here: "shipHere", board: "shipBoard", gone: "shipGone" }[stage]), ...when);
    return (r < CALL ? shipCall() : r < CALL + WHY ? why() : null) || own() || why();
  }
  /* what Rico reports while the passengers are ashore, the newest first; null: nothing new, so a line of the stage */
  function shipPort(st, line) {
    const v = st.v || {}, S = v.sent || {}, L = SHIPLIVE, now = Date.now(), ago = k => now - (L.said[k] || 0);
    L.ev = L.ev.filter(e => now - e.at < 240000);
    while (L.ev.length) {
      const e = L.ev.shift(), keys = { book: RICO.SETS.shipBook, cancel: RICO.SETS.shipCancel, bill: RICO.SETS.shipBill, half: ["ss_strain"], full: ["se_full"], ref1: ["se_ref1"], ref3: ["se_ref3"] }[e.k];
      const more = e.k === "book" ? [Q("({n} bookings so far)", { n: S.book || 0 })] : e.k === "cancel" ? [Q("({n} withdrawn so far)", { n: S.cancel || 0 })]
        : e.k === "bill" ? [Q("({n} group bills so far)", { n: S.bill || 0 })] : /^ref/.test(e.k) ? [Q("({n} refused so far)", { n: v.refused || 0 })] : [];
      const l = line(keys, ...more); if (l) return l;
    }
    /* the newest block holds a few of their transactions (the blocks Rico reads anyway, shipSeen) */
    const b = L.block;
    if (b && !b.said && now - b.at < 180000 && ago("block") > 120000) {
      const ks = RICO.SETS.shipBlock.filter(sayable);
      if (ks.length) { const k = pickLine(ks); b.said = 1; L.said.block = now; return { k, parts: [banded(k, b.n, b.h)] }; }
    }
    /* how the lagoon copes: when that changed, or every twelve minutes */
    const ld = L.load;
    if (ld && now - ld.at < 300000 && (ld.changed || ago("load") > 720000)) {
      const l = line(ld.state === "calm" ? RICO.SETS.shipCalm : ld.state === "busy" ? RICO.SETS.shipBusy : ["ss_strain"], Q(LOADQ[ld.state], { n: ld.waiting, m: ld.sealed, a: ld.cruise }));
      if (l) { ld.changed = false; L.said.load = now; return l; }
    }
    /* the tally, every six minutes or so */
    const total = (S.pay || 0) + (S.bill || 0) + (S.book || 0) + (S.cancel || 0);
    if (total >= 2 && ago("total") > 360000 && Math.random() < 0.6) {
      const ks = RICO.SETS.shipTotal.filter(sayable);
      if (ks.length) { const k = pickLine(ks); L.said.total = now; return { k, parts: [banded(k, total), { t: shipSoFar(S, v.kinds || ["pay"], true), v: null }] }; }
    }
    /* where most of them are: when that changed, or every ten minutes */
    const top = Object.entries(v.at || {}).filter(([id, n]) => id !== "pier" && n >= 2 && RICO.L["sa_" + id]).sort((a, b) => b[1] - a[1])[0];
    if (st.stage === "here" && top && (top[0] !== L.top || ago("place") > 600000) && Math.random() < 0.7) {
      const l = line(["sa_" + top[0]], Q("({x}: {n} passengers)", { x: (SC.places[top[0]] || {}).name || SHIPAT[top[0]] || top[0], n: top[1] }));
      if (l) { L.top = top[0]; L.said.place = now; return l; }
    }
    return null;
  }
  /* a listener (or an islander) calls about the ship near: each call once, until Rico has said a lot of other things */
  function shipCall() {
    if (ROT.callLast) return null;
    const sf = shipFacts(), keys = RICO.CALLS.map((c, i) => (c.when && /ship|queen|dryrun/.test(c.when) && holds(sf, c.when) ? "call:" + i : null))
      .filter(x => x && !SAID.includes(x) && sayable(x));
    return keys.length ? dial(keys[Math.floor(Math.random() * keys.length)]) : null;
  }
  function shipShow() {
    if (SC.ship) SC.ship(SHIPV.v);
    const b = $("cvShip"); if (!b) return;
    const v = SHIPV.v, ph = v && v.phase;
    b.hidden = !v || (ph === "gone" && Date.now() / 1000 - v.end > 300);
    if (b.hidden) return;
    b.textContent = (ph === "approach" ? F("🛳 {x} at {t}", { x: v.name, t: berlinHM(v.t0) })
      : ph === "waiting" ? F("🛳 {x} waits offshore", { x: v.name })
      : ph === "gone" ? F("🛳 {x} has left", { x: v.name })
      : v.style === "pirate" ? F("🏴 {x} in port: {n} tricks tried, {m} refused by the chain", { x: v.name, n: (v.tricks || {}).tried || 0, m: (v.tricks || {}).stopped || 0 })
      : F("🛳 {x}: {n} ashore", { x: v.name, n: v.ashore || 0 })) + (v.preview ? " · " + T("preview") : "");
  }
  /* a ring at the place each passenger transaction in a new block paid (a booking: the place it is for); a block with a
     few of them is news for Rico's ship report (shipPort) */
  function shipSeen(nb) {
    if (!SRC.ship.size) return;
    for (const b of nb) {
      let n = 0;
      for (const tx of b.transactions || []) {
        if (!SRC.ship.has(lc(tx.sender_pubkey))) continue;
        n++;
        const k = txKind(tx), tos = k === "user_tx" ? (((tx.operations || {})["1"]) || []).map(op => lc(op && op[1])) : k === "retractable_transfer" ? [lc(tx.recipient_pubkey)] : [];
        if (SC.ping) tos.forEach(to => { const j = jarName(to); if (j && j !== "council") SC.ping(j); });
      }
      if (n >= 2) SHIPLIVE.block = { n, h: b.header.block_number, at: Date.now() };
    }
  }
  function shipCard() {
    const v = SHIPV.v; if (!v) return;
    openCard("pier", box => {
      const S = v.sent || {}, n = Object.values(S).reduce((a, b) => a + (Number(b) || 0), 0), K = v.kinds || ["pay"];
      const book = K.includes("book") || S.book > 0, bill = K.includes("bill") || S.bill > 0;
      const where = Object.entries(v.at || {}).filter(([, k]) => k > 0).sort((a, b) => b[1] - a[1])
        .map(([id, k]) => T((SC.places[id] || {}).name || SHIPAT[id] || id) + " " + k).join(" · ");
      const now = v.phase === "approach" ? F("Lands at {t}, German time, with {n} simulated passengers.", { t: berlinHM(v.t0), n: v.passengers })
        : v.phase === "waiting" ? T("Waiting off the island: it lands only while the testnet is calm.")
        : v.phase === "gone" ? T(v.why === "no landing" ? "It sailed on without landing: the testnet was not calm."
          : v.why === "refused" ? "It left early: the node refused its passengers’ transactions, and the ship took them back at once."
          : "It left early: the testnet stalled, and the ship took its passengers back at once.")
        : v.style === "pirate" ? F("{n} pirates aboard, in port until {t}: {a} tricks tried so far, {b} refused by the chain.", { n: v.passengers, t: berlinHM(v.end), a: (v.tricks || {}).tried || 0, b: (v.tricks || {}).stopped || 0 })
        : F("{a} of {n} passengers ashore, in port until {t}.", { a: v.ashore || 0, n: v.passengers, t: berlinHM(v.end) });
      box.append(el("h3", { text: v.name + (v.preview ? " · " + T("preview") : "") }),
        el("p", { text: T(v.style === "pirate" ? "A pirate ship. Its crew stays aboard and trades from the boat: rum at Bar La Ola, supplies at the market. Now and then a pirate tries a trick the chain must refuse." : v.style === "expedition" ? "A small expedition ship with curious passengers: the lighthouse, Captain Wren’s Old Ship, the school, a dive on the reef." : "A big luxury liner: the spa at the South Current resort, Bar La Ola, song requests on Radio Coco, souvenirs.") }),
        el("ul", { class: "cv-help" },
          el("li", { text: T("Nobody on board is a real person: our relay makes the passengers up. What they do here is real: every stop is a test transaction on Tau Testnet Alpha to the till of the place.") }),
          v.style === "pirate" ? el("li", { text: T("The tricks: paying more than the wallet holds, sending a payment the chain already took a second time, a payment whose time ran out, a payment signed with another pirate’s key. Each one the chain refuses is the chain doing its job; the logbook shows its answer.") }) : null,
          book ? el("li", { text: T("Some book a dive or a treatment with the right to withdraw: the money waits in escrow until its time, then the chain pays the place by itself. A few change their minds and take it back.") }) : null,
          bill ? el("li", { text: T("At Bar La Ola a table pays one bill: a single transaction that pays the bar, Radio Coco and the Coconut Works at once.") }) : null,
          el("li", { text: T("At most twelve transactions a minute, only when the island bot has nothing to send; half as many while the testnet strains, and the ship leaves at once if it stalls. Its logbook keeps every one.") }),
          el("li", { text: now }),
          n || v.phase !== "approach" ? el("li", { text: shipSoFar(S, K, true) }) : null,
          where ? el("li", { text: where }) : null),
        el("div", { class: "cv-acts" },
          btn(T("The logbook"), () => window.open("/cruise/", "_blank", "noopener")),
          btn(T("Testnet load"), () => window.open("/load/", "_blank", "noopener")),
          btn(T("Back to the island"), () => closeCard(), { go: true })));
    });
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
      if (txs.length >= Math.max(10, 3 * share())) heard("burst", n);
      if (txs.some(tx => (((tx.operations || {})["1"]) || []).some(op => op && String(op[1]).toLowerCase() === DEJA.bowl && Number(op[2]) >= 1))) heard("deja", n);
      for (const tx of txs) {
        const k = txKind(tx), paid = k === "user_tx" ? ((tx.operations || {})["1"] || []).reduce((a, x) => a + (Number(x && x[2]) || 0), 0) : Number(tx.amount) || 0;
        if (paid >= 100000) heard("whale", n);
        if (KIND[k] && !SRC.ship.has(lc(tx.sender_pubkey))) heard(KIND[k], n);   // a passenger's booking or withdrawal: Rico's ship report has it (shipNews)
        else if (k === "consensus_rule_update") heard(s.sim ? "lawSim" : "law", n);
      }
      if (s.sim) for (const d of TauSim.chain.dropped(n) || []) heard(d.type === "consensus_rule_update" ? "refusedLaw" : /o5|own rule|its rule/i.test(d.why || "") ? "refusedOwn" : "refused", n);
    }
    sources(nb, s);
    shipSeen(nb);
    if (!s.sim) { chainLife(s); return; }
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
  /* what the real chain shows about itself, as island news: one hand sealing every recent block (and sending nothing
     of its own), a second hand joining in, the chain started over and not yet past its old height (block 5028, where
     the old chain stood still on 1 November 2026), and the moment it passes it. Each at most every 20 minutes. */
  const OLD_TOP = 5028;
  function chainLife(s) {
    const props = new Set(s.bs.map(b => b.header.proposer_pubkey).filter(Boolean)), now = performance.now();
    const once = (set, h) => { RADAR.netAt = RADAR.netAt || {}; if (now - (RADAR.netAt[set] || -1e9) < 1200000) return; RADAR.netAt[set] = now; heard(set, h); };
    const was = RADAR.props || 0; RADAR.props = props.size;
    RADAR.solo = props.size === 1 && s.bs.length >= 6;
    if (props.size >= 2 && was === 1) once("duet", s.h);
    else if (RADAR.solo && Math.random() < 0.5) {
      const p = [...props][0], sent = s.bs.some(b => (b.transactions || []).some(tx => tx.sender_pubkey === p)), any = s.bs.some(b => (b.transactions || []).length);
      once(any && !sent && Math.random() < 0.4 ? "postman" : "solo", s.h);
    }
    RADAR.fresh = s.h < OLD_TOP;
    if (RADAR.fresh && Math.random() < 0.3) once("fresh", s.h);
    if (s.h >= OLD_TOP && s.h < OLD_TOP + 400 && !RADAR.recorded) { RADAR.recorded = 1; heard("record", s.h); }
  }
  /* how long ago the last block came: in minutes, then hours, then days */
  const ago = (y, m) => m < 120 ? Q("(last block {y}, {n} minutes ago)", { y, n: Math.round(m) }) : m < 2880 ? Q("(last block {y}, {n} hours ago)", { y, n: Math.round(m / 60) }) : Q("(last block {y}, {n} days ago)", { y, n: Math.round(m / 1440) });
  /* the chain weather: the newest blocks turned into a forecast, the numbers shown beside it */
  function weather(s) {
    const at = String(s.h), txs = s.bs.reduce((n, b) => n + (b.transactions || []).length, 0);
    const w = [V(s.sim ? "wxSim" : "wxChain")], band = set => { const k = pickLine(RICO.SETS[set]); markSaid(k); w.push(V(k)); };
    if (s.age > 10) { band(s.age >= 720 ? "fogDay" : s.age >= 180 ? "fogLong" : s.age >= 60 ? "fogHour" : "fog"); w.push(ago(at, s.age)); }
    else if (!txs) { band("calm"); w.push(Q("({n} empty blocks, up to block {y})", { n: s.bs.length, y: at })); }
    else {
      /* every sender known (relay /api/v1/sources/recent, for about the same blocks): who it is, not just "busy" */
      const r = SRC.recent, who = r && r.to != null && Math.abs(r.to - s.h) <= 3 && RICO.wxSource ? RICO.wxSource(r.n) : null;
      band(who ? who.set : txs <= s.bs.length / 2 ? "breeze" : "choppy"); w.push(Q("({n} transactions in the last {m} blocks, up to block {y})", { n: txs, m: s.bs.length, y: at }));
      if (who && who.page) w.push(who.page === "hud" ? Q("(sent from tauhud.com)") : /^(direct|elsewhere)$/.test(who.page) ? Q("(sent from the Tau HUD wallet)") : Q("(sent from tauhud.com/{x}/)", { x: who.page }));
    }
    const rules = s.bs.filter(b => (b.transactions || []).some(tx => txKind(tx) === "rule_deploy")).map(b => b.header.block_number);
    if (rules.length) w.push(V("rule"), Q("(block {y})", { y: String(rules[rules.length - 1]) }));
    band(s.wait ? "showers" : "clear"); if (s.wait) w.push(Q("({n} waiting)", { n: s.wait }));
    return w;
  }
  /* what comes next on air: first a hello, then news from the chain when there is some (every other line at most),
     the weather every fourth line, and in between the game and the island, never the same line twice in a row */
  const ROT = { n: 0, newsLast: false };
  /* a listener phones in: Rico picks up, the caller asks in their own voice (through the telephone), Rico answers */
  /* a call is a little conversation: the caller, Rico, the caller again, a goodbye, and Rico signs off (rico.js CALLS) */
  function phoneIn() {
    /* when: solo or fresh (the chain). The calls about the cruise ships ("shipTomorrow+queen", like talk.js) come with
       Rico's ship talk instead (shipLine), as often as a ship is near */
    const ok = c => !c.when || (c.when === "solo" ? RADAR.solo : c.when === "fresh" ? RADAR.fresh : false);
    const keys = RICO.CALLS.map((c, i) => ok(c) ? "call:" + i : null).filter(Boolean);
    if (SND.on && RICO.voiced && !keys.some(x => RICO.voiced(x) !== false)) return null;   // no call has its voices yet: something Rico can say aloud instead
    return dial(pickLine(keys));
  }
  /* the phone rings, the conversation, Rico's goodbye */
  function dial(k) {
    const c = RICO.CALLS[+k.slice(5)], ring = pickLine(RICO.SETS.ring), bye = pickLine(RICO.SETS.bye); markSaid(ring); if (!c.cut) markSaid(bye);
    return { k, parts: RICO.call(c, ring, bye), call: true };
  }
  /* chain news as a host tells it: big moments with a sting before and a word after, small ones now and then */
  function story(n) {
    const big = /^(now|to|restart|midnight|val|fee|rev|whale)/.test(n.set), k = pickLine(n.keys || RICO.SETS[n.set]), line = RICO.L[k];
    const main = n.v ? { t: F(line, n.v), v: RICO.fill(line, n.s || n.v) } : V(k);   // a wave: the numbers shown, the bands spoken
    const l = { k, parts: [main, ...(n.more || []), ...(n.h != null && !line.includes("{where}") ? [Q("(block {y})", { y: String(n.h) })] : [])] };
    const bit = set => { const k = pickLine(RICO.SETS[set]); markSaid(k); return V(k); };
    if (big || Math.random() < 0.4) l.parts.unshift(bit("flash"));
    if (big || Math.random() < 0.3) l.parts.push(bit("tag"));
    return l;
  }
  function nextLine() {
    ROT.n++;
    /* the show opens with a shout, after the drum roll and the station horn */
    if (ROT.n === 1) { const k = RICO.wake(); return { k, parts: [V(k)], wake: true }; }
    if (ROT.n === 2) { const hr = new Date().getHours(); return one(Math.random() < 0.5 ? "open" : hr >= 5 && hr < 11 ? "morning" : hr < 17 && hr >= 11 ? "afternoon" : hr >= 17 && hr < 22 ? "evening" : "night"); }
    const big = RADAR.news.some(n => /^(now|to|restart|midnight)/.test(n.set));
    if (ROT.n % 4 === 3 && !big && RADAR.snap && performance.now() - RADAR.snap.at < 180000) { ROT.newsLast = false; return { k: null, parts: weather(RADAR.snap) }; }
    RADAR.news = RADAR.news.filter(n => performance.now() - n.at < 600000);
    /* the big moments always go on air; small news only while Rico has not just used up all its lines */
    const recent = SAID.slice(-20), i = RADAR.news.findIndex(n => /^(now|to|restart|midnight)/.test(n.set) || (n.keys || RICO.SETS[n.set]).some(k => !recent.includes(k)));
    if (i >= 0 && (!ROT.newsLast || big)) { ROT.newsLast = true; return story(RADAR.news.splice(i, 1)[0]); }
    ROT.newsLast = false;
    /* a new song on the radio: Rico says what it is */
    if (DJ.songNew && RICO.L["sn_" + DJ.songNew] && !(SND.on && RICO.voiced && RICO.voiced("sn_" + DJ.songNew) === false)) { const k = "sn_" + DJ.songNew; DJ.songNew = null; return { k, parts: [V(k)] }; }
    /* a cruise ship near: Rico talks about it, the more the nearer it is, and reports from the island while she is in */
    const sh = shipLine(); if (sh) return sh;
    /* in between: the game, a joke now and then, the phone-in, Tau corner, a word between songs, the jungle legend, the island's habits */
    /* the chain has stood still for an hour or more: Rico talks about it now and then, not only in the weather */
    const st = RADAR.snap;
    if (st && !st.sim && st.age >= 60 && performance.now() - st.at < 180000 && Math.random() < 0.3) return one("stall", ago(String(st.h), st.age));
    const r = Math.random();
    if (r < 0.26) { const L = djLines(), c = unsaid(L.map(l => l.k)), k = c[Math.floor(Math.random() * c.length)]; const l = L.find(x => x.k === k); if (l) return l; }
    /* the phone-in is the busiest part of the show: about one line in three, never two calls in a row */
    const set = r < 0.35 ? "joke" : r < 0.42 ? "salado" : r < 0.72 ? (ROT.callLast ? "net" : "call") : r < 0.76 ? "corner" : r < 0.81 ? (Math.random() < 0.25 ? "dunno" : "lagoon") : r < 0.85 ? "segue" : r < 0.89 ? "legend" : r < 0.93 ? "mainland" : r < 0.96 ? "net" : "general";
    ROT.callLast = false;
    /* a thank-you to the builders now and then reads the title of their latest change, shown between two spoken halves */
    if (set === "lagoon" && SRC.title && Math.random() < 0.3 && !SAID.slice(-40).includes("bld4a")) return { k: "bld4a", parts: [V("bld4a"), Q("“{x}”", { x: SRC.title }), V("bld4b")] };
    if (set === "call" && Math.random() < 0.88) { const p = phoneIn(); if (p) { ROT.callLast = true; return p; } return one("joke"); }   // otherwise a letter from a listener, read out by Rico
    return one(set);
  }
  /* a tab in the background stays quiet, unless the sound is on: then Radio Coco goes on, like a radio left on in the
     next room, and Rico keeps reading the chain so what he says is still news (a tab playing sound is not slowed down) */
  const away = () => document.hidden && !SND.on;
  readChain(); setInterval(() => { if (!away()) readChain(); }, 90000);
  dejaFetch(); setInterval(() => { if (!away()) dejaFetch(); }, 600000);
  srcFetch(); setInterval(() => { if (!away()) srcFetch(); }, 600000);
  /* who sent the last blocks' transactions (totals only), for the chain weather */
  const recentFetch = () => { if (window.TauSim && TauSim.on) return; fetch("https://node.tauhud.com/api/v1/sources/recent", { cache: "no-store" }).then(r => (r.ok ? r.json() : null)).then(j => { if (j && j.n) SRC.recent = j; }, () => {}); };
  recentFetch(); setInterval(() => { if (!away()) recentFetch(); }, 60000);
  if (QS.get("rico") === "sources") window.__sources = { sources, share, call, SRC, RADAR, story, nextLine, markSaid, shipStage, shipOdds, shipLine, shipPick, SHIPLIVE, SHIPV, ROT };   // the headless check (tests)
  setInterval(() => {
    if (!G || G.over || G.counting || away() || performance.now() < DJ.next || SND.gap) return;
    /* the Night Line's hour belongs to the callers between the songs (the show's opener still comes first) */
    if (ROT.n > 0 && RICO.night && RICO.night()) return;
    /* the show waits for the sound to come on (the first tap), so the opener is heard, not just read; after a while it goes on in text */
    if (ROT.n === 0 && !SND.on && performance.now() < 90000) return;
    if (DJ.opened && DJ.after) { const a = DJ.after; DJ.after = null; onAir(a, 1); return; }
    const l = nextLine(); if (!l) return;
    if (l.k) markSaid(l.k);
    DJ.opened = true;
    if (l.wake && SND.on) { SND.sfx("wake"); DJ.next = performance.now() + 60000; setTimeout(() => onAir(l.parts, true), 2000); return; }
    onAir(l.parts, false, l.call);
  }, 2000);
  /* between two songs the band stops and Rico says a word that fits (rico.js brk): the song that ended and the one
     coming, or the hour; in the Night Line's hour a listener with a problem. He names the next song, so it is not
     announced again once it plays. */
  if (RICO.brk) SND.onbreak = ({ from, to }) => {
    if (!G || G.over || G.counting) return 0;
    const b = RICO.brk(from, to, { pick: pickLine }); if (!b) return 0;
    markSaid(b.k); (b.also || []).forEach(markSaid);
    DJ.song = to; DJ.songNew = null; DJ.opened = true;
    return onAir(b.parts, true, b.call).then(secs => { if (secs) DJ.next = Math.max(DJ.next, performance.now() + secs * 1000 + 25000); return secs; });
  };
  /* the radio plays its songs one after the other (music.js PLAYLIST): when a new one starts, Rico announces it next */
  setInterval(() => { const so = SND.song; if (!so || !so.id || UI.card) return; if (DJ.song && so.id !== DJ.song) DJ.songNew = so.id; DJ.song = so.id; }, 3000);

  /* ---------- election night ---------- */
  function tally() {
    const R = seeded(G.seed + 99), ballots = PEOPLE.map(p => {
      const sc = Object.keys(CANDS).map(c => [c, G.sup[c][p.id] + R() * 4]); sc.sort((a, b) => b[1] - a[1]); return [p, sc[0][0]];
    });
    /* the eleventh ballot belongs to the visitors: it goes to whoever leads the island ballot on the real testnet */
    const vp = visitorsPick(); if (vp) ballots.push([{ name: T("The visitors, by their votes on the testnet") }, vp]);
    const count = {}; Object.keys(CANDS).forEach(c => (count[c] = 0)); ballots.forEach(([, c]) => count[c]++);
    const max = Math.max(...Object.values(count)), top = Object.keys(count).filter(c => count[c] === max);
    const win = top.length > 1 ? top[Math.floor(R() * top.length)] : top[0];
    Object.keys(CANDS).forEach(c => (count[c] = 0));   // the night counts them again, one by one
    return { R, ballots, vp, count, win, tie: top.length > 1 };
  }
  function election() {
    G.counting = true; G.move = MOVES; hud(); SC.setHour(2.6); SC.gather(1);
    SND.set({ tense: true });
    const t0 = tally(), { R, ballots, vp, count } = t0;
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
        if (top.length > 1) { win = top.includes(t0.win) ? t0.win : top[Math.floor(R() * top.length)]; tape.textContent = F("A tie. The black cat walks past the ballot box of {x}, twice. Sam says that settles it.", { x: nm(win) }); SC.cat(true); SND.sfx("glitch"); setTimeout(() => SND.sfx("meow"), 900); }
        G.over = { win, count, lies: G.lies.filter(l => l.by === G.me && l.lie).length };
        let goal = "-"; try { if (G.amb && AMB[G.amb.id].check()) goal = G.amb.id; } catch (e) {}
        isleTell("end", gidOf(), G.me, win, G.laws.map(l => l.id).join(",") || "-", myPk() || "-", String(count[G.me] || 0), goal);
        write("sam", F("counted the ballots: {x} is governor of the island", { x: nm(win) }), "law");
        save(); SND.set({ tense: false }); SND.sfx("cheer");
        setTimeout(ending, top.length > 1 ? 4200 : 1600);
      };
      setTimeout(next, 900);
    });
  }
  /* ---------- after the count: a special edition of the Key Crier about the campaign, then the result ---------- */
  const AFTER = {
    night: "The Friday night market now sells more fried plantain than the mainland eats in a year.",
    quiet: "After ten the island is so quiet that the gulls have started to whisper.",
    reef: "The parrotfish came back, and brought their cousins.",
    harbour: "The cruise ships came. The fish moved two bays further on and send postcards.",
    boat: "The school boat has never once been late. The children have tried.",
    lunch: "Fresh fish for lunch every day. The cat outside the school window has enrolled.",
    concerts: "The Sunday concerts got so good that Radio Coco plays them again on Mondays.",
    road: "The road round the island is finished. The coconuts have seen the other side and want to stay.",
    copy: "The copy of the Book on the square is the most read thing on the island, after the menu at Lola’s.",
    tax: "The coconut tax mended every roof. Nobody likes it. Every roof is dry.",
  };
  const OATH = {
    marisol: "Marisol was sworn in under the council tree, between two orders of coffee.",
    tobias: "Tobias was sworn in under the council tree and gave the speech himself. All of it. The ships waited.",
    baako: "Baako was sworn in under the council tree and counted the guests. All of them, twice.",
    hana: "Hana was sworn in under the council tree and corrected the oath while she took it.",
  };
  /* a template whose fillings are already translated: the template is looked up first, then filled (F would hand the dictionary a mostly translated line, which it leaves alone) */
  /* translate the template, then fill it: names stay as they are (F translates a filled line, which fails on a name).
     Numbers go in before translating, because the dictionary's templates expect a number where {n} stands */
  const Fd = (s, v) => { const num = {}, txt = {}; for (const k in v) (typeof v[k] === "number" ? num : txt)[k] = v[k]; return T(s.replace(/\{(\w+)\}/g, (m, k) => (k in num ? num[k] : m))).replace(/\{(\w+)\}/g, (m, k) => (k in txt ? txt[k] : m)); };
  function campaignFacts() {
    const o = G.over, me = G.me, mine = G.book.filter(b => b.who === me), out = [];
    const myLaws = G.laws.filter(l => l.by === me).map(l => "“" + T(LAWS[l.id].t) + "”");
    out.push(myLaws.length ? Fd("Your laws in force: {x}", { x: myLaws.join(T(", ")) }) : T("None of your laws made it into force."));
    const total = Object.values(o.count || {}).reduce((a, b) => a + b, 0);
    if (total) out.push(F("Ballots for you: {n} of {m}", { n: (o.count || {})[me] || 0, m: total }));
    const pacts = G.pacts.filter(p => p.a === me || p.b === me), broken = pacts.filter(p => p.broken).length;
    if (pacts.length) out.push(F("Pacts: {n} kept, {m} broken", { n: pacts.length - broken, m: broken }));
    const lies = G.lies.filter(l => l.by === me && l.lie), truths = G.lies.filter(l => l.by === me && !l.lie).length;
    if (lies.length) out.push(F("Rumours you paid for: {n}, shown up by the Book: {m}", { n: lies.length, m: lies.filter(l => l.out).length }));
    if (truths) out.push(F("Truths you paid Radio Coco to tell: {n}", { n: truths }));
    G.deals.filter(d => d.by === me).forEach(d => out.push(F(d.kept ? "Took {n} coins from the {x} and kept the promise" : "Took {n} coins from the {x} and never kept the promise", { n: EMB[d.emb].coins, x: EMB[d.emb].name })));
    const signed = mine.filter(b => b.tx).length;
    if (signed) out.push(F("{n} of your moves signed into Tau Testnet Alpha", { n: signed }));
    if (G.amb) { const A = AMB[G.amb.id], ok = A.check(); out.push(Fd(ok ? "Your ambition, {x}: reached" : "Your ambition, {x}: missed", { x: T(A.name) })); }
    events().filter(e => e.done).forEach(e => out.push(Fd("The week of the {x}: you {y}", { x: T(EVENT_NAMES[e.id]), y: mine.some(b => b.text === T(EVENTS[e.id].act.line)) ? T("helped") : T("looked the other way") })));
    return out;
  }
  function islandSays() {
    const o = G.over, me = G.me, won = o.win === me, out = [];
    const broke = G.pacts.some(p => p.broken && (p.a === me || p.b === me)), unkept = G.deals.some(d => d.by === me && !d.kept);
    const mark = !o.lies && !broke && !unkept ? "Full marks. I checked." : o.lies + (broke ? 1 : 0) + (unkept ? 1 : 0) > 1 ? "See me after class." : "B minus. See the footnotes.";
    if (me !== "hana") out.push(["hana", T(mark)]);
    if (me !== "marisol") out.push(["marisol", T(won ? "I heard it first. Obviously." : "I heard it first. I always do.")]);
    out.push(["sam", T("It is all in the Book. It always was.")]);
    return out;
  }
  function edition() {
    const o = G.over, me = G.me, won = o.win === me;
    SC.gather(0); SC.focus(null);
    const head = won && !o.lies ? F("{x} sworn in under the council tree", { x: nm(me) }) : won ? F("{x} sworn in, and the Book has questions", { x: nm(me) }) : F("{x} governs; {y} goes back to the hammock", { x: nm(o.win), y: nm(me) });
    const facts = campaignFacts(), later = G.laws.filter(l => AFTER[l.id]).slice(-2).map(l => T(AFTER[l.id]));
    if (!later.length) later.push(T("No new law passed. The island did what it always does, only with more meetings."));
    later.push(T("And the ferry to the mainland? Still coming soon."));
    const face = portrait(o.win, 64, 1), amb = ambOutcome(); bank();
    const box = el("div", { class: "cv-paper cv-edition" },
      el("p", { class: "mast", text: T("The Key Crier") }), el("p", { class: "date", text: T("Special edition · the day after the election") }),
      el("div", { class: "lead" }, face, el("div", null, el("h3", { class: "head", text: head }), el("p", { text: T(OATH[o.win]) + " " + T("Ama tied the shell necklace. Rico played the anthem twice, once on purpose.") }))),
      el("div", { class: "cols" },
        el("div", null, el("h4", { text: T("Your campaign, as the Book has it") }), el("ul", null, facts.slice(0, 5).map(x => el("li", { text: x }))),
          amb ? el("div", { class: "says amb " + amb.how }, el("h4", { text: T(amb.A.name) + ": " + T(amb.how === "won" ? "reached" : amb.how === "betrayed" ? "betrayed" : "missed") }), el("p", null, el("b", { translate: "no", text: nm(amb.A.who) + ": " }), "“" + amb.line + "”")) : null),
        el("div", null, el("h4", { text: T("Five years later") }), el("ul", { class: "later" }, later.map(x => el("li", { text: x }))),
          el("div", { class: "says" }, islandSays().map(([who, q]) => el("p", null, el("b", { translate: "no", text: nm(who) + ": " }), "“" + q + "”"))))));
    openCard(null, b => {
      b.classList.add("paper", "edition"); b.append(box); setTimeout(() => { b.scrollTop = 0; }, 80);
      b.append(el("div", { class: "cv-acts" },
        btn(T("Share this front page"), () => shareEdition(head, facts, face)),
        btn(T("Continue"), () => { G.over.read = true; save(); closeCard(true); ending(); }, { go: true })));
    });
  }
  /* the front page as a picture to share: drawn fresh, the governor's face taken from the page */
  function editionCard(head, facts, face) {
    const c = document.createElement("canvas"); c.width = 1200; c.height = 630; const g = c.getContext("2d");
    g.fillStyle = "#f3ead6"; g.fillRect(0, 0, 1200, 630);
    g.fillStyle = "#1c1a16"; g.textAlign = "center"; g.font = "700 64px Georgia, serif"; g.fillText(T("The Key Crier"), 600, 86);
    g.fillRect(60, 108, 1080, 3); g.fillRect(60, 116, 1080, 1.5);
    g.font = "20px ui-monospace, monospace"; g.fillStyle = "#5a5246"; g.fillText(T("Special edition · the day after the election"), 600, 148);
    try { g.drawImage(face, 70, 180, 200, 200); } catch (e) {}
    const wrap = (text, x, y, w, lh, max) => { const words = text.split(/(\s+)/), lines = []; let cur = ""; for (const wd of words) { const t = cur + wd; if (g.measureText(t).width > w && cur.trim()) { lines.push(cur.trim()); cur = wd.trimStart(); } else cur = t; } if (cur.trim()) lines.push(cur.trim()); lines.slice(0, max).forEach((l, i) => g.fillText(l, x, y + i * lh)); return y + Math.min(max, lines.length) * lh; };
    g.textAlign = "left"; g.fillStyle = "#1c1a16"; g.font = "700 44px Georgia, serif";
    let y = wrap(head, 300, 222, 840, 52, 3) + 14;
    g.font = "26px Georgia, serif"; g.fillStyle = "#2a261f";
    for (const f of facts.slice(0, 4)) { y = wrap("· " + f, 300, y, 840, 34, 2) + 4; if (y > 560) break; }
    g.font = "22px ui-monospace, monospace"; g.fillStyle = "#5a5246"; g.textAlign = "center"; g.fillText("White Rabbit Key · tauhud.com/rabbit", 600, 600);
    return c;
  }
  async function shareEdition(head, facts, face) {
    const c = editionCard(head, facts, face), url = "https://tauhud.com/rabbit/";
    const blob = await new Promise(r => c.toBlob(r, "image/png")); if (!blob) return;
    const file = typeof File === "function" ? new File([blob], "white-rabbit-key.png", { type: "image/png" }) : null;
    try { if (file && navigator.canShare && navigator.canShare({ files: [file] })) { await navigator.share({ files: [file], text: head + " · White Rabbit Key " + url }); return; } }
    catch (e) { if (e && e.name === "AbortError") return; }
    const a = el("a", { href: URL.createObjectURL(blob), download: "white-rabbit-key.png" }); document.body.append(a); a.click(); a.remove();
    toast(T("The front page is saved as a picture."));
  }
  function ending() {
    if (!G.over.read) return edition();
    const o = G.over, me = G.me, won = o.win === me;
    if (o.late && !o.lateSaid) { o.lateSaid = true; save(); setTimeout(() => toast(T("The week ended before your campaign did: the islanders voted on Sunday without you. This one is not counted for the island.")), 1200); }
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
      acts.append(ballotEl(), isleVerdict());
      bank(); acts.append(el("p", { class: "cv-note", text: Fd("Your savings: {n} coins. They carry over to your next campaign and buy things the island keeps: a roof for the school, a lamp for the lighthouse, a stone in Tano’s circle.", { n: savings().coins }) }));
      const again = FREE || !G.week || G.week !== weekId();
      acts.append(btn(again ? T("Play again") : T("Next campaign on Monday"), () => { store.del(KEY); G = null; closeCard(); start(); }, { go: true, off: !again, sub: again ? null : Fd("the week is played; a new one begins {x}", { x: countIn() }) }), btn(T("Read the Book"), () => openCard("book", PLACE.book)), btn(T("The players’ board"), () => openBoard()), btn(T("The special edition"), () => { G.over.read = false; closeCard(true); ending(); }));
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
  const CHAIN = { ws: null, wait: new Map(), q: [], payq: [], busy: false, next: 0, fee: null, made: false, follow: 0 };
  function relay() {
    return new Promise(res => {
      if (CHAIN.ws && CHAIN.ws.readyState === 1) return res(CHAIN.ws);
      let ws; try { ws = new WebSocket("wss://node.tauhud.com"); } catch (e) { return res(null); }
      ws.onopen = () => { ws.send("hello version=1"); if (ISLE.want) ws.send("isle join"); CHAIN.ws = ws; setTimeout(() => res(ws), 150); };
      ws.onmessage = ev => {
        let m; try { m = JSON.parse(String(ev.data)); } catch (e) { return; }
        if (m.command === "isle") { if (m.status === "ok" && m.data && m.data.day) onIsle(m.data); else if (m.status === "ok" && m.data && m.data.board && typeof m.data.board === "object") onBoard(m.data.board); return; }   // the shared island: pushes and acks, never an answer someone waits for
        const q = CHAIN.wait.get(m.command); if (q && q.length) q.shift()(m);
      };
      ws.onerror = ws.onclose = () => { if (CHAIN.ws === ws) CHAIN.ws = null; res(null); isleRetry(); };
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
    if (b.who !== G.me) { ask("islandmove " + b.who + " " + b.kind + " " + (TILL[b.at] ? b.at : "hall"), 8000).then(m => { if (m && m.status === "ok" && m.data && m.data.queued) { b.bot = true; save(); } }); return; }
    if (G.onchain) mySend(tillOf(b.at), nm(b.who) + " " + b.text, h => { if (h) { b.tx = h; save(); } }, b.pay, b.at);
  }
  /* money that comes to the visitor (a shift's wage, an embassy's money) is real too: the island's purses on the relay
     pay it into their test wallet (infra/relay/island.py PURSES), when they sign their moves on the testnet */
  /* the wage or the embassy's money: asked for once the move's own transaction is through (the relay pays only after a move) */
  function payMe(purse, from) {
    if (!G || !G.onchain) return;
    CHAIN.payq.push({ purse, from });
    if (!CHAIN.busy && !CHAIN.q.length) flushPay();
  }
  function flushPay() {
    const k = myKey(); if (!k) { CHAIN.payq.length = 0; return; }
    CHAIN.payq.splice(0).forEach(({ purse, from }) => ask("islandpay " + purse + " " + k.pk, 8000).then(m => {
      if (!(m && m.status === "ok" && m.data && m.data.queued)) return;
      if (m.data.from) remember(m.data.from, "Key purse · " + from);
      toast(F("{x} is sending you {n} test AGRS on the testnet.", { x: from, n: m.data.amount }));
    }, () => {}));
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
  function mySend(to, label, done, pay, at) { CHAIN.q.push({ to, label, done, pay: pay || 1, at }); pump(); }
  async function pump() {
    if (CHAIN.busy || !CHAIN.q.length) return;
    CHAIN.busy = true;
    const { to, label, done, pay, at } = CHAIN.q.shift();
    let hash = null;
    try {
      const k = myKey(); if (!k) throw 0;
      if (CHAIN.fee == null) { const g = await ask("getgovernance"); const m = /o9\[t\]:bv\[24\]\s*=\s*\{\s*#x([0-9a-fA-F]+)/.exec((g && g.data && g.data.consensus_rules) || ""); CHAIN.fee = m ? parseInt(m[1], 16) : 10; }
      const st = await ask("getsequence " + k.pk); if (!st || st.status !== "ok") throw 0;
      const seq = Math.max(st.data.sequence_number || 0, CHAIN.next), tip = st.data.tip_height || 0;
      const tx = { tx_type: "user_tx", sender_pubkey: k.pk, sequence_number: seq, expiration_time: Math.floor(Date.now() / 1000) + 600, expire_at_height: tip + 1000, fee_limit: String(CHAIN.fee * 5), operations: { "1": [[k.pk, to, String(pay)]] } };
      const d = { sender_pubkey: tx.sender_pubkey, sequence_number: tx.sequence_number, expiration_time: tx.expiration_time, fee_limit: tx.fee_limit, tx_type: tx.tx_type, expire_at_height: tx.expire_at_height, operations: tx.operations };
      tx.signature = window.TauBLS.bytesToHex(window.TauBLS.sign(new TextEncoder().encode(canon(d)), k.sk));
      await ask("via rabbit");
      const r = await ask("sendtx " + JSON.stringify(tx));
      if (r && r.status === "ok" && !(r.data && r.data.ok === false)) {
        hash = (r.data && r.data.tx_hash) || String(Date.now()); CHAIN.next = seq + 1;
        try { const lk = "tauhud-wallet-log-live-" + k.pk, logs = JSON.parse(store.get(lk) || "[]"); logs.unshift({ hash, kind: "pay", label: T("White Rabbit Key") + ": " + label, at: Date.now(), status: "queued", seq, paid: true }); store.set(lk, JSON.stringify(logs.slice(0, 40))); } catch (e) {}
        if (TILL[at]) remember(to, "Key jar · " + ((SC.places[at] || {}).name || at));   // a readable name in the wallet's address book
        if (!txNote(hash, label, pay)) toast(F("Signed into the testnet: {n} test AGRS from your wallet.", { n: pay }));
        if (CHAIN.payq.length) flushPay();
      } else { CHAIN.payq.length = 0; CHAIN.next = 0; toast(T("The testnet did not take this move just now; the game goes on.")); }
    } catch (e) { if (G && G.onchain) toast(T("The testnet is out of reach just now; the game goes on.")); }
    CHAIN.busy = false; done && done(hash);
    if (CHAIN.q.length) setTimeout(pump, 400);
  }
  /* ---------- the chain moment: every move signed into the testnet is shown as what it is ----------
     A strip under the island says "signed, waiting for a block", then "sealed in block N", with the hash and a link to
     the Explorer; a chip in the bar counts the campaign's transactions, and opens the list of them with the chain's
     answer to each. The game keeps the list (G.txs) and asks the relay for the status of what is still waiting. */
  const txShort = h => h.slice(0, 6) + "…" + h.slice(-4);
  const txUrl = h => "/explorer/?tx=" + h + (window.TauI18n && TauI18n.lang !== "en" ? "&lang=" + TauI18n.lang : "");
  function txNote(h, label, pay) {
    if (!G || !/^[0-9a-f]{64}$/i.test(h || "")) return false;
    G.txs = Array.isArray(G.txs) ? G.txs : [];
    G.txs.unshift({ h, label, pay: pay || 1, at: Date.now(), st: "queued" }); if (G.txs.length > 60) G.txs.length = 60;
    save(); chainChip(); chainStrip(G.txs[0]); followTxs();
    return true;
  }
  function chainChip() {
    const b = $("cvChainChip"); if (!b) return;
    const txs = (G && G.txs) || []; b.hidden = !txs.length; if (!txs.length) return;
    const sealed = txs.filter(t => t.st === "in").length, waiting = txs.filter(t => t.st === "queued").length;
    b.replaceChildren(el("i", { class: "dot" + (waiting ? " now" : ""), "aria-hidden": "true" }), el("b", { class: "num", text: String(sealed + waiting) }), el("span", { class: "lb", text: T("on chain") }));
    b.title = F("{n} moves on Tau Testnet Alpha this campaign: {m} sealed in a block, {k} waiting. Click: every transaction with the chain’s answer.", { n: txs.length, m: sealed, k: waiting });
    b.setAttribute("aria-label", F("{n} on chain", { n: sealed + waiting }));
  }
  let stripT = 0;
  function chainStrip(t) {
    const d = $("cvChain"); if (!d || !t) return;
    const text = t.st === "in" ? F("Sealed in block {n} on Tau Testnet Alpha", { n: t.block }) : t.st === "out" ? F("Refused by the chain: {x}", { x: t.why || "" }) : F("Signed into Tau Testnet Alpha: {n} test AGRS · waiting for a block", { n: t.pay });
    d.replaceChildren(el("i", { class: "dot" + (t.st === "in" ? " ok" : t.st === "out" ? " no" : " now"), "aria-hidden": "true" }), el("span", { class: "tx", text: text }), el("code", { class: "h", text: txShort(t.h) }),
      el("a", { href: txUrl(t.h), target: "_blank", rel: "noopener", text: T("Explorer") }));
    d.hidden = false; requestAnimationFrame(() => d.classList.add("on"));
    clearTimeout(stripT); stripT = setTimeout(() => { d.classList.remove("on"); setTimeout(() => { if (!d.classList.contains("on")) d.hidden = true; }, 350); }, t.st === "queued" ? 14000 : 9000);
  }
  function followTxs() {
    if (CHAIN.follow) return;
    const tick = async () => {
      CHAIN.follow = 0;
      if (!G || document.hidden) { CHAIN.follow = setTimeout(tick, 15000); return; }
      const open = (G.txs || []).filter(t => t.st === "queued" && Date.now() - t.at < 900000).slice(0, 4);
      if (!open.length) return;
      let changed = false;
      for (const t of open) {
        const m = await ask("gettxstatus " + t.h, 8000); if (!m || m.status !== "ok") continue;
        const d = m.data || {}, st = String(d.status || d.state || "").toLowerCase();
        if (d.block_number != null || /confirmed|included|mined|sealed|applied/.test(st)) { t.st = "in"; t.block = d.block_number ?? d.height ?? null; changed = true; if (G.txs[0] === t) chainStrip(t); }
        else if (/reject|fail|dropped|expired|invalid/.test(st)) { t.st = "out"; t.why = d.reason || d.error || st; changed = true; if (G.txs[0] === t) chainStrip(t); }
      }
      if (changed) { save(); chainChip(); if (UI.card && UI.card.classList.contains("chain")) chainCard(); }
      CHAIN.follow = setTimeout(tick, 6000);
    };
    CHAIN.follow = setTimeout(tick, 5000);
  }
  function chainCard() {
    const pk = myPk(), lang = window.TauI18n && TauI18n.lang !== "en" ? "&lang=" + TauI18n.lang : "", open = u => window.open(u, "_blank", "noopener");
    openCard("book", box => {
      box.classList.add("chain");
      const rows = ((G && G.txs) || []).map(t => el("li", { class: t.st === "out" ? "k-broke" : "k-fact" },
        el("small", { text: t.st === "in" ? F("in block {n}", { n: t.block }) : t.st === "out" ? F("refused: {x}", { x: t.why || "" }) : T("waiting for a block") }),
        el("span", null, el("span", { text: t.label }), " ", el("a", { class: "cv-tx", href: txUrl(t.h), target: "_blank", rel: "noopener", text: txShort(t.h) }))));
      scene(box, "sam", T("Your moves on Tau Testnet Alpha"), T("Every move you make goes to the testnet as a transaction from your test wallet: 1 test AGRS to the place’s jar, signed in this browser. Here is each one, with the chain’s answer."),
        [btn(T("Your test wallet"), () => open("/wallet/" + (lang ? "?" + lang.slice(1) : ""))), pk ? btn(T("Your Tau card"), () => open("/card/?a=" + pk + lang)) : null, btn(T("Back to the island"), () => closeCard(), { go: true })].filter(Boolean),
        el("ol", { class: "cv-book" }, rows.length ? rows : [el("li", { class: "dim", text: T("Nothing yet.") })]));
    });
  }
  let drawer = null;
  function remember(addr, name) {
    try { const b = JSON.parse(store.get(BOOK_LIVE) || "[]"); if (Array.isArray(b) && !b.some(c => c && c.addr === addr)) { b.push({ name, addr }); store.set(BOOK_LIVE, JSON.stringify(b)); } } catch (e) {}
  }
  function openWallet(to, what) {
    remember(ADDR[to], BOOKNAME[to]);
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
      if (m.status === "ok" && c) { BAL.n[c] = votesIn(d.balance); todo.splice(todo.indexOf(c), 1); }
      if (!todo.length) { BAL.state = "ok"; clearTimeout(stop); try { ws.close(); } catch (e) {} ballotLine(); return; }
      setTimeout(ask, m.status === "ok" ? 300 : 1500);
    };
    ws.onerror = () => { BAL.state = "off"; ballotLine(); };
  }
  /* the testnet runs with its auto-faucet on: an account it has never seen answers getbalance with the faucet's 100,000
     test AGRS, though nothing was ever sent to it. A ballot box has no key and never sends, and the first vote into it
     counts from 0, so a box that reads exactly the faucet amount has had no vote yet (a box with real votes would need
     100,000 of them to read that). */
  const FAUCET = 100000;
  const votesIn = bal => { const n = Math.floor(Number(bal) || 0); return n === FAUCET ? 0 : n; };
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

  /* ---------- the shared island: every campaign played today, added up by the relay (infra/relay/isle.py) ----------
     Everyone plays their own island week against the three rivals, and nobody ever waits for anybody. The visitor's own
     moves are told to the relay as a few words (which kind of move, which law or topic, where; no names, no text), and
     every page gets the same small summary back, pushed when it changes: how many campaigns today, which laws passed
     most, who won most, the latest moves. One player or thousands, the message is the same size. When few people play,
     the islanders make moves of their own on the relay; they are counted apart and always shown as the islanders'.
     If the relay is out of reach, all of this simply stays hidden and the game is the same as alone. */
  const ISLE = { s: null, want: false, at: 0 };
  const ISLE_KINDS = ["law", "down", "refused", "talk", "lie", "fact", "deal", "pact", "broke", "gift"];
  const gidOf = () => { if (!G.gid) { G.gid = (Math.random().toString(36).slice(2) + Date.now().toString(36)).slice(0, 12); save(); } return G.gid; };
  function isleTell(...words) { relay().then(ws => { if (ws) try { ws.send("isle " + words.join(" ")); } catch (e) {} }); }
  function isleMove(kind, x, at) {
    if (!G || !ISLE_KINDS.includes(kind)) return;
    isleTell("move", gidOf(), G.me, kind, x && /^[a-z]{2,12}$/.test(x) ? x : "-", TILL[at] || at === "hall" ? at : "hall", myPk() || "-");
  }
  /* the visitor's test wallet address, if this browser has one (never made here: the first signed move makes it) */
  const myPk = () => { try { const k = JSON.parse(store.get(WKEY) || "null"); return k && /^[0-9a-f]{96}$/.test(k.pk || "") ? k.pk : null; } catch (e) { return null; } };
  function isleJoin() { ISLE.want = true; relay().then(ws => { if (ws) try { ws.send("isle join"); ISLE.wait = 0; } catch (e) {} }); }
  /* "playing now" counts the games that are open: a dropped socket joins again by itself (15 s, then slower), and a tab
     left in the background for five minutes leaves the island until someone looks at it again */
  function isleRetry() {
    if (!ISLE.want || ISLE.retry) return;
    ISLE.wait = Math.min(120000, (ISLE.wait || 7500) * 2);
    ISLE.retry = setTimeout(() => { ISLE.retry = null; if (ISLE.want) isleJoin(); }, ISLE.wait);
  }
  document.addEventListener("visibilitychange", () => {
    clearTimeout(ISLE.idle);
    if (document.hidden) ISLE.idle = setTimeout(() => { if (!ISLE.want) return; ISLE.want = false; ISLE.away = true; if (CHAIN.ws && CHAIN.ws.readyState === 1) try { CHAIN.ws.send("isle leave"); } catch (e) {} }, 300000);
    else if (ISLE.away) { ISLE.away = false; isleJoin(); }
  });
  function onIsle(s) {
    ISLE.s = s; ISLE.at = Date.now();
    isleRule(); isleChip();
    document.querySelectorAll(".cv-isle-intro").forEach(p => p.replaceWith(isleIntro()));
    document.querySelectorAll(".cv-isle-gov").forEach(p => p.replaceChildren(...isleGov()));
    const bd = UI.card && UI.card._board && UI.card.querySelector(".cv-board"); if (bd && s.board) { bd.replaceWith(boardBody(s.board)); fitCard(UI.card); }
  }
  const isleTop = (o, n = 1) => Object.keys(o || {}).sort((a, b) => o[b] - o[a]).slice(0, n);
  /* the laws passed today on the whole island: the players' campaigns and the islanders' own, together */
  function isleLaws() {
    const s = ISLE.s, all = {}; if (!s) return all;
    [s.players.laws, s.islanders.laws].forEach(o => { for (const k in o || {}) if (LAWS[k]) all[k] = (all[k] || 0) + o[k]; });
    return all;
  }
  /* the week: Monday to Sunday on the island's clock, the candidate who won the most campaigns governs the week after,
     and the laws most often in force at the end of those campaigns are the island's laws that week: every new campaign
     starts with them in force (holder: the island), until someone repeals them in the hall */
  const isleLast = () => (ISLE.s && ISLE.s.last && CANDS[ISLE.s.last.governor]) ? ISLE.s.last : null;
  const isleWeek = () => (ISLE.s && ISLE.s.week) || null;
  /* the governor's count is Monday 00:00 on the island's clock (Europe/Berlin), whatever the relay says; shown as a countdown */
  const countIn = () => spanText((7 - berlin().dow) * 86400 + untilMidnight());
  const countLine = () => Fd("Governor’s count {x}, Monday 00:00 German time", { x: countIn() || T("every week") });
  function isleRule() {
    const last = isleLast(); if (!G || G.ruled || G.day !== 1 || G.move || G.over || !last) return;
    G.ruled = last.id;
    const laws = (last.laws || []).filter(id => LAWS[id] && !inForce(id) && !conflict(id));
    laws.forEach(id => G.laws.push({ id, by: ISLE_BY, day: 0 }));
    news(Fd("Governor of the island this week: {x}, who won {n} of {m} campaigns last week.", { x: nm(last.governor), n: last.wins[last.governor] || 0, m: last.finished }), RICO.L.bkGovernor);
    if (laws.length) news(Fd("In force since last week, by the whole island: {x}. Repeal in the hall if you must.", { x: laws.map(id => "“" + T(LAWS[id].t) + "”").join(", ") }), RICO.L.bkCarry);
    save(); if (UI.card && UI.card._visit === "hall") openCard("hall", PLACE.hall);
  }
  const isleWho = e => e.h ? nm(e.c) : F("A player as {x}", { x: nm(e.c) });
  function isleText(e) {
    const law = LAWS[e.x] ? T(LAWS[e.x].t) : null;
    switch (e.k) {
      case "law": return law ? F("passed “{x}”", { x: law }) : T("changed a law");
      case "down": return law ? F("proposed “{x}”: voted down", { x: law }) : T("was turned down");
      case "refused": return law ? F("proposed “{x}”: refused, it contradicts a law in force", { x: law }) : T("proposed a law that was refused");
      case "talk": return TOPICS[e.x] ? F("spoke on the market square about {x}", { x: T(TOPICS[e.x]) }) : T("did an honest day’s work");
      case "lie": return CANDS[e.x] ? F("paid Radio Coco for a rumour about {x}", { x: nm(e.x) }) : T("paid Radio Coco for a rumour");
      case "fact": return CANDS[e.x] ? F("paid Radio Coco to tell the truth about {x}", { x: nm(e.x) }) : T("put a fact in the Book");
      case "deal": return EMB[e.x] ? F("took the {x}’s money", { x: T(EMB[e.x].name) }) : T("took an embassy’s money");
      case "pact": return CANDS[e.x] ? F("made a pact with {x}", { x: nm(e.x) }) : T("made a pact");
      case "broke": return T("broke a pact");
      default: return "";
    }
  }
  const isleLine = e => e.k === "won" ? F("{x} won a campaign played as {y}", { x: nm(e.c), y: nm(e.x) }) : isleWho(e) + " " + isleText(e);
  const isleAgo = t => { const m = Math.max(0, Math.round((Date.now() / 1000 - t) / 60)); return m < 1 ? T("just now") : m < 120 ? F("{n} min ago", { n: m }) : F("{n} h ago", { n: Math.round(m / 60) }); };
  /* the live counter: people with the game open right now, you included, counted by the relay (one browser once) */
  function isleChip() {
    const b = $("cvIsle"); if (!b) return;
    const s = ISLE.s; b.hidden = !s; if (!s) return;
    const n = s.players.campaigns, here = Math.max(1, s.here || 0);
    b.replaceChildren(el("i", { class: "dot now", "aria-hidden": "true" }), el("b", { class: "num", text: String(here) }), el("span", { class: "lb", text: T("playing now") }));
    b.title = F("{n} playing now, you included: people with White Rabbit Key open, counted live by the relay.", { n: here }) + "\n" + (n ? F("{n} campaigns today. Click: the island today.", { n }) : T("Click: the island today."));
    b.setAttribute("aria-label", F("{n} playing now", { n: here }));
  }
  /* on the start card: a chip that says the island is shared, and who else is on it right now (counted live by the
     relay; until it answers, the words alone), and a line under the four with this week's governor */
  function isleIntro() {
    const s = ISLE.s, c = el("span", { class: "ivc cv-isle-intro", title: T("Everyone this week plays the same island, each their own campaign against the island’s three rivals; every finished campaign counts for its candidate. The relay counts who has the page open right now.") });
    const n = s ? s.players.campaigns : 0, here = s ? Math.max(1, s.here || 0) : 1;
    c.append(el("i", { class: "dot" + (here > 1 ? " now" : ""), "aria-hidden": "true" }), el("span", { text: !s ? T("Shared island: everyone plays the same week")
      : (here > 1 ? F("{n} playing now", { n: here }) : T("Shared island")) + " · " + (n ? F("{n} campaigns today", { n }) : T("yours would be the first campaign today")) }));
    return c;
  }
  function isleGov() { const last = isleLast(); return last ? [el("b", { text: T("The island:") }), " ", Fd("{x} governs the island this week.", { x: nm(last.governor) })] : []; }
  /* each morning the paper says what the whole island talks about, and people who care about it lean a little toward
     whoever has that law in force in this game: the same nudge whether one campaign or a thousand were played */
  function isleMorning() {
    if (!ISLE.s || !G || (G.mood || 0) >= G.day) return;
    G.mood = G.day;
    const top = isleTop(isleLaws())[0]; if (!top) return;
    const holder = (G.laws.find(l => l.id === top) || {}).by, good = Object.keys(LAWS[top].fx).filter(k => LAWS[top].fx[k] > 0);
    if (holder && holder !== ISLE_BY && good.length) bump(holder, p => p.cares.some(c => good.includes(c)), 2);
    news(F("All over the island, people talk about “{x}” today.", { x: T(LAWS[top].t) }) + (holder ? " " + (holder === ISLE_BY ? T("Here it is the island’s own law this week.") : F("Here it is {y}’s law.", { y: nm(holder) })) : ""), RICO.L.bkTalk);
  }
  /* Rico's lines about the whole island: the numbers change all day, so they are shown exactly and spoken as a band
     or a name (rico.js isN, isLaw, isWin, isGov, isNews1/2), the rest in brackets beside */
  function isleLines() {
    const s = ISLE.s, L = []; if (!s || Date.now() - ISLE.at > 600000) return L;
    const p = s.players, laws = isleLaws(), top = isleTop(laws)[0];
    if (p.campaigns > 1) L.push({ k: "isle:n", parts: [{ t: F(RICO.L.isN, { n: p.campaigns }), v: RICO.fill(RICO.L.isN, { n: band(p.campaigns) }) }, Q("({n} of them finished)", { n: p.finished })] });
    if (top && laws[top] > 1) L.push({ k: "isle:law", parts: [V("isLaw"), Q("(“{x}”, {n} times)", { x: T(LAWS[top].t), n: laws[top] })] });
    const w = isleTop(p.wins)[0]; if (w && p.finished > 2) L.push({ k: "isle:win", parts: [V("isWin", { x: nm(w) }), Q("({n} of {m})", { n: p.wins[w], m: p.finished })] });
    const last = isleLast(); if (last) L.push({ k: "isle:gov", parts: [V("isGov", { x: nm(last.governor) }), Q("({n} of last week’s {m} campaigns won; next governor’s count {y}, Monday 00:00 German time)", { n: last.wins[last.governor] || 0, m: last.finished, y: countIn() || T("next week") })] });
    const e = (s.recent || []).find(x => x.k !== "won"); if (e) L.push({ k: "isle:" + e.t, parts: [V(e.h ? "isNews1" : "isNews2"), Q("{x}.", { x: isleLine(e) })] });
    return L;
  }
  /* after the election: how this campaign compares with the island's */
  function isleVerdict() {
    const s = ISLE.s, p = el("p", { class: "cv-note" }); if (!s || !s.players.finished) return p;
    const w = isleTop(s.players.wins)[0];
    p.textContent = F("Across the island today, {x} won {n} of {m} finished campaigns.", { x: nm(w), n: s.players.wins[w], m: s.players.finished });
    const wk = isleWeek(), lw = wk && isleTop(wk.wins)[0];
    if (lw) p.append(" ", Fd("This result is one ballot for {x} in the island’s week. So far {y} leads with {n} of {m}; whoever leads at the governor’s count ({z}, Monday 00:00 German time) governs the island next week.", { x: nm(w), y: nm(lw), n: wk.wins[lw], m: wk.finished, z: countIn() || T("every week") }));
    return p;
  }
  /* the card: the island's day, everyone's campaigns added up */
  function openIsle() {
    const s = ISLE.s, back = G && UI.card && UI.card._visit === "book";
    openCard(null, box => {
      box._isle = true; box.classList.add("isle-card");
      if (!s) { scene(box, "sam", T("The island today"), T("The island’s numbers are out of reach just now. Your campaign goes on as before."), [btn(T("Back to the island"), () => closeCard(), { go: true })]); return; }
      const p = s.players, isl = s.islanders, laws = isleLaws();
      scene(box, "sam", T("The island today"), p.campaigns
        ? F("{n} campaigns on this island today, {m} finished. Everyone plays their own island week; here they all add up.", { n: p.campaigns, m: p.finished })
        : T("No visitor has campaigned yet today. The islanders keep their own politics going until someone does."), [btn(T("The players’ board"), () => openBoard(), { sub: T("test wallets ranked, this week and all time") }), btn(T("Back to the island"), () => closeCard(), { go: true })]);
      const extra = el("div", { class: "cv-isle" });
      if (p.campaigns) {
        const row = el("div", { class: "cv-votes four" });
        Object.keys(CANDS).forEach(c => row.append(el("figure", null, portrait(c, 36), el("figcaption", { translate: "no", text: nm(c) }), el("small", { text: F("played {n} · won {m}", { n: p.as[c] || 0, m: p.wins[c] || 0 }) }))));
        extra.append(row);
      }
      const tl = isleTop(laws, 3), two = el("div", { class: "two" }), col = () => { const c = el("div"); two.append(c); return c; };
      extra.append(two);
      if (tl.length) col().append(el("h4", { text: T("Laws passed today") }), el("ul", { class: "cv-book" }, tl.map(k => el("li", { class: "k-law" }, el("span", { text: T(LAWS[k].t) }), el("small", { text: [p.laws[k] ? F("in {n} players’ campaigns", { n: p.laws[k] }) : "", isl.laws[k] ? F("{n} by the islanders", { n: isl.laws[k] }) : ""].filter(Boolean).join(" · ") })))));
      const wk = isleWeek(), last = isleLast(), wl = wk && isleTop(wk.wins)[0];
      if (wk) {
        const li = [];
        li.push(el("li", { class: last ? "k-law" : "dim" }, el("span", { text: last ? Fd("Governor: {x}, won {n} of {m} campaigns last week", { x: nm(last.governor), n: last.wins[last.governor] || 0, m: last.finished }) : T("No governor yet: the first week’s count is still running.") })));
        if (last && last.laws.length) li.push(el("li", { class: "k-law" }, el("span", { text: Fd("Laws of the week: {x}", { x: last.laws.map(id => T(LAWS[id].t)).join(", ") }) }), el("small", { text: T("in force at the start of every campaign this week") })));
        li.push(el("li", null, el("span", { text: wl ? Fd("This week: {x} leads with {n} of {m} finished campaigns", { x: nm(wl), n: wk.wins[wl], m: wk.finished }) : T("This week: no campaign finished yet") }), el("small", { text: countLine() })));
        col().append(el("h4", { text: T("The governor’s count") }), el("ul", { class: "cv-book" }, li));
      }
      const built = s.built || {}, bl = Object.keys(BUILDS).filter(k => built[k]);
      if (bl.length) col().append(el("h4", { text: T("Built by the players") }), el("ul", { class: "cv-book" }, bl.map(k => el("li", { class: "k-gift" }, el("span", { text: Fd({ roof: "{n} roofs for the school", lamp: "{n} lamps for the lighthouse", stone: "{n} stones in Tano’s circle" }[k], { n: built[k] }) })))));
      const rec = (s.recent || []).slice(0, 4);
      if (rec.length) col().append(el("h4", { text: T("Just now on the island") }), el("ol", { class: "cv-book" }, rec.map(e => el("li", { class: "k-" + e.k }, el("small", { text: isleAgo(e.t) + (e.h ? " · " + T("the islanders") : "") }), el("span", { text: isleLine(e) })))));
      extra.append(el("p", { class: "cv-note small", text: T("Counted by the relay from what each game tells it, not read from the chain. The islanders fill the quiet hours.") }));
      if (back) extra.append(el("div", { class: "cv-acts" }, btn(T("Back to the Book"), () => openCard("book", PLACE.book))));
      box.querySelector(".cv-acts").before(extra);
    });
  }

  /* ---------- the players' board: test wallets ranked by the relay (infra/relay/isle.py), never people or names ----------
     A wallet is on it once it has signed a move into the testnet from the same connection the game reports from, so
     nobody can put numbers on someone else's wallet. Each week counts a wallet's first finished campaign; all time adds
     the weeks up. The short pushed summary shows at once; `isle board <wallet>` brings where this browser's wallet stands. */
  const BOARD = { me: null, at: 0, view: null };
  const shortPk = pk => pk.slice(0, 6) + "…" + pk.slice(-4);
  function onBoard(b) { BOARD.me = b.me || null; BOARD.at = Date.now(); if (ISLE.s) ISLE.s.board = Object.assign({}, ISLE.s.board, { best: b.best.slice(0, 5), busy: b.busy.slice(0, 5), ever: b.ever.slice(0, 5), prev: b.prev }); const old = UI.card && UI.card._board && UI.card.querySelector(".cv-board"); if (old && ISLE.s) { old.replaceWith(boardBody(ISLE.s.board)); fitCard(UI.card); } }
  function boardRows(rows, mine, text, empty) {
    if (!rows || !rows.length) return el("p", { class: "cv-note small", text: empty });
    return el("ul", { class: "cv-book cv-rank" }, rows.map(r => el("li", { class: r.id === mine ? "me" : null },
      el("span", null, el("b", { text: "#" + r.n + " " }), el("span", { class: "pk", translate: "no", text: r.id }), r.id === mine ? el("em", { text: " · " + T("you") }) : null), el("small", { text: text(r) }))));
  }
  function openBoard() {
    const b = ISLE.s && ISLE.s.board, pk = myPk();
    if (pk && Date.now() - BOARD.at > 15000) isleTell("board", pk);
    openCard(null, box => {
      box._board = true; box.classList.add("isle-card");
      const back = [btn(T("The island today"), () => openIsle()), btn(T("Back to the island"), () => closeCard(), { go: true })];
      if (!b) { scene(box, "sam", T("The players’ board"), T("The island’s numbers are out of reach just now. Your campaign goes on as before."), back); return; }
      scene(box, "sam", T("The players’ board"), T("The players here are test wallets, not people. A move counts for a wallet when that wallet signed it into the testnet from the same connection. Each week counts a wallet’s first finished campaign; the result is what its game reports."), back);
      box.querySelector(".cv-acts").before(boardBody(b));
    });
  }
  function boardBody(b) {
    const pk = myPk(), mine = pk ? shortPk(pk) : null, me = BOARD.me;
    const result = r => [F(r.won ? "as {x} · elected · {n} of 10 votes" : "as {x} · not elected · {n} of 10 votes", { x: nm(r.as), n: r.votes }), r.goal && AMB[r.goal] ? Fd("ambition reached: {x}", { x: T(AMB[r.goal].name) }) : ""].filter(Boolean).join(" · ");
    const LISTS = {
      best: [T("Best results this week"), () => boardRows(b.best, mine, result, T("No campaign finished yet this week."))],
      busy: [T("Most active this week"), () => boardRows(b.busy, mine, r => F("{n} moves · {m} laws passed", { n: r.moves, m: r.laws }) + (r.as ? " · " + F("as {x}", { x: nm(r.as) }) : ""), T("No move signed yet this week."))],
      ever: [T("All time"), () => boardRows(b.ever, mine, r => F("elected {n} of {m} times", { n: r.won, m: r.played }) + (r.goals ? " · " + F("ambitions reached: {n}", { n: r.goals }) : ""), T("Nobody yet."))],
    };
    if (!LISTS[BOARD.view]) BOARD.view = b.best && b.best.length ? "best" : "busy";
    /* one list at a time: the plate is narrow and never scrolls */
    const extra = el("div", { class: "cv-isle cv-board" }), seg = el("div", { class: "cv-seg", role: "group" });
    Object.keys(LISTS).forEach(k => seg.append(el("button", { type: "button", "aria-pressed": k === BOARD.view ? "true" : "false", text: LISTS[k][0],
      onclick: e => { e.stopPropagation(); BOARD.view = k; SND.sfx("tap"); extra.replaceWith(boardBody(b)); if (UI.card) fitCard(UI.card); } })));
    extra.append(el("div", { class: "cv-seg-row" }, el("h4", { text: T("Ranking") }), seg), LISTS[BOARD.view][1]());
    const you = !pk ? T("No test wallet in this browser yet; your first signed move makes one.")
      : !me || (!me.busy && !me.best && !me.ever) ? F("Your test wallet {h} is not on the board yet: it joins with your next move signed into the testnet.", { h: mine })
      : me.best ? F("Your test wallet {h}: place {n} for results, place {m} for moves this week.", { h: mine, n: me.best, m: me.busy || 0 })
      : me.busy ? F("Your test wallet {h}: place {n} for moves this week; your result joins when your campaign ends.", { h: mine, n: me.busy })
      : F("Your test wallet {h}: place {n} all time.", { h: mine, n: me.ever });
    extra.append(el("p", { class: "cv-note cv-me" }, el("b", { text: you })));
    const prev = b.prev && b.prev.best && b.prev.best[0];
    if (prev) extra.append(el("p", { class: "cv-note small", text: F("Last week’s best: {h}, as {x}, {n} of 10 votes", { h: prev.id, x: nm(prev.as), n: prev.votes }) }));
    return extra;
  }

  /* ---------- the start: pick your candidate ---------- */
  function start() {
    G = load();
    if (G) { G.onchain = true; hud(); if (G.picked === "…") G.picked = null; signUp(); if (G.over) return ending(); if (!FREE && G.week && G.week !== weekId()) return decideLate(); if (G.counting) { G.counting = false; return election(); } if (G.waiting) return resume(); if (G.move >= MOVES) return endDay(); setTimeout(signsOn, 800); followTxs(); return; }
    SC.setHour(0, true); hud();
    openCard(null, introCard);
  }
  /* ---------- signs at the places until the first move: a newcomer sees at once where to go, and that a tap is a move ----------
     The names stand over the buildings, the council hall marked as the place to start. They follow the island when it is
     panned on a phone, hide behind every card, and never come back once a move was made in this browser. */
  const SIGNS = ["hall", "market", "radio", "north", "south", "bar", "book"], SIGNED = "rabbit-first-move";
  let signsRaf = 0;
  function signsOn() {
    if (store.get(SIGNED) || !G || G.over || G.move >= MOVES || $("cvSigns")) return;
    const host = el("div", { class: "signs", id: "cvSigns", "aria-label": T("Places on the island") });
    const few = $("cvStage").clientWidth < 700;   // a phone: the four that matter first, the embassies and the bar stay in ☰
    SIGNS.filter(id => SC.places[id] && PLACE[id] && !SC.locked(id) && !(few && /^(north|south|bar)$/.test(id))).forEach(id => {
      const b = el("button", { type: "button", class: "sign" + (id === "hall" ? " go" : ""), "data-id": id, onclick: e => { e.stopPropagation(); wake(); if (G && !UI.card) openCard(id, PLACE[id]); } }, el("b", { text: T(SC.places[id].name) }));
      if (id === "hall") b.append(el("small", { text: T("Start here: propose a law") }));
      host.append(b);
    });
    $("cvStage").append(host);
    /* each sign hangs under its place's ground point; one that would cover another slides down, one at the edge slides in */
    const place = () => {
      if (!host.isConnected) { signsRaf = 0; return; }
      const W = host.clientWidth, put = [];
      for (const b of host.querySelectorAll(".sign")) {
        const p = SC.places[b.dataset.id] || {}, w = b.offsetWidth, h = b.offsetHeight; let [x, y] = SC.toScreen(p.x, p.y);
        x = Math.max(w / 2 + 4, Math.min(W - w / 2 - 4, x)); y += 10;
        const base = y;   // a sign in another's way moves up when its place stands higher on the island, else down, until it is clear
        for (let n = 0, moved = true; moved && n < 8; n++) { moved = false; for (const o of put) if (Math.abs(o.x - x) < (o.w + w) / 2 + 6 && y < o.y + o.h + 6 && y + h + 6 > o.y) { y = base < o.base ? o.y - h - 8 : o.y + o.h + 8; moved = true; } }
        put.push({ x, y, w, h, base }); b.style.left = x + "px"; b.style.top = y + "px";
      }
      signsRaf = requestAnimationFrame(place);
    };
    place();
  }
  function signsOff() { const s = $("cvSigns"); if (s) s.remove(); if (signsRaf) { cancelAnimationFrame(signsRaf); signsRaf = 0; } }
  /* a laptop or a desktop: the four candidates stand large across the island at dusk, as in a game's opening scene, the
     facts in a quiet strip below them. A phone, or a screen too low for that, keeps the plate with four small faces. */
  const wideIntro = () => { const st = $("cvStage"); return !LAND.matches && innerWidth >= 900 && st.clientWidth >= 860 && st.clientHeight >= 480; };
  function introCard(box) {
    const wide = wideIntro(), stH = $("cvStage").clientHeight;
    box.classList.add("intro"); box.classList.toggle("wide", wide); box.classList.toggle("low", wide && stH < 760); box._wide = wide;
    /* the first twenty seconds, before the four faces: what the game is, what you are after, who the rivals are and why
       every move is on Tau; three chips under it say the same in three words each, one of them counted live */
    box.append(el("div", { class: "iv-head" }, el("p", { class: "kick", text: T("An election game on Tau Testnet Alpha") }), el("h2", { text: T("White Rabbit Key") }),
      el("p", { class: "cv-line", text: T("Run for governor of a small island. Your three rivals are played by the island; ten islanders vote on Sunday night, and whoever wins more of them governs next week. Three moves a day, six on your first, each one a real transaction on Tau Testnet Alpha from a test wallet this browser makes for you. Other people play beside you this week: on Sunday night every campaign counts.") }),
      el("div", { class: "iv-chips" },
        el("span", { class: "ivc", title: T("1 test AGRS per move, paid to the place where you make it. Wages and embassy money come back into your wallet; the rivals’ moves go on chain too. Test AGRS have no value.") }, el("i", { class: "dot", "aria-hidden": "true" }), el("span", { text: T("Every move: a real testnet transaction") })),
        isleIntro(),
        el("span", { class: "ivc", title: T("Ten islanders vote in every campaign. Every campaign won this week is a ballot for its candidate; the one with the most governs the island next week.") }, el("i", { class: "dot", "aria-hidden": "true" }), el("span", { text: Fd("Election Sunday night · count {x}", { x: countIn() }) })))));
    const pick = el("div", { class: "cv-pick" });
    /* wide: a canvas as large as the figure will stand (about half the stage high), drawn at twice that for sharpness */
    const big = Math.max(240, Math.min(640, Math.round(stH * 0.6)));
    Object.keys(CANDS).forEach(c => pick.append(el("button", { type: "button", class: "cv-cand", title: wide ? nm(c) + " · " + T(CANDS[c].role) : null, onclick: () => begin(c) },
      wide ? el("span", { class: "fig" }, portrait(c, big, 0, true)) : portrait(c, innerWidth < 760 || innerHeight < 520 ? 56 : 96),
      el("span", { class: "plate" }, el("b", { translate: "no", text: nm(c) }), el("small", { text: T(CANDS[c].role) }), el("em", { text: T(CANDS[c].pitch) })))));
    box.append(el("div", { class: "iv-cast" }, el("p", { class: "cv-h", text: T("Which candidate are you?") }), pick));
    /* under the four: the week in one line, who governs, the island's ballot as the chain shows it, the wallet */
    const td = todayIdx();
    const camp = [el("b", { text: T("Your campaign:") }), " ", T("this week, Monday to Sunday. An island day is a real day: three moves, a few minutes. Sunday evening the islanders vote."), " ",
      td === 1 ? T("Today is Monday: the week begins.") : td === DAYS ? T("Today is Sunday: play the whole week now, the vote is tonight.") : Fd("Today is {x}: catch up Monday to {y} briefly or start today, then a day a day.", { x: dayName(td), y: dayName(td - 1) })];
    box.append(el("div", { class: "iv-facts" }, el("p", { class: "cv-note" }, ...camp), el("p", { class: "cv-note cv-isle-gov" }, ...isleGov()), ballotEl(),
      el("p", { class: "cv-note cv-chain" }, el("a", { href: "/wallet/", text: T("Your test wallet") }), " · ", el("span", { text: T("Test AGRS have no value.") }))));
  }
  /* once per browser, after the first move signed into the testnet: where that move can be seen, and the two other pages
     the same test wallet opens. Shown at the first quiet moment, so it never cuts into a scene. */
  function bridgeCard() {
    store.set("rabbit-bridged", "1");
    const pk = myPk(), h = /^[0-9a-f]{64}$/.test(G.picked || "") ? G.picked : null, lang = window.TauI18n && TauI18n.lang !== "en" ? "&lang=" + TauI18n.lang : "";
    const open = u => window.open(u, "_blank", "noopener");
    openCard(null, box => {
      box.classList.add("paper");
      box.append(el("div", { class: "cv-paper" }, el("p", { class: "mast", text: T("The Key Crier") }), el("p", { class: "date", text: T("Extra") }),
        el("p", { class: "lead", text: T("Your first move is on Tau Testnet Alpha: 1 test AGRS to the Book, signed by the test wallet this browser made for you. The same wallet opens two more pages, and Agorzilla eats transactions like yours.") }),
        el("ul", null, el("li", { text: T("Explorer: the transaction itself, and the block that sealed it.") }),
          el("li", { text: T("Your Tau card: one picture of what this wallet did on the testnet, to post or keep.") }),
          el("li", { text: T("Agorzilla: a creature fed by live testnet transactions, with its own test wallet on agorzilla.com.") }))),
        el("div", { class: "cv-acts" },
          btn(T("See it in the Explorer"), () => open(h ? "/explorer/?tx=" + h + lang : "/explorer/?a=" + pk + lang), { go: true }),
          btn(T("Your Tau card"), () => open("/card/?a=" + pk + lang)),
          btn(T("Feed Agorzilla"), () => open("https://agorzilla.com/")),
          btn(T("Back to the island"), () => closeCard())));
    });
  }
  setInterval(() => { if (G && !G.over && G.picked && G.picked !== "…" && myPk() && !store.get("rabbit-bridged") && !UI.card && !drawer && !document.hidden) bridgeCard(); }, 4000);
  function dragHint() {
    if (!matchMedia("(pointer: coarse) and (orientation: portrait)").matches || store.get("rabbit-drag-hint")) return;
    setTimeout(() => { if (G && !UI.card && SC.canPan()) { store.set("rabbit-drag-hint", "1"); toast(T("Drag the island to look around, or turn your phone sideways. ☰ lists every place.")); } }, 3500);
  }
  function begin(c) {
    G = fresh(c); save();
    signUp();
    const start = () => {
      news(T("The Key Crier: a week to the election, Sunday night. Everything anyone does is written in the Book."), RICO.L.bkWeek);
      isleRule();
      closeCard(); hud();
      welcome();
    };
    const td = todayIdx();
    if (!FREE && td > 1 && td < DAYS) return lateCard(td, start);
    start();
  }
  /* a campaign begun in the middle of the week: the days before today are either played briefly, one move a day with the
     rivals moving every night as usual, or skipped, the rivals' nights run and the campaign starts today with three moves.
     A Sunday start keeps the whole week in one go: the vote is tonight. */
  const briefDay = () => !!(G && G.brief && !FREE && G.day < todayIdx());
  function lateCard(td, then) {
    openCard(null, box => {
      box.classList.add("paper");
      box.append(el("div", { class: "cv-paper" }, el("p", { class: "mast", text: T("The Key Crier") }), el("p", { class: "date", text: dayName(td) }),
        el("p", { class: "lead", text: Fd("It is {x} already: Monday to {y} went by without you. Catch up briefly, or start today with the island as the rivals left it.", { x: dayName(td), y: dayName(td - 1) }) })),
        el("div", { class: "cv-acts" },
          btn(T("Catch up briefly"), () => { G.brief = true; G.spare = 0; if (briefDay()) G.move = MOVES - 1; save(); then(); }, { go: true, sub: Fd("{n} days with one move each, then today with three", { n: td - 1 }) }),
          btn(T("Play from today"), () => { skipTo(td); then(); }, { sub: T("Six moves today, then three a day; what the rivals did until now is in the Book") })));
    });
  }
  function skipTo(td) {
    while (G.day < td) { night(); G.day++; }
    G.move = 0; G.skipped = td - 1;
    news(Fd("{x} joined the race on {y}; until then the rivals had the island to themselves.", { x: nm(G.me), y: dayName(td) }), RICO.L.bkWeek);
    save();
  }
  /* the pick is the campaign's first transaction, with no click of its own: as Old Sam writes the name into the Book, the
     visitor's test wallet (made here if there is none yet) signs 1 test AGRS to the Book's till. Once it is through, the
     relay puts that wallet on the players' board and counts which candidate it picked (isle start; its favourite shows
     on the wallet's Tau card). A campaign from before this was signed once, the next time the page opens. */
  function signUp() {
    if (!G || !G.onchain || G.picked || G.over || (!FREE && G.week && G.week !== weekId())) return;
    const me = G.me;
    G.picked = "…";
    mySend(TILL.book, F("{x}, name written into the Book", { x: nm(me) }), h => {
      if (!G || G.me !== me) return;
      if (!h) { G.picked = null; return; }
      G.picked = h; save();
      const pk = myPk(); if (pk) isleTell("start", gidOf(), me, pk);
    }, 1, "book");
  }
  /* the first scene of a campaign: Old Sam writes your name into the Book, and says what you stand for and when the island votes */
  const WELCOME = {
    marisol: "So it is true, Marisol: your name is on the list, in my own hand. Four candidates, one governor’s chair under the council tree, and on Sunday night the ten islanders who vote choose who sits in it. You hear everything first at your café. This week the island hears about you. Every move you make goes into this Book.",
    tobias: "So it is true, Tobias: the harbour master wants to be governor. Your name is on the list, in my own hand. Four candidates, one chair under the council tree, and on Sunday night the ten islanders who vote choose who sits in it. The embassies know you already. The island will know you by what goes into this Book.",
    baako: "So it is true, Baako: your name is on the list, in my own hand. You count everything, so count this: four candidates, one governor’s chair under the council tree, ten islanders who vote on Sunday night. Every move you make goes into this Book, and I count too.",
    hana: "So it is true, Hana: your name is on the list, in my own hand. Four candidates, one governor’s chair under the council tree, and on Sunday night the ten islanders who vote choose who sits in it. You write everything down, so you know how this works. Laws are made in the Council Hall. Everything else is written here.",
  };
  function welcome() {
    const after = () => { toast(T("Tap a sign for your first move: a real transaction on Tau Testnet Alpha.")); signsOn(); dragHint(); };
    const go = () => { closeCard(); const pend = G.pending.splice(0); if (pend.length) councilQueue(pend, after); else after(); };   // a campaign begun today: the rivals' laws from the skipped nights come to the council first
    openCard("book", box => {
      box.classList.add("welcome");
      scene(box, "sam", T("Your name in the Book"), T(WELCOME[G.me]), [btn(T("Walk onto the island"), go, { go: true })],
        el("p", { class: "cv-note" }, el("b", { text: T("You:") }), " ", F("{x}, candidate for governor. Ten islanders vote on Sunday night; win more of them than the other three.", { x: nm(G.me) })),
        el("p", { class: "cv-note small" }, el("b", { text: T("On the testnet:") }), " ", T("Sam’s entry is your first transaction, signed by your test wallet in this browser: 1 test AGRS to the Book. It puts your wallet on the players’ board.")));
      box.querySelector(".cv-x").onclick = go;
    });
  }
  function help() {
    openCard("pier", box => scene(box, "sam", T("How it works"), T("Three moves a day, six on your first day, seven days from Monday to Sunday, then the island votes. Each of the ten islanders cares about two things; laws and talk about those win them over. Rumours work for a day, until people read the Book."), [btn(T("Licence and credits"), () => window.open("https://github.com/jimb000o/tau-command-hud/blob/main/rabbit/LICENSE.md", "_blank", "noopener")), btn(T("Back to the island"), () => closeCard(), { go: true })],
      el("ul", { class: "cv-help" }, el("li", { text: T("Council Hall: propose a law. Two of the other three candidates must vote yes. A law that contradicts one in force is refused first.") }),
        el("li", { text: T("Market square: talk about a topic. People who care about it move toward you.") }), el("li", { text: T("Radio Coco: pay for a line on air. True lines are safe. Lies come back when people read the Book.") }),
        el("li", { text: T("Embassies: coins now, for a promise to propose their law. Forget it and they tell everyone.") }), el("li", { text: T("Bar La Ola: pacts. Partners vote for each other’s laws.") }),
        el("li", { text: T("The lighthouse: the Book. Free to read, and nobody can change it.") }),
        el("li", { text: T("Free, no move: asking anyone a question, reading the Book, The island today, and every visit to the school, the dive centre, the works, the camp, the old ship, the stone circle and the drums. One more move: the evening bell at eight, your first pact, the key in the grotto.") }),
        el("li", { text: T("The coins you have left when a campaign ends are saved in this browser. At the school, the lighthouse and the stone circle they pay for things the island keeps, and everyone sees the count in The island today.") }),
        el("li", { text: T("On day two or three someone who has read the Book makes you an offer: a goal of your own beside the election, with its own ending in the special edition.") }),
        el("li", { text: T("Some mornings something happens to the island. The Key Crier leads with it, you get one choice, and that topic is the talk of the week: speeches about it count more and laws for it pass more easily.") }),
        el("li", { text: T("Election night: the visitors of the site cast an eleventh ballot, for whoever leads the island ballot on the real testnet.") }),
        el("li", { text: T("One clock, the real one (German time). An island day is a real day with three moves; a campaign is this week, Monday to Sunday, and the islanders vote on Sunday evening. Days of the week you have not played yet are played in one go, so a Wednesday start means Monday to Wednesday now and then a day a day. Monday 00:00 the island counts every campaign of the week: the governor’s count.") }),
        el("li", { text: T("The governor’s count: every campaign won is one ballot for its candidate. Whoever has the most governs the island the week after, and the laws most often in force at the end of those campaigns are the island’s laws, in force when every new campaign starts. Repeal them in the hall if you must.") }),
        el("li", { text: T("On the chain: every line in the Book is also a transaction on Tau Testnet Alpha, 1 test AGRS to the island council. The rivals send theirs from their own campaign wallets, yours from the test wallet this browser made for you. A ⛓ in the Book marks them.") }),
        el("li", { text: T("Inspired by \"Caribbean Disaster\" (1995). An independent homage, not affiliated with or endorsed by its creators. All art, characters, story and music are original.") }))));
  }
  /* ?voice=check: one tap plays Rico's first line and the plate shows each step, for a phone that stays silent */
  function voiceCheck() {
    openCard(null, box => {
      box.classList.add("intro");
      const list = el("ul", { class: "cv-help" }, el("li", { text: "Tap the button. Rico should say his first line." }));
      box.append(el("h3", { text: "Voice check" }), list, el("div", { class: "cv-acts" },
        btn("Play Rico", async () => { wake(); SND.start(); const r = await RICO.check(); list.replaceChildren(...r.map(t => el("li", { text: t }))); }, { go: true }),
        btn("Back to the island", () => { closeCard(); start(); })));
    });
  }
  let toastT = 0;
  function toast(s) { const t = $("cvToast"); t.textContent = s; t.classList.add("on"); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("on"), Math.max(2600, s.length * 55)); }

  /* ---------- the cat and the legend ---------- */
  /* Déjà cannot be fed by one person: she eats only on days when at least three wallets agree (agorzilla.com/cat/) */
  const dejaDay = () => Math.floor((Date.now() / 1000 - DEJA.born) / 86400);
  const fedDeja = () => !!G && G.deja === dejaDay();
  function dejaFetch(done) {
    if (window.TauSim && TauSim.on) return done && done(null);
    if (DJ_S.s && Date.now() - DJ_S.at < 60000) return done && done(DJ_S.s);
    fetch("https://node.tauhud.com/deja", { cache: "no-store" }).then(r => (r.ok ? r.json() : null)).then(j => { if (j && typeof j.agreed === "number") { if (j.fed && SRC.fed === false) call("dejaFed", "deja", null, { keys: ["deja3"] }); SRC.fed = !!j.fed; DJ_S.s = j; DJ_S.at = Date.now(); } done && done(DJ_S.s); }, () => done && done(DJ_S.s));
  }
  /* her count as a line of the card: what the relay saw today, or a pointer to her page */
  function dejaStatus(s) {
    if (!s) return T("Her count for today is on her page.");
    const n = s.agreed + (s.partial && !s.fed ? "+" : "");
    const left = Math.max(0, s.closes_at - Date.now() / 1000);
    return (s.fed ? Fd("She has eaten today: {n} wallets agreed.", { n }) : s.agreed ? Fd("Today: {n} of 3 wallets agreed.", { n }) : T("Nobody has agreed yet today."))
      + " " + Fd("Her day closes {x}, 19:00 German time.", { x: spanText(left) });
  }
  function deja() {
    SND.sfx("meow");
    openCard(null, box => {
      const status = el("p", { class: "cv-note", text: dejaStatus(DJ_S.s) });
      scene(box, "marisol", T("Déjà, the café cat"), T("Nobody owns her, and nobody feeds her alone: she eats on a day only when three wallets agree, one test AGRS each. Say yes and you are one of the three. The other two? Whoever passes through."), [
        status,
        btn(T("Agree to feed her · 1 test AGRS"), agreeDeja, { off: fedDeja() || !G.onchain, sub: fedDeja() ? T("You agreed today") : G.onchain ? T("once a day, no move, no coins: one real transaction from your wallet") : T("needs the testnet") }),
        btn(T("Her page: agorzilla.com/cat/"), () => window.open("https://agorzilla.com/cat/", "_blank", "noopener")),
        btn(T("Back to the island"), () => closeCard(), { go: true }),
      ]);
      dejaFetch(s => { status.textContent = dejaStatus(s); });
    });
  }
  function agreeDeja() {
    if (fedDeja() || !G.onchain) return;
    G.deja = dejaDay();
    const b = { day: G.day, hour: Math.min(2, G.move), who: G.me, text: T("agreed to feed Déjà, the café cat"), kind: "gift", at: "market", pay: 1 };
    G.book.push(b); save();
    mySend(DEJA.bowl, T("agreed to feed Déjà"), h => { if (h) { b.tx = h; save(); DJ_S.at = 0; } }, 1, null);
    SND.sfx("meow"); toast(T("You agreed. Déjà looked at you as if she had expected it."));
    if (UI.card) deja();
  }
  /* Rico's line about her: her count as a word (one, two), so the line has its clip; more than three shown beside */
  function dejaLines() {
    const s = DJ_S.s, L = []; if (!s || Date.now() - DJ_S.at > 1800000) return L;
    if (s.fed) L.push({ k: "deja:fed", parts: [V("dejaFed"), ...(s.agreed > 3 ? [Q("({n} wallets)", { n: s.agreed })] : [])] });
    else if (s.agreed >= 1 && s.agreed <= 2) L.push({ k: "deja:" + s.agreed, parts: [{ t: F(RICO.L.dejaN, { n: s.agreed }), v: RICO.fill(RICO.L.dejaN, { n: ["one", "two"][s.agreed - 1] }) }] });
    else L.push({ k: "deja:0", parts: [V("dejaNone")] });
    return L;
  }
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
      const id = SC.hit(...where(e)); cv.style.cursor = id ? "pointer" : "default";   // only the name and the hand: the painting itself never lights up under the mouse
      UI.q = false;
      if (!id) { if (SC.lockedAt(...where(e))) tipAt(e, "?"); else tip.hidden = true; return; }   // a quarter not open yet: only a "?"
      tipAt(e, id === "rabbit" ? T("The white rabbit: follow it") : id === "agorzilla" ? T("Something moves in the jungle") : id === "deja" ? T("Déjà, the café cat") : T(SC.places[id].name));
    });
    function tipAt(e, text) {   // the label next to the pointer
      tip.hidden = false; tip.textContent = text;
      const r = $("cvStage").getBoundingClientRect(); tip.style.left = Math.min(r.width - 180, e.clientX - r.left + 14) + "px"; tip.style.top = (e.clientY - r.top + 14) + "px";
    }
    cv.addEventListener("pointerleave", () => { tip.hidden = true; });
    cv.addEventListener("pointerdown", e => { UI.touch = e.pointerType !== "mouse"; });
    cv.addEventListener("click", e => {
      wake();
      if (!G) return;
      if (SC.hit(...where(e)) === "deja") { deja(); return; }   // she may sit in a room while its card is open
      if (UI.card) { if (!UI.card.classList.contains("intro") && !UI.card.classList.contains("paper") && !UI.card.classList.contains("end") && !UI.card.classList.contains("locked")) closeCard(); return; }
      const id = SC.hit(...where(e)); tip.hidden = true;
      /* a tap on a quarter not open yet (a phone has no hover): the "?" for a moment */
      if (!id && SC.lockedAt(...where(e))) { tipAt(e, "?"); if (UI.touch) { UI.q = true; clearTimeout(UI.qt); UI.qt = setTimeout(() => { if (UI.q) tip.hidden = true; }, 1400); } return; }
      if (id === "rabbit") { if (G.over || G.move >= MOVES) return; const [to, line] = hint(); toast(line); SND.sfx("tap"); setTimeout(() => openCard(to, PLACE[to]), 700); return; }
      if (id === "agorzilla") { legend(); return; }
      if (id && PLACE[id]) openCard(id, PLACE[id]);
    });
    /* places by keyboard: the list under the scene, one button each */
    placeKeys();
    addEventListener("keydown", e => { if (e.key === "Escape" && UI.card && !UI.card.classList.contains("intro") && !UI.card.classList.contains("locked")) closeCard(); });
    /* the day's last move is spent and nothing is open any more: the night comes, however the last card was left */
    setInterval(() => { if (G && !G.over && !G.waiting && G.move >= MOVES && !UI.card && !drawer) { if (G.counting) { G.counting = false; election(); } else endDay(); } }, 1200);
    /* after the election the result stays: a card closed over it (the Book read from the result, ✕, Escape) brings it back,
       so nobody is left on a finished island without "Play again" */
    setInterval(() => { if (G && G.over && !UI.card && !drawer && !$("cvPlaces").classList.contains("on")) ending(); }, 1500);
    $("cvHelp").onclick = () => { wake(); help(); };
    $("cvBookBtn").onclick = () => { wake(); if (G) openCard("book", PLACE.book); };
    $("cvIsle").onclick = () => { wake(); openIsle(); };
    if ($("cvChainChip")) $("cvChainChip").onclick = () => { wake(); chainCard(); };
    if ($("cvBell")) { $("cvBell").onclick = () => { wake(); answerBell(); }; bellChip(); setInterval(bellChip, 5000); }
    if ($("cvShip")) { $("cvShip").onclick = () => { wake(); shipCard(); }; shipFetch(); setInterval(() => { if (!document.hidden || SND.on) shipFetch(); }, 60000); }
    isleJoin();
    const sb = $("cvSound");
    const showSound = () => { const l = SND.on ? T("Sound on") : SND.wanted ? T("Tap for sound") : T("Sound off"); sb.replaceChildren("♪", el("span", { class: "lb", text: " " + l })); sb.setAttribute("aria-label", l); sb.classList.toggle("off", !SND.wanted); sb.setAttribute("aria-pressed", SND.on ? "true" : "false"); };
    let woke = 0;   // the press that just started the music must not also switch it off
    sb.onclick = e => { e.stopPropagation(); if (Date.now() - woke < 800) return showSound(); if (!SND.on && SND.wanted) SND.start(); else SND.toggle(); showSound(); };
    /* the music starts as the page opens; where the browser holds it back, it starts on the first click, tap or key anywhere */
    const GESTURES = ["pointerdown", "touchstart", "keydown", "click"];
    wake = () => { if (!SND.on && SND.wanted) { SND.start(); woke = Date.now(); } showSound(); if (SND.on || !SND.wanted) GESTURES.forEach(n => removeEventListener(n, wake, true)); };
    GESTURES.forEach(n => addEventListener(n, wake, true));
    SND.onchange = showSound;
    if (SND.wanted) SND.start();
    showSound();
    /* full screen in one tap, on every device: the whole page goes full screen (so the wallet drawer stays visible) and
       only the island and its bar are left; a phone turns to landscape where it can. An iPhone has no full screen for a
       page: there the header and the tab bar go away all the same, and a hint says how to get the rest. */
    const fs = $("cvFull"), root = document.documentElement;
    const fsEl = () => document.fullscreenElement || document.webkitFullscreenElement;
    const canFs = !!(root.requestFullscreen || root.webkitRequestFullscreen) && (document.fullscreenEnabled !== false || document.webkitFullscreenEnabled);
    const full = on => {
      root.classList.toggle("rk-full", on); fs.setAttribute("aria-pressed", on ? "true" : "false"); fs.title = T(on ? "Leave full screen" : "Full screen");
      setTimeout(() => window.dispatchEvent(new Event("resize")), 60);
    };
    fs.onclick = e => {
      e.stopPropagation(); wake();
      if (root.classList.contains("rk-full")) { full(false); if (fsEl()) (document.exitFullscreen || document.webkitExitFullscreen).call(document); return; }
      full(true);
      if (!canFs) { if (!store.get("rabbit-ios-full")) { store.set("rabbit-ios-full", "1"); toast(T("Full screen on an iPhone: Share, then Add to Home Screen, and start the game from there.")); } return; }
      try {
        const p = (root.requestFullscreen || root.webkitRequestFullscreen).call(root, { navigationUI: "hide" });
        const turn = () => { if (matchMedia("(pointer: coarse)").matches && screen.orientation && screen.orientation.lock) screen.orientation.lock("landscape").catch(() => {}); };
        if (p && p.then) p.then(turn, () => {}); else turn();
      } catch (err) {}
    };
    const pf = $("cvPlayFull"); if (pf) pf.onclick = e => fs.onclick(e);   // the big button on a phone held upright does what ⛶ does
    ["fullscreenchange", "webkitfullscreenchange"].forEach(n => document.addEventListener(n, () => { if (!fsEl() && canFs) full(false); }));
    if (navigator.standalone || matchMedia("(display-mode: standalone), (display-mode: fullscreen)").matches) full(true);   // started from the home screen
    /* ☰: every place as a button (the island is small on a phone, and some quarters sit at its edges) */
    const go = $("cvGo"), list = $("cvPlaces");
    const showList = on => { list.classList.toggle("on", on); go.setAttribute("aria-expanded", on ? "true" : "false"); };
    go.onclick = e => { e.stopPropagation(); wake(); if (UI.card && !UI.card.classList.contains("intro")) closeCard(); showList(!list.classList.contains("on")); };
    /* a tapped place lets go of its button: a focused button keeps the list showing (for the keyboard), and on a phone
       turned sideways it stood over the room behind the plate */
    list.addEventListener("click", e => { showList(false); if (e.detail && list.contains(document.activeElement)) document.activeElement.blur(); });
    /* a phone held upright sees part of the island: say once that it can be dragged, or turned */
    dragHint();
    $("cvReset").onclick = () => { if (confirm(T("Start a new election? This game will be lost."))) { store.del(KEY); G = null; closeCard(); start(); } };
    /* debug: ?rabbit=<place> opens a place, &day= and &move= set the day */
    const q = new URLSearchParams(location.search);
    start();
    if (q.get("rabbit") === "end" && G) { G.over = { win: G.me, count: {}, lies: 0 }; ending(); }
    else if (q.get("rabbit") && G && PLACE[q.get("rabbit")]) openCard(q.get("rabbit"), PLACE[q.get("rabbit")]);
    else if (q.get("rabbit") === "paper" && G) morning(3);
    if (q.get("voice") === "check") voiceCheck();
  }
  setTimeout(readBallot, 1200);
  window.COVE_GAME = { get state() { return G; }, begin, endDay, face, ending, open: p => openCard(p, PLACE[p]) };
  wire();
})();

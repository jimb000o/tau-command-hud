/* The wallets that walk on White Rabbit Key: every wallet that sent a real transaction on Tau Net testnet in the last day
   walks on the island as a small islander (relay infra/relay/walkers.py, GET node.tauhud.com/walkers). Hover says what
   it is, a click opens a card with what the chain tells about it, read as a few plain traits (a night owl, Agorzilla's
   friend, writes its own rules …), and the islander carries the matching thing: a lantern, a banana, a scroll.

   Only wallets, never people: nothing here knows who holds a key, and one person can hold many. Our own server's
   wallets never walk (the island bot, the cruise passengers, No Memo's purse, the hack of the week, the showcase
   wallets); IDNI's genesis accounts walk in grey. Nobody plays a walker: they walk by themselves, to the places
   that fit what their wallet does (the Council Hall for the island's politicians, the lighthouse for rule writers …).

   The look: without a choice, a wallet's islander is drawn from its key, always the same. The browser's own test
   wallet (tauhud.com/wallet/, the same key the game plays with) can choose its look here: the choice is a real
   transaction of LOOK + code test AGRS to the hearts box, which has no key behind it; the newest one counts.
   ?islander=1 opens the choice at once. Test params: ?walkers=demo shows made-up walkers (marked as such).
   Your own islander walks where you click (goTo), and every page sees it walk (remote, relay steer.py).
   window.ISLE_WALKERS = { figure, look, open, board, choose, goTo, remote, mine } */
(() => {
  "use strict";
  const SC = window.COVE_SCENE; if (!SC || !SC.extra) return;
  const RELAY = "https://node.tauhud.com", WS = "wss://node.tauhud.com", WKEY = "tauhud-wallet-key", MINE = "tauhud-islander-look";
  const T = s => (window.TauI18n ? TauI18n.t(s) : s);
  const F = (s, v) => T(s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m)));   // filled in first: the dictionaries match the whole sentence
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const Q = new URLSearchParams(location.search), DEMO = Q.get("walkers") === "demo";
  const phone = () => innerWidth < 760;
  const INK = "#22303a";

  /* ---------- the look: skin, hair or hat, shirt (code = skin * 64 + hair * 8 + shirt) ---------- */
  const SKINS = ["#f1c27d", "#e0ac69", "#c68642", "#a8693f", "#8d5524", "#5a3620"];
  const HAIRS = ["Short hair", "Long hair", "Bun", "Straw hat", "Cap", "Bandana", "Beanie", "Flower"];
  const SHIRTS = ["#e85d4a", "#f2b134", "#3aa6a0", "#f4f1ea", "#e86fa0", "#6fa8ff", "#a3e05a", "#c9a0ff"];
  const HAIRC = ["#1d1410", "#3b2416", "#6b4423", "#111", "#9a9aa0", "#c98c3c"];
  const LOOKS = 384;
  let BASE = 1200, BOX = "a43259757c7e5a26dae5dde9ce22ecafe2d7570c93e71ccf65756691d57e7a512e7fdfbfc78e9ce3bfd608b71e286a0b";
  const keyCode = a => parseInt(String(a || "0").slice(2, 10), 16) % LOOKS;
  const look = (code, a) => { const c = Number.isInteger(code) && code >= 0 && code < LOOKS ? code : keyCode(a); return { code: c, skin: Math.floor(c / 64), hair: Math.floor(c / 8) % 8, shirt: c % 8, hc: HAIRC[(c * 7 + 3) % HAIRC.length] }; };

  /* ---------- what a wallet's traits mean, and what its islander carries ---------- */
  const TRAITS = {
    idni: ["IDNI test account", "One of the accounts the testnet started with, set up by IDNI, the team behind Tau.", null, "hall"],
    winner: ["Island winner", "Won {n} White Rabbit Key elections.", "crown"],
    guardian: ["Guarded", "A guardian co-signs its bigger payments: its rule asks for a second signature.", "shield"],
    hacker: ["No Memo crew", "Cracked {n} No Memo chapters.", "visor"],
    lawmaker: ["Rule writer", "Wrote its own rule on the chain {n} times.", "scroll"],
    vault: ["Patient", "Its rule keeps its money locked until a date.", "scroll"],
    picky: ["Picky payer", "Its rule pays only addresses it trusts.", "scroll"],
    capped: ["Self-limited", "Its rule caps every payment.", "scroll"],
    frozen: ["Frozen", "Its rule stops every payment for now.", "scroll"],
    feeder: ["Agorzilla's friend", "Fed Agorzilla {n} times.", "banana"],
    catfriend: ["Café cat friend", "Put food in Déjà's bowl {n} times.", "cat"],
    politician: ["Island politician", "Plays White Rabbit Key: {n} moves on the island.", "rosette"],
    voter: ["Has a say", "Voted {n} times: Agorzilla's ballot boxes and the island's.", "ballot"],
    hearts: ["Heart giver", "Gave {n} hearts to parts of Tau HUD.", "heart"],
    nightowl: ["Night owl", "{n}% of its transactions between 22:00 and 05:00 German time.", "lantern"],
    earlybird: ["Early bird", "{n}% of its transactions between 05:00 and 09:00 German time.", "cup"],
    allrounder: ["Tries everything", "Used {n} different apps of Tau HUD and Agorzilla.", "backpack"],
    connector: ["Connector", "Paid {n} different wallets.", "satchel"],
    bigspender: ["Big mover", "Moved {n} test AGRS in all.", "coins"],
    busy: ["Busy", "{n} transactions in the last day: maybe a script, maybe very keen.", null],
    regular: ["Regular", "Active on {n} different days.", null],
    veteran: ["Old hand", "First seen {n} days ago.", "stick"],
    newcomer: ["Newcomer", "Its first transaction was in the last day.", "suitcase"],
    quiet: ["Quiet wanderer", "Sends now and then: {n} transactions so far.", null],
  };
  const HEAD = new Set(["crown", "visor"]), CHEST = new Set(["rosette", "heart"]), BUDDY = new Set(["cat"]);
  function gear(traits) {
    const g = {};
    for (const k of traits || []) {
      const it = (TRAITS[k] || [])[2]; if (!it) continue;
      const slot = HEAD.has(it) ? "head" : CHEST.has(it) ? "chest" : BUDDY.has(it) ? "buddy" : it === "backpack" || it === "satchel" ? "back" : "hand";
      if (!g[slot]) g[slot] = it;
    }
    return g;
  }
  const title = k => T((TRAITS[k] || TRAITS.quiet)[0]);

  /* ---------- drawing an islander: feet at (x, y), s = scale (1: about 28 world units tall) ---------- */
  function figure(g, x, y, s, lk, o = {}) {
    const t = o.t || 0, ph = o.ph || 0, go = o.walk ? 1 : 0, face = o.face || 1, grey = !!o.idni, gr = o.gear || {};
    const sw = Math.sin(ph) * 2.2 * go, bob = Math.abs(Math.sin(ph)) * 0.9 * go;
    const skin = SKINS[lk.skin], shirt = grey ? "#8d9097" : SHIRTS[lk.shirt], hc = grey ? "#2d2f33" : lk.hc;
    g.save(); g.translate(x, y); g.scale(s * face, s); g.lineCap = "round"; g.lineJoin = "round";
    g.fillStyle = "rgba(20,34,40,.28)"; g.beginPath(); g.ellipse(0, 0.5, 6, 1.8, 0, 0, Math.PI * 2); g.fill();
    if (gr.buddy === "cat") {   // a small cat at its heels
      const cx = -9, cy = 0, hop = Math.abs(Math.sin(ph * 1.3)) * 0.8 * go;
      g.fillStyle = "#3a3a3a"; g.strokeStyle = INK; g.lineWidth = 0.6;
      g.beginPath(); g.ellipse(cx, cy - 2.4 - hop, 3, 1.7, 0, 0, Math.PI * 2); g.fill();
      g.beginPath(); g.arc(cx + 2.8, cy - 4 - hop, 1.4, 0, Math.PI * 2); g.fill();
      g.beginPath(); g.moveTo(cx + 2.2, cy - 5.1 - hop); g.lineTo(cx + 2.5, cy - 6.3 - hop); g.lineTo(cx + 3, cy - 5.2 - hop); g.moveTo(cx + 3.2, cy - 5.1 - hop); g.lineTo(cx + 3.8, cy - 6.2 - hop); g.lineTo(cx + 4, cy - 4.9 - hop); g.fill();
      g.strokeStyle = "#3a3a3a"; g.lineWidth = 0.8; g.beginPath(); g.moveTo(cx - 2.8, cy - 2.6 - hop); g.quadraticCurveTo(cx - 5, cy - 5, cx - 4, cy - 6.5 - hop); g.stroke();
    }
    g.translate(0, -bob);
    if (gr.back) {   // a backpack or a satchel behind
      g.fillStyle = gr.back === "backpack" ? "#7a5a3a" : "#b08850"; g.strokeStyle = INK; g.lineWidth = 0.7;
      g.beginPath(); g.roundRect ? g.roundRect(-6.6, -18, 3.4, gr.back === "backpack" ? 7 : 5, 1) : g.rect(-6.6, -18, 3.4, 6); g.fill(); g.stroke();
    }
    g.strokeStyle = INK; g.lineWidth = 1.8;   // legs
    g.beginPath(); g.moveTo(-1.6, -9); g.lineTo(-1.6 + sw, 0); g.moveTo(1.6, -9); g.lineTo(1.6 - sw, 0); g.stroke();
    g.fillStyle = shirt; g.lineWidth = 0.9;   // body
    g.beginPath(); g.moveTo(-4.6, -8.5); g.lineTo(-3.6, -18.5); g.lineTo(3.6, -18.5); g.lineTo(4.6, -8.5); g.closePath(); g.fill(); g.stroke();
    g.lineWidth = 1.5; g.strokeStyle = skin;   // arms
    g.beginPath(); g.moveTo(-3.7, -17); g.lineTo(-5.3 - sw * 0.4, -10.5); g.moveTo(3.7, -17); g.lineTo(5.6 + sw * 0.4, -11); g.stroke();
    if (gr.chest === "heart") { g.fillStyle = "#e8436a"; g.beginPath(); g.moveTo(1.2, -12.6); g.bezierCurveTo(-0.6, -14, 0.1, -15.6, 1.2, -14.6); g.bezierCurveTo(2.3, -15.6, 3, -14, 1.2, -12.6); g.fill(); }
    if (gr.chest === "rosette") { g.fillStyle = "#e9b44c"; g.beginPath(); g.arc(1.6, -15, 1.3, 0, Math.PI * 2); g.fill(); g.fillStyle = "#c0533f"; g.fillRect(1, -13.8, 0.6, 1.8); g.fillRect(1.8, -13.8, 0.6, 1.8); }
    g.fillStyle = skin; g.strokeStyle = INK; g.lineWidth = 0.9;   // head
    g.beginPath(); g.arc(0, -22, 3.7, 0, Math.PI * 2); g.fill(); g.stroke();
    g.fillStyle = INK; g.beginPath(); g.arc(1.4, -22.4, 0.45, 0, Math.PI * 2); g.fill();
    hair(g, grey ? 4 : lk.hair, hc);
    if (gr.head === "crown") { g.fillStyle = "#f2c94c"; g.strokeStyle = INK; g.lineWidth = 0.6; g.beginPath(); g.moveTo(-3, -25.2); g.lineTo(-3, -28); g.lineTo(-1.5, -26.6); g.lineTo(0, -28.6); g.lineTo(1.5, -26.6); g.lineTo(3, -28); g.lineTo(3, -25.2); g.closePath(); g.fill(); g.stroke(); }
    if (gr.head === "visor") { g.fillStyle = "rgba(57,255,138,.9)"; g.fillRect(-1.2, -23.3, 4.6, 1.4); g.shadowColor = "#39ff8a"; g.shadowBlur = 4; g.fillRect(-1.2, -23.3, 4.6, 1.4); g.shadowBlur = 0; }
    hand(g, gr.hand, 5.6 + sw * 0.4, -11, t, o.light || 0);
    g.restore();
  }
  function hair(g, h, c) {
    g.fillStyle = c; g.strokeStyle = INK; g.lineWidth = 0.6;
    const cap = (col, brim) => { g.fillStyle = col; g.beginPath(); g.arc(0, -23, 3.9, Math.PI, 0); g.fill(); g.stroke(); if (brim) { g.beginPath(); g.ellipse(2.6, -23, 2.8, 0.7, 0, 0, Math.PI * 2); g.fill(); g.stroke(); } };
    switch (h) {
      case 0: g.beginPath(); g.arc(0, -22.8, 3.9, Math.PI * 1.05, Math.PI * 1.95); g.fill(); break;
      case 1: g.beginPath(); g.arc(0, -22.8, 4, Math.PI, Math.PI * 2); g.lineTo(3.4, -18.6); g.lineTo(2.4, -21); g.lineTo(-3.2, -21); g.lineTo(-4.2, -18); g.closePath(); g.fill(); break;
      case 2: g.beginPath(); g.arc(0, -22.8, 3.9, Math.PI * 1.05, Math.PI * 1.95); g.fill(); g.beginPath(); g.arc(-1.4, -27, 1.9, 0, Math.PI * 2); g.fill(); break;
      case 3: g.fillStyle = "#e3c26a"; g.beginPath(); g.ellipse(0, -24.6, 6.4, 1.4, 0, 0, Math.PI * 2); g.fill(); g.stroke(); g.beginPath(); g.arc(0, -24.8, 3.2, Math.PI, 0); g.fill(); g.stroke(); g.fillStyle = "#c0533f"; g.fillRect(-3.1, -25.6, 6.2, 0.8); break;
      case 4: cap("#284b63", true); break;
      case 5: cap("#c0533f", false); g.fillStyle = "#c0533f"; g.beginPath(); g.moveTo(-3.6, -22.6); g.lineTo(-6, -21.2); g.lineTo(-5.4, -23.4); g.fill(); break;
      case 6: cap("#2c8c88", false); g.fillStyle = "#f4f1ea"; g.beginPath(); g.arc(0, -27, 1.1, 0, Math.PI * 2); g.fill(); break;
      default: g.beginPath(); g.arc(0, -22.8, 3.9, Math.PI * 1.05, Math.PI * 1.95); g.fill(); g.fillStyle = "#e86fa0"; for (let k = 0; k < 5; k++) { const a = k / 5 * Math.PI * 2; g.beginPath(); g.arc(-2.6 + Math.cos(a) * 1, -25 + Math.sin(a) * 1, 0.8, 0, Math.PI * 2); g.fill(); } g.fillStyle = "#f2c94c"; g.beginPath(); g.arc(-2.6, -25, 0.6, 0, Math.PI * 2); g.fill();
    }
  }
  function hand(g, it, x, y, t, light) {
    if (!it) return;
    g.strokeStyle = INK; g.lineWidth = 0.6;
    if (it === "lantern") {
      g.strokeStyle = "#5a4a3a"; g.lineWidth = 0.6; g.beginPath(); g.moveTo(x, y); g.lineTo(x, y + 1.6); g.stroke();
      const glow = 0.55 + 0.45 * Math.sin(t * 0.004) * 0.3 + light * 0.4;
      g.fillStyle = `rgba(255,214,120,${glow})`; g.shadowColor = "#ffd678"; g.shadowBlur = 4 + light * 10; g.fillRect(x - 1.2, y + 1.6, 2.4, 3); g.shadowBlur = 0;
      g.strokeStyle = INK; g.strokeRect(x - 1.2, y + 1.6, 2.4, 3);
    } else if (it === "banana") {
      g.strokeStyle = "#f2c94c"; g.lineWidth = 1.4; g.beginPath(); g.arc(x + 1.5, y - 1, 2.6, Math.PI * 0.55, Math.PI * 1.35); g.stroke();
    } else if (it === "scroll") {
      g.fillStyle = "#f3e7c9"; g.fillRect(x - 0.4, y - 3.4, 2.2, 4.6); g.strokeRect(x - 0.4, y - 3.4, 2.2, 4.6); g.fillStyle = "#c0533f"; g.fillRect(x - 0.4, y - 1.4, 2.2, 0.6);
    } else if (it === "shield") {
      g.fillStyle = "#3aa6a0"; g.beginPath(); g.moveTo(x - 1.2, y - 3.4); g.lineTo(x + 2.8, y - 3.4); g.lineTo(x + 2.8, y - 0.8); g.quadraticCurveTo(x + 2.8, y + 1.6, x + 0.8, y + 2.4); g.quadraticCurveTo(x - 1.2, y + 1.6, x - 1.2, y - 0.8); g.closePath(); g.fill(); g.stroke();
      g.strokeStyle = "#f4f1ea"; g.lineWidth = 0.6; g.beginPath(); g.moveTo(x + 0.8, y - 2.6); g.lineTo(x + 0.8, y + 1.4); g.stroke();
    } else if (it === "stick") {
      g.strokeStyle = "#7a5a3a"; g.lineWidth = 0.9; g.beginPath(); g.moveTo(x + 0.6, y - 4); g.lineTo(x + 1.6, y + 11); g.stroke();
    } else if (it === "suitcase") {
      g.fillStyle = "#b5523b"; g.fillRect(x - 1, y + 1, 4.2, 3.4); g.strokeRect(x - 1, y + 1, 4.2, 3.4); g.beginPath(); g.moveTo(x + 0.2, y + 1); g.lineTo(x + 0.2, y); g.lineTo(x + 2, y); g.lineTo(x + 2, y + 1); g.stroke();
    } else if (it === "coins") {
      g.fillStyle = "#c9a35a"; g.beginPath(); g.arc(x + 0.8, y + 2.2, 2.1, 0, Math.PI * 2); g.fill(); g.stroke(); g.fillStyle = "#f2c94c"; g.beginPath(); g.arc(x + 0.8, y + 2.2, 0.8, 0, Math.PI * 2); g.fill();
    } else if (it === "ballot") {
      g.fillStyle = "#fbf3df"; g.fillRect(x - 0.2, y - 3, 2.6, 3.4); g.strokeRect(x - 0.2, y - 3, 2.6, 3.4); g.strokeStyle = "#2c8c88"; g.beginPath(); g.moveTo(x + 0.3, y - 1.6); g.lineTo(x + 0.9, y - 0.8); g.lineTo(x + 2, y - 2.4); g.stroke();
    } else if (it === "cup") {
      g.fillStyle = "#f4f1ea"; g.fillRect(x - 0.4, y - 2.6, 2.2, 2.4); g.strokeRect(x - 0.4, y - 2.6, 2.2, 2.4);
      g.strokeStyle = "rgba(255,255,255,.7)"; g.beginPath(); g.moveTo(x + 0.6, y - 3.2); g.quadraticCurveTo(x + 1.4, y - 4.4, x + 0.6, y - 5.4); g.stroke();
    }
  }

  /* ---------- who walks ---------- */
  const W = { list: [], by: new Map(), total: 0, idni: 0, at: 0, sel: null, bubble: null, nextBubble: 0, board: null, ok: false };
  const myPk = () => { try { const k = JSON.parse(store.get(WKEY) || "null"); return k && k.pk ? String(k.pk).toLowerCase() : null; } catch (e) { return null; } };
  const myLook = () => { const v = parseInt(store.get(MINE) || "", 10); return v >= 0 && v < LOOKS ? v : null; };
  const placeIds = () => Object.keys(SC.places).filter(id => SC.places[id] && Number.isFinite(SC.places[id].x));
  function spot(id) {
    const p = SC.places[id] || SC.places.market || SC.places.hall; if (!p) return [800, 600];
    return [p.x + (Math.random() - 0.5) * 90, p.y + 10 + Math.random() * 22];
  }
  /* on a painting whose ways are traced (paths.js) a walker keeps to them: it stands about a place's door and walks
     there along paths, beaches, bridges and stairs, never through a house, over a roof, a cliff or water */
  const ways = () => (SC.ways ? SC.ways() : null);
  function onWays(w, N) {   // a walker that came before the painting (or stood on another one) steps onto the ways
    const home = w.d && w.d.home != null ? N.door(w.d.home) : null;
    w.node = home != null ? home : N.near(w.x, w.y); [w.x, w.y] = N.stand(w.node); w.tx = w.x; w.ty = w.y; w.route = null; w.N = N;
  }
  function setOff(w, N) {   // where next: its home place more often than not, else one of three places picked at random, the nearest
    const ids = placeIds().filter(id => N.door(id) != null), home = w.d.home != null ? N.door(w.d.home) : null;
    let to = home != null && Math.random() < 0.55 ? home : null;
    if (to == null && ids.length) {
      let bd = Infinity;
      for (let k = 0; k < 3; k++) { const n = N.door(ids[Math.floor(Math.random() * ids.length)]), p = N.node(n), d = Math.hypot(p[0] - w.x, p[1] - w.y); if (d < bd) { bd = d; to = n; } }
    }
    if (to == null) to = w.node;
    w.route = N.route(w.x, w.y, w.node, to, w.lane); w.ri = 1; w.node = to;
    if (!w.route) w.wait = 3000;   // no way there: it stays a while and picks again
  }
  /* ---------- your own islander: it walks where you click, and every page on the island sees it walk ----------
     The browser's own test wallet (tauhud.com/wallet/, the key the game plays with) steers its walker: a click on the
     island walks it to the nearest spot it can reach on foot, a click on a place walks it to the door first (the game
     opens the place when it arrives, never more than about three seconds). The relay passes the walk to every page
     (infra/relay/steer.py: start, end, how long ago; the wallet says hello once a day with a signature of its key), and
     every page works out the same way along the paths (paths.js way(), no randomness), so all show it in one place.
     A steered walker stays where it was walked for half an hour, then wanders again. */
  const STEER = { hello: null, cbT: 0, mark: null, mine: 0 }, HOLD = 30 * 60 * 1000, ROUND = v => Math.round(v * 10) / 10;
  const mineW = () => W.list.find(w => w.me) || null;
  function walk(w, go, age) {   // go = { f: [x, y], t: [x, y], p }; age: ms since it was asked
    const N = ways(); if (!N) { w.later = { go, age, at: performance.now() }; return null; }
    const wy = N.way(go.f[0], go.f[1], go.t[0], go.t[1]); if (!wy) return null;
    const t0 = performance.now() - (age || 0);
    w.go = { pts: wy.pts, len: wy.len, v: Math.max(0.06, wy.len / 3000), t0, until: t0 + HOLD, node: wy.node, to: wy.to, key: go.f.join() + "|" + go.t.join() };
    w.route = null; w.wait = 0; w.N = N; w.later = null;
    return w.go;
  }
  function steered(w, N, dt) {   // a walker someone walks: where it is now on its way, the same in every browser
    const g = w.go, now = performance.now(), s = (now - g.t0) * g.v;
    if (s >= g.len) {
      [w.x, w.y] = g.pts[g.pts.length - 1]; w.node = g.node; w.wait = 1e9;   // there: it stands
      if (now > g.until) { w.go = null; w.wait = 2000 + Math.random() * 4000; }
      return;
    }
    let rest = s;
    for (let k = 1; k < g.pts.length; k++) {
      const a = g.pts[k - 1], b = g.pts[k], d = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (rest <= d || k === g.pts.length - 1) { const f = d ? Math.min(1, rest / d) : 1; w.x = a[0] + (b[0] - a[0]) * f; w.y = a[1] + (b[1] - a[1]) * f; if (Math.abs(b[0] - a[0]) > 0.05) w.face = b[0] < a[0] ? -1 : 1; break; }
      rest -= d;
    }
    w.wait = 0; w.ph += dt * 0.012 * 1.6;   // a brisk step
  }
  /* walk your own islander to (x, y), or to a place's door; done() once it is there. false: nothing to walk here */
  function goTo(x, y, place, done) {
    const w = mineW(), N = ways(); if (!w || !N) return false;
    const to = place ? N.doorSpot(place, w.a) : [ROUND(x), ROUND(y)]; if (!to) return false;
    const go = { f: [ROUND(w.x), ROUND(w.y)], t: to, p: place || "-" }, g = walk(w, go, 0); if (!g) return false;
    if (W.sel === w.a) W.sel = null;
    STEER.mine = performance.now(); STEER.mark = { x: g.to[0], y: g.to[1], t0: performance.now() };
    clearTimeout(STEER.cbT);
    if (done) STEER.cbT = setTimeout(done, Math.min(3200, g.len / g.v) + 150);
    tell(w.a, go);
    return true;
  }
  function myKey() {
    const B = window.TauBLS; try { const s = JSON.parse(store.get(WKEY) || "null"); if (B && s && /^[0-9a-f]{64}$/.test(s.sk)) return { sk: B.hexToBytes(s.sk), pk: (s.pk || B.bytesToHex(B.pubOf(B.hexToBytes(s.sk)))).toLowerCase() }; } catch (e) {}
    return null;
  }
  async function tell(a, go) {   // the relay passes it to every page (nothing happens if it is out of reach)
    const game = window.COVE_GAME; if (!game || !game.ask || W.demo) return;
    const k = myKey(); if (!k || k.pk !== a) return;
    const line = ["walker go", a, go.f[0], go.f[1], go.t[0], go.t[1], go.p].join(" ");
    for (let tries = 0; tries < 2; tries++) {
      const day = new Date().toISOString().slice(0, 10);
      if (!STEER.hello || STEER.hello !== game.socket() + day) {
        const sig = window.TauBLS.bytesToHex(window.TauBLS.sign(new TextEncoder().encode("tauhud.com walker " + a + " " + day), k.sk));
        const h = await game.ask(["walker hello", a, day, sig].join(" "), 15000);
        if (!h || h.status !== "ok") return;
        STEER.hello = game.socket() + day;
      }
      const r = await game.ask(line, 8000);
      if (r && r.status === "ok") return;
      if (!(r && r.error && /hello/.test(String(r.error.message || r.error)))) return;
      STEER.hello = null;   // the socket was new: say hello again, once
    }
  }
  /* a walk someone asked for (pushed by the relay, or in GET /walkers for a page opened later) */
  function remote(go) {
    if (!go || typeof go.a !== "string" || !Array.isArray(go.f) || !Array.isArray(go.t) || !(go.age < HOLD)) return;
    const w = W.by.get(go.a); if (!w) return;
    if (w.me && STEER.mine && performance.now() - STEER.mine < HOLD) return;   // this page walks it itself
    if ((w.go && w.go.key === go.f.join() + "|" + go.t.join()) || (w.later && w.later.go.f.join() + "|" + w.later.go.t.join() === go.f.join() + "|" + go.t.join())) return;
    walk(w, go, go.age || 0);
  }
  function demo() {
    const T0 = Math.floor(Date.now() / 1000), hx = n => Array.from({ length: 96 }, (_, i) => "0123456789abcdef"[(n * 7 + i * 13 + (i * n) % 11) % 16]).join("");
    const sets = [["nightowl", "feeder", "lawmaker"], ["winner", "politician", "voter"], ["guardian", "lawmaker", "regular"], ["hacker", "allrounder"], ["catfriend", "hearts", "earlybird"], ["newcomer"], ["veteran", "connector", "bigspender"], ["quiet"], ["busy", "regular"]];
    return { total: sets.length, idni: 1, walkers: [...sets.map((t, i) => ({ a: hx(i + 3), look: i % 3 ? null : i * 37 % LOOKS, idni: false, last: T0 - i * 400, n24: 3 + i, traits: t, home: "" })),
      { a: hx(99), look: null, idni: true, last: T0, n24: 40, traits: ["idni", "busy"], home: "hall" }] };
  }
  async function poll() {
    if (document.hidden && W.ok) return;
    let j = null;
    if (DEMO) j = demo();
    else if (window.TauSim && TauSim.on) j = null;   // the simulation has no real wallets to show
    else try { const r = await fetch(RELAY + "/walkers", { cache: "no-store" }); if (r.ok) j = await r.json(); } catch (e) {}
    if (!j || !Array.isArray(j.walkers)) return;
    W.ok = true;
    if (j.look) { BOX = j.look.box || BOX; BASE = j.look.base || BASE; }
    const me = myPk(), cap = phone() ? 12 : 30;
    const rows = j.walkers.filter(w => w && /^[0-9a-f]{96}$/.test(w.a));
    const mine = rows.find(w => w.a === me), rest = rows.filter(w => w.a !== me && !w.idni), idni = rows.filter(w => w.idni && w.a !== me);
    const pick = [...(mine ? [mine] : []), ...rest.slice(0, cap - (mine ? 1 : 0) - Math.min(3, idni.length)), ...idni.slice(0, 3)].slice(0, cap);
    W.total = (j.total || 0) + (j.idni || 0); W.idni = j.idni || 0; W.all = rows; W.demo = DEMO;
    const keep = new Map();
    for (const d of pick) {
      let w = W.by.get(d.a);
      if (!w) {
        const [x, y] = spot(d.home && SC.places[d.home] ? d.home : placeIds()[Math.floor(Math.random() * placeIds().length)]);
        w = { a: d.a, x, y, tx: x, ty: y, wait: Math.random() * 3000, ph: Math.random() * 6, face: 1, ping: 0, lane: (Math.random() - 0.5) * 5 };
      } else if (d.last > w.d.last) w.ping = performance.now();   // it just sent another transaction
      w.d = d; w.me = d.a === me;
      const code = w.me && myLook() != null ? myLook() : d.look;
      w.lk = look(code, d.a); w.gear = gear(d.traits); w.speed = (d.traits.includes("busy") ? 0.03 : d.traits.includes("veteran") ? 0.011 : 0.016) * (0.85 + Math.random() * 0.3);
      keep.set(d.a, w);
    }
    W.by = keep; W.list = [...keep.values()];
    (Array.isArray(j.go) ? j.go : []).forEach(remote);   // the walks wallets asked for lately (steer.py)
    if (W.sel && !keep.has(W.sel)) W.sel = null;
  }

  /* ---------- walking, drawn with the island's people in depth order ---------- */
  function step(w, dt) {
    if (W.sel === w.a && !w.go) return;   // the one whose card is open stands still (a steered one keeps to its shared way)
    const N = ways();
    if (N && w.later) { const L = w.later; w.later = null; walk(w, L.go, L.age + performance.now() - L.at); }
    if (N && w.go) { steered(w, N, dt); return; }
    if (N && w.N !== N) onWays(w, N); else if (!N && w.N) { w.N = null; w.route = null; }
    if (w.wait > 0) { w.wait -= dt; return; }
    if (N) {
      if (!w.route) { setOff(w, N); if (!w.route) return; }
      let v = w.speed * dt;
      while (v > 0 && w.ri < w.route.length) {
        const [px, py] = w.route[w.ri], dx = px - w.x, dy = py - w.y, d = Math.hypot(dx, dy);
        if (Math.abs(dx) > 0.05) w.face = dx < 0 ? -1 : 1;
        if (d <= v) { w.x = px; w.y = py; v -= d; w.ri++; } else { w.x += dx / d * v; w.y += dy / d * v; v = 0; }
      }
      w.ph += dt * 0.012;
      if (w.ri >= w.route.length) { w.route = null; w.wait = 1800 + Math.random() * 5200; }
      return;
    }
    const dx = w.tx - w.x, dy = w.ty - w.y, d = Math.hypot(dx, dy), v = w.speed * dt;
    if (d < 1.5) {
      w.wait = 1800 + Math.random() * 5200;
      const ids = placeIds(), home = w.d.home && SC.places[w.d.home] ? w.d.home : null;
      const to = home && Math.random() < 0.55 ? home : ids[Math.floor(Math.random() * ids.length)];
      [w.tx, w.ty] = spot(to); return;
    }
    w.x += dx / d * Math.min(v, d); w.y += dy / d * Math.min(v, d); w.face = dx < 0 ? -1 : 1; w.ph += dt * 0.012;
  }
  function boardSpot() { const p = SC.places.pier || SC.places.market || { x: 1000, y: 700 }; return [p.x - 95, p.y - 6]; }
  function drawBoard(g, x, y) {   // the notice board: how many wallets walked the island today
    g.save(); g.translate(x, y); g.strokeStyle = INK; g.lineWidth = 1.4; g.fillStyle = "#8b6a48";
    g.fillRect(-1.6, -22, 3.2, 22); g.strokeRect(-1.6, -22, 3.2, 22);
    g.fillStyle = "#f3e7c9"; g.fillRect(-22, -44, 44, 24); g.strokeRect(-22, -44, 44, 24);
    g.fillStyle = "#39ff8a"; g.shadowColor = "#39ff8a"; g.shadowBlur = 4; g.beginPath(); g.arc(-15, -38.5, 1.8, 0, Math.PI * 2); g.fill(); g.shadowBlur = 0;
    figure(g, -11, -23.5, 0.62, look(0, "00"), { idni: true });
    g.fillStyle = INK; g.font = "800 13px Sora, sans-serif"; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(String(W.total), 6, -31.5);
    g.restore(); W.board = [x - 23, y - 45, 46, 45];
  }
  SC.extra((g, t, dt, items, light) => {
    if (!W.list.length) { W.board = null; return; }
    const now = performance.now();
    if (now > W.nextBubble) { const c = W.list[Math.floor(Math.random() * W.list.length)]; W.bubble = { a: c.a, until: now + 3600 }; W.nextBubble = now + 6500 + Math.random() * 5000; }
    for (const w of W.list) {
      step(w, dt);
      items.push([w.y, () => {
        const moving = W.sel !== w.a && w.wait <= 0, s = 1.25;
        figure(g, w.x, w.y, s, w.lk, { t, ph: w.ph, walk: moving, face: w.face, idni: w.d.idni, gear: w.gear, light });
        const top = w.y - 31 * s;
        g.fillStyle = w.d.idni ? "#b8bcc4" : "#39ff8a"; g.shadowColor = g.fillStyle; g.shadowBlur = 4;   // a real wallet: the green dot (IDNI's: grey)
        g.beginPath(); g.arc(w.x, top, 1.6, 0, Math.PI * 2); g.fill(); g.shadowBlur = 0;
        const pa = (now - w.ping) / 4000;   // it just sent a transaction: a ring goes out
        if (pa >= 0 && pa < 1) { g.strokeStyle = `rgba(57,255,138,${1 - pa})`; g.lineWidth = 1.2; g.beginPath(); g.ellipse(w.x, w.y, 6 + pa * 22, 2 + pa * 7, 0, 0, Math.PI * 2); g.stroke(); }
        if (W.sel === w.a) { g.strokeStyle = "#39ff8a"; g.lineWidth = 1.2; g.beginPath(); g.ellipse(w.x, w.y + 0.5, 8, 2.6, 0, 0, Math.PI * 2); g.stroke(); }
        const label = w.me ? T("you") : W.bubble && W.bubble.a === w.a && now < W.bubble.until ? title(w.d.traits[0]) : null;
        if (label) bubble(g, w.x, top - 4, label, w.me);
      }]);
    }
    if (W.total) { const [bx, by] = boardSpot(); items.push([by, () => drawBoard(g, bx, by)]); }
    const mk = STEER.mark, ma = mk ? (now - mk.t0) / 1400 : 1;   // where your islander is going: a ring, for a moment
    if (ma < 1) items.push([mk.y - 1, () => { g.strokeStyle = `rgba(57,255,138,${(1 - ma) * 0.9})`; g.lineWidth = 1.4; g.beginPath(); g.ellipse(mk.x, mk.y, 5 + ma * 9, 1.8 + ma * 3, 0, 0, Math.PI * 2); g.stroke(); }]);
    else STEER.mark = null;
  }, (x, y, tol) => {
    let best = null, bd = Math.max(5, tol);
    for (const w of W.list) { const d = Math.hypot(x - w.x, (y - (w.y - 13)) * 0.6); if (d < bd + 6) { bd = d - 6; best = "walker:" + w.a; } }
    if (best) return best;
    const b = W.board; if (b && x >= b[0] - tol && x <= b[0] + b[2] + tol && y >= b[1] - tol && y <= b[1] + b[3] + tol) return "walker:board";
    return null;
  });
  function bubble(g, x, y, text, me) {
    g.save(); g.font = "600 6.4px Sora, sans-serif"; g.textAlign = "center";
    const w = g.measureText(text).width + 7;
    g.fillStyle = me ? "rgba(57,255,138,.95)" : "rgba(5,5,6,.82)"; g.strokeStyle = me ? "#0a3" : "rgba(255,255,255,.35)"; g.lineWidth = 0.5;
    g.beginPath(); g.roundRect ? g.roundRect(x - w / 2, y - 9.5, w, 9.5, 3) : g.rect(x - w / 2, y - 9.5, w, 9.5); g.fill(); g.stroke();
    g.fillStyle = me ? "#09090a" : "#fff"; g.fillText(text, x, y - 2.8); g.restore();
  }

  /* ---------- hover and cards ---------- */
  function tip(id) {
    if (id === "walker:board") return F("{n} real wallets on Tau Net testnet were active today", { n: W.total });
    const w = W.by.get(id.slice(7)); if (!w) return "";
    return (w.me ? T("You") : title(w.d.traits[0])) + " · " + (w.d.idni ? T("an IDNI test account on Tau Net testnet, active today") : T("a real wallet on Tau Net testnet, active today"));
  }
  const G = () => window.COVE_GAME;
  const short = a => a.slice(0, 6) + "…" + a.slice(-4);
  const day = s => { try { return new Intl.DateTimeFormat(window.TauI18n && TauI18n.lang === "zh" ? "zh-CN" : window.TauI18n && TauI18n.lang === "ja" ? "ja-JP" : "en-GB", { day: "numeric", month: "short", timeZone: "Europe/Berlin" }).format(new Date(s * 1000)); } catch (e) { return ""; } };
  function portrait(lk, traits, idni, size) {
    const c = document.createElement("canvas"), r = Math.min(2, devicePixelRatio || 1); c.width = c.height = size * r; c.className = "wk-face"; c.style.width = c.style.height = size + "px";
    const g = c.getContext("2d"); g.scale(r, r); figure(g, size / 2 + 2, size - 6, (size - 12) / 30, lk, { gear: gear(traits), idni, t: 0 }); return c;
  }
  function open(id) {
    const game = G(); if (!game) return;
    if (id === "board") return board();
    const w = W.by.get(id) || { a: id, d: (W.all || []).find(x => x.a === id) || { a: id, traits: [], look: null } };
    W.sel = id;
    const lk = w.lk || look(w.d.look, id), el = game.el, size = innerHeight < 520 ? 44 : phone() ? 64 : 92;
    game.card(null, box => {
      box.classList.add("wk-card");
      const who = el("div", { class: "cv-who" }, portrait(lk, w.d.traits, w.d.idni, size),
        el("div", null, el("b", { text: w.me ? T("You") : title(w.d.traits[0]) }), el("small", { translate: "no", text: short(id) })));
      const line = el("p", { class: "cv-line", text: (w.d.traits || []).slice(0, 3).map(title).join(" · ") }), list = el("ul", { class: "cv-help" }, el("li", { text: T("Reading the chain…") }));
      const acts = el("div", { class: "cv-acts" },
        game.btn(T("In the Explorer"), () => window.open("/explorer/?a=" + id, "_blank", "noopener")),
        w.me ? game.btn(T("Choose your look"), () => choose()) : null,
        game.btn(T("Back to the island"), () => game.closeCard(), { go: true }));
      box.append(who, line, list, el("p", { class: "wk-note", text: T("A real wallet on Tau Net testnet. Wallets, not people: one person can hold many, and nothing here knows who.") }), acts);
      card(id, list, acts, game, w);
    });
    watchClose();
  }
  async function card(id, list, acts, game, w) {
    let c = null;
    await new Promise(r => setTimeout(r, 0));   // the card is on the page once its builder returns
    if (W.demo) c = { traits: w.d.traits.map((k, i) => [k, 3 + i * 4]), first: Date.now() / 1000 - 86400 * 9, txs: 41, days: 6, rule: { deploys: 1, parts: ["co"], in_force: true }, idni: w.d.idni };
    else try { const r = await fetch(RELAY + "/walkers/" + id, { cache: "no-store" }); if (r.ok) c = await r.json(); } catch (e) {}
    if (!list.isConnected) return;
    if (!c || c.error) { list.replaceChildren(game.el("li", { text: T("The chain's reading of this wallet is out of reach just now.") })); return; }
    const el = game.el, L = [];
    for (const [k, n] of c.traits || []) if (TRAITS[k]) L.push(el("li", null, el("b", { text: title(k) + ": " }), document.createTextNode(k === "connector" && n >= 64 ? T("Paid 64 or more different wallets.") : F(TRAITS[k][1], { n }))));
    L.push(el("li", { class: "wk-facts", text: F("First seen {d} · {n} transactions · active on {m} days", { d: day(c.first), n: c.txs, m: c.days }) }));
    if (c.rule && c.rule.deploys) L.push(el("li", { text: c.rule.in_force === true ? T("A personal rule is in force for this wallet now.") : c.rule.in_force === false ? T("No personal rule is in force for it now.") : T("It wrote a personal rule.") }));
    list.replaceChildren(...L);
    if (c.rule && c.rule.deploys) acts.prepend(game.btn(T("Its rules"), () => window.open("/account/?a=" + id, "_blank", "noopener")));
  }
  function watchClose() {   // the card was closed (✕, Escape, a click on the island): the walker walks on
    clearInterval(W.watch); W.watch = setInterval(() => { if (!document.querySelector(".cv-card.wk-card")) { W.sel = null; clearInterval(W.watch); } }, 400);
  }
  function board() {
    const game = G(); if (!game) return;
    const el = game.el, rows = (W.all || []).slice(0, phone() ? 8 : 14);
    game.card(null, box => {
      box.classList.add("wk-card");
      box.append(el("h3", { text: F("{n} real wallets walk the island today", { n: W.total }) }),
        el("p", { class: "cv-line", text: T("Every wallet that sent a transaction on Tau Net testnet in the last day walks here by itself. Click one to see what the chain says about it: its rules, Agorzilla, No Memo, the island.") + (W.demo ? " " + T("(made-up walkers for a test)") : "") }),
        el("ul", { class: "cv-help wk-list" }, rows.map(d => el("li", null, el("button", { type: "button", class: "wk-row", onclick: () => open(d.a) }, portrait(look(d.a === myPk() && myLook() != null ? myLook() : d.look, d.a), d.traits, d.idni, 26), el("span", { translate: "no", text: short(d.a) }), el("span", { text: (d.traits || []).slice(0, 2).map(title).join(" · ") }))))),
        el("p", { class: "wk-note", text: T("Our own server's wallets never walk here: the cruise passengers and the island's bot are made up. IDNI's test accounts walk in grey.") }),
        el("div", { class: "cv-acts" }, game.btn(T("Choose your look"), () => choose()), game.btn(T("Back to the island"), () => game.closeCard(), { go: true })));
    });
  }

  /* ---------- choosing your own look: one real transaction ---------- */
  function choose() {
    const game = G(); if (!game) return;
    const el = game.el, pk = myPk(), now = look(myLook() != null ? myLook() : (W.by.get(pk) || {}).d ? W.by.get(pk).d.look : null, pk || "00");
    const pick = { skin: now.skin, hair: now.hair, shirt: now.shirt };
    const code = () => pick.skin * 64 + pick.hair * 8 + pick.shirt;
    game.card(null, box => {
      box.classList.add("wk-card", "wk-pick");
      const pv = el("div", { class: "wk-pv" }), msg = el("p", { class: "wk-note", role: "status" });
      const draw = () => { const lk = look(code(), pk); lk.hc = now.hc; pv.replaceChildren(portrait(lk, (W.by.get(pk) || { d: { traits: [] } }).d.traits, false, phone() ? 64 : 92)); };
      const icon = i => { const c = document.createElement("canvas"), r = Math.min(2, devicePixelRatio || 1); c.width = c.height = 30 * r; c.style.width = c.style.height = "30px"; const g = c.getContext("2d"); g.scale(r, r); const lk = look(pick.skin * 64 + i * 8 + pick.shirt, pk); lk.hc = now.hc; figure(g, 15, 15 + 22 * 1.7, 1.7, lk, {}); return c; };
      const row = (label, n, key, sw) => el("div", { class: "wk-opts", role: "radiogroup", "aria-label": label }, el("small", { text: label }),
        Array.from({ length: n }, (_, i) => el("button", { type: "button", class: "wk-o" + (pick[key] === i ? " on" : ""), role: "radio", "aria-checked": String(pick[key] === i), title: sw ? null : T(HAIRS[i]), "aria-label": sw ? String(i + 1) : T(HAIRS[i]),
          style: sw ? "background:" + sw[i] : null, onclick: e => { pick[key] = i; e.currentTarget.parentNode.querySelectorAll(".wk-o").forEach((b, j) => { b.classList.toggle("on", j === i); b.setAttribute("aria-checked", String(j === i)); }); draw(); } }, sw ? null : icon(i))));
      box.append(el("h3", { text: T("Your islander") }),
        el("div", { class: "wk-pickrow" }, pv, el("div", null, row(T("Skin"), 6, "skin", SKINS), row(T("Hair or hat"), 8, "hair"), row(T("Shirt"), 8, "shirt", SHIRTS))),
        el("p", { class: "cv-line", text: T("Your look is a real transaction from the test wallet in this browser: 1,200 to 1,583 test AGRS (no value) to the hearts box, which has no key. No account, no name; public on the chain, and a new choice replaces it. What your islander carries, it earns on the chain.") }),
        msg,
        el("div", { class: "cv-acts" }, game.btn(T("Sign and send"), e => send(code(), msg, e.currentTarget), { go: true }), game.btn(T("Back to the island"), () => game.closeCard())));
      draw();
    });
  }
  const canon = o => Array.isArray(o) ? "[" + o.map(canon).join(",") + "]" : o === null || typeof o !== "object" ? JSON.stringify(o).replace(/[\u007f-￿]/g, c => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0")) : "{" + Object.keys(o).sort().map(k => JSON.stringify(k) + ":" + canon(o[k])).join(",") + "}";
  function socket() {
    return new Promise(res => {
      let ws; try { ws = new WebSocket(WS); } catch (e) { return res(null); }
      const wait = new Map();
      ws.onmessage = ev => { let m; try { m = JSON.parse(String(ev.data)); } catch (e) { return; } const q = wait.get(m.command); if (q && q.length) q.shift()(m); };
      ws.onerror = ws.onclose = () => res(null);
      ws.onopen = () => {
        ws.send("hello version=1");
        const ask = (cmd, ms = 12000) => new Promise(r => { const c = cmd.split(" ")[0]; if (!wait.has(c)) wait.set(c, []); const q = wait.get(c); q.push(r); try { ws.send(cmd); } catch (e) { r(null); } setTimeout(() => { const i = q.indexOf(r); if (i >= 0) { q.splice(i, 1); r(null); } }, ms); });
        setTimeout(() => res({ ask, close: () => { try { ws.close(); } catch (e) {} } }), 150);
      };
    });
  }
  async function send(code, msg, b) {
    const B = window.TauBLS; let k = null;
    try { const s = JSON.parse(store.get(WKEY) || "null"); if (B && s && /^[0-9a-f]{64}$/.test(s.sk)) k = { sk: B.hexToBytes(s.sk), pk: s.pk || B.bytesToHex(B.pubOf(B.hexToBytes(s.sk))) }; } catch (e) {}
    if (!k) { msg.textContent = T("This browser has no test wallet yet: start a campaign on the island or open tauhud.com/wallet/ first."); return; }
    if (b) b.disabled = true; msg.textContent = T("Signing…");
    const c = await socket();
    try {
      if (!c) throw new Error("relay");
      const gv = await c.ask("getgovernance"), m = /o9\[t\]:bv\[24\]\s*=\s*\{\s*#x([0-9a-fA-F]+)/.exec((gv && gv.data && gv.data.consensus_rules) || ""), fee = m ? parseInt(m[1], 16) : 10;
      await c.ask("via islander");
      const st = await c.ask("getsequence " + k.pk); if (!st || st.status !== "ok") throw new Error("seq");
      if (st.data && st.data.balance != null && Number(st.data.balance) < BASE + LOOKS + fee * 5) { msg.textContent = T("Your test wallet needs a few more test AGRS first: the wallet page gets them from the faucet."); return; }
      const tx = { tx_type: "user_tx", sender_pubkey: k.pk, sequence_number: st.data.sequence_number || 0, expiration_time: Math.floor(Date.now() / 1000) + 600,
        expire_at_height: (st.data.tip_height || 0) + 1000, fee_limit: String(fee * 5), operations: { "1": [[k.pk, BOX, String(BASE + code)]] } };
      const d = { sender_pubkey: tx.sender_pubkey, sequence_number: tx.sequence_number, expiration_time: tx.expiration_time, fee_limit: tx.fee_limit, tx_type: tx.tx_type, expire_at_height: tx.expire_at_height, operations: tx.operations };
      tx.signature = B.bytesToHex(B.sign(new TextEncoder().encode(canon(d)), k.sk));
      const r = await c.ask("sendtx " + JSON.stringify(tx), 20000);
      if (!(r && r.status === "ok" && !(r.data && r.data.ok === false))) throw new Error("refused");
      store.set(MINE, String(code));
      const w = W.by.get(k.pk.toLowerCase()); if (w) { w.lk = look(code, w.a); w.ping = performance.now(); }
      msg.textContent = T("Sent. Your islander wears it now; the island shows it to everyone once a block holds the transaction.");
    } catch (e) { msg.textContent = T("The testnet did not take it just now. Try again in a minute."); }
    finally { if (c) c.close(); if (b) b.disabled = false; }
  }

  window.ISLE_WALKERS = { figure, look, gear, tip, open, board, choose, traits: TRAITS, goTo, remote, mine: () => !!(mineW() && ways()), at: a => { const w = W.by.get(a); return w ? [w.x, w.y] : null; } };
  poll(); setInterval(poll, 60000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) poll(); });
  if (Q.get("islander") === "1") { const go = () => (G() ? setTimeout(choose, 600) : setTimeout(go, 500)); go(); }
})();

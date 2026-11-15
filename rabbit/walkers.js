/* The wallets that walk on White Rabbit Key: every wallet that sent a real transaction on Tau Net testnet in the last day
   walks on the island as a small islander (relay infra/relay/walkers.py, GET node.tauhud.com/walkers). Hover says what
   it is, a click opens a card with what the chain tells about it, read as a few plain traits (a night owl, Agorzilla's
   friend, writes its own rules …), and the islander carries the matching thing: a lantern, a banana, a scroll.

   Only wallets, never people: nothing here knows who holds a key, and one person can hold many. Our own server's
   wallets never walk (the island bot, the cruise passengers, No Memo's purse, the hack of the week, the showcase
   wallets); IDNI's genesis accounts walk in grey. Nobody plays a walker: they walk by themselves, to the places
   that fit what their wallet does (the Council Hall for the island's politicians, the lighthouse for rule writers …).

   The look (islander.js): seventeen parts, from the wallet's key until it chooses them in the islander studio
   (studio.js) with one real transaction to the hearts box, which has no key behind it. Each islander has a name made
   from its key's syllables (never on the chain). The islanders live with the chain: one waves when its wallet's
   transaction lands in a block, shakes its head when its own rule refused a payment, and they all sit down while
   the chain pauses (no new block for five minutes).
   ?islander=1 opens the studio at once. Test params: ?walkers=demo shows made-up walkers (marked as such).
   Your own islander walks where you click (goTo), and every page sees it walk (remote, relay steer.py).
   What an islander's wallet last wrote in the troll box (The Coconut Wire, assets/chat.js) pops up over its head now and
   then (said, unsaid; relay chat.py keeps which wallet said it, in memory only).
   window.ISLE_WALKERS = { figure, look, open, board, choose, goTo, remote, mine, find, me, cardOf, traits, said, unsaid } */
(() => {
  "use strict";
  const SC = window.COVE_SCENE; if (!SC || !SC.extra) return;
  const RELAY = "https://node.tauhud.com", WS = "wss://node.tauhud.com", WKEY = "tauhud-wallet-key", MINE = "tauhud-islander-look", MINE2 = "tauhud-islander-parts";
  const IS = window.ISLANDER; if (!IS) return;
  const T = s => (window.TauI18n ? TauI18n.t(s) : s);
  const F = (s, v) => T(s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m)));   // filled in first: the dictionaries match the whole sentence
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const Q = new URLSearchParams(location.search), DEMO = Q.get("walkers") === "demo";
  const phone = () => innerWidth < 760;
  const INK = "#22303a";

  /* ---------- the look: the islander's parts (islander.js); an older choice (1,200 + code) still counts ---------- */
  const LOOKS = 384;
  let BASE = 1200, BOX = "a43259757c7e5a26dae5dde9ce22ecafe2d7570c93e71ccf65756691d57e7a512e7fdfbfc78e9ce3bfd608b71e286a0b";
  const look = (code, a) => IS.parts(a, IS.fromLook(code));
  const partsOf = d => (Array.isArray(d.pt) && d.pt.length === IS.N.length ? d.pt.map(Number) : look(d.look, d.a));
  /* what this browser chose last, until the relay has read it from a block (half an hour at most) */
  const pending = () => { try { const v = JSON.parse(store.get(MINE2) || "null"); return v && Array.isArray(v.p) && Date.now() - v.at < 1800000 ? v : null; } catch (e) { return null; } };
  const WALK_SPEED = [1, 1.05, 1.12, 0.78, 0.95];

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

  /* ---------- drawing an islander: feet at (x, y), s = scale (1: about 28 world units tall); what it carries on top ---------- */
  function figure(g, x, y, s, lk, o = {}) {
    const at = IS.figure(g, x, y, s, lk, o);
    if (o.gear && o.gear.hand && !o.wave) { g.save(); g.translate(x, y); g.scale(s * (o.face || 1), s); hand(g, o.gear.hand, at.hx, at.hy, o.t || 0, o.light || 0); g.restore(); }
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
  const W = { list: [], by: new Map(), total: 0, idni: 0, at: 0, sel: null, bubble: null, nextBubble: 0, board: null, ok: false, said: new Map() };
  const myPk = () => { try { const k = JSON.parse(store.get(WKEY) || "null"); return k && k.pk ? String(k.pk).toLowerCase() : null; } catch (e) { return null; } };
  const myLook = () => { const v = parseInt(store.get(MINE) || "", 10); return v >= 0 && v < LOOKS ? v : null; };
  const myParts = (d, pk) => { const q = pending(); if (q && q.pk === pk) return q.p; return d ? partsOf(d) : myLook() != null ? look(myLook(), pk) : IS.parts(pk); };
  const placeIds = () => Object.keys(SC.places).filter(id => SC.places[id] && Number.isFinite(SC.places[id].x));
  const NAMES = new Map(), nameOf = a => { if (!NAMES.has(a)) NAMES.set(a, IS.name(a)); return NAMES.get(a); };
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
  /* ---------- what an islander last said in the troll box (The Coconut Wire) ----------
     Only the latest message that is still in the troll box (a hidden or day-old one goes), and not all the time: it pops
     up for a few seconds when it is new, then now and then for a moment. When is worked out from the clock and the
     wallet, so every page shows it at the same moments. */
  const SAY = { every: 80, show: 7, fresh: 10000 };
  function said(m, old, pushed) {   // pushed: it was just written; else from the list (it pops at once only if new)
    if (!m || typeof m.w !== "string" || typeof m.text !== "string" || !Number.isFinite(m.id)) return;
    if (old && old.id > m.id) { W.said.set(m.w, old); return; }   // a newer one came by push already
    const fresh = pushed || Date.now() / 1000 - (m.ts || 0) < SAY.fresh / 1000;
    W.said.set(m.w, { id: m.id, ts: m.ts || 0, text: m.text, got: old && old.id === m.id ? old.got : fresh ? performance.now() : 0 });
  }
  function unsaid(id) { for (const [a, m] of W.said) if (m.id === Number(id)) W.said.delete(a); }
  function saying(a, now) {   // how much of the bubble shows now (0 = none)
    const m = W.said.get(a); if (!m) return 0;
    if (Date.now() / 1000 - m.ts > 86400) { W.said.delete(a); return 0; }
    const ramp = t => Math.min(1, t / 400);
    if (m.got && now - m.got < SAY.fresh) return Math.min(ramp(now - m.got), ramp(SAY.fresh - (now - m.got)));
    let h = 7; for (const ch of a.slice(0, 16) + m.id) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    const t = (Date.now() + (h % (SAY.every * 1000))) % (SAY.every * 1000);
    return t < SAY.show * 1000 ? Math.min(ramp(t), ramp(SAY.show * 1000 - t)) : 0;
  }
  function lines(g, text, max) {   // at most two lines, the rest cut with …
    const words = text.split(/\s+/), out = [""];
    for (const wd of words) {
      const tryL = out[out.length - 1] ? out[out.length - 1] + " " + wd : wd;
      if (g.measureText(tryL).width <= max) { out[out.length - 1] = tryL; continue; }
      if (out.length === 2) { out[1] += " …"; break; }
      out.push(wd);
    }
    return out.map(l => { if (g.measureText(l).width <= max) return l; let c = l; while (c.length > 1 && g.measureText(c + "…").width > max) c = c.slice(0, -1); return c + "…"; });
  }
  function speech(g, x, y, text, alpha) {   // a speech bubble whose tail points down to (x, y)
    const FS = phone() ? 11 : 9, LH = FS * 1.25;
    g.save(); g.globalAlpha = alpha; g.font = `600 ${FS}px Sora, sans-serif`; g.textAlign = "center"; g.textBaseline = "alphabetic";
    const ls = lines(g, text, FS * 14), w = Math.max(...ls.map(l => g.measureText(l).width)) + FS * 1.4, h = ls.length * LH + FS * 0.7;
    const bx = x - w / 2, by = y - 4.5 - h;
    g.fillStyle = "rgba(244,241,234,.97)"; g.strokeStyle = INK; g.lineWidth = 0.8;
    g.beginPath(); g.roundRect ? g.roundRect(bx, by, w, h, FS * 0.5) : g.rect(bx, by, w, h); g.fill(); g.stroke();
    g.beginPath(); g.moveTo(x - 3.5, by + h - 0.4); g.lineTo(x, y); g.lineTo(x + 3.5, by + h - 0.4); g.closePath(); g.fill();
    g.beginPath(); g.moveTo(x - 3.5, by + h); g.lineTo(x, y); g.lineTo(x + 3.5, by + h); g.stroke();
    g.fillStyle = INK; ls.forEach((l, i) => g.fillText(l, x, by + FS * 0.35 + LH * (i + 0.8)));
    g.restore();
  }
  function demo() {
    const T0 = Math.floor(Date.now() / 1000), hx = n => Array.from({ length: 96 }, (_, i) => "0123456789abcdef"[(n * 7 + i * 13 + (i * n) % 11) % 16]).join("");
    const sets = [["nightowl", "feeder", "lawmaker"], ["winner", "politician", "voter"], ["guardian", "lawmaker", "regular"], ["hacker", "allrounder"], ["catfriend", "hearts", "earlybird"], ["newcomer"], ["veteran", "connector", "bigspender"], ["quiet"], ["busy", "regular"]];
    return { total: sets.length, idni: 1, walkers: [...sets.map((t, i) => ({ a: hx(i + 3), look: i % 3 ? null : i * 37 % LOOKS, idni: false, last: T0 - i * 400, n24: 3 + i, traits: t, home: "" })),
      { a: hx(99), look: null, idni: true, last: T0, n24: 40, traits: ["idni", "busy"], home: "hall" }].map((w, i) => ({ ...w, first: i === 1 || undefined, held: i === 2 ? T0 - 120 : undefined })),
      chain: { tip: Q.get("chain") === "paused" ? T0 - 900 : T0 - 20, height: 4200, restart: Q.get("chain") === "restart" ? T0 - 600 : 0 },
      said: [{ id: 1, ts: T0 - 5, w: hx(3), text: "Anyone else feeding Agorzilla tonight?" }, { id: 2, ts: T0 - 900, w: hx(4), text: "Just won my second election on this island, the hall was packed and the governor looked nervous" },
        { id: 3, ts: T0 - 60, w: hx(6), text: "gm" }] };
  }
  async function poll() {
    if (document.hidden && W.ok) return;
    let j = null;
    if (DEMO) j = demo();
    else if (window.TauSim && TauSim.on) j = null;   // the simulation has no real wallets to show
    else try { const r = await fetch(RELAY + "/walkers", { cache: "no-store" }); if (r.ok) j = await r.json(); } catch (e) {}
    if (!j || !Array.isArray(j.walkers)) return;
    hudLoad();
    W.ok = true;
    if (j.look) { BOX = j.look.box || BOX; BASE = j.look.base || BASE; }
    W.chain = j.chain || null; W.polled = Date.now() / 1000;
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
      w.lk = w.me ? myParts(d, me) : partsOf(d); w.gear = gear(d.traits); w.name = nameOf(d.a);
      w.speed = (d.traits.includes("busy") ? 0.03 : d.traits.includes("veteran") ? 0.011 : 0.016) * (0.85 + Math.random() * 0.3) * WALK_SPEED[w.lk[7]];
      keep.set(d.a, w);
    }
    W.by = keep; W.list = [...keep.values()];
    (Array.isArray(j.go) ? j.go : []).forEach(remote);   // the walks wallets asked for lately (steer.py)
    if (Array.isArray(j.said)) {   // what their islanders last said in the troll box: only messages that are still there
      const was = W.said; W.said = new Map();
      j.said.forEach(m => said(m, was.get(m && m.w), false));
    }
    if (W.sel && !keep.has(W.sel)) W.sel = null;
  }

  /* ---------- walking, drawn with the island's people in depth order ---------- */
  /* the chain pauses (no new block for five minutes): everyone sits down; it started over in the last half hour: the board says so */
  const paused = () => { const c = W.chain; return !!(c && c.tip && (W.polled || Date.now() / 1000) - c.tip > 300); };
  const restarted = () => { const c = W.chain; return !!(c && c.restart && Date.now() / 1000 - c.restart < 1800); };
  const heldNow = w => w.d.held && Date.now() / 1000 - w.d.held < 900;
  function step(w, dt) {
    if ((W.sel === w.a && !w.go) || paused()) return;   // the one whose card is open stands still (a steered one keeps to its shared way); everyone sits while the chain rests
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
    IS.figure(g, -11, -23.5, 0.62, IS.parts("00"), { idni: true });
    g.fillStyle = INK; g.font = "800 13px Sora, sans-serif"; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(String(W.total), 6, -31.5);
    if (paused() || restarted()) {   // amber, never red: a pause or a fresh start is the testnet's normal life
      g.fillStyle = "#ffb13b"; g.shadowColor = "#ffb13b"; g.shadowBlur = 5; g.beginPath(); g.arc(17, -41, 3.2, 0, Math.PI * 2); g.fill(); g.shadowBlur = 0;
      g.fillStyle = "#09090a"; g.font = "800 5px Sora, sans-serif"; g.fillText("!", 17, -40.8);
    }
    g.restore(); W.board = [x - 23, y - 45, 46, 45];
  }
  SC.extra((g, t, dt, items, light) => {
    if (!W.list.length) { W.board = null; return; }
    const now = performance.now();
    if (now > W.nextBubble) { const held = W.list.filter(heldNow), c = held.length && Math.random() < 0.6 ? held[Math.floor(Math.random() * held.length)] : W.list[Math.floor(Math.random() * W.list.length)]; W.bubble = { a: c.a, until: now + 3600 }; W.nextBubble = now + 6500 + Math.random() * 5000; }
    for (const w of W.list) {
      step(w, dt);
      const talk = W.said.size ? saying(w.a, now) : 0;   // what it last said in the troll box, now and then
      items.push([w.y, () => {
        const sit = paused(), moving = W.sel !== w.a && w.wait <= 0 && !sit, s = 1.25, waving = now - w.ping < 3500 || (W.find && W.find.a === w.a && now < W.find.until);
        figure(g, w.x, w.y, s, w.lk, { t, ph: w.ph, walk: moving, face: w.face, idni: w.d.idni, gear: w.gear, light, wave: waving, shake: heldNow(w) && W.bubble && W.bubble.a === w.a, sit });
        const top = w.y - 31 * s;
        g.fillStyle = w.d.idni ? "#b8bcc4" : "#39ff8a"; g.shadowColor = g.fillStyle; g.shadowBlur = 4;   // a real wallet: the green dot (IDNI's: grey)
        g.beginPath(); g.arc(w.x, top, 1.6, 0, Math.PI * 2); g.fill(); g.shadowBlur = 0;
        const pa = (now - w.ping) / 4000;   // it just sent a transaction: a ring goes out
        if (pa >= 0 && pa < 1) { g.strokeStyle = `rgba(57,255,138,${1 - pa})`; g.lineWidth = 1.2; g.beginPath(); g.ellipse(w.x, w.y, 6 + pa * 22, 2 + pa * 7, 0, 0, Math.PI * 2); g.stroke(); }
        if (W.sel === w.a) { g.strokeStyle = "#39ff8a"; g.lineWidth = 1.2; g.beginPath(); g.ellipse(w.x, w.y + 0.5, 8, 2.6, 0, 0, Math.PI * 2); g.stroke(); }
        if (W.find && W.find.a === w.a && now < W.find.until) {   // "find me": a beacon over your islander
          const k = (now % 1200) / 1200; g.strokeStyle = `rgba(57,255,138,${1 - k})`; g.lineWidth = 1.6; g.beginPath(); g.ellipse(w.x, w.y, 8 + k * 30, 2.6 + k * 10, 0, 0, Math.PI * 2); g.stroke();
          g.fillStyle = "#39ff8a"; g.beginPath(); const ay = top - 16 - Math.abs(Math.sin(now * 0.006)) * 5; g.moveTo(w.x - 4, ay - 6); g.lineTo(w.x + 4, ay - 6); g.lineTo(w.x, ay); g.fill();
        }
        const mine = W.bubble && W.bubble.a === w.a && now < W.bubble.until;
        const label = w.me ? (OF() && OF().count() ? "✉ " : "") + T("you") + " · " + w.name : mine && !talk ? (heldNow(w) ? T("My rule said no") : sit ? T("The chain is resting") : w.name + " · " + title(w.d.traits[0])) : null;
        if (label) bubble(g, w.x, top - 4, label, w.me);
      }]);
      if (talk > 0) items.push([1e6 + w.y, () => speech(g, w.x, w.y - 31 * 1.25 - (w.me ? 15 : 4), W.said.get(w.a).text, talk)]);   // over everything
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
  /* how a wallet relates to Tau HUD, from its traits: which of our apps it uses (a wallet can also use Tau Net elsewhere) */
  const APPS = [["No Memo", "/nomemo/", ["hacker"]], ["Agorzilla", "https://agorzilla.com", ["feeder", "voter"]], ["White Rabbit Key", "/rabbit/", ["politician", "winner"]],
    ["Déjà's café", "https://agorzilla.com/cat/", ["catfriend"]], ["its own rule", "/rules/", ["lawmaker", "guardian", "vault", "picky", "capped", "frozen"]], ["hearts on Tau HUD", "/hearts/", ["hearts"]]];
  const appsOf = traits => APPS.filter(a => a[2].some(k => (traits || []).includes(k)));
  /* whether a wallet sent through Tau HUD's own wallet, from our relay's record of what it sent (GET /wallets/tags "apps",
     walletdays.py). A plain payment on the chain does not say which wallet app signed it, so the blocks alone cannot tell */
  const HUD = { map: new Map(), at: 0 };
  async function hudLoad() {
    if (DEMO || Date.now() - HUD.at < 300000) return;
    HUD.at = Date.now();
    try { const r = await fetch(RELAY + "/wallets/tags", { cache: "no-store" }); if (r.ok) { const j = await r.json(); if (j && j.apps && typeof j.apps === "object") HUD.map = new Map(Object.entries(j.apps)); } } catch (e) {}
  }
  const hudOf = a => { const e = HUD.map.get(a); return e && (e.b === "tauhud" || (e.u || []).includes("tauhud")) ? e : null; };
  function kind(d) {   // one line: who this wallet is on Tau HUD
    if (d.idni) return T("An IDNI test account: one of the accounts the testnet started with.");
    const a = appsOf(d.traits).filter(x => x[1] !== "/rules/"), rule = appsOf(d.traits).some(x => x[1] === "/rules/");
    if (!a.length && !rule) return hudOf(d.a) ? T("Sends payments on Tau Net testnet through Tau HUD's wallet.") : T("Sends plain payments on Tau Net testnet. A plain payment does not show which wallet app signed it.");
    if (!a.length) return T("On Tau HUD it wrote its own rule for its wallet.");
    return F("On Tau HUD it uses {x}.", { x: a.map(x => T(x[0])).join(", ") }) + (rule ? " " + T("It also wrote its own rule for its wallet.") : "");
  }
  const ago = ts => { const m = Math.max(1, Math.round((Date.now() / 1000 - ts) / 60)); return m < 60 ? F("{n} min ago", { n: m }) : F("{n} h ago", { n: Math.round(m / 60) }); };
  function tip(id) {
    if (id === "walker:board") return F("{n} real wallets on Tau Net testnet were active today", { n: W.total }) + (paused() ? " · " + T("the chain is resting: no new block for a few minutes") : restarted() ? " · " + T("the testnet started over in the last half hour") : "");
    const w = W.by.get(id.slice(7)); if (!w) return "";
    const ap = appsOf(w.d.traits), a = ap.filter(x => x[1] !== "/rules/").map(x => T(x[0])), rule = ap.length > a.length;
    const what = [a.length ? F("uses {x}", { x: a.join(", ") }) : "", rule ? T("has its own rule") : ""].filter(Boolean).join(" · ");
    return (w.me ? T("You") + " · " + w.name : w.name + " · " + title(w.d.traits[0])) + " · " + (w.d.idni ? T("IDNI test account") : what || (hudOf(w.a) ? T("pays through Tau HUD's wallet") : T("plain payments so far"))) + " · " + F("last transaction {x}", { x: ago(w.d.last) }) + " · " + T("click for its story");
  }
  const G = () => window.COVE_GAME, OF = () => window.ISLE_OFFERS;   // offers.js: rules proposed between wallets
  const short = a => a.slice(0, 6) + "…" + a.slice(-4);
  const day = s => { try { return new Intl.DateTimeFormat(window.TauI18n && TauI18n.lang === "zh" ? "zh-CN" : window.TauI18n && TauI18n.lang === "ja" ? "ja-JP" : "en-GB", { day: "numeric", month: "short", timeZone: "Europe/Berlin" }).format(new Date(s * 1000)); } catch (e) { return ""; } };
  /* a portrait: the face (islander.js bust) from 44 px up, the whole small figure below that */
  function portrait(lk, traits, idni, size) {
    const c = document.createElement("canvas"), r = Math.min(2, devicePixelRatio || 1); c.width = c.height = size * r; c.className = "wk-face"; c.style.width = c.style.height = size + "px";
    const g = c.getContext("2d"); g.scale(r, r);
    if (size >= 44) IS.bust(g, 0, 0, size, lk, { idni }); else figure(g, size / 2 + 2, size - 6, (size - 12) / 30, lk, { gear: gear(traits), idni, t: 0 });
    return c;
  }
  function open(id) {
    const game = G(); if (!game) return;
    if (id === "board") return board();
    const w = W.by.get(id) || { a: id, name: nameOf(id), d: (W.all || []).find(x => x.a === id) || { a: id, traits: [], look: null } };
    W.sel = id;
    const lk = w.lk || partsOf(w.d), el = game.el, size = innerHeight < 520 ? 52 : phone() ? 72 : 104, me = w.me || id === myPk();
    game.card(null, box => {
      box.classList.add("wk-card");
      const who = el("div", { class: "cv-who" }, portrait(lk, w.d.traits, w.d.idni, size),
        el("div", null, el("b", { text: (me ? T("You") + " · " : "") + (w.name || nameOf(id)) }), el("small", { text: (w.d.traits || []).length ? title(w.d.traits[0]) : "" }), el("small", { translate: "no", text: short(id) })));
      const line = el("p", { class: "cv-line", text: kind(w.d) + (w.d.last ? " " + F("Last transaction {x}.", { x: ago(w.d.last) }) : "") }), list = el("ul", { class: "cv-help" }, el("li", { text: T("Reading the chain…") }));
      const of = OF(), theirs = of && !me ? of.from(id).length : 0, mineN = of && me ? of.count() : 0;
      const acts = el("div", { class: "cv-acts" },
        of && !me && !w.d.idni && of.can(id) ? game.btn(T("Propose a rule"), () => of.propose(id), { go: true }) : null,
        theirs ? game.btn(theirs === 1 ? T("Read the rule it proposed to you") : F("Read the {n} rules it proposed to you", { n: theirs }), () => of.inbox()) : null,
        me && of ? game.btn(mineN ? F("Rules proposed to you ({n})", { n: mineN }) : T("Rules proposed to you"), () => of.inbox()) : null,
        game.btn(T("In the Explorer"), () => window.open("/explorer/?a=" + id, "_blank", "noopener")),
        me ? game.btn(T("Islander studio"), () => choose()) : null,
        game.btn(T("Back to the island"), () => game.closeCard(), { go: true }));
      box.append(who, line, list, el("p", { class: "wk-note", text: T("A real wallet on Tau Net testnet. Wallets, not people: one person can hold many, and nothing here knows who. The name comes from the key's letters; it is not on the chain.") }), acts);
      card(id, list, acts, game, w);
    });
    watchClose();
  }
  /* GET /walkers/<address>, kept a minute (the studio and the pass card read it too) */
  const CARDS = new Map();
  async function cardOf(id, fresh) {
    const k = CARDS.get(id); if (k && !fresh && Date.now() - k.at < 60000) return k.c;
    let c = null;
    const d = (W.all || []).find(x => x.a === id);
    if (W.demo) c = d ? { traits: d.traits.map((k, i) => [k, 3 + i * 4]), first: Date.now() / 1000 - 86400 * 9, txs: 41, days: 6, idni: d.idni, ...((t => ({ meals: t("feeder") ? 7 : 0, votes: t("voter") ? 3 : 0, deja: t("catfriend") ? 4 : 0, hearts: t("hearts") ? 5 : 0, rabbit: { moves: t("politician") ? 12 : 0, played: t("politician") ? 2 : 0, won: t("winner") ? 1 : 0 }, nomemo: { chapters: t("hacker") ? 3 : 0 }, rule: t("lawmaker") || t("guardian") ? { deploys: 2, parts: t("guardian") ? ["co", "cap"] : ["only"], in_force: true } : { deploys: 0 } }))(k => d.traits.includes(k))),
      pt: partsOf(d), chosen: null, earned: d.traits.map(t => IS.EARN.indexOf(t)).filter(i => i > 0), face: { first: d.first ? id : null, mine: !!d.first } } : null;
    else try { const r = await fetch(RELAY + "/walkers/" + id, { cache: "no-store" }); if (r.ok) c = await r.json(); } catch (e) {}
    if (c && !c.error) CARDS.set(id, { c, at: Date.now() });
    return c && !c.error ? c : null;
  }
  async function card(id, list, acts, game, w) {
    await new Promise(r => setTimeout(r, 0));   // the card is on the page once its builder returns
    const c = await cardOf(id);
    if (!list.isConnected) return;
    if (!c) { list.replaceChildren(game.el("li", { text: T("The chain's reading of this wallet is out of reach just now.") })); return; }
    const el = game.el, L = [], rb = c.rabbit || {}, nm = c.nomemo || {};
    /* what it did on Tau HUD, app by app, from its own transactions on the chain */
    const did = (app, url, text) => L.push(el("li", null, el("b", null, el("a", { href: url, target: url.startsWith("http") ? "_blank" : null, rel: "noopener", text: T(app) }), document.createTextNode(": ")), document.createTextNode(text)));
    if (nm.chapters) did("No Memo", "/nomemo/", F("cracked {n} chapters of the hacker game, with real transactions.", { n: nm.chapters }));
    if (c.meals || c.votes || c.asks) did("Agorzilla", "https://agorzilla.com", [c.meals ? F("fed it {n} times", { n: c.meals }) : "", c.votes ? F("voted {n} times", { n: c.votes }) : "", c.asks ? F("asked it {n} questions", { n: c.asks }) : ""].filter(Boolean).join(", ") + ".");
    if (rb.moves || rb.played || rb.lines || rb.ballots || rb.won) did("White Rabbit Key", "/rabbit/", [rb.played ? F("played {n} games", { n: rb.played }) : "", rb.moves ? F("{n} moves", { n: rb.moves }) : "", rb.won ? F("won {n} elections", { n: rb.won }) : "", rb.ballots ? F("{n} ballots", { n: rb.ballots }) : ""].filter(Boolean).join(", ") + ".");
    if (c.deja) did("Déjà's café", "https://agorzilla.com/cat/", F("put food in the cat's bowl {n} times.", { n: c.deja }));
    if (c.hearts) did("hearts on Tau HUD", "/hearts/", F("gave {n} hearts to parts of the site.", { n: c.hearts }));
    if (c.rule && c.rule.deploys) {
      const words = { co: T("a second signature for bigger payments"), only: T("pays only addresses it trusts"), cap: T("a cap on every payment"), from: T("money locked until a date"), balance: T("keeps a floor under its balance"), freeze: T("stops every payment") };
      const parts = (c.rule.parts || []).map(p => words[p]).filter(Boolean);
      did("Its own rule", "/account/?a=" + id, (parts.length ? parts.join(", ") + "." + " " : "") + (c.rule.in_force === true ? T("In force now.") : c.rule.in_force === false ? T("Not in force now.") : F("Written {n} times.", { n: c.rule.deploys })));
    }
    const hud = !c.idni && hudOf(id);
    if (hud) did("Tau HUD's wallet", "/wallet/", hud.b === "tauhud" && hud.d ? F("sent through tauhud.com's wallet; its first transaction we know of came from there, on {x}.", { x: day(Date.parse(hud.d + "T12:00:00Z") / 1000) }) : T("sent through tauhud.com's wallet."));
    if (!L.length && !c.idni) L.push(el("li", { text: T("Plain payments so far. A plain payment does not show which wallet app signed it, so it may come from Tau HUD's wallet or from anywhere else; our server has no record of it sending through ours.") }));
    for (const [k, n] of c.traits || []) if (TRAITS[k] && !APPS.some(a => a[2].includes(k))) L.push(el("li", null, el("b", { text: title(k) + ": " }), document.createTextNode(k === "connector" && n >= 64 ? T("Paid 64 or more different wallets.") : F(TRAITS[k][1], { n }))));
    L.push(el("li", { class: "wk-facts", text: F("First seen {d} · {n} transactions · active on {m} days", { d: day(c.first), n: c.txs, m: c.days }) }));
    if (c.face && c.face.mine) L.push(el("li", { class: "wk-first", text: T("First to wear this face: no wallet chose it on the chain before.") }));
    else if (c.face && c.face.first && c.face.first !== id) L.push(el("li", { class: "wk-facts", text: F("Its face was first chosen by {x}.", { x: nameOf(c.face.first) }) }));
    if (heldNow(w)) L.push(el("li", { text: T("Its own rule refused one of its payments a few minutes ago: the rule did its job.") }));
    list.replaceChildren(...L);
    if (c.rule && c.rule.deploys) acts.prepend(game.btn(T("Its rules"), () => window.open("/account/?a=" + id, "_blank", "noopener")));
  }
  function watchClose() {   // the card was closed (✕, Escape, a click on the island): the walker walks on
    clearInterval(W.watch); W.watch = setInterval(() => { if (!document.querySelector(".cv-card.wk-card")) { W.sel = null; clearInterval(W.watch); } }, 400);
  }
  function board() {
    const game = G(); if (!game) return;
    const el = game.el, rows = (W.all || []).slice(0, phone() ? 8 : 14), me = myPk();
    game.card(null, box => {
      box.classList.add("wk-card");
      box.append(el("h3", { text: F("{n} real wallets walk the island today", { n: W.total }) }),
        el("p", { class: "cv-line", text: T("Every wallet that sent a transaction on Tau Net testnet in the last day walks here by itself. Click one to see what the chain says about it: its rules, Agorzilla, No Memo, the island.") + (W.demo ? " " + T("(made-up walkers for a test)") : "") }),
        paused() ? el("p", { class: "wk-amber", text: T("The chain is resting: no new block for a few minutes, so the islanders sat down. They get up with the next block.") })
          : restarted() ? el("p", { class: "wk-amber", text: T("The testnet started over in the last half hour. The islanders keep their looks: the relay remembers what the old chain said.") }) : null,
        el("ul", { class: "cv-help wk-list" }, rows.map(d => el("li", null, el("button", { type: "button", class: "wk-row", onclick: () => open(d.a) }, portrait(d.a === me ? myParts(d, me) : partsOf(d), d.traits, d.idni, 26), el("span", { translate: "no", text: nameOf(d.a) }), el("span", { text: (d.traits || []).slice(0, 2).map(title).join(" · ") }))))),
        el("p", { class: "wk-note", text: T("Our own server's wallets never walk here: the cruise passengers and the island's bot are made up. IDNI's test accounts walk in grey.") }),
        el("div", { class: "cv-acts" }, game.btn(T("Islander studio"), () => choose()), OF() ? game.btn(T("Rules between wallets"), () => OF().inbox()) : null, me && W.by.has(me) ? game.btn(T("Find me"), () => { game.closeCard(); find(); }) : null, game.btn(T("Back to the island"), () => game.closeCard(), { go: true })));
    });
  }
  /* ---------- your own islander ---------- */
  function find() {   // a beacon over your islander for ten seconds (it waves)
    const me = myPk(); if (!me || !W.by.has(me)) return false;
    W.find = { a: me, until: performance.now() + 10000 }; return true;
  }
  const mine = () => { const me = myPk(); return me ? { pk: me, w: W.by.get(me) || null, parts: myParts((W.all || []).find(x => x.a === me), me), name: nameOf(me) } : null; };
  /* after a choice was sent: this browser's islander wears it at once; the island shows it to everyone once a block holds it */
  function wear(pk, p) {
    try { store.set(MINE2, JSON.stringify({ pk, p, at: Date.now() })); } catch (e) {}
    const w = W.by.get(pk); if (w) { w.lk = p.slice(); w.ping = performance.now(); }
    CARDS.delete(pk);
  }
  function choose() { if (window.ISLE_STUDIO) ISLE_STUDIO.open(); }

  /* for offers.js: a wallet's face and name by its address, a ring when it sent something */
  const faceOf = (a, size) => { const w = W.by.get(a), d = w ? w.d : (W.all || []).find(x => x.a === a) || { a, traits: [], look: null }; return portrait(w && w.lk ? w.lk : a === myPk() ? myParts(d.pt ? d : null, a) : partsOf({ ...d, a }), d.traits || [], !!d.idni, size); };
  const whoOf = a => { const d = (W.by.get(a) || {}).d || (W.all || []).find(x => x.a === a); return nameOf(a) + (d && d.traits && d.traits.length ? " · " + title(d.traits[0]) : ""); };
  const ping = a => { const w = W.by.get(a); if (w) w.ping = performance.now(); };
  window.ISLE_WALKERS = { faceOf, whoOf, ping, figure, look, gear, tip, open, board, choose, find, me: mine, wear, cardOf, portrait, title, nameOf, relay: () => ({ RELAY, WS, WKEY, BOX }), traits: TRAITS, get demo() { return W.demo; },
    goTo, remote, said: m => said(m, m && W.said.get(m.w), true), unsaid, mine: () => !!(mineW() && ways()), at: a => { const w = W.by.get(a); return w ? [w.x, w.y] : null; } };
  poll(); setInterval(poll, 60000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) poll(); });
  if (Q.get("islander") === "1") { const go = () => (G() && window.ISLE_STUDIO ? setTimeout(choose, 600) : setTimeout(go, 500)); go(); }
})();

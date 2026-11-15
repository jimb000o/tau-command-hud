/* An islander, part by part: what a wallet's islander on White Rabbit Key is made of and how it is drawn, small on the
   island (figure) and large on its card (bust). Used by walkers.js (who walks) and studio.js (the islander studio).

   Seventeen parts, each a number. Without a choice every part comes from the wallet's key (byte i of the key for
   part i; beard, marks and glasses only for about three keys in ten), so every wallet has its own islander from its first transaction, at no cost. A choice is a real payment to
   the hearts box (no key behind it): PART + part * 32 + choice test AGRS, one payment per changed part, all of them in
   one transaction (one fee). The relay (infra/relay/walkers.py) reads them from the blocks, the newest per part wins.
   The older look payments (1,200 + code: skin, hair or hat, shirt) still count; they set skin, hair, hair colour
   and shirt colour. Part 16 is earned on the chain: it is shown only while the wallet has the matching trait.

   On the island an islander is about 28 units tall, so what reads there is its outline: build, hair or hat,
   clothes, colours, the way it walks. The face is seen on its card. (The WoW Diary notes that fine face settings
   were rarely seen under armour; here the face gets its own large drawing instead.)
   window.ISLANDER = { SLOTS, FACE, PART, EARN, parts, fromLook, figure, bust, name, sig, cost } */
(() => {
  "use strict";
  const INK = "#22303a";
  /* id, label, number of choices, the choices' names (colours have none) */
  const SLOTS = [
    ["body", "Build", ["Average", "Slim", "Round", "Tall", "Sturdy"]],
    ["skin", "Skin", 10],
    ["hair", "Hair or hat", ["Short hair", "Long hair", "Bun", "Straw hat", "Cap", "Bandana", "Beanie", "Flower", "Bald", "Curls", "Big curls", "Braids", "Mohawk", "Ponytail", "Headscarf", "Sun hat"]],
    ["hairc", "Hair colour", 10],
    ["top", "Clothes", ["T-shirt", "Tank top", "Shirt with collar", "Hoodie", "Dress", "Poncho", "Vest", "Overalls"]],
    ["topc", "Clothes colour", 16],
    ["legs", "Trousers", 8],
    ["walk", "Walk", ["Stroll", "Bounce", "March", "Shuffle", "Sway"]],
    ["head", "Face shape", ["Round", "Oval", "Square", "Heart", "Long", "Wide"]],
    ["eyes", "Eyes", ["Dots", "Round", "Sleepy", "Wide", "Smiling", "Almond", "Lashes", "Narrow", "Shiny", "Wink"]],
    ["brows", "Brows", ["Light", "Straight", "Arched", "Thick", "Stern", "Worried", "Bushy", "Thin"]],
    ["nose", "Nose", ["Button", "Small", "Long", "Wide", "Pointed", "Round", "Hooked", "Snub"]],
    ["mouth", "Mouth", ["Smile", "Grin", "Calm", "Smirk", "Open", "Pout", "Laugh", "Small o"]],
    ["beard", "Beard", ["None", "Stubble", "Moustache", "Full beard", "Goatee", "Curly moustache", "Sideburns", "Long beard"]],
    ["marks", "Marks", ["None", "Freckles", "Beauty spot", "Rosy cheeks", "Scar", "Laugh lines", "Dimples", "Face paint"]],
    ["extra", "Glasses and jewellery", ["None", "Round glasses", "Square glasses", "Sunglasses", "Monocle", "Gold stud", "Hoops", "Nose ring", "Flower behind the ear", "Eye patch"]],
    ["earned", "Earned on the chain", ["None", "Rule writer's sash", "No Memo goggles", "Banana brooch", "Old hand's scarf", "Guardian badge", "Winner's laurel", "Voter's feather", "Heart pin", "Paw patch"]],
  ];
  const N = SLOTS.map(s => (Array.isArray(s[2]) ? s[2].length : s[2]));
  const PART = 1600, STRIDE = 32;
  /* the trait a wallet needs to wear an earned piece (relay walkers.py EARN, the same list) */
  const EARN = [null, "lawmaker", "hacker", "feeder", "veteran", "guardian", "winner", "voter", "hearts", "catfriend"];
  const EARN_HOW = [null, "Write a rule for your own wallet on the chain.", "Crack a chapter in No Memo.", "Feed Agorzilla.", "Be on the chain for 14 days.", "Give your wallet a guardian: a rule that asks for a co-signer.", "Win a White Rabbit Key election.", "Vote twice: Agorzilla's ballot boxes or the island's.", "Give two hearts to parts of Tau HUD.", "Put food in Déjà's bowl at the café."];
  /* the parts that make a face: two wallets with the same ones wear the same face (earned piece, build, clothes and walk aside) */
  const FACE = [1, 2, 3, 8, 9, 10, 11, 12, 13, 14, 15];

  const SKINS = ["#fbe0c8", "#f1c27d", "#e0ac69", "#d9a066", "#c68642", "#a8693f", "#9a6240", "#8d5524", "#6e4128", "#5a3620"];
  const HAIRC = ["#1d1410", "#3b2416", "#6b4423", "#111111", "#9a9aa0", "#c98c3c", "#e3c98a", "#a8432f", "#ece9e2", "#2c8c88"];
  const TOPS = ["#e85d4a", "#f2b134", "#3aa6a0", "#f4f1ea", "#e86fa0", "#6fa8ff", "#a3e05a", "#c9a0ff", "#284b63", "#7a5a3a", "#1f6f6b", "#2a2a30", "#b5523b", "#e9b44c", "#5a6b3a", "#9a9aa0"];
  const LEGS = ["#2b3a4a", "#4a3a2a", "#e9dfc8", "#1f1f24", "#3a5a7a", "#6b7b4a", "#8d4a3a", "#c9c2b3"];
  const COLOURS = { 1: SKINS, 3: HAIRC, 5: TOPS, 6: LEGS };
  const OLD_SKIN = [1, 2, 4, 5, 7, 9];   // the six skins of the first look payments

  /* a wallet's parts: from its key, then its choices (an array of 17, null = not chosen) */
  function parts(pk, chosen) {
    const k = /^[0-9a-f]{96}$/i.test(String(pk || "")) ? String(pk).toLowerCase() : "0".repeat(96);
    return SLOTS.map((s, i) => {
      const c = chosen && Number.isInteger(chosen[i]) && chosen[i] >= 0 && chosen[i] < N[i] ? chosen[i] : null;
      if (c != null) return c;
      const b = parseInt(k.slice(2 * i, 2 * i + 2), 16);
      return i === 16 ? 0 : i >= 13 ? (b < 180 ? 0 : 1 + b % (N[i] - 1)) : b % N[i];   // beard, marks, glasses: most keys have none
    });
  }
  /* an older look code (0..383 = skin * 64 + hair * 8 + shirt) as choices */
  function fromLook(code) {
    if (!Number.isInteger(code) || code < 0 || code >= 384) return null;
    const c = new Array(17).fill(null);
    c[1] = OLD_SKIN[Math.floor(code / 64)]; c[2] = Math.floor(code / 8) % 8; c[3] = (code * 7 + 3) % 6; c[5] = code % 8;
    return c;
  }
  const sig = p => FACE.map(i => p[i]).join("-");
  const cost = (from, to) => to.reduce((s, v, i) => s + (v !== from[i] ? PART + i * STRIDE + v : 0), 0);

  /* a name from the key's syllables: the same key, the same name, never on the chain */
  function name(pk) {
    const k = String(pk || "").toLowerCase().replace(/[^0-9a-f]/g, "").padEnd(96, "0");
    const C = "klmnprstvbdhjz", V = "aeiou", b = i => parseInt(k.slice(68 + i * 2, 70 + i * 2), 16);
    const n = 2 + (b(0) % 2);
    let s = "";
    for (let i = 0; i < n; i++) s += C[b(i + 1) % C.length] + V[b(i + 4) % V.length];
    if (b(8) % 3 === 0) s += "nlr"[b(9) % 3];
    return s[0].toUpperCase() + s.slice(1);
  }

  const shade = (hex, f) => { const n = parseInt(hex.slice(1), 16), c = [n >> 16, (n >> 8) & 255, n & 255].map(v => Math.max(0, Math.min(255, Math.round(f < 0 ? v * (1 + f) : v + (255 - v) * f)))); return "#" + c.map(v => v.toString(16).padStart(2, "0")).join(""); };
  const BODY = [[4.6, 3.6, 1], [3.9, 3.1, 1], [5.9, 4.1, 0.94], [4.3, 3.5, 1.13], [5.4, 4.9, 1]];   // hem, shoulders, height
  const WALK = [[2.2, 0.9, 0, 1], [1.8, 2.1, 0, 1.05], [3.1, 0.45, 0, 1.12], [1, 0.3, 0, 0.78], [2, 0.8, 0.09, 0.95]];   // leg swing, bob, sway, speed

  /* ---------- small, on the island: feet at (x, y), s = scale; o = { t, ph, walk, face, idni, gear, light, wave, shake, sit } ---------- */
  function figure(g, x, y, s, p, o = {}) {
    const t = o.t || 0, ph = o.ph || 0, go = o.walk && !o.sit ? 1 : 0, face = o.face || 1, grey = !!o.idni, gr = o.gear || {};
    const [hem, sh, tall] = BODY[p[0]], [swA, bobA, swayA] = WALK[p[7]];
    const sw = Math.sin(ph) * swA * go, bob = Math.abs(Math.sin(ph)) * bobA * go;
    const skin = SKINS[p[1]], top = grey ? "#8d9097" : TOPS[p[5]], legs = grey ? "#4a4d52" : LEGS[p[6]], hc = grey ? "#2d2f33" : HAIRC[p[3]];
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
    const L = 9 * tall;   // legs
    g.translate(0, -bob);
    if (swayA && go) g.rotate(Math.sin(ph) * swayA);
    if (o.shake) g.rotate(Math.sin(t * 0.03) * 0.06);
    if (gr.back) {
      g.fillStyle = gr.back === "backpack" ? "#7a5a3a" : "#b08850"; g.strokeStyle = INK; g.lineWidth = 0.7;
      g.beginPath(); g.roundRect ? g.roundRect(-sh - 3, -L - 9.5 * tall, 3.4, gr.back === "backpack" ? 7 : 5, 1) : g.rect(-sh - 3, -L - 9.5 * tall, 3.4, 6); g.fill(); g.stroke();
    }
    g.strokeStyle = legs; g.lineWidth = 1.9;
    if (o.sit) { g.beginPath(); g.moveTo(-1.6, -L * 0.45); g.lineTo(3.5, -L * 0.4); g.lineTo(4.5, 0); g.moveTo(1.6, -L * 0.45); g.lineTo(6, -L * 0.45); g.lineTo(6.8, -0.2); g.stroke(); }
    else { g.beginPath(); g.moveTo(-1.6, -L); g.lineTo(-1.6 + sw, 0); g.moveTo(1.6, -L); g.lineTo(1.6 - sw, 0); g.stroke(); }
    g.strokeStyle = INK; g.lineWidth = 0.6; g.fillStyle = INK; g.beginPath(); g.ellipse(-1.6 + (o.sit ? 6 : sw), -0.3, 1.3, 0.6, 0, 0, Math.PI * 2); g.ellipse(1.6 + (o.sit ? 5.2 : -sw), -0.3, 1.3, 0.6, 0, 0, Math.PI * 2); g.fill();
    const by = o.sit ? -L * 0.45 : -L, ty = by - 10 * tall, tp = p[4];   // the body: hem at by, shoulders at ty (sitting on the ground: lower)
    g.fillStyle = top; g.strokeStyle = INK; g.lineWidth = 0.9;
    const bodyPath = (hw, low) => { g.beginPath(); g.moveTo(-hw, by + low); g.lineTo(-sh, ty); g.lineTo(sh, ty); g.lineTo(hw, by + low); g.closePath(); };
    if (tp === 4) bodyPath(hem + 1.6, 2.6);        // dress: longer and wider
    else if (tp === 5) { g.beginPath(); g.moveTo(-hem - 2.2, by - 1); g.lineTo(0, ty - 0.6); g.lineTo(hem + 2.2, by - 1); g.closePath(); }   // poncho
    else bodyPath(hem, 0.5);
    g.fill(); g.stroke();
    if (tp === 5) { g.strokeStyle = shade(top, -0.35); g.lineWidth = 0.7; g.beginPath(); g.moveTo(-hem - 0.6, by - 3); g.lineTo(hem + 0.6, by - 3); g.stroke(); }
    if (tp === 6) { g.fillStyle = "#f4f1ea"; g.beginPath(); g.moveTo(-1, ty); g.lineTo(1, ty); g.lineTo(0.8, by + 0.4); g.lineTo(-0.8, by + 0.4); g.fill(); }   // vest: the shirt shows
    if (tp === 7) { g.fillStyle = shade(top, -0.3); g.fillRect(-hem * 0.8, by - 4.5, hem * 1.6, 5); g.fillRect(-2.2, ty, 0.9, 6); g.fillRect(1.3, ty, 0.9, 6); }   // overalls
    if (tp === 3) { g.fillStyle = shade(top, -0.18); g.beginPath(); g.arc(0, ty + 0.4, 2.6, Math.PI, 0); g.fill(); }   // hood
    if (tp === 2) { g.fillStyle = "#f4f1ea"; g.beginPath(); g.moveTo(-1.8, ty); g.lineTo(0, ty + 2.2); g.lineTo(1.8, ty); g.fill(); }
    // arms
    g.lineWidth = 1.5; g.strokeStyle = tp === 1 || tp === 4 ? skin : top;
    const ay = ty + 1.5, wave = o.wave ? Math.sin(t * 0.02) : null;
    g.beginPath(); g.moveTo(-sh - 0.1, ay); g.lineTo(-sh - 1.7 - sw * 0.4, ay + 6.5);
    if (wave != null) { g.moveTo(sh + 0.1, ay); g.lineTo(sh + 3.2 + wave * 1.4, ay - 6); }
    else { g.moveTo(sh + 0.1, ay); g.lineTo(sh + 2 + sw * 0.4, ay + 6); }
    g.stroke();
    g.fillStyle = skin; g.beginPath(); g.arc(-sh - 1.7 - sw * 0.4, ay + 6.8, 0.8, 0, Math.PI * 2); g.fill();
    if (gr.chest === "heart") { g.fillStyle = "#e8436a"; g.beginPath(); g.moveTo(1.2, ty + 5.9); g.bezierCurveTo(-0.6, ty + 4.5, 0.1, ty + 2.9, 1.2, ty + 3.9); g.bezierCurveTo(2.3, ty + 2.9, 3, ty + 4.5, 1.2, ty + 5.9); g.fill(); }
    if (gr.chest === "rosette") { g.fillStyle = "#e9b44c"; g.beginPath(); g.arc(1.6, ty + 3.5, 1.3, 0, Math.PI * 2); g.fill(); g.fillStyle = "#c0533f"; g.fillRect(1, ty + 4.7, 0.6, 1.8); g.fillRect(1.8, ty + 4.7, 0.6, 1.8); }
    earnedSmall(g, grey ? 0 : p[16], sh, ty, by);
    // head
    const hy = ty - 3.6, [rx, ry] = [[3.7, 3.7], [3.4, 4.0], [3.7, 3.8], [3.8, 3.7], [3.2, 4.2], [4.2, 3.5]][p[8]];
    g.fillStyle = skin; g.strokeStyle = INK; g.lineWidth = 0.9;
    g.beginPath(); if (p[8] === 2 && g.roundRect) g.roundRect(-rx, hy - ry, rx * 2, ry * 2, 1.6); else g.ellipse(0, hy, rx, ry, 0, 0, Math.PI * 2); g.fill(); g.stroke();
    if (!grey && p[13]) { g.fillStyle = p[13] === 1 ? "rgba(40,30,25,.25)" : hc; g.beginPath(); if (p[13] === 2 || p[13] === 5) g.fillRect(0.2, hy + 0.9, 2.6, 0.7); else if (p[13] === 6) { g.fillRect(-rx + 0.2, hy - 0.5, 1, 2.6); } else g.ellipse(0.6, hy + ry * 0.62, rx * 0.8, ry * (p[13] === 7 ? 0.75 : 0.42), 0, 0, Math.PI * 2); g.fill(); }
    g.fillStyle = INK; g.beginPath(); g.arc(1.4, hy - 0.4, 0.45, 0, Math.PI * 2); g.fill();
    if (!grey && p[15] >= 1 && p[15] <= 3) { g.strokeStyle = p[15] === 3 ? "#111" : "#3b3b3b"; g.lineWidth = p[15] === 3 ? 1.2 : 0.5; g.beginPath(); g.moveTo(0.2, hy - 0.5); g.lineTo(rx + 0.2, hy - 0.5); g.stroke(); }
    if (!grey && p[15] === 9) { g.fillStyle = "#111"; g.beginPath(); g.arc(1.6, hy - 0.4, 0.9, 0, Math.PI * 2); g.fill(); }
    hairSmall(g, grey ? 4 : p[2], hc, hy, rx, ry);
    if (!grey && p[16] === 2) { g.fillStyle = "rgba(57,255,138,.95)"; g.fillRect(-rx * 0.6, hy - ry * 0.95, rx * 1.4, 1.1); }
    if (!grey && p[16] === 6) { g.strokeStyle = "#5a9a4a"; g.lineWidth = 0.9; g.beginPath(); g.arc(0, hy - 0.5, rx + 0.4, Math.PI * 1.1, Math.PI * 1.9); g.stroke(); }
    if (!grey && p[16] === 7) { g.strokeStyle = "#e9b44c"; g.lineWidth = 0.8; g.beginPath(); g.moveTo(-rx, hy - 1); g.quadraticCurveTo(-rx - 1.5, hy - 4, -rx - 0.6, hy - 6); g.stroke(); }
    if (gr.head === "crown") { g.fillStyle = "#f2c94c"; g.strokeStyle = INK; g.lineWidth = 0.6; const cy = hy - ry; g.beginPath(); g.moveTo(-3, cy - 0.4); g.lineTo(-3, cy - 3.2); g.lineTo(-1.5, cy - 1.8); g.lineTo(0, cy - 3.8); g.lineTo(1.5, cy - 1.8); g.lineTo(3, cy - 3.2); g.lineTo(3, cy - 0.4); g.closePath(); g.fill(); g.stroke(); }
    if (gr.head === "visor") { g.fillStyle = "rgba(57,255,138,.9)"; g.fillRect(-1.2, hy - 1.3, 4.6, 1.4); g.shadowColor = "#39ff8a"; g.shadowBlur = 4; g.fillRect(-1.2, hy - 1.3, 4.6, 1.4); g.shadowBlur = 0; }
    g.restore();
    const dy = -bob;   // where the free hand is, in the figure's own units (walkers.js hangs what it carries there)
    return { hx: sh + 2 + sw * 0.4, hy: ay + 6 + dy, top: hy - ry + dy };
  }
  function earnedSmall(g, e, sh, ty, by) {
    if (!e) return;
    g.lineWidth = 0.6; g.strokeStyle = INK;
    if (e === 1) { g.strokeStyle = "#e9b44c"; g.lineWidth = 1.3; g.beginPath(); g.moveTo(-sh + 0.4, ty + 0.4); g.lineTo(sh - 0.6, by - 0.6); g.stroke(); }
    else if (e === 3) { g.strokeStyle = "#f2c94c"; g.lineWidth = 0.9; g.beginPath(); g.arc(-1.2, ty + 3.6, 1.2, Math.PI * 0.2, Math.PI * 1.1); g.stroke(); }
    else if (e === 4) { g.fillStyle = "#c0533f"; g.fillRect(-sh, ty - 0.6, sh * 2, 1.6); g.fillRect(-sh + 0.6, ty + 0.6, 1.1, 3.4); }
    else if (e === 5) { g.fillStyle = "#3aa6a0"; g.beginPath(); g.moveTo(-2.4, ty + 2.4); g.lineTo(-0.4, ty + 2.4); g.lineTo(-0.4, ty + 4); g.lineTo(-1.4, ty + 5); g.lineTo(-2.4, ty + 4); g.closePath(); g.fill(); }
    else if (e === 8) { g.fillStyle = "#e8436a"; g.beginPath(); g.arc(-1.8, ty + 3.4, 0.8, 0, Math.PI * 2); g.fill(); }
    else if (e === 9) { g.fillStyle = "#f4f1ea"; g.beginPath(); g.arc(-1.6, ty + 3.6, 1, 0, Math.PI * 2); g.fill(); }
  }
  function hairSmall(g, h, c, hy, rx, ry) {
    g.fillStyle = c; g.strokeStyle = INK; g.lineWidth = 0.6;
    const top = hy - ry, capr = rx + 0.2;
    const cap = (col, brim) => { g.fillStyle = col; g.beginPath(); g.arc(0, hy - 1, capr, Math.PI, 0); g.fill(); g.stroke(); if (brim) { g.beginPath(); g.ellipse(2.6, hy - 1, 2.8, 0.7, 0, 0, Math.PI * 2); g.fill(); g.stroke(); } };
    const crop = () => { g.beginPath(); g.arc(0, hy - 0.8, capr, Math.PI * 1.05, Math.PI * 1.95); g.fill(); };
    switch (h) {
      case 0: crop(); break;
      case 1: g.beginPath(); g.arc(0, hy - 0.8, rx + 0.3, Math.PI, Math.PI * 2); g.lineTo(rx - 0.3, hy + ry + 0.6); g.lineTo(rx - 1.3, hy + 1); g.lineTo(-rx + 0.5, hy + 1); g.lineTo(-rx - 0.5, hy + ry + 1); g.closePath(); g.fill(); break;
      case 2: crop(); g.beginPath(); g.arc(-1.4, top - 1.2, 1.9, 0, Math.PI * 2); g.fill(); break;
      case 3: g.fillStyle = "#e3c26a"; g.beginPath(); g.ellipse(0, top + 1.1, 6.4, 1.4, 0, 0, Math.PI * 2); g.fill(); g.stroke(); g.beginPath(); g.arc(0, top + 0.9, 3.2, Math.PI, 0); g.fill(); g.stroke(); g.fillStyle = "#c0533f"; g.fillRect(-3.1, top + 0.1, 6.2, 0.8); break;
      case 4: cap("#284b63", true); break;
      case 5: cap("#c0533f", false); g.fillStyle = "#c0533f"; g.beginPath(); g.moveTo(-rx + 0.1, hy - 0.6); g.lineTo(-rx - 2.3, hy + 0.8); g.lineTo(-rx - 1.7, hy - 1.4); g.fill(); break;
      case 6: cap("#2c8c88", false); g.fillStyle = "#f4f1ea"; g.beginPath(); g.arc(0, top - 1.2, 1.1, 0, Math.PI * 2); g.fill(); break;
      case 7: crop(); g.fillStyle = "#e86fa0"; for (let k = 0; k < 5; k++) { const a = k / 5 * Math.PI * 2; g.beginPath(); g.arc(-2.6 + Math.cos(a), top + 0.7 + Math.sin(a), 0.8, 0, Math.PI * 2); g.fill(); } g.fillStyle = "#f2c94c"; g.beginPath(); g.arc(-2.6, top + 0.7, 0.6, 0, Math.PI * 2); g.fill(); break;
      case 8: g.fillStyle = "rgba(255,255,255,.35)"; g.beginPath(); g.arc(-1, top + 1.2, 0.8, 0, Math.PI * 2); g.fill(); break;
      case 9: for (let k = 0; k < 7; k++) { const a = Math.PI * (1 + k / 6); g.beginPath(); g.arc(Math.cos(a) * rx, hy - 0.8 + Math.sin(a) * ry, 1.3, 0, Math.PI * 2); g.fill(); } break;
      case 10: g.beginPath(); g.arc(0, hy - 1.6, rx + 2.2, Math.PI * 0.95, Math.PI * 2.05); g.fill(); g.stroke(); break;
      case 11: crop(); g.fillRect(-rx - 0.4, hy - 0.6, 1, ry + 3); g.fillRect(rx - 0.6, hy - 0.6, 1, ry + 3); break;
      case 12: g.fillRect(-0.9, top - 2, 1.8, 3.4); break;
      case 13: crop(); g.beginPath(); g.ellipse(-rx - 1, hy + 0.8, 1.2, 2.6, 0.3, 0, Math.PI * 2); g.fill(); break;
      case 14: g.fillStyle = "#3aa6a0"; g.beginPath(); g.arc(0, hy - 0.6, rx + 0.5, Math.PI * 0.85, Math.PI * 2.15); g.fill(); g.stroke(); break;
      default: g.fillStyle = "#3b3026"; g.beginPath(); g.ellipse(0, top + 1, 6.6, 1.3, 0, 0, Math.PI * 2); g.fill(); g.stroke(); g.beginPath(); g.arc(0, top + 0.8, 3.3, Math.PI, 0); g.fill(); g.stroke(); g.fillStyle = "#e9b44c"; g.fillRect(-3.2, top, 6.4, 0.7);
    }
  }

  /* ---------- large, on its card: a bust in a box of size × size; o = { t, blink, mood: "happy" | "no", idni, bg } ---------- */
  function bust(g, X, Y, size, p, o = {}) {
    const grey = !!o.idni, k = size / 200;
    g.save(); g.translate(X, Y); g.scale(k, k); g.lineCap = "round"; g.lineJoin = "round";
    const skin = SKINS[p[1]], dk = shade(skin, -0.22), hc = grey ? "#2d2f33" : HAIRC[p[3]], top = grey ? "#8d9097" : TOPS[p[5]];
    const [rx, ry, jw, cr] = [[46, 50, 0.78, 0.6], [41, 54, 0.66, 0.5], [45, 51, 0.92, 0.25], [47, 50, 0.5, 0.4], [38, 58, 0.7, 0.45], [51, 46, 0.85, 0.6]][p[8]];
    const cx = 100, cy = 92 - (ry - 50) * 0.3, sx = rx / 46;
    hairBack(g, grey ? 8 : p[2], hc, cx, cy, rx, ry);
    // shoulders and clothes
    const sw = [62, 54, 70, 58, 76][p[0]];
    g.strokeStyle = INK; g.lineWidth = 3;
    g.fillStyle = skin; g.beginPath(); g.moveTo(cx - 15, cy + ry - 14); g.lineTo(cx - 15, 168); g.lineTo(cx + 15, 168); g.lineTo(cx + 15, cy + ry - 14); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = dk; g.globalAlpha = 0.5; g.fillRect(cx - 14, cy + ry - 10, 28, 9); g.globalAlpha = 1;
    clothes(g, grey ? 0 : p[4], top, skin, cx, sw);
    earnedChest(g, grey ? 0 : p[16], cx, sw);
    // ears and head
    g.fillStyle = skin; g.strokeStyle = INK; g.lineWidth = 3;
    for (const d of [-1, 1]) { g.beginPath(); g.ellipse(cx + d * (rx - 1), cy + 6, 8, 11, 0, 0, Math.PI * 2); g.fill(); g.stroke(); }
    headPath(g, cx, cy, rx, ry, jw, cr); g.fill(); g.stroke();
    g.save(); headPath(g, cx, cy, rx, ry, jw, cr); g.clip();   // soft light from the upper left, like the island's paintings
    const sh = g.createRadialGradient(cx - rx * 0.35, cy - ry * 0.4, 6, cx, cy, rx * 1.35); sh.addColorStop(0, "rgba(255,240,220,.22)"); sh.addColorStop(0.6, "rgba(0,0,0,0)"); sh.addColorStop(1, "rgba(30,15,10,.22)");
    g.fillStyle = sh; g.fillRect(cx - rx - 2, cy - ry - 2, rx * 2 + 4, ry * 2 + 4);
    if (!grey) marks(g, p[14], cx, cy, sx, skin);
    if (!grey && p[13]) beardFull(g, p[13], hc, cx, cy, rx, ry, jw);
    g.restore();
    const ey = cy + 4, ex = 17 * sx;
    eyes(g, grey ? 1 : p[9], cx, ey, ex, { ...o, skin });
    brows(g, grey ? 1 : p[10], hc, cx, ey - 15, ex, o.mood);
    nose(g, p[11], dk, cx, cy + 18);
    mouth(g, grey ? 2 : o.mood === "happy" && ![1, 6].includes(p[12]) ? 0 : o.mood === "no" ? 2 : p[12], cx, cy + 33 * (ry / 50));
    if (!grey && [2, 4, 5].includes(p[13])) moustache(g, p[13], hc, cx, cy + 27 * (ry / 50));
    if (!grey) extra(g, p[15], cx, ey, ex, rx, cy);
    hairFront(g, grey ? 4 : p[2], hc, cx, cy, rx, ry);
    if (!grey) earnedHead(g, p[16], cx, cy, rx, ry);
    g.restore();
  }
  function headPath(g, cx, cy, rx, ry, jw, cr) {
    g.beginPath(); g.moveTo(cx, cy - ry);
    g.bezierCurveTo(cx + rx * 0.56, cy - ry, cx + rx, cy - ry * 0.55, cx + rx, cy);
    g.bezierCurveTo(cx + rx, cy + ry * 0.35, cx + rx * (jw + 0.12), cy + ry * 0.6, cx + rx * jw, cy + ry * 0.72);
    g.quadraticCurveTo(cx + rx * jw * cr, cy + ry, cx, cy + ry);
    g.quadraticCurveTo(cx - rx * jw * cr, cy + ry, cx - rx * jw, cy + ry * 0.72);
    g.bezierCurveTo(cx - rx * (jw + 0.12), cy + ry * 0.6, cx - rx, cy + ry * 0.35, cx - rx, cy);
    g.bezierCurveTo(cx - rx, cy - ry * 0.55, cx - rx * 0.56, cy - ry, cx, cy - ry);
    g.closePath();
  }
  function clothes(g, tp, c, skin, cx, sw) {
    const d = shade(c, -0.25), y0 = 160;
    g.strokeStyle = INK; g.lineWidth = 3; g.fillStyle = c;
    const torso = () => { g.beginPath(); g.moveTo(cx - sw - 8, 206); g.quadraticCurveTo(cx - sw - 4, y0 + 4, cx - 30, y0 - 2); g.lineTo(cx + 30, y0 - 2); g.quadraticCurveTo(cx + sw + 4, y0 + 4, cx + sw + 8, 206); g.closePath(); };
    if (tp === 5) { g.beginPath(); g.moveTo(cx - sw - 16, 206); g.lineTo(cx - 24, y0 - 4); g.lineTo(cx + 24, y0 - 4); g.lineTo(cx + sw + 16, 206); g.closePath(); g.fill(); g.stroke();
      for (const [yy, col] of [[184, shade(c, 0.35)], [194, d]]) { g.strokeStyle = col; g.lineWidth = 5; g.beginPath(); g.moveTo(cx - sw - 6, yy); g.lineTo(cx + sw + 6, yy); g.stroke(); }
      g.strokeStyle = INK; g.lineWidth = 3; g.fillStyle = skin; g.beginPath(); g.moveTo(cx - 15, y0 - 4); g.lineTo(cx, y0 + 12); g.lineTo(cx + 15, y0 - 4); g.fill(); g.stroke(); return; }
    if (tp === 1 || tp === 4) {   // tank top, dress: the shoulders show
      g.fillStyle = skin; torso(); g.fill(); g.stroke();
      g.fillStyle = c; g.beginPath(); g.moveTo(cx - sw + 6, 206); g.lineTo(cx - sw + 14, y0 + 16); g.lineTo(cx - 24, y0 + 2); g.quadraticCurveTo(cx, tp === 4 ? y0 + 26 : y0 + 18, cx + 24, y0 + 2); g.lineTo(cx + sw - 14, y0 + 16); g.lineTo(cx + sw - 6, 206); g.closePath(); g.fill(); g.stroke();
      if (tp === 4) { g.fillStyle = shade(c, 0.4); for (let i = 0; i < 6; i++) { g.beginPath(); g.arc(cx - 30 + i * 12, 192 + (i % 2) * 6, 2.2, 0, Math.PI * 2); g.fill(); } }
      return;
    }
    torso(); g.fill(); g.stroke();
    if (tp === 3) { g.fillStyle = d; g.beginPath(); g.moveTo(cx - 34, y0 - 1); g.quadraticCurveTo(cx, y0 + 30, cx + 34, y0 - 1); g.quadraticCurveTo(cx, y0 + 12, cx - 34, y0 - 1); g.fill(); g.stroke();
      g.strokeStyle = "#f4f1ea"; g.lineWidth = 2; g.beginPath(); g.moveTo(cx - 8, y0 + 12); g.lineTo(cx - 9, y0 + 30); g.moveTo(cx + 8, y0 + 12); g.lineTo(cx + 9, y0 + 30); g.stroke(); }
    else if (tp === 2) { g.fillStyle = "#f4f1ea"; for (const s of [-1, 1]) { g.beginPath(); g.moveTo(cx, y0 + 12); g.lineTo(cx + s * 22, y0 - 3); g.lineTo(cx + s * 18, y0 + 14); g.closePath(); g.fill(); g.stroke(); }
      g.fillStyle = d; for (let i = 0; i < 3; i++) { g.beginPath(); g.arc(cx, y0 + 22 + i * 9, 2, 0, Math.PI * 2); g.fill(); } }
    else if (tp === 6) { g.fillStyle = "#f4f1ea"; g.beginPath(); g.moveTo(cx - 20, y0 - 1); g.lineTo(cx + 20, y0 - 1); g.lineTo(cx + 10, 206); g.lineTo(cx - 10, 206); g.closePath(); g.fill(); g.stroke(); g.fillStyle = skin; g.beginPath(); g.moveTo(cx - 12, y0 - 1); g.lineTo(cx, y0 + 10); g.lineTo(cx + 12, y0 - 1); g.fill(); }
    else if (tp === 7) { g.fillStyle = "#f4f1ea"; g.beginPath(); g.moveTo(cx - 14, y0 - 1); g.quadraticCurveTo(cx, y0 + 12, cx + 14, y0 - 1); g.fill(); g.fillStyle = d; g.fillRect(cx - 30, 186, 60, 22); g.strokeRect(cx - 30, 186, 60, 22); for (const s of [-1, 1]) { g.fillRect(cx + s * 22 - 4, y0 + 2, 8, 26); g.strokeRect(cx + s * 22 - 4, y0 + 2, 8, 26); } g.fillStyle = "#e9b44c"; for (const s of [-1, 1]) { g.beginPath(); g.arc(cx + s * 22, 190, 3, 0, Math.PI * 2); g.fill(); } }
    else { g.fillStyle = skin; g.beginPath(); g.moveTo(cx - 16, y0 - 1); g.quadraticCurveTo(cx, y0 + 14, cx + 16, y0 - 1); g.fill(); g.stroke(); }
  }
  function earnedChest(g, e, cx, sw) {
    g.strokeStyle = INK; g.lineWidth = 2.4;
    if (e === 1) { g.fillStyle = "#e9b44c"; g.beginPath(); g.moveTo(cx - 40, 160); g.lineTo(cx - 26, 158); g.lineTo(cx + sw, 206); g.lineTo(cx + sw - 18, 206); g.closePath(); g.fill(); g.stroke(); g.fillStyle = "#f3e7c9"; g.fillRect(cx + 4, 180, 12, 16); g.strokeRect(cx + 4, 180, 12, 16); g.fillStyle = "#c0533f"; g.fillRect(cx + 4, 186, 12, 3); }
    else if (e === 3) { g.strokeStyle = "#f2c94c"; g.lineWidth = 6; g.beginPath(); g.arc(cx - 26, 182, 9, Math.PI * 0.15, Math.PI * 1.05); g.stroke(); g.strokeStyle = "#7a5a3a"; g.lineWidth = 2; g.beginPath(); g.moveTo(cx - 17, 184); g.lineTo(cx - 14, 186); g.stroke(); }
    else if (e === 4) { g.fillStyle = "#c0533f"; g.beginPath(); g.moveTo(cx - 34, 154); g.quadraticCurveTo(cx, 176, cx + 34, 154); g.lineTo(cx + 34, 166); g.quadraticCurveTo(cx, 188, cx - 34, 166); g.closePath(); g.fill(); g.stroke(); g.fillRect(cx - 28, 170, 13, 34); g.strokeRect(cx - 28, 170, 13, 34); g.strokeStyle = "#f2b134"; g.lineWidth = 2; for (let y = 178; y < 202; y += 7) { g.beginPath(); g.moveTo(cx - 28, y); g.lineTo(cx - 15, y); g.stroke(); } }
    else if (e === 5) { g.fillStyle = "#3aa6a0"; g.beginPath(); g.moveTo(cx - 34, 176); g.lineTo(cx - 16, 176); g.lineTo(cx - 16, 190); g.quadraticCurveTo(cx - 16, 198, cx - 25, 202); g.quadraticCurveTo(cx - 34, 198, cx - 34, 190); g.closePath(); g.fill(); g.stroke(); g.strokeStyle = "#f4f1ea"; g.lineWidth = 2.5; g.beginPath(); g.moveTo(cx - 25, 180); g.lineTo(cx - 25, 197); g.stroke(); }
    else if (e === 8) { g.fillStyle = "#e8436a"; g.beginPath(); g.moveTo(cx - 25, 194); g.bezierCurveTo(cx - 38, 184, cx - 31, 172, cx - 25, 180); g.bezierCurveTo(cx - 19, 172, cx - 12, 184, cx - 25, 194); g.fill(); g.stroke(); }
    else if (e === 9) { g.fillStyle = "#f4f1ea"; g.beginPath(); g.arc(cx - 25, 186, 12, 0, Math.PI * 2); g.fill(); g.stroke(); g.fillStyle = "#3a3a3a"; g.beginPath(); g.ellipse(cx - 25, 190, 4.5, 3.5, 0, 0, Math.PI * 2); g.fill(); for (const [a, b] of [[-6, -3], [-2, -7], [3, -7], [7, -3]]) { g.beginPath(); g.arc(cx - 25 + a, 186 + b, 2, 0, Math.PI * 2); g.fill(); } }
  }
  function earnedHead(g, e, cx, cy, rx, ry) {
    g.strokeStyle = INK; g.lineWidth = 2.4;
    if (e === 2) { const y = cy - ry * 0.62; g.fillStyle = "#3b3b3b"; g.fillRect(cx - rx - 2, y - 4, rx * 2 + 4, 7); for (const s of [-1, 1]) { g.fillStyle = "#2a2a30"; g.beginPath(); g.ellipse(cx + s * 16, y, 12, 9, 0, 0, Math.PI * 2); g.fill(); g.stroke(); g.fillStyle = "rgba(57,255,138,.85)"; g.beginPath(); g.ellipse(cx + s * 16, y, 8, 6, 0, 0, Math.PI * 2); g.fill(); g.fillStyle = "rgba(255,255,255,.7)"; g.beginPath(); g.arc(cx + s * 16 - 3, y - 2, 1.8, 0, Math.PI * 2); g.fill(); } }
    else if (e === 6) { g.fillStyle = "#5a9a4a"; for (const s of [-1, 1]) for (let i = 0; i < 5; i++) { const a = Math.PI * (1.5 + s * (0.18 + i * 0.12)); const x = cx + Math.cos(a) * (rx + 2), y = cy - 6 + Math.sin(a) * (ry + 2); g.beginPath(); g.ellipse(x, y, 7, 3.6, a + Math.PI / 2 + s * 0.5, 0, Math.PI * 2); g.fill(); g.stroke(); } }
    else if (e === 7) { g.fillStyle = "#e9b44c"; g.beginPath(); g.moveTo(cx - rx - 2, cy - 4); g.quadraticCurveTo(cx - rx - 26, cy - 30, cx - rx - 14, cy - 62); g.quadraticCurveTo(cx - rx - 4, cy - 30, cx - rx - 2, cy - 4); g.fill(); g.stroke(); g.strokeStyle = "#c0533f"; g.lineWidth = 2; g.beginPath(); g.moveTo(cx - rx - 3, cy - 6); g.quadraticCurveTo(cx - rx - 14, cy - 30, cx - rx - 13, cy - 56); g.stroke(); }
  }
  function marks(g, m, cx, cy, sx, skin) {
    const cheek = 26 * sx;
    if (m === 1) { g.fillStyle = shade(skin, -0.35); for (const s of [-1, 1]) for (let i = 0; i < 6; i++) { g.beginPath(); g.arc(cx + s * (cheek - 8 + (i % 3) * 6), cy + 16 + Math.floor(i / 3) * 5 + (i % 2) * 2, 1.4, 0, Math.PI * 2); g.fill(); } }
    else if (m === 2) { g.fillStyle = "#3b2416"; g.beginPath(); g.arc(cx + 18 * sx, cy + 34, 2, 0, Math.PI * 2); g.fill(); }
    else if (m === 3) { g.fillStyle = "rgba(232,93,110,.28)"; for (const s of [-1, 1]) { g.beginPath(); g.ellipse(cx + s * cheek, cy + 22, 10, 6, 0, 0, Math.PI * 2); g.fill(); } }
    else if (m === 4) { g.strokeStyle = shade(skin, -0.32); g.lineWidth = 2.4; g.beginPath(); g.moveTo(cx + 22 * sx, cy - 20); g.lineTo(cx + 30 * sx, cy + 4); g.stroke(); g.lineWidth = 1.6; for (const y of [-14, -6]) { g.beginPath(); g.moveTo(cx + 22 * sx + (y + 20) * 0.3 - 3, cy + y); g.lineTo(cx + 22 * sx + (y + 20) * 0.3 + 4, cy + y); g.stroke(); } }
    else if (m === 5) { g.strokeStyle = shade(skin, -0.3); g.lineWidth = 2; for (const s of [-1, 1]) { g.beginPath(); g.arc(cx + s * 22 * sx, cy + 32, 9, s < 0 ? -0.3 : Math.PI - 0.9, s < 0 ? 0.9 : Math.PI + 0.3); g.stroke(); } }
    else if (m === 6) { g.strokeStyle = shade(skin, -0.3); g.lineWidth = 2; for (const s of [-1, 1]) { g.beginPath(); g.arc(cx + s * 22 * sx, cy + 36, 3, 0, Math.PI); g.stroke(); } }
    else if (m === 7) { g.strokeStyle = "#3aa6a0"; g.lineWidth = 3.4; for (const d of [0, 7]) { g.beginPath(); g.moveTo(cx - cheek - 8, cy + 14 + d); g.lineTo(cx - cheek + 8, cy + 12 + d); g.stroke(); } }
  }
  function beardFull(g, b, c, cx, cy, rx, ry, jw) {
    g.fillStyle = b === 1 ? "rgba(40,28,22,.22)" : c;
    if (b === 1) { g.beginPath(); g.moveTo(cx - rx, cy + 10); g.quadraticCurveTo(cx - rx * 0.9, cy + ry, cx, cy + ry); g.quadraticCurveTo(cx + rx * 0.9, cy + ry, cx + rx, cy + 10); g.quadraticCurveTo(cx, cy + 40, cx - rx, cy + 10); g.fill(); return; }
    if (b === 3 || b === 7) { const low = b === 7 ? 46 : 8; g.beginPath(); g.moveTo(cx - rx - 2, cy + 2); g.quadraticCurveTo(cx - rx * 0.85, cy + ry + low * 0.6, cx, cy + ry + low); g.quadraticCurveTo(cx + rx * 0.85, cy + ry + low * 0.6, cx + rx + 2, cy + 2); g.lineTo(cx + rx * 0.62, cy + 18); g.quadraticCurveTo(cx, cy + 50, cx - rx * 0.62, cy + 18); g.closePath(); g.fill(); }
    if (b === 4) { g.beginPath(); g.ellipse(cx, cy + ry - 6, 12, 10, 0, 0, Math.PI * 2); g.fill(); }
    if (b === 6) for (const s of [-1, 1]) { g.beginPath(); g.moveTo(cx + s * rx, cy - 6); g.lineTo(cx + s * (rx - 9), cy - 6); g.lineTo(cx + s * (rx - 11), cy + 26); g.lineTo(cx + s * (rx - 2), cy + 22); g.closePath(); g.fill(); }
  }
  function moustache(g, b, c, cx, y) {
    g.fillStyle = c; g.strokeStyle = c; g.lineWidth = 2;
    if (b === 5) { for (const s of [-1, 1]) { g.beginPath(); g.moveTo(cx, y); g.quadraticCurveTo(cx + s * 12, y - 6, cx + s * 20, y + 2); g.quadraticCurveTo(cx + s * 24, y - 6, cx + s * 18, y - 8); g.lineWidth = 4; g.stroke(); } return; }
    g.beginPath(); g.moveTo(cx - (b === 4 ? 10 : 15), y + 3); g.quadraticCurveTo(cx - 8, y - 6, cx, y - 2); g.quadraticCurveTo(cx + 8, y - 6, cx + (b === 4 ? 10 : 15), y + 3); g.quadraticCurveTo(cx, y + 1, cx - (b === 4 ? 10 : 15), y + 3); g.fill();
  }
  function eyes(g, e, cx, y, ex, o) {
    const blink = o.blink, iris = "#3b2a20";
    for (const s of [-1, 1]) {
      const x = cx + s * ex;
      g.strokeStyle = INK; g.lineWidth = 2.4; g.fillStyle = INK;
      if (blink || e === 4 || (e === 9 && s > 0)) { g.beginPath(); g.arc(x, y + 2, 6, Math.PI * 1.15, Math.PI * 1.85); g.stroke(); continue; }
      if (e === 0) { g.beginPath(); g.arc(x, y, 3.8, 0, Math.PI * 2); g.fill(); g.fillStyle = "#fff"; g.beginPath(); g.arc(x - 1.2, y - 1.2, 1.1, 0, Math.PI * 2); g.fill(); continue; }
      if (e === 7) { g.beginPath(); g.moveTo(x - 7, y); g.quadraticCurveTo(x, y - 3, x + 7, y); g.stroke(); g.beginPath(); g.arc(x, y - 0.6, 2.2, 0, Math.PI * 2); g.fill(); continue; }
      const w = e === 3 ? 9 : e === 5 ? 9 : e === 8 ? 8 : 7.4, h = e === 3 ? 8 : e === 5 ? 5 : e === 8 ? 7.4 : 6.4;
      g.fillStyle = "#fbf8f2"; g.beginPath();
      if (e === 5) { g.moveTo(x - w, y); g.quadraticCurveTo(x, y - h * 1.6, x + w, y); g.quadraticCurveTo(x, y + h * 1.4, x - w, y); } else g.ellipse(x, y, w, h, 0, 0, Math.PI * 2);
      g.fill(); g.stroke();
      const ir = e === 8 ? 6 : 4.2;
      g.fillStyle = iris; g.beginPath(); g.arc(x + 0.6, y + 0.4, ir, 0, Math.PI * 2); g.fill();
      g.fillStyle = "#111"; g.beginPath(); g.arc(x + 0.6, y + 0.4, ir * 0.5, 0, Math.PI * 2); g.fill();
      g.fillStyle = "#fff"; g.beginPath(); g.arc(x - 1, y - 1.6, e === 8 ? 2.2 : 1.4, 0, Math.PI * 2); g.fill(); if (e === 8) { g.beginPath(); g.arc(x + 3, y + 2.4, 1, 0, Math.PI * 2); g.fill(); }
      if (e === 2) { g.fillStyle = shade(o.skin || SKINS[0], -0.12); g.beginPath(); g.ellipse(x, y - 1, w + 0.6, h * 0.62, 0, Math.PI, 0); g.fill(); g.beginPath(); g.moveTo(x - w, y - 1); g.lineTo(x + w, y - 1); g.stroke(); }
      if (e === 6) { g.lineWidth = 2; for (const d of [-0.6, 0, 0.6]) { const a = -Math.PI / 2 + s * 0.9 + d * 0.5; g.beginPath(); g.moveTo(x + Math.cos(a) * w, y + Math.sin(a) * h); g.lineTo(x + Math.cos(a) * (w + 4), y + Math.sin(a) * (h + 4)); g.stroke(); } }
    }
  }
  function brows(g, b, c, cx, y, ex, mood) {
    g.strokeStyle = b === 0 ? shade(c, 0.35) : c; g.lineCap = "round";
    const lw = [2.4, 3.4, 3.2, 5.6, 4, 3.4, 6.4, 2][b]; g.lineWidth = lw;
    for (const s of [-1, 1]) {
      const x = cx + s * ex, up = mood === "happy" ? -2 : 0;
      g.beginPath();
      if (b === 0) { g.moveTo(x - s * 5, y + up); g.lineTo(x + s * 5, y - 1 + up); }
      else if (b === 1 || b === 3) { g.moveTo(x - s * 8, y + up); g.lineTo(x + s * 8, y + up); }
      else if (b === 2 || b === 7) { g.moveTo(x - s * 8, y + 2 + up); g.quadraticCurveTo(x, y - (b === 7 ? 9 : 6) + up, x + s * 8, y + 1 + up); }
      else if (b === 4 || mood === "no") { g.moveTo(x - s * 8, y + 4); g.lineTo(x + s * 8, y - 3); }
      else if (b === 5) { g.moveTo(x - s * 8, y - 4 + up); g.lineTo(x + s * 8, y + 2 + up); }
      else { for (let i = -2; i <= 2; i++) { g.moveTo(x + s * i * 3.4 - 2, y + 1 + Math.abs(i) * 0.6); g.lineTo(x + s * i * 3.4 + 2, y - 2 + Math.abs(i) * 0.6); } }
      g.stroke();
    }
  }
  function nose(g, n, c, cx, y) {
    g.strokeStyle = c; g.fillStyle = c; g.lineWidth = 2.6;
    if (n === 0) { g.beginPath(); g.ellipse(cx, y + 2, 4.4, 3.2, 0, 0, Math.PI * 2); g.fill(); }
    else if (n === 1) { g.beginPath(); g.moveTo(cx - 3, y + 4); g.quadraticCurveTo(cx, y + 7, cx + 3, y + 4); g.stroke(); }
    else if (n === 2) { g.beginPath(); g.moveTo(cx + 1, y - 14); g.lineTo(cx + 3, y + 4); g.quadraticCurveTo(cx, y + 8, cx - 4, y + 5); g.stroke(); }
    else if (n === 3) { g.beginPath(); g.moveTo(cx - 9, y + 3); g.quadraticCurveTo(cx - 6, y + 8, cx, y + 7); g.quadraticCurveTo(cx + 6, y + 8, cx + 9, y + 3); g.stroke(); }
    else if (n === 4) { g.beginPath(); g.moveTo(cx, y - 10); g.lineTo(cx + 6, y + 5); g.lineTo(cx - 1, y + 6); g.stroke(); }
    else if (n === 5) { g.globalAlpha = 0.6; g.beginPath(); g.arc(cx, y + 2, 6.4, 0, Math.PI * 2); g.fill(); g.globalAlpha = 1; }
    else if (n === 6) { g.beginPath(); g.moveTo(cx - 1, y - 12); g.quadraticCurveTo(cx + 9, y - 2, cx + 4, y + 6); g.quadraticCurveTo(cx, y + 7, cx - 3, y + 4); g.stroke(); }
    else { g.beginPath(); g.moveTo(cx - 2, y - 6); g.quadraticCurveTo(cx + 5, y + 2, cx + 2, y + 4); g.stroke(); g.beginPath(); g.arc(cx - 3, y + 5, 1.4, 0, Math.PI * 2); g.arc(cx + 3, y + 5, 1.4, 0, Math.PI * 2); g.fill(); }
  }
  function mouth(g, m, cx, y) {
    g.strokeStyle = "#5a2a2a"; g.lineWidth = 2.6; g.fillStyle = "#6b2e2e";
    g.beginPath();
    if (m === 0) { g.moveTo(cx - 11, y - 2); g.quadraticCurveTo(cx, y + 8, cx + 11, y - 2); g.stroke(); }
    else if (m === 1 || m === 6) { const w = m === 6 ? 15 : 12; g.moveTo(cx - w, y - 3); g.quadraticCurveTo(cx, y + (m === 6 ? 16 : 11), cx + w, y - 3); g.closePath(); g.fill(); g.stroke(); g.fillStyle = "#fff"; g.beginPath(); g.moveTo(cx - w + 2, y - 2); g.lineTo(cx + w - 2, y - 2); g.lineTo(cx + w - 5, y + 2); g.lineTo(cx - w + 5, y + 2); g.fill(); if (m === 6) { g.fillStyle = "#d9606a"; g.beginPath(); g.ellipse(cx, y + 8, 6, 3, 0, 0, Math.PI * 2); g.fill(); } }
    else if (m === 2) { g.moveTo(cx - 9, y); g.lineTo(cx + 9, y); g.stroke(); }
    else if (m === 3) { g.moveTo(cx - 9, y + 1); g.quadraticCurveTo(cx + 2, y + 3, cx + 11, y - 4); g.stroke(); }
    else if (m === 4) { g.ellipse(cx, y + 2, 7, 6, 0, 0, Math.PI * 2); g.fill(); g.stroke(); }
    else if (m === 5) { g.fillStyle = "#b8505a"; g.ellipse(cx, y + 1, 7, 4.2, 0, 0, Math.PI * 2); g.fill(); g.lineWidth = 1.6; g.beginPath(); g.moveTo(cx - 6, y + 1); g.lineTo(cx + 6, y + 1); g.stroke(); }
    else { g.arc(cx, y + 1, 3.6, 0, Math.PI * 2); g.fill(); g.stroke(); }
  }
  function extra(g, x, cx, y, ex, rx, cy) {
    g.strokeStyle = "#2a2a30"; g.lineWidth = 2.6;
    if (x === 1 || x === 2 || x === 3) {
      for (const s of [-1, 1]) { g.beginPath(); if (x === 1) g.arc(cx + s * ex, y, 11, 0, Math.PI * 2); else if (g.roundRect) g.roundRect(cx + s * ex - 12, y - 8, 24, 16, x === 3 ? 6 : 2); else g.rect(cx + s * ex - 12, y - 8, 24, 16);
        if (x === 3) { g.fillStyle = "rgba(15,18,22,.88)"; g.fill(); } else { g.fillStyle = "rgba(200,230,255,.12)"; g.fill(); } g.stroke(); }
      g.beginPath(); g.moveTo(cx - ex + 11, y - 1); g.quadraticCurveTo(cx, y - 6, cx + ex - 11, y - 1); g.moveTo(cx - ex - 11, y - 1); g.lineTo(cx - rx + 1, y - 3); g.moveTo(cx + ex + 11, y - 1); g.lineTo(cx + rx - 1, y - 3); g.stroke();
      if (x === 3) { g.fillStyle = "rgba(255,255,255,.5)"; for (const s of [-1, 1]) { g.beginPath(); g.ellipse(cx + s * ex - 4, y - 3, 3, 1.6, -0.5, 0, Math.PI * 2); g.fill(); } }
    } else if (x === 4) { g.strokeStyle = "#c9a35a"; g.beginPath(); g.arc(cx + ex, y, 11, 0, Math.PI * 2); g.stroke(); g.lineWidth = 1.4; g.beginPath(); g.moveTo(cx + ex + 6, y + 9); g.quadraticCurveTo(cx + ex + 14, y + 30, cx + ex + 8, y + 48); g.stroke(); }
    else if (x === 5 || x === 6) { for (const s of [-1, 1]) { const ex2 = cx + s * (rx - 1), ey = cy + 16; if (x === 5) { g.fillStyle = "#f2c94c"; g.beginPath(); g.arc(ex2, ey, 3, 0, Math.PI * 2); g.fill(); } else { g.strokeStyle = "#f2c94c"; g.lineWidth = 2.4; g.beginPath(); g.arc(ex2, ey + 8, 7, 0, Math.PI * 2); g.stroke(); } } }
    else if (x === 7) { g.strokeStyle = "#d9d4c8"; g.lineWidth = 2; g.beginPath(); g.arc(cx + 4, cy + 26, 3.2, -0.5, Math.PI * 1.3); g.stroke(); }
    else if (x === 8) { const fx = cx + rx - 2, fy = cy - 6; g.fillStyle = "#e86fa0"; for (let k = 0; k < 5; k++) { const a = k / 5 * Math.PI * 2; g.beginPath(); g.arc(fx + Math.cos(a) * 6, fy + Math.sin(a) * 6, 5, 0, Math.PI * 2); g.fill(); } g.fillStyle = "#f2c94c"; g.beginPath(); g.arc(fx, fy, 4, 0, Math.PI * 2); g.fill(); }
    else if (x === 9) { g.fillStyle = "#1a1a1e"; g.beginPath(); g.ellipse(cx + ex, y, 10, 8.5, 0, 0, Math.PI * 2); g.fill(); g.lineWidth = 2; g.strokeStyle = "#1a1a1e"; g.beginPath(); g.moveTo(cx - rx + 4, y - 22); g.lineTo(cx + rx - 2, y + 10); g.stroke(); }
  }
  function hairBack(g, h, c, cx, cy, rx, ry) {
    g.fillStyle = c; g.strokeStyle = INK; g.lineWidth = 3;
    if (h === 1) { g.beginPath(); g.moveTo(cx - rx - 8, cy - 10); g.quadraticCurveTo(cx - rx - 16, cy + 60, cx - rx - 6, cy + 86); g.lineTo(cx + rx + 6, cy + 86); g.quadraticCurveTo(cx + rx + 16, cy + 60, cx + rx + 8, cy - 10); g.closePath(); g.fill(); g.stroke(); }
    else if (h === 10) { g.beginPath(); g.arc(cx, cy - 10, rx + 30, 0, Math.PI * 2); g.fill(); g.stroke(); }
    else if (h === 11) for (const s of [-1, 1]) { const x = cx + s * (rx + 2); for (let i = 0; i < 6; i++) { g.beginPath(); g.ellipse(x + s * (i % 2 ? 2 : -1), cy + 6 + i * 13, 7, 8, 0, 0, Math.PI * 2); g.fill(); g.stroke(); } }
    else if (h === 13) { g.beginPath(); g.moveTo(cx + rx - 6, cy - ry + 18); g.quadraticCurveTo(cx + rx + 40, cy - 6, cx + rx + 16, cy + 62); g.quadraticCurveTo(cx + rx + 18, cy + 10, cx + rx - 12, cy - ry + 30); g.closePath(); g.fill(); g.stroke(); }
    else if (h === 14) { g.fillStyle = "#3aa6a0"; g.beginPath(); g.moveTo(cx - rx - 10, cy - 6); g.quadraticCurveTo(cx - rx - 14, cy + 50, cx - rx + 4, cy + 70); g.lineTo(cx + rx - 4, cy + 70); g.quadraticCurveTo(cx + rx + 14, cy + 50, cx + rx + 10, cy - 6); g.closePath(); g.fill(); g.stroke(); }
  }
  function hairFront(g, h, c, cx, cy, rx, ry) {
    g.fillStyle = c; g.strokeStyle = INK; g.lineWidth = 3;
    const top = cy - ry;
    const crop = (low = 0.42) => { g.beginPath(); g.moveTo(cx - rx - 2, cy - ry * 0.05); g.bezierCurveTo(cx - rx - 4, top - 14, cx + rx + 4, top - 14, cx + rx + 2, cy - ry * 0.05);
      g.lineTo(cx + rx - 6, cy - ry * low); for (let i = 5; i >= 0; i--) { const x = cx - rx + 6 + i * (rx * 2 - 12) / 5; g.quadraticCurveTo(x + (rx * 2 - 12) / 10, cy - ry * (low - 0.18), x, cy - ry * low); } g.closePath(); g.fill(); g.stroke(); };
    const capShape = (col, brim) => { g.fillStyle = col; g.beginPath(); g.moveTo(cx - rx - 4, cy - ry * 0.3); g.bezierCurveTo(cx - rx - 4, top - 22, cx + rx + 4, top - 22, cx + rx + 4, cy - ry * 0.3); g.closePath(); g.fill(); g.stroke(); if (brim) { g.beginPath(); g.moveTo(cx - rx + 6, cy - ry * 0.32); g.quadraticCurveTo(cx + rx * 0.5, cy - ry * 0.48, cx + rx + 34, cy - ry * 0.18); g.quadraticCurveTo(cx + rx * 0.4, cy - ry * 0.12, cx - rx + 6, cy - ry * 0.32); g.fill(); g.stroke(); } };
    const brimHat = (col, band) => { g.fillStyle = col; g.beginPath(); g.ellipse(cx, cy - ry * 0.38, rx + 40, 13, 0, 0, Math.PI * 2); g.fill(); g.stroke(); g.beginPath(); g.moveTo(cx - rx + 4, cy - ry * 0.38); g.bezierCurveTo(cx - rx + 2, top - 34, cx + rx - 2, top - 34, cx + rx - 4, cy - ry * 0.38); g.closePath(); g.fill(); g.stroke(); g.fillStyle = band; g.fillRect(cx - rx + 4, cy - ry * 0.38 - 12, rx * 2 - 8, 8); };
    switch (h) {
      case 0: crop(); break;
      case 1: crop(0.3); break;
      case 2: g.beginPath(); g.arc(cx - 8, top - 16, 18, 0, Math.PI * 2); g.fill(); g.stroke(); crop(0.5); break;
      case 3: brimHat("#e3c26a", "#c0533f"); g.strokeStyle = "rgba(122,90,58,.5)"; g.lineWidth = 1.4; for (let i = -3; i <= 3; i++) { g.beginPath(); g.moveTo(cx + i * 12, cy - ry * 0.38 - 10); g.lineTo(cx + i * 14, cy - ry * 0.38 + 10); g.stroke(); } break;
      case 4: capShape("#284b63", true); g.fillStyle = "#f4f1ea"; g.beginPath(); g.arc(cx, top - 10, 4, 0, Math.PI * 2); g.fill(); break;
      case 5: capShape("#c0533f", false); g.fillStyle = "#f4f1ea"; for (let i = 0; i < 7; i++) { g.beginPath(); g.arc(cx - rx + 14 + i * 12, cy - ry * 0.55 - (i % 2) * 8, 2.2, 0, Math.PI * 2); g.fill(); } g.fillStyle = "#c0533f"; g.strokeStyle = INK; g.beginPath(); g.moveTo(cx - rx - 2, cy - ry * 0.3); g.lineTo(cx - rx - 26, cy - 4); g.lineTo(cx - rx - 14, cy - ry * 0.4); g.closePath(); g.fill(); g.stroke(); break;
      case 6: capShape("#2c8c88", false); g.strokeStyle = "rgba(255,255,255,.25)"; g.lineWidth = 2; for (let i = -4; i <= 4; i++) { g.beginPath(); g.moveTo(cx + i * 10, top - 8); g.lineTo(cx + i * 11, cy - ry * 0.34); g.stroke(); } g.fillStyle = "#f4f1ea"; g.strokeStyle = INK; g.lineWidth = 3; g.beginPath(); g.arc(cx, top - 22, 10, 0, Math.PI * 2); g.fill(); g.stroke(); break;
      case 7: crop(); { const fx = cx - rx * 0.55, fy = top + 6; g.fillStyle = "#e86fa0"; for (let k = 0; k < 5; k++) { const a = k / 5 * Math.PI * 2; g.beginPath(); g.arc(fx + Math.cos(a) * 8, fy + Math.sin(a) * 8, 7, 0, Math.PI * 2); g.fill(); g.stroke(); } g.fillStyle = "#f2c94c"; g.beginPath(); g.arc(fx, fy, 5, 0, Math.PI * 2); g.fill(); } break;
      case 8: g.fillStyle = "rgba(255,255,255,.18)"; g.beginPath(); g.ellipse(cx - rx * 0.35, top + 14, 12, 6, -0.4, 0, Math.PI * 2); g.fill(); break;
      case 9: for (let i = 0; i < 11; i++) { const a = Math.PI * (0.95 + i * 0.11); g.beginPath(); g.arc(cx + Math.cos(a) * (rx + 2), cy - 8 + Math.sin(a) * (ry + 4), 11, 0, Math.PI * 2); g.fill(); g.stroke(); } break;
      case 10: g.beginPath(); g.moveTo(cx - rx, cy - ry * 0.3); g.bezierCurveTo(cx - rx, top - 4, cx + rx, top - 4, cx + rx, cy - ry * 0.3); g.quadraticCurveTo(cx, cy - ry * 0.55, cx - rx, cy - ry * 0.3); g.fill(); break;
      case 11: crop(0.46); g.strokeStyle = "rgba(0,0,0,.3)"; g.lineWidth = 2; g.beginPath(); g.moveTo(cx, top - 6); g.lineTo(cx, cy - ry * 0.5); g.stroke(); break;
      case 12: g.beginPath(); g.moveTo(cx - 12, cy - ry * 0.55); for (let i = 0; i < 7; i++) g.lineTo(cx - 12 + i * 4, top - 26 - (i % 2) * 8); g.lineTo(cx + 14, cy - ry * 0.55); g.closePath(); g.fill(); g.stroke(); break;
      case 13: crop(0.5); g.fillStyle = "#c0533f"; g.beginPath(); g.ellipse(cx + rx - 6, top + 22, 5, 7, 0.4, 0, Math.PI * 2); g.fill(); break;
      case 14: g.fillStyle = "#3aa6a0"; g.beginPath(); g.moveTo(cx - rx - 8, cy + 4); g.bezierCurveTo(cx - rx - 12, top - 20, cx + rx + 12, top - 20, cx + rx + 8, cy + 4); g.quadraticCurveTo(cx + rx - 6, cy - ry * 0.4, cx, cy - ry * 0.5); g.quadraticCurveTo(cx - rx + 6, cy - ry * 0.4, cx - rx - 8, cy + 4); g.fill(); g.stroke(); g.strokeStyle = "#e9b44c"; g.lineWidth = 3; g.beginPath(); g.moveTo(cx - rx + 4, cy - ry * 0.44); g.quadraticCurveTo(cx, cy - ry * 0.62, cx + rx - 4, cy - ry * 0.44); g.stroke(); break;
      default: brimHat("#3b3026", "#e9b44c");
    }
  }

  window.ISLANDER = { SLOTS, N, FACE, PART, STRIDE, EARN, EARN_HOW, COLOURS, parts, fromLook, figure, bust, name, sig, cost };
})();

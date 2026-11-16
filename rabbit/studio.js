/* The islander studio on White Rabbit Key: make your wallet's islander part by part (islander.js), see the face large
   and the figure walking, roll the dice or go back to the face your key gave you, then wear it with one real
   transaction from the test wallet in this browser: two small payments to the hearts box per changed part (islander.js
   pays: MARK + part, then PICK + choice test AGRS, no value; the box has no key), all in one transaction, one fee. The
   relay reads it from the block (infra/relay/walkers.py) and the island shows it to everyone. The button says each
   step (signing, sent, waiting for a block, worn) and the studio celebrates when a block holds it.
   On a large screen everything grows with the stage (--k), so the options stay easy to see and hit.

   The earned piece is not for sale: each one opens when the wallet has the matching trait on the chain (a rule of its
   own, a No Memo chapter, a meal for Agorzilla …); a locked one says how to earn it. The first wallet that chooses a
   face is named as its first wearer, by block order, which anyone can check against the blocks.

   The islander pass: a picture (1200 × 675) of your islander with what the chain says about the wallet, to save or
   share. It is drawn in the browser and goes nowhere by itself.
   window.ISLE_STUDIO = { open, close, pass } */
(() => {
  "use strict";
  const IS = window.ISLANDER, WK = () => window.ISLE_WALKERS, GM = () => window.COVE_GAME;
  if (!IS) return;
  const T = s => (window.TauI18n ? TauI18n.t(s) : s);
  const F = (s, v) => T(s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m)));
  const nf = n => Number(n).toLocaleString(window.TauI18n && TauI18n.lang === "zh" ? "zh-CN" : window.TauI18n && TauI18n.lang === "ja" ? "ja-JP" : "en-US");
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } } };
  const phone = () => innerWidth < 760;
  const DPR = () => Math.min(2, devicePixelRatio || 1);
  function el(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) { if (v == null) continue; if (k === "text") e.textContent = v; else if (k === "class") e.className = v; else if (k.startsWith("on")) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v); }
    for (const c of kids.flat()) if (c != null) e.append(c.nodeType ? c : document.createTextNode(c));
    return e;
  }
  const canvas = (w, h) => { const c = document.createElement("canvas"), r = DPR(); c.width = w * r; c.height = h * r; c.style.width = w + "px"; c.style.height = h + "px"; const g = c.getContext("2d"); g.scale(r, r); return [c, g]; };

  /* the tabs: which parts each shows, and how an option is pictured (face = the bust close up, figure = the small islander) */
  const TABS = [
    ["Body", [0, 1, 7]], ["Hair", [2, 3]], ["Clothes", [4, 5, 6]], ["Face", [8, 9, 10, 11, 12]], ["Details", [13, 14, 15]], ["Earned", [16]],
  ];
  const PICT = { 0: "figure", 2: "head", 4: "whole", 7: "figure", 8: "face", 9: "eyes", 10: "eyes", 11: "nose", 12: "mouth", 13: "face", 14: "face", 15: "face", 16: "whole" };
  const CROP = { head: [0, -6, 1], face: [30, 28, 1.6], eyes: [50, 52, 2.4], mouth: [50, 88, 2.4], nose: [50, 66, 2.4], whole: [-10, -16, 0.9] };   // [x, y, zoom] into the 200 box

  const S = { box: null, pk: null, base: null, pick: null, tab: 0, card: null, earned: new Set(), anim: 0, faceAt: 0, faceSig: "", busy: false };

  function thumb(i, v, size) {
    const [c, g] = canvas(size, size), p = S.pick.slice(); p[i] = v;
    const kind = PICT[i];
    if (kind === "figure") IS.figure(g, size / 2, size - 2, (size - 4) / 27, p, { walk: i === 7, ph: 1.2 });
    else { const [x, y, z] = CROP[kind] || [0, 0, 1], k = size / 200 * z; g.save(); g.scale(k, k); g.translate(-x, -y); IS.bust(g, 0, 0, 200, p, {}); g.restore(); }
    return c;
  }
  function optionRow(i) {
    const slot = IS.SLOTS[i], names = Array.isArray(slot[2]) ? slot[2] : null, col = IS.COLOURS[i];
    const list = IS.SHOW[i].includes(S.pick[i]) ? IS.SHOW[i] : IS.SHOW[i].concat(S.pick[i]);   // a look chosen before the lists got shorter still shows
    const n = list.length;
    const size = phone() ? 48 : Math.max(matchMedia("(pointer: coarse)").matches ? 48 : 0, Math.round((col ? 40 : n > 8 ? 44 : 46) * S.k));
    const btns = list.map((v, k) => {
      const locked = i === 16 && v > 0 && !S.earned.has(v) && !S.demoAll;
      const label = names ? T(names[v]) : F("{what} {n}", { what: T(slot[1]), n: k + 1 });
      const b = el("button", { type: "button", class: "st-o" + (S.pick[i] === v ? " on" : "") + (locked ? " locked" : "") + (col ? " sw" : ""), role: "radio", "aria-checked": String(S.pick[i] === v),
        "aria-label": label + (locked ? " · " + T("locked") : ""), title: locked ? label + " · " + T(IS.EARN_HOW[v]) : label, style: `--sz:${size}px` + (col ? `;background:${col[v]}` : "") });
      if (!col) b.append(thumb(i, v, size - 4));
      if (locked) b.append(el("span", { class: "st-lock", "aria-hidden": "true", text: "🔒" }));
      b.addEventListener("click", () => {
        if (locked) { say(F("{x} opens when your wallet does this on the chain: {how}", { x: label, how: T(IS.EARN_HOW[v]) })); return; }
        S.pick[i] = v; render(); });
      return b;
    });
    return el("div", { class: "st-row", role: "radiogroup", "aria-label": T(slot[1]) }, el("small", { text: T(slot[1]) + (names && !(i === 16 && S.pick[i] === 0) ? " · " + T(names[S.pick[i]]) : "") }), el("div", { class: "st-opts" }, btns));
  }
  /* the status line by the button: tone "" / "ok" / "warn" / "work"; an optional link or button after the text */
  const say = (t, tone, extra) => { const m = S.box && S.box.querySelector(".st-msg"); if (!m) return; m.className = "st-msg" + (t ? " show" : "") + (tone ? " " + tone : ""); m.replaceChildren(...(t ? [el("span", { text: t }), extra || null].filter(Boolean) : [])); };
  const sendLabel = (t, busy) => { const b = S.box && S.box.querySelector(".st-send"); if (!b) return; b.textContent = t; b.classList.toggle("busy", !!busy); };

  function render() {
    if (!S.box) return;
    const main = S.box.querySelector(".st-parts");
    main.replaceChildren(...TABS[S.tab][1].map(optionRow));
    if (TABS[S.tab][1].includes(16)) {   // how each piece is earned: the testnet, one step at a time
      const names = IS.SLOTS[16][2];
      main.append(el("ul", { class: "st-earn" }, IS.EARN.map((k, v) => !k ? null : el("li", { class: S.earned.has(v) ? "ok" : "" },
        el("b", { text: (S.earned.has(v) ? "✓ " : "🔒 ") + T(names[v]) + ": " }), T(IS.EARN_HOW[v])))));
      main.append(el("p", { class: "wk-note", text: T("Earned pieces cannot be bought: the relay shows one only while the wallet's own transactions on the chain earn it.") }));
    }
    S.box.querySelectorAll(".st-tab").forEach((b, k) => { b.classList.toggle("on", k === S.tab); b.setAttribute("aria-selected", String(k === S.tab)); });
    const ch = S.pick.map((v, i) => v !== S.base[i] ? i : -1).filter(i => i >= 0);
    const amt = IS.cost(S.base, S.pick);
    S.box.querySelector(".st-cost").textContent = ch.length
      ? (ch.length === 1 ? F("1 part changed: {a} test AGRS (no value) to the hearts box, plus the fee.", { a: nf(amt) }) : F("{n} parts changed: {a} test AGRS (no value) to the hearts box in one transaction, plus the fee.", { n: ch.length, a: nf(amt) }))
      : S.worn ? T("You wear this look now. Change any part to try another one.")
      : T("Nothing changed yet. Your key's face costs nothing: only the parts you change are sent.");
    const sb = S.box.querySelector(".st-send");
    sb.disabled = !ch.length || S.busy;
    if (!S.busy) sendLabel(ch.length ? T("Sign and wear it") : S.worn ? "✓ " + T("Worn") : T("Sign and wear it"));
    const sig = IS.sig(S.pick);
    if (sig !== S.faceSig) { S.faceSig = sig; clearTimeout(S.faceT); S.faceT = setTimeout(() => firstOf(sig), 450); }
  }
  async function firstOf(sig) {
    const line = S.box && S.box.querySelector(".st-first"); if (!line) return;
    if (S.base && IS.sig(S.base) === sig && S.card && S.card.face && S.card.face.mine) { line.textContent = T("You are the first wearer of this face."); line.className = "st-first ok"; return; }
    let f = null;
    if (!(WK() && WK().demo)) try { const r = await fetch(WK().relay().RELAY + "/walkers/face/" + sig, { cache: "no-store" }); if (r.ok) f = await r.json(); } catch (e) {}
    if (!S.box || S.faceSig !== sig) return;
    if (!f || f.error) { line.textContent = ""; return; }
    if (!f.first) { line.textContent = T("No wallet has chosen this face yet: wear it and you are its first wearer."); line.className = "st-first ok"; }
    else if (f.first === S.pk) { line.textContent = T("You are the first wearer of this face."); line.className = "st-first ok"; }
    else { line.textContent = F("{x} chose this face first. You can still wear it.", { x: WK().nameOf(f.first) }); line.className = "st-first"; }
  }
  function loop() {
    if (!S.box || !S.box.isConnected) return;
    const t = performance.now(), b = S.box.querySelector(".st-bust"), f = S.box.querySelector(".st-walk");
    if (b && t - S.drawn > 70) {
      S.drawn = t;
      const g = b.getContext("2d"), r = DPR(), w = b.width / r, h = b.height / r;
      g.setTransform(r, 0, 0, r, 0, 0); g.clearRect(0, 0, w, h);
      const blink = (t % 4200) < 140, mood = t < S.happyUntil ? "happy" : null;
      IS.bust(g, (w - h) / 2, 0, h, S.pick, { blink, mood });
      if (S.party && t - S.party < 2600) {   // worn: a little burst of confetti over the portrait
        const q = (t - S.party) / 2600;
        for (let i = 0; i < 28; i++) {
          const ang = i * 2.39996, sp = 0.35 + (i % 5) * 0.09, x = w / 2 + Math.cos(ang) * sp * w * q, y = h * 0.42 + Math.sin(ang) * sp * h * q + q * q * h * 0.5;
          g.globalAlpha = 1 - q; g.fillStyle = ["#39ff8a", "#ffb13b", "#ff6fa0", "#6fa8ff", "#fff"][i % 5];
          g.save(); g.translate(x, y); g.rotate(ang + q * 6); g.fillRect(-3, -1.5, 6, 3); g.restore();
        }
        g.globalAlpha = 1;
      }
      const fg = f.getContext("2d"), fw = f.width / r, fh = f.height / r;
      fg.setTransform(r, 0, 0, r, 0, 0); fg.clearRect(0, 0, fw, fh);
      fg.fillStyle = "rgba(57,255,138,.08)"; fg.beginPath(); fg.ellipse(fw / 2, fh - 6, fw * 0.36, 5, 0, 0, Math.PI * 2); fg.fill();
      IS.figure(fg, fw / 2, fh - 6, (fh - 14) / 32, S.pick, { walk: true, ph: t * 0.006 * [1, 1.05, 1.12, 0.78, 0.95][S.pick[7]], t, wave: t < S.happyUntil });
    }
    S.anim = requestAnimationFrame(loop);
  }

  async function open() {
    const W = WK(); if (!W) return;
    close(); const game = GM(); if (game) game.closeCard();
    const me = W.me();
    S.pk = me ? me.pk : null;
    S.base = me ? me.parts.slice() : IS.parts(null);
    S.pick = S.base.slice(); S.tab = 0; S.card = null; S.earned = new Set(); S.happyUntil = 0; S.drawn = 0; S.faceSig = ""; S.worn = false; S.party = 0;
    const host = document.getElementById("cvStage") || document.body, R = host.getBoundingClientRect();
    S.k = phone() ? 1 : Math.max(1, Math.min(1.9, Math.min(R.width / 1150, R.height / 640)));
    const bh = phone() ? 132 : Math.round(Math.max(150, Math.min(250 * S.k, R.height - 330)));
    const [bust] = canvas(bh, bh), [walk] = canvas(Math.round((phone() ? 54 : 70) * S.k), Math.round((phone() ? 80 : 100) * S.k));
    bust.className = "st-bust"; walk.className = "st-walk";
    const tabs = el("div", { class: "st-tabs", role: "tablist" }, TABS.map(([n], k) => el("button", { type: "button", role: "tab", class: "st-tab", onclick: () => { S.tab = k; render(); } }, T(n))));
    const box = el("section", { class: "wk-studio", role: "dialog", "aria-modal": "true", "aria-label": T("Islander studio"), style: "--k:" + S.k.toFixed(3) },
      el("button", { type: "button", class: "cv-x", "aria-label": T("Back to the island"), onclick: close, text: "✕" }),
      el("div", { class: "st-prev" },
        el("div", { class: "st-stage" }, bust, walk),
        el("b", { class: "st-name", translate: "no", text: me ? me.name : T("Your islander") }),
        el("small", { class: "st-sub", text: me ? T("Your name comes from your key's letters: the same key, the same name. It is not on the chain.") : T("This browser has no test wallet yet: open tauhud.com/wallet/ first, then your islander gets its own face from your key.") }),
        el("p", { class: "st-first" })),
      el("div", { class: "st-main" },
        el("h3", { text: T("Islander studio") }),
        tabs,
        el("div", { class: "st-parts" }),
        el("div", { class: "st-foot" },
        el("p", { class: "st-cost" }),
        el("p", { class: "st-msg", role: "status", "aria-live": "polite" }),
        el("div", { class: "st-acts" },
          el("button", { type: "button", class: "cv-b", onclick: dice }, "🎲 " + T("Roll the dice")),
          el("button", { type: "button", class: "cv-b", onclick: () => { S.pick = IS.parts(S.pk); say(T("The face your key gave you: free, nothing to send.")); render(); } }, T("My key's face")),
          el("button", { type: "button", class: "cv-b", onclick: () => { S.pick = S.base.slice(); say(""); render(); } }, T("Undo")),
          el("button", { type: "button", class: "cv-b", onclick: () => pass() }, T("Islander pass")),
          el("button", { type: "button", class: "cv-b go st-send", onclick: e => send(e.currentTarget) }, T("Sign and wear it"))))));
    host.append(box);
    S.box = box;
    box.addEventListener("keydown", e => { if (e.key === "Escape") close(); });
    render(); loop();
    setTimeout(() => { const b = box.querySelector(".st-tab"); if (b && !matchMedia("(pointer: coarse)").matches) b.focus({ preventScroll: true }); }, 50);
    if (S.pk) {
      const c = await W.cardOf(S.pk, true);
      if (!S.box) return;
      S.card = c;
      if (c) {
        S.earned = new Set(c.earned || []);
        let pend = null; try { pend = JSON.parse(store.get("tauhud-islander-parts") || "null"); } catch (e) {}
        const fresh = pend && pend.pk === S.pk && Date.now() - pend.at < 1800000;
        if (Array.isArray(c.chosen) && !me.w && !fresh && S.pick.every((v, i) => v === S.base[i])) { S.base = IS.parts(S.pk, c.chosen); S.pick = S.base.slice(); }   // not walking today: what the chain last said
        render();
      }
    }
  }
  function close() {
    cancelAnimationFrame(S.anim); clearTimeout(S.faceT);
    if (S.box) S.box.remove(); S.box = null;
  }
  function dice() {
    const any = L => L[Math.floor(Math.random() * L.length)];
    S.pick = S.pick.map((v, i) => i === 16 ? v : i >= 13 ? (Math.random() < 0.6 ? 0 : any(IS.SHOW[i].slice(1))) : any(IS.SHOW[i]));
    say(""); render();
  }

  /* ---------- wearing it: one transaction, one payment per changed part ---------- */
  const canon = o => Array.isArray(o) ? "[" + o.map(canon).join(",") + "]" : o === null || typeof o !== "object" ? JSON.stringify(o).replace(/[\u007f-￿]/g, c => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0")) : "{" + Object.keys(o).sort().map(k => JSON.stringify(k) + ":" + canon(o[k])).join(",") + "}";
  function socket(url) {
    return new Promise(res => {
      let ws; try { ws = new WebSocket(url); } catch (e) { return res(null); }
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
  const toWallet = () => el("a", { class: "st-link", href: "/wallet/", target: "_blank", rel: "noopener", text: T("Open the wallet page") });
  /* the animated wait while the testnet forges the next block: never an error, only time passing */
  const forge = t => el("span", { class: "st-forge", "aria-hidden": "true" }, el("i"), el("i"), el("i"));
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const PER_TX = 4;   // parts per transaction: the node runs Tau once per transfer (two per part), so 8 transfers answer in seconds
  async function send(b) {
    if (S.busy) return;
    const W = WK(), B = window.TauBLS, R = W.relay(); let k = null;
    try { const s = JSON.parse(store.get(R.WKEY) || "null"); if (B && s && /^[0-9a-f]{64}$/.test(s.sk)) k = { sk: B.hexToBytes(s.sk), pk: s.pk || B.bytesToHex(B.pubOf(B.hexToBytes(s.sk))) }; } catch (e) {}
    if (!k) { say(T("This browser has no test wallet yet: start a campaign on the island or open the wallet page first."), "warn", toWallet()); return; }
    const pick = S.pick.slice(), base = S.base.slice();
    const changed = pick.map((v, i) => (v !== base[i] ? i : -1)).filter(i => i >= 0);
    if (!changed.length) return;
    const groups = [];
    for (let g = 0; g < changed.length; g += PER_TX) groups.push(changed.slice(g, g + PER_TX));
    const parts = changed.length, amount = IS.cost(base, pick);
    S.busy = true; S.worn = false; if (b) b.disabled = true;
    sendLabel(T("Signing…"), true); say(T("Signing in this browser: your key never leaves it."), "work");
    const c = await Promise.race([socket(R.WS), new Promise(r => setTimeout(() => r(null), 8000))]);
    const hashes = [], done = base.slice();
    let unanswered = false, busy = 0;
    try {
      if (!c) throw Object.assign(new Error("relay"), { why: "" });
      const gv = await c.ask("getgovernance"), m = /o9\[t\]:bv\[24\]\s*=\s*\{\s*#x([0-9a-fA-F]+)/.exec((gv && gv.data && gv.data.consensus_rules) || ""), fee = m ? parseInt(m[1], 16) : 10;
      await c.ask("via islander", 4000);
      const st = await c.ask("getsequence " + k.pk); if (!st || st.status !== "ok") throw Object.assign(new Error("relay"), { why: "" });
      const need = amount + fee * 5 * groups.length;
      if (st.data && st.data.balance != null && Number(st.data.balance) < need) {
        say(F("Your test wallet needs {a} test AGRS for this and has {b}. Change fewer parts, or get test AGRS on the wallet page (the faucet pays a wallet that is at 0).", { a: nf(need), b: nf(st.data.balance) }), "warn", toWallet());
        return;
      }
      let seq = st.data.sequence_number || 0;
      for (let g = 0; g < groups.length; g++) {
        const ops = groups[g].flatMap(i => [[k.pk, R.BOX, String(IS.MARK + i)], [k.pk, R.BOX, String(IS.PICK + pick[i])]]);
        const tx = { tx_type: "user_tx", sender_pubkey: k.pk, sequence_number: seq, expiration_time: Math.floor(Date.now() / 1000) + 900,
          expire_at_height: (st.data.tip_height || 0) + 1000, fee_limit: String(fee * 5), operations: { "1": ops } };
        const d = { sender_pubkey: tx.sender_pubkey, sequence_number: tx.sequence_number, expiration_time: tx.expiration_time, fee_limit: tx.fee_limit, tx_type: tx.tx_type, expire_at_height: tx.expire_at_height, operations: tx.operations };
        tx.signature = B.bytesToHex(B.sign(new TextEncoder().encode(canon(d)), k.sk));
        sendLabel(groups.length > 1 ? F("Sending {n} of {m}…", { n: g + 1, m: groups.length }) : T("Sending…"), true);
        say(T("The testnet checks each payment against its rules. That takes a few seconds."), "work", forge());
        const r = await c.ask("sendtx " + JSON.stringify(tx), 90000);
        const er = (r && r.error) || {};
        if (!r || er.code === "NO_ANSWER") { unanswered = true; break; }   // no answer in time: the node may still be checking it, so this is no refusal
        if ((er.code === "BUSY" || er.code === "RATE_LIMITED") && ++busy < 6) { g -= 1; await wait(8000); continue; }   // the relay asks us to wait a moment
        if (!(r.status === "ok" && !(r.data && r.data.ok === false))) {
          const why = String(er.message || r.message || (r.data && (r.data.error || r.data.reason)) || er.code || r.status || "").slice(0, 160);
          try { console.warn("[islander] sendtx refused", r); } catch (x) {}
          throw Object.assign(new Error(/o5|own (policy|rule)|user policy/i.test(why) ? "rule" : "refused"), { why });
        }
        if (r.data && /^[0-9a-f]{64}$/i.test(r.data.tx_hash || "")) hashes.push(r.data.tx_hash);
        groups[g].forEach(i => { done[i] = pick[i]; });
        seq += 1;
      }
      W.wear(k.pk, done); S.base = done.slice(); S.happyUntil = performance.now() + 2500;
      render();
      /* waiting for the block: the node's own answer for the last transaction (the sequence number counts the mempool) */
      const h = hashes[hashes.length - 1] || null;
      const lang = window.TauI18n && TauI18n.lang !== "en" ? "&lang=" + TauI18n.lang : "";
      const ex = () => h ? el("a", { class: "st-link", href: "/explorer/?tx=" + h + lang, target: "_blank", rel: "noopener", text: T("See it in the explorer") }) : null;
      const t0 = Date.now();
      let held = null, out = null, n = 0;
      while (S.box && Date.now() - t0 < 600000) {
        const s2 = Math.round((Date.now() - t0) / 1000);
        sendLabel(F("Forging the block · {n} s", { n: s2 }), true);
        if (n % 10 === 0) say(unanswered ? T("The testnet is still checking your payments. Nothing is wrong: your islander changes as soon as a block holds them.")
          : parts === 1 ? T("Sent. The testnet is forging the next block; your islander here wears it already.") : F("Sent: {n} parts. The testnet is forging the next block; your islander here wears them already.", { n: parts }), "work", el("span", null, forge(), ex()));
        await wait(1000);
        if (++n % 4) continue;   // the label counts every second, the node (or the relay) is asked every four
        if (h) {
          const q = await c.ask("gettxstatus " + h, 6000); if (!q || q.status !== "ok") continue;
          const dd = q.data || {}, stt = String(dd.status || dd.state || "").toLowerCase();
          if (dd.block_number != null || /confirmed|included|mined|sealed|applied/.test(stt)) { held = dd.block_number ?? dd.height ?? true; break; }
          if (/reject|fail|dropped|expired|invalid/.test(stt)) { out = dd.reason || dd.error || stt; break; }
        } else {   // no hash to ask about: the relay's card says what the chain holds for this wallet
          const cd = await W.cardOf(k.pk, true);
          if (cd && Array.isArray(cd.chosen) && changed.every(i => cd.chosen[i] === pick[i])) { held = true; break; }
        }
      }
      if (!S.box) return;
      if (held) {
        if (unanswered) { W.wear(k.pk, pick); S.base = pick.slice(); }
        S.worn = true; S.happyUntil = performance.now() + 6000; S.party = performance.now();
        say((held === true ? T("A block holds it") : F("Block {n} holds it", { n: nf(held) })) + ": " + T("everyone on the island sees your new look now."), "ok",
          el("button", { type: "button", class: "st-link", onclick: () => { close(); if (W.find) W.find(); } }, T("Show me on the island")));
        celebrate(held, k.pk);
      } else if (out) {
        say(F("The testnet dropped it: {x}. Nothing changed on the chain; try again.", { x: String(out).slice(0, 80) }), "warn", ex());
      } else {
        say(T("Still no block after ten minutes: the testnet is resting. Your islander here wears it; the island catches up with the next block."), "work", ex());
      }
    } catch (e) {
      const part = done.some((v, i) => v !== base[i]);
      if (part) { W.wear(k.pk, done); S.base = done.slice(); }
      say((e.message === "rule" ? T("Your wallet's own rule said no to this payment. The rule works: change the rule on the wallet page, or keep your look.")
        : e.message === "relay" ? T("The testnet cannot be reached just now. Nothing was sent; try again in a minute.")
        : T("The testnet said no to this payment.")) + (e.why ? " " + F("The node's answer: {x}", { x: e.why }) : "") + (part ? " " + T("The parts sent before it are worn.") : ""), "warn");
    }
    finally { S.busy = false; if (c) c.close(); if (S.box) render(); }
  }

  /* ---------- the moment a block holds the new look: the whole studio celebrates with the player ---------- */
  function celebrate(block, pk) {
    if (!S.box) return;
    const W = WK(), old = S.box.querySelector(".st-party"); if (old) old.remove();
    const size = Math.round(Math.min(260 * S.k, S.box.clientHeight * 0.48));
    const [face, fg] = canvas(size, size), [fx, gx] = canvas(S.box.clientWidth, S.box.clientHeight);
    fx.className = "st-confetti";
    const first = S.faceSig && S.box.querySelector(".st-first.ok") && /first wearer|第一位|最初/.test(S.box.querySelector(".st-first").textContent);
    const box = el("div", { class: "st-party", role: "alertdialog", "aria-label": T("Your new look is on the chain") }, fx,
      el("div", { class: "st-party-in" }, face,
        el("p", { class: "st-party-k", text: block === true ? T("A block holds it") : F("Block {n}", { n: nf(block) }) }),
        el("h3", { text: T("Your new look is on the chain!") }),
        el("p", { class: "st-party-s", text: (W && pk ? W.nameOf(pk) + " · " : "") + T("Everyone on the island sees it now, and anyone can check it in the blocks.") }),
        first ? el("p", { class: "st-party-first", text: "★ " + T("You are the first wearer of this face.") }) : null,
        el("div", { class: "st-party-acts" },
          el("button", { type: "button", class: "cv-b go", onclick: () => { close(); if (W && W.find) W.find(); } }, T("Show me on the island")),
          el("button", { type: "button", class: "cv-b", onclick: () => pass() }, T("Islander pass")),
          el("button", { type: "button", class: "cv-b", onclick: () => box.remove() }, T("Keep editing")))));
    S.box.append(box);
    const bits = Array.from({ length: 140 }, (_, i) => ({ x: Math.random() * fx.width, y: -20 - Math.random() * fx.height * 0.6, v: 1.6 + Math.random() * 3, w: (Math.random() - 0.5) * 0.2, r: Math.random() * 6, c: ["#39ff8a", "#ffb13b", "#ff6fa0", "#6fa8ff", "#ffffff", "#c9a0ff"][i % 6] }));
    const t0 = performance.now(), cw = S.box.clientWidth, ch = S.box.clientHeight;
    (function tick(t) {
      if (!box.isConnected) return;
      const q = (t - t0) / 1000;
      fg.setTransform(DPR(), 0, 0, DPR(), 0, 0); fg.clearRect(0, 0, size, size);
      IS.bust(fg, 0, 0 - Math.max(0, 1 - q * 2) * 30, size, S.pick, { mood: "happy", blink: (t % 3000) < 120 });
      gx.setTransform(DPR(), 0, 0, DPR(), 0, 0); gx.clearRect(0, 0, cw, ch);
      if (q < 6) for (const b of bits) {
        b.y += b.v; b.x += Math.sin(q * 3 + b.r) * 1.2; b.r += b.w;
        gx.globalAlpha = Math.max(0, Math.min(1, 6 - q)); gx.fillStyle = b.c;
        gx.save(); gx.translate(b.x, b.y); gx.rotate(b.r); gx.fillRect(-4, -2, 8, 4); gx.restore();
      }
      gx.globalAlpha = 1;
      requestAnimationFrame(tick);
    })(t0);
    setTimeout(() => { const g = box.querySelector(".cv-b.go"); if (g && !matchMedia("(pointer: coarse)").matches) g.focus({ preventScroll: true }); }, 60);
  }

  /* ---------- the islander pass: 1200 × 675, drawn here, saved or shared by you ---------- */
  async function pass() {
    const W = WK(); if (!W || !S.box) return;
    const c = S.card || (S.pk ? await W.cardOf(S.pk) : null);
    const cv = document.createElement("canvas"); cv.width = 1200; cv.height = 675;
    const g = cv.getContext("2d");
    const sky = g.createLinearGradient(0, 0, 0, 675); sky.addColorStop(0, "#0d3b4f"); sky.addColorStop(0.62, "#0b2a3a"); sky.addColorStop(1, "#071a24");
    g.fillStyle = sky; g.fillRect(0, 0, 1200, 675);
    g.fillStyle = "rgba(255,214,120,.10)"; g.beginPath(); g.arc(300, 300, 260, 0, Math.PI * 2); g.fill();   // the island's evening sun behind the portrait
    g.strokeStyle = "rgba(57,255,138,.55)"; g.lineWidth = 2; g.strokeRect(24, 24, 1152, 627);
    IS.bust(g, 40, 70, 520, S.pick, { mood: "happy" });
    const font = (w, px) => `${w} ${px}px Sora, "Segoe UI", sans-serif`;
    g.fillStyle = "#39ff8a"; g.font = font(700, 22); g.fillText(T("ISLANDER PASS · WHITE RABBIT KEY"), 600, 92);
    g.fillStyle = "#ffffff"; g.font = font(800, 76); g.fillText(S.pk ? W.nameOf(S.pk) : T("Your islander"), 600, 170);
    const lines = [];
    const tr = (c && c.traits) || [];
    if (tr.length) lines.push(tr.slice(0, 3).map(([k]) => W.title(k)).join(" · "));
    if (c && c.first) lines.push(F("On the chain since {d} · {n} transactions", { d: new Date(c.first * 1000).toLocaleDateString(window.TauI18n && TauI18n.lang === "zh" ? "zh-CN" : window.TauI18n && TauI18n.lang === "ja" ? "ja-JP" : "en-GB", { day: "numeric", month: "short", year: "numeric" }), n: nf(c.txs) }));
    if (c && c.rule && c.rule.in_force) lines.push(T("A personal rule guards this wallet"));
    if (c && c.face && c.face.mine && IS.sig(S.pick) === IS.sig(S.base)) lines.push("★ " + T("First wearer of this face"));
    if (!lines.length) lines.push(T("A real wallet on Tau Net testnet"));
    g.font = font(600, 30); let y = 240;
    for (const l of lines.slice(0, 4)) { g.fillStyle = l.startsWith("★") ? "#ffb13b" : "#ebebee"; wrap(g, l, 600, y, 540, 40).forEach(([t, yy]) => { g.fillText(t, 600, yy); y = yy; }); y += 52; }
    g.fillStyle = "#8a8a94"; g.font = font(500, 22);
    g.fillText(T("Made of 17 parts, worn with one transaction."), 600, 560);
    g.fillText(T("Wallets, not people. Test AGRS have no value."), 600, 592);
    g.fillStyle = "#39ff8a"; g.font = font(700, 26); g.fillText("tauhud.com/rabbit", 600, 632);
    if (S.pk) { g.fillStyle = "#8a8a94"; g.font = `500 18px "JetBrains Mono", monospace`; g.fillText(S.pk.slice(0, 10) + "…" + S.pk.slice(-6), 900, 632); }
    const url = cv.toDataURL("image/png");
    const main = S.box.querySelector(".st-main");
    const img = el("img", { class: "st-pass", src: url, alt: T("Your islander pass") });
    const back = () => { view.remove(); main.hidden = false; };
    const view = el("div", { class: "st-main st-passview" }, el("h3", { text: T("Islander pass") }), img,
      el("p", { class: "wk-note", text: T("Drawn in your browser from what the chain says about your wallet. Save it or share it: nothing is sent anywhere by itself.") }),
      el("div", { class: "st-acts" },
        el("a", { class: "cv-b go", href: url, download: "islander-" + (S.pk ? W.nameOf(S.pk).toLowerCase() : "pass") + ".png" }, T("Save the picture")),
        navigator.canShare ? el("button", { type: "button", class: "cv-b", onclick: async () => { try { const blob = await (await fetch(url)).blob(), file = new File([blob], "islander.png", { type: "image/png" }); if (navigator.canShare({ files: [file] })) await navigator.share({ files: [file], text: T("My islander on White Rabbit Key, made of 17 parts and worn with one transaction on Tau Net testnet:") + " https://tauhud.com/rabbit/" }); } catch (e) {} } }, T("Share")) : null,
        el("button", { type: "button", class: "cv-b", onclick: back }, T("Back to the studio"))));
    main.hidden = true; main.after(view);
  }
  function wrap(g, text, x, y, max, lh) {
    const out = []; let line = "";
    for (const w of text.split(/(\s+)/)) { const t = line + w; if (g.measureText(t).width > max && line.trim()) { out.push([line.trim(), y]); y += lh; line = w.trimStart(); } else line = t; }
    if (line.trim()) out.push([line.trim(), y]);
    return out;
  }

  window.ISLE_STUDIO = { open, close, pass, celebrate };   // celebrate(block): the moment a block holds the look (also for tests)
})();

/* the "Your islander" chip in the top bar opens the studio (so nobody has to find it on a card) */
(function () { const b = document.getElementById("cvIslander"); if (b) b.addEventListener("click", () => { if (window.ISLE_WALKERS) ISLE_WALKERS.choose(); }); })();

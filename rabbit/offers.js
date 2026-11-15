/* Rules between islanders on White Rabbit Key: click another islander and propose a personal rule to its wallet, and
   read, accept or decline the rules other wallets proposed to yours. It is Tau Net's own rule sharing (IDNI tau-testnet
   consensus/rule_offers.py): rule_offer, rule_offer_accept, rule_offer_reject, all signed by the test wallet in this
   browser (tauhud.com/wallet/, the same key the game plays with) and sent through the relay like any wallet transaction.

   What a proposal can and cannot do: a personal rule (o5) only says yes or no to the payments of the wallet that holds
   it; it can never move money. Nobody can put a rule on another wallet: the other wallet's own key has to sign Accept,
   and until then nothing changes for it. Accepting replaces the rule that wallet holds now (one clause per account),
   and its owner can remove it again in the wallet. From the island one proposes one of two shapes, exactly as the
   wallet's rule builder writes them (wallet/index.html buildRule, read back by assets/rulekinds.js): a most per payment,
   or "above N, I co-sign". The inbox shows any rule offered to you, also ones written by hand elsewhere.

   Test params: ?offers=demo shows a made-up proposal in the inbox (marked as such; nothing is signed).
   window.ISLE_OFFERS = { propose, inbox, open, from, count } */
(() => {
  "use strict";
  const WS = "wss://node.tauhud.com", WKEY = "tauhud-wallet-key";
  const T = s => (window.TauI18n ? TauI18n.t(s) : s);
  const F = (s, v) => T(s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m)));
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const Q = new URLSearchParams(location.search), DEMO = Q.get("offers") === "demo" || Q.get("walkers") === "demo";
  const SIMON = () => !!(window.TauSim && TauSim.on);
  const G = () => window.COVE_GAME, WK = () => window.ISLE_WALKERS;
  const short = a => String(a || "").slice(0, 6) + "…" + String(a || "").slice(-4);
  const fmt = n => Number(n).toLocaleString("en-US");
  const phone = () => innerWidth < 760;
  const isAddr = a => /^[0-9a-f]{96}$/.test(String(a || ""));

  /* ---------- the two shapes one proposes from the island, written like the wallet's builder ---------- */
  const MAX_AMOUNT = 2 ** 24 - 1;
  const hex6 = n => Math.max(0, Math.min(MAX_AMOUNT, Math.floor(n))).toString(16).padStart(6, "0");
  const ALLOW = "(o5[t]:bv[24] = { #x000001 }:bv[24])", BLOCK = "(o5[t]:bv[24] = { #x000000 }:bv[24])";
  const capRule = n => `always ( (i1[t]:bv[24] >= { #x${hex6(n + 1)} }:bv[24]) ? ${BLOCK} : ${ALLOW} ).`;
  const coRule = (n, who) => `always ( (i1[t]:bv[24] > { #x${hex6(n)} }:bv[24] && !(i18[t]:bv[384] = { #x${who} }:bv[384])) ? ${BLOCK} : ${ALLOW} ).`;
  const KINDS = {
    cap: { name: "A most per payment", amounts: [500, 1000, 5000], text: (n) => capRule(n),
      says: n => F("Every payment from their wallet stays at {n} test AGRS or less.", { n: fmt(n) }) },
    co: { name: "I co-sign their big payments", amounts: [1000, 5000, 20000], text: (n, me) => coRule(n, me),
      says: n => F("Their payments above {n} test AGRS wait until you co-sign them in your wallet.", { n: fmt(n) }) },
  };

  /* reading a rule back in plain words: the builder's shapes, anything else as "written by hand" */
  function readRule(text) {
    const t = String(text || "");
    if (!t.trim()) return null;
    const r = { cap: null, co: null, only: [], from: null, freeze: false };
    if (/^\s*(always\s*\()?\s*\(\s*o5\[t\]:bv\[24\]\s*=\s*\{\s*#x000001\s*\}:bv\[24\]\s*\)\s*(\)\s*\.)?\s*$/i.test(t)) return { neutral: true };
    if (/i1\[t\]:bv\[24\]\s*>\s*\{\s*#x000000\s*\}:bv\[24\]\s*\)\s*\?/i.test(t) && !/i4\[|i5\[|i1[89]\[|i2[0-5]\[/.test(t)) return { ...r, freeze: true };
    r.only = [...new Set([...t.matchAll(/i4\[t\]:bv\[384\]\s*=\s*\{\s*#x([0-9a-f]{96})/gi)].map(m => m[1].toLowerCase()))];
    const cap = /i1\[t\]:bv\[24\]\s*>=\s*\{\s*#x([0-9a-f]+)/i.exec(t); if (cap) r.cap = parseInt(cap[1], 16) - 1;
    const from = /i5\[t\]:bv\[64\]\s*<\s*\{\s*(\d+)\s*\}/i.exec(t); if (from) r.from = Number(from[1]);
    const lim = /i1\[t\]:bv\[24\]\s*>\s*\{\s*#x([0-9a-f]+)/i.exec(t);
    const who = [...new Set([...t.matchAll(/i(?:1[89]|2[0-5])\[t\]:bv\[384\]\s*=\s*\{\s*#x([0-9a-f]{96})/gi)].map(m => m[1].toLowerCase()))];
    if (lim && who.length) r.co = { limit: parseInt(lim[1], 16), who, all: (t.match(/i1\[t\]:bv\[24\]\s*>\s*\{/g) || []).length > 1 };
    r.unknown = !r.only.length && r.cap == null && r.from == null && !r.co;
    return r;
  }
  function describe(r, me) {
    if (!r) return [T("A rule for your own payments.")];
    if (r.neutral) return [T("No rule: every payment goes through as signed. Accepting it removes the rule you have now.")];
    if (r.freeze) return [T("Nothing leaves your wallet any more.")];
    if (r.unknown) return [T("A rule written by hand. Read it in Tau below, or open it in your wallet.")];
    const name = a => (a === me ? T("you") : short(a)), out = [];
    if (r.only.length) out.push(F("Your payments go only to {x}.", { x: r.only.map(name).join(", ") }));
    if (r.cap != null) out.push(F("At most {n} test AGRS per payment.", { n: fmt(r.cap) }));
    if (r.from != null) out.push(F("Nothing leaves before {x}.", { x: new Date(r.from * 1000).toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" }) }));
    if (r.co) out.push(F(r.co.all ? "Above {n} test AGRS, {x} all co-sign." : "Above {n} test AGRS, {x} co-signs.", { n: fmt(r.co.limit), x: r.co.who.map(name).join(r.co.all ? T(" and ") : T(" or ")) }));
    return out;
  }

  /* ---------- your wallet's offers, from the node (getruleoffers <you> all) ---------- */
  const O = { inc: [], out: [], clause: null, ok: false, told: new Set(), sent: new Map() };   // sent: recipient -> {at, text} proposed from this page
  function myKey() {
    const B = window.TauBLS; try { const s = JSON.parse(store.get(WKEY) || "null"); if (B && s && /^[0-9a-f]{64}$/.test(s.sk)) return { sk: B.hexToBytes(s.sk), pk: (s.pk || B.bytesToHex(B.pubOf(B.hexToBytes(s.sk)))).toLowerCase() }; } catch (e) {}
    return null;
  }
  const myPk = () => { const k = myKey(); return k ? k.pk : null; };
  function demoOffers(me) {
    const a = "8f3a" + "1c".repeat(46), b = "77b0" + "e4".repeat(46);
    return { incoming: [{ offer_id: "d".repeat(64), offerer_pubkey: a, recipient_pubkey: me, status: "offered", expire_at_height: 4321, rule_text: capRule(1000), demo: true },
      { offer_id: "e".repeat(64), offerer_pubkey: b, recipient_pubkey: me, status: "offered", expire_at_height: 4400, rule_text: coRule(5000, b), demo: true }],
      outgoing: [{ offer_id: "f".repeat(64), offerer_pubkey: me, recipient_pubkey: a, status: "accepted", rule_text: capRule(500) }], accepted_clauses: [] };
  }
  async function poll() {
    if (SIMON() || (document.hidden && O.ok)) return;
    const pk = myPk(), game = G(); if (!pk || !game || !game.ask) { O.inc = []; chip(); return; }
    let d = null;
    if (DEMO) d = demoOffers(pk);
    else { const m = await game.ask("getruleoffers " + pk + " all", 15000); if (m && m.status === "ok" && m.data) d = m.data; }
    if (!d) return;
    O.ok = true;
    O.inc = (d.incoming || []).filter(o => o && o.status === "offered");
    O.out = (d.outgoing || []).slice();
    const c = (d.accepted_clauses || []).find(x => x.target_stream === "o5" || x.target_stream === 5);
    O.clause = c ? c.clause_body || null : null;
    for (const [a, s] of O.sent) if (O.out.some(o => o.recipient_pubkey === a && o.status === "offered") || Date.now() - s.at > 6e5) O.sent.delete(a);
    const fresh = O.inc.filter(o => !O.told.has(o.offer_id));
    fresh.forEach(o => O.told.add(o.offer_id));
    if (fresh.length && game.toast && !document.querySelector(".cv-card.of-card")) game.toast(fresh.length === 1 ? T("A wallet proposed a rule to yours. Read it under ✉ at the top.") : F("{n} rules proposed to your wallet. Read them under ✉ at the top.", { n: fresh.length }));
    chip();
    const open = document.querySelector(".cv-card.of-inbox"); if (open && !open.contains(document.activeElement)) inbox();
  }
  function chip() {
    const b = document.getElementById("cvOffers"); if (!b) return;
    const n = O.inc.length;
    b.hidden = !n;
    b.querySelector(".lb").textContent = n === 1 ? T("1 rule for you") : F("{n} rules for you", { n });
  }

  /* ---------- signing and sending, the wallet's way (sign in this browser, the node dry-runs it, then it is sent) ---------- */
  const SIGNED = { rule_offer: ["recipient_pubkey", "rule_text", "expire_at_height"], rule_offer_accept: ["offer_id", "rule_text"], rule_offer_reject: ["offer_id"] };
  const canon = o => Array.isArray(o) ? "[" + o.map(canon).join(",") + "]" : o === null || typeof o !== "object" ? JSON.stringify(o === undefined ? null : o).replace(/[\u007f-￿]/g, c => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0")) : "{" + Object.keys(o).sort().map(k => JSON.stringify(k) + ":" + canon(o[k])).join(",") + "}";
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
  function why(env) {
    const e = (env && (env.error || (env.data && env.data.ok === false ? env.data : null))) || {}, m = String(e.message || e.reason || e || ""), code = String(e.code || "");
    if (/INSUFFICIENT_FUNDS|insufficient/i.test(code + m)) return T("Your test wallet needs a few test AGRS for the fee first: the wallet page gets them from the faucet. Nothing was sent.");
    if (/OFFER_UNKNOWN|unknown offer/i.test(code + m)) return T("That proposal is gone: it was answered or ran out. Nothing was sent.");
    if (/pending|too many/i.test(m)) return T("Too many proposals are open (at most 16 from one wallet, 32 to one wallet). Wait for answers first. Nothing was sent.");
    if (/no room for new wallet|ADMISSION_UNAVAILABLE/i.test(code + m)) return T("Our node can't take this wallet yet (it has no room for new wallet addresses, IDNI issue #108). Nothing was sent.");
    return m ? F("The node said no: {x}. Nothing was sent.", { x: m.slice(0, 160) }) : T("The testnet did not take it just now. Try again in a minute.");
  }
  async function send(type, extra) {
    const k = myKey(); if (!k) return { ok: false, why: T("This browser has no test wallet yet: start a campaign on the island or open tauhud.com/wallet/ first.") };
    if (DEMO) return { ok: false, why: T("A made-up proposal for a test: nothing is signed.") };
    const B = window.TauBLS, c = await socket();
    try {
      if (!c) return { ok: false, why: T("Our node is not reachable right now; nothing was sent.") };
      const gv = await c.ask("getgovernance"), m = /o9\[t\]:bv\[24\]\s*=\s*\{\s*#x([0-9a-fA-F]+)/.exec((gv && gv.data && gv.data.consensus_rules) || ""), fee = m ? parseInt(m[1], 16) : 10;
      await c.ask("via islander");
      const st = await c.ask("getsequence " + k.pk); if (!st || st.status !== "ok") return { ok: false, why: T("No answer from the node; nothing was sent. Try again in a minute.") };
      const tx = { tx_type: type, sender_pubkey: k.pk, sequence_number: st.data.sequence_number || 0, expiration_time: Math.floor(Date.now() / 1000) + 600,
        expire_at_height: (st.data.tip_height || 0) + 1000, fee_limit: String(fee * 5), ...extra };
      const d = { sender_pubkey: tx.sender_pubkey, sequence_number: tx.sequence_number, expiration_time: tx.expiration_time, fee_limit: tx.fee_limit, tx_type: tx.tx_type, expire_at_height: tx.expire_at_height };
      for (const f of SIGNED[type]) d[f] = tx[f];
      tx.signature = B.bytesToHex(B.sign(new TextEncoder().encode(canon(d)), k.sk));
      const body = JSON.stringify(tx);
      const chk = await c.ask("checktx " + body, 20000);
      if (!chk) return { ok: false, why: T("No answer from the node; nothing was sent. Try again in a minute.") };
      if (chk.status !== "ok" || (chk.data && chk.data.ok === false)) return { ok: false, why: why(chk) };
      const r = await c.ask("sendtx " + body, 20000);
      if (!r) return { ok: false, why: T("No answer from the node. It may still arrive: watch your wallet.") };
      if (r.status !== "ok" || (r.data && r.data.ok === false)) return { ok: false, why: why(r) };
      const w = WK() && WK().ping; if (w) w(k.pk);
      return { ok: true, hash: (r.data && r.data.tx_hash) || null };
    } catch (e) { return { ok: false, why: T("The testnet did not take it just now. Try again in a minute.") }; }
    finally { if (c) c.close(); }
  }

  /* ---------- the cards ---------- */
  const face = (a, size) => { const W = WK(); return W && W.portrait ? W.portrait(a, size) : null; };
  const who = a => { const W = WK(), t = W && W.title ? W.title(a) : null; return t ? t + " · " + short(a) : short(a); };
  const SAFE = "A personal rule only says yes or no to its own wallet’s payments; it can never move money.";
  function tauText(el, text) {
    return el("details", { class: "of-tau" }, el("summary", { text: T("The rule in Tau") }), el("code", { translate: "no", text: String(text || "") }));
  }

  /* propose a rule to the wallet `to` */
  function propose(to) {
    const game = G(); if (!game || !isAddr(to)) return;
    const el = game.el, me = myPk(), pick = { kind: "cap", n: 1000 };
    if (to === me) return inbox();
    game.card(null, box => {
      box.classList.add("wk-card", "of-card"); if (phone()) box._tall = true;   // an upright phone: the choice and the button on one page
      const msg = el("p", { class: "wk-note of-msg", role: "status" }), says = el("p", { class: "cv-line of-says" }), tau = el("div");
      const sentTo = O.sent.get(to), open = O.out.filter(o => o.recipient_pubkey === to && o.status === "offered").length;
      const draw = () => {
        const K = KINDS[pick.kind];
        says.textContent = K.says(pick.n);
        tau.replaceChildren(tauText(el, K.text(pick.n, me || "0".repeat(96))));
        box.querySelectorAll(".of-k").forEach(b => { const on = b.dataset.k === pick.kind; b.classList.toggle("on", on); b.setAttribute("aria-checked", String(on)); });
        amts.replaceChildren(...K.amounts.map(n => el("button", { type: "button", class: "of-n" + (n === pick.n ? " on" : ""), role: "radio", "aria-checked": String(n === pick.n), text: fmt(n), onclick: () => { pick.n = n; draw(); } })));
      };
      const amts = el("div", { class: "of-opts", role: "radiogroup", "aria-label": T("Test AGRS") });
      const kinds = el("div", { class: "of-opts", role: "radiogroup", "aria-label": T("Which rule") }, Object.entries(KINDS).map(([k, K]) =>
        el("button", { type: "button", class: "of-k", "data-k": k, role: "radio", text: T(K.name), onclick: () => { pick.kind = k; if (!K.amounts.includes(pick.n)) pick.n = K.amounts[1]; draw(); } })));
      box.append(...[
        el("div", { class: "cv-who" }, face(to, innerHeight < 520 ? 40 : 56), el("div", null, el("b", { text: T("Propose a rule") }), el("small", { translate: "no", text: who(to) }))),
        says, kinds, amts,
        el("p", { class: "wk-note", text: (phone() ? T("Only their own key can take it. A rule never moves money.") : T("Only their own key can take it: they read it and accept or decline. It replaces a rule they hold now. A rule only says yes or no to its own wallet’s payments; it never moves money.")) + (sentTo || open ? " " + T("You already proposed them one; it waits for their answer.") : "") }),
        phone() ? null : tau, msg,
        el("div", { class: "cv-acts" },
          game.btn(T("Sign and propose"), async e => {
            const b = e.currentTarget; b.disabled = true; msg.textContent = T("Signing in your browser, then asking the node…");
            const text = KINDS[pick.kind].text(pick.n, myPk() || "");
            const r = await send("rule_offer", { recipient_pubkey: to, rule_text: text });
            b.disabled = false;
            if (r.ok) { O.sent.set(to, { at: Date.now(), text }); msg.textContent = T("Proposed. Their wallet finds it under ✉ on the island and under Activity in tauhud.com/wallet/. You see their answer here."); setTimeout(poll, 8000); }
            else msg.textContent = r.why;
          }, { go: true }),
          game.btn(T("Back to the island"), () => game.closeCard()))].filter(Boolean));
      draw();
    });
  }

  /* your inbox: rules proposed to your wallet, and what became of yours */
  const STATUS = { offered: "waiting for their answer", accepted: "taken", rejected: "declined", expired: "ran out" };
  function inbox() {
    const game = G(); if (!game) return;
    const el = game.el, me = myPk();
    game.card(null, box => {
      box.classList.add("wk-card", "of-card", "of-inbox");
      const msg = el("p", { class: "wk-note of-msg", role: "status" });
      const mine = readRule(O.clause), hasRule = !!(O.clause && !(mine && mine.neutral));
      const rows = O.inc.slice(0, 6).map(o => {
        const r = readRule(o.rule_text || o.rule_text_preview), acts = el("div", { class: "of-acts" });
        const answer = async (yes, b) => {
          b.disabled = true; msg.textContent = T("Signing in your browser, then asking the node…");
          let text = o.rule_text;
          if (yes && !text && !DEMO) { const m = await G().ask("getruleoffer " + o.offer_id, 15000); text = m && m.status === "ok" && m.data ? m.data.rule_text : null; }
          if (yes && !text && !DEMO) { b.disabled = false; msg.textContent = T("Could not read the proposed rule; try again."); return; }
          const res = await send(yes ? "rule_offer_accept" : "rule_offer_reject", yes ? { offer_id: o.offer_id, rule_text: text } : { offer_id: o.offer_id });
          b.disabled = false;
          if (res.ok) { O.inc = O.inc.filter(x => x.offer_id !== o.offer_id); chip(); msg.textContent = yes ? T("Accepted. From the next block your wallet’s own payments must pass this rule.") : T("Declined. Nothing changes for your wallet."); setTimeout(poll, 8000); box.querySelector(`[data-o="${o.offer_id}"]`)?.remove(); }
          else msg.textContent = res.why;
        };
        const sure = el("div", { class: "of-sure", hidden: true }, el("span", { text: hasRule ? T("Take it? It replaces the rule your wallet holds now.") : T("Take it? From the next block your own payments must pass it.") }),
          game.btn(T("Yes, take this rule"), e => answer(true, e.currentTarget), { go: true }), game.btn(T("Not yet"), () => { sure.hidden = true; acts.hidden = false; }));
        acts.append(...[game.btn(T("Accept"), () => { acts.hidden = true; sure.hidden = false; }, { go: true }), game.btn(T("Decline"), e => answer(false, e.currentTarget)),
          WK() && WK().at && WK().at(o.offerer_pubkey) ? game.btn(T("Who is this?"), () => WK().open(o.offerer_pubkey)) : null].filter(Boolean));
        return el("li", { class: "of-row", "data-o": o.offer_id },
          el("div", { class: "cv-who" }, face(o.offerer_pubkey, 36), el("div", null, el("b", { text: F("{x} proposes", { x: who(o.offerer_pubkey) }) }),
            el("small", { text: o.expire_at_height ? F("Open until block #{a}", { a: fmt(o.expire_at_height) }) + (o.demo ? " · " + T("made up for a test") : "") : "" }))),
          ...describe(r, me).map(t => el("p", { class: "of-says", text: t })),
          phone() && r && !r.unknown ? null : tauText(el, o.rule_text || o.rule_text_preview), acts, sure);
      });
      const outs = O.out.slice(-6).reverse().map(o => el("li", null, el("span", { translate: "no", text: short(o.recipient_pubkey) }), " · ",
        document.createTextNode((describe(readRule(o.rule_text || o.rule_text_preview), me)[0] || "") + " "), el("b", { text: T(STATUS[o.status] || o.status || "") })));
      const addr = el("input", { type: "text", class: "of-addr", placeholder: T("a wallet address (96 characters)"), "aria-label": T("Wallet address"), spellcheck: "false", autocomplete: "off" });
      box.append(...[el("h3", { text: T("Rules proposed to you") }),
        !me ? el("p", { class: "cv-line", text: T("This browser has no test wallet yet: start a campaign on the island or open tauhud.com/wallet/ first.") })
          : rows.length ? el("ul", { class: "of-list" }, rows)
          : el("p", { class: "cv-line", text: O.ok ? T("Nothing proposed to your wallet right now. Click another islander to propose a rule to it.") : T("Reading the chain…") }),
        me ? el("p", { class: "wk-note", text: phone() ? T("A rule never moves money, and only your wallet can take it.") : T(SAFE) + " " + T("Only your wallet can take a rule: Accept is a transaction this browser signs. You can remove a rule again in tauhud.com/wallet/.") }) : null,
        outs.length && !phone() ? el("div", null, el("small", { class: "of-h", text: T("Rules you proposed") }), el("ul", { class: "cv-help of-out" }, outs)) : null,
        me && !phone() ? el("div", { class: "of-any" }, el("small", { class: "of-h", text: T("Propose to any wallet, also one not on the island:") }), el("div", { class: "of-anyrow" }, addr,
          game.btn(T("Propose"), () => { const a = addr.value.trim().toLowerCase(); if (isAddr(a) && a !== me) propose(a); else msg.textContent = T("That is not a wallet address: 96 characters, 0–9 and a–f."); }))) : null,
        msg,
        el("div", { class: "cv-acts" }, me ? game.btn(T("Open my wallet"), () => window.open("/wallet/", "_blank", "noopener")) : null, game.btn(T("Back to the island"), () => game.closeCard(), { go: true }))].filter(Boolean));
    });
  }

  /* for a walker's card: what this wallet proposed to yours, and what you proposed to it */
  const from = a => O.inc.filter(o => o.offerer_pubkey === a);
  const to = a => O.out.filter(o => o.recipient_pubkey === a && o.status === "offered").length + (O.sent.has(a) ? 1 : 0);
  const can = a => !SIMON() && isAddr(a) && !!myPk() && a !== myPk();

  window.ISLE_OFFERS = { propose, inbox, from, to, can, count: () => O.inc.length, read: readRule, describe };
  const wire = () => { const b = document.getElementById("cvOffers"); if (b) b.addEventListener("click", inbox); };
  wire();
  const start = () => (G() ? (poll(), setInterval(poll, 60000)) : setTimeout(start, 700));
  setTimeout(start, 1500);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) poll(); });
  if (Q.get("offers") === "inbox") { const go = () => (G() ? setTimeout(inbox, 900) : setTimeout(go, 500)); go(); }
})();

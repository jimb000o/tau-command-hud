/* Hearts: a visitor marks a part of a page they love with ♥, so we learn what people value most and build that first.
   No tracking: a heart is a real transaction on Tau Testnet Alpha, signed in the browser by the visitor's own test wallet
   (the same key as tauhud.com/wallet/, made here if there is none) and sent to one box with no key behind it (BOX).
   A transaction has no memo, so the amount says which part and which way: LIKE + id gives the heart, UNLIKE + id takes it
   back. Clicks wait SETTLE ms after the last one and only the end state is sent, so a hundred clicks are at most one
   transaction per part; the relay (infra/relay/hearts.py, GET /hearts) counts only each wallet's newest mark per part.
   It counts wallets, not people, and the hearts are public on the chain (no name, only the wallet's key). Test AGRS have no value.
   A part: any element with data-heart="<key>" whose key is in PARTS; the button goes into its h2.
   TauHearts.parts / .name(id) / .counts() for the page that lists them (tauhud.com/hearts/). */
(() => {
  "use strict";
  const BOX = "a43259757c7e5a26dae5dde9ce22ecafe2d7570c93e71ccf65756691d57e7a512e7fdfbfc78e9ce3bfd608b71e286a0b";
  const LIKE = 100, UNLIKE = 200, SETTLE = 10000, RELAY = "https://node.tauhud.com", WS = "wss://node.tauhud.com";
  /* the ids are on the chain for good: never reuse or renumber one, only add */
  const PARTS = {
    "hud-core": [1, "HUD · The chain right now (chain core)"],
    "hud-feed": [2, "HUD · Transactions"],
    "hud-rules": [3, "HUD · Personal money rules"],
    "hud-votes": [4, "HUD · Rule changes by agreement"],
    "hud-check": [5, "HUD · Block check by rules"],
    "hud-chain": [6, "HUD · Blockchain"],
    "hud-sharing": [7, "HUD · Rule sharing"],
    "hud-validators": [8, "HUD · Validators"],
    "hud-state": [9, "HUD · Rules in force now"],
    "hud-log": [10, "HUD · Node log"],
  };
  const T = s => (window.TauI18n ? TauI18n.t(s) : s);
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const load = k => { try { return JSON.parse(store.get(k) || "{}") || {}; } catch (e) { return {}; } };
  const WANT = "tauhud-hearts", SENT = "tauhud-hearts-sent", TOLD = "tauhud-hearts-told", WKEY = "tauhud-wallet-key";
  let want = load(WANT), sent = load(SENT), counts = {}, timer = 0, busy = false;
  const save = () => { store.set(WANT, JSON.stringify(want)); store.set(SENT, JSON.stringify(sent)); };

  /* ---------- the count per part (relay) ---------- */
  async function fetchCounts() {
    try { const r = await fetch(RELAY + "/hearts", { cache: "no-store" }); if (!r.ok) return; const j = await r.json(); counts = (j && j.parts) || {}; paint(); } catch (e) {}
  }
  /* a heart not sent yet shows at once: +1 or −1 on top of the relay's number (a sent one shows once its block is read) */
  const shown = id => Math.max(0, (counts[id] || 0) + (want[id] ? 1 : 0) - (sent[id] && sent[id].on ? 1 : 0));
  function paint() {
    document.querySelectorAll("button.heart[data-id]").forEach(b => {
      const id = b.dataset.id, on = !!want[id], n = shown(id);
      b.setAttribute("aria-pressed", String(on));
      const c = b.querySelector(".hn"); if (c) c.textContent = n ? String(n) : "";
      b.dataset.full = (on ? T("You gave this part a heart. Click again to take it back.") : T("Give this part a heart: tell us you love it, so we build more of it.")) + "\n" +
        (n === 1 ? T("1 wallet loves this part.") : T(`${n} wallets love this part.`)) + "\n" + T("Each heart is a real testnet transaction from the test wallet in your browser: public on the chain, with no name, test AGRS only (no value). It counts wallets, not people.");
    });
  }

  /* ---------- the first heart says what it is, once ---------- */
  function tell(btn, go) {
    if (store.get(TOLD)) return go();
    document.querySelectorAll(".heart-tell").forEach(e => e.remove());
    const box = document.createElement("div"); box.className = "heart-tell"; box.setAttribute("role", "dialog"); box.setAttribute("aria-label", T("What a heart is"));
    const p = document.createElement("p");
    p.textContent = T("A heart tells us which parts of Tau HUD you love most, so we build those first. It is not tracking: the heart is a real transaction on the Tau Net testnet, signed by the test wallet in your browser (made for you if you have none). It is public on the chain with no name, costs only test AGRS (no value), and a second click takes it back.");
    const row = document.createElement("div"); row.className = "ht-row";
    const yes = document.createElement("button"); yes.type = "button"; yes.className = "ht-yes"; yes.textContent = T("Give the heart");
    const no = document.createElement("button"); no.type = "button"; no.textContent = T("Not now");
    const more = document.createElement("a"); more.href = (document.documentElement.dataset.root || "/") + "hearts/"; more.textContent = T("What you love most ›");
    row.append(yes, no, more); box.append(p, row); document.body.append(box);
    const r = btn.getBoundingClientRect(), w = Math.min(360, innerWidth - 24);
    box.style.width = w + "px"; box.style.left = Math.max(12, Math.min(innerWidth - w - 12, r.right - w)) + "px";
    const below = r.bottom + 8 + box.offsetHeight < innerHeight; box.style.top = (below ? r.bottom + 8 : Math.max(12, r.top - 8 - box.offsetHeight)) + "px";
    const close = () => { box.remove(); removeEventListener("keydown", esc); };
    const esc = e => { if (e.key === "Escape") close(); };
    addEventListener("keydown", esc);
    yes.onclick = () => { store.set(TOLD, "1"); close(); go(); };
    no.onclick = close;
    yes.focus();
  }
  function toggle(btn) {
    const id = btn.dataset.id;
    const go = () => { if (want[id]) delete want[id]; else want[id] = 1; save(); paint(); clearTimeout(timer); timer = setTimeout(flush, SETTLE); };
    if (!want[id]) tell(btn, go); else go();
  }

  /* ---------- the transaction ---------- */
  function bls() {
    if (window.TauBLS) return Promise.resolve(window.TauBLS);
    return new Promise(res => {
      const s = document.createElement("script"); s.src = (document.documentElement.dataset.root || "/") + "wallet/vendor/tau-bls.min.js";
      s.onload = () => res(window.TauBLS || null); s.onerror = () => res(null); document.head.append(s);
    });
  }
  async function key() {
    const B = await bls(); if (!B) return null;
    try { const k = JSON.parse(store.get(WKEY) || "null"); if (k && /^[0-9a-f]{64}$/.test(k.sk)) return { B, sk: B.hexToBytes(k.sk), pk: k.pk || B.bytesToHex(B.pubOf(B.hexToBytes(k.sk))) }; } catch (e) {}
    const skHex = B.bytesToHex(B.keygen()), pk = B.bytesToHex(B.pubOf(B.hexToBytes(skHex)));
    store.set(WKEY, JSON.stringify({ sk: skHex, pk }));
    note(T("A test wallet was made for you in this browser. You find it at tauhud.com/wallet/."));
    return { B, sk: B.hexToBytes(skHex), pk };
  }
  /* Python's json.dumps(sort_keys=True, separators=(",", ":")), what the node signs over */
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
  async function flush() {
    if (busy) { clearTimeout(timer); timer = setTimeout(flush, 2000); return; }
    const diff = Object.keys(PARTS).map(k => String(PARTS[k][0])).filter(id => !!want[id] !== !!(sent[id] && sent[id].on));
    if (!diff.length) return;
    busy = true;
    let c = null;
    try {
      const k = await key(); if (!k) throw new Error("no key");
      c = await socket(); if (!c) throw new Error("no relay");
      const g = await c.ask("getgovernance"), m = /o9\[t\]:bv\[24\]\s*=\s*\{\s*#x([0-9a-fA-F]+)/.exec((g && g.data && g.data.consensus_rules) || ""), fee = m ? parseInt(m[1], 16) : 10;
      await c.ask("via hud");
      for (const id of diff) {
        const on = !!want[id], st = await c.ask("getsequence " + k.pk); if (!st || st.status !== "ok") throw new Error("no sequence");
        const tx = { tx_type: "user_tx", sender_pubkey: k.pk, sequence_number: st.data.sequence_number || 0, expiration_time: Math.floor(Date.now() / 1000) + 600,
          expire_at_height: (st.data.tip_height || 0) + 1000, fee_limit: String(fee * 5), operations: { "1": [[k.pk, BOX, String((on ? LIKE : UNLIKE) + Number(id))]] } };
        const d = { sender_pubkey: tx.sender_pubkey, sequence_number: tx.sequence_number, expiration_time: tx.expiration_time, fee_limit: tx.fee_limit, tx_type: tx.tx_type, expire_at_height: tx.expire_at_height, operations: tx.operations };
        tx.signature = k.B.bytesToHex(k.B.sign(new TextEncoder().encode(canon(d)), k.sk));
        const r = await c.ask("sendtx " + JSON.stringify(tx), 20000);
        if (!(r && r.status === "ok" && !(r.data && r.data.ok === false))) { note(T("The testnet did not take the heart just now; it is sent again on your next visit.")); break; }
        sent[id] = { on, at: Date.now(), hash: (r.data && r.data.tx_hash) || "" }; save();
        try { const lk = "tauhud-wallet-log-live-" + k.pk, logs = JSON.parse(store.get(lk) || "[]"); logs.unshift({ hash: sent[id].hash, kind: "pay", label: (on ? "♥ " : "♡ ") + T(PARTS[Object.keys(PARTS).find(p => String(PARTS[p][0]) === id)][1]), at: Date.now(), status: "queued", seq: tx.sequence_number, paid: true }); store.set(lk, JSON.stringify(logs.slice(0, 200))); } catch (e) {}
      }
    } catch (e) { note(T("The testnet is out of reach just now; your heart is sent on your next visit.")); }
    if (c) c.close();
    busy = false; paint(); setTimeout(fetchCounts, 60000);
  }
  function note(t) {
    let n = document.querySelector(".heart-note"); if (!n) { n = document.createElement("div"); n.className = "heart-note"; n.setAttribute("role", "status"); document.body.append(n); }
    n.textContent = t; n.hidden = false; clearTimeout(note.t); note.t = setTimeout(() => { n.hidden = true; }, 6000);
  }

  /* ---------- the buttons ---------- */
  function mount(root = document) {
    root.querySelectorAll("[data-heart]").forEach(part => {
      const p = PARTS[part.dataset.heart], h = part.querySelector("h2, h3"); if (!p || !h || h.querySelector("button.heart")) return;
      const b = document.createElement("button"); b.type = "button"; b.className = "heart"; b.dataset.id = String(p[0]);
      b.setAttribute("aria-label", T("Heart for this part"));
      b.innerHTML = '<span class="hh" aria-hidden="true">♥</span><span class="hn"></span>';
      b.onclick = e => { e.stopPropagation(); toggle(b); };
      const info = h.querySelector("button.info"); if (info) h.insertBefore(b, info); else h.append(b);
    });
    paint();
  }
  /* the CSS travels with the script, so any page gets the same heart */
  const css = document.createElement("style");
  css.textContent = `button.heart{display:inline-flex;align-items:center;gap:4px;flex:none;margin-left:6px;padding:0 6px;min-height:22px;border:1px solid var(--line,rgba(255,255,255,.12));border-radius:999px;background:transparent;color:var(--dim,#8a8a94);font:500 11px var(--mono,monospace);letter-spacing:0;text-transform:none;cursor:pointer;line-height:1}
button.heart .hh{font-size:12px}button.heart:hover,button.heart:focus-visible{color:#ff6b8a;border-color:rgba(255,107,138,.6)}
button.heart[aria-pressed="true"]{color:#ff6b8a;border-color:rgba(255,107,138,.7);background:rgba(255,107,138,.1)}
@media (pointer:coarse){button.heart{min-height:44px;min-width:44px;justify-content:center}}
.heart-tell{position:fixed;z-index:80;background:#101012;border:1px solid rgba(255,107,138,.6);border-radius:8px;padding:12px;box-shadow:0 20px 50px -10px rgba(0,0,0,.9);font:13px/1.5 var(--mono,monospace);color:#ebebee}
.heart-tell p{margin:0 0 10px}.heart-tell .ht-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.heart-tell button{min-height:36px;padding:4px 12px;border-radius:999px;border:1px solid rgba(255,255,255,.2);background:transparent;color:#fff;font:600 12px var(--display,sans-serif);cursor:pointer}
.heart-tell .ht-yes{background:#ff6b8a;border-color:#ff6b8a;color:#000}.heart-tell a{color:#8a8a94;font-size:12px}
.heart-note{position:fixed;z-index:80;left:50%;bottom:16px;transform:translateX(-50%);max-width:calc(100% - 32px);background:#101012;border:1px solid rgba(255,255,255,.2);border-radius:8px;padding:8px 12px;font:12px/1.4 var(--mono,monospace);color:#ebebee}.heart-note[hidden]{display:none}`;
  document.head.append(css);
  const start = () => { mount(); fetchCounts(); setInterval(() => { if (!document.hidden) fetchCounts(); }, 120000); if (Object.keys(PARTS).some(k => { const id = String(PARTS[k][0]); return !!want[id] !== !!(sent[id] && sent[id].on); })) timer = setTimeout(flush, 4000); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
  window.TauHearts = { BOX, LIKE, UNLIKE, parts: PARTS, mount, counts: () => counts, fetch: fetchCounts,
    name: id => { const k = Object.keys(PARTS).find(p => String(PARTS[p][0]) === String(id)); return k ? PARTS[k][1] : null; },
    decode: a => { const n = Number(a); return n > LIKE && n < LIKE + 100 ? { id: n - LIKE, on: true } : n > UNLIKE && n < UNLIKE + 100 ? { id: n - UNLIKE, on: false } : null; } };
})();

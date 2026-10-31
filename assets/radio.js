/* Radio Coco in the header: one sound switch for the whole site. On the HUD and the other pages it plays the island's
   radio from the White Rabbit Key: the same calypso (rabbit/music.js), Rico's voice and lines (rabbit/rico.js, clips made
   on the server) and his reading of the chain weather. Where a page has a sound of its own, the switch is that sound:
   the newspaper and its café (gazette-sound), the island game (tauhud-rabbit-sound). Turning it on or off sets all three,
   so the choice follows the visitor from page to page. Browsers allow sound only after a click, so on a new page a
   radio that was on waits for the first click or key anywhere, and the button glows until then.
   window.TauRadio = { mount(host, page, tip) } (called by nav.js). */
(() => {
  "use strict";
  if (window.TauRadio) return;
  const me = document.currentScript, ROOT = me && me.src ? new URL("..", me.src).href : location.origin + "/";
  const KEY = "tauhud-radio", KEYS = [KEY, "gazette-sound", "tauhud-rabbit-sound"];
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const I = window.TauI18n, T = s => (I ? I.t(s) : s), F = (s, v) => T(s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m)));
  const CJK = I && /^(zh|ja)$/.test(I.lang);
  const ICON = `<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 6.5 12.5 2.6l.4 1-6.7 2.9H14a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V7.5a1 1 0 0 1 1-1h1zm-.5 1.5v5.5h11V8h-11zm8 .8a1.95 1.95 0 1 1 0 3.9 1.95 1.95 0 0 1 0-3.9zM3.5 9h4v1h-4V9zm0 2h4v1h-4v-1z"/></svg>`;
  const TIP = {
    radio: "Radio Coco 97.3 from the White Rabbit Key: calypso, and Rico on the chain. Stays on across pages.",
    gazette: "The café's sound: street, room, gramophone. The same switch as Radio Coco elsewhere.",
    rabbit: "The island's sound and Radio Coco. The same switch as on every other page.",
  };

  const R = { page: "hud", btn: null, cap: null, mode: "radio", loading: null, waiting: false, timer: 0, next: 0, n: 0, last: -1 };
  const wanted = () => store.get(KEY) === "on";
  const setAll = on => KEYS.forEach(k => store.set(k, on ? "on" : "off"));

  /* ---------- the button ---------- */
  function show() {
    const b = R.btn; if (!b) return;
    let on, wait = false;
    if (R.mode === "gazette") on = store.get("gazette-sound") !== "off";
    else if (R.mode === "rabbit") { const S = window.COVE_SOUND; on = !!(S && S.wanted); wait = on && !(S && S.on); }
    else { on = wanted(); wait = on && R.waiting; }
    b.classList.toggle("on", on); b.classList.toggle("wake", wait);
    b.setAttribute("aria-pressed", on ? "true" : "false");
    b.querySelector(".lbl").textContent = T("Radio Coco");
    b.setAttribute("aria-label", T(wait ? "Tap for Radio Coco" : on ? "Radio Coco: on. Turn the sound off" : "Radio Coco: off. Turn the sound on"));
  }

  /* ---------- the island's radio, loaded only when somebody wants it ---------- */
  const script = src => new Promise(res => { const s = document.createElement("script"); s.src = src; s.onload = () => res(true); s.onerror = () => res(false); document.head.append(s); });
  function load() {
    if (R.loading) return R.loading;
    const need = [];
    if (I && I.lang !== "en") need.push(script(ROOT + "assets/i18n/" + I.lang + "/rabbit.js"));   // Rico's lines in the reader's language
    if (!window.COVE_SOUND) need.push(script(ROOT + "rabbit/music.js"));
    if (!window.RICO) need.push(script(ROOT + "rabbit/rico.js"));
    return (R.loading = Promise.all(need).then(() => !!(window.COVE_SOUND && window.RICO)));
  }
  async function play() {
    if (!(await load())) return false;
    const S = window.COVE_SOUND;
    if (!S.wanted) S.toggle(); else S.start();
    S.set({ place: "radio", radio: false, amb: 0.35 });   // the station's arrangement, the sea faint behind it
    R.waiting = !S.on;
    if (S.on) {
      if (!R.timer) { R.timer = setInterval(tick, 2000); R.next = performance.now() + 2500; R.n = 0; }
      if (!R.hello) { R.hello = true; S.sfx("jingle"); setTimeout(() => air(hello()), 900); }
    }
    show(); return S.on;
  }
  function stop() {
    const S = window.COVE_SOUND;
    if (S && S.wanted) S.toggle();
    clearInterval(R.timer); R.timer = 0; R.hello = false; R.waiting = false; caption(null); show();
  }

  /* ---------- what Rico says ---------- */
  const pick = a => a[Math.floor(Math.random() * a.length)];
  /* a key into RICO.L, or one of a set of interchangeable keys when rico.js has them */
  const key = k => (window.RICO.SETS && Array.isArray(RICO.SETS[k]) && RICO.SETS[k].length ? pick(RICO.SETS[k]) : k);
  const V = (k, v) => { const L = RICO.L, kk = key(k), s = L[kk] || L[k]; return s ? { t: v ? F(s, v) : T(s), v: v ? RICO.fill(s, v) : s } : null; };
  const Q = (s, v) => ({ t: v ? F(s, v) : T(s), v: null });
  const STATION = "This just in on Radio Coco, ninety-seven point three!";
  function hello() {
    const L = window.RICO.hud && RICO.hud();
    const hi = Array.isArray(L) && L.find(p => p && p[0] && /radio coco/i.test(p[0].v || ""));
    return hi || [{ t: T(STATION), v: STATION }];
  }
  function pool() {
    const L = typeof RICO.hud === "function" ? RICO.hud() : null;
    if (Array.isArray(L) && L.length) return L.filter(p => Array.isArray(p) && p.length);
    return ["fact", "song", "warm", "sam", "tips", "dedicate", "copy"].map(k => [V(k)]).filter(p => p[0]);
  }
  /* the chain weather, read the way the game reads it: the last blocks and the waiting transactions */
  const WX = { at: 0, line: null };
  function weather(done) {
    if (performance.now() - WX.at < 90000 && WX.line) return done(WX.line);
    const sim = !!(window.TauSim && TauSim.on);
    let ws; try { ws = sim ? TauSim.socket() : new WebSocket("wss://node.tauhud.com"); } catch (e) { return done(null); }
    const blocks = new Map(); let mem = null, fin = false;
    const finish = () => {
      if (fin) return; fin = true; try { ws.close(); } catch (e) {}
      const bs = [...blocks.values()].sort((a, b) => a.header.block_number - b.header.block_number).slice(-12);
      if (!bs.length) return done(null);
      const last = bs[bs.length - 1], y = String(last.header.block_number), ts = Number(last.header.timestamp) || 0;
      const age = ts ? Math.max(0, Date.now() / 1000 - (ts > 1e12 ? ts / 1000 : ts)) / 60 : 0;
      const txs = bs.reduce((n, b) => n + (b.transactions || []).length, 0);
      const rules = bs.filter(b => (b.transactions || []).some(tx => tx.operations && tx.operations["0"])).map(b => b.header.block_number);
      const wait = Array.isArray(mem) ? mem.length : mem && Array.isArray(mem.transactions) ? mem.transactions.length : mem && Array.isArray(mem.mempool) ? mem.mempool.length : 0;
      const out = [V(sim ? "wxSim" : "wxChain")];
      if (age > 10) out.push(V("fog"), Q("(last block {y}, {n} minutes ago)", { y, n: Math.round(age) }));
      else if (!txs) out.push(V("calm"), Q("({n} empty blocks, up to block {y})", { n: bs.length, y }));
      else out.push(V(txs <= bs.length / 2 ? "breeze" : "choppy"), Q("({n} txs in the last {m} blocks, up to block {y})", { n: txs, m: bs.length, y }));
      if (rules.length) out.push(V("rule"), Q("(block {y})", { y: String(rules[rules.length - 1]) }));
      out.push(...(wait ? [V("showers"), Q("({n} waiting)", { n: wait })] : [V("clear")]));
      WX.at = performance.now(); WX.line = out.filter(Boolean); done(WX.line);
    };
    const t = setTimeout(finish, 7000);
    ws.onopen = () => { ws.send("hello version=1"); setTimeout(() => { try { ws.send("getmempool"); ws.send("getblocks"); } catch (e) {} }, 200); };
    ws.onmessage = ev => {
      let m; try { m = JSON.parse(String(ev.data)); } catch (e) { return; }
      if (m.status !== "ok") return;
      if (m.command === "getmempool") mem = m.data;
      if ((m.command === "getblocks" || m.command === "getblockrange") && m.data && Array.isArray(m.data.blocks)) m.data.blocks.forEach(b => b && b.header && blocks.set(b.header.block_number, b));
      if (mem !== null && blocks.size) { clearTimeout(t); setTimeout(finish, 300); }
    };
    ws.onerror = () => { clearTimeout(t); finish(); };
  }
  function tick() {
    const S = window.COVE_SOUND;
    if (!S || !S.on || document.hidden || performance.now() < R.next) return;
    R.next = performance.now() + 60000;   // held until this line is over
    if (++R.n % 3 === 1) return weather(line => (line ? air(line) : (R.next = 0)));
    const L = pool(); if (!L.length) return;
    let k = Math.floor(Math.random() * L.length); if (k === R.last && L.length > 1) k = (k + 1) % L.length; R.last = k;
    air(L[k]);
  }
  /* on air: the line under the header while Rico says it; then music for a while */
  async function air(parts) {
    const S = window.COVE_SOUND; if (!S || !S.on) return;
    const text = parts.map(p => p.t).join(CJK ? "" : " ");
    caption(text);
    let secs = false; try { secs = await RICO.speak(parts, "rico"); } catch (e) {}
    const hold = (secs || Math.min(14, 4 + text.length / 18)) + 2;
    clearTimeout(R.capT); R.capT = setTimeout(() => caption(null), hold * 1000);
    R.next = performance.now() + hold * 1000 + 35000 + Math.random() * 35000;
  }
  function caption(text) {
    if (!R.cap) {
      R.cap = document.createElement("div"); R.cap.className = "tn-onair"; R.cap.setAttribute("role", "status"); R.cap.setAttribute("aria-live", "polite"); R.cap.hidden = true;
      R.cap.innerHTML = `<b translate="no">Radio Coco 97.3</b><span></span><button type="button" aria-label="Close">×</button>`;
      R.cap.querySelector("button").addEventListener("click", () => { R.cap.hidden = true; if (window.COVE_SOUND) COVE_SOUND.hush(); });
      document.body.append(R.cap);
    }
    if (!text) { R.cap.hidden = true; return; }
    R.cap.querySelector("span").textContent = text; R.cap.hidden = false;
  }

  /* ---------- clicks ---------- */
  function click(e) {
    e.stopPropagation();
    if (R.mode === "gazette") {   // the newspaper's own switch does the work; the radio follows it
      const b = document.getElementById("bSnd");
      if (b) b.click();
      setTimeout(() => { const on = store.get("gazette-sound") !== "off"; setAll(on); show(); }, 0);
      return;
    }
    if (R.mode === "rabbit") {
      const S = window.COVE_SOUND; if (!S) return;
      /* still waiting for its first touch (the glow): this press starts the sound, it does not turn it off */
      if (R.btn.classList.contains("wake") || (!S.on && S.wanted)) S.start(); else S.toggle();
      setAll(S.wanted); show(); return;
    }
    if (wanted() && !R.waiting) { setAll(false); stop(); return; }
    setAll(true); R.waiting = false; play();
  }
  /* a radio left on: it comes back with the first click or key on this page */
  function resume() {
    R.waiting = true; show();
    const go = () => { removeEventListener("pointerdown", go, true); removeEventListener("keydown", go, true); if (wanted()) play(); };
    addEventListener("pointerdown", go, true); addEventListener("keydown", go, true);
  }

  function mount(host, page, tip) {
    R.page = page; R.mode = page === "gazette" ? "gazette" : page === "rabbit" ? "rabbit" : "radio";
    const b = R.btn = document.createElement("button");
    b.type = "button"; b.className = "pill tn-radiob"; b.innerHTML = `${ICON}<span class="lbl">Radio Coco</span>`;
    if (tip) tip(b, TIP[R.mode]);
    b.addEventListener("click", click);
    host.append(b);
    if (R.mode === "gazette") window.addEventListener("gazette-sound", e => { setAll(!!e.detail); show(); });
    if (R.mode === "rabbit") setInterval(show, 1000);   // the game has its own sound button; follow it
    if (R.mode === "radio" && wanted()) resume();
    show();
  }
  window.TauRadio = { mount };
})();

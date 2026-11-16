/* The next testnet cruise, where every visitor sees it: a line on the door (first visit) and a chip in the HUD's header,
   right of Agorzilla. Both read the relay's timetable (node.tauhud.com/cruise, infra/relay/cruise.py brief()): the next
   call in the reader's own time with a countdown, and while a ship is in port that it sails now, how long is left and
   what it has sent. Nothing is written here: the ships, the extra calls and the off switch (CRUISE_ENABLED=0) live on the
   server, so a make-up call shows by itself and a switched-off fleet hides both. A surprise ship (the pirates) is never
   announced as next; once she is in port she shows like any other.
   The passengers are simulated, the transactions they send are real test transactions: every text says so. */
(function () {
  const NODE = "https://node.tauhud.com";
  const lang = (window.TauI18n && TauI18n.lang) || "en";
  const W = {
    en: {
      kNext: "Next testnet stress test", kSoon: "Testnet stress test soon", kLive: "Live now · testnet stress test", kWait: "Testnet stress test · waiting",
      when: "{d} {t} your time", today: "today", tomorrow: "tomorrow",
      inT: "in {d}", left: "{d} left", leaves: "leaves in {d}", arrives: "arrives in {d}",
      wait: "waits offshore until the testnet is calm",
      subNext: "{n} simulated passengers send real transactions to Tau Net for {m} minutes, to see how the testnet holds up.",
      subLive: "{a} simulated passengers ashore · {x} real test transactions sent so far · {r} refused by the chain",
      subWait: "The ship lands only on a calm testnet; it waits up to 10 minutes, else it sails on.",
      goLive: "Watch it live ›", goNext: "What it tests ›",
      chipNext: "Stress test in {d}", chipLive: "Stress test live · {d} left", chipWait: "Stress test waiting", shortLive: "Live · {d}",
      tip: "{s} docks at White Rabbit Key: simulated passengers pay in real test transactions on Tau Net, at most {p} a minute, so the chain is tested, not flooded.",
      tipLast: "Last call: {s}, {x} real test transactions sent, {r} refused.",
      tipGo: "Click to watch the island live while she is in port, otherwise the public logbook.",
      clock: "{h} h {m} min", day: "{d} d {h} h",
    },
    zh: {
      kNext: "下一次测试网压力测试", kSoon: "测试网压力测试即将开始", kLive: "正在进行 · 测试网压力测试", kWait: "测试网压力测试 · 等待中",
      when: "{d} {t}（你的当地时间）", today: "今天", tomorrow: "明天",
      inT: "{d} 后", left: "还剩 {d}", leaves: "{d} 后离港", arrives: "{d} 后到港",
      wait: "在海上等待测试网平稳下来",
      subNext: "{n} 位模拟乘客在 {m} 分钟内向 Tau Net 发送真实交易，看看测试网能否撑住。",
      subLive: "{a} 位模拟乘客已上岸 · 已发送 {x} 笔真实测试交易 · 链拒绝了 {r} 笔",
      subWait: "游轮只在测试网平稳时靠岸；最多等 10 分钟，否则继续航行。",
      goLive: "观看直播 ›", goNext: "它测试什么 ›",
      chipNext: "压力测试 {d} 后", chipLive: "压力测试进行中 · 还剩 {d}", chipWait: "压力测试等待中", shortLive: "进行中 · {d}",
      tip: "{s} 停靠 White Rabbit Key：模拟乘客用 Tau Net 上真实的测试交易付款，每分钟最多 {p} 笔，测试链而不淹没它。",
      tipLast: "上一次到港：{s}，发送了 {x} 笔真实测试交易，{r} 笔被拒绝。",
      tipGo: "点击：在港时观看岛屿直播，其余时间打开公开的航海日志。",
      clock: "{h} 小时 {m} 分", day: "{d} 天 {h} 小时",
    },
    ja: {
      kNext: "次のテストネット負荷テスト", kSoon: "まもなくテストネット負荷テスト", kLive: "実施中 · テストネット負荷テスト", kWait: "テストネット負荷テスト · 待機中",
      when: "{d} {t}（あなたの時刻）", today: "今日", tomorrow: "明日",
      inT: "あと {d}", left: "残り {d}", leaves: "あと {d} で出港", arrives: "あと {d} で入港",
      wait: "テストネットが落ち着くまで沖で待機中",
      subNext: "模擬乗客 {n} 人が {m} 分間、Tau Net に本物の取引を送り、テストネットが持ちこたえるかを確かめます。",
      subLive: "模擬乗客 {a} 人が上陸中 · 本物のテスト取引 {x} 件送信 · チェーンが拒否 {r} 件",
      subWait: "船はテストネットが落ち着いているときだけ上陸します。最大 10 分待ち、だめなら次へ向かいます。",
      goLive: "ライブで見る ›", goNext: "何をテストするか ›",
      chipNext: "負荷テストまで {d}", chipLive: "負荷テスト実施中 · 残り {d}", chipWait: "負荷テスト待機中", shortLive: "実施中 · {d}",
      tip: "{s} が White Rabbit Key に入港：模擬乗客が Tau Net 上の本物のテスト取引で支払います。1 分に最大 {p} 件、チェーンをあふれさせずにテストします。",
      tipLast: "前回の入港：{s}、本物のテスト取引 {x} 件送信、{r} 件拒否。",
      tipGo: "クリック：入港中は島のライブ、それ以外は公開の航海日誌。",
      clock: "{h}時間 {m}分", day: "{d}日 {h}時間",
    },
  };
  const w = W[lang] || W.en;
  const fill = (s, o) => s.replace(/\{(\w)\}/g, (_, k) => (o[k] != null ? o[k] : ""));
  const fmtN = n => Number(n || 0).toLocaleString(lang === "zh" ? "zh-CN" : lang === "ja" ? "ja-JP" : "en-US");
  const pad = n => String(n).padStart(2, "0");
  /* a span of time: days and hours far off, hours and minutes today, a ticking mm:ss in the last hour */
  const span = sec => {
    sec = Math.max(0, Math.round(sec));
    const d = Math.floor(sec / 86400), h = Math.floor(sec % 86400 / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60;
    if (d) return fill(w.day, { d, h });
    if (h) return fill(w.clock, { h, m });
    return pad(m) + ":" + pad(s);
  };
  const when = t => {
    const at = new Date(t * 1000), day = x => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const off = Math.round((day(at) - day(new Date())) / 864e5);
    let d;
    try { d = off === 0 ? w.today : off === 1 ? w.tomorrow : at.toLocaleDateString(lang === "zh" ? "zh-CN" : lang === "ja" ? "ja-JP" : "en-US", { weekday: "short" }); } catch (e) { d = ""; }
    return fill(w.when, { d, t: pad(at.getHours()) + ":" + pad(at.getMinutes()) });
  };
  const sum = o => (o && typeof o === "object" ? Object.values(o).reduce((a, b) => a + (Number(b) || 0), 0) : Number(o) || 0);
  const href = p => { const l = new URLSearchParams(location.search).get("lang"); return p + (l ? "?lang=" + encodeURIComponent(l) : ""); };

  /* ---------- the look: green, the HUD's one accent; it pulses only while a ship is in port ---------- */
  const css = `
.door-cruise { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 4px 14px; max-width: min(100%, 980px); margin: 0; padding: 9px 18px; border: 1px solid rgba(57,255,138,.4); border-radius: 14px; background: rgba(57,255,138,.05); color: var(--text); text-decoration: none; font: 400 13px/1.35 var(--display); }
.door-cruise:hover { border-color: var(--ok); background: rgba(57,255,138,.09); }
.door-cruise[hidden] { display: none; }
.door-cruise .dc-k { font: 600 11px var(--display); letter-spacing: .22em; text-transform: uppercase; color: var(--ok); }
.door-cruise .dc-k i { display: inline-block; width: 8px; height: 8px; margin: 0 8px 1px 0; border-radius: 50%; background: var(--ok); box-shadow: 0 0 8px var(--ok); vertical-align: middle; }
.door-cruise .dc-s { font: 600 15px var(--display); color: #fff; }
.door-cruise .dc-w { color: var(--dim); }
.door-cruise .dc-c { font: 600 18px var(--mono); color: var(--ok); font-variant-numeric: tabular-nums; }
.door-cruise .dc-go { font: 600 11px var(--display); letter-spacing: .12em; text-transform: uppercase; color: #fff; border: 1px solid var(--ok); border-radius: 999px; padding: 4px 12px; }
.door-cruise .dc-sub { flex-basis: 100%; text-align: center; font-size: 12px; color: var(--dim); }
.door-cruise.live { border-color: var(--ok); animation: dcGlow 2.4s ease-in-out infinite; }
.door-cruise.live .dc-k i, .chip.cruise.live .dot { animation: dcBlink 1.2s ease-in-out infinite; }
@keyframes dcGlow { 0%, 100% { box-shadow: 0 0 0 rgba(57,255,138,0); } 50% { box-shadow: 0 0 22px rgba(57,255,138,.28); } }
@keyframes dcBlink { 0%, 100% { opacity: 1; } 50% { opacity: .25; } }
.chip.cruise { text-decoration: none; cursor: pointer; border-color: rgba(57,255,138,.45); color: var(--text); }
.chip.cruise:hover { border-color: var(--ok); background: rgba(57,255,138,.08); }
.chip.cruise b { color: var(--ok); margin-left: 0; }
.chip.cruise .dot { display: inline-block; width: 7px; height: 7px; margin-right: 7px; border-radius: 50%; background: var(--ok); vertical-align: middle; }
.chip.cruise:not(.live) .dot { display: none; }
.chip.cruise .ship { width: 15px; height: 11px; margin: 0 7px 2px 0; vertical-align: middle; color: var(--ok); }
.chip.cruise.live .ship { display: none; }
.chip.cruise.live { border-color: var(--ok); background: rgba(57,255,138,.1); }
.chip.cruise[hidden] { display: none; }
@media (pointer: coarse) { .door-cruise { min-height: 44px; } .door-cruise .dc-go { padding: 8px 14px; } }
@media (max-width: 760px) { .door-cruise { padding: 8px 12px; gap: 2px 10px; } .door-cruise .dc-s { font-size: 14px; } .door-cruise .dc-c { font-size: 16px; } .door-cruise .dc-sub { font-size: 11px; } }
@media (prefers-reduced-motion: reduce) { .door-cruise.live, .door-cruise.live .dc-k i, .chip.cruise.live .dot { animation: none; } }
`;
  const st = document.createElement("style"); st.textContent = css; document.head.append(st);

  /* ---------- the two places ---------- */
  const mk = (tag, cls, html) => { const e = document.createElement(tag); e.className = cls; e.setAttribute("translate", "no"); if (html) e.innerHTML = html; return e; };
  const door = mk("a", "door-cruise", '<span class="dc-k"><i></i><span></span></span><span class="dc-s"></span><span class="dc-w"></span><span class="dc-c"></span><span class="dc-go"></span><span class="dc-sub"></span>');
  door.id = "doorCruise"; door.hidden = true;
  const SHIP_SVG = '<svg class="ship" viewBox="0 0 16 12" aria-hidden="true"><path d="M2 7h12l-2.2 3.4H4.2z M5 7V4h5l2 3 M7 4V1.5" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>';
  const chip = mk("a", "chip cruise", '<span class="dot" aria-hidden="true"></span>' + SHIP_SVG + '<b></b>');
  chip.id = "chipCruise"; chip.hidden = true;
  const q = (el, s) => el.querySelector(s);
  const set = (el, t) => { if (el.textContent !== t) el.textContent = t; };
  /* the door's line sits under the proof line; the chip in the header's free space after the "unofficial" notice, before the
     live chips, so it never pushes the Live/Simulation switch Agorzilla watches (nav.js may build the header after this
     file, so the chip finds its place again whenever it lost it) */
  const mount = () => {
    const proof = document.getElementById("doorProof");
    if (proof && door.parentNode !== proof.parentNode) proof.after(door);
    const un = document.querySelector("header.rail .unoff"), nav = document.querySelector("header.rail .tnav-r");
    if (slot === "nav" && nav) { if (nav.firstElementChild !== chip) nav.prepend(chip); }
    else if (un && chip.previousElementSibling !== un) un.after(chip);
  };

  let D = null, fetched = 0, fit = true;
  /* the chip may take only room the header has to spare: it never makes the header a line taller, and never leaves
     Agorzilla (who stands left of the Live/Simulation switch and keeps clear of the chip) without his spot. It tries the
     whole line, then only the time with the ship as its sign, first after the notice, then at the start of the menu's right
     side (Search, Follow, …); else it stays out of the header (the door still shows the
     cruise). Decided again on every resize and level change. */
  let room = "full", slot = "top";
  const fitAgz = () => {
    const rail = document.querySelector("header.rail"), a = document.getElementById("agz");
    if (!rail || !chip.parentNode) return;
    const place = () => { if (typeof window.placeAgz === "function") window.placeAgz(); };
    const seen = () => !!a && getComputedStyle(a).display !== "none";
    const look = () => ({ h: Math.round(rail.getBoundingClientRect().height), c: seen() && a.classList.contains("cramped") });
    room = "none"; render(); place(); const base = look();
    const ok = () => { place(); const n = look(); return n.h <= base.h && (!n.c || base.c); };
    for (const [sl, r] of [["top", "full"], ["top", "short"], ["nav", "full"], ["nav", "short"]]) { slot = sl; room = r; render(); if (ok()) return; }
    slot = "top"; room = "none"; render(); place();
  };
  addEventListener("resize", () => { fit = true; requestAnimationFrame(() => D && render()); });
  addEventListener("tau-level", () => { fit = true; requestAnimationFrame(() => D && render()); });
  const load = () => {
    const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), 8000);
    return fetch(NODE + "/cruise", { cache: "no-cache", signal: ctl.signal }).then(r => (r.ok ? r.json() : null))
      .then(j => { D = j && typeof j === "object" ? j : null; fetched = Date.now(); })
      .catch(() => {}).finally(() => clearTimeout(t));
  };

  /* what to show now: the ship in port, else the next call; nothing when the fleet is off or the relay has not answered */
  const state = () => {
    if (!D || D.enabled === false) return null;
    const now = Date.now() / 1000, v = D.now;
    if (v && v.name && v.phase !== "gone" && Number(v.end) > now) {
      if (v.phase === "approach") return { k: "soon", ship: v, to: Number(v.t0) - now };
      if (v.phase === "waiting") return { k: "wait", ship: v };
      return { k: "live", ship: v, to: Number(v.end) - now };
    }
    const n = D.next;
    if (n && n.name && Number(n.t0) > now) return { k: Number(n.t0) - now <= 3600 ? "soon" : "next", ship: n, to: Number(n.t0) - now };
    return null;
  };

  const render = () => {
    mount();
    const s = state();
    door.hidden = !s; chip.hidden = !s || room === "none";
    if (!s) return;
    const name = s.ship.name, ships = (D && D.ships) || {}, info = ships[s.ship.ship] || {};
    const per = (D.pace && D.pace[s.ship.ship]) || (D.limits && D.limits.per_min) || 12;
    const live = s.k === "live";
    door.classList.toggle("live", live); chip.classList.toggle("live", live);
    door.href = chip.href = href(live || s.k === "wait" ? "rabbit/" : "cruise/");
    set(q(door, ".dc-k span"), s.k === "live" ? w.kLive : s.k === "wait" ? w.kWait : s.k === "soon" ? w.kSoon : w.kNext);
    set(q(door, ".dc-s"), name);
    set(q(door, ".dc-w"), s.k === "wait" ? w.wait : live ? (s.ship.phase === "boarding" ? fill(w.leaves, { d: span(s.to) }) : "") : when(s.ship.t0));
    set(q(door, ".dc-c"), s.k === "wait" ? "" : live ? (s.ship.phase === "boarding" ? "" : fill(w.left, { d: span(s.to) })) : fill(w.inT, { d: span(s.to) }));
    set(q(door, ".dc-go"), live || s.k === "wait" ? w.goLive : w.goNext);
    const sub = live ? fill(w.subLive, { a: fmtN(s.ship.ashore), x: fmtN(sum(s.ship.sent)), r: fmtN(s.ship.refused) })
      : s.k === "wait" ? w.subWait : fill(w.subNext, { n: fmtN(info.passengers || s.ship.passengers || ""), m: info.minutes || 90 });
    set(q(door, ".dc-sub"), sub);
    q(door, ".dc-w").hidden = !q(door, ".dc-w").textContent; q(door, ".dc-c").hidden = !q(door, ".dc-c").textContent;
    set(q(chip, "b"), s.k === "wait" ? w.chipWait : live ? fill(room === "short" ? w.shortLive : w.chipLive, { d: span(s.to) }) : room === "short" ? span(s.to) : fill(w.chipNext, { d: span(s.to) }));
    if (fit) { fit = false; fitAgz(); }
    const L = D.last, lastName = L && (L.name || (ships[L.ship] || {}).name);
    const last = L && lastName && L.landed && L.id !== s.ship.visit ? fill(w.tipLast, { s: lastName, x: fmtN(sum(L.sent)), r: fmtN(sum(L.refused)) }) : "";
    const tip = [fill(w.tip, { s: name, p: per }), !live && s.k !== "wait" ? when(s.ship.t0) + " · " + fill(w.inT, { d: span(s.to) }) : sub, last, w.tipGo].filter(Boolean).join("\n");
    if (chip.dataset.full !== tip) { chip.dataset.full = tip; door.dataset.full = tip; door.setAttribute("aria-label", name + ". " + sub); }
  };

  /* the relay is asked every 5 min, every minute in the last hour and while a ship is in port; the countdown ticks every
     second when it shows seconds, else every 20 s. A hidden tab asks nothing. */
  const tick = () => {
    const s = state(), near = s && (s.k !== "next");
    if (!document.hidden && Date.now() - fetched > (near ? 60e3 : 300e3)) load().then(render);
    else render();
    setTimeout(tick, s && (s.k === "soon" || (s.k === "live" && s.to < 3600)) ? 1000 : 20000);
  };
  const go = () => { mount(); load().then(render); setTimeout(tick, 1000); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go); else go();
  document.addEventListener("visibilitychange", () => { if (!document.hidden && Date.now() - fetched > 60e3) load().then(render); });
})();

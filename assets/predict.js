/* Tau HUD forecasts: guess the next round of the simulation before it starts.

   Every hour the simulated chain proposes one rule change at hh:20 and the visitors vote on it until hh:27 (sim.js, the
   ballot in infra/relay/simvotes.py). Before the ballot opens anyone can guess two things: does the change come into
   force at hh:30, and how many visitors vote. The relay scores each round from its own tally (infra/relay/simpredict.py)
   and keeps a board per UTC day, the day of the simulated chain. Same anonymous identity as the ballot (TauSim.me()),
   nothing to sign up for, no free text.

   TauPredict.open()  opens the sheet (also #predict in the address)      TauPredict.on  true where the simulation is loaded */
(() => {
  "use strict";
  if (!window.TauSim || !TauSim.me) { window.TauPredict = { on: false, open() {} }; return; }   // the HUD may show the simulation before tau-mode is set, so TauSim.on is not required
  const RELAY = "https://node.tauhud.com", AMBER = "#ffb13b";
  const BUCKETS = ["none", "1–2", "3–5", "6–10", "11–20", "21 or more"];
  const WHAT = { stake: "proof of stake takes over", fixed: "the fixed validator list returns", admit: "a new validator joins", remove: "a validator leaves",
    super: "two thirds must agree", major: "more than half must agree" };
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const localTime = new Date().getTimezoneOffset() !== 0;
  const hm = x => { const d = new Date(x * 1000); return localTime ? d.toTimeString().slice(0, 5) : d.toISOString().slice(11, 16); };
  const when = x => localTime ? `${hm(x)} (${new Date(x * 1000).toISOString().slice(11, 16)} UTC)` : `${hm(x)} UTC`;
  const mmss = s => { s = Math.max(0, Math.round(s)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };

  /* the visitor: the ballot's anonymous identity (sim.js); names and colours in the page language from the same lists */
  const me = () => TauSim.me();
  const nameOf = row => (TauSim.nameOf ? TauSim.nameOf(row.a, row.b) : row.name) || "A visitor";
  const colourOf = row => (TauSim.colourOf ? TauSim.colourOf(row.c) : null) || "#c8c8d0";

  /* the round open for guesses: the next rule change of the day's programme that is not proposed yet */
  function nextRound() {
    const now = Date.now() / 1000;
    const u = (TauSim.upcoming ? TauSim.upcoming() : []).find(x => x.kind !== "restart" && x.proposed_ts > now);
    return u ? { ...u, k: Math.round((u.proposed_at - 150) / 450), item: `slot:${Math.round((u.proposed_at - 150) / 450)}` } : null;
  }

  const S = { data: null, err: "", pick: { come: null, n: null }, sending: false, timer: null, el: null, last: 0 };
  async function load() {
    try {
      const r = await fetch(`${RELAY}/sim/predictions?voter=${me().token}`, { cache: "no-store" });
      if (!r.ok) throw new Error(r.status);
      S.data = await r.json(); S.err = ""; S.last = Date.now();
    } catch (e) { S.err = "The forecast board is not reachable right now. Your guess can wait: try again in a minute."; }
    render();
  }
  async function send() {
    const round = nextRound(), id = TauSim.me(true);
    if (!round || S.pick.come == null || S.pick.n == null || S.sending) return;
    S.sending = true; render();
    try {
      const q = new URLSearchParams({ item: round.item, voter: id.token, a: id.a, b: id.b, c: id.c, come: S.pick.come ? "1" : "0", n: S.pick.n });
      const r = await fetch(`${RELAY}/sim/predict?${q}`, { cache: "no-store" }), j = await r.json().catch(() => ({}));
      if (!r.ok) S.err = r.status === 409 ? "Too late for this round: the visitors' vote has opened. The next round opens for guesses right away." : r.status === 429 ? "Too many guesses from your address. Wait a moment and try again." : "The guess did not arrive. Try again in a minute.";
      else { S.data = j; S.err = ""; }
    } catch (e) { S.err = "The guess did not arrive. Try again in a minute."; }
    S.sending = false; render();
  }

  /* ---------- the sheet ---------- */
  const CSS = `
.tp-modal{--tp-deck:#121214;--tp-glass:rgba(16,16,18,.9);--tp-line:rgba(255,255,255,.09);--tp-hair:rgba(255,255,255,.18);--tp-dim:#8a8a94;--tp-text:#ebebee;--tp-amber:${AMBER};--tp-display:"Sora","Manrope","Segoe UI",sans-serif;--tp-mono:"JetBrains Mono",ui-monospace,Menlo,monospace;
position:fixed;inset:0;z-index:85;background:rgba(3,8,13,.78);display:flex;align-items:center;justify-content:center;padding:24px;box-sizing:border-box;color:var(--tp-text);font:13px/1.5 var(--tp-mono);text-align:left}
.tp-modal[hidden]{display:none}.tp-modal *,.tp-modal *::before,.tp-modal *::after{box-sizing:border-box}
.tp-sheet{position:relative;width:min(1100px,100%);max-height:100%;overflow:auto;scrollbar-width:thin;background:var(--tp-deck);border:1px solid rgba(255,177,59,.55);border-radius:10px;padding:16px;box-shadow:0 30px 80px rgba(0,0,0,.7)}
.tp-head{display:flex;align-items:center;gap:12px;margin:0 40px 12px 0;flex-wrap:wrap}
.tp-head h2{margin:0;font:600 15px var(--tp-display);letter-spacing:.2em;text-transform:uppercase;color:#fff}
.tp-tag{font:600 11px var(--tp-display);letter-spacing:.14em;text-transform:uppercase;color:#fff;border:1px solid rgba(255,177,59,.7);border-radius:999px;padding:3px 9px;background:repeating-linear-gradient(135deg,rgba(255,177,59,.14) 0 10px,rgba(255,177,59,.03) 10px 20px)}
.tp-head p{margin:0;color:var(--tp-dim);font-size:12px;flex:1 1 280px}
.tp-close{position:absolute;top:10px;right:10px;width:36px;height:36px;border-radius:50%;border:1px solid var(--tp-hair);background:var(--tp-deck);color:#fff;cursor:pointer;font:15px var(--tp-display)}
.tp-close:hover{background:#fff;color:#000}
.tp-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr) minmax(0,1fr);gap:12px;align-items:stretch}
.tp-panel{background:var(--tp-glass);border:1px solid var(--tp-line);border-radius:6px;padding:12px;min-width:0;display:flex;flex-direction:column;gap:8px}
.tp-panel h3{margin:0;font:600 12px var(--tp-display);letter-spacing:.2em;text-transform:uppercase;color:#fff;display:flex;justify-content:space-between;gap:8px}
.tp-panel h3 small{color:var(--tp-dim);font:400 11px var(--tp-mono);letter-spacing:0;text-transform:none}
.tp-what{font:600 15px/1.35 var(--tp-display);color:#fff}.tp-what::first-letter{text-transform:uppercase}
.tp-dim{color:var(--tp-dim);font-size:12px}.tp-dim b{color:var(--tp-text);font-weight:600}
.tp-clock{font:600 22px var(--tp-mono);color:var(--tp-amber);letter-spacing:.02em}
.tp-q{font:600 13px var(--tp-display);color:#fff;margin-top:2px}
.tp-opts{display:flex;flex-wrap:wrap;gap:6px}
.tp-opt{min-height:36px;padding:6px 12px;border-radius:999px;border:1px solid var(--tp-hair);background:transparent;color:var(--tp-text);font:500 12px var(--tp-mono);cursor:pointer}
.tp-opt:hover{border-color:#fff;color:#fff}.tp-opt[aria-pressed="true"]{background:var(--tp-amber);border-color:var(--tp-amber);color:#000;font-weight:600}
.tp-opt:disabled{opacity:.45;cursor:default}
.tp-send{align-self:flex-start;min-height:38px;padding:8px 16px;border-radius:999px;border:1px solid var(--tp-amber);background:transparent;color:var(--tp-amber);font:600 12px var(--tp-display);letter-spacing:.14em;text-transform:uppercase;cursor:pointer}
.tp-send:hover:not(:disabled){background:var(--tp-amber);color:#000}.tp-send:disabled{opacity:.45;cursor:default}
.tp-ok{color:var(--tp-text);font-size:12px;border-left:2px solid var(--tp-amber);padding-left:8px}
.tp-err{color:var(--tp-text);font-size:12px;border-left:2px solid var(--tp-hair);padding-left:8px}
.tp-board{list-style:none;margin:0;padding:0;display:grid;gap:2px}
.tp-board li{display:grid;grid-template-columns:2.2em 12px minmax(0,1fr) auto;gap:8px;align-items:center;padding:3px 6px;border-radius:4px;font-size:12px}
.tp-board li.rd{grid-template-columns:3.4em 0 minmax(0,1fr) auto;padding:2px 0}.tp-board li.me{background:rgba(255,177,59,.12);outline:1px solid rgba(255,177,59,.45)}
.tp-board .r{color:var(--tp-dim);text-align:right}.tp-board .d{width:10px;height:10px;border-radius:50%}
.tp-board .p{font-weight:600;color:#fff;white-space:nowrap}.tp-board .p small{color:var(--tp-dim);font-weight:400}
.tp-res{display:grid;gap:4px;font-size:12px;border-top:1px solid var(--tp-line);padding-top:8px;margin-top:auto}
.tp-res b{color:#fff;font-weight:600}
.tp-bars{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:3px 8px;font-size:11px;color:var(--tp-dim);align-items:center}
.tp-bars i{display:block;height:6px;border-radius:3px;background:rgba(255,177,59,.6);min-width:2px}
.tp-me{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--tp-dim)}.tp-me b{color:#fff}.tp-me i{width:10px;height:10px;border-radius:50%;display:inline-block}
@media (max-width:900px){.tp-grid{grid-template-columns:1fr}.tp-modal{padding:8px}.tp-opt{min-height:44px}.tp-send{min-height:44px}}`;

  function build() {
    if (S.el) return S.el;
    const st = document.createElement("style"); st.textContent = CSS; document.head.append(st);
    const el = document.createElement("div");
    el.className = "tp-modal"; el.hidden = true; el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "true"); el.setAttribute("aria-label", "Guess the next round");   // i18n.js translates the label
    el.innerHTML = `<div class="tp-sheet"><button type="button" class="tp-close" aria-label="Close">✕</button><div id="tpBody"></div></div>`;
    el.addEventListener("click", e => {
      if (e.target === el || e.target.closest(".tp-close")) return close();
      const o = e.target.closest("[data-come],[data-n]");
      if (o && !o.disabled) { if (o.dataset.come != null) S.pick.come = o.dataset.come === "1"; else S.pick.n = +o.dataset.n; render(); return; }
      if (e.target.closest(".tp-send")) send();
    });
    document.addEventListener("keydown", e => { if (e.key === "Escape" && !el.hidden) close(); });
    document.body.append(el); S.el = el; return el;
  }
  let lastFocus = null;
  function open() {
    const el = build(); lastFocus = document.activeElement; el.hidden = false; S.err = "";
    load(); clearInterval(S.timer);
    S.timer = setInterval(() => { if (Date.now() - S.last > 30000) load(); else render(); }, 1000);
    el.querySelector(".tp-close").focus();
  }
  function close() {
    if (!S.el) return; S.el.hidden = true; clearInterval(S.timer);
    if (location.hash === "#predict") try { history.replaceState(history.state, "", location.pathname + location.search); } catch (e) {}
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  /* L(english, {name: html}): the sentence in the page language (assets/i18n/zh/predict.js), escaped, its {placeholders} filled with ready HTML */
  const L = (s, v) => { let out = esc(window.TauI18n && TauI18n.lang !== "en" ? TauI18n.t(s) : s); for (const k in v || {}) out = out.split("{" + k + "}").join(v[k]); return out; };
  const B = x => `<b>${esc(x)}</b>`;
  let lastHtml = "";
  function render() {
    if (!S.el || S.el.hidden) return;
    const now = Date.now() / 1000, round = nextRound(), d = S.data, id = me();
    const rounds = d && d.rounds || [], mineNow = round && rounds.find(r => r.item === round.item);
    const mine = mineNow && mineNow.mine;
    if (mine && S.pick.come == null && S.pick.n == null) S.pick = { come: mine.come, n: mine.n };
    // the round being voted on right now (guesses closed) and the newest scored one
    const live = (TauSim.upcoming ? TauSim.upcoming() : []).find(x => x.kind !== "restart" && x.proposed_ts <= now && x.at_ts > now);
    const liveItem = live ? `slot:${Math.round((live.proposed_at - 150) / 450)}` : null;
    const ballot = live && TauSim.ballots ? ((TauSim.ballots() || {}).items || {})[liveItem] : null;
    const liveRound = liveItem && rounds.find(r => r.item === liveItem);
    const scored = rounds.filter(r => r.result).slice(-1)[0];
    const what = u => L(WHAT[u.kind] || u.title);

    // column 1: what happens next and when guesses close
    let c1;
    if (round) {
      c1 = `<h3>${L("Next round")} <small>${esc(when(round.proposed_ts))}</small></h3>
        <div class="tp-what">${what(round)}</div>
        <div class="tp-dim">${L("Proposed at {x}, then the visitors vote until {y}. More no than yes and it is dropped; a tie or no votes and it comes into force at {z} as planned.", { x: B(hm(round.proposed_ts)), y: B(hm(round.proposed_ts + 420)), z: B(hm(round.at_ts)) })}</div>
        <div class="tp-dim">${L("Guesses close when the vote opens, in")}</div><div class="tp-clock">${mmss(round.proposed_ts - now)}</div>`;
    } else c1 = `<h3>${L("Next round")}</h3><div class="tp-what">${L("No more rounds today")}</div><div class="tp-dim">${L("The simulated chain starts over at midnight UTC and so does the board. The first round of the new day is proposed at 00:20 UTC.")}</div>`;
    if (live) c1 += `<div class="tp-res"><b>${L("Voting now: {x}", { x: what(live) })}</b><span>${ballot ? L("Yes {x} · No {y} · until {z}", { x: ballot.yes || 0, y: ballot.no || 0, z: esc(hm(live.proposed_ts + 420)) }) : L("Until {z}", { z: esc(hm(live.proposed_ts + 420)) })}</span>${liveRound && liveRound.guesses ? `<span>${L("{x} guessed this round, {y} of them that it comes.", { x: liveRound.guesses, y: liveRound.come_yes })}</span>` : ""}</div>`;

    // column 2: the guess
    const dis = !round || S.sending ? " disabled" : "";
    const pressed = (k, v) => S.pick[k] === v ? "true" : "false";
    let c2 = `<h3>${L("Your guess")} <small>${round ? L("round {x}", { x: round.k + 1 }) : ""}</small></h3>
      <div class="tp-me"><i style="background:${esc(id.colour || colourOf(id))}"></i>${L("You guess as {x}", { x: B(nameOf(id)) })}</div>
      <div class="tp-q">${round ? L("Does it come into force at {x}?", { x: esc(hm(round.at_ts)) }) : L("Does it come into force?")}</div>
      <div class="tp-opts"><button type="button" class="tp-opt" data-come="1" aria-pressed="${pressed("come", true)}"${dis}>${L("Yes, it comes")}</button><button type="button" class="tp-opt" data-come="0" aria-pressed="${pressed("come", false)}"${dis}>${L("No, it is dropped")}</button></div>
      <div class="tp-q">${L("How many visitors vote on it?")}</div>
      <div class="tp-opts">${BUCKETS.map((b, i) => `<button type="button" class="tp-opt" data-n="${i}" aria-pressed="${pressed("n", i)}"${dis}>${L(b)}</button>`).join("")}</div>
      <button type="button" class="tp-send"${!round || S.pick.come == null || S.pick.n == null || S.sending ? " disabled" : ""}>${mine ? L("Change my guess") : L("Lock in my guess")}</button>`;
    if (S.err) c2 += `<div class="tp-err">${L(S.err)}</div>`;
    else if (mine && round) c2 += `<div class="tp-ok">${L(mine.come ? "Locked in: it comes, {w} voting. You can change it until {x}." : "Locked in: it is dropped, {w} voting. You can change it until {x}.", { w: L(BUCKETS[mine.n]), x: esc(hm(round.proposed_ts)) })}</div>`;
    c2 += `<div class="tp-dim">${L("Points: {x} for yes or no, {y} for the right number of voters, {z} for the group next to it. Vote yourself in the round too: it counts like everyone's.", { x: B(2), y: B(3), z: B(1) })}</div>`;
    if (mineNow && mineNow.guesses > 1) {
      const max = Math.max(1, ...mineNow.buckets);
      c2 += `<div class="tp-bars">${mineNow.buckets.map((n, i) => `<span>${L(BUCKETS[i])}</span><i style="width:${(n / max * 100).toFixed(0)}%"></i><span>${n}</span>`).join("")}</div><div class="tp-dim">${L("{x} guesses so far, {y} say it comes.", { x: mineNow.guesses, y: mineNow.come_yes })}</div>`;
    }

    // column 3: the day's board and the last result
    const board = d && d.board || [], meRow = d && d.me;
    let c3 = `<h3>${L("Today's forecasters")} <small>${d ? L("{x} playing · UTC day", { x: d.forecasters }) : ""}</small></h3>`;
    if (!d && !S.err) c3 += `<div class="tp-dim">${L("Loading the board…")}</div>`;
    else if (!board.length) c3 += `<div class="tp-dim">${L("Nobody has guessed today yet. Lock in a guess and you lead the board: it starts over at midnight UTC together with the simulated chain.")}</div>`;
    else c3 += `<ol class="tp-board">${board.slice(0, 10).map(r => `<li class="${meRow && r.rank === meRow.rank ? "me" : ""}"><span class="r">${r.rank}</span><span class="d" style="background:${esc(colourOf(r))}"></span><span>${esc(nameOf(r))}</span><span class="p">${r.points} <small>${L("pts · {x}/{y} rounds", { x: r.scored, y: r.rounds })}</small></span></li>`).join("")}</ol>`
      + (meRow && meRow.rank > 10 ? `<div class="tp-dim">${L("You: {x} with {y} points.", { x: B("#" + meRow.rank), y: meRow.points })}</div>` : "");
    if (d && d.yesterday && d.yesterday.board && d.yesterday.board.length) {
      const y = d.yesterday.board[0];
      c3 += `<div class="tp-res"><b>${L("Yesterday's best")}</b><span>${L("{x} with {y} points.", { x: esc(nameOf(y)), y: y.points })}</span></div>`;
    }
    // column 1, below: today's finished rounds, newest first, with the visitor's points
    const done = rounds.filter(r => r.result).slice(-5).reverse(), dayT = d ? Date.parse(d.day + "T00:00:00Z") / 1000 : 0;
    if (done.length) c1 += `<div class="tp-res"><b>${L("Today's rounds")}</b><ol class="tp-board">${done.map(x => {
      const r = x.result, t = dayT + (150 + 450 * +x.item.slice(5)) * 8;
      const how = r.outcome === "none" ? "a tie or no votes, so the plan stood" : r.outcome === "yes" ? "more yes than no" : "more no than yes";
      return `<li class="rd" title="${esc(L(how))}"><span class="r">${esc(hm(t))}</span><span></span><span>${L(r.come ? "came, {x} voted" : "dropped, {x} voted", { x: r.voters })}</span><span class="p">${x.mine ? "+" + x.mine.points : "—"}</span></li>`; }).join("")}</ol>${meRow ? `<span>${L("Your day: {x} points from {y} rounds, place {z}.", { x: B(meRow.points), y: meRow.scored, z: B("#" + meRow.rank) })}</span>` : ""}</div>`;
    const html = `<div class="tp-head"><span class="tp-tag">${L("Simulation")}</span><h2>${L("Guess the next round")}</h2><p>${L("Every hour the visitors vote on one simulated rule change. Guess the outcome before the vote opens.")}</p></div>
      <div class="tp-grid"><section class="tp-panel">${c1}</section><section class="tp-panel">${c2}</section><section class="tp-panel">${c3}</section></div>`;
    if (html === lastHtml) return; lastHtml = html;
    const body = S.el.querySelector("#tpBody"), f = document.activeElement, key = f && f.dataset ? (f.dataset.come != null ? "come" + f.dataset.come : f.dataset.n != null ? "n" + f.dataset.n : f.classList.contains("tp-send") ? "send" : "") : "";
    body.innerHTML = html;
    if (key) { const g = key === "send" ? body.querySelector(".tp-send") : body.querySelector(key[0] === "c" ? `[data-come="${key.slice(4)}"]` : `[data-n="${key.slice(1)}"]`); if (g) g.focus(); }
  }

  /* Chinese and Japanese: this sheet's dictionary is loaded on demand, the sheet draws again once it is there */
  if (window.TauI18n && TauI18n.lang !== "en") {
    const s = document.createElement("script"); s.src = new URL("i18n/" + TauI18n.lang + "/predict.js", document.currentScript ? document.currentScript.src : location.href).href;
    s.onload = () => { lastHtml = ""; render(); }; document.head.append(s);
  }

  window.TauPredict = { on: true, open, close, nextRound };
  const fromHash = () => { if (location.hash === "#predict") open(); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fromHash); else fromHash();
  window.addEventListener("hashchange", fromHash);
  document.addEventListener("click", e => { const a = e.target.closest("[data-predict]"); if (a) { e.preventDefault(); open(); } });
})();

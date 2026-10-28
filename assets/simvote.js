/* Tau HUD simulation: the visitors' vote on the hourly rule change, as a strip any page can show (HUD bar, Proposals).

   TauVote.strip(u)   HTML for an upcoming entry of TauSim.upcoming() that carries a ballot: the question, Yes / No,
                      the tally, the visitor's own name and colour; after the close, what the visitors decided
   TauVote.bind(el)   handles the Yes / No clicks inside el (once per element)
   Needs assets/sim.js. Styles are added once; the strip uses the simulation's amber, the visitor's colour only on its dot. */
(() => {
  "use strict";
  if (!window.TauSim) return;
  const EVENT = { stake: "proof of stake takes over", fixed: "the fixed validator list returns", admit: "a new validator joins", remove: "a validator leaves",
    super: "two thirds must agree", major: "more than half must agree" };
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const hhmm = x => { const d = new Date(x * 1000), loc = d.toTimeString().slice(0, 5), utc = d.toISOString().slice(11, 16); return new Date().getTimezoneOffset() ? `${loc} (${utc} UTC)` : `${utc} UTC`; };
  const mins = x => { const m = Math.ceil((x - Date.now() / 1000) / 60); return m <= 1 ? "in 1 min" : `in ${m} min`; };
  const MSG = { closed: "The vote has closed.", limit: "Too many votes from your network on this one.", rate: "Too fast. Try again in a few seconds.", offline: "The vote server is out of reach right now. Your vote did not count.", bad: "That did not work.", unknown: "This vote is not open." };
  const css = document.createElement("style");
  css.textContent = `.tv { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; font: 12px/1.4 var(--mono, "JetBrains Mono", monospace); letter-spacing: 0; text-transform: none; color: #ffb13b; }
.tv .tv-q { font: 600 12px/1.35 var(--display, Sora, sans-serif); color: #fff; }
.tv.tv button[data-vote] { font: 600 11px var(--display, Sora, sans-serif); letter-spacing: .14em; text-transform: uppercase; background: transparent; border: 1px solid rgba(255,177,59,.6); color: #ffb13b; border-radius: 999px; padding: 4px 12px; min-height: 26px; cursor: pointer; }
.tv.tv button[data-vote]:hover, .tv.tv button[data-vote]:focus-visible { background: rgba(255,177,59,.18); }
.tv.tv button[data-vote][aria-pressed="true"] { background: #ffb13b; border-color: #ffb13b; color: #000; }
.tv .tv-t { color: #fff; } .tv .tv-t b { font-weight: 700; }
.tv .tv-me { color: rgba(255,255,255,.7); white-space: nowrap; } .tv .tv-me i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; vertical-align: 0; }
.tv .tv-msg { color: #fff; font-style: normal; } .tv .tv-msg:empty { display: none; }
@media (max-width: 700px) { .tv.tv button[data-vote] { min-height: 44px; padding: 4px 16px; } .tv { font-size: 11px; } }`;
  document.head.append(css);

  function strip(u) {
    const b = u && u.ballot; if (!b || b.opens == null) return "";
    const what = EVENT[u.kind] || u.short || u.title, me = TauSim.me(), t = Date.now() / 1000;
    const tally = `<span class="tv-t"><b>${b.yes}</b> yes · <b>${b.no}</b> no</span>`;
    const who = `<span class="tv-me"><i style="background:${esc(me.colour)}"></i>You vote as ${esc(me.name)}</span>`;
    if (b.open) return `<div class="tv" data-item="${esc(b.item)}"><span class="tv-q">Your call: ${esc(what)}?</span>`
      + `<button type="button" data-vote="1" aria-pressed="${b.mine === 1}">Yes</button><button type="button" data-vote="0" aria-pressed="${b.mine === 0}">No</button>`
      + `${tally}<span>· voting closes ${mins(b.closes)}, the majority decides at ${hhmm(u.at_ts)}</span>${who}<em class="tv-msg" role="status"></em></div>`;
    if (t < b.opens || t >= u.at_ts) return "";
    const out = b.outcome || "none";
    const said = out === "yes" ? `The visitors said yes (${b.yes} to ${b.no}): the validators agree, ${esc(what)} at ${hhmm(u.at_ts)}.`
      : out === "no" ? `The visitors said no (${b.no} to ${b.yes}): the validators hold back, the change is dropped at ${hhmm(u.at_ts)} and the old rules stand.`
      : b.yes + b.no ? `A tie (${b.yes} to ${b.no}): the validators go ahead as planned, ${esc(what)} at ${hhmm(u.at_ts)}.`
      : `No visitor voted: the validators go ahead as planned, ${esc(what)} at ${hhmm(u.at_ts)}.`;
    return `<div class="tv" data-item="${esc(b.item)}"><span class="tv-q">${said}</span></div>`;
  }
  function bind(el) {
    if (!el || el.dataset.tvBound) return; el.dataset.tvBound = "1";
    el.addEventListener("click", async e => {
      const btn = e.target.closest("[data-vote]"), box = btn && btn.closest(".tv"); if (!box) return;
      e.stopPropagation(); e.preventDefault();
      const yes = btn.dataset.vote === "1", msg = box.querySelector(".tv-msg");
      box.querySelectorAll("[data-vote]").forEach(x => x.setAttribute("aria-pressed", String(x === btn)));
      const r = await TauSim.vote(box.dataset.item, yes);
      if (msg) msg.textContent = r && r.ok ? (yes ? "Counted: yes." : "Counted: no.") : MSG[(r && r.error) || "bad"] || MSG.bad;
      if (r && r.item) { const t = box.querySelector(".tv-t"); if (t) t.innerHTML = `<b>${r.item.yes}</b> yes · <b>${r.item.no}</b> no`; if (!r.ok && r.item.mine != null) box.querySelectorAll("[data-vote]").forEach(x => x.setAttribute("aria-pressed", String(Number(x.dataset.vote) === r.item.mine))); }
      else if (!(r && r.ok)) box.querySelectorAll("[data-vote]").forEach(x => x.setAttribute("aria-pressed", "false"));
    });
  }
  /* the ballot that matters now: open, or closed and waiting for the change to take effect */
  function current() {
    const t = Date.now() / 1000;
    return (TauSim.upcoming ? TauSim.upcoming() : []).find(u => u.ballot && u.ballot.opens != null && t >= u.ballot.opens && t < u.at_ts) || null;
  }
  window.TauVote = { strip, bind, current, sig: u => u && u.ballot ? JSON.stringify([u.ballot.item, u.ballot.open, u.ballot.yes, u.ballot.no, u.ballot.mine, u.ballot.outcome, Math.ceil((u.ballot.closes - Date.now() / 1000) / 60)]) : "" };
})();

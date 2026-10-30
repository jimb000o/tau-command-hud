/* Tau HUD: one way for every page to show that it is still reading the chain from our node.
   A page that loads the chain block range by block range calls
     TauChainLoad.progress(read, total)   while blocks arrive (total = blocks the chain has),
     TauChainLoad.done()                  once every block is in.
   Meanwhile a thin amber bar runs along the top of the window, a small label at the bottom says
   "Reading the chain · 1,900 of 3,204 blocks", and the page's numbers (its <main>, or anything marked
   data-chainwait) stay dimmed so a half-read chain never looks like the answer. When the last block is in,
   the bar fills, the label says "Up to date" and the numbers come up together. Nothing is stored. */
(() => {
  "use strict";
  if (window.TauChainLoad) return;
  const css = `
.chainload-bar { position: fixed; left: 0; top: 0; height: 2px; width: 100%; z-index: 90; pointer-events: none; background: rgba(255,177,59,.12); opacity: 0; transition: opacity .5s; }
.chainload-bar i { display: block; height: 100%; width: 0; background: #ffb13b; box-shadow: 0 0 8px rgba(255,177,59,.6); transition: width .4s ease-out; }
.chainload-tag { position: fixed; left: 50%; bottom: 14px; transform: translate(-50%, 8px); z-index: 90; pointer-events: none; opacity: 0;
  display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px; border-radius: 999px; border: 1px solid rgba(255,177,59,.45);
  background: rgba(9,9,10,.92); color: #ebebee; font: 12px/1.3 "JetBrains Mono", ui-monospace, monospace; white-space: nowrap; transition: opacity .4s, transform .4s; }
.chainload-tag b { font-weight: 600; color: #ffb13b; }
.chainload-tag::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: #ffb13b; box-shadow: 0 0 6px #ffb13b; animation: chainload-pulse 1.2s ease-in-out infinite; }
html.chain-reading .chainload-bar, html.chain-reading .chainload-tag, html.chain-settled .chainload-bar, html.chain-settled .chainload-tag { opacity: 1; }
html.chain-reading .chainload-tag, html.chain-settled .chainload-tag { transform: translate(-50%, 0); }
html.chain-settled .chainload-bar i { background: #39ff8a; box-shadow: 0 0 8px rgba(57,255,138,.6); }
html.chain-settled .chainload-tag { border-color: rgba(57,255,138,.45); }
html.chain-settled .chainload-tag b { color: #39ff8a; }
html.chain-settled .chainload-tag::before { background: #39ff8a; box-shadow: 0 0 6px #39ff8a; animation: none; }
.wrap > main, [data-chainwait] { transition: opacity .6s ease, filter .6s ease; }
html.chain-reading .wrap > main, html.chain-reading [data-chainwait] { opacity: .38; filter: saturate(.2); }
@keyframes chainload-pulse { 50% { opacity: .35; } }
@media (prefers-reduced-motion: reduce) { .chainload-bar i, .chainload-tag, .wrap > main, [data-chainwait] { transition: none; } .chainload-tag::before { animation: none; } }
@media (max-width: 700px) { .chainload-tag { bottom: 10px; font-size: 11px; } }`;
  let bar = null, tag = null, text = null, settleT = null, reading = false;
  const html = document.documentElement;
  const nf = new Intl.NumberFormat("en-US");
  function mount() {
    if (bar || !document.body) return;
    const st = document.createElement("style"); st.id = "chainload-css"; st.textContent = css; document.head.append(st);
    bar = document.createElement("div"); bar.className = "chainload-bar"; bar.setAttribute("aria-hidden", "true"); bar.innerHTML = "<i></i>";
    tag = document.createElement("div"); tag.className = "chainload-tag"; tag.setAttribute("role", "status"); tag.setAttribute("aria-live", "polite");
    tag.innerHTML = `<b>Reading the chain</b><span></span>`;
    text = tag.querySelector("span");
    document.body.append(bar, tag);
  }
  function progress(read, total) {
    mount(); if (!bar) return;
    clearTimeout(settleT); html.classList.remove("chain-settled");
    if (!reading) { reading = true; html.classList.add("chain-reading"); tag.querySelector("b").textContent = "Reading the chain"; }
    const r = Math.max(0, Math.round(read || 0)), t = Math.max(r, Math.round(total || 0));
    bar.firstChild.style.width = t ? `${Math.min(100, r / t * 100).toFixed(1)}%` : "4%";
    text.textContent = t ? `${nf.format(r)} of ${nf.format(t)} blocks` : "asking our node…";
  }
  function done() {
    if (!reading) return;
    reading = false; mount();
    html.classList.remove("chain-reading"); html.classList.add("chain-settled");
    bar.firstChild.style.width = "100%";
    tag.querySelector("b").textContent = "Up to date"; text.textContent = "every block read";
    clearTimeout(settleT); settleT = setTimeout(() => html.classList.remove("chain-settled"), 1400);
  }
  // the page stopped reading without finishing (node offline, old relay): drop the state quietly
  function stop() { reading = false; clearTimeout(settleT); html.classList.remove("chain-reading", "chain-settled"); }
  window.TauChainLoad = { progress, done, stop, get reading() { return reading; } };
})();

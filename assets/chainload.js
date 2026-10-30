/* Tau HUD: one way for every page to show that it is still reading the chain from our node.
   A page that loads the chain block range by block range calls
     TauChainLoad.progress(read, total)   while blocks arrive (total = blocks the chain has),
     TauChainLoad.done()                  once every block is in.
   Meanwhile a band runs across the top of the window: "Reading the chain", "1,900 of 3,204 blocks", a
   percentage, roughly how long is left, and a line saying what the page does meanwhile, over a thick amber
   bar. A page that builds itself up as the blocks arrive sets TauChainLoad.live = true before its first
   progress(): its numbers stay visible and count up, and the line says so. Any other page keeps its <main>
   (or anything marked data-chainwait) dimmed, so a half-read chain never looks like the answer. When the
   last block is in, the band turns green ("Up to date") and slides away. Nothing is stored. */
(() => {
  "use strict";
  if (window.TauChainLoad) return;
  const css = `
.chainload-band { position: fixed; left: 0; right: 0; top: 0; z-index: 90; pointer-events: none; transform: translateY(-110%); transition: transform .45s ease;
  background: rgba(9,9,10,.95); border-bottom: 1px solid rgba(255,177,59,.5); box-shadow: 0 6px 24px rgba(0,0,0,.55); color: #ebebee; }
.chainload-band .in { display: flex; align-items: center; gap: 10px 18px; flex-wrap: wrap; padding: 10px 20px 12px; font: 13px/1.35 "JetBrains Mono", ui-monospace, monospace; }
.chainload-band .dot { width: 9px; height: 9px; border-radius: 50%; background: #ffb13b; box-shadow: 0 0 8px #ffb13b; animation: chainload-pulse 1.2s ease-in-out infinite; flex: none; }
.chainload-band b { font: 600 13px "Sora", "Manrope", "Segoe UI", sans-serif; letter-spacing: .16em; text-transform: uppercase; color: #ffb13b; }
.chainload-band .n { font: 600 20px/1 "Sora", "Manrope", "Segoe UI", sans-serif; color: #fff; font-variant-numeric: tabular-nums; }
.chainload-band .pc { color: #ffb13b; font-variant-numeric: tabular-nums; }
.chainload-band .eta { color: #9a9aa2; font-variant-numeric: tabular-nums; }
.chainload-band .why { color: #9a9aa2; flex: 1 1 260px; text-align: right; }
.chainload-band .bar { height: 4px; background: rgba(255,177,59,.14); }
.chainload-band .bar i { display: block; height: 100%; width: 0; background: #ffb13b; box-shadow: 0 0 10px rgba(255,177,59,.7); transition: width .4s ease-out; }
html.chain-reading .chainload-band, html.chain-settled .chainload-band { transform: none; }
html.chain-settled .chainload-band { border-bottom-color: rgba(57,255,138,.5); }
html.chain-settled .chainload-band b, html.chain-settled .chainload-band .pc { color: #39ff8a; }
html.chain-settled .chainload-band .dot { background: #39ff8a; box-shadow: 0 0 8px #39ff8a; animation: none; }
html.chain-settled .chainload-band .bar i { background: #39ff8a; box-shadow: 0 0 10px rgba(57,255,138,.7); }
.wrap > main, [data-chainwait] { transition: opacity .6s ease, filter .6s ease; }
html.chain-reading:not(.chain-live) .wrap > main, html.chain-reading [data-chainwait] { opacity: .38; filter: saturate(.2); }
@keyframes chainload-pulse { 50% { opacity: .35; } }
@media (prefers-reduced-motion: reduce) { .chainload-band, .chainload-band .bar i, .wrap > main, [data-chainwait] { transition: none; } .chainload-band .dot { animation: none; } }
@media (max-width: 700px) { .chainload-band .in { padding: 8px 16px 10px; gap: 4px 12px; } .chainload-band .why { text-align: left; flex-basis: 100%; font-size: 12px; } .chainload-band .n { font-size: 17px; } }`;
  let band = null, settleT = null, reading = false, t0 = 0, r0 = 0;
  const html = document.documentElement;
  const nf = new Intl.NumberFormat("en-US");
  const api = { progress, done, stop, live: false, get reading() { return reading; } };
  const $ = s => band.querySelector(s);
  function mount() {
    if (band || !document.body) return;
    const st = document.createElement("style"); st.id = "chainload-css"; st.textContent = css; document.head.append(st);
    band = document.createElement("div"); band.className = "chainload-band"; band.setAttribute("role", "status"); band.setAttribute("aria-live", "polite");
    band.innerHTML = `<div class="in"><span class="dot"></span><b>Reading the chain</b><span class="n"></span><span class="pc"></span><span class="eta"></span><span class="why"></span></div><div class="bar"><i></i></div>`;
    document.body.append(band);
  }
  // how long is left, from the pace so far; only once there is a pace to go by
  function eta(r, t) {
    const s = (Date.now() - t0) / 1000, rate = (r - r0) / Math.max(s, 0.001);
    if (s < 1.5 || rate <= 0 || r >= t) return "";
    const left = (t - r) / rate;
    return left < 2 ? "almost there" : left < 90 ? `about ${Math.round(left)} s left` : `about ${Math.round(left / 60)} min left`;
  }
  function progress(read, total) {
    mount(); if (!band) return;
    clearTimeout(settleT); html.classList.remove("chain-settled"); html.classList.toggle("chain-live", !!api.live);
    const r = Math.max(0, Math.round(read || 0)), t = Math.max(r, Math.round(total || 0));
    if (!reading) {
      reading = true; t0 = Date.now(); r0 = r; html.classList.add("chain-reading");
      $("b").textContent = "Reading the chain";
      $(".why").textContent = api.live ? "Every number on this page counts up as the blocks arrive." : "This page fills in once every block is read.";
    }
    $(".bar i").style.width = t ? `${Math.min(100, r / t * 100).toFixed(1)}%` : "3%";
    $(".n").textContent = t ? `${nf.format(r)} of ${nf.format(t)} blocks` : "asking our node…";
    $(".pc").textContent = t ? `${Math.floor(r / t * 100)}%` : "";
    $(".eta").textContent = t ? eta(r, t) : "";
  }
  function done() {
    if (!reading) return;
    reading = false; mount();
    html.classList.remove("chain-reading"); html.classList.add("chain-settled");
    $(".bar i").style.width = "100%";
    $("b").textContent = "Up to date"; $(".n").textContent = "every block read"; $(".pc").textContent = "100%"; $(".eta").textContent = ""; $(".why").textContent = "";
    clearTimeout(settleT); settleT = setTimeout(() => html.classList.remove("chain-settled", "chain-live"), 1600);
  }
  // the page stopped reading without finishing (node offline, old relay): drop the state quietly
  function stop() { reading = false; clearTimeout(settleT); html.classList.remove("chain-reading", "chain-settled", "chain-live"); }
  window.TauChainLoad = api;
})();

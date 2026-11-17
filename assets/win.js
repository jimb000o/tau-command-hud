/* The moment you did something: one shared way to say it on every tauhud.com page (14.11.2026).
   A short card rises at the bottom of the screen: a green ring closes, a check draws itself, then one line says what you
   did, one line what it means, and the proof (the block it is in, the transaction) for those who want it. The element
   you just used glows once. It says only what happened: no points, no streaks, no countdowns, nothing to lose.

   By level (html[data-level], set by nav.js):
     new  the plain-word line on what it means; the card stays 8 s
     mid  that line and the proof chip; 7 s
     pro  one compact line with the proof; 4 s, no glow
   The first time of a kind in this browser (key) gets a "first time" tag and a few sparks. Reduced motion: it just appears.

   TauWin.moment({ title, meaning, proof, href, at, key, once, go })   title: what you did · meaning: what it means · proof: "block #12 · tx ab12…"
                                                             go: { href, text, onclick } a button for the next step (the card then stays 14 s)
                                                             href: where the proof is · at: the element to glow · key: kind of first
   TauWin.glow(el)                                           the element glows once
   TauWin.count(el, to, ms)                                  a number counts up to its new value */
(() => {
  "use strict";
  if (window.TauWin) return;
  const T = s => (window.TauI18n ? TauI18n.t(s) : s);
  const still = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
  const level = () => document.documentElement.dataset.level || "mid";
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const CSS = `
.twin{position:fixed;left:50%;bottom:max(18px,env(safe-area-inset-bottom));z-index:2147483000;display:flex;align-items:center;gap:14px;box-sizing:border-box;width:max-content;max-width:min(560px,calc(100vw - 32px));
  padding:12px 12px 12px 14px;border:1px solid rgba(57,255,138,.45);border-radius:14px;background:rgba(6,14,10,.96);color:#e8f3ec;box-shadow:0 18px 50px -12px rgba(0,0,0,.8),0 0 0 1px rgba(0,0,0,.4),0 0 40px -14px rgba(57,255,138,.55);
  font:400 13px/1.4 "Sora",system-ui,sans-serif;transform:translate(-50%,0);animation:twin-in .5s cubic-bezier(.2,1.3,.4,1) both}
.twin.out{animation:twin-out .35s ease-in forwards}
@keyframes twin-in{from{opacity:0;transform:translate(-50%,24px) scale(.96)}}
@keyframes twin-out{to{opacity:0;transform:translate(-50%,16px)}}
.twin .tw-mark{position:relative;flex:none;width:40px;height:40px}
.twin .tw-mark svg{width:40px;height:40px;overflow:visible}
.twin .tw-ring{fill:none;stroke:#39ff8a;stroke-width:2.5;stroke-linecap:round;stroke-dasharray:1 1;stroke-dashoffset:1;transform:rotate(-90deg);transform-origin:50% 50%;animation:twin-draw .55s .1s ease-out forwards}
.twin .tw-ck{fill:none;stroke:#39ff8a;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:1 1;stroke-dashoffset:1;animation:twin-draw .3s .55s ease-out forwards}
.twin .tw-fill{fill:rgba(57,255,138,.12);transform-origin:50% 50%;animation:twin-pop .5s .5s cubic-bezier(.2,1.6,.4,1) both}
@keyframes twin-draw{to{stroke-dashoffset:0}}
@keyframes twin-pop{from{transform:scale(.3);opacity:0}}
.twin .tw-sp{position:absolute;left:50%;top:50%;width:5px;height:5px;margin:-2.5px;border-radius:50%;background:#39ff8a;box-shadow:0 0 8px #39ff8a;opacity:0;animation:twin-spark .8s .6s ease-out forwards}
@keyframes twin-spark{0%{opacity:1;transform:translate(0,0) scale(1)}100%{opacity:0;transform:translate(var(--x),var(--y)) scale(.4)}}
.twin .tw-txt{min-width:0;flex:1}
.twin .tw-t{display:block;font-weight:600;color:#fff;font-size:14px}
.twin .tw-tag{display:inline-block;margin-left:8px;padding:1px 7px;border:1px solid rgba(57,255,138,.55);border-radius:99px;color:#39ff8a;font-size:11px;font-weight:500;letter-spacing:.04em;vertical-align:1px}
.twin .tw-m{display:block;color:#b9cbbf;margin-top:2px}
.twin .tw-p{display:inline-block;margin-top:4px;font:500 11.5px/1.3 "JetBrains Mono",ui-monospace,monospace;color:#39ff8a;text-decoration:none;border-bottom:1px dotted rgba(57,255,138,.5)}
.twin .tw-p:hover{color:#fff}
.twin .tw-go{display:inline-flex;align-items:center;min-height:36px;margin-top:8px;padding:6px 14px;border-radius:8px;background:#39ff8a;color:#000;font:600 12px/1.2 "Sora",system-ui,sans-serif;letter-spacing:.04em;text-decoration:none}
.twin .tw-go:hover{background:#fff}
.twin.pro .tw-go{margin:0 0 0 10px;min-height:30px;padding:4px 10px}
.twin .tw-x{flex:none;align-self:flex-start;width:44px;height:44px;margin:-8px -8px -8px 0;border:0;border-radius:10px;background:none;color:#8aa596;font-size:20px;line-height:1;cursor:pointer}
.twin .tw-x:hover{color:#fff;background:rgba(255,255,255,.06)}
.twin.pro{padding:8px 8px 8px 12px;gap:10px}.twin.pro .tw-mark,.twin.pro .tw-mark svg{width:26px;height:26px}.twin.pro .tw-t{display:inline;font-size:13px}.twin.pro .tw-p{margin:0 0 0 10px}
.tw-glow{animation:twin-glow 1.3s ease-out}
@keyframes twin-glow{0%{box-shadow:0 0 0 0 rgba(57,255,138,.75),0 0 0 0 rgba(57,255,138,.35)}100%{box-shadow:0 0 0 14px rgba(57,255,138,0),0 0 40px 6px rgba(57,255,138,0)}}
.tw-count{animation:twin-num .9s ease-out}
@keyframes twin-num{0%{color:#39ff8a;text-shadow:0 0 12px rgba(57,255,138,.8)}}
@media (prefers-reduced-motion:reduce){.twin,.twin *,.tw-glow,.tw-count{animation:none!important}.twin .tw-ring,.twin .tw-ck{stroke-dashoffset:0}.twin .tw-sp{display:none}}
@media (max-width:599px){.twin{gap:10px;padding:10px 8px 10px 12px;font-size:12.5px;width:calc(100vw - 32px);bottom:calc(72px + env(safe-area-inset-bottom))}.twin .tw-mark,.twin .tw-mark svg{width:32px;height:32px}}`;
  function css() { if (document.getElementById("twin-css")) return; const s = document.createElement("style"); s.id = "twin-css"; s.textContent = CSS; document.head.appendChild(s); }
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  let card = null, timer = null;
  function close() {
    if (!card) return;
    const c = card; card = null; clearTimeout(timer);
    if (still()) return c.remove();
    c.classList.add("out"); setTimeout(() => c.remove(), 360);
  }
  function glow(el) {
    if (!el || !el.classList || still()) return;
    el.classList.remove("tw-glow"); void el.offsetWidth; el.classList.add("tw-glow");
    setTimeout(() => el.classList.remove("tw-glow"), 1400);
  }
  function seenKey(key) { try { return !!(JSON.parse(store.get("tauhud-firsts") || "{}") || {})[key]; } catch (e) { return false; } }
  function first(key) {
    if (!key) return false;
    let seen = {}; try { seen = JSON.parse(store.get("tauhud-firsts") || "{}") || {}; } catch (e) {}
    if (seen[key]) return false;
    seen[key] = new Date().toISOString().slice(0, 10); store.set("tauhud-firsts", JSON.stringify(seen));
    return true;
  }
  function moment(o) {
    o = o || {}; css();
    if (o.once && o.key && seenKey(o.key)) return null;   // a moment that belongs to one time only (a finished walk-through)
    const lv = level(), isFirst = first(o.key);
    close();
    const c = document.createElement("div");
    c.className = "twin" + (lv === "pro" ? " pro" : "");
    c.setAttribute("role", "status"); c.setAttribute("aria-live", "polite");
    const sparks = isFirst && lv !== "pro" ? Array.from({ length: 10 }, (_, k) => { const a = k / 10 * Math.PI * 2, r = 26 + (k % 3) * 6; return `<i class="tw-sp" style="--x:${Math.round(Math.cos(a) * r)}px;--y:${Math.round(Math.sin(a) * r)}px;animation-delay:${.55 + (k % 4) * .04}s"></i>`; }).join("") : "";
    const proof = o.proof && lv !== "new" ? (o.href ? `<a class="tw-p" href="${esc(o.href)}">${esc(o.proof)} →</a>` : `<span class="tw-p">${esc(o.proof)}</span>`) : "";
    const meaning = o.meaning && lv !== "pro" ? `<span class="tw-m">${esc(o.meaning)}</span>` : "";
    const go = o.go && o.go.href ? `<a class="tw-go" href="${esc(o.go.href)}">${esc(o.go.text)}</a>` : "";
    c.innerHTML = `<span class="tw-mark"><svg viewBox="0 0 40 40" aria-hidden="true"><circle class="tw-fill" cx="20" cy="20" r="17"/><circle class="tw-ring" cx="20" cy="20" r="17" pathLength="1"/><path class="tw-ck" d="M12.5 20.5l5 5L28 14.5" pathLength="1"/></svg>${sparks}</span>`
      + `<span class="tw-txt"><span class="tw-t">${esc(o.title)}${isFirst ? `<span class="tw-tag">${esc(T("first time"))}</span>` : ""}</span>${meaning}${proof}${go ? (lv === "pro" ? "" : "<br>") + go : ""}</span>`
      + `<button type="button" class="tw-x" aria-label="${esc(T("Close"))}">×</button>`;
    c.querySelector(".tw-x").onclick = close;
    if (go && o.go.onclick) c.querySelector(".tw-go").addEventListener("click", o.go.onclick);
    document.body.appendChild(c); card = c;
    if (lv !== "pro") glow(o.at);
    let left = go ? 14000 : lv === "pro" ? 4000 : lv === "new" ? 8000 : 7000;
    const run = () => { clearTimeout(timer); timer = setTimeout(close, left); };
    c.onmouseenter = () => clearTimeout(timer); c.onmouseleave = () => { left = 2500; run(); };
    run();
    return c;
  }
  // a number counts up to its new value (the text keeps its grouping: 100,000)
  function count(el, to, ms = 900) {
    if (!el) return;
    const fmt = n => Math.round(n).toLocaleString("en-US");
    const from = Number(String(el.textContent).replace(/[^\d.-]/g, "")) || 0;
    if (still() || !isFinite(to) || from === to) { el.textContent = fmt(to); return; }
    el.classList.remove("tw-count"); void el.offsetWidth; el.classList.add("tw-count");
    const t0 = performance.now();
    const step = t => { const k = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - k, 3); el.textContent = fmt(from + (to - from) * e); if (k < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  }
  document.addEventListener("keydown", e => { if (e.key === "Escape" && card) close(); });
  window.TauWin = { moment, glow, count, close };
})();

/* Power-on: the crew terminal starts like a machine before the game shows. A CRT line opens, the ROM checks its
   parts (a few lines on a return visit), then the picture tears and the real screen glitches in underneath.

   - Runs on every load, first visit about 3 s, return visit about 1.5 s. Any click, tap or key jumps to the glitch.
   - The lines are the terminal's own fiction, except two that read this browser: whether a test wallet is here, and
     the node the game talks to. Nothing is asked from the network.
   - prefers-reduced-motion, a background tab, an automated browser or ?intro=0: no power-on. ?intro=1 forces it.
   - In the cabin (scene.js) it plays on the ship's screen, after the camera has sat down.
   - game.js waits for window.NoMemoPower before it opens the first-visit door or the ?boot screen. */
(() => {
  const root = document.documentElement, q = new URLSearchParams(location.search);
  const REDUCED = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const force = q.get("intro") === "1";
  if (!force && (q.get("intro") === "0" || REDUCED || navigator.webdriver || document.hidden)) { window.NoMemoPower = Promise.resolve(); return; }
  const get = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  let seen = false; try { const s = JSON.parse(get("tauhud-nomemo") || "null"); seen = !!(s && s.booted); } catch (e) { }
  const wallet = !!get("tauhud-wallet-key");
  const lang = (window.TauI18n && TauI18n.lang) || "en";
  const HINT = { en: "tap or any key: skip", zh: "点击或按任意键跳过", ja: "タップまたは任意のキーでスキップ" };
  root.classList.add("nm-power");

  let done, skipped = false;
  window.NoMemoPower = new Promise(r => { done = r; });
  /* the clock stands still while the cabin camera is still moving to the desk */
  const sleep = ms => new Promise(r => {
    let left = ms, t0 = performance.now();
    const tick = () => { const now = performance.now(); if (!root.classList.contains("cab-intro")) left -= now - t0; t0 = now; if (skipped || left <= 0) r(); else setTimeout(tick, 16); };
    tick();
  });
  const mk = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const dots = (k, v) => (k + " ").padEnd(15, ".") + " " + v;

  function start() {
    const box = document.getElementById("power") || document.body.appendChild(mk("div"));
    box.id = "power"; box.setAttribute("aria-hidden", "true"); box.replaceChildren();
    const noise = mk("canvas", "pw-noise"), txt = mk("div", "pw-txt"), crt = mk("i", "pw-crt"), band = mk("i", "pw-band"), hint = mk("span", "pw-hint", HINT[lang] || HINT.en);
    noise.width = 160; noise.height = 90;
    box.append(noise, txt, crt, band, mk("i", "pw-scan"), hint);
    const g = noise.getContext("2d"), img = g.createImageData(160, 90);
    const fizz = setInterval(() => { const d = img.data; for (let i = 0; i < d.length; i += 4) { const v = Math.random() * 255 | 0; d[i] = d[i + 2] = v * .7; d[i + 1] = v; d[i + 3] = 255; } g.putImageData(img, 0, 0); }, 60);
    const line = (t, cls) => { const p = mk("p", cls, t); txt.append(p); return p; };

    let ended = false;
    const finish = () => {
      if (ended) return; ended = true;
      clearInterval(fizz); removeEventListener("keydown", skip, true); removeEventListener("pointerdown", skip, true);
      root.classList.remove("nm-power", "nm-glitch-in"); box.remove(); done();
    };
    const skip = e => { if (skipped) return; skipped = true; if (e && e.type === "keydown" && e.key !== "Tab") e.preventDefault(); };
    addEventListener("keydown", skip, true); addEventListener("pointerdown", skip, true);
    setTimeout(finish, 9000);   // whatever happens, the game is never held longer than this

    (async () => {
      /* 1 · the tube warms: a line, then the picture */
      box.classList.add("pw-on"); await sleep(520); box.classList.remove("pw-on"); box.classList.add("pw-lit");
      /* 2 · the ROM checks its parts */
      if (!skipped) {
        line("BSQ-7 CREW TERMINAL      ROM 4.1", "pw-h");
        line("the Black Sequence · no memo, no names", "pw-d"); await sleep(seen ? 160 : 320);
        if (!seen) {
          line(dots("CPU", "OK")); await sleep(120);
          const mem = line(dots("MEMORY", "0K"));
          for (let k = 0; k <= 65536 && !skipped; k += 4096) { mem.textContent = dots("MEMORY", k + "K" + (k === 65536 ? " OK" : "")); await sleep(28); }
          line(dots("CLOCK", "OK")); await sleep(120);
        }
        line(dots("KEYSTORE", wallet ? "1 test wallet · this browser" : "empty · made at the first contract")); await sleep(seen ? 140 : 220);
        line(dots("MODEM", "node.tauhud.com")); await sleep(seen ? 120 : 200);
        if (!seen) { line(dots("CHAIN", "Tau Testnet Alpha")); await sleep(200); line(dots("MEMO FIELD", "not found"), "pw-w"); await sleep(320); }
        const bar = line("", "pw-bar"), n = 22;
        for (let i = 0; i <= n && !skipped; i++) { bar.textContent = "loading NO MEMO  [" + "█".repeat(i) + "·".repeat(n - i) + "]"; await sleep(seen ? 14 : 30); }
        await sleep(seen ? 120 : 260);
      }
      /* 3 · the picture tears and the real screen glitches in under it */
      skipped = false;   // the tear always plays, short after a skip
      box.classList.add("pw-glitch"); hint.remove();
      await sleep(170);
      root.classList.add("nm-glitch-in"); box.classList.add("pw-out");
      await sleep(820);
      finish();
    })();
  }
  if (document.body) start(); else document.addEventListener("DOMContentLoaded", start, { once: true });
})();

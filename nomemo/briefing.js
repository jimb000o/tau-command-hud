/* The contract briefing: how a contract works, as a short animated film on the crew terminal's screen, in the style
   of the power-on (poweron.js / poweron.css). Six scenes: the contract comes in, the draft (six fields, no memo), the
   signature in this browser, the way to the chain, the chain's answer, the trace.

   - Plays once before the first contract (game.js, S.seen.brief), and again with the command `briefing`.
   - Each scene runs by itself (about 5 s); click, tap, Space or → goes on, ← goes back, Esc ends it.
   - prefers-reduced-motion: the same scenes without glitches and moving parts.
   - Every line is in the page's dictionaries (assets/i18n/<lang>/nomemo.js); nothing here asks the network.
   window.NoMemoBriefing.play({ start }) → a promise that settles when the film is over. */
(() => {
  const REDUCED = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const T = s => (window.TauI18n ? TauI18n.t(s) : s);
  const mk = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const row = (k, v, cls) => { const p = mk("p", "bf-f" + (cls ? " " + cls : "")); p.append(mk("span", "bf-k", T(k)), mk("b", null, T(v))); return p; };
  const hex = n => { let s = ""; for (let i = 0; i < n; i++) s += "0123456789abcdef"[Math.random() * 16 | 0]; return s; };

  const SCENES = [
    { title: "Incoming", text: "The crew sends you contracts. Each one is a real transaction on Tau Testnet Alpha, from your own test wallet.",
      draw: v => { const c = mk("div", "bf-card"); c.append(mk("p", "bf-ch", T("CONTRACT 1 · Make your mark")), row("from", "the Quartermaster"), row("task", "Pay 1 test AGRS to the crew’s drop."), row("trace", "a few blocks")); v.append(c); } },
    { title: "The draft", text: "A transaction is six fields, signed. There is no memo field: what you mean, you say in the amount.",
      draw: v => { const c = mk("div", "bf-card bf-rows");
        for (const [k, x] of [["from", "your test wallet"], ["to", "the drop"], ["amount", "1"], ["fee limit", "the most you pay"], ["seq", "your next number, taken once"], ["expiry", "after it: refused"]]) c.append(row(k, x));
        c.append(row("memo", "none", "bf-memo")); v.append(c); } },
    { title: "Signed here", text: "Your key is made in this browser and signs here. It never leaves it.",
      draw: v => { const c = mk("div", "bf-card bf-sign"), h = mk("p", "bf-hex", hex(48)); c.append(mk("p", "bf-ch", T("signing with your key")), h, mk("p", "bf-ok", T("signed · BLS"))); v.append(c);
        if (!REDUCED) { let i = 0; const t = setInterval(() => { h.textContent = hex(48); if (++i > 18 || !h.isConnected) clearInterval(t); }, 70); } } },
    { title: "To the chain", text: "Our node passes it on to the live test chain. Everybody plays the same chain, right now.",
      draw: v => { const r = mk("div", "bf-route");
        for (const [i, x] of ["this browser", "node.tauhud.com", "Tau Testnet Alpha"].entries()) { if (i) r.append(mk("i", "bf-wire")); r.append(mk("span", "bf-hop", T(x))); }
        const b = mk("div", "bf-blocks"); for (let i = 0; i < 6; i++) b.append(mk("i")); v.append(r, b); } },
    { title: "The answer", text: "The chain answers with a code. Some contracts want a yes. Some want a no, for the right reason.",
      draw: v => { const r = mk("div", "bf-ans"); r.append(mk("p", "bf-yes", T("✓ accepted · sealed in a block")), mk("p", "bf-no", "✕ " + T("refused") + " · FEE_LIMIT_TOO_LOW")); v.append(r); } },
    { title: "The trace", text: "Every contract has a deadline in blocks. Beat the block clock and you gain standing; a finished chapter pays your share back.",
      draw: v => { const t = mk("div", "bf-trace"); t.append(mk("i")); v.append(t, mk("p", "bf-tick", T("block clock running"))); } },
  ];

  let open = null;
  function play(opt) {
    if (open) return open;
    const start = opt && opt.start;
    open = new Promise(done => {
      const box = mk("div", "bf" + (REDUCED ? " bf-calm" : "")); box.setAttribute("role", "dialog"); box.setAttribute("aria-label", T("Contract briefing"));
      const noise = mk("canvas", "pw-noise"); noise.width = 160; noise.height = 90;
      const bar = mk("div", "bf-bar"), head = mk("p", "bf-head"), stage = mk("div", "bf-stage"), cap = mk("p", "bf-cap"), ctl = mk("div", "bf-ctl");
      for (let i = 0; i < SCENES.length; i++) bar.append(mk("i"));
      const back = mk("button", "bf-btn ghost", "‹"), next = mk("button", "bf-btn", ""), skip = mk("button", "bf-btn ghost", T("skip"));
      for (const b of [back, next, skip]) b.type = "button";
      back.setAttribute("aria-label", T("back")); ctl.append(back, skip, next);
      box.append(noise, bar, head, stage, cap, mk("i", "pw-scan"), ctl);
      document.body.append(box);
      const g = noise.getContext("2d"), img = g.createImageData(160, 90);
      const fizz = REDUCED ? 0 : setInterval(() => { const d = img.data; for (let i = 0; i < d.length; i += 4) { const x = Math.random() * 255 | 0; d[i] = d[i + 2] = x * .7; d[i + 1] = x; d[i + 3] = 255; } g.putImageData(img, 0, 0); }, 70);
      let at = -1, timer = 0;
      const end = () => { clearTimeout(timer); clearInterval(fizz); removeEventListener("keydown", key, true); box.classList.add("bf-gone"); setTimeout(() => box.remove(), REDUCED ? 0 : 320); open = null; done(); };
      const show = i => {
        if (i < 0) i = 0; if (i >= SCENES.length) return end();
        clearTimeout(timer); at = i; const s = SCENES[i];
        box.classList.remove("bf-cut"); void box.offsetWidth; if (!REDUCED) box.classList.add("bf-cut");
        bar.querySelectorAll("i").forEach((x, k) => { x.className = k < i ? "on" : k === i ? "now" : ""; });
        head.textContent = T("CONTRACT BRIEFING") + "  " + (i + 1) + "/" + SCENES.length + "  ·  " + T(s.title);
        stage.replaceChildren(); s.draw(stage); cap.textContent = T(s.text);
        back.disabled = i === 0; next.textContent = i === SCENES.length - 1 ? T(start ? "Start the contract" : "close") : T("next") + " ›";
        timer = setTimeout(() => show(at + 1), i === SCENES.length - 1 ? 12000 : 5600);
      };
      const key = e => {
        if (e.key === "Escape") { e.preventDefault(); end(); }
        else if (e.key === "ArrowRight" || e.key === " " || e.key === "Enter") { e.preventDefault(); e.stopPropagation(); show(at + 1); }
        else if (e.key === "ArrowLeft") { e.preventDefault(); show(at - 1); }
      };
      addEventListener("keydown", key, true);
      next.onclick = e => { e.stopPropagation(); show(at + 1); };
      back.onclick = e => { e.stopPropagation(); show(at - 1); };
      skip.onclick = e => { e.stopPropagation(); end(); };
      box.addEventListener("click", () => show(at + 1));
      show(0); next.focus({ preventScroll: true });
    });
    return open;
  }
  window.NoMemoBriefing = { play };
})();

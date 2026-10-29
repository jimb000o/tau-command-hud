/* The Daily Consensus: the world around the paper. A café window on a 1920s city street at eight
   in the morning, drawn here in the visitor's browser (no photographs, no recordings), in the
   paper's sepia, soft and dark enough that the page stays the brightest thing on the screen.
   Outside, streetcars come and go and people walk to work; the café can be heard on request. */
(() => {
  const desk = document.getElementById("desk"); if (!desk) return;
  if (/[?&]scene=off\b/.test(location.search)) return;
  const layer = cls => { const c = document.createElement("canvas"); c.className = "scene " + cls; c.setAttribute("aria-hidden", "true"); desk.insertBefore(c, desk.querySelector(".stage")); return c; };
  const BG = layer("bg"), LIVE = layer("live"), ROOM = layer("room"), STEAM = layer("steam"), FX = layer("fx");
  const still = () => matchMedia("(prefers-reduced-motion: reduce)").matches || desk.clientWidth < 900;
  let CUP = null;

  /* a seeded random, so the street looks the same on every visit */
  const rnd = s => () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  /* sepia ramp: 0 = deep shadow, 1 = morning haze */
  const STOPS = [[14, 11, 8], [42, 33, 23], [92, 74, 51], [168, 140, 98], [226, 201, 152]];
  const tone = (t, a = 1) => {
    t = Math.max(0, Math.min(1, t)) * (STOPS.length - 1); const i = Math.min(STOPS.length - 2, Math.floor(t)), f = t - i;
    const c = STOPS[i].map((v, k) => Math.round(v + (STOPS[i + 1][k] - v) * f)); return `rgba(${c[0]},${c[1]},${c[2]},${a})`;
  };
  /* the street runs away to the left of the paper, so its end and the sun stay in view on wide screens */
  const SW = 20, KERB = 13;  /* building line and kerb, metres from the middle */
  const geo = (W, H) => { const cx = W * 0.2, vy = H * 0.46, f = Math.max(W * 0.3, H * 0.55), eye = 1.6; return { cx, vy, f, P: (X, Y, z) => [cx + X * f / z, vy - (Y - eye) * f / z] }; };

  /* ----- the street: Market Street style, looking east into the morning sun ----- */
  function street(g, W, H, o = {}) {
    /* the street runs away to the left of the paper, so its end and the sun stay in view on wide screens */
    const R = rnd(1923), { cx, vy, f, P } = geo(W, H);
    /* sky and haze: brightest at the end of the street where the sun comes up */
    let gr = g.createLinearGradient(0, 0, 0, vy); gr.addColorStop(0, tone(0.12)); gr.addColorStop(1, tone(0.62));
    g.fillStyle = gr; g.fillRect(0, 0, W, vy + 2);
    gr = g.createRadialGradient(cx, vy, 0, cx, vy, W * 0.55); gr.addColorStop(0, tone(1, 0.85)); gr.addColorStop(0.25, tone(0.8, 0.35)); gr.addColorStop(1, tone(0.5, 0));
    g.fillStyle = gr; g.fillRect(0, 0, W, H);
    /* the street and the sidewalks */
    gr = g.createLinearGradient(0, vy, 0, H); gr.addColorStop(0, tone(0.6)); gr.addColorStop(0.3, tone(0.3)); gr.addColorStop(1, tone(0.08));
    g.fillStyle = gr; g.fillRect(0, vy, W, H - vy);
    for (const s of [-1, 1]) {
      const a = P(s * KERB, 0, 0.6), b = P(s * SW, 0, 0.6), c = P(s * SW, 0, 400), d = P(s * KERB, 0, 400);
      g.fillStyle = tone(0.22, 0.9); g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.lineTo(...c); g.lineTo(...d); g.fill();
      g.strokeStyle = tone(0.55, 0.5); g.lineWidth = 1.2; g.beginPath(); g.moveTo(...a); g.lineTo(...d); g.stroke();
    }
    /* streetcar rails, two tracks, catching the light */
    g.lineWidth = 1;
    for (const x of [-4.2, -2.8, 2.8, 4.2]) { const a = P(x, 0, 0.8), b = P(x, 0, 400); gr = g.createLinearGradient(a[0], a[1], b[0], b[1]); gr.addColorStop(0, tone(0.5, 0.15)); gr.addColorStop(1, tone(0.95, 0.7)); g.strokeStyle = gr; g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.stroke(); }
    /* buildings: block after block on both sides, hazier with distance */
    for (const s of [-1, 1]) {
      let z = 3; const blocks = [];
      while (z < 260) { const d = 9 + R() * 16; blocks.push({ z0: z, z1: z + d, h: 14 + R() * 38 + (z < 30 ? R() * 25 : 0), win: 3 + Math.floor(R() * 3), set: R() < 0.3 }); z += d; }
      blocks.reverse().forEach(b => {
        const haze = Math.min(1, b.z0 / 160), base = 0.1 + haze * 0.55;
        const n0 = P(s * SW, 0, b.z0), n1 = P(s * SW, b.h, b.z0), f1 = P(s * SW, b.h, b.z1), f0 = P(s * SW, 0, b.z1);
        g.fillStyle = tone(base + 0.04); g.beginPath(); g.moveTo(...n0); g.lineTo(...n1); g.lineTo(...f1); g.lineTo(...f0); g.fill();
        /* the end wall facing us, lit by the sun */
        const e1 = P(s * (SW + 14), b.h, b.z0), e0 = P(s * (SW + 14), 0, b.z0);
        g.fillStyle = tone(base + 0.12); g.beginPath(); g.moveTo(...n0); g.lineTo(...n1); g.lineTo(...e1); g.lineTo(...e0); g.fill();
        /* cornice */
        const c0 = P(s * (SW - 0.6), b.h, b.z0), c1 = P(s * (SW - 0.6), b.h, b.z1);
        g.strokeStyle = tone(base + 0.3, 0.8); g.lineWidth = Math.max(1, 0.5 * f / b.z0 / 3); g.beginPath(); g.moveTo(...c0); g.lineTo(...c1); g.stroke();
        /* windows: rows and columns in perspective, a few lit */
        const floors = Math.floor(b.h / 3.6), cols = Math.max(2, Math.floor((b.z1 - b.z0) / b.win));
        if (b.z0 < 120) for (let fl = 1; fl < floors; fl++) for (let c = 0; c < cols; c++) {
          const za = b.z0 + (c + 0.25) * (b.z1 - b.z0) / cols, zb = b.z0 + (c + 0.75) * (b.z1 - b.z0) / cols, y0 = fl * 3.6 + 0.6, y1 = y0 + 2;
          const q = [P(s * SW, y0, za), P(s * SW, y1, za), P(s * SW, y1, zb), P(s * SW, y0, zb)];
          g.fillStyle = R() < 0.12 ? tone(0.9, 0.55) : tone(base - 0.06, 0.9);
          g.beginPath(); g.moveTo(...q[0]); q.slice(1).forEach(p => g.lineTo(...p)); g.fill();
        }
        /* shop windows on the ground floor, lit for the morning trade, and a sign above each */
        if (b.z0 < 70) { const n = Math.max(1, Math.round((b.z1 - b.z0) / 6));
          for (let k = 0; k < n; k++) { const za = b.z0 + (k + 0.12) * (b.z1 - b.z0) / n, zb = b.z0 + (k + 0.88) * (b.z1 - b.z0) / n;
            const q = [P(s * SW, 0.5, za), P(s * SW, 3.1, za), P(s * SW, 3.1, zb), P(s * SW, 0.5, zb)];
            g.fillStyle = tone(0.62 + R() * 0.2, 0.55); g.beginPath(); g.moveTo(...q[0]); q.slice(1).forEach(p => g.lineTo(...p)); g.fill();
            const t = [P(s * SW, 3.4, za), P(s * SW, 4.1, za), P(s * SW, 4.1, zb), P(s * SW, 3.4, zb)];
            g.fillStyle = tone(base + 0.25, 0.8); g.beginPath(); g.moveTo(...t[0]); t.slice(1).forEach(p => g.lineTo(...p)); g.fill(); } }
        /* shop awnings at street level */
        if (b.z0 < 90 && R() < 0.7) { const q = [P(s * SW, 4.2, b.z0 + 1), P(s * (SW - 2.2), 3.4, b.z0 + 1), P(s * (SW - 2.2), 3.4, b.z1 - 1), P(s * SW, 4.2, b.z1 - 1)];
          g.fillStyle = tone(base + 0.18, 0.9); g.beginPath(); g.moveTo(...q[0]); q.slice(1).forEach(p => g.lineTo(...p)); g.fill(); }
      });
    }
    /* the clock tower at the end of the street, against the sun */
    { const t0 = P(-1.6, 0, 330), t1 = P(1.6, 74, 330); g.fillStyle = tone(0.55, 0.8); g.fillRect(t0[0], t1[1], t1[0] - t0[0], t0[1] - t1[1]); }
    /* overhead wires for the streetcars */
    g.strokeStyle = tone(0.08, 0.55); g.lineWidth = 1;
    for (const x of [-3.5, 3.5]) { const a = P(x, 6.2, 0.7), b = P(x, 6.2, 400); g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.stroke(); }
    for (let z = 3; z < 200; z *= 1.45) { const a = P(-SW, 7, z), b = P(SW, 7, z); g.beginPath(); g.moveTo(...a); g.quadraticCurveTo(cx, (a[1] + b[1]) / 2 + 4 * f / z * 0.02, ...b); g.stroke(); }
    /* poles with lamps */
    for (const s of [-1, 1]) for (let z = 3; z < 160; z *= 1.6) { const a = P(s * (KERB - 0.4), 0, z), b = P(s * (KERB - 0.4), 7.2, z); g.strokeStyle = tone(0.06 + Math.min(0.4, z / 300), 0.9); g.lineWidth = Math.max(1, 0.25 * f / z); g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.stroke(); }
    /* sunbeams down the street */
    g.save(); g.globalCompositeOperation = "screen";
    for (let i = 0; i < 9; i++) { const a = -0.9 + R() * 1.8, l = W; g.fillStyle = tone(0.9, 0.035 + R() * 0.03);
      g.beginPath(); g.moveTo(cx, vy); g.lineTo(cx + Math.cos(Math.PI / 2 + a) * l - 60, vy + Math.sin(Math.PI / 2 + a) * l); g.lineTo(cx + Math.cos(Math.PI / 2 + a) * l + 60, vy + Math.sin(Math.PI / 2 + a) * l); g.fill(); }
    g.restore();
  }

  /* ----- what moves outside: streetcars both ways, people walking to work, steam from a grate ----- */
  const CYCLE = 64, WALK = (() => { const R = rnd(8); return Array.from({ length: 46 }, () => ({ s: R() < 0.5 ? -1 : 1, x: KERB + 0.8 + R() * (SW - KERB - 1.6), z: 4 + R() * 116, v: (R() < 0.5 ? -1 : 1) * (1.1 + R() * 0.5), h: 1.6 + R() * 0.22, w: R() })); })();
  const carAt = t => { const u = (t % CYCLE) / 42, v = ((t + CYCLE / 2) % CYCLE) / 42; return { inbound: u <= 1 ? 150 - 144 * u : null, outbound: v <= 1 ? 6 + 150 * v : null }; };
  function live(g, W, H, t) {
    const { f, P } = geo(W, H);
    g.clearRect(0, 0, W, H);
    /* the morning light breathes as small clouds pass the sun */
    g.fillStyle = tone(1, 0.05 + 0.04 * Math.sin(t / 9) * Math.sin(t / 23)); g.fillRect(0, 0, W, H);
    const car = (x, z, dir) => {
      const w = 2.6, h = 3.4, a = P(x - w / 2, 0.3, z), b = P(x + w / 2, h, z), sc = f / z;
      g.fillStyle = tone(0.1 + z / 400); g.fillRect(a[0], b[1], b[0] - a[0], a[1] - b[1]);
      g.fillStyle = tone(0.75, 0.6); for (let i = 0; i < 3; i++) g.fillRect(a[0] + (0.15 + i * 0.8) * sc, b[1] + 0.45 * sc, 0.6 * sc, 0.9 * sc);
      g.fillStyle = tone(0.35); g.fillRect(a[0] - 0.1 * sc, b[1] - 0.25 * sc, (w + 0.2) * sc, 0.25 * sc);
      g.strokeStyle = tone(0.05, 0.8); g.lineWidth = Math.max(1, 0.06 * sc); g.beginPath(); g.moveTo(a[0] + w / 2 * sc, b[1] - 0.25 * sc); g.lineTo(a[0] + (w / 2 + dir * 0.9) * sc, P(0, 6.2, z)[1]); g.stroke();
      if (dir < 0) { g.fillStyle = tone(1, 0.8); g.beginPath(); g.arc(a[0] + w / 2 * sc, a[1] - 0.8 * sc, 0.1 * sc, 0, 7); g.fill(); }
      g.fillStyle = tone(0, 0.3); g.fillRect(a[0], a[1], b[0] - a[0], 0.15 * sc);
    };
    const c = carAt(t), cars = [];
    if (c.inbound) cars.push([-3.5, c.inbound, -1]); if (c.outbound) cars.push([3.5, c.outbound, 1]);
    /* people, far ones first */
    const ppl = WALK.map(p => { let z = p.z + p.v * t; z = 4 + (((z - 4) % 116) + 116) % 116; return { p, z }; });
    const items = ppl.map(o => ({ z: o.z, draw: () => {
      const { p, z } = o, sc = f / z, [px, py0] = P(p.s * p.x, 0, z), step = Math.sin(t * 6.5 + p.w * 9), py = py0 - Math.abs(step) * 0.03 * sc;
      const h = p.h * sc, w = 0.48 * sc, col = tone(0.05 + Math.min(0.45, z / 250));
      g.fillStyle = tone(0, 0.25); g.beginPath(); g.ellipse(px, py0 + 0.12 * sc, w * 0.6, 0.12 * sc, 0, 0, 7); g.fill();
      g.strokeStyle = col; g.lineWidth = Math.max(1, w * 0.22); g.beginPath(); g.moveTo(px - w * 0.15, py - h * 0.35); g.lineTo(px - w * 0.15 + step * w * 0.3, py0); g.moveTo(px + w * 0.15, py - h * 0.35); g.lineTo(px + w * 0.15 - step * w * 0.3, py0); g.stroke();
      g.fillStyle = col; g.beginPath(); g.moveTo(px - w / 2, py - h * 0.3); g.lineTo(px - w * 0.42, py - h * 0.82); g.lineTo(px + w * 0.42, py - h * 0.82); g.lineTo(px + w / 2, py - h * 0.3); g.fill();
      g.beginPath(); g.arc(px, py - h * 0.88, w * 0.26, 0, 7); g.fill();
      g.fillRect(px - w * 0.36, py - h * 0.99, w * 0.72, h * 0.03); g.fillRect(px - w * 0.2, py - h * 1.06, w * 0.4, h * 0.08);
    } })).concat(cars.map(([x, z, d]) => ({ z, draw: () => car(x, z, d) })));
    items.sort((a, b) => b.z - a.z).forEach(i => i.draw());
    /* parked at the kerb on our side: a motor car, and a newsboy calling the morning edition */
    { const z = 9.5, sc = f / z, [x, y] = P(KERB - 1.2, 0, z), w = 3.8 * sc, h = 1.7 * sc;
      g.fillStyle = tone(0.07); g.fillRect(x - w * 0.1, y - h * 0.55, w * 0.25, h * 0.35); g.fillRect(x + w * 0.12, y - h, w * 0.42, h * 0.8);
      g.fillRect(x - w * 0.12, y - h * 0.35, w * 0.9, h * 0.22);
      g.fillStyle = tone(0.5, 0.55); g.fillRect(x + w * 0.16, y - h * 0.92, w * 0.15, h * 0.32); g.fillRect(x + w * 0.35, y - h * 0.92, w * 0.15, h * 0.32);
      g.fillStyle = tone(0.03); for (const wx of [0.0, 0.62]) { g.beginPath(); g.arc(x + w * wx, y - h * 0.1, h * 0.2, 0, 7); g.fill(); }
      g.fillStyle = tone(0.6, 0.6); for (const wx of [0.0, 0.62]) { g.beginPath(); g.arc(x + w * wx, y - h * 0.1, h * 0.07, 0, 7); g.fill(); } }
    { const z = 7.2, sc = f / z, [x, y] = P(KERB + 1.4, 0, z), h = 1.35 * sc, w = 0.42 * sc, wave = Math.max(0, Math.sin(t * 1.3)) ;
      g.fillStyle = tone(0.06); g.fillRect(x - w * 0.4, y - h * 0.82, w * 0.8, h * 0.5); g.fillRect(x - w * 0.3, y - h * 0.35, w * 0.22, h * 0.35); g.fillRect(x + w * 0.08, y - h * 0.35, w * 0.22, h * 0.35);
      g.beginPath(); g.arc(x, y - h * 0.9, w * 0.24, 0, 7); g.fill(); g.fillRect(x - w * 0.32, y - h * 1.0, w * 0.64, h * 0.06);
      /* the paper held up high */
      g.save(); g.translate(x + w * 0.4, y - h * (0.9 + 0.12 * wave)); g.rotate(-0.3 - wave * 0.3); g.fillStyle = tone(0.75); g.fillRect(-w * 0.1, -w * 0.5, w * 0.8, w * 0.6); g.restore();
      g.fillStyle = tone(0.5); g.fillRect(x - w * 0.9, y - h * 0.3, w * 0.5, h * 0.3); }
    /* steam from a grate on the far sidewalk */
    for (let k = 0; k < 5; k++) { const u = ((t * 0.18 + k / 5) % 1), z = 16, sc = f / z, [x, y] = P(KERB + 2.2, 0, z);
      g.fillStyle = `rgba(235,220,190,${0.13 * (1 - u)})`; g.beginPath(); g.ellipse(x + Math.sin(t + k) * 0.4 * sc, y - u * 4 * sc, (0.5 + u * 1.6) * sc, (0.4 + u) * sc, 0, 0, 7); g.fill(); }
  }
  /* the coffee steams */
  function steam(g, W, H, t) {
    g.clearRect(0, 0, W, H); if (!CUP) return;
    const { x, y, r } = CUP;
    g.save(); g.globalCompositeOperation = "screen"; g.lineCap = "round";
    for (let k = -1; k <= 1; k++) { const p = t * 0.6 + k * 1.7, x0 = x + k * r * 0.22;
      g.strokeStyle = `rgba(255,240,220,${0.07 + 0.03 * Math.sin(p * 1.3)})`; g.lineWidth = r * 0.16;
      g.beginPath(); g.moveTo(x0, y - r * 0.8); g.bezierCurveTo(x0 + Math.sin(p) * r * 0.5, y - r * 1.4, x0 + Math.sin(p + 2) * r * 0.5, y - r * 1.9, x0 + Math.sin(p + 1) * r * 0.3, y - r * 2.6); g.stroke(); }
    g.restore();
  }

  /* ----- the café, closer to life: wood, brass, lace, marble and the morning sun through the glass ----- */
  function room(g, W, H) {
    const R = rnd(1926), tab = H * 0.8, m = Math.max(22, W * 0.014), sill = tab - H * 0.02;
    const lin = (x0, y0, x1, y1, st) => { const gr = g.createLinearGradient(x0, y0, x1, y1); st.forEach(([o, c]) => gr.addColorStop(o, c)); return gr; };
    /* the glass lets the bright street through */
    g.fillStyle = tone(0.9, 0.08); g.fillRect(0, 0, W, sill);
    /* the panes: four tall windows with a transom, the posts in between in dark polished wood */
    const posts = [0, 0.235, 0.765, 1].map(x => W * x), cols = [];
    for (let i = 0; i < posts.length - 1; i++) cols.push([posts[i] + (i ? m / 2 : W * 0.035), posts[i + 1] - (i < posts.length - 2 ? m / 2 : W * 0.035)]);
    /* glass: a cool sheen, faint dust and streaks */
    cols.forEach(([a, b]) => { g.fillStyle = lin(a, 0, b, sill, [[0, "rgba(255,245,225,0.06)"], [0.5, "rgba(255,245,225,0)"], [1, "rgba(255,245,225,0.05)"]]); g.fillRect(a, H * 0.07, b - a, sill - H * 0.07);
      g.save(); g.globalCompositeOperation = "screen"; for (let k = 0; k < 3; k++) { const x = a + R() * (b - a); g.fillStyle = "rgba(255,240,215,0.045)"; g.beginPath(); g.moveTo(x, H * 0.07); g.lineTo(x + 50, H * 0.07); g.lineTo(x - 120, sill); g.lineTo(x - 170, sill); g.fill(); } g.restore(); });
    /* the wooden frame: header, transom bar, posts, each with a lit bevel toward the room light */
    const wood = (x, y, w, h, vert) => {
      g.fillStyle = vert ? lin(x, 0, x + w, 0, [[0, tone(0.03)], [0.3, tone(0.13)], [0.55, tone(0.07)], [1, tone(0.02)]]) : lin(0, y, 0, y + h, [[0, tone(0.03)], [0.35, tone(0.12)], [1, tone(0.02)]]);
      g.fillRect(x, y, w, h);
      g.save(); g.globalAlpha = 0.18; g.strokeStyle = tone(0.4); g.lineWidth = 1; for (let k = 0; k < 6; k++) { g.beginPath(); if (vert) { const xx = x + R() * w; g.moveTo(xx, y); g.bezierCurveTo(xx + 3, y + h / 3, xx - 3, y + h * 2 / 3, xx, y + h); } else { const yy = y + R() * h; g.moveTo(x, yy); g.lineTo(x + w, yy + 2); } g.stroke(); } g.restore();
    };
    wood(0, 0, W, H * 0.07, false);
    wood(0, H * 0.265, W, m * 0.75, false);
    posts.forEach((x, i) => wood(i === 0 ? 0 : i === posts.length - 1 ? W - W * 0.035 : x - m / 2, 0, i === 0 || i === posts.length - 1 ? W * 0.035 : m, sill, true));
    /* gold-leaf lettering on the transom, read from inside, with its black outline */
    const gold = (txt, x, y, size) => { g.save(); g.translate(x, y); g.scale(-1, 1); g.font = `700 ${size}px Georgia, "Times New Roman", serif`; g.textAlign = "center";
      g.lineWidth = size * 0.08; g.strokeStyle = "rgba(10,8,5,0.55)"; g.strokeText(txt, 0, 0);
      g.fillStyle = lin(0, -size, 0, 0, [[0, "rgba(250,225,160,0.62)"], [0.5, "rgba(190,150,80,0.55)"], [1, "rgba(245,215,150,0.62)"]]); g.fillText(txt, 0, 0); g.restore(); };
    gold("CAFÉ", (cols[0][0] + cols[0][1]) / 2, H * 0.215, Math.round(H * 0.075));
    gold("COFFEE · 5¢", (cols[2][0] + cols[2][1]) / 2, H * 0.205, Math.round(H * 0.052));
    /* café curtains on a brass rod across the lower half, lace you can see through */
    const rod = H * 0.635;
    g.strokeStyle = lin(0, rod - 4, 0, rod + 4, [[0, tone(0.95)], [0.5, tone(0.55)], [1, tone(0.2)]]); g.lineWidth = 6; g.beginPath(); g.moveTo(0, rod); g.lineTo(W, rod); g.stroke();
    cols.forEach(([a, b]) => {
      const folds = Math.max(6, Math.round((b - a) / 26));
      for (let k = 0; k < folds; k++) { const x = a + (b - a) * k / folds, w = (b - a) / folds;
        g.fillStyle = lin(x, 0, x + w, 0, [[0, "rgba(235,215,180,0.20)"], [0.5, "rgba(250,236,205,0.34)"], [1, "rgba(200,180,145,0.16)"]]); g.fillRect(x, rod, w + 1, sill - rod); }
      /* lace: rows of small holes */
      g.fillStyle = "rgba(20,15,10,0.12)"; for (let y = rod + 14; y < sill - 8; y += 12) for (let x = a + 6 + ((y / 12) % 2) * 6; x < b - 4; x += 12) { g.beginPath(); g.arc(x, y, 2.2, 0, 7); g.fill(); }
      /* scalloped hem */
      g.fillStyle = "rgba(250,236,205,0.3)"; for (let x = a; x < b; x += 18) { g.beginPath(); g.arc(x + 9, sill - 2, 9, 0, Math.PI); g.fill(); }
    });
    /* the sill and the marble table, lit by the window */
    wood(0, sill, W, tab - sill, false);
    g.fillStyle = lin(0, tab, 0, H, [[0, tone(0.62)], [0.25, tone(0.5)], [1, tone(0.2)]]); g.fillRect(0, tab, W, H - tab);
    g.save(); g.globalAlpha = 0.22; g.strokeStyle = tone(0.15); for (let k = 0; k < 14; k++) { g.lineWidth = 0.6 + R() * 1.4; let x = R() * W, y = tab + R() * (H - tab); g.beginPath(); g.moveTo(x, y); for (let j = 0; j < 6; j++) { x += 40 + R() * 90; y += (R() - 0.5) * 30; g.lineTo(x, y); } g.stroke(); } g.restore();
    g.fillStyle = tone(0.9, 0.55); g.fillRect(0, tab, W, 2);
    /* the sun falls through the panes onto the table: bright shapes, the posts in shadow */
    g.save(); g.globalCompositeOperation = "screen";
    cols.forEach(([a, b]) => { g.fillStyle = "rgba(255,226,170,0.24)"; g.beginPath(); g.moveTo(a + W * 0.04, tab); g.lineTo(b + W * 0.04, tab); g.lineTo(b + W * 0.12, H); g.lineTo(a + W * 0.12, H); g.fill(); });
    g.restore();
    /* sunbeams in the room air */
    g.save(); g.globalCompositeOperation = "screen";
    cols.forEach(([a, b]) => { g.fillStyle = lin(a, H * 0.1, a + W * 0.1, tab, [[0, "rgba(255,230,180,0.07)"], [1, "rgba(255,230,180,0)"]]); g.beginPath(); g.moveTo(a, H * 0.07); g.lineTo(b, H * 0.07); g.lineTo(b + W * 0.08, tab); g.lineTo(a + W * 0.08, tab); g.fill(); });
    g.restore();
    /* things on the table */
    const shadow = (x, y, rx, ry, a = 0.45) => { const gr = g.createRadialGradient(x, y, 0, x, y, rx); gr.addColorStop(0, `rgba(0,0,0,${a})`); gr.addColorStop(1, "rgba(0,0,0,0)"); g.save(); g.scale(1, ry / rx); g.fillStyle = gr; g.beginPath(); g.arc(x, y * rx / ry, rx, 0, 7); g.fill(); g.restore(); };
    const cup = (cx, cy, r) => {
      shadow(cx + r * 0.5, cy + r * 0.35, r * 1.9, r * 0.45);
      g.fillStyle = lin(cx - r * 1.3, 0, cx + r * 1.3, 0, [[0, tone(0.55)], [0.35, tone(0.95)], [1, tone(0.5)]]); g.beginPath(); g.ellipse(cx, cy + r * 0.22, r * 1.35, r * 0.34, 0, 0, 7); g.fill();
      g.fillStyle = tone(0.7, 0.6); g.beginPath(); g.ellipse(cx, cy + r * 0.16, r * 0.85, r * 0.2, 0, 0, 7); g.fill();
      g.fillStyle = lin(cx - r * 0.75, 0, cx + r * 0.75, 0, [[0, tone(0.6)], [0.3, tone(1)], [0.7, tone(0.85)], [1, tone(0.45)]]);
      g.beginPath(); g.moveTo(cx - r * 0.75, cy - r * 0.65); g.bezierCurveTo(cx - r * 0.75, cy + r * 0.05, cx - r * 0.45, cy + r * 0.2, cx, cy + r * 0.2); g.bezierCurveTo(cx + r * 0.45, cy + r * 0.2, cx + r * 0.75, cy + r * 0.05, cx + r * 0.75, cy - r * 0.65); g.fill();
      g.fillStyle = tone(0.95); g.beginPath(); g.ellipse(cx, cy - r * 0.65, r * 0.75, r * 0.17, 0, 0, 7); g.fill();
      g.fillStyle = lin(0, cy - r * 0.78, 0, cy - r * 0.55, [[0, "#2a1a0e"], [1, "#4a3020"]]); g.beginPath(); g.ellipse(cx, cy - r * 0.64, r * 0.66, r * 0.13, 0, 0, 7); g.fill();
      g.strokeStyle = tone(0.9); g.lineWidth = r * 0.13; g.beginPath(); g.ellipse(cx + r * 0.85, cy - r * 0.3, r * 0.22, r * 0.26, 0, -1.6, 1.6); g.stroke();
      /* a spoon on the saucer */
      g.strokeStyle = lin(cx - r, 0, cx + r, 0, [[0, tone(0.4)], [0.5, tone(1)], [1, tone(0.5)]]); g.lineWidth = r * 0.07; g.beginPath(); g.moveTo(cx - r * 1.15, cy + r * 0.3); g.lineTo(cx - r * 0.55, cy + r * 0.12); g.stroke();
    };
    const tr = H - tab;
    CUP = { x: W * 0.84, y: tab + tr * 0.5, r: Math.min(W * 0.045, tr * 0.55) }; cup(CUP.x, CUP.y, CUP.r);
    /* a sugar dispenser, glass with a metal cap, on the left */
    { const x = W * 0.075, y = tab + tr * 0.42, r = Math.min(W * 0.012, tr * 0.2);
      shadow(x + r * 0.6, y + r * 1.25, r * 1.8, r * 0.4);
      g.fillStyle = "rgba(250,240,220,0.22)"; g.fillRect(x - r, y - r * 1.2, r * 2, r * 2.4);
      g.fillStyle = "rgba(255,250,240,0.55)"; g.fillRect(x - r, y - r * 0.1, r * 2, r * 1.3);
      g.fillStyle = lin(x - r, 0, x + r, 0, [[0, tone(0.3)], [0.4, tone(1)], [1, tone(0.35)]]); g.beginPath(); g.moveTo(x - r, y - r * 1.2); g.quadraticCurveTo(x, y - r * 2.3, x + r, y - r * 1.2); g.fill();
      g.fillStyle = "rgba(255,250,235,0.5)"; g.fillRect(x - r * 0.75, y - r * 1.1, r * 0.18, r * 2.2); }
    /* folded papers of other days, left of the cup of the day */
    { const x = W * 0.2, y = tab + tr * 0.55; g.save(); g.translate(x, y); g.rotate(-0.08);
      shadow(10, 18, W * 0.06, 14, 0.4);
      const pw = W * 0.1, ph = tr * 0.42;
      for (let k = 2; k >= 0; k--) { g.fillStyle = lin(0, -ph / 2, 0, ph / 2, [[0, tone(0.9 - k * 0.06)], [1, tone(0.74 - k * 0.06)]]); g.fillRect(-pw / 2 + k * 5, -ph / 2 - k * 6, pw, ph);
        g.fillStyle = "rgba(0,0,0,0.25)"; g.fillRect(-pw / 2 + k * 5, ph / 2 - k * 6 - 2, pw, 2); }
      /* masthead, a headline and columns of type on the top copy */
      g.fillStyle = tone(0.15, 0.75); g.fillRect(-pw * 0.4, -ph * 0.4, pw * 0.8, ph * 0.1);
      g.fillStyle = tone(0.2, 0.5); g.fillRect(-pw * 0.44, -ph * 0.22, pw * 0.88, ph * 0.08);
      g.fillStyle = tone(0.3, 0.35); for (let c = 0; c < 4; c++) for (let l = 0; l < 6; l++) g.fillRect(-pw * 0.44 + c * pw * 0.225, -ph * 0.06 + l * ph * 0.075, pw * 0.2, ph * 0.03);
      g.restore(); }
    /* the room behind us: warm lamplight from above */
    const gr = g.createRadialGradient(W / 2, -H * 0.2, 0, W / 2, -H * 0.2, H * 1.1); gr.addColorStop(0, "rgba(255,210,150,0.12)"); gr.addColorStop(1, "rgba(255,210,150,0)"); g.fillStyle = gr; g.fillRect(0, 0, W, H);
  }

  /* depth, light and grain over everything, then dark toward the edges */
  function finish(g, W, H) {
    let gr = g.createRadialGradient(W / 2, H * 0.45, Math.min(W, H) * 0.25, W / 2, H * 0.5, Math.max(W, H) * 0.75);
    gr.addColorStop(0, "rgba(0,0,0,0.25)"); gr.addColorStop(1, "rgba(0,0,0,0.82)"); g.fillStyle = gr; g.fillRect(0, 0, W, H);
    const R = rnd(5), n = Math.round(W * H / 900); g.fillStyle = "rgba(255,240,210,0.035)";
    for (let i = 0; i < n; i++) g.fillRect(R() * W, R() * H, 1, 1);
    g.fillStyle = "rgba(0,0,0,0.05)"; for (let i = 0; i < n; i++) g.fillRect(R() * W, R() * H, 1, 1);
  }

  /* the street drawn once on its own, then laid down out of focus in a single pass */
  function soft(g, W, H, px) {
    const o = document.createElement("canvas"); o.width = W; o.height = H; street(o.getContext("2d"), W, H);
    g.save(); g.filter = `blur(${px}px)`; g.drawImage(o, 0, 0, W, H); g.restore();
  }

  /* ----- layers: drawn once per size, the moving ones on every frame ----- */
  let W = 0, H = 0;
  const fit = (c, k) => { c.width = Math.max(1, Math.round(W * k)); c.height = Math.max(1, Math.round(H * k)); const g = c.getContext("2d"); g.setTransform(k, 0, 0, k, 0, 0); return g; };
  const K = () => Math.min(1.5, window.devicePixelRatio || 1);
  function layout() {
    W = desk.clientWidth; H = desk.clientHeight; if (!W || !H) return;
    soft(fit(BG, K()), W, H, 4.5);
    room(fit(ROOM, K()), W, H);
    finish(fit(FX, K()), W, H);
    fit(LIVE, 0.4); fit(STEAM, 0.5);  /* low resolution: soft like the rest of the street, and cheap to redraw */
    frame(performance.now());
  }
  const T0 = (/[?&]scene-t=(\d+)/.exec(location.search) || [])[1] != null ? +RegExp.$1 : null;
  let last = 0, raf = 0, bell = false;
  function frame(now) {
    raf = 0; if (!W) return;
    const t = T0 != null ? T0 : (Date.now() / 1000) % 86400;
    live(LIVE.getContext("2d"), W, H, t); steam(STEAM.getContext("2d"), W, H, t);
    /* the inbound streetcar rings its bell as it passes the corner */
    const c = carAt(t), near = c.inbound != null && c.inbound < 46 && c.inbound > 38;
    if (near && !bell) AMB.bell(); bell = near; AMB.rumble(c.inbound != null ? Math.max(0, 1 - c.inbound / 50) : 0);
    last = now; loop();
  }
  function loop() { if (!raf && !document.hidden && !still()) raf = requestAnimationFrame(n => n - last >= 40 ? frame(n) : (raf = 0, loop())); }
  document.addEventListener("visibilitychange", () => { loop(); AMB.pause(document.hidden); });
  let rt; new ResizeObserver(() => { clearTimeout(rt); rt = setTimeout(layout, 150); }).observe(desk);

  /* ----- the café, to hear: off until asked for; everything is made here, no recordings ----- */
  const AMB = (() => {
    let A = null, master, level = 0, rumbleG, timers = [], music = null;
    const noise = secs => { const b = A.createBuffer(1, A.sampleRate * secs, A.sampleRate), d = b.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1; return b; };
    const loopSrc = buf => { const s = A.createBufferSource(); s.buffer = buf; s.loop = true; s.start(); return s; };
    const chain = (...n) => { for (let i = 0; i < n.length - 1; i++) n[i].connect(n[i + 1]); return n[n.length - 1]; };
    const filt = (type, f, q = 0.7) => { const b = A.createBiquadFilter(); b.type = type; b.frequency.value = f; b.Q.value = q; return b; };
    const gain = v => { const g = A.createGain(); g.gain.value = v; return g; };
    function start() {
      A = new (window.AudioContext || window.webkitAudioContext)();
      master = gain(0); master.connect(A.destination);
      const N = noise(4);
      /* the room: voices across the café, a murmur that rises and falls */
      for (const [f, v] of [[480, 0.05], [1150, 0.02]]) { const g = gain(v); chain(loopSrc(N), filt("bandpass", f, 0.9), g, master);
        timers.push(setInterval(() => g.gain.setTargetAtTime(v * (0.4 + Math.random() * 1.2), A.currentTime, 0.12), 260)); }
      chain(loopSrc(N), filt("lowpass", 180), gain(0.025), master);
      /* the street through the glass: traffic, and the streetcar's rumble as it comes close */
      rumbleG = gain(0.015); chain(loopSrc(N), filt("lowpass", 95), rumbleG, master);
      /* cups and spoons */
      const clink = () => { if (level) { const t = A.currentTime, f = 2400 + Math.random() * 1800;
          for (const [m, a] of [[1, 0.035], [2.71, 0.012]]) { const o = A.createOscillator(), g = gain(0); o.frequency.value = f * m; chain(o, g, master); g.gain.setValueAtTime(a, t); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.35); o.start(t); o.stop(t + 0.4); }
          if (Math.random() < 0.4) { const s = A.createBufferSource(), g = gain(0); s.buffer = N; chain(s, filt("bandpass", 1700, 3), g, master); g.gain.setValueAtTime(0.06, t + 0.5); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.56); s.start(t + 0.5, Math.random() * 3, 0.1); } }
        timers.push(setTimeout(clink, 2500 + Math.random() * 7000)); };
      clink();
    }
    /* a gramophone at the back: a slow twelve-bar blues in F, swung, through a horn and a worn record */
    function gramophone() {
      const out = gain(0.11), shaper = A.createWaveShaper(), curve = new Float32Array(256);
      for (let i = 0; i < 256; i++) { const x = i / 128 - 1; curve[i] = Math.tanh(2.2 * x); } shaper.curve = curve;
      chain(shaper, filt("highpass", 320), filt("lowpass", 3000), out, master);
      const hiss = gain(0.012); chain(loopSrc(noise(3)), filt("bandpass", 2500, 0.5), hiss, master);
      const cr = noise(2), d = cr.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() < 0.0006 ? (Math.random() * 2 - 1) : 0;
      const crackle = gain(0.25); chain(loopSrc(cr), filt("highpass", 1500), crackle, master);
      const BRUSH = noise(0.2), BPM = 104, beat = 60 / BPM, sw = beat * 2 / 3;
      const F = 174.61, n = s => F * Math.pow(2, s / 12);
      const BARS = [0, 0, 0, 0, 5, 5, 0, 0, 7, 5, 0, 7];   /* roots in semitones above F */
      const BLUES = [0, 3, 5, 6, 7, 10, 12, 15];
      const note = (f, t, len, type, v, to) => { const o = A.createOscillator(), g = gain(0); o.type = type; o.frequency.value = f; chain(o, g, to || shaper);
        g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v, t + 0.012); g.gain.exponentialRampToValueAtTime(0.0001, t + len); o.start(t); o.stop(t + len + 0.05); return o; };
      const horn = gain(1); const hb = filt("bandpass", 1100, 1.6); chain(horn, hb, shaper);
      let bar = 0, next = A.currentTime + 0.3, R = rnd(1925);
      const tick = () => {
        while (next < A.currentTime + 0.5) {
          const root = BARS[bar % 12], nr = BARS[(bar + 1) % 12], t = next;
          /* walking bass: root, third, fifth, a step toward the next chord */
          [0, 4, 7, nr - 1 - (nr - 1 > 6 ? 12 : 0)].forEach((s, i) => note(n(root + s - 24), t + i * beat, beat * 0.9, "triangle", 0.5));
          /* piano on two and four */
          for (const b of [1, 3]) [4, 10, 14].forEach(s => note(n(root + s), t + b * beat, 0.32, "triangle", 0.09));
          /* brushes */
          for (const b of [1, 3]) { const s = A.createBufferSource(), g = gain(0); s.buffer = BRUSH; chain(s, filt("highpass", 3000), g, shaper); g.gain.setValueAtTime(0.07, t + b * beat); g.gain.exponentialRampToValueAtTime(0.0001, t + b * beat + 0.18); s.start(t + b * beat); }
          /* a muted horn answers every other pair of bars */
          if ((bar >> 1) % 2 === 0) { let at = t;
            for (let k = 0; k < 6; k++) { const s = BLUES[Math.floor(R() * BLUES.length)], o = note(n(s + 12), at, 0.28, "sawtooth", 0.07, horn);
              const v = A.createOscillator(), vg = gain(4); v.frequency.value = 5.5; chain(v, vg, o.frequency); v.start(at); v.stop(at + 0.3); at += k % 2 ? beat - sw : sw; } }
          next += 4 * beat; bar++;
        }
      };
      const id = setInterval(tick, 120); tick();
      return { stop() { clearInterval(id); out.gain.setTargetAtTime(0, A.currentTime, 0.3); hiss.gain.setTargetAtTime(0, A.currentTime, 0.3); crackle.gain.setTargetAtTime(0, A.currentTime, 0.3); } };
    }
    return {
      set(l) { level = l; if (l && !A) start(); if (!A) return; if (l) A.resume();
        master.gain.setTargetAtTime(l ? 0.9 : 0, A.currentTime, 0.4);
        if (l === 2 && !music) music = gramophone(); if (l !== 2 && music) { music.stop(); music = null; } },
      bell() { if (!A || !level) return; const t0 = A.currentTime;
        for (const t of [t0, t0 + 0.38]) for (const [m, a] of [[1, 0.05], [2.4, 0.025], [3.9, 0.012], [5.4, 0.006]]) {
          const o = A.createOscillator(), g = gain(0), lp = filt("lowpass", 2600); o.frequency.value = 1040 * m; chain(o, lp, g, master);
          g.gain.setValueAtTime(a, t); g.gain.exponentialRampToValueAtTime(0.0001, t + 1.8 / m); o.start(t); o.stop(t + 2); } },
      rumble(v) { if (A && rumbleG) rumbleG.gain.setTargetAtTime(0.015 + 0.12 * v, A.currentTime, 0.5); },
      pause(h) { if (A && level) h ? A.suspend() : A.resume(); },
    };
  })();
  /* the button cycles: off, the café, the café with its gramophone; it always starts off */
  const btn = document.getElementById("bAmb");
  if (btn) { let l = 0;
    const label = () => { const L = window.GAZETTE_AMB || ["Café: quiet", "Café: sounds", "Café: + gramophone"]; btn.textContent = L[l]; btn.setAttribute("aria-pressed", String(l > 0)); };
    btn.onclick = e => { e.stopPropagation(); l = (l + 1) % 3; AMB.set(l); label(); };
    label(); window.addEventListener("gazette-labels", label); }
  layout();
})();

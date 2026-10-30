/* The Daily Consensus: the world around the paper. A café window on a 1920s city street at eight
   in the morning, drawn here in the visitor's browser (no photographs, no recordings), in the
   paper's sepia, soft and dark enough that the page stays the brightest thing on the screen.
   Outside, streetcars come and go and people walk to work; the café can be heard on request. */
(() => {
  const desk = document.getElementById("desk"); if (!desk) return;
  if (/[?&]scene=off\b/.test(location.search)) return;
  const layer = cls => { const c = document.createElement("canvas"); c.className = "scene " + cls; c.setAttribute("aria-hidden", "true"); desk.insertBefore(c, desk.querySelector(".stage")); return c; };
  const BG = layer("bg"), LIVE = layer("live"), TRAM = layer("tram"), ROOM = layer("room"), STEAM = layer("steam"), FX = layer("fx");
  const still = () => matchMedia("(prefers-reduced-motion: reduce)").matches || desk.clientWidth < 900;
  let CUP = null, HITS = {}, SUGAR = null, PAPERS = null;

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
    for (const x of [-6.2, -4.8, 4.8, 6.2]) { const a = P(x, 0, 0.8), b = P(x, 0, 400); gr = g.createLinearGradient(a[0], a[1], b[0], b[1]); gr.addColorStop(0, tone(0.5, 0.15)); gr.addColorStop(1, tone(0.95, 0.7)); g.strokeStyle = gr; g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.stroke(); }
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
    for (const x of [-5.5, 5.5]) { const a = P(x, 6.2, 0.7), b = P(x, 6.2, 400); g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.stroke(); }
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
  const carAt = t => { const u = (t % CYCLE) / 42, v = ((t + CYCLE / 2) % CYCLE) / 42; return { inbound: u <= 1 ? 176 - 190 * u : null, outbound: v <= 1 ? -14 + 192 * v : null }; };
  /* cars come out of the haze and leave past the edge of the window beside us, never popping in or out in view:
     a car runs on until its far end (14 m behind its near end) has passed us too */
  function live(g, W, H, t, busy) {
    const { f, P } = geo(W, H);
    g.clearRect(0, 0, W, H);
    /* the morning light breathes as small clouds pass the sun */
    g.fillStyle = tone(1, 0.05 + 0.04 * Math.sin(t / 9) * Math.sin(t / 23)); g.fillRect(0, 0, W, H);
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
    } }));
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
  /* ----- the streetcars: Market Street cars of the twenties and thirties (single deck, arched clerestory roof,
     route box, fender), drawn as solid bodies in the street's perspective. One leaves from right beside us when
     the paper opens and runs away down the street; then they come and go on both tracks. ----- */
  const INTRO = { delay: 1.2, z0: 2.6, v: 4.6, a: 0.09, end: 175 };
  const introAt = e => { e -= INTRO.delay; return e < 0 ? null : INTRO.z0 + INTRO.v * e + INTRO.a * e * e; };
  function trams(g, W, H, cars) {
    g.clearRect(0, 0, W, H);
    cars.filter(c => c.z != null && c.z < 178 && c.z > -14).sort((a, b) => b.z - a.z).forEach(c => tram(g, W, H, c));
  }
  function tram(g, W, H, { x: xc, z: zr, away }) {
    const { f, P: P0 } = geo(W, H), P = (X, Y, z) => P0(X, Y, Math.max(0.35, z)), L = 14, s = Math.sign(xc), Xs = xc - s * 1.3, Xo = xc + s * 1.3, zf = zr + L, Xm = xc;
    /* farther off everything sinks into the morning haze */
    const hz = Math.min(0.6, Math.max(0, (zr - 6) / 260)), T = (v, a = 1) => tone(v + (0.6 - v) * hz, a);
    const sc = z => f / Math.max(0.35, z);
    const poly = (pts, fill) => { g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(...p) : g.moveTo(...p)); g.closePath(); g.fillStyle = fill; g.fill(); };
    const side = (y0, y1, za, zb, fill, x = Xs) => poly([P(x, y0, za), P(x, y1, za), P(x, y1, zb), P(x, y0, zb)], fill);
    const end = (xa, xb, y0, y1, fill, z = zr) => poly([P(xa, y0, z), P(xa, y1, z), P(xb, y1, z), P(xb, y0, z)], fill);
    const Xe = Xs - s * 0.35, zc0 = zr + 0.45, lerpX = u => Xo + (Xe - Xo) * u;   /* across the end, 0 = outer edge, 1 = the corner toward us */
    const sideGrad = (a, b) => { const p = P(Xs, 1, zr), q = P(Xs, 1, zf), l = g.createLinearGradient(p[0], p[1], q[0], q[1]); l.addColorStop(0, T(a)); l.addColorStop(1, T(b)); return l; };
    g.save(); g.globalAlpha = Math.max(0, Math.min(1, (178 - zr) / 28));
    /* the shadow on the cobbles, thrown toward us by the low sun at the end of the street */
    poly([P(Xo + s * 0.3, 0.01, zr - 1.6), P(Xs - s * 0.6, 0.01, zr - 1.6), P(Xs - s * 0.6, 0.01, zf), P(Xo + s * 0.3, 0.01, zf)], tone(0, 0.34 * (1 - hz)));
    /* the side toward us: skirt, dark lower panel, belt rail, window band, letterboard, clerestory */
    side(0.35, 0.6, zr + 0.4, zf - 0.4, T(0.03));
    side(0.6, 1.8, zr, zf, sideGrad(0.1, 0.26));
    side(1.8, 3.0, zr, zf, sideGrad(0.34, 0.5));
    side(3.0, 3.3, zr, zf, sideGrad(0.16, 0.3));
    side(3.3, 3.5, zr + 0.05, zf - 0.05, sideGrad(0.24, 0.4));                 /* the curve of the roof toward the clerestory */
    side(3.5, 3.85, zr + 1.2, zf - 1.2, sideGrad(0.2, 0.34), Xs + s * 0.55);  /* the clerestory, set back from the side */
    for (let i = 0; i < 9; i++) { const m = zr + 2.1 + i * 1.2; side(3.58, 3.76, m - 0.3, m + 0.3, T(0.72, 0.8), Xs + s * 0.55); }
    /* the roof's top edge catches the sun */
    g.strokeStyle = T(0.95, 0.65); g.lineWidth = Math.max(1, 0.05 * sc(zr)); g.beginPath(); g.moveTo(...P(Xs + s * 0.1, 3.5, zr + 0.1)); g.lineTo(...P(Xs + s * 0.1, 3.5, zf - 0.1)); g.stroke();
    g.beginPath(); g.moveTo(...P(Xs + s * 0.55, 3.86, zr + 1.2)); g.lineTo(...P(Xs + s * 0.55, 3.86, zf - 1.2)); g.stroke();
    /* windows: the platforms' and nine in the saloon, lit warm, with posts between them and riders inside */
    const wins = [[0.3, 1.3]]; for (let i = 0; i < 9; i++) wins.push([2.2 + i * 1.05, 3.05 + i * 1.05]); wins.push([L - 1.3, L - 0.3]);
    wins.forEach(([a, b], i) => { side(1.95, 2.85, zr + a, zr + b, T(0.78, 0.92));
      side(1.95, 2.2, zr + a, zr + b, T(0.95, 0.5));                           /* the sky in the glass */
      if (i > 0 && i < wins.length - 1 && (i * 5) % 3) { const m = zr + (a + b) / 2, [hx, hy] = P(Xs + s * 0.4, 2.35, m), r = 0.19 * sc(m);
        g.fillStyle = T(0.2, 0.85); g.beginPath(); g.arc(hx, hy, r, 0, 7); g.fill(); g.fillRect(hx - r * 1.2, hy + r * 0.8, r * 2.4, r * 2); } });
    side(1.8, 1.86, zr, zf, T(0.8, 0.9)); side(2.96, 3.0, zr, zf, T(0.7, 0.7));
    /* the platform door and the step */
    side(0.6, 1.8, zr + 0.3, zr + 1.3, T(0.05, 0.6)); side(0.3, 0.45, zr + 0.2, zr + 1.4, T(0.2));
    /* "Market Street Railway" on the letterboard, and the car number */
    { const [lx, ly] = P(Xs, 3.15, zr + L / 2), k = sc(zr + L / 2); if (k > 7) { g.fillStyle = T(0.75, 0.8); g.font = `600 ${0.2 * k}px Georgia, serif`; g.textAlign = "center"; g.textBaseline = "middle";
      g.save(); const a = P(Xs, 3.15, zr + L / 2 - 1), b = P(Xs, 3.15, zr + L / 2 + 1); g.translate(lx, ly); g.rotate(Math.atan2(b[1] - a[1], b[0] - a[0]) + (s > 0 ? Math.PI : 0));
      const n0 = P(Xs, 3.15, zr + 3), n1 = P(Xs, 3.15, zf - 3), room = Math.hypot(n1[0] - n0[0], n1[1] - n0[1]), wd = g.measureText("MARKET STREET RAILWAY").width;
      g.scale(Math.min(1, room / wd), 1); g.fillText("MARKET STREET RAILWAY", 0, 0); g.restore(); } }
    /* trucks and wheels under the skirt */
    for (const c of [1.9, 3.5, L - 3.5, L - 1.9]) { const zc = zr + c, pts = []; for (let k = 0; k < 16; k++) { const a = k / 16 * 6.283; pts.push(P(Xs + s * 0.1, 0.42 + 0.4 * Math.sin(a), zc + 0.4 * Math.cos(a))); }
      poly(pts, T(0.02)); const [hx, hy] = P(Xs + s * 0.08, 0.42, zc); g.fillStyle = T(0.55, 0.8); g.beginPath(); g.arc(hx, hy, 0.08 * sc(zc), 0, 7); g.fill(); }
    side(0.15, 0.35, zr + 1.3, zr + 4.1, T(0.06)); side(0.15, 0.35, zf - 4.1, zf - 1.3, T(0.06));
    /* the near end: a little in shadow, lighter toward its edge; arched roof, three windows, route box, lamp, fender */
    { const l = g.createLinearGradient(...P(Xm, 0.6, zr), ...P(Xm, 3.3, zr)); l.addColorStop(0, T(0.04)); l.addColorStop(0.6, T(0.1)); l.addColorStop(1, T(0.16)); end(Xo, Xe, 0.6, 3.3, l); }
    { const pts = []; for (let k = 0; k <= 12; k++) { const u = k / 12; pts.push(P(lerpX(u), 3.3 + 0.5 * Math.sin(Math.PI * u), zr + 0.05)); } pts.push(P(Xe, 3.3, zr), P(Xo, 3.3, zr)); poly(pts, T(0.14)); }
    /* the angled corner between end and side, half lit, with its own window */
    const cham = (y0, y1, fill) => poly([P(Xe, y0, zr), P(Xe, y1, zr), P(Xs, y1, zc0), P(Xs, y0, zc0)], fill);
    cham(0.6, 3.3, T(0.22)); cham(1.95, 2.95, T(0.8, 0.9)); cham(1.95, 2.2, T(0.95, 0.5)); cham(3.3, 3.5, T(0.3));
    for (const xp of [Xo, Xe]) { g.strokeStyle = T(xp === Xe ? 0.7 : 0.3, 0.6); g.lineWidth = Math.max(1, 0.05 * sc(zr)); g.beginPath(); g.moveTo(...P(xp, 0.6, zr)); g.lineTo(...P(xp, 3.3, zr)); g.stroke(); }
    for (const [a, b] of [[0.08, 0.34], [0.38, 0.62], [0.66, 0.92]]) { end(lerpX(a), lerpX(b), 1.95, 2.95, T(0.74, 0.92)); end(lerpX(a), lerpX(b), 1.95, 2.2, T(0.95, 0.45)); }
    end(lerpX(0.3), lerpX(0.7), 3.42, 3.75, T(0.88), zr + 0.02);
    { const [bx, by] = P(Xm, 3.585, zr), k = sc(zr); g.fillStyle = T(0.04); g.font = `700 ${Math.max(5, 0.27 * k)}px Georgia, serif`; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText("21", bx, by); }
    { const [lx, ly] = P(Xm, 1.25, zr - 0.05), k = sc(zr), lit = !away;
      if (lit) { const gl = g.createRadialGradient(lx, ly, 0, lx, ly, 1.2 * k); gl.addColorStop(0, "rgba(255,236,190,0.35)"); gl.addColorStop(1, "rgba(255,236,190,0)"); g.fillStyle = gl; g.fillRect(lx - 1.2 * k, ly - 1.2 * k, 2.4 * k, 2.4 * k); }
      g.fillStyle = lit ? "rgba(255,240,205,0.95)" : T(0.55, 0.9); g.beginPath(); g.arc(lx, ly, 0.12 * k, 0, 7); g.fill(); }
    end(Xo, Xe, 0.55, 0.62, T(0.4, 0.8), zr - 0.02);                                  /* bumper */
    poly([P(Xo - s * 0.1, 0.34, zr - 0.05), P(Xe, 0.34, zr - 0.05), P(Xe, 0.16, zr - 0.5), P(Xo - s * 0.1, 0.16, zr - 0.5)], T(0.04, 0.6));
    for (let k = 0; k < 9; k++) { const u = 0.06 + k * 0.11; poly([P(lerpX(u), 0.34, zr - 0.05), P(lerpX(u + 0.025), 0.34, zr - 0.05), P(lerpX(u + 0.025), 0.16, zr - 0.5), P(lerpX(u), 0.16, zr - 0.5)], T(0.16, 0.9)); }
    /* rim light down the near corner */
    g.strokeStyle = T(0.85, 0.5); g.lineWidth = Math.max(1, 0.035 * sc(zr)); g.beginPath(); g.moveTo(...P(Xs, 0.6, zc0)); g.lineTo(...P(Xs, 3.3, zc0)); g.stroke();
    /* the trolley pole trails behind, up to the wire */
    { const base = away ? zr + 3 : zf - 3, tip = away ? zr - 1.5 : zf + 1.5, a = P(xc, 3.86, base), b = P(xc, 6.2, tip);
      g.strokeStyle = T(0.05, 0.95); g.lineWidth = Math.max(1, 0.06 * sc(base)); g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.stroke(); }
    g.restore();
  }
  /* the coffee steams */
  function steam(g, W, H, t) {
    g.clearRect(0, 0, W, H); if (!CUP) return;
    const { x, y, r } = CUP, stir = touched("cup"), up = stir == null ? 1 : 1 + 2.2 * Math.sin(Math.PI * Math.min(1, stir * 1.4));
    g.save(); g.globalCompositeOperation = "screen"; g.lineCap = "round";
    /* stirred: rings run across the coffee and the steam rises thick for a moment */
    if (stir != null) for (let k = 0; k < 3; k++) { const u = (stir * 2.5 + k / 3) % 1, a = (1 - stir) * (1 - u) * 0.5;
      g.strokeStyle = `rgba(255,235,205,${a})`; g.lineWidth = Math.max(1, r * 0.03); g.beginPath(); g.ellipse(x, y - r * 0.64, r * 0.64 * u, r * 0.12 * u, 0, 0, 7); g.stroke(); }
    for (let k = -1; k <= 1; k++) { const p = t * 0.6 + k * 1.7, x0 = x + k * r * 0.22;
      g.strokeStyle = `rgba(255,240,220,${Math.min(0.3, (0.07 + 0.03 * Math.sin(p * 1.3)) * up)})`; g.lineWidth = r * 0.16 * Math.sqrt(up);
      g.beginPath(); g.moveTo(x0, y - r * 0.8); g.bezierCurveTo(x0 + Math.sin(p) * r * 0.5, y - r * 1.4, x0 + Math.sin(p + 2) * r * 0.5, y - r * 1.9, x0 + Math.sin(p + 1) * r * 0.3, y - r * 2.6 * Math.sqrt(up)); g.stroke(); }
    /* and for a moment the steam writes a tau above the cup */
    if (stir != null) { const a = Math.sin(Math.PI * Math.min(1, Math.max(0, (stir - 0.1) / 0.8))) * 0.42;
      g.fillStyle = `rgba(255,242,222,${a})`; g.font = `italic 400 ${r * 1.7}px Georgia, serif`; g.textAlign = "center"; g.textBaseline = "middle";
      g.fillText("τ", x + Math.sin(stir * 5) * r * 0.08, y - r * (2.1 + stir * 0.6)); }
    g.restore();
    /* the sugar: a thin stream of grains from the spout, a small heap on the marble */
    const su = touched("sugar"); if (su != null && SUGAR) { const { x: sx, y: sy, r: sr } = SUGAR, R = rnd(5), flow = su < 0.5;
      g.fillStyle = "rgba(255,250,240,0.85)";
      for (let k = 0; k < 40; k++) { const ph = (R() + su * 6) % 1; if (!flow && ph > (1 - su) * 2 - 0.4) continue;
        g.fillRect(sx + sr * 1.4 + R() * sr * 0.5, sy - sr * 1.5 + ph * sr * 2.7, Math.max(1, sr * 0.08), Math.max(1, sr * 0.08)); }
      /* the grains settle as cubes in a row, linked: a little chain, the newest block lit for a moment */
      const fade = su > 0.85 ? (1 - su) / 0.15 : 1, c = sr * 0.72;
      for (let k = 0; k < 4; k++) { const t0 = 0.2 + k * 0.1, a = Math.min(1, Math.max(0, (su - t0) / 0.06)) * fade; if (!a) continue;
        const bx = sx - sr * 1.2 + k * c * 1.8, by = sy + sr * 2.5 - c;
        if (k) { g.strokeStyle = `rgba(255,250,240,${0.6 * a})`; g.lineWidth = Math.max(1, c * 0.12); g.beginPath(); g.moveTo(bx - c * 0.9, by + c * 0.5); g.lineTo(bx, by + c * 0.5); g.stroke(); }
        g.fillStyle = `rgba(250,244,232,${0.95 * a})`; g.fillRect(bx, by, c, c);
        g.fillStyle = `rgba(255,255,250,${a})`; g.beginPath(); g.moveTo(bx, by); g.lineTo(bx + c * 0.3, by - c * 0.25); g.lineTo(bx + c * 1.3, by - c * 0.25); g.lineTo(bx + c, by); g.fill();
        g.fillStyle = `rgba(200,190,170,${0.9 * a})`; g.beginPath(); g.moveTo(bx + c, by); g.lineTo(bx + c * 1.3, by - c * 0.25); g.lineTo(bx + c * 1.3, by + c * 0.75); g.lineTo(bx + c, by + c); g.fill();
        if (k === 3) { const glow = Math.max(0, 1 - (su - t0) / 0.25) * a; if (glow > 0) { g.fillStyle = `rgba(90,210,130,${0.55 * glow})`; g.fillRect(bx - 1, by - 1, c + 2, c + 2); } } } }
    /* the papers: the top copy lifts at its corner and settles again */
    const pa = touched("papers"); if (pa != null && PAPERS) { const { x: px, y: py, pw, ph } = PAPERS, lift = Math.sin(Math.PI * pa);
      g.save(); g.translate(px, py); g.rotate(-0.08);
      const cx0 = pw / 2, cy0 = ph / 2, s = pw * 0.38 * lift;
      g.fillStyle = "rgba(0,0,0,0.25)"; g.beginPath(); g.moveTo(cx0 - s, cy0); g.lineTo(cx0, cy0 - s * 0.8); g.lineTo(cx0 + s * 0.15, cy0 + s * 0.15); g.fill();
      g.fillStyle = tone(0.85); g.beginPath(); g.moveTo(cx0 - s, cy0); g.lineTo(cx0, cy0 - s * 0.8); g.lineTo(cx0 - s * 0.9, cy0 - s * 1.2); g.fill();
      g.fillStyle = tone(0.3, 0.4); g.fillRect(cx0 - s * 0.8, cy0 - s * 0.9, s * 0.4, Math.max(1, s * 0.05)); g.restore(); }
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
    { const x = W * 0.075, y = tab + tr * 0.42, r = Math.min(W * 0.012, tr * 0.2); SUGAR = { x, y, r };
      shadow(x + r * 0.6, y + r * 1.25, r * 1.8, r * 0.4);
      g.fillStyle = "rgba(250,240,220,0.22)"; g.fillRect(x - r, y - r * 1.2, r * 2, r * 2.4);
      g.fillStyle = "rgba(255,250,240,0.55)"; g.fillRect(x - r, y - r * 0.1, r * 2, r * 1.3);
      g.fillStyle = lin(x - r, 0, x + r, 0, [[0, tone(0.3)], [0.4, tone(1)], [1, tone(0.35)]]); g.beginPath(); g.moveTo(x - r, y - r * 1.2); g.quadraticCurveTo(x, y - r * 2.3, x + r, y - r * 1.2); g.fill();
      g.fillStyle = "rgba(255,250,235,0.5)"; g.fillRect(x - r * 0.75, y - r * 1.1, r * 0.18, r * 2.2); }
    /* folded papers of other days, left of the cup of the day */
    { const x = W * 0.2, y = tab + tr * 0.55; g.save(); g.translate(x, y); g.rotate(-0.08);
      shadow(10, 18, W * 0.06, 14, 0.4);
      const pw = W * 0.1, ph = tr * 0.42; PAPERS = { x, y, pw, ph };
      for (let k = 2; k >= 0; k--) { g.fillStyle = lin(0, -ph / 2, 0, ph / 2, [[0, tone(0.9 - k * 0.06)], [1, tone(0.74 - k * 0.06)]]); g.fillRect(-pw / 2 + k * 5, -ph / 2 - k * 6, pw, ph);
        g.fillStyle = "rgba(0,0,0,0.25)"; g.fillRect(-pw / 2 + k * 5, ph / 2 - k * 6 - 2, pw, 2); }
      /* masthead, a headline and columns of type on the top copy */
      g.fillStyle = tone(0.15, 0.75); g.fillRect(-pw * 0.4, -ph * 0.4, pw * 0.8, ph * 0.1);
      g.fillStyle = tone(0.2, 0.5); g.fillRect(-pw * 0.44, -ph * 0.22, pw * 0.88, ph * 0.08);
      g.fillStyle = tone(0.3, 0.35); for (let c = 0; c < 4; c++) for (let l = 0; l < 6; l++) g.fillRect(-pw * 0.44 + c * pw * 0.225, -ph * 0.06 + l * ph * 0.075, pw * 0.2, ph * 0.03);
      g.restore(); }
    { const c = CUP, su = SUGAR, p = PAPERS;
      HITS = { cup: { x: c.x - c.r * 1.4, y: c.y - c.r * 1.2, w: c.r * 2.8, h: c.r * 1.8 }, sugar: { x: su.x - su.r * 1.6, y: su.y - su.r * 2.6, w: su.r * 3.2, h: su.r * 4.2 },
        papers: { x: p.x - p.pw * 0.6, y: p.y - p.ph * 0.75, w: p.pw * 1.2, h: p.ph * 1.4 } }; }
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
    fit(LIVE, 0.4); fit(TRAM, 0.75); fit(STEAM, 0.5); hotspots();  /* low resolution: soft like the rest of the street, and cheap to redraw */
    frame(performance.now());
  }
  const T0 = (/[?&]scene-t=(\d+)/.exec(location.search) || [])[1] != null ? +RegExp.$1 : null;
  let last = 0, raf = 0, bell = false, introBell = false;
  /* the opening streetcar counts from page load; ?scene-intro=<seconds> freezes it for a picture */
  const LOAD = performance.now(), TI = (/[?&]scene-intro=([\d.]+)/.exec(location.search) || [])[1] != null ? +RegExp.$1 : null;
  function frame(now) {
    raf = 0; if (!W) return;
    const t = T0 != null ? T0 : (Date.now() / 1000) % 86400;
    const zi = still() ? null : introAt(TI != null ? TI : (now - LOAD) / 1000), busy = still() ? false : zi != null ? zi <= INTRO.end : TI == null && now - LOAD < INTRO.delay * 1000;
    live(LIVE.getContext("2d"), W, H, t, busy);
    trams(TRAM.getContext("2d"), W, H, [{ x: -5.5, z: zi, away: true }, { x: -5.5, z: busy ? null : carAt(t).inbound, away: false }, { x: 5.5, z: carAt(t).outbound, away: true }]); steam(STEAM.getContext("2d"), W, H, t);
    /* the inbound streetcar rings its bell as it passes the corner; the opening one as it sets off */
    const c = carAt(t), near = !busy && c.inbound != null && c.inbound < 46 && c.inbound > 38, off = zi != null && zi < 4;
    if ((near && !bell) || (off && !introBell)) AMB.bell(); bell = near; introBell = introBell || off;
    AMB.rumble(busy && zi != null ? Math.max(0, 1 - zi / 40) : !busy && c.inbound != null ? Math.max(0, Math.min(1, 1 - c.inbound / 50)) : 0);
    last = now; loop();
  }
  function loop() { if (!raf && !document.hidden && (!still() || Object.keys(TOUCH).some(k => touched(k) != null))) raf = requestAnimationFrame(n => n - last >= 40 ? frame(n) : (raf = 0, loop())); }
  document.addEventListener("visibilitychange", () => { loop(); AMB.pause(document.hidden); });
  let rt; new ResizeObserver(() => { clearTimeout(rt); rt = setTimeout(layout, 150); }).observe(desk);

  /* ----- the café, to hear: off until asked for; everything is made here, no recordings.
     Inside: voices, cups, the register. Through the glass: Market Street at eight, streetcars with their
     foot gongs, hooves and a cart, a Model T and its klaxon, footsteps, the newsboy, gulls and a foghorn
     from the bay. Each sound comes at its own random time, so nothing repeats in a loop. ----- */
  const AMB = (() => {
    let A = null, master, street, glass, level = 0, rumbleG, timers = [], music = null, N, BR;
    /* the café walk (cafe.js) moves the listener: the street nearer or farther, the gramophone louder in the back room */
    const MIX = { street: 1, open: 0, music: 1 };
    const mix = () => { if (!A) return; const t = A.currentTime; street.gain.setTargetAtTime(MIX.street, t, 0.6);
      glass.frequency.setTargetAtTime(2600 + 9000 * MIX.open, t, 0.6); if (music) music.out.gain.setTargetAtTime(0.16 * MIX.music, t, 0.6); };
    const noise = secs => { const b = A.createBuffer(1, A.sampleRate * secs, A.sampleRate), d = b.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1; return b; };
    /* brown noise: soft, without the hiss of white noise */
    const brown = secs => { const b = A.createBuffer(1, A.sampleRate * secs, A.sampleRate), d = b.getChannelData(0); let v = 0; for (let i = 0; i < d.length; i++) { v = (v + 0.02 * (Math.random() * 2 - 1)) / 1.02; d[i] = v * 3.5; } return b; };
    const loopSrc = (buf, off = 0) => { const s = A.createBufferSource(); s.buffer = buf; s.loop = true; s.start(0, off); return s; };
    const chain = (...n) => { for (let i = 0; i < n.length - 1; i++) n[i].connect(n[i + 1]); return n[n.length - 1]; };
    const filt = (type, f, q = 0.7) => { const b = A.createBiquadFilter(); b.type = type; b.frequency.value = f; b.Q.value = q; return b; };
    const gain = v => { const g = A.createGain(); g.gain.value = v; return g; };
    const pan = p => { if (!A.createStereoPanner) return gain(1); const n = A.createStereoPanner(); n.pan.value = p; return n; };
    const rand = (a, b) => a + Math.random() * (b - a);
    const every = (fn, a, b) => { const go = () => { timers.push(setTimeout(() => { if (level && !document.hidden) fn(); go(); }, rand(a, b) * 1000)); }; go(); };
    const burst = (t, dur, f, q, v, to, buf = N) => { const s = A.createBufferSource(), g = gain(0); s.buffer = buf; chain(s, filt("bandpass", f, q), g, to);
      g.gain.setValueAtTime(v, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur); s.start(t, Math.random() * 2, dur + 0.05); };
    const tone1 = (t, f, dur, v, to, type = "sine", att = 0.004) => { const o = A.createOscillator(), g = gain(0); o.type = type; o.frequency.value = f; chain(o, g, to);
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v, t + att); g.gain.exponentialRampToValueAtTime(0.0001, t + dur); o.start(t); o.stop(t + dur + 0.05); return o; };
    /* something that passes the window: a panner that travels from one side to the other */
    const passing = (secs, v, from = rand(-0.9, -0.5) * (Math.random() < 0.5 ? -1 : 1)) => { const t = A.currentTime, p = pan(from), g = gain(0); chain(g, p, street);
      if (p.pan) { p.pan.setValueAtTime(from, t); p.pan.linearRampToValueAtTime(-from, t + secs); }
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v, t + secs * 0.45); g.gain.linearRampToValueAtTime(0, t + secs); return g; };

    /* the streetcar's foot gong: a struck bronze bell, clang-clang */
    function gong(times = 2, v = 0.07, to = street) { const t0 = A.currentTime + 0.02, f0 = rand(1180, 1260);
      for (let k = 0; k < times; k++) { const t = t0 + k * rand(0.2, 0.26);
        for (const [m, a, d] of [[1, 1, 2.2], [2.32, 0.5, 1.2], [2.98, 0.28, 0.9], [4.16, 0.18, 0.5], [5.43, 0.1, 0.3]]) tone1(t, f0 * m, d, v * a * (k ? 0.85 : 1), to);
        burst(t, 0.025, 3500, 1, v * 0.8, to); } }
    function start() {
      A = new (window.AudioContext || window.webkitAudioContext)(); N = noise(3); BR = brown(6);
      master = gain(0); chain(master, filt("highpass", 130, 0.6), A.destination);  /* nothing below 130 Hz: no hum */
      /* the street is heard through the window glass */
      street = gain(MIX.street); glass = filt("lowpass", 2600); chain(street, glass, filt("highpass", 90), master);
      /* the café: a few tables talking, each voice rising and falling in syllables, now and then a pause */
      for (let k = 0; k < 6; k++) { const g = gain(0), f = rand(380, 900), v = rand(0.035, 0.06); chain(loopSrc(BR, rand(0, 5)), filt("highpass", 250), filt("bandpass", f, 2.2), filt("peaking", f * 2.6, 1.5), g, pan(rand(-0.8, 0.8)), master);
        let talk = Math.random() < 0.6;
        timers.push(setInterval(() => { if (Math.random() < 0.02) talk = !talk; g.gain.setTargetAtTime(talk ? v * (0.15 + Math.random()) : 0, A.currentTime, 0.04); }, rand(110, 170))); }
      /* the street's own wash of traffic, and the streetcar's rumble as it comes close */
      chain(loopSrc(BR, 2), filt("highpass", 300), filt("bandpass", 700, 0.7), gain(0.03), street);
      rumbleG = gain(0); chain(loopSrc(BR, 4), filt("lowpass", 160), rumbleG, street);
      /* cups, spoons, saucers */
      every(() => { const t = A.currentTime, f = rand(2600, 4200), p = pan(rand(-0.7, 0.7)); p.connect(master);
        for (const [m, a] of [[1, 0.03], [2.71, 0.01]]) tone1(t, f * m, 0.35, a, p);
        if (Math.random() < 0.4) burst(t + 0.4, 0.06, 1700, 3, 0.05, p); }, 2, 8);
      /* the register, now and then */
      every(() => { const t = A.currentTime, p = pan(0.6); p.connect(master); for (let k = 0; k < 3; k++) burst(t + k * 0.05, 0.03, 2500, 2, 0.05, p); tone1(t + 0.18, 1900, 0.9, 0.025, p); tone1(t + 0.18, 2850, 0.6, 0.012, p); }, 40, 90);
      /* streetcars that pass without stopping: wheels on the joints, the motor, a gong at the crossing */
      every(() => { const g = passing(rand(9, 13), 0.9), t = A.currentTime; chain(loopSrc(BR), filt("lowpass", 200), gain(0.25), g);
        const m = A.createOscillator(); m.type = "sawtooth"; m.frequency.setValueAtTime(90, t); m.frequency.linearRampToValueAtTime(150, t + 5); chain(m, filt("lowpass", 300), gain(0.03), g); m.start(t); m.stop(t + 14);
        for (let k = 0; k < 10; k++) { const tk = t + 2 + k * 0.9; burst(tk, 0.06, 300, 2, 0.12, g, BR); burst(tk + 0.12, 0.06, 300, 2, 0.1, g, BR); }
        if (Math.random() < 0.7) setTimeout(() => level && gong(Math.random() < 0.3 ? 3 : 2, 0.05), rand(3000, 6000)); }, 35, 70);
      /* hooves and a delivery cart */
      every(() => { const secs = rand(8, 12), g = passing(secs, 1), t = A.currentTime, step = rand(0.42, 0.5);
        for (let k = 0; k < secs / step; k++) { const tk = t + k * step; burst(tk, 0.05, rand(1400, 2000), 4, 0.12, g); tone1(tk, rand(420, 480), 0.06, 0.03, g); burst(tk + step * 0.28, 0.04, rand(1300, 1800), 4, 0.08, g); }
        chain(loopSrc(BR, 1), filt("lowpass", 260), gain(0.18), g);
        const c = A.createOscillator(); c.type = "sawtooth"; c.frequency.value = 380; const l = A.createOscillator(), lg = gain(40); l.frequency.value = 0.9; chain(l, lg, c.frequency);
        const cg = gain(0); chain(c, filt("bandpass", 900, 6), cg, g); for (let k = 0; k < secs; k += 1.8) { cg.gain.setTargetAtTime(0.012, t + k, 0.05); cg.gain.setTargetAtTime(0, t + k + 0.35, 0.08); }
        c.start(t); l.start(t); c.stop(t + secs); l.stop(t + secs); }, 25, 60);
      /* a Model T: the putter of four cylinders, and sometimes its klaxon */
      every(() => { const secs = rand(6, 9), g = passing(secs, 1), t = A.currentTime, o = A.createOscillator(), am = gain(0), lfo = A.createOscillator(), ld = gain(0.5);
        o.type = "square"; o.frequency.value = 55; lfo.type = "square"; lfo.frequency.setValueAtTime(14, t); lfo.frequency.linearRampToValueAtTime(19, t + secs);
        chain(lfo, ld, am.gain); chain(o, filt("lowpass", 380), am, gain(0.08), g); o.start(t); lfo.start(t); o.stop(t + secs); lfo.stop(t + secs);
        if (Math.random() < 0.5) { const tk = t + secs * rand(0.3, 0.5); for (let k = 0; k < 2; k++) { const a = tk + k * 0.55, h = A.createOscillator(), hg = gain(0); h.type = "sawtooth";
          h.frequency.setValueAtTime(260, a); h.frequency.exponentialRampToValueAtTime(560, a + 0.3); chain(h, filt("bandpass", 1000, 2.5), hg, g); hg.gain.setValueAtTime(0, a); hg.gain.linearRampToValueAtTime(0.06, a + 0.05); hg.gain.setValueAtTime(0.06, a + 0.38); hg.gain.linearRampToValueAtTime(0, a + 0.45); h.start(a); h.stop(a + 0.5); } } }, 20, 45);
      /* people walking past on the pavement */
      every(() => { const n = Math.floor(rand(8, 16)), step = rand(0.5, 0.62), g = passing(n * step, 1), t = A.currentTime;
        for (let k = 0; k < n; k++) burst(t + k * step + rand(-0.02, 0.02), 0.045, rand(2200, 3200), 1.5, 0.05, g); }, 6, 16);
      /* the newsboy: "Extra!" and "Paper!", a voice made of two vowels */
      every(() => { const t = A.currentTime + 0.05, p = pan(rand(0.2, 0.6)), out = gain(1); chain(out, p, street);
        const word = (t, f0, vowels) => { const o = A.createOscillator(), g = gain(0); o.type = "sawtooth"; o.frequency.setValueAtTime(f0, t); o.frequency.linearRampToValueAtTime(f0 * 1.25, t + 0.12); o.frequency.linearRampToValueAtTime(f0 * 0.8, t + 0.5);
          const f1 = filt("bandpass", vowels[0][0], 6), f2 = filt("bandpass", vowels[0][1], 8), mix = gain(1); o.connect(f1); o.connect(f2); f1.connect(mix); f2.connect(mix); chain(mix, g, out);
          vowels.forEach(([a, b], i) => { const at = t + i * 0.22; f1.frequency.linearRampToValueAtTime(a, at + 0.05); f2.frequency.linearRampToValueAtTime(b, at + 0.05); });
          g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.05, t + 0.04); g.gain.setValueAtTime(0.05, t + 0.18); g.gain.linearRampToValueAtTime(0.01, t + 0.24); g.gain.linearRampToValueAtTime(0.045, t + 0.3); g.gain.linearRampToValueAtTime(0, t + 0.5); o.start(t); o.stop(t + 0.55); };
        const f0 = rand(270, 320); word(t, f0, [[530, 1840], [750, 1200]]); burst(t + 0.2, 0.05, 4000, 2, 0.03, out); word(t + 0.7, f0, [[530, 1840], [750, 1200]]);
        if (Math.random() < 0.5) word(t + 1.6, f0 * 0.95, [[660, 1700], [500, 1400]]); }, 18, 40);
      /* from the bay: gulls, and once in a while the foghorn */
      every(() => { const t = A.currentTime, p = pan(rand(-0.9, 0.9)); p.connect(street); const n = Math.floor(rand(2, 4));
        for (let k = 0; k < n; k++) { const a = t + k * rand(0.35, 0.5), o = A.createOscillator(), g = gain(0); o.type = "triangle";
          o.frequency.setValueAtTime(1500, a); o.frequency.exponentialRampToValueAtTime(950, a + 0.28); const w = A.createOscillator(), wg = gain(60); w.frequency.value = 22; chain(w, wg, o.frequency);
          chain(o, filt("bandpass", 1300, 2), g, p); g.gain.setValueAtTime(0, a); g.gain.linearRampToValueAtTime(0.012, a + 0.04); g.gain.linearRampToValueAtTime(0, a + 0.3); o.start(a); w.start(a); o.stop(a + 0.32); w.stop(a + 0.32); } }, 20, 50);
      every(() => { const t = A.currentTime, g = gain(0); chain(g, filt("lowpass", 420), street);
        for (const f of [98, 147]) { const o = A.createOscillator(); o.type = "sawtooth"; o.frequency.value = f; o.connect(g); o.start(t); o.stop(t + 4.2); }
        g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.03, t + 0.8); g.gain.setValueAtTime(0.03, t + 3); g.gain.linearRampToValueAtTime(0, t + 4.2); }, 80, 160);
    }

    /* a gramophone at the back: a slow twelve-bar blues in F, swung, with a clarinet, a piano, a walking bass and brushes */
    function gramophone() {
      const out = gain(0.16), shaper = A.createWaveShaper(), curve = new Float32Array(256);
      for (let i = 0; i < 256; i++) { const x = i / 128 - 1; curve[i] = Math.tanh(1.3 * x) / Math.tanh(1.3); } shaper.curve = curve;
      chain(shaper, filt("highpass", 160), filt("peaking", 1200, 0.8), filt("lowpass", 3800), out, master);
      const hiss = gain(0.003); chain(loopSrc(noise(3)), filt("bandpass", 3000, 0.6), hiss, master);
      const cr = noise(2), d = cr.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() < 0.0004 ? (Math.random() * 2 - 1) : 0;
      const crackle = gain(0.12); chain(loopSrc(cr), filt("highpass", 2000), crackle, master);
      const BPM = 92, beat = 60 / BPM, at8 = (t, k) => t + Math.floor(k / 2) * beat + (k % 2) * beat * 2 / 3;
      const F = 174.61, hz = s => F * Math.pow(2, s / 12);
      const BARS = [0, 5, 0, 0, 5, 5, 0, 0, 7, 5, 0, 7];   /* a quick change to the four in bar two */
      /* the tune: a riff stated, answered and resolved (semitones above F, length in swung eighths) */
      const RIFF = [[[12, 1], [15, 1], [17, 1], [18, 1], [19, 3], [15, 1], [null, 8]], [[12, 1], [15, 1], [17, 1], [18, 1], [19, 3], [15, 1], [null, 8]],
        [[19, 2], [17, 1], [15, 1], [12, 2], [10, 2], [12, 6], [null, 2]], [[7, 1], [10, 1], [12, 1], [15, 2], [12, 1], [10, 1], [7, 1], [5, 4], [3, 1], [0, 3]]];
      const pluck = (t, f, v, len) => { for (const [m, a, dk] of [[1, 1, 1], [2, 0.45, 0.6], [3, 0.2, 0.4], [4, 0.08, 0.3]]) tone1(t, f * m * (1 + rand(-0.001, 0.001)), len * dk, v * a, shaper); };
      const clar = (t, f, len, v) => { const o = A.createOscillator(), g = gain(0), vib = A.createOscillator(), vg = gain(0); o.type = "square"; o.frequency.value = f;
        vib.frequency.value = 5.2; chain(vib, vg, o.frequency); vg.gain.setValueAtTime(0, t); vg.gain.linearRampToValueAtTime(f * 0.006, t + Math.min(len, 0.4));
        chain(o, filt("lowpass", 1500, 0.9), g, shaper); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v, t + 0.035); g.gain.setValueAtTime(v * 0.85, t + len * 0.8); g.gain.linearRampToValueAtTime(0, t + len + 0.06);
        o.start(t); vib.start(t); o.stop(t + len + 0.1); vib.stop(t + len + 0.1); };
      let bar = 0, next = A.currentTime + 0.3;
      const tick = () => {
        while (next < A.currentTime + 0.6) {
          const t = next, root = BARS[bar % 12], nr = BARS[(bar + 1) % 12];
          /* walking bass: root, third, fifth, a half step into the next chord */
          [0, 4, 7, nr + 1].forEach((s, i) => pluck(t + i * beat, hz(root + s - 24 - (i === 3 && nr + 1 > 9 ? 12 : 0)), 0.16, 0.7));
          /* piano: a Charleston figure on the chord's third, seventh and ninth */
          for (const k of [0, 3]) for (const s of [4, 10, 14]) pluck(at8(t, k), hz(root + s), 0.035, 0.9);
          /* brushes: a swish on every beat, a tap on two and four */
          for (let b = 0; b < 4; b++) { burst(t + b * beat, 0.22, 6000, 0.7, 0.012, shaper); burst(at8(t, b * 2 + 1), 0.08, 7000, 0.8, 0.008, shaper); }
          for (const b of [1, 3]) burst(t + b * beat, 0.07, 2500, 1, 0.025, shaper);
          /* the clarinet: a phrase over each pair of bars, every other chorus a little lower */
          const ph = bar % 2 ? null : RIFF[[0, null, 1, null, 2, 3][(bar % 12) / 2]];
          if (ph) { const sh = Math.floor(bar / 12) % 2 ? -5 : 0; let k = 0;
            for (const [s, l] of ph) { if (s != null) clar(at8(t, k), hz(s + sh), l * beat / 2 * 0.95, 0.03); k += l; } }
          next += 4 * beat; bar++;
        }
      };
      const id = setInterval(tick, 150); tick();
      return { out, stop() { clearInterval(id); for (const g of [out, hiss, crackle]) g.gain.setTargetAtTime(0, A.currentTime, 0.3); } };
    }
    const VOL = [0, 0.35, 0.9];
    return {
      set(l) { level = l; if (l && !A) start(); if (!A) return; if (l) A.resume();
        master.gain.setTargetAtTime(VOL[l], A.currentTime, 0.5);
        if (l && !music) { music = gramophone(); mix(); } if (!l && music) { music.stop(); music = null; } },
      mix(o) { Object.assign(MIX, o); mix(); },
      ctx: () => A && level ? { A, out: master } : null,
      on: () => !!(A && level),
      bell() { if (A && level) gong(2, 0.08); },
      rumble(v) { if (A && rumbleG) rumbleG.gain.setTargetAtTime(0.35 * v, A.currentTime, 0.5); },
      pause(h) { if (A && level) h ? A.suspend() : A.resume(); },
      /* the things on the table, when clicked */
      play(what) { if (!A || !level) return; const t = A.currentTime;
        if (what === "cup") { for (let k = 0; k < 4; k++) { const f = rand(3000, 3600); tone1(t + k * 0.16, f, 0.3, 0.05, master); tone1(t + k * 0.16, f * 2.71, 0.2, 0.015, master); } burst(t + 0.75, 0.08, 1500, 2, 0.06, master); }
        if (what === "sugar") for (let k = 0; k < 5; k++) burst(t + k * 0.13, 0.11, rand(5000, 7000), 1.2, 0.06, master);
        if (what === "papers") for (let k = 0; k < 7; k++) burst(t + k * 0.05 + rand(0, 0.03), 0.09, rand(2500, 4500), 0.8, 0.05, master); },
    };
  })();
  /* the things on the table answer a click: the coffee is stirred, the sugar pours, the old papers rustle */
  const TOUCH = {};
  const touched = (k, now = performance.now()) => TOUCH[k] != null && now - TOUCH[k] < 4500 ? (now - TOUCH[k]) / 4500 : null;
  const HOT = {};
  function hotspots() {
    for (const [k, b] of Object.entries(HITS)) { let el = HOT[k];
      if (!el) { el = HOT[k] = document.createElement("button"); el.className = "scene-hit"; el.setAttribute("data-noflip", ""); el.dataset.k = k;
        el.onclick = e => { e.stopPropagation(); TOUCH[k] = performance.now(); AMB.play(k); note(k); loop(); }; desk.appendChild(el); }
      const tip = (window.GAZETTE_HIT || {})[k] || { cup: "Stir the coffee", sugar: "Sugar", papers: "Yesterday's papers" }[k]; el.title = tip; el.setAttribute("aria-label", tip);
      Object.assign(el.style, { left: b.x + "px", top: b.y + "px", width: b.w + "px", height: b.h + "px" }); }
  }
  window.addEventListener("gazette-labels", hotspots);
  /* each answer comes with a short note about the chain: the real block height from the wire, when the wire has it */
  let NOTE = null, noteT = 0;
  function note(k) {
    const b = HITS[k]; if (!b) return;
    const L = window.GAZETTE_LIVE || {}, N = window.GAZETTE_NOTE || {}, h = Number.isFinite(L.height) ? L.height : null;
    const age = h != null && Number.isFinite(L.age) ? L.age + Math.round((Date.now() - L.at) / 1000) : null;
    if (!N[k]) return; const txt = N[k](h, age);
    if (!NOTE) { NOTE = document.createElement("div"); NOTE.className = "scene-note"; NOTE.setAttribute("role", "status"); desk.appendChild(NOTE); }
    NOTE.textContent = txt; NOTE.classList.add("on");
    const w = Math.min(300, desk.clientWidth * 0.3); NOTE.style.width = w + "px";
    NOTE.style.left = Math.max(8, Math.min(desk.clientWidth - w - 8, b.x + b.w / 2 - w / 2)) + "px"; NOTE.style.bottom = (desk.clientHeight - b.y + 8) + "px";
    clearTimeout(noteT); noteT = setTimeout(() => NOTE.classList.remove("on"), 6500);
  }
  /* the button cycles: off, quiet, lively; it always starts off */
  const btn = document.getElementById("bAmb");
  if (btn) { let l = 0;
    const label = () => { const L = window.GAZETTE_AMB || ["Café: off", "Café: quiet", "Café: lively"]; btn.textContent = L[l]; btn.setAttribute("aria-pressed", String(l > 0)); };
    const to = n => { l = n; AMB.set(l); label(); };
    btn.onclick = e => { e.stopPropagation(); to((l + 1) % 3); window.dispatchEvent(new CustomEvent("gazette-cafe", { detail: l })); };
    /* the page's sound switch leads: on opens the café quietly, off closes it */
    window.addEventListener("gazette-sound", e => { if (e.detail && !l) to(1); else if (!e.detail && l) to(0); });
    /* when the reader's sound is already on, the café opens quietly with their first touch of the page (browsers allow sound only after one) */
    const first = e => { removeEventListener("pointerdown", first, true); removeEventListener("keydown", first, true);
      if (e.target && e.target.closest && e.target.closest("#bAmb, #bSnd")) return;
      let on = true; try { on = localStorage.getItem("gazette-sound") !== "off"; } catch (x) {} if (on && !l) to(1); };
    addEventListener("pointerdown", first, true); addEventListener("keydown", first, true);
    label(); window.addEventListener("gazette-labels", label); }
  layout();
  /* for the café walk (cafe.js): the drawn layers, the street on its own, and the sound */
  window.GAZETTE_SCENE = { layers: [BG, LIVE, TRAM, ROOM, STEAM, FX], street, tone, rnd, still, amb: AMB, amb_btn: btn };
})();

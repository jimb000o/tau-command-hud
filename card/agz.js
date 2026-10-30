/* Agorzilla beside the My Tau card, and his mood is the card's (card/index.html calls CardAgz.set(0..4)).
   The puppet and the soft-mesh face come from agorzilla.com (its assets/rig.js): the painted head and trunk are drawn as
   meshes in WebGL, so the picture itself bends. The mouth corners sink and the lower lip pushes up when he is sad, the
   corners lift into a smile when he is happy, the chest breathes, the shoulders slump or lift. Eyes, lids and brows
   are the rig's own pieces. He never walks: sad, he is slow and small (long sighs, a sob, tears, a look down at the
   card); happy, he is quick (weight shifts, chuckles, a little bounce). No WebGL: the flat pictures stay and the
   brows, lids, head and body still carry the mood. */
(() => {
  "use strict";
  const a = document.getElementById("agz"); if (!a) return;
  const W = 760, H = 1140, TEX = 1024;
  const still = matchMedia("(prefers-reduced-motion: reduce)");
  const q = s => a.querySelector(s), gaze = q(".gaze"), dir = q(".dir"), mover = q(".mover"), tears = [...a.querySelectorAll(".tear")];
  const smooth = (x0, x1, x) => { const t = Math.max(0, Math.min(1, (x - x0) / (x1 - x0))); return t * t * (3 - 2 * t); };
  const gauss = (x, y, cx, cy, r) => Math.exp(-((x - cx) * (x - cx) + (y - cy) * (y - cy)) / (r * r));
  const rnd = (lo, hi) => lo + Math.random() * (hi - lo), wait = ms => new Promise(r => setTimeout(r, ms));

  /* ---------- the painted mouth, measured on head.webp (as on agorzilla.com) ---------- */
  const LIP = [[448, 458], [452, 457], [456, 457], [464, 456], [472, 457], [480, 457], [488, 456], [496, 455], [504, 453], [512, 451], [520, 448], [528, 445],
    [536, 442], [544, 440], [552, 437], [560, 436], [568, 434], [576, 431], [584, 428], [588, 426], [592, 424], [596, 422]];
  const lipY = x => {
    if (x <= LIP[0][0]) return LIP[0][1];
    for (let i = 1; i < LIP.length; i++) if (x <= LIP[i][0]) { const [x0, y0] = LIP[i - 1], [x1, y1] = LIP[i]; return y0 + (y1 - y0) * (x - x0) / (x1 - x0); }
    return LIP[LIP.length - 1][1];
  };
  const MX0 = 453, MX1 = 591, MOUTH_C = [522, 447], MAXO = 34;
  const col = x => (x <= MX0 || x >= MX1 ? 0 : Math.pow(Math.sin(Math.PI * (x - MX0) / (MX1 - MX0)), .8));

  /* ---------- springs, so every change eases in and settles; sad ones are slow ---------- */
  const spring = (k, d) => ({ v: 0, vel: 0, t: 0, k, d });
  const P = { open: spring(420, 34), smile: spring(60, 14), sad: spring(40, 12), nose: spring(500, 30), shift: spring(16, 7.5), crouch: spring(170, 11), shrug: spring(70, 13), sigh: spring(14, 6) };
  const set = (k, t) => { P[k].t = t; };
  const step = dt => { for (const k in P) { const s = P[k]; s.vel += (s.k * (s.t - s.v) - s.d * s.vel) * dt; s.v += s.vel * dt; } };

  function face(x, y, out) {
    if (x < 370 || x > 690 || y < 330 || y > 610) { out[0] = out[1] = 0; return; }
    const o = P.open.v, sm = P.smile.v, sd = P.sad.v, ns = P.nose.v;
    let dx = 0, dy = 0, g;
    // smiling lifts the corners and the cheeks
    g = gauss(x, y, 454, 457, 26); dx -= 4.5 * sm * g; dy -= 7.5 * sm * g;
    g = gauss(x, y, 590, 426, 24); dx += 4 * sm * g; dy -= 7 * sm * g;
    dy -= 4 * sm * (gauss(x, y, 440, 425, 55) + gauss(x, y, 605, 395, 50));
    // sad: the corners sink and draw in, the middle of the lower lip pushes up into a pout, the cheeks fall
    g = gauss(x, y, 452, 462, 24); dx += 4 * sd * g; dy += 15 * sd * g;
    g = gauss(x, y, 592, 430, 22); dx -= 4 * sd * g; dy += 15 * sd * g;
    dy -= 7 * sd * gauss(x, y, 522, 462, 22) * smooth(440, 456, y);
    dy += 3 * sd * (gauss(x, y, 440, 430, 50) + gauss(x, y, 605, 400, 45));
    // the nose twitches up when he sniffs
    g = gauss(x, y, 505, 398, 28); dy -= 4 * ns * g; dx += (x - 505) * .04 * ns * g;
    dy -= o * 5 * col(x) * Math.exp(-Math.pow((y - lipY(x)) / 16, 2));
    dy += o * MAXO * .3 * (gauss(x, y, 440, 505, 55) + gauss(x, y, 612, 490, 45));
    out[0] = dx; out[1] = dy;
  }
  const jaw = x => { const c = col(x); return [0, P.open.v * MAXO * c]; };
  let breath = 0;
  function trunk(x, y, out) {
    if (y > 880) { out[0] = out[1] = 0; return; }
    const up = smooth(860, 600, y), low = smooth(880, 520, y), br = breath + P.sigh.v, sx = P.shift.v, cr = P.crouch.v, sh = P.shrug.v;
    let dx = 0, dy = 0, g;
    g = gauss(x, y, 480, 700, 160) * .02 * br; dx += (x - 480) * g; dy += (y - 700) * g;
    dy -= br * 2.6 * up;
    dx += sx * 14 * Math.pow(up, 1.2); dy -= sx * 4 * ((x - 470) / 300) * up;
    dy += cr * 22 * low; dx += cr * 7 * ((x - 470) / 300) * low;
    dy -= sh * 12 * (gauss(x, y, 300, 600, 110) + gauss(x, y, 650, 560, 100)) + sh * 6 * gauss(x, y, 520, 560, 80);
    out[0] = dx; out[1] = dy;
  }

  /* ---------- WebGL: one mesh per painted layer ---------- */
  const VS = `attribute vec2 aPos; attribute vec2 aUV; varying vec2 vUV;
    void main() { vUV = aUV; gl_Position = vec4(aPos.x / ${W}.0 * 2.0 - 1.0, 1.0 - aPos.y / ${H}.0 * 2.0, 0.0, 1.0); }`;
  const FS = `precision mediump float; uniform sampler2D uTex; uniform sampler2D uMask; uniform float uMode; varying vec2 vUV;
    void main() { vec4 c = texture2D(uTex, vUV); float m = texture2D(uMask, vUV).r;
      float k = uMode < .5 ? 1.0 : uMode < 1.5 ? 1.0 - m : m; gl_FragColor = c * k; }`;
  const CVS = `attribute vec2 aPos; attribute vec2 aT; varying vec2 vT;
    void main() { vT = aT; gl_Position = vec4(aPos.x / ${W}.0 * 2.0 - 1.0, 1.0 - aPos.y / ${H}.0 * 2.0, 0.0, 1.0); }`;
  const CFS = `precision mediump float; varying vec2 vT;
    void main() { float u = vT.x, t = vT.y;
      vec3 c = mix(vec3(.07, .02, .025), vec3(.2, .06, .07), smoothstep(.0, .9, t));
      float tongue = smoothstep(.42, .95, t) * (1.0 - smoothstep(.2, .38, abs(u - .55)));
      vec3 tc = mix(vec3(.45, .17, .2), vec3(.66, .32, .35), smoothstep(.55, 1.0, t) * (1.0 - abs(u - .55) * 2.5));
      c = mix(c, tc, tongue * .9); c *= mix(.55, 1.0, smoothstep(.0, .35, t));
      gl_FragColor = vec4(c, 1.0); }`;
  function compile(gl, vs, fs) {
    const p = gl.createProgram();
    for (const [type, src] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) {
      const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      gl.attachShader(p, s);
    }
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    return p;
  }
  function texture(gl, source, sw, sh) {
    const cv = document.createElement("canvas"); cv.width = cv.height = TEX;
    cv.getContext("2d").drawImage(source, 0, 0, sw, sh, 0, 0, TEX, TEX);
    const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, cv);
    gl.generateMipmap(gl.TEXTURE_2D);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }
  function jawMask(rh) {
    const cv = document.createElement("canvas"); cv.width = cv.height = TEX;
    const cx = cv.getContext("2d"), sx = TEX / W, sy = TEX / rh;
    cx.fillStyle = "#000"; cx.fillRect(0, 0, TEX, TEX); cx.fillStyle = "#fff";
    cx.beginPath(); cx.moveTo(MX0 * sx, rh * sy);
    for (let x = MX0; x <= MX1; x += 2) cx.lineTo(x * sx, (lipY(x) + .6) * sy);
    cx.lineTo(MX1 * sx, rh * sy); cx.closePath(); cx.fill();
    return cv;
  }
  function Mesh(img, opts) {
    const rh = opts.rh, px = opts.step, cv = document.createElement("canvas");
    cv.className = img.className + " mesh"; cv.width = W; cv.height = H; cv.setAttribute("aria-hidden", "true");
    const gl = cv.getContext("webgl", { premultipliedAlpha: true, alpha: true, antialias: true });
    if (!gl) throw new Error("no webgl");
    const prog = compile(gl, VS, FS), tex = texture(gl, img, W, rh);
    let mask = null;
    if (opts.jaw) { gl.activeTexture(gl.TEXTURE1); mask = texture(gl, jawMask(rh), TEX, TEX); gl.activeTexture(gl.TEXTURE0); }
    const nx = Math.ceil(W / px) + 1, ny = Math.ceil(rh / px) + 1, n = nx * ny;
    const base = new Float32Array(n * 2), uv = new Float32Array(n * 2), pos = new Float32Array(n * 2), posJ = opts.jaw ? new Float32Array(n * 2) : null;
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) { const k = (j * nx + i) * 2, x = Math.min(W, i * px), y = Math.min(rh, j * px); base[k] = x; base[k + 1] = y; uv[k] = x / W; uv[k + 1] = y / rh; }
    const idx = new (n > 65535 ? Uint32Array : Uint16Array)((nx - 1) * (ny - 1) * 6);
    let c = 0;
    for (let j = 0; j < ny - 1; j++) for (let i = 0; i < nx - 1; i++) { const p0 = j * nx + i, p1 = p0 + 1, p2 = p0 + nx, p3 = p2 + 1; idx.set([p0, p1, p2, p1, p3, p2], c); c += 6; }
    const bUV = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, bUV); gl.bufferData(gl.ARRAY_BUFFER, uv, gl.STATIC_DRAW);
    const bPos = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, bPos); gl.bufferData(gl.ARRAY_BUFFER, pos.byteLength, gl.DYNAMIC_DRAW);
    const bIdx = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, bIdx); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW);
    const loc = { pos: gl.getAttribLocation(prog, "aPos"), uv: gl.getAttribLocation(prog, "aUV"), mode: gl.getUniformLocation(prog, "uMode"), tex: gl.getUniformLocation(prog, "uTex"), mask: gl.getUniformLocation(prog, "uMask") };
    let cav = null;
    if (opts.jaw) {
      const p = compile(gl, CVS, CFS), m = Math.floor((MX1 - MX0) / 2) + 1;
      cav = { p, m, pos: gl.createBuffer(), t: gl.createBuffer(), data: new Float32Array(m * 4), aPos: gl.getAttribLocation(p, "aPos"), aT: gl.getAttribLocation(p, "aT") };
      const t = new Float32Array(m * 4); for (let i = 0; i < m; i++) { const u = i / (m - 1); t.set([u, 0, u, 1], i * 4); }
      gl.bindBuffer(gl.ARRAY_BUFFER, cav.t); gl.bufferData(gl.ARRAY_BUFFER, t, gl.STATIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, cav.pos); gl.bufferData(gl.ARRAY_BUFFER, cav.data.byteLength, gl.DYNAMIC_DRAW);
    }
    const it = idx instanceof Uint32Array ? (gl.getExtension("OES_element_index_uint"), gl.UNSIGNED_INT) : gl.UNSIGNED_SHORT;
    const d = [0, 0];
    function draw(buf, mode) {
      gl.useProgram(prog);
      gl.bindBuffer(gl.ARRAY_BUFFER, bPos); gl.bufferSubData(gl.ARRAY_BUFFER, 0, buf);
      gl.enableVertexAttribArray(loc.pos); gl.vertexAttribPointer(loc.pos, 2, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, bUV); gl.enableVertexAttribArray(loc.uv); gl.vertexAttribPointer(loc.uv, 2, gl.FLOAT, false, 0, 0);
      gl.uniform1f(loc.mode, mode); gl.uniform1i(loc.tex, 0); gl.uniform1i(loc.mask, 1);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
      if (mask) { gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, mask); gl.activeTexture(gl.TEXTURE0); }
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, bIdx); gl.drawElements(gl.TRIANGLES, idx.length, it, 0);
      gl.disableVertexAttribArray(loc.uv);
    }
    return {
      el: cv, img, key: "",
      size(w) { w = Math.max(64, Math.min(W, Math.round(w))); if (cv.width !== w) { cv.width = w; cv.height = Math.round(w * H / W); this.key = ""; } },
      render() {
        if (opts.jaw) { const key = ["open", "smile", "sad", "nose"].map(k => P[k].v.toFixed(3)).join(); if (key === this.key) return; this.key = key; }
        const field = opts.jaw ? face : trunk;
        for (let k = 0; k < n * 2; k += 2) {
          field(base[k], base[k + 1], d); pos[k] = base[k] + d[0]; pos[k + 1] = base[k + 1] + d[1];
          if (posJ) { const j = jaw(base[k]); posJ[k] = pos[k] + j[0]; posJ[k + 1] = pos[k + 1] + j[1]; }
        }
        gl.viewport(0, 0, cv.width, cv.height); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
        gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
        if (!opts.jaw) return draw(pos, 0);
        if (P.open.v > .01) {
          for (let i = 0; i < cav.m; i++) { const x = MX0 + i * 2, y = lipY(x); face(x, y, d); const j = jaw(x); cav.data.set([x + d[0], y + d[1] - 1.5, x + d[0] + j[0], y + d[1] + j[1] + .8], i * 4); }
          gl.useProgram(cav.p);
          gl.bindBuffer(gl.ARRAY_BUFFER, cav.pos); gl.bufferSubData(gl.ARRAY_BUFFER, 0, cav.data);
          gl.enableVertexAttribArray(cav.aPos); gl.vertexAttribPointer(cav.aPos, 2, gl.FLOAT, false, 0, 0);
          gl.bindBuffer(gl.ARRAY_BUFFER, cav.t); gl.enableVertexAttribArray(cav.aT); gl.vertexAttribPointer(cav.aT, 2, gl.FLOAT, false, 0, 0);
          gl.drawArrays(gl.TRIANGLE_STRIP, 0, cav.m * 2); gl.disableVertexAttribArray(cav.aT);
        }
        draw(pos, 1); gl.blendFunc(gl.ONE, gl.ONE); draw(posJ, 2);
      },
    };
  }
  const meshes = [];
  let meshed = false;
  async function build() {
    const parts = [[q(".gaze > img.face"), { rh: 640, step: 8, jaw: true }], [q("img.trunk"), { rh: H, step: 16 }]];
    try {
      await Promise.all(parts.map(([img]) => img.decode ? img.decode() : Promise.resolve()));
      for (const [img, o] of parts) meshes.push(Mesh(img, o));
    } catch (e) { meshes.length = 0; return; }
    for (const m of meshes) { m.img.after(m.el); m.img.hidden = true; m.el.addEventListener("webglcontextlost", e => { e.preventDefault(); undo(); }); }
    a.classList.add("meshed"); meshed = true;
    resize(); new ResizeObserver(resize).observe(a);
  }
  function undo() { for (const m of meshes) { m.el.remove(); m.img.hidden = false; } meshes.length = 0; a.classList.remove("meshed"); meshed = false; }
  function resize() { const w = a.offsetWidth * Math.min(2, devicePixelRatio || 1); for (const m of meshes) m.size(w); }

  /* ---------- the five moods: face, posture and pace ---------- */
  const MOODS = [
    { smile: 0, sad: 1, crouch: .3, shrug: -.55, lid: .32, bu: .5, bf: -1, ht: 6, hy: 3.5, ey: 4, ex: -2, br: [6.5, .6], gap: [3500, 6500], tear: 1 },
    { smile: 0, sad: .55, crouch: .15, shrug: -.3, lid: .2, bu: .35, bf: -.7, ht: 3.5, hy: 2, ey: 3, ex: -2, br: [5.6, .8], gap: [4500, 8000], tear: .35 },
    { smile: .3, sad: 0, crouch: 0, shrug: 0, lid: .08, bu: 0, bf: 0, ht: 1, hy: .4, ey: 1, ex: -1, br: [4.4, 1], gap: [5000, 9000], tear: 0 },
    { smile: .7, sad: 0, crouch: -.05, shrug: .1, lid: 0, bu: .4, bf: 0, ht: -1.5, hy: -.6, ey: 0, ex: 0, br: [3.8, 1.1], gap: [3500, 7000], tear: 0 },
    { smile: 1, sad: 0, crouch: -.1, shrug: .2, lid: 0, bu: .55, bf: .1, ht: -3, hy: -1.2, ey: -1, ex: 0, br: [3.2, 1.2], gap: [2500, 5000], tear: 0 },
  ];
  let M = 2, cur = MOODS[2];
  const css = (k, v) => a.style.setProperty(k, v);
  const eyes = (x, y) => { css("--ex", (cur.ex + x) + "%"); css("--ey", (cur.ey + y) + "%"); };
  const head = (dt = 0, dy = 0, ms) => { css("--hd", (ms || (M < 2 ? 2200 : 900)) + "ms"); css("--ht", (cur.ht + dt) + "deg"); css("--hy", (cur.hy + dy) + "%"); };
  function apply() {
    set("smile", cur.smile); set("sad", cur.sad); set("crouch", cur.crouch); set("shrug", cur.shrug);
    css("--lid", cur.lid); css("--bu", cur.bu); css("--bf", cur.bf); eyes(0, 0); head();
    a.dataset.m = M;
  }

  /* ---------- acting: never walking, always in the mood ---------- */
  const pulses = [];
  const pulse = (ms, f) => { const t = performance.now(); pulses.push([t, t + ms, f]); };
  const blink = (slow) => a.animate([{ "--blink": 0 }, { "--blink": 1, offset: .35 }, { "--blink": 1, offset: slow ? .6 : .45 }, { "--blink": 0 }], { duration: slow ? 560 : 260 }).finished.catch(() => {});
  const cry = () => { const t = tears[Math.random() < .6 ? 0 : 1]; return t.animate([{ opacity: 0, transform: "scale(.4)" }, { opacity: .9, transform: "scale(1)", offset: .2 }, { opacity: .9, transform: "translate(-5%, 90%) scale(1, 1.15)", offset: .42 }, { opacity: .7, transform: "translate(-15%, 280%) scale(.9, 1.25)", offset: .85 }, { opacity: 0, transform: "translate(-20%, 340%) scale(.6)" }], { duration: 3800, easing: "ease-in" }).finished.catch(() => {}); };
  const hop = h => mover.animate([{ transform: "none" }, { transform: `translateY(-${h}%) scale(.98, 1.03)`, offset: .45, easing: "ease-in" }, { transform: "scale(1.03, .96)", offset: .78 }, { transform: "none" }], { duration: 640 }).finished.catch(() => {});
  const ACTS = {
    // a long breath in, the shoulders rise, then everything sinks lower than before
    sigh: async () => { set("sigh", 2.2); set("shrug", cur.shrug + .35); head(-1.5, -.8, 1600); await wait(1500); set("sigh", -.8); set("shrug", cur.shrug - .25); head(2, 1, 1800); pulse(1400, t => ({ open: .1 * Math.sin(t * Math.PI) })); await wait(2200); set("sigh", 0); set("shrug", cur.shrug); head(); await wait(600); },
    // a sob: two small catches of breath, a sniff, and a tear
    sob: async () => { cry(); for (let k = 0; k < 2; k++) { set("shrug", cur.shrug + .4); pulse(160, t => ({ nose: Math.sin(t * Math.PI) })); await wait(170); set("shrug", cur.shrug); await wait(260); } await blink(true); await wait(1400); },
    // he looks down at the empty card, then away
    lookCard: async () => { eyes(-6, 2); head(1.5, .5, 1800); await wait(rnd(1800, 2600)); eyes(0, 0); head(); await wait(800); },
    tear: async () => { await cry(); },
    shift: async () => { const s = (Math.random() < .5 ? -1 : 1) * rnd(.4, .8); set("shift", s); await wait(rnd(2200, 3600)); set("shift", 0); await wait(600); },
    sniff: async () => { for (let k = 0; k < 3; k++) { pulse(140, t => ({ nose: Math.sin(t * Math.PI) })); await wait(170); } await wait(400); },
    glance: async () => { eyes(-5, 1); head(.5, 0); await wait(rnd(1000, 1700)); eyes(0, 0); head(); await wait(400); },
    chuckle: async () => { set("shrug", cur.shrug + .25); for (let k = 0; k < 4; k++) { pulse(130, t => ({ open: .3 * Math.sin(t * Math.PI), smile: 1 })); await wait(150); } set("shrug", cur.shrug); a.classList.add("squint"); await wait(500); a.classList.remove("squint"); },
    bounce: async () => { set("crouch", .7); await wait(200); set("crouch", -.3); pulse(700, t => ({ open: .18 * Math.sin(t * Math.PI), smile: 1 })); await hop(M === 4 ? 6 : 3.5); P.crouch.v = .5; set("crouch", cur.crouch); await wait(500); },
    perk: async () => { css("--bu", cur.bu + .5); eyes(2, -2); await wait(900); css("--bu", cur.bu); eyes(0, 0); },
  };
  const POOL = [
    ["sob", "sigh", "sigh", "lookCard", "tear"],
    ["sigh", "lookCard", "tear", "shift", "lookCard"],
    ["shift", "glance", "sniff", "glance", "shift"],
    ["shift", "chuckle", "glance", "perk", "bounce"],
    ["chuckle", "bounce", "shift", "perk", "chuckle", "bounce"],
  ];
  let busy = false;
  async function act(k) { if (busy || still.matches) return; busy = true; try { await ACTS[k](); } finally { busy = false; } }
  (function life() { setTimeout(async () => { if (!document.hidden && a.offsetParent) { const p = POOL[M]; await act(p[Math.floor(Math.random() * p.length)]); } life(); }, rnd(...cur.gap)); })();
  (function blinkLoop() { setTimeout(async () => { if (!document.hidden && !still.matches) { await blink(M < 2); if (M >= 2 && Math.random() < .2) { await wait(120); await blink(); } } blinkLoop(); }, rnd(2600, 6000) * (M < 2 ? 1.3 : 1)); })();
  /* his eyes find the pointer when it comes near; a sad Agorzilla only half looks up */
  addEventListener("pointermove", e => {
    if (still.matches || busy || !a.offsetParent) return;
    const r = a.getBoundingClientRect(), cx = r.left + r.width * .5, cy = r.top + r.height * .3, dx = e.clientX - cx, dy = e.clientY - cy;
    if (Math.hypot(dx, dy) > 560) return eyes(0, 0);
    const k = M < 2 ? .5 : 1;   // mirrored: he faces left, so a pointer to the right is behind his right shoulder
    eyes(Math.max(-5, Math.min(5, -dx / 40)) * k, Math.max(-4, Math.min(4, dy / 50)) * k);
  }, { passive: true });
  a.addEventListener("click", () => act(M >= 3 ? "bounce" : M === 2 ? "perk" : "sob"));

  /* ---------- the frame loop: breathing, springs, mesh ---------- */
  let last = 0, phase = 0;
  function frame(now) {
    requestAnimationFrame(frame);
    const dt = Math.min(.05, (now - (last || now)) / 1000); last = now;
    if (document.hidden || !a.offsetParent) return;
    phase += dt / cur.br[0]; breath = still.matches ? 0 : cur.br[1] * Math.sin(phase * Math.PI * 2);
    let open = 0, smile = cur.smile, nose = 0;
    for (let i = pulses.length - 1; i >= 0; i--) {
      const [t0, t1, f] = pulses[i];
      if (now >= t1) { pulses.splice(i, 1); continue; }
      if (now >= t0) { const o = f((now - t0) / (t1 - t0)) || {}; if (o.open != null) open = Math.max(open, o.open); if (o.smile != null) smile = o.smile; if (o.nose != null) nose = Math.max(nose, o.nose); }
    }
    set("open", open); set("smile", smile); set("nose", nose);
    for (let t = dt; t > 0; t -= 1 / 120) step(Math.min(t, 1 / 120));
    if (meshed) {
      for (const m of meshes) m.render();
      const d = [0, 0], s = a.offsetWidth / W;
      trunk(520, 560, d); css("--nx", (d[0] * s).toFixed(2) + "px"); css("--ny", (d[1] * s).toFixed(2) + "px");
    } else {
      // no mesh: the body still breathes and slumps as one piece
      css("--nx", "0px"); css("--ny", ((P.crouch.v * 22 - (breath + P.sigh.v) * 2.6 - P.shrug.v * 6) * a.offsetWidth / W).toFixed(2) + "px");
    }
  }

  window.CardAgz = {
    set(m) {
      m = Math.max(0, Math.min(4, m | 0)); if (m === M && a.dataset.m) return;
      const up = m > M; M = m; cur = MOODS[m]; apply();
      if (up && m >= 3) setTimeout(() => act("bounce"), 700);
    },
    act, _P: P,
  };
  apply();
  if (window.WebGLRenderingContext) { if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build); else build(); }
  requestAnimationFrame(frame);
})();

/* Your hands on the cabin keyboard: they type what you type. On a monitor 1600 px and wider the camera sits back
   (scene.js) and the painted keyboard shows; painted hands rest on it, and each key you press is pressed by the finger
   that would press it, at the same moment.

   - nomemo/art/hands/hands.json lists, per cabin painting, the resting hands (a picture over cabin.json "hands") and one
     small cut-out per finger (box = where it sits, as fractions of the hands picture); a pressed key taps that finger
     down onto the keyboard, and its hand gives a little. Until it is there, nothing shows.
   - Fingers by touch typing: l5 … l2 the left hand from the little finger, r2 … r5 the right hand, thumb the space bar.
   - Any key typed while the page has focus counts (the terminal's command line most of all); the finger stays down while
     the key is held, at least 90 ms, so a fast typist still sees every tap. */
(() => {
  const root = document.documentElement, BASE = "art/hands/";
  const FINGER = {};
  for (const [f, keys] of Object.entries({ l5: "`1qaz!~", l4: "2wsx@", l3: "3edc#", l2: "45rtfgvb$%", r2: "67yuhjnm^&", r3: "8ik,*<", r4: "9ol.(>", r5: "0p;/-=[]'\\\")_+{}:?|" }))
    for (const k of keys) FINGER[k] = f;
  let thumbs = 0;
  const SPECIAL = { " ": () => (thumbs++ % 2 ? "lt" : "thumb"), Enter: "r5", Backspace: "r5", Tab: "l5", Escape: "l5", ArrowUp: "r3", ArrowDown: "r3", ArrowLeft: "r2", ArrowRight: "r4", Delete: "r5" };
  let cabin = null, art = null, layer = null, src = null;
  const down = {}, since = {};

  function build() {
    const sway = document.querySelector(".cab-sway"), img = sway && sway.querySelector("img"); if (!img || !cabin || !art) return;
    const name = (img.getAttribute("src") || "").split("/").pop();
    if (name === src && layer && layer.isConnected) return;
    if (layer) layer.remove(); layer = null; src = name;
    const v = cabin.variants.find(x => x.src === name), a = art.variants && art.variants[name];
    if (!v || !v.hands || !a) return;
    const [x0, y0, x1, y1] = v.hands;
    layer = document.createElement("div"); layer.className = "cab-hands"; layer.setAttribute("aria-hidden", "true");
    Object.assign(layer.style, { left: x0 * 100 + "%", top: y0 * 100 + "%", width: (x1 - x0) * 100 + "%", height: (y1 - y0) * 100 + "%" });
    const rest = new Image(); rest.className = "cab-hands-rest"; rest.alt = ""; rest.decoding = "async"; rest.src = BASE + a.base; layer.append(rest);
    for (const [f, p] of Object.entries(a.poses || {})) {
      const [px0, py0, px1, py1] = p.box, i = new Image(); i.alt = ""; i.decoding = "async"; i.src = BASE + p.src; i.dataset.f = f;
      Object.assign(i.style, { left: px0 * 100 + "%", top: py0 * 100 + "%", width: (px1 - px0) * 100 + "%", height: (py1 - py0) * 100 + "%" });
      layer.append(i);
    }
    rest.onload = () => layer && layer.classList.add("on");
    sway.querySelector(".cab-spill").before(layer);   // under the screen's light, so the green glow falls on the hands too
  }
  function press(f, on) {
    if (!layer) return;
    const i = layer.querySelector('img[data-f="' + f + '"]'); if (!i) return;
    if (on) { down[f] = (down[f] || 0) + 1; since[f] = performance.now(); i.classList.add("down"); layer.classList.add(f[0] === "l" ? "dip-l" : "dip-r"); }
    else {
      down[f] = Math.max(0, (down[f] || 0) - 1); if (down[f]) return;
      const left = 90 - (performance.now() - (since[f] || 0));
      setTimeout(() => { if (down[f]) return; i.classList.remove("down"); if (!layer.querySelector(".down")) layer.classList.remove("dip-l", "dip-r"); }, Math.max(0, left));
    }
  }
  const fingerOf = e => (typeof SPECIAL[e.key] === "function" ? SPECIAL[e.key]() : SPECIAL[e.key]) || FINGER[(e.key || "").toLowerCase()] || (e.key && e.key.length === 1 ? "r2" : null);
  const held = new Map();
  addEventListener("keydown", e => {
    if (!root.classList.contains("scene") || e.ctrlKey || e.metaKey || e.altKey) return;
    if (held.has(e.code)) return;   // auto-repeat: the finger is already down
    const f = fingerOf(e); if (!f) return; held.set(e.code, f); press(f, true);
  }, true);
  addEventListener("keyup", e => { const f = held.get(e.code); if (f) { held.delete(e.code); press(f, false); } }, true);
  addEventListener("blur", () => { for (const [, f] of held) press(f, false); held.clear(); });

  async function start() {
    try {
      const [c, h] = await Promise.all([fetch("art/cabin/cabin.json", { cache: "no-cache" }), fetch(BASE + "hands.json", { cache: "no-cache" })]);
      if (!c.ok || !h.ok) return;
      cabin = await c.json(); art = await h.json();
    } catch (e) { return; }
    build();
    new MutationObserver(build).observe(root, { attributes: true, attributeFilter: ["class"] });
    const sway = document.querySelector(".cab-sway img"); if (sway) new MutationObserver(build).observe(sway, { attributes: true, attributeFilter: ["src"] });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();

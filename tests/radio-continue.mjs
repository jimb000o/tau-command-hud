// Radio Coco carries on across a page change: the next page plays the same song from the bar the last one left,
// instead of picking a new first song (rabbit/music.js, sessionStorage "radio-coco-pos").
import { readFileSync } from "node:fs";
const root = new URL("..", import.meta.url), src = readFileSync(new URL("rabbit/music.js", root), "utf8");
const bad = [], ok = (c, m) => { if (!c) bad.push(m); };
const mem = () => ({ m: {}, getItem(k) { return this.m[k] ?? null; }, setItem(k, v) { this.m[k] = String(v); }, removeItem(k) { delete this.m[k]; } });
/* a fake AudioContext that is enough for build(): every node connects and does nothing */
const node = () => new Proxy(function () {}, { get: (t, k) => (k === "then" ? undefined : k === "getChannelData" ? () => new Float32Array(8) : k === "value" ? 0 : node()), set: () => true, apply: () => node() });
class Ctx { constructor() { this.state = "running"; this.currentTime = 0; this.sampleRate = 8; this.destination = node(); }
  resume() { return Promise.resolve(); } createBuffer() { return node(); } }
for (const k of ["createGain", "createConvolver", "createBiquadFilter", "createBufferSource", "createOscillator", "createAnalyser", "createDynamicsCompressor", "createWaveShaper"]) Ctx.prototype[k] = () => node();
const ss = mem(), ls = mem();
function page() {   // one page load in the same tab: a fresh window, the tab's sessionStorage, the browser's localStorage
  const on = {}, timers = [];
  const w = { sessionStorage: ss, localStorage: ls, AudioContext: Ctx, navigator: {}, document: { visibilityState: "visible" },
    addEventListener: (e, f) => { (on[e] = on[e] || []).push(f); }, setInterval: f => timers.push(f), setTimeout: () => 0 };
  w.window = w;
  new Function(...Object.keys(w), src)(...Object.values(w));
  return { S: w.COVE_SOUND, leave: () => (on.pagehide || []).forEach(f => f()) };
}
const a = page(), first = a.S.song.id;
a.leave();   // radio never really played here: nothing remembered
ok(ss.getItem("radio-coco-pos") === null, "a page where the radio did not play remembered a position");
const b = page(); b.S.start(); b.S.set({ place: "radio" });
const song = b.S.song.id; b.leave();
const pos = JSON.parse(ss.getItem("radio-coco-pos") || "null");
ok(pos && pos.song === song, "the playing song was not remembered: " + JSON.stringify(pos));
for (let i = 0; i < 5; i++) { const c = page(); ok(c.S.song.id === song, "page " + (i + 3) + " switched from " + song + " to " + c.S.song.id); c.S.start(); c.leave(); }
ss.setItem("radio-coco-pos", JSON.stringify({ ...pos, t: Date.now() - 31 * 60000 }));
ok(page().S.song.id !== undefined, "an old position breaks the start");
console.log(bad.length ? "FAIL\n" + bad.join("\n") : "ok: Radio Coco keeps its song across " + 5 + " page changes (first pick " + first + ", kept " + song + ")");
process.exit(bad.length ? 1 : 0);

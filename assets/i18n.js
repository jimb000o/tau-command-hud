/* Tau HUD languages. English is the source text in the pages; a translation is a dictionary keyed by that English text
   (assets/i18n/<lang>/common.js for the shared header, plus one file per page). This file runs first in <head>:
   it picks the language (?lang=zh or ?lang=ja, then the saved choice, else English), loads the dictionaries,
   and translates every text node and hover text as the page builds and updates it. A string without a translation
   stays English, so a page never breaks when its English changes. ?i18n=missing lists untranslated strings in the console.
   Japanese keeps the English colours. Chinese also flips the signal colours to the Chinese convention: red is the positive accent, green means offline or down. */
(() => {
  "use strict";
  const KEY = "tauhud-lang", LANGS = { en: "English", zh: "中文", ja: "日本語" };
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const q = new URLSearchParams(location.search);
  const norm = l => (!l ? null : /^zh/i.test(l) ? "zh" : /^ja/i.test(l) ? "ja" : /^en/i.test(l) ? "en" : null);
  let lang = norm(q.get("lang"));
  if (lang) store.set(KEY, lang);
  else lang = norm(store.get(KEY)) || "en";   // a first visit is always English, whatever the browser language; 中文 and 日本語 are one click away in the header
  /* the address bar keeps ?lang=zh (or ja), so a link copied from the Chinese site opens in Chinese */
  if (lang !== "en" && q.get("lang") !== lang) try { const u = new URL(location.href); u.searchParams.set("lang", lang); history.replaceState(history.state, "", u.href); } catch (e) {}
  const me = document.currentScript, ROOT = me && me.src ? new URL("..", me.src) : new URL("/", location.href);
  const api = window.TauI18n = {
    lang, langs: LANGS, strings: new Map(), upper: new Map(), patterns: [],   // lang is also the dictionary folder, assets/i18n/<lang>/
    t: s => s, // translate a whole string (English when there is no translation)
    set(l) { if (!LANGS[l] || l === lang) return; store.set(KEY, l); const u = new URL(location.href); u.searchParams.delete("lang");
      /* same address apart from the #part (English with #p6 on the newspaper): replace() would only jump to the anchor, so reload; the #part is kept */
      if (u.href === location.href) location.reload(); else location.replace(u.href); },
    /* strings: { "English": "译文" }. A key with {a} placeholders is a template: "{n} refused": "{n} 被拒绝";
       whatever fills a placeholder is translated too when it is words (a quoted rule name, a state). */
    add(dict) {
      for (const k in dict.strings || {}) {
        const key = squash(k), v = dict.strings[k];
        if (!/\{\w+\}/.test(key)) { api.strings.set(key, v); api.upper.set(key.toUpperCase(), v); continue; }
        const names = [], src = key.split(/(\{\w+\})/).map(part => { const m = /^\{(\w+)\}$/.exec(part); if (m) { names.push(m[1]); return SLOT[m[1][0]] || "(.*?)"; } return part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }).join("");
        api.patterns.push([new RegExp("^" + src + "$"), (...g) => { let out = v; names.forEach((n, i) => { out = out.split("{" + n + "}").join(api.t(g[i + 1])); }); return out; }]);
      }
      if (dict.patterns) api.patterns.push(...dict.patterns);
      /* the template with the most fixed text first, so "{n} for {x} ({y}), {m} for {z} ({w})" beats "{n} for {x} ({y})" */
      const fixed = re => re.source.replace(/\(.*?\)|\\/g, "").length;
      api.patterns.sort((a, b) => fixed(b[0]) - fixed(a[0]));
    },
  };
  /* placeholder kinds: {n} {m} {a} {b} {c} numbers, {h} {g} hashes or addresses, anything else free text */
  const NUM = "(#?-?[\\d][\\d.,]*)", HASH = "([0-9a-f]{4,}…[0-9a-f]{4,}|[0-9a-f]{8,})";
  const SLOT = { n: NUM, m: NUM, a: NUM, b: NUM, c: NUM, h: HASH, g: HASH, e: "(\\{e\\d+\\})" };   // {e1}: an inline element kept in place
  function squash(s) { return String(s).replace(/\\n|\s+/g, " ").replace(/ +/g, " ").trim(); }
  if (lang === "en") return;

  const page = (() => {
    const p = location.pathname.slice(ROOT.pathname.length).split("/").filter(Boolean)[0] || "hud";
    return /^[a-z]+$/.test(p) && p !== "index.html" ? p : "hud";
  })();
  const html = document.documentElement;
  const ZH = lang === "zh";
  html.lang = ZH ? "zh-CN" : "ja"; html.classList.add("i18n-" + lang, "i18n-cjk", "i18n-wait");
  /* CJK glyphs come from the system fonts (no extra webfont); wide Latin letter-spacing reads badly between ideographs */
  document.write(`<style id="i18n-css">html.i18n-wait body{visibility:hidden}html.i18n-cjk body *:not(svg *){letter-spacing:.03em!important}@media (max-width:700px){html.i18n-cjk header.trail .chip.unoff::after{content:"${ZH ? "非官方 · 与 IDNI 无关" : "非公式 · IDNI とは無関係"}"}}</style>`);
  for (const f of ["common", page]) document.write(`<script src="${ROOT.href}assets/i18n/${lang}/${f}.js"><\/script>`);

  const debug = q.get("i18n") === "missing", missing = window.__i18nMissing = new Set();
  const cache = new Map(), NOISE = /[0-9a-f]*…[0-9a-f]*|\b[0-9a-f]{6,}\b|\bAGRS\b|\b\w+_\w+(\.\w+)*\b|#?\d[\d.,]*/gi;   // hashes, amounts, numbers and code names are not words
  /* a long line built from parts is translated part by part: sentences first, then clauses */
  const SEPS = [". ", "; ", " · ", ": ", ", "], PUNCT = { ". ": "。", "; ": ZH ? "；" : "。", ": ": "：", " · ": " · ", ", ": ZH ? "，" : "、" };
  const words = k => /[A-Za-z]{2}/.test(k.replace(NOISE, ""));
  const one = k => {
    const hit = api.strings.get(k);
    if (hit != null) return hit;
    if (k === k.toUpperCase() && api.upper.has(k)) return api.upper.get(k);   // labels upper-cased by the page
    for (const [re, rep] of api.patterns) { if (re.test(k)) return k.replace(re, rep); }
    return null;
  };
  let held = null;   // while best() tries a text two ways, the misses wait here; only the way it keeps reports them
  const note = k => { if (!debug || k.includes("{e") || missing.has(k)) return; if (held) { held.push(k); return; } missing.add(k); console.debug("[i18n] missing:", k); };
  /* returns [text, letters translated, letters left in English] */
  const letters = k => k.replace(NOISE, "").replace(/[^A-Za-z]/g, "").length;
  function parts(k, level) {
    if (!words(k)) return [k, 0, 0];
    let r = one(k);
    if (r == null && /\.$/.test(k)) { r = one(k.slice(0, -1)); if (r != null) r += /[。！？]$/.test(r) ? "" : "。"; }
    if (r == null && /\w$/.test(k)) { r = one(k + "."); if (r != null) r = r.replace(/[。.]$/, ""); }   // a sentence cut out of a longer line has lost its full stop
    if (r != null) return [r, letters(k), 0];
    for (let l = level; l < SEPS.length; l++) {
      const sep = SEPS[l]; if (!k.includes(sep)) continue;
      let done = 0, left = 0;
      const out = k.split(sep).map(p => { const [t, a, b] = parts(p, l + 1); done += a; left += b; return t; });
      if (done) return [out.join(PUNCT[sep]), done, left];
    }
    return [k, 0, letters(k)];
  }
  const lookup = k => {
    if (!k || !words(k)) return null;   // nothing to translate
    if (/[\u3000-\u9fff\uff00-\uffef]/.test(k)) return api.strings.get(k) ?? null;   // already translated, unless it is a key that quotes Chinese (“EN | 中文”)
    if (cache.has(k)) { const r = cache.get(k); if (r == null) note(k); return r; }
    let [t, done, left] = parts(k, 0);
    const [, pre, core, post] = /^([·•\s]*)([\s\S]*?)([\s·•]*)$/.exec(k);   // "· frozen until block #5" is a fragment of a line; so is "{e1}Headline: text" with a leading bold label
    if (left && core !== k) { const [t2, d2, l2] = parts(core, 0); if (l2 < left) [t, done, left] = [pre + t2 + post, d2, l2]; }
    if (left && /^\{e\d+\}|\{e\d+\}$/.test(k)) {   // "{e1}Headline: text": a bold label before or after the sentence
      let a = "", b = "", c = k, m;
      while ((m = /^\{e\d+\}\s*/.exec(c))) { a += m[0]; c = c.slice(m[0].length); }
      while ((m = /\s*\{e\d+\}$/.exec(c))) { b = m[0] + b; c = c.slice(0, -m[0].length); }
      const [t3, d3, l3] = parts(c, 0); if (l3 < left) [t, done, left] = [a + t3 + b, d3, l3];
    }
    if (left) note(k);
    const r = done && left <= done / 4 ? t : null;   // a line that would stay mostly English stays all English
    if (cache.size > 4000) cache.clear();
    cache.set(k, r);
    return r;
  };
  /* a hover built from several lines: each line on its own, so one unknown line cannot spoil the rest */
  const byLine = s => {
    if (!s.includes("\n")) return null;
    let any = false;
    const out = s.split("\n").map(l => { const r = lookup(squash(l)); if (r != null) { any = true; return r; } return l; });
    return any ? out.join("\n") : null;
  };
  /* whichever of whole-text and line-by-line leaves fewer English words */
  const latin = s => (s.match(/[A-Za-z]{2,}/g) || []).length;
  const best = s => {
    if (!debug) {
      const w = lookup(squash(s)), l = byLine(s.trim());
      if (w == null || l == null) return w ?? l;
      return latin(l) < latin(w) ? l : w;
    }
    const outer = held;
    held = []; const w = lookup(squash(s)), wMiss = held;
    held = []; const l = byLine(s.trim()), lMiss = held;
    held = outer;
    const useL = w == null ? l != null || s.includes("\n") : l != null && latin(l) < latin(w);
    (useL ? lMiss : wMiss).forEach(note);
    return useL ? l ?? w : w;
  };
  api.t = s => { const r = best(s); return r == null ? s : r; };
  const tr = s => {
    const r = best(s);
    if (r == null) return null;
    const lead = /^\s/.test(s) && !/^[，。：；、）]/.test(r) ? " " : "", tail = /\s$/.test(s) ? " " : "";
    return lead + r + tail;
  };
  const SKIP = new Set(["SCRIPT", "STYLE", "CODE", "PRE", "KBD", "TEXTAREA", "NOSCRIPT", "SAMP"]);
  const ATTRS = ["title", "placeholder", "aria-label", "alt", "data-tnt", "data-full", "data-tip"];
  const skip = el => !el || SKIP.has(el.nodeName) || (el.closest && el.closest("[translate=no], .notranslate, code, pre, textarea"));
  const orig = new WeakMap(), wrote = new WeakMap();   // text node → its English source / the translation we put there
  const src = n => { const v = n.nodeValue; if (wrote.get(n) === v) return orig.get(n) || v; return v; };
  function text(n) {
    const v = n.nodeValue; if (!v || wrote.get(n) === v || !/[A-Za-z]/.test(v) || skip(n.parentElement)) return;
    const r = tr(v); if (r != null && r !== v) { orig.set(n, v); wrote.set(n, r); n.nodeValue = r; }
  }
  /* a sentence with a link or bold word inside is several text nodes; translate it whole so the word order can change.
     The inline elements become {e1} {e2} … in the key and keep their place (and listeners) in the translation. */
  const INLINE = new Set(["A", "B", "STRONG", "EM", "I", "SPAN", "CODE", "SMALL", "KBD", "SUB", "SUP", "ABBR", "U", "S", "MARK", "TIME", "Q"]);
  const done = new WeakMap();   // element → its text right after our last block translation
  function block(el) {
    if (!el || el.nodeType !== 1 || skip(el)) return false;
    const kids = el.childNodes; if (kids.length < 2 || kids.length > 13) return false;
    let key = "", els = [], words = false;
    for (const c of kids) {
      if (c.nodeType === 3) { const v = src(c); if (/[\u3000-\u9fff]/.test(v) && !/[A-Za-z]{3}/.test(v)) return false; if (/[A-Za-z]{2}/.test(v)) words = true; key += v; }
      else if (c.nodeType === 1) { if (!INLINE.has(c.nodeName) || c.firstElementChild && c.querySelector("div,p,ul,ol,li,table,br,h1,h2,h3,h4,h5")) return false; els.push(c); key += "{e" + els.length + "}"; }
    }
    if (!els.length || !words) return false;
    const r = lookup(squash(key));
    if (r == null || r === squash(key)) return false;
    if (done.get(el) === el.textContent) return true;   // already shows our translation; writing it again would wake the observer forever
    const bits = r.split(/(\{e\d+\})/), used = new Set();
    for (const b of bits) { const m = /^\{e(\d+)\}$/.exec(b); if (m) { if (used.has(m[1]) || !els[m[1] - 1]) return false; used.add(m[1]); } }
    if (used.size !== els.length) return false;
    const lead = /^\s/.test(key) ? " " : "", nodes = bits.filter(b => b !== "").map(b => { const m = /^\{e(\d+)\}$/.exec(b); if (m) return els[m[1] - 1]; const t = document.createTextNode(b); wrote.set(t, b); return t; });
    if (lead && typeof nodes[0] === "object" && nodes[0].nodeType === 3) nodes[0].nodeValue = lead + nodes[0].nodeValue;
    el.replaceChildren(...nodes);
    els.forEach(walk);
    done.set(el, el.textContent);
    return true;
  }
  function attrs(el) {
    for (const a of ATTRS) { const v = el.getAttribute(a); if (v && /[A-Za-z]/.test(v)) { const r = tr(v); if (r != null && r !== v) el.setAttribute(a, r); } }
    if (el.tagName === "INPUT" && /^(button|submit)$/i.test(el.type) && el.value) { const r = tr(el.value); if (r != null) el.value = r; }
  }
  function walk(root) {
    if (root.nodeType === 3) return block(root.parentElement) || text(root);
    if (root.nodeType !== 1) return;
    if (SKIP.has(root.nodeName)) { if (root.nodeName === "TEXTAREA") attrs(root); return; }   // a text box keeps its text, but its placeholder is ours
    if (root.hasAttributes()) attrs(root);
    block(root);
    const w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, { acceptNode: n => n.nodeType === 1 && SKIP.has(n.nodeName) ? (n.nodeName === "TEXTAREA" && attrs(n), NodeFilter.FILTER_REJECT) : NodeFilter.FILTER_ACCEPT });
    for (let n = w.nextNode(); n; n = w.nextNode()) { if (n.nodeType === 3) text(n); else { if (n.hasAttributes()) { attrs(n); colorEl(n); } block(n); } }
    colorEl(root);
  }

  /* ---------- colours (Chinese only): green ↔ red, so red is the positive accent and green means offline or down; amber stays ---------- */
  const SWAP = { "57,255,138": "255,59,82", "255,77,109": "57,255,138", "185,255,214": "255,190,198", "230,255,240": "255,232,235", "22,192,96": "214,40,64", "229,72,77": "48,164,108" };
  const HEX = { "39ff8a": "ff3b52", "ff4d6d": "39ff8a", "b9ffd6": "ffbec6", "16c060": "d62840", "e5484d": "30a46c" };
  const COLOR_RE = /#(39ff8a|ff4d6d|b9ffd6|16c060|e5484d)\b|rgba?\(\s*(57\s*,\s*255\s*,\s*138|255\s*,\s*77\s*,\s*109|185\s*,\s*255\s*,\s*214|230\s*,\s*255\s*,\s*240|22\s*,\s*192\s*,\s*96|229\s*,\s*72\s*,\s*77)\s*([,/][^)]*)?\)/gi;
  const swap = s => !ZH || typeof s !== "string" || !s ? s : s.replace(COLOR_RE, (m, hex, rgb, rest) => {
    if (hex) return "#" + HEX[hex.toLowerCase()];
    const k = rgb.replace(/\s+/g, ""); return (rest ? "rgba(" : "rgb(") + SWAP[k] + (rest || "") + ")";
  });
  const mine = new WeakMap();   // element → style/fill values we wrote, so our own write is not swapped back
  function colorEl(el) {
    if (!ZH) return;
    for (const a of ["style", "fill", "stroke", "stop-color", "color"]) {
      const v = el.getAttribute(a); if (!v) continue;
      const seen = mine.get(el); if (seen && seen[a] === v) continue;
      const s = swap(v); if (s !== v) { el.setAttribute(a, s); (mine.get(el) || mine.set(el, {}).get(el))[a] = s; }
    }
  }
  const doneSheets = new WeakSet();
  function rules(list) {
    for (const r of list) {
      if (r.style) for (let i = 0; i < r.style.length; i++) {
        const p = r.style[i], v = r.style.getPropertyValue(p), s = swap(v);
        if (s !== v) r.style.setProperty(p, s, r.style.getPropertyPriority(p));
      }
      if (r.cssRules) rules(r.cssRules);
    }
  }
  function sheets() {
    if (!ZH) return;
    for (const sh of document.styleSheets) {
      if (doneSheets.has(sh)) continue;
      let list; try { list = sh.cssRules; } catch (e) { continue; }   // cross-origin font sheets
      if (!list) continue;
      doneSheets.add(sh); rules(list);
    }
  }
  // canvas drawings (chain core, rain, charts) pass their colours as strings
  const C2 = window.CanvasRenderingContext2D && CanvasRenderingContext2D.prototype;
  if (C2 && ZH) for (const p of ["fillStyle", "strokeStyle", "shadowColor"]) {
    const d = Object.getOwnPropertyDescriptor(C2, p); if (!d || !d.set) continue;
    Object.defineProperty(C2, p, { configurable: true, enumerable: d.enumerable, get: d.get, set(v) { d.set.call(this, swap(v)); } });
  }
  if (C2) for (const f of ["fillText", "strokeText", "measureText"]) {   // labels drawn on canvas (the core's watermark and ring labels)
    const orig = C2[f];
    C2[f] = function (t, ...rest) { if (typeof t === "string" && /[A-Za-z]{2}/.test(t)) { const r = tr(t); if (r != null) t = r; } return orig.call(this, t, ...rest); };
  }
  if (window.CanvasGradient && ZH) { const add = CanvasGradient.prototype.addColorStop; CanvasGradient.prototype.addColorStop = function (o, c) { return add.call(this, o, swap(c)); }; }
  const icon = () => ZH && document.querySelectorAll('link[rel~="icon"][type="image/svg+xml"]').forEach(l => {
    if (l.dataset.zh) return; l.dataset.zh = "1";
    l.href = "data:image/svg+xml," + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#09090a"/><circle cx="32" cy="32" r="23" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="3.5"/><path d="M14 33 H23 L27.5 24 L34.5 43 L39 33 H50" fill="none" stroke="#ff3b52" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`);
  });

  const obs = new MutationObserver(list => {
    if (document.readyState === "loading") return;   // the parser can hand over half a text node; the full pass runs at DOMContentLoaded
    let css = false;
    for (const m of list) {
      if (m.type === "characterData") { if (!block(m.target.parentElement)) text(m.target); }
      else if (m.type === "attributes") { if (ATTRS.includes(m.attributeName)) { const v = m.target.getAttribute(m.attributeName); if (v && /[A-Za-z]/.test(v)) { const r = tr(v); if (r != null && r !== v) m.target.setAttribute(m.attributeName, r); } } else colorEl(m.target); }
      else { if (m.addedNodes.length) block(m.target); for (const n of m.addedNodes) { walk(n); if (n.nodeName === "STYLE" || n.nodeName === "LINK") css = true; } }
    }
    if (css) sheets();
  });
  const start = () => {
    if (document.title) { const r = tr(document.title); if (r) document.title = r; }
    walk(document.body); sheets(); icon();
    html.classList.remove("i18n-wait");
  };
  obs.observe(html, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS.concat(["style", "fill", "stroke", "stop-color"]) });
  document.addEventListener("DOMContentLoaded", start);
  addEventListener("load", () => { sheets(); html.classList.remove("i18n-wait"); });
  setTimeout(() => html.classList.remove("i18n-wait"), 2500);   // never leave a page hidden
})();

/* Rule text diff: what a consensus rule proposal changes in the rules in force, line by line.
   The node folds a proposal into the running spec pointwise: every output stream the proposal
   defines gets the new definition, every other stream keeps its old one. So the diff compares the
   whole spec before and after that fold. Same parsing as infra/alerts/explain.py.
   Used by /proposals/, /history/ and the HUD. No dependencies. */
(function () {
  "use strict";
  const GENESIS = "always (\n    o6[t]:bv[16] = i10[t]:bv[16] &&\n    o7[t]:bv[16] = { 1 }:bv[16]\n &&\n    o9[t]:bv[24] = { #x00000a }:bv[24]\n)\n";
  const TOPIC = { o6: "which blocks count as valid", o7: "who may make blocks", o9: "base fee per transaction" };
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const norm = s => s.replace(/\s+/g, "");
  const num = s => +s.slice(1);

  // comment lines start with # but #x… / #b… are literals
  const stripComments = t => t.split("\n").map(l => /^\s*#(?![xb][0-9a-fA-F])/.test(l) ? "" : l).join("\n");
  function body(text) {
    const t = stripComments(text), m = /\balways\s*\(/.exec(t);
    if (!m) return t.trim().replace(/\.$/, "");
    let depth = 0; const start = m.index + m[0].length - 1;
    for (let i = start; i < t.length; i++) {
      if (t[i] === "(") depth++;
      else if (t[i] === ")" && --depth === 0) return t.slice(start + 1, i);
    }
    return t.slice(start + 1);
  }
  function splitAnd(b) {
    const parts = []; let depth = 0, cur = "";
    for (let i = 0; i < b.length; i++) {
      const c = b[i];
      if ("({[".includes(c)) depth++; else if (")}]".includes(c)) depth--;
      if (depth === 0 && b.startsWith("&&", i)) { parts.push(cur); cur = ""; i++; continue; }
      cur += c;
    }
    parts.push(cur);
    return parts.map(p => p.trim()).filter(Boolean);
  }
  // output stream -> the conjunct that defines it
  function clauses(text) {
    const out = {};
    for (const c of splitAnd(body(text))) for (const s of new Set((c.match(/\bo\d+(?=\[t\])/g) || []))) out[s] = c;
    return out;
  }
  function apply(spec, revisions) {
    const next = { ...spec };
    for (const r of revisions || []) Object.assign(next, clauses(r));
    return next;
  }
  // rules in force at a height, from the genesis text and the proposals that took effect before it
  function specAt(h, proposals, genesis) {
    let spec = clauses(genesis || GENESIS);
    proposals.filter(p => p.activatedAt != null && p.activatedAt < h)
      .sort((a, b) => a.activatedAt - b.activatedAt || (a.id < b.id ? -1 : 1))
      .forEach(p => { spec = apply(spec, p.revisions); });
    return spec;
  }

  // the spec as one readable text: always ( clause && clause ... ), streams in order
  function lines(spec) {
    const seen = new Set(), out = [{ i: 0, t: "always (", k: "always (" }];
    const cs = Object.keys(spec).sort((a, b) => num(a) - num(b)).map(s => spec[s]).filter(c => !seen.has(c) && seen.add(c));
    cs.forEach((c, i) => {
      const ls = c.split("\n").map(l => l.replace(/\s+$/, "")).filter(l => l.trim());
      const ind = Math.min(...ls.slice(1).map(l => l.match(/^\s*/)[0].length), 99);
      ls.forEach((l, j) => {
        const rest = j ? l.slice(ind === 99 ? 0 : ind) : l.trim(), t = rest.trimStart();
        // the && joining two clauses is shown but not compared, so adding a clause does not mark the one before it
        out.push({ i: (j ? 8 : 4) + rest.length - t.length, t: t + (j === ls.length - 1 && i < cs.length - 1 ? " &&" : ""), k: t.trim() });
      });
    });
    out.push({ i: 0, t: ")", k: ")" });
    return out;
  }
  function lcs(a, b, eq) {
    const n = a.length, m = b.length, L = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
    for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = eq(a[i], b[j]) ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
    const ops = []; let i = 0, j = 0;
    while (i < n && j < m) {
      if (eq(a[i], b[j])) { ops.push([" ", a[i], b[j]]); i++; j++; }
      else if (L[i + 1][j] >= L[i][j + 1]) ops.push(["-", a[i++]]);
      else ops.push(["+", b[j++]]);
    }
    while (i < n) ops.push(["-", a[i++]]);
    while (j < m) ops.push(["+", b[j++]]);
    return ops;
  }
  const tokens = s => s.match(/\s+|#x[0-9a-fA-F]+|#b[01]+|[A-Za-z_]\w*|\d+|./g) || [];
  // a removed line and the added line that replaces it: mark only the tokens that differ
  function inline(a, b) {
    const ops = lcs(tokens(a), tokens(b), (x, y) => x === y);
    let da = "", db = "";
    for (const [op, x] of ops) {
      if (op === " ") { da += esc(x); db += esc(x); }
      else if (op === "-") da += /^\s+$/.test(x) ? esc(x) : `<del>${esc(x)}</del>`;
      else db += /^\s+$/.test(x) ? esc(x) : `<ins>${esc(x)}</ins>`;
    }
    return [da, db];
  }

  /* diff(spec, revisions) -> { rows: [{op, html}], added, removed, streams: [changed streams], same: bool }
     Whitespace-only changes to a stream are not changes (the node compares the meaning, and so does explain.py). */
  function diff(spec, revisions) {
    const next = { ...spec }, streams = [];
    for (const [s, c] of Object.entries(apply({}, revisions))) {
      if (spec[s] != null && norm(spec[s]) === norm(c)) continue;
      next[s] = c; streams.push(s);
    }
    streams.sort((a, b) => num(a) - num(b));
    const ops = lcs(lines(spec), lines(next), (x, y) => x.k === y.k);
    const rows = [];
    for (let i = 0; i < ops.length; i++) {
      if (ops[i][0] === " ") { rows.push({ op: " ", i: ops[i][2].i, html: esc(ops[i][2].t) }); continue; }
      const del = [], add = [];
      while (i < ops.length && ops[i][0] !== " ") (ops[i][0] === "-" ? del : add).push(ops[i++][1]);
      i--;
      const pair = Math.min(del.length, add.length), dh = del.map(x => esc(x.t)), ah = add.map(x => esc(x.t));
      for (let j = 0; j < pair; j++) [dh[j], ah[j]] = inline(del[j].t, add[j].t);
      dh.forEach((h, j) => rows.push({ op: "-", i: del[j].i, html: h }));
      ah.forEach((h, j) => rows.push({ op: "+", i: add[j].i, html: h }));
    }
    const added = rows.filter(r => r.op === "+").length, removed = rows.filter(r => r.op === "-").length;
    return { rows, added, removed, streams, same: !added && !removed };
  }
  const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
  function summary(d) {
    if (d.same) return "no difference";
    return [d.added ? `+${plural(d.added, "line")}` : "", d.removed ? `−${plural(d.removed, "line")}` : ""].filter(Boolean).join(", ");
  }

  /* html(spec, revisions, {at, open, patch}) -> a collapsible "Rule text diff" block */
  function html(spec, revisions, o = {}) {
    style();
    const at = o.at != null ? ` at block #${Number(o.at).toLocaleString("en-US")}` : "";
    if (!revisions || !revisions.length) {
      return `<details class="rdiff"${o.open === false ? "" : " open"}><summary><b>Rule text diff</b><span>no rule text</span></summary>
        <p class="rd-note">This proposal carries no rule text${o.patch ? ", only settings (listed below)" : ""}. The rule text in force stays as it is.</p></details>`;
    }
    const d = diff(spec, revisions);
    const what = d.streams.map(s => TOPIC[s] ? `${s} (${TOPIC[s]})` : s);
    const head = d.same
      ? `<p class="rd-note rd-same"><b>No difference.</b> The proposed text equals the rules in force${at}, so nothing changes when it takes effect. The whole rule text is shown in grey.</p>`
      : `<p class="rd-note">Compared with the rules in force${at}. Changes ${what.join(", ")}. <span class="rd-key"><i class="a">+</i> added <i class="r">−</i> removed <i>·</i> grey: unchanged</span></p>`;
    return `<details class="rdiff"${o.open === false ? "" : " open"}><summary><b>Rule text diff</b><span${d.same ? "" : ' class="on"'}>${summary(d)}</span></summary>${head}
      <div class="rd-code" role="table" aria-label="Rule text diff">${d.rows.map(r => `<div class="rd-l rd-${r.op === "+" ? "add" : r.op === "-" ? "del" : "ctx"}" role="row"><span class="rd-g" aria-label="${r.op === "+" ? "added" : r.op === "-" ? "removed" : "unchanged"}">${r.op === "+" ? "+" : r.op === "-" ? "−" : ""}</span><span class="rd-t" style="--n:${r.i}">${r.html}</span></div>`).join("")}</div></details>`;
  }

  let styled = false;
  function style() {
    if (styled || typeof document === "undefined") return;
    styled = true;
    const s = document.createElement("style");
    s.textContent = `
.rdiff { margin: 14px 0 0; }
.rdiff > summary { cursor: pointer; list-style: none; display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; min-height: 28px; padding: 4px 0; }
.rdiff > summary::-webkit-details-marker { display: none; }
.rdiff > summary::before { content: "▸"; color: var(--dim, #8a8a94); width: 10px; }
.rdiff[open] > summary::before { content: "▾"; }
.rdiff > summary b { font: 600 10.5px var(--display, sans-serif); letter-spacing: .18em; text-transform: uppercase; color: var(--dim, #8a8a94); }
.rdiff > summary span { font: 11.5px var(--mono, monospace); color: var(--dim, #8a8a94); }
.rdiff > summary span.on { color: var(--ok, #39ff8a); }
.rd-note { margin: 2px 0 6px; color: var(--dim, #8a8a94); font-size: 12px; }
.rd-note.rd-same b { color: #fff; font-weight: 600; }
.rd-key { white-space: nowrap; }
.rd-key i { font-style: normal; color: var(--dim, #8a8a94); margin-left: 8px; }
.rd-key i.a { color: var(--ok, #39ff8a); }
.rd-code { background: #0c0c0d; border: 1px solid var(--line, rgba(255,255,255,.09)); border-radius: 6px; padding: 6px 0; font: 11.5px/1.55 var(--mono, monospace); max-height: 46vh; overflow: auto; }
.rd-l { display: grid; grid-template-columns: 22px minmax(0, 1fr); padding: 0 10px 0 0; }
.rd-g { text-align: center; user-select: none; }
.rd-t { white-space: pre-wrap; overflow-wrap: anywhere; padding-left: calc(var(--n, 0) * 1ch); }
.rd-ctx { color: #6f6f78; }
.rd-add { color: var(--ok, #39ff8a); background: rgba(57,255,138,.07); box-shadow: inset 2px 0 var(--ok, #39ff8a); }
.rd-del { color: var(--dim, #8a8a94); box-shadow: inset 2px 0 rgba(255,255,255,.28); }
.rd-del .rd-t { text-decoration: line-through; text-decoration-color: rgba(255,255,255,.35); }
.rd-del del { text-decoration: line-through; text-decoration-color: #fff; color: #c9c9cf; background: rgba(255,255,255,.08); border-radius: 2px; }
.rd-add ins { text-decoration: none; background: rgba(57,255,138,.22); color: #b9ffd6; border-radius: 2px; }
@media (max-width: 700px) { .rd-code, .rd-note { font-size: 12px; } .rd-t { padding-left: calc(var(--n, 0) * .5ch); } .rdiff > summary { min-height: 44px; } }`;
    document.head.appendChild(s);
  }

  window.RuleDiff = { GENESIS, clauses, apply, specAt, diff, summary, html };
})();

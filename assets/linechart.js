/* Tau HUD line chart: the chart of the "In numbers" page (/meta/) as a shared piece, so other pages draw time series the
   same way: green line over a soft green fill, hairline grid, a crosshair and a small card on hover, a shaded stretch for
   the part of the range before recording began, dates (or months on long ranges) along the bottom.
   Extras for scores: a band down to a second value per point (p.lo) and dashed threshold lines with a name.

   TauLineChart.draw(box, pts, opts)
     box   an element with a height (position: relative); the chart fills it
     pts   [{t, v, lo?, open?}] in time order, t in ms; v null leaves a gap
     opts  {start, end, step, first?, label, yMin?, yMax?, ticks?, fmt?, thresholds?: [{v, label?}],
            before?: "text for the shaded part", tip(p) -> html, locale?}
   Styles: the page gives the box class "lc" (see .lc rules in status/index.html, same as .chart on /meta/). */
(() => {
  "use strict";
  const DAY = 86400000, HOUR = 3600000;
  const T = s => (window.TauI18n ? TauI18n.t(s) : s);
  const escH = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const f1 = n => n.toFixed(1);
  let uidN = 0;

  function draw(box, pts, opts) {
    const { start, end, step } = opts, first = opts.first ?? start, loc = opts.locale || "en-GB";
    const fmt = opts.fmt || (n => Number(n).toLocaleString("en-US"));
    const shortDate = t => new Date(t).toLocaleDateString(loc, { day: "numeric", month: "short", timeZone: "UTC" });
    const monthDate = t => new Date(t).toLocaleDateString(loc, { month: "short", year: "numeric", timeZone: "UTC" });
    const hourLabel = t => String(new Date(t).getUTCHours()).padStart(2, "0") + ":00";
    const w = Math.max(box.clientWidth, 10), h = Math.max(box.clientHeight, 10);
    const tk = opts.ticks || [0, 25, 50, 75, 100];
    const yMin = opts.yMin ?? tk[0], yMax = opts.yMax ?? tk[tk.length - 1];
    const L = Math.max(...tk.map(v => fmt(v).length)) * 7 + 14, R = 10, top = 10, B = 22, cw = w - L - R, ch = h - top - B;
    const x = t => L + (end === start ? cw / 2 : cw * (t - start) / (end - start));
    const y = v => top + ch - ch * (Math.max(yMin, Math.min(yMax, v)) - yMin) / (yMax - yMin || 1);
    const uid = "lc" + (++uidN);
    /* a monotone curve through the points (Fritsch–Carlson): smooth, but it never swings above or below a real value */
    const path = (arr, key = "v") => {
      const X = arr.map(p => x(p.t)), Y = arr.map(p => y(p[key])), n = arr.length;
      if (n < 3) return arr.map((p, i) => (i ? "L" : "M") + f1(X[i]) + " " + f1(Y[i])).join(" ");
      const d = [], m = [];
      for (let i = 0; i < n - 1; i++) d.push((Y[i + 1] - Y[i]) / (X[i + 1] - X[i] || 1));
      m[0] = d[0]; m[n - 1] = d[n - 2];
      for (let i = 1; i < n - 1; i++) m[i] = d[i - 1] * d[i] <= 0 ? 0 : 2 * d[i - 1] * d[i] / (d[i - 1] + d[i]);
      let s = "M" + f1(X[0]) + " " + f1(Y[0]);
      for (let i = 0; i < n - 1; i++) { const h3 = (X[i + 1] - X[i]) / 3; s += `C${f1(X[i] + h3)} ${f1(Y[i] + m[i] * h3)} ${f1(X[i + 1] - h3)} ${f1(Y[i + 1] - m[i + 1] * h3)} ${f1(X[i + 1])} ${f1(Y[i + 1])}`; }
      return s;
    };
    let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${escH(opts.label || "")}"><defs><linearGradient id="g-${uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#39ff8a" stop-opacity=".18"/><stop offset="1" stop-color="#39ff8a" stop-opacity="0"/></linearGradient></defs>`;
    for (const v of tk) s += `<line class="grid" x1="${L}" x2="${w - R}" y1="${f1(y(v))}" y2="${f1(y(v))}"/><text class="axis" x="${L - 8}" y="${f1(y(v) + 4)}" text-anchor="end">${fmt(v)}</text>`;
    // the part of the range before recording began: shaded, said once
    if (first > start) {
      const xb = x(Math.min(end, first - step / 2));
      s += `<rect class="before" x="${L}" y="${top}" width="${f1(Math.max(0, xb - L))}" height="${ch}"/>`;
      if (xb - L > 150 && opts.before) s += `<text class="before-t" x="${f1((L + xb) / 2)}" y="${f1(top + ch / 2)}" text-anchor="middle">${escH(T(opts.before))}</text>`;
    }
    // thresholds: a dashed line, with its name at the left end when it has one
    for (const th of opts.thresholds || []) s += `<line class="thr" x1="${L}" x2="${w - R}" y1="${f1(y(th.v))}" y2="${f1(y(th.v))}"/>` + (th.label ? `<text class="thr-t" x="${L + 4}" y="${f1(y(th.v) - 4)}">${escH(T(th.label))}</text>` : "");
    // x labels: hours, days, or months on long ranges
    const n = Math.round((end - start) / step) + 1, maxLabels = Math.max(2, Math.floor(cw / 78));
    if (step < DAY && end - start > 2 * DAY) {
      const nd = Math.round((end - start) / DAY), every = Math.ceil(nd / maxLabels), endDay = Math.floor(end / DAY) * DAY;
      for (let t = start + ((DAY - start % DAY) % DAY); t <= end; t += DAY) if ((Math.round((endDay - t) / DAY) % every) === 0 && x(t) - L > 24) s += `<text class="axis" x="${f1(x(t))}" y="${h - 5}" text-anchor="middle">${escH(shortDate(t))}</text>`;
    } else if (step < DAY) {
      const every = [1, 2, 3, 4, 6, 12].find(e => n / e <= maxLabels) || 12;
      for (let i = n - 1; i >= 0; i--) { const t = start + i * step; if (new Date(t).getUTCHours() % every === 0) s += `<text class="axis" x="${f1(x(t))}" y="${h - 5}" text-anchor="middle">${escH(hourLabel(t))}</text>`; }
    } else if (n > 120) {
      const d = new Date(start); d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() + 1);
      const every = Math.ceil(((end - start) / (30 * DAY)) / maxLabels);
      for (let i = 0; d.getTime() <= end; i++, d.setUTCMonth(d.getUTCMonth() + 1)) if (i % every === 0) s += `<text class="axis" x="${f1(x(d.getTime()))}" y="${h - 5}" text-anchor="middle">${escH(monthDate(d.getTime()))}</text>`;
    } else {
      const every = Math.ceil(n / maxLabels);
      for (let i = n - 1; i >= 0; i -= every) { const t = start + i * step; s += `<text class="axis" x="${f1(x(t))}" y="${h - 5}" text-anchor="${i === 0 && n > 1 ? "start" : "middle"}">${escH(shortDate(t))}</text>`; }
    }
    // runs of known points (a gap where nothing was recorded); band down to the lowest value, then fill, then line
    const runs = []; let run = [];
    for (const p of pts) { if (p.v == null) { if (run.length) runs.push(run); run = []; } else run.push(p); }
    if (run.length) runs.push(run);
    for (const r of runs) {
      if (r.some(p => p.lo != null)) {
        const lo = r.map(p => ({ t: p.t, lo: p.lo ?? p.v }));
        if (r.length === 1) s += `<line class="band-l" x1="${f1(x(r[0].t))}" x2="${f1(x(r[0].t))}" y1="${f1(y(r[0].v))}" y2="${f1(y(lo[0].lo))}"/>`;
        else s += `<path class="band" d="${r.map((p, i) => (i ? "L" : "M") + f1(x(p.t)) + " " + f1(y(p.v))).join("")}${lo.slice().reverse().map(p => "L" + f1(x(p.t)) + " " + f1(y(p.lo))).join("")}Z"/>`;
      }
    }
    const known = pts.filter(p => p.v != null), last = known[known.length - 1];
    for (const r of runs) {
      if (r.length < 2) continue;
      const closed = r.filter(p => !p.open), tail = r[r.length - 1];
      s += `<path d="${path(r)} L${f1(x(tail.t))} ${top + ch} L${f1(x(r[0].t))} ${top + ch} Z" fill="url(#g-${uid})"/>`;
      if (closed.length > 1) s += `<path class="line${known.length > 60 ? " fine" : ""}" d="${path(closed)}"/>`;
      if (tail.open && closed.length) s += `<path class="line open" d="${path([closed[closed.length - 1], tail])}"/>`;
    }
    // no dot on every point (the hover shows each one): only the newest; a short history keeps its dots
    if (known.length <= 3) known.forEach(p => { if (p !== last) s += `<circle class="pt" cx="${f1(x(p.t))}" cy="${f1(y(p.v))}" r="3.5"/>`; });
    if (last) s += `<circle class="pt end${last.open ? " open" : ""}" cx="${f1(x(last.t))}" cy="${f1(y(last.v))}" r="4"/>`;
    s += `<line class="xh" y1="${top}" y2="${top + ch}" visibility="hidden"/><circle class="hov" r="5" visibility="hidden"/>`;
    s += `<rect class="ov" x="${L}" y="${top}" width="${cw}" height="${ch}"/></svg><div class="ctip" hidden></div>`;
    box.innerHTML = s;
    if (!opts.tip) return;
    const ov = box.querySelector(".ov"), xh = box.querySelector(".xh"), hv = box.querySelector(".hov"), tipEl = box.querySelector(".ctip");
    const near = e => {
      const r = box.getBoundingClientRect(), z = r.width / w, mx = (e.clientX - r.left) / z;
      let best = null, bd = 1e9; for (const p of known) { const d = Math.abs(x(p.t) - mx); if (d < bd) { bd = d; best = p; } }
      return bd < Math.max(24, cw / n) ? best : null;
    };
    ov.addEventListener("mousemove", e => {
      const p = near(e);
      if (!p) { xh.setAttribute("visibility", "hidden"); hv.setAttribute("visibility", "hidden"); tipEl.hidden = true; return; }
      const px = x(p.t), py = y(p.v);
      xh.setAttribute("x1", px); xh.setAttribute("x2", px); xh.setAttribute("visibility", "visible");
      hv.setAttribute("cx", px); hv.setAttribute("cy", py); hv.setAttribute("visibility", "visible");
      tipEl.innerHTML = opts.tip(p); tipEl.hidden = false;
      const tw = tipEl.offsetWidth, left = px + 14 + tw > w ? px - 14 - tw : px + 14;
      tipEl.style.left = Math.max(0, left) + "px"; tipEl.style.top = Math.max(0, Math.min(py - 20, h - tipEl.offsetHeight - B)) + "px";
    });
    ov.addEventListener("mouseleave", () => { xh.setAttribute("visibility", "hidden"); hv.setAttribute("visibility", "hidden"); tipEl.hidden = true; });
  }
  window.TauLineChart = { draw, DAY, HOUR };
})();

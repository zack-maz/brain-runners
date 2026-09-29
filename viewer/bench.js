// The benchmark page's arithmetic: scales, ticks, the survival line, number formats. Pure: no DOM, so
// `node --test viewer/tests` can run it. The numbers themselves come from bakeoff/bench.py.
(function (root) {
  "use strict";

  // everything from a run (player names, run ids, verdicts) goes through esc() before it becomes markup
  const esc = (value) => String(value).replace(/[&<>"']/g, (c) => "&#" + c.charCodeAt(0) + ";");

  function linear([d0, d1], [r0, r1]) {
    return (v) => (d1 === d0 ? (r0 + r1) / 2 : r0 + ((v - d0) / (d1 - d0)) * (r1 - r0));
  }

  function log([d0, d1], range) {
    const inner = linear([Math.log10(d0), Math.log10(d1)], range);
    return (v) => inner(Math.log10(v));
  }

  // round steps (1, 2 or 5 times a power of ten) from lo to hi, about `count` of them
  function ticks(lo, hi, count) {
    if (!(hi > lo)) return [lo];
    const raw = (hi - lo) / Math.max(1, count);
    const power = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 5, 10].map((m) => m * power).find((s) => s >= raw);
    const out = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(+v.toFixed(10));
    return out;
  }

  // 1, 2 and 5 times each power of ten between lo and hi (for a log axis)
  function logTicks(lo, hi) {
    const out = [];
    for (let p = Math.floor(Math.log10(lo)); p <= Math.ceil(Math.log10(hi)); p++) {
      for (const m of [1, 2, 5]) {
        const v = +(m * Math.pow(10, p)).toPrecision(12);
        if (v >= lo * (1 - 1e-9) && v <= hi * (1 + 1e-9)) out.push(v);
      }
    }
    return out;
  }

  // a log domain around the values, padded by a quarter of a decade each side
  function logDomain(values) {
    const lo = Math.min(...values), hi = Math.max(...values);
    return [lo / Math.pow(10, 0.25), hi * Math.pow(10, 0.25)];
  }

  // the survival curve as a step line: share alive at row r is survival[r]
  function survivalPath(survival, x, y) {
    let d = `M${x(0).toFixed(1)},${y(survival[0]).toFixed(1)}`;
    for (let r = 1; r < survival.length; r++) {
      if (survival[r] !== survival[r - 1]) d += `H${x(r).toFixed(1)}V${y(survival[r]).toFixed(1)}`;
    }
    return d + `H${x(survival.length - 1).toFixed(1)}`;
  }

  // players that have the value, and the ones that do not (drawn apart, never at 0)
  function split(players, key) {
    return {
      placed: players.filter((p) => typeof p[key] === "number" && p[key] > 0),
      missing: players.filter((p) => !(typeof p[key] === "number" && p[key] > 0)),
    };
  }

  // The frontier as a staircase through its players' points (already scaled to the page), cheapest or quickest
  // first: along to the next player's cost or time, then up to its rows. Nothing to draw for fewer than one.
  function frontierPath(points) {
    const sorted = points.slice().sort((a, b) => a.x - b.x || a.y - b.y);
    if (!sorted.length) return "";
    let d = `M${sorted[0].x.toFixed(1)},${sorted[0].y.toFixed(1)}`;
    for (const p of sorted.slice(1)) d += `H${p.x.toFixed(1)}V${p.y.toFixed(1)}`;
    return d;
  }

  const dash = "–";
  const rows = (v) => (v == null ? dash : v.toFixed(1));
  const interval = (lo, hi) => (lo == null ? dash : `${lo.toFixed(1)} to ${hi.toFixed(1)}`);
  const percent = (v) => (v == null ? dash : Math.round(v * 100) + "%");
  const seconds = (v) => (v == null ? dash : v < 0.1 ? v.toFixed(3) + " s" : v.toFixed(2) + " s");
  const usd = (v) => (v == null ? dash : v.toPrecision(2) + " USD");
  const signed = (v) => (v == null ? dash : (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(1));
  // a track's cost as the study charts it: free, the listed price, or Jev's estimate (free to the user)
  const estimate = (p) => (p.cost_basis === "estimate" ? " (estimate)" : "");
  const track = (p) => (p.cost_basis === "free" ? "free" : usd(p.usd_per_track) + estimate(p));
  // a named score: a free player has no rows per cent, and an untimed one no rows per second
  const score = (v, none) => (v == null ? none : v >= 100 ? Math.round(v).toString() : v.toPrecision(3));
  // rows per cent and the price per request: Jev's rest on its estimated price, so they say so, like its track cost
  const perCent = (p) => (p.rows_per_cent == null ? (p.cost_basis === "free" ? "free" : dash) : score(p.rows_per_cent) + estimate(p));
  const price = (p) => (p.cost_basis === "free" ? "free" : usd(p.price_usd) + estimate(p));

  const api = { esc, linear, log, ticks, logTicks, logDomain, survivalPath, split, frontierPath,
                fmt: { rows, interval, percent, seconds, usd, signed, track, score, perCent, price } };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Bench = api;
})(typeof window !== "undefined" ? window : globalThis);

// The Writeup screen's numbers: each `<span data-stat="PLAYER FIELD">` of docs/WRITEUP.html is filled from the
// Charts numbers (GET /charts), so the write-up never says a number the data does not give. Pure and tested; the
// DOM glue is in front.js. The fields are bakeoff/writeup.py's STAT_FIELDS.
(function (root) {
  "use strict";

  const B = typeof module !== "undefined" && module.exports ? require("./bench.js") : root.Bench;
  const { fmt } = B;

  const FIELDS = {
    mean_rows: (p) => fmt.rows(p.mean_rows), ci_low: (p) => fmt.rows(p.ci_low), ci_high: (p) => fmt.rows(p.ci_high),
    median_rows: (p) => fmt.rows(p.median_rows), seeds: (p) => String(p.seeds), finished: (p) => fmt.percent(p.finished),
    usd_per_track: (p) => fmt.track(p), s_per_decision_median: (p) => fmt.seconds(p.s_per_decision_median),
    failed_rate: (p) => fmt.percent(p.failed_rate), rows_per_cent: (p) => fmt.score(p.rows_per_cent, "free"),
    rows_per_second: (p) => fmt.score(p.rows_per_second, "no time"),
  };

  // {text, ok} for one citation. A player with no numbers, an unknown field or no charts is not ok: the page
  // shows it as an error rather than leave a gap that reads like a number.
  function statText(bench, spec) {
    const [player, field, extra] = String(spec).trim().split(/\s+/);
    if (!FIELDS[field] || extra !== undefined) return { text: "[" + spec + "?]", ok: false };
    const p = bench && (bench.players || []).find((q) => q.player === player);
    if (!p) return { text: "[" + player + ": no numbers]", ok: false };
    return { text: FIELDS[field](p), ok: true };
  }

  const api = { FIELDS, statText };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Writeup = api;
})(typeof window !== "undefined" ? window : globalThis);

// The Writeup screen's numbers: each `<span data-stat="PLAYER FIELD">` of docs/WRITEUP.html is filled from the
// Charts numbers over the held-out tracks (GET /charts?scope=held_out), which the write-up's Method promises;
// `<span data-stat="PLAYER FIELD all">` is filled from every recorded track (GET /charts) instead. So the write-up
// never says a number the data does not give. Pure and tested; the DOM glue is in front.js. The fields are
// bakeoff/writeup.py's STAT_FIELDS.
(function (root) {
  "use strict";

  const B = typeof module !== "undefined" && module.exports ? require("./bench.js") : root.Bench;
  const { fmt } = B;

  const FIELDS = {
    mean_rows: (p) => fmt.rows(p.mean_rows), ci_low: (p) => fmt.rows(p.ci_low), ci_high: (p) => fmt.rows(p.ci_high),
    median_rows: (p) => fmt.rows(p.median_rows), seeds: (p) => String(p.seeds), finished: (p) => fmt.percent(p.finished),
    usd_per_track: (p) => fmt.track(p), price_usd: (p) => fmt.price(p),
    s_per_decision_median: (p) => fmt.seconds(p.s_per_decision_median),
    s_per_decision_mean: (p) => fmt.seconds(p.s_per_decision_mean), s_per_track: (p) => fmt.seconds(p.s_per_track),
    failed_rate: (p) => fmt.percent(p.failed_rate), rows_per_cent: (p) => fmt.perCent(p),
    rows_per_second: (p) => fmt.score(p.rows_per_second, "no time"),
  };
  // what each scope's numbers are over, as the page says it
  const SCOPES = { held_out: "the held-out tracks", all: "every recorded track" };

  // The scope a citation asks for ("held_out", or "all" when it ends in `all`), or null when it is not one.
  function scopeOf(spec) {
    const parts = String(spec).trim().split(/\s+/);
    if (!FIELDS[parts[1]] || parts.length > 3 || (parts.length === 3 && parts[2] !== "all")) return null;
    return parts.length === 3 ? "all" : "held_out";
  }

  // {text, ok, scope} for one citation. `scopes` is {held_out, all}: GET /charts' answer for each. A player with no
  // numbers, an unknown field or no charts is not ok: the page shows it as an error rather than leave a gap that
  // reads like a number.
  function statText(scopes, spec) {
    const scope = scopeOf(spec);
    if (!scope) return { text: "[" + spec + "?]", ok: false, scope: null };
    const [player, field] = String(spec).trim().split(/\s+/);
    const charts = scopes && scopes[scope];
    const p = charts && charts.bench && (charts.bench.players || []).find((q) => q.player === player);
    if (!p) return { text: "[" + player + ": no numbers over " + SCOPES[scope] + "]", ok: false, scope };
    return { text: FIELDS[field](p), ok: true, scope };
  }

  // Why a scope the text cites has no numbers at all: said once, above the text, not only on every span.
  function numbersWhy(scopes, specs) {
    const cited = new Set(specs.map(scopeOf).filter(Boolean));
    return Object.keys(SCOPES).filter((scope) => cited.has(scope) && !(scopes && scopes[scope] && scopes[scope].bench))
      .map((scope) => "Numbers over " + SCOPES[scope] + ": " +
        ((scopes && scopes[scope] && scopes[scope].why) || "the charts could not be read").replace(/\.?$/, "."));
  }

  // The line above the text: which tracks its numbers are over. `charts` is the held-out answer, `range` its tracks.
  function scopeLine(charts, range) {
    const n = charts && charts.bench ? charts.track_count : 0;
    return "The numbers are over the held-out tracks " + range[0] + "–" + range[1] + " (" +
      (n ? n + " scored so far" : "none scored yet") + "); one cited over every recorded track says so when pointed at.";
  }

  // The Writeup's two subtabs (decision 62), in the order docs/WRITEUP.html holds its sections: the one asked for
  // when it is one, otherwise Background (competitors). Arrow keys move along the strip and wrap; Home and End go to its ends.
  const TABS = ["competitors", "results"];
  function tabOf(wanted) {
    return TABS.includes(wanted) ? wanted : TABS[0];
  }
  function tabStep(current, key) {
    const at = TABS.indexOf(tabOf(current));
    if (key === "ArrowRight") return TABS[(at + 1) % TABS.length];
    if (key === "ArrowLeft") return TABS[(at - 1 + TABS.length) % TABS.length];
    if (key === "Home") return TABS[0];
    if (key === "End") return TABS[TABS.length - 1];
    return null;
  }

  const api = { FIELDS, SCOPES, scopeOf, statText, numbersWhy, scopeLine, TABS, tabOf, tabStep };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Writeup = api;
})(typeof window !== "undefined" ? window : globalThis);

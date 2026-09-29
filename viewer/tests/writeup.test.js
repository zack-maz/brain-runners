const test = require("node:test");
const assert = require("node:assert/strict");
const Writeup = require("../writeup.js");

const BENCH = { players: [
  { player: "jev_step2", seeds: 100, mean_rows: 144.62, ci_low: 140.1, ci_high: 149.0, median_rows: 150, finished: 0.8,
    usd_per_track: 0.0039, cost_basis: "estimate", s_per_decision_median: 0.187, failed_rate: 0, rows_per_cent: 374.1,
    rows_per_second: 5.63 },
  { player: "fly", seeds: 100, mean_rows: 66.1, cost_basis: "free", usd_per_track: 0, rows_per_cent: null, rows_per_second: null,
    s_per_decision_median: null, failed_rate: 0 },
] };

test("a citation is the number the charts give, formatted as the charts format it", () => {
  assert.deepEqual(Writeup.statText(BENCH, "jev_step2 mean_rows"), { text: "144.6", ok: true });
  assert.deepEqual(Writeup.statText(BENCH, "jev_step2 seeds"), { text: "100", ok: true });
  assert.deepEqual(Writeup.statText(BENCH, "jev_step2 usd_per_track"), { text: "0.0039 USD (estimate)", ok: true });
  assert.deepEqual(Writeup.statText(BENCH, "jev_step2 finished"), { text: "80%", ok: true });
  assert.deepEqual(Writeup.statText(BENCH, "fly usd_per_track"), { text: "free", ok: true });
  assert.deepEqual(Writeup.statText(BENCH, "fly rows_per_cent"), { text: "free", ok: true });
  assert.deepEqual(Writeup.statText(BENCH, "fly rows_per_second"), { text: "no time", ok: true });
});

test("a citation the charts cannot answer says so instead of leaving a gap", () => {
  assert.deepEqual(Writeup.statText(BENCH, "haiku_map mean_rows"), { text: "[haiku_map: no numbers]", ok: false });
  assert.deepEqual(Writeup.statText(BENCH, "fly bogus"), { text: "[fly bogus?]", ok: false });
  assert.deepEqual(Writeup.statText(BENCH, "fly mean_rows more"), { text: "[fly mean_rows more?]", ok: false });
  assert.deepEqual(Writeup.statText(null, "fly mean_rows"), { text: "[fly: no numbers]", ok: false });
});

test("every field the Python side allows is one this side formats", () => {
  const fs = require("node:fs");
  const py = fs.readFileSync(require("node:path").join(__dirname, "..", "..", "bakeoff", "writeup.py"), "utf8");
  const listed = py.match(/STAT_FIELDS = \(([^)]*)\)/)[1].match(/"([a-z_]+)"/g).map((s) => s.slice(1, -1));
  assert.deepEqual(Object.keys(Writeup.FIELDS).sort(), listed.sort());
});

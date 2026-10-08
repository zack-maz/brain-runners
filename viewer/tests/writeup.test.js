const test = require("node:test");
const assert = require("node:assert/strict");
const Writeup = require("../writeup.js");

const BENCH = { players: [
  { player: "jev_step2", seeds: 100, mean_rows: 144.62, ci_low: 140.1, ci_high: 149.0, median_rows: 150, finished: 0.8,
    usd_per_track: 0.0039, cost_basis: "estimate", s_per_decision_median: 0.187, failed_rate: 0, rows_per_cent: 374.1,
    rows_per_second: 5.63, price_usd: 0.00003, s_per_decision_mean: 0.2051, s_per_track: 26.4 },
  { player: "fly", seeds: 100, mean_rows: 66.1, cost_basis: "free", usd_per_track: 0, rows_per_cent: null, rows_per_second: null,
    s_per_decision_median: null, failed_rate: 0 },
] };

// GET /charts?scope=held_out and GET /charts, as the Writeup screen fetches them
const ALL = { players: [{ ...BENCH.players[1], seeds: 120, mean_rows: 70.2 }] };
const SCOPES = { held_out: { bench: BENCH, tracks: [100, 199], track_count: 100 }, all: { bench: ALL } };

test("a citation is the number the held-out charts give, formatted as the charts format it", () => {
  assert.deepEqual(Writeup.statText(SCOPES, "jev_step2 mean_rows"), { text: "144.6", ok: true, scope: "held_out" });
  assert.deepEqual(Writeup.statText(SCOPES, "jev_step2 seeds"), { text: "100", ok: true, scope: "held_out" });
  assert.deepEqual(Writeup.statText(SCOPES, "jev_step2 usd_per_track"), { text: "0.0039 USD (estimate)", ok: true, scope: "held_out" });
  assert.deepEqual(Writeup.statText(SCOPES, "jev_step2 finished"), { text: "80%", ok: true, scope: "held_out" });
  assert.deepEqual(Writeup.statText(SCOPES, "jev_step2 rows_per_cent"), { text: "374 (estimate)", ok: true, scope: "held_out" });
  assert.deepEqual(Writeup.statText(SCOPES, "jev_step2 price_usd"), { text: "0.000030 USD (estimate)", ok: true, scope: "held_out" });
  assert.deepEqual(Writeup.statText(SCOPES, "jev_step2 s_per_decision_mean"), { text: "0.21 s", ok: true, scope: "held_out" });
  assert.deepEqual(Writeup.statText(SCOPES, "jev_step2 s_per_track"), { text: "26.40 s", ok: true, scope: "held_out" });
  assert.deepEqual(Writeup.statText(SCOPES, "fly usd_per_track"), { text: "free", ok: true, scope: "held_out" });
  assert.deepEqual(Writeup.statText(SCOPES, "fly rows_per_cent"), { text: "free", ok: true, scope: "held_out" });
  assert.deepEqual(Writeup.statText(SCOPES, "fly rows_per_second"), { text: "no time", ok: true, scope: "held_out" });
});

test("a citation ending in all is over every recorded track", () => {
  assert.deepEqual(Writeup.statText(SCOPES, "fly mean_rows all"), { text: "70.2", ok: true, scope: "all" });
  assert.deepEqual(Writeup.statText(SCOPES, "fly seeds all"), { text: "120", ok: true, scope: "all" });
  assert.deepEqual(Writeup.statText(SCOPES, "jev_step2 mean_rows all"), { text: "[jev_step2: no numbers over every recorded track]", ok: false, scope: "all" });
});

test("a citation the charts cannot answer says so instead of leaving a gap", () => {
  assert.deepEqual(Writeup.statText(SCOPES, "haiku_map mean_rows"), { text: "[haiku_map: no numbers over the held-out tracks]", ok: false, scope: "held_out" });
  assert.deepEqual(Writeup.statText(SCOPES, "fly bogus"), { text: "[fly bogus?]", ok: false, scope: null });
  assert.deepEqual(Writeup.statText(SCOPES, "fly mean_rows more"), { text: "[fly mean_rows more?]", ok: false, scope: null });
  assert.deepEqual(Writeup.statText(SCOPES, "fly mean_rows all more"), { text: "[fly mean_rows all more?]", ok: false, scope: null });
  assert.deepEqual(Writeup.statText(null, "fly mean_rows"), { text: "[fly: no numbers over the held-out tracks]", ok: false, scope: "held_out" });
});

test("when the charts could not give numbers, the page says why once, for the scopes the text cites", () => {
  const failed = { held_out: { bench: null, why: "no completed track 100–199 of game v2 has been recorded yet." },
                   all: { bench: null, why: "the charts could not be read" } };
  assert.deepEqual(Writeup.numbersWhy(failed, ["fly mean_rows", "fly2 seeds", "fly bogus"]),
    ["Numbers over the held-out tracks: no completed track 100–199 of game v2 has been recorded yet."]);
  assert.deepEqual(Writeup.numbersWhy(failed, ["fly mean_rows all", "fly mean_rows"]).length, 2);
  assert.deepEqual(Writeup.numbersWhy(failed, []), []);
  assert.deepEqual(Writeup.numbersWhy(SCOPES, ["fly mean_rows", "fly mean_rows all"]), []);
  assert.deepEqual(Writeup.numbersWhy(null, ["fly mean_rows"]), ["Numbers over the held-out tracks: the charts could not be read."]);
});

test("the screen says which tracks its numbers are over", () => {
  assert.equal(Writeup.scopeLine(SCOPES.held_out, [100, 199]),
    "The numbers are over the held-out tracks 100–199 (100 scored so far); one cited over every recorded track says so " +
    "when pointed at.");
  assert.equal(Writeup.scopeLine({ bench: null, track_count: 0 }, [100, 199]),
    "The numbers are over the held-out tracks 100–199 (none scored yet); one cited over every recorded track says so " +
    "when pointed at.");
});

test("every field the Python side allows is one this side formats", () => {
  const fs = require("node:fs");
  const py = fs.readFileSync(require("node:path").join(__dirname, "..", "..", "bakeoff", "writeup.py"), "utf8");
  const listed = py.match(/STAT_FIELDS = \(([^)]*)\)/)[1].match(/"([a-z_]+)"/g).map((s) => s.slice(1, -1));
  assert.deepEqual(Object.keys(Writeup.FIELDS).sort(), listed.sort());
});

test("the Writeup opens on Competitors, and the arrow keys, Home and End move between its two tabs", () => {
  assert.deepEqual(Writeup.TABS, ["competitors", "results"]);
  assert.equal(Writeup.tabOf(undefined), "competitors");
  assert.equal(Writeup.tabOf("results"), "results");
  assert.equal(Writeup.tabOf("charts"), "competitors");
  assert.equal(Writeup.tabStep("competitors", "ArrowRight"), "results");
  assert.equal(Writeup.tabStep("results", "ArrowRight"), "competitors");
  assert.equal(Writeup.tabStep("competitors", "ArrowLeft"), "results");
  assert.equal(Writeup.tabStep("results", "Home"), "competitors");
  assert.equal(Writeup.tabStep("competitors", "End"), "results");
  assert.equal(Writeup.tabStep("competitors", "Enter"), null);
});

test("the tabs are the sections of docs/WRITEUP.html, in its order", () => {
  const fs = require("node:fs");
  const html = fs.readFileSync(require("node:path").join(__dirname, "..", "..", "docs", "WRITEUP.html"), "utf8")
    .replace(/<!--[\s\S]*?-->/g, "");
  assert.deepEqual([...html.matchAll(/<section data-tab="([a-z]+)"/g)].map((m) => m[1]), Writeup.TABS);
});

const test = require("node:test");
const assert = require("node:assert/strict");
const Records = require("../records.js");

const skin = (player, name, color, inks) => ({ player, name, about: "", color, inks: inks || {} });
const ROSTER = [
  { id: "fly", name: "Fly", sprite: "fly", skins: [skin("fly", "Looming", "#AEB4BA"), skin("fly2", "Sideways", "#F7768E")] },
  { id: "jev", name: "Jev", sprite: "visor", skins: [skin("jev_step2", "Step 2", "#B8404F"), skin("jev_map", "Map", "#1E2227", { V: "#7AA2F7" })] },
  { id: "bot", name: "Bot", sprite: "bot", skins: [skin("solver", "Solver", "#7AA2F7")] },
];
// the shape of GET /charts (bakeoff/charts.py, with bench.benchmark's numbers) and GET /records' runs
const player = (name, seeds, mean, lo, hi) => ({ player: name, seeds, mean_rows: mean, ci_low: lo, ci_high: hi, ranked: lo != null });
const RECORDS = {
  game: "v2", max_rows: 150, tracks: [100, 1019], why: null, left_out: 3, unreadable: [], tuned_on: { fly2: [1000, 1199] },
  tuned_tracks: { fly2: 12 },
  bench: {
    players: [player("solver", 20, 150, 150, 150), player("jev_step2", 5, 144.6, 129.6, 150), player("fly2", 20, 78.2, 61.8, 94.6),
              player("jev_map", 2, 49.6, null, null)],
    pairs: [
      { a: "jev_step2", b: "fly2", common_seeds: 5, mean_diff: 66.4, ci_low: 11.8, ci_high: 121.0, wins: 5, ties: 0, losses: 0,
        verdict: "jev_step2 ahead", seeds_needed: 5 },
      { a: "fly2", b: "jev_map", common_seeds: 2, mean_diff: 20, ci_low: null, ci_high: null, wins: 2, ties: 0, losses: 0,
        verdict: "too few tracks (2)", seeds_needed: null },
    ],
    notes: [],
  },
  runs: [
    { run_id: "20260925-163957", status: "running", started_at: "2026-09-25T16:39:57", seeds: [1400, 1401, 1402], players: ["fly", "fly2"], game: "v2", current: true },
    { run_id: "20260924-211656", status: "budget_exhausted", started_at: "2026-09-24T21:16:56", seeds: [1001], players: ["jev_step2", "jev_map", "fly"], game: "v2", current: false },
    { run_id: "20260924-100000", status: "running", started_at: null, seeds: [], players: ["<b>x</b>"], game: "v2", current: false },
  ],
  ours: {},
};

test("the leaderboard: ranked players numbered, yardsticks greyed and never ranked, too few tracks said so", () => {
  const rows = Records.board(RECORDS, ROSTER);
  assert.deepEqual(rows.map((r) => [r.rank, r.name, r.tracks, r.value]), [
    ["", "Bot · Solver (yardstick)", "20 tracks", "150.0"], ["1", "Jev · Step 2", "5 tracks", "144.6"],
    ["2", "Fly · Sideways", "20 tracks", "78.2"], ["", "Jev · Map", "2 tracks", "not ranked"]]);
  assert.equal(rows[0].yardstick, true);
  assert.equal(rows[1].lo, (129.6 / 150) * 100);
  assert.equal(rows[3].span, 0);
});

test("fly2 is marked when some of its tracks here are ones it was tuned on (decision 46)", () => {
  const rows = Records.board(RECORDS, ROSTER);
  assert.deepEqual(rows.filter((r) => r.tuned).map((r) => r.player), ["fly2"]);
  assert.equal(Records.tunedHere({ ...RECORDS, tuned_tracks: {} }, "fly2"), false);
  assert.match(Records.boardHtml(rows, []), /Fly · Sideways <span class="warn">tuned on some of these tracks<\/span>/);
});

test("a black skin gets an edge in its own ink, so it can be seen", () => {
  const map = Records.board(RECORDS, ROSTER).find((r) => r.player === "jev_map");
  assert.equal(map.edge, "#7AA2F7");
  assert.equal(Records.board(RECORDS, ROSTER).find((r) => r.player === "fly2").edge, null);
});

test("the notes: the order is no verdict, what is in-sample, what was left out and what could not be read", () => {
  const notes = Records.boardNotes({ ...RECORDS, unreadable: ["20260101-000000"] }, ROSTER);
  assert.match(notes[0], /^Most players have \d+ tracks?: their intervals overlap/);
  assert.equal(notes[1], "Fly · Sideways's numbers were tuned on tracks 1000–1199: 12 of its 20 tracks here are among " +
    "them, so its mean here is partly in-sample.");
  assert.equal(notes[2], "3 older copies of a track left out: each player's track counts once, from its newest run.");
  assert.equal(notes[3], "Could not be read, so not counted: 20260101-000000.");
});

test("a pair reads the same either way round, with its numbers turned", () => {
  const turned = Records.pairOf(RECORDS, "fly2", "jev_step2");
  assert.deepEqual([turned.a, turned.b, turned.mean_diff, turned.ci_low, turned.ci_high, turned.wins, turned.losses],
    ["fly2", "jev_step2", -66.4, -121.0, -11.8, 0, 5]);
  assert.equal(turned.verdict, "jev_step2 ahead");
  assert.equal(Records.pairOf(RECORDS, "fly2", "nobody"), null);
});

test("the head to head: a verdict only when the interval leaves out 0, in the players' labels", () => {
  const v = Records.pairView(Records.pairOf(RECORDS, "jev_step2", "fly2"), ROSTER, 150);
  assert.equal(v.verdict, "Jev · Step 2 ahead");
  assert.equal(v.tell, true);
  assert.equal(v.diff, "+66.4");
  assert.equal(v.interval, "11.8 to 121.0");
  assert.equal(v.needed, "about 5");
  const few = Records.pairView(Records.pairOf(RECORDS, "fly2", "jev_map"), ROSTER, 150);
  assert.equal(few.tell, false);
  assert.equal(few.lo, null);
  assert.equal(few.note, "Too few tracks in common for an interval.");
});

test("chips offer ranked pairs only, the verdicts first", () => {
  assert.deepEqual(Records.chips(RECORDS, ROSTER).map((c) => c.label), ["Jev · Step 2 vs Fly · Sideways"]);
});

test("past runs: only this session's run is live; another that says running is not ours to stream", () => {
  const { total, rows } = Records.pastRuns(RECORDS, ROSTER, true);
  assert.equal(total, 3);
  assert.deepEqual(rows.map((r) => [r.status, r.kind, r.watch]), [["running now", "live", "Watch live"],
    ["budget used up", "warn", "Watch"], ["running elsewhere, or stopped without closing", "warn", "Watch"]]);
  assert.equal(rows[0].tracks, "1400–1402 (3)");
  assert.equal(rows[0].when, "25 Sep 16:39");
  assert.equal(rows[1].players, "Jev · Step 2, Map; Fly · Looming");
  assert.equal(rows[2].when, "-");
  const html = Records.runsHtml(rows);
  assert.equal(html.includes("<b>"), false);
  assert.match(html, /data-watch="20260925-163957" data-now="true"/);
});

test("past runs: the run still playing offers Watch live but no Results until it ends", () => {
  const html = Records.runsHtml(Records.pastRuns(RECORDS, ROSTER, true).rows);
  assert.equal(html.includes('data-results="20260925-163957"'), false);
  assert.match(html, /data-results="20260924-211656"/);
  assert.match(html, /data-results="20260924-100000"/);
});

test("the first ten past runs, then all of them when asked", () => {
  const many = { ...RECORDS, runs: Array.from({ length: 12 }, (_, i) => ({ ...RECORDS.runs[1], run_id: "r" + i })) };
  assert.equal(Records.pastRuns(many, ROSTER, false).rows.length, Records.SHOWN_RUNS);
  assert.equal(Records.pastRuns(many, ROSTER, true).rows.length, 12);
  assert.equal(Records.SHOWN_RUNS, 10);
});

test("the charts' scope counts the different tracks, so a range never reads as every track in it", () => {
  assert.equal(Records.scope({ ...RECORDS, held_out: [100, 199], track_count: 45 }),
    "game v2 · every recorded track: 45 tracks between 100 and 1019 · held out 100–199");
  assert.equal(Records.scope({ ...RECORDS, held_out: [100, 199], tracks: [1001, 1001], track_count: 1 }),
    "game v2 · every recorded track: 1 track, 1001 · held out 100–199");
  assert.equal(Records.scope({ ...RECORDS, held_out: [100, 199], tracks: null, track_count: 0 }), "");
});

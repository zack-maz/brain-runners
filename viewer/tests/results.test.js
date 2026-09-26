const test = require("node:test");
const assert = require("node:assert/strict");
const Results = require("../results.js");

const skin = (player, name) => ({ player, name, about: "", color: "#5FA35A", inks: {} });
const ROSTER = [
  { id: "fly", name: "Fly", sprite: "fly", skins: [skin("fly2", "Sideways")] },
  { id: "jev", name: "Jev", sprite: "visor", skins: [skin("jev_guided", "Guided")] },
  { id: "haiku", name: "Haiku", sprite: "chat", skins: [skin("haiku_guided", "Guided")] },
  { id: "glm", name: "GLM Flash", sprite: "ox", skins: [skin("glm_plain", "Plain")] },
];
// the shape of bakeoff/results.py's players (the report's row, plus the results' own keys)
const entry = (player, track, extra) => ({
  player, runs: track && track.complete ? 1 : 0, incomplete: track && !track.complete ? 1 : 0,
  mean_rows: track && track.complete ? track.rows : null, finished: track && track.finished ? 1 : 0,
  ran_into_gap: 0, jumped_into_gap: 0, dodged_into_gap: 0, jump_share: 0.1728, wrong_moves: 1, fatal_wrong_moves: 1,
  fallback_rate: 0, invalid_rate: 0, error_rate: 0, requests: 81, cache_hits: 0, input_tokens: 68752, output_tokens: 3645,
  paid: true, price_usd: 0.00004, cost_estimate_usd: 0.00324, s_per_row: 0.1754, tracks: track ? [track] : [], ...extra,
});
const track = (rows, extra) => ({ seed: 1000, rows, complete: true, finished: false, death_cause: "jumped_into_gap",
                                  trapped: false, fatal: { row: rows - 1, move: "jump", safe: ["stay"] }, ...extra });
const RESULTS = {
  run_id: "20260921-165433", status: "completed", seeds: [1000], game: { version: "v2", max_rows: 150 },
  players: [
    entry("fly2", track(72), { paid: false, price_usd: 0, requests: 0, input_tokens: 0, output_tokens: 0, s_per_row: 0.494 }),
    entry("jev_guided", track(94)),
    entry("haiku_guided", track(93, { death_cause: "dodged_into_gap" }), { price_usd: 0.0009, cost_estimate_usd: 0.0828, s_per_row: 0.75 }),
  ],
};

test("the cards are ranked by rows survived, each keeping its slot's label", () => {
  const cards = Results.cards(RESULTS, ROSTER);
  assert.deepEqual(cards.map((c) => [c.place, c.label, c.title, c.rows]),
    [[1, "P2", "Jev · Guided", 94], [2, "P3", "Haiku · Guided", 93], [3, "P1", "Fly · Sideways", 72]]);
  assert.deepEqual(cards[0], { place: 1, top: true, label: "P2", player: "jev_guided", title: "Jev · Guided", rows: 94,
                               rowsWord: "rows", death: "Jumped into a gap · row 94", stopped: false, finished: false, perRow: "175 ms",
                               requests: "81", cost: "0.0032 USD", paid: true }); // Lobby.usd, the page's one way to write money
  assert.equal(cards[2].requests, "none (simulated)");
  assert.equal(cards[2].cost, "free");
});

test("ties share a place, and a stopped runner comes last and is never a death", () => {
  const tied = { ...RESULTS, players: [
    entry("jev_guided", track(150, { finished: true, death_cause: null, fatal: null })),
    entry("haiku_guided", track(150, { finished: true, death_cause: null, fatal: null })),
    entry("fly2", track(140, { complete: false, death_cause: null, fatal: null })),
    entry("glm_plain", track(12)),
  ] };
  const cards = Results.cards(tied, ROSTER);
  assert.deepEqual(cards.map((c) => [c.player, c.place]), [["jev_guided", 1], ["haiku_guided", 1], ["glm_plain", 3], ["fly2", 4]]);
  assert.equal(cards[0].death, "Reached the finish line");
  assert.equal(cards[0].finished, true);
  assert.match(Results.cardsHtml(cards, false), /<span class="death">Reached the finish line<\/span>/); // not --bad
  assert.equal(cards[3].death, "Stopped at row 140: not a death");
  assert.equal(cards[3].stopped, true);
  assert.equal(cards[3].top, false);
});

test("free tier and a fighter that never started", () => {
  const out = { ...RESULTS, players: [entry("glm_plain", null, { price_usd: 0, cost_estimate_usd: 0 })] };
  const [card] = Results.cards(out, ROSTER);
  assert.equal(card.cost, "free tier");
  assert.equal(card.death, "Never started");
});

test("a bar per fighter against the track's length, and the solver's line when it did not run", () => {
  const bars = Results.bars(RESULTS, ROSTER);
  assert.deepEqual(bars.map((b) => [b.name, b.rows]), [["Jev · Guided", 94], ["Haiku · Guided", 93],
    ["Fly · Sideways", 72], ["Solver (yardstick)", 150]]);
  assert.equal(bars[0].width, 94 / 150);
  assert.equal(bars[3].yardstick, true);
});

test("the warning names the two best numbers", () => {
  assert.equal(Results.warning(RESULTS, ROSTER),
    "One track is not a result: 94 against 93 rows can be this track's luck. Records holds the benchmark over many tracks.");
  assert.match(Results.warning({ ...RESULTS, players: [RESULTS.players[0]] }, ROSTER), /^One track is not a result\. /);
});

test("More numbers: the wrong moves name the fatal one and what was safe", () => {
  const t = Results.table(RESULTS, ROSTER);
  assert.deepEqual(t.heads, ["Jev · Guided", "Haiku · Guided", "Fly · Sideways"]);
  const row = (name) => t.rows.find((r) => r.name === name).vals;
  assert.deepEqual(row("Wrong moves")[0], "1 · fatal, row 93: jump (stay safe)");
  assert.deepEqual(row("Moves that were jumps"), ["17%", "17%", "17%"]);
  assert.deepEqual(row("Asked live"), ["81", "81", "none (simulated)"]);
  assert.deepEqual(row("Tokens")[0], "68,752 / 3,645");
  assert.deepEqual(row("Cost"), ["0.0032 USD", "0.08 USD", "free"]);
  const trapped = entry("jev_guided", track(20, { trapped: true, fatal: null }), { wrong_moves: 2 });
  assert.equal(Results.wrongText(trapped, true), "2 · trapped at the end: no move there was safe");
});

test("failures appear only when there were any", () => {
  assert.deepEqual(Results.failures(RESULTS, ROSTER), []);
  const failing = { ...RESULTS, players: [entry("haiku_guided", track(9), { fallback_rate: 0.03, error_rate: 0.01, invalid_rate: 0.02 })] };
  assert.deepEqual(Results.failures(failing, ROSTER),
    ["Haiku · Guided: 3.0% of its rows fell back to the default move (errors 1.0%, unreadable answers 2.0%)."]);
});

test("the note says what is left out and what is ours, from the lineup", () => {
  assert.match(Results.note(RESULTS, ROSTER), /The fly is asked nothing; how gaps become its input is ours\./);
  assert.match(Results.note(RESULTS, ROSTER), /an estimate, not a bill/);
  assert.doesNotMatch(Results.note({ ...RESULTS, players: [RESULTS.players[1]] }, ROSTER), /fly/);
});

test("a run of several tracks shows means and deaths counted by cause", () => {
  const many = { ...RESULTS, seeds: [1000, 1001, 1002], players: [entry("jev_guided", null,
    { runs: 3, mean_rows: 71.33, jumped_into_gap: 2, dodged_into_gap: 1, incomplete: 0, finished: 0 })] };
  const [card] = Results.cards(many, ROSTER);
  assert.equal(card.rows, "71.3");
  assert.equal(card.rowsWord, "rows a track");
  assert.equal(card.death, "2 jumped into a gap, 1 dodged into a gap");
  assert.deepEqual(Results.header(many), { left: "Run ended · 1 fighter", right: "Tracks 1000–1002 (3) · game v2 · 150 rows" });
});

test("several tracks: a fighter that finished every track is not drawn as a death, one that fell on some is", () => {
  const many = { ...RESULTS, seeds: [1000, 1001, 1002], players: [
    entry("jev_guided", null, { runs: 3, mean_rows: 150, finished: 3, incomplete: 0 }),
    entry("haiku_guided", null, { runs: 3, mean_rows: 120, finished: 2, jumped_into_gap: 1, incomplete: 0 }),
  ] };
  const cards = Results.cards(many, ROSTER);
  assert.equal(cards[0].death, "3 finished");
  assert.equal(cards[0].finished, true);
  assert.equal(cards[1].finished, false);
  const html = Results.cardsHtml(cards, false);
  assert.match(html, /<span class="death">3 finished<\/span>/); // a finish is not a death
  assert.match(html, /<span class="death bad">2 finished · 1 jumped into a gap<\/span>/);
});

test("the header and the markup, every text escaped", () => {
  assert.deepEqual(Results.header(RESULTS), { left: "Run ended · 3 fighters", right: "Track 1000 · game v2 · 150 rows" });
  assert.equal(Results.header({ ...RESULTS, status: "interrupted" }).left, "Run interrupted · 3 fighters");
  const evil = { ...RESULTS, players: [entry("<b>x</b>", track(3))] };
  const html = Results.cardsHtml(Results.cards(evil, ROSTER), false) + Results.tableHtml(Results.table(evil, ROSTER)) +
    Results.barsHtml(Results.bars(evil, ROSTER), () => "#5FA35A");
  assert.equal(html.includes("<b>"), false);
  assert.match(Results.cardsHtml(Results.cards(RESULTS, ROSTER), true), /^<article class="card leader"/);
  assert.equal(Results.cardsHtml(Results.cards(RESULTS, ROSTER), true).includes("canvas"), false); // More numbers hides the art
});

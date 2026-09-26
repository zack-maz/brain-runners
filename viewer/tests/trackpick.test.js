const test = require("node:test");
const assert = require("node:assert/strict");
const TrackPick = require("../trackpick.js");

const skin = (player, name) => ({ player, name, about: "", color: "#8A9097", inks: {} });
const ROSTER = [
  { id: "fly", name: "Fly", sprite: "fly", skins: [skin("fly2", "Sideways")] },
  { id: "haiku", name: "Haiku", sprite: "chat", skins: [skin("haiku_guided", "Guided")] },
  { id: "glm", name: "GLM Flash", sprite: "ox", skins: [skin("glm_plain", "Plain")] },
];
// the shape of GET /state?seed=1001 (bakeoff/session.py)
const state = (extra) => ({
  status: "lobby", max_rows: 150, requests_per_row: 1, max_requests: 200, tournament: false,
  first_practice_seed: 1000, practice_tracks: 20, seed: 1001,
  players: [
    { name: "fly2", paid: false, price_usd: 0, requests_left: null, played_before: true, seeds_played: [1000, 1001], why_not: null },
    { name: "haiku_guided", paid: true, price_usd: 0.0009, requests_left: 200, played_before: false, seeds_played: [1000], why_not: null },
    { name: "glm_plain", paid: true, price_usd: 0, requests_left: 200, played_before: false, seeds_played: [], why_not: null },
  ],
  ...extra,
});
const LINEUP = ["haiku_guided", "fly2"];

test("a track number is whole and never below the lowest the command allows", () => {
  assert.equal(TrackPick.clampSeed(1004.4, state()), 1004);
  assert.equal(TrackPick.clampSeed(7, state()), 1000);
  assert.equal(TrackPick.clampSeed(7, state({ tournament: true })), 7);
  assert.equal(TrackPick.clampSeed("nope", state()), 1000);
});

test("Random picks a practice track, 1000 to 9999", () => {
  assert.equal(TrackPick.randomSeed(state(), () => 0), 1000);
  assert.equal(TrackPick.randomSeed(state(), () => 0.9999999), 9999);
});

test("the practice tracks, each marked with how many of this lineup played it", () => {
  const tiles = TrackPick.tiles(state(), LINEUP, 1001);
  assert.equal(tiles.length, 20);
  assert.deepEqual([tiles[0].seed, tiles[19].seed], [1000, 1019]);
  assert.deepEqual(tiles.slice(0, 3).map((t) => t.mark), ["2 / 2 played", "1 / 2 played", "new"]);
  assert.deepEqual(tiles.filter((t) => t.current).map((t) => t.seed), [1001]);
});

test("the lineup: each fighter's worst case, free ones said so", () => {
  const [haiku, fly] = TrackPick.lineup(state(), ROSTER, LINEUP);
  assert.deepEqual(haiku, { label: "P1", player: "haiku_guided", title: "Haiku · Guided", played: "new track",
                            cost: "0.14 USD", requests: "150 requests", paid: true, why: null });
  assert.deepEqual(fly, { label: "P2", player: "fly2", title: "Fly · Sideways", played: "played before",
                          cost: "free", requests: "simulated", paid: false, why: null });
  const [glm] = TrackPick.lineup(state(), ROSTER, ["glm_plain"]);
  assert.equal(glm.cost, "free tier");
  assert.equal(glm.paid, false);
  const [capped] = TrackPick.lineup(state({ players: state().players.map((p) => ({ ...p, requests_left: p.paid ? 12 : null })) }),
    ROSTER, ["haiku_guided"]);
  assert.equal(capped.requests, "12 requests"); // the worst case stops where the cap does
});

test("RUN asks once, with the worst case on it, before a run that can spend", () => {
  assert.deepEqual(TrackPick.runButton(state(), LINEUP, 1001, false), { label: "RUN", sub: "Enter", why: null, armed: false });
  assert.deepEqual(TrackPick.runButton(state(), LINEUP, 1001, true),
    { label: "CONFIRM", sub: "spend at most 0.14 USD", why: null, armed: true });
  // a lineup that spends nothing starts at once, armed or not
  assert.equal(TrackPick.runButton(state(), ["fly2"], 1001, true).label, "RUN");
  assert.equal(TrackPick.runButton(state({ max_requests: 0, players: state().players.map((p) => ({ ...p, requests_left: p.paid ? 0 : null })) }),
    LINEUP, 1001, true).label, "RUN");
});

test("RUN cannot be pressed while a run is going or a fighter is refused, and says why", () => {
  assert.equal(TrackPick.runButton(state({ status: "running" }), LINEUP, 1001, false).why, "a run is already going");
  const refused = state({ players: state().players.map((p) => (p.name === "haiku_guided" ? { ...p, why_not: "no <cap> left" } : p)) });
  assert.equal(TrackPick.runButton(refused, LINEUP, 1001, true).why, "no <cap> left");
  assert.match(TrackPick.lineupHtml(TrackPick.lineup(refused, ROSTER, LINEUP)), /no &#60;cap&#62; left/);
});

test("the cap line comes from the state", () => {
  assert.match(TrackPick.capText(state(), LINEUP), /until its cap of 200 runs out/);
  assert.match(TrackPick.capText(state({ max_requests: 0 }), LINEUP), /no cap: the paid runners replay/);
  assert.equal(TrackPick.capText(state(), ["fly2"]), "No paid runner: this run spends nothing.");
});

test("the preview draws the real track: one dark cell per gap on its rows", () => {
  const track = { seed: 1001, lanes: 12, max_rows: 3, gaps: [[], [0, 7], [11], [4]] }; // the last row is past the end
  const svg = TrackPick.previewSvg(track, { runway_rows: 1 });
  assert.equal((svg.match(/class="gap"/g) || []).length, 3);
  assert.match(svg, /viewBox="0 0 12 60"/);
  assert.match(svg, /class="runway"/);
  assert.equal(TrackPick.gapTiles(track), 3);
  assert.equal(TrackPick.previewSvg(null), "");
});

test("the keys: arrows step the track, R picks one, Enter runs, Escape goes back", () => {
  assert.deepEqual(TrackPick.onKey(1001, state(), "ArrowRight"), { seed: 1002, go: null });
  assert.deepEqual(TrackPick.onKey(1000, state(), "ArrowLeft"), { seed: 1000, go: null });
  assert.deepEqual(TrackPick.onKey(1001, state(), "r", () => 0.5), { seed: 5500, go: null });
  assert.equal(TrackPick.onKey(1001, state(), "Enter").go, "run");
  assert.equal(TrackPick.onKey(1001, state(), "Escape").go, "back");
  assert.equal(TrackPick.onKey(1001, state(), "q"), null);
});

test("with no cap, the line says Jev still plays and what the other paid runners do", () => {
  const jev = { name: "jev_step1", paid: true, price_usd: 0.00003, requests_left: null, capped: false,
                played_before: false, seeds_played: [], why_not: null };
  const s = state({ max_requests: 0, players: [...state().players, jev] });
  assert.equal(TrackPick.capText(s, ["jev_step1"]),
    "Jev plays without a cap: every row may cost it a request, counted and priced here. Cached answers are free.");
  assert.match(TrackPick.capText(s, ["jev_step1", "haiku_guided"]),
    /^Jev plays without a cap: .* The other paid runners replay answers already cached and stop at their first uncached question\.$/);
});

test("with a cap, Jev beside a capped runner is still said to play without one", () => {
  const jev = { name: "jev_step1", paid: true, price_usd: 0.00003, requests_left: null, capped: false,
                played_before: false, seeds_played: [], why_not: null };
  const s = state({ players: [...state().players, jev] });
  assert.equal(TrackPick.capText(s, ["jev_step1", "haiku_guided"]),
    "Jev plays without a cap: every row may cost it a request, counted and priced here. The other paid runners " +
    "cost 1 request a row each, until their cap of 200 runs out. Cached answers are free, so the real cost is usually lower.");
});

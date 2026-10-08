const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const Figs = require("../writeup_figs.js");

const REPO = path.join(__dirname, "..", "..");
const STUDY = JSON.parse(fs.readFileSync(path.join(REPO, "docs", "STUDY.json"), "utf8"));

const P = (player, mean_rows, more = {}) => ({ player, seeds: 100, mean_rows, ci_low: mean_rows - 5, ci_high: mean_rows + 5,
  median_rows: mean_rows, finished: 0, usd_per_track: 0, cost_basis: "free", s_per_decision_median: null, rows_per_cent: null,
  rows_per_second: null, failed_rate: 0, ranked: true, yardstick: false, frontier_cost: false, frontier_speed: false, ...more });
const SMALL = {
  players: [P("solver", 149, { yardstick: true, finished: 0.98 }), P("jev_step2", 139, { finished: 0.74, usd_per_track: 0.0037, cost_basis: "estimate",
    s_per_decision_median: 0.1, frontier_cost: true, frontier_speed: true, rows_per_cent: 374, rows_per_second: 5.6 }),
  P("haiku_plain", 45, { seeds: 15, usd_per_track: 0.028, cost_basis: "listed", s_per_decision_median: 0.77 }),
  P("jev_plain", 25, { usd_per_track: 0.001, cost_basis: "estimate", s_per_decision_median: 0.11 }),
  P("fly2", 76, { finished: 0.05, s_per_decision_median: 0.69, frontier_cost: true }), P("random", 22, { yardstick: true })],
  pairs: [{ a: "jev_plain", b: "haiku_plain", common_seeds: 15, mean_diff: -17.2, ci_low: -25.7, ci_high: -8.7, wins: 1, ties: 3,
    losses: 11, mean_a_shared: 28.3, mean_b_shared: 45.5 }],
  notes: ["a note"],
};

test("the fields the figures read are the ones bakeoff/writeup.py cuts the study to, and docs/STUDY.json holds", () => {
  const py = fs.readFileSync(path.join(REPO, "bakeoff", "writeup.py"), "utf8");
  const tuple = (name) => py.match(new RegExp(name + " = \\(([^)]*)\\)"))[1].match(/"([a-z_]+)"/g).map((s) => s.slice(1, -1));
  assert.deepEqual(Figs.PLAYER_FIELDS, tuple("STUDY_PLAYER_FIELDS"));
  assert.deepEqual(Figs.PAIR_FIELDS, tuple("STUDY_PAIR_FIELDS"));
  assert.deepEqual(Object.keys(STUDY).sort(), ["notes", "pairs", "players"]);
  for (const p of STUDY.players) assert.deepEqual(Object.keys(p).sort(), [...Figs.PLAYER_FIELDS].sort());
  for (const q of STUDY.pairs) assert.deepEqual(Object.keys(q).sort(), [...Figs.PAIR_FIELDS].sort());
});

test("every figure slot of docs/WRITEUP.html is one this draws, in order", () => {
  const html = fs.readFileSync(path.join(REPO, "docs", "WRITEUP.html"), "utf8").replace(/<!--[\s\S]*?-->/g, "");
  const keys = [...html.matchAll(/data-fig="([^"]*)"/g)].map((m) => m[1]);
  assert.deepEqual(keys, Figs.KEYS);
});

test("players are named as the write-up names them", () => {
  assert.equal(Figs.nameOf("jev_step2"), "Jev · step-2");
  assert.equal(Figs.nameOf("haiku_plain"), "Claude Haiku · plain");
  assert.equal(Figs.nameOf("fly2"), "Fly · sideways");
  assert.equal(Figs.nameOf("always_jump"), "Bot · Always jump");
  assert.equal(Figs.nameOf("someone_new"), "someone_new");
});

test("numbers are formatted once, the free and the estimated said so", () => {
  assert.equal(Figs.fmt.rows(139.09), "139.1");
  assert.equal(Figs.fmt.usd(SMALL.players[1]), "$0.0037 (est.)");
  assert.equal(Figs.fmt.usd(SMALL.players[4]), "free");
  assert.equal(Figs.fmt.pct(0.74), "74%");
  assert.equal(Figs.fmt.score(374.1), "374");
  assert.equal(Figs.fmt.secs(null), "–");
});

test("the leaderboard ranks everyone, bots too: the best three on a podium, 2nd 1st 3rd, then the rest in order", () => {
  assert.deepEqual(Figs.standings(SMALL).map(({ p, place }) => [p.player, place]),
    [["solver", 1], ["jev_step2", 2], ["fly2", 3], ["haiku_plain", 4], ["jev_plain", 5], ["random", 6]]);
  const html = Figs.leaderboardHtml(SMALL, "jev_step2");
  const [podium, list] = html.split('<ol class="wf-standings">');
  assert.deepEqual([...podium.matchAll(/data-player="([a-z0-9_]+)"/g)].map((m) => m[1]), ["jev_step2", "solver", "fly2"]);
  assert.match(podium, /wf-place-2 focus" data-player="jev_step2"[\s\S]*?<span class="wf-pos">2nd<\/span>/);
  assert.deepEqual([...list.matchAll(/data-player="([a-z0-9_]+)"/g)].map((m) => m[1]), ["haiku_plain", "jev_plain", "random"]);
  assert.match(list, /<span class="wf-pos">6th<\/span><span class="wf-who"><span class="wf-part">Bot<\/span> · <span class="wf-part">Random<\/span> <span class="wf-tag">bot, for scale<\/span>/);
  assert.doesNotMatch(html, /–/);
  // the icons: under the name on the podium, left of the name in the list
  const real = Figs.leaderboardHtml(STUDY, "jev_step2");
  assert.match(real, /<span class="wf-who">Jev · step-2<\/span><svg class="wf-icon"/);
  assert.match(real, /<span class="wf-pos">4th<\/span><svg class="wf-icon"[^]*?<\/svg><span class="wf-who">/);
  assert.deepEqual([1, 2, 3, 4, 11, 12, 13, 21, 22, 101, 111].map(Figs.ordinal),
    ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "101st", "111th"]);
});

test("each player's icon is its skin as viewer/sprites.js paints it standing still", () => {
  const Sprites = require("../sprites.js");
  for (const p of STUDY.players) {
    const { icon } = p;
    const mine = [];
    icon.rows.forEach((row, y) => [...row].forEach((ink, x) => { if (ink !== ".") mine.push({ x, y, ink: icon.palette[ink] }); }));
    assert.deepEqual(mine, Sprites.pixels(icon.sprite, { color: icon.color, inks: icon.inks }), p.player);
    const svg = Figs.iconSvg(icon);
    assert.match(svg, /^<svg class="wf-icon" viewBox="0 0 \d+ \d+" shape-rendering="crispEdges"/);
  }
  assert.equal(Figs.iconSvg(null), "");
  const evil = Figs.iconSvg({ rows: ["ab"], palette: { a: '"><script>', b: "#FFFFFF" } });
  assert.doesNotMatch(evil, /script/);
  assert.match(evil, /<rect x="1" y="0" width="1" height="1" fill="#FFFFFF"\/>/);
});

test("Fig. 1 shows the reference, the best of each mind and chance", () => {
  assert.deepEqual(Figs.glance(SMALL).map(({ p, note }) => [p.player, note]),
    [["solver", "reference"], ["jev_step2", "best Jev"], ["haiku_plain", "best Claude Haiku"], ["fly2", "best fly"], ["random", "chance"]]);
});

test("blue marks one player: the one in focus, Jev · step-2 at first", () => {
  assert.equal(Figs.focusOf(SMALL, null), "jev_step2");
  assert.equal(Figs.focusOf(SMALL, "fly2"), "fly2");
  assert.equal(Figs.focusOf(SMALL, "nobody"), "jev_step2");
  const board = Figs.boardHtml(SMALL, "fly2");
  assert.equal((board.match(/ focus/g) || []).length, 1);
  assert.match(board, /class="wf-row focus" data-player="fly2" aria-pressed="true"/);
  assert.match(board, /class="wf-row bot" data-player="solver"/);
  assert.equal((Figs.scoresHtml(SMALL, "fly2").match(/class="focus"/g) || []).length, 1);
  assert.doesNotMatch(Figs.scoresHtml(SMALL, "fly2"), /solver|random/); // the bots are there for scale only
});

test("Fig. 3 names who led on the tracks both ran, whichever twin it was", () => {
  const html = Figs.pairHtml(SMALL, "plain");
  assert.match(html, /Claude Haiku · plain ran <span class="num">17\.2<\/span> rows further than Jev · plain/);
  assert.match(html, /8\.7 to 25\.7 rows/);
  assert.match(html, /73%<\/span><span class="label">Claude Haiku · plain win rate/); // 11 of 15
  assert.match(html, /<button type="button" class="wf-chip" data-set="plain" aria-pressed="true">plain<\/button>/);
  assert.equal(Figs.setOf(SMALL, "nope"), "plain");
  assert.match(Figs.pairHtml({ ...SMALL, pairs: [] }, null), /No Jev and Claude Haiku pair/);
  const real = Figs.pairsOf(STUDY).map((q) => q.set);
  assert.deepEqual(real, ["step1", "step2", "guided", "plain"]);
});

test("Fig. 4 lists the players that finished a track, most first", () => {
  const html = Figs.finishedHtml(SMALL, "jev_step2");
  assert.deepEqual([...html.matchAll(/data-player="([a-z0-9_]+)"/g)].map((m) => m[1]), ["solver", "jev_step2", "fly2"]);
  assert.match(html, /74 \/ 100/);
});

test("Fig. 5 draws the frontier, leaves the bots out and names the player in focus", () => {
  const cost = Figs.scatterSvg(SMALL, "usd_per_track", "jev_step2");
  assert.match(cost, /class="wf-frontier"/);
  assert.doesNotMatch(cost, /data-player="(solver|random)"/);
  assert.match(cost, />free<\/text>/);
  assert.match(cost, /<text class="wf-dotname focus"[^>]*>Jev · step-2<\/text>/);
  const time = Figs.scatterSvg(SMALL, "s_per_decision_median", "jev_step2");
  assert.match(time, /seconds per decision \(log\)/);
  assert.match(Figs.scatterSvg(STUDY, "usd_per_track", "jev_step2"), /\$0\.001/);
});

test("text from the numbers is escaped", () => {
  const evil = { players: [P('<img src=x onerror="1">', 50)], pairs: [], notes: [] };
  for (const html of Object.values(Figs.figures(evil, {}))) assert.doesNotMatch(html, /<img/);
});

test("with no numbers every slot says so", () => {
  const out = Figs.figures(null, {});
  assert.deepEqual(Object.keys(out), Figs.KEYS);
  for (const html of Object.values(out)) assert.match(html, /No numbers to draw yet/);
});

// a DOM just big enough for mount: slots with a .fig-body, one click listener
function fakeRoot(keys) {
  const listeners = [];
  const slots = keys.map((key) => {
    const body = { innerHTML: "", className: "fig-body" };
    return { body, getAttribute: (n) => (n === "data-fig" ? key : null), querySelector: () => body };
  });
  return {
    slots, listeners,
    querySelectorAll: () => slots,
    querySelector: () => null,
    contains: () => true,
    addEventListener: (type, fn) => listeners.push(fn),
    removeEventListener: (type, fn) => listeners.splice(listeners.indexOf(fn), 1),
  };
}

test("mount fills every slot it knows, leaves any other alone, and a second mount replaces the first", () => {
  const root = fakeRoot(["someone-elses", "leaderboard", "rows", "rows-ci", "jev-vs-haiku", "finished", "cost-time", "scores"]);
  root.slots[0].body.innerHTML = "the placeholder";
  Figs.mount(root, STUDY);
  assert.equal(root.slots[0].body.innerHTML, "the placeholder");
  for (const slot of root.slots.slice(1)) assert.ok(slot.body.innerHTML.length > 50);
  const first = root.slots[1].body.innerHTML;
  Figs.mount(root, STUDY);
  assert.equal(root.listeners.length, 1);
  assert.equal(root.slots[1].body.innerHTML, first);
});

test("a click on a player follows it in every figure; a chip picks the pair", () => {
  const root = fakeRoot(["rows-ci", "jev-vs-haiku"]);
  const state = Figs.mount(root, STUDY);
  const el = (attrs, match) => ({ getAttribute: (n) => attrs[n] ?? null, closest: (sel) => (match(sel) ? el(attrs, match) : sel === "[data-fig]" ? { getAttribute: () => "rows-ci" } : null),
    ownerDocument: { activeElement: null } });
  const player = el({ "data-player": "fly2" }, (sel) => sel === "[data-player]");
  root.listeners[0]({ target: player });
  assert.equal(state.focus, "fly2");
  assert.match(root.slots[0].body.innerHTML, /class="wf-row focus" data-player="fly2"/);
  const chip = el({ "data-set": "guided" }, (sel) => sel === ".wf-chip[data-set]");
  root.listeners[0]({ target: chip });
  assert.match(root.slots[1].body.innerHTML, /data-set="guided" aria-pressed="true"/);
});

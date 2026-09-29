// The benchmark renderer's rules that do not need a DOM: what it says when there is nothing to draw,
// and that its shell names the parts both pages style. The drawing itself is looked at, not tested.
const test = require("node:test");
const assert = require("node:assert");
const BenchView = require("../bench_view.js");

test("why says what is missing, and nothing when there are numbers", () => {
  assert.equal(BenchView.why(null), "No benchmark was built for this page.");
  assert.equal(BenchView.why({ players: [] }), "No completed run to score: the benchmark needs runs that ended.");
  assert.equal(BenchView.why({ players: [{ player: "solver" }] }), null);
});

test("the shell names every part the stylesheet keys on", () => {
  for (const name of ["players", "survival", "survival-table", "cost", "time", "scores", "pairs", "notes", "thin"]) {
    assert.ok(BenchView.SHELL.includes('data-bench="' + name + '"'), name);
  }
});

test("mount refuses numbers it cannot draw rather than emptying the element", () => {
  const element = { innerHTML: "what was there" };
  assert.equal(BenchView.mount(element, { players: [] }), false);
  assert.equal(element.innerHTML, "what was there");
});

test("the chart note says who the frontier is drawn among and that each point is over its own tracks", () => {
  assert.ok(BenchView.SHELL.includes("drawn among the players with at least five tracks"));
  assert.ok(BenchView.SHELL.includes("each point over its own tracks"));
});

test("an unranked player is drawn apart and named as not ranked; a stopped one says so", () => {
  const ranked = { player: "jev_step2", ranked: true, cost_basis: "estimate", failed_rate: 0, stopped: 0 };
  const thin = { player: "glm_step1", ranked: false, cost_basis: "free", failed_rate: 0.5, stopped: 2 };
  assert.equal(BenchView.dotClass(ranked, "fly"), "dot");
  assert.equal(BenchView.dotClass(thin, "fly"), "dot unranked");
  assert.equal(BenchView.dotClass({ ...thin, player: "fly", yardstick: true }, "fly"), "dot focus yardstick unranked");
  assert.equal(BenchView.scoresName(ranked), "jev_step2");
  assert.equal(BenchView.scoresName(thin), "glm_step1 (not ranked)");
  assert.equal(BenchView.scoresName({ ...thin, yardstick: true, ranked: true, player: "solver" }), "solver (yardstick)");
  assert.equal(BenchView.failedText(ranked), "0%");
  assert.equal(BenchView.failedText(thin), "50% · stopped 2");
});

test("Jev's dot on the cost chart says its cost is an estimate", () => {
  assert.equal(BenchView.dotLabel({ player: "jev_step2", cost_basis: "estimate" }, "cost"), "jev_step2 (est.)");
  assert.equal(BenchView.dotLabel({ player: "jev_step2", cost_basis: "estimate" }, "time"), "jev_step2");
  assert.equal(BenchView.dotLabel({ player: "haiku_plain", cost_basis: "listed" }, "cost"), "haiku_plain");
});

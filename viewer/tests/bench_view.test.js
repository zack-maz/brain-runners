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
  for (const name of ["players", "survival", "survival-table", "cost", "time", "pairs", "notes", "thin"]) {
    assert.ok(BenchView.SHELL.includes('data-bench="' + name + '"'), name);
  }
});

test("mount refuses numbers it cannot draw rather than emptying the element", () => {
  const element = { innerHTML: "what was there" };
  assert.equal(BenchView.mount(element, { players: [] }), false);
  assert.equal(element.innerHTML, "what was there");
});

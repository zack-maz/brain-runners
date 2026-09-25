const test = require("node:test");
const assert = require("node:assert/strict");
const { NAMES, select, stateOf, step } = require("../tabs.js");

test("there are two tabs and the run is the first", () => {
  assert.deepEqual(NAMES, ["run", "analysis"]);
});

test("select takes the tab asked for when it is a real one", () => {
  assert.equal(select("run", "analysis"), "analysis");
  assert.equal(select("analysis", "run"), "run");
});

test("select keeps the tab in focus when the one asked for is not real", () => {
  assert.equal(select("analysis", "nonsense"), "analysis");
  assert.equal(select("analysis", null), "analysis");
});

test("a page that opens on nothing opens on the run", () => {
  assert.equal(select(null, null), "run");
  assert.equal(select("nonsense", "nonsense"), "run");
});

test("stateOf selects exactly one tab and hides the other", () => {
  const state = stateOf("analysis");
  assert.deepEqual(state, [{ name: "run", selected: false, hidden: true },
                           { name: "analysis", selected: true, hidden: false }]);
  assert.equal(stateOf("nonsense").filter((t) => t.selected).length, 1);
});

test("the arrow keys move along the strip and wrap", () => {
  assert.equal(step("run", "ArrowRight"), "analysis");
  assert.equal(step("analysis", "ArrowRight"), "run");
  assert.equal(step("run", "ArrowLeft"), "analysis");
  assert.equal(step("run", "Enter"), null);
});

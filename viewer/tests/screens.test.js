const test = require("node:test");
const assert = require("node:assert/strict");
const Screens = require("../screens.js");

test("the screens, in the order the flow goes through them", () => {
  assert.deepEqual(Screens.NAMES, ["home", "select", "track", "run", "results", "records"]);
});

test("a screen that does not exist leaves the one shown, and a page that opens on nothing opens on home", () => {
  assert.equal(Screens.select("track", "results"), "results");
  assert.equal(Screens.select("track", "lobby"), "track");
  assert.equal(Screens.select(undefined, "nowhere"), "home");
});

test("Back walks the flow backwards, and Records returns to where it was opened from", () => {
  assert.equal(Screens.back("select"), "home");
  assert.equal(Screens.back("track"), "select");
  assert.equal(Screens.back("run"), "home");
  assert.equal(Screens.back("results"), "home");
  assert.equal(Screens.back("records", "home"), "home");
  assert.equal(Screens.back("records", "results"), "results");
  assert.equal(Screens.back("home"), "home");
});

test("exactly one screen is shown", () => {
  const state = Screens.stateOf("track");
  assert.deepEqual(state.filter((s) => !s.hidden).map((s) => s.name), ["track"]);
  assert.equal(state.length, Screens.NAMES.length);
  assert.deepEqual(Screens.stateOf("bogus").filter((s) => !s.hidden).map((s) => s.name), ["home"]);
});

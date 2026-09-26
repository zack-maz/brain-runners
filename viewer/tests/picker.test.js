const test = require("node:test");
const assert = require("node:assert/strict");
const { list, hint, toggle } = require("../picker.js");

const players = ["fly", "jev_step1", "haiku_plain", "solver"];
const here = ["fly", "jev_step1", "haiku_plain"];

test("a shown player's button is pressed, a hidden one's is not", () => {
  const html = list(players, here, new Set(["fly"]), {});
  assert.ok(html.includes('data-player="fly" aria-pressed="true"'));
  assert.ok(html.includes('data-player="jev_step1" aria-pressed="false"'));
});

test("a player that did not run this track is disabled and says so", () => {
  const html = list(players, here, new Set(players), {});
  assert.ok(/data-player="solver" aria-pressed="false" disabled/.test(html));
  assert.ok(html.includes("not on this track"));
});

test("a player name and its description are escaped", () => {
  const html = list(['<b>x</b>'], ['<b>x</b>'], new Set(), { "<b>x</b>": '"><script>' });
  assert.ok(!html.includes("<b>"));
  assert.ok(!html.includes("<script>"));
});

test("hint counts what is shown of what ran the track", () => {
  assert.equal(hint(players, here, new Set(["fly", "haiku_plain"]), 1001), "2 of 3 shown on track 1001.");
  assert.equal(hint(players, here, new Set(), 1001), "Nobody is in the tunnel: pick a player to show it.");
  assert.equal(hint(players, [], new Set(), 1001), "No player ran track 1001.");
  assert.equal(hint([], [], new Set(), null), "Nothing has been played yet.");
});

test("hint escapes a seed that is not a number", () => {
  assert.ok(!hint(players, [], new Set(), "<b>").includes("<b>"));
});

test("toggle turns a player on and off without changing the set it was given", () => {
  const shown = new Set(["fly"]);
  assert.deepEqual([...toggle(shown, here, "haiku_plain")], ["fly", "haiku_plain"]);
  assert.deepEqual([...toggle(shown, here, "fly")], []);
  assert.deepEqual([...shown], ["fly"]);
});

test("toggle can never show a player that did not run this track", () => {
  assert.deepEqual([...toggle(new Set(), here, "solver")], []);
});

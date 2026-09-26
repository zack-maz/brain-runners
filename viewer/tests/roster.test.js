const test = require("node:test");
const assert = require("node:assert/strict");
const Roster = require("../roster.js");

// a slice of bakeoff/roster.py's JSON, enough for every rule here
const DATA = [
  { id: "jev", name: "Jev", sprite: "visor", skins: [
    { player: "jev_plain", name: "Plain", about: "One broad question.", color: "#B9BEC4", inks: {} },
    { player: "jev_step1", name: "Step 1", about: "Four yes/no questions.", color: "#E6B422", inks: {} },
    { player: "jev_step2", name: "Step 2", about: "Eight questions.", color: "#B8404F", inks: {} },
    { player: "jev_map", name: "Map", about: "One question per tile.", color: "#1E2227", inks: { V: "#7AA2F7" } },
  ] },
  { id: "bot", name: "Bot", sprite: "bot", skins: [
    { player: "solver", name: "Solver", about: "A perfect search.", color: "#7AA2F7", inks: {} },
  ] },
];

test("a player is labelled with its character and skin, as on the select screen", () => {
  const roster = Roster.make(DATA);
  assert.equal(roster.label("jev_step1"), "Jev · Step 1");
  assert.equal(roster.label("solver"), "Bot · Solver");
});

test("a player not on the roster keeps its upper-case name and the grey block", () => {
  for (const roster of [Roster.make(DATA), Roster.make(null)]) {
    assert.equal(roster.label("my_bot"), "MY_BOT");
    assert.deepEqual(roster.look("my_bot"), { sprite: "block", color: null, inks: {} });
    assert.equal(roster.ink("my_bot"), null);
    assert.equal(roster.has("my_bot"), false);
  }
});

test("a skin's look is its character's sprite in the skin's colours", () => {
  assert.deepEqual(Roster.make(DATA).look("jev_map"), { sprite: "visor", color: "#1E2227", inks: { V: "#7AA2F7" } });
});

test("a label takes its skin's colour only where that colour reads on the page's ground", () => {
  const roster = Roster.make(DATA);
  assert.equal(roster.ink("jev_step1"), "#E6B422");
  assert.equal(roster.ink("jev_step2"), "#B8404F");
  assert.equal(roster.ink("jev_map"), null); // black on black: the page's own ink, and the swatch shows the black
  assert.equal(roster.colour("jev_map"), "#1E2227");
});

test("contrast is WCAG's ratio", () => {
  assert.equal(Roster.contrast("#FFFFFF", "#000000"), 21);
  assert.equal(Roster.contrast("#777777", "#777777"), 1);
});

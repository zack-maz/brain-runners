const test = require("node:test");
const assert = require("node:assert/strict");
const { OVERLAP_ALPHA, HOLD_ROWS, overlaps, safeActions, autoFocus } = require("../stage.js");

const at = (id, row, lane) => ({ id, row, lane });
const SAFE = { left: 6, stay: 6, right: 6, jump: 6 };
const running = (id, depths) => ({ id, status: "running", frame: { solver_depths: { ...SAFE, ...depths } } });

test("three runners on the start tile are translucent, fanned out and their tags stack", () => {
  const out = overlaps([at("fly", 0, 6), at("jev_composed", 0, 6), at("llm", 0, 6)], 12);
  assert.deepEqual(out.fly, { alpha: OVERLAP_ALPHA, fan: -1, stack: 0 });
  assert.deepEqual(out.jev_composed, { alpha: OVERLAP_ALPHA, fan: 0, stack: 1 });
  assert.deepEqual(out.llm, { alpha: OVERLAP_ALPHA, fan: 1, stack: 2 });
  assert.equal(OVERLAP_ALPHA, 0.55);
});

test("a runner alone on its tile is opaque and where it stands", () => {
  const out = overlaps([at("fly", 4, 5), at("jev_composed", 4, 6), at("llm", 4, 6.4)], 12);
  assert.deepEqual(out.fly, { alpha: 1, fan: 0, stack: 0 });
  assert.deepEqual(out.jev_composed, { alpha: OVERLAP_ALPHA, fan: -0.5, stack: 0 }); // within half a lane of the llm
  assert.deepEqual(out.llm, { alpha: OVERLAP_ALPHA, fan: 0.5, stack: 1 });
});

test("overlap needs the same row, and lanes are compared round the ring", () => {
  const apart = overlaps([at("a", 4, 6), at("b", 5, 6)], 12);
  assert.equal(apart.a.alpha, 1);
  assert.equal(apart.b.alpha, 1);
  const ring = overlaps([at("a", 4, 0.2), at("b", 4, 11.9), at("c", 4, -0.1)], 12); // 11.9 and -0.1 are the same place
  assert.deepEqual([ring.a.alpha, ring.b.alpha, ring.c.alpha], [OVERLAP_ALPHA, OVERLAP_ALPHA, OVERLAP_ALPHA]);
  assert.deepEqual(overlaps([], 12), {});
});

test("safe actions are the ones the solver does not see landing on a gap", () => {
  assert.equal(safeActions({ solver_depths: SAFE }), 4);
  assert.equal(safeActions({ solver_depths: { left: 0, stay: 0, right: 3, jump: 6 } }), 2);
  assert.equal(safeActions({ solver_depths: { left: 0, stay: 0, right: 0, jump: 0 } }), 0);
  assert.equal(safeActions({}), 0);
});

test("auto-focus cuts to the runner in danger, the one with the fewest safe actions", () => {
  const states = [running("fly", { stay: 0 }), running("jev_composed", { stay: 0, left: 0 }), running("llm", {})];
  assert.deepEqual(autoFocus("llm", states, 0, 10), { focus: "jev_composed", heldSince: 10 });
  const tie = [running("fly", { stay: 0 }), running("jev_composed", { jump: 0 }), running("llm", {})];
  assert.deepEqual(autoFocus("jev_composed", tie, 0, 10), { focus: "jev_composed", heldSince: 0 }); // a tie stays
  assert.deepEqual(autoFocus("llm", tie, 0, 10), { focus: "fly", heldSince: 10 }); // else panel order
});

test("auto-focus holds for three rows so it does not flicker", () => {
  const states = [running("fly", { stay: 0 }), running("llm", {})];
  assert.equal(HOLD_ROWS, 3);
  assert.deepEqual(autoFocus("llm", states, 10, 12.9), { focus: "llm", heldSince: 10 });
  assert.deepEqual(autoFocus("llm", states, 10, 13), { focus: "fly", heldSince: 13 });
  assert.deepEqual(autoFocus("llm", states, 10, 4), { focus: "fly", heldSince: 4 }); // scrubbed back: the hold is void
});

test("auto-focus ignores the fallen and stays put when nobody is in danger", () => {
  const dead = { id: "fly", status: "dead", frame: { solver_depths: { left: 0, stay: 0, right: 0, jump: 0 } } };
  assert.deepEqual(autoFocus("llm", [dead, running("llm", {})], 0, 50), { focus: "llm", heldSince: 0 });
  assert.deepEqual(autoFocus(null, [dead, running("llm", {})], 0, 50), { focus: "fly", heldSince: 50 }); // nothing chosen yet
  assert.deepEqual(autoFocus(null, [], 0, 0), { focus: null, heldSince: 0 });
});

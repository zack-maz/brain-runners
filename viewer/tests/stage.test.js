const test = require("node:test");
const assert = require("node:assert/strict");
const { OVERLAP_ALPHA, HOLD_ROWS, overlaps, safeActions, autoFocus } = require("../stage.js");

const at = (id, row, lane) => ({ id, row, lane });
const SAFE = { left: 6, stay: 6, right: 6, jump: 6 };
const running = (id, depths) => ({ id, status: "running", frame: { solver_depths: { ...SAFE, ...depths } } });

test("three runners on the start tile are translucent, fanned out and their tags stack", () => {
  const out = overlaps([at("fly", 0, 6), at("jev_step1", 0, 6), at("haiku_plain", 0, 6)], 12);
  assert.deepEqual(out.fly, { alpha: OVERLAP_ALPHA, fan: -1, stack: 0 });
  assert.deepEqual(out.jev_step1, { alpha: OVERLAP_ALPHA, fan: 0, stack: 1 });
  assert.deepEqual(out.haiku_plain, { alpha: OVERLAP_ALPHA, fan: 1, stack: 2 });
  assert.equal(OVERLAP_ALPHA, 0.55);
});

test("a runner alone on its tile is opaque and where it stands", () => {
  const out = overlaps([at("fly", 4, 5), at("jev_step1", 4, 6), at("haiku_plain", 4, 6.4)], 12);
  assert.deepEqual(out.fly, { alpha: 1, fan: 0, stack: 0 });
  assert.deepEqual(out.jev_step1, { alpha: OVERLAP_ALPHA, fan: -0.5, stack: 0 }); // within half a lane of haiku
  assert.deepEqual(out.haiku_plain, { alpha: OVERLAP_ALPHA, fan: 0.5, stack: 1 });
});

test("overlap needs the same row, and lanes are compared round the ring", () => {
  const apart = overlaps([at("a", 4, 6), at("b", 5, 6)], 12);
  assert.equal(apart.a.alpha, 1);
  assert.equal(apart.b.alpha, 1);
  const ring = overlaps([at("a", 4, 0.2), at("b", 4, 11.9), at("c", 4, -0.1)], 12); // 11.9 and -0.1 are the same place
  assert.deepEqual([ring.a.alpha, ring.b.alpha, ring.c.alpha], [OVERLAP_ALPHA, OVERLAP_ALPHA, OVERLAP_ALPHA]);
  assert.deepEqual(overlaps([], 12), {});
});

test("runners that overlap through a runner between them are one group, whatever order they come in", () => {
  // a and c are 0.8 lanes apart, but both overlap b: all three must be pulled apart together
  for (const order of [["a", "b", "c"], ["a", "c", "b"], ["c", "a", "b"]]) {
    const lane = { a: 6, b: 6.4, c: 6.8 };
    const out = overlaps(order.map((id) => at(id, 4, lane[id])), 12);
    assert.deepEqual(order.map((id) => out[id].alpha), [OVERLAP_ALPHA, OVERLAP_ALPHA, OVERLAP_ALPHA], order.join());
    assert.deepEqual(order.map((id) => out[id].fan), [-1, 0, 1], order.join()); // fanned in the order given
    assert.deepEqual(order.map((id) => out[id].stack), [0, 1, 2], order.join());
  }
});

test("safe actions are the ones the solver does not see landing on a gap", () => {
  assert.equal(safeActions({ solver_depths: SAFE }), 4);
  assert.equal(safeActions({ solver_depths: { left: 0, stay: 0, right: 3, jump: 6 } }), 2);
  assert.equal(safeActions({ solver_depths: { left: 0, stay: 0, right: 0, jump: 0 } }), 0);
  assert.equal(safeActions({}), 0);
});

test("auto-focus cuts to the runner in danger, the one with the fewest safe actions", () => {
  const states = [running("fly", { stay: 0 }), running("jev_step1", { stay: 0, left: 0 }), running("haiku_plain", {})];
  assert.deepEqual(autoFocus("haiku_plain", states, 0, 10), { focus: "jev_step1", heldSince: 10 });
  const tie = [running("fly", { stay: 0 }), running("jev_step1", { jump: 0 }), running("haiku_plain", {})];
  assert.deepEqual(autoFocus("jev_step1", tie, 0, 10), { focus: "jev_step1", heldSince: 0 }); // a tie stays
  assert.deepEqual(autoFocus("haiku_plain", tie, 0, 10), { focus: "fly", heldSince: 10 }); // else panel order
});

test("auto-focus holds for three rows so it does not flicker", () => {
  const states = [running("fly", { stay: 0 }), running("haiku_plain", {})];
  assert.equal(HOLD_ROWS, 3);
  assert.deepEqual(autoFocus("haiku_plain", states, 10, 12.9), { focus: "haiku_plain", heldSince: 10 });
  assert.deepEqual(autoFocus("haiku_plain", states, 10, 13), { focus: "fly", heldSince: 13 });
  assert.deepEqual(autoFocus("haiku_plain", states, 10, 4), { focus: "fly", heldSince: 4 }); // scrubbed back: the hold is void
});

test("auto-focus leaves a runner that is no longer running once its hold is over", () => {
  const dead = { id: "fly", status: "dead", frame: { solver_depths: { left: 0, stay: 0, right: 0, jump: 0 } } };
  const calm = [dead, running("jev_step1", {}), running("haiku_plain", {})];
  assert.deepEqual(autoFocus("fly", calm, 58, 60), { focus: "fly", heldSince: 58 }); // the fall is still being read
  assert.deepEqual(autoFocus("fly", calm, 58, 61), { focus: "jev_step1", heldSince: 61 }); // then on to the living
  const over = [dead, { ...running("haiku_plain", {}), status: "finished" }];
  assert.deepEqual(autoFocus("fly", over, 58, 300), { focus: "fly", heldSince: 58 }); // nobody left to cut to
});

test("auto-focus ignores the fallen and stays put when nobody is in danger", () => {
  const dead = { id: "fly", status: "dead", frame: { solver_depths: { left: 0, stay: 0, right: 0, jump: 0 } } };
  assert.deepEqual(autoFocus("haiku_plain", [dead, running("haiku_plain", {})], 0, 50), { focus: "haiku_plain", heldSince: 0 });
  assert.deepEqual(autoFocus(null, [dead, running("haiku_plain", {})], 0, 50), { focus: "haiku_plain", heldSince: 50 }); // nothing chosen yet: someone running
  assert.deepEqual(autoFocus(null, [dead], 0, 50), { focus: "fly", heldSince: 50 }); // or whoever there is
  assert.deepEqual(autoFocus(null, [], 0, 0), { focus: null, heldSince: 0 });
});

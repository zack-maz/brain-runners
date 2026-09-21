const test = require("node:test");
const assert = require("node:assert/strict");
const { DEPTH, isGap, offset, quads, seenOutline, place } = require("../tunnel.js");

const track = { lanes: 12, max_rows: 300, gaps: [[], [], [5, 6], [0, 11]] };
const SIZE = 400;
const centreX = (quad) => quad.points.reduce((sum, p) => sum + p[0], 0) / 4;
const centreY = (quad) => quad.points.reduce((sum, p) => sum + p[1], 0) / 4;

test("gaps wrap round the ring and rows past the list are floor", () => {
  assert.equal(isGap(track, 2, 5), true);
  assert.equal(isGap(track, 3, -1), true); // lane -1 is lane 11
  assert.equal(isGap(track, 3, 12), true); // lane 12 is lane 0
  assert.equal(isGap(track, 2, 4), false);
  assert.equal(isGap(track, 99, 5), false);
});

test("offsets are wrapped the way the senses wrap them", () => {
  assert.deepEqual([6, 7, 5, 0, 11].map((lane) => offset(lane, 6, 12)), [0, 1, -1, -6, 5]);
  assert.equal(offset(11, 0, 12), -1);
});

test("a gap is a missing tile and every other tile of the drawn rows is there", () => {
  const all = quads(track, 0, SIZE, 300);
  assert.equal(all.length, (DEPTH + 1) * 12 - 4);
  assert.equal(all.some((q) => q.row === 2 && (q.lane === 5 || q.lane === 6)), false);
  assert.equal(all[0].row, DEPTH); // far to near, so near tiles paint over far ones
  assert.equal(all[all.length - 1].row, 0);
});

test("the camera is fixed: the start lane is at the bottom whatever the runners do, lane 0 is the ceiling", () => {
  const all = quads(track, 0, SIZE, 300);
  const tile = (row, lane) => all.find((q) => q.row === row && q.lane === lane);
  assert.ok(Math.abs(centreX(tile(0, 6)) - SIZE / 2) < 1e-6);
  assert.ok(centreY(tile(0, 6)) > SIZE / 2);
  assert.ok(centreX(tile(0, 7)) > centreX(tile(0, 6)));
  assert.ok(centreX(tile(0, 5)) < centreX(tile(0, 6)));
  assert.ok(centreY(tile(0, 0)) < SIZE / 2); // the opposite lane is the ceiling
  assert.ok(centreY(tile(5, 6)) < centreY(tile(0, 6))); // further away is nearer the middle
  assert.equal(quads.length, 4); // (track, row, size, maxRows): no camera lane, no `seen`
});

test("the camera moves along the tube with the clock", () => {
  const all = quads(track, 2.5, SIZE, 300);
  assert.equal(all[all.length - 1].row, 2);
  assert.equal(all[0].row, 2 + DEPTH);
  assert.equal(all.some((q) => q.row < 2), false);
});

test("tiles are floor, or finish from the last row on", () => {
  const all = quads(track, 0, SIZE, 4);
  const kind = (row, lane) => all.find((q) => q.row === row && q.lane === lane).kind;
  assert.equal(kind(1, 6), "floor");
  assert.equal(kind(3, 6), "floor");
  assert.equal(kind(4, 6), "finish");
  assert.equal(kind(9, 0), "finish");
});

test("a gap the engine can never kill on past the finish line is drawn as finish floor, not a hole", () => {
  // maxRows 2: row 2 is at the finish (the engine can still kill there); row 3 is past it (never kills)
  const pastFinish = { lanes: 12, max_rows: 300, gaps: [[], [], [5], [3]] };
  const all = quads(pastFinish, 0, SIZE, 2);
  const tile = (row, lane) => all.find((q) => q.row === row && q.lane === lane);
  assert.equal(tile(3, 3).kind, "finish"); // gaps[3] lists lane 3, but row 3 > max_rows 2: drawn anyway
  assert.equal(tile(2, 5), undefined); // row 2 <= max_rows 2: the engine could still kill there, so it's a real hole
});

test("the focused mind's tiles: six rows ahead of where it stood, three lanes either side", () => {
  const tiles = seenOutline({ row: 10, lane: 1 }, 6, 3);
  assert.equal(tiles.length, 6 * 7);
  const has = (row, lane) => tiles.some((t) => t.row === row && t.lane === lane);
  assert.equal(has(11, 1), true);
  assert.equal(has(16, 4), true);
  assert.equal(has(11, -2), true); // lane -2 is lane 10: left unwrapped, isGap and corners wrap it
  assert.equal(has(10, 1), false); // its own row is not ahead
  assert.equal(has(17, 1), false);
  assert.equal(has(11, 5), false);
});

test("a runner stands on the wall at its lane with its head toward the axis", () => {
  const running = { row: 4, lane: 6, air: 0, status: "running", since: 0 };
  const bottom = place(running, 12, SIZE);
  assert.ok(Math.abs(bottom.x - SIZE / 2) < 1e-6 && bottom.y > SIZE / 2);
  assert.ok(Math.abs(bottom.rotation) < 1e-9); // upright at the bottom
  assert.equal(bottom.lift, 0);
  assert.equal(bottom.fall, 0);
  assert.equal(bottom.visible, true);
  const ceiling = place({ ...running, lane: 0 }, 12, SIZE);
  assert.ok(Math.abs(ceiling.x - SIZE / 2) < 1e-6 && ceiling.y < SIZE / 2);
  assert.ok(Math.abs(Math.abs(ceiling.rotation) - Math.PI) < 1e-9); // a ceiling runner is upside down
  const right = place({ ...running, lane: 9 }, 12, SIZE);
  assert.ok(right.x > SIZE / 2 && Math.abs(right.y - SIZE / 2) < 1e-6);
  // an upright sprite's head is at (0, -1); a canvas rotation by r turns that into (sin r, -cos r),
  // which must point from the runner to the axis on every wall
  for (let lane = 0; lane < 12; lane++) {
    const at = place({ ...running, lane }, 12, SIZE);
    const head = [Math.sin(at.rotation), -Math.cos(at.rotation)];
    const toAxis = [SIZE / 2 - at.x, SIZE / 2 - at.y];
    const length = Math.hypot(...toAxis);
    assert.ok(Math.abs(head[0] - toAxis[0] / length) < 1e-9 && Math.abs(head[1] - toAxis[1] / length) < 1e-9, "lane " + lane);
  }
  // lane -1 is lane 11: the unwrapped lane of a step round the ring lands in the same place
  assert.ok(Math.abs(place({ ...running, lane: -1 }, 12, SIZE).x - place({ ...running, lane: 11 }, 12, SIZE).x) < 1e-6);
});

test("a jump lifts the runner, a death drops it, and a runner the camera has passed is not drawn", () => {
  const jumping = place({ row: 4.5, lane: 6, air: 1, status: "running", since: 0 }, 12, SIZE);
  assert.ok(jumping.lift > 0);
  assert.equal(place({ row: 9, lane: 6, air: 0, status: "dead", since: 0.25 }, 12, SIZE).fall, 0.25);
  assert.equal(place({ row: 9, lane: 6, air: 0, status: "dead", since: 3 }, 12, SIZE).fall, 1);
  const cut = { row: 9, lane: 6, air: 0, status: "cut", since: 2 };
  assert.equal(place(cut, 12, SIZE, 9).visible, true);
  assert.equal(place(cut, 12, SIZE, 11).visible, false);
  const ahead = place({ ...cut, row: 12 }, 12, SIZE, 9); // further along the tube: smaller and nearer the axis
  assert.ok(ahead.scale < place(cut, 12, SIZE, 9).scale);
});

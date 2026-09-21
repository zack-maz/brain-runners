const test = require("node:test");
const assert = require("node:assert/strict");
const { DEPTH, isGap, offset, wasSeen, quads } = require("../tunnel.js");

const track = { lanes: 12, max_rows: 300, gaps: [[], [], [5, 6], [0, 11]] };
const seen = { row: 0, lane: 6, lookahead: 6, window: 3 };
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

test("the player saw six rows ahead and three lanes either side", () => {
  assert.equal(wasSeen(1, 6, seen, 12), true);
  assert.equal(wasSeen(6, 9, seen, 12), true);
  assert.equal(wasSeen(0, 6, seen, 12), false); // its own row is not ahead
  assert.equal(wasSeen(7, 6, seen, 12), false);
  assert.equal(wasSeen(1, 10, seen, 12), false);
  assert.equal(wasSeen(1, 10, { ...seen, lane: 0 }, 12), true); // lane 10 is two to the left of lane 0
});

test("a gap is a missing tile and every other tile of the drawn rows is there", () => {
  const all = quads(track, { row: 0, lane: 6 }, seen, SIZE, 300);
  assert.equal(all.length, (DEPTH + 1) * 12 - 4);
  assert.equal(all.some((q) => q.row === 2 && (q.lane === 5 || q.lane === 6)), false);
  assert.equal(all[0].row, DEPTH); // far to near, so near tiles paint over far ones
  assert.equal(all[all.length - 1].row, 0);
});

test("the runner's lane is at the bottom and the lane to its right is on the right", () => {
  const all = quads(track, { row: 0, lane: 6 }, seen, SIZE, 300);
  const tile = (row, lane) => all.find((q) => q.row === row && q.lane === lane);
  assert.ok(Math.abs(centreX(tile(0, 6)) - SIZE / 2) < 1e-6);
  assert.ok(centreY(tile(0, 6)) > SIZE / 2);
  assert.ok(centreX(tile(0, 7)) > centreX(tile(0, 6)));
  assert.ok(centreX(tile(0, 5)) < centreX(tile(0, 6)));
  assert.ok(centreY(tile(0, 0)) < SIZE / 2); // the opposite lane is the ceiling
  assert.ok(centreY(tile(5, 6)) < centreY(tile(0, 6))); // further away is nearer the middle
});

test("tiles are marked as seen, floor or finish", () => {
  const all = quads(track, { row: 0, lane: 6 }, seen, SIZE, 4);
  const kind = (row, lane) => all.find((q) => q.row === row && q.lane === lane).kind;
  assert.equal(kind(1, 6), "seen");
  assert.equal(kind(1, 11), "floor");
  assert.equal(kind(0, 6), "floor");
  assert.equal(kind(4, 6), "finish");
});

test("a gap the engine can never kill on past the finish line is drawn as finish floor, not a hole", () => {
  // maxRows 2: row 2 is at the finish (the engine can still kill there); row 3 is past it (never kills)
  const pastFinish = { lanes: 12, max_rows: 300, gaps: [[], [], [5], [3]] };
  const cam = { row: 0, lane: 6 };
  const all = quads(pastFinish, cam, seen, SIZE, 2);
  const tile = (row, lane) => all.find((q) => q.row === row && q.lane === lane);
  assert.equal(tile(3, 3).kind, "finish"); // gaps[3] lists lane 3, but row 3 > max_rows 2: drawn anyway
  assert.equal(tile(2, 5), undefined); // row 2 <= max_rows 2: the engine could still kill there, so it's a real hole
});

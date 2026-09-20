const test = require("node:test");
const assert = require("node:assert/strict");
const { frameIndexAt, laneShift, endRow, stateAt } = require("../timeline.js");

const frame = (row, lane, landing, extra) => ({ row, lane, landing, alive: true, finished: false, ...extra });
// stay, jump (rows 1 -> 3), step left round the ring, then a fatal step right
const episode = {
  frames: [
    frame(0, 0, [1, 0]),
    frame(1, 0, [3, 0]),
    frame(3, 0, [4, 11]),
    frame(4, 11, [5, 0], { alive: false }),
  ],
};

test("the frame on screen is the last one decided at or before t", () => {
  assert.deepEqual([0, 0.9, 1, 2.5, 3, 4.2, 99].map((t) => frameIndexAt(episode, t)), [0, 0, 1, 1, 2, 3, 3]);
});

test("a jump takes two ticks, peaks half way and keeps its frame", () => {
  const mid = stateAt(episode, 2, 12);
  assert.equal(mid.index, 1);
  assert.equal(mid.row, 2);
  assert.equal(mid.air, 1);
  assert.equal(stateAt(episode, 1, 12).air, 0);
  assert.equal(stateAt(episode, 0.5, 12).air, 0); // a stay never leaves the floor
});

test("lane steps go the short way round the ring", () => {
  assert.equal(laneShift(episode.frames[2], 12), -1);
  assert.equal(laneShift(episode.frames[3], 12), 1);
  assert.equal(laneShift(episode.frames[0], 12), 0);
  assert.equal(stateAt(episode, 3.5, 12).lane, -0.5); // not wrapped: 0 -> -1, never 0 -> 11
});

test("a fatal move runs until it lands, then the runner is dead", () => {
  assert.equal(stateAt(episode, 4.5, 12).status, "running");
  const dead = stateAt(episode, 6, 12);
  assert.equal(dead.status, "dead");
  assert.equal(dead.row, 5);
  assert.equal(dead.since, 1);
  assert.equal(endRow(episode), 5);
});

test("an episode ends finished or cut, never dead, when its last frame is alive", () => {
  const finished = { frames: [frame(0, 6, [1, 6], { finished: true })] };
  const cut = { frames: [frame(0, 6, [1, 6])] };
  assert.equal(stateAt(finished, 1, 12).status, "finished");
  assert.equal(stateAt(cut, 1, 12).status, "cut");
  assert.equal(stateAt(cut, 0.5, 12).status, "running");
});

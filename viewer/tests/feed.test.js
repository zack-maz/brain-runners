const test = require("node:test");
const assert = require("node:assert/strict");
const { fromEmbedded, fromStream } = require("../feed.js");

function recorder() {
  const calls = [];
  const handler = (name) => (...args) => calls.push([name, ...args]);
  return { calls, handlers: { onMeta: handler("meta"), onEpisode: handler("episode"), onFrame: handler("frame"),
                              onEnd: handler("end"), onError: handler("error") } };
}

class FakeEventSource {
  constructor(url) { this.url = url; this.listeners = {}; this.closed = false; FakeEventSource.last = this; }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  emit(name, payload) { this.listeners[name](payload === undefined ? {} : { data: JSON.stringify(payload) }); }
  close() { this.closed = true; }
}

const TRACK = { seed: 1000, lanes: 12, max_rows: 300, gaps: [[], [5]] };
const frame = (row) => ({ row, lane: 6, landing: [row + 1, 6], alive: true, finished: false });
const episode = (player, frames) => ({ player, seed: 1000, run_id: "r", complete: true, finished: false, death_cause: "ran_into_gap",
                                       rows_survived: 2, max_rows: 300, questions: [], frames });

test("an embedded replay arrives as meta, then each episode and its frames in order", () => {
  const { calls, handlers } = recorder();
  const replay = { game: { version: "v2" }, runs: [{ run_id: "r" }], players: ["fly", "llm"], seeds: [1000], tracks: { 1000: TRACK },
                   scoreboard: { columns: ["player"], rows: [], same_seeds: true },
                   episodes: [episode("fly", [frame(0), frame(1)]), episode("llm", [frame(0)])] };
  fromEmbedded(replay, handlers);
  assert.deepEqual(calls.map((c) => c[0]), ["meta", "episode", "frame", "frame", "episode", "frame"]);
  assert.deepEqual(calls[0][1], { game: { version: "v2" }, runs: replay.runs, players: replay.players, seeds: [1000], scoreboard: replay.scoreboard });
  const [, header, track] = calls[1];
  assert.equal(header.player, "fly");
  assert.equal(header.death_cause, "ran_into_gap");
  assert.equal("frames" in header, false); // the page builds its own list from onFrame
  assert.equal(track, TRACK);
  assert.deepEqual(calls[3], ["frame", "fly", 1000, frame(1), null]);
  assert.equal(replay.episodes[0].frames.length, 2); // the replay object is not changed
});

test("an empty replay, as the live page embeds it, is only meta", () => {
  const { calls, handlers } = recorder();
  fromEmbedded({ runs: [], players: [], seeds: [], tracks: {}, episodes: [] }, handlers);
  assert.deepEqual(calls, [["meta", { game: null, runs: [], players: [], seeds: [], scoreboard: { columns: [], rows: [], same_seeds: true } }]]);
});

test("a live stream delivers the same calls in the replay's own shapes", () => {
  const { calls, handlers } = recorder();
  const source = fromStream("/events", handlers, FakeEventSource);
  assert.equal(source.url, "/events");
  const summary = { complete: false, finished: false, death_cause: null, rows_survived: 1 };
  source.emit("episode", { episode: { ...episode("fly", []), complete: false }, track: TRACK });
  source.emit("frame", { player: "fly", seed: 1000, frame: frame(0), summary });
  assert.deepEqual(calls.map((c) => c[0]), ["episode", "frame"]);
  assert.deepEqual(calls[0][2], TRACK);
  assert.deepEqual(calls[1], ["frame", "fly", 1000, frame(0), summary]);
});

test("history replayed after a reconnect is dropped: no episode twice, no row twice", () => {
  const { calls, handlers } = recorder();
  const source = fromStream("/events", handlers, FakeEventSource);
  const header = { episode: episode("fly", []), track: TRACK };
  source.emit("episode", header);
  source.emit("frame", { player: "fly", seed: 1000, frame: frame(0) });
  source.emit("frame", { player: "fly", seed: 1000, frame: frame(2) }); // a jump: rows are not consecutive
  source.emit("episode", header);
  source.emit("frame", { player: "fly", seed: 1000, frame: frame(0) });
  source.emit("frame", { player: "fly", seed: 1000, frame: frame(2) });
  source.emit("frame", { player: "fly", seed: 1000, frame: frame(3) });
  source.emit("frame", { player: "llm", seed: 1000, frame: frame(0) }); // no episode yet: nothing to add it to
  assert.deepEqual(calls.map((c) => (c[0] === "frame" ? c[3].row : c[0])), ["episode", 0, 2, 3]);
});

test("the end closes the stream, so the browser does not reconnect and start over", () => {
  const { calls, handlers } = recorder();
  const source = fromStream("/events", handlers, FakeEventSource);
  source.emit("end", { status: "completed", runs: [{ run_id: "r" }], scoreboard: { columns: [], rows: [], same_seeds: true } });
  assert.equal(source.closed, true);
  assert.equal(calls[0][0], "end");
  assert.equal(calls[0][1].status, "completed");
});

test("our error event carries a message, a dropped connection does not", () => {
  const { calls, handlers } = recorder();
  const source = fromStream("/events", handlers, FakeEventSource);
  source.emit("error", { message: "request cap of 5 reached" });
  source.emit("error");
  assert.deepEqual(calls, [["error", "request cap of 5 reached"], ["error", null]]);
});

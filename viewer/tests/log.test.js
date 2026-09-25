const test = require("node:test");
const assert = require("node:assert/strict");
const { asked, answered, move, timing, line, lines, short } = require("../log.js");

const composed = { player: "jev_composed", questions: [{ gap_left: {}, gap_stay: {}, gap_right: {}, gap_jump: {} }] };
const frame = (extra) => ({ row: 7, chosen_action: "stay", executed_action: "stay", q: 0, cache_hit: false,
                            latency_ms: 212.4, answers: { gap_stay: { noul: 0.05 } }, ...extra });

test("asked counts a question set's questions and calls a prompt one", () => {
  assert.equal(asked(composed, frame()), "4 questions");
  assert.equal(asked({ questions: [{ system: "rules", user: "row" }] }, frame()), "one prompt");
  assert.equal(asked({ questions: [{ action: {} }] }, frame()), "1 question");
});

test("asked says nothing when the frame points at no questions", () => {
  assert.equal(asked(composed, frame({ q: null })), "");
  assert.equal(asked({ player: "fly" }, frame({ q: null })), "");
});

test("answered quotes the chosen move's gap probability", () => {
  assert.equal(answered(composed, frame()), "5% it lands on a gap");
});

test("answered falls back to the choice when there is no per-move number", () => {
  assert.equal(answered({ player: "jev_choice" }, frame({ answers: { action: { choice: "jump" } } })), "chose jump");
});

test("answered shortens a written reply to one line", () => {
  const text = "line one\nline two that goes on and on and on and on and on and on and on and on";
  const out = answered({ player: "haiku" }, frame({ answers: { text } }));
  assert.ok(out.endsWith("…"));
  assert.ok(!out.includes("\n"));
  assert.ok(out.length <= 64);
});

test("answered gives the fly its rates, signals and spike count, and says the input is ours", () => {
  const fly = { player: "fly" };
  const info = { left_hz: 120.4, right_hz: 80, turn_signal_hz: -14.6, jump_signal_hz: 41.2, total_spikes: 5312 };
  assert.equal(answered(fly, frame({ info, answers: null })),
    "input (ours) 120 Hz / 80 Hz, turn -15 Hz, jump 41 Hz, 5312 spikes");
});

test("a rounded chance never reads as certainty", () => {
  const jev = { player: "jev_composed" };
  assert.equal(answered(jev, frame({ chosen_action: "stay", answers: { gap_stay: { noul: 0.004 } } })),
    "<1% it lands on a gap");
  assert.equal(answered(jev, frame({ chosen_action: "stay", answers: { gap_stay: { noul: 0.998 } } })),
    ">99% it lands on a gap");
  assert.equal(answered(jev, frame({ chosen_action: "stay", answers: { gap_stay: { noul: 0 } } })),
    "0% it lands on a gap");
});

test("a set that asks about being trapped says both halves, because the rule used both", () => {
  const two = { player: "jev_two_step" };
  assert.equal(answered(two, frame({ chosen_action: "left", answers: { gap_left: { noul: 0.3 }, trapped_left: { noul: 0.02 } } })),
    "lands on a gap 30% · trapped after it 2%");
});

test("a move the player never made is not printed twice", () => {
  assert.equal(move(frame({ chosen_action: null, executed_action: "stay" })),
    '<span class="warn">no move, ran stay</span>');
});

test("the fly's line carries the time its simulation took", () => {
  assert.equal(timing(frame({ latency_ms: null, info: { wall_ms: 1043.6 } })), "simulated in 1044 ms");
});

test("answered marks a missing fly signal rather than printing NaN", () => {
  const out = answered({ player: "fly" }, frame({ info: { total_spikes: 3 }, answers: null }));
  assert.ok(out.includes("–"));
  assert.ok(!out.includes("NaN"));
});

test("move names the move the game ran when it differs, and why", () => {
  assert.equal(move(frame()), "stay");
  const held = move(frame({ chosen_action: "jump", executed_action: "stay", gated: true }));
  assert.ok(held.includes("held back") && held.includes("ran stay"));
  assert.ok(move(frame({ chosen_action: "jump", executed_action: "stay", invalid: true })).includes("not a valid move"));
  assert.ok(move(frame({ chosen_action: null, executed_action: "stay", error: "boom" })).includes("error"));
});

test("timing prefers the cache over a latency", () => {
  assert.equal(timing(frame()), "212 ms");
  assert.equal(timing(frame({ cache_hit: true })), "cached");
  assert.equal(timing(frame({ latency_ms: null })), "");
});

test("a line carries the row, the move and the timing", () => {
  const html = line(composed, frame());
  assert.ok(html.includes("0007"));
  assert.ok(html.includes("stay"));
  assert.ok(html.includes("212 ms"));
  assert.ok(html.includes("4 questions"));
});

test("an error is shown in --bad, escaped", () => {
  const html = line(composed, frame({ error: "<script>x</script>" }));
  assert.ok(html.includes('<span class="bad">'));
  assert.ok(!html.includes("<script>"));
  assert.ok(html.includes("&#60;script&#62;"));
});

test("a written answer is escaped, never markup", () => {
  const html = line({ player: "haiku", questions: [] }, frame({ q: null, answers: { text: '<img src=x onerror="a">' } }));
  assert.ok(!html.includes("<img"));
  assert.ok(html.includes("&#60;img"));
});

test("lines keeps the frames' order, oldest first", () => {
  const html = lines(composed, [frame({ row: 1 }), frame({ row: 2 })]);
  assert.ok(html.indexOf("0001") < html.indexOf("0002"));
});

test("short leaves a short line alone", () => {
  assert.equal(short("  a  b "), "a b");
});

test("answered gives fly2 its channels, signals and branch, and says the input and the rule are ours", () => {
  const info = { channels_hz: { centre: 300, left: 0, right: 100 }, turn_signal_hz: -41.6, jump_signal_hz: 230.2,
                 branch: "dodge", total_spikes: 4100 };
  assert.equal(answered({ player: "fly2" }, frame({ info, answers: null })),
    "input (ours) centre 300 Hz / left 0 Hz / right 100 Hz, turn -42 Hz, jump 230 Hz, dodged (our rule), 4100 spikes");
});

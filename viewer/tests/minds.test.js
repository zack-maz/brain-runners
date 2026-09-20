const test = require("node:test");
const assert = require("node:assert/strict");
const Minds = require("../minds.js");

const depths = { stay: 6, left: 6, right: 0, jump: 3 };
const frame = (extra) => ({
  row: 3, lane: 6, landing: [4, 6], ahead: [[0, 1], [], [-3], [], [], []], chosen_action: "stay", executed_action: "stay",
  solver_depths: depths, gated: false, invalid: false, error: null, ground_truth: { gap_ahead: true, left_safe: true },
  answers: null, q: null, info: null, latency_ms: null, usage: null, cache_hit: false, ...extra,
});
const context = (extra) => ({ windowMs: 100, maxHz: null, window: 3, ...extra });
const count = (html, needle) => html.split(needle).length - 1;

test("text from a log is escaped, never markup", () => {
  assert.equal(Minds.esc('<img src=x onerror="alert(1)">&\''), "&#60;img src=x onerror=&#34;alert(1)&#34;&#62;&#38;&#39;");
  const evil = "</pre><script>alert(1)</script>";
  const html = Minds.mind({ player: "llm", questions: [{ system: evil }] },
    frame({ answers: { text: evil, stop_reason: evil }, chosen_action: evil, error: evil, q: 0 }), context());
  assert.equal(html.includes("<script>"), false);
  assert.equal(count(html, "&#60;script&#62;"), 5); // the move, the error, the answer, the stop reason, the question
});

test("the senses grid has a dark cell for every gap the player was shown", () => {
  const html = Minds.sensesGrid(frame(), 3);
  assert.equal(count(html, 'class="gap"'), 3);
  assert.equal(count(html, 'class="tile"'), 6 * 7 - 3);
});

test("the senses grid's column count follows the window it is given", () => {
  const html = Minds.sensesGrid(frame(), 2);
  assert.equal(count(html, "<rect"), 5 * 6);
});

test("the verdict rates the choice against the solver's depths", () => {
  assert.match(Minds.verdict(frame()), /as good as any move \(6 rows seen safe\)/);
  assert.match(Minds.verdict(frame({ chosen_action: "jump", executed_action: "jump" })),
    /solver preferred left or stay \(6 rows safe, this move 3\)/);
  assert.match(Minds.verdict(frame({ solver_depths: { stay: 0, left: 0, right: 0, jump: 0 } })), /no move was known to be safe/);
});

test("a fallback says why the game ran something else", () => {
  assert.match(Minds.verdict(frame({ chosen_action: "teleport", invalid: true })), /not a valid move, so the game ran stay/);
  assert.match(Minds.verdict(frame({ chosen_action: null, error: "APIError: 503" })), /no move.*error, so the game ran stay.*APIError: 503/s);
  // no valid move was chosen: the solver's best is reported, with no invented "this move" depth
  assert.match(Minds.verdict(frame({ chosen_action: "teleport", invalid: true })), /solver's best: left or stay \(6 rows seen safe\)/);
  assert.equal(Minds.verdict(frame({ chosen_action: "teleport", invalid: true })).includes("this move"), false);
  assert.equal(Minds.verdict(frame({ chosen_action: null, error: "APIError: 503" })).includes("this move"), false);
});

test("the fly's panel draws one line per spike and both thresholds", () => {
  const info = {
    left_hz: 250, right_hz: 0, total_spikes: 13207, turn_signal_hz: 30, jump_signal_hz: 210, jump_threshold_hz: 200,
    turn_threshold_hz: 0, spike_times_ms: { DNp01_left: [1, 50, 99], DNa01_right: [20] },
  };
  const html = Minds.mind({ player: "fly", questions: [] }, frame({ info }), context());
  assert.equal(count(html, 'class="spike'), 4);
  assert.match(html, /left eye 250 Hz/);
  assert.match(html, /jumps above 200 Hz, our threshold/);
  assert.match(html, /turns beyond ±0 Hz, our threshold/);
  assert.match(html, /13207 spikes in the whole brain in 100 ms/);
});

test("the turn bar never pegs, even on a signal beyond the usual span", () => {
  const info = {
    left_hz: 0, right_hz: 0, total_spikes: 1, turn_signal_hz: 140, jump_signal_hz: 0, jump_threshold_hz: 200,
    turn_threshold_hz: 0, spike_times_ms: {},
  };
  const html = Minds.flyMind(frame({ info }), context());
  const width = Number(html.match(/turn signal[\s\S]*?class="fill" style="left:[\d.]+%;width:([\d.]+)%/)[1]);
  assert.ok(width <= 50);
});

test("a turn threshold beyond zero draws two more ticks and names itself", () => {
  const info = {
    left_hz: 0, right_hz: 0, total_spikes: 1, turn_signal_hz: 5, jump_signal_hz: 0, jump_threshold_hz: 200,
    turn_threshold_hz: 20, spike_times_ms: {},
  };
  const html = Minds.flyMind(frame({ info }), context());
  const turnBlock = html.slice(html.indexOf("turn signal"));
  assert.equal(count(turnBlock.slice(0, turnBlock.indexOf("</div>")), 'class="tick"'), 3);
  assert.match(html, /turns beyond ±20 Hz, our threshold/);
});

test("an unknown window leaves the milliseconds out of the spikes line", () => {
  const info = {
    left_hz: 0, right_hz: 0, total_spikes: 7, turn_signal_hz: 0, jump_signal_hz: 0, jump_threshold_hz: 200,
    turn_threshold_hz: 0, spike_times_ms: {},
  };
  const html = Minds.flyMind(frame({ info }), context({ windowMs: null }));
  assert.match(html, /7 spikes in the whole brain<\/p>/);
});

test("the fly panel escapes its numbers like every other log value", () => {
  const info = {
    left_hz: 0, right_hz: 0, total_spikes: "<script>x</script>", turn_signal_hz: 0, jump_signal_hz: 0, jump_threshold_hz: 200,
    turn_threshold_hz: 0, spike_times_ms: {},
  };
  const html = Minds.mind({ player: "fly", questions: [] }, frame({ info }), context({ windowMs: "<b>1</b>" }));
  assert.equal(html.includes("<script>"), false);
  assert.equal(html.includes("<b>"), false);
  assert.match(html, /&#60;script&#62;/);
});

test("Jev's panel shows the four probabilities and scores the two questions against the truth", () => {
  const answers = {
    action: { choice: "left", confidence: 0.09, probabilities: { left: 0.33, stay: 0.21, right: 0.21, jump: 0.25 } },
    gap_ahead: { noul: 0.03 }, left_safe: { noul: 0.98 },
  };
  const html = Minds.jevMind(frame({ answers }));
  assert.match(html, /<tr class="picked"><th>left<\/th>.*33%/);
  assert.match(html, /confidence 9%/);
  assert.match(html, /3% yes<\/td><td class="warn">truth: yes/); // it said no gap, there was one
  assert.match(html, /98% yes<\/td><td class="muted">truth: yes/);
  assert.equal(Minds.jevMind(frame()), ""); // after a provider error there are no answers
});

test("Jev's panel leaves the truth cell empty when the record has no ground truth for it", () => {
  const answers = { action: { choice: "left", confidence: 0.5, probabilities: { left: 0.5, stay: 0.5, right: 0, jump: 0 } },
                     gap_ahead: { noul: 0.5 } };
  const html = Minds.jevMind(frame({ answers, ground_truth: {} }));
  assert.equal(html.includes("truth:"), false);
  assert.match(html, /<td class="muted"><\/td>/);
});

test("the cost line tells a live answer from a cached one", () => {
  assert.match(Minds.cost(frame({ latency_ms: 717.9, usage: { input_tokens: 540, output_tokens: 9 } })), /answered in 718 ms, 540 tokens in, 9 out/);
  assert.match(Minds.cost(frame({ cache_hit: true, usage: { input_tokens: 540, output_tokens: 9 } })), /replayed from the cache/);
  assert.equal(Minds.cost(frame()), "");
});

const flyRun = (extra) => ({
  game: { looming: { gain_hz: 25, falloff: 1, max_hz: 250, step_hz: 25 } },
  fly: { turn_threshold_hz: 0, jump_threshold_hz: 200, window_ms: 100, provisional: false },
  ...extra,
});

test("Minds.ours names the calibrated four and says the rest were not tuned", () => {
  const html = Minds.ours(flyRun());
  assert.match(html, /gain.{0,40}falloff.{0,40}two thresholds/s);
  assert.match(html, /chosen once.*frozen \(calibration\/REPORT\.md\)/s);
  assert.match(html, /cap, the step and the window length are fixed design choices of ours and were not tuned/);
});

test("Minds.ours shows the provisional warning instead of the calibration sentence", () => {
  const html = Minds.ours(flyRun({ fly: { turn_threshold_hz: 0, jump_threshold_hz: 200, window_ms: 100, provisional: true } }));
  assert.match(html, /provisional when this run was made/);
  assert.equal(html.includes("frozen"), false);
});

test("Minds.ours admits when a run recorded no fly constants", () => {
  assert.equal(Minds.ours(undefined), "<li>The runs in this replay did not record the fly's constants.</li>");
  assert.equal(Minds.ours({}), "<li>The runs in this replay did not record the fly's constants.</li>");
  assert.equal(Minds.ours(flyRun({ game: { looming: { falloff: null } } })),
    "<li>The runs in this replay did not record the fly's constants.</li>");
});

test("Minds.ours escapes every number, even a mischievous one", () => {
  const html = Minds.ours(flyRun({ game: { looming: { gain_hz: "<b>", falloff: 1, max_hz: 250, step_hz: 25 } } }));
  assert.equal(html.includes("<b>"), false);
  assert.match(html, /&#60;b&#62;/);
});

test("the status line says how an episode ended", () => {
  const episode = { rows_survived: 23, death_cause: "dodged_into_gap" };
  assert.match(Minds.statusLine(episode, { status: "dead" }, 12), /Fell after 23 rows: stepped sideways into a gap/);
  assert.match(Minds.statusLine(episode, { status: "cut" }, 12), /Run stopped after 23 rows \(not a death\)/);
  assert.match(Minds.statusLine(episode, { status: "finished" }, 12), /Reached the finish line/);
  assert.equal(Minds.statusLine(episode, { status: "running", row: 4.5, lane: -0.6 }, 12), "row 4, lane 11");
});

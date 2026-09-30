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
  const html = Minds.mind({ player: "haiku_plain", questions: [{ system: evil }] },
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

test("the senses grid has as many rows as the player was shown, and says so", () => {
  const html = Minds.sensesGrid({ ...frame(), ahead: [[0], [], []] }, 3);
  assert.equal(count(html, "<rect"), 3 * 7);
  assert.match(html, /aria-label="the 3 rows it was shown"/);
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
  assert.match(html, /chosen once.*frozen \(docs\/calibration\/REPORT\.md\)/s);
  assert.match(html, /cap, the step and the window length are fixed design choices of ours and were not tuned/);
});

test("Minds.ours says the fly was calibrated on v1 and not retuned for any other game", () => {
  const looming = { gain_hz: 25, falloff: 1, max_hz: 250, step_hz: 25 };
  const game = (version) => flyRun({ game: { version, looming } });
  assert.match(Minds.ours(flyRun()), /practice tracks 1000 to 1199 of game v1, which are not the held-out tracks,/);
  assert.doesNotMatch(Minds.ours(flyRun()), /tournament/); // decision 53: a study, not a tournament
  assert.doesNotMatch(Minds.ours(flyRun()), /not retuned/); // a run from before versions was v1
  assert.doesNotMatch(Minds.ours(game("v1")), /not retuned/);
  assert.match(Minds.ours(game("v2")), /This run is game v2; the fly was not retuned for it\./);
  assert.match(Minds.ours(game("v1+look8")), /This run is game v1\+look8; the fly was not retuned for it\./);
  assert.match(Minds.ours(game("<b>")), /This run is game &#60;b&#62;;/); // escaped like every log value
});

test("jev_step1 shows its four answers with the chosen action marked, and says what is ours", () => {
  const answers = { gap_left: { noul: 0.97 }, gap_stay: { noul: 0.02 }, gap_right: { noul: 0.5 }, gap_jump: { noul: 0.01 } };
  const info = { model: "jev-latest", rule: "lowest_gap_probability", order: ["stay", "left", "right", "<b>jump</b>"] };
  const html = Minds.mind({ player: "jev_step1", questions: [] }, frame({ answers, info, chosen_action: "jump", executed_action: "jump" }), context());
  assert.match(html, /Lands on a gap\?/);
  assert.match(html, /<tr class="picked"><th>jump<\/th>/);
  assert.equal(count(html, 'class="picked"'), 1);
  assert.match(html, /<th>left<\/th><td>.*?<\/td><td>97%<\/td>/);
  assert.match(html, /ties in the order stay, left, right, &#60;b&#62;jump&#60;\/b&#62;/); // from the log, so escaped
  assert.match(html, /The wording and that rule are ours\. It looks one step ahead only\./);
  assert.equal(Minds.jevStep1Mind(frame()), ""); // after a provider error there are no answers
  const partial = Minds.jevStep1Mind(frame({ answers: { gap_left: { noul: 0.4 } }, chosen_action: null }));
  assert.equal(count(partial, "–"), 3); // an answer that did not arrive is a dash, never 0%
  assert.equal(count(partial, 'class="picked"'), 0);
});

test("the visor shows how sure Jev was that the move it chose is safe", () => {
  const answers = { gap_left: { noul: 0.97 }, gap_stay: { noul: 0.02 }, gap_right: { noul: 0.5 }, gap_jump: { noul: 0.25 } };
  assert.equal(Minds.visorP(frame({ answers, chosen_action: "jump" })), 0.75);
  assert.equal(Minds.visorP(frame({ answers, chosen_action: "stay" })), 0.98);
  assert.equal(Minds.visorP(frame({ answers, chosen_action: null })), null); // an invalid answer: the slit is dark
  assert.equal(Minds.visorP(frame({ answers: null })), null);
  assert.equal(Minds.visorP(frame({ answers: { gap_stay: { noul: "0.1" } } })), null);
});

test("tags are short and uppercase, and an unknown player still gets one", () => {
  assert.deepEqual(["fly", "jev_step1", "haiku_plain", "jev_plain", "glm_plain"].map(Minds.tagOf),
    ["FLY", "JEV STEP 1", "HAIKU PLAIN", "JEV PLAIN", "GLM PLAIN"]);
  assert.equal(Minds.tagOf("my_bot"), "MY_BOT");
});

test("with the roster, a tag is the select screen's label after a swatch of the skin's colour", () => {
  const Roster = require("../roster.js");
  Minds.useRoster(Roster.make([{ id: "jev", name: "Jev", sprite: "visor", skins: [
    { player: "jev_step1", name: "Step 1", about: "", color: "#E6B422", inks: {} },
    { player: "jev_map", name: "Map", about: "", color: "#1E2227", inks: { V: "#7AA2F7" } },
    { player: "jev_x", name: "<b>", about: "", color: "#E6B422\"><script>", inks: {} }] }]));
  try {
    assert.equal(Minds.tagOf("jev_step1"), "Jev \u00b7 Step 1");
    assert.equal(Minds.tagHtml("jev_step1"), '<span class="label tag" style="color:#E6B422"><span class="swatch" ' +
      'style="background:#E6B422" aria-hidden="true"></span>Jev \u00b7 Step 1</span>');
    // black does not read on the dark page: the label keeps the page's ink, the swatch still shows the skin
    assert.equal(Minds.tagHtml("jev_map"), '<span class="label tag"><span class="swatch" style="background:#1E2227" ' +
      'aria-hidden="true"></span>Jev \u00b7 Map</span>');
    assert.equal(Minds.tagHtml("solver"), '<span class="label tag">SOLVER</span>'); // not on this roster
    assert.equal(Minds.tagHtml("jev_x").includes("<script>") || Minds.tagHtml("jev_x").includes("<b>"), false);
  } finally {
    Minds.useRoster(null);
  }
  assert.equal(Minds.tagOf("jev_step1"), "JEV STEP 1");
});

test("the two plain chat models get the same panel", () => {
  const answered = frame({ answers: { text: '{"action": "jump"}', stop_reason: "end_turn" }, chosen_action: "jump" });
  const haiku = Minds.mind({ player: "haiku_plain", questions: [] }, answered, context());
  const glm = Minds.mind({ player: "glm_plain", questions: [] }, answered, context());
  assert.match(glm, /<pre class="answer">/);
  assert.equal(glm, haiku);
});

test("a death and an error are marked bad, a stopped run is only a warning", () => {
  const episode = { rows_survived: 23, death_cause: "ran_into_gap" };
  assert.match(Minds.statusLine(episode, { status: "dead" }, 12), /^<span class="bad">/);
  assert.match(Minds.statusLine(episode, { status: "cut" }, 12), /^<span class="warn">/);
  assert.match(Minds.verdict(frame({ error: "boom", chosen_action: null })), /<p class="bad">boom<\/p>/);
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
  const hostile = { ...episode, rows_survived: "<script>" };
  for (const status of ["dead", "cut", "finished"]) assert.doesNotMatch(Minds.statusLine(hostile, { status }, 12), /<script>/);
});

test("question-set players get the set panel; jev_step1 and the plain players keep theirs", () => {
  assert.deepEqual(["jev_guided", "jev_step2", "jev_map", "haiku_step1", "haiku_guided", "haiku_step2", "haiku_map"]
    .map(Minds.isSetPlayer), [true, true, true, true, true, true, true]);
  assert.deepEqual(["jev_step1", "jev_plain", "haiku_plain", "fly", "jev_other"].map(Minds.isSetPlayer), [false, false, false, false, false]);
  assert.equal(Minds.tagOf("jev_step2"), "JEV STEP 2");
  assert.equal(Minds.tagOf("haiku_map"), "HAIKU MAP");
});

test("the step2 panel shows both answers per move, marks the move made and names the rule as ours", () => {
  const answers = {};
  for (const a of ["left", "stay", "right", "jump"]) { answers["gap_" + a] = { noul: 0.1 }; answers["trapped_" + a] = { noul: 0.2 }; }
  const html = Minds.setMind(frame({ answers, chosen_action: "left", info: { rule: "lowest_two_step_risk" } }));
  assert.match(html, /lands on a gap<\/th><th>dead end after/);
  assert.match(html, /<tr class="picked"><th>left<\/th>/);
  assert.equal(count(html, "10%"), 4);
  assert.match(html, /by lowest_two_step_risk\. The questions and that rule are ours\./);
});

test("the reader panel draws what it read, darker for surer gaps, and escapes a choice and a stop reason", () => {
  const answers = { tile_r1_c: { noul: 0.9 }, tile_r1_l1: { noul: 0 }, tile_r1_r1: { noul: 0.25 }, tile_r2_c: { noul: 1 },
                    tile_r2_l1: { noul: 0 }, tile_r2_r1: { noul: 0 } };
  const html = Minds.setMind(frame({ answers, info: null }));
  assert.match(html, /aria-label="the 6 tiles it read"/);
  assert.match(html, /fill-opacity="0\.90"/);
  assert.match(html, /by its rule\./);
  const odd = Minds.setMind(frame({ answers: { action: { choice: "<b>" }, stop_reason: "<i>" } }));
  assert.match(odd, /Chose &#60;b&#62;/);
  assert.match(odd, /stopped: &#60;i&#62;/);
  assert.equal(Minds.readGrid({ gap_left: { noul: 0.1 } }), "");
});

const fly2Info = (extra) => ({
  channels_hz: { centre: 300, left: 0, right: 100 }, turn_types: ["DNa02", "DNa01", "DNg13"],
  turn_signal_hz: -42, jump_signal_hz: 230, turn_threshold_hz: 20, jump_threshold_hz: 200, branch: "dodge",
  total_spikes: 4100, spike_times_ms: { DNa02_left: [12.5], DNp01_right: [40] }, ...extra,
});
const fly2Meta = (extra) => ({
  mapping: "M1", summary: "a straight-ahead channel", max_hz: 500, step_hz: 100, gain_hz: 250, falloff: 3,
  cells: { centre: ["LPLC2 left", "LPLC2 right"], left: ["LC4 left"], right: ["LC4 right"] },
  sees: { centre: [0], left: [-3, -2, -1], right: [1, 2, 3] }, turn_types: ["DNa02", "DNa01", "DNg13"],
  turn_threshold_hz: 20, jump_threshold_hz: 200, window_ms: 100, provisional: false,
  controls: { seeds: "1200-1399", practice_seeds: "1000-1199", candidates: 3, fly2: 98.5, no_brain: 71.25, shuffled: 40, fly: 66 },
  ...extra,
});

test("fly2's panel shows every channel, its own read-out, both thresholds and which branch of our rule fired", () => {
  const html = Minds.fly2Mind(frame({ info: fly2Info() }), context({ fly2: fly2Meta() }));
  assert.match(html, /centre 300 Hz/);
  assert.match(html, /right 100 Hz/);
  assert.match(html, /centre: LPLC2 left, LPLC2 right; left: LC4 left/);
  assert.match(html, /Which gaps drive which cells, and how hard, is ours/);
  assert.match(html, /right minus left of DNa02 \+ DNa01 \+ DNg13, our read-out; dodges beyond ±20 Hz, our threshold/);
  assert.match(html, /jumps above 200 Hz, our threshold, when it does not dodge/);
  assert.match(html, /Our rule, dodge before jump: dodged: the turn was beyond its threshold/);
  assert.match(html, /DNa02 L/);  // the raster draws the read-out neurons that decide
  assert.match(html, /DNb05 L/);  // and the logged ones
  assert.equal(Minds.fly2Mind(frame({ info: null }), context()), "");
});

test("fly2's panel works without the run's fly2 block, and a read-out without DNa02 draws it as logged only", () => {
  const html = Minds.fly2Mind(frame({ info: fly2Info({ turn_types: ["DNa01", "DNg13"], branch: "stay" }) }), context());
  assert.match(html, /right minus left of DNa01 \+ DNg13,/);
  assert.match(html, /stayed: neither signal crossed its threshold/);
  assert.match(html, /DNa02 L/);
  assert.doesNotMatch(html, /Input to/);
});

test("the mind dispatches fly2 to its own panel and escapes what it logs", () => {
  const html = Minds.mind({ player: "fly2" }, frame({ info: fly2Info({ channels_hz: { "<b>": 1 }, branch: "<i>" }) }), context());
  assert.match(html, /&#60;b&#62; 1 Hz/);
  assert.equal(html.includes("<b>"), false);
  assert.equal(Minds.tagOf("fly2"), "FLY2");
  // the raster's neuron names come from the log (turn_types) and must be escaped too
  const raster = Minds.mind({ player: "fly2" }, frame({ info: fly2Info({ turn_types: ["<b>"] }) }), context());
  assert.equal(raster.includes("<b>"), false);
  assert.match(raster, /&#60;b&#62; L/);
});

test("Minds.oursFly2 lists the mapping, the read-out, the rule, the numbers and the controls", () => {
  const html = Minds.oursFly2({ fly2: fly2Meta() });
  assert.match(html, /Input mapping M1, a straight-ahead channel/);
  assert.match(html, /250 \/ row<sup>3<\/sup> Hz, capped at 500 Hz and rounded to 100 Hz steps/);
  assert.match(html, /centre \(lanes 0\) drives LPLC2 left, LPLC2 right/);
  assert.match(html, /right minus left of DNa02 \+ DNa01 \+ DNg13/);
  assert.match(html, /a turn beyond 20 Hz goes left or right; otherwise a Giant Fiber above 200 Hz jumps/);
  // the count and the seed range come from f.controls, not a literal
  assert.match(html, /The mapping \(one of 3\), the gain, the falloff and the two thresholds were chosen once/);
  assert.match(html, /on practice tracks 1000-1199 of game v2, then frozen/);
  assert.match(html, /fly2 98.50, the same rule with no brain 71.25, on shuffled wiring 40, fly on its own stand-in 66/);
  assert.match(html, /all played on the stand-in brain \(the measured response surfaces\)/);
  assert.match(Minds.oursFly2({ fly2: fly2Meta({ provisional: true }) }), /provisional when this run was made/);
  assert.doesNotMatch(Minds.oursFly2({ fly2: fly2Meta({ provisional: true }) }), /Controls/);
  assert.match(Minds.oursFly2({ fly2: fly2Meta({ controls: { ...fly2Meta().controls, shuffled: null } }) }),
    /on shuffled wiring not measured/);
  // no controls recorded at all: no count, no seed range, and no Controls line
  const noControls = Minds.oursFly2({ fly2: fly2Meta({ controls: undefined }) });
  assert.match(noControls, /The mapping, the gain, the falloff and the two thresholds were chosen once, by a rule fixed before any measurement, then frozen/);
  assert.doesNotMatch(noControls, /one of/);
  assert.doesNotMatch(noControls, /practice tracks/);
  assert.doesNotMatch(noControls, /Controls/);
  assert.equal(Minds.oursFly2(undefined), "");
  assert.equal(Minds.oursFly2({ fly2: null }), "");
});

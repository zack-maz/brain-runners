// What each player had in mind for one decision, as HTML strings (pure, tested under node).
// Everything that comes from a log goes through esc(): an LLM's answer is text, never markup.
(function (root) {
  "use strict";

  const ACTIONS = ["left", "stay", "right", "jump"];
  const FLY_GROUPS = [
    ["DNa01", "steering"], ["DNb01", "steering"], ["DNp01", "Giant Fiber, escape jump"], ["DNa02", "logged only"],
  ];
  // the short uppercase tag a runner carries when the page has no roster (a page built before Brain Battle)
  const TAGS = { fly: "FLY", fly2: "FLY2", solver: "SOLVER", random: "RANDOM", always_jump: "JUMPER",
    jev_plain: "JEV PLAIN", jev_guided: "JEV GUIDED", jev_step1: "JEV STEP 1", jev_step2: "JEV STEP 2", jev_map: "JEV MAP",
    haiku_plain: "HAIKU PLAIN", haiku_guided: "HAIKU GUIDED", haiku_step1: "HAIKU STEP 1", haiku_step2: "HAIKU STEP 2",
    haiku_map: "HAIKU MAP",
    glm_plain: "GLM PLAIN", glm_guided: "GLM GUIDED", glm_step1: "GLM STEP 1", glm_step2: "GLM STEP 2", glm_map: "GLM MAP" };
  // players that ask a question set (bakeoff/players/question_sets.py): Jev, Claude Haiku or GLM, and the set's name
  const SET_PLAYER = /^(jev|haiku|glm)_(step1|guided|step2|map)$/;
  const isSetPlayer = (player) => SET_PLAYER.test(player) && player !== "jev_step1";
  // With the roster (roster.js, set once by app.js) a runner is labelled as on the select screen, "Jev · Step 1".
  let roster = null;
  const useRoster = (made) => { roster = made || null; };
  const tagOf = (player) => (roster && roster.has(player) ? roster.label(player) : TAGS[player] || String(player).toUpperCase());
  // The tag as markup: the label, in its skin's colour where that reads on the dark page, after a swatch of the
  // skin's colour. A player not on the roster gets the plain tag. Every value is escaped.
  const tagHtml = (player) => {
    const colour = roster && roster.has(player) ? roster.colour(player) : null;
    const ink = colour ? roster.ink(player) : null;
    return '<span class="label tag"' + (ink ? ' style="color:' + esc(ink) + '"' : "") + ">" +
      (colour ? '<span class="swatch" style="background:' + esc(colour) + '" aria-hidden="true"></span>' : "") +
      esc(tagOf(player)) + "</span>";
  };
  const DEATHS = {
    ran_into_gap: "ran straight into a gap",
    jumped_into_gap: "jumped into a gap",
    dodged_into_gap: "stepped sideways into a gap",
  };

  const esc = (value) => String(value).replace(/[&<>"']/g, (c) => "&#" + c.charCodeAt(0) + ";");
  const percent = (p) => Math.round(p * 100) + "%";
  const hz = (value) => Math.round(value) + " Hz";

  // a value from a run's meta or log for display: null is "-", an integer or a string is escaped,
  // any other number is 2 decimals, or 4 when it is small enough that 2 would round it to 0
  function cell(value) {
    if (value == null) return "–";
    if (typeof value !== "number" || Number.isInteger(value)) return esc(value);
    return Math.abs(value) > 0 && Math.abs(value) < 0.1 ? value.toFixed(4) : value.toFixed(2);
  }

  // a horizontal bar, share 0..1, with an optional tick at `mark` (0..1)
  function bar(share, mark) {
    const width = Math.max(0, Math.min(1, share)) * 100;
    const tick = mark == null ? "" : '<i class="tick" style="left:' + Math.max(0, Math.min(1, mark)) * 100 + '%"></i>';
    return '<span class="bar"><i class="fill" style="width:' + width.toFixed(1) + '%"></i>' + tick + "</span>";
  }

  // The senses as the player got them: the game's rows ahead (far at the top), `window` lanes either side, gaps dark.
  function sensesGrid(frame, window) {
    let cells = "";
    for (let r = frame.ahead.length - 1; r >= 0; r--) {
      for (let off = -window; off <= window; off++) {
        const gap = frame.ahead[r].includes(off);
        cells += '<rect x="' + (off + window) * 12 + '" y="' + (frame.ahead.length - 1 - r) * 8 +
          '" width="11" height="7" class="' + (gap ? "gap" : "tile") + '"/>';
      }
    }
    const height = frame.ahead.length * 8, width = (2 * window + 1) * 12;
    return '<svg class="senses" viewBox="0 0 ' + width + " " + (height + 8) + '" role="img" aria-label="the ' + frame.ahead.length +
      ' rows it was shown">' +
      cells + '<circle cx="' + (width / 2 - 0.5) + '" cy="' + (height + 4) + '" r="3" class="me"/></svg>';
  }

  // chosen, executed and the reference solver's verdict on the same senses
  function verdict(frame) {
    const best = Math.max(...Object.values(frame.solver_depths));
    const safe = ACTIONS.filter((a) => frame.solver_depths[a] === best);
    const chosen = frame.chosen_action == null ? "no move" : esc(frame.chosen_action);
    let line = "<strong>" + chosen + "</strong>";
    if (frame.chosen_action !== frame.executed_action) {
      const why = frame.error != null ? "error" : frame.invalid ? "not a valid move" : frame.gated ? "held back" : "no move";
      line += ' <span class="warn">' + why + ", so the game ran " + esc(frame.executed_action) + "</span>";
    }
    const known = ACTIONS.includes(frame.chosen_action);
    const depth = known ? frame.solver_depths[frame.chosen_action] : undefined;
    const rating = best === 0 ? "no move was known to be safe"
      : !known ? "solver's best: " + safe.join(" or ") + " (" + esc(best) + " rows seen safe)"
      : depth === best ? "as good as any move (" + esc(best) + " rows seen safe)"
      : "solver preferred " + safe.join(" or ") + " (" + esc(best) + " rows safe, this move " + esc(depth) + ")";
    return '<p class="verdict">' + line + '<br><span class="muted">' + rating + "</span></p>" +
      (frame.error != null ? '<p class="bad">' + esc(frame.error) + "</p>" : "");
  }

  // windowMs null: the window is unknown, so the x axis is scaled by the frame's own latest spike instead
  // groups: [name, what it is] of the read-out neurons to draw, fly's by default
  function spikeRaster(info, windowMs, groups = FLY_GROUPS) {
    const rowHeight = 9, width = 200;
    const times = (group, side) => (info.spike_times_ms || {})[group + "_" + side] || [];
    const latest = Math.max(1, ...groups.flatMap(([group]) => ["left", "right"].flatMap((side) => times(group, side))));
    const span = windowMs == null ? latest : windowMs;
    let rows = "";
    groups.forEach(([group], g) => {
      ["left", "right"].forEach((side, s) => {
        const y = (g * 2 + s) * rowHeight + g * 4;
        rows += '<text x="0" y="' + (y + 7) + '">' + esc(group) + " " + side[0].toUpperCase() + "</text>";
        rows += times(group, side).map((t) => '<line class="spike ' + side + '" x1="' + (52 + (t / span) * width).toFixed(1) +
          '" x2="' + (52 + (t / span) * width).toFixed(1) + '" y1="' + y + '" y2="' + (y + rowHeight - 2) + '"/>').join("");
      });
    });
    const height = groups.length * (2 * rowHeight + 4);
    const label = "spikes of the read-out neurons" + (windowMs == null ? "" : " over the " + esc(windowMs) + " ms window");
    return '<svg class="raster" viewBox="0 0 256 ' + height + '" role="img" aria-label="' + label + '">' + rows + "</svg>";
  }

  // context = {windowMs, maxHz, window}: windowMs is the fly's simulated window, maxHz the looming cap the
  // eye and jump bars scale against (both from the run's meta, and both may be null when the run predates them)
  function flyMind(frame, context) {
    const info = frame.info;
    if (!info) return "";
    const windowMs = context.windowMs, maxHz = context.maxHz;
    const eyeScale = maxHz || Math.max(info.left_hz, info.right_hz, 1);
    const turn = info.turn_signal_hz, threshold = info.turn_threshold_hz;
    const jumpScale = Math.max(maxHz || 0, info.jump_signal_hz, info.jump_threshold_hz, 1);
    return '<div class="eyes"><span>left eye ' + hz(info.left_hz) + bar(info.left_hz / eyeScale) + "</span>" +
      "<span>right eye " + hz(info.right_hz) + bar(info.right_hz / eyeScale) + "</span></div>" +
      '<p class="muted">Looming input to the LPLC2 and LC4 cells of each eye. The weighting of gaps is ours.</p>' +
      spikeRaster(info, windowMs) +
      '<p class="muted">' + esc(info.total_spikes) + " spikes in the whole brain" +
      (windowMs == null ? "" : " in " + esc(windowMs) + " ms") + "</p>" +
      '<div class="signal">turn signal ' + hz(turn) + ' <span class="muted">(right minus left steering; turns beyond ±' +
      Math.round(threshold) + " Hz, our threshold)</span>" + turnBar(turn, threshold) + "</div>" +
      '<div class="signal">jump signal ' + hz(info.jump_signal_hz) + ' <span class="muted">(Giant Fiber; jumps above ' +
      hz(info.jump_threshold_hz) + ", our threshold)</span>" +
      bar(info.jump_signal_hz / jumpScale, info.jump_threshold_hz / jumpScale) + "</div>";
  }

  // a bar centred on zero, filled towards the turn, with ticks at zero and at ±threshold
  function turnBar(turn, threshold) {
    const limit = Math.ceil(Math.max(100, Math.abs(turn), Math.abs(threshold)) / 50) * 50; // the turn bar's span
    const turnShare = 0.5 + Math.max(-limit, Math.min(limit, turn)) / (2 * limit);
    const thresholdShare = threshold / (2 * limit);
    let turnTicks = '<i class="tick" style="left:50%"></i>';
    if (threshold > 0) {
      turnTicks += '<i class="tick" style="left:' + ((0.5 + thresholdShare) * 100).toFixed(1) + '%"></i>' +
        '<i class="tick" style="left:' + ((0.5 - thresholdShare) * 100).toFixed(1) + '%"></i>';
    }
    return '<span class="bar centred"><i class="fill" style="left:' + (Math.min(turnShare, 0.5) * 100).toFixed(1) + "%;width:" +
      (Math.abs(turnShare - 0.5) * 100).toFixed(1) + '%"></i>' + turnTicks + "</span>";
  }

  const STEERING = ["DNa02", "DNa01", "DNg13"];
  const BRANCHES = {
    dodge: "dodged: the turn was beyond its threshold",
    jump: "jumped: no dodge, and the Giant Fiber was above its threshold",
    stay: "stayed: neither signal crossed its threshold",
  };

  // fly2's panel. context.fly2 is the run's fly2 block (its mapping and constants, from meta.json), or null
  // for a run that did not record it; the input bars then scale against the frame's own largest channel.
  function fly2Mind(frame, context) {
    const info = frame.info;
    if (!info) return "";
    const meta = context.fly2 || {};
    const channels = info.channels_hz || {};
    const scale = meta.max_hz || Math.max(1, ...Object.values(channels));
    const cells = meta.cells || {};
    const types = info.turn_types || [];
    const groups = types.map((t) => [t, "steering"]).concat([["DNp01", "Giant Fiber, escape jump"]],
      STEERING.filter((t) => !types.includes(t)).concat(["DNb05", "DNa04"]).map((t) => [t, "logged only"]));
    const drives = Object.keys(cells).map((ch) => esc(ch) + ": " + cells[ch].map(esc).join(", ")).join("; ");
    const turn = info.turn_signal_hz, threshold = info.turn_threshold_hz;
    const jumpScale = Math.max(meta.max_hz || 0, info.jump_signal_hz, info.jump_threshold_hz, 1);
    return '<div class="eyes">' + Object.keys(channels).map((ch) => "<span>" + esc(ch) + " " + hz(channels[ch]) +
      bar(channels[ch] / scale) + "</span>").join("") + "</div>" +
      '<p class="muted">Input' + (drives ? " to " + drives : "") + ". Which gaps drive which cells, and how hard, is ours.</p>" +
      spikeRaster(info, context.windowMs, groups) +
      '<p class="muted">' + esc(info.total_spikes) + " spikes in the whole brain" +
      (context.windowMs == null ? "" : " in " + esc(context.windowMs) + " ms") + "</p>" +
      '<div class="signal">turn signal ' + hz(turn) + ' <span class="muted">(right minus left of ' +
      types.map(esc).join(" + ") + ", our read-out; dodges beyond ±" + Math.round(threshold) + " Hz, our threshold)</span>" +
      turnBar(turn, threshold) + "</div>" +
      '<div class="signal">jump signal ' + hz(info.jump_signal_hz) + ' <span class="muted">(Giant Fiber; jumps above ' +
      hz(info.jump_threshold_hz) + ", our threshold, when it does not dodge)</span>" +
      bar(info.jump_signal_hz / jumpScale, info.jump_threshold_hz / jumpScale) + "</div>" +
      '<p class="muted">Our rule, dodge before jump: ' + (BRANCHES[info.branch] || esc(info.branch)) + ".</p>";
  }

  function jevMind(frame) {
    const answers = frame.answers;
    if (!answers) return "";
    const action = answers.action || {};
    const probabilities = action.probabilities || {};
    let html = '<table class="probs">' + ACTIONS.map((a) => "<tr" + (a === action.choice ? ' class="picked"' : "") + "><th>" + a +
      "</th><td>" + bar(probabilities[a] || 0) + "</td><td>" + percent(probabilities[a] || 0) + "</td></tr>").join("") + "</table>";
    if (typeof action.confidence === "number") html += '<p class="muted">confidence ' + percent(action.confidence) + "</p>";
    const nouls = [["gap_ahead", "Gap straight ahead?"], ["left_safe", "Left lane safe?"]];
    html += '<table class="probs">' + nouls.filter(([key]) => answers[key] && typeof answers[key].noul === "number").map(([key, label]) => {
      const truth = (frame.ground_truth || {})[key];
      const known = typeof truth === "boolean";
      const right = known && (answers[key].noul >= 0.5) === truth;
      return "<tr><th>" + label + "</th><td>" + bar(answers[key].noul) + "</td><td>" + percent(answers[key].noul) +
        ' yes</td><td class="' + (known && !right ? "warn" : "muted") + '">' +
        (known ? "truth: " + (truth ? "yes" : "no") : "") + "</td></tr>";
    }).join("") + "</table>";
    return html + '<p class="muted">The two yes/no questions are asked alongside the move and never influence it.</p>';
  }

  // jev_step1: four yes/no answers, one per action, and the rule that turns them into a move.
  function jevStep1Mind(frame) {
    const answers = frame.answers;
    if (!answers) return "";
    const rows = ACTIONS.map((a) => {
      const noul = (answers["gap_" + a] || {}).noul;
      const known = typeof noul === "number";
      return "<tr" + (a === frame.chosen_action ? ' class="picked"' : "") + "><th>" + a + "</th><td>" + bar(known ? noul : 0) +
        "</td><td>" + (known ? percent(noul) : "–") + "</td></tr>";
    }).join("");
    const order = frame.info && Array.isArray(frame.info.order) ? frame.info.order.map(esc).join(", ") : null;
    return '<p class="label">Lands on a gap?</p><table class="probs">' + rows + "</table>" +
      '<p class="muted">Four yes/no questions in one request; code picks the lowest' + (order ? ", ties in the order " + order : "") +
      ". The wording and that rule are ours. It looks one step ahead only.</p>";
  }

  // How sure jev_step1 was that the move it chose does not land on a gap (the visor's slit), or null
  function visorP(frame) {
    const answer = (frame.answers || {})["gap_" + frame.chosen_action];
    return answer && typeof answer.noul === "number" ? 1 - answer.noul : null;
  }

  // What a question-set player was told (docs/superpowers/specs/2026-09-21-jev-family-design.md): the read tiles as a
  // grid (darker = more sure it is a gap), each move's yes/no answers as bars, or the Choice it made.
  function readGrid(answers) {
    const tiles = Object.keys(answers).map((id) => /^tile_r(\d+)_(c|l\d+|r\d+)$/.exec(id)).filter(Boolean).map((m) => ({
      row: Number(m[1]), offset: m[2] === "c" ? 0 : (m[2][0] === "l" ? -1 : 1) * Number(m[2].slice(1)), p: answers[m[0]].noul }));
    if (!tiles.length) return "";
    const rows = Math.max(...tiles.map((t) => t.row)), window_ = Math.max(...tiles.map((t) => Math.abs(t.offset)));
    const cells = tiles.map((t) => '<rect x="' + (t.offset + window_) * 12 + '" y="' + (rows - t.row) * 8 +
      '" width="11" height="7" class="tile"/>' + (typeof t.p === "number" ? '<rect x="' + (t.offset + window_) * 12 + '" y="' +
      (rows - t.row) * 8 + '" width="11" height="7" class="gap" fill-opacity="' + Math.max(0, Math.min(1, t.p)).toFixed(2) + '"/>' : "")).join("");
    return '<p class="label">What it read (darker = more sure it is a gap)</p><svg class="senses" viewBox="0 0 ' +
      (2 * window_ + 1) * 12 + " " + rows * 8 + '" role="img" aria-label="the ' + tiles.length + ' tiles it read">' + cells + "</svg>";
  }

  function setMind(frame) {
    const answers = frame.answers;
    if (!answers) return "";
    const noul = (id) => (answers[id] && typeof answers[id].noul === "number" ? answers[id].noul : null);
    const kinds = [["gap_", "lands on a gap"], ["trapped_", "dead end after"]].filter(([prefix]) => ACTIONS.some((a) => answers[prefix + a]));
    let html = readGrid(answers);
    if (kinds.length) {
      html += '<table class="probs"><tr><th></th>' + kinds.map(([, label]) => "<th>" + label + "</th>").join("") + "</tr>" +
        ACTIONS.map((a) => "<tr" + (a === frame.chosen_action ? ' class="picked"' : "") + "><th>" + a + "</th>" +
          kinds.map(([prefix]) => { const p = noul(prefix + a); return "<td>" + (p == null ? "–" : bar(p) + " " + percent(p)) + "</td>"; }).join("") +
          "</tr>").join("") + "</table>";
    }
    if (answers.action && answers.action.choice != null) html += '<p class="label">Chose ' + esc(answers.action.choice) + "</p>";
    if (answers.stop_reason != null && answers.stop_reason !== "end_turn") html += '<p class="warn">stopped: ' + esc(answers.stop_reason) + "</p>";
    const rule = frame.info && frame.info.rule ? esc(frame.info.rule) : "its rule";
    return html + '<p class="muted">Code picks the move from these answers by ' + rule + ". The questions and that rule are ours.</p>";
  }

  function chatMind(frame) {
    const answers = frame.answers;
    if (!answers) return "";
    return '<pre class="answer">' + esc(answers.text == null ? "" : answers.text) + "</pre>" +
      (answers.stop_reason === "end_turn" ? "" : '<p class="warn">stopped: ' + esc(answers.stop_reason) + "</p>");
  }

  function cost(frame) {
    if (frame.cache_hit) return '<p class="muted">answer replayed from the cache</p>';
    if (frame.latency_ms == null) return "";
    const usage = frame.usage || {};
    return '<p class="muted">answered in ' + Math.round(frame.latency_ms) + " ms, " + esc(usage.input_tokens || 0) + " tokens in, " +
      esc(usage.output_tokens || 0) + " out</p>";
  }

  function asked(episode, frame) {
    if (frame.q == null || !episode.questions[frame.q]) return "";
    return "<details><summary>What it was asked</summary><pre>" + esc(JSON.stringify(episode.questions[frame.q], null, 2)) +
      "</pre></details>";
  }

  // the "what is ours" list, from one run of replay.runs (or undefined): everything the fly's
  // decisions are weighted by that is ours, not the fly's biology, read from the run's meta, never invented
  function ours(run) {
    const looming = run && run.game && run.game.looming;
    if (!run || !run.fly || !looming || looming.falloff == null) {
      return "<li>The runs in this replay did not record the fly's constants.</li>";
    }
    return "<li>Each gap the fly can see adds " + cell(looming.gain_hz) + " / row<sup>" + cell(looming.falloff) +
      "</sup> Hz to the eye on its side " +
      "(a gap in the runner's own lane: both eyes), capped at " + cell(looming.max_hz) + " Hz and rounded to " + cell(looming.step_hz) +
      " Hz steps. A gap one row away counts " + Math.pow(2, looming.falloff) + " times as much as one two rows away.</li>" +
      "<li>A turn signal beyond " + cell(run.fly.turn_threshold_hz) + " Hz turns; a Giant Fiber mean above " +
      cell(run.fly.jump_threshold_hz) + " Hz jumps, and a jump wins over a turn. Each decision simulates " +
      cell(run.fly.window_ms) + " ms from a clean brain.</li>" +
      (run.fly.provisional
        ? '<li class="warn">These values were provisional when this run was made: not yet calibrated.</li>'
        : "<li>The gain, the falloff and the two thresholds were chosen once, by a rule fixed beforehand, on practice tracks " +
          "1000 to 1199 of game v1, which are not the held-out tracks, then frozen (docs/calibration/REPORT.md)." +
          // a run from before game versions has no version and was v1
          (run.game.version && run.game.version !== "v1"
            ? " This run is game " + esc(run.game.version) + "; the fly was not retuned for it." : "") +
          " The cap, the step and the window length are fixed design choices of ours and were not tuned.</li>");
  }

  // fly2's part of "what is ours", from one run of replay.runs that played it (or undefined): its mapping,
  // read-out, rule, numbers and controls, all read from the run's meta. Empty when no run recorded fly2.
  function oursFly2(run) {
    const f = run && run.fly2;
    if (!f || f.mapping == null) return "";
    const seen = Object.keys(f.cells || {}).map((ch) => esc(ch) + " (lanes " + (f.sees[ch] || []).map(esc).join(", ") +
      ") drives " + f.cells[ch].map(esc).join(", ")).join("; ");
    let html = "<li>Input mapping " + esc(f.mapping) + ", " + esc(f.summary) + ": each gap a channel sees adds " +
      cell(f.gain_hz) + " / row<sup>" + cell(f.falloff) + "</sup> Hz, capped at " + cell(f.max_hz) + " Hz and rounded to " +
      cell(f.step_hz) + " Hz steps. " + seen + ". Lane 0 is the runner's own.</li>" +
      "<li>Read-out: the turn is right minus left of " + (f.turn_types || []).map(esc).join(" + ") +
      ", chosen for this mapping by a probe of the brain (spike 04); the jump is the Giant Fiber mean.</li>" +
      "<li>Rule, dodge before jump: a turn beyond " + cell(f.turn_threshold_hz) + " Hz goes left or right; otherwise a " +
      "Giant Fiber above " + cell(f.jump_threshold_hz) + " Hz jumps; otherwise it runs straight.</li>";
    if (f.provisional) return html + '<li class="warn">fly2\'s values were provisional when this run was made: not yet calibrated.</li>';
    const c = f.controls;
    const count = c && c.candidates != null ? " (one of " + cell(c.candidates) + ")" : "";
    const seeds = c && c.practice_seeds != null ? "on practice tracks " + esc(c.practice_seeds) + " of game v2, " : "";
    html += "<li>The mapping" + count + ", the gain, the falloff and the two thresholds were chosen once, by a rule fixed " +
      "before any measurement, " + seeds + "then frozen (docs/calibration/FLY2_REPORT.md).</li>";
    if (c) {
      html += "<li>Controls, mean rows on held-out tracks " + esc(c.seeds) + ", all played on the stand-in brain (the measured " +
        "response surfaces): fly2 " + cell(c.fly2) + ", the same rule with no brain " + cell(c.no_brain) +
        ", on shuffled wiring " + (c.shuffled == null ? "not measured" : cell(c.shuffled)) + ", fly on its own stand-in " +
        cell(c.fly) + ". Where the no-brain control does as well, the gain is our mapping's and rule's, not the wiring's.</li>";
    }
    return html;
  }

  // the whole panel for one decision; context = {windowMs, maxHz, window, fly2}, from the run's meta
  function mind(episode, frame, context) {
    const body = episode.player === "fly" ? flyMind(frame, context)
      : episode.player === "fly2" ? fly2Mind(frame, context)
      : episode.player === "jev_plain" ? jevMind(frame)
      : episode.player === "jev_step1" ? jevStep1Mind(frame)
      : episode.player === "haiku_plain" || episode.player === "glm_plain" ? chatMind(frame)
      : isSetPlayer(episode.player) ? setMind(frame) : "";
    return '<div class="saw">' + sensesGrid(frame, context.window) + verdict(frame) + "</div>" + body + cost(frame) + asked(episode, frame);
  }

  // one line under the tunnel: where the runner is, or how the episode ended
  function statusLine(episode, state, lanes) {
    const rows = esc(episode.rows_survived);
    if (state.status === "dead") return '<span class="bad">Fell after ' + rows + " rows: " + (DEATHS[episode.death_cause] || "fell") + "</span>";
    if (state.status === "finished") return "Reached the finish line, " + rows + " rows";
    if (state.status === "cut") return '<span class="warn">Run stopped after ' + rows + " rows (not a death)</span>";
    return "row " + Math.floor(state.row) + ", lane " + (((Math.round(state.lane) % lanes) + lanes) % lanes);
  }

  const api = { esc, cell, bar, tagOf, tagHtml, useRoster, sensesGrid, verdict, spikeRaster, flyMind, fly2Mind, oursFly2, jevMind, jevStep1Mind, visorP, chatMind, cost, asked,
                ours, mind, statusLine, isSetPlayer, readGrid, setMind };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Minds = api;
})(typeof window !== "undefined" ? window : globalThis);

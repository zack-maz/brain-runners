// What each player had in mind for one decision, as HTML strings (pure, tested under node).
// Everything that comes from a log goes through esc(): an LLM's answer is text, never markup.
(function (root) {
  "use strict";

  const ACTIONS = ["left", "stay", "right", "jump"];
  const FLY_GROUPS = [
    ["DNa01", "steering"], ["DNb01", "steering"], ["DNp01", "Giant Fiber, escape jump"], ["DNa02", "logged only"],
  ];
  const DEATHS = {
    ran_into_gap: "ran straight into a gap",
    jumped_into_gap: "jumped into a gap",
    dodged_into_gap: "stepped sideways into a gap",
  };

  const esc = (value) => String(value).replace(/[&<>"']/g, (c) => "&#" + c.charCodeAt(0) + ";");
  const percent = (p) => Math.round(p * 100) + "%";
  const hz = (value) => Math.round(value) + " Hz";

  // a horizontal bar, share 0..1, with an optional tick at `mark` (0..1)
  function bar(share, mark) {
    const width = Math.max(0, Math.min(1, share)) * 100;
    const tick = mark == null ? "" : '<i class="tick" style="left:' + Math.max(0, Math.min(1, mark)) * 100 + '%"></i>';
    return '<span class="bar"><i class="fill" style="width:' + width.toFixed(1) + '%"></i>' + tick + "</span>";
  }

  // The senses as the player got them: 6 rows ahead (far at the top), 3 lanes either side, gaps dark.
  function sensesGrid(frame) {
    let cells = "";
    for (let r = frame.ahead.length - 1; r >= 0; r--) {
      for (let off = -3; off <= 3; off++) {
        const gap = frame.ahead[r].includes(off);
        cells += '<rect x="' + (off + 3) * 12 + '" y="' + (frame.ahead.length - 1 - r) * 8 +
          '" width="11" height="7" class="' + (gap ? "gap" : "tile") + '"/>';
      }
    }
    const height = frame.ahead.length * 8;
    return '<svg class="senses" viewBox="0 0 84 ' + (height + 8) + '" role="img" aria-label="the six rows it was shown">' +
      cells + '<circle cx="41.5" cy="' + (height + 4) + '" r="3" class="me"/></svg>';
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
    const depth = frame.solver_depths[frame.chosen_action];
    const rating = best === 0 ? "no move was known to be safe"
      : depth === best ? "as good as any move (" + best + " rows seen safe)"
      : "solver preferred " + safe.join(" or ") + " (" + best + " rows safe, this move " + (depth || 0) + ")";
    return '<p class="verdict">' + line + '<br><span class="muted">' + rating + "</span></p>" +
      (frame.error != null ? '<p class="warn">' + esc(frame.error) + "</p>" : "");
  }

  function spikeRaster(info, windowMs) {
    const rowHeight = 9, width = 200;
    let rows = "";
    FLY_GROUPS.forEach(([group], g) => {
      ["left", "right"].forEach((side, s) => {
        const y = (g * 2 + s) * rowHeight + g * 4;
        const times = (info.spike_times_ms || {})[group + "_" + side] || [];
        rows += '<text x="0" y="' + (y + 7) + '">' + group + " " + side[0].toUpperCase() + "</text>";
        rows += times.map((t) => '<line class="spike ' + side + '" x1="' + (52 + (t / windowMs) * width).toFixed(1) +
          '" x2="' + (52 + (t / windowMs) * width).toFixed(1) + '" y1="' + y + '" y2="' + (y + rowHeight - 2) + '"/>').join("");
      });
    });
    const height = FLY_GROUPS.length * (2 * rowHeight + 4);
    return '<svg class="raster" viewBox="0 0 256 ' + height + '" role="img" aria-label="spikes of the read-out neurons over the ' +
      windowMs + ' ms window">' + rows + "</svg>";
  }

  function flyMind(frame, windowMs) {
    const info = frame.info;
    if (!info) return "";
    const turn = info.turn_signal_hz, limit = 100; // the turn bar spans -100 .. +100 Hz
    const turnShare = 0.5 + Math.max(-limit, Math.min(limit, turn)) / (2 * limit);
    return '<div class="eyes"><span>left eye ' + hz(info.left_hz) + bar(info.left_hz / 250) + "</span>" +
      "<span>right eye " + hz(info.right_hz) + bar(info.right_hz / 250) + "</span></div>" +
      '<p class="muted">Looming input to the LPLC2 and LC4 cells of each eye. The weighting of gaps is ours.</p>' +
      spikeRaster(info, windowMs) +
      '<p class="muted">' + info.total_spikes + " spikes in the whole brain in " + windowMs + " ms</p>" +
      '<div class="signal">turn signal ' + hz(turn) + ' <span class="muted">(right minus left steering)</span>' +
      '<span class="bar centred"><i class="fill" style="left:' + (Math.min(turnShare, 0.5) * 100).toFixed(1) + "%;width:" +
      (Math.abs(turnShare - 0.5) * 100).toFixed(1) + '%"></i><i class="tick" style="left:50%"></i></span></div>' +
      '<div class="signal">jump signal ' + hz(info.jump_signal_hz) + ' <span class="muted">(Giant Fiber; jumps above ' +
      hz(info.jump_threshold_hz) + ", our threshold)</span>" + bar(info.jump_signal_hz / 250, info.jump_threshold_hz / 250) + "</div>";
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
      const right = (answers[key].noul >= 0.5) === truth;
      return "<tr><th>" + label + "</th><td>" + bar(answers[key].noul) + "</td><td>" + percent(answers[key].noul) +
        ' yes</td><td class="' + (right ? "muted" : "warn") + '">truth: ' + (truth ? "yes" : "no") + "</td></tr>";
    }).join("") + "</table>";
    return html + '<p class="muted">The two yes/no questions are asked alongside the move and never influence it.</p>';
  }

  function llmMind(frame) {
    const answers = frame.answers;
    if (!answers) return "";
    return '<pre class="answer">' + esc(answers.text == null ? "" : answers.text) + "</pre>" +
      (answers.stop_reason === "end_turn" ? "" : '<p class="warn">stopped: ' + esc(answers.stop_reason) + "</p>");
  }

  function cost(frame) {
    if (frame.cache_hit) return '<p class="muted">answer replayed from the cache</p>';
    if (frame.latency_ms == null) return "";
    const usage = frame.usage || {};
    return '<p class="muted">answered in ' + Math.round(frame.latency_ms) + " ms, " + (usage.input_tokens || 0) + " tokens in, " +
      (usage.output_tokens || 0) + " out</p>";
  }

  function asked(episode, frame) {
    if (frame.q == null || !episode.questions[frame.q]) return "";
    return "<details><summary>What it was asked</summary><pre>" + esc(JSON.stringify(episode.questions[frame.q], null, 2)) +
      "</pre></details>";
  }

  // the whole panel for one decision; windowMs is the fly's simulated window from the run's meta
  function mind(episode, frame, windowMs) {
    const body = episode.player === "fly" ? flyMind(frame, windowMs || 100)
      : episode.player === "jev" ? jevMind(frame)
      : episode.player === "llm" ? llmMind(frame) : "";
    return '<div class="saw">' + sensesGrid(frame) + verdict(frame) + "</div>" + body + cost(frame) + asked(episode, frame);
  }

  // one line under the tunnel: where the runner is, or how the episode ended
  function statusLine(episode, state, lanes) {
    const rows = episode.rows_survived;
    if (state.status === "dead") return '<span class="warn">Fell after ' + rows + " rows: " + (DEATHS[episode.death_cause] || "fell") + "</span>";
    if (state.status === "finished") return "Reached the finish line, " + rows + " rows";
    if (state.status === "cut") return '<span class="warn">Run stopped after ' + rows + " rows (not a death)</span>";
    return "row " + Math.floor(state.row) + ", lane " + (((Math.round(state.lane) % lanes) + lanes) % lanes);
  }

  const api = { esc, bar, sensesGrid, verdict, spikeRaster, flyMind, jevMind, llmMind, cost, asked, mind, statusLine };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Minds = api;
})(typeof window !== "undefined" ? window : globalThis);

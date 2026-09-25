// The running log of one mind: one line per row, newest last (pure, so node --test can run it).
// Nothing here is streamed: every line is built from a frame the strip already has, and every value
// that comes from a log goes through esc(). Numbers are shown as the run recorded them.
(function (root) {
  "use strict";

  const Mind = typeof module !== "undefined" && module.exports ? require("./minds.js") : root.Minds;
  const esc = Mind.esc;

  const hz = (value) => (typeof value === "number" ? Math.round(value) + " Hz" : "–");
  // rounded, but never rounded to certainty: 0.004 is not 0% and 0.996 is not 100%
  const percent = (p) => (p > 0 && p < 0.005 ? "<1%" : p < 1 && p > 0.995 ? ">99%" : Math.round(p * 100) + "%");
  const CUT = 64; // how much of a written answer one line carries; the whole of it is in the panel above

  // one line of text, cut at CUT characters with an ellipsis, newlines flattened to spaces
  function short(text) {
    const flat = String(text).replace(/\s+/g, " ").trim();
    return flat.length > CUT ? flat.slice(0, CUT - 1) + "…" : flat;
  }

  // what the player was asked, in a few words. A question set names its questions; an LLM prompt is
  // one message, so it counts as one. A player that asks nothing (the fly, the solver) says nothing.
  function asked(episode, frame) {
    const questions = frame.q == null ? null : (episode.questions || [])[frame.q];
    if (!questions) return "";
    if (questions.system != null || questions.user != null) return "one prompt";
    const n = Object.keys(questions).length;
    return n === 1 ? "1 question" : n + " questions";
  }

  // what it answered: the fly's read-out, a written reply's first line, or how sure it was about the
  // move it picked. The number quoted is the one the panel above shows for that move.
  function answered(episode, frame) {
    const info = frame.info || {};
    if (episode.player === "fly") {
      // "ours" is the honesty rule: the looming input is our weighting of the gaps and the turn and
      // jump signals are read against our thresholds. The panel above says so; a log is read alone.
      return "input (ours) " + hz(info.left_hz) + " / " + hz(info.right_hz) + ", turn " + hz(info.turn_signal_hz) +
        ", jump " + hz(info.jump_signal_hz) + ", " + (info.total_spikes == null ? "–" : info.total_spikes) + " spikes";
    }
    if (episode.player === "fly2") {
      const channels = info.channels_hz || {};
      return "input (ours) " + Object.keys(channels).map((ch) => ch + " " + hz(channels[ch])).join(" / ") +
        ", turn " + hz(info.turn_signal_hz) + ", jump " + hz(info.jump_signal_hz) + ", " +
        ({ dodge: "dodged", jump: "jumped", stay: "stayed" }[info.branch] || "–") + " (our rule), " +
        (info.total_spikes == null ? "–" : info.total_spikes) + " spikes";
    }
    const answers = frame.answers;
    if (!answers) return "";
    if (typeof answers.text === "string" && answers.text !== "") return short(answers.text);
    const gap = (answers["gap_" + frame.chosen_action] || {}).noul;
    const trapped = (answers["trapped_" + frame.chosen_action] || {}).noul;
    // both halves when the set asks for both, because the rule chose on both
    if (typeof gap === "number" && typeof trapped === "number") {
      return "lands on a gap " + percent(gap) + " · trapped after it " + percent(trapped);
    }
    if (typeof gap === "number") return percent(gap) + " it lands on a gap";
    const choice = (answers.action || {}).choice;
    if (choice != null) return "chose " + choice;
    return "";
  }

  // the move, and why the game ran a different one when it did
  function move(frame) {
    if (frame.chosen_action === frame.executed_action) return esc(frame.chosen_action);
    const why = frame.error != null ? "error" : frame.invalid ? "not a valid move" : frame.gated ? "held back" : "no move";
    const said = '<span class="warn">' + why + ", ran " + esc(frame.executed_action) + "</span>";
    return frame.chosen_action == null ? said : esc(frame.chosen_action) + " " + said;
  }

  // how long it took, or that the answer never left this machine
  function timing(frame) {
    if (frame.cache_hit) return "cached";
    if (frame.latency_ms != null) return Math.round(frame.latency_ms) + " ms";
    const wall = (frame.info || {}).wall_ms; // the fly sends no request: what it took is its simulation
    if (wall != null) return "simulated in " + Math.round(wall) + " ms";
    return "";
  }

  // one row's line. `frame.row` is the row it decided on.
  function line(episode, frame) {
    const parts = [asked(episode, frame), answered(episode, frame), timing(frame)].filter((p) => p !== "");
    return '<li><span class="at">' + esc(String(frame.row).padStart(4, "0")) + "</span>" +
      '<span class="did">' + move(frame) + "</span>" +
      '<span class="said">' + parts.map(esc).join(" · ") + "</span>" +
      (frame.error == null ? "" : '<span class="bad">' + esc(frame.error) + "</span>") + "</li>";
  }

  // the whole log, oldest first, so the newest line is at the bottom
  function lines(episode, frames) {
    return frames.map((frame) => line(episode, frame)).join("");
  }

  const api = { asked, answered, move, timing, line, lines, short };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Log = api;
})(typeof window !== "undefined" ? window : globalThis);

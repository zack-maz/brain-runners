// Staging rules for three runners in one tunnel. Pure: no DOM (tested under node).
//
// `overlaps`: who is drawn translucent and fanned out, because they stand on top of one another.
// `autoFocus`: where the blue cursor goes when nobody is steering it.
(function (root) {
  "use strict";

  const ACTIONS = ["left", "stay", "right", "jump"];
  const NEAR_LANES = 0.5; // runners within half a lane of each other on the same row overlap
  const OVERLAP_ALPHA = 0.55;
  const HOLD_ROWS = 3; // auto-focus stays where it is for at least this many rows, so it does not flicker

  // distance between two lanes round the ring (lanes may be fractions and unwrapped)
  function laneDistance(a, b, lanes) {
    const d = (((a - b) % lanes) + lanes) % lanes;
    return Math.min(d, lanes - d);
  }

  // runners: [{id, row, lane}] of the runners being drawn, in panel order. Returns {id: {alpha, fan,
  // stack}}: fan is the sideways shift in units of one fan step (-1, 0, 1 for three runners on one tile),
  // stack the line its tag goes on (0 nearest the runner), so tags never overprint.
  function overlaps(runners, lanes) {
    const out = {};
    const groups = [];
    for (const runner of runners) {
      const group = groups.find((g) => g.some((other) =>
        Math.abs(other.row - runner.row) < 0.5 && laneDistance(other.lane, runner.lane, lanes) <= NEAR_LANES));
      if (group) group.push(runner); else groups.push([runner]);
    }
    for (const group of groups) {
      group.forEach((runner, i) => {
        out[runner.id] = group.length === 1 ? { alpha: 1, fan: 0, stack: 0 }
          : { alpha: OVERLAP_ALPHA, fan: i - (group.length - 1) / 2, stack: i };
      });
    }
    return out;
  }

  // how many of the four actions do not land on a gap, by the reference solver's reading of the same
  // senses (solver_depths is 0 for an action whose landing tile is a gap): the rule stays in Python
  function safeActions(frame) {
    const depths = frame.solver_depths || {};
    return ACTIONS.filter((action) => depths[action] > 0).length;
  }

  // Where auto-focus goes at time t. states: [{id, status, frame}] in panel order (from
  // Timeline.stateAt). It cuts to a runner that is still running and whose current decision has at
  // least one action that lands on a gap; among several, the one with the fewest safe actions, ties to
  // the current focus, then to panel order. It holds for HOLD_ROWS rows. Returns {focus, heldSince}.
  function autoFocus(current, states, heldSince, t) {
    const keep = { focus: current, heldSince };
    if (current != null && t >= heldSince && t - heldSince < HOLD_ROWS) return keep;
    const inDanger = states.filter((s) => s.status === "running" && safeActions(s.frame) < ACTIONS.length);
    if (!inDanger.length) return current == null && states.length ? { focus: states[0].id, heldSince: t } : keep;
    const fewest = Math.min(...inDanger.map((s) => safeActions(s.frame)));
    const tied = inDanger.filter((s) => safeActions(s.frame) === fewest);
    const pick = tied.find((s) => s.id === current) || tied[0];
    return pick.id === current ? keep : { focus: pick.id, heldSince: t };
  }

  const api = { OVERLAP_ALPHA, HOLD_ROWS, laneDistance, overlaps, safeActions, autoFocus };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Stage = api;
})(typeof window !== "undefined" ? window : globalThis);

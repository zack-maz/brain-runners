// Where a runner is at replay time t. Pure: no DOM, so `node --test viewer/tests` can run it.
//
// Time is measured in rows and every player's clock is the track: at time t everyone still running
// is at row t, so the columns show the same stretch of tunnel. A jump covers two rows, so it takes
// two ticks and the frame that decided it stays on screen for both.
(function (root) {
  "use strict";

  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  const smooth = (p) => p * p * (3 - 2 * p);

  // index of the last frame decided at or before time t (frames are sorted by row, first row is 0)
  function frameIndexAt(episode, t) {
    const frames = episode.frames;
    let lo = 0, hi = frames.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (frames[mid].row <= t) lo = mid; else hi = mid - 1;
    }
    return lo;
  }

  // -1, 0 or 1: the way the move went round the ring (lane 0 going left lands on the last lane)
  function laneShift(frame, lanes) {
    const delta = (((frame.landing[1] - frame.lane) % lanes) + lanes) % lanes;
    return delta === lanes - 1 ? -1 : delta;
  }

  // the row at which the episode's last move lands: where it died, finished or was cut off
  function endRow(episode) {
    return episode.frames[episode.frames.length - 1].landing[0];
  }

  // status: "running", or once the last move has landed "dead", "finished" or "cut" (a run that was
  // stopped, not a death). `lane` is not wrapped, so a step from lane 0 to lane 11 reads 0 -> -1 and
  // the tunnel turns the short way. `air` is 0..1, the height of a jump. `since` is the time since
  // the episode ended (0 while running); the view uses it to draw the fall.
  function stateAt(episode, t, lanes) {
    const index = frameIndexAt(episode, t);
    const frame = episode.frames[index];
    const advance = frame.landing[0] - frame.row;
    const p = clamp01((t - frame.row) / advance);
    const last = index === episode.frames.length - 1;
    let status = "running";
    if (last && p >= 1) status = !frame.alive ? "dead" : frame.finished ? "finished" : "cut";
    return {
      index, frame, status,
      row: frame.row + advance * p,
      lane: frame.lane + laneShift(frame, lanes) * smooth(p),
      air: advance === 2 ? Math.sin(Math.PI * p) : 0,
      since: status === "running" ? 0 : t - frame.landing[0],
    };
  }

  const api = { frameIndexAt, laneShift, endRow, stateAt };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Timeline = api;
})(typeof window !== "undefined" ? window : globalThis);

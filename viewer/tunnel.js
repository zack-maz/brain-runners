// The tunnel as seen from behind the runner. `quads` is pure geometry (tested under node);
// `draw` paints it on a canvas.
//
// The track is a ring of lanes, so it is drawn as a tube: the runner's lane is at the bottom, the
// lane to its right is to the right, and changing lane turns the tube. A gap is a missing tile.
(function (root) {
  "use strict";

  const DEPTH = 20; // rows drawn ahead of the runner
  const PERSPECTIVE = 0.32; // a tile d rows away is drawn at scale 1 / (1 + PERSPECTIVE * d)
  const RADIUS = 0.43; // tube radius at the runner, as a share of the canvas size

  const wrap = (lane, lanes) => ((lane % lanes) + lanes) % lanes;

  function isGap(track, row, lane) {
    return row >= 0 && row < track.gaps.length && track.gaps[row].includes(wrap(lane, track.lanes));
  }

  // lane offset from the runner, -lanes/2 .. lanes/2 - 1, the way the senses wrap it
  function offset(lane, from, lanes) {
    return wrap(lane - from + lanes / 2, lanes) - lanes / 2;
  }

  // Was tile (row, lane) in the senses of the decision taken at `seen` = {row, lane, lookahead, window}?
  function wasSeen(row, lane, seen, lanes) {
    const ahead = row - seen.row;
    return ahead >= 1 && ahead <= seen.lookahead && Math.abs(offset(lane, seen.lane, lanes)) <= seen.window;
  }

  // Floor tiles from far to near, each {row, lane, kind, depth, points}. kind: "seen" (the player was
  // shown this tile), "floor", or "finish" (past the last row). cam = {row, lane}, both may be fractions.
  function quads(track, cam, seen, size, maxRows) {
    const centre = size / 2;
    const step = (2 * Math.PI) / track.lanes;
    const point = (angle, d) => {
      const radius = (RADIUS * size) / (1 + PERSPECTIVE * d);
      return [centre + radius * Math.cos(angle), centre + radius * Math.sin(angle)];
    };
    const out = [];
    const first = Math.floor(cam.row);
    for (let row = first + DEPTH; row >= first; row--) {
      const near = Math.max(row - cam.row, -1), far = row + 1 - cam.row;
      // mirrors Game.step (bakeoff/game/engine.py): only row <= maxRows can ever be a fatal gap, so a
      // row past the finish line is never a hole, whatever `gaps` lists there
      const neverKills = row > maxRows;
      for (let lane = 0; lane < track.lanes; lane++) {
        if (!neverKills && isGap(track, row, lane)) continue;
        // canvas y points down, so the bottom of the tube is angle pi/2 and "right" is a smaller angle
        const angle = Math.PI / 2 - offset(lane, cam.lane, track.lanes) * step;
        const a = angle + step / 2, b = angle - step / 2;
        const kind = row >= maxRows ? "finish" : wasSeen(row, lane, seen, track.lanes) ? "seen" : "floor";
        out.push({ row, lane, kind, depth: near, points: [point(a, near), point(b, near), point(b, far), point(a, far)] });
      }
    }
    return out;
  }

  const rgb = (colour) => "rgb(" + colour.join(",") + ")";

  function mix(from, to, share) {
    return "rgb(" + from.map((c, i) => Math.round(c + (to[i] - c) * share)).join(",") + ")";
  }

  // state comes from Timeline.stateAt; colours are [r, g, b]
  function draw(ctx, size, track, state, seen, maxRows, colours) {
    ctx.fillStyle = rgb(colours.space);
    ctx.fillRect(0, 0, size, size);
    const cam = { row: state.row, lane: state.lane };
    for (const quad of quads(track, cam, seen, size, maxRows)) {
      const fog = Math.min(1, Math.max(0, quad.depth) / DEPTH);
      const base = quad.kind === "seen" ? colours.seen : quad.kind === "finish" ? colours.finish : colours.floor;
      ctx.fillStyle = mix(base, colours.space, fog * 0.85);
      ctx.strokeStyle = mix(colours.space, base, 0.25);
      ctx.lineWidth = 1;
      ctx.beginPath();
      quad.points.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    }
    drawRunner(ctx, size, state, colours);
  }

  // The runner stands at the bottom of the tube. A jump lifts it towards the middle; a death drops it
  // through the floor and fades it out over one row of time.
  function drawRunner(ctx, size, state, colours) {
    const fall = state.status === "dead" ? Math.min(1, state.since) : 0;
    if (fall >= 1) return;
    const floor = size / 2 + RADIUS * size * 0.92;
    const height = size * 0.075;
    const y = floor - state.air * size * 0.2 + fall * size * 0.16;
    ctx.globalAlpha = 1 - fall;
    ctx.fillStyle = "rgba(0,0,0,0.35)";
    ctx.beginPath();
    ctx.ellipse(size / 2, floor, height * (0.5 - state.air * 0.2), height * 0.14, 0, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = rgb(colours.runner);
    ctx.strokeStyle = rgb(colours.space); // an outline, so a grey baseline runner shows on grey tiles
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.roundRect(size / 2 - height * 0.3, y - height * 0.95, height * 0.6, height * 0.7, height * 0.2);
    ctx.fill();
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(size / 2, y - height * 1.2, height * 0.27, 0, 2 * Math.PI);
    ctx.fill();
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  const api = { DEPTH, isGap, offset, wasSeen, quads, draw };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Tunnel = api;
})(typeof window !== "undefined" ? window : globalThis);

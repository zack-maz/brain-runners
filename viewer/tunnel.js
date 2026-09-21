// The tunnel: one tube of poured concrete seen from a fixed camera. `quads`, `seenOutline` and `place`
// are pure geometry (tested under node); `draw` paints the tube on a canvas.
//
// The track is a ring of lanes, so it is drawn as a tube. The camera never turns: the start lane
// (lanes / 2) is at the bottom, the lane to its right is to the right, lane 0 is the ceiling. The
// camera moves along the tube with the clock, so every runner still running is on the nearest row.
// A gap is a missing tile.
(function (root) {
  "use strict";

  const DEPTH = 26; // rows drawn ahead of the camera
  const PERSPECTIVE = 0.3; // a tile d rows away is drawn at scale 1 / (1 + PERSPECTIVE * d)
  const RADIUS = 0.47; // tube radius at the camera, as a share of the canvas size
  const STANDS = 0.35; // how far into its tile a runner stands, in rows

  const wrap = (lane, lanes) => ((lane % lanes) + lanes) % lanes;

  function isGap(track, row, lane) {
    return row >= 0 && row < track.gaps.length && track.gaps[row].includes(wrap(lane, track.lanes));
  }

  // lane offset from `from`, -lanes/2 .. lanes/2 - 1, the way the senses wrap it
  function offset(lane, from, lanes) {
    return wrap(lane - from + lanes / 2, lanes) - lanes / 2;
  }

  // canvas y points down, so the bottom of the tube is angle pi/2 and "right" is a smaller angle.
  // `lane` may be a fraction and may be unwrapped (a step from lane 0 to lane 11 reads 0 -> -1).
  function angleOf(lane, lanes) {
    return Math.PI / 2 - (lane - Math.floor(lanes / 2)) * ((2 * Math.PI) / lanes);
  }

  function point(angle, depth, size) {
    const radius = (RADIUS * size) / (1 + PERSPECTIVE * depth);
    return [size / 2 + radius * Math.cos(angle), size / 2 + radius * Math.sin(angle)];
  }

  // the four corners of tile (row, lane) for a camera at `camRow` (a fraction while the clock runs)
  function corners(lanes, row, lane, camRow, size) {
    const half = Math.PI / lanes, angle = angleOf(lane, lanes);
    const near = Math.max(row - camRow, -1), far = row + 1 - camRow;
    return [point(angle + half, near, size), point(angle - half, near, size), point(angle - half, far, size), point(angle + half, far, size)];
  }

  // Floor tiles from far to near, each {row, lane, kind, depth, points}. kind: "floor", or "finish" (at or
  // past the last row). `row` is the camera's row and may be a fraction.
  function quads(track, row, size, maxRows) {
    const out = [];
    const first = Math.floor(row);
    for (let r = first + DEPTH; r >= first; r--) {
      // mirrors Game.step (bakeoff/game/engine.py): only row <= maxRows can ever be a fatal gap, so a
      // row past the finish line is never a hole, whatever `gaps` lists there
      const neverKills = r > maxRows;
      for (let lane = 0; lane < track.lanes; lane++) {
        if (!neverKills && isGap(track, r, lane)) continue;
        out.push({ row: r, lane, kind: r >= maxRows ? "finish" : "floor", depth: Math.max(r - row, -1),
                   points: corners(track.lanes, r, lane, row, size) });
      }
    }
    return out;
  }

  // The tiles a mind was shown for the decision in `frame`: `lookahead` rows ahead of where it stood,
  // `window` lanes either side. Lanes are wrapped by the caller's isGap / corners, not here.
  function seenOutline(frame, lookahead, window) {
    const tiles = [];
    for (let ahead = 1; ahead <= lookahead; ahead++) {
      for (let off = -window; off <= window; off++) tiles.push({ row: frame.row + ahead, lane: frame.lane + off });
    }
    return tiles;
  }

  // Where a runner is drawn. `state` comes from Timeline.stateAt; `camRow` is the clock (default: the
  // runner's own row). The runner stands on the tube wall with its head toward the axis: `rotation`
  // turns an upright sprite to stand there (0 at the bottom, pi on the ceiling). `lift` is how far a
  // jump raises it toward the axis, `fall` (0..1) how far a dead runner has dropped through the floor.
  function place(state, lanes, size, camRow) {
    const depth = state.row - (camRow == null ? state.row : camRow);
    const scale = 1 / (1 + PERSPECTIVE * Math.max(0, depth + STANDS));
    const angle = angleOf(state.lane, lanes);
    const [x, y] = point(angle, Math.max(0, depth + STANDS), size);
    return {
      x, y, scale, rotation: angle - Math.PI / 2,
      lift: state.air * 0.13 * size * scale,
      fall: state.status === "dead" ? Math.min(1, state.since) : 0,
      visible: depth > -0.5 && depth <= DEPTH,
    };
  }

  const ACCENT = "rgba(122,162,247,0.6)"; // brand --accent: only ever the focused mind's tiles

  function path(ctx, points) {
    ctx.beginPath();
    points.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.closePath();
  }

  // outline: the tiles from seenOutline for the mind in focus, or null
  function draw(ctx, size, track, row, maxRows, outline) {
    ctx.fillStyle = "#0A0A0A";
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = "#050505"; // the far end of the tube
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, ((RADIUS * size) / (1 + PERSPECTIVE * (DEPTH + 1))) * 0.92, 0, 2 * Math.PI);
    ctx.fill();
    for (const quad of quads(track, row, size, maxRows)) {
      const fog = Math.min(1, Math.max(0, quad.depth) / DEPTH);
      // poured concrete: slightly uneven greys that fade into the void; the finish is a lighter band
      const shade = Math.round((quad.kind === "finish" ? 78 : 34) * (1 - fog * 0.72) + ((quad.lane * 7 + quad.row * 3) % 5));
      ctx.fillStyle = "rgb(" + shade + "," + (shade + 2) + "," + (shade + 4) + ")";
      ctx.strokeStyle = fog > 0.75 ? "#1E2227" : "#2A2F35";
      ctx.lineWidth = 1;
      path(ctx, quad.points);
      ctx.fill();
      ctx.stroke();
    }
    if (!outline) return;
    ctx.strokeStyle = ACCENT;
    ctx.lineWidth = 1.5;
    for (const tile of outline) {
      if (tile.row - row > DEPTH || tile.row + 1 - row <= 0) continue;
      if (tile.row <= maxRows && isGap(track, tile.row, tile.lane)) continue;
      path(ctx, corners(track.lanes, tile.row, tile.lane, row, size));
      ctx.stroke();
    }
  }

  const api = { DEPTH, isGap, offset, angleOf, corners, quads, seenOutline, place, draw };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Tunnel = api;
})(typeof window !== "undefined" ? window : globalThis);

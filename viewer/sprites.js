// The runners as pixel sprites: grids of characters, one character = one pixel, `.` is empty.
// All of them are our own drawings. The LLM's orange critter is our rendition, not anyone's artwork.
// `pixels` and `visorCells` are pure (tested under node); `drawSprite` paints on a canvas.
(function (root) {
  "use strict";

  const GRIDS = {
    // a fruit fly seen from behind: pale folded wings, dark body, red eyes
    fly: ["..ee.ee..", "...bbb...", ".w.bbb.w.", "ww.bbb.ww", "wwwbbbwww", "ww.bbb.ww", ".w.bbb.w.", "...b.b...", "..b...b.."],
    // the same fly in a jump: wings open
    fly_open: ["..ee.ee..", "w..bbb..w", "ww.bbb.ww", "wwwbbbwww", "ww.bbb.ww", "w..bbb..w", "...bbb...", "...b.b...", "..b...b.."],
    chat: [".ooooooo.", ".ooooooo.", ".okoookoo", "ooooooooo", ".ooooooo.", ".ooooooo.", ".o.o.o.o.", ".o.o.o.o."],
    // "the visor": a pale monolith with one slit of five cells, V lit and v unlit (see visorCells)
    visor: [".jjjjj.", "jjjjjjj", "jVVVvvj", "jjjjjjj", ".jjjjj.", "..jjj..", ".jjjjj.", ".jjjjj.", ".j...j.", ".j...j."],
    // baselines and the one-shot Jev: a plain grey block
    block: ["ggggg", "ggggg", "ggggg", "ggggg", "ggggg", "ggggg", "ggggg"],
  };
  const INKS = { w: "#AEB4BA", b: "#3A4046", e: "#F7768E", o: "#D97757", k: "#1A0E0A", j: "#B9BEC4", V: "#FFFFFF", v: "#15181C", g: "#7C848D" };
  const SLIT = 5;

  // Which of the visor's five cells are lit, left to right: round(5 * p) of them, where p is the
  // probability Jev gave that the move it made does not land on a gap. Unknown p: none.
  function visorCells(p) {
    const lit = typeof p === "number" && isFinite(p) ? Math.round(SLIT * Math.max(0, Math.min(1, p))) : 0;
    return Array.from({ length: SLIT }, (_, i) => i < lit);
  }

  // The sprite as a list of {x, y, ink}, (0, 0) being the top left pixel. options: {p} for the visor's
  // slit, {open: true} for the fly's open wings.
  function pixels(name, options) {
    const opts = options || {};
    const grid = GRIDS[name === "fly" && opts.open ? "fly_open" : name] || GRIDS.block;
    const cells = name === "visor" ? visorCells(opts.p) : [];
    let slit = 0;
    const out = [];
    grid.forEach((line, y) => {
      for (let x = 0; x < line.length; x++) {
        let ink = line[x];
        if (ink === ".") continue;
        if (ink === "V" || ink === "v") ink = cells[slit++] ? "V" : "v";
        out.push({ x, y, ink: INKS[ink] });
      }
    });
    return out;
  }

  function sizeOf(name) {
    const grid = GRIDS[name] || GRIDS.block;
    return { width: grid[0].length, height: grid.length };
  }

  // The sprite painted once at whole-pixel size, so a translucent or rotated runner shows no seams
  // between its pixels. Cached per look: there are only a handful.
  const bitmaps = {};
  function bitmap(name, px, options) {
    const opts = options || {};
    const key = [name, px, !!opts.open, name === "visor" ? visorCells(opts.p).filter(Boolean).length : 0].join(" ");
    if (!bitmaps[key]) {
      const { width, height } = sizeOf(name);
      const canvas = document.createElement("canvas");
      canvas.width = width * px;
      canvas.height = height * px;
      const paint = canvas.getContext("2d");
      for (const cell of pixels(name, opts)) {
        paint.fillStyle = cell.ink;
        paint.fillRect(cell.x * px, cell.y * px, px, px);
      }
      bitmaps[key] = canvas;
    }
    return bitmaps[key];
  }

  // Paints the sprite standing on the canvas origin: feet at (0, 0), head toward -y, centred on x.
  // The caller translates and rotates the context (Tunnel.place). px is the whole-number size of one pixel.
  function drawSprite(ctx, name, px, options) {
    const image = bitmap(name, px, options);
    ctx.imageSmoothingEnabled = false; // pixel art stays hard-edged on a side wall too
    ctx.drawImage(image, -Math.round(image.width / 2), -image.height);
  }

  const api = { GRIDS, INKS, visorCells, pixels, sizeOf, drawSprite };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Sprites = api;
})(typeof window !== "undefined" ? window : globalThis);

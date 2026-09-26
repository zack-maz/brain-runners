const test = require("node:test");
const assert = require("node:assert/strict");
const { GRIDS, INKS, BODY, visorCells, pixels, sizeOf } = require("../sprites.js");

test("the approved grids, character for character", () => {
  assert.deepEqual(GRIDS.fly, ["..ee.ee..", "...bbb...", ".w.bbb.w.", "ww.bbb.ww", "wwwbbbwww", "ww.bbb.ww", ".w.bbb.w.", "...b.b...", "..b...b.."]);
  assert.deepEqual(GRIDS.chat, [".ooooooo.", ".ooooooo.", ".okoookoo", "ooooooooo", ".ooooooo.", ".ooooooo.", ".o.o.o.o.", ".o.o.o.o."]);
  assert.deepEqual(GRIDS.visor, [".jjjjj.", "jjjjjjj", "jVVVvvj", "jjjjjjj", ".jjjjj.", "..jjj..", ".jjjjj.", ".jjjjj.", ".j...j.", ".j...j."]);
  assert.deepEqual({ w: INKS.w, b: INKS.b, e: INKS.e, o: INKS.o, k: INKS.k, j: INKS.j, V: INKS.V, v: INKS.v },
    { w: "#AEB4BA", b: "#3A4046", e: "#F7768E", o: "#D97757", k: "#1A0E0A", j: "#B9BEC4", V: "#FFFFFF", v: "#15181C" });
});

test("every grid is a rectangle drawn only in known inks", () => {
  for (const [name, grid] of Object.entries(GRIDS)) {
    assert.equal(new Set(grid.map((line) => line.length)).size, 1, name);
    for (const ink of grid.join("").replace(/\./g, "")) assert.ok(INKS[ink], name + " uses " + ink);
  }
  assert.deepEqual(sizeOf("fly"), sizeOf("fly_open")); // the jump does not change the sprite's size
});

test("the visor's slit lights round(5 p) cells from the left", () => {
  assert.deepEqual(visorCells(0), [false, false, false, false, false]);
  assert.deepEqual(visorCells(0.5), [true, true, true, false, false]); // round(2.5) is 3
  assert.deepEqual(visorCells(1), [true, true, true, true, true]);
  assert.deepEqual(visorCells(0.29), [true, false, false, false, false]);
  assert.deepEqual(visorCells(1.7), [true, true, true, true, true]);
  assert.deepEqual(visorCells(null), [false, false, false, false, false]); // no answer: dark
  assert.deepEqual(visorCells(NaN), [false, false, false, false, false]);
});

test("the visor's pixels carry the slit, left to right", () => {
  const slit = (p) => pixels("visor", { p }).filter((c) => c.y === 2 && c.x >= 1 && c.x <= 5).map((c) => c.ink);
  assert.deepEqual(slit(1), Array(5).fill(INKS.V));
  assert.deepEqual(slit(0.4), [INKS.V, INKS.V, INKS.v, INKS.v, INKS.v]);
  assert.deepEqual(slit(undefined), Array(5).fill(INKS.v));
});

test("the fly opens its wings in a jump and keeps its red eyes", () => {
  const folded = pixels("fly"), open = pixels("fly", { open: true });
  assert.notDeepEqual(folded, open);
  for (const sprite of [folded, open]) assert.equal(sprite.filter((c) => c.ink === INKS.e).length, 4);
  assert.ok(open.some((c) => c.x === 0 && c.y === 1 && c.ink === INKS.w)); // a wing tip raised to the edge
});

test("an unknown sprite is a plain grey block", () => {
  assert.deepEqual(pixels("nobody"), pixels("block"));
  assert.ok(pixels("nobody").every((c) => c.ink === INKS.g));
  assert.deepEqual(sizeOf("nobody"), { width: 5, height: 7 });
});

test("the ox and the robot, character for character, each with a body ink", () => {
  assert.deepEqual(GRIDS.ox, ["y.........y", "yy.......yy", ".yttttttty.", "..ttttttt..", "..tktttkt..", "..ttttttt..", "...nnnnn...", "...nknkn...", "....y.y....", ".....y....."]);
  assert.deepEqual(GRIDS.bot, [".zzzzz.", ".zkzkz.", ".zzzzz.", ".zzzzz.", "..zzz..", "zzzzzzz", "z.zzz.z", "..z.z..", "..z.z.."]);
  for (const name of Object.keys(GRIDS)) assert.ok(GRIDS[name].join("").includes(BODY[name]), name + " has its body ink");
});

test("a skin paints the body in its colour and recolours only the cells it names", () => {
  const plain = pixels("chat"), map = pixels("chat", { color: "#1E2227", inks: { k: "#7AA2F7" } });
  assert.equal(map.length, plain.length);
  plain.forEach((cell, i) => {
    const want = cell.ink === INKS.o ? "#1E2227" : cell.ink === INKS.k ? "#7AA2F7" : cell.ink;
    assert.equal(map[i].ink, want);
  });
});

test("a skin's colour reaches the fly's open wings and the visor's lit slit takes the skin's ink", () => {
  const sideways = pixels("fly", { open: true, color: "#F7768E", inks: { e: "#AEB4BA" } }); // red wings, grey eyes
  const wings = GRIDS.fly_open.join("").split("w").length - 1;
  assert.equal(sideways.filter((c) => c.ink === "#F7768E").length, wings);
  assert.equal(sideways.filter((c) => c.ink === "#AEB4BA").length, 4);
  const slit = pixels("visor", { p: 1, color: "#1E2227", inks: { V: "#7AA2F7" } }).filter((c) => c.y === 2 && c.x >= 1 && c.x <= 5);
  assert.deepEqual(slit.map((c) => c.ink), Array(5).fill("#7AA2F7"));
});

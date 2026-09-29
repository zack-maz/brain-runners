const test = require("node:test");
const assert = require("node:assert/strict");
const { esc, linear, log, ticks, logTicks, logDomain, survivalPath, split, fmt } = require("../bench.js");

test("esc makes a run's text inert", () => {
  assert.equal(esc(`<img src=x onerror="a">'`), "&#60;img src=x onerror=&#34;a&#34;&#62;&#39;");
});

test("a linear scale maps the domain onto the range, a flat domain to its middle", () => {
  const x = linear([0, 150], [40, 340]);
  assert.equal(x(0), 40);
  assert.equal(x(75), 190);
  assert.equal(linear([5, 5], [0, 10])(5), 5);
});

test("a log scale spaces decades evenly", () => {
  const x = log([0.001, 1], [0, 300]);
  assert.equal(x(0.001), 0);
  assert.ok(Math.abs(x(0.01) - 100) < 1e-9 && Math.abs(x(1) - 300) < 1e-9);
});

test("ticks are round steps", () => {
  assert.deepEqual(ticks(0, 150, 5), [0, 50, 100, 150]);
  assert.deepEqual(ticks(0, 1, 4), [0, 0.5, 1]);
  assert.deepEqual(ticks(3, 3, 5), [3]);
  assert.deepEqual(logTicks(0.0004, 0.006), [0.0005, 0.001, 0.002, 0.005]);
  const [lo, hi] = logDomain([0.001, 0.01]);
  assert.ok(lo < 0.001 && hi > 0.01 && Math.abs(Math.log10(hi / lo) - 1.5) < 1e-9);
});

test("the survival line steps down where the share alive changes", () => {
  const id = (v) => v;
  assert.equal(survivalPath([1, 1, 0.5, 0.5, 0], id, id), "M0.0,1.0H2.0V0.5H4.0V0.0H4.0");
  assert.equal(survivalPath([1, 1, 1], id, id), "M0.0,1.0H2.0");
});

test("players without a value are kept apart, never drawn at 0", () => {
  const { placed, missing } = split([{ p: "a", v: 0.001 }, { p: "b", v: null }, { p: "c" }, { p: "d", v: 0 }], "v");
  assert.deepEqual(placed.map((p) => p.p), ["a"]);
  assert.deepEqual(missing.map((p) => p.p), ["b", "c", "d"]);
});

test("formats", () => {
  assert.equal(fmt.rows(144.6), "144.6");
  assert.equal(fmt.rows(null), "–");
  assert.equal(fmt.interval(133.8, 150), "133.8 to 150.0");
  assert.equal(fmt.interval(null, null), "–");
  assert.equal(fmt.percent(0.8), "80%");
  assert.equal(fmt.seconds(2.876), "2.88 s");
  assert.equal(fmt.seconds(0.0412), "0.041 s");
  assert.equal(fmt.usd(0.000637), "0.00064 USD");
  assert.equal(fmt.signed(-16.2), "−16.2");
  assert.equal(fmt.signed(35), "+35.0");
});

test("the frontier is a staircase from the cheapest point, along and then up", () => {
  const { frontierPath } = require("../bench.js");
  assert.equal(frontierPath([]), "");
  assert.equal(frontierPath([{ x: 10, y: 50 }]), "M10.0,50.0");
  // given out of order, drawn cheapest first; y grows downwards on a page, so more rows is a smaller y
  assert.equal(frontierPath([{ x: 90, y: 20 }, { x: 10, y: 80 }, { x: 40, y: 60 }]), "M10.0,80.0H40.0V60.0H90.0V20.0");
});

test("a track's cost and the named scores say free, estimate and no time instead of a number", () => {
  assert.equal(fmt.track({ cost_basis: "free", usd_per_track: 0 }), "free");
  assert.equal(fmt.track({ cost_basis: "listed", usd_per_track: 0.1302 }), "0.13 USD");
  assert.equal(fmt.track({ cost_basis: "estimate", usd_per_track: 0.00391 }), "0.0039 USD (estimate)");
  assert.equal(fmt.score(null, "free"), "free");
  assert.equal(fmt.score(370.12, "free"), "370");
  assert.equal(fmt.score(10.155, "free"), "10.2");
  assert.equal(fmt.score(0.5071, "no time"), "0.507");
});

test("rows per cent and the price say free and mark Jev's estimate, never reading as measured", () => {
  assert.equal(fmt.perCent({ cost_basis: "free", rows_per_cent: null }), "free");
  assert.equal(fmt.perCent({ cost_basis: "listed", rows_per_cent: 10.155 }), "10.2");
  assert.equal(fmt.perCent({ cost_basis: "estimate", rows_per_cent: 360.4 }), "360 (estimate)");
  assert.equal(fmt.perCent({ cost_basis: "listed", rows_per_cent: null }), "–");
  assert.equal(fmt.price({ cost_basis: "free", price_usd: 0 }), "free");
  assert.equal(fmt.price({ cost_basis: "listed", price_usd: 0.0006 }), "0.00060 USD");
  assert.equal(fmt.price({ cost_basis: "estimate", price_usd: 0.00003 }), "0.000030 USD (estimate)");
});

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

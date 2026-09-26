const test = require("node:test");
const assert = require("node:assert/strict");
const Lobby = require("../lobby.js");

const player = (name, extra) => ({ name, paid: false, price_usd: 0, requests_left: null, played_before: false,
                                   why_not: null, ...extra });
const state = (extra) => ({
  status: "lobby", game: { version: "v2" }, max_rows: 150, requests_per_row: 1, max_requests: 0,
  tournament: false, first_practice_seed: 1000, seed: 1001, run: null,
  players: [player("fly"), player("solver"),
            player("haiku_plain", { paid: true, price_usd: 0.0006, requests_left: 200 }),
            player("jev_step1", { paid: true, price_usd: 0.00003, requests_left: 200 }),
            player("glm_step1", { paid: true, price_usd: 0, requests_left: 200 })],
  ...extra,
});

test("the estimate is the worst case: every row a request, until the budget runs out", () => {
  const { rows, lines, total_usd } = Lobby.estimate(state(), ["fly", "haiku_plain", "jev_step1"]);
  assert.equal(rows, 150);
  assert.deepEqual(lines.map((l) => [l.player, l.requests]), [["haiku_plain", 150], ["jev_step1", 150]]);
  assert.equal(total_usd.toFixed(4), (150 * 0.0006 + 150 * 0.00003).toFixed(4));
  // a budget smaller than the track caps the estimate: the run stops when the cap is reached
  const short = Lobby.estimate(state({ players: [player("haiku_plain", { paid: true, price_usd: 0.0006, requests_left: 20 })] }), ["haiku_plain"]);
  assert.deepEqual(short.lines.map((l) => l.requests), [20]);
  assert.equal(short.total_usd.toFixed(4), "0.0120");
});

test("a run of free players says it spends nothing, and the free tier says so too", () => {
  assert.match(Lobby.estimateText(state(), ["fly", "solver"]), /spends nothing/);
  const text = Lobby.estimateText(state(), ["glm_step1"]);
  assert.match(text, /0 USD \(free tier\)/);
  assert.match(text, /GLM STEP 1 150 requests at worst/);
});

test("the estimate names each paid player, its worst case and whether the track was played before", () => {
  const played = state({ players: [player("haiku_plain", { paid: true, price_usd: 0.0006, requests_left: 150, played_before: true })] });
  const text = Lobby.estimateText(played, ["haiku_plain"]);
  assert.match(text, /At worst this run of 150 rows spends 0.09 USD/);
  assert.match(text, /HAIKU PLAIN 150 requests at worst, 0.09 USD, played before \(some answers may be cached\)/);
});

test("money is written so that a fraction of a cent is still readable", () => {
  assert.equal(Lobby.usd(0), "0.00 USD");
  assert.equal(Lobby.usd(0.00003), "0.00003 USD"); // a price far below a cent keeps its digits
  assert.equal(Lobby.usd(1e-12), "less than 0.00000001 USD");
  assert.equal(Lobby.usd(0.0045), "0.0045 USD");
  assert.equal(Lobby.usd(1.5), "1.50 USD");
});

test("the page says why a run cannot be started, before anyone presses anything", () => {
  assert.equal(Lobby.whyNot(state(), ["fly"], 1001), null);
  assert.equal(Lobby.whyNot(state(), [], 1001), "choose at least one player");
  assert.equal(Lobby.whyNot(state(), ["fly"], -1), "the track must be a whole number, 0 or more");
  assert.equal(Lobby.whyNot(state(), ["fly"], 1.5), "the track must be a whole number, 0 or more");
  assert.equal(Lobby.whyNot(state({ status: "running" }), ["fly"], 1001), "a run is already going");
  const refused = state({ players: [player("haiku_plain", { paid: true, why_not: "no requests left" })] });
  assert.equal(Lobby.whyNot(refused, ["haiku_plain"], 7), "no requests left");
});

test("a name from the server is text, never markup", () => {
  const evil = "</label><script>alert(1)</script>";
  assert.equal(Lobby.estimateText(state({ players: [player(evil, { paid: true, price_usd: 1, requests_left: 2 })] }),
                                  [evil]).includes("<script>"), false);
});

test("with nothing left of the cap the page says what a paid player can still do, and asks nothing", () => {
  // a cap of 0 is the default: paid players replay what is cached and stop at their first uncached
  // question, so the run cannot spend and there is nothing to confirm
  const spent = state({ players: [player("haiku_plain", { paid: true, price_usd: 0.0065, requests_left: 0 })] });
  assert.match(Lobby.estimateText(spent, ["haiku_plain"]), /No request left of this command's cap/);
  assert.match(Lobby.estimateText(spent, ["haiku_plain"]), /stop at their first uncached question/);
  assert.equal(Lobby.spends(spent, ["haiku_plain"]), false);
  assert.equal(Lobby.spends(state(), ["haiku_plain"]), true);
  assert.equal(Lobby.spends(state(), ["fly", "solver"]), false);
});

test("the ceiling is written out, cap or no cap", () => {
  assert.match(Lobby.ceilingText(state()), /without a cap, so paid players only replay answers that are already cached/);
  assert.match(Lobby.ceilingText(state()), /may only play seeds 1000 and up/);
  assert.match(Lobby.ceilingText(state({ max_requests: 700 })), /cap is 700 requests for each paid player/);
  assert.match(Lobby.ceilingText(state({ tournament: true })), /Seeds below 1000 are allowed here/);
  assert.match(Lobby.ceilingText(state()), /Nothing on this page can raise either\./);
});

test("Jev plays without a cap: its worst case is the whole track, shown but never confirmed (decision 50)", () => {
  const uncapped = state({ players: [
    player("jev_step1", { paid: true, price_usd: 0.00003, requests_left: null, capped: false }),
    player("haiku_plain", { paid: true, price_usd: 0.0006, requests_left: 0, capped: true })] });
  const { lines, total_usd } = Lobby.estimate(uncapped, ["jev_step1"]);
  assert.deepEqual(lines.map((l) => [l.player, l.requests, l.uncapped]), [["jev_step1", 150, true]]);
  assert.equal(total_usd.toFixed(4), (150 * 0.00003).toFixed(4));
  assert.equal(Lobby.spends(uncapped, ["jev_step1"]), false); // it costs the user nothing: no confirmation
  assert.match(Lobby.estimateText(uncapped, ["jev_step1"]), /JEV STEP 1 150 requests at worst, 0\.0045 USD, no cap/);
  assert.match(Lobby.ceilingText(uncapped), /Jev plays without a cap; its requests are still counted and priced\./);
  // a capped player beside it still asks for confirmation when it has requests left
  const both = state({ players: [...uncapped.players.slice(0, 1),
    player("haiku_plain", { paid: true, price_usd: 0.0006, requests_left: 10, capped: true })] });
  assert.equal(Lobby.spends(both, ["jev_step1", "haiku_plain"]), true);
});

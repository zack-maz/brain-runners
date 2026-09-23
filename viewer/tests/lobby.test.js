const test = require("node:test");
const assert = require("node:assert/strict");
const Lobby = require("../lobby.js");

const player = (name, extra) => ({ name, paid: false, price_usd: 0, requests_left: null, played_before: false,
                                   why_not: null, ...extra });
const state = (extra) => ({
  status: "lobby", game: { version: "v2" }, max_rows: 150, requests_per_row: 1, max_requests: 0,
  tournament: false, first_practice_seed: 1000, seed: 1001, run: null,
  players: [player("fly"), player("solver"),
            player("llm", { paid: true, price_usd: 0.0006, requests_left: 200 }),
            player("jev_composed", { paid: true, price_usd: 0.00003, requests_left: 200 }),
            player("glm_composed", { paid: true, price_usd: 0, requests_left: 200 })],
  ...extra,
});

test("the estimate is the worst case: every row a request, until the budget runs out", () => {
  const { rows, lines, total_usd } = Lobby.estimate(state(), ["fly", "llm", "jev_composed"]);
  assert.equal(rows, 150);
  assert.deepEqual(lines.map((l) => [l.player, l.requests]), [["llm", 150], ["jev_composed", 150]]);
  assert.equal(total_usd.toFixed(4), (150 * 0.0006 + 150 * 0.00003).toFixed(4));
  // a budget smaller than the track caps the estimate: the run stops when the cap is reached
  const short = Lobby.estimate(state({ players: [player("llm", { paid: true, price_usd: 0.0006, requests_left: 20 })] }), ["llm"]);
  assert.deepEqual(short.lines.map((l) => l.requests), [20]);
  assert.equal(short.total_usd.toFixed(4), "0.0120");
});

test("a run of free players says it spends nothing, and the free tier says so too", () => {
  assert.match(Lobby.estimateText(state(), ["fly", "solver"]), /spends nothing/);
  const text = Lobby.estimateText(state(), ["glm_composed"]);
  assert.match(text, /0 USD \(free tier\)/);
  assert.match(text, /GLM COMPOSED 150 requests at worst/);
});

test("the estimate names each paid player, its worst case and whether the track was played before", () => {
  const played = state({ players: [player("llm", { paid: true, price_usd: 0.0006, requests_left: 150, played_before: true })] });
  const text = Lobby.estimateText(played, ["llm"]);
  assert.match(text, /At worst this run of 150 rows spends 0.09 USD/);
  assert.match(text, /LLM 150 requests at worst, 0.09 USD, played before \(some answers may be cached\)/);
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
  const refused = state({ players: [player("llm", { paid: true, why_not: "no requests left" })] });
  assert.equal(Lobby.whyNot(refused, ["llm"], 7), "no requests left");
});

test("the player list marks the paid ones, their price and what is left of the cap", () => {
  const html = Lobby.playerList(state(), ["fly"]);
  assert.match(html, /value="fly" checked/);
  assert.match(html, /value="solver"(?! checked)/);
  assert.match(html, /0\.0006 USD a request · 200 left of the cap/);
  assert.match(html, /free tier · 200 left of the cap/); // GLM Flash
  assert.match(html, />free</);
});

test("a player that may not run is disabled and says why", () => {
  const blocked = state({ players: [player("llm", { paid: true, price_usd: 0.0006, requests_left: 0,
                                                    why_not: "llm has no requests left of this session's cap of 5" })] });
  const html = Lobby.playerList(blocked, []);
  assert.match(html, /disabled/);
  assert.match(html, /class="pick blocked"/);
  assert.match(html, /no requests left of this session&#39;s cap of 5/);
});

test("a name or a reason from the server is text, never markup", () => {
  const evil = "</label><script>alert(1)</script>";
  const html = Lobby.playerList(state({ players: [player(evil, { why_not: evil })] }), []);
  assert.equal(html.includes("<script>"), false);
  assert.match(html, /&#60;script&#62;/);
  assert.equal(Lobby.estimateText(state({ players: [player(evil, { paid: true, price_usd: 1, requests_left: 2 })] }),
                                  [evil]).includes("<script>"), false);
});

test("with nothing left of the cap the page says what a paid player can still do, and asks nothing", () => {
  // a cap of 0 is the default: paid players replay what is cached and stop at their first uncached
  // question, so the run cannot spend and there is nothing to confirm
  const spent = state({ players: [player("llm", { paid: true, price_usd: 0.0065, requests_left: 0 })] });
  assert.match(Lobby.estimateText(spent, ["llm"]), /No request left of this command's cap/);
  assert.match(Lobby.estimateText(spent, ["llm"]), /stop at their first uncached question/);
  assert.equal(Lobby.spends(spent, ["llm"]), false);
  assert.equal(Lobby.spends(state(), ["llm"]), true);
  assert.equal(Lobby.spends(state(), ["fly", "solver"]), false);
});

test("the ceiling is written out, cap or no cap", () => {
  assert.match(Lobby.ceilingText(state()), /without a cap, so paid players only replay answers that are already cached/);
  assert.match(Lobby.ceilingText(state()), /may only play seeds 1000 and up/);
  assert.match(Lobby.ceilingText(state({ max_requests: 700 })), /cap is 700 requests for each paid player/);
  assert.match(Lobby.ceilingText(state({ tournament: true })), /Seeds below 1000 are allowed here/);
  assert.match(Lobby.ceilingText(state()), /Nothing on this page can raise either\./);
});

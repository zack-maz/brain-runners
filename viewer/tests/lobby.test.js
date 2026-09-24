const test = require("node:test");
const assert = require("node:assert/strict");
const Lobby = require("../lobby.js");

const player = (name, extra) => ({ name, paid: false, price_usd: 0, requests_left: null, played_before: false,
                                   why_not: null, ...extra });
const state = (extra) => ({
  status: "lobby", game: { version: "v2" }, max_rows: 150, requests_per_row: 1, max_requests: 0,
  tournament: false, first_practice_seed: 1000, seed: 1001, run: null,
  players: [player("fly"), player("solver"),
            player("haiku", { paid: true, price_usd: 0.0006, requests_left: 200 }),
            player("jev_composed", { paid: true, price_usd: 0.00003, requests_left: 200 }),
            player("glm_composed", { paid: true, price_usd: 0, requests_left: 200 })],
  ...extra,
});

test("the estimate is the worst case: every row a request, until the budget runs out", () => {
  const { rows, lines, total_usd } = Lobby.estimate(state(), ["fly", "haiku", "jev_composed"]);
  assert.equal(rows, 150);
  assert.deepEqual(lines.map((l) => [l.player, l.requests]), [["haiku", 150], ["jev_composed", 150]]);
  assert.equal(total_usd.toFixed(4), (150 * 0.0006 + 150 * 0.00003).toFixed(4));
  // a budget smaller than the track caps the estimate: the run stops when the cap is reached
  const short = Lobby.estimate(state({ players: [player("haiku", { paid: true, price_usd: 0.0006, requests_left: 20 })] }), ["haiku"]);
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
  const played = state({ players: [player("haiku", { paid: true, price_usd: 0.0006, requests_left: 150, played_before: true })] });
  const text = Lobby.estimateText(played, ["haiku"]);
  assert.match(text, /At worst this run of 150 rows spends 0.09 USD/);
  assert.match(text, /HAIKU 150 requests at worst, 0.09 USD, played before \(some answers may be cached\)/);
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
  const refused = state({ players: [player("haiku", { paid: true, why_not: "no requests left" })] });
  assert.equal(Lobby.whyNot(refused, ["haiku"], 7), "no requests left");
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
  const blocked = state({ players: [player("haiku", { paid: true, price_usd: 0.0006, requests_left: 0,
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
  const spent = state({ players: [player("haiku", { paid: true, price_usd: 0.0065, requests_left: 0 })] });
  assert.match(Lobby.estimateText(spent, ["haiku"]), /No request left of this command's cap/);
  assert.match(Lobby.estimateText(spent, ["haiku"]), /stop at their first uncached question/);
  assert.equal(Lobby.spends(spent, ["haiku"]), false);
  assert.equal(Lobby.spends(state(), ["haiku"]), true);
  assert.equal(Lobby.spends(state(), ["fly", "solver"]), false);
});

test("the ceiling is written out, cap or no cap", () => {
  assert.match(Lobby.ceilingText(state()), /without a cap, so paid players only replay answers that are already cached/);
  assert.match(Lobby.ceilingText(state()), /may only play seeds 1000 and up/);
  assert.match(Lobby.ceilingText(state({ max_requests: 700 })), /cap is 700 requests for each paid player/);
  assert.match(Lobby.ceilingText(state({ tournament: true })), /Seeds below 1000 are allowed here/);
  assert.match(Lobby.ceilingText(state()), /Nothing on this page can raise either\./);
});

// ---- the grid: question sets down, models across -------------------------------------------------

const ALL = ["fly", "solver", "random", "always_jump", "jev", "haiku",
             "jev_composed", "haiku_composed", "glm_composed",
             "jev_choice", "haiku_choice", "glm_choice",
             "jev_two_step", "haiku_two_step", "glm_two_step",
             "jev_reader", "haiku_reader", "glm_reader"];
const everyone = (extra) => state({ players: ALL.map((n) => player(n, { paid: !["fly", "solver", "random", "always_jump"].includes(n) })), ...extra });

test("playerAt names the player at each crossing, and nothing where there is none", () => {
  assert.equal(Lobby.playerAt("composed", "jev"), "jev_composed");
  assert.equal(Lobby.playerAt("composed", "haiku"), "haiku_composed");
  assert.equal(Lobby.playerAt("two_step", "glm"), "glm_two_step");
  assert.equal(Lobby.playerAt("", "jev"), "jev");
  assert.equal(Lobby.playerAt("", "haiku"), "haiku");
  assert.equal(Lobby.playerAt("", "glm"), null); // GLM never had a one-shot
});

test("every player the server offers appears exactly once", () => {
  const html = Lobby.playerList(everyone(), []);
  for (const name of ALL) {
    const seen = html.split('value="' + name + '"').length - 1;
    assert.equal(seen, 1, name + " appears " + seen + " times");
  }
});

test("a player nobody planned for still shows up rather than vanishing", () => {
  const html = Lobby.playerList(everyone({ players: [player("fly"), player("brand_new_mind")] }), []);
  assert.match(html, /value="brand_new_mind"/);
});

test("the grid says what each question set asks and what each model is", () => {
  const html = Lobby.playerList(everyone(), []);
  assert.match(html, /Four yes\/no questions/);
  assert.match(html, /Eight questions, two moves ahead/);
  assert.match(html, /Reads every tile/);
  assert.match(html, /Jev/);
  assert.match(html, /Claude Haiku/);
  assert.match(html, /GLM Flash/);
  assert.match(html, /Asked nothing/);            // the fly
  assert.match(html, /Yardsticks, not contestants/);
});

test("a crossing with no player is an em dash, not an empty box", () => {
  const html = Lobby.playerList(everyone(), []);
  assert.match(html, /<td class="none"[^>]*>—<\/td>/);
});

test("a column no player fills is left out altogether", () => {
  const withoutGlm = everyone({ players: ALL.filter((n) => !n.startsWith("glm")).map((n) => player(n)) });
  const html = Lobby.playerList(withoutGlm, []);
  assert.equal(html.includes("GLM Flash"), false);
  assert.match(html, /Claude Haiku/);
});

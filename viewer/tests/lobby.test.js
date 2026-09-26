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

test("the player list marks the paid ones, their price and what is left of the cap", () => {
  const html = Lobby.playerList(state(), ["fly"]);
  assert.match(html, /value="fly" checked/);
  assert.match(html, /value="solver"(?! checked)/);
  assert.match(html, /0\.0006 USD a request · 200 left of the cap/);
  assert.match(html, /free tier · 200 left of the cap/); // GLM Flash
  assert.match(html, />free</);
});

test("a player that may not run is disabled and says why", () => {
  const blocked = state({ players: [player("haiku_plain", { paid: true, price_usd: 0.0006, requests_left: 0,
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

// ---- the grid: question sets down, models across -------------------------------------------------

const ALL = ["fly", "solver", "random", "always_jump", "jev_plain", "haiku_plain", "glm_plain",
             "jev_step1", "haiku_step1", "glm_step1",
             "jev_guided", "haiku_guided", "glm_guided",
             "jev_step2", "haiku_step2", "glm_step2",
             "jev_map", "haiku_map", "glm_map"];
const everyone = (extra) => state({ players: ALL.map((n) => player(n, { paid: !["fly", "solver", "random", "always_jump"].includes(n) })), ...extra });

test("playerAt names the player at each crossing, and nothing where there is none", () => {
  assert.equal(Lobby.playerAt("step1", "jev"), "jev_step1");
  assert.equal(Lobby.playerAt("step1", "haiku"), "haiku_step1");
  assert.equal(Lobby.playerAt("step2", "glm"), "glm_step2");
  assert.equal(Lobby.playerAt("plain", "jev"), "jev_plain");
  assert.equal(Lobby.playerAt("plain", "haiku"), "haiku_plain");
  assert.equal(Lobby.playerAt("plain", "glm"), "glm_plain");
});

const modelled = (extra) => everyone({ players: ALL.map((n) => player(n, {
  paid: /^(jev|haiku|glm)/.test(n),
  model: n.startsWith("jev_plain") ? "jev-latest" : n.startsWith("haiku_plain") ? "claude-haiku-4-5-20251001"
    : n.startsWith("glm_plain") ? "glm-4.5-flash" : null,
  model_answered: n.startsWith("jev_plain") ? "jev-1.13.0" : n.startsWith("haiku_plain") ? "claude-haiku-4-5-20251001"
    : n.startsWith("glm_plain") ? "glm-4.5-flash" : null })), ...extra });

test("each column says which model version it really used, above what the model is", () => {
  const html = Lobby.playerList(modelled(), []);
  assert.match(html, /Claude Haiku 4\.5<\/span><span class="note mono">claude-haiku-4-5-20251001<\/span>/);
  assert.match(html, /GLM-4\.5 Flash<\/span><span class="note mono">glm-4\.5-flash<\/span>/);
});

test("a moving name shows the version it answered as, and says what was asked for", () => {
  const html = Lobby.playerList(modelled(), []);
  assert.match(html, /jev-1\.13\.0<span class="muted"> asked as jev-latest<\/span>/);
  assert.equal(html.includes('mono">jev-latest'), false);
});

test("a column with no answer yet falls back to the name it asks for", () => {
  const nothingPlayed = everyone({ players: ALL.map((n) => player(n, { model: /^jev/.test(n) ? "jev-latest" : null })) });
  assert.match(Lobby.playerList(nothingPlayed, []), /<span class="note mono">jev-latest<\/span>/);
});

test("a column whose players never say their model keeps its header, without a version", () => {
  const html = Lobby.playerList(everyone(), []);   // no model field at all
  assert.equal(html.includes('class="note mono"'), false);
  assert.match(html, /Claude Haiku 4\.5/);
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
  assert.match(html, /Step 1<\/span>/);
  assert.match(html, /Would each move land on a gap\?/);
  assert.match(html, /Map<\/span>/);
  assert.match(html, /Jev/);
  assert.match(html, /Claude Haiku 4\.5/);
  assert.match(html, /GLM-4\.5 Flash/);
  assert.match(html, /Asked nothing/);            // the fly
  assert.match(html, /Yardsticks, not contestants/);
});

test("a crossing with no player is an em dash, not an empty box", () => {
  const short = everyone({ players: ALL.filter((n) => n !== "glm_plain").map((n) => player(n)) });
  const html = Lobby.playerList(short, []);       // the GLM column stands, its plain cell is empty
  assert.match(html, /<td class="none"[^>]*>—<\/td>/);
});

test("a column no player fills is left out altogether", () => {
  const withoutGlm = everyone({ players: ALL.filter((n) => !n.startsWith("glm")).map((n) => player(n)) });
  const html = Lobby.playerList(withoutGlm, []);
  assert.equal(html.includes("GLM-4.5 Flash"), false);
  assert.match(html, /Claude Haiku 4\.5/);
});

test("both flies sit in the row of those asked nothing, each saying what it is", () => {
  const players = [player("fly", { about: "looming → escape reflex (phase 2)" }),
                   player("fly2", { about: "a straight-ahead channel, walking-steering neurons, dodge before jump",
                                    why_not: "fly2 is not calibrated yet (calibration/FLY2_REPORT.md)" }),
                   player("solver")];
  const html = Lobby.playerList(state({ players }), []);
  const asked = html.slice(html.indexOf("Asked nothing"), html.indexOf("Yardsticks"));
  assert.match(asked, /value="fly"/);
  assert.match(asked, /value="fly2" disabled/);
  assert.match(asked, /looming → escape reflex \(phase 2\)/);
  assert.match(asked, /a straight-ahead channel, walking-steering neurons, dodge before jump/);
  assert.match(asked, /fly2 is not calibrated yet/);
  assert.match(asked, /How gaps become input is ours/);
});

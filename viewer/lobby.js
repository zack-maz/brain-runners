// The lobby: who may run, what a run would cost at worst, and the list the page shows. Pure and
// tested under node; app.js does the fetching and the DOM. Everything that comes from the server
// goes through esc(): a player name or a refusal is text, never markup.
//
// `state` is what GET /state answers (bakeoff/session.py): {status, game, max_rows, requests_per_row,
// max_requests, tournament, first_practice_seed, seed, players: [{name, paid, price_usd,
// requests_left, played_before, why_not}], run}.
(function (root) {
  "use strict";

  const Minds_ = typeof require !== "undefined" ? require("./minds.js") : root.Minds;
  const esc = Minds_.esc;
  const tagOf = Minds_.tagOf;

  // USD, as the page writes it: 0 is free, and a price far below a cent keeps enough digits to be read
  // (Jev is 0.00003 USD a request), so nothing that costs money is ever written as 0.00.
  function usd(amount) {
    if (!(amount > 0)) return "0.00 USD";
    if (amount >= 0.01) return amount.toFixed(2) + " USD";
    const digits = Math.min(8, Math.max(4, 1 - Math.floor(Math.log10(amount))));
    const written = amount.toFixed(digits).replace(/0+$/, "");
    return Number(written) > 0 ? written + " USD" : "less than 0.00000001 USD";
  }

  // The worst case of the run about to be asked for: every row of the track costs a request for every
  // paid player, until its budget runs out. Nothing here is a bill; it is the most it could come to.
  function estimate(state, chosen) {
    const byName = new Map((state.players || []).map((p) => [p.name, p]));
    const rows = state.max_rows || 0;
    const lines = [];
    let total = 0;
    for (const name of chosen) {
      const player = byName.get(name);
      if (!player || !player.paid) continue;
      const requests = Math.min(rows * (state.requests_per_row || 1), player.requests_left || 0);
      const cost = requests * (player.price_usd || 0);
      total += cost;
      lines.push({ player: name, requests, usd: cost, free: !(player.price_usd > 0),
                   played_before: !!player.played_before });
    }
    return { rows, lines, total_usd: total };
  }

  // What the page says before it starts a run, and what the user confirms.
  function estimateText(state, chosen) {
    const { rows, lines, total_usd } = estimate(state, chosen);
    if (!lines.length) return "No paid player: this run spends nothing.";
    const each = lines.map((line) => tagOf(line.player) + " " + line.requests + " request" +
      (line.requests === 1 ? "" : "s") + " at worst, " + (line.free ? "0 USD (free tier)" : usd(line.usd)) +
      (line.played_before ? ", played before (some answers may be cached)" : ""));
    if (!lines.some((line) => line.requests > 0)) {
      return "No request left of this command's cap: the paid players replay what is already cached and stop " +
        "at their first uncached question. This run spends nothing.";
    }
    return "At worst this run of " + rows + " rows spends " + usd(total_usd) + ": " + each.join(" · ") +
      ". Cached answers are free, so the real cost is usually lower.";
  }

  // Why this run cannot be started, or null. The server decides again on /run; this is so the page
  // can say so before anyone presses anything.
  function whyNot(state, chosen, seed) {
    if (state.status === "running") return "a run is already going";
    if (!Number.isInteger(seed) || seed < 0) return "the track must be a whole number, 0 or more";
    if (!chosen.length) return "choose at least one player";
    const blocked = (state.players || []).filter((p) => chosen.includes(p.name) && p.why_not);
    if (blocked.length) return blocked[0].why_not;
    return null;
  }

  // ---- who the players are ---------------------------------------------------------------------
  // The bakeoff is a grid: a question set (what a player is asked, and the rule its answers go
  // through) crossed with a model (who is asked). Both are ours except the models themselves, and
  // this is the one place the page says what each row and column means.
  const SETS = [
    { key: "composed", title: "Four yes/no questions", says: "Would each move land on a gap? Code picks the move least likely to. One step ahead." },
    { key: "choice", title: "One choice", says: "One question over the four moves, naming the tile each would land on. Code takes its favourite." },
    { key: "two_step", title: "Eight questions, two moves ahead", says: "Each move's landing, and whether it leaves a way on. Code takes the lowest combined risk." },
    { key: "reader", title: "Reads every tile", says: "One question per visible tile (42 of them), then code plans a path through what it read, like the solver." },
    { key: "", title: "One broad question", says: "\u201cWhich move?\u201d, asked once, with no pointed question under it. Kept because it is how this started." },
  ];
  const MODELS = [
    { key: "jev", title: "Jev", says: "TypeSafe\u2019s System One model: answers are probabilities, made in parallel, each blind to the others." },
    { key: "haiku", title: "Claude Haiku", says: "A chat model: it also gets the briefing of the rules, writes every answer in one reply, and states its probabilities as numbers." },
    { key: "glm", title: "GLM Flash", says: "Sent exactly what Claude Haiku is sent, on Zhipu\u2019s free tier, so the model is what differs." },
  ];
  // the players that are not in the grid, and why they are here at all
  const APART = [
    { key: "asked", title: "Asked nothing", says: "The fly is not asked anything: gaps ahead become looming into its eyes and its own neurons steer.",
      players: ["fly"] },
    { key: "yardsticks", title: "Yardsticks, not contestants", says: "What good and bad look like on the same track: a perfect search, a coin, and one that always jumps.",
      players: ["solver", "random", "always_jump"] },
  ];

  // the name of the player at (set, model), or null where there is none
  function playerAt(set, model) {
    if (set === "") return model;                                    // jev, haiku, glm
    if (set === "composed" && model === "jev") return "jev_composed"; // its own class, same questions
    return model + "_" + set;
  }

  // What a cell says under its tick: what it costs, what is left, whether this track was played.
  function notesFor(player) {
    const notes = [];
    if (player.paid) {
      notes.push(player.price_usd > 0 ? usd(player.price_usd) + " a request" : "free tier");
      notes.push((player.requests_left || 0) + " left of the cap");
    } else {
      notes.push("free");
    }
    if (player.played_before) notes.push("played before");  // this track, this game: some answers may be cached
    return notes.join(" \u00b7 ");
  }

  // A cell names the player as the command line does (`jev_composed`), because the row and the column
  // already say what it is asked and who is asked; its tag would only repeat them, and disagree.
  function cell(player, chosen) {
    if (!player) return '<td class="none" aria-label="no such player">\u2014</td>';
    const on = chosen.includes(player.name);
    return '<td><label class="pick' + (player.why_not ? " blocked" : "") + '">' +
      '<input type="checkbox" name="player" value="' + esc(player.name) + '"' + (on ? " checked" : "") +
      (player.why_not ? " disabled" : "") + ">" +
      '<span class="pick-name">' + esc(player.name) + "</span>" +
      '<span class="note">' + esc(notesFor(player)) + "</span>" +
      (player.why_not ? '<span class="note warn">' + esc(player.why_not) + "</span>" : "") +
      "</label></td>";
  }

  // The grid: one row per question set, one column per model, plus the players that are apart.
  // Every player the server offered appears exactly once; anything unexpected joins the yardsticks,
  // so a new player can never be invisible here.
  function playerList(state, chosen) {
    const byName = new Map((state.players || []).map((p) => [p.name, p]));
    const placed = new Set();
    const models = MODELS.filter((m) => SETS.some((s) => byName.has(playerAt(s.key, m.key))));
    let html = '<table class="players"><thead><tr><th class="what"><span class="label">What it is asked</span></th>' +
      models.map((m) => '<th><span class="label">' + esc(m.title) + "</span>" +
        '<span class="note">' + esc(m.says) + "</span></th>").join("") + "</tr></thead><tbody>";
    for (const set of SETS) {
      const cells = models.map((m) => byName.get(playerAt(set.key, m.key)) || null);
      if (!cells.some(Boolean)) continue;
      for (const c of cells) if (c) placed.add(c.name);
      html += '<tr><th class="what"><span class="label">' + esc(set.title) + "</span>" +
        '<span class="note">' + esc(set.says) + "</span></th>" +
        cells.map((c) => cell(c, chosen)).join("") + "</tr>";
    }
    html += "</tbody></table>";

    const groups = APART.map((group) => ({ ...group, found: group.players.map((n) => byName.get(n)).filter(Boolean) }));
    const left = (state.players || []).filter((p) => !placed.has(p.name) &&
      !groups.some((g) => g.found.some((f) => f.name === p.name)));
    if (left.length) groups[groups.length - 1].found = groups[groups.length - 1].found.concat(left);
    for (const group of groups) {
      if (!group.found.length) continue;
      for (const p of group.found) placed.add(p.name);
      html += '<div class="apart"><h4 class="label row-label">' + esc(group.title) + "</h4>" +
        '<p class="note">' + esc(group.says) + "</p><div class=\"picks-row\">" +
        group.found.map((p) => cell(p, chosen).replace(/^<td[^>]*>/, "").replace(/<\/td>$/, "")).join("") + "</div></div>";
    }
    return html;
  }

  // The line under the lobby: the ceiling the command set, and the seed rule.
  function ceilingText(state) {
    const cap = state.max_requests === 0
      ? "This command was started without a cap, so paid players only replay answers that are already cached."
      : "This command's cap is " + state.max_requests + " requests for each paid player, for the whole session.";
    const seeds = state.tournament
      ? "Seeds below " + state.first_practice_seed + " are allowed here (--tournament)."
      : "Paid players may only play seeds " + state.first_practice_seed + " and up; the tournament seeds are kept unseen.";
    return cap + " " + seeds + " Nothing on this page can raise either.";
  }

  // Does starting this run need confirming? Only when it can really spend: a run that has no request
  // left of the cap spends nothing whatever it asks for.
  const spends = (state, chosen) => estimate(state, chosen).lines.some((line) => line.requests > 0);

  const api = { usd, estimate, estimateText, whyNot, playerList, playerAt, SETS, MODELS, APART, ceilingText, spends };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Lobby = api;
})(typeof window !== "undefined" ? window : globalThis);

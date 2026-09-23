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
      (line.played_before ? ", played before (cached answers cost nothing)" : ""));
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

  // One row per player: a checkbox, what it is, and what it would cost.
  function playerList(state, chosen) {
    return (state.players || []).map((player) => {
      const on = chosen.includes(player.name);
      const notes = [];
      if (player.paid) {
        notes.push(player.price_usd > 0 ? usd(player.price_usd) + " a request" : "free tier");
        notes.push((player.requests_left || 0) + " left of the cap");
      } else {
        notes.push("free");
      }
      if (player.played_before) notes.push("played before");
      return '<label class="pick' + (player.why_not ? " blocked" : "") + '">' +
        '<input type="checkbox" name="player" value="' + esc(player.name) + '"' + (on ? " checked" : "") +
        (player.why_not ? " disabled" : "") + ">" +
        '<span class="label tag">' + esc(tagOf(player.name)) + "</span>" +
        '<span class="about">' + esc(player.name) + "</span>" +
        '<span class="note">' + esc(notes.join(" · ")) + "</span>" +
        (player.why_not ? '<span class="note warn">' + esc(player.why_not) + "</span>" : "") +
        "</label>";
    }).join("");
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

  const api = { usd, estimate, estimateText, whyNot, playerList, ceilingText };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Lobby = api;
})(typeof window !== "undefined" ? window : globalThis);

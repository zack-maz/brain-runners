// Who is in the tunnel: it shows and hides the runners, live or replay. Who runs is chosen on the Brain
// Battle character select (select.js).
// Pure and tested under node; app.js does the DOM. Every player name goes through esc().
(function (root) {
  "use strict";

  const Mind = typeof module !== "undefined" && module.exports ? require("./minds.js") : root.Minds;
  const esc = Mind.esc;

  // One button per player of the replay, pressed when its runner is shown. A player that did not run
  // the track in view cannot be shown, so its button is disabled and says so.
  // `players` is every player in the replay, in the replay's own order; `here` those with an episode
  // on the track in view; `shown` those currently in the tunnel; `about` a one-line description each.
  function list(players, here, shown, about) {
    const present = new Set(here);
    return players.map((player) => {
      const on = present.has(player) && shown.has(player);
      const title = (about || {})[player];
      return '<button type="button" class="pick-player" data-player="' + esc(player) + '"' +
        ' aria-pressed="' + on + '"' + (present.has(player) ? "" : " disabled") +
        (title ? ' title="' + esc(title) + '"' : "") + ">" +
        Mind.tagHtml(player) +
        (present.has(player) ? "" : '<span class="note">not on this track</span>') + "</button>";
    }).join("");
  }

  // What the control says under itself, so an empty tunnel is never a mystery.
  function hint(players, here, shown, seed) {
    if (!players.length) return "Nothing has been played yet.";
    if (!here.length) return "No player ran track " + esc(seed) + ".";
    const on = here.filter((p) => shown.has(p)).length;
    if (!on) return "Nobody is in the tunnel: pick a player to show it.";
    return on + " of " + here.length + " shown on track " + esc(seed) + ".";
  }

  // Toggling one player. A player that did not run this track can never be turned on, whatever is
  // clicked, so the tunnel's contents and the level table can never disagree.
  function toggle(shown, here, player) {
    const next = new Set(shown);
    if (next.has(player)) next.delete(player);
    else if (here.includes(player)) next.add(player);
    return next;
  }

  const api = { list, hint, toggle };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Picker = api;
})(typeof window !== "undefined" ? window : globalThis);

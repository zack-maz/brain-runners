// The track select: which track, what it looks like, who has played it, and what the run can cost at worst.
// This is where the lobby's money confirmation lives now (spec section G): the worst case is Lobby.estimate's,
// shown per fighter and in total, and a run that can spend is confirmed once before it starts. Pure and
// tested; the markup is returned as strings and app.js puts it in the page (sprites as empty canvases).
//
// `state` is GET /state?seed= (bakeoff/session.py); `roster` is bakeoff/roster.py's JSON; `players` the
// lineup chosen on the character select, in slot order.
(function (root) {
  "use strict";

  const Minds_ = typeof require !== "undefined" ? require("./minds.js") : root.Minds;
  const Lobby_ = typeof require !== "undefined" ? require("./lobby.js") : root.Lobby;
  const esc = Minds_.esc;

  // The lowest track this command may play: the held-out seeds only with --held-out.
  const lowest = (state) => (state.held_out ? 0 : state.first_practice_seed);

  // A track number the command allows: a whole number, never below the lowest.
  function clampSeed(seed, state) {
    const whole = Math.round(Number(seed));
    return Number.isFinite(whole) ? Math.max(lowest(state), whole) : state.first_practice_seed;
  }

  // Random: a practice track, first_practice_seed to 9999. `rng` is Math.random or a test's stand-in.
  function randomSeed(state, rng) {
    const first = state.first_practice_seed;
    return first + Math.floor(rng() * (10000 - first));
  }

  // The practice tracks the screen offers (1000 to 1019), each with how many of this lineup played it.
  function tiles(state, players, seed) {
    const byName = new Map((state.players || []).map((p) => [p.name, p]));
    const out = [];
    for (let s = state.first_practice_seed; s < state.first_practice_seed + state.practice_tracks; s++) {
      const n = players.filter((name) => ((byName.get(name) || {}).seeds_played || []).includes(s)).length;
      out.push({ seed: s, current: s === seed, mark: n === 0 ? "new" : n + " / " + players.length + " played" });
    }
    return out;
  }

  // One line per fighter: who, whether this track was played before, and its worst case.
  function lineup(state, roster, players) {
    const byName = new Map((state.players || []).map((p) => [p.name, p]));
    const worst = new Map(Lobby_.estimate(state, players).lines.map((line) => [line.player, line]));
    const skinOf = new Map();
    for (const character of roster) for (const skin of character.skins) skinOf.set(skin.player, { character, skin });
    return players.map((name, i) => {
      const found = skinOf.get(name);
      const entry = byName.get(name) || {};
      const line = worst.get(name);
      let cost = "free", requests = found && found.character.id === "fly" ? "simulated" : "";
      if (line) {
        cost = line.free ? "free tier" : Lobby_.usd(line.usd);
        requests = line.requests + (line.requests === 1 ? " request" : " requests");
      }
      return { label: "P" + (i + 1), player: name, title: found ? found.character.name + " · " + found.skin.name : name,
               played: entry.played_before ? "played before" : "new track", cost, requests,
               paid: !!(line && !line.free), why: entry.why_not || null };
    });
  }

  // The whole track as a picture: one column per row, one cell per lane, the gaps dark. The runway (the
  // rows before any gap may fall) is lighter, as in the approved mock-up. An SVG, since 1,800 cells as
  // elements would be slow for no gain.
  function previewSvg(track, game) {
    if (!track) return "";
    const rows = track.max_rows, lanes = track.lanes, cw = 4, ch = 5;
    const runway = (game && game.runway_rows) || 0;
    let cells = '<rect width="' + rows * cw + '" height="' + lanes * ch + '" class="floor"/>';
    if (runway) cells += '<rect width="' + runway * cw + '" height="' + lanes * ch + '" class="runway"/>';
    for (let row = 0; row < rows; row++) {
      for (const lane of track.gaps[row] || []) {
        cells += '<rect x="' + row * cw + '" y="' + lane * ch + '" width="' + cw + '" height="' + ch + '" class="gap"/>';
      }
    }
    return '<svg class="preview" viewBox="0 0 ' + rows * cw + " " + lanes * ch + '" role="img" aria-label="Track ' +
      esc(track.seed) + ", row 0 to " + esc(rows) + '">' + cells + "</svg>";
  }

  // How many gap tiles the track has on its rows.
  function gapTiles(track) {
    if (!track) return 0;
    return track.gaps.slice(0, track.max_rows).reduce((n, row) => n + row.length, 0);
  }

  // The RUN button: what it says, and why it cannot be pressed. `armed`: the worst case was shown on the
  // button and one more press starts the run.
  function runButton(state, players, seed, armed) {
    const why = Lobby_.whyNot(state, players, seed);
    if (why) return { label: "RUN", sub: "", why, armed: false };
    const cost = Lobby_.estimate(state, players);
    if (armed && Lobby_.spends(state, players)) {
      return { label: "CONFIRM", sub: "spend at most " + Lobby_.usd(cost.total_usd), why: null, armed: true };
    }
    return { label: "RUN", sub: "Enter", why: null, armed: false };
  }

  // The line under the total: the cap and what a row costs, from /state, never typed in.
  function capText(state, players) {
    const lines = Lobby_.estimate(state, players).lines;
    if (!lines.length) return "No paid runner: this run spends nothing.";
    const jev = lines.some((l) => l.uncapped), others = lines.some((l) => !l.uncapped);
    const said = "Jev plays without a cap: every row may cost it a request, counted and priced here.";
    if (jev && !others) return said + " Cached answers are free.";
    if (jev && !state.max_requests) {
      return said + " The other paid runners replay answers already cached and stop at their first uncached question.";
    }
    if (jev) {
      return said + " The other paid runners cost " + state.requests_per_row + " request a row each, until their cap of " +
        state.max_requests + " runs out. Cached answers are free, so the real cost is usually lower.";
    }
    if (!state.max_requests) {
      return "This command's cap is 0: the paid runners replay answers already cached and stop at their first " +
        "uncached question, so this run spends nothing.";
    }
    return "Every row costs " + state.requests_per_row + " request for every paid runner, until its cap of " +
      state.max_requests + " runs out. Cached answers are free, so the real cost is usually lower.";
  }

  // A key on the track select: the new seed, and where to go.
  function onKey(seed, state, name, rng) {
    if (name === "ArrowLeft") return { seed: clampSeed(seed - 1, state), go: null };
    if (name === "ArrowRight") return { seed: clampSeed(seed + 1, state), go: null };
    if (name === "r" || name === "R") return { seed: randomSeed(state, rng), go: null };
    if (name === "Enter") return { seed, go: "run" };
    if (name === "Escape") return { seed, go: "back" };
    return null;
  }

  // ---- the markup --------------------------------------------------------------------------------
  function tilesHtml(list) {
    return list.map((t) => '<button type="button" class="tile' + (t.current ? " current" : "") + '" data-seed="' + t.seed +
      '" aria-label="Track ' + t.seed + '"><span class="seed">' + t.seed + '</span><span class="mark">' + esc(t.mark) +
      "</span></button>").join("");
  }

  function lineupHtml(lines) {
    return lines.map((l) => '<div class="fighter"><span class="label who">' + l.label + "</span>" +
      '<span class="art"><canvas class="sprite" data-player="' + esc(l.player) + '" data-px="4"></canvas></span>' +
      '<span class="what"><span class="title">' + esc(l.title) + '</span><span class="sub">' + esc(l.player) + " · " +
      esc(l.played) + "</span>" + (l.why ? '<span class="sub warn">' + esc(l.why) + "</span>" : "") + "</span>" +
      '<span class="cost"><span class="usd' + (l.paid ? " paid" : "") + '">' + esc(l.cost) + '</span><span class="sub">' +
      esc(l.requests) + "</span></span></div>").join("");
  }

  const api = { lowest, clampSeed, randomSeed, tiles, lineup, previewSvg, gapTiles, runButton, capText, onKey, tilesHtml, lineupHtml };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.TrackPick = api;
})(typeof window !== "undefined" ? window : globalThis);

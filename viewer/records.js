// The records screen: the leaderboard, the head to head, and the past runs. Every number is `bakeoff
// bench`'s, worked out by bakeoff/records.py (GET /records); this file only orders, words and draws them. Pure
// and tested; the markup is returned as strings.
//
// `records` is {game, max_rows, tracks, bench: {players, pairs, notes} | null, why, left_out, unreadable, runs,
// tuned_on, ours}; `roster` is bakeoff/roster.py's JSON.
(function (root) {
  "use strict";

  const Minds_ = typeof require !== "undefined" ? require("./minds.js") : root.Minds;
  const esc = Minds_.esc;

  const SHOWN_RUNS = 10; // past runs listed before "Show all"
  const DARK = "#1E2227"; // a skin this dark needs an edge to be seen on the page (the Map skins' black)

  function skinOf(roster, player) {
    for (const character of roster || []) {
      for (const skin of character.skins) if (skin.player === player) return { character, skin };
    }
    return null;
  }
  const labelOf = (roster, player) => {
    const found = skinOf(roster, player);
    return found ? found.character.name + " · " + found.skin.name : player;
  };
  // the yardsticks are the Bot's skins: shown for scale, greyed, never ranked
  const isYardstick = (roster, player) => {
    const found = skinOf(roster, player);
    return !!found && found.character.id === "bot";
  };

  // Did this player's frozen numbers come from the tracks ranked here? (fly2 was tuned on 1000 to 1199.)
  function tunedHere(records, player) {
    const on = (records.tuned_on || {})[player];
    const tracks = records.tracks || [];
    return !!on && tracks.length === 2 && on[0] <= tracks[1] && on[1] >= tracks[0];
  }

  // The leaderboard, in bench's order: ranked players first by mean rows, then those with too few tracks
  // for an interval. Only a ranked non-yardstick gets a place number.
  function board(records, roster) {
    const players = (records.bench && records.bench.players) || [];
    const max = records.max_rows || 1;
    const pct = (x) => Math.max(0, Math.min(100, (x / max) * 100));
    let place = 0;
    return players.map((p) => {
      const yardstick = isYardstick(roster, p.player);
      const ranked = p.ranked && !yardstick;
      if (ranked) place += 1;
      const found = skinOf(roster, p.player);
      const colour = found ? found.skin.color : "#3A4046";
      const edge = colour === DARK && found ? Object.values(found.skin.inks)[0] || "#2A2F35" : null;
      return {
        player: p.player, rank: ranked ? String(place) : "", name: labelOf(roster, p.player) + (yardstick ? " (yardstick)" : ""),
        yardstick, tracks: p.seeds + (p.seeds === 1 ? " track" : " tracks"), colour, edge,
        lo: pct(p.ci_low == null ? p.mean_rows : p.ci_low), span: p.ci_low == null ? 0 : pct(p.ci_high) - pct(p.ci_low),
        mean: pct(p.mean_rows), value: p.ci_low == null ? "not ranked" : p.mean_rows.toFixed(1),
        tuned: tunedHere(records, p.player),
      };
    });
  }

  // The notes under the leaderboard: that its order is no verdict, which rows are in-sample, what was left out.
  function boardNotes(records, roster) {
    const rows = board(records, roster).filter((r) => !r.yardstick);
    const notes = [];
    if (rows.length) {
      const counts = rows.map((r) => Number.parseInt(r.tracks, 10));
      const common = counts.slice().sort((a, b) => counts.filter((c) => c === b).length - counts.filter((c) => c === a).length)[0];
      notes.push("Most players have " + common + (common === 1 ? " track" : " tracks") + ": their intervals overlap, so this " +
        "order is not a verdict. Pick a pair to see what the numbers can tell apart.");
    }
    for (const r of rows.filter((x) => x.tuned)) {
      const on = records.tuned_on[r.player];
      notes.push(labelOf(roster, r.player) + "'s numbers were tuned on tracks " + on[0] + "–" + on[1] +
        ", these tracks included: its mean here is in-sample.");
    }
    if (records.left_out) {
      notes.push(records.left_out + " older " + (records.left_out === 1 ? "copy" : "copies") + " of a track left out: each " +
        "player's track counts once, from its newest run.");
    }
    if ((records.unreadable || []).length) {
      notes.push("Could not be read, so not counted: " + records.unreadable.join(", ") + ".");
    }
    return notes;
  }

  // The pair from bench's list, whichever way round it was asked for: (a, b) or (b, a) with the sign flipped.
  function pairOf(records, a, b) {
    const pairs = (records.bench && records.bench.pairs) || [];
    const found = pairs.find((p) => p.a === a && p.b === b);
    if (found) return found;
    const turned = pairs.find((p) => p.a === b && p.b === a);
    if (!turned) return null;
    // the verdict names its player ("jev_step2 ahead"), so it reads the same whichever way round
    const flip = (x) => (x == null ? null : -x);
    return { ...turned, a, b, mean_diff: flip(turned.mean_diff), ci_low: flip(turned.ci_high), ci_high: flip(turned.ci_low),
             wins: turned.losses, losses: turned.wins };
  }

  // Up to six pairs to offer as chips: among the players ranked here (no yardsticks), the pairs with a verdict
  // first, then the ones with the most tracks in common, then the largest differences.
  function chips(records, roster) {
    const ranked = new Set(board(records, roster).filter((r) => r.rank).map((r) => r.player));
    const pairs = ((records.bench && records.bench.pairs) || []).filter((p) => ranked.has(p.a) && ranked.has(p.b));
    const clear = (p) => p.verdict.endsWith(" ahead");
    return pairs.slice().sort((x, y) => (clear(y) - clear(x)) || (y.common_seeds - x.common_seeds) ||
      (Math.abs(y.mean_diff || 0) - Math.abs(x.mean_diff || 0))).slice(0, 6)
      .map((p) => ({ a: p.a, b: p.b, label: labelOf(roster, p.a) + " vs " + labelOf(roster, p.b) }));
  }

  // One pair, as the head to head shows it. The axis runs from the whole track behind to the whole track ahead.
  function pairView(pair, roster, maxRows) {
    const R = maxRows || 150;
    const ax = (x) => ((Math.max(-R, Math.min(R, x)) + R) / (2 * R)) * 100;
    const a = labelOf(roster, pair.a), b = labelOf(roster, pair.b);
    const tell = pair.verdict.endsWith(" ahead");
    const sign = (x) => (x >= 0 ? "+" : "") + x.toFixed(1);
    return {
      a, b, tracks: pair.common_seeds, diff: pair.mean_diff == null ? "-" : sign(pair.mean_diff),
      lo: pair.ci_low == null ? null : ax(pair.ci_low), span: pair.ci_low == null ? 0 : ax(pair.ci_high) - ax(pair.ci_low),
      mean: pair.mean_diff == null ? null : ax(pair.mean_diff),
      interval: pair.ci_low == null ? "-" : pair.ci_low.toFixed(1) + " to " + pair.ci_high.toFixed(1),
      wtl: pair.wins + " / " + pair.ties + " / " + pair.losses,
      needed: pair.seeds_needed == null ? "-" : "about " + pair.seeds_needed,
      verdict: pair.verdict.replace(pair.a + " ahead", a + " ahead").replace(pair.b + " ahead", b + " ahead"), tell,
      note: tell ? "The interval stays clear of 0 on the tracks both played."
        : pair.ci_low == null ? "Too few tracks in common for an interval."
          : "The interval crosses 0: on these tracks either could be ahead.",
    };
  }

  // When a run started, as the list says it: "25 Sep 16:39", in the viewer's own time zone.
  function when(iso) {
    const d = new Date(iso);
    if (!iso || Number.isNaN(d.getTime())) return "-";
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const two = (n) => String(n).padStart(2, "0");
    return d.getDate() + " " + months[d.getMonth()] + " " + two(d.getHours()) + ":" + two(d.getMinutes());
  }

  function tracksText(seeds) {
    if (!seeds.length) return "-";
    if (seeds.length === 1) return String(seeds[0]);
    return Math.min(...seeds) + "–" + Math.max(...seeds) + " (" + seeds.length + ")";
  }

  // "Jev · Step 1, Guided; Fly · Looming": each character once, its skins after it, in the run's own order.
  function playersText(roster, players) {
    const groups = [];
    for (const player of players) {
      const found = skinOf(roster, player);
      const name = found ? found.character.name : player;
      const group = groups.find((g) => g.name === name);
      if (group) { if (found) group.skins.push(found.skin.name); } else groups.push({ name, skins: found ? [found.skin.name] : [] });
    }
    return groups.map((g) => g.name + (g.skins.length ? " · " + g.skins.join(", ") : "")).join("; ");
  }

  const STATUS = { completed: ["completed", "ok"], interrupted: ["interrupted", "warn"], budget_exhausted: ["budget used up", "warn"],
                   aborted: ["aborted", "warn"], crashed: ["crashed", "bad"] };

  // The past runs, newest first: the first ten unless all are asked for. Only this session's run pulses and
  // can be watched live; another run whose meta.json says running is not this page's to stream.
  function pastRuns(records, roster, all) {
    const runs = records.runs || [];
    return { total: runs.length, rows: (all ? runs : runs.slice(0, SHOWN_RUNS)).map((r) => {
      let status = STATUS[r.status] || [r.status || "status unknown", "warn"];
      if (r.status === "running") status = r.current ? ["running now", "live"] : ["running elsewhere, or stopped without closing", "warn"];
      return { run_id: r.run_id, when: when(r.started_at), tracks: tracksText(r.seeds), players: playersText(roster, r.players),
               status: status[0], kind: status[1], watch: r.current ? "Watch live" : "Watch" };
    }) };
  }

  // ---- the markup --------------------------------------------------------------------------------
  function boardHtml(rows, chosen) {
    return rows.map((r) => '<button type="button" class="entry' + (r.yardstick ? " yardstick" : "") +
      (chosen.includes(r.player) ? " chosen" : "") + '" data-player="' + esc(r.player) + '">' +
      '<span class="rank">' + esc(r.rank) + '</span><span class="swatch" style="background:' + esc(r.colour) +
      (r.edge ? ";box-shadow:inset 0 0 0 1px " + esc(r.edge) : "") + '"></span><span class="name">' + esc(r.name) +
      (r.tuned ? ' <span class="warn">tuned on these tracks</span>' : "") + '</span><span class="tracks">' + esc(r.tracks) +
      '</span><span class="band"><span class="ci" style="left:' + r.lo.toFixed(2) + "%;width:" + r.span.toFixed(2) + '%"></span>' +
      '<span class="mean" style="left:calc(' + r.mean.toFixed(2) + '% - 1px)"></span></span><span class="value">' + esc(r.value) +
      "</span></button>").join("");
  }

  function chipsHtml(list, a, b) {
    return list.map((c) => '<button type="button" class="chip' + (c.a === a && c.b === b ? " on" : "") + '" data-a="' + esc(c.a) +
      '" data-b="' + esc(c.b) + '">' + esc(c.label) + "</button>").join("");
  }

  function pairHtml(v) {
    return '<div class="vs"><span class="who">' + esc(v.a) + '</span><span class="label">VS</span><span class="who">' + esc(v.b) +
      '</span></div><div class="diff"><span class="n">' + esc(v.diff) + "</span><span>rows a track, on " + esc(v.tracks) +
      " tracks both played</span></div>" +
      '<div class="axis"><span class="zero"></span>' +
      (v.lo == null ? "" : '<span class="ci' + (v.tell ? " tell" : "") + '" style="left:' + v.lo.toFixed(2) + "%;width:" + v.span.toFixed(2) + '%"></span>') +
      (v.mean == null ? "" : '<span class="mean" style="left:calc(' + v.mean.toFixed(2) + '% - 1px)"></span>') + "</div>" +
      '<div class="axis-labels"><span>' + esc(v.b) + " ahead</span><span>0</span><span>" + esc(v.a) + " ahead</span></div>" +
      '<div class="stats"><span><span class="label">95% interval</span>' + esc(v.interval) + '</span><span><span class="label">' +
      "Wins / ties / losses</span>" + esc(v.wtl) + '</span><span><span class="label">Tracks for a verdict</span>' + esc(v.needed) +
      '</span></div><div class="verdict' + (v.tell ? " tell" : "") + '"><span class="word">' + esc(v.verdict) + '</span><span class="note">' +
      esc(v.note) + "</span></div>";
  }

  function runsHtml(list) {
    return list.map((r) => '<div class="past"><span class="when">' + esc(r.when) + '</span><span>' + esc(r.tracks) + "</span>" +
      '<span class="players">' + esc(r.players) + '</span><span class="label status ' + r.kind + '">' + esc(r.status) + "</span>" +
      '<span class="actions"><button type="button" data-watch="' + esc(r.run_id) + '"' + (r.watch === "Watch live" ? ' data-live="true"' : "") +
      ">" + esc(r.watch) + '</button><button type="button" data-results="' + esc(r.run_id) + '">Results</button></span></div>').join("");
  }

  const api = { SHOWN_RUNS, tunedHere, board, boardNotes, pairOf, chips, pairView, when, tracksText, playersText, pastRuns,
                boardHtml, chipsHtml, pairHtml, runsHtml };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Records = api;
})(typeof window !== "undefined" ? window : globalThis);

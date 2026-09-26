// The results screen: a card per fighter ranked by rows survived, a bar each against the track's length,
// and More numbers. Every number comes from bakeoff/results.py (the end event, or GET /results); this file
// only ranks and words them. Pure and tested; the markup is returned as strings (sprites as empty canvases).
// No winner banner: one track is not a result, and the screen says so.
(function (root) {
  "use strict";

  const Minds_ = typeof require !== "undefined" ? require("./minds.js") : root.Minds;
  const Lobby_ = typeof require !== "undefined" ? require("./lobby.js") : root.Lobby;
  const esc = Minds_.esc;

  const DEATHS = { ran_into_gap: "Ran into a gap", jumped_into_gap: "Jumped into a gap", dodged_into_gap: "Dodged into a gap" };

  const labelOf = (roster, player) => {
    for (const character of roster || []) {
      for (const skin of character.skins) if (skin.player === player) return character.name + " · " + skin.name;
    }
    return player;
  };
  const isFly = (roster, player) => (roster || []).some((c) => c.id === "fly" && c.skins.some((s) => s.player === player));

  // A share as the page writes it: one decimal below 10%, none above.
  function percent(share) {
    if (share == null) return "-";
    const p = share * 100;
    return (p > 0 && p < 10 ? p.toFixed(1) : Math.round(p)) + "%";
  }

  // Seconds a row as the page writes it.
  function perRow(seconds) {
    if (seconds == null) return "-";
    return seconds < 1 ? Math.round(seconds * 1000) + " ms" : seconds.toFixed(1) + " s";
  }

  // How far an entry got, for the ranking: on one track its rows (a stopped runner counts below every
  // complete one), over several its mean over the complete tracks.
  function score(entry, single) {
    if (single) {
      const track = entry.tracks[0];
      return track ? { value: track.rows, stopped: !track.complete } : { value: -1, stopped: true };
    }
    return { value: entry.mean_rows == null ? -1 : entry.mean_rows, stopped: entry.mean_rows == null };
  }

  // The fighters in rank order, each with its place. Ties share a place (two finishers are both 1st); a
  // stopped runner comes after every one that finished or fell, and is never ranked above one.
  function rank(results) {
    const single = (results.seeds || []).length <= 1;
    const scored = results.players.map((entry, slot) => ({ entry, slot, ...score(entry, single) }));
    scored.sort((a, b) => (a.stopped - b.stopped) || (b.value - a.value) || (a.slot - b.slot));
    let place = 0;
    return scored.map((s, i) => {
      const prev = scored[i - 1];
      if (!prev || prev.stopped !== s.stopped || prev.value !== s.value) place = i + 1;
      return { ...s, place };
    });
  }

  // How a fighter's run ended, in words.
  function death(entry, single) {
    if (single) {
      const track = entry.tracks[0];
      if (!track) return "Never started";
      if (!track.complete) return "Stopped at row " + track.rows + ": not a death";
      if (track.finished) return "Reached the finish line";
      return (DEATHS[track.death_cause] || "Fell") + " · row " + track.rows;
    }
    const causes = Object.keys(DEATHS).filter((c) => entry[c] > 0).map((c) => entry[c] + " " + DEATHS[c].toLowerCase());
    const parts = [];
    if (entry.finished) parts.push(entry.finished + " finished");
    if (causes.length) parts.push(causes.join(", "));
    if (entry.incomplete) parts.push(entry.incomplete + " stopped");
    return parts.join(" · ") || "No complete track";
  }

  function requestsText(entry, roster) {
    if (!entry.paid) return isFly(roster, entry.player) ? "none (simulated)" : "none";
    return String(entry.requests);
  }

  function costText(entry) {
    if (!entry.paid) return "free";
    if (!(entry.price_usd > 0)) return "free tier";
    return Lobby_.usd(entry.cost_estimate_usd);
  }

  // The wrong moves, as More numbers says them: the count, and the fatal one named with what was safe.
  function wrongText(entry, single) {
    const count = String(entry.wrong_moves);
    const track = single ? entry.tracks[0] : null;
    if (track && track.fatal) {
      return count + " · fatal, row " + track.fatal.row + ": " + track.fatal.move + " (" + track.fatal.safe.join(" or ") + " safe)";
    }
    if (track && track.trapped) return count + " · trapped at the end: no move there was safe";
    if (!single && entry.fatal_wrong_moves) return count + " · " + entry.fatal_wrong_moves + " fatal";
    return count;
  }

  function header(results) {
    const seeds = results.seeds || [];
    const n = results.players.length;
    const ended = results.status === "completed" ? "Run ended" : "Run " + (results.status || "ended");
    const where = seeds.length <= 1 ? "Track " + seeds[0]
      : "Tracks " + Math.min(...seeds) + "–" + Math.max(...seeds) + " (" + seeds.length + ")";
    return { left: ended + " · " + n + (n === 1 ? " fighter" : " fighters"),
             right: where + " · game " + results.game.version + " · " + results.game.max_rows + " rows" };
  }

  // The cards, in rank order.
  function cards(results, roster) {
    const single = (results.seeds || []).length <= 1;
    const slotOf = new Map(results.players.map((e, i) => [e.player, i]));
    return rank(results).map((r) => ({
      place: r.place, top: r.place === 1 && !r.stopped, label: "P" + (slotOf.get(r.entry.player) + 1), player: r.entry.player,
      title: labelOf(roster, r.entry.player),
      rows: single ? (r.entry.tracks[0] ? r.entry.tracks[0].rows : 0) : (r.entry.mean_rows == null ? "-" : r.entry.mean_rows.toFixed(1)),
      rowsWord: single ? "rows" : "rows a track", death: death(r.entry, single), stopped: r.stopped,
      // over several tracks: every complete track finished (a complete track that did not finish is a death)
      finished: single ? !!(r.entry.tracks[0] && r.entry.tracks[0].finished) : r.entry.runs > 0 && r.entry.finished === r.entry.runs,
      perRow: perRow(r.entry.s_per_row), requests: requestsText(r.entry, roster), cost: costText(r.entry),
      paid: !!(r.entry.paid && r.entry.price_usd > 0),
    }));
  }

  // One bar per fighter against the track's length, and the solver's line, which is the whole track (every
  // track can be finished), unless the solver ran.
  function bars(results, roster) {
    const max = results.game.max_rows;
    const single = (results.seeds || []).length <= 1;
    const out = rank(results).map((r) => {
      const rows = single ? (r.entry.tracks[0] ? r.entry.tracks[0].rows : 0) : (r.entry.mean_rows || 0);
      return { player: r.entry.player, name: labelOf(roster, r.entry.player), rows, width: max ? rows / max : 0, yardstick: false };
    });
    if (!results.players.some((e) => e.player === "solver")) {
      out.push({ player: "solver", name: "Solver (yardstick)", rows: max, width: 1, yardstick: true });
    }
    return out;
  }

  // The warning that one track is not a result, with the two best numbers in it.
  function warning(results, roster) {
    const single = (results.seeds || []).length <= 1;
    const ranked = cards(results, roster).filter((c) => !c.stopped);
    if (!single) return "A few tracks are not a result either. Records holds the benchmark over many tracks.";
    if (ranked.length < 2) return "One track is not a result. Records holds the benchmark over many tracks.";
    return "One track is not a result: " + ranked[0].rows + " against " + ranked[1].rows +
      " rows can be this track's luck. Records holds the benchmark over many tracks.";
  }

  // More numbers: one row per number, one column per fighter in rank order.
  function table(results, roster) {
    const single = (results.seeds || []).length <= 1;
    const order = rank(results).map((r) => r.entry);
    const col = (fn) => order.map(fn);
    return {
      heads: order.map((e) => labelOf(roster, e.player)),
      rows: [
        { name: "Rows survived", hint: single ? "of " + results.game.max_rows : "mean, of " + results.game.max_rows,
          vals: col((e) => (single ? (e.tracks[0] ? String(e.tracks[0].rows) : "-") : (e.mean_rows == null ? "-" : e.mean_rows.toFixed(1)))) },
        { name: "Death", hint: "", vals: col((e) => death(e, single)) },
        { name: "Moves that were jumps", hint: "", vals: col((e) => percent(e.jump_share)) },
        { name: "Wrong moves", hint: "worse than the best", vals: col((e) => wrongText(e, single)) },
        { name: "Asked live", hint: "requests", vals: col((e) => requestsText(e, roster)) },
        { name: "From cache", hint: "replayed, free", vals: col((e) => (e.paid ? String(e.cache_hits) : "none")) },
        { name: "Time per row", hint: "mean", vals: col((e) => perRow(e.s_per_row)) },
        { name: "Tokens", hint: "in / out", vals: col((e) => (e.requests ? e.input_tokens.toLocaleString("en-US") + " / " +
          e.output_tokens.toLocaleString("en-US") : "none")) },
        { name: "Cost", hint: "estimate", vals: col(costText) },
      ],
    };
  }

  // Failed or unreadable answers, only when there were any: one line per fighter that had them.
  function failures(results, roster) {
    return results.players.filter((e) => e.fallback_rate > 0).map((e) => labelOf(roster, e.player) + ": " +
      percent(e.fallback_rate) + " of its rows fell back to the default move (errors " + percent(e.error_rate) +
      ", unreadable answers " + percent(e.invalid_rate) + ").");
  }

  // The note under More numbers: what is left out and why, and what is ours, from this lineup.
  function note(results, roster) {
    const parts = ["Probability scores are left out; the benchmark in Records has none either."];
    if (results.players.some((e) => isFly(roster, e.player))) {
      parts.push("The fly is asked nothing; how gaps become its input is ours.");
    }
    if (results.players.some((e) => e.paid && e.price_usd > 0)) {
      parts.push("Costs are live requests times the page's price per request: an estimate, not a bill.");
    }
    return parts.join(" ");
  }

  // ---- the markup --------------------------------------------------------------------------------
  function cardsHtml(list, more) {
    // a finish is not a death: only a fall is --bad, and a stopped run is --warn
    return list.map((c, i) => '<article class="card' + (c.top ? " leader" : "") + (c.stopped ? " stopped" : "") + '" style="animation-delay:' +
      i * 90 + 'ms"><div class="card-top"><span class="place">' + c.place + '</span><span class="label who">' + esc(c.label) +
      "</span></div>" + (more ? "" : '<div class="art"><canvas class="sprite" data-player="' + esc(c.player) + '" data-px="11"></canvas></div>') +
      '<span class="title">' + esc(c.title) + '</span><span class="player">' + esc(c.player) + "</span>" +
      '<div class="rows"><span class="n">' + esc(c.rows) + '</span><span class="word">' + esc(c.rowsWord) + '</span><span class="death' +
      (c.stopped ? " warn" : c.finished ? "" : " bad") + '">' + esc(c.death) + "</span></div>" +
      '<div class="stats"><span><span class="label">Per row</span>' + esc(c.perRow) + '</span><span><span class="label">Requests</span>' +
      esc(c.requests) + '</span><span><span class="label">Cost</span><span class="' + (c.paid ? "warn" : "muted") + '">' + esc(c.cost) +
      "</span></span></div></article>").join("");
  }

  function barsHtml(list, colourOf) {
    return list.map((b) => '<div class="result-bar' + (b.yardstick ? " yardstick" : "") + '"><span class="name">' + esc(b.name) + "</span>" +
      '<span class="track"><span class="fill" style="width:' + (b.width * 100).toFixed(2) + "%" +
      (b.yardstick ? "" : ";background:" + esc(colourOf(b.player) || "#3A4046")) + '"></span></span>' +
      '<span class="n">' + esc(typeof b.rows === "number" && !Number.isInteger(b.rows) ? b.rows.toFixed(1) : b.rows) + "</span></div>").join("");
  }

  function tableHtml(t) {
    return '<table class="numbers"><thead><tr><th></th>' + t.heads.map((h) => "<th>" + esc(h) + "</th>").join("") +
      "</tr></thead><tbody>" + t.rows.map((r) => '<tr><th>' + esc(r.name) + (r.hint ? ' <span class="muted">' + esc(r.hint) + "</span>" : "") +
      "</th>" + r.vals.map((v) => "<td>" + esc(v) + "</td>").join("") + "</tr>").join("") + "</tbody></table>";
  }

  const api = { percent, perRow, rank, death, wrongText, header, cards, bars, warning, table, failures, note, cardsHtml, barsHtml, tableHtml };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Results = api;
})(typeof window !== "undefined" ? window : globalThis);

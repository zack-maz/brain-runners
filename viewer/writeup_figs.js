// The Writeup's figures (decisions 62, 63): every `<figure data-fig="KEY">` of docs/WRITEUP.html is an empty slot this
// fills from the study's numbers, `{players, pairs, notes}` (docs/STUDY.json, or bakeoff.writeup.study_of's answer
// in Brain Runners). One code for both hosts: Brain Runners' Writeup screen and motg.dev/runners. Click a player in
// any figure to follow it (blue marks that one player everywhere); the chips of Fig. 3 pick the question set. It
// loads nothing and escapes every text it puts in the page. The builders are pure and tested; `mount` is the glue.
(function (root) {
  "use strict";

  // what the figures read, and all docs/STUDY.json holds (bakeoff/writeup.py's STUDY_PLAYER_FIELDS and
  // STUDY_PAIR_FIELDS; a test keeps the three equal)
  const PLAYER_FIELDS = ["player", "seeds", "mean_rows", "ci_low", "ci_high", "median_rows", "finished",
    "usd_per_track", "cost_basis", "s_per_decision_median", "rows_per_cent", "rows_per_second", "failed_rate",
    "ranked", "yardstick", "frontier_cost", "frontier_speed"];
  const PAIR_FIELDS = ["a", "b", "common_seeds", "mean_diff", "ci_low", "ci_high", "wins", "ties", "losses",
    "mean_a_shared", "mean_b_shared"];
  // the slots this draws
  const KEYS = ["leaderboard", "rows", "rows-ci", "jev-vs-haiku", "finished", "cost-time", "scores"];
  const MAX = 150;
  const FIRST_FOCUS = "jev_step2";

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  const WHO = { jev: "Jev", haiku: "Claude Haiku", glm: "GLM Flash" };
  const SETS = { plain: "plain", guided: "guided", step1: "step-1", step2: "step-2", map: "map" };
  const NAMED = { fly: "Fly · looming", fly2: "Fly · sideways", solver: "Bot · Solver", random: "Bot · Random",
    always_jump: "Bot · Always jump" };
  function nameOf(id) {
    if (NAMED[id]) return NAMED[id];
    const at = String(id).indexOf("_");
    const who = WHO[String(id).slice(0, at)], set = SETS[String(id).slice(at + 1)];
    return at > 0 && who && set ? who + " · " + set : String(id);
  }

  const fmt = {
    rows: (v) => (v == null ? "–" : Number(v).toFixed(1)),
    pct: (v) => (v == null ? "–" : Math.round(v * 100) + "%"),
    secs: (v) => (v == null ? "–" : Number(v).toFixed(2) + " s"),
    usd: (p) => (p.cost_basis === "free" || !p.usd_per_track ? "free"
      : "$" + (p.usd_per_track < 0.01 ? p.usd_per_track.toFixed(4) : p.usd_per_track.toFixed(2)) +
        (p.cost_basis === "estimate" ? " (est.)" : "")),
    score: (v) => (v == null ? "–" : v >= 100 ? String(Math.round(v)) : Number(v).toPrecision(3)),
  };

  // ---- the numbers each figure shows ---------------------------------------------------------------
  function byMean(study) {
    return (study.players || []).slice().sort((a, b) => b.mean_rows - a.mean_rows);
  }
  function bestOf(study, prefix) {
    return byMean(study).find((p) => p.player.startsWith(prefix)) || null;
  }

  // Fig. 1: the reference, the best of each mind and chance, as [{player, note}]
  function glance(study) {
    const has = (id) => (study.players || []).find((p) => p.player === id);
    return [
      has("solver") && { p: has("solver"), note: "reference" },
      bestOf(study, "jev_") && { p: bestOf(study, "jev_"), note: "best Jev" },
      bestOf(study, "haiku_") && { p: bestOf(study, "haiku_"), note: "best Claude Haiku" },
      bestOf(study, "fly") && { p: bestOf(study, "fly"), note: "best fly" },
      has("random") && { p: has("random"), note: "chance" },
    ].filter(Boolean);
  }

  // Fig. 3: the twins in the study's order, each named by its set, and who led on the tracks both ran
  function pairsOf(study) {
    return (study.pairs || []).map((q) => ({ ...q, set: q.a.slice(q.a.indexOf("_") + 1) }));
  }
  function leadOf(q) {
    const jevLeads = q.mean_diff >= 0;
    return { leader: jevLeads ? q.a : q.b, other: jevLeads ? q.b : q.a, by: Math.abs(q.mean_diff),
      leaderMean: jevLeads ? q.mean_a_shared : q.mean_b_shared, otherMean: jevLeads ? q.mean_b_shared : q.mean_a_shared,
      leaderWins: jevLeads ? q.wins : q.losses };
  }

  // the player in focus: the one asked for when it is in the study, otherwise Jev · step-2, otherwise the best mind
  function focusOf(study, wanted) {
    const players = study.players || [];
    if (players.some((p) => p.player === wanted)) return wanted;
    if (players.some((p) => p.player === FIRST_FOCUS)) return FIRST_FOCUS;
    const mind = byMean(study).find((p) => !p.yardstick);
    return mind ? mind.player : null;
  }
  function setOf(study, wanted) {
    const pairs = pairsOf(study);
    return (pairs.find((q) => q.set === wanted) || pairs[0] || {}).set || null;
  }

  // ---- the figures, as HTML ------------------------------------------------------------------------
  const focusClass = (p, focus) => (p.player === focus ? " focus" : "") + (p.yardstick ? " bot" : "");
  const pressed = (p, focus) => 'aria-pressed="' + (p.player === focus) + '"';

  // The leaderboard, as at the end of a Mario Kart race: the three best minds on a podium (2nd, 1st, 3rd from the
  // left), then everyone else in order. The bots are not racing: they sit in the list at their place, unnumbered,
  // for scale.
  function ordinal(n) {
    const teen = n % 100 >= 11 && n % 100 <= 13;
    return n + (teen ? "th" : ["th", "st", "nd", "rd"][n % 10] || "th");
  }
  function standings(study) {
    let place = 0;
    return byMean(study).map((p) => ({ p, place: p.yardstick ? null : ++place }));
  }
  function leaderboardHtml(study, focus) {
    const all = standings(study);
    const top = all.filter((s) => s.place && s.place <= 3);
    const step = ({ p, place }) =>
      '<button type="button" class="wf-step wf-place-' + place + focusClass(p, focus) + '" data-player="' + esc(p.player) + '" ' + pressed(p, focus) + ">" +
      '<span class="wf-who">' + esc(nameOf(p.player)) + "</span>" +
      '<span class="wf-n">' + fmt.rows(p.mean_rows) + '<span class="wf-of"> / ' + MAX + "</span></span>" +
      '<span class="wf-block"><span class="wf-pos">' + ordinal(place) + "</span></span></button>";
    const podium = [top[1], top[0], top[2]].filter(Boolean).map(step).join("");
    const rest = all.filter((s) => !(s.place && s.place <= 3)).map(({ p, place }) =>
      '<li><button type="button" class="wf-standing' + focusClass(p, focus) + '" data-player="' + esc(p.player) + '" ' + pressed(p, focus) + ">" +
      '<span class="wf-pos">' + (place ? ordinal(place) : "–") + "</span>" +
      '<span class="wf-who">' + esc(nameOf(p.player)) + (p.yardstick ? ' <span class="wf-tag">bot, for scale</span>' : "") + "</span>" +
      '<span class="wf-tracks">' + p.seeds + '<span class="wf-unit"> tracks</span></span>'  +
      '<span class="wf-n">' + fmt.rows(p.mean_rows) + "</span></button></li>").join("");
    return '<div class="wf-podium">' + podium + "</div>" + '<ol class="wf-standings">' + rest + "</ol>";
  }

  function rowsHtml(study, focus) {
    return '<div class="wf-glance">' + glance(study).map(({ p, note }) =>
      '<button type="button" class="wf-tile' + focusClass(p, focus) + '" data-player="' + esc(p.player) + '" ' + pressed(p, focus) + ">" +
      '<span class="label">' + esc(nameOf(p.player)) + '</span><span class="wf-big">' + fmt.rows(p.mean_rows) + "</span>" +
      '<span class="wf-who">' + esc(note) + "</span></button>").join("") + "</div>";
  }

  function boardHtml(study, focus) {
    const x = (v) => (Math.max(0, Math.min(MAX, v)) / MAX) * 100;
    const rows = byMean(study).map((p) =>
      '<button type="button" class="wf-row' + focusClass(p, focus) + '" data-player="' + esc(p.player) + '" ' + pressed(p, focus) + ">" +
      '<span class="wf-who">' + esc(nameOf(p.player)) + "</span>" +
      '<span class="wf-bar"><span class="wf-track"></span>' +
      (p.ci_low != null ? '<span class="wf-ci" style="left:' + x(p.ci_low) + "%;width:" + (x(p.ci_high) - x(p.ci_low)) + '%"></span>' : "") +
      '<span class="wf-mean" style="left:' + x(p.mean_rows) + '%"></span></span>' +
      '<span class="wf-n">' + fmt.rows(p.mean_rows) + "</span></button>").join("");
    const ticks = [0, 50, 100, 150].map((t) => '<span style="left:' + (t / MAX) * 100 + '%">' + t + "</span>").join("");
    return '<div class="wf-fig-head"><span class="label">Mean rows · 95% interval</span><span class="label">click a player to follow it</span></div>' +
      '<div class="wf-board">' + rows + "</div>" +
      '<div class="wf-axis"><span></span><div class="wf-ticks">' + ticks + "</div><span></span></div>" +
      '<div class="wf-axis"><span></span><span class="wf-axis-title">mean rows survived (of 150)</span><span></span></div>';
  }

  function pairHtml(study, set) {
    const pairs = pairsOf(study);
    const q = pairs.find((r) => r.set === set);
    if (!q) return '<p class="why">No Jev and Claude Haiku pair in these numbers.</p>';
    const chips = '<div class="wf-chips" role="group" aria-label="Question set">' + pairs.map((r) =>
      '<button type="button" class="wf-chip" data-set="' + esc(r.set) + '" aria-pressed="' + (r.set === set) + '">' +
      esc(SETS[r.set] || r.set) + "</button>").join("") + "</div>";
    const l = leadOf(q), n = q.common_seeds;
    const bar = (id, v, lead) => '<div class="wf-duel-row' + (lead ? " lead" : "") + '"><span class="wf-who">' + esc(nameOf(id)) + "</span>" +
      '<span class="wf-bar"><span class="wf-fill" style="width:' + (Math.max(0, Math.min(MAX, v)) / MAX) * 100 + '%"></span></span>' +
      '<span class="wf-n">' + fmt.rows(v) + "</span></div>";
    const cells = [].concat(Array(q.wins).fill("ahead"), Array(q.ties).fill("tied"), Array(q.losses).fill("behind"))
      .map((k) => '<i class="' + k + '"></i>').join("");
    const interval = q.ci_low == null ? "" : '<span class="label">95% interval of the difference: ' +
      fmt.rows(Math.abs(l.leader === q.a ? q.ci_low : q.ci_high)) + " to " + fmt.rows(Math.abs(l.leader === q.a ? q.ci_high : q.ci_low)) + " rows</span>";
    return chips + '<div class="wf-pair">' +
      '<p class="wf-verdict">' + esc(nameOf(l.leader)) + ' ran <span class="num">' + fmt.rows(l.by) + "</span> rows further than " +
      esc(nameOf(l.other)) + "</p>" + interval +
      '<div class="wf-duel"><span class="label">average rows on the ' + n + " tracks both ran</span>" +
      bar(l.leader, l.leaderMean, true) + bar(l.other, l.otherMean, false) + "</div>" +
      '<div class="wf-record"><span class="label">track by track, ' + esc(nameOf(q.a)) + "’s side</span>" +
      '<div class="wf-record-row"><div class="wf-cells" role="img" aria-label="' + q.wins + " ahead, " + q.ties + " tied, " + q.losses + ' behind">' + cells + "</div>" +
      '<div class="wf-rate"><span class="num">' + Math.round((100 * l.leaderWins) / n) + '%</span><span class="label">' + esc(nameOf(l.leader)) + " win rate</span></div></div>" +
      '<div class="wf-legend"><span><i class="ahead"></i>' + q.wins + " ahead</span><span><i class=\"tied\"></i>" + q.ties + " tied</span>" +
      '<span><i class="behind"></i>' + q.losses + " behind</span></div></div></div>";
  }

  function finishedHtml(study, focus) {
    const list = (study.players || []).filter((p) => p.finished > 0)
      .sort((a, b) => b.finished - a.finished || b.mean_rows - a.mean_rows);
    return '<div class="wf-fig-head"><span class="label">Tracks finished · all 150 rows</span><span class="label">share · count</span></div>' +
      '<div class="wf-cbars">' + list.map((p) =>
        '<button type="button" class="wf-cbar' + focusClass(p, focus) + '" data-player="' + esc(p.player) + '" ' + pressed(p, focus) + ">" +
        '<span class="wf-who">' + esc(nameOf(p.player)) + "</span>" +
        '<span class="wf-bar"><span class="wf-fill" style="width:' + p.finished * 100 + '%"></span></span>' +
        '<span class="wf-n">' + fmt.pct(p.finished) + '</span><span class="wf-of">' + Math.round(p.finished * p.seeds) + " / " + p.seeds + "</span></button>").join("") +
      "</div>";
  }

  // One trade-off chart: mean rows against `key` on a log axis, the free players in a column of their own on the
  // cost chart, the frontier dashed, the player in focus named. The bots are left out: they are there for scale.
  function scatterSvg(study, key, focus) {
    const W = 440, H = 320, L = 56, R = 16, T = 16, B = 48;
    const cost = key === "usd_per_track";
    const pts = (study.players || []).filter((p) => !p.yardstick && (cost || p[key] != null));
    const paid = pts.filter((p) => p[key] > 0);
    if (!paid.length) return '<svg class="wf-chart" viewBox="0 0 ' + W + " " + H + '"></svg>';
    const lmin = Math.floor(Math.log10(Math.min(...paid.map((p) => p[key]))));
    const lmax = Math.max(lmin + 1, Math.ceil(Math.log10(Math.max(...paid.map((p) => p[key])))));
    const freeCol = cost ? 56 : 0;
    const x = (v) => (cost && !(v > 0)) ? L + 16 : L + freeCol + ((Math.log10(v) - lmin) / (lmax - lmin)) * (W - L - R - freeCol);
    const y = (v) => T + (1 - Math.max(0, Math.min(MAX, v)) / MAX) * (H - T - B);
    const r1 = (v) => Math.round(v * 10) / 10;
    let s = "";
    [0, 50, 100, 150].forEach((v) => {
      s += '<line class="wf-grid" x1="' + L + '" x2="' + (W - R) + '" y1="' + y(v) + '" y2="' + y(v) + '"/>' +
        '<text x="' + (L - 8) + '" y="' + (y(v) + 4) + '" text-anchor="end">' + v + "</text>";
    });
    for (let e = lmin; e <= lmax; e++) {
      const v = Math.pow(10, e);
      const t = cost ? "$" + (v >= 1 ? String(v) : v.toFixed(-e)) : (v >= 1 ? String(v) : v.toFixed(-e)) + " s";
      s += '<text x="' + r1(x(v)) + '" y="' + (H - 26) + '" text-anchor="middle">' + t + "</text>";
    }
    if (cost) s += '<text x="' + (L + 16) + '" y="' + (H - 26) + '" text-anchor="middle">free</text>' +
      '<line class="wf-grid" x1="' + (L + 40) + '" x2="' + (L + 40) + '" y1="' + T + '" y2="' + (H - B) + '"/>';
    s += '<text class="wf-axt" x="' + (L + W - R) / 2 + '" y="' + (H - 4) + '" text-anchor="middle">' +
      (cost ? "USD per track (log)" : "seconds per decision (log)") + "</text>" +
      '<text class="wf-axt" transform="translate(14 ' + (T + H - B) / 2 + ') rotate(-90)" text-anchor="middle">mean rows</text>';
    const front = pts.filter((p) => p[cost ? "frontier_cost" : "frontier_speed"]).sort((a, b) => x(a[key]) - x(b[key]));
    if (front.length > 1) s += '<polyline class="wf-frontier" points="' + front.map((p) => r1(x(p[key])) + "," + r1(y(p.mean_rows))).join(" ") + '"/>';
    const marks = pts.slice().sort((a, b) => (a.player === focus) - (b.player === focus)); // the focus drawn last, on top
    marks.forEach((p) => {
      const cx = r1(x(p[key])), cy = r1(y(p.mean_rows)), on = p.player === focus ? " focus" : "";
      if (p.ci_low != null) s += '<line class="wf-whisker' + on + '" x1="' + cx + '" x2="' + cx + '" y1="' + r1(y(p.ci_high)) + '" y2="' + r1(y(p.ci_low)) + '"/>';
      s += '<g class="wf-hit" data-player="' + esc(p.player) + '"><title>' + esc(nameOf(p.player)) + "</title>" +
        '<circle class="wf-hit-area" cx="' + cx + '" cy="' + cy + '" r="14"/>' +
        '<rect class="wf-dot' + on + '" x="' + (cx - 4.5) + '" y="' + (cy - 4.5) + '" width="9" height="9"/></g>';
    });
    const f = pts.find((p) => p.player === focus);
    if (f) {
      const cx = x(f[key]), right = cx > W - 150;
      s += '<text class="wf-dotname focus" x="' + r1(cx + (right ? -10 : 10)) + '" y="' + r1(y(f.mean_rows) - 8) + '" text-anchor="' +
        (right ? "end" : "start") + '">' + esc(nameOf(f.player)) + "</text>";
    }
    return '<svg class="wf-chart" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Mean rows against ' +
      (cost ? "USD per track" : "seconds per decision") + '">' + s + "</svg>";
  }

  function costTimeHtml(study, focus) {
    return '<div class="wf-two">' +
      '<div class="wf-frame"><div class="wf-fig-head"><span class="label">Rows against cost per track</span></div>' + scatterSvg(study, "usd_per_track", focus) + "</div>" +
      '<div class="wf-frame"><div class="wf-fig-head"><span class="label">Rows against time per decision</span></div>' + scatterSvg(study, "s_per_decision_median", focus) + "</div>" +
      "</div>";
  }

  function scoresHtml(study, focus) {
    const head = ["player", "mean rows", "USD per track", "rows per cent", "s per decision", "rows per second"];
    return '<div class="scroll"><table><thead><tr>' + head.map((h, i) => "<th" + (i ? ' class="r"' : "") + ">" + h + "</th>").join("") +
      "</tr></thead><tbody>" + byMean(study).filter((p) => !p.yardstick).map((p) =>
        '<tr data-player="' + esc(p.player) + '" class="' + (p.player === focus ? "focus" : "") + '">' +
        '<td><button type="button" data-player="' + esc(p.player) + '" ' + pressed(p, focus) + ">" + esc(nameOf(p.player)) + "</button></td>" +
        '<td class="r">' + fmt.rows(p.mean_rows) + '</td><td class="r">' + esc(fmt.usd(p)) + "</td>" +
        '<td class="r">' + (p.rows_per_cent == null ? "free" : fmt.score(p.rows_per_cent) + (p.cost_basis === "estimate" ? " (est.)" : "")) + "</td>" +
        '<td class="r">' + fmt.secs(p.s_per_decision_median) + '</td><td class="r">' + fmt.score(p.rows_per_second) + "</td></tr>").join("") +
      "</tbody></table></div>";
  }

  // Every slot's HTML for one state: {KEY: html}
  function figures(study, state) {
    if (!study || !Array.isArray(study.players) || !study.players.length) {
      return Object.fromEntries(KEYS.map((k) => [k, '<p class="why">No numbers to draw yet.</p>']));
    }
    const focus = focusOf(study, state.focus), set = setOf(study, state.set);
    return { leaderboard: leaderboardHtml(study, focus), rows: rowsHtml(study, focus), "rows-ci": boardHtml(study, focus), "jev-vs-haiku": pairHtml(study, set),
      finished: finishedHtml(study, focus), "cost-time": costTimeHtml(study, focus), scores: scoresHtml(study, focus) };
  }

  // ---- the glue ------------------------------------------------------------------------------------
  const MOUNTED = typeof WeakMap === "function" ? new WeakMap() : null;

  // Fills every [data-fig] slot under `root` (but `new`) from `study` and wires its clicks. A second mount on the
  // same root replaces the first: its listener is taken off and every slot drawn again, never added to.
  function mount(rootEl, study) {
    const before = MOUNTED && MOUNTED.get(rootEl);
    if (before) rootEl.removeEventListener("click", before.onClick);
    const state = { focus: before ? before.state.focus : null, set: before ? before.state.set : null };
    const slots = [...rootEl.querySelectorAll("[data-fig]")].filter((el) => KEYS.includes(el.getAttribute("data-fig")));
    function draw() {
      const html = figures(study, state);
      for (const slot of slots) {
        let body = slot.querySelector(".fig-body");
        if (!body) {
          body = slot.ownerDocument.createElement("div");
          body.className = "fig-body";
          slot.insertBefore(body, slot.firstChild);
        }
        body.innerHTML = html[slot.getAttribute("data-fig")];
      }
    }
    function onClick(event) {
      const target = event.target && event.target.closest ? event.target : null;
      if (!target) return;
      const chip = target.closest(".wf-chip[data-set]");
      if (chip && rootEl.contains(chip)) { state.set = chip.getAttribute("data-set"); return redraw(chip); }
      const hit = target.closest("[data-player]");
      if (hit && rootEl.contains(hit) && hit.closest("[data-fig]")) { state.focus = hit.getAttribute("data-player"); redraw(hit); }
    }
    // drawn again, the element clicked is a new one: keyboard focus goes to its twin so Tab carries on from there
    function redraw(from) {
      const fig = from.closest("[data-fig]"), key = fig && fig.getAttribute("data-fig");
      const which = from.getAttribute("data-set") != null ? '[data-set="' + from.getAttribute("data-set") + '"]'
        : 'button[data-player="' + from.getAttribute("data-player") + '"]';
      const hadFocus = from.ownerDocument && from.ownerDocument.activeElement === from;
      draw();
      if (hadFocus && key) {
        const again = rootEl.querySelector('[data-fig="' + key + '"] ' + which);
        if (again && again.focus) again.focus();
      }
    }
    draw();
    rootEl.addEventListener("click", onClick);
    if (MOUNTED) MOUNTED.set(rootEl, { onClick, state });
    return state;
  }

  const api = { PLAYER_FIELDS, PAIR_FIELDS, KEYS, esc, nameOf, fmt, glance, ordinal, standings, leaderboardHtml, pairsOf, leadOf, focusOf, setOf,
    rowsHtml, boardHtml, pairHtml, finishedHtml, scatterSvg, costTimeHtml, scoresHtml, figures, mount };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.WriteupFigs = api;
})(typeof window !== "undefined" ? window : globalThis);

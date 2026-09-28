// The benchmark, drawn into whatever element it is given: the standalone page (bench.html) and the
// replay's Analysis tab both mount this one renderer, so there is one drawing code and one set of
// numbers. The arithmetic is in bench.js (tested); this file only builds markup from it. Everything
// that comes from a run goes through esc().
(function (root) {
  "use strict";

  const B = typeof module !== "undefined" && module.exports ? require("./bench.js") : root.Bench;
  const { esc, linear, log, ticks, logTicks, logDomain, survivalPath, split, frontierPath, fmt } = B;

  const W = 720, H = 320, M = { left: 48, right: 120, top: 12, bottom: 36 };

  // The sections the benchmark needs, as markup, so a page only has to give it an empty element.
  // `at` names the parts this renderer fills; a page never has to know their ids.
  const SHELL = `
<section aria-label="Players">
  <h2 class="label">Players</h2>
  <p class="warn first" data-bench="thin" hidden></p>
  <p class="note first">Rows survived per track, with a 95% interval for the mean over tracks like these. Players
    with fewer than five tracks get no interval and are not ranked. Click a player to follow it through the charts;
    the blue marks the player in focus, nothing else.</p>
  <div class="scroll"><table data-bench="players"></table></div>
</section>

<section aria-label="Survival">
  <h2 class="label">Still running, row by row</h2>
  <svg data-bench="survival" class="chart" role="img" aria-label="Share of tracks each player is still running at each row. The numbers are in the table below it."></svg>
  <details class="numbers"><summary class="label">The numbers</summary>
    <div class="scroll"><table data-bench="survival-table"></table></div>
  </details>
</section>

<section aria-label="Rows against cost and time">
  <p class="note first">Each dot is a player's mean rows, its whisker the 95% interval. The dashed line is the
    frontier: the players no other beats on both axes, more rows for less. It names no single winner.</p>
  <div class="pair-charts">
    <div>
      <h2 class="label">Rows against cost per track</h2>
      <svg data-bench="cost" class="chart" role="img" aria-label="Mean rows against USD per track, free players in their own column. The same numbers are in the scores table."></svg>
    </div>
    <div>
      <h2 class="label">Rows against time per decision</h2>
      <svg data-bench="time" class="chart" role="img" aria-label="Mean rows against the median seconds a decision took. The same numbers are in the scores table."></svg>
    </div>
  </div>
</section>

<section aria-label="Scores">
  <h2 class="label">Rows for the money and the time</h2>
  <p class="note first">Extras beside the charts, never the verdict: rows per cent is mean rows over a track's cost in
    cents; rows per second is mean rows over the seconds a track's decisions took. Failed is the share of decisions
    that came back as no move.</p>
  <div class="scroll"><table data-bench="scores"></table></div>
</section>

<section aria-label="Pairs">
  <h2 class="label">Player against player</h2>
  <p class="note first">Only tracks both players ran, paired track by track. A verdict means the interval does not
    cross zero; "tracks needed" is how many tracks like these would give an 80% chance of one.</p>
  <div class="scroll"><table data-bench="pairs"></table></div>
</section>

<section aria-label="Notes">
  <h2 class="label">What these numbers do and do not say</h2>
  <ul class="prose" data-bench="notes"></ul>
</section>`;

  // Draw `data` (what bakeoff/bench.py wrote) into `element`. Returns nothing; clicking a player
  // anywhere moves the focus and redraws. Called again with new numbers, it simply redraws.
  function mount(element, data) {
    if (!data || !data.players || !data.players.length) return false;
    element.innerHTML = SHELL;
    const at = (name) => element.querySelector('[data-bench="' + name + '"]');
    // start on the best player with an interval (at least 5 tracks), else the best
    let focus = (data.players.find((p) => p.ci_low != null) || data.players[0]).player;

    function setFocus(player) {
      focus = player;
      render();
    }

    function ciBar(p) {
      const x = linear([0, data.max_rows], [2, 158]);
      const range = p.ci_low == null ? "" : `<line class="range" x1="${x(p.ci_low)}" x2="${x(p.ci_high)}" y1="7" y2="7"/>`;
      return `<svg class="ci" width="160" height="14" aria-hidden="true"><line class="track" x1="2" x2="158" y1="7" y2="7"/>` +
        `${range}<circle class="mean" cx="${x(p.mean_rows)}" cy="7" r="3"/></svg>`;
    }

    // What a handful of tracks is: said above the table, where the numbers are read, not only in the
    // notes at the bottom. A benchmark of one track is what happened, not a result.
    function leadLine() {
      const thin = at("thin");
      if (data.players.some((p) => p.ranked)) { thin.hidden = true; return; }
      const tracks = Math.max(...data.players.map((p) => p.seeds));
      thin.hidden = false;
      thin.textContent = tracks === 1 ? "One track: what happened on it, not a result. A player needs five tracks for an interval and a ranking."
        : tracks + " tracks: what happened on them, not a result. A player needs five tracks for an interval and a ranking.";
    }

    function playersTable() {
      const head = ["player", "tracks", "mean rows", "95% interval", "", "median", "finished", "USD per track",
                    "s per decision", "failed", "live", "cached"];
      const rows = data.players.map((p) => {
        const cur = p.player === focus ? ' aria-current="true"' : "";
        const interval = p.ranked ? fmt.interval(p.ci_low, p.ci_high) : "not ranked";
        return `<tr data-player="${esc(p.player)}"${cur} tabindex="0"><td>${esc(p.player)}</td><td>${p.seeds}</td>` +
          `<td>${fmt.rows(p.mean_rows)}</td><td>${interval}</td><td>${ciBar(p)}</td>` +
          `<td>${fmt.rows(p.median_rows)}</td><td>${fmt.percent(p.finished)}</td><td>${esc(fmt.track(p))}</td>` +
          `<td>${fmt.seconds(p.s_per_decision_median)}</td><td>${fmt.percent(p.failed_rate)}</td>` +
          `<td>${p.live_decisions}</td><td>${p.cache_hits}</td></tr>`;
      });
      const table = at("players");
      table.innerHTML = `<thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody>`;
      table.querySelectorAll("tbody tr").forEach((tr) => {
        tr.addEventListener("click", () => setFocus(tr.dataset.player));
        tr.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setFocus(tr.dataset.player); } });
      });
    }

    function axes(xTicks, x, yTicks, y, xLabel, yLabel, xFormat) {
      let s = "";
      for (const t of yTicks) s += `<line class="grid" x1="${M.left}" x2="${W - M.right}" y1="${y(t)}" y2="${y(t)}"/>` +
        `<text x="${M.left - 8}" y="${y(t) + 4}" text-anchor="end">${t}</text>`;
      for (const t of xTicks) s += `<text x="${x(t)}" y="${H - M.bottom + 18}" text-anchor="middle">${xFormat(t)}</text>`;
      s += `<line class="axis" x1="${M.left}" x2="${W - M.right}" y1="${H - M.bottom}" y2="${H - M.bottom}"/>`;
      s += `<text x="${W - M.right}" y="${H - 4}" text-anchor="end">${xLabel}</text>`;
      s += `<text x="${M.left}" y="${M.top - 2}" text-anchor="start">${yLabel}</text>`;
      return s;
    }

    function survivalChart() {
      const x = linear([0, data.max_rows], [M.left, W - M.right]);
      const y = linear([0, 1], [H - M.bottom, M.top + 8]);
      let s = axes(ticks(0, data.max_rows, 6), x, [0, 0.5, 1], y, "row", "share still running", (t) => t);
      const ordered = data.players.slice().sort((a, b) => (a.player === focus) - (b.player === focus)); // focus on top
      for (const p of ordered) {
        const f = p.player === focus ? " focus" : "";
        s += `<path class="line${f}" data-player="${esc(p.player)}" d="${survivalPath(p.survival, x, y)}"><title>${esc(p.player)}</title></path>`;
      }
      const p = data.players.find((q) => q.player === focus);
      const last = p.survival[p.survival.length - 1];
      s += `<text class="name focus" x="${W - M.right + 8}" y="${y(last) + 4}">${esc(p.player)}</text>`;
      const svg = at("survival");
      svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
      svg.innerHTML = s;
      svg.querySelectorAll(".line").forEach((el) => el.addEventListener("click", () => setFocus(el.dataset.player)));
      survivalTable();
    }

    // the survival curve as numbers: share still running at round rows and at the finish line
    function survivalTable() {
      const list = ticks(0, data.max_rows, 8).filter((r) => r > 0);
      if (list[list.length - 1] !== data.max_rows) list.push(data.max_rows);
      const head = `<tr><th>player</th>${list.map((r) => `<th>row ${r}</th>`).join("")}</tr>`;
      const rows = data.players.map((p) => `<tr${p.player === focus ? ' aria-current="true"' : ""}><td>${esc(p.player)}</td>` +
        list.map((r) => `<td>${fmt.percent(p.survival[r])}</td>`).join("") + "</tr>");
      at("survival-table").innerHTML = `<thead>${head}</thead><tbody>${rows.join("")}</tbody>`;
    }

    // `strips`: for a player without a value, the label of the strip it is listed in (never drawn at 0).
    // `zero`: the label of a column at the left for players whose value is 0 (the free ones), or null.
    // `edge`: the players' flag for this chart's frontier, drawn as a dashed staircase through them.
    function scatter(name, key, xLabel, xFormat, strips, zero, edge) {
      const zeroes = zero ? data.players.filter((p) => p[key] === 0) : [];
      const { placed, missing } = split(data.players.filter((p) => !zeroes.includes(p)), key);
      const svg = at(name);
      const w = 520, h = 340, m = { left: 48, right: 24, top: 12, bottom: 76 };
      const left = m.left + (zeroes.length ? 44 : 12); // room for the free column
      svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
      const y = linear([0, data.max_rows], [h - m.bottom, m.top + 8]);
      let s = "";
      for (const t of ticks(0, data.max_rows, 3)) s += `<line class="grid" x1="${m.left}" x2="${w - m.right}" y1="${y(t)}" y2="${y(t)}"/>` +
        `<text x="${m.left - 8}" y="${y(t) + 4}" text-anchor="end">${t}</text>`;
      s += `<text x="${m.left}" y="${m.top - 2}">mean rows</text>`;
      const at_ = new Map(); // player -> its x on this chart
      if (zeroes.length) {
        for (const p of zeroes) at_.set(p.player, m.left + 16);
        s += `<text x="${m.left + 16}" y="${h - m.bottom + 18}" text-anchor="middle">${esc(zero)}</text>`;
      }
      if (placed.length) {
        const domain = logDomain(placed.map((p) => p[key]));
        const x = log(domain, [left, w - m.right - 12]);
        for (const p of placed) at_.set(p.player, x(p[key]));
        for (const t of logTicks(domain[0], domain[1])) s += `<text x="${x(t)}" y="${h - m.bottom + 18}" text-anchor="middle">${xFormat(t)}</text>`;
        s += `<text x="${w - m.right}" y="${h - m.bottom + 34}" text-anchor="end">${xLabel}, log scale</text>`;
      }
      if (at_.size) s += `<line class="axis" x1="${m.left}" x2="${w - m.right}" y1="${h - m.bottom}" y2="${h - m.bottom}"/>`;
      const drawn = [...zeroes, ...placed];
      const onEdge = drawn.filter((p) => p[edge]).map((p) => ({ x: at_.get(p.player), y: y(p.mean_rows) }));
      if (onEdge.length) s += `<path class="frontier" d="${frontierPath(onEdge)}"/>`;
      for (const p of drawn) {
        const f = p.player === focus ? " focus" : "";
        const kind = p.yardstick ? " yardstick" : "";
        const cx = at_.get(p.player);
        if (p.ci_low != null) s += `<line class="whisker${f}" x1="${cx}" x2="${cx}" y1="${y(p.ci_low)}" y2="${y(p.ci_high)}"/>`;
        s += `<circle class="dot${f}${kind}" data-player="${esc(p.player)}" cx="${cx}" cy="${y(p.mean_rows)}" r="${f ? 5 : 4}"><title>${esc(p.player)}</title></circle>`;
        if (f) s += `<text class="name focus" x="${cx + 8}" y="${y(p.mean_rows) - 8}">${esc(p.player)}</text>`;
        // with many players only the frontier is named, so the line can be read without clicking
        else if (drawn.length <= 12 || p[edge]) s += `<text class="dot-name" x="${cx + 7}" y="${y(p.mean_rows) + 3}">${esc(p.player)}</text>`;
      }
      const groups = {};
      for (const p of missing) (groups[strips(p)] = groups[strips(p)] || []).push(esc(p.player));
      Object.keys(groups).forEach((label, i) => {
        s += `<text class="strip" x="${m.left}" y="${h - 4 - 14 * i}">${esc(label)}: ${groups[label].join(", ")}</text>`;
      });
      svg.innerHTML = s;
      svg.querySelectorAll(".dot").forEach((el) => el.addEventListener("click", () => setFocus(el.dataset.player)));
    }

    // the named scores, in the players table's order: extras, never the verdict
    function scoresTable() {
      const head = ["player", "tracks", "mean rows", "USD per track", "rows per cent", "s per decision", "rows per second", "failed"];
      const rows = data.players.map((p) => {
        const cur = p.player === focus ? ' aria-current="true"' : "";
        return `<tr data-player="${esc(p.player)}"${cur}><td>${esc(p.player)}${p.yardstick ? " (yardstick)" : ""}</td>` +
          `<td>${p.seeds}</td><td>${fmt.rows(p.mean_rows)}</td><td>${esc(fmt.track(p))}</td>` +
          `<td>${esc(fmt.score(p.rows_per_cent, p.cost_basis === "free" ? "free" : "–"))}</td>` +
          `<td>${fmt.seconds(p.s_per_decision_median)}</td><td>${esc(fmt.score(p.rows_per_second, "no time"))}</td>` +
          `<td>${fmt.percent(p.failed_rate)}</td></tr>`;
      });
      at("scores").innerHTML = `<thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody>`;
    }

    function pairsTable() {
      const head = ["A", "B", "tracks", "A − B", "95% interval", "A wins / ties / B wins", "verdict", "tracks needed"];
      const rows = data.pairs.map((q) => {
        const f = q.a === focus || q.b === focus ? ' class="focus"' : "";
        return `<tr${f}><td>${esc(q.a)}</td><td>${esc(q.b)}</td><td>${q.common_seeds}</td><td>${fmt.signed(q.mean_diff)}</td>` +
          `<td>${fmt.interval(q.ci_low, q.ci_high)}</td><td>${q.wins} / ${q.ties} / ${q.losses}</td>` +
          `<td class="verdict">${esc(q.verdict)}</td><td>${q.seeds_needed == null ? "–" : q.seeds_needed}</td></tr>`;
      });
      at("pairs").innerHTML =
        `<thead><tr>${head.map((h, i) => `<th${i === 6 ? ' class="verdict"' : ""}>${h}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody>`;
    }

    function notes() {
      const items = data.notes.map(esc);
      if (data.incomplete.length) {
        items.unshift("Left out, neither dead nor finished (a stopped run): " + data.incomplete
          .map((e) => `${esc(e.player)} on track ${e.seed} (${esc(e.run_id)}, ${e.rows} rows)`).join(", ") + ".");
      }
      items.push("Runs read: " + data.runs.map(esc).join(", ") + ".");
      at("notes").innerHTML = items.map((t) => `<li>${t}</li>`).join("");
    }

    function render() {
      leadLine();
      playersTable();
      survivalChart();
      scatter("cost", "usd_per_track", "USD per track", (t) => String(t), () => "no price", "free", "frontier_cost");
      scatter("time", "s_per_decision_median", "seconds per decision", (t) => String(t), () => "no time recorded", null,
              "frontier_speed");
      scoresTable();
      pairsTable();
    }

    notes();
    render();
    return true;
  }

  // The line a page shows instead of the charts when there is nothing to draw.
  function why(data) {
    if (!data) return "No benchmark was built for this page.";
    if (!data.players || !data.players.length) return "No completed run to score: the benchmark needs runs that ended.";
    return null;
  }

  const api = { mount, why, SHELL };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.BenchView = api;
})(typeof window !== "undefined" ? window : globalThis);

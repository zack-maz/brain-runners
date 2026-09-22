// The benchmark page: reads the numbers bakeoff/bench.py embedded and draws the tables and charts.
// Arithmetic lives in bench.js (tested); this file only builds markup from it.
(function () {
  "use strict";
  const { esc, linear, log, ticks, logTicks, logDomain, survivalPath, split, fmt } = window.Bench;
  const data = JSON.parse(document.getElementById("replay-data").textContent);
  if (!data || !data.players || !data.players.length) {
    document.getElementById("empty").hidden = false;
    return;
  }
  document.getElementById("app").hidden = false;
  document.getElementById("game").textContent = `game ${data.game || "unknown"} · ${data.runs.length} runs`;

  // start on the best player with an interval (at least 5 tracks), else the best
  let focus = (data.players.find((p) => p.ci_low != null) || data.players[0]).player;
  const W = 720, H = 320, M = { left: 48, right: 120, top: 12, bottom: 36 };

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

  function playersTable() {
    const head = ["player", "tracks", "mean rows", "95% interval", "", "median", "finished", "s per row", "USD per row",
                  "live", "cached"];
    const rows = data.players.map((p) => {
      const cur = p.player === focus ? ' aria-current="true"' : "";
      const interval = p.ranked ? fmt.interval(p.ci_low, p.ci_high) : "not ranked";
      const cost = p.cost === "priced" ? fmt.usd(p.usd_per_row) : esc(p.cost);
      return `<tr data-player="${esc(p.player)}"${cur} tabindex="0"><td>${esc(p.player)}</td><td>${p.seeds}</td>` +
        `<td>${fmt.rows(p.mean_rows)}</td><td>${interval}</td><td>${ciBar(p)}</td>` +
        `<td>${fmt.rows(p.median_rows)}</td><td>${fmt.percent(p.finished)}</td><td>${fmt.seconds(p.s_per_row)}</td>` +
        `<td>${cost}</td><td>${p.live_decisions}</td><td>${p.cache_hits}</td></tr>`;
    });
    const table = document.getElementById("players");
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
    const svg = document.getElementById("survival");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.innerHTML = s;
    svg.querySelectorAll(".line").forEach((el) => el.addEventListener("click", () => setFocus(el.dataset.player)));
    survivalTable();
  }

  // the survival curve as numbers: share still running at round rows and at the finish line
  function survivalTable() {
    const at = ticks(0, data.max_rows, 8).filter((r) => r > 0);
    if (at[at.length - 1] !== data.max_rows) at.push(data.max_rows);
    const head = `<tr><th>player</th>${at.map((r) => `<th>row ${r}</th>`).join("")}</tr>`;
    const rows = data.players.map((p) => `<tr${p.player === focus ? ' aria-current="true"' : ""}><td>${esc(p.player)}</td>` +
      at.map((r) => `<td>${fmt.percent(p.survival[r])}</td>`).join("") + "</tr>");
    document.getElementById("survival-table").innerHTML = `<thead>${head}</thead><tbody>${rows.join("")}</tbody>`;
  }

  // `strips`: for a player without a value, the label of the strip it is listed in (never drawn at 0)
  function scatter(id, key, xLabel, xFormat, strips) {
    const { placed, missing } = split(data.players, key);
    const svg = document.getElementById(id);
    const w = 520, h = 340, m = { left: 48, right: 24, top: 12, bottom: 76 };
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    const y = linear([0, data.max_rows], [h - m.bottom, m.top + 8]);
    let s = "";
    for (const t of ticks(0, data.max_rows, 3)) s += `<line class="grid" x1="${m.left}" x2="${w - m.right}" y1="${y(t)}" y2="${y(t)}"/>` +
      `<text x="${m.left - 8}" y="${y(t) + 4}" text-anchor="end">${t}</text>`;
    s += `<text x="${m.left}" y="${m.top - 2}">mean rows</text>`;
    if (placed.length) {
      const x = log(logDomain(placed.map((p) => p[key])), [m.left + 12, w - m.right - 12]);
      const domain = logDomain(placed.map((p) => p[key]));
      for (const t of logTicks(domain[0], domain[1])) s += `<text x="${x(t)}" y="${h - m.bottom + 18}" text-anchor="middle">${xFormat(t)}</text>`;
      s += `<line class="axis" x1="${m.left}" x2="${w - m.right}" y1="${h - m.bottom}" y2="${h - m.bottom}"/>`;
      s += `<text x="${w - m.right}" y="${h - m.bottom + 34}" text-anchor="end">${xLabel}, log scale</text>`;
      for (const p of placed) {
        const f = p.player === focus ? " focus" : "";
        const cx = x(p[key]);
        if (p.ci_low != null) s += `<line class="whisker${f}" x1="${cx}" x2="${cx}" y1="${y(p.ci_low)}" y2="${y(p.ci_high)}"/>`;
        s += `<circle class="dot${f}" data-player="${esc(p.player)}" cx="${cx}" cy="${y(p.mean_rows)}" r="${f ? 5 : 4}"><title>${esc(p.player)}</title></circle>`;
        if (f) s += `<text class="name focus" x="${cx + 8}" y="${y(p.mean_rows) - 8}">${esc(p.player)}</text>`;
        else if (placed.length <= 12) s += `<text class="dot-name" x="${cx + 7}" y="${y(p.mean_rows) + 3}">${esc(p.player)}</text>`;
      }
    }
    const groups = {};
    for (const p of missing) (groups[strips(p)] = groups[strips(p)] || []).push(esc(p.player));
    Object.keys(groups).forEach((label, i) => {
      s += `<text class="strip" x="${m.left}" y="${h - 4 - 14 * i}">${esc(label)}: ${groups[label].join(", ")}</text>`;
    });
    svg.innerHTML = s;
    svg.querySelectorAll(".dot").forEach((el) => el.addEventListener("click", () => setFocus(el.dataset.player)));
  }

  function pairsTable() {
    const head = ["A", "B", "tracks", "A − B", "95% interval", "A wins / ties / B wins", "verdict", "tracks needed"];
    const rows = data.pairs.map((q) => {
      const f = q.a === focus || q.b === focus ? ' class="focus"' : "";
      return `<tr${f}><td>${esc(q.a)}</td><td>${esc(q.b)}</td><td>${q.common_seeds}</td><td>${fmt.signed(q.mean_diff)}</td>` +
        `<td>${fmt.interval(q.ci_low, q.ci_high)}</td><td>${q.wins} / ${q.ties} / ${q.losses}</td>` +
        `<td class="verdict">${esc(q.verdict)}</td><td>${q.seeds_needed == null ? "–" : q.seeds_needed}</td></tr>`;
    });
    document.getElementById("pairs").innerHTML =
      `<thead><tr>${head.map((h, i) => `<th${i === 6 ? ' class="verdict"' : ""}>${h}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody>`;
  }

  function notes() {
    const items = data.notes.map(esc);
    if (data.incomplete.length) {
      items.unshift("Left out, neither dead nor finished (a stopped run): " + data.incomplete
        .map((e) => `${esc(e.player)} on track ${e.seed} (${esc(e.run_id)}, ${e.rows} rows)`).join(", ") + ".");
    }
    items.push("Runs read: " + data.runs.map(esc).join(", ") + ".");
    document.getElementById("notes").innerHTML = items.map((t) => `<li>${t}</li>`).join("");
  }

  function render() {
    playersTable();
    survivalChart();
    scatter("cost", "usd_per_row", "USD per row", (t) => String(t), (p) => (p.cost === "free" ? "free" : "no price"));
    scatter("time", "s_per_row", "seconds per row", (t) => String(t), () => "no time recorded");
    pairsTable();
  }

  notes();
  render();
})();

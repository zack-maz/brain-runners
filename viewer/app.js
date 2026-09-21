// The page: track table, transport, one column per player, scoreboard. Glue only; the parts with
// rules in them are timeline.js, tunnel.js and minds.js, which have tests.
(function () {
  "use strict";

  const replay = JSON.parse(document.getElementById("replay-data").textContent);
  if (!replay) return;
  document.getElementById("empty").hidden = true;
  document.getElementById("app").hidden = false;

  const $ = (id) => document.getElementById(id);
  const esc = Minds.esc;
  const cell = Minds.cell;
  const CONTESTANTS = ["fly", "jev", "llm"];
  const COLOURS = { fly: [176, 116, 0], jev: [11, 134, 128], llm: [94, 82, 204] };
  const BASELINE = [96, 108, 116];
  const ABOUT = {
    fly: "Fruit fly connectome, untrained",
    jev: "Jev, TypeSafe System One",
    llm: "Large language model",
    random: "Random moves, the floor",
    always_jump: "Always jumps, the second floor",
    solver: "Scripted solver, the reference (not a contestant)",
  };
  const TAIL = 1.5; // rows of time after the last landing, so the last fall is seen
  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const runOf = (episode) => replay.runs.find((run) => run.run_id === episode.run_id) || {};
  const episodeOf = (player, seed) => replay.episodes.find((e) => e.player === player && e.seed === seed);
  const colourOf = (player) => COLOURS[player] || BASELINE;
  const blend = (a, b, share) => a.map((c, i) => Math.round(c + (b[i] - c) * share));

  const contestants = replay.players.filter((p) => CONTESTANTS.includes(p));
  const view = {
    seed: replay.seeds[0],
    shown: new Set(contestants.length ? contestants : replay.players),
    t: 0, playing: false, speed: 3, columns: [], duration: 1, lastRow: 1,
  };

  // ---- header -------------------------------------------------------------------------------
  $("runs").innerHTML = "Replay of " + replay.runs.map((run) => {
    const sha = run.git_sha ? run.git_sha.slice(0, 7) + (run.git_dirty ? ", uncommitted changes" : "") : "unknown commit";
    const status = run.status === "completed" ? "completed" : '<span class="warn">' + esc(run.status || "status unknown") + "</span>";
    return "run " + esc(run.run_id) + " (" + status + ", " + esc(sha) + ")";
  }).join("; ");

  const gameRun = replay.runs.find((run) => run.game);
  $("sight").innerHTML = gameRun
    ? "Every player gets the same track and sees the same " + esc(gameRun.game.lookahead) + " rows ahead, " +
      esc(gameRun.game.window) + " lanes either side (the brighter tiles)."
    : "Every player gets the same track and sees the same rows ahead (the brighter tiles).";

  // ---- track table --------------------------------------------------------------------------
  function renderMatrix() {
    let html = "<thead><tr><th>track</th>" + replay.seeds.map((seed) =>
      '<th><button type="button" data-seed="' + esc(seed) + '"' + (seed === view.seed ? ' aria-current="true"' : "") + ">" + esc(seed) +
      "</button></th>").join("") + "</tr></thead><tbody>";
    for (const player of replay.players) {
      html += '<tr style="--player:rgb(' + colourOf(player).join(",") + ')"><th><button type="button" data-player="' + esc(player) +
        '" aria-pressed="' + view.shown.has(player) + '">' + esc(player) + "</button></th>";
      for (const seed of replay.seeds) {
        const episode = episodeOf(player, seed);
        const track = replay.tracks[String(seed)];
        const mark = !episode ? "" : !episode.complete ? " …" : episode.finished ? " ✓" : "";
        const shorter = episode && track && episode.max_rows != null && episode.max_rows !== track.max_rows ? " /" + esc(episode.max_rows) : "";
        const shown = episode ? esc(episode.rows_survived) + mark + shorter : "";
        html += "<td" + (seed === view.seed ? ' class="current"' : "") + ">" + shown + "</td>";
      }
      html += "</tr>";
    }
    $("matrix").innerHTML = html + "</tbody>";
  }

  $("matrix").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.dataset.seed != null) {
      view.seed = Number(button.dataset.seed);
      view.t = 0;
      setPlaying(false);
    } else if (view.shown.has(button.dataset.player)) view.shown.delete(button.dataset.player);
    else view.shown.add(button.dataset.player);
    renderMatrix();
    renderStage();
  });

  // ---- stage --------------------------------------------------------------------------------
  function renderStage() {
    const track = replay.tracks[String(view.seed)];
    const episodes = replay.episodes.filter((e) => e.seed === view.seed && view.shown.has(e.player));
    const stage = $("stage");
    stage.innerHTML = "";
    view.columns = [];
    if (!track || !episodes.length) {
      stage.innerHTML = '<p class="muted">None of the players shown ran track ' + esc(view.seed) + ". Pick a player above to show it.</p>";
      return;
    }
    for (const episode of episodes) {
      const run = runOf(episode);
      const colour = colourOf(episode.player);
      const model = (run.models || {})[episode.player];
      const column = document.createElement("article");
      column.style.setProperty("--player", "rgb(" + colour.join(",") + ")");
      column.innerHTML = "<h3>" + esc(episode.player) + '</h3><p class="muted">' + esc(ABOUT[episode.player] || "") +
        (model ? " (" + esc(model) + ")" : "") + '</p><canvas></canvas><p class="status"></p><div class="mind"></div>';
      stage.appendChild(column);
      const canvas = column.querySelector("canvas");
      const size = 360, ratio = window.devicePixelRatio || 1;
      canvas.width = canvas.height = size * ratio;
      const ctx = canvas.getContext("2d");
      ctx.scale(ratio, ratio);
      const game = run.game || {};
      const lanesEitherSide = run.game ? game.window : 3; // default 3 only when the run has no game block at all
      view.columns.push({
        episode, track, ctx, size, index: -1,
        status: column.querySelector(".status"), mind: column.querySelector(".mind"),
        lookahead: game.lookahead || 6, window: lanesEitherSide,
        context: { windowMs: run.fly ? run.fly.window_ms : null, window: lanesEitherSide,
                   maxHz: game.looming ? game.looming.max_hz : null },
        colours: { space: [14, 24, 34], floor: [104, 120, 130], finish: [236, 224, 180],
                   seen: blend([214, 224, 226], colour, 0.3), runner: blend(colour, [255, 255, 255], 0.35) },
      });
    }
    view.duration = Math.max(1, ...episodes.map(Timeline.endRow)) + TAIL;
    // the scrubber still ends where the last shown runner ends; the clock's "of N" is the length
    // of the track being played, not wherever a runner that died early happened to stop
    const rowsShown = episodes.map((e) => e.max_rows).filter((n) => n != null);
    view.lastRow = rowsShown.length ? Math.max(...rowsShown) : (track ? track.max_rows : 1);
    $("scrub").max = view.duration;
    draw();
  }

  function draw() {
    const t = still ? Math.floor(view.t) : view.t;
    for (const column of view.columns) {
      const { episode, track } = column;
      const state = Timeline.stateAt(episode, t, track.lanes);
      const seen = { row: state.frame.row, lane: state.frame.lane, lookahead: column.lookahead, window: column.window };
      Tunnel.draw(column.ctx, column.size, track, state, seen, episode.max_rows || track.max_rows, column.colours);
      const status = Minds.statusLine(episode, state, track.lanes);
      if (column.status.innerHTML !== status) column.status.innerHTML = status;
      if (state.index !== column.index) {
        const open = !!(column.mind.querySelector("details") || {}).open;
        column.mind.innerHTML = Minds.mind(episode, state.frame, column.context);
        if (open && column.mind.querySelector("details")) column.mind.querySelector("details").open = true;
        column.index = state.index;
      }
    }
    $("scrub").value = view.t;
    $("clock").textContent = "row " + Math.min(Math.floor(view.t), view.lastRow) + " of " + view.lastRow;
  }

  // ---- transport ----------------------------------------------------------------------------
  let lastTick = null;
  function tick(now) {
    if (!view.playing) return;
    view.t = Math.min(view.duration, view.t + ((now - lastTick) / 1000) * view.speed);
    lastTick = now;
    draw();
    if (view.t >= view.duration) setPlaying(false);
    else requestAnimationFrame(tick);
  }

  function setPlaying(playing) {
    if (playing && view.t >= view.duration) view.t = 0;
    view.playing = playing;
    $("play").textContent = playing ? "Pause" : "Play";
    if (playing) {
      lastTick = performance.now();
      requestAnimationFrame(tick);
    }
  }

  function stepRows(rows) {
    setPlaying(false);
    view.t = Math.max(0, Math.min(view.duration, Math.round(view.t) + rows));
    draw();
  }

  $("play").addEventListener("click", () => setPlaying(!view.playing));
  $("back").addEventListener("click", () => stepRows(-1));
  $("forward").addEventListener("click", () => stepRows(1));
  $("speed").addEventListener("change", (event) => { view.speed = Number(event.target.value); });
  $("scrub").addEventListener("input", (event) => { view.t = Number(event.target.value); draw(); });
  document.addEventListener("keydown", (event) => {
    if (event.target.closest("button, select, input, summary")) return;
    if (event.key === " ") { event.preventDefault(); setPlaying(!view.playing); }
    if (event.key === "ArrowLeft") stepRows(-1);
    if (event.key === "ArrowRight") stepRows(1);
  });

  // ---- scoreboard ---------------------------------------------------------------------------
  const board = replay.scoreboard;
  $("scoreboard").innerHTML = "<thead><tr>" + board.columns.map((c) => "<th>" + esc(c.replace(/_/g, " ")) + "</th>").join("") +
    "</tr></thead><tbody>" + board.rows.map((row) => "<tr>" + board.columns.map((c) =>
      (c === "player" ? "<th>" + cell(row[c]) + "</th>" : "<td>" + cell(row[c]) + "</td>")).join("") + "</tr>").join("") + "</tbody>";
  $("fairness").hidden = board.same_seeds;

  // ---- what is ours -------------------------------------------------------------------------
  const flyRun = replay.runs.find((run) => run.fly && (run.players || []).includes("fly")) || replay.runs.find((run) => run.fly);
  $("ours").innerHTML = Minds.ours(flyRun);

  renderMatrix();
  renderStage();
})();

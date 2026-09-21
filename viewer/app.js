// The page: one tunnel with every shown runner in it, the mind strip, the blue cursor, the transport
// and the three sections underneath. Glue only; the parts with rules in them are timeline.js, tunnel.js,
// sprites.js, stage.js, minds.js and feed.js, which have tests. Frames reach this file through Feed
// alone, so a replay file and a live run are the same thing here.
(function () {
  "use strict";

  const embedded = JSON.parse(document.getElementById("replay-data").textContent);
  if (!embedded) return;
  const liveUrl = document.body.dataset.live || null;

  const $ = (id) => document.getElementById(id);
  const esc = Minds.esc;
  const cell = Minds.cell;
  const DEMO = ["fly", "jev_composed", "llm"]; // the default view; an older replay has only the one-shot jev
  const SPRITE = { fly: "fly", jev_composed: "visor", llm: "llm" }; // everyone else is a plain grey block
  const ABOUT = {
    fly: "Fruit fly connectome, untrained",
    jev_composed: "Jev, four yes/no questions a row",
    jev: "Jev, one broad question a row",
    llm: "Large language model",
    random: "Random moves, the floor",
    always_jump: "Always jumps, the second floor",
    solver: "Scripted solver, the reference (not a contestant)",
  };
  const TAIL = 1.5; // rows of time after the last landing, so the last fall is seen
  const INK = { muted: "#7C848D", bright: "#E8EBED", accent: "#7AA2F7" }; // brand tokens, for the canvas
  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---- the store: everything the feed has delivered -------------------------------------------
  const store = { game: null, runs: [], players: [], seeds: [], tracks: {}, episodes: [], scoreboard: null, ended: !liveUrl, error: null };
  const view = {
    seed: null, shown: new Set(), focus: null, auto: true, heldSince: 0,
    t: 0, playing: false, speed: 3, following: !!liveUrl, size: 0, runners: [], panels: {},
  };

  const runOf = (episode) => store.runs.find((run) => run.run_id === episode.run_id) || {};
  const episodeOf = (player, seed) => store.episodes.find((e) => e.player === player && e.seed === seed);
  // a runner can be placed once it has a frame and its track is known
  const playing = () => store.episodes.filter((e) => e.seed === view.seed && view.shown.has(e.player) && e.frames.length &&
    store.tracks[String(e.seed)])
    .sort((a, b) => order(a.player) - order(b.player));
  const order = (player) => {
    const at = store.players.indexOf(player);
    return at < 0 ? store.players.length : at;
  };

  const handlers = {
    onMeta(meta) {
      Object.assign(store, { game: meta.game, runs: meta.runs, players: meta.players.slice(), seeds: meta.seeds.slice(), scoreboard: meta.scoreboard });
    },
    onEpisode(episode, track) {
      store.episodes.push({ ...episode, frames: [] });
      if (track) store.tracks[String(episode.seed)] = track;
      if (!store.players.includes(episode.player)) store.players.push(episode.player);
      if (!store.seeds.includes(episode.seed)) store.seeds.push(episode.seed);
      if (ready) arrived(episode);
    },
    onFrame(player, seed, frame, summary) {
      const episode = episodeOf(player, seed);
      episode.frames.push(frame);
      if (summary) Object.assign(episode, summary);
      if (!ready) return;
      if (episode.frames.length === 1) renderAll(); // a runner can be placed once it has decided something
      else renderMatrix();
      follow();
    },
    onEnd(end) {
      store.ended = true;
      if (end.runs) store.runs = end.runs;
      if (end.scoreboard) store.scoreboard = end.scoreboard;
      notice(end.status === "completed" ? null : "The run ended: " + end.status, false);
      renderAll();
    },
    onError(message) {
      if (store.ended) return;
      if (message != null) store.error = message; // why the run stops; it stays on screen
      notice(message == null ? "The connection to the live run was lost. Waiting for it to come back." : message, message != null);
    },
  };

  function notice(text, bad) {
    $("notice").hidden = text == null;
    $("notice").textContent = text || "";
    $("notice").className = "label corner bottom" + (bad ? " bad" : "");
  }

  // ---- what is shown ------------------------------------------------------------------------
  function chooseDefaults() {
    const demoOn = (seed) => DEMO.filter((p) => episodeOf(p, seed)).length;
    view.seed = store.seeds.slice().sort((a, b) => demoOn(b) - demoOn(a) || a - b)[0];
    if (view.seed == null) return;
    const here = store.players.filter((p) => episodeOf(p, view.seed));
    let shown = here.filter((p) => DEMO.includes(p));
    if (!shown.includes("jev_composed") && here.includes("jev")) shown.push("jev");
    view.shown = new Set(shown.length ? shown : here);
  }

  function arrived(episode) { // live: a runner joins. The operator chose who plays, so everyone is shown.
    if (view.seed == null) view.seed = episode.seed;
    if (episode.seed === view.seed) view.shown.add(episode.player);
    renderAll();
  }

  // ---- level table --------------------------------------------------------------------------
  function renderMatrix() {
    let html = "<thead><tr><th>track</th>" + store.seeds.map((seed) =>
      '<th><button type="button" data-seed="' + esc(seed) + '"' + (seed === view.seed ? ' aria-current="true"' : "") + ">" + esc(seed) +
      "</button></th>").join("") + "</tr></thead><tbody>";
    for (const player of store.players) {
      html += '<tr><th><button type="button" data-player="' + esc(player) + '" aria-pressed="' + view.shown.has(player) + '">' +
        esc(Minds.tagOf(player)) + "</button></th>";
      for (const seed of store.seeds) {
        const episode = episodeOf(player, seed);
        const track = store.tracks[String(seed)];
        // "…" means the run was stopped; an episode of a live run that is still going is neither stopped nor over
        const mark = !episode ? "" : !episode.complete ? (store.ended ? " …" : "") : episode.finished ? " ✓" : "";
        const shorter = episode && track && episode.max_rows != null && episode.max_rows !== track.max_rows ? " /" + esc(episode.max_rows) : "";
        const shown = episode && episode.rows_survived != null ? esc(episode.rows_survived) + mark + shorter : "";
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
      view.focus = null;
      setPlaying(false);
    } else if (view.shown.has(button.dataset.player)) view.shown.delete(button.dataset.player);
    else view.shown.add(button.dataset.player);
    renderAll();
  });

  // ---- the mind strip -----------------------------------------------------------------------
  function renderStrip() {
    const strip = $("strip");
    strip.innerHTML = "";
    view.panels = {};
    view.runners = playing().map((episode) => {
      const run = runOf(episode);
      const game = run.game || {};
      const window_ = run.game ? game.window : 3; // 3 only when the run has no game block at all
      const model = (run.models || {})[episode.player];
      const panel = document.createElement("article");
      panel.className = "mind";
      panel.dataset.player = episode.player;
      panel.innerHTML = '<header><span class="label tag">' + esc(Minds.tagOf(episode.player)) + '</span><span class="about">' +
        esc(ABOUT[episode.player] || "") + (model ? " · " + esc(model) : "") + '</span></header><div class="body"><p class="status"></p>' +
        '<div class="decision"></div></div>';
      strip.appendChild(panel);
      view.panels[episode.player] = { panel, status: panel.querySelector(".status"), decision: panel.querySelector(".decision"), index: -1 };
      return { episode, track: store.tracks[String(episode.seed)], lookahead: game.lookahead || 6, window: window_,
               context: { windowMs: run.fly ? run.fly.window_ms : null, window: window_, maxHz: game.looming ? game.looming.max_hz : null } };
    });
    if (!view.runners.length) {
      strip.innerHTML = '<p class="note" style="padding:16px">' + (view.seed == null ? "Nothing has been played yet."
        : "None of the players shown ran track " + esc(view.seed) + ". Pick a player in the level table to show it.") + "</p>";
    }
  }

  $("strip").addEventListener("click", (event) => {
    if (event.target.closest("summary, details")) return;
    const panel = event.target.closest(".mind");
    if (panel) focusOn(panel.dataset.player, true);
  });

  function focusOn(player, manual) {
    if (manual) setAuto(false); // any manual choice turns auto off until it is switched back on
    view.focus = player;
    draw();
  }

  function setAuto(on) {
    view.auto = on;
    view.heldSince = view.t;
    $("auto").setAttribute("aria-pressed", String(on));
  }

  // ---- time ---------------------------------------------------------------------------------
  // how far the clock may run: to the end of the last runner, or in a live run to the newest row
  // that every runner still running has decided
  function horizon() {
    const runners = view.runners;
    if (!runners.length) return 1;
    const ends = runners.map((r) => Timeline.endRow(r.episode));
    if (store.ended) return Math.max(...ends) + TAIL;
    const open = runners.filter((r) => !r.episode.complete).map((r) => Timeline.endRow(r.episode));
    return open.length ? Math.min(...open) : Math.max(...ends) + TAIL;
  }

  function states(t) {
    return view.runners.map((runner) => {
      const state = Timeline.stateAt(runner.episode, t, runner.track.lanes);
      // a live runner that has used up its frames is thinking, not stopped
      if (!store.ended && state.status === "cut") state.status = "running";
      return { id: runner.episode.player, runner, ...state };
    });
  }

  // ---- drawing ------------------------------------------------------------------------------
  const canvas = $("canvas");
  const ctx = canvas.getContext("2d");

  function resize() {
    const wrap = $("tunnel");
    const size = Math.max(280, Math.floor(Math.min(wrap.parentElement.clientWidth, window.innerHeight * 0.72)));
    if (size === view.size) return;
    view.size = size;
    wrap.style.width = wrap.style.height = size + "px";
    const ratio = window.devicePixelRatio || 1;
    canvas.width = canvas.height = size * ratio;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  }

  function draw() {
    const t = still ? Math.floor(view.t) : view.t;
    const size = view.size;
    const all = states(t);
    const track = view.runners.length ? view.runners[0].track : store.tracks[String(view.seed)];
    if (view.auto) {
      const next = Stage.autoFocus(view.focus, all, view.heldSince, t);
      view.focus = next.focus;
      view.heldSince = next.heldSince;
    }
    if (view.focus == null || !all.some((s) => s.id === view.focus)) view.focus = all.length ? all[0].id : null;
    const focused = all.find((s) => s.id === view.focus);

    ctx.clearRect(0, 0, size, size);
    if (track) {
      const maxRows = Math.max(...view.runners.map((r) => r.episode.max_rows || track.max_rows), 0) || track.max_rows;
      const outline = focused ? Tunnel.seenOutline(focused.frame, focused.runner.lookahead, focused.runner.window) : null;
      Tunnel.draw(ctx, size, track, t, maxRows, outline);
      drawRunners(all, track, t, size);
      $("row-label").textContent = "Row " + String(Math.min(Math.floor(t), maxRows)).padStart(4, "0") + " / " + String(maxRows).padStart(4, "0");
      $("track-label").textContent = "Track " + view.seed + (store.game ? " · " + store.game.version : "");
    }

    for (const s of all) {
      const ui = view.panels[s.id];
      const episode = s.runner.episode;
      ui.panel.setAttribute("aria-current", String(s.id === view.focus));
      ui.panel.classList.toggle("fallen", s.status === "dead");
      const status = !store.ended && !episode.complete && s.index === episode.frames.length - 1 && t >= s.frame.landing[0]
        ? "thinking…" : Minds.statusLine(episode, s, s.runner.track.lanes);
      if (ui.status.innerHTML !== status) ui.status.innerHTML = status;
      if (s.index !== ui.index) {
        const open = !!(ui.decision.querySelector("details") || {}).open;
        ui.decision.innerHTML = Minds.mind(episode, s.frame, s.runner.context);
        if (open && ui.decision.querySelector("details")) ui.decision.querySelector("details").open = true;
        ui.index = s.index;
      }
    }
    const end = horizon();
    $("scrub").max = end;
    $("scrub").value = view.t;
    $("clock").textContent = "row " + Math.floor(Math.min(view.t, end));
  }

  function drawRunners(all, track, t, size) {
    const drawn = all.map((s) => ({ s, at: Tunnel.place(s, track.lanes, size, t) })).filter((d) => d.at.visible && d.at.fall < 1);
    const overlap = Stage.overlaps(drawn.map((d) => ({ id: d.s.id, row: d.s.row, lane: d.s.lane })), track.lanes);
    drawn.sort((a, b) => (a.s.id === view.focus) - (b.s.id === view.focus)); // the mind in focus is painted last
    view.hit = [];
    for (const { s, at } of drawn) {
      const name = SPRITE[s.id] || "block";
      const px = Math.max(2, Math.round(size * 0.008 * at.scale));
      const sprite = Sprites.sizeOf(name);
      const o = overlap[s.id];
      ctx.save();
      ctx.translate(at.x, at.y);
      ctx.rotate(at.rotation);
      ctx.globalAlpha = o.alpha * (1 - at.fall);
      const fan = o.fan * sprite.width * px * 0.62;
      ctx.translate(fan, -at.lift + at.fall * size * 0.12);
      Sprites.drawSprite(ctx, name, px, { p: Minds.visorP(s.frame), open: s.air > 0.15 });
      // the tag, upright whatever wall the runner stands on; blue only for the mind in focus. Runners that
      // overlap share one column of tags over the middle of the group, so the tags never overprint.
      const inFocus = s.id === view.focus;
      const text = inFocus ? "[ " + Minds.tagOf(s.id) + " ]" : Minds.tagOf(s.id);
      ctx.font = '12px "JetBrains Mono", ui-monospace, monospace';
      // on a side wall the upright tag lies across the runner's axis, so it must clear half its own width
      const clear = Math.abs(Math.sin(at.rotation)) * (ctx.measureText(text).width / 2);
      ctx.translate(-fan, -(10 * px + 12 + clear + o.stack * 15));
      ctx.rotate(-at.rotation);
      ctx.globalAlpha = 1 - at.fall;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.lineWidth = 3;
      ctx.strokeStyle = "#0A0A0A";
      ctx.strokeText(text, 0, 0);
      ctx.fillStyle = inFocus ? INK.accent : INK.muted;
      ctx.fillText(text, 0, 0);
      ctx.restore();
      view.hit.push({ id: s.id, x: at.x, y: at.y, r: sprite.height * px });
    }
  }

  canvas.addEventListener("click", (event) => {
    const box = canvas.getBoundingClientRect();
    const x = event.clientX - box.left, y = event.clientY - box.top;
    const near = (view.hit || []).map((h) => ({ id: h.id, d: Math.hypot(h.x - x, h.y - y) / h.r })).filter((h) => h.d < 1.6)
      .sort((a, b) => a.d - b.d)[0];
    if (near) focusOn(near.id, true);
  });

  // ---- transport ----------------------------------------------------------------------------
  let lastTick = null;
  function tick(now) {
    if (!view.playing) return;
    const end = horizon();
    view.t = Math.min(end, view.t + ((now - lastTick) / 1000) * view.speed);
    lastTick = now;
    draw();
    if (view.t >= end && store.ended) setPlaying(false);
    else requestAnimationFrame(tick);
  }

  function setPlaying(on) {
    if (on && store.ended && view.t >= horizon()) view.t = 0;
    view.playing = on;
    $("play").textContent = on ? "Pause" : "Play";
    if (on) {
      lastTick = performance.now();
      requestAnimationFrame(tick);
    }
  }

  function follow() { // live, paused at the newest row: show each new row as it arrives
    if (!view.following || view.playing) return;
    setPlaying(true);
  }

  function setFollowing(on) {
    view.following = on;
    $("live").setAttribute("aria-pressed", String(on));
    if (on) { view.t = Math.max(view.t, horizon() - 1); setPlaying(true); }
  }

  function stepRows(rows) {
    setPlaying(false);
    if (liveUrl) setFollowingOff();
    view.t = Math.max(0, Math.min(horizon(), Math.round(view.t) + rows));
    draw();
  }

  function setFollowingOff() {
    view.following = false;
    $("live").setAttribute("aria-pressed", "false");
  }

  function togglePlay() {
    if (view.playing && liveUrl) setFollowingOff();
    setPlaying(!view.playing);
  }

  $("play").addEventListener("click", togglePlay);
  $("back").addEventListener("click", () => stepRows(-1));
  $("forward").addEventListener("click", () => stepRows(1));
  $("speeds").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    view.speed = Number(button.dataset.speed);
    for (const b of $("speeds").querySelectorAll("button")) b.setAttribute("aria-pressed", String(b === button));
  });
  $("scrub").addEventListener("input", (event) => {
    if (liveUrl) setFollowingOff();
    view.t = Number(event.target.value);
    draw();
  });
  $("auto").addEventListener("click", () => { setAuto(!view.auto); draw(); });
  $("live").addEventListener("click", () => setFollowing(!view.following));
  document.addEventListener("keydown", (event) => {
    const typing = event.target instanceof Element && event.target.closest("button, select, input, summary");
    if (typing || event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.key === " ") { event.preventDefault(); togglePlay(); }
    if (event.key === "ArrowLeft") stepRows(-1);
    if (event.key === "ArrowRight") stepRows(1);
    if (event.key === "a" || event.key === "A") { setAuto(!view.auto); draw(); }
    const nth = view.runners[Number(event.key) - 1];
    if (nth) focusOn(nth.episode.player, true);
  });

  // ---- the sections underneath --------------------------------------------------------------
  function renderBelow() {
    const board = store.scoreboard || { columns: [], rows: [], same_seeds: true };
    $("scoreboard").innerHTML = "<thead><tr>" + board.columns.map((c) => "<th>" + esc(c.replace(/_/g, " ")) + "</th>").join("") +
      "</tr></thead><tbody>" + board.rows.map((row) => "<tr>" + board.columns.map((c) =>
        (c === "player" ? "<th>" + cell(row[c]) + "</th>" : "<td>" + cell(row[c]) + "</td>")).join("") + "</tr>").join("") + "</tbody>";
    $("fairness").hidden = board.same_seeds;
    $("board").hidden = !board.rows.length; // a live run has no scoreboard until it ends
    const flyRun = store.runs.find((run) => run.fly && (run.players || []).includes("fly")) || store.runs.find((run) => run.fly);
    $("ours").innerHTML = Minds.ours(flyRun);
    $("runs").innerHTML = store.runs.map((run) => {
      const sha = run.git_sha ? run.git_sha.slice(0, 7) + (run.git_dirty ? ", uncommitted changes" : "") : "unknown commit";
      const status = run.status === "completed" ? "completed" : '<span class="warn">' + esc(run.status || "status unknown") + "</span>";
      return "Run " + esc(run.run_id) + " (" + status + ", " + esc(sha) + ")";
    }).join(" · ");
    const gameRun = store.runs.find((run) => run.game);
    $("sight").innerHTML = gameRun
      ? "Every runner gets the same track and is shown the same " + esc(gameRun.game.lookahead) + " rows ahead, " +
        esc(gameRun.game.window) + " lanes either side."
      : "Every runner gets the same track and is shown the same rows ahead.";
  }

  function renderAll() {
    renderMatrix();
    renderStrip();
    renderBelow();
    resize();
    draw();
  }

  // ---- start --------------------------------------------------------------------------------
  let ready = false;
  Feed.fromEmbedded(embedded, handlers);
  chooseDefaults();
  $("empty").hidden = true;
  $("app").hidden = false;
  $("transport").hidden = false;
  $("mode").textContent = liveUrl ? "Live" : "Replay";
  $("live").hidden = !liveUrl;
  ready = true;
  renderAll();
  window.addEventListener("resize", () => { resize(); draw(); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw); // the canvas tags use the embedded mono
  if (liveUrl) {
    notice("Waiting for the first decision…", false);
    const clear = handlers.onFrame;
    // a frame means the stream is alive: the waiting or the lost-connection notice goes, a real error stays
    handlers.onFrame = (...args) => { if (store.error == null) notice(null); clear(...args); };
    Feed.fromStream(liveUrl, handlers);
  }
})();

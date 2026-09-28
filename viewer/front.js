// Brain Battle, the front of `bakeoff live`: home, the character select, the track select, results and
// records around the run screen (#app, app.js). Glue only: the rules are in screens.js, select.js,
// trackpick.js, results.js and records.js, which have tests. It talks to the server through the control
// routes (GET /state, POST /run, POST /cancel, GET /results, /records, /replay), every request carrying the
// session's token, and drives the run screen through window.Race. A replay file has no server and no front.
(function (root) {
  "use strict";

  const liveUrl = document.body.dataset.live || null;
  if (!liveUrl) return; // a replay file: no server, no front, the two tabs as before

  const $ = (id) => document.getElementById(id);
  const token = document.body.dataset.token || null;
  const rosterSlot = document.getElementById("roster-data");
  const roster = (rosterSlot && JSON.parse(rosterSlot.textContent)) || [];
  const looks = Roster.make(roster);

  // the pixel brain behind the logo (the approved home mock-up); its rows are padded to one width
  const BRAIN = ["..........BBBBBBBBB", "......BBBBBBBBBBBBBBBBB", "....BBBBBBBBBBBBBBBBBBBBB", "...BBBBBBBBBBBBBBBBBBBBBBBB",
    "..BBBBBBBBBBBBBBBBBBBBBBBBBB", ".BBBBBBBBBBBBBBBBBBBBBBBBBBBB", ".BBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", ".BBBBBBBBBBBBBBBBBBBBBBBBBBBB", ".BBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    "..BBBBBBBBBBBBBBBBBBBBBBBBBB", "...BBBBBBBBBBBBBBBBBBBBBBBB", ".....BBBBBBBBBBBBBBBBBBBBBB",
    ".................BBBBBBBBBBB", "..................BBBBBBBBB", "....................BBB", "....................BBB"];
  const ACCENT = "#7AA2F7"; // --accent: the brain is the one use of blue that is not the cursor (docs/FRONTEND.md)

  const front = {
    screen: "home", from: "home", state: null, sel: Select.make(roster, []), seed: null, armed: false, refusal: null,
    timer: null, leaving: false, starting: false, cancelError: null, notice: null, armedAt: 0,
    results: null, more: false, autoResults: false, // the results on screen, and whether the run's end opens them
    records: null, allRuns: false, // the past runs on screen
    charts: null, pair: [], // the charts on screen, and the two players compared
  };

  async function control(path, options) {
    const settings = options || {};
    try {
      const response = await fetch(path, { ...settings, headers: { "X-Bakeoff-Token": token, ...(settings.headers || {}) } });
      const body = await response.json().catch(() => ({ error: "the server answered something that is not JSON" }));
      return { ok: response.ok, body };
    } catch (e) { // the command was stopped, or the machine went to sleep
      return { ok: false, body: { error: "no answer from the run: is `bakeoff live` still going?" } };
    }
  }

  // Every empty sprite canvas under `el` gets its fighter, in its skin. The fly shows its wings open, as on the
  // approved screens. A portrait is not a decision, so Jev's slit is no gauge here: it is lit as the mock-ups
  // light it (three cells), and the Map skin shows its blue; only the tunnel's slit reads Jev's probability.
  const PORTRAIT_P = 0.6;
  function paintSprites(el) {
    for (const canvas of el.querySelectorAll("canvas.sprite[data-player]")) {
      const look = looks.look(canvas.dataset.player);
      const p = look.sprite === "visor" && !(look.inks || {}).V ? PORTRAIT_P : null;
      Sprites.paint(canvas, look.sprite, Number(canvas.dataset.px) || 4,
                    { color: look.color, inks: look.inks, open: look.sprite === "fly", p });
    }
  }

  // ---- the screens ---------------------------------------------------------------------------------
  // Answers the lookup of the track it started, if it started one (entering the track screen with a state for
  // another track), so a caller can wait for it.
  function show(screen) {
    const next = Screens.select(front.screen, screen);
    if (next === "records" && front.screen !== "records") front.from = front.screen;
    if (next !== front.screen) { // a confirmation, a refusal or a message belongs to the screen it was shown on
      front.armed = false;
      front.refusal = null;
      front.cancelError = null;
      front.notice = null;
    }
    front.screen = next;
    for (const s of Screens.stateOf(next)) {
      const el = s.name === "run" ? $("app") : $("screen-" + s.name);
      if (el) el.hidden = s.hidden;
    }
    $("front").hidden = next === "run";
    Race.setShown(next === "run");
    render();
    window.scrollTo(0, 0);
    if (next === "track" && front.state && front.state.seed !== front.seed) return refreshState();
    return null;
  }

  function render() {
    if (front.screen === "home") renderHome();
    if (front.screen === "select") renderSelect();
    if (front.screen === "track") renderTrack();
    if (front.screen === "results") renderResults();
    if (front.screen === "records") renderRecords();
    if (front.screen === "charts") renderCharts();
    renderRunBar();
  }

  // ---- home ------------------------------------------------------------------------------------------
  function paintBrain() {
    const canvas = $("brain"), px = 18, width = Math.max(...BRAIN.map((row) => row.length));
    canvas.width = width * px;
    canvas.height = BRAIN.length * px;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = ACCENT;
    BRAIN.forEach((row, y) => { for (let x = 0; x < row.length; x++) if (row[x] === "B") ctx.fillRect(x * px, y * px, px, px); });
  }

  function renderHome() {
    const state = front.state;
    $("home-where").textContent = location.host + (state ? " · ceiling " + state.max_requests + " requests" : "");
    $("home-game").textContent = state ? "Game " + state.game.version + " · " + state.max_rows + " rows" : "";
    // the four contestants, each in its default skin; the yardsticks are not on the title screen
    $("home-fighters").innerHTML = roster.filter((c) => c.id !== "bot").map((c, i) =>
      '<figure><span class="bob" style="animation-delay:' + (i * 0.2).toFixed(1) + 's"><canvas class="sprite" data-player="' +
      Minds.esc(c.skins[0].player) + '" data-px="8"></canvas></span><figcaption class="label">' + Minds.esc(c.name) +
      "</figcaption></figure>").join("");
    paintSprites($("home-fighters"));
  }

  $("launch").addEventListener("click", () => show("select"));

  // ---- the character select ------------------------------------------------------------------------
  function renderSelect() {
    const sel = front.sel;
    $("select-count").textContent = sel.slots.length + " / " + Select.MAX + " runners";
    $("portraits").innerHTML = Select.portraitsHtml(sel, roster);
    $("slots").innerHTML = Select.slotsHtml(sel, roster);
    $("select-info").innerHTML = Select.infoHtml(sel, roster, front.state ? front.state.players : []);
    $("fight").hidden = !Select.ready(sel);
    $("not-ready").hidden = Select.ready(sel);
    paintSprites($("portraits"));
    paintSprites($("slots"));
  }

  function setSel(sel) {
    front.sel = sel;
    front.armed = false; // another lineup: another worst case to confirm
    renderSelect();
  }

  $("portraits").addEventListener("click", (event) => {
    const portrait = event.target.closest("button[data-char]");
    if (portrait) setSel(Select.add(front.sel, roster, Number(portrait.dataset.char)));
  });
  $("slots").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.dataset.remove != null) setSel(Select.remove(front.sel, Number(button.dataset.remove)));
    else if (button.dataset.skin != null) setSel(Select.setSkin(front.sel, Number(button.dataset.slot), Number(button.dataset.skin)));
    else if (button.dataset.focus != null) setSel(Select.focusSlot(front.sel, Number(button.dataset.focus)));
  });
  $("fight").addEventListener("click", () => { if (Select.ready(front.sel)) show("track"); });

  // ---- the track select ------------------------------------------------------------------------------
  const players = () => Select.players(front.sel, roster);

  function renderTrack() {
    const state = front.state;
    if (!state) return;
    const seed = front.seed;
    const fresh = state.seed === seed; // the state answers for the track on screen, not the one before
    $("track-game").textContent = "Run · game " + state.game.version + " · " + state.max_rows + " rows";
    $("seed-rule").textContent = state.held_out ? "Held-out seeds are open (--held-out)"
      : "Practice seeds are " + state.first_practice_seed + " and up";
    $("seed-shown").textContent = seed;
    $("preview-what").textContent = "The track, row 0 to " + state.max_rows;
    $("preview").innerHTML = fresh ? TrackPick.previewSvg(state.track, state.game) : "";
    $("preview-gaps").textContent = fresh && state.track ? TrackPick.gapTiles(state.track) + " gap tiles" : "";
    $("tiles").innerHTML = TrackPick.tilesHtml(TrackPick.tiles(state, players(), seed));
    $("ceiling").textContent = Lobby.ceilingText(state);
    $("lineup").innerHTML = TrackPick.lineupHtml(TrackPick.lineup(state, roster, players()));
    paintSprites($("lineup"));
    $("total").textContent = Lobby.usd(Lobby.estimate(state, players()).total_usd);
    $("cap").textContent = TrackPick.capText(state, players());
    const button = TrackPick.runButton(state, players(), seed, front.armed);
    const why = front.refusal || button.why || (fresh ? null : "Looking up track " + seed + "…");
    $("run-why").hidden = !why;
    $("run-why").textContent = why || "";
    $("run").disabled = !!why;
    $("run").dataset.armed = String(button.armed);
    $("run-label").textContent = button.label;
    $("run-sub").textContent = button.sub;
  }

  function setSeed(seed) {
    if (!front.state) return;
    front.seed = TrackPick.clampSeed(seed, front.state);
    front.armed = false; // another track: another worst case to confirm
    front.refusal = null;
    renderTrack();
    clearTimeout(front.timer);
    front.timer = setTimeout(refreshState, 250);
  }

  const CONFIRM_AFTER_MS = 500;
  // RUN: a lineup that can spend is confirmed once, with its worst case on the button; then it starts.
  function pressedRun() {
    const state = front.state;
    if (front.starting) return; // a POST /run is on its way: a second press neither re-arms nor posts again
    if (!state || state.seed !== front.seed || Lobby.whyNot(state, players(), front.seed)) return;
    if (Lobby.spends(state, players()) && !front.armed) {
      front.armed = true;
      front.armedAt = Date.now();
      return renderTrack();
    }
    // a confirmation is a second, separate press: one that follows the arming this closely is the same press
    // repeating (a held key on a focused button, a double click), so it does not spend
    if (front.armed && Date.now() - front.armedAt < CONFIRM_AFTER_MS) return;
    startRun();
  }

  async function startRun() {
    front.armed = false;
    front.refusal = null;
    front.starting = true;
    let answer;
    try {
      answer = await control("/run", { method: "POST", headers: { "Content-Type": "application/json" },
                                       body: JSON.stringify({ seed: front.seed, players: players() }) });
    } finally {
      front.starting = false;
    }
    const { ok, body } = answer;
    if (!ok) { // refused: say why, and look again (a run may be going, started from another tab)
      front.refusal = body.error || "the run was refused";
      render();
      return refreshState();
    }
    applyState(body.state, body.run_id);
  }

  $("seed-prev").addEventListener("click", () => setSeed(front.seed - 1));
  $("seed-next").addEventListener("click", () => setSeed(front.seed + 1));
  $("seed-random").addEventListener("click", () => setSeed(TrackPick.randomSeed(front.state, Math.random)));
  $("tiles").addEventListener("click", (event) => {
    const tile = event.target.closest("button[data-seed]");
    if (tile) setSeed(Number(tile.dataset.seed));
  });
  $("run").addEventListener("click", pressedRun);

  // ---- the run screen's bar ------------------------------------------------------------------------
  const running = () => !!front.state && front.state.status === "running";

  // The bar describes the run on screen: this session's run while it is watched, or a recorded run loaded
  // from Records (Race.watching() is null then), which has no Cancel and no results of its own here.
  function renderRunBar() {
    const watched = Race.watching();
    const session = front.state && front.state.run;
    const run = watched != null && session && session.run_id === watched ? session : null;
    $("run-bar").hidden = false;
    $("run-what").textContent = watched == null ? "Replay · a recorded run"
      : run ? "Track " + run.seed + (running() ? " · live" : " · " + run.status) : "";
    $("run-error").hidden = !front.cancelError;
    $("run-error").textContent = front.cancelError || "";
    $("run-cancel").hidden = !(run && running());
    $("run-home").textContent = front.leaving ? "Home? The run keeps going" : "‹ Home";
    // the results of the run on screen, for a viewer who scrubbed back and was not taken there
    $("run-results").hidden = !(front.results && !front.results.why && run && front.results.run_id === run.run_id && !running());
  }

  // Going home does not cancel the run, so while one is going the first press says so and the second goes.
  function goHome() {
    if (running() && !front.leaving) { front.leaving = true; return renderRunBar(); }
    front.leaving = false;
    show("home");
  }
  $("run-home").addEventListener("click", goHome);
  $("run-cancel").addEventListener("click", async () => {
    front.cancelError = null;
    const { ok, body } = await control("/cancel", { method: "POST" });
    if (ok && body.state) return applyState(body.state);
    if (!ok) { front.cancelError = "The run could not be cancelled: " + (body.error || "no reason given"); renderRunBar(); }
  });

  $("run-results").addEventListener("click", () => show("results"));

  // ---- results --------------------------------------------------------------------------------------
  function renderResults() {
    const results = front.results;
    $("results-why").hidden = !(results && results.why);
    $("results-why").textContent = results && results.why ? results.why : "";
    if (!results || results.why) {
      for (const id of ["cards", "numbers", "failures"]) $(id).innerHTML = "";
      return;
    }
    const head = Results.header(results);
    $("results-left").textContent = head.left;
    $("results-right").textContent = head.right;
    const more = front.more;
    $("cards").innerHTML = Results.cardsHtml(Results.cards(results, roster), more);
    $("cards").dataset.count = String(Math.min(4, results.players.length));
    paintSprites($("cards"));
    $("numbers-title").textContent = more ? "The numbers" : "How far each got";
    $("results-warning").textContent = Results.warning(results, roster);
    $("more").textContent = more ? "Fewer numbers" : "More numbers";
    $("more").setAttribute("aria-expanded", String(more));
    $("numbers").innerHTML = more ? Results.tableHtml(Results.table(results, roster))
      : Results.barsHtml(Results.bars(results, roster), looks.colour);
    const failures = more ? Results.failures(results, roster) : [];
    $("failures").innerHTML = failures.map((line) => '<p class="warn small">' + Minds.esc(line) + "</p>").join("");
    $("results-note").hidden = !more;
    $("results-note").textContent = Results.note(results, roster);
    $("results-refusal").hidden = !front.notice;
    $("results-refusal").textContent = front.notice || "";
  }

  // The lineup and track of the results on screen, for Run again, New track and Fighters: a past run's
  // results start from its own lineup, as the run just played does.
  function takeLineup() {
    const results = front.results;
    if (!results || results.why) return;
    front.sel = Select.make(roster, results.players.map((p) => p.player));
    if ((results.seeds || []).length) { // a past run's track, kept to the seeds this session may play
      front.seed = front.state ? TrackPick.clampSeed(results.seeds[0], front.state) : results.seeds[0];
    }
    front.armed = false;
    front.refusal = null;
  }

  async function goTrack() {
    takeLineup();
    await (show("track") || refreshState()); // show looks the track up itself when the state is for another
  }

  $("more").addEventListener("click", () => { front.more = !front.more; renderResults(); });
  $("again").addEventListener("click", async () => { await goTrack(); pressedRun(); }); // straight to RUN's confirmation
  $("new-track").addEventListener("click", goTrack);
  $("to-fighters").addEventListener("click", () => { takeLineup(); show("select"); });
  // Loading a recorded run closes this session's live stream, so while its run is going it is watched first.
  const WATCH_LIVE_FIRST = "This session's run is still going: watch it live first (Records, playing now). " +
    "Recorded runs can be watched once it ends.";

  $("watch-replay").addEventListener("click", async () => {
    const results = front.results;
    if (results && Race.watching() !== results.run_id) { // a past run's results: load that run first
      if (running()) { front.notice = WATCH_LIVE_FIRST; return renderResults(); }
      const { ok, body } = await control("/replay?run=" + encodeURIComponent(results.run_id));
      if (!ok) { results.why = body.error || "the replay could not be read"; return renderResults(); }
      Race.load(body);
      front.autoResults = false; // the session run's results are not this replay's
    }
    show("run");
    Race.rewind();
  });
  $("results-records").addEventListener("click", openRecords);
  $("results-home").addEventListener("click", () => show("home"));

  async function openResults(runId) {
    const { ok, body } = await control("/results?run=" + encodeURIComponent(runId));
    front.results = ok ? body : { why: body.error || "the results could not be read" };
    front.autoResults = false;
    front.more = false;
    show("results");
  }

  // ---- records --------------------------------------------------------------------------------------
  async function openRecords() {
    show("records");
    const { ok, body } = await control("/records");
    front.records = ok ? body : { why: body.error || "the records could not be read", runs: [] };
    renderRecords();
  }

  function renderRecords() {
    const records = front.records;
    $("records-back").textContent = front.from === "results" ? "‹ Results" : "‹ Home";
    if (!records) return;
    $("records-why").hidden = !records.why;
    $("records-why").textContent = records.why || "";
    const past = Records.pastRuns(records, roster, front.allRuns);
    $("past").innerHTML = Records.runsHtml(past.rows);
    $("all-runs").hidden = past.total <= Records.SHOWN_RUNS;
    $("all-runs").textContent = front.allRuns ? "Show the newest " + Records.SHOWN_RUNS : "Show all " + past.total;
    $("ours").innerHTML = Minds.ours(records.ours);
    $("ours-fly2").innerHTML = Minds.oursFly2(records.ours);
    $("honesty-fly2").hidden = !(records.ours && records.ours.fly2);
  }

  $("open-records").addEventListener("click", openRecords);
  $("all-runs").addEventListener("click", () => { front.allRuns = !front.allRuns; renderRecords(); });
  $("past").addEventListener("click", async (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.dataset.results) return openResults(button.dataset.results);
    if (button.dataset.now) { // this session's run, playing now: the stream is already this page's
      await refreshState();
      return show("run");
    }
    if (running()) { front.records.why = WATCH_LIVE_FIRST; return renderRecords(); }
    const { ok, body } = await control("/replay?run=" + encodeURIComponent(button.dataset.watch));
    if (!ok) { front.records.why = body.error || "the replay could not be read"; return renderRecords(); }
    Race.load(body);
    front.autoResults = false; // the session run's results are not this replay's
    show("run");
  });
  const setOurs = (open) => {
    $("ours-panel").hidden = !open;
    $("ours-toggle").setAttribute("aria-expanded", String(open));
  };
  $("ours-toggle").addEventListener("click", () => setOurs($("ours-panel").hidden));
  $("ours-close").addEventListener("click", () => setOurs(false));

  // ---- charts ---------------------------------------------------------------------------------------
  // Every recorded track of this game, each player and track once (GET /charts): the leaderboard and the head to
  // head on top, the benchmark's tables and trade-off charts below them, drawn by the one renderer (bench_view.js).
  async function openCharts() {
    show("charts");
    const { ok, body } = await control("/charts");
    front.charts = ok ? body : { why: body.error || "the charts could not be read", bench: null };
    const chips = ok ? Records.chips(front.charts, roster) : [];
    if (front.pair.length !== 2 && chips.length) front.pair = [chips[0].a, chips[0].b];
    renderCharts();
    if (front.charts.bench) BenchView.mount($("charts-bench"), front.charts.bench);
    $("charts-bench").hidden = !front.charts.bench;
  }

  function renderCharts() {
    const charts = front.charts;
    if (!charts) return;
    $("charts-why").hidden = !charts.why;
    $("charts-why").textContent = charts.why || "";
    $("charts-scope").textContent = charts.tracks ? "game " + charts.game + " · every recorded track, " + charts.tracks[0] +
      "–" + charts.tracks[1] + " · held out " + charts.held_out[0] + "–" + charts.held_out[1] : "";
    $("board-title").textContent = charts.game == null ? "" : "Mean rows · each player on the tracks it ran";
    $("leaderboard").innerHTML = Records.boardHtml(Records.board(charts, roster), front.pair);
    $("board-notes").innerHTML = Records.boardNotes(charts, roster).map((n) => '<p class="warn small">' + Minds.esc(n) + "</p>").join("");
    const [a, b] = front.pair;
    $("chips").innerHTML = Records.chipsHtml(Records.chips(charts, roster), a, b);
    const pair = a && b ? Records.pairOf(charts, a, b) : null;
    $("pair").innerHTML = pair ? Records.pairHtml(Records.pairView(pair, roster, charts.max_rows))
      : '<p class="muted small">Pick two players to compare them on the tracks both played.</p>';
  }

  $("open-charts").addEventListener("click", openCharts);
  $("leaderboard").addEventListener("click", (event) => { // two rows make a pair: a third starts a new one
    const row = event.target.closest("button[data-player]");
    if (!row) return;
    const player = row.dataset.player;
    front.pair = front.pair.length === 1 && front.pair[0] !== player ? [front.pair[0], player] : [player];
    renderCharts();
  });
  $("chips").addEventListener("click", (event) => {
    const chip = event.target.closest("button[data-a]");
    if (chip) { front.pair = [chip.dataset.a, chip.dataset.b]; renderCharts(); }
  });

  // ---- keys and Back -------------------------------------------------------------------------------
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-back]")) show(Screens.back(front.screen, front.from));
  });
  document.addEventListener("keydown", (event) => {
    // a held Enter is one press: its repeats would walk through RUN's confirmation (select → track → arm → post),
    // and on a focused button the browser would click it once per repeat, so that default is stopped too.
    // Held arrows keep stepping seeds and portraits.
    if (event.repeat && event.key === "Enter") { event.preventDefault(); return; }
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (front.screen === "run") { // the race has its own keys (app.js); Escape is ‹ Home
      if (event.key === "Escape") { event.preventDefault(); goHome(); }
      return;
    }
    if (front.screen === "records" && event.key === "Escape" && !$("ours-panel").hidden) {
      event.preventDefault();
      return setOurs(false); // an open "What is ours" closes first
    }
    // a focused button already answers Enter and Space with a click; typing in a field is not a command
    if (event.target instanceof Element && event.target.closest("input, select, textarea") ||
        (event.target instanceof Element && event.target.closest("button") && (event.key === "Enter" || event.key === " "))) return;
    let out = null;
    if (front.screen === "home") {
      if (event.key === "Enter") out = { go: "select" };
    } else if (front.screen === "select") {
      out = Select.onKey(front.sel, roster, event.key);
      if (out && out.sel !== front.sel) setSel(out.sel);
    } else if (front.screen === "track" && front.state) {
      out = TrackPick.onKey(front.seed, front.state, event.key, Math.random);
      if (out && out.seed !== front.seed) setSeed(out.seed);
      if (out && out.go === "run") { pressedRun(); out = { go: null }; }
    } else if (event.key === "Escape") {
      out = { go: "back" };
    }
    if (!out) return;
    event.preventDefault();
    if (out.go === "back") show(Screens.back(front.screen, front.from));
    else if (out.go) show(out.go);
  });

  // ---- the state ------------------------------------------------------------------------------------
  async function refreshState() {
    const seed = front.seed == null ? "" : String(front.seed);
    const { ok, body } = await control("/state?seed=" + encodeURIComponent(seed));
    if (!ok) { front.refusal = body.error; return render(); }
    applyState(body);
  }

  // `started`: the run this page just started, watched even when it is already over (free players can finish
  // a track before the answer to POST /run arrives).
  function applyState(state, started) {
    const first = front.state == null;
    if (first) { // the first answer: the select opens with what the command line offered
      front.sel = Select.make(roster, (state.ready || {}).players || []);
      front.seed = (state.ready || {}).seed != null ? state.ready.seed : state.first_practice_seed;
    }
    front.state = state;
    const run = state.run;
    // a run that is going and not watched yet: this page started it, or the command line did (--start), or
    // the page was reloaded while it ran. Watch it, on the run screen.
    if (run && run.replay && (state.status === "running" || run.run_id === started) && Race.watching() !== run.run_id) {
      Race.watch(run);
      front.leaving = false;
      return show("run");
    }
    if (first && front.seed !== state.seed) return refreshState(); // the state for the track on screen
    render();
  }

  // app.js calls this when a run has ended, with its end event: the results arrive with it, and open by
  // themselves once the tunnel on screen has shown the last row (reachedEnd). A viewer who scrubbed back is
  // not pulled away: the bar offers "Results" instead.
  function ended(end) {
    front.leaving = false;
    // the results belong to the run whose stream ended, the one watched
    front.results = { run_id: Race.watching(), ...(end.results || { why: "the run ended without results" }) };
    front.more = false;
    front.autoResults = true;
    refreshState();
    if (Race.atEnd()) reachedEnd();
  }

  function reachedEnd() {
    // only the results of the run on screen open by themselves, never over a replay of another run
    if (!front.autoResults || front.screen !== "run" || !front.results || front.results.run_id !== Race.watching()) return;
    front.autoResults = false;
    setTimeout(() => { if (front.screen === "run") show("results"); }, 1200); // a moment on the last fall first
  }

  // app.js calls this once the run screen is ready (live only).
  function start() {
    paintBrain();
    $("ours-slot").appendChild($("honesty")); // the whole "what is ours" section, moved into Records unchanged
    show("home");
    refreshState();
  }

  root.Front = { start, ended, reachedEnd };
})(typeof window !== "undefined" ? window : globalThis);

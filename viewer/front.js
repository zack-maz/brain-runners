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
    timer: null, leaving: false,
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
  function show(screen) {
    const next = Screens.select(front.screen, screen);
    if (next === "records" && front.screen !== "records") front.from = front.screen;
    front.screen = next;
    for (const s of Screens.stateOf(next)) {
      const el = s.name === "run" ? $("app") : $("screen-" + s.name);
      if (el) el.hidden = s.hidden;
    }
    $("front").hidden = next === "run";
    Race.setShown(next === "run");
    render();
    window.scrollTo(0, 0);
  }

  function render() {
    if (front.screen === "home") renderHome();
    if (front.screen === "select") renderSelect();
    if (front.screen === "track") renderTrack();
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
    $("select-count").textContent = sel.slots.length + " / " + Select.MAX + " fighters";
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
    $("seed-rule").textContent = state.tournament ? "Tournament seeds are open (--tournament)"
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

  // RUN: a lineup that can spend is confirmed once, with its worst case on the button; then it starts.
  function pressedRun() {
    const state = front.state;
    if (!state || state.seed !== front.seed || Lobby.whyNot(state, players(), front.seed)) return;
    if (Lobby.spends(state, players()) && !front.armed) {
      front.armed = true;
      return renderTrack();
    }
    startRun();
  }

  async function startRun() {
    front.armed = false;
    front.refusal = null;
    const { ok, body } = await control("/run", { method: "POST", headers: { "Content-Type": "application/json" },
                                                 body: JSON.stringify({ seed: front.seed, players: players() }) });
    if (!ok) { front.refusal = body.error || "the run was refused"; return render(); }
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

  function renderRunBar() {
    const run = front.state && front.state.run;
    $("run-bar").hidden = false;
    $("run-what").textContent = run ? "Track " + run.seed + (running() ? " · live" : " · " + run.status) : "";
    $("run-cancel").hidden = !running();
    $("run-home").textContent = front.leaving ? "Home? The run keeps going" : "‹ Home";
  }

  // Going home does not cancel the run, so while one is going the first press says so and the second goes.
  $("run-home").addEventListener("click", () => {
    if (running() && !front.leaving) { front.leaving = true; return renderRunBar(); }
    front.leaving = false;
    show("home");
  });
  $("run-cancel").addEventListener("click", async () => {
    const { ok, body } = await control("/cancel", { method: "POST" });
    if (ok && body.state) applyState(body.state);
  });

  // ---- keys and Back -------------------------------------------------------------------------------
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-back]")) show(Screens.back(front.screen, front.from));
  });
  document.addEventListener("keydown", (event) => {
    if (front.screen === "run" || event.metaKey || event.ctrlKey || event.altKey) return;
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

  // app.js calls this when a run has ended: the state says so, and the bar stops offering Cancel.
  function ended() {
    front.leaving = false;
    refreshState();
  }

  // app.js calls this once the run screen is ready (live only).
  function start() {
    paintBrain();
    show("home");
    refreshState();
  }

  root.Front = { start, ended };
})(typeof window !== "undefined" ? window : globalThis);

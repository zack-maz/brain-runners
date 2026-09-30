# Update 3b: the rest of the page — the logs, the two tabs and the player picker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the page becomes the whole tool. Every mind panel carries a running log of what its player was asked, what it answered and how long it took; the page splits into a Run tab (the tunnel, the strip, the lobby, the transport) and an Analysis tab (the levels, the scoreboard, what is ours, the benchmark); and one player picker over the tunnel governs who is in it, so no two controls can disagree. A live run's own benchmark arrives with its last event, so the Analysis tab fills in without a reload.

**Architecture:** three new pure JavaScript modules, each tested under `node --test`: `viewer/log.js` builds one line per row from a frame the strip already has; `viewer/tabs.js` is the two tabs as a rule (which tab is in focus, what each button and panel should be, arrow keys); `viewer/picker.js` is who is in the tunnel (the buttons, the hint, the toggle, with a player that did not run the track in view unable to be turned on). `viewer/app.js` does the DOM and the wiring, as always. The benchmark's drawing moves out of `viewer/bench_app.js` into `viewer/bench_view.js`, a renderer mounted into a container, used by both `bench.html` and the Analysis tab, so there is one drawing code. On the Python side `bakeoff/bench.py` gains `benchmark_of(run_dirs) -> (numbers | None, why | None)`, which answers with a reason instead of failing; `bakeoff/view.py` gains a second data slot (`bench-data`) and `bakeoff/__main__.py` fills it when it writes a page; `bakeoff/live.py` scores the run it just played and sends the numbers with the `end` event.

**Tech Stack:** Python 3.13, `uv`, `pytest`; plain JavaScript with `node --test` (run by `uv run pytest` through `tests/test_viewer_js.py`). Standard library only: no new dependency, no build step, no npm package.

**Spec:** `docs/superpowers/specs/2026-09-22-page-control-design.md`, sections D, E and F (binding). Background: `docs/DECISIONS.md` decisions 35, 36 and 37; `docs/UPDATES.md` items 4, 8, 9. Update 3a (the control channel, the session ceiling and the lobby) is already built and is **not** in scope here.

**Branch:** `phase6-updates` (already checked out; never build on `main`).

## Global Constraints

- Python via `uv` only: `uv run pytest`, `uv run python -m ...`. Python 3.13. Never call `pip` or bare `python`. No `uv add`.
- TDD: write the failing test, watch it fail, then implement. **No test touches the network**: every test here uses free players (`solver`, `random`, and the fakes in `tests/fakes.py`), and the only connections are to the loopback server under test.
- **This plan spends no money.** No `--max-requests` on a real command, no `pytest -m live`, no `pytest -m slow`, no `bakeoff run`/`live` with a paid player or the fly. A paid or fly run is the controller's and the user's alone.
- **A guard blocks every shell command that contains the text `.env`.** Never put it in a command.
- **Frozen:** the players, the game, the fly, the senses and the step record (`schema_version` stays 1); `runner.play_row` and `replay.frame_of` stay the one source of a live run's records and frames; the response cache and every cache key; the benchmark's arithmetic in `bakeoff/bench.py` (only `benchmark_of` is added).
- **Viewer rules:** plain JavaScript, no build step, no npm packages; the page loads nothing from the network; everything that comes from a log or from the server (a player name, an answer, a refusal) goes through `Minds.esc` before it becomes markup. Rules of the game stay in Python.
- **The page is the user's brand:** tokens from `viewer/viewer.css`, blue only for the cursor (the mind in focus and its tiles), mono for short labels only, deaths and errors `--bad`, warnings `--warn`. Add no colour of your own.
- Every code block below was run in a prototype and passes as written (final state: 429 fast tests, 9 deselected; 27 new JavaScript tests). If a test fails, suspect a transcription slip before redesigning.
- Commit after every task with the message given. The controller pre-writes each message to a file, attribution trailers included; the implementer runs exactly `git commit -F <that file>`, never `-m`, and checks `git log -1 --format=%B` afterwards.

## Decisions this plan makes beyond the spec

1. **A log line is built from a frame, never streamed.** Everything a line shows is already in the frame the strip has, so a log is the same in a replay and in a live run, and nothing new is recorded.
2. **Lines are appended, not re-rendered.** `appendLog` adds only the frames the panel has not logged yet and keeps the scroll where it was unless the reader was at the bottom, so a live log can be read while it grows.
3. **One log is open at a time.** Opening a panel's log closes the others, and the open one survives a re-render of the strip (`view.openLog`).
4. **What a line says** is: the row, what it was asked (a question set's count, or "one prompt" for an LLM), what it answered (the fly's eye rates, turn and jump signals and spike count; a written reply's first 64 characters; or how sure it was about the move it picked), the latency or `cached`, the move and why the game ran a different one, and any error in `--bad`.
5. **The tabs are a rule, not a router.** Plain buttons over one page, no navigation and no history; the tab in focus is remembered while the page is open and nowhere else. The transport hides off the Run tab, and the canvas is sized and drawn when the Run tab comes back, because it cannot be sized while it is hidden.
6. **The level table no longer toggles players** (decision 37). It keeps its track buttons, and picking a track returns to the Run tab, where the track is watched. The picker is the one control over who is in the tunnel, so the two can never disagree.
7. **A player that did not run the track in view can never be turned on**, whatever is clicked: the button is disabled and says "not on this track", and `Picker.toggle` refuses it as well.
8. **One drawing code for the benchmark** (decision 36): `viewer/bench_view.js` is a renderer mounted into a container; `bench_app.js` keeps only what the standalone page does (read the slot, mount, say why there is nothing).
9. **The benchmark is drawn when it is looked at**, and again when the numbers change: `renderBench` does nothing off the Analysis tab or for numbers already drawn.
10. **A page asks for numbers it may not be able to have.** `benchmark_of` returns `(None, why)` for a run that never ended or runs of two lengths, and the page prints the reason; `bakeoff bench` still refuses loudly.
11. **A live run's numbers come from the server** (decision 36): `LiveRun._end_event` scores the run directory it just played and sends `bench` with the `end` event, so the Analysis tab fills in without a reload. One track is rarely enough for an interval, and the numbers say so themselves.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `viewer/log.js` | one line per row of a mind's log (pure) | 1 |
| `viewer/app.js`, `viewer/index.html`, `viewer/viewer.css` | the log in every panel, one open at a time, appended as frames arrive | 2 |
| `viewer/tabs.js`, `viewer/picker.js` | the two tabs and who is in the tunnel (pure) | 3 |
| `viewer/bench_view.js`, `viewer/bench_app.js`, `viewer/bench.html` | one drawing code for the benchmark | 3 |
| `bakeoff/bench.py`, `bakeoff/view.py`, `bakeoff/__main__.py` | `benchmark_of`, the `bench-data` slot, `view` filling it | 3 |
| `bakeoff/live.py` | the `end` event carries the benchmark of what was just played | 4 |
| `CLAUDE.md`, `docs/UPDATES.md` | what the page now does | 5 |

### Task 1: A mind's running log, one line per row (pure)

**Files:**
- Create: `viewer/log.js`
- Test: `viewer/tests/log.test.js`

**Interfaces:**
`viewer/log.js` exposes `Log` (and `module.exports` under node): `asked(episode, frame)`, `answered(episode, frame)`, `move(frame)`, `timing(frame)`, `line(episode, frame)`, `lines(episode, frames)`, `short(text)`.
- `line` returns one `<li>` with `.at` (the row, padded to four digits), `.did` (the move, with a `.warn` span when the game ran a different one), `.said` (what it was asked · what it answered · the timing) and, when the frame has one, a `.bad` span with the error.
- `lines` joins them oldest first, so the newest line is at the bottom.
- Nothing here touches the DOM: it builds strings, which is why `node --test` can run it. It requires `./minds.js` for `esc` under node and reads `root.Minds` in the browser.

The fly's line is its read-out (eye rates, turn and jump signals, spike count) because it is asked nothing. A written answer is cut at 64 characters with an ellipsis; the whole of it stays in the panel above.

- [ ] **Step 1: Write the failing tests**

Create `viewer/tests/log.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const { asked, answered, move, timing, line, lines, short } = require("../log.js");

const composed = { player: "jev_composed", questions: [{ gap_left: {}, gap_stay: {}, gap_right: {}, gap_jump: {} }] };
const frame = (extra) => ({ row: 7, chosen_action: "stay", executed_action: "stay", q: 0, cache_hit: false,
                            latency_ms: 212.4, answers: { gap_stay: { noul: 0.05 } }, ...extra });

test("asked counts a question set's questions and calls a prompt one", () => {
  assert.equal(asked(composed, frame()), "4 questions");
  assert.equal(asked({ questions: [{ system: "rules", user: "row" }] }, frame()), "one prompt");
  assert.equal(asked({ questions: [{ action: {} }] }, frame()), "1 question");
});

test("asked says nothing when the frame points at no questions", () => {
  assert.equal(asked(composed, frame({ q: null })), "");
  assert.equal(asked({ player: "fly" }, frame({ q: null })), "");
});

test("answered quotes the chosen move's gap probability", () => {
  assert.equal(answered(composed, frame()), "5% it lands on a gap");
});

test("answered falls back to the choice when there is no per-move number", () => {
  assert.equal(answered({ player: "jev_choice" }, frame({ answers: { action: { choice: "jump" } } })), "chose jump");
});

test("answered shortens a written reply to one line", () => {
  const text = "line one\nline two that goes on and on and on and on and on and on and on and on";
  const out = answered({ player: "llm" }, frame({ answers: { text } }));
  assert.ok(out.endsWith("…"));
  assert.ok(!out.includes("\n"));
  assert.ok(out.length <= 64);
});

test("answered gives the fly its rates, signals and spike count", () => {
  const fly = { player: "fly" };
  const info = { left_hz: 120.4, right_hz: 80, turn_signal_hz: -14.6, jump_signal_hz: 41.2, total_spikes: 5312 };
  assert.equal(answered(fly, frame({ info, answers: null })),
    "eyes 120 Hz / 80 Hz, turn -15 Hz, jump 41 Hz, 5312 spikes");
});

test("answered marks a missing fly signal rather than printing NaN", () => {
  const out = answered({ player: "fly" }, frame({ info: { total_spikes: 3 }, answers: null }));
  assert.ok(out.includes("–"));
  assert.ok(!out.includes("NaN"));
});

test("move names the move the game ran when it differs, and why", () => {
  assert.equal(move(frame()), "stay");
  const held = move(frame({ chosen_action: "jump", executed_action: "stay", gated: true }));
  assert.ok(held.includes("held back") && held.includes("ran stay"));
  assert.ok(move(frame({ chosen_action: "jump", executed_action: "stay", invalid: true })).includes("not a valid move"));
  assert.ok(move(frame({ chosen_action: null, executed_action: "stay", error: "boom" })).includes("error"));
});

test("timing prefers the cache over a latency", () => {
  assert.equal(timing(frame()), "212 ms");
  assert.equal(timing(frame({ cache_hit: true })), "cached");
  assert.equal(timing(frame({ latency_ms: null })), "");
});

test("a line carries the row, the move and the timing", () => {
  const html = line(composed, frame());
  assert.ok(html.includes("0007"));
  assert.ok(html.includes("stay"));
  assert.ok(html.includes("212 ms"));
  assert.ok(html.includes("4 questions"));
});

test("an error is shown in --bad, escaped", () => {
  const html = line(composed, frame({ error: "<script>x</script>" }));
  assert.ok(html.includes('<span class="bad">'));
  assert.ok(!html.includes("<script>"));
  assert.ok(html.includes("&#60;script&#62;"));
});

test("a written answer is escaped, never markup", () => {
  const html = line({ player: "llm", questions: [] }, frame({ q: null, answers: { text: '<img src=x onerror="a">' } }));
  assert.ok(!html.includes("<img"));
  assert.ok(html.includes("&#60;img"));
});

test("lines keeps the frames' order, oldest first", () => {
  const html = lines(composed, [frame({ row: 1 }), frame({ row: 2 })]);
  assert.ok(html.indexOf("0001") < html.indexOf("0002"));
});

test("short leaves a short line alone", () => {
  assert.equal(short("  a  b "), "a b");
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `node --test viewer/tests/log.test.js`
Expected:

```text
✖ viewer/tests/log.test.js
ℹ pass 0
ℹ fail 1
```

- [ ] **Step 3: Write the implementation**

Create `viewer/log.js`:

```javascript
// The running log of one mind: one line per row, newest last (pure, so node --test can run it).
// Nothing here is streamed: every line is built from a frame the strip already has, and every value
// that comes from a log goes through esc(). Numbers are shown as the run recorded them.
(function (root) {
  "use strict";

  const Mind = typeof module !== "undefined" && module.exports ? require("./minds.js") : root.Minds;
  const esc = Mind.esc;

  const hz = (value) => (typeof value === "number" ? Math.round(value) + " Hz" : "–");
  const percent = (p) => Math.round(p * 100) + "%";
  const CUT = 64; // how much of a written answer one line carries; the whole of it is in the panel above

  // one line of text, cut at CUT characters with an ellipsis, newlines flattened to spaces
  function short(text) {
    const flat = String(text).replace(/\s+/g, " ").trim();
    return flat.length > CUT ? flat.slice(0, CUT - 1) + "…" : flat;
  }

  // what the player was asked, in a few words. A question set names its questions; an LLM prompt is
  // one message, so it counts as one. A player that asks nothing (the fly, the solver) says nothing.
  function asked(episode, frame) {
    const questions = frame.q == null ? null : (episode.questions || [])[frame.q];
    if (!questions) return "";
    if (questions.system != null || questions.user != null) return "one prompt";
    const n = Object.keys(questions).length;
    return n === 1 ? "1 question" : n + " questions";
  }

  // what it answered: the fly's read-out, a written reply's first line, or how sure it was about the
  // move it picked. The number quoted is the one the panel above shows for that move.
  function answered(episode, frame) {
    const info = frame.info || {};
    if (episode.player === "fly") {
      return "eyes " + hz(info.left_hz) + " / " + hz(info.right_hz) + ", turn " + hz(info.turn_signal_hz) +
        ", jump " + hz(info.jump_signal_hz) + ", " + (info.total_spikes == null ? "–" : info.total_spikes) + " spikes";
    }
    const answers = frame.answers;
    if (!answers) return "";
    if (typeof answers.text === "string" && answers.text !== "") return short(answers.text);
    const gap = (answers["gap_" + frame.chosen_action] || {}).noul;
    if (typeof gap === "number") return percent(gap) + " it lands on a gap";
    const choice = (answers.action || {}).choice;
    if (choice != null) return "chose " + choice;
    return "";
  }

  // the move, and why the game ran a different one when it did
  function move(frame) {
    const chosen = frame.chosen_action == null ? "no move" : frame.chosen_action;
    if (frame.chosen_action === frame.executed_action) return esc(chosen);
    const why = frame.error != null ? "error" : frame.invalid ? "not a valid move" : frame.gated ? "held back" : "no move";
    return esc(chosen) + ' <span class="warn">' + why + ", ran " + esc(frame.executed_action) + "</span>";
  }

  // how long it took, or that the answer never left this machine
  function timing(frame) {
    if (frame.cache_hit) return "cached";
    if (frame.latency_ms == null) return "";
    return Math.round(frame.latency_ms) + " ms";
  }

  // one row's line. `frame.row` is the row it decided on.
  function line(episode, frame) {
    const parts = [asked(episode, frame), answered(episode, frame), timing(frame)].filter((p) => p !== "");
    return '<li><span class="at">' + esc(String(frame.row).padStart(4, "0")) + "</span>" +
      '<span class="did">' + move(frame) + "</span>" +
      '<span class="said">' + parts.map(esc).join(" · ") + "</span>" +
      (frame.error == null ? "" : '<span class="bad">' + esc(frame.error) + "</span>") + "</li>";
  }

  // the whole log, oldest first, so the newest line is at the bottom
  function lines(episode, frames) {
    return frames.map((frame) => line(episode, frame)).join("");
  }

  const api = { asked, answered, move, timing, line, lines, short };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Log = api;
})(typeof window !== "undefined" ? window : globalThis);
```

- [ ] **Step 4: Run the task's tests**

Run: `node --test viewer/tests/log.test.js`
Expected: `pass 14, fail 0`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `420 passed, 9 deselected in 32.28s`

- [ ] **Step 6: Commit**

```bash
git add viewer/log.js viewer/tests/log.test.js
git commit -F <message file>   # feat: a mind's running log, one line per row (pure, tested)
```

---

### Task 2: Every mind panel gains its log, one open at a time

**Files:**
- Modify: `viewer/app.js`
- Modify: `viewer/index.html`
- Modify: `viewer/viewer.css`
- Test: `tests/test_view.py`

**Interfaces:**
`viewer/index.html` names `log.js` before `feed.js`. Each mind panel gains `<details class="log"><summary class="label">Its log</summary><ol class="log-lines"></ol></details>`, and `view.panels[player]` gains `log`, `lines` and `logged` (how many frames that panel has already logged). `view.openLog` is the player whose log is open, so it survives a re-render of the strip.

`appendLog(player)` appends only the frames not logged yet and keeps the scroll unless the reader was at the bottom (within 4 px), in which case it follows the newest line. The strip's capturing `toggle` listener keeps one log open at a time.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_view.py`:

```diff
@@ -59,7 +59,7 @@ def test_the_page_keeps_every_caveat_about_the_fly_and_about_jevs_questions():
 
 def test_every_script_the_page_names_exists_and_app_comes_last():
     names = re.findall(r'<script src="([^"]+)"></script>', (VIEWER_DIR / "index.html").read_text())
-    assert names == ["timeline.js", "tunnel.js", "sprites.js", "stage.js", "minds.js", "feed.js", "lobby.js", "app.js"]
+    assert names == ["timeline.js", "tunnel.js", "sprites.js", "stage.js", "minds.js", "log.js", "feed.js", "lobby.js", "app.js"]
     assert all((VIEWER_DIR / name).is_file() for name in names)
 
 
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_view.py`
Expected:

```text
FAILED tests/test_view.py::test_every_script_the_page_names_exists_and_app_comes_last
1 failed, 13 passed in 0.22s
```

- [ ] **Step 3: Write the implementation**

Apply to `viewer/app.js`:

```diff
@@ -43,7 +43,7 @@
   const store = { game: null, runs: [], players: [], seeds: [], tracks: {}, episodes: [], scoreboard: null, ended: !liveUrl, error: null };
   const view = {
     seed: null, shown: new Set(), focus: null, auto: true, heldSince: 0,
-    t: 0, playing: false, speed: 3, following: !!liveUrl, size: 0, runners: [], panels: {},
+    t: 0, playing: false, speed: 3, following: !!liveUrl, size: 0, runners: [], panels: {}, openLog: null,
   };
 
   const runOf = (episode) => store.runs.find((run) => run.run_id === episode.run_id) || {};
@@ -153,6 +153,7 @@
   // ---- the mind strip -----------------------------------------------------------------------
   function renderStrip() {
     const strip = $("strip");
+    const openLog = view.openLog; // only one log is open at a time; it survives a re-render of the strip
     strip.innerHTML = "";
     view.panels = {};
     view.runners = playing().map((episode) => {
@@ -165,18 +166,44 @@
       panel.dataset.player = episode.player;
       panel.innerHTML = '<header><span class="label tag">' + esc(Minds.tagOf(episode.player)) + '</span><span class="about">' +
         esc(ABOUT[episode.player] || "") + (model ? " · " + esc(model) : "") + '</span></header><div class="body"><p class="status"></p>' +
-        '<div class="decision"></div></div>';
+        '<div class="decision"></div><details class="log"><summary class="label">Its log</summary><ol class="log-lines"></ol></details></div>';
       strip.appendChild(panel);
-      view.panels[episode.player] = { panel, status: panel.querySelector(".status"), decision: panel.querySelector(".decision"), index: -1 };
+      view.panels[episode.player] = { panel, status: panel.querySelector(".status"), decision: panel.querySelector(".decision"),
+                                      log: panel.querySelector(".log"), lines: panel.querySelector(".log-lines"), index: -1, logged: 0 };
       return { episode, track: store.tracks[String(episode.seed)], lookahead: game.lookahead || 6, window: window_,
                context: { windowMs: run.fly ? run.fly.window_ms : null, window: window_, maxHz: game.looming ? game.looming.max_hz : null } };
     });
+    if (openLog && view.panels[openLog]) view.panels[openLog].log.open = true;
     if (!view.runners.length) {
       strip.innerHTML = '<p class="note" style="padding:16px">' + (view.seed == null ? "Nothing has been played yet."
-        : "None of the players shown ran track " + esc(view.seed) + ". Pick a player in the level table to show it.") + "</p>";
+        : "None of the players shown ran track " + esc(view.seed) + ". Pick a player above to show it.") + "</p>";
     }
   }
 
+  // the log of one decision at a time, appended as the frames arrive so the list keeps its scroll
+  function appendLog(player) {
+    const ui = view.panels[player];
+    const episode = episodeOf(player, view.seed);
+    if (!ui || !episode || episode.frames.length <= ui.logged) return;
+    // "at the bottom" before the append decides whether the newest line is scrolled to afterwards
+    const atEnd = ui.lines.scrollTop + ui.lines.clientHeight >= ui.lines.scrollHeight - 4;
+    ui.lines.insertAdjacentHTML("beforeend", Log.lines(episode, episode.frames.slice(ui.logged)));
+    ui.logged = episode.frames.length;
+    if (atEnd) ui.lines.scrollTop = ui.lines.scrollHeight;
+  }
+
+  // one panel's log open at a time: opening one closes the rest
+  $("strip").addEventListener("toggle", (event) => {
+    const log = event.target.closest("details.log");
+    if (!log) return;
+    if (!log.open) {
+      if (view.openLog === log.closest(".mind").dataset.player) view.openLog = null;
+      return;
+    }
+    view.openLog = log.closest(".mind").dataset.player;
+    for (const other of $("strip").querySelectorAll("details.log")) if (other !== log) other.open = false;
+  }, true);
+
   $("strip").addEventListener("click", (event) => {
     if (event.target.closest("summary, details")) return;
     const panel = event.target.closest(".mind");
@@ -262,6 +289,7 @@
       const status = !store.ended && !episode.complete && s.index === episode.frames.length - 1 && t >= s.frame.landing[0]
         ? "thinking…" : Minds.statusLine(episode, s, s.runner.track.lanes);
       if (ui.status.innerHTML !== status) ui.status.innerHTML = status;
+      appendLog(s.id);
       if (s.index !== ui.index) {
         const open = !!(ui.decision.querySelector("details") || {}).open;
         ui.decision.innerHTML = Minds.mind(episode, s.frame, s.runner.context);
@@ -446,7 +474,7 @@
     Object.assign(store, { game: null, runs: [], players: [], seeds: [], tracks: {}, episodes: [],
                            scoreboard: null, ended: false, error: null });
     Object.assign(view, { seed: null, shown: new Set(), focus: null, auto: true, heldSince: 0, t: 0,
-                          playing: false, following: true, runners: [], panels: {} });
+                          playing: false, following: true, runners: [], panels: {}, openLog: null });
     Feed.fromEmbedded(replay, handlers);
     renderAll();
   }
```

Apply to `viewer/index.html`:

```diff
@@ -130,6 +130,7 @@
 <script src="sprites.js"></script>
 <script src="stage.js"></script>
 <script src="minds.js"></script>
+<script src="log.js"></script>
 <script src="feed.js"></script>
 <script src="lobby.js"></script>
 <script src="app.js"></script>
```

Apply to `viewer/viewer.css`:

```diff
@@ -66,6 +66,15 @@ section > h2.label { margin-bottom: 20px; }
 .mind header .about { color: var(--muted); font-size: var(--size-small); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
 .mind .status { min-height: 1.6em; color: var(--text); }
 .mind p { margin-top: 8px; }
+.mind .log { margin-top: 12px; border-top: 1px solid var(--hairline); }
+.log-lines { list-style: none; margin: 0 0 4px; padding: 0; max-height: 220px; overflow-y: auto;
+  font-family: "JetBrains Mono", ui-monospace, monospace; font-size: var(--size-small); }
+.log-lines li { display: grid; grid-template-columns: 4.5em minmax(0, 7em) minmax(0, 1fr); gap: 10px;
+  padding: 3px 0; border-bottom: 1px solid var(--hairline); }
+.log-lines li:last-child { border-bottom: 0; }
+.log-lines .at { color: var(--muted); }
+.log-lines .said { color: var(--muted); overflow-wrap: anywhere; }
+.log-lines .bad { grid-column: 1 / -1; }
 .mind .saw { display: flex; gap: 16px; align-items: flex-start; margin-top: 10px; }
 .mind .verdict { margin-top: 0; }
 .mind .verdict strong { font-weight: 500; font-size: 20px; letter-spacing: -0.015em; color: var(--bright); }
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_view.py`
Expected: `14 passed in 0.29s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `420 passed, 9 deselected in 31.78s`

- [ ] **Step 6: Commit**

```bash
git add tests/test_view.py viewer/app.js viewer/index.html viewer/viewer.css
git commit -F <message file>   # feat: every mind panel gains its log, one open at a time, keeping its scroll
```

---

### Task 3: One player picker over the tunnel, and the Run and Analysis tabs

**Files:**
- Modify: `bakeoff/__main__.py`
- Modify: `bakeoff/bench.py`
- Modify: `bakeoff/view.py`
- Modify: `viewer/app.js`
- Modify: `viewer/bench.html`
- Modify: `viewer/bench_app.js`
- Create: `viewer/bench_view.js`
- Modify: `viewer/index.html`
- Create: `viewer/picker.js`
- Create: `viewer/tabs.js`
- Modify: `viewer/viewer.css`
- Test: `tests/test_bench.py`
- Test: `tests/test_view.py`
- Test: `viewer/tests/picker.test.js`
- Test: `viewer/tests/tabs.test.js`

**Interfaces:**
- `viewer/tabs.js` exposes `Tabs`: `NAMES` (`["run", "analysis"]`), `select(current, wanted)`, `stateOf(focus)` (one `{name, selected, hidden}` per tab, returned rather than applied), `step(focus, key)` (arrow keys, wrapping).
- `viewer/picker.js` exposes `Picker`: `list(players, here, shown, about)` (one button per player, `aria-pressed`, disabled with "not on this track" when the player has no episode on the track in view), `hint(players, here, shown, seed)`, `toggle(shown, here, player)` (returns a new Set; a player not in `here` can never be turned on).
- `viewer/bench_view.js` exposes `BenchView`: `mount(container, numbers)` and `why(numbers)`; `bench_app.js` keeps only what the standalone page does.
- `bakeoff/bench.py` gains `benchmark_of(run_dirs) -> (numbers | None, why | None)`.
- `bakeoff/view.py` gains `BENCH_SLOT` and the `bench=` argument of `render_html`; a page with no benchmark slot must not be given one. `bakeoff/__main__.py` fills it when `view` writes a page.

Decision 37: the level table no longer toggles players. It keeps its track buttons, and picking a track calls `showTab("run")`. `renderBench` draws only on the Analysis tab and only when the numbers changed; the canvas is sized and drawn when the Run tab comes back, because it cannot be sized while it is hidden.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_bench.py`:

```diff
@@ -195,3 +195,24 @@ def test_a_colon_in_a_directory_path_is_not_a_player_list():
     from pathlib import Path
     assert parse_source("runs/a:b/c") == Source(Path("runs/a:b/c"), None)
     assert parse_source("runs/a:b/c:llm") == Source(Path("runs/a:b/c"), ("llm",))
+
+
+def test_benchmark_of_scores_a_run_directory(tmp_path):
+    from bakeoff.bench import benchmark_of
+
+    run = write_run(tmp_path, "r", episode("solver", 1000, 40) + episode("random", 1000, 9), {"game": V2})
+    out, why = benchmark_of([run])
+    assert why is None
+    assert {p["player"] for p in out["players"]} == {"solver", "random"}
+
+
+def test_benchmark_of_says_why_instead_of_failing_when_there_is_nothing_to_score(tmp_path):
+    """The page asks for numbers it may not be able to have; `bakeoff bench` still refuses loudly."""
+    from bakeoff.bench import benchmark_of
+
+    out, why = benchmark_of([tmp_path / "missing"])
+    assert out is None and why
+
+    run = write_run(tmp_path, "open", [record(player="solver", seed=1000, row=0)], {"game": V2})
+    out, why = benchmark_of([run])
+    assert out is None and "needs runs that ended" in why
```

Apply to `tests/test_view.py`:

```diff
@@ -59,7 +59,8 @@ def test_the_page_keeps_every_caveat_about_the_fly_and_about_jevs_questions():
 
 def test_every_script_the_page_names_exists_and_app_comes_last():
     names = re.findall(r'<script src="([^"]+)"></script>', (VIEWER_DIR / "index.html").read_text())
-    assert names == ["timeline.js", "tunnel.js", "sprites.js", "stage.js", "minds.js", "log.js", "feed.js", "lobby.js", "app.js"]
+    assert names == ["timeline.js", "tunnel.js", "sprites.js", "stage.js", "minds.js", "log.js", "picker.js", "tabs.js",
+                     "feed.js", "lobby.js", "bench.js", "bench_view.js", "app.js"]
     assert all((VIEWER_DIR / name).is_file() for name in names)
 
 
@@ -144,4 +145,51 @@ def test_the_benchmark_page_makes_no_network_request_and_names_only_existing_scr
     assert not re.search(r"(src|href)=[\"']?https?:", page) and "@import" not in page
     source = (VIEWER_DIR / "bench.html").read_text()
     scripts = re.findall(r'<script src="([^"]+)"></script>', source)
-    assert scripts == ["bench.js", "bench_app.js"] and all((VIEWER_DIR / s).exists() for s in scripts)
+    assert scripts == ["bench.js", "bench_view.js", "bench_app.js"] and all((VIEWER_DIR / s).exists() for s in scripts)
+
+
+BENCH = re.compile(r'<script type="application/json" id="bench-data">(.*?)</script>', re.S)
+
+
+def test_the_benchmark_rides_in_its_own_slot_and_leaves_the_replay_alone():
+    page = render_html({"episodes": []}, bench={"players": [{"player": "solver"}]})
+    assert json.loads(BENCH.search(page).group(1)) == {"players": [{"player": "solver"}]}
+    assert json.loads(DATA.search(page).group(1)) == {"episodes": []}
+
+
+def test_a_page_given_no_benchmark_keeps_an_empty_slot():
+    page = render_html({"episodes": []})
+    assert json.loads(BENCH.search(page).group(1)) is None
+
+
+def test_a_benchmark_cannot_close_its_script_element_either():
+    page = render_html({"episodes": []}, bench={"notes": ["</script><script>alert(1)</script>"]})
+    assert "</script><script>alert(1)" not in page
+    assert json.loads(BENCH.search(page).group(1))["notes"] == ["</script><script>alert(1)</script>"]
+
+
+def test_the_benchmark_page_has_no_slot_for_a_benchmark_and_refuses_one():
+    """bench.html carries its numbers in the replay slot; giving it a second set would lose them."""
+    with pytest.raises(ValueError, match="benchmark data slot"):
+        render_html({}, page_name="bench.html", bench={"players": []})
+
+
+def test_view_writes_the_benchmark_of_the_runs_it_merges(tmp_path, capsys):
+    from tests.test_replay import DIED, record, write_run
+
+    records = ([record(player="solver", seed=1000, row=r) for r in range(9)] + [record(player="solver", seed=1000, row=9, **DIED)])
+    run = write_run(tmp_path, "r", records, {"game": None})
+    out = tmp_path / "page.html"
+    assert main(["view", str(run), "--out", str(out)]) == 0
+    numbers = json.loads(BENCH.search(out.read_text()).group(1))
+    assert [p["player"] for p in numbers["players"]] == ["solver"]
+
+
+def test_view_still_builds_a_page_when_there_is_nothing_to_score(tmp_path):
+    """A run that never ended has no benchmark; the page says why rather than failing to build."""
+    from tests.test_replay import record, write_run
+
+    run = write_run(tmp_path, "open", [record(player="solver", seed=1000, row=0)], {"game": None})
+    out = tmp_path / "page.html"
+    assert main(["view", str(run), "--out", str(out)]) == 0
+    assert "why" in json.loads(BENCH.search(out.read_text()).group(1))
```

Create `viewer/tests/picker.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const { list, hint, toggle } = require("../picker.js");

const players = ["fly", "jev_composed", "llm", "solver"];
const here = ["fly", "jev_composed", "llm"];

test("a shown player's button is pressed, a hidden one's is not", () => {
  const html = list(players, here, new Set(["fly"]), {});
  assert.ok(html.includes('data-player="fly" aria-pressed="true"'));
  assert.ok(html.includes('data-player="jev_composed" aria-pressed="false"'));
});

test("a player that did not run this track is disabled and says so", () => {
  const html = list(players, here, new Set(players), {});
  assert.ok(/data-player="solver" aria-pressed="false" disabled/.test(html));
  assert.ok(html.includes("not on this track"));
});

test("a player name and its description are escaped", () => {
  const html = list(['<b>x</b>'], ['<b>x</b>'], new Set(), { "<b>x</b>": '"><script>' });
  assert.ok(!html.includes("<b>"));
  assert.ok(!html.includes("<script>"));
});

test("hint counts what is shown of what ran the track", () => {
  assert.equal(hint(players, here, new Set(["fly", "llm"]), 1001), "2 of 3 shown on track 1001.");
  assert.equal(hint(players, here, new Set(), 1001), "Nobody is in the tunnel: pick a player to show it.");
  assert.equal(hint(players, [], new Set(), 1001), "No player ran track 1001.");
  assert.equal(hint([], [], new Set(), null), "Nothing has been played yet.");
});

test("hint escapes a seed that is not a number", () => {
  assert.ok(!hint(players, [], new Set(), "<b>").includes("<b>"));
});

test("toggle turns a player on and off without changing the set it was given", () => {
  const shown = new Set(["fly"]);
  assert.deepEqual([...toggle(shown, here, "llm")], ["fly", "llm"]);
  assert.deepEqual([...toggle(shown, here, "fly")], []);
  assert.deepEqual([...shown], ["fly"]);
});

test("toggle can never show a player that did not run this track", () => {
  assert.deepEqual([...toggle(new Set(), here, "solver")], []);
});
```

Create `viewer/tests/tabs.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const { NAMES, select, stateOf, step } = require("../tabs.js");

test("there are two tabs and the run is the first", () => {
  assert.deepEqual(NAMES, ["run", "analysis"]);
});

test("select takes the tab asked for when it is a real one", () => {
  assert.equal(select("run", "analysis"), "analysis");
  assert.equal(select("analysis", "run"), "run");
});

test("select keeps the tab in focus when the one asked for is not real", () => {
  assert.equal(select("analysis", "nonsense"), "analysis");
  assert.equal(select("analysis", null), "analysis");
});

test("a page that opens on nothing opens on the run", () => {
  assert.equal(select(null, null), "run");
  assert.equal(select("nonsense", "nonsense"), "run");
});

test("stateOf selects exactly one tab and hides the other", () => {
  const state = stateOf("analysis");
  assert.deepEqual(state, [{ name: "run", selected: false, hidden: true },
                           { name: "analysis", selected: true, hidden: false }]);
  assert.equal(stateOf("nonsense").filter((t) => t.selected).length, 1);
});

test("the arrow keys move along the strip and wrap", () => {
  assert.equal(step("run", "ArrowRight"), "analysis");
  assert.equal(step("analysis", "ArrowRight"), "run");
  assert.equal(step("run", "ArrowLeft"), "analysis");
  assert.equal(step("run", "Enter"), null);
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_view.py tests/test_bench.py tests/test_viewer_js.py`
Expected:

```text
FAILED tests/test_view.py::test_every_script_the_page_names_exists_and_app_comes_last
FAILED tests/test_view.py::test_the_benchmark_page_makes_no_network_request_and_names_only_existing_scripts
FAILED tests/test_view.py::test_the_benchmark_rides_in_its_own_slot_and_leaves_the_replay_alone
FAILED tests/test_view.py::test_a_page_given_no_benchmark_keeps_an_empty_slot
FAILED tests/test_view.py::test_a_benchmark_cannot_close_its_script_element_either
FAILED tests/test_view.py::test_the_benchmark_page_has_no_slot_for_a_benchmark_and_refuses_one
FAILED tests/test_view.py::test_view_writes_the_benchmark_of_the_runs_it_merges
FAILED tests/test_view.py::test_view_still_builds_a_page_when_there_is_nothing_to_score
FAILED tests/test_bench.py::test_benchmark_of_scores_a_run_directory - Import...
FAILED tests/test_bench.py::test_benchmark_of_says_why_instead_of_failing_when_there_is_nothing_to_score
FAILED tests/test_viewer_js.py::test_viewer_javascript - AssertionError: ✔ es...
11 failed, 27 passed in 3.41s
```

- [ ] **Step 3: Write the implementation**

Apply to `bakeoff/__main__.py`:

```diff
@@ -285,9 +285,12 @@ def main(argv: list[str] | None = None) -> int:
         if not replay["episodes"]:
             print("no step records in " + ", ".join(args.run_dirs), file=sys.stderr)
             return 2
+        from bakeoff.bench import benchmark_of  # numpy: only when a page wants the benchmark
+
+        numbers, why = benchmark_of(args.run_dirs)
         output = Path(args.output)
         try:
-            output.write_text(render_html(replay), encoding="utf-8")
+            output.write_text(render_html(replay, bench=numbers if numbers else {"why": why}), encoding="utf-8")
         except OSError as e:
             print(f"cannot write {output}: {e}", file=sys.stderr)
             return 2
```

Apply to `bakeoff/bench.py`:

```diff
@@ -272,6 +272,19 @@ def benchmark(loaded: Loaded) -> dict:
 
 # ---- the terminal ----------------------------------------------------------------------------------------------
 
+def benchmark_of(run_dirs: list[str | Path]) -> tuple[dict | None, str | None]:
+    """The benchmark of these run directories, or (None, why not). The page asks for numbers it may
+    not be able to have — a live run of one track, runs of two lengths — and says so instead of
+    failing; `bakeoff bench` still refuses loudly."""
+    try:
+        loaded = load([parse_source(str(d)) for d in run_dirs])
+    except (FileNotFoundError, ValueError) as e:
+        return None, str(e)
+    if not loaded.episodes:
+        return None, "no completed run to score: the benchmark needs runs that ended."
+    return benchmark(loaded), None
+
+
 def _num(value, digits: int = 1) -> str:
     return "-" if value is None else f"{value:.{digits}f}"
 
```

Replace the whole of `bakeoff/view.py` with:

```python
"""Replay object + viewer/ -> one self-contained HTML file: no server, no network, opens from disk."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

VIEWER_DIR = Path(__file__).resolve().parent.parent / "viewer"
DATA_SLOT = '<script type="application/json" id="replay-data">null</script>'
BENCH_SLOT = '<script type="application/json" id="bench-data">null</script>'
_STYLESHEET = re.compile(r'<link rel="stylesheet" href="([^"]+)">')
_SCRIPT = re.compile(r'<script src="([^"]+)"></script>')
_CSS_URL = re.compile(r"url\(([^)]*)\)", re.IGNORECASE)  # CSS function names are case-insensitive
# the other ways a stylesheet can fetch something; none has a use in a page that must load nothing
_CSS_FETCHES = re.compile(r"@import|image-set|https?:", re.IGNORECASE)
_FONT = re.compile(r"fonts/[A-Za-z0-9_-]+\.woff2")


def embed_json(value) -> str:
    """JSON that is safe inside a <script> element. A logged answer may contain `</script>` or
    `<!--`; with every `<` written as \\u003c nothing in the data can end the element."""
    return json.dumps(value, separators=(",", ":")).replace("<", "\\u003c")


def _stylesheet(path: Path) -> str:
    """A stylesheet with its fonts embedded as base64, so the page stays one file that fetches nothing.
    The only url() a viewer stylesheet may contain is a bundled font, `fonts/<name>.woff2`."""
    css = path.read_text(encoding="utf-8")
    other = _CSS_FETCHES.search(css)
    if other:
        raise ValueError(f"{path.name} may only load fonts/<name>.woff2, not {other.group(0)!r}")

    def embed(match: re.Match) -> str:
        target = match.group(1).strip().strip("'\"")
        if not _FONT.fullmatch(target):
            raise ValueError(f"{path.name} may only load fonts/<name>.woff2, not {target!r}")
        return "url(data:font/woff2;base64," + base64.b64encode((path.parent / target).read_bytes()).decode("ascii") + ")"

    return _CSS_URL.sub(embed, css)


def render_html(replay: dict, viewer_dir: Path | str = VIEWER_DIR, live: str | None = None,
                page_name: str = "index.html", token: str | None = None, bench: dict | None = None) -> str:
    """`live`: the path of the event stream of `bakeoff live`. The page then also listens there, and
    drives the session through the control routes; a replay file has no such attribute and never looks
    for a server. `token`: the session's token, which every request of the page carries. `page_name`:
    the viewer page to fill, `index.html` (the replay) or `bench.html` (the benchmark); both carry the
    same data slot. `bench`: the benchmark's numbers for the same runs, for the page's Analysis tab;
    a page with no benchmark slot must not be given any."""
    viewer_dir = Path(viewer_dir)
    page = (viewer_dir / page_name).read_text(encoding="utf-8")
    if page.count(DATA_SLOT) != 1:
        raise ValueError(f"{viewer_dir / page_name} must contain the replay data slot exactly once")
    if bench is not None and page.count(BENCH_SLOT) != 1:
        raise ValueError(f"{viewer_dir / page_name} must contain the benchmark data slot exactly once to be given one")
    if live is not None:
        if not re.fullmatch(r"/[a-z]+", live):
            raise ValueError(f"live must be a path like /events, not {live!r}")
        if page.count("<body>") != 1:
            raise ValueError(f"{viewer_dir / page_name} must contain <body> exactly once")
        attributes = f'data-live="{live}"'
        if token is not None:
            if not re.fullmatch(r"[A-Za-z0-9_-]+", token):
                raise ValueError("the token must be url-safe text")
            attributes += f' data-token="{token}"'
        page = page.replace("<body>", f"<body {attributes}>")
    # lambdas, so that a backslash in a file is never read as a regex group reference
    page = _STYLESHEET.sub(lambda m: "<style>\n" + _stylesheet(viewer_dir / m.group(1)) + "</style>", page)
    page = _SCRIPT.sub(lambda m: "<script>\n" + (viewer_dir / m.group(1)).read_text(encoding="utf-8") + "</script>", page)
    if bench is not None:
        page = page.replace(BENCH_SLOT, '<script type="application/json" id="bench-data">' + embed_json(bench) + "</script>")
    return page.replace(DATA_SLOT, '<script type="application/json" id="replay-data">' + embed_json(replay) + "</script>")
```

Apply to `viewer/app.js`:

```diff
@@ -7,6 +7,8 @@
 
   const embedded = JSON.parse(document.getElementById("replay-data").textContent);
   if (!embedded) return;
+  const benchSlot = document.getElementById("bench-data");
+  let benchData = benchSlot ? JSON.parse(benchSlot.textContent) : null; // a live run gets its own when it ends
   const liveUrl = document.body.dataset.live || null;
   const token = document.body.dataset.token || null; // every control request carries it; a replay has none
 
@@ -43,7 +45,7 @@
   const store = { game: null, runs: [], players: [], seeds: [], tracks: {}, episodes: [], scoreboard: null, ended: !liveUrl, error: null };
   const view = {
     seed: null, shown: new Set(), focus: null, auto: true, heldSince: 0,
-    t: 0, playing: false, speed: 3, following: !!liveUrl, size: 0, runners: [], panels: {}, openLog: null,
+    t: 0, playing: false, speed: 3, following: !!liveUrl, size: 0, runners: [], panels: {}, openLog: null, tab: "run",
   };
 
   const runOf = (episode) => store.runs.find((run) => run.run_id === episode.run_id) || {};
@@ -81,6 +83,7 @@
       store.ended = true;
       if (end.runs) store.runs = end.runs;
       if (end.scoreboard) store.scoreboard = end.scoreboard;
+      if (end.bench) benchData = end.bench; // the numbers for the run that just ended, scored by the server
       notice(end.status === "completed" ? null : "The run ended: " + end.status, false);
       renderAll();
       if (liveUrl) refreshState(); // the run is over: the lobby comes back, with the run still on screen
@@ -121,8 +124,7 @@
       '<th><button type="button" data-seed="' + esc(seed) + '"' + (seed === view.seed ? ' aria-current="true"' : "") + ">" + esc(seed) +
       "</button></th>").join("") + "</tr></thead><tbody>";
     for (const player of store.players) {
-      html += '<tr><th><button type="button" data-player="' + esc(player) + '" aria-pressed="' + view.shown.has(player) + '">' +
-        esc(Minds.tagOf(player)) + "</button></th>";
+      html += "<tr><th>" + esc(Minds.tagOf(player)) + "</th>";
       for (const seed of store.seeds) {
         const episode = episodeOf(player, seed);
         const track = store.tracks[String(seed)];
@@ -137,16 +139,56 @@
     $("matrix").innerHTML = html + "</tbody>";
   }
 
+  // the level table picks the track; picking one goes back to the race, where the track is watched
   $("matrix").addEventListener("click", (event) => {
-    const button = event.target.closest("button");
+    const button = event.target.closest("button[data-seed]");
+    if (!button) return;
+    view.seed = Number(button.dataset.seed);
+    view.t = 0;
+    view.focus = null;
+    setPlaying(false);
+    showTab("run");
+    renderAll();
+  });
+
+  // ---- the tabs -----------------------------------------------------------------------------
+  function showTab(wanted) {
+    view.tab = Tabs.select(view.tab, wanted);
+    for (const tab of Tabs.stateOf(view.tab)) {
+      const button = $("tab-" + tab.name);
+      button.setAttribute("aria-selected", String(tab.selected));
+      button.tabIndex = tab.selected ? 0 : -1;
+      $("panel-" + tab.name).hidden = tab.hidden;
+    }
+    $("transport").hidden = view.tab !== "run" || !ready; // the transport drives the race, and only it
+    if (view.tab === "run") { resize(); draw(); } // the canvas cannot be sized while it is hidden
+    else renderBench();
+  }
+
+  document.querySelector(".tabs").addEventListener("click", (event) => {
+    const button = event.target.closest("button[data-tab]");
+    if (button) showTab(button.dataset.tab);
+  });
+  document.querySelector(".tabs").addEventListener("keydown", (event) => {
+    const next = Tabs.step(view.tab, event.key);
+    if (!next) return;
+    event.preventDefault();
+    showTab(next);
+    $("tab-" + next).focus();
+  });
+
+  // ---- who is in the tunnel -------------------------------------------------------------------
+  function renderPicker() {
+    const here = store.players.filter((p) => episodeOf(p, view.seed));
+    $("picks-replay").innerHTML = Picker.list(store.players, here, view.shown, ABOUT);
+    $("picker-hint").textContent = Picker.hint(store.players, here, view.shown, view.seed);
+  }
+
+  $("picks-replay").addEventListener("click", (event) => {
+    const button = event.target.closest("button[data-player]");
     if (!button) return;
-    if (button.dataset.seed != null) {
-      view.seed = Number(button.dataset.seed);
-      view.t = 0;
-      view.focus = null;
-      setPlaying(false);
-    } else if (view.shown.has(button.dataset.player)) view.shown.delete(button.dataset.player);
-    else view.shown.add(button.dataset.player);
+    const here = store.players.filter((p) => episodeOf(p, view.seed));
+    view.shown = Picker.toggle(view.shown, here, button.dataset.player);
     renderAll();
   });
 
@@ -564,22 +606,37 @@
 
   function renderAll() {
     renderMatrix();
+    renderPicker();
     renderStrip();
     renderBelow();
+    renderBench();
     resize();
     draw();
   }
 
+  // The benchmark, drawn once for a set of numbers: it is only built when the Analysis tab is looked
+  // at, and again when a live run ends and the server sends the numbers for what was just played.
+  let benchDrawn = null;
+  function renderBench() {
+    if (view.tab !== "analysis" || benchDrawn === benchData) return;
+    benchDrawn = benchData;
+    const why = benchData && benchData.why ? benchData.why : BenchView.why(benchData);
+    $("bench-why").hidden = !why;
+    $("bench-why").textContent = why || "";
+    $("bench").innerHTML = "";
+    if (!why) BenchView.mount($("bench"), benchData);
+  }
+
   // ---- start --------------------------------------------------------------------------------
   let ready = false;
   Feed.fromEmbedded(embedded, handlers);
   chooseDefaults();
   $("empty").hidden = true;
   $("app").hidden = false;
-  $("transport").hidden = false;
   $("mode").textContent = liveUrl ? "Live" : "Replay";
   $("live").hidden = !liveUrl;
   ready = true;
+  showTab(view.tab);
   renderAll();
   window.addEventListener("resize", () => { resize(); draw(); });
   if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw); // the canvas tags use the embedded mono
```

Replace the whole of `viewer/bench.html` with:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tunnel Run · Benchmark</title>
<link rel="stylesheet" href="viewer.css">
<link rel="stylesheet" href="bench.css">
</head>
<body>
<header class="top">
  <h1 class="label">Tunnel Run · Benchmark</h1>
  <p class="label" id="game"></p>
</header>

<main id="app" hidden>
  <div id="bench"></div>
</main>
<p class="note" id="empty" hidden>No benchmark data in this page.</p>

<script type="application/json" id="replay-data">null</script>
<script src="bench.js"></script>
<script src="bench_view.js"></script>
<script src="bench_app.js"></script>
</body>
</html>
```

Replace the whole of `viewer/bench_app.js` with:

```javascript
// The standalone benchmark page: reads the numbers bakeoff/bench.py embedded and hands them to the
// one renderer (bench_view.js), which the replay's Analysis tab mounts too.
(function () {
  "use strict";
  const data = JSON.parse(document.getElementById("replay-data").textContent);
  const why = window.BenchView.why(data);
  if (why) {
    document.getElementById("empty").hidden = false;
    document.getElementById("empty").textContent = why;
    return;
  }
  document.getElementById("app").hidden = false;
  document.getElementById("game").textContent = `game ${data.game || "unknown"} · ${data.runs.length} runs`;
  window.BenchView.mount(document.getElementById("bench"), data);
})();
```

Create `viewer/bench_view.js`:

```javascript
// The benchmark, drawn into whatever element it is given: the standalone page (bench.html) and the
// replay's Analysis tab both mount this one renderer, so there is one drawing code and one set of
// numbers. The arithmetic is in bench.js (tested); this file only builds markup from it. Everything
// that comes from a run goes through esc().
(function (root) {
  "use strict";

  const B = typeof module !== "undefined" && module.exports ? require("./bench.js") : root.Bench;
  const { esc, linear, log, ticks, logTicks, logDomain, survivalPath, split, fmt } = B;

  const W = 720, H = 320, M = { left: 48, right: 120, top: 12, bottom: 36 };

  // The sections the benchmark needs, as markup, so a page only has to give it an empty element.
  // `at` names the parts this renderer fills; a page never has to know their ids.
  const SHELL = `
<section aria-label="Players">
  <h2 class="label">Players</h2>
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

<section aria-label="Rows against cost and time" class="pair-charts">
  <div>
    <h2 class="label">Rows against cost</h2>
    <svg data-bench="cost" class="chart" role="img" aria-label="Mean rows against USD per row. The same numbers are in the players table."></svg>
  </div>
  <div>
    <h2 class="label">Rows against time</h2>
    <svg data-bench="time" class="chart" role="img" aria-label="Mean rows against seconds per row. The same numbers are in the players table."></svg>
  </div>
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

    // `strips`: for a player without a value, the label of the strip it is listed in (never drawn at 0)
    function scatter(name, key, xLabel, xFormat, strips) {
      const { placed, missing } = split(data.players, key);
      const svg = at(name);
      const w = 520, h = 340, m = { left: 48, right: 24, top: 12, bottom: 76 };
      svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
      const y = linear([0, data.max_rows], [h - m.bottom, m.top + 8]);
      let s = "";
      for (const t of ticks(0, data.max_rows, 3)) s += `<line class="grid" x1="${m.left}" x2="${w - m.right}" y1="${y(t)}" y2="${y(t)}"/>` +
        `<text x="${m.left - 8}" y="${y(t) + 4}" text-anchor="end">${t}</text>`;
      s += `<text x="${m.left}" y="${m.top - 2}">mean rows</text>`;
      if (placed.length) {
        const domain = logDomain(placed.map((p) => p[key]));
        const x = log(domain, [m.left + 12, w - m.right - 12]);
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
      playersTable();
      survivalChart();
      scatter("cost", "usd_per_row", "USD per row", (t) => String(t), (p) => (p.cost === "free" ? "free" : "no price"));
      scatter("time", "s_per_row", "seconds per row", (t) => String(t), () => "no time recorded");
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
```

Apply to `viewer/index.html`:

```diff
@@ -13,6 +13,12 @@
 </header>
 
 <main id="app" hidden>
+<div class="tabs" role="tablist" aria-label="The run and the analysis">
+  <button type="button" class="label" role="tab" id="tab-run" data-tab="run" aria-controls="panel-run" aria-selected="true">Run</button>
+  <button type="button" class="label" role="tab" id="tab-analysis" data-tab="analysis" aria-controls="panel-analysis" aria-selected="false" tabindex="-1">Analysis</button>
+</div>
+
+<div id="panel-run" role="tabpanel" aria-labelledby="tab-run">
   <section id="player" aria-label="The run">
     <div id="tunnel">
       <canvas id="canvas" aria-label="Three runners in one tunnel. The same information is in the panels below."></canvas>
@@ -41,10 +47,18 @@
     </form>
   </section>
 
+  <section id="picker" aria-label="Who is in the tunnel">
+    <h2 class="label">Who is in the tunnel</h2>
+    <div id="picks-replay" role="group" aria-label="Show or hide a runner"></div>
+    <p class="note" id="picker-hint"></p>
+  </section>
+</div>
+
+<div id="panel-analysis" role="tabpanel" aria-labelledby="tab-analysis" hidden>
   <section aria-label="Levels">
     <h2 class="label">Levels</h2>
     <div class="scroll"><table id="matrix"></table></div>
-    <p class="note">Rows survived on each track. Pick a track to play it; pick a player to show or hide its runner.
+    <p class="note">Rows survived on each track. Pick a track to watch it; who is in the tunnel is chosen on the Run tab.
       ✓ reached the finish line · … the run was stopped, which is not a death · a number after a slash is the
       length of a shorter run.</p>
   </section>
@@ -99,10 +113,17 @@
     </div>
   </section>
 
+  <section id="benchmark" aria-label="Benchmark">
+    <h2 class="label">Benchmark</h2>
+    <p class="note" id="bench-why" hidden></p>
+    <div id="bench"></div>
+  </section>
+
   <section aria-label="Runs">
     <h2 class="label">Runs</h2>
     <p class="note" id="runs"></p>
   </section>
+</div>
 </main>
 
 <p id="empty" class="note">This is the viewer's template. Build a replay with
@@ -125,14 +146,19 @@
 </nav>
 
 <script type="application/json" id="replay-data">null</script>
+<script type="application/json" id="bench-data">null</script>
 <script src="timeline.js"></script>
 <script src="tunnel.js"></script>
 <script src="sprites.js"></script>
 <script src="stage.js"></script>
 <script src="minds.js"></script>
 <script src="log.js"></script>
+<script src="picker.js"></script>
+<script src="tabs.js"></script>
 <script src="feed.js"></script>
 <script src="lobby.js"></script>
+<script src="bench.js"></script>
+<script src="bench_view.js"></script>
 <script src="app.js"></script>
 </body>
 </html>
```

Create `viewer/picker.js`:

```javascript
// Who is in the tunnel. One control governs both: in a replay it shows and hides the runners, and in
// a live command, while nothing is running, the lobby's own list (lobby.js) chooses who runs instead.
// Pure and tested under node; app.js does the DOM. Every player name goes through esc().
(function (root) {
  "use strict";

  const Mind = typeof module !== "undefined" && module.exports ? require("./minds.js") : root.Minds;
  const esc = Mind.esc;
  const tagOf = Mind.tagOf;

  // One button per player of the replay, pressed when its runner is shown. A player that did not run
  // the track in view cannot be shown, so its button is disabled and says so.
  // `players` is every player in the replay, in the replay's own order; `here` those with an episode
  // on the track in view; `shown` those currently in the tunnel; `about` a one-line description each.
  function list(players, here, shown, about) {
    const present = new Set(here);
    return players.map((player) => {
      const on = present.has(player) && shown.has(player);
      const title = (about || {})[player];
      return '<button type="button" class="pick-player" data-player="' + esc(player) + '"' +
        ' aria-pressed="' + on + '"' + (present.has(player) ? "" : " disabled") +
        (title ? ' title="' + esc(title) + '"' : "") + ">" +
        '<span class="label tag">' + esc(tagOf(player)) + "</span>" +
        (present.has(player) ? "" : '<span class="note">not on this track</span>') + "</button>";
    }).join("");
  }

  // What the control says under itself, so an empty tunnel is never a mystery.
  function hint(players, here, shown, seed) {
    if (!players.length) return "Nothing has been played yet.";
    if (!here.length) return "No player ran track " + esc(seed) + ".";
    const on = here.filter((p) => shown.has(p)).length;
    if (!on) return "Nobody is in the tunnel: pick a player to show it.";
    return on + " of " + here.length + " shown on track " + esc(seed) + ".";
  }

  // Toggling one player. A player that did not run this track can never be turned on, whatever is
  // clicked, so the tunnel's contents and the level table can never disagree.
  function toggle(shown, here, player) {
    const next = new Set(shown);
    if (next.has(player)) next.delete(player);
    else if (here.includes(player)) next.add(player);
    return next;
  }

  const api = { list, hint, toggle };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Picker = api;
})(typeof window !== "undefined" ? window : globalThis);
```

Create `viewer/tabs.js`:

```javascript
// The two tabs, as a rule rather than a router: plain buttons over one page, no navigation, no build
// step. The tab in focus is remembered while the page is open and nowhere else. Pure, tested.
(function (root) {
  "use strict";

  const NAMES = ["run", "analysis"];

  // The tab to show: the one asked for when it exists, otherwise the one already in focus, otherwise
  // the run. A page that opens on nothing always opens on the race.
  function select(current, wanted) {
    if (NAMES.includes(wanted)) return wanted;
    return NAMES.includes(current) ? current : NAMES[0];
  }

  // What each tab's button and panel should be, given the tab in focus: aria-selected on the button,
  // hidden on the panel. Returned rather than applied, so the rule can be tested without a DOM.
  function stateOf(focus) {
    const chosen = select(focus, focus);
    return NAMES.map((name) => ({ name, selected: name === chosen, hidden: name !== chosen }));
  }

  // Arrow keys move along the tab strip and wrap, as a tab list should.
  function step(focus, key) {
    const at = NAMES.indexOf(select(focus, focus));
    if (key === "ArrowRight") return NAMES[(at + 1) % NAMES.length];
    if (key === "ArrowLeft") return NAMES[(at - 1 + NAMES.length) % NAMES.length];
    return null;
  }

  const api = { NAMES, select, stateOf, step };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Tabs = api;
})(typeof window !== "undefined" ? window : globalThis);
```

Apply to `viewer/viewer.css`:

```diff
@@ -181,3 +181,20 @@ table { border-collapse: collapse; font-size: var(--size-small); font-variant-nu
 .pick .about { color: var(--muted); font-size: var(--size-small); }
 .pick .note { grid-column: 2; margin-top: 0; font-size: var(--size-label-sm); }
 .pick.blocked { opacity: 0.55; cursor: not-allowed; }
+
+/* the two tabs: plain buttons over one page, no routing */
+.tabs { display: flex; gap: 4px; padding: 0 16px; border-bottom: 1px solid var(--hairline); }
+.tabs button { min-height: 44px; padding: 0 16px; background: none; border: 0; border-bottom: 2px solid transparent;
+  color: var(--muted); cursor: pointer; }
+.tabs button[aria-selected="true"] { color: var(--bright); border-bottom-color: var(--accent); }
+.tabs button:hover { color: var(--text); }
+/* the tab strip is the rule above the first section of either panel */
+[role="tabpanel"] > section:first-child { margin-top: 0; border-top: 0; }
+
+/* who is in the tunnel */
+#picks-replay { display: flex; flex-wrap: wrap; gap: 8px; }
+.pick-player { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; padding: 0 12px;
+  background: var(--panel); border: 1px solid var(--hairline); color: var(--muted); cursor: pointer; }
+.pick-player[aria-pressed="true"] { color: var(--bright); border-color: var(--text); }
+.pick-player[disabled] { opacity: 0.45; cursor: default; }
+.pick-player .note { font-size: var(--size-small); }
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_view.py tests/test_bench.py tests/test_viewer_js.py`
Expected: `38 passed in 0.88s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `428 passed, 9 deselected in 32.68s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/__main__.py bakeoff/bench.py bakeoff/view.py tests/test_bench.py tests/test_view.py viewer/app.js viewer/bench.html viewer/bench_app.js viewer/bench_view.js viewer/index.html viewer/picker.js viewer/tabs.js viewer/tests/picker.test.js viewer/tests/tabs.test.js viewer/viewer.css
git commit -F <message file>   # feat: one player picker over the tunnel, and the Run and Analysis tabs
```

---

### Task 4: A live run ends with the benchmark of what it just played

**Files:**
- Modify: `bakeoff/live.py`
- Test: `tests/test_live_run.py`
- Test: `tests/test_live_server.py`

**Interfaces:**
`LiveRun._end_event(replay) -> dict` builds the last event of a run: `{status, runs, scoreboard, bench}`, where `bench` is `benchmark_of([self.run_dir])`'s numbers or `{"why": ...}`. Both places that emitted `end` now call it. `bakeoff.bench` is imported inside the function, because it pulls in numpy and only a run that ends needs it.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_live_run.py`:

```diff
@@ -69,7 +69,10 @@ def test_the_stream_is_the_replay_in_the_replays_own_shapes(tmp_path):
         assert set(header["episode"]) == set(episode) - {"frames"}
     assert events[0][0] == "episode" and events[1][0] == "frame"  # a runner is announced, then it moves
     name, end = events[-1]
-    assert name == "end" and end == {"status": "completed", "runs": replay["runs"], "scoreboard": replay["scoreboard"]}
+    assert name == "end"
+    # the benchmark of the run just played rides along (decision 36); the rest is the replay's own shapes
+    assert end.pop("bench")["runs"] == replay["runs"][0]["run_id"].split()  # one run, scored where it was recorded
+    assert end == {"status": "completed", "runs": replay["runs"], "scoreboard": replay["scoreboard"]}
     json.dumps(events)
 
 
```

Apply to `tests/test_live_server.py`:

```diff
@@ -203,3 +203,17 @@ def test_a_request_that_is_not_json_is_a_refusal_not_a_crash(server):
     response = connection.getresponse()
     assert response.status == 400 and "not JSON" in json.loads(response.read())["error"]
     connection.close()
+
+
+def test_the_end_of_a_live_run_carries_the_benchmark_of_what_was_just_played(server):
+    """The page has no numbers of its own: the server scores the run it just recorded and sends them
+    with the end event, so the Analysis tab fills in without a reload (decision 36)."""
+    httpd, session = server
+    started = payload(httpd, "POST", "/run", {"seed": 1001, "players": ["solver", "random"]})[1]
+    session.wait(30)
+    body = get(httpd, f"{EVENTS_PATH}?run={started['run_id']}")[1]
+    blocks = [b.split("\n") for b in body.strip().split("\n\n")]
+    end = json.loads(next(lines[1][6:] for lines in blocks if lines[0] == "event: end"))
+    assert {p["player"] for p in end["bench"]["players"]} == {"solver", "random"}
+    assert end["bench"]["players"][0]["seeds"] == 1  # one track: enough to score, never enough to rank
+    assert all(p["ranked"] is False for p in end["bench"]["players"])
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_live_run.py tests/test_live_server.py`
Expected:

```text
FAILED tests/test_live_run.py::test_the_stream_is_the_replay_in_the_replays_own_shapes
FAILED tests/test_live_server.py::test_the_end_of_a_live_run_carries_the_benchmark_of_what_was_just_played
2 failed, 26 passed in 7.33s
```

- [ ] **Step 3: Write the implementation**

Apply to `bakeoff/live.py`:

```diff
@@ -146,9 +146,19 @@ class LiveRun:
         self.meta.update(status=self.status, finished_at=_now())
         self._write_meta()
         replay = build_replay([self.run_dir])  # the same last event as a run that played: read from disk
-        self.broadcast.emit("end", {"status": self.status, "runs": replay["runs"], "scoreboard": replay["scoreboard"]})
+        self.broadcast.emit("end", self._end_event(replay))
         self.broadcast.close()
 
+    def _end_event(self, replay: dict) -> dict:
+        """The last event of a run: what the page needs to settle. It carries the benchmark of the run
+        that just played, scored here rather than in the browser, so the Analysis tab fills in without
+        a reload. One track is rarely enough for an interval, and the numbers say so themselves."""
+        from bakeoff.bench import benchmark_of  # numpy: only when a run ends
+
+        numbers, why = benchmark_of([self.run_dir])
+        return {"status": self.status, "runs": replay["runs"], "scoreboard": replay["scoreboard"],
+                "bench": numbers if numbers else {"why": why}}
+
     def _write_meta(self) -> None:
         (self.run_dir / "meta.json").write_text(json.dumps(self.meta, indent=2))
 
@@ -207,6 +217,6 @@ class LiveRun:
             self.meta.update(status=self.status, finished_at=_now(), requests=_requests(self.players))
             self._write_meta()
             replay = build_replay([self.run_dir])
-            self.broadcast.emit("end", {"status": self.status, "runs": replay["runs"], "scoreboard": replay["scoreboard"]})
+            self.broadcast.emit("end", self._end_event(replay))
             self.broadcast.close()
         return self.run_dir
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_live_run.py tests/test_live_server.py`
Expected: `28 passed in 7.80s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `429 passed, 9 deselected in 31.35s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/live.py tests/test_live_run.py tests/test_live_server.py
git commit -F <message file>   # feat: a live run ends with the benchmark of what it just played
```

---

### Task 5: What the page now does (docs)

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/UPDATES.md`

No prototype text for this one: write it from what the four tasks built, in the voice of the files around it, and change nothing else.

- [ ] **Step 1: `CLAUDE.md`** — in the viewer paragraph, add `log.js`, `tabs.js`, `picker.js` and `bench_view.js` to the list of pure JavaScript tested by `viewer/tests/*.test.js`, and say in one sentence that the page has a Run tab and an Analysis tab, that every mind panel carries a log (one open at a time), that one picker over the tunnel governs who is in it (the level table only picks the track), and that a live run's `end` event carries the benchmark of what it just played.
- [ ] **Step 2: `docs/UPDATES.md`** — mark items 4, 8 and 9 as done by update 3b, naming the branch work as 3a (the control channel and the lobby) and 3b (the panels, the tabs and the picker).
- [ ] **Step 3: Run all tests**

Run: `uv run pytest -q`
Expected: `429 passed, 9 deselected`

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/UPDATES.md
git commit -F <message file>   # docs: the rest of the page (update 3b): the logs, the two tabs and the player picker
```

---

### Task 6: Look at it (controller only)

Nothing here is dispatched to an implementer. Free players only; no paid player, no fly.

- [ ] `uv run python -m bakeoff view runs/20260921-165433 --output /tmp/3b-replay.html` and open it: the two tabs switch, the transport hides off the Run tab, the picker shows and hides runners, a player that did not run the track in view is disabled and says so, and the Analysis tab draws the benchmark.
- [ ] In a mind panel, open "Its log": lines carry the row, what it was asked, what it answered, the latency or `cached`, and an error in `--bad`; the fly's lines carry its eye rates, its turn and jump signals and its spike count. Opening a second panel's log closes the first.
- [ ] `uv run python -m bakeoff live --port 8765 --out /tmp/3b-live --players solver,random`, start a run from the lobby, and watch a log fill as it plays while the list keeps its scroll; when the run ends, the Analysis tab shows that run's own numbers without a reload.
- [ ] The level table: picking a track returns to the Run tab and watches it; nothing in that table toggles a player any more.
- [ ] Delete `.playwright-mcp/` if a browser check wrote screenshots into the repo, and remove `/tmp/3b-live` and `/tmp/3b-replay.html`.

### Task 7: Review (controller only)

- [ ] Byte-compare each task against its prototype commit with `.superpowers/tools/compare.sh`; skip the per-task review when nothing DIFFERS.
- [ ] One whole-update review aimed at the design, not at transcription: honesty (a log says what the run recorded and nothing more; the benchmark of one track says itself that it is not a result), escaping (every value from a log or from the server goes through `Minds.esc`), the brand (blue for the cursor alone), and the page still loading nothing from the network. Worth carrying in from 3a's review: the lobby never polls `/state`, so the page's freshness depends on the `end` event arriving; and the design text still says "another program on this machine cannot drive the run", which is not what the token does.
- [ ] Then `docs/NEXT.md` is rewritten: the updates are done, the explainer refresh and the "Opus v1" PR are what is left.

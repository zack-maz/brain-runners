# Brain Battle a, the server and the numbers — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** everything the Brain Battle screens will need from Python is built, tested and served:
- the roster of characters and skins;
- the results of a run and the records of every run;
- the two wrong-move numbers;
- the new routes.

The page itself changes in one way only: runners are drawn in their skin's colours and labelled "Jev · Step 1".

**Architecture:**
- **New Python modules:**
  - `bakeoff/roster.py` is the one list of characters and skins. It is embedded in every page by `bakeoff/view.py`.
  - `bakeoff/results.py` gives one run's numbers. They ride on the live run's `end` event and are served at `/results`.
  - `bakeoff/records.py` gives the leaderboard, the pairs and the past runs, at `/records`. It takes each (player, track) from the newest run that completed it.
- **The report:** `bakeoff/report.py` gains two columns, `wrong_moves` and `fatal_wrong_moves`.
- **The server:** `bakeoff/session.py` and `bakeoff/live_server.py` add:
  - `seeds_played` and the real `track` to `/state`;
  - three read-only routes behind the token: `/results`, `/records` and `/replay`.
- **The viewer:**
  - `viewer/roster.js` reads the embedded roster;
  - `viewer/sprites.js` gains the ox, the robot and skin colours;
  - `viewer/minds.js` labels by the roster;
  - `app.js` draws each runner as its character in its skin.

**Tech Stack:** Python 3.13, `uv`, `pytest`, numpy (already a dependency), the standard library's HTTP server; plain JavaScript with `node --test`, which `uv run pytest` runs through `tests/test_viewer_js.py`. No new dependency, no build step, no npm package.

**Spec:** `docs/superpowers/specs/2026-09-25-brain-battle-design.md` (binding; decision 45), sections A, B (the routes), D and E, and F's numbers. The screens (section C) and the money's new home (section G) are plan b. The request, the answers, the colour table and the mock-up links are in `docs/FRONTEND.md`. The mock-ups' sources are in `docs/mockups/brain-battle/` (the approved look, not viewer code).

**Branch:** `brain-battle`, in the git worktree `../brain-battle`. The main checkout is on `fly2-settle` and another session uses it: never write there, never switch its branch.

## Global Constraints

- Python via `uv` only: `uv run pytest`, `uv run python -m ...`. Python 3.13. Never call `pip` or bare `python`. No `uv add`.
- TDD: write the failing test, watch it fail, then implement. **No test touches the network.**
- **Implementers run the fast suite only** (`uv run pytest -q`). Never run `uv run pytest -m slow`, `bakeoff run` or `bakeoff live` with a fly. The real brain needs about 1 GB and only one may run on this 8 GB Mac at a time; another session may be running one. The controller runs the live smoke with a fly, once, when nothing else is.
- **This plan spends no money:** no paid player, no `--max-requests`, no `pytest -m live`.
- **A guard blocks every shell command that contains the text `.env`.** Never put it in a command.
- **Viewer rules:**
  - Plain JavaScript, no build step, and the page loads nothing from the network.
  - Everything that comes from a log or the server goes through `Minds.esc` before it becomes markup.
  - Blue is the cursor: the mind in focus and its tiles. A skin's own colour is the one other use, as the user chose it (Bot · Solver, the Map skins' eyes).
  - Deaths and errors use `--bad`, warnings `--warn`.
  - Add no colour of your own. Every skin colour comes from `bakeoff/roster.py`.
- **Honesty rule:** what is ours is labelled as ours. A skin's `about` line says what is ours about it (a fly's input, read-out and thresholds; a set's questions and rule).
- **The run path stays one path:** a live run's records still come from `runner.play_row` and its frames from `replay.frame_of`.
- **Old names:** a run recorded under an old name (`jev_composed`, `llm`, …) is read through `canonical()` everywhere. This plan adds no new place that reads a player name from disk without it.
- Every code block below was run in a prototype and passes as written: 565 fast tests pass with 16 deselected. If a test fails, suspect a transcription slip before redesigning.
- Commit after every task with the message given. The controller pre-writes each message to a file, attribution trailers included. The implementer runs exactly `git commit -F <that file>`, never `-m`, and checks `git log -1 --format=%B` afterwards.

## Review Focus

Inputs and conditions the spec implies that are most likely to bite, and where each is pinned:

1. **The same player on the same track in several run directories.** A live session replays tracks, and the recorded runs already hold `haiku_plain` on 1001 twice. Records must take the newest complete one, not refuse. Pinned by `test_each_player_and_track_counts_once_from_the_newest_run_that_completed_it` (task 6).
2. **A `run=` the page sends that is not a run.** Examples: `../cache`, an encoded path, a timestamp with no directory, a directory with no `meta.json`. It must be a 404, and no path may be built from it. Pinned by `test_only_a_recorded_run_directory_can_be_named` (task 7) and `test_a_run_that_is_not_a_recorded_run_directory_is_not_found` (task 7).
3. **A run directory broken part way** (a line that is not JSON before the last one). `/results` must answer 500 with the reason, and Records must list it as unreadable and still score the rest. Pinned by `test_a_run_directory_that_cannot_be_read_is_an_error_that_says_why` (task 7) and `test_records_say_why_instead_of_failing` (task 6).
4. **The results failing when a run ends.** The `end` event is what the page waits for, so it must still be sent, with the reason in place of the results. Pinned by `test_results_that_cannot_be_worked_out_never_cost_the_end_event` (task 5).
5. **A skin whose colour does not read on the dark page** (the Map skins' black `#1E2227`). Its label must keep the page's ink, with a swatch beside it, and never be written black on black. Pinned by `a label takes its skin's colour only where that colour reads on the page's ground` (task 3) and the tag test in `minds.test.js` (task 4).

## Decisions this plan makes beyond the spec

1. **`fatal_wrong_moves`, not `fatal_wrong_move`.** A run of several tracks has several deaths, so the report column is a count of episodes that ended on a wrong move. On one track it is 0 or 1. A result's `tracks[].trapped` says when a death had no surviving move.
2. **`bench.Source` gains `episodes`, a set of (player, seed) pairs, rather than a list of seeds.** Records takes each pair from its own newest run, and one run can hold the newest copy of one player's track but not of another's.
3. **The Map skins' labels:** black does not read on the page. Every tag carries a swatch of its skin's colour, and the label text takes the colour only where it has a WCAG contrast of at least 3 against `#0A0A0A`. Only the three Map skins fall short, at 1.24.
4. **The panel's focus is its blue top border, as before.** The rule that turned the focused panel's tag blue is dropped, so a tag always shows its skin (spec D). In the tunnel, the focused runner's tag keeps its blue brackets, since that is the cursor.
5. **Two approved texts are corrected on the honesty surface:**
   - The flies' `about` lines now name everything that is ours: "how gaps become input, which neurons we read and the thresholds", and fly2's "input, read-out, rule and thresholds". The mock-up named only the input.
   - The Map skin's line drops the mock-up's "(42)". That number follows the game's vision, and the page must not type in a number the logs carry.
6. **The page's note "The blue marks the mind in focus … nothing else" is now false** (Bot · Solver is blue, and so are the Map skins' eyes). It says so instead. The figures note names the ox and the robot, and says a skin's colours are ours.
7. **Every Jev skin wears the visor, every Haiku skin the critter.** The visor's slit shows `Minds.visorP`, which is dark where a set gives no probability for its move (Plain).

## For the user, noticed while prototyping (not changed)

- **The leaderboard mixes track counts.** Over the recorded runs, `fly` has 120 practice tracks and `fly2` 107 (1000–1199), from their calibration and settle runs. Most question sets have 5, and GLM Flash 1. Intervals and the head to head (common tracks only) stay honest. But a mean over 120 tracks and a mean over 5 are not the same track set, and fly's thresholds were fixed on these seeds (on game v1). Plan b's Records screen could limit the leaderboard to tracks 1000–1019, or mark the flies' count. That is your call; this plan scores what is recorded.

---

### Task 1: Wrong moves in the report

**Files:**
- Modify: `bakeoff/report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: the step record's `executed_action` and `solver_depths` (docs/STEP_RECORD.md).
- Produces: `COLUMNS` gains `"wrong_moves", "fatal_wrong_moves"` right after `"solver_agreement"`; every `summarize()` row carries them (ints). `wrong_moves`: steps where `solver_depths[executed_action] < max(solver_depths.values())`. `fatal_wrong_moves`: complete episodes whose last step is a death on a wrong move.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_report.py`:

```diff
@@ -55,6 +55,29 @@ def test_a_tied_best_choice_counts_as_agreement_even_if_it_is_not_the_solvers_pi
     assert row["solver_agreement"] == pytest.approx(1 / 3)  # left ties stay; jump is worse; teleport is no key
 
 
+def test_a_wrong_move_is_a_move_made_that_reaches_less_far_than_the_best():
+    best_left = {"stay": 2, "left": 6, "right": 0, "jump": 6}
+    steps = [step(chosen="left", depths=best_left),  # the best: not wrong
+             step(row=1, chosen="jump", depths=best_left),  # ties the best: not wrong
+             step(row=2, chosen="stay", depths=best_left),  # survives two rows only: wrong, not fatal
+             step(row=3, chosen="jump", executed="stay", gated=True, depths=best_left)]  # a fallback counts too
+    (row,) = summarize(steps)
+    assert row["wrong_moves"] == 2 and row["fatal_wrong_moves"] == 0
+    assert COLUMNS[COLUMNS.index("solver_agreement") + 1:][:2] == ("wrong_moves", "fatal_wrong_moves")
+
+
+def test_a_death_on_a_wrong_move_is_fatal_and_a_trapped_death_is_not():
+    fatal = {"stay": 0, "left": 6, "right": 0, "jump": 0}
+    trapped = {"stay": 0, "left": 0, "right": 0, "jump": 0}
+    steps = [step(seed=0, row=0), step(seed=0, row=1, chosen="stay", depths=fatal, alive=False,
+                                        death_cause="ran_into_gap", rows_survived=1),
+             step(seed=1, row=0), step(seed=1, row=1, chosen="stay", depths=trapped, alive=False,
+                                        death_cause="ran_into_gap", rows_survived=1)]
+    (row,) = summarize(steps)
+    assert row["fatal_wrong_moves"] == 1
+    assert row["wrong_moves"] == 1  # nothing was better on the trapped row, so it is not a wrong move
+
+
 def test_jump_share_is_the_share_of_executed_jumps():
     steps = [step(chosen="jump"), step(row=2, chosen="jump", executed="stay", gated=True),
              step(row=3, chosen="left"), step(row=4, chosen="jump", alive=False, death_cause="jumped_into_gap")]
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_report.py`
Expected:

```text
FAILED tests/test_report.py::test_a_wrong_move_is_a_move_made_that_reaches_less_far_than_the_best
FAILED tests/test_report.py::test_a_death_on_a_wrong_move_is_fatal_and_a_trapped_death_is_not
2 failed, 28 passed in 0.20s
```

- [ ] **Step 3: Write the implementation**

Apply to `bakeoff/report.py`:

```diff
@@ -12,6 +12,7 @@ from bakeoff.senses import truth_of
 
 COLUMNS = ("player", "runs", "incomplete", "missing", "mean_rows", "median_rows", "finished",
            "ran_into_gap", "jumped_into_gap", "dodged_into_gap", "jump_share", "solver_agreement",
+           "wrong_moves", "fatal_wrong_moves",
            "fallback_rate", "invalid_rate", "error_rate",
            "requests", "spent", "cache_hits", "mean_latency_ms", "input_tokens", "output_tokens", "cost_usd",
            "brier_gap_ahead", "brier_left_safe",
@@ -75,6 +76,13 @@ def _agrees(step: dict) -> bool:
     return step["chosen_action"] in depths and depths[step["chosen_action"]] == max(depths.values())
 
 
+def _is_wrong(step: dict) -> bool:
+    """The move made (`executed_action`, a fallback included) reaches less far than the best move. What was done
+    on the track counts, not only what was chosen: a fallback `stay` into a gap is a wrong move too."""
+    depths = step["solver_depths"]
+    return step["executed_action"] in depths and depths[step["executed_action"]] < max(depths.values())
+
+
 def _is_fallback(step: dict) -> bool:
     """A gated `stay` is a fallback even though executed equals chosen."""
     return bool(step["gated"] or step["invalid"] or step["error"] is not None or step["chosen_action"] is None)
@@ -138,6 +146,10 @@ def _summarize_player(player: str, steps: list[dict], model: str | None = None)
            for cause in ("ran_into_gap", "jumped_into_gap", "dodged_into_gap")},
         "jump_share": _ratio(sum(s["executed_action"] == "jump" for s in steps), len(steps)),
         "solver_agreement": _ratio(sum(_agrees(s) for s in comparable), len(comparable)),
+        "wrong_moves": sum(_is_wrong(s) for s in steps),
+        # died on a row where some other move survived; a death where every move falls is "trapped", and the
+        # wrong move came earlier
+        "fatal_wrong_moves": sum(not f["alive"] and _is_wrong(f) for f in complete),
         "fallback_rate": _ratio(sum(_is_fallback(s) for s in steps), len(steps)),
         "invalid_rate": _ratio(sum(s["invalid"] for s in steps), len(steps)),
         "error_rate": _ratio(sum(s["error"] is not None for s in steps), len(steps)),
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_report.py`
Expected: `30 passed in 0.08s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `542 passed, 16 deselected in 36.85s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/report.py tests/test_report.py
git commit -F <message file>   # report: wrong moves and fatal wrong moves
```

---

### Task 2: The roster, embedded in every page

**Files:**
- Create: `bakeoff/roster.py`
- Modify: `bakeoff/view.py`
- Modify: `viewer/index.html`
- Test: `tests/test_roster.py`
- Test: `tests/test_view.py`

**Interfaces:**
- Consumes: `bakeoff.players.REGISTRY`.
- Produces: `bakeoff/roster.py`: `ROSTER` (tuple of characters `{id, name, sprite, skins: [{player, name, about, color, inks}]}`, sprites `fly`, `visor`, `chat`, `ox`, `bot`), `roster_json() -> list[dict]` (a copy), `players() -> list[str]`. `bakeoff/view.py`: `ROSTER_SLOT`; `render_html` fills `<script type="application/json" id="roster-data">` with `roster_json()` whenever the page has the slot. `viewer/index.html` carries the slot.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_roster.py`:

```python
import re

from bakeoff.players import REGISTRY
from bakeoff.roster import ROSTER, players, roster_json

HEX = re.compile(r"#[0-9A-F]{6}")


def test_every_registered_player_is_exactly_one_skin():
    assert sorted(players()) == sorted(REGISTRY)
    assert len(players()) == len(set(players()))


def test_the_characters_and_their_default_skins_in_the_select_screens_order():
    assert [c["name"] for c in ROSTER] == ["Fly", "Jev", "Haiku", "GLM Flash", "Bot"]
    assert [c["skins"][0]["player"] for c in ROSTER] == ["fly", "jev_plain", "haiku_plain", "glm_plain", "random"]
    jev = next(c for c in ROSTER if c["id"] == "jev")
    assert [s["name"] for s in jev["skins"]] == ["Plain", "Guided", "Step 1", "Step 2", "Map"]
    assert [s["player"] for s in jev["skins"]] == ["jev_plain", "jev_guided", "jev_step1", "jev_step2", "jev_map"]


def test_the_skin_colours_the_user_settled():
    colour = {s["player"]: s["color"] for c in ROSTER for s in c["skins"]}
    assert [colour[f"jev_{k}"] for k in ("plain", "guided", "step1", "step2", "map")] == \
        ["#B9BEC4", "#5FA35A", "#E6B422", "#B8404F", "#1E2227"]
    assert colour["haiku_plain"] == "#D97757" and colour["glm_plain"] == "#9AA0A6"
    assert colour["haiku_guided"] == colour["glm_guided"] == colour["jev_guided"]
    assert (colour["fly"], colour["fly2"]) == ("#AEB4BA", "#F7768E")
    assert (colour["random"], colour["solver"], colour["always_jump"]) == ("#8A9097", "#7AA2F7", "#E8EBED")


def test_every_colour_is_a_hex_colour_and_every_skin_says_what_it_does():
    for character in ROSTER:
        assert character["sprite"] in ("fly", "visor", "chat", "ox", "bot")
        for skin in character["skins"]:
            assert HEX.fullmatch(skin["color"]), skin
            assert all(len(k) == 1 and HEX.fullmatch(v) for k, v in skin["inks"].items()), skin
            assert skin["about"].endswith("."), skin


def test_the_json_is_a_copy():
    data = roster_json()
    data[0]["skins"][0]["inks"]["x"] = "#000000"
    data[0]["name"] = "changed"
    assert ROSTER[0]["name"] == "Fly" and "x" not in ROSTER[0]["skins"][0]["inks"]
```

Apply to `tests/test_view.py`:

```diff
@@ -4,6 +4,7 @@ import re
 import pytest
 
 from bakeoff.__main__ import main
+from bakeoff.roster import roster_json
 from bakeoff.view import DATA_SLOT, VIEWER_DIR, embed_json, render_html
 
 DATA = re.compile(r'<script type="application/json" id="replay-data">(.*?)</script>', re.S)
@@ -29,6 +30,12 @@ def test_render_inlines_every_file_and_the_data():
     assert DATA_SLOT not in page
 
 
+def test_every_page_carries_the_roster_live_or_replay():
+    for page in (render_html({"episodes": []}), render_html({"episodes": []}, live="/events", token="t")):
+        (data,) = re.findall(r'<script type="application/json" id="roster-data">(.*?)</script>', page, re.S)
+        assert json.loads(data) == roster_json()
+
+
 def test_the_page_makes_no_network_request():
     page = render_html({"episodes": []})
     assert not re.search(r"""(src|href)=["']?(https?:)?//""", page)
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_roster.py tests/test_view.py`
Expected:

```text
ERROR tests/test_roster.py
ERROR tests/test_view.py
2 errors in 0.15s
```

- [ ] **Step 3: Write the implementation**

Create `bakeoff/roster.py`:

```python
"""The Brain Battle roster: the characters, their skins, and what each skin is called and looks like
(docs/superpowers/specs/2026-09-25-brain-battle-design.md, section A; colours from docs/FRONTEND.md).

A skin is a player: the character is who plays, the skin is how (a question set and its rule, a fly's
input, a yardstick). Every registered player is exactly one skin, and a test keeps it so. The page gets
this as JSON (`roster_json`, embedded by `bakeoff/view.py`) and colours a runner by its skin in the
tunnel, the mind strip and every screen. The drawing itself, the grids and the inks they start from, is
the viewer's (`viewer/sprites.js`); a skin names its sprite, the colour of the sprite's body, and any
other cell it recolours."""

from __future__ import annotations

# the question sets as skins, in the select screen's order (decision 44); plain is the default skin
SETS = (
    ("plain", "Plain", "One broad question: “Which move?”, asked once, with no pointed question under it."),
    ("guided", "Guided", "One question over the four moves, naming the tile each would land on. Code takes its "
                         "favourite."),
    ("step1", "Step 1", "Four yes/no questions: would each move land on a gap? Code picks the move least likely to."),
    ("step2", "Step 2", "Eight questions, two moves ahead. Code takes the lowest combined risk."),
    ("map", "Map", "One question per visible tile, then code plans a path through what it read."),
)
# per model, one look per set in the order above: plain is the character's own colour; guided green, step1
# yellow, step2 red, map black with its eyes (or visor) lit blue, which the user chose (docs/FRONTEND.md)
SET_LOOKS = {
    "jev": ({"color": "#B9BEC4"}, {"color": "#5FA35A"}, {"color": "#E6B422"}, {"color": "#B8404F"},
            {"color": "#1E2227", "inks": {"V": "#7AA2F7"}}),
    "haiku": ({"color": "#D97757"}, {"color": "#5FA35A"}, {"color": "#E6B422"}, {"color": "#B8404F"},
              {"color": "#1E2227", "inks": {"k": "#7AA2F7"}}),
    "glm": ({"color": "#9AA0A6"}, {"color": "#5FA35A"}, {"color": "#E6B422"}, {"color": "#B8404F"},
            {"color": "#1E2227", "inks": {"n": "#3A4046", "k": "#7AA2F7"}}),
}


def _skin(player: str, name: str, about: str, color: str, inks: dict | None = None) -> dict:
    return {"player": player, "name": name, "about": about, "color": color, "inks": dict(inks or {})}


def _model(character_id: str, name: str, sprite: str) -> dict:
    skins = [_skin(f"{character_id}_{suffix}", skin_name, about, **look)
             for (suffix, skin_name, about), look in zip(SETS, SET_LOOKS[character_id])]
    return {"id": character_id, "name": name, "sprite": sprite, "skins": skins}


# in the select screen's order; each character's first skin is its default
ROSTER = (
    {"id": "fly", "name": "Fly", "sprite": "fly", "skins": [
        _skin("fly", "Looming", "Looming → escape reflex. Untrained, innate wiring; how gaps become input, which "
                         "neurons we read and the thresholds are ours.", "#AEB4BA"),
        _skin("fly2", "Sideways", "Side-lane gaps drive a sideways channel; dodge before jump. Untrained; its input, "
                                  "read-out, rule and thresholds are ours.", "#F7768E", {"e": "#AEB4BA"}),
    ]},
    _model("jev", "Jev", "visor"),
    _model("haiku", "Haiku", "chat"),
    _model("glm", "GLM Flash", "ox"),
    {"id": "bot", "name": "Bot", "sprite": "bot", "skins": [
        _skin("random", "Random", "A coin: any move. A yardstick, not a contestant.", "#8A9097"),
        _skin("solver", "Solver", "A perfect search: what the track allows. A yardstick, not a contestant.", "#7AA2F7"),
        _skin("always_jump", "Always jump", "Jumps every row. A yardstick, not a contestant.", "#E8EBED"),
    ]},
)


def roster_json() -> list[dict]:
    """The roster as the page reads it: a fresh copy, so nothing a caller does can change the table."""
    return [{**character, "skins": [{**skin, "inks": dict(skin["inks"])} for skin in character["skins"]]}
            for character in ROSTER]


def players() -> list[str]:
    """Every skin's player, in the roster's order."""
    return [skin["player"] for character in ROSTER for skin in character["skins"]]
```

Apply to `bakeoff/view.py`:

```diff
@@ -7,9 +7,12 @@ import json
 import re
 from pathlib import Path
 
+from bakeoff.roster import roster_json
+
 VIEWER_DIR = Path(__file__).resolve().parent.parent / "viewer"
 DATA_SLOT = '<script type="application/json" id="replay-data">null</script>'
 BENCH_SLOT = '<script type="application/json" id="bench-data">null</script>'
+ROSTER_SLOT = '<script type="application/json" id="roster-data">null</script>'
 _STYLESHEET = re.compile(r'<link rel="stylesheet" href="([^"]+)">')
 _SCRIPT = re.compile(r'<script src="([^"]+)"></script>')
 _CSS_URL = re.compile(r"url\(([^)]*)\)", re.IGNORECASE)  # CSS function names are case-insensitive
@@ -48,7 +51,8 @@ def render_html(replay: dict, viewer_dir: Path | str = VIEWER_DIR, live: str | N
     for a server. `token`: the session's token, which every request of the page carries. `page_name`:
     the viewer page to fill, `index.html` (the replay) or `bench.html` (the benchmark); both carry the
     same data slot. `bench`: the benchmark's numbers for the same runs, for the page's Analysis tab;
-    a page with no benchmark slot must not be given any."""
+    a page with no benchmark slot must not be given any. A page with a roster slot always gets the roster
+    (`bakeoff/roster.py`), live or replay, so a runner is drawn in its skin in both."""
     viewer_dir = Path(viewer_dir)
     page = (viewer_dir / page_name).read_text(encoding="utf-8")
     if page.count(DATA_SLOT) != 1:
@@ -69,6 +73,10 @@ def render_html(replay: dict, viewer_dir: Path | str = VIEWER_DIR, live: str | N
     # lambdas, so that a backslash in a file is never read as a regex group reference
     page = _STYLESHEET.sub(lambda m: "<style>\n" + _stylesheet(viewer_dir / m.group(1)) + "</style>", page)
     page = _SCRIPT.sub(lambda m: "<script>\n" + (viewer_dir / m.group(1)).read_text(encoding="utf-8") + "</script>", page)
+    if page.count(ROSTER_SLOT) > 1:
+        raise ValueError(f"{viewer_dir / page_name} must contain the roster slot at most once")
+    page = page.replace(ROSTER_SLOT, '<script type="application/json" id="roster-data">' + embed_json(roster_json())
+                        + "</script>")
     if bench is not None:
         page = page.replace(BENCH_SLOT, '<script type="application/json" id="bench-data">' + embed_json(bench) + "</script>")
     return page.replace(DATA_SLOT, '<script type="application/json" id="replay-data">' + embed_json(replay) + "</script>")
```

Apply to `viewer/index.html`:

```diff
@@ -159,6 +159,7 @@
 
 <script type="application/json" id="replay-data">null</script>
 <script type="application/json" id="bench-data">null</script>
+<script type="application/json" id="roster-data">null</script>
 <script src="timeline.js"></script>
 <script src="tunnel.js"></script>
 <script src="sprites.js"></script>
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_roster.py tests/test_view.py`
Expected: `27 passed in 0.96s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `548 passed, 16 deselected in 36.06s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/roster.py bakeoff/view.py tests/test_roster.py tests/test_view.py viewer/index.html
git commit -F <message file>   # the Brain Battle roster, embedded in every page
```

---

### Task 3: Sprites in skins, the ox and the robot; the page's roster

**Files:**
- Create: `viewer/roster.js`
- Modify: `viewer/sprites.js`
- Test: `viewer/tests/roster.test.js`
- Test: `viewer/tests/sprites.test.js`

**Interfaces:**
- Consumes: the roster JSON's shape (task 2).
- Produces: `viewer/sprites.js`: `GRIDS.ox`, `GRIDS.bot`, inks `t y n z`, `BODY` (the body ink of each grid), `pixels(name, {p, open, color, inks})` where `color` repaints the body cells and `inks` any named cell; `drawSprite(ctx, name, px, options)` takes the same options. `viewer/roster.js` (global `Roster`, or `require`): `Roster.make(data) -> {has(player), label(player), look(player) -> {sprite, color, inks}, ink(player) -> colour or null, colour(player)}`, plus `luminance(hex)`, `contrast(a, b)`. `make(null)` is a roster with nobody on it.

- [ ] **Step 1: Write the failing tests**

Create `viewer/tests/roster.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const Roster = require("../roster.js");

// a slice of bakeoff/roster.py's JSON, enough for every rule here
const DATA = [
  { id: "jev", name: "Jev", sprite: "visor", skins: [
    { player: "jev_plain", name: "Plain", about: "One broad question.", color: "#B9BEC4", inks: {} },
    { player: "jev_step1", name: "Step 1", about: "Four yes/no questions.", color: "#E6B422", inks: {} },
    { player: "jev_step2", name: "Step 2", about: "Eight questions.", color: "#B8404F", inks: {} },
    { player: "jev_map", name: "Map", about: "One question per tile.", color: "#1E2227", inks: { V: "#7AA2F7" } },
  ] },
  { id: "bot", name: "Bot", sprite: "bot", skins: [
    { player: "solver", name: "Solver", about: "A perfect search.", color: "#7AA2F7", inks: {} },
  ] },
];

test("a player is labelled with its character and skin, as on the select screen", () => {
  const roster = Roster.make(DATA);
  assert.equal(roster.label("jev_step1"), "Jev · Step 1");
  assert.equal(roster.label("solver"), "Bot · Solver");
});

test("a player not on the roster keeps its upper-case name and the grey block", () => {
  for (const roster of [Roster.make(DATA), Roster.make(null)]) {
    assert.equal(roster.label("my_bot"), "MY_BOT");
    assert.deepEqual(roster.look("my_bot"), { sprite: "block", color: null, inks: {} });
    assert.equal(roster.ink("my_bot"), null);
    assert.equal(roster.has("my_bot"), false);
  }
});

test("a skin's look is its character's sprite in the skin's colours", () => {
  assert.deepEqual(Roster.make(DATA).look("jev_map"), { sprite: "visor", color: "#1E2227", inks: { V: "#7AA2F7" } });
});

test("a label takes its skin's colour only where that colour reads on the page's ground", () => {
  const roster = Roster.make(DATA);
  assert.equal(roster.ink("jev_step1"), "#E6B422");
  assert.equal(roster.ink("jev_step2"), "#B8404F");
  assert.equal(roster.ink("jev_map"), null); // black on black: the page's own ink, and the swatch shows the black
  assert.equal(roster.colour("jev_map"), "#1E2227");
});

test("contrast is WCAG's ratio", () => {
  assert.equal(Roster.contrast("#FFFFFF", "#000000"), 21);
  assert.equal(Roster.contrast("#777777", "#777777"), 1);
});
```

Replace the whole of `viewer/tests/sprites.test.js` with:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const { GRIDS, INKS, BODY, visorCells, pixels, sizeOf } = require("../sprites.js");

test("the approved grids, character for character", () => {
  assert.deepEqual(GRIDS.fly, ["..ee.ee..", "...bbb...", ".w.bbb.w.", "ww.bbb.ww", "wwwbbbwww", "ww.bbb.ww", ".w.bbb.w.", "...b.b...", "..b...b.."]);
  assert.deepEqual(GRIDS.chat, [".ooooooo.", ".ooooooo.", ".okoookoo", "ooooooooo", ".ooooooo.", ".ooooooo.", ".o.o.o.o.", ".o.o.o.o."]);
  assert.deepEqual(GRIDS.visor, [".jjjjj.", "jjjjjjj", "jVVVvvj", "jjjjjjj", ".jjjjj.", "..jjj..", ".jjjjj.", ".jjjjj.", ".j...j.", ".j...j."]);
  assert.deepEqual({ w: INKS.w, b: INKS.b, e: INKS.e, o: INKS.o, k: INKS.k, j: INKS.j, V: INKS.V, v: INKS.v },
    { w: "#AEB4BA", b: "#3A4046", e: "#F7768E", o: "#D97757", k: "#1A0E0A", j: "#B9BEC4", V: "#FFFFFF", v: "#15181C" });
});

test("every grid is a rectangle drawn only in known inks", () => {
  for (const [name, grid] of Object.entries(GRIDS)) {
    assert.equal(new Set(grid.map((line) => line.length)).size, 1, name);
    for (const ink of grid.join("").replace(/\./g, "")) assert.ok(INKS[ink], name + " uses " + ink);
  }
  assert.deepEqual(sizeOf("fly"), sizeOf("fly_open")); // the jump does not change the sprite's size
});

test("the visor's slit lights round(5 p) cells from the left", () => {
  assert.deepEqual(visorCells(0), [false, false, false, false, false]);
  assert.deepEqual(visorCells(0.5), [true, true, true, false, false]); // round(2.5) is 3
  assert.deepEqual(visorCells(1), [true, true, true, true, true]);
  assert.deepEqual(visorCells(0.29), [true, false, false, false, false]);
  assert.deepEqual(visorCells(1.7), [true, true, true, true, true]);
  assert.deepEqual(visorCells(null), [false, false, false, false, false]); // no answer: dark
  assert.deepEqual(visorCells(NaN), [false, false, false, false, false]);
});

test("the visor's pixels carry the slit, left to right", () => {
  const slit = (p) => pixels("visor", { p }).filter((c) => c.y === 2 && c.x >= 1 && c.x <= 5).map((c) => c.ink);
  assert.deepEqual(slit(1), Array(5).fill(INKS.V));
  assert.deepEqual(slit(0.4), [INKS.V, INKS.V, INKS.v, INKS.v, INKS.v]);
  assert.deepEqual(slit(undefined), Array(5).fill(INKS.v));
});

test("the fly opens its wings in a jump and keeps its red eyes", () => {
  const folded = pixels("fly"), open = pixels("fly", { open: true });
  assert.notDeepEqual(folded, open);
  for (const sprite of [folded, open]) assert.equal(sprite.filter((c) => c.ink === INKS.e).length, 4);
  assert.ok(open.some((c) => c.x === 0 && c.y === 1 && c.ink === INKS.w)); // a wing tip raised to the edge
});

test("an unknown sprite is a plain grey block", () => {
  assert.deepEqual(pixels("nobody"), pixels("block"));
  assert.ok(pixels("nobody").every((c) => c.ink === INKS.g));
  assert.deepEqual(sizeOf("nobody"), { width: 5, height: 7 });
});

test("the ox and the robot, character for character, each with a body ink", () => {
  assert.deepEqual(GRIDS.ox, ["y.........y", "yy.......yy", ".yttttttty.", "..ttttttt..", "..tktttkt..", "..ttttttt..", "...nnnnn...", "...nknkn...", "....y.y....", ".....y....."]);
  assert.deepEqual(GRIDS.bot, [".zzzzz.", ".zkzkz.", ".zzzzz.", ".zzzzz.", "..zzz..", "zzzzzzz", "z.zzz.z", "..z.z..", "..z.z.."]);
  for (const name of Object.keys(GRIDS)) assert.ok(GRIDS[name].join("").includes(BODY[name]), name + " has its body ink");
});

test("a skin paints the body in its colour and recolours only the cells it names", () => {
  const plain = pixels("chat"), map = pixels("chat", { color: "#1E2227", inks: { k: "#7AA2F7" } });
  assert.equal(map.length, plain.length);
  plain.forEach((cell, i) => {
    const want = cell.ink === INKS.o ? "#1E2227" : cell.ink === INKS.k ? "#7AA2F7" : cell.ink;
    assert.equal(map[i].ink, want);
  });
});

test("a skin's colour reaches the fly's open wings and the visor's lit slit takes the skin's ink", () => {
  const sideways = pixels("fly", { open: true, color: "#F7768E", inks: { e: "#AEB4BA" } }); // red wings, grey eyes
  const wings = GRIDS.fly_open.join("").split("w").length - 1;
  assert.equal(sideways.filter((c) => c.ink === "#F7768E").length, wings);
  assert.equal(sideways.filter((c) => c.ink === "#AEB4BA").length, 4);
  const slit = pixels("visor", { p: 1, color: "#1E2227", inks: { V: "#7AA2F7" } }).filter((c) => c.y === 2 && c.x >= 1 && c.x <= 5);
  assert.deepEqual(slit.map((c) => c.ink), Array(5).fill("#7AA2F7"));
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `node --test viewer/tests/sprites.test.js viewer/tests/roster.test.js`
Expected:

```text
✖ viewer/tests/roster.test.js
✖ the ox and the robot, character for character, each with a body ink
✖ a skin paints the body in its colour and recolours only the cells it names
✖ a skin's colour reaches the fly's open wings and the visor's lit slit takes the skin's ink
ℹ pass 6
ℹ fail 4
```

- [ ] **Step 3: Write the implementation**

Create `viewer/roster.js`:

```javascript
// The roster as the page reads it (bakeoff/roster.py, embedded by bakeoff/view.py): each player's
// character and skin, the label the select screen gives it ("Jev · Step 1"), how its sprite is coloured,
// and the ink its label can be written in. Pure and tested under node.
(function (root) {
  "use strict";

  const GROUND = "#0A0A0A"; // the page's background (--bg): a label must be readable on it
  const MIN_CONTRAST = 3; // WCAG's floor for large or bold text; the labels are short and bold

  // relative luminance of a #RRGGBB colour (WCAG 2)
  function luminance(hex) {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
      .map((c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)));
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  function contrast(a, b) {
    const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
  }

  // `data` is the embedded roster, or null (a page built before the roster): then every player keeps its
  // upper-case name and the grey block, as before.
  function make(data) {
    const bySkin = new Map();
    for (const character of data || []) {
      for (const skin of character.skins || []) bySkin.set(skin.player, { character, skin });
    }
    const found = (player) => bySkin.get(player) || null;
    return {
      has: (player) => bySkin.has(player),
      label: (player) => {
        const f = found(player);
        return f ? f.character.name + " · " + f.skin.name : String(player).toUpperCase();
      },
      // what Sprites.drawSprite needs: the character's sprite and the skin's colours
      look: (player) => {
        const f = found(player);
        return f ? { sprite: f.character.sprite, color: f.skin.color, inks: f.skin.inks || {} }
          : { sprite: "block", color: null, inks: {} };
      },
      // the skin's colour for its label, or null where it would not read on the page's dark ground (the Map
      // skins' black): the label then keeps the page's own ink, and the swatch beside it shows the colour
      ink: (player) => {
        const f = found(player);
        return f && contrast(f.skin.color, GROUND) >= MIN_CONTRAST ? f.skin.color : null;
      },
      colour: (player) => (found(player) ? found(player).skin.color : null),
    };
  }

  const api = { make, luminance, contrast };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Roster = api;
})(typeof window !== "undefined" ? window : globalThis);
```

Replace the whole of `viewer/sprites.js` with:

```javascript
// The runners as pixel sprites: grids of characters, one character = one pixel, `.` is empty.
// All of them are our own drawings. The LLM's orange critter is our rendition, not anyone's artwork, and
// so are GLM Flash's ox and the yardsticks' boxy robot. A skin (bakeoff/roster.py) recolours a sprite:
// `color` paints its body cells (BODY) and `inks` any other named cell.
// `pixels` and `visorCells` are pure (tested under node); `drawSprite` paints on a canvas.
(function (root) {
  "use strict";

  const GRIDS = {
    // a fruit fly seen from behind: pale folded wings, dark body, red eyes
    fly: ["..ee.ee..", "...bbb...", ".w.bbb.w.", "ww.bbb.ww", "wwwbbbwww", "ww.bbb.ww", ".w.bbb.w.", "...b.b...", "..b...b.."],
    // the same fly in a jump: wings open
    fly_open: ["..ee.ee..", "w..bbb..w", "ww.bbb.ww", "wwwbbbwww", "ww.bbb.ww", "w..bbb..w", "...bbb...", "...b.b...", "..b...b.."],
    chat: [".ooooooo.", ".ooooooo.", ".okoookoo", "ooooooooo", ".ooooooo.", ".ooooooo.", ".o.o.o.o.", ".o.o.o.o."],
    // "the visor": a pale monolith with one slit of five cells, V lit and v unlit (see visorCells)
    visor: [".jjjjj.", "jjjjjjj", "jVVVvvj", "jjjjjjj", ".jjjjj.", "..jjj..", ".jjjjj.", ".jjjjj.", ".j...j.", ".j...j."],
    // GLM Flash, an ox for its preview name Ox Alpha: horns, a greyscale head, a muzzle with a ring
    ox: ["y.........y", "yy.......yy", ".yttttttty.", "..ttttttt..", "..tktttkt..", "..ttttttt..", "...nnnnn...", "...nknkn...", "....y.y....", ".....y....."],
    // the yardsticks: a simple boxy robot, no antenna, no mouth
    bot: [".zzzzz.", ".zkzkz.", ".zzzzz.", ".zzzzz.", "..zzz..", "zzzzzzz", "z.zzz.z", "..z.z..", "..z.z.."],
    // a player that is not on the roster: a plain grey block
    block: ["ggggg", "ggggg", "ggggg", "ggggg", "ggggg", "ggggg", "ggggg"],
  };
  const INKS = { w: "#AEB4BA", b: "#3A4046", e: "#F7768E", o: "#D97757", k: "#1A0E0A", j: "#B9BEC4", V: "#FFFFFF", v: "#15181C", g: "#7C848D",
    t: "#9AA0A6", y: "#D5D9DD", n: "#5C636B", z: "#8A9097" };
  // the ink a skin's colour replaces: the fly's wings, the visor, the critter, the ox's head, the robot
  const BODY = { fly: "w", fly_open: "w", visor: "j", chat: "o", ox: "t", bot: "z", block: "g" };
  const SLIT = 5;

  // Which of the visor's five cells are lit, left to right: round(5 * p) of them, where p is the
  // probability Jev gave that the move it made does not land on a gap. Unknown p: none.
  function visorCells(p) {
    const lit = typeof p === "number" && isFinite(p) ? Math.round(SLIT * Math.max(0, Math.min(1, p))) : 0;
    return Array.from({ length: SLIT }, (_, i) => i < lit);
  }

  // The sprite as a list of {x, y, ink}, (0, 0) being the top left pixel. options: {p} for the visor's
  // slit, {open: true} for the fly's open wings, {color, inks} for a skin.
  function pixels(name, options) {
    const opts = options || {};
    const drawn = name === "fly" && opts.open ? "fly_open" : GRIDS[name] ? name : "block";
    const grid = GRIDS[drawn];
    const cells = name === "visor" ? visorCells(opts.p) : [];
    const own = Object.assign({}, opts.inks || {});
    if (opts.color) own[BODY[drawn]] = opts.color;
    let slit = 0;
    const out = [];
    grid.forEach((line, y) => {
      for (let x = 0; x < line.length; x++) {
        let ink = line[x];
        if (ink === ".") continue;
        if (ink === "V" || ink === "v") ink = cells[slit++] ? "V" : "v";
        out.push({ x, y, ink: own[ink] || INKS[ink] });
      }
    });
    return out;
  }

  function sizeOf(name) {
    const grid = GRIDS[name] || GRIDS.block;
    return { width: grid[0].length, height: grid.length };
  }

  // The sprite painted once at whole-pixel size, so a translucent or rotated runner shows no seams
  // between its pixels. Cached per look: there are only a handful.
  const bitmaps = {};
  function bitmap(name, px, options) {
    const opts = options || {};
    const key = [name, px, !!opts.open, name === "visor" ? visorCells(opts.p).filter(Boolean).length : 0,
      opts.color || "", JSON.stringify(opts.inks || {})].join(" ");
    if (!bitmaps[key]) {
      const { width, height } = sizeOf(name);
      const canvas = document.createElement("canvas");
      canvas.width = width * px;
      canvas.height = height * px;
      const paint = canvas.getContext("2d");
      for (const cell of pixels(name, opts)) {
        paint.fillStyle = cell.ink;
        paint.fillRect(cell.x * px, cell.y * px, px, px);
      }
      bitmaps[key] = canvas;
    }
    return bitmaps[key];
  }

  // Paints the sprite standing on the canvas origin: feet at (0, 0), head toward -y, centred on x.
  // The caller translates and rotates the context (Tunnel.place). px is the whole-number size of one pixel.
  function drawSprite(ctx, name, px, options) {
    const image = bitmap(name, px, options);
    ctx.imageSmoothingEnabled = false; // pixel art stays hard-edged on a side wall too
    ctx.drawImage(image, -Math.round(image.width / 2), -image.height);
  }

  const api = { GRIDS, INKS, BODY, visorCells, pixels, sizeOf, drawSprite };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Sprites = api;
})(typeof window !== "undefined" ? window : globalThis);
```

- [ ] **Step 4: Run the task's tests**

Run: `node --test viewer/tests/sprites.test.js viewer/tests/roster.test.js`
Expected: `pass 14, fail 0`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `548 passed, 16 deselected in 36.45s`

- [ ] **Step 6: Commit**

```bash
git add viewer/roster.js viewer/sprites.js viewer/tests/roster.test.js viewer/tests/sprites.test.js
git commit -F <message file>   # sprites: skins, the ox and the robot; the page's roster
```

---

### Task 4: Runners in their skins, tagged as on the select screen

**Files:**
- Modify: `viewer/app.js`
- Modify: `viewer/index.html`
- Modify: `viewer/minds.js`
- Modify: `viewer/picker.js`
- Modify: `viewer/viewer.css`
- Test: `tests/test_view.py`
- Test: `viewer/tests/minds.test.js`

**Interfaces:**
- Consumes: `Roster.make` and `Sprites.pixels`/`drawSprite` options (task 3); the embedded `roster-data` (task 2).
- Produces: `Minds.useRoster(roster)` (null to clear) and `Minds.tagHtml(player)` (a `label tag` span with a swatch, in the skin's ink where it reads); `Minds.tagOf(player)` answers the roster's label when one is set, the old upper-case tag otherwise. `Picker.list` writes `Minds.tagHtml`. `app.js` makes the roster from `#roster-data`, calls `Minds.useRoster`, and draws each runner as `roster.look(player)`. `index.html` loads `roster.js` after `sprites.js`.

`viewer/index.html` and `viewer/app.js` are long: insert each hunk exactly where its context lines are. A byte-compare against the prototype follows.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_view.py`:

```diff
@@ -51,7 +51,8 @@ def test_the_page_says_what_is_ours_about_jev_and_the_figures():
     assert "looks one step ahead only" in page
     assert "landed on a gap about as often as always staying would have" in page
     assert "our own drawing and nobody's official artwork" in page
-    assert "The blue marks the mind in focus and the tiles it was shown, nothing else." in page
+    assert ("The blue marks the mind in focus and the tiles it was shown; elsewhere it is a skin's own colour "
+            "(Bot · Solver, the Map skins' eyes).") in page
 
 
 def test_the_page_keeps_every_caveat_about_the_fly_and_about_jevs_questions():
@@ -72,7 +73,7 @@ def test_the_page_carries_the_chart_rules_the_analysis_tab_draws_with():
 
 def test_every_script_the_page_names_exists_and_app_comes_last():
     names = re.findall(r'<script src="([^"]+)"></script>', (VIEWER_DIR / "index.html").read_text())
-    assert names == ["timeline.js", "tunnel.js", "sprites.js", "stage.js", "minds.js", "log.js", "picker.js", "tabs.js",
+    assert names == ["timeline.js", "tunnel.js", "sprites.js", "roster.js", "stage.js", "minds.js", "log.js", "picker.js", "tabs.js",
                      "feed.js", "lobby.js", "bench.js", "bench_view.js", "app.js"]
     assert all((VIEWER_DIR / name).is_file() for name in names)
 
```

Apply to `viewer/tests/minds.test.js`:

```diff
@@ -189,6 +189,27 @@ test("tags are short and uppercase, and an unknown player still gets one", () =>
   assert.equal(Minds.tagOf("my_bot"), "MY_BOT");
 });
 
+test("with the roster, a tag is the select screen's label after a swatch of the skin's colour", () => {
+  const Roster = require("../roster.js");
+  Minds.useRoster(Roster.make([{ id: "jev", name: "Jev", sprite: "visor", skins: [
+    { player: "jev_step1", name: "Step 1", about: "", color: "#E6B422", inks: {} },
+    { player: "jev_map", name: "Map", about: "", color: "#1E2227", inks: { V: "#7AA2F7" } },
+    { player: "jev_x", name: "<b>", about: "", color: "#E6B422\"><script>", inks: {} }] }]));
+  try {
+    assert.equal(Minds.tagOf("jev_step1"), "Jev \u00b7 Step 1");
+    assert.equal(Minds.tagHtml("jev_step1"), '<span class="label tag" style="color:#E6B422"><span class="swatch" ' +
+      'style="background:#E6B422" aria-hidden="true"></span>Jev \u00b7 Step 1</span>');
+    // black does not read on the dark page: the label keeps the page's ink, the swatch still shows the skin
+    assert.equal(Minds.tagHtml("jev_map"), '<span class="label tag"><span class="swatch" style="background:#1E2227" ' +
+      'aria-hidden="true"></span>Jev \u00b7 Map</span>');
+    assert.equal(Minds.tagHtml("solver"), '<span class="label tag">SOLVER</span>'); // not on this roster
+    assert.equal(Minds.tagHtml("jev_x").includes("<script>") || Minds.tagHtml("jev_x").includes("<b>"), false);
+  } finally {
+    Minds.useRoster(null);
+  }
+  assert.equal(Minds.tagOf("jev_step1"), "JEV STEP 1");
+});
+
 test("the two plain chat models get the same panel", () => {
   const answered = frame({ answers: { text: '{"action": "jump"}', stop_reason: "end_turn" }, chosen_action: "jump" });
   const haiku = Minds.mind({ player: "haiku_plain", questions: [] }, answered, context());
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_view.py tests/test_viewer_js.py`
Expected:

```text
FAILED tests/test_view.py::test_the_page_says_what_is_ours_about_jev_and_the_figures
FAILED tests/test_view.py::test_every_script_the_page_names_exists_and_app_comes_last
FAILED tests/test_viewer_js.py::test_viewer_javascript - AssertionError: ✔ es...
3 failed, 20 passed in 1.41s
```

- [ ] **Step 3: Write the implementation**

Apply to `viewer/app.js`:

```diff
@@ -17,7 +17,9 @@
   const esc = Minds.esc;
   const cell = Minds.cell;
   const DEMO = ["fly", "jev_step1", "haiku_plain"]; // the default view; an older replay has only jev_plain
-  const SPRITE = { fly: "fly", fly2: "fly", jev_step1: "visor", haiku_plain: "chat" }; // everyone else is a plain grey block
+  const rosterSlot = document.getElementById("roster-data");
+  const roster = Roster.make(rosterSlot ? JSON.parse(rosterSlot.textContent) : null); // each runner's character and skin
+  Minds.useRoster(roster);
   const ABOUT = {
     fly: "Fruit fly connectome, untrained",
     fly2: "The same fly, a richer input and read-out (ours)",
@@ -209,7 +211,7 @@
       const panel = document.createElement("article");
       panel.className = "mind";
       panel.dataset.player = episode.player;
-      panel.innerHTML = '<header><span class="label tag">' + esc(Minds.tagOf(episode.player)) + '</span><span class="about">' +
+      panel.innerHTML = "<header>" + Minds.tagHtml(episode.player) + '<span class="about">' +
         esc(ABOUT[episode.player] || "") + (model ? " · " + esc(model) : "") + '</span></header><div class="body"><p class="status"></p>' +
         '<div class="decision"></div><details class="log"><summary class="label">Its log</summary><ol class="log-lines"></ol></details></div>';
       strip.appendChild(panel);
@@ -368,7 +370,8 @@
     drawn.sort((a, b) => (a.s.id === view.focus) - (b.s.id === view.focus)); // the mind in focus is painted last
     view.hit = [];
     for (const { s, at } of drawn) {
-      const name = SPRITE[s.id] || "block";
+      const look = roster.look(s.id);
+      const name = look.sprite;
       const px = Math.max(2, Math.round(size * 0.008 * at.scale));
       const sprite = Sprites.sizeOf(name);
       const o = overlap[s.id];
@@ -378,8 +381,8 @@
       ctx.globalAlpha = o.alpha * (1 - at.fall);
       const fan = o.fan * sprite.width * px * 0.62;
       ctx.translate(fan, -at.lift + at.fall * size * 0.12);
-      Sprites.drawSprite(ctx, name, px, { p: Minds.visorP(s.frame), open: s.air > 0.15 });
-      // the tag, upright whatever wall the runner stands on; blue only for the mind in focus. Runners that
+      Sprites.drawSprite(ctx, name, px, { p: Minds.visorP(s.frame), open: s.air > 0.15, color: look.color, inks: look.inks });
+      // the tag, upright whatever wall the runner stands on, in its skin's colour; blue brackets for the mind in focus. Runners that
       // overlap share one column of tags over the middle of the group, so the tags never overprint.
       const inFocus = s.id === view.focus;
       const text = inFocus ? "[ " + Minds.tagOf(s.id) + " ]" : Minds.tagOf(s.id);
@@ -394,7 +397,7 @@
       ctx.lineWidth = 3;
       ctx.strokeStyle = "#0A0A0A";
       ctx.strokeText(text, 0, 0);
-      ctx.fillStyle = inFocus ? INK.accent : INK.muted;
+      ctx.fillStyle = inFocus ? INK.accent : roster.ink(s.id) || INK.muted;
       ctx.fillText(text, 0, 0);
       ctx.restore();
       view.hit.push({ id: s.id, x: at.x, y: at.y, r: sprite.height * px });
```

Apply to `viewer/index.html`:

```diff
@@ -28,7 +28,7 @@
       <p class="label corner bottom" id="notice" hidden></p>
     </div>
     <div id="strip"></div>
-    <p class="note"><span id="sight"></span> The blue marks the mind in focus and the tiles it was shown, nothing else.
+    <p class="note"><span id="sight"></span> The blue marks the mind in focus and the tiles it was shown; elsewhere it is a skin's own colour (Bot · Solver, the Map skins' eyes).
       Everyone is on the same row at the same time: a jump covers two rows, so it takes two ticks.</p>
   </section>
 
@@ -120,8 +120,9 @@
         always right. <code>jev_plain</code> is still in the level table for comparison; its request also carries two yes/no
         questions for calibration, which for the same reason are not a scaffold for its move. The LLM answers one question per
         row and is told the rules in the same words as <code>jev_plain</code>; what each was asked is under every panel.</p>
-      <p>The figures are ours too: a fruit fly, a visor whose slit shows how sure Jev is that its move is safe, and an
-        orange critter for the LLM, which is our own drawing and nobody's official artwork.</p>
+      <p>The figures are ours too: a fruit fly, a visor whose slit shows how sure Jev is that its move is safe, an
+        orange critter for Claude Haiku, an ox for GLM Flash and a boxy robot for the yardsticks, each our own drawing and
+        nobody's official artwork. A skin's colours are ours as well.</p>
     </div>
   </section>
 
@@ -163,6 +164,7 @@
 <script src="timeline.js"></script>
 <script src="tunnel.js"></script>
 <script src="sprites.js"></script>
+<script src="roster.js"></script>
 <script src="stage.js"></script>
 <script src="minds.js"></script>
 <script src="log.js"></script>
```

Apply to `viewer/minds.js`:

```diff
@@ -7,7 +7,7 @@
   const FLY_GROUPS = [
     ["DNa01", "steering"], ["DNb01", "steering"], ["DNp01", "Giant Fiber, escape jump"], ["DNa02", "logged only"],
   ];
-  // the short uppercase tag a runner carries in the tunnel and on its panel
+  // the short uppercase tag a runner carries when the page has no roster (a page built before Brain Battle)
   const TAGS = { fly: "FLY", fly2: "FLY2", solver: "SOLVER", random: "RANDOM", always_jump: "JUMPER",
     jev_plain: "JEV PLAIN", jev_guided: "JEV GUIDED", jev_step1: "JEV STEP 1", jev_step2: "JEV STEP 2", jev_map: "JEV MAP",
     haiku_plain: "HAIKU PLAIN", haiku_guided: "HAIKU GUIDED", haiku_step1: "HAIKU STEP 1", haiku_step2: "HAIKU STEP 2",
@@ -16,7 +16,19 @@
   // players that ask a question set (bakeoff/players/question_sets.py): Jev, Claude Haiku or GLM, and the set's name
   const SET_PLAYER = /^(jev|haiku|glm)_(step1|guided|step2|map)$/;
   const isSetPlayer = (player) => SET_PLAYER.test(player) && player !== "jev_step1";
-  const tagOf = (player) => TAGS[player] || String(player).toUpperCase();
+  // With the roster (roster.js, set once by app.js) a runner is labelled as on the select screen, "Jev · Step 1".
+  let roster = null;
+  const useRoster = (made) => { roster = made || null; };
+  const tagOf = (player) => (roster && roster.has(player) ? roster.label(player) : TAGS[player] || String(player).toUpperCase());
+  // The tag as markup: the label, in its skin's colour where that reads on the dark page, after a swatch of the
+  // skin's colour. A player not on the roster gets the plain tag. Every value is escaped.
+  const tagHtml = (player) => {
+    const colour = roster && roster.has(player) ? roster.colour(player) : null;
+    const ink = colour ? roster.ink(player) : null;
+    return '<span class="label tag"' + (ink ? ' style="color:' + esc(ink) + '"' : "") + ">" +
+      (colour ? '<span class="swatch" style="background:' + esc(colour) + '" aria-hidden="true"></span>' : "") +
+      esc(tagOf(player)) + "</span>";
+  };
   const DEATHS = {
     ran_into_gap: "ran straight into a gap",
     jumped_into_gap: "jumped into a gap",
@@ -340,7 +352,7 @@
     return "row " + Math.floor(state.row) + ", lane " + (((Math.round(state.lane) % lanes) + lanes) % lanes);
   }
 
-  const api = { esc, cell, bar, tagOf, sensesGrid, verdict, spikeRaster, flyMind, fly2Mind, oursFly2, jevMind, jevStep1Mind, visorP, chatMind, cost, asked,
+  const api = { esc, cell, bar, tagOf, tagHtml, useRoster, sensesGrid, verdict, spikeRaster, flyMind, fly2Mind, oursFly2, jevMind, jevStep1Mind, visorP, chatMind, cost, asked,
                 ours, mind, statusLine, isSetPlayer, readGrid, setMind };
   if (typeof module !== "undefined" && module.exports) module.exports = api;
   else root.Minds = api;
```

Apply to `viewer/picker.js`:

```diff
@@ -6,7 +6,6 @@
 
   const Mind = typeof module !== "undefined" && module.exports ? require("./minds.js") : root.Minds;
   const esc = Mind.esc;
-  const tagOf = Mind.tagOf;
 
   // One button per player of the replay, pressed when its runner is shown. A player that did not run
   // the track in view cannot be shown, so its button is disabled and says so.
@@ -20,7 +19,7 @@
       return '<button type="button" class="pick-player" data-player="' + esc(player) + '"' +
         ' aria-pressed="' + on + '"' + (present.has(player) ? "" : " disabled") +
         (title ? ' title="' + esc(title) + '"' : "") + ">" +
-        '<span class="label tag">' + esc(tagOf(player)) + "</span>" +
+        Mind.tagHtml(player) +
         (present.has(player) ? "" : '<span class="note">not on this track</span>') + "</button>";
     }).join("");
   }
```

Apply to `viewer/viewer.css`:

```diff
@@ -60,7 +60,9 @@ section > h2.label { margin-bottom: 20px; }
 .mind { min-width: 0; padding: 0 16px 20px; background: var(--panel); border-right: 1px solid var(--hairline);
   border-top: 2px solid transparent; font-size: var(--size-small); cursor: pointer; transition: opacity var(--fast) var(--ease); }
 .mind[aria-current="true"] { border-top-color: var(--accent); cursor: default; }
-.mind[aria-current="true"] .tag { color: var(--accent); }
+.mind header .tag { flex: none; white-space: nowrap; }
+.tag .swatch { display: inline-block; width: 0.75em; height: 0.75em; margin-right: 0.45em; vertical-align: -0.05em;
+  border: 1px solid var(--line-strong); }
 .mind.fallen .decision { opacity: 0.45; }
 .mind header { display: flex; align-items: baseline; gap: 12px; padding: 14px 0 10px; min-height: 44px; }
 .mind header .about { color: var(--muted); font-size: var(--size-small); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_view.py tests/test_viewer_js.py`
Expected: `23 passed in 0.69s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `548 passed, 16 deselected in 35.62s`

- [ ] **Step 6: Commit**

```bash
git add tests/test_view.py viewer/app.js viewer/index.html viewer/minds.js viewer/picker.js viewer/tests/minds.test.js viewer/viewer.css
git commit -F <message file>   # the page: runners in their skins, tagged as on the select screen
```

---

### Task 5: One run's results, and the end event carries them

**Files:**
- Modify: `bakeoff/live.py`
- Create: `bakeoff/results.py`
- Test: `tests/test_live_run.py`
- Test: `tests/test_results.py`

**Interfaces:**
- Consumes: `report.summarize` (with task 1's columns), `bench.load`, `bench.Source`, `bench.player_numbers`, `session.PRICE_USD`, `players.PAID`.
- Produces: `bakeoff/results.py`: `results_of(run_dir) -> {run_id, status, seeds, game: {version, max_rows}, players: [{...summarize row, paid, price_usd, cost_estimate_usd, s_per_row, tracks: [{seed, rows, complete, finished, death_cause, trapped}]}]}`, players in the run's own order. `LiveRun._end_event` adds `"results"`: that dict, or `{"why": "the results could not be worked out: ..."}`.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_live_run.py`:

```diff
@@ -72,10 +72,25 @@ def test_the_stream_is_the_replay_in_the_replays_own_shapes(tmp_path):
     assert name == "end"
     # the benchmark of the run just played rides along (decision 36); the rest is the replay's own shapes
     assert end.pop("bench")["runs"] == replay["runs"][0]["run_id"].split()  # one run, scored where it was recorded
+    # and so do its results, for the results screen (Brain Battle, section E)
+    assert [p["player"] for p in end.pop("results")["players"]] == ["solver", "stayer"]
     assert end == {"status": "completed", "runs": replay["runs"], "scoreboard": replay["scoreboard"]}
     json.dumps(events)
 
 
+def test_results_that_cannot_be_worked_out_never_cost_the_end_event(tmp_path, monkeypatch):
+    import bakeoff.results
+
+    def broken(run_dir):
+        raise RuntimeError("boom")
+
+    monkeypatch.setattr(bakeoff.results, "results_of", broken)
+    live, events = run_live(tmp_path, [make_player("solver")])
+    name, end = events[-1]
+    assert name == "end" and end["status"] == "completed"
+    assert end["results"] == {"why": "the results could not be worked out: RuntimeError('boom')"}
+
+
 def test_the_directory_is_a_normal_completed_run(tmp_path):
     live, _ = run_live(tmp_path, [make_player("solver"), Scripted("stayer", "stay")])
     meta = json.loads((live.run_dir / "meta.json").read_text())
```

Create `tests/test_results.py`:

```python
"""The results screen's numbers (bakeoff/results.py), from real run directories played by free and scripted
players. No network, no fly brain."""

import json

from bakeoff.game.rules import V1
from bakeoff.live import LiveRun
from bakeoff.players import make_player
from bakeoff.players.base import Decision
from bakeoff.results import results_of
from bakeoff.session import PRICE_USD


class Scripted:
    """Always the same move, as a paid player named `name` would log it (latency, no cache hit)."""

    def __init__(self, name, action):
        self.name, self.action = name, action

    def reset(self, game, seed): pass

    def act(self, senses):
        return Decision(self.action, questions={"q": 1}, latency_ms=100.0)

    def observe(self, executed_action): pass

    def close(self): pass


def play(tmp_path, players, seed=1001, run_id="r1"):
    live = LiveRun(players, seed, out_root=tmp_path, rules=V1, max_rows=40, run_id=run_id)
    live.run()
    return live.run_dir


def test_one_entry_per_player_in_the_runs_order_with_how_its_track_ended(tmp_path):
    out = results_of(play(tmp_path, [make_player("solver"), Scripted("stayer", "stay")]))
    assert out["run_id"] == "r1" and out["status"] == "completed" and out["seeds"] == [1001]
    assert out["game"] == {"version": "v1", "max_rows": 40}
    solver, stayer = out["players"]
    assert (solver["player"], stayer["player"]) == ("solver", "stayer")
    assert solver["tracks"] == [{"seed": 1001, "rows": 40, "complete": True, "finished": True, "death_cause": None,
                                 "trapped": False}]
    (track,) = stayer["tracks"]
    assert track["complete"] and not track["finished"] and track["death_cause"] == "ran_into_gap"
    assert track["rows"] == stayer["mean_rows"] < 40
    assert stayer["fatal_wrong_moves"] == 1 and stayer["wrong_moves"] >= 1  # the solver would have lived
    assert solver["wrong_moves"] == 0
    json.dumps(out)


def test_cost_is_live_requests_at_the_pages_price_and_free_players_cost_nothing(tmp_path):
    out = results_of(play(tmp_path, [make_player("random"), Scripted("haiku_step1", "stay")]))
    random_, haiku = out["players"]
    assert (random_["paid"], random_["price_usd"], random_["cost_estimate_usd"]) == (False, 0.0, 0.0)
    assert haiku["paid"] and haiku["price_usd"] == PRICE_USD["haiku_step1"]
    assert haiku["requests"] > 0
    assert haiku["cost_estimate_usd"] == haiku["requests"] * PRICE_USD["haiku_step1"]
    assert haiku["s_per_row"] is not None  # 100 ms a live decision


def test_a_stopped_run_keeps_its_players_rows_and_is_not_a_death(tmp_path):
    live = LiveRun([make_player("solver")], 1001, out_root=tmp_path, rules=V1, max_rows=40, run_id="stopped")
    live.prepare()
    live.cancel()  # given up before the first decision
    out = results_of(live.run_dir)
    assert out["status"] == "interrupted"
    (solver,) = out["players"]
    assert solver["tracks"] == [] and solver["runs"] == 0 and solver["s_per_row"] is None


def test_a_death_where_every_move_falls_is_trapped(tmp_path):
    run_dir = tmp_path / "hand"
    run_dir.mkdir()
    base = {"player": "p", "seed": 1000, "chosen_action": "stay", "executed_action": "stay", "gated": False,
            "invalid": False, "error": None, "latency_ms": None, "usage": None, "cache_hit": False, "finished": False,
            "death_cause": None}
    steps = [{**base, "row": 0, "alive": True, "rows_survived": 0, "solver_depths": {"stay": 1, "left": 0, "right": 0,
                                                                                     "jump": 3}},
             {**base, "row": 1, "alive": False, "rows_survived": 1, "death_cause": "ran_into_gap",
              "solver_depths": {"stay": 0, "left": 0, "right": 0, "jump": 0}}]
    (run_dir / "p.jsonl").write_text("".join(json.dumps(s) + "\n" for s in steps))
    (player,) = results_of(run_dir)["players"]
    assert player["tracks"][0]["trapped"] is True
    assert player["fatal_wrong_moves"] == 0 and player["wrong_moves"] == 1  # the wrong move was row 0's stay
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_results.py tests/test_live_run.py`
Expected:

```text
ERROR tests/test_results.py
1 error in 0.14s
```

- [ ] **Step 3: Write the implementation**

Apply to `bakeoff/live.py`:

```diff
@@ -152,16 +152,22 @@ class LiveRun:
     def _end_event(self, replay: dict) -> dict:
         """The last event of a run: what the page needs to settle. It carries the benchmark of the run
         that just played, scored here rather than in the browser, so the Analysis tab fills in without
-        a reload. One track is rarely enough for an interval, and the numbers say so themselves."""
+        a reload, and its results (bakeoff/results.py) for the results screen. One track is rarely
+        enough for an interval, and the numbers say so themselves."""
         from bakeoff.bench import benchmark_of  # numpy: only when a run ends
+        from bakeoff.results import results_of
 
         try:
             numbers, why = benchmark_of([self.run_dir])
         except Exception as e:  # the run's end is what the page waits for: never lose it to the extra
             numbers, why = None, f"the benchmark could not be scored: {e!r}"
+        try:
+            results = results_of(self.run_dir)
+        except Exception as e:  # the same: the page says why instead of waiting for ever
+            results = {"why": f"the results could not be worked out: {e!r}"}
 
         return {"status": self.status, "runs": replay["runs"], "scoreboard": replay["scoreboard"],
-                "bench": numbers if numbers else {"why": why}}
+                "bench": numbers if numbers else {"why": why}, "results": results}
 
     def _write_meta(self) -> None:
         (self.run_dir / "meta.json").write_text(json.dumps(self.meta, indent=2))
```

Create `bakeoff/results.py`:

```python
"""The results of one recorded run, for the Brain Battle results screen
(docs/superpowers/specs/2026-09-25-brain-battle-design.md, section E). Reads files only, spends nothing.

One entry per player of the run: the report's row (`summarize`), how each of its tracks ended, the
benchmark's time per row, and a cost estimate of live requests times the page's price per request. The
page ranks and words it; the numbers are all worked out here."""

from __future__ import annotations

from pathlib import Path

from bakeoff.bench import Source, load, player_numbers
from bakeoff.players import PAID
from bakeoff.report import load_meta, load_steps, summarize
from bakeoff.session import PRICE_USD


def _ending(steps: list[dict]) -> dict:
    """How one track ended for one player, from its last record. `trapped`: it died on a row where every move
    fell, so no move there was wrong (the wrong move came earlier)."""
    last = max(steps, key=lambda s: s["row"])
    complete = bool(last["finished"] or not last["alive"])
    depths = last.get("solver_depths") or {}
    return {"seed": last["seed"], "rows": last["rows_survived"], "complete": complete, "finished": bool(last["finished"]),
            "death_cause": last["death_cause"],
            "trapped": bool(not last["alive"] and depths and max(depths.values()) == 0)}


def results_of(run_dir: Path | str) -> dict:
    """{run_id, status, seeds, game, players: [...]} for one run directory. A player the run planned but never
    started still gets an entry, with no tracks."""
    run_dir = Path(run_dir)
    steps = load_steps(run_dir)
    meta = load_meta(run_dir) or {}
    loaded = load([Source(run_dir)])
    max_rows = (meta.get("game") or {}).get("max_rows") or max((s["rows_survived"] for s in steps), default=0)
    rows = {row["player"]: row for row in summarize(steps, meta)}
    order = list(dict.fromkeys([*(meta.get("players") or []), *rows]))
    players = []
    for player in order:
        own = [s for s in steps if s["player"] == player]
        by_seed: dict[int, list[dict]] = {}
        for s in own:
            by_seed.setdefault(s["seed"], []).append(s)
        episodes = [e for e in (*loaded.episodes, *loaded.incomplete) if e.player == player]
        timing = player_numbers(episodes, max_rows)["s_per_row"] if episodes else None
        paid = player in PAID
        price = PRICE_USD.get(player, 0.0) if paid else 0.0
        row = rows[player]
        players.append({**row, "paid": paid, "price_usd": price,
                        # live requests at the page's price: an estimate, not the provider's bill
                        "cost_estimate_usd": row["requests"] * price,
                        "s_per_row": timing,
                        "tracks": [_ending(by_seed[seed]) for seed in sorted(by_seed)]})
    return {"run_id": meta.get("run_id") or run_dir.name, "status": meta.get("status"),
            "seeds": meta.get("seeds") or sorted({s["seed"] for s in steps}),
            "game": {"version": (meta.get("game") or {}).get("version"), "max_rows": max_rows},
            "players": players}
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_results.py tests/test_live_run.py`
Expected: `20 passed in 1.25s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `553 passed, 16 deselected in 35.39s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/live.py bakeoff/results.py tests/test_live_run.py tests/test_results.py
git commit -F <message file>   # results: one run's numbers for the results screen, in the end event too
```

---

### Task 6: Records: newest episode of each player and track

**Files:**
- Modify: `bakeoff/bench.py`
- Create: `bakeoff/records.py`
- Test: `tests/test_bench.py`
- Test: `tests/test_records.py`

**Interfaces:**
- Consumes: `bench.load`, `bench.benchmark`, `report.load_meta`/`load_steps`, `session.FIRST_PRACTICE_SEED`, `Rules`.
- Produces: `bench.Source(run_dir, players=None, episodes=None)` where `episodes` is a `frozenset[tuple[str, int]]` narrowing the directory to those pairs. `bakeoff/records.py`: `pick(out_root, rules) -> (list[Source], left_out: int, unreadable: list[str])`, `past_runs(out_root, current=None) -> list[dict]` (`run_id, status, started_at, finished_at, seeds, players, game, current`, newest first), `records_of(out_root, rules, current=None) -> {game, max_rows, bench, why, left_out, unreadable, runs}`.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_bench.py`:

```diff
@@ -31,6 +31,15 @@ def test_load_merges_directories_and_takes_only_the_named_players(tmp_path):
     assert loaded.game.version == "v2" and loaded.run_ids == ("a", "b") and loaded.episodes[1].model == "m"
 
 
+def test_a_source_can_be_narrowed_to_some_player_and_track_pairs(tmp_path):
+    a = write_run(tmp_path, "a", episode("fly", 1000, 3) + episode("fly", 1001, 4) + episode("haiku_plain", 1000, 2),
+                  {"game": V2})
+    b = write_run(tmp_path, "b", episode("fly", 1000, 9), {"game": V2})
+    loaded = load([Source(a, episodes=frozenset({("fly", 1001), ("haiku_plain", 1000)})), Source(b)])
+    assert sorted((e.player, e.seed, e.run_id) for e in loaded.episodes) == \
+        [("fly", 1000, "b"), ("fly", 1001, "a"), ("haiku_plain", 1000, "a")]
+
+
 def test_an_episode_that_neither_died_nor_finished_is_set_aside(tmp_path):
     stopped = [record(player="haiku_plain", seed=1000, row=r) for r in range(5)]  # alive at its last record
     run = write_run(tmp_path, "a", stopped + episode("haiku_plain", 1001, 3) + episode("solver", 1000, 150, finished=True))
```

Create `tests/test_records.py`:

```python
"""Records (bakeoff/records.py): which episodes count, and the past runs. Hand-made run directories only."""

from bakeoff.game.rules import V1, V2
from bakeoff.records import pick, records_of
from tests.test_bench import V2 as V2_BLOCK
from tests.test_bench import episode
from tests.test_replay import record, write_run


def test_each_player_and_track_counts_once_from_the_newest_run_that_completed_it(tmp_path):
    write_run(tmp_path, "20260921-100000", episode("fly", 1000, 3) + episode("fly", 1001, 5), {"game": V2_BLOCK})
    write_run(tmp_path, "20260922-100000", episode("fly", 1000, 9), {"game": V2_BLOCK})
    stopped = [record(player="fly", seed=1001, row=r) for r in range(4)]  # alive at its last record: not a result
    write_run(tmp_path, "20260923-100000", stopped, {"game": V2_BLOCK})
    sources, left_out, unreadable = pick(tmp_path, V2)
    assert [(s.run_dir.name, sorted(s.episodes)) for s in sources] == [
        ("20260922-100000", [("fly", 1000)]), ("20260921-100000", [("fly", 1001)])]
    assert left_out == 1 and unreadable == []
    (fly,) = records_of(tmp_path, V2)["bench"]["players"]
    assert fly["seeds"] == 2 and fly["mean_rows"] == 7  # 9 on track 1000 (the newer run) and 5 on track 1001


def test_tournament_seeds_other_games_and_other_lengths_stay_out(tmp_path):
    write_run(tmp_path, "a", episode("fly", 999, 3) + episode("fly", 1000, 4), {"game": V2_BLOCK})
    write_run(tmp_path, "b", episode("fly", 1001, 4), {"game": V1.to_json()})
    write_run(tmp_path, "c", episode("fly", 1002, 4), {"game": {**V2_BLOCK, "max_rows": 40}})
    write_run(tmp_path, "d", episode("fly", 1003, 4), {})  # no game block: from before game versions
    sources, _, _ = pick(tmp_path, V2)
    assert [(s.run_dir.name, sorted(s.episodes)) for s in sources] == [("a", [("fly", 1000)])]


def test_the_past_runs_newest_first_and_only_this_sessions_run_is_current(tmp_path):
    write_run(tmp_path, "20260921-100000", episode("fly", 1000, 3),
              {"game": V2_BLOCK, "status": "completed", "players": ["fly"], "seeds": [1000]})
    write_run(tmp_path, "20260925-100000", episode("jev", 1000, 3),  # an old name comes back as the new one
              {"game": V2_BLOCK, "status": "running", "players": ["jev"], "seeds": [1000]})
    runs = records_of(tmp_path, V2, current="20260921-100000")["runs"]
    assert [(r["run_id"], r["status"], r["players"], r["current"]) for r in runs] == [
        ("20260925-100000", "running", ["jev_plain"], False), ("20260921-100000", "completed", ["fly"], True)]
    assert runs[0]["game"] == "v2" and runs[0]["seeds"] == [1000]


def test_records_say_why_instead_of_failing(tmp_path):
    assert records_of(tmp_path / "missing", V2)["why"] == "no run has been recorded yet."
    write_run(tmp_path, "a", episode("fly", 999, 3), {"game": V2_BLOCK})
    out = records_of(tmp_path, V2)
    assert out["bench"] is None and out["why"] == "no completed practice track of game v2 has been recorded yet."
    bad = write_run(tmp_path, "b", episode("fly", 1000, 3), {"game": V2_BLOCK})
    (bad / "fly.jsonl").write_text("not json\n{}\n")  # broken before its last line
    assert records_of(tmp_path, V2)["unreadable"] == ["b"]
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_records.py tests/test_bench.py`
Expected:

```text
ERROR tests/test_records.py
1 error in 0.83s
```

- [ ] **Step 3: Write the implementation**

Apply to `bakeoff/bench.py`:

```diff
@@ -18,9 +18,11 @@ from bakeoff.report import PRICES_USD_PER_MTOK, load_meta, load_steps
 
 @dataclass(frozen=True)
 class Source:
-    """A run directory and the players to take from it (None: all of them)."""
+    """A run directory and the players to take from it (None: all of them). `episodes`, when given, narrows it to
+    those (player, seed) pairs: Records takes each pair from the newest run that completed it (bakeoff/records.py)."""
     run_dir: Path
     players: tuple[str, ...] | None = None
+    episodes: frozenset[tuple[str, int]] | None = None
 
 
 def parse_source(arg: str) -> Source:
@@ -91,6 +93,8 @@ def load(sources: list[Source]) -> Loaded:
             if missing:
                 raise ValueError(f"{source.run_dir} has no {', '.join(missing)}; it has {', '.join(sorted(present))}")
             steps = [s for s in steps if s["player"] in source.players]
+        if source.episodes is not None:
+            steps = [s for s in steps if (s["player"], s["seed"]) in source.episodes]
         run_ids.append(run_id)
         grouped: dict[tuple[str, int], list[dict]] = {}
         for s in steps:
```

Create `bakeoff/records.py`:

```python
"""Records, for the Brain Battle records screen (docs/superpowers/specs/2026-09-25-brain-battle-design.md,
section F): the leaderboard and the pairs over every recorded practice track of this game, and the past
runs. Reads files only, spends nothing. The numbers are `bakeoff bench`'s; nothing here adds a statistic.

A live session replays tracks, so one (player, seed) can sit in several run directories, which `bench.load`
rightly refuses. Records takes each pair from the newest run that completed it and leaves the older copies
out, and says how many it left out."""

from __future__ import annotations

from pathlib import Path

from bakeoff.bench import Source, benchmark, load
from bakeoff.game.rules import Rules
from bakeoff.report import load_meta, load_steps
from bakeoff.session import FIRST_PRACTICE_SEED


def _run_dirs(out_root: Path) -> list[Path]:
    """Every run directory, newest first (run ids are timestamps)."""
    return sorted((d for d in out_root.iterdir() if d.is_dir() and (d / "meta.json").is_file()),
                  key=lambda d: d.name, reverse=True)


def _same_game(meta: dict, rules: Rules) -> bool:
    try:
        recorded = Rules.from_json(meta["game"])
    except (KeyError, TypeError, ValueError):
        return False  # a run from before game versions, or a game block this code cannot read
    return recorded.same_game(rules) and recorded.max_rows == rules.max_rows


def pick(out_root: Path | str, rules: Rules) -> tuple[list[Source], int, list[str]]:
    """(the sources to score, how many older complete episodes were left out, the run ids that could not be
    read). Only practice seeds, only runs of this game and length, only complete episodes."""
    taken: set[tuple[str, int]] = set()
    sources, left_out, unreadable = [], 0, []
    for run_dir in _run_dirs(Path(out_root)):
        meta = load_meta(run_dir) or {}
        if not _same_game(meta, rules):
            continue
        try:
            steps = load_steps(run_dir)
        except (OSError, ValueError):
            unreadable.append(run_dir.name)
            continue
        last: dict[tuple[str, int], dict] = {}
        for s in steps:
            key = (s["player"], s["seed"])
            if s["seed"] >= FIRST_PRACTICE_SEED and (key not in last or s["row"] > last[key]["row"]):
                last[key] = s
        mine = set()
        for key, step in last.items():
            if not (step["finished"] or not step["alive"]):
                continue  # stopped part way: not a result, and a newer or older complete one may stand in
            if key in taken:
                left_out += 1
            else:
                taken.add(key)
                mine.add(key)
        if mine:
            sources.append(Source(run_dir, episodes=frozenset(mine)))
    return sources, left_out, unreadable


def past_runs(out_root: Path | str, current: str | None = None) -> list[dict]:
    """Every run directory's meta.json, newest first. `current` is the run this session is playing: only it can
    be watched live, since the page cannot stream another process's run."""
    runs = []
    for run_dir in _run_dirs(Path(out_root)):
        meta = load_meta(run_dir) or {}
        runs.append({"run_id": run_dir.name, "status": meta.get("status"), "started_at": meta.get("started_at"),
                     "finished_at": meta.get("finished_at"), "seeds": meta.get("seeds") or [],
                     "players": meta.get("players") or [], "game": (meta.get("game") or {}).get("version"),
                     "current": run_dir.name == current})
    return runs


def records_of(out_root: Path | str, rules: Rules, current: str | None = None) -> dict:
    """{game, max_rows, bench (bench.benchmark's numbers, or None), why, left_out, unreadable, runs}. Like
    `benchmark_of`, it answers with a reason instead of failing."""
    out_root = Path(out_root)
    if not out_root.is_dir():
        return {"game": rules.version, "max_rows": rules.max_rows, "bench": None, "why": "no run has been recorded yet.",
                "left_out": 0, "unreadable": [], "runs": []}
    sources, left_out, unreadable = pick(out_root, rules)
    numbers, why = None, None
    if not sources:
        why = f"no completed practice track of game {rules.version} has been recorded yet."
    else:
        try:
            numbers = benchmark(load(sources))
        except (OSError, ValueError) as e:
            why = f"the records could not be scored: {e}"
    return {"game": rules.version, "max_rows": rules.max_rows, "bench": numbers, "why": why, "left_out": left_out,
            "unreadable": unreadable, "runs": past_runs(out_root, current)}
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_records.py tests/test_bench.py`
Expected: `22 passed in 2.40s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `558 passed, 16 deselected in 33.49s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/bench.py bakeoff/records.py tests/test_bench.py tests/test_records.py
git commit -F <message file>   # records: the leaderboard, the pairs and the past runs, newest episode of each player and track
```

---

### Task 7: The routes: state, results, records, replay

**Files:**
- Modify: `bakeoff/live_server.py`
- Modify: `bakeoff/session.py`
- Test: `tests/test_live_server.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: `results_of` (task 5), `records_of` (task 6), `replay.build_replay`, `track.generate_track`.
- Produces: `session.RUN_ID` (the run id pattern); `LiveSession.run_dir_of(run_id) -> Path | None`, `.results(run_id)`, `.replay(run_id)` (None for no such run), `.records()`; `state()` players gain `seeds_played: list[int]` and the state gains `track` (the seed's track JSON, or None). Routes behind the token: `GET /results?run=`, `GET /records`, `GET /replay?run=`: 404 for no such run, 500 `{ok: false, error}` for a run that cannot be read.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_live_server.py`:

```diff
@@ -221,3 +221,36 @@ def test_the_end_of_a_live_run_carries_the_benchmark_of_what_was_just_played(ser
     assert {p["player"] for p in end["bench"]["players"]} == {"solver", "random"}
     assert end["bench"]["players"][0]["seeds"] == 1  # one track: enough to score, never enough to rank
     assert all(p["ranked"] is False for p in end["bench"]["players"])
+
+
+def test_what_was_recorded_is_served_behind_the_token(server):
+    httpd, session = server
+    started = payload(httpd, "POST", "/run", {"seed": 1001, "players": ["solver", "random"]})[1]
+    session.wait(30)
+    run_id = started["run_id"]
+    status, results = payload(httpd, "GET", f"/results?run={run_id}")
+    assert status == 200 and [p["player"] for p in results["players"]] == ["solver", "random"]
+    status, replay = payload(httpd, "GET", f"/replay?run={run_id}")
+    assert status == 200 and replay["runs"][0]["run_id"] == run_id
+    status, records = payload(httpd, "GET", "/records")
+    assert status == 200 and [r["run_id"] for r in records["runs"]] == [run_id]
+    for path in (f"/results?run={run_id}", f"/replay?run={run_id}", "/records"):
+        assert get(httpd, path, token=None)[0].status == 403
+        assert get(httpd, path, token="wrong")[0].status == 403
+
+
+def test_a_run_that_is_not_a_recorded_run_directory_is_not_found(server):
+    httpd, _ = server
+    for path in ("/results", "/results?run=", "/results?run=..%2F..%2Fpyproject.toml", "/replay?run=../cache",
+                 "/replay?run=20990101-000000"):
+        assert get(httpd, path)[0].status == 404, path
+
+
+def test_a_run_directory_that_cannot_be_read_is_an_error_that_says_why(server):
+    httpd, session = server
+    started = payload(httpd, "POST", "/run", {"seed": 1001, "players": ["solver"]})[1]
+    session.wait(30)
+    log = session.run_dir_of(started["run_id"]) / "solver.jsonl"
+    log.write_text("not json\n" + log.read_text())  # broken before its last line: not a truncated tail
+    status, body = payload(httpd, "GET", f"/results?run={started['run_id']}")
+    assert status == 500 and body["ok"] is False and "cannot read that run" in body["error"]
```

Apply to `tests/test_session.py`:

```diff
@@ -257,3 +257,51 @@ def test_each_fly_says_what_it_is_and_nobody_else_needs_to(tmp_path, monkeypatch
     monkeypatch.setattr(fly2, "CALIBRATED", True)
     by_name = {p["name"]: p for p in session(tmp_path).state()["players"]}
     assert by_name["fly2"]["about"] == MAPPINGS[fly2.MAPPING].summary + ", walking-steering neurons, dodge before jump"
+
+
+def test_the_state_carries_every_track_a_player_has_played_and_the_real_track_for_the_preview(tmp_path):
+    from bakeoff.game.track import generate_track
+
+    lobby = session(tmp_path)
+    play(lobby, seed=1001, players=["solver"])
+    play(lobby, seed=1003, players=["solver", "random"])
+    state = lobby.state(seed=1002)
+    by_name = {p["name"]: p for p in state["players"]}
+    assert by_name["solver"]["seeds_played"] == [1001, 1003] and by_name["random"]["seeds_played"] == [1003]
+    assert by_name["fly"]["seeds_played"] == []
+    assert state["track"] == generate_track(1002, RULES).to_json()
+    assert lobby.state()["track"] is None and lobby.state(seed=-1)["track"] is None
+
+
+def test_only_a_recorded_run_directory_can_be_named(tmp_path):
+    lobby = session(tmp_path)
+    run_id = play(lobby, players=["solver"]).run.run_id
+    assert lobby.run_dir_of(run_id) == tmp_path / "runs" / run_id
+    (tmp_path / "runs" / "20260101-000000").mkdir()  # a directory with no meta.json is not a run
+    for wanted in (None, "", "../cache", "/etc", run_id + "/meta.json", "20260101-000000", "20990101-000000", "x"):
+        assert lobby.run_dir_of(wanted) is None, wanted
+    assert lobby.results("../cache") is None and lobby.replay("../cache") is None
+
+
+def test_results_replay_and_records_of_what_this_session_recorded(tmp_path):
+    lobby = session(tmp_path)
+    run_id = play(lobby, players=["solver", "random"]).run.run_id
+    results = lobby.results(run_id)
+    assert results["run_id"] == run_id and [p["player"] for p in results["players"]] == ["solver", "random"]
+    assert lobby.replay(run_id)["runs"][0]["run_id"] == run_id
+    records = lobby.records()
+    assert [r["run_id"] for r in records["runs"]] == [run_id]
+    assert records["runs"][0]["current"] is False  # it is over: it can be watched, not watched live
+    assert {p["player"] for p in records["bench"]["players"]} == {"solver", "random"}
+
+
+def test_the_run_playing_now_is_the_one_past_run_that_can_be_watched_live(tmp_path, monkeypatch):
+    lobby = session(tmp_path)
+    started = lobby.start(1001, [slow_player(monkeypatch)])
+    try:
+        (run,) = lobby.records()["runs"]
+        assert run["run_id"] == started.run.run_id and run["current"] is True and run["status"] == "running"
+    finally:
+        lobby.cancel()
+        lobby.wait(30)
+    assert lobby.records()["runs"][0]["current"] is False
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_session.py tests/test_live_server.py`
Expected:

```text
FAILED tests/test_session.py::test_the_state_carries_every_track_a_player_has_played_and_the_real_track_for_the_preview
FAILED tests/test_session.py::test_only_a_recorded_run_directory_can_be_named
FAILED tests/test_session.py::test_results_replay_and_records_of_what_this_session_recorded
FAILED tests/test_session.py::test_the_run_playing_now_is_the_one_past_run_that_can_be_watched_live
FAILED tests/test_live_server.py::test_what_was_recorded_is_served_behind_the_token
FAILED tests/test_live_server.py::test_a_run_directory_that_cannot_be_read_is_an_error_that_says_why
6 failed, 40 passed in 9.64s
```

- [ ] **Step 3: Write the implementation**

Apply to `bakeoff/live_server.py`:

```diff
@@ -15,6 +15,9 @@ the run.
 | `POST /run`        | `{seed, players}`: start a run, or refuse and name the reason |
 | `POST /cancel`     | stop the run that is going |
 | `GET /events`      | the frames of a run, Server-Sent Events (`?run=<run_id>`) |
+| `GET /results`     | the results of a recorded run (`?run=<run_id>`), for the results screen |
+| `GET /records`     | the leaderboard, the pairs and the past runs, for the records screen |
+| `GET /replay`      | the replay of a recorded run (`?run=<run_id>`), for Records' Watch |
 """
 
 from __future__ import annotations
@@ -101,6 +104,9 @@ def serve(page: str | None, session: LiveSession, port: int = 8000) -> Threading
             elif self._route == EVENTS_PATH:
                 if self._token():
                     self._events()
+            elif self._route in ("/results", "/records", "/replay"):
+                if self._token():
+                    self._recorded()
             else:
                 self.send_error(404)
 
@@ -127,6 +133,21 @@ def serve(page: str | None, session: LiveSession, port: int = 8000) -> Threading
             except OSError as e:  # the run directory could not be made: nothing was started
                 self._json({"ok": False, "error": f"cannot start the run: {e}"}, status=500)
 
+        def _recorded(self) -> None:
+            """What was recorded: files only, nothing spent. A run that is not a recorded run is a 404; a run
+            directory that cannot be read is a 500 that says why, so the page can say it too."""
+            session = self.server.session
+            try:
+                if self._route == "/records":
+                    return self._json(session.records())
+                wanted = self._query().get("run")
+                out = session.results(wanted) if self._route == "/results" else session.replay(wanted)
+            except (OSError, ValueError) as e:
+                return self._json({"ok": False, "error": f"cannot read that run: {e}"}, status=500)
+            if out is None:
+                return self.send_error(404)
+            self._json(out)
+
         def _page(self) -> None:
             if self.server.page is None:
                 return self.send_error(503)
```

Apply to `bakeoff/session.py`:

```diff
@@ -9,6 +9,7 @@ at a time. The page asks it what can be run (`state`), starts a run (`start`) an
 from __future__ import annotations
 
 import json
+import re
 import secrets
 import threading
 import time
@@ -17,6 +18,7 @@ from pathlib import Path
 
 from bakeoff.clients.core import DiskCache, RequestBudget, SharedBudget
 from bakeoff.game.rules import Rules
+from bakeoff.game.track import generate_track
 from bakeoff.live import LiveRun
 from bakeoff.players import PAID, REGISTRY, fly2, make_player
 from bakeoff.players.names import canonical
@@ -39,6 +41,10 @@ PRICE_USD = {"haiku_plain": 0.0006, "haiku_step1": 0.0010, "haiku_guided": 0.000
 # every player here asks its provider once a row, so a track of N rows costs at worst N requests
 REQUESTS_PER_ROW = 1
 
+# what a run id looks like (a timestamp, and a counter when two runs start in one second): anything else the page
+# sends as `run=` names no run, and no path is ever built from it
+RUN_ID = re.compile(r"[0-9]{8}-[0-9]{6}(-[0-9]+)?")
+
 
 def model_of(name: str) -> str | None:
     """The model a paid player asks, as its client asks for it. Nothing overrides it: no command takes a
@@ -175,6 +181,8 @@ class LiveSession:
                 "model_answered": answered.get(name) if paid else None,
                 "requests_left": self.budgets[name].remaining if paid else None,
                 "played_before": seed is not None and seed in played.get(name, []),
+                # every track it has a recorded run of, for the track select's marks
+                "seeds_played": played.get(name, []),
                 # why this player cannot play this track, so the page can say so before anything is asked
                 "why_not": None if seed is None else self.why_not(name, seed),
             })
@@ -186,6 +194,8 @@ class LiveSession:
             "max_requests": self.max_requests, "tournament": self.tournament,
             "first_practice_seed": FIRST_PRACTICE_SEED,
             "seed": seed,
+            # the real track, for the track select's preview: the rules stay in Python
+            "track": None if seed is None or seed < 0 else generate_track(seed, self.rules).to_json(),
             "ready": {"seed": self.ready_seed, "players": list(self.ready_players)},
             "players": players,
             # `replay` is the empty replay of this run: the page resets itself to it and fills it from
@@ -289,6 +299,37 @@ class LiveSession:
                 players.append(make_player(name))
         return players
 
+    # ---- what was recorded -----------------------------------------------------------------------
+    def run_dir_of(self, run_id: str | None) -> Path | None:
+        """The directory of a recorded run, or None. Only a run id of the usual shape that names a directory
+        directly under `out_root` holding a meta.json: nothing the page sends becomes any other path."""
+        if not run_id or not RUN_ID.fullmatch(run_id):
+            return None
+        run_dir = self.out_root / run_id
+        return run_dir if (run_dir / "meta.json").is_file() else None
+
+    def results(self, run_id: str | None) -> dict | None:
+        """The results screen's numbers for a recorded run (bakeoff/results.py), or None for no such run."""
+        from bakeoff.results import results_of  # numpy: only when asked
+
+        run_dir = self.run_dir_of(run_id)
+        return None if run_dir is None else results_of(run_dir)
+
+    def replay(self, run_id: str | None) -> dict | None:
+        """The replay of a recorded run, for Records' Watch, or None for no such run."""
+        from bakeoff.replay import build_replay
+
+        run_dir = self.run_dir_of(run_id)
+        return None if run_dir is None else build_replay([run_dir])
+
+    def records(self) -> dict:
+        """The records screen's numbers (bakeoff/records.py). Reads every run directory, so it is worked out when
+        the page asks, never on a timer."""
+        from bakeoff.records import records_of
+
+        current = self.run.run_id if self.run is not None and self.status == "running" else None
+        return records_of(self.out_root, self.rules, current=current)
+
     def find(self, run_id: str | None) -> LiveRun | None:
         """The run with this id, whether it is still going or already closed; without an id, the
         run going now (or the last one). The page opens one event stream per run and names it."""
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_session.py tests/test_live_server.py`
Expected: `46 passed in 8.81s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `565 passed, 16 deselected in 38.87s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/live_server.py bakeoff/session.py tests/test_live_server.py tests/test_session.py
git commit -F <message file>   # the server: seeds played and the real track in the state; results, records and replays of recorded runs
```

---

## After the tasks (controller only)

- [ ] **Look at it.** Build a replay of recorded v2 runs with `uv run python -m bakeoff view <runs> --output <scratchpad>/replay.html`.
  - Open it in a browser. Check each runner's character and skin colours, the tags and swatches, and a Map skin's label.
  - Nothing in the suite sees colour.
- [ ] **Live smoke with a fly**, once no other session is running a fly (`pgrep -fl "bakeoff"`):
  - Run `uv run python -m bakeoff live --port 0 --seed 1001 --players fly,solver --start` and open the page.
  - Check that the run plays, that the `end` event carries `results` (with `fatal_wrong_moves` and `tracks`), that `/records` lists the run, and that `/results?run=<id>` answers.
  - Stop it with the page's Cancel or at its end; never leave a fly process running.
- [ ] **Docs:**
  - `CLAUDE.md`: `roster.js` in the list of pure JavaScript; the three new routes in the `bakeoff live` paragraph.
  - `docs/STEP_RECORD.md` or `docs/REPLAY_DATA.md`: wherever the report's columns are listed.
  - `docs/NEXT.md` and `docs/FRONTEND.md`'s "Where this stands".
  - Read what any docs agent wrote before calling the docs done.
- [ ] **One whole-branch design review** (the most capable model), aimed at:
  - the `run=` handling and the token;
  - Records' dedupe and what it leaves out;
  - the honesty surface: the `about` lines, the page's blue note and the figures note;
  - that nothing new reads a name from disk without `canonical()`.

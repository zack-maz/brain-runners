# Phase 5b: The Demo Player — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the replay page becomes the demo player: the fly, the composed Jev and the LLM run one concrete tunnel together as pixel figures under a fixed camera, their minds in a strip underneath, blue as the cursor, in the user's brand, still one offline file.

**Architecture:** the spine of phase 4 stays (Python builds the replay object and owns the rules; JavaScript draws). `viewer/tunnel.js` loses its camera lane and gains `seenOutline` and `place`; three new pure modules carry everything with a rule in it (`sprites.js`: grids, inks, the visor's slit; `stage.js`: who overlaps, where auto-focus goes; `feed.js`: the one way frames reach the page, from an embedded replay now and from a live stream in 5c). `minds.js` gains the composed Jev's panel. `app.js`, `index.html` and `viewer.css` are rewritten as glue and look. `bakeoff/view.py` embeds the two brand fonts as base64.

**Tech Stack:** Python 3.13, `uv`, `pytest`; plain JavaScript, no build step, no npm, tests through `node --test`. No new dependency.

**Spec:** `docs/superpowers/specs/2026-09-20-demo-player-design.md`, sections "What you see", "Look" and "Phase 5b" (binding). Approved mockups: `docs/superpowers/specs/mockups/`.

**Branch:** `phase5-demo-player` (phase 5a is on it; never build on `main`).

## Global Constraints

- Python via `uv` only: `uv run pytest`, `uv run python -m ...`. Never `pip` or bare `python`. No `uv add`, no `npm`: the viewer has no packages.
- TDD: write the failing test, watch it fail, then implement. **No test touches the network.**
- **This phase spends no money** and needs no key and no fly brain: no `--max-requests`, no `pytest -m live`, no `pytest -m slow`, no `bakeoff run` with a paid player.
- **A guard blocks every shell command that contains the text `.env`.** Never put it in a command.
- **Frozen:** `bakeoff/game/`, `bakeoff/fly/`, `bakeoff/players/`, `bakeoff/clients/`, `bakeoff/runner.py`, `bakeoff/report.py`, `bakeoff/senses.py`, `calibration/`, `viewer/timeline.js`. The replay format does not change (`replay_version` stays 1); `bakeoff/replay.py` changes one constant (the order of `players`).
- **The page must work offline from one file:** no CDN, no web font request, no `fetch`, no external `src` or `href`. The only `url()` in the stylesheet is a bundled font, which `bakeoff/view.py` turns into base64.
- **Text from a log is never markup:** everything from a log reaches `innerHTML` only through `Minds.esc` or `Minds.cell`.
- **Rules of the game stay in Python.** "Which actions land on a gap" is read from the logged `solver_depths` (0 means the landing tile is a gap), not recomputed in JavaScript.
- **Brand** (`~/Documents/PROJECTS/BRAND/brand.css`, tokens verbatim): dark only; blue is the cursor and nothing else (the focused mind's tag, the top edge of its panel, the outline of the tiles it was shown); deaths and errors are `--bad`, warnings `--warn`; mono for short uppercase labels only; no gradients, no glow, no rounded cards; tap targets at least 44 px.
- **Honesty:** what is ours is labelled as ours on the page: the fly's numbers (read from the run), the composed Jev's wording and rule, the figures.
- Every code block below was run in a prototype and passes as written (final state: 267 fast tests, 9 deselected; 56 node tests inside one of them). The page was opened in a browser against the real practice runs of track 1000 at 1440 and 390 wide: no console error but the test server's missing favicon, no horizontal overflow, every transport button at least 44 px. If a test fails, suspect a transcription slip before redesigning.
- Commit after every task with the message given. The controller pre-writes each message to a file, attribution trailers included; the implementer runs exactly `git commit -F <that file>`, never `-m`, and checks `git log -1 --format=%B` afterwards.

## Decisions this plan makes beyond the spec

1. **`place` takes the clock as a fourth argument** (`place(state, lanes, size, camRow)`): a runner whose run was cut off stays where it stopped while the camera moves on, so it must be placed relative to the camera and hidden once the camera has passed it. Without the argument it is placed at its own row, as the spec's signature says.
2. **`overlaps` and `autoFocus` take what they need to be pure:** `overlaps(runners, lanes)` (lane distance is measured round the ring) and `autoFocus(current, states, heldSince, t)`, returning `{focus, heldSince}`. A hold that lies in the future (the user scrubbed back) is void.
3. **Danger is read from the solver's verdict, not recomputed:** an action "lands on a gap" when the frame's `solver_depths[action]` is 0. The rule of the game stays in Python.
4. **Tags are drawn upright** whatever wall the runner stands on, and runners that overlap share one column of tags over the middle of the group. The focused tag reads `[ JEV ]` in blue; all others are muted.
5. **Sprites are painted once to an offscreen bitmap per look and drawn as one image,** because painting translucent pixels one by one doubles the alpha where they touch. The fly's open-wing grid (`fly_open`) is ours, like every figure; the three approved grids are asserted character for character.
6. **The composed Jev's panel shows a missing answer as a dash, never 0%,** and takes the tie-break order from the log (`info.order`), escaped.
7. **Deaths and errors move from `warn` to `bad`** (`statusLine`, `verdict`); a stopped run stays a warning.
8. **`players` order becomes fly, jev_composed, llm, jev, then the rest** (`CONTESTANTS` in `bakeoff/replay.py`), which is the order of the panels and of keys 1, 2, 3. The default view is the demo's three; an older replay without the composed Jev shows the one-shot Jev in its place.
9. **Phone width:** the mind in focus is open and the others are one line each (tap to read); the transport has two rows and offers speeds 3 and 8 only, so every target stays 44 px.
10. **`feed.js` already speaks the live stream's events** (`episode`, `frame`, `end`, `error`, in the replay's own shapes, history replayed on reconnect and de-duplicated here), so phase 5c adds a server and no second format. `fromEmbedded` never signals an end: a live page embeds an empty replay first.
11. **`view.py` refuses any stylesheet `url()` that is not `fonts/<name>.woff2`,** so the no-network rule is enforced where the page is built, not only tested.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `viewer/fonts/*.woff2`, `viewer/fonts/LICENSE.md` | the two brand fonts (OFL) and their licence note | 1 |
| `bakeoff/view.py`, `tests/test_view.py`, `viewer/viewer.css` (two `@font-face` rules) | fonts embedded as base64 | 1 |
| `viewer/tunnel.js`, `viewer/tests/tunnel.test.js` | fixed camera, `seenOutline`, `place` | 2 |
| `viewer/sprites.js`, `viewer/tests/sprites.test.js` | grids, inks, `visorCells`, `pixels`, `drawSprite` | 3 |
| `viewer/stage.js`, `viewer/tests/stage.test.js` | `overlaps`, `autoFocus` | 4 |
| `viewer/feed.js`, `viewer/tests/feed.test.js` | `fromEmbedded`, `fromStream` | 5 |
| `viewer/minds.js`, `viewer/tests/minds.test.js`, `bakeoff/replay.py`, `tests/test_replay.py`, `docs/REPLAY_DATA.md` | `jevComposedMind`, `visorP`, `tagOf`, bad/warn; the order of `players` | 6 |
| `viewer/app.js`, `viewer/index.html`, `viewer/viewer.css`, `tests/test_view.py`, `README.md`, `CLAUDE.md`, `docs/REPLAY_DATA.md` | the page and its documents | 7 |

Between Task 2 and Task 7 the old `app.js` calls a `Tunnel.draw` that has changed, so the built page does not draw until Task 7; every test is green at every commit.

---

### Task 1: The two brand fonts, embedded

**Files:**
- Modify: `bakeoff/view.py`
- Create: `viewer/fonts/HankenGrotesk-latin.woff2`
- Create: `viewer/fonts/JetBrainsMono-latin.woff2`
- Create: `viewer/fonts/LICENSE.md`
- Modify: `viewer/viewer.css`
- Test: `tests/test_view.py`

**Interfaces:**
- Consumes: `render_html`, `VIEWER_DIR`.
- Produces: `viewer/fonts/HankenGrotesk-latin.woff2`, `viewer/fonts/JetBrainsMono-latin.woff2`; every `url(fonts/<name>.woff2)` in a viewer stylesheet becomes a base64 data URI; any other `url()` raises `ValueError`.

The two font files are binary. Copy them exactly (Step 3):

```bash
mkdir -p viewer/fonts
cp ~/Documents/PROJECTS/BRAND/website/ds-bundle/fonts/HankenGrotesk-latin.woff2 ~/Documents/PROJECTS/BRAND/website/ds-bundle/fonts/JetBrainsMono-latin.woff2 viewer/fonts/
```

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_view.py`:

```diff
@@ -20,8 +20,10 @@ def test_render_inlines_every_file_and_the_data():
     replay = {"replay_version": 1, "episodes": [], "note": "</script>"}
     page = render_html(replay)
     assert "<link" not in page and "<script src" not in page  # one file: nothing left to fetch
-    for name in ("timeline.js", "tunnel.js", "minds.js", "app.js", "viewer.css"):
+    for name in ("timeline.js", "tunnel.js", "minds.js", "app.js"):
         assert (VIEWER_DIR / name).read_text() in page
+    rules = (VIEWER_DIR / "viewer.css").read_text().split("}\n\n", 1)[1]  # everything after the two font faces
+    assert rules in page
     (data,) = DATA.findall(page)
     assert json.loads(data) == replay
     assert DATA_SLOT not in page
@@ -30,7 +32,29 @@ def test_render_inlines_every_file_and_the_data():
 def test_the_page_makes_no_network_request():
     page = render_html({"episodes": []})
     assert not re.search(r"""(src|href)=["']?(https?:)?//""", page)
-    assert "@import" not in page and "url(" not in page
+    assert "@import" not in page
+    assert all(url.startswith("data:") for url in re.findall(r"url\(([^)]*)\)", page))  # only embedded data
+
+
+def test_the_two_brand_fonts_are_embedded_not_fetched():
+    page = render_html({"episodes": []})
+    fonts = re.findall(r"@font-face\s*{[^}]*}", page)
+    assert len(fonts) == 2
+    assert {re.search(r'font-family:\s*"([^"]+)"', f).group(1) for f in fonts} == {"Hanken Grotesk", "JetBrains Mono"}
+    for face in fonts:
+        (source,) = re.findall(r"url\(([^)]*)\)", face)
+        assert source.startswith("data:font/woff2;base64,") and len(source) > 40_000
+    assert "url(fonts/" not in page and ".woff2" not in page
+
+
+def test_a_stylesheet_url_that_is_not_a_bundled_font_is_an_error(tmp_path):
+    (tmp_path / "index.html").write_text('<link rel="stylesheet" href="a.css">' + DATA_SLOT)
+    (tmp_path / "a.css").write_text("body { background: url(https://example.com/x.png); }")
+    with pytest.raises(ValueError, match="a.css may only load fonts/<name>.woff2"):
+        render_html({}, tmp_path)
+    (tmp_path / "a.css").write_text('@font-face { font-family: "X"; src: url(fonts/missing.woff2) format("woff2"); }')
+    with pytest.raises(FileNotFoundError):
+        render_html({}, tmp_path)
 
 
 def test_a_backslash_in_a_viewer_file_survives(tmp_path):
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_view.py`
Expected:

```text
FAILED tests/test_view.py::test_the_two_brand_fonts_are_embedded_not_fetched
FAILED tests/test_view.py::test_a_stylesheet_url_that_is_not_a_bundled_font_is_an_error
2 failed, 7 passed
```

- [ ] **Step 3: Write the implementation**

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
_STYLESHEET = re.compile(r'<link rel="stylesheet" href="([^"]+)">')
_SCRIPT = re.compile(r'<script src="([^"]+)"></script>')
_CSS_URL = re.compile(r"url\(([^)]*)\)")
_FONT = re.compile(r"fonts/[A-Za-z0-9_-]+\.woff2")


def embed_json(value) -> str:
    """JSON that is safe inside a <script> element. A logged answer may contain `</script>` or
    `<!--`; with every `<` written as \\u003c nothing in the data can end the element."""
    return json.dumps(value, separators=(",", ":")).replace("<", "\\u003c")


def _stylesheet(path: Path) -> str:
    """A stylesheet with its fonts embedded as base64, so the page stays one file that fetches nothing.
    The only url() a viewer stylesheet may contain is a bundled font, `fonts/<name>.woff2`."""
    def embed(match: re.Match) -> str:
        target = match.group(1).strip("'\"")
        if not _FONT.fullmatch(target):
            raise ValueError(f"{path.name} may only load fonts/<name>.woff2, not {target!r}")
        return "url(data:font/woff2;base64," + base64.b64encode((path.parent / target).read_bytes()).decode("ascii") + ")"

    return _CSS_URL.sub(embed, path.read_text(encoding="utf-8"))


def render_html(replay: dict, viewer_dir: Path | str = VIEWER_DIR) -> str:
    viewer_dir = Path(viewer_dir)
    page = (viewer_dir / "index.html").read_text(encoding="utf-8")
    if page.count(DATA_SLOT) != 1:
        raise ValueError(f"{viewer_dir / 'index.html'} must contain the replay data slot exactly once")
    # lambdas, so that a backslash in a file is never read as a regex group reference
    page = _STYLESHEET.sub(lambda m: "<style>\n" + _stylesheet(viewer_dir / m.group(1)) + "</style>", page)
    page = _SCRIPT.sub(lambda m: "<script>\n" + (viewer_dir / m.group(1)).read_text(encoding="utf-8") + "</script>", page)
    return page.replace(DATA_SLOT, '<script type="application/json" id="replay-data">' + embed_json(replay) + "</script>")
```

Copy `viewer/fonts/HankenGrotesk-latin.woff2` as the task's notes say (binary).

Copy `viewer/fonts/JetBrainsMono-latin.woff2` as the task's notes say (binary).

Create `viewer/fonts/LICENSE.md`:

```markdown
# Fonts

Both files are the latin subsets served by Google Fonts, copied from the brand's design-system bundle
(`~/Documents/PROJECTS/BRAND/website/ds-bundle/fonts/`). Both are licensed under the SIL Open Font
License, Version 1.1 (https://openfontlicense.org), which allows bundling and embedding.

| file | family | copyright |
| --- | --- | --- |
| `HankenGrotesk-latin.woff2` | Hanken Grotesk (variable weight) | Copyright 2021 The Hanken Grotesk Project Authors (https://github.com/marcologous/hanken-grotesk) |
| `JetBrainsMono-latin.woff2` | JetBrains Mono (variable weight) | Copyright 2020 The JetBrains Mono Project Authors (https://github.com/JetBrains/JetBrainsMono) |

`bakeoff/view.py` embeds them in the page as base64, so the replay stays one file that loads nothing.
```

Apply to `viewer/viewer.css`:

```diff
@@ -1,3 +1,7 @@
+/* The two brand fonts (OFL, viewer/fonts/LICENSE.md). bakeoff/view.py embeds them as base64. */
+@font-face { font-family: "Hanken Grotesk"; font-style: normal; font-weight: 100 900; font-display: swap; src: url(fonts/HankenGrotesk-latin.woff2) format("woff2"); }
+@font-face { font-family: "JetBrains Mono"; font-style: normal; font-weight: 100 800; font-display: swap; src: url(fonts/JetBrainsMono-latin.woff2) format("woff2"); }
+
 :root {
   --paper: #edf0ec;
   --grid: #dde3dd;
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_view.py`
Expected: `9 passed`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `264 passed, 9 deselected`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/view.py tests/test_view.py viewer/fonts/HankenGrotesk-latin.woff2 viewer/fonts/JetBrainsMono-latin.woff2 viewer/fonts/LICENSE.md viewer/viewer.css
git commit -F <message file>   # feat: the two brand fonts are embedded in the page as base64, and a stylesheet may load nothing else
```

---

### Task 2: The tunnel under a fixed camera

**Files:**
- Modify: `viewer/tunnel.js`
- Test: `viewer/tests/tunnel.test.js`

**Interfaces:**
- Consumes: a state from `Timeline.stateAt` (`row`, `lane`, `air`, `status`, `since`).
- Produces: `Tunnel.quads(track, row, size, maxRows)` (kinds `floor` and `finish`), `Tunnel.seenOutline(frame, lookahead, window) -> [{row, lane}]` (lanes unwrapped), `Tunnel.place(state, lanes, size, camRow?) -> {x, y, scale, rotation, lift, fall, visible}`, `Tunnel.corners`, `Tunnel.angleOf`, `Tunnel.draw(ctx, size, track, row, maxRows, outline)`. `wasSeen` is gone.

- [ ] **Step 1: Write the failing tests**

Replace the whole of `viewer/tests/tunnel.test.js` with:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const { DEPTH, isGap, offset, quads, seenOutline, place } = require("../tunnel.js");

const track = { lanes: 12, max_rows: 300, gaps: [[], [], [5, 6], [0, 11]] };
const SIZE = 400;
const centreX = (quad) => quad.points.reduce((sum, p) => sum + p[0], 0) / 4;
const centreY = (quad) => quad.points.reduce((sum, p) => sum + p[1], 0) / 4;

test("gaps wrap round the ring and rows past the list are floor", () => {
  assert.equal(isGap(track, 2, 5), true);
  assert.equal(isGap(track, 3, -1), true); // lane -1 is lane 11
  assert.equal(isGap(track, 3, 12), true); // lane 12 is lane 0
  assert.equal(isGap(track, 2, 4), false);
  assert.equal(isGap(track, 99, 5), false);
});

test("offsets are wrapped the way the senses wrap them", () => {
  assert.deepEqual([6, 7, 5, 0, 11].map((lane) => offset(lane, 6, 12)), [0, 1, -1, -6, 5]);
  assert.equal(offset(11, 0, 12), -1);
});

test("a gap is a missing tile and every other tile of the drawn rows is there", () => {
  const all = quads(track, 0, SIZE, 300);
  assert.equal(all.length, (DEPTH + 1) * 12 - 4);
  assert.equal(all.some((q) => q.row === 2 && (q.lane === 5 || q.lane === 6)), false);
  assert.equal(all[0].row, DEPTH); // far to near, so near tiles paint over far ones
  assert.equal(all[all.length - 1].row, 0);
});

test("the camera is fixed: the start lane is at the bottom whatever the runners do, lane 0 is the ceiling", () => {
  const all = quads(track, 0, SIZE, 300);
  const tile = (row, lane) => all.find((q) => q.row === row && q.lane === lane);
  assert.ok(Math.abs(centreX(tile(0, 6)) - SIZE / 2) < 1e-6);
  assert.ok(centreY(tile(0, 6)) > SIZE / 2);
  assert.ok(centreX(tile(0, 7)) > centreX(tile(0, 6)));
  assert.ok(centreX(tile(0, 5)) < centreX(tile(0, 6)));
  assert.ok(centreY(tile(0, 0)) < SIZE / 2); // the opposite lane is the ceiling
  assert.ok(centreY(tile(5, 6)) < centreY(tile(0, 6))); // further away is nearer the middle
  assert.equal(quads.length, 4); // (track, row, size, maxRows): no camera lane, no `seen`
});

test("the camera moves along the tube with the clock", () => {
  const all = quads(track, 2.5, SIZE, 300);
  assert.equal(all[all.length - 1].row, 2);
  assert.equal(all[0].row, 2 + DEPTH);
  assert.equal(all.some((q) => q.row < 2), false);
});

test("tiles are floor, or finish from the last row on", () => {
  const all = quads(track, 0, SIZE, 4);
  const kind = (row, lane) => all.find((q) => q.row === row && q.lane === lane).kind;
  assert.equal(kind(1, 6), "floor");
  assert.equal(kind(3, 6), "floor");
  assert.equal(kind(4, 6), "finish");
  assert.equal(kind(9, 0), "finish");
});

test("a gap the engine can never kill on past the finish line is drawn as finish floor, not a hole", () => {
  // maxRows 2: row 2 is at the finish (the engine can still kill there); row 3 is past it (never kills)
  const pastFinish = { lanes: 12, max_rows: 300, gaps: [[], [], [5], [3]] };
  const all = quads(pastFinish, 0, SIZE, 2);
  const tile = (row, lane) => all.find((q) => q.row === row && q.lane === lane);
  assert.equal(tile(3, 3).kind, "finish"); // gaps[3] lists lane 3, but row 3 > max_rows 2: drawn anyway
  assert.equal(tile(2, 5), undefined); // row 2 <= max_rows 2: the engine could still kill there, so it's a real hole
});

test("the focused mind's tiles: six rows ahead of where it stood, three lanes either side", () => {
  const tiles = seenOutline({ row: 10, lane: 1 }, 6, 3);
  assert.equal(tiles.length, 6 * 7);
  const has = (row, lane) => tiles.some((t) => t.row === row && t.lane === lane);
  assert.equal(has(11, 1), true);
  assert.equal(has(16, 4), true);
  assert.equal(has(11, -2), true); // lane -2 is lane 10: left unwrapped, isGap and corners wrap it
  assert.equal(has(10, 1), false); // its own row is not ahead
  assert.equal(has(17, 1), false);
  assert.equal(has(11, 5), false);
});

test("a runner stands on the wall at its lane with its head toward the axis", () => {
  const running = { row: 4, lane: 6, air: 0, status: "running", since: 0 };
  const bottom = place(running, 12, SIZE);
  assert.ok(Math.abs(bottom.x - SIZE / 2) < 1e-6 && bottom.y > SIZE / 2);
  assert.ok(Math.abs(bottom.rotation) < 1e-9); // upright at the bottom
  assert.equal(bottom.lift, 0);
  assert.equal(bottom.fall, 0);
  assert.equal(bottom.visible, true);
  const ceiling = place({ ...running, lane: 0 }, 12, SIZE);
  assert.ok(Math.abs(ceiling.x - SIZE / 2) < 1e-6 && ceiling.y < SIZE / 2);
  assert.ok(Math.abs(Math.abs(ceiling.rotation) - Math.PI) < 1e-9); // a ceiling runner is upside down
  const right = place({ ...running, lane: 9 }, 12, SIZE);
  assert.ok(right.x > SIZE / 2 && Math.abs(right.y - SIZE / 2) < 1e-6);
  // an upright sprite's head is at (0, -1); a canvas rotation by r turns that into (sin r, -cos r),
  // which must point from the runner to the axis on every wall
  for (let lane = 0; lane < 12; lane++) {
    const at = place({ ...running, lane }, 12, SIZE);
    const head = [Math.sin(at.rotation), -Math.cos(at.rotation)];
    const toAxis = [SIZE / 2 - at.x, SIZE / 2 - at.y];
    const length = Math.hypot(...toAxis);
    assert.ok(Math.abs(head[0] - toAxis[0] / length) < 1e-9 && Math.abs(head[1] - toAxis[1] / length) < 1e-9, "lane " + lane);
  }
  // lane -1 is lane 11: the unwrapped lane of a step round the ring lands in the same place
  assert.ok(Math.abs(place({ ...running, lane: -1 }, 12, SIZE).x - place({ ...running, lane: 11 }, 12, SIZE).x) < 1e-6);
});

test("a jump lifts the runner, a death drops it, and a runner the camera has passed is not drawn", () => {
  const jumping = place({ row: 4.5, lane: 6, air: 1, status: "running", since: 0 }, 12, SIZE);
  assert.ok(jumping.lift > 0);
  assert.equal(place({ row: 9, lane: 6, air: 0, status: "dead", since: 0.25 }, 12, SIZE).fall, 0.25);
  assert.equal(place({ row: 9, lane: 6, air: 0, status: "dead", since: 3 }, 12, SIZE).fall, 1);
  const cut = { row: 9, lane: 6, air: 0, status: "cut", since: 2 };
  assert.equal(place(cut, 12, SIZE, 9).visible, true);
  assert.equal(place(cut, 12, SIZE, 11).visible, false);
  const ahead = place({ ...cut, row: 12 }, 12, SIZE, 9); // further along the tube: smaller and nearer the axis
  assert.ok(ahead.scale < place(cut, 12, SIZE, 9).scale);
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `node --test viewer/tests/tunnel.test.js`
Expected:

```text
✖ a gap is a missing tile and every other tile of the drawn rows is there
✖ the camera is fixed: the start lane is at the bottom whatever the runners do, lane 0 is the ceiling
✖ the camera moves along the tube with the clock
✖ tiles are floor, or finish from the last row on
✖ a gap the engine can never kill on past the finish line is drawn as finish floor, not a hole
✖ the focused mind's tiles: six rows ahead of where it stood, three lanes either side
✖ a runner stands on the wall at its lane with its head toward the axis
✖ a jump lifts the runner, a death drops it, and a runner the camera has passed is not drawn
ℹ pass 2
ℹ fail 8
```

- [ ] **Step 3: Write the implementation**

Replace the whole of `viewer/tunnel.js` with:

```javascript
// The tunnel: one tube of poured concrete seen from a fixed camera. `quads`, `seenOutline` and `place`
// are pure geometry (tested under node); `draw` paints the tube on a canvas.
//
// The track is a ring of lanes, so it is drawn as a tube. The camera never turns: the start lane
// (lanes / 2) is at the bottom, the lane to its right is to the right, lane 0 is the ceiling. The
// camera moves along the tube with the clock, so every runner still running is on the nearest row.
// A gap is a missing tile.
(function (root) {
  "use strict";

  const DEPTH = 26; // rows drawn ahead of the camera
  const PERSPECTIVE = 0.3; // a tile d rows away is drawn at scale 1 / (1 + PERSPECTIVE * d)
  const RADIUS = 0.47; // tube radius at the camera, as a share of the canvas size
  const STANDS = 0.35; // how far into its tile a runner stands, in rows

  const wrap = (lane, lanes) => ((lane % lanes) + lanes) % lanes;

  function isGap(track, row, lane) {
    return row >= 0 && row < track.gaps.length && track.gaps[row].includes(wrap(lane, track.lanes));
  }

  // lane offset from `from`, -lanes/2 .. lanes/2 - 1, the way the senses wrap it
  function offset(lane, from, lanes) {
    return wrap(lane - from + lanes / 2, lanes) - lanes / 2;
  }

  // canvas y points down, so the bottom of the tube is angle pi/2 and "right" is a smaller angle.
  // `lane` may be a fraction and may be unwrapped (a step from lane 0 to lane 11 reads 0 -> -1).
  function angleOf(lane, lanes) {
    return Math.PI / 2 - (lane - Math.floor(lanes / 2)) * ((2 * Math.PI) / lanes);
  }

  function point(angle, depth, size) {
    const radius = (RADIUS * size) / (1 + PERSPECTIVE * depth);
    return [size / 2 + radius * Math.cos(angle), size / 2 + radius * Math.sin(angle)];
  }

  // the four corners of tile (row, lane) for a camera at `camRow` (a fraction while the clock runs)
  function corners(lanes, row, lane, camRow, size) {
    const half = Math.PI / lanes, angle = angleOf(lane, lanes);
    const near = Math.max(row - camRow, -1), far = row + 1 - camRow;
    return [point(angle + half, near, size), point(angle - half, near, size), point(angle - half, far, size), point(angle + half, far, size)];
  }

  // Floor tiles from far to near, each {row, lane, kind, depth, points}. kind: "floor", or "finish" (at or
  // past the last row). `row` is the camera's row and may be a fraction.
  function quads(track, row, size, maxRows) {
    const out = [];
    const first = Math.floor(row);
    for (let r = first + DEPTH; r >= first; r--) {
      // mirrors Game.step (bakeoff/game/engine.py): only row <= maxRows can ever be a fatal gap, so a
      // row past the finish line is never a hole, whatever `gaps` lists there
      const neverKills = r > maxRows;
      for (let lane = 0; lane < track.lanes; lane++) {
        if (!neverKills && isGap(track, r, lane)) continue;
        out.push({ row: r, lane, kind: r >= maxRows ? "finish" : "floor", depth: Math.max(r - row, -1),
                   points: corners(track.lanes, r, lane, row, size) });
      }
    }
    return out;
  }

  // The tiles a mind was shown for the decision in `frame`: `lookahead` rows ahead of where it stood,
  // `window` lanes either side. Lanes are wrapped by the caller's isGap / corners, not here.
  function seenOutline(frame, lookahead, window) {
    const tiles = [];
    for (let ahead = 1; ahead <= lookahead; ahead++) {
      for (let off = -window; off <= window; off++) tiles.push({ row: frame.row + ahead, lane: frame.lane + off });
    }
    return tiles;
  }

  // Where a runner is drawn. `state` comes from Timeline.stateAt; `camRow` is the clock (default: the
  // runner's own row). The runner stands on the tube wall with its head toward the axis: `rotation`
  // turns an upright sprite to stand there (0 at the bottom, pi on the ceiling). `lift` is how far a
  // jump raises it toward the axis, `fall` (0..1) how far a dead runner has dropped through the floor.
  function place(state, lanes, size, camRow) {
    const depth = state.row - (camRow == null ? state.row : camRow);
    const scale = 1 / (1 + PERSPECTIVE * Math.max(0, depth + STANDS));
    const angle = angleOf(state.lane, lanes);
    const [x, y] = point(angle, Math.max(0, depth + STANDS), size);
    return {
      x, y, scale, rotation: angle - Math.PI / 2,
      lift: state.air * 0.13 * size * scale,
      fall: state.status === "dead" ? Math.min(1, state.since) : 0,
      visible: depth > -0.5 && depth <= DEPTH,
    };
  }

  const ACCENT = "rgba(122,162,247,0.6)"; // brand --accent: only ever the focused mind's tiles

  function path(ctx, points) {
    ctx.beginPath();
    points.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.closePath();
  }

  // outline: the tiles from seenOutline for the mind in focus, or null
  function draw(ctx, size, track, row, maxRows, outline) {
    ctx.fillStyle = "#0A0A0A";
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = "#050505"; // the far end of the tube
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, ((RADIUS * size) / (1 + PERSPECTIVE * (DEPTH + 1))) * 0.92, 0, 2 * Math.PI);
    ctx.fill();
    for (const quad of quads(track, row, size, maxRows)) {
      const fog = Math.min(1, Math.max(0, quad.depth) / DEPTH);
      // poured concrete: slightly uneven greys that fade into the void; the finish is a lighter band
      const shade = Math.round((quad.kind === "finish" ? 78 : 34) * (1 - fog * 0.72) + ((quad.lane * 7 + quad.row * 3) % 5));
      ctx.fillStyle = "rgb(" + shade + "," + (shade + 2) + "," + (shade + 4) + ")";
      ctx.strokeStyle = fog > 0.75 ? "#1E2227" : "#2A2F35";
      ctx.lineWidth = 1;
      path(ctx, quad.points);
      ctx.fill();
      ctx.stroke();
    }
    if (!outline) return;
    ctx.strokeStyle = ACCENT;
    ctx.lineWidth = 1.5;
    for (const tile of outline) {
      if (tile.row - row > DEPTH || tile.row + 1 - row <= 0) continue;
      if (tile.row <= maxRows && isGap(track, tile.row, tile.lane)) continue;
      path(ctx, corners(track.lanes, tile.row, tile.lane, row, size));
      ctx.stroke();
    }
  }

  const api = { DEPTH, isGap, offset, angleOf, corners, quads, seenOutline, place, draw };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Tunnel = api;
})(typeof window !== "undefined" ? window : globalThis);
```

- [ ] **Step 4: Run the task's tests**

Run: `node --test viewer/tests/tunnel.test.js`
Expected: `pass 10, fail 0`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `264 passed, 9 deselected`

- [ ] **Step 6: Commit**

```bash
git add viewer/tests/tunnel.test.js viewer/tunnel.js
git commit -F <message file>   # feat: the tunnel has a fixed camera, the focused mind's tiles as an outline, and a place for every runner
```

---

### Task 3: The sprites

**Files:**
- Create: `viewer/sprites.js`
- Test: `viewer/tests/sprites.test.js`

**Interfaces:**
- Produces: `Sprites.GRIDS`, `Sprites.INKS`, `Sprites.visorCells(p) -> bool[5]`, `Sprites.pixels(name, {p, open}) -> [{x, y, ink}]`, `Sprites.sizeOf(name)`, `Sprites.drawSprite(ctx, name, px, {p, open})` (feet on the origin, head toward -y).

- [ ] **Step 1: Write the failing tests**

Create `viewer/tests/sprites.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const { GRIDS, INKS, visorCells, pixels, sizeOf } = require("../sprites.js");

test("the approved grids, character for character", () => {
  assert.deepEqual(GRIDS.fly, ["..ee.ee..", "...bbb...", ".w.bbb.w.", "ww.bbb.ww", "wwwbbbwww", "ww.bbb.ww", ".w.bbb.w.", "...b.b...", "..b...b.."]);
  assert.deepEqual(GRIDS.llm, [".ooooooo.", ".ooooooo.", ".okoookoo", "ooooooooo", ".ooooooo.", ".ooooooo.", ".o.o.o.o.", ".o.o.o.o."]);
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

test("an unknown runner is a plain grey block", () => {
  assert.deepEqual(pixels("solver"), pixels("block"));
  assert.ok(pixels("always_jump").every((c) => c.ink === INKS.g));
  assert.deepEqual(sizeOf("random"), { width: 5, height: 7 });
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `node --test viewer/tests/sprites.test.js`
Expected:

```text
✖ viewer/tests/sprites.test.js
ℹ pass 0
ℹ fail 1
```

- [ ] **Step 3: Write the implementation**

Create `viewer/sprites.js`:

```javascript
// The runners as pixel sprites: grids of characters, one character = one pixel, `.` is empty.
// All of them are our own drawings. The LLM's orange critter is our rendition, not anyone's artwork.
// `pixels` and `visorCells` are pure (tested under node); `drawSprite` paints on a canvas.
(function (root) {
  "use strict";

  const GRIDS = {
    // a fruit fly seen from behind: pale folded wings, dark body, red eyes
    fly: ["..ee.ee..", "...bbb...", ".w.bbb.w.", "ww.bbb.ww", "wwwbbbwww", "ww.bbb.ww", ".w.bbb.w.", "...b.b...", "..b...b.."],
    // the same fly in a jump: wings open
    fly_open: ["..ee.ee..", "w..bbb..w", "ww.bbb.ww", "wwwbbbwww", "ww.bbb.ww", "w..bbb..w", "...bbb...", "...b.b...", "..b...b.."],
    llm: [".ooooooo.", ".ooooooo.", ".okoookoo", "ooooooooo", ".ooooooo.", ".ooooooo.", ".o.o.o.o.", ".o.o.o.o."],
    // "the visor": a pale monolith with one slit of five cells, V lit and v unlit (see visorCells)
    visor: [".jjjjj.", "jjjjjjj", "jVVVvvj", "jjjjjjj", ".jjjjj.", "..jjj..", ".jjjjj.", ".jjjjj.", ".j...j.", ".j...j."],
    // baselines and the one-shot Jev: a plain grey block
    block: ["ggggg", "ggggg", "ggggg", "ggggg", "ggggg", "ggggg", "ggggg"],
  };
  const INKS = { w: "#AEB4BA", b: "#3A4046", e: "#F7768E", o: "#D97757", k: "#1A0E0A", j: "#B9BEC4", V: "#FFFFFF", v: "#15181C", g: "#7C848D" };
  const SLIT = 5;

  // Which of the visor's five cells are lit, left to right: round(5 * p) of them, where p is the
  // probability Jev gave that the move it made does not land on a gap. Unknown p: none.
  function visorCells(p) {
    const lit = typeof p === "number" && isFinite(p) ? Math.round(SLIT * Math.max(0, Math.min(1, p))) : 0;
    return Array.from({ length: SLIT }, (_, i) => i < lit);
  }

  // The sprite as a list of {x, y, ink}, (0, 0) being the top left pixel. options: {p} for the visor's
  // slit, {open: true} for the fly's open wings.
  function pixels(name, options) {
    const opts = options || {};
    const grid = GRIDS[name === "fly" && opts.open ? "fly_open" : name] || GRIDS.block;
    const cells = name === "visor" ? visorCells(opts.p) : [];
    let slit = 0;
    const out = [];
    grid.forEach((line, y) => {
      for (let x = 0; x < line.length; x++) {
        let ink = line[x];
        if (ink === ".") continue;
        if (ink === "V" || ink === "v") ink = cells[slit++] ? "V" : "v";
        out.push({ x, y, ink: INKS[ink] });
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
    const key = [name, px, !!opts.open, name === "visor" ? visorCells(opts.p).filter(Boolean).length : 0].join(" ");
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

  const api = { GRIDS, INKS, visorCells, pixels, sizeOf, drawSprite };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Sprites = api;
})(typeof window !== "undefined" ? window : globalThis);
```

- [ ] **Step 4: Run the task's tests**

Run: `node --test viewer/tests/sprites.test.js`
Expected: `pass 6, fail 0`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `264 passed, 9 deselected`

- [ ] **Step 6: Commit**

```bash
git add viewer/sprites.js viewer/tests/sprites.test.js
git commit -F <message file>   # feat: pixel sprites: the fly, the visor with its slit, the orange critter and a grey block
```

---

### Task 4: Staging rules: overlap and auto-focus

**Files:**
- Create: `viewer/stage.js`
- Test: `viewer/tests/stage.test.js`

**Interfaces:**
- Consumes: frames' `solver_depths`.
- Produces: `Stage.overlaps(runners, lanes) -> {id: {alpha, fan, stack}}`, `Stage.safeActions(frame)`, `Stage.autoFocus(current, states, heldSince, t) -> {focus, heldSince}`, `Stage.OVERLAP_ALPHA` (0.55), `Stage.HOLD_ROWS` (3).

- [ ] **Step 1: Write the failing tests**

Create `viewer/tests/stage.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const { OVERLAP_ALPHA, HOLD_ROWS, overlaps, safeActions, autoFocus } = require("../stage.js");

const at = (id, row, lane) => ({ id, row, lane });
const SAFE = { left: 6, stay: 6, right: 6, jump: 6 };
const running = (id, depths) => ({ id, status: "running", frame: { solver_depths: { ...SAFE, ...depths } } });

test("three runners on the start tile are translucent, fanned out and their tags stack", () => {
  const out = overlaps([at("fly", 0, 6), at("jev_composed", 0, 6), at("llm", 0, 6)], 12);
  assert.deepEqual(out.fly, { alpha: OVERLAP_ALPHA, fan: -1, stack: 0 });
  assert.deepEqual(out.jev_composed, { alpha: OVERLAP_ALPHA, fan: 0, stack: 1 });
  assert.deepEqual(out.llm, { alpha: OVERLAP_ALPHA, fan: 1, stack: 2 });
  assert.equal(OVERLAP_ALPHA, 0.55);
});

test("a runner alone on its tile is opaque and where it stands", () => {
  const out = overlaps([at("fly", 4, 5), at("jev_composed", 4, 6), at("llm", 4, 6.4)], 12);
  assert.deepEqual(out.fly, { alpha: 1, fan: 0, stack: 0 });
  assert.deepEqual(out.jev_composed, { alpha: OVERLAP_ALPHA, fan: -0.5, stack: 0 }); // within half a lane of the llm
  assert.deepEqual(out.llm, { alpha: OVERLAP_ALPHA, fan: 0.5, stack: 1 });
});

test("overlap needs the same row, and lanes are compared round the ring", () => {
  const apart = overlaps([at("a", 4, 6), at("b", 5, 6)], 12);
  assert.equal(apart.a.alpha, 1);
  assert.equal(apart.b.alpha, 1);
  const ring = overlaps([at("a", 4, 0.2), at("b", 4, 11.9), at("c", 4, -0.1)], 12); // 11.9 and -0.1 are the same place
  assert.deepEqual([ring.a.alpha, ring.b.alpha, ring.c.alpha], [OVERLAP_ALPHA, OVERLAP_ALPHA, OVERLAP_ALPHA]);
  assert.deepEqual(overlaps([], 12), {});
});

test("safe actions are the ones the solver does not see landing on a gap", () => {
  assert.equal(safeActions({ solver_depths: SAFE }), 4);
  assert.equal(safeActions({ solver_depths: { left: 0, stay: 0, right: 3, jump: 6 } }), 2);
  assert.equal(safeActions({ solver_depths: { left: 0, stay: 0, right: 0, jump: 0 } }), 0);
  assert.equal(safeActions({}), 0);
});

test("auto-focus cuts to the runner in danger, the one with the fewest safe actions", () => {
  const states = [running("fly", { stay: 0 }), running("jev_composed", { stay: 0, left: 0 }), running("llm", {})];
  assert.deepEqual(autoFocus("llm", states, 0, 10), { focus: "jev_composed", heldSince: 10 });
  const tie = [running("fly", { stay: 0 }), running("jev_composed", { jump: 0 }), running("llm", {})];
  assert.deepEqual(autoFocus("jev_composed", tie, 0, 10), { focus: "jev_composed", heldSince: 0 }); // a tie stays
  assert.deepEqual(autoFocus("llm", tie, 0, 10), { focus: "fly", heldSince: 10 }); // else panel order
});

test("auto-focus holds for three rows so it does not flicker", () => {
  const states = [running("fly", { stay: 0 }), running("llm", {})];
  assert.equal(HOLD_ROWS, 3);
  assert.deepEqual(autoFocus("llm", states, 10, 12.9), { focus: "llm", heldSince: 10 });
  assert.deepEqual(autoFocus("llm", states, 10, 13), { focus: "fly", heldSince: 13 });
  assert.deepEqual(autoFocus("llm", states, 10, 4), { focus: "fly", heldSince: 4 }); // scrubbed back: the hold is void
});

test("auto-focus ignores the fallen and stays put when nobody is in danger", () => {
  const dead = { id: "fly", status: "dead", frame: { solver_depths: { left: 0, stay: 0, right: 0, jump: 0 } } };
  assert.deepEqual(autoFocus("llm", [dead, running("llm", {})], 0, 50), { focus: "llm", heldSince: 0 });
  assert.deepEqual(autoFocus(null, [dead, running("llm", {})], 0, 50), { focus: "fly", heldSince: 50 }); // nothing chosen yet
  assert.deepEqual(autoFocus(null, [], 0, 0), { focus: null, heldSince: 0 });
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `node --test viewer/tests/stage.test.js`
Expected:

```text
✖ viewer/tests/stage.test.js
ℹ pass 0
ℹ fail 1
```

- [ ] **Step 3: Write the implementation**

Create `viewer/stage.js`:

```javascript
// Staging rules for three runners in one tunnel. Pure: no DOM (tested under node).
//
// `overlaps`: who is drawn translucent and fanned out, because they stand on top of one another.
// `autoFocus`: where the blue cursor goes when nobody is steering it.
(function (root) {
  "use strict";

  const ACTIONS = ["left", "stay", "right", "jump"];
  const NEAR_LANES = 0.5; // runners within half a lane of each other on the same row overlap
  const OVERLAP_ALPHA = 0.55;
  const HOLD_ROWS = 3; // auto-focus stays where it is for at least this many rows, so it does not flicker

  // distance between two lanes round the ring (lanes may be fractions and unwrapped)
  function laneDistance(a, b, lanes) {
    const d = (((a - b) % lanes) + lanes) % lanes;
    return Math.min(d, lanes - d);
  }

  // runners: [{id, row, lane}] of the runners being drawn, in panel order. Returns {id: {alpha, fan,
  // stack}}: fan is the sideways shift in units of one fan step (-1, 0, 1 for three runners on one tile),
  // stack the line its tag goes on (0 nearest the runner), so tags never overprint.
  function overlaps(runners, lanes) {
    const out = {};
    const groups = [];
    for (const runner of runners) {
      const group = groups.find((g) => g.some((other) =>
        Math.abs(other.row - runner.row) < 0.5 && laneDistance(other.lane, runner.lane, lanes) <= NEAR_LANES));
      if (group) group.push(runner); else groups.push([runner]);
    }
    for (const group of groups) {
      group.forEach((runner, i) => {
        out[runner.id] = group.length === 1 ? { alpha: 1, fan: 0, stack: 0 }
          : { alpha: OVERLAP_ALPHA, fan: i - (group.length - 1) / 2, stack: i };
      });
    }
    return out;
  }

  // how many of the four actions do not land on a gap, by the reference solver's reading of the same
  // senses (solver_depths is 0 for an action whose landing tile is a gap): the rule stays in Python
  function safeActions(frame) {
    const depths = frame.solver_depths || {};
    return ACTIONS.filter((action) => depths[action] > 0).length;
  }

  // Where auto-focus goes at time t. states: [{id, status, frame}] in panel order (from
  // Timeline.stateAt). It cuts to a runner that is still running and whose current decision has at
  // least one action that lands on a gap; among several, the one with the fewest safe actions, ties to
  // the current focus, then to panel order. It holds for HOLD_ROWS rows. Returns {focus, heldSince}.
  function autoFocus(current, states, heldSince, t) {
    const keep = { focus: current, heldSince };
    if (current != null && t >= heldSince && t - heldSince < HOLD_ROWS) return keep;
    const inDanger = states.filter((s) => s.status === "running" && safeActions(s.frame) < ACTIONS.length);
    if (!inDanger.length) return current == null && states.length ? { focus: states[0].id, heldSince: t } : keep;
    const fewest = Math.min(...inDanger.map((s) => safeActions(s.frame)));
    const tied = inDanger.filter((s) => safeActions(s.frame) === fewest);
    const pick = tied.find((s) => s.id === current) || tied[0];
    return pick.id === current ? keep : { focus: pick.id, heldSince: t };
  }

  const api = { OVERLAP_ALPHA, HOLD_ROWS, laneDistance, overlaps, safeActions, autoFocus };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Stage = api;
})(typeof window !== "undefined" ? window : globalThis);
```

- [ ] **Step 4: Run the task's tests**

Run: `node --test viewer/tests/stage.test.js`
Expected: `pass 7, fail 0`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `264 passed, 9 deselected`

- [ ] **Step 6: Commit**

```bash
git add viewer/stage.js viewer/tests/stage.test.js
git commit -F <message file>   # feat: staging rules: overlapping runners are translucent and fanned, auto-focus cuts to the runner in danger
```

---

### Task 5: The feed

**Files:**
- Create: `viewer/feed.js`
- Test: `viewer/tests/feed.test.js`

**Interfaces:**
- Consumes: the replay object (`docs/REPLAY_DATA.md`); an `EventSource`-like class.
- Produces: `Feed.fromEmbedded(replay, handlers)`, `Feed.fromStream(url, handlers, EventSourceClass?)`; handlers `onMeta`, `onEpisode(episode, track)`, `onFrame(player, seed, frame, summary)`, `onEnd`, `onError`.

- [ ] **Step 1: Write the failing tests**

Create `viewer/tests/feed.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const { fromEmbedded, fromStream } = require("../feed.js");

function recorder() {
  const calls = [];
  const handler = (name) => (...args) => calls.push([name, ...args]);
  return { calls, handlers: { onMeta: handler("meta"), onEpisode: handler("episode"), onFrame: handler("frame"),
                              onEnd: handler("end"), onError: handler("error") } };
}

class FakeEventSource {
  constructor(url) { this.url = url; this.listeners = {}; this.closed = false; FakeEventSource.last = this; }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  emit(name, payload) { this.listeners[name](payload === undefined ? {} : { data: JSON.stringify(payload) }); }
  close() { this.closed = true; }
}

const TRACK = { seed: 1000, lanes: 12, max_rows: 300, gaps: [[], [5]] };
const frame = (row) => ({ row, lane: 6, landing: [row + 1, 6], alive: true, finished: false });
const episode = (player, frames) => ({ player, seed: 1000, run_id: "r", complete: true, finished: false, death_cause: "ran_into_gap",
                                       rows_survived: 2, max_rows: 300, questions: [], frames });

test("an embedded replay arrives as meta, then each episode and its frames in order", () => {
  const { calls, handlers } = recorder();
  const replay = { runs: [{ run_id: "r" }], players: ["fly", "llm"], seeds: [1000], tracks: { 1000: TRACK },
                   scoreboard: { columns: ["player"], rows: [], same_seeds: true },
                   episodes: [episode("fly", [frame(0), frame(1)]), episode("llm", [frame(0)])] };
  fromEmbedded(replay, handlers);
  assert.deepEqual(calls.map((c) => c[0]), ["meta", "episode", "frame", "frame", "episode", "frame"]);
  assert.deepEqual(calls[0][1], { runs: replay.runs, players: replay.players, seeds: [1000], scoreboard: replay.scoreboard });
  const [, header, track] = calls[1];
  assert.equal(header.player, "fly");
  assert.equal(header.death_cause, "ran_into_gap");
  assert.equal("frames" in header, false); // the page builds its own list from onFrame
  assert.equal(track, TRACK);
  assert.deepEqual(calls[3], ["frame", "fly", 1000, frame(1), null]);
  assert.equal(replay.episodes[0].frames.length, 2); // the replay object is not changed
});

test("an empty replay, as the live page embeds it, is only meta", () => {
  const { calls, handlers } = recorder();
  fromEmbedded({ runs: [], players: [], seeds: [], tracks: {}, episodes: [] }, handlers);
  assert.deepEqual(calls, [["meta", { runs: [], players: [], seeds: [], scoreboard: { columns: [], rows: [], same_seeds: true } }]]);
});

test("a live stream delivers the same calls in the replay's own shapes", () => {
  const { calls, handlers } = recorder();
  const source = fromStream("/events", handlers, FakeEventSource);
  assert.equal(source.url, "/events");
  const summary = { complete: false, finished: false, death_cause: null, rows_survived: 1 };
  source.emit("episode", { episode: { ...episode("fly", []), complete: false }, track: TRACK });
  source.emit("frame", { player: "fly", seed: 1000, frame: frame(0), summary });
  assert.deepEqual(calls.map((c) => c[0]), ["episode", "frame"]);
  assert.deepEqual(calls[0][2], TRACK);
  assert.deepEqual(calls[1], ["frame", "fly", 1000, frame(0), summary]);
});

test("history replayed after a reconnect is dropped: no episode twice, no row twice", () => {
  const { calls, handlers } = recorder();
  const source = fromStream("/events", handlers, FakeEventSource);
  const header = { episode: episode("fly", []), track: TRACK };
  source.emit("episode", header);
  source.emit("frame", { player: "fly", seed: 1000, frame: frame(0) });
  source.emit("frame", { player: "fly", seed: 1000, frame: frame(2) }); // a jump: rows are not consecutive
  source.emit("episode", header);
  source.emit("frame", { player: "fly", seed: 1000, frame: frame(0) });
  source.emit("frame", { player: "fly", seed: 1000, frame: frame(2) });
  source.emit("frame", { player: "fly", seed: 1000, frame: frame(3) });
  source.emit("frame", { player: "llm", seed: 1000, frame: frame(0) }); // no episode yet: nothing to add it to
  assert.deepEqual(calls.map((c) => (c[0] === "frame" ? c[3].row : c[0])), ["episode", 0, 2, 3]);
});

test("the end closes the stream, so the browser does not reconnect and start over", () => {
  const { calls, handlers } = recorder();
  const source = fromStream("/events", handlers, FakeEventSource);
  source.emit("end", { status: "completed", runs: [{ run_id: "r" }], scoreboard: { columns: [], rows: [], same_seeds: true } });
  assert.equal(source.closed, true);
  assert.equal(calls[0][0], "end");
  assert.equal(calls[0][1].status, "completed");
});

test("our error event carries a message, a dropped connection does not", () => {
  const { calls, handlers } = recorder();
  const source = fromStream("/events", handlers, FakeEventSource);
  source.emit("error", { message: "request cap of 5 reached" });
  source.emit("error");
  assert.deepEqual(calls, [["error", "request cap of 5 reached"], ["error", null]]);
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `node --test viewer/tests/feed.test.js`
Expected:

```text
✖ viewer/tests/feed.test.js
ℹ pass 0
ℹ fail 1
```

- [ ] **Step 3: Write the implementation**

Create `viewer/feed.js`:

```javascript
// The one way frames reach the page. A replay file and a live run look the same to it:
//
//   handlers.onMeta({runs, players, seeds, scoreboard})   once, from the embedded replay
//   handlers.onEpisode(episode, track)                    an episode begins; `episode` has no frames yet
//   handlers.onFrame(player, seed, frame, summary)        one decision; `summary` is the episode's
//                                                         {complete, finished, death_cause, rows_survived}
//                                                         after it, or null when the episode already says
//   handlers.onEnd({status, runs, scoreboard})            live only: the run is over
//   handlers.onError(message)                             live only
//
// fromEmbedded(replay) reads the object bakeoff/replay.py built (docs/REPLAY_DATA.md). fromStream(url)
// listens to `bakeoff live`, whose events carry the same shapes. The page never reads the replay object
// itself. Pure apart from the EventSource, which tests replace.
(function (root) {
  "use strict";

  const header = (episode) => {
    const copy = { ...episode };
    delete copy.frames;
    return copy;
  };

  function fromEmbedded(replay, handlers) {
    handlers.onMeta({ runs: replay.runs || [], players: replay.players || [], seeds: replay.seeds || [],
                      scoreboard: replay.scoreboard || { columns: [], rows: [], same_seeds: true } });
    for (const episode of replay.episodes || []) {
      handlers.onEpisode(header(episode), (replay.tracks || {})[String(episode.seed)]);
      for (const frame of episode.frames) handlers.onFrame(episode.player, episode.seed, frame, null);
    }
  }

  // Events: `episode` {episode, track}, `frame` {player, seed, frame, summary}, `end` {status, runs,
  // scoreboard}, `error` {message}. The server replays its history to a page that connects late or
  // reconnects, so an episode or a row that was already delivered is dropped here.
  function fromStream(url, handlers, EventSourceClass) {
    const Source = EventSourceClass || root.EventSource;
    const source = new Source(url);
    const lastRow = {}; // "player seed" -> the last row delivered
    const data = (event) => JSON.parse(event.data);
    source.addEventListener("episode", (event) => {
      const { episode, track } = data(event);
      const key = episode.player + " " + episode.seed;
      if (key in lastRow) return;
      lastRow[key] = -1;
      handlers.onEpisode(header(episode), track);
    });
    source.addEventListener("frame", (event) => {
      const { player, seed, frame, summary } = data(event);
      const key = player + " " + seed;
      if (!(key in lastRow) || frame.row <= lastRow[key]) return;
      lastRow[key] = frame.row;
      handlers.onFrame(player, seed, frame, summary || null);
    });
    source.addEventListener("end", (event) => {
      source.close(); // or the browser would reconnect and the run would seem to start again
      handlers.onEnd(data(event));
    });
    // a named `error` event is ours and carries JSON; a bare one is the browser's (the connection dropped)
    source.addEventListener("error", (event) => {
      if (event && typeof event.data === "string") handlers.onError(data(event).message);
      else handlers.onError(null);
    });
    return source;
  }

  const api = { fromEmbedded, fromStream };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Feed = api;
})(typeof window !== "undefined" ? window : globalThis);
```

- [ ] **Step 4: Run the task's tests**

Run: `node --test viewer/tests/feed.test.js`
Expected: `pass 6, fail 0`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `264 passed, 9 deselected`

- [ ] **Step 6: Commit**

```bash
git add viewer/feed.js viewer/tests/feed.test.js
git commit -F <message file>   # feat: feed.js: a replay file and a live stream reach the page as the same calls
```

---

### Task 6: The composed Jev's panel, tags, and the order of the players

**Files:**
- Modify: `bakeoff/replay.py`
- Modify: `docs/REPLAY_DATA.md`
- Modify: `viewer/minds.js`
- Test: `tests/test_replay.py`
- Test: `viewer/tests/minds.test.js`

**Interfaces:**
- Consumes: frames of `jev_composed` (`answers.gap_<action>.noul`, `info.order`).
- Produces: `Minds.jevComposedMind(frame)`, `Minds.visorP(frame) -> number | null`, `Minds.tagOf(player)`; `statusLine` and `verdict` use class `bad` for a death and an error; `replay.players` is ordered fly, jev_composed, llm, jev, then the rest.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_replay.py`:

```diff
@@ -117,6 +117,12 @@ def test_runs_are_merged_with_the_contestants_first(tmp_path):
     assert board["same_seeds"] is False  # the fly played a seed the others did not
 
 
+def test_the_demos_three_come_first_then_the_one_shot_jev(tmp_path):
+    run_dir = write_run(tmp_path, "a", [record(p, track=TRACK) for p in ("jev", "llm", "solver", "jev_composed", "fly")],
+                        meta={"players": ["jev", "llm", "solver", "jev_composed", "fly"], "seeds": [0]})
+    assert build_replay([run_dir])["players"] == ["fly", "jev_composed", "llm", "jev", "solver"]
+
+
 def test_other_players_keep_the_order_the_run_planned(tmp_path):
     run_dir = write_run(tmp_path, "a", [record("solver", track=TRACK), record("always_jump", track=TRACK),
                                         record("fly", track=TRACK)],
```

Apply to `viewer/tests/minds.test.js`:

```diff
@@ -141,6 +141,43 @@ test("Minds.ours names the calibrated four and says the rest were not tuned", ()
   assert.match(html, /cap, the step and the window length are fixed design choices of ours and were not tuned/);
 });
 
+test("composed Jev shows its four answers with the chosen action marked, and says what is ours", () => {
+  const answers = { gap_left: { noul: 0.97 }, gap_stay: { noul: 0.02 }, gap_right: { noul: 0.5 }, gap_jump: { noul: 0.01 } };
+  const info = { model: "jev-latest", rule: "lowest_gap_probability", order: ["stay", "left", "right", "<b>jump</b>"] };
+  const html = Minds.mind({ player: "jev_composed", questions: [] }, frame({ answers, info, chosen_action: "jump", executed_action: "jump" }), context());
+  assert.match(html, /Lands on a gap\?/);
+  assert.match(html, /<tr class="picked"><th>jump<\/th>/);
+  assert.equal(count(html, 'class="picked"'), 1);
+  assert.match(html, /<th>left<\/th><td>.*?<\/td><td>97%<\/td>/);
+  assert.match(html, /ties in the order stay, left, right, &#60;b&#62;jump&#60;\/b&#62;/); // from the log, so escaped
+  assert.match(html, /The wording and that rule are ours\. It looks one step ahead only\./);
+  assert.equal(Minds.jevComposedMind(frame()), ""); // after a provider error there are no answers
+  const partial = Minds.jevComposedMind(frame({ answers: { gap_left: { noul: 0.4 } }, chosen_action: null }));
+  assert.equal(count(partial, "–"), 3); // an answer that did not arrive is a dash, never 0%
+  assert.equal(count(partial, 'class="picked"'), 0);
+});
+
+test("the visor shows how sure Jev was that the move it chose is safe", () => {
+  const answers = { gap_left: { noul: 0.97 }, gap_stay: { noul: 0.02 }, gap_right: { noul: 0.5 }, gap_jump: { noul: 0.25 } };
+  assert.equal(Minds.visorP(frame({ answers, chosen_action: "jump" })), 0.75);
+  assert.equal(Minds.visorP(frame({ answers, chosen_action: "stay" })), 0.98);
+  assert.equal(Minds.visorP(frame({ answers, chosen_action: null })), null); // an invalid answer: the slit is dark
+  assert.equal(Minds.visorP(frame({ answers: null })), null);
+  assert.equal(Minds.visorP(frame({ answers: { gap_stay: { noul: "0.1" } } })), null);
+});
+
+test("tags are short and uppercase, and an unknown player still gets one", () => {
+  assert.deepEqual(["fly", "jev_composed", "llm", "jev"].map(Minds.tagOf), ["FLY", "JEV", "LLM", "JEV ONE-SHOT"]);
+  assert.equal(Minds.tagOf("my_bot"), "MY_BOT");
+});
+
+test("a death and an error are marked bad, a stopped run is only a warning", () => {
+  const episode = { rows_survived: 23, death_cause: "ran_into_gap" };
+  assert.match(Minds.statusLine(episode, { status: "dead" }, 12), /^<span class="bad">/);
+  assert.match(Minds.statusLine(episode, { status: "cut" }, 12), /^<span class="warn">/);
+  assert.match(Minds.verdict(frame({ error: "boom", chosen_action: null })), /<p class="bad">boom<\/p>/);
+});
+
 test("Minds.ours shows the provisional warning instead of the calibration sentence", () => {
   const html = Minds.ours(flyRun({ fly: { turn_threshold_hz: 0, jump_threshold_hz: 200, window_ms: 100, provisional: true } }));
   assert.match(html, /provisional when this run was made/);
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_replay.py tests/test_viewer_js.py`
Expected:

```text
FAILED tests/test_replay.py::test_the_demos_three_come_first_then_the_one_shot_jev
FAILED tests/test_viewer_js.py::test_viewer_javascript - AssertionError: ✔ an...
2 failed, 18 passed
```

- [ ] **Step 3: Write the implementation**

Apply to `bakeoff/replay.py`:

```diff
@@ -12,7 +12,9 @@ from bakeoff.report import COLUMNS, load_meta, load_steps, summarize
 
 REPLAY_VERSION = 1
 SCHEMA_VERSION = 1  # the step record this module reads; the runner writes it (a test keeps the two equal)
-CONTESTANTS = ("fly", "jev", "llm")  # shown first, in this order; everyone else in order of appearance
+# shown first, in this order: the demo's three (the composed Jev is its Jev), then the one-shot Jev;
+# everyone else in order of appearance
+CONTESTANTS = ("fly", "jev_composed", "llm", "jev")
 # what a frame leaves out of its step record: the first three name the episode, the others are
 # replaced by `ahead`, `q` and the replay's `tracks`
 DROPPED = ("run_id", "player", "seed", "senses", "questions", "track")
```

Apply to `docs/REPLAY_DATA.md`:

```diff
@@ -11,7 +11,7 @@ records it is built from are described in `docs/STEP_RECORD.md`.
 | --- | --- | --- |
 | `replay_version` | int | 1. Bumped on any breaking change to this object |
 | `runs` | object[] | one per run directory, in the order given: `run_id` plus these keys of its `meta.json`, null when absent: `status`, `git_sha`, `git_dirty`, `started_at`, `finished_at`, `players`, `seeds`, `game`, `fly`, `models`, `requests`. A directory without `meta.json` is named after the directory |
-| `players` | string[] | players with at least one episode: `fly`, `jev`, `llm` first, the others in the order the runs planned them |
+| `players` | string[] | players with at least one episode: `fly`, `jev_composed`, `llm` (the demo's three), then `jev`, then the others in the order the runs planned them |
 | `seeds` | int[] | every seed with at least one episode, ascending |
 | `tracks` | object | `{"<seed>": track}`, the step record's `track`. When runs played the same seed with different `max_rows`, the longest is kept (the shorter one is its prefix) |
 | `episodes` | object[] | one per (player, seed), sorted by seed, then by `players` order |
```

Apply to `viewer/minds.js`:

```diff
@@ -7,6 +7,9 @@
   const FLY_GROUPS = [
     ["DNa01", "steering"], ["DNb01", "steering"], ["DNp01", "Giant Fiber, escape jump"], ["DNa02", "logged only"],
   ];
+  // the short uppercase tag a runner carries in the tunnel and on its panel
+  const TAGS = { fly: "FLY", jev_composed: "JEV", llm: "LLM", jev: "JEV ONE-SHOT", solver: "SOLVER", random: "RANDOM", always_jump: "JUMPER" };
+  const tagOf = (player) => TAGS[player] || String(player).toUpperCase();
   const DEATHS = {
     ran_into_gap: "ran straight into a gap",
     jumped_into_gap: "jumped into a gap",
@@ -64,7 +67,7 @@
       : depth === best ? "as good as any move (" + esc(best) + " rows seen safe)"
       : "solver preferred " + safe.join(" or ") + " (" + esc(best) + " rows safe, this move " + esc(depth) + ")";
     return '<p class="verdict">' + line + '<br><span class="muted">' + rating + "</span></p>" +
-      (frame.error != null ? '<p class="warn">' + esc(frame.error) + "</p>" : "");
+      (frame.error != null ? '<p class="bad">' + esc(frame.error) + "</p>" : "");
   }
 
   // windowMs null: the window is unknown, so the x axis is scaled by the frame's own latest spike instead
@@ -139,6 +142,28 @@
     return html + '<p class="muted">The two yes/no questions are asked alongside the move and never influence it.</p>';
   }
 
+  // Composed Jev: four yes/no answers, one per action, and the rule that turns them into a move.
+  function jevComposedMind(frame) {
+    const answers = frame.answers;
+    if (!answers) return "";
+    const rows = ACTIONS.map((a) => {
+      const noul = (answers["gap_" + a] || {}).noul;
+      const known = typeof noul === "number";
+      return "<tr" + (a === frame.chosen_action ? ' class="picked"' : "") + "><th>" + a + "</th><td>" + bar(known ? noul : 0) +
+        "</td><td>" + (known ? percent(noul) : "–") + "</td></tr>";
+    }).join("");
+    const order = frame.info && Array.isArray(frame.info.order) ? frame.info.order.map(esc).join(", ") : null;
+    return '<p class="label">Lands on a gap?</p><table class="probs">' + rows + "</table>" +
+      '<p class="muted">Four yes/no questions in one request; code picks the lowest' + (order ? ", ties in the order " + order : "") +
+      ". The wording and that rule are ours. It looks one step ahead only.</p>";
+  }
+
+  // How sure the composed Jev was that the move it chose does not land on a gap (the visor's slit), or null
+  function visorP(frame) {
+    const answer = (frame.answers || {})["gap_" + frame.chosen_action];
+    return answer && typeof answer.noul === "number" ? 1 - answer.noul : null;
+  }
+
   function llmMind(frame) {
     const answers = frame.answers;
     if (!answers) return "";
@@ -185,6 +210,7 @@
   function mind(episode, frame, context) {
     const body = episode.player === "fly" ? flyMind(frame, context)
       : episode.player === "jev" ? jevMind(frame)
+      : episode.player === "jev_composed" ? jevComposedMind(frame)
       : episode.player === "llm" ? llmMind(frame) : "";
     return '<div class="saw">' + sensesGrid(frame, context.window) + verdict(frame) + "</div>" + body + cost(frame) + asked(episode, frame);
   }
@@ -192,13 +218,14 @@
   // one line under the tunnel: where the runner is, or how the episode ended
   function statusLine(episode, state, lanes) {
     const rows = esc(episode.rows_survived);
-    if (state.status === "dead") return '<span class="warn">Fell after ' + rows + " rows: " + (DEATHS[episode.death_cause] || "fell") + "</span>";
+    if (state.status === "dead") return '<span class="bad">Fell after ' + rows + " rows: " + (DEATHS[episode.death_cause] || "fell") + "</span>";
     if (state.status === "finished") return "Reached the finish line, " + rows + " rows";
     if (state.status === "cut") return '<span class="warn">Run stopped after ' + rows + " rows (not a death)</span>";
     return "row " + Math.floor(state.row) + ", lane " + (((Math.round(state.lane) % lanes) + lanes) % lanes);
   }
 
-  const api = { esc, cell, bar, sensesGrid, verdict, spikeRaster, flyMind, jevMind, llmMind, cost, asked, ours, mind, statusLine };
+  const api = { esc, cell, bar, tagOf, sensesGrid, verdict, spikeRaster, flyMind, jevMind, jevComposedMind, visorP, llmMind, cost, asked,
+                ours, mind, statusLine };
   if (typeof module !== "undefined" && module.exports) module.exports = api;
   else root.Minds = api;
 })(typeof window !== "undefined" ? window : globalThis);
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_replay.py tests/test_viewer_js.py`
Expected: `20 passed`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `265 passed, 9 deselected`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/replay.py docs/REPLAY_DATA.md tests/test_replay.py viewer/minds.js viewer/tests/minds.test.js
git commit -F <message file>   # feat: the composed Jev's panel and visor reading, tags, deaths marked bad; the demo's three come first
```

---

### Task 7: The page

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `docs/REPLAY_DATA.md`
- Modify: `viewer/app.js`
- Modify: `viewer/index.html`
- Modify: `viewer/viewer.css`
- Test: `tests/test_view.py`

**Interfaces:**
- Consumes: everything above.
- Produces: the page. `body[data-live]` (set by phase 5c) switches the feed to a stream and shows the `LIVE` button.

`viewer/app.js`, `viewer/index.html` and `viewer/viewer.css` are replaced whole: write each file from the block below, do not edit the old one. The first three lines of `viewer/viewer.css` (the comment and the two `@font-face` rules from Task 1) are part of the block.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_view.py`:

```diff
@@ -20,7 +20,7 @@ def test_render_inlines_every_file_and_the_data():
     replay = {"replay_version": 1, "episodes": [], "note": "</script>"}
     page = render_html(replay)
     assert "<link" not in page and "<script src" not in page  # one file: nothing left to fetch
-    for name in ("timeline.js", "tunnel.js", "minds.js", "app.js"):
+    for name in ("timeline.js", "tunnel.js", "sprites.js", "stage.js", "minds.js", "feed.js", "app.js"):
         assert (VIEWER_DIR / name).read_text() in page
     rules = (VIEWER_DIR / "viewer.css").read_text().split("}\n\n", 1)[1]  # everything after the two font faces
     assert rules in page
@@ -36,6 +36,21 @@ def test_the_page_makes_no_network_request():
     assert all(url.startswith("data:") for url in re.findall(r"url\(([^)]*)\)", page))  # only embedded data
 
 
+def test_the_page_says_what_is_ours_about_jev_and_the_figures():
+    page = " ".join(render_html({"episodes": []}).split())
+    assert "The wording of those questions and that rule are ours, not TypeSafe's" in page
+    assert "looks one step ahead only" in page
+    assert "landed on a gap about as often as always staying would have" in page
+    assert "our own drawing and nobody's official artwork" in page
+    assert "The blue marks the mind in focus and the tiles it was shown, nothing else." in page
+
+
+def test_every_script_the_page_names_exists_and_app_comes_last():
+    names = re.findall(r'<script src="([^"]+)"></script>', (VIEWER_DIR / "index.html").read_text())
+    assert names == ["timeline.js", "tunnel.js", "sprites.js", "stage.js", "minds.js", "feed.js", "app.js"]
+    assert all((VIEWER_DIR / name).is_file() for name in names)
+
+
 def test_the_two_brand_fonts_are_embedded_not_fetched():
     page = render_html({"episodes": []})
     fonts = re.findall(r"@font-face\s*{[^}]*}", page)
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_view.py`
Expected:

```text
FAILED tests/test_view.py::test_render_inlines_every_file_and_the_data - asse...
FAILED tests/test_view.py::test_the_page_says_what_is_ours_about_jev_and_the_figures
FAILED tests/test_view.py::test_every_script_the_page_names_exists_and_app_comes_last
3 failed, 8 passed
```

- [ ] **Step 3: Write the implementation**

Apply to `CLAUDE.md`:

```diff
@@ -51,9 +51,13 @@ its own plan.
 - `uv run pytest` runs the fast tests only. `uv run pytest -m slow` builds the real fly brain (about 1 GB,
   one minute); never run two fly processes at once.
 - The viewer is plain JavaScript with no build step and no npm packages. Rules of the game stay in
-  Python (`bakeoff/replay.py`); the pure JavaScript (`timeline.js`, `tunnel.js`, `minds.js`) is tested by
+  Python (`bakeoff/replay.py`); the pure JavaScript (`timeline.js`, `tunnel.js`, `sprites.js`, `stage.js`, `minds.js`,
+  `feed.js`) is tested by
   `viewer/tests/*.test.js`, which `uv run pytest` runs through `node --test`. Text from a log is always
-  escaped (`Minds.esc`) and the page must never load anything from the network.
+  escaped (`Minds.esc`) and the page must never load anything from the network (the two brand fonts in
+  `viewer/fonts/` are embedded as base64 by `bakeoff/view.py`). The page is the user's brand: tokens from
+  `~/Documents/PROJECTS/BRAND/brand.css`, blue only for the cursor (the mind in focus and its tiles), mono for short
+  labels only, deaths and errors `--bad`, warnings `--warn`. Frames reach `app.js` through `Feed` alone.
 - Paid players spend nothing without `--max-requests` (default 0 replays `.cache/responses`). Never
   raise a cap, rerun a paid command or run `pytest -m live` without the user's go-ahead. No paid
   request on a seed below 1000 before the tournament; the CLI refuses a live paid run on seeds
```

Apply to `README.md`:

```diff
@@ -43,10 +43,15 @@ makes one real request per provider. A live paid run on seeds below 1000 is refu
 ends there, so later players in the list do not play: put free players first, or run paid players
 alone.
 
-`view` writes one self-contained HTML file (no server, no network): the players of a track side by
-side in the tunnel, each with what it had in mind (the fly's spikes and read-out signals, Jev's
-probabilities, the LLM's answer), a table of rows survived per track, the scoreboard, and what in
-the fly's set-up is ours rather than the fly's. Several run directories are merged, since the fly and
+`view` writes one self-contained HTML file (no server, no network, fonts embedded): the demo player. The
+fly, the composed Jev and the LLM run one tunnel together as pixel figures (fixed camera, everyone on the
+same row at the same time), with a strip of panels underneath showing what each had in mind (the fly's
+spikes and read-out signals, Jev's four answers, the LLM's answer). Blue is the cursor: it marks the mind
+in focus and the tiles that mind was shown, and with auto on it cuts to whoever faces a gap (keys 1, 2, 3
+or a click choose by hand; space plays, the arrows step a row). Below are the level table (rows survived
+per track; it picks the track and shows or hides runners, baselines and the one-shot Jev included), the
+scoreboard, and what in the set-up is ours rather than the fly's or TypeSafe's. The look is the user's
+brand (`~/Documents/PROJECTS/BRAND/brand.css`). Several run directories are merged, since the fly and
 the paid players usually run separately; one (player, seed) may appear only once. Viewing costs
 nothing: it reads logs only. The viewer's JavaScript has its own tests, which `uv run pytest` runs
 through `node --test` (skipped when node is not installed).
```

Apply to `docs/REPLAY_DATA.md`:

```diff
@@ -45,8 +45,11 @@ Frames are sorted by `row`. A jump advances two rows, so rows are not consecutiv
 
 ## How the viewer uses it
 
+The page never reads this object directly: `viewer/feed.js` hands it over as calls (`onMeta`, then
+`onEpisode` and `onFrame` per episode), the same calls a live run will make, so the two cannot drift apart.
+
 Replay time is measured in rows and every player is on the same clock: at time `t` every runner
-still alive is at row `t`, so the columns show the same stretch of track. The frame on screen is
+still alive is at row `t`, so they all run the same stretch of one tunnel. The frame on screen is
 the last one with `row <= t`; between `row` and `landing[0]` the runner moves from one to the
 other (a jump takes two ticks). After the last frame's landing the episode is `dead`, `finished`
 or, when `complete` is false, `cut`.
```

Replace the whole of `viewer/app.js` with:

```javascript
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
  const store = { runs: [], players: [], seeds: [], tracks: {}, episodes: [], scoreboard: null, ended: !liveUrl, error: null };
  const view = {
    seed: null, shown: new Set(), focus: null, auto: true, heldSince: 0,
    t: 0, playing: false, speed: 3, following: !!liveUrl, size: 0, runners: [], panels: {},
  };

  const runOf = (episode) => store.runs.find((run) => run.run_id === episode.run_id) || {};
  const episodeOf = (player, seed) => store.episodes.find((e) => e.player === player && e.seed === seed);
  const playing = () => store.episodes.filter((e) => e.seed === view.seed && view.shown.has(e.player) && e.frames.length)
    .sort((a, b) => order(a.player) - order(b.player));
  const order = (player) => {
    const at = store.players.indexOf(player);
    return at < 0 ? store.players.length : at;
  };

  const handlers = {
    onMeta(meta) {
      Object.assign(store, { runs: meta.runs, players: meta.players.slice(), seeds: meta.seeds.slice(), scoreboard: meta.scoreboard });
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
      store.error = message;
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

  function arrived(episode) { // live: a runner joins
    if (view.seed == null) view.seed = episode.seed;
    if (episode.seed === view.seed && (DEMO.includes(episode.player) || !view.shown.size)) view.shown.add(episode.player);
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
      strip.innerHTML = '<p class="note" style="padding:16px">None of the players shown ran track ' + esc(view.seed) +
        ". Pick a player in the level table to show it.</p>";
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
      $("track-label").textContent = "Track " + view.seed;
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

  $("play").addEventListener("click", () => setPlaying(!view.playing));
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
    if (event.key === " ") { event.preventDefault(); setPlaying(!view.playing); }
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
    handlers.onFrame = (...args) => { if (!store.error) notice(null); clear(...args); };
    Feed.fromStream(liveUrl, handlers);
  }
})();
```

Replace the whole of `viewer/index.html` with:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tunnel Run</title>
<link rel="stylesheet" href="viewer.css">
</head>
<body>
<header class="top">
  <h1 class="label">Tunnel Run</h1>
  <p class="label" id="mode"></p>
</header>

<main id="app" hidden>
  <section id="player" aria-label="The run">
    <div id="tunnel">
      <canvas id="canvas" aria-label="Three runners in one tunnel. The same information is in the panels below."></canvas>
      <span class="label corner left" id="row-label"></span>
      <span class="label corner right" id="track-label"></span>
      <p class="label corner bottom" id="notice" hidden></p>
    </div>
    <div id="strip"></div>
    <p class="note"><span id="sight"></span> The blue marks the mind in focus and the tiles it was shown, nothing else.
      Everyone is on the same row at the same time: a jump covers two rows, so it takes two ticks.</p>
  </section>

  <section aria-label="Levels">
    <h2 class="label">Levels</h2>
    <div class="scroll"><table id="matrix"></table></div>
    <p class="note">Rows survived on each track. Pick a track to play it; pick a player to show or hide its runner.
      ✓ reached the finish line · … the run was stopped, which is not a death · a number after a slash is the
      length of a shorter run.</p>
  </section>

  <section aria-label="Scoreboard">
    <h2 class="label">Scoreboard</h2>
    <p id="fairness" class="warn" hidden>The rows of this table do not all average the same tracks, so their averages are
      not a fair comparison. Compare the players track by track in the table above.</p>
    <div class="scroll"><table id="scoreboard"></table></div>
    <p class="note">The columns of <code>python -m bakeoff report</code>. Only complete runs count; a run that was stopped
      is listed as incomplete, not as a death.</p>
  </section>

  <section id="honesty" aria-label="What is the fly's and what is ours">
    <h2 class="label">What is the fly's and what is ours</h2>
    <div class="prose">
      <p>The fly is the published whole-brain model of the adult <i>Drosophila</i> connectome (Shiu et al., Nature 2024;
        FlyWire v783, 138,639 neurons), untrained, with default parameters. Gaps stimulate the looming detectors of
        each eye (LPLC2 and LC4); the steering neurons DNa01 and DNb01 are read as left and right, the Giant Fiber
        (DNp01) as jump. The wiring is the fly's. These numbers are ours:</p>
      <ul id="ours"></ul>
      <p>Known weaknesses:</p>
      <ul>
        <li>The fly does not plan. It flees gaps by reflex and may dodge into another gap.</li>
        <li>Its input is crude: a whole eye is stimulated at one rate. Stimulating part of the visual field was not tested.</li>
        <li>On equal input to both eyes its deciding read-out leans right (0 to +20 Hz, never negative; the model's
          left eye has 162 looming cells, its right eye 152). With our turn threshold (listed above) that lean decides
          moves: a gap straight ahead that does not trigger a jump usually becomes a step to the right. The lean is the
          fly's, the threshold that exposes it is ours.</li>
        <li>The wiring also has a mild left bias in DNa02, which is logged but never decides.</li>
        <li>The model has no spontaneous activity and no memory between decisions; trial-to-trial spread comes only
          from the random input spikes.</li>
      </ul>
      <p>Jev and the LLM. The Jev in this player is the composed Jev: each row it is asked four yes/no questions in one
        request, one per action ("would <code>left</code> land the runner on a gap, that is, does
        <code>ahead[0].gaps_relative</code> contain -1?"), and code picks the action it thinks least likely to land on a
        gap, ties in the order stay, left, right, jump. The wording of those questions and that rule are ours, not
        TypeSafe's, and the rule looks one step ahead only; it does not plan. We built it after measuring the one-shot
        Jev, which answers a single broad question ("which action?"): on the dangerous rows of practice track 1000 its
        choice landed on a gap about as often as always staying would have, while its narrow yes/no answers were almost
        always right. The one-shot Jev is still in the level table for comparison. The LLM answers one question per
        row and is told the rules in the same words as the one-shot Jev; what each was asked is under every panel.</p>
      <p>The figures are ours too: a fruit fly, a visor whose slit shows how sure Jev is that its move is safe, and an
        orange critter for the LLM, which is our own drawing and nobody's official artwork.</p>
    </div>
  </section>

  <section aria-label="Runs">
    <h2 class="label">Runs</h2>
    <p class="note" id="runs"></p>
  </section>
</main>

<p id="empty" class="note">This is the viewer's template. Build a replay with
  <code>uv run python -m bakeoff view runs/&lt;run_id&gt;</code>, or go live with <code>uv run python -m bakeoff live</code>.</p>

<nav id="transport" aria-label="Transport" hidden>
  <button id="play" type="button" class="label">Play</button>
  <button id="back" type="button" class="label" aria-label="Back one row">&lsaquo;</button>
  <button id="forward" type="button" class="label" aria-label="Forward one row">&rsaquo;</button>
  <div id="speeds" role="group" aria-label="Rows a second">
    <button type="button" class="label" data-speed="1">1</button>
    <button type="button" class="label" data-speed="3" aria-pressed="true">3</button>
    <button type="button" class="label" data-speed="8">8</button>
    <button type="button" class="label" data-speed="20">20</button>
  </div>
  <input id="scrub" type="range" min="0" max="1" step="0.01" value="0" aria-label="Position on the track">
  <button id="live" type="button" class="label" aria-pressed="true" hidden>Live</button>
  <output id="clock" class="label"></output>
  <button id="auto" type="button" class="label" aria-pressed="true" title="Let the focus cut to whoever faces a gap">Auto</button>
</nav>

<script type="application/json" id="replay-data">null</script>
<script src="timeline.js"></script>
<script src="tunnel.js"></script>
<script src="sprites.js"></script>
<script src="stage.js"></script>
<script src="minds.js"></script>
<script src="feed.js"></script>
<script src="app.js"></script>
</body>
</html>
```

Replace the whole of `viewer/viewer.css` with:

```css
/* The two brand fonts (OFL, viewer/fonts/LICENSE.md). bakeoff/view.py embeds them as base64. */
@font-face { font-family: "Hanken Grotesk"; font-style: normal; font-weight: 100 900; font-display: swap; src: url(fonts/HankenGrotesk-latin.woff2) format("woff2"); }
@font-face { font-family: "JetBrains Mono"; font-style: normal; font-weight: 100 800; font-display: swap; src: url(fonts/JetBrainsMono-latin.woff2) format("woff2"); }

/* Tokens verbatim from the brand stylesheet (~/Documents/PROJECTS/BRAND/brand.css). Dark only.
   House rules kept here: blue is rationed (in this page it is the cursor: the mind in focus and the tiles
   it was shown, nothing else; status uses --bad and --warn), mono is for short uppercase labels only,
   no gradients, no glow, no rounded cards. */
:root {
  --void: #0A0A0A; --panel: #0D0F12; --hairline: #1E2227; --line-strong: #2A2F35;
  --muted: #7C848D; --text: #C9CDD2; --bright: #E8EBED; --accent: #7AA2F7;
  --good: #9ECE6A; --warn: #E0AF68; --bad: #F7768E;
  --font-body: "Hanken Grotesk", "Helvetica Neue", Arial, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, Menlo, monospace;
  --size-body: 16px; --size-small: 14px; --size-label: 12px; --size-label-sm: 11px;
  --leading-body: 1.6; --tracking-label: 0.08em; --measure: 600px;
  --gutter: 24px; --margin: 80px; --section: 56px;
  --ease: cubic-bezier(.2, .7, .2, 1); --fast: 200ms;
  --transport: 64px;
}
@media (max-width: 720px) { :root { --margin: 16px; --section: 48px; } }

* { box-sizing: border-box; }
body {
  margin: 0; padding: 0 var(--margin) calc(var(--transport) + 48px);
  background: var(--void); color: var(--text);
  font: var(--size-body)/var(--leading-body) var(--font-body); -webkit-font-smoothing: antialiased;
}
:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
::selection { background: var(--bright); color: var(--void); }
p { margin: 0; }
code { font: inherit; color: var(--bright); }
.label {
  margin: 0; font: 400 var(--size-label)/1.4 var(--font-mono); letter-spacing: var(--tracking-label);
  text-transform: uppercase; color: var(--muted);
}
.note { max-width: var(--measure); margin-top: 16px; font-size: var(--size-small); color: var(--muted); text-wrap: pretty; }
.muted { color: var(--muted); }
.warn { color: var(--warn); }
.bad { color: var(--bad); }

.top { display: flex; justify-content: space-between; gap: var(--gutter); padding: 20px 0; }
.top h1 { color: var(--bright); }
section { margin-top: var(--section); border-top: 1px solid var(--hairline); padding-top: 24px; }
section > h2.label { margin-bottom: 20px; }
#fairness { max-width: var(--measure); margin-bottom: 16px; font-size: var(--size-small); }
#player { margin-top: 0; border-top: 0; padding-top: 0; }

/* ---- the tunnel ---------------------------------------------------------------------------- */
#tunnel { position: relative; margin: 0 auto; background: var(--void); border: 1px solid var(--hairline); }
#canvas { display: block; width: 100%; height: 100%; cursor: pointer; }
.corner { position: absolute; top: 14px; pointer-events: none; }
.corner.left { left: 16px; }
.corner.right { right: 16px; }
.corner.bottom { top: auto; bottom: 14px; left: 16px; right: 16px; text-align: center; color: var(--warn); }

/* ---- the mind strip -------------------------------------------------------------------------- */
#strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); margin-top: var(--gutter);
  border: 1px solid var(--hairline); border-right: 0; }
.mind { min-width: 0; padding: 0 16px 20px; background: var(--panel); border-right: 1px solid var(--hairline);
  border-top: 2px solid transparent; font-size: var(--size-small); cursor: pointer; transition: opacity var(--fast) var(--ease); }
.mind[aria-current="true"] { border-top-color: var(--accent); cursor: default; }
.mind[aria-current="true"] .tag { color: var(--accent); }
.mind.fallen .decision { opacity: 0.45; }
.mind header { display: flex; align-items: baseline; gap: 12px; padding: 14px 0 10px; min-height: 44px; }
.mind header .about { color: var(--muted); font-size: var(--size-small); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mind .status { min-height: 1.6em; color: var(--text); }
.mind p { margin-top: 8px; }
.mind .saw { display: flex; gap: 16px; align-items: flex-start; margin-top: 10px; }
.mind .verdict { margin-top: 0; }
.mind .verdict strong { font-weight: 500; font-size: 20px; letter-spacing: -0.015em; color: var(--bright); }
.senses { flex: none; width: 112px; }
.senses .tile { fill: var(--line-strong); }
.senses .gap { fill: var(--void); stroke: var(--hairline); stroke-width: 0.5; }
.senses .me { fill: var(--bright); }

/* bars and rasters are --text on --hairline; the focused panel's bars do not turn blue */
.bar { position: relative; display: block; height: 4px; margin-top: 6px; background: var(--hairline); }
.bar .fill { position: absolute; top: 0; bottom: 0; left: 0; background: var(--text); }
.bar .tick { position: absolute; top: -3px; bottom: -3px; width: 1px; background: var(--muted); }
.eyes { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px; }
.signal { margin-top: 10px; }
.raster { display: block; width: 100%; max-width: 360px; margin-top: 10px; }
.raster text { font: 7px var(--font-mono); fill: var(--muted); }
.raster .spike { stroke: var(--text); stroke-width: 1; }
.probs { width: 100%; margin-top: 8px; border-collapse: collapse; }
.probs th { width: 1%; padding: 3px 12px 3px 0; font-weight: 400; text-align: left; white-space: nowrap; color: var(--muted); }
.probs td { padding: 3px 0; }
.probs td:last-child { width: 1%; padding-left: 12px; text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
.probs .picked th, .probs .picked td { color: var(--bright); }
.probs .picked th::before { content: "› "; }
.answer, details pre { margin: 10px 0 0; padding: 10px 12px; overflow-x: auto; white-space: pre-wrap; word-break: break-word;
  background: var(--void); border: 1px solid var(--hairline); color: var(--text); font: 12px/1.5 var(--font-mono); }
details { margin-top: 10px; }
summary { min-height: 44px; display: flex; align-items: center; cursor: pointer; color: var(--muted); }

@media (max-width: 720px) {
  /* at phone width the mind in focus is open and the others are one line each: tap one to read it */
  #strip { grid-template-columns: 1fr; border-right: 1px solid var(--hairline); }
  .mind { border-right: 0; border-bottom: 1px solid var(--hairline); padding-bottom: 8px; }
  .mind:last-child { border-bottom: 0; }
  .mind:not([aria-current="true"]) > .body { display: none; }
  .mind[aria-current="true"] { padding-bottom: 20px; }
}

/* ---- tables ---------------------------------------------------------------------------------- */
.scroll { overflow-x: auto; }
table { border-collapse: collapse; font-size: var(--size-small); font-variant-numeric: tabular-nums; }
#matrix th, #matrix td, #scoreboard th, #scoreboard td { padding: 6px 14px 6px 0; text-align: right; white-space: nowrap;
  border-bottom: 1px solid var(--hairline); font-weight: 400; }
#matrix th:first-child, #scoreboard th:first-child, #scoreboard td:first-child { text-align: left; }
#scoreboard thead th { font: 400 var(--size-label-sm)/1.4 var(--font-mono); letter-spacing: var(--tracking-label);
  text-transform: uppercase; color: var(--muted); vertical-align: bottom; }
#scoreboard tbody th { color: var(--bright); }
#matrix td.current { color: var(--bright); background: var(--panel); }
#matrix button { min-height: 44px; padding: 0 2px; border: 0; background: none; cursor: pointer; color: var(--muted);
  font: 400 var(--size-label)/1.4 var(--font-mono); letter-spacing: var(--tracking-label); text-transform: uppercase; }
#matrix button:hover { color: var(--bright); }
#matrix button[aria-current="true"], #matrix button[aria-pressed="true"] { color: var(--bright); }
#matrix button[aria-current="true"] { box-shadow: inset 0 -1px 0 var(--bright); }
#matrix button[aria-pressed="true"]::before { content: "■ "; }
#matrix button[aria-pressed="false"]::before { content: "□ "; }

.prose p, .prose ul { max-width: 640px; margin: 0 0 14px; text-wrap: pretty; }
.prose ul { padding-left: 20px; }
.prose li { margin-bottom: 6px; }
#empty { margin-top: 48px; }

/* ---- transport, docked at the bottom of the window ------------------------------------------ */
#transport { position: fixed; left: 0; right: 0; bottom: 0; z-index: 2; min-height: var(--transport); display: flex; align-items: center;
  gap: 8px; padding: 8px var(--margin); background: var(--void); border-top: 1px solid var(--line-strong); }
#transport[hidden] { display: none; }
#transport button { min-width: 44px; min-height: 44px; padding: 0 12px; border: 1px solid var(--hairline); background: var(--panel);
  color: var(--text); cursor: pointer; transition: border-color var(--fast) var(--ease), color var(--fast) var(--ease); }
#transport button:hover { border-color: var(--line-strong); color: var(--bright); }
#transport button[aria-pressed="true"] { border-color: var(--muted); color: var(--bright); }
#transport button[aria-pressed="false"] { color: var(--muted); }
#play { min-width: 76px; }
#speeds { display: flex; }
#speeds button + button { border-left: 0; }
#scrub { flex: 1; min-width: 60px; height: 44px; margin: 0 8px; accent-color: var(--text); background: none; }
#clock { min-width: 9ch; text-align: right; color: var(--text); font-variant-numeric: tabular-nums; }
#live[aria-pressed="true"] { border-color: var(--bad); color: var(--bad); }
@media (max-width: 720px) {
  :root { --transport: 108px; }
  #transport { flex-wrap: wrap; gap: 6px; padding: 6px var(--margin); }
  /* two rows: the scrubber with the row readout, then the buttons (speeds 3 and 8 only, to keep 44 px targets) */
  #scrub { order: -2; flex: 1 1 60%; margin: 0; }
  #clock { order: -1; min-width: 7ch; }
  #live { order: -1; }
  #transport button { padding: 0 8px; }
  #play { min-width: 60px; }
  #speeds button[data-speed="1"], #speeds button[data-speed="20"] { display: none; }
  #auto { margin-left: auto; }
}
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_view.py`
Expected: `11 passed`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `267 passed, 9 deselected`

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md README.md docs/REPLAY_DATA.md tests/test_view.py viewer/app.js viewer/index.html viewer/viewer.css
git commit -F <message file>   # feat: the demo player: one tunnel, three runners, the mind strip, the blue cursor, in the brand
```

---

### Task 8: Look at it (controller only)

- [ ] Build the demo of practice track 1000: `uv run python -m bakeoff view runs/20260919-151934 runs/20260920-102919 runs/20260921-120903 --output demo-1000.html`.
- [ ] Serve its directory on loopback (`python3 -m http.server 8765 --bind 127.0.0.1`; the browser tools refuse `file:`), open it at 1440 by 900 and at 390 by 844: no console error but the missing favicon, no horizontal overflow, keys 1 2 3 / space / arrows / A, a click on a runner and on a panel, auto-focus cutting to a runner in danger, the fly's fall at row 58 and its dimmed panel, the end of the run. Delete `.playwright-mcp/` and the screenshots afterwards.

## Self-review against the spec

| Spec | Where |
| --- | --- |
| one tube, fixed camera, lane 6 at the bottom, concrete tiles fading into the void, finish band, two mono corner labels | Task 2 (`quads`, `draw`), Task 7 (`#row-label`, `#track-label`) |
| runners on the wall, heads toward the axis; same start tile; overlap at 55% and fanned, tags stack; jump lifts and opens the fly's wings; a fall fades over one row | Task 2 (`place`, tested on all 12 lanes), Task 3, Task 4 (`overlaps`), Task 7 |
| the clock is the track | `timeline.js`, unchanged |
| mind strip FLY, JEV, LLM; the grid, the move, the solver's verdict; each mind's own part; a fallen panel dims and says how it ended | Task 6, Task 7 |
| the blue cursor: tag, top edge, tiles; click, keys 1 2 3; auto with the fewest-safe rule, ties to the current focus, 3-row hold; a manual choice turns auto off | Task 2 (`seenOutline`), Task 4 (`autoFocus`), Task 7 |
| transport docked at the bottom: play, step, speeds 1 3 8 20, scrubber, row readout, auto switch, `LIVE` in live mode | Task 7 (the `LIVE` button is hidden until 5c sets `data-live`) |
| below: level table, scoreboard with its fairness note, "what is the fly's and what is ours" with the new paragraph | Task 7 (`tests/test_view.py` asserts the sentences) |
| brand tokens verbatim, blue rationed, bars `--text` on `--hairline`, no decoration, 44 px targets, reduced motion steps row by row | Task 7 |
| one offline file, two fonts with their licence note embedded as base64, nothing fetched | Task 1 |
| `feed.js` is the one way frames reach the page | Task 5, Task 7 |
| every pure function has node tests, incl. three runners on the start tile, a ceiling runner's rotation, the visor at 0, 0.5 and 1, the 3-row hold and the manual pick, fonts present and no network reference | Tasks 1 to 6; the manual pick turning auto off is glue in `app.js`, checked in the browser (Task 8) |

## Rulings on the task reviews (controller, after Task 7)

- **Task 1, Important, fixed:** the stylesheet guard matched `url(` case-sensitively, so `URL(https://...)` reached the page although decision 11 says a stylesheet may load nothing but a bundled font, and the test had the same blind spot. The guard is now case-insensitive and also refuses `@import`, `image-set` and any `http(s):` reference.
- **Tasks 3 to 5, Important, fixed:** `Stage.overlaps` could leave a runner out of a group it overlaps, depending on the order given (a, c, b with b between them); a runner that touches several groups now joins them. Chained grouping itself is intended: runners that overlap through a runner between them must be pulled apart together.
- **Tasks 3 to 5, Important, fixed:** auto-focus stayed on a fallen runner for as long as nobody else was in danger. After the hold (time to read how it ended) it now goes to the first runner still running; with nothing chosen yet it also prefers a runner that is running.
- **Task 7, Important, fixed (glue in `viewer/app.js`, checked in a browser against a free live run):** an episode whose track never arrived is left out instead of throwing; the "connection lost" notice goes with the next frame (a real error stays); pausing a live run turns following off, so the next frame no longer undoes the pause (`LIVE` resumes); an episode without a summary shows an empty cell, not "undefined"; "track null" is now "Nothing has been played yet." Also: the level table's track buttons were 37 px wide at phone width and are now at least 44.

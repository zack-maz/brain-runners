# Phase 2: The Fly Player — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The untrained fruit-fly brain model plays Tunnel Run through its own looming → steering / Giant Fiber wiring, with its looming weighting and two thresholds fixed once on practice seeds, and a first fly-vs-baselines scoreboard.

**Architecture:** `bakeoff/fly/` holds everything that touches the simulation: `data.py` pins and checks the downloaded files, `neurons.py` picks FlyWire IDs by cell type and side, `brain.py` builds the authors' network once and runs one restored 100 ms window per decision. `bakeoff/players/fly.py` is pure thresholding on the brain's read-out rates and never imports the simulator until a fly actually plays. Calibration does not search with the real brain (0.7 s per decision): the looming input is quantised to 11 levels per eye, all 121 inputs are measured once into a committed response surface, and a stand-in brain replays that table so hundreds of candidates can play 200 practice tracks in minutes.

**Tech Stack:** Python 3.13, `uv`, `pytest`; new runtime dependencies `brian2`, `cython`, `setuptools`, `pandas`, `pyarrow`, `joblib`.

**Spec:** `docs/superpowers/specs/2026-09-19-tunnel-run-design.md` (binding; sections "Senses", "Fly player", "Testing"). Background: `docs/DECISIONS.md`, spike report `spikes/01-fly-steering/REPORT.md` on branch `spike/fly-steering` (throwaway code: port ideas, do not merge or copy it).

**Branch:** `phase2-fly-player` (already created; never build on `main`).

## Global Constraints

- Python via `uv` only: `uv add`, `uv run pytest`, `uv run python -m ...`. Python 3.13. Never call `pip` or bare `python`.
- TDD: write the failing test, watch it fail, then implement. No test touches the network.
- Every shell command that mentions `.env` is blocked by a guard. Nothing in this phase needs keys; do not create, read or mention that file.
- **One fly process at a time.** A brain needs about 1 GB on this 8 GB Mac. Never run two of: `pytest -m slow`, `python -m bakeoff.fly.surface`, `python -m bakeoff run --players fly...`. Never run the slow tests in parallel (`-n`).
- Fast loop: `uv run pytest -q -m "not slow"` (about 2 s). Slow tests: `uv run pytest -q -m slow` (about 1 minute; the first ever run compiles for a few minutes more). Slow tests are skipped automatically when `data/` is absent.
- **Honesty rule:** the fly is untrained, innate wiring only. The network is built by the authors' own `create_model` with their `default_params`. Anything that is ours rather than the fly's biology says so in a comment and in the generated calibration report: the looming weighting, the 25 Hz input steps, the two thresholds, the input mechanics (one `PoissonGroup`).
- **Seed hygiene:** practice seeds are 1000–1199, held-out seeds 1200–1399. Tournament seeds will be below 1000. No fly run on a seed below 1000 may happen before the calibrated constants are committed (Task 9).
- Fly model constants, verbatim from the spec: FlyWire **v783**, 138,639 neurons; inputs LPLC2 **108 L / 102 R** and LC4 **54 L / 50 R**; read-outs DNa01, DNb01 (steering) and DNp01 (Giant Fiber), one neuron per side each; **100 ms** window; looming rates **0–250 Hz**; turn signal = (DNa01 + DNb01, right) − (DNa01 + DNb01, left); jump signal = Giant Fiber mean over both sides; jump wins over a turn.
- Every code block below was run in a prototype and passes as written (final state: 135 fast tests, 7 slow). If a test fails, suspect a transcription slip before redesigning. Do not change game constants or anything in `bakeoff/game/`.
- Commit after every task with the message given. End each commit message with the two attribution lines the session provides, as literal text (do not substitute your own model name); commit with `git commit -F <file>` or a heredoc and check `git log -1 --format=%B` afterwards.

## Decisions this plan makes beyond the spec

1. **Looming input comes in 25 Hz steps.** Each eye's sum is capped at 250 Hz and rounded to the nearest 25 Hz, so an eye has 11 levels and the brain has 11 × 11 = 121 possible inputs. One spike in a 100 ms window is already 10 Hz of read-out, so little is lost, and it lets the response surface cover *every* input the fly can receive instead of interpolating. Ours, labelled as such.
2. **The weighting family** is `gain_hz / row ** falloff` per visible gap (own-lane gaps to both eyes, as the spec says). Calibration picks `gain_hz`, `falloff`, `turn_threshold_hz` and `jump_threshold_hz` together from a fixed grid of 768 candidates.
3. **Calibration uses a measured stand-in, never for scoring.** `python -m bakeoff.fly.surface` runs the real brain on all 121 inputs × 8 noise trials (16 minutes in the prototype) and writes `calibration/response_surface.json`, which is committed. `python -m bakeoff.fly.calibrate` plays the candidates with a `SurrogateBrain` that replays those trials. The rule is fixed beforehand: highest mean rows on practice seeds 1000–1199 wins, ties to grid order; the winner alone then plays held-out seeds 1200–1399 once. The real brain then plays 20 practice seeds as a check (Task 10). All scoreboards use the real brain.
4. **Runs are repeatable.** Input noise is the model's only randomness; each decision seeds Brian2 with `crc32("fly:{seed}:{row}")`. Measured: the same seed reproduces a window spike for spike.
5. **`always_jump` baseline and a `jump_share` report column** (answers the open question in `docs/DECISIONS.md`): always-jump averages 45.5 rows against random's 30.8, and the Giant Fiber fires in every threat trial, so a jump-heavy fly has to be judged against that floor.
6. **The authors' `model.py` is loaded from the pinned clone with `importlib`,** not re-implemented and not put on `sys.path`. Only the input mechanics are ours (validated in the spike against the authors' `poi()`).
7. **DNa02 is read and logged but never decides** (the spec notes it is left-biased and inversely graded; the viewer will want to show it). Spike *times* of the read-out neurons are logged too, so phase 4 can draw them firing.
8. **`Decision.latency_ms` stays `None` for the fly** (the report counts steps with a latency as paid requests); the window's wall time goes to `info["wall_ms"]`.
9. **A simulator failure is not a fallback.** Exceptions from the brain propagate; the run ends `interrupted` and its rows show as `incomplete`. Falling back to `stay` would quietly change the fly's score.
10. **Data is pinned:** model repo commit `91bdd1e7dcf193f3e7ca5a8933497fcef63b7960`, annotations commit `17fc57722002e1a7d38cdd0c89ac382bf92718da`, and a sha256 for each of the four files the brain reads. The copy already in `data/` on the user's machine matches all of them.
11. `schema_version` stays 1: `meta.json` only gains keys (`fly`, `game.looming.falloff`, `game.looming.step_hz`).

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `pyproject.toml`, `uv.lock` | New dependencies | 1 |
| `bakeoff/fly/__init__.py` | Empty package marker | 1 |
| `bakeoff/fly/data.py` | Paths, pinned commits, sha256 list, `problems()`, `data_available()`; no heavy imports | 1 |
| `scripts/__init__.py`, `scripts/fetch_fly_data.py` | Clone the model at its pinned commit, download the annotations, verify hashes | 1 |
| `tests/conftest.py` | Skip `slow` tests when the data is absent | 1 |
| `bakeoff/fly/neurons.py` | `select_neurons`, `load_selection`, `Selection` with coverage | 2 |
| `bakeoff/players/always_jump.py`, `bakeoff/report.py` | Second floor; `jump_share` column | 3 |
| `bakeoff/senses.py` | Looming weighting family and 25 Hz steps | 4 |
| `bakeoff/fly/reading.py` | `WINDOW_MS`, `Reading`; no heavy imports | 5 |
| `bakeoff/players/fly.py`, `bakeoff/players/__init__.py`, `bakeoff/runner.py` | Thresholding, lazy brain, `info`; registry; `meta.json` `fly` section | 5 |
| `bakeoff/fly/brain.py` | `Brain`: build once, `window(left_hz, right_hz, noise_seed)`, `close()` | 6 |
| `bakeoff/fly/surface.py`, `calibration/response_surface.json` | Measure the 121-input surface; `SurrogateBrain` | 7 |
| `bakeoff/fly/calibrate.py` | Candidate search on practice seeds; generated report | 8 |
| `calibration/REPORT.md`, constants in `senses.py` and `players/fly.py`, `docs/STEP_RECORD.md` | The fixed numbers and their paper trail | 9 |
| `README.md`, `CLAUDE.md`, `docs/DECISIONS.md` | First scoreboard and status | 10 |

Tests: `tests/test_fly_data.py`, `tests/test_fly_neurons.py`, `tests/test_fly_brain.py` (slow), `tests/test_fly_player.py`, `tests/test_fly_surface.py`, `tests/test_fly_calibrate.py`; edits to `tests/test_players.py`, `tests/test_report.py`, `tests/test_senses.py`, `tests/test_runner.py`.

---

### Task 1: Dependencies, pinned data and the fetch script

**Files:**
- Modify: `pyproject.toml`, `uv.lock` (via `uv add`), `tests/conftest.py`
- Create: `bakeoff/fly/__init__.py` (empty), `bakeoff/fly/data.py`, `scripts/__init__.py` (empty), `scripts/fetch_fly_data.py`
- Test: `tests/test_fly_data.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces (all in `bakeoff.fly.data`): `DATA_DIR`, `MODEL_DIR`, `MODEL_CODE`, `COMPLETENESS`, `CONNECTIVITY`, `ANNOTATIONS` (`Path`s); `MODEL_REPO_URL`, `MODEL_REPO_COMMIT`, `ANNOTATIONS_COMMIT`, `ANNOTATIONS_URL` (`str`); `SHA256: dict[str, str]` keyed by path relative to `data/`; `sha256_of(path) -> str`; `problems(data_dir=DATA_DIR, check_hashes=False, expected=SHA256) -> list[str]`; `data_available(data_dir=DATA_DIR) -> bool`. `scripts.fetch_fly_data.fetch(data_dir, run, download, expected) -> list[str]` and `main() -> int`.

- [ ] **Step 1: Add the dependencies**

Run: `uv add brian2 cython setuptools pandas pyarrow joblib`
Expected: `brian2`, `cython`, `joblib`, `numpy`, `pandas`, `pyarrow`, `setuptools`, `sympy` and a few others are installed. (`joblib` is imported by the authors' `model.py`; `cython` and `setuptools` are what Brian2 compiles with; `pyarrow` reads the connectivity parquet.)

Run: `uv run pytest -q`
Expected: `95 passed`.

- [ ] **Step 2: Write the failing tests**

Create empty files `bakeoff/fly/__init__.py` and `scripts/__init__.py`.

`tests/test_fly_data.py`:

```python
import hashlib

from bakeoff.fly import data
from scripts.fetch_fly_data import fetch

FILES = {"Drosophila_brain_model/model.py": b"model", "neuron_annotations.tsv": b"annotations"}
EXPECTED = {name: hashlib.sha256(content).hexdigest() for name, content in FILES.items()}


def write(data_dir, name):
    path = data_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(FILES[name])


def test_problems_lists_missing_files_and_wrong_hashes(tmp_path):
    assert data.problems(tmp_path, expected=EXPECTED) == [
        f"missing: {tmp_path / name}" for name in EXPECTED]
    for name in FILES:
        write(tmp_path, name)
    assert data.problems(tmp_path, check_hashes=True, expected=EXPECTED) == []
    (tmp_path / "neuron_annotations.tsv").write_bytes(b"tampered")
    assert data.problems(tmp_path, expected=EXPECTED) == []  # presence only
    assert data.problems(tmp_path, check_hashes=True, expected=EXPECTED) == [
        f"wrong sha256: {tmp_path / 'neuron_annotations.tsv'}"]


def test_the_pinned_sources_name_a_commit_not_a_branch():
    assert len(data.MODEL_REPO_COMMIT) == 40 and data.ANNOTATIONS_COMMIT in data.ANNOTATIONS_URL
    assert set(data.SHA256) == {"Drosophila_brain_model/model.py", "Drosophila_brain_model/Completeness_783.csv",
                                "Drosophila_brain_model/Connectivity_783.parquet", "neuron_annotations.tsv"}


def test_fetch_clones_at_the_pinned_commit_and_downloads_the_annotations(tmp_path):
    commands, downloads = [], []

    def run(command, check):
        commands.append(command)
        if command[1] == "clone":
            (tmp_path / "Drosophila_brain_model" / ".git").mkdir(parents=True)
            write(tmp_path, "Drosophila_brain_model/model.py")

    def download(url, target):
        downloads.append(url)
        write(tmp_path, "neuron_annotations.tsv")

    assert fetch(tmp_path, run=run, download=download, expected=EXPECTED) == []
    assert commands == [
        ["git", "clone", data.MODEL_REPO_URL, str(tmp_path / "Drosophila_brain_model")],
        ["git", "-C", str(tmp_path / "Drosophila_brain_model"), "checkout", "--quiet", data.MODEL_REPO_COMMIT]]
    assert downloads == [data.ANNOTATIONS_URL]


def test_fetch_does_nothing_when_the_data_is_already_good(tmp_path):
    for name in FILES:
        write(tmp_path, name)

    def forbidden(*args, **kwargs):
        raise AssertionError("must not touch the network")

    assert fetch(tmp_path, run=forbidden, download=forbidden, expected=EXPECTED) == []


def test_fetch_reports_a_download_that_does_not_match_its_hash(tmp_path):
    write(tmp_path, "Drosophila_brain_model/model.py")
    (tmp_path / "Drosophila_brain_model" / ".git").mkdir()

    def download(url, target):
        target.write_bytes(b"something else")

    remaining = fetch(tmp_path, run=lambda command, check: None, download=download, expected=EXPECTED)
    assert remaining == [f"wrong sha256: {tmp_path / 'neuron_annotations.tsv'}"]
```

- [ ] **Step 3: Run the tests to see them fail**

Run: `uv run pytest -q tests/test_fly_data.py`
Expected: collection error, `ModuleNotFoundError: No module named 'bakeoff.fly.data'`.

- [ ] **Step 4: Write `bakeoff/fly/data.py`**

```python
"""Where the fly data lives and exactly which upstream versions it is. No heavy imports."""

from __future__ import annotations

import hashlib
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MODEL_DIR = DATA_DIR / "Drosophila_brain_model"
MODEL_REPO_URL = "https://github.com/philshiu/Drosophila_brain_model.git"
MODEL_REPO_COMMIT = "91bdd1e7dcf193f3e7ca5a8933497fcef63b7960"  # 2024-09-14, FlyWire v783 files
ANNOTATIONS_COMMIT = "17fc57722002e1a7d38cdd0c89ac382bf92718da"  # 2026-05-04
ANNOTATIONS_URL = ("https://raw.githubusercontent.com/flyconnectome/flywire_annotations/"
                   f"{ANNOTATIONS_COMMIT}/supplemental_files/Supplemental_file1_neuron_annotations.tsv")

MODEL_CODE = MODEL_DIR / "model.py"
COMPLETENESS = MODEL_DIR / "Completeness_783.csv"
CONNECTIVITY = MODEL_DIR / "Connectivity_783.parquet"
ANNOTATIONS = DATA_DIR / "neuron_annotations.tsv"

SHA256 = {
    "Drosophila_brain_model/model.py": "fc45837d7122c6ce2a7f3f2f23c515992e4b232aadb919efabb72337fac88e4e",
    "Drosophila_brain_model/Completeness_783.csv": "bbb847a4cc2caaa7a16349722d220c087317b946d148d4d592d94d250617a311",
    "Drosophila_brain_model/Connectivity_783.parquet": "efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347",
    "neuron_annotations.tsv": "9a4f8b2f843196074431ebd7cd883536afa1be86c8a4ce90970441e8be81d1be",
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def problems(data_dir: Path = DATA_DIR, check_hashes: bool = False,
             expected: dict[str, str] = SHA256) -> list[str]:
    """Why the data cannot be used, one line per file; empty when all is well."""
    found = []
    for relative, sha256 in expected.items():
        path = data_dir / relative
        if not path.is_file():
            found.append(f"missing: {path}")
        elif check_hashes and sha256_of(path) != sha256:
            found.append(f"wrong sha256: {path}")
    return found


def data_available(data_dir: Path = DATA_DIR) -> bool:
    return not problems(data_dir)
```

- [ ] **Step 5: Write `scripts/fetch_fly_data.py`**

It is run as a module (`-m`) so that `bakeoff` is importable from the repo root.

```python
"""Download the fly model and the FlyWire annotations into the git-ignored data/ directory.

    uv run python -m scripts.fetch_fly_data

About 400 MB. Both sources are pinned to a commit and every file the brain uses is checked
against a recorded sha256, so everybody simulates exactly the same fly.
"""

from __future__ import annotations

import subprocess
import sys
import urllib.request
from pathlib import Path

from bakeoff.fly import data


def fetch(data_dir: Path = data.DATA_DIR, run=subprocess.run, download=urllib.request.urlretrieve,
          expected: dict[str, str] = data.SHA256) -> list[str]:
    """Fetch whatever is missing; return the problems that remain (empty list = ready)."""
    if not data.problems(data_dir, check_hashes=True, expected=expected):
        return []
    data_dir.mkdir(parents=True, exist_ok=True)
    model_dir = data_dir / data.MODEL_DIR.name
    if not (model_dir / ".git").is_dir():
        run(["git", "clone", data.MODEL_REPO_URL, str(model_dir)], check=True)
    run(["git", "-C", str(model_dir), "checkout", "--quiet", data.MODEL_REPO_COMMIT], check=True)
    annotations = data_dir / data.ANNOTATIONS.name
    if not annotations.is_file():
        download(data.ANNOTATIONS_URL, annotations)
    return data.problems(data_dir, check_hashes=True, expected=expected)


def main() -> int:
    remaining = fetch()
    for line in remaining:
        print(line, file=sys.stderr)
    print("fly data: " + ("NOT ready" if remaining else f"ready in {data.DATA_DIR}"))
    return 1 if remaining else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Skip `slow` tests when the data is absent**

Append to `tests/conftest.py`:

```python


def pytest_collection_modifyitems(config, items):
    """`slow` tests run the real fly brain; they are skipped when its data has not been fetched."""
    from bakeoff.fly.data import data_available

    if data_available():
        return
    skip = pytest.mark.skip(reason="fly data absent: uv run python -m scripts.fetch_fly_data")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)
```

- [ ] **Step 7: Run the tests**

Run: `uv run pytest -q`
Expected: `100 passed`.

- [ ] **Step 8: Check the real data against the pins**

Run: `uv run python -m scripts.fetch_fly_data`
Expected on the user's machine, where `data/` already exists (takes a second, downloads nothing): `fly data: ready in .../data`. On a machine without the data it clones about 370 MB and downloads 32 MB first. If it prints `wrong sha256`, stop and report: the pins in `data.py` are the contract.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock bakeoff/fly/__init__.py bakeoff/fly/data.py scripts/__init__.py scripts/fetch_fly_data.py tests/conftest.py tests/test_fly_data.py
git commit -m "feat: pinned fly data, fetch script and simulation dependencies"
```

---

### Task 2: Neuron selection

**Files:**
- Create: `bakeoff/fly/neurons.py`
- Test: `tests/test_fly_neurons.py`

**Interfaces:**
- Consumes: `bakeoff.fly.data.ANNOTATIONS`, `bakeoff.fly.data.COMPLETENESS` (slow test only).
- Produces: `SIDES = ("left", "right")`, `INPUT_TYPES = ("LPLC2", "LC4")`, `READOUT_TYPES = ("DNa01", "DNb01", "DNp01")`, `LOGGED_ONLY_TYPES = ("DNa02",)`; `Selection` (frozen dataclass: `inputs: dict[side, tuple[int, ...]]`, `readouts: dict["<type>_<side>", tuple[int, ...]]`, `coverage: dict["<type>_<side>", {"annotated": int, "in_model": int}]`); `select_neurons(annotations: pd.DataFrame, model_ids: Sequence[int]) -> Selection`; `load_selection(annotations_path, completeness_path) -> Selection`. A neuron's *model index* is its row position in `Completeness_783.csv`; that is the index Brian2 uses.

- [ ] **Step 1: Write the failing tests**

`tests/test_fly_neurons.py`:

```python
import pandas as pd
import pytest

from bakeoff.fly import data
from bakeoff.fly.neurons import load_selection, select_neurons

TYPES = ("LPLC2", "LC4", "DNa01", "DNb01", "DNp01", "DNa02")


def annotations(extra=()):
    rows = [(100 + 10 * t + s, cell_type, side)
            for t, cell_type in enumerate(TYPES) for s, side in enumerate(("left", "right"))]
    return pd.DataFrame(list(rows) + list(extra), columns=["root_id", "cell_type", "side"])


def test_a_neurons_model_index_is_its_position_in_the_model_id_list():
    model_ids = [999] + [int(r) for r in annotations()["root_id"]]  # 999 shifts every index by one
    selection = select_neurons(annotations(), model_ids)
    assert selection.inputs == {"left": (1, 3), "right": (2, 4)}  # LPLC2 then LC4 of that eye
    assert selection.readouts["DNa01_left"] == (5,) and selection.readouts["DNp01_right"] == (10,)
    assert set(selection.readouts) == {f"{t}_{s}" for t in TYPES[2:] for s in ("left", "right")}


def test_an_annotated_cell_that_the_model_lacks_is_counted_but_not_used():
    extra = [(777, "LC4", "left")]
    model_ids = [int(r) for r in annotations()["root_id"]]
    selection = select_neurons(annotations(extra), model_ids)
    assert selection.coverage["LC4_left"] == {"annotated": 2, "in_model": 1}
    assert selection.coverage["LPLC2_right"] == {"annotated": 1, "in_model": 1}
    assert len(selection.inputs["left"]) == 2


def test_other_cell_types_and_center_cells_are_ignored():
    extra = [(778, "LC6", "left"), (779, "LC4", "center")]
    model_ids = [int(r) for r in annotations(extra)["root_id"]]
    selection = select_neurons(annotations(extra), model_ids)
    assert len(selection.inputs["left"]) == len(selection.inputs["right"]) == 2


def test_a_group_with_no_neuron_in_the_model_is_an_error():
    model_ids = [int(r) for r in annotations()["root_id"] if r != 120]  # 120 is the left DNa01
    with pytest.raises(ValueError, match="no left DNa01 neuron is in the model"):
        select_neurons(annotations(), model_ids)


@pytest.mark.slow
def test_the_real_data_has_the_cell_counts_the_spec_quotes():
    selection = load_selection(data.ANNOTATIONS, data.COMPLETENESS)
    in_model = {name: c["in_model"] for name, c in selection.coverage.items()}
    assert in_model == {"LPLC2_left": 108, "LPLC2_right": 102, "LC4_left": 54, "LC4_right": 50,
                        **{f"{t}_{s}": 1 for t in TYPES[2:] for s in ("left", "right")}}
    assert all(c["annotated"] == c["in_model"] for c in selection.coverage.values())
    assert len(selection.inputs["left"]) == 162 and len(selection.inputs["right"]) == 152
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest -q tests/test_fly_neurons.py`
Expected: collection error, `ModuleNotFoundError: No module named 'bakeoff.fly.neurons'`.

- [ ] **Step 3: Write `bakeoff/fly/neurons.py`**

```python
"""Pick the fly's input and read-out neurons by cell type and side from the FlyWire annotations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

SIDES = ("left", "right")
INPUT_TYPES = ("LPLC2", "LC4")  # looming detectors of each eye
READOUT_TYPES = ("DNa01", "DNb01", "DNp01")  # steering, steering, Giant Fiber: these decide
LOGGED_ONLY_TYPES = ("DNa02",)  # shown in the viewer (left-biased, inversely graded); never decides


@dataclass(frozen=True)
class Selection:
    inputs: dict[str, tuple[int, ...]]  # side -> model indices of that eye's LPLC2 + LC4 cells
    readouts: dict[str, tuple[int, ...]]  # "DNa01_left" -> model indices
    coverage: dict[str, dict[str, int]]  # "LPLC2_left" -> {"annotated": 108, "in_model": 108}


def select_neurons(annotations: pd.DataFrame, model_ids: Sequence[int]) -> Selection:
    """`model_ids` are the FlyWire root ids in the model's order: a neuron's model index is its
    position there. A cell that is annotated but absent from the model is counted, not used."""
    index_of = {int(root_id): i for i, root_id in enumerate(model_ids)}
    coverage: dict[str, dict[str, int]] = {}

    def indices(cell_type: str, side: str) -> tuple[int, ...]:
        rows = annotations[(annotations["cell_type"] == cell_type) & (annotations["side"] == side)]
        found = tuple(sorted(index_of[int(r)] for r in rows["root_id"] if int(r) in index_of))
        coverage[f"{cell_type}_{side}"] = {"annotated": len(rows), "in_model": len(found)}
        if not found:
            raise ValueError(f"no {side} {cell_type} neuron is in the model")
        return found

    inputs = {side: tuple(i for t in INPUT_TYPES for i in indices(t, side)) for side in SIDES}
    readouts = {f"{t}_{side}": indices(t, side) for t in READOUT_TYPES + LOGGED_ONLY_TYPES for side in SIDES}
    return Selection(inputs=inputs, readouts=readouts, coverage=coverage)


def load_selection(annotations_path: Path, completeness_path: Path) -> Selection:
    annotations = pd.read_csv(annotations_path, sep="\t", usecols=["root_id", "cell_type", "side"])
    model_ids = pd.read_csv(completeness_path, index_col=0).index
    return select_neurons(annotations, model_ids)
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -q tests/test_fly_neurons.py`
Expected: `5 passed` (the slow one reads the 32 MB annotations file, about 1 s; it is skipped without `data/`).

- [ ] **Step 5: Commit**

```bash
git add bakeoff/fly/neurons.py tests/test_fly_neurons.py
git commit -m "feat: select the fly's input and read-out neurons by cell type and side"
```

---

### Task 3: `always_jump` baseline and the `jump_share` column

**Files:**
- Create: `bakeoff/players/always_jump.py`
- Modify: `bakeoff/players/__init__.py`, `bakeoff/report.py`
- Test: `tests/test_players.py`, `tests/test_report.py`

**Interfaces:**
- Consumes: `Decision`, `Game`, `REGISTRY`, `make_player`; `report.summarize`, `report.COLUMNS`.
- Produces: `AlwaysJumpPlayer` (`name = "always_jump"`), registered as `"always_jump"`; report column `jump_share` (share of *executed* actions that are `jump`, `None` without steps) placed right after `dodged_into_gap`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_players.py` replace the body of `test_factory_knows_the_baselines_and_rejects_unknown_names` down to (not including) the `with pytest.raises` line:

```python
def test_factory_knows_the_baselines_and_rejects_unknown_names():
    assert set(REGISTRY) == {"random", "always_jump", "solver"}
    assert all(make_player(name).name == name for name in REGISTRY)
    with pytest.raises(KeyError, match="unknown player 'nope'"):
        make_player("nope")
```

and add, just above `test_solver_runs_straight_on_open_floor`:

```python
def test_always_jump_is_the_floor_for_a_jump_heavy_player():
    # Measured over seeds 0-199: always-jump averages 45.5 rows, random 30.8.
    jump_rows = [play(generate_track(seed), make_player("always_jump"), seed).rows_survived for seed in range(50)]
    random_rows = [play(generate_track(seed), make_player("random"), seed).rows_survived for seed in range(50)]
    assert sum(jump_rows) > sum(random_rows)
    assert max(jump_rows) < 300
```

In `tests/test_report.py` add, just above `test_invalid_rate_and_fallback_rate`:

```python
def test_jump_share_is_the_share_of_executed_jumps():
    steps = [step(chosen="jump"), step(row=2, chosen="jump", executed="stay", gated=True),
             step(row=3, chosen="left"), step(row=4, chosen="jump", alive=False, death_cause="jumped_into_gap")]
    (row,) = summarize(steps)
    assert row["jump_share"] == 0.5
    assert COLUMNS[COLUMNS.index("dodged_into_gap") + 1] == "jump_share"
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest -q tests/test_players.py tests/test_report.py`
Expected: 3 failures (`always_jump` missing from the registry twice, `KeyError: 'jump_share'`).

- [ ] **Step 3: Write `bakeoff/players/always_jump.py`**

```python
"""Second floor: a jump lands on only every other row, so always jumping outlives `random`.
A jump-heavy fly has to beat this, not just `random`."""

from __future__ import annotations

from bakeoff.game.engine import Game
from bakeoff.players.base import Decision


class AlwaysJumpPlayer:
    name = "always_jump"

    def reset(self, game: Game, seed: int) -> None:
        pass

    def act(self, senses: dict) -> Decision:
        return Decision("jump")

    def observe(self, executed_action: str) -> None:
        pass
```

- [ ] **Step 4: Register it**

In `bakeoff/players/__init__.py` add the import `from bakeoff.players.always_jump import AlwaysJumpPlayer` (first of the `bakeoff.players` imports, to keep them sorted) and replace the `REGISTRY` line with:

```python
REGISTRY: dict[str, Callable[..., Player]] = {
    "random": RandomPlayer, "always_jump": AlwaysJumpPlayer, "solver": SolverPlayer}
```

- [ ] **Step 5: Add the report column**

In `bakeoff/report.py`, in `COLUMNS` change

```python
           "ran_into_gap", "jumped_into_gap", "dodged_into_gap", "solver_agreement",
```

to

```python
           "ran_into_gap", "jumped_into_gap", "dodged_into_gap", "jump_share", "solver_agreement",
```

and in the dict returned by `_summarize_player` add this line directly above the `"solver_agreement": ...` line:

```python
        "jump_share": _ratio(sum(s["executed_action"] == "jump" for s in steps), len(steps)),
```

- [ ] **Step 6: Run the tests**

Run: `uv run pytest -q -m "not slow"`
Expected: `106 passed, 1 deselected`.

- [ ] **Step 7: Commit**

```bash
git add bakeoff/players/always_jump.py bakeoff/players/__init__.py bakeoff/report.py tests/test_players.py tests/test_report.py
git commit -m "feat: always_jump baseline and jump_share report column"
```

---

### Task 4: Looming weighting family in 25 Hz steps

**Files:**
- Modify: `bakeoff/senses.py`, `bakeoff/runner.py`, `docs/STEP_RECORD.md`
- Test: `tests/test_senses.py`, `tests/test_runner.py`

**Interfaces:**
- Consumes: the existing `compute_senses` output (`senses["ahead"]`).
- Produces: `LOOMING_GAIN_HZ = 100.0`, `LOOMING_FALLOFF = 1.0` (both provisional until Task 9), `LOOMING_STEP_HZ = 25.0`, `MAX_HZ = 250.0`; `looming_rates(senses, gain_hz=LOOMING_GAIN_HZ, falloff=LOOMING_FALLOFF) -> tuple[float, float]`, each value a multiple of 25.0 in 0.0–250.0. `meta.json` `game.looming` gains `falloff` and `step_hz`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_senses.py` change the import line to

```python
from bakeoff.senses import LOOMING_STEP_HZ, MAX_HZ, compute_senses, ground_truth, looming_rates
```

and replace `test_nearer_gaps_loom_larger` with these four tests (they pass the weighting explicitly, so they keep passing when Task 9 changes the defaults):

```python
def test_nearer_gaps_loom_larger(make_track):
    near, _ = looming_rates(compute_senses(Game(make_track({1: [5]}))), gain_hz=100.0, falloff=1.0)
    far, _ = looming_rates(compute_senses(Game(make_track({4: [5]}))), gain_hz=100.0, falloff=1.0)
    assert (near, far) == (100.0, 25.0)


def test_falloff_is_the_power_of_the_distance(make_track):
    senses = compute_senses(Game(make_track({2: [5]})))
    assert looming_rates(senses, gain_hz=200.0, falloff=1.0) == (100.0, 0.0)
    assert looming_rates(senses, gain_hz=200.0, falloff=2.0) == (50.0, 0.0)
    assert looming_rates(senses, gain_hz=200.0, falloff=3.0) == (25.0, 0.0)


def test_gaps_in_one_eye_add_up(make_track):
    senses = compute_senses(Game(make_track({1: [4, 5], 2: [7]})))
    assert looming_rates(senses, gain_hz=100.0, falloff=1.0) == (200.0, 50.0)


def test_rates_are_rounded_to_the_nearest_input_level(make_track):
    assert LOOMING_STEP_HZ == 25.0
    senses = compute_senses(Game(make_track({3: [5], 6: [7]})))
    assert looming_rates(senses, gain_hz=100.0, falloff=1.0) == (25.0, 25.0)  # 33.3 and 16.7
    assert looming_rates(senses, gain_hz=70.0, falloff=1.0) == (25.0, 0.0)  # 23.3 and 11.7
    assert looming_rates(senses, gain_hz=112.5, falloff=1.0) == (50.0, 25.0)  # 37.5 rounds up, 18.75 up
```

In `tests/test_runner.py`, in `test_run_writes_one_jsonl_per_player_and_meta`, replace the `"looming": {...}` line of the `meta["game"]` assertion with:

```python
                            "looming": {"gain_hz": 100.0, "falloff": 1.0, "step_hz": 25.0, "max_hz": 250.0,
                                        "provisional": True}}
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest -q tests/test_senses.py tests/test_runner.py`
Expected: `ImportError: cannot import name 'LOOMING_STEP_HZ'` for the senses file and one failure in the runner file.

- [ ] **Step 3: Rewrite `bakeoff/senses.py`**

The whole file (only the constants block, `_to_level` and `looming_rates` change):

```python
"""Engine state -> JSON senses and -> looming rates. One source of truth, two encodings. Pure."""

from __future__ import annotations

import math

from bakeoff.game.engine import Game
from bakeoff.game.track import LOOKAHEAD

WINDOW = 3  # gaps are visible up to this many lanes either side of the runner
MAX_HZ = 250.0
# OURS, not the fly's biology: a gap `row` rows ahead adds LOOMING_GAIN_HZ / row ** LOOMING_FALLOFF
# to its eye; each eye's sum is capped at MAX_HZ and rounded to the nearest LOOMING_STEP_HZ, so
# an eye has 11 input levels and the measured response surface covers every input the fly can get.
# PROVISIONAL until the calibration task fixes gain and falloff on practice seeds.
LOOMING_GAIN_HZ = 100.0
LOOMING_FALLOFF = 1.0
LOOMING_STEP_HZ = 25.0
ACTION_DESCRIPTIONS = {
    "left": "move one lane left", "right": "move one lane right",
    "jump": "clear the next row, land on the one after", "stay": "run straight",
}


def compute_senses(game: Game) -> dict:
    ahead = []
    for distance in range(1, LOOKAHEAD + 1):
        offsets = [o for o in range(-WINDOW, WINDOW + 1) if game.track.is_gap(game.row + distance, game.lane + o)]
        ahead.append({"row": distance, "gaps_relative": offsets})
    return {"lane": game.lane, "lanes": game.track.lanes, "rows_survived": game.rows_survived,
            "ahead": ahead, "actions": dict(ACTION_DESCRIPTIONS)}


def _to_level(hz: float) -> float:
    return math.floor(min(hz, MAX_HZ) / LOOMING_STEP_HZ + 0.5) * LOOMING_STEP_HZ


def looming_rates(senses: dict, gain_hz: float = LOOMING_GAIN_HZ,
                  falloff: float = LOOMING_FALLOFF) -> tuple[float, float]:
    left = right = 0.0
    for entry in senses["ahead"]:
        intensity = gain_hz / entry["row"] ** falloff
        for offset in entry["gaps_relative"]:
            if offset <= 0:
                left += intensity
            if offset >= 0:
                right += intensity
    return _to_level(left), _to_level(right)


def ground_truth(game: Game) -> dict:
    return {"gap_ahead": game.track.is_gap(game.row + 1, game.lane),
            "left_safe": not game.track.is_gap(game.row + 1, game.lane - 1)}
```

`math.floor(x + 0.5)` rounds halves up; Python's `round()` rounds halves to even, which would make 37.5 Hz and 62.5 Hz behave differently.

- [ ] **Step 4: Record the weighting in `meta.json`**

In `bakeoff/runner.py` replace the `from bakeoff.senses import ...` line with

```python
from bakeoff.senses import (LOOMING_FALLOFF, LOOMING_GAIN_HZ, LOOMING_STEP_HZ, MAX_HZ, WINDOW, compute_senses,
                            ground_truth, looming_rates)
```

and the `"looming": {...}` line inside `meta["game"]` with

```python
                     "looming": {"gain_hz": LOOMING_GAIN_HZ, "falloff": LOOMING_FALLOFF, "step_hz": LOOMING_STEP_HZ,
                                 "max_hz": MAX_HZ, "provisional": True}},
```

- [ ] **Step 5: Update `docs/STEP_RECORD.md`**

Replace the `looming` row of the step record table with:

```markdown
| `looming` | `{left_hz, right_hz}` | floats, the fly's eye rates for these senses: each visible gap adds `gain_hz / row ** falloff` to its eye (own lane: both eyes), the sum is capped at `max_hz` and rounded to the nearest `step_hz` (so 11 levels, 0 to 250). Ours, not the fly's biology |
```

and the `game` row of the `meta.json` table with:

```markdown
| `game` | object | `lanes`, `max_rows`, `lookahead`, `window` (visible lanes each side), `looming: {gain_hz, falloff, step_hz, max_hz, provisional}` |
```

- [ ] **Step 6: Run the tests**

Run: `uv run pytest -q -m "not slow"`
Expected: `109 passed, 1 deselected`.

- [ ] **Step 7: Commit**

```bash
git add bakeoff/senses.py bakeoff/runner.py docs/STEP_RECORD.md tests/test_senses.py tests/test_runner.py
git commit -m "feat: looming weighting family (gain, falloff) in 25 Hz input steps"
```

---

### Task 5: The fly player

**Files:**
- Create: `bakeoff/fly/reading.py`, `bakeoff/players/fly.py`
- Modify: `bakeoff/players/__init__.py`, `bakeoff/runner.py`, `docs/STEP_RECORD.md`
- Test: `tests/test_fly_player.py`, `tests/test_players.py`, `tests/test_runner.py`

**Interfaces:**
- Consumes: `looming_rates(senses, gain_hz, falloff)`, `LOOMING_GAIN_HZ`, `LOOMING_FALLOFF` (Task 4); `Decision`; `bakeoff.fly.data.MODEL_REPO_COMMIT`, `ANNOTATIONS_COMMIT` (Task 1). A *brain* is anything with `window(left_hz: float, right_hz: float, noise_seed: int | None) -> Reading` and `close()`; the real one arrives in Task 6 as `bakeoff.fly.brain.Brain` and is imported lazily.
- Produces:
  - `bakeoff.fly.reading`: `WINDOW_MS = 100.0`; `Reading` (frozen dataclass: `rates_hz: dict[str, float]`, `spike_counts: dict[str, int]`, `spike_times_ms: dict[str, list[float]]`, `total_spikes: int`, `wall_ms: float`), dict keys `"<type>_<side>"` for DNa01, DNb01, DNp01, DNa02.
  - `bakeoff.players.fly`: `TURN_THRESHOLD_HZ = 20.0`, `JUMP_THRESHOLD_HZ = 150.0`, `CALIBRATED = False` (all provisional until Task 9); `turn_signal_hz(rates_hz) -> float`; `jump_signal_hz(rates_hz) -> float`; `choose(rates_hz, turn_threshold_hz, jump_threshold_hz) -> str`; `noise_seed(seed: int, row: int) -> int`; `FlyPlayer(brain_factory=_real_brain, turn_threshold_hz=..., jump_threshold_hz=..., gain_hz=..., falloff=...)` with `name = "fly"`, `reset`, `act`, `observe`, `close`.
  - `meta.json` gains `fly`; `game.looming.provisional` and `fly.provisional` are `not CALIBRATED`.

- [ ] **Step 1: Write the failing tests**

`tests/test_fly_player.py`:

```python
import subprocess
import sys
from pathlib import Path

import pytest

from bakeoff.fly.reading import Reading
from bakeoff.game.engine import Game
from bakeoff.players.fly import FlyPlayer, choose, jump_signal_hz, noise_seed, turn_signal_hz
from bakeoff.senses import compute_senses

QUIET = {"DNa01_left": 0.0, "DNa01_right": 0.0, "DNb01_left": 0.0, "DNb01_right": 0.0,
         "DNp01_left": 0.0, "DNp01_right": 0.0, "DNa02_left": 0.0, "DNa02_right": 0.0}


def rates(**changed):
    return {**QUIET, **changed}


class FakeBrain:
    def __init__(self, rates_hz=QUIET):
        self.rates_hz, self.calls, self.closed = rates_hz, [], False

    def window(self, left_hz, right_hz, noise_seed=None):
        self.calls.append((left_hz, right_hz, noise_seed))
        return Reading(rates_hz=self.rates_hz, spike_counts={k: int(v / 10) for k, v in self.rates_hz.items()},
                       spike_times_ms={k: [] for k in self.rates_hz}, total_spikes=7, wall_ms=1.5)

    def close(self):
        self.closed = True


def test_turn_signal_is_right_steering_minus_left_steering():
    assert turn_signal_hz(rates(DNa01_right=40.0, DNb01_right=50.0)) == 90.0
    assert turn_signal_hz(rates(DNa01_left=30.0, DNb01_left=30.0, DNb01_right=10.0)) == -50.0
    assert turn_signal_hz(rates(DNa02_left=200.0)) == 0.0  # DNa02 is logged, never used


def test_jump_signal_is_the_giant_fiber_mean_over_both_sides():
    assert jump_signal_hz(rates(DNp01_left=170.0, DNp01_right=100.0)) == 135.0


@pytest.mark.parametrize("changed, action", [
    ({}, "stay"),
    ({"DNa01_right": 30.0}, "right"),
    ({"DNb01_left": 30.0}, "left"),
    ({"DNa01_right": 20.0}, "stay"),  # the threshold itself is not enough
    ({"DNa01_left": 20.0}, "stay"),
    ({"DNp01_left": 160.0, "DNp01_right": 160.0}, "jump"),
    ({"DNp01_left": 150.0, "DNp01_right": 150.0}, "stay"),
    ({"DNp01_left": 200.0, "DNp01_right": 200.0, "DNa01_right": 90.0}, "jump"),  # jump wins over a turn
])
def test_choose_applies_the_two_thresholds(changed, action):
    assert choose(rates(**changed), turn_threshold_hz=20.0, jump_threshold_hz=150.0) == action


def test_noise_seed_depends_on_track_seed_and_row_and_is_stable_across_processes():
    assert noise_seed(3, 7) == noise_seed(3, 7) == 3662795588
    assert len({noise_seed(s, r) for s in range(5) for r in range(5)}) == 25


def test_listing_the_players_does_not_import_the_simulator():
    # In a fresh interpreter: the slow tests may already have imported brian2 into this one.
    code = ("import sys, bakeoff.__main__; from bakeoff.players import make_player; make_player('fly'); "
            "assert not {'brian2', 'pandas', 'numpy'} & set(sys.modules)")
    subprocess.run([sys.executable, "-c", code], check=True, cwd=Path(__file__).resolve().parents[1])


def test_the_brain_is_built_on_the_first_reset_and_only_once(make_track):
    built = []
    player = FlyPlayer(brain_factory=lambda: built.append(FakeBrain()) or built[-1])
    assert built == []
    player.reset(Game(make_track({})), 0)
    player.reset(Game(make_track({})), 1)
    assert len(built) == 1


def test_act_feeds_the_looming_rates_to_the_brain_and_logs_what_it_read(make_track):
    brain = FakeBrain(rates(DNa01_right=40.0, DNb01_right=50.0, DNp01_left=100.0))
    player = FlyPlayer(brain_factory=lambda: brain, turn_threshold_hz=20.0, jump_threshold_hz=150.0,
                       gain_hz=100.0, falloff=1.0)
    game = Game(make_track({1: [5]}))  # one gap, next row, one lane to the left
    player.reset(game, 3)
    decision = player.act(compute_senses(game))
    assert brain.calls == [(100.0, 0.0, noise_seed(3, 0))]
    assert decision.chosen_action == "right" and not decision.needs_fallback
    assert decision.latency_ms is None  # not an API call: the report must not count it as a request
    assert decision.info == {
        "left_hz": 100.0, "right_hz": 0.0, "noise_seed": noise_seed(3, 0),
        "rates_hz": brain.rates_hz, "spike_counts": {k: int(v / 10) for k, v in brain.rates_hz.items()},
        "spike_times_ms": {k: [] for k in brain.rates_hz}, "total_spikes": 7,
        "turn_signal_hz": 90.0, "jump_signal_hz": 50.0,
        "turn_threshold_hz": 20.0, "jump_threshold_hz": 150.0, "wall_ms": 1.5}


def test_the_noise_seed_follows_the_row(make_track):
    brain = FakeBrain()
    player = FlyPlayer(brain_factory=lambda: brain)
    game = Game(make_track({}))
    player.reset(game, 9)
    player.act(compute_senses(game))
    game.step("stay")
    player.act(compute_senses(game))
    assert [call[2] for call in brain.calls] == [noise_seed(9, 0), noise_seed(9, 1)]


def test_close_releases_the_brain_and_is_safe_to_repeat(make_track):
    brain = FakeBrain()
    player = FlyPlayer(brain_factory=lambda: brain)
    player.close()  # never built: nothing to do
    player.reset(Game(make_track({})), 0)
    player.close()
    player.close()
    assert brain.closed
```

In `tests/test_players.py` change the registry assertion to:

```python
    assert set(REGISTRY) == {"random", "always_jump", "solver", "fly"}
```

In `tests/test_runner.py`, in `test_run_writes_one_jsonl_per_player_and_meta`, add directly below the `meta["game"]` assertion:

```python
    assert meta["fly"] == {"turn_threshold_hz": 20.0, "jump_threshold_hz": 150.0, "window_ms": 100.0,
                           "provisional": True, "model_commit": "91bdd1e7dcf193f3e7ca5a8933497fcef63b7960",
                           "annotations_commit": "17fc57722002e1a7d38cdd0c89ac382bf92718da"}
```

and replace the last line of that test with:

```python
    assert "git_sha" in meta and {"anthropic", "brian2", "numpy"} <= set(meta["versions"])
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest -q tests/test_fly_player.py tests/test_players.py tests/test_runner.py`
Expected: collection error for `tests/test_fly_player.py` (`No module named 'bakeoff.fly.reading'`) and one failure in each of the other two files.

- [ ] **Step 3: Write `bakeoff/fly/reading.py`**

```python
"""What one decision window of a brain yields. No heavy imports: the runner and the stand-in use it."""

from __future__ import annotations

from dataclasses import dataclass

WINDOW_MS = 100.0  # simulated time per decision


@dataclass(frozen=True)
class Reading:
    rates_hz: dict[str, float]  # "DNa01_left" -> mean rate per neuron of the group over the window
    spike_counts: dict[str, int]
    spike_times_ms: dict[str, list[float]]  # from the start of the window
    total_spikes: int  # the whole brain
    wall_ms: float
```

- [ ] **Step 4: Write `bakeoff/players/fly.py`**

```python
"""The fly player: looming rates in, the brain's read-out neurons out, two thresholds between."""

from __future__ import annotations

import zlib
from typing import Callable

from bakeoff.game.engine import Game
from bakeoff.players.base import Decision
from bakeoff.senses import LOOMING_FALLOFF, LOOMING_GAIN_HZ, looming_rates

# The fly's only tuning. PROVISIONAL until the calibration task fixes them on practice seeds
# and sets CALIBRATED (which also covers the looming gain and falloff in bakeoff/senses.py).
TURN_THRESHOLD_HZ = 20.0
JUMP_THRESHOLD_HZ = 150.0
CALIBRATED = False


def turn_signal_hz(rates_hz: dict[str, float]) -> float:
    """(DNa01 + DNb01, right) - (DNa01 + DNb01, left). These neurons fire on the side opposite a
    one-sided threat and turn the fly toward the active side, so positive means turn right."""
    return (rates_hz["DNa01_right"] + rates_hz["DNb01_right"]) - (rates_hz["DNa01_left"] + rates_hz["DNb01_left"])


def jump_signal_hz(rates_hz: dict[str, float]) -> float:
    """Giant Fiber (DNp01) mean rate over both sides."""
    return (rates_hz["DNp01_left"] + rates_hz["DNp01_right"]) / 2.0


def choose(rates_hz: dict[str, float], turn_threshold_hz: float, jump_threshold_hz: float) -> str:
    if jump_signal_hz(rates_hz) > jump_threshold_hz:
        return "jump"  # jump wins over a turn
    turn = turn_signal_hz(rates_hz)
    if turn > turn_threshold_hz:
        return "right"
    if turn < -turn_threshold_hz:
        return "left"
    return "stay"


def noise_seed(seed: int, row: int) -> int:
    """Input noise is the model's only randomness; seeding it per decision makes a run repeatable."""
    return zlib.crc32(f"fly:{seed}:{row}".encode())


def _real_brain():
    from bakeoff.fly.brain import Brain  # imports brian2: only when a fly actually plays

    return Brain()


class FlyPlayer:
    name = "fly"

    def __init__(self, brain_factory: Callable[[], object] = _real_brain,
                 turn_threshold_hz: float = TURN_THRESHOLD_HZ, jump_threshold_hz: float = JUMP_THRESHOLD_HZ,
                 gain_hz: float = LOOMING_GAIN_HZ, falloff: float = LOOMING_FALLOFF):
        self._brain_factory = brain_factory
        self._brain = None  # about 1 GB: built on the first reset(), not when the CLI lists players
        self._seed = 0
        self.turn_threshold_hz, self.jump_threshold_hz = turn_threshold_hz, jump_threshold_hz
        self.gain_hz, self.falloff = gain_hz, falloff

    def reset(self, game: Game, seed: int) -> None:
        self._seed = seed
        if self._brain is None:
            self._brain = self._brain_factory()

    def act(self, senses: dict) -> Decision:
        left_hz, right_hz = looming_rates(senses, self.gain_hz, self.falloff)
        seed = noise_seed(self._seed, senses["rows_survived"])
        reading = self._brain.window(left_hz, right_hz, noise_seed=seed)
        action = choose(reading.rates_hz, self.turn_threshold_hz, self.jump_threshold_hz)
        return Decision(action, info={
            "left_hz": left_hz, "right_hz": right_hz, "noise_seed": seed,
            "rates_hz": reading.rates_hz, "spike_counts": reading.spike_counts,
            "spike_times_ms": reading.spike_times_ms, "total_spikes": reading.total_spikes,
            "turn_signal_hz": turn_signal_hz(reading.rates_hz), "jump_signal_hz": jump_signal_hz(reading.rates_hz),
            "turn_threshold_hz": self.turn_threshold_hz, "jump_threshold_hz": self.jump_threshold_hz,
            "wall_ms": reading.wall_ms,
        })

    def observe(self, executed_action: str) -> None:
        pass

    def close(self) -> None:
        if self._brain is not None:
            self._brain.close()
            self._brain = None
```

`senses["rows_survived"]` equals the runner's row at decision time, so the noise seed follows (track seed, row).

- [ ] **Step 5: Register it**

`bakeoff/players/__init__.py`, whole file:

```python
from __future__ import annotations

from typing import Callable

from bakeoff.players.always_jump import AlwaysJumpPlayer
from bakeoff.players.base import Player
from bakeoff.players.fly import FlyPlayer
from bakeoff.players.random_player import RandomPlayer
from bakeoff.players.solver import SolverPlayer

REGISTRY: dict[str, Callable[..., Player]] = {
    "random": RandomPlayer, "always_jump": AlwaysJumpPlayer, "solver": SolverPlayer, "fly": FlyPlayer}


def make_player(name: str, **options) -> Player:
    """Options are passed to the player's constructor (paid players need a client and a cap)."""
    if name not in REGISTRY:
        raise KeyError(f"unknown player {name!r}; choose from {sorted(REGISTRY)}")
    return REGISTRY[name](**options)
```

- [ ] **Step 6: Record the fly's constants in `meta.json`**

In `bakeoff/runner.py` add these imports, keeping the block sorted: the first two directly above `from bakeoff.game.engine import ACTIONS, Game`, the third directly above `from bakeoff.players.base import Player`:

```python
from bakeoff.fly import data as fly_data
from bakeoff.fly.reading import WINDOW_MS
```

```python
from bakeoff.players import fly
```

In `meta`, change `"provisional": True` in the `looming` dict to `"provisional": not fly.CALIBRATED`, add this entry directly below the `"game": {...}` entry:

```python
            "fly": {"turn_threshold_hz": fly.TURN_THRESHOLD_HZ, "jump_threshold_hz": fly.JUMP_THRESHOLD_HZ,
                    "window_ms": WINDOW_MS, "provisional": not fly.CALIBRATED,
                    "model_commit": fly_data.MODEL_REPO_COMMIT, "annotations_commit": fly_data.ANNOTATIONS_COMMIT},
```

and change the `versions` line to:

```python
            "versions": {pkg: _version(pkg) for pkg in ("brian2", "cython", "numpy", "typesafe-sdk", "anthropic")},
```

- [ ] **Step 7: Document the fly's `info` and the new `meta.json` keys**

In `docs/STEP_RECORD.md` add this section directly above `## The landing tile`:

```markdown
### `info` of the fly

One object per decision, everything the viewer needs to draw the fly's "mind". Neuron-group keys
are `<cell type>_<side>`: `DNa01`, `DNb01` (steering), `DNp01` (Giant Fiber) and `DNa02` (logged
only, never decides), each `_left` and `_right`; every group is a single neuron.

| key | type | meaning |
| --- | --- | --- |
| `left_hz`, `right_hz` | float | Poisson rate given to the LPLC2 + LC4 looming detectors of each eye (equals `looming`) |
| `noise_seed` | int | seed of this decision's input noise, `crc32("fly:{seed}:{row}")`; the same seed repeats the window exactly |
| `rates_hz` | object | firing rate of each group over the window |
| `spike_counts` | object | spikes of each group in the window |
| `spike_times_ms` | object | spike times of each group, ms from the start of the window |
| `total_spikes` | int | spikes in the whole brain during the window |
| `turn_signal_hz` | float | (DNa01 + DNb01, right) − (DNa01 + DNb01, left); above `turn_threshold_hz` → `right`, below its negative → `left` |
| `jump_signal_hz` | float | Giant Fiber mean over both sides; above `jump_threshold_hz` → `jump`, which wins over a turn |
| `turn_threshold_hz`, `jump_threshold_hz` | float | the fly's only tuning (ours), as used for this decision |
| `wall_ms` | float | wall-clock time of the simulated window |
```

In the `meta.json` table add this row below the `game` row, and replace the `versions` row:

```markdown
| `fly` | object | `turn_threshold_hz`, `jump_threshold_hz`, `window_ms`, `provisional` (true until calibrated), `model_commit`, `annotations_commit` |
| `versions` | object | `brian2`, `cython`, `numpy`, `typesafe-sdk`, `anthropic` versions or null |
```

- [ ] **Step 8: Run the tests**

Run: `uv run pytest -q -m "not slow"`
Expected: `125 passed, 1 deselected`.

- [ ] **Step 9: Commit**

```bash
git add bakeoff/fly/reading.py bakeoff/players/fly.py bakeoff/players/__init__.py bakeoff/runner.py docs/STEP_RECORD.md tests/test_fly_player.py tests/test_players.py tests/test_runner.py
git commit -m "feat: fly player, two thresholds on the brain's steering and Giant Fiber read-outs"
```

---

### Task 6: The brain wrapper

**Files:**
- Create: `bakeoff/fly/brain.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_fly_brain.py` (all `slow`)

**Interfaces:**
- Consumes: `bakeoff.fly.data` (`problems`, `MODEL_CODE`, `COMPLETENESS`, `CONNECTIVITY`, `ANNOTATIONS`); `bakeoff.fly.neurons` (`SIDES`, `Selection`, `load_selection`); `bakeoff.fly.reading` (`WINDOW_MS`, `Reading`); in the tests `turn_signal_hz`, `jump_signal_hz` from `bakeoff.players.fly`.
- Produces: `bakeoff.fly.brain.Brain(selection=None, window_ms=WINDOW_MS, target="cython")` with `window(left_hz: float, right_hz: float, noise_seed: int | None = None) -> Reading`, `close() -> None`, attributes `selection`, `window_ms`; raises `FileNotFoundError` when the data is missing. A session-scoped pytest fixture `brain` (the real brain) in `tests/conftest.py`.

What the wrapper does, and why: the authors' `create_model` builds the 138,639-neuron network. After a 0.1 ms warm-up run that compiles the code, `store("clean")` snapshots it; every decision `restore`s that snapshot (0.04 s), so no state carries over between decisions, as the spec requires. The authors' `poi()` makes one fixed-rate `PoissonInput` per neuron; one `PoissonGroup` wired one-to-one with the same kick lets the rates change per decision. Measured in the prototype: build about 45 s, then about 0.65 s per window; peak memory about 875 MB.

- [ ] **Step 1: Write the failing tests**

`tests/test_fly_brain.py`:

```python
"""The real brain. Slow (one build of about half a minute, then about 0.7 s per window) and about
1 GB: run with `uv run pytest -m slow`, never while another fly process is running."""

import pytest

from bakeoff.players.fly import jump_signal_hz, turn_signal_hz

pytestmark = pytest.mark.slow  # the `brain` fixture is in conftest.py: one real brain per test session


def test_no_input_means_no_spikes_at_all(brain):
    reading = brain.window(0.0, 0.0, noise_seed=1)
    assert reading.total_spikes == 0 and set(reading.rates_hz.values()) == {0.0}


def test_the_same_noise_seed_repeats_the_window_exactly_and_another_does_not(brain):
    first, again, other = (brain.window(150.0, 0.0, noise_seed=s) for s in (1, 1, 2))
    assert (first.spike_counts, first.spike_times_ms, first.total_spikes) == (
        again.spike_counts, again.spike_times_ms, again.total_spikes)
    assert other.total_spikes != first.total_spikes


def test_a_threat_in_one_eye_fires_the_steering_neurons_of_the_other_side_only(brain):
    left_threat, right_threat = brain.window(150.0, 0.0, noise_seed=1), brain.window(0.0, 150.0, noise_seed=1)
    assert left_threat.spike_counts["DNa01_left"] == left_threat.spike_counts["DNb01_left"] == 0
    assert right_threat.spike_counts["DNa01_right"] == right_threat.spike_counts["DNb01_right"] == 0
    assert turn_signal_hz(left_threat.rates_hz) >= 40.0  # turn right, away from the left threat
    assert turn_signal_hz(right_threat.rates_hz) <= -40.0


def test_the_giant_fiber_is_graded_with_the_threat(brain):
    weak, strong = brain.window(50.0, 50.0, noise_seed=1), brain.window(250.0, 250.0, noise_seed=1)
    assert 0 < jump_signal_hz(weak.rates_hz) < jump_signal_hz(strong.rates_hz)
    assert abs(turn_signal_hz(strong.rates_hz)) <= 40.0  # both eyes: steering roughly cancels


def test_a_reading_names_every_read_out_group_and_times_lie_in_the_window(brain):
    reading = brain.window(150.0, 0.0, noise_seed=1)
    names = {f"{t}_{s}" for t in ("DNa01", "DNb01", "DNp01", "DNa02") for s in ("left", "right")}
    assert set(reading.rates_hz) == set(reading.spike_counts) == set(reading.spike_times_ms) == names
    assert reading.rates_hz["DNp01_left"] == reading.spike_counts["DNp01_left"] * 10.0  # one neuron, 100 ms
    assert all(0.0 <= t <= 100.0 for times in reading.spike_times_ms.values() for t in times)
    assert len(reading.spike_times_ms["DNp01_left"]) == reading.spike_counts["DNp01_left"]
```

Append to `tests/conftest.py`:

```python


@pytest.fixture(scope="session")
def brain():
    """The real fly brain, built once per test session (about 1 GB, half a minute). Slow tests only."""
    from bakeoff.fly.brain import Brain

    brain = Brain()
    yield brain
    brain.close()
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest -q -m slow tests/test_fly_brain.py`
Expected: 5 errors, `ModuleNotFoundError: No module named 'bakeoff.fly.brain'`.

- [ ] **Step 3: Write `bakeoff/fly/brain.py`**

```python
"""The untrained whole-brain model (Shiu et al. 2024): built once, restored before every decision.

The network is built by the authors' own `create_model` with their `default_params`. Ours is only
the input mechanics: one PoissonGroup wired one-to-one onto the looming detectors, with the same
kick (w_syn * f_poi) and zero refractory period that the authors' `poi()` gives stimulated
neurons, so the rates can change between decisions without a rebuild.
"""

from __future__ import annotations

import importlib.util
import time

import numpy as np

from bakeoff.fly import data
from bakeoff.fly.neurons import SIDES, Selection, load_selection
from bakeoff.fly.reading import WINDOW_MS, Reading


def _upstream_model():
    spec = importlib.util.spec_from_file_location("shiu_model", data.MODEL_CODE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Brain:
    def __init__(self, selection: Selection | None = None, window_ms: float = WINDOW_MS, target: str = "cython"):
        found = data.problems()
        if found:
            raise FileNotFoundError("fly data unusable (run `uv run python -m scripts.fetch_fly_data`): "
                                    + "; ".join(found))
        import brian2 as b2

        self._b2 = b2
        b2.prefs.codegen.target = target
        upstream = _upstream_model()
        self.selection = selection or load_selection(data.ANNOTATIONS, data.COMPLETENESS)
        self.window_ms = window_ms
        params = dict(upstream.default_params)
        self._neurons, synapses, self._monitor = upstream.create_model(
            str(data.COMPLETENESS), str(data.CONNECTIVITY), params)
        stimulated = np.array([i for side in SIDES for i in self.selection.inputs[side]], dtype=int)
        self._n_left = len(self.selection.inputs["left"])
        self._poisson = b2.PoissonGroup(len(stimulated), rates=np.zeros(len(stimulated)) * b2.Hz, name="looming")
        kick_mv = float(params["w_syn"] * params["f_poi"] / b2.mV)
        wiring = b2.Synapses(self._poisson, self._neurons, on_pre=f"v_post += {kick_mv!r}*mV", name="looming_wiring")
        wiring.connect(i=np.arange(len(stimulated)), j=stimulated)
        self._neurons.rfc[stimulated] = 0 * b2.ms  # as upstream poi(): no refractory period for Poisson targets
        self._net = b2.Network(self._neurons, synapses, self._monitor, self._poisson, wiring)
        self._net.run(0.1 * b2.ms)  # compiles the code once
        self._net.store("clean")
        self._t0_ms = float(self._net.t / b2.ms)

    def window(self, left_hz: float, right_hz: float, noise_seed: int | None = None) -> Reading:
        b2 = self._b2
        started = time.perf_counter()
        self._net.restore("clean")
        if noise_seed is not None:
            b2.seed(noise_seed)
        hz = np.full(len(self._poisson), float(right_hz))  # not named `rates`: brian2 would warn
        hz[:self._n_left] = float(left_hz)
        self._poisson.rates = hz * b2.Hz
        self._net.run(self.window_ms * b2.ms)
        who = np.asarray(self._monitor.i)
        when_ms = np.asarray(self._monitor.t / b2.ms) - self._t0_ms
        rates_hz, counts, times = {}, {}, {}
        for name, members in self.selection.readouts.items():
            mask = np.isin(who, members)
            counts[name] = int(mask.sum())
            rates_hz[name] = counts[name] / len(members) / (self.window_ms / 1000.0)
            times[name] = [round(float(t), 1) for t in when_ms[mask]]
        return Reading(rates_hz=rates_hz, spike_counts=counts, spike_times_ms=times,
                       total_spikes=int(len(who)), wall_ms=(time.perf_counter() - started) * 1000.0)

    def close(self) -> None:
        self._net = self._neurons = self._monitor = self._poisson = None
```

- [ ] **Step 4: Run the slow tests**

Make sure no other fly process is running, then:

Run: `uv run pytest -q -m slow`
Expected: `6 passed` in one to two minutes (the very first run on a machine compiles Cython code for a few minutes more; Brian2 caches it in `~/.cython`). Brian2 `INFO` lines about the cache are harmless.

- [ ] **Step 5: Run the fast suite**

Run: `uv run pytest -q -m "not slow"`
Expected: `125 passed, 6 deselected`.

- [ ] **Step 6: Commit**

```bash
git add bakeoff/fly/brain.py tests/conftest.py tests/test_fly_brain.py
git commit -m "feat: fly brain wrapper, built once and restored per 100 ms decision window"
```

---
### Task 7: Response surface and the stand-in brain

**Files:**
- Create: `bakeoff/fly/surface.py`, `calibration/response_surface.json` (generated, committed)
- Test: `tests/test_fly_surface.py`

**Interfaces:**
- Consumes: `Reading` (Task 5); `LOOMING_STEP_HZ`, `MAX_HZ` (Task 4); `bakeoff.fly.data.MODEL_REPO_COMMIT`, `ANNOTATIONS_COMMIT`; any brain with `window(left_hz, right_hz, noise_seed)` and `window_ms`; the session fixture `brain` (Task 6).
- Produces: `SURFACE_SCHEMA = 1`, `TRIALS = 8`, `LEVELS_HZ` (the 11 floats 0.0, 25.0, … 250.0); `measure_surface(brain, levels_hz=LEVELS_HZ, trials=TRIALS, progress=None) -> dict`; `load_surface(path) -> dict`; `SurrogateBrain(surface)` with the same `window()` / `close()` / `window_ms` as `Brain`; `main(argv) -> int`. Surface JSON: `{schema, window_ms, levels_hz, trials, model_commit, annotations_commit, cells: [{left_hz, right_hz, spike_counts: [ {"DNa01_left": int, ...} per trial ]}]}`.

- [ ] **Step 1: Write the failing tests**

`tests/test_fly_surface.py`:

```python
import json
from pathlib import Path

import pytest

from bakeoff.fly.reading import Reading
from bakeoff.fly.surface import LEVELS_HZ, SurrogateBrain, load_surface, measure_surface

SURFACE_FILE = Path(__file__).resolve().parents[1] / "calibration" / "response_surface.json"


class CountingBrain:
    """Left DNa01 spikes once per 25 Hz in the right eye and vice versa; every other call adds a "noise" spike."""

    window_ms = 100.0

    def __init__(self):
        self.calls = []

    def window(self, left_hz, right_hz, noise_seed=None):
        self.calls.append((left_hz, right_hz, noise_seed))
        counts = {"DNa01_left": int(right_hz // 25) + len(self.calls) % 2, "DNa01_right": int(left_hz // 25)}
        return Reading(rates_hz={}, spike_counts=counts, spike_times_ms={}, total_spikes=0, wall_ms=0.0)


def test_the_levels_are_the_eleven_steps_from_0_to_250_hz():
    assert LEVELS_HZ == (0.0, 25.0, 50.0, 75.0, 100.0, 125.0, 150.0, 175.0, 200.0, 225.0, 250.0)


def test_measure_surface_runs_every_input_pair_with_distinct_repeatable_noise():
    brain, ticks = CountingBrain(), []
    surface = measure_surface(brain, levels_hz=(0.0, 25.0), trials=3, progress=lambda done, total: ticks.append((done, total)))
    assert [(c["left_hz"], c["right_hz"]) for c in surface["cells"]] == [(0.0, 0.0), (0.0, 25.0), (25.0, 0.0), (25.0, 25.0)]
    assert all(len(c["spike_counts"]) == 3 for c in surface["cells"])
    assert len({seed for _, _, seed in brain.calls}) == 12
    assert ticks == [(1, 4), (2, 4), (3, 4), (4, 4)]
    assert (surface["schema"], surface["window_ms"], surface["trials"], surface["levels_hz"]) == (1, 100.0, 3, [0.0, 25.0])
    assert len(surface["model_commit"]) == 40 and len(surface["annotations_commit"]) == 40
    again = measure_surface(CountingBrain(), levels_hz=(0.0, 25.0), trials=3)
    assert again == surface
    json.dumps(surface)


def test_the_surrogate_replays_a_measured_trial_chosen_by_the_noise_seed(tmp_path):
    surface = measure_surface(CountingBrain(), levels_hz=(0.0, 25.0), trials=4)
    path = tmp_path / "surface.json"
    path.write_text(json.dumps(surface))
    brain = SurrogateBrain(load_surface(path))
    reading = brain.window(25.0, 0.0, noise_seed=5)
    assert reading == brain.window(25.0, 0.0, noise_seed=5)
    assert reading.spike_counts["DNa01_right"] == 1 and reading.rates_hz["DNa01_right"] == 10.0  # 1 spike in 100 ms
    seen = {brain.window(0.0, 25.0, noise_seed=s).spike_counts["DNa01_left"] for s in range(40)}
    assert seen == {1, 2}  # both noise outcomes that were measured come back
    brain.close()


def test_the_surrogate_refuses_an_input_that_was_not_measured():
    brain = SurrogateBrain(measure_surface(CountingBrain(), levels_hz=(0.0, 25.0), trials=1))
    with pytest.raises(KeyError, match="was not measured"):
        brain.window(10.0, 0.0, noise_seed=1)


def test_the_surrogate_refuses_an_unknown_schema():
    with pytest.raises(ValueError, match="unknown response surface schema"):
        SurrogateBrain({"schema": 99})


@pytest.mark.slow
def test_the_committed_surface_is_what_the_brain_does_today(brain):
    """Guards the calibration against drift (a Brian2 upgrade, different data, a changed wrapper)."""
    committed = load_surface(SURFACE_FILE)
    assert (committed["schema"], committed["trials"], committed["levels_hz"]) == (1, 8, list(LEVELS_HZ))
    assert len(committed["cells"]) == 121
    cells = {(c["left_hz"], c["right_hz"]): c["spike_counts"] for c in committed["cells"]}
    for cell in measure_surface(brain, levels_hz=(0.0, 150.0), trials=8)["cells"]:
        assert cell["spike_counts"] == cells[(cell["left_hz"], cell["right_hz"])]
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest -q -m "not slow" tests/test_fly_surface.py`
Expected: collection error, `ModuleNotFoundError: No module named 'bakeoff.fly.surface'`.

- [ ] **Step 3: Write `bakeoff/fly/surface.py`**

```python
"""The fly's measured response to every input it can get, and a stand-in brain that replays it.

Looming rates come in steps of LOOMING_STEP_HZ, so an eye has 11 levels and the brain has
11 x 11 possible inputs. Measuring each one a few times with fresh input noise gives a table from
which thousands of practice games can be played in seconds (the real brain needs about 0.7 s per
decision). The stand-in is a calibration tool only: tournament runs always use the real brain.

    uv run python -m bakeoff.fly.surface calibration/response_surface.json
"""

from __future__ import annotations

import json
import random
import sys
import zlib
from pathlib import Path

from bakeoff.fly import data
from bakeoff.fly.reading import Reading
from bakeoff.senses import LOOMING_STEP_HZ, MAX_HZ

SURFACE_SCHEMA = 1
TRIALS = 8
LEVELS_HZ = tuple(i * LOOMING_STEP_HZ for i in range(int(MAX_HZ / LOOMING_STEP_HZ) + 1))


def _trial_seed(left_hz: float, right_hz: float, trial: int) -> int:
    return zlib.crc32(f"surface:{left_hz}:{right_hz}:{trial}".encode())


def measure_surface(brain, levels_hz=LEVELS_HZ, trials: int = TRIALS, progress=None) -> dict:
    cells = []
    for left_hz in levels_hz:
        for right_hz in levels_hz:
            readings = [brain.window(left_hz, right_hz, noise_seed=_trial_seed(left_hz, right_hz, t))
                        for t in range(trials)]
            cells.append({"left_hz": left_hz, "right_hz": right_hz,
                          "spike_counts": [r.spike_counts for r in readings]})
            if progress is not None:
                progress(len(cells), len(levels_hz) ** 2)
    return {"schema": SURFACE_SCHEMA, "window_ms": brain.window_ms, "levels_hz": list(levels_hz),
            "trials": trials, "model_commit": data.MODEL_REPO_COMMIT,
            "annotations_commit": data.ANNOTATIONS_COMMIT, "cells": cells}


class SurrogateBrain:
    """Same `window()` as the real Brain, answered from the table: the noise seed picks one of the
    measured trials of that input. Every read-out neuron group has one neuron, so rate = count / window."""

    def __init__(self, surface: dict):
        if surface.get("schema") != SURFACE_SCHEMA:
            raise ValueError(f"unknown response surface schema: {surface.get('schema')!r}")
        self.window_ms = surface["window_ms"]
        self._cells = {(c["left_hz"], c["right_hz"]): c["spike_counts"] for c in surface["cells"]}

    def window(self, left_hz: float, right_hz: float, noise_seed: int | None = None) -> Reading:
        trials = self._cells.get((left_hz, right_hz))
        if trials is None:
            raise KeyError(f"input ({left_hz}, {right_hz}) Hz was not measured; levels are steps of {LOOMING_STEP_HZ} Hz")
        counts = trials[random.Random(noise_seed).randrange(len(trials))]
        seconds = self.window_ms / 1000.0
        return Reading(rates_hz={name: n / seconds for name, n in counts.items()}, spike_counts=dict(counts),
                       spike_times_ms={}, total_spikes=0, wall_ms=0.0)

    def close(self) -> None:
        pass


def load_surface(path: Path | str) -> dict:
    return json.loads(Path(path).read_text())


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m bakeoff.fly.surface <out.json>", file=sys.stderr)
        return 2
    from bakeoff.fly.brain import Brain

    brain = Brain()
    try:
        surface = measure_surface(brain, progress=lambda done, total: print(f"\r{done}/{total} inputs", end="", flush=True))
    finally:
        brain.close()
    out = Path(argv[0])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(surface, separators=(",", ":")) + "\n")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the fast tests**

Run: `uv run pytest -q -m "not slow"`
Expected: `130 passed, 7 deselected`.

- [ ] **Step 5: Measure the surface with the real brain**

Make sure no other fly process is running. This takes 15 to 40 minutes (968 windows; strong inputs simulate more slowly; 16 minutes in the prototype) and prints a counter. Run it in the background and wait for it; do not start anything else that builds a brain meanwhile.

Run: `uv run python -m bakeoff.fly.surface calibration/response_surface.json`
Expected: `121/121 inputs`, then `wrote calibration/response_surface.json` (about 130 KB).

Sanity-check it:

```bash
uv run python -c "
from bakeoff.fly.surface import SurrogateBrain, load_surface
from bakeoff.players.fly import jump_signal_hz, turn_signal_hz
brain = SurrogateBrain(load_surface('calibration/response_surface.json'))
for left, right in ((0.0, 0.0), (150.0, 0.0), (0.0, 150.0), (250.0, 250.0)):
    r = brain.window(left, right, noise_seed=0).rates_hz
    print(left, right, turn_signal_hz(r), jump_signal_hz(r))"
```

Expected (columns: left Hz, right Hz, turn signal, jump signal): zero turn and zero jump signal for `0.0 0.0`; a clearly positive turn signal for `150.0 0.0` (threat on the left, turn right), clearly negative for `0.0 150.0`; the largest jump signal for `250.0 250.0`. In the prototype:

```
0.0 0.0 0.0 0.0
150.0 0.0 70.0 130.0
0.0 150.0 -60.0 135.0
250.0 250.0 20.0 215.0
```

- [ ] **Step 6: Check the file against the brain**

Run: `uv run pytest -q -m slow`
Expected: `7 passed`. The new slow test re-measures four inputs and demands the identical spike counts: the seeded simulation is repeatable across processes. If it fails right after measuring, stop and report; do not loosen the test.

- [ ] **Step 7: Commit**

```bash
git add bakeoff/fly/surface.py tests/test_fly_surface.py calibration/response_surface.json
git commit -m "feat: measured fly response surface (121 inputs x 8 trials) and a stand-in brain that replays it"
```

---

### Task 8: Calibration search

**Files:**
- Create: `bakeoff/fly/calibrate.py`
- Test: `tests/test_fly_calibrate.py`

**Interfaces:**
- Consumes: `SurrogateBrain`, `load_surface`, `measure_surface`, `LEVELS_HZ` (Task 7); `FlyPlayer(brain_factory, turn_threshold_hz, jump_threshold_hz, gain_hz, falloff)` (Task 5); `make_player`; `Game`, `generate_track`, `compute_senses`.
- Produces: `PRACTICE_SEEDS = range(1000, 1200)`, `HELD_OUT_SEEDS = range(1200, 1400)`, `CHECK_SEEDS = range(1000, 1020)`; the grid `GAINS_HZ`, `FALLOFFS`, `TURN_THRESHOLDS_HZ`, `JUMP_THRESHOLDS_HZ` (4 × 4 × 6 × 8 = 768 candidates); `CONFIG_COLUMNS`, `SCORE_COLUMNS`; `play(player, track) -> (Game, list[str])`; `score(player, tracks) -> {mean_rows, median_rows, finished, jump_share}`; `search(surface, tracks, ...) -> list[dict]` best first; `report(surface, results, held_out, check, floors) -> str`; `main(argv) -> int`.

The grid, and why these values: a gain of 250 Hz lets a single gap in the next row saturate an eye and 50 Hz needs five; falloff 1–4 goes from "all six rows matter" to "only the next row or two". Turn thresholds step in whole spikes (one spike of one neuron in 100 ms is 10 Hz). The Giant Fiber mean sits near 100 Hz for weak threats and near 200 Hz for the strongest, so 75 Hz is "jump at almost anything" and 250 Hz is "never jump".

- [ ] **Step 1: Write the failing tests**

`tests/test_fly_calibrate.py` (the cartoon `ReflexBrain` stands in for the measured surface, so these tests are fast and need no data):

```python
from bakeoff.fly.calibrate import CONFIG_COLUMNS, play, report, score, search
from bakeoff.fly.reading import Reading
from bakeoff.fly.surface import LEVELS_HZ, measure_surface
from bakeoff.game.track import generate_track
from bakeoff.players import make_player

NAMES = ("DNa01_left", "DNa01_right", "DNb01_left", "DNb01_right", "DNp01_left", "DNp01_right")


class ReflexBrain:
    """A cartoon of the real one: steering fires opposite the louder eye, the Giant Fiber with the sum."""

    window_ms = 100.0

    def window(self, left_hz, right_hz, noise_seed=None):
        counts = dict.fromkeys(NAMES, 0)
        counts["DNa01_right"] = int(max(left_hz - right_hz, 0) // 25)
        counts["DNa01_left"] = int(max(right_hz - left_hz, 0) // 25)
        counts["DNp01_left"] = counts["DNp01_right"] = int((left_hz + right_hz) // 25)
        return Reading(rates_hz={}, spike_counts=counts, spike_times_ms={}, total_spikes=0, wall_ms=0.0)


def surface():
    return measure_surface(ReflexBrain(), levels_hz=LEVELS_HZ, trials=1)


def test_play_returns_the_finished_game_and_the_actions_taken():
    track = generate_track(1000, max_rows=40)
    game, actions = play(make_player("solver"), track)
    assert game.over and game.rows_survived == 40
    assert sum(2 if a == "jump" else 1 for a in actions) >= 40


def test_score_summarises_a_player_over_tracks():
    tracks = [generate_track(seed, max_rows=40) for seed in (1000, 1001, 1002)]
    assert score(make_player("always_jump"), tracks)["jump_share"] == 1.0
    solver = score(make_player("solver"), tracks)
    assert solver == {"mean_rows": 40.0, "median_rows": 40, "finished": 3, "jump_share": solver["jump_share"]}


def test_search_scores_every_candidate_and_puts_the_best_first():
    tracks = [generate_track(seed, max_rows=60) for seed in range(1000, 1006)]
    results = search(surface(), tracks, gains_hz=(100.0,), falloffs=(1.0, 2.0),
                     turn_thresholds_hz=(10.0, 1000.0), jump_thresholds_hz=(100.0, 1000.0))
    assert len(results) == 8
    assert [r["mean_rows"] for r in results] == sorted((r["mean_rows"] for r in results), reverse=True)
    never_moves = [r for r in results if r["turn_threshold_hz"] == 1000.0 and r["jump_threshold_hz"] == 1000.0]
    assert all(r["jump_share"] == 0.0 for r in never_moves)
    assert results[0]["mean_rows"] > never_moves[0]["mean_rows"]  # reacting beats running straight
    assert search(surface(), tracks, gains_hz=(100.0,), falloffs=(1.0, 2.0),
                  turn_thresholds_hz=(10.0, 1000.0), jump_thresholds_hz=(100.0, 1000.0)) == results


def test_report_names_the_winner_and_says_whose_tuning_it_is():
    tracks = [generate_track(seed, max_rows=40) for seed in (1000, 1001)]
    results = search(surface(), tracks, gains_hz=(100.0,), falloffs=(1.0,),
                     turn_thresholds_hz=(10.0,), jump_thresholds_hz=(100.0, 150.0))
    floors = [{"player": "random", **score(make_player("random"), tracks)}]
    solver = score(make_player("solver"), tracks)
    text = report(surface(), results, held_out=solver, check=solver, floors=floors)
    assert "OUR tuning, not the fly's biology" in text
    assert "| " + " | ".join(CONFIG_COLUMNS) in text and "## Winner" in text and "| random |" in text
    assert "2 candidates" in text and "121 inputs x 1 trials" in text
    assert "--players fly --seeds 20 --seed-start 1000" in text
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest -q tests/test_fly_calibrate.py`
Expected: collection error, `ModuleNotFoundError: No module named 'bakeoff.fly.calibrate'`.

- [ ] **Step 3: Write `bakeoff/fly/calibrate.py`**

```python
"""Fix the looming weighting and the fly's two thresholds on practice seeds.

Every candidate plays the practice tracks with the stand-in brain (the measured response surface).
The rule is fixed before looking: the candidate with the highest mean rows survived on
PRACTICE_SEEDS wins; ties go to the candidate listed first. HELD_OUT_SEEDS are played once, by the
winner only, to show how much of its score is luck. CHECK_SEEDS are the practice seeds the real
brain replays afterwards, to show how far the stand-in can be trusted. Tournament seeds (below
1000) are never touched.

    uv run python -m bakeoff.fly.calibrate calibration/response_surface.json calibration/REPORT.md
"""

from __future__ import annotations

import itertools
import statistics
import sys
from pathlib import Path

from bakeoff.fly.surface import SurrogateBrain, load_surface
from bakeoff.game.engine import Game
from bakeoff.game.track import Track, generate_track
from bakeoff.players import make_player
from bakeoff.players.fly import FlyPlayer
from bakeoff.senses import compute_senses

PRACTICE_SEEDS = range(1000, 1200)
HELD_OUT_SEEDS = range(1200, 1400)
CHECK_SEEDS = range(1000, 1020)
GAINS_HZ = (50.0, 100.0, 150.0, 250.0)
FALLOFFS = (1.0, 2.0, 3.0, 4.0)
TURN_THRESHOLDS_HZ = (0.0, 10.0, 20.0, 30.0, 40.0, 60.0)
JUMP_THRESHOLDS_HZ = (75.0, 100.0, 125.0, 150.0, 175.0, 200.0, 225.0, 250.0)
FLOORS = ("random", "always_jump", "solver")


def play(player, track: Track) -> tuple[Game, list[str]]:
    game = Game(track)
    player.reset(game, track.seed)
    actions = []
    while not game.over:
        action = player.act(compute_senses(game)).chosen_action
        game.step(action)
        player.observe(action)
        actions.append(action)
    return game, actions


def score(player, tracks: list[Track]) -> dict:
    games, actions = [], []
    for track in tracks:
        game, played = play(player, track)
        games.append(game)
        actions += played
    rows = [g.rows_survived for g in games]
    return {"mean_rows": sum(rows) / len(rows), "median_rows": statistics.median(rows),
            "finished": sum(g.finished for g in games), "jump_share": actions.count("jump") / len(actions)}


def search(surface: dict, tracks: list[Track], gains_hz=GAINS_HZ, falloffs=FALLOFFS,
           turn_thresholds_hz=TURN_THRESHOLDS_HZ, jump_thresholds_hz=JUMP_THRESHOLDS_HZ) -> list[dict]:
    """Every candidate's score, best first (stable sort: ties keep grid order)."""
    brain = SurrogateBrain(surface)
    results = []
    for gain, falloff, turn, jump in itertools.product(gains_hz, falloffs, turn_thresholds_hz, jump_thresholds_hz):
        config = {"gain_hz": gain, "falloff": falloff, "turn_threshold_hz": turn, "jump_threshold_hz": jump}
        results.append({**config, **score(FlyPlayer(brain_factory=lambda: brain, **config), tracks)})
    return sorted(results, key=lambda r: -r["mean_rows"])


def _table(rows: list[dict], columns: tuple[str, ...]) -> str:
    def fmt(value) -> str:
        return f"{value:.2f}" if isinstance(value, float) else str(value)

    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    return "\n".join(lines + ["| " + " | ".join(fmt(r[c]) for c in columns) + " |" for r in rows])


CONFIG_COLUMNS = ("gain_hz", "falloff", "turn_threshold_hz", "jump_threshold_hz")
SCORE_COLUMNS = ("mean_rows", "median_rows", "finished", "jump_share")


def report(surface: dict, results: list[dict], held_out: dict, check: dict, floors: list[dict]) -> str:
    winner = results[0]
    return "\n\n".join([
        "# Fly calibration",
        "Generated by `python -m bakeoff.fly.calibrate`; do not edit by hand. Everything here is OUR "
        "tuning, not the fly's biology: the looming weighting (`gain_hz / row ** falloff` per visible gap) "
        "and the two thresholds on the fly's own read-out neurons.",
        f"Stand-in brain: measured response surface, {len(surface['cells'])} inputs x {surface['trials']} trials, "
        f"{surface['window_ms']:.0f} ms window, model commit `{surface['model_commit'][:12]}`. "
        f"{len(results)} candidates, practice seeds {PRACTICE_SEEDS.start}-{PRACTICE_SEEDS.stop - 1}. "
        "Rule fixed beforehand: highest mean rows survived wins, ties to the first in grid order.",
        "## Winner\n\n" + _table([winner], CONFIG_COLUMNS + SCORE_COLUMNS),
        f"## Winner on held-out seeds {HELD_OUT_SEEDS.start}-{HELD_OUT_SEEDS.stop - 1} (played once)\n\n"
        + _table([held_out], SCORE_COLUMNS),
        f"## Winner on check seeds {CHECK_SEEDS.start}-{CHECK_SEEDS.stop - 1}, stand-in brain\n\n"
        + _table([check], SCORE_COLUMNS)
        + f"\n\nCompare with the real brain: `uv run python -m bakeoff run --players fly --seeds {len(CHECK_SEEDS)} "
        f"--seed-start {CHECK_SEEDS.start}`.",
        "## Floors and reference on the practice seeds\n\n" + _table(floors, ("player",) + SCORE_COLUMNS),
        "## Top 10 candidates\n\n" + _table(results[:10], CONFIG_COLUMNS + SCORE_COLUMNS),
    ]) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: python -m bakeoff.fly.calibrate <response_surface.json> <REPORT.md>", file=sys.stderr)
        return 2
    surface = load_surface(argv[0])
    practice = [generate_track(seed) for seed in PRACTICE_SEEDS]
    results = search(surface, practice)
    winner = {k: results[0][k] for k in CONFIG_COLUMNS}
    brain = SurrogateBrain(surface)

    def winner_on(seeds: range) -> dict:
        return score(FlyPlayer(brain_factory=lambda: brain, **winner), [generate_track(seed) for seed in seeds])

    floors = [{"player": name, **score(make_player(name), practice)} for name in FLOORS]
    text = report(surface, results, winner_on(HELD_OUT_SEEDS), winner_on(CHECK_SEEDS), floors)
    Path(argv[1]).write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -q -m "not slow"`
Expected: `134 passed, 7 deselected`.

- [ ] **Step 5: Commit**

```bash
git add bakeoff/fly/calibrate.py tests/test_fly_calibrate.py
git commit -m "feat: calibration search over looming weighting and thresholds on practice seeds"
```

---
### Task 9: Run the calibration and fix the constants

**Files:**
- Create: `calibration/REPORT.md` (generated)
- Modify: `bakeoff/senses.py`, `bakeoff/players/fly.py`
- Test: `tests/test_fly_calibrate.py`, `tests/test_runner.py`

**Interfaces:**
- Consumes: `python -m bakeoff.fly.calibrate` (Task 8), `calibration/response_surface.json` (Task 7).
- Produces: the final `LOOMING_GAIN_HZ`, `LOOMING_FALLOFF` (`bakeoff/senses.py`), `TURN_THRESHOLD_HZ`, `JUMP_THRESHOLD_HZ`, `CALIBRATED = True` (`bakeoff/players/fly.py`). After this commit the numbers are frozen for the tournament.

**The procedure is binding, not the numbers printed in this plan.** The prototype's winner was gain 250 Hz, falloff 3, turn threshold 0 Hz, jump threshold 200 Hz, and because the surface is seeded you should get exactly that. If your `calibration/REPORT.md` names a different winner, use *your* winner's four numbers everywhere in this task, and say so prominently in your task report.

- [ ] **Step 1: Run the search**

No brain is built here; it takes two to three minutes.

Run: `uv run python -m bakeoff.fly.calibrate calibration/response_surface.json calibration/REPORT.md`
Expected (prototype output, abridged):

```
## Winner

| gain_hz | falloff | turn_threshold_hz | jump_threshold_hz | mean_rows | median_rows | finished | jump_share |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 250.00 | 3.00 | 0.00 | 200.00 | 140.71 | 145.00 | 0 | 0.09 |

## Winner on held-out seeds 1200-1399 (played once)

| 139.76 | 144.00 | 0 | 0.09 |

## Winner on check seeds 1000-1019, stand-in brain

| 118.70 | 120.50 | 0 | 0.07 |

## Floors and reference on the practice seeds

| random | 32.35 | 28.00 | 0 | 0.25 |
| always_jump | 46.56 | 39.00 | 0 | 1.00 |
| solver | 298.75 | 300.00 | 195 | 0.02 |
```

What it says: the stand-in fly survives about 140 rows, three times the always-jump floor and under half the solver; it jumps in 9 % of its moves, so it is not winning by jumping; held-out seeds score the same as practice seeds, so the choice is not luck.

- [ ] **Step 2: Write the failing tests**

In `tests/test_fly_calibrate.py` add `from pathlib import Path` as the first import (followed by a blank line), replace the line `from bakeoff.players import make_player` with

```python
from bakeoff.players import fly, make_player
from bakeoff.senses import LOOMING_FALLOFF, LOOMING_GAIN_HZ
```

and append:

```python


def test_the_committed_constants_are_the_calibration_winner():
    text = (Path(__file__).resolve().parents[1] / "calibration" / "REPORT.md").read_text()
    winner_row = text.split("## Winner\n\n")[1].splitlines()[2]
    winner = tuple(float(cell) for cell in winner_row.strip("| ").split(" | ")[:4])
    assert winner == (LOOMING_GAIN_HZ, LOOMING_FALLOFF, fly.TURN_THRESHOLD_HZ, fly.JUMP_THRESHOLD_HZ)
    assert fly.CALIBRATED
```

In `tests/test_runner.py`, in `test_run_writes_one_jsonl_per_player_and_meta`, replace the `looming` and `fly` expectations with the winner's numbers and `provisional` false:

```python
                            "looming": {"gain_hz": 250.0, "falloff": 3.0, "step_hz": 25.0, "max_hz": 250.0,
                                        "provisional": False}}
    assert meta["fly"] == {"turn_threshold_hz": 0.0, "jump_threshold_hz": 200.0, "window_ms": 100.0,
                           "provisional": False, "model_commit": "91bdd1e7dcf193f3e7ca5a8933497fcef63b7960",
                           "annotations_commit": "17fc57722002e1a7d38cdd0c89ac382bf92718da"}
```

- [ ] **Step 3: Run the tests to see them fail**

Run: `uv run pytest -q tests/test_fly_calibrate.py tests/test_runner.py`
Expected: 2 failures (the constants are still the provisional ones).

- [ ] **Step 4: Fix the constants**

In `bakeoff/senses.py` replace

```python
# PROVISIONAL until the calibration task fixes gain and falloff on practice seeds.
LOOMING_GAIN_HZ = 100.0
LOOMING_FALLOFF = 1.0
```

with

```python
# Gain and falloff were fixed on practice seeds 1000-1199 (calibration/REPORT.md); do not retune.
LOOMING_GAIN_HZ = 250.0
LOOMING_FALLOFF = 3.0
```

In `bakeoff/players/fly.py` replace

```python
# The fly's only tuning. PROVISIONAL until the calibration task fixes them on practice seeds
# and sets CALIBRATED (which also covers the looming gain and falloff in bakeoff/senses.py).
TURN_THRESHOLD_HZ = 20.0
JUMP_THRESHOLD_HZ = 150.0
CALIBRATED = False
```

with

```python
# The fly's only tuning, and OURS: fixed once on practice seeds 1000-1199 together with the looming
# gain and falloff in bakeoff/senses.py (calibration/REPORT.md). Do not retune: tournament seeds
# must never influence these numbers. A turn threshold of 0 means any net steering spike turns.
TURN_THRESHOLD_HZ = 0.0
JUMP_THRESHOLD_HZ = 200.0
CALIBRATED = True
```

(If your winner's turn threshold is not 0, drop the last comment sentence.)

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -q -m "not slow"`
Expected: `135 passed, 7 deselected`.

- [ ] **Step 6: Commit**

```bash
git add calibration/REPORT.md bakeoff/senses.py bakeoff/players/fly.py tests/test_fly_calibrate.py tests/test_runner.py
git commit -m "feat: fly constants fixed on practice seeds (gain 250 Hz, falloff 3, turn 0 Hz, jump 200 Hz)"
```

---

### Task 10: Real-brain check, first scoreboard and docs

**Files:**
- Create: `calibration/RESULTS.md`
- Modify: `README.md`, `CLAUDE.md`, `docs/DECISIONS.md`, `docs/superpowers/specs/2026-09-19-tunnel-run-design.md` (one bullet)

**Interfaces:**
- Consumes: the CLI (`python -m bakeoff run|report`), players `fly`, `always_jump`, `random`, `solver`; `calibration/REPORT.md`.
- Produces: the first fly-vs-baselines scoreboard; project docs that point phase 3 at the right next step.

Both runs below use the real brain: one fly process at a time, nothing else heavy running. A fly decision takes 0.7 s on a quiet machine and about 1.2 s on a busy one, so a run takes roughly `rows survived × seeds × 1 s`: expect 30 to 60 minutes each. Lines are flushed per step; an interrupted run keeps its rows and the report shows them as `incomplete`. Run them in the background and wait.

- [ ] **Step 1: The real brain on the check seeds**

Run: `uv run python -m bakeoff run --players fly --seeds 20 --seed-start 1000`
Expected: 20 to 40 minutes (33 in the prototype, on a busy machine); `status: completed`; a `fly` row with `runs` 20. In the prototype:

```
status: completed
| player | runs | incomplete | missing | mean_rows | median_rows | finished | ran_into_gap | jumped_into_gap | dodged_into_gap | jump_share | solver_agreement | fallback_rate | invalid_rate | error_rate | requests | mean_latency_ms | input_tokens | output_tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fly | 20 | 0 | 0 | 117.95 | 113.00 | 0 | 0 | 20 | 0 | 0.08 | 0.99 | 0.00 | 0.00 | 0.00 | 0 | - | 0 | 0 |
```

Compare `mean_rows` with the stand-in's number for the same seeds in `calibration/REPORT.md` ("Winner on check seeds"): 117.95 against 118.70 in the prototype, a ratio of 0.99. The two differ only by input noise (fresh per decision here, one of 8 recorded trials there), and the run is seeded, so you should see the same 117.95. Note what the table already shows about this fly: it agrees with the solver on 99 % of its moves, and all 20 deaths are `jumped_into_gap`. Its Giant Fiber jumps at a gap straight ahead without knowing whether the landing tile is floor. That is the reflex, not a bug; leave it.

**Stop rule:** if the real brain's `mean_rows` is below 0.7 × the stand-in's, stop here and report both numbers to the user: the stand-in cannot be trusted and the calibration needs rethinking. Do not retune anything yourself.

- [ ] **Step 2: The first scoreboard**

The constants are committed, so tournament-range seeds may now be played.

Run: `uv run python -m bakeoff run --players fly,always_jump,random,solver --seeds 20`
Expected: about as long as Step 1; `status: completed`; four rows. The three baselines are seeded and must start exactly `always_jump | 20 | 0 | 0 | 47.80 | 39.00`, `random | 20 | 0 | 0 | 34.70 | 30.00` and `solver | 20 | 0 | 0 | 299.70 | 300.00 | 19`. There are no prototype numbers for the fly here on purpose: the prototype never played a seed below 1000. Whatever the fly scores is the result; do not react to it by changing anything.

- [ ] **Step 3: Write `calibration/RESULTS.md`**

Paste the two report tables printed by your runs where indicated (complete rows, all columns), and fill the three numbers in the first paragraph from them:

````markdown
# Fly: first results with the real brain

Constants from `calibration/REPORT.md` (ours, not the fly's biology), real Brian2 brain, one
decision per 100 ms window, input noise seeded per (track seed, row) so these runs repeat exactly.

On check seeds 1000-1019 the real brain averaged <real mean_rows> rows; the stand-in brain used for
calibration predicted <stand-in mean_rows from REPORT.md> (ratio <real / stand-in, two decimals>).

## Check seeds 1000-1019 (practice)

<table printed by the Step 1 run>

## First scoreboard, seeds 0-19

<table printed by the Step 2 run>

`always_jump` is the floor for a jump-heavy player, `random` the floor for everything else, `solver`
the reference (same 6-row, ±3-lane view; not a contestant).
````

- [ ] **Step 4: Update the docs**

In `README.md` replace the `Status:` paragraph and the command block below it with (fill the fly's mean rows from Step 2, rounded to a whole number):

```markdown
Status: phase 2 of 5 built. The untrained fly plays: on seeds 0–19 it survives <fly mean_rows> rows
on average (random 35, always-jump 48, solver 300; `calibration/RESULTS.md`).

    uv run pytest -m "not slow"                      # 2 s; `-m slow` runs the real brain (1 GB)
    uv run python -m scripts.fetch_fly_data          # once: 400 MB into data/
    uv run python -m bakeoff run --players fly,always_jump,random,solver --seeds 20
    uv run python -m bakeoff report runs/<run_id>
```

In `CLAUDE.md` replace the body of `## Status` with:

```markdown
Design approved 2026-09-19. Phase 1 built (game, senses, baselines, runner, report, CLI). Phase 2
built (plan: `docs/superpowers/plans/2026-09-19-phase2-fly-player.md`): fly player on the real
Brian2 model, looming weighting and two thresholds fixed on practice seeds 1000–1199 and frozen
(`calibration/REPORT.md`; never retune, never let seeds below 1000 influence them). First
scoreboard in `calibration/RESULTS.md`. Next: write the phase 3 plan (Jev and LLM players with
cache and request cap), then build it. Each phase gets its own plan.
```

and add to the list under `## How we work here`:

```markdown
- Fast tests: `uv run pytest -m "not slow"`. `-m slow` builds the real fly brain (about 1 GB,
  one minute); never run two fly processes at once.
```

In `docs/DECISIONS.md` add after decision 7:

```markdown
8. **Fly input and tuning (phase 2, ours, not the fly's biology):** each visible gap adds
   `250 / row³` Hz to its eye, capped at 250 Hz and rounded to 25 Hz steps; any net steering
   spike turns (threshold 0 Hz); Giant Fiber mean above 200 Hz jumps. Chosen by a fixed rule from
   768 candidates on practice seeds 1000–1199 using a measured response surface as a stand-in
   brain, confirmed with the real brain. Frozen: `calibration/REPORT.md`, `calibration/RESULTS.md`.
9. **`always_jump` is a second floor** and the report shows `jump_share`, so a jump-heavy player
   is judged against the right baseline.
10. **Tournament seeds must be below 1000**; 1000–1399 were used for calibration.
```

(Use your winner's numbers if they differ.) In the spec, `docs/superpowers/specs/2026-09-19-tunnel-run-design.md`, under `## Open items`, replace the bullet that starts `- The looming weighting function and the two fly thresholds` with:

```markdown
- Resolved in phase 2: looming weighting and fly thresholds, see `calibration/REPORT.md`
  (input in 25 Hz steps; `always_jump` added as a second floor).
```

In `docs/DECISIONS.md`, in `## Open`, delete the two items about the fly's looming weighting and about `always_jump`. Replace the body of `## Next step` with:

```markdown
Phases 1 and 2 are built. Write the phase 3 plan (Jev and LLM players: thin clients sharing a disk
cache and a hard `--max-requests` cap, keys loaded inside the program, first cost numbers from one
capped track).
```

- [ ] **Step 5: Run everything once more**

Run: `uv run pytest -q -m "not slow"` — expected `135 passed, 7 deselected`.
Run: `uv run pytest -q -m slow` — expected `7 passed`.

- [ ] **Step 6: Commit**

```bash
git add calibration/RESULTS.md README.md CLAUDE.md docs/DECISIONS.md docs/superpowers/specs/2026-09-19-tunnel-run-design.md
git commit -m "docs: first fly-vs-baselines scoreboard and phase 2 status"
```

---

## Notes for the phase 3 plan

- `make_player(name, **options)` passes constructor options, but the CLI still exposes none; the paid players need `--max-requests` and a cache directory.
- The report counts a step as a paid request when `latency_ms` is set and `cache_hit` is false. The fly deliberately leaves `latency_ms` empty.
- A fly run is slow (about 0.7 s per row survived). Put `fly` first in `--players` when mixing with paid players, so an API failure does not waste a finished fly run; or run it separately and merge in the viewer.
- Phase 4 (viewer) gets per decision: input rates, read-out rates, spike counts and spike times of DNa01, DNb01, DNp01, DNa02 (both sides), both signals and both thresholds (`docs/STEP_RECORD.md`, "`info` of the fly"), plus the whole response surface in `calibration/response_surface.json` if it wants to show the fly's full input–output table.
- Known weaknesses to state in the viewer and write-up are listed in the spec ("Fly player"). Add: the 25 Hz input steps and the weighting are ours; with falloff 3 the fly effectively sees only the next row or two.
- The solver dies on about 4 % of tracks in late dead ends; pick tournament seeds (below 1000) with that in mind and say so.

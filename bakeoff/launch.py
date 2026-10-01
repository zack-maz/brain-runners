"""uv run brain-runners [live flags]: the one command that opens Brain Runners.

Fetches the study's recorded runs if they are missing (free, about 7 MB, once), then runs `bakeoff live --open`
from the repository root, so runs/ and the response cache are the clone's wherever it is started from. Any flag
passes through to `bakeoff live`, e.g. `uv run brain-runners --max-requests 150`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from bakeoff.__main__ import _parser
from bakeoff.__main__ import main as bakeoff_main

ROOT = Path(__file__).resolve().parents[1]
PATH_FLAGS = ("--out", "--cache")  # the user's own paths stay relative to where they typed the command


def fetch_study_runs() -> list[str]:
    from scripts.study_data import RUNS_DIR, STUDY_RUNS, fetch

    if not all((RUNS_DIR / name / "meta.json").is_file() for name in STUDY_RUNS):
        print("downloading the study's recorded runs (7 MB, free, only this once)...", flush=True)
    return fetch()


def _absolute_paths(argv: list[str], cwd: Path) -> list[str]:
    """`--out x` and `--out=x` with x made absolute against cwd, so the chdir to the root does not move them."""
    out = []
    for i, arg in enumerate(argv):
        flag, eq, value = arg.partition("=")
        if eq and flag in PATH_FLAGS:
            arg = f"{flag}={cwd / value}"
        elif i and argv[i - 1] in PATH_FLAGS:
            arg = str(cwd / arg)
        out.append(arg)
    return out


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    _parser().parse_args(["live", "--open", *argv])  # --help and a mistyped flag answer before any download
    argv = _absolute_paths(argv, Path.cwd())
    os.chdir(ROOT)
    try:
        problems = fetch_study_runs()
    except Exception as e:  # offline, a GitHub hiccup: the page still opens, without the study's runs
        problems = [f"{type(e).__name__}: {e}"]
    for problem in problems:
        print(f"the study's runs are not here ({problem}); Records and Charts show only your own runs. "
              "Try again later: uv run python -m scripts.study_data fetch", file=sys.stderr)
    return bakeoff_main(["live", "--open", *argv])


if __name__ == "__main__":
    sys.exit(main())

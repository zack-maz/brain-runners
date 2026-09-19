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
    if not annotations.is_file() or data.sha256_of(annotations) != expected.get(data.ANNOTATIONS.name):
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

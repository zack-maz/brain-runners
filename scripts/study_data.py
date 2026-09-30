"""The study's runs as one download (decision 57): the recorded runs behind Charts, Records, the Writeup and every
replay, which are too big for the repository, attached to a GitHub Release instead.

    uv run python -m scripts.study_data fetch     # download, check and unpack into the git-ignored runs/
    uv run python -m scripts.study_data pack OUT  # (the maintainer) build the archive from runs/

About 7 MB to download. The archive is checked against a recorded sha256 before anything is unpacked, and
nothing in it may land outside runs/. Spends nothing: these are files, not requests.
"""

from __future__ import annotations

import hashlib
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

RUNS_DIR = Path(__file__).resolve().parents[1] / "runs"

# The study's runs (decision 53, docs/COSTS.md): held-out tracks 100-199 for the free players, 100-114 for
# Claude Haiku. GLM Flash's partial run is not part of it (decision 56).
STUDY_RUNS = (
    # Jev x5 and the bots; the Jev tracks lost to the 2026-09-28 outage were played again below
    "20260928-180538", "20260928-182420", "20260928-182422", "20260928-182423",
    "20260929-120732", "20260929-121210", "20260929-150830", "20260929-160242",
    # fly and fly2
    "20260928-180554", "20260928-210528", "20260929-002309", "20260929-064700",
    # Claude Haiku x4 (decision 54)
    "20260929-175320", "20260929-175905", "20260929-193446", "20260929-193721",
)
URL = "https://github.com/zack-maz/brain-runners/releases/download/study-v1/study-runs.tar.gz"
SHA256 = "797b07c955a5be243b366deb59cdaa68477afc98dbc464ee52a438e9692c7f4d"  # of the uploaded archive


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def pack(runs_dir: Path, out: Path, runs=STUDY_RUNS) -> tuple[Path, str]:
    """The archive of `runs` (each a directory of runs_dir) and its sha256."""
    missing = [name for name in runs if not (Path(runs_dir) / name / "meta.json").is_file()]
    if missing:
        raise FileNotFoundError(f"not in {runs_dir}: {', '.join(missing)}")
    with tarfile.open(out, "w:gz") as tar:
        for name in runs:
            tar.add(Path(runs_dir) / name, arcname=name)
    return Path(out), sha256_of(out)


def fetch(runs_dir: Path = RUNS_DIR, url: str = URL, sha256: str = SHA256, runs=STUDY_RUNS,
          download=urllib.request.urlretrieve) -> list[str]:
    """Download and unpack whatever is missing; return the problems that remain (empty list = ready)."""
    runs_dir = Path(runs_dir)
    if all((runs_dir / name / "meta.json").is_file() for name in runs):
        return []
    with tempfile.TemporaryDirectory() as scratch:
        archive = Path(scratch) / "study-runs.tar.gz"
        download(url, archive)
        got = sha256_of(archive)
        if got != sha256:
            return [f"the download's sha256 is {got}, expected {sha256}: nothing unpacked"]
        runs_dir.mkdir(parents=True, exist_ok=True)
        try:
            with tarfile.open(archive) as tar:
                tar.extractall(runs_dir, filter="data")  # refuses members that would land outside runs_dir
        except tarfile.FilterError as e:
            return [f"the archive tried to write outside {runs_dir}: {e}"]
    return [f"missing after unpacking: {name}" for name in runs if not (runs_dir / name / "meta.json").is_file()]


def main(argv: list[str]) -> int:
    if argv[:1] == ["pack"] and len(argv) == 2:
        archive, digest = pack(RUNS_DIR, Path(argv[1]))
        print(f"{archive}: sha256 {digest}")
        return 0
    if argv == ["fetch"]:
        remaining = fetch()
        for line in remaining:
            print(line, file=sys.stderr)
        print("study runs: " + ("NOT ready" if remaining else f"ready in {RUNS_DIR}"))
        return 1 if remaining else 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

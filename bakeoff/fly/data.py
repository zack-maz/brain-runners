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

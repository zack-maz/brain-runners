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

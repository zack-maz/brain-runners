"""The study's runs as one download (decision 57): packed once from runs/, fetched from a GitHub Release, checked
against a recorded sha256 and unpacked into runs/. No test touches the network: `download` is a local copy."""

import io
import json
import shutil
import tarfile

import pytest

from scripts import study_data


def make_runs(root, names):
    for name in names:
        run = root / name
        run.mkdir(parents=True)
        (run / "meta.json").write_text(json.dumps({"run_id": name}))
        (run / "solver.jsonl").write_text('{"row": 0}\n')


def copier(source):
    def download(url, target):
        shutil.copyfile(source, target)
    return download


def test_pack_then_fetch_puts_every_study_run_back(tmp_path):
    names = ["20260928-180538", "20260929-175320"]
    make_runs(tmp_path / "src", names)
    archive, digest = study_data.pack(tmp_path / "src", tmp_path / "study.tar.gz", names)
    problems = study_data.fetch(tmp_path / "runs", url="https://example.invalid/study.tar.gz", sha256=digest,
                                runs=names, download=copier(archive))
    assert problems == []
    for name in names:
        assert json.loads((tmp_path / "runs" / name / "meta.json").read_text()) == {"run_id": name}


def test_pack_refuses_a_missing_run(tmp_path):
    make_runs(tmp_path / "src", ["20260928-180538"])
    with pytest.raises(FileNotFoundError, match="20260929-175320"):
        study_data.pack(tmp_path / "src", tmp_path / "study.tar.gz", ["20260928-180538", "20260929-175320"])


def test_a_wrong_checksum_unpacks_nothing(tmp_path):
    names = ["20260928-180538"]
    make_runs(tmp_path / "src", names)
    archive, _ = study_data.pack(tmp_path / "src", tmp_path / "study.tar.gz", names)
    problems = study_data.fetch(tmp_path / "runs", url="https://example.invalid/x", sha256="0" * 64, runs=names,
                                download=copier(archive))
    assert problems and "sha256" in problems[0]
    assert not (tmp_path / "runs" / "20260928-180538").exists()


def test_nothing_is_downloaded_when_every_run_is_already_there(tmp_path):
    names = ["20260928-180538"]
    make_runs(tmp_path / "runs", names)

    def refuse(url, target):
        raise AssertionError("downloaded although every run was there")

    assert study_data.fetch(tmp_path / "runs", url="https://example.invalid/x", sha256="0" * 64, runs=names,
                            download=refuse) == []


def test_an_archive_reaching_outside_runs_is_refused(tmp_path):
    evil = tmp_path / "evil.tar.gz"
    with tarfile.open(evil, "w:gz") as tar:
        data = b"x"
        info = tarfile.TarInfo("../outside.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    digest = study_data.sha256_of(evil)
    problems = study_data.fetch(tmp_path / "runs", url="https://example.invalid/x", sha256=digest,
                                runs=["20260928-180538"], download=copier(evil))
    assert problems and not (tmp_path / "outside.txt").exists()


def test_the_recorded_study_is_the_held_out_runs_without_glm():
    assert len(study_data.STUDY_RUNS) == 16 and len(set(study_data.STUDY_RUNS)) == 16
    assert study_data.URL.startswith("https://github.com/zack-maz/brain-runners/releases/download/")
    assert len(study_data.SHA256) == 64

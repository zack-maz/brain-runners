"""`uv run brain-runners`: the one command that opens Brain Runners. It fetches the study's runs when they are
missing, then runs `bakeoff live --open` from the repository root, passing any flag through."""

import os
from pathlib import Path

import pytest

from bakeoff import launch
from bakeoff.__main__ import _parser


@pytest.fixture
def calls(monkeypatch):
    seen = {"live": [], "fetch": 0}

    def fake_fetch():
        seen["fetch"] += 1
        return seen.get("problems", [])

    monkeypatch.setattr(launch, "fetch_study_runs", fake_fetch)
    monkeypatch.setattr(launch, "bakeoff_main", lambda argv: seen["live"].append((argv, os.getcwd())) or 0)
    return seen


def test_it_fetches_the_study_then_opens_the_page_from_the_repository_root(calls, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # started from anywhere inside or outside the clone
    assert launch.main([]) == 0
    assert calls["fetch"] == 1
    assert calls["live"] == [(["live", "--open"], str(Path(launch.__file__).resolve().parents[1]))]


def test_flags_pass_through_to_live(calls):
    assert launch.main(["--max-requests", "150", "--port", "8001"]) == 0
    assert calls["live"][0][0] == ["live", "--open", "--max-requests", "150", "--port", "8001"]


def test_a_failed_fetch_is_said_but_the_page_still_opens(calls, capsys):
    calls["problems"] = ["no network"]
    assert launch.main([]) == 0
    assert "no network" in capsys.readouterr().err
    assert calls["live"]


def test_a_fetch_that_raises_is_said_but_the_page_still_opens(calls, capsys, monkeypatch):
    monkeypatch.setattr(launch, "fetch_study_runs", lambda: (_ for _ in ()).throw(OSError("offline")))
    assert launch.main([]) == 0
    assert "offline" in capsys.readouterr().err
    assert calls["live"]


def test_live_opens_the_browser_only_when_asked(monkeypatch, tmp_path, capsys):
    from bakeoff.__main__ import main

    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))
    monkeypatch.setattr("bakeoff.__main__._serve_until_interrupted", lambda session, printed=None: 0)
    args = ["live", "--port", "0", "--out", str(tmp_path / "runs"), "--cache", str(tmp_path / "cache")]
    assert main(args) == 0 and opened == []
    assert main([*args, "--open"]) == 0
    assert len(opened) == 1 and opened[0].startswith("http://127.0.0.1:")
    assert _parser().parse_args(["live"]).open is False

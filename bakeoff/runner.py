"""Players x seeds, fallback rule, streaming JSONL step log and meta.json run status."""

from __future__ import annotations

import json
import platform
import subprocess
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Callable, Sequence

from bakeoff.errors import BudgetExhausted, PreflightError, RunAborted  # noqa: F401  (re-exported)
from bakeoff.fly import data as fly_data
from bakeoff.fly.reading import WINDOW_MS
from bakeoff.game.engine import ACTIONS, Game
from bakeoff.game.track import LANES, LOOKAHEAD, MAX_ROWS, generate_track
from bakeoff.players import fly
from bakeoff.players.base import Player
from bakeoff.players.solver import solve_depths
from bakeoff.senses import (LOOMING_FALLOFF, LOOMING_GAIN_HZ, LOOMING_STEP_HZ, MAX_HZ, WINDOW, compute_senses,
                            ground_truth, looming_rates)

SCHEMA_VERSION = 1
FALLBACK_ACTION = "stay"  # never the solver's move: a rescue would hide what we want to see


def _version(package: str) -> str | None:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def _git(*args: str) -> str | None:
    """Run git in the package's directory, so the answer does not depend on where the CLI started."""
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True,
                              cwd=Path(__file__).resolve().parent).stdout.strip()
    except Exception:
        return None


def _git_sha() -> str | None:
    return _git("rev-parse", "HEAD")


def _git_dirty() -> bool | None:
    status = _git("status", "--porcelain")
    return None if status is None else bool(status)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _close(player: Player) -> None:
    """Players that hold resources (fly brain, API clients) may define close(). A failing
    close() must not mask an exception that is already propagating."""
    close = getattr(player, "close", None)
    if close is None:
        return
    try:
        close()
    except Exception:
        pass


def _preflight(players: list[Player]) -> None:
    """Players may define preflight(): a check that they can start at all. It runs before the run
    directory exists, so a usage error (no fly data, no key) leaves nothing behind."""
    for player in players:
        check = getattr(player, "preflight", None)
        if check is None:
            continue
        try:
            check()
        except (OSError, ValueError) as e:
            raise PreflightError(f"{player.name}: {e}") from e


class Runner:
    def __init__(self, out_root: Path | str = "runs", max_consecutive_errors: int = 5):
        self.out_root = Path(out_root)
        self.max_consecutive_errors = max_consecutive_errors
        # Deliberately counts consecutive errors across seeds and players within one run()
        # call: a whole-run circuit breaker, not a per-seed one.
        self._error_streak = 0

    def run_seed(self, player: Player, seed: int, run_id: str, max_rows: int = MAX_ROWS,
                 sink: Callable[[dict], None] | None = None) -> list[dict]:
        track = generate_track(seed, max_rows=max_rows)
        game = Game(track)
        player.reset(game, seed)
        records: list[dict] = []
        while not game.over:
            senses = compute_senses(game)
            left_hz, right_hz = looming_rates(senses)
            truth = ground_truth(game)
            depths = solve_depths(senses)
            row, lane = game.row, game.lane
            decision = player.act(senses)
            invalid = decision.invalid or (
                decision.chosen_action is not None and decision.chosen_action not in ACTIONS)
            executed = FALLBACK_ACTION if decision.needs_fallback or invalid else decision.chosen_action
            game.step(executed)
            player.observe(executed)
            record = {
                "run_id": run_id, "player": player.name, "seed": seed, "row": row, "lane": lane,
                "senses": senses, "looming": {"left_hz": left_hz, "right_hz": right_hz},
                "questions": decision.questions, "answers": decision.answers,
                "chosen_action": decision.chosen_action, "executed_action": executed,
                "solver_action": max(depths, key=depths.get), "solver_depths": depths,
                "gated": decision.gated, "invalid": invalid, "error": decision.error,
                "ground_truth": truth, "alive": game.alive, "finished": game.finished, "death_cause": game.death_cause,
                "rows_survived": game.rows_survived, "latency_ms": decision.latency_ms,
                "usage": decision.usage, "cache_hit": decision.cache_hit, "info": decision.info,
                "track": track.to_json() if not records else None,
            }
            records.append(record)
            if sink is not None:
                sink(record)
            self._error_streak = self._error_streak + 1 if decision.error is not None else 0
            if self._error_streak > self.max_consecutive_errors:
                raise RunAborted(f"{self._error_streak} consecutive player errors; last: {decision.error}")
        return records

    def run(self, players: list[Player], seeds: Sequence[int], max_rows: int = MAX_ROWS,
            run_id: str | None = None, args: dict | None = None) -> Path:
        names = [p.name for p in players]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:  # two players would write the same <name>.jsonl
            raise ValueError(f"duplicate player names: {duplicates}")
        _preflight(players)
        run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
        run_dir = self.out_root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        meta_path = run_dir / "meta.json"
        meta = {
            "run_id": run_id, "schema_version": SCHEMA_VERSION, "git_sha": _git_sha(), "git_dirty": _git_dirty(),
            "started_at": _now(), "finished_at": None, "status": "running",
            "players": names, "seeds": list(seeds),
            "game": {"lanes": LANES, "max_rows": max_rows, "lookahead": LOOKAHEAD, "window": WINDOW,
                     "looming": {"gain_hz": LOOMING_GAIN_HZ, "falloff": LOOMING_FALLOFF, "step_hz": LOOMING_STEP_HZ,
                                 "max_hz": MAX_HZ, "provisional": not fly.CALIBRATED}},
            "fly": {"turn_threshold_hz": fly.TURN_THRESHOLD_HZ, "jump_threshold_hz": fly.JUMP_THRESHOLD_HZ,
                    "window_ms": WINDOW_MS, "provisional": not fly.CALIBRATED,
                    "model_commit": fly_data.MODEL_REPO_COMMIT, "annotations_commit": fly_data.ANNOTATIONS_COMMIT},
            "args": args or {}, "python": platform.python_version(),
            "versions": {pkg: _version(pkg) for pkg in ("brian2", "cython", "numpy", "typesafe-sdk", "anthropic")},
        }
        meta_path.write_text(json.dumps(meta, indent=2))
        self._error_streak = 0
        try:
            for player in players:
                try:
                    with open(run_dir / f"{player.name}.jsonl", "w") as f:
                        def sink(record: dict, f=f) -> None:
                            f.write(json.dumps(record) + "\n")
                            f.flush()

                        for seed in seeds:
                            self.run_seed(player, seed, run_id, max_rows=max_rows, sink=sink)
                finally:
                    _close(player)
        except RunAborted as abort:
            meta["status"] = abort.status
            raise
        except BaseException:
            meta["status"] = "interrupted"
            raise
        else:
            meta["status"] = "completed"
        finally:
            meta["finished_at"] = _now()
            meta_path.write_text(json.dumps(meta, indent=2))
        return run_dir

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
from bakeoff.game.rules import Rules, resolve
from bakeoff.game.track import generate_track
from bakeoff.players import fly
from bakeoff.players.base import Player
from bakeoff.players.solver import solve_depths
from bakeoff.senses import (LOOMING_FALLOFF, LOOMING_GAIN_HZ, LOOMING_STEP_HZ, MAX_HZ, compute_senses,
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


def _requests(players: list[Player]) -> dict:
    """Live requests spent against each paid player's cap (failed requests included). In a `bakeoff live`
    session the cap belongs to the session, so `max` here is what was left of it when this run began,
    while `args.max_requests` is the cap the command set: a second run of a session shows the smaller
    number, and `used` is always what this run alone spent."""
    return {p.name: {"max": p.budget.max_requests, "used": p.budget.used}
            for p in players if getattr(p, "budget", None) is not None}


def play_row(player: Player, game: Game, seed: int, run_id: str, first: bool) -> dict:
    """One decision and one move: asks the player, applies the fallback rule, steps the game and
    returns the step record. The runner and the live loop both build their records here, so a
    live run's log is a normal log. `first`: the episode's first record carries the track."""
    senses = compute_senses(game)
    left_hz, right_hz = looming_rates(senses)
    truth = ground_truth(game)
    depths = solve_depths(senses, game.track.rules.window)
    row, lane = game.row, game.lane
    decision = player.act(senses)
    invalid = decision.invalid or (
        decision.chosen_action is not None and decision.chosen_action not in ACTIONS)
    executed = FALLBACK_ACTION if decision.needs_fallback or invalid else decision.chosen_action
    game.step(executed)
    player.observe(executed)
    return {
        "run_id": run_id, "player": player.name, "seed": seed, "row": row, "lane": lane,
        "senses": senses, "looming": {"left_hz": left_hz, "right_hz": right_hz},
        "questions": decision.questions, "answers": decision.answers,
        "chosen_action": decision.chosen_action, "executed_action": executed,
        "solver_action": max(depths, key=depths.get), "solver_depths": depths,
        "gated": decision.gated, "invalid": invalid, "error": decision.error,
        "ground_truth": truth, "alive": game.alive, "finished": game.finished, "death_cause": game.death_cause,
        "rows_survived": game.rows_survived, "latency_ms": decision.latency_ms,
        "usage": decision.usage, "cache_hit": decision.cache_hit, "info": decision.info,
        "track": game.track.to_json() if first else None,
    }


def new_meta(run_id: str, players: list[Player], seeds: Sequence[int], rules: Rules, args: dict | None) -> dict:
    """meta.json as a run starts: status `running`, no finish time yet."""
    return {
        "run_id": run_id, "schema_version": SCHEMA_VERSION, "git_sha": _git_sha(), "git_dirty": _git_dirty(),
        "started_at": _now(), "finished_at": None, "status": "running",
        "players": [p.name for p in players], "seeds": list(seeds),
        "game": {**rules.to_json(),
                 "looming": {"gain_hz": LOOMING_GAIN_HZ, "falloff": LOOMING_FALLOFF, "step_hz": LOOMING_STEP_HZ,
                             "max_hz": MAX_HZ, "provisional": not fly.CALIBRATED}},
        "fly": {"turn_threshold_hz": fly.TURN_THRESHOLD_HZ, "jump_threshold_hz": fly.JUMP_THRESHOLD_HZ,
                "window_ms": WINDOW_MS, "provisional": not fly.CALIBRATED,
                "model_commit": fly_data.MODEL_REPO_COMMIT, "annotations_commit": fly_data.ANNOTATIONS_COMMIT},
        "models": {p.name: p.model for p in players if getattr(p, "model", None)},
        "requests": _requests(players),
        "args": args or {}, "python": platform.python_version(),
        "versions": {pkg: _version(pkg) for pkg in ("brian2", "cython", "numpy", "typesafe-sdk", "anthropic",
                                                     "python-dotenv")},
    }


class Runner:
    def __init__(self, out_root: Path | str = "runs", max_consecutive_errors: int = 5):
        self.out_root = Path(out_root)
        self.max_consecutive_errors = max_consecutive_errors
        # Deliberately counts consecutive errors across seeds and players within one run()
        # call: a whole-run circuit breaker, not a per-seed one.
        self._error_streak = 0

    def run_seed(self, player: Player, seed: int, run_id: str, rules: Rules | None = None, max_rows: int | None = None,
                 sink: Callable[[dict], None] | None = None) -> list[dict]:
        track = generate_track(seed, rules, max_rows)
        game = Game(track)
        player.reset(game, seed)
        records: list[dict] = []
        while not game.over:
            record = play_row(player, game, seed, run_id, first=not records)
            records.append(record)
            if sink is not None:
                sink(record)
            self._error_streak = self._error_streak + 1 if record["error"] is not None else 0
            if self._error_streak > self.max_consecutive_errors:
                raise RunAborted(f"{self._error_streak} consecutive player errors; last: {record['error']}")
        return records

    def run(self, players: list[Player], seeds: Sequence[int], rules: Rules | None = None, max_rows: int | None = None,
            run_id: str | None = None, args: dict | None = None) -> Path:
        rules = resolve(rules, max_rows)
        names = [p.name for p in players]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:  # two players would write the same <name>.jsonl
            raise ValueError(f"duplicate player names: {duplicates}")
        _preflight(players)
        run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
        run_dir = self.out_root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        meta_path = run_dir / "meta.json"
        meta = new_meta(run_id, players, seeds, rules, args)
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
                            self.run_seed(player, seed, run_id, rules, sink=sink)
                finally:
                    _close(player)
        except RunAborted as abort:
            meta["status"] = abort.status
            raise
        except KeyboardInterrupt:
            meta["status"] = "interrupted"
            raise
        except BaseException as e:  # our bug: a crash is not someone pressing Ctrl-C
            meta["status"], meta["error"] = "crashed", f"{type(e).__name__}: {e}"
            raise
        else:
            meta["status"] = "completed"
        finally:
            meta["finished_at"] = _now()
            meta["requests"] = _requests(players)
            meta_path.write_text(json.dumps(meta, indent=2))
        return run_dir

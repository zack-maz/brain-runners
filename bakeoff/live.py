"""`bakeoff live`: the minds play one track in real time, in lockstep by row, and every decision is
written to a normal run directory and sent to the page as it happens.

`Broadcast` holds the events so far, for any number of listeners; `LiveRun` is the lockstep loop."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Iterator

from bakeoff.errors import RunAborted
from bakeoff.game.engine import Game
from bakeoff.game.track import MAX_ROWS, generate_track
from bakeoff.players.base import Player
from bakeoff.replay import META_KEYS, REPLAY_VERSION, build_replay, frame_of, summary_of
from bakeoff.report import COLUMNS
from bakeoff.runner import _close, _now, _preflight, _requests, new_meta, play_row

MAX_CONSECUTIVE_ERRORS = 5  # as the runner: a provider that keeps failing ends the run


class Broadcast:
    """Every event of the run, in order. A listener gets the history first and then waits for more,
    so a page that connects late, or reconnects, misses nothing. Thread-safe."""

    def __init__(self):
        self._events: list[tuple[str, dict]] = []
        self._changed = threading.Condition()
        self.closed = False
        self.listeners = 0

    def emit(self, name: str, data: dict) -> None:
        # a snapshot: the run goes on changing its own objects (an episode's list of question sets grows),
        # and what was sent must not change under a listener that is still serialising it
        snapshot = json.loads(json.dumps(data))
        with self._changed:
            self._events.append((name, snapshot))
            self._changed.notify_all()

    def close(self) -> None:
        with self._changed:
            self.closed = True
            self._changed.notify_all()

    def wait_for_listener(self, timeout: float | None = None) -> bool:
        with self._changed:
            return self._changed.wait_for(lambda: self.listeners > 0 or self.closed, timeout)

    def listen(self, poll_seconds: float = 15.0) -> Iterator[tuple[str, dict] | None]:
        """Yields (name, data); None when nothing happened for `poll_seconds` (time for a keep-alive).
        Ends after the last event once the broadcast is closed."""
        sent = 0
        with self._changed:
            self.listeners += 1
            self._changed.notify_all()
        try:
            while True:
                with self._changed:
                    if sent >= len(self._events) and not self.closed:
                        self._changed.wait(poll_seconds)
                    batch, done = self._events[sent:], self.closed
                if not batch and done:
                    return
                if not batch:
                    yield None
                for event in batch:
                    yield event
                sent += len(batch)
        finally:  # the page was closed, or the run is over
            with self._changed:
                self.listeners -= 1


class LiveRun:
    """One track, every player on it at once. Each tick every player that stands on this row decides;
    a jumper stands two rows on and skips the next tick; the slowest mind sets the pace. Records are
    the runner's own (`play_row`), so the directory is a normal run and `bakeoff view` plays it."""

    def __init__(self, players: list[Player], seed: int, out_root: Path | str = "runs", max_rows: int = MAX_ROWS,
                 run_id: str | None = None, args: dict | None = None, broadcast: Broadcast | None = None):
        names = [p.name for p in players]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"duplicate player names: {duplicates}")
        self.players, self.seed, self.max_rows = players, seed, max_rows
        self.run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
        self.run_dir = Path(out_root) / self.run_id
        self.args = args or {}
        self.broadcast = broadcast if broadcast is not None else Broadcast()
        self.status = "running"
        self.error: str | None = None  # why the run stopped early, when a cap or a failing provider stopped it
        self.meta: dict | None = None

    def prepare(self) -> dict:
        """Preflight, the run directory and meta.json. Returns the empty replay the page starts from."""
        _preflight(self.players)
        self.run_dir.mkdir(parents=True, exist_ok=False)
        self.meta = new_meta(self.run_id, self.players, [self.seed], self.max_rows, self.args)
        self._write_meta()
        return {"replay_version": REPLAY_VERSION,
                "runs": [{"run_id": self.run_id, **{k: self.meta.get(k) for k in META_KEYS}}],
                "players": [], "seeds": [self.seed], "tracks": {}, "episodes": [],
                "scoreboard": {"columns": ["run_id", *COLUMNS], "rows": [], "same_seeds": True}}

    def cancel(self) -> None:
        """The operator gave up before the run began (Ctrl-C while waiting for a browser)."""
        self.status = "interrupted"
        self.meta.update(status=self.status, finished_at=_now())
        self._write_meta()
        self.broadcast.close()

    def _write_meta(self) -> None:
        (self.run_dir / "meta.json").write_text(json.dumps(self.meta, indent=2))

    def run(self) -> Path:
        if self.meta is None:
            self.prepare()
        track = generate_track(self.seed, max_rows=self.max_rows)
        games = {p.name: Game(track) for p in self.players}
        questions: dict[str, list[dict]] = {p.name: [] for p in self.players}
        started: set[str] = set()
        logs = {p.name: open(self.run_dir / f"{p.name}.jsonl", "w") for p in self.players}
        streak = 0
        try:
            for player in self.players:
                player.reset(games[player.name], self.seed)
            row = 0
            while not all(game.over for game in games.values()):
                for player in self.players:
                    game = games[player.name]
                    if game.over or game.row != row:
                        continue  # fallen, finished, or in the air over this row
                    record = play_row(player, game, self.seed, self.run_id, first=player.name not in started)
                    logs[player.name].write(json.dumps(record) + "\n")
                    logs[player.name].flush()
                    frame = frame_of(record, track.lanes, questions[player.name])
                    if player.name not in started:
                        started.add(player.name)
                        self.broadcast.emit("episode", {
                            "episode": {"player": player.name, "seed": self.seed, "run_id": self.run_id,
                                        "complete": False, "finished": False, "death_cause": None, "rows_survived": 0,
                                        "max_rows": self.max_rows, "questions": questions[player.name]},
                            "track": track.to_json()})
                    self.broadcast.emit("frame", {"player": player.name, "seed": self.seed, "frame": frame,
                                                  "summary": summary_of(record)})
                    streak = streak + 1 if record["error"] is not None else 0
                    if streak > MAX_CONSECUTIVE_ERRORS:
                        raise RunAborted(f"{streak} consecutive player errors; last: {record['error']}")
                row += 1
            self.status = "completed"
        except RunAborted as abort:  # a cap was reached (budget_exhausted) or a provider kept failing
            self.status, self.error = abort.status, str(abort)
            self.broadcast.emit("error", {"message": self.error})
        except BaseException as e:  # Ctrl-C, or our bug: the directory is still a valid, incomplete run
            self.status = "interrupted"
            if not isinstance(e, KeyboardInterrupt):
                raise
        finally:
            for log in logs.values():
                log.close()
            for player in self.players:
                _close(player)
            self.meta.update(status=self.status, finished_at=_now(), requests=_requests(self.players))
            self._write_meta()
            replay = build_replay([self.run_dir])
            self.broadcast.emit("end", {"status": self.status, "runs": replay["runs"], "scoreboard": replay["scoreboard"]})
            self.broadcast.close()
        return self.run_dir

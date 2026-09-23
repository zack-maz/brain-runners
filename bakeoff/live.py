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
from bakeoff.game.rules import Rules, resolve
from bakeoff.game.track import generate_track
from bakeoff.players.base import Player
from bakeoff.replay import META_KEYS, build_replay, empty_replay, frame_of, summary_of
from bakeoff.runner import _close, _now, _preflight, _requests, new_meta, play_row

MAX_CONSECUTIVE_ERRORS = 5  # as the runner: a provider that keeps failing ends the run


class Cancelled(Exception):
    """`stop()` was called: the operator, or the page, gave up on a run that had begun."""


class Broadcast:
    """Every event of the run, in order. A listener gets the history first and then waits for more,
    so a page that connects late, or reconnects, misses nothing. Thread-safe."""

    def __init__(self):
        self._events: list[tuple[str, dict]] = []
        self._changed = threading.Condition()
        self.closed = False
        self.abandoned = False  # nobody is coming: stop waiting for a browser
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

    def abandon(self) -> None:
        """Nobody is coming (the run was cancelled before it began): wake whoever waits for a browser.
        Not `close()`: the run still has a directory to close and a last event to send."""
        with self._changed:
            self.abandoned = True
            self._changed.notify_all()

    def wait_for_listener(self, timeout: float | None = None) -> bool:
        with self._changed:
            return self._changed.wait_for(lambda: self.listeners > 0 or self.closed or self.abandoned, timeout)

    def forget(self) -> None:
        """Drop the history of a run that is over. A session plays run after run and each history is
        every frame of a track; only the run on screen can still be asked for."""
        with self._changed:
            if self.closed:
                self._events = []

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

    def __init__(self, players: list[Player], seed: int, out_root: Path | str = "runs", rules: Rules | None = None,
                 max_rows: int | None = None, run_id: str | None = None, args: dict | None = None,
                 broadcast: Broadcast | None = None):
        names = [p.name for p in players]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"duplicate player names: {duplicates}")
        self.players, self.seed, self.rules = players, seed, resolve(rules, max_rows)
        self.run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
        self.run_dir = Path(out_root) / self.run_id
        self.args = args or {}
        self.broadcast = broadcast if broadcast is not None else Broadcast()
        self.status = "running"
        self.replay: dict | None = None  # the empty replay a page starts from, filled by prepare()
        self._stop = threading.Event()
        self.error: str | None = None  # why the run stopped early, when a cap or a failing provider stopped it
        self.meta: dict | None = None

    def prepare(self) -> dict:
        """Preflight, the run directory and meta.json. Returns the empty replay the page starts from."""
        _preflight(self.players)
        self.run_dir.mkdir(parents=True, exist_ok=False)
        self.meta = new_meta(self.run_id, self.players, [self.seed], self.rules, self.args)
        self._write_meta()
        self.replay = {**empty_replay(self.rules), "seeds": [self.seed],
                       "runs": [{"run_id": self.run_id, **{k: self.meta.get(k) for k in META_KEYS}}]}
        return self.replay

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

    def stop(self) -> None:
        """Ask a run that has begun to stop. It is checked between decisions, so a decision already
        in flight (a paid request) is finished and recorded first; the run then closes as a normal
        run directory with status `interrupted`. A run that has not begun (it is waiting for a browser)
        is woken, so it closes at once instead of waiting for a page that will never come."""
        self._stop.set()
        self.broadcast.abandon()

    def cancel(self) -> None:
        """The run was given up before it began (Ctrl-C, or Cancel, while waiting for a browser). It
        ends like any other run: the same `end` event, so a page that is watching stops waiting and
        goes back to its lobby instead of reconnecting to a stream that will never say anything."""
        self.status = "interrupted"
        self.meta.update(status=self.status, finished_at=_now())
        self._write_meta()
        replay = build_replay([self.run_dir])  # the same last event as a run that played: read from disk
        self.broadcast.emit("end", {"status": self.status, "runs": replay["runs"], "scoreboard": replay["scoreboard"]})
        self.broadcast.close()

    def _write_meta(self) -> None:
        (self.run_dir / "meta.json").write_text(json.dumps(self.meta, indent=2))

    def run(self) -> Path:
        if self.meta is None:
            self.prepare()
        track = generate_track(self.seed, self.rules)
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
                    if self._stop.is_set():
                        raise Cancelled("cancelled")
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
                                        "max_rows": track.max_rows, "questions": questions[player.name]},
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
        except Cancelled:  # the page pressed cancel, or the operator did
            self.status = "interrupted"
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

"""The session behind `bakeoff live`: what the page is allowed to start, and what it costs.

One session per command. It holds the ceiling the command set (one `RequestBudget` per paid player
for the whole session, never raised by anything the page sends), and it runs at most one `LiveRun`
at a time. The page asks it what can be run (`state`), starts a run (`start`) and stops it
(`cancel`); every refusal names its reason.
"""

from __future__ import annotations

import json
import re
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from bakeoff.clients.core import DiskCache, RequestBudget, SharedBudget
from bakeoff.game.rules import Rules
from bakeoff.game.track import generate_track
from bakeoff.live import LiveRun
from bakeoff.players import PAID, REGISTRY, fly2, make_player
from bakeoff.players.names import canonical
from bakeoff.replay import CONTESTANTS

# tournament seeds are below this and must not be paid for, or shape prompts, before the tournament
FIRST_PRACTICE_SEED = 1000

# USD per live request, measured in docs/COSTS.md (update 2a) and rounded up, because this number is what
# the page asks the user to agree to: it must never be lower than what a request really costs. A price per
# player, not per provider: the same model costs what its question set makes it read and write, and the
# map set is about eleven times the plain one's. The budget, not this table, enforces the ceiling.
# Jev's prices are estimates (its provider does not bill per request; COSTS.md explains the token basis).
# GLM Flash is free while its free tier lasts.
PRICE_USD = {"haiku_plain": 0.0006, "haiku_step1": 0.0010, "haiku_guided": 0.0009, "haiku_step2": 0.0016,
             "haiku_map": 0.0065, "jev_plain": 0.00004, "jev_step1": 0.00003, "jev_guided": 0.00004,
             "jev_step2": 0.00003, "jev_map": 0.00012,
             "glm_plain": 0.0, "glm_step1": 0.0, "glm_guided": 0.0, "glm_step2": 0.0, "glm_map": 0.0}

# every player here asks its provider once a row, so a track of N rows costs at worst N requests
REQUESTS_PER_ROW = 1

# what a run id looks like (a timestamp, and a counter when two runs start in one second): anything else the page
# sends as `run=` names no run, and no path is ever built from it
RUN_ID = re.compile(r"[0-9]{8}-[0-9]{6}(-[0-9]+)?")


def model_of(name: str) -> str | None:
    """The model a paid player asks, as its client asks for it. Nothing overrides it: no command takes a
    model, so this is what a run really uses, and the page says it rather than a name typed by hand."""
    client = getattr(REGISTRY.get(name), "client_class", None)
    return getattr(client, "default_model", None)


def _first_model(path: Path) -> str | None:
    """The model the first complete record in a log answered as. Only the first lines are read: every row of
    one episode is answered by the same model."""
    try:
        with path.open() as log:
            for line in log:
                try:
                    model = (json.loads(line).get("info") or {}).get("model")
                except (ValueError, AttributeError):
                    continue  # a truncated last line, or a record with no info
                if model:
                    return model
    except OSError:
        return None
    return None


def answered_models(out_root: Path | str) -> dict[str, str]:
    """Each player's model as it last answered, from the newest run that recorded it. Jev's client asks for
    `jev-latest`, so the version is only knowable from an answer; the page says this one rather than pin the
    client, which would change the cache key and orphan every answer already paid for. One pass, newest run
    first, reading only the head of each log."""
    models: dict[str, str] = {}
    for run_dir in sorted(Path(out_root).glob("*/"), reverse=True):
        for path in sorted(run_dir.glob("*.jsonl")):
            player = canonical(path.stem)
            if player in models:
                continue  # a newer run has already answered for it
            model = _first_model(path)
            if model:
                models[player] = model
    return models


def about_of(name: str) -> str | None:
    """What a fly is, for its tick in the lobby; the grid's rows and columns say it for everyone else.
    fly2 shows a neutral line while it is not calibrated, instead of a provisional mapping's summary as if
    it had already won."""
    if name == "fly2":
        return (fly2.about() if fly2.CALIBRATED
                else "not calibrated yet: its input, read-out and numbers are fixed by calibration/FLY2_REPORT.md")
    return {"fly": "looming \u2192 escape reflex (phase 2)"}.get(name)


def _order(names) -> list[str]:
    """The contestants first, in the page's own order, then the free yardsticks."""
    rest = sorted(set(names) - set(CONTESTANTS))
    return [name for name in CONTESTANTS if name in names] + rest


class LobbyError(Exception):
    """The page asked for something the session will not do. The message is shown to the user."""


@dataclass
class Started:
    """What `start` gives back: the run and the empty replay the page resets itself from."""

    run: LiveRun
    replay: dict


def played_before(out_root: Path | str, game_version: str) -> dict[str, list[int]]:
    """(player, seed) pairs already recorded under this game version, from the run directories'
    `meta.json`. Their answers are in the response cache, so replaying them spends nothing. Coarse:
    a player that died on row 3 of a track is listed for it, and only the rows it reached are cached."""
    played: dict[str, set[int]] = {}
    for meta_path in sorted(Path(out_root).glob("*/meta.json")):
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            continue  # a half-written or unreadable directory tells us nothing
        if (meta.get("game") or {}).get("version") != game_version:
            continue  # another game is another set of questions, so another set of cached answers
        for player in meta.get("players") or []:  # an old name (decisions 39 and 44) counts as the new one
            played.setdefault(canonical(player), set()).update(meta.get("seeds") or [])
    return {player: sorted(seeds) for player, seeds in played.items()}


class LiveSession:
    """The command's ceiling and the page's lobby. Thread-safe: the run loop is a thread of its own."""

    def __init__(self, rules: Rules, out_root: Path | str = "runs", cache_dir: Path | str = ".cache/responses",
                 max_requests: int = 0, tournament: bool = False, args: dict | None = None,
                 token: str | None = None, paid_blocked: str | None = None,
                 ready: tuple[int, list[str]] | None = None):
        self.rules, self.out_root, self.cache = rules, Path(out_root), DiskCache(cache_dir)
        self.max_requests, self.tournament = max_requests, tournament
        # why no paid player may play at all this session, if any (a vision the briefing does not match)
        self.paid_blocked = paid_blocked
        # what the command line offered: the lobby opens with this track and these players ticked
        self.ready_seed, self.ready_players = ready or (FIRST_PRACTICE_SEED + 1, [])
        self.args = args or {}
        self.token = token or secrets.token_urlsafe(16)
        # one budget per paid player for the whole session: the command's cap is per player per session,
        # so a second run from the page spends what the first one left
        self.budgets: dict[str, RequestBudget] = {name: RequestBudget(max_requests) for name in PAID}
        self.run: LiveRun | None = None
        self.finished: list[LiveRun] = []
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # ---- what can be run ---------------------------------------------------------------------
    @property
    def status(self) -> str:
        if self.run is None:
            return "lobby"
        # `run.status` can say "completed" before the run's thread has finished closing its players
        # (live.py's `finally`); treat that gap as still running too, so a new run cannot start into it.
        thread_alive = self._thread is not None and self._thread.is_alive()
        return "running" if self.run.status == "running" or thread_alive else "finished"

    def state(self, seed: int | None = None) -> dict:
        """Everything the lobby needs: the players with their price and their budget, the seed rule,
        the game, and what is happening now."""
        played = played_before(self.out_root, self.rules.version)
        answered = answered_models(self.out_root)
        players = []
        for name in _order(REGISTRY):
            paid = name in PAID
            players.append({
                "name": name, "paid": paid, "about": about_of(name),
                "price_usd": PRICE_USD.get(name) if paid else 0.0,
                "model": model_of(name) if paid else None,
                # what it answered as last: the asked-for name may be a moving one (`jev-latest`)
                "model_answered": answered.get(name) if paid else None,
                "requests_left": self.budgets[name].remaining if paid else None,
                "played_before": seed is not None and seed in played.get(name, []),
                # the track select's own practice tracks it has a recorded run of, for its marks: a
                # tournament seed or a bulk-run seed past the track select's own 20 is not offered there
                "seeds_played": [s for s in played.get(name, [])
                                 if FIRST_PRACTICE_SEED <= s < FIRST_PRACTICE_SEED + 20],
                # why this player cannot play this track, so the page can say so before anything is asked
                "why_not": None if seed is None else self.why_not(name, seed),
            })
        run = self.run
        return {
            "status": self.status,
            "game": self.rules.to_json(), "max_rows": self.rules.max_rows,
            "requests_per_row": REQUESTS_PER_ROW,
            "max_requests": self.max_requests, "tournament": self.tournament,
            "first_practice_seed": FIRST_PRACTICE_SEED,
            "seed": seed,
            # the real track, for the track select's preview: the rules stay in Python. A tournament seed
            # is locked until the session is one, same as `why_not` locks paid players off it
            "track": None if seed is None or (seed < FIRST_PRACTICE_SEED and not self.tournament)
                     else generate_track(seed, self.rules).to_json(),
            "ready": {"seed": self.ready_seed, "players": list(self.ready_players)},
            "players": players,
            # `replay` is the empty replay of this run: the page resets itself to it and fills it from
            # the event stream, whether the page started the run or the command line did (--start)
            "run": None if run is None else {"run_id": run.run_id, "run_dir": str(run.run_dir),
                                             "seed": run.seed, "players": [p.name for p in run.players],
                                             "status": run.status, "error": run.error, "replay": run.replay},
        }

    # ---- starting and stopping ---------------------------------------------------------------
    def why_not(self, name: str, seed: int) -> str | None:
        """Why this player may not play this track, or None. The one place that rule lives: `check`
        refuses with it and `state` shows it."""
        if name == "fly2" and not fly2.CALIBRATED:
            return "fly2 is not calibrated yet (calibration/FLY2_REPORT.md)"
        if name not in PAID:
            return None
        if self.paid_blocked:
            return self.paid_blocked
        if seed < FIRST_PRACTICE_SEED and not self.tournament:
            return (f"paid players may not play seeds below {FIRST_PRACTICE_SEED} (tournament seeds); "
                    "this command was not started with --tournament")
        if self.max_requests > 0 and self.budgets[name].remaining == 0:
            return f"{name} has no requests left of this session's cap of {self.max_requests}"
        return None

    def check(self, seed: int, names: list[str]) -> None:
        """Raises `LobbyError` naming the first reason this run will not be started."""
        if self.status == "running":
            raise LobbyError("a run is already going; cancel it first")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise LobbyError("the track must be a whole number")
        if seed < 0:
            raise LobbyError("the track must not be negative")
        if not names:
            raise LobbyError("choose at least one player")
        names = [canonical(n) for n in names]  # an old llm* name from a saved link still works
        unknown = [n for n in names if n not in REGISTRY]
        if unknown:
            raise LobbyError(f"unknown player {unknown[0]!r}; choose from {sorted(REGISTRY)}")
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise LobbyError(f"duplicate player names: {duplicates}")
        refused = [self.why_not(name, seed) for name in names]
        if any(refused):
            raise LobbyError(next(reason for reason in refused if reason))
        for name in names:  # a question set that cannot be asked on this vision, before anyone plays
            question_set = getattr(REGISTRY[name], "question_set", None)
            if question_set is not None:
                try:
                    question_set.build(self.rules)
                except ValueError as e:
                    raise LobbyError(f"{name}: {e}") from e

    def start(self, seed: int, names: list[str], wait_for_page: bool = False) -> Started:
        """Validates, builds the players on the session's budgets, prepares the run directory and
        plays it in a thread. Returns the run and the empty replay the page starts from.
        `wait_for_page`: hold the first decision until a browser is listening (`bakeoff live --start`;
        a run the page itself started needs no wait, since the stream carries its history)."""
        with self._lock:
            self.check(seed, names)
            for old in self.finished:  # a session plays run after run; only the newest is still watched
                old.broadcast.forget()
            players = self._players(names)
            run = LiveRun(players, seed, out_root=self.out_root, rules=self.rules, run_id=self._run_id(),
                          args={**self.args, "seed": seed, "players": ",".join(names)})
            replay = run.prepare()  # the directory and meta.json: a failure here starts nothing
            self.run = run
            self._thread = threading.Thread(target=self._play, args=(run, wait_for_page), daemon=True)
            self._thread.start()
            return Started(run, replay)

    def _run_id(self) -> str:
        """The usual timestamp, with a counter when a session plays two runs in the same second."""
        stamp = run_id = time.strftime("%Y%m%d-%H%M%S")
        nth = 1
        while (self.out_root / run_id).exists():
            nth += 1
            run_id = f"{stamp}-{nth}"
        return run_id

    def _play(self, run: LiveRun, wait_for_page: bool = False) -> None:
        try:
            if wait_for_page:
                run.broadcast.wait_for_listener()
            if run.stopped:  # cancelled while it waited: the directory closes without a decision
                run.cancel()
            else:
                run.run()
        finally:
            self.finished.append(run)

    def _players(self, names: list[str]) -> list:
        players = []
        for name in names:
            if name in PAID:
                # a view of the session's budget: it spends from the session's cap but a run's meta.json
                # records only what that run spent, against what it could have spent
                players.append(make_player(name, cache=self.cache, budget=SharedBudget(self.budgets[name])))
            else:
                players.append(make_player(name))
        return players

    # ---- what was recorded -----------------------------------------------------------------------
    def run_dir_of(self, run_id: str | None) -> Path | None:
        """The directory of a recorded run, or None. Only a run id of the usual shape that names a directory
        directly under `out_root` holding a meta.json: nothing the page sends becomes any other path."""
        if not run_id or not RUN_ID.fullmatch(run_id):
            return None
        run_dir = self.out_root / run_id
        return run_dir if (run_dir / "meta.json").is_file() else None

    def results(self, run_id: str | None) -> dict | None:
        """The results screen's numbers for a recorded run (bakeoff/results.py), or None for no such run."""
        from bakeoff.results import results_of  # numpy: only when asked

        run_dir = self.run_dir_of(run_id)
        return None if run_dir is None else results_of(run_dir)

    def replay(self, run_id: str | None) -> dict | None:
        """The replay of a recorded run, for Records' Watch, or None for no such run."""
        from bakeoff.replay import build_replay

        run_dir = self.run_dir_of(run_id)
        return None if run_dir is None else build_replay([run_dir])

    def records(self) -> dict:
        """The records screen's numbers (bakeoff/records.py). Reads every run directory, so it is worked out when
        the page asks, never on a timer."""
        from bakeoff.records import records_of

        current = self.run.run_id if self.run is not None and self.status == "running" else None
        return records_of(self.out_root, self.rules, current=current)

    def find(self, run_id: str | None) -> LiveRun | None:
        """The run with this id, whether it is still going or already closed; without an id, the
        run going now (or the last one). The page opens one event stream per run and names it."""
        if not run_id:
            return self.run
        return next((run for run in [*self.finished, self.run] if run is not None and run.run_id == run_id), None)

    def cancel(self) -> None:
        """Stop the run that is going. It closes as a normal run directory with status `interrupted`."""
        with self._lock:  # the same lock `start` holds, so a cancel cannot cross a run beginning
            run = self.run
            if run is None or run.status != "running":
                raise LobbyError("no run is going")
            run.stop()

    def wait(self, timeout: float | None = None) -> None:
        """Waits for the run that is going, if any (the command's own thread does this)."""
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

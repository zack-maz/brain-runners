"""Game state and rules. Pure: no I/O, no randomness."""

from __future__ import annotations

from bakeoff.game.track import Track, start_lane

ACTIONS = ("left", "right", "jump", "stay")
DEATH_CAUSES = {"stay": "ran_into_gap", "jump": "jumped_into_gap",
                "left": "dodged_into_gap", "right": "dodged_into_gap"}


class Game:
    def __init__(self, track: Track):
        self.track = track
        self.row = 0
        self.lane = start_lane(track.lanes)
        self.alive = True
        self.death_cause: str | None = None
        self._cleared = 0

    @property
    def finished(self) -> bool:
        return self.alive and self.row >= self.track.max_rows

    @property
    def over(self) -> bool:
        return not self.alive or self.finished

    @property
    def rows_survived(self) -> int:
        return min(self._cleared, self.track.max_rows)

    def step(self, action: str) -> None:
        if action not in ACTIONS:
            raise ValueError(f"unknown action {action!r}; choose from {ACTIONS}")
        if self.over:
            raise RuntimeError("the run is over")
        advance = 2 if action == "jump" else 1
        lane = (self.lane + {"left": -1, "right": 1}.get(action, 0)) % self.track.lanes
        row = self.row + advance
        # a jump from max_rows - 1 lands past the finish line, where nothing can kill the runner
        if row <= self.track.max_rows and self.track.is_gap(row, lane):
            self.alive = False
            self.death_cause = DEATH_CAUSES[action]
            self._cleared = row - 1  # a fatal jump still cleared the row it flew over
            return
        self.row, self.lane, self._cleared = row, lane, row

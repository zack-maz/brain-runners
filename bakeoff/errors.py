"""Exceptions that end a run. A module of their own, so a paid client can raise them without importing the runner."""

from __future__ import annotations


class RunAborted(Exception):
    """Ends one player's part of a run: a cap reached, or a provider that keeps failing. That player drops out and
    the others play on; the run itself ends this way only when every player has stopped."""

    status = "aborted"  # a subclass may set a more specific status
    seed: int | None = None  # where the player stopped, set by whoever plays it
    row: int | None = None

    def stopped(self) -> dict:
        """What `meta.json` records of a player that dropped out."""
        return {"status": self.status, "reason": str(self), "seed": self.seed, "row": self.row}


class BudgetExhausted(RunAborted):
    """Raised by a paid client when its hard request cap is reached."""

    status = "budget_exhausted"


class PreflightError(ValueError):
    """A player cannot start (fly data missing, key missing). Raised before the run directory exists."""

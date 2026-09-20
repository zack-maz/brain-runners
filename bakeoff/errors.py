"""Exceptions that end a run. A module of their own, so a paid client can raise them without importing the runner."""

from __future__ import annotations


class RunAborted(Exception):
    status = "aborted"  # a subclass may set a more specific status


class BudgetExhausted(RunAborted):
    """Raised by a paid client when its hard request cap is reached."""

    status = "budget_exhausted"


class PreflightError(ValueError):
    """A player cannot start (fly data missing, key missing). Raised before the run directory exists."""

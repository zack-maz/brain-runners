"""Step logs -> scoreboard. Reads files only."""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

COLUMNS = ("player", "runs", "incomplete", "mean_rows", "median_rows", "finished",
           "ran_into_gap", "jumped_into_gap", "dodged_into_gap", "solver_agreement",
           "fallback_rate", "invalid_rate", "error_rate",
           "requests", "mean_latency_ms", "input_tokens", "output_tokens")


def load_steps(run_dir: Path | str) -> list[dict]:
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise FileNotFoundError(f"no such run directory: {run_dir}")
    steps = []
    for path in sorted(run_dir.glob("*.jsonl")):
        lines = [line for line in path.read_text().splitlines() if line.strip()]
        for number, line in enumerate(lines):
            try:
                steps.append(json.loads(line))
            except json.JSONDecodeError:
                if number != len(lines) - 1:
                    raise
                # a run killed mid-write leaves a truncated last line; the rest is still good
    return steps


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _summarize_player(player: str, steps: list[dict]) -> dict:
    runs = defaultdict(list)
    for s in steps:
        runs[s["seed"]].append(s)
    finals = [max(run, key=lambda s: s["row"]) for run in runs.values()]
    # A run cut off mid-way (abort, budget stop, Ctrl-C) is incomplete, not a death.
    complete = [f for f in finals if f["finished"] or not f["alive"]]
    rows = [f["rows_survived"] for f in complete]

    comparable = [s for s in steps if s["chosen_action"] is not None]
    live = [s for s in steps if s["latency_ms"] is not None and not s["cache_hit"]]
    usage = [s["usage"] or {} for s in live]

    return {
        "player": player, "runs": len(complete), "incomplete": len(finals) - len(complete),
        "mean_rows": _mean(rows), "median_rows": statistics.median(rows) if rows else None,
        "finished": sum(f["finished"] for f in complete),
        **{cause: sum(f["death_cause"] == cause for f in complete)
           for cause in ("ran_into_gap", "jumped_into_gap", "dodged_into_gap")},
        "solver_agreement": _ratio(sum(s["chosen_action"] == s["solver_action"] for s in comparable), len(comparable)),
        "fallback_rate": _ratio(sum(s["executed_action"] != s["chosen_action"] for s in steps), len(steps)),
        "invalid_rate": _ratio(sum(s["invalid"] for s in steps), len(steps)),
        "error_rate": _ratio(sum(s["error"] is not None for s in steps), len(steps)),
        "requests": len(live),
        "mean_latency_ms": _mean([s["latency_ms"] for s in live]),
        "input_tokens": sum(u.get("input_tokens") or 0 for u in usage),
        "output_tokens": sum(u.get("output_tokens") or 0 for u in usage),
    }


def summarize(steps: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for s in steps:
        groups[s["player"]].append(s)
    return [_summarize_player(player, group) for player, group in sorted(groups.items())]


def _fmt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def format_table(rows: list[dict]) -> str:
    lines = ["| " + " | ".join(COLUMNS) + " |", "| " + " | ".join("---" for _ in COLUMNS) + " |"]
    lines += ["| " + " | ".join(_fmt(row[c]) for c in COLUMNS) + " |" for row in rows]
    return "\n".join(lines)

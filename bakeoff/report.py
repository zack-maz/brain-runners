"""Step logs -> scoreboard. Reads files only."""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

from bakeoff.senses import truth_of

COLUMNS = ("player", "runs", "incomplete", "missing", "mean_rows", "median_rows", "finished",
           "ran_into_gap", "jumped_into_gap", "dodged_into_gap", "jump_share", "solver_agreement",
           "fallback_rate", "invalid_rate", "error_rate",
           "requests", "spent", "cache_hits", "mean_latency_ms", "input_tokens", "output_tokens", "cost_usd",
           "brier_gap_ahead", "brier_left_safe",
           "brier_gap_left", "brier_gap_stay", "brier_gap_right", "brier_gap_jump", "brier_all")

# USD per million tokens (input, output), by the model id in meta.json. Jev is absent: only a blended
# figure from its console is known (docs/COSTS.md), not an input and an output price, so its cost
# shows as "-", never as 0.
PRICES_USD_PER_MTOK = {"claude-haiku-4-5-20251001": (1.00, 5.00)}


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
            except json.JSONDecodeError as e:
                if number != len(lines) - 1:
                    raise ValueError(f"{path}: line {number + 1} is not valid JSON: {e}") from e
                # a run killed mid-write leaves a truncated last line; the rest is still good
    return steps


def load_meta(run_dir: Path | str) -> dict | None:
    """meta.json of a run, or None if it is absent or unreadable."""
    try:
        meta = json.loads((Path(run_dir) / "meta.json").read_text())
    except (OSError, ValueError):
        return None
    return meta if isinstance(meta, dict) else None


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _agrees(step: dict) -> bool:
    """The choice is as deep as the best move; ties with the solver's own pick count."""
    depths = step["solver_depths"]
    return step["chosen_action"] in depths and depths[step["chosen_action"]] == max(depths.values())


def _is_fallback(step: dict) -> bool:
    """A gated `stay` is a fallback even though executed equals chosen."""
    return bool(step["gated"] or step["invalid"] or step["error"] is not None or step["chosen_action"] is None)


def _cost_usd(model: str | None, input_tokens: int, output_tokens: int) -> float | None:
    if model not in PRICES_USD_PER_MTOK:
        return None
    per_input, per_output = PRICES_USD_PER_MTOK[model]
    return (input_tokens * per_input + output_tokens * per_output) / 1_000_000


def _truth(step: dict, noul: str) -> bool | None:
    """The logged `ground_truth` for the one-shot Jev's two Nouls. The question sets' Nouls (`gap_<action>`,
    `trapped_<action>`, `tile_r<row>_<side>`) ask what the senses show, so their truth is read from the
    record's senses (bakeoff.senses.truth_of)."""
    truth = (step.get("ground_truth") or {}).get(noul)
    if truth is None and step.get("senses"):
        truth = truth_of(step["senses"], noul)
    return truth


def _brier(steps: list[dict], noul: str | None) -> float | None:
    """Mean squared gap between a logged Noul probability and the truth (0 is perfect, 0.25 is what
    always answering 0.5 scores), for one Noul id, or for every Noul whose truth is known when `noul` is
    None. Cached answers count: a judgment is a judgment; a value outside 0 to 1 is not one."""
    errors = []
    for s in steps:
        answers = s.get("answers") or {}
        for qid in (answers if noul is None else (noul,)):
            answer = answers.get(qid)
            if not isinstance(answer, dict) or isinstance(answer.get("noul"), bool) \
                    or not isinstance(answer.get("noul"), (int, float)) or not 0 <= answer["noul"] <= 1:
                continue  # an answer outside 0 to 1 is not a probability; it made its decision invalid
            truth = _truth(s, qid)
            if truth is not None:
                errors.append((answer["noul"] - float(truth)) ** 2)
    return _mean(errors)


def _summarize_player(player: str, steps: list[dict], model: str | None = None) -> dict:
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
    input_tokens = sum(u.get("input_tokens") or 0 for u in usage)
    output_tokens = sum(u.get("output_tokens") or 0 for u in usage)

    return {
        "player": player, "runs": len(complete), "incomplete": len(finals) - len(complete),
        "mean_rows": _mean(rows), "median_rows": statistics.median(rows) if rows else None,
        "finished": sum(f["finished"] for f in complete),
        **{cause: sum(f["death_cause"] == cause for f in complete)
           for cause in ("ran_into_gap", "jumped_into_gap", "dodged_into_gap")},
        "jump_share": _ratio(sum(s["executed_action"] == "jump" for s in steps), len(steps)),
        "solver_agreement": _ratio(sum(_agrees(s) for s in comparable), len(comparable)),
        "fallback_rate": _ratio(sum(_is_fallback(s) for s in steps), len(steps)),
        "invalid_rate": _ratio(sum(s["invalid"] for s in steps), len(steps)),
        "error_rate": _ratio(sum(s["error"] is not None for s in steps), len(steps)),
        "missing": None,  # filled in by summarize() when meta.json says which seeds were planned
        "spent": None,  # filled in by summarize() from meta.json's requests[player].used, when present
        "requests": len(live), "cache_hits": sum(bool(s["cache_hit"]) for s in steps),
        "mean_latency_ms": _mean([s["latency_ms"] for s in live]),
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "cost_usd": _cost_usd(model, input_tokens, output_tokens),
        "brier_gap_ahead": _brier(steps, "gap_ahead"), "brier_left_safe": _brier(steps, "left_safe"),
        **{f"brier_gap_{action}": _brier(steps, f"gap_{action}") for action in ("left", "stay", "right", "jump")},
        "brier_all": _brier(steps, None),
    }


def summarize(steps: list[dict], meta: dict | None = None) -> list[dict]:
    groups = defaultdict(list)
    for s in steps:
        groups[s["player"]].append(s)
    for player in (meta or {}).get("players", ()):
        groups.setdefault(player, [])  # a player that never started still gets a row
    rows = []
    for player, group in sorted(groups.items()):
        row = _summarize_player(player, group, ((meta or {}).get("models") or {}).get(player))
        if meta is not None:
            row["missing"] = len(set(meta.get("seeds", ())) - {s["seed"] for s in group})
            row["spent"] = (meta.get("requests") or {}).get(player, {}).get("used")
        rows.append(row)
    return rows


def _fmt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}" if 0 < abs(value) < 0.1 else f"{value:.2f}"  # a track costs cents
    return str(value)


def format_table(rows: list[dict]) -> str:
    lines = ["| " + " | ".join(COLUMNS) + " |", "| " + " | ".join("---" for _ in COLUMNS) + " |"]
    lines += ["| " + " | ".join(_fmt(row[c]) for c in COLUMNS) + " |" for row in rows]
    return "\n".join(lines)

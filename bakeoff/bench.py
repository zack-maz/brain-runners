"""The benchmark (item 7): which player is better and how sure we can be, and what each costs in money and time
for what it scores, from recorded runs only (docs/superpowers/specs/2026-09-22-benchmark-design.md). It reads run
directories and spends nothing."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from bakeoff.game.rules import Rules
from bakeoff.replay import SCHEMA_VERSION
from bakeoff.report import PRICES_USD_PER_MTOK, load_meta, load_steps


@dataclass(frozen=True)
class Source:
    """A run directory and the players to take from it (None: all of them)."""
    run_dir: Path
    players: tuple[str, ...] | None = None


def parse_source(arg: str) -> Source:
    """`runs/X` or `runs/X:llm,jev_composed`."""
    path, sep, names = arg.partition(":")
    players = tuple(n.strip() for n in names.split(",") if n.strip())
    if sep and not players:
        raise ValueError(f"{arg}: no players after ':'")
    return Source(Path(path), players if sep else None)


@dataclass(frozen=True)
class Episode:
    player: str
    seed: int
    run_id: str
    steps: tuple[dict, ...]  # in row order
    model: str | None  # the provider's model from meta.json, None for a free player

    @property
    def complete(self) -> bool:
        """Dead or finished. A run that was stopped or aborted leaves an episode that is neither."""
        last = self.steps[-1]
        return bool(last["finished"]) or not last["alive"]

    @property
    def rows(self) -> int:
        return self.steps[-1]["rows_survived"]


@dataclass(frozen=True)
class Loaded:
    game: Rules | None  # None when no run recorded its game (runs from before game versions)
    run_ids: tuple[str, ...]
    episodes: tuple[Episode, ...]  # complete ones only
    incomplete: tuple[Episode, ...]


def load(sources: list[Source]) -> Loaded:
    """Merge run directories like `view` does: one game, one schema, each (player, seed) from one directory."""
    game: tuple[str, Rules] | None = None
    owner: dict[tuple[str, int], str] = {}
    run_ids, complete, incomplete = [], [], []
    for source in sources:
        steps = load_steps(source.run_dir)
        meta = load_meta(source.run_dir) or {}
        run_id = meta.get("run_id") or source.run_dir.name
        if meta.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
            raise ValueError(f"{run_id} has schema_version {meta['schema_version']}; this benchmark reads "
                             f"{SCHEMA_VERSION}")
        if meta.get("game"):
            rules = Rules.from_json(meta["game"])
            if game is None:
                game = (run_id, rules)
            elif not game[1].same_game(rules):
                raise ValueError(f"{game[0]} is game {game[1].version} but {run_id} is game {rules.version}; "
                                 "a benchmark compares one game")
        present = {s["player"] for s in steps}
        if source.players is not None:
            missing = [p for p in source.players if p not in present]
            if missing:
                raise ValueError(f"{source.run_dir} has no {', '.join(missing)}; it has {', '.join(sorted(present))}")
            steps = [s for s in steps if s["player"] in source.players]
        run_ids.append(run_id)
        grouped: dict[tuple[str, int], list[dict]] = {}
        for s in steps:
            grouped.setdefault((s["player"], s["seed"]), []).append(s)
        for (player, seed), group in grouped.items():
            if (player, seed) in owner:
                raise ValueError(f"{player} on seed {seed} is in both {owner[(player, seed)]} and {run_id}; "
                                 "take it from one of them (DIR:PLAYER,...)")
            owner[(player, seed)] = run_id
            episode = Episode(player, seed, run_id, tuple(sorted(group, key=lambda s: s["row"])),
                              (meta.get("models") or {}).get(player))
            (complete if episode.complete else incomplete).append(episode)
    return Loaded(game[1] if game else None, tuple(run_ids), tuple(complete), tuple(incomplete))


# ---- the numbers -----------------------------------------------------------------------------------------------

BOOTSTRAP_DRAWS = 10_000
Z95 = 1.96
# a bootstrap of fewer values only returns their range, not an honest interval: below this, no interval, no verdict
MIN_SEEDS = 5


def _bootstrap(values: list[float]) -> tuple[float, float] | None:
    """95% percentile bootstrap interval of the mean, resampling the values (one per seed). A fresh generator with
    seed 0 for every interval, so a number does not depend on what was computed before it. None below MIN_SEEDS."""
    if len(values) < MIN_SEEDS:
        return None
    sample = np.asarray(values, dtype=float)
    draws = np.random.default_rng(0).choice(sample, size=(BOOTSTRAP_DRAWS, len(sample)), replace=True).mean(axis=1)
    low, high = np.percentile(draws, [2.5, 97.5])
    return float(low), float(high)


def _seconds(step: dict) -> float | None:
    """Seconds this decision took: the fly's simulation time, or a paid player's latency when it went to the
    provider. A cache hit records no latency (replaying it costs nothing), a free player records none."""
    info = step.get("info") or {}
    if isinstance(info.get("wall_ms"), (int, float)):
        return info["wall_ms"] / 1000.0
    if not step.get("cache_hit") and isinstance(step.get("latency_ms"), (int, float)):
        return step["latency_ms"] / 1000.0
    return None


def _usd(step: dict, model: str | None) -> float | None:
    usage = step.get("usage")
    if step.get("cache_hit") or not usage or model not in PRICES_USD_PER_MTOK:
        return None
    per_input, per_output = PRICES_USD_PER_MTOK[model]
    return (usage.get("input_tokens", 0) * per_input + usage.get("output_tokens", 0) * per_output) / 1e6


def player_numbers(episodes: list[Episode], max_rows: int) -> dict:
    """One player's row of the benchmark, over its complete episodes."""
    rows = [e.rows for e in episodes]
    steps = [s for e in episodes for s in e.steps]
    model = next((e.model for e in episodes if e.model), None)
    ci = _bootstrap(rows)
    decisions_per_row = len(steps) / sum(rows) if sum(rows) else None
    seconds = [t for t in map(_seconds, steps) if t is not None]
    usd = [u for u in (_usd(s, model) for s in steps) if u is not None]
    s_mean = float(np.mean(seconds)) if seconds else None
    usd_mean = float(np.mean(usd)) if usd else None
    return {
        "player": episodes[0].player,
        "seeds": len(episodes),
        "mean_rows": float(np.mean(rows)),
        "ci_low": ci[0] if ci else None,
        "ci_high": ci[1] if ci else None,
        "median_rows": float(np.median(rows)),
        "finished": sum(bool(e.steps[-1]["finished"]) for e in episodes) / len(episodes),
        "survival": [sum(r >= row for r in rows) / len(rows) for row in range(max_rows + 1)],
        "decisions_per_row": decisions_per_row,
        "s_per_decision_median": float(np.median(seconds)) if seconds else None,
        "s_per_decision_p90": float(np.percentile(seconds, 90)) if seconds else None,
        "s_per_row": s_mean * decisions_per_row if s_mean is not None and decisions_per_row else None,
        "usd_per_decision": usd_mean,
        "usd_per_row": usd_mean * decisions_per_row if usd_mean is not None and decisions_per_row else None,
        "model": model,
        "live_decisions": sum(_seconds(s) is not None or _usd(s, model) is not None for s in steps),
        "cache_hits": sum(bool(s.get("cache_hit")) for s in steps),
    }


def pair_numbers(a: list[Episode], b: list[Episode]) -> dict:
    """A against B on the seeds both completed: per seed, A's rows minus B's."""
    rows_b = {e.seed: e.rows for e in b}
    diffs = [e.rows - rows_b[e.seed] for e in a if e.seed in rows_b]
    ci = _bootstrap(diffs)
    mean = float(np.mean(diffs)) if diffs else None
    name_a, name_b = a[0].player, b[0].player
    if ci is None:
        verdict = f"too few seeds ({len(diffs)})"
    elif ci[0] > 0:
        verdict = f"{name_a} ahead"
    elif ci[1] < 0:
        verdict = f"{name_b} ahead"
    else:
        verdict = "can't tell yet"
    needed = None
    if len(diffs) >= 2 and mean:
        sd = float(np.std(diffs, ddof=1))
        needed = max(MIN_SEEDS, math.ceil((Z95 * sd / mean) ** 2))
    return {"a": name_a, "b": name_b, "common_seeds": len(diffs), "mean_diff": mean,
            "ci_low": ci[0] if ci else None, "ci_high": ci[1] if ci else None,
            "wins": sum(d > 0 for d in diffs), "ties": sum(d == 0 for d in diffs), "losses": sum(d < 0 for d in diffs),
            "verdict": verdict, "seeds_needed": needed}


JEV_PRICE_NOTE = ("Jev has no per-token price, so its cost shows as \"-\"; its console gave a blended estimate of about "
                  "0.00003 USD a request (docs/COSTS.md).")
NOTES = ("Time and cost come from live decisions only: a cache hit records neither.",
         f"Intervals and verdicts need at least {MIN_SEEDS} seeds: a bootstrap of fewer only returns their range.",
         "Seeds needed is an estimate from the seeds seen so far, if the difference and its spread stayed the same.")


def benchmark(loaded: Loaded) -> dict:
    """Everything the terminal tables and the page show, JSON-ready."""
    by_player: dict[str, list[Episode]] = {}
    for e in loaded.episodes:
        by_player.setdefault(e.player, []).append(e)
    max_rows = loaded.game.max_rows if loaded.game else max((e.rows for e in loaded.episodes), default=0)
    players = sorted((player_numbers(eps, max_rows) for eps in by_player.values()), key=lambda p: -p["mean_rows"])
    order = [p["player"] for p in players]
    pairs = [pair_numbers(by_player[a], by_player[b]) for i, a in enumerate(order) for b in order[i + 1:]]
    notes = list(NOTES)
    if any(p["player"].startswith("jev") for p in players):
        notes.append(JEV_PRICE_NOTE)
    return {"game": loaded.game.version if loaded.game else None, "max_rows": max_rows, "runs": list(loaded.run_ids),
            "players": players, "pairs": pairs,
            "incomplete": [{"player": e.player, "seed": e.seed, "run_id": e.run_id, "rows": e.rows}
                           for e in loaded.incomplete],
            "notes": notes}


# ---- the terminal ----------------------------------------------------------------------------------------------

def _num(value, digits: int = 1) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def _interval(low, high) -> str:
    return "-" if low is None else f"{low:.1f} to {high:.1f}"


def format_tables(out: dict, pairs: list[tuple[str, str]] | None = None) -> str:
    """The players table, the pairs table (all, or only `pairs`), what was left out, and the notes."""
    lines = [f"game: {out['game'] or 'unknown'} · runs: {', '.join(out['runs'])}", "",
             "| player | seeds | mean rows | 95% interval | median | finished | s per row | USD per row | live | cached |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for p in out["players"]:
        lines.append(f"| {p['player']} | {p['seeds']} | {_num(p['mean_rows'])} | {_interval(p['ci_low'], p['ci_high'])} "
                     f"| {_num(p['median_rows'])} | {p['finished']:.0%} | {_num(p['s_per_row'], 2)} "
                     f"| {_num(p['usd_per_row'], 5)} | {p['live_decisions']} | {p['cache_hits']} |")
    wanted = None if pairs is None else {frozenset(pair) for pair in pairs}
    lines += ["", "| A | B | seeds | mean A - B | 95% interval | A wins / ties / B wins | verdict | seeds needed |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for q in out["pairs"]:
        if wanted is None or frozenset((q["a"], q["b"])) in wanted:
            lines.append(f"| {q['a']} | {q['b']} | {q['common_seeds']} | {_num(q['mean_diff'])} "
                         f"| {_interval(q['ci_low'], q['ci_high'])} | {q['wins']} / {q['ties']} / {q['losses']} "
                         f"| {q['verdict']} | {q['seeds_needed'] if q['seeds_needed'] is not None else '-'} |")
    if out["incomplete"]:
        lines += ["", "Left out, neither dead nor finished: " + ", ".join(
            f"{e['player']} on seed {e['seed']} ({e['run_id']}, {e['rows']} rows)" for e in out["incomplete"])]
    lines += [""] + out["notes"]
    return "\n".join(lines)

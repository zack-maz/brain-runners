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
from bakeoff.players.names import canonical
from bakeoff.prices import ESTIMATED, PRICE_USD
from bakeoff.report import PRICES_USD_PER_MTOK, load_meta, load_steps
from bakeoff.roster import ROSTER


@dataclass(frozen=True)
class Source:
    """A run directory and the players to take from it (None: all of them). `episodes`, when given, narrows it to
    those (player, seed) pairs: Records takes each pair from the newest run that completed it (bakeoff/records.py)."""
    run_dir: Path
    players: tuple[str, ...] | None = None
    episodes: frozenset[tuple[str, int]] | None = None


def parse_source(arg: str) -> Source:
    """`runs/X` or `runs/X:haiku_plain,jev_step1`. The last `:` separates the players, unless what follows it is a path."""
    path, sep, names = arg.rpartition(":")
    if not sep or "/" in names:
        return Source(Path(arg), None)
    players = tuple(canonical(n.strip()) for n in names.split(",") if n.strip())
    if not players:
        raise ValueError(f"{arg}: no players after ':'")
    return Source(Path(path), players)


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
    """Merge run directories like `view` does: one game, one schema, each (player, seed) from one directory. Unlike
    `view`, one length too: a finisher of a shorter run would score as a death in a longer one."""
    game: tuple[str, Rules] | None = None
    owner: dict[tuple[str, int], str] = {}
    models: dict[str, tuple[str | None, str]] = {}  # player -> (model, the run it came from)
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
            elif game[1].max_rows != rules.max_rows:
                raise ValueError(f"{game[0]} has tracks of {game[1].max_rows} rows but {run_id} of {rules.max_rows}; "
                                 "a benchmark compares runs of one length")
        present = {s["player"] for s in steps}
        if source.players is not None:
            missing = [p for p in source.players if p not in present]
            if missing:
                raise ValueError(f"{source.run_dir} has no {', '.join(missing)}; it has {', '.join(sorted(present))}")
            steps = [s for s in steps if s["player"] in source.players]
        if source.episodes is not None:
            steps = [s for s in steps if (s["player"], s["seed"]) in source.episodes]
        run_ids.append(run_id)
        grouped: dict[tuple[str, int], list[dict]] = {}
        for s in steps:
            grouped.setdefault((s["player"], s["seed"]), []).append(s)
        for (player, seed), group in grouped.items():
            if (player, seed) in owner:
                raise ValueError(f"{player} on seed {seed} is in both {owner[(player, seed)]} and {run_id}; "
                                 "take it from one of them (DIR:PLAYER,...)")
            owner[(player, seed)] = run_id
            rows = [s["row"] for s in group]
            if len(set(rows)) != len(rows):
                raise ValueError(f"{player} on seed {seed} appears more than once in {run_id}")
            model = (meta.get("models") or {}).get(player)
            if player in models and models[player][0] != model:
                raise ValueError(f"{player} is {models[player][0]} in {models[player][1]} but {model} in {run_id}; "
                                 "take it from runs of one model")
            models[player] = (model, run_id)
            episode = Episode(player, seed, run_id, tuple(sorted(group, key=lambda s: s["row"])), model)
            (complete if episode.complete else incomplete).append(episode)
    return Loaded(game[1] if game else None, tuple(run_ids), tuple(complete), tuple(incomplete))


# ---- the numbers -----------------------------------------------------------------------------------------------

# Intervals are Student t intervals of a mean over tracks (for a pair: of the per-track differences, a paired t
# interval). A percentile bootstrap was tried first and is too narrow at a handful of tracks: at 5 it left out zero
# for about 1 pair in 7 with no real difference (final review of item 7, decision 32).
MIN_SEEDS = 5  # below this: no interval, no verdict, no tracks-needed estimate
# two-sided 97.5% quantiles of Student's t by degrees of freedom; between entries the next lower df is used (wider)
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
        21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
        40: 2.021, 60: 2.000, 120: 1.980}
Z975, Z80 = 1.960, 0.842  # for the tracks-needed estimate: 95% two-sided, 80% power


def t975(df: int) -> float:
    return T975[max(k for k in T975 if k <= df)]


def _t_interval(values: list[float]) -> tuple[float, float] | None:
    """95% t interval of the mean of the values (one per track). None below MIN_SEEDS."""
    if len(values) < MIN_SEEDS:
        return None
    mean, sd = float(np.mean(values)), float(np.std(values, ddof=1))
    half = t975(len(values) - 1) * sd / math.sqrt(len(values))
    return mean - half, mean + half


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


def _failed(step: dict) -> bool:
    """A decision that did not come back as a move: the provider failed, or the answer was not one."""
    return step.get("error") is not None or bool(step.get("invalid"))


def player_numbers(episodes: list[Episode], max_rows: int, stopped: list[Episode] = ()) -> dict:
    """One player's row of the benchmark, over its complete episodes. `stopped` are its episodes that are neither
    dead nor finished (decision 52: it dropped out): their decisions count in the failed rate, so a provider that
    made a player quit never looks reliable, and in no other number."""
    rows = [e.rows for e in episodes]
    steps = [s for e in episodes for s in e.steps]
    priced = [(s, e.model) for e in episodes for s in e.steps]  # each step priced by its own run's model
    model = next((e.model for e in episodes if e.model), None)
    ci = _t_interval(rows)
    if ci:  # rows cannot leave 0..max_rows; a player that finishes most tracks is understated by the cap
        ci = (max(0.0, ci[0]), min(float(max_rows), ci[1]))
    decisions_per_row = len(steps) / sum(rows) if sum(rows) else None
    seconds = [t for t in map(_seconds, steps) if t is not None]
    usd = [u for u in (_usd(s, m) for s, m in priced) if u is not None]
    s_mean = float(np.mean(seconds)) if seconds else None
    decisions_per_track = len(steps) / len(episodes)
    # the study's cost (decision 53): every decision at the listed price, a cached one too, so that a replay never
    # looks cheaper than the run it replays. The flies and the bots are not in the table: free.
    price = PRICE_USD.get(episodes[0].player, 0.0)
    usd_per_track = price * decisions_per_track
    s_per_track = s_mean * decisions_per_track if s_mean is not None else None
    mean_rows = float(np.mean(rows))
    usd_mean = float(np.mean(usd)) if usd else None
    if usd_mean:
        cost = "priced"
    elif usd_mean == 0 or (model is None and not any(s.get("usage") for s in steps)):
        cost = "free"  # the fly and the baselines, and a model priced at 0 (GLM Flash's free tier)
    else:
        cost = "no price"  # a paid player whose model has no per-token price (Jev), or only cache hits
    return {
        "player": episodes[0].player,
        "seeds": len(episodes),
        "mean_rows": mean_rows,
        "ci_low": ci[0] if ci else None,
        "ci_high": ci[1] if ci else None,
        "median_rows": float(np.median(rows)),
        "finished": sum(bool(e.steps[-1]["finished"]) for e in episodes) / len(episodes),
        "survival": [sum(r >= row for r in rows) / len(rows) for row in range(max_rows + 1)],
        "decisions_per_row": decisions_per_row,
        "s_per_decision_median": float(np.median(seconds)) if seconds else None,
        "s_per_decision_p90": float(np.percentile(seconds, 90)) if seconds else None,
        "s_per_row": s_mean * decisions_per_row if s_mean is not None and decisions_per_row else None,
        # measured tokens at the per-token price, live decisions only: not the study's cost, which is usd_per_track
        "usd_per_decision": usd_mean,
        "usd_per_row": usd_mean * decisions_per_row if usd_mean is not None and decisions_per_row else None,
        "cost": cost,
        "price_usd": price,
        "cost_basis": "free" if price == 0 else "estimate" if episodes[0].player in ESTIMATED else "listed",
        "decisions_per_track": decisions_per_track,
        "usd_per_track": usd_per_track,
        "s_per_decision_mean": s_mean,
        "s_per_track": s_per_track,
        "failed_rate": (sum(map(_failed, steps)) + sum(_failed(s) for e in stopped for s in e.steps))
                       / (len(steps) + sum(len(e.steps) for e in stopped)),
        "stopped": len(stopped),
        # the named scores: extras beside the charts, never the verdict. A free player has no rows per cent.
        "rows_per_cent": mean_rows / (usd_per_track * 100) if usd_per_track > 0 else None,
        "rows_per_second": mean_rows / s_per_track if s_per_track else None,
        "model": model,
        "live_decisions": sum(_seconds(s) is not None or _usd(s, m) is not None for s, m in priced),
        "cache_hits": sum(bool(s.get("cache_hit")) for s in steps),
    }


def pair_numbers(a: list[Episode], b: list[Episode]) -> dict:
    """A against B on the tracks both completed: per track, A's rows minus B's, and a paired t interval."""
    rows_b = {e.seed: e.rows for e in b}
    diffs = [e.rows - rows_b[e.seed] for e in a if e.seed in rows_b]
    ci = _t_interval(diffs)
    mean = float(np.mean(diffs)) if diffs else None
    name_a, name_b = a[0].player, b[0].player
    if ci is None:
        verdict = f"too few tracks ({len(diffs)})"
    elif ci[0] > 0:
        verdict = f"{name_a} ahead"
    elif ci[1] < 0:
        verdict = f"{name_b} ahead"
    else:
        verdict = "can't tell yet"
    needed = None
    if len(diffs) >= MIN_SEEDS and mean:
        # tracks for an 80% chance that the interval leaves out zero, if the difference and its spread stay as seen
        sd = float(np.std(diffs, ddof=1))
        needed = max(MIN_SEEDS, math.ceil(((Z975 + Z80) * sd / mean) ** 2))
    return {"a": name_a, "b": name_b, "common_seeds": len(diffs), "mean_diff": mean,
            "ci_low": ci[0] if ci else None, "ci_high": ci[1] if ci else None,
            "wins": sum(d > 0 for d in diffs), "ties": sum(d == 0 for d in diffs), "losses": sum(d < 0 for d in diffs),
            "verdict": verdict, "seeds_needed": needed}


JEV_PRICE_NOTE = "Jev's USD per track is an estimate (about 0.00003 USD a request, docs/COSTS.md); what it really costs depends on your TypeSafe plan."
# the yardsticks are the Bot's skins (bakeoff/roster.py): shown for scale, never on a frontier
YARDSTICKS = frozenset(skin["player"] for character in ROSTER if character["id"] == "bot" for skin in character["skins"])


def frontier(players: list[dict], key: str) -> set[str]:
    """The players no other player beats on both axes: none has as many rows or more for as little `key` or less,
    and more of one or less of the other. The yardsticks and players without the number are left out; two
    players at the same point are both on it."""
    placed = [p for p in players if p["player"] not in YARDSTICKS and isinstance(p.get(key), (int, float))]

    def beaten(p: dict) -> bool:
        return any(q[key] <= p[key] and q["mean_rows"] >= p["mean_rows"]
                   and (q[key] < p[key] or q["mean_rows"] > p["mean_rows"]) for q in placed)

    return {p["player"] for p in placed if not beaten(p)}
NOTES = ("Time comes from live decisions only: a cache hit records none.",
         f"Intervals are 95% t intervals over tracks (for a pair, of the per-track differences). Below {MIN_SEEDS} "
         "tracks there is no interval and no verdict.",
         "Rows stop at the finish line, so a player that finishes most tracks is understated and two finishers tie.",
         "Tracks needed: how many tracks would give an 80% chance of a verdict if the difference and its spread "
         "stayed as seen so far. An estimate, not a promise.",
         "USD per track counts every decision at the listed price (measured, rounded up), cached answers included, "
         "so a replay never looks cheaper. GLM Flash's free tier, the flies and the bots cost nothing.",
         "A frontier is the players no other beats on both axes: more rows for less money, or for less time. It "
         f"names no single winner; the bots are there for scale and are never on it, nor is a player with fewer "
         f"than {MIN_SEEDS} tracks.")


def _comparisons_note(pairs: list[dict]) -> str | None:
    tested = sum(p["common_seeds"] >= MIN_SEEDS for p in pairs)
    if tested < 2:
        return None
    return (f"{tested} pairs are compared at 95% each: even with no real differences about {tested / 20:.1f} of them "
            "would show a verdict by chance. Read a single verdict as a lead, not a result.")


def benchmark(loaded: Loaded) -> dict:
    """Everything the terminal tables and the page show, JSON-ready."""
    by_player: dict[str, list[Episode]] = {}
    for e in loaded.episodes:
        by_player.setdefault(e.player, []).append(e)
    stopped: dict[str, list[Episode]] = {}
    for e in loaded.incomplete:
        stopped.setdefault(e.player, []).append(e)
    max_rows = loaded.game.max_rows if loaded.game else max((e.rows for e in loaded.episodes), default=0)
    # players with an interval are ranked by mean rows; those with too few tracks follow, not ranked
    players = sorted((player_numbers(eps, max_rows, stopped.get(name, [])) for name, eps in by_player.items()),
                     key=lambda p: (p["ci_low"] is None, -p["mean_rows"]))
    for p in players:
        p["ranked"] = p["ci_low"] is not None
    ranked = [p for p in players if p["ranked"]]  # a player with too few tracks for an interval is on no frontier
    on_cost, on_speed = frontier(ranked, "usd_per_track"), frontier(ranked, "s_per_decision_median")
    for p in players:
        p["yardstick"] = p["player"] in YARDSTICKS
        p["frontier_cost"], p["frontier_speed"] = p["player"] in on_cost, p["player"] in on_speed
    order = [p["player"] for p in players]
    pairs = [pair_numbers(by_player[a], by_player[b]) for i, a in enumerate(order) for b in order[i + 1:]]
    notes = list(NOTES)
    comparisons = _comparisons_note(pairs)
    if comparisons:
        notes.append(comparisons)
    if any(p["player"].startswith("jev") for p in players):
        notes.append(JEV_PRICE_NOTE)
    return {"game": loaded.game.version if loaded.game else None, "max_rows": max_rows, "runs": list(loaded.run_ids),
            "players": players, "pairs": pairs,
            "incomplete": [{"player": e.player, "seed": e.seed, "run_id": e.run_id, "rows": e.rows}
                           for e in loaded.incomplete],
            "notes": notes}


# ---- the terminal ----------------------------------------------------------------------------------------------

def benchmark_of(run_dirs: list[str | Path]) -> tuple[dict | None, str | None]:
    """The benchmark of these run directories, or (None, why not). The page asks for numbers it may
    not be able to have — a live run of one track, runs of two lengths — and says so instead of
    failing; `bakeoff bench` still refuses loudly."""
    try:
        loaded = load([parse_source(str(d)) for d in run_dirs])
    except (FileNotFoundError, ValueError) as e:
        return None, str(e)
    if not loaded.episodes:
        return None, "no completed run to score: the benchmark needs runs that ended."
    return benchmark(loaded), None


def _num(value, digits: int = 1) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def _interval(low, high) -> str:
    return "-" if low is None else f"{low:.1f} to {high:.1f}"


def format_tables(out: dict, pairs: list[tuple[str, str]] | None = None) -> str:
    """The players table, the pairs table (all, or only `pairs`), what was left out, and the notes."""
    lines = [f"game: {out['game'] or 'unknown'} · runs: {', '.join(out['runs'])}", "",
             "| player | tracks | mean rows | 95% interval | median | finished | USD per track | s per decision "
             "| failed | live | cached |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for p in out["players"]:
        usd = "free" if p["cost_basis"] == "free" else _num(p["usd_per_track"], 4) + (
            " (estimate)" if p["cost_basis"] == "estimate" else "")
        interval = _interval(p["ci_low"], p["ci_high"]) if p["ranked"] else "not ranked"
        lines.append(f"| {p['player']} | {p['seeds']} | {_num(p['mean_rows'])} | {interval} "
                     f"| {_num(p['median_rows'])} | {p['finished']:.0%} | {usd} "
                     f"| {_num(p['s_per_decision_median'], 2)} | {p['failed_rate']:.1%} "
                     f"| {p['live_decisions']} | {p['cache_hits']} |")
    wanted = None if pairs is None else {frozenset(pair) for pair in pairs}
    lines += ["", "| A | B | tracks | mean A - B | 95% interval | A wins / ties / B wins | verdict | tracks needed |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for q in out["pairs"]:
        if wanted is None or frozenset((q["a"], q["b"])) in wanted:
            lines.append(f"| {q['a']} | {q['b']} | {q['common_seeds']} | {_num(q['mean_diff'])} "
                         f"| {_interval(q['ci_low'], q['ci_high'])} | {q['wins']} / {q['ties']} / {q['losses']} "
                         f"| {q['verdict']} | {q['seeds_needed'] if q['seeds_needed'] is not None else '-'} |")
    if out["incomplete"]:
        lines += ["", "Left out, neither dead nor finished: " + ", ".join(
            f"{e['player']} on track {e['seed']} ({e['run_id']}, {e['rows']} rows)" for e in out["incomplete"])]
    lines += [""] + out["notes"]
    return "\n".join(lines)

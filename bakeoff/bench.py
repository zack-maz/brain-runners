"""The benchmark (item 7): which player is better and how sure we can be, and what each costs in money and time
for what it scores, from recorded runs only (docs/superpowers/specs/2026-09-22-benchmark-design.md). It reads run
directories and spends nothing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bakeoff.game.rules import Rules
from bakeoff.replay import SCHEMA_VERSION
from bakeoff.report import load_meta, load_steps


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

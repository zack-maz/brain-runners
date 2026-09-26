"""The results of one recorded run, for the Brain Battle results screen
(docs/superpowers/specs/2026-09-25-brain-battle-design.md, section E). Reads files only, spends nothing.

One entry per player of the run: the report's row (`summarize`), how each of its tracks ended, the
benchmark's time per row, and a cost estimate of live requests times the page's price per request. The
page ranks and words it; the numbers are all worked out here."""

from __future__ import annotations

from pathlib import Path

from bakeoff.bench import Source, load, player_numbers
from bakeoff.players import PAID
from bakeoff.report import load_meta, load_steps, summarize
from bakeoff.session import PRICE_USD


def _ending(steps: list[dict]) -> dict:
    """How one track ended for one player, from its last record. `trapped`: it died on a row where every move
    fell, so no move there was wrong (the wrong move came earlier)."""
    last = max(steps, key=lambda s: s["row"])
    complete = bool(last["finished"] or not last["alive"])
    depths = last.get("solver_depths") or {}
    return {"seed": last["seed"], "rows": last["rows_survived"], "complete": complete, "finished": bool(last["finished"]),
            "death_cause": last["death_cause"],
            "trapped": bool(not last["alive"] and depths and max(depths.values()) == 0)}


def results_of(run_dir: Path | str) -> dict:
    """{run_id, status, seeds, game, players: [...]} for one run directory. A player the run planned but never
    started still gets an entry, with no tracks."""
    run_dir = Path(run_dir)
    steps = load_steps(run_dir)
    meta = load_meta(run_dir) or {}
    loaded = load([Source(run_dir)])
    max_rows = (meta.get("game") or {}).get("max_rows") or max((s["rows_survived"] for s in steps), default=0)
    rows = {row["player"]: row for row in summarize(steps, meta)}
    order = list(dict.fromkeys([*(meta.get("players") or []), *rows]))
    players = []
    for player in order:
        own = [s for s in steps if s["player"] == player]
        by_seed: dict[int, list[dict]] = {}
        for s in own:
            by_seed.setdefault(s["seed"], []).append(s)
        episodes = [e for e in (*loaded.episodes, *loaded.incomplete) if e.player == player]
        timing = player_numbers(episodes, max_rows)["s_per_row"] if episodes else None
        paid = player in PAID
        price = PRICE_USD.get(player, 0.0) if paid else 0.0
        row = rows[player]
        players.append({**row, "paid": paid, "price_usd": price,
                        # live requests at the page's price: an estimate, not the provider's bill
                        "cost_estimate_usd": row["requests"] * price,
                        "s_per_row": timing,
                        "tracks": [_ending(by_seed[seed]) for seed in sorted(by_seed)]})
    return {"run_id": meta.get("run_id") or run_dir.name, "status": meta.get("status"),
            "seeds": meta.get("seeds") or sorted({s["seed"] for s in steps}),
            "game": {"version": (meta.get("game") or {}).get("version"), "max_rows": max_rows},
            "players": players}

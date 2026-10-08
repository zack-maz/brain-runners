"""The Writeup's source (decisions 53 and 62): `docs/WRITEUP.html`, read when the page asks, so the text on screen
is always the file's. It is this repository's own words, never a log's. One source serves two hosts: Brain Runners'
Writeup screen and motg.dev/runners. Its shape is a contract the website depends on: one
`<article class="writeup">` holding two `<section data-tab="competitors">` and `<section data-tab="results">`, in that
order, each figure the page draws an empty `<figure data-fig="KEY">` that viewer/writeup_figs.js fills from
`docs/STUDY.json`'s shape (`study_of`), and no script or style of its own.

Zack's numbers are typed in his prose (decision 62, superseding decision 53's "a number is never typed"). A
`<span data-stat="PLAYER FIELD">` still works for whoever wants one: the page fills it from the Charts numbers over
the held-out tracks, or every recorded track with `<span data-stat="PLAYER FIELD all">`. The page loads nothing
from the network, so a source that would (a `src=` or `href=` to `http:`, `https:` or `//`) is refused."""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
SPRITES = DOCS.parent / "viewer" / "sprites.js"
WRITEUP = DOCS / "WRITEUP.html"
STUDY = DOCS / "STUDY.json"

# the two tabs, in order, and every figure slot viewer/writeup_figs.js fills
TABS = ("competitors", "results")
FIG_KEYS = ("leaderboard", "rows", "rows-ci", "jev-vs-haiku", "finished", "cost-time", "scores")

# the benchmark's per-player numbers a write-up may cite (bench.player_numbers); viewer/writeup.js formats them
STAT_FIELDS = ("mean_rows", "ci_low", "ci_high", "median_rows", "seeds", "finished", "usd_per_track", "price_usd",
               "s_per_decision_median", "s_per_decision_mean", "s_per_track", "failed_rate", "rows_per_cent",
               "rows_per_second")
STAT = re.compile(r'data-stat="([^"]*)"')
FIG = re.compile(r'data-fig="([^"]*)"')
SECTION = re.compile(r'<section\b[^>]*\bdata-tab="([^"]*)"')
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)  # a comment may show the syntax; it cites nothing
# an address the browser would fetch from outside this machine, quoted or not
NETWORK = re.compile(r"""\b(?:src|href)\s*=\s*["']?\s*(?:https?:|//)""", re.IGNORECASE)

# what the figures read of the benchmark (bench.benchmark), and nothing else: docs/STUDY.json is exactly this
STUDY_PLAYER_FIELDS = ("player", "seeds", "mean_rows", "ci_low", "ci_high", "median_rows", "finished",
                       "usd_per_track", "cost_basis", "s_per_decision_median", "rows_per_cent", "rows_per_second",
                       "failed_rate", "ranked", "yardstick", "frontier_cost", "frontier_speed", "icon")
STUDY_PAIR_FIELDS = ("a", "b", "common_seeds", "mean_diff", "ci_low", "ci_high", "wins", "ties", "losses",
                     "mean_a_shared", "mean_b_shared")
# GLM Flash left the study (decision 56): its stopped held-out run is in the charts, never in the study's numbers
LEFT_OUT = ("glm_",)
# the question sets Jev and Claude Haiku both play, in the order Fig. 3's chips show them
TWIN_SETS = ("step1", "step2", "guided", "plain", "map")


def stats_in(html: str) -> list[tuple[str, str, str]]:
    """Every (player, field, scope) the source cites, in order: the scope is "held_out", or "all" when the citation
    ends in `all`. A citation that is not `PLAYER FIELD` or `PLAYER FIELD all` with a known field is a ValueError
    naming it."""
    out = []
    for spec in STAT.findall(COMMENT.sub("", html)):
        parts = spec.split()
        if len(parts) not in (2, 3) or parts[1] not in STAT_FIELDS or parts[2:] not in ([], ["all"]):
            raise ValueError(f'data-stat="{spec}" must be "PLAYER FIELD" or "PLAYER FIELD all", FIELD one of '
                             f'{", ".join(STAT_FIELDS)}')
        out.append((parts[0], parts[1], "all" if parts[2:] else "held_out"))
    return out


def figs_in(html: str) -> list[str]:
    """Every figure slot's key, in order, comments left out."""
    return FIG.findall(COMMENT.sub("", html))


def structure_why(html: str) -> str | None:
    """Why the source is not in the contract's shape, or None when it is."""
    html = COMMENT.sub("", html)
    if len(re.findall(r'<article class="writeup"', html)) != 1:
        return 'it must have one <article class="writeup">'
    if tuple(SECTION.findall(html)) != TABS:
        return f'it must have two sections, data-tab="{TABS[0]}" then data-tab="{TABS[1]}"'
    unknown = [key for key in figs_in(html) if key not in FIG_KEYS]
    if unknown:
        return f'data-fig="{unknown[0]}" is not a figure the page draws ({", ".join(FIG_KEYS)})'
    for tag in ("script", "style"):
        if re.search(rf"<{tag}\b", html, re.IGNORECASE):
            return f"it must not carry a <{tag}>: each host brings its own"
    return None


def writeup_of(path: Path | str = WRITEUP) -> dict:
    """{html, source, draft, why}: the page's text, or why there is none. It answers with a reason instead of
    failing, like the charts."""
    path = Path(path)
    try:
        html = path.read_text(encoding="utf-8")
    except OSError as e:
        return {"html": None, "source": path.name, "draft": False, "why": f"the writeup could not be read: {e}"}
    reached = NETWORK.search(COMMENT.sub("", html))
    if reached:
        return {"html": None, "source": path.name, "draft": False,
                "why": f"the writeup would load from the network ({reached.group(0)}...); the page loads nothing from it"}
    shape = structure_why(html)
    if shape:
        return {"html": None, "source": path.name, "draft": False, "why": f"the writeup is not in its shape: {shape}"}
    try:
        stats_in(html)
    except ValueError as e:
        return {"html": None, "source": path.name, "draft": False, "why": f"the writeup cites a number wrongly: {e}"}
    return {"html": html, "source": path.name, "draft": 'data-draft="true"' in COMMENT.sub("", html), "why": None}


def _twin(pair: dict) -> dict | None:
    """A pair of Jev and Claude Haiku on the same question set, Jev first, or None when it is not one."""
    a, b = pair["a"], pair["b"]
    if b.startswith("jev_") and a.startswith("haiku_"):  # the benchmark orders a pair by rank: turn it round
        flip = lambda v: None if v is None else -v  # noqa: E731
        pair = {**pair, "a": b, "b": a, "mean_diff": flip(pair["mean_diff"]), "ci_low": flip(pair["ci_high"]),
                "ci_high": flip(pair["ci_low"]), "wins": pair["losses"], "losses": pair["wins"],
                "mean_a_shared": pair["mean_b_shared"], "mean_b_shared": pair["mean_a_shared"]}
    a, b = pair["a"], pair["b"]
    if not (a.startswith("jev_") and b == "haiku_" + a[4:] and a[4:] in TWIN_SETS and pair["common_seeds"]):
        return None
    return {key: pair[key] for key in STUDY_PAIR_FIELDS}


@cache
def _sprite_tables() -> dict:
    """viewer/sprites.js' GRIDS, INKS and BODY, read out of the file: the drawings stay the viewer's alone."""
    js = re.sub(r"//[^\n]*", "", SPRITES.read_text(encoding="utf-8"))
    tables = {}
    for name in ("GRIDS", "INKS", "BODY"):
        literal = re.search(rf"const {name} = (\{{.*?\}});", js, re.DOTALL).group(1)
        literal = re.sub(r"([{,]\s*)([A-Za-z_]\w*)\s*:", r'\1"\2":', literal)
        tables[name] = json.loads(re.sub(r",(\s*[}\]])", r"\1", literal))
    return tables


def icon_of(player: str) -> dict:
    """A player's skin as a still pixel icon: {sprite, color, inks} (its look, bakeoff/roster.py) and {rows,
    palette}, the sprite's grid and the colour of each cell ink in it, as viewer/sprites.js' `pixels` paints it
    standing still with no gauge (a visor's slit in one ink). viewer/writeup_figs.js draws it; a test keeps it equal
    to `Sprites.pixels`."""
    from bakeoff.roster import ROSTER

    look = next(({"sprite": c["sprite"], "color": s["color"], "inks": dict(s["inks"])}
                 for c in ROSTER for s in c["skins"] if s["player"] == player),
                {"sprite": "block", "color": None, "inks": {}})
    t = _sprite_tables()
    sprite = look["sprite"] if look["sprite"] in t["GRIDS"] else "block"
    own = dict(look["inks"])
    if look["color"]:
        own[t["BODY"][sprite]] = look["color"]
    rows = t["GRIDS"][sprite]
    palette = {ink: own.get(ink, t["INKS"].get(ink)) for ink in sorted({c for row in rows for c in row} - {"."})}
    if sprite == "visor":  # no gauge: the slit in the skin's own V ink, or the visor's body colour
        slit = own.get("V") or own.get(t["BODY"][sprite]) or t["INKS"][t["BODY"][sprite]]
        palette["V"] = palette["v"] = slit
    return {**look, "sprite": sprite, "rows": rows, "palette": palette}


def in_study(player: str) -> bool:
    """Whether a player is one of the study's: Jev, Claude Haiku, the flies and the bots (decision 56)."""
    return not player.startswith(LEFT_OUT)


def study_charts(out_root: Path | str, rules) -> dict:
    """The held-out charts of the study's players alone, scored as if no other had played (so the frontiers and the
    notes are the study's): what `study_of` is given, by `bakeoff study-json` and by the Writeup screen alike."""
    from bakeoff.charts import HELD_OUT, charts_of  # numpy: only when asked

    return charts_of(out_root, rules, HELD_OUT, keep=in_study)


def study_of(charts: dict) -> dict | None:
    """The numbers the Writeup's figures are drawn from (docs/STUDY.json's shape), from `study_charts`' answer: every player cut to STUDY_PLAYER_FIELDS in the benchmark's order, the Jev and Claude
    Haiku twins (Jev first, in TWIN_SETS' order) and the benchmark's notes. None when the charts have no numbers."""
    bench = charts.get("bench")
    if not bench:
        return None
    pairs = [twin for twin in map(_twin, bench["pairs"]) if twin]
    pairs.sort(key=lambda q: TWIN_SETS.index(q["a"][4:]))
    return {"players": [{**{key: p.get(key) for key in STUDY_PLAYER_FIELDS}, "icon": icon_of(p["player"])}
                        for p in bench["players"]],
            "pairs": pairs, "notes": list(bench["notes"])}

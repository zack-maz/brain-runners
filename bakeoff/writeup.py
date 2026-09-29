"""The Writeup page's source (decision 53): `docs/WRITEUP.html`, read when the page asks, so the text on screen
is always the file's. It is this repository's own words, never a log's. Its numbers are not typed in it: each is a
`<span data-stat="PLAYER FIELD">` the page fills from the Charts numbers (bakeoff/charts.py), so the write-up
never says a number the data does not give."""

from __future__ import annotations

import re
from pathlib import Path

WRITEUP = Path(__file__).resolve().parent.parent / "docs" / "WRITEUP.html"

# the benchmark's per-player numbers a write-up may cite (bench.player_numbers); viewer/writeup.js formats them
STAT_FIELDS = ("mean_rows", "ci_low", "ci_high", "median_rows", "seeds", "finished", "usd_per_track",
               "s_per_decision_median", "failed_rate", "rows_per_cent", "rows_per_second")
STAT = re.compile(r'data-stat="([^"]*)"')
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)  # a comment may show the syntax; it cites nothing


def stats_in(html: str) -> list[tuple[str, str]]:
    """Every (player, field) the source cites, in order. A citation that is not `PLAYER FIELD` with a known field
    is a ValueError naming it."""
    out = []
    for spec in STAT.findall(COMMENT.sub("", html)):
        parts = spec.split()
        if len(parts) != 2 or parts[1] not in STAT_FIELDS:
            raise ValueError(f'data-stat="{spec}" must be "PLAYER FIELD", FIELD one of {", ".join(STAT_FIELDS)}')
        out.append((parts[0], parts[1]))
    return out


def writeup_of(path: Path | str = WRITEUP) -> dict:
    """{html, source, draft, why}: the page's text, or why there is none. It answers with a reason instead of
    failing, like the charts."""
    path = Path(path)
    try:
        html = path.read_text(encoding="utf-8")
    except OSError as e:
        return {"html": None, "source": path.name, "draft": False, "why": f"the writeup could not be read: {e}"}
    try:
        stats_in(html)
    except ValueError as e:
        return {"html": None, "source": path.name, "draft": False, "why": f"the writeup cites a number wrongly: {e}"}
    return {"html": html, "source": path.name, "draft": 'data-draft="true"' in COMMENT.sub("", html), "why": None}

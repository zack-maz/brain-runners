"""Replay object + viewer/ -> one self-contained HTML file: no server, no network, opens from disk."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

VIEWER_DIR = Path(__file__).resolve().parent.parent / "viewer"
DATA_SLOT = '<script type="application/json" id="replay-data">null</script>'
BENCH_SLOT = '<script type="application/json" id="bench-data">null</script>'
_STYLESHEET = re.compile(r'<link rel="stylesheet" href="([^"]+)">')
_SCRIPT = re.compile(r'<script src="([^"]+)"></script>')
_CSS_URL = re.compile(r"url\(([^)]*)\)", re.IGNORECASE)  # CSS function names are case-insensitive
# the other ways a stylesheet can fetch something; none has a use in a page that must load nothing
_CSS_FETCHES = re.compile(r"@import|image-set|https?:", re.IGNORECASE)
_FONT = re.compile(r"fonts/[A-Za-z0-9_-]+\.woff2")


def embed_json(value) -> str:
    """JSON that is safe inside a <script> element. A logged answer may contain `</script>` or
    `<!--`; with every `<` written as \\u003c nothing in the data can end the element."""
    return json.dumps(value, separators=(",", ":")).replace("<", "\\u003c")


def _stylesheet(path: Path) -> str:
    """A stylesheet with its fonts embedded as base64, so the page stays one file that fetches nothing.
    The only url() a viewer stylesheet may contain is a bundled font, `fonts/<name>.woff2`."""
    css = path.read_text(encoding="utf-8")
    other = _CSS_FETCHES.search(css)
    if other:
        raise ValueError(f"{path.name} may only load fonts/<name>.woff2, not {other.group(0)!r}")

    def embed(match: re.Match) -> str:
        target = match.group(1).strip().strip("'\"")
        if not _FONT.fullmatch(target):
            raise ValueError(f"{path.name} may only load fonts/<name>.woff2, not {target!r}")
        return "url(data:font/woff2;base64," + base64.b64encode((path.parent / target).read_bytes()).decode("ascii") + ")"

    return _CSS_URL.sub(embed, css)


def render_html(replay: dict, viewer_dir: Path | str = VIEWER_DIR, live: str | None = None,
                page_name: str = "index.html", token: str | None = None, bench: dict | None = None) -> str:
    """`live`: the path of the event stream of `bakeoff live`. The page then also listens there, and
    drives the session through the control routes; a replay file has no such attribute and never looks
    for a server. `token`: the session's token, which every request of the page carries. `page_name`:
    the viewer page to fill, `index.html` (the replay) or `bench.html` (the benchmark); both carry the
    same data slot. `bench`: the benchmark's numbers for the same runs, for the page's Analysis tab;
    a page with no benchmark slot must not be given any."""
    viewer_dir = Path(viewer_dir)
    page = (viewer_dir / page_name).read_text(encoding="utf-8")
    if page.count(DATA_SLOT) != 1:
        raise ValueError(f"{viewer_dir / page_name} must contain the replay data slot exactly once")
    if bench is not None and page.count(BENCH_SLOT) != 1:
        raise ValueError(f"{viewer_dir / page_name} must contain the benchmark data slot exactly once to be given one")
    if live is not None:
        if not re.fullmatch(r"/[a-z]+", live):
            raise ValueError(f"live must be a path like /events, not {live!r}")
        if page.count("<body>") != 1:
            raise ValueError(f"{viewer_dir / page_name} must contain <body> exactly once")
        attributes = f'data-live="{live}"'
        if token is not None:
            if not re.fullmatch(r"[A-Za-z0-9_-]+", token):
                raise ValueError("the token must be url-safe text")
            attributes += f' data-token="{token}"'
        page = page.replace("<body>", f"<body {attributes}>")
    # lambdas, so that a backslash in a file is never read as a regex group reference
    page = _STYLESHEET.sub(lambda m: "<style>\n" + _stylesheet(viewer_dir / m.group(1)) + "</style>", page)
    page = _SCRIPT.sub(lambda m: "<script>\n" + (viewer_dir / m.group(1)).read_text(encoding="utf-8") + "</script>", page)
    if bench is not None:
        page = page.replace(BENCH_SLOT, '<script type="application/json" id="bench-data">' + embed_json(bench) + "</script>")
    return page.replace(DATA_SLOT, '<script type="application/json" id="replay-data">' + embed_json(replay) + "</script>")

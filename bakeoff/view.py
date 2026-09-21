"""Replay object + viewer/ -> one self-contained HTML file: no server, no network, opens from disk."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

VIEWER_DIR = Path(__file__).resolve().parent.parent / "viewer"
DATA_SLOT = '<script type="application/json" id="replay-data">null</script>'
_STYLESHEET = re.compile(r'<link rel="stylesheet" href="([^"]+)">')
_SCRIPT = re.compile(r'<script src="([^"]+)"></script>')
_CSS_URL = re.compile(r"url\(([^)]*)\)")
_FONT = re.compile(r"fonts/[A-Za-z0-9_-]+\.woff2")


def embed_json(value) -> str:
    """JSON that is safe inside a <script> element. A logged answer may contain `</script>` or
    `<!--`; with every `<` written as \\u003c nothing in the data can end the element."""
    return json.dumps(value, separators=(",", ":")).replace("<", "\\u003c")


def _stylesheet(path: Path) -> str:
    """A stylesheet with its fonts embedded as base64, so the page stays one file that fetches nothing.
    The only url() a viewer stylesheet may contain is a bundled font, `fonts/<name>.woff2`."""
    def embed(match: re.Match) -> str:
        target = match.group(1).strip("'\"")
        if not _FONT.fullmatch(target):
            raise ValueError(f"{path.name} may only load fonts/<name>.woff2, not {target!r}")
        return "url(data:font/woff2;base64," + base64.b64encode((path.parent / target).read_bytes()).decode("ascii") + ")"

    return _CSS_URL.sub(embed, path.read_text(encoding="utf-8"))


def render_html(replay: dict, viewer_dir: Path | str = VIEWER_DIR) -> str:
    viewer_dir = Path(viewer_dir)
    page = (viewer_dir / "index.html").read_text(encoding="utf-8")
    if page.count(DATA_SLOT) != 1:
        raise ValueError(f"{viewer_dir / 'index.html'} must contain the replay data slot exactly once")
    # lambdas, so that a backslash in a file is never read as a regex group reference
    page = _STYLESHEET.sub(lambda m: "<style>\n" + _stylesheet(viewer_dir / m.group(1)) + "</style>", page)
    page = _SCRIPT.sub(lambda m: "<script>\n" + (viewer_dir / m.group(1)).read_text(encoding="utf-8") + "</script>", page)
    return page.replace(DATA_SLOT, '<script type="application/json" id="replay-data">' + embed_json(replay) + "</script>")

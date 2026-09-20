"""Replay object + viewer/ -> one self-contained HTML file: no server, no network, opens from disk."""

from __future__ import annotations

import json
import re
from pathlib import Path

VIEWER_DIR = Path(__file__).resolve().parent.parent / "viewer"
DATA_SLOT = '<script type="application/json" id="replay-data">null</script>'
_STYLESHEET = re.compile(r'<link rel="stylesheet" href="([^"]+)">')
_SCRIPT = re.compile(r'<script src="([^"]+)"></script>')


def embed_json(value) -> str:
    """JSON that is safe inside a <script> element. A logged answer may contain `</script>` or
    `<!--`; with every `<` written as \\u003c nothing in the data can end the element."""
    return json.dumps(value, separators=(",", ":")).replace("<", "\\u003c")


def render_html(replay: dict, viewer_dir: Path | str = VIEWER_DIR) -> str:
    viewer_dir = Path(viewer_dir)
    page = (viewer_dir / "index.html").read_text()
    if page.count(DATA_SLOT) != 1:
        raise ValueError(f"{viewer_dir / 'index.html'} must contain the replay data slot exactly once")
    # lambdas, so that a backslash in a file is never read as a regex group reference
    page = _STYLESHEET.sub(lambda m: "<style>\n" + (viewer_dir / m.group(1)).read_text() + "</style>", page)
    page = _SCRIPT.sub(lambda m: "<script>\n" + (viewer_dir / m.group(1)).read_text() + "</script>", page)
    return page.replace(DATA_SLOT, '<script type="application/json" id="replay-data">' + embed_json(replay) + "</script>")

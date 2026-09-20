"""The viewer's pure JavaScript (timeline, tunnel geometry, mind panels) has its own tests, run by
node's built-in test runner. No npm packages. Skipped when node is not installed."""

import shutil
import subprocess
from pathlib import Path

import pytest

VIEWER = Path(__file__).resolve().parent.parent / "viewer"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_viewer_javascript():
    tests = sorted(str(p) for p in (VIEWER / "tests").glob("*.test.js"))
    assert tests, "no viewer tests found"
    result = subprocess.run(["node", "--test", *tests], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr

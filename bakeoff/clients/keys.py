"""API keys: from the environment, else from the git-ignored .env file at the repo root, read inside
the program. A key is returned to the caller and never printed, logged or put in an error message."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def require_key(name: str, env_file: Path | str | None = None) -> str:
    value = os.environ.get(name) or dotenv_values(env_file or ENV_FILE).get(name) or ""
    if not value.strip():
        raise ValueError(f"{name} is not set: add it to the .env file at the repo root (see .env.example)")
    return value.strip()

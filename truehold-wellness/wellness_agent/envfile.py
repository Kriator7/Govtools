"""Load truehold-wellness/.env without python-dotenv."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def load_local_env(path: Path | None = None) -> Path:
    env_path = path or (PACKAGE_ROOT / ".env")
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return env_path
    if not env_path.is_file():
        return env_path
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
    return env_path

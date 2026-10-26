"""Runtime settings, overridable with environment variables."""

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    """Where labs and runtime files live (default /opt/sakbe)."""
    return Path(os.environ.get("SAKBE_DATA", "/opt/sakbe"))


def labs_dir() -> Path:
    path = data_dir() / "labs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def templates_dir() -> Path:
    """Node templates. Falls back to the repository copy during development."""
    env = os.environ.get("SAKBE_TEMPLATES")
    if env:
        return Path(env)
    installed = data_dir() / "templates"
    return installed if installed.is_dir() else _REPO_ROOT / "templates"

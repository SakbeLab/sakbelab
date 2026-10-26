"""Runtime settings, overridable with environment variables."""

import hashlib
import os
import tempfile
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


def sock_dir(lab: str, node: str) -> Path:
    """Short directory for a node's Unix sockets (consoles, QMP, VNC).

    Linux limits socket paths to 108 bytes, so they cannot live under long data
    paths like /opt/sakbe/run/<lab>/<node>/.
    """
    base = Path(os.environ.get("SAKBE_SOCK_DIR", "/run/sakbe"))
    try:
        base.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError:
        base = Path(tempfile.gettempdir()) / f"sakbe-{os.getuid()}"
        base.mkdir(mode=0o700, exist_ok=True)
    path = base / hashlib.sha1(f"{lab}|{node}".encode()).hexdigest()[:12]
    path.mkdir(mode=0o700, exist_ok=True)
    return path

"""Shared fixtures: a TestClient whose host commands are faked."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sakbe import util
from sakbe.api.main import app

EXAMPLE = (Path(__file__).resolve().parents[2] / "examples" / "fase0.yml").read_text()
REPO_TEMPLATES = Path(__file__).resolve().parents[2] / "templates"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SAKBE_DATA", str(tmp_path))
    tdir = tmp_path / "templates"
    tdir.mkdir()
    for f in REPO_TEMPLATES.glob("*.yml"):
        (tdir / f.name).write_text(f.read_text())
    monkeypatch.setenv("SAKBE_TEMPLATES", str(tdir))
    calls: list[list[str]] = []
    running: set[str] = set()
    links: set[str] = set()

    def fake_run(cmd, check=True, input=None):
        calls.append(cmd)
        if cmd[:2] == ["docker", "create"]:
            running.add(cmd[cmd.index("--name") + 1])
        elif cmd[:3] == ["docker", "rm", "-f"]:
            running.discard(cmd[3])
        elif cmd[:2] == ["docker", "inspect"]:
            if cmd[-1] not in running:
                return ""
            return "running\n" if "Status" in cmd[3] else "4242\n"
        elif cmd[:3] == ["ip", "link", "add"]:
            links.add(cmd[3])
        elif cmd[:3] == ["ip", "link", "del"]:
            links.discard(cmd[3])
        elif cmd[:3] == ["ip", "link", "show"]:
            return f"1: {cmd[3]}: <UP>\n" if cmd[3] in links else ""
        return ""

    monkeypatch.setattr(util, "run", fake_run)
    c = TestClient(app)
    c.calls = calls
    c.running = running
    return c

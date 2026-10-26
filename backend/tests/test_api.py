from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sakbe import util
from sakbe.api.main import app

EXAMPLE = (Path(__file__).resolve().parents[2] / "examples" / "fase0.yml").read_text()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SAKBE_DATA", str(tmp_path))
    calls: list[list[str]] = []
    running: set[str] = set()

    def fake_run(cmd, check=True, input=None):
        calls.append(cmd)
        if cmd[:2] == ["docker", "create"]:
            running.add(cmd[cmd.index("--name") + 1])
        if cmd[:3] == ["docker", "rm", "-f"]:
            running.discard(cmd[3])
        if cmd[:2] == ["docker", "inspect"]:
            if cmd[-1] not in running:
                return ""
            return "running\n" if "Status" in cmd[3] else "4242\n"
        return ""

    monkeypatch.setattr(util, "run", fake_run)
    c = TestClient(app)
    c.calls = calls
    return c


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_templates_include_frr(client):
    ids = {t["id"]: t for t in client.get("/api/v1/templates").json()}
    assert "frr" in ids
    assert ids["frr"]["interface_names"][0] == "eth1"
    assert ids["cisco-iol-l3"]["interface_names"][:2] == ["Ethernet0/0", "Ethernet0/1"]


def test_yaml_lab_lifecycle(client):
    r = client.post("/api/v1/labs/yaml", content=EXAMPLE, headers={"Content-Type": "text/plain"})
    assert r.status_code == 201, r.text
    assert r.json()["state"] == "stopped"

    r = client.post("/api/v1/labs/fase0/start")
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "running"
    flat = [" ".join(c) for c in client.calls]
    assert any(c.startswith("ip link add sk-") and "type bridge" in c for c in flat)
    assert any("nsenter -t 4242 -n ip link set" in c and "name eth1" in c for c in flat)

    assert client.post("/api/v1/labs/fase0/start").status_code == 409
    assert client.post("/api/v1/labs/fase0/stop").json()["state"] == "stopped"
    assert client.delete("/api/v1/labs/fase0").status_code == 204
    assert client.get("/api/v1/labs/fase0").status_code == 404


def test_invalid_interface_is_rejected(client):
    bad = EXAMPLE.replace("[R1:eth1, R2:eth1]", "[R1:eth99, R2:eth1]")
    client.post("/api/v1/labs/yaml", content=bad, headers={"Content-Type": "text/plain"})
    r = client.post("/api/v1/labs/fase0/start")
    assert r.status_code == 409
    assert "eth99" in r.json()["detail"]


def test_unknown_node_in_link(client):
    bad = EXAMPLE.replace("[R1:eth1, R2:eth1]", "[R1:eth1, R9:eth1]")
    r = client.post("/api/v1/labs/yaml", content=bad, headers={"Content-Type": "text/plain"})
    assert r.status_code == 422


def test_iol_engine_not_available_yet(client):
    lab = {"name": "iol", "nodes": [{"name": "R1", "template": "cisco-iol-l3"}], "links": []}
    assert client.post("/api/v1/labs", json=lab).status_code == 201
    r = client.post("/api/v1/labs/iol/start")
    assert r.status_code == 409
    assert "IOL" in r.json()["detail"]

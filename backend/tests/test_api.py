from fastapi.testclient import TestClient

from sakbe.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_and_get_lab():
    lab = {
        "name": "ospf-area0",
        "nodes": [
            {"name": "R1", "template": "cisco-iol-l3"},
            {"name": "R2", "template": "cisco-iol-l3"},
        ],
        "links": [{"a": "R1:Ethernet0/0", "b": "R2:Ethernet0/0"}],
    }
    assert client.post("/api/v1/labs", json=lab).status_code == 201
    r = client.get("/api/v1/labs/ospf-area0")
    assert r.status_code == 200
    assert len(r.json()["nodes"]) == 2

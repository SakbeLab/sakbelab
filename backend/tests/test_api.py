from tests.conftest import EXAMPLE


def _yaml(client, text=EXAMPLE):
    return client.post("/api/v1/labs/yaml", content=text, headers={"Content-Type": "text/plain"})


def test_health(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_templates(client):
    ids = {t["id"]: t for t in client.get("/api/v1/templates").json()}
    assert ids["frr"]["interface_names"][0] == "eth1"
    assert ids["frr"]["category"] == "router"
    assert ids["ethernet-switch"]["interface_names"][:2] == ["e0", "e1"]
    assert ids["cisco-iol-l3"]["interface_names"][:2] == ["Ethernet0/0", "Ethernet0/1"]
    assert ids["cisco-iol-l2"]["interface_names"][4] == "Ethernet1/0"
    assert ids["cisco-iol-l3"]["available"] is True


def test_yaml_lab_lifecycle(client):
    assert _yaml(client).status_code == 201
    r = client.post("/api/v1/labs/fase0/start")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["state"] == "running" and body["errors"] == []
    assert all(link["a_up"] and link["b_up"] for link in body["links"])
    flat = [" ".join(c) for c in client.calls]
    assert any(c.startswith("ip link add sk-") and "type bridge" in c for c in flat)
    assert any("nsenter -t 4242 -n ip link set" in c and "name eth1" in c for c in flat)
    assert client.post("/api/v1/labs/fase0/stop").json()["state"] == "stopped"
    assert client.delete("/api/v1/labs/fase0").status_code == 204
    assert client.get("/api/v1/labs/fase0").status_code == 404


def test_build_lab_from_editor(client):
    assert client.post("/api/v1/labs", json={"name": "editor"}).status_code == 201
    r = client.post("/api/v1/labs/editor/nodes", json={"template": "frr", "x": 10, "y": 20})
    r = client.post("/api/v1/labs/editor/nodes", json={"template": "frr", "x": 200, "y": 20})
    r = client.post("/api/v1/labs/editor/nodes", json={"template": "ethernet-switch"})
    names = [n["name"] for n in r.json()["nodes"]]
    assert names == ["R1", "R2", "SW1"]

    r = client.post("/api/v1/labs/editor/links", json={"a": "R1:eth1", "b": "SW1:e0"})
    assert r.status_code == 201, r.text
    r = client.post("/api/v1/labs/editor/links", json={"a": "R2:eth1", "b": "SW1:e1"})
    lab = r.json()
    assert len(lab["links"]) == 2
    assert lab["nodes"][2]["used_interfaces"] == ["e0", "e1"]

    # Interface already in use and invalid interface are rejected.
    assert (
        client.post("/api/v1/labs/editor/links", json={"a": "R1:eth1", "b": "R2:eth2"}).status_code
        == 422
    )
    assert (
        client.post("/api/v1/labs/editor/links", json={"a": "R1:eth99", "b": "R2:eth2"}).status_code
        == 422
    )

    # Start one node: its links get a bridge; the switch is still off.
    r = client.post("/api/v1/labs/editor/nodes/R1/start")
    assert r.status_code == 200, r.text
    states = {n["name"]: n["state"] for n in r.json()["nodes"]}
    assert states == {"R1": "running", "R2": "absent", "SW1": "absent"}

    # Start the switch: it attaches to the existing bridge live.
    client.post("/api/v1/labs/editor/nodes/SW1/start")
    flat = [" ".join(c) for c in client.calls]
    assert any(c.startswith("ip link set sp") and "master ss-" in c for c in flat)

    # Move, lock, and a locked node cannot be deleted.
    client.patch("/api/v1/labs/editor/nodes/R2", json={"x": 300, "y": 40})
    client.patch("/api/v1/labs/editor/nodes/R2", json={"locked": True})
    assert client.delete("/api/v1/labs/editor/nodes/R2").status_code == 423
    assert client.patch("/api/v1/labs/editor/nodes/R2", json={"x": 1}).status_code == 423
    client.post("/api/v1/labs/editor/lock", json={"locked": False})

    # Rename a stopped node updates its links.
    r = client.patch("/api/v1/labs/editor/nodes/R2", json={"name": "Core"})
    assert r.status_code == 200, r.text
    assert any(link["a"] == "Core:eth1" for link in r.json()["links"])
    # Renaming a running node is refused.
    assert client.patch("/api/v1/labs/editor/nodes/R1", json={"name": "Edge"}).status_code == 409

    # Delete a link and a node.
    link_id = r.json()["links"][0]["id"]
    assert len(client.delete(f"/api/v1/labs/editor/links/{link_id}").json()["links"]) == 1
    r = client.delete("/api/v1/labs/editor/nodes/Core")
    assert [n["name"] for n in r.json()["nodes"]] == ["R1", "SW1"]
    assert r.json()["links"] == []


def test_notes(client):
    client.post("/api/v1/labs", json={"name": "notas"})
    r = client.post("/api/v1/labs/notas/notes", json={"text": "Área 0", "x": 5, "y": 6})
    note = r.json()["notes"][0]
    r = client.patch(f"/api/v1/labs/notas/notes/{note['id']}", json={"text": "Área 1"})
    assert r.json()["notes"][0]["text"] == "Área 1"
    assert client.delete(f"/api/v1/labs/notas/notes/{note['id']}").json()["notes"] == []


def test_iol_engine_not_available_yet(client):
    client.post(
        "/api/v1/labs", json={"name": "iol", "nodes": [{"name": "R1", "template": "cisco-iol-l3"}]}
    )
    r = client.post("/api/v1/labs/iol/start")
    assert r.status_code == 200
    assert "IOL" in r.json()["errors"][0]


def test_create_template(client):
    tpl = {
        "id": "fortigate-7-2",
        "name": "FortiGate 7.2",
        "vendor": "Fortinet",
        "engine": "qemu",
        "category": "security",
        "icon": "firewall",
        "name_prefix": "FW",
        "image": "fortios-7.2.qcow2",
        "defaults": {"ram": 2048, "cpus": 1},
        "interfaces": {"count": 10, "naming": "port{index}", "start": 1},
    }
    r = client.post("/api/v1/templates", json=tpl)
    assert r.status_code == 201, r.text
    assert r.json()["interface_names"][0] == "port1"
    assert r.json()["available"] is False
    assert client.post("/api/v1/templates", json=tpl).status_code == 409
    assert client.delete("/api/v1/templates/fortigate-7-2").status_code == 204


def test_upload_and_delete_image(client):
    data = b"QFI\xfb" + b"\0" * 1000
    r = client.put("/api/v1/images/qemu/test.qcow2", content=data)
    assert r.status_code == 201, r.text
    assert r.json()["size"] == len(data)
    import hashlib

    assert r.json()["sha256"] == hashlib.sha256(data).hexdigest()
    assert [i["name"] for i in client.get("/api/v1/images").json()] == ["test.qcow2"]
    assert client.put("/api/v1/images/qemu/../evil.qcow2", content=data).status_code in (404, 422)
    assert client.put("/api/v1/images/qemu/bad.exe", content=data).status_code == 422
    assert client.delete("/api/v1/images/qemu/test.qcow2").status_code == 204
    assert client.get("/api/v1/images").json() == []

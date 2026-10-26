import io
import json
import zipfile

import yaml

from tests.conftest import EXAMPLE


def _export(client, name="fase0"):
    client.post("/api/v1/labs/yaml", content=EXAMPLE, headers={"Content-Type": "text/plain"})
    r = client.get(f"/api/v1/labs/{name}/sakbe", params={"author": "Victor Rodas"})
    assert r.status_code == 200
    assert r.headers["content-disposition"].endswith('fase0.sakbe"')
    return r.content


def test_export_structure(client):
    blob = _export(client)
    z = zipfile.ZipFile(io.BytesIO(blob))
    names = set(z.namelist())
    assert {
        "manifest.json",
        "topology.yml",
        "configs/R1.cfg",
        "configs/R2.cfg",
        "templates/frr.yml",
    } <= names
    manifest = json.loads(z.read("manifest.json"))
    assert manifest["format"] == "sakbe" and manifest["version"] == 1
    assert manifest["author"] == "Victor Rodas"
    assert manifest["requires"][0]["engine"] == "docker"
    topo = yaml.safe_load(z.read("topology.yml"))
    assert topo["nodes"]["R1"]["config"] == "configs/R1.cfg"
    assert "ip address 1.1.1.1/32" in z.read("configs/R1.cfg").decode()


def test_import_roundtrip_with_rename_and_conflict(client, tmp_path):
    blob = _export(client)
    # Same name already exists.
    r = client.post("/api/v1/labs/import", content=blob)
    assert r.status_code == 409
    r = client.post("/api/v1/labs/import", content=blob, params={"name": "copia"})
    assert r.status_code == 201, r.text
    lab = r.json()
    assert lab["name"] == "copia"
    assert "ip address 1.1.1.1/32" in lab["nodes"][0]["config"]
    assert lab["links"][0]["a"] == "R1:eth1"


def test_import_installs_missing_template_and_warns_missing_image(client, tmp_path, monkeypatch):
    blob = _export(client)
    (tmp_path / "templates" / "frr.yml").unlink()
    client.delete("/api/v1/labs/fase0")
    r = client.post("/api/v1/labs/import", content=blob)
    assert r.status_code == 201, r.text
    warnings = " ".join(r.json()["warnings"])
    assert "Se instaló la plantilla 'Router FRR'" in warnings
    assert "Falta la imagen Docker" in warnings  # the fake docker has no images
    assert (tmp_path / "templates" / "frr.yml").exists()


def test_import_yaml_body(client):
    r = client.post("/api/v1/labs/import", content=EXAMPLE.encode(), params={"name": "desde-yaml"})
    assert r.status_code == 201
    assert r.json()["name"] == "desde-yaml"


def test_rejects_bad_archives(client):
    assert client.post("/api/v1/labs/import", content=b"PK\x03\x04garbage").status_code == 422
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("manifest.json", json.dumps({"format": "sakbe", "version": 1}))
        z.writestr("topology.yml", "name: evil\nnodes: {}\n")
        z.writestr("../escape.txt", "x")
    r = client.post("/api/v1/labs/import", content=buf.getvalue())
    assert r.status_code == 422
    assert "Ruta inválida" in r.json()["detail"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("manifest.json", json.dumps({"format": "sakbe", "version": 9}))
        z.writestr("topology.yml", "name: futuro\n")
    r = client.post("/api/v1/labs/import", content=buf.getvalue())
    assert r.status_code == 422 and "actualizá SakbeLab" in r.json()["detail"]

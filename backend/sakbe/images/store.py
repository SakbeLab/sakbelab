"""Image store: files the user uploads (QCOW2, IOL binaries, Docker image tarballs).

SakbeLab never downloads vendor images. Each user brings their own.

    /opt/sakbe/images/qemu/<file>.qcow2
    /opt/sakbe/images/iol/<file>.bin
    /opt/sakbe/images/docker/<file>.json   (record of a loaded `docker save` tarball)

Every image has a `<file>.sha256` sidecar so .sakbe labs can check requirements.
"""

import json
import os
import re
from pathlib import Path

from sakbe import settings, util

KINDS = {
    "qemu": (".qcow2", ".img", ".vmdk", ".iso"),
    "iol": (".bin", ".iol", ""),
    "docker": (".tar", ".tar.gz", ".tgz"),
}
FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")


class ImageError(ValueError):
    pass


def kind_dir(kind: str) -> Path:
    if kind not in KINDS:
        raise ImageError(f"Tipo de imagen desconocido '{kind}'. Use: {', '.join(KINDS)}")
    path = settings.data_dir() / "images" / kind
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_name(kind: str, filename: str) -> None:
    if not FILENAME.match(filename) or ".." in filename:
        raise ImageError("Nombre de archivo inválido: use letras, números, '.', '-', '_' o '+'.")
    exts = KINDS[kind]
    if "" not in exts and not filename.lower().endswith(exts):
        raise ImageError(f"Para '{kind}' se aceptan: {', '.join(exts)}")


def path_for(kind: str, filename: str) -> Path:
    validate_name(kind, filename)
    return kind_dir(kind) / filename


def finalize(kind: str, filename: str, part: Path, sha256: str) -> dict:
    """Move a completed upload into place and post-process it per kind."""
    dest = path_for(kind, filename)
    if kind == "docker":
        out = util.run(["docker", "load", "-i", str(part)])
        part.unlink(missing_ok=True)
        refs = [
            line.split(":", 1)[1].strip()
            for line in out.splitlines()
            if line.startswith(("Loaded image:", "Loaded image ID:"))
        ]
        record = {"file": filename, "sha256": sha256, "refs": refs}
        Path(f"{dest}.json").write_text(json.dumps(record), encoding="utf-8")
        return describe(kind, f"{filename}.json")
    os.replace(part, dest)
    if kind == "iol":
        dest.chmod(0o755)
    Path(f"{dest}.sha256").write_text(sha256 + "\n", encoding="utf-8")
    return describe(kind, filename)


def describe(kind: str, filename: str) -> dict:
    path = kind_dir(kind) / filename
    if kind == "docker":
        record = json.loads(path.read_text(encoding="utf-8"))
        return {
            "kind": kind,
            "name": record["file"],
            "size": None,
            "sha256": record["sha256"],
            "refs": record["refs"],
            "reference": record["refs"][0] if record["refs"] else None,
        }
    sidecar = Path(f"{path}.sha256")
    return {
        "kind": kind,
        "name": filename,
        "size": path.stat().st_size,
        "sha256": sidecar.read_text().strip() if sidecar.exists() else None,
        "reference": filename,
    }


def list_all() -> list[dict]:
    result = []
    for kind in KINDS:
        for path in sorted(kind_dir(kind).iterdir()):
            name = path.name
            if name.endswith((".sha256", ".part")):
                continue
            if kind == "docker" and not name.endswith(".json"):
                continue
            result.append(describe(kind, name))
    return result


def delete(kind: str, name: str) -> None:
    if kind == "docker":
        record_path = kind_dir(kind) / f"{name}.json"
        if record_path.exists():
            record = json.loads(record_path.read_text(encoding="utf-8"))
            for ref in record.get("refs", []):
                util.run(["docker", "rmi", ref], check=False)
            record_path.unlink()
        return
    path = path_for(kind, name)
    path.unlink(missing_ok=True)
    Path(f"{path}.sha256").unlink(missing_ok=True)


def local_docker_images() -> list[str]:
    out = util.run(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"], check=False)
    return sorted({line for line in out.splitlines() if line and "<none>" not in line})

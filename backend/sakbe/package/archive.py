"""The .sakbe format: one ZIP file with everything a lab needs except vendor images.

    mi-lab.sakbe
    ├── manifest.json   format, version, author, required images and their SHA256
    ├── topology.yml    nodes, links, notes (same YAML as labs-as-code)
    ├── configs/        day-0 configuration of each node (R1.cfg ...)
    └── templates/      node templates used by the lab (without images)

See spec/sakbe-format-v1.md.
"""

import io
import json
import zipfile
from datetime import date
from pathlib import Path

import yaml

from sakbe import __version__, util
from sakbe.images import store as images
from sakbe.images import templates
from sakbe.labs import store
from sakbe.labs.models import Lab

FORMAT = "sakbe"
VERSION = 1
MAX_MEMBERS = 2000
MAX_UNCOMPRESSED = 50 * 1024 * 1024  # labs are text; refuse zip bombs


class ArchiveError(ValueError):
    pass


def _image_sha(engine: str, image: str | None) -> str | None:
    if not image or engine not in ("qemu", "iol"):
        return None
    sidecar = images.kind_dir(engine) / f"{image}.sha256"
    return sidecar.read_text().strip() if sidecar.exists() else None


def requirements(lab: Lab) -> list[dict]:
    tpl = templates.load_all()
    reqs, seen = [], set()
    for node in lab.nodes:
        t = tpl.get(node.template)
        if not t:
            continue
        image = node.image or t.image
        key = (t.id, image)
        if key in seen or not image:
            continue
        seen.add(key)
        reqs.append(
            {
                "template": t.id,
                "engine": t.engine,
                "image": image,
                "sha256": _image_sha(t.engine, image),
                "hint": t.name,
            }
        )
    return reqs


def export_lab(lab: Lab, author: str = "") -> bytes:
    tpl = templates.load_all()
    data = yaml.safe_load(store.lab_to_yaml(lab))
    configs: dict[str, str] = {}
    for name, attrs in (data.get("nodes") or {}).items():
        if attrs.get("config"):
            path = f"configs/{name}.cfg"
            configs[path] = attrs["config"]
            attrs["config"] = path
    manifest = {
        "format": FORMAT,
        "version": VERSION,
        "name": lab.name,
        "description": lab.description,
        "author": author,
        "created": date.today().isoformat(),
        "generator": f"SakbeLab {__version__}",
        "requires": requirements(lab),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        z.writestr("topology.yml", yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
        for path, text in configs.items():
            z.writestr(path, text)
        for tid in sorted({n.template for n in lab.nodes}):
            if tid in tpl:
                body = yaml.safe_dump(tpl[tid].model_dump(), sort_keys=False, allow_unicode=True)
                z.writestr(f"templates/{tid}.yml", body)
    return buf.getvalue()


def _read(z: zipfile.ZipFile, name: str) -> str:
    try:
        return z.read(name).decode("utf-8")
    except KeyError:
        raise ArchiveError(f"Falta {name} dentro del archivo .sakbe.") from None


def _check_image(req: dict) -> str | None:
    """Return a warning if a required image is not available here."""
    engine, image = req.get("engine"), req.get("image")
    if not image:
        return None
    if engine == "docker":
        if util.run(["docker", "image", "inspect", image], check=False) == "":
            return f"Falta la imagen Docker '{image}' ({req.get('hint', '')}). Cargala o descargala con docker pull."
        return None
    if engine in ("qemu", "iol"):
        path = images.kind_dir(engine) / image
        if not path.exists():
            return f"Falta la imagen '{image}' ({req.get('hint', '')}). Cargala en Imágenes y plantillas."
        expected = req.get("sha256")
        actual = _image_sha(engine, image)
        if expected and actual and expected != actual:
            return f"La imagen '{image}' que tenés es distinta a la del autor (SHA256 diferente)."
    return None


def import_lab(
    blob: bytes, rename: str | None = None, replace: bool = False
) -> tuple[Lab, list[str]]:
    """Install templates, create the lab and return it with warnings."""
    try:
        z = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile:
        raise ArchiveError("El archivo no es un .sakbe válido.") from None
    with z:
        infos = z.infolist()
        if len(infos) > MAX_MEMBERS or sum(i.file_size for i in infos) > MAX_UNCOMPRESSED:
            raise ArchiveError("El archivo .sakbe es demasiado grande.")
        for info in infos:
            p = Path(info.filename)
            if p.is_absolute() or ".." in p.parts:
                raise ArchiveError(f"Ruta inválida dentro del archivo: {info.filename}")

        manifest = json.loads(_read(z, "manifest.json"))
        if manifest.get("format") != FORMAT:
            raise ArchiveError("El archivo no tiene formato sakbe.")
        if int(manifest.get("version", 0)) > VERSION:
            raise ArchiveError(
                f"Este .sakbe usa la versión {manifest['version']} del formato; "
                "actualizá SakbeLab para abrirlo."
            )

        data = yaml.safe_load(_read(z, "topology.yml")) or {}
        names = set(z.namelist())
        for attrs in (data.get("nodes") or {}).values():
            cfg = (attrs or {}).get("config")
            if cfg and cfg.startswith("configs/"):
                if cfg not in names:
                    raise ArchiveError(f"Falta {cfg} dentro del archivo .sakbe.")
                attrs["config"] = z.read(cfg).decode("utf-8")
        if rename:
            data["name"] = rename

        warnings: list[str] = []
        installed = templates.load_all()
        for name in sorted(n for n in names if n.startswith("templates/") and n.endswith(".yml")):
            t = templates.Template.model_validate(yaml.safe_load(z.read(name)))
            if t.id not in installed:
                templates.save(t)
                warnings.append(f"Se instaló la plantilla '{t.name}'.")

    lab = store.lab_from_dict(data)
    if store.exists(lab.name) and not replace:
        raise FileExistsError(lab.name)
    for req in manifest.get("requires", []):
        warning = _check_image(req)
        if warning:
            warnings.append(warning)
    missing_tpl = {n.template for n in lab.nodes} - templates.load_all().keys()
    for tid in sorted(missing_tpl):
        warnings.append(f"Falta la plantilla '{tid}' y el archivo no la incluye.")
    store.save(lab)
    return lab, warnings

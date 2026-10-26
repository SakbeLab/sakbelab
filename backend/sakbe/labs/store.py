"""Read and write labs as YAML (the same format used by labs-as-code and .sakbe)."""

from pathlib import Path

import yaml

from sakbe import settings
from sakbe.labs.models import Lab

_NODE_FIELDS = ("template", "image", "ram", "cpus", "x", "y", "locked", "config")


class _Literal(str):
    pass


def _literal_presenter(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.SafeDumper.add_representer(_Literal, _literal_presenter)


def lab_from_dict(data: dict) -> Lab:
    """Accept nodes as a mapping (YAML style) or a list (API style)."""
    data = dict(data)
    nodes = data.get("nodes") or []
    if isinstance(nodes, dict):
        nodes = [{"name": name, **(attrs or {})} for name, attrs in nodes.items()]
    data["nodes"] = nodes
    data["notes"] = data.get("notes") or []
    links = data.get("links") or []
    data["links"] = [
        {"a": link[0], "b": link[1]} if isinstance(link, (list, tuple)) else link for link in links
    ]
    return Lab.model_validate(data)


def lab_from_yaml(text: str) -> Lab:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(  # noqa: TRY004 (reported to users as a validation error)
            "the YAML document must be a mapping with name, nodes and links"
        )
    return lab_from_dict(data)


def lab_to_yaml(lab: Lab) -> str:
    nodes = {}
    for n in lab.nodes:
        attrs = {}
        for f in _NODE_FIELDS:
            value = getattr(n, f)
            if value in (None, "", False) or (f in ("x", "y") and value == 0):
                continue
            if f == "config":
                value = _Literal(value.rstrip() + "\n")
            elif isinstance(value, float) and value.is_integer():
                value = int(value)
            attrs[f] = value
        nodes[n.name] = attrs
    doc = {
        "name": lab.name,
        "description": lab.description,
        "nodes": nodes,
        "links": [[link.a, link.b] for link in lab.links],
    }
    if lab.notes:
        doc["notes"] = [
            {k: v for k, v in note.model_dump().items() if v not in (False, "") or k == "text"}
            for note in lab.notes
        ]
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)


def _path(name: str) -> Path:
    return settings.labs_dir() / f"{name}.yml"


def save(lab: Lab) -> None:
    _path(lab.name).write_text(lab_to_yaml(lab), encoding="utf-8")


def load(name: str) -> Lab:
    path = _path(name)
    if not path.is_file():
        raise KeyError(name)
    return lab_from_yaml(path.read_text(encoding="utf-8"))


def exists(name: str) -> bool:
    return _path(name).is_file()


def delete(name: str) -> None:
    _path(name).unlink(missing_ok=True)


def list_names() -> list[str]:
    return sorted(p.stem for p in settings.labs_dir().glob("*.yml"))

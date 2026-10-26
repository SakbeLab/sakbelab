"""Node templates: one YAML file per template in the templates directory."""

import re

import yaml
from pydantic import BaseModel, field_validator

from sakbe import settings

TEMPLATE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
CATEGORIES = ("router", "switch", "security", "end-device", "other")
ENGINES = ("docker", "switch", "iol", "qemu")


class Interfaces(BaseModel):
    count: int = 4
    naming: str = "eth{index}"
    start: int = 0
    ports_per_slot: int = 4

    def names(self) -> list[str]:
        result = []
        for i in range(self.start, self.start + self.count):
            slot, port = divmod(i - self.start, self.ports_per_slot)
            result.append(self.naming.format(index=i, slot=slot, port=port))
        return result


class Console(BaseModel):
    type: str = "exec"
    command: list[str] = ["/bin/sh"]


class Template(BaseModel):
    id: str
    name: str
    vendor: str = ""
    engine: str
    category: str = "other"
    image: str | None = None
    icon: str = "router"
    name_prefix: str = "N"
    defaults: dict = {}
    interfaces: Interfaces = Interfaces()
    console: Console = Console()
    config: dict = {}

    @field_validator("id")
    @classmethod
    def _valid_id(cls, v: str) -> str:
        if not TEMPLATE_ID.match(v):
            raise ValueError("template ids use lowercase letters, digits, '-' or '_'")
        return v

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError(f"category must be one of {', '.join(CATEGORIES)}")
        return v

    @field_validator("engine")
    @classmethod
    def _valid_engine(cls, v: str) -> str:
        if v not in ENGINES:
            raise ValueError(f"engine must be one of {', '.join(ENGINES)}")
        return v


def load_all() -> dict[str, Template]:
    templates = {}
    for path in sorted(settings.templates_dir().glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        t = Template.model_validate(data)
        templates[t.id] = t
    return templates


def get(template_id: str) -> Template:
    templates = load_all()
    if template_id not in templates:
        raise KeyError(f"template '{template_id}' is not installed")
    return templates[template_id]


def save(template: Template) -> None:
    path = settings.templates_dir() / f"{template.id}.yml"
    data = template.model_dump(exclude_defaults=False)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def delete(template_id: str) -> None:
    (settings.templates_dir() / f"{template_id}.yml").unlink(missing_ok=True)

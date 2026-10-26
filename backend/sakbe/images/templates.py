"""Node templates: one YAML file per template in the templates directory."""

import yaml
from pydantic import BaseModel

from sakbe import settings


class Interfaces(BaseModel):
    count: int = 4
    naming: str = "eth{index}"
    start: int = 0
    ports_per_slot: int = 4

    def names(self) -> list[str]:
        result = []
        for i in range(self.start, self.start + self.count):
            slot, port = divmod(i, self.ports_per_slot)
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
    image: str | None = None
    icon: str = "router"
    defaults: dict = {}
    interfaces: Interfaces = Interfaces()
    console: Console = Console()
    config: dict = {}


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

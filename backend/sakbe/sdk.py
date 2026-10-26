"""SakbeLab Python SDK: build labs as code.

    from sakbe import Lab

    lab = Lab("ospf-area0", server="http://192.168.56.101")
    r1 = lab.node("R1", template="frr")
    r2 = lab.node("R2", template="frr")
    lab.link(r1["eth1"], r2["eth1"])
    r1.config(\"\"\"
    interface eth1
     ip address 10.0.12.1/30
    \"\"\")
    lab.deploy()
    lab.wait_ready()
    lab.export("ospf-area0.sakbe")

Nodes without x/y are placed on a grid automatically.
"""

import time
from pathlib import Path

import yaml

from sakbe.client import DEFAULT_SERVER, Client, SakbeError, quote

__all__ = ["Interface", "Lab", "Node", "SakbeError"]


class Interface:
    def __init__(self, node: "Node", name: str):
        self.node = node
        self.name = name

    def __str__(self) -> str:
        return f"{self.node.name}:{self.name}"

    __repr__ = __str__


class Node:
    def __init__(self, lab: "Lab", name: str, template: str, **attrs):
        self.lab = lab
        self.name = name
        self.template = template
        self.attrs = {k: v for k, v in attrs.items() if v is not None}

    def __getitem__(self, iface: str) -> Interface:
        return Interface(self, iface)

    def config(self, text: str) -> "Node":
        """Set the day-0 configuration (applied when the node starts)."""
        lines = [ln for ln in text.splitlines()]
        while lines and not lines[0].strip():
            lines.pop(0)
        indent = min((len(ln) - len(ln.lstrip()) for ln in lines if ln.strip()), default=0)
        self.attrs["config"] = "\n".join(ln[indent:] for ln in lines).strip() + "\n"
        return self

    def start(self) -> None:
        self.lab._client.post(f"/labs/{quote(self.lab.name)}/nodes/{quote(self.name)}/start")

    def stop(self) -> None:
        self.lab._client.post(f"/labs/{quote(self.lab.name)}/nodes/{quote(self.name)}/stop")

    @property
    def state(self) -> str:
        return self.lab.states().get(self.name, "absent")

    def to_dict(self) -> dict:
        return {"name": self.name, "template": self.template, **self.attrs}

    def __repr__(self) -> str:
        return f"Node({self.name!r}, template={self.template!r})"


class Lab:
    GRID = (220, 160)
    COLUMNS = 5

    def __init__(
        self,
        name: str,
        server: str = DEFAULT_SERVER,
        token: str | None = None,
        description: str = "",
    ):
        self.name = name
        self.description = description
        self.nodes: dict[str, Node] = {}
        self.links: list[tuple[str, str]] = []
        self.notes: list[dict] = []
        self._client = Client(server, token)

    # ------------------------------------------------------------ building

    def node(
        self,
        name: str,
        template: str,
        ram: int | None = None,
        cpus: int | None = None,
        image: str | None = None,
        x: float | None = None,
        y: float | None = None,
        config: str | None = None,
    ) -> Node:
        if name in self.nodes:
            raise ValueError(f"Ya existe un nodo '{name}' en el lab")
        if x is None or y is None:
            i = len(self.nodes)
            x = 100 + (i % self.COLUMNS) * self.GRID[0]
            y = 100 + (i // self.COLUMNS) * self.GRID[1]
        n = Node(self, name, template, ram=ram, cpus=cpus, image=image, x=x, y=y)
        if config:
            n.config(config)
        self.nodes[name] = n
        return n

    def link(self, a: Interface | str, b: Interface | str) -> None:
        self.links.append((str(a), str(b)))

    def note(self, text: str, x: float = 0, y: float = 0) -> None:
        self.notes.append({"id": f"n{len(self.notes) + 1}", "text": text, "x": x, "y": y})

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "links": [{"a": a, "b": b} for a, b in self.links],
            "notes": self.notes,
        }

    def to_yaml(self) -> str:
        doc = {
            "name": self.name,
            "description": self.description,
            "nodes": {n.name: {"template": n.template, **n.attrs} for n in self.nodes.values()},
            "links": [[a, b] for a, b in self.links],
        }
        if self.notes:
            doc["notes"] = self.notes
        return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)

    @classmethod
    def from_yaml(
        cls, path: str | Path, server: str = DEFAULT_SERVER, token: str | None = None
    ) -> "Lab":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        lab = cls(data["name"], server=server, token=token, description=data.get("description", ""))
        nodes = data.get("nodes") or {}
        items = nodes.items() if isinstance(nodes, dict) else ((n["name"], n) for n in nodes)
        for name, attrs in items:
            attrs = {k: v for k, v in (attrs or {}).items() if k != "name"}
            lab.nodes[name] = Node(lab, name, attrs.pop("template"), **attrs)
        for link in data.get("links") or []:
            lab.links.append(
                (link[0], link[1]) if isinstance(link, list) else (link["a"], link["b"])
            )
        lab.notes = data.get("notes") or []
        return lab

    # ------------------------------------------------------------ server

    def deploy(self, replace: bool = True, start: bool = True) -> list[str]:
        """Create (or replace, stopping it first) the lab on the server and start it."""
        c = self._client
        if replace:
            try:
                c.post(f"/labs/{quote(self.name)}/stop")
            except SakbeError as exc:
                if exc.status != 404:
                    raise
        c.post("/labs", self.to_dict(), params={"replace": "true" if replace else None})
        if not start:
            return []
        return c.post(f"/labs/{quote(self.name)}/start").get("errors", [])

    def start(self) -> list[str]:
        return self._client.post(f"/labs/{quote(self.name)}/start").get("errors", [])

    def stop(self) -> None:
        self._client.post(f"/labs/{quote(self.name)}/stop")

    def destroy(self, delete: bool = False) -> None:
        if delete:
            self._client.delete(f"/labs/{quote(self.name)}")
        else:
            self.stop()

    def states(self) -> dict[str, str]:
        data = self._client.get(f"/labs/{quote(self.name)}")
        return {n["name"]: n["state"] for n in data["nodes"]}

    def wait_ready(self, timeout: float = 120, interval: float = 2) -> None:
        """Wait until every node is running."""
        deadline = time.time() + timeout
        while True:
            states = self.states()
            if states and all(s == "running" for s in states.values()):
                return
            if time.time() > deadline:
                pending = [n for n, s in states.items() if s != "running"]
                raise TimeoutError(
                    f"Equipos sin encender después de {timeout}s: {', '.join(pending)}"
                )
            time.sleep(interval)

    def save_configs(self) -> list[str]:
        return self._client.post(f"/labs/{quote(self.name)}/save")["saved"]

    def export(self, path: str | Path, author: str = "") -> Path:
        """Download the lab as .sakbe (complete package) or .yml (topology)."""
        path = Path(path)
        kind = "yaml" if path.suffix in (".yml", ".yaml") else "sakbe"
        data = self._client.get(
            f"/labs/{quote(self.name)}/{kind}", params={"author": author or None}
        )
        path.write_bytes(data if isinstance(data, bytes) else str(data).encode())
        return path

    @classmethod
    def load(cls, name: str, server: str = DEFAULT_SERVER, token: str | None = None) -> "Lab":
        """Fetch an existing lab from the server."""
        lab = cls(name, server=server, token=token)
        data = lab._client.get(f"/labs/{quote(name)}")
        lab.description = data.get("description", "")
        for n in data["nodes"]:
            attrs = {k: n.get(k) for k in ("ram", "cpus", "image", "x", "y", "config")}
            lab.nodes[n["name"]] = Node(lab, n["name"], n["template"], **attrs)
        lab.links = [(lk["a"], lk["b"]) for lk in data["links"]]
        lab.notes = [{k: v for k, v in nt.items() if k != "locked"} for nt in data["notes"]]
        return lab

    def __repr__(self) -> str:
        return f"Lab({self.name!r}, nodes={len(self.nodes)}, links={len(self.links)})"

"""Lab data model shared by the API, the CLI, the SDK and the .sakbe format."""

import re

from pydantic import BaseModel, Field, field_validator, model_validator

LAB_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
NODE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")


class Node(BaseModel):
    name: str
    template: str
    image: str | None = Field(default=None, description="Overrides the template image")
    ram: int | None = Field(default=None, description="RAM in MB; template default if omitted")
    cpus: int | None = None
    config: str | None = Field(default=None, description="Day-0 configuration")
    x: float = 0
    y: float = 0

    @field_validator("name")
    @classmethod
    def _valid_name(cls, v: str) -> str:
        if not NODE_NAME.match(v):
            raise ValueError("node names use letters, digits, '-' or '_' (max 32)")
        return v


class Link(BaseModel):
    a: str = Field(description="Endpoint as NODE:INTERFACE, e.g. R1:eth1")
    b: str

    @field_validator("a", "b")
    @classmethod
    def _valid_endpoint(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError(f"endpoint '{v}' must look like NODE:INTERFACE")
        return v


def split_endpoint(endpoint: str) -> tuple[str, str]:
    node, iface = endpoint.split(":", 1)
    return node, iface


class LabCreate(BaseModel):
    name: str
    description: str = ""
    nodes: list[Node] = []
    links: list[Link] = []

    @field_validator("name")
    @classmethod
    def _valid_name(cls, v: str) -> str:
        if not LAB_NAME.match(v):
            raise ValueError("lab names use lowercase letters, digits, '-' or '_' (max 32)")
        return v

    @model_validator(mode="after")
    def _consistent(self):
        names = [n.name for n in self.nodes]
        if len(names) != len(set(names)):
            raise ValueError("node names must be unique")
        used: set[str] = set()
        for link in self.links:
            for ep in (link.a, link.b):
                node, _ = split_endpoint(ep)
                if node not in names:
                    raise ValueError(f"link endpoint '{ep}' references unknown node '{node}'")
                if ep in used:
                    raise ValueError(f"interface '{ep}' is used by more than one link")
                used.add(ep)
        return self

    def node(self, name: str) -> Node:
        for n in self.nodes:
            if n.name == name:
                return n
        raise KeyError(name)


class Lab(LabCreate):
    pass

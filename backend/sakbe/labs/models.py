"""Lab data model shared by the API, the CLI, the SDK and the .sakbe format."""

import hashlib
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
    locked: bool = False

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

    def id(self, lab: str) -> str:
        return hashlib.sha1(f"{lab}|{self.a}|{self.b}".encode()).hexdigest()[:8]


class Note(BaseModel):
    id: str
    text: str = ""
    x: float = 0
    y: float = 0
    locked: bool = False


def split_endpoint(endpoint: str) -> tuple[str, str]:
    node, iface = endpoint.split(":", 1)
    return node, iface


class LabCreate(BaseModel):
    name: str
    description: str = ""
    nodes: list[Node] = []
    links: list[Link] = []
    notes: list[Note] = []

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

    def link(self, link_id: str) -> Link:
        for link in self.links:
            if link.id(self.name) == link_id:
                return link
        raise KeyError(link_id)

    def links_of(self, node_name: str) -> list[Link]:
        return [
            link
            for link in self.links
            if split_endpoint(link.a)[0] == node_name or split_endpoint(link.b)[0] == node_name
        ]

    def used_interfaces(self, node_name: str) -> set[str]:
        used = set()
        for link in self.links:
            for ep in (link.a, link.b):
                n, iface = split_endpoint(ep)
                if n == node_name:
                    used.add(iface)
        return used


class Lab(LabCreate):
    pass

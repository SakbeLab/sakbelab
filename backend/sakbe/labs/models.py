"""Lab data model shared by the API, the CLI, the SDK and the .sakbe format."""

from pydantic import BaseModel, Field


class Node(BaseModel):
    name: str
    template: str
    ram: int | None = Field(default=None, description="RAM in MB; template default if omitted")
    cpus: int | None = None
    config: str | None = Field(default=None, description="Day-0 configuration")
    x: float = 0
    y: float = 0


class Link(BaseModel):
    a: str = Field(description="Endpoint as NODE:INTERFACE, e.g. R1:Ethernet0/0")
    b: str


class LabCreate(BaseModel):
    name: str
    description: str = ""
    nodes: list[Node] = []
    links: list[Link] = []


class Lab(LabCreate):
    state: str = "stopped"

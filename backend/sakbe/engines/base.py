"""Common interface for every emulation engine (Docker, switch, IOL, QEMU)."""

from abc import ABC, abstractmethod

from sakbe.images.templates import Template
from sakbe.labs.models import Node


class EngineUnavailable(RuntimeError):
    pass


class Engine(ABC):
    """An engine creates, destroys, wires and exposes the console of a node.

    Every link is a Linux bridge on the host. `attach` connects one node
    interface to that bridge through a host-side device named `host_if`.
    """

    name: str

    @abstractmethod
    def create(self, lab: str, node: Node, template: Template) -> None:
        """Create and start the node, applying its day-0 configuration."""

    @abstractmethod
    def destroy(self, lab: str, node: Node) -> None:
        """Stop and remove the node. Must not fail if it does not exist."""

    @abstractmethod
    def status(self, lab: str, node: Node) -> str:
        """Return 'running', 'stopped' or 'absent'."""

    @abstractmethod
    def attach(self, lab: str, node: Node, iface: str, bridge: str, host_if: str) -> None:
        """Connect `iface` of a running node to `bridge`. Must be idempotent."""

    @abstractmethod
    def console_command(self, lab: str, node: Node, template: Template) -> list[str]:
        """Host command that opens the node console when run on a PTY."""

    def has_console(self) -> bool:
        return True

    def save_config(self, lab: str, node: Node) -> str | None:
        """Return the node's running configuration, if the engine supports it."""
        return None

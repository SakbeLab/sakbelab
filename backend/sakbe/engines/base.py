"""Common interface for every emulation engine (Docker, IOL, QEMU)."""

from abc import ABC, abstractmethod

from sakbe.images.templates import Template
from sakbe.labs.models import Node


class EngineUnavailable(RuntimeError):
    pass


class Engine(ABC):
    """An engine creates, destroys and exposes the console of a node.

    Every node runs inside its own Linux network namespace; links are wired
    by sakbe.network using the PID returned by `pid()`.
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
    def pid(self, lab: str, node: Node) -> int:
        """PID of a process inside the node's network namespace."""

    @abstractmethod
    def console_command(self, lab: str, node: Node, template: Template) -> list[str]:
        """Host command that opens the node console when run on a PTY."""

    def save_config(self, lab: str, node: Node) -> str | None:
        """Return the node's running configuration, if the engine supports it."""
        return None

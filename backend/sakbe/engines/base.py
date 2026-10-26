"""Common interface for every emulation engine (IOL, QEMU, Docker)."""

from abc import ABC, abstractmethod


class Engine(ABC):
    """An engine starts, stops and exposes the console of one node."""

    name: str

    @abstractmethod
    def start(self, node_id: str, image: str, ram: int, cpus: int, config: str | None) -> None:
        """Start the node, applying the day-0 configuration if provided."""

    @abstractmethod
    def stop(self, node_id: str) -> None:
        """Stop the node."""

    @abstractmethod
    def console_port(self, node_id: str) -> int:
        """Return the local TCP port of the node's serial console."""

    @abstractmethod
    def attach_interface(self, node_id: str, interface: str, bridge: str) -> None:
        """Connect one node interface to a Linux bridge (one bridge per link)."""

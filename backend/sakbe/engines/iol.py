"""Cisco IOL engine (Phase 0 target).

IOL runs as a native Linux binary, so it does not need nested virtualization.
Phase 0 goal: start two IOL nodes, connect them and ping between them from
the browser console.
"""

from sakbe.engines.base import Engine


class IOLEngine(Engine):
    name = "iol"

    def start(self, node_id, image, ram, cpus, config):
        raise NotImplementedError("Phase 0")

    def stop(self, node_id):
        raise NotImplementedError("Phase 0")

    def console_port(self, node_id):
        raise NotImplementedError("Phase 0")

    def attach_interface(self, node_id, interface, bridge):
        raise NotImplementedError("Phase 0")

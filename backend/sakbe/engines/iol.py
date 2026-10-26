"""Cisco IOL engine (planned for MVP 0.1, issue #9).

IOL runs as a native Linux binary, so it does not need nested virtualization.
Users must provide their own licensed images.
"""

from sakbe.engines.base import Engine, EngineUnavailable

_MSG = "El motor IOL todavía no está disponible (planificado para el MVP 0.1)."


class IOLEngine(Engine):
    name = "iol"

    def create(self, lab, node, template):
        raise EngineUnavailable(_MSG)

    def destroy(self, lab, node):
        return None

    def status(self, lab, node):
        return "absent"

    def pid(self, lab, node):
        raise EngineUnavailable(_MSG)

    def console_command(self, lab, node, template):
        raise EngineUnavailable(_MSG)

from sakbe.engines.base import Engine, EngineUnavailable
from sakbe.engines.docker import DockerEngine
from sakbe.engines.iol import IOLEngine

ENGINES: dict[str, Engine] = {e.name: e for e in (DockerEngine(), IOLEngine())}


def get(name: str) -> Engine:
    if name not in ENGINES:
        raise EngineUnavailable(f"El motor '{name}' no existe en esta versión de SakbeLab.")
    return ENGINES[name]


__all__ = ["ENGINES", "Engine", "EngineUnavailable", "get"]

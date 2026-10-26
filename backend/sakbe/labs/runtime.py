"""Start, stop and inspect labs: ties engines, templates and links together."""

from sakbe import engines
from sakbe.images import templates
from sakbe.labs.models import Lab, split_endpoint
from sakbe.network import links


class LabError(RuntimeError):
    pass


def _templates_for(lab: Lab) -> dict:
    available = templates.load_all()
    missing = {n.template for n in lab.nodes} - available.keys()
    if missing:
        raise LabError(f"Plantillas no instaladas: {', '.join(sorted(missing))}")
    return available


def validate_interfaces(lab: Lab) -> None:
    tpl = _templates_for(lab)
    for link in lab.links:
        for ep in (link.a, link.b):
            node_name, iface = split_endpoint(ep)
            node = lab.node(node_name)
            valid = tpl[node.template].interfaces.names()
            if iface not in valid:
                raise LabError(
                    f"'{iface}' no existe en {node_name} ({node.template}). "
                    f"Interfaces válidas: {', '.join(valid)}"
                )


def node_states(lab: Lab) -> dict[str, str]:
    tpl = templates.load_all()
    states = {}
    for node in lab.nodes:
        t = tpl.get(node.template)
        states[node.name] = engines.get(t.engine).status(lab.name, node) if t else "absent"
    return states


def lab_state(lab: Lab) -> str:
    states = set(node_states(lab).values())
    if states == {"running"}:
        return "running"
    if states <= {"absent"}:
        return "stopped"
    return "partial"


def start(lab: Lab) -> None:
    validate_interfaces(lab)
    tpl = _templates_for(lab)
    if lab_state(lab) != "stopped":
        raise LabError(
            f"El lab '{lab.name}' ya está encendido. Apagalo antes de volver a iniciarlo."
        )
    try:
        for node in lab.nodes:
            t = tpl[node.template]
            engines.get(t.engine).create(lab.name, node, t)
        for link in lab.links:
            ends = []
            for ep in (link.a, link.b):
                node_name, iface = split_endpoint(ep)
                node = lab.node(node_name)
                ends.append((engines.get(tpl[node.template].engine).pid(lab.name, node), iface))
            links.connect(links.link_id(lab.name, link.a, link.b), ends[0], ends[1])
    except Exception:
        stop(lab)
        raise


def stop(lab: Lab) -> None:
    tpl = templates.load_all()
    for node in lab.nodes:
        t = tpl.get(node.template)
        if t:
            engines.get(t.engine).destroy(lab.name, node)
    for link in lab.links:
        links.disconnect(links.link_id(lab.name, link.a, link.b))


def save_configs(lab: Lab) -> list[str]:
    """Copy each running node's configuration into the lab. Returns saved node names."""
    tpl = templates.load_all()
    saved = []
    for node in lab.nodes:
        engine = engines.get(tpl[node.template].engine)
        if engine.status(lab.name, node) != "running":
            continue
        config = engine.save_config(lab.name, node)
        if config:
            node.config = config
            saved.append(node.name)
    return saved


def console_command(lab: Lab, node_name: str) -> list[str]:
    node = lab.node(node_name)
    t = templates.get(node.template)
    return engines.get(t.engine).console_command(lab.name, node, t)

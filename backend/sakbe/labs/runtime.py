"""Run labs: start and stop nodes one by one and keep links wired live.

Nodes start and stop independently, like in GNS3. A link's bridge exists
while at least one of its endpoints is running; each running endpoint is
attached to it. Adding a link between running nodes wires it immediately.
"""

from sakbe import engines
from sakbe.images import templates
from sakbe.labs.models import Lab, Link, Node, split_endpoint
from sakbe.network import links as net


class LabError(RuntimeError):
    pass


def _template(node: Node, tpl: dict | None = None):
    tpl = tpl if tpl is not None else templates.load_all()
    if node.template not in tpl:
        raise LabError(f"La plantilla '{node.template}' no está instalada.")
    return tpl[node.template]


def interface_names(node: Node, tpl: dict | None = None) -> list[str]:
    return _template(node, tpl).interfaces.names()


def validate_link(lab: Lab, link: Link, tpl: dict | None = None) -> None:
    tpl = tpl if tpl is not None else templates.load_all()
    for ep in (link.a, link.b):
        node_name, iface = split_endpoint(ep)
        try:
            node = lab.node(node_name)
        except KeyError:
            raise LabError(f"No existe el nodo '{node_name}'.") from None
        valid = interface_names(node, tpl)
        if iface not in valid:
            raise LabError(
                f"'{iface}' no existe en {node_name} ({node.template}). "
                f"Interfaces válidas: {', '.join(valid)}"
            )
    if split_endpoint(link.a)[0] == split_endpoint(link.b)[0]:
        raise LabError("Un enlace no puede conectar un nodo consigo mismo.")


def validate_interfaces(lab: Lab) -> None:
    tpl = templates.load_all()
    for link in lab.links:
        validate_link(lab, link, tpl)


def node_state(lab: Lab, node: Node, tpl: dict | None = None) -> str:
    try:
        t = _template(node, tpl)
    except LabError:
        return "absent"
    return engines.get(t.engine).status(lab.name, node)


def node_states(lab: Lab) -> dict[str, str]:
    tpl = templates.load_all()
    return {n.name: node_state(lab, n, tpl) for n in lab.nodes}


def lab_state(lab: Lab) -> str:
    states = set(node_states(lab).values())
    if states == {"running"}:
        return "running"
    if states <= {"absent", "stopped"}:
        return "stopped"
    return "partial"


def wire_link(lab: Lab, link: Link, tpl: dict | None = None) -> None:
    """Attach every running endpoint of a link to its bridge."""
    tpl = tpl if tpl is not None else templates.load_all()
    lid = link.id(lab.name)
    ends = []
    for side, ep in (("a", link.a), ("b", link.b)):
        node_name, iface = split_endpoint(ep)
        node = lab.node(node_name)
        if node_state(lab, node, tpl) == "running":
            ends.append((side, node, iface))
    if not ends:
        return
    bridge = net.bridge_name(lid)
    net.ensure_bridge(bridge)
    for side, node, iface in ends:
        engine = engines.get(_template(node, tpl).engine)
        engine.attach(lab.name, node, iface, bridge, net.host_if(lid, side))


def unwire_link(lab: Lab, link: Link) -> None:
    net.remove_link(link.id(lab.name))


def start_node(lab: Lab, node_name: str) -> None:
    tpl = templates.load_all()
    node = lab.node(node_name)
    t = _template(node, tpl)
    engine = engines.get(t.engine)
    if engine.status(lab.name, node) == "running":
        return
    engine.destroy(lab.name, node)
    try:
        engine.create(lab.name, node, t)
        for link in lab.links_of(node_name):
            wire_link(lab, link, tpl)
    except Exception:
        stop_node(lab, node_name)
        raise


def stop_node(lab: Lab, node_name: str) -> None:
    tpl = templates.load_all()
    node = lab.node(node_name)
    t = tpl.get(node.template)
    if t:
        engines.get(t.engine).destroy(lab.name, node)
    for link in lab.links_of(node_name):
        lid = link.id(lab.name)
        side = "a" if split_endpoint(link.a)[0] == node_name else "b"
        net.delete(net.host_if(lid, side))
        other = split_endpoint(link.b if side == "a" else link.a)[0]
        if node_state(lab, lab.node(other), tpl) != "running":
            net.delete(net.bridge_name(lid))


def wipe_node(lab: Lab, node_name: str) -> None:
    """Remove persistent data of a node that is being deleted."""
    node = lab.node(node_name)
    t = templates.load_all().get(node.template)
    if t:
        engines.get(t.engine).wipe(lab.name, node)


def start(lab: Lab) -> list[str]:
    """Start every node. Returns errors as text; one failing node does not stop the rest."""
    validate_interfaces(lab)
    errors = []
    for node in lab.nodes:
        try:
            start_node(lab, node.name)
        except Exception as exc:  # noqa: BLE001 (reported per node)
            errors.append(f"{node.name}: {exc}")
    return errors


def stop(lab: Lab) -> None:
    for node in lab.nodes:
        stop_node(lab, node.name)
    for link in lab.links:
        unwire_link(lab, link)


def save_configs(lab: Lab) -> list[str]:
    """Copy each running node's configuration into the lab. Returns saved node names."""
    tpl = templates.load_all()
    saved = []
    for node in lab.nodes:
        t = tpl.get(node.template)
        if not t:
            continue
        engine = engines.get(t.engine)
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
    engine = engines.get(t.engine)
    if not engine.has_console():
        raise LabError(f"{node_name} no tiene consola.")
    return engine.console_command(lab.name, node, t)

"""Built-in Ethernet switch: an unmanaged switch made of one Linux bridge.

Like the GNS3 Ethernet switch, it needs no image. Each connected port is a
veth pair joining the link bridge and the switch bridge.
"""

import hashlib

from sakbe import util
from sakbe.engines.base import Engine
from sakbe.network import links


def switch_bridge(lab: str, node_name: str) -> str:
    return "ss-" + hashlib.sha1(f"{lab}|{node_name}".encode()).hexdigest()[:8]


class SwitchEngine(Engine):
    name = "switch"

    def create(self, lab, node, template):
        br = switch_bridge(lab, node.name)
        links.ensure_bridge(br)

    def destroy(self, lab, node):
        br = switch_bridge(lab, node.name)
        if not links.exists(br):
            return
        out = util.run(["ip", "-o", "link", "show", "master", br], check=False)
        for line in out.splitlines():
            # "12: spxxxxxxxxa@svxxxxxxxxa: <...>"
            dev = line.split(":")[1].strip().split("@")[0]
            links.delete(dev)
        links.delete(br)

    def status(self, lab, node):
        return "running" if links.exists(switch_bridge(lab, node.name)) else "absent"

    def attach(self, lab, node, iface, bridge, host_if):
        if links.exists(host_if):
            return
        port = "sp" + host_if[2:]
        util.run(["ip", "link", "add", host_if, "type", "veth", "peer", "name", port])
        util.run(["ip", "link", "set", host_if, "master", bridge])
        util.run(["ip", "link", "set", port, "master", switch_bridge(lab, node.name)])
        util.run(["ip", "link", "set", host_if, "up"])
        util.run(["ip", "link", "set", port, "up"])

    def has_console(self):
        return False

    def console_command(self, lab, node, template):
        return []

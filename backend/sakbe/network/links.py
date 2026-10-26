"""Virtual cables: one Linux bridge per link, one host-side device per endpoint.

    node A                 host                          node B
    [eth1] <-veth-> [svXXXXXXXXa] -- br sk-XXXXXXXX -- [svXXXXXXXXb] <-veth-> [eth1]

A bridge per link lets either side start or stop independently, lets us
capture traffic, and lets the built-in Ethernet switch plug in like any node.
"""

from sakbe import util


def bridge_name(link_id: str) -> str:
    return f"sk-{link_id}"


def host_if(link_id: str, side: str) -> str:
    return f"sv{link_id}{side}"


def exists(dev: str) -> bool:
    return util.run(["ip", "link", "show", dev], check=False) != ""


def delete(dev: str) -> None:
    util.run(["ip", "link", "del", dev], check=False)


def allow_bridged_traffic() -> None:
    """Let frames cross SakbeLab bridges when the host firewall filters bridges.

    Docker loads br_netfilter (bridge-nf-call-iptables=1) and sets the FORWARD
    policy to DROP, which silently breaks every lab link. The global sysctl
    overrides the per-bridge nf_call_* options, so we add explicit rules.
    """
    for tool in ("iptables", "ip6tables"):
        chain = "DOCKER-USER"
        if util.run([tool, "-n", "-L", chain], check=False) == "":
            chain = "FORWARD"
        for rule in (["-i", "sk-+", "-o", "sk-+"], ["-i", "ss-+", "-o", "ss-+"]):
            rule = [*rule, "-j", "ACCEPT"]
            try:
                util.run([tool, "-C", chain, *rule])
            except util.CommandError:
                util.run([tool, "-I", chain, *rule], check=False)


def ensure_bridge(name: str) -> None:
    if exists(name):
        return
    allow_bridged_traffic()
    util.run(["ip", "link", "add", name, "type", "bridge"])
    util.run(
        [
            "ip",
            "link",
            "set",
            name,
            "type",
            "bridge",
            "nf_call_iptables",
            "0",
            "nf_call_ip6tables",
            "0",
            "nf_call_arptables",
            "0",
        ],
        check=False,
    )
    # Forward link-local protocols (LLDP, LACP...) like a real cable would.
    util.run(["ip", "link", "set", name, "type", "bridge", "group_fwd_mask", "0x4000"], check=False)
    util.run(["ip", "link", "set", name, "up"])


def veth_into_netns(pid: int, iface: str, bridge: str, host: str) -> None:
    """Create a veth pair, plug `host` into `bridge` and move the peer into a netns."""
    if exists(host):
        return
    peer = "sp" + host[2:]
    util.run(["ip", "link", "add", host, "type", "veth", "peer", "name", peer])
    util.run(["ip", "link", "set", host, "master", bridge])
    util.run(["ip", "link", "set", host, "up"])
    util.run(["ip", "link", "set", peer, "netns", str(pid)])
    ns = ["nsenter", "-t", str(pid), "-n", "ip", "link", "set"]
    util.run([*ns, peer, "name", iface])
    util.run([*ns, iface, "up"])


def remove_link(link_id: str) -> None:
    """Remove a link completely. Veth peers disappear with their host ends."""
    for dev in (host_if(link_id, "a"), host_if(link_id, "b"), bridge_name(link_id)):
        delete(dev)

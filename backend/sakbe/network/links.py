"""Virtual cables: one Linux bridge per link, one veth pair per endpoint.

    node A netns            host                 node B netns
    [eth1] <-veth-> [svXXXXXXXXa] -- br sk-XXXXXXXX -- [svXXXXXXXXb] <-veth-> [eth1]

A bridge per link (instead of a direct veth) lets us capture traffic and later
attach more than two endpoints, like a hub or an unmanaged switch.
"""

import hashlib

from sakbe import util


def link_id(lab: str, a: str, b: str) -> str:
    return hashlib.sha1(f"{lab}|{a}|{b}".encode()).hexdigest()[:8]


def bridge_name(lid: str) -> str:
    return f"sk-{lid}"


def _ns(pid: int, *args: str) -> None:
    util.run(["nsenter", "-t", str(pid), "-n", "ip", *args])


def allow_bridged_traffic() -> None:
    """Let frames cross SakbeLab bridges when the host firewall filters bridges.

    Docker loads br_netfilter (bridge-nf-call-iptables=1) and sets the FORWARD
    policy to DROP, which silently breaks every lab link. The global sysctl
    overrides the per-bridge nf_call_* options, so we add an explicit rule.
    """
    for tool in ("iptables", "ip6tables"):
        chain = "DOCKER-USER"
        if util.run([tool, "-n", "-L", chain], check=False) == "":
            chain = "FORWARD"
        rule = ["-i", "sk-+", "-o", "sk-+", "-j", "ACCEPT"]
        try:
            util.run([tool, "-C", chain, *rule])
        except util.CommandError:
            util.run([tool, "-I", chain, *rule], check=False)


def connect(lid: str, end_a: tuple[int, str], end_b: tuple[int, str]) -> None:
    """Wire two (pid, interface name) endpoints together."""
    allow_bridged_traffic()
    br = bridge_name(lid)
    util.run(["ip", "link", "add", br, "type", "bridge"])
    # Docker enables br_netfilter; keep our bridges out of the host firewall.
    util.run(
        [
            "ip",
            "link",
            "set",
            br,
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
    util.run(["ip", "link", "set", br, "up"])
    for side, (pid, ifname) in (("a", end_a), ("b", end_b)):
        host, peer = f"sv{lid}{side}", f"sp{lid}{side}"
        util.run(["ip", "link", "add", host, "type", "veth", "peer", "name", peer])
        util.run(["ip", "link", "set", host, "master", br])
        util.run(["ip", "link", "set", host, "up"])
        util.run(["ip", "link", "set", peer, "netns", str(pid)])
        _ns(pid, "link", "set", peer, "name", ifname)
        _ns(pid, "link", "set", ifname, "up")


def disconnect(lid: str) -> None:
    """Remove a link. Veth ends disappear with the node namespaces."""
    for dev in (f"sv{lid}a", f"sv{lid}b", bridge_name(lid)):
        util.run(["ip", "link", "del", dev], check=False)

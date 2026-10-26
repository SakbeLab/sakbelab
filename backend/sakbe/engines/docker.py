"""Docker engine: container-based nodes such as FRR routers and Linux hosts.

Containers start with `--network none`, so their only interfaces are the ones
SakbeLab wires in for each link.
"""

import tempfile
from pathlib import Path

from sakbe import util
from sakbe.engines.base import Engine
from sakbe.images.templates import Template
from sakbe.labs.models import Node

FRR_DAEMONS = """\
zebra=yes
bgpd=yes
ospfd=yes
ospf6d=yes
ripd=yes
ripngd=yes
isisd=yes
eigrpd=yes
bfdd=yes
staticd=yes
vtysh_enable=yes
"""

# Works with the official FRR image (docker-start) and Debian/Ubuntu-based images.
FRR_START = (
    "echo 1 > /proc/sys/net/ipv4/ip_forward 2>/dev/null; "
    "echo 1 > /proc/sys/net/ipv6/conf/all/forwarding 2>/dev/null; "
    "chown -R frr:frr /etc/frr 2>/dev/null; "
    "if [ -x /usr/lib/frr/docker-start ]; then exec /usr/lib/frr/docker-start; "
    "else /usr/lib/frr/frrinit.sh start; exec sleep infinity; fi"
)


def container_name(lab: str, node: Node) -> str:
    return f"sakbe-{lab}-{node.name}"


def _frr_config(node: Node) -> str:
    body = (node.config or "").strip()
    if "hostname" not in body:
        body = f"hostname {node.name}\n{body}"
    return f"frr defaults traditional\nservice integrated-vtysh-config\n{body}\n!\n"


class DockerEngine(Engine):
    name = "docker"

    def create(self, lab, node, template: Template):
        image = node.image or template.image
        if not image:
            raise ValueError(f"template '{template.id}' has no image")
        name = container_name(lab, node)
        cmd = [
            "docker",
            "create",
            "--name",
            name,
            "--hostname",
            node.name,
            "--network",
            "none",
            "--privileged",
            "--init",
            "--label",
            f"sakbe.lab={lab}",
            "--label",
            f"sakbe.node={node.name}",
        ]
        ram = node.ram or template.defaults.get("ram")
        if ram:
            cmd += ["--memory", f"{ram}m"]
        cpus = node.cpus or template.defaults.get("cpus")
        if cpus:
            cmd += ["--cpus", str(cpus)]
        flavor = template.config.get("flavor")
        if flavor == "frr":
            # Forwarding is enabled inside the container (works even without IPv6).
            cmd += [
                "--entrypoint",
                "/bin/sh",
                image,
                "-c",
                FRR_START,
            ]
        else:
            cmd += ["--entrypoint", "/bin/sh", image, "-c", "exec sleep infinity"]
        util.run(cmd)
        if flavor == "frr":
            self._copy_files(
                name,
                {
                    "/etc/frr/daemons": FRR_DAEMONS,
                    "/etc/frr/vtysh.conf": "service integrated-vtysh-config\n",
                    "/etc/frr/frr.conf": _frr_config(node),
                },
            )
        elif node.config:
            self._copy_files(name, {"/etc/sakbe-day0.sh": node.config})
        util.run(["docker", "start", name])
        if flavor != "frr" and node.config:
            util.run(["docker", "exec", name, "/bin/sh", "/etc/sakbe-day0.sh"], check=False)

    @staticmethod
    def _copy_files(container: str, files: dict[str, str]) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for i, (dest, content) in enumerate(files.items()):
                src = Path(tmp) / f"f{i}"
                src.write_text(content, encoding="utf-8")
                util.run(["docker", "cp", str(src), f"{container}:{dest}"])

    def destroy(self, lab, node):
        util.run(["docker", "rm", "-f", container_name(lab, node)], check=False)

    def status(self, lab, node):
        out = util.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", container_name(lab, node)],
            check=False,
        ).strip()
        if not out:
            return "absent"
        return "running" if out == "running" else "stopped"

    def pid(self, lab, node):
        out = util.run(["docker", "inspect", "-f", "{{.State.Pid}}", container_name(lab, node)])
        return int(out.strip())

    def console_command(self, lab, node, template):
        return ["docker", "exec", "-it", container_name(lab, node), *template.console.command]

    def save_config(self, lab, node):
        name = container_name(lab, node)
        out = util.run(["docker", "exec", name, "vtysh", "-c", "show running-config"])
        lines = [
            line
            for line in out.splitlines()
            if not line.startswith(
                (
                    "Building configuration",
                    "Current configuration",
                    "frr version",
                    "frr defaults",
                    "service integrated-vtysh-config",
                    "end",
                )
            )
        ]
        return "\n".join(lines).strip("!\n ") + "\n"

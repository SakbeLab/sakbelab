"""QEMU engine: boots the user's QCOW2 (or raw/vmdk) images as full VMs.

Each node is one qemu-system process:
- a per-node overlay disk on top of the user's base image, so the base stays
  pristine and `write memory` inside the appliance persists across stop/start;
- one tap device per interface (`sqXXXXXXXXNN`), opened by QEMU and plugged into
  the link bridge by `attach`, like the IOL engine;
- the serial console on a Unix socket (shown in the browser);
- VNC on a Unix socket for appliances with a graphical console;
- QMP on a Unix socket for status and graceful shutdown.

Needs qemu-system and qemu-img installed, and /dev/kvm for acceptable speed
(falls back to software emulation otherwise).
"""

import contextlib
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from sakbe import settings, util
from sakbe.engines.base import Engine, EngineUnavailable
from sakbe.engines.qmp import QMP
from sakbe.images import store as images
from sakbe.images.templates import Template
from sakbe.labs.models import Node

ARCH_BINARY = {
    "x86_64": "qemu-system-x86_64",
    "i386": "qemu-system-i386",
    "arm64": "qemu-system-aarch64",
}


def workdir(lab: str, node: Node) -> Path:
    return settings.data_dir() / "run" / lab / node.name


def tap_name(lab: str, node: Node, index: int) -> str:
    h = hashlib.sha1(f"{lab}|{node.name}".encode()).hexdigest()[:8]
    return f"sq{h}{index:02d}"


def mac_address(lab: str, node: Node, index: int) -> str:
    h = hashlib.sha1(f"{lab}|{node.name}|{index}".encode()).hexdigest()
    return "02:" + ":".join(h[i : i + 2] for i in range(0, 8, 2)) + f":{index:02x}"


def _pid(path: Path) -> int | None:
    try:
        pid = int(path.read_text())
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        return None


def have_kvm() -> bool:
    return os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)


class QemuEngine(Engine):
    name = "qemu"

    def _binary(self, template: Template) -> str:
        arch = template.config.get("arch", "x86_64")
        binary = ARCH_BINARY.get(arch, f"qemu-system-{arch}")
        if shutil.which(binary) is None:
            raise EngineUnavailable(
                f"Falta {binary}. Instalá QEMU en el servidor (apt-get install qemu-system)."
            )
        return binary

    def _overlay(self, lab, node, template: Template) -> Path:
        wd = workdir(lab, node)
        overlay = wd / "disk.qcow2"
        if overlay.exists():
            return overlay
        image = node.image or template.image
        if not image:
            raise EngineUnavailable(f"La plantilla '{template.name}' no tiene imagen asignada.")
        base = images.kind_dir("qemu") / image
        if not base.exists():
            raise EngineUnavailable(f"Falta la imagen '{image}'. Cargala en Imágenes y plantillas.")
        if shutil.which("qemu-img") is None:
            raise EngineUnavailable("Falta qemu-img. Instalá qemu-utils en el servidor.")
        try:
            info = json.loads(util.run(["qemu-img", "info", "--output=json", str(base)]))
            base_format = info.get("format", "qcow2")
        except (util.CommandError, json.JSONDecodeError):
            base_format = "qcow2"
        util.run(
            [
                "qemu-img",
                "create",
                "-q",
                "-f",
                "qcow2",
                "-b",
                str(base),
                "-F",
                base_format,
                str(overlay),
            ]
        )
        return overlay

    def create(self, lab, node, template: Template):
        wd = workdir(lab, node)
        wd.mkdir(parents=True, exist_ok=True)
        overlay = self._overlay(lab, node, template)
        binary = self._binary(template)

        names = template.interfaces.names()
        (wd / "ifaces.json").write_text(json.dumps(names))
        taps = [tap_name(lab, node, i) for i in range(len(names))]
        for tap in taps:
            if util.run(["ip", "link", "show", tap], check=False) == "":
                util.run(["ip", "tuntap", "add", "dev", tap, "mode", "tap"])
            util.run(["ip", "link", "set", tap, "up"])

        cfg = template.config
        ram = node.ram or template.defaults.get("ram", 1024)
        cpus = node.cpus or template.defaults.get("cpus", 1)
        accel = "kvm:tcg" if have_kvm() else "tcg"
        machine = cfg.get("machine", "pc")
        disk_if = cfg.get("disk_interface", "virtio")
        nic = cfg.get("nic", "virtio-net-pci")

        cmd = [
            binary,
            "-name",
            f"sakbe-{lab}-{node.name}",
            "-machine",
            f"{machine},accel={accel}",
            "-m",
            str(ram),
            "-smp",
            str(cpus),
            "-drive",
            f"file={overlay},if={disk_if},cache=writeback",
            "-serial",
            f"unix:{wd / 'console.sock'},server,nowait",
            "-qmp",
            f"unix:{wd / 'qmp.sock'},server,nowait",
            "-pidfile",
            str(wd / "qemu.pid"),
            "-daemonize",
            "-no-shutdown",
        ]
        if cfg.get("cpu"):
            cmd += ["-cpu", cfg["cpu"]]
        elif have_kvm():
            cmd += ["-cpu", "host"]
        if cfg.get("display") == "vnc":
            cmd += ["-vnc", f"unix:{wd / 'vnc.sock'}"]
        else:
            cmd += ["-display", "none", "-vga", cfg.get("vga", "std")]
        for i, tap in enumerate(taps):
            cmd += [
                "-netdev",
                f"tap,id=net{i},ifname={tap},script=no,downscript=no",
                "-device",
                f"{nic},netdev=net{i},mac={mac_address(lab, node, i)}",
            ]
        config_iso = self._day0_iso(lab, node, template)
        if config_iso:
            cmd += ["-drive", f"file={config_iso},media=cdrom,if=ide"]
        cmd += list(cfg.get("extra_args", []))

        (wd / "qemu.pid").unlink(missing_ok=True)
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0 or not (wd / "qemu.pid").exists():
            self.destroy(lab, node)
            reason = (proc.stderr or proc.stdout).strip().splitlines()
            raise EngineUnavailable(
                f"QEMU no arrancó en {node.name}: {' '.join(reason[-3:]) or 'sin detalles'}"
            )

    def _day0_iso(self, lab, node, template: Template) -> Path | None:
        """Build a cloud-init NoCloud ISO when the template asks for it."""
        if not node.config or template.config.get("config") != "cloud-init":
            return None
        mkiso = shutil.which("genisoimage") or shutil.which("mkisofs") or shutil.which("xorriso")
        if not mkiso:
            return None
        wd = workdir(lab, node)
        seed = wd / "seed"
        seed.mkdir(exist_ok=True)
        (seed / "meta-data").write_text(f"instance-id: {node.name}\nlocal-hostname: {node.name}\n")
        (seed / "user-data").write_text("#cloud-config\n" + node.config)
        iso = wd / "config.iso"
        args = ["-output", str(iso)] if "xorriso" in mkiso else ["-o", str(iso)]
        base = [mkiso, "-quiet"] + (["-as", "genisoimage"] if "xorriso" in mkiso else [])
        util.run(
            [
                *base,
                "-volid",
                "cidata",
                "-joliet",
                "-rock",
                *args,
                str(seed / "user-data"),
                str(seed / "meta-data"),
            ]
        )
        return iso

    def destroy(self, lab, node):
        wd = workdir(lab, node)
        pid = _pid(wd / "qemu.pid")
        if pid:
            with contextlib.suppress(Exception), QMP(str(wd / "qmp.sock"), timeout=2) as qmp:
                qmp.execute("quit")
            for _ in range(30):
                if _pid(wd / "qemu.pid") is None:
                    break
                time.sleep(0.1)
            else:
                with contextlib.suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGKILL)
        for i in range(64):
            tap = tap_name(lab, node, i)
            if util.run(["ip", "link", "show", tap], check=False) == "":
                continue
            util.run(["ip", "link", "del", tap], check=False)
        (wd / "qemu.pid").unlink(missing_ok=True)
        for sock in ("console.sock", "qmp.sock", "vnc.sock"):
            (wd / sock).unlink(missing_ok=True)

    def status(self, lab, node):
        return "running" if _pid(workdir(lab, node) / "qemu.pid") else "absent"

    def attach(self, lab, node, iface, bridge, host_if):
        # host_if is unused: QEMU owns the tap; we just put the tap on the bridge.
        tap = tap_name(lab, node, self._iface_index(lab, node, iface))
        util.run(["ip", "link", "set", tap, "master", bridge])
        util.run(["ip", "link", "set", tap, "up"])

    def _iface_index(self, lab, node, iface) -> int:
        ifaces = json.loads((workdir(lab, node) / "ifaces.json").read_text())
        if iface not in ifaces:
            raise EngineUnavailable(f"'{iface}' no existe en {node.name}.")
        return ifaces.index(iface)

    def console_command(self, lab, node, template):
        sock = workdir(lab, node) / "console.sock"
        return [sys.executable, "-m", "sakbe.engines.socket_console", str(sock), "30"]

    def wipe(self, lab, node):
        shutil.rmtree(workdir(lab, node), ignore_errors=True)

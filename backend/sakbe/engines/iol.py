"""Cisco IOL engine: IOL binaries provided by the user, run natively (no VT-x needed).

Each node gets a working directory that survives stop/start, so `write memory`
inside IOL persists (IOL keeps its NVRAM there), like in GNS3 and EVE-NG.
Networking and the console go through sakbe.engines.iol_wrapper.
"""

import contextlib
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from sakbe import settings, util
from sakbe.engines.base import Engine, EngineUnavailable
from sakbe.images import store as images
from sakbe.images.templates import Template
from sakbe.labs.models import Node

MAX_ID = 511  # instance ids 1..511; the wrapper uses id + 512


def workdir(lab: str, node: Node) -> Path:
    return settings.data_dir() / "run" / lab / node.name


def _alloc_id(wd: Path) -> int:
    id_file = wd / "iol_id"
    if id_file.exists():
        return int(id_file.read_text())
    used = set()
    for f in (settings.data_dir() / "run").glob("*/*/iol_id"):
        with contextlib.suppress(ValueError):
            used.add(int(f.read_text()))
    for i in range(1, MAX_ID + 1):
        if i not in used:
            id_file.write_text(str(i))
            return i
    raise EngineUnavailable("No quedan identificadores IOL libres (máximo 511 equipos IOL).")


def tap_name(lab: str, node: Node, index: int) -> str:
    h = hashlib.sha1(f"{lab}|{node.name}".encode()).hexdigest()[:8]
    return f"si{h}{index:02d}"


def _pid(path: Path) -> int | None:
    try:
        pid = int(path.read_text())
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        return None


class IOLEngine(Engine):
    name = "iol"

    def create(self, lab, node, template: Template):
        image = node.image or template.image
        if not image:
            raise EngineUnavailable(f"La plantilla '{template.name}' no tiene imagen IOL asignada.")
        image_path = images.kind_dir("iol") / image
        if not image_path.exists():
            raise EngineUnavailable(
                f"Falta la imagen IOL '{image}'. Cargala en Imágenes y plantillas."
            )
        wd = workdir(lab, node)
        wd.mkdir(parents=True, exist_ok=True)
        iol_id = _alloc_id(wd)
        names = template.interfaces.names()
        pps = template.interfaces.ports_per_slot or 4
        ports = [
            {"tap": tap_name(lab, node, i), "bay": i // pps, "unit": i % pps, "name": n}
            for i, n in enumerate(names)
        ]
        bays = max(p["bay"] for p in ports) + 1
        ram = node.ram or template.defaults.get("ram", 512)
        command = [str(image_path), "-e", str(bays), "-s", "0", "-m", str(ram), "-n", "1024"]
        nvram = wd / f"nvram_{iol_id:05d}"
        if node.config and not nvram.exists():
            (wd / "startup-config.cfg").write_text(node.config.rstrip() + "\nend\n")
            command += ["-c", "startup-config.cfg"]
        command.append(str(iol_id))
        iourc = images.kind_dir("iol") / "iourc"
        spec = {
            "workdir": str(wd),
            "iol_id": iol_id,
            "bridge_id": iol_id + 512,
            "ports": ports,
            "command": command,
            "iourc": str(iourc) if iourc.exists() else None,
        }
        (wd / "spec.json").write_text(json.dumps(spec, indent=2))
        (wd / "ready").unlink(missing_ok=True)
        log = (wd / "wrapper.log").open("ab")
        proc = subprocess.Popen(
            [sys.executable, "-m", "sakbe.engines.iol_wrapper", str(wd / "spec.json")],
            stdout=log,
            stderr=log,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        (wd / "wrapper.pid").write_text(str(proc.pid))
        for _ in range(50):
            if (wd / "ready").exists():
                return
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        tail = (wd / "wrapper.log").read_text(errors="replace")[-400:]
        self.destroy(lab, node)
        raise EngineUnavailable(f"IOL no arrancó en {node.name}: {tail.strip() or 'sin detalles'}")

    def destroy(self, lab, node):
        wd = workdir(lab, node)
        pid = _pid(wd / "wrapper.pid")
        if pid:
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, signal.SIGTERM)
            for _ in range(50):
                if _pid(wd / "wrapper.pid") is None:
                    break
                time.sleep(0.1)
            else:
                with contextlib.suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGKILL)
        (wd / "wrapper.pid").unlink(missing_ok=True)

    def status(self, lab, node):
        return "running" if _pid(workdir(lab, node) / "wrapper.pid") else "absent"

    def attach(self, lab, node, iface, bridge, host_if):
        spec = json.loads((workdir(lab, node) / "spec.json").read_text())
        tap = next((p["tap"] for p in spec["ports"] if p["name"] == iface), None)
        if not tap:
            raise EngineUnavailable(f"'{iface}' no existe en {node.name}.")
        util.run(["ip", "link", "set", tap, "master", bridge])
        util.run(["ip", "link", "set", tap, "up"])

    def console_command(self, lab, node, template):
        sock = workdir(lab, node) / "console.sock"
        return [sys.executable, "-m", "sakbe.engines.iol_console", str(sock)]

    def save_config(self, lab, node):
        """Best effort: read `show running-config` through the console."""
        sock_path = workdir(lab, node) / "console.sock"
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect(str(sock_path))
        except OSError:
            return None
        out = bytearray()
        with s:
            for cmd in (b"\x1a\r", b"enable\r", b"terminal length 0\r", b"show running-config\r"):
                s.sendall(cmd)
                time.sleep(0.4)
            deadline = time.time() + 8
            while time.time() < deadline:
                try:
                    chunk = s.recv(65536)
                except TimeoutError:
                    chunk = b""
                out.extend(chunk)
                if b"\nend" in out[-4000:]:
                    break
        text = out.decode(errors="replace").replace("\r", "")
        start = text.rfind("Building configuration")
        end = text.rfind("\nend")
        if start < 0 or end < 0:
            return None
        lines = text[start:end].splitlines()[1:]
        while lines and (
            not lines[0].strip() or lines[0].startswith(("Current configuration", "!"))
        ):
            lines.pop(0)
        return "\n".join(lines).strip() + "\n"

    def wipe(self, lab, node):
        shutil.rmtree(workdir(lab, node), ignore_errors=True)

"""Runs one Cisco IOL instance and bridges it to Linux.

IOL talks to its neighbours with the IOU "netio" protocol: Unix datagram sockets
in /tmp/netio<uid>/<instance id>, each frame prefixed with an 8-byte header.
NETMAP (in the working directory) tells IOL which peer id owns each port.

This wrapper is that peer for every interface: it owns one tap device per IOL
interface (`siXXXXXXXXNN`) and copies frames between the tap and the IOL socket.
SakbeLab then plugs the taps into link bridges like any other node.

It also runs IOL on a pseudo-terminal and serves that console on a Unix socket
(`console.sock`), keeping a short scrollback for clients that join later.

    python -m sakbe.engines.iol_wrapper <spec.json>
"""

import fcntl
import json
import os
import pty
import select
import signal
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

TUNSETIFF = 0x400454CA
IFF_TAP = 0x0002
IFF_NO_PI = 0x1000
HEADER = 8
SCROLLBACK = 64 * 1024


def port_number(bay: int, unit: int) -> int:
    """IOU encodes Ethernet<bay>/<unit> as bay + unit * 16."""
    return bay + unit * 16


def iou_header(dst_id: int, src_id: int, dst_port: int, src_port: int) -> bytes:
    return struct.pack("!HHBBBB", dst_id, src_id, dst_port, src_port, 1, 0)


def open_tap(name: str) -> int:
    fd = os.open("/dev/net/tun", os.O_RDWR | os.O_NONBLOCK)
    fcntl.ioctl(fd, TUNSETIFF, struct.pack("16sH", name.encode(), IFF_TAP | IFF_NO_PI))
    subprocess.run(["ip", "link", "set", name, "up"], check=False)
    return fd


def netio_dir() -> Path:
    path = Path(f"/tmp/netio{os.getuid()}")
    path.mkdir(mode=0o700, exist_ok=True)
    return path


def run(spec: dict) -> None:
    workdir = Path(spec["workdir"])
    iol_id = int(spec["iol_id"])
    bridge_id = int(spec["bridge_id"])
    ports = spec["ports"]  # [{"tap": ..., "bay": 0, "unit": 0}, ...]

    (workdir / "NETMAP").write_text(
        "".join(
            f"{iol_id}:{p['bay']}/{p['unit']} {bridge_id}:{p['bay']}/{p['unit']}\n" for p in ports
        )
    )

    taps: dict[int, int] = {}  # fd -> iou port
    port_fd: dict[int, int] = {}  # iou port -> fd
    for p in ports:
        fd = open_tap(p["tap"])
        num = port_number(p["bay"], p["unit"])
        taps[fd] = num
        port_fd[num] = fd

    ndir = netio_dir()
    bridge_path = ndir / str(bridge_id)
    bridge_path.unlink(missing_ok=True)
    netio = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    netio.bind(str(bridge_path))
    netio.setblocking(False)
    iol_path = str(ndir / str(iol_id))

    console_path = workdir / "console.sock"
    console_path.unlink(missing_ok=True)
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(console_path))
    listener.listen(8)
    listener.setblocking(False)

    env = dict(os.environ)
    if spec.get("iourc"):
        env["IOURC"] = spec["iourc"]
    pid, master = pty.fork()
    if pid == 0:
        os.chdir(workdir)
        try:
            os.execve(spec["command"][0], spec["command"], env)
        except OSError as exc:
            hint = ""
            if isinstance(exc, FileNotFoundError) and Path(spec["command"][0]).exists():
                hint = " (es un binario de 32 bits: faltan las librerías libc6:i386)"
            elif exc.errno == 8:
                hint = " (formato de ejecutable no soportado por este sistema)"
            os.write(1, f"No se pudo ejecutar la imagen IOL: {exc.strerror}{hint}\r\n".encode())
            os._exit(127)
    os.set_blocking(master, False)
    (workdir / "iol.pid").write_text(str(pid))

    stopping = False
    stopping_by_signal = False

    def stop(*_):
        nonlocal stopping, stopping_by_signal
        stopping = True
        stopping_by_signal = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    clients: list[socket.socket] = []
    history = bytearray()
    ready = workdir / "ready"
    (workdir / "exited").unlink(missing_ok=True)
    ready.write_text("1")

    try:
        while not stopping:
            fds = [netio, listener, master, *taps.keys(), *clients]
            try:
                readable, _, _ = select.select(fds, [], [], 1.0)
            except InterruptedError:
                continue
            for r in readable:
                if r is netio:
                    try:
                        data = netio.recv(65536)
                    except BlockingIOError:
                        continue
                    if len(data) <= HEADER:
                        continue
                    fd = port_fd.get(data[4])
                    if fd is not None:
                        try:
                            os.write(fd, data[HEADER:])
                        except OSError:
                            pass
                elif r is listener:
                    conn, _ = listener.accept()
                    conn.setblocking(False)
                    if history:
                        try:
                            conn.sendall(bytes(history))
                        except OSError:
                            pass
                    clients.append(conn)
                elif r is master:
                    try:
                        out = os.read(master, 65536)
                    except OSError:
                        out = b""
                    if not out:
                        stopping = True
                        break
                    history.extend(out)
                    del history[:-SCROLLBACK]
                    for c in list(clients):
                        try:
                            c.sendall(out)
                        except OSError:
                            clients.remove(c)
                elif r in clients:
                    try:
                        data = r.recv(4096)
                    except OSError:
                        data = b""
                    if not data:
                        clients.remove(r)
                        r.close()
                    else:
                        os.write(master, data)
                else:
                    try:
                        frame = os.read(r, 65536)
                    except OSError:
                        continue
                    num = taps[r]
                    try:
                        netio.sendto(iou_header(iol_id, bridge_id, num, num) + frame, iol_path)
                    except OSError:
                        pass  # IOL not listening yet
    finally:
        if not stopping_by_signal:
            # IOL exited by itself: keep what it printed, it explains why.
            text = history.decode(errors="replace").replace("\r", "").strip()
            sys.stderr.write(
                f"IOL terminó solo. Últimos mensajes:\n{text[-2000:] or '(ninguno)'}\n"
            )
            sys.stderr.flush()
            (workdir / "exited").write_text(text[-2000:])
        try:
            os.kill(pid, signal.SIGTERM)
            for _ in range(30):
                if os.waitpid(pid, os.WNOHANG)[0]:
                    break
                time.sleep(0.1)
            else:
                os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, ChildProcessError):
            pass
        for path in (bridge_path, console_path, ready):
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    run(json.loads(Path(sys.argv[1]).read_text()))

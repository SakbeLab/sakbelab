"""Attach a terminal to a node console served on a Unix stream socket.

    python -m sakbe.engines.socket_console <socket>

Used by the IOL and QEMU engines: both expose their serial console on a Unix
socket, and the web console runs this on a PTY to bridge the two.
"""

import os
import select
import socket
import sys
import termios
import time
import tty


def main(path: str, wait: float = 0.0) -> None:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    deadline = time.time() + wait
    while True:
        try:
            sock.connect(path)
            break
        except OSError:
            if time.time() >= deadline:
                sys.stdout.write("La consola no está disponible: ¿el equipo está encendido?\r\n")
                return
            time.sleep(0.3)
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd) if os.isatty(fd) else None
    if saved:
        tty.setraw(fd)
    try:
        sock.sendall(b"\r")
        while True:
            readable, _, _ = select.select([sock, fd], [], [])
            if sock in readable:
                data = sock.recv(65536)
                if not data:
                    break
                os.write(sys.stdout.fileno(), data)
            if fd in readable:
                data = os.read(fd, 4096)
                if not data:
                    break
                sock.sendall(data)
    finally:
        if saved:
            termios.tcsetattr(fd, termios.TCSADRAIN, saved)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.0)

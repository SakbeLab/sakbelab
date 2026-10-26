"""Attach a terminal to an IOL console socket: python -m sakbe.engines.iol_console <socket>."""

import os
import select
import socket
import sys
import termios
import tty


def main(path: str) -> None:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(path)
    except OSError:
        sys.stdout.write("La consola no está disponible: ¿el equipo está encendido?\r\n")
        return
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
    main(sys.argv[1])

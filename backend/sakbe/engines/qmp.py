"""Tiny QMP (QEMU Machine Protocol) client over a Unix socket."""

import json
import socket


class QMP:
    def __init__(self, path: str, timeout: float = 5.0):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect(path)
        self._buf = b""
        self._readline()  # greeting
        self.execute("qmp_capabilities")

    def _readline(self) -> dict:
        while b"\n" not in self._buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("QMP cerró la conexión")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return json.loads(line)

    def execute(self, command: str, **arguments) -> dict:
        msg = {"execute": command}
        if arguments:
            msg["arguments"] = arguments
        self.sock.sendall((json.dumps(msg) + "\r\n").encode())
        while True:
            reply = self._readline()
            if "event" in reply:  # skip async events, wait for the response
                continue
            if "error" in reply:
                raise RuntimeError(reply["error"].get("desc", "error QMP"))
            return reply.get("return", {})

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.close()

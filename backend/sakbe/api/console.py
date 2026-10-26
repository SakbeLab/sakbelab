"""Web console: bridges a WebSocket to a PTY running the node's console command.

Protocol (client -> server, JSON text frames):
    {"t": "i", "d": "<keystrokes>"}        input
    {"t": "r", "c": <cols>, "r": <rows>}   terminal resize
Server -> client: raw terminal output as text frames.
"""

import asyncio
import codecs
import contextlib
import fcntl
import json
import os
import pty
import signal
import struct
import subprocess
import termios

from fastapi import WebSocket, WebSocketDisconnect


def _resize(fd: int, cols: int, rows: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


async def bridge(ws: WebSocket, command: list[str]) -> None:
    master, slave = pty.openpty()
    _resize(master, 100, 30)
    proc = subprocess.Popen(  # noqa: ASYNC220 (spawning is instant; I/O is async)
        command,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        start_new_session=True,
        close_fds=True,
    )
    os.close(slave)
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[bytes] = asyncio.Queue()

    def on_readable() -> None:
        try:
            data = os.read(master, 65536)
        except OSError:
            data = b""
        if not data:
            loop.remove_reader(master)
        queue.put_nowait(data)

    loop.add_reader(master, on_readable)

    async def pump_output() -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        while True:
            data = await queue.get()
            if not data:
                break
            await ws.send_text(decoder.decode(data))
        with contextlib.suppress(Exception):
            await ws.send_text("\r\n\x1b[90m[sesión terminada]\x1b[0m\r\n")
            await ws.close()

    output = asyncio.create_task(pump_output())
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            if msg.get("t") == "i":
                os.write(master, msg.get("d", "").encode())
            elif msg.get("t") == "r":
                _resize(master, int(msg["c"]), int(msg["r"]))
    except (WebSocketDisconnect, RuntimeError, OSError):
        pass
    finally:
        with contextlib.suppress(Exception):
            loop.remove_reader(master)
        if proc.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGHUP)
        with contextlib.suppress(OSError):
            os.close(master)
        output.cancel()
        await asyncio.to_thread(proc.wait)

#!/usr/bin/env python3
# ruff: noqa: SIM115 (test fixture: the log stays open for the whole process)
"""Fake IOL for tests: speaks the IOU netio protocol and echoes every frame back.

Usage like IOL: fake_iol.py [options] <instance id>. Reads NETMAP from the cwd,
logs each received header to rx.log and offers a tiny console on stdin/stdout.
"""

import os
import select
import socket
import struct
import sys

iol_id = int(sys.argv[-1])
ndir = f"/tmp/netio{os.getuid()}"
os.makedirs(ndir, exist_ok=True)
path = f"{ndir}/{iol_id}"
if os.path.exists(path):
    os.unlink(path)
sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
sock.bind(path)
log = open("rx.log", "a", buffering=1)
log.write("ARGS " + " ".join(sys.argv[1:]) + "\n")
if "-c" in sys.argv:
    log.write("CONFIG " + open(sys.argv[sys.argv.index("-c") + 1]).read().replace("\n", "|") + "\n")
os.write(1, b"\r\nFake IOL\r\nRouter>")
buf = b""
while True:
    r, _, _ = select.select([sock, 0], [], [])
    if sock in r:
        data = sock.recv(65536)
        dst, src, dport, sport, kind, chan = struct.unpack("!HHBBBB", data[:8])
        log.write(f"RX dst={dst} src={src} dport={dport} sport={sport} len={len(data) - 8}\n")
        reply = struct.pack("!HHBBBB", src, dst, sport, dport, 1, 0) + data[8:]
        sock.sendto(reply, f"{ndir}/{src}")
    if 0 in r:
        ch = os.read(0, 1024)
        if not ch:
            break
        os.write(1, ch)
        if b"\r" in ch:
            os.write(1, b"\nRouter>")

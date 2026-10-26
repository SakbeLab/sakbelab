"""Integration test of the IOL wrapper with a fake IOL. Needs root and /dev/net/tun."""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from sakbe.engines.iol_wrapper import iou_header, port_number

FAKE = Path(__file__).parent / "fixtures" / "fake_iol.py"
can_tap = os.geteuid() == 0 and os.path.exists("/dev/net/tun")


def test_port_numbering():
    assert port_number(0, 0) == 0
    assert port_number(1, 0) == 1
    assert port_number(0, 1) == 16
    assert port_number(2, 3) == 50
    assert iou_header(5, 517, 16, 16) == bytes([0, 5, 2, 5, 16, 16, 1, 0])


@pytest.mark.skipif(not can_tap, reason="needs root and /dev/net/tun")
def test_wrapper_bridges_frames_and_console(tmp_path):
    tap = "sitest0000"
    spec = {
        "workdir": str(tmp_path),
        "iol_id": 501,
        "bridge_id": 1013,
        "ports": [{"tap": tap, "bay": 0, "unit": 1, "name": "Ethernet0/1"}],
        "command": [sys.executable, str(FAKE), "-e", "1", "-c", "startup.cfg", "501"],
        "iourc": None,
    }
    (tmp_path / "startup.cfg").write_text("hostname R1\nend\n")
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    proc = subprocess.Popen(
        [sys.executable, "-m", "sakbe.engines.iol_wrapper", str(tmp_path / "spec.json")]
    )
    try:
        for _ in range(50):
            if (tmp_path / "ready").exists():
                break
            time.sleep(0.1)
        assert (tmp_path / "NETMAP").read_text() == "501:0/1 1013:0/1\n"

        raw = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
        raw.bind((tap, 0))
        raw.settimeout(3)
        frame = (
            bytes.fromhex("ffffffffffff020000000001") + b"\x88\xb5" + b"sakbe-test".ljust(46, b"\0")
        )
        raw.send(frame)
        echoed = None
        deadline = time.time() + 3
        while time.time() < deadline:
            data = raw.recv(2048)
            if data[: len(frame)] == frame and data is not None:
                echoed = data
                break
        assert echoed is not None, "frame did not come back through the fake IOL"
        log = (tmp_path / "rx.log").read_text()
        assert "RX dst=501 src=1013 dport=16 sport=16" in log
        assert "CONFIG hostname R1|end|" in log

        con = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        con.connect(str(tmp_path / "console.sock"))
        con.settimeout(2)
        got = b""
        while b"Router>" not in got:
            got += con.recv(4096)
        con.sendall(b"show version\r")
        time.sleep(0.3)
        got = con.recv(4096)
        assert b"show version" in got
    finally:
        proc.terminate()
        proc.wait(5)
    assert not (tmp_path / "console.sock").exists()

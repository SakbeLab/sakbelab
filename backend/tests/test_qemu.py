"""QEMU engine: command construction and lifecycle, with host commands faked."""

import subprocess
from pathlib import Path

import pytest

from sakbe.engines import qemu
from sakbe.engines.base import EngineUnavailable
from sakbe.images.templates import Template
from sakbe.labs.models import Node


@pytest.fixture()
def fake_host(tmp_path, monkeypatch):
    monkeypatch.setenv("SAKBE_DATA", str(tmp_path))
    base = tmp_path / "images" / "qemu" / "fortios.qcow2"
    base.parent.mkdir(parents=True)
    base.write_bytes(b"QFI\xfb" + b"\0" * 100)

    monkeypatch.setattr(qemu.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(qemu, "have_kvm", lambda: False)

    taps: set[str] = set()
    runs: list[list[str]] = []

    def fake_util_run(cmd, check=True, input=None):
        runs.append(cmd)
        if cmd[:3] == ["ip", "link", "add"] or cmd[:4] == ["ip", "tuntap", "add", "dev"]:
            taps.add(cmd[cmd.index("dev") + 1] if "dev" in cmd else cmd[3])
        elif cmd[:3] == ["ip", "link", "del"]:
            taps.discard(cmd[3])
        elif cmd[:3] == ["ip", "link", "show"]:
            return f"1: {cmd[3]}\n" if cmd[3] in taps else ""
        elif cmd[:2] == ["qemu-img"] and cmd[2] == "info":
            return '{"format": "qcow2"}'
        elif cmd[:2] == ["qemu-img"] and cmd[2] == "create":
            Path(cmd[-1]).write_bytes(b"overlay")
        return ""

    def fake_subprocess_run(cmd, check=False, capture_output=True, text=True):
        runs.append(cmd)
        if "-pidfile" in cmd:
            Path(cmd[cmd.index("-pidfile") + 1]).write_text("4242")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(qemu.util, "run", fake_util_run)
    monkeypatch.setattr(qemu.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(qemu.os, "kill", lambda pid, sig: None)
    return runs


def _template(**config):
    return Template(
        id="fortigate",
        name="FortiGate",
        engine="qemu",
        image="fortios.qcow2",
        defaults={"ram": 2048, "cpus": 2},
        interfaces={"count": 4, "naming": "port{index}", "start": 1},
        config=config,
    )


def test_deterministic_helpers():
    n = Node(name="R1", template="fortigate")
    assert qemu.tap_name("lab", n, 0).startswith("sq")
    assert qemu.tap_name("lab", n, 3).endswith("03")
    assert qemu.tap_name("lab", n, 0) == qemu.tap_name("lab", n, 0)
    mac = qemu.mac_address("lab", n, 1)
    assert mac.startswith("02:") and mac.endswith(":01") and len(mac.split(":")) == 6


def test_create_builds_qemu_command(fake_host):
    runs = fake_host
    node = Node(name="FW1", template="fortigate", ram=4096)
    qemu.QemuEngine().create("lab1", node, _template())

    qemu_cmd = next(c for c in runs if c and str(c[0]).startswith("qemu-system"))
    joined = " ".join(qemu_cmd)
    assert "-m 4096" in joined  # per-node RAM overrides the template
    assert "-smp 2" in joined  # cpus from the template
    assert "accel=tcg" in joined  # no kvm in the test host
    assert "if=virtio" in joined
    assert joined.count("-netdev tap,") == 4
    assert "-serial unix:" in joined and "console.sock,server,nowait" in joined
    assert "-qmp unix:" in joined
    # taps created up front and named deterministically
    created = [c[4] for c in runs if c[:4] == ["ip", "tuntap", "add", "dev"]]
    assert created == [qemu.tap_name("lab1", node, i) for i in range(4)]


def test_display_modes(fake_host):
    node = Node(name="DESK", template="fortigate")
    qemu.QemuEngine().create("lab", node, _template(display="vnc"))
    vnc_cmd = next(c for c in fake_host if c and str(c[0]).startswith("qemu-system"))
    assert any("vnc.sock" in a for a in vnc_cmd)
    assert "-display" not in vnc_cmd


def test_nic_and_disk_from_template(fake_host):
    node = Node(name="X", template="fortigate")
    qemu.QemuEngine().create("lab", node, _template(nic="e1000", disk_interface="ide"))
    cmd = " ".join(next(c for c in fake_host if c and str(c[0]).startswith("qemu-system")))
    assert "e1000,netdev=net0" in cmd
    assert "if=ide" in cmd


def test_attach_puts_tap_on_bridge(fake_host):
    node = Node(name="FW1", template="fortigate")
    eng = qemu.QemuEngine()
    eng.create("lab1", node, _template())
    eng.attach("lab1", node, "port2", "sk-abcd1234", "sv-unused")
    tap = qemu.tap_name("lab1", node, 1)  # port2 is index 1 (start=1)
    assert ["ip", "link", "set", tap, "master", "sk-abcd1234"] in fake_host


def test_missing_image_is_reported(fake_host):
    node = Node(name="Y", template="fortigate", image="noexiste.qcow2")
    with pytest.raises(EngineUnavailable, match="Falta la imagen"):
        qemu.QemuEngine().create("lab", node, _template())


def test_status_and_registration():
    from sakbe import engines

    assert isinstance(engines.get("qemu"), qemu.QemuEngine)
    assert qemu.QemuEngine().status("nolab", Node(name="Z", template="fortigate")) == "absent"

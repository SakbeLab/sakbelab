from sakbe import Lab
from sakbe.sdk import Lab as SdkLab
from tests.conftest import EXAMPLE


def test_lazy_import():
    assert Lab is SdkLab


def test_build_lab_as_code():
    lab = Lab("anillo", server="http://ejemplo")
    routers = [lab.node(f"R{i}", template="frr") for i in range(1, 7)]
    for i, r in enumerate(routers):
        lab.link(r["eth1"], routers[(i + 1) % len(routers)]["eth2"])
    routers[0].config("""
        hostname R1
        interface eth1
         ip address 10.0.0.1/30
    """)
    d = lab.to_dict()
    assert len(d["nodes"]) == 6 and len(d["links"]) == 6
    assert d["links"][0] == {"a": "R1:eth1", "b": "R2:eth2"}
    assert d["nodes"][0]["config"] == "hostname R1\ninterface eth1\n ip address 10.0.0.1/30\n"
    # Grid placement: 5 per row.
    assert (d["nodes"][5]["x"], d["nodes"][5]["y"]) == (100, 260)


def test_yaml_roundtrip(tmp_path):
    path = tmp_path / "fase0.yml"
    path.write_text(EXAMPLE)
    lab = Lab.from_yaml(path)
    assert lab.name == "fase0"
    assert lab.links == [("R1:eth1", "R2:eth1")]
    again = tmp_path / "again.yml"
    again.write_text(lab.to_yaml())
    assert Lab.from_yaml(again).to_dict() == lab.to_dict()

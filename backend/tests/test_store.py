from sakbe.labs.store import lab_from_yaml, lab_to_yaml

YAML = """
name: demo
nodes:
  R1:
    template: frr
    config: |
      hostname R1
      interface eth1
       ip address 10.0.0.1/30
  R2: {template: frr}
links:
  - [R1:eth1, R2:eth1]
"""


def test_roundtrip():
    lab = lab_from_yaml(YAML)
    assert [n.name for n in lab.nodes] == ["R1", "R2"]
    again = lab_from_yaml(lab_to_yaml(lab))
    assert again == lab
    assert "ip address 10.0.0.1/30" in again.node("R1").config


def test_interface_used_twice_is_rejected():
    import pytest
    from pydantic import ValidationError

    bad = YAML + "  - [R1:eth1, R2:eth2]\n"
    with pytest.raises(ValidationError):
        lab_from_yaml(bad)

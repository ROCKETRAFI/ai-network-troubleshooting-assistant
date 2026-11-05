from pathlib import Path
from unittest.mock import patch

from src.netbox_client import MockNetBox
from src.topology_vision import describe_topology


NETBOX = MockNetBox(Path("data/netbox_mock.json"))


def test_describe_topology_marks_unknown_devices():
    payload = """
    {
      "devices": ["R1", "R99"],
      "links": [{"from": "R1", "to": "R99", "subnet": "10.9.9.0/30"}],
      "protocols": ["ospf"],
      "summary": "Two routers",
      "suggested_change": "Connect R1 and R2 with OSPF on 10.1.1.0/30 area 0"
    }
    """
    with patch("src.topology_vision.generate_vision", return_value=(payload, None)):
        result = describe_topology(b"fake-image", "image/png", NETBOX)
    assert result["ok"] is True
    assert "R1" in result["in_inventory"]
    assert "R99" in result["unknown_devices"]


def test_describe_topology_requires_image():
    result = describe_topology(b"", "image/png", NETBOX)
    assert result["ok"] is False

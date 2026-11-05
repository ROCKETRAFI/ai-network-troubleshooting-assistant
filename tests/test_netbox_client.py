from pathlib import Path

from src.netbox_client import MockNetBox


NETBOX = MockNetBox(Path("data/netbox_mock.json"))


def test_device_exists():
    assert NETBOX.device_exists("R1")


def test_missing_device_does_not_exist():
    assert not NETBOX.device_exists("R99")


def test_interface_exists():
    assert NETBOX.interface_exists("R1", "GigabitEthernet0/0")


def test_core_device_role():
    assert NETBOX.is_core_device("R1")


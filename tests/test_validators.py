from pathlib import Path

from src.intent_parser import parse_intent
from src.netbox_client import MockNetBox
from src.validators import validate_intent


NETBOX = MockNetBox(Path("data/netbox_mock.json"))


def test_valid_ospf_intent_passes():
    intent = parse_intent("Connect R1 and R2 with OSPF on 10.1.1.0/30 area 0")
    result = validate_intent(intent, NETBOX)
    assert result.ok


def test_unknown_device_fails():
    intent = parse_intent("Connect R99 with OSPF on 10.1.1.0/30 area 0")
    result = validate_intent(intent, NETBOX)
    assert not result.ok


def test_missing_bgp_asn_fails():
    intent = parse_intent("Add BGP neighbor 10.1.2.2 on R1")
    result = validate_intent(intent, NETBOX)
    assert not result.ok


def test_invalid_protocol_fails():
    intent = parse_intent("Configure RIP on R1")
    result = validate_intent(intent, NETBOX)
    assert not result.ok


from pathlib import Path

from src.intent_parser import parse_intent
from src.netbox_client import MockNetBox
from src.risk_scorer import score_risk
from src.validators import validate_intent


NETBOX = MockNetBox(Path("data/netbox_mock.json"))


def test_ospf_risk_is_not_critical_for_small_change():
    intent = parse_intent("Add OSPF on R2 network 10.1.1.0/30 area 0")
    validation = validate_intent(intent, NETBOX)
    risk = score_risk(intent, validation)
    assert risk.level in {"Low", "Medium"}


def test_bgp_risk_is_higher_than_ospf():
    bgp = parse_intent(
        "Add BGP neighbor 10.1.2.2 on R1 with local ASN 65001 and remote ASN 65002"
    )
    ospf = parse_intent("Add OSPF on R2 network 10.1.1.0/30 area 0")
    bgp_result = validate_intent(bgp, NETBOX)
    ospf_result = validate_intent(ospf, NETBOX)
    assert score_risk(bgp, bgp_result).score > score_risk(ospf, ospf_result).score


def test_remove_mode_increases_risk():
    intent = parse_intent("Remove OSPF network 10.1.1.0/30 area 0 from R1")
    validation = validate_intent(intent, NETBOX)
    risk = score_risk(intent, validation)
    assert risk.score >= 40


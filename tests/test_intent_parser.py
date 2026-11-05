from src.intent_parser import parse_intent


def test_parse_ospf_intent():
    intent = parse_intent("Connect R1 and R2 with OSPF on 10.1.1.0/30 area 0")
    assert intent.protocol == "ospf"
    assert intent.devices == ["R1", "R2"]
    assert intent.network == "10.1.1.0/30"
    assert intent.area == "0"


def test_parse_bgp_intent():
    intent = parse_intent(
        "Add BGP neighbor 10.1.2.2 on R1 with local ASN 65001 and remote ASN 65002"
    )
    assert intent.protocol == "bgp"
    assert intent.neighbor_ip == "10.1.2.2"
    assert intent.local_asn == "65001"
    assert intent.remote_asn == "65002"


def test_parse_remove_mode():
    intent = parse_intent("Remove OSPF network 10.1.1.0/30 area 0 from R1")
    assert intent.mode == "remove"


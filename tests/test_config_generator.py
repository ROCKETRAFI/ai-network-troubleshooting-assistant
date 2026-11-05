from src.config_generator import generate_config
from src.intent_parser import parse_intent


def test_generate_ospf_config():
    intent = parse_intent("Connect R1 with OSPF on 10.1.1.0/30 area 0")
    config = generate_config(intent).to_text()
    assert "router ospf 1" in config
    assert "network 10.1.1.0 0.0.0.3 area 0" in config


def test_generate_bgp_config():
    intent = parse_intent(
        "Add BGP neighbor 10.1.2.2 on R1 with local ASN 65001 and remote ASN 65002"
    )
    config = generate_config(intent).to_text()
    assert "router bgp 65001" in config
    assert "neighbor 10.1.2.2 remote-as 65002" in config


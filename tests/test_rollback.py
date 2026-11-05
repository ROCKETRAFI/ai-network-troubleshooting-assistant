from src.intent_parser import parse_intent
from src.rollback import generate_rollback


def test_rollback_for_add_ospf_uses_no_network():
    intent = parse_intent("Add OSPF on R1 network 10.1.1.0/30 area 0")
    rollback = generate_rollback(intent).to_text()
    assert "no network 10.1.1.0 0.0.0.3 area 0" in rollback


def test_rollback_for_remove_bgp_readds_neighbor():
    intent = parse_intent(
        "Remove BGP neighbor 10.1.2.2 on R1 with local ASN 65001 and remote ASN 65002"
    )
    rollback = generate_rollback(intent).to_text()
    assert "neighbor 10.1.2.2 remote-as 65002" in rollback


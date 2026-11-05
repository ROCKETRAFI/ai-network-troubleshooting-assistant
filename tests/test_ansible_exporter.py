from src.ansible_exporter import export_playbook
from src.config_generator import generate_config
from src.intent_parser import parse_intent


def test_export_playbook_contains_ios_config():
    intent = parse_intent("Add OSPF on R1 network 10.1.1.0/30 area 0")
    playbook = export_playbook(intent, generate_config(intent))
    assert "cisco.ios.ios_config" in playbook
    assert "router ospf 1" in playbook


from pathlib import Path
from unittest.mock import patch

from src.config_inspector import inspect_existing_config
from src.intent_parser import parse_intent_with_rules
from src.netbox_client import MockNetBox
from src.validators import validate_intent
from src.verifier import verify_generated
from src.config_generator import generate_config
from src.pipeline import HELD_PLAYBOOK, execute_change
from app import process_change


NETBOX = MockNetBox(Path("data/netbox_mock.json"))
R1_CONFIG = Path("configs/R1.cfg").read_text(encoding="utf-8")


def test_inspector_reads_existing_ospf_network():
    facts = inspect_existing_config(R1_CONFIG)
    assert "1" in facts["ospf_processes"]
    networks = {item["network"] for item in facts["ospf_networks"]}
    assert "192.168.10.0" in networks


def test_duplicate_ospf_network_is_rejected_from_sample_inventory():
    intent = parse_intent_with_rules("Add OSPF on R1 network 192.168.10.0/24 area 0")
    result = validate_intent(intent, NETBOX, "hostname R1\ninterface GigabitEthernet0/0\n no shutdown\n")
    assert not result.ok
    assert any("already exists" in error for error in result.errors)


def test_new_ospf_network_on_existing_process_is_allowed():
    intent = parse_intent_with_rules("Add OSPF on R1 network 10.1.1.0/30 area 0")
    result = validate_intent(intent, NETBOX, R1_CONFIG)
    assert result.ok


def test_self_check_passes_for_ospf_delta():
    intent = parse_intent_with_rules("Connect R2 with OSPF on 10.1.1.0/30 area 0")
    generated = generate_config(intent)
    verify = verify_generated(intent, generated)
    assert verify.ok


@patch("src.pipeline.parse_intent", side_effect=parse_intent_with_rules)
def test_playbook_is_held_without_approval(_parsed):
    result = process_change("Add OSPF on R2 network 10.1.1.0/30 area 0", "", False)
    assert result[-1] == "Pending engineer approval"
    assert "held until an engineer approves" in result[6]
    assert "cisco.ios.ios_config" not in result[6]


@patch("src.pipeline.parse_intent", side_effect=parse_intent_with_rules)
def test_execute_change_includes_self_check(_parsed):
    result = execute_change("Add OSPF on R2 network 10.1.1.0/30 area 0", NETBOX, "", True)
    assert result.verify.ok
    assert "Self-check: PASS" in result.validation_report()
    assert HELD_PLAYBOOK not in result.playbook

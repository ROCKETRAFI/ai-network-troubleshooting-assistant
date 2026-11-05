from pathlib import Path
from unittest.mock import patch

from src.chat_assistant import chat_response
from src.intent_parser import parse_intent_with_rules
from src.netbox_client import MockNetBox


NETBOX = MockNetBox(Path("data/netbox_mock.json"))


def test_chat_greeting_has_local_response():
    with patch("src.chat_assistant._general_llm_response", return_value=None):
        response = chat_response("hi", [], NETBOX)
    assert "chat normally" in response


@patch("src.pipeline.parse_intent", side_effect=parse_intent_with_rules)
def test_chat_network_change_generates_config(_parsed):
    response = chat_response("Connect R1 and R2 with OSPF on 10.1.1.0/30 area 0", [], NETBOX)
    assert "Cisco IOS delta" in response
    assert "router ospf 1" in response
    assert "held until an engineer approves" in response


@patch("src.pipeline.parse_intent", side_effect=parse_intent_with_rules)
def test_chat_invalid_network_change_reports_validation(_parsed):
    response = chat_response("Configure RIP on R1", [], NETBOX)
    assert "validation failed" in response.lower()


def test_chat_uses_topology_context():
    topology = {
        "ok": True,
        "devices": ["R1", "R2", "SW1"],
        "in_inventory": ["R1", "R2", "SW1"],
        "unknown_devices": [],
        "protocols": ["ospf"],
        "summary": "Campus OSPF lab",
        "suggested_change": "Connect R1 and R2 with OSPF on 10.1.1.0/30 area 0",
        "links": [{"from": "R1", "to": "R2", "subnet": "10.1.1.0/30"}],
        "notes": [],
    }
    with patch("src.chat_assistant._general_llm_response", return_value=None):
        response = chat_response("which devices are on the diagram?", [], NETBOX, topology=topology)
    assert "R1" in response
    assert "10.1.1.0/30" in response


def test_chat_uses_studio_context():
    studio = {
        "intent": '{"protocol": "ospf"}',
        "validation": "Status: PASS",
        "config": "router ospf 1",
        "rollback": "no network 10.1.1.0",
        "risk": "Risk level: Medium",
        "approval_status": "Pending engineer approval",
        "playbook": "# held",
        "diff": "+ router ospf 1",
    }
    with patch("src.chat_assistant._general_llm_response", return_value=None):
        response = chat_response("what is the rollback from studio?", [], NETBOX, studio=studio)
    assert "no network 10.1.1.0" in response
    assert "Pending engineer approval" in response


@patch("src.pipeline.parse_intent", side_effect=parse_intent_with_rules)
def test_chat_generates_suggested_change_from_diagram(_parsed):
    topology = {
        "ok": True,
        "suggested_change": "Connect R1 and R2 with OSPF on 10.1.1.0/30 area 0",
        "devices": ["R1", "R2"],
    }
    response = chat_response("generate the suggested change from the diagram", [], NETBOX, topology=topology)
    assert "router ospf 1" in response


def test_chat_project_question_has_summary():
    with patch("src.chat_assistant._general_llm_response", return_value=None):
        response = chat_response("what is this project?", [], NETBOX)
    assert "network automation assistant" in response

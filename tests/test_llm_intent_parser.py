import os
from unittest.mock import patch

from src.intent_parser import parse_intent, parse_intent_with_rules
from src.llm_intent_parser import (
    _intent_from_dict,
    parse_intent_with_gemini,
    parse_intent_with_llm,
    parse_intent_with_openai,
)


def test_llm_parser_returns_none_without_api_key():
    with patch.dict(os.environ, {}, clear=True):
        assert parse_intent_with_llm("Add OSPF on R1 network 10.1.1.0/30 area 0") is None


def test_gemini_parser_returns_none_without_api_key():
    with patch.dict(os.environ, {}, clear=True):
        assert parse_intent_with_gemini("Add OSPF on R1 network 10.1.1.0/30 area 0") is None


def test_openai_parser_returns_none_without_api_key():
    with patch.dict(os.environ, {}, clear=True):
        assert parse_intent_with_openai("Add OSPF on R1 network 10.1.1.0/30 area 0") is None


def test_parse_intent_can_disable_llm():
    intent = parse_intent("Add OSPF on R1 network 10.1.1.0/30 area 0", use_llm=False)
    assert intent.protocol == "ospf"
    assert intent.devices == ["R1"]


def test_rule_parser_still_available_directly():
    intent = parse_intent_with_rules("Add OSPF on R2 network 10.1.1.0/30 area 0")
    assert intent.devices == ["R2"]


def test_intent_from_llm_dict_normalizes_values():
    intent = _intent_from_dict(
        {
            "change_type": "routing",
            "protocol": "OSPF",
            "mode": "ADD",
            "devices": ["r1"],
            "network": "10.1.1.0/30",
            "area": 0,
            "process_id": 1,
            "local_asn": None,
            "remote_asn": None,
            "neighbor_ip": None,
            "interface": None,
        },
        "raw",
    )
    assert intent.protocol == "ospf"
    assert intent.mode == "add"
    assert intent.devices == ["R1"]
    assert intent.area == "0"

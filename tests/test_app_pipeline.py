from unittest.mock import patch

from app import process_change, respond_chat
from src.intent_parser import parse_intent_with_rules


def test_process_change_empty_request_returns_eight_outputs():
    result = process_change("", "", False)
    assert len(result) == 8
    assert result[-1] == "Not approved"


@patch("src.pipeline.parse_intent", side_effect=parse_intent_with_rules)
def test_process_change_valid_request_returns_playbook(_parsed):
    result = process_change("Add OSPF on R2 network 10.1.1.0/30 area 0", "", True)
    assert len(result) == 8
    assert "cisco.ios.ios_config" in result[6]
    assert result[-1] == "Approved for export"


@patch("src.pipeline.parse_intent", side_effect=parse_intent_with_rules)
def test_process_change_invalid_request_rejected(_parsed):
    result = process_change("Configure RIP on R1", "", False)
    assert len(result) == 8
    assert result[-1] == "Rejected: validation failed"


@patch("src.chat_assistant._general_llm_response", return_value=None)
def test_respond_chat_returns_message(_llm):
    result = respond_chat("hi", [], "", False)
    assert isinstance(result, str)
    assert result

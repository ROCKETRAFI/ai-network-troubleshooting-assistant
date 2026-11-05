from src.diff_engine import build_diff


def test_diff_contains_added_lines():
    diff = build_diff("hostname R1", "! device: R1\nrouter ospf 1")
    assert "+++ candidate.cfg" in diff
    assert "+router ospf 1" in diff


def test_diff_keeps_existing_file_name():
    diff = build_diff("hostname R1", "router ospf 1")
    assert "--- existing.cfg" in diff


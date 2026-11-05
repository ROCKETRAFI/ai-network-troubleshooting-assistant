from __future__ import annotations

import re

from src.models import Intent
from src.llm_intent_parser import parse_intent_with_llm


DEVICE_RE = re.compile(r"\b([A-Z]{1,3}\d+)\b", re.IGNORECASE)
CIDR_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
ASN_RE = re.compile(r"\b(?:asn|as)\s*(\d{1,10})\b", re.IGNORECASE)


def parse_intent(text: str, use_llm: bool = True) -> Intent:
    if use_llm:
        llm_intent = parse_intent_with_llm(text)
        if llm_intent:
            return llm_intent

    return parse_intent_with_rules(text)


def parse_intent_with_rules(text: str) -> Intent:
    normalized = text.strip()
    lowered = normalized.lower()
    protocol = "bgp" if "bgp" in lowered else "ospf" if "ospf" in lowered else "unknown"
    mode = _detect_mode(lowered)
    devices = _unique(device.upper() for device in DEVICE_RE.findall(normalized))
    network_match = CIDR_RE.search(normalized)
    area_match = re.search(r"\barea\s+(\d+)\b", lowered)
    process_match = re.search(r"\b(?:process|pid|process id)\s+(\d+)\b", lowered)
    neighbor_match = re.search(r"\bneighbor\s+((?:\d{1,3}\.){3}\d{1,3})\b", lowered)
    interface_match = re.search(r"\b(?:interface|int)\s+([A-Za-z]+\S*)\b", normalized)

    local_asn, remote_asn = _extract_asns(lowered)

    return Intent(
        change_type="routing" if protocol in {"ospf", "bgp"} else "unknown",
        protocol=protocol,
        mode=mode,
        devices=devices,
        network=network_match.group(0) if network_match else None,
        area=area_match.group(1) if area_match else ("0" if protocol == "ospf" else None),
        process_id=process_match.group(1) if process_match else "1",
        local_asn=local_asn,
        remote_asn=remote_asn,
        neighbor_ip=neighbor_match.group(1) if neighbor_match else _infer_neighbor_ip(protocol, lowered),
        interface=interface_match.group(1) if interface_match else None,
        raw_text=normalized,
    )


def _detect_mode(lowered: str) -> str:
    if any(word in lowered for word in ["remove", "delete", "disable", "no "]):
        return "remove"
    if any(word in lowered for word in ["modify", "change", "update"]):
        return "modify"
    return "add"


def _extract_asns(lowered: str) -> tuple[str | None, str | None]:
    local = re.search(r"\blocal\s+(?:asn|as)\s*(\d{1,10})\b", lowered)
    remote = re.search(r"\bremote\s+(?:asn|as)\s*(\d{1,10})\b", lowered)
    if local or remote:
        return (
            local.group(1) if local else None,
            remote.group(1) if remote else None,
        )
    asns = ASN_RE.findall(lowered)
    if len(asns) >= 2:
        return asns[0], asns[1]
    if len(asns) == 1:
        return asns[0], None
    return None, None


def _infer_neighbor_ip(protocol: str, lowered: str) -> str | None:
    if protocol != "bgp":
        return None
    ips = IP_RE.findall(lowered)
    return ips[0] if ips else None


def _unique(items) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

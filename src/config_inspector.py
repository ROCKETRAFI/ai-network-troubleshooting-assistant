from __future__ import annotations

import ipaddress
import re
from pathlib import Path

try:
    from ciscoconfparse import CiscoConfParse
except ModuleNotFoundError:
    CiscoConfParse = None

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"


def sample_running_config(device: str) -> str:
    path = CONFIGS_DIR / f"{device}.cfg"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def running_config_for_intent(devices: list[str], extra_config: str = "") -> str:
    chunks: list[str] = []
    if extra_config.strip():
        chunks.append(extra_config)
    seen = set()
    for device in devices:
        sample = sample_running_config(device)
        if sample and sample not in seen:
            seen.add(sample)
            chunks.append(f"! sample running-config: {device}\n{sample}")
    return "\n".join(chunks)


def baseline_config_for_diff(devices: list[str], extra_config: str = "") -> str:
    if extra_config.strip() and "router ospf" in extra_config.lower():
        return extra_config
    if len(devices) == 1:
        sample = sample_running_config(devices[0])
        if sample:
            return sample
    return extra_config


def inspect_existing_config(existing_config: str) -> dict:
    text = existing_config or ""
    facts = {
        "ospf_processes": [],
        "ospf_networks": [],
        "bgp_asns": [],
        "bgp_neighbors": [],
        "shutdown_interfaces": [],
        "has_default_originate": "default-information originate" in text.lower(),
        "has_redistribute": bool(re.search(r"^\s*redistribute\s+", text, re.MULTILINE | re.IGNORECASE)),
    }
    if not text.strip():
        return facts

    if CiscoConfParse is None:
        _inspect_with_regex(text, facts)
        return facts

    try:
        parsed = CiscoConfParse(text.splitlines(), syntax="ios")
    except Exception:
        _inspect_with_regex(text, facts)
        return facts

    for process in parsed.find_objects(r"^router ospf\s+\d+"):
        match = re.search(r"router ospf\s+(\d+)", process.text, re.IGNORECASE)
        process_id = match.group(1) if match else "1"
        facts["ospf_processes"].append(process_id)
        for child in process.all_children:
            network = _parse_ospf_network_line(child.text)
            if network:
                facts["ospf_networks"].append({"process_id": process_id, **network})

    for bgp in parsed.find_objects(r"^router bgp\s+\d+"):
        match = re.search(r"router bgp\s+(\d+)", bgp.text, re.IGNORECASE)
        if match:
            facts["bgp_asns"].append(match.group(1))
        for child in bgp.all_children:
            neighbor = _parse_bgp_neighbor_line(child.text)
            if neighbor:
                facts["bgp_neighbors"].append(neighbor)

    for interface in parsed.find_objects(r"^interface\s+\S+"):
        name = interface.text.split(None, 1)[-1]
        has_shutdown = any(re.search(r"^\s*shutdown\b", child.text, re.IGNORECASE) for child in interface.all_children)
        has_no_shutdown = any(re.search(r"^\s*no\s+shutdown\b", child.text, re.IGNORECASE) for child in interface.all_children)
        if has_shutdown and not has_no_shutdown:
            facts["shutdown_interfaces"].append(name)

    return facts


def _inspect_with_regex(text: str, facts: dict) -> None:
    facts["ospf_processes"] = re.findall(r"^router ospf\s+(\d+)", text, re.MULTILINE | re.IGNORECASE)
    for line in text.splitlines():
        network = _parse_ospf_network_line(line)
        if network:
            facts["ospf_networks"].append({"process_id": facts["ospf_processes"][-1] if facts["ospf_processes"] else "1", **network})
        neighbor = _parse_bgp_neighbor_line(line)
        if neighbor:
            facts["bgp_neighbors"].append(neighbor)
    facts["bgp_asns"] = re.findall(r"^router bgp\s+(\d+)", text, re.MULTILINE | re.IGNORECASE)


def _parse_ospf_network_line(line: str) -> dict | None:
    match = re.search(
        r"network\s+((?:\d{1,3}\.){3}\d{1,3})\s+((?:\d{1,3}\.){3}\d{1,3})\s+area\s+(\S+)",
        line,
        re.IGNORECASE,
    )
    if not match:
        return None
    return {"network": match.group(1), "wildcard": match.group(2), "area": match.group(3)}


def _parse_bgp_neighbor_line(line: str) -> dict | None:
    match = re.search(
        r"neighbor\s+((?:\d{1,3}\.){3}\d{1,3})(?:\s+remote-as\s+(\d+))?",
        line,
        re.IGNORECASE,
    )
    if not match:
        return None
    return {"ip": match.group(1), "remote_asn": match.group(2)}


def wildcard_for_cidr(cidr: str) -> str:
    network = ipaddress.ip_network(cidr, strict=False)
    return ".".join(str(255 - int(octet)) for octet in str(network.netmask).split("."))

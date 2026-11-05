from __future__ import annotations

import ipaddress

from src.config_inspector import inspect_existing_config, running_config_for_intent, wildcard_for_cidr
from src.models import Intent, ValidationResult
from src.netbox_client import MockNetBox


DANGEROUS_TERMS = ["write erase", "reload", "format", "delete flash", "no router"]


def validate_intent(intent: Intent, netbox: MockNetBox, existing_config: str = "") -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if intent.protocol not in {"ospf", "bgp"}:
        errors.append("Only OSPF and BGP are supported in this MVP.")

    if not intent.devices:
        errors.append("No device was found in the request.")

    for device in intent.devices:
        if not netbox.device_exists(device):
            errors.append(f"Device does not exist in source of truth: {device}")
        elif netbox.is_core_device(device):
            warnings.append(f"{device} is marked as a core device.")

    if intent.interface:
        for device in intent.devices:
            if netbox.device_exists(device) and not netbox.interface_exists(device, intent.interface):
                errors.append(f"Interface {intent.interface} does not exist on {device}.")

    if intent.protocol == "ospf":
        _validate_ospf(intent, netbox, errors, warnings)

    if intent.protocol == "bgp":
        _validate_bgp(intent, errors, warnings)

    lowered_config = existing_config.lower()
    for term in DANGEROUS_TERMS:
        if term in lowered_config:
            warnings.append(f"Existing config contains risky command pattern: {term}")

    facts = inspect_existing_config(running_config_for_intent(intent.devices, existing_config))
    _validate_against_existing(intent, facts, errors, warnings)

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def _validate_ospf(intent: Intent, netbox: MockNetBox, errors: list[str], warnings: list[str]) -> None:
    if not intent.network:
        errors.append("OSPF change requires a network in CIDR format.")
        return

    try:
        network = ipaddress.ip_network(intent.network, strict=False)
    except ValueError:
        errors.append(f"Invalid OSPF network: {intent.network}")
        return

    if intent.area is None:
        errors.append("OSPF area is required.")

    if network.prefixlen < 24:
        warnings.append("OSPF network is broad; verify blast radius before approval.")

    for prefix in netbox.known_prefixes():
        known = ipaddress.ip_network(prefix, strict=False)
        if network.overlaps(known) and network != known:
            warnings.append(f"Requested network overlaps known prefix {prefix}.")


def _validate_bgp(intent: Intent, errors: list[str], warnings: list[str]) -> None:
    if not intent.neighbor_ip:
        errors.append("BGP change requires a neighbor IP.")
    else:
        try:
            ipaddress.ip_address(intent.neighbor_ip)
        except ValueError:
            errors.append(f"Invalid BGP neighbor IP: {intent.neighbor_ip}")

    if not intent.local_asn:
        errors.append("BGP change requires local ASN.")
    if not intent.remote_asn:
        errors.append("BGP change requires remote ASN.")

    for label, asn in [("local ASN", intent.local_asn), ("remote ASN", intent.remote_asn)]:
        if asn and not 1 <= int(asn) <= 4294967295:
            errors.append(f"Invalid {label}: {asn}")

    if len(intent.devices) > 1:
        warnings.append("BGP neighbor generation is per-device; verify peer direction manually.")


def _validate_against_existing(intent: Intent, facts: dict, errors: list[str], warnings: list[str]) -> None:
    if facts.get("has_default_originate"):
        warnings.append("Existing config advertises a default route.")
    if facts.get("has_redistribute"):
        warnings.append("Existing config contains redistribution; confirm route leakage.")

    if intent.interface:
        for name in facts.get("shutdown_interfaces", []):
            if name.lower() == intent.interface.lower():
                warnings.append(f"Interface {intent.interface} is shutdown in the existing config.")

    if intent.protocol == "ospf" and intent.network:
        try:
            network = ipaddress.ip_network(intent.network, strict=False)
            wildcard = wildcard_for_cidr(intent.network)
            address = str(network.network_address)
        except ValueError:
            return
        already = [
            item
            for item in facts.get("ospf_networks", [])
            if item["network"] == address and item["wildcard"] == wildcard
        ]
        if intent.mode == "add" and already:
            errors.append(f"OSPF network {intent.network} already exists in the current config.")
        if intent.mode == "remove" and not already and facts.get("ospf_networks"):
            warnings.append(f"OSPF network {intent.network} was not found in the current config.")
        if intent.mode == "modify" and not already:
            warnings.append("Modify mode did not find an existing OSPF network; this will be treated like an add.")
        if facts.get("ospf_processes") and intent.process_id not in facts["ospf_processes"]:
            warnings.append(
                f"Existing OSPF process {', '.join(facts['ospf_processes'])} differs from requested process {intent.process_id}."
            )

    if intent.protocol == "bgp" and intent.neighbor_ip:
        neighbors = {item["ip"] for item in facts.get("bgp_neighbors", [])}
        if intent.mode == "add" and intent.neighbor_ip in neighbors:
            errors.append(f"BGP neighbor {intent.neighbor_ip} already exists in the current config.")
        if intent.mode == "remove" and intent.neighbor_ip not in neighbors and neighbors:
            warnings.append(f"BGP neighbor {intent.neighbor_ip} was not found in the current config.")
        if facts.get("bgp_asns") and intent.local_asn and intent.local_asn not in facts["bgp_asns"]:
            warnings.append(
                f"Existing BGP ASN {', '.join(facts['bgp_asns'])} differs from requested local ASN {intent.local_asn}."
            )


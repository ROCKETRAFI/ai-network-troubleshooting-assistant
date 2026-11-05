from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field

from src.models import DeviceConfig, Intent


@dataclass
class VerifyResult:
    ok: bool
    notes: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [f"Self-check: {'PASS' if self.ok else 'FAIL'}"]
        lines.extend(f"- {note}" for note in self.notes)
        return "\n".join(lines)


def verify_generated(intent: Intent, generated: DeviceConfig) -> VerifyResult:
    issues: list[str] = []
    text = generated.to_text()
    lowered = text.lower()

    if not generated.configs:
        return VerifyResult(False, ["Generated config is empty."])

    if intent.protocol == "ospf":
        if "router ospf" not in lowered:
            issues.append("Generated config is missing an OSPF process.")
        if intent.network:
            network = ipaddress.ip_network(intent.network, strict=False)
            if str(network.network_address) not in text:
                issues.append(f"Generated config does not include network {intent.network}.")
        if intent.area is not None and f"area {intent.area}" not in lowered:
            issues.append(f"Generated config does not include area {intent.area}.")
        if intent.mode == "remove" and "no network" not in lowered:
            issues.append("Remove mode should emit a 'no network' OSPF statement.")

    if intent.protocol == "bgp":
        if "router bgp" not in lowered:
            issues.append("Generated config is missing a BGP process.")
        if intent.neighbor_ip and intent.neighbor_ip not in text:
            issues.append(f"Generated config does not include neighbor {intent.neighbor_ip}.")
        if intent.mode != "remove" and intent.remote_asn and intent.remote_asn not in text:
            issues.append(f"Generated config does not include remote ASN {intent.remote_asn}.")

    for device in intent.devices:
        if device not in generated.configs:
            issues.append(f"No config section was generated for {device}.")

    if issues:
        return VerifyResult(False, issues)
    return VerifyResult(True, ["Generated IOS delta matches the parsed intent."])

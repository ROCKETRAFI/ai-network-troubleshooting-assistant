from __future__ import annotations

from dataclasses import dataclass, field
import json


@dataclass
class Intent:
    change_type: str
    protocol: str
    mode: str = "add"
    devices: list[str] = field(default_factory=list)
    network: str | None = None
    area: str | None = None
    process_id: str = "1"
    local_asn: str | None = None
    remote_asn: str | None = None
    neighbor_ip: str | None = None
    interface: str | None = None
    raw_text: str = ""

    def to_dict(self) -> dict:
        return {
            "change_type": self.change_type,
            "protocol": self.protocol,
            "mode": self.mode,
            "devices": self.devices,
            "network": self.network,
            "area": self.area,
            "process_id": self.process_id,
            "local_asn": self.local_asn,
            "remote_asn": self.remote_asn,
            "neighbor_ip": self.neighbor_ip,
            "interface": self.interface,
            "raw_text": self.raw_text,
        }

    def to_pretty_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [f"Status: {'PASS' if self.ok else 'FAIL'}"]
        if self.errors:
            lines.append("Errors:")
            lines.extend(f"- {error}" for error in self.errors)
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"- {warning}" for warning in self.warnings)
        if len(lines) == 1:
            lines.append("No validation issues found.")
        return "\n".join(lines)


@dataclass
class DeviceConfig:
    configs: dict[str, list[str]]

    def to_text(self) -> str:
        sections: list[str] = []
        for device, lines in self.configs.items():
            sections.append(f"! device: {device}")
            sections.extend(lines)
        return "\n".join(sections)


from __future__ import annotations

from dataclasses import dataclass

from src.models import Intent, ValidationResult


@dataclass
class RiskResult:
    level: str
    score: int
    blast_radius: str
    reasons: list[str]

    def to_text(self) -> str:
        lines = [
            f"Risk level: {self.level}",
            f"Risk score: {self.score}/100",
            f"Blast radius: {self.blast_radius}",
            "Reasons:",
        ]
        lines.extend(f"- {reason}" for reason in self.reasons)
        return "\n".join(lines)


def score_risk(intent: Intent, validation: ValidationResult, existing_config: str = "") -> RiskResult:
    score = 10
    reasons = ["Network configuration change requires engineer review."]

    if intent.protocol == "bgp":
        score += 30
        reasons.append("BGP changes can affect inter-domain or edge routing.")
    elif intent.protocol == "ospf":
        score += 15
        reasons.append("OSPF changes can affect internal route propagation.")

    if len(intent.devices) > 1:
        score += 10
        reasons.append(f"{len(intent.devices)} devices are affected.")

    if intent.mode in {"modify", "remove"}:
        score += 15
        reasons.append(f"{intent.mode.title()} mode can interrupt existing behavior.")

    if validation.warnings:
        score += min(20, len(validation.warnings) * 5)
        reasons.extend(validation.warnings)

    if "default-information originate" in existing_config.lower():
        score += 10
        reasons.append("Existing config contains default route advertisement.")

    score = min(score, 100)
    if score >= 75:
        level = "Critical"
    elif score >= 50:
        level = "High"
    elif score >= 30:
        level = "Medium"
    else:
        level = "Low"

    blast_radius = "High" if score >= 50 else "Medium" if score >= 30 else "Low"
    return RiskResult(level=level, score=score, blast_radius=blast_radius, reasons=reasons)


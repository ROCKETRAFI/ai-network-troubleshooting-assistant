from __future__ import annotations

from dataclasses import dataclass

from src.ansible_exporter import export_playbook
from src.config_inspector import baseline_config_for_diff
from src.config_generator import generate_config
from src.diff_engine import build_diff
from src.intent_parser import parse_intent
from src.models import Intent, ValidationResult
from src.netbox_client import MockNetBox
from src.risk_scorer import RiskResult, score_risk
from src.rollback import generate_rollback
from src.validators import validate_intent
from src.verifier import VerifyResult, verify_generated


HELD_PLAYBOOK = (
    "# Ansible export is held until an engineer approves this change.\n"
    "# Review the IOS delta, diff, rollback, and risk first, then tick approval.\n"
)


@dataclass
class ChangeResult:
    intent: Intent
    validation: ValidationResult
    generated_text: str
    diff: str
    rollback: str
    risk: RiskResult
    verify: VerifyResult
    playbook: str
    approval_status: str

    def validation_report(self) -> str:
        parts = [self.validation.to_text(), "", self.verify.to_text()]
        return "\n".join(parts).strip()

    def risk_report(self) -> str:
        return self.risk.to_text()


def execute_change(
    request_text: str,
    netbox: MockNetBox,
    existing_config: str = "",
    approval: bool = False,
) -> ChangeResult:
    intent = parse_intent(request_text)
    validation = validate_intent(intent, netbox, existing_config)
    empty_verify = VerifyResult(True, ["Self-check skipped because validation failed."])
    baseline = baseline_config_for_diff(intent.devices, existing_config)

    if not validation.ok:
        return ChangeResult(
            intent=intent,
            validation=validation,
            generated_text="",
            diff="",
            rollback="",
            risk=score_risk(intent, validation, existing_config),
            verify=empty_verify,
            playbook="",
            approval_status="Rejected: validation failed",
        )

    generated = generate_config(intent)
    verify = verify_generated(intent, generated)
    if not verify.ok:
        validation.ok = False
        validation.errors.append("Self-check failed: generated config does not match intent.")
        return ChangeResult(
            intent=intent,
            validation=validation,
            generated_text=generated.to_text(),
            diff=build_diff(baseline, generated.to_text()),
            rollback=generate_rollback(intent).to_text(),
            risk=score_risk(intent, validation, existing_config),
            verify=verify,
            playbook="",
            approval_status="Rejected: self-check failed",
        )

    playbook = export_playbook(intent, generated) if approval else HELD_PLAYBOOK
    status = "Approved for export" if approval else "Pending engineer approval"
    return ChangeResult(
        intent=intent,
        validation=validation,
        generated_text=generated.to_text(),
        diff=build_diff(baseline, generated.to_text()),
        rollback=generate_rollback(intent).to_text(),
        risk=score_risk(intent, validation, existing_config),
        verify=verify,
        playbook=playbook,
        approval_status=status,
    )

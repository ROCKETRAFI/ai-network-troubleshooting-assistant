from __future__ import annotations

import os
import re

from src.gemini_client import generate_text
from src.netbox_client import MockNetBox
from src.pipeline import execute_change


NETWORK_KEYWORDS = {
    "ospf",
    "bgp",
    "router",
    "routing",
    "neighbor",
    "network",
    "subnet",
    "asn",
    "area",
    "cisco",
    "config",
    "interface",
    "rollback",
    "ansible",
}


def chat_response(
    message: str,
    history: list[dict[str, str]] | list[tuple[str, str]] | None,
    netbox: MockNetBox,
    existing_config: str = "",
    approval: bool = False,
    topology: dict | None = None,
    studio: dict | None = None,
) -> str:
    text = message.strip()
    if not text:
        return "Type a network request or ask me something about the project."

    if _wants_diagram_change(text, topology):
        suggested = str((topology or {}).get("suggested_change") or "").strip()
        return _network_change_response(suggested, netbox, existing_config, approval)

    if _looks_like_network_change(text):
        return _network_change_response(text, netbox, existing_config, approval)

    packed = _workspace_context(topology, studio)
    llm_answer = _general_llm_response(text, history or [], packed)
    if llm_answer:
        return llm_answer

    return _local_general_response(text, topology, studio)


def format_topology_context(topology: dict | None) -> str:
    if not topology or not topology.get("ok"):
        return ""
    devices = ", ".join(topology.get("devices") or []) or "(none)"
    in_lab = ", ".join(topology.get("in_inventory") or []) or "(none)"
    unknown = ", ".join(topology.get("unknown_devices") or []) or "(none)"
    protocols = ", ".join(topology.get("protocols") or []) or "(none)"
    suggested = str(topology.get("suggested_change") or "").strip() or "(none — out of OSPF/BGP scope)"
    links = topology.get("links") or []
    link_lines = []
    for item in links[:12]:
        if isinstance(item, dict):
            src = item.get("from") or item.get("src") or "?"
            dst = item.get("to") or item.get("dst") or "?"
            subnet = item.get("subnet") or ""
            extra = f" {subnet}" if subnet else ""
            link_lines.append(f"- {src} -- {dst}{extra}")
        else:
            link_lines.append(f"- {item}")
    notes = topology.get("notes") or []
    note_text = "\n".join(f"- {note}" for note in notes) if notes else "- (none)"
    return (
        "Last Topology tab analysis:\n"
        f"Summary: {topology.get('summary') or '(none)'}\n"
        f"Devices: {devices}\n"
        f"In mock NetBox: {in_lab}\n"
        f"Unknown devices: {unknown}\n"
        f"Protocols: {protocols}\n"
        f"Suggested OSPF/BGP change: {suggested}\n"
        "Links:\n"
        + ("\n".join(link_lines) if link_lines else "- (none)")
        + "\nNotes:\n"
        + note_text
    )


def format_studio_context(studio: dict | None) -> str:
    if not studio:
        return ""
    intent = str(studio.get("intent") or "").strip()
    validation = str(studio.get("validation") or "").strip()
    config = str(studio.get("config") or "").strip()
    if intent in {"", "{}"} and validation in {"", "—"} and config in {"", "—"}:
        return ""
    approval = str(studio.get("approval_status") or studio.get("approval") or "").strip() or "(unknown)"
    return (
        "Last Change Studio review pack:\n"
        f"Approval: {approval}\n"
        f"Intent:\n{_clip(intent, 1200)}\n"
        f"Validation:\n{_clip(validation, 800)}\n"
        f"Cisco IOS delta:\n{_clip(config, 800)}\n"
        f"Rollback:\n{_clip(str(studio.get('rollback') or ''), 800)}\n"
        f"Risk:\n{_clip(str(studio.get('risk') or ''), 800)}\n"
        f"Diff:\n{_clip(str(studio.get('diff') or ''), 800)}\n"
        f"Ansible:\n{_clip(str(studio.get('playbook') or ''), 800)}"
    )


def _workspace_context(topology: dict | None, studio: dict | None) -> str:
    parts = [format_topology_context(topology), format_studio_context(studio)]
    return "\n\n".join(part for part in parts if part)


def _clip(text: str, limit: int) -> str:
    cleaned = text.strip() or "(none)"
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit] + "\n… (truncated)"


def _wants_diagram_change(text: str, topology: dict | None) -> bool:
    if not topology or not str(topology.get("suggested_change") or "").strip():
        return False
    lowered = text.lower()
    hints = (
        "diagram",
        "topology",
        "suggested",
        "this change",
        "from the image",
        "from the upload",
        "from the picture",
        "generate from",
        "apply this",
    )
    return any(hint in lowered for hint in hints)


def _looks_like_network_change(text: str) -> bool:
    lowered = text.lower()
    has_action = any(
        word in lowered
        for word in ["add", "connect", "configure", "remove", "delete", "modify", "update"]
    )
    has_network_word = any(keyword in lowered for keyword in NETWORK_KEYWORDS)
    return has_action and has_network_word


def _network_change_response(
    text: str,
    netbox: MockNetBox,
    existing_config: str,
    approval: bool,
) -> str:
    result = execute_change(text, netbox, existing_config, approval)
    if not result.validation.ok:
        return (
            "I understood this as a network change, but validation failed.\n\n"
            f"```json\n{result.intent.to_pretty_json()}\n```\n\n"
            f"```text\n{result.validation_report()}\n```"
        )

    return (
        "I generated a validated network change.\n\n"
        f"Approval: **{result.approval_status}**\n\n"
        f"Intent:\n```json\n{result.intent.to_pretty_json()}\n```\n\n"
        f"Validation:\n```text\n{result.validation_report()}\n```\n\n"
        f"Cisco IOS delta:\n```text\n{result.generated_text}\n```\n\n"
        f"Rollback:\n```text\n{result.rollback}\n```\n\n"
        f"Risk:\n```text\n{result.risk_report()}\n```\n\n"
        f"Diff:\n```diff\n{result.diff}\n```\n\n"
        f"Ansible playbook:\n```yaml\n{result.playbook}\n```"
    )


def _general_llm_response(
    message: str,
    history: list[dict[str, str]] | list[tuple[str, str]],
    workspace: str = "",
) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    context = _format_history(history)
    extra = f"\n\nWorkspace from other tabs (use this when the user asks about it):\n{workspace}\n" if workspace else ""
    prompt = (
        "You are a helpful assistant inside a student network automation project. "
        "Answer casually and clearly. If the user asks about the topology diagram or "
        "the Change Studio review pack, use the workspace context. "
        "If they ask for a new network config generation, they must provide devices, "
        "protocol, subnet, area/ASN, and intent. Do not invent Cisco IOS beyond the workspace.\n"
        f"{extra}\n"
        f"Conversation so far:\n{context}\n\nUser: {message}"
    )
    text, error = generate_text(prompt)
    if text:
        return text
    if error:
        return (
            "I can answer basic project questions offline. "
            f"{error}. Network change generation still works without Gemini."
        )
    return None


def _format_history(history: list[dict[str, str]] | list[tuple[str, str]]) -> str:
    lines: list[str] = []
    for item in history[-6:]:
        if isinstance(item, dict):
            role = item.get("role", "user")
            content = item.get("content", "")
            lines.append(f"{role}: {content}")
        elif isinstance(item, tuple) and len(item) == 2:
            user_message, assistant_message = item
            lines.append(f"user: {user_message}")
            lines.append(f"assistant: {assistant_message}")
    return "\n".join(lines)


def _asks_about_workspace(message: str) -> bool:
    lowered = message.lower()
    return any(
        word in lowered
        for word in (
            "diagram",
            "topology",
            "studio",
            "device",
            "link",
            "rollback",
            "risk",
            "blast",
            "ansible",
            "playbook",
            "intent",
            "diff",
            "ios",
            "upload",
            "image",
            "change pack",
            "validation",
            "approval",
        )
    )


def _local_general_response(
    message: str,
    topology: dict | None = None,
    studio: dict | None = None,
) -> str:
    lowered = message.lower()
    packed = _workspace_context(topology, studio)
    if packed and _asks_about_workspace(message):
        return (
            "I am using the last Topology analysis and/or Change Studio result.\n\n"
            f"```text\n{packed}\n```"
        )
    if "what" in lowered and "project" in lowered:
        return (
            "This project is an AI-powered network automation assistant. "
            "It converts English requests into validated Cisco IOS config deltas, rollback, "
            "risk score, and Ansible playbooks."
        )
    tokens = set(re.findall(r"\b[a-z]+\b", lowered))
    if tokens.intersection({"hi", "hello", "hey", "vanakkam"}):
        extra = " I can also discuss the last topology diagram or Change Studio review pack." if packed else ""
        return (
            "Hi! I can chat normally, and I can also generate OSPF/BGP Cisco IOS changes."
            + extra
        )
    if "example" in lowered:
        return "Try: `Connect R1 and R2 with OSPF on 10.1.1.0/30 area 0`"
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return (
            "I can answer basic project questions offline. "
            "Gemini did not return a reply. Network change generation still works without Gemini."
        )
    return (
        "I can answer basic project questions offline. For richer normal chat, set "
        "`GEMINI_API_KEY` in `.env`, then restart the app."
    )

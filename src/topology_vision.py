from __future__ import annotations

import json
from typing import Any

from src.gemini_client import generate_vision
from src.netbox_client import MockNetBox

VISION_PROMPT = """You read a network topology diagram (GNS3, Packet Tracer, PowerPoint, or a sketch).
Return ONLY valid JSON with this shape:
{
  "devices": ["R1", "R2"],
  "links": [{"from": "R1", "to": "R2", "subnet": "10.1.1.0/30", "note": ""}],
  "protocols": ["ospf"],
  "summary": "one sentence",
  "suggested_change": "Connect R1 and R2 with OSPF on 10.1.1.0/30 area 0"
}
Rules:
- Device names uppercase like R1, R2, SW1.
- Use null or empty string when a subnet is not readable.
- suggested_change must be a single English OSPF or BGP change request if possible.
- If the diagram is a firewall/ACL/DMZ design, set suggested_change to empty string and explain in summary that this copilot only generates OSPF/BGP deltas.
- Do not invent Cisco IOS configuration.
"""


def describe_topology(image_bytes: bytes, mime_type: str, netbox: MockNetBox) -> dict[str, Any]:
    if not image_bytes:
        return {"ok": False, "error": "No image was uploaded."}

    raw, error = generate_vision(VISION_PROMPT, image_bytes, mime_type or "image/jpeg")
    if not raw:
        return {
            "ok": False,
            "error": error or "Could not read the topology image.",
            "devices": [],
            "links": [],
            "in_inventory": [],
            "unknown_devices": [],
            "suggested_change": "",
            "summary": "",
        }

    try:
        data = _load_json(raw)
    except Exception:
        return {
            "ok": False,
            "error": "Vision model did not return valid JSON.",
            "raw": raw[:800],
            "devices": [],
            "links": [],
            "in_inventory": [],
            "unknown_devices": [],
            "suggested_change": "",
            "summary": "",
        }

    devices = [str(name).upper() for name in (data.get("devices") or []) if str(name).strip()]
    in_inventory = [name for name in devices if netbox.device_exists(name)]
    unknown = [name for name in devices if not netbox.device_exists(name)]
    suggested = str(data.get("suggested_change") or "").strip()
    summary = str(data.get("summary") or "").strip()
    links = data.get("links") if isinstance(data.get("links"), list) else []

    notes = []
    if unknown:
        notes.append(f"Not in mock NetBox: {', '.join(unknown)}")
    if in_inventory:
        notes.append(f"Known lab devices: {', '.join(in_inventory)}")
    if not suggested:
        notes.append("No OSPF/BGP change was inferred. Use Change Studio with an English request.")

    return {
        "ok": True,
        "devices": devices,
        "links": links,
        "protocols": data.get("protocols") or [],
        "summary": summary,
        "suggested_change": suggested,
        "in_inventory": in_inventory,
        "unknown_devices": unknown,
        "notes": notes,
        "error": None,
    }


def _load_json(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()
    loaded = json.loads(cleaned)
    if not isinstance(loaded, dict):
        raise ValueError("Vision response must be a JSON object.")
    return loaded

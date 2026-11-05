from __future__ import annotations

import json
import os
from typing import Any

from src.gemini_client import generate_text
from src.models import Intent

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()


SYSTEM_PROMPT = """You extract structured network automation intent.
Return only valid JSON with these keys:
change_type, protocol, mode, devices, network, area, process_id,
local_asn, remote_asn, neighbor_ip, interface.

Allowed protocols: ospf, bgp, unknown.
Allowed modes: add, modify, remove.
Use null when a value is missing.
Devices must be uppercase, for example R1, R2, SW1.
Do not generate configuration.
"""


def parse_intent_with_llm(text: str) -> Intent | None:
    provider = os.getenv("AI_PROVIDER", "auto").lower()
    if provider in {"auto", "gemini", "google"}:
        gemini_intent = parse_intent_with_gemini(text)
        if gemini_intent:
            return gemini_intent

    if provider in {"auto", "openai"}:
        openai_intent = parse_intent_with_openai(text)
        if openai_intent:
            return openai_intent

    return None


def parse_intent_with_gemini(text: str) -> Intent | None:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    prompt = f"{SYSTEM_PROMPT}\n\nUser request:\n{text}"
    raw, _error = generate_text(prompt)
    if not raw:
        return None
    try:
        data = _load_json(raw)
        return _intent_from_dict(data, text)
    except Exception:
        return None


def parse_intent_with_openai(text: str) -> Intent | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ModuleNotFoundError:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0,
        )
        data = _load_json(response.output_text)
        return _intent_from_dict(data, text)
    except Exception:
        return None


def _load_json(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()
    loaded = json.loads(cleaned)
    if not isinstance(loaded, dict):
        raise ValueError("LLM response must be a JSON object.")
    return loaded


def _intent_from_dict(data: dict[str, Any], raw_text: str) -> Intent:
    devices = data.get("devices") or []
    if not isinstance(devices, list):
        devices = []

    return Intent(
        change_type=_string_or_default(data.get("change_type"), "unknown"),
        protocol=_string_or_default(data.get("protocol"), "unknown").lower(),
        mode=_string_or_default(data.get("mode"), "add").lower(),
        devices=[str(device).upper() for device in devices],
        network=_optional_string(data.get("network")),
        area=_optional_string(data.get("area")),
        process_id=_string_or_default(data.get("process_id"), "1"),
        local_asn=_optional_string(data.get("local_asn")),
        remote_asn=_optional_string(data.get("remote_asn")),
        neighbor_ip=_optional_string(data.get("neighbor_ip")),
        interface=_optional_string(data.get("interface")),
        raw_text=raw_text.strip(),
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_or_default(value: Any, default: str) -> str:
    text = _optional_string(value)
    return text if text is not None else default

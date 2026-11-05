from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(override=True)

FALLBACK_MODELS = (
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
    "gemma-4-31b-it",
)


def generate_text(prompt: str) -> tuple[str | None, str | None]:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None, None

    try:
        from google import genai
    except ModuleNotFoundError:
        return None, "google-genai is not installed"

    last_error = "Gemini request failed"
    for model in _models_to_try():
        try:
            client = genai.Client(api_key=api_key, vertexai=False)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            text = (getattr(response, "text", None) or "").strip()
            if text:
                return text, None
        except Exception as exc:
            last_error = _friendly_error(exc)
            if _is_quota_or_not_found(exc):
                continue
            return None, last_error
    return None, last_error


def generate_vision(prompt: str, image_bytes: bytes, mime_type: str) -> tuple[str | None, str | None]:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None, "Set GEMINI_API_KEY to read topology images"

    try:
        from google import genai
        from google.genai import types
    except ModuleNotFoundError:
        return None, "google-genai is not installed"

    last_error = "Gemini vision request failed"
    for model in _models_to_try():
        try:
            client = genai.Client(api_key=api_key, vertexai=False)
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
            )
            text = (getattr(response, "text", None) or "").strip()
            if text:
                return text, None
        except Exception as exc:
            last_error = _friendly_error(exc)
            if _is_quota_or_not_found(exc):
                continue
            return None, last_error
    return None, last_error


def _models_to_try() -> list[str]:
    preferred = (os.getenv("GEMINI_MODEL") or "").strip()
    models: list[str] = []
    for model in (preferred, *FALLBACK_MODELS):
        if model and model not in models:
            models.append(model)
    return models


def _is_quota_or_not_found(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(token in text for token in ("429", "quota", "resource_exhausted", "404", "not found", "no longer available"))


def _friendly_error(exc: Exception) -> str:
    text = str(exc)
    lowered = text.lower()
    if "429" in text or "quota" in lowered or "resource_exhausted" in lowered:
        return "Gemini free-tier quota is exhausted for the current model"
    if "401" in text or "unauthenticated" in lowered or "api key" in lowered:
        return "Gemini rejected the API key"
    if "404" in text or "no longer available" in lowered:
        return "The configured Gemini model is not available for this key"
    return "Gemini request failed"

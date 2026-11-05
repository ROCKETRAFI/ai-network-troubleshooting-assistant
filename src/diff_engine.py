from __future__ import annotations

import difflib


def build_diff(existing_config: str, generated_config: str) -> str:
    existing_lines = existing_config.splitlines()
    generated_lines = generated_config.splitlines()
    return "\n".join(
        difflib.unified_diff(
            existing_lines,
            existing_lines + generated_lines,
            fromfile="existing.cfg",
            tofile="candidate.cfg",
            lineterm="",
        )
    )


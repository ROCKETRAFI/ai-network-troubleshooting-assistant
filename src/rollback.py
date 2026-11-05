from __future__ import annotations

from copy import deepcopy

from src.config_generator import generate_config
from src.models import DeviceConfig, Intent


def generate_rollback(intent: Intent) -> DeviceConfig:
    rollback_intent = deepcopy(intent)
    rollback_intent.mode = "remove" if intent.mode in {"add", "modify"} else "add"
    return generate_config(rollback_intent)


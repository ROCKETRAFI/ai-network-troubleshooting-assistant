from __future__ import annotations

import json
from pathlib import Path


class MockNetBox:
    def __init__(self, data_path: Path):
        self.data = json.loads(data_path.read_text(encoding="utf-8"))

    def device_exists(self, name: str) -> bool:
        return name in self.data["devices"]

    def interface_exists(self, device: str, interface: str) -> bool:
        if not self.device_exists(device):
            return False
        return interface in self.data["devices"][device].get("interfaces", [])

    def is_core_device(self, device: str) -> bool:
        if not self.device_exists(device):
            return False
        return self.data["devices"][device].get("role") == "core"

    def known_prefixes(self) -> list[str]:
        return self.data.get("prefixes", [])


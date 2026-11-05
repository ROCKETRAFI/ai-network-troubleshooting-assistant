from __future__ import annotations

import yaml

from src.models import DeviceConfig, Intent


def export_playbook(intent: Intent, generated: DeviceConfig) -> str:
    plays = []
    for device, lines in generated.configs.items():
        if not lines:
            continue
        parent = lines[0]
        child_lines = [line.strip() for line in lines[1:]]
        plays.append(
            {
                "name": f"Apply {intent.protocol.upper()} change on {device}",
                "hosts": device,
                "gather_facts": False,
                "tasks": [
                    {
                        "name": "Apply Cisco IOS config delta",
                        "cisco.ios.ios_config": {
                            "parents": [parent],
                            "lines": child_lines,
                        },
                    }
                ],
            }
        )
    return yaml.safe_dump(plays, sort_keys=False)


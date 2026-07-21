#!/usr/bin/env python3
"""Compare the original and current Route 218 event layouts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVENT_PATH = Path("res/field/events/events_route_218.json")
BASE_COMMIT = "5bb653e49"


def load_original() -> dict:
    raw = subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{BASE_COMMIT}:{EVENT_PATH}"],
        text=True,
    )
    return json.loads(raw)


def print_layout(label: str, data: dict) -> None:
    print(f"=== {label} objects ===")
    for obj in data.get("object_events", []):
        print(
            f"id={obj.get('id')} gfx={obj.get('graphics_id')} "
            f"x={obj.get('x')} y={obj.get('y')} z={obj.get('z')} "
            f"script={obj.get('script')} flag={obj.get('flag', 0)}"
        )

    events = data.get("coord_events", data.get("coordinate_events", []))
    print(f"=== {label} coordinate events ===")
    for event in events:
        print(json.dumps(event, sort_keys=True))

    print(f"=== {label} warps ===")
    for warp in data.get("warp_events", []):
        print(json.dumps(warp, sort_keys=True))


def main() -> None:
    current = json.loads((ROOT / EVENT_PATH).read_text())
    print_layout("ORIGINAL", load_original())
    print_layout("CURRENT", current)


if __name__ == "__main__":
    main()

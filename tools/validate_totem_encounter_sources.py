#!/usr/bin/env python3
"""Validate the production source wiring for all eight Totem encounters."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from integrate_totem_encounters import (
    ENCOUNTERS,
    EVENTS_DIR,
    FLAGS_PATH,
    MAP_HEADERS_PATH,
    SCRIPTS_DIR,
    script_entries,
)


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def validate_encounter(encounter) -> dict[str, object]:
    failures: list[str] = []
    script_path = SCRIPTS_DIR / encounter.scripts_file
    event_path = EVENTS_DIR / encounter.events_file
    script_text = script_path.read_text()
    entries = script_entries(script_text)

    require(entries.count(encounter.label) == 1, "script entry is missing or duplicated", failures)
    script_id = entries.index(encounter.label) + 1 if encounter.label in entries else -1

    start = script_text.find(f"{encounter.label}:")
    end = script_text.find("    End", start)
    routine = script_text[start : end + len("    End")] if start >= 0 and end >= 0 else ""
    expected_lines = (
        "    LockAll",
        "    FacePlayer",
        f"    PlayCry SPECIES_{encounter.species}",
        "    SetFlag FLAG_MAP_LOCAL",
        f"    StartLegendaryBattle SPECIES_{encounter.species}, {encounter.level}",
        "    ClearFlag FLAG_MAP_LOCAL",
        "    CheckWonBattle VAR_RESULT",
        f"    GoToIfEq VAR_RESULT, FALSE, {encounter.label}_LostBattle",
        f"    SetFlag {encounter.defeated_flag}",
        f"    SetFlag {encounter.hide_flag}",
        "    RemoveObject VAR_LAST_TALKED",
    )
    for line in expected_lines:
        require(line in routine, f"canonical routine line missing: {line.strip()}", failures)

    loss_label = f"{encounter.label}_LostBattle:"
    loss_start = script_text.find(loss_label)
    loss_end = script_text.find("    End", loss_start)
    loss_routine = script_text[loss_start : loss_end + len("    End")] if loss_start >= 0 and loss_end >= 0 else ""
    require("    BlackOutFromBattle" in loss_routine, "loss branch lacks BlackOutFromBattle", failures)
    require(encounter.defeated_flag not in loss_routine, "loss branch sets defeated flag", failures)
    require(encounter.hide_flag not in loss_routine, "loss branch sets hide flag", failures)

    event_data = json.loads(event_path.read_text())
    matches = [obj for obj in event_data["object_events"] if obj.get("graphics_id") == encounter.graphics]
    require(len(matches) == 1, f"expected one event object, found {len(matches)}", failures)
    obj = matches[0] if len(matches) == 1 else {}
    expected_fields = {
        "script": script_id,
        "hidden_flag": encounter.hide_flag,
        "movement_type": "MOVEMENT_TYPE_NONE",
        "trainer_type": "TRAINER_TYPE_NONE",
        "x": encounter.x,
        "y": encounter.y,
        "z": encounter.z,
    }
    for field, expected in expected_fields.items():
        require(obj.get(field) == expected, f"event {field}={obj.get(field)!r}, expected {expected!r}", failures)

    if encounter.story_flag is not None:
        prefix = encounter.label.removesuffix("_Encounter")
        require(
            f"GoToIfUnset {encounter.story_flag}, {prefix}_Hide" in script_text,
            "story-gate visibility test missing",
            failures,
        )
        require(
            f"GoToIfSet {encounter.defeated_flag}, {prefix}_Hide" in script_text,
            "defeated visibility test missing",
            failures,
        )

    if encounter.new_script_bank:
        bank = Path(encounter.scripts_file).stem
        order = (SCRIPTS_DIR / "scripts.order").read_text().splitlines()
        meson = (SCRIPTS_DIR / "meson.build").read_text()
        headers = MAP_HEADERS_PATH.read_text()
        require(bank in order, "new script bank missing from scripts.order", failures)
        require(f"'{bank}.s'," in meson, "new script bank missing from meson.build", failures)
        header_start = headers.find(f"[{encounter.map_header}] = {{")
        header_end = headers.find("    },", header_start)
        header_record = headers[header_start:header_end] if header_start >= 0 and header_end >= 0 else ""
        require(f".scriptsArchiveID = {bank}," in header_record, "map header uses wrong script bank", failures)

    return {
        "key": encounter.key,
        "species": encounter.species,
        "map_events": encounter.events_file,
        "coordinates": [encounter.x, encounter.y, encounter.z],
        "script_id": script_id,
        "level": encounter.level,
        "story_gate": encounter.story_flag,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    flag_lines = FLAGS_PATH.read_text().splitlines()
    records = [validate_encounter(encounter) for encounter in ENCOUNTERS]
    flag_failures = []
    for index, encounter in enumerate(ENCOUNTERS):
        expected_flags = (
            (0x0900 + index, encounter.defeated_flag),
            (0x0908 + index, encounter.hide_flag),
        )
        for flag_id, flag in expected_flags:
            count = flag_lines.count(flag)
            if count != 1:
                flag_failures.append(
                    f"{flag}: expected once in canonical flag list, found {count}"
                )
            actual = flag_lines[flag_id] if flag_id < len(flag_lines) else None
            if actual != flag:
                flag_failures.append(
                    f"flag 0x{flag_id:04X}: found {actual!r}, expected {flag!r}"
                )

    result = {
        "encounters": records,
        "flag_failures": flag_failures,
        "overall": "PASS"
        if not flag_failures and all(record["status"] == "PASS" for record in records)
        else "FAIL",
    }
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")
    return 0 if result["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

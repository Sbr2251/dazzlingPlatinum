#!/usr/bin/env python3
"""Integrate the eight planned one-time Totem field encounters.

This phase intentionally uses ordinary StartLegendaryBattle encounters. Custom
Totem battle rules are deferred; the goal here is production placement,
A-button interaction, one-time persistence, and reproducible validation.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FLAGS_PATH = ROOT / "generated/vars_flags.txt"
SCRIPTS_DIR = ROOT / "res/field/scripts"
EVENTS_DIR = ROOT / "res/field/events"
MAP_HEADERS_PATH = ROOT / "include/data/map_headers.h"


@dataclass(frozen=True)
class Encounter:
    key: str
    species: str
    graphics: str
    events_file: str
    scripts_file: str
    object_prefix: str
    label: str
    x: int
    z: int
    y: int
    level: int
    defeated_flag: str
    hide_flag: str
    story_flag: str | None = None
    transition_label: str | None = None
    new_script_bank: bool = False
    map_header: str | None = None


ENCOUNTERS = (
    Encounter(
        key="hitmonlee",
        species="HITMONLEE",
        graphics="OBJ_EVENT_GFX_TOTEM_HITMONLEE",
        events_file="events_ravaged_path.json",
        scripts_file="scripts_ravaged_path.s",
        object_prefix="RAVAGED_PATH_TOTEM_HITMONLEE",
        label="TotemHitmonlee_Encounter",
        x=19,
        z=45,
        y=0,
        level=20,
        defeated_flag="FLAG_TOTEM_HITMONLEE_DEFEATED",
        hide_flag="FLAG_HIDE_TOTEM_HITMONLEE",
    ),
    Encounter(
        key="vespiquen",
        species="VESPIQUEN",
        graphics="OBJ_EVENT_GFX_TOTEM_VESPIQUEN",
        events_file="events_eterna_forest.json",
        scripts_file="scripts_eterna_forest.s",
        object_prefix="ETERNA_FOREST_TOTEM_VESPIQUEN",
        label="TotemVespiquen_Encounter",
        x=84,
        z=36,
        y=0,
        level=25,
        defeated_flag="FLAG_TOTEM_VESPIQUEN_DEFEATED",
        hide_flag="FLAG_HIDE_TOTEM_VESPIQUEN",
        story_flag="FLAG_TRAVELED_WITH_CHERYL",
        transition_label="_0032",
    ),
    Encounter(
        key="skarmory",
        species="SKARMORY",
        graphics="OBJ_EVENT_GFX_TOTEM_SKARMORY",
        events_file="events_route_214.json",
        scripts_file="scripts_route_214.s",
        object_prefix="ROUTE_214_TOTEM_SKARMORY",
        label="TotemSkarmory_Encounter",
        x=726,
        z=664,
        y=0,
        level=35,
        defeated_flag="FLAG_TOTEM_SKARMORY_DEFEATED",
        hide_flag="FLAG_HIDE_TOTEM_SKARMORY",
    ),
    Encounter(
        key="lapras",
        species="LAPRAS",
        graphics="OBJ_EVENT_GFX_TOTEM_LAPRAS",
        events_file="events_route_213.json",
        scripts_file="scripts_route_213.s",
        object_prefix="ROUTE_213_TOTEM_LAPRAS",
        label="TotemLapras_Encounter",
        x=715,
        z=830,
        y=0,
        level=36,
        defeated_flag="FLAG_TOTEM_LAPRAS_DEFEATED",
        hide_flag="FLAG_HIDE_TOTEM_LAPRAS",
    ),
    Encounter(
        key="spiritomb",
        species="SPIRITOMB",
        graphics="OBJ_EVENT_GFX_TOTEM_SPIRITOMB",
        events_file="events_route_209_lost_tower_2f.json",
        scripts_file="scripts_route_209_lost_tower_2f.s",
        object_prefix="ROUTE_209_LOST_TOWER_2F_TOTEM_SPIRITOMB",
        label="TotemSpiritomb_Encounter",
        x=6,
        z=8,
        y=0,
        level=30,
        defeated_flag="FLAG_TOTEM_SPIRITOMB_DEFEATED",
        hide_flag="FLAG_HIDE_TOTEM_SPIRITOMB",
        new_script_bank=True,
        map_header="MAP_HEADER_ROUTE_209_LOST_TOWER_2F",
    ),
    Encounter(
        key="aggron",
        species="AGGRON",
        graphics="OBJ_EVENT_GFX_TOTEM_AGGRON",
        events_file="events_iron_island_b3f.json",
        scripts_file="scripts_iron_island_b3f.s",
        object_prefix="IRON_ISLAND_B3F_TOTEM_AGGRON",
        label="TotemAggron_Encounter",
        x=10,
        z=8,
        y=0,
        level=42,
        defeated_flag="FLAG_TOTEM_AGGRON_DEFEATED",
        hide_flag="FLAG_HIDE_TOTEM_AGGRON",
        story_flag="FLAG_TRAVELED_WITH_RILEY",
        transition_label="_0032",
    ),
    Encounter(
        key="mamoswine",
        species="MAMOSWINE",
        graphics="OBJ_EVENT_GFX_TOTEM_MAMOSWINE",
        events_file="events_acuity_lakefront.json",
        scripts_file="scripts_acuity_lakefront.s",
        object_prefix="ACUITY_LAKEFRONT_TOTEM_MAMOSWINE",
        label="TotemMamoswine_Encounter",
        x=312,
        z=243,
        y=0,
        level=44,
        defeated_flag="FLAG_TOTEM_MAMOSWINE_DEFEATED",
        hide_flag="FLAG_HIDE_TOTEM_MAMOSWINE",
    ),
    Encounter(
        key="kingdra",
        species="KINGDRA",
        graphics="OBJ_EVENT_GFX_TOTEM_KINGDRA",
        events_file="events_route_223.json",
        scripts_file="scripts_route_223.s",
        object_prefix="ROUTE_223_TOTEM_KINGDRA",
        label="TotemKingdra_Encounter",
        x=853,
        z=739,
        y=0,
        level=50,
        defeated_flag="FLAG_TOTEM_KINGDRA_DEFEATED",
        hide_flag="FLAG_HIDE_TOTEM_KINGDRA",
        new_script_bank=True,
        map_header="MAP_HEADER_ROUTE_223",
    ),
)


FLAG_RENAMES = (
    ("FLAG_UNK_0x0900", "FLAG_TOTEM_HITMONLEE_DEFEATED"),
    ("FLAG_UNK_0x0901", "FLAG_TOTEM_VESPIQUEN_DEFEATED"),
    ("FLAG_UNK_0x0902", "FLAG_TOTEM_SKARMORY_DEFEATED"),
    ("FLAG_UNK_0x0903", "FLAG_TOTEM_LAPRAS_DEFEATED"),
    ("FLAG_UNK_0x0904", "FLAG_TOTEM_SPIRITOMB_DEFEATED"),
    ("FLAG_UNK_0x0905", "FLAG_TOTEM_AGGRON_DEFEATED"),
    ("FLAG_UNK_0x0906", "FLAG_TOTEM_MAMOSWINE_DEFEATED"),
    ("FLAG_UNK_0x0907", "FLAG_TOTEM_KINGDRA_DEFEATED"),
    ("FLAG_UNK_0x0908", "FLAG_HIDE_TOTEM_HITMONLEE"),
    ("FLAG_UNK_0x0909", "FLAG_HIDE_TOTEM_VESPIQUEN"),
    ("FLAG_UNK_0x090A", "FLAG_HIDE_TOTEM_SKARMORY"),
    ("FLAG_UNK_0x090B", "FLAG_HIDE_TOTEM_LAPRAS"),
    ("FLAG_UNK_0x090C", "FLAG_HIDE_TOTEM_SPIRITOMB"),
    ("FLAG_UNK_0x090D", "FLAG_HIDE_TOTEM_AGGRON"),
    ("FLAG_UNK_0x090E", "FLAG_HIDE_TOTEM_MAMOSWINE"),
    ("FLAG_UNK_0x090F", "FLAG_HIDE_TOTEM_KINGDRA"),
)

BAD_FLAG_RENAMES = (
    ("FLAG_UNK_0x0AC3", "FLAG_TOTEM_HITMONLEE_DEFEATED"),
    ("FLAG_UNK_0x0AC4", "FLAG_TOTEM_VESPIQUEN_DEFEATED"),
    ("FLAG_UNK_0x0AC5", "FLAG_TOTEM_SKARMORY_DEFEATED"),
    ("FLAG_UNK_0x0AC6", "FLAG_TOTEM_LAPRAS_DEFEATED"),
    ("FLAG_UNK_0x0AC7", "FLAG_TOTEM_SPIRITOMB_DEFEATED"),
    ("FLAG_UNK_0x0AC8", "FLAG_TOTEM_AGGRON_DEFEATED"),
    ("FLAG_UNK_0x0AC9", "FLAG_TOTEM_MAMOSWINE_DEFEATED"),
    ("FLAG_UNK_0x0ACA", "FLAG_TOTEM_KINGDRA_DEFEATED"),
    ("FLAG_UNK_0x0ACB", "FLAG_HIDE_TOTEM_HITMONLEE"),
    ("FLAG_UNK_0x0ACC", "FLAG_HIDE_TOTEM_VESPIQUEN"),
    ("FLAG_UNK_0x0ACD", "FLAG_HIDE_TOTEM_SKARMORY"),
    ("FLAG_UNK_0x0ACE", "FLAG_HIDE_TOTEM_LAPRAS"),
    ("FLAG_UNK_0x0ACF", "FLAG_HIDE_TOTEM_SPIRITOMB"),
    ("FLAG_UNK_0x0AD0", "FLAG_HIDE_TOTEM_AGGRON"),
    ("FLAG_UNK_0x0AD1", "FLAG_HIDE_TOTEM_MAMOSWINE"),
    ("FLAG_UNK_0x0AD2", "FLAG_HIDE_TOTEM_KINGDRA"),
)


def write_if_changed(path: Path, text: str) -> None:
    if not text.endswith("\n"):
        text += "\n"
    if path.exists() and path.read_text() == text:
        return
    path.write_text(text)


def rename_flags() -> None:
    text = FLAGS_PATH.read_text()
    for old, new in BAD_FLAG_RENAMES:
        if new in text and old not in text:
            text = text.replace(new, old, 1)
    for old, new in FLAG_RENAMES:
        if new in text:
            continue
        count = text.count(old)
        if count != 1:
            raise RuntimeError(f"expected exactly one {old}, found {count}")
        text = text.replace(old, new, 1)
    write_if_changed(FLAGS_PATH, text)


def encounter_block(encounter: Encounter) -> str:
    lost = f"{encounter.label}_LostBattle"
    return f"""{encounter.label}:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    PlayCry SPECIES_{encounter.species}
    WaitCry
    SetFlag FLAG_MAP_LOCAL
    StartLegendaryBattle SPECIES_{encounter.species}, {encounter.level}
    ClearFlag FLAG_MAP_LOCAL
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, {lost}
    SetFlag {encounter.defeated_flag}
    SetFlag {encounter.hide_flag}
    RemoveObject VAR_LAST_TALKED
    ReleaseAll
    End

{lost}:
    BlackOutFromBattle
    ReleaseAll
    End"""


def visibility_block(encounter: Encounter) -> str:
    assert encounter.story_flag is not None
    prefix = encounter.label.removesuffix("_Encounter")
    update = f"{prefix}_UpdateVisibility"
    hide = f"{prefix}_Hide"
    return f"""{update}:
    GoToIfUnset {encounter.story_flag}, {hide}
    GoToIfSet {encounter.defeated_flag}, {hide}
    ClearFlag {encounter.hide_flag}
    Return

{hide}:
    SetFlag {encounter.hide_flag}
    Return"""


def script_entries(text: str) -> list[str]:
    before_end = text.split("ScriptEntryEnd", 1)[0]
    return re.findall(r"^\s*ScriptEntry\s+([A-Za-z0-9_]+)\s*$", before_end, re.MULTILINE)


def ensure_script(encounter: Encounter) -> int:
    path = SCRIPTS_DIR / encounter.scripts_file
    if path.exists():
        text = path.read_text()
    else:
        if not encounter.new_script_bank:
            raise FileNotFoundError(path)
        text = '#include "macros/scrcmd.inc"\n\n\n    ScriptEntryEnd\n'

    entries = script_entries(text)
    if encounter.label not in entries:
        marker = "    ScriptEntryEnd"
        if marker not in text:
            raise RuntimeError(f"missing ScriptEntryEnd in {path}")
        text = text.replace(marker, f"    ScriptEntry {encounter.label}\n{marker}", 1)
        entries.append(encounter.label)

    if f"{encounter.label}:" not in text:
        text = text.rstrip() + "\n\n" + encounter_block(encounter) + "\n\n    .balign 4, 0\n"

    if encounter.story_flag is not None:
        assert encounter.transition_label is not None
        call_line = f"    Call {encounter.label.removesuffix('_Encounter')}_UpdateVisibility"
        label_line = f"{encounter.transition_label}:"
        if call_line not in text:
            if label_line not in text:
                raise RuntimeError(f"missing transition label {label_line} in {path}")
            text = text.replace(label_line, f"{label_line}\n{call_line}", 1)
        update_label = f"{encounter.label.removesuffix('_Encounter')}_UpdateVisibility:"
        if update_label not in text:
            text = text.rstrip() + "\n\n" + visibility_block(encounter) + "\n\n    .balign 4, 0\n"

    write_if_changed(path, text)
    entries = script_entries(text)
    return entries.index(encounter.label) + 1


def ensure_event(encounter: Encounter, script_id: int) -> None:
    path = EVENTS_DIR / encounter.events_file
    data = json.loads(path.read_text())
    objects = data["object_events"]
    matches = [obj for obj in objects if obj.get("graphics_id") == encounter.graphics]
    expected = {
        "graphics_id": encounter.graphics,
        "movement_type": "MOVEMENT_TYPE_NONE",
        "trainer_type": "TRAINER_TYPE_NONE",
        "hidden_flag": encounter.hide_flag,
        "script": script_id,
        "initial_dir": 1,
        "data": [],
        "movement_range_x": 0,
        "movement_range_z": 0,
        "x": encounter.x,
        "z": encounter.z,
        "y": encounter.y,
    }
    if len(matches) > 1:
        raise RuntimeError(f"multiple {encounter.graphics} objects in {path}")
    if matches:
        obj = matches[0]
        obj.update(expected)
    else:
        obj = {"id": f"{encounter.object_prefix}_{len(objects)}", **expected}
        objects.append(obj)
    write_if_changed(path, json.dumps(data, indent=4) + "\n")


def ensure_new_script_archives() -> None:
    names = [Path(enc.scripts_file).stem for enc in ENCOUNTERS if enc.new_script_bank]

    order_path = SCRIPTS_DIR / "scripts.order"
    order_lines = order_path.read_text().splitlines()
    for name in names:
        if name not in order_lines:
            order_lines.append(name)
    write_if_changed(order_path, "\n".join(order_lines) + "\n")

    meson_path = SCRIPTS_DIR / "meson.build"
    meson = meson_path.read_text()
    anchor = "\n)\n\nscr_seq_narc_order = files('scripts.order')"
    if anchor not in meson:
        raise RuntimeError("field-script Meson list anchor not found")
    additions = "".join(
        f"    '{name}.s',\n" for name in names if f"    '{name}.s',\n" not in meson
    )
    if additions:
        meson = meson.replace(anchor, f"\n{additions})\n\nscr_seq_narc_order = files('scripts.order')", 1)
        write_if_changed(meson_path, meson)


def ensure_map_header_script_bank(encounter: Encounter) -> None:
    assert encounter.map_header is not None
    bank = Path(encounter.scripts_file).stem
    text = MAP_HEADERS_PATH.read_text()
    start_marker = f"    [{encounter.map_header}] = {{"
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"missing {encounter.map_header}")
    end = text.find("    },", start)
    if end < 0:
        raise RuntimeError(f"unterminated {encounter.map_header}")
    record = text[start:end]
    desired = f".scriptsArchiveID = {bank},"
    if desired not in record:
        replaced, count = re.subn(
            r"\.scriptsArchiveID = [A-Za-z0-9_]+,",
            desired,
            record,
            count=1,
        )
        if count != 1:
            raise RuntimeError(f"could not update scriptsArchiveID for {encounter.map_header}")
        text = text[:start] + replaced + text[end:]
        write_if_changed(MAP_HEADERS_PATH, text)


def main() -> None:
    rename_flags()
    ensure_new_script_archives()

    summary: list[dict[str, object]] = []
    for encounter in ENCOUNTERS:
        script_id = ensure_script(encounter)
        ensure_event(encounter, script_id)
        if encounter.new_script_bank:
            ensure_map_header_script_bank(encounter)
        summary.append(
            {
                "species": encounter.species,
                "map_events": encounter.events_file,
                "coordinates": [encounter.x, encounter.y, encounter.z],
                "script": encounter.scripts_file,
                "script_id": script_id,
                "level": encounter.level,
                "story_gate": encounter.story_flag,
                "defeated_flag": encounter.defeated_flag,
                "hide_flag": encounter.hide_flag,
            }
        )

    print(json.dumps({"encounters": summary}, indent=2))


if __name__ == "__main__":
    main()

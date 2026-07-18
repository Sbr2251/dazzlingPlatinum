#!/usr/bin/env python3
"""Build a temporary ROM that warps a verified online save to each Totem map.

The production encounter implementation remains active. The proof-only ROM appends
8 warp handlers to Victory Road 1F and injects one runtime Poké Ball beside the
loaded player. Eight donor-save variants encode the requested destination in the
active partition's X/facing fields while staying within the same map chunk.
Production sources and ROM are rebuilt and restored after copying the proof ROM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path

PARTITION_SIZE = 0x40000
GENERAL_SIZE = 0xCF2C
MAIN_FOOTER_SIZE = 20
FIELD_PLAYER_STATE_OFFSET = 0x1280
ROM_PATH = Path("build/pokeplatinum.us.nds")
MAP_OBJECT_PATH = Path("src/map_object.c")
VICTORY_SCRIPT_PATH = Path("res/field/scripts/scripts_victory_road_1f.s")


@dataclass(frozen=True)
class Destination:
    slug: str
    species: str
    map_header: str
    player_x: int
    player_z: int
    warp_face: int
    approach_key: str
    totem_x: int
    totem_z: int


DESTINATIONS = (
    Destination("hitmonlee", "HITMONLEE", "MAP_HEADER_RAVAGED_PATH", 18, 45, 3, "Right", 19, 45),
    Destination("vespiquen", "VESPIQUEN", "MAP_HEADER_ETERNA_FOREST", 83, 36, 3, "Right", 84, 36),
    Destination("skarmory", "SKARMORY", "MAP_HEADER_ROUTE_214", 725, 664, 3, "Right", 726, 664),
    Destination("lapras", "LAPRAS", "MAP_HEADER_ROUTE_213", 714, 830, 3, "Right", 715, 830),
    Destination("spiritomb", "SPIRITOMB", "MAP_HEADER_ROUTE_209_LOST_TOWER_2F", 5, 8, 3, "Right", 6, 8),
    Destination("aggron", "AGGRON", "MAP_HEADER_IRON_ISLAND_B3F", 10, 9, 0, "Up", 10, 8),
    Destination("mamoswine", "MAMOSWINE", "MAP_HEADER_ACUITY_LAKEFRONT", 311, 243, 3, "Right", 312, 243),
    Destination("kingdra", "KINGDRA", "MAP_HEADER_ROUTE_223", 853, 740, 0, "Up", 853, 739),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def general_block_valid(raw: bytes | bytearray, base: int) -> bool:
    footer = base + GENERAL_SIZE - MAIN_FOOTER_SIZE
    expected = struct.unpack_from("<H", raw, footer + 18)[0]
    return crc16_ccitt(raw[base:footer]) == expected


def active_partition(raw: bytes | bytearray) -> int:
    candidates: list[tuple[int, int, int]] = []
    for partition in (0, 1):
        base = partition * PARTITION_SIZE
        if not general_block_valid(raw, base):
            continue
        footer = base + GENERAL_SIZE - MAIN_FOOTER_SIZE
        save_counter, block_counter = struct.unpack_from("<II", raw, footer)
        candidates.append((save_counter, block_counter, partition))
    if not candidates:
        raise ValueError("donor has no valid general partition")
    return max(candidates)[2]


def resolve_map_id(root: Path, symbol: str) -> int:
    symbols = (root / "generated/map_headers.txt").read_text().splitlines()
    return symbols.index(symbol)


def build_selector_saves(root: Path, donor: Path, output_dir: Path) -> list[dict[str, object]]:
    raw = donor.read_bytes()
    if len(raw) != 0x80000:
        raise ValueError(f"expected 512 KiB raw donor, got {len(raw)} bytes")
    victory_id = resolve_map_id(root, "MAP_HEADER_VICTORY_ROAD_1F")
    active = active_partition(raw)
    active_base = active * PARTITION_SIZE
    state = active_base + FIELD_PLAYER_STATE_OFFSET
    map_id, warp_id, original_x, original_z, original_face = struct.unpack_from("<iiiii", raw, state)
    if map_id != victory_id:
        raise ValueError(f"active donor partition must be Victory Road 1F ({victory_id}), got {map_id}")

    save_dir = output_dir / "selector-saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for selector, destination in enumerate(DESTINATIONS):
        staged = bytearray(raw)
        encoded_x = 36 if selector < 4 else 37
        encoded_face = selector % 4
        struct.pack_into("<iiiii", staged, state, map_id, -1, encoded_x, original_z, encoded_face)
        footer = active_base + GENERAL_SIZE - MAIN_FOOTER_SIZE
        struct.pack_into("<H", staged, footer + 18, crc16_ccitt(staged[active_base:footer]))
        if not general_block_valid(staged, active_base):
            raise AssertionError(f"selector {selector} general-block checksum failed")
        output = save_dir / f"{destination.slug}-selector.sav"
        output.write_bytes(staged)
        records.append(
            {
                "selector": selector,
                "species": destination.species,
                "slug": destination.slug,
                "encoded_donor_state": {
                    "map_id": map_id,
                    "warp_id": -1,
                    "x": encoded_x,
                    "z": original_z,
                    "face": encoded_face,
                },
                "target": {
                    "map_header": destination.map_header,
                    "player_x": destination.player_x,
                    "player_z": destination.player_z,
                    "warp_face": destination.warp_face,
                    "approach_key": destination.approach_key,
                    "totem_x": destination.totem_x,
                    "totem_z": destination.totem_z,
                },
                "path": str(output),
                "sha256": sha256_bytes(staged),
            }
        )
    return records


def stage_victory_script(original: bytes) -> bytes:
    source = original.decode()
    entry_anchor = "    ScriptEntryEnd\n"
    if source.count(entry_anchor) != 1:
        raise ValueError("Victory Road ScriptEntryEnd anchor is not unique")
    entries = "".join(f"    ScriptEntry TotemLocationWarp_{d.species}\n" for d in DESTINATIONS)
    source = source.replace(entry_anchor, entries + entry_anchor, 1)

    body_anchor = "    .balign 4, 0\n"
    if source.count(body_anchor) != 1:
        raise ValueError("Victory Road alignment anchor is not unique")
    handlers: list[str] = []
    for destination in DESTINATIONS:
        handlers.append(
            f"TotemLocationWarp_{destination.species}:\n"
            "    PlayFanfare SEQ_SE_CONFIRM\n"
            "    LockAll\n"
            "    FacePlayer\n"
            "    FadeScreenOut\n"
            "    WaitFadeScreen\n"
            f"    Warp {destination.map_header}, 0, {destination.player_x}, {destination.player_z}, {destination.warp_face}\n"
            "    FadeScreenIn\n"
            "    WaitFadeScreen\n"
            "    ReleaseAll\n"
            "    End\n\n"
        )
    return source.replace(body_anchor, "".join(handlers) + body_anchor, 1).encode()


def stage_map_object_source(original: bytes) -> bytes:
    source = original.decode()
    include_anchor = '#include "generated/movement_types.h"\n'
    include_replacement = (
        '#include "generated/map_headers.h"\n'
        '#include "generated/movement_types.h"\n'
        '#include "generated/object_events_gfx.h"\n'
    )
    if source.count(include_anchor) != 1:
        raise ValueError("map_object.c include anchor is not unique")
    source = source.replace(include_anchor, include_replacement, 1)

    function_anchor = "        size--;\n    }\n}\n\nstatic void MapObject_Save"
    hook = (
        "        size--;\n"
        "    }\n\n"
        "    {\n"
        "        FieldSystem *fieldSystem = MapObjectMan_FieldSystem(mapObjMan);\n"
        "        if (fieldSystem->location->mapId == MAP_HEADER_VICTORY_ROAD_1F) {\n"
        "            int selector = fieldSystem->location->faceDirection & 3;\n"
        "            MapObject *selectorObject;\n"
        "            if (fieldSystem->location->x == 37) {\n"
        "                selector += 4;\n"
        "            }\n"
        "            selectorObject = MapObjectMan_AddMapObject(\n"
        "                mapObjMan, fieldSystem->location->x + 1, fieldSystem->location->z,\n"
        "                2, OBJ_EVENT_GFX_POKEBALL, MOVEMENT_TYPE_NONE, MAP_HEADER_VICTORY_ROAD_1F);\n"
        "            if (selectorObject != NULL) {\n"
        "                MapObject_SetLocalID(selectorObject, 250);\n"
        "                MapObject_SetScript(selectorObject, 3 + selector);\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "}\n\nstatic void MapObject_Save"
    )
    if source.count(function_anchor) != 1:
        raise ValueError("MapObjectMan_LoadAllObjects tail anchor is not unique")
    return source.replace(function_anchor, hook, 1).encode()


def run_build(root: Path, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("wb") as log:
        result = subprocess.run(
            ["ninja", "-C", "build", "-j2"],
            cwd=root,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if result.returncode != 0:
        raise RuntimeError(f"build failed; see {log_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("donor_save", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    root = args.root.resolve()
    donor = args.donor_save.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    map_object_path = root / MAP_OBJECT_PATH
    script_path = root / VICTORY_SCRIPT_PATH
    rom_path = root / ROM_PATH
    original_map_object = map_object_path.read_bytes()
    original_script = script_path.read_bytes()
    staged_map_object = stage_map_object_source(original_map_object)
    staged_script = stage_victory_script(original_script)
    selector_records = build_selector_saves(root, donor, output_dir)

    proof_rom = output_dir / "totem-location-save-generator.nds"
    try:
        map_object_path.write_bytes(staged_map_object)
        script_path.write_bytes(staged_script)
        run_build(root, output_dir / "proof-build.log")
        shutil.copy2(rom_path, proof_rom)
    finally:
        map_object_path.write_bytes(original_map_object)
        script_path.write_bytes(original_script)
        run_build(root, output_dir / "production-restore-build.log")

    if map_object_path.read_bytes() != original_map_object:
        raise AssertionError("map_object.c was not restored byte-for-byte")
    if script_path.read_bytes() != original_script:
        raise AssertionError("Victory Road script was not restored byte-for-byte")

    manifest = {
        "donor": {
            "path": str(donor),
            "sha256": sha256_bytes(donor.read_bytes()),
        },
        "proof_rom": {
            "path": str(proof_rom),
            "sha256": sha256_bytes(proof_rom.read_bytes()),
        },
        "restored_production_rom": {
            "path": str(rom_path),
            "sha256": sha256_bytes(rom_path.read_bytes()),
        },
        "source_restoration": {
            "map_object_restored": True,
            "victory_road_script_restored": True,
        },
        "selectors": selector_records,
    }
    (output_dir / "generator-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

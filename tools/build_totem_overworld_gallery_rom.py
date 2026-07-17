#!/usr/bin/env python3
"""Build an isolated Route 206 overworld gallery ROM for Totem sprite QA.

The production branch keeps only the eight graphics resources and runtime table
registrations. This tool temporarily appends eight noninteractive static objects
to Route 206 around the project's proven validation save, builds and copies a
proof ROM, restores the event source, then rebuilds the production ROM. The
source save is copied byte-for-byte; no cross-map relocation is attempted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path

from assign_mega_stones_to_party import (
    GENERAL_SIZE,
    MAIN_FOOTER_SIZE,
    PARTITION_SIZE,
    crc16_ccitt,
    general_block_valid,
)

EVENT_PATH = Path("res/field/events/events_route_206.json")
MAP_OBJECT_SOURCE_PATH = Path("src/map_object.c")
ROM_PATH = Path("build/pokeplatinum.us.nds")
FIELD_PLAYER_STATE_OFFSET = 0x1280

# The known-good source save's current general partition is on southern Route
# 206 at (309, 685). Preserve that save byte-for-byte and stage the proof just
# north of it on the same y=0 terrain used by the production Poké Ball row at
# z=678. This avoids corrupting internally coupled field state by editing X/Z.
GALLERY_PLAYER_X = 309
GALLERY_PLAYER_Z = 685
GALLERY_Y = 0

TOTEM_OBJECTS = (
    ("TOTEM_GALLERY_HITMONLEE", "OBJ_EVENT_GFX_TOTEM_HITMONLEE", 309, 678, GALLERY_Y),
    ("TOTEM_GALLERY_VESPIQUEN", "OBJ_EVENT_GFX_TOTEM_VESPIQUEN", 310, 678, GALLERY_Y),
    ("TOTEM_GALLERY_SKARMORY", "OBJ_EVENT_GFX_TOTEM_SKARMORY", 309, 680, GALLERY_Y),
    ("TOTEM_GALLERY_LAPRAS", "OBJ_EVENT_GFX_TOTEM_LAPRAS", 310, 680, GALLERY_Y),
    ("TOTEM_GALLERY_SPIRITOMB", "OBJ_EVENT_GFX_TOTEM_SPIRITOMB", 309, 682, GALLERY_Y),
    ("TOTEM_GALLERY_AGGRON", "OBJ_EVENT_GFX_TOTEM_AGGRON", 310, 682, GALLERY_Y),
    ("TOTEM_GALLERY_MAMOSWINE", "OBJ_EVENT_GFX_TOTEM_MAMOSWINE", 309, 684, GALLERY_Y),
    ("TOTEM_GALLERY_KINGDRA", "OBJ_EVENT_GFX_TOTEM_KINGDRA", 310, 684, GALLERY_Y),
)

CONTROL_OBJECTS = (
    ("TOTEM_GALLERY_CONTROL_WEST", "OBJ_EVENT_GFX_HIKER", 308, 685, GALLERY_Y),
    ("TOTEM_GALLERY_CONTROL_EAST", "OBJ_EVENT_GFX_UXIE", 310, 685, GALLERY_Y),
    ("TOTEM_GALLERY_CONTROL_NORTH", "OBJ_EVENT_GFX_POKECENTER_NURSE", 309, 684, GALLERY_Y),
    ("TOTEM_GALLERY_CONTROL_SOUTH", "OBJ_EVENT_GFX_POKEBALL", 309, 686, GALLERY_Y),
)

SPECIES_GRAPHICS = {
    "hitmonlee": "OBJ_EVENT_GFX_TOTEM_HITMONLEE",
    "vespiquen": "OBJ_EVENT_GFX_TOTEM_VESPIQUEN",
    "skarmory": "OBJ_EVENT_GFX_TOTEM_SKARMORY",
    "lapras": "OBJ_EVENT_GFX_TOTEM_LAPRAS",
    "spiritomb": "OBJ_EVENT_GFX_TOTEM_SPIRITOMB",
    "aggron": "OBJ_EVENT_GFX_TOTEM_AGGRON",
    "mamoswine": "OBJ_EVENT_GFX_TOTEM_MAMOSWINE",
    "kingdra": "OBJ_EVENT_GFX_TOTEM_KINGDRA",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_map_id(root: Path, symbol: str) -> int:
    symbols = (root / "generated/map_headers.txt").read_text().splitlines()
    return symbols.index(symbol)


def gallery_object(local_id: str, graphics_id: str, x: int, z: int, y: int) -> dict:
    return {
        "id": local_id,
        "graphics_id": graphics_id,
        "movement_type": "MOVEMENT_TYPE_NONE",
        "trainer_type": "TRAINER_TYPE_NONE",
        "hidden_flag": "0",
        "script": 65535,
        "initial_dir": 1,
        "data": [],
        "movement_range_x": 0,
        "movement_range_z": 0,
        "x": x,
        "z": z,
        "y": y,
    }


def stage_gallery_events(original: bytes, objects: tuple[tuple[str, str, int, int, int], ...]) -> bytes:
    events = json.loads(original)
    # Route 206 already contains 35 production objects. The isolated proof ROM
    # replaces that list with at most eight validation objects, and production
    # events are restored byte-for-byte immediately after the proof build.
    events["object_events"] = [
        gallery_object(local_id, graphics_id, x, z, y)
        for local_id, graphics_id, x, z, y in objects
    ]
    return (json.dumps(events, indent=4) + "\n").encode()


def stage_runtime_spawn_source(
    original: bytes,
    objects: tuple[tuple[str, str, int, int, int], ...],
) -> bytes:
    source = original.decode()
    include_anchor = '#include "generated/movement_types.h"\n'
    include_replacement = (
        '#include "generated/map_headers.h"\n'
        '#include "generated/movement_types.h"\n'
        '#include "generated/object_events_gfx.h"\n'
    )
    if source.count(include_anchor) != 1:
        raise ValueError("Could not uniquely locate map_object.c include anchor")
    source = source.replace(include_anchor, include_replacement, 1)

    function_anchor = "        size--;\n    }\n}\n\nstatic void MapObject_Save"
    calls = "\n".join(
        "        MapObjectMan_AddMapObject("
        f"mapObjMan, {x}, {z}, 1, {graphics_id}, "
        "MOVEMENT_TYPE_NONE, MAP_HEADER_ROUTE_206);"
        for _, graphics_id, x, z, _ in objects
    )
    function_replacement = (
        "        size--;\n"
        "    }\n\n"
        "    if (MapObjectMan_FieldSystem(mapObjMan)->location->mapId "
        "== MAP_HEADER_ROUTE_206) {\n"
        f"{calls}\n"
        "    }\n"
        "}\n\n"
        "static void MapObject_Save"
    )
    if source.count(function_anchor) != 1:
        raise ValueError("Could not uniquely locate MapObjectMan_LoadAllObjects tail")
    return source.replace(function_anchor, function_replacement, 1).encode()


def copy_gallery_save(
    root: Path,
    source: Path,
    output: Path,
    relocate: tuple[int, int] | None = None,
) -> list[str]:
    raw_file = source.read_bytes()
    if len(raw_file) not in (0x80000, 0x80000 + 122):
        raise ValueError(f"Unexpected save length: {len(raw_file)}")

    raw = bytearray(raw_file[:0x80000])
    route_206 = resolve_map_id(root, "MAP_HEADER_ROUTE_206")
    messages: list[str] = []
    valid_locations: list[tuple[int, int, int, int, int, int, int, int]] = []

    for partition in (0, 1):
        base = partition * PARTITION_SIZE
        if not general_block_valid(raw, base):
            messages.append(f"partition {partition}: invalid; ignored")
            continue
        offset = base + FIELD_PLAYER_STATE_OFFSET
        map_id, warp_id, x, z, face = struct.unpack_from("<iiiii", raw, offset)
        if map_id != route_206:
            raise ValueError(
                f"partition {partition}: expected Route 206 map {route_206}, got {map_id}"
            )
        footer_offset = base + GENERAL_SIZE - MAIN_FOOTER_SIZE
        save_counter, block_counter = struct.unpack_from("<II", raw, footer_offset)
        valid_locations.append(
            (save_counter, block_counter, partition, map_id, warp_id, x, z, face)
        )
        messages.append(
            f"partition {partition}: Route 206 position ({x},{z}), warp {warp_id}, "
            f"face {face}, save counter {save_counter}, block counter {block_counter}"
        )

    if not valid_locations:
        raise ValueError("No valid Route 206 general save partition found")
    active = max(valid_locations)
    _, _, active_partition, _, _, active_x, active_z, _ = active
    if (active_x, active_z) != (GALLERY_PLAYER_X, GALLERY_PLAYER_Z):
        raise ValueError(
            f"active partition {active_partition}: expected gallery source position "
            f"({GALLERY_PLAYER_X},{GALLERY_PLAYER_Z}), got ({active_x},{active_z})"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    if relocate is None:
        messages.append(
            f"active general partition {active_partition} retained byte-for-byte at "
            f"({active_x},{active_z})"
        )
        shutil.copy2(source, output)
        if output.read_bytes() != raw_file:
            raise AssertionError("Gallery save copy is not byte-identical to source")
        return messages

    relocate_x, relocate_z = relocate
    for _, _, partition, map_id, _, x, z, face in valid_locations:
        base = partition * PARTITION_SIZE
        offset = base + FIELD_PLAYER_STATE_OFFSET
        struct.pack_into(
            "<iiiii", raw, offset, map_id, -1, relocate_x, relocate_z, face
        )
        footer_offset = base + GENERAL_SIZE - MAIN_FOOTER_SIZE
        struct.pack_into(
            "<H", raw, footer_offset + 18, crc16_ccitt(raw[base:footer_offset])
        )
        if not general_block_valid(raw, base):
            raise AssertionError(
                f"partition {partition}: relocated general-block CRC failed"
            )
        messages.append(
            f"partition {partition}: temporary Route 206 relocation "
            f"({x},{z}) -> ({relocate_x},{relocate_z}); warp -1; CRC refreshed"
        )

    output.write_bytes(bytes(raw) + raw_file[0x80000:])
    return messages


def run_ninja(root: Path, build_dir: Path, log_path: Path) -> None:
    result = subprocess.run(
        ["ninja", "-C", str(build_dir)],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(f"ninja failed; see {log_path}")


def build_gallery(
    root: Path,
    build_dir: Path,
    source_save: Path,
    output_dir: Path,
    objects: tuple[tuple[str, str, int, int, int], ...],
    relocate_save: tuple[int, int] | None = None,
) -> None:
    event_path = root / EVENT_PATH
    map_object_source_path = root / MAP_OBJECT_SOURCE_PATH
    rom_path = root / ROM_PATH
    original_events = event_path.read_bytes()
    original_map_object_source = map_object_source_path.read_bytes()
    staged_events = stage_gallery_events(original_events, objects)
    staged_map_object_source = stage_runtime_spawn_source(
        original_map_object_source, objects
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    save_output = output_dir / "totem-overworld-gallery.sav"
    save_messages = copy_gallery_save(
        root, source_save, save_output, relocate=relocate_save
    )
    production_hash_before = sha256(original_events)
    production_map_object_hash_before = sha256(original_map_object_source)
    gallery_hash = sha256(staged_events)
    staged_map_object_hash = sha256(staged_map_object_source)

    gallery_build_log = output_dir / "gallery-build.log"
    restore_build_log = output_dir / "production-restore-build.log"
    gallery_rom = output_dir / "totem-overworld-gallery.nds"

    try:
        event_path.write_bytes(staged_events)
        map_object_source_path.write_bytes(staged_map_object_source)
        run_ninja(root, build_dir, gallery_build_log)
        shutil.copy2(rom_path, gallery_rom)
    finally:
        event_path.write_bytes(original_events)
        map_object_source_path.write_bytes(original_map_object_source)

    if sha256(event_path.read_bytes()) != production_hash_before:
        raise AssertionError("Route 206 event source was not restored byte-for-byte")
    if sha256(map_object_source_path.read_bytes()) != production_map_object_hash_before:
        raise AssertionError("map_object.c was not restored byte-for-byte")

    run_ninja(root, build_dir, restore_build_log)

    manifest_lines = [
        "Totem overworld Route 206 gallery build",
        f"production_event_sha256={production_hash_before}",
        f"staged_gallery_event_sha256={gallery_hash}",
        f"restored_event_sha256={sha256(event_path.read_bytes())}",
        f"production_map_object_sha256={production_map_object_hash_before}",
        f"staged_map_object_sha256={staged_map_object_hash}",
        f"restored_map_object_sha256={sha256(map_object_source_path.read_bytes())}",
        f"gallery_rom_sha256={sha256(gallery_rom.read_bytes())}",
        f"restored_production_rom_sha256={sha256(rom_path.read_bytes())}",
        f"gallery_save_sha256={sha256(save_output.read_bytes())}",
        f"source_save_sha256={sha256(source_save.read_bytes())}",
        "",
        *save_messages,
        "",
        "gallery_objects:",
    ]
    manifest_lines.extend(
        f"  {local_id}: {graphics_id} at ({x},{z},{y})"
        for local_id, graphics_id, x, z, y in objects
    )
    (output_dir / "gallery-build-manifest.txt").write_text(
        "\n".join(manifest_lines) + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--build-dir", type=Path, default=Path("build"))
    parser.add_argument(
        "--source-save",
        type=Path,
        default=Path("deliverables/live-mega-test-no-repel.sav"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("deliverables/totem-overworld-sprites/gallery-build-route206"),
    )
    parser.add_argument(
        "--control-test",
        action="store_true",
        help="Build four vanilla objects on the player-adjacent cardinal tiles.",
    )
    parser.add_argument(
        "--species",
        choices=tuple(SPECIES_GRAPHICS),
        help="Build one Totem species beside the Route 206 south-gate return point.",
    )
    parser.add_argument(
        "--relocate-save",
        type=int,
        nargs=2,
        metavar=("X", "Z"),
        help=(
            "Temporarily relocate every valid Route 206 save partition and refresh "
            "its general-block CRC; intended only to trigger an immediate map reload."
        ),
    )
    args = parser.parse_args()
    if args.control_test and args.species:
        parser.error("--control-test and --species are mutually exclusive")
    root = args.root.resolve()
    build_dir = args.build_dir if args.build_dir.is_absolute() else root / args.build_dir
    source_save = args.source_save if args.source_save.is_absolute() else root / args.source_save
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    if args.control_test:
        objects = CONTROL_OBJECTS
    elif args.species:
        objects = (
            (
                f"TOTEM_PROOF_{args.species.upper()}",
                SPECIES_GRAPHICS[args.species],
                310,
                685,
                GALLERY_Y,
            ),
        )
    else:
        objects = TOTEM_OBJECTS
    relocate_save = tuple(args.relocate_save) if args.relocate_save else None
    build_gallery(
        root,
        build_dir,
        source_save,
        output_dir,
        objects,
        relocate_save=relocate_save,
    )
    print(f"Gallery ROM and save written to {output_dir}")


if __name__ == "__main__":
    main()

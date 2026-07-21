#!/usr/bin/env python3
"""Build deterministic raw saves for Parallel Sinnoh story-event runtime tests."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from platinum_save_utils import (  # noqa: E402
    GENERAL_SIZE,
    MAIN_FOOTER_SIZE,
    PARTITION_SIZE,
    crc16_ccitt,
    general_block_valid,
    p16,
    u16,
)

FIELD_PLAYER_STATE_OFFSET = 0x1280
FIELD_OVERWORLD_SAVE_OFFSET = 0x2858
MAP_OBJECT_SAVE_SIZE = 0x50
MAP_OBJECT_SAVE_COUNT = 64
VARS_FLAGS_OFFSET = 0x0DAC
VAR_ID_BASE = 0x4000
NUM_VARS = 0x120
FLAGS_OFFSET = VARS_FLAGS_OFFSET + NUM_VARS * 2

MAP_MT_CORONET_1F_SOUTH = 207
MAP_SPEAR_PILLAR = 220
MAP_ROUTE_218 = 388

VAR_CINDER_RIFT_VANILLA_STATE = 0x4096
VAR_EVERSPRING_STATE = 0x40EA
VAR_CINDER_RIFT_RIVAL_STATE = 0x40EB
VAR_SPEAR_PILLAR_STATE = 0x40EC
VAR_CINDER_RIFT_CYRUS_STATE = 0x40FA

FLAG_HIDE_CYRUS_CINDER_RIFT = 0x01AB
FLAG_HIDE_SPEAR_PILLAR_RIVAL = 0x01C5
FLAG_HIDE_SPEAR_PILLAR_CYRUS = 0x01CA
FLAG_HIDE_EVERSPRING_RIVAL = 717
FLAG_HIDE_CINDER_RIFT_RIVAL = 718
TOTEM_FLAGS = tuple(range(2304, 2312))


def find_player_map_object(raw: bytes | bytearray, base: int) -> int:
    matches: list[int] = []
    table = base + FIELD_OVERWORLD_SAVE_OFFSET
    for index in range(MAP_OBJECT_SAVE_COUNT):
        offset = table + index * MAP_OBJECT_SAVE_SIZE
        status = struct.unpack_from("<I", raw, offset)[0]
        local_id = raw[offset + 0x08]
        movement_type = raw[offset + 0x09]
        if status & 1 and local_id == 0xFF and movement_type == 1:
            matches.append(offset)
    if len(matches) != 1:
        relative = [f"0x{offset - base:05X}" for offset in matches]
        raise AssertionError(
            "expected exactly one active player MapObjectSave record; "
            f"found {len(matches)} at {relative}"
        )
    return matches[0]


def set_location(
    raw: bytearray,
    base: int,
    map_id: int,
    x: int,
    z: int,
    face: int = 0,
    y: int = 0,
    height_fx32: int | None = None,
) -> int:
    struct.pack_into("<iiiii", raw, base + FIELD_PLAYER_STATE_OFFSET, map_id, -1, x, z, face)
    object_offset = find_player_map_object(raw, base)
    struct.pack_into("<bbb", raw, object_offset + 0x0C, face, face, face)
    struct.pack_into("<hhhhhh", raw, object_offset + 0x20, x, y, z, x, y, z)
    if height_fx32 is None:
        height_fx32 = (y << 3) * (1 << 12)
    struct.pack_into("<i", raw, object_offset + 0x2C, height_fx32)
    return object_offset


def set_var(raw: bytearray, base: int, var_id: int, value: int) -> None:
    index = var_id - VAR_ID_BASE
    if not 0 <= index < NUM_VARS:
        raise ValueError(f"var 0x{var_id:04X} outside save range")
    p16(raw, base + VARS_FLAGS_OFFSET + index * 2, value)


def get_var(raw: bytearray, base: int, var_id: int) -> int:
    return u16(raw, base + VARS_FLAGS_OFFSET + (var_id - VAR_ID_BASE) * 2)


def set_flag(raw: bytearray, base: int, flag_id: int, value: bool) -> None:
    offset = base + FLAGS_OFFSET + flag_id // 8
    mask = 1 << (flag_id % 8)
    if value:
        raw[offset] |= mask
    else:
        raw[offset] &= ~mask


def get_flag(raw: bytearray, base: int, flag_id: int) -> bool:
    offset = base + FLAGS_OFFSET + flag_id // 8
    return bool(raw[offset] & (1 << (flag_id % 8)))


def refresh(raw: bytearray, base: int) -> None:
    footer = base + GENERAL_SIZE - MAIN_FOOTER_SIZE
    p16(raw, footer + 18, crc16_ccitt(raw[base:footer]))
    if not general_block_valid(raw, base):
        raise AssertionError(f"partition {base // PARTITION_SIZE}: CRC refresh failed")


def build_fixture(source: bytes, spec: dict[str, object]) -> tuple[bytes, list[dict[str, object]]]:
    raw = bytearray(source)
    evidence: list[dict[str, object]] = []
    for partition in (0, 1):
        base = partition * PARTITION_SIZE
        if not general_block_valid(raw, base):
            raise ValueError(f"partition {partition} has an invalid general block")
        object_offset = set_location(
            raw,
            base,
            int(spec["map_id"]),
            int(spec["x"]),
            int(spec["z"]),
            int(spec.get("face", 0)),
            int(spec.get("y", 0)),
            int(spec["height_fx32"]) if "height_fx32" in spec else None,
        )
        for var_id, value in spec.get("vars", {}).items():
            set_var(raw, base, int(var_id), int(value))
        for flag_id, value in spec.get("flags", {}).items():
            set_flag(raw, base, int(flag_id), bool(value))
        refresh(raw, base)

        map_id, warp_id, x, z, face = struct.unpack_from("<iiiii", raw, base + FIELD_PLAYER_STATE_OFFSET)
        directions = struct.unpack_from("<bbb", raw, object_offset + 0x0C)
        coordinates = struct.unpack_from("<hhhhhh", raw, object_offset + 0x20)
        height_fx32 = struct.unpack_from("<i", raw, object_offset + 0x2C)[0]
        expected_coordinates = (
            int(spec["x"]),
            int(spec.get("y", 0)),
            int(spec["z"]),
            int(spec["x"]),
            int(spec.get("y", 0)),
            int(spec["z"]),
        )
        if coordinates != expected_coordinates:
            raise AssertionError(f"partition {partition}: persisted coordinates did not round-trip")
        expected_height_fx32 = int(spec.get("height_fx32", (int(spec.get("y", 0)) << 3) * (1 << 12)))
        if height_fx32 != expected_height_fx32:
            raise AssertionError(
                f"partition {partition}: height {height_fx32} != expected {expected_height_fx32}"
            )
        evidence.append(
            {
                "partition": partition,
                "map_id": map_id,
                "warp_id": warp_id,
                "x": x,
                "z": z,
                "face": face,
                "map_object_offset": f"0x{object_offset - base:05X}",
                "directions": directions,
                "coordinates": coordinates,
                "height_fx32": height_fx32,
                "vars": {f"0x{int(var_id):04X}": get_var(raw, base, int(var_id)) for var_id in spec.get("vars", {})},
                "flags": {f"0x{int(flag_id):04X}": get_flag(raw, base, int(flag_id)) for flag_id in spec.get("flags", {})},
                "crc_valid": general_block_valid(raw, base),
            }
        )
    return bytes(raw), evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    source = args.source.read_bytes()
    if len(source) != 0x80000:
        raise SystemExit(f"expected 524288-byte raw save, got {len(source)}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    common_spear_flags = {
        FLAG_HIDE_SPEAR_PILLAR_CYRUS: False,
        FLAG_HIDE_SPEAR_PILLAR_RIVAL: False,
    }
    specs: dict[str, dict[str, object]] = {
        "act1_cyrus": {
            "map_id": MAP_MT_CORONET_1F_SOUTH,
            "x": 14,
            "z": 24,
            "face": 0,
            "vars": {
                VAR_CINDER_RIFT_VANILLA_STATE: 0,
                VAR_CINDER_RIFT_CYRUS_STATE: 0,
                VAR_CINDER_RIFT_RIVAL_STATE: 0,
            },
            "flags": {FLAG_HIDE_CYRUS_CINDER_RIFT: False, FLAG_HIDE_CINDER_RIFT_RIVAL: False},
        },
        "act1_rival": {
            "map_id": MAP_MT_CORONET_1F_SOUTH,
            "x": 25,
            "z": 8,
            "face": 0,
            # BDHC plate 9 at tiles (25, 7-8): 48.0 world units.
            "height_fx32": 196608,
            "vars": {
                VAR_CINDER_RIFT_VANILLA_STATE: 1,
                VAR_CINDER_RIFT_CYRUS_STATE: 1,
                VAR_CINDER_RIFT_RIVAL_STATE: 1,
            },
            "flags": {FLAG_HIDE_CYRUS_CINDER_RIFT: True, FLAG_HIDE_CINDER_RIFT_RIVAL: False},
        },
        "act2_everspring": {
            "map_id": MAP_ROUTE_218,
            # Approach the relocated story trigger from proven vanilla ground.
            "x": 88,
            "z": 756,
            "face": 0,
            "vars": {VAR_EVERSPRING_STATE: 0},
            "flags": {FLAG_HIDE_EVERSPRING_RIVAL: False},
        },
        "act3_blocked": {
            "map_id": MAP_SPEAR_PILLAR,
            "x": 31,
            "z": 47,
            "face": 1,
            # MAP_377 BDHC plate 0: 48.0 world units.
            "height_fx32": 196608,
            "vars": {VAR_SPEAR_PILLAR_STATE: 0},
            "flags": {**common_spear_flags, **{flag_id: False for flag_id in TOTEM_FLAGS}},
        },
        "act3_climax": {
            "map_id": MAP_SPEAR_PILLAR,
            "x": 31,
            "z": 33,
            "face": 0,
            # MAP_377 BDHC plate 0: 48.0 world units.
            "height_fx32": 196608,
            "vars": {VAR_SPEAR_PILLAR_STATE: 1},
            "flags": {**common_spear_flags, **{flag_id: True for flag_id in TOTEM_FLAGS}},
        },
    }

    manifest: dict[str, object] = {"source": str(args.source), "fixtures": {}}
    for name, spec in specs.items():
        payload, evidence = build_fixture(source, spec)
        output = args.output_dir / f"{name}.sav"
        output.write_bytes(payload)
        manifest["fixtures"][name] = {"path": str(output), "spec": spec, "partitions": evidence}

    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

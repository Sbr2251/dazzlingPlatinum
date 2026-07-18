#!/usr/bin/env python3
"""Assert species-specific Totem outcome flags in the active Platinum save partition."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from platinum_save_utils import (
    GENERAL_SIZE,
    MAIN_FOOTER_SIZE,
    PARTITION_SIZE,
    general_block_valid,
)
from inspect_totem_save_flags import flag_is_set

SPECIES_INDEX = {
    "hitmonlee": 0,
    "vespiquen": 1,
    "skarmory": 2,
    "lapras": 3,
    "spiritomb": 4,
    "aggron": 5,
    "mamoswine": 6,
    "kingdra": 7,
}


def partition_counters(raw: bytes, partition: int) -> tuple[int, int]:
    footer = partition * PARTITION_SIZE + GENERAL_SIZE - MAIN_FOOTER_SIZE
    return struct.unpack_from("<II", raw, footer)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("save", type=Path)
    parser.add_argument("species", choices=tuple(SPECIES_INDEX))
    parser.add_argument("expected", choices=("set", "clear"))
    args = parser.parse_args()

    payload = args.save.read_bytes()
    if len(payload) not in (0x80000, 0x80000 + 122):
        raise SystemExit(f"Unexpected save size: {len(payload)}")
    raw = payload[:0x80000]

    candidates: list[tuple[int, int, int]] = []
    for partition in (0, 1):
        base = partition * PARTITION_SIZE
        if not general_block_valid(raw, base):
            continue
        save_counter, block_counter = partition_counters(raw, partition)
        candidates.append((save_counter, block_counter, partition))
    if not candidates:
        raise SystemExit("No valid general save partition")

    save_counter, block_counter, active = max(candidates)
    index = SPECIES_INDEX[args.species]
    defeated_flag = 0x0900 + index
    hide_flag = 0x0908 + index
    defeated = flag_is_set(raw, active, defeated_flag)
    hidden = flag_is_set(raw, active, hide_flag)
    expected_value = args.expected == "set"

    print(f"file={args.save}")
    print(f"species={args.species.upper()}")
    print(f"active_partition={active}")
    print(f"save_counter={save_counter}")
    print(f"block_counter={block_counter}")
    print(f"defeated_flag=0x{defeated_flag:04X} value={int(defeated)}")
    print(f"hide_flag=0x{hide_flag:04X} value={int(hidden)}")
    print(f"expected={args.expected}")

    if defeated != expected_value or hidden != expected_value:
        print("result=FAIL")
        return 1
    print("result=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

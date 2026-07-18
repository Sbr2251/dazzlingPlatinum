#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from platinum_save_utils import PARTITION_SIZE, general_block_valid

VARS_FLAGS_OFFSET = 0x0DAC
NUM_VARS = 0x120
FLAGS_OFFSET = VARS_FLAGS_OFFSET + NUM_VARS * 2

STORY_FLAGS = {
    0x0096: "FLAG_UNK_0x0096_ROUTE_223_JASMINE_HIDE",
    0x00BA: "FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY",
    0x00E3: "FLAG_TRAVELED_WITH_CHERYL",
    0x00E5: "FLAG_TRAVELED_WITH_RILEY",
}

TOTEM_FLAGS = {
    0x0900: "FLAG_TOTEM_HITMONLEE_DEFEATED",
    0x0901: "FLAG_TOTEM_VESPIQUEN_DEFEATED",
    0x0902: "FLAG_TOTEM_SKARMORY_DEFEATED",
    0x0903: "FLAG_TOTEM_LAPRAS_DEFEATED",
    0x0904: "FLAG_TOTEM_SPIRITOMB_DEFEATED",
    0x0905: "FLAG_TOTEM_AGGRON_DEFEATED",
    0x0906: "FLAG_TOTEM_MAMOSWINE_DEFEATED",
    0x0907: "FLAG_TOTEM_KINGDRA_DEFEATED",
    0x0908: "FLAG_HIDE_TOTEM_HITMONLEE",
    0x0909: "FLAG_HIDE_TOTEM_VESPIQUEN",
    0x090A: "FLAG_HIDE_TOTEM_SKARMORY",
    0x090B: "FLAG_HIDE_TOTEM_LAPRAS",
    0x090C: "FLAG_HIDE_TOTEM_SPIRITOMB",
    0x090D: "FLAG_HIDE_TOTEM_AGGRON",
    0x090E: "FLAG_HIDE_TOTEM_MAMOSWINE",
    0x090F: "FLAG_HIDE_TOTEM_KINGDRA",
}


def flag_is_set(raw: bytes, partition: int, flag_id: int) -> bool:
    byte_offset = partition * PARTITION_SIZE + FLAGS_OFFSET + flag_id // 8
    mask = 1 << (flag_id % 8)
    return bool(raw[byte_offset] & mask)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Totem, Cheryl, and Riley flags in a Platinum save.")
    parser.add_argument("save", type=Path)
    args = parser.parse_args()

    payload = args.save.read_bytes()
    if len(payload) not in (0x80000, 0x80000 + 122):
        raise SystemExit(f"Unexpected save size: {len(payload)}")
    raw = payload[:0x80000]

    print(f"file={args.save}")
    print(f"vars_flags_offset=0x{VARS_FLAGS_OFFSET:04X}")
    print(f"flags_offset=0x{FLAGS_OFFSET:04X}")
    for partition in (0, 1):
        valid = general_block_valid(raw, partition * PARTITION_SIZE)
        print(f"partition={partition} general_block_valid={str(valid).lower()}")
        if not valid:
            continue
        for flag_id, name in {**STORY_FLAGS, **TOTEM_FLAGS}.items():
            print(f"  0x{flag_id:04X} {name}={int(flag_is_set(raw, partition, flag_id))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

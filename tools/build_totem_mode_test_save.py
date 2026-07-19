#!/usr/bin/env python3
"""Build a deterministic save for Totem battle turn-lifecycle validation.

The output keeps the source save's world position and lead species, but makes
that lead a durable level-100 battler. Move slot 1 is Splash, allowing a turn
to end without damaging the Totem. Move slot 2 is Aerial Ace, allowing a
controlled KO while validating ally replacement and summon-cap behavior.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from platinum_save_utils import (
    GENERAL_SIZE,
    MAIN_FOOTER_SIZE,
    PARTY_COUNT_OFFSET,
    PARTY_OFFSET,
    PARTITION_SIZE,
    PK4_PARTY_SIZE,
    add16,
    crc16_ccitt,
    decrypt_pk4,
    encrypt_pk4,
    general_block_valid,
    p16,
    u16,
)

MOVE_SPLASH = 150
MOVE_AERIAL_ACE = 332
MOVE_OFFSETS = (0x28, 0x2A, 0x2C, 0x2E)
PP_OFFSETS = (0x30, 0x31, 0x32, 0x33)
PP_UP_OFFSETS = (0x34, 0x35, 0x36, 0x37)
STATUS_OFFSET = 0x88
LEVEL_OFFSET = 0x8C
CURRENT_HP_OFFSET = 0x8E
MAX_HP_OFFSET = 0x90
ATTACK_OFFSET = 0x92
DEFENSE_OFFSET = 0x94
SPEED_OFFSET = 0x96
SP_ATTACK_OFFSET = 0x98
SP_DEFENSE_OFFSET = 0x9A
TEST_LEVEL = 100
TEST_STAT = 999
TEST_MOVES = (MOVE_SPLASH, MOVE_AERIAL_ACE, MOVE_SPLASH, MOVE_SPLASH)
TEST_PP = (40, 20, 40, 40)

TOTEM_OUTCOME_FLAGS_BY_SPECIES = {
    "hitmonlee": (0x0900, 0x0908),
    "vespiquen": (0x0901, 0x0909),
    "skarmory": (0x0902, 0x090A),
    "lapras": (0x0903, 0x090B),
    "spiritomb": (0x0904, 0x090C),
    "aggron": (0x0905, 0x090D),
    "mamoswine": (0x0906, 0x090E),
    "kingdra": (0x0907, 0x090F),
}


def write_u32(raw: bytearray, offset: int, value: int) -> None:
    raw[offset : offset + 4] = int(value).to_bytes(4, "little")


def clear_outcome_flags(
    raw: bytearray,
    base: int,
    species: str,
    vars_flags_rel: int,
) -> dict[str, int]:
    defeated_flag, hide_flag = TOTEM_OUTCOME_FLAGS_BY_SPECIES[species]

    for flag_id in (defeated_flag, hide_flag):
        byte_offset = base + vars_flags_rel + (flag_id >> 3)
        raw[byte_offset] &= ~(1 << (flag_id & 7))

    return {"defeated_flag": defeated_flag, "hide_flag": hide_flag}


def patch_partition(
    raw: bytearray,
    partition: int,
    species: str,
    vars_flags_rel: int,
) -> dict[str, object]:
    base = partition * PARTITION_SIZE
    if not general_block_valid(raw, base):
        return {"partition": partition, "status": "skipped invalid general block"}

    original_count = raw[base + PARTY_COUNT_OFFSET]
    if not 1 <= original_count <= 6:
        raise ValueError(f"partition {partition}: invalid party count {original_count}")

    offset = base + PARTY_OFFSET
    decrypted = decrypt_pk4(bytes(raw[offset : offset + PK4_PARTY_SIZE]))
    lead_species = u16(decrypted, 0x08)
    stored_checksum = u16(decrypted, 0x06)
    calculated_checksum = add16(decrypted[0x08:0x88])
    if stored_checksum != calculated_checksum:
        raise ValueError(
            f"partition {partition}: lead PK4 checksum mismatch "
            f"stored={stored_checksum:04X} calculated={calculated_checksum:04X}"
        )

    for move_offset, move in zip(MOVE_OFFSETS, TEST_MOVES, strict=True):
        p16(decrypted, move_offset, move)
    for pp_offset, pp in zip(PP_OFFSETS, TEST_PP, strict=True):
        decrypted[pp_offset] = pp
    for pp_up_offset in PP_UP_OFFSETS:
        decrypted[pp_up_offset] = 0

    write_u32(decrypted, STATUS_OFFSET, 0)
    decrypted[LEVEL_OFFSET] = TEST_LEVEL
    for stat_offset in (
        CURRENT_HP_OFFSET,
        MAX_HP_OFFSET,
        ATTACK_OFFSET,
        DEFENSE_OFFSET,
        SPEED_OFFSET,
        SP_ATTACK_OFFSET,
        SP_DEFENSE_OFFSET,
    ):
        p16(decrypted, stat_offset, TEST_STAT)

    p16(decrypted, 0x06, add16(decrypted[0x08:0x88]))
    encrypted = encrypt_pk4(decrypted)
    roundtrip = decrypt_pk4(encrypted)
    if u16(roundtrip, 0x08) != lead_species:
        raise AssertionError(f"partition {partition}: species changed during round-trip")
    if tuple(u16(roundtrip, move_offset) for move_offset in MOVE_OFFSETS) != TEST_MOVES:
        raise AssertionError(f"partition {partition}: move round-trip failed")
    if roundtrip[LEVEL_OFFSET] != TEST_LEVEL:
        raise AssertionError(f"partition {partition}: level round-trip failed")
    if any(
        u16(roundtrip, stat_offset) != TEST_STAT
        for stat_offset in (
            CURRENT_HP_OFFSET,
            MAX_HP_OFFSET,
            ATTACK_OFFSET,
            DEFENSE_OFFSET,
            SPEED_OFFSET,
            SP_ATTACK_OFFSET,
            SP_DEFENSE_OFFSET,
        )
    ):
        raise AssertionError(f"partition {partition}: stat round-trip failed")
    if u16(roundtrip, 0x06) != add16(roundtrip[0x08:0x88]):
        raise AssertionError(f"partition {partition}: PK4 checksum refresh failed")

    raw[offset : offset + PK4_PARTY_SIZE] = encrypted
    raw[base + PARTY_COUNT_OFFSET] = 1
    flag_report = clear_outcome_flags(raw, base, species, vars_flags_rel)

    footer = base + GENERAL_SIZE - MAIN_FOOTER_SIZE
    p16(raw, footer + 18, crc16_ccitt(raw[base:footer]))
    if not general_block_valid(raw, base):
        raise AssertionError(f"partition {partition}: general-block CRC refresh failed")

    return {
        "partition": partition,
        "status": "patched",
        "party_count_before": original_count,
        "party_count_after": 1,
        "lead_species_id": lead_species,
        "level": TEST_LEVEL,
        "hp_and_stats": TEST_STAT,
        "move_ids": list(TEST_MOVES),
        **flag_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--species",
        choices=sorted(TOTEM_OUTCOME_FLAGS_BY_SPECIES),
        default="hitmonlee",
        help="Totem outcome flags to clear in the generated test save",
    )
    parser.add_argument(
        "--vars-flags-rel",
        type=lambda value: int(value, 0),
        default=0xFEC,
        help="Relative start of the flags bit array in the general save block (default: 0x0FEC)",
    )
    args = parser.parse_args()

    source = args.source.read_bytes()
    if len(source) not in (0x80000, 0x80000 + 122):
        raise SystemExit(f"Unexpected save size: {len(source)}")
    footer = source[0x80000:]
    raw = bytearray(source[:0x80000])

    reports = [
        patch_partition(raw, partition, args.species, args.vars_flags_rel)
        for partition in (0, 1)
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(bytes(raw) + footer)

    print(
        json.dumps(
            {
                "source": str(args.source.resolve()),
                "output": str(args.output.resolve()),
                "size": args.output.stat().st_size,
                "species": args.species,
                "partitions": reports,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

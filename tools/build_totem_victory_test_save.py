#!/usr/bin/env python3
"""Build a checksum-valid one-Pokémon Platinum save for deterministic Totem victories."""

from __future__ import annotations

import argparse
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

MOVE_AERIAL_ACE = 332
MOVE_OFFSETS = (0x28, 0x2A, 0x2C, 0x2E)
PP_OFFSETS = (0x30, 0x31, 0x32, 0x33)
PP_UP_OFFSETS = (0x34, 0x35, 0x36, 0x37)
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


def patch_partition(raw: bytearray, partition: int) -> str:
    base = partition * PARTITION_SIZE
    if not general_block_valid(raw, base):
        return f"partition {partition}: skipped invalid general block"

    original_count = raw[base + PARTY_COUNT_OFFSET]
    if not 1 <= original_count <= 6:
        raise ValueError(f"partition {partition}: invalid party count {original_count}")

    offset = base + PARTY_OFFSET
    decrypted = decrypt_pk4(bytes(raw[offset : offset + PK4_PARTY_SIZE]))
    species = u16(decrypted, 0x08)
    stored_checksum = u16(decrypted, 0x06)
    calculated_checksum = add16(decrypted[0x08:0x88])
    if stored_checksum != calculated_checksum:
        raise ValueError(
            f"partition {partition}: lead PK4 checksum mismatch "
            f"stored={stored_checksum:04X} calculated={calculated_checksum:04X}"
        )

    for move_offset in MOVE_OFFSETS:
        p16(decrypted, move_offset, MOVE_AERIAL_ACE)
    for pp_offset in PP_OFFSETS:
        decrypted[pp_offset] = 20
    for pp_up_offset in PP_UP_OFFSETS:
        decrypted[pp_up_offset] = 0

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
    if u16(roundtrip, 0x08) != species:
        raise AssertionError(f"partition {partition}: species changed during round-trip")
    if any(u16(roundtrip, move_offset) != MOVE_AERIAL_ACE for move_offset in MOVE_OFFSETS):
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
    footer = base + GENERAL_SIZE - MAIN_FOOTER_SIZE
    p16(raw, footer + 18, crc16_ccitt(raw[base:footer]))
    if not general_block_valid(raw, base):
        raise AssertionError(f"partition {partition}: general-block CRC refresh failed")

    return (
        f"partition {partition}: party_count {original_count}->1 species={species} "
        f"level={TEST_LEVEL} hp={TEST_STAT}/{TEST_STAT} stats={TEST_STAT} "
        f"moves={MOVE_AERIAL_ACE},{MOVE_AERIAL_ACE},{MOVE_AERIAL_ACE},{MOVE_AERIAL_ACE}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a checksum-valid one-Pokémon Platinum save for deterministic Totem victory testing."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    source = args.source.read_bytes()
    if len(source) not in (0x80000, 0x80000 + 122):
        raise SystemExit(f"Unexpected save size: {len(source)}")
    footer = source[0x80000:]
    raw = bytearray(source[:0x80000])

    reports = [patch_partition(raw, partition) for partition in (0, 1)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(bytes(raw) + footer)
    for report in reports:
        print(report)
    print(f"output={args.output} size={args.output.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

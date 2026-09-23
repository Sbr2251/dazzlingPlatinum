#!/usr/bin/env python3
"""Shared helpers for Platinum save partitions and encrypted party records."""

from __future__ import annotations

import struct

PARTITION_SIZE = 0x40000
GENERAL_SIZE = 0xCF2C
MAIN_FOOTER_SIZE = 0x14
PARTY_COUNT_OFFSET = 0x9C
PARTY_OFFSET = 0xA0
PK4_PARTY_SIZE = 236
PK4_STORED_SIZE = 136
PK4_BLOCK_SIZE = 32
SECTOR_SIGNATURE = 0x20060623

BLOCK_POSITION = (
    0, 1, 2, 3, 0, 1, 3, 2, 0, 2, 1, 3, 0, 3, 1, 2,
    0, 2, 3, 1, 0, 3, 2, 1, 1, 0, 2, 3, 1, 0, 3, 2,
    2, 0, 1, 3, 3, 0, 1, 2, 2, 0, 3, 1, 3, 0, 2, 1,
    1, 2, 0, 3, 1, 3, 0, 2, 2, 1, 0, 3, 3, 1, 0, 2,
    2, 3, 0, 1, 3, 2, 0, 1, 1, 2, 3, 0, 1, 3, 2, 0,
    2, 1, 3, 0, 3, 1, 2, 0, 2, 3, 1, 0, 3, 2, 1, 0,
    0, 1, 2, 3, 0, 1, 3, 2, 0, 2, 1, 3, 0, 3, 1, 2,
    0, 2, 3, 1, 0, 3, 2, 1, 1, 0, 2, 3, 1, 0, 3, 2,
)
BLOCK_POSITION_INVERT = (
    0, 1, 2, 4, 3, 5, 6, 7, 12, 18, 13, 19,
    8, 10, 14, 20, 16, 22, 9, 11, 15, 21, 17, 23,
    0, 1, 2, 4, 3, 5, 6, 7,
)


def u16(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def p16(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<H", data, offset, value)


def crc16_ccitt(data: bytes | bytearray) -> int:
    top = 0xFF
    bot = 0xFF
    for value in data:
        x = value ^ top
        x ^= x >> 4
        top = (bot ^ (x >> 3) ^ ((x << 4) & 0xFF)) & 0xFF
        bot = (x ^ ((x << 5) & 0xFF)) & 0xFF
    return (top << 8) | bot


def add16(data: bytes | bytearray) -> int:
    if len(data) % 2:
        raise ValueError("Add16 input must have even length")
    return sum(struct.unpack(f"<{len(data) // 2}H", data)) & 0xFFFF


def crypt_array(data: bytearray, seed: int) -> None:
    for offset in range(0, len(data), 2):
        seed = (0x41C64E6D * seed + 0x6073) & 0xFFFFFFFF
        p16(data, offset, u16(data, offset) ^ (seed >> 16))


def shuffle45(data: bytearray, sv: int) -> None:
    if sv == 0:
        return
    permutation = [0, 1, 2, 3]
    slot_of = [0, 1, 2, 3]
    desired_order = BLOCK_POSITION[sv * 4 : sv * 4 + 4]
    for index in range(3):
        desired = desired_order[index]
        swap_index = slot_of[desired]
        if swap_index == index:
            continue
        first = bytes(data[index * PK4_BLOCK_SIZE : (index + 1) * PK4_BLOCK_SIZE])
        second = bytes(data[swap_index * PK4_BLOCK_SIZE : (swap_index + 1) * PK4_BLOCK_SIZE])
        data[index * PK4_BLOCK_SIZE : (index + 1) * PK4_BLOCK_SIZE] = second
        data[swap_index * PK4_BLOCK_SIZE : (swap_index + 1) * PK4_BLOCK_SIZE] = first
        block_at_index = permutation[index]
        permutation[swap_index] = block_at_index
        slot_of[block_at_index] = swap_index


def decrypt_pk4(record: bytes) -> bytearray:
    if len(record) != PK4_PARTY_SIZE:
        raise ValueError(f"Unexpected PK4 party size: {len(record)}")
    result = bytearray(record)
    pid = u32(result, 0)
    checksum = u16(result, 6)
    shuffle_value = (pid >> 13) & 31
    core = bytearray(result[8:PK4_STORED_SIZE])
    crypt_array(core, checksum)
    shuffle45(core, shuffle_value)
    stats = bytearray(result[PK4_STORED_SIZE:])
    crypt_array(stats, pid)
    result[8:PK4_STORED_SIZE] = core
    result[PK4_STORED_SIZE:] = stats
    return result


def encrypt_pk4(record: bytearray) -> bytes:
    result = bytearray(record)
    pid = u32(result, 0)
    checksum = u16(result, 6)
    shuffle_value = BLOCK_POSITION_INVERT[(pid >> 13) & 31]
    core = bytearray(result[8:PK4_STORED_SIZE])
    shuffle45(core, shuffle_value)
    crypt_array(core, checksum)
    stats = bytearray(result[PK4_STORED_SIZE:])
    crypt_array(stats, pid)
    result[8:PK4_STORED_SIZE] = core
    result[PK4_STORED_SIZE:] = stats
    return bytes(result)


def general_block_valid(raw: bytes | bytearray, base: int) -> bool:
    footer = base + GENERAL_SIZE - MAIN_FOOTER_SIZE
    declared_size = u32(raw, footer + 8)
    signature = u32(raw, footer + 12)
    block_id = raw[footer + 16]
    saved_crc = u16(raw, footer + 18)
    calculated_crc = crc16_ccitt(raw[base:footer])
    return (
        declared_size == GENERAL_SIZE
        and signature == SECTOR_SIGNATURE
        and block_id == 0
        and saved_crc == calculated_crc
    )

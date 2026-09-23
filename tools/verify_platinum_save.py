#!/usr/bin/env python3
from __future__ import annotations

import argparse
import struct
from pathlib import Path

PARTITION_SIZE = 0x40000
GENERAL_SIZE = 0xCF2C
STORAGE_START = GENERAL_SIZE
STORAGE_SIZE = 0x121E4
MAIN_FOOTER_SIZE = 0x14
SECTOR_SIGNATURE = 0x20060623
EXTRA_BLOCKS = (
    (0, 0x20000, 0x2AC0),
    (1, 0x23000, 0x0BB0),
    (2, 0x24000, 0x1D60),
    (3, 0x26000, 0x1D60),
    (4, 0x28000, 0x1D60),
    (5, 0x2A000, 0x1D60),
)


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from('<H', data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from('<I', data, offset)[0]


def crc16_ccitt(data: bytes) -> int:
    top = 0xFF
    bot = 0xFF
    for value in data:
        x = value ^ top
        x ^= x >> 4
        top = (bot ^ (x >> 3) ^ ((x << 4) & 0xFF)) & 0xFF
        bot = (x ^ ((x << 5) & 0xFF)) & 0xFF
    return (top << 8) | bot


def main_block_report(data: bytes, name: str, offset: int, size: int, block_id: int) -> dict[str, object]:
    block = data[offset:offset + size]
    footer = size - MAIN_FOOTER_SIZE
    save_counter = u32(block, footer)
    block_counter = u32(block, footer + 4)
    declared_size = u32(block, footer + 8)
    signature = u32(block, footer + 12)
    declared_block_id = block[footer + 16]
    saved = u16(block, footer + 18)
    calc = crc16_ccitt(block[:-MAIN_FOOTER_SIZE])
    fields_valid = (
        declared_size == size
        and signature == SECTOR_SIGNATURE
        and declared_block_id == block_id
    )
    return {
        'name': name,
        'offset': offset,
        'size': size,
        'save_counter': save_counter,
        'block_counter': block_counter,
        'declared_size': declared_size,
        'signature': signature,
        'block_id': declared_block_id,
        'expected_block_id': block_id,
        'saved_crc': saved,
        'calc_crc': calc,
        'fields_valid': fields_valid,
        'valid': fields_valid and saved == calc,
    }


def extra_block_report(data: bytes, partition: int, block_id: int, offset: int, size: int) -> dict[str, object]:
    base = partition * PARTITION_SIZE
    block = data[base + offset:base + offset + size]
    footer = size - 0x10
    save_counter = u32(block, footer + 4)
    key = u32(block, 0)
    initialized = (block_id == 0 and save_counter != 0xFFFFFFFF) or (block_id != 0 and key != 0xFFFFFFFF)
    signature = u32(block, footer)
    declared_size = u32(block, footer + 8)
    declared_block_id = u16(block, footer + 12)
    calc = crc16_ccitt(block[:-2])
    saved = u16(block, size - 2)
    fields_valid = (
        signature == SECTOR_SIGNATURE
        and declared_size == size
        and declared_block_id == block_id
    )
    return {
        'name': f'p{partition}-extra-{block_id}',
        'offset': base + offset,
        'size': size,
        'signature': signature,
        'save_counter': save_counter,
        'declared_size': declared_size,
        'block_id': declared_block_id,
        'expected_block_id': block_id,
        'initialized': initialized,
        'saved_crc': saved,
        'calc_crc': calc,
        'fields_valid': fields_valid,
        'valid': (not initialized) or (fields_valid and saved == calc),
    }


def compare_counters(counter1: int, counter2: int) -> int:
    if counter1 == 0xFFFFFFFF and counter2 == 0:
        return -1
    if counter1 == 0 and counter2 == 0xFFFFFFFF:
        return 1
    return (counter1 > counter2) - (counter1 < counter2)


def compare_sectors(primary: dict[str, object], backup: dict[str, object]) -> tuple[str, int | None, int | None]:
    p_valid = bool(primary['valid'])
    b_valid = bool(backup['valid'])
    if p_valid and b_valid:
        global_diff = compare_counters(int(primary['save_counter']), int(backup['save_counter']))
        block_diff = compare_counters(int(primary['block_counter']), int(backup['block_counter']))
        if global_diff > 0 or (global_diff == 0 and block_diff >= 0):
            return 'VALID', 0, 1
        return 'VALID', 1, 0
    if p_valid:
        return 'PARTIAL_VALID', 0, None
    if b_valid:
        return 'PARTIAL_VALID', 1, None
    return 'INVALID', None, None


def native_load_result(main_reports: list[dict[str, object]]) -> str:
    normal = [main_reports[0], main_reports[2]]
    boxes = [main_reports[1], main_reports[3]]
    normal_result, curr_normal, stale_normal = compare_sectors(normal[0], normal[1])
    box_result, curr_box, stale_box = compare_sectors(boxes[0], boxes[1])

    if normal_result == 'INVALID' and box_result == 'INVALID':
        return 'EMPTY'
    if normal_result == 'INVALID' or box_result == 'INVALID':
        return 'ERROR'
    assert curr_normal is not None and curr_box is not None

    normal_counter = int(normal[curr_normal]['save_counter'])
    box_counter = int(boxes[curr_box]['save_counter'])
    if normal_result == 'VALID' and box_result == 'VALID':
        return 'OK' if normal_counter == box_counter else 'CORRUPT'
    if normal_result == 'PARTIAL_VALID' and box_result == 'VALID':
        if normal_counter == box_counter:
            return 'CORRUPT'
        if stale_box is not None and normal_counter == int(boxes[stale_box]['save_counter']):
            return 'CORRUPT'
        return 'ERROR'
    if normal_result == 'VALID' and box_result == 'PARTIAL_VALID':
        return 'OK' if normal_counter == box_counter else 'CORRUPT'
    return 'OK' if curr_normal == curr_box else 'CORRUPT'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('save', type=Path)
    args = parser.parse_args()
    raw = args.save.read_bytes()
    if len(raw) not in (0x80000, 0x80000 + 122):
        raise SystemExit(f'Unexpected save length: {len(raw)}')
    data = raw[:0x80000]

    main_reports: list[dict[str, object]] = []
    extra_reports: list[dict[str, object]] = []
    for partition in (0, 1):
        base = partition * PARTITION_SIZE
        main_reports.append(main_block_report(data, f'p{partition}-general', base, GENERAL_SIZE, 0))
        main_reports.append(main_block_report(data, f'p{partition}-storage', base + STORAGE_START, STORAGE_SIZE, 1))
        for block_id, offset, size in EXTRA_BLOCKS:
            extra_reports.append(extra_block_report(data, partition, block_id, offset, size))

    print(f'file={args.save}')
    print(f'length={len(raw)} raw_length={len(data)}')
    all_valid = True
    for report in main_reports:
        valid = bool(report['valid'])
        all_valid &= valid
        state = 'VALID' if valid else 'INVALID'
        print(
            f"{report['name']}: {state} "
            f"saved={report['saved_crc']:04X} calc={report['calc_crc']:04X} "
            f"signature={report['signature']:08X} save_counter={report['save_counter']} "
            f"block_counter={report['block_counter']} declared_size={report['declared_size']} "
            f"block_id={report['block_id']} expected_block_id={report['expected_block_id']}"
        )
    for report in extra_reports:
        valid = bool(report['valid'])
        all_valid &= valid
        state = 'VALID' if valid else 'INVALID'
        print(
            f"{report['name']}: {state} initialized={report['initialized']} "
            f"saved={report['saved_crc']:04X} calc={report['calc_crc']:04X} "
            f"signature={report['signature']:08X} save_counter={report['save_counter']} "
            f"declared_size={report['declared_size']} block_id={report['block_id']}"
        )
    load_result = native_load_result(main_reports)
    print(f'native_main_load_result={load_result}')
    print(f'all_checked_blocks_valid={all_valid}')
    return 0 if load_result in ('OK', 'CORRUPT') else 1


if __name__ == '__main__':
    raise SystemExit(main())

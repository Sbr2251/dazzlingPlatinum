#!/usr/bin/env python3
"""Stores each distinct member of a NARC once, pointing duplicate FAT entries at the first copy.

Usage: dedupe_narc.py <narc>  (rewrites the file in place)

narc.c reads every member through its FAT start/end pair, so members sharing
bytes load exactly as before. Member indices and count are unchanged.
"""
import struct
import sys


def dedupe(data):
    assert data[:4] == b'NARC'
    header_size = struct.unpack_from('<H', data, 12)[0]
    fat = header_size
    assert data[fat:fat + 4] == b'BTAF'
    fat_size, count = struct.unpack_from('<IH', data, fat + 4)
    fnt = fat + fat_size
    assert data[fnt:fnt + 4] == b'BTNF'
    img = fnt + struct.unpack_from('<I', data, fnt + 4)[0]
    assert data[img:img + 4] == b'GMIF'
    base = img + 8

    out = bytearray(data[:img + 8])
    blob = bytearray()
    offsets = {}
    for i in range(count):
        start, end = struct.unpack_from('<II', data, fat + 12 + 8 * i)
        member = bytes(data[base + start:base + end])
        if member not in offsets:
            offsets[member] = len(blob)
            blob += member
            blob += b'\xff' * (-len(blob) % 4)
        new_start = offsets[member]
        struct.pack_into('<II', out, fat + 12 + 8 * i, new_start, new_start + len(member))

    out += blob
    struct.pack_into('<I', out, img + 4, 8 + len(blob))
    struct.pack_into('<I', out, 8, len(out))
    return bytes(out)


def main():
    path = sys.argv[1]
    with open(path, 'rb') as f:
        data = f.read()
    with open(path, 'wb') as f:
        f.write(dedupe(data))


if __name__ == '__main__':
    main()

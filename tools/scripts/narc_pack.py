#!/usr/bin/env python3
"""Reads and rewrites the members of a packed NARC, storing each distinct member once.

Usage: narc_pack.py <narc>  (dedupes the file in place)

Duplicate members share bytes: their FAT entries point at the first copy. narc.c
reads every member through its own FAT start/end pair, so members sharing bytes
load exactly as before. Member indices and count are unchanged.
"""
import struct
import sys


def _layout(data):
    assert data[:4] == b'NARC'
    fat = struct.unpack_from('<H', data, 12)[0]
    assert data[fat:fat + 4] == b'BTAF'
    fat_size, count = struct.unpack_from('<IH', data, fat + 4)
    fnt = fat + fat_size
    assert data[fnt:fnt + 4] == b'BTNF'
    img = fnt + struct.unpack_from('<I', data, fnt + 4)[0]
    assert data[img:img + 4] == b'GMIF'
    return fat, count, img


def read_members(data):
    fat, count, img = _layout(data)
    members = []
    for i in range(count):
        start, end = struct.unpack_from('<II', data, fat + 12 + 8 * i)
        members.append(bytes(data[img + 8 + start:img + 8 + end]))
    return members


def pack(data, members):
    """Rebuilds data (a NARC) around a new list of members, one per existing FAT entry."""
    fat, count, img = _layout(data)
    assert len(members) == count
    out = bytearray(data[:img + 8])
    blob = bytearray()
    offsets = {}
    for i, member in enumerate(members):
        if member not in offsets:
            offsets[member] = len(blob)
            blob += member
            blob += b'\xff' * (-len(blob) % 4)
        start = offsets[member]
        struct.pack_into('<II', out, fat + 12 + 8 * i, start, start + len(member))

    out += blob
    struct.pack_into('<I', out, img + 4, 8 + len(blob))
    struct.pack_into('<I', out, 8, len(out))
    return bytes(out)


def dedupe(data):
    return pack(data, read_members(data))


def main():
    path = sys.argv[1]
    with open(path, 'rb') as f:
        data = f.read()
    with open(path, 'wb') as f:
        f.write(dedupe(data))


if __name__ == '__main__':
    main()

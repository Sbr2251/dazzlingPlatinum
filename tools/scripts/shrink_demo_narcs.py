#!/usr/bin/env python3
"""Shrinks the prebuilt credits and opening-movie NARCs in place. Safe to re-run.

Usage: python3 tools/scripts/shrink_demo_narcs.py

graphic/ending.narc: LZ-compresses the credits slideshow images, which
ov99_021D439C loads with compressed=TRUE.
demo/title/op_demo.narc: empties the members no code loads.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'giratina_title'))

import lz10  # noqa: E402
import narc_pack  # noqa: E402

ENDING = 'res/prebuilt/graphic/ending.narc'
# NCGR tiles in the Unk_ov99_021D5394/52F4/5274/52B4 tables of src/overlay099/ov99_021D4134.c
ENDING_SLIDESHOW_TILES = [*range(38, 48), *range(58, 68), *range(87, 91), *range(95, 99)]

OP_DEMO = 'res/prebuilt/demo/title/op_demo.narc'
# Not loaded by the title screen or src/game_opening
OP_DEMO_UNUSED = [*range(0, 3), *range(7, 12), *range(28, 46)]


def rewrite(path, edit):
    path = os.path.join(ROOT, path)
    with open(path, 'rb') as f:
        data = f.read()
    members = narc_pack.read_members(data)
    edit(members)
    out = narc_pack.pack(data, members)
    with open(path, 'wb') as f:
        f.write(out)
    print(f'{os.path.relpath(path, ROOT)}: {len(data)} -> {len(out)} bytes')


def compress_slideshow(members):
    for i in ENDING_SLIDESHOW_TILES:
        if members[i][:4] != b'RGCN':
            continue  # already compressed
        packed = lz10.compress(members[i])
        assert lz10.decompress(packed) == members[i]
        members[i] = packed


def empty_unused(members):
    for i in OP_DEMO_UNUSED:
        members[i] = b''


def main():
    rewrite(ENDING, compress_slideshow)
    rewrite(OP_DEMO, empty_unused)


if __name__ == '__main__':
    main()

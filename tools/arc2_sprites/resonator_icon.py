#!/usr/bin/env python3
"""Resonator bag icon: the Portal Reader with a glowing violet Calm Shard fitted.

    python3 tools/arc2_sprites/resonator_icon.py           # write resonator.png / resonator.pal
    python3 tools/arc2_sprites/resonator_icon.py --check   # fail if stale

Built from res/graphics/item_icons/portal_reader.png (Arc 1's own icon): the Reader's body, screen and
antenna are kept; the white side panel is replaced by a grey socket on the Reader's shoulder holding
an upright Calm Shard, white-hot at the core, with violet glow pixels around it, and the screen lit a
brighter violet. Same 16-colour palette as the Reader, with index 15 (unused there) as the core glow.
Output is a 32x32 4-bit PNG plus a 256-entry JASC-PAL with CRLF line endings, as CLAUDE.md requires.
Pure Python (writes the PNG itself), deterministic.
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ICONS = REPO / "res/graphics/item_icons"

PALETTE = [
    (180, 180, 180),  # 0 transparent
    (49, 49, 49),     # 1 outline
    (230, 230, 230),  # 2 light grey
    (176, 104, 232),  # 3 violet
    (238, 190, 255),  # 4 pale violet
    (139, 139, 139),  # 5 grey
    (82, 82, 82),     # 6 dark grey
    (172, 172, 172),  # 7 mid grey
    (98, 57, 148),    # 8 deep violet
    (123, 90, 213),   # 9 violet shade
    (172, 139, 246),  # A lavender
    (255, 255, 255),  # B white
    (206, 160, 246),  # C glow violet
    (213, 180, 57),   # D gold (unused here)
    (65, 65, 65),     # E dark outline
    (250, 236, 255),  # F core glow (new; unused in the Reader's icon)
]

# 32x32, one hex digit per pixel ('.' = 0). Rows 0-22 carry the art; the rest is blank.
GRID = """
...................C............
..........11......88..C.........
.........1441....84A8...........
.........1561...84FA98..........
.........1751..84FFA398.C.......
.......111751..84FA3398.........
......1BB1761.84FFA3398.........
.....1B2B6761.84FA33398.C.......
....1B2B66EE1.84AA33998.........
...1B2B6ECC6511722557E1.........
..1B2B6ECC4CE5116557E1..........
.1B2B6ECC4B4CE511661............
.1B26ECC4BB4C3E511..............
.1B26CC4BBBB4C3E5611............
.1B26C4ABBBBA4C3E561............
.1B2B6C4ABBA4C3E561.............
.15B2B6C4AA4C381111.............
..15B2B6C44C381.................
...15B2B6CC381..................
....15B2B681....................
.....15BBB1.....................
......15661.....................
.......1111.....................
"""


def pixels() -> list[list[int]]:
    rows = [r for r in GRID.strip("\n").split("\n")]
    out = []
    for r in rows:
        if len(r) != 32:
            raise ValueError(f"row is {len(r)} wide: {r!r}")
        out.append([0 if c == "." else int(c, 16) for c in r])
    while len(out) < 32:
        out.append([0] * 32)
    return out


def png_bytes(px: list[list[int]]) -> bytes:
    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes((row[x] << 4) | row[x + 1] for x in range(0, 32, 2)) for row in px)
    ihdr = struct.pack(">IIBBBBB", 32, 32, 4, 3, 0, 0, 0)
    plte = b"".join(bytes(c) for c in PALETTE)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"PLTE", plte)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def pal_bytes() -> bytes:
    lines = ["JASC-PAL", "0100", "256"] + [f"{r} {g} {b}" for r, g, b in PALETTE] + ["0 0 0"] * 240
    return ("\r\n".join(lines) + "\r\n").encode("ascii")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    want = {ICONS / "resonator.png": png_bytes(pixels()), ICONS / "resonator.pal": pal_bytes()}
    if args.check:
        stale = [p.name for p, b in want.items() if not p.exists() or p.read_bytes() != b]
        if stale:
            print("out of date: " + ", ".join(stale), file=sys.stderr)
            return 1
        print("Resonator icon matches the generator")
        return 0
    for p, b in want.items():
        p.write_bytes(b)
        print(f"wrote {p.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

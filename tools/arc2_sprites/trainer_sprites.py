#!/usr/bin/env python3
"""Placeholder battle (trainer class) sprites for the three Arc 2 Eclipse classes: palette swaps.

    python3 tools/arc2_sprites/trainer_sprites.py           # rewrite the 6 PNGs' palettes
    python3 tools/arc2_sprites/trainer_sprites.py --check   # fail if a PNG is out of date

R0 registered TRAINER_CLASS_ECLIPSE_GRUNT_M/_F and _LEADER with byte copies of the Galactic Grunt M/F and
Commander Mars graphics (res/trainers/classes/eclipse_*/front.png and front_scan.png). This rewrites
only the PLTE chunk of those PNGs from the stock source, so the pixels, the cell/anim JSON and the
scan key stay untouched and the build is unchanged apart from colours. Placeholder quality by plan
(art-final draws the real battle sprites):
  - Grunts: the white suit becomes the dark Eclipse uniform with violet shading, the gold "G" becomes
    a violet glow, the teal bowl cut becomes a dark violet hood colour (male) or lilac-silver hair
    (female), matching the overworld grunts (res/field/objects/arc1/eclipse_grunt_{m,f}.png).
  - Leader: Mars recoloured as Indra (dark auburn hair, violet-black coat, violet trim), since Indra
    is the only ECLIPSE_LEADER battle in Arc 2 (TRAINER_INDRA_DEPOT).
Index 1 (the red half of the held Poke Ball) and the skin ramp are kept.
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLASSES = REPO / "res/trainers/classes"

# Stock grunt palette, for reference: 0 bg, 1 ball red, 2 gold G, 3/4/5 teal hair (light..dark),
# 6 light grey, 7 grey, 8 dark grey, 9 near-black, 10/11/12/13 skin (light..outline), 14 white, 15 black.
GRUNT_COMMON = {
    2: (232, 208, 255),   # gold G -> violet glow
    6: (86, 74, 122),     # light grey -> uniform mid
    7: (104, 40, 176),    # grey -> violet trim / shading
    8: (40, 34, 60),      # dark grey -> uniform dark
    9: (24, 20, 36),      # near-black -> uniform deepest
    14: (132, 120, 172),  # white -> uniform light
}
GRUNT_M = GRUNT_COMMON | {3: (150, 132, 196), 4: (90, 76, 132), 5: (56, 46, 86)}      # hood
GRUNT_F = GRUNT_COMMON | {3: (236, 222, 252), 4: (200, 184, 232), 5: (128, 112, 168)}  # lilac-silver hair

# Stock Mars palette: 3/4/5 red hair (light..dark), the rest as the grunts.
LEADER = {
    2: (232, 208, 255),   # gold -> violet glow
    3: (158, 78, 64),     # hair light
    4: (106, 46, 44),     # hair mid
    5: (56, 22, 30),      # hair dark
    6: (64, 48, 98),      # coat dark violet
    7: (100, 42, 170),    # violet trim
    8: (34, 26, 50),      # coat darkest
    9: (20, 14, 30),      # near-black
    14: (108, 88, 152),   # white dress -> coat light
}

TARGETS = [  # (class dir, stock source dir, colour overrides)
    ("eclipse_grunt_m", "galactic_grunt_male", GRUNT_M),
    ("eclipse_grunt_f", "galactic_grunt_female", GRUNT_F),
    ("eclipse_leader", "commander_mars", LEADER),
]
FILES = ("front.png", "front_scan.png")


def chunks(data: bytes):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos = 8
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        yield kind, body
        pos += 12 + length


def chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def recolour(src: bytes, overrides: dict[int, tuple[int, int, int]]) -> bytes:
    out = [src[:8]]
    seen = False
    for kind, body in chunks(src):
        if kind == b"PLTE":
            seen = True
            pal = bytearray(body)
            for i, rgb in overrides.items():
                if 3 * i + 3 > len(pal):
                    raise ValueError(f"palette has no entry {i}")
                # store BGR555-exact values so the PNG shows what the DS shows
                pal[3 * i:3 * i + 3] = bytes(((c >> 3) << 3) | (c >> 5) for c in rgb)
            body = bytes(pal)
        out.append(chunk(kind, body))
    if not seen:
        raise ValueError("no PLTE chunk")
    return b"".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for target, source, overrides in TARGETS:
        for name in FILES:
            fresh = recolour((CLASSES / source / name).read_bytes(), overrides)
            dest = CLASSES / target / name
            if args.check:
                if not dest.exists() or dest.read_bytes() != fresh:
                    stale.append(f"{target}/{name}")
            else:
                dest.write_bytes(fresh)
                print(f"wrote {dest.relative_to(REPO)} (palette of {source}/{name})")
    if stale:
        print("out of date: " + ", ".join(stale), file=sys.stderr)
        return 1
    if args.check:
        print("all Eclipse trainer sprites match the generator")
    return 0


if __name__ == "__main__":
    sys.exit(main())

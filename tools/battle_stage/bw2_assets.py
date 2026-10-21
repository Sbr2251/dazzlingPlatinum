#!/usr/bin/env python3
"""Battle stage textures taken from Pokemon Black 2 / White 2's battle field models.

The battle side of this hack already uses B/W assets, and the BW2 visual parity work may
use the battle view textures of the pokebw2 decomp's checked-in res/graphics/btlv for battle
visuals (docs/living_battle_stage/stage_format.md, "BW2 visual parity: stage animation").
The textures the arena uses are extracted once into tools/battle_stage/bw2/ and checked in,
so build_stage.py does not need the pokebw2 checkout. Each file is

    char[4] "BW2T", u16 width, u16 height, u8 GXTexFmt, u8 0, u16 palette colours,
    texel data (the DS layout of the format), GXRgb palette

Run this script with a pokebw2 checkout to extract them again:

    python3 tools/battle_stage/bw2_assets.py [--pokebw2 /data/repos/pokebw2]

ASSETS lists (name, source file under res/graphics/btlv, texture, palette, transform):

    wave   batt_field21n of 115.nsbmd (batt_bg21, the water field): the translucent
           a3i5 glint layer that scrolls over BW2's water, 128x64. Every other row is
           kept (128x32): the glints are one or two texels tall, and it halves the VRAM.
"""

import argparse
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(HERE, "bw2")
MAGIC = b"BW2T"
HEAD = struct.Struct("<4sHHBBH")

TEXFMT_A3I5 = 1
TEXFMT_PLTT16 = 3
TEXFMT_PLTT256 = 4
BPP = {1: 8, 2: 2, 3: 4, 4: 8, 6: 8}

ASSETS = (
    ("wave", "115.nsbmd", "batt_field21n", "batt_field21n_pl", "every_other_row"),
)


class Bw2Texture:
    def __init__(self, width, height, fmt, data, palette):
        self.width, self.height, self.format = width, height, fmt
        self.data = bytes(data)
        self.palette = list(palette)

    def pack(self):
        return HEAD.pack(MAGIC, self.width, self.height, self.format, 0, len(self.palette)) + self.data + struct.pack(
            f"<{len(self.palette)}H", *self.palette)


def load(name):
    """The checked-in texture `name` (see ASSETS)."""
    with open(os.path.join(ASSET_DIR, name + ".bin"), "rb") as f:
        blob = f.read()

    magic, w, h, fmt, _pad, ncolors = HEAD.unpack_from(blob, 0)
    assert magic == MAGIC
    size = w * h * BPP[fmt] // 8
    data = blob[HEAD.size:HEAD.size + size]
    palette = struct.unpack_from(f"<{ncolors}H", blob, HEAD.size + size)
    return Bw2Texture(w, h, fmt, data, palette)


# ---- extraction from an NSBMD's TEX0 block (only used to refresh the checked-in files) ----

def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def _u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def _dict(b, off):
    """Nitro resource dictionary: [(name, entry data)]."""
    n = b[off + 1]
    entries = off + _u16(b, off + 6)
    unit, names = _u16(b, entries), _u16(b, entries + 2)
    return [(b[entries + names + 16 * i:entries + names + 16 * i + 16].split(b"\0")[0].decode("latin1"),
             b[entries + 4 + i * unit:entries + 4 + (i + 1) * unit]) for i in range(n)]


def extract(path, tex_name, pal_name):
    b = open(path, "rb").read()

    for i in range(_u16(b, 14)):
        o = _u32(b, 16 + 4 * i)

        if b[o:o + 4] != b"TEX0":
            continue

        tex_data, pal_data = o + _u32(b, o + 20), o + _u32(b, o + 56)
        texs = dict(_dict(b, o + _u16(b, o + 14)))
        pals = dict(_dict(b, o + _u16(b, o + 52)))
        param = _u32(texs[tex_name], 0)
        fmt, w, h = (param >> 26) & 7, 8 << ((param >> 20) & 7), 8 << ((param >> 23) & 7)
        start = tex_data + ((param & 0xFFFF) << 3)
        data = b[start:start + w * h * BPP[fmt] // 8]
        ncolors = {1: 32, 2: 4, 3: 16, 4: 256, 6: 8}[fmt]
        pal_start = pal_data + (_u16(pals[pal_name], 0) << 3)
        palette = [_u16(b, pal_start + 2 * k) for k in range(ncolors) if pal_start + 2 * k + 2 <= len(b)]
        return Bw2Texture(w, h, fmt, data, palette + [0] * (ncolors - len(palette)))

    raise ValueError(f"{path} has no TEX0 block")


def every_other_row(tex):
    row = tex.width * BPP[tex.format] // 8
    data = b"".join(tex.data[y * row:(y + 1) * row] for y in range(0, tex.height, 2))
    return Bw2Texture(tex.width, tex.height // 2, tex.format, data, tex.palette)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--pokebw2", default="/data/repos/pokebw2")
    args = parser.parse_args()
    os.makedirs(ASSET_DIR, exist_ok=True)

    for name, source, tex_name, pal_name, transform in ASSETS:
        tex = extract(os.path.join(args.pokebw2, "res/graphics/btlv", source), tex_name, pal_name)

        if transform:
            tex = globals()[transform](tex)

        out = os.path.join(ASSET_DIR, name + ".bin")

        with open(out, "wb") as f:
            f.write(tex.pack())

        print(f"{os.path.relpath(out)}: {tex_name} of {source}, {tex.width}x{tex.height} format {tex.format}")


if __name__ == "__main__":
    main()

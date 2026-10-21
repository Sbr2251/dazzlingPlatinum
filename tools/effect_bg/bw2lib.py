"""Readers for Black 2/White 2's extracted battle effect backgrounds (pokebw2, read-only).

Source: /data/repos/pokebw2/res/graphics/btlv_effvm_bg (ARCID_BTLV_EFFVM_BG, archive 94) and
btlv_effvm_pal_anim (ARCID_BTLV_EFFVM_PAL_ANIM, archive 231), as extracted by pokebw2's configure.py.

btlv_effvm_bg holds 77 backgrounds as triples, file id N = 3 * k:
    N      .nscr  512x512 text screen, 4bpp entries, stored in 32x32-tile screen blocks
    N + 1  .png   the 4bpp tile sheet (256 px wide, 8bpp PNG with a 16-entry PLTE: only the indices count)
    N + 2  .pal   JASC palette, 16..128 colours; BtlvEffvm_CmdLoadBg (btlv_effvm.c:1874) loads it at BG
                  colour 0x80, so its row r is BG palette row 8 + r, and screen entries name rows 8..15.
                  Entries on row 0 are BW2's empty tiles.
then 231 .ncer / 232 .nanr and 17 png/pal pairs (233..266): the Poke Ball OBJ sheets, not backgrounds.

btlv_effvm_pal_anim holds 23 anims as pairs, file id 2 * k:
    2k     .bin   u8 rows (8..15) ended by 0xff, then at 0x80 u16 frame counts ended by 0xff98
    2k + 1 .pal   the rows the anim cycles: anim row r is file row r - 8 (BtlvEffvm_PalAnimTask,
                  btlv_effvm.c:4410, copies it over BG palette row 8, i.e. the background's row 0).
"""

import os
import struct

import numpy as np
from PIL import Image

BW2_ROOT = os.environ.get("POKEBW2", "/data/repos/pokebw2")
BG_DIR = os.path.join(BW2_ROOT, "res/graphics/btlv_effvm_bg")
ANIM_DIR = os.path.join(BW2_ROOT, "res/graphics/btlv_effvm_pal_anim")

BG_IDS = list(range(0, 231, 3))  # the 77 backgrounds, by BW2 file id of their NSCR
ANIM_IDS = list(range(23))
BALL_SHEETS = list(range(233, 267, 2))


def read_jasc(path):
    lines = open(path).read().split("\n")
    count = int(lines[2])
    return np.array([tuple(map(int, lines[3 + i].split())) for i in range(count)], np.int32)


def write_jasc(path, colors, total=None):
    colors = [tuple(int(v) for v in c) for c in colors]
    if total is not None:
        colors = colors + [(0, 0, 0)] * (total - len(colors))
    with open(path, "w", newline="\r\n") as f:
        f.write("JASC-PAL\n0100\n%d\n" % len(colors))
        for c in colors:
            f.write("%d %d %d\n" % c)


def read_nscr(path):
    """(width_px, height_px, entries as a 2D array [rows][cols] in screen order)."""
    data = open(path, "rb").read()
    width, height = struct.unpack("<HH", data[24:28])
    size = struct.unpack("<I", data[32:36])[0]
    raw = np.frombuffer(data[36:36 + size], dtype="<u2").astype(np.int32)
    tw, th = width // 8, height // 8
    grid = np.zeros((th, tw), np.int32)
    blocks_x = max(tw // 32, 1)
    for i, v in enumerate(raw):
        block, j = divmod(i, 1024)
        bx, by = block % blocks_x, block // blocks_x
        grid[by * 32 + j // 32, bx * 32 + j % 32] = v
    return width, height, grid


def read_tiles(path):
    img = np.array(Image.open(path))
    h, w = img.shape
    return img.reshape(h // 8, 8, w // 8, 8).transpose(0, 2, 1, 3).reshape(-1, 8, 8).astype(np.int32)


class Bw2Bg:
    def __init__(self, bg_id):
        self.id = bg_id
        self.width, self.height, self.grid = read_nscr(os.path.join(BG_DIR, "%03d.nscr" % bg_id))
        self.tiles = read_tiles(os.path.join(BG_DIR, "%03d.png" % (bg_id + 1)))
        self.palette = read_jasc(os.path.join(BG_DIR, "%03d.pal" % (bg_id + 2)))

    def render(self, palette=None, grid=None):
        """RGB array of the whole screen; row-0 (empty) entries are black."""
        pal = self.palette if palette is None else palette
        grid = self.grid if grid is None else grid
        th, tw = grid.shape
        out = np.zeros((th * 8, tw * 8, 3), np.uint8)
        for ty in range(th):
            for tx in range(tw):
                v = grid[ty, tx]
                row = (v >> 12) - 8
                if row < 0:
                    continue
                t = self.tiles[v & 0x3FF]
                if v & 0x400:
                    t = t[:, ::-1]
                if v & 0x800:
                    t = t[::-1, :]
                ci = np.clip(row * 16 + t, 0, len(pal) - 1)
                out[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8] = pal[ci]
        return out


class Bw2PalAnim:
    def __init__(self, anim_id):
        self.id = anim_id
        data = open(os.path.join(ANIM_DIR, "%02d.bin" % (2 * anim_id)), "rb").read()
        self.raw = data
        self.rows = []
        i = 0
        while data[i] != 0xFF:
            self.rows.append(data[i])
            i += 1
        self.frames = []
        j = 0x80
        while struct.unpack("<H", data[j:j + 2])[0] != 0xFF98:
            self.frames.append(struct.unpack("<H", data[j:j + 2])[0])
            j += 2
        self.palette = read_jasc(os.path.join(ANIM_DIR, "%02d.pal" % (2 * anim_id + 1)))

    def row_colors(self, row):
        """The 16 colours of anim row `row`; rows past the end of the extracted palette are black
        (the extraction drops trailing black rows: anim 10 shows row 12, past its 4 rows)."""
        colors = np.zeros((16, 3), np.int32)
        part = self.palette[(row - 8) * 16:(row - 8) * 16 + 16]
        colors[:len(part)] = part
        return colors

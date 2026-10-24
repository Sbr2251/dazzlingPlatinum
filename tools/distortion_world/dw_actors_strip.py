#!/usr/bin/env python3
"""Render frame strips from dw_actors_test FRAME log lines (stdlib only, PNG via zlib).

Usage: python3 tools/distortion_world/dw_actors_strip.py <actors_test.log> <out_dir>
Writes fall_strip.png (wall row + floor row, stone 0 falling to the landing tile) and
shadow_strip.png (floor row, shadow patrol), one row per sampled frame, in log order.
Row captions live in /tmp/dwp/engine-b/README.md, not in the image (no font rasteriser).
"""
import re
import struct
import sys
import zlib
from pathlib import Path

CELL = 24
GAP = 4
BG = (16, 16, 16)
TILE = (42, 42, 42)
EDGE = (229, 72, 77)
STONE = (201, 168, 106)
LANDED = (126, 217, 87)
SHADOW = (139, 92, 246)
VOIDCOL = (30, 58, 95)


def _chunk(kind, data):
    c = struct.pack(">I", len(data)) + kind + data
    c += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return c


def write_png(path, px, w, h):
    raw = b"".join(b"\x00" + bytes(px[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(raw))
    png += _chunk(b"IEND", b"")
    Path(path).write_bytes(png)


def paint(px, w, x, y, color, size=CELL):
    for dy in range(size):
        for dx in range(size):
            idx = ((y + dy) * w + (x + dx)) * 3
            px[idx:idx + 3] = bytes(color)


def fall_strip(frames, out):
    # frames: list of (frame, stone x,y,z, state, override). Two rows per frame: wall z 12..20,
    # floor z 12..20 (landing at z=18). Sample every 3rd frame + the landing frame.
    sample = [f for f in frames if f[0] % 3 == 0 or f[4] == 2]
    cols = 9
    w = cols * (CELL + GAP) + GAP
    h = len(sample) * 2 * (CELL + GAP) + GAP
    px = bytearray(bytes(BG) * w * h)
    for r, (num, sx, sy, sz, state, override) in enumerate(sample):
        for kind, y0 in (("wall", 0), ("floor", 1)):
            for c in range(cols):
                z = 12 + c
                x = GAP + c * (CELL + GAP)
                y = GAP + (r * 2 + y0) * (CELL + GAP)
                color = TILE
                if kind == "wall" and z == 18:
                    color = EDGE
                if kind == "floor" and z == 18:
                    color = VOIDCOL if override == 0 else LANDED
                if kind == "wall" and state == 1 and sz == z and sy == 3:
                    color = STONE
                if kind == "floor" and state == 2 and sz == z:
                    color = STONE
                paint(px, w, x, y, color)
    write_png(out, px, w, h)


def shadow_strip(frames, out):
    # frames: list of (frame, phase, tile z). One floor row per frame, z 12..20.
    cols = 9
    w = cols * (CELL + GAP) + GAP
    h = len(frames) * (CELL + GAP) + GAP
    px = bytearray(bytes(BG) * w * h)
    for r, (num, phase, tz) in enumerate(frames):
        for c in range(cols):
            z = 12 + c
            color = SHADOW if z == tz else TILE
            paint(px, w, GAP + c * (CELL + GAP), GAP + r * (CELL + GAP), color)
    write_png(out, px, w, h)


def main():
    log = Path(sys.argv[1]).read_text()
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    fall, shadow = [], []
    for line in log.splitlines():
        m = re.match(r"FRAME fall (\d+) stone0=(\d+),(\d+),(\d+) state=(\d+) blocks=\d+,\d+ override=(\d+)", line)
        if m:
            fall.append(tuple(int(v) for v in m.groups()))
        m = re.match(r"FRAME shadow (\d+) phase=(\d+) tile=(\d+),(\d+),(\d+) state=(\d+)", line)
        if m:
            frame, phase, _, _, tz, _ = (int(v) for v in m.groups())
            shadow.append((frame, phase, tz))
    if fall:
        n = len([f for f in fall if f[0] % 3 == 0 or f[4] == 2])
        fall_strip(fall, out_dir / "fall_strip.png")
        print(f"fall_strip.png: {n} sampled frames")
    if shadow:
        shadow_strip(shadow, out_dir / "shadow_strip.png")
        print(f"shadow_strip.png: {len(shadow)} frames")


if __name__ == "__main__":
    main()

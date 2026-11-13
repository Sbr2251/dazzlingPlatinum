#!/usr/bin/env python3
"""Build the demo TexturePack: nearest-2x + hand-tuned detail pass.

Usage: make_demo_pack.py <dump-dir> <out-dir> [hash ...]
With no hashes, picks the 8 largest textures in <dump-dir>/manifest.csv
(the Twinleaf field tilesets when run on a Twinleaf dump). The pass is
pixel art, not a smoothing upscale: each source pixel becomes a 2x2
block, the top-left sub-pixel is lightened, the bottom/right sub-pixels
are darkened, flat areas get a checker grain, and colour edges get a
dark outline sub-pixel. No neighbouring colours are ever blended.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pngio import read_png, write_png

def shade(c, f):
    return max(0, min(255, int(round(c * f))))

def detail(w, h, px):
    out = bytearray(w * 2 * h * 2 * 4)
    W = w * 2
    def get(x, y):
        x = min(max(x, 0), w - 1); y = min(max(y, 0), h - 1)
        i = (y * w + x) * 4
        return px[i:i+4]
    for y in range(h):
        for x in range(w):
            c = get(x, y)
            if c[3] == 0:
                continue
            flat = get(x-1, y) == c and get(x+1, y) == c and get(x, y-1) == c and get(x, y+1) == c
            edge_r = get(x+1, y) != c
            edge_b = get(x, y+1) != c
            for dy in range(2):
                for dx in range(2):
                    f = 1.0
                    if dx == 0 and dy == 0: f = 1.07       # highlight
                    if dx == 1 and dy == 1: f = 0.92       # shade
                    if flat and (x + y) % 2 == 0: f *= 0.96  # grain
                    if edge_r and dx == 1: f *= 0.85       # outline
                    if edge_b and dy == 1: f *= 0.85
                    o = ((y*2+dy) * W + (x*2+dx)) * 4
                    out[o] = shade(c[0], f); out[o+1] = shade(c[1], f)
                    out[o+2] = shade(c[2], f); out[o+3] = c[3]
    return bytes(out)

def main():
    dump, outdir = sys.argv[1], sys.argv[2]
    hashes = sys.argv[3:]
    if not hashes:
        rows = []
        for line in open(os.path.join(dump, 'manifest.csv')):
            p = line.strip().split(',')
            if len(p) >= 3: rows.append((p[0], int(p[1]) * int(p[2])))
        rows.sort(key=lambda r: -r[1])
        hashes = [r[0] for r in rows[:8]]
    os.makedirs(outdir, exist_ok=True)
    for name in hashes:
        w, h, px = read_png(os.path.join(dump, name + '.png'))
        write_png(os.path.join(outdir, name + '.png'), w * 2, h * 2, detail(w, h, px))
        print(f'{name}: {w}x{h} -> {w*2}x{h*2}')
    with open(os.path.join(outdir, 'pack.txt'), 'w') as f:
        f.write('Demo pack: nearest-2x + detail pass by tools/texpack/make_demo_pack.py\n')
        for name in hashes: f.write(name + '\n')

if __name__ == '__main__':
    main()

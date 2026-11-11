#!/usr/bin/env python3
"""Pixel-compare two SIM_DEBUG_SHOT_DIR screenshot sets (CPU vs GPU 2D path).

Usage: g2gpu_compare.py <dirA> <dirB>
Compares frame_*.bmp files present in both dirs byte-wise after the BMP
header (BMP pixel data from SDL_SaveBMP is uncompressed). Prints per-frame
diff counts and a summary. Exit 0 iff every common frame is pixel-exact.
ASCII only.
"""
import os, struct, sys

def load_bmp(path):
    with open(path, 'rb') as f:
        data = f.read()
    if data[:2] != b'BM':
        raise ValueError(path + ': not a BMP')
    off = struct.unpack_from('<I', data, 10)[0]
    w = struct.unpack_from('<i', data, 18)[0]
    h = struct.unpack_from('<i', data, 22)[0]
    bpp = struct.unpack_from('<H', data, 28)[0]
    return w, abs(h), bpp, data[off:]

def main():
    a_dir, b_dir = sys.argv[1], sys.argv[2]
    names = sorted(set(os.listdir(a_dir)) & set(os.listdir(b_dir)))
    names = [n for n in names if n.startswith('frame_') and n.endswith('.bmp')]
    if not names:
        print('no common frames'); return 2
    bad = 0
    for n in names:
        wa, ha, ba, pa = load_bmp(os.path.join(a_dir, n))
        wb, hb, bb, pb = load_bmp(os.path.join(b_dir, n))
        if (wa, ha, ba) != (wb, hb, bb) or len(pa) != len(pb):
            print(n + ': geometry mismatch'); bad += 1; continue
        diff = sum(1 for i in range(0, len(pa), 4) if pa[i:i+4] != pb[i:i+4])
        if diff:
            bad += 1
            print('%s: %d/%d pixels differ' % (n, diff, wa * ha))
        else:
            print(n + ': exact')
    print('frames=%d mismatched=%d' % (len(names), bad))
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main())

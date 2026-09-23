#!/usr/bin/env python3
"""Reconstruct giratina_prerender.bin exactly as title_screen.c plays it.

Mirrors the C runtime: parse header, LZ10-decode the keyframe into the RAM
framebuffer, then per step decode the chunk, apply the change bitmask to the
framebuffer and "upload" it to the back char slot, flipping on the next
VBlank. Dumps the displayed image per step as PNG (BGR555 -> 8-bit like the
DS LCD path) and checks the memory / bandwidth budgets used by the C code.
"""

import argparse
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lz10  # noqa: E402
from pack_frames import FB_SIZE, H, HEADER_SIZE, MAGIC, MASK_SIZE, NUM_TILES, TH, TW, W  # noqa: E402

# Budgets that title_screen.c relies on (keep in sync with the C defines).
CHAR_SLOT_SIZE = 0x10000          # slot A at BG VRAM 0x10000 (bank B), slot B at 0x20000 (bank D)
TEXT_BG_MAX_TILES = 1024          # 10-bit tile index of a text BG tilemap entry
HEAP_EXTRA = 0x70000 - 0x40000    # TITLE_SCREEN_HEAP_SIZE growth over the stock heap
MAX_CHUNK_LIMIT = 0x8000          # C allocates maxChunkSize from the header; sanity cap


def parse(blob):
    assert blob[:4] == MAGIC, "bad magic"
    ver, num = struct.unpack_from("<HH", blob, 4)
    pal_off, key_off, key_size, max_chunk, max_raw, total_vb = struct.unpack_from("<IIIIII", blob, 8)
    assert ver == 1
    steps = []
    for i in range(num):
        off, sh = struct.unpack_from("<II", blob, HEADER_SIZE + i * 8)
        steps.append((off, sh & 0xFFFFFF, sh >> 24))
    pal = np.frombuffer(blob, dtype="<u2", count=256, offset=pal_off)
    return dict(num=num, pal_off=pal_off, key_off=key_off, key_size=key_size, max_chunk=max_chunk,
                max_raw=max_raw, total_vb=total_vb, steps=steps, pal=pal)


def pal_to_rgb(pal):
    r = pal & 31
    g = (pal >> 5) & 31
    b = (pal >> 10) & 31
    c = np.stack([r, g, b], -1).astype(np.int32)
    return ((c << 3) | (c >> 2)).astype(np.uint8)


def render(fb, pal_rgb):
    tiles = np.frombuffer(bytes(fb), dtype=np.uint8).reshape(TH, TW, 8, 8)
    idx = tiles.transpose(0, 2, 1, 3).reshape(H, W)
    assert not (idx == 0).any(), "index 0 (transparent) used by a pixel"
    return pal_rgb[idx]


def apply_chunk(fb, raw):
    mask = raw[:MASK_SIZE]
    p = MASK_SIZE
    for t in range(NUM_TILES):
        if mask[t >> 3] & (1 << (t & 7)):
            fb[t * 64:(t + 1) * 64] = raw[p:p + 64]
            p += 64
    assert p == len(raw), "chunk length mismatch"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bin")
    ap.add_argument("--out", default="/tmp/gir_prerender/sim")
    ap.add_argument("--ref", default="/tmp/gir_prerender/frames256.npy")
    ap.add_argument("--schedule", default="1-360:1:2", help="same spec given to pack_frames.py")
    ap.add_argument("--loops", type=int, default=2)
    ap.add_argument("--dump-every", type=int, default=1)
    args = ap.parse_args()

    from PIL import Image
    from pack_frames import parse_schedule

    blob = open(args.bin, "rb").read()
    hd = parse(blob)
    pal_rgb = pal_to_rgb(hd["pal"])
    ref = np.load(args.ref) if args.ref else None
    sched = parse_schedule(args.schedule, ref.shape[0]) if ref is not None else None
    os.makedirs(args.out, exist_ok=True)

    # budgets
    assert hd["key_size"] <= hd["max_chunk"] and hd["max_chunk"] <= MAX_CHUNK_LIMIT, hd["max_chunk"]
    assert hd["max_raw"] <= MASK_SIZE + FB_SIZE
    heap = FB_SIZE + (MASK_SIZE + FB_SIZE) + hd["max_chunk"] + hd["num"] * 8 + 512 + 64
    assert heap <= HEAP_EXTRA, heap
    assert FB_SIZE <= CHAR_SLOT_SIZE and NUM_TILES <= TEXT_BG_MAX_TILES
    assert len(blob) < 16 * 1024 * 1024

    fb = bytearray(lz10.decompress(blob[hd["key_off"]:hd["key_off"] + hd["key_size"]]))
    assert len(fb) == FB_SIZE
    key_state = bytes(fb)

    # step i shows state i; the chunk for state i (i>0) is entry i, entry 0 wraps
    psnr = []
    worst_upload = 0
    total_read = 0
    vb = 0
    for loop in range(args.loops):
        for i in range(hd["num"]):
            if loop > 0 or i > 0:
                off, size, _ = hd["steps"][i]
                assert off % 4 == 0 and off + size <= len(blob)
                raw = lz10.decompress(blob[off:off + size])
                assert len(raw) <= hd["max_raw"]
                apply_chunk(fb, raw)
                total_read += size
                worst_upload = max(worst_upload, FB_SIZE)
            if i == 0:
                assert bytes(fb) == key_state, "loop is not exactly periodic"
            hold = hd["steps"][i][2]
            if loop == 0:
                img = render(fb, pal_rgb)
                if ref is not None:
                    tgt = ref[sched[i][0]].astype(np.float32)
                    mse = ((img.astype(np.float32) - tgt) ** 2).mean()
                    psnr.append(10 * np.log10(255.0 ** 2 / max(mse, 1e-6)))
                if i % args.dump_every == 0:
                    Image.fromarray(img).save(os.path.join(args.out, "s%03d.png" % i))
            vb += hold
    assert vb == hd["total_vb"] * args.loops
    secs = hd["total_vb"] / 60.0
    print("steps %d, loop %.2fs, file %d B, maxChunk %d B, maxRaw %d B, heap need %d B"
          % (hd["num"], secs, len(blob), hd["max_chunk"], hd["max_raw"], heap))
    print("card read avg %.1f KB/s, per-step VRAM upload %d B (outside VBlank, back slot)"
          % (total_read / args.loops / secs / 1024.0, worst_upload))
    if psnr:
        p = np.array(psnr)
        print("PSNR vs 256x192 render: mean %.2f dB min %.2f dB (step %d)" % (p.mean(), p.min(), p.argmin()))
    print("loop periodic: OK; index 0 unused: OK")


if __name__ == "__main__":
    main()

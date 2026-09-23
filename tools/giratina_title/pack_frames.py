#!/usr/bin/env python3
"""Pack pre-rendered Giratina title frames into a streamable DS blob.

Input : 256x192 RGB frames (a .npy stack of shape (N,192,256,3) uint8, or a
        directory of f####.png written by render_frames.py).
Output: giratina_prerender.bin, consumed by src/applications/title_screen.c.

Scheme (8bpp text BG, one shared 256-color extended palette):
  * Global palette: k-means in sRGB over samples from every frame, colors
    snapped to BGR555. Index 0 is transparent on 8bpp BGs, so it is never
    referenced by a pixel (it is written as black for completeness).
  * Spatially fixed 4x4 Bayer ordered dither, so static areas stay
    temporally stable (no dither crawl) and compress well.
  * Conditional replenishment on an identity tilemap: the DS keeps a 48KB
    framebuffer of 768 8x8 8bpp tiles; each step only ships the tiles whose
    quantized error against the new target frame would improve by more than
    a threshold (plus any tile that has drifted too far).
  * Each step = LZ10(96-byte change bitmask + 64 bytes per changed tile).
    Table entry i turns state i-1 into state i; entry 0 is the wrap delta
    that turns the last state back into the exact keyframe state, so the
    loop is exactly periodic.

File layout (little endian, all offsets from file start, 4-byte aligned):
  0x00 u32 magic 'GTPR'
  0x04 u16 version (1)
  0x06 u16 numSteps
  0x08 u32 paletteOffset      (512 bytes, 256 x BGR555)
  0x0C u32 keyframeOffset     (LZ10 of the full 49152-byte framebuffer)
  0x10 u32 keyframeSize       (compressed bytes)
  0x14 u32 maxChunkSize       (largest compressed step / keyframe, bytes)
  0x18 u32 maxRawSize         (largest decompressed step, bytes)
  0x1C u32 totalVBlanks       (sum of holds = loop length in VBlanks)
  0x20 step table, numSteps x { u32 offset; u32 sizeAndHold }
       sizeAndHold = compressedSize | (holdVBlanks << 24)
"""

import argparse
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lz10  # noqa: E402

W, H = 256, 192
TW, TH = W // 8, H // 8
NUM_TILES = TW * TH
FB_SIZE = NUM_TILES * 64
MASK_SIZE = NUM_TILES // 8
MAGIC = b"GTPR"
HEADER_SIZE = 0x20

BAYER4 = (np.array([[0, 8, 2, 10],
                    [12, 4, 14, 6],
                    [3, 11, 1, 9],
                    [15, 7, 13, 5]], dtype=np.float32) + 0.5) / 16.0 - 0.5


def load_frames(src):
    if src.endswith(".npy"):
        return np.load(src)
    from PIL import Image
    names = sorted(n for n in os.listdir(src) if n.endswith(".png"))
    out = []
    for n in names:
        im = Image.open(os.path.join(src, n)).convert("RGB")
        if im.size != (W, H):
            im = im.resize((W, H), Image.LANCZOS)
        out.append(np.asarray(im))
    return np.stack(out)


def parse_schedule(spec, count):
    """spec: comma list of 'A-B:STEP:HOLD' over 1-based frame numbers."""
    steps = []
    for part in spec.split(","):
        rng, step, hold = part.split(":")
        a, b = (int(x) for x in rng.split("-"))
        for f in range(a, b + 1, int(step)):
            if not 1 <= f <= count:
                raise ValueError("frame %d out of range" % f)
            steps.append((f - 1, int(hold)))
    return steps


def to555(rgb):
    """Snap 8-bit RGB to the nearest BGR555 level, returned as 8-bit RGB."""
    c5 = np.clip(np.rint(rgb.astype(np.float32) * 31.0 / 255.0), 0, 31).astype(np.int32)
    return (c5 << 3) | (c5 >> 2), c5


def kmeans_palette(frames, ncolors, seed=1, iters=24, samples=240000):
    rng = np.random.default_rng(seed)
    n = frames.shape[0]
    per = max(1, samples // n)
    pix = []
    for i in range(n):
        f = frames[i].reshape(-1, 3)
        pix.append(f[rng.integers(0, f.shape[0], per)])
    pix = np.concatenate(pix).astype(np.float32)
    # init: farthest-point-ish via random unique picks sorted by luminance
    uniq = np.unique(pix.astype(np.uint8), axis=0).astype(np.float32)
    idx = rng.choice(uniq.shape[0], min(ncolors, uniq.shape[0]), replace=False)
    cent = uniq[idx].copy()
    for _ in range(iters):
        lab = nearest(pix, cent)
        sums = np.zeros_like(cent)
        cnt = np.bincount(lab, minlength=cent.shape[0]).astype(np.float32)
        for ch in range(3):
            sums[:, ch] = np.bincount(lab, weights=pix[:, ch], minlength=cent.shape[0])
        empty = cnt == 0
        cent[~empty] = sums[~empty] / cnt[~empty, None]
        if empty.any():
            # re-seed empty clusters at the worst-represented samples
            err = ((pix - cent[lab]) ** 2).sum(1)
            worst = np.argsort(err)[-int(empty.sum()):]
            cent[empty] = pix[worst]
    return cent


def nearest(pix, cent, block=65536):
    out = np.empty(pix.shape[0], dtype=np.int32)
    c2 = (cent ** 2).sum(1)
    for s in range(0, pix.shape[0], block):
        p = pix[s:s + block]
        d = c2[None, :] - 2.0 * p @ cent.T
        out[s:s + block] = np.argmin(d, axis=1)
    return out


def build_lut(pal_rgb, bits=6):
    """LUT from a bits-per-channel lattice to the nearest palette entry."""
    lv = np.arange(1 << bits, dtype=np.float32) * 255.0 / ((1 << bits) - 1)
    g = np.stack(np.meshgrid(lv, lv, lv, indexing="ij"), -1).reshape(-1, 3)
    return nearest(g, pal_rgb.astype(np.float32)).astype(np.uint8)


def quantize(frame, pal_rgb, lut, amp, bits=6):
    """Ordered-dither one frame; returns palette indices (1..255) HxW."""
    f = frame.astype(np.float32)
    thr = np.tile(BAYER4, (H // 4, W // 4))[..., None] * amp
    f = np.clip(f + thr, 0, 255)
    q = np.rint(f * ((1 << bits) - 1) / 255.0).astype(np.int32)
    key = (q[..., 0] << (2 * bits)) | (q[..., 1] << bits) | q[..., 2]
    return lut[key]


def to_tiles(idx):
    """HxW index image -> (768, 64) tile array in tilemap order."""
    return idx.reshape(TH, 8, TW, 8).transpose(0, 2, 1, 3).reshape(NUM_TILES, 64)


def tile_err(rgb_tiles_a, rgb_tiles_b):
    return ((rgb_tiles_a.astype(np.float32) - rgb_tiles_b.astype(np.float32)) ** 2).mean(axis=(1, 2))


def encode_delta(prev, new, changed):
    mask = np.zeros(MASK_SIZE, dtype=np.uint8)
    for t in np.nonzero(changed)[0]:
        mask[t >> 3] |= 1 << (t & 7)
    raw = mask.tobytes() + new[changed].astype(np.uint8).tobytes()
    return raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="/tmp/gir_prerender/frames256.npy")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pal-out", help="optional JASC .pal dump for inspection")
    ap.add_argument("--schedule", default="1-360:1:2",
                    help="comma list of A-B:STEP:HOLD (1-based frames, hold in VBlanks)")
    ap.add_argument("--dither", type=float, default=6.0, help="Bayer amplitude (8-bit units)")
    ap.add_argument("--thresh", type=float, default=30.0,
                    help="min MSE improvement (per-pixel RGB^2) to resend a tile")
    ap.add_argument("--drift", type=float, default=60.0,
                    help="always resend a tile whose displayed MSE exceeds this")
    ap.add_argument("--gamma", type=float, default=0.6,
                    help="work space exponent: palette fit, dither and tile error run on "
                         "255*(x/255)^gamma so the dark gradient gets enough colors")
    args = ap.parse_args()

    frames = load_frames(args.src)
    n = frames.shape[0]
    sched = parse_schedule(args.schedule, n)
    print("frames %d, steps %d, loop %d vblanks" % (n, len(sched), sum(h for _, h in sched)))

    g = args.gamma

    def fwd(x):
        return 255.0 * (np.asarray(x, dtype=np.float32) / 255.0) ** g

    def inv(y):
        return 255.0 * (np.clip(np.asarray(y, dtype=np.float32), 0, 255) / 255.0) ** (1.0 / g)

    used = np.stack([fwd(frames[f]) for f, _ in sched])
    cent = kmeans_palette(used, 255)
    del used
    pal8, pal5 = to555(inv(cent))
    # palette entry 0 = transparent (unused); entries 1..255 = k-means colors
    pal_rgb = np.zeros((256, 3), dtype=np.int32)
    pal_rgb[1:] = pal8
    pal_bgr555 = np.zeros(256, dtype=np.uint16)
    pal_bgr555[1:] = (pal5[:, 0] | (pal5[:, 1] << 5) | (pal5[:, 2] << 10)).astype(np.uint16)
    pal_t = fwd(pal_rgb)  # palette in work space, for matching and error
    lut = build_lut(pal_t[1:]) + 1  # indices 1..255

    targets = []
    quant = []
    for f, _ in sched:
        ft = fwd(frames[f])
        q = quantize(ft, pal_t, lut, args.dither)
        quant.append(to_tiles(q))
        targets.append(ft.reshape(TH, 8, TW, 8, 3).transpose(0, 2, 1, 3, 4)
                       .reshape(NUM_TILES, 64, 3))

    # conditional replenishment
    state = quant[0].copy()
    states = [state.copy()]
    deltas = [None]
    counts = []
    for i in range(1, len(sched)):
        tgt = targets[i]
        err_keep = tile_err(pal_t[state], tgt)
        err_new = tile_err(pal_t[quant[i]], tgt)
        changed = ((err_keep - err_new) > args.thresh) | (err_keep > args.drift)
        changed &= np.any(state != quant[i], axis=1)
        raw = encode_delta(state, quant[i], changed)
        state = state.copy()
        state[changed] = quant[i][changed]
        states.append(state.copy())
        deltas.append(raw)
        counts.append(int(changed.sum()))
    # wrap: last state -> exact keyframe state
    wrap_changed = np.any(state != states[0], axis=1)
    deltas[0] = encode_delta(state, states[0], wrap_changed)
    counts.append(int(wrap_changed.sum()))

    key_raw = states[0].astype(np.uint8).tobytes()
    assert len(key_raw) == FB_SIZE
    key_lz = lz10.compress(key_raw)
    comp = [lz10.compress(d) for d in deltas]

    num = len(sched)
    table_off = HEADER_SIZE
    pal_off = table_off + num * 8
    key_off = pal_off + 512
    pos = key_off + len(key_lz)
    offsets = []
    for c in comp:
        offsets.append(pos)
        pos += len(c)
    max_chunk = max([len(key_lz)] + [len(c) for c in comp])
    max_raw = max(len(d) for d in deltas)
    total_vb = sum(h for _, h in sched)

    blob = bytearray()
    blob += MAGIC
    blob += struct.pack("<HH", 1, num)
    blob += struct.pack("<IIIIII", pal_off, key_off, len(key_lz), max_chunk, max_raw, total_vb)
    assert len(blob) == HEADER_SIZE
    for (f, hold), off, c in zip(sched, offsets, comp):
        assert len(c) < (1 << 24) and 1 <= hold < 256 and off % 4 == 0
        blob += struct.pack("<II", off, len(c) | (hold << 24))
    blob += pal_bgr555.astype("<u2").tobytes()
    blob += key_lz
    for c in comp:
        blob += c
    assert len(blob) == pos

    with open(args.out, "wb") as fh:
        fh.write(blob)

    if args.pal_out:
        with open(args.pal_out, "w", newline="\r\n") as fh:
            fh.write("JASC-PAL\n0100\n256\n")
            for r, g, b in pal_rgb:
                fh.write("%d %d %d\n" % (r, g, b))

    cs = np.array(counts)
    sizes = np.array([len(c) for c in comp])
    print("tiles/step mean %.1f max %d | chunk mean %d max %d B | key %d B | raw max %d B"
          % (cs.mean(), cs.max(), sizes.mean(), sizes.max(), len(key_lz), max_raw))
    print("total %d bytes (%.1f KB)" % (len(blob), len(blob) / 1024.0))


if __name__ == "__main__":
    main()

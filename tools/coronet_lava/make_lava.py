"""Lava tile for Mt. Coronet 1F South (dun_sea in texture set 074). See docs/coronet_1f_lava/PLAN.md, Step 1.

Usage: python3 tools/coronet_lava/make_lava.py  (needs Pillow; writes to $OUT_DIR, default /tmp/coronet_lava)

Outputs:
  lava_tile.png      frame 0, 16x16 indexed
  lava.pal           JASC-PAL, 16 colours
  lava_frames.bin    NUM_FRAMES x 128 bytes of 4bpp texels (DS format 3, low nibble = left texel)
  lava_preview.gif   tiled preview with texel frames + palette cycling, reference only

Other scripts import palette(), frames() and texels_4bpp() from here.
"""
import math
import os
import random

SIZE = 16
# The speckle layer drifts +1 px right per frame, so a seamless loop over a 16 px tile takes 16 frames.
NUM_FRAMES = 16
FRAME_VBLANKS = 6

PALETTE = [
    (160, 40, 22),   # 0 darkest crust / veins
    (91, 40, 51),    # 1 dark crimson cooling spots
    (210, 36, 14),   # 2-5 red-orange base, cycled
    (228, 40, 15),
    (240, 42, 15),
    (243, 56, 16),
    (243, 74, 17),   # 6-9 orange speckle bodies, cycled
    (245, 94, 18),
    (243, 114, 17),
    (248, 134, 20),
    (250, 154, 21),  # 10-13 yellow-orange speckle cores, cycled
    (252, 176, 40),
    (255, 196, 64),
    (255, 214, 90),
    (255, 236, 150), # 14 hot fleck
    (255, 250, 210), # 15 bubble pop, runtime only
]

# (first index, length, period in VBlanks) for the palette shimmer, Step 4b
CYCLES = [(2, 4, 10), (6, 4, 7), (10, 4, 5)]

# Speckle rows, about 4 px apart and staggered: (row y, [(x, radius, phase)...]).
# radius 1 = 2x2-ish blob, 2 = 3-4 px blob. phase offsets the cycling indices so neighbours differ.
ROWS = [
    (1, [(2, 2, 0), (10, 1, 2)]),
    (5, [(6, 1, 1), (13, 2, 3)]),
    (9, [(1, 1, 2), (9, 2, 0)]),
    (13, [(5, 2, 1), (14, 1, 3)]),
]
# 4-frame vertical bob; odd rows run in opposite phase so the rows don't move as one sheet
BOB = [0, 1, 0, -1]


def palette():
    return list(PALETTE)


def bgr555(c):
    r, g, b = c
    return (r >> 3) | (g >> 3) << 5 | (b >> 3) << 10


def _wrap(v):
    return v % SIZE


def base_layer():
    """Diagonal bands of 2-5 with a tileable wobble; neighbouring texels step through consecutive indices."""
    px = [[0] * SIZE for _ in range(SIZE)]
    for y in range(SIZE):
        for x in range(SIZE):
            wob = round(1.5 * math.sin(2 * math.pi * y / SIZE) + math.sin(2 * math.pi * 2 * x / SIZE))
            px[y][x] = 2 + ((x + y + wob) // 2) % 4
    rnd = random.Random(7)
    # sparse crimson cooling spots
    for x, y in [(4, 3), (12, 7), (7, 11), (15, 15)]:
        px[y][x] = 1
    # one dark vein, a short wandering diagonal
    x, y = 9, 2
    for _ in range(6):
        px[y][x] = 0
        x = _wrap(x + rnd.choice((0, 1)))
        y = _wrap(y + 1)
    return px


def speckle_layer(shift, frame):
    """Returns {(x, y): index} for the speckle clusters at the given horizontal drift and bob frame."""
    out = {}
    for r, (ry, blobs) in enumerate(ROWS):
        bob = BOB[frame % 4] * (-1 if r % 2 else 1)
        for bx, rad, ph in blobs:
            cx, cy = bx + shift, ry + bob
            for dy in range(-rad, rad + 1):
                for dx in range(-rad, rad + 1):
                    d2 = dx * dx + dy * dy
                    if d2 > rad * rad + (1 if rad > 1 else 0):
                        continue
                    p = (_wrap(cx + dx), _wrap(cy + dy))
                    if d2 == 0:
                        out[p] = 14 if rad > 1 and ph % 2 == 0 else 10 + (ph % 4)
                    elif d2 <= 1 and rad > 1:
                        out[p] = 10 + ((ph + dx + dy) % 4)
                    else:
                        out[p] = 6 + ((ph + dx + 2 * dy) % 4)
    return out


def frames():
    """NUM_FRAMES lists of 16 rows x 16 indices."""
    base = base_layer()
    result = []
    for f in range(NUM_FRAMES):
        px = [row[:] for row in base]
        for (x, y), v in speckle_layer(f, f).items():
            px[y][x] = v
        result.append(px)
    return result


def texels_4bpp(px):
    """DS format 3: 2 texels per byte, left texel in the low nibble."""
    out = bytearray()
    for row in px:
        for x in range(0, SIZE, 2):
            out.append(row[x] | (row[x + 1] << 4))
    return bytes(out)


def cycled_palette(vblank):
    pal = list(PALETTE)
    for first, n, period in CYCLES:
        r = vblank // period
        for i in range(n):
            pal[first + i] = PALETTE[first + (i + r) % n]
    return pal


def main():
    from PIL import Image

    out_dir = os.environ.get("OUT_DIR", "/tmp/coronet_lava")
    os.makedirs(out_dir, exist_ok=True)
    fr = frames()
    flat_pal = [c for rgb in PALETTE for c in rgb]

    im = Image.new("P", (SIZE, SIZE))
    im.putpalette(flat_pal)
    im.putdata([v for row in fr[0] for v in row])
    im.save(os.path.join(out_dir, "lava_tile.png"), bits=4)

    with open(os.path.join(out_dir, "lava.pal"), "w", newline="\r\n") as f:
        f.write("JASC-PAL\n0100\n16\n")
        for r, g, b in PALETTE:
            f.write(f"{r} {g} {b}\n")

    with open(os.path.join(out_dir, "lava_frames.bin"), "wb") as f:
        for px in fr:
            f.write(texels_4bpp(px))

    # preview: 6 s at 10 fps, one GIF frame per texel-frame swap
    tiles_x, tiles_y, scale = 8, 5, 3
    gif = []
    for step in range(60):
        vb = step * FRAME_VBLANKS
        pal = cycled_palette(vb)
        px = fr[step % NUM_FRAMES]
        tile = Image.new("RGB", (SIZE, SIZE))
        tile.putdata([pal[v] for row in px for v in row])
        big = Image.new("RGB", (SIZE * tiles_x, SIZE * tiles_y))
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                big.paste(tile, (tx * SIZE, ty * SIZE))
        gif.append(big.resize((big.width * scale, big.height * scale), Image.NEAREST))
    gif[0].save(os.path.join(out_dir, "lava_preview.gif"), save_all=True, append_images=gif[1:],
                duration=1000 * FRAME_VBLANKS // 60, loop=0)
    gif[0].save(os.path.join(out_dir, "lava_preview_frame0.png"))
    print(f"wrote lava_tile.png, lava.pal, lava_frames.bin, lava_preview.gif to {out_dir}")


if __name__ == "__main__":
    main()

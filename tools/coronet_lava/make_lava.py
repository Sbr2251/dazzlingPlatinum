"""Lava art for Mt. Coronet 1F South (texture set 074). See docs/coronet_1f_lava/PLAN.md, Step 1.

Usage: python3 tools/coronet_lava/make_lava.py  (needs Pillow; writes to $OUT_DIR, default /tmp/coronet_lava)

Outputs:
  lava_tile.png      frame 0, 16x16 indexed
  lava.pal           JASC-PAL, 16 colours
  lava_frames.bin    NUM_FRAMES x 128 bytes of 4bpp texels (DS format 3, low nibble = left texel)
  lava_preview.gif   tiled lava pool with its shore rim, reference only

The lava is a tileable cellular pattern: yellow-orange cells split by red-orange channels, as in
LavaArtDirection.jpeg. Cell seeds orbit their home point and cell heat pulses, so the pool churns in place.
The shore rim (dun_sside, palette seaside3) is a jagged crust with a molten lower edge that meets the lava.

Other scripts import palette(), frames(), texels_4bpp(), shore_palette() and shore_texels() from here.
"""
import math
import os
import random

SIZE = 16
NUM_FRAMES = 16
FRAME_VBLANKS = 7

PALETTE = [
    (176, 30, 12),   # 0-2 channels between cells
    (204, 38, 14),
    (228, 50, 15),
    (240, 70, 17),   # 3-5 orange cell rims
    (246, 92, 19),
    (250, 116, 22),
    (252, 140, 28),  # 6-9 yellow-orange cell bodies
    (254, 164, 38),
    (255, 186, 56),
    (255, 206, 84),
    (255, 224, 124), # 10-11 hot cores and flecks
    (255, 242, 184),
    (255, 250, 220), # 12-15 unused
    (255, 250, 220),
    (255, 250, 220),
    (255, 250, 220),
]

# Cell seeds: (x, y, heat). Heat shifts a cell's colours; cooler cells stay orange, hot ones go yellow.
SEEDS = [(3.0, 2.5, 1.0), (10.5, 2.0, 0.2), (14.0, 8.5, 0.8), (6.0, 8.0, -0.1), (2.0, 13.0, 0.5),
         (9.5, 13.0, 1.1)]
ORBIT = 1.2  # seed orbit radius in texels over the 16-frame loop


def palette():
    return list(PALETTE)


def bgr555(c):
    r, g, b = c
    return (r >> 3) | (g >> 3) << 5 | (b >> 3) << 10


def _torus_d2(ax, ay, bx, by):
    dx = abs(ax - bx) % SIZE
    dy = abs(ay - by) % SIZE
    dx, dy = min(dx, SIZE - dx), min(dy, SIZE - dy)
    return dx * dx + dy * dy


def lava_frame(f):
    rnd = random.Random(11)
    phases = [rnd.random() * 2 * math.pi for _ in SEEDS]
    spin = [rnd.choice((-1, 1)) for _ in SEEDS]
    a = 2 * math.pi * f / NUM_FRAMES
    seeds = []
    for (x, y, heat), ph, s in zip(SEEDS, phases, spin):
        seeds.append((x + ORBIT * math.cos(s * a + ph), y + ORBIT * math.sin(s * a + ph),
                      heat + 0.6 * math.sin(a + ph)))
    px = [[0] * SIZE for _ in range(SIZE)]
    for y in range(SIZE):
        for x in range(SIZE):
            cx, cy = x + 0.5, y + 0.5
            d = sorted((_torus_d2(cx, cy, sx, sy), h) for sx, sy, h in seeds)
            f1, heat = math.sqrt(d[0][0]), d[0][1]
            edge = math.sqrt(d[1][0]) - f1  # 0 on the boundary between two cells
            v = 1.2 * edge + 0.9 * heat - 0.25 * f1 + 1.4
            if edge < 0.45:
                v = min(v, 1.0 + edge * 2)
            px[y][x] = max(0, min(11, round(v)))
    return px


def frames():
    """NUM_FRAMES lists of 16 rows x 16 indices."""
    return [lava_frame(f) for f in range(NUM_FRAMES)]


# Shore rim. Texture rows run from the floor side (row 0) down to the lava (row 15). Index 0 is transparent.
SHORE_PALETTE = [
    None,            # 0 transparent, keeps the stock colour
    (22, 14, 20),    # 1-4 crust, dark to lava-lit
    (38, 24, 30),
    (60, 34, 36),
    (96, 46, 38),
    (138, 58, 34),   # 5 lit crust edge
    (120, 28, 16),   # 6-9 glowing cracks, dim to hot
    (184, 46, 16),
    (236, 96, 22),
    (255, 176, 60),
    (176, 30, 12),   # 10-13 molten edge, same reds as the lava channels and rims
    (204, 38, 14),
    (228, 50, 15),
    (246, 92, 19),
    (72, 26, 28),    # 14-15 heated crust
    (104, 34, 26),
]


def shore_palette(stock0):
    return [stock0] + SHORE_PALETTE[1:]


def shore_texels():
    """16 rows x 16 indices for dun_sside, tileable along x."""
    rnd = random.Random(23)
    # crust chunks: split the 16 columns into irregular widths, each chunk with its own top height
    widths, x = [], 0
    while x < SIZE:
        w = min(rnd.choice((3, 4, 5, 6)), SIZE - x)
        widths.append(w)
        x += w
    top, seam, chunk_of = [], [], []
    for i, w in enumerate(widths):
        t = rnd.choice((1, 2, 2, 3))
        m = rnd.choice((11, 12, 12, 13))
        for j in range(w):
            top.append(t + (1 if j == 0 or j == w - 1 else 0) * rnd.choice((0, 1)))
            seam.append(m + rnd.choice((-1, 0, 0, 1)))
            chunk_of.append((i, j, w))
    px = [[0] * SIZE for _ in range(SIZE)]
    for x in range(SIZE):
        i, j, w = chunk_of[x]
        for y in range(SIZE):
            t = (y - top[x]) / max(1, seam[x] - top[x])
            if y < top[x]:
                v = 0
            elif j == 0 and y > top[x] + 1 and y < seam[x]:
                v = 1 if t < 0.5 else 14  # gap between chunks
            elif y == top[x]:
                v = 5 if j < w - 1 else 4
            elif y == top[x] + 1:
                v = 4 if j < w // 2 + 1 else 3
            elif y < seam[x]:
                v = rnd.choice((2, 3, 3) if t < 0.45 else (3, 14, 14) if t < 0.75 else (14, 15, 15))
            elif y == seam[x]:
                v = rnd.choice((7, 8, 8, 9))
            else:
                v = rnd.choice((13, 12)) if y == seam[x] + 1 else rnd.choice((10, 11, 11, 12))
            px[y][x] = v
    # glowing cracks running down from the chunk gaps into the seam
    for x in range(SIZE):
        i, j, w = chunk_of[x]
        if j == 0:
            for y in range(seam[x] - 3, seam[x]):
                px[y][x] = 6 if y < seam[x] - 1 else 7
    return px


def texels_4bpp(px):
    """DS format 3: 2 texels per byte, left texel in the low nibble."""
    out = bytearray()
    for row in px:
        for x in range(0, SIZE, 2):
            out.append(row[x] | (row[x + 1] << 4))
    return bytes(out)


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

    # preview: a pool of lava tiles under one row of shore rim, on a dark floor
    tiles_x, tiles_y, scale = 8, 5, 3
    spal = shore_palette((56, 44, 54))
    rim = shore_texels()
    rim_tile = Image.new("RGB", (SIZE, SIZE))
    rim_tile.putdata([spal[v] for row in rim for v in row])
    gif = []
    for f in range(NUM_FRAMES):
        tile = Image.new("RGB", (SIZE, SIZE))
        tile.putdata([PALETTE[v] for row in fr[f] for v in row])
        big = Image.new("RGB", (SIZE * tiles_x, SIZE * (tiles_y + 1)))
        for tx in range(tiles_x):
            big.paste(rim_tile, (tx * SIZE, 0))
            for ty in range(tiles_y):
                big.paste(tile, (tx * SIZE, (ty + 1) * SIZE))
        gif.append(big.resize((big.width * scale, big.height * scale), Image.NEAREST))
    gif[0].save(os.path.join(out_dir, "lava_preview.gif"), save_all=True, append_images=gif[1:],
                duration=1000 * FRAME_VBLANKS // 60, loop=0)
    gif[0].save(os.path.join(out_dir, "lava_preview_frame0.png"))
    print(f"wrote lava_tile.png, lava.pal, lava_frames.bin, lava_preview.gif to {out_dir}")


if __name__ == "__main__":
    main()

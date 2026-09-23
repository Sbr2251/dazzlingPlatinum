"""Lava mock for Mt. Coronet 1F South: recolours the map screenshot in docs/coronet_1f_lava/.

Usage: python3 tools/coronet_lava/make_mock.py  (needs Pillow; writes to $OUT_DIR, default /tmp/coronet_lava)
"""
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import os

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.join(HERE, "..", "..", "docs", "coronet_1f_lava")
OUT = os.environ.get("OUT_DIR", "/tmp/coronet_lava")
os.makedirs(OUT, exist_ok=True)
src = Image.open(f"{MR}/mtcoronetsouth.png").convert("RGB")
W, H = src.size
SP = src.load()


def is_water(c):
    return c[1] > c[0] + 40 and c[2] > c[0] + 40


def keep(c):
    # labels, blue "[A]", warp glows, Poke Ball red
    r, g, b = c
    if c == (255, 255, 255) or (b > 200 and r < 60 and g < 60):
        return True
    if r >= g + 40 and r > b + 10:
        return True
    return False


def lum(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def ramp(t, stops):
    t = max(0.0, min(1.0, t))
    f = t * (len(stops) - 1)
    i = min(int(f), len(stops) - 2)
    u = f - i
    a, b = stops[i], stops[i + 1]
    return tuple(int(a[k] + (b[k] - a[k]) * u) for k in range(3))


# palettes sampled from the art-direction screenshot: near-black slate cliffs, dark brown floor
CLIFF = [(10, 9, 14), (22, 20, 28), (38, 35, 46), (58, 54, 68), (88, 82, 98)]
FLOOR = [(26, 20, 22), (40, 32, 33), (54, 44, 44), (66, 54, 52), (84, 70, 66)]


def lava_tile(n=32, seed=3):
    """Tileable cellular lava: yellow-orange blobs separated by red-orange veins."""
    rnd = random.Random(seed)
    pts = [(rnd.uniform(0, n), rnd.uniform(0, n)) for _ in range(14)]
    im = Image.new("RGB", (n, n))
    p = im.load()
    for y in range(n):
        for x in range(n):
            ds = []
            for px, py in pts:
                dx = min(abs(x - px), n - abs(x - px))
                dy = min(abs(y - py), n - abs(y - py))
                ds.append((dx * dx + dy * dy) ** 0.5)
            ds.sort()
            edge = ds[1] - ds[0]          # 0 on a vein, larger toward a blob centre
            if edge < 0.9:
                c = (196, 52, 14)
            elif edge < 2.0:
                c = (236, 104, 22)
            elif edge < 3.4:
                c = (250, 150, 34)
            else:
                c = (255, 206, 72)
            p[x, y] = c
    # sparse hot flecks, like the sample's bright pixels
    for _ in range(10):
        p[rnd.randrange(n), rnd.randrange(n)] = (255, 244, 170)
    return im


LAVA = lava_tile()
LP = LAVA.load()

water = [[is_water(SP[x, y]) for x in range(W)] for y in range(H)]

# cooled-basalt causeways so nothing that needed Surf is cut off
# north pool (x 119-272, y 101-129): bottom row becomes a crust path from the west shore to the east shore
# south lake (x 263-415, y 352-393): bottom row becomes a crust path to the Poke Ball in the far corner
CAUSE = [(119, 116, 273, 130), (263, 378, 416, 394)]


def in_cause(x, y):
    return any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in CAUSE)


out = Image.new("RGB", (W, H))
OP = out.load()
for y in range(H):
    for x in range(W):
        c = SP[x, y]
        if water[y][x]:
            OP[x, y] = LP[x % 32, y % 32]
        elif keep(c):
            OP[x, y] = c
        elif c == (6, 1, 67):
            OP[x, y] = (8, 6, 12)
        elif lum(c) > 130:
            OP[x, y] = c  # warp glow
        else:
            t = lum(c) / 115.0
            OP[x, y] = ramp(t, FLOOR if c[2] - c[0] >= 20 else CLIFF)

# red-hot rim where lava meets rock (1px, like the sample's hard lava edge)
for y in range(1, H - 1):
    for x in range(1, W - 1):
        if water[y][x] and not all(water[y + dy][x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            OP[x, y] = (150, 30, 10)

# causeways: copy recoloured floor texture, with a dark lip and a thin glowing seam on the lava side
floor_patch = out.crop((70, 170, 102, 202))
d = ImageDraw.Draw(out)
for x0, y0, x1, y1 in CAUSE:
    for yy in range(y0, y1, 32):
        for xx in range(x0, x1, 32):
            out.paste(floor_patch.crop((0, 0, min(32, x1 - xx), min(32, y1 - yy))), (xx, yy))
    d.line([x0, y0, x1 - 1, y0], fill=(255, 150, 40))
    d.line([x0, y0 + 1, x1 - 1, y0 + 1], fill=(20, 14, 16))
    for xx in range(x0 + 6, x1 - 4, 11):
        d.point((xx, y0 + 4 + (xx * 7) % 7), fill=(120, 40, 20))

# faint warm reflection on rock right next to the lava (the sample keeps glow tight)
mask = Image.new("L", (W, H), 0)
mp = mask.load()
for y in range(H):
    for x in range(W):
        if water[y][x] and not in_cause(x, y):
            mp[x, y] = 255
halo = mask.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(3))
hp = halo.load()
for y in range(H):
    for x in range(W):
        if not water[y][x] or in_cause(x, y):
            a = hp[x, y] / 255 * 0.28
            if a > 0.01 and not keep(SP[x, y]):
                r, g, b = OP[x, y]
                OP[x, y] = (int(r + (255 - r) * a), int(g + (110 - g) * a * 0.6), int(b * (1 - a)))

out.save(f"{OUT}/south_after.png")

# ---- review sheet ----
def font(size):
    for f in ("/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


F, FB, FS = font(15), font(22), font(12)


def label(dd, xy, s, fill=(255, 255, 255), font=FS):
    dd.text((xy[0] + 1, xy[1] + 1), s, fill=(0, 0, 0), font=font)
    dd.text(xy, s, fill=fill, font=font)


pad = 24
ref = Image.open(f"{MR}/LavaArtDirection.jpeg").convert("RGB")
ref = ref.resize((W * 2 // 3, ref.size[1] * (W * 2 // 3) // ref.size[0]))
zoom = out.crop((90, 60, 346, 252)).resize((512, 384), Image.NEAREST)
zoom2 = out.crop((250, 210, 506, 402)).resize((512, 384), Image.NEAREST)
SW = pad * 3 + W * 2
SH = 60 + 22 + H + 40 + 22 + 384 + 40 + 22 + ref.size[1] + 200
sheet = Image.new("RGB", (SW, SH), (18, 12, 16))
d = ImageDraw.Draw(sheet)
label(d, (pad, 18), "Mt. Coronet 1F South (Route 207 / Route 208)  -  Lava theme mock v2", font=FB)
y = 60
label(d, (pad, y), "CURRENT", fill=(170, 200, 255), font=F)
label(d, (pad * 2 + W, y), "PROPOSED: Magma cavern", fill=(255, 170, 90), font=F)
y += 22
sheet.paste(src, (pad, y))
ax = pad * 2 + W
sheet.paste(out, (ax, y))
label(d, (ax + 150, y + 131), "cooled basalt path (was Surf)", fill=(255, 240, 200))
label(d, (ax + 272, y + 394 - 30), "basalt path to the item", fill=(255, 240, 200))
y += H + 12
label(d, (pad, y), "All four pools become lava. Layout, ledges, Rock Climb, stairs, Rock Smash rocks, trainers and items are unchanged.", fill=(200, 190, 210))
y += 30
label(d, (pad, y), "CLOSE-UP, 2x  (north lava pool + causeway | south lake + Route 208)", font=F)
y += 22
sheet.paste(zoom, (pad, y))
sheet.paste(zoom2, (pad * 2 + W, y))
y += 384 + 20
label(d, (pad, y), "ART DIRECTION (your reference)", font=F)
y += 22
sheet.paste(ref, (pad, y))
nx = pad * 2 + ref.size[0]
notes = [
    "What I took from the reference",
    "- Near-black slate cliffs with lighter ridges, dark brown floor",
    "- Lava is bright orange with yellow blobs and red veins, hard edge,",
    "  little bloom - the light stays on the lava itself",
    "- Tight warm reflection only on rock touching the lava",
    "",
    "Implementation",
    "- New texture set + area data used only by this map, so 2F, 3F,",
    "  B1F, North rooms and the Iceberg Ruins keep the normal look",
    "- Water tiles -> animated lava (blobs cycle via texture animation)",
    "- Lava can't be surfed: two basalt paths keep the ledge / Rock",
    "  Climb / [A] stairs route and the far Poke Ball reachable",
    "- Optional: fire-type encounters (Slugma, Numel, Magmar,",
    "  Houndour, Torkoal)",
]
for i, s in enumerate(notes):
    hdr = s in ("What I took from the reference", "Implementation")
    label(d, (nx, y + i * 19), s, fill=(255, 200, 150) if hdr else (230, 220, 235), font=F if hdr else FS)
y += max(ref.size[1], len(notes) * 19) + 20
sheet.crop((0, 0, SW, y)).save(f"{OUT}/coronet_1f_south_lava_mock_v2.png")
print(sheet.size, y)

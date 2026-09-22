#!/usr/bin/env python3
"""Generate the Distortion World top screen for the Giratina title.

Writes res/graphics/title_screen/logo.png (256x192, 8bpp indexed) and
res/graphics/title_screen/logo.NSCR (256x256 8bpp tilemap). The logo layer
becomes a full-screen opaque image that covers the stock border layers.

Palette layout (must match title_screen.c):
    0            transparent key (never used by a pixel)
    1..191       general colours
    192..239     "DAZZLING PLATINUM" letters: 8 diagonal bands x 6 tones,
                 index = 192 + band * 6 + tone, so the C code can sweep a shine
                 across the bands by editing the palette
    240..255     unused

Needs PIL (/usr/bin/python3 on macOS) and Arial Black from the macOS
supplemental fonts. The POKEMON wordmark comes from assets/pokemon_wordmark.png,
extracted from the original logo.png.

Usage: python3 make_top_screen.py [--preview out.png]
"""

import argparse
import math
import os
import random
import struct

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(REPO, "res", "graphics", "title_screen")
WORDMARK = os.path.join(HERE, "assets", "pokemon_wordmark.png")
FONT = "/System/Library/Fonts/Supplemental/Arial Black.ttf"

W, H = 256, 192
SS = 4  # supersample factor for vector elements

GENERAL_COLORS = 191
PLAT_BASE = 192
PLAT_BANDS = 8
PLAT_TONES = 6

SKY_TOP = (9, 0, 12)
SKY_BOTTOM = (30, 0, 22)  # matches the top edge of the bottom-screen sky

rng = random.Random(7)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(len(a)))


def sky():
    im = Image.new("RGBA", (W, H))
    px = im.load()
    for y in range(H):
        c = lerp(SKY_TOP, SKY_BOTTOM, (y / (H - 1)) ** 0.8)
        for x in range(W):
            d = math.hypot((x - 128) / 150.0, (y - 70) / 70.0)
            g = max(0.0, 1.0 - d) ** 2
            px[x, y] = lerp(c, (60, 14, 70), g * 0.55) + (255,)
    for _ in range(38):
        x, y = rng.randrange(W), rng.randrange(18, H - 30)
        b = rng.choice([70, 90, 120, 170])
        px[x, y] = (b, int(b * 0.75), b, 255)
    for x, y in [(22, 40), (230, 58), (212, 132), (40, 128)]:
        for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]:
            px[x + dx, y + dy] = (200, 170, 230, 255) if (dx, dy) == (0, 0) else (110, 80, 140, 255)
    return im


def island(draw, cx, top, w, depth, seed):
    r = random.Random(seed)
    n = 9
    pts_top = [(cx - w / 2 + w * i / n, top + r.uniform(-1.5, 1.0)) for i in range(n + 1)]
    under = []
    m = 12
    for i in range(m, -1, -1):
        x = cx - w / 2 + w * i / m
        u = max(0.0, 1 - abs((x - cx) / (w / 2))) ** 0.9
        under.append((x, top + 2 + depth * u * r.uniform(0.7, 1.0)))
    draw.polygon([(x * SS, y * SS) for x, y in pts_top + under], fill=(20, 6, 28, 255))
    draw.line([(x * SS, y * SS) for x, y in pts_top], fill=(96, 50, 150, 255), width=SS)
    for _ in range(2 if w > 20 else 0):
        x = cx + r.uniform(-w * 0.3, w * 0.3)
        hgt = r.uniform(5, 9)
        draw.line([(x * SS, top * SS), (x * SS, (top - hgt) * SS)], fill=(6, 0, 8, 255), width=SS)
        draw.line([(x * SS, (top - hgt * 0.6) * SS), ((x + 3) * SS, (top - hgt) * SS)], fill=(6, 0, 8, 255), width=SS // 2)
    for _ in range(2):
        x = cx + r.uniform(-w * 0.3, w * 0.3)
        y0 = top + depth * 0.5
        draw.polygon([((x - 2) * SS, y0 * SS), ((x + 2) * SS, y0 * SS), (x * SS, (y0 + depth * 0.6) * SS)], fill=(20, 6, 28, 255))
    right = [(x, y) for x, y in under if x > cx]
    draw.line([(x * SS, y * SS) for x, y in right], fill=(70, 34, 110, 255), width=SS)


def border(draw, y_edge, down, seed):
    r = random.Random(seed)
    pts = []
    x = 0
    while x <= W:
        pts.append((x, y_edge + (r.uniform(0, 6) if down else -r.uniform(0, 6))))
        x += r.uniform(6, 16)
    pts.append((W, pts[-1][1]))
    edge = 0 if down else H
    poly = [(0, edge)] + pts + [(W, edge)]
    draw.polygon([(x * SS, y * SS) for x, y in poly], fill=(4, 0, 6, 255))
    draw.line([(x * SS, y * SS) for x, y in pts], fill=(120, 70, 170, 255), width=SS)
    inner = [(x, y + (2 if down else -2)) for x, y in pts]
    draw.line([(x * SS, y * SS) for x, y in inner], fill=(40, 12, 58, 255), width=SS)


def pokemon_wordmark():
    mark = Image.open(WORDMARK).convert("RGBA")
    px = mark.load()
    for y in range(mark.height):
        for x in range(mark.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            # The original was drawn over white with a red colour key; recolour
            # the white rim and the pink key fringe to the dark outline colour.
            if (r > 190 and g > 190 and b > 190) or (r > g + 40 and r > b + 30 and g < 150):
                px[x, y] = (10, 6, 30, 255)
    return mark.crop(mark.getbbox())


def outline(img, color, radius):
    grown = img.split()[3].filter(ImageFilter.MaxFilter(radius * 2 + 1))
    base = Image.new("RGBA", img.size, color + (0,))
    base.putalpha(grown)
    base.alpha_composite(img)
    return base


def glow(img, color, radius, strength):
    a = img.split()[3].filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(radius))
    a = a.point(lambda v: min(255, int(v * strength)))
    g = Image.new("RGBA", img.size, color + (0,))
    g.putalpha(a)
    return g


def platinum_text(text, size, tracking):
    font = ImageFont.truetype(FONT, size * SS)
    widths = [font.getbbox(ch)[2] - font.getbbox(ch)[0] for ch in text]
    total = sum(widths) + tracking * SS * (len(text) - 1)
    asc, desc = font.getmetrics()
    mask = Image.new("L", (total + 8 * SS, asc + desc + 8 * SS), 0)
    d = ImageDraw.Draw(mask)
    x = 4 * SS
    for ch, w in zip(text, widths):
        d.text((x - font.getbbox(ch)[0], 4 * SS), ch, font=font, fill=255)
        x += w + tracking * SS
    mask = mask.crop(mask.getbbox())
    mw, mh = mask.size
    fill = Image.new("RGBA", (mw, mh))
    fp = fill.load()
    for y in range(mh):
        t = y / max(1, mh - 1)
        if t < 0.45:
            c = lerp((255, 255, 255), (214, 216, 228), t / 0.45)
        elif t < 0.52:
            c = (170, 172, 190)
        else:
            c = lerp((196, 190, 222), (150, 132, 196), (t - 0.52) / 0.48)
        for x in range(mw):
            fp[x, y] = c + (255,)
    fill.putalpha(mask)
    return fill.resize((max(1, mw // SS), max(1, mh // SS)), Image.LANCZOS)


def sparkle(draw, x, y, r):
    draw.line([(x - r, y), (x + r, y)], fill=(255, 255, 255, 255))
    draw.line([(x, y - r), (x, y + r)], fill=(255, 255, 255, 255))
    draw.point([(x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1), (x + 1, y + 1)], fill=(200, 190, 255, 255))


def compose():
    """Returns (rgb image, platinum mask {(x, y): band}) for the top screen."""
    base = sky()

    layer = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # Floating islands, kept clear of the "Press Start" strip (y 152-167, x 40-216)
    island(d, 22, 146, 46, 34, 1)
    island(d, 236, 150, 38, 28, 2)
    island(d, 200, 140, 14, 12, 3)
    island(d, 52, 124, 10, 9, 4)
    border(d, 9, True, 11)
    border(d, H - 7, False, 12)
    base.alpha_composite(layer.resize((W, H), Image.LANCZOS))

    # POKEMON wordmark with a dark outline and a violet glow
    mark = outline(pokemon_wordmark(), (10, 6, 30), 1)
    pad = 8
    padded = Image.new("RGBA", (mark.width + pad * 2, mark.height + pad * 2), (0, 0, 0, 0))
    padded.alpha_composite(mark, (pad, pad))
    mx = (W - padded.width) // 2
    my = 0
    base.alpha_composite(glow(padded, (150, 70, 255), 4, 1.1), (mx, my))
    base.alpha_composite(padded, (mx, my))
    mark_bottom = my + pad + mark.height

    # DAZZLING / PLATINUM in brushed platinum
    plat_alpha = Image.new("L", (W, H), 0)
    dz_fill = platinum_text("DAZZLING", 28, 1)
    pl_fill = platinum_text("PLATINUM", 14, 4)
    dy = mark_bottom + 2
    pl_y = dy + dz_fill.height + 6
    for fill, y in [(dz_fill, dy), (pl_fill, pl_y)]:
        full = outline(fill, (14, 8, 34), 2)
        p = Image.new("RGBA", (full.width + 12, full.height + 12), (0, 0, 0, 0))
        p.alpha_composite(full, (6, 6))
        x = (W - p.width) // 2
        base.alpha_composite(glow(p, (120, 60, 220), 3, 0.9), (x, y - 6))
        base.alpha_composite(p, (x, y - 6))
        plat_alpha.paste(fill.split()[3], (x + 6 + 2, y + 2))
    red_y = pl_y + pl_fill.height + 4

    # Giratina-red accent line under PLATINUM, fading at the ends
    half = 58
    for i in range(-half, half + 1):
        t = 1 - abs(i) / half
        a = int(255 * min(1, t * 2.2))
        c = lerp((40, 0, 12), (214, 18, 22), min(1, t * 1.6))
        base.alpha_composite(Image.new("RGBA", (1, 1), c + (a,)), (128 + i, red_y))
        base.alpha_composite(Image.new("RGBA", (1, 1), (170, 10, 16, a)), (128 + i, red_y + 1))

    # Sparkle glints on the letters
    spark = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(spark)
    sparkle(ds, 62, dy + 4, 3)
    sparkle(ds, 178, dy + 14, 2)
    sparkle(ds, 194, pl_y + 3, 2)
    base.alpha_composite(spark)

    # Platinum letter pixels (not outline, not sparkles) get the band indices
    pa = plat_alpha.load()
    sa = spark.split()[3].load()
    xs = [x for y in range(H) for x in range(W) if pa[x, y] >= 128]
    ys = [y for y in range(H) for x in range(W) if pa[x, y] >= 128]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    span = (x1 - x0) + (y1 - y0) * 0.6 + 1
    plat = {}
    for y in range(H):
        for x in range(W):
            if pa[x, y] >= 128 and sa[x, y] == 0:
                band = int(((x - x0) + (y - y0) * 0.6) / span * PLAT_BANDS)
                plat[(x, y)] = min(PLAT_BANDS - 1, max(0, band))
    return base.convert("RGB"), plat


BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def to555(c, x, y):
    """8-bit RGB -> 5-bit RGB with 4x4 ordered dithering."""
    t = (BAYER4[y & 3][x & 3] + 0.5) / 16.0
    return tuple(min(31, int(v / 255.0 * 31 + t)) for v in c)


def build_indexed(rgb, plat):
    px = rgb.load()

    # Platinum letters: 6 tones by luminance, same colours in every band
    lum = {p: sum(px[p]) / 3.0 for p in plat}
    lo, hi = min(lum.values()), max(lum.values())
    tone_of = {p: min(PLAT_TONES - 1, int((lum[p] - lo) / (hi - lo + 1e-6) * PLAT_TONES)) for p in plat}
    sums = [[0, 0, 0, 0] for _ in range(PLAT_TONES)]
    for p, t in tone_of.items():
        c = px[p]
        for i in range(3):
            sums[t][i] += c[i]
        sums[t][3] += 1
    tone_col = []
    for t in range(PLAT_TONES):
        s = sums[t]
        n = max(1, s[3])
        tone_col.append(tuple(int(round(s[i] / n / 255.0 * 31)) for i in range(3)))

    # Everything else: dithered 5-bit, then median cut if it needs more than 191
    g5 = {}
    for y in range(H):
        for x in range(W):
            if (x, y) not in plat:
                g5[(x, y)] = to555(px[x, y], x, y)
    uniq = sorted(set(g5.values()))
    if len(uniq) > GENERAL_COLORS:
        tmp = Image.new("RGB", (len(g5), 1))
        tmp.putdata([tuple(v * 8 for v in c) for c in g5.values()])
        q = tmp.quantize(GENERAL_COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        qpal = q.getpalette()[: GENERAL_COLORS * 3]
        general = [tuple(min(31, round(qpal[i * 3 + k] / 8)) for k in range(3)) for i in range(GENERAL_COLORS)]
        qd = list(q.getdata())
        gidx = {p: 1 + qd[i] for i, p in enumerate(g5.keys())}
    else:
        general = uniq
        lut = {c: 1 + i for i, c in enumerate(uniq)}
        gidx = {p: lut[c] for p, c in g5.items()}

    pal = [(31, 0, 31)] + list(general)
    pal += [(0, 0, 0)] * (PLAT_BASE - len(pal))
    for b in range(PLAT_BANDS):
        pal += tone_col
    pal += [(0, 0, 0)] * (256 - len(pal))
    assert len(pal) == 256

    idx = Image.new("P", (W, H), 0)
    ip = idx.load()
    for y in range(H):
        for x in range(W):
            p = (x, y)
            ip[x, y] = PLAT_BASE + plat[p] * PLAT_TONES + tone_of[p] if p in plat else gidx[p]
    flat = []
    for c in pal:
        flat += [v * 255 // 31 for v in c]
    idx.putpalette(flat)
    idx.info["transparency"] = 0
    return idx, len(uniq)


def write_nscr(path):
    entries = []
    for row in range(32):
        src = min(row, 23)  # rows past the screen repeat the last row
        entries += [src * 32 + col for col in range(32)]
    data = struct.pack("<1024H", *entries)
    nrcs = b"NRCS" + struct.pack("<IHHHHI", 0x14 + len(data), 256, 256, 1, 0, len(data)) + data
    hdr = b"RCSN" + struct.pack("<HHIHH", 0xFEFF, 0x0100, 0x10 + len(nrcs), 0x10, 1)
    with open(path, "wb") as f:
        f.write(hdr + nrcs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", help="also write a 3x RGB preview of the decoded result")
    args = ap.parse_args()

    rgb, plat = compose()
    idx, ncolors = build_indexed(rgb, plat)
    idx.save(os.path.join(OUT_DIR, "logo.png"), transparency=0)
    write_nscr(os.path.join(OUT_DIR, "logo.NSCR"))
    print(f"general colours before reduction: {ncolors}, platinum pixels: {len(plat)}")

    if args.preview:
        idx.convert("RGB").resize((W * 3, H * 3), Image.NEAREST).save(args.preview)


if __name__ == "__main__":
    main()

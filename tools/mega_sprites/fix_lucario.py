#!/usr/bin/env python3
# Rebuilds the Mega Lucario battle sprites (front.png, back.png, normal.pal,
# shiny.pal in res/pokemon/lucario/forms/mega/) from the Gen 5-style sprites
# by the Smogon Sprite Project, as hosted by Pokemon Showdown:
#   https://play.pokemonshowdown.com/sprites/gen5/lucario-mega.png
#   https://play.pokemonshowdown.com/sprites/gen5-back/lucario-mega.png
#   https://play.pokemonshowdown.com/sprites/gen5-shiny/lucario-mega.png
#
# The 96x96 sources are cropped (not scaled) into the 80x80 DS frame, placed
# where the base Lucario sprites sit, and reduced to one 16-colour palette
# shared by the front and back. The shiny palette is read from the shiny front,
# which is the same drawing as the normal front.
#
# Usage: ~/.venvs/desmume/bin/python tools/mega_sprites/fix_lucario.py [srcdir]
# srcdir holds gen5.png, gen5-back.png and gen5-shiny.png; they are downloaded
# into it when missing.

import os
import sys
import urllib.request
from collections import Counter

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, 'res', 'pokemon', 'lucario', 'forms', 'mega')
URL = 'https://play.pokemonshowdown.com/sprites/{}/lucario-mega.png'
SOURCES = ['gen5', 'gen5-back', 'gen5-shiny']

FRAME = 80
TRANSPARENT = (0, 128, 0)

# Last opaque row (exclusive) and horizontal centre, matching the base Lucario
# sprites so the Mega stands on the same spot in battle. The back stops one row
# short of the frame edge.
FRONT_BOTTOM = 70
BACK_BOTTOM = 79
CENTRE_X = 40

# Frame 2 lifts the upper body by one pixel (a breath); rows below this
# fraction of the figure height stay put so the feet don't move.
BREATH_SPLIT = 0.6


def load_sources(src_dir):
    images = {}
    for name in SOURCES:
        path = os.path.join(src_dir, name + '.png')
        if not os.path.exists(path):
            os.makedirs(src_dir, exist_ok=True)
            urllib.request.urlretrieve(URL.format(name), path)
        images[name] = Image.open(path).convert('RGBA')
    return images


def place(image, bottom):
    """Crops the figure into an 80x80 RGBA frame, bottom-aligned and centred."""
    left, top, right, low = image.getbbox()
    width, height = right - left, low - top
    if width > FRAME or height > FRAME:
        sys.exit(f'figure is {width}x{height}, larger than the {FRAME}x{FRAME} frame')

    frame = Image.new('RGBA', (FRAME, FRAME), (0, 0, 0, 0))
    x = CENTRE_X - width // 2
    y = bottom - height
    frame.paste(image.crop((left, top, right, low)), (x, y))
    return frame


def colour_distance(a, b):
    # Weighted RGB distance; close enough to perceptual for picking palette slots.
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return 2 * dr * dr + 4 * dg * dg + 3 * db * db


def opaque_colours(image):
    pixels = image.load()
    return Counter(pixels[x, y][:3] for y in range(image.height) for x in range(image.width) if pixels[x, y][3] >= 128)


def build_palette(front, back):
    """Every front colour, plus the back-only colours that are furthest from
    them, up to 15 opaque entries."""
    front_counts = opaque_colours(front)
    palette = [c for c, _ in front_counts.most_common()]

    back_only = [(c, n) for c, n in opaque_colours(back).items() if c not in front_counts]
    while len(palette) < 15 and back_only:
        best = max(back_only, key=lambda cn: cn[1] * min(colour_distance(cn[0], p) for p in palette))
        palette.append(best[0])
        back_only.remove(best)
    return palette


def nearest(colour, palette):
    return min(range(len(palette)), key=lambda i: colour_distance(colour, palette[i]))


def to_indices(frame, palette):
    """Maps an RGBA frame onto palette indices 1-15; transparent pixels are 0."""
    out = Image.new('L', frame.size, 0)
    src = frame.load()
    dst = out.load()
    for y in range(frame.height):
        for x in range(frame.width):
            pixel = src[x, y]
            if pixel[3] >= 128:
                dst[x, y] = 1 + nearest(pixel[:3], palette)
    return out


def breath_frame(indices):
    """Frame 2: rows above the split move down one pixel; the row at the split
    is dropped so everything below it stays still."""
    bbox = indices.point(lambda v: 255 if v else 0).getbbox()
    top, low = bbox[1], bbox[3]
    split = top + int((low - top) * BREATH_SPLIT)

    out = indices.copy()
    out.paste(indices.crop((0, top, FRAME, split)), (0, top + 1))
    out.paste(0, (0, top, FRAME, top + 1))
    return out


def shiny_palette(normal_front, shiny_front, palette):
    """Majority vote of the shiny colour under each palette index, using the
    same pixel positions in the normal and shiny fronts. Entries only used by
    the back take the shift of their nearest front colour."""
    votes = [Counter() for _ in palette]
    normal = normal_front.load()
    shiny = shiny_front.load()
    for y in range(normal_front.height):
        for x in range(normal_front.width):
            n, s = normal[x, y], shiny[x, y]
            if n[3] >= 128 and s[3] >= 128:
                votes[palette.index(n[:3])][s[:3]] += 1

    result = [None] * len(palette)
    for i, counter in enumerate(votes):
        if counter:
            result[i] = counter.most_common(1)[0][0]
    voted = [i for i in range(len(palette)) if result[i] is not None]
    for i in range(len(palette)):
        if result[i] is None:
            j = min(voted, key=lambda k: colour_distance(palette[i], palette[k]))
            result[i] = tuple(max(0, min(255, s + (c - n))) for c, n, s in zip(palette[i], palette[j], result[j]))
    return result


def padded(palette):
    return palette + [(0, 0, 0)] * (15 - len(palette))


def write_png(path, frame1, frame2, palette):
    sheet = Image.new('P', (FRAME * 2, FRAME), 0)
    sheet.paste(frame1, (0, 0))
    sheet.paste(frame2, (FRAME, 0))
    flat = [v for c in [TRANSPARENT] + padded(palette) for v in c]
    sheet.putpalette(flat + [0] * (48 - len(flat)))
    sheet.save(path, bits=4, optimize=False)


def write_pal(path, palette):
    lines = ['JASC-PAL', '0100', '16'] + [f'{r} {g} {b}' for r, g, b in [TRANSPARENT] + padded(palette)]
    with open(path, 'w', newline='') as f:
        f.write('\r\n'.join(lines) + '\r\n')


def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else '/tmp/lucario_mega_src'
    images = load_sources(src_dir)

    front = place(images['gen5'], FRONT_BOTTOM)
    back = place(images['gen5-back'], BACK_BOTTOM)
    shiny_front = place(images['gen5-shiny'], FRONT_BOTTOM)

    palette = build_palette(front, back)
    shiny = shiny_palette(front, shiny_front, palette)

    for name, frame in [('front', front), ('back', back)]:
        indices = to_indices(frame, palette)
        write_png(os.path.join(OUT_DIR, name + '.png'), indices, breath_frame(indices), palette)

    write_pal(os.path.join(OUT_DIR, 'normal.pal'), palette)
    write_pal(os.path.join(OUT_DIR, 'shiny.pal'), shiny)


if __name__ == '__main__':
    main()

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
# shared by the front and back. The front keeps its 13 source colours; the
# back's olive tail is moved onto the front's tan ramp so the two match, and the
# last two slots hold the dark tan and dark red shades the back is drawn with.
# The shiny palette is read from the shiny front, which is the same drawing as
# the normal front.
#
# Frame 2 is an idle pose built by moving body parts of frame 1: the upper body
# sinks, the head sinks further, the paws spread, and the ear appendages and
# tail sway, while the feet stay planted.
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

# The back sprite draws its tail and paws with its own olive and red shades.
# They are moved onto the front's colours, plus one darker tan and one darker
# red (the back's shadow shades) which also get explicit shiny colours.
BACK_REMAP = {
    (230, 230, 156): (230, 208, 131),
    (180, 180, 98): (176, 154, 77),
    (134, 134, 64): (134, 117, 59),
    (164, 49, 49): (154, 38, 38),
}
EXTRA_SHADES = {
    # normal: shiny
    (115, 34, 34): (104, 35, 43),
    (134, 117, 59): (62, 90, 119),
}


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


def build_palette(front):
    """The front's colours, most used first, then the extra back shades."""
    palette = [c for c, _ in opaque_colours(front).most_common()]
    palette += list(EXTRA_SHADES)
    if len(palette) > 15:
        sys.exit(f'{len(palette)} colours do not fit in 15 palette slots')
    return palette


def remap_back(image):
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            if (r, g, b) in BACK_REMAP:
                pixels[x, y] = BACK_REMAP[(r, g, b)] + (a,)
    return image


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


# Frame 2 parts, in paint order. Each part lists the offset it moves by and
# the offset of the part it hangs from; it is painted at every step between
# the two, so the joint stretches instead of tearing.
FRONT_PARTS = [
    ('tail', (2, 0), (2, 0)),
    ('ears', (2, 2), (0, 1)),
    ('ear_tips', (3, 3), (2, 2)),
    ('legs', (0, 0), (0, 0)),
    ('torso', (0, 1), (0, 0)),
    ('head', (0, 2), (0, 1)),
    ('left_paw', (-2, 1), (0, 1)),
    ('right_paw', (2, 1), (0, 1)),
]
BACK_PARTS = [
    ('legs', (0, 0), (0, 0)),
    ('torso', (0, 1), (0, 0)),
    ('tail', (-2, 1), (0, 1)),
    ('tail_tip', (-3, 0), (-2, 1)),
    ('head', (0, 2), (0, 1)),
    ('left_paw', (-2, 1), (0, 1)),
    ('right_paw', (2, 1), (0, 1)),
]


def front_part(x, y, colour):
    """Which frame 2 part a front pixel belongs to (80x80 frame coordinates)."""
    tan = colour in ((176, 154, 77), (230, 208, 131))
    if 46 <= x <= 56 and 39 <= y <= 53 and not tan:
        return 'right_paw'
    if x <= 29 and 37 <= y <= 51:
        return 'left_paw'
    if (x >= 50 and 18 <= y <= 45) or (45 <= x <= 49 and 18 <= y <= 29):
        return 'ear_tips' if x >= 56 and y >= 33 else 'ears'
    if x >= 54 and 46 <= y <= 66:
        return 'tail'
    if y <= 26:
        return 'head'
    return 'torso' if y <= 52 else 'legs'


def back_part(x, y, colour):
    """Which frame 2 part a back pixel belongs to (80x80 frame coordinates)."""
    tan = colour in ((176, 154, 77), (230, 208, 131), (134, 117, 59))
    if x >= 55 and 37 <= y <= 51:
        return 'right_paw'
    if 23 <= x <= 38 and 38 <= y <= 50 and not tan:
        return 'left_paw'
    if x <= 30 and 41 <= y <= 63:
        return 'tail_tip' if x <= 22 else 'tail'
    if y <= 31:
        return 'head'
    return 'torso' if y <= 56 else 'legs'


def idle_frame(indices, palette, parts, part_of):
    src = indices.load()
    labels = {}
    for y in range(FRAME):
        for x in range(FRAME):
            if src[x, y]:
                labels.setdefault(part_of(x, y, palette[src[x, y] - 1]), []).append((x, y))

    out = Image.new('L', indices.size, 0)
    dst = out.load()
    for name, (dx, dy), (px, py) in parts:
        steps = max(abs(dx - px), abs(dy - py), 1)
        offsets = [(px + round((dx - px) * i / steps), py + round((dy - py) * i / steps))
                   for i in range(steps + 1)]
        for ox, oy in offsets:
            for x, y in labels.get(name, []):
                tx, ty = x + ox, y + oy
                if 0 < tx < FRAME - 1 and 0 < ty < FRAME - 1:
                    dst[tx, ty] = src[x, y]
    return out


def shiny_palette(normal_front, shiny_front, palette):
    """Majority vote of the shiny colour under each palette index, using the
    same pixel positions in the normal and shiny fronts. The extra back shades
    use their listed shiny colours."""
    votes = [Counter() for _ in palette]
    normal = normal_front.load()
    shiny = shiny_front.load()
    for y in range(normal_front.height):
        for x in range(normal_front.width):
            n, s = normal[x, y], shiny[x, y]
            if n[3] >= 128 and s[3] >= 128 and n[:3] not in EXTRA_SHADES:
                votes[palette.index(n[:3])][s[:3]] += 1

    result = []
    for colour, counter in zip(palette, votes):
        result.append(EXTRA_SHADES[colour] if colour in EXTRA_SHADES else counter.most_common(1)[0][0])
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
    back = remap_back(place(images['gen5-back'], BACK_BOTTOM))
    shiny_front = place(images['gen5-shiny'], FRONT_BOTTOM)

    palette = build_palette(front)
    shiny = shiny_palette(front, shiny_front, palette)

    for name, frame, parts, part_of in [('front', front, FRONT_PARTS, front_part), ('back', back, BACK_PARTS, back_part)]:
        indices = to_indices(frame, palette)
        write_png(os.path.join(OUT_DIR, name + '.png'), indices, idle_frame(indices, palette, parts, part_of), palette)

    write_pal(os.path.join(OUT_DIR, 'normal.pal'), palette)
    write_pal(os.path.join(OUT_DIR, 'shiny.pal'), shiny)


if __name__ == '__main__':
    main()

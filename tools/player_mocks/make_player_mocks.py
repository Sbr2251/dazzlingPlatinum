#!/usr/bin/env python3
"""Renders player (Lucas) redesign mocks as palette swaps of the stock sprites.

Usage: python3 tools/player_mocks/make_player_mocks.py [out_dir]   (Pillow; default docs/player_mocks)

Each design gives new colours to five roles: accent (cap and shirt), jacket, dark (hair and trousers), light (scarf,
whites) and grey. Skin and outlines keep their stock colours. Every sprite keeps its own 16-colour palette and its
pixels are untouched, so a chosen design ships by rewriting palettes only.
"""
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
TRAINER = os.path.join(ROOT, 'res/trainers/classes/player_male')
OVERWORLD = os.path.join(ROOT, 'res/prebuilt/data/mmodel/mmodel/mmodel_00000090.bin')  # pl_boy01c
FONT_DIR = '/usr/share/fonts/dejavu-sans-fonts'

# palette index -> (role, level) for each stock sprite; None keeps the stock colour
ROLES = {
    'front': {1: ('jkt', 2), 2: ('acc', 1), 3: ('acc', 2), 4: ('drk', 0), 5: ('jkt', 0), 6: ('gry', 0), 7: ('drk', 1),
              8: ('lit', 2), 10: ('acc', 0), 14: ('lit', 1), 15: ('lit', 3)},
    'back': {1: ('jkt', 2), 2: ('acc', 1), 3: ('acc', 2), 4: ('drk', 0), 5: ('jkt', 0), 6: ('lit', 3), 7: ('jkt', 3),
             8: ('lit', 2), 9: ('lit', 2), 10: ('acc', 0), 14: ('lit', 1), 15: ('lit', 3)},
    'mugshot': {2: ('acc', 1), 3: ('acc', 2), 4: ('drk', 0), 5: ('jkt', 0), 6: ('jkt', 1), 7: ('jkt', 2),
                8: ('lit', 2), 9: ('lit', 0), 14: ('lit', 1), 15: ('lit', 3)},
    'overworld': {1: ('acc', 1), 2: ('acc', 2), 3: ('acc', 0), 5: ('lit', 3), 6: ('lit', 2), 7: ('drk', 0),
                  8: ('lit', 1), 10: ('jkt', 0), 12: ('jkt', 1), 13: ('jkt', 2)},
}

DESIGNS = [
    {
        'key': 'a_distortion',
        'name': 'A - Distortion Walker',
        'tagline': 'Dark and dramatic. Giratina colours: charcoal-violet jacket, crimson cap, gold bag straps.',
        'acc': [(96, 24, 40), (168, 32, 48), (216, 64, 72)],
        'jkt': [(40, 36, 56), (56, 52, 76), (80, 72, 104), (112, 104, 144)],
        'drk': [(24, 20, 32), (48, 44, 64)],
        'lit': [(112, 104, 128), (152, 144, 168), (200, 192, 208), (240, 236, 248)],
        'gry': [(184, 144, 56)],
        'bg': [(40, 28, 56), (88, 40, 72)],
        'ground': [(56, 48, 72), (64, 56, 84)],
    },
    {
        'key': 'b_ember',
        'name': 'B - Ember Ranger',
        'tagline': 'Warm and rugged. Mt. Coronet lava: burnt-orange jacket, charcoal cap and shirt, cream scarf.',
        'acc': [(72, 40, 32), (64, 56, 56), (96, 88, 88)],
        'jkt': [(136, 56, 24), (176, 80, 32), (216, 112, 48), (240, 152, 80)],
        'drk': [(48, 32, 24), (96, 72, 56)],
        'lit': [(152, 128, 104), (192, 168, 136), (224, 208, 176), (248, 240, 216)],
        'gry': [(120, 104, 88)],
        'bg': [(64, 32, 24), (184, 88, 40)],
        'ground': [(120, 72, 48), (128, 78, 54)],
    },
    {
        'key': 'c_summit',
        'name': 'C - Summit Keystone',
        'tagline': 'Bright and sporty. Mega Evolution: deep-teal jacket, gold cap and shirt, crisp white scarf.',
        'acc': [(136, 72, 32), (224, 160, 32), (248, 208, 72)],
        'jkt': [(24, 96, 104), (32, 128, 136), (56, 168, 168), (112, 208, 200)],
        'drk': [(32, 48, 64), (72, 88, 112)],
        'lit': [(128, 144, 160), (176, 192, 208), (216, 224, 232), (248, 248, 248)],
        'gry': [(112, 128, 136)],
        'bg': [(64, 136, 168), (200, 232, 232)],
        'ground': [(112, 176, 96), (120, 184, 104)],
    },
]

ORIGINAL = {'key': 'original', 'name': 'Original', 'bg': [(96, 104, 136), (200, 200, 216)],
            'ground': [(112, 176, 96), (120, 184, 104)]}

# numeric texture suffixes in pl_boy01c: 1-4 up, 5-8 down, 9-12 left, 13-16 right, 17-32 running
OW_FRAMES = [(5, 'down'), (6, 'walk'), (1, 'up'), (9, 'left'), (13, 'right'), (26, 'run')]


def ds(c):
    """Rounds to the DS's 15-bit colour, as the game would show it."""
    return tuple(round(v * 31 / 255) * 255 // 31 for v in c)


def recolour(pal, roles, design):
    pal = list(pal)
    if design is None:
        return pal
    for i, (role, level) in roles.items():
        pal[i] = ds(design[role][level])
    return pal


def trainer_sprite(name, crop=None):
    im = Image.open(os.path.join(TRAINER, f'{name}.png'))
    if crop:
        im = im.crop(crop)
    p = im.getpalette()
    return im, [tuple(p[i * 3:i * 3 + 3]) for i in range(16)]


def overworld_frames():
    """Decodes pl_boy01c's 4bpp textures into (index image, palette)."""
    d = open(OVERWORLD, 'rb').read()
    tex = d[struct.unpack_from('<I', d, 16)[0]:]
    u16 = lambda o: struct.unpack_from('<H', tex, o)[0]
    u32 = lambda o: struct.unpack_from('<I', tex, o)[0]

    def entries(o):
        n, dh = tex[o + 1], o + u16(o + 6)
        size, names = u16(dh), dh + u16(dh + 2)
        return [(tex[names + 16 * i:names + 16 * i + 16].rstrip(b'\0').decode(), tex[dh + 4 + i * size:dh + 4 + (i + 1) * size])
                for i in range(n)]

    tex_data, pal_data = u32(0x14), u32(0x38)
    pal_off = struct.unpack_from('<H', entries(u16(0x34))[0][1])[0] << 3
    pal = [struct.unpack_from('<H', tex, pal_data + pal_off + 2 * i)[0] for i in range(16)]
    pal = [((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31) for c in pal]
    frames = {}
    for name, e in entries(u16(0x0E)):
        param = struct.unpack_from('<I', e)[0]
        base = tex_data + ((param & 0xFFFF) << 3)
        im = Image.new('P', (32, 32))
        im.putdata([tex[base + i // 2] >> (4 * (i & 1)) & 15 for i in range(32 * 32)])
        frames[int(name.split('.')[1])] = im
    return frames, pal


def to_rgba(im, pal):
    """Index image -> RGBA with index 0 transparent."""
    out = Image.new('RGBA', im.size)
    out.putdata([(0, 0, 0, 0) if v == 0 else pal[v] + (255,) for v in im.get_flattened_data()])
    return out


def font(size, bold=False):
    return ImageFont.truetype(os.path.join(FONT_DIR, 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'), size)


def gradient(size, top, bottom):
    w, h = size
    g = Image.new('RGBA', size)
    d = ImageDraw.Draw(g)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)) + (255,))
    return g


def ground(size, tones, tile=40):
    g = Image.new('RGBA', size)
    d = ImageDraw.Draw(g)
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            d.rectangle([x, y, x + tile - 1, y + tile - 1], fill=tones[(x // tile + y // tile) & 1] + (255,))
    return g


def battle_panel(sprite, size, design, scale, platform=True):
    panel = gradient(size, *design['bg'])
    d = ImageDraw.Draw(panel)
    big = sprite.resize((sprite.width * scale, sprite.height * scale), Image.NEAREST)
    x, y = (size[0] - big.width) // 2, size[1] - big.height - 14
    if platform:
        pw, ph = int(big.width * 0.8), 34
        cx, cy = size[0] // 2, size[1] - 34
        shade = tuple(max(0, c - 40) for c in design['bg'][1])
        d.ellipse([cx - pw // 2, cy - ph // 2, cx + pw // 2, cy + ph // 2], fill=shade + (255,))
    panel.alpha_composite(big, (x, y))
    return panel


def swatches(design):
    cols = [design[r][i] for r in ('acc', 'jkt', 'drk', 'lit') for i in (1, len(design[r]) - 1)]
    im = Image.new('RGBA', (len(cols) * 34, 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, c in enumerate(cols):
        d.rectangle([i * 34, 0, i * 34 + 30, 29], fill=ds(c) + (255,), outline=(20, 20, 20, 255))
    return im


def render_set(design, sprites, ow):
    """Returns the recoloured RGBA sprites for one design (None = stock colours)."""
    out = {name: to_rgba(im, recolour(pal, ROLES[name], design)) for name, (im, pal) in sprites.items()}
    frames, pal = ow
    ow_pal = recolour(pal, ROLES['overworld'], design)
    out['overworld'] = [(label, to_rgba(frames[n], ow_pal)) for n, label in OW_FRAMES]
    return out


def colour_count(im):
    return len({p for p in im.get_flattened_data() if p[3]})


def design_sheet(design, rendered, path):
    W, H = 1280, 820
    sheet = Image.new('RGBA', (W, H), (24, 24, 28, 255))
    d = ImageDraw.Draw(sheet)
    d.text((32, 22), design['name'], font=font(36, True), fill=(245, 245, 245))
    d.text((32, 72), design['tagline'], font=font(18), fill=(200, 200, 210))
    sw = swatches(design)
    sheet.alpha_composite(sw, (W - sw.width - 32, 30))
    for i, name in enumerate(('cap/shirt', 'jacket', 'hair/pants', 'scarf')):
        cx = W - sw.width - 32 + i * 68 + 32
        d.text((cx, 66), name, font=font(13), fill=(170, 170, 180), anchor='mt')

    y = 116
    label = font(15, True)
    for x, img, title, scale, size in [(32, rendered['front'], 'Battle - front', 4, (360, 360)),
                                       (412, rendered['back'], 'Battle - back', 4, (360, 360)),
                                       (792, rendered['mugshot'], 'Mugshot', 4, (456, 360))]:
        sheet.alpha_composite(battle_panel(img, size, design, scale, platform=title != 'Mugshot'), (x, y + 24))
        d.text((x, y), title, font=label, fill=(230, 230, 230))

    y = 524
    d.text((32, y), 'Overworld (5x) - down, walk, up, left, right, run', font=label, fill=(230, 230, 230))
    strip = ground((W - 64, 220), design['ground'])
    for i, (name, fr) in enumerate(rendered['overworld']):
        big = fr.resize((160, 160), Image.NEAREST)
        strip.alpha_composite(big, (22 + i * 196, 30))
        ImageDraw.Draw(strip).text((22 + i * 196 + 80, 192), name, font=font(15, True), fill=(240, 240, 240),
                                    anchor='mt', stroke_width=2, stroke_fill=(0, 0, 0))
    sheet.alpha_composite(strip, (32, y + 24))
    d.text((32, H - 40), 'Palette swap of the stock Lucas sprites: same pixels, new colours, within the DS 16-colour limit.',
           font=font(14), fill=(150, 150, 160))
    sheet.convert('RGB').save(path)


def comparison_sheet(entries, path):
    col, W = 320, 320 * len(entries)
    H = 700
    sheet = Image.new('RGBA', (W, H), (24, 24, 28, 255))
    d = ImageDraw.Draw(sheet)
    for i, (design, rendered) in enumerate(entries):
        x = i * col
        d.text((x + 16, 16), design['name'], font=font(20, True), fill=(240, 240, 240))
        sheet.alpha_composite(battle_panel(rendered['front'], (col - 24, 330), design, 4), (x + 12, 52))
        sheet.alpha_composite(battle_panel(rendered['mugshot'], (col - 24, 136), design, 2, platform=False), (x + 12, 392))
        strip = ground((col - 24, 150), design['ground'])
        for j, n in enumerate((0, 2, 3)):
            strip.alpha_composite(rendered['overworld'][n][1].resize((96, 96), Image.NEAREST), (2 + j * 98, 28))
        sheet.alpha_composite(strip, (x + 12, 538))
    sheet.convert('RGB').save(path)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'docs/player_mocks')
    os.makedirs(out_dir, exist_ok=True)
    sprites = {'front': trainer_sprite('front'), 'back': trainer_sprite('back', (0, 0, 80, 80)),
               'mugshot': trainer_sprite('mugshot')}
    ow = overworld_frames()

    entries = [(ORIGINAL, render_set(None, sprites, ow))]
    for design in DESIGNS:
        rendered = render_set(design, sprites, ow)
        counts = {k: colour_count(v) for k, v in rendered.items() if k != 'overworld'}
        assert all(c <= 15 for c in counts.values()), counts
        design_sheet(design, rendered, os.path.join(out_dir, f"{design['key']}.png"))
        entries.append((design, rendered))
    comparison_sheet(entries, os.path.join(out_dir, 'compare.png'))
    print('wrote', out_dir)


if __name__ == '__main__':
    main()

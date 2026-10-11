"""DS-style (Platinum proportion) overworld redraw engine.

Every pixel here is authored: per-character region masks (ASCII) + hand-placed detail overlays,
with a deterministic shading/outline pass. Stock Platinum sprites are used only as a size reference
(23-24 px tall figure, feet on y=29, x 7..23) - no stock pixels are read or copied.
"""
from PIL import Image

CELL = 32
OUTLINE = (24, 20, 24)

# region letter -> ramp name; tones: 0 light, 1 mid, 2 dark
# explicit colour letters usable directly in masks (key into the palette)
EXPLICIT = {'k': 'outline', '1': 'hair0', '2': 'hair1', '3': 'hair2', '4': 'skin0', '5': 'skin1', '6': 'skin2',
            'e': 'outline', 'E': 'eye', 'w': 'white0', '7': 'top0', '8': 'top1', '9': 'top2', 'a': 'top20', 'b': 'top21',
            'x': 'acc0', 'o': 'bottom0', 'p': 'bottom1', 'g': 'glass'}
REGION = {
    'H': 'hair', 'F': 'skin', 'h': 'skin', 'G': 'skin',
    'T': 'top', 'U': 'top', 'V': 'top', 'J': 'top2', 'C': 'coat', 'c': 'coat',
    'P': 'bottom', 'M': 'shoes', 'X': 'acc', 'W': 'white',
}
MOVABLE_ARM = set('UVh')


def parse(grid, x0=7, bottom=29):
    rows = [r for r in grid.strip('\n').split('\n')]
    rows = [r.split('#')[0].rstrip() for r in rows]
    h = len(rows)
    y0 = bottom - h + 1
    m = {}
    for j, r in enumerate(rows):
        r = r.strip()
        off = 0
        if ':' in r:
            a, r = r.split(':', 1)
            off = int(a)
        for i, ch in enumerate(r):
            if ch not in '. ':
                m[(x0 + off + i, y0 + j)] = ch
    return m


def shift(m, dx, dy, pred=lambda k, v: True):
    out = {}
    for (x, y), v in m.items():
        if pred((x, y), v):
            out[(x + dx, y + dy)] = v
    for (x, y), v in m.items():
        if not pred((x, y), v):
            out.setdefault((x, y), v)
    return out


def mirror(m):
    return {(30 - x, y): v for (x, y), v in m.items()}


def render(mask, pal, details=None, light_left=True):
    """mask: {(x,y): region letter}; pal: {ramp: [light, mid, dark]} + 'outline'; details: {(x,y): colour key or rgb}."""
    img = Image.new('RGBA', (CELL, CELL), (0, 0, 0, 0))
    px = img.load()
    inside = set(mask)
    ol = pal.get('outline', OUTLINE)
    for (x, y), ch in mask.items():
        if not (0 <= x < CELL and 0 <= y < CELL):
            continue
        if ch in EXPLICIT:
            px[x, y] = tuple(pal.get(EXPLICIT[ch], pal['outline'])) + (255,)
            continue
        n4 = [(x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1)]
        if any(p not in inside for p in n4):
            px[x, y] = ol + (255,)
            continue
        reg = REGION[ch]
        ramp = pal[reg]
        same = lambda p: p in mask and REGION.get(mask[p]) == reg and not (mask[p] in MOVABLE_ARM) != (ch in MOVABLE_ARM)
        up, down = same((x, y - 1)), same((x, y + 1))
        left, right = same((x - 1, y)), same((x + 1, y))
        # separate arms from torso with an outline line (DS style)
        if (ch in MOVABLE_ARM) != (mask.get((x + 1, y), '.') in MOVABLE_ARM) and mask.get((x + 1, y), '.') not in '.' and ch == 'U' and mask.get((x + 1, y)) in 'TJC':
            px[x, y] = ol + (255,); continue
        if ch == 'U' and mask.get((x - 1, y)) in ('T', 'J', 'C'):
            px[x, y] = ol + (255,); continue
        if ch == 'V' and mask.get((x + 1, y)) in ('T', 'J', 'C'):
            px[x, y] = ol + (255,); continue
        tone = 1
        if reg == 'hair':
            # DS hair ramp: light band near the top-left of the mass, dark rim at the bottom/right edges
            dt = 0
            while (x, y - dt - 1) in mask and REGION.get(mask[(x, y - dt - 1)]) == 'hair':
                dt += 1
            db = 0
            while (x, y + db + 1) in mask and REGION.get(mask[(x, y + db + 1)]) == 'hair':
                db += 1
            xs = [p[0] for p, v in mask.items() if p[1] == y and REGION.get(v) == 'hair']
            cx = (min(xs) + max(xs)) / 2
            if db == 0 or not right or mask.get((x, y + 1)) == 'F':
                tone = 2
            elif dt <= 2 and x <= cx + 2:
                tone = 0
            elif db <= 1 and x > cx + 3:
                tone = 2
            else:
                tone = 1
            px[x, y] = tuple(ramp[tone]) + (255,)
            continue
        if not down or (not right if light_left else not left):
            tone = 2
        if not up and down:
            tone = 0 if tone == 1 else 1
        # face just under hair is in shadow
        if reg == 'skin' and mask.get((x, y - 1)) == 'H':
            tone = 2
        if reg == 'hair' and mask.get((x, y + 1)) in ('F',):
            tone = 2
        if len(ramp) == 2:
            tone = min(tone, 1)
        px[x, y] = tuple(ramp[min(tone, len(ramp) - 1)]) + (255,)
    for (x, y), c in (details or {}).items():
        if not (0 <= x < CELL and 0 <= y < CELL):
            continue
        if c is None:
            px[x, y] = (0, 0, 0, 0)
            continue
        if isinstance(c, str):
            if c == 'k':
                c = ol
            else:
                ramp, t = c[:-1], int(c[-1])
                c = pal[ramp][t]
        px[x, y] = tuple(c) + (255,)
    return img


def overlay(grid, key, x0=7, bottom=29):
    """ASCII detail overlay: char -> colour key via `key` dict; '.'/' ' = no change."""
    m = parse(grid, x0, bottom)
    return {p: key[ch] for p, ch in m.items() if ch in key}

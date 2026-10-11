import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/tmp/a1r3/tools')
from owlib import *
from PIL import Image

PCCP = SRC / 'slawter/graphics/event_objects/pics/people'
TSR = 'https://www.spriters-resource.com/ds_dsi/'


def bw_hero(img, y0, fish_x):
    walk = walk_bw3(grid(img, 4, y0, 3, 4))
    run = walk_bw3(grid(img, 112, y0, 3, 4))
    surf = grid(img, 212, y0, 4, 4)
    bike = grid(img, 344, y0, 3, 4)
    fish = grid(img, fish_x, 284, 4, 1, pitch=64, size=64)
    extras = [
        ('bike', [bike[r][c] for r in range(4) for c in range(3)]),
        ('surf', [surf[r][c] for r in range(4) for c in (0, 1)]),
        ('fish', fish[0]),
    ]
    return walk, run, extras


def b2_hero(img):
    g = lambda x, y, c, r, **k: grid(img, x, y, c, r, pitch=33, **k)
    walk = walk_bw3(g(1, 1, 3, 4))
    run = walk_bw3(g(133, 1, 3, 4))
    bike = g(265, 1, 3, 4)
    surf = g(1, 397, 4, 4)
    fish = grid(img, 1, 529, 4, 1, pitch=65, size=64)
    extras = [
        ('bike', [bike[r][c] for r in range(4) for c in range(3)]),
        ('surf', [surf[r][c] for r in range(4) for c in (0, 1)]),
        ('fish', fish[0]),
    ]
    return walk, run, extras


def pccp_hero(name, walkfile='walking.png'):
    d = PCCP / name
    walk = walk_emerald(emerald_frames(d / walkfile))
    run = walk_emerald(emerald_frames(d / 'running.png')) if (d / 'running.png').exists() else None
    extras = []
    if (d / 'bike.png').exists():
        b = emerald_frames(d / 'bike.png')
        extras.append(('bike', [b[0], b[3], b[4], b[1], b[5], b[6], b[2], b[7], b[8]]))
    if (d / 'surfing.png').exists():
        extras.append(('surf', emerald_frames(d / 'surfing.png')))
    if (d / 'fishing.png').exists():
        extras.append(('fish', emerald_frames(d / 'fishing.png')[:12]))
    return walk, run, extras


def walk_2col4(cells):
    """rows up/down/left/right, each (stand, step)."""
    w = {}
    for i, f in enumerate(FACINGS):
        s, st = cells[i][0], cells[i][1]
        w[f] = [s, st, s, mirror(st)] if f in ('up', 'down') else [s, st, s, st]
    return w


def recolor_stock(member_const, color_map):
    """Stock Platinum walker with palette entries replaced (index -> RGB)."""
    from btx import load, gfx_member_map
    t, p, _ = load(gfx_member_map()[member_const])
    pal = list(p)
    for k, v in color_map.items():
        pal[k] = v
    frames = []
    for n, w_, h_, f_, px in t[:16]:
        o = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        o.putdata([(0, 0, 0, 0) if v == 0 else pal[v] + (255,) for v in px])
        frames.append(o)
    walk = {f: frames[4 * i: 4 * i + 4] for i, f in enumerate(FACINGS)}
    return walk, p

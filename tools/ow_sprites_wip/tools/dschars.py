"""Character designs: DS-proportion redraws of the four CC0 Openmon designs.

Masks: H hair, F face/neck skin, h hand (movable), U sleeve (movable), T top, J top2 (inner shirt / trim),
C coat, P bottoms, G leg skin, M shoes, X accent, W white.
Detail overlay keys (KEY): k outline, a/b/c hair light/mid/dark, x/y/z skin, q/r/s top, t/u top2,
o/p bottoms, m shoes, X accent, w white, e eye white-ish highlight, '-' clear.
"""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/tmp/a1r3/tools')
from dsdraw import *

KEY = {'k': 'k', 'a': 'hair0', 'b': 'hair1', 'c': 'hair2', 'x': 'skin0', 'y': 'skin1', 'z': 'skin2',
       'q': 'top0', 'r': 'top1', 's': 'top2', 't': 'top20', 'u': 'top21', 'o': 'bottom0', 'p': 'bottom1',
       'm': 'shoes0', 'X': 'acc0', 'Y': 'acc1', 'w': 'white0', 'g': 'coat0', 'h': 'coat1', 'j': 'coat2', '-': None}

# ---------------------------------------------------------------- legs
LEGS = {
    'down': {
        'stand': """
....PPPPPPPPP....
....PPPP.PPPP....
....PPPP.PPPP....
....MMMM.MMMM....""",
        'stepA': """
....PPPPPPPPP....
....PPPPPPPPP....
....PPPP.PPPP....
....MMMM.PPPP....
.........MMMM....
.........MMMM....""",
        'stepB': """
....PPPPPPPPP....
....PPPPPPPPP....
....PPPP.PPPP....
....PPPP.MMMM....
....MMMM.........
....MMMM.........""",
    },
    'up': {
        'stand': """
....PPPPPPPPP....
....PPPP.PPPP....
....PPPP.PPPP....
....MMMM.MMMM....""",
        'stepA': """
....PPPPPPPPP....
....PPPPPPPPP....
....PPPP.PPPP....
....MMMM.PPPP....
.........MMMM....
.........MMMM....""",
        'stepB': """
....PPPPPPPPP....
....PPPPPPPPP....
....PPPP.PPPP....
....PPPP.MMMM....
....MMMM.........
....MMMM.........""",
    },
    'left': {
        'stand': """
.....PPPPPP......
.....PPPPPP......
.....PPPPP.......
....MMMMMM.......""",
        'stepA': """
.....PPPPPP......
....PPPPPPPP.....
...PPPP..PPPP....
..MMMM...PPPP....
.........MMMM....
.................""",
        'stepB': """
.....PPPPPP......
.....PPPPPPP.....
....PPPP.PPPP....
...MMMMM.MMMMM...
.................
.................""",
    },
}


def body(grid_upper, step, facing, legs=None, arm_swing=0):
    """Upper body (bottom row y25) + legs; steps raise the upper body 1 px and push one foot to y30."""
    legs = legs or LEGS
    up = parse(grid_upper, bottom=25)
    if step == 'stand':
        leg = parse(legs[facing]['stand'], bottom=29)
    else:
        up = {(x, y - 1): v for (x, y), v in up.items()}
        leg = parse(legs[facing][step], bottom=30)
        if facing == 'left' and arm_swing:
            dx = arm_swing if step == 'stepA' else -arm_swing
            arms = {p: v for p, v in up.items() if v in 'UVh'}
            rest = {p: v for p, v in up.items() if v not in 'UVh'}
            up = dict(rest)
            for (x, y), v in arms.items():
                up[(x + dx, y)] = v
    m = dict(leg)
    m.update(up)
    return m


class Design:
    def __init__(self, name, pal, grids, details, legs=None, arm_swing=0):
        self.name, self.pal, self.grids, self.details = name, pal, grids, details
        self.legs = legs or LEGS
        self.arm_swing = arm_swing

    def palette(self):
        p = {'outline': OUTLINE}
        for k, v in self.pal.items():
            p[k] = v
            for i, c in enumerate(v):
                p[f'{k}{i}'] = c
        p.setdefault('white', [(248, 248, 248)])
        p.setdefault('white0', (248, 248, 248))
        p.setdefault('eye', p.get('hair2', OUTLINE))
        p.setdefault('glass', (200, 220, 240))
        return p

    def frame(self, facing, step):
        f = 'left' if facing in ('left', 'right') else facing
        m = body(self.grids[f], step, f, self.legs, self.arm_swing)
        pal = self.palette()
        det = {}
        if f in self.details:
            d = overlay(self.details[f], {k: v for k, v in KEY.items()}, bottom=25)
            if step != 'stand':
                d = {(x, y - 1): v for (x, y), v in d.items()}
            det = {p: (pal[v] if (v and v != 'k' and v in pal) else v) for p, v in d.items()}
            det = {p: (pal['outline'] if v == 'k' else v) for p, v in det.items()}
        img = render(m, pal, det)
        if facing == 'right':
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
            # flipping around the cell centre moves x->31-x; stock right rows mirror around x=15.5 too
        return img

    def walk(self):
        return {f: [self.frame(f, s) for s in ('stand', 'stepA', 'stand', 'stepB')]
                for f in ('up', 'down', 'left', 'right')}

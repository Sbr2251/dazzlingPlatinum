"""Rebuild Mega Alakazam's back frame 2 as an idle built from back frame 1.

Frame 2 used to be almost the same as frame 1. The front already raises its
arms between frames, so the back now does the same:
  - the head and torso lift 1 px, and the lift eases to 0 at the hips;
  - the arms and hands rise another 2 px (3 px in total) and move 1 px outward;
  - each of the five floating spoons drifts on its own by 1-3 px;
  - the white tufts and the crossed legs stay where they are.

The body is warped backwards through a smooth displacement field. Where the
field changes, rows are repeated instead of leaving gaps, so the outline stays
closed. Every pixel is copied from frame 1, so the palette indices are
unchanged. back.png frame 1 and both .pal files are not touched.

Run with: ~/.venvs/desmume/bin/python tools/mega_sprites/animate_alakazam.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BACK = ROOT / "res/pokemon/alakazam/forms/mega/back.png"
W = 80
CX = 40  # the body's vertical centre line

# Rigid (dx, dy) for each spoon, keyed by its top-left pixel in frame 1.
# The spoons fan outward and float up a little, with the centre spoon rising most.
SPOONS = {
    (38, 5): (0, -3),   # centre
    (24, 8): (-1, -1),  # inner left
    (48, 8): (1, -1),   # inner right
    (14, 16): (-1, -2),  # outer left
    (55, 16): (1, -2),  # outer right
}


def label(mask):
    lab = np.zeros(mask.shape, int)
    n = 0
    for y, x in zip(*np.where(mask)):
        if lab[y, x]:
            continue
        n += 1
        lab[y, x] = n
        stack = [(y, x)]
        while stack:
            cy, cx = stack.pop()
            for ny in (cy - 1, cy, cy + 1):
                for nx in (cx - 1, cx, cx + 1):
                    if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] \
                            and mask[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = n
                        stack.append((ny, nx))
    return lab, n


def ramp(v, lo, hi):
    """0 at v <= lo, 1 at v >= hi, linear in between."""
    return min(1.0, max(0.0, (v - lo) / (hi - lo)))


def displacement(x, y):
    """Return (dx, dy) for the body pixel at target (x, y). Negative dy means up."""
    torso = 1.0 - ramp(y, 46, 56)          # head and chest up 1, hips planted
    arm = ramp(abs(x - CX), 12, 20) * (1.0 - ramp(y, 46, 54))
    dy = -(torso + 2.0 * arm)
    dx = (1.0 if x > CX else -1.0) * arm
    return dx, dy


def build_frame2(f1):
    lab, n = label(f1 > 0)
    sizes = [(lab == i).sum() for i in range(1, n + 1)]
    body_id = 1 + int(np.argmax(sizes))
    body = np.where(lab == body_id, f1, 0)

    f2 = np.zeros_like(f1)
    for y in range(W):
        for x in range(W):
            dx, dy = displacement(x, y)
            sx, sy = int(round(x - dx)), int(round(y - dy))
            if 0 <= sx < W and 0 <= sy < W:
                f2[y, x] = body[sy, sx]

    for i in range(1, n + 1):
        if i == body_id:
            continue
        ys, xs = np.where(lab == i)
        key = (int(xs.min()), int(ys.min()))
        ox, oy = SPOONS[key]
        f2[ys + oy, xs + ox] = f1[ys, xs]
    return f2


def main():
    im = Image.open(BACK)
    assert im.mode == "P" and im.size == (160, 80)
    pal = im.getpalette()
    a = np.array(Image.frombytes("L", im.size, im.tobytes()))
    f1 = a[:, :W]
    f2 = build_frame2(f1)
    for fr in (f2,):
        assert not (fr[0].any() or fr[-1].any() or fr[:, 0].any() or fr[:, -1].any())
    out = np.concatenate([f1, f2], axis=1).astype(np.uint8)
    new = Image.frombytes("P", im.size, out.tobytes())
    new.putpalette(pal)
    new.save(BACK, bits=4, optimize=False)
    print("wrote", BACK.relative_to(ROOT))


if __name__ == "__main__":
    main()

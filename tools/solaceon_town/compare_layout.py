#!/usr/bin/env python3
"""Layout-vs-render comparison for Solaceon (standard library only; after tools/lake_verity/compare_layout.py).

Usage: python3 tools/solaceon_town/compare_layout.py <graybox_top.png> <out.png> [--region 540,632,612,680]

The render must be a top view (render.py "top", region 540,632,612,680 by default). Writes three panels over the
two town chunks (x 544..607, z 640..671): layout.py's tile kinds as flat colours (tile grid drawn), the render, and
the render with every blocked layout tile darkened, so footprints can be checked against the drawn buildings.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
sys.path.insert(0, HERE)
import layout  # noqa: E402
import png  # noqa: E402

COLORS = {"grass": (110, 200, 100), "road": (225, 200, 140), "paving": (175, 175, 185), "emblem": (90, 60, 130),
          "tallgrass": (40, 130, 60), "tree": (30, 90, 40), "house": (150, 90, 50), "pc": (230, 80, 60),
          "mart": (60, 110, 230), "hall": (150, 110, 200), "door": (255, 220, 0), "wall": (120, 100, 100),
          "pillar": (80, 60, 60), "gate": (255, 255, 255), "fence": (240, 240, 240), "post": (110, 60, 160),
          "lantern": (255, 240, 150), "bench": (140, 100, 60), "offering": (250, 120, 160), "plaque": (90, 90, 90),
          "tent": (245, 240, 220), "tent_floor": (230, 210, 170), "table": (170, 120, 70), "kennel": (130, 90, 60),
          "stall": (200, 170, 120), "trough": (60, 140, 60), "yard": (200, 180, 130), "bay": (50, 50, 60),
          "ruts": (170, 140, 100), "scaffold": (160, 120, 70), "crate": (120, 80, 40), "worklight": (255, 255, 120),
          "dig": (190, 140, 120), "gap": (255, 0, 0), "berry": (120, 70, 40)}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    region = (540, 632, 612, 680)
    if "--region" in sys.argv:
        region = tuple(int(v) for v in sys.argv[sys.argv.index("--region") + 1].split(","))
        args = [a for a in args if a != sys.argv[sys.argv.index("--region") + 1]]
    img = png.read(args[0])
    ppt = img.width // (region[2] - region[0])
    t = layout.tiles()
    W, H = (layout.X1 - layout.X0 + 1) * ppt, (layout.Z1 - layout.Z0 + 1) * ppt
    rows = [[(0, 0, 0, 255)] * (3 * W + 16) for _ in range(H)]
    for y in range(H):
        for x in range(W):
            tx, tz = layout.X0 + x // ppt, layout.Z0 + y // ppt
            coll, h, kind = t[(tx, tz)]
            if kind == "stock":
                c = (60, 60, 60) if coll & layout.BLOCK else (150, 150, 150)
            else:
                c = COLORS[kind]
            edge = x % ppt == 0 or y % ppt == 0
            rows[y][x] = tuple(v // 2 for v in c) + (255,) if edge else c + (255,)
            px = img.pixels[(tz - region[1]) * ppt + y % ppt][(tx - region[0]) * ppt + x % ppt]
            rows[y][W + 8 + x] = px
            if coll & layout.BLOCK:
                px = (px[0] // 2, px[1] // 2, px[2] // 2, 255)
            rows[y][2 * W + 16 + x] = px
    png.write_rgba(args[1], 3 * W + 16, H, rows)
    print("wrote", args[1])


if __name__ == "__main__":
    main()

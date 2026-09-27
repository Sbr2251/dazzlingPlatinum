#!/usr/bin/env python3
"""Layout-vs-render comparison image (standard library only).

Usage: python3 tools/lake_verity/compare_layout.py <top render.png> <out.png> [--region x0,z0,x1,z1] [--stock]

Draws layout.py's tile kinds (the same window as `layout.py --ascii`, x 4..63, z 10..59 by default) as flat
colours, and writes [layout | render | render with the layout's non-stock tiles outlined] side by side. The render
must be a blender_preview.py top view of the same region (any pixels-per-tile; it is sampled per tile).
--stock colours the stock collision grid instead of the redesigned layout (to check the render/axes alignment).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout  # noqa: E402
import png  # noqa: E402

COLORS = {"forest": (30, 90, 40), "water": (70, 120, 210), "grass": (90, 190, 80), "ground": (200, 190, 140),
          "exit": (250, 60, 60), "courtyard": (180, 170, 160), "wall1": (110, 100, 100), "wall2": (90, 80, 90),
          "keep2": (120, 110, 120), "wall3": (70, 60, 80), "terrace1": (160, 150, 150), "roof": (190, 180, 200),
          "tower": (60, 50, 50), "door1": (250, 200, 0), "door2": (250, 200, 0), "hatch": (250, 140, 0),
          "launchpad": (240, 80, 240), "stair": (230, 230, 120), "landing": (210, 210, 110), "rail": (80, 70, 60),
          "bridge": (150, 100, 50), "gate": (50, 40, 40), "gate_arch": (140, 110, 80)}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    region = (4, 10, 64, 60)
    if "--region" in sys.argv:
        region = tuple(int(v) for v in sys.argv[sys.argv.index("--region") + 1].split(","))
        args.remove(sys.argv[sys.argv.index("--region") + 1])
    render_path, out_path = args[0], args[1]
    x0, z0, x1, z1 = region
    t = layout.tiles()
    stock = layout.stock_grid()
    img = png.read(render_path)
    ppt = img.width // (x1 - x0)
    w, h = img.width, img.height
    rows = [[(0, 0, 0, 255)] * (3 * w + 16) for _ in range(h)]
    for y in range(h):
        for x in range(w):
            tx, tz = x0 + x // ppt, z0 + y // ppt
            if "--stock" in sys.argv:
                v = stock[(tx, tz)]
                kind = {layout.BLOCK: "forest", layout.WATER: "water", layout.GRASS: "grass",
                        layout.EXIT: "exit"}.get(v, "ground" if v == 0 else "door1")
            else:
                kind = t[(tx, tz)][2]
            c = COLORS[kind]
            edge = x % ppt == 0 or y % ppt == 0
            rows[y][x] = (c[0] // 2, c[1] // 2, c[2] // 2, 255) if edge else c + (255,)
            px = img.pixels[y][x]
            rows[y][w + 8 + x] = px
            # third panel: render, with tiles the redesign changes tinted by their layout colour
            changed = t[(tx, tz)][2] != {layout.BLOCK: "forest", layout.WATER: "water", layout.GRASS: "grass",
                                         layout.WALK: "ground", layout.EXIT: "exit"}.get(stock[(tx, tz)], "ground")
            if changed:
                px = tuple((px[k] + c[k]) // 2 for k in range(3)) + (255,)
            rows[y][2 * w + 16 + x] = px
    png.write_rgba(out_path, 3 * w + 16, h, rows)
    print("wrote", out_path)


if __name__ == "__main__":
    main()

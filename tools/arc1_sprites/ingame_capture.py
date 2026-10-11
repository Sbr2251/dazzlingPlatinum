#!/usr/bin/env python3
"""Capture the scratch placement (scratch_events.py) headlessly and check the palettes.

    SDL_VIDEODRIVER=dummy A1P2_REPO=<worktree> ~/.venvs/desmume39/bin/python \
        tools/arc1_sprites/ingame_capture.py ROM_DIR OUT_DIR

ROM_DIR holds a copy of dazzlingPlatinum.nds + main.nef.xMAP from the scratch build. Uses the Arc 1
part 2 harness (/tmp/act1p2/harness, golden save). Each scene runs in its own process (the harness
allows one emulator per process). The clock is pinned through sDebugClockHour (src/rtc.c).
The palette check needs PIL and runs with --check OUT_DIR (any Python with PIL).
"""

import os
import subprocess
import sys
from pathlib import Path

HARNESS = os.environ.get("A1P2_HARNESS", "/tmp/act1p2/harness")
SCENES = [  # map, x, z, facing, hour, seq frames (every 4 frames)
    ("TWINLEAF_TOWN", 116, 886, 1, 12, 300),
    ("TWINLEAF_TOWN", 116, 886, 1, 21, 2),
    ("OREBURGH_MINE_B2F", 12, 17, 2, 12, 20),
    ("JUBILIFE_CITY", 164, 756, 0, 12, 4),
    ("JUBILIFE_CITY", 164, 756, 0, 21, 2),
]


def capture_one(rom_dir, out, mapname, x, z, facing, hour, n):
    sys.path.insert(0, HARNESS)
    import a1p2emu as h
    rom, xmap = os.path.join(rom_dir, "dazzlingPlatinum.nds"), os.path.join(rom_dir, "main.nef.xMAP")
    e = h.boot_state(rom, xmap, mapname, x, z, facing, outdir=out)
    clock = h.read_xmap(xmap)["sDebugClockHour"][0]
    for _ in range(40):
        e.write(clock, bytes([hour]))
        e.run(10)
    e.shot(f"{mapname.lower()}_h{hour}")
    for i in range(n):
        e.write(clock, bytes([hour]))
        e.run(4)
        e.screens().crop((0, 0, 256, 192)).save(f"{out}/{mapname.lower()}_h{hour}_seq_{i:03d}.png")
    print(mapname, hour, e.state())


def check(out):
    """Exact 5-bit colour check of every statically placed walker/idle object on the Twinleaf noon shot."""
    from PIL import Image
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pixelkit import REPO_ROOT, read_png
    shot = Image.open(f"{out}/twinleaf_town_h12_seq_000.png").convert("RGB")
    P = shot.load()
    q = lambda c: tuple(v >> 3 for v in c)  # noqa: E731

    def frame(name, idx):
        w, h, px, pal = read_png(REPO_ROOT / "res/field/objects" / name)
        r, c = divmod(idx, w // 32)
        return [px[(r * 32 + y) * w + c * 32 + x] for y in range(32) for x in range(32)], [q(c) for c in pal]

    objs = []
    for name, z in (("arc1/saros.png", 888), ("arc1/eclipse_grunt_m.png", 890), ("arc1/eclipse_grunt_f.png", 892)):
        for k, idx in enumerate((4, 0, 8, 12)):
            objs.append((name, idx, 110 + 2 * k, z))
    objs += [("arc1/arc1_rift.png", 0, 119, 888), ("arc1/arc1_rift.png", 1, 119, 888),
             ("arc1/totem_hitmonlee_violet.png", 0, 121, 888), ("arc1/totem_hitmonlee_violet.png", 1, 121, 888)]
    worst = 1.0
    for name, idx, tx, tz in objs:
        f, pal = frame(name, idx)
        ex, ey = 16 * (tx - 116) + 110, 16 * (tz - 886) + 66
        pts = [(x, y, pal[v]) for y in range(32) for x in range(32) if (v := f[y * 32 + x])]
        best = (0, 0, 0, 0)
        for oy in range(ey - 10, ey + 11):
            for ox in range(ex - 10, ex + 11):
                vis = [(x, y, c) for x, y, c in pts if 0 <= ox + x < 256 and 0 <= oy + y < 192]
                m = sum(1 for x, y, c in vis if q(P[ox + x, oy + y]) == c)
                if m > best[0]:
                    best = (m, len(vis), ox, oy)
        m, n, ox, oy = best
        opaque = {(x, y) for x, y, _ in pts}
        palset = set(pal[1:])
        inner = [(x, y) for x, y, _ in pts if 0 <= ox + x < 256 and 0 <= oy + y < 192
                 and all((x + dx, y + dy) in opaque for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        ok = sum(1 for x, y in inner if q(P[ox + x, oy + y]) in palset) / max(len(inner), 1)
        worst = min(worst, ok)
        print(f"{name:34s} frame {idx:2d} tile ({tx},{tz}) screen ({ox:3d},{oy:3d}) exact-index {m}/{n} "
              f"= {m / max(n, 1):5.1%}  inner pixels in palette {ok:6.1%}")
    print(f"worst inner in-palette: {worst:.1%}")


def main():
    if sys.argv[1] == "--check":
        check(sys.argv[2])
        return
    if sys.argv[1] == "--one":
        rom_dir, out, mapname, x, z, facing, hour, n = sys.argv[2:10]
        capture_one(rom_dir, out, mapname, int(x), int(z), int(facing), int(hour), int(n))
        return
    rom_dir, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for scene in SCENES:
        subprocess.run([sys.executable, __file__, "--one", rom_dir, out] + [str(v) for v in scene], check=True)


if __name__ == "__main__":
    main()

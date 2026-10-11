#!/usr/bin/env python3
"""Battle-intro capture for the Eclipse trainer classes (scratch scene T of scratch_events.py).

    SDL_VIDEODRIVER=dummy A2_REPO=<worktree> ~/.venvs/desmume39/bin/python \
        tools/arc2_sprites/battle_capture.py ROM_DIR OUT_DIR

Boots on Twinleaf at (x,887) for x in 112/116/120 facing down, steps into the trainer's sight line and
mashes A through the approach and the intro text, saving the top screen every 10 frames until the
battle menu appears. One process per trainer (one emulator per process).
"""

import os
import subprocess
import sys

sys.path.insert(0, "/tmp/a2/harness")
TRAINERS = [("indra", 112), ("grunt_m", 116), ("grunt_f", 120)]


def one(rom_dir, out, tag, x):
    import a2lib
    rom, xmap = os.path.join(rom_dir, "dazzlingPlatinum.nds"), os.path.join(rom_dir, "main.nef.xMAP")
    sav = os.path.join(out, f"battle_{tag}.sav")
    a2lib.make_state(sav, "MAP_HEADER_TWINLEAF_TOWN", x, 886, "DOWN")
    e = a2lib.boot(rom, xmap, sav, out, expect_map="MAP_HEADER_TWINLEAF_TOWN")
    e.run(30)
    e.hold("DOWN", 16, 8)
    n = 0
    start = e.frame
    while e.frame - start < 4000 and not e.battle_menu_up():
        e.run(10)
        e.screens().save(f"{out}/battle_{tag}_{n:03d}.png")
        n += 1
        if n % 3 == 0:
            e.tap("A", 0)
    e.screens().save(f"{out}/battle_{tag}_menu.png")
    print(tag, "frames", n, "menu", e.battle_menu_up())


def main():
    if sys.argv[1] == "--one":
        one(*sys.argv[2:5], int(sys.argv[5]))
        return
    rom_dir, out = sys.argv[1:3]
    os.makedirs(out, exist_ok=True)
    for tag, x in TRAINERS:
        subprocess.run([sys.executable, __file__, "--one", rom_dir, out, tag, str(x)], check=True)


if __name__ == "__main__":
    main()

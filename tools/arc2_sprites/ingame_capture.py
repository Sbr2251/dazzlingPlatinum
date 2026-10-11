#!/usr/bin/env python3
"""Capture the scratch placement (scratch_events.py) headlessly.

    SDL_VIDEODRIVER=dummy A2_REPO=<worktree> ~/.venvs/desmume39/bin/python \
        tools/arc2_sprites/ingame_capture.py ROM_DIR OUT_DIR TAG [HOUR ...]

ROM_DIR holds dazzlingPlatinum.nds + main.nef.xMAP copied from the scratch build. Uses the Arc 2 harness
(/tmp/a2/harness/a2lib.py, golden save /tmp/a2/golden/post_gym1.sav) and boots on Twinleaf at (116,886)
facing up. Writes OUT_DIR/<TAG>_h<HOUR>.png (top screen, 256x192) plus a short sequence of frames
(every 4 frames) for the walk cycles. Each hour runs in its own process (one emulator per process).
The clock is pinned through sDebugClockHour (src/rtc.c).
"""

import os
import subprocess
import sys

sys.path.insert(0, "/tmp/a2/harness")


def capture_one(rom_dir, out, tag, hour, n):
    import a2lib
    rom, xmap = os.path.join(rom_dir, "dazzlingPlatinum.nds"), os.path.join(rom_dir, "main.nef.xMAP")
    sav = os.path.join(out, f"{tag}.sav")
    a2lib.make_state(sav, "MAP_HEADER_TWINLEAF_TOWN", 116, 886, "UP")
    e = a2lib.boot(rom, xmap, sav, out, expect_map="MAP_HEADER_TWINLEAF_TOWN")
    clock = a2lib.h.read_xmap(xmap)["sDebugClockHour"][0]
    for _ in range(40):
        e.write(clock, bytes([hour]))
        e.run(10)
    e.screens().crop((0, 0, 256, 192)).save(f"{out}/{tag}_h{hour}.png")
    for i in range(n):
        e.write(clock, bytes([hour]))
        e.run(4)
        e.screens().crop((0, 0, 256, 192)).save(f"{out}/{tag}_h{hour}_seq_{i:03d}.png")
    print(tag, hour, e.state())


def main():
    if sys.argv[1] == "--one":
        rom_dir, out, tag, hour, n = sys.argv[2:7]
        capture_one(rom_dir, out, tag, int(hour), int(n))
        return
    rom_dir, out, tag = sys.argv[1:4]
    hours = [int(h) for h in sys.argv[4:]] or [12]
    os.makedirs(out, exist_ok=True)
    for k, hour in enumerate(hours):
        n = 120 if k == 0 else 1
        subprocess.run([sys.executable, __file__, "--one", rom_dir, out, tag, str(hour), str(n)], check=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Garius (the rival): front battle sprite, the pose shown as a battle starts.

An original pose, drawn by hand and not derived from any stock frame: facing the viewer
square-on, feet apart, both hands in the pockets of his father's jacket. Stock sprites
are used only as a size reference (a stock teen such as Lucas is about 65 px tall).

    python3 tools/garius_sprite/garius_battle.py            # write both 80x80 frames (160x80)
    python3 tools/garius_sprite/garius_battle.py --preview  # also the preview (needs PIL)

Two frames for the intro animation (bowed with eyes shut, then looking up). Design
frames only: not wired into res/trainers/classes/meson.build yet.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "arc1_sprites"))

from garius import LEGEND  # noqa: E402
from garius import PALETTE as OVERWORLD_PALETTE  # noqa: E402
from integrate_mawile_overworld_sprite import write_indexed_png  # noqa: E402
from pixelkit import parse_grid  # noqa: E402

SIZE = 80
FRAME = REPO_ROOT / "res/trainers/classes/garius/front_design.png"
PREVIEW = REPO_ROOT / "docs/story/art/garius_battle_design.png"

# The overworld palette with one change: the skin shadow and the jacket's dark tone share
# one rust brown (index 5), which frees index 8 for a second trouser tone.
PALETTE = list(OVERWORLD_PALETTE)
PALETTE[5] = (150, 72, 44)   # S rust: skin shadow and jacket dark
PALETTE[8] = (60, 60, 76)    # C charcoal dark
PALETTE[13] = (102, 102, 118)  # c charcoal mid

LEGEND = dict(LEGEND, D=8)
del LEGEND["O"]

LEG = "|.......KDcccDK..KDcccDK.......|"
KNEE = "|.......KDDccDK..KDccDDK.......|"

FRONT_ORIGIN = (25, 13)
FRONT = """
|.................HHH..........|
|...............HHhiiH.........|
|..........HHHHHhhiihH.........|
|........HHhhhihhiihhhH........|
|.......HhhhiihhhihhhhhH.......|
|......HhhhiihhhhhhhHhhhH......|
|......HhhhihhhhHhhhHhhhH......|
|......HhhhhhhhHhhhHhhhhH......|
|......HhhHhhHhhhHhhhhHhH......|
|......HhHhHsHhsaHhsHhHhH......|
|.......HHssssHaaasaHsHH.......|
|.......KHSSSaaaaaaSSSHK.......|
|.......KsaeKaaaaaaKeasK.......|
|.......KsawKaaaaaaKwasK.......|
|.......KSaaaaaasaaaaaSK.......|
|........KsaaaaaaaSaasK........|
|........KsaaaaSSSaaasK........|
|.........KKsaaaaaasKK.........|
|......KwwK.KSssssSK.KwwK......|
|....KKpwwsKKSssssSKKswwpKK....|
|..KKopppwwsKttttttKswwpppoKK..|
|.KoopppowwSttttttttSwwopppooK.|
|.KoppoSopowttttttttwopoSoppoK.|
|.KoppoSopowHttttttHwopoSoppoK.|
|.KoppoSoppwHttttttHwppoSoppoK.|
|.KopooSoppwHttttttHwppoSoopoK.|
|.KopoSSoppwHttttttHwppoSSopoK.|
|.KopoSooppwHttttttHwppooSopoK.|
|.KopoSoopowHttttttHwopooSopoK.|
|KoopoSoopowHttttttHwopooSopooK|
|KoppoSoopowHttttttHwopooSoppoK|
|KopooSooopwHttttttHwpoooSoopoK|
|KSoooSKKKowHttttttHwoKKKSoooSK|
|.KSooooSKowHttttttHwoKSooooSK.|
|..KSSoooKowHttttttHwoKoooSSK..|
|...KKSSoSowHttttttHwoSoSSKK...|
|.....KSooowHttttttHwoooSK.....|
|.....KSoopwHHttttHHwpooSK.....|
|.....KSSoowDDDDDDDDwooSSK.....|
|.....KKSSSKccccccccKSSSKK.....|
|........KcccccDDcccccK........|
|........KccccDccDccccK........|
|........KDcccDKKDcccDK........|
""" + "\n".join([LEG] * 7 + [KNEE] * 2 + [LEG] * 9) + """
|.......KDccDDK..KDDccDK.......|
|......KwwSSwK....KwSSwwK......|
|.....KwwwwwwK....KwwwwwwK.....|
|.....KKKKKKKK....KKKKKKKK.....|
"""

# His father's pocket watch: a chain from under the jacket hem, the watch on the thigh.
WATCH = [(19, 42), (19, 43), (18, 44), (19, 44), (18, 45), (19, 45)]


HEAD_ROWS = 18  # the first rows of FRONT, down to the chin

# Frame 1 of the intro: head bowed one pixel, eyes shut, mouth flat. Frame 2 is FRONT
# itself: he looks up at you and the smirk appears. Rows are indexes into FRONT.
BOWED = {
    12: "|.......KsaaaaaaaaaaaasK.......|",
    13: "|.......KsaKKaaaaaaKKasK.......|",
    15: "|........KsaaaaaaaaaasK........|",
    16: "|........KsaaaaSSaaaasK........|",
}
TORSO_ROWS = 22  # collar to jacket hem, after the head


def _draw(frame: list[int], rows: list[str], oy: int) -> None:
    ox = FRONT_ORIGIN[0]
    for gy, row in enumerate(rows):
        for gx, ch in enumerate(row):
            if ch != ".":
                frame[(oy + gy) * SIZE + ox + gx] = LEGEND[ch]


def front_frames() -> list[list[int]]:
    """[frame 1 (bowed, eyes shut), frame 2 (looking up, smirking)]."""
    ox, oy = FRONT_ORIGIN
    grid = parse_grid(FRONT)
    # Slim each arm by one column so the shoulders suit the head (drawn 30 wide, used 28).
    for n in range(HEAD_ROWS, HEAD_ROWS + TORSO_ROWS):
        row = grid[n]
        grid[n] = "." + row[:4] + row[5:25] + row[26:] + "."
    assert oy + len(grid) <= SIZE - 2, len(grid)
    frames = []
    for bowed in (True, False):
        frame = [0] * (SIZE * SIZE)
        _draw(frame, grid[HEAD_ROWS:], oy + HEAD_ROWS)
        for gx, gy in WATCH:
            frame[(oy + gy) * SIZE + ox + gx] = LEGEND["g"]
        head = list(grid[:HEAD_ROWS])
        if bowed:
            for n, row in BOWED.items():
                head[n] = parse_grid(row)[0]
        _draw(frame, head, oy + (1 if bowed else 0))
        frames.append(frame)
    return frames


def preview(frames: list[list[int]], scale: int = 4) -> None:
    from PIL import Image

    bg = (197, 189, 156)
    strip = Image.new("RGB", (SIZE * 4, SIZE), bg)
    for n, name in enumerate(("rival", 0, 1, "galactic_boss")):
        if isinstance(name, int):
            for i, v in enumerate(frames[name]):
                if v:
                    strip.putpixel((n * SIZE + i % SIZE, i // SIZE), PALETTE[v])
            continue
        im = Image.open(REPO_ROOT / "res/trainers/classes" / name / "front_scan.png")
        stock = im.convert("RGB").crop((0, 0, SIZE, SIZE))
        first = stock.getpixel((0, 0))
        for y in range(SIZE):
            for x in range(SIZE):
                px = stock.getpixel((x, y))
                strip.putpixel((n * SIZE + x, y), bg if px == first else px)
    big = strip.resize((strip.width * scale, SIZE * scale), Image.NEAREST)
    out = Image.new("RGB", (big.width, big.height + SIZE + 16), bg)
    out.paste(big, (0, 0))
    out.paste(strip, (8, big.height + 8))
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    out.save(PREVIEW)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    frames = front_frames()
    sheet = [0] * (SIZE * 2 * SIZE)  # both frames side by side, like a stock front_scan.png
    for n, frame in enumerate(frames):
        for i, v in enumerate(frame):
            sheet[(i // SIZE) * SIZE * 2 + n * SIZE + i % SIZE] = v
    snapped = [tuple(((ch >> 3) << 3) | (ch >> 5) for ch in rgb) for rgb in PALETTE]
    FRAME.parent.mkdir(parents=True, exist_ok=True)
    write_indexed_png(FRAME, SIZE * 2, SIZE, sheet, snapped)
    if args.preview:
        preview(frames)
    return 0


if __name__ == "__main__":
    sys.exit(main())

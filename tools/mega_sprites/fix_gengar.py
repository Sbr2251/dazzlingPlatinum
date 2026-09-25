#!/usr/bin/env python3
"""Restore the Mega Gengar battle sprites.

The sprites from commit 2bb0d86b2 were a clean 16-colour Mega Gengar. A later
"direction fix" swapped the front for a different sprite whose background was
palette index 1 (a green box), and edited the palette so the back rendered as
noise. This restores the 2bb0d86b2 art and palettes, then:

  - mirrors both front frames so Gengar faces left like other Gen 4 fronts
    (its face sat 5-9 px right of centre);
  - lifts the purples so the body separates from its shading against dark
    battle backgrounds. The shiny ramp is already light grey, so only the
    normal palette changes;
  - replaces both second frames. The originals were smaller, differently
    posed drawings (front 1790 px vs 2478), so the idle animation shrank and
    jumped. Frame 2 is now frame 1 with a few near-duplicate rows removed, so
    the upper body dips 1-3 px (2 px on the back) while the claws, feet and
    shadow stay put;
  - shades the back, which was mostly flat index 2: a lit band on the
    upper-left edges, spike-tip highlights, a shadow on the lower-right edges,
    and the front's magenta shadow tint on the legs.

The .png.key files are left alone; they are arbitrary encryption seeds.

Run with a Python that has Pillow, e.g. ~/.venvs/desmume/bin/python.
"""

import io
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MEGA_DIR = ROOT / "res/pokemon/gengar/forms/mega"
SOURCE_REV = "2bb0d86b2"
FRAME_SIZE = 80
FRAME_COUNT = 2
TRANSPARENT_RGB = (0, 128, 0)

# index: (old, new). Old values are checked so a changed source fails loudly.
NORMAL_LIFT = {
    1: ((32, 16, 48), (40, 24, 64)),
    2: ((56, 32, 80), (72, 40, 96)),
    3: ((80, 48, 112), (104, 64, 144)),
    4: ((112, 64, 144), (128, 80, 168)),
    14: ((64, 24, 64), (80, 32, 80)),
    15: ((96, 40, 96), (104, 48, 104)),
}


def git_show(name: str) -> bytes:
    path = f"res/pokemon/gengar/forms/mega/{name}"
    return subprocess.check_output(["git", "show", f"{SOURCE_REV}:{path}"], cwd=ROOT)


def read_jasc(data: bytes) -> list[tuple[int, int, int]]:
    lines = [line for line in data.decode("ascii").splitlines()[3:] if line.strip()]
    colors = [tuple(int(v) for v in line.split()) for line in lines]
    assert len(colors) == 16, len(colors)
    return colors


def write_jasc(path: Path, colors: list[tuple[int, int, int]]) -> None:
    lines = ["JASC-PAL", "0100", "16"] + [f"{r} {g} {b}" for r, g, b in colors]
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode("ascii"))


def load_indices(data: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(data))
    assert im.mode == "P" and im.size == (FRAME_SIZE * FRAME_COUNT, FRAME_SIZE), (im.mode, im.size)
    # Image.point() on a P image maps the palette, so read the raw indices.
    return Image.frombytes("L", im.size, im.tobytes())


def mirror_frames(indices: Image.Image) -> Image.Image:
    out = indices.copy()
    for frame in range(FRAME_COUNT):
        box = (frame * FRAME_SIZE, 0, (frame + 1) * FRAME_SIZE, FRAME_SIZE)
        out.paste(indices.crop(box).transpose(Image.Transpose.FLIP_LEFT_RIGHT), box[:2])
    return out


# Rows of frame 1 dropped to make frame 2: each is almost identical to the row
# above it, so removing it lowers everything above without a visible seam.
FRONT_SQUASH_ROWS = (11, 26, 36)
BACK_SQUASH_ROWS = (32, 56)

# Back shading. Index 13 is the outline; 1-5 are the purple ramp, dark to light;
# 14 and 15 are the magenta the front uses on its lower body.
OUTLINE = 13
OPEN = (0, OUTLINE)
BACK_LEG_ROWS = range(58, 67)
LEG_TINT = {1: 14, 2: 14, 3: 15, 4: 15}

Grid = list[list[int]]


def get_frame(indices: Image.Image, frame: int) -> Grid:
    return [[indices.getpixel((frame * FRAME_SIZE + x, y)) for x in range(FRAME_SIZE)]
            for y in range(FRAME_SIZE)]


def put_frame(indices: Image.Image, frame: int, grid: Grid) -> None:
    for y, row in enumerate(grid):
        for x, value in enumerate(row):
            indices.putpixel((frame * FRAME_SIZE + x, y), value)


def squash(grid: Grid, rows: tuple[int, ...]) -> Grid:
    kept = [row[:] for y, row in enumerate(grid) if y not in rows]
    return [[0] * FRAME_SIZE for _ in rows] + kept


def distance_to_open(grid: Grid, x: int, y: int, dx: int, dy: int, limit: int = 4) -> int:
    for d in range(1, limit + 1):
        xx, yy = x + dx * d, y + dy * d
        if not (0 <= xx < FRAME_SIZE and 0 <= yy < FRAME_SIZE) or grid[yy][xx] in OPEN:
            return d
    return limit + 1


def shade_back(grid: Grid) -> Grid:
    out = [row[:] for row in grid]
    for y in range(FRAME_SIZE):
        for x in range(FRAME_SIZE):
            value = grid[y][x]
            if value not in (2, 3):
                continue
            lit = min(distance_to_open(grid, x, y, 0, -1), distance_to_open(grid, x, y, -1, 0),
                      distance_to_open(grid, x, y, -1, -1))
            shadow = min(distance_to_open(grid, x, y, 0, 1), distance_to_open(grid, x, y, 1, 0))
            if value == 2:
                if lit == 1:
                    out[y][x] = 4
                elif lit <= 3:
                    out[y][x] = 3
                elif shadow <= 2:
                    out[y][x] = 1
            elif lit <= 2:
                out[y][x] = 5 if lit == 1 else 4

    # Spike tips: lit pixels open both above and to the left, brightest where
    # the diagonal is open too.
    for y in range(1, FRAME_SIZE):
        for x in range(1, FRAME_SIZE):
            if out[y][x] in (4, 5) and grid[y - 1][x] in OPEN and grid[y][x - 1] in OPEN:
                out[y][x] = 6 if grid[y - 1][x - 1] in OPEN else 5

    # The legs take the front's magenta tint, with one dithered row at the top.
    top = BACK_LEG_ROWS.start
    for y in BACK_LEG_ROWS:
        for x in range(FRAME_SIZE):
            value = out[y][x]
            if value in LEG_TINT and (y >= top + 3 or (y == top + 2 and (x + y) % 2 == 0) or value == 1):
                out[y][x] = LEG_TINT[value]
    return out


def rebuild_second_frame(indices: Image.Image, rows: tuple[int, ...], shade=None) -> Image.Image:
    out = indices.copy()
    first = get_frame(indices, 0)
    if shade:
        first = shade(first)
        put_frame(out, 0, first)
    put_frame(out, 1, squash(first, rows))
    return out


def save_indexed(path: Path, indices: Image.Image, colors: list[tuple[int, int, int]]) -> None:
    im = Image.frombytes("P", indices.size, indices.tobytes())
    im.putpalette([c for rgb in colors for c in rgb])
    im.save(path, bits=4, optimize=False)


def main() -> None:
    normal = read_jasc(git_show("normal.pal"))
    shiny = read_jasc(git_show("shiny.pal"))
    assert normal[0] == TRANSPARENT_RGB and shiny[0] == TRANSPARENT_RGB

    for index, (old, new) in NORMAL_LIFT.items():
        assert normal[index] == old, (index, normal[index])
        normal[index] = new

    front = mirror_frames(load_indices(git_show("front.png")))
    front = rebuild_second_frame(front, FRONT_SQUASH_ROWS)
    back = rebuild_second_frame(load_indices(git_show("back.png")), BACK_SQUASH_ROWS, shade_back)

    save_indexed(MEGA_DIR / "front.png", front, normal)
    save_indexed(MEGA_DIR / "back.png", back, normal)
    write_jasc(MEGA_DIR / "normal.pal", normal)
    write_jasc(MEGA_DIR / "shiny.pal", shiny)
    print(f"Restored Mega Gengar from {SOURCE_REV} into {MEGA_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

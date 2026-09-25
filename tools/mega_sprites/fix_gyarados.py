#!/usr/bin/env python3
"""Rebuild the Mega Gyarados battle sprites from their last good revision.

Commit d9f8565c3 reordered the Mega Gyarados palette. The front was remapped
to match, but the back was not, so the back rendered as red/green noise and
palette slot 1 became a second copy of the background green. This restores
the front and both palettes from 2bb0d86b2, where they agree. The d9f8565c3
reorder changed no colours, so normal and shiny look the same as it intended.
The back is rebuilt by fix_gyarados_back.py, which must run after this.

The 2bb0d86b2 front has a 1-px border (index 15) drawn around both frames.
Long straight runs of it are erased, then any tiny index-15 fragments that
were left detached.

Run with a Python that has Pillow (e.g. ~/.venvs/desmume/bin/python).
Reads from git, so it can be re-run safely.
"""

import io
import struct
import subprocess
import zlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MEGA_DIR = ROOT / "res/pokemon/gyarados/forms/mega"
SOURCE_REV = "2bb0d86b2"
FRAME_SIZE = 80
FRAME_COUNT = 2
BORDER_INDEX = 15
MIN_LINE_RUN = 20
MAX_FRAGMENT_SIZE = 4


def git_show(name: str) -> bytes:
    path = (MEGA_DIR / name).relative_to(ROOT).as_posix()
    return subprocess.check_output(["git", "show", f"{SOURCE_REV}:{path}"], cwd=ROOT)


def read_palette(data: bytes) -> list[tuple[int, int, int]]:
    lines = [line for line in data.decode().splitlines()[3:] if line.strip()]
    return [tuple(int(v) for v in line.split()) for line in lines[:16]]


def write_palette(path: Path, colours: list[tuple[int, int, int]]) -> None:
    lines = ["JASC-PAL", "0100", "16"] + [f"{r} {g} {b}" for r, g, b in colours]
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode())


def load_indices(data: bytes) -> list[list[int]]:
    image = Image.open(io.BytesIO(data))
    assert image.mode == "P" and image.size == (FRAME_SIZE * FRAME_COUNT, FRAME_SIZE)
    raw = image.tobytes()
    width = image.size[0]
    return [list(raw[y * width:(y + 1) * width]) for y in range(FRAME_SIZE)]


def erase_border_lines(pixels: list[list[int]], x0: int) -> int:
    erased = set()
    xs = range(x0, x0 + FRAME_SIZE)

    for y in range(FRAME_SIZE):
        run = []
        for x in list(xs) + [None]:
            if x is not None and pixels[y][x] == BORDER_INDEX:
                run.append((x, y))
                continue
            if len(run) >= MIN_LINE_RUN:
                erased.update(run)
            run = []

    for x in xs:
        run = []
        for y in list(range(FRAME_SIZE)) + [None]:
            if y is not None and pixels[y][x] == BORDER_INDEX:
                run.append((x, y))
                continue
            if len(run) >= MIN_LINE_RUN:
                erased.update(run)
            run = []

    for x, y in erased:
        pixels[y][x] = 0
    return len(erased)


def erase_border_fragments(pixels: list[list[int]], x0: int) -> list[tuple[int, int]]:
    seen = set()
    erased = []
    for y in range(FRAME_SIZE):
        for x in range(x0, x0 + FRAME_SIZE):
            if pixels[y][x] == 0 or (x, y) in seen:
                continue
            component = []
            stack = [(x, y)]
            seen.add((x, y))
            while stack:
                cx, cy = stack.pop()
                component.append((cx, cy))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if (x0 <= nx < x0 + FRAME_SIZE and 0 <= ny < FRAME_SIZE
                                and pixels[ny][nx] and (nx, ny) not in seen):
                            seen.add((nx, ny))
                            stack.append((nx, ny))
            if len(component) <= MAX_FRAGMENT_SIZE and all(pixels[cy][cx] == BORDER_INDEX for cx, cy in component):
                for cx, cy in component:
                    pixels[cy][cx] = 0
                erased.extend(component)
    return erased


def save_sprite(path: Path, pixels: list[list[int]], colours: list[tuple[int, int, int]]) -> None:
    image = Image.frombytes("P", (FRAME_SIZE * FRAME_COUNT, FRAME_SIZE), bytes(v for row in pixels for v in row))
    image.putpalette([c for colour in colours for c in colour])
    image.save(path, bits=4)
    key = zlib.crc32(path.read_bytes()) or 1
    path.with_suffix(path.suffix + ".key").write_bytes(struct.pack("<I", key))


def main() -> None:
    normal = read_palette(git_show("normal.pal"))
    shiny = read_palette(git_show("shiny.pal"))
    assert normal[0] == (0, 128, 0) and normal[1] != normal[0]

    # The back is rebuilt from the Smogon Sprite Project art by
    # fix_gyarados_back.py; run that after this.
    for name in ("front.png",):
        pixels = load_indices(git_show(name))
        for frame in range(FRAME_COUNT):
            x0 = frame * FRAME_SIZE
            lines = erase_border_lines(pixels, x0)
            fragments = erase_border_fragments(pixels, x0) if lines else []
            print(f"{name} frame {frame}: erased {lines} line px, {len(fragments)} fragment px {fragments}")
        save_sprite(MEGA_DIR / name, pixels, normal)

    write_palette(MEGA_DIR / "normal.pal", normal)
    write_palette(MEGA_DIR / "shiny.pal", shiny)


if __name__ == "__main__":
    main()

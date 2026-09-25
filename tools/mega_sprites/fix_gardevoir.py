#!/usr/bin/env python3
"""Rebuild the Mega Gardevoir battle sprites from their last intact version.

Commit 2bb0d86b2 has the only Mega Gardevoir sprites whose pixels and palettes
agree. Later commits remapped the indices without updating normal.pal, which
garbled the back, and filled the front's background with speckle. This script
restores that version and cleans it up:

  - erases the 1 px frame line drawn around the edges of each front frame
  - erases isolated specks (1-2 px) that aren't part of the green hair swirls
  - mirrors the front so it faces left, like the Gen 4 front sprites
  - recolours stray hair-green pixels scattered over the gown and body, and
    erases the ones floating loose in the background
  - erases dark specks floating in the swirl or background, cut off from the body
  - fills tiny enclosed holes, then draws a 1 px dark outline around the
    silhouette like the other Gen 4 sprites
  - writes 4-bit PNGs and CRLF JASC palettes

Run from the repository root with a Python that has Pillow, e.g.
    ~/.venvs/desmume/bin/python tools/mega_sprites/fix_gardevoir.py
"""

import subprocess
from collections import Counter
from io import BytesIO
from pathlib import Path

from PIL import Image

SOURCE_COMMIT = "2bb0d86b2"
MEGA_DIR = Path("res/pokemon/gardevoir/forms/mega")
FRAME_SIZE = 80
FRAME_COUNT = 2
SPECK_MAX_SIZE = 2
# Palette indices of the hair greens; small clusters of these are the
# intentional wisps around the swirl, not stray pixels.
HAIR_INDICES = {5, 6, 7, 11}
DARK_HAIR_INDEX = 6
OUTLINE_INDEX = 15
# Green clusters at least this big are the hair and swirl; smaller ones within
# WISP_DISTANCE of them are wisps, anything else is a stray.
HAIR_MIN_SIZE = 20
WISP_DISTANCE = 2
STRAY_GREEN_MAX_SIZE = 3
LOOSE_SPECK_MAX_SIZE = 4
HOLE_MAX_SIZE = 2
NEIGHBOURS_4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
NEIGHBOURS_8 = tuple((dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)


def git_show(name):
    return subprocess.check_output(["git", "show", f"{SOURCE_COMMIT}:{MEGA_DIR / name}"])


def read_palette(data):
    lines = [line for line in data.decode().splitlines()[3:] if line.strip()]
    return [tuple(int(v) for v in line.split()) for line in lines[:16]]


def write_palette(path, palette):
    lines = ["JASC-PAL", "0100", "16"] + [f"{r} {g} {b}" for r, g, b in palette]
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode())


def read_indices(data):
    image = Image.open(BytesIO(data))
    assert image.mode == "P" and image.size == (FRAME_SIZE * FRAME_COUNT, FRAME_SIZE)
    # tobytes() gives palette indices; point() would map through the palette.
    indices = Image.frombytes("L", image.size, image.tobytes())
    return [list(indices.crop((f * FRAME_SIZE, 0, (f + 1) * FRAME_SIZE, FRAME_SIZE)).getdata())
            for f in range(FRAME_COUNT)]


def clear_border(frame):
    for i in range(FRAME_SIZE):
        for x, y in ((i, 0), (i, FRAME_SIZE - 1), (0, i), (FRAME_SIZE - 1, i)):
            frame[y * FRAME_SIZE + x] = 0


def neighbours(p, offsets):
    px, py = p % FRAME_SIZE, p // FRAME_SIZE
    for dx, dy in offsets:
        nx, ny = px + dx, py + dy
        if 0 <= nx < FRAME_SIZE and 0 <= ny < FRAME_SIZE:
            yield ny * FRAME_SIZE + nx


def components(frame, include, offsets=NEIGHBOURS_8):
    seen = set()
    for start in range(len(frame)):
        if start in seen or not include(frame[start]):
            continue
        component, stack = [], [start]
        seen.add(start)
        while stack:
            p = stack.pop()
            component.append(p)
            for n in neighbours(p, offsets):
                if n not in seen and include(frame[n]):
                    seen.add(n)
                    stack.append(n)
        yield component


def surrounding_colour(frame, p, exclude=()):
    counts = Counter(frame[n] for n in neighbours(p, NEIGHBOURS_8) if frame[n] and frame[n] not in exclude)
    if not counts:
        return 0
    # Prefer a body colour over the outline colour on ties.
    return max(counts, key=lambda v: (counts[v], v != OUTLINE_INDEX))


def remove_specks(frame):
    for component in list(components(frame, bool)):
        if len(component) <= SPECK_MAX_SIZE and not all(frame[p] in HAIR_INDICES for p in component):
            for p in component:
                frame[p] = 0


def clean_stray_greens(frame):
    greens = list(components(frame, lambda v: v in HAIR_INDICES))
    hair = [p for c in greens if len(c) >= HAIR_MIN_SIZE for p in c]
    for component in greens:
        if len(component) > STRAY_GREEN_MAX_SIZE:
            continue
        members = set(component)
        body = transparent = 0
        for p in component:
            for n in neighbours(p, NEIGHBOURS_8):
                if n in members:
                    continue
                if not frame[n]:
                    transparent += 1
                elif frame[n] not in HAIR_INDICES:
                    body += 1
        near_hair = any(abs(p % FRAME_SIZE - h % FRAME_SIZE) <= WISP_DISTANCE
                        and abs(p // FRAME_SIZE - h // FRAME_SIZE) <= WISP_DISTANCE
                        for p in component for h in hair)
        if near_hair and transparent >= body:
            continue
        for p in component:
            frame[p] = surrounding_colour(frame, p, HAIR_INDICES) if body >= transparent else 0


def clean_loose_specks(frame):
    for component in list(components(frame, lambda v: v and v not in HAIR_INDICES)):
        if len(component) > LOOSE_SPECK_MAX_SIZE:
            continue
        for p in component:
            enclosed = all(frame[n] for n in neighbours(p, NEIGHBOURS_4))
            frame[p] = DARK_HAIR_INDEX if enclosed else 0


def fill_holes(frame):
    for component in list(components(frame, lambda v: v == 0, NEIGHBOURS_4)):
        edge = any(p % FRAME_SIZE in (0, FRAME_SIZE - 1) or p // FRAME_SIZE in (0, FRAME_SIZE - 1)
                   for p in component)
        if len(component) <= HOLE_MAX_SIZE and not edge:
            for p in component:
                frame[p] = surrounding_colour(frame, p)


def add_outline(frame):
    ring = [p for p in range(len(frame))
            if not frame[p] and any(frame[n] for n in neighbours(p, NEIGHBOURS_4))]
    for p in ring:
        frame[p] = OUTLINE_INDEX


def polish(frame):
    clean_stray_greens(frame)
    clean_loose_specks(frame)
    fill_holes(frame)
    add_outline(frame)


def mirror(frame):
    return [frame[y * FRAME_SIZE + (FRAME_SIZE - 1 - x)] for y in range(FRAME_SIZE) for x in range(FRAME_SIZE)]


def write_png(path, frames, palette):
    image = Image.new("P", (FRAME_SIZE * FRAME_COUNT, FRAME_SIZE))
    for f, frame in enumerate(frames):
        strip = Image.new("P", (FRAME_SIZE, FRAME_SIZE))
        strip.putdata(frame)
        image.paste(strip, (f * FRAME_SIZE, 0))
    image.putpalette([c for rgb in palette for c in rgb])
    image.save(path, bits=4, optimize=False)


def main():
    normal = read_palette(git_show("normal.pal"))
    shiny = read_palette(git_show("shiny.pal"))

    front = read_indices(git_show("front.png"))
    for frame in front:
        clear_border(frame)
        remove_specks(frame)
    front = [mirror(frame) for frame in front]
    for frame in front:
        polish(frame)

    back = read_indices(git_show("back.png"))
    for frame in back:
        clear_border(frame)
        remove_specks(frame)
        polish(frame)

    write_png(MEGA_DIR / "front.png", front, normal)
    write_png(MEGA_DIR / "back.png", back, normal)
    write_palette(MEGA_DIR / "normal.pal", normal)
    write_palette(MEGA_DIR / "shiny.pal", shiny)
    print(f"Rebuilt Mega Gardevoir sprites in {MEGA_DIR} from {SOURCE_COMMIT}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build the Mega Gyarados back sprite from the Smogon Sprite Project art.

Source: Mega Gyarados Gen 5-style back sprite by the Smogon Sprite Project,
downloaded from Pokemon Showdown
(https://play.pokemonshowdown.com/sprites/gen5-back/gyarados-mega.png).

The front and back share normal.pal and shiny.pal, and the front uses a
custom colour scheme (navy body, orange fins, red whiskers), so each source
colour is mapped onto an existing palette slot instead of adding colours.
Slot 4 is unused by the front; its normal/shiny entries already sit on the
body ramps, so it takes the light-blue highlight. Because every slot keeps
its shiny entry, the shiny back follows the front's shiny scheme.

The 94x91 figure does not fit an 80x80 frame, so it is shrunk to 82% by
coverage voting (outline pixels weighted up so thin lines survive), then
body/fin pixels left touching transparency are turned into outline.
Frame 2 is an idle breath: the top of the body rises 2 px, easing to 0 px
at the tail, so the pose stays the same.

Run fix_gyarados.py first (it restores the front and palettes), then this.
Run with a Python that has Pillow (e.g. ~/.venvs/desmume/bin/python).
Pass a directory to reuse an already downloaded source PNG.
"""

import io
import struct
import sys
import urllib.request
import zlib
from collections import defaultdict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MEGA_DIR = ROOT / "res/pokemon/gyarados/forms/mega"
SOURCE_URL = "https://play.pokemonshowdown.com/sprites/gen5-back/gyarados-mega.png"
FRAME_SIZE = 80
SCALE = 0.82
OUTLINE_INDEX = 15
OUTLINE_WEIGHT = 1.6
FRAME_X = 2
FRAME_BOTTOM = 77
BREATH_RISE = 2
BREATH_END = 0.6

# Showdown colour -> palette slot (see normal.pal).
COLOUR_TO_INDEX = {
    (27, 104, 167): 1,    # body blue
    (33, 146, 228): 4,    # body highlight
    (20, 79, 126): 3,     # body shade
    (19, 45, 91): 5,      # body dark
    (19, 20, 23): 15,     # outline
    (39, 40, 45): 12,     # belly
    (60, 63, 71): 12,     # belly highlight
    (230, 65, 74): 6,     # spots
    (153, 33, 55): 7,     # spot shade
    (200, 176, 120): 8,   # fins -> orange
    (240, 224, 168): 14,  # fin highlight -> light orange
    (95, 69, 35): 7,      # fin shade
    (240, 240, 240): 6,   # whiskers -> red, as on the front
    (103, 104, 107): 7,   # whisker shade
}
# Slots that get an outline where they touch transparency. Whisker/spot reds
# are left alone so the 1-px whiskers don't turn black.
OUTLINED = {1, 3, 4, 5, 8, 14}


def load_source(cache: Path | None) -> Image.Image:
    if cache is not None and (cache / "gen5-back.png").exists():
        return Image.open(cache / "gen5-back.png").convert("RGBA")
    data = urllib.request.urlopen(SOURCE_URL).read()
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / "gen5-back.png").write_bytes(data)
    return Image.open(io.BytesIO(data)).convert("RGBA")


def to_indices(image: Image.Image) -> list[list[int]]:
    width, height = image.size
    pixels = image.load()
    rows = []
    for y in range(height):
        row = []
        for x in range(width):
            r, g, b, a = pixels[x, y]
            row.append(COLOUR_TO_INDEX[(r, g, b)] if a else 0)
        rows.append(row)
    return rows


def shrink(src: list[list[int]], bbox: tuple[int, int, int, int]) -> list[list[int]]:
    x0, y0, x1, y1 = bbox
    height, width = len(src), len(src[0])
    out_w = round((x1 - x0) * SCALE)
    out_h = round((y1 - y0) * SCALE)
    out = [[0] * out_w for _ in range(out_h)]
    for oy in range(out_h):
        ay, by = y0 + oy / SCALE, y0 + (oy + 1) / SCALE
        for ox in range(out_w):
            ax, bx = x0 + ox / SCALE, x0 + (ox + 1) / SCALE
            coverage = defaultdict(float)
            for sy in range(int(ay), min(int(by - 1e-9) + 1, height)):
                for sx in range(int(ax), min(int(bx - 1e-9) + 1, width)):
                    area = (min(bx, sx + 1) - max(ax, sx)) * (min(by, sy + 1) - max(ay, sy))
                    if area > 0:
                        value = src[sy][sx]
                        coverage[value] += area * (OUTLINE_WEIGHT if value == OUTLINE_INDEX else 1)
            out[oy][ox] = max(coverage, key=coverage.get)
    return out


def repair_outline(pixels: list[list[int]]) -> int:
    height, width = len(pixels), len(pixels[0])
    edges = []
    for y in range(height):
        for x in range(width):
            if pixels[y][x] not in OUTLINED:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < width and 0 <= ny < height) or pixels[ny][nx] == 0:
                    edges.append((x, y))
                    break
    for x, y in edges:
        pixels[y][x] = OUTLINE_INDEX
    return len(edges)


def place(figure: list[list[int]]) -> list[list[int]]:
    frame = [[0] * FRAME_SIZE for _ in range(FRAME_SIZE)]
    top = FRAME_BOTTOM + 1 - len(figure)
    for y, row in enumerate(figure):
        for x, value in enumerate(row):
            frame[top + y][FRAME_X + x] = value
    return frame


def breathe(frame: list[list[int]]) -> list[list[int]]:
    rows = [y for y in range(FRAME_SIZE) if any(frame[y])]
    top, bottom = rows[0], rows[-1]
    end = top + (bottom - top) * BREATH_END
    out = [[0] * FRAME_SIZE for _ in range(FRAME_SIZE)]
    for y in range(FRAME_SIZE):
        # Rows near the top take their pixels from further down, so the body
        # rises; the offset eases to 0 by BREATH_END of the figure's height.
        t = max(0.0, (end - y) / (end - top + BREATH_RISE))
        source = min(FRAME_SIZE - 1, y + round(BREATH_RISE * min(1.0, t)))
        out[y] = frame[source][:]
    return out


def read_palette(path: Path) -> list[tuple[int, int, int]]:
    lines = [line for line in path.read_text().splitlines()[3:] if line.strip()]
    return [tuple(int(v) for v in line.split()) for line in lines[:16]]


def save_sprite(path: Path, frames: list[list[list[int]]], colours: list[tuple[int, int, int]]) -> None:
    rows = [sum((frame[y] for frame in frames), []) for y in range(FRAME_SIZE)]
    image = Image.frombytes("P", (FRAME_SIZE * len(frames), FRAME_SIZE), bytes(v for row in rows for v in row))
    image.putpalette([c for colour in colours for c in colour])
    image.save(path, bits=4)
    key = zlib.crc32(path.read_bytes()) or 1
    path.with_suffix(path.suffix + ".key").write_bytes(struct.pack("<I", key))


def main() -> None:
    cache = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    source = load_source(cache)
    figure = shrink(to_indices(source), source.getbbox())
    outlined = repair_outline(figure)
    # Keep row/column 0 and 79 empty in both frames.
    assert FRAME_X + len(figure[0]) <= FRAME_SIZE - 1 and len(figure) + BREATH_RISE <= FRAME_BOTTOM
    frame1 = place(figure)
    frame2 = breathe(frame1)
    save_sprite(MEGA_DIR / "back.png", [frame1, frame2], read_palette(MEGA_DIR / "normal.pal"))
    changed = sum(a != b for r1, r2 in zip(frame1, frame2) for a, b in zip(r1, r2))
    print(f"figure {len(figure[0])}x{len(figure)}, {outlined} outline px repaired, frame 2 differs by {changed} px")


if __name__ == "__main__":
    main()

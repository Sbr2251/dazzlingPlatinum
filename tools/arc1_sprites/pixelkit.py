"""Small pixel-art helpers for the Arc 1 field sprites (pure Python, no PIL).

A frame is a flat list of CELL*CELL palette indexes (row-major), index 0 transparent.
Hand-drawn patches are ASCII grids: one character per pixel, mapped to palette
indexes through a legend. Two characters are special in every legend:
  '.'  leave the pixel underneath untouched
  ' '  same as '.' (lets grids be indented / padded)
  '_'  clear the pixel to transparent (index 0)
"""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from integrate_arc1_field_sprites import CELL, _frames_from_member  # noqa: E402
from integrate_mawile_overworld_sprite import read_indexed_png, write_indexed_png  # noqa: E402

MMODEL_DIR = REPO_ROOT / "res/prebuilt/data/mmodel/mmodel"

# Walker frame numbering (0-based): row * 4 + column, rows up/down/left/right,
# columns stand, step A, stand, step B.
UP, DOWN, LEFT, RIGHT = range(4)


def stock_walker(member: int) -> tuple[list[list[int]], list[tuple[int, int, int]]]:
    """The 16 frames and palette of a stock walker mmodel member."""
    return _frames_from_member(MMODEL_DIR / f"mmodel_{member:08d}.bin", 16)


def read_png(path: Path) -> tuple[int, int, list[int], list[tuple[int, int, int]]]:
    return read_indexed_png(path)


def blank() -> list[int]:
    return [0] * (CELL * CELL)


def top_row(frame: list[int]) -> int:
    for y in range(CELL):
        if any(frame[y * CELL : (y + 1) * CELL]):
            return y
    return CELL


def remap(frame: list[int], mapping: dict[int, int]) -> list[int]:
    return [mapping.get(v, v) if v else 0 for v in frame]


def remap_rows(frame: list[int], mapping: dict[int, int], y0: int, y1: int) -> list[int]:
    """Remap only rows y0 <= y < y1."""
    out = list(frame)
    for y in range(max(0, y0), min(CELL, y1)):
        for x in range(CELL):
            v = out[y * CELL + x]
            if v:
                out[y * CELL + x] = mapping.get(v, v)
    return out


def clear_rows(frame: list[int], y0: int, y1: int) -> list[int]:
    out = list(frame)
    for y in range(max(0, y0), min(CELL, y1)):
        out[y * CELL : (y + 1) * CELL] = [0] * CELL
    return out


def parse_grid(text: str) -> list[str]:
    """Strip a triple-quoted grid: drop blank first/last lines and a common '|' margin.

    Grid rows may be written as |....| so trailing spaces stay visible; the bars are removed.
    """
    rows = []
    for line in text.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            line = line[1:-1]
        rows.append(line)
    width = max(len(r) for r in rows)
    if any(len(r) != width for r in rows):
        lengths = sorted({len(r) for r in rows})
        raise ValueError(f"ragged grid (row lengths {lengths}):\n" + "\n".join(rows))
    return rows


def paint(frame: list[int], grid: list[str], legend: dict[str, int], ox: int, oy: int) -> list[int]:
    out = list(frame)
    for gy, row in enumerate(grid):
        for gx, ch in enumerate(row):
            if ch in ". ":
                continue
            x, y = ox + gx, oy + gy
            if not (0 <= x < CELL and 0 <= y < CELL):
                continue
            if ch == "_":
                out[y * CELL + x] = 0
            else:
                out[y * CELL + x] = legend[ch]
    return out


def mirror(frame: list[int]) -> list[int]:
    return [frame[y * CELL + (CELL - 1 - x)] for y in range(CELL) for x in range(CELL)]


def mirror_grid(grid: list[str]) -> list[str]:
    return [row[::-1] for row in grid]


def shift(frame: list[int], dx: int, dy: int) -> list[int]:
    out = blank()
    for y in range(CELL):
        for x in range(CELL):
            v = frame[y * CELL + x]
            if v and 0 <= x + dx < CELL and 0 <= y + dy < CELL:
                out[(y + dy) * CELL + x + dx] = v
    return out


def neighbours(frame: list[int], x: int, y: int, diagonal: bool = True):
    steps = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if diagonal:
        steps += [(-1, -1), (1, -1), (-1, 1), (1, 1)]
    for dx, dy in steps:
        nx, ny = x + dx, y + dy
        if 0 <= nx < CELL and 0 <= ny < CELL:
            yield nx, ny, frame[ny * CELL + nx]


def halo(frame: list[int], index: int, diagonal: bool = False, skip=lambda x, y: False) -> list[int]:
    """Colour every transparent pixel that touches an opaque one with `index`."""
    out = list(frame)
    for y in range(CELL):
        for x in range(CELL):
            if frame[y * CELL + x] or skip(x, y):
                continue
            if any(v for _, _, v in neighbours(frame, x, y, diagonal)):
                out[y * CELL + x] = index
    return out


def check_frame(frame: list[int], name: str) -> None:
    if len(frame) != CELL * CELL:
        raise ValueError(f"{name}: frame has {len(frame)} pixels")
    bad = [v for v in frame if not 0 <= v <= 15]
    if bad:
        raise ValueError(f"{name}: palette index {bad[0]} out of range")


def write_sheet(path: Path, frames: list[list[int]], columns: int, palette: list[tuple[int, int, int]]) -> None:
    """Write frames into a columns-wide 4bpp sheet (frame N at row N // columns)."""
    if len(palette) != 16:
        raise ValueError(f"{path}: palette must have 16 entries")
    rows = (len(frames) + columns - 1) // columns
    width, height = CELL * columns, CELL * rows
    pixels = [0] * (width * height)
    for n, frame in enumerate(frames):
        check_frame(frame, f"{path.name} frame {n}")
        r, c = divmod(n, columns)
        for i, v in enumerate(frame):
            x, y = i % CELL, i // CELL
            pixels[(r * CELL + y) * width + c * CELL + x] = v
    # Snap colours to what the DS will show (BGR555) so the PNG previews honestly.
    snapped = [tuple(((ch >> 3) << 3) | (ch >> 5) for ch in rgb) for rgb in palette]
    path.parent.mkdir(parents=True, exist_ok=True)
    write_indexed_png(path, width, height, pixels, snapped)

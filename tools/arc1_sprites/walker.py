"""Compose a 16-frame walker sheet from a stock walker body plus hand-drawn parts.

The stock body supplies the walk cycle (leg poses and the 1 px bob of every step
frame). A character spec then:
  1. remaps the stock palette indexes onto the character's own 16-colour palette
     (optionally per direction and per row band, e.g. boots vs jacket),
  2. clears everything above a per-direction cut row (the stock head),
  3. paints a hand-drawn head per direction (up, down, left) that follows the bob,
  4. paints body overlays per direction (emblems, collars, coat tails). Overlays
     marked "bob" follow the torso bob; the others are fixed to the cell (legs).
The right-facing row is the mirror image of the left row, exactly as in every
stock Platinum walker (checked on the grunts, gentleman, Cyrus and Looker).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pixelkit import (
    CELL,
    DOWN,
    LEFT,
    UP,
    clear_rows,
    mirror,
    paint,
    parse_grid,
    remap,
    stock_walker,
    top_row,
)


@dataclass
class Part:
    grid: str
    x: int
    y: int
    bob: bool = True  # follow the frame's vertical bob
    frames: tuple[int, ...] = (0, 1, 2, 3)  # columns (stand, step A, stand, step B) it applies to


@dataclass
class Character:
    name: str
    base_member: int
    palette: list[tuple[int, int, int]]
    legend: dict[str, int]
    index_map: dict[int, int]
    cut: dict[int, int]  # direction -> first stock row kept (rows above are cleared, bob-adjusted)
    heads: dict[int, Part]
    overlays: dict[int, list[Part]] = field(default_factory=dict)
    # direction -> list of (y0, y1, mapping) applied to the stock body after index_map,
    # keyed by stock index; rows are those of the stand frame and follow the bob
    band_maps: dict[int, list[tuple[int, int, dict[int, int]]]] = field(default_factory=dict)
    post: object = None  # optional callable(frame, direction, column) -> frame


def bob_of(frames: list[list[int]], number: int) -> int:
    direction = number // 4
    return top_row(frames[number]) - top_row(frames[direction * 4])


def compose(char: Character) -> list[list[int]]:
    base, _ = stock_walker(char.base_member)
    out: list[list[int]] = []
    for number in range(12):
        direction, column = divmod(number, 4)
        bob = bob_of(base, number)
        frame = remap(base[number], char.index_map)
        for y0, y1, mapping in char.band_maps.get(direction, []):
            for y in range(max(0, y0 + bob), min(CELL, y1 + bob)):
                for x in range(CELL):
                    # band maps are written in stock indexes: look at the stock pixel
                    s = base[number][y * CELL + x]
                    if s and s in mapping:
                        frame[y * CELL + x] = mapping[s]
        frame = clear_rows(frame, 0, char.cut[direction] + bob)
        head = char.heads[direction]
        frame = paint(frame, parse_grid(head.grid), char.legend, head.x, head.y + bob)
        for part in char.overlays.get(direction, []):
            if column not in part.frames:
                continue
            frame = paint(frame, parse_grid(part.grid), char.legend, part.x, part.y + (bob if part.bob else 0))
        if char.post:
            frame = char.post(frame, direction, column)
        out.append(frame)
    out += [mirror(out[LEFT * 4 + c]) for c in range(4)]
    return out


__all__ = ["Character", "Part", "compose", "UP", "DOWN", "LEFT"]

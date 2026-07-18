#!/usr/bin/env python3
"""Audit Platinum overworld Totem reachability from an ordinary route entry.

The tool resolves world coordinates through map matrix 0, decodes each 32x32
land-data terrain grid, computes an approximate on-foot connected component,
and ranks collision-free object/approach pairs. Emulator traversal remains the
final authority; this static audit is used to reject impossible anchors and to
select safe candidates before rebuilding.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

MAP_TILES = 32
LAND_HEADER_SIZE = 16
COLLISION_MASK = 0x8000
BEHAVIOR_MASK = 0x00FF

TILE_BEHAVIOR_WATER_RIVER = 0x10
TILE_BEHAVIOR_WATERFALL = 0x13
TILE_BEHAVIOR_WATER_SEA = 0x15
TILE_BEHAVIOR_SHALLOW_WATER = 0x17
TILE_BEHAVIOR_SAND = 0x21
FOOT_BLOCKED_BEHAVIORS = {
    TILE_BEHAVIOR_WATER_RIVER,
    TILE_BEHAVIOR_WATERFALL,
    TILE_BEHAVIOR_WATER_SEA,
}

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "res/field/maps/matrices/map_matrix_000.json"
LAND_DIR = ROOT / "res/field/maps/data"


@dataclass(frozen=True)
class Tile:
    value: int
    header: str
    map_symbol: str

    @property
    def collision(self) -> bool:
        return bool(self.value & COLLISION_MASK)

    @property
    def behavior(self) -> int:
        return self.value & BEHAVIOR_MASK

    @property
    def foot_passable(self) -> bool:
        return not self.collision and self.behavior not in FOOT_BLOCKED_BEHAVIORS

    @property
    def sea(self) -> bool:
        return not self.collision and self.behavior == TILE_BEHAVIOR_WATER_SEA


@dataclass(frozen=True)
class Candidate:
    anchor: tuple[int, int]
    approach: tuple[int, int]
    facing: str
    distance: int
    clearance: int
    object_distance: int
    anchor_behavior: int
    approach_behavior: int


DIRECTIONS = (
    (0, -1, "Up"),
    (0, 1, "Down"),
    (-1, 0, "Left"),
    (1, 0, "Right"),
)


def load_land_attrs(path: Path) -> tuple[int, ...]:
    raw = path.read_bytes()
    terrain_size, props_size, model_size, bdhc_size = struct.unpack_from("<IIII", raw, 0)
    if terrain_size != MAP_TILES * MAP_TILES * 2:
        raise ValueError(f"{path}: unexpected terrain size {terrain_size}")
    expected_size = LAND_HEADER_SIZE + terrain_size + props_size + model_size + bdhc_size
    if expected_size != len(raw):
        raise ValueError(f"{path}: section sizes total {expected_size}, file has {len(raw)}")
    return struct.unpack_from(f"<{MAP_TILES * MAP_TILES}H", raw, LAND_HEADER_SIZE)


def load_route_tiles(header_name: str) -> dict[tuple[int, int], Tile]:
    matrix = json.loads(MATRIX_PATH.read_text())
    headers = matrix["headers"]
    maps = matrix["maps"]
    cache: dict[str, tuple[int, ...]] = {}
    tiles: dict[tuple[int, int], Tile] = {}

    for matrix_z, header_row in enumerate(headers):
        for matrix_x, header in enumerate(header_row):
            if header != header_name:
                continue
            map_symbol = maps[matrix_z][matrix_x]
            match = re.fullmatch(r"MAP_(\d+)", map_symbol)
            if match is None:
                raise ValueError(
                    f"{header_name} cell ({matrix_x},{matrix_z}) has unsupported map symbol {map_symbol}"
                )
            attrs = cache.get(map_symbol)
            if attrs is None:
                member = int(match.group(1))
                attrs = load_land_attrs(LAND_DIR / f"map_data_{member:03d}.bin")
                cache[map_symbol] = attrs
            for local_z in range(MAP_TILES):
                for local_x in range(MAP_TILES):
                    world_x = matrix_x * MAP_TILES + local_x
                    world_z = matrix_z * MAP_TILES + local_z
                    value = attrs[local_z * MAP_TILES + local_x]
                    tiles[(world_x, world_z)] = Tile(value, header, map_symbol)
    return tiles


def neighbors(point: tuple[int, int]) -> Iterable[tuple[int, int]]:
    x, z = point
    for dx, dz, _ in DIRECTIONS:
        yield x + dx, z + dz


def reachable_component(
    tiles: dict[tuple[int, int], Tile],
    start: tuple[int, int],
    blocked: set[tuple[int, int]],
) -> tuple[
    set[tuple[int, int]],
    dict[tuple[int, int], int],
    dict[tuple[int, int], tuple[int, int] | None],
]:
    tile = tiles.get(start)
    if tile is None:
        raise ValueError(f"entry {start} is outside the selected map header")
    if not tile.foot_passable:
        raise ValueError(
            f"entry {start} is not foot-passable: value=0x{tile.value:04X}, behavior=0x{tile.behavior:02X}"
        )

    reached = {start}
    distance = {start: 0}
    predecessor: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    queue = deque([start])
    while queue:
        point = queue.popleft()
        for nxt in neighbors(point):
            next_tile = tiles.get(nxt)
            if (
                nxt in reached
                or nxt in blocked
                or next_tile is None
                or not next_tile.foot_passable
            ):
                continue
            reached.add(nxt)
            distance[nxt] = distance[point] + 1
            predecessor[nxt] = point
            queue.append(nxt)
    return reached, distance, predecessor


def load_events(path: Path) -> tuple[dict[tuple[int, int], str], set[tuple[int, int]]]:
    data = json.loads(path.read_text())
    objects = {
        (int(obj["x"]), int(obj["z"])): str(obj.get("id", obj.get("graphics_id", "OBJECT")))
        for obj in data.get("object_events", [])
    }
    warps = {(int(warp["x"]), int(warp["z"])) for warp in data.get("warp_events", [])}
    return objects, warps


def manhattan_to_nearest(point: tuple[int, int], occupied: set[tuple[int, int]]) -> int:
    if not occupied:
        return 9999
    x, z = point
    return min(abs(x - ox) + abs(z - oz) for ox, oz in occupied)


def visual_clearance(
    tiles: dict[tuple[int, int], Tile], anchor: tuple[int, int], mode: str
) -> int:
    """Count noncollidable cells in a billboard-sized neighborhood.

    The production billboard extends primarily left/up from its logical anchor,
    so this intentionally weights a broad rectangle west of the anchor.
    """

    x, z = anchor
    score = 0
    for check_z in range(z - 4, z + 4):
        for check_x in range(x - 7, x + 3):
            tile = tiles.get((check_x, check_z))
            if tile is None or tile.collision:
                continue
            if mode == "shoreline":
                score += 1
            elif tile.foot_passable:
                score += 1
    return score


def candidate_pairs(
    *,
    tiles: dict[tuple[int, int], Tile],
    reached: set[tuple[int, int]],
    distance: dict[tuple[int, int], int],
    objects: dict[tuple[int, int], str],
    warps: set[tuple[int, int]],
    mode: str,
) -> list[Candidate]:
    occupied = set(objects) | warps
    candidates: list[Candidate] = []
    for anchor, tile in tiles.items():
        if anchor in occupied:
            continue
        if mode == "land":
            anchor_ok = tile.foot_passable and anchor in reached
        elif mode == "shoreline":
            anchor_ok = tile.sea
        else:
            raise ValueError(f"unsupported mode {mode}")
        if not anchor_ok:
            continue

        ax, az = anchor
        for dx, dz, facing_from_anchor in DIRECTIONS:
            approach = ax + dx, az + dz
            approach_tile = tiles.get(approach)
            if (
                approach not in reached
                or approach in occupied
                or approach_tile is None
                or not approach_tile.foot_passable
            ):
                continue
            facing = {
                "Up": "Down",
                "Down": "Up",
                "Left": "Right",
                "Right": "Left",
            }[facing_from_anchor]
            candidates.append(
                Candidate(
                    anchor=anchor,
                    approach=approach,
                    facing=facing,
                    distance=distance[approach],
                    clearance=visual_clearance(tiles, anchor, mode),
                    object_distance=manhattan_to_nearest(anchor, occupied),
                    anchor_behavior=tile.behavior,
                    approach_behavior=approach_tile.behavior,
                )
            )
    candidates.sort(
        key=lambda item: (
            -item.clearance,
            -min(item.object_distance, 30),
            item.distance,
            item.anchor[1],
            item.anchor[0],
            item.approach,
        )
    )
    return candidates


def reconstruct_path(
    predecessor: dict[tuple[int, int], tuple[int, int] | None],
    target: tuple[int, int],
) -> list[tuple[int, int]]:
    if target not in predecessor:
        return []
    path = [target]
    while predecessor[path[-1]] is not None:
        path.append(predecessor[path[-1]])
    path.reverse()
    return path


def path_runs(path: list[tuple[int, int]]) -> list[tuple[str, int]]:
    keys: list[str] = []
    key_for_delta = {
        (0, -1): "Up",
        (0, 1): "Down",
        (-1, 0): "Left",
        (1, 0): "Right",
    }
    for start, end in zip(path, path[1:]):
        keys.append(key_for_delta[(end[0] - start[0], end[1] - start[1])])
    runs: list[tuple[str, int]] = []
    for key in keys:
        if runs and runs[-1][0] == key:
            runs[-1] = key, runs[-1][1] + 1
        else:
            runs.append((key, 1))
    return runs


def tile_glyph(tile: Tile) -> str:
    if tile.collision:
        return "#"
    if tile.behavior == TILE_BEHAVIOR_WATER_SEA:
        return "~"
    if tile.behavior == TILE_BEHAVIOR_WATER_RIVER:
        return "r"
    if tile.behavior == TILE_BEHAVIOR_WATERFALL:
        return "f"
    if tile.behavior == TILE_BEHAVIOR_SHALLOW_WATER:
        return "s"
    if tile.behavior == TILE_BEHAVIOR_SAND:
        return "a"
    return "."


def render_region(
    *,
    tiles: dict[tuple[int, int], Tile],
    reached: set[tuple[int, int]],
    objects: dict[tuple[int, int], str],
    warps: set[tuple[int, int]],
    entry: tuple[int, int],
    current: tuple[int, int] | None,
    center: tuple[int, int],
    radius_x: int,
    radius_z: int,
) -> str:
    min_x = center[0] - radius_x
    max_x = center[0] + radius_x
    min_z = center[1] - radius_z
    max_z = center[1] + radius_z
    lines = [f"region x={min_x}..{max_x}, z={min_z}..{max_z}"]
    lines.append("legend: # collision, ~=sea, r=river, f=waterfall, s=shallow, a=sand, .=other passable, o=object, w=warp, E=entry, T=current")
    lines.append("      " + "".join(str(x // 10 % 10) for x in range(min_x, max_x + 1)))
    lines.append("      " + "".join(str(x % 10) for x in range(min_x, max_x + 1)))
    for z in range(min_z, max_z + 1):
        chars: list[str] = []
        for x in range(min_x, max_x + 1):
            point = (x, z)
            tile = tiles.get(point)
            glyph = " " if tile is None else tile_glyph(tile)
            if point in objects:
                glyph = "o"
            if point in warps:
                glyph = "w"
            if point == current:
                glyph = "T"
            if point == entry:
                glyph = "E"
            if point in reached and glyph == ".":
                glyph = ","
            chars.append(glyph)
        lines.append(f"z{z:04d} " + "".join(chars))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--header", required=True, help="Map header symbol, e.g. MAP_HEADER_ROUTE_214")
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--entry-x", required=True, type=int)
    parser.add_argument("--entry-z", required=True, type=int)
    parser.add_argument("--current-x", type=int)
    parser.add_argument("--current-z", type=int)
    parser.add_argument("--mode", choices=("land", "shoreline"), required=True)
    parser.add_argument("--target-x", type=int)
    parser.add_argument("--target-z", type=int)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--region-radius-x", type=int, default=18)
    parser.add_argument("--region-radius-z", type=int, default=14)
    args = parser.parse_args()

    entry = (args.entry_x, args.entry_z)
    current = None
    if args.current_x is not None or args.current_z is not None:
        if args.current_x is None or args.current_z is None:
            parser.error("--current-x and --current-z must be supplied together")
        current = (args.current_x, args.current_z)

    target = None
    if args.target_x is not None or args.target_z is not None:
        if args.target_x is None or args.target_z is None:
            parser.error("--target-x and --target-z must be supplied together")
        target = (args.target_x, args.target_z)

    events_path = args.events if args.events.is_absolute() else ROOT / args.events
    tiles = load_route_tiles(args.header)
    objects, warps = load_events(events_path)
    blocked = (set(objects) | warps) - {entry}
    reached, distance, predecessor = reachable_component(tiles, entry, blocked)
    candidates = candidate_pairs(
        tiles=tiles,
        reached=reached,
        distance=distance,
        objects=objects,
        warps=warps,
        mode=args.mode,
    )

    print(f"header={args.header}")
    print(f"events={events_path.relative_to(ROOT)}")
    print(f"entry={entry} entry_value=0x{tiles[entry].value:04X}")
    print(f"route_tiles={len(tiles)} foot_reachable={len(reached)}")
    if current is not None:
        tile = tiles.get(current)
        if tile is None:
            print(f"current={current} outside selected header")
        else:
            print(
                f"current={current} value=0x{tile.value:04X} collision={int(tile.collision)} "
                f"behavior=0x{tile.behavior:02X} foot_reachable={int(current in reached)}"
            )
    if target is not None:
        target_tile = tiles.get(target)
        if target_tile is None:
            print(f"target={target} outside selected header")
            return 3
        path = reconstruct_path(predecessor, target)
        print(
            f"target={target} value=0x{target_tile.value:04X} "
            f"foot_reachable={int(bool(path))} path_steps={max(0, len(path) - 1)}"
        )
        if not path:
            return 3
        runs = path_runs(path)
        print("path_runs=" + ",".join(f"{key}:{count}" for key, count in runs))
        print("path_points=" + ";".join(f"{x}:{z}" for x, z in path))
    print()
    print(render_region(
        tiles=tiles,
        reached=reached,
        objects=objects,
        warps=warps,
        entry=entry,
        current=current,
        center=current if current is not None else entry,
        radius_x=args.region_radius_x,
        radius_z=args.region_radius_z,
    ))
    print()
    print("rank anchor_x anchor_z approach_x approach_z facing distance clearance object_distance anchor_beh approach_beh")
    for index, candidate in enumerate(candidates[: args.limit], start=1):
        print(
            f"{index:02d} {candidate.anchor[0]:4d} {candidate.anchor[1]:4d} "
            f"{candidate.approach[0]:4d} {candidate.approach[1]:4d} {candidate.facing:5s} "
            f"{candidate.distance:4d} {candidate.clearance:3d} {candidate.object_distance:3d} "
            f"0x{candidate.anchor_behavior:02X} 0x{candidate.approach_behavior:02X}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

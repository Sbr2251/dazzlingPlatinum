#!/usr/bin/env python3
"""Inspect Platinum BDHC collision heights at a map tile.

The implementation mirrors the structures and selection logic in
src/overlay005/bdhc.c and the coordinate conversion in
src/terrain_collision_manager.c for a selected matrix cell.
"""

from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path

FX32_ONE = 4096
MAP_TILES = 32
TILE_SIZE_FX32 = 16 * FX32_ONE


@dataclass(frozen=True)
class Point:
    x: int
    z: int


@dataclass(frozen=True)
class Normal:
    x: int
    y: int
    z: int


@dataclass(frozen=True)
class Plate:
    first: int
    second: int
    normal: int
    constant: int


def fx_mul(a: int, b: int) -> int:
    # Nitro FX_Mul uses a 64-bit product shifted back to fx32 precision.
    return (a * b) >> 12


def fx_div(a: int, b: int) -> int:
    if b == 0:
        raise ZeroDivisionError("BDHC plane has normal.y == 0")
    # Truncate toward zero, matching signed C integer division semantics.
    numerator = a << 12
    return abs(numerator) // abs(b) * (-1 if (numerator < 0) ^ (b < 0) else 1)


def parse_bdhc(data: bytes):
    off = data.find(b"BDHC")
    if off < 0:
        raise ValueError("BDHC magic not found")
    counts = struct.unpack_from("<6H", data, off + 4)
    points_count, normals_count, constants_count, plates_count, strips_count, access_count = counts
    pos = off + 16

    points = [Point(*struct.unpack_from("<ii", data, pos + i * 8)) for i in range(points_count)]
    pos += points_count * 8
    normals = [Normal(*struct.unpack_from("<iii", data, pos + i * 12)) for i in range(normals_count)]
    pos += normals_count * 12
    constants = list(struct.unpack_from(f"<{constants_count}i", data, pos))
    pos += constants_count * 4
    plates = [Plate(*struct.unpack_from("<HHHH", data, pos + i * 8)) for i in range(plates_count)]
    pos += plates_count * 8
    strips = [struct.unpack_from("<iHH", data, pos + i * 8) for i in range(strips_count)]
    pos += strips_count * 8
    access = list(struct.unpack_from(f"<{access_count}H", data, pos))

    return off, counts, points, normals, constants, plates, strips, access


def find_strip(strips, scanline: int) -> int:
    if not strips:
        raise ValueError("BDHC has no strips")
    if len(strips) == 1:
        return 0
    low = 0
    high = len(strips) - 1
    mid = high // 2
    while True:
        if strips[mid][0] > scanline:
            if high - 1 > low:
                high = mid
                mid = (low + high) // 2
            else:
                return mid
        else:
            if low + 1 < high:
                low = mid
                mid = (low + high) // 2
            else:
                return mid + 1


def in_bbox(a: Point, b: Point, x: int, z: int) -> bool:
    return min(a.x, b.x) <= x <= max(a.x, b.x) and min(a.z, b.z) <= z <= max(a.z, b.z)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("land_member", type=Path)
    parser.add_argument("tile_x", type=int)
    parser.add_argument("tile_z", type=int)
    parser.add_argument("--matrix-x", type=int, default=0)
    parser.add_argument("--matrix-z", type=int, default=0)
    parser.add_argument("--current-height-fx32", type=int, default=0)
    args = parser.parse_args()

    data = args.land_member.read_bytes()
    off, counts, points, normals, constants, plates, strips, access = parse_bdhc(data)

    world_x = ((args.tile_x << 4) * FX32_ONE) + (TILE_SIZE_FX32 >> 1)
    world_z = ((args.tile_z << 4) * FX32_ONE) + (TILE_SIZE_FX32 >> 1)
    origin_x = (args.matrix_x * MAP_TILES + MAP_TILES // 2) * TILE_SIZE_FX32
    origin_z = (args.matrix_z * MAP_TILES + MAP_TILES // 2) * TILE_SIZE_FX32
    local_x = world_x - origin_x
    local_z = world_z - origin_z

    strip_index = find_strip(strips, local_z)
    _, access_count, access_start = strips[strip_index]
    candidate_rows = []
    for plate_index in access[access_start : access_start + access_count]:
        plate = plates[plate_index]
        p0 = points[plate.first]
        p1 = points[plate.second]
        if not in_bbox(p0, p1, local_x, local_z):
            continue
        normal = normals[plate.normal]
        constant = constants[plate.constant]
        numerator = -(fx_mul(normal.x, local_x) + fx_mul(normal.z, local_z) + constant)
        height = fx_div(numerator, normal.y)
        candidate_rows.append((plate_index, height, normal, constant, p0, p1))
        if len(candidate_rows) >= 10:
            break

    print(f"land_member={args.land_member}")
    print(f"bdhc_offset={off} counts={counts}")
    print(f"tile=({args.tile_x},{args.tile_z}) matrix=({args.matrix_x},{args.matrix_z})")
    print(f"world_fx32=({world_x},{world_z}) local_fx32=({local_x},{local_z}) strip={strip_index}")
    print(f"current_height_fx32={args.current_height_fx32}")
    if not candidate_rows:
        print("candidate_count=0")
        return 2

    print(f"candidate_count={len(candidate_rows)}")
    for idx, (plate_index, height, normal, constant, p0, p1) in enumerate(candidate_rows):
        print(
            f"candidate[{idx}] plate={plate_index} height_fx32={height} "
            f"height={height / FX32_ONE:.6f} diff={abs(height - args.current_height_fx32)} "
            f"normal=({normal.x},{normal.y},{normal.z}) constant={constant} "
            f"bbox=({p0.x},{p0.z})..({p1.x},{p1.z})"
        )
    selected = min(candidate_rows, key=lambda row: abs(row[1] - args.current_height_fx32))
    print(f"selected_plate={selected[0]}")
    print(f"selected_height_fx32={selected[1]}")
    print(f"selected_height={selected[1] / FX32_ONE:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

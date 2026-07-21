#!/usr/bin/env python3
"""Build executable Platinum land-data components for Everspring Sanctuary.

Inputs are the approved 64x32 behavior contract, the two Map Studio-exported
model-only NSBMD files, the shared custom NSBTX, and the original Route 218
members (used only to preserve their building sections). The compact BDHC
writer follows the structures read by pokeplatinum's src/overlay005/bdhc.c.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import struct
from collections import Counter, deque
from pathlib import Path

from PIL import Image, ImageDraw

TOOL_DIR = Path(__file__).resolve().parent
REPO = TOOL_DIR.parents[1]
STORY = TOOL_DIR
CONTRACT = TOOL_DIR / "assets/Everspring_behavior_contract.csv"
LAYOUT = TOOL_DIR / "assets/everspring_layout.json"
MODEL_DIR = TOOL_DIR / "assets"
OUTPUT = REPO / "build/everspring_generated"

MEMBERS = {
    50: {
        "donor": REPO / "res/field/maps/data/map_data_050.bin",
        "model": MODEL_DIR / "Everspring_Sanctuary_00_00_model.nsbmd",
        "cell_x": 0,
    },
    51: {
        "donor": REPO / "res/field/maps/data/map_data_051.bin",
        "model": MODEL_DIR / "Everspring_Sanctuary_01_00_model.nsbmd",
        "cell_x": 1,
    },
}
SHARED_TEXTURE = MODEL_DIR / "Everspring_shared_textures.nsbtx"

MAP_SIZE = 32
FX32_ONE = 4096
TILE_WORLD_SIZE = 16
HEIGHT_STEP = 16

# Permission layer 0: TileBehavior; layer 1: movement collision.
TILE_BEHAVIOR_NONE = 0x00
TILE_BEHAVIOR_TALL_GRASS = 0x02
TILE_BEHAVIOR_WATER_SEA = 0x15
COLLISION_OPEN = 0x00
COLLISION_SOLID = 0x80

FOOT_SYMBOLS = {"G", "P", "F", "S"}
SURF_SYMBOLS = {"W"}
BLOCKED_SYMBOLS = {"T", "L", "R"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_nitro(
    path: Path,
    expected_magic: bytes,
    expected_block: bytes,
    expected_version: int,
) -> dict:
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != expected_magic:
        raise ValueError(f"{path}: expected {expected_magic!r} Nitro header")
    byte_order, version, declared_size, header_size, block_count = struct.unpack_from("<HHIHH", data, 4)
    if byte_order != 0xFEFF or version != expected_version or header_size != 16:
        raise ValueError(
            f"{path}: invalid Nitro header fields; expected version {expected_version}, "
            f"got byte_order=0x{byte_order:04X}, version={version}, header_size={header_size}"
        )
    if declared_size != len(data) or block_count != 1:
        raise ValueError(f"{path}: declared size/block count mismatch")
    first_offset = struct.unpack_from("<I", data, 16)[0]
    if first_offset != 20 or data[first_offset : first_offset + 4] != expected_block:
        raise ValueError(f"{path}: missing expected {expected_block!r} block")
    block_size = struct.unpack_from("<I", data, first_offset + 4)[0]
    if first_offset + block_size != len(data):
        raise ValueError(f"{path}: block size does not reach EOF")
    return {
        "magic": expected_magic.decode("ascii"),
        "block": expected_block.decode("ascii"),
        "size": len(data),
        "sha256": sha256(path),
    }


def split_land_member(path: Path) -> dict[str, bytes]:
    data = path.read_bytes()
    if len(data) < 16:
        raise ValueError(f"{path}: truncated land member")
    per_len, bld_len, model_len, bdhc_len = struct.unpack_from("<4I", data, 0)
    if 16 + per_len + bld_len + model_len + bdhc_len != len(data):
        raise ValueError(f"{path}: component lengths do not match file size")
    per_off = 16
    bld_off = per_off + per_len
    model_off = bld_off + bld_len
    bdhc_off = model_off + model_len
    return {
        "header": data[:16],
        "per": data[per_off:bld_off],
        "bld": data[bld_off:model_off],
        "model": data[model_off:bdhc_off],
        "bdhc": data[bdhc_off:],
    }


def load_contract() -> tuple[dict[int, list[list[dict]]], dict]:
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    rows = layout["rows"]
    if len(rows) != 32 or any(len(row) != 64 for row in rows):
        raise ValueError("Everspring layout is not 64x32")

    by_member = {
        member: [[None for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]
        for member in MEMBERS
    }
    with CONTRACT.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            member = int(row["map_member"])
            lx = int(row["local_x"])
            ly = int(row["local_y"])
            gx = int(row["global_x"])
            gy = int(row["global_y"])
            if member not in by_member:
                raise ValueError(f"Unexpected member {member}")
            if row["symbol"] != rows[gy][gx]:
                raise ValueError(f"Contract/layout mismatch at ({gx},{gy})")
            if by_member[member][ly][lx] is not None:
                raise ValueError(f"Duplicate contract cell member {member} ({lx},{ly})")
            by_member[member][ly][lx] = {
                **row,
                "map_member": member,
                "local_x": lx,
                "local_y": ly,
                "global_x": gx,
                "global_y": gy,
            }

    for member, grid in by_member.items():
        missing = [(x, y) for y in range(32) for x in range(32) if grid[y][x] is None]
        if missing:
            raise ValueError(f"Member {member} has missing contract cells: {missing[:5]}")
    return by_member, layout


def elevated(global_x: int, global_y: int) -> bool:
    north_west = 4 <= global_x <= 24 and 2 <= global_y <= 11
    north_east = 41 <= global_x <= 59 and 2 <= global_y <= 11
    south_west = 4 <= global_x <= 22 and 24 <= global_y <= 29
    return north_west or north_east or south_west


def expected_height(cell: dict, z_fraction: float = 0.5) -> float:
    """Return the BDHC height at a north-to-south position inside one tile."""
    if not 0.0 <= z_fraction <= 1.0:
        raise ValueError(f"z_fraction must be in [0, 1], got {z_fraction}")
    gx, gy = cell["global_x"], cell["global_y"]
    if cell["symbol"] == "S":
        if gy == 12:
            return HEIGHT_STEP * (1.0 - z_fraction)
        if gy == 23:
            return HEIGHT_STEP * z_fraction
        raise ValueError(f"Unexpected stair row {gy}")
    return float(HEIGHT_STEP if elevated(gx, gy) else 0)


def permission_pair(symbol: str) -> tuple[int, int]:
    if symbol == "F":
        return TILE_BEHAVIOR_TALL_GRASS, COLLISION_OPEN
    if symbol == "W":
        return TILE_BEHAVIOR_WATER_SEA, COLLISION_OPEN
    if symbol in FOOT_SYMBOLS:
        return TILE_BEHAVIOR_NONE, COLLISION_OPEN
    if symbol in BLOCKED_SYMBOLS:
        return TILE_BEHAVIOR_NONE, COLLISION_SOLID
    raise ValueError(f"Unknown symbol {symbol!r}")


def build_permissions(grid: list[list[dict]]) -> tuple[bytes, dict]:
    out = bytearray()
    counts = Counter()
    for y in range(MAP_SIZE):
        for x in range(MAP_SIZE):
            pair = permission_pair(grid[y][x]["symbol"])
            out.extend(pair)
            counts[f"{pair[0]:02X}:{pair[1]:02X}"] += 1
    if len(out) != 2048:
        raise AssertionError("Platinum permission block must be 2048 bytes")
    return bytes(out), dict(sorted(counts.items()))


def fx(value: float | int) -> int:
    result = int(round(float(value) * FX32_ONE))
    if not -(2**31) <= result < 2**31:
        raise OverflowError(value)
    return result


def build_compact_bdhc(grid: list[list[dict]]) -> tuple[bytes, dict]:
    points: list[tuple[int, int]] = []
    point_index: dict[tuple[int, int], int] = {}
    normals: list[tuple[int, int, int]] = []
    normal_index: dict[tuple[int, int, int], int] = {}
    constants: list[int] = []
    constant_index: dict[int, int] = {}
    plates: list[tuple[int, int, int, int]] = []
    row_plate_indices: list[list[int]] = [[] for _ in range(MAP_SIZE)]

    def intern_point(value: tuple[int, int]) -> int:
        if value not in point_index:
            point_index[value] = len(points)
            points.append(value)
        return point_index[value]

    def intern_normal(value: tuple[int, int, int]) -> int:
        if value not in normal_index:
            normal_index[value] = len(normals)
            normals.append(value)
        return normal_index[value]

    def intern_constant(value: int) -> int:
        if value not in constant_index:
            constant_index[value] = len(constants)
            constants.append(value)
        return constant_index[value]

    for y in range(MAP_SIZE):
        z0 = (y - 16) * TILE_WORLD_SIZE
        z1 = z0 + TILE_WORLD_SIZE
        for x in range(MAP_SIZE):
            x0 = (x - 16) * TILE_WORLD_SIZE
            x1 = x0 + TILE_WORLD_SIZE
            cell = grid[y][x]
            symbol = cell["symbol"]
            gy = cell["global_y"]

            if symbol == "S" and gy == 12:
                # North side height 16, south side height 0: y + z + 48 = 0.
                normal = (fx(0), fx(1), fx(1))
                constant = fx(-z1)
            elif symbol == "S" and gy == 23:
                # North side height 0, south side height 16: y - z + 112 = 0.
                normal = (fx(0), fx(1), fx(-1))
                constant = fx(z0)
            else:
                height = HEIGHT_STEP if elevated(cell["global_x"], gy) else 0
                normal = (fx(0), fx(1), fx(0))
                constant = fx(-height)

            first = intern_point((fx(x0), fx(z0)))
            second = intern_point((fx(x1), fx(z1)))
            normal_id = intern_normal(normal)
            constant_id = intern_constant(constant)
            plate_id = len(plates)
            plates.append((first, second, normal_id, constant_id))
            row_plate_indices[y].append(plate_id)

    strips: list[tuple[int, int, int]] = []
    access_list: list[int] = []
    for y in range(MAP_SIZE):
        z1 = (y - 15) * TILE_WORLD_SIZE
        start = len(access_list)
        access_list.extend(row_plate_indices[y])
        strips.append((fx(z1), len(row_plate_indices[y]), start))

    counts = (len(points), len(normals), len(constants), len(plates), len(strips), len(access_list))
    if any(value > 0xFFFF for value in counts):
        raise ValueError(f"BDHC count exceeds u16: {counts}")

    out = bytearray(b"BDHC")
    out.extend(struct.pack("<6H", *counts))
    for x, z in points:
        out.extend(struct.pack("<ii", x, z))
    for x, y, z in normals:
        out.extend(struct.pack("<iii", x, y, z))
    for value in constants:
        out.extend(struct.pack("<i", value))
    for plate in plates:
        out.extend(struct.pack("<4H", *plate))
    for strip in strips:
        out.extend(struct.pack("<iHH", *strip))
    for plate_id in access_list:
        out.extend(struct.pack("<H", plate_id))

    expected_size = 16 + len(points) * 8 + len(normals) * 12 + len(constants) * 4 + len(plates) * 8 + len(strips) * 8 + len(access_list) * 2
    if len(out) != expected_size:
        raise AssertionError((len(out), expected_size))

    summary = {
        "size": len(out),
        "counts": {
            "points": len(points),
            "normals": len(normals),
            "constants": len(constants),
            "plates": len(plates),
            "strips": len(strips),
            "access_list": len(access_list),
        },
        "x_extent": [-256, 256],
        "z_extent": [-256, 256],
        "flat_heights": [0, HEIGHT_STEP],
        "stair_rows_global": [12, 23],
    }
    return bytes(out), summary


def parse_compact_bdhc(data: bytes) -> dict:
    if data[:4] != b"BDHC" or len(data) < 16:
        raise ValueError("Invalid compact BDHC")
    counts = struct.unpack_from("<6H", data, 4)
    point_count, normal_count, constant_count, plate_count, strip_count, access_count = counts
    off = 16
    points = [struct.unpack_from("<ii", data, off + index * 8) for index in range(point_count)]
    off += point_count * 8
    normals = [struct.unpack_from("<iii", data, off + index * 12) for index in range(normal_count)]
    off += normal_count * 12
    constants = list(struct.unpack_from(f"<{constant_count}i", data, off))
    off += constant_count * 4
    plates = [struct.unpack_from("<4H", data, off + index * 8) for index in range(plate_count)]
    off += plate_count * 8
    strips = [struct.unpack_from("<iHH", data, off + index * 8) for index in range(strip_count)]
    off += strip_count * 8
    access = list(struct.unpack_from(f"<{access_count}H", data, off))
    off += access_count * 2
    if off != len(data):
        raise ValueError(f"BDHC parser ended at {off}, file size {len(data)}")
    return {
        "points": points,
        "normals": normals,
        "constants": constants,
        "plates": plates,
        "strips": strips,
        "access": access,
    }


def runtime_strip_index(parsed: dict, z: float) -> int:
    """Mirror BDHC_FindStripIndexByScanline from Platinum's bdhc.c."""
    strips = parsed["strips"]
    count = len(strips)
    if count == 0:
        raise ValueError("BDHC has no strips")
    if count == 1:
        return 0

    scanline = fx(z)
    low = 0
    high = count - 1
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


def calculate_heights(parsed: dict, x: float, z: float) -> list[float]:
    strip_index = runtime_strip_index(parsed, z)
    _, count, start = parsed["strips"][strip_index]
    candidates = []
    for plate_id in parsed["access"][start : start + count]:
        p1_id, p2_id, normal_id, constant_id = parsed["plates"][plate_id]
        p1, p2 = parsed["points"][p1_id], parsed["points"][p2_id]
        min_x, max_x = sorted((p1[0], p2[0]))
        min_z, max_z = sorted((p1[1], p2[1]))
        x_fx, z_fx = fx(x), fx(z)
        if min_x <= x_fx <= max_x and min_z <= z_fx <= max_z:
            nx, ny, nz = parsed["normals"][normal_id]
            constant = parsed["constants"][constant_id]
            if ny == 0:
                raise ValueError("BDHC plate has zero Y normal")
            # All values are fx32; reproduce the plane algebra at exact integer inputs.
            height_fx = -((nx * x_fx // FX32_ONE) + (nz * z_fx // FX32_ONE) + constant)
            height_fx = height_fx * FX32_ONE // ny
            candidates.append(height_fx / FX32_ONE)
    return candidates


def validate_bdhc(data: bytes, grid: list[list[dict]]) -> dict:
    parsed = parse_compact_bdhc(data)
    sample_fractions = (0.125, 0.5, 0.875)
    checked = 0
    center_checked = 0
    candidate_histogram = Counter()
    errors = []
    for y in range(MAP_SIZE):
        for x in range(MAP_SIZE):
            for z_fraction in sample_fractions:
                for x_fraction in sample_fractions:
                    world_x = (x - MAP_SIZE / 2 + x_fraction) * TILE_WORLD_SIZE
                    world_z = (y - MAP_SIZE / 2 + z_fraction) * TILE_WORLD_SIZE
                    candidates = calculate_heights(parsed, world_x, world_z)
                    candidate_histogram[len(candidates)] += 1
                    expected = expected_height(grid[y][x], z_fraction=z_fraction)
                    if len(candidates) != 1 or abs(candidates[0] - expected) > 0.001:
                        errors.append({
                            "x": x,
                            "y": y,
                            "x_fraction": x_fraction,
                            "z_fraction": z_fraction,
                            "expected": expected,
                            "candidates": candidates,
                        })
                    checked += 1
                    if x_fraction == 0.5 and z_fraction == 0.5:
                        center_checked += 1
    if errors:
        raise ValueError(f"BDHC runtime-sample validation failed: {errors[:5]}")

    payload_size = len(data) - 16
    if payload_size > 0x9000:
        raise ValueError(
            f"BDHC payload {payload_size} exceeds Platinum BDHC_BUFFER_SIZE 0x9000"
        )
    return {
        "tile_centers_checked": center_checked,
        "interior_samples_checked": checked,
        "samples_per_tile": len(sample_fractions) ** 2,
        "sample_fractions": list(sample_fractions),
        "candidate_count_histogram": dict(sorted(candidate_histogram.items())),
        "unique_height_at_every_sample": True,
        "all_expected_heights_present": True,
        "runtime_strip_search_mirrored": True,
        "runtime_buffer_payload_bytes": payload_size,
        "runtime_buffer_limit_bytes": 0x9000,
        "runtime_buffer_within_limit": True,
    }


def assemble_land_member(per: bytes, bld: bytes, model: bytes, bdhc: bytes) -> bytes:
    component_lengths = [len(per), len(bld), len(model), len(bdhc)]
    return struct.pack("<4I", *component_lengths) + per + bld + model + bdhc


def validate_land_member(data: bytes, expected_bld: bytes) -> dict:
    if len(data) < 16:
        raise ValueError("Truncated land member")
    per_len, bld_len, model_len, bdhc_len = struct.unpack_from("<4I", data, 0)
    if 16 + per_len + bld_len + model_len + bdhc_len != len(data):
        raise ValueError("Land-member component lengths do not match file size")
    per_off = 16
    bld_off = per_off + per_len
    model_off = bld_off + bld_len
    bdhc_off = model_off + model_len
    per = data[per_off:bld_off]
    bld = data[bld_off:model_off]
    model = data[model_off:bdhc_off]
    bdhc = data[bdhc_off:]
    if len(per) != 2048 or bld != expected_bld:
        raise ValueError("Permission length or preserved building component mismatch")
    if model[:4] != b"BMD0" or bdhc[:4] != b"BDHC":
        raise ValueError("Model or collision magic mismatch")
    if struct.unpack_from("<I", model, 8)[0] != len(model):
        raise ValueError("Embedded model declared size mismatch")
    parse_compact_bdhc(bdhc)
    return {
        "size": len(data),
        "header_component_lengths": {"permissions": per_len, "building": bld_len, "model": model_len, "bdhc": bdhc_len},
        "computed_offsets": {"permissions": per_off, "building": bld_off, "model": model_off, "bdhc": bdhc_off},
        "component_sizes": {"permissions": len(per), "building": len(bld), "model": len(model), "bdhc": len(bdhc)},
    }


def foot_neighbors(grid64: list[str], point: tuple[int, int]) -> list[tuple[int, int]]:
    x, y = point
    current_symbol = grid64[y][x]
    current_h = expected_height({"symbol": current_symbol, "global_x": x, "global_y": y})
    output = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if not (0 <= nx < 64 and 0 <= ny < 32) or grid64[ny][nx] not in FOOT_SYMBOLS:
            continue
        neighbor_symbol = grid64[ny][nx]
        next_h = expected_height({"symbol": neighbor_symbol, "global_x": nx, "global_y": ny})
        # Platinum blocks height changes of 20 world units or more. Everspring's
        # 16-unit terraces and 8-unit stair-center transitions are traversable.
        if abs(current_h - next_h) < 20:
            output.append((nx, ny))
    return output


def walkability_validation(layout: dict) -> dict:
    rows = layout["rows"]
    starts = {(6, 18), (6, 19)}
    goals = {(57, 22), (57, 23)}
    queue = deque(sorted(starts))
    visited = set(starts)
    while queue:
        point = queue.popleft()
        for neighbor in foot_neighbors(rows, point):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    required = starts | goals | {
        (25, 13), (33, 19), (20, 25), (44, 13), (14, 9), (48, 8), (8, 17), (55, 21)
    }
    unreachable_required = sorted(required - visited)
    all_foot = {(x, y) for y in range(32) for x in range(64) if rows[y][x] in FOOT_SYMBOLS}
    unreachable_foot = sorted(all_foot - visited)
    seam_edges = []
    for y in range(32):
        if (31, y) in visited and (32, y) in visited and (32, y) in foot_neighbors(rows, (31, y)):
            seam_edges.append([[31, y], [32, y]])

    stair_runs = []
    for y in (12, 23):
        x = 0
        while x < 64:
            if rows[y][x] != "S":
                x += 1
                continue
            start = x
            while x < 64 and rows[y][x] == "S":
                x += 1
            cells = [[value, y] for value in range(start, x)]
            if len(cells) != 3:
                raise ValueError(f"Invalid stair run at y={y}: {cells}")
            stair_runs.append({"row": y, "cells": cells, "reachable": all(tuple(cell) in visited for cell in cells)})

    if unreachable_required or unreachable_foot:
        raise ValueError(
            f"Everspring foot traversal failed: required={unreachable_required[:8]}, "
            f"walkable={unreachable_foot[:8]}"
        )
    if not seam_edges or not all(run["reachable"] for run in stair_runs):
        raise ValueError("Everspring seam or stair traversal validation failed")

    return {
        "foot_walkable_tiles": len(all_foot),
        "reachable_foot_tiles": len(visited & all_foot),
        "all_foot_tiles_connected": True,
        "required_anchors_reachable": [list(value) for value in sorted(required)],
        "canalave_to_jubilife_connected": goals <= visited,
        "cross_member_seam_edges": seam_edges,
        "stair_runs": stair_runs,
        "surf_tiles": sum(row.count("W") for row in rows),
        "blocked_tiles": sum(sum(char in BLOCKED_SYMBOLS for char in row) for row in rows),
    }


def render_permissions(layout: dict, output: Path) -> None:
    colors = {
        "G": (112, 201, 127),
        "P": (231, 208, 154),
        "F": (223, 115, 180),
        "S": (245, 245, 245),
        "W": (55, 137, 207),
        "T": (30, 50, 43),
        "L": (87, 73, 55),
        "R": (110, 74, 157),
    }
    scale = 12
    image = Image.new("RGB", (64 * scale, 32 * scale), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    for y, row in enumerate(layout["rows"]):
        for x, symbol in enumerate(row):
            draw.rectangle((x * scale, y * scale, (x + 1) * scale - 1, (y + 1) * scale - 1), fill=colors[symbol])
    draw.line((32 * scale, 0, 32 * scale, 32 * scale), fill=(255, 0, 255), width=2)
    for x, y in ((6, 18), (6, 19), (57, 22), (57, 23)):
        draw.rectangle((x * scale + 2, y * scale + 2, (x + 1) * scale - 3, (y + 1) * scale - 3), outline=(255, 255, 255), width=2)
    for y in (12, 23):
        for x, symbol in enumerate(layout["rows"][y]):
            if symbol == "S":
                draw.rectangle((x * scale + 1, y * scale + 1, (x + 1) * scale - 2, (y + 1) * scale - 2), outline=(255, 220, 0), width=2)
    image.save(output)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    components_dir = OUTPUT / "components"
    members_dir = OUTPUT / "members"
    components_dir.mkdir(exist_ok=True)
    members_dir.mkdir(exist_ok=True)

    contract_by_member, layout = load_contract()
    walkability = walkability_validation(layout)
    texture_info = parse_nitro(SHARED_TEXTURE, b"BTX0", b"TEX0", 1)
    shutil.copy2(SHARED_TEXTURE, OUTPUT / "Everspring_shared_textures.nsbtx")

    manifest = {
        "area": "Everspring Sanctuary",
        "target_map": "MAP_HEADER_ROUTE_218",
        "target_members": [50, 51],
        "permission_contract": str(CONTRACT),
        "permission_encoding": {
            "plain_walkable": [TILE_BEHAVIOR_NONE, COLLISION_OPEN],
            "encounter_flowers": [TILE_BEHAVIOR_TALL_GRASS, COLLISION_OPEN],
            "surf_water": [TILE_BEHAVIOR_WATER_SEA, COLLISION_OPEN],
            "solid": [TILE_BEHAVIOR_NONE, COLLISION_SOLID],
        },
        "height_step_world_units": HEIGHT_STEP,
        "shared_texture": texture_info,
        "walkability": walkability,
        "members": {},
    }

    for member, spec in MEMBERS.items():
        donor_parts = split_land_member(spec["donor"])
        if len(donor_parts["per"]) != 2048:
            raise ValueError(f"Donor member {member} permission size is not 2048")
        model_info = parse_nitro(spec["model"], b"BMD0", b"MDL0", 2)
        model = spec["model"].read_bytes()
        grid = contract_by_member[member]
        per, permission_counts = build_permissions(grid)
        bdhc, bdhc_summary = build_compact_bdhc(grid)
        bdhc_validation = validate_bdhc(bdhc, grid)
        land = assemble_land_member(per, donor_parts["bld"], model, bdhc)
        land_validation = validate_land_member(land, donor_parts["bld"])

        stem = f"map_data_{member:03d}"
        paths = {
            "permissions": components_dir / f"{stem}.per",
            "building": components_dir / f"{stem}.bld",
            "model": components_dir / f"{stem}.nsbmd",
            "bdhc": components_dir / f"{stem}.bdhc",
            "member": members_dir / f"{stem}.bin",
        }
        paths["permissions"].write_bytes(per)
        paths["building"].write_bytes(donor_parts["bld"])
        paths["model"].write_bytes(model)
        paths["bdhc"].write_bytes(bdhc)
        paths["member"].write_bytes(land)

        manifest["members"][str(member)] = {
            "cell_x": spec["cell_x"],
            "model": model_info,
            "permission_pairs": permission_counts,
            "bdhc": bdhc_summary,
            "bdhc_validation": bdhc_validation,
            "land_validation": land_validation,
            "preserved_building_sha256": sha256(paths["building"]),
            "outputs": {name: {"path": str(path), "size": path.stat().st_size, "sha256": sha256(path)} for name, path in paths.items()},
        }

    render_permissions(layout, OUTPUT / "Everspring_walkability_permissions.png")
    manifest["walkability_preview"] = {
        "path": str(OUTPUT / "Everspring_walkability_permissions.png"),
        "sha256": sha256(OUTPUT / "Everspring_walkability_permissions.png"),
    }
    manifest_path = OUTPUT / "Everspring_land_data_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    checksum_lines = []
    for path in sorted(p for p in OUTPUT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"):
        checksum_lines.append(f"{sha256(path)}  {path.relative_to(OUTPUT)}")
    (OUTPUT / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": "PASS",
        "output": str(OUTPUT),
        "members": {key: value["land_validation"] for key, value in manifest["members"].items()},
        "walkability": walkability,
        "texture": texture_info,
    }, indent=2))


if __name__ == "__main__":
    main()

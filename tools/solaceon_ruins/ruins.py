#!/usr/bin/env python3
"""Shared constants for the Solaceon Ruins raid tools (standard library only).

Every Ruins room is a one-chunk map (matrix 1x1, chunk (0,0)), so absolute tiles = chunk-local tiles = event x/z.
Area data 56 = (props list 52, texture set 55, light 1), shared with Turnback Cave (all rooms) and the Celestic Town
cave: set 55 is append-only.

Paths are one constant each so the macOS port (branch solaceon-mac: res/field/mapmodels/data/ and
res/field/mapmodels/texture_sets/) only changes MAP_DATA_DIR / TEXSET_DIR.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))

BASE_REV = "50482f890"                       # PLAN.md section 5: stock inputs are read from git at this rev
MAP_DATA_DIR = "res/field/maps/data"         # solaceon-mac: res/field/mapmodels/data
TEXSET_DIR = "res/field/maps/texture_sets"   # solaceon-mac: res/field/mapmodels/texture_sets
EVENTS_DIR = "res/field/events"              # solaceon-mac: res/field/maps/<map>/events.json
TEXSET = 55
AREA = 56
PREVIEW_DIR = "/tmp/Solaceon Update/raid"    # ~/Documents is not writable from this session


def chunk_rel(n):
    return f"{MAP_DATA_DIR}/map_data_{n:03d}.bin"


def texset_rel(n=TEXSET):
    return f"{TEXSET_DIR}/map_texture_set_{n:03d}.nsbtx"


# header suffix (MAP_HEADER_SOLACEON_RUINS_<suffix>) -> (short name, matrix id, chunk = map_data id)
ROOMS = {
    "MANIAC_TUNNEL_ROOM": ("MT", 25, 389),
    "ROOM_1": ("R1", 26, 390),
    "ROOM_1_NORTHWEST_DEAD_END": ("R1-NW", 35, 399),
    "ROOM_1_SOUTHEAST_DEAD_END": ("R1-SE", 31, 395),
    "ROOM_2": ("R2", 39, 403),
    "ROOM_2_NORTHEAST_DEAD_END": ("R2-NE", 40, 404),
    "ROOM_2_SOUTHEAST_DEAD_END": ("R2-SE", 31, 395),
    "ROOM_3": ("R3", 34, 398),
    "ROOM_3_NORTHWEST_DEAD_END": ("R3-NW", 35, 399),
    "ROOM_3_SOUTHWEST_DEAD_END": ("R3-SW", 35, 399),
    "ROOM_4": ("R4", 36, 400),
    "ROOM_4_SOUTHEAST_DEAD_END": ("R4-SE", 31, 395),
    "ROOM_5": ("R5", 30, 394),
    "ROOM_5_SOUTHWEST_DEAD_END": ("R5-SW", 42, 406),
    "ROOM_5_SOUTHEAST_DEADEND": ("R5-SE", 31, 395),
    "ROOM_6": ("R6", 34, 398),
    "ROOM_6_NORTHWEST_DEAD_END": ("R6-NW", 35, 399),
    "ROOM_6_SOUTHEAST_DEAD_END": ("R6-SE", 40, 404),
    "ROOM_7": ("R7", 41, 405),
}


def events_rel(suffix):
    return f"{EVENTS_DIR}/events_solaceon_ruins_{suffix.lower()}.json"


def rooms_of_chunk(chunk):
    return [v[0] for v in ROOMS.values() if v[2] == chunk]

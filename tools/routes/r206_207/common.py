#!/usr/bin/env python3
"""Shared constants and helpers for the Routes 206-207 Eclipse Supply Road redesign (docs/routes_wave2/PLAN.md).

Chunks (map matrix 0, 32 x 32 tiles each; absolute tile x/z):
  MAP_030 cell (9,18)  x 288..319  z 576..607   Route 206 north (Cycling Road north gate, Wayward Cave)
  MAP_029 cell (9,19)  x 288..319  z 608..639   Route 206
  MAP_028 cell (9,20)  x 288..319  z 640..671   Route 206
  MAP_027 cell (9,21)  x 288..319  z 672..703   Route 206 south (Cycling Road south gate, junction)
  MAP_025 cell (9,22)  x 288..319  z 704..735   Route 207 west (Oreburgh north seam, Route 206 junction)
  MAP_026 cell (10,22) x 320..351  z 704..735   Route 207 east (Mt. Coronet 1F south entrance)

Every input is read from git at BASE_REV, so reruns never feed back on themselves.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.append(os.path.join(ROOT, "tools", "lake_verity"))
sys.path.append(os.path.join(ROOT, "tools", "world_art"))

BASE_REV = "406c75f6a8"           # routes-wave2 contract commit: stock chunks 025..030, stock set 007
MAP_DIR = "res/field/mapmodels/data"
SET_REL = "res/field/mapmodels/texture_sets/map_texture_set_079.nsbtx"
BASE_SET_REL = "res/field/mapmodels/texture_sets/map_texture_set_007.nsbtx"
LIGHTING_REL = "res/field/lighting/lighting_set_007.json"
LIGHTING_TEMPLATE = "res/field/lighting/lighting_set_000.json"

CHUNKS = {25: (9, 22), 26: (10, 22), 27: (9, 21), 28: (9, 20), 29: (9, 19), 30: (9, 18)}

MODEL_BUFFER = 0xF000             # include/overlay005/loaded_map_buffers.h MAP_MODEL_FILE_SIZE
BDHC_BUFFER = 0x9000              # include/constants/field/bdhc.h BDHC_BUFFER_SIZE
VRAM_TARGET = 160 * 1024          # task budget for set 079

BLOCK = 0x8000


def chunk_rel(c):
    return f"{MAP_DIR}/map_data_{c:03d}.bin"


def git_bytes(rev, rel):
    return subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{rel}"], check=True, capture_output=True).stdout


def chunk_of(x, z):
    for c, (cx, cz) in CHUNKS.items():
        if cx * 32 <= x < cx * 32 + 32 and cz * 32 <= z < cz * 32 + 32:
            return c
    return None

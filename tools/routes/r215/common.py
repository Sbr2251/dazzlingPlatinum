#!/usr/bin/env python3
"""Shared constants and stock readers for the Route 215 flooded-lowland redesign (tools/routes/r215).

Route 215 is overworld matrix 0 row z 18: MAP_069 (cell 18,18: x 576..607), MAP_070 (19,18: x 608..639),
MAP_071 (20,18: x 640..671), z 576..607. West neighbour MAP_067 (Route 210 North), east neighbour MAP_077
(Veilstone City); north/south are MAP_176 filler. Every stock input is read from git BASE_REV so reruns never feed
back on themselves.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
sys.path.insert(0, os.path.join(ROOT, "tools", "world_art"))
import chunkedit as C  # noqa: E402
import mapdata  # noqa: E402

BASE_REV = "406c75f6a8"           # routes-wave2 contract commit (stock Route 215 chunks, set 010)
CHUNK_DIR = "res/field/mapmodels/data"
CHUNKS = {69: (18, 18), 70: (19, 18), 71: (20, 18)}
NEIGHBOURS = {"west": (67, (17, 18)), "east": (77, (21, 18))}
EVENTS_REL = "res/field/maps/route_215/events.json"
XS = range(576, 672)
ZS = range(576, 608)


def git_file(rel, rev=BASE_REV):
    return subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{rel}"], check=True, capture_output=True).stdout


def chunk_rel(c):
    return f"{CHUNK_DIR}/map_data_{c:03d}.bin"


def chunk_of(x):
    return 69 + (x - 576) // 32


def stock_chunks():
    out = {}
    for c, cell in CHUNKS.items():
        edit = C.ChunkEdit(chunk_rel(c), cell, BASE_REV)
        out[c] = dict(edit=edit, sec=edit.sec, cell=cell)
    return out


def merged_permissions(stock):
    perm = {}
    for c, d in stock.items():
        g = mapdata.read_permissions(d["sec"]["permissions"])
        cx, cz = d["cell"]
        for lz in range(32):
            for lx in range(32):
                perm[(cx * 32 + lx, cz * 32 + lz)] = g[lz][lx]
    return perm


def bdhc_height(bdhc_raw, x, z, cell):
    """World y / 16 (tiles) of the BDHC at the centre of absolute tile (x, z) of the chunk at cell."""
    b = mapdata.read_bdhc(bdhc_raw)
    lx, lz = x - cell[0] * 32, z - cell[1] * 32
    h = mapdata.height_at(b, *mapdata.tile_centre(lx, lz))
    return None if h is None else h / mapdata.FX / mapdata.TILE


def merged_heights(stock):
    hts = {}
    for c, d in stock.items():
        b = mapdata.read_bdhc(d["sec"]["bdhc"])
        cx, cz = d["cell"]
        for lz in range(32):
            for lx in range(32):
                h = mapdata.height_at(b, *mapdata.tile_centre(lx, lz))
                hts[(cx * 32 + lx, cz * 32 + lz)] = None if h is None else h / mapdata.FX / mapdata.TILE
    return hts


def stock_events():
    return json.loads(git_file(EVENTS_REL))


def event_marks(ev):
    m = {}
    for o in ev["object_events"]:
        gid = o["graphics_id"]
        ch = "T" if o["trainer_type"] != "TRAINER_TYPE_NONE" else (
            "i" if gid == "OBJ_EVENT_GFX_POKEBALL" else "c" if gid == "OBJ_EVENT_GFX_CUT_TREE" else
            "b" if gid == "OBJ_EVENT_GFX_BERRY_SOIL" else "s" if "SIGNPOST" in gid else "N")
        m[(o["x"], o["z"])] = ch
    for o in ev["bg_events"]:
        m[(o["x"], o["z"])] = "S"
    for o in ev["warp_events"]:
        m[(o["x"], o["z"])] = "W"
    for o in ev["coord_events"]:
        m.setdefault((o["x"], o["z"]), "C")
    return m


def perm_char(p):
    b = p & 0xFF
    if p & 0x8000:
        return "#"
    if b == 0:
        return "."
    if b in (0x10, 0x15, 0x13, 0x16):
        return "~"
    if b == 0x02:
        return "g"
    return "%x" % (b & 0xF)


def hchar(h):
    k = round((h - 2.0) * 2)
    if k < 0:
        return "-"
    return str(k) if k < 10 else "+"

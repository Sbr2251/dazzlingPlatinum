#!/usr/bin/env python3
"""Builds res/prebuilt/battle/graphic/battle_stage.narc.

Member BACKGROUND_PLAIN gets the backdrop piece and member BACKGROUND_MAX +
TERRAIN_PLAIN the platform piece that arena.py generates; every other member is an
empty piece, so the classic 2D scene stays on for those. The output only depends on
the stock battle graphics and this tool, so running it again gives the same bytes.

    python3 tools/battle_stage/build_stage.py [--out PATH]
"""

import argparse
import os
import sys

import arena as arena_mod
import classic
import nitro
import stage_format as sf
from fx import to_fx32

OUT = os.path.join(classic.ROOT, "res/prebuilt/battle/graphic/battle_stage.narc")

BACKGROUND_PLAIN = 0
TERRAIN_PLAIN = 0
DAY = 0

# Texture VRAM budget (docs/living_battle_stage/PLAN.md)
TEXTURE_BUDGET = 64 * 1024


def enum_count(name):
    """Index of the *_MAX line of a generated enum list."""
    with open(os.path.join(classic.ROOT, "generated", name)) as f:
        lines = [line.strip() for line in f if line.strip()]

    return next(i for i, line in enumerate(lines) if line.endswith("_MAX"))


def backdrop_textures(backdrop):
    """Textures A (rows 0..127) and B (rows 127..158) of the BG3 backdrop."""
    image = backdrop.image
    a = bytes(image[y][x] for y in range(arena_mod.TEX_A_ROWS) for x in range(256))
    first = arena_mod.TEX_B_FIRST_ROW
    b = bytes(image[y][x] for y in range(first, first + arena_mod.TEX_B_ROWS) for x in range(256))
    palette = backdrop.palettes[DAY]
    return [
        sf.Texture(256, arena_mod.TEX_A_ROWS, sf.TEXFMT_PLTT256, sf.PALETTE_BG, a, palette),
        sf.Texture(256, arena_mod.TEX_B_ROWS, sf.TEXFMT_PLTT256, sf.PALETTE_BG, b, palette),
    ]


def platform_texture(platform):
    side = platform.side
    width, height = arena_mod.PLATFORM_TEX_SIZE[side]
    ox, oy = arena_mod.PLATFORM_TEX_ORIGIN[side]
    rows = [[0] * width for _ in range(height)]

    for (x, y), index in platform.pixels.items():
        s, t = x + ox, y + oy
        assert 0 <= s < width and 0 <= t < height or index == 0, f"platform {side} pixel ({x}, {y}) is outside its texture"

        if 0 <= s < width and 0 <= t < height:
            rows[t][s] = index

    return sf.Texture(width, height, sf.TEXFMT_PLTT16, sf.PALETTE_PLATFORM_OBJ, sf.pack_pltt16(rows), platform.palettes[DAY])


def texcoord(v):
    tc = int(round(v * sf.TEXCOORD_ONE))
    assert -0x8000 <= tc <= 0x7FFF, f"texture coordinate {v} out of range"
    return tc


def file_mesh(mesh):
    vertices = [(v.pos, (texcoord(st[0]), texcoord(st[1])), sf.VERTEX_COLOR_UNSHADED) for v, st in mesh.vertices]
    return sf.Mesh(mesh.primitive, sf.MAX_ALPHA, mesh.texture, mesh.flags, vertices)


def header(arena):
    home = arena.home
    return sf.Header(
        home.cam_pos, home.cam_target, home.fovy_sin, home.fovy_cos, home.near, home.far, home.vertex_scale,
        [to_fx32(p) for p in arena.pixel_to_world])


def build_pieces():
    """(backdrop piece, platform piece, arena) for BACKGROUND_PLAIN / TERRAIN_PLAIN."""
    arena = arena_mod.Arena()
    backdrop = classic.Backdrop(BACKGROUND_PLAIN)
    assert backdrop.is_mirrored(), "REPEAT_S | FLIP_S needs a mirrored 512-wide map"
    platforms = [p.art for p in arena.platforms]

    bd = sf.Piece(header(arena), backdrop_textures(backdrop), [file_mesh(m) for m in arena.backdrop.meshes])
    pl = sf.Piece(header(arena), [platform_texture(p) for p in platforms], [file_mesh(m) for p in arena.platforms for m in p.meshes])

    textures = bd.textures + pl.textures
    tex_bytes = sum((len(t.data) + 7) & ~7 for t in textures)
    assert len(textures) <= sf.MAX_TEXTURES and len(bd.meshes) + len(pl.meshes) <= sf.MAX_MESHES
    assert tex_bytes <= TEXTURE_BUDGET, f"{tex_bytes} bytes of textures"
    return bd, pl, arena


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=OUT)
    args = parser.parse_args()

    assert enum_count("battle_backgrounds.txt") == sf.BACKGROUND_MAX
    assert enum_count("battle_terrains.txt") == sf.TERRAIN_MAX

    bd, pl, arena = build_pieces()
    members = [sf.write_piece(None)] * sf.NUM_MEMBERS
    members[BACKGROUND_PLAIN] = sf.write_piece(bd)
    members[sf.BACKGROUND_MAX + TERRAIN_PLAIN] = sf.write_piece(pl)
    nitro.write_narc(args.out, members)

    polys = sum(m.num_polygons() for m in arena.backdrop.meshes) + sum(m.num_polygons() for p in arena.platforms for m in p.meshes)
    verts = sum(len(m.vertices) for m in bd.meshes + pl.meshes)
    tex_bytes = sum(len(t.data) for t in bd.textures + pl.textures)
    print(f"{os.path.relpath(args.out)}: backdrop {len(members[BACKGROUND_PLAIN])} bytes, platforms "
          f"{len(members[sf.BACKGROUND_MAX])} bytes; {len(bd.meshes) + len(pl.meshes)} meshes, {polys} polygons, "
          f"{verts} vertices, {tex_bytes} texture bytes")


if __name__ == "__main__":
    sys.exit(main())

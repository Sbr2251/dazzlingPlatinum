#!/usr/bin/env python3
"""Builds res/prebuilt/battle/graphic/battle_stage.narc.

Every member is a real piece: the backdrop piece of each BACKGROUND_* (geometry from
arena.py, light and fog from atmosphere.py) and the platform piece of each TERRAIN_*.
The output only depends on the stock battle graphics and this tool, so running it
again gives the same bytes. Standard library only.

    python3 tools/battle_stage/build_stage.py [--out PATH] [--quiet]
"""

import argparse
import os
import sys

import arena as arena_mod
import atmosphere
import classic
import nitro
import stage_format as sf
from fx import to_fx32

OUT = os.path.join(classic.ROOT, "res/prebuilt/battle/graphic/battle_stage.narc")

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


def file_mesh(mesh, texture_index=None):
    vertices = [(v.pos, (texcoord(st[0]), texcoord(st[1])), sf.VERTEX_COLOR_UNSHADED, sf.pack_normal(n)) for v, st, n in mesh.vertices]
    texture = mesh.texture if texture_index is None else texture_index
    return sf.Mesh(mesh.primitive, sf.MAX_ALPHA, texture, mesh.flags, vertices, mesh.scroll_amplitude, mesh.scroll_period)


def header(arena):
    home = arena.home
    return sf.Header(
        home.cam_pos, home.cam_target, home.fovy_sin, home.fovy_cos, home.near, home.far, home.vertex_scale,
        [to_fx32(p) for p in arena.pixel_to_world])


def backdrop_piece(home_header, backdrop):
    art = classic.Backdrop(backdrop.background)
    assert art.is_mirrored(), f"background {backdrop.background}: REPEAT_S | FLIP_S needs a mirrored 512-wide map"
    return sf.Piece(home_header, backdrop_textures(art), [file_mesh(m) for m in backdrop.meshes], atmosphere.build(backdrop))


def platform_piece(home_header, platforms):
    """Platform piece of the non-empty platforms; textures in side order."""
    present = [p for p in platforms if p is not None]
    textures = [platform_texture(p.art) for p in present]
    meshes = [file_mesh(m, i) for i, p in enumerate(present) for m in p.meshes]
    return sf.Piece(home_header, textures, meshes)


def polygons(meshes):
    return sum(m.num_polygons() for m in meshes)


class Build:
    """Every piece plus the per-battle budget over each backdrop x terrain pair."""

    def __init__(self):
        self.home = arena_mod.HomeCamera()
        self.backdrops = [arena_mod.Backdrop(self.home, bg) for bg in range(sf.BACKGROUND_MAX)]
        self.arenas = [arena_mod.Arena(t, None, self.home) for t in range(sf.TERRAIN_MAX)]
        home_header = header(self.arenas[0])
        self.backdrop_pieces = [backdrop_piece(home_header, b) for b in self.backdrops]
        self.platform_pieces = [platform_piece(home_header, a.platforms) for a in self.arenas]
        self.max = {}

        for bg, bd in enumerate(self.backdrop_pieces):
            for t, pl in enumerate(self.platform_pieces):
                textures = bd.textures + pl.textures
                tex_bytes = sum((len(x.data) + 7) & ~7 for x in textures)
                meshes = len(bd.meshes) + len(pl.meshes)
                polys = polygons(self.backdrops[bg].meshes) + sum(polygons(p.meshes) for p in self.arenas[t].platforms if p)
                verts = sum(len(m.vertices) for m in bd.meshes + pl.meshes)
                assert len(textures) <= sf.MAX_TEXTURES, f"background {bg} terrain {t}: {len(textures)} textures"
                assert meshes <= sf.MAX_MESHES, f"background {bg} terrain {t}: {meshes} meshes"
                assert tex_bytes <= TEXTURE_BUDGET, f"background {bg} terrain {t}: {tex_bytes} bytes of textures"

                for key, value in (("texture bytes", tex_bytes), ("meshes", meshes), ("polygons", polys), ("vertices", verts)):
                    self.max[key] = max(self.max.get(key, 0), value)

    def members(self):
        return [sf.write_piece(p) for p in self.backdrop_pieces] + [sf.write_piece(p) for p in self.platform_pieces]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=OUT)
    parser.add_argument("--quiet", action="store_true", help="only print the totals")
    args = parser.parse_args()

    assert enum_count("battle_backgrounds.txt") == sf.BACKGROUND_MAX
    assert enum_count("battle_terrains.txt") == sf.TERRAIN_MAX

    build = Build()
    members = build.members()
    assert len(members) == sf.NUM_MEMBERS
    nitro.write_narc(args.out, members)
    print(f"{os.path.relpath(args.out)}: {os.path.getsize(args.out)} bytes, {len(members)} members")

    if not args.quiet:
        for bg, b in enumerate(build.backdrops):
            atm = build.backdrop_pieces[bg].atmosphere
            fog = f"fog shift {atm.fog_shift} offset {atm.fog_offset}" if atm.fog_enabled else "no fog"
            print(f"  background {bg:2} {arena_mod.KIND_NAMES[b.kind]:7} base row {b.base_row}: {len(members[bg])} bytes, "
                  f"{len(b.meshes)} meshes, {polygons(b.meshes)} polygons, {fog}")

        for t, a in enumerate(build.arenas):
            plats = [p for p in a.platforms if p]
            print(f"  terrain {t:2}: {len(members[sf.BACKGROUND_MAX + t])} bytes, {len(plats)} platforms, "
                  f"{sum(len(p.meshes) for p in plats)} meshes, {sum(polygons(p.meshes) for p in plats)} polygons")

    print("  per battle at most: " + ", ".join(f"{v} {k}" for k, v in build.max.items()))


if __name__ == "__main__":
    sys.exit(main())

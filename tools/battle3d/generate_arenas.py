#!/usr/bin/env python3
"""Procedural BDSP-style 3D battle biome arena generator (.b3d v1).

Generates all 8 Sinnoh battle biome arenas under res/battle3d/*.b3d using
pure Python 3 stdlib and validates every generated binary against sim_battle3d.h.
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
OUT_DIR = REPO_ROOT / "res" / "battle3d"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from b3d_io import (  # noqa: E402
    ArenaScene,
    B3D_SUBMESH_CAST_SHADOW,
    B3D_SUBMESH_DOUBLE_SIDED,
    B3D_SUBMESH_RECEIVE_SHADOW,
    B3D_SUBMESH_UNLIT,
    B3D_TEX_FLAG_REPEAT,
    validate_b3d,
)
from geometry import (  # noqa: E402
    add_box,
    add_broadleaf_tree,
    add_crystal_spire,
    add_cylinder,
    add_floating_island,
    add_grass_tuft,
    add_icosphere_blob,
    add_leafy_bush,
    add_mountain_ring,
    add_pine_tree,
    add_pitched_house,
    add_radial_ground,
    add_sculpted_cliff,
    add_sky_dome,
    add_wildflower,
)
from proc_textures import (  # noqa: E402
    make_bark_texture,
    make_crystal_texture,
    make_foliage_texture,
    make_gym_court_texture,
    make_painterly_ground_texture,
    make_plaza_stone_texture,
    make_rock_cliff_texture,
    make_sky_dome_texture,
    make_water_texture,
)

SHADOW_BOTH = B3D_SUBMESH_CAST_SHADOW | B3D_SUBMESH_RECEIVE_SHADOW
SKY_FLAGS = B3D_SUBMESH_UNLIT | B3D_SUBMESH_DOUBLE_SIDED


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def _lerp4(a, b, t):
    t = _clamp01(t)
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
        a[3] + (b[3] - a[3]) * t,
    )


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = _clamp01((x - edge0) / max(edge1 - edge0, 1e-6))
    return t * t * (3.0 - 2.0 * t)


def build_plain_route() -> ArenaScene:
    """Hero Sinnoh Route 201/202 sunny meadow clearing (BDSP reference style)."""
    rng = random.Random(20101)
    scene = ArenaScene("plain_route")

    sky_tex = scene.add_texture(
        256, 128,
        make_sky_dome_texture(
            256, 128, 101,
            zenith=(0.20, 0.54, 0.94),
            mid_sky=(0.44, 0.76, 0.98),
            horizon=(0.76, 0.92, 0.99),
            cloud_lit=(1.0, 0.99, 0.97),
            cloud_shade=(0.74, 0.86, 0.96),
            cloud_amount=0.58,
            sun_dir_u=0.22,
        ),
        B3D_TEX_FLAG_REPEAT,
    )
    ground_tex = scene.add_texture(
        256, 256,
        make_painterly_ground_texture(
            256, 102,
            base_tint=(0.94, 0.95, 0.90),
            dark_tint=(0.76, 0.80, 0.72),
            speck_tint=(1.0, 0.99, 0.92),
            brush_strength=0.95,
        ),
        B3D_TEX_FLAG_REPEAT,
    )
    rock_tex = scene.add_texture(
        128, 128,
        make_rock_cliff_texture(
            128, 103,
            rock_light=(0.82, 0.72, 0.56),
            rock_mid=(0.66, 0.55, 0.40),
            rock_dark=(0.44, 0.36, 0.26),
            strata_freq=7,
        ),
        B3D_TEX_FLAG_REPEAT,
    )
    pine_tex = scene.add_texture(
        128, 128,
        make_foliage_texture(
            128, 104,
            dark=(0.14, 0.36, 0.34),
            mid=(0.22, 0.50, 0.44),
            bright=(0.38, 0.68, 0.52),
            needle_style=True,
        ),
        B3D_TEX_FLAG_REPEAT,
    )
    bush_tex = scene.add_texture(
        128, 128,
        make_foliage_texture(
            128, 105,
            dark=(0.16, 0.44, 0.42),
            mid=(0.28, 0.62, 0.48),
            bright=(0.50, 0.82, 0.44),
            needle_style=False,
        ),
        B3D_TEX_FLAG_REPEAT,
    )
    bark_tex = scene.add_texture(128, 128, make_bark_texture(128, 106), B3D_TEX_FLAG_REPEAT)

    sky_sm = scene.add_submesh(sky_tex, SKY_FLAGS, roughness=1.0, fog_factor=0.0)
    mtn_sm = scene.add_submesh(rock_tex, B3D_SUBMESH_RECEIVE_SHADOW, roughness=0.95, fog_factor=1.0)
    ground_sm = scene.add_submesh(ground_tex, B3D_SUBMESH_RECEIVE_SHADOW, roughness=0.9, fog_factor=0.72)
    rock_sm = scene.add_submesh(rock_tex, SHADOW_BOTH, roughness=0.88, fog_factor=0.85)
    cap_sm = scene.add_submesh(ground_tex, SHADOW_BOTH, roughness=0.85, fog_factor=0.82)
    bark_sm = scene.add_submesh(bark_tex, SHADOW_BOTH, roughness=0.92, fog_factor=0.95)
    pine_sm = scene.add_submesh(pine_tex, SHADOW_BOTH, roughness=0.85, fog_factor=1.0)
    bush_sm = scene.add_submesh(bush_tex, SHADOW_BOTH, roughness=0.82, fog_factor=0.88)
    tuft_sm = scene.add_submesh(-1, B3D_SUBMESH_RECEIVE_SHADOW | B3D_SUBMESH_DOUBLE_SIDED, roughness=0.8, fog_factor=0.82)

    add_sky_dome(sky_sm, radius=74.0, segs_u=32, segs_v=12)
    add_mountain_ring(mtn_sm, rng, r_inner=40.0, r_peak=52.0, r_outer=64.0, segs=72)

    # Smooth flat clearing (r <= 9.2) rising into rolling green hills behind cliffs.
    def height_fn(x: float, z: float) -> float:
        r = math.hypot(x, z)
        if r <= 9.2:
            return 0.0
        t = _smoothstep(9.2, 34.0, r)
        hill = 2.6 * t + 1.35 * t * (math.sin(x * 0.14 + 0.6) * math.cos(z * 0.13 - 0.3) + 0.5)
        if z < -10.0:
            hill += 1.4 * _smoothstep(-10.0, -34.0, z)
        return hill

    def color_fn(x: float, z: float, r: float, y: float):
        # Warm sunlit sandy-ochre clearing center -> vibrant BDSP chartreuse grass -> rich forest floor.
        n = 0.5 + 0.5 * math.sin(x * 0.38 + z * 0.29) * math.cos(z * 0.44 - x * 0.21)
        dirt = (0.86, 0.78, 0.48, 1.0)
        mid_grass = (0.62, 0.84, 0.36, 1.0)
        lush_grass = (0.40, 0.72, 0.32, 1.0)
        deep_floor = (0.28, 0.56, 0.28, 1.0)
        r_warped = r + (n - 0.5) * 1.6
        if r_warped < 6.0:
            return _lerp4(dirt, mid_grass, _smoothstep(2.4, 6.0, r_warped))
        if r_warped < 14.0:
            return _lerp4(mid_grass, lush_grass, _smoothstep(6.0, 14.0, r_warped))
        return _lerp4(lush_grass, deep_floor, _smoothstep(14.0, 28.0, r_warped))

    radii = [0.0, 1.6, 3.2, 5.0, 7.0, 9.2, 11.5, 14.5, 18.5, 24.0, 31.0, 39.0]
    add_radial_ground(ground_sm, radii, 44, height_fn, color_fn, uv_scale=0.20)

    # Ring of sculpted Sinnoh earthen cliffs with bright overhanging grass caps.
    # Camera looks along (+0.37, -0.09, -0.92), so z=-10..-16, x=-10..+18 is hero framing.
    cliff_specs = [
        # Hero back cliffs directly behind opponent & framing left/right
        (-7.5, -10.8, 6.2, 4.4, 1.75, 0.25),
        (-1.4, -12.6, 6.8, 4.6, 1.60, -0.10),
        (5.6, -12.4, 7.2, 4.8, 1.85, -0.32),
        (11.8, -9.8, 6.6, 4.5, 1.80, -0.68),
        (14.6, -3.6, 6.0, 4.4, 1.65, -1.25),
        (-12.2, -5.8, 6.2, 4.4, 1.75, 0.85),
        # Rear wrap cliffs so orbits have zero holes
        (13.2, 4.0, 6.2, 4.2, 1.55, -1.85),
        (8.0, 11.2, 6.6, 4.4, 1.50, -2.55),
        (-1.5, 13.0, 7.0, 4.4, 1.50, 3.05),
        (-10.2, 9.8, 6.4, 4.4, 1.55, 2.35),
        (-14.2, 2.4, 6.0, 4.2, 1.60, 1.60),
    ]
    for cx, cz, cw, cd, ch, yaw in cliff_specs:
        by = max(0.0, height_fn(cx, cz) - 0.55)
        add_sculpted_cliff(
            rock_sm, cap_sm, cx, cz, by, cw, cd, ch, yaw, rng,
            rock_tint=(1.0, 0.98, 0.94, 1.0),
            cap_top_color=(0.48, 0.84, 0.34, 1.0),
            cap_lip_color=(0.30, 0.62, 0.24, 1.0),
            n_sides=9,
            cap_thickness=0.38,
        )

    # Hero foreground/midground stylized Sinnoh pine trees (treetops in-frame + window to mountain peak).
    hero_pines = [
        (-13.2, -6.6, 7.2, 2.15, 6),
        (-10.4, -12.2, 7.8, 2.30, 6),
        (-5.6, -15.0, 6.6, 1.95, 5),
        (-1.2, -16.2, 8.0, 2.35, 6),
        (2.8, -15.6, 6.8, 2.00, 5),
        (7.0, -14.2, 6.0, 1.85, 5),
        (14.8, -9.6, 7.4, 2.20, 6),
        (16.8, -4.6, 6.8, 2.00, 5),
        (-14.8, -1.6, 7.0, 2.05, 6),
        (-11.2, -16.0, 7.6, 2.20, 6),
    ]
    for px, pz, ph, pr, tiers in hero_pines:
        py = height_fn(px, pz) - 0.1
        add_pine_tree(
            bark_sm, pine_sm, px, py, pz, ph, pr, rng,
            tiers=tiers, lobes=9, curved=True,
            tint_dark=(0.46, 0.68, 0.62, 1.0),
            tint_lit=(0.96, 1.00, 0.90, 1.0),
        )

    # Outer forest ring (r = 18.5..34) for atmospheric blue haze depth & 360 orbit wrap.
    for i in range(30):
        ang = (i / 30.0) * math.tau + rng.uniform(-0.08, 0.08)
        if abs((ang - (-0.42) + math.pi) % math.tau - math.pi) < 0.20:
            continue
        dist = rng.uniform(18.5, 34.0)
        px = math.cos(ang) * dist
        pz = math.sin(ang) * dist
        py = height_fn(px, pz) - 0.15
        ph = rng.uniform(6.6, 10.4)
        pr = ph * rng.uniform(0.23, 0.27)
        add_pine_tree(
            bark_sm, pine_sm, px, py, pz, ph, pr, rng,
            tiers=4, lobes=7, curved=False,
            tint_dark=(0.42, 0.64, 0.62, 1.0),
            tint_lit=(0.90, 0.98, 0.90, 1.0),
        )

    # Lush bushes tucked along cliff bases.
    bush_spots = [
        (-5.2, -9.8, 1.25), (0.6, -10.8, 1.35), (4.6, -10.6, 1.10),
        (9.4, -8.8, 1.30), (11.6, -4.6, 1.20), (-9.6, -6.2, 1.20),
        (-3.0, -11.4, 1.05), (7.6, -10.2, 1.00), (-7.8, -8.6, 1.05),
        (10.8, 1.2, 1.25), (6.4, 9.6, 1.15), (-5.8, 10.0, 1.20),
    ]
    for bx, bz, br in bush_spots:
        add_leafy_bush(
            bush_sm, bx, height_fn(bx, bz), bz, br, rng,
            c_bot=(0.24, 0.56, 0.48, 1.0),
            c_top=(0.74, 0.98, 0.62, 1.0),
            puffs=4,
        )

    # Pebbles, grass tufts, and bright wildflowers around clearing edge (r = 7.4..10.4).
    for i in range(28):
        ang = (i / 28.0) * math.tau + rng.uniform(-0.1, 0.1)
        dist = rng.uniform(7.5, 10.2)
        gx = math.cos(ang) * dist
        gz = math.sin(ang) * dist
        gy = height_fn(gx, gz)
        add_grass_tuft(tuft_sm, gx, gy, gz, rng.uniform(0.75, 1.25), rng)
        if i % 3 == 0:
            petal = (1.0, 0.98, 0.88, 1.0) if (i % 6 == 0) else (1.0, 0.88, 0.36, 1.0)
            add_wildflower(tuft_sm, gx + rng.uniform(-0.4, 0.4), gy, gz + rng.uniform(-0.4, 0.4), 0.9, petal, rng)
        if i % 4 == 0:
            add_icosphere_blob(
                rock_sm, gx + rng.uniform(-0.5, 0.5), gy + 0.12, gz + rng.uniform(-0.5, 0.5),
                rng.uniform(0.28, 0.52), rng.uniform(0.18, 0.30), rng.uniform(0.26, 0.48),
                rng, (0.55, 0.50, 0.44, 1.0), (0.86, 0.80, 0.70, 1.0), flatten_bottom=0.5,
            )

    return scene


def build_forest() -> ArenaScene:
    """Eterna Forest BDSP-parity clearing: dense 3-band pine forest, mossy cliffs, flowers, distant mountains."""
    rng = random.Random(20202)
    scene = ArenaScene("forest")

    sky_tex = scene.add_texture(
        256, 128,
        make_sky_dome_texture(
            256, 128, 201,
            zenith=(0.16, 0.46, 0.78), mid_sky=(0.36, 0.68, 0.88), horizon=(0.64, 0.84, 0.86),
            cloud_amount=0.40,
        ),
        B3D_TEX_FLAG_REPEAT,
    )
    ground_tex = scene.add_texture(
        256, 256,
        make_painterly_ground_texture(
            256, 202,
            base_tint=(0.86, 0.92, 0.84),
            dark_tint=(0.60, 0.72, 0.58),
            speck_tint=(0.96, 0.98, 0.88),
        ),
        B3D_TEX_FLAG_REPEAT,
    )
    rock_tex = scene.add_texture(
        128, 128,
        make_rock_cliff_texture(
            128, 203,
            rock_light=(0.56, 0.62, 0.54),
            rock_mid=(0.38, 0.44, 0.39),
            rock_dark=(0.22, 0.27, 0.25),
            strata_freq=8,
        ),
        B3D_TEX_FLAG_REPEAT,
    )
    pine_tex = scene.add_texture(
        128, 128,
        make_foliage_texture(
            128, 204,
            dark=(0.09, 0.28, 0.28),
            mid=(0.16, 0.44, 0.38),
            bright=(0.32, 0.64, 0.44),
            needle_style=True,
        ),
        B3D_TEX_FLAG_REPEAT,
    )
    bush_tex = scene.add_texture(
        128, 128,
        make_foliage_texture(
            128, 205,
            dark=(0.12, 0.34, 0.32),
            mid=(0.22, 0.52, 0.40),
            bright=(0.40, 0.72, 0.46),
            needle_style=False,
        ),
        B3D_TEX_FLAG_REPEAT,
    )
    bark_tex = scene.add_texture(128, 128, make_bark_texture(128, 206, (0.22, 0.16, 0.12), (0.40, 0.30, 0.22)), B3D_TEX_FLAG_REPEAT)

    sky_sm = scene.add_submesh(sky_tex, SKY_FLAGS, 1.0, 0.0)
    mtn_sm = scene.add_submesh(rock_tex, B3D_SUBMESH_RECEIVE_SHADOW, 0.95, 1.0)
    ground_sm = scene.add_submesh(ground_tex, B3D_SUBMESH_RECEIVE_SHADOW, 0.92, 0.80)
    rock_sm = scene.add_submesh(rock_tex, SHADOW_BOTH, 0.90, 0.88)
    cap_sm = scene.add_submesh(ground_tex, SHADOW_BOTH, 0.86, 0.85)
    bark_sm = scene.add_submesh(bark_tex, SHADOW_BOTH, 0.92, 0.95)
    pine_sm = scene.add_submesh(pine_tex, SHADOW_BOTH, 0.86, 1.0)
    bush_sm = scene.add_submesh(bush_tex, SHADOW_BOTH, 0.84, 0.90)
    tuft_sm = scene.add_submesh(-1, B3D_SUBMESH_RECEIVE_SHADOW | B3D_SUBMESH_DOUBLE_SIDED, 0.82, 0.84)

    add_sky_dome(sky_sm, 72.0, segs_u=32, segs_v=12)
    add_mountain_ring(mtn_sm, rng, r_inner=40.0, r_peak=52.0, r_outer=64.0, segs=72)

    def hfn(x: float, z: float) -> float:
        r = math.hypot(x, z)
        if r <= 9.2:
            return 0.0
        t = _smoothstep(9.2, 34.0, r)
        hill = 2.4 * t + 1.2 * t * (math.sin(x * 0.15 + 0.4) * math.cos(z * 0.14 - 0.5) + 0.5)
        if z < -10.0:
            hill += 1.2 * _smoothstep(-10.0, -34.0, z)
        return hill

    def cfn(x: float, z: float, r: float, y: float):
        n = 0.5 + 0.5 * math.sin(x * 0.36 + z * 0.31) * math.cos(z * 0.41 - x * 0.24)
        clearing = (0.58, 0.64, 0.38, 1.0)
        grass = (0.36, 0.64, 0.32, 1.0)
        moss = (0.24, 0.52, 0.28, 1.0)
        deep = (0.14, 0.34, 0.20, 1.0)
        rw = r + (n - 0.5) * 1.6
        if rw < 5.5:
            return _lerp4(clearing, grass, _smoothstep(2.2, 5.5, rw))
        if rw < 13.5:
            return _lerp4(grass, moss, _smoothstep(5.5, 13.5, rw))
        return _lerp4(moss, deep, _smoothstep(13.5, 26.0, rw))

    add_radial_ground(ground_sm, [0.0, 1.8, 3.6, 5.5, 7.4, 9.2, 11.8, 15.0, 19.5, 25.0, 32.0, 39.0], 44, hfn, cfn, 0.20)

    # Sculpted mossy rock cliff ledges framing the clearing (low enough to show treetops & sky)
    cliff_specs = [
        (-8.2, -10.2, 6.4, 4.4, 1.75, 0.25),
        (-2.2, -12.4, 6.8, 4.6, 1.60, -0.10),
        (4.8, -12.2, 6.8, 4.6, 1.80, -0.32),
        (11.6, -8.8, 6.4, 4.4, 1.75, -0.75),
        (14.4, -3.2, 6.0, 4.2, 1.65, -1.25),
        (-12.2, -5.2, 6.2, 4.4, 1.70, 0.85),
        (12.8, 4.2, 6.2, 4.2, 1.55, -1.85),
        (7.6, 11.2, 6.6, 4.4, 1.50, -2.55),
        (-1.5, 13.0, 7.0, 4.4, 1.50, 3.05),
        (-10.2, 9.8, 6.4, 4.4, 1.55, 2.35),
    ]
    for cx, cz, w, d, ch, yaw in cliff_specs:
        add_sculpted_cliff(
            rock_sm, cap_sm, cx, cz, hfn(cx, cz), w, d, ch, yaw, rng,
            rock_tint=(0.86, 0.90, 0.88, 1.0),
            cap_top_color=(0.36, 0.68, 0.34, 1.0),
            cap_lip_color=(0.22, 0.48, 0.24, 1.0),
            n_sides=9,
            cap_thickness=0.38,
        )

    def _near_cam(px: float, pz: float) -> bool:
        return math.hypot(px - (-4.2), pz - 6.8) < 4.5 or (-6.5 < px < -0.5 and 3.0 < pz < 10.5)

    # Band 1: Hero foreground/midground curved 6-tier pines framing left, back, and right
    # Heights 6.2..8.0m so treetops sit cleanly in-frame against the starry sky,
    # leaving a scenic window on the right-back for the distant mountain peak.
    hero_pines = [
        (-13.4, -6.8, 7.2, 2.2, 6), (-10.8, -12.6, 8.0, 2.4, 6), (-6.2, -15.2, 6.8, 2.0, 5),
        (-1.4, -16.4, 8.2, 2.4, 6), (2.8, -16.0, 6.8, 2.0, 5), (6.8, -14.8, 6.0, 1.9, 5),
        (15.2, -9.8, 7.4, 2.2, 6), (17.2, -4.4, 6.8, 2.0, 5), (16.8, 1.0, 6.4, 1.9, 5),
        (-15.2, -1.2, 7.2, 2.1, 6), (-14.4, 4.4, 6.6, 2.0, 5),
    ]
    for px, pz, h, rad, tiers in hero_pines:
        add_pine_tree(
            bark_sm, pine_sm, px, hfn(px, pz) - 0.1, pz, h, rad, rng,
            tiers=tiers, lobes=9, curved=True,
            tint_dark=(0.42, 0.62, 0.58, 1.0),
            tint_lit=(0.94, 1.0, 0.88, 1.0),
        )

    # Band 2: Mid-back forest wall (24 trees)
    for k in range(24):
        ang = (k / 24.0) * math.tau + rng.uniform(-0.08, 0.08)
        # Keep scenic valley window toward hero mountain (-0.42 rad)
        if abs((ang - (-0.42) + math.pi) % math.tau - math.pi) < 0.24:
            continue
        dist = rng.uniform(18.5, 25.5)
        tx, tz = math.cos(ang) * dist, math.sin(ang) * dist
        if _near_cam(tx, tz):
            continue
        h = rng.uniform(7.0, 10.2)
        add_pine_tree(
            bark_sm, pine_sm, tx, hfn(tx, tz) - 0.1, tz, h, h * rng.uniform(0.23, 0.27), rng,
            tiers=5, lobes=8, curved=True,
            tint_dark=(0.40, 0.60, 0.58, 1.0),
            tint_lit=(0.90, 0.98, 0.88, 1.0),
        )

    # Band 3: Far silhouette treeline (28 LOD trees bathed in atmospheric haze)
    for k in range(28):
        ang = (k / 28.0) * math.tau + rng.uniform(-0.07, 0.07)
        if abs((ang - (-0.42) + math.pi) % math.tau - math.pi) < 0.18:
            continue
        dist = rng.uniform(27.5, 36.5)
        tx, tz = math.cos(ang) * dist, math.sin(ang) * dist
        h = rng.uniform(7.8, 11.2)
        add_pine_tree(
            bark_sm, pine_sm, tx, hfn(tx, tz) - 0.1, tz, h, h * rng.uniform(0.22, 0.26), rng,
            tiers=4, lobes=7, curved=False,
            tint_dark=(0.38, 0.56, 0.60, 1.0),
            tint_lit=(0.82, 0.92, 0.90, 1.0),
        )

    # Lush bushes & mossy boulders tucked along cliff bases
    bush_spots = [
        (-5.2, -9.8, 1.25), (0.8, -10.8, 1.35), (4.6, -10.4, 1.15),
        (9.2, -8.6, 1.30), (11.6, -4.4, 1.20), (-9.6, -6.2, 1.20),
        (-3.0, -11.2, 1.05), (7.6, -10.0, 1.00), (-7.8, -8.6, 1.05),
        (10.8, 1.2, 1.25), (6.4, 9.6, 1.15), (-5.8, 10.0, 1.20),
    ]
    for bx, bz, br in bush_spots:
        add_leafy_bush(
            bush_sm, bx, hfn(bx, bz) - 0.04, bz, br, rng,
            c_bot=(0.20, 0.48, 0.44, 1.0),
            c_top=(0.64, 0.92, 0.60, 1.0),
            puffs=4,
        )

    for i in range(12):
        ang = (i / 12.0) * math.tau + rng.uniform(-0.15, 0.15)
        dist = rng.uniform(8.8, 11.0)
        rx, rz = math.cos(ang) * dist, math.sin(ang) * dist
        if _near_cam(rx, rz):
            continue
        add_icosphere_blob(
            rock_sm, rx, hfn(rx, rz) + 0.25, rz,
            rng.uniform(0.45, 0.85), rng.uniform(0.30, 0.50), rng.uniform(0.42, 0.78),
            rng, (0.38, 0.44, 0.40, 1.0), (0.56, 0.72, 0.52, 1.0), flatten_bottom=0.45,
        )

    # Grass tufts & tiny white/blue wildflowers along cliff base
    for i in range(44):
        ang = (i / 44.0) * math.tau + rng.uniform(-0.08, 0.08)
        dist = rng.uniform(7.4, 10.2)
        gx, gz = math.cos(ang) * dist, math.sin(ang) * dist
        if _near_cam(gx, gz):
            continue
        gy = hfn(gx, gz)
        add_grass_tuft(
            tuft_sm, gx, gy, gz, rng.uniform(0.80, 1.30), rng,
            c_root=(0.18, 0.44, 0.22, 1.0),
            c_tip=(0.48, 0.82, 0.36, 1.0),
        )
        if i % 2 == 0:
            petal = (0.96, 0.98, 1.0, 1.0) if (i % 4 == 0) else (0.76, 0.88, 1.0, 1.0)
            add_wildflower(tuft_sm, gx + rng.uniform(-0.35, 0.35), gy, gz + rng.uniform(-0.35, 0.35), rng.uniform(1.2, 1.5), petal, rng)

    return scene


def build_water_lake() -> ArenaScene:
    """Sinnoh Lake Verity / Valor shoreline clearing with sparkling lake behind."""
    rng = random.Random(20303)
    scene = ArenaScene("water_lake")

    sky_tex = scene.add_texture(256, 128, make_sky_dome_texture(256, 128, 301, (0.18, 0.52, 0.94), (0.44, 0.78, 0.98), (0.78, 0.94, 1.0), cloud_amount=0.52), B3D_TEX_FLAG_REPEAT)
    ground_tex = scene.add_texture(256, 256, make_painterly_ground_texture(256, 302, (0.96, 0.94, 0.84), (0.80, 0.78, 0.66)), B3D_TEX_FLAG_REPEAT)
    water_tex = scene.add_texture(256, 256, make_water_texture(256, 303), B3D_TEX_FLAG_REPEAT)
    rock_tex = scene.add_texture(128, 128, make_rock_cliff_texture(128, 304, (0.74, 0.70, 0.60), (0.56, 0.54, 0.48), (0.36, 0.38, 0.36)), B3D_TEX_FLAG_REPEAT)
    pine_tex = scene.add_texture(128, 128, make_foliage_texture(128, 305, (0.14, 0.38, 0.36), (0.24, 0.54, 0.46), (0.42, 0.72, 0.52), True), B3D_TEX_FLAG_REPEAT)
    bark_tex = scene.add_texture(128, 128, make_bark_texture(128, 306), B3D_TEX_FLAG_REPEAT)

    sky_sm = scene.add_submesh(sky_tex, SKY_FLAGS, 1.0, 0.0)
    mtn_sm = scene.add_submesh(rock_tex, B3D_SUBMESH_RECEIVE_SHADOW, 0.95, 1.0)
    ground_sm = scene.add_submesh(ground_tex, B3D_SUBMESH_RECEIVE_SHADOW, 0.88, 0.72)
    water_sm = scene.add_submesh(water_tex, B3D_SUBMESH_RECEIVE_SHADOW, 0.25, 0.82)
    rock_sm = scene.add_submesh(rock_tex, SHADOW_BOTH, 0.85, 0.88)
    cap_sm = scene.add_submesh(ground_tex, SHADOW_BOTH, 0.85, 0.85)
    bark_sm = scene.add_submesh(bark_tex, SHADOW_BOTH, 0.92, 0.95)
    pine_sm = scene.add_submesh(pine_tex, SHADOW_BOTH, 0.85, 1.0)

    add_sky_dome(sky_sm, 74.0)
    add_mountain_ring(mtn_sm, rng, r_inner=42.0, r_peak=54.0, r_outer=65.0, segs=72)

    def shore_h(x, z):
        r = math.hypot(x, z)
        if r <= 8.5:
            return 0.0
        if z < -6.5:
            return -0.65 * _smoothstep(-6.5, -14.0, z)
        return 0.9 * _smoothstep(8.5, 24.0, r)

    def shore_c(x, z, r, y):
        sand = (0.92, 0.86, 0.64, 1.0)
        grass = (0.48, 0.78, 0.38, 1.0)
        wet = (0.64, 0.62, 0.50, 1.0)
        if y < -0.1:
            return wet
        return _lerp4(sand, grass, _smoothstep(4.5, 10.5, r))

    add_radial_ground(ground_sm, [0.0, 2.2, 4.8, 7.5, 10.0, 14.0, 20.0, 30.0], 40, shore_h, shore_c, 0.20)
    # Calm sparkling lake plane slightly below clearing at y = -0.22
    add_radial_ground(water_sm, [0.0, 8.0, 16.0, 28.0, 44.0], 32, lambda x, z: -0.22, lambda x, z, r, y: (0.85, 0.95, 1.0, 1.0), 0.14)

    # Distant forested lake shore / island behind the water
    for cx, cz, cw, ch in [(-14.0, -24.0, 11.0, 2.8), (2.0, -28.0, 14.0, 3.2), (17.0, -22.0, 11.0, 2.6)]:
        add_sculpted_cliff(rock_sm, cap_sm, cx, cz, -0.5, cw, 7.0, ch, rng.uniform(-0.4, 0.4), rng)
        for k in range(5):
            px = cx + rng.uniform(-cw * 0.45, cw * 0.45)
            pz = cz + rng.uniform(-2.5, 2.5)
            add_pine_tree(bark_sm, pine_sm, px, ch - 0.3, pz, rng.uniform(7.0, 10.5), rng.uniform(2.0, 2.6), rng)

    for i in range(10):
        ang = rng.uniform(-0.4, math.pi + 0.4)
        dist = rng.uniform(11.5, 22.0)
        px, pz = math.cos(ang) * dist, math.sin(ang) * dist
        add_pine_tree(bark_sm, pine_sm, px, shore_h(px, pz), pz, rng.uniform(7.5, 10.5), 2.3, rng)
    return scene


def build_mountain_cave() -> ArenaScene:
    """Mt. Coronet / Oreburgh rocky cavern with glowing crystal veins."""
    rng = random.Random(20404)
    scene = ArenaScene("mountain_cave")

    sky_tex = scene.add_texture(256, 128, make_sky_dome_texture(256, 128, 401, (0.08, 0.09, 0.14), (0.14, 0.16, 0.22), (0.20, 0.22, 0.28), cloud_amount=0.15), B3D_TEX_FLAG_REPEAT)
    floor_tex = scene.add_texture(256, 256, make_painterly_ground_texture(256, 402, (0.58, 0.56, 0.54), (0.36, 0.36, 0.38), (0.74, 0.72, 0.68)), B3D_TEX_FLAG_REPEAT)
    rock_tex = scene.add_texture(128, 128, make_rock_cliff_texture(128, 403, (0.54, 0.52, 0.56), (0.36, 0.35, 0.40), (0.20, 0.20, 0.25), strata_freq=10), B3D_TEX_FLAG_REPEAT)
    crys_tex = scene.add_texture(128, 128, make_crystal_texture(128, 404, (0.62, 0.90, 1.0), (0.24, 0.52, 0.92)), B3D_TEX_FLAG_REPEAT)

    sky_sm = scene.add_submesh(sky_tex, SKY_FLAGS, 1.0, 0.0)
    floor_sm = scene.add_submesh(floor_tex, B3D_SUBMESH_RECEIVE_SHADOW, 0.92, 0.85)
    rock_sm = scene.add_submesh(rock_tex, SHADOW_BOTH, 0.90, 0.95)
    crys_sm = scene.add_submesh(crys_tex, B3D_SUBMESH_UNLIT, 0.20, 0.45)

    add_sky_dome(sky_sm, 64.0)
    add_radial_ground(
        floor_sm, [0.0, 2.5, 5.5, 8.8, 12.5, 18.0, 28.0], 36,
        lambda x, z: 0.0 if math.hypot(x, z) <= 8.8 else 2.2 * _smoothstep(8.8, 28.0, math.hypot(x, z)),
        lambda x, z, r, y: _lerp4((0.72, 0.68, 0.64, 1.0), (0.38, 0.38, 0.44, 1.0), _smoothstep(3.0, 18.0, r)),
        0.22,
    )

    for i in range(18):
        ang = (i / 18.0) * math.tau
        dist = rng.uniform(11.5, 18.0)
        cx, cz = math.cos(ang) * dist, math.sin(ang) * dist
        add_sculpted_cliff(rock_sm, rock_sm, cx, cz, -0.3, rng.uniform(5.0, 8.0), rng.uniform(4.0, 6.0), rng.uniform(4.5, 9.0), ang, rng,
                           rock_tint=(0.85, 0.86, 0.92, 1.0), cap_top_color=(0.48, 0.48, 0.54, 1.0), cap_lip_color=(0.32, 0.32, 0.38, 1.0))

    for i in range(16):
        ang = (i / 16.0) * math.tau + 0.15
        dist = rng.uniform(9.2, 13.5)
        sx, sz = math.cos(ang) * dist, math.sin(ang) * dist
        add_crystal_spire(crys_sm, sx, 0.0, sz, rng.uniform(0.35, 0.65), rng.uniform(1.6, 3.8), rng.uniform(-0.22, 0.22), rng.uniform(-0.22, 0.22),
                          (0.30, 0.62, 0.96, 1.0), (0.82, 0.98, 1.0, 1.0))
    return scene


def build_snow() -> ArenaScene:
    """Snowpoint / Route 216 snowy clearing with frost-dusted pines."""
    rng = random.Random(20505)
    scene = ArenaScene("snow")

    sky_tex = scene.add_texture(256, 128, make_sky_dome_texture(256, 128, 501, (0.38, 0.62, 0.88), (0.62, 0.80, 0.94), (0.86, 0.93, 0.98), cloud_amount=0.62), B3D_TEX_FLAG_REPEAT)
    snow_tex = scene.add_texture(256, 256, make_painterly_ground_texture(256, 502, (0.95, 0.97, 1.0), (0.78, 0.86, 0.95), (1.0, 1.0, 1.0)), B3D_TEX_FLAG_REPEAT)
    rock_tex = scene.add_texture(128, 128, make_rock_cliff_texture(128, 503, (0.66, 0.72, 0.82), (0.46, 0.54, 0.66), (0.28, 0.36, 0.48)), B3D_TEX_FLAG_REPEAT)
    pine_tex = scene.add_texture(128, 128, make_foliage_texture(128, 504, (0.16, 0.34, 0.40), (0.30, 0.50, 0.56), (0.78, 0.88, 0.96), True), B3D_TEX_FLAG_REPEAT)
    bark_tex = scene.add_texture(128, 128, make_bark_texture(128, 505, (0.24, 0.20, 0.20), (0.44, 0.38, 0.36)), B3D_TEX_FLAG_REPEAT)

    sky_sm = scene.add_submesh(sky_tex, SKY_FLAGS, 1.0, 0.0)
    mtn_sm = scene.add_submesh(rock_tex, B3D_SUBMESH_RECEIVE_SHADOW, 0.92, 1.0)
    ground_sm = scene.add_submesh(snow_tex, B3D_SUBMESH_RECEIVE_SHADOW, 0.78, 0.78)
    rock_sm = scene.add_submesh(rock_tex, SHADOW_BOTH, 0.85, 0.88)
    cap_sm = scene.add_submesh(snow_tex, SHADOW_BOTH, 0.75, 0.85)
    bark_sm = scene.add_submesh(bark_tex, SHADOW_BOTH, 0.92, 0.95)
    pine_sm = scene.add_submesh(pine_tex, SHADOW_BOTH, 0.82, 1.0)

    add_sky_dome(sky_sm, 74.0)
    add_mountain_ring(mtn_sm, rng, r_inner=40.0, r_peak=52.0, r_outer=64.0, segs=72, c_base=(0.45, 0.56, 0.74, 1.0), c_peak=(0.82, 0.90, 0.98, 1.0))

    def hfn(x, z):
        r = math.hypot(x, z)
        return 0.0 if r <= 9.2 else 2.8 * _smoothstep(9.2, 34.0, r)

    add_radial_ground(
        ground_sm, [0.0, 2.2, 5.0, 9.2, 14.0, 22.0, 36.0], 40, hfn,
        lambda x, z, r, y: _lerp4((0.96, 0.98, 1.0, 1.0), (0.78, 0.88, 0.98, 1.0), _smoothstep(5.0, 24.0, r)),
        0.20,
    )

    for i in range(10):
        ang = (i / 10.0) * math.tau
        cx, cz = math.cos(ang) * 13.0, math.sin(ang) * 13.0
        add_sculpted_cliff(rock_sm, cap_sm, cx, cz, max(0.0, hfn(cx, cz) - 0.5), 6.5, 4.6, 2.4, ang, rng,
                           rock_tint=(0.9, 0.95, 1.0, 1.0), cap_top_color=(0.94, 0.97, 1.0, 1.0), cap_lip_color=(0.76, 0.86, 0.96, 1.0))

    for i in range(34):
        ang = (i / 34.0) * math.tau + rng.uniform(-0.08, 0.08)
        if abs((ang - (-0.42) + math.pi) % math.tau - math.pi) < 0.20:
            continue
        dist = rng.uniform(12.5, 32.0)
        px, pz = math.cos(ang) * dist, math.sin(ang) * dist
        add_pine_tree(bark_sm, pine_sm, px, hfn(px, pz) + 0.1, pz, rng.uniform(6.8, 10.2), rng.uniform(1.9, 2.5), rng, tiers=5, lobes=8, curved=(dist < 22.0), snow_dusted=True)
    return scene


def build_city() -> ArenaScene:
    """Jubilife / Veilstone paved battle plaza framed by hedges and Sinnoh roofs."""
    rng = random.Random(20606)
    scene = ArenaScene("city")

    sky_tex = scene.add_texture(256, 128, make_sky_dome_texture(256, 128, 601, (0.22, 0.56, 0.94), (0.48, 0.78, 0.98), (0.80, 0.92, 0.99), cloud_amount=0.48), B3D_TEX_FLAG_REPEAT)
    plaza_tex = scene.add_texture(256, 256, make_plaza_stone_texture(256, 602), B3D_TEX_FLAG_REPEAT)
    leaf_tex = scene.add_texture(128, 128, make_foliage_texture(128, 603, (0.16, 0.42, 0.26), (0.28, 0.62, 0.36), (0.48, 0.82, 0.46), False), B3D_TEX_FLAG_REPEAT)
    bark_tex = scene.add_texture(128, 128, make_bark_texture(128, 604), B3D_TEX_FLAG_REPEAT)

    sky_sm = scene.add_submesh(sky_tex, SKY_FLAGS, 1.0, 0.0)
    floor_sm = scene.add_submesh(plaza_tex, B3D_SUBMESH_RECEIVE_SHADOW, 0.75, 0.72)
    wall_sm = scene.add_submesh(-1, SHADOW_BOTH, 0.82, 0.88)
    roof_sm = scene.add_submesh(-1, SHADOW_BOTH, 0.72, 0.90)
    leaf_sm = scene.add_submesh(leaf_tex, SHADOW_BOTH, 0.82, 0.88)
    bark_sm = scene.add_submesh(bark_tex, SHADOW_BOTH, 0.90, 0.90)

    add_sky_dome(sky_sm, 74.0)
    add_radial_ground(floor_sm, [0.0, 3.0, 6.5, 10.5, 16.0, 26.0, 36.0], 40, lambda x, z: 0.0,
                      lambda x, z, r, y: (0.94, 0.93, 0.90, 1.0) if r < 11.0 else (0.78, 0.80, 0.82, 1.0), 0.24)

    # Low stone curb + hedges ringing the plaza
    for i in range(16):
        ang = (i / 16.0) * math.tau
        hx, hz = math.cos(ang) * 11.2, math.sin(ang) * 11.2
        add_box(wall_sm, hx, 0.35, hz, 3.6, 0.7, 0.75, -ang + math.pi * 0.5, (0.86, 0.84, 0.80, 1.0), (0.94, 0.92, 0.88, 1.0))
        if i % 2 == 0:
            add_leafy_bush(leaf_sm, hx * 1.08, 0.3, hz * 1.08, 1.15, rng)

    # Sinnoh town houses & broadleaf trees around perimeter
    roof_palette = [(0.74, 0.26, 0.26, 1.0), (0.28, 0.46, 0.76, 1.0), (0.26, 0.58, 0.46, 1.0)]
    for i in range(10):
        ang = (i / 10.0) * math.tau + 0.2
        dist = rng.uniform(17.0, 23.0)
        hx, hz = math.cos(ang) * dist, math.sin(ang) * dist
        add_pitched_house(wall_sm, roof_sm, hx, 0.0, hz, 6.0, 5.2, 4.2, 2.4, -ang, (0.94, 0.92, 0.86, 1.0), roof_palette[i % 3])
        tx, tz = math.cos(ang + 0.3) * (dist - 3.0), math.sin(ang + 0.3) * (dist - 3.0)
        add_broadleaf_tree(bark_sm, leaf_sm, tx, 0.0, tz, rng.uniform(5.8, 7.6), 2.2, rng)
    return scene


def build_indoors_gym() -> ArenaScene:
    """Sinnoh Gym / League stadium court with painted markings and pillars."""
    scene = ArenaScene("indoors_gym")

    sky_tex = scene.add_texture(256, 128, make_sky_dome_texture(256, 128, 701, (0.18, 0.24, 0.36), (0.28, 0.36, 0.50), (0.46, 0.52, 0.62), cloud_amount=0.10), B3D_TEX_FLAG_REPEAT)
    court_tex = scene.add_texture(256, 256, make_gym_court_texture(256, 702), B3D_TEX_FLAG_REPEAT)

    sky_sm = scene.add_submesh(sky_tex, SKY_FLAGS, 1.0, 0.0)
    floor_sm = scene.add_submesh(court_tex, B3D_SUBMESH_RECEIVE_SHADOW, 0.55, 0.45)
    arch_sm = scene.add_submesh(-1, SHADOW_BOTH, 0.65, 0.60)
    trim_sm = scene.add_submesh(-1, B3D_SUBMESH_UNLIT, 0.25, 0.20)

    add_sky_dome(sky_sm, 60.0)
    add_radial_ground(floor_sm, [0.0, 3.0, 6.5, 10.5, 16.0, 24.0], 40, lambda x, z: 0.0,
                      lambda x, z, r, y: (1.0, 1.0, 1.0, 1.0), planar_uv_radius=12.0)

    # Stadium walls and architectural pillars
    for i in range(12):
        ang = (i / 12.0) * math.tau
        px, pz = math.cos(ang) * 14.5, math.sin(ang) * 14.5
        add_cylinder(arch_sm, px, 0.0, pz, 0.85, 0.72, 11.0, 10, (0.64, 0.68, 0.76, 1.0), (0.86, 0.88, 0.94, 1.0), cap_top=True)
        wx, wz = math.cos(ang + math.pi / 12.0) * 15.8, math.sin(ang + math.pi / 12.0) * 15.8
        add_box(arch_sm, wx, 4.5, wz, 8.2, 9.0, 1.2, -(ang + math.pi / 12.0) + math.pi * 0.5, (0.56, 0.60, 0.70, 1.0), (0.72, 0.76, 0.84, 1.0))
        add_box(trim_sm, wx * 0.95, 8.2, wz * 0.95, 6.8, 0.35, 0.3, -(ang + math.pi / 12.0) + math.pi * 0.5, (0.76, 0.90, 1.0, 1.0))
    return scene


def build_distortion_world() -> ArenaScene:
    """Distortion World floating fractured island amidst cosmic nebula & inverted spires."""
    rng = random.Random(20808)
    scene = ArenaScene("distortion_world")

    sky_tex = scene.add_texture(
        256, 128,
        make_sky_dome_texture(
            256, 128, 801,
            zenith=(0.08, 0.04, 0.22), mid_sky=(0.24, 0.12, 0.44), horizon=(0.44, 0.20, 0.52),
            cloud_lit=(0.74, 0.42, 0.92), cloud_shade=(0.24, 0.14, 0.42), cloud_amount=0.65, nebula_mode=True,
        ),
        B3D_TEX_FLAG_REPEAT,
    )
    floor_tex = scene.add_texture(256, 256, make_painterly_ground_texture(256, 802, (0.54, 0.48, 0.68), (0.30, 0.26, 0.44), (0.72, 0.64, 0.88)), B3D_TEX_FLAG_REPEAT)
    rock_tex = scene.add_texture(128, 128, make_rock_cliff_texture(128, 803, (0.44, 0.36, 0.58), (0.28, 0.22, 0.40), (0.14, 0.12, 0.24)), B3D_TEX_FLAG_REPEAT)
    crys_tex = scene.add_texture(128, 128, make_crystal_texture(128, 804, (0.86, 0.48, 1.0), (0.42, 0.18, 0.78)), B3D_TEX_FLAG_REPEAT)

    sky_sm = scene.add_submesh(sky_tex, SKY_FLAGS, 1.0, 0.0)
    floor_sm = scene.add_submesh(floor_tex, B3D_SUBMESH_RECEIVE_SHADOW, 0.85, 0.55)
    rock_sm = scene.add_submesh(rock_tex, SHADOW_BOTH, 0.88, 0.70)
    crys_sm = scene.add_submesh(crys_tex, B3D_SUBMESH_UNLIT, 0.20, 0.35)

    add_sky_dome(sky_sm, 74.0, elev_min=-0.65)
    add_radial_ground(floor_sm, [0.0, 2.5, 5.5, 8.6, 10.2], 32, lambda x, z: 0.0,
                      lambda x, z, r, y: _lerp4((0.76, 0.70, 0.88, 1.0), (0.42, 0.36, 0.60, 1.0), _smoothstep(4.0, 10.2, r)), 0.22)

    for i in range(14):
        ang = (i / 14.0) * math.tau + rng.uniform(-0.1, 0.1)
        dist = rng.uniform(14.0, 28.0)
        ix, iz = math.cos(ang) * dist, math.sin(ang) * dist
        iy = rng.uniform(-1.5, 7.5)
        add_floating_island(floor_sm, rock_sm, ix, iy, iz, rng.uniform(2.0, 4.2), rng.uniform(2.5, 5.5), rng,
                            (0.56, 0.48, 0.74, 1.0), (0.32, 0.26, 0.48, 1.0))
        add_crystal_spire(crys_sm, ix, iy, iz, rng.uniform(0.45, 0.85), rng.uniform(2.5, 5.5),
                          rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25),
                          (0.52, 0.22, 0.86, 1.0), (0.96, 0.62, 1.0, 1.0), invert_y=(i % 3 == 0))
    return scene


BIOME_BUILDERS = [
    ("plain_route.b3d", build_plain_route),
    ("forest.b3d", build_forest),
    ("water_lake.b3d", build_water_lake),
    ("mountain_cave.b3d", build_mountain_cave),
    ("snow.b3d", build_snow),
    ("city.b3d", build_city),
    ("indoors_gym.b3d", build_indoors_gym),
    ("distortion_world.b3d", build_distortion_world),
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, builder in BIOME_BUILDERS:
        out_path = OUT_DIR / filename
        scene = builder()
        scene.write_b3d(out_path)
        stats = validate_b3d(out_path)
        print(
            f"[OK] {filename:22s}  {stats['bytes']//1024:4d} KB  "
            f"tris={stats['triangles']:5d}  verts={stats['vertices']:5d}  "
            f"submeshes={stats['submeshes']:2d}  tex={stats['textures']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

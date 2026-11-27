"""Outdoor natural Sinnoh biome builders: plain_route (hero), forest, water_lake, snow."""

from __future__ import annotations

import math
import random
from typing import Tuple

from b3d_io import (
    ArenaScene,
    B3D_SUBMESH_CAST_SHADOW,
    B3D_SUBMESH_DOUBLE_SIDED,
    B3D_SUBMESH_RECEIVE_SHADOW,
    B3D_SUBMESH_UNLIT,
    B3D_TEX_FLAG_REPEAT,
)
from geometry import (
    Color4,
    add_broadleaf_tree,
    add_grass_tuft,
    add_icosphere_blob,
    add_leafy_bush,
    add_pine_tree,
    add_radial_ground,
    add_sculpted_cliff,
    add_sky_dome,
    add_wildflower,
)
from proc_textures import (
    make_bark_texture,
    make_foliage_texture,
    make_painterly_ground_texture,
    make_rock_cliff_texture,
    make_sky_dome_texture,
    make_water_texture,
)

CAST_RECV = B3D_SUBMESH_CAST_SHADOW | B3D_SUBMESH_RECEIVE_SHADOW
SKY_FLAGS = B3D_SUBMESH_UNLIT | B3D_SUBMESH_DOUBLE_SIDED


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def _smoothstep(a: float, b: float, x: float) -> float:
    t = _clamp01((x - a) / max(1e-6, b - a))
    return t * t * (3.0 - 2.0 * t)


def _lerp4(a: Color4, b: Color4, t: float) -> Color4:
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
        a[3] + (b[3] - a[3]) * t,
    )


def _organic_noise(x: float, z: float, phase: float = 0.0) -> float:
    """Fast deterministic multi-sine organic variation in [-1, 1]."""
    return (
        0.50 * math.sin(x * 0.27 + z * 0.19 + phase)
        + 0.30 * math.cos(x * 0.43 - z * 0.37 + phase * 1.7)
        + 0.20 * math.sin((x - z) * 0.61 + phase * 0.6)
    )


def _near_home_camera(x: float, z: float, margin: float = 3.2) -> bool:
    """Keep home camera at (-3.6, 2.35, +8.4) and its sightline to (+0.5, 1.35, -1.8) unobstructed."""
    if math.hypot(x - (-3.6), z - 8.4) < margin:
        return True
    # Slight clearance behind player battler (-2.2, +2.8) toward camera
    if -6.0 < x < -0.5 and 4.0 < z < 11.2:
        return True
    return False


def build_plain_route() -> ArenaScene:
    """HERO BIOME (SIM_BATTLE3D_BIOME_PLAIN = 0): Sinnoh Route 201/202 sunny clearing."""
    rng = random.Random(201202)
    scene = ArenaScene("plain_route")

    # Textures: 256x128 sky, 256x256 ground, 128x128 cliff rock, 128x128 pine, 64x64 bark
    tex_sky = scene.add_texture(
        256, 128,
        make_sky_dome_texture(
            256, 128, seed=101,
            zenith=(0.17, 0.50, 0.90),
            mid_sky=(0.42, 0.75, 0.98),
            horizon=(0.78, 0.91, 0.99),
            cloud_lit=(1.0, 0.99, 0.96),
            cloud_shade=(0.76, 0.86, 0.96),
            cloud_amount=0.62,
            sun_dir_u=0.82,
        ),
        flags=0,
    )
    tex_ground = scene.add_texture(
        256, 256,
        make_painterly_ground_texture(
            256, seed=102,
            base_tint=(0.94, 0.95, 0.89),
            dark_tint=(0.76, 0.80, 0.72),
            speck_tint=(1.0, 0.99, 0.92),
            brush_strength=1.0,
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_rock = scene.add_texture(
        128, 128,
        make_rock_cliff_texture(
            128, seed=103,
            rock_light=(0.82, 0.67, 0.46),
            rock_mid=(0.64, 0.49, 0.32),
            rock_dark=(0.42, 0.31, 0.21),
            strata_freq=7,
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_pine = scene.add_texture(
        128, 128,
        make_foliage_texture(
            128, seed=104,
            dark=(0.14, 0.36, 0.25),
            mid=(0.24, 0.56, 0.32),
            bright=(0.46, 0.78, 0.36),
            needle_style=True,
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_bark = scene.add_texture(
        64, 64,
        make_bark_texture(64, seed=105, dark=(0.30, 0.20, 0.13), light=(0.54, 0.38, 0.25)),
        flags=B3D_TEX_FLAG_REPEAT,
    )

    # Submeshes
    sm_sky = scene.add_submesh(tex_sky, SKY_FLAGS, roughness=1.0, fog_factor=0.0)
    sm_ground = scene.add_submesh(tex_ground, B3D_SUBMESH_RECEIVE_SHADOW, roughness=0.90, fog_factor=0.75)
    sm_rock = scene.add_submesh(tex_rock, CAST_RECV, roughness=0.88, fog_factor=0.85)
    sm_cap = scene.add_submesh(tex_ground, CAST_RECV, roughness=0.84, fog_factor=0.85)
    sm_bark = scene.add_submesh(tex_bark, CAST_RECV, roughness=0.90, fog_factor=1.0)
    sm_pine = scene.add_submesh(tex_pine, CAST_RECV, roughness=0.78, fog_factor=1.0)
    sm_bush = scene.add_submesh(tex_pine, CAST_RECV, roughness=0.76, fog_factor=0.85)
    sm_flora = scene.add_submesh(-1, B3D_SUBMESH_RECEIVE_SHADOW | B3D_SUBMESH_DOUBLE_SIDED, roughness=0.72, fog_factor=0.85)

    # 1. Sky dome (radius 72)
    add_sky_dome(sm_sky, radius=72.0, segs_u=32, segs_v=12)

    # 2. Grassy clearing ground: flat Y=0 inside r<=9.2, smooth rolling hills outside r>9.5
    def ground_h(x: float, z: float) -> float:
        r = math.hypot(x, z)
        if r <= 9.2:
            return 0.0
        t = _smoothstep(9.3, 38.0, r)
        # Higher scenic rolling ridges behind the enemy (Z < 0, X > -10)
        back_boost = 1.0 + 0.55 * _smoothstep(4.0, -18.0, z)
        undul = 0.55 + 0.45 * _organic_noise(x * 0.25, z * 0.25, phase=0.7)
        return t * t * 5.2 * back_boost * (0.65 + 0.55 * undul) + _smoothstep(9.5, 16.0, r) * 0.45 * undul

    def ground_col(x: float, z: float, r: float, y: float) -> Color4:
        # Organic clearing dirt center transitioning smoothly into lush vibrant grass
        n = _organic_noise(x, z, phase=1.2)
        n2 = _organic_noise(x * 1.9, z * 1.9, phase=3.1)
        # Slightly offset clearing center toward combat corridor between (-2.2, 2.8) and (2.1, -3.2)
        d_combat = math.hypot(x * 0.92, z * 0.88)
        eff_r = d_combat + n * 1.15 + n2 * 0.45

        c_dirt: Color4 = (0.93, 0.82, 0.58, 1.0)
        c_warm_grass: Color4 = (0.56, 0.86, 0.30, 1.0)
        c_lush_grass: Color4 = (0.38, 0.72, 0.26, 1.0)
        c_forest_floor: Color4 = (0.24, 0.50, 0.23, 1.0)

        t_grass = _smoothstep(3.8, 6.8, eff_r)
        col = _lerp4(c_dirt, c_warm_grass, t_grass)
        t_mid = _smoothstep(6.8, 13.5, eff_r)
        col = _lerp4(col, c_lush_grass, t_mid)
        t_outer = _smoothstep(14.5, 27.0, r)
        col = _lerp4(col, c_forest_floor, t_outer)

        # Subtle sunny variation patches on grass
        sun_patch = 0.94 + 0.10 * n2
        return (_clamp01(col[0] * sun_patch), _clamp01(col[1] * sun_patch), _clamp01(col[2] * sun_patch), 1.0)

    radii = [1.6, 3.2, 4.8, 6.4, 8.0, 9.2, 11.2, 13.8, 17.0, 21.0, 26.0, 32.0, 38.0, 44.0]
    add_radial_ground(sm_ground, radii, segs=40, height_fn=ground_h, color_fn=ground_col, uv_scale=0.18)

    # 3. Sculpted Earthen Cliffs & Grassy Embankments ringing the clearing (r = 10.8 .. 15.5)
    # Place hero backdrop cliffs prominently behind enemy (Z = -10..-15, X = -8..+18) + 360 deg wrap
    cliff_specs = [
        # Hero backdrop arc right inside home camera frustum (azimuth ~ -125 deg .. -15 deg)
        (-7.8, -11.4, 5.4, 4.2, 2.35),
        (-3.2, -12.6, 5.8, 4.4, 2.65),
        (1.8, -12.8, 6.2, 4.6, 2.75),
        (6.8, -11.6, 5.8, 4.4, 2.55),
        (11.2, -9.2, 5.6, 4.4, 2.40),
        (13.8, -4.8, 5.4, 4.2, 2.25),
        # Right & front-right wrap
        (14.2, 0.5, 5.2, 4.0, 2.05),
        (12.6, 6.0, 5.4, 4.2, 1.95),
        (8.6, 10.4, 5.2, 4.0, 1.85),
        (3.2, 12.6, 5.0, 3.8, 1.70),
        # Behind camera (pulled back to r ~ 13.8 so camera never clips!)
        (-3.2, 13.8, 5.4, 3.8, 1.65),
        (-9.4, 11.2, 5.4, 4.2, 1.85),
        # Left wrap back to hero backdrop
        (-13.2, 5.6, 5.4, 4.2, 2.05),
        (-13.8, -0.4, 5.6, 4.2, 2.20),
        (-11.8, -6.6, 5.6, 4.2, 2.30),
    ]
    cliff_tops = []
    for cx, cz, cw, cd, ch in cliff_specs:
        by = ground_h(cx, cz)
        yaw = math.atan2(-cz, cx) + rng.uniform(-0.25, 0.25)
        add_sculpted_cliff(
            sm_rock, sm_cap, cx, cz, by, cw, cd, ch, yaw, rng,
            rock_tint=(1.0, 0.96, 0.90, 1.0),
            cap_top_color=(0.48, 0.82, 0.28, 1.0),
            cap_lip_color=(0.28, 0.58, 0.22, 1.0),
            n_sides=8,
            cap_thickness=0.44,
        )
        cliff_tops.append((cx, cz, by + ch + 0.25, cw * 0.45))

    def surface_y_with_cliffs(x: float, z: float) -> float:
        y = ground_h(x, z)
        for cx, cz, ty, cr in cliff_tops:
            if math.hypot(x - cx, z - cz) < cr:
                y = max(y, ty)
        return y

    # 4. Multi-Tiered Stylized Pine Trees (42 trees: hero cliff-top pines + dense midground + distant ridge silhouettes)
    # Hero pines carefully composed in the home camera frustum (framing left, center-left, center-right, right behind enemy)
    hero_pines = [
        # (x, z, height, radius, tiers)
        (-7.4, -12.2, 8.6, 2.35, 5),
        (-2.2, -13.6, 9.8, 2.55, 5),
        (3.8, -13.8, 9.2, 2.45, 5),
        (8.6, -12.0, 8.8, 2.35, 5),
        (13.2, -8.8, 9.4, 2.45, 5),
        (15.2, -3.6, 8.4, 2.25, 5),
        # Second hero layer just behind cliffs for deep BDSP staggered skyline
        (-10.5, -17.5, 10.6, 2.70, 5),
        (-4.5, -19.2, 11.2, 2.80, 5),
        (1.6, -20.5, 10.4, 2.65, 5),
        (7.8, -18.8, 11.4, 2.85, 5),
        (14.5, -16.2, 10.2, 2.60, 5),
        (19.8, -11.5, 9.8, 2.55, 5),
    ]
    for px, pz, h, rad, tiers in hero_pines:
        py = surface_y_with_cliffs(px, pz)
        add_pine_tree(
            sm_bark, sm_pine, px, py, pz, h, rad, rng,
            tiers=tiers, lobes=6,
            tint_dark=(0.56, 0.76, 0.64, 1.0),
            tint_lit=(1.0, 1.0, 0.90, 1.0),
        )

    # Distant silhouette pines along the back ridges in camera frustum (depth haze layer!)
    distant_back = [
        (-11.0, -27.0, 11.2, 2.9), (-4.0, -29.5, 11.5, 3.0), (3.5, -31.0, 10.8, 2.8),
        (10.5, -28.5, 11.4, 2.9), (17.5, -24.5, 10.8, 2.8), (24.0, -19.5, 10.5, 2.7),
        (28.5, -13.0, 9.8, 2.6), (7.0, -35.5, 11.5, 3.0), (15.0, -33.0, 11.0, 2.9),
        (-8.5, -34.0, 10.6, 2.8),
    ]
    for px, pz, h, rad in distant_back:
        py = ground_h(px, pz)
        add_pine_tree(
            sm_bark, sm_pine, px, py, pz, h, rad, rng,
            tiers=4, lobes=5,
            tint_dark=(0.48, 0.68, 0.64, 1.0),
            tint_lit=(0.88, 0.96, 0.88, 1.0),
        )

    # 360-degree surrounding pine forest ring (20 additional trees so camera orbits show zero gaps!)
    for k in range(20):
        ang = (k / 20.0) * math.tau + rng.uniform(-0.12, 0.12)
        # Skip the dense hero sector slightly so we distribute evenly around the full circle
        r = rng.uniform(14.0, 28.0)
        px = r * math.cos(ang)
        pz = r * math.sin(ang)
        if _near_home_camera(px, pz, margin=5.5):
            r = max(r, 17.5)
            px = r * math.cos(ang)
            pz = r * math.sin(ang)
        py = surface_y_with_cliffs(px, pz)
        h = rng.uniform(6.0, 10.2)
        rad = h * rng.uniform(0.24, 0.28)
        add_pine_tree(
            sm_bark, sm_pine, px, py, pz, h, rad, rng,
            tiers=4, lobes=5,
            tint_dark=(0.52, 0.72, 0.60, 1.0),
            tint_lit=(0.98, 1.0, 0.88, 1.0),
        )

    # 5. Lush leafy bushes tucked along cliff bases (r = 9.8 .. 12.2, clear of home camera)
    bush_angles = [i * (math.tau / 22.0) + rng.uniform(-0.08, 0.08) for i in range(22)]
    for ang in bush_angles:
        r = rng.uniform(9.8, 11.4)
        bx = r * math.cos(ang)
        bz = r * math.sin(ang)
        if _near_home_camera(bx, bz, margin=3.8):
            continue
        by = ground_h(bx, bz)
        br = rng.uniform(0.85, 1.35)
        add_leafy_bush(
            sm_bush, bx, by - 0.06, bz, br, rng,
            c_bot=(0.36, 0.64, 0.36, 1.0),
            c_top=(0.88, 1.0, 0.56, 1.0),
            puffs=3,
        )

    # 6. Pebbles & small boulders around cliff edge
    for k in range(18):
        ang = rng.uniform(0.0, math.tau)
        r = rng.uniform(8.2, 11.2)
        rx = r * math.cos(ang)
        rz = r * math.sin(ang)
        if _near_home_camera(rx, rz, margin=2.8):
            continue
        ry = ground_h(rx, rz)
        s = rng.uniform(0.22, 0.55)
        add_icosphere_blob(
            sm_rock, rx, ry + s * 0.25, rz,
            s * 1.15, s * 0.68, s * 0.95, rng,
            c_bot=(0.58, 0.52, 0.45, 1.0),
            c_top=(0.94, 0.88, 0.78, 1.0),
            jitter=0.18, flatten_bottom=0.35,
        )

    # 7. Bright 3D grass tufts & tiny white/yellow wildflowers around clearing edge (r = 7.4..10.4)
    for k in range(56):
        ang = rng.uniform(0.0, math.tau)
        r = rng.uniform(7.2, 10.3)
        gx = r * math.cos(ang)
        gz = r * math.sin(ang)
        if _near_home_camera(gx, gz, margin=2.4):
            continue
        gy = ground_h(gx, gz)
        add_grass_tuft(
            sm_flora, gx, gy, gz,
            scale=rng.uniform(0.85, 1.35),
            rng=rng,
            c_root=(0.24, 0.56, 0.20, 1.0),
            c_tip=(0.64, 0.94, 0.34, 1.0),
            blades=4,
        )

    flower_palette: Tuple[Color4, ...] = (
        (1.0, 0.98, 0.92, 1.0),   # daisy white
        (1.0, 0.88, 0.26, 1.0),   # buttercup yellow
        (1.0, 0.76, 0.86, 1.0),   # soft wildflower pink
        (0.82, 0.90, 1.0, 1.0),   # forget-me-not blue
    )
    for k in range(30):
        ang = rng.uniform(0.0, math.tau)
        r = rng.uniform(7.5, 10.2)
        fx = r * math.cos(ang)
        fz = r * math.sin(ang)
        if _near_home_camera(fx, fz, margin=2.4):
            continue
        fy = ground_h(fx, fz)
        add_wildflower(sm_flora, fx, fy, fz, rng.uniform(0.85, 1.25), rng.choice(flower_palette), rng)

    return scene


def build_forest() -> ArenaScene:
    """SIM_BATTLE3D_BIOME_FOREST = 1: Eterna Forest dense canopy clearing, mossy boulders, tall pines & broadleaves."""
    rng = random.Random(205206)
    scene = ArenaScene("forest")

    tex_sky = scene.add_texture(
        256, 128,
        make_sky_dome_texture(
            256, 128, seed=201,
            zenith=(0.14, 0.34, 0.44),
            mid_sky=(0.30, 0.56, 0.58),
            horizon=(0.56, 0.74, 0.66),
            cloud_lit=(0.88, 0.96, 0.88),
            cloud_shade=(0.52, 0.68, 0.64),
            cloud_amount=0.45,
            sun_glow=(0.94, 1.0, 0.78),
        ),
        flags=0,
    )
    tex_ground = scene.add_texture(
        128, 128,
        make_painterly_ground_texture(
            128, seed=202,
            base_tint=(0.88, 0.92, 0.84),
            dark_tint=(0.64, 0.72, 0.62),
            speck_tint=(0.96, 0.98, 0.86),
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_rock = scene.add_texture(
        128, 128,
        make_rock_cliff_texture(
            128, seed=203,
            rock_light=(0.48, 0.54, 0.44),
            rock_mid=(0.34, 0.40, 0.34),
            rock_dark=(0.20, 0.25, 0.22),
            strata_freq=6,
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_foliage = scene.add_texture(
        128, 128,
        make_foliage_texture(
            128, seed=204,
            dark=(0.08, 0.26, 0.18),
            mid=(0.16, 0.44, 0.24),
            bright=(0.34, 0.68, 0.28),
            needle_style=False,
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_bark = scene.add_texture(
        64, 64,
        make_bark_texture(64, seed=205, dark=(0.22, 0.16, 0.12), light=(0.40, 0.30, 0.22)),
        flags=B3D_TEX_FLAG_REPEAT,
    )

    sm_sky = scene.add_submesh(tex_sky, SKY_FLAGS, roughness=1.0, fog_factor=0.0)
    sm_ground = scene.add_submesh(tex_ground, B3D_SUBMESH_RECEIVE_SHADOW, roughness=0.92, fog_factor=0.80)
    sm_rock = scene.add_submesh(tex_rock, CAST_RECV, roughness=0.90, fog_factor=0.90)
    sm_bark = scene.add_submesh(tex_bark, CAST_RECV, roughness=0.92, fog_factor=1.0)
    sm_leaf = scene.add_submesh(tex_foliage, CAST_RECV, roughness=0.80, fog_factor=1.0)
    sm_flora = scene.add_submesh(-1, B3D_SUBMESH_RECEIVE_SHADOW | B3D_SUBMESH_DOUBLE_SIDED, roughness=0.75, fog_factor=0.85)

    add_sky_dome(sm_sky, radius=72.0, segs_u=28, segs_v=10)

    def ground_h(x: float, z: float) -> float:
        r = math.hypot(x, z)
        if r <= 9.2:
            return 0.0
        t = _smoothstep(9.3, 36.0, r)
        u = 0.5 + 0.5 * _organic_noise(x * 0.28, z * 0.28, 2.3)
        return t * t * 3.8 * (0.6 + 0.6 * u)

    def ground_col(x: float, z: float, r: float, y: float) -> Color4:
        n = _organic_noise(x, z, 2.1)
        eff_r = r + n * 1.1
        c_center: Color4 = (0.48, 0.66, 0.32, 1.0)
        c_moss: Color4 = (0.24, 0.52, 0.24, 1.0)
        c_deep: Color4 = (0.14, 0.34, 0.18, 1.0)
        col = _lerp4(c_center, c_moss, _smoothstep(3.5, 9.0, eff_r))
        return _lerp4(col, c_deep, _smoothstep(10.0, 22.0, eff_r))

    add_radial_ground(
        sm_ground,
        [1.8, 3.6, 5.4, 7.2, 9.2, 11.5, 14.5, 18.5, 23.5, 30.0, 38.0],
        segs=36, height_fn=ground_h, color_fn=ground_col, uv_scale=0.20,
    )

    # Dense Eterna Forest mix of towering pines and broadleaf canopy trees
    for k in range(34):
        ang = (k / 34.0) * math.tau + rng.uniform(-0.08, 0.08)
        r = rng.uniform(11.2, 17.5) if (k % 2 == 0) else rng.uniform(18.0, 30.0)
        tx = r * math.cos(ang)
        tz = r * math.sin(ang)
        if _near_home_camera(tx, tz, margin=4.5):
            r = max(r, 15.0)
            tx, tz = r * math.cos(ang), r * math.sin(ang)
        ty = ground_h(tx, tz)
        if k % 3 == 0:
            add_broadleaf_tree(
                sm_bark, sm_leaf, tx, ty, tz,
                height=rng.uniform(7.5, 11.0),
                canopy_r=rng.uniform(2.8, 4.0),
                rng=rng,
                c_bot=(0.24, 0.48, 0.28, 1.0),
                c_top=(0.74, 0.96, 0.52, 1.0),
            )
        else:
            add_pine_tree(
                sm_bark, sm_leaf, tx, ty, tz,
                height=rng.uniform(8.0, 12.2),
                base_radius=rng.uniform(2.1, 2.9),
                rng=rng,
                tiers=5 if r < 18.0 else 4,
                lobes=6,
                tint_dark=(0.36, 0.60, 0.46, 1.0),
                tint_lit=(0.84, 0.98, 0.72, 1.0),
            )

    # Mossy boulders & thick forest ferns/bushes
    for k in range(16):
        ang = (k / 16.0) * math.tau + rng.uniform(-0.15, 0.15)
        r = rng.uniform(9.8, 13.5)
        bx, bz = r * math.cos(ang), r * math.sin(ang)
        if _near_home_camera(bx, bz, margin=3.6):
            continue
        by = ground_h(bx, bz)
        s = rng.uniform(0.75, 1.55)
        add_icosphere_blob(
            sm_rock, bx, by + s * 0.36, bz,
            s * 1.25, s * 0.78, s * 1.05, rng,
            c_bot=(0.45, 0.52, 0.44, 1.0),
            c_top=(0.56, 0.84, 0.46, 1.0),
            jitter=0.18, flatten_bottom=0.32,
        )

    for k in range(20):
        ang = (k / 20.0) * math.tau + rng.uniform(-0.1, 0.1)
        r = rng.uniform(9.5, 12.0)
        bx, bz = r * math.cos(ang), r * math.sin(ang)
        if _near_home_camera(bx, bz, margin=3.6):
            continue
        add_leafy_bush(
            sm_leaf, bx, ground_h(bx, bz) - 0.05, bz, rng.uniform(0.9, 1.45), rng,
            c_bot=(0.24, 0.50, 0.28, 1.0),
            c_top=(0.68, 0.94, 0.46, 1.0),
            puffs=3,
        )

    for k in range(52):
        ang = rng.uniform(0.0, math.tau)
        r = rng.uniform(6.8, 10.6)
        gx, gz = r * math.cos(ang), r * math.sin(ang)
        if _near_home_camera(gx, gz, margin=2.4):
            continue
        add_grass_tuft(
            sm_flora, gx, ground_h(gx, gz), gz, rng.uniform(0.95, 1.55), rng,
            c_root=(0.14, 0.40, 0.16, 1.0),
            c_tip=(0.46, 0.82, 0.30, 1.0),
            blades=4,
        )
    return scene


def build_water_lake() -> ArenaScene:
    """SIM_BATTLE3D_BIOME_WATER = 2: Lake Verity/Valor sandy shore clearing, shimmering water & pine island."""
    rng = random.Random(207208)
    scene = ArenaScene("water_lake")

    tex_sky = scene.add_texture(
        256, 128,
        make_sky_dome_texture(
            256, 128, seed=301,
            zenith=(0.14, 0.48, 0.92),
            mid_sky=(0.40, 0.78, 0.99),
            horizon=(0.82, 0.94, 1.0),
            cloud_amount=0.58,
            sun_dir_u=0.76,
        ),
        flags=0,
    )
    tex_ground = scene.add_texture(
        128, 128,
        make_painterly_ground_texture(
            128, seed=302,
            base_tint=(0.95, 0.93, 0.86),
            dark_tint=(0.78, 0.76, 0.68),
            speck_tint=(1.0, 0.98, 0.90),
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_water = scene.add_texture(128, 128, make_water_texture(128, seed=303), flags=B3D_TEX_FLAG_REPEAT)
    tex_rock = scene.add_texture(
        128, 128,
        make_rock_cliff_texture(
            128, seed=304,
            rock_light=(0.74, 0.66, 0.54),
            rock_mid=(0.56, 0.49, 0.40),
            rock_dark=(0.36, 0.32, 0.28),
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_pine = scene.add_texture(
        128, 128,
        make_foliage_texture(
            128, seed=305,
            dark=(0.12, 0.38, 0.28),
            mid=(0.24, 0.58, 0.36),
            bright=(0.46, 0.78, 0.40),
            needle_style=True,
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_bark = scene.add_texture(64, 64, make_bark_texture(64, seed=306), flags=B3D_TEX_FLAG_REPEAT)

    sm_sky = scene.add_submesh(tex_sky, SKY_FLAGS, roughness=1.0, fog_factor=0.0)
    sm_ground = scene.add_submesh(tex_ground, B3D_SUBMESH_RECEIVE_SHADOW, roughness=0.88, fog_factor=0.75)
    sm_water = scene.add_submesh(tex_water, B3D_SUBMESH_RECEIVE_SHADOW, roughness=0.22, fog_factor=0.70)
    sm_rock = scene.add_submesh(tex_rock, CAST_RECV, roughness=0.86, fog_factor=0.85)
    sm_cap = scene.add_submesh(tex_ground, CAST_RECV, roughness=0.84, fog_factor=0.85)
    sm_bark = scene.add_submesh(tex_bark, CAST_RECV, roughness=0.90, fog_factor=1.0)
    sm_pine = scene.add_submesh(tex_pine, CAST_RECV, roughness=0.78, fog_factor=1.0)

    add_sky_dome(sm_sky, radius=72.0, segs_u=30, segs_v=11)

    # Sandy shoreline clearing (flat Y=0 inside r<=9.2), sloping gently into lakebed behind enemy (z < -8)
    # and rising to grassy shore banks on front/left/right and far shore beyond r > 28
    def lake_basin_mask(x: float, z: float) -> float:
        # Broad calm lake stretching behind the enemy from z = -8.5 to z = -27
        lake_d = math.hypot((x - 4.0) * 0.75, (z + 18.0) * 1.05)
        return 1.0 - _smoothstep(8.0, 14.5, lake_d)

    def ground_h(x: float, z: float) -> float:
        r = math.hypot(x, z)
        if r <= 9.0:
            return 0.0
        basin = lake_basin_mask(x, z)
        # Lake Verity island centerpiece in the middle of the lake around (5.5, -21.5)
        isl_d = math.hypot(x - 5.5, z + 21.5)
        island = (1.0 - _smoothstep(3.2, 6.2, isl_d)) * 2.2
        far_shore = _smoothstep(24.0, 42.0, r) * 4.2
        near_bank = _smoothstep(9.5, 18.0, r) * (1.0 - basin) * 2.0
        undul = 0.7 + 0.3 * _organic_noise(x * 0.25, z * 0.25, 3.4)
        return max(-1.35, -1.35 * basin + island + (far_shore + near_bank) * undul)

    def ground_col(x: float, z: float, r: float, y: float) -> Color4:
        c_wet_sand: Color4 = (0.76, 0.68, 0.50, 1.0)
        c_sand: Color4 = (0.94, 0.87, 0.68, 1.0)
        c_grass: Color4 = (0.42, 0.76, 0.30, 1.0)
        if y < -0.15:
            return c_wet_sand
        t_g = _smoothstep(0.35, 1.25, y)
        return _lerp4(c_sand, c_grass, t_g)

    add_radial_ground(
        sm_ground,
        [1.8, 3.6, 5.6, 7.6, 9.2, 11.5, 14.5, 18.0, 22.0, 26.5, 32.0, 38.0, 44.0],
        segs=40, height_fn=ground_h, color_fn=ground_col, uv_scale=0.18,
    )

    # Shimmering cerulean water plane at Y = -0.18 spanning the lake basin
    def water_h(x: float, z: float) -> float:
        return -0.18

    def water_col(x: float, z: float, r: float, y: float) -> Color4:
        depth = _clamp01((-0.18 - ground_h(x, z)) / 1.1)
        return _lerp4((0.76, 0.96, 1.0, 0.92), (0.38, 0.72, 0.96, 0.98), depth)

    add_radial_ground(
        sm_water,
        [10.0, 13.0, 16.5, 20.5, 25.0, 30.0, 36.0],
        segs=32, height_fn=water_h, color_fn=water_col, uv_scale=0.22,
    )

    # Lake Verity island rocky bluff + hero pines right in the camera view!
    add_sculpted_cliff(
        sm_rock, sm_cap, 5.5, -21.5, -0.3, 8.2, 6.8, 2.2, 0.4, rng,
        cap_top_color=(0.44, 0.78, 0.30, 1.0),
        cap_lip_color=(0.28, 0.56, 0.24, 1.0),
    )
    for ix, iz, ih in [(3.8, -21.8, 7.6), (6.2, -22.2, 8.8), (7.4, -20.5, 6.8)]:
        add_pine_tree(sm_bark, sm_pine, ix, 2.1, iz, ih, ih * 0.26, rng, tiers=5, lobes=6)

    # Flanking lakeside cliffs & pine-lined distant shoreline (360 deg wrap)
    shore_cliffs = [
        (-11.5, -13.5, 5.8, 4.5, 2.3),
        (16.5, -11.5, 6.0, 4.5, 2.4),
        (16.0, 3.0, 5.6, 4.2, 2.0),
        (-14.5, 4.0, 5.6, 4.2, 2.0),
        (2.0, -33.0, 8.5, 5.5, 3.2),
        (13.0, -30.5, 8.0, 5.2, 3.0),
        (-9.0, -31.0, 8.0, 5.2, 2.9),
    ]
    for cx, cz, cw, cd, ch in shore_cliffs:
        add_sculpted_cliff(
            sm_rock, sm_cap, cx, cz, ground_h(cx, cz), cw, cd, ch, rng.uniform(0, math.tau), rng,
            cap_top_color=(0.44, 0.78, 0.30, 1.0),
            cap_lip_color=(0.28, 0.58, 0.24, 1.0),
        )

    for k in range(28):
        ang = (k / 28.0) * math.tau + rng.uniform(-0.08, 0.08)
        r = rng.uniform(28.0, 37.0) if (-2.4 < ang - math.tau < -0.3 or (ang > 3.6 and ang < 6.0)) else rng.uniform(14.5, 26.0)
        px, pz = r * math.cos(ang), r * math.sin(ang)
        if ground_h(px, pz) < 0.05 or _near_home_camera(px, pz, margin=5.0):
            continue
        add_pine_tree(
            sm_bark, sm_pine, px, ground_h(px, pz), pz,
            rng.uniform(6.8, 10.6), rng.uniform(1.8, 2.7), rng, tiers=4, lobes=5,
        )

    # Shore boulders & lakeside bushes
    for k in range(16):
        ang = rng.uniform(0.0, math.tau)
        r = rng.uniform(9.2, 12.4)
        rx, rz = r * math.cos(ang), r * math.sin(ang)
        if _near_home_camera(rx, rz, margin=3.4):
            continue
        ry = ground_h(rx, rz)
        if ry < -0.3:
            continue
        s = rng.uniform(0.45, 0.95)
        add_icosphere_blob(
            sm_rock, rx, ry + s * 0.28, rz, s * 1.2, s * 0.7, s, rng,
            c_bot=(0.56, 0.54, 0.50, 1.0), c_top=(0.88, 0.84, 0.76, 1.0),
            jitter=0.16, flatten_bottom=0.35,
        )

    return scene


def build_snow() -> ArenaScene:
    """SIM_BATTLE3D_BIOME_SNOW = 4: Snowpoint / Route 216 crisp snow clearing, icy cliffs & snow-dusted pines."""
    rng = random.Random(216217)
    scene = ArenaScene("snow")

    tex_sky = scene.add_texture(
        256, 128,
        make_sky_dome_texture(
            256, 128, seed=501,
            zenith=(0.34, 0.54, 0.78),
            mid_sky=(0.64, 0.78, 0.92),
            horizon=(0.88, 0.93, 0.98),
            cloud_lit=(0.98, 0.99, 1.0),
            cloud_shade=(0.76, 0.84, 0.93),
            cloud_amount=0.68,
            sun_glow=(1.0, 0.98, 0.94),
        ),
        flags=0,
    )
    tex_snow = scene.add_texture(
        128, 128,
        make_painterly_ground_texture(
            128, seed=502,
            base_tint=(0.96, 0.98, 1.0),
            dark_tint=(0.80, 0.86, 0.94),
            speck_tint=(1.0, 1.0, 1.0),
            brush_strength=0.85,
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_rock = scene.add_texture(
        128, 128,
        make_rock_cliff_texture(
            128, seed=503,
            rock_light=(0.62, 0.70, 0.82),
            rock_mid=(0.42, 0.50, 0.64),
            rock_dark=(0.24, 0.30, 0.42),
            strata_freq=7,
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_pine = scene.add_texture(
        128, 128,
        make_foliage_texture(
            128, seed=504,
            dark=(0.14, 0.32, 0.36),
            mid=(0.26, 0.48, 0.50),
            bright=(0.76, 0.88, 0.92),
            needle_style=True,
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_bark = scene.add_texture(64, 64, make_bark_texture(64, seed=505, dark=(0.24, 0.20, 0.20), light=(0.42, 0.36, 0.36)), flags=B3D_TEX_FLAG_REPEAT)

    sm_sky = scene.add_submesh(tex_sky, SKY_FLAGS, roughness=1.0, fog_factor=0.0)
    sm_ground = scene.add_submesh(tex_snow, B3D_SUBMESH_RECEIVE_SHADOW, roughness=0.72, fog_factor=0.80)
    sm_rock = scene.add_submesh(tex_rock, CAST_RECV, roughness=0.80, fog_factor=0.88)
    sm_cap = scene.add_submesh(tex_snow, CAST_RECV, roughness=0.70, fog_factor=0.88)
    sm_bark = scene.add_submesh(tex_bark, CAST_RECV, roughness=0.90, fog_factor=1.0)
    sm_pine = scene.add_submesh(tex_pine, CAST_RECV, roughness=0.72, fog_factor=1.0)

    add_sky_dome(sm_sky, radius=72.0, segs_u=30, segs_v=11)

    def ground_h(x: float, z: float) -> float:
        r = math.hypot(x, z)
        if r <= 9.2:
            return 0.0
        t = _smoothstep(9.3, 38.0, r)
        u = 0.55 + 0.45 * _organic_noise(x * 0.24, z * 0.24, 5.1)
        return t * t * 5.6 * (0.7 + 0.5 * u)

    def ground_col(x: float, z: float, r: float, y: float) -> Color4:
        n = _organic_noise(x * 0.8, z * 0.8, 5.2)
        c_center: Color4 = (0.94, 0.97, 1.0, 1.0)
        c_drift: Color4 = (0.84, 0.90, 0.98, 1.0)
        c_shadow: Color4 = (0.72, 0.82, 0.94, 1.0)
        col = _lerp4(c_center, c_drift, _smoothstep(4.5, 13.0, r + n))
        return _lerp4(col, c_shadow, _smoothstep(16.0, 32.0, r))

    add_radial_ground(
        sm_ground,
        [1.8, 3.6, 5.6, 7.6, 9.2, 11.5, 14.5, 18.5, 23.5, 30.0, 38.0, 44.0],
        segs=36, height_fn=ground_h, color_fn=ground_col, uv_scale=0.18,
    )

    # Icy blue cliffs with thick overhanging snowdrifts
    cliff_tops = []
    for k in range(14):
        ang = (k / 14.0) * math.tau
        r = 12.6 if (-2.4 < ang - math.tau < -0.2 or 3.6 < ang < 6.0) else 13.8
        cx, cz = r * math.cos(ang), r * math.sin(ang)
        if _near_home_camera(cx, cz, margin=4.5):
            r = 14.8
            cx, cz = r * math.cos(ang), r * math.sin(ang)
        by = ground_h(cx, cz)
        ch = rng.uniform(2.0, 3.1)
        add_sculpted_cliff(
            sm_rock, sm_cap, cx, cz, by, rng.uniform(5.0, 6.2), rng.uniform(4.0, 4.8), ch,
            ang + rng.uniform(-0.2, 0.2), rng,
            rock_tint=(0.92, 0.96, 1.0, 1.0),
            cap_top_color=(0.97, 0.99, 1.0, 1.0),
            cap_lip_color=(0.76, 0.86, 0.96, 1.0),
            n_sides=8,
            cap_thickness=0.52,
        )
        cliff_tops.append((cx, cz, by + ch + 0.3, 2.6))

    def surf_y(x: float, z: float) -> float:
        y = ground_h(x, z)
        for cx, cz, ty, cr in cliff_tops:
            if math.hypot(x - cx, z - cz) < cr:
                y = max(y, ty)
        return y

    # 34 snow-dusted pine trees
    for k in range(34):
        ang = (k / 34.0) * math.tau + rng.uniform(-0.08, 0.08)
        r = rng.uniform(12.2, 17.0) if (k % 2 == 0) else rng.uniform(19.0, 34.0)
        px, pz = r * math.cos(ang), r * math.sin(ang)
        if _near_home_camera(px, pz, margin=5.2):
            r = max(r, 17.0)
            px, pz = r * math.cos(ang), r * math.sin(ang)
        add_pine_tree(
            sm_bark, sm_pine, px, surf_y(px, pz), pz,
            rng.uniform(6.4, 11.2), rng.uniform(1.8, 2.7), rng,
            tiers=5 if r < 18.0 else 4, lobes=6,
            tint_dark=(0.46, 0.64, 0.72, 1.0),
            tint_lit=(0.94, 0.98, 1.0, 1.0),
            snow_dusted=True,
        )

    # Snow-capped boulders & drifts
    for k in range(18):
        ang = rng.uniform(0.0, math.tau)
        r = rng.uniform(9.4, 12.2)
        rx, rz = r * math.cos(ang), r * math.sin(ang)
        if _near_home_camera(rx, rz, margin=3.4):
            continue
        s = rng.uniform(0.55, 1.15)
        add_icosphere_blob(
            sm_rock, rx, ground_h(rx, rz) + s * 0.30, rz, s * 1.2, s * 0.72, s, rng,
            c_bot=(0.48, 0.58, 0.74, 1.0), c_top=(0.95, 0.98, 1.0, 1.0),
            jitter=0.16, flatten_bottom=0.35,
        )

    return scene

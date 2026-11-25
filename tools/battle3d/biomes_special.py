"""Special Sinnoh biome builders: mountain_cave, city, indoors_gym, distortion_world."""

from __future__ import annotations

import math
import random

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
    add_box,
    add_broadleaf_tree,
    add_crystal_spire,
    add_cylinder,
    add_floating_island,
    add_icosphere_blob,
    add_leafy_bush,
    add_pitched_house,
    add_radial_ground,
    add_sculpted_cliff,
    add_sky_dome,
)
from proc_textures import (
    make_bark_texture,
    make_crystal_texture,
    make_foliage_texture,
    make_gym_court_texture,
    make_painterly_ground_texture,
    make_plaza_stone_texture,
    make_rock_cliff_texture,
    make_sky_dome_texture,
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


def _near_home_camera(x: float, z: float, margin: float = 3.4) -> bool:
    if math.hypot(x - (-3.6), z - 8.4) < margin:
        return True
    if -6.0 < x < -0.5 and 4.0 < z < 11.2:
        return True
    return False


def build_mountain_cave() -> ArenaScene:
    """SIM_BATTLE3D_BIOME_CAVE = 3: Mt. Coronet / Oreburgh rocky cavern, stalagmites, glowing crystals & ceiling arch."""
    rng = random.Random(303304)
    scene = ArenaScene("mountain_cave")

    tex_dome = scene.add_texture(
        256, 128,
        make_sky_dome_texture(
            256, 128, seed=401,
            zenith=(0.06, 0.07, 0.11),
            mid_sky=(0.12, 0.13, 0.19),
            horizon=(0.20, 0.21, 0.28),
            cloud_lit=(0.26, 0.28, 0.38),
            cloud_shade=(0.10, 0.11, 0.16),
            cloud_amount=0.45,
            sun_glow=(0.30, 0.45, 0.65),
        ),
        flags=0,
    )
    tex_rock = scene.add_texture(
        128, 128,
        make_rock_cliff_texture(
            128, seed=402,
            rock_light=(0.50, 0.48, 0.54),
            rock_mid=(0.34, 0.33, 0.38),
            rock_dark=(0.18, 0.18, 0.22),
            strata_freq=9,
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_floor = scene.add_texture(
        128, 128,
        make_painterly_ground_texture(
            128, seed=403,
            base_tint=(0.74, 0.70, 0.68),
            dark_tint=(0.46, 0.44, 0.46),
            speck_tint=(0.88, 0.84, 0.80),
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_crystal = scene.add_texture(
        128, 128,
        make_crystal_texture(128, seed=404, core=(0.56, 0.94, 1.0), edge=(0.20, 0.48, 0.86)),
        flags=B3D_TEX_FLAG_REPEAT,
    )

    sm_dome = scene.add_submesh(tex_dome, SKY_FLAGS, roughness=1.0, fog_factor=0.0)
    sm_ground = scene.add_submesh(tex_floor, B3D_SUBMESH_RECEIVE_SHADOW, roughness=0.90, fog_factor=0.80)
    sm_rock = scene.add_submesh(tex_rock, CAST_RECV, roughness=0.88, fog_factor=0.90)
    sm_crystal = scene.add_submesh(tex_crystal, B3D_SUBMESH_UNLIT | B3D_SUBMESH_CAST_SHADOW, roughness=0.25, fog_factor=0.45)

    # Dark vaulted cavern ceiling dome
    add_sky_dome(sm_dome, radius=48.0, segs_u=28, segs_v=11)

    def ground_h(x: float, z: float) -> float:
        r = math.hypot(x, z)
        if r <= 9.2:
            return 0.0
        t = _smoothstep(9.3, 30.0, r)
        bump = 0.6 + 0.4 * math.sin(x * 0.32) * math.cos(z * 0.29)
        return t * t * 6.5 * bump

    def ground_col(x: float, z: float, r: float, y: float) -> Color4:
        c_center: Color4 = (0.76, 0.70, 0.62, 1.0)
        c_mid: Color4 = (0.50, 0.48, 0.54, 1.0)
        c_wall: Color4 = (0.28, 0.28, 0.34, 1.0)
        col = _lerp4(c_center, c_mid, _smoothstep(4.5, 11.0, r))
        return _lerp4(col, c_wall, _smoothstep(12.0, 24.0, r))

    add_radial_ground(
        sm_ground,
        [1.8, 3.6, 5.6, 7.6, 9.2, 11.5, 14.5, 18.5, 23.5, 30.0],
        segs=36, height_fn=ground_h, color_fn=ground_col, uv_scale=0.20,
    )

    # Dark slate cavern cliff walls ringing the arena
    for k in range(16):
        ang = (k / 16.0) * math.tau
        r = 13.8 + rng.uniform(-0.8, 1.6)
        cx, cz = r * math.cos(ang), r * math.sin(ang)
        if _near_home_camera(cx, cz, margin=4.5):
            r = 16.0
            cx, cz = r * math.cos(ang), r * math.sin(ang)
        ch = rng.uniform(4.8, 9.5)
        add_sculpted_cliff(
            sm_rock, sm_rock, cx, cz, ground_h(cx, cz) - 0.3,
            rng.uniform(5.2, 7.0), rng.uniform(4.5, 5.8), ch,
            ang + rng.uniform(-0.3, 0.3), rng,
            rock_tint=(0.86, 0.86, 0.94, 1.0),
            cap_top_color=(0.48, 0.48, 0.56, 1.0),
            cap_lip_color=(0.30, 0.30, 0.36, 1.0),
            n_sides=7, cap_thickness=0.6,
        )

    # Dramatic cavern ceiling rock arch ribs spanning behind enemy
    for k in range(7):
        t = k / 6.0
        ang = (t - 0.5) * 1.65
        ax = -2.0 + math.sin(ang) * 17.5
        az = -15.5 + math.cos(ang) * 3.0
        ay = 10.5 + math.cos(ang * 1.4) * 3.5
        add_icosphere_blob(
            sm_rock, ax, ay, az,
            4.8, 2.2, 3.8, rng,
            c_bot=(0.24, 0.25, 0.32, 1.0),
            c_top=(0.44, 0.45, 0.54, 1.0),
            jitter=0.20,
        )
        # Hanging stalactites from the arch
        add_crystal_spire(
            sm_rock, ax + rng.uniform(-1.5, 1.5), ay - 1.2, az + rng.uniform(-1.0, 1.0),
            rng.uniform(0.55, 0.95), rng.uniform(2.5, 4.8),
            rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2),
            (0.42, 0.43, 0.50, 1.0), (0.24, 0.25, 0.32, 1.0),
            sides=6, invert_y=True,
        )

    # Floor stalagmites & jagged rocks
    for k in range(24):
        ang = (k / 24.0) * math.tau + rng.uniform(-0.1, 0.1)
        r = rng.uniform(9.8, 18.5)
        sx, sz = r * math.cos(ang), r * math.sin(ang)
        if _near_home_camera(sx, sz, margin=3.6):
            continue
        add_crystal_spire(
            sm_rock, sx, ground_h(sx, sz) - 0.2, sz,
            rng.uniform(0.65, 1.35), rng.uniform(2.6, 6.4),
            rng.uniform(-0.35, 0.35), rng.uniform(-0.35, 0.35),
            (0.36, 0.36, 0.42, 1.0), (0.64, 0.64, 0.72, 1.0),
            sides=6, invert_y=False,
        )

    # Glowing cyan & amethyst crystal clusters illuminating the cavern
    crystal_spots = [
        (-5.8, -10.8), (0.8, -11.4), (7.6, -10.2), (11.8, -4.5),
        (-10.8, -4.2), (9.8, 6.2), (-9.6, 5.2), (4.2, -16.8), (-4.5, -17.0),
    ]
    for idx, (cx, cz) in enumerate(crystal_spots):
        cy = ground_h(cx, cz) - 0.15
        if idx % 3 == 0:
            c_base, c_tip = (0.48, 0.28, 0.84, 1.0), (0.88, 0.66, 1.0, 1.0)
        else:
            c_base, c_tip = (0.18, 0.56, 0.88, 1.0), (0.64, 0.98, 1.0, 1.0)
        for shard in range(4):
            sa = shard * 1.55 + rng.uniform(-0.3, 0.3)
            sh = rng.uniform(1.4, 3.2) if shard == 0 else rng.uniform(0.9, 2.2)
            sr = rng.uniform(0.24, 0.46)
            add_crystal_spire(
                sm_crystal,
                cx + math.cos(sa) * 0.45, cy, cz + math.sin(sa) * 0.45,
                sr, sh,
                math.cos(sa) * rng.uniform(0.2, 0.75),
                math.sin(sa) * rng.uniform(0.2, 0.75),
                c_base, c_tip, sides=5,
            )

    return scene


def build_city() -> ArenaScene:
    """SIM_BATTLE3D_BIOME_CITY = 5: Jubilife / Veilstone stone-paved plaza, hedges, lampposts & Sinnoh townhouses."""
    rng = random.Random(210211)
    scene = ArenaScene("city")

    tex_sky = scene.add_texture(
        256, 128,
        make_sky_dome_texture(
            256, 128, seed=601,
            zenith=(0.20, 0.54, 0.92),
            mid_sky=(0.48, 0.78, 0.98),
            horizon=(0.82, 0.92, 0.99),
            cloud_amount=0.52,
            sun_dir_u=0.80,
        ),
        flags=0,
    )
    tex_plaza = scene.add_texture(128, 128, make_plaza_stone_texture(128, seed=602, tiles=4), flags=B3D_TEX_FLAG_REPEAT)
    tex_wall = scene.add_texture(
        128, 128,
        make_plaza_stone_texture(
            128, seed=603,
            tile_a=(0.94, 0.91, 0.84),
            tile_b=(0.89, 0.86, 0.79),
            grout=(0.74, 0.70, 0.64),
            tiles=3,
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_leaf = scene.add_texture(
        128, 128,
        make_foliage_texture(
            128, seed=604,
            dark=(0.14, 0.38, 0.22),
            mid=(0.26, 0.58, 0.30),
            bright=(0.48, 0.80, 0.36),
            needle_style=False,
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_bark = scene.add_texture(64, 64, make_bark_texture(64, seed=605), flags=B3D_TEX_FLAG_REPEAT)

    sm_sky = scene.add_submesh(tex_sky, SKY_FLAGS, roughness=1.0, fog_factor=0.0)
    sm_ground = scene.add_submesh(tex_plaza, B3D_SUBMESH_RECEIVE_SHADOW, roughness=0.72, fog_factor=0.72)
    sm_wall = scene.add_submesh(tex_wall, CAST_RECV, roughness=0.78, fog_factor=0.85)
    sm_roof = scene.add_submesh(-1, CAST_RECV, roughness=0.68, fog_factor=0.88)
    sm_leaf = scene.add_submesh(tex_leaf, CAST_RECV, roughness=0.78, fog_factor=0.88)
    sm_bark = scene.add_submesh(tex_bark, CAST_RECV, roughness=0.90, fog_factor=0.90)
    sm_lamp = scene.add_submesh(-1, B3D_SUBMESH_UNLIT, roughness=0.20, fog_factor=0.35)

    add_sky_dome(sm_sky, radius=72.0, segs_u=30, segs_v=11)

    def flat_h(x: float, z: float) -> float:
        return 0.0

    def plaza_col(x: float, z: float, r: float, y: float) -> Color4:
        # Decorative cream center plaza -> cool slate sidewalk outer ring -> park grass beyond r=16
        c_center: Color4 = (0.98, 0.96, 0.90, 1.0)
        c_border: Color4 = (0.82, 0.85, 0.90, 1.0)
        c_outer: Color4 = (0.58, 0.74, 0.46, 1.0)
        if r < 11.5:
            return _lerp4(c_center, c_border, _smoothstep(7.2, 10.8, r))
        return _lerp4(c_border, c_outer, _smoothstep(14.0, 18.5, r))

    add_radial_ground(
        sm_ground,
        [2.0, 4.0, 6.0, 8.0, 10.0, 12.2, 15.0, 19.0, 25.0, 34.0, 44.0],
        segs=36, height_fn=flat_h, color_fn=plaza_col, uv_scale=0.25,
    )

    # Low stone plaza curb + decorative manicured hedges ringing r = 10.6..11.4
    for k in range(16):
        ang = (k / 16.0) * math.tau
        hx, hz = 11.2 * math.cos(ang), 11.2 * math.sin(ang)
        if _near_home_camera(hx, hz, margin=3.6):
            continue
        yaw = -ang + math.pi * 0.5
        # Low stone planter curb
        add_box(sm_wall, hx, 0.25, hz, 3.2, 0.50, 1.25, yaw=yaw, color=(0.86, 0.85, 0.82, 1.0))
        # Trimmed hedge block + leafy puffs on top
        add_box(sm_leaf, hx, 0.92, hz, 2.9, 0.92, 0.96, yaw=yaw, color=(0.66, 0.90, 0.54, 1.0))
        add_leafy_bush(sm_leaf, hx, 0.95, hz, 0.62, rng, c_bot=(0.45, 0.72, 0.42, 1.0), c_top=(0.86, 1.0, 0.60, 1.0), puffs=2)

    # Decorative Sinnoh lampposts with glowing globes around the plaza
    for k in range(8):
        ang = (k / 8.0) * math.tau + 0.20
        lx, lz = 10.2 * math.cos(ang), 10.2 * math.sin(ang)
        if _near_home_camera(lx, lz, margin=3.2):
            continue
        # Cast-iron dark slate post
        add_cylinder(sm_roof, lx, 0.0, lz, 0.22, 0.14, 0.55, segs=6, c_bot=(0.24, 0.28, 0.34, 1.0), c_top=(0.30, 0.34, 0.40, 1.0))
        add_cylinder(sm_roof, lx, 0.55, lz, 0.09, 0.07, 3.2, segs=6, c_bot=(0.26, 0.30, 0.36, 1.0), c_top=(0.34, 0.38, 0.44, 1.0))
        # Warm glowing lantern globe
        add_icosphere_blob(sm_lamp, lx, 3.92, lz, 0.26, 0.30, 0.26, rng, (1.0, 0.92, 0.68, 1.0), (1.0, 0.99, 0.90, 1.0), jitter=0.0)

    # Stylized Sinnoh townhouses with colorful pitched roofs ringing r = 18..28
    roof_colors = [
        (0.84, 0.28, 0.26, 1.0),  # Pokemon Center crimson
        (0.24, 0.46, 0.80, 1.0),  # Poke Mart blue
        (0.24, 0.62, 0.56, 1.0),  # Jubilife teal
        (0.76, 0.48, 0.26, 1.0),  # warm terracotta
    ]
    for k in range(12):
        ang = (k / 12.0) * math.tau + 0.15
        r = rng.uniform(18.5, 25.0)
        bx, bz = r * math.cos(ang), r * math.sin(ang)
        yaw = -ang + math.pi * 0.5 + rng.uniform(-0.18, 0.18)
        w = rng.uniform(5.2, 7.6)
        d = rng.uniform(4.2, 5.8)
        wh = rng.uniform(3.8, 6.2)
        rh = rng.uniform(1.8, 2.8)
        add_pitched_house(
            sm_wall, sm_roof, bx, 0.0, bz, w, d, wh, rh, yaw,
            wall_color=(0.95, 0.93, 0.88, 1.0),
            roof_color=roof_colors[k % len(roof_colors)],
        )

    # Ornamental town park trees between buildings
    for k in range(14):
        ang = (k / 14.0) * math.tau + 0.08
        r = rng.uniform(15.2, 22.0)
        tx, tz = r * math.cos(ang), r * math.sin(ang)
        if _near_home_camera(tx, tz, margin=5.0):
            continue
        add_broadleaf_tree(
            sm_bark, sm_leaf, tx, 0.0, tz,
            height=rng.uniform(5.8, 8.2), canopy_r=rng.uniform(2.0, 2.8), rng=rng,
            c_bot=(0.28, 0.54, 0.30, 1.0), c_top=(0.76, 0.96, 0.54, 1.0),
        )

    return scene


def build_indoors_gym() -> ArenaScene:
    """SIM_BATTLE3D_BIOME_INDOORS = 6: Sinnoh Gym / League stadium court, pillars, perimeter walls & overhead lights."""
    rng = random.Random(220221)
    scene = ArenaScene("indoors_gym")

    tex_dome = scene.add_texture(
        256, 128,
        make_sky_dome_texture(
            256, 128, seed=701,
            zenith=(0.12, 0.16, 0.26),
            mid_sky=(0.18, 0.24, 0.36),
            horizon=(0.28, 0.34, 0.46),
            cloud_lit=(0.32, 0.40, 0.56),
            cloud_shade=(0.16, 0.20, 0.30),
            cloud_amount=0.25,
            sun_glow=(0.65, 0.78, 0.98),
        ),
        flags=0,
    )
    tex_court = scene.add_texture(256, 256, make_gym_court_texture(256, seed=702), flags=0)
    tex_stone = scene.add_texture(
        128, 128,
        make_plaza_stone_texture(
            128, seed=703,
            tile_a=(0.82, 0.84, 0.88),
            tile_b=(0.74, 0.77, 0.82),
            grout=(0.52, 0.56, 0.64),
            tiles=4,
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )

    sm_dome = scene.add_submesh(tex_dome, SKY_FLAGS, roughness=1.0, fog_factor=0.0)
    sm_court = scene.add_submesh(tex_court, B3D_SUBMESH_RECEIVE_SHADOW, roughness=0.38, fog_factor=0.35)
    sm_arch = scene.add_submesh(tex_stone, CAST_RECV, roughness=0.55, fog_factor=0.55)
    sm_trim = scene.add_submesh(-1, CAST_RECV, roughness=0.45, fog_factor=0.55)
    sm_light = scene.add_submesh(-1, B3D_SUBMESH_UNLIT, roughness=0.10, fog_factor=0.15)

    add_sky_dome(sm_dome, radius=46.0, segs_u=28, segs_v=10)

    # Polished stone battle court mapped 1:1 to make_gym_court_texture across r = 0..14
    def flat_h(x: float, z: float) -> float:
        return 0.0

    def court_col(x: float, z: float, r: float, y: float) -> Color4:
        return (1.0, 1.0, 1.0, 1.0) if r <= 12.5 else (0.72, 0.76, 0.84, 1.0)

    add_radial_ground(
        sm_court,
        [1.5, 3.0, 4.5, 6.2, 8.0, 10.0, 12.5, 14.2],
        segs=36, height_fn=flat_h, color_fn=court_col, planar_uv_radius=13.5,
    )

    # Stadium perimeter wall & tiered spectator balcony (r = 14.2..20.5)
    wall_segs = 18
    for k in range(wall_segs):
        ang = (k / wall_segs) * math.tau
        wx, wz = 15.2 * math.cos(ang), 15.2 * math.sin(ang)
        yaw = -ang + math.pi * 0.5
        # Lower stadium wall with blue League accent band
        add_box(sm_arch, wx, 1.25, wz, 5.4, 2.5, 1.2, yaw=yaw, color=(0.84, 0.86, 0.90, 1.0))
        add_box(sm_trim, wx, 2.65, wz, 5.45, 0.35, 1.32, yaw=yaw, color=(0.24, 0.48, 0.84, 1.0))
        # Upper arena wall behind balcony
        ux, uz = 18.8 * math.cos(ang), 18.8 * math.sin(ang)
        add_box(sm_arch, ux, 5.5, uz, 6.8, 11.0, 1.4, yaw=yaw, color=(0.62, 0.66, 0.74, 1.0))
        # Crimson & gold Gym banners alternating around upper wall
        if k % 2 == 0:
            bx, bz = 17.9 * math.cos(ang), 17.9 * math.sin(ang)
            bcol: Color4 = (0.86, 0.24, 0.28, 1.0) if (k % 4 == 0) else (0.24, 0.50, 0.86, 1.0)
            add_box(sm_trim, bx, 6.2, bz, 1.8, 3.8, 0.2, yaw=yaw, color=bcol)

    # 12 Fluted Stadium Pillars around r = 13.8 (skipping directly behind home camera)
    for k in range(12):
        ang = (k / 12.0) * math.tau + 0.14
        px, pz = 13.8 * math.cos(ang), 13.8 * math.sin(ang)
        if _near_home_camera(px, pz, margin=3.6):
            continue
        # Pedestal base
        add_box(sm_arch, px, 0.45, pz, 1.5, 0.9, 1.5, yaw=-ang, color=(0.76, 0.78, 0.84, 1.0))
        # Pillar shaft
        add_cylinder(
            sm_arch, px, 0.9, pz, 0.52, 0.46, 9.6, segs=10,
            c_bot=(0.82, 0.84, 0.90, 1.0), c_top=(0.94, 0.96, 1.0, 1.0), cap_top=True,
        )
        # Gold capital ring
        add_box(sm_trim, px, 10.65, pz, 1.45, 0.42, 1.45, yaw=-ang, color=(0.90, 0.76, 0.36, 1.0))

    # Overhead stadium light ring & glowing light banks (Y = 10.8)
    ring_segs = 16
    for k in range(ring_segs):
        ang = (k / ring_segs) * math.tau
        rx, rz = 13.4 * math.cos(ang), 13.4 * math.sin(ang)
        yaw = -ang + math.pi * 0.5
        add_box(sm_trim, rx, 11.2, rz, 5.4, 0.65, 0.85, yaw=yaw, color=(0.24, 0.28, 0.36, 1.0))
        if k % 2 == 0:
            lx, lz = 12.6 * math.cos(ang), 12.6 * math.sin(ang)
            add_box(sm_light, lx, 10.75, lz, 2.2, 0.30, 0.65, yaw=yaw, color=(0.96, 0.98, 1.0, 1.0))

    return scene


def build_distortion_world() -> ArenaScene:
    """SIM_BATTLE3D_BIOME_DISTORTION = 7: Floating fractured islands, inverted crystal spires & cosmic nebula sky."""
    rng = random.Random(487487)
    scene = ArenaScene("distortion_world")

    tex_sky = scene.add_texture(
        256, 128,
        make_sky_dome_texture(
            256, 128, seed=801,
            zenith=(0.06, 0.03, 0.16),
            mid_sky=(0.16, 0.08, 0.34),
            horizon=(0.28, 0.14, 0.48),
            cloud_lit=(0.74, 0.36, 0.92),
            cloud_shade=(0.18, 0.12, 0.40),
            cloud_amount=0.80,
            sun_glow=(0.50, 0.86, 0.96),
            nebula_mode=True,
        ),
        flags=0,
    )
    tex_stone = scene.add_texture(
        128, 128,
        make_rock_cliff_texture(
            128, seed=802,
            rock_light=(0.48, 0.42, 0.60),
            rock_mid=(0.30, 0.25, 0.42),
            rock_dark=(0.14, 0.11, 0.22),
            strata_freq=8,
        ),
        flags=B3D_TEX_FLAG_REPEAT,
    )
    tex_crystal = scene.add_texture(
        128, 128,
        make_crystal_texture(128, seed=803, core=(0.92, 0.44, 0.98), edge=(0.28, 0.18, 0.68)),
        flags=B3D_TEX_FLAG_REPEAT,
    )

    sm_sky = scene.add_submesh(tex_sky, SKY_FLAGS, roughness=1.0, fog_factor=0.0)
    sm_ground = scene.add_submesh(tex_stone, B3D_SUBMESH_RECEIVE_SHADOW, roughness=0.80, fog_factor=0.65)
    sm_rock = scene.add_submesh(tex_stone, CAST_RECV, roughness=0.82, fog_factor=0.75)
    sm_crystal = scene.add_submesh(tex_crystal, B3D_SUBMESH_UNLIT | B3D_SUBMESH_CAST_SHADOW, roughness=0.22, fog_factor=0.45)

    # Full-sphere-like cosmic nebula sky dome (extends deep below the floating island!)
    add_sky_dome(sm_sky, radius=72.0, segs_u=32, segs_v=14, elev_min=-0.95)

    # Main fractured floating stone island clearing (flat Y=0 inside r <= 9.2, sharp fractured drop outside)
    def main_h(x: float, z: float) -> float:
        r = math.hypot(x, z)
        if r <= 9.2:
            return 0.0
        # Craggy drop-off down to an underside spire tip
        ang = math.atan2(z, x)
        edge = 9.5 + 0.9 * math.sin(ang * 5.0) + 0.5 * math.cos(ang * 9.0)
        if r <= edge:
            return 0.0
        return -_smoothstep(edge, edge + 2.4, r) * 3.8

    def main_col(x: float, z: float, r: float, y: float) -> Color4:
        c_top: Color4 = (0.76, 0.72, 0.88, 1.0)
        c_edge: Color4 = (0.48, 0.36, 0.66, 1.0)
        c_under: Color4 = (0.22, 0.16, 0.34, 1.0)
        if y < -0.2:
            return c_under
        return _lerp4(c_top, c_edge, _smoothstep(6.2, 9.6, r))

    add_radial_ground(
        sm_ground,
        [1.8, 3.6, 5.6, 7.6, 9.2, 10.2, 11.4, 12.2],
        segs=32, height_fn=main_h, color_fn=main_col, uv_scale=0.20,
    )

    # Floating fractured rock islands hovering at impossible heights & angles all around the clearing
    island_specs = [
        # (x, top_y, z, radius, depth)
        (-7.5, 1.4, -14.5, 3.6, 6.2),
        (2.4, 2.2, -16.8, 4.4, 7.5),
        (11.5, 0.8, -13.2, 3.8, 6.0),
        (16.2, 3.5, -5.5, 3.5, 6.4),
        (-14.5, 2.8, -5.0, 3.8, 6.8),
        (14.0, -1.2, 7.5, 3.4, 5.4),
        (-13.2, 0.6, 8.2, 3.2, 5.2),
        (1.5, 4.8, -26.5, 5.2, 9.0),
        (13.5, 5.6, -24.0, 4.6, 8.2),
        (-11.0, 4.4, -24.5, 4.5, 8.0),
        (6.0, -3.5, -12.5, 2.6, 4.4),
        (-3.0, 6.2, -18.5, 2.8, 4.8),
    ]
    for ix, iy, iz, irad, idep in island_specs:
        add_floating_island(
            sm_rock, sm_rock, ix, iy, iz, irad, idep, rng,
            top_color=(0.74, 0.68, 0.88, 1.0),
            rock_color=(0.44, 0.36, 0.60, 1.0),
            sides=8,
        )
        # Crown each floating island with a glowing crystal spire OR inverted ruined stone pillar!
        if rng.random() < 0.65:
            add_crystal_spire(
                sm_crystal, ix, iy - 0.1, iz,
                rng.uniform(0.55, 1.05), rng.uniform(3.2, 6.8),
                rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8),
                (0.46, 0.24, 0.86, 1.0), (0.98, 0.64, 1.0, 1.0),
                sides=5, invert_y=False,
            )
        else:
            # Inverted pillar hanging underneath the floating island
            add_box(sm_rock, ix, iy + 2.4, iz, 1.1, 4.8, 1.1, yaw=rng.uniform(0, 1.5), color=(0.60, 0.54, 0.76, 1.0))

    # Dramatic floating inverted crystal spires & broken pillars framing the backdrop
    for k in range(18):
        ang = (k / 18.0) * math.tau + rng.uniform(-0.1, 0.1)
        r = rng.uniform(13.0, 32.0)
        sx, sz = r * math.cos(ang), r * math.sin(ang)
        if _near_home_camera(sx, sz, margin=4.5):
            continue
        sy = rng.uniform(2.5, 10.5)
        inv = (k % 2 == 0)
        c_base: Color4 = (0.24, 0.72, 0.94, 1.0) if (k % 3 == 0) else (0.58, 0.24, 0.88, 1.0)
        c_tip: Color4 = (0.74, 0.98, 1.0, 1.0) if (k % 3 == 0) else (1.0, 0.66, 0.98, 1.0)
        add_crystal_spire(
            sm_crystal, sx, sy, sz,
            rng.uniform(0.45, 1.15), rng.uniform(3.0, 7.8),
            rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9),
            c_base, c_tip, sides=5, invert_y=inv,
        )

    # Ring of floating fractured stone shards around the main island perimeter
    for k in range(16):
        ang = (k / 16.0) * math.tau + 0.12
        r = rng.uniform(10.6, 13.0)
        fx, fz = r * math.cos(ang), r * math.sin(ang)
        if _near_home_camera(fx, fz, margin=3.2):
            continue
        add_box(
            sm_rock, fx, rng.uniform(-0.8, 1.4), fz,
            rng.uniform(0.7, 1.6), rng.uniform(0.5, 1.2), rng.uniform(0.7, 1.6),
            yaw=rng.uniform(0.0, math.tau),
            color=(0.56, 0.48, 0.74, 1.0),
        )

    return scene

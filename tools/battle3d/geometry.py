"""Reusable clean-room BDSP-style 3D geometry builders (RH: X right, Y up, Z toward camera)."""

from __future__ import annotations

import math
import random
from typing import Callable, List, Sequence, Tuple

from b3d_io import SubmeshBuilder, v3_norm

Color4 = Tuple[float, float, float, float]
Vec3 = Tuple[float, float, float]


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp4(a: Color4, b: Color4, t: float) -> Color4:
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
        a[3] + (b[3] - a[3]) * t,
    )


def _mul_color(c: Color4, s: float) -> Color4:
    return (_clamp01(c[0] * s), _clamp01(c[1] * s), _clamp01(c[2] * s), c[3])


def _rot_y(x: float, z: float, angle: float) -> Tuple[float, float]:
    ca = math.cos(angle)
    sa = math.sin(angle)
    return (x * ca + z * sa, -x * sa + z * ca)


def add_sky_dome(
    sm: SubmeshBuilder,
    radius: float = 72.0,
    segs_u: int = 32,
    segs_v: int = 12,
    elev_min: float = -0.14,
    tint: Color4 = (1.0, 1.0, 1.0, 1.0),
) -> None:
    """Hemisphere sky dome extending slightly below Y=0; inward normals & CCW inward winding."""
    elev_max = math.pi * 0.498
    grid: List[List[int]] = []
    for iv in range(segs_v + 1):
        t = iv / segs_v  # 0 = zenith, 1 = bottom skirt
        elev = _lerp(elev_max, elev_min, t)
        # Map horizon (elev=0) to v=0.985, zenith to v=0.0, below horizon clamped near 0.995
        if elev >= 0.0:
            v_uv = (1.0 - elev / elev_max) * 0.985
        else:
            v_uv = 0.995
        cy = math.sin(elev)
        cr = math.cos(elev)
        row: List[int] = []
        for iu in range(segs_u + 1):
            u = iu / segs_u
            theta = u * math.tau
            x = cr * math.cos(theta)
            z = cr * math.sin(theta)
            pos = (x * radius, cy * radius, z * radius)
            inward_n = (-x, -cy, -z)
            row.append(sm.add_vertex(pos, inward_n, (u, v_uv), tint))
        grid.append(row)

    for iv in range(segs_v):
        for iu in range(segs_u):
            a = grid[iv][iu]
            b = grid[iv][iu + 1]
            c = grid[iv + 1][iu + 1]
            d = grid[iv + 1][iu]
            sm.add_quad(a, b, c, d, enforce_winding=True)


def add_radial_ground(
    sm: SubmeshBuilder,
    radii: Sequence[float],
    segs: int,
    height_fn: Callable[[float, float], float],
    color_fn: Callable[[float, float, float, float], Color4],
    uv_scale: float = 0.18,
    planar_uv_radius: float | None = None,
) -> None:
    """Smooth radial terrain mesh with finite-difference normals and zero center UV pinch."""
    eps = 0.25

    def eval_v(x: float, z: float) -> Tuple[Vec3, Vec3, Tuple[float, float], Color4]:
        y = height_fn(x, z)
        r = math.hypot(x, z)
        hx = (height_fn(x + eps, z) - height_fn(x - eps, z)) / (2.0 * eps)
        hz = (height_fn(x, z + eps) - height_fn(x, z - eps)) / (2.0 * eps)
        n = v3_norm((-hx, 1.0, -hz))
        if planar_uv_radius is not None:
            u = (x / (2.0 * planar_uv_radius)) + 0.5
            v = (z / (2.0 * planar_uv_radius)) + 0.5
        else:
            u = x * uv_scale
            v = z * uv_scale
        return (x, y, z), n, (u, v), color_fn(x, z, r, y)

    p0, n0, uv0, c0 = eval_v(0.0, 0.0)
    center_idx = sm.add_vertex(p0, n0, uv0, c0)

    rings: List[List[int]] = []
    for r in radii:
        ring: List[int] = []
        for s in range(segs):
            ang = (s / segs) * math.tau
            x = r * math.cos(ang)
            z = r * math.sin(ang)
            p, n, uv, c = eval_v(x, z)
            ring.append(sm.add_vertex(p, n, uv, c))
        rings.append(ring)

    # Center fan
    first_ring = rings[0]
    for s in range(segs):
        s_next = (s + 1) % segs
        sm.add_tri(center_idx, first_ring[s_next], first_ring[s], enforce_winding=True)

    # Concentric quads
    for ri in range(len(rings) - 1):
        r0 = rings[ri]
        r1 = rings[ri + 1]
        for s in range(segs):
            s_next = (s + 1) % segs
            sm.add_quad(r0[s], r0[s_next], r1[s_next], r1[s], enforce_winding=True)


def add_sculpted_cliff(
    rock_sm: SubmeshBuilder,
    cap_sm: SubmeshBuilder,
    cx: float,
    cz: float,
    base_y: float,
    width: float,
    depth: float,
    height: float,
    yaw: float,
    rng: random.Random,
    rock_tint: Color4 = (1.0, 1.0, 1.0, 1.0),
    cap_top_color: Color4 = (0.48, 0.80, 0.30, 1.0),
    cap_lip_color: Color4 = (0.30, 0.58, 0.22, 1.0),
    n_sides: int = 9,
    cap_thickness: float = 0.42,
) -> None:
    """Faceted BDSP rocky embankment with thick overhanging grass/snow cap."""
    # Generate organic irregular polygon profile in local XZ
    pts_local: List[Tuple[float, float]] = []
    for i in range(n_sides):
        ang = (i / n_sides) * math.tau
        rad_jit = rng.uniform(0.84, 1.14)
        lx = math.cos(ang) * (width * 0.5) * rad_jit
        lz = math.sin(ang) * (depth * 0.5) * rad_jit
        pts_local.append((lx, lz))

    y_bot = base_y - 0.85
    y_mid = base_y + height * 0.52
    y_top = base_y + height

    # Build 2 vertical rock bands (slight organic crag step halfway up)
    ring_bot: List[Vec3] = []
    ring_mid: List[Vec3] = []
    ring_top: List[Vec3] = []
    for lx, lz in pts_local:
        bx, bz = _rot_y(lx * 1.06, lz * 1.06, yaw)
        mx, mz = _rot_y(lx * rng.uniform(0.92, 1.02), lz * rng.uniform(0.92, 1.02), yaw)
        tx, tz = _rot_y(lx * 0.86, lz * 0.86, yaw)
        ring_bot.append((cx + bx, y_bot, cz + bz))
        ring_mid.append((cx + mx, y_mid + rng.uniform(-0.14, 0.14), cz + mz))
        ring_top.append((cx + tx, y_top + rng.uniform(-0.10, 0.10), cz + tz))

    c_bot = _mul_color(rock_tint, 0.68)
    c_mid = _mul_color(rock_tint, 0.92)
    c_top = _mul_color(rock_tint, 1.0)

    # Faceted rock sides
    u_acc = 0.0
    for i in range(n_sides):
        j = (i + 1) % n_sides
        p0, p1 = ring_bot[i], ring_bot[j]
        p2, p3 = ring_mid[j], ring_mid[i]
        p4, p5 = ring_top[j], ring_top[i]
        seg_len = math.hypot(p1[0] - p0[0], p1[2] - p0[2])
        u0 = u_acc * 0.28
        u1 = (u_acc + seg_len) * 0.28
        u_acc += seg_len
        mx = (p0[0] + p1[0]) * 0.5 - cx
        mz = (p0[2] + p1[2]) * 0.5 - cz
        out_hint = (mx, 0.15, mz)
        rock_sm.add_flat_quad(
            p0, p1, p2, p3,
            (u0, 0.0), (u1, 0.0), (u1, height * 0.22), (u0, height * 0.22),
            c_bot, c_bot, c_mid, c_mid,
            outward_hint=out_hint,
        )
        rock_sm.add_flat_quad(
            p3, p2, p4, p5,
            (u0, height * 0.22), (u1, height * 0.22), (u1, height * 0.44), (u0, height * 0.44),
            c_mid, c_mid, c_top, c_top,
            outward_hint=out_hint,
        )

    # Thick overhanging grass/snow cap (lip underside -> beveled edge -> domed crown)
    cap_outer: List[Vec3] = []
    cap_bevel: List[Vec3] = []
    cap_under: List[Vec3] = []
    for i, (lx, lz) in enumerate(pts_local):
        top_y_i = ring_top[i][1]
        ox, oz = _rot_y(lx * 0.98, lz * 0.98, yaw)
        bx, bz = _rot_y(lx * 0.88, lz * 0.88, yaw)
        ux, uz = _rot_y(lx * 0.84, lz * 0.84, yaw)
        cap_under.append((cx + ux, top_y_i - cap_thickness * 0.35, cz + uz))
        cap_outer.append((cx + ox, top_y_i + cap_thickness * 0.15, cz + oz))
        cap_bevel.append((cx + bx, top_y_i + cap_thickness * 0.72, cz + bz))

    crown_pos = (cx, y_top + cap_thickness * 1.02, cz)
    c_under = _mul_color(cap_lip_color, 0.72)
    c_crown = _mul_color(cap_top_color, 1.06)

    for i in range(n_sides):
        j = (i + 1) % n_sides
        out_x = (cap_outer[i][0] + cap_outer[j][0]) * 0.5 - cx
        out_z = (cap_outer[i][2] + cap_outer[j][2]) * 0.5 - cz
        # Underside overhang lip
        cap_sm.add_flat_quad(
            cap_under[i], cap_under[j], cap_outer[j], cap_outer[i],
            (cap_under[i][0] * 0.2, cap_under[i][2] * 0.2),
            (cap_under[j][0] * 0.2, cap_under[j][2] * 0.2),
            (cap_outer[j][0] * 0.2, cap_outer[j][2] * 0.2),
            (cap_outer[i][0] * 0.2, cap_outer[i][2] * 0.2),
            c_under, c_under, cap_lip_color, cap_lip_color,
            outward_hint=(out_x, -0.35, out_z),
        )
        # Beveled upper turf edge
        cap_sm.add_flat_quad(
            cap_outer[i], cap_outer[j], cap_bevel[j], cap_bevel[i],
            (cap_outer[i][0] * 0.2, cap_outer[i][2] * 0.2),
            (cap_outer[j][0] * 0.2, cap_outer[j][2] * 0.2),
            (cap_bevel[j][0] * 0.2, cap_bevel[j][2] * 0.2),
            (cap_bevel[i][0] * 0.2, cap_bevel[i][2] * 0.2),
            cap_lip_color, cap_lip_color, cap_top_color, cap_top_color,
            outward_hint=(out_x, 0.65, out_z),
        )
        # Top cap dome fan
        cap_sm.add_flat_tri(
            cap_bevel[i], cap_bevel[j], crown_pos,
            (cap_bevel[i][0] * 0.2, cap_bevel[i][2] * 0.2),
            (cap_bevel[j][0] * 0.2, cap_bevel[j][2] * 0.2),
            (crown_pos[0] * 0.2, crown_pos[2] * 0.2),
            cap_top_color, cap_top_color, c_crown,
            outward_hint=(0.0, 1.0, 0.0),
        )


def add_cylinder(
    sm: SubmeshBuilder,
    x: float,
    y0: float,
    z: float,
    r0: float,
    r1: float,
    height: float,
    segs: int = 8,
    c_bot: Color4 = (0.8, 0.8, 0.8, 1.0),
    c_top: Color4 = (1.0, 1.0, 1.0, 1.0),
    cap_top: bool = False,
    cap_bot: bool = False,
    tilt_x: float = 0.0,
    tilt_z: float = 0.0,
) -> None:
    """Tapered cylinder with smooth side normals and optional end caps."""
    bot_ring: List[int] = []
    top_ring: List[int] = []
    y1 = y0 + height
    slope_y = (r0 - r1) / max(0.01, height)
    for i in range(segs + 1):
        u = i / segs
        ang = u * math.tau
        ca = math.cos(ang)
        sa = math.sin(ang)
        n = v3_norm((ca, slope_y, sa))
        bot_ring.append(sm.add_vertex((x + ca * r0, y0, z + sa * r0), n, (u, 0.0), c_bot))
        top_ring.append(
            sm.add_vertex((x + tilt_x + ca * r1, y1, z + tilt_z + sa * r1), n, (u, height * 0.35), c_top)
        )

    for i in range(segs):
        sm.add_quad(bot_ring[i], bot_ring[i + 1], top_ring[i + 1], top_ring[i], enforce_winding=True)

    if cap_top and r1 > 1e-4:
        ci = sm.add_vertex((x + tilt_x, y1, z + tilt_z), (0.0, 1.0, 0.0), (0.5, 0.5), c_top)
        ring = []
        for i in range(segs):
            ang = (i / segs) * math.tau
            ca, sa = math.cos(ang), math.sin(ang)
            ring.append(
                sm.add_vertex(
                    (x + tilt_x + ca * r1, y1, z + tilt_z + sa * r1),
                    (0.0, 1.0, 0.0),
                    (0.5 + 0.5 * ca, 0.5 + 0.5 * sa),
                    c_top,
                )
            )
        for i in range(segs):
            sm.add_tri(ci, ring[(i + 1) % segs], ring[i], enforce_winding=True)

    if cap_bot and r0 > 1e-4:
        ci = sm.add_vertex((x, y0, z), (0.0, -1.0, 0.0), (0.5, 0.5), c_bot)
        ring = []
        for i in range(segs):
            ang = (i / segs) * math.tau
            ca, sa = math.cos(ang), math.sin(ang)
            ring.append(
                sm.add_vertex(
                    (x + ca * r0, y0, z + sa * r0),
                    (0.0, -1.0, 0.0),
                    (0.5 + 0.5 * ca, 0.5 + 0.5 * sa),
                    c_bot,
                )
            )
        for i in range(segs):
            sm.add_tri(ci, ring[i], ring[(i + 1) % segs], enforce_winding=True)


def add_pine_tree(
    bark_sm: SubmeshBuilder,
    pine_sm: SubmeshBuilder,
    x: float,
    y: float,
    z: float,
    height: float,
    base_radius: float,
    rng: random.Random,
    tiers: int = 5,
    lobes: int = 8,
    tint_dark: Color4 = (0.48, 0.66, 0.58, 1.0),
    tint_lit: Color4 = (0.98, 1.0, 0.90, 1.0),
    snow_dusted: bool = False,
    curved: bool = True,
) -> None:
    """Stylized BDSP multi-tiered conifer with curved drooping boughs and AO shading."""
    lean_x = rng.uniform(-0.18, 0.18)
    lean_z = rng.uniform(-0.18, 0.18)

    # Tapered trunk embedded slightly below y
    trunk_h = height * 0.62
    trunk_r0 = base_radius * 0.19
    trunk_r1 = base_radius * 0.06
    add_cylinder(
        bark_sm,
        x, y - 0.35, z,
        trunk_r0, trunk_r1, trunk_h + 0.35,
        segs=6,
        c_bot=(0.76, 0.72, 0.68, 1.0),
        c_top=(0.54, 0.50, 0.48, 1.0),
        tilt_x=lean_x * 0.55,
        tilt_z=lean_z * 0.55,
    )

    n_pts = lobes * 2  # alternating outer branch tips & inner valleys
    bough_start = height * 0.16
    bough_span = height - bough_start
    phase_base = rng.uniform(0.0, math.tau)

    for t in range(tiers):
        frac0 = t / tiers
        frac1 = (t + 1) / tiers
        # Overlapping tiers: each tier reaches down past previous tier's base
        ty_bot = y + bough_start + bough_span * (frac0 * 0.76)
        ty_top = y + bough_start + bough_span * (min(1.0, frac0 * 0.76 + (1.0 / tiers) * 1.52))
        if t == tiers - 1:
            ty_top = y + height
        tr_out = base_radius * ((1.0 - frac0 * 0.76) * rng.uniform(0.94, 1.06))
        tr_in = tr_out * 0.74
        # Slight horizontal lean along trunk
        ox_bot = x + lean_x * (ty_bot - y) / height
        oz_bot = z + lean_z * (ty_bot - y) / height
        ox_top = x + lean_x * (ty_top - y) / height
        oz_top = z + lean_z * (ty_top - y) / height

        # Vertical AO gradient: lower tiers darker, sunlit tips brighter
        tier_shade = 0.72 + 0.28 * frac1
        c_rim_out = _lerp4(tint_dark, tint_lit, 0.44 + 0.38 * frac1)
        c_rim_in = _mul_color(_lerp4(tint_dark, tint_lit, 0.22 + 0.25 * frac1), 0.76)
        c_mid_out = _lerp4(tint_dark, tint_lit, 0.56 + 0.32 * frac1)
        c_apex = _lerp4(tint_dark, tint_lit, 0.74 + 0.26 * frac1)
        if snow_dusted:
            c_apex = _lerp4(c_apex, (0.96, 0.98, 1.0, 1.0), 0.65 + 0.25 * frac1)
            c_mid_out = _lerp4(c_mid_out, (0.92, 0.96, 1.0, 1.0), 0.45 + 0.25 * frac1)
            c_rim_out = _lerp4(c_rim_out, (0.90, 0.95, 1.0, 1.0), 0.35 + 0.25 * frac1)
        c_under = _mul_color(tint_dark, 0.54 * tier_shade)

        apex_idx = pine_sm.add_vertex((ox_top, ty_top, oz_top), (0.0, 1.0, 0.0), (0.5, 0.0), c_apex)
        under_center_idx = pine_sm.add_vertex(
            (ox_bot, ty_bot + (ty_top - ty_bot) * 0.16, oz_bot),
            (0.0, -1.0, 0.0),
            (0.5, 1.0),
            c_under,
        )

        phase = phase_base + t * (math.pi / lobes) + rng.uniform(-0.16, 0.16)
        mid_ids: List[int] = []
        rim_top_ids: List[int] = []
        rim_und_ids: List[int] = []
        slope_h = max(0.2, ty_top - ty_bot)
        ox_mid = _lerp(ox_top, ox_bot, 0.48)
        oz_mid = _lerp(oz_top, oz_bot, 0.48)
        ty_mid = _lerp(ty_top, ty_bot, 0.46)

        for i in range(n_pts):
            ang = phase + (i / n_pts) * math.tau
            is_lobe = (i % 2 == 0)
            rad = (tr_out if is_lobe else tr_in) * rng.uniform(0.95, 1.05)
            droop = -0.20 * slope_h if is_lobe else 0.04 * slope_h
            ca = math.cos(ang)
            sa = math.sin(ang)
            px = ox_bot + ca * rad
            pz = oz_bot + sa * rad
            py = ty_bot + droop
            n_out = v3_norm((ca * slope_h, rad * 0.88, sa * slope_h))
            u = (i / n_pts) * 2.0
            c_v = c_rim_out if is_lobe else c_rim_in
            if curved:
                mid_rad = rad * (0.52 if is_lobe else 0.46)
                mx = ox_mid + ca * mid_rad
                mz = oz_mid + sa * mid_rad
                my = ty_mid + (0.04 * slope_h if is_lobe else 0.06 * slope_h)
                mid_ids.append(pine_sm.add_vertex((mx, my, mz), n_out, (u, 0.48), c_mid_out if is_lobe else c_rim_in))
            rim_top_ids.append(pine_sm.add_vertex((px, py, pz), n_out, (u, 1.0), c_v))
            rim_und_ids.append(pine_sm.add_vertex((px, py, pz), (ca * 0.2, -0.96, sa * 0.2), (u, 0.9), c_under))

        for i in range(n_pts):
            j = (i + 1) % n_pts
            if curved:
                pine_sm.add_tri(apex_idx, mid_ids[j], mid_ids[i], enforce_winding=True)
                pine_sm.add_quad(mid_ids[i], mid_ids[j], rim_top_ids[j], rim_top_ids[i], enforce_winding=True)
            else:
                pine_sm.add_tri(apex_idx, rim_top_ids[j], rim_top_ids[i], enforce_winding=True)
            pine_sm.add_tri(under_center_idx, rim_und_ids[i], rim_und_ids[j], enforce_winding=True)


def add_icosphere_blob(
    sm: SubmeshBuilder,
    cx: float,
    cy: float,
    cz: float,
    rx: float,
    ry: float,
    rz: float,
    rng: random.Random,
    c_bot: Color4,
    c_top: Color4,
    jitter: float = 0.14,
    flatten_bottom: float = 0.0,
    uv_scale: float = 0.65,
) -> None:
    """Organic low-poly 20-tri perturbed ellipsoid (ideal for bushes, boulders, broadleaf canopy)."""
    phi = (1.0 + math.sqrt(5.0)) * 0.5
    raw_verts = [
        (-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0),
        (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi),
        (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1),
    ]
    faces = [
        (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
        (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
        (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
        (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
    ]
    yaw = rng.uniform(0.0, math.tau)
    v_ids: List[int] = []
    for vx, vy, vz in raw_verts:
        nx, ny, nz = v3_norm((vx, vy, vz))
        nx, nz = _rot_y(nx, nz, yaw)
        s = 1.0 + rng.uniform(-jitter, jitter)
        px = cx + nx * rx * s
        py_local = ny * ry * s
        if flatten_bottom > 0.0 and py_local < -ry * (1.0 - flatten_bottom):
            py_local = -ry * (1.0 - flatten_bottom)
        py = cy + py_local
        pz = cz + nz * rz * s
        t_h = _clamp01((ny + 1.0) * 0.5)
        col = _lerp4(c_bot, c_top, t_h * t_h * 0.4 + t_h * 0.6)
        u = (math.atan2(nz, nx) / math.tau + 0.5) * 2.0 * uv_scale
        v = (0.5 - math.asin(max(-1.0, min(1.0, ny))) / math.pi) * 2.0 * uv_scale
        v_ids.append(sm.add_vertex((px, py, pz), (nx, ny, nz), (u, v), col))

    for a, b, c in faces:
        sm.add_tri(v_ids[a], v_ids[b], v_ids[c], enforce_winding=True)


def add_leafy_bush(
    sm: SubmeshBuilder,
    x: float,
    y: float,
    z: float,
    radius: float,
    rng: random.Random,
    c_bot: Color4 = (0.34, 0.58, 0.36, 1.0),
    c_top: Color4 = (0.86, 1.0, 0.64, 1.0),
    puffs: int = 3,
) -> None:
    """Clustered rounded BDSP leafy bush made of overlapping organic puffs."""
    # Main central puff
    add_icosphere_blob(
        sm, x, y + radius * 0.48, z,
        radius * 0.95, radius * 0.72, radius * 0.92,
        rng, c_bot, c_top, jitter=0.14, flatten_bottom=0.28,
    )
    for k in range(puffs - 1):
        ang = rng.uniform(0.0, math.tau)
        dist = radius * rng.uniform(0.38, 0.68)
        pr = radius * rng.uniform(0.55, 0.76)
        add_icosphere_blob(
            sm,
            x + math.cos(ang) * dist,
            y + pr * rng.uniform(0.36, 0.56),
            z + math.sin(ang) * dist,
            pr, pr * rng.uniform(0.68, 0.85), pr,
            rng, c_bot, _mul_color(c_top, rng.uniform(0.92, 1.06)),
            jitter=0.14, flatten_bottom=0.25,
        )


def add_broadleaf_tree(
    bark_sm: SubmeshBuilder,
    leaf_sm: SubmeshBuilder,
    x: float,
    y: float,
    z: float,
    height: float,
    canopy_r: float,
    rng: random.Random,
    c_bot: Color4 = (0.28, 0.52, 0.30, 1.0),
    c_top: Color4 = (0.80, 0.98, 0.58, 1.0),
) -> None:
    """Lush broadleaf forest/park tree with gnarled trunk and clustered foliage crown."""
    trunk_h = height * 0.58
    add_cylinder(
        bark_sm, x, y - 0.3, z,
        canopy_r * 0.19, canopy_r * 0.10, trunk_h + 0.3,
        segs=7,
        c_bot=(0.74, 0.68, 0.62, 1.0),
        c_top=(0.52, 0.48, 0.44, 1.0),
        tilt_x=rng.uniform(-0.22, 0.22),
        tilt_z=rng.uniform(-0.22, 0.22),
    )
    crown_y = y + height * 0.68
    add_icosphere_blob(
        leaf_sm, x, crown_y + canopy_r * 0.22, z,
        canopy_r * 0.92, canopy_r * 0.76, canopy_r * 0.92,
        rng, c_bot, c_top, jitter=0.14,
    )
    for k in range(3):
        ang = (k / 3.0) * math.tau + rng.uniform(-0.35, 0.35)
        pr = canopy_r * rng.uniform(0.62, 0.78)
        dist = canopy_r * rng.uniform(0.45, 0.65)
        add_icosphere_blob(
            leaf_sm,
            x + math.cos(ang) * dist,
            crown_y - canopy_r * rng.uniform(0.05, 0.24),
            z + math.sin(ang) * dist,
            pr, pr * 0.78, pr,
            rng, _mul_color(c_bot, 0.92), _mul_color(c_top, rng.uniform(0.92, 1.04)),
            jitter=0.13,
        )


def add_grass_tuft(
    sm: SubmeshBuilder,
    x: float,
    y: float,
    z: float,
    scale: float,
    rng: random.Random,
    c_root: Color4 = (0.24, 0.52, 0.18, 1.0),
    c_tip: Color4 = (0.62, 0.92, 0.34, 1.0),
    blades: int = 4,
) -> None:
    """Cluster of 3D tapered grass blades (use on DOUBLE_SIDED submesh)."""
    for k in range(blades):
        ang = (k / blades) * math.tau + rng.uniform(-0.35, 0.35)
        ca, sa = math.cos(ang), math.sin(ang)
        tx, tz = -sa, ca  # blade width tangent
        bw = 0.085 * scale * rng.uniform(0.85, 1.2)
        bh = 0.34 * scale * rng.uniform(0.75, 1.35)
        lean = 0.16 * scale * rng.uniform(0.6, 1.3)
        ox = x + ca * 0.05 * scale
        oz = z + sa * 0.05 * scale
        p0 = (ox - tx * bw, y - 0.02, oz - tz * bw)
        p1 = (ox + tx * bw, y - 0.02, oz + tz * bw)
        p2 = (ox + ca * lean, y + bh, oz + sa * lean)
        n = v3_norm((ca * 0.4, 0.9, sa * 0.4))
        i0 = sm.add_vertex(p0, n, (0.0, 1.0), c_root)
        i1 = sm.add_vertex(p1, n, (1.0, 1.0), c_root)
        i2 = sm.add_vertex(p2, n, (0.5, 0.0), c_tip)
        sm.add_tri(i0, i1, i2, enforce_winding=True)


def add_wildflower(
    sm: SubmeshBuilder,
    x: float,
    y: float,
    z: float,
    scale: float,
    petal_color: Color4,
    rng: random.Random,
) -> None:
    """Cute stylized BDSP wildflower blossom (small cupped 5-petal star on grass)."""
    fy = y + 0.18 * scale
    yaw = rng.uniform(0.0, math.tau)
    center_c: Color4 = (1.0, 0.86, 0.24, 1.0)
    ci = sm.add_vertex((x, fy + 0.025 * scale, z), (0.0, 1.0, 0.0), (0.5, 0.5), center_c)
    petals = 5
    r_out = 0.16 * scale
    r_in = 0.065 * scale
    ring: List[int] = []
    for i in range(petals * 2):
        ang = yaw + (i / (petals * 2)) * math.tau
        rad = r_out if (i % 2 == 0) else r_in
        dy = 0.03 * scale if (i % 2 == 0) else 0.0
        px = x + math.cos(ang) * rad
        pz = z + math.sin(ang) * rad
        col = petal_color if (i % 2 == 0) else _lerp4(petal_color, center_c, 0.5)
        ring.append(sm.add_vertex((px, fy + dy, pz), (0.0, 1.0, 0.0), (0.5, 0.5), col))
    for i in range(petals * 2):
        j = (i + 1) % (petals * 2)
        sm.add_tri(ci, ring[j], ring[i], enforce_winding=True)


def add_box(
    sm: SubmeshBuilder,
    cx: float,
    cy: float,
    cz: float,
    sx: float,
    sy: float,
    sz: float,
    yaw: float = 0.0,
    color: Color4 = (1.0, 1.0, 1.0, 1.0),
    top_color: Color4 | None = None,
    bot_shade: float = 0.80,
    uv_scale: float = 0.35,
) -> None:
    """Oriented 3D box with clean outward face normals and world-scaled UVs."""
    hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
    c_top = top_color if top_color is not None else color
    c_bot = _mul_color(color, bot_shade)

    def xform(lx: float, ly: float, lz: float) -> Vec3:
        rx, rz = _rot_y(lx, lz, yaw)
        return (cx + rx, cy + ly, cz + rz)

    def xform_n(nx: float, ny: float, nz: float) -> Vec3:
        rx, rz = _rot_y(nx, nz, yaw)
        return v3_norm((rx, ny, rz))

    corners = [
        xform(-hx, -hy, -hz),  # 0
        xform(+hx, -hy, -hz),  # 1
        xform(+hx, +hy, -hz),  # 2
        xform(-hx, +hy, -hz),  # 3
        xform(-hx, -hy, +hz),  # 4
        xform(+hx, -hy, +hz),  # 5
        xform(+hx, +hy, +hz),  # 6
        xform(-hx, +hy, +hz),  # 7
    ]
    # 6 faces: (indices, local_n, u_dim, v_dim, colors)
    faces = [
        ((4, 5, 6, 7), (0, 0, 1), sx, sy, (c_bot, c_bot, color, color)),
        ((1, 0, 3, 2), (0, 0, -1), sx, sy, (c_bot, c_bot, color, color)),
        ((5, 1, 2, 6), (1, 0, 0), sz, sy, (c_bot, c_bot, color, color)),
        ((0, 4, 7, 3), (-1, 0, 0), sz, sy, (c_bot, c_bot, color, color)),
        ((3, 7, 6, 2), (0, 1, 0), sx, sz, (c_top, c_top, c_top, c_top)),
        ((0, 1, 5, 4), (0, -1, 0), sx, sz, (c_bot, c_bot, c_bot, c_bot)),
    ]
    for (a, b, c, d), ln, ud, vd, cols in faces:
        hint = xform_n(*ln)
        sm.add_flat_quad(
            corners[a], corners[b], corners[c], corners[d],
            (0.0, 0.0), (ud * uv_scale, 0.0), (ud * uv_scale, vd * uv_scale), (0.0, vd * uv_scale),
            cols[0], cols[1], cols[2], cols[3],
            outward_hint=hint,
        )


def add_pitched_house(
    wall_sm: SubmeshBuilder,
    roof_sm: SubmeshBuilder,
    cx: float,
    base_y: float,
    cz: float,
    w: float,
    d: float,
    wall_h: float,
    roof_h: float,
    yaw: float,
    wall_color: Color4,
    roof_color: Color4,
) -> None:
    """Stylized Sinnoh town house (box walls + overhanging gabled pitched roof)."""
    add_box(wall_sm, cx, base_y + wall_h * 0.5, cz, w, wall_h, d, yaw=yaw, color=wall_color)

    hx = w * 0.56
    hz = d * 0.56
    y0 = base_y + wall_h - 0.12
    y1 = base_y + wall_h + roof_h

    def xf(lx: float, ly: float, lz: float) -> Vec3:
        rx, rz = _rot_y(lx, lz, yaw)
        return (cx + rx, ly, cz + rz)

    p_fl = xf(-hx, y0, +hz)
    p_fr = xf(+hx, y0, +hz)
    p_bl = xf(-hx, y0, -hz)
    p_br = xf(+hx, y0, -hz)
    r_l = xf(-hx, y1, 0.0)
    r_r = xf(+hx, y1, 0.0)

    c_dark = _mul_color(roof_color, 0.80)
    c_top = _mul_color(roof_color, 1.05)
    # Front slope
    nf = _rot_y(0.0, 1.0, yaw)
    roof_sm.add_flat_quad(
        p_fl, p_fr, r_r, r_l,
        (0, 0), (2, 0), (2, 1), (0, 1),
        c_dark, c_dark, c_top, c_top,
        outward_hint=(nf[0], 0.8, nf[1]),
    )
    # Back slope
    nb = _rot_y(0.0, -1.0, yaw)
    roof_sm.add_flat_quad(
        p_br, p_bl, r_l, r_r,
        (0, 0), (2, 0), (2, 1), (0, 1),
        c_dark, c_dark, c_top, c_top,
        outward_hint=(nb[0], 0.8, nb[1]),
    )
    # Gable triangles
    nl = _rot_y(-1.0, 0.0, yaw)
    nr = _rot_y(1.0, 0.0, yaw)
    roof_sm.add_flat_tri(p_bl, p_fl, r_l, (0, 0), (1, 0), (0.5, 1), wall_color, wall_color, wall_color, (nl[0], 0.0, nl[1]))
    roof_sm.add_flat_tri(p_fr, p_br, r_r, (0, 0), (1, 0), (0.5, 1), wall_color, wall_color, wall_color, (nr[0], 0.0, nr[1]))


def add_crystal_spire(
    sm: SubmeshBuilder,
    x: float,
    y: float,
    z: float,
    radius: float,
    height: float,
    tilt_x: float,
    tilt_z: float,
    c_base: Color4,
    c_tip: Color4,
    sides: int = 6,
    invert_y: bool = False,
) -> None:
    """Faceted crystalline prism spire (pointing up or inverted for Distortion World / stalactites)."""
    s_dir = -1.0 if invert_y else 1.0
    y_mid = y + s_dir * height * 0.72
    y_tip = y + s_dir * height
    r_mid = radius * 0.82

    bot_pts: List[Vec3] = []
    mid_pts: List[Vec3] = []
    for i in range(sides):
        ang = (i / sides) * math.tau
        ca, sa = math.cos(ang), math.sin(ang)
        bot_pts.append((x + ca * radius, y, z + sa * radius))
        mid_pts.append((x + tilt_x * 0.72 + ca * r_mid, y_mid, z + tilt_z * 0.72 + sa * r_mid))
    tip = (x + tilt_x, y_tip, z + tilt_z)

    for i in range(sides):
        j = (i + 1) % sides
        out_x = (bot_pts[i][0] + bot_pts[j][0]) * 0.5 - x
        out_z = (bot_pts[i][2] + bot_pts[j][2]) * 0.5 - z
        u0, u1 = i / sides, (i + 1) / sides
        sm.add_flat_quad(
            bot_pts[i], bot_pts[j], mid_pts[j], mid_pts[i],
            (u0, 1.0), (u1, 1.0), (u1, 0.28), (u0, 0.28),
            c_base, c_base, c_tip, c_tip,
            outward_hint=(out_x, 0.1 * s_dir, out_z),
        )
        sm.add_flat_tri(
            mid_pts[i], mid_pts[j], tip,
            (u0, 0.28), (u1, 0.28), ((u0 + u1) * 0.5, 0.0),
            c_tip, c_tip, _mul_color(c_tip, 1.15),
            outward_hint=(out_x, 0.6 * s_dir, out_z),
        )


def add_floating_island(
    top_sm: SubmeshBuilder,
    rock_sm: SubmeshBuilder,
    cx: float,
    top_y: float,
    cz: float,
    radius: float,
    depth: float,
    rng: random.Random,
    top_color: Color4,
    rock_color: Color4,
    sides: int = 8,
) -> None:
    """Fractured floating stone platform with craggy tapered rocky underside (Distortion World)."""
    ring_top: List[Vec3] = []
    ring_rim: List[Vec3] = []
    for i in range(sides):
        ang = (i / sides) * math.tau
        rad = radius * rng.uniform(0.84, 1.14)
        px = cx + math.cos(ang) * rad
        pz = cz + math.sin(ang) * rad
        ring_top.append((px, top_y, pz))
        ring_rim.append((cx + math.cos(ang) * rad * 0.88, top_y - 0.55, cz + math.sin(ang) * rad * 0.88))

    tip = (cx + rng.uniform(-0.3, 0.3), top_y - depth, cz + rng.uniform(-0.3, 0.3))
    center_top = (cx, top_y + 0.04, cz)
    c_mid = _mul_color(rock_color, 0.78)
    c_tip = _mul_color(rock_color, 0.42)

    for i in range(sides):
        j = (i + 1) % sides
        out_x = (ring_top[i][0] + ring_top[j][0]) * 0.5 - cx
        out_z = (ring_top[i][2] + ring_top[j][2]) * 0.5 - cz
        top_sm.add_flat_tri(
            ring_top[i], ring_top[j], center_top,
            (ring_top[i][0] * 0.2, ring_top[i][2] * 0.2),
            (ring_top[j][0] * 0.2, ring_top[j][2] * 0.2),
            (center_top[0] * 0.2, center_top[2] * 0.2),
            top_color, top_color, _mul_color(top_color, 1.06),
            outward_hint=(0.0, 1.0, 0.0),
        )
        rock_sm.add_flat_quad(
            ring_rim[i], ring_rim[j], ring_top[j], ring_top[i],
            (0.0, 0.2), (1.0, 0.2), (1.0, 0.0), (0.0, 0.0),
            c_mid, c_mid, rock_color, rock_color,
            outward_hint=(out_x, 0.0, out_z),
        )
        rock_sm.add_flat_tri(
            ring_rim[i], ring_rim[j], tip,
            (0.0, 0.2), (1.0, 0.2), (0.5, 1.0),
            c_mid, c_mid, c_tip,
            outward_hint=(out_x, -0.75, out_z),
        )


def add_mountain_ring(
    sm: SubmeshBuilder,
    rng: random.Random,
    r_inner: float = 40.0,
    r_peak: float = 52.0,
    r_outer: float = 64.0,
    segs: int = 72,
    base_y: float = -0.5,
    base_height: float = 9.5,
    c_base: Color4 = (0.28, 0.36, 0.52, 1.0),
    c_peak: Color4 = (0.48, 0.58, 0.78, 1.0),
) -> None:
    """Distant blue-hazed faceted mountain range ringing the horizon (Mt. Coronet backdrop)."""
    inner_pts: List[Vec3] = []
    ridge_pts: List[Vec3] = []
    outer_pts: List[Vec3] = []

    for i in range(segs):
        ang = (i / segs) * math.tau
        ca = math.cos(ang)
        sa = math.sin(ang)

        # Wrap angular distance helper
        def ang_dist(target: float) -> float:
            d = (ang - target + math.pi) % math.tau - math.pi
            return abs(d)

        # Hero Mt. Coronet massif right-back behind opponent (-0.42 rad) + secondary peaks
        hero = 15.5 * math.exp(-((ang_dist(-0.42) / 0.22) ** 2))
        sec1 = 7.0 * math.exp(-((ang_dist(-1.15) / 0.28) ** 2))
        sec2 = 6.5 * math.exp(-((ang_dist(-2.05) / 0.32) ** 2))
        sec3 = 5.5 * math.exp(-((ang_dist(0.35) / 0.35) ** 2))
        harm = (
            2.6 * math.sin(ang * 5.0 + 0.4)
            + 1.8 * math.cos(ang * 9.0 - 1.1)
            + 1.2 * math.sin(ang * 17.0 + 0.7)
        )
        h = max(3.5, base_height + hero + sec1 + sec2 + sec3 + harm + rng.uniform(-0.8, 0.8))

        ri = r_inner + rng.uniform(-1.5, 1.5)
        rp = r_peak + rng.uniform(-2.0, 2.0)
        ro = r_outer
        inner_pts.append((ca * ri, base_y, sa * ri))
        ridge_pts.append((ca * rp, base_y + h, sa * rp))
        outer_pts.append((ca * ro, base_y - 2.0, sa * ro))

    for i in range(segs):
        j = (i + 1) % segs
        p0, p1 = inner_pts[i], inner_pts[j]
        p2, p3 = ridge_pts[j], ridge_pts[i]
        o0, o1 = outer_pts[i], outer_pts[j]
        out_in = (-((p0[0] + p1[0]) * 0.5), 0.35, -((p0[2] + p1[2]) * 0.5))
        sm.add_flat_quad(
            p0, p1, p2, p3,
            (i * 0.15, 0.0), ((i + 1) * 0.15, 0.0), ((i + 1) * 0.15, 1.0), (i * 0.15, 1.0),
            c_base, c_base, c_peak, c_peak,
            outward_hint=out_in,
        )
        out_ex = ((p2[0] + p3[0]) * 0.5, 0.35, (p2[2] + p3[2]) * 0.5)
        sm.add_flat_quad(
            p3, p2, o1, o0,
            (i * 0.15, 1.0), ((i + 1) * 0.15, 1.0), ((i + 1) * 0.15, 0.0), (i * 0.15, 0.0),
            c_peak, c_peak, c_base, c_base,
            outward_hint=out_ex,
        )


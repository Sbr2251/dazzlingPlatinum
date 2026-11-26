#!/usr/bin/env python3
"""The Gardevoir Fountain of Everspring Sanctuary (Route 218, tiles x 93..96, z 749..752) and the shared low-poly
kit (lathe, baked vertex lighting, camera-facing test) that build_art.py also uses for the Rift Conduit crystal,
mushrooms, lanterns and blossom trees.

Everything here is pure math: lathed octagonal tiers, fluted columns (alternating radii), a sculpted Gardevoir
(16-fold fluted ballgown in three flared tiers, slender waist and torso, rose-crystal chest fin front and back,
outstretched arms curving over the basin, emerald bob helmet around a pale face, upward-swept emerald cheek
crests), four parabolic water jets and a carved south plaque. Lighting is baked into vertex colours: a cool
moonlight key from the upper left, lavender ambient, sky fill, ambient occlusion in the gown folds, under the tier
lips, the arms and the neck, and cyan-lavender bounce light from the glowing water below. The fountain is unlit
geometry (polygon lights off), so it reads as a softly luminous moonstone monument at every time of day.

Placement: centred on the 4x4 blocked rect, (95.0, 751.0). Every fountain face goes to map_data_050 (its
centroid is at x <= 96.95, the chunk seam is x = 96.0): NNS draws a chunk model's polygons wherever they are (no
per-chunk clipping), and the fountain then loads, culls and draws as one model, so the statue can never be split
from its basin by chunk streaming. The basin's east 0.95 tile past the seam is well inside the chunk's fx16 range
(+-32 tiles around the chunk centre at posScale 64).

Not runnable on its own: build_art.py calls build(F) with its face builder, then summary().
"""
import math

CX, CZ = 95.0, 751.0            # fountain centre (absolute tiles); 4x4 blocked rect x 93..97, z 749..753
CHUNK = 50
OCT = [math.radians(22.5 + 45 * k) for k in range(8)]      # octagon vertex angles (flats face the axes)
A_STEP, A_WALL, A_CAP, A_IN = 1.95, 1.80, 1.86, 1.50       # apothems: base step, outer wall, cap molding, inner wall
H_STEP, H_CAP0, H_CAP, H_WATER = 0.10, 0.40, 0.48, 0.36
PED_R, PED_TOP = 0.30, 0.86
BOWL_R, BOWL_IN, BOWL_TOP, BOWL_WATER = 0.86, 0.74, 1.12, 1.06
HB = 1.16                        # statue base (top of the drum in the bowl)
SR, SV = 1.22, 1.32               # statue scale: radial, vertical (reads at the field camera's 59-degree pitch)
CAM = (0.0, 0.857, 0.515)        # direction to the field camera (CAMERA_TYPE_DEFAULT, pitch 59 degrees)

# texel boxes in the 32x32 atlases (see textures_math.py)
GV = {"hair": (1, 1, 15, 15), "pearl": (17, 1, 31, 15), "rose": (1, 17, 15, 31), "fold": (17, 17, 31, 31)}


# ---------------------------------------------------------------------------------------------------------------
# vector helpers and the shared kit
# ---------------------------------------------------------------------------------------------------------------

def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def face_n(pts):
    n = cross(sub(pts[1], pts[0]), sub(pts[2], pts[0]))
    if len(pts) == 4 and sum(c * c for c in n) < 1e-12:
        n = cross(sub(pts[2], pts[0]), sub(pts[3], pts[0]))
    return norm(n)


def visible(n, margin=0.25):
    """Could a face with outward normal n face the field camera anywhere on screen?"""
    return dot(n, CAM) > -margin


def uvbox(box, size=32):
    x0, y0, x1, y1 = box
    return (x0 / size, y0 / size, x1 / size, y1 / size)


LIGHT = norm((-0.42, 0.80, 0.42))


def bake(n, h, ao=1.0, tint=(1.0, 1.0, 1.0), water_h=H_WATER, bounce=1.0, glow=0.0, cap=0.97):
    """Baked vertex colour (0..255): lavender ambient + cool moonlight key + sky fill, times AO, plus cyan-lavender
    bounce from the water below (stronger on down-facing normals, fading with height)."""
    d = max(0.0, dot(n, LIGHT))
    sky = 0.10 * max(0.0, n[1])
    base = [0.50 + 0.50 * d + sky, 0.50 + 0.47 * d + sky * 1.05, 0.60 + 0.42 * d + sky * 1.2]
    up = max(0.0, h - water_h)
    k = bounce * (0.30 + 0.70 * max(0.0, -n[1])) * math.exp(-up / 0.75) * 0.32
    bnc = (0.42 * k, 0.80 * k, 1.0 * k)
    out = []
    for i in range(3):
        v = tint[i] * base[i] * ao + bnc[i] + glow
        out.append(int(round(255 * max(0.0, min(cap, v)))))
    return tuple(out)


def ring_pts(cx, cz, r, h, angles, rmul=None):
    return [(cx + r * (rmul[j] if rmul else 1.0) * math.sin(a), h, cz + r * (rmul[j] if rmul else 1.0) * math.cos(a))
            for j, a in enumerate(angles)]


def lathe(F, mat, center, profile, segs, uv, chunk=None, ang0=0.0, flutes=None, color=None, cull=True,
          normal_out=True, group=None, solid=True, skip=None, chain="around"):
    """Surface of revolution around (cx, cz). profile: [(r, h)] bottom to top (r = 0 makes a pole). Angles from +z
    (south, toward the camera) clockwise toward +x. flutes: radius multipliers per segment vertex (fluting).
    color(n, h, j, i) -> rgb for unlit materials (None: lit, normals sent). Faces the camera never sees are dropped
    (cull); skip(j, i) drops the quad between columns j, j+1 and rings i, i+1.

    Display-list economy: every face is a quad (a pole becomes a degenerate quad whose pole vertex has one shared
    normal / uv / colour), wound so nsbmd.faces_to_prims chains each band into one quad strip around the axis
    (chain="around", 2 vertices per quad) or each column up the profile (chain="up"). Returns faces added."""
    cx, cz = center
    angles = [ang0 + 2 * math.pi * j / segs for j in range(segs)]
    rings = [ring_pts(cx, cz, r, h, angles, flutes if r > 0 else None) for r, h in profile]
    u0, v0, u1, v1 = uv
    norms = []
    for i, (r, h) in enumerate(profile):
        a = profile[max(0, i - 1)]
        b = profile[min(len(profile) - 1, i + 1)]
        dr, dh = b[0] - a[0], b[1] - a[1]
        row = []
        for j, ang in enumerate(angles):
            if r == 0:
                nn = (0.0, 1.0 if i > 0 else -1.0, 0.0)
            else:
                rad = (math.sin(ang), 0.0, math.cos(ang))
                nn = norm((rad[0] * dh, -dr, rad[2] * dh)) if (dr or dh) else (0.0, 1.0, 0.0)
            if not normal_out:
                nn = (-nn[0], -nn[1], -nn[2])
            row.append(nn)
        norms.append(row)
    nb = len(profile) - 1

    def vert(i, j):
        r = profile[i][0]
        uu = (u0 + u1) / 2 if r == 0 else u0 + (u1 - u0) * j / segs
        vv = v1 - (v1 - v0) * i / nb
        jj = j % segs
        col = color(norms[i][jj], rings[i][jj][1], 0 if r == 0 else jj, i) if color else None
        return rings[i][jj], (uu, vv), norms[i][jj], col
    added = 0
    for i in range(nb):
        for j in range(segs):
            if skip and skip(j, i):
                continue
            a, b_, c, d = vert(i, j), vert(i, j + 1), vert(i + 1, j + 1), vert(i + 1, j)
            fn = norm(tuple(a[2][q] + b_[2][q] + c[2][q] + d[2][q] for q in range(3)))
            if cull and not visible(fn):
                continue
            order = [d, a, b_, c] if chain == "around" else [a, b_, c, d]
            if order[0][0] == order[1][0] and order[2][0] == order[3][0]:
                continue
            F.add(mat, [o[0] for o in order], [o[1] for o in order],
                  colors=[o[3] for o in order] if color else None, normals=None if color else [o[2] for o in order],
                  facing=fn, chunk=chunk, group=group, solid=solid)
            added += 1
    return added


def disc(F, mat, center, r_out, r_in, h, segs, uv, chunk=None, ang0=0.0, color=None, group=None, solid=True,
         flutes=None, up=True):
    """Flat annulus (r_in > 0) or polygon (r_in == 0: degenerate quads round one shared centre vertex) facing up,
    wound so the ring chains into one quad strip."""
    cx, cz = center
    angles = [ang0 + 2 * math.pi * j / segs for j in range(segs)]
    u0, v0, u1, v1 = uv
    n = (0.0, 1.0, 0.0) if up else (0.0, -1.0, 0.0)

    def tuv(p):
        return (u0 + (u1 - u0) * (0.5 + (p[0] - cx) / (2 * r_out)), v0 + (v1 - v0) * (0.5 + (p[2] - cz) / (2 * r_out)))
    outer = [(cx + r_out * (flutes[j] if flutes else 1.0) * math.sin(a), h,
              cz + r_out * (flutes[j] if flutes else 1.0) * math.cos(a)) for j, a in enumerate(angles)]
    inner = [(cx + r_in * math.sin(a), h, cz + r_in * math.cos(a)) for a in angles] if r_in > 0 else [(cx, h, cz)] * segs
    for j in range(segs):
        k = (j + 1) % segs
        pts = [inner[j], outer[j], outer[k], inner[k]]
        uvs = [tuv(p) for p in pts]
        if r_in <= 0:
            uvs[0] = uvs[3] = ((u0 + u1) / 2, (v0 + v1) / 2)
        cols = [color(n, p[1], (p[0] - cx, p[2] - cz)) for p in pts] if color else None
        F.add(mat, pts, uvs, colors=cols, normals=None if color else [n] * 4, facing=n, chunk=chunk, group=group,
              solid=solid)


# ---------------------------------------------------------------------------------------------------------------
# the fountain
# ---------------------------------------------------------------------------------------------------------------

STATS = {}


def _count(name, F, before):
    STATS[name] = STATS.get(name, 0) + F.count(group="fountain") - before


def build(F):
    """Adds the Gardevoir Fountain to F (build_art.Art). Materials: u_marble (basin, pedestal, bowl, plaque),
    u_water (glowing water surfaces), u_jet (double-sided water jets), u_gv (statue), u_gv2 (statue blades)."""
    STATS.clear()
    C = (CX, CZ)
    grp = dict(chunk=CHUNK, group="fountain")
    marble = uvbox((0, 0, 32, 32))
    oct_r = lambda a: a / math.cos(math.radians(22.5))  # noqa: E731  apothem -> circumradius
    ang0 = math.radians(22.5)

    def stone(ao=1.0, tint=(0.98, 0.98, 1.0)):
        return lambda n, h, *a: bake(n, h, ao, tint)

    # -- tier 1: base step, outer wall, cap molding, inner wall (octagonal, pale moonstone)
    b = F.count(group="fountain")
    lathe(F, "u_marble", C, [(oct_r(A_STEP), 0.0), (oct_r(A_STEP), H_STEP)], 8, (0, 0, 1, 0.12), ang0=ang0,
          color=lambda n, h, j, i: bake(n, h, 0.82 if i == 0 else 0.95), **grp)
    disc(F, "u_marble", C, oct_r(A_STEP), oct_r(A_WALL), H_STEP, 8, marble, ang0=ang0,
         color=lambda n, h, d: bake(n, h, 0.86 if math.hypot(*d) < oct_r(A_WALL) + 0.05 else 1.0), **grp)
    lathe(F, "u_marble", C, [(oct_r(A_WALL), H_STEP), (oct_r(A_WALL), H_CAP0)], 8, (0, 0.1, 1, 0.5), ang0=ang0,
          color=lambda n, h, j, i: bake(n, h, 0.78 if i == 0 else 0.9), **grp)
    lathe(F, "u_marble", C, [(oct_r(A_WALL), H_CAP0), (oct_r(A_CAP), H_CAP0 + 0.02), (oct_r(A_CAP), H_CAP)], 8,
          (0, 0.5, 1, 0.62), ang0=ang0, color=lambda n, h, j, i: bake(n, h, 0.85 if i == 0 else 1.0), **grp)
    disc(F, "u_marble", C, oct_r(A_CAP), oct_r(A_IN), H_CAP, 8, marble, ang0=ang0,
         color=lambda n, h, d: bake(n, h, 1.0, glow=0.04 if math.hypot(*d) < oct_r(A_IN) + 0.05 else 0.0), **grp)
    lathe(F, "u_marble", C, [(oct_r(A_IN), H_CAP), (oct_r(A_IN), H_WATER)], 8, (0, 0.62, 1, 0.75), ang0=ang0,
          normal_out=False, color=lambda n, h, j, i: bake(n, h, 0.9, water_h=H_WATER, bounce=1.6), **grp)
    _count("outer basin (3 tiers)", F, b)

    # -- glowing water surface: bright cyan around the pedestal, lavender toward the rim
    b = F.count(group="fountain")

    def water_col(n, h, d):
        r = math.hypot(*d) / oct_r(A_IN)
        c0, c1 = (255, 255, 255), (214, 196, 255)
        return tuple(int(c0[i] + (c1[i] - c0[i]) * min(1.0, r)) for i in range(3))
    disc(F, "u_water", C, oct_r(A_IN), PED_R + 0.06, H_WATER, 8, (0, 0, 2.0, 2.0), ang0=ang0, color=water_col,
         solid=False, **grp)
    _count("basin water", F, b)

    # -- fluted marble pedestal (16 flutes) with a torus foot and a capital
    b = F.count(group="fountain")
    fl16 = [1.0 if j % 2 == 0 else 0.84 for j in range(16)]
    lathe(F, "u_marble", C, [(PED_R + 0.08, H_WATER), (PED_R + 0.08, H_WATER + 0.06), (PED_R + 0.02, H_WATER + 0.10)],
          8, (0, 0.75, 0.5, 0.85), ang0=ang0, color=lambda n, h, j, i: bake(n, h, 0.95, bounce=1.5), **grp)
    lathe(F, "u_marble", C, [(PED_R, H_WATER + 0.10), (PED_R * 0.92, PED_TOP - 0.06)], 16, (0, 0, 1, 1), flutes=fl16,
          color=lambda n, h, j, i: bake(n, h, 1.0 if j % 2 == 0 else 0.72, bounce=1.4), **grp)
    lathe(F, "u_marble", C, [(PED_R * 0.95, PED_TOP - 0.06), (PED_R + 0.07, PED_TOP)], 8, (0, 0.85, 0.5, 0.95),
          ang0=ang0, color=lambda n, h, j, i: bake(n, h, 0.9), **grp)
    _count("fluted pedestal", F, b)

    # -- upper bowl (tier 2): flared octagonal bowl, rim, glowing water, drum under the statue
    b = F.count(group="fountain")
    lathe(F, "u_marble", C, [(PED_R + 0.07, PED_TOP), (0.62, 0.98), (BOWL_R, BOWL_TOP - 0.04), (BOWL_R, BOWL_TOP)],
          8, (0, 0, 1, 0.4), ang0=ang0, color=lambda n, h, j, i: bake(n, h, (0.7, 0.85, 0.95, 1.0)[i], bounce=1.3),
          **grp)
    disc(F, "u_marble", C, BOWL_R, BOWL_IN, BOWL_TOP, 8, marble, ang0=ang0, color=lambda n, h, d: bake(n, h, 1.0),
         **grp)
    lathe(F, "u_marble", C, [(BOWL_IN, BOWL_TOP), (BOWL_IN, BOWL_WATER)], 8, (0, 0.4, 1, 0.5), ang0=ang0,
          normal_out=False, color=lambda n, h, j, i: bake(n, h, 0.9, water_h=BOWL_WATER, bounce=1.6), **grp)
    disc(F, "u_water", C, BOWL_IN, 0.38, BOWL_WATER, 8, (0, 0, 0.6, 0.6), ang0=ang0,
         color=lambda n, h, d: (235, 252, 255) if math.hypot(*d) < 0.5 else (196, 200, 250), solid=False, **grp)
    lathe(F, "u_marble", C, [(0.38, BOWL_WATER), (0.38, HB - 0.03), (0.33, HB)], 8, (0, 0.5, 0.6, 0.6), ang0=ang0,
          color=lambda n, h, j, i: bake(n, h, 0.85 if i == 0 else 1.0, water_h=BOWL_WATER, bounce=1.5), **grp)
    disc(F, "u_marble", C, 0.33, 0.0, HB, 8, marble, ang0=ang0, color=lambda n, h, d: bake(n, h, 0.7), **grp)
    _count("upper bowl + drum", F, b)

    # -- four arching water jets from the bowl rim (diagonals), bright cyan/white ribbons, plus splash stars
    b = F.count(group="fountain")
    for k in range(4):
        a = math.radians(45 + 90 * k)
        rad, tan = (math.sin(a), math.cos(a)), (math.cos(a), -math.sin(a))
        segs = 6
        pts = []
        for s in range(segs + 1):
            t = s / segs
            r = BOWL_R + 0.02 + 0.50 * t
            h = BOWL_TOP + 0.02 + 0.30 * t - 1.08 * t * t
            pts.append((CX + rad[0] * r, h, CZ + rad[1] * r, t))
        for s in range(segs):
            (x0, h0, z0, t0), (x1, h1, z1, t1) = pts[s], pts[s + 1]
            w0, w1 = 0.085 * (1 - 0.35 * t0), 0.085 * (1 - 0.35 * t1)
            quad = [(x0 - tan[0] * w0, h0, z0 - tan[1] * w0), (x0 + tan[0] * w0, h0, z0 + tan[1] * w0),
                    (x1 + tan[0] * w1, h1, z1 + tan[1] * w1), (x1 - tan[0] * w1, h1, z1 - tan[1] * w1)]
            c0 = (250, 255, 255) if s < 2 else (200, 244, 255)
            c1 = (230, 252, 255) if s < 1 else (150, 220, 250)
            F.add("u_jet", quad, [(0.1, t0), (0.4, t0), (0.4, t1), (0.1, t1)], colors=[c0, c0, c1, c1],
                  facing=(0, 1, 0), solid=False, **grp)
        lx, lz = CX + rad[0] * (BOWL_R + 0.52), CZ + rad[1] * (BOWL_R + 0.52)
        star = [(lx + 0.16 * math.sin(math.radians(30 * q)) * (1 if q % 2 == 0 else 0.45), H_WATER + 0.015,
                 lz + 0.16 * math.cos(math.radians(30 * q)) * (1 if q % 2 == 0 else 0.45)) for q in range(12)]
        for q in range(0, 12, 2):
            tri = [star[q], star[(q + 1) % 12], (lx, H_WATER + 0.02, lz)]
            F.add("u_jet", tri, [(0.5, 0.5), (0.6, 0.5), (0.55, 0.6)],
                  colors=[(235, 252, 255), (190, 236, 255), (255, 255, 255)], facing=(0, 1, 0), solid=False, **grp)
    _count("4 water jets + splashes", F, b)

    # -- carved plaque slab on the south face, facing the reading tiles (94..95, 753)
    b = F.count(group="fountain")
    zf = CZ + A_WALL + 0.09
    px0, px1, ph0, ph1 = CX - 0.62, CX + 0.62, H_STEP + 0.02, H_CAP0 - 0.01
    F.box("u_marble", px0, CZ + A_WALL - 0.02, px1, zf, ph0, ph1, (0, 0, 1, 0.3),
          color=lambda n, h: bake(n, h, 1.0, tint=(1.0, 0.99, 1.02)), sides="swet", **grp)
    F.add("u_marble", [(px0 + 0.08, ph1 - 0.06, zf + 0.004), (px0 + 0.08, ph0 + 0.05, zf + 0.004),
                       (px1 - 0.08, ph0 + 0.05, zf + 0.004), (px1 - 0.08, ph1 - 0.06, zf + 0.004)][::-1],
          [(0.1, 0.4), (0.1, 0.6), (0.9, 0.6), (0.9, 0.4)][::-1],
          colors=[(150, 146, 196)] * 4, facing=(0, 0, 1), **grp)                     # recessed carved field
    ex, ey = CX, (ph0 + ph1) / 2
    gem = [(ex, ey + 0.09, zf + 0.008), (ex - 0.07, ey, zf + 0.008), (ex, ey - 0.09, zf + 0.008),
           (ex + 0.07, ey, zf + 0.008)]
    F.add("u_gv", gem, [(0.1, 0.55), (0.05, 0.75), (0.25, 0.95), (0.35, 0.75)], colors=[(255, 240, 248)] * 4,
          facing=(0, 0, 1), **grp)                                                    # rose-crystal heart emblem
    for sx in (-1, 1):                                                                # engraved rune ticks
        for q in range(3):
            x = ex + sx * (0.18 + 0.12 * q)
            F.add("u_marble", [(x - 0.025, ey + 0.05, zf + 0.006), (x - 0.025, ey - 0.05, zf + 0.006),
                               (x + 0.025, ey - 0.05, zf + 0.006), (x + 0.025, ey + 0.05, zf + 0.006)][::-1],
                  [(0.5, 0.5)] * 4, colors=[(214, 200, 250)] * 4, facing=(0, 0, 1), **grp)
    _count("carved south plaque", F, b)

    build_statue(F, grp)
    return STATS


class _Scaled:
    """Face-builder proxy scaling the statue about its base centre (CX, HB, CZ) by SR radially and SV vertically."""

    def __init__(self, F):
        self.F = F

    def add(self, mat, pts, uvs, **kw):
        pts = [(CX + (p[0] - CX) * SR, HB + (p[1] - HB) * SV, CZ + (p[2] - CZ) * SR) for p in pts]
        self.F.add(mat, pts, uvs, **kw)

    def count(self, group=None):
        return self.F.count(group)


def build_statue(F, grp):
    F = _Scaled(F)
    C = (CX, CZ)
    hair, pearl, rose, fold = (uvbox(GV[k]) for k in ("hair", "pearl", "rose", "fold"))

    def gown(ao_fn, tint=(1.0, 1.0, 1.0)):
        return lambda n, h, j, i: bake(n, h, ao_fn(j, i), tint=tint, water_h=BOWL_WATER, bounce=1.4)

    # skirt: three flared, 16-fold fluted tiers (alternate vertices pulled in = folds, darkened = AO)
    b = F.count(group="fountain")
    fl = [1.0 if j % 2 == 0 else 0.86 for j in range(16)]
    lathe(F, "u_gv", C, [(0.60, HB), (0.52, HB + 0.22), (0.40, HB + 0.48)], 16, fold, flutes=fl,
          color=gown(lambda j, i: (1.0 if j % 2 == 0 else 0.74) * (0.82 if i == 2 else 1.0)), **grp)
    lathe(F, "u_gv", C, [(0.46, HB + 0.40), (0.37, HB + 0.60), (0.25, HB + 0.84)], 16, fold, flutes=fl,
          ang0=math.pi / 16, color=gown(lambda j, i: (1.0 if j % 2 == 0 else 0.76) * (0.85 if i == 2 else 1.0)), **grp)
    lathe(F, "u_gv", C, [(0.28, HB + 0.78), (0.19, HB + 0.93), (0.115, HB + 1.04)], 8, pearl,
          color=gown(lambda j, i: 0.88 if i == 2 else 1.0), **grp)
    # emerald under-gown glimpsed through the front split of the lowest tier
    F.add("u_gv", [(CX - 0.11, HB + 0.02, CZ + 0.62), (CX + 0.11, HB + 0.02, CZ + 0.62), (CX, HB + 0.40, CZ + 0.44)],
          [(0.1, 0.4), (0.4, 0.4), (0.25, 0.05)], colors=[(196, 232, 236), (196, 232, 236), (150, 176, 196)],
          facing=(0, 0.3, 1), **grp)
    _count("Gardevoir: fluted ballgown (3 tiers)", F, b)

    # waist, torso, neck
    b = F.count(group="fountain")
    lathe(F, "u_gv", C, [(0.11, HB + 1.03), (0.15, HB + 1.18), (0.18, HB + 1.32), (0.14, HB + 1.43), (0.06, HB + 1.50)],
          8, pearl, color=gown(lambda j, i: (0.85, 1.0, 1.0, 0.92, 0.8)[i]), **grp)
    lathe(F, "u_gv", C, [(0.055, HB + 1.48), (0.05, HB + 1.59)], 6, pearl, color=gown(lambda j, i: 0.72), **grp)
    _count("Gardevoir: waist, torso, neck", F, b)

    # head: pale face (front window) inside an emerald bob helmet with a fringe
    b = F.count(group="fountain")
    hc = HB + 1.71
    lathe(F, "u_gv", C, [(0.0, hc - 0.15), (0.09, hc - 0.12), (0.145, hc - 0.03), (0.14, hc + 0.06), (0.10, hc + 0.13),
                         (0.0, hc + 0.16)], 8, pearl, color=gown(lambda j, i: 1.0, tint=(1.0, 0.99, 1.02)), **grp)
    front = lambda j: min(abs(((j + 0.5) / 12.0 * 360.0 + 180) % 360 - 180), 360) < 55  # noqa: E731
    lathe(F, "u_gv", C, [(0.17, hc - 0.13), (0.205, hc - 0.03), (0.20, hc + 0.08), (0.13, hc + 0.19), (0.0, hc + 0.23)],
          12, hair, color=lambda n, h, j, i: bake(n, h, (0.7, 0.9, 1.0, 1.0, 1.0)[i], water_h=BOWL_WATER),
          skip=lambda j, i: front(j) and i < 2, **grp)
    lathe(F, "u_gv", C, [(0.20, hc + 0.08), (0.185, hc + 0.025)], 12, hair, ang0=0.0,
          color=lambda n, h, j, i: bake(n, h, 0.85), skip=lambda j, i: not front(j), **grp)
    _count("Gardevoir: face + emerald bob helmet", F, b)

    # upward-swept emerald cheek crests (double-sided blades)
    b = F.count(group="fountain")
    for sx in (-1, 1):
        root_hi = (CX + sx * 0.19, hc - 0.02, CZ + 0.06)
        root_lo = (CX + sx * 0.17, hc - 0.14, CZ + 0.05)
        mid = (CX + sx * 0.25, hc - 0.16, CZ + 0.12)
        tip = (CX + sx * 0.36, hc + 0.06, CZ + 0.17)
        n = norm((0.2 * sx, 0.3, 1.0))
        cols = [bake(n, p[1], 0.9) for p in (root_hi, root_lo, mid, tip)]
        F.add("u_gv2", [root_hi, root_lo, mid], [(0.1, 0.1), (0.1, 0.4), (0.3, 0.45)], colors=cols[:3], facing=n, **grp)
        F.add("u_gv2", [root_hi, mid, tip], [(0.1, 0.1), (0.3, 0.45), (0.45, 0.05)], colors=[cols[0], cols[2], cols[3]],
              facing=n, **grp)
    _count("Gardevoir: cheek crests", F, b)

    # rose-crystal chest fin, front (toward the camera) and back
    b = F.count(group="fountain")
    for sz, reach in ((1, 0.46), (-1, 0.38)):
        tp = (CX, HB + 1.42, CZ + sz * 0.12)
        tip = (CX, HB + 1.22, CZ + sz * reach)
        bt = (CX, HB + 1.05, CZ + sz * 0.12)
        l, r = (CX - 0.05, HB + 1.24, CZ + sz * 0.17), (CX + 0.05, HB + 1.24, CZ + sz * 0.17)
        ru = uvbox(GV["rose"])
        for face in ((tp, l, tip), (tip, l, bt), (tp, tip, r), (tip, bt, r)):
            fn = face_n(face)
            if sz < 0:
                face = face[::-1]
                fn = face_n(face)
            cols = [bake(fn, p[1], 1.0, tint=(1.05, 1.0, 1.02), glow=0.05) for p in face]
            F.add("u_gv", list(face), [(ru[0], ru[1]), (ru[0], ru[3]), (ru[2], ru[3])], colors=cols, facing=fn, **grp)
    _count("Gardevoir: rose-crystal chest fins", F, b)

    # outstretched slender arms curving over the basin, hands as tapered blades
    b = F.count(group="fountain")
    for sx in (-1, 1):
        path = [(CX + sx * 0.16, HB + 1.40, CZ + 0.0), (CX + sx * 0.48, HB + 1.31, CZ + 0.13),
                (CX + sx * 0.78, HB + 1.37, CZ + 0.29)]
        radii = [0.052, 0.042, 0.034]
        for s in range(2):
            p0, p1 = path[s], path[s + 1]
            ax = norm(sub(p1, p0))
            e1 = norm(cross(ax, (0, 1, 0)))
            e2 = norm(cross(e1, ax))
            sq0 = [tuple(p0[c] + radii[s] * (math.cos(a) * e1[c] + math.sin(a) * e2[c]) for c in range(3))
                   for a in (0.785, 2.356, 3.927, 5.498)]
            sq1 = [tuple(p1[c] + radii[s + 1] * (math.cos(a) * e1[c] + math.sin(a) * e2[c]) for c in range(3))
                   for a in (0.785, 2.356, 3.927, 5.498)]
            for q in range(4):
                quad = [sq0[q], sq0[(q + 1) % 4], sq1[(q + 1) % 4], sq1[q]]
                fn = face_n(quad)
                mid = tuple(sum(p[c] for p in quad) / 4 for c in range(3))
                out = norm(sub(mid, tuple((p0[c] + p1[c]) / 2 for c in range(3))))
                if dot(fn, out) < 0:
                    quad, fn = quad[::-1], tuple(-c for c in fn)
                if not visible(fn):
                    continue
                cols = [bake(fn, p[1], 0.8 if fn[1] < -0.3 else 1.0, water_h=BOWL_WATER, bounce=1.8) for p in quad]
                F.add("u_gv", quad, [(0.6, 0.1), (0.9, 0.1), (0.9, 0.4), (0.6, 0.4)], colors=cols, facing=fn, **grp)
        w = path[-1]
        hand = [(w[0], w[1] + 0.03, w[2] - 0.02), (w[0] + sx * 0.17, w[1] - 0.05, w[2] + 0.10),
                (w[0], w[1] - 0.03, w[2] + 0.04)]
        fn = norm((0.0, 1.0, 0.3))
        F.add("u_gv2", hand, [(0.6, 0.1), (0.9, 0.25), (0.6, 0.4)], colors=[bake(fn, p[1], 1.0) for p in hand],
              facing=fn, **grp)
    _count("Gardevoir: arms + hands", F, b)


def summary():
    tot = sum(STATS.values())
    lines = [f"  {k:42s} {v:4d}" for k, v in STATS.items()]
    return "\n".join(lines + [f"  {'total fountain + statue':42s} {tot:4d} polygons"]), tot

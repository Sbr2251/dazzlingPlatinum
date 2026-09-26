"""Arena geometry: the home camera, the backdrop piece (ground and panorama) and the
platform piece (two platform discs) of BACKGROUND_PLAIN / TERRAIN_PLAIN.

Every texture coordinate is the home-camera screen position of its vertex, so at the
home pose each pixel shows the texel the classic BG3 or platform OBJ shows there. To
make that exact both on the DS, whose rasterizer uses integer vertex coordinates, and
in DeSmuME, which keeps 1/16 pixel, the vertices the home view can see are placed so
they project within VERTEX_WINDOW right of and below integers X, Y, and get the
texture coordinate
(X + HALF_PIXEL, Y + HALF_PIXEL) minus the texture's origin. fx.py projects every
vertex with the DS integer math to check where it lands.

World units: y is up, the ground is y = 0 and the camera looks toward -z. A vertex is
stored as fx16 world / VERTEX_SCALE.

Screen-affine texture coordinates are only exact where perspective-correct
interpolation is linear. On the ground, the platforms and the frontal part of the
panorama that holds along screen rows (no camera yaw), so columns can be wide; down a
column the error of a band h pixels tall and d pixels below the horizon is about
h * h / (4 * d), so bands get taller with distance from the horizon.
"""

import math

import classic
import fx
from fx import FX32_ONE, to_fx32

# Camera
FOVY_DEG = 40
CAM_HEIGHT = 4.0
CAM_Z = 14.0  # the camera is at (0, CAM_HEIGHT, CAM_Z)
HORIZON_ROW = 20  # screen row of the ground's horizon at the home pose
NEAR = 1.0
FAR = 128.0
VERTEX_SCALE = 8

# Sampling. A pixel's texture coordinate is its integer position plus HALF_PIXEL, so it
# lands mid-texel whether the rasterizer samples at the pixel's corner or its centre.
# Exact vertices project to [X, X + VERTEX_WINDOW) so the DS's truncation gives X and
# DeSmuME's rounding to 1/16 pixel gives exactly X. DeSmuME starts a span with the
# attributes of the edge point, so an edge even 1/16 right of X would move every texel
# of the span one pixel right. VERTEX_NUDGE, the middle of the window, is where they
# are aimed.
HALF_PIXEL = 0.5
VERTEX_WINDOW = 1 / 32
VERTEX_NUDGE = 1 / 64

# Rows the classic scene never shows: BG1 covers rows 144..191
HIDDEN_FROM_ROW = 144

# The backdrop is split into texture A (rows 0..127) and texture B (rows 127..158,
# mirrored beyond). Ground polygons above SPLIT_ROW use A, the ones below use B. Both
# textures hold row SPLIT_ROW, so it doesn't matter which one draws it.
TEX_A_ROWS = 128
TEX_B_FIRST_ROW = 127
TEX_B_ROWS = 32
SPLIT_ROW = 127

# The panorama stands on the ground at this row; the tree line (rows 50..57) is on it
WALL_BASE_ROW = 57
WALL_TOP_ROW = -64  # home screen row of its top edge (clamps to texture row 0)
WALL_ROW_STEP = 16

# Ground rows below the screen and the lateral reach, for the debug views
GROUND_LAST_ROW = 240
GROUND_FAR_X = 720  # home screen x the ground reaches on its near rows

# Texture coordinates are s16 in 1/16 texels; stay clear of the limit
MAX_TEXCOORD = 1900

# On-screen column width. The spans along a row are exact at any width.
COLUMN_PX = 32
SIDE_SEGMENTS = 4  # ground columns each side of the home frustum

# The panorama curves toward the camera beyond the home frustum: a circular arc of
# this radius, tangent to the frontal part, that ends on ARC_END_ROW's ground line
ARC_RADIUS = 30.0
ARC_END_ROW = 90
ARC_EXTRA_ROWS = (59, 61)  # extra ground rows to smooth the start of the curve

# Band height rule: max interpolation error in pixels
BAND_ERROR_PX = 0.25

# Platforms
PLATFORM_HEIGHT = 0.1  # the disc floats this high; its side band hangs to the ground
PLATFORM_BAND_BOTTOM = -0.02  # a little under the ground, so the ground can't z-fight it
PLATFORM_COLUMNS = (8, 5)  # vertices per disc row, minus one: player, enemy
PLATFORM_ROW_STEP = (4, 5)  # disc rows in the visible part
PLATFORM_HIDDEN_ROW_STEP = 8
PLATFORM_TEX_SIZE = ((256, 32), (128, 32))
# Texel of the sprite's origin in the platform texture. The enemy art (sprite rows
# -14..15) is placed at t 1..30 so the texture's clamped edge rows are transparent;
# the player's texture mirrors at t 32 (sprite row 16) instead.
PLATFORM_TEX_ORIGIN = ((128, 16), (64, 15))


def fx16(world):
    """fx16 of a world coordinate."""
    v = int(round(world / VERTEX_SCALE * FX32_ONE))
    assert -0x8000 <= v <= 0x7FFF, f"{world} is outside the fx16 range"
    return v


def fx16_vec(p):
    return tuple(fx16(c) for c in p)


def world_of(v):
    return tuple(c * VERTEX_SCALE / FX32_ONE for c in v)


class HomeCamera:
    """The home camera as fx32 header values plus the fx.Camera built from them."""

    def __init__(self):
        half = math.radians(FOVY_DEG / 2)
        self.fovy_sin = to_fx32(math.sin(half))
        self.fovy_cos = to_fx32(math.cos(half))
        self.near = to_fx32(NEAR)
        self.far = to_fx32(FAR)
        self.vertex_scale = to_fx32(VERTEX_SCALE)

        focal_y = (fx.SCREEN_H / 2) / math.tan(half)
        pitch = math.atan((fx.SCREEN_H / 2 - HORIZON_ROW) / focal_y)

        # Target: on the optical axis, midway (in depth) between the two platforms
        depths = []

        for side in (classic.SIDE_PLAYER, classic.SIDE_ENEMY):
            row = PLATFORM_CENTRE_ROW[side]
            below = pitch + math.atan((row - fx.SCREEN_H / 2) / focal_y)
            depths.append(CAM_HEIGHT / math.tan(below))

        dist = sum(depths) / 2
        self.cam_pos = (0, to_fx32(CAM_HEIGHT), to_fx32(CAM_Z))
        self.cam_target = (0, to_fx32(CAM_HEIGHT - dist * math.tan(pitch)), to_fx32(CAM_Z - dist))
        self.cam = self.camera(0)

    def camera(self, view):
        return fx.Camera(self.cam_pos, self.cam_target, self.fovy_sin, self.fovy_cos, self.near, self.far, self.vertex_scale, view)

    def pixel_to_world(self, depth):
        """World units per screen pixel of sideways motion at a view depth."""
        return depth / (self.cam.p00 * fx.SCREEN_W / 2)


# Centre row of each platform's art ellipse: the player art is the top half of an
# ellipse mirrored at sprite y 16, the enemy art a whole one around sprite y 0
PLATFORM_CENTRE_ROW = (classic.PLATFORM_HOME[0][1] + 16, classic.PLATFORM_HOME[1][1])


class Vertex:
    __slots__ = ("pos", "screen", "exact")

    def __init__(self, pos, screen, exact):
        self.pos = pos  # fx16 (x, y, z)
        self.screen = screen  # (sx, sy) whose texel this vertex shows
        self.exact = exact  # TRUE if placed on the pixel grid


class Mesh:
    def __init__(self, name, texture, flags, primitive, vertices):
        self.name = name
        self.texture = texture  # index into the piece's textures
        self.flags = flags
        self.primitive = primitive
        self.vertices = vertices  # [(Vertex, (s, t) in texels)]

    def num_polygons(self):
        n = len(self.vertices)

        if self.primitive == PRIM_QUADS:
            return n // 4

        if self.primitive == PRIM_QUAD_STRIP:
            return (n - 2) // 2

        if self.primitive == PRIM_TRIANGLES:
            return n // 3

        return n - 2


# GX_BEGIN_*
PRIM_TRIANGLES = 0
PRIM_QUADS = 1
PRIM_TRIANGLE_STRIP = 2
PRIM_QUAD_STRIP = 3

# BattleStageMeshFlag
FLAG_FOLLOW_PLATFORM_PLAYER = 1 << 0
FLAG_FOLLOW_PLATFORM_ENEMY = 1 << 1
FLAG_COLOR0_TRANSPARENT = 1 << 2
FLAG_FOLLOW_BG3_SCROLL = 1 << 3
FLAG_REPEAT_S = 1 << 4
FLAG_REPEAT_T = 1 << 5
FLAG_FLIP_S = 1 << 6
FLAG_FLIP_T = 1 << 7


# fx16 offsets Placer.exact tries around a vertex, nearest first. Near the middle of the
# screen y and z barely move a vertex sideways, so they need a wider range than x.
LATTICE = sorted(
    ((dx, dy, dz) for dx in range(-4, 5) for dy in range(-16, 17) for dz in range(-16, 17)),
    key=lambda d: sum(c * c for c in d),
)


class Placer:
    """Puts vertices on surfaces through the home camera."""

    def __init__(self, home):
        self.home = home
        self.cam = home.cam
        self.cache = {}

    def exact(self, x, y, surface):
        """Vertex on surface that the DS projects to pixel (x, y) plus less than
        VERTEX_WINDOW. surface(origin, direction) returns the world point on the ray."""
        key = (x, y, surface)

        if key in self.cache:
            return self.cache[key]

        best = None

        def score(v):
            _sx, _sy, sxf, syf, _w = self.cam.to_screen(v)
            fx_, fy = sxf - x, syf - y

            if 0 <= fx_ < VERTEX_WINDOW and 0 <= fy < VERTEX_WINDOW:
                return max(abs(fx_ - VERTEX_NUDGE), abs(fy - VERTEX_NUDGE))

            return None

        # Aim the ray, correcting for where the rounded vertex lands, then try the
        # fx16 lattice around it: close to the camera one fx16 step is more than
        # VERTEX_WINDOW, but some mix of steps in x, y and z lands inside it.
        aim_x, aim_y = x + VERTEX_NUDGE, y + VERTEX_NUDGE

        for _ in range(3):
            origin, direction = self.cam.ray(aim_x, aim_y)
            v = fx16_vec(surface(origin, direction))
            err = score(v)

            if err is not None:
                best = (err, v)
                break

            _sx, _sy, sxf, syf, _w = self.cam.to_screen(v)
            aim_x -= sxf - x - VERTEX_NUDGE
            aim_y -= syf - y - VERTEX_NUDGE

        if best is None:
            for d in LATTICE:
                cand = tuple(v[i] + d[i] for i in range(3))
                err = score(cand)

                if err is not None:
                    best = (err, cand)
                    break

        assert best is not None, f"no vertex projects to pixel ({x}, {y})"
        vertex = Vertex(best[1], (x + HALF_PIXEL, y + HALF_PIXEL), True)
        self.cache[key] = vertex
        return vertex

    def free(self, p):
        """Vertex at world point p; its texture coordinate follows its projection."""
        v = fx16_vec(p)
        _sx, _sy, sxf, syf, _w = self.cam.to_screen(v)
        return Vertex(v, (sxf - VERTEX_NUDGE + HALF_PIXEL, syf - VERTEX_NUDGE + HALF_PIXEL), False)

    def screen_point(self, sx, sy, surface):
        origin, direction = self.cam.ray(sx, sy)
        return surface(origin, direction)


def plane_y(h):
    def surface(origin, direction):
        t = (h - origin[1]) / direction[1]
        assert t > 0
        return tuple(origin[i] + t * direction[i] for i in range(3))

    surface.key = ("y", h)
    return surface


def plane_z(z):
    def surface(origin, direction):
        t = (z - origin[2]) / direction[2]
        assert t > 0
        return tuple(origin[i] + t * direction[i] for i in range(3))

    surface.key = ("z", z)
    return surface


def band_rows(first, last, forced=()):
    """Band edges from first to last so each band keeps the interpolation error under
    BAND_ERROR_PX, with every forced row an edge."""
    rows = [first]

    while rows[-1] < last:
        d = rows[-1] - HORIZON_ROW
        step = max(2, int(math.sqrt(4 * BAND_ERROR_PX * d)))
        nxt = min(rows[-1] + step, last)

        for f in sorted(forced):
            if rows[-1] < f < nxt:
                nxt = f
                break

        rows.append(nxt)

    return rows


def tex_coord(vertex, origin):
    return (vertex.screen[0] - origin[0], vertex.screen[1] - origin[1])


def strip_mesh(name, texture, flags, top, bottom, origin):
    """QUAD_STRIP over two rows of vertices (left to right)."""
    vertices = []

    for a, b in zip(top, bottom):
        vertices.append((a, tex_coord(a, origin)))
        vertices.append((b, tex_coord(b, origin)))

    return Mesh(name, texture, flags, PRIM_QUAD_STRIP, vertices)


# Backdrop piece textures
TEX_A = 0
TEX_B = 1
BACKDROP_FLAGS = FLAG_FOLLOW_BG3_SCROLL | FLAG_REPEAT_S | FLAG_FLIP_S
TEX_A_FLAGS = BACKDROP_FLAGS
TEX_B_FLAGS = BACKDROP_FLAGS | FLAG_REPEAT_T | FLAG_FLIP_T


class Backdrop:
    """Ground and panorama. meshes, plus the ground grid for inspection."""

    def __init__(self, home):
        self.home = home
        place = Placer(home)
        cam = home.cam
        ground = plane_y(0.0)

        # The frontal panorama is the plane through the ground line of WALL_BASE_ROW
        base_mid = place.screen_point(128 + VERTEX_NUDGE, WALL_BASE_ROW + VERTEX_NUDGE, ground)
        self.wall_z = base_mid[2]
        wall = plane_z(self.wall_z)

        rows = band_rows(WALL_BASE_ROW, HIDDEN_FROM_ROW, forced=set(ARC_EXTRA_ROWS) | {SPLIT_ROW, ARC_END_ROW})
        rows += [r for r in (160, 192, GROUND_LAST_ROW) if r > rows[-1]]
        self.rows = rows
        columns = list(range(0, fx.SCREEN_W + 1, COLUMN_PX))

        # On-screen ground grid; the base row is shared with the panorama
        grid = {}

        for y in rows:
            for x in columns:
                if y < HIDDEN_FROM_ROW or x in (0, fx.SCREEN_W):
                    grid[x, y] = place.exact(x, y, ground)
                else:
                    grid[x, y] = place.free(place.screen_point(x + VERTEX_NUDGE, y + VERTEX_NUDGE, ground))

        # Row k's ground line has constant z (the camera has no yaw or roll)
        row_z = [world_of(grid[fx.SCREEN_W, y].pos)[2] for y in rows]

        # Arc: starts at the frontal panorama's edge, bends toward the camera
        edge_x = world_of(grid[fx.SCREEN_W, WALL_BASE_ROW].pos)[0]
        centre_z = self.wall_z + ARC_RADIUS
        end_k = rows.index(ARC_END_ROW)

        def arc_x(z):
            c = (centre_z - z) / ARC_RADIUS
            return edge_x + ARC_RADIUS * math.sqrt(max(0.0, 1 - c * c))

        arc_end_x = arc_x(row_z[end_k])

        # Side ground: row lines from the frustum edge out to the arc, or beyond its end
        sides = {}

        for sign in (1, -1):
            edge_col = fx.SCREEN_W if sign > 0 else 0

            for k, y in enumerate(rows):
                z = row_z[k]
                inner = world_of(grid[edge_col, y].pos)

                if k <= end_k:
                    outer_x = arc_x(z)
                else:
                    depth = cam.world_to_view((0, 0, z))[2] * -1
                    px_to_x = depth / (cam.p00 * 128)
                    outer_x = min(max(arc_end_x, (GROUND_FAR_X - 128) * px_to_x), (MAX_TEXCOORD - 128) * px_to_x)

                line = [grid[edge_col, y]]

                for i in range(1, SIDE_SEGMENTS + 1):
                    x = inner[0] + (sign * outer_x - inner[0]) * i / SIDE_SEGMENTS
                    line.append(place.free((x, 0.0, z)))

                sides[sign, k] = line

        self.meshes = []

        # Ground bands, one strip each from the far left to the far right
        for k in range(len(rows) - 1):
            y0, y1 = rows[k], rows[k + 1]
            texture = TEX_A if y1 <= SPLIT_ROW else TEX_B
            origin = (0, 0) if texture == TEX_A else (0, TEX_B_FIRST_ROW)
            flags = TEX_A_FLAGS if texture == TEX_A else TEX_B_FLAGS

            def full_row(kk, yy):
                return sides[-1, kk][::-1] + [grid[x, yy] for x in columns[1:-1]] + sides[1, kk]

            top, bottom = full_row(k, y0), full_row(k + 1, y1)
            # The first band's far edge collapses to a point at each end (the arc starts
            # there); quads with two equal vertices are triangles, which is fine
            self.meshes.append(strip_mesh(f"ground {y0}-{y1}", texture, flags, top, bottom, origin))

        # Panorama: frontal part on the wall plane, curved part through the side
        # ground's outer ends. Rows are horizontal lines (constant height).
        # Everything above screen row 0 shows texture row 0 (t clamps), so one band
        # covers it
        wall_rows = list(range(WALL_BASE_ROW, 0, -WALL_ROW_STEP)) + [0, WALL_TOP_ROW]
        wall_grid = {}

        for y in wall_rows:
            for x in columns:
                if y == WALL_BASE_ROW:
                    wall_grid[x, y] = grid[x, y]
                elif y >= 0 or x in (0, fx.SCREEN_W):
                    wall_grid[x, y] = place.exact(x, y, wall)
                else:
                    wall_grid[x, y] = place.free(place.screen_point(x + VERTEX_NUDGE, y + VERTEX_NUDGE, wall))

        heights = [world_of(wall_grid[fx.SCREEN_W, y].pos)[1] for y in wall_rows]

        def wall_row(j):
            y = wall_rows[j]
            line = []

            for sign in (-1, 1):
                arc = []

                for k in range(1, end_k + 1):
                    outer = world_of(sides[sign, k][-1].pos)
                    arc.append(sides[sign, k][-1] if j == 0 else place.free((outer[0], heights[j], outer[2])))

                if sign < 0:
                    line += arc[::-1]
                    line += [wall_grid[x, y] for x in columns]
                else:
                    line += arc

            return line

        for j in range(len(wall_rows) - 1):
            top, bottom = wall_row(j + 1), wall_row(j)
            self.meshes.append(strip_mesh(f"panorama {wall_rows[j + 1]}-{wall_rows[j]}", TEX_A, TEX_A_FLAGS, top, bottom, (0, 0)))

        self.num_polygons = sum(m.num_polygons() for m in self.meshes)


class PlatformDisc:
    """One platform: a disc PLATFORM_HEIGHT above the ground whose home projection plus
    its side band covers the platform art, both textured through the home camera."""

    def __init__(self, home, side, art):
        self.home = home
        self.side = side
        self.art = art
        place = Placer(home)
        disc = plane_y(PLATFORM_HEIGHT)
        hx, hy = classic.PLATFORM_HOME[side]
        origin = (hx - PLATFORM_TEX_ORIGIN[side][0], hy - PLATFORM_TEX_ORIGIN[side][1])

        # Opaque extent of each screen row of the art; the player's is mirrored below
        # sprite y 16 like its texture (FLIP_T)
        extents = {}

        for (x, y), index in art.pixels.items():
            if index == 0:
                continue

            rows = [y]

            if side == classic.SIDE_PLAYER:
                rows.append(31 - y)

            for yy in rows:
                lo, hi = extents.get(yy + hy, (999, -999))
                extents[yy + hy] = (min(lo, x + hx), max(hi, x + hx))

        art_top, art_bottom = min(extents), max(extents)
        band_px = self.band_pixels(art_bottom)

        # Disc rows. The disc covers pixel rows (first, last]; the band below its front
        # edge covers the rest of the art.
        last = art_bottom - max(0, int(band_px) - 1)
        rows = [art_top - 1]
        step = PLATFORM_ROW_STEP[side]

        while rows[-1] < last:
            s = step if rows[-1] < HIDDEN_FROM_ROW else PLATFORM_HIDDEN_ROW_STEP
            rows.append(min(rows[-1] + s, last))

        def extent(k):
            lo_row = rows[k - 1] if k > 0 else rows[k]
            hi_row = rows[k + 1] if k + 1 < len(rows) else art_bottom
            span = [extents[r] for r in range(lo_row, hi_row + 1) if r in extents]
            return min(s[0] for s in span) - 1, max(s[1] for s in span) + 1

        def vertex(x, y):
            if y < HIDDEN_FROM_ROW:
                return place.exact(x, y, disc)

            return place.free(place.screen_point(x + VERTEX_NUDGE, y + VERTEX_NUDGE, disc))

        # Every disc row has the same columns, so each polygon's sides are vertical at
        # home: DeSmuME starts a span with the attributes of its exact left edge, so on
        # a slanted side the texels shift by the edge's fraction. The corners outside
        # the ellipse are transparent.
        n = PLATFORM_COLUMNS[side]
        lo = min(extent(k)[0] for k in range(len(rows)))
        hi = max(extent(k)[1] for k in range(len(rows)))
        xs = [int(round(lo + (hi - lo) * i / n)) for i in range(n + 1)]
        grid = [[vertex(x, y) for x in xs] for y in rows]

        self.rows = rows
        follow = FLAG_FOLLOW_PLATFORM_PLAYER if side == classic.SIDE_PLAYER else FLAG_FOLLOW_PLATFORM_ENEMY
        flags = follow | FLAG_COLOR0_TRANSPARENT

        if side == classic.SIDE_PLAYER:
            flags |= FLAG_REPEAT_T | FLAG_FLIP_T

        self.flags = flags
        self.meshes = []
        name = ("player", "enemy")[side]

        for k in range(len(rows) - 1):
            self.meshes.append(strip_mesh(f"{name} disc {rows[k]}-{rows[k + 1]}", side, flags, grid[k], grid[k + 1], origin))

        # Side band along the front half of the rim, from the widest row round the
        # front: top at the art's outline on the disc, bottom on (just under) the ground,
        # on the pixel grid where the home view sees it. The back half is always behind
        # the disc, and would show through its transparent margin. At home the disc
        # covers the band down to the last disc row; below it the band's front is
        # rectangles on the disc's columns.
        widths = [extent(k)[1] - extent(k)[0] for k in range(len(rows))]
        widest = widths.index(max(widths))
        front = range(widest, len(rows))
        lo_last, hi_last = extent(len(rows) - 1)
        rim = (
            [vertex(extent(k)[0], rows[k]) for k in front]
            + [vertex(x, rows[-1]) for x in xs if lo_last < x < hi_last]
            + [vertex(extent(k)[1], rows[k]) for k in reversed(front)]
        )
        ground = plane_y(PLATFORM_BAND_BOTTOM)
        tops, bottoms = [], []

        for v in rim:
            p = world_of(v.pos)
            below = (p[0], PLATFORM_BAND_BOTTOM, p[2])
            _sx, _sy, sxf, syf, _w = home.cam.to_screen(fx16_vec(below))
            x, y = int(round(sxf - VERTEX_NUDGE)), int(round(syf - VERTEX_NUDGE))

            if y < HIDDEN_FROM_ROW:
                bottoms.append(place.exact(x, y, ground))
            else:
                bottoms.append(place.free(below))

            tops.append(v)

        self.meshes.append(strip_mesh(f"{name} band", side, flags, tops, bottoms, origin))
        self.band_px = band_px
        self.num_polygons = sum(m.num_polygons() for m in self.meshes)

        # Where the disc is in view space, for platformPixelToWorld
        centre = place.screen_point(hx + VERTEX_NUDGE, PLATFORM_CENTRE_ROW[side] + VERTEX_NUDGE, disc)
        self.depth = -home.cam.world_to_view(centre)[2]

    def band_pixels(self, row):
        """Screen height of the side band at a row near the platform's front."""
        cam = self.home.cam
        hx = classic.PLATFORM_HOME[self.side][0]
        top = Placer(self.home).screen_point(hx, row, plane_y(PLATFORM_HEIGHT))
        _x, y0, _w = cam.project_float(top)
        _x, y1, _w = cam.project_float((top[0], 0.0, top[2]))
        return y1 - y0


class Arena:
    def __init__(self):
        self.home = HomeCamera()
        self.backdrop = Backdrop(self.home)
        self.platforms = [PlatformDisc(self.home, side, classic.Platform(side, 0)) for side in (classic.SIDE_PLAYER, classic.SIDE_ENEMY)]
        self.pixel_to_world = [self.home.pixel_to_world(p.depth) for p in self.platforms]


if __name__ == "__main__":
    arena = Arena()
    home = arena.home
    print("camPos", [c / FX32_ONE for c in home.cam_pos], "camTarget", [c / FX32_ONE for c in home.cam_target])
    print("ground rows", arena.backdrop.rows)
    print("wall z", arena.backdrop.wall_z)

    for m in arena.backdrop.meshes:
        print(f"  {m.name:24} verts {len(m.vertices):4} polys {m.num_polygons()}")

    for p in arena.platforms:
        print("platform", p.side, "rows", p.rows, "band px %.2f" % p.band_px, "depth %.2f" % p.depth)

        for m in p.meshes:
            print(f"  {m.name:24} verts {len(m.vertices):4} polys {m.num_polygons()}")

    total_polys = arena.backdrop.num_polygons + sum(p.num_polygons for p in arena.platforms)
    total_verts = sum(len(m.vertices) for m in arena.backdrop.meshes) + sum(len(m.vertices) for p in arena.platforms for m in p.meshes)
    print("polygons", total_polys, "vertices", total_verts, "meshes", len(arena.backdrop.meshes) + sum(len(p.meshes) for p in arena.platforms))
    print("pixelToWorld", arena.pixel_to_world)

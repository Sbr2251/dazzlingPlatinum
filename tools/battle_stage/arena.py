"""Arena geometry: the home camera, the backdrop pieces (ground or floor, panorama or
walls) of every BACKGROUND_* and the platform pieces (two platform discs) of every
TERRAIN_*.

Every texture coordinate the home view can see is the home-camera screen position of
its vertex, so at the home pose each pixel shows the texel the classic BG3 or platform
OBJ shows there. To make that exact both on the DS, whose rasterizer uses integer
vertex coordinates, and in DeSmuME, which keeps 1/16 pixel, the vertices the home view
can see are placed so they project within VERTEX_WINDOW right of and below integers
X, Y, and get the texture coordinate
(X + HALF_PIXEL, Y + HALF_PIXEL) minus the texture's origin. fx.py projects every
vertex with the DS integer math to check where it lands.

World units: y is up, the ground is y = 0 and the camera looks toward -z. A vertex is
stored as fx16 world / VERTEX_SCALE.

Screen-affine texture coordinates are only exact where perspective-correct
interpolation is linear. On the ground, the platforms and the frontal part of the
panorama that holds along screen rows (no camera yaw), so columns can be wide; down a
column the error of a band h pixels tall and d pixels below the horizon is about
h * h / (4 * d), so bands get taller with distance from the horizon.

Every mesh is LIT (it sends normals; the backdrop piece's atmosphere lights it) and
FOG. Normals: ground, floor and disc tops face up, the frontal panorama or back wall
faces the camera (+z), the outdoor panorama's curved sides face the centre of their
arc, room side walls face into the room and the disc side bands face outward.
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

# Backdrop kinds. OUTDOOR, CAVE and VOID: the ground plus a panorama that stands on it
# at the base row and curves toward the camera beyond the home frustum. ROOM: a floor
# plus a box of walls, the back wall standing on the floor at the base row and a side
# wall on each side, where the back wall's base meets the frustum edge.
KIND_OUTDOOR = 0
KIND_CAVE = 1
KIND_ROOM = 2
KIND_VOID = 3
KIND_NAMES = ("outdoor", "cave", "room", "void")

# Per BACKGROUND_*: the screen row where the image's ground or floor meets its
# panorama or back wall (the first row that is clearly ground), and the kind
BACKGROUND_BASE_ROW = (
    57, 57, 56, 53, 58, 48,  # plain, water, city, forest, mountain, snow
    58, 62, 64,  # indoors 1..3
    50, 52, 52,  # caves 1..3
    57, 57, 57, 57, 46,  # Aaron, Bertha, Flint, Lucian, Cynthia
    52,  # Distortion World
    62, 64, 62, 62, 62,  # Battle Tower, Factory, Arcade, Castle, Hall
)
BACKGROUND_KIND = (
    (KIND_OUTDOOR,) * 6 + (KIND_ROOM,) * 3 + (KIND_CAVE,) * 3 + (KIND_ROOM,) * 5 + (KIND_VOID,) + (KIND_ROOM,) * 5
)
BACKGROUND_MAX = len(BACKGROUND_BASE_ROW)
BACKGROUND_WATER = 1

# Water: the ground bands from WATER_FIRST_ROW_BELOW rows under the base row sway
WATER_BACKGROUNDS = (BACKGROUND_WATER,)
WATER_FIRST_ROW_BELOW = 4
WATER_SCROLL_AMPLITUDE = (3, 1)  # texels, s and t
# Arena draws: the battle draws the 3D scene at 30 fps, so 105 draws = 3.5 s (210 VBlanks)
WATER_SCROLL_PERIOD = 105

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
ARC_EXTRA_ROWS = (2, 4)  # extra ground rows below the base row, to smooth the start of the curve

# Band height rule: max interpolation error in pixels
BAND_ERROR_PX = 0.25

# Platforms
PLATFORM_HEIGHT = 0.1  # the disc floats this high; its side band hangs to the ground
PLATFORM_BAND_BOTTOM = -0.02  # a little under the ground, so the ground can't z-fight it
PLATFORM_COLUMNS = (8, 5)  # vertices per disc row, minus one: player, enemy
PLATFORM_ROW_STEP = (4, 5)  # disc rows in the visible part
PLATFORM_HIDDEN_ROW_STEP = 8
PLATFORM_TEX_SIZE = ((256, 32), (128, 64))
# Texel of the sprite's origin in the platform texture. The enemy art (sprite rows
# -16..15 at most: the grass tufts use row -16) is placed at t 8..39 so the texture's
# clamped edge rows are transparent; the player's texture mirrors at t 32 (sprite row
# 16) instead.
PLATFORM_TEX_ORIGIN = ((128, 16), (64, 24))


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
    def __init__(self, name, texture, flags, primitive, vertices, scroll_amplitude=(0, 0), scroll_period=1):
        self.name = name
        self.texture = texture  # index into the piece's textures
        self.flags = flags | FLAG_LIT | FLAG_FOG
        self.primitive = primitive
        self.vertices = vertices  # [(Vertex, (s, t) in texels, unit normal)]
        self.scroll_amplitude = scroll_amplitude
        self.scroll_period = scroll_period

        if scroll_amplitude != (0, 0):
            self.flags |= FLAG_SCROLL

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
FLAG_LIT = 1 << 8
FLAG_FOG = 1 << 9
FLAG_SCROLL = 1 << 10

UP = (0.0, 1.0, 0.0)
TOWARD_CAMERA = (0.0, 0.0, 1.0)


def normalize(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


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

        if best is None:
            # Close to the camera the DS projection reaches only some sub-pixel
            # positions; search wider, keeping the smallest move
            found = []

            for dx in range(-12, 13):
                for dy in range(-40, 41):
                    for dz in range(-40, 41):
                        cand = (v[0] + dx, v[1] + dy, v[2] + dz)
                        err = score(cand)

                        if err is not None:
                            found.append((dx * dx + dy * dy + dz * dz, err, cand))

            if found:
                _n, err, cand = min(found)
                best = (err, cand)

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


def strip_mesh(name, texture, flags, top, bottom, origin, normal=UP, **kw):
    """QUAD_STRIP over two rows of vertices (left to right). A row entry is a Vertex,
    which gets normal, or a (Vertex, normal) pair."""
    vertices = []

    def entry(v):
        if isinstance(v, tuple):
            return (v[0], tex_coord(v[0], origin), v[1])

        return (v, tex_coord(v, origin), normal)

    for a, b in zip(top, bottom):
        vertices.append(entry(a))
        vertices.append(entry(b))

    return Mesh(name, texture, flags, PRIM_QUAD_STRIP, vertices, **kw)


# Backdrop piece textures
TEX_A = 0
TEX_B = 1
BACKDROP_FLAGS = FLAG_FOLLOW_BG3_SCROLL | FLAG_REPEAT_S | FLAG_FLIP_S
TEX_A_FLAGS = BACKDROP_FLAGS
TEX_B_FLAGS = BACKDROP_FLAGS | FLAG_REPEAT_T | FLAG_FLIP_T


class Backdrop:
    """Ground or floor plus panorama or walls of one background. meshes, plus the ground
    grid for inspection."""

    def __init__(self, home, background=0):
        self.home = home
        self.background = background
        self.kind = BACKGROUND_KIND[background]
        self.base_row = base_row = BACKGROUND_BASE_ROW[background]
        room = self.kind == KIND_ROOM
        place = Placer(home)
        cam = home.cam
        ground = plane_y(0.0)

        # The frontal panorama or back wall is the plane through the ground line of the
        # base row
        base_mid = place.screen_point(128 + VERTEX_NUDGE, base_row + VERTEX_NUDGE, ground)
        self.wall_z = base_mid[2]
        wall = plane_z(self.wall_z)

        extra = {base_row + d for d in ARC_EXTRA_ROWS}
        water_row = base_row + WATER_FIRST_ROW_BELOW if background in WATER_BACKGROUNDS else None
        forced = extra | {SPLIT_ROW} | ({ARC_END_ROW} if not room else set())
        rows = band_rows(base_row, HIDDEN_FROM_ROW, forced=forced)
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

        # Outdoors the panorama's arc starts at the frontal part's edge and bends toward
        # the camera; in a room the side walls stand straight at that edge
        edge_x = world_of(grid[fx.SCREEN_W, base_row].pos)[0]
        centre_z = self.wall_z + ARC_RADIUS
        end_k = len(rows) - 1 if room else rows.index(ARC_END_ROW)
        self.edge_x = edge_x

        def arc_x(z):
            if room:
                return edge_x

            c = (centre_z - z) / ARC_RADIUS
            return edge_x + ARC_RADIUS * math.sqrt(max(0.0, 1 - c * c))

        arc_end_x = arc_x(row_z[end_k])

        # Side ground: row lines from the frustum edge out to the arc (or the side
        # wall), or beyond the arc's end
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
            scroll = {}

            if water_row is not None and y0 >= water_row:
                scroll = dict(scroll_amplitude=WATER_SCROLL_AMPLITUDE, scroll_period=WATER_SCROLL_PERIOD)

            def full_row(kk, yy):
                return sides[-1, kk][::-1] + [grid[x, yy] for x in columns[1:-1]] + sides[1, kk]

            top, bottom = full_row(k, y0), full_row(k + 1, y1)
            # The first band's far edge collapses to a point at each end (the arc starts
            # there); quads with two equal vertices are triangles, which is fine
            self.meshes.append(strip_mesh(f"ground {y0}-{y1}", texture, flags, top, bottom, origin, UP, **scroll))

        # Panorama or walls: frontal part on the wall plane, the arc or the side walls
        # through the side ground's outer ends. Rows are horizontal lines (constant
        # height). Everything above screen row 0 shows texture row 0 (t clamps), so one
        # band covers it
        wall_rows = list(range(base_row, 0, -WALL_ROW_STEP)) + [0, WALL_TOP_ROW]
        wall_grid = {}

        for y in wall_rows:
            for x in columns:
                if y == base_row:
                    wall_grid[x, y] = grid[x, y]
                elif y >= 0 or x in (0, fx.SCREEN_W):
                    wall_grid[x, y] = place.exact(x, y, wall)
                else:
                    wall_grid[x, y] = place.free(place.screen_point(x + VERTEX_NUDGE, y + VERTEX_NUDGE, wall))

        heights = [world_of(wall_grid[fx.SCREEN_W, y].pos)[1] for y in wall_rows]
        self.wall_top = heights[-1]

        # Side walls aren't in the home view, so their texture coordinates don't come
        # from it: the back wall's texture continues round the corner at the density it
        # has at the corner (mirrored by FLIP_S), rows at the corner's rows
        corner_depth = -cam.world_to_view((edge_x, 0.0, self.wall_z))[2]
        texels_per_unit = cam.p00 * (fx.SCREEN_W / 2) / corner_depth

        def side_wall_vertex(sign, j, k):
            p = (sign * edge_x, heights[j], row_z[k])
            corner = wall_grid[fx.SCREEN_W if sign > 0 else 0, wall_rows[j]]
            s = corner.screen[0] + sign * (self.wall_z - p[2]) * texels_per_unit
            return Vertex(fx16_vec(p), (s, corner.screen[1]), False)

        def arc_normal(sign, v):
            x, _y, z = world_of(v.pos)
            return normalize((sign * edge_x - x, 0.0, centre_z - z))

        def wall_row(j):
            y = wall_rows[j]
            line = []

            for sign in (-1, 1):
                arc = []

                for k in range(1, end_k + 1):
                    if room:
                        arc.append((side_wall_vertex(sign, j, k), (-sign, 0.0, 0.0)))
                    else:
                        outer = world_of(sides[sign, k][-1].pos)
                        v = sides[sign, k][-1] if j == 0 else place.free((outer[0], heights[j], outer[2]))
                        arc.append((v, arc_normal(sign, v)))

                corner = wall_grid[fx.SCREEN_W if sign > 0 else 0, y]

                if sign < 0:
                    line += arc[::-1]

                    # A room's corner is a crease: repeat the corner vertex with each
                    # wall's normal (the quad between them has no area)
                    if room:
                        line.append((corner, (1.0, 0.0, 0.0)))

                    line += [(wall_grid[x, y], TOWARD_CAMERA) for x in columns]
                else:
                    if room:
                        line.append((corner, (-1.0, 0.0, 0.0)))

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
        tex_left, tex_right = origin[0], origin[0] + PLATFORM_TEX_SIZE[side][0]

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
            nxt = rows[-1] + s

            # A polygon with a free (hidden) vertex row drifts in DeSmuME on the rows it
            # spreads over, so the visible rows end on an exact row
            if rows[-1] < HIDDEN_FROM_ROW < nxt:
                nxt = HIDDEN_FROM_ROW

            rows.append(min(nxt, last))

        def extent(k):
            lo_row = rows[k - 1] if k > 0 else rows[k]
            hi_row = rows[k + 1] if k + 1 < len(rows) else art_bottom
            span = [extents[r] for r in range(lo_row, hi_row + 1) if r in extents]
            # One transparent column of margin, but never past the texture's edge,
            # where the clamp would repeat the edge texels
            return max(tex_left, min(s[0] for s in span) - 1), min(tex_right, max(s[1] for s in span) + 1)

        def vertex(x, y):
            if y <= HIDDEN_FROM_ROW:
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

        # The band faces outward: the normal of the ellipse through the rim, whose
        # centre and semi-axes come from the rim's extent
        rim_world = [world_of(v.pos) for v in rim]
        cx = (min(p[0] for p in rim_world) + max(p[0] for p in rim_world)) / 2
        cz = min(p[2] for p in rim_world)  # the widest row, at the back of the band
        ax = max(abs(p[0] - cx) for p in rim_world)
        az = max(max(p[2] - cz for p in rim_world), 1e-3)

        def band_normal(p):
            return normalize(((p[0] - cx) / (ax * ax), 0.0, (p[2] - cz) / (az * az)))

        for v in rim:
            p = world_of(v.pos)
            below = (p[0], PLATFORM_BAND_BOTTOM, p[2])
            _sx, _sy, sxf, syf, _w = home.cam.to_screen(fx16_vec(below))
            x, y = int(round(sxf - VERTEX_NUDGE)), int(round(syf - VERTEX_NUDGE))

            n = band_normal(p)

            if y < HIDDEN_FROM_ROW:
                bottoms.append((place.exact(x, y, ground), n))
            else:
                bottoms.append((place.free(below), n))

            tops.append((v, n))

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


def platform_depths(home):
    """View depth of each platform's centre."""
    out = []

    for side in (classic.SIDE_PLAYER, classic.SIDE_ENEMY):
        hx = classic.PLATFORM_HOME[side][0]
        centre = Placer(home).screen_point(hx + VERTEX_NUDGE, PLATFORM_CENTRE_ROW[side] + VERTEX_NUDGE, plane_y(PLATFORM_HEIGHT))
        out.append(-home.cam.world_to_view(centre)[2])

    return out


class Arena:
    """The backdrop of a background and the platforms of a terrain. A platform whose
    art is empty (TERRAIN_GIRATINA's enemy side) is None."""

    def __init__(self, terrain=0, background=0, home=None):
        self.home = home or HomeCamera()
        self.backdrop = Backdrop(self.home, background) if background is not None else None
        self.platforms = []

        if terrain is not None:
            for side in (classic.SIDE_PLAYER, classic.SIDE_ENEMY):
                art = classic.Platform(side, terrain)
                self.platforms.append(None if art.is_empty() else PlatformDisc(self.home, side, art))

        self.pixel_to_world = [self.home.pixel_to_world(d) for d in platform_depths(self.home)]


if __name__ == "__main__":
    import sys

    arena = Arena(int(sys.argv[2]) if len(sys.argv) > 2 else 0, int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    home = arena.home
    print("camPos", [c / FX32_ONE for c in home.cam_pos], "camTarget", [c / FX32_ONE for c in home.cam_target])
    print("ground rows", arena.backdrop.rows)
    print("wall z", arena.backdrop.wall_z)

    for m in arena.backdrop.meshes:
        print(f"  {m.name:24} verts {len(m.vertices):4} polys {m.num_polygons()}")

    for p in filter(None, arena.platforms):
        print("platform", p.side, "rows", p.rows, "band px %.2f" % p.band_px, "depth %.2f" % p.depth)

        for m in p.meshes:
            print(f"  {m.name:24} verts {len(m.vertices):4} polys {m.num_polygons()}")

    plats = list(filter(None, arena.platforms))
    total_polys = arena.backdrop.num_polygons + sum(p.num_polygons for p in plats)
    total_verts = sum(len(m.vertices) for m in arena.backdrop.meshes) + sum(len(m.vertices) for p in plats for m in p.meshes)
    print("polygons", total_polys, "vertices", total_verts, "meshes", len(arena.backdrop.meshes) + sum(len(p.meshes) for p in plats))
    print("pixelToWorld", arena.pixel_to_world)

#!/usr/bin/env python3
"""Software-renders battle_stage.narc the way the renderer draws it, to check the arenas
without building the ROM.

For one background (--bg, default BACKGROUND_PLAIN) with one terrain (--terrain,
default the terrain that usually goes with it) it renders the home pose and the three
debug views (L+R+B in battle) at every time of day (or --tod), compares the home pose
with the classic 2D scene (BG3 + platform OBJs, the palettes of the same
ov16_0223EC04 column) and prints, per time of day and raster:

    mean, max    absolute difference home vs classic over rows 0..143 (BG1 covers
                 the rest), per channel on the 0..255 scale
    differ       number of pixels that differ in rows 0..143
    holes        pixels nothing was drawn to in view 0 (rows 0..143) and views 1..3

--all does that for every background with its usual terrain at the three times of day,
and for every terrain on BACKGROUND_PLAIN at day. Images go to --out (default
/tmp/battle_stage_preview):

    sheet_bgNN_tT.png        (one background) classic | home | diff above views 1..3
    sheet_bgNN.png           (--all) classic | home | diff per time of day, then views
                             1..3 at day
    contact_home_<tod>.png   (--all) the home pose of every background
    contact_view<N>.png      (--all) debug view N of every background at day
    contact_terrains.png     (--all) every terrain on BACKGROUND_PLAIN at day

In the diff images grey is equal, red is different (brighter = larger difference),
magenta is a hole; rows 144+ are dimmed. Holes are magenta in the renders as well.

The rasterizer follows the DS closely enough for pixel checks: the same integer
vertex transform as fx.py (with the renderer's depth remap), near/far clipping,
scanline edge walking with perspective correct interpolation of texture coordinates
and vertex colours, a depth test, palette index 0 transparency, the texture
clamp/repeat/flip modes, and the arena atmosphere:

    lighting   LIT meshes get the DS vertex light of the column's BattleStageFileLighting,
               min(31, emission + ambient*light + diffuse*light*max(0, -L.N)), from the
               fx10 normal; the texel is modulated by the vertex colour on 6 bits,
               ((texel + 1) * (vertex + 1) - 1) >> 6
    fog        FOG pixels blend toward the fog colour by the density the fog table gives
               their 15-bit depth (GX_BUFFERMODE_Z), interpolated between entries like
               DeSmuME; density 127 counts as 128
    sway       with --frame N (arena draws, 30 per second), SCROLL meshes shift their
               texture by amplitude * (sin, cos)(2pi N / period) texels (default: no
               sway)

--raster picks how screen positions, spans and depth work:

    desmume   like the soft rasterizer of DeSmuME 0.9.12 (py-desmume, which the
              critic runs; the default): positions rounded to 1/16 pixel, and a
              span's first pixel gets the attributes of the exact edge point, not of
              the pixel, so a vertex just right of a pixel boundary shifts the span's
              texels one pixel right; fog depth (z/w + 1) * 0x4000
    hardware  positions truncated to whole pixels, attributes taken at each pixel,
              fog depth z/w * 0x4000 + 0x3FFF, like the DS
    both      both of the above (images from desmume)

Needs numpy and PIL (~/.venvs/desmume/bin/python).
"""

import argparse
import math
import os
import time

import numpy as np
from PIL import Image, ImageDraw

import atmosphere
import classic
import fx
import nitro
import stage_format as sf

HOME_VISIBLE_ROWS = 144  # BG1 covers the rest
HOLE_RGB = (255, 0, 255)
W, H = fx.SCREEN_W, fx.SCREEN_H
TOD_NAMES = classic.TIMES_OF_DAY
RASTERS = ("desmume", "hardware")

# The terrain each background usually comes with
USUAL_TERRAIN = (
    2,  # PLAIN: GRASS
    7,  # WATER: WATER
    0,  # CITY: PLAIN
    2,  # FOREST: GRASS
    4,  # MOUNTAIN: MOUNTAIN
    6,  # SNOW: SNOW
    9, 9, 9,  # INDOORS_*: BUILDING
    5, 5, 5,  # CAVE_*: CAVE
    12, 13, 14, 15, 16,  # Elite Four and Champion
    23,  # DISTORTION_WORLD: GIRATINA (no enemy platform)
    18, 19, 20, 21, 22,  # Battle Frontier
)


def polygons(mesh):
    """Vertex index lists of the DS polygons a mesh makes."""
    n = len(mesh.vertices)

    if mesh.primitive == 0:
        return [[i, i + 1, i + 2] for i in range(0, n - 2, 3)]

    if mesh.primitive == 1:
        return [[i, i + 1, i + 2, i + 3] for i in range(0, n - 3, 4)]

    if mesh.primitive == 2:
        return [[i, i + 1, i + 2] for i in range(n - 2)]

    return [[i, i + 1, i + 3, i + 2] for i in range(0, n - 3, 2)]


def wrap(coord, size, repeat, flip):
    """Texel index along one axis for integer coords (numpy)."""
    if not repeat:
        return np.clip(coord, 0, size - 1)

    period = coord // size
    inside = coord % size

    if flip:
        return np.where(period % 2 == 1, size - 1 - inside, inside)

    return inside


def clip_polygon(verts, plane):
    """Sutherland-Hodgman against plane(v) >= 0; verts are tuples of floats with the
    clip coordinates first."""
    out = []

    for i, a in enumerate(verts):
        b = verts[(i + 1) % len(verts)]
        da, db = plane(a), plane(b)

        if da >= 0:
            out.append(a)

        if (da >= 0) != (db >= 0):
            t = da / (da - db)
            out.append(tuple(a[k] + (b[k] - a[k]) * t for k in range(len(a))))

    return out


def to6(c5):
    """DeSmuME's 5 to 6 bit colour expansion (numpy or int)."""
    return np.where(c5 > 0, c5 * 2 + 1, 0) if isinstance(c5, np.ndarray) else (c5 * 2 + 1 if c5 else 0)


def fog_density_lut(atm):
    """Density 0..128 for every 15-bit depth, like DeSmuME builds it."""
    step = 0x400 >> atm.fog_shift
    shift_inv = 10 - atm.fog_shift
    table = atm.fog_table
    offset = atm.fog_offset
    lut = np.empty(0x8000, np.int32)

    for depth in range(0x8000):
        if depth < offset + step:
            d = table[0]
        elif depth >= offset + step * 32:
            d = table[31]
        else:
            value = (depth - offset) % step
            j = ((depth - offset) >> shift_inv) - 1
            d = (value * table[j + 1] + (step - value) * table[j]) >> shift_inv

        lut[depth] = 128 if d == 127 else d

    return lut


class Renderer:
    def __init__(self, pieces, palettes, raster="desmume", column=0, frame=None):
        """pieces: [backdrop piece, platform piece or None]; palettes: {"bg" or
        ("platform", side): (N, 3) 5-bit colours}; column: the lighting column
        (ov16_0223EC04); frame: sway frame or None."""
        self.pieces = [p for p in pieces if p is not None]
        self.palettes = palettes
        self.raster = raster
        self.frame = frame
        atm = pieces[0].atmosphere
        self.lighting = atm.lighting[column] if atm else None
        self.fog = atm if atm and atm.fog_enabled else None
        self.fog_lut = fog_density_lut(atm) if self.fog else None

    def render(self, camera):
        """(rgb888 image, covered mask) of one camera."""
        col6 = np.zeros((H, W, 3), np.int32)
        depth = np.full((H, W), np.inf)
        fog_bit = np.zeros((H, W), bool)
        covered = np.zeros((H, W), bool)
        self.num_polygons = 0

        for piece in self.pieces:
            for mesh in piece.meshes:
                tex = piece.textures[mesh.texture_index]
                pal = self.palette_for(tex, mesh)
                ds, dt = self.sway(mesh)
                clip = []

                for pos, tc, color, normal in mesh.vertices:
                    x, y, _z, w = camera.to_clip(pos)

                    if mesh.flags & sf.FLAG_LIT and self.lighting is not None:
                        c5 = atmosphere.vertex_color(self.lighting, sf.unpack_normal(normal))
                    else:
                        c5 = atmosphere.unrgb(color if not mesh.flags & sf.FLAG_LIT else 0x7FFF)

                    clip.append((x, y, camera.clip_depth(pos), w, tc[0] / sf.TEXCOORD_ONE + ds, tc[1] / sf.TEXCOORD_ONE + dt)
                                + tuple(to6(c) for c in c5))

                for poly in polygons(mesh):
                    verts = [clip[i] for i in poly]
                    verts = clip_polygon(verts, lambda v: v[2] + v[3])  # near: z >= -w
                    verts = clip_polygon(verts, lambda v: v[3] - v[2])  # far: z <= w

                    if len(verts) >= 3:
                        self.num_polygons += 1
                        self.draw(verts, tex, mesh.flags, pal, col6, depth, fog_bit, covered)

        if self.fog is not None:
            self.apply_fog(col6, depth, fog_bit & covered)

        c5 = col6 >> 1
        rgb = ((c5 << 3) | (c5 >> 2)).astype(np.uint8)
        rgb[~covered] = HOLE_RGB
        return rgb, covered

    def sway(self, mesh):
        if self.frame is None or not mesh.flags & sf.FLAG_SCROLL:
            return 0.0, 0.0

        a = 2 * math.pi * self.frame / mesh.scroll_period
        return mesh.scroll_amplitude[0] * math.sin(a), mesh.scroll_amplitude[1] * math.cos(a)

    def palette_for(self, tex, mesh):
        if tex.palette_source == sf.PALETTE_PLATFORM_OBJ:
            side = 1 if mesh.flags & sf.FLAG_FOLLOW_PLATFORM_ENEMY else 0
            return self.palettes.get(("platform", side), palette5(tex.palette))

        if tex.palette_source == sf.PALETTE_BG:
            return self.palettes.get("bg", palette5(tex.palette))

        return palette5(tex.palette)

    def fog_depth(self, ndc):
        if self.raster == "hardware":
            d = np.floor(ndc * 0x4000) + 0x3FFF
        else:
            d = np.floor((ndc + 1) * 0x4000)

        return np.clip(d, 0, 0x7FFF).astype(np.int64)

    def apply_fog(self, col6, depth, mask):
        density = self.fog_lut[self.fog_depth(np.where(mask, depth, 0))][mask][:, None]
        fog6 = np.array([to6(c) for c in atmosphere.unrgb(self.lighting.fog_color)], np.int32)
        col6[mask] = (fog6 * density + col6[mask] * (128 - density)) >> 7

    def screen(self, x, y, w):
        sx = (x + w) * W / (2 * w)
        sy = (w - y) * H / (2 * w)

        if self.raster == "hardware":
            return math.floor(sx), math.floor(sy)

        # DeSmuME keeps positions in 28.4 fixed point
        return math.floor(sx * 16 + 0.5) / 16, math.floor(sy * 16 + 0.5) / 16

    def draw(self, verts, tex, flags, pal, col6, depth, fog_bit, covered):
        # Screen vertices: x, y, then 1/w, s/w, t/w, z/w, r/w, g/w, b/w, linear in
        # screen space
        sv = []

        for x, y, z, w, s, t, r, g, b in verts:
            sx, sy = self.screen(x, y, w)
            sv.append((sx, sy, 1 / w, s / w, t / w, z / w, r / w, g / w, b / w))

        ys = [v[1] for v in sv]
        y_first = max(0, math.ceil(min(ys)))
        y_end = min(H, math.ceil(max(ys)))
        n = len(sv)
        nattr = len(sv[0])

        for py in range(y_first, y_end):
            hits = []

            for i in range(n):
                a, b = sv[i], sv[(i + 1) % n]

                if a[1] == b[1]:
                    continue

                if a[1] > b[1]:
                    a, b = b, a

                # rows ceil(ya) .. ceil(yb) - 1 belong to the edge
                if not math.ceil(a[1]) <= py < math.ceil(b[1]):
                    continue

                f = (py - a[1]) / (b[1] - a[1])
                hits.append(tuple(a[k] + (b[k] - a[k]) * f for k in range(nattr)))

            if len(hits) < 2:
                continue

            left = min(hits, key=lambda h: h[0])
            right = max(hits, key=lambda h: h[0])
            x0 = max(0, math.ceil(left[0]))
            x1 = min(W, math.ceil(right[0]))

            if x1 <= x0:
                continue

            px = np.arange(x0, x1)

            if self.raster == "hardware":
                start, span = left[0], right[0] - left[0]
            else:
                # DeSmuME spreads the edge values over the covered pixels
                start = math.ceil(left[0])
                span = math.ceil(right[0]) - start

            f = (px - start) / span if span > 0 else np.zeros(len(px))
            inv_w, s_w, t_w, z, r_w, g_w, b_w = [left[k] + (right[k] - left[k]) * f for k in range(2, nattr)]
            s = np.floor(s_w / inv_w).astype(np.int64)
            t = np.floor(t_w / inv_w).astype(np.int64)
            s = wrap(s, tex.width, flags & sf.FLAG_REPEAT_S, flags & sf.FLAG_FLIP_S)
            t = wrap(t, tex.height, flags & sf.FLAG_REPEAT_T, flags & sf.FLAG_FLIP_T)
            index = tex.array[t, s]

            visible = z < depth[py, x0:x1]

            if flags & sf.FLAG_COLOR0_TRANSPARENT:
                visible &= index != 0

            cols = px[visible]
            vtx6 = np.stack([np.clip(np.floor(c / inv_w + 1e-4), 0, 63) for c in (r_w, g_w, b_w)], axis=1).astype(np.int32)
            tex6 = to6(pal[index])
            out6 = ((tex6 + 1) * (vtx6 + 1) - 1) >> 6
            depth[py, cols] = z[visible]
            col6[py, cols] = out6[visible]
            fog_bit[py, cols] = bool(flags & sf.FLAG_FOG)
            covered[py, cols] = True


def texture_array(tex):
    if tex.format == sf.TEXFMT_PLTT256:
        return np.frombuffer(tex.data, np.uint8).reshape(tex.height, tex.width)

    packed = np.frombuffer(tex.data, np.uint8).reshape(tex.height, tex.width // 2)
    out = np.empty((tex.height, tex.width), np.uint8)
    out[:, 0::2] = packed & 0xF
    out[:, 1::2] = packed >> 4
    return out


def palette5(colors):
    """(256, 3) 5-bit colours of a GXRgb palette."""
    colors = list(colors) + [0] * (256 - len(colors))
    return np.array([atmosphere.unrgb(c) for c in colors], np.int32)


class Stage:
    """The NARC's pieces plus the classic art, cached per background and terrain."""

    def __init__(self, narc_path):
        self.members = nitro.read_narc(narc_path)
        assert len(self.members) == sf.NUM_MEMBERS
        self.cache = {}

    def piece(self, member):
        if member not in self.cache:
            piece = sf.read_piece(self.members[member])

            if piece is not None:
                for tex in piece.textures:
                    tex.array = texture_array(tex)

            self.cache[member] = piece

        return self.cache[member]

    def pieces(self, background, terrain):
        backdrop = self.piece(background)
        assert backdrop is not None, f"background {background} has an empty piece"
        return [backdrop, self.piece(sf.BACKGROUND_MAX + terrain)]

    def classic(self, background, terrain):
        key = ("classic", background, terrain)

        if key not in self.cache:
            backdrop = classic.Backdrop(background)
            platforms = [classic.Platform(side, terrain) for side in (classic.SIDE_PLAYER, classic.SIDE_ENEMY)]
            platforms = [p for p in platforms if not p.is_empty()]
            self.cache[key] = (backdrop, platforms, classic.classic_frame(backdrop, platforms))

        return self.cache[key]


def camera_for(piece, view):
    h = piece.header
    return fx.Camera(h.cam_pos, h.cam_target, h.fovy_sin, h.fovy_cos, h.near, h.far, h.vertex_scale, view)


def diff_image(home, covered, reference):
    delta = np.abs(home.astype(np.int32) - reference.astype(np.int32)).max(axis=2)
    grey = reference.mean(axis=2, keepdims=True).astype(np.uint8) // 2 + 64
    out = np.repeat(grey, 3, axis=2)
    bad = delta > 0
    out[bad] = 0
    out[bad, 0] = np.minimum(255, 96 + delta[bad] * 4)
    out[~covered] = HOLE_RGB
    out[HOME_VISIBLE_ROWS:] //= 3
    return out


class Result:
    def __init__(self, background, terrain, tod, raster, home, covered, reference, holes, views):
        rows = slice(0, HOME_VISIBLE_ROWS)
        delta = np.abs(home[rows].astype(np.int32) - reference[rows].astype(np.int32))
        self.background, self.terrain, self.tod, self.raster = background, terrain, tod, raster
        self.mean = float(delta.mean())
        self.max = int(delta.max())
        self.differ = int(delta.any(axis=2).sum())
        self.holes = holes  # view 0 (rows 0..143), views 1..3
        self.home, self.reference, self.views = home, reference, views
        self.diff = diff_image(home, covered, reference)

    def row(self):
        holes = "/".join(str(h) for h in self.holes)
        return (f"{self.background:2}  {self.terrain:2}  {TOD_NAMES[self.tod]:8}  {self.raster:8}  "
                f"{self.mean:7.3f}  {self.max:3}  {self.differ:6}  {holes}")


HEADER_ROW = "bg  tr  tod       raster      mean  max  differ  holes v0/v1/v2/v3"


def evaluate(stage, background, terrain, tod, raster, frame=None, views=True, view_cache=None):
    """Renders one arena at one time of day; views 1..3 are cached per geometry (the
    light and fog do not change coverage)."""
    column = classic.palette_column(background, tod)
    backdrop, platforms, frame_px = stage.classic(background, terrain)
    reference = np.array(classic.frame_rgb(frame_px, backdrop, platforms, column), np.uint8)
    palettes = {"bg": palette5(backdrop.palettes[column])}

    for plat in platforms:
        palettes["platform", plat.side] = palette5(plat.palettes[column])

    pieces = stage.pieces(background, terrain)
    renderer = Renderer(pieces, palettes, raster, column, frame)
    home, covered = renderer.render(camera_for(pieces[0], 0))
    holes = [int((~covered[:HOME_VISIBLE_ROWS]).sum())]
    images = []
    key = (background, terrain, raster)

    if views:
        if view_cache is not None and key in view_cache and tod != 0:
            holes += view_cache[key][0]
            images = view_cache[key][1]
        else:
            for view in range(1, fx.NUM_VIEWS):
                img, cov = renderer.render(camera_for(pieces[0], view))
                holes.append(int((~cov).sum()))
                images.append(img)

            if view_cache is not None:
                view_cache[key] = (holes[1:], images)

    return Result(background, terrain, tod, raster, home, covered, reference, holes, images)


def hstack(images, gap=4):
    out = []

    for i, img in enumerate(images):
        if i:
            out.append(np.zeros((img.shape[0], gap, 3), np.uint8))

        out.append(img)

    return np.concatenate(out, axis=1)


def vstack(images, gap=4):
    width = max(img.shape[1] for img in images)
    out = []

    for i, img in enumerate(images):
        if i:
            out.append(np.zeros((gap, width, 3), np.uint8))

        pad = np.zeros((img.shape[0], width - img.shape[1], 3), np.uint8)
        out.append(np.concatenate([img, pad], axis=1))

    return np.concatenate(out, axis=0)


def labelled(img, text):
    im = Image.fromarray(img)
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, 0, 8 + 6 * len(text), 12), fill=(0, 0, 0))
    draw.text((3, 1), text, fill=(255, 255, 255))
    return np.array(im)


def grid(tiles, columns=6):
    rows = [hstack(tiles[i:i + columns]) for i in range(0, len(tiles), columns)]
    return vstack(rows)


def save(path, img, scale=1):
    im = Image.fromarray(img)

    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)

    im.save(path)


def summary(results):
    print(HEADER_ROW)

    for r in results:
        print(r.row())


def aggregate(results, label):
    """One line per raster: worst numbers over a set of results."""
    for raster in RASTERS:
        rs = [r for r in results if r.raster == raster]

        if not rs:
            continue

        worst = max(rs, key=lambda r: r.mean)
        holes = sum(sum(r.holes) for r in rs)
        print(f"  {label} {raster:8}: mean diff max {worst.mean:.3f} (bg {worst.background} {TOD_NAMES[worst.tod]}), "
              f"max diff {max(r.max for r in rs)}, holes {holes}")


def run_one(stage, args, rasters):
    background = args.bg
    terrain = USUAL_TERRAIN[background] if args.terrain is None else args.terrain
    tods = range(3) if args.tod is None else [args.tod]
    results = []

    for raster in rasters:
        for tod in tods:
            r = evaluate(stage, background, terrain, tod, raster, args.frame)
            results.append(r)

            if raster == rasters[0]:
                top = hstack([r.reference, r.home, r.diff])
                sheet = vstack([top, hstack(r.views)])
                save(os.path.join(args.out, f"sheet_bg{background:02}_t{tod}.png"), sheet, 2)
                save(os.path.join(args.out, f"home_bg{background:02}_t{tod}.png"), r.home)

    summary(results)
    print(f"wrote {args.out}/sheet_bg{background:02}_t*.png")


def run_all(stage, args, rasters):
    results = []
    homes = {tod: [] for tod in range(3)}
    views = {view: [] for view in range(1, fx.NUM_VIEWS)}
    started = time.time()

    for background in range(sf.BACKGROUND_MAX):
        terrain = USUAL_TERRAIN[background]

        for raster in rasters:
            view_cache = {}
            rows = []

            for tod in range(3):
                r = evaluate(stage, background, terrain, tod, raster, args.frame, True, view_cache)
                results.append(r)
                rows.append(hstack([r.reference, r.home, r.diff]))

                if raster == rasters[0]:
                    homes[tod].append(labelled(r.home, f"bg {background} t{terrain}"))

                    if tod == 0:
                        for i, img in enumerate(r.views):
                            views[i + 1].append(labelled(img, f"bg {background}"))

            if raster == rasters[0]:
                sheet = vstack(rows + [hstack(view_cache[(background, terrain, raster)][1])])
                save(os.path.join(args.out, f"sheet_bg{background:02}.png"), sheet)

    terrain_results = []
    terrain_tiles = []

    for terrain in range(sf.TERRAIN_MAX):
        for raster in rasters:
            r = evaluate(stage, 0, terrain, 0, raster, args.frame, True, {})
            terrain_results.append(r)

            if raster == rasters[0]:
                terrain_tiles.append(labelled(r.home, f"terrain {terrain}"))

    for tod in range(3):
        save(os.path.join(args.out, f"contact_home_{TOD_NAMES[tod]}.png"), grid(homes[tod]))

    for view, tiles in views.items():
        save(os.path.join(args.out, f"contact_view{view}.png"), grid(tiles))

    save(os.path.join(args.out, "contact_terrains.png"), grid(terrain_tiles))

    print("backgrounds (usual terrain):")
    summary(results)
    print("terrains on background 0, day:")
    summary(terrain_results)
    print("worst:")

    for tod in range(3):
        aggregate([r for r in results if r.tod == tod], f"{TOD_NAMES[tod]:8}")

    aggregate(terrain_results, "terrains")
    print(f"wrote {args.out}/sheet_bg*.png, contact_*.png in {time.time() - started:.0f} s")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--narc", default=os.path.join(classic.ROOT, "res/prebuilt/battle/graphic/battle_stage.narc"))
    parser.add_argument("--out", default="/tmp/battle_stage_preview")
    parser.add_argument("--raster", choices=RASTERS + ("both",), default="desmume")
    parser.add_argument("--bg", type=int, default=0, help="background (BACKGROUND_*)")
    parser.add_argument("--terrain", type=int, help="platform piece (TERRAIN_*); default: the background's usual one")
    parser.add_argument("--tod", type=int, choices=(0, 1, 2), help="0 day, 1 twilight, 2 night; default: all three")
    parser.add_argument("--frame", type=int, help="sway SCROLL meshes to this arena draw (30 per second; default: no sway)")
    parser.add_argument("--all", action="store_true", help="every background and every terrain")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rasters = RASTERS if args.raster == "both" else (args.raster,)
    stage = Stage(args.narc)

    if args.all:
        run_all(stage, args, rasters)
    else:
        run_one(stage, args, rasters)


if __name__ == "__main__":
    main()

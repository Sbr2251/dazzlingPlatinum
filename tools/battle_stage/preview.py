#!/usr/bin/env python3
"""Software-renders battle_stage.narc the way the renderer draws it, to check an arena
without building the ROM.

For the arena of BACKGROUND_PLAIN / TERRAIN_PLAIN it writes, to --out (default
/tmp/battle_stage_preview):

    view0.png .. view3.png   home pose and the three debug views (L+R+B in battle);
                             magenta pixels are holes (nothing drawn)
    classic.png              the classic 2D scene (BG3 + platform OBJs)
    home_diff.png            home pose vs classic: grey = same, red = different,
                             magenta = hole; rows 144+ (under the text box) are dimmed
    sheet.png                all of the above side by side

and prints the differing pixel count at home and the hole count of every view.

The rasterizer follows the DS closely enough for pixel checks: the same integer
vertex transform as fx.py, near/far clipping, scanline edge walking with perspective
correct interpolation, a depth test, palette index 0 transparency and the texture
clamp/repeat/flip modes. --raster picks how screen positions and spans work:

    desmume   like the soft rasterizer of DeSmuME 0.9.12 (py-desmume, which the
              critic runs; the default): positions rounded to 1/16 pixel, and a
              span's first pixel gets the attributes of the exact edge point, not of
              the pixel, so a vertex just right of a pixel boundary shifts the span's
              texels one pixel right
    hardware  positions truncated to whole pixels, attributes taken at each pixel,
              like the DS

Needs numpy and PIL (~/.venvs/desmume/bin/python).
"""

import argparse
import math
import os

import numpy as np
from PIL import Image

import classic
import fx
import nitro
import stage_format as sf

HOME_VISIBLE_ROWS = 144  # BG1 covers the rest
HOLE_RGB = (255, 0, 255)
W, H = fx.SCREEN_W, fx.SCREEN_H

FLAG_REPEAT_S = 1 << 4
FLAG_REPEAT_T = 1 << 5
FLAG_FLIP_S = 1 << 6
FLAG_FLIP_T = 1 << 7
FLAG_COLOR0_TRANSPARENT = 1 << 2


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


class Renderer:
    def __init__(self, pieces, palettes, raster="desmume"):
        self.pieces = pieces
        self.palettes = palettes  # {palette source key: [RGB888] }
        self.raster = raster

    def render(self, camera):
        color = np.zeros((H, W, 3), np.uint8)
        color[:] = HOLE_RGB
        depth = np.full((H, W), np.inf)
        covered = np.zeros((H, W), bool)
        self.num_polygons = 0

        for p_index, piece in enumerate(self.pieces):
            for mesh in piece.meshes:
                tex = piece.textures[mesh.texture_index]
                pal = self.palette_for(p_index, tex, mesh)

                clip = [camera.to_clip(v[0]) for v in mesh.vertices]
                tcs = [(v[1][0] / sf.TEXCOORD_ONE, v[1][1] / sf.TEXCOORD_ONE) for v in mesh.vertices]

                for poly in polygons(mesh):
                    verts = [clip[i] + tcs[i] for i in poly]
                    verts = clip_polygon(verts, lambda v: v[2] + v[3])  # near: z >= -w
                    verts = clip_polygon(verts, lambda v: v[3] - v[2])  # far: z <= w

                    if len(verts) >= 3:
                        self.num_polygons += 1
                        self.draw(verts, tex, mesh.flags, pal, color, depth, covered)

        return color, covered

    def palette_for(self, p_index, tex, mesh):
        if tex.palette_source == sf.PALETTE_PLATFORM_OBJ:
            side = 1 if mesh.flags & 2 else 0
            return self.palettes.get(("platform", side), tex.palette)

        if tex.palette_source == sf.PALETTE_BG:
            return self.palettes.get("bg", tex.palette)

        return tex.palette

    def screen(self, x, y, w):
        sx = (x + w) * W / (2 * w)
        sy = (w - y) * H / (2 * w)

        if self.raster == "hardware":
            return math.floor(sx), math.floor(sy)

        # DeSmuME keeps positions in 28.4 fixed point
        return math.floor(sx * 16 + 0.5) / 16, math.floor(sy * 16 + 0.5) / 16

    def draw(self, verts, tex, flags, pal, color, depth, covered):
        # Screen vertices: x, y, then 1/w, s/w, t/w, z/w, linear in screen space
        sv = []

        for x, y, z, w, s, t in verts:
            sx, sy = self.screen(x, y, w)
            sv.append((sx, sy, 1 / w, s / w, t / w, z / w))

        ys = [v[1] for v in sv]
        y_first = max(0, math.ceil(min(ys)))
        y_end = min(H, math.ceil(max(ys)))
        n = len(sv)
        rgb = pal if isinstance(pal, np.ndarray) else None

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
                hits.append(tuple(a[k] + (b[k] - a[k]) * f for k in range(6)))

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
            attr = [left[k] + (right[k] - left[k]) * f for k in range(2, 6)]
            inv_w, s_w, t_w, z = attr
            s = np.floor(s_w / inv_w).astype(np.int64)
            t = np.floor(t_w / inv_w).astype(np.int64)
            s = wrap(s, tex.width, flags & FLAG_REPEAT_S, flags & FLAG_FLIP_S)
            t = wrap(t, tex.height, flags & FLAG_REPEAT_T, flags & FLAG_FLIP_T)
            index = tex.array[t, s]

            visible = z < depth[py, x0:x1]

            if flags & FLAG_COLOR0_TRANSPARENT:
                visible &= index != 0

            cols = px[visible]
            depth[py, cols] = z[visible]
            color[py, cols] = rgb[index[visible]]
            covered[py, cols] = True


def texture_array(tex):
    if tex.format == sf.TEXFMT_PLTT256:
        return np.frombuffer(tex.data, np.uint8).reshape(tex.height, tex.width)

    packed = np.frombuffer(tex.data, np.uint8).reshape(tex.height, tex.width // 2)
    out = np.empty((tex.height, tex.width), np.uint8)
    out[:, 0::2] = packed & 0xF
    out[:, 1::2] = packed >> 4
    return out


def rgb_palette(colors):
    return np.array([nitro.gxrgb_to_rgb888(c) for c in colors] + [(0, 0, 0)] * (256 - len(colors)), np.uint8)


def load_pieces(narc_path, background=0, terrain=0):
    members = nitro.read_narc(narc_path)
    pieces = [sf.read_piece(members[background]), sf.read_piece(members[sf.BACKGROUND_MAX + terrain])]
    assert pieces[0] is not None and pieces[1] is not None, "empty piece"

    for piece in pieces:
        for tex in piece.textures:
            tex.array = texture_array(tex)

    return pieces


def camera_for(piece, view):
    h = piece.header
    return fx.Camera(h.cam_pos, h.cam_target, h.fovy_sin, h.fovy_cos, h.near, h.far, h.vertex_scale, view)


def classic_rgb(tod=0, terrain=0):
    backdrop = classic.Backdrop(0)
    platforms = [classic.Platform(side, terrain) for side in (classic.SIDE_PLAYER, classic.SIDE_ENEMY)]
    frame = classic.classic_frame(backdrop, platforms)
    rows = classic.frame_rgb(frame, backdrop, platforms, tod)
    return np.array(rows, np.uint8), backdrop, platforms


def diff_image(home, covered, reference):
    same = np.all(home == reference, axis=2)
    grey = reference.mean(axis=2, keepdims=True).astype(np.uint8) // 2 + 64
    out = np.repeat(grey, 3, axis=2)
    out[~same] = (255, 0, 0)
    out[~covered] = HOLE_RGB
    out[HOME_VISIBLE_ROWS:] //= 3
    return out, same


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--narc", default=os.path.join(classic.ROOT, "res/prebuilt/battle/graphic/battle_stage.narc"))
    parser.add_argument("--out", default="/tmp/battle_stage_preview")
    parser.add_argument("--raster", choices=("desmume", "hardware"), default="desmume")
    parser.add_argument("--tod", type=int, default=0, help="time of day palettes: 0 day, 1 twilight, 2 night")
    parser.add_argument("--terrain", type=int, default=0, help="platform piece: 0 TERRAIN_PLAIN, 2 TERRAIN_GRASS")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    pieces = load_pieces(args.narc, terrain=args.terrain)
    reference, backdrop, platforms = classic_rgb(args.tod, args.terrain)
    palettes = {"bg": rgb_palette(backdrop.palettes[args.tod])}

    for plat in platforms:
        palettes["platform", plat.side] = rgb_palette(plat.palettes[args.tod])

    renderer = Renderer(pieces, palettes, args.raster)
    images = []

    for view in range(fx.NUM_VIEWS):
        img, covered = renderer.render(camera_for(pieces[0], view))
        rows = HOME_VISIBLE_ROWS if view == 0 else H
        holes = int((~covered[:rows]).sum())
        print(f"view {view}: {renderer.num_polygons} polygons drawn, {holes} hole pixels" + (" (rows 0..143)" if view == 0 else ""))
        Image.fromarray(img).save(os.path.join(args.out, f"view{view}.png"))
        images.append(img)

        if view == 0:
            diff, same = diff_image(img, covered, reference)
            bad = ~same[:HOME_VISIBLE_ROWS]
            print(f"home vs classic: {int(bad.sum())} of {W * HOME_VISIBLE_ROWS} pixels differ in rows 0..143")

            if bad.any():
                ys, xs = np.nonzero(bad)
                print("  first differing pixels:", list(zip(xs[:12].tolist(), ys[:12].tolist())))

            Image.fromarray(diff).save(os.path.join(args.out, "home_diff.png"))

    Image.fromarray(reference).save(os.path.join(args.out, "classic.png"))
    gap = np.zeros((H, 4, 3), np.uint8)
    top = np.concatenate([reference, gap, images[0], gap, diff], axis=1)
    bottom = np.concatenate([images[1], gap, images[2], gap, images[3]], axis=1)
    sheet = np.concatenate([top, np.zeros((4, top.shape[1], 3), np.uint8), bottom], axis=0)
    Image.fromarray(sheet).resize((sheet.shape[1] * 2, sheet.shape[0] * 2), Image.NEAREST).save(os.path.join(args.out, "sheet.png"))
    print(f"wrote {args.out}/view0..3.png, classic.png, home_diff.png, sheet.png")


if __name__ == "__main__":
    main()

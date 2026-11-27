#!/usr/bin/env python3
"""Software previews of Route 215 (NumPy + PIL): a textured top view and field-camera views of the chunks,
rendered straight from the NSBMD models and the texture set (decoded back from the built bytes), so what is
checked is what the game loads.

Usage:
  ~/.venvs/desmume/bin/python tools/routes/r215/render.py OUT_DIR [--stock] [--top] [--views]

  --stock   render the stock chunks + stock set 010 (from git BASE_REV) instead of the work tree
  --top     top view of the whole route (16 px per tile)
  --views   field-camera views at every VIEWPOINTS entry (CAMERA_TYPE_DEFAULT pitch/distance/FOV)
"""
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as R  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402

PITCH, DIST, HALF_FOV = 59.051513671875, 666.922119140625, 8.0914306640625
LIGHT = np.array([-0.35, 0.85, 0.40])
LIGHT = LIGHT / np.linalg.norm(LIGHT)

VIEWPOINTS = [
    ("01_west_entry", 582, 600),
    ("02_flooded_boardwalk", 600, 592),
    ("03_lowland_070", 620, 592),
    ("04_north_staging_yard", 633, 585),
    ("05_south_field_crates", 652, 592),
    ("06_veilstone_gate_yard", 663, 598),
    ("07_west_flood_overlook", 591, 596),
]


class TexCache:
    def __init__(self, set_bytes):
        s = nsbtx.parse(set_bytes)
        self.T = {t["name"]: t for t in s["textures"]}
        self.P = {p["name"]: p for p in s["palettes"]}
        self.cache = {}

    def get(self, tex, pal):
        k = (tex, pal)
        if k not in self.cache:
            t = self.T.get(tex)
            if t is None:
                self.cache[k] = np.full((8, 8, 4), (255, 0, 255, 255), np.uint8)
            else:
                p = self.P.get(pal)
                rgba, _ = nsbtx.decode(t, p["colors"] if p else None)
                self.cache[k] = np.array(rgba, np.uint8).reshape(t["h"], t["w"], 4)
        return self.cache[k]


def load_faces(chunks, tc):
    """chunks: [(model bytes, cell)] -> list of dicts per material batch with world-space triangles."""
    batches = []
    for model_bytes, cell in chunks:
        bmd = nsbmd.parse_bmd(model_bytes)
        model = bmd["models"][0]
        mesh = nsbmd.model_to_mesh(model, cell)
        mats = {m["name"]: m for m in mesh["materials"]}
        for me in mesh["meshes"]:
            m = mats[me["material"]]
            tex = tc.get(m["texture"], m["palette"])
            P = np.array(me["positions"], float)
            W = np.stack([P[:, 0] * 16.0, 16.0 + P[:, 1] * 16.0, P[:, 2] * 16.0], 1)
            UV = np.array(me["uvs"], float)
            tris = [f for f in me["tris"]] + [t for q in me["quads"] for t in ((q[0], q[1], q[2]), (q[0], q[2], q[3]))]
            if not tris:
                continue
            tp = m["tex_param"]
            pa = m["polygon_attr"]
            batches.append(dict(W=W, UV=UV, tris=np.array(tris, int), tex=tex,
                                rep=(tp.get("repeat_s", True), tp.get("repeat_t", True)),
                                flip=(tp.get("flip_s", False), tp.get("flip_t", False)),
                                alpha=pa.get("alpha", 31) / 31.0, cull=pa.get("cull", "back"),
                                lit=pa.get("lights", 1) != 0, name=m["name"],
                                colors=np.array(me["colors"], float) / 255.0))
    return batches


def wrap(u, n, rep, flip):
    if not rep:
        return np.clip(u, 0, n - 1)
    if flip:
        p = np.mod(u, 2 * n)
        return np.where(p >= n, 2 * n - 1 - p, p)
    return np.mod(u, n)


def raster(batches, project, Wd, Ht, bg=(46, 58, 70)):
    """project(world Nx3) -> (sx, sy, depth) arrays; smaller depth = nearer."""
    img = np.zeros((Ht, Wd, 3), float)
    img[:] = np.array(bg) / 255.0
    zb = np.full((Ht, Wd), np.inf)
    for b in batches:
        a = b["tex"][..., 3]
        b["soft"] = bool(((a > 0) & (a < 255)).any())               # A3I5 / A5I3: real per-texel alpha
    order = sorted(batches, key=lambda b: (b["alpha"] < 0.99 or b["soft"], b["soft"]))   # opaque first
    for b in order:
        sx, sy, dz = project(b["W"])
        tex = b["tex"].astype(float) / 255.0
        th, tw = tex.shape[:2]
        for tri in b["tris"]:
            xs, ys, zs = sx[tri], sy[tri], dz[tri]
            if not np.all(np.isfinite(zs)) or np.any(zs <= 0):
                continue
            area = (xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0])
            if abs(area) < 1e-9:
                continue
            if b["cull"] == "back" and area > 0:
                continue
            x0, x1 = max(int(np.floor(xs.min())), 0), min(int(np.ceil(xs.max())), Wd - 1)
            y0, y1 = max(int(np.floor(ys.min())), 0), min(int(np.ceil(ys.max())), Ht - 1)
            if x0 > x1 or y0 > y1:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            w0 = ((xs[1] - gx) * (ys[2] - gy) - (xs[2] - gx) * (ys[1] - gy)) / area
            w1 = ((xs[2] - gx) * (ys[0] - gy) - (xs[0] - gx) * (ys[2] - gy)) / area
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not inside.any():
                continue
            # perspective-correct depth and texture coordinates (interpolate 1/z and uv/z, like the hardware):
            # affine interpolation breaks down on the big pad / sheet polygons
            iz = w0 / zs[0] + w1 / zs[1] + w2 / zs[2]
            z = 1.0 / iz
            p0, p1, p2 = w0 / zs[0] * z, w1 / zs[1] * z, w2 / zs[2] * z
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            ok = inside & (z < sub - 0.02)
            if not ok.any():
                continue
            uv = b["UV"][tri]
            u = (p0 * uv[0, 0] + p1 * uv[1, 0] + p2 * uv[2, 0]) * tw
            v = (p0 * uv[0, 1] + p1 * uv[1, 1] + p2 * uv[2, 1]) * th
            iu = wrap(np.floor(u).astype(int), tw, b["rep"][0], b["flip"][0])
            iv = wrap(np.floor(v).astype(int), th, b["rep"][1], b["flip"][1])
            c = tex[iv, iu]
            a = c[..., 3] * b["alpha"]
            ok &= a > 0.02
            if not ok.any():
                continue
            pts = b["W"][tri]
            n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
            n = n / (np.linalg.norm(n) or 1)
            shade = (0.72 + 0.32 * max(0.0, float(np.dot(n, LIGHT)))) if b["lit"] else 1.0
            col = c[..., :3] * shade
            if not b["lit"]:
                vc = b["colors"][tri]
                col = col * (w0[..., None] * vc[0] + w1[..., None] * vc[1] + w2[..., None] * vc[2])
            region = img[y0:y1 + 1, x0:x1 + 1]
            aa = np.where(ok, a, 0)[..., None]
            if b["alpha"] >= 0.99 and not b["soft"]:
                aa = np.where(ok, (a > 0.5).astype(float), 0)[..., None]
                sub[ok & (a > 0.5)] = z[ok & (a > 0.5)]
            region[:] = region * (1 - aa) + np.clip(col, 0, 1) * aa
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def top_view(batches, x0=576, x1=672, z0=576, z1=608, ppt=16):
    def project(W):
        return (W[:, 0] / 16.0 - x0) * ppt, (W[:, 2] / 16.0 - z0) * ppt, 1000.0 - W[:, 1]
    # top view: looking down -y, image x = +x, image y = +z; triangles wound CCW from above appear CW in image space
    for b in batches:
        b["cull_saved"] = b["cull"]
        b["cull"] = "none"
    img = raster(batches, project, (x1 - x0) * ppt, (z1 - z0) * ppt)
    for b in batches:
        b["cull"] = b.pop("cull_saved")
    return img


def camera_view(batches, tx, tz, Wd=768, Ht=576, ty=32.0):
    p = math.radians(PITCH)
    tgt = np.array([(tx + 0.5) * 16.0, ty, (tz + 0.5) * 16.0])
    cam = tgt + np.array([0.0, DIST * math.sin(p), DIST * math.cos(p)])
    fwd = (tgt - cam) / np.linalg.norm(tgt - cam)
    right = np.cross(fwd, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    f = (Ht / 2) / math.tan(math.radians(HALF_FOV))

    def project(W):
        d = W - cam
        zc = d @ fwd
        xc = d @ right
        yc = d @ up
        with np.errstate(divide="ignore", invalid="ignore"):
            return Wd / 2 + f * xc / zc, Ht / 2 - f * yc / zc, zc
    return raster(batches, project, Wd, Ht)


def grid_overlay(img, x0=576, z0=576, ppt=16, marks=None):
    im = Image.fromarray(img)
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    for x in range(0, img.shape[1], ppt * 8):
        d.line([(x, 0), (x, img.shape[0])], fill=(255, 255, 255), width=1)
        d.text((x + 2, 2), str(x0 + x // ppt), fill=(255, 255, 0))
    for y in range(0, img.shape[0], ppt * 8):
        d.line([(0, y), (img.shape[1], y)], fill=(255, 255, 255), width=1)
        d.text((2, y + 2), str(z0 + y // ppt), fill=(255, 255, 0))
    for (x, z), ch in (marks or {}).items():
        px, pz = (x - x0) * ppt, (z - z0) * ppt
        d.rectangle([px + 3, pz + 3, px + ppt - 4, pz + ppt - 4], outline=(255, 0, 0))
        d.text((px + 4, pz + 2), ch, fill=(255, 255, 255))
    return im


def sources(stock):
    if stock:
        chunks = [(mapdata.unpack(R.git_file(R.chunk_rel(c)))["model"], cell) for c, cell in R.CHUNKS.items()]
        set_bytes = R.git_file("res/field/mapmodels/texture_sets/map_texture_set_010.nsbtx")
    else:
        chunks = [(mapdata.unpack(open(os.path.join(R.ROOT, R.chunk_rel(c)), "rb").read())["model"], cell)
                  for c, cell in R.CHUNKS.items()]
        set_bytes = open(os.path.join(R.ROOT, "res/field/mapmodels/texture_sets/map_texture_set_078.nsbtx"),
                         "rb").read()
    return chunks, set_bytes


def main():
    out = sys.argv[1]
    args = sys.argv[2:]
    stock = "--stock" in args
    os.makedirs(out, exist_ok=True)
    chunks, set_bytes = sources(stock)
    tc = TexCache(set_bytes)
    batches = load_faces(chunks, tc)
    tag = "stock" if stock else "new"
    if "--top" in args or not ("--views" in args):
        img = top_view(batches)
        marks = R.event_marks(R.stock_events()) if "--marks" in args else None
        grid_overlay(img, marks=marks).save(os.path.join(out, f"top_{tag}.png"))
        print("wrote", os.path.join(out, f"top_{tag}.png"))
    if "--views" in args:
        for name, x, z in VIEWPOINTS:
            img = camera_view(batches, x, z)
            Image.fromarray(img).save(os.path.join(out, f"view_{tag}_{name}.png"))
            print("wrote", f"view_{tag}_{name}.png")


if __name__ == "__main__":
    main()

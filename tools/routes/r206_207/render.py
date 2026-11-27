#!/usr/bin/env python3
"""Preview renderer for Routes 206-207: a small NumPy rasteriser (after tools/everspring/build_art.render) that draws
chunk NSBMDs with the real set textures (any size, colour-0 transparency, repeat/flip), the field camera
(CAMERA_TYPE_DEFAULT) or a top-down orthographic view. Needs ~/.venvs/desmume/bin/python (NumPy + PIL).

  render_views(models, set_bytes, out_dir, views, night=False)
models: {chunk: NSBMD bytes}.  views: {name: ("cam", x, z, zoom) | ("top", x0, z0, x1, z1, px_per_tile)}.

Usage (stock):
  ~/.venvs/desmume/bin/python tools/routes/r206_207/render.py OUT_DIR [--night]
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as K  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402

DAY = dict(sky=(0.62, 0.70, 0.88), light=(0.92, 0.88, 0.80), amb=(0.55, 0.53, 0.55), dirv=(0.463, -0.879, -0.114))
NIGHT = dict(sky=(0.08, 0.07, 0.16), light=(0.36, 0.38, 0.62), amb=(0.33, 0.33, 0.48), dirv=(0.463, -0.879, -0.114))


def texture_arrays(set_bytes):
    import numpy as np
    s = nsbtx.parse(set_bytes)
    P = {p["name"]: p["colors"] for p in s["palettes"]}
    T = {t["name"]: t for t in s["textures"]}
    cache = {}

    def get(tex, pal):
        k = (tex, pal)
        if k not in cache:
            t = T.get(tex)
            if t is None:
                cache[k] = np.full((8, 8, 4), (1.0, 0.0, 1.0, 1.0))
            else:
                px, _ = nsbtx.decode(t, P.get(pal) or next(iter(P.values())))
                cache[k] = np.array(px, float) / 255.0
        return cache[k]
    return get


def collect(models, get_tex, light):
    """-> list of (P (n,3) world, UV (n,2), shade (n,3), tri list, texture array, flags) per mesh."""
    import numpy as np
    L = -np.array(light["dirv"])
    out = []
    for c, data in models.items():
        model = nsbmd.parse_bmd(data)["models"][0]
        mesh = nsbmd.model_to_mesh(model, K.CHUNKS[c])
        mats = {m["name"]: m for m in mesh["materials"]}
        for me in mesh["meshes"]:
            m = mats[me["material"]]
            pa, tp = m["polygon_attr"], m["tex_param"]
            T = get_tex(m["texture"], m["palette"])
            P = np.array(me["positions"], float) * 16.0 + [0, 16.0, 0]
            UV = np.array(me["uvs"], float)
            if pa["lights"]:
                N = np.array([n if n else [0, 1, 0] for n in me["normals"]] if me["normals"] else [[0, 1, 0]] * len(P))
                d = np.clip(N @ L, 0, 1)[:, None]
                sh = np.array(light["amb"]) + np.array(light["light"]) * 0.75 * d
            else:
                sh = np.array(me["colors"], float) / 255.0
            tris = [tuple(q) for q in me["tris"]] + [t for q in me["quads"] for t in ((q[0], q[1], q[2]),
                                                                                      (q[0], q[2], q[3]))]
            out.append((P, UV, sh, tris, T, dict(two=pa["cull"] != "back", alpha=pa["alpha"] / 31.0,
                                                 rs=tp["repeat_s"], rt=tp["repeat_t"], fs=tp["flip_s"],
                                                 ft=tp["flip_t"])))
    return out


def _wrap(u, n, rep, flip):
    import numpy as np
    t = np.floor(u * n).astype(int)
    if not rep:
        return np.clip(t, 0, n - 1)
    if flip:
        k = np.floor_divide(t, n)
        r = np.mod(t, n)
        return np.where(k % 2 == 0, r, n - 1 - r)
    return np.mod(t, n)


PROP_ORDER = "res/field/props/models/map_prop_models.order"


def prop_meshes(chunk_props, light):
    """Map props (build models, by index into map_prop_models.order) as flat-shaded grey-violet solids, so previews
    show their footprint. chunk_props: {chunk: [prop dicts from mapdata.read_props]}."""
    import numpy as np
    order = open(os.path.join(K.ROOT, PROP_ORDER)).read().split()
    L = -np.array(light["dirv"])
    tex = np.ones((8, 8, 4))
    out = []
    for c, props in chunk_props.items():
        for p in props:
            data = open(os.path.join(K.ROOT, "res/field/props/models", order[p["model"]]), "rb").read()
            pm = nsbmd.parse_bmd(data)["models"][0]
            mesh = nsbmd.model_to_mesh(pm, K.CHUNKS[c], offset=[v / 4096 for v in p["pos"]])
            for me in mesh["meshes"]:
                P = np.array(me["positions"], float) * 16.0 + [0, 16.0, 0]
                tris = [tuple(q) for q in me["tris"]] + [t for q in me["quads"] for t in ((q[0], q[1], q[2]),
                                                                                          (q[0], q[2], q[3]))]
                sh = np.zeros((len(P), 3))
                for a, b, cc in tris:
                    n = np.cross(P[b] - P[a], P[cc] - P[a])
                    n = n / (np.linalg.norm(n) or 1)
                    v = 0.45 + 0.5 * max(0.0, float(n @ L))
                    sh[[a, b, cc]] = (v * 0.8, v * 0.75, v * 0.9)
                out.append((P, np.zeros((len(P), 2)), sh, tris, tex, dict(two=True, alpha=1.0, rs=True, rt=True,
                                                                          fs=False, ft=False)))
    return out


def rasterise(meshes, project, w, h, sky):
    import numpy as np
    img = np.zeros((h, w, 3))
    img[:] = sky
    zb = np.full((h, w), np.inf)
    for P, UV, SH, tris, T, fl in meshes:
        sx, sy, zc = project(P)
        th, tw = T.shape[:2]
        for a, b, c in tris:
            if min(zc[a], zc[b], zc[c]) < 1e-3:
                continue
            x0, y0, x1, y1, x2, y2 = sx[a], sy[a], sx[b], sy[b], sx[c], sy[c]
            area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
            if area == 0 or (area > 0 and not fl["two"]):
                continue
            bx0, bx1 = max(int(min(x0, x1, x2)), 0), min(int(max(x0, x1, x2)) + 1, w)
            by0, by1 = max(int(min(y0, y1, y2)), 0), min(int(max(y0, y1, y2)) + 1, h)
            if bx0 >= bx1 or by0 >= by1:
                continue
            gy, gx = np.mgrid[by0:by1, bx0:bx1] + 0.5
            w0 = ((x1 - gx) * (y2 - gy) - (x2 - gx) * (y1 - gy)) / area
            w1 = ((x2 - gx) * (y0 - gy) - (x0 - gx) * (y2 - gy)) / area
            w2 = 1 - w0 - w1
            msk = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not msk.any():
                continue
            iz = w0 / zc[a] + w1 / zc[b] + w2 / zc[c]
            depth = 1 / iz
            sub = zb[by0:by1, bx0:bx1]
            msk &= depth < sub - 1e-4
            if not msk.any():
                continue
            pu = (w0 * UV[a, 0] / zc[a] + w1 * UV[b, 0] / zc[b] + w2 * UV[c, 0] / zc[c]) * depth
            pv = (w0 * UV[a, 1] / zc[a] + w1 * UV[b, 1] / zc[b] + w2 * UV[c, 1] / zc[c]) * depth
            tc = T[_wrap(pv, th, fl["rt"], fl["ft"]), _wrap(pu, tw, fl["rs"], fl["fs"])]
            msk &= tc[..., 3] > 0.5
            if not msk.any():
                continue
            shade = w0[..., None] * SH[a] + w1[..., None] * SH[b] + w2[..., None] * SH[c]
            col = np.clip(tc[..., :3] * np.clip(shade, 0, 1.3), 0, 1)
            reg = img[by0:by1, bx0:bx1]
            if fl["alpha"] < 0.99:
                reg[msk] = reg[msk] * (1 - fl["alpha"]) + col[msk] * fl["alpha"]
            else:
                reg[msk] = col[msk]
                sub[msk] = depth[msk]
    return img


def cam_projector(tx, tz, w, h, zoom=1.0, th=4.0):
    """Field camera (CAMERA_TYPE_DEFAULT: pitch 59.05, distance 666.9, fovy 2 x 8.09) on tile (tx, tz); th = target
    mesh h (tiles)."""
    import numpy as np
    pitch, dist = math.radians(59.05), 666.9
    fovy = 2 * math.atan(math.tan(math.radians(8.09)) / zoom)
    tgt = np.array([(tx + 0.5) * 16, 16.0 + 16 * th, (tz + 0.5) * 16])
    cam = tgt + np.array([0, dist * math.sin(pitch), dist * math.cos(pitch)])
    fwd = (tgt - cam) / np.linalg.norm(tgt - cam)
    right = np.cross(fwd, [0, 1, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    f = 1 / math.tan(fovy / 2)

    def project(P):
        rel = P - cam
        xc, yc, zc = rel @ right, rel @ up, rel @ fwd
        zc = np.where(zc < 50, -1.0, zc)
        return w / 2 + xc / np.abs(zc) * f * h / 2, h / 2 - yc / np.abs(zc) * f * h / 2, zc
    return project


def top_projector(x0, z0, ppt):
    """Orthographic straight down: (x0, z0) at the image's top-left, ppt pixels per tile."""
    def project(P):
        return (P[:, 0] / 16.0 - x0) * ppt, (P[:, 2] / 16.0 - z0) * ppt, 5000.0 - P[:, 1]
    return project


def render_views(models, set_bytes, out_dir, views, night=False, suffix="", props=None):
    import numpy as np
    from PIL import Image
    os.makedirs(out_dir, exist_ok=True)
    light = NIGHT if night else DAY
    meshes = collect(models, texture_arrays(set_bytes), light)
    if props:
        meshes += prop_meshes(props, light)
    meshes.sort(key=lambda m: m[5]["alpha"] < 0.99)          # translucent polygons after the opaque ones
    paths = []
    for name, v in views.items():
        if v[0] == "cam":
            _, x, z, zoom, th = v
            w, h = 512, 384
            img = rasterise(meshes, cam_projector(x, z, w, h, zoom, th), w, h, light["sky"])
            im = Image.fromarray((img * 255).astype("uint8")).resize((w * 2, h * 2), Image.NEAREST)
        else:
            _, x0, z0, x1, z1, ppt = v
            w, h = int((x1 - x0) * ppt), int((z1 - z0) * ppt)
            img = rasterise(meshes, top_projector(x0, z0, ppt), w, h, light["sky"])
            im = Image.fromarray((img * 255).astype("uint8"))
        p = os.path.join(out_dir, f"{name}{suffix}.png")
        im.save(p)
        paths.append(p)
    return paths


STOCK_VIEWS = {
    "top_207": ("top", 288, 700, 352, 736, 16),
    "top_206": ("top", 288, 576, 320, 704, 12),
    "cam_coronet": ("cam", 336, 713, 1.0, 4.0),
    "cam_junction": ("cam", 310, 712, 1.0, 4.0),
    "cam_206_south": ("cam", 303, 693, 1.0, 4.0),
    "cam_206_mid": ("cam", 307, 650, 1.0, 0.0),
}


def main():
    out = sys.argv[1]
    secs = {c: mapdata.unpack(K.git_bytes(K.BASE_REV, K.chunk_rel(c))) for c in K.CHUNKS}
    models = {c: s["model"] for c, s in secs.items()}
    props = {c: mapdata.read_props(s["props"]) for c, s in secs.items()}
    sb = K.git_bytes(K.BASE_REV, K.BASE_SET_REL)
    for p in render_views(models, sb, out, STOCK_VIEWS, night="--night" in sys.argv, props=props):
        print(p)


if __name__ == "__main__":
    main()

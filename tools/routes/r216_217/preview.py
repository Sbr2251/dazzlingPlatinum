#!/usr/bin/env python3
"""Field-camera preview renderer for Routes 216-217 (NumPy + PIL): rasterises chunk NSBMD models with the textures
of a texture set (palette per material, colour 0 transparent when c0), Gouraud-lit like the GX light 0, unlit
materials with their baked vertex colours.

Library use (build_art.py): render(models, set_bytes, target, path, ...). CLI:
  ~/.venvs/desmume/bin/python tools/routes/r216_217/preview.py stock OUTDIR      stock chunks, top views + field views
"""
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402

CELLS = {106: (9, 8), 107: (9, 9), 108: (9, 10), 109: (9, 11), 110: (9, 12), 111: (10, 12), 112: (11, 12)}
BASE_REV = "406c75f6a8"


def texture_cache(set_bytes):
    s = nsbtx.parse(set_bytes)
    T = {t["name"]: t for t in s["textures"]}
    P = {p["name"]: p for p in s["palettes"]}
    cache = {}

    def get(tex, pal):
        k = (tex, pal)
        if k not in cache:
            import numpy as np
            if tex not in T or pal not in P:
                cache[k] = np.ones((8, 8, 4)) * [1, 0, 1, 1]
            else:
                rgba, _ = nsbtx.decode(T[tex], P[pal]["colors"])
                cache[k] = np.array(rgba, float) / 255.0
        return cache[k]
    return get


def render(models, set_bytes, target, path, night=False, w=640, h=384, top=False, zoom=1.0, target_h=1.0,
           yaw=0.0, pitch_deg=None):
    """models: [(model dict, (cx, cz))]. target (x, z) absolute tiles (tile centre +0.5 added)."""
    import numpy as np
    from PIL import Image
    tex = texture_cache(set_bytes)
    pitch, dist, fovy = math.radians(59.05), 666.9, math.radians(8.09) * 2
    if pitch_deg is not None:
        pitch = math.radians(pitch_deg)
    if top:
        pitch, dist, fovy = math.radians(89.0), 3000.0, math.radians(14.0)
    fovy = 2 * math.atan(math.tan(fovy / 2) / zoom)
    tx, tz = target
    tgt = np.array([(tx + 0.5) * 16, 16.0 + 16 * target_h, (tz + 0.5) * 16])
    off = np.array([dist * math.cos(pitch) * math.sin(yaw), dist * math.sin(pitch), dist * math.cos(pitch) * math.cos(yaw)])
    cam = tgt + off
    fwd = (tgt - cam) / np.linalg.norm(tgt - cam)
    right = np.cross(fwd, [0, 1, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    f = 1 / math.tan(fovy / 2)
    img = np.zeros((h, w, 3))
    img[:] = (0.10, 0.11, 0.20) if night else (0.70, 0.78, 0.90)
    zb = np.full((h, w), np.inf)
    light = -np.array([0.463, -0.879, -0.114])
    lc = (0.36, 0.40, 0.62) if night else (0.80, 0.82, 0.88)
    amb = (0.34, 0.38, 0.58) if night else (0.58, 0.60, 0.66)
    for model, cell in models:
        mesh = nsbmd.model_to_mesh(model, cell)
        mats = {m["name"]: m for m in mesh["materials"]}
        for me in mesh["meshes"]:
            m = mats[me["material"]]
            lit = m["polygon_attr"]["lights"] != 0
            two = m["polygon_attr"]["cull"] != "back"
            alpha = m.get("alpha", 31) / 31.0
            T = tex(m["texture"], m["palette"])
            th, tw = T.shape[:2]
            P = np.array(me["positions"]) * 16.0 + [0, 16, 0]
            UV = np.array(me["uvs"])
            CO = np.array(me["colors"], float) / 255.0
            NO = np.array([n if n else [0, 1, 0] for n in me["normals"]]) if me["normals"] else None
            rel = P - cam
            xc, yc, zc = rel @ right, rel @ up, rel @ fwd
            with np.errstate(divide="ignore", invalid="ignore"):
                sx = w / 2 + xc / zc * f * h / 2
                sy = h / 2 - yc / zc * f * h / 2
            tris = [tuple(q) for q in me["tris"]] + [t for q in me["quads"] for t in ((q[0], q[1], q[2]), (q[0], q[2], q[3]))]
            for a, b, cc in tris:
                if min(zc[a], zc[b], zc[cc]) < 50:
                    continue
                x0, y0, x1, y1, x2, y2 = sx[a], sy[a], sx[b], sy[b], sx[cc], sy[cc]
                area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
                if area == 0 or (area > 0 and not two):
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
                iz = w0 / zc[a] + w1 / zc[b] + w2 / zc[cc]
                depth = 1 / iz
                sub = zb[by0:by1, bx0:bx1]
                msk &= depth < sub
                if not msk.any():
                    continue
                pu = (w0 * UV[a, 0] / zc[a] + w1 * UV[b, 0] / zc[b] + w2 * UV[cc, 0] / zc[cc]) * depth
                pv = (w0 * UV[a, 1] / zc[a] + w1 * UV[b, 1] / zc[b] + w2 * UV[cc, 1] / zc[cc]) * depth
                tc = T[(np.floor(pv * th).astype(int)) % th, (np.floor(pu * tw).astype(int)) % tw]
                msk &= tc[..., 3] > 0.5
                if not msk.any():
                    continue
                if lit:
                    sh = [np.array([amb[k] + lc[k] * max(0.0, float(np.dot(NO[v], light))) for k in range(3)])
                          for v in (a, b, cc)]
                    shade = w0[..., None] * sh[0] + w1[..., None] * sh[1] + w2[..., None] * sh[2]
                    col = tc[..., :3] * np.clip(shade, 0, 1.2)
                else:
                    vc = (w0[..., None] * CO[a] + w1[..., None] * CO[b] + w2[..., None] * CO[cc])
                    col = tc[..., :3] * vc
                reg = img[by0:by1, bx0:bx1]
                if alpha < 0.99:
                    reg[msk] = reg[msk] * (1 - alpha) + np.clip(col[msk], 0, 1) * alpha
                else:
                    reg[msk] = np.clip(col[msk], 0, 1)
                    sub[msk] = depth[msk]
    Image.fromarray((img * 255).astype("uint8")).resize((w * 2, h * 2), Image.NEAREST).save(path)


def stock_models(chunks=None, rev=BASE_REV):
    out = []
    for c in chunks or sorted(CELLS):
        raw = subprocess.run(["git", "-C", ROOT, "show", f"{rev}:res/field/mapmodels/data/map_data_{c:03d}.bin"],
                             check=True, capture_output=True).stdout
        out.append((nsbmd.parse_bmd(mapdata.unpack(raw)["model"])["models"][0], CELLS[c]))
    return out


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "stock":
        d = sys.argv[2]
        os.makedirs(d, exist_ok=True)
        sb = subprocess.run(["git", "-C", ROOT, "show", f"{BASE_REV}:res/field/mapmodels/texture_sets/map_texture_set_014.nsbtx"],
                            check=True, capture_output=True).stdout
        views = [a.split(",") for a in sys.argv[3:]]
        models = stock_models()
        for v in views:
            x, z = float(v[0]), float(v[1])
            kw = {}
            if len(v) > 2 and v[2] == "top":
                kw = dict(top=True, zoom=float(v[3]) if len(v) > 3 else 1.0)
            elif len(v) > 2:
                kw = dict(target_h=float(v[2]))
            render(models, sb, (x, z), os.path.join(d, f"stock_{v[0]}_{v[1]}{'_top' if kw.get('top') else ''}.png"), **kw)
            print("wrote", v)


if __name__ == "__main__":
    main()

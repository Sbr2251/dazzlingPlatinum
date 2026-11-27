#!/usr/bin/env python3
"""Route 222 preview rasteriser (NumPy + PIL): field-camera and top-down renders of NSBMD chunk models with their real
set-081 textures (every stock format via nsbtx.decode: c0 transparency, a3i5/a5i3 alpha, 4x4), the stock props with
their embedded textures, and an approximation of the GX lighting from a lighting_set JSON block (per vertex:
emission + ambient * light + diffuse * light * max(0, N.L), Gouraud), so lighting curves can be judged offline.

Used by build_art.py --preview. Not a substitute for the in-game check (no fog, no sprites, no sea animation).
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402

PITCH, DIST, HALF_FOV = 59.051513671875, 666.922119140625, 8.0914306640625   # CAMERA_TYPE_DEFAULT


class TexCache:
    """(texture, palette) -> float RGBA array (h, w, 4), from one or more parsed NSBTX blocks."""

    def __init__(self, *sets):
        self.T, self.P = {}, {}
        for s in sets:
            if s is None:
                continue
            for t in s["textures"]:
                self.T.setdefault(t["name"], t)
            for p in s["palettes"]:
                self.P.setdefault(p["name"], p)
        self.cache = {}

    def get(self, tex, pal):
        k = (tex, pal)
        if k not in self.cache:
            t = self.T.get(tex)
            if t is None:
                self.cache[k] = np.full((8, 8, 4), (1.0, 0.0, 1.0, 1.0))
            else:
                p = self.P.get(pal)
                rgba, _ = nsbtx.decode(t, p["colors"] if p else None)
                self.cache[k] = np.array(rgba, float).reshape(t["h"], t["w"], 4) / 255.0
        return self.cache[k]


def light_terms(block):
    """lighting_set block -> (light0 colour, diffuse, ambient, emission, light direction, specular) floats 0..1."""
    c = lambda d: np.array([d["red"], d["green"], d["blue"]], float) / 31.0  # noqa: E731
    l0 = block["lights"][0]
    d = l0["direction"]
    return c(l0["color"]), c(block["diffuseColor"]), c(block["ambientColor"]), c(block["emissionColor"]), \
        -np.array([d["x"], d["y"], d["z"]]), c(block.get("specularColor", block["diffuseColor"]))


DEFAULT_LIGHT = {"lights": [{"color": {"red": 31, "green": 31, "blue": 31},
                             "direction": {"x": 0.463, "y": -0.879, "z": -0.114}}],
                 "diffuseColor": {"red": 16, "green": 16, "blue": 16}, "ambientColor": {"red": 10, "green": 10, "blue": 10},
                 "emissionColor": {"red": 12, "green": 12, "blue": 12}}


def render(meshes, texcache, path, target=None, light=None, w=384, h=288, top=None, scale=2, bg=(0.06, 0.05, 0.10),
           zoom=1.0, target_h=1.0, marks=()):
    """meshes: [mesh dict (nsbmd.model_to_mesh, absolute tiles)]. target (x, z): field camera on that tile.
    top (x0, z0, x1, z1): orthographic top-down of that tile rect instead (w = px per tile * width).
    marks: [(x, z, rgb)] small squares drawn on tile centres (top views)."""
    from PIL import Image
    lc, dif, amb, emi, ldir, spc = light_terms(light or DEFAULT_LIGHT)
    img = np.zeros((h, w, 3))
    img[:] = bg
    zb = np.full((h, w), np.inf)
    if top is None:
        p = math.radians(PITCH)
        tx, tz = target
        tgt = np.array([(tx + 0.5) * 16, 16.0 * target_h + 0.0, (tz + 0.5) * 16])
        cam = tgt + np.array([0, DIST * math.sin(p), DIST * math.cos(p)])
        fwd = (tgt - cam) / np.linalg.norm(tgt - cam)
        right = np.cross(fwd, [0, 1, 0])
        right /= np.linalg.norm(right)
        up = np.cross(right, fwd)
        f = 1 / math.tan(math.radians(HALF_FOV)) * zoom
    for me_all in meshes:
        mats = {m["name"]: m for m in me_all["materials"]}
        for me in me_all["meshes"]:
            m = mats[me["material"]]
            pa = m.get("polygon_attr", {})
            lit = pa.get("lights", 1) != 0
            two = pa.get("cull", "back") != "back"
            alpha = m.get("alpha", pa.get("alpha", 31)) / 31.0
            T = texcache.get(m["texture"], m["palette"])
            th, tw = T.shape[:2]
            P = np.array(me["positions"], float) * 16 + [0, 16, 0]
            if not len(P):
                continue
            UV = np.array(me["uvs"], float)
            if lit:
                NO = np.array([n if n else [0, 1, 0] for n in me["normals"]], float) if me.get("normals") else \
                    np.tile([0.0, 1.0, 0.0], (len(P), 1))
                ndl = np.clip(NO @ ldir, 0, 1)[:, None]
                # GX: emission + ambient * light + diffuse * light * N.L + specular * light * level (no shininess
                # table: the level is ~(N.H)^2, approximated from N.L)
                VC = np.clip(emi + amb * lc + dif * lc * ndl + spc * lc * ndl ** 2 * 0.5, 0, 1)
            else:
                VC = np.array(me["colors"], float) / 255.0 if me.get("colors") else np.ones((len(P), 3))
            if top is None:
                rel = P - cam
                xc, yc, zc = rel @ right, rel @ up, rel @ fwd
                zc = np.where(zc < 1e-3, 1e-3, zc)
                sx = w / 2 + xc / zc * f * h / 2
                sy = h / 2 - yc / zc * f * h / 2
                dep = zc
            else:
                x0, z0, x1, z1 = top
                sx = (P[:, 0] / 16 - x0) / (x1 - x0) * w
                sy = (P[:, 2] / 16 - z0) / (z1 - z0) * h
                dep = 10000.0 - P[:, 1]
                zc = np.ones(len(P))
            tris = [tuple(q) for q in me["tris"]] + [t for q in me["quads"] for t in ((q[0], q[1], q[2]), (q[0], q[2], q[3]))]
            for a, b, c in tris:
                if top is None and min(zc[a], zc[b], zc[c]) < 50:
                    continue
                X0, Y0, X1, Y1, X2, Y2 = sx[a], sy[a], sx[b], sy[b], sx[c], sy[c]
                area = (X1 - X0) * (Y2 - Y0) - (X2 - X0) * (Y1 - Y0)
                if area == 0 or (area > 0 and not two):
                    continue
                bx0, bx1 = max(int(min(X0, X1, X2)), 0), min(int(max(X0, X1, X2)) + 1, w)
                by0, by1 = max(int(min(Y0, Y1, Y2)), 0), min(int(max(Y0, Y1, Y2)) + 1, h)
                if bx0 >= bx1 or by0 >= by1:
                    continue
                gy, gx = np.mgrid[by0:by1, bx0:bx1] + 0.5
                w0 = ((X1 - gx) * (Y2 - gy) - (X2 - gx) * (Y1 - gy)) / area
                w1 = ((X2 - gx) * (Y0 - gy) - (X0 - gx) * (Y2 - gy)) / area
                w2 = 1 - w0 - w1
                msk = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
                if not msk.any():
                    continue
                if top is None:
                    iz = w0 / zc[a] + w1 / zc[b] + w2 / zc[c]
                    depth = 1 / iz
                    pu = (w0 * UV[a, 0] / zc[a] + w1 * UV[b, 0] / zc[b] + w2 * UV[c, 0] / zc[c]) * depth
                    pv = (w0 * UV[a, 1] / zc[a] + w1 * UV[b, 1] / zc[b] + w2 * UV[c, 1] / zc[c]) * depth
                else:
                    depth = w0 * dep[a] + w1 * dep[b] + w2 * dep[c]
                    pu = w0 * UV[a, 0] + w1 * UV[b, 0] + w2 * UV[c, 0]
                    pv = w0 * UV[a, 1] + w1 * UV[b, 1] + w2 * UV[c, 1]
                sub = zb[by0:by1, bx0:bx1]
                msk &= depth < sub
                if not msk.any():
                    continue
                tc = T[np.floor(pv * th).astype(int) % th, np.floor(pu * tw).astype(int) % tw]
                msk &= tc[..., 3] > 0.5
                if not msk.any():
                    continue
                shade = w0[..., None] * VC[a] + w1[..., None] * VC[b] + w2[..., None] * VC[c]
                col = np.clip(tc[..., :3] * shade, 0, 1)
                reg = img[by0:by1, bx0:bx1]
                if alpha < 0.99:
                    reg[msk] = reg[msk] * (1 - alpha) + col[msk] * alpha
                else:
                    reg[msk] = col[msk]
                    sub[msk] = depth[msk]
    if top is not None:
        x0, z0, x1, z1 = top
        for mx, mz, rgb in marks:
            cx, cy = (mx + 0.5 - x0) / (x1 - x0) * w, (mz + 0.5 - z0) / (z1 - z0) * h
            r = max(1, int(w / (x1 - x0) * 0.22))
            img[max(0, int(cy) - r):int(cy) + r, max(0, int(cx) - r):int(cx) + r] = np.array(rgb) / 255.0
    Image.fromarray((np.clip(img, 0, 1) * 255).astype("uint8")).resize((w * scale, h * scale), Image.NEAREST).save(path)

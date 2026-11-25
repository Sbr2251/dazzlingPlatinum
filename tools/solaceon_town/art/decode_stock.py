#!/usr/bin/env python3
"""Step 1 of the Solaceon texture kit: decode the stock textures it has to match, and measure the stock look.

Usage: python3 tools/solaceon_town/art/decode_stock.py [--out DIR]

Writes (DIR defaults to common.preview_dir()):
  stock_set010/<texture>.png + .json     every texture of map texture set 010 (Solaceon, Celestic, Routes 209, 210,
                                         211 East, 215), with the palette the area-0xA chunk models bind to it
  stock_set010_sheet.png                 labelled contact sheet (name, size, format, palette, swatches)
  stock_set010_palettes.png              every palette of set 010 as swatches
  stock_props_<town>/ + _sheet.png       the building (map prop) textures of Solaceon, Eterna, Hearthome, Veilstone
                                         (areabm_texset of each town's area), with the palettes their models bind
  stock_density.txt                      texels per tile, per material, for Solaceon chunks 072/073 and the stock
                                         buildings (ground / wall / roof faces separately)
All stock data is read from git at common.BASE_REV.
"""
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402
import png  # noqa: E402

SOL_CHUNKS = [72, 73]                     # Solaceon Town
AREA_A_CHUNKS = [72, 73, 68, 74]          # + Route 210 South, Route 209 (for palette pairing)
DENSITY_MODELS = {                         # build_model index -> what it is
    4: "pc (Pokemon Center)", 5: "fs (Poke Mart)", 197: "t4_h01 (Solaceon house)", 198: "t4_s01 (Solaceon Day Care)",
    202: "t5_s01 (Celestic)", 205: "r210h02 (Route 210 house)", 37: "t3_s01 (Eterna)", 62: "c4_s01 (Eterna)",
    188: "c5_h01 (Hearthome house)", 190: "c5_b01 (Hearthome bldg)", 206: "c7_h01 (Veilstone house)",
    208: "c7_s02a (Veilstone warehouse)", 210: "c7_o01a (Veilstone container)",
}


# stock pairs the chunk scan gets wrong or misses (blueglay is bound to the memorial wall's sol_stone in 072)
PAIR_OVERRIDES = {"blueglay": "blueglay", "conttree_b": "conttree", "conttree_t": "conttree", "tree04_2": "tree01"}


def chunk_pairs(chunks):
    out = dict(PAIR_OVERRIDES)
    for c in chunks:
        m, _ = C.map_model(c)
        for mat in m["materials"]:
            if mat["texture"] and mat["palette"]:
                out.setdefault(mat["texture"], mat["palette"])
    return out


def model_pairs(models):
    out = {}
    for m in models:
        for mat in m["materials"]:
            if mat["texture"] and mat["palette"]:
                out.setdefault(mat["texture"], mat["palette"])
    return out


def dump_set(s, pairs, out_dir, sheet_path, title):
    os.makedirs(out_dir, exist_ok=True)
    pals = {p["name"]: p for p in s["palettes"]}
    items, info = [], []
    for t in s["textures"]:
        pn = nsbtx.guess_palette(t["name"], pals, pairs)
        colors = pals[pn]["colors"] if pn else None
        rgba = C.decode_rgba(t, colors)
        fmt = nsbtx.FMT_NAMES[t["fmt"]]
        idx = C.decode_indices(t) if t["fmt"] in (1, 2, 3, 4, 6) else None
        used = sorted({v for r in idx for v in r}) if idx else []
        png.write_rgba(os.path.join(out_dir, t["name"] + ".png"), t["w"], t["h"], rgba)
        meta = {"format": fmt, "size": [t["w"], t["h"]], "palette": pn, "c0": t["c0"], "used_indices": used,
                "palette_rgb": [list(nsbtx.rgb(c)) for c in colors] if colors else None,
                "bytes": len(t["data"])}
        json.dump(meta, open(os.path.join(out_dir, t["name"] + ".json"), "w"))
        info.append((t["name"], meta))
        pal_show = [nsbtx.rgb(colors[i]) for i in used if i < len(colors)] if colors and used else None
        items.append(([f"{t['name']} {t['w']}x{t['h']}", f"{fmt} {pn or '?'} {len(used)}C"], rgba, pal_show))
    C.contact_sheet(sheet_path, items, title)
    return info


def palette_sheet(s, path, title):
    cv = C.Canvas(8 + 4 * 18 + 16 * 12 + 8, 24 + len(s["palettes"]) * 12 + 8)
    cv.text(6, 6, title, (255, 230, 150), 2)
    for k, p in enumerate(s["palettes"]):
        y = 24 + k * 12
        cv.text(6, y + 2, p["name"][:16])
        cv.swatches(8 + 4 * 18, y, [nsbtx.rgb(c) for c in p["colors"][:16]], 12)
    cv.save(path)


# ---------------------------------------------------------------------------------------------------------------
# texel density
# ---------------------------------------------------------------------------------------------------------------

def node_scale(model):
    import struct
    sc = []
    for n in model["nodes"]:
        d = bytes.fromhex(n["data"])
        flag = struct.unpack_from("<H", d)[0]
        o = 4 + (0 if flag & 1 else 12) + (0 if flag & 2 else 0)
        s = 1.0
        if not flag & 4:
            # translation (12 B unless flag 1), rotation (flag 2 = identity; else pivot/compressed), then scale
            if flag & 2:
                s = struct.unpack_from("<i", d, o)[0] / 4096
        sc.append(s)
    return sc


def face_stats(mesh, sizes):
    """{material: {"ground"|"wall"|"roof": [texels per tile per edge]}}"""
    out = {}
    for me, mat in zip(mesh["meshes"], [None] * len(mesh["meshes"])):
        m = next(x for x in mesh["materials"] if x["name"] == me["material"])
        w, h = sizes.get(m["texture"], m["size"])
        P, U = me["positions"], me["uvs"]
        for f in me["tris"] + me["quads"]:
            a, b, c = P[f[0]], P[f[1]], P[f[2]]
            u = [b[k] - a[k] for k in range(3)]
            v = [c[k] - a[k] for k in range(3)]
            n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
            ln = math.sqrt(sum(x * x for x in n)) or 1
            ny = abs(n[1]) / ln
            kind = "ground" if ny > 0.9 else "wall" if ny < 0.25 else "roof"
            for i in range(len(f)):
                p, q = P[f[i]], P[f[(i + 1) % len(f)]]
                L = math.sqrt(sum((p[k] - q[k]) ** 2 for k in range(3)))
                if L < 0.2:
                    continue
                du = (U[f[i]][0] - U[f[(i + 1) % len(f)]][0]) * w
                dv = (U[f[i]][1] - U[f[(i + 1) % len(f)]][1]) * h
                out.setdefault(m["name"] + ":" + str(m["texture"]), {}).setdefault(kind, []).append(
                    math.hypot(du, dv) / L)
    return out


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


def density_report(lines):
    s = C.set010()
    sizes = {t["name"]: (t["w"], t["h"]) for t in s["textures"]}
    for c in SOL_CHUNKS:
        m, _ = C.map_model(c)
        mesh = nsbmd.model_to_mesh(m, (0, 0))
        lines.append(f"chunk {c:03d} (set 010 terrain)")
        for k, d in sorted(face_stats(mesh, sizes).items()):
            lines.append("  %-26s " % k + "  ".join(f"{kind} {med(v):5.1f} (n{len(v)})" for kind, v in sorted(d.items())))
    psets = {}
    for i, what in DENSITY_MODELS.items():
        m = C.build_model(i)
        mesh = nsbmd.model_to_mesh(m, (0, 0))
        sc = node_scale(m)
        lines.append(f"build model {i} {what}  pos_scale {m['info']['pos_scale'] / 4096:g}  node scales {sc}")
        stats = face_stats(mesh, {})
        for k, d in sorted(stats.items()):
            lines.append("  %-26s " % k + "  ".join(f"{kind} {med(v) / (sc[0] or 1):5.1f} (n{len(v)})"
                                                     for kind, v in sorted(d.items())))
        # extents in tiles
        P = [p for me in mesh["meshes"] for p in me["positions"]]
        ext = [max(p[k] for p in P) - min(p[k] for p in P) for k in range(3)]
        lines.append("  extent (tiles) x %.2f h %.2f z %.2f" % tuple(e * sc[0] for e in ext))
    return psets


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else C.preview_dir()
    s = C.set010()
    pairs = chunk_pairs(AREA_A_CHUNKS)
    info = dump_set(s, pairs, os.path.join(out, "stock_set010"), os.path.join(out, "stock_set010_sheet.png"),
                    f"SET 010 AT {C.BASE_REV} ({len(s['textures'])} TEXTURES)")
    palette_sheet(s, os.path.join(out, "stock_set010_palettes.png"), "SET 010 PALETTES")
    tv, pv = nsbtx.vram_usage(s)
    lines = [f"set 010 at {C.BASE_REV}: {len(s['textures'])} textures, {len(s['palettes'])} palettes, "
             f"VRAM {tv} + {pv} = {tv + pv} B"]
    for area, town in C.TOWN_AREAS.items():
        props, tex, light = C.area_entry(area)
        ids = C.area_props(props)
        ps = C.prop_texset(props)
        models = [C.build_model(i) for i in ids]
        mp = model_pairs(models)
        dump_set(ps, mp, os.path.join(out, f"stock_props_{town}"), os.path.join(out, f"stock_props_{town}_sheet.png"),
                 f"{town.upper()} BUILDINGS (AREA {area:#x}: PROPS {props}, MAP SET {tex:03d})")
        pv2 = nsbtx.vram_usage(ps)
        lines.append(f"area {area:#x} {town}: map set {tex:03d}, props list {props} = "
                     f"{', '.join(f'{i} {m['name']}' for i, m in zip(ids, models))}; prop textures {sum(pv2)} B")
    density_report(lines)
    open(os.path.join(out, "stock_density.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("wrote", out)


if __name__ == "__main__":
    main()

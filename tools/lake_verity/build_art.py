#!/usr/bin/env python3
"""Assembles the art agent's exports into Lake Verity map data (standard library only).

    python3 tools/lake_verity/build_art.py [--assets DIR] [--write] [--preview DIR] [--keep-lake | --drop-lake]
                                           [--new-set] [--art-terrain]

Terrain modes:
  default (stock terrain)  every chunk keeps the stock terrain (water, trees, shores, grass, paths; same geometry,
                         materials and textures), minus what rises above the water inside the redesign footprint
                         (old island, Verity Cavern hut) and the lakebed under the island's interior. The only new
                         terrain is the castle island, clipped out of the art chunk meshes (in_island), without
                         the natural materials (ISLAND_DROP: lv_water, lv_foam, lv_canopy, lv_path); lv_grass is
                         redrawn with stock "tshadow" (GRASS_REMAP). Vertical island/prop faces that end under
                         the water get skirt quads down to the lakebed (h -4). The l_lake water prop stays.
  --art-terrain            the art chunk meshes replace the stock terrain completely (the older mode).
Only textures the result uses go into the set and fldtanime.

Inputs (PLAN.md "Intermediate mesh format"), default DIR = tools/lake_verity/assets:
  chunk_<id>.mesh.json   the art's terrain for that chunk (see the modes above).
  <other>.mesh.json      props (castle, bridge, portal, ...), absolute tile positions; split into the chunks
                         by face centroid and merged into the chunk models.
  textures/<name>.png + <name>.json  {"format", "repeat", "c0", optional "palette", "frames": [names],
                         "frame_ticks"}. Textures listed as another texture's frames are animation frames: they
                         go into fldtanime, not the texture set, re-indexed together with the base texture onto
                         one palette.

Outputs (only with --write; otherwise a dry run that prints the report):
  res/field/maps/data/map_data_{537,538,540,541}.bin    terrain + props + layout permissions/BDHC
  res/field/maps/texture_sets/map_texture_set_061.nsbtx  stock set 61 with the new textures appended
                                                         (area 62 is shared, so nothing stock is removed)
  res/prebuilt/data/fldtanime.narc                      one entry + frame NSBTX per texture with "frames"

--new-set: instead of growing the shared set 61, write stock set 61 + the new textures as a new set
(map_texture_set_075.nsbtx, registered in meson.build and map_texture_set.order) and append a copy of area data
entry 62 that uses it (area_data.narc entry 76 = 0x4C). Set 61 stays stock. The map header is not touched:
MAP_HEADER_LAKE_VERITY's areaDataArchiveID must then be set to the printed id (include/data/map_headers.h), or
Lake Verity will draw the art with missing textures. Re-running rewrites the same set and entry.

Lighting: materials whose meshes carry "colors" and do not set polygon_attr.lights are built unlit (lights 0),
so the baked vertex colours are what the DS draws (stock map materials are lit and have no colours).
The stock l_lake prop (animated water plane) is dropped when the result uses an "lv_water" texture (only
possible with --art-terrain), unless --keep-lake is given. fldtanime always starts from the stock archive.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "coronet_lava"))

import assemble  # noqa: E402
import collision  # noqa: E402
import layout  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402
import png  # noqa: E402

FLDTANIME = os.path.join(assemble.ROOT, "res", "prebuilt", "data", "fldtanime.narc")
AREA_DATA = os.path.join(assemble.ROOT, "res", "prebuilt", "fielddata", "areadata", "area_data.narc")
TEXSETS = os.path.join(assemble.ROOT, "res", "field", "maps", "texture_sets")
NEW_SET = 75                 # first free map texture set (074 is the Coronet lava set)
BASE_AREA = 62               # stock Lake Verity area: props list 58, set 61, light 0
ANIME_ENTRY = 16 + 18 * 2
HEIGHT_TOL = 0.25            # tiles
# stock-terrain mode (default): natural art materials that the stock terrain replaces, and art materials that are
# redrawn with a stock set-61 texture: {art texture: (stock texture, tiles per texture repeat)}
ISLAND_DROP = {"lv_water", "lv_foam", "lv_canopy", "lv_path"}
GRASS_REMAP = {"lv_grass": ("tshadow", 2.0)}     # the stock lake-shore ground (u = x / 2, v = z / 2 as in stock)
SKIRT_TOP, SKIRT_BOTTOM = -0.9, -4.0             # island sides below the water go down to the stock lakebed


def load_assets(adir):
    chunks, props = {}, []
    for f in sorted(os.listdir(adir)):
        if not f.endswith(".mesh.json"):
            continue
        m = json.load(open(os.path.join(adir, f)))
        stem = f[:-len(".mesh.json")]
        if stem.startswith("chunk_") and stem[6:].isdigit():
            chunks[int(stem[6:])] = m
        else:
            props.append(m)
    return chunks, props


def share_palette(imgs, fmt, c0):
    """Re-indexes several RGBA images (an animation) onto one palette, so the frames can be copied over the base
    texture's texels without swapping its palette. -> list of indexed png.Image."""
    maxn = {"pltt4": 4, "pltt16": 16, "pltt256": 256, "a3i5": 32, "a5i3": 8}[fmt]
    alpha_fmt = fmt in ("a3i5", "a5i3")
    reserve0 = bool(c0) and not alpha_fmt
    cols = [None] if reserve0 else []
    out = []
    for img in imgs:
        rows = []
        for row in img.pixels:
            r = []
            for p in row:
                if reserve0 and p[3] < 128:
                    r.append(0)
                    continue
                c = tuple(v >> 3 << 3 for v in p[:3])
                if c not in cols:
                    cols.append(c)
                r.append(cols.index(c))
            rows.append(r)
        out.append(rows)
    assert len(cols) <= maxn, f"animation uses {len(cols)} colours, {fmt} allows {maxn}"
    pal = [(0, 0, 0, 0) if c is None else c + (255,) for c in cols]
    res = []
    for img, rows in zip(imgs, out):
        px = img.pixels if alpha_fmt else [[pal[i] for i in r] for r in rows]
        res.append(png.Image(img.width, img.height, px, palette=pal, indices=rows))
    return res


def load_textures(tdir):
    """-> (textures, palettes, metas {name: json}, animations {name: (frame images, ticks)})."""
    metas = {f[:-5]: json.load(open(os.path.join(tdir, f))) for f in sorted(os.listdir(tdir)) if f.endswith(".json")}
    tex, pals, anims = [], [], {}
    frame_only = {f for n, m in metas.items() for f in m.get("frames", []) if f != n}
    for n, meta in sorted(metas.items()):
        if n in frame_only:          # animation frames live in fldtanime, not in the texture set
            continue
        fmt = meta.get("format", "pltt16")
        img = png.read(os.path.join(tdir, n + ".png"))
        if meta.get("frames"):
            frames = [png.read(os.path.join(tdir, f + ".png")) for f in meta["frames"]]
            shared = share_palette([img] + frames, fmt, meta.get("c0"))
            img, frames = shared[0], shared[1:]
            anims[n] = (frames, meta.get("frame_ticks", 4))
        t, p = nsbtx.encode_texture(n, img, fmt, meta.get("c0"))
        tex.append(t)
        if p:
            p["name"] = meta.get("palette", p["name"])
            pals.append(p)
    return tex, pals, metas, anims


def set_lighting(mesh):
    """Unlit (baked colours) for materials without an explicit lights value whose meshes have colours."""
    coloured = {me["material"] for me in mesh["meshes"] if me.get("colors")}
    mats = []
    for m in mesh.get("materials", []):
        pa = dict(m.get("polygon_attr", {}))
        if "lights" not in pa and m["name"] in coloured:
            pa["lights"] = 0
        mats.append(dict(m, polygon_attr=pa))
    return dict(mesh, materials=mats)


def frame_btx(name, frames, meta):
    """NSBTX with the frames as textures <name>.1 .. <name>.N. fldtanime copies their texels over <name>'s by
    index and never swaps the palette, so the frames are indexed on the base texture's palette (share_palette)."""
    texs = [nsbtx.encode_texture(f"{name}.{i + 1}"[:16], img, meta.get("format", "pltt16"), meta.get("c0"))[0]
            for i, img in enumerate(frames)]
    return nsbtx.build(texs, [])


def update_fldtanime(anims, metas, write):
    import narc
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".narc") as tmp:     # start from stock: dropped entries disappear
        tmp.write(assemble.stock_file("res/prebuilt/data/fldtanime.narc"))
        tmp.flush()
        header, btnf, files = narc.read_files(tmp.name)
    table = bytearray(files[0])
    count = int.from_bytes(table[:4], "little")
    names = [bytes(table[4 + i * ANIME_ENTRY:20 + i * ANIME_ENTRY]).rstrip(b"\0") for i in range(count)]
    report = []
    for name, (frames, ticks) in sorted(anims.items()):
        assert len(frames) < 18, f"{name}: at most 17 frames"
        entry = bytearray(name.encode().ljust(16, b"\0") + b"\xff" * 36)
        for i in range(len(frames)):
            entry[16 + 2 * i:18 + 2 * i] = bytes((i, ticks))
        btx = frame_btx(name, frames, metas[name])
        key = name.encode()
        if key in names:
            idx = names.index(key)
            table[4 + idx * ANIME_ENTRY:4 + (idx + 1) * ANIME_ENTRY] = entry
        else:
            idx = count
            table[4 + count * ANIME_ENTRY:4 + count * ANIME_ENTRY] = entry
            count += 1
            names.append(key)
            table[:4] = count.to_bytes(4, "little")
            files.append(b"")
        files[idx + 1] = btx
        report.append(f"{name}: {len(frames)} frames x {ticks} vblanks -> fldtanime member {idx + 1}")
    files[0] = bytes(table)
    if write:
        narc.write_files(FLDTANIME, header, btnf, files)
    return report


def write_new_area(new_set):
    """Writes set NEW_SET and an area data entry using it (see --new-set). -> area data id."""
    import narc
    name = f"map_texture_set_{NEW_SET:03d}.nsbtx"
    open(os.path.join(TEXSETS, name), "wb").write(new_set)
    mb = os.path.join(TEXSETS, "meson.build")
    s = open(mb).read()
    prev = f"'map_texture_set_{NEW_SET - 1:03d}.nsbtx'"
    if f"'{name}'" not in s:
        assert s.count(prev + "\n") == 1, f"{prev} is not the last set in {mb}"
        s = s.replace(prev + "\n", f"{prev},\n    '{name}'\n")
        open(mb, "w", newline="").write(s)
    order = os.path.join(TEXSETS, "map_texture_set.order")
    lines = open(order, newline="").read().splitlines(keepends=True)
    if not any(ln.strip() == name for ln in lines):
        assert lines[-1].strip() == prev.strip("'"), f"{prev} is not the last line of {order}"
        eol = lines[-1][len(lines[-1].rstrip("\r\n")):] or "\n"
        lines[-1] = lines[-1].rstrip("\r\n") + eol
        lines.append(name + eol)
        open(order, "w", newline="").write("".join(lines))
    header, btnf, files = narc.read_files(AREA_DATA)
    props, _, dummy, light = struct.unpack("<4H", files[BASE_AREA])
    entry = struct.pack("<4H", props, NEW_SET, dummy, light)
    ids = [i for i, f in enumerate(files) if struct.unpack("<4H", f)[1] == NEW_SET]
    area = ids[0] if ids else len(files)
    files = files[:area] + [entry] + files[area + 1:]
    narc.write_files(AREA_DATA, header, btnf, files)
    return area


def in_island(cx, cz, margin=0.7):
    """True if the point (tiles) lies on the castle island (layout.ISLAND with its octagon corner cuts), grown by
    margin so the island's edge faces (cliffs, grass fringe) are included but the lake shores are not."""
    x0, z0, x1, z1 = layout.ISLAND
    if not (x0 - margin <= cx <= x1 + 1 + margin and z0 - margin <= cz <= z1 + 1 + margin):
        return False
    dx, dz = min(cx - x0, x1 + 1 - cx), min(cz - z0, z1 + 1 - cz)
    return dx + dz >= 2 - margin * 1.42


def _face_normal(P, f):
    a, b, c = P[f[0]], P[f[1]], P[f[2]]
    u = [b[i] - a[i] for i in range(3)]
    w = [c[i] - a[i] for i in range(3)]
    n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
    ln = sum(v * v for v in n) ** 0.5 or 1.0
    return [v / ln for v in n]


def island_part(mesh, stock):
    """The castle island out of an art chunk mesh (stock-terrain mode): faces whose centroid is on the island,
    without the natural materials (ISLAND_DROP; the stock terrain draws water, trees and shores). Materials in
    GRASS_REMAP are redrawn with the stock set-61 texture and the stock material (lit, stock UV scale)."""
    tex_of = {m["name"]: m.get("texture", m["name"]) for m in mesh.get("materials", [])}
    stock_mat = {m.get("texture"): m for m in stock["materials"]}
    mats, meshes = {}, []
    for me in mesh["meshes"]:
        tex = tex_of.get(me["material"], me["material"])
        if tex in ISLAND_DROP:
            continue
        P = me["positions"]
        keep = {}
        for key in ("tris", "quads"):
            keep[key] = [f for f in me.get(key, [])
                         if in_island(sum(P[i][0] for i in f) / len(f), sum(P[i][2] for i in f) / len(f))]
        if not keep["tris"] and not keep["quads"]:
            continue
        if tex in GRASS_REMAP:
            sm, rep = stock_mat[GRASS_REMAP[tex][0]], GRASS_REMAP[tex][1]
            mats[sm["name"]] = sm
            meshes.append({"material": sm["name"], "positions": P, "uvs": [[p[0] / rep, p[2] / rep] for p in P],
                           "normals": None, "colors": None, **keep})
        else:
            mats[me["material"]] = next(m for m in mesh["materials"] if m["name"] == me["material"])
            meshes.append(dict(me, **keep))
    return {"name": mesh["name"] + "_island", "materials": list(mats.values()), "meshes": meshes}


def add_skirts(mesh):
    """Extends every vertical face whose bottom edge is under the water (h <= SKIRT_TOP) down to the lakebed
    (SKIRT_BOTTOM) with a quad in the same material, so no gap shows through the translucent l_lake water where
    the island meets the lake. Colours are darkened, UVs repeat the bottom edge. -> (mesh, skirts added)."""
    out, added = [], 0
    for me in mesh["meshes"]:
        P = [list(p) for p in me["positions"]]
        uv = [list(u) for u in me.get("uvs") or [[0, 0]] * len(P)]
        col = me.get("colors")
        col = [list(c) for c in col] if col else None
        nrm = me.get("normals")
        nrm = list(nrm) if nrm else None
        quads = [list(q) for q in me.get("quads", [])]
        for f in me.get("tris", []) + me.get("quads", []):
            if abs(_face_normal(P, f)[1]) > 0.1:
                continue
            for k in range(len(f)):
                a, b = f[k], f[(k + 1) % len(f)]
                if P[a][1] <= SKIRT_TOP and P[b][1] <= SKIRT_TOP and abs(P[a][1] - P[b][1]) < 1e-3:
                    base = len(P)
                    for v in (a, b):
                        P.append([P[v][0], SKIRT_BOTTOM, P[v][2]])
                        uv.append(list(uv[v]))
                        if col:
                            col.append([c // 2 for c in col[v]])
                        if nrm:
                            nrm.append(nrm[v])
                    quads.append([b, a, base, base + 1])
                    added += 1
        out.append(dict(me, positions=P, uvs=uv, colors=col, normals=nrm, quads=quads))
    return dict(mesh, meshes=out), added


def height_report(models):
    """Walkable tiles whose drawn floor (the upward face through the tile centre closest to the layout height)
    is more than HEIGHT_TOL tiles off the layout/BDHC height."""
    t = layout.tiles()
    faces = []
    for c, model in models.items():
        for me in nsbmd.model_to_mesh(model, layout.CHUNKS[c])["meshes"]:
            P = me["positions"]
            for f in me["tris"] + [[q[0], q[1], q[2]] for q in me["quads"]] + [[q[0], q[2], q[3]] for q in me["quads"]]:
                faces.append([P[i] for i in f])
    grid = {}
    for tri in faces:
        (ax, ah, az), (bx, bh, bz), (cx, ch, cz) = tri
        den = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
        if abs(den) < 1e-9:
            continue
        for x in range(int(min(ax, bx, cx)), int(max(ax, bx, cx)) + 1):
            for z in range(int(min(az, bz, cz)), int(max(az, bz, cz)) + 1):
                px, pz = x + 0.5, z + 0.5
                l1 = ((bz - cz) * (px - cx) + (cx - bx) * (pz - cz)) / den
                l2 = ((cz - az) * (px - cx) + (ax - cx) * (pz - cz)) / den
                l3 = 1 - l1 - l2
                if min(l1, l2, l3) >= -1e-6:
                    grid.setdefault((x, z), []).append(l1 * ah + l2 * bh + l3 * ch)
    bad = []
    for c in models:
        cx, cz = layout.CHUNKS[c]
        for x in range(cx * 32, cx * 32 + 32):
            for z in range(cz * 32, cz * 32 + 32):
                coll, h, kind = t[(x, z)]
                if kind == "water" or coll != 0:
                    continue
                hs = grid.get((x, z))
                best = min(hs, key=lambda v: abs(v - h)) if hs else None
                if best is None or abs(best - h) > HEIGHT_TOL:
                    bad.append((x, z, kind, h, None if best is None else round(best, 3)))
    return bad


def main():
    args = sys.argv[1:]
    adir = args[args.index("--assets") + 1] if "--assets" in args else os.path.join(HERE, "assets")
    write = "--write" in args
    preview = args[args.index("--preview") + 1] if "--preview" in args else None
    tdir = os.path.join(adir, "textures")
    art_terrain = "--art-terrain" in args
    chunk_meshes, props = load_assets(adir)
    tex, pals, metas, anims = load_textures(tdir)

    fp = assemble.footprint()
    stock = {c: assemble.stock_mesh(c) for c in assemble.CHUNKS}
    props = [set_lighting(p) for p in props]
    skirts = 0
    if art_terrain:
        bases = {c: set_lighting(chunk_meshes[c]) if c in chunk_meshes else assemble.cut_stock(stock[c][0], fp)
                 for c in assemble.CHUNKS}
    else:
        # stock terrain everywhere, minus what rises above the water inside the footprint (old island, hut);
        # the stock lakebed is kept except under the island's interior (tiles whose 8 neighbours are all in the
        # footprint: hidden under the island top, and the skirts close the sides), plus the art's island edge
        interior = {(x, z) for (x, z) in fp
                    if all((x + dx, z + dz) in fp for dx in (-1, 0, 1) for dz in (-1, 0, 1))}
        bases, island = {}, []
        for c in assemble.CHUNKS:
            bases[c] = assemble.cut_stock(stock[c][0], fp, keep_under=fp - interior)
            if c in chunk_meshes:
                part, n = add_skirts(island_part(set_lighting(chunk_meshes[c]), stock[c][0]))
                skirts += n
                island.append(part)
        sk = [add_skirts(p) for p in props]
        props = [p for p, n in sk] + island
        skirts += sum(n for p, n in sk)
        # only the textures the result uses go into the set / fldtanime
        used = {m.get("texture") for p in props for m in p.get("materials", [])}
        tex = [t for t in tex if t["name"] in used]
        names = {t["name"] for t in tex}
        pals = [p for p in pals if any(metas[n].get("palette", n + "_pl") == p["name"] for n in names)]
        anims = {n: a for n, a in anims.items() if n in names}

    new_area = "--new-set" in args
    stock_set = assemble.stock_texset()
    s = nsbtx.parse(stock_set)
    clash = sorted({t["name"] for t in tex} & {t["name"] for t in s["textures"]})
    assert not clash, f"texture names already in set 61: {clash}"
    new_set = nsbtx.build(s["textures"] + tex, s["palettes"] + pals, pal_flag=s["header"]["pal_flag"])
    texel, pal_b = nsbtx.vram_usage(nsbtx.parse(new_set))
    textures = assemble.texture_table(new_set)

    uses_water = any(m.get("texture") == "lv_water" for mm in list(bases.values()) + props
                     for m in mm.get("materials", []))
    keep_lake = "--keep-lake" in args or ("--drop-lake" not in args and not uses_water)

    prop_parts = {}
    for p in props:
        for c, part in assemble.split_by_chunk(p).items():
            prop_parts.setdefault(c, []).append(part)
    stats, models, outs = [], {}, {}
    for c in assemble.CHUNKS:
        smesh, sec, smodel = stock[c]
        mesh = assemble.merge([bases[c]] + prop_parts.get(c, []), smodel["name"])
        model = nsbmd.mesh_to_model(mesh, layout.CHUNKS[c], name=smodel["name"], textures=textures)
        missing = sorted({m["texture"] for m in model["materials"]} - set(textures))
        assert not missing, f"chunk {c}: textures missing from the set: {missing}"
        nsb = nsbmd.build_bmd([model])
        bd = collision.bdhc(c)
        outs[c] = mapdata.pack(collision.permissions(c), sec["props"] if keep_lake else b"", nsb, bd)
        st = nsbmd.model_stats(model)
        stats.append({"chunk": c, "polygons": st["polygons"], "vertices_sent": st["vertices_sent"],
                      "model_bytes": len(nsb), "bdhc_bytes": len(bd), "materials": len(model["materials"]),
                      "source": ("art" if c in chunk_meshes else "stock-cut") if art_terrain else "stock+island"})
        models[c] = model
        if preview:
            os.makedirs(preview, exist_ok=True)
            json.dump(nsbmd.model_to_mesh(nsbmd.parse_bmd(nsb)["models"][0], layout.CHUNKS[c], name=f"chunk_{c}"),
                      open(os.path.join(preview, f"chunk_{c}.mesh.json"), "w"))

    anim_report = update_fldtanime(anims, metas, write)
    import build_graybox
    win, at = build_graybox.view_window_polys(models)
    heights = height_report(models)

    print(f"assets: {adir}")
    print(f"texture set 61: {len(s['textures'])} stock + {len(tex)} new textures, VRAM {texel} + {pal_b} = "
          f"{texel + pal_b} bytes (stock 44320, largest stock set {assemble.VRAM_PROVEN})")
    print(f"terrain: {'art chunk meshes (--art-terrain)' if art_terrain else 'stock + art island'}, "
          f"{skirts} underwater skirt quads")
    print(f"new textures: {', '.join(t['name'] for t in tex)}")
    print(f"l_lake water prop: {'kept' if keep_lake else 'dropped (assets bring lv_water)'}")
    for s_ in stats:
        print(f"chunk {s_['chunk']} ({s_['source']}): {s_['polygons']} polys, {s_['vertices_sent']} verts, "
              f"model {s_['model_bytes']} B, BDHC {s_['bdhc_bytes']} B, {s_['materials']} materials")
    print(f"worst 16x12-tile window: {win} polygons at {at}")
    for line in anim_report:
        print("anim " + line)
    print(f"walkable tiles whose drawn floor is > {HEIGHT_TOL} tile off the layout height: {len(heights)}")
    for b in heights[:20]:
        print("   ", b)
    cams = assemble.camera_polys(models)
    for name, culled, unculled, at in cams:
        print(f"camera {name}: worst {culled} polygons on screen after culling ({unculled} in the frustum) at {at}")
    problems, warnings = assemble.check_budgets(stats, window_polys=win, camera=cams, vram=texel + pal_b)
    for w in warnings:
        print("warning: " + w)
    print("budgets ok" if not problems else "BUDGET PROBLEMS: " + "; ".join(problems))
    if write:
        if problems:
            raise SystemExit("not writing: fix the budget problems first")
        for c, data in outs.items():
            open(assemble.map_path(c), "wb").write(data)
        if new_area:
            area = write_new_area(new_set)
            open(assemble.TEXSET, "wb").write(stock_set)
            print(f"wrote map_texture_set_{NEW_SET:03d}.nsbtx and area data entry {area} (0x{area:X}); set 61 is stock."
                  f" Set MAP_HEADER_LAKE_VERITY.areaDataArchiveID = 0x{area:X} in include/data/map_headers.h")
        else:
            open(assemble.TEXSET, "wb").write(new_set)
            print("wrote map_texture_set_061.nsbtx")
        print("wrote map_data 537/538/540/541, fldtanime.narc")
    else:
        print("dry run (use --write to write the files)")


if __name__ == "__main__":
    main()

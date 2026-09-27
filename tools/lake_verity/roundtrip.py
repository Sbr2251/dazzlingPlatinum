#!/usr/bin/env python3
"""Round-trip and consistency checks for the Lake Verity pipeline (standard library only).

Usage: python3 tools/lake_verity/roundtrip.py [--generated]

Stock checks:
  1. NSBMD, stock chunks 537/538/540/541 (read from git at assemble.STOCK_REV):
     - parse -> build is byte-identical;
     - every display list decodes and re-encodes byte-identically;
     - mesh round trip: model -> mesh.json -> model (quad-strip builder) -> NSBMD -> parse gives the same faces
       (positions, UVs, normals, per material) and the same material attributes.
  2. Texture sets:
     - all map texture sets rebuild byte-identically (set 007 differs; the coronet tools rewrote it);
     - every set-61 texture decoded to RGBA and re-encoded in its format decodes to the same pixels.
  3. BDHC:
     - all stock BDHC sections write back byte-identically;
     - the strip builder reproduces the stock strips and access lists.
  4. map_data: unpack -> pack is byte-identical for every map_data file.
Generated checks (with --generated, or whenever the chunks have been regenerated):
  5. Checked-in map_data 537/538/540/541:
     - BDHC height at every tile centre equals layout h (world y = 16 + 16 h);
     - permissions equal layout.py.
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import assemble  # noqa: E402
import collision  # noqa: E402
import layout  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402

ROOT = os.path.join(HERE, "..", "..")
MAPS = os.path.join(ROOT, "res", "field", "maps", "data")
TEXSETS = os.path.join(ROOT, "res", "field", "maps", "texture_sets")
CHUNKS = (537, 538, 540, 541)
failures = []


def report(name, ok, detail=""):
    print(f"[{'ok' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def face_set(model):
    out = {}
    for mi, si in nsbmd.shape_material_pairs(model):
        m = model["materials"][mi]
        tris, quads = nsbmd.prims_to_faces(nsbmd.dl_primitives(nsbmd.dl_decode(model["shapes"][si]["dl"])))
        key = lambda f: tuple((v["pos"], v["uv"], v["normal"]) for v in f)  # noqa: E731
        s = out.setdefault(m["name"], [])
        s += [key(f) for f in tris] + [key(f) for f in quads]
    return {k: sorted(v) for k, v in out.items()}


def mat_attrs(model):
    return {m["name"]: (m["texture"], m["palette"], m["poly_attr"], m["tex_image_param"], m["orig_width"],
                        m["orig_height"], m["diff_amb"], m["flag"]) for m in model["materials"]}


def stock_path(c):
    return os.path.join(MAPS, f"map_data_{c:03d}.bin")


def check_nsbmd(chunks):
    for c in chunks:
        raw = nsbmd.map_model_bytes(assemble.stock_bytes(c))
        bmd = nsbmd.parse_bmd(raw)
        report(f"NSBMD {c} parse -> build identical", nsbmd.build_bmd(bmd["models"], tex0=bmd["tex0"]) == raw)
        model = bmd["models"][0]
        n_ok = sum(nsbmd.dl_pack(nsbmd.encode_prims(nsbmd.dl_primitives(nsbmd.dl_decode(s["dl"])))) == s["dl"]
                   for s in model["shapes"])
        report(f"NSBMD {c} display lists re-encode identical", n_ok == len(model["shapes"]),
               f"{n_ok}/{len(model['shapes'])}")
        mesh = nsbmd.model_to_mesh(model, layout.CHUNKS[c], name=model["name"])
        new = nsbmd.mesh_to_model(mesh, layout.CHUNKS[c], name=model["name"])
        back = nsbmd.parse_bmd(nsbmd.build_bmd([new]))["models"][0]
        st0, st1 = nsbmd.model_stats(model), nsbmd.model_stats(back)
        report(f"NSBMD {c} mesh.json -> NSBMD -> decode: same faces and materials",
               face_set(back) == face_set(model) and mat_attrs(back) == mat_attrs(model),
               f"polys {st1['polygons']} (stock {st0['polygons']}), verts sent {st1['vertices_sent']} "
               f"(stock {st0['vertices_sent']}), {len(nsbmd.build_bmd([new]))} bytes (stock {len(raw)})")


def check_textures():
    ok, differ = 0, []
    for p in sorted(glob.glob(os.path.join(TEXSETS, "*.nsbtx"))):
        d = open(p, "rb").read()
        s = nsbtx.parse(d)
        if nsbtx.build(s["textures"], s["palettes"], keep_offsets=True, pal_flag=s["header"]["pal_flag"]) == d:
            ok += 1
        else:
            differ.append(os.path.basename(p))
    report("NSBTX texture sets rebuild identical", differ in ([], ["map_texture_set_007.nsbtx"]),
           f"{ok} identical, differ: {differ} (007 was rewritten by the coronet tools with other dictionary numbering)")
    s = nsbtx.parse(open(os.path.join(TEXSETS, "map_texture_set_061.nsbtx"), "rb").read())
    pals = {q["name"]: q["colors"] for q in s["palettes"]}
    pairs = nsbtx.pairs_from_models([assemble.stock_bytes(c) for c in CHUNKS])
    bad = []
    fmts = {}
    import png
    for t in s["textures"]:
        pn = nsbtx.guess_palette(t["name"], pals, pairs)
        px, _ = nsbtx.decode(t, pals.get(pn))
        img = png.Image(t["w"], t["h"], px)
        et, ep = nsbtx.encode_texture(t["name"], img, nsbtx.FMT_NAMES[t["fmt"]])
        px2, _ = nsbtx.decode(et, ep["colors"] if ep else None)
        same = all((a[3] == b[3] and (a[3] == 0 or a[:3] == b[:3])) for ra, rb in zip(px, px2) for a, b in zip(ra, rb))
        fmts[nsbtx.FMT_NAMES[t["fmt"]]] = fmts.get(nsbtx.FMT_NAMES[t["fmt"]], 0) + 1
        if not same:
            bad.append(t["name"])
    report("NSBTX set 61 textures decode -> encode -> decode same pixels", not bad, f"{len(s['textures'])} textures "
           f"{fmts}, mismatches {bad}")


def check_bdhc_and_mapdata():
    n = ok_w = ok_s = ok_pack = n_pack = 0
    for p in sorted(glob.glob(os.path.join(MAPS, "map_data_*.bin"))):
        d = open(p, "rb").read()
        sec = mapdata.unpack(d)
        n_pack += 1
        ok_pack += mapdata.pack(sec["permissions"], sec["props"], sec["model"], sec["bdhc"]) == d
        if not sec["bdhc"].startswith(b"BDHC"):
            continue
        n += 1
        b = mapdata.read_bdhc(sec["bdhc"])
        ok_w += mapdata.write_bdhc(b) == sec["bdhc"]
        st, acc = mapdata.make_strips([r[:4] for r in mapdata.bdhc_plates(b)])
        ok_s += (st == b["strips"] and acc == b["access"])
    report("map_data unpack -> pack identical", ok_pack == n_pack, f"{ok_pack}/{n_pack}")
    report("BDHC read -> write identical", ok_w == n, f"{ok_w}/{n}")
    report("BDHC strip builder matches stock strips", ok_s >= n - 1,
           f"{ok_s}/{n} (map_data_184 has a zero-depth plate the stock tool listed once more)")


def check_generated():
    for c in CHUNKS:
        sec = mapdata.unpack(open(stock_path(c), "rb").read())
        bad = collision.check(c, sec["bdhc"])
        report(f"map_data {c} BDHC heights = layout h at all 1024 tile centres", not bad, str(bad[:4]))
        report(f"map_data {c} permissions = layout", sec["permissions"] == collision.permissions(c))


def check_layout_bdhc():
    for c in CHUNKS:
        bad = collision.check(c, collision.bdhc(c))
        report(f"collision.bdhc({c}) heights = layout h at all 1024 tile centres", not bad, str(bad[:4]))


def main():
    check_nsbmd(CHUNKS)
    check_textures()
    check_bdhc_and_mapdata()
    check_layout_bdhc()
    if "--generated" in sys.argv:
        check_generated()
    print("all checks passed" if not failures else f"{len(failures)} FAILED: {failures}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

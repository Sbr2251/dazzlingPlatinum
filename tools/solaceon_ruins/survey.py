#!/usr/bin/env python3
"""Survey of the stock Solaceon Ruins (standard library only; stock inputs read from git at ruins.BASE_REV).

Usage:
  python3 tools/solaceon_ruins/survey.py                     report: headers, chunks and who shares them, warp graph,
                                                             per-room tile maps with warps/objects/signs
  python3 tools/solaceon_ruins/survey.py --preview DIR       also dump every Ruins chunk + its props to mesh.json and
                                                             set 55 + prop textures to DIR/textures
  python3 tools/solaceon_ruins/survey.py --preview DIR --render
                                                             and render top + in-game (CAMERA_TYPE_CAVE) views per room
                                                             with Blender (DIR/<room>_top.png, DIR/<room>_game.png)

Tile map legend: '#' blocked, '.' floor (0x08), 'W' warp tile (0x5e east / 0x5f west / 0x6c / 0x6f exit),
'o' object event, 's' sign/bg event; '>' '<' 'v' mark the warp's walking direction.
"""
import json
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ruins as R  # noqa: E402

sys.path.insert(0, os.path.join(R.ROOT, "tools", "world_art"))
sys.path.insert(0, os.path.join(R.ROOT, "tools", "coronet_lava"))
import chunkedit as C  # noqa: E402
import mapdata  # noqa: E402
import narc  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402
import png  # noqa: E402

BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
AREA_BUILD = "res/prebuilt/fielddata/areadata/area_build_model/area_build.narc"
BUILD_MODEL = "res/prebuilt/fielddata/build_model/build_model.narc"
WARP_DIR = {0x5E: ">", 0x5F: "<", 0x6C: ">", 0x6F: "v", 0x6E: "^"}


def events(suffix, rev=R.BASE_REV):
    return json.loads(C.git_file(rev, R.events_rel(suffix)))


def short(dest):
    s = dest.replace("MAP_HEADER_SOLACEON_RUINS_", "")
    return R.ROOMS[s][0] if s in R.ROOMS else dest.replace("MAP_HEADER_", "")


def chunk(n, rev=R.BASE_REV):
    return mapdata.unpack(C.git_file(rev, R.chunk_rel(n)))


def room_map(suffix, rev=R.BASE_REV):
    name, mtx, ch = R.ROOMS[suffix]
    sec = chunk(ch, rev)
    perm = mapdata.read_permissions(sec["permissions"])
    ev = events(suffix, rev)
    marks = {}
    for w in ev["warp_events"]:
        marks[(w["x"], w["z"])] = "W"
    for o in ev["object_events"]:
        marks[(o["x"], o["z"])] = "o"
    for b in ev["bg_events"]:
        marks[(b["x"], b["z"])] = "s"
    xs = [x for x in range(32) for z in range(32) if not perm[z][x] & 0x8000]
    zs = [z for x in range(32) for z in range(32) if not perm[z][x] & 0x8000]
    x0, x1, z0, z1 = max(0, min(xs) - 2), min(31, max(xs) + 2), max(0, min(zs) - 2), min(31, max(zs) + 2)
    lines = ["      " + "".join(f"{x:3d}" for x in range(x0, x1 + 1))]
    for z in range(z0, z1 + 1):
        row = []
        for x in range(x0, x1 + 1):
            v = perm[z][x]
            c = "#" if v & 0x8000 else "."
            if v & 0xFF in WARP_DIR and not v & 0x8000:
                c = "W" + WARP_DIR[v & 0xFF]
            if (x, z) in marks and marks[(x, z)] != "W":
                c = (c if c != "." else "") + marks[(x, z)]
            row.append(c.rjust(3))
        lines.append(f"  {z:3d} " + "".join(row))
    return lines, (x0, z0, x1, z1)


def report():
    out = []
    out.append(f"Solaceon Ruins at {R.BASE_REV}: area {R.AREA}, texture set {R.TEXSET}")
    out.append("")
    out.append("| room | header suffix | matrix | chunk | chunk shared with | walkable tiles | polys | model B |")
    out.append("|---|---|---|---|---|---|---|---|")
    for suf, (name, mtx, ch) in R.ROOMS.items():
        sec = chunk(ch)
        perm = mapdata.read_permissions(sec["permissions"])
        walk = sum(1 for z in range(32) for x in range(32) if not perm[z][x] & 0x8000)
        st = nsbmd.model_stats(nsbmd.parse_bmd(sec["model"])["models"][0])
        others = [r for r in R.rooms_of_chunk(ch) if r != name]
        out.append(f"| {name} | {suf} | {mtx} | {ch} | {', '.join(others) or '-'} | {walk} | {st['polygons']} | "
                   f"{len(sec['model'])} |")
    out.append("")
    out.append("Warp graph (edges: room (x,z) -> room):")
    seen = set()
    for suf, (name, mtx, ch) in R.ROOMS.items():
        for w in events(suf)["warp_events"]:
            d = short(w["dest_header_id"])
            key = tuple(sorted((name, d)))
            tag = "" if key not in seen else " (back)"
            seen.add(key)
            out.append(f"  {name:6s} ({w['x']},{w['z']}) -> {d}{tag}")
    out.append("")
    for suf, (name, mtx, ch) in R.ROOMS.items():
        ev = events(suf)
        out.append(f"{name} ({suf}, chunk {ch}):")
        lines, _ = room_map(suf)
        out += lines
        for o in ev["object_events"]:
            out.append(f"    obj {o['id']} {o['graphics_id']} ({o['x']},{o['z']}) script {o['script']} "
                       f"flag {o['hidden_flag']}")
        for b in ev["bg_events"]:
            out.append(f"    bg ({b['x']},{b['z']}) script {b['script']} {b['player_facing_dir']}")
        out.append("")
    return "\n".join(out)


def dump(out_dir, rev=R.BASE_REV):
    tex_dir = os.path.join(out_dir, "textures")
    os.makedirs(tex_dir, exist_ok=True)
    ab = narc.read_files(os.path.join(R.ROOT, AREA_BUILD))[2]
    bm = narc.read_files(os.path.join(R.ROOT, BUILD_MODEL))[2]
    # set 55, palettes paired by the map models' bindings
    pairs = {}
    for ch in sorted({v[2] for v in R.ROOMS.values()}):
        m = nsbmd.parse_bmd(chunk(ch, rev)["model"])["models"][0]
        for mt in m["materials"]:
            if mt["texture"]:
                pairs[mt["texture"]] = mt["palette"]
    s = nsbtx.parse(C.git_file(rev, R.texset_rel()))
    pals = {p["name"]: p["colors"] for p in s["palettes"]}
    for t in s["textures"]:
        pn = pairs.get(t["name"]) or nsbtx.guess_palette(t["name"], pals, pairs)
        px, _ = nsbtx.decode(t, pals.get(pn))
        png.write_rgba(os.path.join(tex_dir, t["name"] + ".png"), t["w"], t["h"], px)
        json.dump({"format": nsbtx.FMT_NAMES[t["fmt"]], "palette": pn, "c0": t["c0"], "size": [t["w"], t["h"]]},
                  open(os.path.join(tex_dir, t["name"] + ".json"), "w"))
    done = set()
    for ch in sorted({v[2] for v in R.ROOMS.values()}):
        sec = chunk(ch, rev)
        model = nsbmd.parse_bmd(sec["model"])["models"][0]
        json.dump(nsbmd.model_to_mesh(model, (0, 0), name=f"chunk_{ch}"),
                  open(os.path.join(out_dir, f"chunk_{ch}.mesh.json"), "w"))
        props = {"name": f"chunk_{ch}_props", "origin_tile": [0, 0], "materials": [], "meshes": []}
        for p in mapdata.read_props(sec["props"]):
            b = nsbmd.parse_bmd(bm[p["model"]])
            pm = b["models"][0]
            sub = nsbmd.model_to_mesh(pm, (0, 0), offset=[v / 4096 for v in p["pos"]])
            props["materials"] += sub["materials"]
            props["meshes"] += sub["meshes"]
            if b["tex0"] and p["model"] not in done:
                done.add(p["model"])
                ps = nsbtx.parse(b["tex0"])
                ppals = {q["name"]: q["colors"] for q in ps["palettes"]}
                mp = {mt["texture"]: mt["palette"] for mt in pm["materials"]}
                for t in ps["textures"]:
                    px, _ = nsbtx.decode(t, ppals.get(mp.get(t["name"])) or list(ppals.values())[0])
                    png.write_rgba(os.path.join(tex_dir, t["name"] + ".png"), t["w"], t["h"], px)
        json.dump(props, open(os.path.join(out_dir, f"chunk_{ch}_props.mesh.json"), "w"))
    props_id = struct.unpack_from("<H", narc.read_files(os.path.join(R.ROOT, "res/prebuilt/fielddata/areadata/area_data.narc"))[2][R.AREA])[0]
    n = struct.unpack_from("<H", ab[props_id])[0]
    print(f"area {R.AREA}: props list {props_id} = build models {list(struct.unpack_from('<%dH' % n, ab[props_id], 2))}")
    print(f"dumped {len(s['textures'])} set-{R.TEXSET} textures and {len(done)} prop models to {out_dir}")


def render(out_dir, mesh_dir=None, rooms=None, tag="", extra_tex=(), px=24, extra_files=None, dest=None,
           target=None, views="top,game"):
    """Top + cave-camera views per room. out_dir holds the stock dump (textures, props); mesh_dir holds the
    chunk_NNN.mesh.json to show (default out_dir); renders go to dest (default out_dir)."""
    mesh_dir = mesh_dir or out_dir
    dest = dest or out_dir
    tex = [os.path.join(out_dir, "textures")] + list(extra_tex)
    for suf, (name, mtx, ch) in R.ROOMS.items():
        if rooms and name not in rooms:
            continue
        _, (x0, z0, x1, z1) = room_map(suf)
        files = [os.path.join(mesh_dir, f"chunk_{ch}.mesh.json"), os.path.join(out_dir, f"chunk_{ch}_props.mesh.json")]
        files += (extra_files or {}).get(name, [])
        tx, tz = (target or {}).get(name, ((x0 + x1) / 2, (z0 + z1) / 2))
        cmd = [BLENDER, "-b", "--factory-startup", "-P", os.path.join(HERE, "blender_cpu.py"),
               "--"]
        for t in tex:
            cmd += ["--tex", t]
        cmd += ["--out", os.path.join(dest, f"{name}{tag}"), "--views", views, "--camera", "cave",
                "--region", f"{x0},{z0 - 1},{x1 + 1},{z1 + 1}", "--px", str(px), "--target", f"{tx},{tz}"] + files
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(name, "rendered" if r.returncode == 0 else "FAILED\n" + r.stdout[-2000:] + r.stderr[-2000:])


def contact_sheet(paths, out, cols=4, shrink=4, label_rows=0):
    """Paste PNGs (same size) into one sheet, shrunk by `shrink` (nearest)."""
    imgs = [png.read(p) for p in paths]
    w, h = imgs[0].width // shrink, imgs[0].height // shrink
    rows = (len(imgs) + cols - 1) // cols
    W, H = cols * (w + 4), rows * (h + 4)
    px = [[(20, 20, 24, 255)] * W for _ in range(H)]
    for i, im in enumerate(imgs):
        ox, oy = (i % cols) * (w + 4), (i // cols) * (h + 4)
        for y in range(min(h, im.height // shrink)):
            src = im.pixels[y * shrink]
            row = px[oy + y]
            for x in range(min(w, im.width // shrink)):
                row[ox + x] = src[x * shrink]
    png.write_rgba(out, W, H, px)


def main():
    print(report())
    if "--preview" in sys.argv:
        d = sys.argv[sys.argv.index("--preview") + 1]
        dump(d)
        if "--render" in sys.argv:
            render(d)
            names = [v[0] for v in R.ROOMS.values()]
            contact_sheet([os.path.join(d, f"{n}_game.png") for n in names], os.path.join(d, "stock_game_sheet.png"),
                          cols=5)
            print("sheet", os.path.join(d, "stock_game_sheet.png"), "order:", names)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Renders the Solaceon graybox (or stock) previews with Blender: a top view of the whole town and the real field
camera (CAMERA_TYPE_DEFAULT) at named spots. Standard library only (it runs Blender as a subprocess).

Usage:
  python3 tools/solaceon_town/dump_stock.py OUT/stock                     (once: stock meshes + set-010 textures)
  python3 tools/solaceon_town/build_graybox.py --preview OUT/gb
  python3 tools/solaceon_town/render.py OUT [--stock | --art] [--views top,plaza,...] [--cycles]
  (--art: the art pass, after build_art.py --preview OUT; meshes from OUT/art, kit + prop textures OUT/art/textures)

OUT defaults to ~/Documents/Solaceon Update/layout. Writes OUT/graybox_top.png and OUT/graybox_<view>_game.png (or stock_* with
--stock, art_* with --art). Neighbour chunks (068, 074 and the filler) always come from OUT/stock. --cycles renders on the CPU
(SOL_PREVIEW_ENGINE=cycles; use it when EEVEE's Metal shaders fail to compile in a sandbox).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
# name -> (blender_preview view args)
VIEWS = {
    "top": ["--views", "top", "--region", "540,632,612,680", "--px", "12"],
    "north": ["--views", "game", "--target", "564,646", "--target_h", "1"],       # pilgrim road + tent
    "plaza": ["--views", "game", "--target", "561,655", "--target_h", "1"],       # memorial plaza + garden
    "compound": ["--views", "game", "--target", "580,657", "--target_h", "1"],    # Sanctuary gate + hall
    "dig": ["--views", "game", "--target", "593,660", "--target_h", "1"],         # excavation
    "kennel": ["--views", "game", "--target", "553,666", "--target_h", "1"],      # kennel + loading yard
    "south": ["--views", "game", "--target", "574,665", "--target_h", "1"],       # Mart, East House
    # art-pass views (town-art): the zones the in-game screenshots visit
    "tent": ["--views", "game", "--target", "566,646", "--target_h", "1"],        # registration tent, banner posts
    "wall": ["--views", "game", "--target", "558,654", "--target_h", "1"],        # plaza at the memorial wall
    "garden": ["--views", "game", "--target", "563,651", "--target_h", "1"],      # garden of names, bench
    "gate": ["--views", "game", "--target", "580,660", "--target_h", "1"],        # compound gate from the street
    "forecourt": ["--views", "game", "--target", "580,655", "--target_h", "1"],   # emblem, lanterns
    "door": ["--views", "game", "--target", "580,653", "--target_h", "1"],        # in front of the hall door
    "gap": ["--views", "game", "--target", "595,661", "--target_h", "1"],         # excavation gap
    "yard": ["--views", "game", "--target", "552,667", "--target_h", "1"],        # kennel, loading yard, ruts
    "southexit": ["--views", "game", "--target", "560,669", "--target_h", "1"],   # road to Route 209
    "northroad": ["--views", "game", "--target", "560,643", "--target_h", "1"],   # road from Route 210
}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = args[0] if args else os.path.expanduser("~/Documents/Solaceon Update/layout")
    stock = os.path.join(out, "stock")
    views = VIEWS.keys()
    if "--views" in sys.argv:
        views = sys.argv[sys.argv.index("--views") + 1].split(",")
        args = [a for a in args if a != sys.argv[sys.argv.index("--views") + 1]]
    town = (["chunk_072_17_20.mesh.json", "chunk_073_18_20.mesh.json", "chunk_072_props.mesh.json",
             "chunk_073_props.mesh.json"] if "--stock" in sys.argv else None)
    src = "art" if "--art" in sys.argv else "gb"
    files = [os.path.join(stock, f) for f in town] if town else \
        [os.path.join(out, src, f) for f in ("chunk_072.mesh.json", "chunk_073.mesh.json", "props_072.mesh.json",
                                              "props_073.mesh.json")]
    files += [os.path.join(stock, f) for f in sorted(os.listdir(stock))
              if f.endswith(".mesh.json") and not f.startswith(("chunk_072", "chunk_073"))]
    env = dict(os.environ)
    if "--cycles" in sys.argv:
        env["SOL_PREVIEW_ENGINE"] = "cycles"
    prefix = "stock" if "--stock" in sys.argv else "art" if src == "art" else "graybox"
    for v in views:
        cmd = [BLENDER, "-b", "--factory-startup", "-P", os.path.join(HERE, "preview.py"), "--",
               "--tex", os.path.join(out, src, "textures"), "--tex", os.path.join(stock, "textures"),
               "--out", os.path.join(out, prefix if v == "top" else f"{prefix}_{v}"), "--lit"] + \
            VIEWS[v] + files
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        wrote = [ln for ln in r.stdout.splitlines() if ln.startswith("wrote")]
        print(v, wrote[-1] if wrote else ("FAILED\n" + r.stdout[-2000:] + r.stderr[-2000:]))


if __name__ == "__main__":
    main()

"""Headless Blender render of the Giratina title loop at 2x DS resolution.

Usage (never saves the .blend):
  Blender -b giratina_title_v2_snapshot.blend --python render_frames.py -- \
      --out /tmp/gir_prerender/raw --frames 1-360:2 [--scale 2] [--samples 32]

Frame spec: comma-separated items, each N or A-B or A-B:STEP (inclusive).
Output files are <out>/f####.png (sRGB display-transformed, AgX look kept).
"""
import argparse
import os
import sys
import time

import bpy

SCENE_NAME = "Giratina_Shadow_Loop_002"


def parse_frames(spec):
    frames = []
    for item in spec.split(","):
        step = 1
        if ":" in item:
            item, step = item.split(":")
            step = int(step)
        if "-" in item:
            a, b = item.split("-")
            frames.extend(range(int(a), int(b) + 1, step))
        else:
            frames.append(int(item))
    return sorted(set(frames))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", default="1-360")
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--skip-existing", action="store_true")
    # EEVEE needs a Metal shader compile that fails inside some sandboxed
    # shells; Cycles CPU is the fallback and matches the lighting closely.
    ap.add_argument("--engine", choices=("EEVEE", "CYCLES"), default="EEVEE")
    args = ap.parse_args(argv)

    scene = bpy.data.scenes[SCENE_NAME]
    bpy.context.window.scene = scene if bpy.context.window else None
    scene.render.resolution_x = 256 * args.scale
    scene.render.resolution_y = 192 * args.scale
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    if args.engine == "CYCLES":
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = args.samples
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
        # EEVEE (no raytracing) has no object-to-object bounce light; keep
        # Cycles direct-lit so the shadowed reveal stays as dark as authored.
        scene.cycles.max_bounces = 8
        scene.cycles.diffuse_bounces = 0
        scene.cycles.glossy_bounces = 1
        scene.cycles.transmission_bounces = 2
        scene.cycles.transparent_max_bounces = 8
    else:
        scene.eevee.taa_render_samples = args.samples

    os.makedirs(args.out, exist_ok=True)
    for frame in parse_frames(args.frames):
        path = os.path.join(args.out, "f%04d.png" % frame)
        if args.skip_existing and os.path.exists(path):
            continue
        t = time.time()
        scene.frame_set(frame)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True, scene=scene.name)
        print("RENDERED", frame, "%.1fs" % (time.time() - t), flush=True)


main()

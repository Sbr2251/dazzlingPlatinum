"""Runs tools/lake_verity/blender_preview.py with Cycles on the CPU instead of EEVEE.

Same arguments as blender_preview.py. Use it where EEVEE cannot compile its Metal shaders (sandboxed sessions:
"could not build module 'monolithic_metal'", every render comes out as the background colour). The materials are
emission-only, so Cycles at a few samples with a tiny pixel filter gives the same flat, nearest-filtered image.

  Blender -b --factory-startup -P tools/solaceon_town/interior/preview_cycles.py -- <blender_preview.py args>
"""
import os

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "lake_verity", "blender_preview.py")

_orig_render = bpy.ops.render.render


def _setup():
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.cycles.samples = 16
    s.cycles.use_denoising = False
    s.cycles.pixel_filter_type = "BOX"
    s.cycles.filter_width = 0.01
    s.cycles.max_bounces = 0
    s.cycles.transparent_max_bounces = 8
    s.render.film_transparent = False


code = open(SRC).read()
code = code.replace('scene.render.engine = "BLENDER_EEVEE"', 'scene.render.engine = "CYCLES"')
code = code.replace("    bpy.ops.render.render(write_still=True)", "    _setup()\n    bpy.ops.render.render(write_still=True)")
exec(compile(code, SRC, "exec"), {"__name__": "__main__", "_setup": _setup, "__file__": SRC})

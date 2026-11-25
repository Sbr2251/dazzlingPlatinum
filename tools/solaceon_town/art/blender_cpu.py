"""Runs tools/lake_verity/blender_preview.py with Cycles on the CPU instead of EEVEE.

Sandboxed sessions cannot build Metal shaders, so EEVEE crashes there. Same arguments as blender_preview.py:
  Blender -b --factory-startup -P tools/solaceon_town/art/blender_cpu.py -- <blender_preview.py arguments>
Emission-only materials (the default, unlit preview) need few samples; a box filter keeps texels crisp.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "lake_verity", "blender_preview.py")

code = open(SRC).read()
patch = ('scene.render.engine = "CYCLES"\n'
         'scene.cycles.device = "CPU"\n'
         'scene.cycles.samples = 24 if "--lit" in sys.argv else 6\n'
         'scene.cycles.use_denoising = False\n'
         'scene.cycles.pixel_filter_type = "BOX"\n'
         'scene.cycles.filter_width = 0.5\n'
         'scene.cycles.max_bounces = 1\n')
assert 'scene.render.engine = "BLENDER_EEVEE"\n' in code
code = code.replace('scene.render.engine = "BLENDER_EEVEE"\n', patch)
exec(compile(code, SRC, "exec"), {"__name__": "__main__", "__file__": SRC})

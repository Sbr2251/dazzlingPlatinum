"""Blender preview for Solaceon: tools/lake_verity/blender_preview.py plus the overworld field camera.

Run with Blender 5, exactly like blender_preview.py (same arguments); --camera default (the default here) is
CAMERA_TYPE_DEFAULT, the camera of the Solaceon Town map header (field_camera.c: distance 666.922 world units,
pitch 59.052 deg, vertical half-fov 8.091 deg). --camera zoomed is the Lake Verity camera.

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P tools/solaceon_town/preview.py -- \
      --tex <dir> --out <prefix> --views top,game --region 540,632,612,680 --target 560,655 --target_h 1 \
      [--lit] mesh.json ...

blender_preview.py is not modified: its source is read and the extra camera is added to its camera table.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "lake_verity", "blender_preview.py")
src = open(SRC).read()
key = '"zoomed": (515.4560546875, 54.656982421875, 10.458984375, False),'
assert key in src, "blender_preview.py camera table changed"
src = src.replace(key, key + '\n                "default": (666.922119140625, 59.051513671875, 8.0914306640625, False),')
src = src.replace('"camera": "zoomed"', '"camera": "default"')
# EEVEE needs the Metal shader compiler, which fails in some sandboxed sessions ("could not build module
# 'monolithic_metal'"); SOL_PREVIEW_ENGINE=cycles renders on the CPU instead (slower, same framing).
if os.environ.get("SOL_PREVIEW_ENGINE", "").lower() == "cycles":
    src = src.replace('scene.render.engine = "BLENDER_EEVEE"',
                      'scene.render.engine = "CYCLES"\nscene.cycles.device = "CPU"\nscene.cycles.samples = 16\n'
                      'scene.cycles.use_denoising = False\nscene.render.film_transparent = False')
exec(compile(src, SRC, "exec"), {"__name__": "__main__", "__file__": SRC})

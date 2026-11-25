"""Runs tools/lake_verity/blender_preview.py with Cycles on the CPU instead of EEVEE (same arguments).

EEVEE needs Metal shaders, and this session cannot write the Metal shader cache, so EEVEE renders come out blank.
Cycles needs no GPU shaders. Back-face culling (an EEVEE material setting) is emulated with the Backfacing output:
culled materials draw back faces transparent, as on the DS.

  Blender -b --factory-startup -P tools/solaceon_ruins/blender_cpu.py -- <blender_preview.py arguments>
"""
import os

import bpy

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lake_verity", "blender_preview.py")
src = open(SRC).read()
src = src.replace('scene.render.engine = "BLENDER_EEVEE"',
                  'scene.render.engine = "CYCLES"\n'
                  'scene.cycles.device = "CPU"\n'
                  'scene.cycles.samples = 16\n'
                  'scene.cycles.use_denoising = False\n'
                  'scene.render.filter_size = 0.01\n')
hook = '''
    if cull == "back":
        _out = [n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"][0]
        _src = _out.inputs["Surface"].links[0].from_socket
        _geo = nt.nodes.new("ShaderNodeNewGeometry")
        _tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        _mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(_geo.outputs["Backfacing"], _mx.inputs[0])
        nt.links.new(_src, _mx.inputs[1])
        nt.links.new(_tr.outputs[0], _mx.inputs[2])
        nt.links.new(_mx.outputs[0], _out.inputs["Surface"])
'''
anchor = '    mat.use_backface_culling = cull == "back"\n'
assert anchor in src
src = src.replace(anchor, anchor + hook)
exec(compile(src, SRC, "exec"), {"__name__": "__main__", "bpy": bpy})

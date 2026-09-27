"""Blender preview of mesh.json files (PLAN.md format), textured, with a top-down and an in-game camera.

Run with Blender (5.x), not plain Python:
  Blender -b --factory-startup -P tools/lake_verity/blender_preview.py -- \
      --tex <texture dir> [--tex <dir> ...] --out <prefix> [--views top,game] [--region x0,z0,x1,z1]
      [--target x,z] [--px 8] [--lit] [--dscolor] [--bg r,g,b] mesh.json [mesh.json ...]

Axes: mesh x (east) -> Blender X, z (south) -> -Y, h (up) -> Z; 1 Blender unit = 1 tile.
--views top   orthographic, straight down, covering --region (tiles, default 4,10,64,60) at --px pixels per tile
--views game  the CAMERA_TYPE_ZOOMED_IN field camera (field_camera.c: distance 515.456 world units = 32.216 tiles,
              pitch 54.657 deg, vertical fov 2 * 10.459 deg, 256x192 scaled up) looking at --target (tiles)
              [--target_h h]; --camera interior uses CAMERA_TYPE_INTERIOR_ORTHOGRAPHIC instead (orthographic,
              pitch 50.087 deg, view 256.5 x 192.4 world units = 16.03 x 12.03 tiles), --camera cave CAMERA_TYPE_CAVE
Materials are unlit (texture x vertex colour) unless --lit, which adds a sun roughly where the DS light 0 is.
By default the vertex colour multiplies in linear space (brighter than the DS for dark colours); --dscolor makes the
shown colour texture x vertex colour in display space, as the DS modulates.
Textures come from <texture dir>/<texture>.png (nearest filtering); v is flipped (mesh.json v is image space).
"""
import json
import math
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opts = {"tex": [], "out": "/tmp/lv_preview", "views": "top,game", "region": "4,10,64,60", "target": "32,36",
        "px": "8", "lit": False, "dscolor": False, "files": [], "camera": "zoomed", "bg": "0.05,0.05,0.08"}
i = 0
while i < len(argv):
    a = argv[i]
    if a == "--tex":
        opts["tex"].append(argv[i + 1])
        i += 2
    elif a == "--lit":
        opts["lit"] = True
        i += 1
    elif a == "--dscolor":
        opts["dscolor"] = True
        i += 1
    elif a.startswith("--"):
        opts[a[2:]] = argv[i + 1]
        i += 2
    else:
        opts["files"].append(a)
        i += 1

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.world = bpy.data.worlds.new("w")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = tuple(float(v) for v in opts["bg"].split(",")) + (1,)
bg.inputs[1].default_value = 1.0
scene.view_settings.view_transform = "Standard"

images = {}


def find_tex(name):
    for d in opts["tex"]:
        p = os.path.join(d, name + ".png")
        if os.path.exists(p):
            return p, (json.load(open(os.path.join(d, name + ".json"))) if os.path.exists(os.path.join(d, name + ".json")) else {})
    return None, {}


mats = {}


def make_material(m):
    key = m["name"]
    if key in mats:
        return mats[key]
    mat = bpy.data.materials.new(key)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    path, meta = find_tex(m.get("texture") or "")
    alpha_socket = None
    if path:
        img = images.get(path) or bpy.data.images.load(path)
        images[path] = img
        tx = nt.nodes.new("ShaderNodeTexImage")
        tx.image = img
        tx.interpolation = "Closest"
        rep = m.get("tex_param", {}).get("repeat_s", True)
        tx.extension = "REPEAT" if rep else "EXTEND"
        nt.links.new(tx.outputs["Color"], mix.inputs[6])
        alpha_socket = tx.outputs["Alpha"]
    else:
        mix.inputs[6].default_value = (1, 0, 1, 1)
    nt.links.new(vc.outputs["Color"], mix.inputs[7])
    if opts["lit"]:
        sh = nt.nodes.new("ShaderNodeBsdfDiffuse")
        nt.links.new(mix.outputs[2], sh.inputs["Color"])
    else:
        sh = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(mix.outputs[2], sh.inputs["Color"])
    alpha = m.get("alpha", 31) / 31.0
    if alpha_socket is not None or alpha < 1:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        if alpha_socket is not None and alpha < 1:
            mul = nt.nodes.new("ShaderNodeMath")
            mul.operation = "MULTIPLY"
            mul.inputs[1].default_value = alpha
            nt.links.new(alpha_socket, mul.inputs[0])
            nt.links.new(mul.outputs[0], mx.inputs[0])
        elif alpha_socket is not None:
            nt.links.new(alpha_socket, mx.inputs[0])
        else:
            mx.inputs[0].default_value = alpha
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(sh.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs["Surface"])
        mat.surface_render_method = "BLENDED" if (alpha < 1 or meta.get("format") in ("a3i5", "a5i3")) else "DITHERED"
    else:
        nt.links.new(sh.outputs[0], out.inputs["Surface"])
    cull = m.get("polygon_attr", {}).get("cull", "back")
    mat.use_backface_culling = cull == "back"
    mats[key] = mat
    return mat


def load_mesh_json(path):
    d = json.load(open(path))
    mdefs = {m["name"]: m for m in d["materials"]}
    for k, me in enumerate(d["meshes"]):
        verts = [(p[0], -p[2], p[1]) for p in me["positions"]]
        faces = [tuple(f) for f in me.get("tris", [])] + [tuple(f) for f in me.get("quads", [])]
        mesh = bpy.data.meshes.new(f"{d['name']}_{k}")
        mesh.from_pydata(verts, [], faces)
        # (x, h, z) -> (x, -z, h) is a proper rotation, so the winding-derived normal already agrees with the
        # display-list NORMALs (checked on all stock faces); no flip needed
        uvl = mesh.uv_layers.new(name="UV")
        col = mesh.color_attributes.new(name="Col", type="BYTE_COLOR", domain="CORNER")
        uvs, cols = me.get("uvs"), me.get("colors")
        for poly in mesh.polygons:
            for li in poly.loop_indices:
                vi = mesh.loops[li].vertex_index
                if uvs:
                    uvl.data[li].uv = (uvs[vi][0], 1.0 - uvs[vi][1])
                c = cols[vi] if cols else (255, 255, 255)
                if opts["dscolor"]:   # DS modulation: shown colour = texture x vertex colour in display space
                    col.data[li].color = tuple((v / 255) ** 2.2 for v in c[:3]) + (1,)
                else:
                    col.data[li].color = (c[0] / 255, c[1] / 255, c[2] / 255, 1)
        mesh.update()
        ob = bpy.data.objects.new(mesh.name, mesh)
        scene.collection.objects.link(ob)
        mdef = mdefs.get(me["material"], {"name": me["material"], "texture": me["material"]})
        ob.data.materials.append(make_material(mdef))


for f in opts["files"]:
    load_mesh_json(f)

if opts["lit"]:
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.0
    so = bpy.data.objects.new("sun", sun)
    so.rotation_euler = (math.radians(35), 0, math.radians(20))
    scene.collection.objects.link(so)
    bg.inputs[1].default_value = 0.6

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

for view in opts["views"].split(","):
    if view == "top":
        x0, z0, x1, z1 = [float(v) for v in opts["region"].split(",")]
        px = int(opts["px"])
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = max(x1 - x0, z1 - z0)
        scene.render.resolution_x = int((x1 - x0) * px)
        scene.render.resolution_y = int((z1 - z0) * px)
        cam_data.sensor_fit = "HORIZONTAL" if (x1 - x0) >= (z1 - z0) else "VERTICAL"
        cam.location = ((x0 + x1) / 2, -(z0 + z1) / 2, 60)
        cam.rotation_euler = (0, 0, 0)
        cam_data.clip_end = 200
    else:
        tx, tz = [float(v) for v in opts["target"].split(",")]
        th = float(opts.get("target_h", 0))
        # field_camera.c sCameraTypes: (distance, pitch deg, fov half-angle deg, orthographic)
        cams = {"zoomed": (515.4560546875, 54.656982421875, 10.458984375, False),
                "cave": (574.577880859375, 63.2647705078125, 9.4976806640625, False),
                "interior": (1563.537841796875, 50.086669921875, 3.5211181640625, True)}
        d_wu, pitch_deg, fov_deg, ortho = cams[opts["camera"]]
        dist = d_wu / 16
        pitch = math.radians(pitch_deg)
        if ortho:
            # camera.c: top = tan(fov) * distance, right = top * 4/3 (NNS_G3dGlbOrtho)
            cam_data.type = "ORTHO"
            cam_data.sensor_fit = "VERTICAL"
            cam_data.ortho_scale = 2 * math.tan(math.radians(fov_deg)) * dist
        else:
            cam_data.type = "PERSP"
            cam_data.sensor_fit = "VERTICAL"
            cam_data.angle_y = math.radians(2 * fov_deg)
        scene.render.resolution_x, scene.render.resolution_y = 256 * 4, 192 * 4
        # camera sits south of and above the target, looking north and down
        cam.location = (tx + 0.5, -(tz + 0.5) - dist * math.cos(pitch), th + dist * math.sin(pitch))
        cam.rotation_euler = (math.radians(90) - pitch, 0, 0)
        cam_data.clip_start = 0.5
        cam_data.clip_end = 400
    scene.render.filepath = f"{opts['out']}_{view}.png"
    bpy.ops.render.render(write_still=True)
    print("wrote", scene.render.filepath)

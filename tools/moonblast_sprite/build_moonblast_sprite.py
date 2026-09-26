"""Render the Moonblast moon sprite in Blender and pack it for the battle anim system.

Run inside Blender (needs bpy + numpy, both bundled with Blender):

    blender -b -P tools/moonblast_sprite/build_moonblast_sprite.py

Everything is procedural, so the output only depends on this script. To preview
the animation in an open Blender session instead, exec() this file with
MOONBLAST_GUI=True in its globals and call build_gui_preview().

Outputs (in res/graphics/battle/moves/):
    moonblast.png        64 x (64 * frames), 4-bit indexed, index 0 transparent
    moonblast_cell.json  one 64x64 OAM cell per frame
    moonblast_anim.json  single play-once sequence (SEQUENCE below)

Frames are also written to tools/moonblast_sprite/out/ for previewing.
"""

import json
import math
import os
import struct
import zlib

import bpy
import mathutils
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT_DIR = os.path.join(REPO, 'res', 'graphics', 'battle', 'moves')
PREVIEW_DIR = os.path.join(REPO, 'tools', 'moonblast_sprite', 'out')

SIZE = 64
NUM_COLORS = 15  # plus index 0 for transparency
ALPHA_CUTOFF = 0.45

# Unique renders: moon radius, rim glow strength, halo radius (0 = hidden),
# pink wash, and moon z-rotation (degrees). Battle OBJ VRAM is only 64KB and
# shared with the HP boxes, so keep this to 8 frames (16KB, same as scary_face)
# and let the animation sequence reuse cells for the pulse.
FRAMES = [
    # radius, rim, halo, pink, rot
    (0.22, 0.2, 0.00, 0.3, 0),   # 0 spark / final orb
    (0.40, 0.3, 0.00, 0.0, 6),   # 1 grow
    (0.58, 0.5, 0.00, 0.0, 12),  # 2 grow
    (0.72, 0.6, 0.86, 0.0, 18),  # 3 halo appears
    (0.76, 0.7, 0.92, 0.0, 24),  # 4 hold (dim)
    (0.76, 0.9, 1.00, 0.1, 30),  # 5 hold (bright)
    (0.82, 1.5, 1.06, 0.5, 40),  # 6 flare
    (0.36, 1.5, 0.50, 0.8, 48),  # 7 collapse
]

# Playback: (frame index, 60fps ticks shown). Grow-in, pulsing hold, flare,
# collapse to an orb; 60 ticks total, matched by moonblast/anim.s.
SEQUENCE = [
    (0, 3), (1, 3), (2, 3), (3, 4),
    (4, 6), (5, 6), (4, 6), (5, 6), (4, 6), (5, 6),
    (6, 4), (7, 4), (0, 3),
]

MOON_BASE = (0.93, 0.91, 1.0, 1.0)
MOON_SHADOW = (0.48, 0.42, 0.66, 1.0)
PINK = (1.0, 0.42, 0.74, 1.0)
HALO_PINK = (1.0, 0.45, 0.78, 1.0)


def reset_scene(factory=True):
    if factory:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    else:
        # Live session: clear the scene but keep add-ons (and the MCP socket) alive.
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.orphans_purge(do_recursive=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.cycles.seed = 1
    scene.render.resolution_x = SIZE
    scene.render.resolution_y = SIZE
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.filter_size = 0.8
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    world = bpy.data.worlds.new('World')
    world.use_nodes = True
    # Faint lavender ambient keeps the shadow side purple instead of black.
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.45, 0.85, 1.0)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.12
    scene.world = world
    return scene


def add_camera(scene):
    cam_data = bpy.data.cameras.new('Camera')
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 2.2
    cam = bpy.data.objects.new('Camera', cam_data)
    cam.location = (0.0, -10.0, 0.0)
    cam.rotation_euler = (math.radians(90), 0.0, 0.0)
    scene.collection.objects.link(cam)
    scene.camera = cam


def add_sun(scene):
    # Strong light from the upper left carves a gibbous/crescent terminator.
    sun_data = bpy.data.lights.new('Sun', 'SUN')
    sun_data.energy = 3.0
    sun_data.angle = math.radians(8)
    sun = bpy.data.objects.new('Sun', sun_data)
    # Light comes from the upper left and slightly behind, so the lower right
    # falls into shadow and the lit side reads as a crescent/gibbous moon.
    travel = mathutils.Vector((1.0, 0.35, -0.8))
    sun.rotation_euler = travel.to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(sun)


def moon_material():
    mat = bpy.data.materials.new('Moon')
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfDiffuse')
    add = nodes.new('ShaderNodeAddShader')
    rim_emit = nodes.new('ShaderNodeEmission')
    rim_emit.name = 'RimEmit'
    rim_emit.inputs['Color'].default_value = PINK
    layer = nodes.new('ShaderNodeLayerWeight')
    layer.inputs['Blend'].default_value = 0.35
    rim_pow = nodes.new('ShaderNodeMath')
    rim_pow.operation = 'POWER'
    rim_pow.inputs[1].default_value = 3.0
    rim_mul = nodes.new('ShaderNodeMath')
    rim_mul.name = 'RimStrength'
    rim_mul.operation = 'MULTIPLY'

    # Craters: large-scale Voronoi pits darkened toward lavender, plus fine noise.
    coord = nodes.new('ShaderNodeTexCoord')
    mapping = nodes.new('ShaderNodeMapping')
    mapping.name = 'CraterMapping'
    voronoi = nodes.new('ShaderNodeTexVoronoi')
    voronoi.inputs['Scale'].default_value = 3.2
    voronoi.feature = 'F1'
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 6.0
    noise.inputs['Detail'].default_value = 4.0
    crater_ramp = nodes.new('ShaderNodeValToRGB')
    crater_ramp.color_ramp.elements[0].position = 0.18
    crater_ramp.color_ramp.elements[0].color = MOON_SHADOW
    crater_ramp.color_ramp.elements[1].position = 0.42
    crater_ramp.color_ramp.elements[1].color = MOON_BASE
    mix = nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Factor'].default_value = 0.35
    pink_wash = nodes.new('ShaderNodeMix')
    pink_wash.name = 'PinkWash'
    pink_wash.data_type = 'RGBA'
    pink_wash.inputs['B'].default_value = PINK
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.35

    links.new(coord.outputs['Object'], mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], voronoi.inputs['Vector'])
    links.new(mapping.outputs['Vector'], noise.inputs['Vector'])
    links.new(voronoi.outputs['Distance'], crater_ramp.inputs['Fac'])
    links.new(crater_ramp.outputs['Color'], mix.inputs['A'])
    links.new(noise.outputs['Color'], mix.inputs['B'])
    links.new(mix.outputs['Result'], pink_wash.inputs['A'])
    links.new(pink_wash.outputs['Result'], bsdf.inputs['Color'])
    links.new(voronoi.outputs['Distance'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    links.new(layer.outputs['Facing'], rim_pow.inputs[0])
    links.new(rim_pow.outputs['Value'], rim_mul.inputs[0])
    links.new(rim_mul.outputs['Value'], rim_emit.inputs['Strength'])
    links.new(bsdf.outputs['BSDF'], add.inputs[0])
    links.new(rim_emit.outputs['Emission'], add.inputs[1])
    links.new(add.outputs['Shader'], out.inputs['Surface'])
    return mat


def halo_material():
    # Radial gradient disc: emission colour, alpha falls off with radius so the
    # alpha cutoff leaves a solid soft-edged aura behind the moon.
    mat = bpy.data.materials.new('Halo')
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    emit = nodes.new('ShaderNodeEmission')
    emit.inputs['Color'].default_value = HALO_PINK
    emit.inputs['Strength'].default_value = 0.9
    transp = nodes.new('ShaderNodeBsdfTransparent')
    mixs = nodes.new('ShaderNodeMixShader')
    coord = nodes.new('ShaderNodeTexCoord')
    grad = nodes.new('ShaderNodeTexGradient')
    grad.gradient_type = 'SPHERICAL'
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.08
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    links.new(coord.outputs['Object'], grad.inputs['Vector'])
    links.new(grad.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], mixs.inputs['Fac'])
    links.new(transp.outputs['BSDF'], mixs.inputs[1])
    links.new(emit.outputs['Emission'], mixs.inputs[2])
    links.new(mixs.outputs['Shader'], out.inputs['Surface'])
    return mat


def build_scene(factory=True):
    scene = reset_scene(factory)
    add_camera(scene)
    add_sun(scene)

    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0, location=(0, 0, 0))
    moon = bpy.context.active_object
    moon.name = 'Moon'
    bpy.ops.object.shade_smooth()
    moon.data.materials.append(moon_material())

    bpy.ops.mesh.primitive_circle_add(vertices=64, radius=1.0, fill_type='NGON', location=(0, 1.5, 0), rotation=(math.radians(90), 0, 0))
    halo = bpy.context.active_object
    halo.name = 'Halo'
    halo.data.materials.append(halo_material())
    return scene, moon, halo


def apply_frame(moon, halo, spec, key_frame=None):
    radius, rim, halo_r, pink, rot = spec
    nodes = moon.data.materials[0].node_tree.nodes
    moon.scale = (radius, radius, radius)
    nodes['RimStrength'].inputs[1].default_value = rim
    nodes['PinkWash'].inputs['Factor'].default_value = pink
    nodes['CraterMapping'].inputs['Rotation'].default_value[2] = math.radians(rot)
    halo.hide_render = halo_r <= 0.0
    halo.hide_viewport = halo_r <= 0.0
    halo.scale = (max(halo_r, 0.01),) * 3

    if key_frame is not None:
        moon.keyframe_insert('scale', frame=key_frame)
        nodes['RimStrength'].inputs[1].keyframe_insert('default_value', frame=key_frame)
        nodes['PinkWash'].inputs['Factor'].keyframe_insert('default_value', frame=key_frame)
        nodes['CraterMapping'].inputs['Rotation'].keyframe_insert('default_value', index=2, frame=key_frame)
        halo.keyframe_insert('hide_render', frame=key_frame)
        halo.keyframe_insert('hide_viewport', frame=key_frame)
        halo.keyframe_insert('scale', frame=key_frame)


def render_frame(scene, moon, halo, spec, index):
    apply_frame(moon, halo, spec)

    os.makedirs(PREVIEW_DIR, exist_ok=True)
    path = os.path.join(PREVIEW_DIR, f'frame_{index:02d}.png')
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

    img = bpy.data.images.load(path, check_existing=False)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(SIZE, SIZE, 4)[::-1]
    bpy.data.images.remove(img)
    return px


def quantize(frames):
    """Shared 15-colour palette over all opaque pixels (deterministic k-means)."""
    stack = np.concatenate([f.reshape(-1, 4) for f in frames])
    opaque = stack[stack[:, 3] >= ALPHA_CUTOFF]
    rgb = np.clip(opaque[:, :3] / np.maximum(opaque[:, 3:4], 1e-6), 0, 1)
    rgb = np.round(rgb * 31) / 31  # work in DS 5-bit colour space

    # Seed centres at luminance percentiles so the ramp from shadow to highlight is covered.
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    order = np.argsort(lum, kind='stable')
    centres = rgb[order[np.linspace(0, len(order) - 1, NUM_COLORS).astype(int)]].copy()
    for _ in range(40):
        d = ((rgb[:, None, :] - centres[None, :, :]) ** 2).sum(-1)
        lab = d.argmin(1)
        for k in range(NUM_COLORS):
            sel = rgb[lab == k]
            if len(sel):
                centres[k] = sel.mean(0)
    centres = np.round(centres * 31) / 31
    centres = centres[np.argsort(centres @ np.array([0.299, 0.587, 0.114]), kind='stable')]

    indexed = []
    for f in frames:
        flat = f.reshape(-1, 4)
        col = np.clip(flat[:, :3] / np.maximum(flat[:, 3:4], 1e-6), 0, 1)
        d = ((col[:, None, :] - centres[None, :, :]) ** 2).sum(-1)
        idx = d.argmin(1) + 1
        idx[flat[:, 3] < ALPHA_CUTOFF] = 0
        indexed.append(idx.reshape(SIZE, SIZE).astype(np.uint8))

    palette = [(0, 0, 0)] + [tuple(int(round(c * 31)) * 255 // 31 for c in rgb_c) for rgb_c in centres]
    return indexed, palette


def write_indexed_png(path, pixels, palette):
    h, w = pixels.shape
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        row = pixels[y]
        for x in range(0, w, 2):
            raw.append((int(row[x]) << 4) | int(row[x + 1]))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)

    plte = b''.join(bytes(c) for c in palette) + b'\x00\x00\x00' * (16 - len(palette))
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 4, 3, 0, 0, 0))
    png += chunk(b'PLTE', plte)
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)


def cell_json(num_frames):
    cells = []
    for i in range(num_frames):
        cells.append({
            'cellAttrs': {'hFlip': False, 'vFlip': False, 'hvFlip': False, 'boundingRect': True, 'boundingSphereRadius': 12},
            'maxX': 32, 'maxY': 32, 'minX': -32, 'minY': -32,
            'oamCount': 1,
            'OAM': [{
                'Attr0': {'YCoordinate': -32, 'Rotation': False, 'SizeDisable': False, 'Mode': 0, 'Mosaic': False, 'Colours': 16, 'Shape': 0},
                'Attr1': {'XCoordinate': -32, 'RotationScaling': 0, 'Size': 3},
                'Attr2': {'CharName': 32 * i, 'Priority': 0, 'Palette': 0},
            }],
        })
    return {
        'labelEnabled': True, 'dontPadKbec': True, 'extended': True, 'vramTransferEnabled': False,
        'cellCount': num_frames, 'mappingType': 1, 'cells': cells,
        'labels': ['CellAnime0'], 'labelCount': 1,
    }


def anim_json(num_frames, sequence):
    n = len(sequence)
    return {
        'labelEnabled': True, 'sequenceCount': 1, 'frameCount': n,
        'sequences': [{
            'frameCount': n, 'loopStartFrame': 0, 'animationElement': 0, 'animationType': 1, 'playbackMode': 1,
            'frameData': [{'frameDelay': d, 'resultId': i} for i, d in sequence],
        }],
        'animationResults': [{'resultType': 0, 'index': i} for i in range(num_frames)],
        'resultCount': num_frames, 'labels': ['CellAnime0'], 'labelCount': 1,
    }


def add_sprite_preview_plane(scene):
    """Plane showing the packed in-game sprite (moonblast.png), stepping through
    SEQUENCE exactly as the NANR plays it. Palette index 0 (black) is transparent."""
    img = bpy.data.images.load(os.path.join(OUT_DIR, 'moonblast.png'), check_existing=True)
    img.reload()

    bpy.ops.mesh.primitive_plane_add(size=2.2, location=(2.4, 0, 0), rotation=(math.radians(90), 0, 0))
    plane = bpy.context.active_object
    plane.name = 'InGameSprite'

    mat = bpy.data.materials.new('InGameSprite')
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    uv = nodes.new('ShaderNodeTexCoord')
    mapping = nodes.new('ShaderNodeMapping')
    mapping.name = 'SheetMapping'
    mapping.inputs['Scale'].default_value = (1.0, 1.0 / len(FRAMES), 1.0)
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = img
    tex.interpolation = 'Closest'
    bw = nodes.new('ShaderNodeRGBToBW')
    opaque = nodes.new('ShaderNodeMath')
    opaque.operation = 'GREATER_THAN'
    opaque.inputs[1].default_value = 0.001
    emit = nodes.new('ShaderNodeEmission')
    transp = nodes.new('ShaderNodeBsdfTransparent')
    mix = nodes.new('ShaderNodeMixShader')
    links.new(uv.outputs['UV'], mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], tex.inputs['Vector'])
    links.new(tex.outputs['Color'], emit.inputs['Color'])
    links.new(tex.outputs['Color'], bw.inputs['Color'])
    links.new(bw.outputs['Val'], opaque.inputs[0])
    links.new(opaque.outputs['Value'], mix.inputs['Fac'])
    links.new(transp.outputs['BSDF'], mix.inputs[1])
    links.new(emit.outputs['Emission'], mix.inputs[2])
    links.new(mix.outputs['Shader'], out.inputs['Surface'])
    plane.data.materials.append(mat)
    return mapping


def action_fcurves(id_block):
    ad = id_block.animation_data
    if ad is None or ad.action is None:
        return []
    if hasattr(ad.action, 'fcurves'):
        return list(ad.action.fcurves)
    # Blender 5 slotted actions
    from bpy_extras.anim_utils import action_get_channelbag_for_slot
    channelbag = action_get_channelbag_for_slot(ad.action, ad.action_slot)
    return list(channelbag.fcurves) if channelbag else []


def build_gui_preview():
    """Build the moon in the open Blender session with SEQUENCE keyed on a 60fps
    timeline (constant interpolation, like the sprite), next to the packed
    in-game sprite. Preview only; the sprite files still come from main()."""
    scene, moon, halo = build_scene(factory=False)
    sheet_mapping = add_sprite_preview_plane(scene)

    # Frame both the 3D moon (x=0) and the in-game sprite (x=2.4).
    scene.camera.location.x = 1.2
    scene.camera.data.ortho_scale = 4.8
    scene.render.resolution_x = SIZE * 2
    scene.render.resolution_y = SIZE
    scene.cycles.preview_samples = 16

    frame = 1
    for index, delay in SEQUENCE:
        apply_frame(moon, halo, FRAMES[index], key_frame=frame)
        loc = sheet_mapping.inputs['Location']
        loc.default_value[1] = (len(FRAMES) - 1 - index) / len(FRAMES)
        loc.keyframe_insert('default_value', index=1, frame=frame)
        frame += delay

    # Sprite frames are discrete, so hold each key instead of tweening.
    for id_block in (moon, halo, moon.data.materials[0].node_tree, sheet_mapping.id_data):
        for fcurve in action_fcurves(id_block):
            for point in fcurve.keyframe_points:
                point.interpolation = 'CONSTANT'

    scene.render.fps = 60
    scene.frame_start = 1
    scene.frame_end = frame - 1
    scene.frame_set(1)

    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                space.region_3d.view_perspective = 'CAMERA'
                space.shading.type = 'RENDERED'
    return scene


def main():
    scene, moon, halo = build_scene()
    frames = [render_frame(scene, moon, halo, spec, i) for i, spec in enumerate(FRAMES)]
    indexed, palette = quantize(frames)

    sheet = np.concatenate(indexed, axis=0)
    write_indexed_png(os.path.join(OUT_DIR, 'moonblast.png'), sheet, palette)
    write_indexed_png(os.path.join(PREVIEW_DIR, 'moonblast_sheet.png'), sheet, palette)

    with open(os.path.join(OUT_DIR, 'moonblast_cell.json'), 'w') as f:
        json.dump(cell_json(len(FRAMES)), f, indent=4)
        f.write('\n')
    with open(os.path.join(OUT_DIR, 'moonblast_anim.json'), 'w') as f:
        json.dump(anim_json(len(FRAMES), SEQUENCE), f, indent=4)
        f.write('\n')
    print(f'moonblast sprite: {len(FRAMES)} frames, {sum(d for _, d in SEQUENCE)} ticks, palette {palette}')


if not globals().get('MOONBLAST_GUI'):
    main()

"""Reads and writes SPL particle archives (.spa). Layouts follow lib/spl/include/spl_resource.h."""
import struct

HEADER = "<IIHHIIIII"
FLAG_BITS = [
    ("emissionType", 4), ("drawType", 2), ("circleAxis", 2), ("hasScaleAnim", 1), ("hasColorAnim", 1),
    ("hasAlphaAnim", 1), ("hasTexAnim", 1), ("hasRotation", 1), ("randomInitAngle", 1), ("selfMaintaining", 1),
    ("followEmitter", 1), ("hasChildResource", 1), ("polygonRotAxis", 2), ("polygonReferencePlane", 1),
    ("randomizeLoopedAnim", 1), ("drawChildrenFirst", 1), ("hideParent", 1), ("useViewSpace", 1),
    ("hasGravityBehavior", 1), ("hasRandomBehavior", 1), ("hasMagnetBehavior", 1), ("hasSpinBehavior", 1),
    ("hasCollisionPlaneBehavior", 1), ("hasConvergenceBehavior", 1), ("hasFixedPolygonID", 1),
    ("childHasFixedPolygonID", 1),
]
# Everything in SPLResourceHeader after the flags, as raw struct fields
RES_HEADER = "<3iiii3hHiiihHhhHHHH4s12shh4s"
RES_HEADER_FIELDS = [
    "posX", "posY", "posZ", "emissionCount", "radius", "length", "axisX", "axisY", "axisZ", "color",
    "initVelPosAmplifier", "initVelAxisAmplifier", "baseScale", "aspectRatio", "startDelay", "minRotation",
    "maxRotation", "initAngle", "reserved", "emitterLifeTime", "particleLifeTime", "randomAttenuation", "misc",
    "polygonX", "polygonY", "userData",
]
OPTIONAL = [("hasScaleAnim", "scaleAnim", 12), ("hasColorAnim", "colorAnim", 12), ("hasAlphaAnim", "alphaAnim", 8),
            ("hasTexAnim", "texAnim", 12), ("hasChildResource", "childResource", 20)]
BEHAVIORS = [("hasGravityBehavior", "gravity", 8), ("hasRandomBehavior", "random", 8), ("hasMagnetBehavior", "magnet", 16),
             ("hasSpinBehavior", "spin", 4), ("hasCollisionPlaneBehavior", "collision", 8),
             ("hasConvergenceBehavior", "convergence", 16)]


def unpack_flags(v):
    out, shift = {}, 0
    for name, bits in FLAG_BITS:
        out[name] = (v >> shift) & ((1 << bits) - 1)
        shift += bits
    return out


def pack_flags(f):
    v, shift = 0, 0
    for name, bits in FLAG_BITS:
        v |= (f.get(name, 0) & ((1 << bits) - 1)) << shift
        shift += bits
    return v


def read(path):
    b = open(path, "rb").read()
    magic, version, res_count, tex_count, _, res_size, tex_size, tex_offset, _ = struct.unpack_from(HEADER, b, 0)
    off = struct.calcsize(HEADER)
    resources = []
    for _ in range(res_count):
        flags = unpack_flags(struct.unpack_from("<I", b, off)[0])
        off += 4
        r = {"flags": flags}
        r.update(zip(RES_HEADER_FIELDS, struct.unpack_from(RES_HEADER, b, off)))
        off += struct.calcsize(RES_HEADER)
        for flag, key, size in OPTIONAL + BEHAVIORS:
            if flags[flag]:
                r[key] = b[off:off + size]
                off += size
        resources.append(r)
    assert off == tex_offset, (path, hex(off), hex(tex_offset))
    textures = []
    for _ in range(tex_count):
        size = struct.unpack_from("<I", b, off + 28)[0]
        textures.append(b[off:off + size])
        off += size
    return {"magic": magic, "version": version, "resources": resources, "textures": textures}


def write(spa):
    body = b""
    for r in spa["resources"]:
        body += struct.pack("<I", pack_flags(r["flags"]))
        body += struct.pack(RES_HEADER, *(r[k] for k in RES_HEADER_FIELDS))
        for flag, key, size in OPTIONAL + BEHAVIORS:
            if r["flags"].get(flag):
                assert len(r[key]) == size, key
                body += r[key]
    tex = b"".join(spa["textures"])
    head_size = struct.calcsize(HEADER)
    header = struct.pack(HEADER, spa["magic"], spa["version"], len(spa["resources"]), len(spa["textures"]), 0,
                         len(body), len(tex), head_size + len(body), 0)
    return header + body + tex

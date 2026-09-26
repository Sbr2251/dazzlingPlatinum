"""Reads and writes battle stage pieces, the members of battle_stage.narc.

Mirrors include/battle/battle_stage_format.h; see docs/living_battle_stage/stage_format.md.
All offsets are from the start of the piece, everything is little endian and 4-byte
aligned.
"""

import struct

MAGIC = 0x47545342  # "BSTG"
VERSION = 1

# BACKGROUND_MAX and TERRAIN_MAX (include/constants/battle/...)
BACKGROUND_MAX = 23
TERRAIN_MAX = 24
NUM_MEMBERS = BACKGROUND_MAX + TERRAIN_MAX

HEADER = struct.Struct("<IHHHHII3i3iiiiii2i")
TEXTURE = struct.Struct("<IIHHBBHII")
MESH = struct.Struct("<IHBBHH")
VERTEX = struct.Struct("<3h2hHH")

# GXTexFmt
TEXFMT_PLTT16 = 3
TEXFMT_PLTT256 = 4

# BattleStagePaletteSource
PALETTE_BG = 0
PALETTE_PLATFORM_OBJ = 1
PALETTE_EMBEDDED = 2

# Renderer limits (src/battle/battle_stage.c)
MAX_TEXTURES = 8  # both pieces together
MAX_MESHES = 64
MAX_ALPHA = 31
VERTEX_COLOR_UNSHADED = 0x7FFF
TEXCOORD_ONE = 16  # texCoord units per texel


class Texture:
    def __init__(self, width, height, fmt, palette_source, data, palette):
        assert width in (8, 16, 32, 64, 128, 256, 512, 1024) and height in (8, 16, 32, 64, 128, 256, 512, 1024)
        assert fmt in (TEXFMT_PLTT16, TEXFMT_PLTT256)
        assert palette_source != PALETTE_PLATFORM_OBJ or fmt == TEXFMT_PLTT16
        assert len(data) == width * height // (2 if fmt == TEXFMT_PLTT16 else 1)
        self.width = width
        self.height = height
        self.format = fmt
        self.palette_source = palette_source
        self.data = bytes(data)
        self.palette = list(palette)  # GXRgb

    def texel(self, s, t):
        """Palette index of texel (s, t), both in range."""
        if self.format == TEXFMT_PLTT256:
            return self.data[t * self.width + s]

        byte = self.data[(t * self.width + s) // 2]
        return byte >> 4 if s & 1 else byte & 0xF


def pack_pltt16(rows):
    """PLTT16 texture data from rows of palette indices; the low nibble is the left
    texel."""
    out = bytearray()

    for row in rows:
        for x in range(0, len(row), 2):
            out.append((row[x] & 0xF) | ((row[x + 1] & 0xF) << 4))

    return bytes(out)


class Mesh:
    def __init__(self, primitive, alpha, texture_index, flags, vertices):
        """vertices: [((x, y, z) fx16, (s, t) texCoord units, colour)]"""
        assert 0 <= alpha <= MAX_ALPHA and 0 <= primitive <= 3 and vertices
        self.primitive = primitive
        self.alpha = alpha
        self.texture_index = texture_index
        self.flags = flags
        self.vertices = vertices


class Header:
    FIELDS = ("cam_pos", "cam_target", "fovy_sin", "fovy_cos", "near", "far", "vertex_scale", "platform_pixel_to_world")

    def __init__(self, cam_pos, cam_target, fovy_sin, fovy_cos, near, far, vertex_scale, platform_pixel_to_world):
        self.cam_pos = tuple(cam_pos)
        self.cam_target = tuple(cam_target)
        self.fovy_sin = fovy_sin
        self.fovy_cos = fovy_cos
        self.near = near
        self.far = far
        self.vertex_scale = vertex_scale
        self.platform_pixel_to_world = tuple(platform_pixel_to_world)


class Piece:
    def __init__(self, header, textures, meshes):
        self.header = header
        self.textures = textures
        self.meshes = meshes


def _align4(blob):
    blob += b"\0" * (-len(blob) % 4)


def write_piece(piece):
    """Bytes of a piece. piece None writes an empty piece (valid header, no meshes),
    which leaves the stage off for that background or terrain."""
    if piece is None:
        return HEADER.pack(MAGIC, VERSION, 0, 0, 0, HEADER.size, HEADER.size, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    for mesh in piece.meshes:
        assert mesh.texture_index < len(piece.textures)

    textures_offset = HEADER.size
    meshes_offset = textures_offset + TEXTURE.size * len(piece.textures)
    blob = bytearray()
    base = meshes_offset + MESH.size * len(piece.meshes)
    texture_entries = []

    for tex in piece.textures:
        data_offset = base + len(blob)
        blob += tex.data
        _align4(blob)
        palette_offset = base + len(blob)
        palette = b"".join(struct.pack("<H", c) for c in tex.palette)
        blob += palette
        _align4(blob)
        texture_entries.append(TEXTURE.pack(data_offset, len(tex.data), tex.width, tex.height, tex.format, tex.palette_source, 0, palette_offset, len(palette)))

    mesh_entries = []

    for mesh in piece.meshes:
        vertex_offset = base + len(blob)

        for pos, tc, color in mesh.vertices:
            blob += VERTEX.pack(pos[0], pos[1], pos[2], tc[0], tc[1], color, 0)

        mesh_entries.append(MESH.pack(vertex_offset, len(mesh.vertices), mesh.primitive, mesh.alpha, mesh.texture_index, mesh.flags))

    h = piece.header
    header = HEADER.pack(
        MAGIC, VERSION, len(piece.textures), len(piece.meshes), 0, textures_offset, meshes_offset,
        *h.cam_pos, *h.cam_target, h.fovy_sin, h.fovy_cos, h.near, h.far, h.vertex_scale, *h.platform_pixel_to_world)

    return header + b"".join(texture_entries) + b"".join(mesh_entries) + bytes(blob)


def read_piece(data):
    """Parses a piece; returns None for an empty one (numMeshes 0)."""
    f = HEADER.unpack_from(data, 0)
    magic, version, num_textures, num_meshes, _pad, textures_offset, meshes_offset = f[:7]
    assert magic == MAGIC and version == VERSION

    if num_meshes == 0:
        return None

    header = Header(f[7:10], f[10:13], f[13], f[14], f[15], f[16], f[17], f[18:20])
    textures = []

    for i in range(num_textures):
        d_off, d_size, w, h, fmt, src, _pad, p_off, p_size = TEXTURE.unpack_from(data, textures_offset + TEXTURE.size * i)
        palette = list(struct.unpack_from(f"<{p_size // 2}H", data, p_off))
        textures.append(Texture(w, h, fmt, src, data[d_off:d_off + d_size], palette))

    meshes = []

    for i in range(num_meshes):
        v_off, n, prim, alpha, tex, flags = MESH.unpack_from(data, meshes_offset + MESH.size * i)
        vertices = []

        for k in range(n):
            x, y, z, s, t, color, _pad = VERTEX.unpack_from(data, v_off + VERTEX.size * k)
            vertices.append(((x, y, z), (s, t), color))

        meshes.append(Mesh(prim, alpha, tex, flags, vertices))

    return Piece(header, textures, meshes)

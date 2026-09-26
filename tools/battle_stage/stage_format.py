"""Reads and writes battle stage pieces, the members of battle_stage.narc.

Mirrors include/battle/battle_stage_format.h; see docs/living_battle_stage/stage_format.md.
All offsets are from the start of the piece, everything is little endian and 4-byte
aligned.
"""

import struct

MAGIC = 0x47545342  # "BSTG"
VERSION = 2

# BACKGROUND_MAX and TERRAIN_MAX (include/constants/battle/...)
BACKGROUND_MAX = 23
TERRAIN_MAX = 24
NUM_MEMBERS = BACKGROUND_MAX + TERRAIN_MAX

HEADER = struct.Struct("<IHHHHII3i3iiiiii2iI")
TEXTURE = struct.Struct("<IIHHBBHII")
MESH = struct.Struct("<IHBBHH2BH")
VERTEX = struct.Struct("<3h2hHI")
ATMOSPHERE = struct.Struct("<BBH32B")
LIGHTING = struct.Struct("<3h5HB3x")
NUM_LIGHTING = 3  # day, twilight, night columns (ov16_0223EC04)

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



# BattleStageMeshFlag
FLAG_FOLLOW_PLATFORM_PLAYER = 1 << 0
FLAG_FOLLOW_PLATFORM_ENEMY = 1 << 1
FLAG_COLOR0_TRANSPARENT = 1 << 2
FLAG_FOLLOW_BG3_SCROLL = 1 << 3
FLAG_REPEAT_S = 1 << 4
FLAG_REPEAT_T = 1 << 5
FLAG_FLIP_S = 1 << 6
FLAG_FLIP_T = 1 << 7
FLAG_LIT = 1 << 8
FLAG_FOG = 1 << 9
FLAG_SCROLL = 1 << 10

FX10_ONE = 512  # GX_FX10: 1.9 fixed point, -512..511


def pack_normal(n):
    """GX_VECFX10 of a float vector (each component clamped to the fx10 range)."""
    out = 0

    for i, c in enumerate(n):
        v = max(-FX10_ONE, min(FX10_ONE - 1, int(round(c * FX10_ONE))))
        out |= (v & 0x3FF) << (10 * i)

    return out


def unpack_normal(packed):
    """(x, y, z) fx10 integers of a GX_VECFX10."""
    out = []

    for i in range(3):
        v = (packed >> (10 * i)) & 0x3FF
        out.append(v - 0x400 if v & 0x200 else v)

    return tuple(out)


class Mesh:
    def __init__(self, primitive, alpha, texture_index, flags, vertices, scroll_amplitude=(0, 0), scroll_period=1):
        """vertices: [((x, y, z) fx16, (s, t) texCoord units, colour, packed normal)]"""
        assert 0 <= alpha <= MAX_ALPHA and 0 <= primitive <= 3 and vertices
        assert scroll_period > 0 and all(0 <= a <= 255 for a in scroll_amplitude)
        self.primitive = primitive
        self.alpha = alpha
        self.texture_index = texture_index
        self.flags = flags
        self.vertices = vertices
        self.scroll_amplitude = tuple(scroll_amplitude)
        self.scroll_period = scroll_period


class Lighting:
    """BattleStageFileLighting: one time-of-day column. Colours are GXRgb."""

    FIELDS = ("light_dir", "light_color", "diffuse", "ambient", "emission", "fog_color", "fog_alpha")

    def __init__(self, light_dir, light_color, diffuse, ambient, emission, fog_color, fog_alpha):
        assert all(-0x1000 < c < 0x1000 for c in light_dir) and 0 <= fog_alpha <= 31
        self.light_dir = tuple(light_dir)  # fx16
        self.light_color = light_color
        self.diffuse = diffuse
        self.ambient = ambient
        self.emission = emission
        self.fog_color = fog_color
        self.fog_alpha = fog_alpha


class Atmosphere:
    """BattleStageFileAtmosphere, only in backdrop pieces."""

    def __init__(self, fog_enabled, fog_shift, fog_offset, fog_table, lighting):
        assert 0 <= fog_shift <= 10 and 0 <= fog_offset <= 0x7FFF
        assert len(fog_table) == 32 and all(0 <= d <= 127 for d in fog_table)
        assert len(lighting) == NUM_LIGHTING
        self.fog_enabled = int(bool(fog_enabled))
        self.fog_shift = fog_shift
        self.fog_offset = fog_offset
        self.fog_table = list(fog_table)
        self.lighting = list(lighting)

    def pack(self):
        out = ATMOSPHERE.pack(self.fog_enabled, self.fog_shift, self.fog_offset, *self.fog_table)

        for li in self.lighting:
            out += LIGHTING.pack(*li.light_dir, li.light_color, li.diffuse, li.ambient, li.emission, li.fog_color, li.fog_alpha)

        return out

    @classmethod
    def unpack(cls, data, offset):
        f = ATMOSPHERE.unpack_from(data, offset)
        lighting = []
        offset += ATMOSPHERE.size

        for _ in range(NUM_LIGHTING):
            g = LIGHTING.unpack_from(data, offset)
            lighting.append(Lighting(g[0:3], *g[3:9]))
            offset += LIGHTING.size

        return cls(f[0], f[1], f[2], f[3:35], lighting)


ATMOSPHERE_SIZE = ATMOSPHERE.size + LIGHTING.size * NUM_LIGHTING  # 96


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
    def __init__(self, header, textures, meshes, atmosphere=None):
        self.header = header
        self.textures = textures
        self.meshes = meshes
        self.atmosphere = atmosphere


def _align4(blob):
    blob += b"\0" * (-len(blob) % 4)


def write_piece(piece):
    """Bytes of a piece. piece None writes an empty piece (valid header, no meshes),
    which leaves the stage off for that background or terrain."""
    if piece is None:
        return HEADER.pack(MAGIC, VERSION, 0, 0, 0, HEADER.size, HEADER.size, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    for mesh in piece.meshes:
        assert mesh.texture_index < len(piece.textures)

    textures_offset = HEADER.size
    meshes_offset = textures_offset + TEXTURE.size * len(piece.textures)
    base = meshes_offset + MESH.size * len(piece.meshes)
    blob = bytearray()
    atmosphere_offset = 0

    if piece.atmosphere is not None:
        atmosphere_offset = base
        blob += piece.atmosphere.pack()
        assert len(blob) == ATMOSPHERE_SIZE

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

        for pos, tc, color, normal in mesh.vertices:
            blob += VERTEX.pack(pos[0], pos[1], pos[2], tc[0], tc[1], color, normal)

        mesh_entries.append(MESH.pack(vertex_offset, len(mesh.vertices), mesh.primitive, mesh.alpha, mesh.texture_index, mesh.flags,
                                      mesh.scroll_amplitude[0], mesh.scroll_amplitude[1], mesh.scroll_period))

    h = piece.header
    header = HEADER.pack(
        MAGIC, VERSION, len(piece.textures), len(piece.meshes), 0, textures_offset, meshes_offset,
        *h.cam_pos, *h.cam_target, h.fovy_sin, h.fovy_cos, h.near, h.far, h.vertex_scale, *h.platform_pixel_to_world,
        atmosphere_offset)

    return header + b"".join(texture_entries) + b"".join(mesh_entries) + bytes(blob)


def read_piece(data):
    """Parses a piece; returns None for an empty one (numMeshes 0)."""
    f = HEADER.unpack_from(data, 0)
    magic, version, num_textures, num_meshes, _pad, textures_offset, meshes_offset = f[:7]
    assert magic == MAGIC and version == VERSION

    if num_meshes == 0:
        return None

    header = Header(f[7:10], f[10:13], f[13], f[14], f[15], f[16], f[17], f[18:20])
    atmosphere = Atmosphere.unpack(data, f[20]) if f[20] else None
    textures = []

    for i in range(num_textures):
        d_off, d_size, w, h, fmt, src, _pad, p_off, p_size = TEXTURE.unpack_from(data, textures_offset + TEXTURE.size * i)
        palette = list(struct.unpack_from(f"<{p_size // 2}H", data, p_off))
        textures.append(Texture(w, h, fmt, src, data[d_off:d_off + d_size], palette))

    meshes = []

    for i in range(num_meshes):
        v_off, n, prim, alpha, tex, flags, amp_s, amp_t, period = MESH.unpack_from(data, meshes_offset + MESH.size * i)
        vertices = []

        for k in range(n):
            x, y, z, s, t, color, normal = VERTEX.unpack_from(data, v_off + VERTEX.size * k)
            vertices.append(((x, y, z), (s, t), color, normal))

        meshes.append(Mesh(prim, alpha, tex, flags, vertices, (amp_s, amp_t), period))

    return Piece(header, textures, meshes, atmosphere)

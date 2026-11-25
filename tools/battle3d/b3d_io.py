"""Binary .b3d v1 writer, mesh container, and validator matching sim_battle3d.h."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

B3D_MAGIC = b"B3D1"
B3D_VERSION = 1

B3D_TEX_FLAG_REPEAT = 1 << 0

B3D_SUBMESH_UNLIT = 1 << 0
B3D_SUBMESH_CAST_SHADOW = 1 << 1
B3D_SUBMESH_RECEIVE_SHADOW = 1 << 2
B3D_SUBMESH_ALPHA_TEST = 1 << 3
B3D_SUBMESH_DOUBLE_SIDED = 1 << 4

HEADER_FMT = "<4s7I"
TEX_DESC_FMT = "<4I"
SUBMESH_DESC_FMT = "<2IiIff2I"
VERTEX_FMT = "<12f"

HEADER_SIZE = struct.calcsize(HEADER_FMT)              # 32
TEX_DESC_SIZE = struct.calcsize(TEX_DESC_FMT)          # 16
SUBMESH_DESC_SIZE = struct.calcsize(SUBMESH_DESC_FMT)  # 32
VERTEX_SIZE = struct.calcsize(VERTEX_FMT)              # 48

assert HEADER_SIZE == 32
assert TEX_DESC_SIZE == 16
assert SUBMESH_DESC_SIZE == 32
assert VERTEX_SIZE == 48


def v3_norm(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if l < 1e-12:
        return (0.0, 1.0, 0.0)
    inv = 1.0 / l
    return (v[0] * inv, v[1] * inv, v[2] * inv)


@dataclass
class TextureAsset:
    width: int
    height: int
    rgba: bytes
    flags: int = B3D_TEX_FLAG_REPEAT


@dataclass
class SubmeshBuilder:
    texture_index: int
    flags: int
    roughness: float = 0.75
    fog_factor: float = 1.0
    vertices: List[Tuple[float, ...]] = field(default_factory=list)
    indices: List[int] = field(default_factory=list)

    def add_vertex(
        self,
        pos: Tuple[float, float, float],
        norm: Tuple[float, float, float],
        uv: Tuple[float, float],
        color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    ) -> int:
        nx, ny, nz = v3_norm(norm)
        idx = len(self.vertices)
        self.vertices.append((
            float(pos[0]), float(pos[1]), float(pos[2]),
            nx, ny, nz,
            float(uv[0]), float(uv[1]),
            max(0.0, min(1.0, float(color[0]))),
            max(0.0, min(1.0, float(color[1]))),
            max(0.0, min(1.0, float(color[2]))),
            max(0.0, min(1.0, float(color[3]))),
        ))
        return idx

    def add_tri(self, i0: int, i1: int, i2: int, enforce_winding: bool = True) -> None:
        if i0 == i1 or i1 == i2 or i2 == i0:
            return
        v0 = self.vertices[i0]
        v1 = self.vertices[i1]
        v2 = self.vertices[i2]
        e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
        cx = e1[1] * e2[2] - e1[2] * e2[1]
        cy = e1[2] * e2[0] - e1[0] * e2[2]
        cz = e1[0] * e2[1] - e1[1] * e2[0]
        if cx * cx + cy * cy + cz * cz < 1e-14:
            return
        if enforce_winding:
            anx = v0[3] + v1[3] + v2[3]
            any_ = v0[4] + v1[4] + v2[4]
            anz = v0[5] + v1[5] + v2[5]
            if cx * anx + cy * any_ + cz * anz < 0.0:
                i1, i2 = i2, i1
        self.indices.append(i0)
        self.indices.append(i1)
        self.indices.append(i2)

    def add_quad(self, i0: int, i1: int, i2: int, i3: int, enforce_winding: bool = True) -> None:
        self.add_tri(i0, i1, i2, enforce_winding=enforce_winding)
        self.add_tri(i0, i2, i3, enforce_winding=enforce_winding)

    def add_flat_tri(
        self,
        p0: Tuple[float, float, float],
        p1: Tuple[float, float, float],
        p2: Tuple[float, float, float],
        uv0: Tuple[float, float],
        uv1: Tuple[float, float],
        uv2: Tuple[float, float],
        c0: Tuple[float, float, float, float],
        c1: Tuple[float, float, float, float],
        c2: Tuple[float, float, float, float],
        outward_hint: Tuple[float, float, float] | None = None,
    ) -> None:
        e1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        e2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        cx = e1[1] * e2[2] - e1[2] * e2[1]
        cy = e1[2] * e2[0] - e1[0] * e2[2]
        cz = e1[0] * e2[1] - e1[1] * e2[0]
        l2 = cx * cx + cy * cy + cz * cz
        if l2 < 1e-14:
            return
        if outward_hint is not None:
            if cx * outward_hint[0] + cy * outward_hint[1] + cz * outward_hint[2] < 0.0:
                p1, p2 = p2, p1
                uv1, uv2 = uv2, uv1
                c1, c2 = c2, c1
                cx, cy, cz = -cx, -cy, -cz
        n = v3_norm((cx, cy, cz))
        i0 = self.add_vertex(p0, n, uv0, c0)
        i1 = self.add_vertex(p1, n, uv1, c1)
        i2 = self.add_vertex(p2, n, uv2, c2)
        self.indices.extend((i0, i1, i2))

    def add_flat_quad(
        self,
        p0: Tuple[float, float, float],
        p1: Tuple[float, float, float],
        p2: Tuple[float, float, float],
        p3: Tuple[float, float, float],
        uv0: Tuple[float, float],
        uv1: Tuple[float, float],
        uv2: Tuple[float, float],
        uv3: Tuple[float, float],
        c0: Tuple[float, float, float, float],
        c1: Tuple[float, float, float, float],
        c2: Tuple[float, float, float, float],
        c3: Tuple[float, float, float, float],
        outward_hint: Tuple[float, float, float] | None = None,
    ) -> None:
        self.add_flat_tri(p0, p1, p2, uv0, uv1, uv2, c0, c1, c2, outward_hint)
        self.add_flat_tri(p0, p2, p3, uv0, uv2, uv3, c0, c2, c3, outward_hint)

    def recompute_smooth_normals(self, invert: bool = False) -> None:
        n = len(self.vertices)
        acc = [[0.0, 0.0, 0.0] for _ in range(n)]
        inds = self.indices
        verts = self.vertices
        for t in range(0, len(inds), 3):
            i0, i1, i2 = inds[t], inds[t + 1], inds[t + 2]
            v0, v1, v2 = verts[i0], verts[i1], verts[i2]
            e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
            e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
            cx = e1[1] * e2[2] - e1[2] * e2[1]
            cy = e1[2] * e2[0] - e1[0] * e2[2]
            cz = e1[0] * e2[1] - e1[1] * e2[0]
            if invert:
                cx, cy, cz = -cx, -cy, -cz
            for idx in (i0, i1, i2):
                acc[idx][0] += cx
                acc[idx][1] += cy
                acc[idx][2] += cz
        for idx in range(n):
            nx, ny, nz = v3_norm((acc[idx][0], acc[idx][1], acc[idx][2]))
            v = verts[idx]
            verts[idx] = (v[0], v[1], v[2], nx, ny, nz, v[6], v[7], v[8], v[9], v[10], v[11])


@dataclass
class ArenaScene:
    name: str
    textures: List[TextureAsset] = field(default_factory=list)
    submeshes: List[SubmeshBuilder] = field(default_factory=list)

    def add_texture(self, width: int, height: int, rgba: bytes, flags: int = B3D_TEX_FLAG_REPEAT) -> int:
        assert len(rgba) == width * height * 4
        idx = len(self.textures)
        self.textures.append(TextureAsset(width, height, rgba, flags))
        return idx

    def add_submesh(
        self,
        texture_index: int,
        flags: int,
        roughness: float = 0.75,
        fog_factor: float = 1.0,
    ) -> SubmeshBuilder:
        sm = SubmeshBuilder(
            texture_index=texture_index,
            flags=flags,
            roughness=roughness,
            fog_factor=fog_factor,
        )
        self.submeshes.append(sm)
        return sm

    def write_b3d(self, out_path: Path) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        active_submeshes = [sm for sm in self.submeshes if len(sm.indices) > 0]

        all_verts: List[Tuple[float, ...]] = []
        all_indices: List[int] = []
        submesh_descs: List[Tuple[int, int, int, int, float, float, int, int]] = []

        for sm in active_submeshes:
            base_v = len(all_verts)
            first_idx = len(all_indices)
            all_verts.extend(sm.vertices)
            all_indices.extend(i + base_v for i in sm.indices)
            submesh_descs.append((
                first_idx,
                len(sm.indices),
                sm.texture_index,
                sm.flags,
                float(sm.roughness),
                float(sm.fog_factor),
                0,
                0,
            ))

        num_tex = len(self.textures)
        num_sm = len(submesh_descs)
        num_v = len(all_verts)
        num_i = len(all_indices)

        data_start = (
            HEADER_SIZE
            + num_tex * TEX_DESC_SIZE
            + num_sm * SUBMESH_DESC_SIZE
            + num_v * VERTEX_SIZE
            + num_i * 4
        )

        tex_descs: List[Tuple[int, int, int, int]] = []
        cursor = data_start
        for tex in self.textures:
            tex_descs.append((tex.width, tex.height, cursor, tex.flags))
            cursor += len(tex.rgba)

        buf = bytearray(cursor)
        pos = 0

        struct.pack_into(
            HEADER_FMT, buf, pos,
            B3D_MAGIC, B3D_VERSION, num_tex, num_sm, num_v, num_i, 0, 0,
        )
        pos += HEADER_SIZE

        for td in tex_descs:
            struct.pack_into(TEX_DESC_FMT, buf, pos, *td)
            pos += TEX_DESC_SIZE

        for sd in submesh_descs:
            struct.pack_into(SUBMESH_DESC_FMT, buf, pos, *sd)
            pos += SUBMESH_DESC_SIZE

        pack_v = struct.Struct(VERTEX_FMT).pack_into
        for v in all_verts:
            pack_v(buf, pos, *v)
            pos += VERTEX_SIZE

        if num_i:
            struct.pack_into(f"<{num_i}I", buf, pos, *all_indices)
            pos += num_i * 4

        assert pos == data_start
        for tex in self.textures:
            nbytes = len(tex.rgba)
            buf[pos:pos + nbytes] = tex.rgba
            pos += nbytes

        assert pos == cursor
        out_path.write_bytes(buf)


def validate_b3d(path: Path) -> dict:
    """Strictly validate a .b3d v1 file against sim_battle3d.h layout & geometry invariants."""
    data = path.read_bytes()
    file_size = len(data)
    if file_size < HEADER_SIZE:
        raise ValueError(f"{path}: truncated header ({file_size} bytes)")

    magic, version, num_tex, num_sm, num_v, num_i, pad0, pad1 = struct.unpack_from(HEADER_FMT, data, 0)
    if magic != B3D_MAGIC:
        raise ValueError(f"{path}: bad magic {magic!r}")
    if version != B3D_VERSION:
        raise ValueError(f"{path}: bad version {version}")
    if pad0 != 0 or pad1 != 0:
        raise ValueError(f"{path}: non-zero header padding")
    if num_i % 3 != 0 or num_i == 0:
        raise ValueError(f"{path}: invalid index count {num_i}")

    off = HEADER_SIZE
    tex_end = off + num_tex * TEX_DESC_SIZE
    sm_end = tex_end + num_sm * SUBMESH_DESC_SIZE
    v_end = sm_end + num_v * VERTEX_SIZE
    i_end = v_end + num_i * 4
    if i_end > file_size:
        raise ValueError(f"{path}: tables exceed file size ({i_end} > {file_size})")

    textures = []
    expected_pixel_end = i_end
    for t in range(num_tex):
        w, h, data_off, flags = struct.unpack_from(TEX_DESC_FMT, data, off + t * TEX_DESC_SIZE)
        if w == 0 or h == 0:
            raise ValueError(f"{path}: texture {t} zero dimension {w}x{h}")
        nbytes = w * h * 4
        if data_off < i_end or data_off + nbytes > file_size:
            raise ValueError(f"{path}: texture {t} offset out of range ({data_off}+{nbytes} > {file_size})")
        expected_pixel_end = max(expected_pixel_end, data_off + nbytes)
        textures.append((w, h, data_off, flags))

    if expected_pixel_end != file_size:
        raise ValueError(f"{path}: trailing bytes ({expected_pixel_end} != {file_size})")

    covered_indices = 0
    for s in range(num_sm):
        first_i, cnt_i, tex_i, flags, rough, fog, sp0, sp1 = struct.unpack_from(
            SUBMESH_DESC_FMT, data, tex_end + s * SUBMESH_DESC_SIZE
        )
        if cnt_i == 0 or cnt_i % 3 != 0:
            raise ValueError(f"{path}: submesh {s} invalid indexCount {cnt_i}")
        if first_i + cnt_i > num_i:
            raise ValueError(f"{path}: submesh {s} indices out of range")
        if tex_i < -1 or tex_i >= num_tex:
            raise ValueError(f"{path}: submesh {s} invalid textureIndex {tex_i}")
        if not (0.0 <= rough <= 1.0 and 0.0 <= fog <= 1.0):
            raise ValueError(f"{path}: submesh {s} roughness/fog out of range")
        if sp0 != 0 or sp1 != 0:
            raise ValueError(f"{path}: submesh {s} non-zero pad")
        covered_indices += cnt_i

    if covered_indices != num_i:
        raise ValueError(f"{path}: submesh index sum {covered_indices} != {num_i}")

    unpack_v = struct.Struct(VERTEX_FMT).unpack_from
    verts = []
    for vi in range(num_v):
        v = unpack_v(data, sm_end + vi * VERTEX_SIZE)
        for f in v:
            if not math.isfinite(f):
                raise ValueError(f"{path}: non-finite vertex value at v={vi}")
        nlen = math.sqrt(v[3] * v[3] + v[4] * v[4] + v[5] * v[5])
        if abs(nlen - 1.0) > 1e-3:
            raise ValueError(f"{path}: non-unit normal at v={vi}: len={nlen}")
        verts.append(v)

    indices = struct.unpack_from(f"<{num_i}I", data, v_end)
    degenerate = 0
    bad_winding = 0
    for t in range(0, num_i, 3):
        i0, i1, i2 = indices[t], indices[t + 1], indices[t + 2]
        if i0 >= num_v or i1 >= num_v or i2 >= num_v:
            raise ValueError(f"{path}: index out of bounds at tri {t // 3}")
        if i0 == i1 or i1 == i2 or i2 == i0:
            degenerate += 1
            continue
        v0, v1, v2 = verts[i0], verts[i1], verts[i2]
        e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
        cx = e1[1] * e2[2] - e1[2] * e2[1]
        cy = e1[2] * e2[0] - e1[0] * e2[2]
        cz = e1[0] * e2[1] - e1[1] * e2[0]
        if cx * cx + cy * cy + cz * cz < 1e-14:
            degenerate += 1
            continue
        anx = v0[3] + v1[3] + v2[3]
        any_ = v0[4] + v1[4] + v2[4]
        anz = v0[5] + v1[5] + v2[5]
        if cx * anx + cy * any_ + cz * anz < -1e-6:
            bad_winding += 1

    if degenerate > 0:
        raise ValueError(f"{path}: found {degenerate} degenerate triangles")
    if bad_winding > 0:
        raise ValueError(f"{path}: found {bad_winding} inward-wound triangles")

    return {
        "file": path.name,
        "bytes": file_size,
        "textures": num_tex,
        "submeshes": num_sm,
        "vertices": num_v,
        "triangles": num_i // 3,
        "tex_dims": [f"{w}x{h}" for (w, h, _, _) in textures],
    }

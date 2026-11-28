"""Minimal self-contained glTF 2.0 binary (.glb) writer."""

from __future__ import annotations

import io
import json
import struct
from typing import Any

import numpy as np
from PIL import Image

# glTF 2.0 componentType constants
COMP_UNSIGNED_BYTE = 5121
COMP_UNSIGNED_SHORT = 5123
COMP_UNSIGNED_INT = 5125
COMP_FLOAT = 5126

# glTF 2.0 bufferView target constants
TARGET_ARRAY_BUFFER = 34962
TARGET_ELEMENT_ARRAY_BUFFER = 34963

# glTF 2.0 sampler wrap / filter constants
WRAP_CLAMP_TO_EDGE = 33071
WRAP_MIRRORED_REPEAT = 33648
WRAP_REPEAT = 10497
FILTER_LINEAR = 9729
FILTER_LINEAR_MIPMAP_LINEAR = 9987


class GlbBuilder:
    """Builds a self-contained glTF 2.0 binary (.glb) with embedded PNGs."""

    def __init__(self, generator: str = "dazzlingPlatinum-bdsp-extract") -> None:
        self._bin = bytearray()
        self.asset: dict[str, Any] = {"version": "2.0", "generator": generator}
        self.buffer_views: list[dict[str, Any]] = []
        self.accessors: list[dict[str, Any]] = []
        self.images: list[dict[str, Any]] = []
        self.samplers: list[dict[str, Any]] = []
        self.textures: list[dict[str, Any]] = []
        self.materials: list[dict[str, Any]] = []
        self.meshes: list[dict[str, Any]] = []
        self.nodes: list[dict[str, Any]] = []
        self.skins: list[dict[str, Any]] = []
        self.animations: list[dict[str, Any]] = []
        self.scene_roots: list[int] = []
        self.extensions_used: set[str] = set()

    def _pad4(self) -> None:
        rem = len(self._bin) & 3
        if rem:
            self._bin.extend(b"\x00" * (4 - rem))

    def add_buffer_view(self, raw: bytes, target: int | None = None) -> int:
        self._pad4()
        offset = len(self._bin)
        self._bin.extend(raw)
        bv: dict[str, Any] = {
            "buffer": 0,
            "byteOffset": offset,
            "byteLength": len(raw),
        }
        if target is not None:
            bv["target"] = target
        idx = len(self.buffer_views)
        self.buffer_views.append(bv)
        return idx

    def add_accessor(
        self,
        arr: np.ndarray,
        comp_type: int,
        acc_type: str,
        target: int | None = None,
        include_minmax: bool = False,
    ) -> int:
        arr_c = np.ascontiguousarray(arr)
        bv_idx = self.add_buffer_view(arr_c.tobytes(), target=target)
        acc: dict[str, Any] = {
            "bufferView": bv_idx,
            "componentType": comp_type,
            "count": int(arr_c.shape[0]),
            "type": acc_type,
        }
        if include_minmax and arr_c.shape[0] > 0:
            if arr_c.ndim == 1:
                acc["min"] = [float(arr_c.min())]
                acc["max"] = [float(arr_c.max())]
            else:
                acc["min"] = [float(v) for v in arr_c.min(axis=0)]
                acc["max"] = [float(v) for v in arr_c.max(axis=0)]
        idx = len(self.accessors)
        self.accessors.append(acc)
        return idx

    def add_sampler(
        self,
        wrap_s: int = WRAP_REPEAT,
        wrap_t: int = WRAP_REPEAT,
        mag_filter: int = FILTER_LINEAR,
        min_filter: int = FILTER_LINEAR_MIPMAP_LINEAR,
    ) -> int:
        spec = {
            "wrapS": wrap_s,
            "wrapT": wrap_t,
            "magFilter": mag_filter,
            "minFilter": min_filter,
        }
        for i, existing in enumerate(self.samplers):
            if existing == spec:
                return i
        idx = len(self.samplers)
        self.samplers.append(spec)
        return idx

    def add_texture_png(
        self,
        image: Image.Image,
        name: str,
        wrap_s: int = WRAP_REPEAT,
        wrap_t: int = WRAP_REPEAT,
    ) -> int:
        buf = io.BytesIO()
        image.convert("RGBA").save(buf, format="PNG", optimize=True)
        bv_idx = self.add_buffer_view(buf.getvalue(), target=None)
        img_idx = len(self.images)
        self.images.append(
            {"bufferView": bv_idx, "mimeType": "image/png", "name": name}
        )
        samp_idx = self.add_sampler(wrap_s=wrap_s, wrap_t=wrap_t)
        tex_idx = len(self.textures)
        self.textures.append({"sampler": samp_idx, "source": img_idx, "name": name})
        return tex_idx

    def add_material(
        self,
        name: str,
        base_color_tex: int | None = None,
        base_color_factor: list[float] | None = None,
        alpha_mode: str = "OPAQUE",
        alpha_cutoff: float | None = None,
        double_sided: bool = False,
        metallic: float = 0.0,
        roughness: float = 0.9,
        emissive_factor: list[float] | None = None,
        unlit: bool = False,
    ) -> int:
        pbr: dict[str, Any] = {
            "metallicFactor": metallic,
            "roughnessFactor": roughness,
        }
        if base_color_tex is not None:
            pbr["baseColorTexture"] = {"index": base_color_tex}
        if base_color_factor is not None:
            pbr["baseColorFactor"] = [float(x) for x in base_color_factor]
        mat: dict[str, Any] = {
            "name": name,
            "pbrMetallicRoughness": pbr,
            "alphaMode": alpha_mode,
        }
        if alpha_mode == "MASK" and alpha_cutoff is not None:
            mat["alphaCutoff"] = float(alpha_cutoff)
        if double_sided:
            mat["doubleSided"] = True
        if emissive_factor is not None:
            mat["emissiveFactor"] = [float(x) for x in emissive_factor]
        if unlit:
            mat["extensions"] = {"KHR_materials_unlit": {}}
            self.extensions_used.add("KHR_materials_unlit")
        idx = len(self.materials)
        self.materials.append(mat)
        return idx

    def build_bytes(self) -> bytes:
        self._pad4()
        gltf: dict[str, Any] = {
            "asset": self.asset,
            "scene": 0,
            "scenes": [{"nodes": self.scene_roots}],
            "nodes": self.nodes,
            "buffers": [{"byteLength": len(self._bin)}],
            "bufferViews": self.buffer_views,
            "accessors": self.accessors,
        }
        if self.extensions_used:
            gltf["extensionsUsed"] = sorted(self.extensions_used)
        if self.meshes:
            gltf["meshes"] = self.meshes
        if self.materials:
            gltf["materials"] = self.materials
        if self.textures:
            gltf["textures"] = self.textures
        if self.images:
            gltf["images"] = self.images
        if self.samplers:
            gltf["samplers"] = self.samplers
        if self.skins:
            gltf["skins"] = self.skins
        if self.animations:
            gltf["animations"] = self.animations

        json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
        json_pad = (4 - (len(json_bytes) & 3)) & 3
        json_bytes += b" " * json_pad

        bin_bytes = bytes(self._bin)
        total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)

        header = struct.pack("<4sII", b"glTF", 2, total_len)
        chunk_json = struct.pack("<I4s", len(json_bytes), b"JSON") + json_bytes
        chunk_bin = struct.pack("<I4s", len(bin_bytes), b"BIN\x00") + bin_bytes
        return header + chunk_json + chunk_bin

    def write(self, path: str) -> int:
        data = self.build_bytes()
        with open(path, "wb") as f:
            f.write(data)
        return len(data)

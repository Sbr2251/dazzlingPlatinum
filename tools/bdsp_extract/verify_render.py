"""GLB validator and lightweight NumPy/PIL software renderer for visual verification."""

from __future__ import annotations

import io
import json
import math
import struct
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from unity_anim import mat4_from_trs_rh

COMP_DTYPE = {
    5120: np.int8,
    5121: np.uint8,
    5122: np.int16,
    5123: np.uint16,
    5125: np.uint32,
    5126: np.float32,
}
TYPE_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def load_glb(path: str) -> tuple[dict[str, Any], bytes]:
    with open(path, "rb") as f:
        raw = f.read()
    magic, ver, length = struct.unpack_from("<4sII", raw, 0)
    assert magic == b"glTF" and ver == 2, f"Invalid GLB header in {path}"
    jlen, jtype = struct.unpack_from("<I4s", raw, 12)
    assert jtype == b"JSON"
    gltf = json.loads(raw[20 : 20 + jlen].decode("utf-8"))
    boff = 20 + jlen
    blen, btype = struct.unpack_from("<I4s", raw, boff)
    assert btype == b"BIN\x00"
    bin_data = raw[boff + 8 : boff + 8 + blen]
    return gltf, bin_data


def read_accessor(gltf: dict[str, Any], bin_data: bytes, acc_idx: int) -> np.ndarray:
    acc = gltf["accessors"][acc_idx]
    bv = gltf["bufferViews"][acc["bufferView"]]
    dtype = COMP_DTYPE[acc["componentType"]]
    width = TYPE_WIDTH[acc["type"]]
    off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    count = acc["count"]
    arr = np.frombuffer(bin_data, dtype=dtype, count=count * width, offset=off)
    if width > 1:
        arr = arr.reshape((count, width))
    return arr.copy()


def read_texture_image(gltf: dict[str, Any], bin_data: bytes, tex_idx: int) -> Image.Image:
    src = gltf["textures"][tex_idx]["source"]
    img_meta = gltf["images"][src]
    bv = gltf["bufferViews"][img_meta["bufferView"]]
    off = bv.get("byteOffset", 0)
    raw = bin_data[off : off + bv["byteLength"]]
    return Image.open(io.BytesIO(raw)).convert("RGBA")


def eval_glb_pose(
    gltf: dict[str, Any],
    bin_data: bytes,
    clip_name: str | None = None,
    t_sec: float = 0.0,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray | None, str, float]]:
    """Return list of (pos[V,3], norm[V,3], uv[V,2], tris[T,3], tex_rgba_or_None, alpha_mode, cutoff)."""
    nodes = gltf.get("nodes", [])
    n = len(nodes)
    parent = [-1] * n
    for i, nd in enumerate(nodes):
        for ch in nd.get("children", []):
            parent[ch] = i

    overrides: dict[int, dict[str, np.ndarray]] = {}
    if clip_name is not None:
        for anim in gltf.get("animations", []):
            if anim["name"] == clip_name:
                for ch in anim["channels"]:
                    samp = anim["samplers"][ch["sampler"]]
                    times = read_accessor(gltf, bin_data, samp["input"])
                    vals = read_accessor(gltf, bin_data, samp["output"])
                    idx = int(np.searchsorted(times, t_sec, side="right")) - 1
                    idx = max(0, min(len(times) - 1, idx))
                    val = vals[idx].astype(np.float64)
                    if idx + 1 < len(times):
                        dt = float(times[idx + 1] - times[idx])
                        if dt > 1e-6:
                            f = max(0.0, min(1.0, (t_sec - float(times[idx])) / dt))
                            v1 = vals[idx + 1].astype(np.float64)
                            if ch["target"]["path"] == "rotation":
                                if np.dot(val, v1) < 0:
                                    v1 = -v1
                                val = val * (1.0 - f) + v1 * f
                                val /= max(np.linalg.norm(val), 1e-9)
                            else:
                                val = val * (1.0 - f) + v1 * f
                    overrides.setdefault(ch["target"]["node"], {})[ch["target"]["path"]] = val
                break

    local = []
    for i, nd in enumerate(nodes):
        ov = overrides.get(i, {})
        t = ov.get("translation", np.array(nd.get("translation", [0.0, 0.0, 0.0]), dtype=np.float64))
        q = ov.get("rotation", np.array(nd.get("rotation", [0.0, 0.0, 0.0, 1.0]), dtype=np.float64))
        s = ov.get("scale", np.array(nd.get("scale", [1.0, 1.0, 1.0]), dtype=np.float64))
        local.append(mat4_from_trs_rh(t, q, s))

    world: list[np.ndarray | None] = [None] * n

    def get_w(i: int) -> np.ndarray:
        if world[i] is not None:
            return world[i]  # type: ignore[return-value]
        world[i] = local[i] if parent[i] < 0 else (get_w(parent[i]) @ local[i])
        return world[i]  # type: ignore[return-value]

    for i in range(n):
        get_w(i)

    tex_cache: dict[int, np.ndarray] = {}
    out = []
    for ni, nd in enumerate(nodes):
        if "mesh" not in nd:
            continue
        mesh = gltf["meshes"][nd["mesh"]]
        skin_mats = None
        if "skin" in nd:
            skin = gltf["skins"][nd["skin"]]
            ibms_raw = read_accessor(gltf, bin_data, skin["inverseBindMatrices"])
            # glTF MAT4 is column-major -> transpose to row-major
            ibms = ibms_raw.reshape((-1, 4, 4)).transpose((0, 2, 1)).astype(np.float64)
            skin_mats = np.array([world[jn] @ ibm for jn, ibm in zip(skin["joints"], ibms)], dtype=np.float64)
        node_w = world[ni]

        for prim in mesh["primitives"]:
            attrs = prim["attributes"]
            pos = read_accessor(gltf, bin_data, attrs["POSITION"]).astype(np.float64)
            norm = read_accessor(gltf, bin_data, attrs["NORMAL"]).astype(np.float64)
            uv = read_accessor(gltf, bin_data, attrs["TEXCOORD_0"]).astype(np.float64)
            tris = read_accessor(gltf, bin_data, prim["indices"]).reshape((-1, 3)).astype(np.int32)

            if skin_mats is not None and "JOINTS_0" in attrs and "WEIGHTS_0" in attrs:
                joints = read_accessor(gltf, bin_data, attrs["JOINTS_0"]).astype(np.int32)
                weights = read_accessor(gltf, bin_data, attrs["WEIGHTS_0"]).astype(np.float64)
                pos_h = np.concatenate([pos, np.ones((len(pos), 1))], axis=1)
                spos = np.zeros_like(pos)
                snorm = np.zeros_like(norm)
                for k in range(4):
                    w = weights[:, k : k + 1]
                    m = skin_mats[joints[:, k]]
                    spos += w * np.einsum("nij,nj->ni", m[:, :3, :], pos_h)
                    snorm += w * np.einsum("nij,nj->ni", m[:, :3, :3], norm)
                pos = spos
                nlen = np.linalg.norm(snorm, axis=1, keepdims=True)
                norm = snorm / np.maximum(nlen, 1e-6)
            else:
                pos = (pos @ node_w[:3, :3].T) + node_w[:3, 3]
                norm = norm @ node_w[:3, :3].T
                norm /= np.maximum(np.linalg.norm(norm, axis=1, keepdims=True), 1e-6)

            mat = gltf["materials"][prim["material"]]
            alpha_mode = mat.get("alphaMode", "OPAQUE")
            cutoff = float(mat.get("alphaCutoff", 0.5))
            pbr = mat.get("pbrMetallicRoughness", {})
            bcf = pbr.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0])
            tex_arr = None
            bct = pbr.get("baseColorTexture")
            if bct is not None:
                tidx = bct["index"]
                if tidx not in tex_cache:
                    tex_cache[tidx] = np.array(read_texture_image(gltf, bin_data, tidx), dtype=np.uint8)
                tex_arr = tex_cache[tidx]
                if bcf != [1.0, 1.0, 1.0, 1.0]:
                    bcf_arr = np.array(bcf, dtype=np.float32)
                    tex_arr = np.clip(tex_arr.astype(np.float32) * bcf_arr[None, None, :], 0, 255).astype(np.uint8)
            elif bcf != [1.0, 1.0, 1.0, 1.0]:
                px = np.clip(np.array(bcf, dtype=np.float32) * 255.0, 0, 255).astype(np.uint8)
                tex_arr = px.reshape((1, 1, 4))

            out.append((pos, norm, uv, tris, tex_arr, alpha_mode, cutoff))
    return out


def render_preview(
    prims: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray | None, str, float]],
    eye: tuple[float, float, float],
    target: tuple[float, float, float],
    fov_deg: float = 38.0,
    width: int = 512,
    height: int = 384,
    bg_rgb: tuple[int, int, int] = (24, 34, 66),
    backface_cull: bool = True,
) -> Image.Image:
    """Fast vectorized triangle rasterizer (per-triangle centroid texture + Lambert shading + painter sort)."""
    eye_v = np.array(eye, dtype=np.float64)
    tgt_v = np.array(target, dtype=np.float64)
    fwd = tgt_v - eye_v
    fwd /= np.linalg.norm(fwd)
    up_ref = np.array([0.0, 1.0, 0.0]) if abs(fwd[1]) < 0.99 else np.array([0.0, 0.0, -1.0])
    right = np.cross(fwd, up_ref)
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)

    f_scale = 0.5 * height / math.tan(math.radians(fov_deg) * 0.5)
    light_dir = np.array([0.45, 0.75, 0.48], dtype=np.float64)
    light_dir /= np.linalg.norm(light_dir)

    # Collect drawable triangles (screen xy, depth, rgba color) for fast PIL painter render
    draw_list: list[tuple[float, list[tuple[float, float]], tuple[int, int, int, int]]] = []
    for pos, norm, uv, tris, tex_arr, alpha_mode, cutoff in prims:
        # Transform to camera space
        rel = pos - eye_v[None, :]
        cx = rel @ right
        cy = rel @ up
        cz = rel @ fwd  # positive in front of camera

        t0, t1, t2 = tris[:, 0], tris[:, 1], tris[:, 2]
        z0, z1, z2 = cz[t0], cz[t1], cz[t2]
        mask = (z0 > 0.15) & (z1 > 0.15) & (z2 > 0.15)
        if not np.any(mask):
            continue
        t0, t1, t2 = t0[mask], t1[mask], t2[mask]
        z0, z1, z2 = z0[mask], z1[mask], z2[mask]

        sx0 = width * 0.5 + (cx[t0] / z0) * f_scale
        sy0 = height * 0.5 - (cy[t0] / z0) * f_scale
        sx1 = width * 0.5 + (cx[t1] / z1) * f_scale
        sy1 = height * 0.5 - (cy[t1] / z1) * f_scale
        sx2 = width * 0.5 + (cx[t2] / z2) * f_scale
        sy2 = height * 0.5 - (cy[t2] / z2) * f_scale

        # Screen-space signed area (Y-down: CCW front-face has negative screen area)
        area2 = (sx1 - sx0) * (sy2 - sy0) - (sy1 - sy0) * (sx2 - sx0)
        if backface_cull and alpha_mode == "OPAQUE":
            front = area2 < 0.0
        else:
            front = np.abs(area2) > 0.05
        # Frustum bounds clip
        in_view = (
            front
            & (np.maximum(np.maximum(sx0, sx1), sx2) >= 0)
            & (np.minimum(np.minimum(sx0, sx1), sx2) < width)
            & (np.maximum(np.maximum(sy0, sy1), sy2) >= 0)
            & (np.minimum(np.minimum(sy0, sy1), sy2) < height)
        )
        if not np.any(in_view):
            continue

        t0, t1, t2 = t0[in_view], t1[in_view], t2[in_view]
        sx0, sy0 = sx0[in_view], sy0[in_view]
        sx1, sy1 = sx1[in_view], sy1[in_view]
        sx2, sy2 = sx2[in_view], sy2[in_view]
        z_avg = (z0[in_view] + z1[in_view] + z2[in_view]) / 3.0

        # Sample texture at triangle centroid UV
        if tex_arr is not None:
            th, tw = tex_arr.shape[:2]
            uc = (uv[t0, 0] + uv[t1, 0] + uv[t2, 0]) / 3.0
            vc = (uv[t0, 1] + uv[t1, 1] + uv[t2, 1]) / 3.0
            px = np.floor((uc % 1.0) * tw).astype(np.int32) % tw
            py = np.floor((vc % 1.0) * th).astype(np.int32) % th
            rgba = tex_arr[py, px]
            if alpha_mode == "MASK":
                keep = rgba[:, 3] >= int(cutoff * 255)
                if not np.any(keep):
                    continue
                t0, t1, t2 = t0[keep], t1[keep], t2[keep]
                sx0, sy0 = sx0[keep], sy0[keep]
                sx1, sy1 = sx1[keep], sy1[keep]
                sx2, sy2 = sx2[keep], sy2[keep]
                z_avg = z_avg[keep]
                rgba = rgba[keep]
            elif alpha_mode == "BLEND":
                keep = rgba[:, 3] >= 8
                if not np.any(keep):
                    continue
                t0, t1, t2 = t0[keep], t1[keep], t2[keep]
                sx0, sy0 = sx0[keep], sy0[keep]
                sx1, sy1 = sx1[keep], sy1[keep]
                sx2, sy2 = sx2[keep], sy2[keep]
                z_avg = z_avg[keep]
                rgba = rgba[keep]
            rgb = rgba[:, :3].astype(np.float64)
            alpha_u8 = rgba[:, 3] if alpha_mode == "BLEND" else np.full(len(t0), 255, dtype=np.uint8)
        else:
            rgb = np.full((len(t0), 3), 200.0, dtype=np.float64)
            alpha_u8 = np.full(len(t0), 255, dtype=np.uint8)

        if alpha_mode == "BLEND":
            col = np.clip(rgb, 0, 255).astype(np.uint8)
        else:
            fn = (norm[t0] + norm[t1] + norm[t2]) / 3.0
            ndotl = np.clip(fn @ light_dir, -1.0, 1.0)
            shade = 0.45 + 0.55 * np.clip(ndotl * 0.5 + 0.5, 0.0, 1.0)
            col = np.clip(rgb * shade[:, None], 0, 255).astype(np.uint8)

        for i in range(len(t0)):
            draw_list.append(
                (
                    float(z_avg[i]),
                    [(float(sx0[i]), float(sy0[i])), (float(sx1[i]), float(sy1[i])), (float(sx2[i]), float(sy2[i]))],
                    (int(col[i, 0]), int(col[i, 1]), int(col[i, 2]), int(alpha_u8[i])),
                )
            )

    draw_list.sort(key=lambda item: -item[0])
    img = Image.new("RGB", (width, height), bg_rgb)
    draw = ImageDraw.Draw(img, "RGBA")
    for _, poly, color in draw_list:
        draw.polygon(poly, fill=color)
    return img


def make_texture_contact_sheet(textures: list[tuple[str, Image.Image]], out_path: str, tile: int = 192) -> None:
    if not textures:
        return
    cols = min(5, len(textures))
    rows = (len(textures) + cols - 1) // cols
    label_h = 22
    sheet = Image.new("RGB", (cols * (tile + 8) + 8, rows * (tile + label_h + 8) + 8), (24, 24, 28))
    draw = ImageDraw.Draw(sheet)
    for idx, (name, im) in enumerate(textures):
        r, c = divmod(idx, cols)
        x = 8 + c * (tile + 8)
        y = 8 + r * (tile + label_h + 8)
        # Checkerboard behind transparent textures
        thumb = Image.new("RGBA", (tile, tile), (48, 48, 56, 255))
        resized = im.convert("RGBA").resize((tile, tile), Image.Resampling.BILINEAR)
        thumb = Image.alpha_composite(thumb, resized).convert("RGB")
        sheet.paste(thumb, (x, y))
        draw.text((x + 2, y + tile + 4), name[:28], fill=(235, 235, 240))
    sheet.save(out_path)

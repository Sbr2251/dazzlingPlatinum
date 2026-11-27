"""Extract a BDSP 3D battle arena ground prefab (e.g. g005 Forest) to a self-contained glTF 2.0 (.glb)."""

from __future__ import annotations

import math
import os
from typing import Any

import numpy as np
from PIL import Image
import UnityPy
from UnityPy.helpers import MeshHelper

from gltf_writer import (
    COMP_FLOAT,
    COMP_UNSIGNED_INT,
    COMP_UNSIGNED_SHORT,
    GlbBuilder,
    TARGET_ARRAY_BUFFER,
    TARGET_ELEMENT_ARRAY_BUFFER,
    WRAP_REPEAT,
)
from unity_anim import lh_to_rh_mat4, mat4_from_trs_rh

# Canonical biome stem -> BDSP Environments/bg/arenas/ground/<id>
ARENA_BIOME_MAP: dict[str, str] = {
    "plain_route": "g001",
    "forest": "g005",
    "water_lake": "g020",
    "mountain_cave": "g011",
    "snow": "g017",
    "city": "g008",
    "indoors_gym": "g024",
    "distortion_world": "g037",
}

STRIP_ARENA_TOKENS = ("collider", "collision", "trigger", "shadow", "dummy", "debug", "sphere")


def _get_dict(prop: Any) -> dict[str, Any]:
    if isinstance(prop, dict):
        return prop
    return dict(prop)


def _unity_trs_mat4(tr: Any) -> np.ndarray:
    t = tr.m_LocalPosition
    q = tr.m_LocalRotation
    s = tr.m_LocalScale
    x, y, z, w = q.x, q.y, q.z, q.w
    R = np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0.0],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0.0],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    S = np.diag([s.x, s.y, s.z, 1.0])
    T = np.eye(4, dtype=np.float64)
    T[0, 3], T[1, 3], T[2, 3] = t.x, t.y, t.z
    return T @ R @ S


def _yaw_mat4_rh(yaw_deg: float) -> np.ndarray:
    rad = math.radians(yaw_deg)
    c, s = math.cos(rad), math.sin(rad)
    return np.array(
        [
            [c, 0.0, s, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [-s, 0.0, c, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def _bake_ground_blend_texture(
    mat: Any,
    uv0_arr: np.ndarray,
    uv1_arr: np.ndarray,
    size: int = 1024,
) -> tuple[Image.Image, bool]:
    """Bake a BDSP 2-layer ground material (_MainTex soil + _LayerTex grass via _BlendTex on UV1).

    Returns (baked_rgba_image, use_uv1_as_texcoord).
    """
    tex_envs = _get_dict(mat.m_SavedProperties.m_TexEnvs)
    main_te = tex_envs.get("_MainTex")
    layer_te = tex_envs.get("_LayerTex")
    blend_te = tex_envs.get("_BlendTex")

    if not (
        main_te
        and main_te.m_Texture.path_id
        and layer_te
        and layer_te.m_Texture.path_id
        and blend_te
        and blend_te.m_Texture.path_id
        and uv1_arr is not None
        and len(uv1_arr) == len(uv0_arr)
    ):
        return None, False  # type: ignore[return-value]

    # Only bake when _MainTex and _LayerTex are actually different textures (e.g. Soil + Grass)
    if main_te.m_Texture.path_id == layer_te.m_Texture.path_id:
        return None, False  # type: ignore[return-value]

    soil_img = np.array(main_te.m_Texture.read().image.convert("RGBA"), dtype=np.float32)
    grass_img = np.array(layer_te.m_Texture.read().image.convert("RGBA"), dtype=np.float32)
    mask_img = np.array(
        blend_te.m_Texture.read().image.convert("RGBA").resize((size, size), Image.Resampling.BILINEAR),
        dtype=np.float32,
    )

    # Fit affine map uv0 = uv1 @ A + b so we can sample tiled soil & grass at each UV1 pixel
    X = np.hstack([uv1_arr.astype(np.float64), np.ones((len(uv1_arr), 1), dtype=np.float64)])
    coef, _, _, _ = np.linalg.lstsq(X, uv0_arr.astype(np.float64), rcond=None)

    # Build UV1 grid matching PNG layout (row 0 = top = Unity V=1)
    u1 = np.linspace(0.0, 1.0, size, endpoint=False, dtype=np.float64) + 0.5 / size
    v1 = 1.0 - (np.linspace(0.0, 1.0, size, endpoint=False, dtype=np.float64) + 0.5 / size)
    UU1, VV1 = np.meshgrid(u1, v1)
    u0 = UU1 * coef[0, 0] + VV1 * coef[1, 0] + coef[2, 0]
    v0 = UU1 * coef[0, 1] + VV1 * coef[1, 1] + coef[2, 1]

    msx, msy = float(main_te.m_Scale.x), float(main_te.m_Scale.y)
    mox, moy = float(main_te.m_Offset.x), float(main_te.m_Offset.y)
    lsx, lsy = float(layer_te.m_Scale.x), float(layer_te.m_Scale.y)
    lox, loy = float(layer_te.m_Offset.x), float(layer_te.m_Offset.y)

    sh, sw = soil_img.shape[:2]
    gh, gw = grass_img.shape[:2]

    su = np.floor(((u0 * msx + mox) % 1.0) * sw).astype(np.int32) % sw
    sv = np.floor(((1.0 - ((v0 * msy + moy) % 1.0)) % 1.0) * sh).astype(np.int32) % sh
    gu = np.floor(((u0 * lsx + lox) % 1.0) * gw).astype(np.int32) % gw
    gv = np.floor(((1.0 - ((v0 * lsy + loy) % 1.0)) % 1.0) * gh).astype(np.int32) % gh

    soil_px = soil_img[sv, su, :3]
    grass_px = grass_img[gv, gu, :3]

    # BDSP GroundMask_01_M: R channel = soil/dirt clearing (yellow center R=1, G=1), green outer (R=0, G=1)
    # Keep a subtle natural blend matching BDSP's clearing (soft dusty-grass transition)
    soil_w = np.clip((mask_img[:, :, 0] / 255.0) * 0.45, 0.0, 1.0)[:, :, None]
    out_rgb = grass_px * (1.0 - soil_w) + soil_px * soil_w
    rgba = np.concatenate(
        [np.clip(out_rgb, 0, 255).astype(np.uint8), np.full((size, size, 1), 255, dtype=np.uint8)],
        axis=2,
    )
    return Image.fromarray(rgba, mode="RGBA"), True


def extract_arena_glb(
    aa_root: str,
    biome: str,
    out_glb_path: str,
    yaw_deg: float = 0.0,
) -> dict[str, Any]:
    """Extract a BDSP battle arena ground prefab to a batched, static RH glTF 2.0 (.glb)."""
    ground_id = ARENA_BIOME_MAP.get(biome, biome)
    bundle_path = os.path.join(aa_root, "Environments/bg/arenas/ground", ground_id)
    if not os.path.isfile(bundle_path):
        raise FileNotFoundError(f"Arena bundle not found: {bundle_path}")

    env = UnityPy.load(bundle_path)
    objs = {o.path_id: o for o in env.objects}
    transforms = {o.path_id: o.read() for o in env.objects if o.type.name == "Transform"}
    roots = [pid for pid, tr in transforms.items() if tr.m_Father.path_id == 0]

    # Compute Unity world matrices
    world_u: dict[int, np.ndarray] = {}

    def walk_u(pid: int, parent_m: np.ndarray) -> None:
        tr = transforms[pid]
        wm = parent_m @ _unity_trs_mat4(tr)
        world_u[pid] = wm
        for ch in tr.m_Children:
            if ch.path_id in transforms:
                walk_u(ch.path_id, wm)

    for r in roots:
        walk_u(r, np.eye(4, dtype=np.float64))

    yaw_m = _yaw_mat4_rh(yaw_deg)

    # Group geometry by material path_id so we emit minimal draw calls (1 primitive per material)
    mat_buckets: dict[int, dict[str, Any]] = {}
    ground_y_samples: list[float] = []
    mesh_count = 0

    for obj in env.objects:
        if obj.type.name != "MeshRenderer":
            continue
        mr = obj.read()
        go = mr.m_GameObject.read()
        if not go.m_IsActive or not mr.m_Enabled:
            continue
        lname = go.m_Name.lower()
        if any(tok in lname for tok in STRIP_ARENA_TOKENS):
            continue

        tr_pid = None
        mf = None
        for comp in go.m_Component:
            cobj = objs.get(comp.component.path_id)
            if cobj is None:
                continue
            if cobj.type.name == "Transform":
                tr_pid = cobj.path_id
            elif cobj.type.name == "MeshFilter":
                mf = cobj.read()
        if tr_pid is None or mf is None or not mf.m_Mesh.path_id:
            continue

        mesh = mf.m_Mesh.read()
        if any(tok in mesh.m_Name.lower() for tok in STRIP_ARENA_TOKENS):
            continue

        mh = MeshHelper.MeshHandler(mesh)
        mh.process()
        if not mh.m_Vertices:
            continue

        verts_u = np.array(mh.m_Vertices, dtype=np.float64)[:, :3]
        norms_u = (
            np.array(mh.m_Normals, dtype=np.float64)[:, :3]
            if (mh.m_Normals and len(mh.m_Normals) == len(verts_u))
            else np.tile(np.array([[0.0, 1.0, 0.0]], dtype=np.float64), (len(verts_u), 1))
        )
        uv0_u = (
            np.array(mh.m_UV0, dtype=np.float32)[:, :2]
            if (mh.m_UV0 and len(mh.m_UV0) == len(verts_u))
            else np.zeros((len(verts_u), 2), dtype=np.float32)
        )
        uv1_u = (
            np.array(mh.m_UV1, dtype=np.float32)[:, :2]
            if (mh.m_UV1 and len(mh.m_UV1) == len(verts_u))
            else None
        )

        # Unity world -> RH world -> optional yaw
        wm_rh = yaw_m @ lh_to_rh_mat4(world_u[tr_pid])
        det = float(np.linalg.det(wm_rh[:3, :3]))
        pos_rh = verts_u.copy()
        pos_rh[:, 0] = -pos_rh[:, 0]
        pos_w = (pos_rh @ wm_rh[:3, :3].T) + wm_rh[:3, 3]

        norm_rh = norms_u.copy()
        norm_rh[:, 0] = -norm_rh[:, 0]
        inv_t = np.linalg.inv(wm_rh[:3, :3]).T if abs(det) > 1e-12 else wm_rh[:3, :3]
        norm_w = norm_rh @ inv_t.T
        nlen = np.linalg.norm(norm_w, axis=1, keepdims=True)
        norm_w = np.where(nlen > 1e-6, norm_w / np.maximum(nlen, 1e-6), np.array([0.0, 1.0, 0.0]))

        tris_by_sm = mh.get_triangles()
        mats = [mp.read() if mp.path_id else None for mp in mr.m_Materials]
        mesh_count += 1

        for smi, sm_tris in enumerate(tris_by_sm):
            if not sm_tris:
                continue
            mat_obj = mats[smi] if smi < len(mats) else None
            mat_pid = mr.m_Materials[smi].path_id if smi < len(mr.m_Materials) else 0
            mname = mat_obj.m_Name if mat_obj else "default"

            # Record clearing ground Y near center
            if "ground" in mname.lower():
                r2 = pos_w[:, 0] ** 2 + pos_w[:, 2] ** 2
                near = r2 < 100.0
                if np.any(near):
                    ground_y_samples.extend(pos_w[near, 1].tolist())

            b = mat_buckets.setdefault(
                mat_pid,
                {
                    "mat_obj": mat_obj,
                    "name": mname,
                    "pos": [],
                    "norm": [],
                    "uv0": [],
                    "uv1": [],
                    "has_uv1": True,
                    "idx": [],
                    "v_offset": 0,
                },
            )

            tri_arr = np.array(sm_tris, dtype=np.uint32)
            # LH->RH flips winding; negative determinant scale flips it back
            if det >= 0.0:
                tri_arr = tri_arr[:, [0, 2, 1]]

            uniq, inv = np.unique(tri_arr.ravel(), return_inverse=True)
            b["pos"].append(pos_w[uniq].astype(np.float32))
            b["norm"].append(norm_w[uniq].astype(np.float32))
            b["uv0"].append(uv0_u[uniq].astype(np.float32))
            if uv1_u is not None:
                b["uv1"].append(uv1_u[uniq].astype(np.float32))
            else:
                b["has_uv1"] = False
            b["idx"].append(inv.astype(np.uint32) + b["v_offset"])
            b["v_offset"] += len(uniq)

    # Shift clearing floor to exact Y = 0 if needed
    ground_y = float(np.median(ground_y_samples)) if ground_y_samples else 0.0

    builder = GlbBuilder()
    primitives: list[dict[str, Any]] = []
    decoded_textures: list[tuple[str, Image.Image]] = []
    total_verts = 0
    total_tris = 0
    all_min = np.array([1e9, 1e9, 1e9], dtype=np.float64)
    all_max = np.array([-1e9, -1e9, -1e9], dtype=np.float64)

    for mat_pid, b in sorted(mat_buckets.items(), key=lambda kv: kv[1]["name"]):
        mat_obj = b["mat_obj"]
        mname = b["name"]
        pos = np.concatenate(b["pos"], axis=0)
        if abs(ground_y) > 1e-4:
            pos[:, 1] -= ground_y
        norm = np.concatenate(b["norm"], axis=0)
        uv0 = np.concatenate(b["uv0"], axis=0)
        uv1 = np.concatenate(b["uv1"], axis=0) if (b["has_uv1"] and b["uv1"]) else None
        indices = np.concatenate(b["idx"], axis=0)

        all_min = np.minimum(all_min, pos.min(axis=0))
        all_max = np.maximum(all_max, pos.max(axis=0))
        total_verts += len(pos)
        total_tris += len(indices) // 3

        # Resolve material texture, UV transform, alpha mode, doubleSided
        img = None
        use_uv1 = False
        usx, usy, uox, uoy = 1.0, 1.0, 0.0, 0.0
        alpha_mode = "OPAQUE"
        alpha_cutoff = None
        double_sided = False

        if mat_obj is not None:
            fl = _get_dict(mat_obj.m_SavedProperties.m_Floats)
            if float(fl.get("_AlphaClip", 0.0)) >= 0.5:
                alpha_mode = "MASK"
                alpha_cutoff = float(fl.get("_Cutoff", 0.5))
            if float(fl.get("_Cull", 2.0)) < 0.5:
                double_sided = True

            # Try baked soil+grass ground mask blend first
            baked_img, use_uv1 = _bake_ground_blend_texture(mat_obj, uv0, uv1) if uv1 is not None else (None, False)
            if baked_img is not None:
                img = baked_img
            else:
                tex_envs = _get_dict(mat_obj.m_SavedProperties.m_TexEnvs)
                te = tex_envs.get("_MainTex")
                if not te or not te.m_Texture.path_id:
                    te = tex_envs.get("_LayerTex")
                if te and te.m_Texture.path_id:
                    img = te.m_Texture.read().image.convert("RGBA")
                    usx, usy = float(te.m_Scale.x), float(te.m_Scale.y)
                    uox, uoy = float(te.m_Offset.x), float(te.m_Offset.y)

        if use_uv1 and uv1 is not None:
            uv_out = uv1.copy()
            uv_out[:, 1] = 1.0 - uv_out[:, 1]
        else:
            uv_out = uv0.copy()
            uv_out[:, 0] = uv_out[:, 0] * usx + uox
            uv_out[:, 1] = 1.0 - (uv_out[:, 1] * usy + uoy)

        tex_idx = None
        if img is not None:
            tex_idx = builder.add_texture_png(img, f"{mname}_diffuse", wrap_s=WRAP_REPEAT, wrap_t=WRAP_REPEAT)
            decoded_textures.append((mname, img))

        gltf_mat_idx = builder.add_material(
            name=mname,
            base_color_tex=tex_idx,
            base_color_factor=[1.0, 1.0, 1.0, 1.0],
            alpha_mode=alpha_mode,
            alpha_cutoff=alpha_cutoff,
            double_sided=double_sided,
        )

        pos_acc = builder.add_accessor(pos.astype(np.float32), COMP_FLOAT, "VEC3", TARGET_ARRAY_BUFFER, include_minmax=True)
        norm_acc = builder.add_accessor(norm.astype(np.float32), COMP_FLOAT, "VEC3", TARGET_ARRAY_BUFFER)
        uv_acc = builder.add_accessor(uv_out.astype(np.float32), COMP_FLOAT, "VEC2", TARGET_ARRAY_BUFFER)
        if len(pos) < 65535:
            idx_acc = builder.add_accessor(indices.astype(np.uint16), COMP_UNSIGNED_SHORT, "SCALAR", TARGET_ELEMENT_ARRAY_BUFFER)
        else:
            idx_acc = builder.add_accessor(indices.astype(np.uint32), COMP_UNSIGNED_INT, "SCALAR", TARGET_ELEMENT_ARRAY_BUFFER)

        primitives.append(
            {
                "attributes": {
                    "POSITION": pos_acc,
                    "NORMAL": norm_acc,
                    "TEXCOORD_0": uv_acc,
                },
                "indices": idx_acc,
                "material": gltf_mat_idx,
            }
        )

    mesh_idx = len(builder.meshes)
    builder.meshes.append({"name": f"arena_{biome}_{ground_id}", "primitives": primitives})
    node_idx = len(builder.nodes)
    builder.nodes.append({"name": f"arena_{biome}", "mesh": mesh_idx})
    builder.scene_roots.append(node_idx)

    os.makedirs(os.path.dirname(os.path.abspath(out_glb_path)), exist_ok=True)
    file_bytes = builder.write(out_glb_path)

    return {
        "biome": biome,
        "source_ground": ground_id,
        "yaw_deg": yaw_deg,
        "file": os.path.relpath(out_glb_path, os.path.dirname(os.path.dirname(out_glb_path))),
        "size_bytes": file_bytes,
        "source_meshes": mesh_count,
        "primitives": len(primitives),
        "vertices": total_verts,
        "triangles": total_tris,
        "materials": len(builder.materials),
        "textures": len(builder.textures),
        "ground_offset_y": round(-ground_y, 4),
        "bbox_min": [round(float(x), 4) for x in all_min],
        "bbox_max": [round(float(x), 4) for x in all_max],
        "decoded_textures": decoded_textures,
    }

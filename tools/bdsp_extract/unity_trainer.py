#!/usr/bin/env python3
"""Extract BDSP 3D battle trainers (Lucas pc0001_00, Dawn pc0002_00) and 3D Poke Ball (ob0204_00) to glTF 2.0 (.glb)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
import UnityPy
from UnityPy.helpers import MeshHelper

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from gltf_writer import (
    COMP_FLOAT,
    COMP_UNSIGNED_INT,
    COMP_UNSIGNED_SHORT,
    GlbBuilder,
    TARGET_ARRAY_BUFFER,
    TARGET_ELEMENT_ARRAY_BUFFER,
    WRAP_CLAMP_TO_EDGE,
    WRAP_REPEAT,
)
from unity_anim import (
    build_transform_path_crc_map,
    decode_animation_clip,
    lh_to_rh_mat4,
    lh_to_rh_quat,
    lh_to_rh_vec3,
    mat4_from_trs_rh,
)
from unity_pokemon import _compute_world_mats_rh, _get_dict, _skin_positions

MAX_JOINTS = 192

TRAINER_CLIP_CANDIDATES: dict[str, list[str]] = {
    "wait": ["wait_b", "wait02_b", "stand_b"],
    "throw": ["advent03_b", "advent06_b", "advent_b", "order_b"],
    "advent": ["advent_b", "advent05_b", "advent06_b"],
    "lose": ["look_left_down_b", "wait02_b", "pose_b"],
}

STRIP_MAT_NAMES = {"shadow"}
STRIP_MESH_TOKENS = ("collider", "proxy", "debug", "hitcheck", "dammy")


def _extract_color_variation_overrides(env: Any) -> dict[tuple[int, int, int], np.ndarray]:
    """Read BDSP ColorVariation MonoBehaviour (ColorIndex==0 / Property00) -> {(smr_pid, mat_idx, channel): rgb}."""
    overrides: dict[tuple[int, int, int], np.ndarray] = {}
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if "ColorIndex" not in tree or "Property00" not in tree:
            continue
        prop0 = tree.get("Property00")
        if not isinstance(prop0, list):
            continue
        for entry in prop0:
            ren = entry.get("renderer", {})
            rpid = int(ren.get("m_PathID", 0))
            if not rpid:
                continue
            for citem in entry.get("colors", []):
                mi = int(citem.get("materialIndex", -1))
                ch = int(citem.get("channel", -1))
                col = citem.get("color", {})
                if mi >= 0 and ch in (0, 1, 2) and isinstance(col, dict):
                    overrides[(rpid, mi, ch)] = np.array(
                        [float(col.get("r", 1.0)), float(col.get("g", 1.0)), float(col.get("b", 1.0))],
                        dtype=np.float32,
                    )
    return overrides


def _mat_color_rgb(cols: dict[str, Any], key: str, default: tuple[float, float, float] = (1.0, 1.0, 1.0)) -> np.ndarray:
    c = cols.get(key)
    if c is None:
        return np.array(default, dtype=np.float32)
    return np.array([float(c.r), float(c.g), float(c.b)], dtype=np.float32)


def _extract_trainer_material(
    mat: Any,
    smr_pid: int = 0,
    mat_idx: int = -1,
    color_overrides: dict[tuple[int, int, int], np.ndarray] | None = None,
) -> tuple[Image.Image | None, tuple[float, float], tuple[float, float], int, int]:
    """Return (diffuse_rgba, uv_scale, uv_offset, wrap_s, wrap_t) with BDSP _MaskTex colorization baked in."""
    if mat is None:
        return None, (1.0, 1.0), (0.0, 0.0), WRAP_REPEAT, WRAP_REPEAT
    tex_envs = _get_dict(mat.m_SavedProperties.m_TexEnvs)
    c0 = tex_envs.get("_MainTex") or tex_envs.get("_Col0Tex")
    if not c0 or not c0.m_Texture.path_id:
        return None, (1.0, 1.0), (0.0, 0.0), WRAP_REPEAT, WRAP_REPEAT

    tex_obj = c0.m_Texture.read()
    img = tex_obj.image.convert("RGBA")
    arr = np.array(img, dtype=np.float32) / 255.0
    base_rgb = arr[:, :, :3]

    # Bake BDSP 3-channel mask colorization: R=_SkinColor (ch0), G=_PrimaryColor (ch1), B=_SecondaryColor (ch2)
    msk = tex_envs.get("_MaskTex")
    if msk and msk.m_Texture.path_id:
        cols = _get_dict(mat.m_SavedProperties.m_Colors)
        c_skin = _mat_color_rgb(cols, "_SkinColor")
        c_prim = _mat_color_rgb(cols, "_PrimaryColor")
        c_sec = _mat_color_rgb(cols, "_SecondaryColor")
        if color_overrides:
            c_skin = color_overrides.get((smr_pid, mat_idx, 0), c_skin)
            c_prim = color_overrides.get((smr_pid, mat_idx, 1), c_prim)
            c_sec = color_overrides.get((smr_pid, mat_idx, 2), c_sec)

        msk_img = msk.m_Texture.read().image.convert("RGBA")
        if msk_img.size != img.size:
            msk_img = msk_img.resize(img.size, Image.Resampling.BILINEAR)
        m_arr = np.array(msk_img, dtype=np.float32) / 255.0
        wr = m_arr[:, :, 0]
        wg = m_arr[:, :, 1]
        wb = m_arr[:, :, 2]
        wsum = wr + wg + wb
        w_unmasked = np.clip(1.0 - wsum, 0.0, 1.0)
        norm = np.where(wsum > 1.0, 1.0 / np.maximum(wsum, 1e-6), 1.0)
        tint = (
            w_unmasked[:, :, None]
            + (wr * norm)[:, :, None] * c_skin[None, None, :]
            + (wg * norm)[:, :, None] * c_prim[None, None, :]
            + (wb * norm)[:, :, None] * c_sec[None, None, :]
        )
        base_rgb = np.clip(base_rgb * tint, 0.0, 1.0)

    out_u8 = np.empty((img.height, img.width, 4), dtype=np.uint8)
    out_u8[:, :, :3] = np.clip(base_rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
    out_u8[:, :, 3] = 255
    img = Image.fromarray(out_u8, mode="RGBA")

    sx, sy = float(c0.m_Scale.x), float(c0.m_Scale.y)
    ox, oy = float(c0.m_Offset.x), float(c0.m_Offset.y)
    wrap_u = int(tex_obj.m_TextureSettings.m_WrapU)
    wrap_v = int(tex_obj.m_TextureSettings.m_WrapV)
    ws = WRAP_CLAMP_TO_EDGE if wrap_u == 1 else WRAP_REPEAT
    wt = WRAP_CLAMP_TO_EDGE if wrap_v == 1 else WRAP_REPEAT
    return img, (sx, sy), (ox, oy), ws, wt


def extract_trainer_glb(
    aa_root: str,
    trainer_id: str,
    out_glb_path: str,
    sample_fps: float = 30.0,
) -> dict[str, Any]:
    """Extract a BDSP battle trainer (e.g. pc0001_00 Lucas, pc0002_00 Dawn) to a self-contained .glb."""
    bundle_path = os.path.join(aa_root, "Characters/persons/battle", trainer_id)
    if not os.path.isfile(bundle_path):
        raise FileNotFoundError(f"Missing trainer bundle: {bundle_path}")

    env = UnityPy.load(bundle_path)

    transforms: dict[int, Any] = {}
    for obj in env.objects:
        if obj.type.name == "Transform":
            transforms[obj.path_id] = obj.read()

    roots = [pid for pid, tr in transforms.items() if tr.m_Father.path_id == 0]
    if not roots:
        raise RuntimeError(f"No root Transform found for {trainer_id}")
    root_pid = roots[0]

    color_overrides = _extract_color_variation_overrides(env)

    kept_smrs: list[tuple[Any, Any, str, int]] = []
    for obj in env.objects:
        if obj.type.name == "SkinnedMeshRenderer":
            smr = obj.read()
            go = smr.m_GameObject.read()
            if not go.m_IsActive or not smr.m_Enabled or not smr.m_Mesh.path_id:
                continue
            mesh = smr.m_Mesh.read()
            lname = (go.m_Name + " " + mesh.m_Name).lower()
            if any(tok in lname for tok in STRIP_MESH_TOKENS):
                continue
            kept_smrs.append((smr, mesh, go.m_Name, obj.path_id))

    if not kept_smrs:
        raise RuntimeError(f"No visible SkinnedMeshRenderer found for {trainer_id}")

    # Build unified bone list (<= MAX_JOINTS)
    joint_pids: list[int] = []
    joint_pid_to_idx: dict[int, int] = {}
    joint_ibms_rh: list[np.ndarray] = []

    for smr, mesh, _, _ in kept_smrs:
        for bi, bp_pptr in enumerate(smr.m_Bones):
            bpid = bp_pptr.path_id
            if bpid not in joint_pid_to_idx:
                bp = mesh.m_BindPose[bi]
                mat_u = np.array(
                    [
                        [bp.e00, bp.e01, bp.e02, bp.e03],
                        [bp.e10, bp.e11, bp.e12, bp.e13],
                        [bp.e20, bp.e21, bp.e22, bp.e23],
                        [bp.e30, bp.e31, bp.e32, bp.e33],
                    ],
                    dtype=np.float64,
                )
                joint_pid_to_idx[bpid] = len(joint_pids)
                joint_pids.append(bpid)
                joint_ibms_rh.append(lh_to_rh_mat4(mat_u))

    if len(joint_pids) > MAX_JOINTS:
        raise RuntimeError(f"{trainer_id} uses {len(joint_pids)} joints (> {MAX_JOINTS} limit)")

    keep_pids: set[int] = {root_pid}
    for jpid in joint_pids:
        cur = jpid
        while cur and cur in transforms:
            keep_pids.add(cur)
            cur = transforms[cur].m_Father.path_id

    builder = GlbBuilder()
    align_node_idx = 0
    builder.nodes.append({"name": f"{trainer_id}_root", "translation": [0.0, 0.0, 0.0], "children": []})
    builder.scene_roots.append(align_node_idx)

    pid_to_node_idx: dict[int, int] = {}

    def add_transform_tree(pid: int) -> int:
        tr = transforms[pid]
        name = tr.m_GameObject.read().m_Name
        t = lh_to_rh_vec3((tr.m_LocalPosition.x, tr.m_LocalPosition.y, tr.m_LocalPosition.z))
        q = lh_to_rh_quat((tr.m_LocalRotation.x, tr.m_LocalRotation.y, tr.m_LocalRotation.z, tr.m_LocalRotation.w))
        s = np.array([tr.m_LocalScale.x, tr.m_LocalScale.y, tr.m_LocalScale.z], dtype=np.float32)

        idx = len(builder.nodes)
        nd: dict[str, Any] = {
            "name": name,
            "translation": [float(v) for v in t],
            "rotation": [float(v) for v in q],
            "scale": [float(v) for v in s],
        }
        builder.nodes.append(nd)
        pid_to_node_idx[pid] = idx

        child_indices = []
        for ch in tr.m_Children:
            if ch.path_id in keep_pids:
                child_indices.append(add_transform_tree(ch.path_id))
        if child_indices:
            nd["children"] = child_indices
        return idx

    prefab_root_idx = add_transform_tree(root_pid)
    builder.nodes[align_node_idx]["children"].append(prefab_root_idx)

    joint_node_indices = [pid_to_node_idx[jpid] for jpid in joint_pids]
    ibm_arr = np.array([m.T.astype(np.float32) for m in joint_ibms_rh], dtype=np.float32)
    ibm_acc = builder.add_accessor(ibm_arr.reshape((-1, 16)), COMP_FLOAT, "MAT4", target=None)
    skin_idx = len(builder.skins)
    builder.skins.append(
        {
            "name": f"{trainer_id}_skin",
            "inverseBindMatrices": ibm_acc,
            "joints": joint_node_indices,
            "skeleton": prefab_root_idx,
        }
    )

    mat_cache: dict[tuple[str, int, int, int], tuple[int, tuple[float, float], tuple[float, float]]] = {}
    baked_tex_cache: dict[tuple[int, int, tuple[int, ...]], int] = {}
    decoded_textures: list[tuple[str, Image.Image]] = []
    primitives: list[dict[str, Any]] = []
    all_positions: list[np.ndarray] = []
    all_joints: list[np.ndarray] = []
    all_weights: list[np.ndarray] = []
    total_verts = 0
    total_tris = 0

    for smr, mesh, go_name, smr_pid in kept_smrs:
        mh = MeshHelper.MeshHandler(mesh)
        mh.process()

        verts_u = np.array(mh.m_Vertices, dtype=np.float32)[:, :3]
        if mh.m_Normals and len(mh.m_Normals) == len(verts_u):
            norms_u = np.array(mh.m_Normals, dtype=np.float32)[:, :3]
        else:
            norms_u = np.tile(np.array([[0.0, 1.0, 0.0]], dtype=np.float32), (len(verts_u), 1))
        if mh.m_UV0 and len(mh.m_UV0) == len(verts_u):
            uv0_u = np.array(mh.m_UV0, dtype=np.float32)[:, :2]
        else:
            uv0_u = np.zeros((len(verts_u), 2), dtype=np.float32)

        local_to_unified = [joint_pid_to_idx[bp.path_id] for bp in smr.m_Bones]
        n_v = len(verts_u)
        j_arr = np.zeros((n_v, 4), dtype=np.uint16)
        w_arr = np.zeros((n_v, 4), dtype=np.float32)
        if mh.m_BoneIndices and mh.m_BoneWeights and len(mh.m_BoneWeights) == n_v:
            raw_j = np.array(mh.m_BoneIndices, dtype=np.int32)
            raw_w = np.array(mh.m_BoneWeights, dtype=np.float32)
            for k in range(min(4, raw_j.shape[1])):
                idx_clamped = np.clip(raw_j[:, k], 0, len(local_to_unified) - 1)
                j_arr[:, k] = np.array([local_to_unified[i] for i in idx_clamped], dtype=np.uint16)
                w_arr[:, k] = np.maximum(0.0, raw_w[:, k])
            w_sum = w_arr.sum(axis=1, keepdims=True)
            bad = w_sum[:, 0] < 1e-6
            w_arr[bad] = [1.0, 0.0, 0.0, 0.0]
            j_arr[bad] = [local_to_unified[0], 0, 0, 0]
            w_sum = w_arr.sum(axis=1, keepdims=True)
            w_arr /= w_sum
        else:
            j_arr[:, 0] = local_to_unified[0]
            w_arr[:, 0] = 1.0

        pos_rh = verts_u.copy()
        pos_rh[:, 0] = -pos_rh[:, 0]
        norm_rh = norms_u.copy()
        norm_rh[:, 0] = -norm_rh[:, 0]
        nlen = np.linalg.norm(norm_rh, axis=1, keepdims=True)
        norm_rh = np.where(nlen > 1e-6, norm_rh / np.maximum(nlen, 1e-6), np.array([0.0, 1.0, 0.0], dtype=np.float32))

        tris_by_sm = mh.get_triangles()
        mat_pptrs = list(smr.m_Materials)

        for smi, sm_tris in enumerate(tris_by_sm):
            if not sm_tris:
                continue
            mp = mat_pptrs[smi] if smi < len(mat_pptrs) else None
            mat_obj = mp.read() if (mp and mp.path_id) else None
            mat_name = mat_obj.m_Name if mat_obj else f"{go_name}_mat{smi}"
            if mat_name.lower() in STRIP_MAT_NAMES:
                continue

            has_ov = any((smr_pid, smi, ch) in color_overrides for ch in (0, 1, 2))
            mat_key = (mat_name, mp.path_id if mp else 0, smr_pid if has_ov else 0, smi if has_ov else -1)
            if mat_key not in mat_cache:
                img, uv_sc, uv_off, ws, wt = _extract_trainer_material(mat_obj, smr_pid, smi, color_overrides)
                tex_idx = None
                if img is not None:
                    te = _get_dict(mat_obj.m_SavedProperties.m_TexEnvs) if mat_obj else {}
                    c0 = te.get("_MainTex") or te.get("_Col0Tex")
                    msk = te.get("_MaskTex")
                    cols = _get_dict(mat_obj.m_SavedProperties.m_Colors) if mat_obj else {}
                    c_skin = color_overrides.get((smr_pid, smi, 0), _mat_color_rgb(cols, "_SkinColor"))
                    c_prim = color_overrides.get((smr_pid, smi, 1), _mat_color_rgb(cols, "_PrimaryColor"))
                    c_sec = color_overrides.get((smr_pid, smi, 2), _mat_color_rgb(cols, "_SecondaryColor"))
                    csig = tuple(int(round(x * 1000)) for x in (*c_skin, *c_prim, *c_sec))
                    tkey = (
                        int(c0.m_Texture.path_id) if (c0 and c0.m_Texture.path_id) else 0,
                        int(msk.m_Texture.path_id) if (msk and msk.m_Texture.path_id) else 0,
                        csig,
                    )
                    if tkey not in baked_tex_cache:
                        tex_label = f"{trainer_id}:{mat_name}"
                        baked_tex_cache[tkey] = builder.add_texture_png(img, tex_label, wrap_s=ws, wrap_t=wt)
                        decoded_textures.append((tex_label, img))
                    tex_idx = baked_tex_cache[tkey]

                gltf_mat_idx = builder.add_material(
                    name=mat_name,
                    base_color_tex=tex_idx,
                    base_color_factor=[1.0, 1.0, 1.0, 1.0],
                    alpha_mode="OPAQUE",
                    double_sided=False,
                )
                mat_cache[mat_key] = (gltf_mat_idx, uv_sc, uv_off)

            gltf_mat_idx, (usx, usy), (uox, uoy) = mat_cache[mat_key]

            tri_arr = np.array(sm_tris, dtype=np.uint32)[:, [0, 2, 1]]
            uniq, inv = np.unique(tri_arr.ravel(), return_inverse=True)
            local_indices = inv.astype(np.uint32)

            sub_pos = pos_rh[uniq].astype(np.float32)
            sub_norm = norm_rh[uniq].astype(np.float32)
            sub_uv = uv0_u[uniq].copy()
            sub_uv[:, 0] = sub_uv[:, 0] * usx + uox
            sub_uv[:, 1] = 1.0 - (sub_uv[:, 1] * usy + uoy)
            sub_uv = sub_uv.astype(np.float32)
            sub_j = j_arr[uniq]
            sub_w = w_arr[uniq]

            all_positions.append(sub_pos)
            all_joints.append(sub_j)
            all_weights.append(sub_w)
            total_verts += len(sub_pos)
            total_tris += len(sm_tris)

            pos_acc = builder.add_accessor(sub_pos, COMP_FLOAT, "VEC3", TARGET_ARRAY_BUFFER, include_minmax=True)
            norm_acc = builder.add_accessor(sub_norm, COMP_FLOAT, "VEC3", TARGET_ARRAY_BUFFER)
            uv_acc = builder.add_accessor(sub_uv, COMP_FLOAT, "VEC2", TARGET_ARRAY_BUFFER)
            j_acc = builder.add_accessor(sub_j, COMP_UNSIGNED_SHORT, "VEC4", TARGET_ARRAY_BUFFER)
            w_acc = builder.add_accessor(sub_w, COMP_FLOAT, "VEC4", TARGET_ARRAY_BUFFER)

            if len(sub_pos) < 65535:
                idx_acc = builder.add_accessor(local_indices.astype(np.uint16), COMP_UNSIGNED_SHORT, "SCALAR", TARGET_ELEMENT_ARRAY_BUFFER)
            else:
                idx_acc = builder.add_accessor(local_indices, COMP_UNSIGNED_INT, "SCALAR", TARGET_ELEMENT_ARRAY_BUFFER)

            primitives.append(
                {
                    "attributes": {
                        "POSITION": pos_acc,
                        "NORMAL": norm_acc,
                        "TEXCOORD_0": uv_acc,
                        "JOINTS_0": j_acc,
                        "WEIGHTS_0": w_acc,
                    },
                    "indices": idx_acc,
                    "material": gltf_mat_idx,
                }
            )

    mesh_idx = len(builder.meshes)
    builder.meshes.append({"name": f"{trainer_id}_mesh", "primitives": primitives})
    mesh_node_idx = len(builder.nodes)
    builder.nodes.append({"name": f"{trainer_id}_skinned", "mesh": mesh_idx, "skin": skin_idx})
    builder.nodes[align_node_idx]["children"].append(mesh_node_idx)

    # Decode battle trainer AnimationClips
    clips_by_name: dict[str, Any] = {}
    for obj in env.objects:
        if obj.type.name == "AnimationClip":
            ac = obj.read()
            clips_by_name[ac.m_Name] = ac

    path_crc_map = build_transform_path_crc_map(transforms, root_pid)
    exported_clips: dict[str, dict[str, Any]] = {}
    wait_frame0_overrides: dict[int, dict[str, np.ndarray]] = {}

    for canonical_name, candidates in TRAINER_CLIP_CANDIDATES.items():
        chosen = None
        for cand in candidates:
            if cand in clips_by_name:
                chosen = clips_by_name[cand]
                break
        if chosen is None:
            continue

        clip_fps = max(sample_fps, 60.0) if canonical_name == "throw" else sample_fps
        decoded = decode_animation_clip(chosen, path_crc_map, pid_to_node_idx, sample_fps=clip_fps)
        times = decoded["times"]
        channels = decoded["channels"]

        if canonical_name == "wait":
            for (nidx, prop), vals in channels.items():
                wait_frame0_overrides.setdefault(nidx, {})[prop] = vals[0].astype(np.float64)

        time_acc = builder.add_accessor(times, COMP_FLOAT, "SCALAR", target=None, include_minmax=True)
        gltf_channels = []
        gltf_samplers = []
        animated_nodes = set()

        for (nidx, prop), vals in sorted(channels.items()):
            acc_type = "VEC4" if prop == "rotation" else "VEC3"
            val_range = float(np.max(np.ptp(vals, axis=0)))
            if val_range > 1e-4:
                animated_nodes.add(nidx)
            val_acc = builder.add_accessor(vals.astype(np.float32), COMP_FLOAT, acc_type, target=None)
            s_idx = len(gltf_samplers)
            gltf_samplers.append({"input": time_acc, "interpolation": "LINEAR", "output": val_acc})
            gltf_channels.append({"sampler": s_idx, "target": {"node": nidx, "path": prop}})

        builder.animations.append(
            {
                "name": canonical_name,
                "channels": gltf_channels,
                "samplers": gltf_samplers,
            }
        )
        exported_clips[canonical_name] = {
            "source_clip": chosen.m_Name,
            "duration_s": round(float(decoded["duration"]), 4),
            "frames": int(len(times)),
            "channel_count": len(gltf_channels),
            "moving_bones": len(animated_nodes),
        }

    # Ground feet cleanly at Y = 0 in wait frame 0
    concat_pos = np.concatenate(all_positions, axis=0)
    concat_j = np.concatenate(all_joints, axis=0)
    concat_w = np.concatenate(all_weights, axis=0)

    world_wait = _compute_world_mats_rh(builder.nodes, overrides=wait_frame0_overrides)
    skinned_wait = _skin_positions(concat_pos, concat_j, concat_w, joint_node_indices, joint_ibms_rh, world_wait)

    min_y = float(skinned_wait[:, 1].min())
    if abs(min_y) > 1e-4:
        builder.nodes[align_node_idx]["translation"] = [0.0, -min_y, 0.0]
        skinned_wait[:, 1] -= min_y

    bbox_min = [round(float(x), 4) for x in skinned_wait.min(axis=0)]
    bbox_max = [round(float(x), 4) for x in skinned_wait.max(axis=0)]
    height_m = round(bbox_max[1] - bbox_min[1], 4)

    os.makedirs(os.path.dirname(os.path.abspath(out_glb_path)), exist_ok=True)
    file_bytes = builder.write(out_glb_path)

    return {
        "id": trainer_id,
        "file": os.path.relpath(out_glb_path, os.path.dirname(os.path.dirname(out_glb_path))),
        "size_bytes": file_bytes,
        "vertices": total_verts,
        "triangles": total_tris,
        "bones": len(joint_pids),
        "materials": len(builder.materials),
        "textures": len(builder.textures),
        "bbox_min": bbox_min,
        "bbox_max": bbox_max,
        "height_m": height_m,
        "ground_offset_y": round(-min_y, 4),
        "clips": exported_clips,
        "decoded_textures": decoded_textures,
    }


def extract_pokeball_glb(
    aa_root: str,
    out_glb_path: str,
    ball_id: str = "ob0204_00",
    target_radius: float = 0.10,
) -> dict[str, Any]:
    """Extract the 3D BDSP Poke Ball (ob0204_00) as a clean centered rigid .glb."""
    bundle_path = os.path.join(aa_root, "Characters/objects", ball_id)
    if not os.path.isfile(bundle_path):
        raise FileNotFoundError(f"Missing Poke Ball bundle: {bundle_path}")

    env = UnityPy.load(bundle_path)
    transforms = {obj.path_id: obj.read() for obj in env.objects if obj.type.name == "Transform"}
    roots = [pid for pid, tr in transforms.items() if tr.m_Father.path_id == 0]
    root_pid = roots[0] if roots else None

    # Compute rest-pose RH world matrices for all transforms so upper & lower shells sit cleanly closed
    pid_to_world: dict[int, np.ndarray] = {}

    def get_world_rh(pid: int) -> np.ndarray:
        if pid in pid_to_world:
            return pid_to_world[pid]
        tr = transforms[pid]
        t = lh_to_rh_vec3((tr.m_LocalPosition.x, tr.m_LocalPosition.y, tr.m_LocalPosition.z))
        q = lh_to_rh_quat((tr.m_LocalRotation.x, tr.m_LocalRotation.y, tr.m_LocalRotation.z, tr.m_LocalRotation.w))
        s = np.array([tr.m_LocalScale.x, tr.m_LocalScale.y, tr.m_LocalScale.z], dtype=np.float64)
        local = mat4_from_trs_rh(t, q, s)
        fpid = tr.m_Father.path_id
        w = (get_world_rh(fpid) @ local) if (fpid and fpid in transforms) else local
        pid_to_world[pid] = w
        return w

    parts: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, Any]] = []
    for obj in env.objects:
        if obj.type.name == "SkinnedMeshRenderer":
            smr = obj.read()
            go = smr.m_GameObject.read()
            if not go.m_IsActive or not smr.m_Enabled or not smr.m_Mesh.path_id:
                continue
            mesh = smr.m_Mesh.read()
            mh = MeshHelper.MeshHandler(mesh)
            mh.process()

            verts_u = np.array(mh.m_Vertices, dtype=np.float32)[:, :3]
            norms_u = (
                np.array(mh.m_Normals, dtype=np.float32)[:, :3]
                if (mh.m_Normals and len(mh.m_Normals) == len(verts_u))
                else np.tile(np.array([[0.0, 1.0, 0.0]], dtype=np.float32), (len(verts_u), 1))
            )
            uv0_u = (
                np.array(mh.m_UV0, dtype=np.float32)[:, :2]
                if (mh.m_UV0 and len(mh.m_UV0) == len(verts_u))
                else np.zeros((len(verts_u), 2), dtype=np.float32)
            )

            pos_rh = verts_u.astype(np.float64).copy()
            pos_rh[:, 0] = -pos_rh[:, 0]
            norm_rh = norms_u.astype(np.float64).copy()
            norm_rh[:, 0] = -norm_rh[:, 0]

            # Evaluate rest-pose skinning so upper & lower halves align precisely
            if smr.m_Bones and mh.m_BoneIndices and mh.m_BoneWeights and len(mh.m_BoneWeights) == len(verts_u):
                skin_mats = []
                for bi, bp_pptr in enumerate(smr.m_Bones):
                    bp = mesh.m_BindPose[bi]
                    mat_u = np.array(
                        [
                            [bp.e00, bp.e01, bp.e02, bp.e03],
                            [bp.e10, bp.e11, bp.e12, bp.e13],
                            [bp.e20, bp.e21, bp.e22, bp.e23],
                            [bp.e30, bp.e31, bp.e32, bp.e33],
                        ],
                        dtype=np.float64,
                    )
                    ibm_rh = lh_to_rh_mat4(mat_u)
                    wmat = get_world_rh(bp_pptr.path_id) if bp_pptr.path_id in transforms else np.eye(4)
                    skin_mats.append(wmat @ ibm_rh)
                skin_mats_arr = np.array(skin_mats, dtype=np.float64)
                raw_j = np.clip(np.array(mh.m_BoneIndices, dtype=np.int32), 0, len(skin_mats) - 1)
                raw_w = np.maximum(0.0, np.array(mh.m_BoneWeights, dtype=np.float64))
                wsum = raw_w.sum(axis=1, keepdims=True)
                raw_w = np.where(wsum > 1e-6, raw_w / np.maximum(wsum, 1e-6), np.array([1.0, 0.0, 0.0, 0.0]))
                pos_h = np.concatenate([pos_rh, np.ones((len(pos_rh), 1))], axis=1)
                spos = np.zeros_like(pos_rh)
                snorm = np.zeros_like(norm_rh)
                for k in range(min(4, raw_j.shape[1])):
                    wk = raw_w[:, k : k + 1]
                    mk = skin_mats_arr[raw_j[:, k]]
                    spos += wk * np.einsum("nij,nj->ni", mk[:, :3, :], pos_h)
                    snorm += wk * np.einsum("nij,nj->ni", mk[:, :3, :3], norm_rh)
                pos_rh = spos
                norm_rh = snorm

            nlen = np.linalg.norm(norm_rh, axis=1, keepdims=True)
            norm_rh = np.where(nlen > 1e-6, norm_rh / np.maximum(nlen, 1e-6), np.array([0.0, 1.0, 0.0]))

            mats = [mp.read() if mp.path_id else None for mp in smr.m_Materials]
            for smi, sm_tris in enumerate(mh.get_triangles()):
                if not sm_tris:
                    continue
                tri_arr = np.array(sm_tris, dtype=np.uint32)[:, [0, 2, 1]]
                mat_obj = mats[smi] if smi < len(mats) else None
                parts.append((pos_rh, norm_rh, uv0_u, tri_arr, mat_obj))

    if not parts:
        raise RuntimeError(f"No meshes found in {bundle_path}")

    # Center at (0,0,0) and scale uniformly to target_radius
    all_pts = np.concatenate([p[0] for p in parts], axis=0)
    center = 0.5 * (all_pts.min(axis=0) + all_pts.max(axis=0))
    native_radius = float(np.linalg.norm(all_pts - center[None, :], axis=1).max())
    scale_f = (target_radius / native_radius) if native_radius > 1e-5 else 1.0

    builder = GlbBuilder()
    mat_cache: dict[str, tuple[int, tuple[float, float], tuple[float, float]]] = {}
    decoded_textures: list[tuple[str, Image.Image]] = []
    primitives = []
    total_verts = 0
    total_tris = 0
    final_pts = []

    for pi, (pos_rh, norm_rh, uv0_u, tri_arr, mat_obj) in enumerate(parts):
        mname = mat_obj.m_Name if mat_obj else f"ball_mat{pi}"
        if mname not in mat_cache:
            img, uv_sc, uv_off, ws, wt = _extract_trainer_material(mat_obj)
            tex_idx = None
            if img is not None:
                tex_idx = builder.add_texture_png(img, f"{ball_id}_{mname}", wrap_s=ws, wrap_t=wt)
                decoded_textures.append((f"{ball_id}:{mname}", img))
            gltf_mat_idx = builder.add_material(
                name=mname,
                base_color_tex=tex_idx,
                base_color_factor=[1.0, 1.0, 1.0, 1.0],
                alpha_mode="OPAQUE",
                double_sided=False,
            )
            mat_cache[mname] = (gltf_mat_idx, uv_sc, uv_off)

        gltf_mat_idx, (usx, usy), (uox, uoy) = mat_cache[mname]
        uniq, inv = np.unique(tri_arr.ravel(), return_inverse=True)
        local_indices = inv.astype(np.uint32)

        sub_pos = ((pos_rh[uniq] - center[None, :]) * scale_f).astype(np.float32)
        sub_norm = norm_rh[uniq].astype(np.float32)
        sub_uv = uv0_u[uniq].copy()
        sub_uv[:, 0] = sub_uv[:, 0] * usx + uox
        sub_uv[:, 1] = 1.0 - (sub_uv[:, 1] * usy + uoy)
        sub_uv = sub_uv.astype(np.float32)

        final_pts.append(sub_pos)
        total_verts += len(sub_pos)
        total_tris += len(tri_arr)

        pos_acc = builder.add_accessor(sub_pos, COMP_FLOAT, "VEC3", TARGET_ARRAY_BUFFER, include_minmax=True)
        norm_acc = builder.add_accessor(sub_norm, COMP_FLOAT, "VEC3", TARGET_ARRAY_BUFFER)
        uv_acc = builder.add_accessor(sub_uv, COMP_FLOAT, "VEC2", TARGET_ARRAY_BUFFER)
        idx_acc = builder.add_accessor(local_indices.astype(np.uint16), COMP_UNSIGNED_SHORT, "SCALAR", TARGET_ELEMENT_ARRAY_BUFFER)
        primitives.append(
            {
                "attributes": {"POSITION": pos_acc, "NORMAL": norm_acc, "TEXCOORD_0": uv_acc},
                "indices": idx_acc,
                "material": gltf_mat_idx,
            }
        )

    mesh_idx = len(builder.meshes)
    builder.meshes.append({"name": "pokeball_mesh", "primitives": primitives})
    node_idx = len(builder.nodes)
    builder.nodes.append({"name": "pokeball_root", "mesh": mesh_idx})
    builder.scene_roots.append(node_idx)

    os.makedirs(os.path.dirname(os.path.abspath(out_glb_path)), exist_ok=True)
    file_bytes = builder.write(out_glb_path)

    cat = np.concatenate(final_pts, axis=0)
    bbox_min = [round(float(x), 4) for x in cat.min(axis=0)]
    bbox_max = [round(float(x), 4) for x in cat.max(axis=0)]
    radius = round(float(np.linalg.norm(cat, axis=1).max()), 4)

    return {
        "id": ball_id,
        "file": os.path.relpath(out_glb_path, os.path.dirname(os.path.dirname(out_glb_path))),
        "size_bytes": file_bytes,
        "vertices": total_verts,
        "triangles": total_tris,
        "materials": len(builder.materials),
        "textures": len(builder.textures),
        "bbox_min": bbox_min,
        "bbox_max": bbox_max,
        "radius_m": radius,
        "native_radius_m": round(native_radius, 4),
        "decoded_textures": decoded_textures,
    }


def _render_trainer_preview(glb_path: str, out_png: str, title: str) -> None:
    from verify_render import eval_glb_pose, load_glb, render_preview

    gltf, bin_data = load_glb(glb_path)
    panels = [
        ("Front wait t=0", "wait", 0.0, (0.0, 0.95, 2.7), (0.0, 0.78, 0.0)),
        ("3/4 Back wait t=0", "wait", 0.0, (-1.6, 1.15, -2.0), (0.0, 0.78, 0.0)),
        ("Throw t=0.25s", "throw", 0.25, (1.8, 1.05, 1.9), (0.0, 0.78, 0.0)),
        ("Throw t=0.55s", "throw", 0.55, (1.8, 1.05, 1.9), (0.0, 0.78, 0.0)),
    ]
    pw, ph = 360, 360
    sheet = Image.new("RGB", (pw * 2 + 12, ph * 2 + 56), (18, 22, 34))
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 6), title, fill=(240, 240, 250))
    for i, (label, clip, t_sec, eye, tgt) in enumerate(panels):
        prims = eval_glb_pose(gltf, bin_data, clip_name=clip, t_sec=t_sec)
        im = render_preview(prims, eye=eye, target=tgt, fov_deg=36.0, width=pw, height=ph, bg_rgb=(36, 52, 82))
        r, c = divmod(i, 2)
        x = 4 + c * (pw + 4)
        y = 28 + r * (ph + 24)
        sheet.paste(im, (x, y))
        draw.text((x + 6, y + ph + 4), label, fill=(225, 230, 240))
    sheet.save(out_png)


def _render_pokeball_preview(glb_path: str, out_png: str) -> None:
    from verify_render import eval_glb_pose, load_glb, render_preview

    gltf, bin_data = load_glb(glb_path)
    prims = eval_glb_pose(gltf, bin_data)
    views = [
        ("Front (+Z)", (0.0, 0.04, 0.42)),
        ("3/4 Top-Right", (0.28, 0.20, 0.30)),
        ("Back (-Z)", (0.0, 0.04, -0.42)),
    ]
    pw, ph = 320, 320
    sheet = Image.new("RGB", (pw * 3 + 16, ph + 48), (18, 22, 34))
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 6), "3D Poke Ball (ob0204_00)", fill=(240, 240, 250))
    for i, (label, eye) in enumerate(views):
        im = render_preview(prims, eye=eye, target=(0.0, 0.0, 0.0), fov_deg=36.0, width=pw, height=ph, bg_rgb=(36, 52, 82))
        x = 4 + i * (pw + 4)
        y = 26
        sheet.paste(im, (x, y))
        draw.text((x + 6, y + ph + 4), label, fill=(225, 230, 240))
    sheet.save(out_png)


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract BDSP 3D battle trainers (Lucas/Dawn) and Poke Ball to .glb")
    ap.add_argument(
        "--romfs",
        default=os.path.expanduser("~/dz-team/bdsp3d-scratch/romfs/Data/StreamingAssets/AssetAssistant"),
        help="Path to unpacked BDSP AssetAssistant directory",
    )
    ap.add_argument(
        "--out-dir",
        default=os.path.expanduser("~/dz-team/bdsp3d-assets/trainers"),
        help="Output directory for untracked .glb files",
    )
    ap.add_argument(
        "--preview-dir",
        default="",
        help="Optional directory to save verification renders & texture contact sheet",
    )
    ap.add_argument("--fps", type=float, default=30.0, help="Animation sampling FPS (default: 30)")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    all_textures: list[tuple[str, Image.Image]] = []
    summary: dict[str, Any] = {}

    for tid, label in [("pc0001_00", "Lucas (pc0001_00)"), ("pc0002_00", "Dawn (pc0002_00)")]:
        out_path = os.path.join(args.out_dir, f"{tid}.glb")
        info = extract_trainer_glb(args.romfs, tid, out_path, sample_fps=args.fps)
        all_textures.extend(info.pop("decoded_textures"))
        summary[tid] = info
        print(f"[ok] {label} -> {out_path} ({info['size_bytes']//1024} KB, {info['vertices']}v, {info['triangles']}t, {info['bones']} bones, h={info['height_m']}m, clips={list(info['clips'].keys())})")

    ball_out = os.path.join(args.out_dir, "pokeball.glb")
    ball_info = extract_pokeball_glb(args.romfs, ball_out)
    all_textures.extend(ball_info.pop("decoded_textures"))
    summary["pokeball"] = ball_info
    print(f"[ok] Poke Ball (ob0204_00) -> {ball_out} ({ball_info['size_bytes']//1024} KB, {ball_info['vertices']}v, {ball_info['triangles']}t, r={ball_info['radius_m']}m)")

    if args.preview_dir:
        from verify_render import make_texture_contact_sheet

        os.makedirs(args.preview_dir, exist_ok=True)
        make_texture_contact_sheet(all_textures, os.path.join(args.preview_dir, "textures_check.png"))
        _render_trainer_preview(
            os.path.join(args.out_dir, "pc0001_00.glb"),
            os.path.join(args.preview_dir, "pc0001_00_preview.png"),
            "Lucas (pc0001_00) - BDSP Extracted GLB",
        )
        _render_trainer_preview(
            os.path.join(args.out_dir, "pc0002_00.glb"),
            os.path.join(args.preview_dir, "pc0002_00_preview.png"),
            "Dawn (pc0002_00) - BDSP Extracted GLB",
        )
        _render_pokeball_preview(
            ball_out,
            os.path.join(args.preview_dir, "pokeball_preview.png"),
        )
        with open(os.path.join(args.preview_dir, "extract_summary.json"), "w") as f:
            json.dump(summary, f, indent=2)
        print(f"[ok] Previews saved to {args.preview_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

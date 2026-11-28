"""Extract a BDSP Pokemon (mesh, decoded RGBA textures, skeleton, skin, animations) to glTF 2.0 (.glb)."""

from __future__ import annotations

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

# Priority order of BDSP animation clip suffixes for each canonical battle clip name
CLIP_CANDIDATES: dict[str, list[str]] = {
    "idle": ["ba10_waitA01", "ba10_waitB01", "kw01_wait01", "fi01_wait01"],
    "attack_phys": ["ba20_buturi01", "ba20_buturi02", "ba20_buturi03"],
    "attack_spec": ["ba21_tokusyu01", "ba21_tokusyu02", "ba20_buturi01"],
    "hit": ["ba30_damageS01", "ba30_damage01", "ba30_damageL01"],
    "faint": ["ba41_down01", "ba31_down01", "ba40_down01"],
    "cry": ["ba02_roar01", "ba01_landA01", "ba01_land01", "kw32_happyB01"],
}

STRIP_MESH_TOKENS = ("firemask", "smokemask", "shadow", "collider", "proxy", "debug", "hitcheck")


def _get_dict(prop: Any) -> dict[str, Any]:
    if isinstance(prop, dict):
        return prop
    return dict(prop)


def _mirror_expand_u(img: Image.Image) -> Image.Image:
    """Expand a wrapU=Mirror texture horizontally [img | flipX(img)] for universal REPEAT sampling."""
    rgba = img.convert("RGBA")
    w, h = rgba.size
    out = Image.new("RGBA", (w * 2, h))
    out.paste(rgba, (0, 0))
    out.paste(rgba.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (w, 0))
    return out


def _bake_eye_with_iris(eye_img: Image.Image, iris_img: Image.Image) -> Image.Image:
    """Composite BDSP _L1Col0Tex (iris) behind transparent cutouts in _Col0Tex (eye sheet)."""
    eye = eye_img.convert("RGBA")
    ew, eh = eye.size
    tile_w = ew // 2
    tile_h = eh // 4
    iris_r = iris_img.convert("RGBA").resize((tile_w, tile_h), Image.Resampling.BILINEAR)
    iris_l = iris_r.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    bg = Image.new("RGBA", (ew, eh), (0, 0, 0, 255))
    for row in range(4):
        bg.paste(iris_r, (0, row * tile_h))
        bg.paste(iris_l, (tile_w, row * tile_h))

    comp = Image.alpha_composite(bg, eye)
    arr = np.array(comp)
    arr[:, :, 3] = 255
    return Image.fromarray(arr, mode="RGBA")


def _pack_fire_core_channels(mat: Any) -> tuple[Image.Image, list[float], list[float]]:
    """Pack real BDSP FireCore textures into a 4-channel shader map + (_BaseColor, _LayerColor).

    Channel layout consumed by battle3d_skinned_frag (flags.y == 2):
      R = _Blend0Tex (scrolling wavy flame ribbon noise)
      G = _Blend1Tex (scrolling fast flame streaks)
      B = _LerpTex luminance (base/inner yellow core -> outer orange-red tip gradient)
      A = _LerpTex alpha (flame silhouette envelope opacity)
    """
    cols = _get_dict(mat.m_SavedProperties.m_Colors)
    base_c = cols.get("_BaseColor")
    layer_c = cols.get("_LayerColor")
    outer_rgb = [float(base_c.r), float(base_c.g), float(base_c.b)] if base_c else [1.0, 0.20, 0.10]
    inner_rgb = [float(layer_c.r), float(layer_c.g), float(layer_c.b)] if layer_c else [0.94, 0.81, 0.0]

    tex_envs = _get_dict(mat.m_SavedProperties.m_TexEnvs)
    sz = 128

    def _read_l(key: str, default_arr: np.ndarray) -> np.ndarray:
        te = tex_envs.get(key)
        if te and te.m_Texture.path_id:
            im = te.m_Texture.read().image.convert("L").resize((sz, sz), Image.Resampling.BILINEAR)
            return np.array(im, dtype=np.uint8)
        return default_arr

    yy = np.linspace(0.0, 255.0, sz, dtype=np.float32)[:, None]
    default_grad = np.broadcast_to(yy, (sz, sz)).astype(np.uint8)
    r_ch = _read_l("_Blend0Tex", np.full((sz, sz), 140, dtype=np.uint8))
    g_ch = _read_l("_Blend1Tex", np.full((sz, sz), 90, dtype=np.uint8))

    b_ch = default_grad.copy()
    a_ch = np.full((sz, sz), 255, dtype=np.uint8)
    lt = tex_envs.get("_LerpTex")
    if lt and lt.m_Texture.path_id:
        lt_im = lt.m_Texture.read().image.convert("RGBA").resize((sz, sz), Image.Resampling.BILINEAR)
        lt_arr = np.array(lt_im, dtype=np.uint8)
        b_ch = lt_arr[:, :, 0]
        a_ch = lt_arr[:, :, 3]

    rgba = np.stack([r_ch, g_ch, b_ch, a_ch], axis=2)
    return Image.fromarray(rgba, mode="RGBA"), outer_rgb, inner_rgb


def _extract_material_diffuse(mat: Any) -> tuple[Image.Image | None, tuple[float, float], tuple[float, float], bool, list[float] | None]:
    """Return (diffuse_rgba_img, uv_scale, uv_offset, mirror_baked, emissive_factor)."""
    mname = mat.m_Name
    tex_envs = _get_dict(mat.m_SavedProperties.m_TexEnvs)

    if "firecore" in mname.lower():
        img, _outer, inner = _pack_fire_core_channels(mat)
        return img, (1.0, 1.0), (0.0, 0.0), False, inner

    c0 = tex_envs.get("_Col0Tex") or tex_envs.get("_MainTex")
    if not c0 or not c0.m_Texture.path_id:
        return None, (1.0, 1.0), (0.0, 0.0), False, None

    tex_obj = c0.m_Texture.read()
    img = tex_obj.image.convert("RGBA")
    sx, sy = float(c0.m_Scale.x), float(c0.m_Scale.y)
    ox, oy = float(c0.m_Offset.x), float(c0.m_Offset.y)
    wrap_u = int(tex_obj.m_TextureSettings.m_WrapU)

    # Composite iris layer behind eye cutout if present
    l1 = tex_envs.get("_L1Col0Tex")
    if l1 and l1.m_Texture.path_id and "eye" in mname.lower():
        iris_tex = l1.m_Texture.read()
        img = _bake_eye_with_iris(img, iris_tex.image)

    # BDSP Eye sheets use a 2-column expression atlas with _ColorBaseU = -0.5 so both eyes
    # mirror across column 0 (neutral expression) rather than sampling column 1 (angry/alt).
    fl = _get_dict(mat.m_SavedProperties.m_Floats)
    color_base_u = float(fl.get("_ColorBaseU", 0.0))
    if abs(color_base_u + 0.5) < 1e-3 and wrap_u == 2 and abs(abs(sx) - 2.0) < 1e-3:
        w, h = img.size
        col0 = img.crop((0, 0, w // 2, h))
        col0_flip = col0.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        sym = Image.new("RGBA", (w, h))
        sym.paste(col0, (0, 0))
        sym.paste(col0_flip, (w // 2, 0))
        img = sym

    # Bake Unity Mirror U wrap + scale.x==2 into a 2x-wide image so standard REPEAT works identically
    mirror_baked = False
    if wrap_u == 2 and abs(abs(sx) - 2.0) < 1e-3:
        img = _mirror_expand_u(img)
        sx = 1.0 if sx > 0 else -1.0
        mirror_baked = True

    return img, (sx, sy), (ox, oy), mirror_baked, None


def _compute_world_mats_rh(
    nodes: list[dict[str, Any]],
    overrides: dict[int, dict[str, np.ndarray]] | None = None,
) -> list[np.ndarray]:
    n = len(nodes)
    parent = [-1] * n
    for i, nd in enumerate(nodes):
        for ch in nd.get("children", []):
            parent[ch] = i

    local = []
    for i, nd in enumerate(nodes):
        ov = overrides.get(i, {}) if overrides else {}
        t = ov.get("translation", np.array(nd.get("translation", [0.0, 0.0, 0.0]), dtype=np.float64))
        q = ov.get("rotation", np.array(nd.get("rotation", [0.0, 0.0, 0.0, 1.0]), dtype=np.float64))
        s = ov.get("scale", np.array(nd.get("scale", [1.0, 1.0, 1.0]), dtype=np.float64))
        local.append(mat4_from_trs_rh(t, q, s))

    world: list[np.ndarray | None] = [None] * n

    def get_w(i: int) -> np.ndarray:
        if world[i] is not None:
            return world[i]  # type: ignore[return-value]
        if parent[i] < 0:
            world[i] = local[i]
        else:
            world[i] = get_w(parent[i]) @ local[i]
        return world[i]  # type: ignore[return-value]

    for i in range(n):
        get_w(i)
    return world  # type: ignore[return-value]


def _skin_positions(
    positions: np.ndarray,
    joints: np.ndarray,
    weights: np.ndarray,
    joint_nodes: list[int],
    ibms: list[np.ndarray],
    world_mats: list[np.ndarray],
) -> np.ndarray:
    skin_mats = np.array([world_mats[jn] @ ibm for jn, ibm in zip(joint_nodes, ibms)], dtype=np.float64)
    n = positions.shape[0]
    pos_h = np.concatenate([positions.astype(np.float64), np.ones((n, 1), dtype=np.float64)], axis=1)
    out = np.zeros((n, 3), dtype=np.float64)
    for k in range(4):
        w = weights[:, k : k + 1].astype(np.float64)
        j = joints[:, k]
        # (n, 4, 4) @ (n, 4, 1) -> (n, 3)
        m = skin_mats[j]
        p = np.einsum("nij,nj->ni", m[:, :3, :], pos_h)
        out += w * p
    return out


# In BDSP AssetAssistant, these 12 multi-form species store their battle forms starting at 11
# (e.g. pm0487_11 = Giratina Altered = Platinum form 0; pm0487_12 = Giratina Origin = Platinum form 1).
MULTI_FORM_BASE11_SPECIES = frozenset({201, 351, 386, 412, 413, 421, 422, 423, 479, 487, 492, 493})


_MANIFEST_DEPS_CACHE: dict[str, dict[str, list[str]]] = {}


def _get_pokemon_manifest_deps(aa_root: str) -> dict[str, list[str]]:
    """Load Pokemon Database AssetBundleManifest dependencies once per process."""
    cached = _MANIFEST_DEPS_CACHE.get(aa_root)
    if cached is not None:
        return cached
    deps_map: dict[str, list[str]] = {}
    mf_path = os.path.join(aa_root, "Pokemon Database", "Pokemon Database")
    if os.path.isfile(mf_path):
        mf_env = UnityPy.load(mf_path)
        for obj in mf_env.objects:
            if obj.type.name == "AssetBundleManifest":
                m = obj.read()
                names = dict(m.AssetBundleNames)
                infos = dict(m.AssetBundleInfos)
                for bid, bname in names.items():
                    info = infos.get(bid)
                    if info is not None:
                        deps_map[bname] = [names[d] for d in info.AssetBundleDependencies if d in names]
                break
    _MANIFEST_DEPS_CACHE[aa_root] = deps_map
    return deps_map


def _resolve_manifest_bundle_path(aa_root: str, dep_name: str) -> str | None:
    if dep_name == "shaders":
        p = os.path.join(aa_root, "Dpr", "shaders")
        return p if os.path.isfile(p) else None
    if dep_name.startswith("pokemons/field/animations/"):
        return None
    p = os.path.join(aa_root, "Pokemon Database", dep_name)
    return p if os.path.isfile(p) else None


def discover_species_forms(aa_root: str, species: int) -> list[int]:
    """Return sorted Platinum formNum values (0, 1, ...) available in BDSP for a species."""
    battle_dir = os.path.join(aa_root, "Pokemon Database/pokemons/battle")
    if species in MULTI_FORM_BASE11_SPECIES:
        forms = []
        prefix = f"pm{species:04d}_"
        for name in os.listdir(battle_dir):
            if name.startswith(prefix) and name.endswith("_00") and len(name) == 12:
                bdsp_f = int(name[7:9])
                if bdsp_f >= 11:
                    forms.append(bdsp_f - 11)
        return sorted(forms)
    if os.path.isfile(os.path.join(battle_dir, f"pm{species:04d}_00_00")):
        return [0]
    return []


def extract_pokemon_glb(
    aa_root: str,
    species: int,
    form: int,
    shiny: bool,
    out_glb_path: str,
    sample_fps: float = 30.0,
) -> dict[str, Any]:
    """Extract one Pokemon species/form (Platinum formNum) from BDSP AssetAssistant into a self-contained .glb."""
    bdsp_form = (11 + form) if species in MULTI_FORM_BASE11_SPECIES else form
    base_id = f"pm{species:04d}_{bdsp_form:02d}"
    var_id = f"{base_id}_{1 if shiny else 0:02d}"
    default_base_id = f"pm{species:04d}_{11 if species in MULTI_FORM_BASE11_SPECIES else 0:02d}"

    common_dir = os.path.join(aa_root, "Pokemon Database/pokemons/common")
    battle_dir = os.path.join(aa_root, "Pokemon Database/pokemons/battle")
    anim_dir = os.path.join(battle_dir, "animations")

    bundle_paths = [
        os.path.join(common_dir, base_id),
        os.path.join(common_dir, var_id),
        os.path.join(battle_dir, var_id),
    ]
    # Animation bundle: exact form first, then default form fallback
    anim_exact = os.path.join(anim_dir, base_id)
    anim_default = os.path.join(anim_dir, default_base_id)
    if os.path.isfile(anim_exact):
        bundle_paths.append(anim_exact)
    elif os.path.isfile(anim_default):
        bundle_paths.append(anim_default)
    # Also include default common if exact form common is absent
    if not os.path.isfile(bundle_paths[0]) and os.path.isfile(os.path.join(common_dir, default_base_id)):
        bundle_paths[0] = os.path.join(common_dir, default_base_id)

    # Pull every declared AssetBundleManifest dependency (Dpr/shaders, shared base-form
    # common bundles like Kangaskhan baby, Unown A materials, Castform/Burmy/Wormadam mats).
    deps_map = _get_pokemon_manifest_deps(aa_root)
    for dep in deps_map.get(f"pokemons/battle/{var_id}", []):
        rp = _resolve_manifest_bundle_path(aa_root, dep)
        if rp is not None:
            bundle_paths.append(rp)
    shaders_bundle = os.path.join(aa_root, "Dpr", "shaders")
    if os.path.isfile(shaders_bundle):
        bundle_paths.append(shaders_bundle)

    existing = []
    for bp in bundle_paths:
        if os.path.isfile(bp) and bp not in existing:
            existing.append(bp)
    if not os.path.isfile(os.path.join(battle_dir, var_id)):
        raise FileNotFoundError(f"Missing battle bundle for {var_id}; found: {existing}")

    env = UnityPy.load(*existing)

    # Collect Transforms & root
    transforms: dict[int, Any] = {}
    for obj in env.objects:
        if obj.type.name == "Transform":
            transforms[obj.path_id] = obj.read()

    roots = [pid for pid, tr in transforms.items() if tr.m_Father.path_id == 0]
    if not roots:
        raise RuntimeError(f"No root Transform found for {var_id}")
    root_pid = roots[0]

    # Collect kept SkinnedMeshRenderers
    kept_smrs: list[tuple[Any, Any, str]] = []
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
            kept_smrs.append((smr, mesh, go.m_Name))

    if not kept_smrs:
        raise RuntimeError(f"No visible SkinnedMeshRenderer found for {var_id}")

    # Build unified bone list (<= 128 joints) from all kept SMRs
    joint_pids: list[int] = []
    joint_pid_to_idx: dict[int, int] = {}
    joint_ibms_rh: list[np.ndarray] = []

    for smr, mesh, _ in kept_smrs:
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

    if len(joint_pids) > 192:
        raise RuntimeError(f"{var_id} uses {len(joint_pids)} joints (> 192 limit)")

    # Keep all ancestor transforms of joints + root + Origin (skip CusAnimMat_* & stripped mesh GOs)
    keep_pids: set[int] = {root_pid}
    for jpid in joint_pids:
        cur = jpid
        while cur and cur in transforms:
            keep_pids.add(cur)
            cur = transforms[cur].m_Father.path_id

    builder = GlbBuilder()
    # Node 0 = alignment wrapper (root_align), Node 1 = prefab root
    align_node_idx = 0
    builder.nodes.append({"name": f"{var_id}_root", "translation": [0.0, 0.0, 0.0], "children": []})
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

    # Create unified skin
    joint_node_indices = [pid_to_node_idx[jpid] for jpid in joint_pids]
    ibm_arr = np.array([m.T.astype(np.float32) for m in joint_ibms_rh], dtype=np.float32)  # column-major per glTF
    ibm_acc = builder.add_accessor(ibm_arr.reshape((-1, 16)), COMP_FLOAT, "MAT4", target=None)
    skin_idx = len(builder.skins)
    builder.skins.append(
        {
            "name": f"{var_id}_skin",
            "inverseBindMatrices": ibm_acc,
            "joints": joint_node_indices,
            "skeleton": prefab_root_idx,
        }
    )

    # Build materials & mesh primitives (one unified mesh with 1 primitive per submesh)
    mat_cache: dict[str, tuple[int, tuple[float, float], tuple[float, float]]] = {}
    decoded_textures: list[tuple[str, Image.Image]] = []
    primitives: list[dict[str, Any]] = []
    all_positions: list[np.ndarray] = []
    all_joints: list[np.ndarray] = []
    all_weights: list[np.ndarray] = []
    total_verts = 0
    total_tris = 0

    for smr, mesh, go_name in kept_smrs:
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

        # Skin weights & joint indices remapped to unified skin
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
            bad = (w_sum[:, 0] < 1e-6)
            w_arr[bad] = [1.0, 0.0, 0.0, 0.0]
            j_arr[bad] = [local_to_unified[0], 0, 0, 0]
            w_sum = w_arr.sum(axis=1, keepdims=True)
            w_arr /= w_sum
        else:
            j_arr[:, 0] = local_to_unified[0]
            w_arr[:, 0] = 1.0

        # Unity LH -> glTF RH positions & normals
        pos_rh = verts_u.copy()
        pos_rh[:, 0] = -pos_rh[:, 0]
        norm_rh = norms_u.copy()
        norm_rh[:, 0] = -norm_rh[:, 0]
        nlen = np.linalg.norm(norm_rh, axis=1, keepdims=True)
        norm_rh = np.where(nlen > 1e-6, norm_rh / np.maximum(nlen, 1e-6), np.array([0.0, 1.0, 0.0], dtype=np.float32))

        tris_by_sm = mh.get_triangles()
        mats = [mp.read() if mp.path_id else None for mp in smr.m_Materials]

        for smi, sm_tris in enumerate(tris_by_sm):
            if not sm_tris:
                continue
            mat_obj = mats[smi] if smi < len(mats) else None
            mat_name = mat_obj.m_Name if mat_obj else f"{go_name}_mat{smi}"
            lmat = mat_name.lower()
            if "firemask" in lmat or "smokemask" in lmat:
                continue

            if mat_name not in mat_cache:
                img, uv_sc, uv_off, _, emissive = (
                    _extract_material_diffuse(mat_obj) if mat_obj else (None, (1.0, 1.0), (0.0, 0.0), False, None)
                )
                if "smokecore" in lmat and img is None:
                    mat_cache[mat_name] = (-1, uv_sc, uv_off)
                else:
                    tex_idx = None
                    if img is not None:
                        tex_idx = builder.add_texture_png(img, f"{mat_name}_diffuse", wrap_s=WRAP_REPEAT, wrap_t=WRAP_REPEAT)
                        decoded_textures.append((mat_name, img))
                    alpha_mode = "OPAQUE"
                    base_factor = [1.0, 1.0, 1.0, 1.0]
                    if "firecore" in lmat and mat_obj is not None:
                        _, outer_rgb, _ = _pack_fire_core_channels(mat_obj)
                        alpha_mode = "BLEND"
                        alpha_v = 0.45 if species == 479 else 1.0
                        base_factor = [outer_rgb[0], outer_rgb[1], outer_rgb[2], alpha_v]
                    gltf_mat_idx = builder.add_material(
                        name=mat_name,
                        base_color_tex=tex_idx,
                        base_color_factor=base_factor,
                        alpha_mode=alpha_mode,
                        double_sided=("firecore" in lmat),
                        emissive_factor=emissive,
                    )
                    mat_cache[mat_name] = (gltf_mat_idx, uv_sc, uv_off)

            gltf_mat_idx, (usx, usy), (uox, uoy) = mat_cache[mat_name]
            if gltf_mat_idx < 0:
                continue

            # Compact vertices used by this submesh and reverse triangle winding (i0, i1, i2) -> (i0, i2, i1)
            tri_arr = np.array(sm_tris, dtype=np.uint32)
            tri_arr = tri_arr[:, [0, 2, 1]]  # LH -> RH winding flip
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
    builder.meshes.append({"name": f"{var_id}_mesh", "primitives": primitives})
    mesh_node_idx = len(builder.nodes)
    builder.nodes.append({"name": f"{var_id}_skinned", "mesh": mesh_idx, "skin": skin_idx})
    builder.nodes[align_node_idx]["children"].append(mesh_node_idx)

    # Decode battle AnimationClips
    clips_by_name: dict[str, Any] = {}
    for obj in env.objects:
        if obj.type.name == "AnimationClip":
            ac = obj.read()
            clips_by_name[ac.m_Name] = ac

    path_crc_map = build_transform_path_crc_map(transforms, root_pid)
    exported_clips: dict[str, dict[str, Any]] = {}
    idle_frame0_overrides: dict[int, dict[str, np.ndarray]] = {}

    for canonical_name, suffixes in CLIP_CANDIDATES.items():
        chosen = None
        for suf in suffixes:
            for cname, ac in clips_by_name.items():
                if cname.endswith("_" + suf) or cname == suf:
                    chosen = ac
                    break
            if chosen is not None:
                break
        if chosen is None:
            continue

        decoded = decode_animation_clip(chosen, path_crc_map, pid_to_node_idx, sample_fps=sample_fps)
        times = decoded["times"]
        channels = decoded["channels"]

        if canonical_name == "idle":
            for (nidx, prop), vals in channels.items():
                idle_frame0_overrides.setdefault(nidx, {})[prop] = vals[0].astype(np.float64)

        time_acc = builder.add_accessor(times, COMP_FLOAT, "SCALAR", target=None, include_minmax=True)
        gltf_channels = []
        gltf_samplers = []
        animated_nodes = set()

        for (nidx, prop), vals in sorted(channels.items()):
            acc_type = "VEC4" if prop == "rotation" else "VEC3"
            # Check motion range for diagnostics
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

    # Evaluate idle frame-0 skinned pose to ground feet cleanly at Y = 0 and measure bbox
    concat_pos = np.concatenate(all_positions, axis=0)
    concat_j = np.concatenate(all_joints, axis=0)
    concat_w = np.concatenate(all_weights, axis=0)

    world_idle = _compute_world_mats_rh(builder.nodes, overrides=idle_frame0_overrides)
    skinned_idle = _skin_positions(concat_pos, concat_j, concat_w, joint_node_indices, joint_ibms_rh, world_idle)

    min_y = float(skinned_idle[:, 1].min())
    # Align feet cleanly to Y = 0 via root_align node (does not disturb any bone animation!)
    if abs(min_y) > 1e-4:
        builder.nodes[align_node_idx]["translation"] = [0.0, -min_y, 0.0]
        skinned_idle[:, 1] -= min_y

    bbox_min = [round(float(x), 4) for x in skinned_idle.min(axis=0)]
    bbox_max = [round(float(x), 4) for x in skinned_idle.max(axis=0)]
    height_m = round(bbox_max[1] - bbox_min[1], 4)

    os.makedirs(os.path.dirname(os.path.abspath(out_glb_path)), exist_ok=True)
    tmp_path = f"{out_glb_path}.tmp.{os.getpid()}"
    file_bytes = builder.write(tmp_path)
    os.replace(tmp_path, out_glb_path)

    return {
        "species": species,
        "form": form,
        "shiny": shiny,
        "id": base_id,
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

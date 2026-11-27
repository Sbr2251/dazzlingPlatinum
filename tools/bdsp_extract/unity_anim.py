"""Unity AnimationClip decoder (StreamedClip + DenseClip + ConstantClip) and LH->RH math."""

from __future__ import annotations

import math
import struct
import zlib
from typing import Any

import numpy as np


# Unity LH -> glTF RH conversion helpers (reflection across X: x -> -x)
def lh_to_rh_vec3(v: tuple[float, float, float]) -> np.ndarray:
    return np.array([-float(v[0]), float(v[1]), float(v[2])], dtype=np.float32)


def lh_to_rh_quat(q: tuple[float, float, float, float]) -> np.ndarray:
    """Convert Unity quaternion (x,y,z,w) to glTF RH quaternion: R' = F R F => (qx, -qy, -qz, qw)."""
    arr = np.array([float(q[0]), -float(q[1]), -float(q[2]), float(q[3])], dtype=np.float64)
    n = np.linalg.norm(arr)
    if n < 1e-12:
        return np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)
    return (arr / n).astype(np.float32)


def unity_euler_deg_to_quat(ex: float, ey: float, ez: float) -> tuple[float, float, float, float]:
    """Unity intrinsic Z-X-Y Euler degrees -> Unity quaternion (x,y,z,w)."""
    rx = math.radians(ex) * 0.5
    ry = math.radians(ey) * 0.5
    rz = math.radians(ez) * 0.5
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    # q = qy * qx * qz
    w = cy * cx * cz + sy * sx * sz
    x = cy * sx * cz + sy * cx * sz
    y = sy * cx * cz - cy * sx * sz
    z = cy * cx * sz - sy * sx * cz
    return (x, y, z, w)


def lh_to_rh_mat4(m: np.ndarray) -> np.ndarray:
    """Similarity transform F @ M @ F with F = diag(-1, 1, 1, 1)."""
    out = m.astype(np.float64).copy()
    out[0, 1:4] = -out[0, 1:4]
    out[1:4, 0] = -out[1:4, 0]
    return out


def mat4_from_trs_rh(t: np.ndarray, q: np.ndarray, s: np.ndarray) -> np.ndarray:
    x, y, z, w = float(q[0]), float(q[1]), float(q[2]), float(q[3])
    R = np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0.0],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0.0],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    S = np.diag([float(s[0]), float(s[1]), float(s[2]), 1.0])
    T = np.eye(4, dtype=np.float64)
    T[0, 3], T[1, 3], T[2, 3] = float(t[0]), float(t[1]), float(t[2])
    return T @ R @ S


def build_transform_path_crc_map(transforms: dict[int, Any], root_pid: int) -> dict[int, int]:
    """Return {crc32(relative_path): transform_path_id} for all descendants of root_pid."""
    out: dict[int, int] = {}

    def walk(pid: int, prefix: str) -> None:
        tr = transforms[pid]
        name = tr.m_GameObject.read().m_Name
        if prefix == "":
            cur = ""
        elif prefix == "/":
            cur = name
        else:
            cur = f"{prefix}/{name}"
        if cur:
            h = zlib.crc32(cur.encode("utf-8")) & 0xFFFFFFFF
            out[h] = pid
        for ch in tr.m_Children:
            if ch.path_id in transforms:
                walk(ch.path_id, "/" if cur == "" else cur)

    walk(root_pid, "")
    return out


def _parse_streamed_clip(sdata: list[int]) -> list[tuple[float, list[tuple[int, float, float, float, float]]]]:
    """Parse Unity StreamedClip frames -> [(time, [(curve_idx, c0, c1, c2, c3), ...]), ...]."""
    if not sdata:
        return []
    raw = struct.pack(f"<{len(sdata)}I", *sdata)
    frames = []
    off = 0
    n = len(raw)
    while off + 8 <= n:
        t, cnt = struct.unpack_from("<fi", raw, off)
        off += 8
        if cnt < 0 or off + cnt * 20 > n:
            break
        keys = []
        for _ in range(cnt):
            cidx, c0, c1, c2, c3 = struct.unpack_from("<iffff", raw, off)
            off += 20
            keys.append((cidx, c0, c1, c2, c3))
        frames.append((t, keys))
    return frames


def decode_animation_clip(
    clip_obj: Any,
    path_crc_to_pid: dict[int, int],
    pid_to_node_idx: dict[int, int],
    sample_fps: float = 30.0,
) -> dict[str, Any]:
    """Decode a Unity AnimationClip into sampled glTF RH TRS channels per node.

    Returns {
      "duration": float,
      "times": np.ndarray (float32, shape [N]),
      "channels": { (node_idx, path_str): np.ndarray (float32, shape [N, 3|4]) }
    }
    """
    mc = clip_obj.m_MuscleClip
    duration = max(float(mc.m_StopTime) - float(mc.m_StartTime), 1.0 / sample_fps)
    clip_data = mc.m_Clip.data
    bc = clip_obj.m_ClipBindingConstant

    # Build uniform sample times covering [0, duration]
    num_steps = max(2, int(round(duration * sample_fps)) + 1)
    times = np.linspace(0.0, duration, num_steps, dtype=np.float32)

    streamed_count = int(clip_data.m_StreamedClip.curveCount)
    dense = clip_data.m_DenseClip
    dense_count = int(dense.m_CurveCount)
    dense_frames = int(dense.m_FrameCount)
    dense_rate = float(dense.m_SampleRate) if dense.m_SampleRate else 30.0
    dense_begin = float(dense.m_BeginTime)
    dense_vals = np.array(dense.m_SampleArray, dtype=np.float32)
    if dense_frames > 0 and dense_count > 0:
        dense_vals = dense_vals.reshape((dense_frames, dense_count))
    else:
        dense_vals = np.zeros((0, 0), dtype=np.float32)
    const_vals = np.array(clip_data.m_ConstantClip.data, dtype=np.float32)

    total_curves = streamed_count + dense_count + len(const_vals)
    # Sample all curves across `times` -> shape (num_steps, total_curves)
    sampled = np.zeros((num_steps, total_curves), dtype=np.float32)

    # 1. Evaluate StreamedClip Hermite cubics
    if streamed_count > 0:
        sframes = _parse_streamed_clip(clip_data.m_StreamedClip.data)
        # Maintain active cubic segment per curve_idx as we advance through frames
        # At time t, for the latest frame with frame_t <= t: val = ((c0*dt + c1)*dt + c2)*dt + c3
        active_t = np.zeros(streamed_count, dtype=np.float64)
        active_c = np.zeros((streamed_count, 4), dtype=np.float64)
        fi = 0
        nf = len(sframes)
        for ti, t in enumerate(times):
            tf = float(t)
            while fi < nf and sframes[fi][0] <= tf + 1e-6:
                ft, keys = sframes[fi]
                for cidx, c0, c1, c2, c3 in keys:
                    if 0 <= cidx < streamed_count:
                        active_t[cidx] = ft
                        active_c[cidx] = (c0, c1, c2, c3)
                fi += 1
            dt = np.maximum(0.0, tf - active_t)
            # Guard against the initial -FLT_MAX sentinel frame (where c0=c1=c2=0, val=c3)
            dt = np.where(active_t < -1e10, 0.0, dt)
            vals = ((active_c[:, 0] * dt + active_c[:, 1]) * dt + active_c[:, 2]) * dt + active_c[:, 3]
            sampled[ti, :streamed_count] = vals.astype(np.float32)

    # 2. Evaluate DenseClip linearly
    if dense_count > 0 and dense_frames > 0:
        for ti, t in enumerate(times):
            fpos = (float(t) - dense_begin) * dense_rate
            if fpos <= 0.0:
                sampled[ti, streamed_count : streamed_count + dense_count] = dense_vals[0]
            elif fpos >= dense_frames - 1:
                sampled[ti, streamed_count : streamed_count + dense_count] = dense_vals[-1]
            else:
                i0 = int(math.floor(fpos))
                frac = fpos - i0
                sampled[ti, streamed_count : streamed_count + dense_count] = (
                    dense_vals[i0] * (1.0 - frac) + dense_vals[i0 + 1] * frac
                )

    # 3. Fill ConstantClip
    if len(const_vals) > 0:
        sampled[:, streamed_count + dense_count :] = const_vals[None, :]

    # Map genericBindings to (node_idx, property) channels
    channels: dict[tuple[int, str], np.ndarray] = {}
    curve_cursor = 0
    for gb in bc.genericBindings:
        attr = int(gb.attribute)
        type_id = int(gb.typeID)
        if type_id == 4:  # Transform
            if attr == 1:
                width = 3
                prop = "translation"
            elif attr == 2:
                width = 4
                prop = "rotation"
            elif attr == 3:
                width = 3
                prop = "scale"
            elif attr == 4:
                width = 3
                prop = "euler"
            else:
                width = 1
                prop = ""
        else:
            width = 1
            prop = ""

        if curve_cursor + width > total_curves:
            break

        pid = path_crc_to_pid.get(int(gb.path))
        if type_id == 4 and prop and pid is not None and pid in pid_to_node_idx:
            node_idx = pid_to_node_idx[pid]
            raw_c = sampled[:, curve_cursor : curve_cursor + width]
            if prop == "translation":
                out = raw_c.copy()
                out[:, 0] = -out[:, 0]
                channels[(node_idx, "translation")] = out.astype(np.float32)
            elif prop == "scale":
                channels[(node_idx, "scale")] = raw_c.astype(np.float32)
            elif prop == "rotation":
                out = np.empty((num_steps, 4), dtype=np.float32)
                for ti in range(num_steps):
                    q = lh_to_rh_quat((raw_c[ti, 0], raw_c[ti, 1], raw_c[ti, 2], raw_c[ti, 3]))
                    if ti > 0 and float(np.dot(out[ti - 1], q)) < 0.0:
                        q = -q
                    out[ti] = q
                channels[(node_idx, "rotation")] = out
            elif prop == "euler":
                out = np.empty((num_steps, 4), dtype=np.float32)
                for ti in range(num_steps):
                    uq = unity_euler_deg_to_quat(float(raw_c[ti, 0]), float(raw_c[ti, 1]), float(raw_c[ti, 2]))
                    q = lh_to_rh_quat(uq)
                    if ti > 0 and float(np.dot(out[ti - 1], q)) < 0.0:
                        q = -q
                    out[ti] = q
                channels[(node_idx, "rotation")] = out

        curve_cursor += width

    return {"duration": duration, "times": times, "channels": channels}

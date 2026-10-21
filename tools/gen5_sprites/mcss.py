#!/usr/bin/env python3
"""Black 2/White 2 battle sprites (MCSS) from pokebw2's extracted data, played and drawn the way the
game does, one 60 Hz tick at a time. gen5_stream.py turns the frames into streams
(docs/living_battle_stage/sprite_stream.md).

Sources, all in pokebw2 (READ-ONLY): res/pokemon/<species>[/form_<n>]/
    <face>_multi_animations.nmar   NMAR: sequence 0 is the loop, sequence 1 (47 species) the idle pose
    <face>_multi_cells.nmcr        NMCR: multi-cells, each a list of nodes (cell animation, position)
    <face>_animations.nanr.lz11    NANR: each node's cell animation (cell index, rotation, scale, translation)
    <face>_info.bin                MCSS's quad table (mcss.c MCSSBin) and the idle nodes (MCSSBinTail)
    <face>.png, <face>_female.png  the 256x128 4bpp atlas the quads sample
    normal.pal, shiny.pal          16 colours, index for index

Behaviour followed, by file (pokebw2 paths):
- lib/nnsys/src/g2d/g2d_Animation.c: the animation controller (frames, loop start, the four play
  modes, zero-length frames, the LAST_FRM callback at a sequence's end). `Ctrl` is a line-for-line port.
- lib/nnsys/src/g2d/g2d_MultiCellAnimation.c, share-cell-animation mode (MCSS_InitMCAnime): when the
  multi-cell animation moves to a keyframe, every node's cell animation is bound again, and a node in
  play mode CONTINUE is played on to the multi-cell animation's total time (totalVideoFrame); between
  keyframes the cell animations tick on their own. `MCAnim`.
- src/system/mcss.c MCSSSys_Draw / MCSS_DrawQuad: the transform chain (multi-cell offset, rotation and
  scale, node position plus cell translation, cell rotation and scale, quad offset and size), nodes
  drawn from node 0 with the depth stepping back per quad, the second quad of a cell in front of the
  first. Ortho ("flat") at scale 16: one texel per pixel. `render`.
- src/ov168/btlv_mcss.c BtlvMcss_Main, BtlvMcss_OnAnimationEnd, BtlvMcss_IdleTask,
  BtlvMcss_IdleNodeCallback: the battle restarts the animation the frame after a loop ends when the face
  has no idle data (idle node count 0xff); otherwise the loop runs on, and an idle switches to sequence 1
  (when there is one), stops the multi-cell clock and every cell animation but the idle nodes', for
  48, 56 or 64 frames. `battle_loop`, `idle_clip`.

Frames are palette indices (uint8, 0 transparent) in an image whose foot point (the MCSS origin, where
the battle puts the Pokemon) is at ORIGIN.
"""

import math
import os
import struct

import numpy as np
from PIL import Image

BW2 = "/data/repos/pokebw2/res/pokemon"
IMG_W, IMG_H = 320, 256
ORIGIN = (160, 200)  # foot point in the rendered image: pixel column 160 starts right of it, row 200 under it

FORWARD, FORWARD_LOOP, REVERSE, REVERSE_LOOP = 1, 2, 3, 4
PLAYMODE_CONTINUE = 1  # a node's nodeAttr & 0xf
IDLE_WAITS = (48, 56, 64)  # btlv_mcss.c data_ov168_021f4184
IDLE_CLIP_TICKS = max(IDLE_WAITS)
NO_IDLE = 0xFF


# ---------------------------------------------------------------------------------------------
# Files

def lz11(data):
    assert data[0] == 0x11, hex(data[0])
    size = data[1] | data[2] << 8 | data[3] << 16
    i, out = 4, bytearray()
    while len(out) < size:
        flags = data[i]
        i += 1
        for b in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> b):
                a = data[i]
                ind = a >> 4
                if ind == 0:
                    n = ((a & 0xF) << 4 | data[i + 1] >> 4) + 0x11
                    disp = ((data[i + 1] & 0xF) << 8 | data[i + 2]) + 1
                    i += 3
                elif ind == 1:
                    n = ((a & 0xF) << 12 | data[i + 1] << 4 | data[i + 2] >> 4) + 0x111
                    disp = ((data[i + 2] & 0xF) << 8 | data[i + 3]) + 1
                    i += 4
                else:
                    n = ind + 1
                    disp = ((a & 0xF) << 8 | data[i + 1]) + 1
                    i += 2
                for _ in range(n):
                    out.append(out[-disp])
            else:
                out.append(data[i])
                i += 1
    return bytes(out)


def blocks(data):
    hdr_size, nblk = struct.unpack_from("<HH", data, 12)
    off, res = hdr_size, {}
    for _ in range(nblk):
        size = struct.unpack_from("<I", data, off + 4)[0]
        res[data[off:off + 4]] = data[off + 8:off + size]
        off += size
    return res


class Seq:
    """An NNSG2dAnimSequence: frames [(element, duration)], element (index, rotZ, sx, sy, px, py)."""

    def __init__(self, frames, loop_start, play_mode):
        self.frames, self.loop_start, self.play_mode = frames, loop_start, play_mode
        self.total = sum(d for _, d in frames)


def parse_anim(data):
    abnk = blocks(data)[b"KNBA"]
    nseq, _, seq_off, fr_off, dat_off = struct.unpack_from("<HHIII", abnk, 0)
    seqs = []
    for s in range(nseq):
        nf, loop, atype, mode, foff = struct.unpack_from("<HHIII", abnk, seq_off + s * 16)
        etype = atype & 0xFF
        frames = []
        for f in range(nf):
            doff, dur, _ = struct.unpack_from("<IHH", abnk, fr_off + foff + f * 8)
            o = dat_off + doff
            if etype == 0:  # NNS_G2D_ANIMELEM_INDEX
                el = (struct.unpack_from("<H", abnk, o)[0], 0, 4096, 4096, 0, 0)
            elif etype == 1:  # INDEX_SRT
                el = struct.unpack_from("<HHiihh", abnk, o)
            else:  # INDEX_T
                idx, _, px, py = struct.unpack_from("<HHhh", abnk, o)
                el = (idx, 0, 4096, 4096, px, py)
            frames.append((el, dur))
        seqs.append(Seq(frames, loop, mode))
    return seqs


def parse_nmcr(data):
    """[(numCellAnim, [(animSequenceIdx, x, y, nodeAttr)])]"""
    bnk = blocks(data)[b"KBCM"]
    n, _, data_off, hier_off = struct.unpack_from("<HHII", bnk, 0)
    out = []
    for m in range(n):
        nnodes, ncell, hoff = struct.unpack_from("<HHI", bnk, data_off + m * 8)
        out.append((ncell, [struct.unpack_from("<HhhH", bnk, hier_off + hoff + k * 8) for k in range(nnodes)]))
    return out


def parse_bin(data):
    """MCSSBin: header and per cell (quad, quad2), each (x, y, w, h, s, t) in fx32; MCSSBinTail."""
    count, w, h, ox, oy = struct.unpack_from("<IHHhh", data, 0)
    cells = []
    for i in range(count):
        v = struct.unpack_from("<12i", data, 12 + i * 48)
        cells.append((v[0:6], v[6:12]))
    tail = data[12 + count * 48:]
    idle_count = tail[0] if tail else NO_IDLE
    idle_nodes = list(tail[2:2 + idle_count]) if idle_count != NO_IDLE else []
    return {"cells": cells, "size": (w, h), "offset": (ox, oy), "idle_count": idle_count,
            "idle_nodes": idle_nodes}


def load_pal(path):
    words = open(path).read().split()
    n = int(words[2])
    return [tuple(int(x) for x in words[3 + i * 3:6 + i * 3]) for i in range(n)]


class Face:
    """One face (front or back) of a pokebw2 sprite directory."""

    def __init__(self, directory, face, female=False):
        p = lambda name: os.path.join(directory, f"{face}_{name}")
        self.directory, self.face = directory, face
        self.nmar = parse_anim(open(p("multi_animations.nmar"), "rb").read())
        self.nanr = parse_anim(lz11(open(p("animations.nanr.lz11"), "rb").read()))
        self.nmcr = parse_nmcr(open(p("multi_cells.nmcr"), "rb").read())
        self.bin = parse_bin(open(p("info.bin"), "rb").read())
        tex = os.path.join(directory, f"{face}_female.png" if female else f"{face}.png")
        im = Image.open(tex)
        assert im.mode == "P", tex
        self.tex = np.array(im, dtype=np.uint8)
        assert self.tex.max() < 16, tex
        self.max_cell_anims = max(n for n, _ in self.nmcr)

    @property
    def idle_count(self):
        return self.bin["idle_count"]


def has_face(directory, face):
    return os.path.exists(os.path.join(directory, f"{face}_info.bin"))


# ---------------------------------------------------------------------------------------------
# NitroSystem animation (g2d_Animation.c, g2d_MultiCellAnimation.c), speed 1, whole ticks

class Ctrl:
    """NNSG2dAnimController at speed FX32_ONE with integer ticks."""

    def __init__(self):
        self.seq = None
        self.cur = 0
        self.active_cur = 0
        self.reverse = False
        self.active = True
        self.time = 0
        self.on_last_frame = None  # NNS_G2D_ANMCALLBACKTYPE_LAST_FRM

    def _loop(self):
        return self.seq.play_mode in (FORWARD_LOOP, REVERSE_LOOP)

    def _reverse_mode(self):
        return self.seq.play_mode in (REVERSE, REVERSE_LOOP)

    def _forward(self):
        return not self.reverse  # bReverse ^ (speed > 0)

    def _reach_edge(self):
        if self._forward():
            return self.cur >= len(self.seq.frames)
        return self.cur <= self.seq.loop_start - 1

    def _end_sequence(self):
        if self.on_last_frame:
            self.on_last_frame()
        if not self._loop():
            self.active = False
        else:
            self.reset()

    def _edge(self):
        if self._reverse_mode():
            self.reverse = not self.reverse
            if self.cur <= self.seq.loop_start - 1:
                self._end_sequence()
        else:
            self._end_sequence()
        last = len(self.seq.frames) - 1
        if self.cur > last:
            self.cur = last
        elif self.cur < 0:
            self.cur = 0

    def tick(self, frames):
        if not self.active:
            return False
        changed = False
        self.time += frames
        guard = 0
        while self.active and self.time >= self.seq.frames[self.cur][1]:
            changed = True
            self.time -= self.seq.frames[self.cur][1]
            self.cur += 1 if self._forward() else -1
            if self._reach_edge():
                self._edge()
            if self.seq.frames[self.cur][1] != 0:
                self.active_cur = self.cur
            guard += 1
            if guard > 100000:
                raise RuntimeError("animation sequence with no length")
        return changed

    def reset(self):
        self.cur = self.seq.loop_start if self._forward() else len(self.seq.frames) - 1
        self.active_cur = self.cur
        self.time = 0
        self.tick(0)

    def bind(self, seq):
        self.seq = seq
        self.reset()

    def element(self):
        """What MCSS draws: pCurrent's element (MCSS_GetAnimSrt)."""
        return self.seq.frames[self.cur][0]

    def state(self):
        return (self.cur, self.time, self.reverse, self.active)


class MCAnim:
    """NNSG2dMultiCellAnimation in NNS_G2D_MCTYPE_SHARE_CELLANIM mode, as MCSS sets it up."""

    def __init__(self, face, seq_index, on_loop_end=None):
        self.face = face
        self.cells = [Ctrl() for _ in range(face.max_cell_anims)]  # MCSS_InitMCAnime: a new work area
        self.ctrl = Ctrl()
        self.ctrl.on_last_frame = on_loop_end
        self.total = 0
        self.mc = None
        self.set_sequence(face.nmar[seq_index])

    def _set_node(self, cell, node):
        seq = self.face.nanr[node[0]]
        cell.bind(seq)
        cell.active = True
        if node[3] & 0xF == PLAYMODE_CONTINUE:
            frames = seq.total
            if frames == 0:
                return
            if cell._loop():
                cell.tick(self.total % frames)
            else:
                cell.tick(min(self.total, frames))

    def _set_mc(self):
        if self.ctrl.seq.frames[self.ctrl.active_cur][1] == 0:
            return
        el = self.ctrl.seq.frames[self.ctrl.active_cur][0]
        self.mc = el[0]
        ncell, nodes = self.face.nmcr[self.mc]
        inited = [False] * ncell
        for node in nodes:
            slot = node[3] >> 8
            if not inited[slot]:
                self._set_node(self.cells[slot], node)
                inited[slot] = True

    def set_sequence(self, seq):
        self.ctrl.bind(seq)
        self.total = 0
        self._set_mc()

    def tick(self, frames=1):
        last = self.ctrl.seq.frames[self.ctrl.cur][1]
        if self.ctrl.tick(frames):
            self.total += last
            self._set_mc()
        else:
            for cell in self.cells[:self.face.nmcr[self.mc][0]]:
                cell.tick(frames)

    def restart(self):
        """NNS_G2dRestartMCAnimation."""
        self.total = 0
        self.set_sequence(self.ctrl.seq)
        self.ctrl.active = True
        for cell in self.cells[:self.face.nmcr[self.mc][0]]:
            cell.reset()
            cell.active = True

    def set_idle_nodes(self, idle):
        """BtlvMcss_IdleNodeCallback over the current multi-cell's nodes (MCSS_TraverseNodes)."""
        for i, node in enumerate(self.face.nmcr[self.mc][1]):
            self.cells[node[3] >> 8].active = (i in self.face.bin["idle_nodes"]) if idle else True

    def pose(self):
        """Everything the draw reads: the multi-cell's element and each node's cell element."""
        nodes = self.face.nmcr[self.mc][1]
        return (self.ctrl.element(), tuple(self.cells[n[3] >> 8].element() for n in nodes))


# ---------------------------------------------------------------------------------------------
# The battle's playback (btlv_mcss.c)

def battle_loop(face):
    """The poses of one loop as the battle shows them, one per 60 Hz tick, and whether the loop
    restarts (face without idle data) or runs on.

    No idle data (idle count 0xff): BtlvMcss_Main restarts the animation the frame after its loop
    ended, so the frames drawn are the pose at the loop's end (sequence back at its loop start, cell
    animations at the total time) and then ticks 1 .. L-1 of a fresh start: that is the loop, period L.
    With idle data the loop runs on into the next until an idle; the first loop, ticks 0 .. L-1 from the
    sprite's load, is the one kept (the loops after it differ only in CONTINUE nodes whose length does
    not divide L, and the idle restarts sequence 0 from tick 0 anyway).
    Returns (poses, wrap_pose): wrap_pose is what is on screen at the tick the loop ends."""
    ended = []
    anim = MCAnim(face, 0, on_loop_end=lambda: ended.append(True))
    length = face.nmar[0].total
    poses = [anim.pose()]
    for _ in range(1, length):
        anim.tick(1)
        poses.append(anim.pose())
    anim.tick(1)
    wrap = anim.pose()
    if face.idle_count == NO_IDLE:
        poses[0] = wrap
    return poses, wrap


def idle_clip(face, wrap_pose):
    """The poses of an idle, one per tick for IDLE_CLIP_TICKS, or None for a face that never idles.
    BtlvMcss_OnAnimationEnd: with a second sequence, MCSS_SetAnimation(1) (a new multi-cell animation
    at its tick 0); BtlvMcss_IdleTask then stops the multi-cell clock and every cell animation but the
    idle nodes'. Without one the pose at the loop's end holds."""
    if face.idle_count == NO_IDLE:
        return None
    if len(face.nmar) < 2:
        return [wrap_pose] * IDLE_CLIP_TICKS
    anim = MCAnim(face, 1)
    anim.ctrl.active = False
    anim.set_idle_nodes(True)
    poses = [anim.pose()]
    for _ in range(1, IDLE_CLIP_TICKS):
        anim.tick(1)
        poses.append(anim.pose())
    return poses


# ---------------------------------------------------------------------------------------------
# Drawing (mcss.c MCSSSys_Draw, MCSS_DrawQuad), ortho at one texel per pixel

def _rot(idx):
    """G3_RotZ(-FX_SinIdx(idx), FX_CosIdx(idx)) on (x, y-up) column vectors."""
    th = idx / 65536.0 * 2 * math.pi
    c, s = math.cos(th), math.sin(th)
    return np.array([[c, s], [-s, c]])


def render(face, pose, scale=1.0, size=(IMG_W, IMG_H), origin=ORIGIN):
    """The pose as palette indices, the foot point at origin (pixel boundary). scale multiplies the
    sprite's own scale (MCSS_SetScale) about the foot point."""
    (mc_el, cell_els) = pose
    mc_idx, mrot, msx, msy, mpx, mpy = mc_el
    nodes = face.nmcr[mc_idx][1]
    cells = face.bin["cells"]
    W, H = size
    out = np.zeros((H, W), dtype=np.uint8)
    done = np.zeros((H, W), dtype=bool)
    # Multi-cell: translate (px, -py), rotate, scale (mcss.c ortho branch: offset * scale / 16)
    m_lin = _rot(mrot) @ np.diag([msx / 4096.0 * scale, msy / 4096.0 * scale])
    m_off = np.array([mpx * scale, -mpy * scale])
    tex = face.tex
    th, tw = tex.shape
    for node, cel in zip(nodes, cell_els):
        ci, crot, csx, csy, cpx, cpy = cel
        if ci >= len(cells):
            continue
        quad, quad2 = cells[ci]
        c_lin = _rot(crot) @ np.diag([csx / 4096.0, csy / 4096.0])
        c_off = np.array([cpx + node[1], -(cpy + node[2])], dtype=np.float64)
        for q in ([quad2, quad] if quad2[2] != 0 else [quad]):
            x, y, w, h, s, t = q
            qw, qh = w / 4096.0, h / 4096.0
            if qw <= 0 or qh <= 0:
                continue
            # quad-local (a, b) in texels, b down -> y-up pixels: (x/256 + a, y/256 - b)
            lin = m_lin @ c_lin  # 2x2 on y-up pixels
            off = m_lin @ (c_lin @ np.array([x / 256.0, y / 256.0]) + c_off) + m_off
            # screen (X right, Y down): X = ox + p.x, Y = oy - p.y; p = lin @ (a, -b) + off
            A = np.array([[lin[0, 0], -lin[0, 1]], [-lin[1, 0], lin[1, 1]]])
            bvec = np.array([origin[0] + off[0], origin[1] - off[1]])
            corners = np.array([[0, 0], [qw, 0], [0, qh], [qw, qh]]) @ A.T + bvec
            x0 = max(0, int(math.floor(corners[:, 0].min())))
            x1 = min(W, int(math.ceil(corners[:, 0].max())))
            y0 = max(0, int(math.floor(corners[:, 1].min())))
            y1 = min(H, int(math.ceil(corners[:, 1].max())))
            if x0 >= x1 or y0 >= y1:
                continue
            det = A[0, 0] * A[1, 1] - A[0, 1] * A[1, 0]
            if abs(det) < 1e-9:
                continue
            inv = np.array([[A[1, 1], -A[0, 1]], [-A[1, 0], A[0, 0]]]) / det
            gy, gx = np.mgrid[y0:y1, x0:x1]
            px = gx + 0.5 - bvec[0]
            py = gy + 0.5 - bvec[1]
            a = inv[0, 0] * px + inv[0, 1] * py
            b = inv[1, 0] * px + inv[1, 1] * py
            eps = 1e-6
            inside = (a >= -eps) & (a < qw - eps) & (b >= -eps) & (b < qh - eps)
            if not inside.any():
                continue
            ai = np.floor(np.clip(a, 0, qw - 1e-3)).astype(np.int64)
            bi = np.floor(np.clip(b, 0, qh - 1e-3)).astype(np.int64)
            sx = (int(s // 4096) + ai) % tw
            ty = (int(t // 4096) + bi) % th
            texel = tex[ty, sx]
            region_done = done[y0:y1, x0:x1]
            take = inside & (texel != 0) & ~region_done
            out[y0:y1, x0:x1][take] = texel[take]
            region_done |= take
    return out


def frames_of(face, poses, scale=1.0):
    """Rendered frames for a list of poses, drawing each distinct pose once."""
    cache, out = {}, []
    for p in poses:
        if p not in cache:
            cache[p] = render(face, p, scale)
        out.append(cache[p])
    return out


def bbox(img):
    ys, xs = np.nonzero(img)
    if len(ys) == 0:
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)

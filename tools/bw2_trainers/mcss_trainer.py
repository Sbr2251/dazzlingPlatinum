#!/usr/bin/env python3
"""Flatten a pokebw2 trainer MCSS (res/trainers/sprites/{front,back}/<class>/) into indexed frames.

Adapted from the gap audit's /tmp/bw2gap/sprites/mcss_render.py (which renders Pokemon MCSS). A trainer
MCSS has the same parts as a Pokemon's: mcss.bin is the per-cell quad table (mcss.c's "info"), sheet.png the
texture (indexed, normal.pal), animations.nanr (stored uncompressed here) animates each node with SRT
keys, multi_cells.nmcr is the node hierarchy and multi_animations.nmar picks the multi-cell per tick.
The result keeps the palette indices, so the frames go straight into a 4bpp OBJ with BW2's own palette.

render(path, tick) -> (list of rows of palette indices, 0 = transparent) on a CANVAS x CANVAS grid with
the MCSS origin (the foot point) at (ORIGIN_X, ORIGIN_Y). Ticks are MCSS ticks (60 Hz).
"""
import math
import struct
from pathlib import Path

CANVAS = 256
ORIGIN_X, ORIGIN_Y = 128, 176


def blocks(data):
    hdr_size = struct.unpack_from("<H", data, 12)[0]
    nblk = struct.unpack_from("<H", data, 14)[0]
    off = hdr_size
    res = {}
    for _ in range(nblk):
        magic = data[off:off + 4]
        size = struct.unpack_from("<I", data, off + 4)[0]
        res[magic] = data[off + 8:off + size]
        off += size
    return res


def anim_srt(data):
    abnk = blocks(data)[b"KNBA"]
    nseq, _nfr, seq_off, fr_off, dat_off = struct.unpack_from("<HHIII", abnk, 0)
    seqs = []
    for s in range(nseq):
        nf, _loop, atype, _mode, foff = struct.unpack_from("<HHIII", abnk, seq_off + s * 16)
        ftype = atype & 0xFFFF
        frames = []
        for f in range(nf):
            doff, dur, _ = struct.unpack_from("<IHH", abnk, fr_off + foff + f * 8)
            o = dat_off + doff
            rot, sx, sy, px, py = 0, 4096, 4096, 0, 0
            if ftype == 0:
                idx = struct.unpack_from("<H", abnk, o)[0]
            elif ftype == 1:  # SRT
                idx, rot, sx, sy, px, py = struct.unpack_from("<HHiihh", abnk, o)
            else:  # T
                idx, _, px, py = struct.unpack_from("<HHhh", abnk, o)
            frames.append((idx, dur, px, py, rot, sx, sy))
        seqs.append(frames)
    return seqs


def seq_length(frames):
    return sum(f[1] for f in frames) or 1


def at_tick(frames, t):
    t %= seq_length(frames)
    for f in frames:
        if t < f[1]:
            return f
        t -= f[1]
    return frames[-1]


def nmcr(data):
    bnk = blocks(data)[b"KBCM"]
    n, _, data_off, hier_off = struct.unpack_from("<HHII", bnk, 0)
    out = []
    for m in range(n):
        nnodes, _ncell, hoff = struct.unpack_from("<HHI", bnk, data_off + m * 8)
        out.append([struct.unpack_from("<HhhH", bnk, hier_off + hoff + k * 8) for k in range(nnodes)])
    return out


def quads(data):
    count = struct.unpack_from("<I", data, 0)[0]
    return [(struct.unpack_from("<6i", data, 12 + i * 48), struct.unpack_from("<6i", data, 36 + i * 48))
            for i in range(count)]


def load_pal(path):
    words = Path(path).read_text().split()
    n = int(words[2])
    return [tuple(map(int, words[3 + i * 3:6 + i * 3])) for i in range(n)]


class Trainer:
    def __init__(self, path):
        from PIL import Image
        p = Path(path)
        self.path = p
        self.nmar = anim_srt((p / "multi_animations.nmar").read_bytes())
        self.nanr = anim_srt((p / "animations.nanr").read_bytes())
        self.mcells = nmcr((p / "multi_cells.nmcr").read_bytes())
        self.quads = quads((p / "mcss.bin").read_bytes())
        tex = Image.open(p / "sheet.png")
        self.tex_w, self.tex_h = tex.size
        self.tex = tex.load()
        self.pal = load_pal(p / "normal.pal")

    def idle_length(self):
        """The loop of NMAR sequence 0 (the idle): the longest node animation it uses decides it."""
        mc_frames = self.nmar[0]
        length = seq_length(mc_frames)
        for f in mc_frames:
            for node in self.mcells[f[0]]:
                if node[0] < len(self.nanr):
                    length = max(length, seq_length(self.nanr[node[0]]))
        return length

    def render(self, tick=0, seq=0):
        W = H = CANVAS
        out = [[0] * W for _ in range(H)]
        mc_idx, _, mpx, mpy, mrot, msx, msy = at_tick(self.nmar[seq], tick)
        mth = mrot / 65536 * 2 * math.pi
        mcs, msn = math.cos(mth), math.sin(mth)
        for anim_idx, hx, hy, _attr in reversed(self.mcells[mc_idx]):  # node 0 last = in front
            if anim_idx < len(self.nanr):
                ci, _, cx, cy, crot, csx, csy = at_tick(self.nanr[anim_idx], tick)
            else:
                ci, cx, cy, crot, csx, csy = 0, 0, 0, 0, 4096, 4096
            if ci >= len(self.quads):
                continue
            q1, q2 = self.quads[ci]
            th = crot / 65536 * 2 * math.pi
            cs, sn = math.cos(th), math.sin(th)
            for q in ([q2, q1] if q2[2] != 0 else [q1]):
                x, y, w, h, s_, t = q
                ww, hh, ss, tt = w // 4096, h // 4096, s_ // 4096, t // 4096
                for j in range(hh):
                    for i in range(ww):
                        c = self.tex[(ss + i) % self.tex_w, (tt + j) % self.tex_h]
                        if c == 0:
                            continue
                        for su in (0.25, 0.75):
                            for sv in (0.25, 0.75):
                                lx = (x / 256 + i + su) * csx / 4096
                                ly = (y / 256 - j - sv) * csy / 4096
                                rx = lx * cs + ly * sn
                                ry = -lx * sn + ly * cs
                                nx = ((cx + hx) + rx) * msx / 4096
                                ny = (-(cy + hy) + ry) * msy / 4096
                                fx = nx * mcs + ny * msn
                                fy = -nx * msn + ny * mcs
                                X = int(math.floor(ORIGIN_X + mpx + fx))
                                Y = int(math.floor(ORIGIN_Y + mpy - fy))
                                if 0 <= X < W and 0 <= Y < H:
                                    out[Y][X] = c
        return out

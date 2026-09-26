#!/usr/bin/env python3
"""Generates res/battle/particles/moonblast.spa, the custom particle file used by
res/battle/moves/moonblast/anim.s.

The output is deterministic (no randomness, no timestamps), so re-running this
script must produce a byte-identical file. The file is checked in; this script
only has to be re-run when the effect is being tweaked.

    python3 tools/scripts/make_moonblast_spa.py            # write + verify
    python3 tools/scripts/make_moonblast_spa.py --check    # verify only

File layout follows lib/spl/include/spl_resource.h (SPLFileHeader,
SPLResourceHeader and the optional anim/child/behavior blocks) and
lib/spl/src/spl_manager.c (texture resources are read sequentially after the
emitter resources).

Emitter indices (what anim.s passes to CreateEmitter 0, N, ...):

    0  Crescent moon     One large crescent (tex 0) above the user that fades in,
                         slowly rises, shifts from pale moonlight to pink and sheds
                         small sparkle children before fading out. ~72 frames.
    1  Moonlight motes   Lavender/white sparkles (tex 2) spawned on a sphere around
                         the user, swirling (spin) and pulled into the center
                         (convergence). ~50 frames.
    2  Charge orb        A single soft pink glow (tex 1) that swells at the user
                         while the motes gather. Starts 6 frames late, ~42 frames.
    3  Projectile        Pink/white orb (tex 1) that follows its emitter, with a
                         sparkle trail (tex 2 children). Not self-maintaining, like
                         flash_cannon emitter 0, so Func_MoveEmitterA2BLinear can
                         move it; it must be created right before that call.
    4  Impact starburst  Burst of white-to-pink 4-point stars (tex 2) flying out
                         from the target. ~28 frames.
    5  Impact ring       Expanding pink moon-halo ring (tex 3) plus a bright core
                         flash at the target. ~24 frames.

Textures (all A5I3 = 5-bit alpha + 3-bit palette index, white palette, tinted
by the particle color like the vanilla files):

    0  64x64 crescent moon with a soft halo (new)
    1  32x32 soft radial glow (new)
    2  16x16 4-point sparkle (new)
    3  64x64 soft ring (new)
"""

import argparse
import math
import pathlib
import struct
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT_PATH = REPO / 'res' / 'battle' / 'particles' / 'moonblast.spa'

SPA_MAGIC = 0x53504120  # ' APS'
SPA_VERSION = 0x315F3231  # '12_1'

# --- fixed point / color helpers ---------------------------------------------


def fx(v):
    """fx32/fx16 (20.12 / 4.12) from a float."""
    return int(round(v * 4096))


def rgb(r, g, b):
    """GXRgb from 5-bit components."""
    assert all(0 <= c <= 31 for c in (r, g, b))
    return r | (g << 5) | (b << 10)


# --- SPLResourceFlags bits ---------------------------------------------------

EMIT_POINT = 0
EMIT_SPHERE_SURFACE = 1
EMIT_CIRCLE_BORDER = 2

DRAW_BILLBOARD = 0

F_SCALE_ANIM = 1 << 8
F_COLOR_ANIM = 1 << 9
F_ALPHA_ANIM = 1 << 10
F_ROTATION = 1 << 12
F_RANDOM_INIT_ANGLE = 1 << 13
F_SELF_MAINTAINING = 1 << 14
F_FOLLOW_EMITTER = 1 << 15
F_CHILD = 1 << 16
F_SPIN = 1 << 27
F_CONVERGENCE = 1 << 29

# SPLChildResourceFlags
CF_SCALE_ANIM = 1 << 1
CF_ALPHA_ANIM = 1 << 2
CF_FOLLOW_EMITTER = 1 << 5
CF_USE_CHILD_COLOR = 1 << 6

SPIN_AXIS_Y = 1

# --- emitter encoding ----------------------------------------------------------


def emitter(
    *,
    emission_type,
    flags=0,
    base_pos=(0.0, 0.0, 0.0),
    count=1.0,
    radius=0.0,
    length=0.0,
    axis=(0.0, 1.0, 0.0),
    color=rgb(31, 31, 31),
    vel_pos=0.0,
    vel_axis=0.0,
    scale=1.0,
    aspect=1.0,
    start_delay=0,
    rotation=(0, 0),
    init_angle=0,
    emitter_life=1,
    particle_life=16,
    rand_scale=0,
    rand_life=0,
    rand_vel=0,
    emission_interval=1,
    alpha=31,
    air_resistance=128,
    texture=0,
    loop_frames=1,
    scale_anim=None,
    color_anim=None,
    alpha_anim=None,
    child=None,
    spin=None,
    convergence=None,
):
    """Packs one SPLResource (header + optional blocks) as bytes.

    scale_anim:  (start, mid, end, curve_in, curve_out)
    color_anim:  (start_rgb, end_rgb, curve_in, curve_peak, curve_out, interpolate)
    alpha_anim:  (start, mid, end, curve_in, curve_out)
    child:       dict, see the child block below
    spin:        (angle_per_frame, axis)
    convergence: (target_xyz, force)
    """
    assert 1 <= loop_frames <= 255  # loopTimeFactor = 0xFFFF / loopFrames
    assert particle_life >= 1
    assert 0 <= texture < len(TEXTURES)

    flags |= emission_type | (DRAW_BILLBOARD << 4)
    if scale_anim:
        flags |= F_SCALE_ANIM
    if color_anim:
        flags |= F_COLOR_ANIM
    if alpha_anim:
        flags |= F_ALPHA_ANIM
    if child:
        flags |= F_CHILD
        assert particle_life >= 2  # child loopTimeFactor divides by life / 2
    if spin:
        flags |= F_SPIN
    if convergence:
        flags |= F_CONVERGENCE

    misc0 = emission_interval | (alpha << 8) | (air_resistance << 16) | (texture << 24)
    # loopFrames, dbbScale 0, texture tile count S/T = 1 (same as most vanilla emitters)
    misc1 = loop_frames | (1 << 24) | (1 << 26)
    rand_att = rand_scale | (rand_life << 8) | (rand_vel << 16)

    out = struct.pack(
        '<I3iiii3hHiiihHhhHHHHIIIIhhI',
        flags,
        *(fx(v) for v in base_pos),
        fx(count),
        fx(radius),
        fx(length),
        *(fx(v) for v in axis),
        color,
        fx(vel_pos),
        fx(vel_axis),
        fx(scale),
        fx(aspect),
        start_delay,
        rotation[0],
        rotation[1],
        init_angle,
        0,
        emitter_life,
        particle_life,
        rand_att,
        misc0,
        misc1,
        0,  # misc2: no texture flip
        0,  # polygonX
        0,  # polygonY
        0,  # userData
    )
    assert len(out) == 88

    if scale_anim:
        s, m, e, cin, cout = scale_anim
        assert cout < 255  # (255 - out) is a divisor in the curve math
        out += struct.pack('<hhhBBHH', fx(s), fx(m), fx(e), cin, cout, 0, 0)
    if color_anim:
        s, e, cin, cpeak, cout, interp = color_anim
        assert cin <= cpeak <= cout < 255
        curve = cin | (cpeak << 8) | (cout << 16)
        out += struct.pack('<HHIHH', s, e, curve, 4 if interp else 0, 0)
    if alpha_anim:
        s, m, e, cin, cout = alpha_anim
        assert cout < 255 and all(0 <= a <= 31 for a in (s, m, e))
        out += struct.pack('<HHBBH', s | (m << 5) | (e << 10), 0, cin, cout, 0)
    if child:
        c = child
        assert 0 <= c['texture'] < len(TEXTURES)
        misc = c['count'] | (c['delay'] << 8) | (c['interval'] << 16) | (c['texture'] << 24)
        out += struct.pack(
            '<HhhHBBHII',
            c['flags'],
            fx(c['rand_vel']),
            fx(c['end_scale']),
            c['life'],
            c['vel_ratio'],
            c['scale_ratio'],
            c['color'],
            misc,
            0,
        )
    # Behaviors, in flag bit order (gravity, random, magnet, spin, collision, convergence)
    if spin:
        out += struct.pack('<HH', spin[0], spin[1])
    if convergence:
        target, force = convergence
        out += struct.pack('<3ihH', *(fx(v) for v in target), fx(force), 0)
    return out


# --- textures ------------------------------------------------------------------

SS = 4  # supersampling factor per axis


def _raster(size, coverage):
    """Returns A5I3 bytes (index 0, alpha in the top 5 bits) for a size x size
    texture. coverage(x, y) returns 0..1 at a point in texel units, origin at
    the top-left corner of the texture."""
    data = bytearray()
    for ty in range(size):
        for tx in range(size):
            acc = 0.0
            for sy in range(SS):
                for sx in range(SS):
                    acc += coverage(tx + (sx + 0.5) / SS, ty + (sy + 0.5) / SS)
            a = int(round(max(0.0, min(1.0, acc / (SS * SS))) * 31))
            data.append(a << 3)
    return bytes(data)


def _smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def tex_crescent():
    # Outer disc minus an offset disc, opening to the upper right, with a halo
    # that follows the lit limb. Leaves a margin so billboards never clip.
    c, r_out = 32.0, 19.0
    cut_c, r_cut = (32.0 + 9.0, 32.0 - 6.0), 16.5

    def lit(x, y):
        d_out = math.hypot(x - c, y - c)
        d_cut = math.hypot(x - cut_c[0], y - cut_c[1])
        inside = 1.0 - _smoothstep(r_out - 0.75, r_out + 0.75, d_out)
        cut = 1.0 - _smoothstep(r_cut - 0.75, r_cut + 0.75, d_cut)
        return inside * (1.0 - cut), d_out, d_cut

    def cov(x, y):
        body, d_out, d_cut = lit(x, y)
        # Signed distance-ish to the crescent: outside the outer disc, or inside the cut
        dist = max(d_out - r_out, r_cut - d_cut)
        halo = 0.35 * (1.0 - _smoothstep(0.0, 9.0, dist)) if dist > 0 else 0.35
        return max(body, halo if body < 1.0 else 0.0)

    return _raster(64, cov)


def tex_glow():
    def cov(x, y):
        d = math.hypot(x - 16.0, y - 16.0) / 15.0
        core = 1.0 - _smoothstep(0.0, 0.35, d)
        soft = (1.0 - _smoothstep(0.0, 1.0, d)) ** 1.6
        return max(core, soft)

    return _raster(32, cov)


def tex_sparkle():
    def cov(x, y):
        dx, dy = abs(x - 8.0), abs(y - 8.0)
        # Thin diamond-tapered rays along both axes plus a round core
        ray_h = max(0.0, 1.0 - dx / 7.5) * max(0.0, 1.0 - dy / (1.4 * max(0.0, 1.0 - dx / 7.5) + 0.01))
        ray_v = max(0.0, 1.0 - dy / 7.5) * max(0.0, 1.0 - dx / (1.4 * max(0.0, 1.0 - dy / 7.5) + 0.01))
        core = 1.0 - _smoothstep(0.8, 2.6, math.hypot(dx, dy))
        return max(ray_h, ray_v, core)

    return _raster(16, cov)


def tex_ring():
    def cov(x, y):
        d = math.hypot(x - 32.0, y - 32.0)
        band = math.exp(-((d - 25.0) / 2.6) ** 2)
        inner = 0.25 * math.exp(-((d - 21.0) / 6.0) ** 2)
        return min(1.0, band + inner) if d < 31.5 else 0.0

    return _raster(64, cov)


# (name, size, generator). param = A5I3 | s | t | palColor0, like vanilla (e.g. 0x10336)
TEXTURES = [
    ('crescent', 64, tex_crescent),
    ('glow', 32, tex_glow),
    ('sparkle', 16, tex_sparkle),
    ('ring', 64, tex_ring),
]
TEX_CRESCENT, TEX_GLOW, TEX_SPARKLE, TEX_RING = range(4)

TEX_FMT_A5I3 = 6
PALETTE = struct.pack('<HH', 0x7FFF, 0x0000)


def pack_texture(size, data):
    log = {16: 1, 32: 2, 64: 3}[size]
    param = TEX_FMT_A5I3 | (log << 4) | (log << 8) | (1 << 16)
    assert len(data) == size * size
    total = 32 + len(data) + len(PALETTE)
    header = struct.pack(
        '<8I',
        SPA_MAGIC,
        param,
        len(data),
        32 + len(data),  # palette offset from the start of this header
        len(PALETTE),
        total,  # unused0; vanilla files store the resource size here too
        0,
        total,
    )
    return header + data + PALETTE


# --- emitters --------------------------------------------------------------------

PINK = rgb(31, 18, 26)
PALE_PINK = rgb(31, 25, 30)
MOON_WHITE = rgb(31, 31, 26)
LAVENDER = rgb(26, 23, 31)
WHITE = rgb(31, 31, 31)


def build_emitters():
    e = []

    # 0: crescent moon above the user
    e.append(emitter(
        emission_type=EMIT_POINT,
        flags=F_SELF_MAINTAINING,
        base_pos=(0.0, 2.6, 0.0),
        axis=(0.0, 1.0, 0.0),
        vel_axis=0.015,  # ~1 unit of rise over its life
        color=LAVENDER,
        scale=1.6,
        emitter_life=1,
        particle_life=72,
        texture=TEX_CRESCENT,
        scale_anim=(0.55, 1.0, 1.12, 45, 200),
        color_anim=(MOON_WHITE, PINK, 50, 120, 200, True),
        alpha_anim=(0, 31, 0, 40, 205),
        child={
            'flags': CF_SCALE_ANIM | CF_ALPHA_ANIM | CF_USE_CHILD_COLOR,
            'rand_vel': 0.35,
            'end_scale': 0.1,
            'life': 18,
            'vel_ratio': 0,
            'scale_ratio': 30,
            'color': PALE_PINK,
            'count': 1,
            'delay': 70,  # start after ~27% of the moon's life
            'interval': 3,
            'texture': TEX_SPARKLE,
        },
    ))

    # 1: moonlight motes swirling into the user
    e.append(emitter(
        emission_type=EMIT_SPHERE_SURFACE,
        flags=F_SELF_MAINTAINING | F_RANDOM_INIT_ANGLE,
        radius=4.0,
        count=2.0,
        color=LAVENDER,
        scale=0.45,
        emitter_life=30,
        particle_life=22,
        rand_scale=90,
        rand_life=40,
        emission_interval=2,
        texture=TEX_SPARKLE,
        scale_anim=(0.6, 1.0, 0.3, 60, 180),
        color_anim=(WHITE, PALE_PINK, 40, 110, 200, True),
        alpha_anim=(0, 31, 4, 50, 190),
        spin=(0x300, SPIN_AXIS_Y),
        convergence=((0.0, 0.0, 0.0), 0.09),
    ))

    # 2: charge orb swelling at the user
    e.append(emitter(
        emission_type=EMIT_POINT,
        flags=F_SELF_MAINTAINING,
        color=PINK,
        scale=1.0,
        start_delay=6,
        emitter_life=1,
        particle_life=42,
        texture=TEX_GLOW,
        scale_anim=(0.15, 1.0, 1.15, 160, 215),
        color_anim=(WHITE, PINK, 20, 120, 210, True),
        alpha_anim=(8, 31, 0, 60, 225),
    ))

    # 3: projectile (moved by Func_MoveEmitterA2BLinear), flash_cannon e0 semantics
    e.append(emitter(
        emission_type=EMIT_CIRCLE_BORDER,
        flags=F_FOLLOW_EMITTER,  # not self-maintaining, same as flash_cannon e0
        axis=(1.0, 0.0, 0.0),
        color=PALE_PINK,
        scale=0.95,
        emitter_life=1,
        particle_life=16,
        texture=TEX_GLOW,
        loop_frames=3,
        scale_anim=(0.9, 1.2, 1.5, 128, 128),
        color_anim=(WHITE, PINK, 0, 100, 230, True),
        alpha_anim=(1, 31, 1, 26, 230),
        child={
            'flags': CF_SCALE_ANIM | CF_ALPHA_ANIM | CF_FOLLOW_EMITTER | CF_USE_CHILD_COLOR,
            'rand_vel': 0.0,
            'end_scale': 0.06,
            'life': 12,
            'vel_ratio': 0,
            'scale_ratio': 60,
            'color': PALE_PINK,
            'count': 1,
            'delay': 0,
            'interval': 1,
            'texture': TEX_SPARKLE,
        },
    ))

    # 4: impact starburst
    e.append(emitter(
        emission_type=EMIT_POINT,
        flags=F_SELF_MAINTAINING | F_ROTATION | F_RANDOM_INIT_ANGLE,
        count=4.0,
        color=PALE_PINK,
        vel_pos=0.9,
        vel_axis=0.12,
        scale=0.7,
        rotation=(-1200, 1200),
        emitter_life=4,
        particle_life=24,
        rand_scale=60,
        rand_life=50,
        rand_vel=60,
        air_resistance=30,
        texture=TEX_SPARKLE,
        scale_anim=(1.6, 1.0, 0.25, 30, 150),
        color_anim=(WHITE, PINK, 30, 90, 180, True),
        alpha_anim=(31, 31, 0, 1, 150),
    ))

    # 5: impact halo ring + core flash (one ring particle, one core particle)
    e.append(emitter(
        emission_type=EMIT_POINT,
        flags=F_SELF_MAINTAINING,
        color=PINK,
        scale=1.3,
        emitter_life=1,
        particle_life=24,
        texture=TEX_RING,
        scale_anim=(0.25, 1.4, 2.6, 70, 110),
        color_anim=(WHITE, PINK, 20, 60, 160, True),
        alpha_anim=(31, 28, 0, 40, 120),
        child={
            'flags': CF_SCALE_ANIM | CF_ALPHA_ANIM | CF_FOLLOW_EMITTER | CF_USE_CHILD_COLOR,
            'rand_vel': 0.0,
            'end_scale': 0.2,
            'life': 12,
            'vel_ratio': 0,
            'scale_ratio': 200,
            'color': WHITE,
            'count': 1,
            'delay': 0,
            'interval': 255,  # emit once, at age 0
            'texture': TEX_GLOW,
        },
    ))
    return e


# --- file assembly -------------------------------------------------------------


def build():
    emitters = build_emitters()
    res = b''.join(emitters)
    tex = b''.join(pack_texture(size, gen()) for _, size, gen in TEXTURES)
    header = struct.pack(
        '<IIHHIIIII',
        SPA_MAGIC,
        SPA_VERSION,
        len(emitters),
        len(TEXTURES),
        0,
        len(res),
        len(tex),
        0x20 + len(res),
        0,
    )
    return header + res + tex


# --- independent verification --------------------------------------------------

BLOCKS = [(8, 12), (9, 12), (10, 8), (11, 12), (16, 20)]
BEHAVIORS = [(24, 8), (25, 8), (26, 16), (27, 4), (28, 8), (29, 16)]


def verify(d):
    """Re-parses a .spa the way the SPL loader walks it and checks the invariants
    the runtime relies on. Returns a list of (index, summary) for the emitters."""
    magic, ver, rc, tc, _, rsz, tsz, toff, _ = struct.unpack_from('<IIHHIIIII', d, 0)
    assert magic == SPA_MAGIC and ver == SPA_VERSION
    off = 0x20
    summary = []
    for i in range(rc):
        hdr = struct.unpack_from('<I3iiii3hHiiihHhhHHHHIIIIhhI', d, off)
        fl = hdr[0]
        emit_life, ptcl_life = hdr[20], hdr[21]
        misc0, misc1 = hdr[23], hdr[24]
        tex_index = misc0 >> 24
        loop_frames = misc1 & 0xFF
        assert tex_index < tc, (i, tex_index)
        assert loop_frames >= 1, i
        assert ptcl_life >= 1, i
        blk = off + 88
        for bit, size in BLOCKS:
            if fl >> bit & 1:
                if bit == 8:  # scale curve out must not be 255
                    assert d[blk + 7] < 255, i
                if bit == 10:
                    assert d[blk + 5] < 255, i
                if bit == 11:
                    raise AssertionError('tex anim not expected')
                if bit == 16:
                    child_tex = struct.unpack_from('<I', d, blk + 12)[0] >> 24
                    assert child_tex < tc, (i, child_tex)
                    assert ptcl_life >= 2, i
                blk += size
        for bit, size in BEHAVIORS:
            if fl >> bit & 1:
                blk += size
        summary.append((i, fl, emit_life, ptcl_life, tex_index, hdr[15], blk - off))
        off = blk
    assert off == 0x20 + rsz == toff, (off, rsz, toff)
    for i in range(tc):
        tid, param, tsize, poff, psize, u0, u1, rsize = struct.unpack_from('<8I', d, off)
        fmt, s, t = param & 15, 8 << ((param >> 4) & 15), 8 << ((param >> 8) & 15)
        assert tid == SPA_MAGIC and fmt == TEX_FMT_A5I3
        assert tsize == s * t and poff == 32 + tsize and rsize == 32 + tsize + psize
        assert all(b & 7 == 0 for b in d[off + 32:off + 32 + tsize])
        assert any(b for b in d[off + 32:off + 32 + tsize])
        off += rsize
    assert off == toff + tsz == len(d), (off, toff, tsz, len(d))
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true', help='verify the checked-in file matches the generator')
    ap.add_argument('--preview', metavar='DIR', help='also dump textures as PGM images to DIR')
    args = ap.parse_args()

    data = build()
    assert data == build(), 'generator is not deterministic'
    verify(data)

    if args.preview:
        pdir = pathlib.Path(args.preview)
        pdir.mkdir(parents=True, exist_ok=True)
        for name, size, gen in TEXTURES:
            px = bytes((b >> 3) * 255 // 31 for b in gen())
            (pdir / f'{name}.pgm').write_bytes(b'P5 %d %d 255\n' % (size, size) + px)

    if args.check:
        on_disk = OUT_PATH.read_bytes()
        verify(on_disk)
        if on_disk != data:
            print(f'{OUT_PATH} is out of date; re-run {pathlib.Path(__file__).name}', file=sys.stderr)
            return 1
        print(f'{OUT_PATH.relative_to(REPO)} is up to date ({len(data)} bytes)')
        return 0

    OUT_PATH.write_bytes(data)
    print(f'wrote {OUT_PATH.relative_to(REPO)} ({len(data)} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())

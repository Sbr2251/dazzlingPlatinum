"""Builds res/battle/particles/mega_evolution.spa, the particles for the Mega Evolution sequence.

Usage: python3 tools/mega_evolution/make_mega_evolution_spa.py  (safe to re-run)

It is played in two parts, over AffinePulse's two stages (subscript_mega_evolution.s):
  common_anims/mega_evolution_charge.s  (emitters 0-4)
    0, 1: rainbow streaks spiralling in onto the Pokemon (three hues each, picked per particle)
    2:    orbs swirling round it and tightening into a cocoon
    3:    the light sphere at the centre, swelling and then collapsing with the squeezed sprite
    4:    a magenta halo pulsing round the sphere
  common_anims/mega_evolution.s  (emitters 5-13)
    5:    the white flash as the sphere breaks
    6, 7: two shockwave rings
    8, 9: rainbow shards of the shell flying outward
    10:   sparkles scattered round the new form
    11:   the soft glow behind the Mega symbol
    12:   the Mega symbol itself, stamped in above the Pokemon, held, then faded
    13:   twinkles round the symbol
Two stock greyscale textures are copied from absorb.spa. The ring, the shard and the Mega symbol are drawn
here: the ring and shard as a quarter that the hardware mirrors into a whole, the symbol in colour.
"""
import colorsys
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "totem_aura"))

import spa  # noqa: E402

PARTICLES = os.path.join(HERE, "..", "..", "res/battle/particles")
OUT = os.path.join(PARTICLES, "mega_evolution.spa")

TEX_GLOW, TEX_STAR, TEX_RING, TEX_SHARD, TEX_SYMBOL = range(5)

FMT_A3I5, FMT_A5I3 = 1, 6
REPEAT_FLIP_ST = 0xF << 12  # repeat and mirror in S and T, so a quarter texture draws as a whole
PAL_COLOR0 = 1 << 16


def rgb(r, g, b):
    return r | g << 5 | b << 10


WHITE = rgb(31, 31, 31)
PALE_PINK = rgb(31, 26, 31)
MAGENTA = rgb(29, 10, 31)
VIOLET = rgb(18, 8, 31)
RED = rgb(31, 8, 10)
ORANGE = rgb(31, 19, 4)
YELLOW = rgb(31, 30, 8)
GREEN = rgb(10, 31, 12)
CYAN = rgb(8, 28, 31)
BLUE = rgb(10, 14, 31)
GOLD = rgb(31, 27, 12)


def fx(v):
    return int(round(v * 4096))


def misc(interval, texture, tile=0, scale_dir=0, air=0x80, dbb=0.0):
    """tile: 1 draws the texture mirrored twice in S and T (for the quarter textures)."""
    return (bytes((interval, 0x1F, air, texture, 1)) + struct.pack("<H", fx(dbb))
            + bytes((tile | tile << 2 | scale_dir << 4,)) + b"\x00\x00\x37\x00")


def scale_anim(start, mid, end, curve_in, curve_out):
    return struct.pack("<hhhBBHH", fx(start), fx(mid), fx(end), curve_in, curve_out, 0, 0)


def color_anim(start, end, curve_in=0, peak=0x80, curve_out=0xFF, random_start=False):
    """random_start: each particle keeps one of start, the resource colour or end, picked at emission."""
    return struct.pack("<HHBBBBHH", start, end, curve_in, peak, curve_out, 0, 0b100 | int(random_start), 0)


def alpha_anim(start, mid, end, curve_in, curve_out, random_range=0):
    return struct.pack("<HHBBH", start | mid << 5 | end << 10, random_range, curve_in, curve_out, 0)


def attenuation(scale=0, life=0, vel=0):
    return bytes((scale, life, vel, 0))


def resource(**kw):
    flags = {"circleAxis": 0, "hasScaleAnim": 1, "hasColorAnim": 1, "hasAlphaAnim": 1, "selfMaintaining": 1}
    flags.update(kw.pop("flags", {}))
    r = {
        "flags": flags, "posX": 0, "posY": 0, "posZ": 0, "emissionCount": fx(1), "radius": 0, "length": 0,
        "axisX": 0, "axisY": fx(1), "axisZ": 0, "color": WHITE, "initVelPosAmplifier": 0,
        "initVelAxisAmplifier": 0, "baseScale": fx(1), "aspectRatio": fx(1), "startDelay": 0, "minRotation": 0,
        "maxRotation": 0, "initAngle": 0, "reserved": 0, "emitterLifeTime": 1, "particleLifeTime": 20,
        "randomAttenuation": attenuation(), "polygonX": 0, "polygonY": 0, "userData": b"\0" * 4,
    }
    r.update(kw)
    return r


def texture(fmt, size_log, data, palette, param_extra=0):
    """size_log: texture side as 8 << size_log. palette: list of RGB555 colours."""
    pal = struct.pack(f"<{len(palette)}H", *palette)
    param = fmt | size_log << 4 | size_log << 8 | param_extra
    size = 32 + len(data) + len(pal)
    return struct.pack("<8I", 0, param, len(data), 32 + len(data), len(pal), size, 0, size) + data + pal


def supersample(side, coverage, n=4):
    """Averages coverage(x, y) over n*n points per texel; x and y run over [-1, 1], y up."""
    out = []
    for ty in range(side):
        row = []
        for tx in range(side):
            acc = 0.0
            for sy in range(n):
                for sx in range(n):
                    x = (tx + (sx + 0.5) / n) / side * 2 - 1
                    y = 1 - (ty + (sy + 0.5) / n) / side * 2
                    acc += coverage(x, y)
            row.append(acc / (n * n))
        out.append(row)
    return out


def a5i3_quarter(side_log, coverage):
    """A white A5I3 quarter whose bottom-right corner is the centre of the mirrored whole.
    coverage(dx, dy) gets offsets from that centre in quarter widths (0..1)."""
    side = 8 << side_log
    grid = supersample(side, lambda x, y: coverage((1 - x) / 2, (1 + y) / 2))
    data = bytes(min(31, int(round(a * 31))) << 3 for row in grid for a in row)
    return texture(FMT_A5I3, side_log, data, [WHITE, 0], REPEAT_FLIP_ST | PAL_COLOR0)


def ring_coverage(dx, dy):
    d = math.hypot(dx, dy)
    return max(0.0, 1 - abs(d - 0.8) / 0.17) ** 1.5


def shard_coverage(dx, dy):
    # a tall rhombus, brightest along its spine
    d = dx / 0.55 + dy
    return 0.0 if d > 1 else 0.55 + 0.45 * (1 - dx / 0.55)


# The Mega symbol: a teardrop, tip up and to the right, with a rainbow band inside a dark outline and a
# white core crossed by a two-stranded helix. Shapes are signed distances in texture units ([-1, 1], y up).
SYMBOL_CENTRE = (-0.08, -0.27)  # centre of the round part
SYMBOL_RADIUS = 0.62
SYMBOL_TIP_DISTANCE = 1.12
SYMBOL_TIP_ANGLE = math.radians(58)
SYMBOL_OUTLINE_WIDTH = 0.09
SYMBOL_BAND_WIDTH = 0.15
SYMBOL_HELIX_WIDTH = 0.065
SYMBOL_OUTLINE = (3, 3, 12)
SYMBOL_CORE = (31, 31, 31)
SYMBOL_HELIX = (14, 4, 22)
SYMBOL_HUES = 28


def hue_rgb(h):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, 0.8, 1.0)
    return (round(r * 31), round(g * 31), round(b * 31))


def segment_distance(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy)))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def _symbol_geometry():
    cx, cy = SYMBOL_CENTRE
    ux, uy = math.cos(SYMBOL_TIP_ANGLE), math.sin(SYMBOL_TIP_ANGLE)
    tip = (cx + ux * SYMBOL_TIP_DISTANCE, cy + uy * SYMBOL_TIP_DISTANCE)
    spread = math.pi / 2 - math.asin(SYMBOL_RADIUS / SYMBOL_TIP_DISTANCE)
    tangents = [(cx + SYMBOL_RADIUS * math.cos(SYMBOL_TIP_ANGLE + s * spread),
                 cy + SYMBOL_RADIUS * math.sin(SYMBOL_TIP_ANGLE + s * spread)) for s in (1, -1)]
    steps = 48
    # strands in the local frame: v along the tip axis, w across it
    strands = [[(0.3 - 0.6 * i / steps, sign * 0.14 * math.sin(math.pi * 1.5 * i / steps)) for i in range(steps + 1)]
               for sign in (1, -1)]
    return (ux, uy), [tip] + tangents, strands


SYMBOL_AXIS, SYMBOL_CONE, SYMBOL_STRANDS = _symbol_geometry()


def symbol_distance(x, y):
    """Signed distance to the teardrop's edge, negative inside."""
    cx, cy = SYMBOL_CENTRE
    circle = math.hypot(x - cx, y - cy) - SYMBOL_RADIUS
    pts = SYMBOL_CONE
    edge = min(segment_distance(x, y, *pts[i], *pts[(i + 1) % 3]) for i in range(3))
    sides = [(pts[(i + 1) % 3][0] - pts[i][0]) * (y - pts[i][1]) - (pts[(i + 1) % 3][1] - pts[i][1]) * (x - pts[i][0])
             for i in range(3)]
    inside = all(s >= 0 for s in sides) or all(s <= 0 for s in sides)
    return min(circle, -edge if inside else edge)


def symbol_sample(x, y):
    """Returns an RGB triple (5-bit channels) or None where the texel is empty."""
    d = symbol_distance(x, y)
    if d > 0:
        return None
    if d > -SYMBOL_OUTLINE_WIDTH:
        return SYMBOL_OUTLINE
    cx, cy = SYMBOL_CENTRE
    dx, dy = x - cx, y - cy
    band = hue_rgb(0.15 - ((math.atan2(dy, dx) - SYMBOL_TIP_ANGLE) % (2 * math.pi)) / (2 * math.pi))
    v = dx * SYMBOL_AXIS[0] + dy * SYMBOL_AXIS[1]
    w = -dx * SYMBOL_AXIS[1] + dy * SYMBOL_AXIS[0]
    if d > -SYMBOL_OUTLINE_WIDTH - SYMBOL_BAND_WIDTH or v > 0.5:
        return band
    for strand in SYMBOL_STRANDS:
        if any(segment_distance(v, w, *strand[i], *strand[i + 1]) < SYMBOL_HELIX_WIDTH for i in range(len(strand) - 1)):
            return SYMBOL_HELIX
    return SYMBOL_CORE


def symbol_texture():
    """32x32 A3I5: 3-bit coverage alpha, 5-bit index into outline, core, helix and a ring of hues."""
    side, n = 32, 4
    palette = [SYMBOL_OUTLINE, SYMBOL_CORE, SYMBOL_HELIX] + [hue_rgb(0.15 - i / SYMBOL_HUES) for i in range(SYMBOL_HUES)]
    palette.append((0, 0, 0))  # unused, pads the palette to 32 entries
    data = bytearray()
    for ty in range(side):
        for tx in range(side):
            hits = []
            for sy in range(n):
                for sx in range(n):
                    c = symbol_sample((tx + (sx + 0.5) / n) / side * 2 - 1, 1 - (ty + (sy + 0.5) / n) / side * 2)
                    if c is not None:
                        hits.append(c)
            alpha = round(len(hits) / (n * n) * 7)
            if alpha == 0:
                data.append(0)
                continue
            avg = [sum(c[i] for c in hits) / len(hits) for i in range(3)]
            index = min(range(len(palette) - 1), key=lambda i: sum((palette[i][j] - avg[j]) ** 2 for j in range(3)))
            data.append(alpha << 5 | index)
    return texture(FMT_A3I5, 2, bytes(data), [rgb(*c) for c in palette])


def build():
    absorb = spa.read(os.path.join(PARTICLES, "absorb.spa"))
    textures = [absorb["textures"][0], absorb["textures"][1], a5i3_quarter(1, ring_coverage),
                a5i3_quarter(0, shard_coverage), symbol_texture()]

    # Timings are in particle frames, which advance at 30 Hz like AffinePulse's ticks.
    # --- charge: every particle is gone by frame 8. The animation starts about 8 ticks into AffinePulse stage 0
    # (20 ticks), and its End turns blending off, so it has to finish before the stage's last dim write or the
    # screen would undim while the form changes. The sphere collapses with the squeezed sprite ---
    def streaks(colors, delay):
        return resource(
            flags={"emissionType": 2, "drawType": 1, "hasSpinBehavior": 1},
            radius=fx(2.4), emissionCount=fx(3), color=colors[1], initVelPosAmplifier=fx(-0.3), baseScale=fx(0.13),
            startDelay=delay, emitterLifeTime=3, particleLifeTime=5, randomAttenuation=attenuation(vel=0x30),
            misc=misc(1, TEX_GLOW, tile=1, dbb=3.0),
            scaleAnim=scale_anim(1.0, 1.0, 0.5, 0x00, 0xA0),
            colorAnim=color_anim(colors[0], colors[2], random_start=True),
            alphaAnim=alpha_anim(8, 31, 8, 0x30, 0xC0),
            spin=struct.pack("<HH", 0x0500, 2),
        )

    streaks_a = streaks((RED, YELLOW, CYAN), 0)
    streaks_b = streaks((ORANGE, GREEN, VIOLET), 0)
    cocoon = resource(
        flags={"emissionType": 2, "hasSpinBehavior": 1, "hasConvergenceBehavior": 1},
        radius=fx(1.4), emissionCount=fx(2), color=MAGENTA, baseScale=fx(0.2), startDelay=1, emitterLifeTime=2,
        particleLifeTime=5, randomAttenuation=attenuation(scale=0x40), misc=misc(1, TEX_GLOW, tile=1),
        scaleAnim=scale_anim(0.4, 1.0, 0.6, 0x30, 0xC0),
        colorAnim=color_anim(CYAN, YELLOW, random_start=True),
        alphaAnim=alpha_anim(8, 28, 0, 0x40, 0xB0),
        spin=struct.pack("<HH", 0x0900, 2),
        convergence=struct.pack("<iiihH", 0, 0, 0, fx(0.15), 0),
    )
    sphere = resource(
        flags={"emissionType": 0}, posZ=fx(0.5), color=WHITE, baseScale=fx(1.35), particleLifeTime=8,
        misc=misc(1, TEX_GLOW, tile=1),
        scaleAnim=scale_anim(0.2, 1.0, 0.05, 0x60, 0xB0),
        colorAnim=color_anim(PALE_PINK, WHITE, 0x00, 0x80, 0xFF),
        alphaAnim=alpha_anim(10, 30, 30, 0x40, 0xFF),
    )
    halo = resource(
        flags={"emissionType": 0}, posZ=fx(0.4), color=MAGENTA, baseScale=fx(2.0), startDelay=1,
        emitterLifeTime=2, particleLifeTime=5, misc=misc(2, TEX_GLOW, tile=1),
        scaleAnim=scale_anim(0.7, 1.0, 1.1, 0x40, 0xC0),
        colorAnim=color_anim(MAGENTA, VIOLET, 0x00, 0x80, 0xFF),
        alphaAnim=alpha_anim(0, 12, 0, 0x50, 0x90),
    )

    # --- burst and symbol: done by frame 58. AffinePulse stage 1 is 22 ticks; the rest replaces the shiny
    # sparkle animation that used to follow it (about 60 ticks), so the sequence ends sooner than before ---
    flash = resource(
        flags={"emissionType": 0}, posZ=fx(0.6), color=WHITE, baseScale=fx(3.4), particleLifeTime=12,
        misc=misc(1, TEX_GLOW, tile=1),
        scaleAnim=scale_anim(0.3, 1.0, 1.1, 0x30, 0xC0),
        colorAnim=color_anim(WHITE, PALE_PINK, 0x00, 0x80, 0xFF),
        alphaAnim=alpha_anim(31, 31, 0, 0x00, 0x40),
    )

    def ring(color, end_color, scale, delay):
        return resource(
            flags={"emissionType": 0}, posZ=fx(0.5), color=color, baseScale=fx(scale), startDelay=delay,
            particleLifeTime=12, misc=misc(1, TEX_RING, tile=1),
            scaleAnim=scale_anim(0.15, 0.75, 1.0, 0x90, 0xFF),
            colorAnim=color_anim(color, end_color, 0x00, 0x80, 0xFF),
            alphaAnim=alpha_anim(31, 28, 0, 0x60, 0x80),
        )

    ring_a = ring(WHITE, MAGENTA, 2.6, 0)
    ring_b = ring(CYAN, VIOLET, 3.4, 3)

    def shards(colors):
        return resource(
            flags={"emissionType": 2, "hasRotation": 1, "randomInitAngle": 1, "hasGravityBehavior": 1},
            radius=fx(0.5), emissionCount=fx(9), color=colors[1], initVelPosAmplifier=fx(0.22),
            baseScale=fx(0.26), minRotation=-2400, maxRotation=2400, particleLifeTime=20,
            randomAttenuation=attenuation(scale=0x60, life=0x40, vel=0x90), misc=misc(1, TEX_SHARD, tile=1, air=0x70),
            scaleAnim=scale_anim(1.0, 1.0, 0.4, 0x00, 0x90),
            colorAnim=color_anim(colors[0], colors[2], random_start=True),
            alphaAnim=alpha_anim(31, 31, 0, 0x00, 0x90),
            gravity=struct.pack("<hhhH", 0, fx(-0.006), 0, 0),
        )

    shards_a = shards((RED, YELLOW, CYAN))
    shards_b = shards((ORANGE, GREEN, VIOLET))
    sparkles = resource(
        flags={"emissionType": 5}, radius=fx(1.5), emissionCount=fx(2), posZ=fx(0.5), color=WHITE,
        baseScale=fx(0.3), startDelay=3, emitterLifeTime=14, particleLifeTime=12,
        randomAttenuation=attenuation(scale=0x50, life=0x30), misc=misc(2, TEX_STAR),
        scaleAnim=scale_anim(0.2, 1.0, 0.0, 0x50, 0xB0),
        colorAnim=color_anim(WHITE, GOLD, random_start=True),
        alphaAnim=alpha_anim(31, 31, 31, 0x00, 0xFF),
    )

    # the symbol arrives as the new form settles (stage 1 tick 14) and fades out by frame 58
    SYMBOL_Y, SYMBOL_DELAY, SYMBOL_LIFE = fx(1.9), 14, 44
    symbol_glow = resource(
        flags={"emissionType": 0}, posY=SYMBOL_Y, posZ=fx(0.6), color=MAGENTA, baseScale=fx(1.1),
        startDelay=SYMBOL_DELAY, particleLifeTime=SYMBOL_LIFE, misc=misc(1, TEX_GLOW, tile=1),
        scaleAnim=scale_anim(0.4, 1.0, 1.1, 0x20, 0xC0),
        colorAnim=color_anim(PALE_PINK, MAGENTA, 0x00, 0x40, 0xFF),
        alphaAnim=alpha_anim(0, 16, 0, 0x20, 0xB8),
    )
    symbol = resource(
        flags={"emissionType": 0}, posY=SYMBOL_Y, posZ=fx(0.7), color=WHITE, baseScale=fx(32 / 48),
        startDelay=SYMBOL_DELAY, particleLifeTime=SYMBOL_LIFE, misc=misc(1, TEX_SYMBOL),
        scaleAnim=scale_anim(2.2, 1.0, 1.0, 0x1C, 0xFF),
        colorAnim=color_anim(WHITE, WHITE),
        alphaAnim=alpha_anim(0, 31, 0, 0x1C, 0xC8),
    )
    symbol_twinkles = resource(
        flags={"emissionType": 2}, posY=SYMBOL_Y, posZ=fx(0.8), radius=fx(0.75), color=WHITE, baseScale=fx(0.25),
        startDelay=SYMBOL_DELAY + 5, emitterLifeTime=18, particleLifeTime=10,
        randomAttenuation=attenuation(scale=0x60), misc=misc(4, TEX_STAR),
        scaleAnim=scale_anim(0.0, 1.0, 0.0, 0x60, 0xA0),
        colorAnim=color_anim(WHITE, WHITE),
        alphaAnim=alpha_anim(31, 31, 31, 0x00, 0xFF),
    )

    resources = [streaks_a, streaks_b, cocoon, sphere, halo, flash, ring_a, ring_b, shards_a, shards_b, sparkles,
                 symbol_glow, symbol, symbol_twinkles]
    return {"magic": absorb["magic"], "version": absorb["version"], "resources": resources, "textures": textures}


def main():
    data = spa.write(build())
    open(OUT, "wb").write(data)
    assert spa.write(spa.read(OUT)) == data
    print(f"wrote {os.path.relpath(OUT)} ({len(data)} bytes)")


if __name__ == "__main__":
    main()

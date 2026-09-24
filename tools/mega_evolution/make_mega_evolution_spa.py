"""Builds res/battle/particles/mega_evolution.spa, the particles for the Mega Evolution sequence.

Usage: python3 tools/mega_evolution/make_mega_evolution_spa.py  (safe to re-run)

It is played by common_anims/mega_evolution.s, alongside AffinePulse (subscript_mega_evolution.s), in the style
of the X and Y games: an orb forms round the Pokemon, which glows white inside it, then the orb bursts and the
new form springs out.
  charge (emitters 0-7, from the charge cue)
    0, 1: rainbow streaks spiralling in onto the Pokemon (three hues each, picked per particle)
    2:    orbs swirling round it and tightening in
    3, 4: purple and pink ribbons circling the orb in opposite directions
    5:    the orb: a sprite-sized bubble with a white-pink rim and a see-through middle, held until the burst
    6:    a glow breathing round the orb
    7:    the orb's fill, turning opaque white at the end so the new form can be swapped in unseen
  burst (emitters 8-16, from the burst cue)
    8:    the white flash as the orb breaks
    9, 10: two shockwave rings
    11:   rainbow sparks flying outward
    12:   large pieces of the orb's shell flying apart
    13:   sparkles scattered round the new form
    14:   the soft glow behind the Mega symbol
    15:   the Mega symbol itself, stamped in above the Pokemon, held, then faded
    16:   twinkles round the symbol
Two stock greyscale textures are copied from absorb.spa. The ring, the shard, the orb, the fill, the ribbon and the
Mega symbol are drawn here: the round ones as a quarter that the hardware mirrors into a whole, the symbol in colour.
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "totem_aura"))

import spa  # noqa: E402

PARTICLES = os.path.join(HERE, "..", "..", "res/battle/particles")
OUT = os.path.join(PARTICLES, "mega_evolution.spa")

TEX_GLOW, TEX_STAR, TEX_RING, TEX_SHARD, TEX_SYMBOL, TEX_ORB, TEX_FILL, TEX_RIBBON = range(8)

FMT_A3I5, FMT_A5I3 = 1, 6
REPEAT_FLIP_ST = 0xF << 12  # repeat and mirror in S and T, so a quarter texture draws as a whole
PAL_COLOR0 = 1 << 16


def rgb(r, g, b):
    return r | g << 5 | b << 10


WHITE = rgb(31, 31, 31)
PALE_PINK = rgb(31, 26, 31)
ORB_PINK = rgb(31, 22, 30)
PINK = rgb(31, 14, 26)
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


def orb_coverage(dx, dy):
    # a bright rim with a soft outer glow, round a faint middle that thickens towards the edge like a bubble
    d = math.hypot(dx, dy)
    if d > 1:
        return 0.0
    rim = math.exp(-((d - ORB_RIM) / 0.05) ** 2)
    inner = 0.12 + 0.4 * (d / ORB_RIM) ** 3 if d < ORB_RIM else 0.0
    outer = 0.35 * math.exp(-(d - ORB_RIM) / 0.05) if d >= ORB_RIM else 0.0
    return min(1.0, rim + inner + outer)


def fill_coverage(dx, dy):
    d = math.hypot(dx, dy)
    return max(0.0, min(1.0, (ORB_RIM + 0.02 - d) / 0.12))


ORB_RIM = 0.86
RIBBON_RADIUS = 0.8
RIBBON_SPAN = math.radians(130)


def ribbon_texture():
    """32x32 A5I3: an arc a third of the way round, thickest and brightest in its middle and tapering to both ends."""
    def coverage(x, y):
        a = math.atan2(y, x) % (2 * math.pi)
        if a > RIBBON_SPAN:
            return 0.0
        taper = math.sin(math.pi * a / RIBBON_SPAN)
        width = 0.02 + 0.09 * taper ** 0.8
        return max(0.0, 1 - abs(math.hypot(x, y) - RIBBON_RADIUS) / width) * (0.4 + 0.6 * taper)

    grid = supersample(32, coverage)
    data = bytes(min(31, int(round(a * 31))) << 3 for row in grid for a in row)
    return texture(FMT_A5I3, 2, data, [WHITE, 0], PAL_COLOR0)


# The Mega symbol: a rainbow DNA helix, an S-shaped band cut by a triangle at each end and two rungs between them.
# Traced from the official symbol (Bulbapedia, File:Mega_Evolution_symbol.png), in its pixel units: 56 wide, 74
# tall, y down. The colours run diagonally, orange to yellow-green to sky blue to magenta, along x + 0.3y.
SYMBOL_SIZE = (56, 74)
SYMBOL_OUTLINE = [
    (29, 0), (36, 0), (35.5, 5), (34, 9), (33.2, 12), (33.2, 15), (34, 17.5), (35.5, 19.5), (37.5, 21.5),
    (40.5, 24.5), (44, 28), (48, 31.5), (51.5, 35), (54.3, 38.5), (55.8, 42), (56, 47), (55.8, 51.5),
    (55, 55), (53, 58), (50.5, 61.5), (47.5, 64.5), (44, 67.5), (39.5, 70.5), (34.5, 72.8), (29.5, 74), (27, 74),
    (26.5, 70), (27, 64.5), (26, 61), (24.5, 58), (22, 55.5), (18, 52.3), (13.5, 48.8), (9, 45), (5, 40.5),
    (2, 36), (0.3, 31), (0, 26), (1, 21.5), (3, 17.5), (5.3, 14.3), (8.3, 11), (12.3, 7.8), (17, 5), (22.5, 2.3),
]
SYMBOL_HOLES = [
    [(25.8, 9.8), (25.8, 19.8), (15.5, 15)],
    [(8.5, 22.5), (11, 20.8), (18, 23.8), (26, 26.8), (35, 30), (38.8, 32.6), (41.6, 35.4), (43.6, 38.6),
     (34, 36.2), (25, 33.2), (17, 30.2), (11, 27.2), (8.5, 25)],
    [(10, 34.5), (12, 36), (15, 37), (18, 38), (21, 39), (26, 41), (30, 42.5), (35, 44), (40, 45.2), (44, 46.2),
     (47.6, 47), (47.6, 53.2), (45, 52.6), (40, 51.2), (36, 50.2), (30, 48.6), (26, 47.2), (19, 44.2),
     (15, 41.2), (12, 38.6), (10.5, 36.5)],
    [(32.6, 56.5), (32.6, 63.6), (41.5, 59)],
]
SYMBOL_STOPS = [(8, (27, 18, 8)), (16, (26, 20, 8)), (24, (23, 23, 9)), (32, (20, 24, 12)), (40, (16, 23, 20)),
                (48, (12, 22, 27)), (56, (17, 17, 23)), (64, (22, 11, 19)), (72, (25, 8, 17))]


def point_in_polygon(poly, x, y):
    inside = False
    for i in range(len(poly)):
        (ax, ay), (bx, by) = poly[i], poly[i - 1]
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            inside = not inside
    return inside


def symbol_gradient(t):
    stops = SYMBOL_STOPS
    t = max(stops[0][0], min(stops[-1][0], t))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return tuple(c0[i] + (c1[i] - c0[i]) * f for i in range(3))


def symbol_sample(x, y):
    """Returns an RGB triple (5-bit channels) or None where the texel is empty. x and y are in [-1, 1], y up."""
    w, h = SYMBOL_SIZE
    scale = h / 31  # symbol pixels per texel: the symbol is 31 texels tall, centred in the 32x32 texture
    sx = ((x + 1) * 16 - 16) * scale + w / 2
    sy = ((1 - y) * 16 - 16) * scale + h / 2
    if not point_in_polygon(SYMBOL_OUTLINE, sx, sy) or any(point_in_polygon(hole, sx, sy) for hole in SYMBOL_HOLES):
        return None
    return symbol_gradient(sx + 0.3 * sy)


def symbol_texture():
    """32x32 A3I5: 3-bit coverage alpha, 5-bit index into 31 steps along the symbol's gradient."""
    side, n = 32, 4
    first, last = SYMBOL_STOPS[0][0], SYMBOL_STOPS[-1][0]
    palette = [symbol_gradient(first + (last - first) * i / 30) for i in range(31)]
    palette = [tuple(round(v) for v in c) for c in palette]
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
                a5i3_quarter(0, shard_coverage), symbol_texture(), a5i3_quarter(2, orb_coverage),
                a5i3_quarter(1, fill_coverage), ribbon_texture()]

    # Timings are in particle frames, which advance at 30 Hz like AffinePulse's ticks. The charge emitters start at
    # the charge cue and the burst emitters at the burst cue, CHARGE frames later (the Delay in mega_evolution.s).
    CHARGE = 36
    ORB_SCALE = 3.2  # about the size of a battle sprite

    # --- charge: the orb forms round the Pokemon and holds until the burst, with ribbons of light circling it.
    # AffinePulse hides the Pokemon under the fill at frame 30 and swaps in the new form ---
    def streaks(colors):
        return resource(
            flags={"emissionType": 2, "drawType": 1, "hasSpinBehavior": 1},
            radius=fx(2.6), emissionCount=fx(2), color=colors[1], initVelPosAmplifier=fx(-0.3), baseScale=fx(0.13),
            emitterLifeTime=CHARGE - 8, particleLifeTime=6, randomAttenuation=attenuation(vel=0x30),
            misc=misc(2, TEX_GLOW, tile=1, dbb=3.0),
            scaleAnim=scale_anim(1.0, 1.0, 0.5, 0x00, 0xA0),
            colorAnim=color_anim(colors[0], colors[2], random_start=True),
            alphaAnim=alpha_anim(8, 31, 8, 0x30, 0xC0),
            spin=struct.pack("<HH", 0x0500, 2),
        )

    streaks_a = streaks((RED, YELLOW, CYAN))
    streaks_b = streaks((ORANGE, GREEN, VIOLET))
    cocoon = resource(
        flags={"emissionType": 2, "hasSpinBehavior": 1, "hasConvergenceBehavior": 1},
        radius=fx(1.6), emissionCount=fx(2), color=MAGENTA, baseScale=fx(0.2), startDelay=2,
        emitterLifeTime=CHARGE - 12, particleLifeTime=7, randomAttenuation=attenuation(scale=0x40),
        misc=misc(2, TEX_GLOW, tile=1),
        scaleAnim=scale_anim(0.4, 1.0, 0.6, 0x30, 0xC0),
        colorAnim=color_anim(CYAN, YELLOW, random_start=True),
        alphaAnim=alpha_anim(8, 28, 0, 0x40, 0xB0),
        spin=struct.pack("<HH", 0x0900, 2),
        convergence=struct.pack("<iiihH", 0, 0, 0, fx(0.12), 0),
    )

    def ribbons(colors, scale, rotation, delay):
        return resource(
            flags={"emissionType": 0, "hasRotation": 1, "randomInitAngle": 1}, posZ=fx(0.6), color=colors[1],
            baseScale=fx(scale), minRotation=rotation[0], maxRotation=rotation[1], startDelay=delay,
            emitterLifeTime=CHARGE - 4 - delay, particleLifeTime=12, randomAttenuation=attenuation(scale=0x20),
            misc=misc(4, TEX_RIBBON),
            scaleAnim=scale_anim(0.9, 1.0, 1.05, 0x40, 0xC0),
            colorAnim=color_anim(colors[0], colors[2], random_start=True),
            alphaAnim=alpha_anim(0, 26, 0, 0x50, 0xA0),
        )

    ribbons_a = ribbons((MAGENTA, PINK, PALE_PINK), ORB_SCALE * 1.15, (0x0700, 0x0A00), 2)
    ribbons_b = ribbons((VIOLET, MAGENTA, PINK), ORB_SCALE * 1.3, (-0x0A00, -0x0700), 4)
    orb = resource(
        flags={"emissionType": 0}, posZ=fx(0.5), color=ORB_PINK, baseScale=fx(ORB_SCALE), particleLifeTime=CHARGE,
        misc=misc(1, TEX_ORB, tile=1),
        scaleAnim=scale_anim(0.5, 1.0, 1.0, 0x48, 0xFF),
        colorAnim=color_anim(MAGENTA, WHITE, 0x00, 0x48, 0xE0),
        alphaAnim=alpha_anim(0, 31, 31, 0x48, 0xFF),
    )
    orb_pulse = resource(
        flags={"emissionType": 0}, posZ=fx(0.4), color=MAGENTA, baseScale=fx(ORB_SCALE * 1.2), startDelay=6,
        emitterLifeTime=CHARGE - 12, particleLifeTime=8, misc=misc(8, TEX_ORB, tile=1),
        scaleAnim=scale_anim(0.9, 1.0, 1.1, 0x40, 0xFF),
        colorAnim=color_anim(PINK, VIOLET, 0x00, 0x80, 0xFF),
        alphaAnim=alpha_anim(0, 14, 0, 0x60, 0x80),
    )
    # opaque from frame 29, just before AffinePulse hides the Pokemon, until the burst
    orb_fill = resource(
        flags={"emissionType": 0, "hasScaleAnim": 0}, posZ=fx(0.45), color=WHITE, baseScale=fx(ORB_SCALE), startDelay=16,
        particleLifeTime=CHARGE - 16, misc=misc(1, TEX_FILL, tile=1),
        colorAnim=color_anim(PALE_PINK, WHITE, 0x00, 0x80, 0xFF),
        alphaAnim=alpha_anim(0, 31, 31, 0xA0, 0xFF),
    )

    # --- burst and symbol: done by frame 58 after the burst cue. AffinePulse's reveal is about 22 ticks; the rest
    # replaces the shiny sparkle animation that used to follow it (about 60 ticks) ---
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

    shards = resource(
        flags={"emissionType": 2, "hasRotation": 1, "randomInitAngle": 1, "hasGravityBehavior": 1},
        radius=fx(0.5), emissionCount=fx(12), color=YELLOW, initVelPosAmplifier=fx(0.24),
        baseScale=fx(0.24), minRotation=-2400, maxRotation=2400, particleLifeTime=18,
        randomAttenuation=attenuation(scale=0x60, life=0x40, vel=0x90), misc=misc(1, TEX_SHARD, tile=1, air=0x70),
        scaleAnim=scale_anim(1.0, 1.0, 0.4, 0x00, 0x90),
        colorAnim=color_anim(RED, CYAN, random_start=True),
        alphaAnim=alpha_anim(31, 31, 0, 0x00, 0x90),
        gravity=struct.pack("<hhhH", 0, fx(-0.006), 0, 0),
    )
    # the orb's shell breaking into a handful of big pieces from round its rim
    shell = resource(
        flags={"emissionType": 2, "hasRotation": 1, "randomInitAngle": 1, "hasGravityBehavior": 1},
        radius=fx(ORB_SCALE * 0.4), emissionCount=fx(7), color=ORB_PINK, initVelPosAmplifier=fx(0.14),
        baseScale=fx(0.65), minRotation=-1200, maxRotation=1200, particleLifeTime=20,
        randomAttenuation=attenuation(scale=0x40, life=0x30, vel=0x50), misc=misc(1, TEX_SHARD, tile=1, air=0x78),
        scaleAnim=scale_anim(1.0, 1.0, 0.6, 0x00, 0xA0),
        colorAnim=color_anim(WHITE, PINK, 0x00, 0x60, 0xFF),
        alphaAnim=alpha_anim(31, 28, 0, 0x60, 0xA0),
        gravity=struct.pack("<hhhH", 0, fx(-0.004), 0, 0),
    )
    sparkles = resource(
        flags={"emissionType": 5}, radius=fx(1.5), emissionCount=fx(2), posZ=fx(0.5), color=WHITE,
        baseScale=fx(0.3), startDelay=3, emitterLifeTime=14, particleLifeTime=12,
        randomAttenuation=attenuation(scale=0x50, life=0x30), misc=misc(2, TEX_STAR),
        scaleAnim=scale_anim(0.2, 1.0, 0.0, 0x50, 0xB0),
        colorAnim=color_anim(WHITE, GOLD, random_start=True),
        alphaAnim=alpha_anim(31, 31, 31, 0x00, 0xFF),
    )

    # the symbol arrives as the new form settles (reveal tick 14) and fades out by frame 58
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

    resources = [streaks_a, streaks_b, cocoon, ribbons_a, ribbons_b, orb, orb_pulse, orb_fill,
                 flash, ring_a, ring_b, shards, shell, sparkles, symbol_glow, symbol, symbol_twinkles]
    return {"magic": absorb["magic"], "version": absorb["version"], "resources": resources, "textures": textures}


def main():
    data = spa.write(build())
    open(OUT, "wb").write(data)
    assert spa.write(spa.read(OUT)) == data
    print(f"wrote {os.path.relpath(OUT)} ({len(data)} bytes)")


if __name__ == "__main__":
    main()

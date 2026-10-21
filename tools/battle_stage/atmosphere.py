"""Light and fog of every background: the BattleStageFileAtmosphere of its backdrop
piece, plus the DS lighting and fog math the preview uses to check it.

Lighting. Light 0 is white and its direction is the same for every background, down
and away from the camera, with equal parts down and forward so the ground (normal up)
and the panorama or back wall (normal toward the camera) get the same level and meet
without a seam at the base row. The material does the tinting: each lighting column is
derived from two targets, the colour of a surface that faces up (or the camera) and of
one that faces away from the light (ambient only). A target of 31 saturates, so the
texture shows unchanged; at day every up- or camera-facing surface saturates and the
home pose shows the classic art exactly, while disc sides, the arc and side walls that
turn away from the light show the shading.

Fog. The renderer squeezes depth into [DEPTH_NEAR, DEPTH_FAR] / 4096 of NDC, so the
15-bit depth the fog table reads only spans about 32420 (1 unit from the camera) to
32759 (128 units); the scene the home camera sees lies around 32700..32755. The table
is sampled from a density curve over view depth: entry j sits at depth
fogOffset + step * (j + 1) with step 0x400 >> fogShift, and fogShift is as large (as
fine) as the curve's depth range allows. Nearer than fogOffset the density is entry 0,
which is always 0, so the platforms and the near ground stay clear.
"""

import math

import arena
import classic
import stage_format as sf

NUM_COLUMNS = sf.NUM_LIGHTING  # enum BattleStageLightingColumn (sf.LIGHTING_COLUMNS)
TOD_NAMES = ("day", "twilight", "night")  # the classic columns (ov16_0223EC04)
COLUMN = {name: i for i, name in enumerate(sf.LIGHTING_COLUMNS)}

# Light 0: world-space direction the light travels. Down and forward equally, a little
# from the left.
LIGHT_DIR = (-0.5, -0.61, -0.61)
LIGHT_COLOR = (31, 31, 31)
FOG_ALPHA = 31
FOG_SHIFT_MAX = 10  # step 1: 0x400 >> 10

WHITE = (31, 31, 31)

# Fraction of the up level from which a target of 31 saturates
SATURATE_FROM = 0.5

# Classes of background
CLASS_OUTDOOR = "outdoor"
CLASS_SNOW = "snow"
CLASS_CAVE = "cave"
CLASS_ROOM = "room"
CLASS_VOID = "void"

# Per class: (up target, away target, fog colour) per column, and the fog ramp
# (near depth with no fog, reference depth, density there, max density) or None. The
# fog table is one per piece, so every column shares the ramp and only the colour
# changes. A near depth of HOME_FAR starts the fog just beyond the farthest point of the
# home view, so outdoors the home pose stays exact and the haze only shows on the far
# panorama when the camera turns.
HOME_FAR = "home far"
DAY = (WHITE, (24, 24, 24), (27, 29, 31))
TWILIGHT = ((31, 30, 28), (24, 21, 19), (26, 18, 16))
NIGHT = ((28, 29, 31), (17, 18, 23), (2, 3, 8))
# bw2vis:stage-light: the BW2-derived intermediate columns the renderer blends in by the RTC
# hour and minute (battle_stage_light.c). BW2's battle light at 9:00 is (15,15,22) against
# (24,24,20) at noon, and at 18:30 (17,13,10) (res/lighting/battle/001.json of pokebw2); these
# keep the hue at a fraction of the strength, on top of the classic palette of that hour (day
# palette at 6:00-9:00, the already warm twilight palette at 18:30), so the 2D fallback
# (BattleStage_Suppress) stays close.
MORNING = ((27, 28, 31), (20, 21, 26), (24, 27, 31))
DUSK = ((31, 27, 22), (24, 17, 13), (28, 17, 11))

CLASS_ATMOSPHERE = {
    CLASS_OUTDOOR: ((DAY, TWILIGHT, NIGHT, MORNING, DUSK), (HOME_FAR, 60.0, 24, 32)),
    CLASS_SNOW: (
        (
            (WHITE, (24, 25, 26), (30, 31, 31)),
            (TWILIGHT[0], TWILIGHT[1], (28, 24, 24)),
            (NIGHT[0], NIGHT[1], (8, 10, 16)),
            (MORNING[0], MORNING[1], (27, 29, 31)),
            (DUSK[0], DUSK[1], (29, 22, 18)),
        ),
        (16.0, 30.0, 10, 24),
    ),
    CLASS_CAVE: ((((30, 30, 31), (18, 18, 22), (2, 2, 5)),) * 3, (10.0, 30.0, 20, 36)),
    CLASS_VOID: ((((29, 28, 31), (20, 18, 28), (6, 2, 10)),) * 3, (12.0, 30.0, 20, 28)),
}

# Rooms: saturated on top, the away side tinted to the room; no fog
ROOM_AWAY_TINT = {
    12: (20, 26, 20),  # Aaron
    13: (26, 22, 16),  # Bertha
    14: (28, 18, 12),  # Flint
    15: (22, 16, 28),  # Lucian
    16: (24, 24, 28),  # Cynthia
}
ROOM_AWAY_DEFAULT = (24, 24, 24)


def background_class(background):
    kind = arena.BACKGROUND_KIND[background]

    if kind == arena.KIND_ROOM:
        return CLASS_ROOM

    if kind == arena.KIND_CAVE:
        return CLASS_CAVE

    if kind == arena.KIND_VOID:
        return CLASS_VOID

    return CLASS_SNOW if background == classic.BACKGROUND_SNOW else CLASS_OUTDOOR


def has_time_of_day(background):
    """The backgrounds whose battles take the time of day (ov16_0223EC04,
    battle_stage_light.c HasTimeOfDay): the six outdoor ones."""
    return background in classic.TIME_OF_DAY_BACKGROUNDS


def spec(background):
    """(columns, fog ramp or None) of a background: NUM_COLUMNS (up, away, fog colour)."""
    cls = background_class(background)

    if cls == CLASS_ROOM:
        away = ROOM_AWAY_TINT.get(background, ROOM_AWAY_DEFAULT)
        return ((WHITE, away, (0, 0, 0)),) * NUM_COLUMNS, None

    tod, ramp = CLASS_ATMOSPHERE[cls]
    tod = tod + (tod[0],) * (sf.NUM_TOD_COLUMNS - len(tod))  # caves and the void: one column
    return tod, ramp


def home_far(backdrop):
    """View depth of the farthest backdrop vertex the home view sees."""
    cam = backdrop.home.cam
    return max(-cam.world_to_view(arena.world_of(v.pos))[2] for m in backdrop.meshes for v, _st, _n in m.vertices if v.exact)


def rgb(c):
    return c[0] | (c[1] << 5) | (c[2] << 10)


def unrgb(v):
    return (v & 31, (v >> 5) & 31, (v >> 10) & 31)


def light_dir_fx16():
    n = math.sqrt(sum(c * c for c in LIGHT_DIR))
    return tuple(int(round(c / n * 4095)) for c in LIGHT_DIR)


def light_dir_fx10(lighting):
    """G3_LightVector packs each fx16 component to fx10 (>> 3)."""
    return tuple(c >> 3 for c in lighting.light_dir)


def diffuse_level(light10, normal10):
    """max(0, -dot(light, normal)) in fx12 (0..4096), from the fx10 vectors (DeSmuME
    widens both to fx12 before the dot product)."""
    dot = sum((a << 3) * (b << 3) for a, b in zip(light10, normal10)) >> 12
    return max(0, -dot)


def vertex_color(lighting, normal10):
    """5-bit (r, g, b) the DS lighting gives a vertex:
    min(31, emission + (diffuse*light*level + ambient*light*4096) >> 17)."""
    level = diffuse_level(light_dir_fx10(lighting), normal10)
    light = unrgb(lighting.light_color)
    dif, amb, emi = unrgb(lighting.diffuse), unrgb(lighting.ambient), unrgb(lighting.emission)
    return tuple(min(31, emi[c] + ((dif[c] * light[c] * level + amb[c] * light[c] * 4096) >> 17)) for c in range(3))


def channel(level, dif, amb, light=31):
    return min(31, (dif * light * level + amb * light * 4096) >> 17)


def material(up, away, level_up):
    """(diffuse, ambient) per channel so a surface at level_up gets up and one at level
    0 gets away (as close as 5 bits allow). A target of 31 saturates from
    SATURATE_FROM * level_up on, so surfaces turned a little from the camera or the sky
    (the front of the disc sides, the ground arc) still show the art unchanged."""
    dif, amb = [], []

    for c in range(3):
        a = min(range(32), key=lambda v: (abs(channel(0, 0, v) - away[c]), v))

        if up[c] >= 31:
            d = next((v for v in range(32) if channel(int(level_up * SATURATE_FROM), v, a) >= 31), 31)
        else:
            d = min(range(32), key=lambda v: (abs(channel(level_up, v, a) - up[c]), v))

        dif.append(d)
        amb.append(a)

    return tuple(dif), tuple(amb)


def ramp_density(near_d, ref_d, ref_density, max_density):
    """Density over view depth: 0 up to near_d, ref_density at ref_d, rising smoothly toward
    max_density."""
    k = -math.log(1 - ref_density / max_density) / (ref_d - near_d)
    return lambda d: 0 if d <= near_d else max_density * (1 - math.exp(-k * (d - near_d)))


def view_depth(cam, depth):
    """The view depth whose 15-bit fog depth is `depth`."""
    lo, hi = arena.NEAR, 1024.0

    for _ in range(60):
        mid = (lo + hi) / 2

        if cam.depth_of_view_depth(mid) < depth:
            lo = mid
        else:
            hi = mid

    return (lo + hi) / 2


def fog_grid(cam, near_d):
    """(shift, offset) of a fog table that starts at near_d and reaches arena.FAR, as fine as
    that allows. Every depth up to near_d (by the hardware formula and by DeSmuME's, one more)
    reads entry 0."""
    offset = int(math.floor(cam.depth_of_view_depth(near_d))) + 1
    far_depth = cam.depth_of_view_depth(arena.FAR)
    shift = FOG_SHIFT_MAX

    while shift > 0 and offset + (0x400 >> shift) * 32 < far_depth:
        shift -= 1

    return shift, offset


def sample_table(cam, shift, offset, density):
    """The 32 entries of a fog table on a grid. Entry j is reached at offset + step * (j + 1);
    sample where it sits. Entry 0 is always 0."""
    step = 0x400 >> shift
    table = [min(127, int(round(density(view_depth(cam, offset + step * (j + 1)))))) for j in range(32)]
    table[0] = 0
    return table


def fog_table(cam, near_d, ref_d, ref_density, max_density):
    """(shift, offset, table) for a density ramp over view depth (ramp_density)."""
    shift, offset = fog_grid(cam, near_d)
    return shift, offset, sample_table(cam, shift, offset, ramp_density(near_d, ref_d, ref_density, max_density))


def build(backdrop):
    """The BattleStageFileAtmosphere of a backdrop's background."""
    cols, ramp = spec(backdrop.background)
    light10 = tuple(c >> 3 for c in light_dir_fx16())
    level_up = diffuse_level(light10, sf.unpack_normal(sf.pack_normal(arena.UP)))
    lighting = []

    for up, away, fog_color in cols:
        dif, amb = material(up, away, level_up)
        lighting.append(sf.Lighting(light_dir_fx16(), rgb(LIGHT_COLOR), rgb(dif), rgb(amb), 0, rgb(fog_color), FOG_ALPHA))

    if ramp is None:
        return sf.Atmosphere(0, 0, 0, [0] * 32, lighting)

    near_d = home_far(backdrop) if ramp[0] == HOME_FAR else ramp[0]
    ref_d = max(ramp[1], near_d + 1)
    shift, offset, table = fog_table(backdrop.home.cam, near_d, ref_d, ramp[2], ramp[3])
    return sf.Atmosphere(1, shift, offset, table, lighting)


# ---- The renderer's pick at battle start (mirrors src/battle/battle_stage_light.c) ----------

WEIGHT_ONE = 256
_D, _T, _N, _M, _K = range(sf.NUM_TOD_COLUMNS)


def _w(**kw):
    w = [0] * sf.NUM_TOD_COLUMNS
    for k, v in kw.items():
        w[{"D": _D, "T": _T, "N": _N, "M": _M, "K": _K}[k]] = v
    return w


# (minute, weights D, T, N, M, K), as sLightKeys
LIGHT_KEYS = (
    (0, _w(N=256)), (4 * 60, _w(N=256)), (6 * 60, _w(M=256)), (9 * 60, _w(M=256)),
    (12 * 60, _w(D=256)), (15 * 60 + 30, _w(D=256)), (17 * 60, _w(T=256)), (18 * 60 + 30, _w(K=256)),
    (20 * 60, _w(N=128, K=128)), (21 * 60, _w(N=256)), (24 * 60, _w(N=256)),
)
FORCED_MINUTE = {"day": 12 * 60, "twilight": 17 * 60, "night": 23 * 60, "morning": 9 * 60}


def schedule_weights(minute):
    for i in range(1, len(LIGHT_KEYS)):
        a, b = LIGHT_KEYS[i - 1], LIGHT_KEYS[i]
        if minute < b[0]:
            break
    t = (minute - a[0]) * WEIGHT_ONE // (b[0] - a[0])
    w = [(a[1][i] * (WEIGHT_ONE - t) + b[1][i] * t + WEIGHT_ONE // 2) // WEIGHT_ONE for i in range(sf.NUM_TOD_COLUMNS)]
    largest = 0
    for i in range(sf.NUM_TOD_COLUMNS):
        if w[i] > w[largest]:
            largest = i
    w[largest] += WEIGHT_ONE - sum(w)
    return w


def _blend(colors, w):
    return rgb(tuple((sum(wi * unrgb(c)[ch] for wi, c in zip(w, colors)) + 128) // 256 for ch in range(3)))


def resolve(atm, background, minute=None):
    """(Lighting, (fog_shift, fog_offset, fog_table)) the renderer uses for a battle on
    `background` at `minute` of the day."""
    if has_time_of_day(background) and minute is not None:
        w = schedule_weights(minute)
    else:
        w = [256] + [0] * (sf.NUM_TOD_COLUMNS - 1)
    cols = atm.lighting[:sf.NUM_TOD_COLUMNS]
    li = cols[0].copy()
    for f in ("light_color", "diffuse", "ambient", "emission", "fog_color"):
        setattr(li, f, _blend([getattr(c, f) for c in cols], w))
    li.fog_alpha = (sum(wi * c.fog_alpha for wi, c in zip(w, cols)) + 128) // 256
    return li, (atm.fog_shift, atm.fog_offset, list(atm.fog_table))

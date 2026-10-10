#!/usr/bin/env python3
"""Textures and palettes for the Route 203 scar, appended to the overworld texture set 006.

Usage:
  python3 tools/route_203/textures.py                 dry run: print what would be added, VRAM before/after
  python3 tools/route_203/textures.py --write         write res/field/maps/texture_sets/map_texture_set_006.nsbtx
  python3 tools/route_203/textures.py --preview DIR   also write PNG previews of every new texture/palette pair

Set 006 belongs to area 6, which is shared by 12 overworld map headers (Twinleaf, Sandgem, Jubilife, Routes 201-204
South, 219-221, Verity Lakefront). Route 203 is reached from Jubilife without a warp, so the scar's textures have to be
in this set. Everything here is APPEND-ONLY: the stock textures and palettes keep their names and data, so the other
maps are unchanged. The set is always rebuilt from the base revision (BASE_REV), so re-running is idempotent.

New texel data (2 x 512 B):
  r203_crack   32x32 pltt16, colour 0 transparent: jagged glowing violet cracks (a decal laid over the ground)
  r203_scorch  32x32 pltt16, colour 0 transparent: a ragged scorched-ash blot (a decal that softens tile edges)
New palettes only (stock texels, recoloured by luminance; 6 x 16-32 B):
  r203_ash    for criff   (rocky dirt)        -> scorched violet-grey ash, the scar's base ground
  r203_rockv  for criffp  (cliff face)        -> dark violet rock, the fissure walls
  r203_rift   for asasea  (shallow sea)       -> violet glow, the fissure floor; asasea keeps its stock fldtanime ripple
  r203_dead   for tree01  (tree)              -> dead brown leaves, the fallen crown
  r203_char   for tree01                      -> charred tree
  r203_bark   for nbridge (plank, dun_bridge) -> bark brown, the fallen trunk
"""
import os
import random
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import nsbtx  # noqa: E402

BASE_REV = "68ae1fadde"      # arc1-part2 before the scar: stock set 006 and chunk 019
SET_REL = "res/field/maps/texture_sets/map_texture_set_006.nsbtx"
VRAM_PROVEN = 76416          # largest stock map texture set (048), see docs/lake_verity_redesign/pipeline.md


def base_file(rel):
    try:
        return subprocess.run(["git", "-C", ROOT, "show", f"{BASE_REV}:{rel}"], check=True,
                              capture_output=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return open(os.path.join(ROOT, rel), "rb").read()


def bgr(c):
    return nsbtx.bgr555(c)


# ---------------------------------------------------------------------------------------------------------------
# palette-only recolours
# ---------------------------------------------------------------------------------------------------------------

def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def ramp(keys, t):
    t = max(0.0, min(1.0, t))
    n = len(keys) - 1
    i = min(int(t * n), n - 1)
    f = t * n - i
    return tuple(round(keys[i][k] + (keys[i + 1][k] - keys[i][k]) * f) for k in range(3))


def recolour(src_colors, used, keys, keep=()):
    """Map each stock colour onto the ramp `keys` by its luminance, normalised over the colours the texture uses.
    Indices in `keep` keep their stock value (e.g. a transparent colour 0)."""
    rgbs = [nsbtx.rgb(c) for c in src_colors]
    ls = [lum(rgbs[i]) for i in used]
    lo, hi = min(ls), max(ls)
    out = []
    for i, c in enumerate(rgbs):
        if i in keep:
            out.append(src_colors[i])
            continue
        t = (lum(c) - lo) / (hi - lo) if hi > lo else 0.5
        out.append(bgr(ramp(keys, t)))
    return out


RECOLOURS = [
    # name,       texture,  stock palette, ramp dark -> light, keep
    ("r203_ash", "criff", "criff", [(44, 36, 50), (66, 56, 74), (88, 78, 96), (112, 102, 118)], ()),
    ("r203_rockv", "criffp", "criff", [(22, 10, 34), (52, 26, 78), (92, 54, 130), (150, 110, 196)], ()),
    ("r203_rift", "asasea", "asasea", [(120, 48, 190), (176, 110, 240), (226, 186, 255), (248, 232, 255)], ()),
    ("r203_dead", "tree01", "tree01", [(40, 28, 20), (92, 58, 30), (150, 98, 46), (204, 156, 84)], (0,)),
    ("r203_char", "tree01", "tree01", [(26, 22, 28), (56, 50, 58), (92, 84, 94), (136, 126, 134)], (0,)),
    ("r203_bark", "nbridge", "dun_bridge", [(52, 34, 24), (86, 60, 40), (118, 86, 58), (150, 116, 80)], (0,)),
]


def used_indices(tx):
    _, idx = nsbtx.decode(tx, [0] * 256)
    return sorted({v for row in idx for v in row})


# ---------------------------------------------------------------------------------------------------------------
# new texel art (deterministic)
# ---------------------------------------------------------------------------------------------------------------

CRACK_PAL = [(0, 0, 0), (30, 8, 44), (70, 22, 110), (128, 56, 196), (196, 140, 255), (244, 226, 255),
             (96, 40, 150), (160, 96, 230)] + [(0, 0, 0)] * 8
SCORCH_PAL = [(0, 0, 0), (30, 24, 34), (50, 42, 56), (66, 58, 74), (82, 74, 92), (98, 90, 108), (116, 108, 124),
              (86, 58, 112), (60, 36, 84)] + [(0, 0, 0)] * 7


def _line(canvas, pts, val, w=32, h=32):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(int(round(max(abs(x1 - x0), abs(y1 - y0)))), 1)
        for k in range(n + 1):
            x = round(x0 + (x1 - x0) * k / n)
            y = round(y0 + (y1 - y0) * k / n)
            if 0 <= x < w and 0 <= y < h:
                canvas[y][x] = max(canvas[y][x], val)


def _jagged(rng, start, angle, length, step=(2, 4), jitter=0.9):
    import math
    pts = [start]
    x, y = start
    travelled = 0
    while travelled < length:
        s = rng.randint(*step)
        a = angle + rng.uniform(-jitter, jitter)
        x, y = x + math.cos(a) * s, y + math.sin(a) * s
        pts.append((x, y))
        travelled += s
    return pts


def make_crack():
    """32x32 indices: 0 transparent, 1 shadow, 2 dark violet glow, 3/6/7 violet, 4 lilac core, 5 hot core."""
    import math
    rng = random.Random(203)
    c = [[0] * 32 for _ in range(32)]
    main = _jagged(rng, (3, 19), -0.35, 30, step=(2, 3), jitter=0.8)
    _line(c, main, 4)
    for (x, y) in main[2:-2:2]:                     # hot spots along the middle of the main crack
        xi, yi = round(x), round(y)
        if 0 <= xi < 32 and 0 <= yi < 32:
            c[yi][xi] = 5
    for k in (2, 4, 6, 8):                          # branches, tapering (value 3 = thinner, dimmer)
        if k < len(main):
            ang = -0.35 + rng.choice((-1, 1)) * rng.uniform(0.9, 1.6)
            br = _jagged(rng, main[k], ang, rng.randint(6, 11), step=(2, 3), jitter=0.7)
            _line(c, br, 3)
            if rng.random() < 0.6 and len(br) > 2:
                tw = _jagged(rng, br[len(br) // 2], ang + rng.uniform(-1.0, 1.0), rng.randint(3, 5), step=(1, 2))
                _line(c, tw, 7)
    # glow ring then shadow (south/east side, where the camera sees into the crack)
    g = [row[:] for row in c]
    for y in range(32):
        for x in range(32):
            if c[y][x] == 0 and any(0 <= x + dx < 32 and 0 <= y + dy < 32 and c[y + dy][x + dx] in (4, 5)
                                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                g[y][x] = 2
            elif c[y][x] == 0 and any(0 <= x + dx < 32 and 0 <= y + dy < 32 and c[y + dy][x + dx] in (3, 7)
                                      for dx, dy in ((1, 0), (0, 1))):
                g[y][x] = 6 if rng.random() < 0.3 else 2
    s = [row[:] for row in g]
    for y in range(32):
        for x in range(32):
            if g[y][x] == 0 and any(0 <= x - dx < 32 and 0 <= y - dy < 32 and g[y - dy][x - dx] in (2, 6)
                                    for dx, dy in ((0, 1), (1, 1))):
                s[y][x] = 1
    # keep the border clear so decals never show a cut line
    for y in range(32):
        for x in range(32):
            if x in (0, 31) or y in (0, 31):
                s[y][x] = 0
    return s


def make_scorch():
    """32x32 indices: a ragged ash blot with a charred rim; 0 outside."""
    import math
    rng = random.Random(2031)
    a1, a2, a3 = rng.uniform(0, 6.28), rng.uniform(0, 6.28), rng.uniform(0, 6.28)
    noise = [[rng.random() for _ in range(32)] for _ in range(32)]
    out = [[0] * 32 for _ in range(32)]
    for y in range(32):
        for x in range(32):
            dx, dy = x - 15.5, y - 15.5
            d = math.hypot(dx, dy)
            th = math.atan2(dy, dx)
            r = 12.2 + 1.8 * math.sin(3 * th + a1) + 1.2 * math.sin(5 * th + a2) + 0.8 * math.sin(9 * th + a3)
            r += (noise[y][x] - 0.5) * 2.2
            if d < r:
                edge = r - d
                n = noise[(y * 7) % 32][(x * 5) % 32]
                if edge < 1.3:
                    v = 1
                elif edge < 2.6:
                    v = 2 if n < 0.6 else 1
                else:
                    v = 2 + int(n * 4.999)                    # 2..6 speckled ash
                    if n > 0.93:
                        v = 7                                 # a few violet flecks
                    elif n < 0.05:
                        v = 8
                out[y][x] = v
    return out


def indexed_texture(name, idx, pal):
    data = bytearray()
    flat = [v for row in idx for v in row]
    for i in range(0, len(flat), 2):
        data.append(flat[i] | flat[i + 1] << 4)
    tex = dict(name=name, fmt=3, w=32, h=32, c0=1, data=bytes(data))
    return tex, dict(name=name + "_pl", colors=[bgr(c) for c in pal], pltt4=0)


# ---------------------------------------------------------------------------------------------------------------

def new_entries(base):
    s = nsbtx.parse(base)
    T = {t["name"]: t for t in s["textures"]}
    P = {p["name"]: p for p in s["palettes"]}
    textures, palettes = [], []
    for name, idx, pal in (("r203_crack", make_crack(), CRACK_PAL), ("r203_scorch", make_scorch(), SCORCH_PAL)):
        t, p = indexed_texture(name, idx, pal)
        textures.append(t)
        palettes.append(p)
    for name, tex, pal, keys, keep in RECOLOURS:
        cols = recolour(P[pal]["colors"], used_indices(T[tex]), keys, keep)
        palettes.append(dict(name=name, colors=cols, pltt4=0))
    return s, textures, palettes


# material table for the chunk builder: material name -> (texture, palette, size)
MATERIALS = {
    "r203_crack": ("r203_crack", "r203_crack_pl", (32, 32)),
    "r203_scorch": ("r203_scorch", "r203_scorch_pl", (32, 32)),
    "r203_ash": ("criff", "r203_ash", (16, 16)),
    "r203_rockv": ("criffp", "r203_rockv", (32, 32)),
    "r203_rift": ("asasea", "r203_rift", (16, 16)),
    "r203_dead": ("tree01", "r203_dead", (64, 64)),
    "r203_char": ("tree01", "r203_char", (64, 64)),
    "r203_bark": ("nbridge", "r203_bark", (32, 32)),
}


def build_set():
    base = base_file(SET_REL)
    s, tex, pals = new_entries(base)
    names = {t["name"] for t in s["textures"]} | {p["name"] for p in s["palettes"]}
    clash = [e["name"] for e in tex + pals if e["name"] in names]
    assert not clash, clash
    out = nsbtx.build(s["textures"] + tex, s["palettes"] + pals, pal_flag=s["header"]["pal_flag"])
    return base, out, tex, pals


def preview(out_bytes, tex, pals, d):
    from png import write_rgba  # tools/lake_verity/png.py
    os.makedirs(d, exist_ok=True)
    s = nsbtx.parse(out_bytes)
    T = {t["name"]: t for t in s["textures"]}
    P = {p["name"]: p for p in s["palettes"]}
    pairs = [(m[0], m[1]) for m in MATERIALS.values()]
    for tn, pn in pairs:
        rows, _ = nsbtx.decode(T[tn], P[pn]["colors"])
        write_rgba(os.path.join(d, f"{tn}__{pn}.png"), T[tn]["w"], T[tn]["h"], [[tuple(p) for p in r] for r in rows])


def main():
    base, out, tex, pals = build_set()
    sb, so = nsbtx.parse(base), nsbtx.parse(out)
    vb, vo = nsbtx.vram_usage(sb), nsbtx.vram_usage(so)
    print(f"set 006: {len(sb['textures'])} -> {len(so['textures'])} textures, {len(sb['palettes'])} -> "
          f"{len(so['palettes'])} palettes; VRAM {sum(vb)} -> {sum(vo)} B (texels {vb[0]} -> {vo[0]}, palettes "
          f"{vb[1]} -> {vo[1]}); file {len(base)} -> {len(out)} B")
    assert sum(vo) <= VRAM_PROVEN
    # stock entries unchanged
    for t in sb["textures"]:
        t2 = next(x for x in so["textures"] if x["name"] == t["name"])
        assert t2["data"] == t["data"] and (t2["fmt"], t2["w"], t2["h"], t2["c0"]) == (t["fmt"], t["w"], t["h"], t["c0"])
    for p in sb["palettes"]:
        p2 = next(x for x in so["palettes"] if x["name"] == p["name"])
        assert p2["colors"][:len(p["colors"])] == p["colors"] or p2["data"].startswith(p["data"][:len(p2["data"])])
    print("stock textures and palettes: unchanged")
    if "--preview" in sys.argv:
        preview(out, tex, pals, sys.argv[sys.argv.index("--preview") + 1])
    if "--write" in sys.argv:
        open(os.path.join(ROOT, SET_REL), "wb").write(out)
        print("wrote", SET_REL)


if __name__ == "__main__":
    main()

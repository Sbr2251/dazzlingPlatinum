#!/usr/bin/env python3
"""Named colours for the Solaceon kit, each sampled from a stock palette that Solaceon (or a Sinnoh town under the
same outdoor light) already shows. Every kit palette is built from these names, so the kit sits in the same light as
set 010 and the Solaceon buildings.

STOCK[name] = (source, palette, index): source "set" = map texture set 010, a number = areabm_texset entry (6 Solaceon
buildings, 4 Eterna, 5 Hearthome, 7 Veilstone). DERIVED[name] = (a, b, t): a blend of two stock names, for the few
shades stock has no exact match for (deep violet for roof shadows, a lighter violet glint). Everything is snapped to
5-5-5. `colour(name)` returns RGB; `report(names)` says how many are exact stock colours.
"""
import common as C

STOCK = {
    # pale stone + lilac: the Lost Tower (r209s01_a, Route 209, in Solaceon's own building set)
    "stone0": (6, "r209s01_a_pl", 9),     # (246,255,255) highlight
    "stone1": (6, "r209s01_a_pl", 10),    # (230,238,238)
    "stone2": (6, "r209s01_a_pl", 8),     # (205,213,213) face
    "stone3": (6, "r209s01_a_pl", 6),     # (189,197,197)
    "stone4": (6, "r209s01_a_pl", 7),     # (164,172,172) joint
    "stone5": (6, "r209s01_a_pl", 5),     # (139,148,148) deep joint
    "stone6": (6, "r209s01_a_pl", 11),    # (98,106,98)
    "lilac1": (6, "r209s01_a_pl", 4),     # (189,197,222)
    "lilac2": (6, "r209s01_a_pl", 3),     # (164,172,197)
    "lilac3": (6, "r209s01_a_pl", 2),     # (131,139,164)
    "lilac4": (6, "r209s01_a_pl", 1),     # (98,106,131)
    "lilac5": (6, "r209s01_a_pl", 0),     # (82,82,123)
    "grey12": (6, "r209s01_a_pl", 12),    # (74,74,74)
    "grey13": (6, "r209s01_a_pl", 13),    # (49,49,49)
    # violet: the Eterna house walls (t3_h01)
    "violet1": (4, "t3_h01_pl", 3),       # (131,115,180)
    "violet2": (4, "t3_h01_pl", 2),       # (106,90,156)
    "violet3": (4, "t3_h01_pl", 1),       # (82,65,131)
    "mist1": (4, "t3_h01_pl", 5),         # (205,205,230)
    "mist2": (4, "t3_h01_pl", 4),         # (180,180,205)
    # gold: the Veilstone containers
    "gold0": (7, "container_pl", 4),      # (238,197,82)
    "gold1": (7, "container_pl", 2),      # (213,164,32)
    "gold2": (7, "container_pl", 0),      # (180,131,8)
    "gold3": (6, "t5_o01_a_pl", 7),       # (106,90,32) Celestic relief, dark gold
    # outlines (the Solaceon house / Day Care outline colours)
    "ink": (6, "t4_h01_a_pl", 1),         # (49,49,41)
    "ink2": (6, "t4_h01_a_pl", 14),       # (82,74,74)
    # Solaceon house wood (t4_h01_a)
    "wood0": (6, "t4_h01_a_pl", 2),       # (222,189,131)
    "wood1": (6, "t4_h01_a_pl", 3),       # (197,148,74)
    "wood2": (6, "t4_h01_a_pl", 5),       # (172,123,57)
    "wood3": (6, "t4_h01_a_pl", 7),       # (131,90,49)
    "wood4": (6, "t4_h01_a_pl", 11),      # (106,74,41)
    "wood5": (6, "t4_h01_a_pl", 10),      # (90,57,32)
    "woodg": (6, "t4_h01_a_pl", 13),      # (164,139,106)
    # Day Care boards (t4_s01_a) and roof (t4_s01_c)
    "board0": (6, "t4_s01_a_pl", 8),      # (238,213,164)
    "board1": (6, "t4_s01_a_pl", 6),      # (197,180,131)
    "board2": (6, "t4_s01_a_pl", 7),      # (172,156,115)
    "blue0": (6, "t4_s01_a_pl", 0),       # (172,197,213)
    "blue1": (6, "t4_s01_a_pl", 2),       # (106,148,197)
    "blue2": (6, "t4_s01_a_pl", 1),       # (65,115,172)
    "blue3": (6, "t4_s01_a_pl", 4),       # (49,106,156)
    "groof1": (6, "t4_s01_c_pl", 2),      # (106,197,106)
    "groof2": (6, "t4_s01_c_pl", 3),      # (90,189,90)
    "groof3": (6, "t4_s01_c_pl", 1),      # (65,172,74)
    "slate1": (6, "t4_s01_c_pl", 7),      # (115,139,148)
    "slate2": (6, "t4_s01_c_pl", 8),      # (98,115,131)
    "slate3": (6, "t4_s01_c_pl", 5),      # (82,90,98)
    # warm light: the Pokemon Center roof oranges + the sand road's lightest yellow
    "glow0": ("set", "sandset", 6),       # (255,238,180)
    "glow1": (6, "pcloof_pl", 6),         # (255,180,90)
    "glow2": (6, "pcloof_pl", 4),         # (255,156,32)
    "glow3": (6, "pcloof_pl", 7),         # (238,123,24)
    "glow4": (6, "pcloof_pl", 8),         # (139,74,16)
    "red1": (6, "pcloof_pl", 9),          # (246,98,0)
    "red2": (6, "pcloof_pl", 12),         # (189,49,0)
    "white": (6, "pcloof_pl", 15),        # (255,255,255)
    # ground: set 010 sand road, grass, dirt
    "sand0": ("set", "sandset", 6),       # (255,238,180)
    "sand1": ("set", "sandset", 5),       # (255,230,156)
    "sand2": ("set", "sandset", 11),      # (255,222,148)
    "sand3": ("set", "nsandp", 5),        # (255,213,131)
    "sand4": ("set", "nsandp", 7),        # (238,197,115)
    "grass0": ("set", "grass", 6),        # (106,255,164)
    "grass1": ("set", "grass", 0),        # (82,255,148)
    "grass2": ("set", "grass", 1),        # (74,246,139)
    "grass3": ("set", "tshadow", 2),      # (57,205,115)
    "grass4": ("set", "tshadow", 4),      # (57,189,106)
    "leaf1": ("set", "imped", 9),         # (98,172,57)
    "leaf2": ("set", "imped", 8),         # (74,131,82)
    "leaf3": ("set", "imped", 7),         # (41,90,57)
    "dirt1": ("set", "ckado", 10),        # (172,156,98)
    "dirt2": ("set", "ckado", 8),         # (156,139,98)
    "dirt3": ("set", "ckado", 6),         # (164,131,115)
    "dirt4": ("set", "ckado", 7),         # (148,115,106)
    "rock1": ("set", "criff", 6),         # (213,172,156)
    "rock2": ("set", "criff", 11),        # (180,139,131)
    "rock3": ("set", "criff", 10),        # (156,123,115)
    "rock4": ("set", "criff", 13),        # (139,98,98)
    "pave0": ("set", "blueglay", 1),      # (197,205,222)
    "pave1": ("set", "blueglay", 2),      # (180,197,205)
    "pave2": ("set", "blueglay", 0),      # (172,180,189)
    "cream0": ("set", "imped", 5),        # (238,246,255)
    "cream1": ("set", "imped", 4),        # (230,230,205)
    "cream2": ("set", "imped", 6),        # (172,172,156)
    "rose1": ("set", "imped", 12),        # (230,205,180)
    "rose2": ("set", "imped", 13),        # (222,180,164)
    # flowers (set 010 flower beds)
    "yellow": ("set", "rhana", 8),        # (230,230,0)
    "orange": ("set", "rhana", 9),        # (255,131,32)
    "pink": ("set", "nhana", 13),         # (255,189,148)
    "sky": ("set", "nhana", 1),           # (139,222,255)
    "lily": ("set", "shana", 2),          # (230,255,238)
    # Hearthome beige stone (c5_s03_a) for the plaza
    "beige0": (5, "c5_s03_a_pl", 2),      # (222,205,156)
    "beige1": (5, "c5_s03_a_pl", 5),      # (189,172,131)
    "beige2": (5, "c5_s03_a_pl", 4),      # (172,156,115)
    "beige3": (5, "c5_s03_a_pl", 3),      # (164,148,106)
    "beige4": (5, "c5_s03_a_pl", 1),      # (148,139,106)
    "beige5": (5, "c5_s03_a_pl", 6),      # (131,115,82)
    # steel: the Veilstone dish truss (para_asi)
    "steel0": (7, "para_asi_pl", 4),      # (156,172,180)
    "steel1": (7, "para_asi_pl", 3),      # (131,148,156)
    "steel2": (7, "para_asi_pl", 2),      # (106,131,139)
    "steel3": (7, "para_asi_pl", 1),      # (82,106,115)
    # window glass (the shared house window h_mado)
    "glass0": (6, "h_mado_pl", 0),        # (205,205,230)
}

DERIVED = {
    "violet0": ("violet1", "mist1", 0.45),     # roof glint
    "violet4": ("violet3", "ink", 0.45),       # roof shadow line
    "violet5": ("violet3", "ink", 0.75),       # eclipse disc rim
    "disc": ("ink", "violet3", 0.25),          # the eclipse disc
    "gold4": ("gold0", "white", 0.5),          # corona flash
}

_resolved = {}


def _stock(src, pal, i):
    s = C.set010() if src == "set" else C.prop_texset(src)
    p = next(p for p in s["palettes"] if p["name"] == pal)
    return C.nsbtx.rgb(p["colors"][i])


def colour(name):
    if name not in _resolved:
        if name in STOCK:
            _resolved[name] = _stock(*STOCK[name])
        else:
            a, b, t = DERIVED[name]
            _resolved[name] = C.snap(C.mix(colour(a), colour(b), t))
    return _resolved[name]


def pal(names):
    return [colour(n) for n in names]


def report(names):
    n = sum(1 for x in names if x in STOCK)
    return f"{n}/{len(names)} stock"


def source(name):
    if name in STOCK:
        s, p, i = STOCK[name]
        return f"{'set010' if s == 'set' else 'areabm_texset %d' % s} {p}[{i}]"
    a, b, t = DERIVED[name]
    return f"blend {a}/{b} {t}"

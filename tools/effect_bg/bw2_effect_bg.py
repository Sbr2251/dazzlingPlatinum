#!/usr/bin/env python3
"""Ports Black 2/White 2's battle effect backgrounds onto our SwitchBg moves.

    bw2_effect_bg.py sheet OUTDIR    contact sheets of all 77 BW2 effect BGs, the palette anims and the mapping
    bw2_effect_bg.py build           writes res/graphics/battle/effect_bg/ (assets, order, meson.build) and the
                                     two generated headers from ENTRIES; deterministic
    bw2_effect_bg.py apply           points every move in MOVES at its BW2 background (SwitchBg / RestoreBg)
    bw2_effect_bg.py redo            writes docs/living_battle_stage/redo/effect_bg.json (and the cut moves' expect elsewhere)
    bw2_effect_bg.py doc             prints the markdown tables of docs/living_battle_stage/effect_bg.md
    bw2_effect_bg.py vram            prints the VRAM and palette budget of every entry

Asset source: pokebw2's extracted res/graphics/btlv_effvm_bg and btlv_effvm_pal_anim (read-only; bw2lib.py).
The BW2 battle assets are allowed for battle visuals (/tmp/bw2vis/COMMON.md, "Asset policy").

How one BW2 background becomes ours (docs/living_battle_stage/effect_bg.md has the why):
- Screen: BW2's is 512x512 with the picture in the top-left 256x192 plus an 8 px margin on every side, or a
  512-wide or 256-period tall pattern. Our BG3 screen is 512x256 (BgTemplate in ov16_0223B140.c), so we keep
  BW2 map rows 0..27 and put rows 60..63 (y -32..-1) in rows 28..31: the margin above the picture stays where
  a vertical shake or wrap reads it, and a 256-period pattern stays seamless.
- Palette: BW2 loads the NCLR at BG row 8 and uses rows 8..13. We put BW2 row 8 at our row 9
  (BATTLE_BG_PALETTE_EFFECT, where BW2's BgPalAnim writes too) and rows 9..13 at our rows 12, 13, 14, 15, 8.
  Rows 12-15 are free during a move, row 8 is the BG2 mon copy's, which none of these moves uses.
- Tiles: 4bpp, at most 1024 (the screen entry's limit, 32 KB at BG3's char base 0x10000 in FADE and CUT
  mode); 512 for an entry used in BLEND mode, whose tiles go at 0xc000 under the backdrop's (Trick Room).
  Over the limit, the closest tiles are merged.
- A mirrored screen for the enemy-attacker case (Platinum's NSCR2), mirrored about the visible centre x=128.
"""

import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bw2lib  # noqa: E402
import catalogue  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(ROOT, "res/graphics/battle/effect_bg")
CONST_H = os.path.join(ROOT, "include/constants/battle/battle_effect_bg.h")
DATA_H = os.path.join(ROOT, "include/battle_anim/bw2_effect_bg_table.h")
NARC_BASENAME = "bw2_effect_bg"

BW2_BG_FIRST = 64  # bgIDs 0-57 are pl_batt_bg.narc's; ours start here
BW2_ROWS = 6
OUR_ROWS = (9, 12, 13, 14, 15, 8)  # our BG palette row for BW2 row 8 + i
MAX_TILES = 1024
MAX_TILES_BLEND = 512
MAP_ROWS = list(range(28)) + list(range(60, 64))

# name, BW2 bg id, Platinum bgID shown instead in contests, palette anim started on load (None = none),
# used in BLEND mode (tiles at 0xc000, 512 max)
ENTRIES = [
    ("RED_BURST", 3, 0, None, False),
    ("MAGENTA_BURST", 6, 5, None, False),
    ("ORANGE_BURST", 9, 6, None, False),
    ("STAR_IMPACT", 12, 0, 0, False),
    ("KALEIDOSCOPE", 15, 1, 1, False),
    ("BLUE_STREAM", 18, 9, None, False),
    ("PURPLE_STREAM", 21, 13, None, False),
    ("RED_STREAM", 24, 12, None, False),
    ("YELLOW_STREAM", 27, 11, None, False),
    ("SNOWSTORM", 30, 50, None, False),
    ("GREEN_RIPPLE", 33, 14, None, False),
    ("FALLING_SPARKS", 36, 51, None, False),
    ("STORM_CLOUDS", 39, 19, None, False),
    ("EARTH", 42, 53, None, False),
    ("PSYCHIC_WAVES", 45, 52, None, False),
    ("CYAN_SPEED", 51, 47, None, False),
    ("SUN_BLAST", 54, 22, None, False),
    ("WHITE_BLAST", 57, 21, None, False),
    ("RAPIDS", 63, 23, None, False),
    ("NIGHTMARE_SWIRLS", 69, 24, None, False),
    ("PSYCHIC_MARBLE", 72, 4, None, False),
    ("WHIRLPOOL", 75, 35, None, False),
    ("WIND_VORTEX", 78, 25, 4, False),
    ("BLUE_AURA", 84, 26, None, False),
    ("DARK_HALO", 87, 27, None, False),
    ("MAGENTA_FLAMES", 90, 28, None, False),
    ("TEAL_FLAMES", 96, 29, None, False),
    ("MIST_CLOUDS", 99, 10, None, False),
    ("FIRE_EXPLOSION", 102, 32, None, False),
    ("FULL_MOON", 108, 54, None, False),
    ("GREY_SPEED", 111, 47, None, False),
    ("LIGHT_BURST", 117, 31, None, False),
    ("SPACE", 126, 56, None, False),
    ("LIGHT_PILLAR", 129, 55, None, False),
    ("UPDRAFT", 132, 55, None, False),
    ("FALLING_LEAVES", 138, 34, None, False),
    ("SEABED", 144, 35, None, False),
    ("UNDERWATER", 147, 17, None, False),
    ("WATER_SPEED", 153, 36, None, False),
    ("FIRE_VORTEX", 156, 33, 13, False),
    ("SKY_RIPPLES", 159, 18, None, False),
    ("GRID_ROOM", 165, 57, None, True),
    ("LEAF_WIND", 168, 38, None, False),
    ("GREEN_BURST", 171, 7, None, False),
    ("FIRE_SPEED", 177, 39, None, False),
    ("ORANGE_FLARE", 180, 40, None, False),
    ("PINK_MANDALA", 183, 41, 16, False),
    ("CRESCENT_MOON", 186, 42, None, False),
    ("MAGMA_DOTS", 189, 43, 8, False),
    ("GREY_BANDS", 192, 44, None, False),
    ("HYPNO_RINGS", 204, 20, 17, False),
]

# move id, anim dir (or common anim path), Platinum bgID it used, entry, mode, reason
CUT, FADE, BLEND = "BATTLE_BG_SWITCH_MODE_CUT", "BATTLE_BG_SWITCH_MODE_FADE", "BATTLE_BG_SWITCH_MODE_BLEND"
MOVES = [
    (19, "fly", 55, "LIGHT_PILLAR", CUT, "BW2's redraw of Platinum's light pillar; tall, so the 32 px/frame vertical rush stays seamless"),
    (25, "mega_kick", 0, "STAR_IMPACT", CUT, "Platinum's 0-4 are one generic red burst; a Normal kick gets BW2's 'pow' star, animated"),
    (38, "double_edge", 6, "ORANGE_BURST", CUT, "BW2's redraw of Platinum's orange-white burst"),
    (56, "hydro_pump", 9, "BLUE_STREAM", CUT, "BW2's redraw of the blue stream; 512 wide for the sideways scroll"),
    (59, "blizzard", 50, "SNOWSTORM", CUT, "BW2's redraw of the grey snowfield: a blowing snowstorm, 512 wide"),
    (63, "hyper_beam", 14, "GREEN_RIPPLE", CUT, "BW2's redraw of Platinum's yellow-green ripple field, 512 wide"),
    (69, "seismic_toss", 51, "FALLING_SPARKS", CUT, "BW2's redraw of the night column with gold sparks; tall, for the vertical toss"),
    (87, "thunder", 19, "STORM_CLOUDS", CUT, "BW2's redraw of the storm-cloud sky"),
    (90, "fissure", 53, "EARTH", CUT, "BW2's redraw of the brown earth"),
    (93, "confusion", 20, "HYPNO_RINGS", CUT, "Platinum's 20 is a black screen; BW2's hypnosis rings, animated, read as confusion"),
    (94, "psychic", 52, "PSYCHIC_WAVES", CUT, "BW2's redraw of the pink psychic waves; tall, for the vertical scroll"),
    (97, "agility", 47, "CYAN_SPEED", CUT, "BW2's cyan speed lines, the redraw of Platinum's"),
    (120, "selfdestruct", 21, "WHITE_BLAST", CUT, "BW2's redraw of the white-pink blast with red rays"),
    (126, "fire_blast", 22, "SUN_BLAST", CUT, "BW2's redraw of the star-shaped fire blast"),
    (127, "waterfall", 23, "RAPIDS", CUT, "BW2's redraw of the blue zigzag rapids; tall, for the climb"),
    (143, "sky_attack", 18, "SKY_RIPPLES", CUT, "BW2's redraw of Platinum's light blue streaked sky, 512 wide"),
    (171, "nightmare", 24, "NIGHTMARE_SWIRLS", FADE, "BW2's redraw of the dark swirls; the fade to black is the nightmare falling, kept"),
    (177, "aeroblast", 25, "WIND_VORTEX", CUT, "BW2's teal vortex, the redraw of Platinum's, spun by palette anim 4"),
    (192, "zap_cannon", 26, "BLUE_AURA", CUT, "BW2's redraw of the blue glowing ellipse"),
    (200, "outrage", 28, "MAGENTA_FLAMES", CUT, "BW2's redraw of the magenta flames, 512 wide"),
    (221, "sacred_fire", 29, "TEAL_FLAMES", CUT, "BW2's redraw of the blue-violet flames, 512 wide"),
    (223, "dynamic_punch", 1, "KALEIDOSCOPE", CUT, "generic red burst in Platinum; BW2's fighting kaleidoscope burst, animated"),
    (224, "megahorn", 2, "RED_BURST", CUT, "BW2's redraw of the red burst"),
    (236, "moonlight", 54, "FULL_MOON", FADE, "BW2's redraw of the full moon; the fade is night falling, kept"),
    (245, "extreme_speed", 47, "GREY_SPEED", CUT, "shares Platinum's speed lines with Agility; BW2's grey Normal speed lines tell them apart"),
    (250, "whirlpool", 35, "WHIRLPOOL", CUT, "Platinum's night sea is shared with Water Pulse; BW2's whirlpool swirl under the line wave"),
    (264, "focus_punch", 31, "LIGHT_BURST", CUT, "BW2's redraw of Platinum's blue light burst (31-33)"),
    (273, "wish", 56, "SPACE", FADE, "BW2's redraw of deep space; the slow fade into the night sky is the wish, kept"),
    (276, "superpower", 3, "RED_BURST", CUT, "BW2's redraw of the red burst"),
    (296, "mist_ball", 10, "MIST_CLOUDS", CUT, "Platinum's 10 is the Hydro Pump stream again; BW2's swirling mist clouds, 512 wide"),
    (308, "hydro_cannon", 17, "UNDERWATER", CUT, "Platinum's 17 recolours Hyper Beam's ripples; BW2's underwater view, 512 wide"),
    (315, "overheat", 32, "FIRE_EXPLOSION", CUT, "generic blue burst in Platinum; BW2's fire explosion"),
    (322, "cosmic_power", 56, "SPACE", FADE, "BW2's redraw of deep space; the fade into space is kept"),
    (327, "sky_uppercut", 55, "UPDRAFT", CUT, "shares Fly's pillar in Platinum; BW2's upward chevrons for the rising blow, tall"),
    (338, "frenzy_plant", 34, "FALLING_LEAVES", CUT, "BW2's redraw of the leaf column; tall, for the vertical scroll"),
    (344, "volt_tackle", 27, "DARK_HALO", CUT, "BW2's redraw of the black ellipse in a yellow glow"),
    (352, "water_pulse", 35, "SEABED", CUT, "BW2's redraw of Platinum's night sea over hills, under the line wave"),
    (354, "psycho_boost", 4, "PSYCHIC_MARBLE", CUT, "generic red burst in Platinum; BW2's psychic marble"),
    (370, "close_combat", 36, "WATER_SPEED", CUT, "BW2's redraw of the blue speed lines, 512 wide"),
    (394, "flare_blitz", 33, "FIRE_VORTEX", CUT, "generic blue burst in Platinum; BW2's fire vortex, spun by palette anim 13"),
    (396, "aura_sphere", 11, "YELLOW_STREAM", CUT, "BW2's redraw of the yellow stream, 512 wide"),
    (411, "focus_blast", 12, "RED_STREAM", CUT, "BW2's redraw of the red stream, 512 wide"),
    (413, "brave_bird", 18, "SKY_RIPPLES", CUT, "BW2's redraw of the streaked sky (shared with Sky Attack in Platinum)"),
    (416, "giga_impact", 5, "MAGENTA_BURST", CUT, "BW2's redraw of the magenta burst"),
    (433, "trick_room", 57, "GRID_ROOM", BLEND, "BW2's redraw of the grid room; the half blend over the backdrop is the effect, kept"),
    (437, "leaf_storm", 38, "LEAF_WIND", CUT, "BW2's redraw of the leaves blowing sideways, 512 wide"),
    (438, "power_whip", 7, "GREEN_BURST", CUT, "BW2's redraw of the green burst"),
    (439, "rock_wrecker", 39, "FIRE_SPEED", CUT, "BW2's redraw of the orange-red streaks, 512 wide"),
    (441, "gunk_shot", 13, "PURPLE_STREAM", CUT, "BW2's redraw of the purple stream, 512 wide"),
    (457, "head_smash", 40, "ORANGE_FLARE", CUT, "BW2's redraw of the orange flare on blue"),
    (460, "spacial_rend", 41, "PINK_MANDALA", CUT, "BW2's redraw of the pink radial rays, cycled by palette anim 16"),
    (461, "lunar_dance", 42, "CRESCENT_MOON", FADE, "BW2's redraw of the crescent moon; the fade into night is kept"),
    (463, "magma_storm", 43, "MAGMA_DOTS", CUT, "BW2's redraw of the yellow heat with orange spots, shimmered by palette anim 8; tall"),
    (464, "dark_void", 44, "GREY_BANDS", FADE, "BW2's redraw of the grey bands; the fade to black is the void, kept"),
    (468, "moonblast", 42, "CRESCENT_MOON", FADE, "the crescent moon Platinum's 42 shows, redrawn; the fade into night is kept"),
]

# The trap-damage common anims of three of those moves show the same background each turn
COMMON_ANIMS = [
    ("res/battle/scripts/common_anims/damage_magma_storm.s", 43, "MAGMA_DOTS", FADE),
    ("res/battle/scripts/common_anims/damage_nightmare.s", 24, "NIGHTMARE_SWIRLS", FADE),
    ("res/battle/scripts/common_anims/damage_whirlpool.s", 35, "WHIRLPOOL", FADE),
]


def entry_id(name):
    for i, e in enumerate(ENTRIES):
        if e[0] == name:
            return BW2_BG_FIRST + i
    raise KeyError(name)


# --- conversion -----------------------------------------------------------------------------------


def tile_render(tile, colors):
    return colors[np.clip(tile, 0, 15)].astype(np.float32)


class Converted:
    """One BW2 background as our 512x256 screen, tile set, palette and mirrored screen."""

    def __init__(self, name, bw2_id, blend):
        self.name = name
        self.bg = bw2lib.Bw2Bg(bw2_id)
        self.max_tiles = MAX_TILES_BLEND if blend else MAX_TILES
        self.merged = 0
        self.rows_merged = 0
        self._convert()

    def _convert(self):
        bg = self.bg
        grid = bg.grid[MAP_ROWS]  # 32 x 64 entries
        pal = np.zeros((BW2_ROWS * 16, 3), np.int32)
        n = min(len(bg.palette), BW2_ROWS * 16)
        pal[:n] = bg.palette[:n]
        self.bw2_palette = pal

        # Empty BW2 entries (rows < 8) become tile 0, colour 0: transparent, over the black backdrop colour
        tiles = [np.zeros((8, 8), np.int32)]
        index = {tiles[0].tobytes(): (0, 0, 0)}
        rows_used = set()
        out = np.zeros(grid.shape, np.int32)

        for (y, x), v in np.ndenumerate(grid):
            row = (v >> 12) - 8
            if row < 0 or row >= BW2_ROWS:
                out[y, x] = 0
                continue
            t = bg.tiles[v & 0x3FF]
            if v & 0x400:
                t = t[:, ::-1]
            if v & 0x800:
                t = t[::-1, :]
            key = None
            for hf in (0, 1):
                for vf in (0, 1):
                    c = t
                    if hf:
                        c = c[:, ::-1]
                    if vf:
                        c = c[::-1, :]
                    k = c.tobytes()
                    if k in index:
                        key = (index[k][0], index[k][1] ^ hf, index[k][2] ^ vf)
                        break
                if key:
                    break
            if key is None:
                tiles.append(t.copy())
                index[t.tobytes()] = (len(tiles) - 1, 0, 0)
                key = (len(tiles) - 1, 0, 0)
            rows_used.add(row)
            out[y, x] = key[0] | (key[1] << 10) | (key[2] << 11) | (row << 12)

        # A one-screen picture leaves x 264..503 empty; a per-line wave (Nightmare, Whirlpool) or a big shake
        # would show black there, so it repeats the picture every 256 px. BW2's own margins (x 256..263 and
        # x -8..-1) stay.
        self.repeated = (out[:, 33:63] != 0).mean() < 0.2
        if self.repeated:
            for c in range(33, 63):
                out[:, c] = out[:, c % 32]

        self.tiles = tiles
        self.grid = out  # rows still BW2-relative (0..5)
        self._limit_tiles()
        self.rows = sorted(rows_used)

    def _limit_tiles(self):
        """Merges the closest tiles (rendered in the row they are used with most) until max_tiles fit."""
        if len(self.tiles) <= self.max_tiles:
            return
        g = self.grid
        uses = {}
        for v in g.ravel():
            if v == 0:
                continue
            uses.setdefault(v & 0x3FF, []).append(v >> 12)
        renders = np.zeros((len(self.tiles), 192), np.float32)
        for i, t in enumerate(self.tiles):
            rows = uses.get(i, [0])
            row = max(set(rows), key=rows.count)
            renders[i] = tile_render(t, self.bw2_palette[row * 16:row * 16 + 16]).ravel()
        alive = list(range(1, len(self.tiles)))
        remap = {i: i for i in range(len(self.tiles))}
        while len(alive) + 1 > self.max_tiles:
            r = renders[alive]
            d = ((r[:, None, :] - r[None, :, :]) ** 2).sum(-1)
            np.fill_diagonal(d, np.inf)
            # weight by use count so rarely used tiles go first
            a, b = np.unravel_index(np.argmin(d), d.shape)
            ta, tb = alive[a], alive[b]
            if len(uses.get(ta, [])) > len(uses.get(tb, [])):
                ta, tb = tb, ta
            remap[ta] = tb
            alive.remove(ta)
            self.merged += 1
        for k in list(remap):
            while remap[remap[k]] != remap[k]:
                remap[k] = remap[remap[k]]
        new_index = {old: i + 1 for i, old in enumerate(alive)}
        new_index[0] = 0
        new_tiles = [self.tiles[0]] + [self.tiles[o] for o in alive]
        out = np.zeros_like(g)
        for (y, x), v in np.ndenumerate(g):
            if v == 0:
                continue
            out[y, x] = (v & ~0x3FF) | new_index[remap[v & 0x3FF]]
        self.tiles = new_tiles
        self.grid = out

    # outputs

    def our_grid(self, mirrored=False):
        g = np.zeros_like(self.grid)
        for (y, x), v in np.ndenumerate(self.grid):
            row = OUR_ROWS[v >> 12] if v else 0
            e = (v & 0xFFF) | (row << 12) if v else 0
            if mirrored:
                g[y, (31 - x) % 64] = e ^ 0x400 if e else 0
            else:
                g[y, x] = e
        return g

    def our_palette(self):
        """Our rows 8..15 as 128 colours; colour 0 of every row stays as BW2's (transparent anyway)."""
        pal = np.zeros((128, 3), np.int32)
        for r in range(BW2_ROWS):
            pal[(OUR_ROWS[r] - 8) * 16:(OUR_ROWS[r] - 8) * 16 + 16] = self.bw2_palette[r * 16:r * 16 + 16]
        return pal

    def row_mask(self):
        mask = 0
        for r in self.rows:
            mask |= 1 << OUR_ROWS[r]
        return mask | (1 << OUR_ROWS[0])

    def tile_png(self, path):
        n = len(self.tiles)
        rows = (n + 31) // 32
        img = np.zeros((rows * 8, 256), np.uint8)
        for i, t in enumerate(self.tiles):
            img[(i // 32) * 8:(i // 32) * 8 + 8, (i % 32) * 8:(i % 32) * 8 + 8] = t
        im = Image.fromarray(img, "P")
        preview = self.bw2_palette[:16].astype(np.uint8).ravel().tolist()
        im.putpalette(preview + [0] * (768 - len(preview)))
        im.save(path, bits=4, optimize=False)

    def render(self, mirrored=False):
        """What our screen shows at scroll 0,0 (256x192), for the sheets."""
        g = self.our_grid(mirrored)
        pal = np.zeros((256, 3), np.int32)
        pal[128:] = self.our_palette()
        out = np.zeros((256, 512, 3), np.uint8)
        for (y, x), v in np.ndenumerate(g):
            if not v:
                continue
            t = self.tiles[v & 0x3FF]
            if v & 0x400:
                t = t[:, ::-1]
            if v & 0x800:
                t = t[::-1, :]
            ci = (v >> 12) * 16 + t
            px = pal[ci]
            px[t == 0] = 0
            out[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = px
        return out


def nscr_bytes(grid):
    """An NSCR file for a 512x256 text screen, in screen-block order (as Platinum's pl_batt_bg screens)."""
    data = bytearray()
    for block in range(2):
        for y in range(32):
            for x in range(32):
                data += struct.pack("<H", int(grid[y, block * 32 + x]))
    nrcs = b"NRCS" + struct.pack("<IHHHHI", 0x14 + len(data), 512, 256, 0, 0, len(data)) + bytes(data)
    head = b"RCSN" + struct.pack("<HHIHH", 0xFEFF, 0x0100, 0x10 + len(nrcs), 0x10, 1)
    return head + nrcs


def anim_ids():
    return sorted({e[3] for e in ENTRIES if e[3] is not None})


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    order = []
    names_png, names_pal, names_scr, names_anim_bin, names_anim_pal = [], [], [], [], []
    table = []
    for name, bw2_id, fallback, anim, blend in ENTRIES:
        c = Converted(name, bw2_id, blend)
        base = name.lower()
        c.tile_png(os.path.join(OUT_DIR, base + ".png"))
        bw2lib.write_jasc(os.path.join(OUT_DIR, base + ".pal"), c.our_palette())
        open(os.path.join(OUT_DIR, base + ".nscr"), "wb").write(nscr_bytes(c.our_grid()))
        open(os.path.join(OUT_DIR, base + "_rev.nscr"), "wb").write(nscr_bytes(c.our_grid(True)))
        names_png.append(base + ".png")
        names_pal.append(base + ".pal")
        names_scr += [base + ".nscr", base + "_rev.nscr"]
        order += [base + ".NCGR.lz", base + ".NCLR", base + ".nscr.lz", base + "_rev.nscr.lz"]
        table.append((name, bw2_id, fallback, anim, blend, len(c.tiles), c.row_mask(), c.merged))
    for k in anim_ids():
        a = bw2lib.Bw2PalAnim(k)
        top = max(a.rows) - 8 + 1
        colors = np.concatenate([a.row_colors(8 + r) for r in range(top)])
        bw2lib.write_jasc(os.path.join(OUT_DIR, "anim_%02d.pal" % k), colors)
        open(os.path.join(OUT_DIR, "anim_%02d.bin" % k), "wb").write(a.raw)
        names_anim_bin.append("anim_%02d.bin" % k)
        names_anim_pal.append("anim_%02d.pal" % k)
        order += ["anim_%02d.bin" % k, "anim_%02d.NCLR" % k]
    open(os.path.join(OUT_DIR, NARC_BASENAME + ".order"), "w").write("\n".join(order) + "\n")
    write_meson(names_png, names_pal, names_scr, names_anim_bin, names_anim_pal)
    write_headers(table)
    return table


def write_meson(pngs, pals, scrs, anim_bins, anim_pals):
    def lst(items):
        return "\n".join("    '%s'," % i for i in items)

    text = f"""# Generated by tools/effect_bg/bw2_effect_bg.py build: BW2's battle effect backgrounds (pokebw2
# res/graphics/btlv_effvm_bg, btlv_effvm_pal_anim), converted for our BG3. Do not edit by hand.

{NARC_BASENAME}_order = files('{NARC_BASENAME}.order')

{NARC_BASENAME}_ncgr = ncgr_lz_gen.process(files(
{lst(pngs)}
), extra_args: [ '-bitdepth', '4' ])

{NARC_BASENAME}_nclr = nclr_gen.process(files(
{lst(pals + anim_pals)}
), extra_args: [ '-bitdepth', '4' ])

{NARC_BASENAME}_nscr = lz_gen.process(files(
{lst(scrs)}
))

{NARC_BASENAME}_anim = copy_gen.process(files(
{lst(anim_bins)}
))

{NARC_BASENAME}_narc = custom_target('{NARC_BASENAME}.narc',
    output: [
        '{NARC_BASENAME}.narc',
        '{NARC_BASENAME}.naix.h',
    ],
    input: [
        {NARC_BASENAME}_ncgr,
        {NARC_BASENAME}_nclr,
        {NARC_BASENAME}_nscr,
        {NARC_BASENAME}_anim,
    ],
    command: [
        narc_exe, 'create',
        '--naix',
        '--order', {NARC_BASENAME}_order,
        '--output', '@OUTPUT0@',
        '@PRIVATE_DIR@',
    ]
)

nitrofs_files += {NARC_BASENAME}_narc
naix_headers += {NARC_BASENAME}_narc[1]
"""
    open(os.path.join(OUT_DIR, "meson.build"), "w").write(text)


def write_headers(table):
    lines = [
        "#ifndef POKEPLATINUM_CONSTANTS_BATTLE_BATTLE_EFFECT_BG_H",
        "#define POKEPLATINUM_CONSTANTS_BATTLE_BATTLE_EFFECT_BG_H",
        "",
        "// Generated by tools/effect_bg/bw2_effect_bg.py build. Do not edit by hand.",
        "// SwitchBg/RestoreBg bgIDs from BATTLE_BG_BW2_FIRST name Black 2/White 2's effect backgrounds",
        "// (bw2_effect_bg.narc); 0-57 stay pl_batt_bg.narc's. docs/living_battle_stage/effect_bg.md lists them.",
        "",
        "#define BATTLE_BG_BW2_FIRST %d" % BW2_BG_FIRST,
    ]
    for i, (name, bw2_id, *_rest) in enumerate(table):
        lines.append("#define BATTLE_BG_BW2_%-18s (BATTLE_BG_BW2_FIRST + %d) // BW2 effect BG %03d: %s"
                     % (name, i, bw2_id, catalogue.BGS[bw2_id][1]))
    lines += [
        "#define BATTLE_BG_BW2_COUNT %d" % len(table),
        "",
        "// BW2 palette anims (btlv_effvm_pal_anim), for BgPalAnim",
    ]
    for k in anim_ids():
        lines.append("#define BATTLE_BG_PAL_ANIM_%02d %d // %s (BW2 BG %03d)" % (k, k, catalogue.ANIMS[k][1], catalogue.ANIMS[k][0]))
    lines += ["#define BATTLE_BG_PAL_ANIM_STOP 255", "", "#endif // POKEPLATINUM_CONSTANTS_BATTLE_BATTLE_EFFECT_BG_H", ""]
    open(CONST_H, "w").write("\n".join(lines))

    rows = [
        "// Generated by tools/effect_bg/bw2_effect_bg.py build. Do not edit by hand.",
        "// Included once, by battle_anim_effect_bg.c.",
        "",
        "static const BattleEffectBgEntry sBattleEffectBgs[BATTLE_BG_BW2_COUNT] = {",
    ]
    for name, bw2_id, fallback, anim, blend, ntiles, mask, merged in table:
        b = name.lower()
        anim_member = "anim_%02d_bin" % anim if anim is not None else "BATTLE_EFFECT_BG_NO_MEMBER"
        rows.append(
            "    [BATTLE_BG_BW2_%s - BATTLE_BG_BW2_FIRST] = { %s_NCGR_lz, %s_NCLR, %s_nscr_lz, %s_rev_nscr_lz, %s, 0x%04X, %d, %d }, // BW2 %03d, %d tiles%s"
            % (name, b, b, b, b,
               anim_member, mask, fallback, ntiles, bw2_id, ntiles, (", %d merged" % merged) if merged else ""))
    rows += ["};", ""]
    rows += ["static const u16 sBattleEffectBgPalAnimMembers[][2] = {"]
    for k in anim_ids():
        rows.append("    { %d, anim_%02d_bin }," % (k, k))
    rows += ["};", ""]
    open(DATA_H, "w").write("\n".join(rows))


# --- applying the mapping to the scripts ------------------------------------------------------------


def apply():
    import re

    changed = []
    jobs = [(os.path.join(ROOT, "res/battle/moves", d, "anim.s"), plat, ent, mode) for _m, d, plat, ent, mode, _r in MOVES]
    jobs += [(os.path.join(ROOT, p), plat, ent, mode) for p, plat, ent, mode in COMMON_ANIMS]
    for path, plat, ent, mode in jobs:
        s = open(path).read()
        new = s
        for cmd in ("SwitchBg", "RestoreBg"):
            pat = re.compile(r"(%s )(\d+), BATTLE_BG_SWITCH_MODE_(FADE|BLEND)" % cmd)
            new = pat.sub(lambda m: "%sBATTLE_BG_BW2_%s, %s" % (m.group(1), ent, mode), new)
        if new != s:
            open(path, "w").write(new)
            changed.append(os.path.relpath(path, ROOT))
    print("\n".join(changed))
    print(len(changed), "files")


# --- sheets -------------------------------------------------------------------------------------------


def _label(img, text):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.size[0], 11], fill=(30, 30, 30))
    d.text((2, 0), text, fill=(255, 255, 0))
    return img


def visible(bg_img):
    """BW2's visible 256x192 at scroll 0,0 with its 8 px margin (272x208), wrapping as the 512x512 map does."""
    h, w = bg_img.shape[:2]
    ys = [(y - 8) % h for y in range(208)]
    xs = [(x - 8) % w for x in range(272)]
    return bg_img[np.ix_(ys, xs)]


def sheet(outdir):
    os.makedirs(outdir, exist_ok=True)
    cell_w, cell_h = 272, 208 + 26
    cols = 7
    ids = bw2lib.BG_IDS
    S = Image.new("RGB", (cols * (cell_w + 4), ((len(ids) + cols - 1) // cols) * (cell_h + 4)), (50, 50, 50))
    for k, n in enumerate(ids):
        b = bw2lib.Bw2Bg(n)
        img = Image.fromarray(visible(b.render()))
        cell = Image.new("RGB", (cell_w, cell_h), (30, 30, 30))
        cell.paste(img, (0, 26))
        cat, desc, size = catalogue.BGS[n]
        d = ImageDraw.Draw(cell)
        d.text((2, 1), "BW2 %03d  [%s, %s]" % (n, cat, size), fill=(255, 255, 0))
        d.text((2, 13), desc[:44], fill=(220, 220, 220))
        S.paste(cell, ((k % cols) * (cell_w + 4), (k // cols) * (cell_h + 4)))
    S.save(os.path.join(outdir, "bw2_effect_bgs.png"))

    # palette anims: every row of each anim on its background
    rows = []
    for k in bw2lib.ANIM_IDS:
        n, what = catalogue.ANIMS[k]
        a = bw2lib.Bw2PalAnim(k)
        b = bw2lib.Bw2Bg(n)
        frames = []
        for r in a.rows[:14]:
            p = b.palette.copy()
            p[:16] = a.row_colors(r)
            frames.append(Image.fromarray(b.render(p)[:192, :256]).resize((128, 96)))
        rows.append((k, n, what, a, frames))
    W = 14 * 130 + 230
    S = Image.new("RGB", (W, len(rows) * 100), (50, 50, 50))
    d = ImageDraw.Draw(S)
    for i, (k, n, what, a, frames) in enumerate(rows):
        d.text((2, i * 100 + 20), "anim %02d -> BG %03d" % (k, n), fill=(255, 255, 0))
        d.text((2, i * 100 + 34), "rows %s" % ",".join(map(str, a.rows))[:34], fill=(200, 200, 200))
        d.text((2, i * 100 + 48), "frames %s" % ",".join(map(str, a.frames))[:34], fill=(200, 200, 200))
        d.text((2, i * 100 + 62), what[:36], fill=(200, 200, 200))
        for j, im in enumerate(frames):
            S.paste(im, (230 + j * 130, i * 100))
    S.save(os.path.join(outdir, "bw2_pal_anims.png"))

    # Poke Ball OBJ sheets (not backgrounds)
    S = Image.new("RGB", (len(bw2lib.BALL_SHEETS) * 40, 560), (50, 50, 50))
    d = ImageDraw.Draw(S)
    for k, n in enumerate(bw2lib.BALL_SHEETS):
        im = np.array(Image.open(os.path.join(bw2lib.BG_DIR, "%03d.png" % n)))
        p = bw2lib.read_jasc(os.path.join(bw2lib.BG_DIR, "%03d.pal" % (n + 1))).astype(np.uint8)
        rgb = p[np.clip(im, 0, len(p) - 1)]
        rgb[im == 0] = 0
        S.paste(Image.fromarray(rgb), (k * 40, 14))
        d.text((k * 40, 0), str(n), fill=(255, 255, 0))
    S.save(os.path.join(outdir, "bw2_ball_sheets.png"))

    # the mapping: Platinum picture -> our converted BW2 picture (what the screen shows at scroll 0)
    sys.path.insert(0, os.path.join(ROOT, "tools/battle_stage"))
    plat = PlatinumBgs()
    cache = {}
    cw, ch = 256, 192
    rows = MOVES
    S = Image.new("RGB", (4 * (2 * cw + 30), ((len(rows) + 3) // 4) * (ch + 40)), (50, 50, 50))
    d = ImageDraw.Draw(S)
    for k, (mid, dname, pid, ent, mode, reason) in enumerate(rows):
        i = entry_id(ent) - BW2_BG_FIRST
        if ent not in cache:
            e = ENTRIES[i]
            cache[ent] = Converted(e[0], e[1], e[4]).render()[:192, :256]
        x = (k % 4) * (2 * cw + 30)
        y = (k // 4) * (ch + 40)
        S.paste(Image.fromarray(plat.render(pid)[:192, :256]), (x, y + 28))
        S.paste(Image.fromarray(cache[ent]), (x + cw + 4, y + 28))
        d.text((x + 2, y + 2), "%03d %s: Platinum %d -> BW2 %03d %s (%s)" % (mid, dname, pid, ENTRIES[i][1], ent, mode.split("_")[-1]), fill=(255, 255, 0))
        d.text((x + 2, y + 14), reason[:84], fill=(210, 210, 210))
    S.save(os.path.join(outdir, "mapping.png"))
    print("sheets in", outdir)


class PlatinumBgs:
    """Renders pl_batt_bg.narc's effect backgrounds (bgID 0-57) with their own palette, for the mapping sheet."""

    def __init__(self):
        import re

        import nitro

        self.nitro = nitro
        src = open(os.path.join(ROOT, "src/battle_anim/battle_anim_system.c")).read()
        tab = src[src.index("sBgNarcIndices[][BG_NARC_MEMBER_COUNT] = {"):]
        tab = tab[:tab.index("};")]
        self.rows = [tuple(int(x, 16) for x in r)
                     for r in re.findall(r"\{ (0x\w+), (0x\w+), (0x\w+), (0x\w+), (0x\w+) \}", tab)]
        self.narc = nitro.read_narc(os.path.join(ROOT, "res/prebuilt/battle/graphic/pl_batt_bg.narc"))

    def _dec(self, d):
        return self.nitro.lz77_decompress(d) if d[:1] == b"\x10" else d

    def render(self, i):
        nitro = self.nitro
        g = self._dec(self.narc[self.rows[i][0]])
        s = self._dec(self.narc[self.rows[i][2]])
        pal = nitro.read_nclr(self.narc[self.rows[i][1]])
        col = np.array([nitro.gxrgb_to_rgb888(c) for c in pal[:16]], np.uint8)
        size = struct.unpack("<I", g[40:44])[0]
        raw = np.frombuffer(g[48:48 + size], np.uint8)
        px = np.zeros(len(raw) * 2, np.uint8)
        px[0::2] = raw & 15
        px[1::2] = raw >> 4
        tiles = px.reshape(-1, 8, 8)
        sw, sh = struct.unpack("<HH", s[24:28])
        ssz = struct.unpack("<I", s[32:36])[0]
        ent = struct.unpack("<%dH" % (ssz // 2), s[36:36 + ssz])
        tw = sw // 8
        out = np.zeros((sh, sw, 3), np.uint8)
        for k, v in enumerate(ent):
            b, j = divmod(k, 1024)
            bx, by = b % max(tw // 32, 1), b // max(tw // 32, 1)
            tx, ty = bx * 32 + j % 32, by * 32 + j // 32
            t = tiles[(v & 0x3FF) % len(tiles)]
            if v & 0x400:
                t = t[:, ::-1]
            if v & 0x800:
                t = t[::-1, :]
            out[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8] = col[t]
        return out


def vram():
    print("%-18s %4s %6s %5s %s" % ("entry", "BW2", "tiles", "KB", "rows"))
    worst = 0
    for name, bw2_id, _f, _a, blend in ENTRIES:
        c = Converted(name, bw2_id, blend)
        kb = len(c.tiles) * 32 / 1024
        worst = max(worst, kb)
        rows = [OUR_ROWS[r] for r in c.rows]
        print("%-18s %03d %6d %5.1f %s%s%s" % (name, bw2_id, len(c.tiles), kb, rows, " BLEND" if blend else "",
                                            " (%d merged)" % c.merged if c.merged else ""))
    print("largest tile set %.1f KB" % worst)


def redo():
    """docs/living_battle_stage/redo/effect_bg.json for the critic's move_redo and switchbg_moves (--moves), and
    the cut moves' expectation in the other redo files that list them."""
    import json

    redo_dir = os.path.join(ROOT, "docs/living_battle_stage/redo")
    out = []
    names = {}
    for mid, dname, pid, ent, mode, reason in MOVES:
        e = ENTRIES[entry_id(ent) - BW2_BG_FIRST]
        expect = {CUT: "cut", FADE: "fade", BLEND: "fade"}[mode]
        how = {CUT: "the arena cuts (no fade) to", FADE: "the arena fades to", BLEND: "the arena fades and BG3 blends to"}[mode]
        names[mid] = (expect, how, e)
        item = {"id": mid, "name": dname.upper(), "category": "effect_bg", "expect": expect, "needs": [],
                "min_change_pct": 3, "bw2_bg": True, "bw2_bg_id": entry_id(ent),
                "effect": "%s BW2 effect BG %03d (%s: %s); Platinum showed bgID %d" % (how, e[1], ent, catalogue.BGS[e[1]][1], pid)}
        if e[3] is not None:
            item["pal_anim"] = True
        out.append(item)
    with open(os.path.join(redo_dir, "effect_bg.json"), "w") as f:
        f.write("[\n" + ",\n".join(json.dumps(i) for i in out) + "\n]\n")
    # Edit the other files line by line, so their own formatting stays
    for other in ("shake.json", "silhouette.json"):
        path = os.path.join(redo_dir, other)
        text = open(path).read()
        for item in json.loads(text):
            if item["id"] not in names or item["expect"] != "fade" or names[item["id"]][0] != "cut":
                continue
            expect, how, e = names[item["id"]]
            old_effect = json.dumps(item["effect"])[1:-1]
            new_effect = item["effect"].replace("the arena fades to", how).replace(
                "the arena fades for SwitchBg", "the arena cuts for SwitchBg")
            new_effect += " (bw2vis:effect-bg: BW2 effect BG %03d %s)" % (e[1], e[0])
            start = text.index('"id": %d,' % item["id"])
            end = text.index("}", text.index(old_effect, start) + len(old_effect))
            chunk = text[start:end]
            chunk = chunk.replace('"expect": "fade"', '"expect": "cut"').replace(old_effect, json.dumps(new_effect)[1:-1])
            text = text[:start] + chunk + text[end:]
        open(path, "w").write(text)


def doc():
    """Markdown tables for docs/living_battle_stage/effect_bg.md: the catalogue, the anims, the mapping, VRAM."""
    used = {e[1]: e[0] for e in ENTRIES}
    print("| BW2 id | kind | what it shows | size | imported as |")
    print("|---|---|---|---|---|")
    for n in bw2lib.BG_IDS:
        cat, desc, size = catalogue.BGS[n]
        print("| %03d | %s | %s | %s | %s |" % (n, cat, desc, size, ("`BATTLE_BG_BW2_%s`" % used[n]) if n in used else "-"))
    print()
    print("| anim | background | what it does | rows | frame counts |")
    print("|---|---|---|---|---|")
    for k in bw2lib.ANIM_IDS:
        n, what = catalogue.ANIMS[k]
        a = bw2lib.Bw2PalAnim(k)
        print("| %02d | %03d | %s | %s | %s |" % (k, n, what, ",".join(map(str, a.rows)), ",".join(map(str, a.frames))))
    print()
    print("| move | Platinum bgID | BW2 background | transition | why |")
    print("|---|---|---|---|---|")
    for mid, dname, pid, ent, mode, reason in MOVES:
        e = ENTRIES[entry_id(ent) - BW2_BG_FIRST]
        print("| %03d %s | %d | %03d `%s`%s | %s | %s |" % (mid, dname, pid, e[1], ent, " (anim %02d)" % e[3] if e[3] is not None else "",
                                                       mode.split("_")[-1].lower(), reason))
    print()
    print("| entry | BW2 id | tiles | BG VRAM | palette rows | anim |")
    print("|---|---|---|---|---|---|")
    total = 0
    for name, bw2_id, _f, anim, blend in ENTRIES:
        c = Converted(name, bw2_id, blend)
        kb = len(c.tiles) * 32 / 1024
        total += kb
        print("| %s | %03d | %d%s | %.1f KB | %s | %s |" % (name, bw2_id, len(c.tiles), " (%d merged, BLEND)" % c.merged if blend else "",
                                                 kb, ", ".join(str(OUR_ROWS[r]) for r in c.rows), "%02d" % anim if anim is not None else "-"))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "sheet":
        sheet(sys.argv[2])
    elif cmd == "build":
        for row in build():
            print(row)
    elif cmd == "apply":
        apply()
    elif cmd == "doc":
        doc()
    elif cmd == "redo":
        redo()
    elif cmd == "vram":
        vram()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

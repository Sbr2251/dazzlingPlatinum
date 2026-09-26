"""The classic 2D battle scene the arena has to reproduce at home pose.

Backdrop (BG3): pl_batt_bg.narc, drawn by BattleSystem_LoadBackground (ov16_0223B140.c)
    NCGR  member 3 + background        (8bpp, 1024 tiles)
    NSCR  member 2                     (shared by all backgrounds, 512x256)
    NCLR  member 172 + background * 3 + timeOfDay   (day, twilight, night)
  The 512-wide map is two 256x256 screen blocks and the right block is an exact
  mirror of the left one, so every BG3 X scroll is reproduced by a 256-wide texture
  with REPEAT_S | FLIP_S. At scroll 0,0 the screen shows map columns 0..255 and rows
  0..191: sky rows 0..49, the dark tree line 50..57, ground 58..159, and rows 160..255
  are colour 0 (black). Rows 144..191 are always under BG1 (the black intro box, then
  the text box), so only rows 0..143 are ever seen.

Platforms (OBJ): pl_batt_obj.narc, loaded by ov16_02268520 (ov16_02268520.c)
    NCGR  PLATFORM_CHAR[side][terrain] (4bpp, 1D mapping)
    NCER  member 128 (player), 131 (enemy); cell 0
    NCLR  PLATFORM_PALETTE[terrain][timeOfDay], 16 colours, colour 0 transparent
  The palette goes to the OBJ palette row the sprite system hands out for resource
  20009 (found with SpriteManager_FindPlttResourceOffset), and is also copied to BG
  palette row 7, which no backdrop tile uses. The sprites sit at priority 3, above BG3.
"""

import os

import nitro

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
BG_NARC = os.path.join(ROOT, "res/prebuilt/battle/graphic/pl_batt_bg.narc")
OBJ_NARC = os.path.join(ROOT, "res/prebuilt/battle/graphic/pl_batt_obj.narc")

TIMES_OF_DAY = ("day", "twilight", "night")

BG_NSCR_MEMBER = 2
BG_NCGR_BASE = 3
BG_NCLR_BASE = 172

SIDE_PLAYER = 0
SIDE_ENEMY = 1

# Unk_ov16_0227009C / Unk_ov16_0227006C in ov16_02268520.c, indexed by terrain
PLATFORM_CHAR = (
    (0x87, 0x91, 0x7F, 0x97, 0x8B, 0x95, 0x8D, 0x85, 0x89, 0x8F, 0x93, 0x97,
     0x99, 0x9B, 0x9D, 0x9F, 0xA1, 0xA3, 0xA5, 0xA7, 0xA9, 0xAB, 0xAD, 0xAF),
    (0x88, 0x92, 0x82, 0x98, 0x8C, 0x96, 0x8E, 0x86, 0x8A, 0x90, 0x94, 0x94,
     0x9A, 0x9C, 0x9E, 0xA0, 0xA2, 0xA4, 0xA6, 0xA8, 0xAA, 0xAC, 0xAE, 0xB0),
)
PLATFORM_CELL = (128, 131)

# Unk_ov16_02270134, [terrain][timeOfDay]; chunk 1 only needs TERRAIN_PLAIN and
# TERRAIN_GRASS
PLATFORM_PALETTE = ((0x7, 0x8, 0x9), (0x16, 0x17, 0x18), (0x1, 0x2, 0x3))

# Sprite position once the intro slide is over (the templates in ov16_02268520.c start
# them off screen at x 0x150 and -80)
PLATFORM_HOME = ((64, 136), (192, 88))


class Backdrop:
    """BG3 backdrop of one BACKGROUND_*: image[y][x] (512x256 palette indices) and the
    256-colour palette of each time of day."""

    def __init__(self, background):
        members = nitro.read_narc(BG_NARC)
        ncgr = nitro.Ncgr(members[BG_NCGR_BASE + background])
        nscr = nitro.Nscr(members[BG_NSCR_MEMBER])
        assert ncgr.bpp == 8
        self.width, self.height = nscr.width, nscr.height
        self.image = nitro.render_bg_256(ncgr, nscr)
        self.palettes = []

        for tod in range(len(TIMES_OF_DAY)):
            pltt = nitro.read_nclr(members[BG_NCLR_BASE + background * 3 + tod])
            self.palettes.append((pltt + [0] * 256)[:256])

    def is_mirrored(self):
        """TRUE when map column 511 - x equals column x on every row."""
        w = self.width
        return all(row[x] == row[w - 1 - x] for row in self.image for x in range(w // 2))

    def screen(self, scroll_x=0, scroll_y=0):
        """The 256x192 screen BG3 shows at the given scroll."""
        return [[self.image[(y + scroll_y) % self.height][(x + scroll_x) % self.width] for x in range(256)] for y in range(192)]


class Platform:
    """Platform OBJ of one side and terrain: pixels {(dx, dy): index} relative to the
    sprite position, and the 16-colour palette of each time of day."""

    def __init__(self, side, terrain):
        members = nitro.read_narc(OBJ_NARC)
        self.side = side
        self.char_member = PLATFORM_CHAR[side][terrain]
        self.cell_member = PLATFORM_CELL[side]
        self.palette_members = PLATFORM_PALETTE[terrain]
        ncgr = nitro.Ncgr(members[self.char_member])
        ncer = nitro.Ncer(members[self.cell_member])
        assert ncgr.bpp == 4
        self.pixels, self.oams = nitro.render_cell(ncgr, ncer, 0)
        self.home = PLATFORM_HOME[side]
        self.palettes = [nitro.read_nclr(members[m])[:16] for m in self.palette_members]

    def bbox(self):
        """(x0, y0, x1, y1) of the opaque pixels relative to the sprite, inclusive."""
        xs = [p[0] for p in self.pixels]
        ys = [p[1] for p in self.pixels]
        return min(xs), min(ys), max(xs), max(ys)

    def screen_pixels(self):
        """{(x, y): index} at the home position."""
        hx, hy = self.home
        return {(x + hx, y + hy): i for (x, y), i in self.pixels.items()}


LAYER_BG = 0
LAYER_PLAYER = 1
LAYER_ENEMY = 2


def classic_frame(backdrop, platforms):
    """The classic home screen as [y][x] = (layer, palette index): BG3 at scroll 0,0
    with both platform OBJs on top."""
    screen = backdrop.screen()
    frame = [[(LAYER_BG, screen[y][x]) for x in range(256)] for y in range(192)]

    for plat in platforms:
        layer = LAYER_PLAYER if plat.side == SIDE_PLAYER else LAYER_ENEMY

        for (x, y), index in plat.screen_pixels().items():
            if 0 <= x < 256 and 0 <= y < 192:
                frame[y][x] = (layer, index)

    return frame


def frame_rgb(frame, backdrop, platforms, tod):
    """Resolves a (layer, index) frame to RGB888 rows with the palettes of one time of
    day. Pixels with layer None (nothing drawn) come out magenta."""
    bg = [nitro.gxrgb_to_rgb888(c) for c in backdrop.palettes[tod]]
    obj = {}

    for plat in platforms:
        layer = LAYER_PLAYER if plat.side == SIDE_PLAYER else LAYER_ENEMY
        obj[layer] = [nitro.gxrgb_to_rgb888(c) for c in plat.palettes[tod]]

    out = []

    for row in frame:
        line = []

        for layer, index in row:
            if layer is None:
                line.append((255, 0, 255))
            elif layer == LAYER_BG:
                line.append(bg[index])
            else:
                line.append(obj[layer][index])

        out.append(line)

    return out

#!/usr/bin/env python3
"""Generate the Distortion World main menu (Continue / New Game card picker).

Writes into res/graphics/main_menu/:
    menu_top_continue.png   + .NSCR  (+ menu_top_continue_female.NSCR)
    menu_top_new_game.png   + .NSCR
    menu_bottom_continue.png + .NSCR
    menu_bottom_new_game.png + .NSCR

Every PNG is a full-screen opaque 8bpp image. Everything static is baked
into these images. src/main_menu/main_menu.c prints only the dynamic values
on BG0: player name, play time, Pokedex count, party levels, location and
party icons.

Top screen palette (both top images share it, must match main_menu.c):
    0         backdrop
    1..31     reserved for the BG0 text palette
    32..39    badge fills, one index per badge (recoloured at runtime)
    40..47    badge rims, one index per badge
    48..255   general colours

Bottom screen palette (both bottom images share it):
    0         backdrop
    1..63     reserved for the BG0 text palette and the 3 party icon palettes
    64..255   general colours

The Continue top image has extra tiles after row 23 holding the female
trainer portrait. menu_top_continue_female.NSCR points the portrait area at
those tiles.

The on-screen positions below are mirrored as constants in main_menu.c.
Keep them in sync.

Needs PIL (/usr/bin/python3 on macOS).

Usage: python3 make_main_menu.py [--preview-dir DIR]
"""

import argparse
import json
import os
import re
import struct

from PIL import Image, ImageDraw, ImageFilter

import make_top_screen as ts

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(REPO, "res", "graphics", "main_menu")

W, H = 256, 192
SS = ts.SS

WHITE = (248, 248, 248)
LAV = (200, 180, 240)
LAV_DIM = (140, 120, 180)
SHADOW = (40, 20, 64)
RED = (214, 18, 22)
PANEL = (24, 10, 44)
EDGE = (150, 110, 220)
SLOT_FILL = (44, 20, 78)
SLOT_EDGE = (110, 80, 170)

TOP_BADGE_FILL = 32
TOP_BADGE_RIM = 40
TOP_GENERAL = 48
BOTTOM_GENERAL = 64

CARD = (36, 38, 220, 164)
PEEK_L = (-60, 50, 22, 152)
PEEK_R = (234, 50, 316, 152)
BADGE_X = CARD[0] + 70  # left edge of the badge row
BADGE_Y = CARD[1] + 30 + 3 * 17 + 16
BADGE_STEP = 13

# Party slots: 3x2 grid, tile aligned so BG0 can place the icons.
SLOT_X = [24, 96, 168]
SLOT_Y = [48, 88]
SLOT_W, SLOT_H = 64, 32


# --- DS system font -------------------------------------------------------

class Font:
    def __init__(self, name="system"):
        self.cmap = {}
        for line in open(os.path.join(REPO, "tools", "msgenc", "charmap.txt"), encoding="utf-8"):
            line = line.split("//")[0].rstrip("\n")
            m = re.match(r"\s*([0-9A-Fa-f]{4})=(.+)$", line)
            if m and len(m.group(2)) == 1 and m.group(2) not in self.cmap:
                self.cmap[m.group(2)] = int(m.group(1), 16)
        self.cmap[" "] = 0x1DE
        self.cmap["'"] = 0x1B3
        self.sheet = Image.open(os.path.join(REPO, "res", "fonts", f"font_{name}.png"))
        meta = json.load(open(os.path.join(REPO, "res", "fonts", f"font_{name}.json")))
        self.widths = meta["glyphWidths"]
        self.cw, self.ch = meta["maxGlyphWidth"], meta["maxGlyphHeight"]
        self.cols = self.sheet.width // self.cw

    def glyph(self, c):
        g = self.cmap[c] - 1
        x, y = (g % self.cols) * self.cw, (g // self.cols) * self.ch
        return self.sheet.crop((x, y, x + self.cw, y + self.ch)), self.widths[g]

    def width(self, s):
        return sum(self.glyph(c)[1] for c in s)

    def draw(self, img, x, y, s, fg, shadow):
        px = img.load()
        for c in s:
            gl, w = self.glyph(c)
            gp = gl.load()
            for yy in range(self.ch):
                for xx in range(self.cw):
                    v = gp[xx, yy]
                    col = fg if v == 1 else (shadow if v == 2 else None)
                    if col is not None and 0 <= x + xx < img.width and 0 <= y + yy < img.height:
                        px[x + xx, y + yy] = col + (255,)
            x += w
        return x


font = Font()


def text(img, x, y, s, fg=WHITE, sh=SHADOW, center=False):
    if center:
        x -= font.width(s) // 2
    return font.draw(img, x, y, s, fg, sh)


# --- drawing helpers (same look as the approved mock) ---------------------

def background():
    im = ts.sky()
    layer = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ts.border(d, 7, True, 11)
    ts.border(d, H - 6, False, 12)
    im.alpha_composite(layer.resize((W, H), Image.LANCZOS))
    return im


def panel(img, box, fill=PANEL, alpha=225, edge=EDGE, glow=True, radius=5):
    x0, y0, x1, y1 = box
    lay = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius * SS, fill=fill + (alpha,), outline=edge + (255,), width=SS)
    d.line([((x0 + radius) * SS, (y0 + 2) * SS), ((x1 - radius) * SS, (y0 + 2) * SS)], fill=(90, 60, 140, 255), width=SS)
    lay = lay.resize((W, H), Image.LANCZOS)
    if glow:
        a = lay.split()[3].filter(ImageFilter.GaussianBlur(4)).point(lambda v: int(v * 0.55))
        g = Image.new("RGBA", (W, H), (150, 70, 255, 0))
        g.putalpha(a)
        img.alpha_composite(g)
    img.alpha_composite(lay)


def red_rule(img, cx, y, half):
    for i in range(-half, half + 1):
        t = 1 - abs(i) / half
        a = int(255 * min(1, t * 2.2))
        img.alpha_composite(Image.new("RGBA", (1, 1), RED + (a,)), (cx + i, y))


def chevron(img, cx, cy, left, bright):
    lay = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    s = 5
    if left:
        pts = [(cx + s * 0.6, cy - s), (cx - s * 0.6, cy), (cx + s * 0.6, cy + s)]
    else:
        pts = [(cx - s * 0.6, cy - s), (cx + s * 0.6, cy), (cx - s * 0.6, cy + s)]
    d.line([(x * SS, y * SS) for x, y in pts], fill=(WHITE if bright else LAV_DIM) + (255,), width=int(2.2 * SS), joint="curve")
    lay = lay.resize((W, H), Image.LANCZOS)
    a = lay.split()[3].filter(ImageFilter.GaussianBlur(2.5))
    g = Image.new("RGBA", (W, H), (170, 90, 255, 0))
    g.putalpha(a)
    img.alpha_composite(g)
    img.alpha_composite(lay)


def pokeball(img, cx, cy, r):
    lay = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    R = r * SS
    X, Y = cx * SS, cy * SS
    d.pieslice([X - R, Y - R, X + R, Y + R], 180, 360, fill=(120, 60, 200, 255))
    d.pieslice([X - R, Y - R, X + R, Y + R], 0, 180, fill=(230, 226, 240, 255))
    d.rectangle([X - R, Y - SS * 1.2, X + R, Y + SS * 1.2], fill=(20, 8, 30, 255))
    d.ellipse([X - R, Y - R, X + R, Y + R], outline=(20, 8, 30, 255), width=int(SS * 1.4))
    d.ellipse([X - R * 0.32, Y - R * 0.32, X + R * 0.32, Y + R * 0.32], fill=(20, 8, 30, 255))
    d.ellipse([X - R * 0.2, Y - R * 0.2, X + R * 0.2, Y + R * 0.2], fill=(250, 250, 255, 255))
    d.arc([X - R * 0.75, Y - R * 0.75, X + R * 0.75, Y + R * 0.75], 200, 250, fill=(210, 170, 255, 255), width=SS)
    img.alpha_composite(lay.resize((W, H), Image.LANCZOS))


def badge_masks():
    """Per-badge fill and rim masks, hard-edged so each maps to one palette index."""
    fills, rims = [], []
    for i in range(8):
        cx = (BADGE_X + i * BADGE_STEP + 5) * SS
        cy = (BADGE_Y + 5) * SS
        r = 4.5 * SS
        outer = Image.new("L", (W * SS, H * SS), 0)
        ImageDraw.Draw(outer).regular_polygon((cx, cy, r), 6, rotation=30, fill=255)
        inner = Image.new("L", (W * SS, H * SS), 0)
        ImageDraw.Draw(inner).regular_polygon((cx, cy, r - SS * 1.1), 6, rotation=30, fill=255)
        outer = outer.resize((W, H), Image.BOX).point(lambda v: 255 if v >= 128 else 0)
        inner = inner.resize((W, H), Image.BOX).point(lambda v: 255 if v >= 128 else 0)
        fills.append({(x, y) for y in range(H) for x in range(W) if inner.getpixel((x, y))})
        rims.append({(x, y) for y in range(H) for x in range(W) if outer.getpixel((x, y)) and not inner.getpixel((x, y))})
    return fills, rims


def tabs(img, active):
    labels = ["CONTINUE", "NEW GAME"]
    gap = 22
    widths = [font.width(s) for s in labels]
    total = sum(widths) + gap
    x = (W - total) // 2
    for i, s in enumerate(labels):
        on = i == active
        text(img, x, 14, s, WHITE if on else LAV_DIM)
        if on:
            red_rule(img, x + widths[i] // 2, 28, widths[i] // 2 + 4)
            red_rule(img, x + widths[i] // 2, 29, widths[i] // 2)
        x += widths[i] + gap
    cx = (W - total) // 2 + widths[0] + gap // 2
    img.alpha_composite(Image.new("RGBA", (2, 2), LAV_DIM + (255,)), (cx - 1, 20))


def page_dots(img, active):
    lay = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    y = 174
    for i in range(2):
        cx = W // 2 + (i - 0.5) * 12
        if i == active:
            d.rounded_rectangle([(cx - 5) * SS, (y - 2) * SS, (cx + 5) * SS, (y + 2) * SS], 2 * SS, fill=WHITE + (255,))
        else:
            d.ellipse([(cx - 2) * SS, (y - 2) * SS, (cx + 2) * SS, (y + 2) * SS], fill=LAV_DIM + (255,))
    img.alpha_composite(lay.resize((W, H), Image.LANCZOS))


def trainer_portrait(img, fx0, fy0, cls):
    spr = Image.open(os.path.join(REPO, "res", "trainers", "classes", cls, "front.png"))
    rgba = spr.convert("RGBA")
    px, idx = rgba.load(), spr.load()
    for yy in range(spr.height):
        for xx in range(spr.width):
            if idx[xx, yy] == 0:
                px[xx, yy] = (0, 0, 0, 0)
    rgba = rgba.crop(rgba.getbbox())
    sx = fx0 + 26 - rgba.width // 2
    sy = fy0 + 74 - rgba.height
    clip = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    clip.alpha_composite(rgba, (sx, sy))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([fx0 + 1, fy0 + 1, fx0 + 51, fy0 + 75], 3, fill=255)
    clip.putalpha(Image.composite(clip.split()[3], Image.new("L", (W, H), 0), mask))
    img.alpha_composite(clip)


def continue_card(img, box, dim=False, trainer="player_male"):
    x0, y0, x1, y1 = box
    panel(img, box, glow=not dim, alpha=170 if dim else 235, edge=(90, 70, 130) if dim else EDGE)
    if dim:
        return
    text(img, x0 + 10, y0 + 7, "CONTINUE")
    red_rule(img, x0 + 10 + 26, y0 + 22, 26)
    fx0, fy0 = x0 + 10, y0 + 28
    panel(img, (fx0, fy0, fx0 + 52, fy0 + 76), fill=SLOT_FILL, alpha=255, edge=SLOT_EDGE, glow=False, radius=3)
    trainer_portrait(img, fx0, fy0, trainer)
    sx0 = x0 + 70
    y = y0 + 30
    for label in ["PLAYER", "TIME", "POKéDEX"]:
        text(img, sx0, y, label, LAV)
        y += 17
    text(img, sx0, y, "BADGES", LAV)


def new_game_card(img, box, dim=False):
    x0, y0, x1, y1 = box
    panel(img, box, glow=not dim, alpha=170 if dim else 235, edge=(90, 70, 130) if dim else EDGE)
    if dim:
        return
    text(img, x0 + 10, y0 + 7, "NEW GAME")
    red_rule(img, x0 + 10 + 26, y0 + 22, 26)
    cx = (x0 + x1) // 2
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([cx - 26, y0 + 36, cx + 26, y0 + 88], fill=(150, 70, 255, 120))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(8)))
    pokeball(img, cx, y0 + 62, 20)
    text(img, cx, y0 + 90, "Begin a new adventure", WHITE, center=True)
    text(img, cx, y0 + 106, "in the Distortion World.", LAV, center=True)


def top(bg, active, trainer="player_male"):
    img = bg.copy()
    tabs(img, active)
    if active == 0:
        continue_card(img, CARD, trainer=trainer)
        new_game_card(img, PEEK_R, dim=True)
        chevron(img, 14, 101, True, bright=False)
        chevron(img, 242, 101, False, bright=True)
    else:
        continue_card(img, PEEK_L, dim=True)
        new_game_card(img, CARD)
        chevron(img, 14, 101, True, bright=True)
        chevron(img, 242, 101, False, bright=False)
    page_dots(img, active)
    return img


def hint_circle(img, x, y):
    lay = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([x * SS, y * SS, (x + 13) * SS, (y + 13) * SS], fill=(60, 30, 100, 255), outline=EDGE + (255,), width=SS)
    return lay, d


def button_hint(img, x, y, glyph, label):
    lay, _ = hint_circle(img, x, y)
    img.alpha_composite(lay.resize((W, H), Image.LANCZOS))
    text(img, x + 7, y - 1, glyph, WHITE, center=True)
    return text(img, x + 17, y - 1, label, LAV)


def dpad_hint(img, x, y):
    lay, d = hint_circle(img, x, y)
    c = (x + 6.5) * SS
    m = (y + 6.5) * SS
    d.rectangle([c - 4 * SS, m - 1.2 * SS, c + 4 * SS, m + 1.2 * SS], fill=WHITE + (255,))
    d.rectangle([c - 1.2 * SS, m - 4 * SS, c + 1.2 * SS, m + 4 * SS], fill=(150, 130, 190, 255))
    img.alpha_composite(lay.resize((W, H), Image.LANCZOS))
    return text(img, x + 17, y - 1, "Select", LAV)


def hint_bar(img):
    panel(img, (16, 150, 240, 176), alpha=200, glow=False, radius=6)
    x = dpad_hint(img, 30, 156) + 16
    x = button_hint(img, x, 156, "A", "Confirm") + 16
    button_hint(img, x, 156, "B", "Back")


def bottom(bg, active):
    img = bg.copy()
    if active == 0:
        panel(img, (16, 18, 240, 140), alpha=220, glow=True)
        text(img, 26, 25, "PARTY")
        red_rule(img, 26 + 16, 40, 16)
        for sy in SLOT_Y:
            for sx in SLOT_X:
                panel(img, (sx, sy, sx + SLOT_W, sy + SLOT_H), fill=SLOT_FILL, alpha=255, edge=SLOT_EDGE, glow=False, radius=4)
        text(img, 26, 122, "LOCATION", LAV)
    else:
        panel(img, (16, 40, 240, 124), alpha=220, glow=True)
        text(img, W // 2, 52, "Starting a new game", WHITE, center=True)
        text(img, W // 2, 68, "won't erase your save file", LAV, center=True)
        text(img, W // 2, 84, "until you choose to save", LAV, center=True)
        text(img, W // 2, 100, "over it.", LAV, center=True)
    hint_bar(img)
    return img


# --- indexing / export -----------------------------------------------------

BAYER4 = ts.BAYER4


def quantize(images, first, overrides=None):
    """Map every pixel of every image into palette indices first..255.

    overrides: list (per image) of {(x, y): index} forced indices.
    Returns (list of index arrays, palette of 256 5-bit colours).
    """
    ncolors = 256 - first
    g5 = []
    for img in images:
        px = img.load()
        g5.append([ts.to555(px[x, y][:3], x, y) for y in range(H) for x in range(W)])
    allc = [c for arr in g5 for c in arr]
    uniq = sorted(set(allc))
    if len(uniq) > ncolors:
        tmp = Image.new("RGB", (len(allc), 1))
        tmp.putdata([tuple(v * 8 for v in c) for c in allc])
        q = tmp.quantize(ncolors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        qpal = q.getpalette()[: ncolors * 3]
        general = [tuple(min(31, round(qpal[i * 3 + k] / 8)) for k in range(3)) for i in range(ncolors)]
        qd = list(q.getdata())
        n = W * H
        idx = [[first + v for v in qd[i * n:(i + 1) * n]] for i in range(len(images))]
    else:
        general = uniq + [(0, 0, 0)] * (ncolors - len(uniq))
        lut = {c: first + i for i, c in enumerate(uniq)}
        idx = [[lut[c] for c in arr] for arr in g5]
    if overrides:
        for arr, ov in zip(idx, overrides):
            for (x, y), v in ov.items():
                arr[y * W + x] = v
    pal = [ts.to555(images[0].getpixel((0, 0))[:3], 1, 1)] + [(0, 0, 0)] * (first - 1) + general
    assert len(pal) == 256
    return idx, pal, len(uniq)


def tiles_of(arr):
    out = []
    for ty in range(H // 8):
        for tx in range(W // 8):
            out.append(tuple(arr[(ty * 8 + r) * W + tx * 8 + c] for r in range(8) for c in range(8)))
    return out


def save_png(path, arr, pal, extra_tiles=()):
    rows = (len(extra_tiles) + 31) // 32
    img = Image.new("P", (W, H + rows * 8), 0)
    img.putdata(arr + [arr[-1]] * (W * rows * 8))
    ip = img.load()
    for k, t in enumerate(extra_tiles):
        tx, ty = k % 32, H // 8 + k // 32
        for i, v in enumerate(t):
            ip[tx * 8 + i % 8, ty * 8 + i // 8] = v
    flat = []
    for c in pal:
        flat += [v * 255 // 31 for v in c]
    img.putpalette(flat)
    img.save(path, transparency=0)
    return img


def write_nscr(path, entries):
    assert len(entries) == 1024
    data = struct.pack("<1024H", *entries)
    nrcs = b"NRCS" + struct.pack("<IHHHHI", 0x14 + len(data), 256, 256, 1, 0, len(data)) + data
    hdr = b"RCSN" + struct.pack("<HHIHH", 0xFEFF, 0x0100, 0x10 + len(nrcs), 0x10, 1)
    with open(path, "wb") as f:
        f.write(hdr + nrcs)


def identity_map():
    entries = []
    for row in range(32):
        src = min(row, 23)  # rows past the screen repeat the last row
        entries += [src * 32 + col for col in range(32)]
    return entries


def preview(arr, pal, path):
    im = Image.new("RGB", (W, H))
    im.putdata([tuple(v * 255 // 31 for v in pal[i]) for i in arr])
    im.resize((W * 3, H * 3), Image.NEAREST).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview-dir", help="write 3x RGB previews of the decoded results here")
    args = ap.parse_args()

    bg = background()

    # Top screen: Continue (male + female portrait) and New Game share a palette.
    fills, rims = badge_masks()
    badge_ov = {}
    for i in range(8):
        for p in fills[i]:
            badge_ov[p] = TOP_BADGE_FILL + i
        for p in rims[i]:
            badge_ov[p] = TOP_BADGE_RIM + i
    tops = [top(bg, 0, "player_male"), top(bg, 0, "player_female"), top(bg, 1)]
    (cont_m, cont_f, newg), top_pal, n = quantize(tops, TOP_GENERAL, [badge_ov, badge_ov, {}])
    # Default (unearned) badge colours; main_menu.c overwrites these per badge.
    for i in range(8):
        top_pal[TOP_BADGE_FILL + i] = ts.to555((40, 22, 66), 1, 1)
        top_pal[TOP_BADGE_RIM + i] = ts.to555((90, 70, 130), 1, 1)
    print(f"top: {n} colours before reduction")

    tm, tf = tiles_of(cont_m), tiles_of(cont_f)
    diff = [i for i in range(len(tm)) if tm[i] != tf[i]]
    extra = [tf[i] for i in diff]
    assert H // 8 * 32 + len(extra) <= 928, "Continue tiles overflow the BG2 char block"
    female_map = identity_map()
    for k, i in enumerate(diff):
        female_map[(i // 32) * 32 + i % 32] = 768 + k
    save_png(os.path.join(OUT_DIR, "menu_top_continue.png"), cont_m, top_pal, extra)
    write_nscr(os.path.join(OUT_DIR, "menu_top_continue.NSCR"), identity_map())
    write_nscr(os.path.join(OUT_DIR, "menu_top_continue_female.NSCR"), female_map)
    save_png(os.path.join(OUT_DIR, "menu_top_new_game.png"), newg, top_pal)
    write_nscr(os.path.join(OUT_DIR, "menu_top_new_game.NSCR"), identity_map())
    print(f"top: {len(extra)} extra tiles for the female portrait")

    bots = [bottom(bg, 0), bottom(bg, 1)]
    (bcont, bnew), bot_pal, n = quantize(bots, BOTTOM_GENERAL)
    print(f"bottom: {n} colours before reduction")
    save_png(os.path.join(OUT_DIR, "menu_bottom_continue.png"), bcont, bot_pal)
    write_nscr(os.path.join(OUT_DIR, "menu_bottom_continue.NSCR"), identity_map())
    save_png(os.path.join(OUT_DIR, "menu_bottom_new_game.png"), bnew, bot_pal)
    write_nscr(os.path.join(OUT_DIR, "menu_bottom_new_game.NSCR"), identity_map())

    if args.preview_dir:
        os.makedirs(args.preview_dir, exist_ok=True)
        for name, arr, pal in [("top_continue", cont_m, top_pal), ("top_continue_female", cont_f, top_pal),
                               ("top_new_game", newg, top_pal), ("bottom_continue", bcont, bot_pal),
                               ("bottom_new_game", bnew, bot_pal)]:
            preview(arr, pal, os.path.join(args.preview_dir, f"{name}.png"))


if __name__ == "__main__":
    main()

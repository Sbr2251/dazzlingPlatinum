#!/usr/bin/env python3
"""Build the Arc 1 sprite design sheets (needs PIL: run with ~/.venvs/desmume/bin/python).

    ~/.venvs/desmume/bin/python tools/arc1_sprites/design_sheet.py
        -> docs/story/art/arc1_sprites_sheet.png   every frame of the five sheets at 4x, next to the
                                                   stock sprite it was built from, plus the palettes
    ~/.venvs/desmume/bin/python tools/arc1_sprites/design_sheet.py --ingame DIR
        -> also docs/story/art/arc1_sprites_ingame.png from the screenshots that
           tools/arc1_sprites/ingame_capture.py wrote to DIR (scratch build, see README)
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from effects import HITMONLEE_PALETTE, RIFT_PALETTE, TOTEM_DIR  # noqa: E402
from gen_arc1_sprites import SHEET_DIR  # noqa: E402
from pixelkit import CELL, MMODEL_DIR, REPO_ROOT, read_png, stock_walker  # noqa: E402

from integrate_arc1_field_sprites import first_texture  # noqa: E402

OUT_DIR = REPO_ROOT / "docs/story/art"
BG = (58, 64, 74)
CELL_BG = (92, 148, 96)
INK = (236, 236, 244)
DIM = (170, 176, 190)

ROW_NAMES = ["up", "down", "left", "right"]
COL_NAMES = ["stand", "step A", "stand", "step B"]


def font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # old Pillow
        return ImageFont.load_default()


def tile(frame, palette, zoom: int) -> Image.Image:
    img = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    img.putdata([(0, 0, 0, 0) if v == 0 else tuple(palette[v]) + (255,) for v in frame])
    return img.resize((CELL * zoom, CELL * zoom), Image.NEAREST)


def sheet_frames(name: str):
    width, height, pixels, palette = read_png(SHEET_DIR / name)
    frames = []
    for n in range((width // CELL) * (height // CELL)):
        r, c = divmod(n, width // CELL)
        frames.append([pixels[(r * CELL + y) * width + c * CELL + x] for y in range(CELL) for x in range(CELL)])
    return frames, palette


def grid(frames, palette, columns: int, zoom: int, labels: bool) -> Image.Image:
    rows = (len(frames) + columns - 1) // columns
    pad = 4
    left = 52 if labels else 0
    top = 18 if labels else 0
    w = left + columns * (CELL * zoom + pad)
    h = top + rows * (CELL * zoom + pad)
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    f = font(13)
    for n, frame in enumerate(frames):
        r, c = divmod(n, columns)
        x, y = left + c * (CELL * zoom + pad), top + r * (CELL * zoom + pad)
        d.rectangle([x, y, x + CELL * zoom - 1, y + CELL * zoom - 1], fill=CELL_BG)
        t = tile(frame, palette, zoom)
        img.paste(t, (x, y), t)
        if labels and c == 0 and columns == 4:
            d.text((4, y + CELL * zoom // 2 - 6), ROW_NAMES[r], fill=DIM, font=f)
        if labels and r == 0:
            d.text((x + 4, 2), COL_NAMES[c] if columns == 4 else f"frame {'AB'[c]}", fill=DIM, font=f)
    return img


def swatches(palette, size: int = 18) -> Image.Image:
    img = Image.new("RGB", (16 * (size + 2), size + 14), BG)
    d = ImageDraw.Draw(img)
    f = font(10)
    for i, rgb in enumerate(palette):
        x = i * (size + 2)
        if i == 0:
            d.rectangle([x, 0, x + size - 1, size - 1], outline=DIM)
            d.line([x, size - 1, x + size - 1, 0], fill=DIM)
        else:
            d.rectangle([x, 0, x + size - 1, size - 1], fill=tuple(rgb))
        d.text((x + 3, size + 1), f"{i:X}", fill=DIM, font=f)
    return img


def stock_rock():
    width, height, pixels, palette = first_texture((MMODEL_DIR / "mmodel_00000083.bin").read_bytes())
    frame = [0] * (CELL * CELL)
    ox, oy = (CELL - width) // 2, 30 - height
    for i, v in enumerate(pixels):
        frame[(oy + i // width) * CELL + ox + i % width] = v
    return [frame, frame], palette


def stock_totem():
    frames, palette = [], None
    for name in ("hitmonlee_idle_a.png", "hitmonlee_idle_b.png"):
        _, _, pixels, pal = read_png(TOTEM_DIR / name)
        frames.append(pixels)
        palette = palette or pal
    return frames, palette


def design_sheet(path: Path) -> None:
    zoom = 4
    blocks = []
    title_f, head_f, small_f = font(22), font(16), font(13)

    walkers = [
        ("OBJ_EVENT_GFX_SAROS", "saros.png", 0x5E, "stock base: Prof. Rowan walker (0x5E)",
         "Saros, Team Eclipse leader: long blue-black coat, stand-up collar, violet waistcoat, "
         "eclipse brooch, silver-streaked swept-back hair"),
        ("OBJ_EVENT_GFX_ECLIPSE_GRUNT_M", "eclipse_grunt_m.png", 0x67, "stock base: Galactic Grunt M (0x67)",
         "Eclipse grunt (male): dark hooded uniform, eclipse ring on hood/chest/back, violet belt"),
        ("OBJ_EVENT_GFX_ECLIPSE_GRUNT_F", "eclipse_grunt_f.png", 0x68, "stock base: Galactic Grunt F (0x68)",
         "Eclipse grunt (female): same uniform, lilac-silver hair out of the hood, ponytail"),
    ]
    for constant, name, member, base_label, blurb in walkers:
        base, base_pal = stock_walker(member)
        final, pal = sheet_frames(name)
        blocks.append((constant, blurb, [(base_label, grid(base, base_pal, 4, zoom, True)),
                                         (f"final: res/field/objects/arc1/{name}", grid(final, pal, 4, zoom, True))],
                       swatches(pal)))
    rock, rock_pal = stock_rock()
    rift, rift_pal = sheet_frames("arc1_rift.png")
    blocks.append(("OBJ_EVENT_GFX_ARC1_RIFT",
                   "Small violet rift hanging in the air: void core, hot violet rim, glow, drifting shards; B breathes",
                   [("placeholder: Rock Smash rock (0x53)", grid(rock, rock_pal, 2, zoom, True)),
                    ("final: res/field/objects/arc1/arc1_rift.png", grid(rift, rift_pal, 2, zoom, True))],
                   swatches(RIFT_PALETTE)))
    totem, totem_pal = stock_totem()
    violet, violet_pal = sheet_frames("totem_hitmonlee_violet.png")
    blocks.append(("OBJ_EVENT_GFX_TOTEM_HITMONLEE_VIOLET",
                   "Giant Hitmonlee seen through the rift: dark violet silhouette, glowing eyes, shimmering aura",
                   [("stock base: totems/hitmonlee_idle_{a,b}.png", grid(totem, totem_pal, 2, zoom, True)),
                    ("final: res/field/objects/arc1/totem_hitmonlee_violet.png", grid(violet, violet_pal, 2, zoom, True))],
                   swatches(HITMONLEE_PALETTE)))

    margin, gap = 24, 28
    width = max(sum(g.width for _, g in parts) + gap * (len(parts) - 1) for _, _, parts, _ in blocks) + 2 * margin
    height = 70
    for _, _, parts, sw in blocks:
        height += 50 + max(g.height for _, g in parts) + 22 + sw.height + 30
    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.text((margin, 16), "Dazzling Platinum, Arc 1 field sprites (Art stream): final art vs stock bases, 4x",
           fill=INK, font=title_f)
    d.text((margin, 44), "Sheets are generated by tools/arc1_sprites/gen_arc1_sprites.py; 16 colours, index 0 transparent, "
           "colours shown as the DS renders them (BGR555).", fill=DIM, font=small_f)
    y = 70
    for constant, blurb, parts, sw in blocks:
        d.text((margin, y), constant, fill=INK, font=head_f)
        d.text((margin, y + 22), blurb, fill=DIM, font=small_f)
        y += 50
        x = margin
        for label, g in parts:
            d.text((x, y), label, fill=INK, font=small_f)
            img.paste(g, (x, y + 18))
            x += g.width + gap
        y += 18 + max(g.height for _, g in parts) + 4
        d.text((margin, y), "palette", fill=DIM, font=small_f)
        img.paste(sw, (margin + 60, y))
        y += sw.height + 30
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)
    print(f"wrote {path} ({img.width}x{img.height})")


# ---------------------------------------------------------------------------
# In-game sheet
# ---------------------------------------------------------------------------

WANDERERS = {  # scratch placement in tools/arc1_sprites/scratch_events.py (tile x, z on Twinleaf)
    "Saros": (110, 883),
    "Eclipse grunt M": (110, 886),
    "Eclipse grunt F": (122, 885),
}


def _screen_box(tx, tz):
    # Twinleaf with the player at (116, 886): sprite cell top-left ~ (16*(x-116)+110, 16*(z-886)+66)
    ox, oy = 16 * (tx - 116) + 110, 16 * (tz - 886) + 66
    return (ox - 16, oy - 14, ox + 48, oy + 42)


def walk_strip(files, box, zoom, limit=10):
    crops, prev = [], None
    for f in files:
        c = Image.open(f).convert("RGB").crop(box)
        if prev is None or ImageChops.difference(c, prev).getbbox():
            crops.append(c)
        prev = c
        if len(crops) >= limit:
            break
    w, h = box[2] - box[0], box[3] - box[1]
    strip = Image.new("RGB", (len(crops) * (w * zoom + 4), h * zoom), BG)
    for i, c in enumerate(crops):
        strip.paste(c.resize((w * zoom, h * zoom), Image.NEAREST), (i * (w * zoom + 4), 0))
    return strip


def ingame_sheet(src: Path, path: Path) -> None:
    title_f, head_f, small_f = font(22), font(16), font(13)
    shots = [
        ("Twinleaf, noon: rows are Saros / grunt M / grunt F facing down, up, left, right; "
         "rift + violet Hitmonlee (top right) next to stock Grunt M and the stock totem", "001_twinleaf_town_h12.png"),
        ("Twinleaf, 21:00 (night tint)", "001_twinleaf_town_h21.png"),
        ("Oreburgh Mine B2F: rift at (9,15) over the violet Hitmonlee at (9,14), Garius at (9,16), as in scene 14",
         "001_oreburgh_mine_b2f_h12.png"),
        ("Jubilife TV plaza, noon: Saros by the TV, Eclipse grunts, with Garius, Cyrus and Looker for contrast",
         "001_jubilife_city_h12.png"),
        ("Jubilife TV plaza, 21:00", "001_jubilife_city_h21.png"),
    ]
    zoom = 2
    tiles = []
    for label, name in shots:
        p = src / name
        if p.exists():
            img = Image.open(p).convert("RGB").crop((0, 0, 256, 192)).resize((512, 384), Image.NEAREST)
            tiles.append((label, img))
    files = sorted(glob.glob(str(src / "twinleaf_town_h12_seq_*.png")))
    strips = [(f"{who}: wandering (captured every 4 frames, unchanged frames dropped), 3x",
               walk_strip(files, _screen_box(*tile_xy), 3)) for who, tile_xy in WANDERERS.items()] if files else []

    margin = 24
    cols = 2
    tw, th = 512, 384
    rows = (len(tiles) + cols - 1) // cols
    width = max([margin * 2 + cols * tw + (cols - 1) * margin] + [margin * 2 + s.width for _, s in strips])
    height = 70 + rows * (th + 48) + sum(s.height + 40 for _, s in strips) + 20
    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.text((margin, 16), "Arc 1 field sprites in game (scratch build, not committed), 2x", fill=INK, font=title_f)
    d.text((margin, 44), "py-desmume headless, clock pinned with sDebugClockHour. Palette check: every inner pixel of every "
           "unoccluded walker matched its sheet palette (see README).", fill=DIM, font=small_f)
    y = 70
    for i, (label, t) in enumerate(tiles):
        r, c = divmod(i, cols)
        x = margin + c * (tw + margin)
        yy = y + r * (th + 48)
        d.text((x, yy), label[:90], fill=INK, font=small_f)
        if len(label) > 90:
            d.text((x, yy + 15), label[90:], fill=INK, font=small_f)
        img.paste(t, (x, yy + 32))
    y += rows * (th + 48)
    for label, s in strips:
        d.text((margin, y), label, fill=INK, font=head_f)
        img.paste(s, (margin, y + 24))
        y += s.height + 40
    img.save(path, optimize=True)
    print(f"wrote {path} ({img.width}x{img.height})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ingame", type=Path, help="directory of in-game screenshots (ingame_capture.py output)")
    args = parser.parse_args()
    design_sheet(OUT_DIR / "arc1_sprites_sheet.png")
    if args.ingame:
        ingame_sheet(args.ingame, OUT_DIR / "arc1_sprites_ingame.png")


if __name__ == "__main__":
    main()

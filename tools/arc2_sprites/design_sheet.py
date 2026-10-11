#!/usr/bin/env python3
"""Build the Arc 2 sprite sheets (needs PIL: run with ~/.venvs/desmume/bin/python).

    ~/.venvs/desmume/bin/python tools/arc2_sprites/design_sheet.py
        -> docs/story/art/arc2/arc2_sprites_sheet.png    every frame of the seven sheets at 4x next to the
                                                         stock sprite each was built from, with palettes
    ~/.venvs/desmume/bin/python tools/arc2_sprites/design_sheet.py --ingame SHOTS --battle BATTLE
        -> also docs/story/art/arc2/arc2_sprites_ingame.png: the in-game captures at 4x next to stock NPCs
           (ingame_capture.py scenes A/B/C, battle_capture.py), the overview uploaded in the report
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import CELL, REPO_ROOT, SHEET_DIR, read_png, stock_walker  # noqa: E402
from objects import CRATE_PALETTE, FRAME_PALETTE, RIFT_PALETTE  # noqa: E402

OUT_DIR = REPO_ROOT / "docs/story/art/arc2"
BG = (58, 64, 74)
CELL_BG = (92, 148, 96)
INK = (236, 236, 244)
DIM = (170, 176, 190)
ROW_NAMES = ["up", "down", "left", "right"]


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def tile(frame, palette, zoom):
    img = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    img.putdata([(0, 0, 0, 0) if v == 0 else tuple(palette[v]) + (255,) for v in frame])
    return img.resize((CELL * zoom, CELL * zoom), Image.NEAREST)


def sheet_frames(name):
    width, height, pixels, palette = read_png(SHEET_DIR / name)
    cols = width // CELL
    frames = []
    for n in range(cols * (height // CELL)):
        r, c = divmod(n, cols)
        frames.append([pixels[(r * CELL + y) * width + c * CELL + x] for y in range(CELL) for x in range(CELL)])
    return frames, palette


def grid(frames, palette, columns, zoom, labels=True):
    rows = (len(frames) + columns - 1) // columns
    pad = 4
    left = 44 if labels and columns == 4 else 0
    img = Image.new("RGB", (left + columns * (CELL * zoom + pad), rows * (CELL * zoom + pad)), BG)
    d = ImageDraw.Draw(img)
    for n, frame in enumerate(frames):
        r, c = divmod(n, columns)
        x, y = left + c * (CELL * zoom + pad), r * (CELL * zoom + pad)
        d.rectangle([x, y, x + CELL * zoom - 1, y + CELL * zoom - 1], fill=CELL_BG)
        t = tile(frame, palette, zoom)
        img.paste(t, (x, y), t)
        if left and c == 0:
            d.text((4, y + CELL * zoom // 2 - 6), ROW_NAMES[r], fill=DIM, font=font(13))
    return img


def swatches(palette, size=16):
    img = Image.new("RGB", (16 * (size + 2), size + 12), BG)
    d = ImageDraw.Draw(img)
    for i, rgb in enumerate(palette[:16]):
        x = i * (size + 2)
        if i == 0:
            d.rectangle([x, 0, x + size - 1, size - 1], outline=DIM)
            d.line([x, size - 1, x + size - 1, 0], fill=DIM)
        else:
            d.rectangle([x, 0, x + size - 1, size - 1], fill=tuple(rgb))
        d.text((x + 3, size), f"{i:X}", fill=DIM, font=font(9))
    return img


WALKERS = [
    ("OBJ_EVENT_GFX_INDRA", "indra.png", 0x75, "stock base: Cynthia (0x75)",
     "Indra: tired, hard; jaw-length dark auburn bob, heavy lids, violet-black coat to a high collar, Eclipse clasp + back ring"),
    ("OBJ_EVENT_GFX_KAHN", "kahn.png", 0x36, "stock base: Sailor (0x36)",
     "Kahn: quiet sailor turned leader; navy officer's cap with violet band + Eclipse badge, pea coat, teal jersey, violet neckerchief, beard"),
    ("OBJ_EVENT_GFX_LOOKER_JANITOR", "looker_janitor.png", 0x178, "stock base: Looker (0x178)",
     "Looker as a janitor: slate-blue coveralls and cap over his own face and hair, a mop planted beside him"),
    ("OBJ_EVENT_GFX_LOOKER_NEWSPAPER", "looker_newspaper.png", 0x178, "stock base: Looker (0x178)",
     "Looker in disguise: fedora, sunglasses, an open newspaper held upside down (headline bar at the bottom)"),
]
OBJECTS = [
    ("OBJ_EVENT_GFX_ECLIPSE_CRATE", "eclipse_crate.png", CRATE_PALETTE,
     "Wooden crate, plank lid, steel brackets, the Eclipse mark stencilled in violet; B moves a glint"),
    ("OBJ_EVENT_GFX_SHARD_FRAME", "shard_frame.png", FRAME_PALETTE,
     "Cracked steel frame, violet scorch, empty chains and cuffs, Eclipse Shard crystals on top and base; B: shards hum"),
    ("OBJ_EVENT_GFX_RIFT_ARC2", "rift_arc2.png", RIFT_PALETTE,
     "Tall leaning violet tear, pale torn lips, black-violet void with specks, hairline cracks; B pulses"),
]


def design_sheet(path):
    zoom = 4
    blocks = []
    for constant, name, member, base_label, blurb in WALKERS:
        base, base_pal = stock_walker(member)
        final, pal = sheet_frames(name)
        blocks.append((constant, blurb, [(base_label, grid(base, base_pal, 4, zoom)),
                                         (f"final: res/field/objects/arc2/{name}", grid(final, pal, 4, zoom))],
                       swatches(pal)))
    for constant, name, pal, blurb in OBJECTS:
        final, pal2 = sheet_frames(name)
        blocks.append((constant, blurb, [(f"res/field/objects/arc2/{name} (frame A, frame B)",
                                          grid(final, pal2, 2, zoom))], swatches(pal2)))
    margin, gap = 24, 28
    width = max(sum(g.width for _, g in parts) + gap * (len(parts) - 1) for _, _, parts, _ in blocks) + 2 * margin
    height = 70 + sum(50 + max(g.height for _, g in parts) + 22 + sw.height + 26 for _, _, parts, sw in blocks)
    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.text((margin, 16), "Dazzling Platinum, Arc 2 field sprites (art-ph): sheets vs stock bases, 4x", fill=INK, font=font(22))
    d.text((margin, 44), "Generated by tools/arc2_sprites/gen_arc2_sprites.py from Platinum's own walkers (edited) and "
           "new pixels; 16 colours, index 0 transparent, BGR555.", fill=DIM, font=font(13))
    y = 70
    for constant, blurb, parts, sw in blocks:
        d.text((margin, y), constant, fill=INK, font=font(16))
        d.text((margin, y + 22), blurb, fill=DIM, font=font(13))
        y += 50
        x = margin
        for label, g in parts:
            d.text((x, y), label, fill=INK, font=font(13))
            img.paste(g, (x, y + 18))
            x += g.width + gap
        y += 18 + max(g.height for _, g in parts) + 4
        d.text((margin, y), "palette", fill=DIM, font=font(13))
        img.paste(sw, (margin + 60, y))
        y += sw.height + 26
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)
    print(f"wrote {path} ({img.width}x{img.height})")
    return img


def ingame_sheet(shots, battle, path, design):
    def load(p):
        return Image.open(p).convert("RGB")

    margin, gap = 24, 20
    sections = []
    a = load(shots / "A_h12.png").crop((0, 28, 200, 150))
    b = load(shots / "B_h12.png").crop((0, 28, 256, 150))
    sections.append(("Twinleaf, noon, 4x. Rows: Indra (top), Kahn (bottom) facing down/up/left/right; right: stock "
                     "Cynthia and Sailor; wandering copies above.", [a.resize((a.width * 4, a.height * 4), Image.NEAREST)]))
    sections.append(("Twinleaf, noon, 4x. Rows: Looker janitor, Looker newspaper; stock Looker and Galactic Grunt; "
                     "crate + shard frame (right), Arc 2 rift next to Arc 1's rift (top left).",
                     [b.resize((b.width * 4, b.height * 4), Image.NEAREST)]))
    nights = [load(shots / f"{t}_h21.png") for t in ("A", "B")]
    sections.append(("21:00 (night tint), 2x", [n.resize((512, 384), Image.NEAREST) for n in nights]))
    cb = load(shots / "B_h12.png").crop((168, 60, 230, 150))
    cc = load(shots / "C_h12.png").crop((168, 60, 230, 150))
    sections.append(("Crate and shard frame, 4x: as registered by R0 (left; the Totem renderer floats them 24 units, "
                     "shadow below) vs with /tmp/a2/art-ph/ground_objects.patch (right; grounded, for the lead)",
                     [cb.resize((cb.width * 4, cb.height * 4), Image.NEAREST),
                      cc.resize((cc.width * 4, cc.height * 4), Image.NEAREST)]))
    bt = [load(battle / f"battle_{t}_056.png").crop((0, 0, 256, 192)) for t in ("indra", "grunt_m", "grunt_f")]
    sections.append(("Battle intros, 2x: TRAINER_INDRA_DEPOT (Eclipse Leader), ECLIPSE_GRUNT_ARC2_01 (M), _02 (F); "
                     "placeholder palette swaps", [x.resize((512, 384), Image.NEAREST) for x in bt]))
    dz = design.resize((design.width * 2 // 3, design.height * 2 // 3), Image.LANCZOS)
    width = max(max(sum(i.width for i in ims) + gap * (len(ims) - 1) for _, ims in sections), dz.width) + 2 * margin
    height = 70 + sum(24 + max(i.height for i in ims) + 24 for _, ims in sections) + dz.height + 40
    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.text((margin, 16), "Dazzling Platinum, Arc 2 sprites in game (art-ph scratch build, not committed)",
           fill=INK, font=font(24))
    d.text((margin, 46), "py-desmume headless, Twinleaf Town, clock pinned with sDebugClockHour; scratch objects from "
           "tools/arc2_sprites/scratch_events.py A/B/T.", fill=DIM, font=font(14))
    y = 76
    for label, ims in sections:
        d.text((margin, y), label, fill=INK, font=font(15))
        y += 24
        x = margin
        for im in ims:
            img.paste(im, (x, y))
            x += im.width + gap
        y += max(i.height for i in ims) + 24
    d.text((margin, y), "Sheets (every frame) vs stock bases:", fill=INK, font=font(15))
    img.paste(dz, (margin, y + 24))
    img.save(path, optimize=True)
    print(f"wrote {path} ({img.width}x{img.height})")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ingame", type=Path)
    parser.add_argument("--battle", type=Path)
    args = parser.parse_args()
    design = design_sheet(OUT_DIR / "arc2_sprites_sheet.png")
    if args.ingame:
        ingame_sheet(args.ingame, args.battle or args.ingame, OUT_DIR / "arc2_sprites_ingame.png", design)


if __name__ == "__main__":
    main()

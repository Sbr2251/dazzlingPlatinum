#!/usr/bin/env python3
"""Build restrained, native-derived Mega Sinnoh starter sprite candidates."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw

from build_mega_sinnoh_sprites import (
    TRANSPARENT_RGB,
    extract_palette,
    indexed_image,
    shiny_color,
    write_jasc_palette,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research/mega-sinnoh-starters/native-derived"
NATIVE = OUT / "native"
PREVIEW = OUT / "preview"

DARK_STONE = (48, 56, 64, 255)
MID_STONE = (104, 112, 120, 255)
PALE_STONE = (216, 216, 208, 255)
AMBER = (184, 128, 56, 255)
DARK_AMBER = (112, 72, 24, 255)
DEEP_GREEN = (24, 80, 40, 255)
MID_GREEN = (48, 144, 64, 255)
INDIGO = (40, 40, 96, 255)
BLUE_VIOLET = (64, 72, 144, 255)
DEEP_RED = (128, 40, 48, 255)
GOLD = (224, 176, 48, 255)
STAFF_DARK = (72, 40, 16, 255)
STAFF_MID = (144, 88, 32, 255)
FLAME_RED = (232, 56, 56, 255)
FLAME_GOLD = (248, 200, 56, 255)
EMP_DARK = (16, 32, 65, 255)
EMP_NAVY = (16, 57, 115, 255)
EMP_BLUE = (82, 139, 230, 255)
EMP_CYAN = (156, 205, 255, 255)
EMP_GOLD = (238, 205, 98, 255)
EMP_LIGHT_GOLD = (255, 230, 131, 255)
EMP_OUTLINE = (16, 16, 16, 255)


def load_native(path: Path) -> Image.Image:
    source = Image.open(path).convert("RGBA")
    bg = source.getpixel((0, 0))[:3]
    pixels = []
    for r, g, b, _a in source.get_flattened_data():
        if (r, g, b) == bg:
            pixels.append((0, 0, 0, 0))
        else:
            pixels.append((r, g, b, 255))
    source.putdata(pixels)
    return source


def recolor_exact(image: Image.Image, mapping: dict[tuple[int, int, int], tuple[int, int, int]]) -> None:
    data = []
    for r, g, b, a in image.get_flattened_data():
        replacement = mapping.get((r, g, b))
        if replacement is not None and a:
            data.append((*replacement, a))
        else:
            data.append((r, g, b, a))
    image.putdata(data)


def draw_staff_behind(base: Image.Image, start: tuple[int, int], end: tuple[int, int], grip: tuple[int, int], flame_tip: tuple[int, int]) -> Image.Image:
    behind = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(behind)
    draw.line((start, end), fill=STAFF_DARK, width=4)
    draw.line((start, end), fill=STAFF_MID, width=2)
    tx, ty = flame_tip
    flame = [
        (tx, ty),
        (tx - 2, ty + 3),
        (tx - 1, ty + 6),
        (tx + 1, ty + 4),
        (tx + 3, ty + 7),
        (tx + 4, ty + 3),
        (tx + 2, ty + 1),
    ]
    draw.polygon(flame, fill=FLAME_RED)
    draw.polygon([(tx + 1, ty + 2), (tx, ty + 5), (tx + 2, ty + 4), (tx + 3, ty + 5), (tx + 3, ty + 2)], fill=FLAME_GOLD)
    result = Image.alpha_composite(behind, base)

    # Redraw the grip in front of the hand so the shaft cannot read as a floating prop.
    gx, gy = grip
    dx = 1 if end[0] >= start[0] else -1
    dy = 1 if end[1] >= start[1] else -1
    foreground = ImageDraw.Draw(result)
    foreground.line((gx - 3 * dx, gy - 3 * dy, gx + 3 * dx, gy + 3 * dy), fill=STAFF_DARK, width=4)
    foreground.line((gx - 3 * dx, gy - 3 * dy, gx + 3 * dx, gy + 3 * dy), fill=STAFF_MID, width=2)
    foreground.rectangle((gx - 2, gy - 1, gx + 2, gy + 1), fill=GOLD)
    return result


def torterra_front() -> Image.Image:
    sheet = load_native(ROOT / "res/pokemon/torterra/male_front.png")
    recolor_exact(sheet, {
        (65, 172, 65): MID_GREEN[:3],
        (24, 98, 24): DEEP_GREEN[:3],
        (49, 139, 57): (40, 120, 56),
    })
    draw = ImageDraw.Draw(sheet)

    # Frame 0: embedded forehead stone, armored shell plates, and restrained cracks in canonical spires.
    draw.polygon([(22, 31), (25, 27), (29, 32), (27, 35), (23, 34)], fill=DARK_STONE)
    draw.polygon([(24, 31), (25, 29), (27, 32), (26, 33)], fill=MID_STONE)
    draw.polygon([(39, 40), (44, 37), (49, 41), (47, 46), (41, 45)], fill=DARK_STONE)
    draw.polygon([(42, 40), (44, 39), (47, 41), (45, 43), (42, 43)], fill=AMBER)
    draw.line([(17, 26), (18, 31)], fill=DARK_AMBER, width=1)
    draw.line([(23, 19), (23, 25), (25, 28)], fill=DARK_AMBER, width=1)
    draw.line([(29, 25), (31, 30)], fill=DARK_AMBER, width=1)
    draw.line([(31, 49), (37, 50), (43, 49)], fill=DARK_STONE, width=2)

    # Frame 1 mirrors the same design rather than inventing a second model.
    draw.polygon([(99, 42), (102, 37), (106, 42), (104, 45), (100, 45)], fill=DARK_STONE)
    draw.polygon([(101, 41), (102, 39), (104, 42), (103, 43)], fill=MID_STONE)
    draw.polygon([(126, 40), (131, 37), (136, 41), (134, 46), (128, 45)], fill=DARK_STONE)
    draw.polygon([(129, 40), (131, 39), (134, 41), (132, 43), (129, 43)], fill=AMBER)
    draw.line([(95, 31), (96, 36)], fill=DARK_AMBER, width=1)
    draw.line([(103, 24), (103, 30), (105, 33)], fill=DARK_AMBER, width=1)
    draw.line([(112, 25), (113, 31)], fill=DARK_AMBER, width=1)
    draw.line([(111, 51), (118, 52), (125, 50)], fill=DARK_STONE, width=2)
    return sheet


def torterra_back() -> Image.Image:
    sheet = load_native(ROOT / "res/pokemon/torterra/male_back.png")
    recolor_exact(sheet, {
        (65, 172, 65): MID_GREEN[:3],
        (24, 98, 24): DEEP_GREEN[:3],
        (49, 139, 57): (40, 120, 56),
    })
    draw = ImageDraw.Draw(sheet)

    # Frame 0: repeat the armored shell language and accent the existing three mountain spires.
    draw.line([(43, 55), (47, 50), (49, 57)], fill=DARK_AMBER, width=1)
    draw.line([(55, 55), (58, 50), (60, 57)], fill=DARK_AMBER, width=1)
    draw.line([(68, 55), (71, 50), (73, 57)], fill=DARK_AMBER, width=1)
    draw.polygon([(31, 58), (36, 54), (42, 58), (40, 63), (34, 63)], fill=DARK_STONE)
    draw.polygon([(34, 58), (36, 56), (39, 59), (37, 61)], fill=AMBER)
    draw.line([(20, 64), (29, 61), (37, 62)], fill=DARK_STONE, width=2)

    # Frame 1.
    draw.line([(125, 55), (128, 49), (130, 57)], fill=DARK_AMBER, width=1)
    draw.line([(137, 55), (140, 50), (142, 57)], fill=DARK_AMBER, width=1)
    draw.line([(150, 56), (153, 51), (155, 58)], fill=DARK_AMBER, width=1)
    draw.polygon([(111, 58), (116, 54), (122, 58), (120, 63), (114, 63)], fill=DARK_STONE)
    draw.polygon([(114, 58), (116, 56), (119, 59), (117, 61)], fill=AMBER)
    draw.line([(99, 64), (108, 61), (117, 62)], fill=DARK_STONE, width=2)
    return sheet


def infernape_front() -> Image.Image:
    base = load_native(ROOT / "res/pokemon/infernape/male_front.png")
    recolor_exact(base, {
        (24, 65, 123): INDIGO[:3],
        (74, 115, 197): BLUE_VIOLET[:3],
        (131, 41, 49): DEEP_RED[:3],
    })
    frame0 = base.crop((0, 0, 80, 80))
    frame1 = base.crop((80, 0, 160, 80))

    frame0 = draw_staff_behind(frame0, (6, 2), (22, 20), (15, 8), (5, 1))
    frame1 = draw_staff_behind(frame1, (75, 4), (53, 31), (57, 24), (74, 2))

    # A narrow, connected sash and matching gold clasp; retain the canonical torso and limbs.
    draw0 = ImageDraw.Draw(frame0)
    draw0.polygon([(28, 39), (37, 41), (38, 44), (30, 44), (26, 42)], fill=INDIGO)
    draw0.rectangle((32, 40, 35, 43), fill=GOLD)
    draw0.line([(34, 43), (38, 48)], fill=DEEP_RED, width=2)

    draw1 = ImageDraw.Draw(frame1)
    draw1.polygon([(29, 35), (39, 36), (40, 40), (31, 40), (27, 38)], fill=INDIGO)
    draw1.rectangle((33, 36, 36, 39), fill=GOLD)
    draw1.line([(36, 39), (41, 44)], fill=DEEP_RED, width=2)

    sheet = Image.new("RGBA", (160, 80), (0, 0, 0, 0))
    sheet.alpha_composite(frame0, (0, 0))
    sheet.alpha_composite(frame1, (80, 0))
    return sheet


def infernape_back() -> Image.Image:
    base = load_native(ROOT / "res/pokemon/infernape/male_back.png")
    recolor_exact(base, {
        (24, 65, 123): INDIGO[:3],
        (74, 115, 197): BLUE_VIOLET[:3],
        (131, 41, 49): DEEP_RED[:3],
    })
    frame0 = base.crop((0, 0, 80, 80))
    frame1 = base.crop((80, 0, 160, 80))

    # Staff runs behind the body and remains visible at the hand-side edge.
    frame0 = draw_staff_behind(frame0, (77, 4), (59, 79), (63, 66), (77, 2))
    frame1 = draw_staff_behind(frame1, (78, 5), (65, 79), (68, 65), (78, 3))

    draw0 = ImageDraw.Draw(frame0)
    draw0.polygon([(31, 49), (44, 49), (47, 53), (35, 55), (29, 52)], fill=INDIGO)
    draw0.rectangle((38, 49, 41, 52), fill=GOLD)
    draw0.line([(42, 53), (47, 58)], fill=DEEP_RED, width=2)

    draw1 = ImageDraw.Draw(frame1)
    draw1.polygon([(32, 48), (45, 47), (48, 51), (37, 54), (31, 51)], fill=INDIGO)
    draw1.rectangle((39, 48, 42, 51), fill=GOLD)
    draw1.line([(44, 52), (49, 57)], fill=DEEP_RED, width=2)

    sheet = Image.new("RGBA", (160, 80), (0, 0, 0, 0))
    sheet.alpha_composite(frame0, (0, 0))
    sheet.alpha_composite(frame1, (80, 0))
    return sheet


def empoleon_front() -> Image.Image:
    base = load_native(ROOT / "res/pokemon/empoleon/male_front.png")
    frame0 = base.crop((0, 0, 80, 80))
    frame1 = base.crop((80, 0, 160, 80))

    # Frame 0: reinforce the existing trident crown and add connected imperial trim.
    draw0 = ImageDraw.Draw(frame0)
    draw0.polygon([(37, 11), (40, 6), (43, 11), (42, 16), (38, 16)], fill=EMP_LIGHT_GOLD)
    draw0.line([(37, 16), (40, 18), (43, 16)], fill=EMP_GOLD, width=1)
    draw0.line([(30, 24), (26, 28), (22, 31)], fill=EMP_GOLD, width=2)
    draw0.line([(50, 24), (54, 28), (58, 31)], fill=EMP_GOLD, width=2)
    draw0.polygon([(36, 30), (40, 27), (44, 30), (42, 35), (38, 35)], fill=EMP_NAVY)
    draw0.line([(37, 30), (40, 28), (43, 30)], fill=EMP_GOLD, width=1)
    draw0.rectangle((39, 31, 41, 33), fill=EMP_CYAN)

    # Frame 1 repeats exactly the same connected motifs on the canonical second pose.
    draw1 = ImageDraw.Draw(frame1)
    draw1.polygon([(40, 10), (43, 4), (46, 10), (45, 15), (41, 15)], fill=EMP_LIGHT_GOLD)
    draw1.line([(40, 15), (43, 17), (46, 15)], fill=EMP_GOLD, width=1)
    draw1.line([(31, 25), (27, 29), (23, 32)], fill=EMP_GOLD, width=2)
    draw1.line([(52, 24), (56, 28), (60, 31)], fill=EMP_GOLD, width=2)
    draw1.polygon([(38, 30), (42, 27), (46, 30), (44, 35), (40, 35)], fill=EMP_NAVY)
    draw1.line([(39, 30), (42, 28), (45, 30)], fill=EMP_GOLD, width=1)
    draw1.rectangle((41, 31, 43, 33), fill=EMP_CYAN)

    sheet = Image.new("RGBA", (160, 80), (0, 0, 0, 0))
    sheet.alpha_composite(frame0, (0, 0))
    sheet.alpha_composite(frame1, (80, 0))
    return sheet


def empoleon_back() -> Image.Image:
    base = load_native(ROOT / "res/pokemon/empoleon/male_back.png")
    frame0 = base.crop((0, 0, 80, 80))
    frame1 = base.crop((80, 0, 160, 80))

    # Preserve the genuine close-cropped rear anatomy; mirror only crown and shoulder trim.
    draw0 = ImageDraw.Draw(frame0)
    draw0.line([(27, 24), (31, 28), (35, 31)], fill=EMP_GOLD, width=2)
    draw0.line([(42, 25), (46, 29), (50, 33)], fill=EMP_GOLD, width=2)
    draw0.polygon([(33, 37), (38, 34), (43, 37), (41, 42), (35, 42)], fill=EMP_NAVY)
    draw0.line([(34, 37), (38, 35), (42, 37)], fill=EMP_GOLD, width=1)
    draw0.rectangle((37, 37, 39, 39), fill=EMP_CYAN)

    draw1 = ImageDraw.Draw(frame1)
    draw1.line([(25, 29), (30, 32), (34, 35)], fill=EMP_GOLD, width=2)
    draw1.line([(47, 26), (52, 30), (56, 34)], fill=EMP_GOLD, width=2)
    draw1.polygon([(35, 38), (40, 35), (45, 38), (43, 43), (37, 43)], fill=EMP_NAVY)
    draw1.line([(36, 38), (40, 36), (44, 38)], fill=EMP_GOLD, width=1)
    draw1.rectangle((39, 38, 41, 40), fill=EMP_CYAN)

    sheet = Image.new("RGBA", (160, 80), (0, 0, 0, 0))
    sheet.alpha_composite(frame0, (0, 0))
    sheet.alpha_composite(frame1, (80, 0))
    return sheet


def write_key(path: Path) -> None:
    key = zlib.crc32(path.read_bytes()) or 1
    path.with_suffix(path.suffix + ".key").write_bytes(struct.pack("<I", key))


def checkerboard(size: tuple[int, int], cell: int = 8) -> Image.Image:
    image = Image.new("RGBA", size, (232, 232, 232, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(200, 200, 200, 255))
    return image


def make_preview(rows: Iterable[tuple[str, Image.Image, Image.Image]]) -> None:
    rows = list(rows)
    scale = 5
    margin = 12
    label_h = 22
    row_h = 80 * scale + label_h + margin
    canvas = Image.new("RGBA", (160 * scale + margin * 2, row_h * len(rows) + margin), (245, 245, 245, 255))
    draw = ImageDraw.Draw(canvas)
    for idx, (label, front, back) in enumerate(rows):
        y = margin + idx * row_h
        draw.text((margin, y), label, fill=(20, 20, 20, 255))
        y_img = y + label_h
        composite = Image.new("RGBA", (160, 80), (0, 0, 0, 0))
        # Show one front frame and one back frame side by side.
        composite.alpha_composite(front.crop((0, 0, 80, 80)), (0, 0))
        composite.alpha_composite(back.crop((0, 0, 80, 80)), (80, 0))
        bg = checkerboard((160, 80), 4)
        bg.alpha_composite(composite)
        canvas.alpha_composite(bg.resize((160 * scale, 80 * scale), Image.Resampling.NEAREST), (margin, y_img))
        draw.line((margin + 80 * scale, y_img, margin + 80 * scale, y_img + 80 * scale), fill=(220, 0, 160, 255), width=2)
        draw.text((margin + 4, y_img + 4), "FRONT", fill=(0, 0, 0, 255))
        draw.text((margin + 80 * scale + 4, y_img + 4), "BACK", fill=(0, 0, 0, 255))
    PREVIEW.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(PREVIEW / "native_derived_sinnoh_starters_preview.png")


def main() -> None:
    NATIVE.mkdir(parents=True, exist_ok=True)
    built = {
        "torterra": (torterra_front(), torterra_back()),
        "infernape": (infernape_front(), infernape_back()),
        "empoleon": (empoleon_front(), empoleon_back()),
    }
    preview_rows = []
    for species, (front, back) in built.items():
        colors = extract_palette([front, back])
        species_dir = NATIVE / species
        species_dir.mkdir(parents=True, exist_ok=True)
        for view, rgba in (("front", front), ("back", back)):
            path = species_dir / f"{view}.png"
            indexed_image(rgba, colors).save(path, optimize=True, bits=4)
            write_key(path)
        write_jasc_palette(species_dir / "normal.pal", colors)
        write_jasc_palette(species_dir / "shiny.pal", [shiny_color(species, color) for color in colors])
        preview_rows.append((f"Mega {species.title()} — native-derived candidate", front, back))
    make_preview(preview_rows)
    print(f"Wrote candidates under {NATIVE}")
    print(f"Wrote preview to {PREVIEW / 'native_derived_sinnoh_starters_preview.png'}")


if __name__ == "__main__":
    main()

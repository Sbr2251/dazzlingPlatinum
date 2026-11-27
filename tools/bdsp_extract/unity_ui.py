#!/usr/bin/env python3
"""Extract exact BDSP Battle UI sprites + packed RGBA atlas + manifest.json from unpacked RomFS.

Reads Unity AssetBundles under <romfs>/Data/StreamingAssets/AssetAssistant/UIs/:
  - shareduiassets/sharedui
  - shareduiassets/sharedui_lang.en
  - shareduiassets/battle_lang.en
  - textures/common
  - textures/common_lang.en

Outputs (into an UNTRACKED directory, e.g. ~/dz-team/bdsp3d-assets/ui/):
  - atlas.png         Single shelf-packed RGBA atlas (with 1px edge extrusion + padding)
  - manifest.json     Sprite atlas coordinates, pixel sizes, and [L, T, R, B] 9-slice borders
  - sprites/*.png     Individual decoded RGBA PNG sprites for inspection

Optional:
  --contact-sheet <path.png>  Saves a labeled visual verification contact sheet.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw
import UnityPy


@dataclass(frozen=True)
class SpriteSpec:
    key: str
    bundle: str
    unity_name: str
    # Safe 9-slice border [left, top, right, bottom] in pixels (None => derive from Unity m_Border or 0)
    border: tuple[int, int, int, int] | None = None


def build_sprite_specs() -> list[SpriteSpec]:
    specs: list[SpriteSpec] = [
        # Action buttons (plates with authentic BDSP right-hand line-art icons baked in)
        SpriteSpec("btn_fight", "shareduiassets/sharedui", "btl_bt_command_01_body_01", (16, 10, 104, 10)),
        SpriteSpec("btn_pokemon", "shareduiassets/sharedui", "btl_bt_command_01_body_02", (16, 10, 104, 10)),
        SpriteSpec("btn_bag", "shareduiassets/sharedui", "btl_bt_command_01_body_03_02", (16, 10, 104, 10)),
        SpriteSpec("btn_run", "shareduiassets/sharedui", "btl_bt_command_01_body_04", (16, 10, 104, 10)),
        SpriteSpec("btn_cancel", "shareduiassets/sharedui", "btl_bt_command_01_body_05", (16, 10, 104, 10)),
        # Plain colored button plates (Yes/No/Mega/Generic)
        SpriteSpec("btn_plain_red", "shareduiassets/sharedui", "btl_bt_command_02_body_01", (16, 10, 16, 10)),
        SpriteSpec("btn_plain_green", "shareduiassets/sharedui", "btl_bt_command_02_body_02", (16, 10, 16, 10)),
        SpriteSpec("btn_plain_gold", "shareduiassets/sharedui", "btl_bt_command_02_body_03", (16, 10, 16, 10)),
        SpriteSpec("btn_plain_blue", "shareduiassets/sharedui", "btl_bt_command_02_body_04", (16, 10, 16, 10)),
        SpriteSpec("btn_quick_ball", "shareduiassets/sharedui", "btl_bt_quickitem_01_body", (12, 10, 12, 10)),
        SpriteSpec("btn_shadow", "shareduiassets/sharedui", "btl_bt_command_01_shadow", (6, 6, 18, 12)),
        SpriteSpec("btn_quick_shadow", "shareduiassets/sharedui", "btl_bt_quickitem_01_shadow", (4, 4, 12, 6)),
        # Selection cursor frames (exact BDSP red+white corner brackets)
        SpriteSpec("cursor_frame", "shareduiassets/sharedui", "cmn_frm_cursor_01", (24, 24, 24, 24)),
        SpriteSpec("cursor_eff", "shareduiassets/sharedui", "cmn_frm_cursor_01_eff", (24, 24, 24, 24)),
        # Nameplates, party strip tray, HP & EXP gauges
        SpriteSpec("card_player", "shareduiassets/sharedui", "btl_pl_status_01_01here_01", (32, 10, 32, 10)),
        SpriteSpec("card_enemy", "shareduiassets/sharedui", "btl_pl_status_01_02away_01", (32, 10, 32, 10)),
        SpriteSpec("party_strip", "shareduiassets/sharedui", "btl_pl_status_ball_01", (26, 0, 26, 0)),
        SpriteSpec("hp_bar_frame", "shareduiassets/sharedui_lang.en", "cmn_pl_txt_hpbar_01", (44, 0, 14, 0)),
        SpriteSpec("hp_fill_green", "shareduiassets/sharedui", "cmn_guage_01_body_01", (4, 0, 4, 0)),
        SpriteSpec("hp_fill_yellow", "shareduiassets/sharedui", "cmn_guage_01_body_02", (4, 0, 4, 0)),
        SpriteSpec("hp_fill_red", "shareduiassets/sharedui", "cmn_guage_01_body_03", (4, 0, 4, 0)),
        SpriteSpec("exp_bg", "shareduiassets/sharedui", "btl_guage_exp_01_bg", (6, 0, 6, 0)),
        SpriteSpec("exp_fill", "shareduiassets/sharedui", "btl_guage_exp_01_body", (4, 0, 4, 0)),
        # Party Poké Balls, wild caught icon, gender badges
        SpriteSpec("ball_ok", "shareduiassets/sharedui", "btl_ico_ball_01_01", (0, 0, 0, 0)),
        SpriteSpec("ball_fainted", "shareduiassets/sharedui", "btl_ico_ball_01_02", (0, 0, 0, 0)),
        SpriteSpec("ball_status", "shareduiassets/sharedui", "btl_ico_ball_01_03", (0, 0, 0, 0)),
        SpriteSpec("ball_hd_ok", "shareduiassets/sharedui", "btl_ico_ball_encount_01", (0, 0, 0, 0)),
        SpriteSpec("ball_hd_status", "shareduiassets/sharedui", "btl_ico_ball_encount_02", (0, 0, 0, 0)),
        SpriteSpec("ball_hd_fainted", "shareduiassets/sharedui", "btl_ico_ball_encount_03", (0, 0, 0, 0)),
        SpriteSpec("ball_hd_empty", "shareduiassets/sharedui", "btl_ico_ball_encount_04", (0, 0, 0, 0)),
        SpriteSpec("caught_icon", "shareduiassets/sharedui", "btl_ico_capture_01", (0, 0, 0, 0)),
        SpriteSpec("gender_m", "textures/common", "cmn_icon_sex_01_m", (0, 0, 0, 0)),
        SpriteSpec("gender_f", "textures/common", "cmn_icon_sex_01_f", (0, 0, 0, 0)),
        # Key-guide icons & badges (A, B, X, Y + battle X/Y pills)
        SpriteSpec("key_a", "shareduiassets/sharedui", "cmn_ico_txt_keyguide_01_01", (0, 0, 0, 0)),
        SpriteSpec("key_b", "shareduiassets/sharedui", "cmn_ico_txt_keyguide_01_02", (0, 0, 0, 0)),
        SpriteSpec("key_x", "shareduiassets/sharedui", "cmn_ico_txt_keyguide_01_03", (0, 0, 0, 0)),
        SpriteSpec("key_y", "shareduiassets/sharedui", "cmn_ico_txt_keyguide_01_04", (0, 0, 0, 0)),
        SpriteSpec("key_pill_x", "shareduiassets/sharedui", "btl_pl_ico_keyguide_01_01", (42, 10, 10, 10)),
        SpriteSpec("key_pill_y", "shareduiassets/sharedui", "btl_pl_ico_keyguide_01_02", (42, 10, 10, 10)),
        # Move category icons (Physical / Special / Status)
        SpriteSpec("cat_phys", "textures/common", "cmn_ico_wazacategory_01_01", (0, 0, 0, 0)),
        SpriteSpec("cat_spec", "textures/common", "cmn_ico_wazacategory_01_02", (0, 0, 0, 0)),
        SpriteSpec("cat_status", "textures/common", "cmn_ico_wazacategory_01_03", (0, 0, 0, 0)),
        # Effectiveness banners (English)
        SpriteSpec("eff_super", "shareduiassets/battle_lang.en", "btl_txt_resist_01_01", (0, 0, 0, 0)),
        SpriteSpec("eff_normal", "shareduiassets/battle_lang.en", "btl_txt_resist_01_02", (0, 0, 0, 0)),
        SpriteSpec("eff_not_very", "shareduiassets/battle_lang.en", "btl_txt_resist_01_03", (0, 0, 0, 0)),
        SpriteSpec("eff_none", "shareduiassets/battle_lang.en", "btl_txt_resist_01_04", (0, 0, 0, 0)),
        # Status condition badges (English)
        SpriteSpec("status_par", "textures/common_lang.en", "cmn_ico_txt_sick_01_01", (0, 0, 0, 0)),
        SpriteSpec("status_slp", "textures/common_lang.en", "cmn_ico_txt_sick_01_02", (0, 0, 0, 0)),
        SpriteSpec("status_frz", "textures/common_lang.en", "cmn_ico_txt_sick_01_03", (0, 0, 0, 0)),
        SpriteSpec("status_brn", "textures/common_lang.en", "cmn_ico_txt_sick_01_04", (0, 0, 0, 0)),
        SpriteSpec("status_psn", "textures/common_lang.en", "cmn_ico_txt_sick_01_05", (0, 0, 0, 0)),
        SpriteSpec("status_tox", "textures/common_lang.en", "cmn_ico_txt_sick_01_06", (0, 0, 0, 0)),
        SpriteSpec("status_fnt", "textures/common_lang.en", "cmn_ico_txt_sick_01_07", (0, 0, 0, 0)),
        # Move detail & Battle status info card panels
        SpriteSpec("info_move_bg", "shareduiassets/sharedui", "btl_pl_wazainfo_01_body", (18, 18, 18, 18)),
        SpriteSpec("info_status_bg", "shareduiassets/sharedui", "btl_pl_subinfo_01_main", (22, 15, 22, 19)),
        SpriteSpec("info_sub_bg", "shareduiassets/sharedui", "btl_pl_subinfo_01_sub", (4, 2, 4, 2)),
        SpriteSpec("move_shadow", "shareduiassets/sharedui", "btl_bt_waza_01_shadow", (4, 4, 14, 10)),
    ]

    # All 18 BDSP types (00=Normal..08=Steel, 09=Fire..17=Fairy)
    for t in range(18):
        specs.append(SpriteSpec(
            f"move_card_{t:02d}", "shareduiassets/sharedui",
            f"btl_bt_waza_01_body_{t:02d}", (82, 8, 120, 8),
        ))
        specs.append(SpriteSpec(
            f"move_deco_{t:02d}", "shareduiassets/sharedui",
            f"btl_bt_waza_01_deco_01_{t:02d}", (0, 0, 0, 0),
        ))
        specs.append(SpriteSpec(
            f"type_badge_{t:02d}", "textures/common_lang.en",
            f"cmn_ico_type_01_{t:02d}", (0, 0, 0, 0),
        ))

    return specs


def paste_with_extrude(atlas: Image.Image, img: Image.Image, x: int, y: int) -> None:
    """Paste RGBA image at (x, y) and extrude 1px around all 4 edges to eliminate bilinear bleed."""
    w, h = img.size
    atlas.paste(img, (x, y))
    if w <= 0 or h <= 0:
        return
    # Top & bottom 1px strips
    top = img.crop((0, 0, w, 1))
    bot = img.crop((0, h - 1, w, h))
    atlas.paste(top, (x, y - 1))
    atlas.paste(bot, (x, y + h))
    # Left & right 1px strips
    left = img.crop((0, 0, 1, h))
    right = img.crop((w - 1, 0, w, h))
    atlas.paste(left, (x - 1, y))
    atlas.paste(right, (x + w, y))
    # 4 corner pixels
    atlas.putpixel((x - 1, y - 1), img.getpixel((0, 0)))
    atlas.putpixel((x + w, y - 1), img.getpixel((w - 1, 0)))
    atlas.putpixel((x - 1, y + h), img.getpixel((0, h - 1)))
    atlas.putpixel((x + w, y + h), img.getpixel((w - 1, h - 1)))


def pack_atlas(
    decoded: list[tuple[SpriteSpec, Image.Image, tuple[int, int, int, int]]],
    atlas_w: int = 2048,
) -> tuple[Image.Image, dict[str, dict[str, Any]]]:
    """Shelf-pack sprites tallest-first into a power-of-two height RGBA atlas."""
    pad = 2  # 1px extrude + 1px transparent guard on each side (total 4px spacing)
    ordered = sorted(decoded, key=lambda item: (-item[1].height, -item[1].width, item[0].key))

    placements: list[tuple[SpriteSpec, Image.Image, tuple[int, int, int, int], int, int]] = []
    pen_x = pad
    pen_y = pad
    row_h = 0

    for spec, img, unity_border in ordered:
        w, h = img.size
        if pen_x + w + pad > atlas_w:
            pen_x = pad
            pen_y += row_h + pad * 2
            row_h = 0
        placements.append((spec, img, unity_border, pen_x, pen_y))
        pen_x += w + pad * 2
        if h > row_h:
            row_h = h

    needed_h = pen_y + row_h + pad
    atlas_h = 1
    while atlas_h < needed_h:
        atlas_h <<= 1
    atlas_h = max(256, atlas_h)

    atlas = Image.new("RGBA", (atlas_w, atlas_h), (0, 0, 0, 0))
    manifest_sprites: dict[str, dict[str, Any]] = {}

    for spec, img, unity_border, x, y in placements:
        paste_with_extrude(atlas, img, x, y)
        border = spec.border
        if border is None:
            # Unity m_Border is (L, B, R, T) -> convert to (L, T, R, B)
            border = (unity_border[0], unity_border[3], unity_border[2], unity_border[1])
        manifest_sprites[spec.key] = {
            "source": spec.unity_name,
            "file": f"sprites/{spec.key}.png",
            "x": x,
            "y": y,
            "w": img.width,
            "h": img.height,
            "border": list(border),
            "unity_border": list(unity_border),
        }

    return atlas, manifest_sprites


def make_contact_sheet(
    decoded: list[tuple[SpriteSpec, Image.Image, tuple[int, int, int, int]]],
    out_path: str,
) -> None:
    cols = 6
    cell_w, cell_h = 260, 108
    rows = math.ceil(len(decoded) / cols)
    sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (34, 38, 48, 255))
    draw = ImageDraw.Draw(sheet)

    for idx, (spec, img, _) in enumerate(decoded):
        r, c = divmod(idx, cols)
        x0, y0 = c * cell_w, r * cell_h
        draw.rectangle(
            [x0 + 4, y0 + 18, x0 + cell_w - 4, y0 + cell_h - 4],
            fill=(56, 62, 74, 255),
            outline=(88, 96, 112, 255),
        )
        draw.text((x0 + 6, y0 + 3), f"{spec.key} ({img.width}x{img.height})", fill=(238, 242, 252, 255))
        max_w, max_h = cell_w - 16, cell_h - 28
        scale = min(max_w / max(1, img.width), max_h / max(1, img.height), 2.0)
        nw, nh = max(1, int(round(img.width * scale))), max(1, int(round(img.height * scale)))
        thumb = img.resize((nw, nh), Image.Resampling.LANCZOS)
        px = x0 + 4 + (cell_w - 8 - nw) // 2
        py = y0 + 18 + (cell_h - 22 - nh) // 2
        sheet.alpha_composite(thumb, (px, py))

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    sheet.save(out_path)


def extract_ui_assets(
    romfs_dir: str,
    out_dir: str,
    contact_sheet_path: str | None = None,
    write_individual: bool = True,
) -> dict[str, Any]:
    ui_root = os.path.join(romfs_dir, "Data", "StreamingAssets", "AssetAssistant", "UIs")
    if not os.path.isdir(ui_root):
        raise FileNotFoundError(f"BDSP UI AssetAssistant directory not found: {ui_root}")

    specs = build_sprite_specs()
    bundles_needed = sorted({s.bundle for s in specs})
    bundle_sprites: dict[str, dict[str, Any]] = {}

    for rel in bundles_needed:
        path = os.path.join(ui_root, rel)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Missing Unity bundle: {path}")
        env = UnityPy.load(path)
        smap: dict[str, Any] = {}
        for obj in env.objects:
            if obj.type.name == "Sprite":
                sp = obj.read()
                smap[sp.m_Name] = sp
        bundle_sprites[rel] = smap

    os.makedirs(out_dir, exist_ok=True)
    sprites_dir = os.path.join(out_dir, "sprites")
    if write_individual:
        os.makedirs(sprites_dir, exist_ok=True)

    decoded: list[tuple[SpriteSpec, Image.Image, tuple[int, int, int, int]]] = []
    missing: list[str] = []

    for spec in specs:
        sp = bundle_sprites[spec.bundle].get(spec.unity_name)
        if sp is None:
            missing.append(f"{spec.key} ({spec.bundle}:{spec.unity_name})")
            continue
        img = sp.image.convert("RGBA")
        b = sp.m_Border
        unity_border = (int(round(b.x)), int(round(b.y)), int(round(b.z)), int(round(b.w)))
        decoded.append((spec, img, unity_border))
        if write_individual:
            img.save(os.path.join(sprites_dir, f"{spec.key}.png"))

    if missing:
        print(f"WARNING: {len(missing)} requested sprites not found:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)

    atlas, manifest_sprites = pack_atlas(decoded, atlas_w=2048)
    atlas_path = os.path.join(out_dir, "atlas.png")
    atlas.save(atlas_path)

    manifest = {
        "version": 1,
        "atlas": "atlas.png",
        "width": atlas.width,
        "height": atlas.height,
        "sprite_count": len(manifest_sprites),
        "sprites": manifest_sprites,
    }
    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")

    if contact_sheet_path:
        make_contact_sheet(decoded, contact_sheet_path)

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract BDSP Battle UI sprites and packed atlas.")
    parser.add_argument(
        "--romfs",
        default=os.path.expanduser("~/dz-team/bdsp3d-scratch/romfs"),
        help="Path to unpacked BDSP RomFS root",
    )
    parser.add_argument(
        "--out",
        default=os.path.expanduser("~/dz-team/bdsp3d-assets/ui"),
        help="Untracked output directory for extracted UI assets",
    )
    parser.add_argument(
        "--contact-sheet",
        default=None,
        help="Optional output path for visual verification contact sheet PNG",
    )
    parser.add_argument(
        "--no-individual",
        action="store_true",
        help="Skip writing individual sprites/*.png files",
    )
    args = parser.parse_args()

    manifest = extract_ui_assets(
        romfs_dir=os.path.expanduser(args.romfs),
        out_dir=os.path.expanduser(args.out),
        contact_sheet_path=os.path.expanduser(args.contact_sheet) if args.contact_sheet else None,
        write_individual=not args.no_individual,
    )
    print(
        f"Extracted {manifest['sprite_count']} BDSP battle UI sprites -> "
        f"{args.out}/atlas.png ({manifest['width']}x{manifest['height']}) + manifest.json"
    )
    if args.contact_sheet:
        print(f"Saved contact sheet -> {args.contact_sheet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

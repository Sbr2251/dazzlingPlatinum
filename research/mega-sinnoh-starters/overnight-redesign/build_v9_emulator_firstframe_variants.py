#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path("/home/ubuntu/dazzlingPlatinum")
WORK = ROOT / "research/mega-sinnoh-starters/overnight-redesign"
SOURCE = ROOT / "src/applications/rowan_intro/rowan_intro_app.c"
ROM = ROOT / "build/pokeplatinum.us.nds"
OUT = WORK / "v9-emulator-evidence/firstframe-roms"

VARIANTS = {
    "mega_torterra_front": ("torterra", "front", 276, 282),
    "mega_torterra_back": ("torterra", "back", 277, 283),
    "mega_infernape_front": ("infernape", "front", 278, 284),
    "mega_infernape_back": ("infernape", "back", 279, 285),
    "mega_empoleon_front": ("empoleon", "front", 280, 286),
    "mega_empoleon_back": ("empoleon", "back", 281, 287),
}

TEMPLATE_NEEDLE = """    BuildPokemonSpriteTemplate(
        &spriteTemplate,
        SPECIES_BUNEARY,
        GENDER_MALE,
        FACE_FRONT,
        FALSE,
        NULL,
        NULL);
"""
RUN_NEEDLE = """static BOOL RowanIntro_Run(RowanIntro *manager)
{
    BOOL isFinished = FALSE;
"""
FREEZE_BLOCK = """static BOOL RowanIntro_Run(RowanIntro *manager)
{
    // Temporary deterministic emulator-evidence harness. This runs through
    // the original DS background/tile/palette path after graphics init.
    static BOOL sMegaEvidenceLoaded = FALSE;
    if (sMegaEvidenceLoaded == FALSE) {
        RowanIntro_LoadBunearySprite(manager);
        // The stock loader intentionally uploads a fully magenta palette for
        // Buneary's reveal animation. Restore the original NCLR colors that it
        // already copied into manager->bunearyPalette before applying the tint.
        Bg_LoadPalette(BG_LAYER_MAIN_2, manager->bunearyPalette, 2 * 16, (2 * 16) * 8);
        Bg_SetOffset(manager->bgConfig, BG_LAYER_MAIN_2, BG_OFFSET_UPDATE_SET_X, 0);
        Bg_SetOffset(manager->bgConfig, BG_LAYER_MAIN_2, BG_OFFSET_UPDATE_SET_Y, 0);
        Bg_SetPriority(BG_LAYER_MAIN_2, 0);
        Bg_ToggleLayer(BG_LAYER_MAIN_0, FALSE);
        Bg_ToggleLayer(BG_LAYER_MAIN_1, FALSE);
        Bg_ToggleLayer(BG_LAYER_MAIN_3, FALSE);
        Bg_ToggleLayer(BG_LAYER_MAIN_2, TRUE);
        sMegaEvidenceLoaded = TRUE;
    }
    // Rowan initializes both engines at black and the fade system can restore
    // that brightness after the one-time setup. Force the evidence layer and
    // neutral brightness every frame so VBlank commits the loaded BG2 tiles.
    Bg_ToggleLayer(BG_LAYER_MAIN_2, TRUE);
    GXLayers_EngineAToggleLayers(GX_PLANEMASK_BG2, TRUE);
    ResetScreenMasterBrightness(DS_SCREEN_MAIN);
    ResetScreenMasterBrightness(DS_SCREEN_SUB);
    return FALSE;

    BOOL isFinished = FALSE;
"""


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def build(log_path: Path) -> None:
    with log_path.open("w", encoding="utf-8") as log:
        subprocess.run(
            ["ninja", "-C", str(ROOT / "build"), "-j2"],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    original_source = SOURCE.read_text(encoding="utf-8")
    if original_source.count(TEMPLATE_NEEDLE) != 1 or original_source.count(RUN_NEEDLE) != 1:
        raise RuntimeError("Expected unique Rowan intro injection points were not found")

    assets = {
        (species, view): ROOT / f"res/pokemon/{species}/forms/mega/{view}.png"
        for species, view, _, _ in VARIANTS.values()
    }
    original_assets = {key: path.read_bytes() for key, path in assets.items()}
    for key, data in original_assets.items():
        with Image.open(assets[key]) as image:
            if image.size != (160, 80):
                raise RuntimeError(f"Expected 160x80 v9 sheet for {key}, got {image.size}")
        if not data:
            raise RuntimeError(f"Empty production asset: {assets[key]}")

    manifest: dict[str, dict[str, object]] = {}
    try:
        for name, (species, view, character, palette) in VARIANTS.items():
            # Restore all sheets before each variant so only one NCGR becomes 80x80.
            for key, data in original_assets.items():
                assets[key].write_bytes(data)

            target = assets[(species, view)]
            with Image.open(target) as sheet:
                frame = sheet.crop((0, 0, 80, 80))
                frame.save(target)
            if Image.open(target).size != (80, 80):
                raise RuntimeError(f"First-frame crop failed for {target}")

            template_override = TEMPLATE_NEEDLE + (
                "\n"
                "    // Temporary emulator-evidence resource override.\n"
                "    spriteTemplate.narcID = NARC_INDEX_POKETOOL__POKEGRA__PL_OTHERPOKE;\n"
                f"    spriteTemplate.character = {character};\n"
                f"    spriteTemplate.palette = {palette};\n"
            )
            patched = original_source.replace(TEMPLATE_NEEDLE, template_override)
            patched = patched.replace(RUN_NEEDLE, FREEZE_BLOCK)
            SOURCE.write_text(patched, encoding="utf-8")

            log_path = OUT / f"{name}.build.log"
            build(log_path)
            destination = OUT / f"{name}.nds"
            shutil.copy2(ROM, destination)
            manifest[name] = {
                "source_sheet": str(target.relative_to(ROOT)),
                "source_sheet_original_sha256": digest_bytes(original_assets[(species, view)]),
                "embedded_frame": "left 80x80 pixels (frame 0)",
                "character_resource": character,
                "palette_resource": palette,
                "rom": str(destination.relative_to(ROOT)),
                "bytes": destination.stat().st_size,
                "sha256": digest_file(destination),
            }
    finally:
        SOURCE.write_text(original_source, encoding="utf-8")
        for key, data in original_assets.items():
            assets[key].write_bytes(data)
        build(OUT / "clean-production-restore.build.log")

    restoration = {
        "source_restored": SOURCE.read_text(encoding="utf-8") == original_source,
        "all_sheets_restored": all(assets[key].read_bytes() == data for key, data in original_assets.items()),
        "clean_rom_sha256": digest_file(ROM),
    }
    manifest["restoration"] = restoration
    (OUT.parent / "firstframe-variant-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

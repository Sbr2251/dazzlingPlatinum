#!/usr/bin/env python3
"""Verify Everspring NSBMD structural and ARM word-alignment invariants."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_TEXTURE_MASK = 0xFFFFFFFF
EXPECTED_POLYGON_MASK = 0x3F1FF8FF
EXPECTED_POLYGON_ATTRIBUTES = 0x001F8081
EXPECTED_TEXTURE_PARAMETER = 0x00030000
EXPECTED_FLAGS = 0x1FCE
EXPECTED_MATERIAL_COUNT = 51


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text())
    errors: list[str] = []
    files_out: list[dict[str, object]] = []
    total_materials = 0

    files = report.get("files", [])
    if len(files) != 2:
        errors.append(f"expected 2 files, found {len(files)}")

    for file_index, file_report in enumerate(files):
        path = file_report.get("path", f"file[{file_index}]")
        if not file_report.get("valid", False):
            errors.append(f"{path}: strict file validation failed")
        if file_report.get("errors"):
            errors.append(f"{path}: strict errors present: {file_report['errors']}")

        models = file_report.get("models", [])
        if len(models) != 1:
            errors.append(f"{path}: expected 1 model, found {len(models)}")
            continue
        model = models[0]
        model_offset = int(model.get("offset", -1))
        if model_offset < 0 or model_offset % 4 != 0:
            errors.append(f"{path}: model base 0x{model_offset:X} is not word-aligned")

        materials = model.get("materials", [])
        total_materials += len(materials)

        material_mods: set[int] = set()
        for material in materials:
            name = material.get("name", f"material[{material.get('index', '?')}]")
            offset = int(material["offset"])
            material_mods.add(offset % 4)
            checks = {
                "valid": material.get("valid") is True,
                "errors_empty": not material.get("errors"),
                "record_aligned": offset % 4 == 0,
                "texture_word_aligned": (offset + 20) % 4 == 0,
                "texture_mask": int(material["texture_image_parameter_mask"]) == EXPECTED_TEXTURE_MASK,
                "polygon_mask": int(material["polygon_attribute_mask"]) == EXPECTED_POLYGON_MASK,
                "polygon_attributes": int(material["polygon_attributes"]) == EXPECTED_POLYGON_ATTRIBUTES,
                "texture_parameter": int(material["texture_image_parameter"]) == EXPECTED_TEXTURE_PARAMETER,
                "flags": int(material["flags"]) == EXPECTED_FLAGS,
            }
            failed = [key for key, value in checks.items() if not value]
            if failed:
                errors.append(f"{path}:{name}: failed {', '.join(failed)}")

        texture_linkage = model.get("texture_linkage", {})
        palette_linkage = model.get("palette_linkage", {})
        texture_name_offset = int(texture_linkage.get("name_offset", -1))
        palette_name_offset = int(palette_linkage.get("name_offset", -1))
        texture_name_absolute = (
            int(texture_linkage.get("offset", -1))
            + int(texture_linkage.get("entry_offset", -1))
            + texture_name_offset
        )
        palette_name_absolute = (
            int(palette_linkage.get("offset", -1))
            + int(palette_linkage.get("entry_offset", -1))
            + palette_name_offset
        )
        sbc = model.get("sbc", {})
        sbc_start = int(sbc.get("offset", -1))
        sbc_end = int(sbc.get("end_limit", -1))
        sbc_size = sbc_end - sbc_start if sbc_start >= 0 and sbc_end >= sbc_start else -1

        if not texture_linkage.get("valid", False) or texture_linkage.get("errors"):
            errors.append(f"{path}: texture linkage is invalid")
        if not palette_linkage.get("valid", False) or palette_linkage.get("errors"):
            errors.append(f"{path}: palette linkage is invalid")
        if texture_name_absolute < 0 or texture_name_absolute % 4 != 0:
            errors.append(
                f"{path}: texture linkage names at 0x{texture_name_absolute:X} are not word-aligned"
            )
        if palette_name_absolute < 0 or palette_name_absolute % 4 != 0:
            errors.append(
                f"{path}: palette linkage names at 0x{palette_name_absolute:X} are not word-aligned"
            )
        if sbc_size < 0 or sbc_size % 4 != 0:
            errors.append(f"{path}: SBC size {sbc_size} is not word-aligned")

        files_out.append(
            {
                "path": path,
                "strict_valid": file_report.get("valid", False),
                "model_offset": model_offset,
                "model_offset_mod4": model_offset % 4,
                "material_count": len(materials),
                "material_offset_mod4": sorted(material_mods),
                "texture_name_absolute": texture_name_absolute,
                "texture_name_absolute_mod4": texture_name_absolute % 4,
                "palette_name_absolute": palette_name_absolute,
                "palette_name_absolute_mod4": palette_name_absolute % 4,
                "sbc_size": sbc_size,
                "sbc_size_mod4": sbc_size % 4 if sbc_size >= 0 else None,
            }
        )

    if total_materials != EXPECTED_MATERIAL_COUNT:
        errors.append(
            f"expected {EXPECTED_MATERIAL_COUNT} materials, found {total_materials}"
        )

    result = {
        "valid": not errors,
        "source_report": str(args.report),
        "expected": {
            "file_count": 2,
            "material_count": EXPECTED_MATERIAL_COUNT,
            "texture_image_parameter_mask": f"0x{EXPECTED_TEXTURE_MASK:08X}",
            "polygon_attribute_mask": f"0x{EXPECTED_POLYGON_MASK:08X}",
            "polygon_attributes": f"0x{EXPECTED_POLYGON_ATTRIBUTES:08X}",
            "texture_image_parameter": f"0x{EXPECTED_TEXTURE_PARAMETER:08X}",
            "flags": f"0x{EXPECTED_FLAGS:04X}",
        },
        "files": files_out,
        "material_count": total_materials,
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

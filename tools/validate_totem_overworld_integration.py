#!/usr/bin/env python3
"""Validate production integration for the eight Totem overworld billboards."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from inspect_nitro_bmd_textures import parse_bmd


@dataclass(frozen=True)
class Totem:
    species: str
    constant: str
    graphics_id: int
    member: int

    @property
    def resource_hex(self) -> str:
        return f"0x{self.member:X}"

    @property
    def member_filename(self) -> str:
        return f"mmodel_{self.member:08d}.bin"


TOTEMS = (
    Totem("hitmonlee", "OBJ_EVENT_GFX_TOTEM_HITMONLEE", 276, 470),
    Totem("vespiquen", "OBJ_EVENT_GFX_TOTEM_VESPIQUEN", 277, 471),
    Totem("skarmory", "OBJ_EVENT_GFX_TOTEM_SKARMORY", 278, 472),
    Totem("lapras", "OBJ_EVENT_GFX_TOTEM_LAPRAS", 279, 473),
    Totem("spiritomb", "OBJ_EVENT_GFX_TOTEM_SPIRITOMB", 280, 474),
    Totem("aggron", "OBJ_EVENT_GFX_TOTEM_AGGRON", 281, 475),
    Totem("mamoswine", "OBJ_EVENT_GFX_TOTEM_MAMOSWINE", 282, 476),
    Totem("kingdra", "OBJ_EVENT_GFX_TOTEM_KINGDRA", 283, 477),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def array_section(source: str, declaration: str) -> str:
    start = source.index(declaration)
    end = source.index("};", start)
    return source[start:end]


def validate_png(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        pixels = list(image.getdata())
        mode = image.mode
        size = image.size
        transparency = image.info.get("transparency")
        corners = [
            image.getpixel((0, 0)),
            image.getpixel((image.width - 1, 0)),
            image.getpixel((0, image.height - 1)),
            image.getpixel((image.width - 1, image.height - 1)),
        ]
        border = (
            [image.getpixel((x, 0)) for x in range(image.width)]
            + [image.getpixel((x, image.height - 1)) for x in range(image.width)]
            + [image.getpixel((0, y)) for y in range(1, image.height - 1)]
            + [image.getpixel((image.width - 1, y)) for y in range(1, image.height - 1)]
        )
    return {
        "path": str(path),
        "mode": mode,
        "size": list(size),
        "transparency": transparency,
        "corners": corners,
        "unique_indices": sorted(set(pixels)),
        "transparent_pixels": pixels.count(0),
        "opaque_pixels": len(pixels) - pixels.count(0),
        "opaque_border_pixels": sum(index != 0 for index in border),
    }


def narc_member_count(path: Path) -> int:
    data = path.read_bytes()
    if data[:4] != b"NARC":
        raise ValueError(f"{path} is not a NARC archive")
    first_section = data[0x10:0x14]
    if first_section not in (b"BTAF", b"FATB"):
        raise ValueError(f"{path} has unexpected first section {first_section!r}")
    return struct.unpack_from("<H", data, 0x18)[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root",
    )
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []
    report: dict[str, Any] = {"totems": {}, "errors": errors}

    gfx_list = (root / "generated/object_events_gfx.txt").read_text().splitlines()
    overlay = (root / "src/overlay005/ov5_021FAF40.c").read_text()
    renderer = array_section(
        overlay,
        "const UnkStruct_ov5_021FB97C Unk_ov5_021FB97C[] = {",
    )
    resource_map = array_section(
        overlay,
        "const UnkStruct_ov5_021ED2D0 Unk_ov5_021FC9B4[] = {",
    )
    animation = array_section(
        overlay,
        "const UnkStruct_ov5_021EDD04 Unk_ov5_021FD77C[] = {",
    )
    draw = array_section(
        overlay,
        "const UnkStruct_ov5_021ECD10 Unk_ov5_021FC194[] = {",
    )

    source_member_dir = root / "res/prebuilt/data/mmodel/mmodel"
    built_member_dir = root / "build/res/prebuilt/data/mmodel/mmodel"
    capture_root = (
        root
        / "deliverables/totem-overworld-sprites/emulator-runtime-transparent-species-proofs"
    )

    for totem in TOTEMS:
        entry: dict[str, Any] = {}
        report["totems"][totem.species] = entry
        try:
            actual_id = gfx_list.index(totem.constant)
        except ValueError:
            actual_id = -1
        entry["graphics_id"] = actual_id
        if actual_id != totem.graphics_id:
            errors.append(
                f"{totem.species}: graphics ID {actual_id}, expected {totem.graphics_id}"
            )

        required_rows = {
            "renderer": (
                renderer,
                rf"\{{\s*{re.escape(totem.constant)},\s*&Unk_ov5_021FB0B4\s*\}}",
            ),
            "resource_map": (
                resource_map,
                rf"\{{\s*{re.escape(totem.constant)},\s*{totem.resource_hex}\s*\}}",
            ),
            "animation": (
                animation,
                rf"\{{\s*{re.escape(totem.constant)},\s*0x0,\s*0x8,\s*Unk_ov5_021FB1C4\s*\}}",
            ),
            "draw": (
                draw,
                rf"\{{\s*{re.escape(totem.constant)},\s*0x1,\s*0x1,\s*0x1,\s*0x1,\s*0x0\s*\}}",
            ),
        }
        row_checks = {
            name: bool(re.search(pattern, section))
            for name, (section, pattern) in required_rows.items()
        }
        entry["runtime_rows"] = row_checks
        for name, passed in row_checks.items():
            if not passed:
                errors.append(f"{totem.species}: missing or incorrect {name} row")
        if re.search(
            rf"\{{\s*{re.escape(totem.constant)},\s*&Unk_ov5_021FAFD8\s*\}}",
            renderer,
        ):
            errors.append(f"{totem.species}: stale generic renderer row remains")

        png_records = []
        for suffix in ("idle_a", "idle_b"):
            png_path = root / f"res/field/objects/totems/{totem.species}_{suffix}.png"
            if not png_path.exists():
                errors.append(f"{totem.species}: missing {png_path}")
                continue
            record = validate_png(png_path)
            png_records.append(record)
            if record["mode"] != "P" or record["size"] != [32, 32]:
                errors.append(f"{totem.species}: invalid PNG mode/size for {suffix}")
            if record["transparency"] != 0:
                errors.append(f"{totem.species}: {suffix} does not declare index 0 transparent")
            if any(index != 0 for index in record["corners"]):
                errors.append(f"{totem.species}: {suffix} corners are not index 0")
            if record["opaque_border_pixels"]:
                errors.append(f"{totem.species}: {suffix} touches the frame border")
            if not record["opaque_pixels"]:
                errors.append(f"{totem.species}: {suffix} is empty")
            if max(record["unique_indices"], default=0) > 15:
                errors.append(f"{totem.species}: {suffix} exceeds 4bpp palette indices")
        entry["png_frames"] = png_records

        source_member = source_member_dir / totem.member_filename
        built_member = built_member_dir / totem.member_filename
        if not source_member.exists():
            errors.append(f"{totem.species}: missing source BTX0 member")
        else:
            parsed = parse_bmd(source_member, None)
            textures = parsed["textures"]
            entry["source_btx0"] = {
                "path": str(source_member),
                "sha256": sha256(source_member),
                "textures": textures,
            }
            if len(textures) != 2:
                errors.append(f"{totem.species}: BTX0 has {len(textures)} textures, expected 2")
            for texture in textures:
                if (
                    texture["width"] != 32
                    or texture["height"] != 32
                    or texture["format"] != 3
                    or not texture["transparent_zero"]
                ):
                    errors.append(f"{totem.species}: invalid BTX0 texture metadata")
        if not built_member.exists():
            errors.append(f"{totem.species}: missing clean-build staged member")
        elif source_member.exists():
            entry["built_member_sha256"] = sha256(built_member)
            if source_member.read_bytes() != built_member.read_bytes():
                errors.append(f"{totem.species}: built member differs from source member")

        proof = capture_root / totem.species / "00_gallery_loaded.png"
        entry["native_proof"] = str(proof)
        if not proof.exists() or proof.stat().st_size == 0:
            errors.append(f"{totem.species}: missing native emulator proof")

    build_list = root / "res/prebuilt/data/mmodel/mmodel/meson.build"
    build_text = build_list.read_text()
    missing_build_members = [
        totem.member_filename
        for totem in TOTEMS
        if build_text.count(totem.member_filename) != 1
    ]
    report["build_list"] = {
        "path": str(build_list),
        "missing_or_duplicate": missing_build_members,
    }
    for filename in missing_build_members:
        errors.append(f"build list missing or duplicates {filename}")

    narc = root / "build/res/prebuilt/data/mmodel/mmodel.narc"
    if not narc.exists():
        errors.append("missing clean-build mmodel.narc")
    else:
        member_count = narc_member_count(narc)
        report["mmodel_narc"] = {
            "path": str(narc),
            "member_count": member_count,
            "sha256": sha256(narc),
        }
        if member_count < 478:
            errors.append(f"mmodel.narc has {member_count} members, expected at least 478")

    rom = root / "build/pokeplatinum.us.nds"
    if not rom.exists():
        errors.append("missing production ROM")
    else:
        report["production_rom"] = {
            "path": str(rom),
            "size": rom.stat().st_size,
            "sha256": sha256(rom),
        }
        if rom.stat().st_size != 134_217_728:
            errors.append(f"production ROM size is {rom.stat().st_size}, expected 134217728")

    git_check = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            "--",
            "src/map_object.c",
            "res/field/events/events_route_206.json",
        ],
        cwd=root,
        check=False,
    )
    report["temporary_instrumentation_restored"] = git_check.returncode == 0
    if git_check.returncode != 0:
        errors.append("temporary map-object or Route 206 instrumentation remains")

    report["status"] = "PASS" if not errors else "FAIL"
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Totem overworld integration validation: {report['status']}")
    print(f"Validated species: {len(TOTEMS)}")
    print(f"Errors: {len(errors)}")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()

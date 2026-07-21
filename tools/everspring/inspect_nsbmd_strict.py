#!/usr/bin/env python3
"""Strict Nitro G3D NSBMD structural auditor.

This intentionally follows the structures bundled with Pokémon Platinum's
NitroSystem source rather than permissive editor-specific readers. It validates:

* BMD0 container and MDL0 block tables
* NNSG3dResDict headers, entries, names, and Patricia lookups
* NNSG3dResMdl / NNSG3dResMdlInfo field layout and section ranges
* node, material, texture/palette-linkage, and shape dictionaries
* scene binary command (SBC) indices and termination
* exact 16-byte NNSG3dResShpData records
* packed Nintendo DS geometry display-list command streams

It emits JSON for reproducible diagnostics and can compare multiple files in one
report. No project code is imported, so it is suitable as an independent check.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


class ParseError(RuntimeError):
    pass


@dataclass
class Audit:
    path: str
    size: int
    summary: dict[str, Any] = field(default_factory=dict)
    dictionaries: list[dict[str, Any]] = field(default_factory=list)
    models: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "size": self.size,
            "valid": self.valid,
            "summary": self.summary,
            "dictionaries": self.dictionaries,
            "models": self.models,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class Reader:
    def __init__(self, data: bytes, audit: Audit):
        self.data = data
        self.audit = audit

    def require(self, offset: int, size: int, label: str) -> None:
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise ParseError(
                f"{label}: range 0x{offset:X}..0x{offset + size:X} exceeds "
                f"file size 0x{len(self.data):X}"
            )

    def unpack(self, fmt: str, offset: int, label: str = "field") -> tuple[Any, ...]:
        size = struct.calcsize(fmt)
        self.require(offset, size, label)
        return struct.unpack_from(fmt, self.data, offset)

    def u8(self, offset: int, label: str = "u8") -> int:
        return self.unpack("<B", offset, label)[0]

    def u16(self, offset: int, label: str = "u16") -> int:
        return self.unpack("<H", offset, label)[0]

    def s16(self, offset: int, label: str = "s16") -> int:
        return self.unpack("<h", offset, label)[0]

    def u32(self, offset: int, label: str = "u32") -> int:
        return self.unpack("<I", offset, label)[0]

    def s32(self, offset: int, label: str = "s32") -> int:
        return self.unpack("<i", offset, label)[0]

    def chunk(self, offset: int, size: int, label: str = "bytes") -> bytes:
        self.require(offset, size, label)
        return self.data[offset : offset + size]


def decode_name(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("ascii", "replace")


def fixed(value: int, frac: int = 12) -> float:
    return value / float(1 << frac)


def get_bit(name: bytes, bit: int) -> int:
    if bit < 0 or bit >= 128:
        return 0
    return (name[bit >> 3] >> (bit & 7)) & 1


def patricia_lookup(nodes: list[dict[str, int]], names_raw: list[bytes], key: bytes) -> int:
    if not nodes or nodes[0]["idx_left"] == 0:
        return -1
    p_idx = 0
    x_idx = nodes[0]["idx_left"]
    guard = 0
    while nodes[p_idx]["ref_bit"] > nodes[x_idx]["ref_bit"]:
        p_idx = x_idx
        node = nodes[x_idx]
        x_idx = node["idx_right"] if get_bit(key, node["ref_bit"]) else node["idx_left"]
        guard += 1
        if guard > len(nodes) + 1 or x_idx >= len(nodes):
            return -1
    entry = nodes[x_idx]["idx_entry"]
    if entry >= len(names_raw):
        return -1
    return entry if names_raw[entry] == key else -1


def parse_dict(
    r: Reader,
    base: int,
    label: str,
    expected_unit: int | None = None,
    enclosing_end: int | None = None,
) -> dict[str, Any]:
    r.require(base, 8, f"{label} header")
    revision, count, size_dict, dummy, ofs_entry = r.unpack(
        "<BBHHH", base, f"{label} header"
    )
    result: dict[str, Any] = {
        "label": label,
        "offset": base,
        "revision": revision,
        "count": count,
        "size": size_dict,
        "dummy": dummy,
        "entry_offset": ofs_entry,
        "nodes": [],
        "entry_unit_size": None,
        "name_offset": None,
        "entries": [],
        "names": [],
        "valid": True,
        "errors": [],
        "warnings": [],
    }

    def err(message: str) -> None:
        result["valid"] = False
        result["errors"].append(message)
        r.audit.error(f"{label}: {message}")

    def warn(message: str) -> None:
        result["warnings"].append(message)
        r.audit.warn(f"{label}: {message}")

    if revision != 0:
        err(f"revision is {revision}, expected 0")
    minimum_tree_end = 8 + 4 * (count + 1)
    if size_dict == 0:
        err("sizeDictBlk is zero")
    elif size_dict < minimum_tree_end + 4 + 16 * count:
        err(
            f"sizeDictBlk 0x{size_dict:X} is too small for {count} nodes, "
            "entry header, and names"
        )
    if enclosing_end is not None and size_dict and base + size_dict > enclosing_end:
        err(
            f"dictionary ends at 0x{base + size_dict:X}, beyond enclosing section "
            f"end 0x{enclosing_end:X}"
        )
    if ofs_entry == 0:
        err("ofsEntry is zero; NitroSystem will treat dictionary bytes as entry data")
    elif ofs_entry < minimum_tree_end:
        err(
            f"ofsEntry 0x{ofs_entry:X} overlaps the {count + 1}-node Patricia tree "
            f"ending at relative 0x{minimum_tree_end:X}"
        )

    try:
        for i in range(count + 1):
            ref_bit, idx_left, idx_right, idx_entry = r.unpack(
                "<BBBB", base + 8 + 4 * i, f"{label} tree node {i}"
            )
            node = {
                "ref_bit": ref_bit,
                "idx_left": idx_left,
                "idx_right": idx_right,
                "idx_entry": idx_entry,
            }
            result["nodes"].append(node)
            if idx_left > count or idx_right > count:
                err(
                    f"tree node {i} references child {idx_left}/{idx_right}, "
                    f"outside node range 0..{count}"
                )
            if idx_entry >= max(count, 1):
                err(
                    f"tree node {i} references entry {idx_entry}, outside entry "
                    f"range 0..{max(count - 1, 0)}"
                )
    except ParseError as exc:
        err(str(exc))
        return result

    if ofs_entry == 0:
        return result

    entry_base = base + ofs_entry
    try:
        unit_size, ofs_name = r.unpack("<HH", entry_base, f"{label} entry header")
    except ParseError as exc:
        err(str(exc))
        return result
    result["entry_unit_size"] = unit_size
    result["name_offset"] = ofs_name

    if unit_size == 0 and count:
        err("entry sizeUnit is zero")
    if expected_unit is not None and unit_size != expected_unit:
        err(f"entry sizeUnit is {unit_size}, expected {expected_unit}")
    minimum_name_offset = 4 + unit_size * count
    if ofs_name < minimum_name_offset:
        err(
            f"ofsName 0x{ofs_name:X} overlaps {count} entries ending at "
            f"relative 0x{minimum_name_offset:X}"
        )

    try:
        for i in range(count):
            raw = r.chunk(
                entry_base + 4 + unit_size * i,
                unit_size,
                f"{label} entry {i}",
            )
            result["entries"].append(raw.hex())
        names_raw = [
            r.chunk(entry_base + ofs_name + 16 * i, 16, f"{label} name {i}")
            for i in range(count)
        ]
    except ParseError as exc:
        err(str(exc))
        return result

    result["names"] = [decode_name(name) for name in names_raw]
    if len(set(names_raw)) != len(names_raw):
        warn("dictionary contains duplicate 16-byte names")

    if count >= 16:
        for i, name in enumerate(names_raw):
            found = patricia_lookup(result["nodes"], names_raw, name)
            if found != i:
                err(
                    f"Patricia lookup for entry {i} ({decode_name(name)!r}) returned {found}"
                )
    return result


def decode_material_linkage(
    r: Reader,
    linkage: dict[str, Any],
    material_base: int,
    material_count: int,
    section_end: int,
) -> dict[str, Any]:
    """Decode NNSG3dResDict{Tex,Pltt}ToMatIdxData entries and lists."""

    bindings: list[dict[str, Any]] = []
    label = linkage["label"]

    def err(message: str) -> None:
        linkage["valid"] = False
        linkage["errors"].append(message)
        r.audit.error(f"{label}: {message}")

    for index, entry_hex in enumerate(linkage["entries"]):
        raw = bytes.fromhex(entry_hex)
        if len(raw) != 4:
            err(f"entry {index} has {len(raw)} bytes, expected 4")
            continue
        offset, count, flag = struct.unpack("<HBB", raw)
        name = linkage["names"][index] if index < len(linkage["names"]) else ""
        entry: dict[str, Any] = {
            "index": index,
            "name": name,
            "material_index_offset": offset,
            "material_index_count": count,
            "flag": flag,
            "material_indices": [],
        }
        if count and offset == 0:
            err(f"entry {index} ({name!r}) has {count} indices but a zero list offset")
        list_start = material_base + offset
        if list_start + count > section_end:
            err(
                f"entry {index} ({name!r}) list ends at 0x{list_start + count:X}, "
                f"beyond material section end 0x{section_end:X}"
            )
        else:
            indices = list(r.chunk(list_start, count, f"{label} entry {index} index list"))
            entry["material_indices"] = indices
            for material_index in indices:
                if material_index >= material_count:
                    err(
                        f"entry {index} ({name!r}) references material {material_index}, "
                        f"but the model has {material_count} materials"
                    )
            if len(set(indices)) != len(indices):
                err(f"entry {index} ({name!r}) contains duplicate material indices {indices}")
        bindings.append(entry)

    linkage["bindings"] = bindings
    return linkage


GPU_PARAM_WORDS: dict[int, int] = {
    0x00: 0,
    0x10: 1,
    0x11: 0,
    0x12: 1,
    0x13: 1,
    0x14: 1,
    0x15: 0,
    0x16: 16,
    0x17: 12,
    0x18: 16,
    0x19: 12,
    0x1A: 9,
    0x1B: 3,
    0x1C: 3,
    0x20: 1,
    0x21: 1,
    0x22: 1,
    0x23: 2,
    0x24: 1,
    0x25: 1,
    0x26: 1,
    0x27: 1,
    0x28: 1,
    0x29: 1,
    0x2A: 1,
    0x2B: 1,
    0x30: 1,
    0x31: 1,
    0x32: 1,
    0x33: 1,
    0x34: 32,
    0x40: 1,
    0x41: 0,
    0x50: 1,
    0x60: 1,
    0x70: 3,
    0x71: 2,
    0x72: 1,
}

GPU_NAMES: dict[int, str] = {
    0x00: "NOP",
    0x14: "MTX_RESTORE",
    0x20: "COLOR",
    0x21: "NORMAL",
    0x22: "TEXCOORD",
    0x23: "VTX_16",
    0x24: "VTX_10",
    0x25: "VTX_XY",
    0x26: "VTX_XZ",
    0x27: "VTX_YZ",
    0x28: "VTX_DIFF",
    0x40: "BEGIN_VTXS",
    0x41: "END_VTXS",
}


def parse_display_list(data: bytes) -> dict[str, Any]:
    pos = 0
    commands: Counter[str] = Counter()
    errors: list[str] = []
    begin_depth = 0
    primitives: Counter[str] = Counter()
    vertex_commands = 0
    while pos < len(data):
        if pos + 4 > len(data):
            errors.append(f"truncated command word at +0x{pos:X}")
            break
        command_word_offset = pos
        cmd_bytes = data[pos : pos + 4]
        pos += 4
        for cmd in cmd_bytes:
            name = GPU_NAMES.get(cmd, f"OP_{cmd:02X}")
            commands[name] += 1
            if cmd not in GPU_PARAM_WORDS:
                errors.append(
                    f"unknown geometry opcode 0x{cmd:02X} in command word at "
                    f"+0x{command_word_offset:X}"
                )
                continue
            words = GPU_PARAM_WORDS[cmd]
            byte_count = words * 4
            if pos + byte_count > len(data):
                errors.append(
                    f"opcode 0x{cmd:02X} at command word +0x{command_word_offset:X} "
                    f"needs {byte_count} parameter bytes beyond display-list end"
                )
                pos = len(data)
                break
            params = data[pos : pos + byte_count]
            pos += byte_count
            if cmd == 0x40:
                begin_depth += 1
                if words == 1:
                    prim = struct.unpack_from("<I", params, 0)[0]
                    primitive_names = {
                        0: "triangles",
                        1: "quads",
                        2: "triangle_strip",
                        3: "quad_strip",
                    }
                    if prim not in primitive_names:
                        errors.append(f"BEGIN_VTXS has invalid primitive value {prim}")
                    else:
                        primitives[primitive_names[prim]] += 1
            elif cmd == 0x41:
                begin_depth -= 1
                if begin_depth < 0:
                    errors.append("END_VTXS appears without a matching BEGIN_VTXS")
                    begin_depth = 0
            elif cmd in (0x23, 0x24, 0x25, 0x26, 0x27, 0x28):
                vertex_commands += 1
    if begin_depth:
        errors.append(f"display list ends with {begin_depth} unmatched BEGIN_VTXS command(s)")
    return {
        "size": len(data),
        "commands": dict(sorted(commands.items())),
        "primitives": dict(sorted(primitives.items())),
        "vertex_commands": vertex_commands,
        "valid": not errors,
        "errors": errors,
    }


def parse_sbc(data: bytes, start: int, end: int, counts: dict[str, int]) -> dict[str, Any]:
    pos = start
    ops: list[dict[str, Any]] = []
    errors: list[str] = []
    saw_ret = False
    current_material: int | None = None
    bindings: list[dict[str, int | None]] = []
    guard = 0
    while pos < end:
        guard += 1
        if guard > 65536:
            errors.append("SBC parser guard exhausted")
            break
        op_offset = pos
        op = data[pos]
        base = op & 0x1F
        flags = op & 0xE0
        length = 1
        args: list[int] = []
        if base == 0x00:
            length = 1
        elif base == 0x01:
            length = 1
            saw_ret = True
        elif base == 0x02:
            length = 3
        elif base in (0x03, 0x04, 0x05, 0x07, 0x08, 0x0C, 0x0D):
            length = 2
        elif base == 0x06:
            length = 4 + (1 if flags & 0x20 else 0) + (1 if flags & 0x40 else 0)
        elif base == 0x09:
            if pos + 3 > end:
                errors.append(f"truncated NODEMIX header at 0x{op_offset:X}")
                break
            count = data[pos + 2]
            length = 3 + 3 * count
        elif base == 0x0A:
            length = 9
        elif base == 0x0B:
            length = 1
        else:
            errors.append(f"unknown SBC opcode 0x{op:02X} at 0x{op_offset:X}")
            break
        if pos + length > end:
            errors.append(
                f"SBC opcode 0x{op:02X} at 0x{op_offset:X} overruns section end 0x{end:X}"
            )
            break
        args = list(data[pos + 1 : pos + length])
        ops.append({"offset": op_offset, "opcode": op, "base": base, "args": args})
        if base == 0x02 and args:
            if args[0] >= counts["nodes"]:
                errors.append(f"NODE references node {args[0]} but model has {counts['nodes']}")
        elif base == 0x04 and args:
            current_material = args[0]
            if current_material >= counts["materials"]:
                errors.append(
                    f"MAT references material {current_material} but model has "
                    f"{counts['materials']}"
                )
        elif base == 0x05 and args:
            shape = args[0]
            if shape >= counts["shapes"]:
                errors.append(f"SHP references shape {shape} but model has {counts['shapes']}")
            bindings.append({"material": current_material, "shape": shape})
            current_material = None
        pos += length
        if saw_ret:
            break
    if not saw_ret:
        errors.append("SBC program has no RET before the material section")
    return {
        "offset": start,
        "end_limit": end,
        "parsed_end": pos,
        "operation_count": len(ops),
        "operations": ops,
        "bindings": bindings,
        "valid": not errors,
        "errors": errors,
    }


def parse_material(r: Reader, base: int, section_end: int, label: str) -> dict[str, Any]:
    result: dict[str, Any] = {"offset": base, "valid": True, "errors": []}
    try:
        (
            item_tag,
            size,
            diff_amb,
            spec_emi,
            poly_attr,
            poly_attr_mask,
            tex_image_param,
            tex_image_param_mask,
            tex_pltt_base,
            flags,
            width,
            height,
            mag_w,
            mag_h,
        ) = r.unpack("<HHIIIIIIHHHHii", base, label)
    except ParseError as exc:
        result["valid"] = False
        result["errors"].append(str(exc))
        return result
    result.update(
        {
            "item_tag": item_tag,
            "size": size,
            "diffuse_ambient": diff_amb,
            "specular_emission": spec_emi,
            "polygon_attributes": poly_attr,
            "polygon_attribute_mask": poly_attr_mask,
            "texture_image_parameter": tex_image_param,
            "texture_image_parameter_mask": tex_image_param_mask,
            "texture_palette_base": tex_pltt_base,
            "flags": flags,
            "width": width,
            "height": height,
            "magnification": [fixed(mag_w), fixed(mag_h)],
        }
    )
    if size < 44:
        result["valid"] = False
        result["errors"].append(f"material size {size} is smaller than base record size 44")
    if base + size > section_end:
        result["valid"] = False
        result["errors"].append(
            f"material ends at 0x{base + size:X}, beyond material section end 0x{section_end:X}"
        )
    return result


def parse_model(r: Reader, model_base: int, model_name: str, index: int, block_end: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "index": index,
        "name": model_name,
        "offset": model_base,
        "valid": True,
        "errors": [],
        "warnings": [],
    }

    def err(message: str) -> None:
        result["valid"] = False
        result["errors"].append(message)
        r.audit.error(f"model {index} ({model_name}): {message}")

    def warn(message: str) -> None:
        result["warnings"].append(message)
        r.audit.warn(f"model {index} ({model_name}): {message}")

    try:
        values = r.unpack("<5I8B2i4H6h2i", model_base, f"model {index} header")
    except ParseError as exc:
        err(str(exc))
        return result
    (
        size,
        ofs_sbc,
        ofs_mat,
        ofs_shp,
        ofs_evp,
        sbc_type,
        scaling_rule,
        tex_mtx_mode,
        num_node,
        num_mat,
        num_shp,
        first_unused_stack,
        dummy,
        pos_scale,
        inv_pos_scale,
        num_vertex,
        num_polygon,
        num_triangle,
        num_quad,
        box_x,
        box_y,
        box_z,
        box_w,
        box_h,
        box_d,
        box_pos_scale,
        box_inv_pos_scale,
    ) = values
    model_end = model_base + size
    result.update(
        {
            "size": size,
            "section_offsets": {
                "sbc": ofs_sbc,
                "materials": ofs_mat,
                "shapes": ofs_shp,
                "envelope_matrices": ofs_evp,
            },
            "info": {
                "sbc_type": sbc_type,
                "scaling_rule": scaling_rule,
                "texture_matrix_mode": tex_mtx_mode,
                "node_count": num_node,
                "material_count": num_mat,
                "shape_count": num_shp,
                "first_unused_matrix_stack_id": first_unused_stack,
                "dummy": dummy,
                "position_scale": fixed(pos_scale),
                "inverse_position_scale": fixed(inv_pos_scale),
                "vertex_count": num_vertex,
                "polygon_count": num_polygon,
                "triangle_count": num_triangle,
                "quad_count": num_quad,
                "box_minimum": [fixed(box_x), fixed(box_y), fixed(box_z)],
                "box_dimensions": [fixed(box_w), fixed(box_h), fixed(box_d)],
                "box_position_scale": fixed(box_pos_scale),
                "inverse_box_position_scale": fixed(box_inv_pos_scale),
            },
        }
    )
    if size < 64 or model_end > block_end:
        err(
            f"model size 0x{size:X} gives end 0x{model_end:X}, outside MDL0 end 0x{block_end:X}"
        )
        model_end = min(max(model_base + 64, model_end), block_end)
    for name, offset in (("SBC", ofs_sbc), ("material", ofs_mat), ("shape", ofs_shp)):
        if offset < 64 or model_base + offset >= model_end:
            err(f"{name} offset 0x{offset:X} is outside model data")
    if num_node == 0:
        err("model has zero nodes")
    if num_mat == 0:
        warn("model has zero materials")
    if num_shp == 0:
        warn("model has zero shapes")
    if not math.isclose(fixed(pos_scale) * fixed(inv_pos_scale), 1.0, rel_tol=1e-4, abs_tol=1e-4):
        err("position scale and inverse do not multiply to 1")
    if not math.isclose(
        fixed(box_pos_scale) * fixed(box_inv_pos_scale), 1.0, rel_tol=1e-4, abs_tol=1e-4
    ):
        err("box position scale and inverse do not multiply to 1")

    try:
        node_dict = parse_dict(
            r,
            model_base + 64,
            f"model {index} node dictionary",
            expected_unit=4,
            enclosing_end=model_base + ofs_sbc if ofs_sbc >= 64 else model_end,
        )
        r.audit.dictionaries.append(node_dict)
        result["node_dictionary"] = node_dict
        if node_dict["count"] != num_node:
            err(
                f"model info says {num_node} nodes but node dictionary has "
                f"{node_dict['count']}"
            )
    except ParseError as exc:
        err(str(exc))

    if model_base + ofs_sbc < model_end and model_base + ofs_mat <= model_end:
        sbc = parse_sbc(
            r.data,
            model_base + ofs_sbc,
            model_base + ofs_mat,
            {"nodes": num_node, "materials": num_mat, "shapes": num_shp},
        )
        result["sbc"] = sbc
        for message in sbc["errors"]:
            err(message)

    if model_base + ofs_mat < model_end:
        mat_base = model_base + ofs_mat
        try:
            tex_link, pal_link = r.unpack("<HH", mat_base, f"model {index} material header")
            material_dict = parse_dict(
                r,
                mat_base + 4,
                f"model {index} material dictionary",
                expected_unit=4,
                enclosing_end=model_base + ofs_shp if ofs_shp > ofs_mat else model_end,
            )
            r.audit.dictionaries.append(material_dict)
            result["material_dictionary"] = material_dict
            result["texture_linkage_offset"] = tex_link
            result["palette_linkage_offset"] = pal_link
            if material_dict["count"] != num_mat:
                err(
                    f"model info says {num_mat} materials but material dictionary has "
                    f"{material_dict['count']}"
                )
            materials: list[dict[str, Any]] = []
            for mat_idx, entry_hex in enumerate(material_dict["entries"]):
                if len(bytes.fromhex(entry_hex)) < 4:
                    continue
                rel = struct.unpack("<I", bytes.fromhex(entry_hex)[:4])[0]
                material = parse_material(
                    r,
                    mat_base + rel,
                    model_base + ofs_shp if ofs_shp > ofs_mat else model_end,
                    f"model {index} material {mat_idx}",
                )
                material["index"] = mat_idx
                material["name"] = material_dict["names"][mat_idx]
                materials.append(material)
                for message in material["errors"]:
                    err(f"material {mat_idx}: {message}")
            result["materials"] = materials
            for linkage_name, linkage_rel in (
                ("texture linkage", tex_link),
                ("palette linkage", pal_link),
            ):
                if linkage_rel:
                    linkage = parse_dict(
                        r,
                        mat_base + linkage_rel,
                        f"model {index} {linkage_name}",
                        expected_unit=4,
                        enclosing_end=model_base + ofs_shp if ofs_shp > ofs_mat else model_end,
                    )
                    decode_material_linkage(
                        r,
                        linkage,
                        mat_base,
                        num_mat,
                        model_base + ofs_shp if ofs_shp > ofs_mat else model_end,
                    )
                    r.audit.dictionaries.append(linkage)
                    result[linkage_name.replace(" ", "_")] = linkage
        except ParseError as exc:
            err(str(exc))

    if model_base + ofs_shp < model_end:
        shp_base = model_base + ofs_shp
        try:
            shape_dict = parse_dict(
                r,
                shp_base,
                f"model {index} shape dictionary",
                expected_unit=4,
                enclosing_end=model_end,
            )
            r.audit.dictionaries.append(shape_dict)
            result["shape_dictionary"] = shape_dict
            if shape_dict["count"] != num_shp:
                err(
                    f"model info says {num_shp} shapes but shape dictionary has "
                    f"{shape_dict['count']}"
                )
            shapes: list[dict[str, Any]] = []
            total_dl = 0
            for shape_idx, entry_hex in enumerate(shape_dict["entries"]):
                raw_entry = bytes.fromhex(entry_hex)
                if len(raw_entry) < 4:
                    continue
                rel = struct.unpack("<I", raw_entry[:4])[0]
                shape_base = shp_base + rel
                try:
                    item_tag, shape_size, flags, ofs_dl, size_dl = r.unpack(
                        "<HHIII", shape_base, f"model {index} shape {shape_idx}"
                    )
                    shape: dict[str, Any] = {
                        "index": shape_idx,
                        "name": shape_dict["names"][shape_idx],
                        "offset": shape_base,
                        "item_tag": item_tag,
                        "size": shape_size,
                        "flags": flags,
                        "display_list_offset": ofs_dl,
                        "display_list_size": size_dl,
                        "valid": True,
                        "errors": [],
                    }
                    if shape_size != 16:
                        shape["valid"] = False
                        shape["errors"].append(
                            f"shape record size is {shape_size}, expected exact Nitro size 16"
                        )
                    if size_dl % 4:
                        shape["valid"] = False
                        shape["errors"].append(
                            f"display-list size {size_dl} is not a multiple of 4"
                        )
                    dl = r.chunk(
                        shape_base + ofs_dl,
                        size_dl,
                        f"model {index} shape {shape_idx} display list",
                    )
                    dl_report = parse_display_list(dl)
                    shape["display_list"] = dl_report
                    total_dl += size_dl
                    if not dl_report["valid"]:
                        shape["valid"] = False
                        shape["errors"].extend(dl_report["errors"])
                    for message in shape["errors"]:
                        err(f"shape {shape_idx}: {message}")
                    shapes.append(shape)
                except ParseError as exc:
                    err(f"shape {shape_idx}: {exc}")
            result["shapes"] = shapes
            result["total_display_list_size"] = total_dl
        except ParseError as exc:
            err(str(exc))
    return result


def audit_nsbmd(path: Path) -> Audit:
    data = path.read_bytes()
    audit = Audit(str(path), len(data))
    r = Reader(data, audit)
    try:
        r.require(0, 16, "BMD0 header")
        magic, bom, version, file_size, header_size, block_count = r.unpack(
            "<4sHHIHH", 0, "BMD0 header"
        )
        audit.summary.update(
            {
                "magic": magic.decode("ascii", "replace"),
                "byte_order_mark": bom,
                "version": version,
                "declared_file_size": file_size,
                "header_size": header_size,
                "block_count": block_count,
            }
        )
        if magic != b"BMD0":
            audit.error(f"magic is {magic!r}, expected b'BMD0'")
        if bom != 0xFEFF:
            audit.error(f"byte-order mark is 0x{bom:04X}, expected 0xFEFF")
        if version != 2:
            audit.error(f"version is {version}, expected 2")
        if file_size != len(data):
            audit.error(
                f"declared file size 0x{file_size:X} differs from actual 0x{len(data):X}"
            )
        if header_size != 16:
            audit.error(f"header size is {header_size}, expected 16")
        if block_count == 0:
            audit.error("file contains zero data blocks")
            return audit
        r.require(header_size, 4 * block_count, "block-offset table")
        offsets = list(r.unpack(f"<{block_count}I", header_size, "block offsets"))
        audit.summary["block_offsets"] = offsets
        block_summaries: list[dict[str, Any]] = []
        for block_idx, block_offset in enumerate(offsets):
            try:
                kind, block_size = r.unpack(
                    "<4sI", block_offset, f"block {block_idx} header"
                )
            except ParseError as exc:
                audit.error(str(exc))
                continue
            kind_text = kind.decode("ascii", "replace")
            block_end = block_offset + block_size
            block_summary = {
                "index": block_idx,
                "kind": kind_text,
                "offset": block_offset,
                "size": block_size,
                "end": block_end,
            }
            block_summaries.append(block_summary)
            if block_end > len(data):
                audit.error(
                    f"block {block_idx} {kind_text} ends at 0x{block_end:X}, "
                    f"beyond file end 0x{len(data):X}"
                )
                continue
            if kind == b"MDL0":
                model_dict = parse_dict(
                    r,
                    block_offset + 8,
                    f"MDL0[{block_idx}] model dictionary",
                    expected_unit=4,
                    enclosing_end=block_end,
                )
                audit.dictionaries.append(model_dict)
                block_summary["model_dictionary"] = model_dict
                for model_idx, entry_hex in enumerate(model_dict["entries"]):
                    raw_entry = bytes.fromhex(entry_hex)
                    if len(raw_entry) < 4:
                        continue
                    rel = struct.unpack("<I", raw_entry[:4])[0]
                    name = (
                        model_dict["names"][model_idx]
                        if model_idx < len(model_dict["names"])
                        else f"model_{model_idx}"
                    )
                    audit.models.append(
                        parse_model(r, block_offset + rel, name, model_idx, block_end)
                    )
            elif kind != b"TEX0":
                audit.warn(f"unknown BMD0 block kind {kind!r} at index {block_idx}")
        audit.summary["blocks"] = block_summaries
        audit.summary["model_count"] = len(audit.models)
        audit.summary["dictionary_count"] = len(audit.dictionaries)
        audit.summary["total_display_list_size"] = sum(
            model.get("total_display_list_size", 0) for model in audit.models
        )
    except ParseError as exc:
        audit.error(str(exc))
    return audit


def compact_comparison(audits: Iterable[Audit]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for audit in audits:
        model = audit.models[0] if audit.models else {}
        info = model.get("info", {})
        rows.append(
            {
                "path": audit.path,
                "size": audit.size,
                "valid": audit.valid,
                "errors": len(audit.errors),
                "warnings": len(audit.warnings),
                "models": len(audit.models),
                "nodes": info.get("node_count"),
                "materials": info.get("material_count"),
                "shapes": info.get("shape_count"),
                "vertices": info.get("vertex_count"),
                "triangles": info.get("triangle_count"),
                "quads": info.get("quad_count"),
                "position_scale": info.get("position_scale"),
                "display_list_bytes": model.get("total_display_list_size"),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="NSBMD files to audit")
    parser.add_argument("--output", type=Path, help="write JSON report to this path")
    parser.add_argument(
        "--allow-invalid",
        action="store_true",
        help="return exit status 0 even when strict validation errors are found",
    )
    args = parser.parse_args()

    audits = [audit_nsbmd(path.resolve()) for path in args.files]
    report = {
        "format": "strict-nitro-g3d-nsbmd-audit-v1",
        "comparison": compact_comparison(audits),
        "files": [audit.as_dict() for audit in audits],
    }
    rendered = json.dumps(report, indent=2, sort_keys=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if args.allow_invalid or all(audit.valid for audit in audits) else 1


if __name__ == "__main__":
    raise SystemExit(main())

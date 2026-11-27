#!/usr/bin/env python3
"""Build follow_mon.narc for Dazzling Platinum from a user-supplied HGSS ROM + Gen 5 assets.

Self-contained (Python 3 standard library only; zero external dependencies and zero
copyrighted assets checked into the repository).

Archive layout (784 members total):
  0..565   : 566 HGSS follower BTX0 sprites (from a/0/8/1[297..862])
             Each BTX0 contains 8 directional 4bpp textures (32x32 or 64x64) and
             2 palettes inside the SAME BTX0:
               - palette 0 ("tsure_poke0", offset 0x00): normal
               - palette 1 ("tsure_poke1", offset 0x20): shiny
  566      : TP_PARAM (a/1/4/1 concatenated + 43 * 4-byte Gen 5 entries = 609 * 4 bytes)
  567      : SEQUENCE (a/0/8/1[292])
  568..570 : BALL_MODEL, BURST_MODEL, BURST_ANIM (from a/1/0/3)
  571..601 : EMOTE_MODEL, EMOTE_SEQUENCE, EMOTE_TEXTURE, 14 EMOTE_TEXTURES, 14 EMOTE_SEQUENCES
  602      : RULES_GLOBAL (a/2/2/0[0])
  603..728 : 126 RULES_LOCATION tables (borrowed by location kind, HGSS-specific rules filtered)
  729      : SCRIPTS (a/2/2/1 concatenated, 1023 * 52 bytes)
  730      : MOVEMENTS (a/2/2/2 concatenated, 108 * 80 bytes)
  731      : SPECIES_ATTR (a/2/3/1[0])
  732..733 : TEXT (a/0/2/7[265]), GIFT_TEXT (a/0/2/7[40])
  734..736 : FLY_JUMP_MODEL, FLY_JUMP_MATERIAL_ANIM, FLY_JUMP_JOINT_ANIM
  737..740 : SWEET_SCENT_MODEL, MATERIAL_ANIM, TEXTURE_ANIM, JOINT_ANIM
  741..783 : 43 synthesized Gen 5 follower BTX0 sprites (from res/pokemon/<name>/icon.png
             + normal.pal / shiny.pal), matching HGSS's exact 32x32 4bpp 8-texture / 2-palette
             BTX0 format.
"""

from __future__ import annotations

import argparse
import os
import re
import struct
import sys
import zlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Archive layout constants (must match include/overlay005/follow_mon_archive.h)
# ---------------------------------------------------------------------------

HGSS_SPRITE_COUNT = 566
GEN5_SPRITE_COUNT = 43

# HGSS ROM internal archive paths
HGSS_MMODEL = "a/0/8/1"
HGSS_TP_PARAM = "a/1/4/1"
HGSS_FIELD_EFFECTS = "a/1/0/3"
HGSS_FIELD_MOVE_EFFECTS = "a/1/3/4"
HGSS_RULES = "a/2/2/0"
HGSS_SCRIPTS = "a/2/2/1"
HGSS_MOVEMENTS = "a/2/2/2"
HGSS_SPECIES_ATTR = "a/2/3/1"
HGSS_MSGDATA = "a/0/2/7"

FIRST_SPRITE = 297
SEQUENCE_IDX = 292
BALL_MODEL = 0x81
BURST_MODEL = 0x68
BURST_ANIM = 0xA4
EMOTE_MODEL = 0x82
EMOTE_SEQUENCE = 0x8C
EMOTE_TEXTURE = 0x1C
EMOTE_KINDS = 14
EMOTE_TEXTURES = 0x02
EMOTE_SEQUENCES = 0x96
FLY_JUMP = (0x83, 0xA7, 0xA5)
SWEET_SCENT = (23, 21, 22, 20)
TEXT_BANK = 265
GIFT_TEXT_BANK = 40

LOCATIONS = 126
RULE_SIZE = 20
LOCATION_RULES = 30
SCRIPT_SIZE = 52
SCRIPT_COUNT = 1023
MOVEMENT_SIZE = 80
MOVEMENT_COUNT = 108

# Ordered layout matching include/overlay005/follow_mon_archive.h
LAYOUT: list[tuple[str, int]] = [
    ("SPRITES", HGSS_SPRITE_COUNT),
    ("TP_PARAM", 1),
    ("SEQUENCE", 1),
    ("BALL_MODEL", 1),
    ("BURST_MODEL", 1),
    ("BURST_ANIM", 1),
    ("EMOTE_MODEL", 1),
    ("EMOTE_SEQUENCE", 1),
    ("EMOTE_TEXTURE", 1),
    ("EMOTE_TEXTURES", EMOTE_KINDS),
    ("EMOTE_SEQUENCES", EMOTE_KINDS),
    ("RULES_GLOBAL", 1),
    ("RULES_LOCATION", LOCATIONS),
    ("SCRIPTS", 1),
    ("MOVEMENTS", 1),
    ("SPECIES_ATTR", 1),
    ("TEXT", 1),
    ("GIFT_TEXT", 1),
    ("FLY_JUMP_MODEL", 1),
    ("FLY_JUMP_MATERIAL_ANIM", 1),
    ("FLY_JUMP_JOINT_ANIM", 1),
    ("SWEET_SCENT_MODEL", 1),
    ("SWEET_SCENT_MATERIAL_ANIM", 1),
    ("SWEET_SCENT_TEXTURE_ANIM", 1),
    ("SWEET_SCENT_JOINT_ANIM", 1),
    ("GEN5_SPRITES", GEN5_SPRITE_COUNT),
]

HGSS_MEMBER_COUNT = sum(count for name, count in LAYOUT if name != "GEN5_SPRITES")
TOTAL_MEMBER_COUNT = sum(count for _, count in LAYOUT)
assert HGSS_MEMBER_COUNT == 741
assert TOTAL_MEMBER_COUNT == 784

HEADER_REL_PATH = Path("include/overlay005/follow_mon_archive.h")

# Platinum location mapsec (0..125) -> donor HGSS mapsec for talk rules
DONORS: dict[int, int] = {
    1: 138, 2: 126, 3: 127, 4: 134, 5: 142, 6: 128, 7: 143, 8: 134, 9: 128, 10: 128, 11: 145, 12: 143,
    13: 130, 14: 134, 15: 15,
    16: 177, 17: 178, 18: 179, 19: 180, 20: 182, 21: 165, 22: 157, 23: 181, 24: 185, 25: 160, 26: 193, 27: 186,
    28: 188, 29: 174, 30: 190, 31: 137, 32: 137, 33: 189, 34: 168, 35: 169, 36: 170, 37: 167, 38: 189, 39: 173,
    40: 176, 41: 175, 42: 171, 43: 152, 44: 150, 45: 167,
    46: 210, 47: 201, 48: 214, 49: 201, 50: 216, 51: 209, 52: 202, 53: 209, 54: 221, 57: 220, 58: 183, 59: 210,
    60: 224, 61: 135, 62: 222, 63: 183, 64: 217, 65: 220, 66: 210, 67: 210, 68: 149, 69: 200, 70: 206, 71: 213,
    72: 191, 73: 191, 74: 191, 75: 195, 76: 135, 77: 135, 78: 135, 79: 224, 81: 130, 82: 134, 83: 146, 84: 219,
    85: 189, 86: 209, 87: 203, 88: 203, 89: 203, 104: 212, 109: 146, 112: 229, 122: 213, 123: 209, 124: 209,
    125: 209,
}

# HGSS fashion-case flag 332 -> Platinum FLAG_RECEIVED_FASHION_CASE (242)
FLAG_FASHION_CASE = (332, 242)

# HGSS talk messages referencing Johto/Kanto-specific characters or places
EXCLUDED_MESSAGES = {
    143, 229, 275, 290, 291, 292, 305, 307, 319, 346, 347, 417, 418, 430, 479, 483, 492, 516, 578, 582, 608, 688,
    689, 726, 740,
}

# Standard HGSS 32x32 follower BTX0 texture and palette names
TEX_NAMES_32 = (
    "tsure_poke.1",
    "tsure_poke.10",
    "tsure_poke.11",
    "tsure_poke.12",
    "tsure_poke.13",
    "tsure_poke.14",
    "tsure_poke.15",
    "tsure_poke.16",
)
TEX_NAMES_64 = (
    "tsure_poke.1",
    "tsure_poke.2",
    "tsure_poke.3",
    "tsure_poke.4",
    "tsure_poke.5",
    "tsure_poke.6",
    "tsure_poke.7",
    "tsure_poke.8",
)
PLTT_NAMES = ("tsure_poke0", "tsure_poke1")


# ---------------------------------------------------------------------------
# Self-contained NDS ROM & NARC I/O (stdlib only)
# ---------------------------------------------------------------------------

NARC_EMPTY_NAMES = struct.pack("<IHH", 8, 0, 1) + b"\x00\xff\xff\xff"
NARC_NEW_HEADER = b"\xff\xfe\x01\x00"


class FileSliceReader:
    """Seek-based sliceable view over an open binary file."""

    def __init__(self, f):
        self._f = f
        self.size = f.seek(0, os.SEEK_END)

    def __len__(self) -> int:
        return self.size

    def read_range(self, start: int, end: int) -> bytes:
        self._f.seek(start)
        return self._f.read(max(0, end - start))


class NdsRom:
    """Minimal Nintendo DS NitroFS reader (FNT + FAT)."""

    def __init__(self, f):
        self._reader = FileSliceReader(f)
        hdr = self._reader.read_range(0, 0x200)
        if len(hdr) < 0x200:
            raise ValueError("File too small to be a Nintendo DS ROM")
        self.title = hdr[0x00:0x0C].rstrip(b"\x00").decode("ascii", "replace")
        self.game_code = hdr[0x0C:0x10].decode("ascii", "replace")
        self.revision = hdr[0x1E]
        self.fnt_offset, self.fnt_size = struct.unpack_from("<II", hdr, 0x40)
        self.fat_offset, self.fat_size = struct.unpack_from("<II", hdr, 0x48)
        fat_raw = self._reader.read_range(self.fat_offset, self.fat_offset + self.fat_size)
        self.fat = [
            struct.unpack_from("<II", fat_raw, i * 8)
            for i in range(self.fat_size // 8)
        ]
        self.paths = self._parse_fnt()

    def _parse_fnt(self) -> dict[str, int]:
        fnt = self._reader.read_range(self.fnt_offset, self.fnt_offset + self.fnt_size)
        out: dict[str, int] = {}

        def walk(dir_id: int, prefix: str) -> None:
            sub_offset, first_file = struct.unpack_from("<IH", fnt, (dir_id & 0xFFF) * 8)
            pos, file_id = sub_offset, first_file
            while pos < len(fnt):
                length = fnt[pos]
                pos += 1
                if length == 0:
                    break
                name_len = length & 0x7F
                name = fnt[pos:pos + name_len].decode("ascii")
                pos += name_len
                if length & 0x80:
                    sub_id = struct.unpack_from("<H", fnt, pos)[0]
                    pos += 2
                    walk(sub_id, prefix + name + "/")
                else:
                    out[prefix + name] = file_id
                    file_id += 1

        walk(0xF000, "")
        return out

    def file_by_path(self, path: str) -> bytes:
        if path not in self.paths:
            raise KeyError(f"Path not found in ROM NitroFS: {path}")
        start, end = self.fat[self.paths[path]]
        return self._reader.read_range(start, end)


class Narc:
    """Nintendo DS NARC archive reader/writer (unnamed archives, 4-byte aligned)."""

    def __init__(self, data: bytes | None = None):
        self.files: list[bytes] = []
        self.header = NARC_NEW_HEADER
        if data is not None:
            self._read(data)

    def _read(self, data: bytes) -> None:
        if data[:4] != b"NARC":
            raise ValueError("Not a NARC archive")
        self.header = data[4:8]
        header_size, num_blocks = struct.unpack_from("<HH", data, 0x0C)
        blocks: dict[bytes, int] = {}
        offset = header_size
        for _ in range(num_blocks):
            magic = data[offset:offset + 4]
            size = struct.unpack_from("<I", data, offset + 4)[0]
            blocks[magic] = offset
            offset += size
        fat = blocks[b"BTAF"]
        gmif = blocks[b"GMIF"] + 8
        count = struct.unpack_from("<H", data, fat + 8)[0]
        self.files = []
        for i in range(count):
            start, end = struct.unpack_from("<II", data, fat + 12 + 8 * i)
            self.files.append(data[gmif + start:gmif + end])

    def save(self) -> bytes:
        fat = bytearray()
        data = bytearray()
        for member in self.files:
            pad = (-len(data)) % 4
            if pad:
                data.extend(b"\x00" * pad)
            start = len(data)
            data.extend(member)
            fat.extend(struct.pack("<II", start, len(data)))
        end_pad = (-len(data)) % 4
        if end_pad:
            data.extend(b"\x00" * end_pad)
        btaf = b"BTAF" + struct.pack("<IHH", 12 + len(fat), len(self.files), 0) + bytes(fat)
        btnf = b"BTNF" + struct.pack("<I", 8 + len(NARC_EMPTY_NAMES)) + NARC_EMPTY_NAMES
        gmif = b"GMIF" + struct.pack("<I", 8 + len(data)) + bytes(data)
        body = btaf + btnf + gmif
        return b"NARC" + self.header + struct.pack("<IHH", 16 + len(body), 16, 3) + body


# ---------------------------------------------------------------------------
# HGSS talk rule filtering (Platinum locations borrowing from HGSS donors)
# ---------------------------------------------------------------------------

def _script_messages(scripts: bytes, script_id: int, seen: set[int] | None = None) -> set[int]:
    if seen is None:
        seen = set()
    if script_id == 0 or script_id in seen or script_id > SCRIPT_COUNT:
        return set()
    seen.add(script_id)
    data = scripts[(script_id - 1) * SCRIPT_SIZE:script_id * SCRIPT_SIZE]
    messages: set[int] = set()
    for i in range(5):
        movement, message = struct.unpack_from("<HH", data, i * 8)
        if movement == 0xFFFF:
            break
        if message:
            messages.add(message - 1)
    yes_id, no_id = struct.unpack_from("<HH", data, 44)
    return messages | _script_messages(scripts, yes_id, seen) | _script_messages(scripts, no_id, seen)


def _borrowed_rule(rule: bytes, scripts: bytes) -> bytes | None:
    script_id = struct.unpack_from("<H", rule, 10)[0] >> 6
    map_id = struct.unpack_from("<H", rule, 12)[0]
    flag = struct.unpack_from("<H", rule, 18)[0]
    pokeathlon = rule[4] >> 5
    if script_id == 0 or map_id or pokeathlon or (flag and flag != FLAG_FASHION_CASE[0]):
        return None
    if _script_messages(scripts, script_id) & EXCLUDED_MESSAGES:
        return None
    if flag:
        rule = rule[:18] + struct.pack("<H", FLAG_FASHION_CASE[1])
    return rule


def _location_rules(rules: list[bytes], scripts: bytes) -> list[bytes]:
    tables: list[bytes] = []
    for location in range(LOCATIONS):
        kept: list[bytes] = []
        if location in DONORS:
            donor = rules[DONORS[location] + 1]
            for i in range(0, len(donor), RULE_SIZE):
                rule = _borrowed_rule(donor[i:i + RULE_SIZE], scripts)
                if rule is not None:
                    kept.append(rule)
        tables.append(b"".join(kept[:LOCATION_RULES]).ljust(RULE_SIZE * LOCATION_RULES, b"\x00"))
    return tables


# ---------------------------------------------------------------------------
# Pure-stdlib PNG & JASC-PAL readers for Gen 5 icons
# ---------------------------------------------------------------------------

def _paeth_predictor(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_indexed_png(path: Path) -> tuple[int, int, list[tuple[int, int, int]], list[list[int]]]:
    """Read an indexed-color PNG (bit depth 4 or 8) using only stdlib zlib/struct."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Not a PNG file: {path}")
    pos = 8
    width = height = bit_depth = color_type = 0
    plte: list[tuple[int, int, int]] | None = None
    idat = bytearray()
    while pos < len(data):
        length, ctype = struct.unpack_from(">I4s", data, pos)
        cdata = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            width, height, bit_depth, color_type, comp, filt, interlace = struct.unpack(">IIBBBBB", cdata)
            if comp != 0 or filt != 0 or interlace != 0:
                raise ValueError(f"Unsupported PNG IHDR options in {path}")
        elif ctype == b"PLTE":
            plte = [(cdata[i], cdata[i + 1], cdata[i + 2]) for i in range(0, len(cdata), 3)]
        elif ctype == b"IDAT":
            idat.extend(cdata)
        elif ctype == b"IEND":
            break
    if color_type != 3 or plte is None or bit_depth not in (4, 8):
        raise ValueError(f"Expected 4/8-bit indexed PNG in {path} (got color_type={color_type}, depth={bit_depth})")

    raw = zlib.decompress(bytes(idat))
    stride = (width * bit_depth + 7) // 8
    rows: list[list[int]] = []
    prev = bytes(stride)
    idx = 0
    for _ in range(height):
        ftype = raw[idx]
        idx += 1
        row = bytearray(raw[idx:idx + stride])
        idx += stride
        if ftype == 0:
            pass
        elif ftype == 1:
            for i in range(1, stride):
                row[i] = (row[i] + row[i - 1]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                a = row[i - 1] if i >= 1 else 0
                row[i] = (row[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                a = row[i - 1] if i >= 1 else 0
                b = prev[i]
                c = prev[i - 1] if i >= 1 else 0
                row[i] = (row[i] + _paeth_predictor(a, b, c)) & 0xFF
        else:
            raise ValueError(f"Unsupported PNG filter type {ftype} in {path}")
        prev = bytes(row)
        if bit_depth == 8:
            pixels = list(row[:width])
        else:
            pixels = []
            for byte in row:
                pixels.append((byte >> 4) & 0xF)
                pixels.append(byte & 0xF)
            pixels = pixels[:width]
        rows.append(pixels)
    return width, height, plte, rows


def read_jasc_pal(path: Path) -> list[tuple[int, int, int]]:
    """Read a JASC-PAL file into a list of (r, g, b) tuples."""
    lines = [line.strip() for line in path.read_text(encoding="ascii").splitlines() if line.strip()]
    if len(lines) < 3 or lines[0] != "JASC-PAL":
        raise ValueError(f"Not a JASC-PAL file: {path}")
    count = int(lines[2])
    colors: list[tuple[int, int, int]] = []
    for i in range(count):
        r, g, b = map(int, lines[3 + i].split())
        colors.append((r, g, b))
    return colors


# ---------------------------------------------------------------------------
# DS BTX0 (NSBTX) builder and verifier (32x32 4bpp, 8 textures, 2 palettes)
# ---------------------------------------------------------------------------

def _name_bit(name16: bytes, ref_bit: int) -> int:
    return (name16[ref_bit >> 3] >> (ref_bit & 7)) & 1


def _build_nns_dict(entries: list[tuple[str, bytes]]) -> bytes:
    """Build a NitroSDK NNSG3dResDict with a valid Patricia trie."""
    num = len(entries)
    if num < 1:
        raise ValueError("NNSG3dResDict requires at least one entry")
    size_unit = len(entries[0][1])
    names = [name.encode("ascii").ljust(16, b"\x00")[:16] for name, _ in entries]

    # Node format: [ref_bit, idx_left, idx_right, idx_entry]
    # Node 0 is the root sentinel (refBit=127, left=0, right=0, idxEntry=0).
    nodes: list[list[int]] = [[127, 0, 0, 0]]

    def search_node(target: bytes) -> int:
        p = 0
        x = nodes[0][1]
        while nodes[p][0] > nodes[x][0]:
            p = x
            x = nodes[x][2] if _name_bit(target, nodes[x][0]) else nodes[x][1]
        return x

    for i, name16 in enumerate(names):
        new_idx = i + 1
        if i == 0:
            # Find highest set bit in first name (differs from root's implicit all-zero key)
            diff_bit = 127
            while diff_bit > 0 and _name_bit(name16, diff_bit) == 0:
                diff_bit -= 1
            nodes[0][1] = new_idx
            nodes.append([diff_bit, 0, new_idx, 0])
            continue

        matched_idx = search_node(name16)
        matched_name = names[nodes[matched_idx][3]] if matched_idx != 0 else b"\x00" * 16
        # Find highest differing bit (127 down to 0)
        diff_bit = 127
        while diff_bit >= 0 and _name_bit(name16, diff_bit) == _name_bit(matched_name, diff_bit):
            diff_bit -= 1
        if diff_bit < 0:
            raise ValueError(f"Duplicate NNS dictionary key: {entries[i][0]!r}")

        # Walk down from root until child has refBit <= diff_bit or upward link
        p = 0
        x = nodes[0][1]
        while nodes[p][0] > nodes[x][0] and nodes[x][0] > diff_bit:
            p = x
            x = nodes[x][2] if _name_bit(name16, nodes[x][0]) else nodes[x][1]

        if _name_bit(name16, diff_bit):
            new_node = [diff_bit, x, new_idx, i]
        else:
            new_node = [diff_bit, new_idx, x, i]
        nodes.append(new_node)

        if p == 0:
            nodes[0][1] = new_idx
        elif _name_bit(name16, nodes[p][0]):
            nodes[p][2] = new_idx
        else:
            nodes[p][1] = new_idx

    ofs_tree = 8
    ofs_entry = ofs_tree + 4 * len(nodes)
    ofs_name_from_entry = 4 + size_unit * num
    size_dict_blk = ofs_entry + ofs_name_from_entry + 16 * num

    out = bytearray()
    out.extend(struct.pack("<BBHHH", 0, num, size_dict_blk, ofs_tree, ofs_entry))
    for node in nodes:
        out.extend(bytes(node))
    out.extend(struct.pack("<HH", size_unit, ofs_name_from_entry))
    for _, payload in entries:
        assert len(payload) == size_unit
        out.extend(payload)
    for name16 in names:
        out.extend(name16)
    assert len(out) == size_dict_blk
    return bytes(out)


def _rgb888_to_rgb555(r: int, g: int, b: int) -> int:
    return ((r >> 3) & 0x1F) | (((g >> 3) & 0x1F) << 5) | (((b >> 3) & 0x1F) << 10)


def _pack_frame_4bpp(grid: list[list[int]]) -> bytes:
    """Pack a 32x32 4-bit indexed image into 512 bytes (DS 4bpp: low nibble = even x)."""
    out = bytearray(512)
    pos = 0
    for y in range(32):
        row = grid[y]
        for x in range(0, 32, 2):
            out[pos] = (row[x] & 0xF) | ((row[x + 1] & 0xF) << 4)
            pos += 1
    return bytes(out)


def _shift_frame_y(grid: list[list[int]], dy: int) -> list[list[int]]:
    if dy == 0:
        return [row[:] for row in grid]
    out = [[0] * 32 for _ in range(32)]
    for y in range(32):
        ny = y + dy
        if 0 <= ny < 32:
            out[ny] = grid[y][:]
    return out


def _mirror_frame_x(grid: list[list[int]]) -> list[list[int]]:
    return [row[::-1] for row in grid]


def _rgb_dist2(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def _derive_shiny_palette(
    icon_pal: list[tuple[int, int, int]],
    normal_pal: list[tuple[int, int, int]],
    shiny_pal: list[tuple[int, int, int]],
) -> list[tuple[int, int, int]]:
    """Map each non-transparent icon color via nearest color in normal.pal -> shiny.pal."""
    out = [icon_pal[0]]
    limit = min(len(normal_pal), len(shiny_pal))
    for i in range(1, 16):
        c = icon_pal[i]
        if limit <= 1:
            out.append(c)
            continue
        best_k = min(range(1, limit), key=lambda k: _rgb_dist2(c, normal_pal[k]))
        out.append(shiny_pal[best_k])
    return out


def build_btx0_32x32(
    frames_8: list[list[list[int]]],
    pal_normal: list[tuple[int, int, int]],
    pal_shiny: list[tuple[int, int, int]],
) -> bytes:
    """Build a valid DS BTX0 (4,544 bytes) matching HGSS's 32x32 4bpp follower layout."""
    assert len(frames_8) == 8
    assert len(pal_normal) == 16 and len(pal_shiny) == 16

    tex_entries: list[tuple[str, bytes]] = []
    for i, name in enumerate(TEX_NAMES_32):
        # VRAM offset in 8-byte units (i * 512 / 8 = i * 0x40)
        # S=32 (2<<20), T=32 (2<<23), GX_TEXFMT_PLTT16 (3<<26), col0 transparent (1<<29)
        tex_image_param = (i * 0x40) | (2 << 20) | (2 << 23) | (3 << 26) | (1 << 29)
        # origW=32, origH=32, sameSize=1 (bit 31)
        extra_param = 32 | (32 << 11) | (1 << 31)
        tex_entries.append((name, struct.pack("<II", tex_image_param, extra_param)))

    pltt_entries = [
        (PLTT_NAMES[0], struct.pack("<HH", 0x0000, 0)),
        (PLTT_NAMES[1], struct.pack("<HH", 0x0004, 0)),  # 32 bytes / 8 = 4
    ]

    tex_dict = _build_nns_dict(tex_entries)
    pltt_dict = _build_nns_dict(pltt_entries)

    tex_dict_ofs = 0x3C
    pltt_dict_ofs = tex_dict_ofs + len(tex_dict)
    tex_data_ofs = pltt_dict_ofs + len(pltt_dict)
    tex_data = b"".join(_pack_frame_4bpp(fr) for fr in frames_8)
    assert len(tex_data) == 4096
    pltt_data_ofs = tex_data_ofs + len(tex_data)

    pltt_data = bytearray()
    for pal in (pal_normal, pal_shiny):
        for r, g, b in pal:
            pltt_data.extend(struct.pack("<H", _rgb888_to_rgb555(r, g, b)))
    assert len(pltt_data) == 64

    tex0_size = pltt_data_ofs + len(pltt_data)
    tex0_header = (
        b"TEX0"
        + struct.pack("<I", tex0_size)
        # texInfo (16 bytes): vramKey, sizeTex>>3, dictOff, flag, pad, ofsTex
        + struct.pack("<IHHHHI", 0, len(tex_data) >> 3, tex_dict_ofs, 0, 0, tex_data_ofs)
        # tex4x4Info (20 bytes): vramKey, sizeTex>>3, dictOff, flag, pad, ofsTex, ofsTexPlttIdx
        + struct.pack("<IHHHHII", 0, 0, tex_dict_ofs, 0, 0, pltt_data_ofs, pltt_data_ofs)
        # plttInfo (16 bytes): vramKey, sizePltt>>3, flag, dictOff, pad, ofsPltt
        + struct.pack("<IHHHHI", 0, len(pltt_data) >> 3, 0, pltt_dict_ofs, 0, pltt_data_ofs)
    )
    assert len(tex0_header) == tex_dict_ofs

    tex0_block = tex0_header + tex_dict + pltt_dict + tex_data + bytes(pltt_data)
    assert len(tex0_block) == tex0_size

    file_size = 20 + tex0_size
    btx0_header = struct.pack("<4sHHIHHI", b"BTX0", 0xFEFF, 0x0001, file_size, 16, 1, 20)
    btx0 = btx0_header + tex0_block
    assert len(btx0) == 4544
    return btx0


def synthesize_gen5_sprite(species_dir: Path) -> bytes:
    """Synthesize a 32x32 8-frame 2-palette BTX0 follower sprite from icon.png + normal/shiny.pal."""
    w, h, plte, rows = read_indexed_png(species_dir / "icon.png")
    if w != 32 or h != 64:
        raise ValueError(f"Expected 32x64 icon.png in {species_dir}, got {w}x{h}")

    normal_pal = read_jasc_pal(species_dir / "normal.pal")
    shiny_pal = read_jasc_pal(species_dir / "shiny.pal")

    # Ensure palette has 16 entries
    icon_pal = list(plte[:16]) + [(0, 0, 0)] * max(0, 16 - len(plte))

    # Detect transparent background index from corners (handles icons whose bg != 0, e.g. deino)
    corners = {rows[0][0], rows[0][31], rows[31][0], rows[31][31]}
    bg = rows[0][0] if len(corners) == 1 else 0
    if bg != 0:
        icon_pal[0], icon_pal[bg] = icon_pal[bg], icon_pal[0]
        swapped = []
        for row in rows:
            swapped.append([0 if v == bg else (bg if v == 0 else v) for v in row])
        rows = swapped

    frame_a = rows[0:32]
    frame_b = rows[32:64]

    # Ground-align both frames together (preserving bounce delta) so bottom sits near y=30
    non_empty_ys = [
        y
        for fr in (frame_a, frame_b)
        for y in range(32)
        if any(fr[y])
    ]
    if non_empty_ys:
        max_y = max(non_empty_ys)
        min_y = min(non_empty_ys)
        target_bottom = 30
        if max_y < target_bottom:
            dy = min(target_bottom - max_y, 31 - max_y)
            # Don't push top out of bounds
            if min_y + dy >= 0:
                frame_a = _shift_frame_y(frame_a, dy)
                frame_b = _shift_frame_y(frame_b, dy)

    frame_a_flip = _mirror_frame_x(frame_a)
    frame_b_flip = _mirror_frame_x(frame_b)

    # HGSS frame order: 0,1 = North; 2,3 = South; 4,5 = West; 6,7 = East
    frames_8 = [
        frame_a, frame_b,            # North (up)
        frame_a, frame_b,            # South (down)
        frame_a, frame_b,            # West (left)
        frame_a_flip, frame_b_flip,  # East (right)
    ]

    pal_shiny = _derive_shiny_palette(icon_pal, normal_pal, shiny_pal)
    return build_btx0_32x32(frames_8, icon_pal, pal_shiny)


# ---------------------------------------------------------------------------
# Gen 5 species discovery
# ---------------------------------------------------------------------------

def gen5_species_dirs(repo_root: Path) -> list[tuple[str, Path]]:
    """Return (SPECIES_NAME, res/pokemon/<name>) for all species after SPECIES_ARCEUS."""
    species_txt = repo_root / "generated/species.txt"
    lines = [line.strip() for line in species_txt.read_text(encoding="utf-8").splitlines() if line.strip()]
    arceus_idx = lines.index("SPECIES_ARCEUS")
    result: list[tuple[str, Path]] = []
    for sym in lines[arceus_idx + 1:]:
        if sym in ("SPECIES_EGG", "SPECIES_BAD_EGG"):
            continue
        dir_name = sym[len("SPECIES_"):].lower()
        result.append((sym, repo_root / "res/pokemon" / dir_name))
    if len(result) != GEN5_SPRITE_COUNT:
        raise ValueError(f"Expected {GEN5_SPRITE_COUNT} Gen 5 species after SPECIES_ARCEUS, found {len(result)}")
    return result


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------

def _verify_nns_dict(data: bytes, dict_ofs: int, expected_names: tuple[str, ...]) -> list[tuple[str, bytes]]:
    rev, num, size_blk, ofs_tree, ofs_entry = struct.unpack_from("<BBHHH", data, dict_ofs)
    assert rev == 0, f"Unexpected NNS dict rev {rev}"
    assert num == len(expected_names), f"Expected {len(expected_names)} dict entries, got {num}"
    nodes = [
        tuple(data[dict_ofs + ofs_tree + i * 4:dict_ofs + ofs_tree + (i + 1) * 4])
        for i in range(num + 1)
    ]
    entry_base = dict_ofs + ofs_entry
    size_unit, ofs_name = struct.unpack_from("<HH", data, entry_base)
    entries: list[tuple[str, bytes]] = []
    raw_names: list[bytes] = []
    for i in range(num):
        payload = data[entry_base + 4 + i * size_unit:entry_base + 4 + (i + 1) * size_unit]
        raw_name = data[entry_base + ofs_name + i * 16:entry_base + ofs_name + (i + 1) * 16]
        raw_names.append(raw_name)
        entries.append((raw_name.split(b"\x00", 1)[0].decode("ascii"), payload))

    actual_names = tuple(name for name, _ in entries)
    assert actual_names == expected_names, f"Dict names mismatch: {actual_names} != {expected_names}"

    # Verify Patricia trie lookup works for every single name (exact NNS_G3dGetResDataByName traversal)
    for i, target in enumerate(raw_names):
        p = 0
        x = nodes[0][1]
        steps = 0
        while nodes[p][0] > nodes[x][0]:
            p = x
            x = nodes[x][2] if _name_bit(target, nodes[x][0]) else nodes[x][1]
            steps += 1
            assert steps <= num + 2, f"Cycle in Patricia trie looking up {expected_names[i]!r}"
        assert nodes[x][3] == i, f"Patricia trie lookup for {expected_names[i]!r} returned {nodes[x][3]}, expected {i}"
    return entries


def verify_btx0(data: bytes, label: str, expected_dim: int | None = None) -> tuple[int, int]:
    """Parse and thoroughly verify a follower BTX0 sprite; returns (dim, palette_count)."""
    assert len(data) >= 0x40, f"{label}: too short ({len(data)} bytes)"
    magic, bom, ver, fsize, hsize, nblocks, blk_ofs = struct.unpack_from("<4sHHIHHI", data, 0)
    assert magic == b"BTX0", f"{label}: bad magic {magic!r}"
    assert bom == 0xFEFF and ver == 0x0001, f"{label}: bad BOM/ver {bom:#x}/{ver:#x}"
    assert fsize == len(data), f"{label}: fileSize {fsize} != len {len(data)}"
    assert hsize == 16 and nblocks == 1 and blk_ofs == 20, f"{label}: unexpected BTX0 header"

    tex_magic, tex_size = struct.unpack_from("<4sI", data, blk_ofs)
    assert tex_magic == b"TEX0" and blk_ofs + tex_size == len(data), f"{label}: bad TEX0 block"

    _, t_size8, t_dict, _, _, t_ofs = struct.unpack_from("<IHHHHI", data, blk_ofs + 8)
    _, p_size8, _, p_dict, _, p_ofs = struct.unpack_from("<IHHHHI", data, blk_ofs + 0x2C)

    t_bytes = t_size8 << 3
    p_bytes = p_size8 << 3
    assert t_bytes in (4096, 16384), f"{label}: unexpected tex_bytes {t_bytes}"
    assert p_bytes == 64, f"{label}: expected 64 palette bytes (2x 16 RGB555), got {p_bytes}"
    assert blk_ofs + t_ofs + t_bytes <= len(data), f"{label}: tex data out of bounds"
    assert blk_ofs + p_ofs + p_bytes <= len(data), f"{label}: pltt data out of bounds"

    dim = 32 if t_bytes == 4096 else 64
    if expected_dim is not None:
        assert dim == expected_dim, f"{label}: expected {expected_dim}x{expected_dim}, got {dim}x{dim}"
    expected_tex_names = TEX_NAMES_32 if dim == 32 else TEX_NAMES_64
    frame_bytes = (dim * dim) // 2

    tex_entries = _verify_nns_dict(data, blk_ofs + t_dict, expected_tex_names)
    for i, (tname, payload) in enumerate(tex_entries):
        param, extra = struct.unpack("<II", payload)
        vram_off = (param & 0xFFFF) << 3
        s = 8 << ((param >> 20) & 7)
        t = 8 << ((param >> 23) & 7)
        fmt = (param >> 26) & 7
        col0 = (param >> 29) & 1
        assert vram_off == i * frame_bytes, f"{label}/{tname}: bad vram offset {vram_off:#x}"
        assert s == dim and t == dim, f"{label}/{tname}: bad size {s}x{t}"
        assert fmt == 3 and col0 == 1, f"{label}/{tname}: bad fmt={fmt} col0={col0}"
        assert (extra & 0x7FF) == dim and ((extra >> 11) & 0x7FF) == dim, f"{label}/{tname}: bad extra {extra:#x}"

    pltt_entries = _verify_nns_dict(data, blk_ofs + p_dict, PLTT_NAMES)
    for i, (pname, payload) in enumerate(pltt_entries):
        ofs8, flag = struct.unpack("<HH", payload)
        assert (ofs8 << 3) == i * 32 and flag == 0, f"{label}/{pname}: bad pltt entry {ofs8:#x}/{flag:#x}"

    return dim, len(pltt_entries)


def verify_header_sync(repo_root: Path) -> None:
    """Check that include/overlay005/follow_mon_archive.h matches LAYOUT exactly."""
    header_path = repo_root / HEADER_REL_PATH
    if not header_path.exists():
        return
    text = header_path.read_text(encoding="utf-8")
    defines = dict(re.findall(r"#define\s+FOLLOW_MON_ARC_(\w+)\s+(\d+)", text))
    offset = 0
    for name, count in LAYOUT:
        if name not in defines:
            raise AssertionError(f"{HEADER_REL_PATH}: missing FOLLOW_MON_ARC_{name}")
        actual = int(defines[name])
        if actual != offset:
            raise AssertionError(f"{HEADER_REL_PATH}: FOLLOW_MON_ARC_{name} is {actual}, expected {offset}")
        offset += count
    assert int(defines["HGSS_SPRITE_COUNT"]) == HGSS_SPRITE_COUNT
    assert int(defines["GEN5_SPRITE_COUNT"]) == GEN5_SPRITE_COUNT
    assert int(defines["HGSS_MEMBER_COUNT"]) == HGSS_MEMBER_COUNT
    if "MEMBER_COUNT" in defines:
        assert int(defines["MEMBER_COUNT"]) == TOTAL_MEMBER_COUNT


def verify_archive(narc_path: Path, repo_root: Path) -> None:
    """Parse and verify every member of a built follow_mon.narc."""
    narc = Narc(narc_path.read_bytes())
    assert len(narc.files) == TOTAL_MEMBER_COUNT, (
        f"Expected {TOTAL_MEMBER_COUNT} NARC members, got {len(narc.files)}"
    )

    dims_hgss = {32: 0, 64: 0}
    for i in range(HGSS_SPRITE_COUNT):
        dim, pcnt = verify_btx0(narc.files[i], f"HGSS sprite {i}")
        assert pcnt == 2
        dims_hgss[dim] += 1

    # TP_PARAM (566)
    tp_param = narc.files[HGSS_SPRITE_COUNT]
    expected_tp_len = 4 * (HGSS_SPRITE_COUNT + GEN5_SPRITE_COUNT)
    assert len(tp_param) == expected_tp_len, f"TP_PARAM len {len(tp_param)} != {expected_tp_len}"
    # Verify large-flag in TP_PARAM matches 64x64 BTX0 dimensions for all 566 HGSS sprites
    for i in range(HGSS_SPRITE_COUNT):
        is_big_tp = tp_param[i * 4 + 1] != 0
        is_big_btx = len(narc.files[i]) == 16832
        assert is_big_tp == is_big_btx, f"TP_PARAM size flag mismatch at sprite {i}"

    # Scripts & movements
    scripts = narc.files[729]
    movements = narc.files[730]
    assert len(scripts) == SCRIPT_SIZE * SCRIPT_COUNT
    assert len(movements) == MOVEMENT_SIZE * MOVEMENT_COUNT

    # Gen 5 sprites (741..783)
    gen5_list = gen5_species_dirs(repo_root)
    for k, (sym, _) in enumerate(gen5_list):
        member_idx = HGSS_MEMBER_COUNT + k
        dim, pcnt = verify_btx0(narc.files[member_idx], f"Gen5 {sym} (member {member_idx})", expected_dim=32)
        assert dim == 32 and pcnt == 2
        # Verify non-empty pixel data
        tex_data = narc.files[member_idx][0x180:0x180 + 4096]
        assert any(tex_data), f"Gen5 {sym} has empty pixel data"

    verify_header_sync(repo_root)
    print(
        f"Verified {narc_path}: {len(narc.files)} members "
        f"(HGSS: {dims_hgss[32]}x 32x32 + {dims_hgss[64]}x 64x64; "
        f"Gen5: {GEN5_SPRITE_COUNT}x 32x32; TP_PARAM: {len(tp_param)} bytes)"
    )


# ---------------------------------------------------------------------------
# Main build logic
# ---------------------------------------------------------------------------

def find_hgss_rom(explicit_rom: str | None, repo_root: Path) -> Path | None:
    candidates: list[Path] = []
    if explicit_rom:
        p = Path(explicit_rom).expanduser()
        return p if p.is_file() else None
    env_rom = os.environ.get("HGSS_ROM")
    if env_rom:
        candidates.append(Path(env_rom).expanduser())
    for base in (repo_root / "ignoreRoms", Path.home() / "Documents/dazzlingPlatinum/ignoreRoms"):
        candidates.append(base / "heartGold.nds")
        candidates.append(base / "soulSilver.nds")
    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def is_up_to_date(out_path: Path, rom_path: Path, repo_root: Path) -> bool:
    if not out_path.is_file():
        return False
    out_mtime = out_path.stat().st_mtime
    inputs = [
        rom_path,
        Path(__file__).resolve(),
        repo_root / "generated/species.txt",
    ]
    for _, sp_dir in gen5_species_dirs(repo_root):
        inputs.extend([sp_dir / "icon.png", sp_dir / "normal.pal", sp_dir / "shiny.pal"])
    return all(p.is_file() and p.stat().st_mtime <= out_mtime for p in inputs)


def build_archive(rom_path: Path, repo_root: Path) -> bytes:
    with rom_path.open("rb") as f:
        rom = NdsRom(f)
        if not (rom.game_code.startswith("IPK") or rom.game_code.startswith("IPG")):
            raise ValueError(
                f"ROM {rom_path} has game code {rom.game_code!r}; expected HeartGold (IPK*) or SoulSilver (IPG*)"
            )
        mmodel = Narc(rom.file_by_path(HGSS_MMODEL)).files
        effects = Narc(rom.file_by_path(HGSS_FIELD_EFFECTS)).files
        move_effects = Narc(rom.file_by_path(HGSS_FIELD_MOVE_EFFECTS)).files
        rules = Narc(rom.file_by_path(HGSS_RULES)).files
        msgdata = Narc(rom.file_by_path(HGSS_MSGDATA)).files

        sprites = mmodel[FIRST_SPRITE:FIRST_SPRITE + HGSS_SPRITE_COUNT]
        tp_param_hgss = b"".join(Narc(rom.file_by_path(HGSS_TP_PARAM)).files)
        scripts = b"".join(Narc(rom.file_by_path(HGSS_SCRIPTS)).files)
        movements = b"".join(Narc(rom.file_by_path(HGSS_MOVEMENTS)).files)
        attrs = Narc(rom.file_by_path(HGSS_SPECIES_ATTR)).files[0]

    assert len(sprites) == HGSS_SPRITE_COUNT
    assert all(s[:4] == b"BTX0" for s in sprites), "HGSS follower sprites not found at expected offsets"
    assert len(tp_param_hgss) == 4 * HGSS_SPRITE_COUNT
    assert len(scripts) == SCRIPT_SIZE * SCRIPT_COUNT
    assert len(movements) == MOVEMENT_SIZE * MOVEMENT_COUNT

    # Synthesize 43 Gen 5 32x32 follower sprites and extend TP_PARAM (4 bytes per sprite)
    gen5_sprites: list[bytes] = []
    gen5_tp_entries = bytearray()
    for _, sp_dir in gen5_species_dirs(repo_root):
        gen5_sprites.append(synthesize_gen5_sprite(sp_dir))
        gen5_tp_entries.extend(b"\x00\x00\x00\x00")  # standard 32x32 grounded sprite

    tp_param = tp_param_hgss + bytes(gen5_tp_entries)
    assert len(tp_param) == 4 * (HGSS_SPRITE_COUNT + GEN5_SPRITE_COUNT)

    members: list[bytes] = (
        list(sprites)
        + [tp_param, mmodel[SEQUENCE_IDX]]
        + [effects[i] for i in (BALL_MODEL, BURST_MODEL, BURST_ANIM)]
        + [effects[i] for i in (EMOTE_MODEL, EMOTE_SEQUENCE, EMOTE_TEXTURE)]
        + [effects[EMOTE_TEXTURES + k] for k in range(EMOTE_KINDS)]
        + [effects[EMOTE_SEQUENCES + k] for k in range(EMOTE_KINDS)]
        + [rules[0]]
        + _location_rules(rules, scripts)
        + [scripts, movements, attrs, msgdata[TEXT_BANK], msgdata[GIFT_TEXT_BANK]]
        + [effects[i] for i in FLY_JUMP]
        + [move_effects[i] for i in SWEET_SCENT]
        + gen5_sprites
    )
    assert len(members) == TOTAL_MEMBER_COUNT

    narc = Narc()
    narc.files = members
    return narc.save()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build follow_mon.narc from an HGSS ROM + Gen 5 assets.")
    parser.add_argument("--rom", help="Path to clean USA HeartGold or SoulSilver .nds ROM")
    parser.add_argument("--out", help="Destination path for follow_mon.narc (default: <repo>/follow_mon.narc)")
    parser.add_argument("--repo", help="Dazzling Platinum repo root (default: auto-detected)")
    parser.add_argument("--optional", action="store_true", help="Exit 0 silently if no HGSS ROM is found")
    parser.add_argument("--if-stale", action="store_true", help="Skip rebuild if --out is newer than all inputs")
    parser.add_argument("--verify", action="store_true", help="Parse and verify every member after building")
    parser.add_argument("--quiet", action="store_true", help="Suppress informational output")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[2]
    out_path = Path(args.out).expanduser() if args.out else repo_root / "follow_mon.narc"

    rom_path = find_hgss_rom(args.rom, repo_root)
    if rom_path is None:
        if args.optional:
            if not args.quiet:
                print("follow_mon: HGSS ROM not found; skipping follow_mon.narc", file=sys.stderr)
            return 0
        print(
            "Error: HGSS ROM not found. Pass --rom <path>, set $HGSS_ROM, or place heartGold.nds in ignoreRoms/.",
            file=sys.stderr,
        )
        return 1

    if args.if_stale and is_up_to_date(out_path, rom_path, repo_root):
        if args.verify:
            verify_archive(out_path, repo_root)
        return 0

    data = build_archive(rom_path, repo_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp_path.write_bytes(data)
    tmp_path.replace(out_path)

    if not args.quiet:
        print(f"follow_mon: wrote {out_path} ({len(data):,} bytes, {TOTAL_MEMBER_COUNT} members) from {rom_path.name}")

    if args.verify:
        verify_archive(out_path, repo_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())

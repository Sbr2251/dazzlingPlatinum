"""Readers for the Nitro graphics files the battle stage tool needs, plus a NARC writer.

Covers exactly what pl_batt_bg.narc / pl_batt_obj.narc use:
    LZ77 (type 0x10) compression
    NARC   archives (unnamed: BTAF + empty BTNF + GMIF)
    NCGR   character data (4bpp / 8bpp tiles)
    NCLR   palettes
    NSCR   text BG tilemaps
    NCER   cell banks (OAM lists)
"""

import struct


def lz77_decompress(data):
    """Decompresses a type 0x10 LZ77 stream. Data that does not start with 0x10 is
    returned unchanged, so callers can pass members that may or may not be compressed."""
    if not data or data[0] != 0x10:
        return bytes(data)

    size = data[1] | (data[2] << 8) | (data[3] << 16)
    src = 4
    out = bytearray()

    while len(out) < size:
        flags = data[src]
        src += 1

        for bit in range(8):
            if len(out) >= size:
                break

            if flags & (0x80 >> bit):
                b0, b1 = data[src], data[src + 1]
                src += 2
                length = (b0 >> 4) + 3
                disp = (((b0 & 0xF) << 8) | b1) + 1

                for _ in range(length):
                    out.append(out[-disp])
            else:
                out.append(data[src])
                src += 1

    return bytes(out)


def read_narc(path):
    """Returns the list of member byte strings of an unnamed NARC."""
    with open(path, "rb") as f:
        d = f.read()

    assert d[:4] == b"NARC", path
    header_size, num_sections = struct.unpack_from("<HH", d, 12)
    sections = {}
    offset = header_size

    for _ in range(num_sections):
        magic = d[offset:offset + 4]
        size = struct.unpack_from("<I", d, offset + 4)[0]
        sections[magic] = d[offset:offset + size]
        offset += size

    btaf, gmif = sections[b"BTAF"], sections[b"GMIF"]
    count = struct.unpack_from("<H", btaf, 8)[0]
    members = []

    for i in range(count):
        start, end = struct.unpack_from("<II", btaf, 12 + 8 * i)
        members.append(gmif[8 + start:8 + end])

    return members


def write_narc(path, members):
    """Writes an unnamed NARC in the same layout as the stock archives: members 4-byte
    aligned with 0xFF padding, an empty BTNF, byte order mark FFFE, version 0x0100."""
    blob = bytearray()
    ranges = []

    for m in members:
        blob += b"\xff" * (-len(blob) % 4)
        ranges.append((len(blob), len(blob) + len(m)))
        blob += m

    blob += b"\xff" * (-len(blob) % 4)

    btaf = b"BTAF" + struct.pack("<IHH", 12 + 8 * len(members), len(members), 0)
    btaf += b"".join(struct.pack("<II", a, b) for a, b in ranges)
    # Root directory entry only: subtable offset 4, first file 0, 1 directory
    btnf = b"BTNF" + struct.pack("<IIHH", 16, 4, 0, 1)
    gmif = b"GMIF" + struct.pack("<I", 8 + len(blob)) + bytes(blob)
    body = btaf + btnf + gmif
    header = b"NARC" + struct.pack("<HHIHH", 0xFFFE, 0x0100, 16 + len(body), 16, 3)

    with open(path, "wb") as f:
        f.write(header + body)


def _sections(data):
    """Splits a Nitro generic file (NCGR, NCLR, ...) into {magic: section bytes}."""
    header_size, num_sections = struct.unpack_from("<HH", data, 12)
    sections = {}
    offset = header_size

    for _ in range(num_sections):
        magic = data[offset:offset + 4]
        size = struct.unpack_from("<I", data, offset + 4)[0]
        sections[magic] = data[offset:offset + size]
        offset += size

    return sections


def read_nclr(data):
    """Returns the palette as a list of 15-bit GXRgb values."""
    pltt = _sections(lz77_decompress(data))[b"TTLP"]
    _bit_depth, _unk, size, offset = struct.unpack_from("<IIII", pltt, 8)
    raw = pltt[8 + offset:8 + offset + size]
    return [c & 0x7FFF for c in struct.unpack("<%dH" % (len(raw) // 2), raw)]


class Ncgr:
    """Character data. tiles[i] is a list of 64 palette indices (8x8, row major)."""

    def __init__(self, data):
        char = _sections(lz77_decompress(data))[b"RAHC"]
        self.height_tiles, self.width_tiles, depth, self.mapping, self.linear, size, offset = struct.unpack_from("<HHIIIII", char, 8)
        self.bpp = 4 if depth == 3 else 8
        raw = char[8 + offset:8 + offset + size]
        tile_bytes = 8 * self.bpp
        self.tiles = []

        for t in range(len(raw) // tile_bytes):
            chunk = raw[t * tile_bytes:(t + 1) * tile_bytes]

            if self.bpp == 8:
                self.tiles.append(list(chunk))
            else:
                pixels = []

                for b in chunk:
                    pixels.append(b & 0xF)
                    pixels.append(b >> 4)

                self.tiles.append(pixels)


class Nscr:
    """Text BG tilemap. entries are in VRAM order: a 512-wide map is two 256x256 screen
    blocks, left then right."""

    def __init__(self, data):
        scrn = _sections(lz77_decompress(data))[b"NRCS"]
        self.width, self.height, _fmt, size = struct.unpack_from("<HHII", scrn, 8)
        raw = scrn[0x14:0x14 + size]
        self.entries = list(struct.unpack("<%dH" % (len(raw) // 2), raw))

    def entry_at(self, tx, ty):
        """Entry for the tile at column tx, row ty of the whole map."""
        blocks_x = max(1, self.width // 256)
        block = (ty // 32) * blocks_x + (tx // 32)
        return self.entries[block * 1024 + (ty % 32) * 32 + (tx % 32)]


def render_bg_256(ncgr, nscr):
    """Renders a 256-colour text BG to a 2D list [y][x] of palette indices (0..255).
    Extended palettes are not used by the battle backdrop, so the entry's palette bits
    are ignored."""
    w, h = nscr.width, nscr.height
    img = [[0] * w for _ in range(h)]

    for ty in range(h // 8):
        for tx in range(w // 8):
            e = nscr.entry_at(tx, ty)
            tile = ncgr.tiles[e & 0x3FF]
            hflip, vflip = (e >> 10) & 1, (e >> 11) & 1

            for py in range(8):
                sy = 7 - py if vflip else py
                row = img[ty * 8 + py]

                for px in range(8):
                    sx = 7 - px if hflip else px
                    row[tx * 8 + px] = tile[sy * 8 + sx]

    return img


# OAM shape/size -> (width, height) in pixels
OBJ_SIZES = {
    (0, 0): (8, 8), (0, 1): (16, 16), (0, 2): (32, 32), (0, 3): (64, 64),
    (1, 0): (16, 8), (1, 1): (32, 8), (1, 2): (32, 16), (1, 3): (64, 32),
    (2, 0): (8, 16), (2, 1): (8, 32), (2, 2): (16, 32), (2, 3): (32, 64),
}


class Ncer:
    """Cell bank. cells[i] is a list of OAM dicts: x, y (relative to the cell origin),
    w, h, tile (in bytes offset units, see char_offset), palette, hflip, vflip, depth4."""

    def __init__(self, data):
        cebk = _sections(lz77_decompress(data))[b"KBEC"]
        num_cells, attr_type, cell_offset, self.mapping = struct.unpack_from("<HHII", cebk, 8)
        base = 8 + cell_offset
        entry_size = 16 if attr_type == 1 else 8
        oam_base = base + num_cells * entry_size
        self.cells = []

        for c in range(num_cells):
            num_oam, _attr, oam_offset = struct.unpack_from("<HHI", cebk, base + c * entry_size)
            oams = []

            for o in range(num_oam):
                a0, a1, a2 = struct.unpack_from("<HHH", cebk, oam_base + oam_offset + o * 6)
                y = a0 & 0xFF
                x = a1 & 0x1FF
                y = y - 256 if y >= 128 else y
                x = x - 512 if x >= 256 else x
                shape, size = a0 >> 14, a1 >> 14
                w, h = OBJ_SIZES[(shape, size)]
                affine = (a0 >> 8) & 1
                oams.append({
                    "x": x,
                    "y": y,
                    "w": w,
                    "h": h,
                    "tile": a2 & 0x3FF,
                    "palette": a2 >> 12,
                    "hflip": 0 if affine else (a1 >> 12) & 1,
                    "vflip": 0 if affine else (a1 >> 13) & 1,
                    "depth8": (a0 >> 13) & 1,
                    "affine": affine,
                })

            self.cells.append(oams)

    def tile_bytes_unit(self):
        """Byte size of one OAM character name step for this bank's mapping mode
        (GX_OBJVRAMMODE_CHAR_1D_32K = 32 bytes, _64K = 64, _128K = 128, _256K = 256)."""
        return {0: 32, 1: 64, 2: 128, 3: 256}.get(self.mapping, 32)


def render_cell(ncgr, ncer, cell_index):
    """Renders one 4bpp cell with 1D character mapping.

    Returns (pixels, oams): pixels is a dict {(x, y): palette index} relative to the
    cell origin (the sprite position), holding only non-transparent pixels. Later OAMs
    in the list are drawn behind earlier ones, as on hardware."""
    pixels = {}
    oams = ncer.cells[cell_index]
    unit = ncer.tile_bytes_unit() // 32  # in 4bpp tiles

    for oam in reversed(oams):
        first_tile = oam["tile"] * unit
        tiles_w = oam["w"] // 8

        for py in range(oam["h"]):
            for px in range(oam["w"]):
                sx = oam["w"] - 1 - px if oam["hflip"] else px
                sy = oam["h"] - 1 - py if oam["vflip"] else py
                tile = ncgr.tiles[first_tile + (sy // 8) * tiles_w + (sx // 8)]
                index = tile[(sy % 8) * 8 + (sx % 8)]

                if index != 0:
                    pixels[(oam["x"] + px, oam["y"] + py)] = index

    return pixels, oams


def gxrgb_to_rgb888(c):
    """GXRgb (5:5:5) to an 8-bit RGB tuple, expanding like DeSmuME (c << 3 | c >> 2)."""
    r, g, b = c & 31, (c >> 5) & 31, (c >> 10) & 31
    return ((r << 3) | (r >> 2), (g << 3) | (g >> 2), (b << 3) | (b >> 2))

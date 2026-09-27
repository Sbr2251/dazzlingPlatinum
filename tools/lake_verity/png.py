#!/usr/bin/env python3
"""Minimal PNG reader/writer (standard library only: zlib + struct).

read(path)  -> Image(width, height, pixels=[[(r, g, b, a)]], palette=[(r, g, b, a)] or None, indices=[[i]] or None)
               Supports bit depths 1/2/4/8 (16 is reduced to 8), colour types 0 (grey), 2 (RGB), 3 (indexed),
               4 (grey+alpha), 6 (RGBA), tRNS, non-interlaced only.
write_rgba(path, w, h, pixels)             8-bit RGBA
write_indexed(path, w, h, indices, palette, bits=None, transparent0=False)
                                           indexed at 1/2/4/8 bits (smallest that fits unless given); palette RGB
                                           tuples; transparent0 writes a tRNS making index 0 fully transparent.
"""
import struct
import zlib


class Image:
    def __init__(self, width, height, pixels, palette=None, indices=None, bit_depth=8, color_type=6):
        self.width, self.height, self.pixels = width, height, pixels
        self.palette, self.indices, self.bit_depth, self.color_type = palette, indices, bit_depth, color_type


def _chunks(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    o = 8
    while o < len(data):
        n = struct.unpack_from(">I", data, o)[0]
        yield data[o + 4:o + 8], data[o + 8:o + 8 + n]
        o += 12 + n


def _unfilter(raw, w, h, bpp_bits):
    bpp = max(1, bpp_bits // 8)
    stride = (w * bpp_bits + 7) // 8
    out, prev, o = [], bytearray(stride), 0
    for _ in range(h):
        ft = raw[o]
        line = bytearray(raw[o + 1:o + 1 + stride])
        o += 1 + stride
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if ft == 1:
                line[i] = (line[i] + a) & 255
            elif ft == 2:
                line[i] = (line[i] + b) & 255
            elif ft == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif ft == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out.append(bytes(line))
        prev = line
    return out


def _samples(line, w, n, bits):
    if bits == 8:
        return list(line[:w * n])
    if bits == 16:
        return [line[2 * i] for i in range(w * n)]
    per = 8 // bits
    mask = (1 << bits) - 1
    return [(line[i // per] >> (8 - bits - (i % per) * bits)) & mask for i in range(w * n)]


def read(path):
    data = open(path, "rb").read()
    idat, plte, trns = b"", None, None
    for typ, body in _chunks(data):
        if typ == b"IHDR":
            w, h, bits, ct, _, _, interlace = struct.unpack(">IIBBBBB", body)
            assert interlace == 0, "interlaced PNG not supported"
        elif typ == b"PLTE":
            plte = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif typ == b"tRNS":
            trns = body
        elif typ == b"IDAT":
            idat += body
    n = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
    lines = _unfilter(zlib.decompress(idat), w, h, bits * n)
    palette = indices = None
    if ct == 3:
        alpha = list(trns or b"") + [255] * (len(plte) - len(trns or b""))
        palette = [plte[i] + (alpha[i],) for i in range(len(plte))]
        indices = [_samples(ln, w, 1, bits) for ln in lines]
        pixels = [[palette[i] if i < len(palette) else (0, 0, 0, 255) for i in row] for row in indices]
    else:
        scale = 255 // ((1 << min(bits, 8)) - 1)
        pixels = []
        for ln in lines:
            s = [v * scale for v in _samples(ln, w, n, bits)]
            if ct == 0:
                row = [(v, v, v, 255) for v in s]
            elif ct == 4:
                row = [(s[2 * i], s[2 * i], s[2 * i], s[2 * i + 1]) for i in range(w)]
            elif ct == 2:
                row = [(s[3 * i], s[3 * i + 1], s[3 * i + 2], 255) for i in range(w)]
            else:
                row = [tuple(s[4 * i:4 * i + 4]) for i in range(w)]
            pixels.append(row)
    return Image(w, h, pixels, palette, indices, bits, ct)


def _chunk(typ, body):
    return struct.pack(">I", len(body)) + typ + body + struct.pack(">I", zlib.crc32(typ + body) & 0xFFFFFFFF)


def _write(path, w, h, bits, ct, rows, extra=b""):
    raw = b"".join(b"\0" + r for r in rows)
    out = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, bits, ct, 0, 0, 0)) + extra
    out += _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(out)


def write_rgba(path, w, h, pixels):
    rows = [bytes(c for p in row for c in (tuple(p) + (255,))[:4]) for row in pixels]
    _write(path, w, h, 8, 6, rows)


def write_indexed(path, w, h, indices, palette, bits=None, transparent0=False):
    if bits is None:
        n = max(len(palette), 1)
        bits = 1 if n <= 2 else 2 if n <= 4 else 4 if n <= 16 else 8
    per = 8 // bits
    rows = []
    for row in indices:
        b = bytearray((w * bits + 7) // 8)
        for x, v in enumerate(row):
            b[x // per] |= (v & ((1 << bits) - 1)) << (8 - bits - (x % per) * bits)
        rows.append(bytes(b))
    pal = list(palette) + [(0, 0, 0)] * ((1 << bits) - len(palette)) if len(palette) < (1 << bits) else list(palette)
    extra = _chunk(b"PLTE", b"".join(bytes(tuple(c)[:3]) for c in pal[:1 << bits]))
    alphas = [tuple(c)[3] if len(tuple(c)) > 3 else 255 for c in pal[:1 << bits]]
    if transparent0:
        alphas[0] = 0
    if any(a != 255 for a in alphas):
        last = max(i for i, a in enumerate(alphas) if a != 255)
        extra += _chunk(b"tRNS", bytes(alphas[:last + 1]))
    _write(path, w, h, bits, 3, rows, extra)

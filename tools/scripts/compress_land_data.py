#!/usr/bin/env python3
"""Compress the map model section of a land data (map_data_*.bin) file.

A land data file is a 16-byte header of four little-endian u32 section sizes
(terrain attributes, map props, map model, BDHC) followed by the sections in
that order. This tool replaces the map model section (an NSBMD, magic "BMD0")
with an LZ10 stream as read by MI_UncompressLZ8, and rewrites the model size in
the header to the on-disk (compressed, 4-byte padded) size. All other sections
are copied unchanged, so sequential readers that skip the model section by its
header size keep working.

The game decompresses the model in place inside its fixed-size model buffer:
the compressed stream is read into the tail of the buffer and decompressed to
the start of it (see LandData_BeginMapModelRead in src/overlay005/land_data.c).
That is only safe if the decompressor's writes never overtake its reads, so
this tool simulates the decompression and keeps the model uncompressed when the
buffer would be too small, or when compression would not save space. The game
tells the two apart by the "BMD0" magic.

Usage: compress_land_data.py INPUT OUTPUT [--buffer-size N]
"""

from __future__ import annotations

import argparse
import struct
import sys

LAND_DATA_HEADER_SIZE = 16
MAP_MODEL_SECTION = 2
MAP_MODEL_MAGIC = b"BMD0"

# Must match MAP_MODEL_FILE_SIZE in include/overlay005/loaded_map_buffers.h.
DEFAULT_MAP_MODEL_BUFFER_SIZE = 0xF000

LZ10_MIN_MATCH = 3
LZ10_MAX_MATCH = 18
LZ10_WINDOW = 4096
LZ10_MAX_CHAIN = 256


def lz10_compress(data: bytes) -> bytes:
    """Greedy LZ10 encoder with one-step lazy matching, 4-byte padded."""
    n = len(data)
    if n >= 1 << 24:
        raise ValueError("LZ10 input too large")

    heads = {}

    def insert(p):
        if p + LZ10_MIN_MATCH <= n:
            heads.setdefault(data[p:p + LZ10_MIN_MATCH], []).append(p)

    def find(p):
        if p + LZ10_MIN_MATCH > n:
            return 0, 0
        chain = heads.get(data[p:p + LZ10_MIN_MATCH])
        if not chain:
            return 0, 0
        limit = min(LZ10_MAX_MATCH, n - p)
        best_len = 0
        best_disp = 0
        for k in range(len(chain) - 1, max(-1, len(chain) - 1 - LZ10_MAX_CHAIN), -1):
            cand = chain[k]
            disp = p - cand
            if disp > LZ10_WINDOW:
                break
            length = LZ10_MIN_MATCH
            while length < limit and data[cand + length] == data[p + length]:
                length += 1
            if length > best_len:
                best_len = length
                best_disp = disp
                if length == limit:
                    break
        return best_len, best_disp

    tokens = []
    pos = 0
    inserted = 0
    while pos < n:
        while inserted < pos:
            insert(inserted)
            inserted += 1
        length, disp = find(pos)
        if length >= LZ10_MIN_MATCH and length < LZ10_MAX_MATCH and pos + 1 < n:
            insert(pos)
            inserted = pos + 1
            next_length, _ = find(pos + 1)
            if next_length > length:
                tokens.append((0, data[pos]))
                pos += 1
                continue
        if length >= LZ10_MIN_MATCH:
            tokens.append((length, disp))
            pos += length
        else:
            tokens.append((0, data[pos]))
            pos += 1

    out = bytearray((0x10 | (n << 8)).to_bytes(4, "little"))
    for i in range(0, len(tokens), 8):
        flag_index = len(out)
        out.append(0)
        flags = 0
        for bit, (length, value) in enumerate(tokens[i:i + 8]):
            if length:
                flags |= 0x80 >> bit
                d = value - 1
                out.append(((length - LZ10_MIN_MATCH) << 4) | (d >> 8))
                out.append(d & 0xFF)
            else:
                out.append(value)
        out[flag_index] = flags

    while len(out) % 4:
        out.append(0)

    return bytes(out)


def lz10_decompress_in_place_margin(src: bytes) -> tuple[bytes, int]:
    """Decompress src the way MI_UncompressLZ8 does and return the output plus
    the minimum offset the stream must start at, relative to the output start,
    for an overlapping in-place decompression to be safe.

    MI_UncompressLZ8 reads a whole token before writing any of its bytes, so a
    token that ends at input offset r and writes output bytes [o, o + len) is
    safe iff o + len <= start + r, i.e. start >= o + len - r.
    """
    header = int.from_bytes(src[0:4], "little")
    if header & 0xFF != 0x10:
        raise ValueError("not LZ10")

    size = header >> 8
    out = bytearray()
    i = 4
    margin = 0

    while len(out) < size:
        flags = src[i]
        i += 1

        for bit in range(8):
            if len(out) >= size:
                break

            if flags & (0x80 >> bit):
                b0, b1 = src[i], src[i + 1]
                i += 2
                length = (b0 >> 4) + LZ10_MIN_MATCH
                disp = (((b0 & 0xF) << 8) | b1) + 1
                if disp > len(out):
                    raise ValueError("LZ10 back-reference before start of output")
                for _ in range(length):
                    out.append(out[-disp])
            else:
                out.append(src[i])
                i += 1

            margin = max(margin, len(out) - i)

    if len(out) != size:
        raise ValueError("LZ10 stream overran its declared size")

    return bytes(out), margin


def compress_land_data(data: bytes, buffer_size: int) -> tuple[bytes, bool]:
    if len(data) < LAND_DATA_HEADER_SIZE:
        raise ValueError("land data file is too small")

    sizes = list(struct.unpack_from("<4I", data, 0))
    if LAND_DATA_HEADER_SIZE + sum(sizes) != len(data):
        raise ValueError(f"section sizes {sizes} do not add up to the file size {len(data)}")

    model_start = LAND_DATA_HEADER_SIZE + sizes[0] + sizes[1]
    model_end = model_start + sizes[MAP_MODEL_SECTION]
    model = data[model_start:model_end]

    if model[:4] != MAP_MODEL_MAGIC:
        raise ValueError(f"map model section does not start with {MAP_MODEL_MAGIC!r}")

    if len(model) > buffer_size:
        raise ValueError(f"map model is {len(model):#x} bytes, larger than the {buffer_size:#x}-byte model buffer")

    compressed = lz10_compress(model)
    decompressed, margin = lz10_decompress_in_place_margin(compressed)
    if decompressed != model:
        raise AssertionError("LZ10 round trip mismatch")

    # The game reads the compressed stream so that it ends at the end of the
    # model buffer, then decompresses it to the start of the buffer.
    stream_start = buffer_size - len(compressed)
    if len(compressed) >= len(model) or stream_start < margin:
        return data, False

    sizes[MAP_MODEL_SECTION] = len(compressed)
    out = struct.pack("<4I", *sizes) + data[LAND_DATA_HEADER_SIZE:model_start] + compressed + data[model_end:]

    return out, True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--buffer-size", type=lambda s: int(s, 0), default=DEFAULT_MAP_MODEL_BUFFER_SIZE)
    args = parser.parse_args()

    with open(args.input, "rb") as f:
        data = f.read()

    try:
        out, _ = compress_land_data(data, args.buffer_size)
    except (ValueError, AssertionError) as e:
        print(f"{args.input}: {e}", file=sys.stderr)
        return 1

    with open(args.output, "wb") as f:
        f.write(out)

    return 0


if __name__ == "__main__":
    sys.exit(main())

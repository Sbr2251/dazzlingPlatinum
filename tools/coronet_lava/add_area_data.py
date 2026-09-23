"""Adds area data entry 0x4B (Mt. Coronet 1F South lava) to area_data.narc. See docs/coronet_1f_lava/PLAN.md, Step 3.

Usage: python3 tools/coronet_lava/add_area_data.py [--light N]
  Entry 0x4B = the stock Mt. Coronet entry 0x45 with texture set 74 and the given area light (default 2).
  Re-running rewrites entry 0x4B in place, so the light can be changed later.

area_data.narc: NARC header, BTAF (start/end offset per file), BTNF (no names), GMIF (packed 8-byte files).
Each file is u16 mapPropArchivesID, u16 mapTextureArchiveID, u16 dummy, u16 areaLightArchiveID.
"""
import argparse
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
NARC = os.path.join(HERE, "..", "..", "res/prebuilt/fielddata/areadata/area_data.narc")

BASE_ENTRY = 0x45
LAVA_ENTRY = 0x4B
LAVA_TEXTURE_SET = 74


def read_sections(d):
    assert d[:4] == b"NARC"
    hdr_size, n_sections = struct.unpack_from("<HH", d, 12)
    sections, o = {}, hdr_size
    for _ in range(n_sections):
        magic, size = d[o:o + 4], struct.unpack_from("<I", d, o + 4)[0]
        sections[magic] = d[o:o + size]
        o += size
    return d[:hdr_size], sections


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--light", type=int, default=2)
    args = ap.parse_args()

    d = open(NARC, "rb").read()
    header, s = read_sections(d)
    btaf, btnf, gmif = s[b"BTAF"], s[b"BTNF"], s[b"GMIF"]
    n = struct.unpack_from("<H", btaf, 8)[0]
    files = []
    for i in range(n):
        start, end = struct.unpack_from("<II", btaf, 12 + 8 * i)
        files.append(gmif[8 + start:8 + end])
    assert n in (LAVA_ENTRY, LAVA_ENTRY + 1), f"expected {LAVA_ENTRY} or {LAVA_ENTRY + 1} files, found {n}"

    props, _, dummy, _ = struct.unpack("<4H", files[BASE_ENTRY])
    entry = struct.pack("<4H", props, LAVA_TEXTURE_SET, dummy, args.light)
    files = files[:LAVA_ENTRY] + [entry]

    offsets, blob = [], b""
    for f in files:
        offsets.append((len(blob), len(blob) + len(f)))
        blob += f
    blob += b"\xff" * (-len(blob) % 4)

    btaf = b"BTAF" + struct.pack("<IHH", 12 + 8 * len(files), len(files), 0)
    btaf += b"".join(struct.pack("<II", a, b) for a, b in offsets)
    gmif = b"GMIF" + struct.pack("<I", 8 + len(blob)) + blob
    body = btaf + btnf + gmif
    header = bytearray(header)
    struct.pack_into("<I", header, 8, len(header) + len(body))
    with open(NARC, "wb") as f:
        f.write(bytes(header) + body)
    print(f"area data 0x{LAVA_ENTRY:02X} = {entry.hex(' ')} ({len(files)} files)")


if __name__ == "__main__":
    main()

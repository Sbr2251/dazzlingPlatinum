"""Adds area data entry 0x4B (Mt. Coronet 1F South lava) to area_data.narc. See docs/coronet_1f_lava/PLAN.md, Step 3.

Usage: python3 tools/coronet_lava/add_area_data.py [--light N]
  Entry 0x4B = the stock Mt. Coronet entry 0x45 with texture set 74 and the given area light
  (default: add_area_light.LAVA_LIGHT). Re-running rewrites entry 0x4B in place.

Each file is u16 mapPropArchivesID, u16 mapTextureArchiveID, u16 dummy, u16 areaLightArchiveID.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import add_area_light  # noqa: E402
import narc  # noqa: E402

NARC = os.path.join(HERE, "..", "..", "res/prebuilt/fielddata/areadata/area_data.narc")

BASE_ENTRY = 0x45
LAVA_ENTRY = 0x4B
LAVA_TEXTURE_SET = 74


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--light", type=int, default=add_area_light.LAVA_LIGHT)
    args = ap.parse_args()

    header, btnf, files = narc.read_files(NARC)
    assert len(files) in (LAVA_ENTRY, LAVA_ENTRY + 1), f"expected {LAVA_ENTRY} or {LAVA_ENTRY + 1} files"

    props, _, dummy, _ = struct.unpack("<4H", files[BASE_ENTRY])
    entry = struct.pack("<4H", props, LAVA_TEXTURE_SET, dummy, args.light)
    files = files[:LAVA_ENTRY] + [entry]
    narc.write_files(NARC, header, btnf, files)
    print(f"area data 0x{LAVA_ENTRY:02X} = {entry.hex(' ')} ({len(files)} files)")


if __name__ == "__main__":
    main()

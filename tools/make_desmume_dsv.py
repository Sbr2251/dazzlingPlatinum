#!/usr/bin/env python3
"""Wrap a raw Nintendo DS save in DeSmuME's DSV footer format."""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

FOOTER_TEXT = b"|<--Snip above here to create a raw sav by excluding this DeSmuME savedata footer:"
COOKIE = b"|-DESMUME SAVE-|"
FLASH_4MBIT_TYPE = 6
FLASH_ADDR_SIZE = 3
FLASH_4MBIT_SIZE = 512 * 1024


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_save", type=Path)
    parser.add_argument("output_dsv", type=Path)
    args = parser.parse_args()

    data = args.raw_save.read_bytes()
    if len(data) != FLASH_4MBIT_SIZE:
        raise SystemExit(f"expected {FLASH_4MBIT_SIZE} bytes, got {len(data)}")

    fields = struct.pack(
        "<6I",
        len(data),
        len(data),
        FLASH_4MBIT_TYPE,
        FLASH_ADDR_SIZE,
        len(data),
        0,
    )
    args.output_dsv.parent.mkdir(parents=True, exist_ok=True)
    args.output_dsv.write_bytes(data + FOOTER_TEXT + fields + COOKIE)
    print(f"wrote {args.output_dsv} ({args.output_dsv.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

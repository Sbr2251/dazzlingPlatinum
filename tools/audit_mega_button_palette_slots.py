#!/usr/bin/env python3
"""Audit palette-bank use in decoded 32x32 Nintendo DS NSCR tilemaps."""

from __future__ import annotations

import argparse
import struct
from collections import Counter
from pathlib import Path


def read_entries(path: Path) -> list[int]:
    data = path.read_bytes()
    if data[:4] != b"RCSN":
        raise ValueError(f"{path}: not an NSCR file")
    if data[0x10:0x14] != b"NRCS":
        raise ValueError(f"{path}: missing SCRN section")
    payload_size = struct.unpack_from("<I", data, 0x20)[0]
    payload = data[0x24 : 0x24 + payload_size]
    if len(payload) != payload_size or payload_size % 2:
        raise ValueError(f"{path}: invalid tilemap payload")
    return list(struct.unpack(f"<{payload_size // 2}H", payload))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    for path in args.paths:
        entries = read_entries(path)
        if len(entries) != 32 * 32:
            raise ValueError(f"{path}: expected 1024 entries, got {len(entries)}")

        all_counts = Counter(entry >> 12 for entry in entries)
        mega_entries = [entries[row * 32 + col] for row in range(0x13, 0x18) for col in range(1, 15)]
        mega_counts = Counter(entry >> 12 for entry in mega_entries)
        border_entries = [entries[row * 32 + col] for row in range(0x13, 0x18) for col in (13, 14)]
        border_counts = Counter(entry >> 12 for entry in border_entries)
        unused = [bank for bank in range(16) if bank not in all_counts]

        print(path.name)
        print("  all:", " ".join(f"{bank}:{all_counts[bank]}" for bank in sorted(all_counts)))
        print("  mega_rect:", " ".join(f"{bank}:{mega_counts[bank]}" for bank in sorted(mega_counts)))
        print("  right_border:", " ".join(f"{bank}:{border_counts[bank]}" for bank in sorted(border_counts)))
        print("  unused:", ",".join(map(str, unused)) or "none")


if __name__ == "__main__":
    main()

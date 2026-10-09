#!/usr/bin/env python3
"""Generate the five Arc 1 field sprite sheets (final art).

    python3 tools/arc1_sprites/gen_arc1_sprites.py           # write the 5 PNGs
    python3 tools/arc1_sprites/gen_arc1_sprites.py --check   # fail if a PNG is out of date

Pure Python (no PIL). Reads the stock walker mmodel members and the stock totem
Hitmonlee PNGs, applies the designs in this directory and writes 4bpp indexed PNGs to
res/field/objects/arc1/, the only files the Art stream owns in the build. The build
turns them into mmodel members 479-483 (tools/integrate_arc1_field_sprites.py).

The design sheet (docs/story/art/arc1_sprites_sheet.png) needs PIL:
    ~/.venvs/desmume/bin/python tools/arc1_sprites/design_sheet.py
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from effects import HITMONLEE_PALETTE, RIFT_PALETTE, hitmonlee_frames, rift_frames  # noqa: E402
from eclipse_grunts import GRUNT_F, GRUNT_M  # noqa: E402
from pixelkit import REPO_ROOT, write_sheet  # noqa: E402
from saros import SAROS  # noqa: E402
from walker import compose  # noqa: E402

SHEET_DIR = REPO_ROOT / "res/field/objects/arc1"


def outputs():
    """(constant, sheet file name, frames, columns, palette) for every sprite."""
    return [
        ("OBJ_EVENT_GFX_SAROS", "saros.png", compose(SAROS), 4, SAROS.palette),
        ("OBJ_EVENT_GFX_ECLIPSE_GRUNT_M", "eclipse_grunt_m.png", compose(GRUNT_M), 4, GRUNT_M.palette),
        ("OBJ_EVENT_GFX_ECLIPSE_GRUNT_F", "eclipse_grunt_f.png", compose(GRUNT_F), 4, GRUNT_F.palette),
        ("OBJ_EVENT_GFX_ARC1_RIFT", "arc1_rift.png", rift_frames(), 2, RIFT_PALETTE),
        ("OBJ_EVENT_GFX_TOTEM_HITMONLEE_VIOLET", "totem_hitmonlee_violet.png", hitmonlee_frames(), 2, HITMONLEE_PALETTE),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="compare against the committed PNGs instead of writing")
    parser.add_argument("--out", type=Path, default=SHEET_DIR, help="output directory (default: the repo sheets)")
    args = parser.parse_args()

    stale = []
    for constant, name, frames, columns, palette in outputs():
        if args.check:
            with tempfile.TemporaryDirectory() as tmp:
                fresh = Path(tmp) / name
                write_sheet(fresh, frames, columns, palette)
                if not (args.out / name).exists() or fresh.read_bytes() != (args.out / name).read_bytes():
                    stale.append(name)
        else:
            write_sheet(args.out / name, frames, columns, palette)
            print(f"wrote {args.out / name} ({constant})")
    if stale:
        print("out of date: " + ", ".join(stale), file=sys.stderr)
        return 1
    if args.check:
        print("all Arc 1 sprite sheets match the generator")
    return 0


if __name__ == "__main__":
    sys.exit(main())

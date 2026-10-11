#!/usr/bin/env python3
"""Generate the seven Arc 2 field sprite sheets (res/field/objects/arc2/*.png).

    python3 tools/arc2_sprites/gen_arc2_sprites.py           # write the 7 PNGs
    python3 tools/arc2_sprites/gen_arc2_sprites.py --check   # fail if a PNG is out of date

Pure Python (no PIL), reusing the Arc 1 helpers in tools/arc1_sprites/. Walkers are edits of stock
Platinum walkers (Indra: Cynthia's body; Kahn: the Sailor; both Lookers: Looker); the three idle2
objects are drawn from scratch. The build turns the sheets into mmodel members 484-490
(tools/integrate_arc2_field_sprites.py). Design notes: docs/story/art/arc2/README.md.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common import SHEET_DIR, compose, write_sheet  # noqa: E402
from indra import INDRA  # noqa: E402
from kahn import KAHN  # noqa: E402
from looker import LOOKER_JANITOR, LOOKER_NEWSPAPER  # noqa: E402
from objects import (  # noqa: E402
    CRATE_PALETTE,
    FRAME_PALETTE,
    RIFT_PALETTE,
    crate_frames,
    frame_frames,
    rift_frames,
)


def outputs():
    """(constant, sheet file name, frames, columns, palette) for every sprite."""
    return [
        ("OBJ_EVENT_GFX_INDRA", "indra.png", compose(INDRA), 4, INDRA.palette),
        ("OBJ_EVENT_GFX_KAHN", "kahn.png", compose(KAHN), 4, KAHN.palette),
        ("OBJ_EVENT_GFX_LOOKER_JANITOR", "looker_janitor.png", compose(LOOKER_JANITOR), 4, LOOKER_JANITOR.palette),
        ("OBJ_EVENT_GFX_LOOKER_NEWSPAPER", "looker_newspaper.png", compose(LOOKER_NEWSPAPER), 4,
         LOOKER_NEWSPAPER.palette),
        ("OBJ_EVENT_GFX_ECLIPSE_CRATE", "eclipse_crate.png", crate_frames(), 2, CRATE_PALETTE),
        ("OBJ_EVENT_GFX_SHARD_FRAME", "shard_frame.png", frame_frames(), 2, FRAME_PALETTE),
        ("OBJ_EVENT_GFX_RIFT_ARC2", "rift_arc2.png", rift_frames(), 2, RIFT_PALETTE),
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
        print("all Arc 2 sprite sheets match the generator")
    return 0


if __name__ == "__main__":
    sys.exit(main())

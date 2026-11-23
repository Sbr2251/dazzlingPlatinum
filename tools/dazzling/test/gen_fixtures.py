#!/usr/bin/env python3
"""Reproduce the small, self-contained field save used by headless tests.

The checked-in fixture is an ordinary 512 KiB in-game save (Jubilife, three
low-level party members).  This script normalizes it through save_tool and
adds only test consumables.  To rebuild from the original headless-created
save, pass it with ``--source``; with no arguments the checked-in fixture is
validated and regenerated in place.
"""
import argparse
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "dazzling"))
import save_tool  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "fixture_field.sav")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=FIXTURE,
                        help="clean in-game 512 KiB save (default: existing fixture)")
    parser.add_argument("--output", default=FIXTURE)
    args = parser.parse_args()
    if not os.path.exists(args.source):
        parser.error("source save does not exist; create an in-game save or pass --source")

    data = save_tool.load(args.source)
    valid = save_tool.regions(data)
    if len(valid) != 2 or not all(ok for _, _, ok in valid):
        parser.error("source does not contain two valid signed save regions")
    for base, _, _ in valid:
        _, count = save_tool.find_party(data, base)
        if count < 3:
            parser.error("source needs at least three party members")

    save_tool.edit(data, lead=None, held=[], give=[
        (save_tool.item_id("ITEM_POKE_BALL"), 20),
        (save_tool.item_id("ITEM_POTION"), 10),
    ])
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "wb") as out:
        out.write(data)
    digest = hashlib.sha256(data).hexdigest()
    print(f"wrote {args.output} ({len(data)} bytes, sha256={digest})")
    save_tool.info(data)


if __name__ == "__main__":
    main()

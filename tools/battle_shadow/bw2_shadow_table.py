#!/usr/bin/env python3
"""Checks sShadowAdjust (src/battle/battle_stage_shadow.c) against BW2's shadow adjust table.

BW2's table is data_ov168_021f3414 in pokebw2's src/ov168/btlv_mcss.c (read-only reference, default
/data/repos/pokebw2). Its species are national dex numbers written as SPECIES_ constants; ours keep the
same constant names for the same national dex species (generated/species.txt; the Gen 5 species this
hack added sit after Arceus, but under their own names), so an entry maps by name. BW2 entries for
species we lack are reported and must be absent from ours.

    python3 tools/battle_shadow/bw2_shadow_table.py [--pokebw2 DIR]
Exit status 1 on any difference.
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENTRY = re.compile(r"\{ SPECIES_(\w+), (\d), (\d), (-?0x[0-9a-f]+), (-?0x[0-9a-f]+), (0x[0-9a-f]+) \}")


def entries(text):
    return [(m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4), 16), int(m.group(5), 16), int(m.group(6), 16))
            for m in ENTRY.finditer(text)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pokebw2", default="/data/repos/pokebw2")
    args = ap.parse_args()
    src = (pathlib.Path(args.pokebw2) / "src/ov168/btlv_mcss.c").read_text()
    start = src.index("data_ov168_021f3414[] = {")
    bw2 = entries(src[start:src.index("};", start)])
    ours_src = (ROOT / "src/battle/battle_stage_shadow.c").read_text()
    start = ours_src.index("sShadowAdjust[] = {")
    ours = entries(ours_src[start:ours_src.index("};", start)])
    species = {line.strip()[len("SPECIES_"):] for line in (ROOT / "generated/species.txt").read_text().split() if line.startswith("SPECIES_")}
    want = [e for e in bw2 if e[0] in species]
    missing = sorted({e[0] for e in bw2 if e[0] not in species})
    ok = want == ours
    print(f"BW2 entries: {len(bw2)}; for species in this game: {len(want)}; ours: {len(ours)}")
    print(f"BW2 species not in this game (left out): {', '.join(missing)}")
    for e in want:
        if e not in ours:
            print("missing or different in ours:", e)
    for e in ours:
        if e not in want:
            print("not BW2's:", e)
    print("OK" if ok else "DIFFERENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

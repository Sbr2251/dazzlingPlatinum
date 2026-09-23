"""Adds area light 4 (warm magma cave light) to arealight.narc. See docs/coronet_1f_lava/PLAN.md, Step 5.

Usage: python3 tools/coronet_lava/add_area_light.py
  Light 4 = stock cave light 2 with warmer colours; directions are unchanged. Re-running rewrites it in place.
  AREA_LIGHT_FILE_COUNT in src/overlay005/area_light.c must cover it.

Each light file is text: blocks of "endTime," then 4 lines "valid,r,g,b,x,y,z," (one per GX light) and
4 lines "r,g,b," (diffuse, ambient, specular, emission), colours in 5-bit units, ending with "EOF".
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import narc  # noqa: E402

NARC = os.path.join(HERE, "..", "..", "res/prebuilt/data/arealight.narc")

BASE_LIGHT = 2
LAVA_LIGHT = 4

# block line index -> replacement; 1-4 are the GX lights (only the colour is replaced, direction kept),
# 5-8 are diffuse, ambient, specular, emission
LIGHT_COLOURS = {1: (10, 7, 8)}  # key light 0: blue (7,7,12) -> dim ember
MATERIAL_COLOURS = {
    5: (16, 14, 14),  # diffuse (14,14,16): about +15% R, -10% B
    6: (10, 6, 6),    # ambient (10,10,10)
    8: (9, 7, 7),     # emission (8,8,11)
}


def warm(text):
    out, pos = [], 0
    for line in text.split("\r\n"):
        if line == "" or line == "EOF":
            pos = 0
        else:
            f = line.rstrip(",").split(",")
            if pos in LIGHT_COLOURS and f[0] == "1":
                f[1:4] = map(str, LIGHT_COLOURS[pos])
            elif pos in MATERIAL_COLOURS:
                f = list(map(str, MATERIAL_COLOURS[pos]))
            line = ",".join(f) + ","
            pos += 1
        out.append(line)
    return "\r\n".join(out)


def main():
    header, btnf, files = narc.read_files(NARC)
    assert len(files) in (LAVA_LIGHT, LAVA_LIGHT + 1), f"expected {LAVA_LIGHT} or {LAVA_LIGHT + 1} files"
    text = warm(files[BASE_LIGHT].decode("ascii"))
    files = files[:LAVA_LIGHT] + [text.encode("ascii")]
    narc.write_files(NARC, header, btnf, files)
    print(f"area light {LAVA_LIGHT} written ({len(files)} files)")


if __name__ == "__main__":
    main()

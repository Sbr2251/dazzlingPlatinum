#!/usr/bin/env python3
"""ASCII tile classes of a rect: '.' flat ground h1, digit = other flat height, g tall grass, # blocked, ? slope /
bridge / other, event letters on top.   show.py x0 z0 x1 z1"""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_art as BA  # noqa: E402
import common as R  # noqa: E402

S = BA.Stock()
mk = R.event_marks(S.ev)
x0, z0, x1, z1 = map(int, sys.argv[1:5])
print("     " + "".join(str((x // 10) % 10) for x in range(x0, x1 + 1)))
print("     " + "".join(str(x % 10) for x in range(x0, x1 + 1)))
for z in range(z0, z1 + 1):
    r = ""
    for x in range(x0, x1 + 1):
        t = (x, z)
        p = S.perm[t]
        if t in mk:
            c = mk[t]
        elif p & 0x8000:
            c = "#"
        else:
            g = S.ground(t)
            if g is not None:
                c = "." if g == 1 else str(g)
            elif S.ground(t, (2,)) is not None:
                c = "g"
            else:
                c = "?"
        r += c
    print(f"{z:4d} " + r)

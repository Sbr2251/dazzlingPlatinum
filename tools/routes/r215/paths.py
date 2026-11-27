#!/usr/bin/env python3
"""Route 215 walkability graph: 4-neighbour moves over unblocked tiles plus one-way ledge jumps (JUMP_* tiles are
blocked; walking onto one in its direction lands two tiles on). Used for the reachability checks and the main path.

  python3 tools/routes/r215/paths.py      ASCII of the shortest west-entrance -> gate path
"""
import os
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as R  # noqa: E402

JUMP = {0x38: (1, 0), 0x39: (-1, 0), 0x3A: (0, -1), 0x3B: (0, 1)}
WEST_ENTRY = [(576, z) for z in range(592, 602)]
GATE = [(670, 598), (670, 599)]


def walkable(perm, t):
    return t in perm and not perm[t] & 0x8000


def neighbours(perm, t):
    x, z = t
    for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n = (x + d[0], z + d[1])
        if walkable(perm, n):
            yield n
        elif n in perm and (perm[n] & 0xFF) in JUMP and JUMP[perm[n] & 0xFF] == d:
            m = (x + 2 * d[0], z + 2 * d[1])
            if walkable(perm, m):
                yield m


def reach(perm, starts=WEST_ENTRY):
    seen = {s for s in starts if walkable(perm, s)}
    q = deque(seen)
    prev = {}
    while q:
        t = q.popleft()
        for n in neighbours(perm, t):
            if n not in seen:
                seen.add(n)
                prev[n] = t
                q.append(n)
    return seen, prev


def path_to(prev, goal):
    out = [goal]
    while out[-1] in prev:
        out.append(prev[out[-1]])
    return out[::-1]


if __name__ == "__main__":
    st = R.stock_chunks()
    perm = R.merged_permissions(st)
    seen, prev = reach(perm)
    p = set(path_to(prev, GATE[0]))
    ev = R.event_marks(R.stock_events())
    print("reachable", len(seen), "walkable", sum(1 for t in perm if walkable(perm, t)))
    print("      " + "".join(str((x // 10) % 10) for x in R.XS))
    print("      " + "".join(str(x % 10) for x in R.XS))
    for z in R.ZS:
        print(f"{z:4d}  " + "".join(ev.get((x, z)) or ("*" if (x, z) in p else "," if (x, z) in seen else
                                                       "." if walkable(perm, (x, z)) else "#") for x in R.XS))

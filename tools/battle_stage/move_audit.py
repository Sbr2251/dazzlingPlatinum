#!/usr/bin/env python3
"""Static move animation audit for the 3D battle stage (chunk 5).

WIP skeleton: C helpers only.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANIM_SRC = ROOT / "src" / "battle_anim"

FUNC_DEF_RE = re.compile(
    r"^(?:static\s+)?(?:inline\s+)?(?:const\s+)?[A-Za-z_][\w \t\*]*?\b([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*\{",
    re.M,
)


def strip_c_comments(text):
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def parse_c_functions(path):
    """Return {name: (body_text, line)} for every function defined in path."""
    text = strip_c_comments(path.read_text(encoding="utf-8", errors="replace"))
    funcs = {}
    for m in FUNC_DEF_RE.finditer(text):
        name = m.group(1)
        if name in ("if", "for", "while", "switch", "return", "sizeof"):
            continue
        start = m.end() - 1
        depth = 0
        i = start
        while i < len(text):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = text[start:i + 1]
        line = text.count("\n", 0, m.start()) + 1
        funcs[name] = (body, path.name, line)
    return funcs


def load_anim_c():
    funcs = {}
    for path in sorted(ANIM_SRC.glob("*.c")):
        funcs.update(parse_c_functions(path))
    return funcs


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--show-func":
        funcs = load_anim_c()
        for name in sys.argv[2:]:
            body, fname, line = funcs[name]
            print(f"== {name} ({fname}:{line})")
            print(body)

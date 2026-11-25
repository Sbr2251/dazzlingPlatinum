#!/usr/bin/env python3
"""Pixel width of a text line in the message font (res/fonts/font_message.json, glyph index = char code - 1), the
same measure the story workstream used for the 197 px / 2-lines-per-box rule (screenplay.md "How to read this file").

    python3 tools/solaceon_ruins/textwidth.py "Some line"    # prints the width
    python3 tools/solaceon_ruins/textwidth.py --bank res/text/solaceon_ruins_room_7.json [--prefix ID_PREFIX]
        checks every line of every message (or only ids starting with the prefix): ASCII, <= 197 px, <= 2 lines
        per box. Control codes ({STRVAR_1 3, 0, 0} = the player's name, counted as 7 W's = 7 chars of max width).
"""
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
MAX_W = 197


def _charmap():
    cm = {}
    with open(os.path.join(ROOT, "tools", "msgenc", "charmap.txt"), encoding="utf-8") as f:
        for ln in f:
            ln = ln.rstrip("\n")
            if "=" in ln:
                code, ch = ln.split("=", 1)
                if len(ch) == 1 and ch not in cm:
                    try:
                        cm[ch] = int(code, 16)
                    except ValueError:
                        pass
    return cm


CHARMAP = _charmap()
with open(os.path.join(ROOT, "res", "fonts", "font_message.json")) as _f:
    GLYPH_W = json.load(_f)["glyphWidths"]
NAME_W = 7 * GLYPH_W[CHARMAP["W"] - 1]     # a 7-letter player name, widest letters (a worst case)


def width(s):
    s = s.rstrip("\n\r\f")
    w = 0
    for part in re.split(r"(\{[^}]*\})", s):
        if part.startswith("{"):
            if part.startswith("{STRVAR_1 3,"):
                w += NAME_W
            continue
        w += sum(GLYPH_W[CHARMAP[c] - 1] for c in part)
    return w


def check_bank(path, prefix=""):
    problems = []
    for m in json.load(open(path))["messages"]:
        if not m["id"].startswith(prefix):
            continue
        lines = m["en_US"] if isinstance(m["en_US"], list) else [m["en_US"]]
        in_box = 0
        for ln in lines:
            if any(ord(c) > 126 for c in ln):
                problems.append(f"{m['id']}: non-ASCII {ln!r}")
            w = width(ln)
            if w > MAX_W:
                problems.append(f"{m['id']}: {w} px > {MAX_W}: {ln!r}")
            in_box += 1
            if in_box > 2:
                problems.append(f"{m['id']}: more than 2 lines in one box at {ln!r}")
            if ln.endswith(("\r", "\f")):
                in_box = 0
    return problems


if __name__ == "__main__":
    if sys.argv[1:2] == ["--bank"]:
        prefix = sys.argv[sys.argv.index("--prefix") + 1] if "--prefix" in sys.argv else ""
        probs = check_bank(sys.argv[2], prefix)
        print("\n".join(probs) or "ok")
        sys.exit(1 if probs else 0)
    for a in sys.argv[1:]:
        print(width(a), a)

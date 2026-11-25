#!/usr/bin/env python3
"""Writes the Solaceon town-scripts text (res/text/solaceon_town.json, res/text/solaceon_sanctuary.json) from
docs/solaceon_redesign/screenplay.md, verbatim. Standard library only.

    python3 tools/solaceon_town/screenplay_text.py            # dry run: list the messages, run the checks
    python3 tools/solaceon_town/screenplay_text.py --write    # (re)write the generated entries

Screenplay rules (screenplay.md "How to read this file"): every line of a ```text fence is one line of the text box;
consecutive lines are one box (at most 2 lines); `--` is a box break (\\r); a blank line starts a new message. Each
generated message is one bank entry: lines in a box end with \\n, boxes end with \\r, and the last line has no
terminator (the scripts follow every Message with WaitABPadPress).

Ids: SolaceonTown_Text_Sol<Role><Band>[_<n>] and SolaceonSanctuary_Text_<Role><Band>[_<n>], signs
..._Sol<Sign><Bands>, scenes ..._Sol<Scene>_<n>. Generated entries are appended after the bank's existing entries;
re-running replaces them in place (same order), so stock and Arc 2 entries and their indices never move.

Checks: ASCII only, every line at most 197 px in res/fonts/font_message.json widths (the 27-tile text box), at most
2 lines per box, every id used by the town and Sanctuary scripts exists.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SCREENPLAY = os.path.join(ROOT, "docs", "solaceon_redesign", "screenplay.md")
TOWN_BANK = os.path.join(ROOT, "res", "text", "solaceon_town.json")
SANCT_BANK = os.path.join(ROOT, "res", "text", "solaceon_sanctuary.json")
TOWN_SCRIPTS = [os.path.join(ROOT, "res", "field", "maps", "solaceon_town", f) for f in ("scripts.s",)]
SANCT_SCRIPTS = [os.path.join(ROOT, "res", "field", "maps", "solaceon_sanctuary", f) for f in ("scripts.s",)]
MAX_PX = 197
PLAYER = "{STRVAR_1 3, 0, 0}"   # BufferPlayerName 0


def fence_blocks():
    """-> [(line, part, band, role, body lines)] for every ```text fence."""
    lines = open(SCREENPLAY, encoding="utf-8").read().split("\n")
    out, part, band, role, i = [], None, None, None, 0
    while i < len(lines):
        l = lines[i]
        m = re.match(r"^# (Part \d)", l)
        if m:
            part, band = m.group(1), None
        m = re.match(r"^## (Band [A-Z]|3\.4a part \d)", l)
        if m:
            band = m.group(1)
        m = re.match(r"^`([A-Z_0-9]+)`.*:\s*$", l) or re.match(r"^\*\*(.+?)\*\*", l)
        if m:
            role = m.group(1)
        if l.strip() == "```text":
            j = i + 1
            while lines[j].strip() != "```":
                j += 1
            out.append((i + 1, part, band, role, lines[i + 1:j]))
            role, i = None, j
        i += 1
    return out


def messages(body):
    """Fence body -> [message]; message = [box]; box = [line]."""
    msgs, cur, box = [], [], []
    for l in body + [""]:
        if l == "":
            if box:
                cur.append(box)
                box = []
            if cur:
                msgs.append(cur)
                cur = []
        elif l == "--":
            if box:
                cur.append(box)
                box = []
        else:
            box.append(l)
    return msgs


def tagged(body):
    """A sign fence with [A] / [B C] / [Lectern, A B C] tag lines -> {tag: body}."""
    out, tag = {}, None
    for l in body:
        m = re.match(r"^\[(.+)\]$", l)
        if m:
            tag = m.group(1)
            out[tag] = []
        elif tag is not None:
            out[tag].append(l)
    return out


def camel(role):
    return "".join(w.capitalize() for w in role.split("_"))


def encode(msg):
    """[box] -> en_US list (lines \\n, boxes \\r, nothing after the last line)."""
    out = []
    for bi, box in enumerate(msg):
        for li, line in enumerate(box):
            line = line.replace("{PLAYER}", PLAYER)
            if li < len(box) - 1:
                out.append(line + "\n")
            elif bi < len(msg) - 1:
                out.append(line + "\r")
            else:
                out.append(line)
    return out


def build():
    """-> (town entries, sanctuary entries): ordered lists of (id, message)."""
    town, sanct = [], []
    blocks = fence_blocks()

    def add(dest, ident, msgs):
        if len(msgs) == 1:
            dest.append((ident, msgs[0]))
        else:
            for n, m in enumerate(msgs, 1):
                dest.append((f"{ident}_{n}", m))

    signs = {}
    scenes = {}
    for ln, part, band, role, body in blocks:
        if part == "Part 1":
            signs[role] = body
        elif part == "Part 2" and band and role and re.match(r"^[A-Z_]+$", role):
            b = band.split()[1]
            msgs = messages(body)
            # "stock msg 8 first" / "stock msg 7": the stock first message is reused, not duplicated
            if role in ("LANTERN_MAN", "SUNDAY_MAN") and b == "A":
                msgs = msgs[1:]
            add(town, f"SolaceonTown_Text_Sol{camel(role)}{b}", msgs)
        elif part == "Part 2" and band == "Band F" and role and role.startswith("Optional"):
            add(town, "SolaceonTown_Text_SolIndraF", messages(body))
        elif part == "Part 2" and band == "Band F" and role is None:
            add(town, "SolaceonTown_Text_SolWallTeoIndra", messages(body))
        elif part == "Part 3" and band is None:
            signs["interior"] = body
        elif part == "Part 3" and band and role:
            add(sanct, f"SolaceonSanctuary_Text_{camel(role)}{band.split()[1]}", messages(body))
        elif part == "Part 4" and band in ("3.4a part 1", "3.4a part 2", "3.4a part 7"):
            scenes.setdefault(band, []).append(messages(body))
        elif part == "Part 5" and role and ("SOL_07" in role or "SOL_08" in role):
            post = tagged(body)["TRMSG_POST_BATTLE"]
            add(town, "SolaceonTown_Text_SolFenceGrunt" + ("M" if "SOL_07" in role else "F") + "Post",
                messages(post))

    # Part 1 signs (the town sign is the stock ShowMapSign 12, unchanged)
    sign_ids = {
        "Sanctuary gate plaque": "GatePlaque", "Tent sign": "TentSign", "Excavation warning sign": "DigSign",
        "Kennel sign": "KennelSign", "Rowan banners": "TornBanner", "The wall banner": "WallBanner",
    }
    for name, ident in sign_ids.items():
        for tag, body in tagged(signs[name]).items():
            if tag.startswith("F: hidden"):
                continue
            suffix = "" if name == "Rowan banners" else tag.replace(" ", "")
            add(town, f"SolaceonTown_Text_Sol{ident}{suffix}", messages(body))
    add(town, "SolaceonTown_Text_SolHallDoorLocked", messages(signs["Sanctuary hall door"]))
    add(town, "SolaceonTown_Text_SolMemorialPlaque", messages(signs["Postgame memorial plaque"]))

    # scenes (part 1 briefing, part 2 the fence, part 7 the seizure; the item-get line is the stock common script's)
    add(town, "SolaceonTown_Text_SolBriefing", scenes["3.4a part 1"][0])
    add(town, "SolaceonTown_Text_SolFence", scenes["3.4a part 2"][0])
    add(town, "SolaceonTown_Text_SolFenceCyrus", scenes["3.4a part 2"][1])
    p7 = scenes["3.4a part 7"]
    assert p7[1][0][0][0].startswith("{PLAYER} received"), p7[1]
    add(town, "SolaceonTown_Text_SolSeizure", p7[0] + p7[2])

    # Part 3 signs inside the hall
    for tag, body in tagged(signs["interior"]).items():
        name, bands = tag.split(",", 1)
        bands = bands.split(":")[0].strip().replace(" ", "")
        ident = camel(re.sub(r"[^A-Za-z ]", "", name).strip().replace(" ", "_").upper())
        add(sanct, f"SolaceonSanctuary_Text_{ident}{bands}", messages(body))
    return town, sanct


def load_widths():
    fw = json.load(open(os.path.join(ROOT, "res", "fonts", "font_message.json")))["glyphWidths"]
    cmap = {}
    for l in open(os.path.join(ROOT, "tools", "msgenc", "charmap.txt"), encoding="utf-8"):
        l = l.split("//")[0].rstrip("\n")
        m = re.match(r"^\s*([0-9A-Fa-f]{4})=(.)$", l)
        if m:
            cmap.setdefault(m.group(2), int(m.group(1), 16))
    return lambda ch: fw[cmap[ch] - 1]


def line_px(line, width):
    line = line.replace(PLAYER, "MMMMMMM")   # a 7-letter name in the widest glyphs (the player's name buffer)
    return sum(width(c) for c in line)


def check(entries, width):
    problems = []
    for ident, msg in entries:
        for box in msg:
            if len(box) > 2:
                problems.append(f"{ident}: {len(box)} lines in one box")
            for line in box:
                if any(ord(c) > 126 or (ord(c) < 32) for c in line):
                    problems.append(f"{ident}: non-ASCII in {line!r}")
                px = line_px(line, width)
                if px > MAX_PX and PLAYER not in line:
                    problems.append(f"{ident}: {px} px > {MAX_PX}: {line!r}")
    return problems


def used_ids(paths, prefix):
    ids = set()
    for p in paths:
        if os.path.exists(p):
            ids |= set(re.findall(r"\b(" + prefix + r"\w+)", open(p).read()))
    return ids


def write_bank(path, entries):
    s = open(path, encoding="utf-8").read()
    d = json.loads(s)
    gen = {i for i, _ in entries}
    keep = [m for m in d["messages"] if m["id"] not in gen]
    d["messages"] = keep + [{"id": i, "en_US": encode(m)} for i, m in entries]
    out = json.dumps(d, indent=2, ensure_ascii=False) + "\n"
    if out != s:
        open(path, "w", encoding="utf-8").write(out)
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    town, sanct = build()
    width = load_widths()
    problems = check(town + sanct, width)
    for path, entries, scripts, prefix in ((TOWN_BANK, town, TOWN_SCRIPTS, "SolaceonTown_Text_"),
                                           (SANCT_BANK, sanct, SANCT_SCRIPTS, "SolaceonSanctuary_Text_")):
        have = {m["id"] for m in json.load(open(path))["messages"]} | {i for i, _ in entries}
        for ident in sorted(used_ids(scripts, prefix) - have):
            problems.append(f"{os.path.relpath(scripts[0], ROOT)} uses {ident}, which no bank entry defines")
    if a.verbose:
        for ident, msg in town + sanct:
            print(ident, json.dumps(encode(msg)))
    print(f"{len(town)} town messages, {len(sanct)} Sanctuary messages")
    for p in problems:
        print("FAIL", p)
    if problems:
        return 1
    if a.write:
        for path, entries in ((TOWN_BANK, town), (SANCT_BANK, sanct)):
            print(("wrote " if write_bank(path, entries) else "unchanged ") + os.path.relpath(path, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())

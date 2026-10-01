#!/usr/bin/env python3
"""Builds res/prebuilt/battle/graphic/mon_stream.narc: Gen 5 (Black/White) animated battle
sprites, streamed one 128x96 frame at a time into a small texture per battler
(docs/living_battle_stage/sprite_stream.md).

For each species it also rewrites res/pokemon/<species>/{male,female}_{front,back}.png and
normal.pal/shiny.pal from the same art, so the classic 80x80 sprite (other screens, and
battle draws that fall back to it) and the battler's palette slot match the stream.
Back art is scaled up first (back_scale), as Black/White draw it at twice its size.

Usage: gen5_stream.py SPECIES [SPECIES ...]   (names as in generated/species.txt, no prefix)

The source GIFs come from the PokeAPI sprites repository and are cached in
~/.cache/gen5_sprites; they are not checked in.

Member 0 of the NARC is the index: u16 member[species][face] (face 0 back, 1 front; 0 = no
stream). Every other member is one stream:

    u16 numFrames, u16 numSteps
    u8 left, u8 width               the animation's box in the 128x96 canvas: bytes (2 pixels)
    u8 top, u8 height               and rows; outside it every frame is transparent
    u32 frameOffset[numFrames]      from the start of the member, each 4-byte aligned
    {u8 frame, u8 duration}[numSteps] duration in 1/60 s, at least 1; the steps loop
    LZ77 (type 0x10) frames: height rows of width bytes, 4bpp with the low nibble left

The runtime copies a frame into rows top.. of a 128 wide 4bpp texture (64 bytes a row),
whose top 96 rows are the canvas.
"""

import json
import os
import struct
import sys
import urllib.request

from PIL import Image, ImageSequence

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "battle_stage"))

from nitro import write_narc  # noqa: E402
from process_mega_sprites import write_4bit_png, write_jasc_pal  # noqa: E402

CACHE = os.path.expanduser("~/.cache/gen5_sprites")
URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-v/black-white/animated"
OUT = os.path.join(ROOT, "res/prebuilt/battle/graphic/mon_stream.narc")

CANVAS_W, CANVAS_H = 128, 96  # a whole texture row wide, room for Gen 5's 2x back sprites
CLASSIC = 80
CLASSIC_LEFT = (CANVAS_W - CLASSIC) // 2  # the classic frame is the canvas at [24, 104) x [8, 88)
CLASSIC_TOP = (CANVAS_H - CLASSIC) // 2
GROUND_ROW = CLASSIC_TOP + CLASSIC - 1  # the union bottom sits on the classic frame's last row
BACK_MAX_SCALE = 2  # Black/White draw back sprites at twice their size
TRANSPARENT = (180, 180, 180)  # colour 0, as the other sprite palettes in the repo

FACES = (("back", "back/"), ("front", ""))


def species_ids():
    with open(os.path.join(ROOT, "generated/species.txt")) as f:
        names = [line.strip() for line in f if line.strip()]
    return {n[len("SPECIES_"):].lower(): i for i, n in enumerate(names)}, len(names)


def fetch(kind, num):
    path = os.path.join(CACHE, kind.replace("/", "_") + f"{num}.gif")
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        with urllib.request.urlopen(f"{URL}/{kind}{num}.gif") as r:
            data = r.read()
        with open(path, "wb") as f:
            f.write(data)
    return path


def load_gif(path):
    """[(RGBA image, duration ms)] with the GIF's disposal applied."""
    im = Image.open(path)
    return [(f.convert("RGBA"), f.info.get("duration", 100) or 100) for f in ImageSequence.Iterator(im)]


def opaque_colours(frames, counts):
    for img, _ in frames:
        for r, g, b, a in img.getdata():
            if a >= 128:
                counts[(r, g, b)] = counts.get((r, g, b), 0) + 1


def reduce_palette(counts, n):
    """Merges the closest colour pair (weighted) until n colours remain: {colour: palette colour}."""
    groups = [[c, w, [c]] for c, w in counts.items()]
    while len(groups) > n:
        best = None
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                a, b = groups[i], groups[j]
                d = sum((x - y) ** 2 for x, y in zip(a[0], b[0])) * min(a[1], b[1])
                if best is None or d < best[0]:
                    best = (d, i, j)
        _, i, j = best
        a, b = groups[i], groups[j]
        w = a[1] + b[1]
        mean = tuple(round((x * a[1] + y * b[1]) / w) for x, y in zip(a[0], b[0]))
        groups[i] = [mean, w, a[2] + b[2]]
        del groups[j]
    mapping = {}
    for mean, _, members in groups:
        for c in members:
            mapping[c] = mean
    return mapping, [g[0] for g in sorted(groups, key=lambda g: -g[1])]


def union_bbox(frames):
    box = None
    for img, _ in frames:
        b = img.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox()
        if b:
            box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    return box


def back_scale(box):
    """Up to BACK_MAX_SCALE, in steps of 1/8, while the union stays as tall as the classic frame
    and as wide as the canvas: Gen 4 back sprites fill their frame, the Gen 5 art is half size."""
    w, h = box[2] - box[0], box[3] - box[1]
    eighths = min(8 * BACK_MAX_SCALE, 8 * CLASSIC // h, 8 * CANVAS_W // w)
    return max(8, eighths) / 8


def scale_frames(frames, scale):
    return [(img.resize((round(img.width * scale), round(img.height * scale)), Image.NEAREST), d) for img, d in frames]


def place(box):
    """Canvas position of the union box's top left, and the crop of the source if it does not fit."""
    l, t, r, b = box
    w, h = r - l, b - t
    if w > CANVAS_W:
        l += (w - CANVAS_W) // 2
        w = CANVAS_W
    if h > CANVAS_H:
        t += h - CANVAS_H  # keep the feet
        h = CANVAS_H
    dx = (CANVAS_W - w) // 2 & ~1  # whole bytes
    dy = max(0, GROUND_ROW + 1 - h)
    return (l, t, l + w, t + h), dx, dy


def index_frame(img, crop, dx, dy, lookup):
    """CANVAS_H rows of CANVAS_W palette indices."""
    rows = [[0] * CANVAS_W for _ in range(CANVAS_H)]
    src = img.crop(crop)
    px = src.load()
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = px[x, y]
            if a >= 128:
                rows[dy + y][dx + x] = lookup[(r, g, b)]
    return rows


def lz10(data):
    """LZ77 type 0x10, as MI_UncompressLZ8 reads it."""
    out = bytearray(struct.pack("<I", 0x10 | (len(data) << 8)))
    heads = {}
    i, n = 0, len(data)
    while i < n:
        flag_pos = len(out)
        out.append(0)
        flags = 0
        for bit in range(8):
            if i >= n:
                break
            best_len, best_dist = 0, 0
            if i + 3 <= n:
                for j in reversed(heads.get(data[i:i + 3], [])[-64:]):
                    dist = i - j
                    if dist > 0x1000:
                        break
                    ln = 3
                    while ln < 18 and i + ln < n and data[j + ln] == data[i + ln]:
                        ln += 1
                    if ln > best_len:
                        best_len, best_dist = ln, dist
                        if ln == 18:
                            break
            step = best_len if best_len >= 3 else 1
            if best_len >= 3:
                flags |= 0x80 >> bit
                d = best_dist - 1
                out += bytes((((best_len - 3) << 4) | (d >> 8), d & 0xFF))
            else:
                out.append(data[i])
            for k in range(i, i + step):
                if k + 3 <= n:
                    heads.setdefault(data[k:k + 3], []).append(k)
            i += step
        out[flag_pos] = flags
    out += b"\x00" * (-len(out) % 4)
    return bytes(out)


def box_bytes(rows, box):
    left, width, top, height = box
    out = bytearray()
    for row in rows[top:top + height]:
        for x in range(2 * left, 2 * (left + width), 2):
            out.append(row[x] | (row[x + 1] << 4))
    return bytes(out)


def build_steps(frames, indexed):
    """Distinct frames and the (frame, duration) steps, timed on the 60 Hz clock without drift."""
    keys, distinct, steps = {}, [], []
    t_ms, t_vb = 0, 0
    for (img, dur), rows in zip(frames, indexed):
        key = bytes(v for row in rows for v in row)
        if key not in keys:
            keys[key] = len(distinct)
            distinct.append(rows)
        t_ms += dur
        vb = max(t_vb + 1, round(t_ms * 60 / 1000))
        steps.append([keys[key], vb - t_vb])
        t_vb = vb
    merged = []
    for f, d in steps:
        if merged and merged[-1][0] == f and merged[-1][1] + d <= 255:
            merged[-1][1] += d
        else:
            merged.append([f, min(d, 255)])
    return distinct, merged


def stream_member(distinct, steps, box):
    head = struct.pack("<HHBBBB", len(distinct), len(steps), *box)
    table_size = 4 * len(distinct)
    steps_blob = b"".join(struct.pack("BB", f, d) for f, d in steps)
    pos = len(head) + table_size + len(steps_blob)
    pos += -pos % 4
    offsets, blobs = [], []
    for rows in distinct:
        blob = lz10(box_bytes(rows, box))
        offsets.append(pos)
        blobs.append(blob)
        pos += len(blob)
    body = head + b"".join(struct.pack("<I", o) for o in offsets) + steps_blob
    body += b"\x00" * (-len(body) % 4)
    return body + b"".join(blobs)


def classic_sheet(rows_a, rows_b):
    """The 160x80 two-frame sheet: the canvas's classic window of each frame."""
    sheet = []
    for y in range(CLASSIC):
        ya = rows_a[CLASSIC_TOP + y][CLASSIC_LEFT:CLASSIC_LEFT + CLASSIC]
        yb = rows_b[CLASSIC_TOP + y][CLASSIC_LEFT:CLASSIC_LEFT + CLASSIC]
        sheet.append(ya + yb)
    return sheet


def bottom_gap(rows):
    for y in range(CLASSIC - 1, -1, -1):
        if any(rows[CLASSIC_TOP + y][CLASSIC_LEFT:CLASSIC_LEFT + CLASSIC]):
            return CLASSIC - 1 - y
    return 0


def build_species(name, num):
    src = {}
    for face, kind in FACES:
        src[face] = load_gif(fetch(kind, num))
        src[face + "_shiny"] = load_gif(fetch(kind + "shiny/", num))

    counts = {}
    for face, _ in FACES:
        opaque_colours(src[face], counts)
    mapping, colours = reduce_palette(counts, 15)
    palette = [TRANSPARENT] + colours + [(0, 0, 0)] * (15 - len(colours))
    lookup = {c: 1 + colours.index(m) for c, m in mapping.items()}

    # Shiny: each index takes the shiny colour most often found where the normal art has it
    votes = [{} for _ in range(16)]
    for face, _ in FACES:
        for (img, _), (simg, _) in zip(src[face], src[face + "_shiny"]):
            if img.size != simg.size:
                continue
            for p, s in zip(img.getdata(), simg.getdata()):
                if p[3] >= 128 and s[3] >= 128:
                    v = votes[lookup[p[:3]]]
                    v[s[:3]] = v.get(s[:3], 0) + 1
    shiny = [TRANSPARENT] + [max(v, key=v.get) if v else palette[i] for i, v in enumerate(votes) if i > 0]

    members, report = {}, {}
    sheets = {}
    for fi, (face, _) in enumerate(FACES):
        frames = src[face]
        scale = back_scale(union_bbox(frames)) if face == "back" else 1
        if scale != 1:
            frames = scale_frames(frames, scale)
        crop, dx, dy = place(union_bbox(frames))
        indexed = [index_frame(img, crop, dx, dy, lookup) for img, _ in frames]
        distinct, steps = build_steps(frames, indexed)
        w, h = crop[2] - crop[0], crop[3] - crop[1]
        box = (dx // 2, (w + 1) // 2, dy, h)
        member = stream_member(distinct, steps, box)
        members[fi] = member
        alt = distinct[steps[len(steps) // 2][0]]
        sheets[face] = (classic_sheet(distinct[steps[0][0]], alt), bottom_gap(distinct[steps[0][0]]))
        report[face] = {
            "scale": scale, "frames": len(frames), "distinct": len(distinct), "steps": len(steps),
            "loop_vblanks": sum(d for _, d in steps), "bytes": len(member),
            "union": [crop[2] - crop[0], crop[3] - crop[1]], "canvas_top": dy,
            "cropped": crop != union_bbox(frames),
        }
    report["colours"] = len(counts)

    sdir = os.path.join(ROOT, "res/pokemon", name)
    for face, _ in FACES:
        sheet, _ = sheets[face]
        for gender in ("male", "female"):
            if os.path.exists(os.path.join(sdir, f"{gender}_{face}.png")):
                write_4bit_png(os.path.join(sdir, f"{gender}_{face}.png"), 160, 80, sheet, palette)
    write_jasc_pal(os.path.join(sdir, "normal.pal"), palette)
    write_jasc_pal(os.path.join(sdir, "shiny.pal"), shiny)

    # y_offset is the blank rows under the static frame (the battle places the sprite that much
    # lower). The canvas puts the animation's lowest row on the frame's last row, so the stream
    # stands on the same line.
    jpath = os.path.join(sdir, "sprite_data.json")
    with open(jpath) as f:
        data = json.load(f)
    for face, _ in FACES:
        for gender in data[face]["y_offset"]:
            data[face]["y_offset"][gender] = 0
    with open(jpath, "w") as f:
        json.dump(data, f, indent=4)
        f.write("\n")
    return members, report


def main():
    ids, count = species_ids()
    names = sys.argv[1:]
    if not names:
        sys.exit(__doc__)
    index = [0] * (count * 2)
    members = [b""]
    reports = {}
    for name in names:
        num = ids[name]
        faces, report = build_species(name, num)
        for fi in (0, 1):
            index[num * 2 + fi] = len(members)
            members.append(faces[fi])
        reports[name] = report
        print(name, json.dumps(report), flush=True)
    members[0] = struct.pack(f"<{len(index)}H", *index)
    write_narc(OUT, members)
    total = sum(len(m) for m in members[1:])
    print(f"{OUT}: {len(members) - 1} streams, {total} bytes")
    with open(os.path.join(os.path.dirname(__file__), "report.json"), "w") as f:
        json.dump(reports, f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()

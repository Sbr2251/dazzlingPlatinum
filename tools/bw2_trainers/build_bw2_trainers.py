#!/usr/bin/env python3
"""Build the BW2 animated battle trainer fronts from pokebw2's trainer MCSS.

    ~/.venvs/desmume/bin/python tools/bw2_trainers/build_bw2_trainers.py [--sheet DIR]

For every row of mapping.MAPPING it flattens BW2's idle loop (NMAR sequence 0) into whole 80x80 frames, keeps
at most MAX_FRAMES distinct ones, and writes a trainer front in Platinum's own format to
res/trainers/bw2/<our class>/:

- front.png: the frames stacked with a 1 px gap, the layout nitrogfx's -cell mode reads (one cell per frame);
  8-bit indexed with BW2's 16-colour palette (index 0 transparent), converted to 4bpp at build time;
- front_cell.json: one cell per frame, each the standard 80x80 six-OAM layout, VRAM transfer of 3200 bytes
  per cell (the size of Platinum's trainer slot: one 80x80 4bpp frame);
- front_anim.json: sequence 0 is frame 0 held (what the slide-in shows, like BW2, which holds the trainer's
  animation until the throw), sequence 1 is the idle loop. Frame 0 of sequence 1 carries the user attribute
  0x102 ("switch to sequence 1, done"), so the encounter task (battle_display.c ov16_02264650) starts the loop
  and goes on at once instead of waiting for a gesture to end, and BattleTrainerBW2_StartIdle can tell a
  looping BW2 front from Platinum's one-shot gestures.

It also writes res/trainers/bw2/trfgra_bw2.order (the archive order, 4 files per entry) and
src/battle/battle_trainer_bw2_table.h (TRAINER_CLASS_* -> entry + 1), and with --sheet a contact sheet of
ours against BW2 for every mapped class.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

from mapping import MAPPING  # noqa: E402
from mcss_trainer import CANVAS, ORIGIN_X, ORIGIN_Y, Trainer  # noqa: E402

BW2_FRONT = Path("/data/repos/pokebw2/res/trainers/sprites/front")
CLASSES = ROOT / "res/trainers/classes"
OUT = ROOT / "res/trainers/bw2"
TABLE = ROOT / "src/battle/battle_trainer_bw2_table.h"

SIZE = 80              # Platinum trainer cell: 80x80, 100 tiles, 3200 bytes at 4bpp
FRAME_BYTES = SIZE * SIZE // 2
MAX_FRAMES = 12        # distinct frames per class: 38.4 KB of battle heap while the trainer is on screen
TICKS_PER_DELAY = 1    # MCSS ticks (60 Hz) per NANR delay unit (the battle animates OBJs once per 60 Hz frame)
IDLE_ATTR = 0x102      # ov16_02264650: 0x1nn = "set sequence nn-1 and finish"


def class_consts():
    return [line.strip() for line in (ROOT / "generated/trainer_classes.txt").read_text().splitlines() if line.strip()]


def choose_window(poses):
    """The 80x80 window (left, top on the canvas). Feet stay on the bottom row as in Platinum's art; a pose
    taller than 80 loses its top. Horizontally the MCSS origin stays at x 40 unless the loop is wider or off
    centre, then the window slides to keep the most pixels."""
    minx = miny = CANVAS
    maxx = maxy = -1
    cols = [0] * CANVAS
    for g in poses:
        for y, row in enumerate(g):
            for x, c in enumerate(row):
                if c:
                    cols[x] += 1
                    minx, maxx = min(minx, x), max(maxx, x)
                    miny, maxy = min(miny, y), max(maxy, y)
    top = maxy + 1 - SIZE
    left = ORIGIN_X - SIZE // 2
    if minx < left or maxx >= left + SIZE:
        if maxx - minx + 1 <= SIZE:
            left = min(max(left, maxx + 1 - SIZE), minx)
        else:
            left = max(range(minx, maxx + 2 - SIZE), key=lambda l: (sum(cols[l:l + SIZE]), -abs(l - (ORIGIN_X - SIZE // 2))))
    return left, top, (minx, miny, maxx, maxy)


def crop(g, left, top):
    out = []
    for y in range(top, top + SIZE):
        row = g[y] if 0 <= y < CANVAS else [0] * CANVAS
        out.append(tuple(row[x] if 0 <= x < CANVAS else 0 for x in range(left, left + SIZE)))
    return tuple(out)


def diff(a, b):
    return sum(1 for ra, rb in zip(a, b) for x, y in zip(ra, rb) if x != y)


def flatten(tr):
    """The idle loop as [(frame index, ticks)] over distinct 80x80 frames, at most MAX_FRAMES of them."""
    length = tr.idle_length()
    full = [tr.render(t) for t in range(length)]
    left, top, bbox = choose_window(full)
    frames, timeline = [], []
    index = {}
    for g in full:
        f = crop(g, left, top)
        if f not in index:
            index[f] = len(frames)
            frames.append(f)
        timeline.append(index[f])
    # Merge the least visible frames into their nearest neighbour until the cap holds
    alive = list(range(len(frames)))
    remap = list(range(len(frames)))
    while len(alive) > MAX_FRAMES:
        ticks = {i: 0 for i in alive}
        for t in timeline:
            ticks[remap[t]] += 1
        best = None
        for i in alive:
            j = min((k for k in alive if k != i), key=lambda k: diff(frames[i], frames[k]))
            cost = diff(frames[i], frames[j]) * ticks[i]
            if best is None or cost < best[0]:
                best = (cost, i, j)
        _, i, j = best
        alive.remove(i)
        remap = [j if r == i else r for r in remap]
    # Renumber in order of first appearance, frame 0 first
    order = []
    for t in timeline:
        if remap[t] not in order:
            order.append(remap[t])
    new_index = {old: n for n, old in enumerate(order)}
    kept = [frames[old] for old in order]
    steps = []
    for t in timeline:
        n = new_index[remap[t]]
        if steps and steps[-1][0] == n:
            steps[-1][1] += 1
        else:
            steps.append([n, 1])
    if len(steps) > 1 and steps[0][0] == steps[-1][0]:
        # the loop wraps: rotate so the sequence starts at frame 0's start (it does: t=0 is frame 0)
        pass
    return kept, [(n, d) for n, d in steps], {"window": (left - ORIGIN_X, top - ORIGIN_Y), "bbox": bbox,
                                              "loop_ticks": length, "distinct": len(frames)}


def write_png(path, frames, pal):
    from PIL import Image
    h = len(frames) * (SIZE + 1) - 1
    im = Image.new("P", (SIZE, h), 0)
    px = im.load()
    for i, f in enumerate(frames):
        for y in range(SIZE):
            for x in range(SIZE):
                px[x, i * (SIZE + 1) + y] = f[y][x]
    flat = [v for c in pal[:16] for v in c]
    flat += [0] * (16 * 3 - len(flat))
    im.putpalette(flat + [0] * (768 - len(flat)))
    im.save(path, bits=8)


def write_cell_json(path, n):
    tmpl = json.loads((CLASSES / "youngster/front_cell.json").read_text())
    cell = tmpl["cells"][0]
    d = copy.deepcopy(tmpl)
    d["cells"] = [copy.deepcopy(cell) for _ in range(n)]
    d["cellCount"] = n
    d["vramTransferMaxSize"] = FRAME_BYTES
    d["transferData"] = [{"offset": i * FRAME_BYTES, "size": FRAME_BYTES} for i in range(n)]
    d["cellAttributes"] = [0] * n
    d["labels"] = ["CellAnime0"]
    d["labelCount"] = 1
    path.write_text(json.dumps(d, indent="\t") + "\n")


def write_anim_json(path, steps):
    n_cells = max(s[0] for s in steps) + 1
    seq0 = {"frameCount": 1, "loopStartFrame": 0, "animationElement": 0, "animationType": 1, "playbackMode": 2,
            "frameData": [{"frameDelay": 4, "resultId": 0}]}
    seq1 = {"frameCount": len(steps), "loopStartFrame": 0, "animationElement": 0, "animationType": 1,
            "playbackMode": 2,
            "frameData": [{"frameDelay": max(1, round(d / TICKS_PER_DELAY)), "resultId": n} for n, d in steps]}
    attrs = [0] + [IDLE_ATTR] + [0] * (len(steps) - 1)
    d = {
        "labelEnabled": True,
        "uaatEnabled": True,
        "sequenceCount": 2,
        "frameCount": 1 + len(steps),
        "sequences": [seq0, seq1],
        "animationResults": [{"resultType": 0, "index": i} for i in range(n_cells)],
        "resultCount": n_cells,
        "labels": ["CellAnime1", "CellAnime0"],
        "labelCount": 2,
        "uaatData": {"sequenceAttributes": [0, 0], "frameAttributes": attrs},
    }
    path.write_text(json.dumps(d, indent="\t") + "\n")


def platinum_frame0(cls):
    from PIL import Image
    im = Image.open(CLASSES / cls / "front.png")
    return im.crop((0, 0, SIZE, SIZE)).convert("RGBA"), im


def contact_sheet(rows, path):
    from PIL import Image, ImageDraw
    scale = 2
    cell = SIZE * scale
    strip_n = 6
    cols = 2 + strip_n
    W = 160 + cols * (cell + 6)
    H = 24 + len(rows) * (cell + 18)
    sheet = Image.new("RGB", (W, H), (48, 52, 60))
    d = ImageDraw.Draw(sheet)
    d.text((4, 4), "ours (Platinum)  |  BW2 frame 0  |  BW2 idle loop, evenly spaced frames (ticks)", fill=(255, 255, 255))
    for r, (cls, bw, ours, frames, steps, pal) in enumerate(rows):
        y = 24 + r * (cell + 18)
        d.text((4, y + cell // 2 - 12), cls, fill=(255, 255, 255))
        d.text((4, y + cell // 2 + 2), "<- " + bw, fill=(180, 200, 255))
        bg = Image.new("RGBA", (cell, cell), (120, 160, 120, 255))
        a = bg.copy()
        a.alpha_composite(ours.resize((cell, cell), Image.NEAREST))
        sheet.paste(a, (160, y))
        total = sum(dd for _, dd in steps)
        picks = [0]
        for k in range(1, strip_n + 1):
            t = total * k // (strip_n + 1)
            acc = 0
            for n, dd in steps:
                if t < acc + dd:
                    picks.append((n, t))
                    break
                acc += dd
        for c, p in enumerate(picks):
            n, t = (0, 0) if p == 0 else p
            im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
            px = im.load()
            for yy in range(SIZE):
                for xx in range(SIZE):
                    v = frames[n][yy][xx]
                    if v:
                        px[xx, yy] = tuple(pal[v]) + (255,)
            b = bg.copy()
            b.alpha_composite(im.resize((cell, cell), Image.NEAREST))
            x = 160 + (c + 1) * (cell + 6)
            sheet.paste(b, (x, y))
            if c:
                d.text((x + 2, y + cell + 2), f"t{t} f{n}", fill=(220, 220, 220))
        d.text((160 + cell + 8, y + cell + 2), f"{len(frames)} frames, loop {total}", fill=(220, 220, 220))
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", help="directory for the contact sheet and the mapping table (evidence)")
    ap.add_argument("--only", nargs="*", help="classes to rebuild (default: all)")
    args = ap.parse_args()

    consts = class_consts()
    keys = sorted(MAPPING, key=lambda k: consts.index("TRAINER_CLASS_" + k.upper()))
    for k in keys:
        assert "TRAINER_CLASS_" + k.upper() in consts, k
    OUT.mkdir(parents=True, exist_ok=True)
    # Drop classes that left the table
    for old in OUT.iterdir():
        if old.is_dir() and old.name not in MAPPING:
            for f in old.iterdir():
                f.unlink()
            old.rmdir()

    rows, report = [], []
    for k in keys:
        bw = MAPPING[k]
        tr = Trainer(BW2_FRONT / bw)
        frames, steps, info = flatten(tr)
        dst = OUT / k
        dst.mkdir(exist_ok=True)
        if not args.only or k in args.only:
            write_png(dst / "front.png", frames, tr.pal)
            write_cell_json(dst / "front_cell.json", len(frames))
            write_anim_json(dst / "front_anim.json", steps)
        bx = info["bbox"]
        w, h = bx[2] - bx[0] + 1, bx[3] - bx[1] + 1
        report.append((k, bw, len(frames), info["distinct"], info["loop_ticks"], len(steps), w, h,
                       max(0, h - SIZE), max(0, w - SIZE)))
        print(f"{k:20s} <- {bw:16s} frames {len(frames):2d}/{info['distinct']:2d} loop {info['loop_ticks']:3d} "
              f"steps {len(steps):3d} size {w}x{h}", flush=True)
        if args.sheet:
            ours, _ = platinum_frame0(k)
            rows.append((k, bw, ours, frames, steps, tr.pal))

    (OUT / "trfgra_bw2.order").write_text("".join(
        f"{k}/front.NCGR\n{k}/front.NCLR\n{k}/front_cell.NCER\n{k}/front_anim.NANR\n" for k in keys))

    lines = [
        "// Generated by tools/bw2_trainers/build_bw2_trainers.py from tools/bw2_trainers/mapping.py. Do not edit.",
        "// Trainer class -> entry + 1 in poketool/trgra/trfgra_bw2.narc (4 files per entry); 0 = Platinum art.",
        "#ifndef POKEPLATINUM_BATTLE_TRAINER_BW2_TABLE_H",
        "#define POKEPLATINUM_BATTLE_TRAINER_BW2_TABLE_H",
        "",
        "static const u8 sTrainerClassBW2Front[] = {",
    ]
    for n, k in enumerate(keys):
        lines.append(f"    [TRAINER_CLASS_{k.upper()}] = {n + 1},")
    lines += ["};", "", "#endif // POKEPLATINUM_BATTLE_TRAINER_BW2_TABLE_H", ""]
    TABLE.write_text("\n".join(lines))

    if args.sheet:
        sd = Path(args.sheet)
        sd.mkdir(parents=True, exist_ok=True)
        half = (len(rows) + 1) // 2
        contact_sheet(rows[:half], sd / "contact_ours_vs_bw2_1.png")
        contact_sheet(rows[half:], sd / "contact_ours_vs_bw2_2.png")
        md = ["| our class | BW2 sprite | frames kept / distinct | loop (ticks) | anim steps | loop size | cropped top | cropped width |",
              "|---|---|---|---|---|---|---|---|"]
        for r in report:
            md.append(f"| {r[0]} | {r[1]} | {r[2]} / {r[3]} | {r[4]} | {r[5]} | {r[6]}x{r[7]} | {r[8]} | {r[9]} |")
        (sd / "mapping_table.md").write_text("\n".join(md) + "\n")


if __name__ == "__main__":
    main()

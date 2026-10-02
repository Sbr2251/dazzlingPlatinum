#!/usr/bin/env python3
"""Builds res/prebuilt/battle/graphic/mon_stream.narc: Gen 5 (Black/White) animated battle
sprites, streamed one 128x96 frame at a time into a small texture per battler
(docs/living_battle_stage/sprite_stream.md).

For each species it also rewrites res/pokemon/<species>/{male,female}_{front,back}.png and
normal.pal/shiny.pal from the same art, so the classic 80x80 sprite (other screens, and
battle draws that fall back to it) and the battler's palette slot match the stream, and it
sets the y_offset in sprite_data.json to 0 (the art already stands on the frame's last row).
Back art is stored at its own size and drawn at 1.75x (the member's scale is 14 eighths): Black/
White draw back sprites at 2x, which puts the big ones well off the screen. Its classic sheet is
the same 1.75x art cut to the 80x80 window.

Usage (needs PIL and numpy, e.g. ~/.venvs/desmume/bin/python):

    gen5_stream.py                    every species that has B/W art (front and back)
    gen5_stream.py --species budew    only these (the NARC then holds only these: for tests)
    gen5_stream.py --seed DIR         first copy DIR/{anim,animback}/<dex>.gif into the cache
    gen5_stream.py --jobs N           worker processes (default: all cores, at most 64)
    gen5_stream.py --max-member B     stream size cap (default MAX_MEMBER, 96 KB)

The source GIFs come from the PokeAPI sprites repository and are cached in
~/.cache/gen5_sprites ("<dex>.gif", "back_<dex>.gif", "shiny_<dex>.gif",
"back_shiny_female_<dex>.gif", ...); they are not checked in. Missing GIFs are downloaded.
Each species' result is cached in ~/.cache/gen5_sprites/built, keyed by this file and the
input GIFs, so a rerun takes seconds; output files are only written when they change.

Skipped: species whose battle sprite comes from PL_OTHERPOKE (forms, see FORM_SPECIES; their
pokegra files are never drawn in battle), Spinda (the game paints its spots on the classic
front at fixed places), Egg.

Megas: B/W has none, so each Mega's classic back (frame A of forms/mega/back.png, in its own
palette) becomes a one-frame stream at PL_OTHERPOKE's back character, drawn like the B/W backs:
standing on the ground row, at the scale that makes it as tall as its base form's back (at least
1.75x, at most 2x). Mega fronts stay classic; most are about the size of the B/W fronts.

Female art: where PokeAPI has a B/W female GIF (female/ and back/female/) the species gets a
female member and female_{front,back}.png; otherwise the female files are the male ones and
the index points the female file at no member (the reader falls back to the male one).
The palette is one per species (male and female share it): 15 colours and transparent.
shiny.pal is mapped index for index: every source colour is paired with the shiny colour
found at the same pixels of the shiny GIF (frames matched by their opaque mask), and the
palette is reduced on those pairs, so a battler's shiny palette slot just works.

Fit: art taller than the room above the ground row (88 rows), or wider than the canvas, is
cropped at the top when it overflows by at most CROP_MAX rows, and scaled down otherwise.
Back art is only cropped: drawn at 1.75x, 88 rows reach above the top of the screen, and the
sides are cut to BACK_MAX_W (the widest mesh, wider than the canvas at 1.75x).
Size: a stream bigger than MAX_MEMBER (or with more than 255 distinct frames) drops its most
similar frames until it fits ("dropped" in report.json), so the battle heap can hold it.
report.json lists per species frames, steps, bytes, scale and fit.

Member 0 of the NARC is the index (version 2):

    u16 version (2), u16 numPokegra, u16 numOtherpoke, u16 reserved (0)
    u16 pokegra[numPokegra]       member for each PL_POKEGRA file, by PokemonSpriteTemplate
                                  .character = species * 6 + file. Files per species:
                                  0 female back, 1 male back, 2 female front, 3 male front
                                  (BuildPokemonSpriteTemplate adds 1 when not female),
                                  4 and 5 the palettes. 0 = no member; a female file with 0
                                  falls back to the male file (+1), and 0 there is classic.
    u16 otherpoke[numOtherpoke]   member for each PL_OTHERPOKE file, by character; 0 = none

Every other member is one stream:

    u8 numFrames, u8 scale, u16 numSteps
                                    scale: in eighths, 8 (fronts), 14 (backs) or 14 to 16
                                    (Mega backs); drawn at
                                    scale/8 the size about the feet (see classic_window)
    u8 left, u8 width               the animation's box in the 128x96 canvas: bytes (2 pixels)
    u8 top, u8 height               and rows; outside it every frame is transparent
    u32 frameOffset[numFrames]      from the start of the member, each 4-byte aligned
    {u8 frame, u8 duration}[numSteps] duration in 1/60 s, at least 1; the steps loop
    LZ77 (type 0x10) frames: height rows of width bytes, 4bpp with the low nibble left

The runtime copies a frame into rows top.. of a 128 wide 4bpp texture (64 bytes a row),
whose top 96 rows are the canvas.
"""

import argparse
import hashlib
import json
import os
import pickle
import re
import shutil
import struct
import sys
import urllib.request
import zlib
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageSequence

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "battle_stage"))

from nitro import lz77_decompress, write_narc  # noqa: E402

CACHE = os.path.expanduser("~/.cache/gen5_sprites")
BUILT = os.path.join(CACHE, "built")
URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-v/black-white/animated"
OUT = os.path.join(ROOT, "res/prebuilt/battle/graphic/mon_stream.narc")
REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.json")

INDEX_VERSION = 2
POKEGRA_FILES = 6  # per species: female back, male back, female front, male front, normal, shiny
FILE_OF = {("female", "back"): 0, ("male", "back"): 1, ("female", "front"): 2, ("male", "front"): 3}

CANVAS_W, CANVAS_H = 128, 96  # a whole texture row wide, room for any B/W frame (96x96)
CLASSIC = 80
CLASSIC_LEFT = (CANVAS_W - CLASSIC) // 2  # the classic frame is the canvas at [24, 104) x [8, 88)
CLASSIC_TOP = (CANVAS_H - CLASSIC) // 2
GROUND_ROW = CLASSIC_TOP + CLASSIC - 1  # the union bottom sits on the classic frame's last row
ROOM_H = GROUND_ROW + 1  # rows above (and on) the ground row
CROP_MAX = 8  # art at most this much taller than ROOM_H loses its top rows, taller art shrinks
ANCHOR_U = CANVAS_W // 2  # the canvas column on the classic frame's centre line
FEET_Y = CLASSIC  # the classic frame row the feet stand on, at any scale
SCALE_ONE = 8  # member scales are in eighths
BACK_SCALE = 14  # 1.75x: Black/White draw back sprites at 2x, too big for the big ones here
MAX_SCALE = 16  # MON_STREAM_MAX_SCALE: 2x
BACK_MAX_W = min(CANVAS_W, 240 * SCALE_ONE // BACK_SCALE)  # 240 px, the widest sprite mesh (MESH_MAX_HALF_SIZE)
MAX_FRAMES = 255  # a step's frame is a u8
MAX_MEMBER = 96 * 1024  # bigger streams drop their most similar frames (the battle heap, see D)
TRANSPARENT = (180, 180, 180)  # colour 0, as the other sprite palettes in the repo

# National dex numbers of the species added after Arceus (species.txt order differs)
DEX_OVERRIDE = {"deino": 633, "zweilous": 634, "hydreigon": 635}
# Battle sprites from PL_OTHERPOKE (BuildPokemonSpriteTemplate), never from their pokegra files
FORM_SPECIES = {"unown", "castform", "deoxys", "burmy", "wormadam", "cherrim", "shellos",
                "gastrodon", "rotom", "giratina", "shaymin", "arceus"}
SKIP_SPECIES = {"none", "egg", "bad_egg", "spinda"} | FORM_SPECIES
# PokeAPI GIFs that show other art: rebuilt from the shiny GIF with the species' colours
SOURCE_FIXES = {("rattata", "back"): "recolour_shiny"}  # back/19.gif is a later gen's dark Rattata


# ---------------------------------------------------------------------------------------------
# Sources

def gif_name(kind, dex):
    """Cache file of PokeAPI path <kind><dex>.gif, kind like "", "back/", "back/shiny/female/"."""
    return os.path.join(CACHE, kind.replace("/", "_") + f"{dex}.gif")


def fetch(kind, dex):
    path = gif_name(kind, dex)
    if os.path.exists(path):
        return path
    missing = path + ".missing"  # remembers a 404 so reruns stay offline
    if os.path.exists(missing):
        return None
    os.makedirs(CACHE, exist_ok=True)
    try:
        with urllib.request.urlopen(f"{URL}/{kind}{dex}.gif", timeout=60) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        open(missing, "w").close()
        return None
    with open(path + ".tmp", "wb") as f:
        f.write(data)
    os.replace(path + ".tmp", path)
    return path


def seed(src):
    """Copies a downloaded B/W set (anim = front, animback = back) into the cache."""
    n = 0
    for sub, kind in (("anim", ""), ("animback", "back/")):
        d = os.path.join(src, sub)
        for f in os.listdir(d) if os.path.isdir(d) else []:
            if f.endswith(".gif") and f[:-4].isdigit() and not os.path.exists(gif_name(kind, f[:-4])):
                os.makedirs(CACHE, exist_ok=True)
                shutil.copyfile(os.path.join(d, f), gif_name(kind, f[:-4]))
                n += 1
    print(f"seeded {n} GIFs from {src}")


def load_gif(path):
    """[(RGBA array HxWx4, duration ms)] with the GIF's disposal applied."""
    im = Image.open(path)
    return [(np.array(f.convert("RGBA")), f.info.get("duration", 100) or 100) for f in ImageSequence.Iterator(im)]


def opaque(arr):
    return arr[:, :, 3] >= 128


def rgb_keys(arr):
    a = arr.astype(np.int64)
    return (a[:, :, 0] << 16) | (a[:, :, 1] << 8) | a[:, :, 2]


def key_rgb(k):
    return ((k >> 16) & 255, (k >> 8) & 255, k & 255)


def bbox(mask):
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def union_bbox(frames):
    box = None
    for arr, _ in frames:
        b = bbox(opaque(arr))
        if b:
            box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    return box


# ---------------------------------------------------------------------------------------------
# Palette

def count_colours(frames, counts):
    for arr, _ in frames:
        keys, n = np.unique(rgb_keys(arr)[opaque(arr)], return_counts=True)
        for k, c in zip(keys.tolist(), n.tolist()):
            counts[k] = counts.get(k, 0) + c


def masked_crop(arr):
    m = opaque(arr)
    b = bbox(m)
    if b is None:
        return None, None
    l, t, r, btm = b
    return m[t:btm, l:r].tobytes() + struct.pack("<HH", r - l, btm - t), arr[t:btm, l:r]


def shiny_votes(frames, shiny_frames, votes):
    """Pairs each normal colour with the shiny colour at the same pixels. Frames are matched
    by their opaque mask (the shiny GIFs have their own canvas sizes and frame counts); among
    shiny frames with the same mask (a mouth opening inside the outline), the one that pairs
    the colours most consistently (fewest distinct pairs) wins."""
    by_mask = {}
    for arr, _ in shiny_frames:
        k, crop = masked_crop(arr)
        if k is not None:
            cands = by_mask.setdefault(k, {})
            cands.setdefault(crop.tobytes(), rgb_keys(crop))
    seen, matched = set(), 0
    for arr, _ in frames:
        k, crop = masked_crop(arr)
        if k is None or k not in by_mask or crop.tobytes() in seen:
            continue
        seen.add(crop.tobytes())
        matched += 1
        m = opaque(crop)
        normal = rgb_keys(crop)[m] << 24
        best = None
        for cand in by_mask[k].values():
            keys, n = np.unique(normal | cand[m], return_counts=True)
            if best is None or len(keys) < len(best[0]):
                best = (keys, n)
        for p, c in zip(*(x.tolist() for x in best)):
            v = votes.setdefault(p >> 24, {})
            v[p & 0xFFFFFF] = v.get(p & 0xFFFFFF, 0) + c
    return matched


def fuzzy_votes(frames, shiny_frames, votes, need, limit=12, shift=2):
    """For colours the exact match missed: pairs frames whose masks agree best (at least 90%
    of their union) within a small shift, and votes for those colours only."""
    shiny_crops = {}
    for arr, _ in shiny_frames:
        k, crop = masked_crop(arr)
        if k is not None:
            shiny_crops.setdefault(k, crop)
    shiny_crops = list(shiny_crops.values())
    tried, seen = 0, set()
    for arr, _ in frames:
        if tried >= limit or not need:
            break
        k, crop = masked_crop(arr)
        if k is None or k in seen:
            continue
        seen.add(k)
        ma, ka = opaque(crop), rgb_keys(crop)
        if not need & set(np.unique(ka[ma]).tolist()):
            continue
        tried += 1
        best = (0.9, None)
        for sc in shiny_crops:
            mb = opaque(sc)
            if abs(mb.shape[0] - ma.shape[0]) > shift or abs(mb.shape[1] - ma.shape[1]) > shift:
                continue
            h, w = max(ma.shape[0], mb.shape[0]) + 2 * shift, max(ma.shape[1], mb.shape[1]) + 2 * shift
            pa = np.zeros((h, w), bool)
            pa[shift:shift + ma.shape[0], shift:shift + ma.shape[1]] = ma
            for oy in range(2 * shift + 1):
                for ox in range(2 * shift + 1):
                    pb = np.zeros((h, w), bool)
                    pb[oy:oy + mb.shape[0], ox:ox + mb.shape[1]] = mb
                    score = (pa & pb).sum() / (pa | pb).sum()
                    if score > best[0]:
                        best = (score, (sc, oy, ox, h, w))
        if best[1] is None:
            continue
        sc, oy, ox, h, w = best[1]
        ca = np.zeros((h, w), np.int64) - 1
        cb = np.zeros((h, w), np.int64) - 1
        ca[shift:shift + ma.shape[0], shift:shift + ma.shape[1]][ma] = ka[ma]
        mb = opaque(sc)
        cb[oy:oy + mb.shape[0], ox:ox + mb.shape[1]][mb] = rgb_keys(sc)[mb]
        both = (ca >= 0) & (cb >= 0)
        for a, b in zip(ca[both].tolist(), cb[both].tolist()):
            if a in need:
                v = votes.setdefault(a, {})
                v[b] = v.get(b, 0) + 1
        need -= set(votes)


def recolour(frames, votes):
    """Normal art made from shiny art, for faces whose normal GIF is wrong (SOURCE_FIXES)."""
    inverse = {}
    for normal, v in votes.items():
        for s, c in v.items():
            if c > inverse.get(s, (0, 0))[1]:
                inverse[s] = (normal, c)
    out = []
    for arr, d in frames:
        keys = rgb_keys(arr)
        new = arr.copy()
        m = opaque(arr)
        for k in np.unique(keys[m]).tolist():
            if k in inverse:
                sel = m & (keys == k)
                new[sel, 0], new[sel, 1], new[sel, 2] = key_rgb(inverse[k][0])
        out.append((new, d))
    return out


def reduce_palette(counts, shiny_of, n):
    """Merges the closest colour pair (weighted, on normal and shiny colour together) until n
    colours remain. Returns {source colour: slot} and the slots' (normal, shiny) colours."""
    groups = [[np.array(key_rgb(c) + shiny_of[c], dtype=np.float64), w, [c]] for c, w in counts.items()]
    while len(groups) > n:
        vec = np.array([g[0] for g in groups])
        w = np.array([g[1] for g in groups], dtype=np.float64)
        d = ((vec[:, None, :] - vec[None, :, :]) ** 2).sum(-1) * np.minimum(w[:, None], w[None, :])
        d[np.tril_indices(len(groups))] = np.inf
        i, j = np.unravel_index(np.argmin(d), d.shape)
        a, b = groups[i], groups[j]
        tw = a[1] + b[1]
        groups[i] = [(a[0] * a[1] + b[0] * b[1]) / tw, tw, a[2] + b[2]]
        del groups[j]
    groups.sort(key=lambda g: -g[1])
    slots, lookup = [], {}
    for i, (vec, _, members) in enumerate(groups):
        v = [int(round(x)) for x in vec]
        slots.append((tuple(v[:3]), tuple(v[3:])))
        for c in members:
            lookup[c] = 1 + i
    return lookup, slots


# ---------------------------------------------------------------------------------------------
# Frames

def resize_frames(frames, scale, smooth):
    out = []
    for arr, d in frames:
        img = Image.fromarray(arr, "RGBA")
        size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
        # Shrinking averages (premultiplied by Pillow), growing repeats pixels
        out.append((np.array(img.resize(size, Image.BOX if smooth else Image.NEAREST)), d))
    return out


def fit(frames, box, scale):
    """Shrinks art that overflows the room by more than CROP_MAX (or the canvas width). At 2x
    the room's top row and the canvas's sides are already off the screen: backs are only cut."""
    w, h = box[2] - box[0], box[3] - box[1]
    if scale != SCALE_ONE or (w <= CANVAS_W and h <= ROOM_H + CROP_MAX):
        return frames, 1
    f = min(CANVAS_W / w, ROOM_H / h)
    return resize_frames(frames, f, True), f


def place(box, max_w):
    """Canvas position of the union box's top left, and the crop of the source if it does not fit."""
    l, t, r, b = box
    w, h = r - l, b - t
    if w > max_w:
        l += (w - max_w) // 2
        w = max_w
    if h > ROOM_H:
        t += h - ROOM_H  # keep the feet on the ground row
        h = ROOM_H
    dx = (CANVAS_W - w) // 2 & ~1  # whole bytes
    dy = ROOM_H - h
    return (l, t, l + w, t + h), dx, dy


class Indexer:
    """Source colour -> palette slot; colours made by shrinking take the nearest slot."""

    def __init__(self, lookup, slots):
        self.lookup = dict(lookup)
        self.normal = np.array([s[0] for s in slots], dtype=np.int64)

    def __call__(self, keys):
        uniq, inv = np.unique(keys, return_inverse=True)
        out = np.empty(len(uniq), dtype=np.uint8)
        for i, k in enumerate(uniq.tolist()):
            s = self.lookup.get(k)
            if s is None:
                d = ((self.normal - np.array(key_rgb(k))) ** 2).sum(1)
                s = self.lookup[k] = 1 + int(np.argmin(d))
            out[i] = s
        return out[inv]


def index_frame(arr, crop, dx, dy, indexer):
    """The CANVAS_H x CANVAS_W palette indices of one frame."""
    canvas = np.zeros((CANVAS_H, CANVAS_W), dtype=np.uint8)
    l, t, r, b = crop
    src = np.zeros((b - t, r - l, 4), dtype=np.uint8)
    # The crop may reach past the frame (union of differently sized frames)
    sl, st = max(l, 0), max(t, 0)
    sr, sb = min(r, arr.shape[1]), min(b, arr.shape[0])
    if sr > sl and sb > st:
        src[st - t:sb - t, sl - l:sr - l] = arr[st:sb, sl:sr]
    m = opaque(src)
    region = canvas[dy:dy + src.shape[0], dx:dx + src.shape[1]]
    region[m] = indexer(rgb_keys(src)[m])
    return canvas


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


def box_bytes(canvas, box):
    left, width, top, height = box
    px = canvas[top:top + height, 2 * left:2 * (left + width)]
    return (px[:, 0::2] | (px[:, 1::2] << 4)).astype(np.uint8).tobytes()


def build_steps(frames, indexed):
    """Distinct frames and the (frame, duration) steps, timed on the 60 Hz clock without drift."""
    keys, distinct, steps = {}, [], []
    t_ms, t_vb = 0, 0
    for (_, dur), canvas in zip(frames, indexed):
        key = canvas.tobytes()
        if key not in keys:
            keys[key] = len(distinct)
            distinct.append(canvas)
        t_ms += dur
        vb = max(t_vb + 1, round(t_ms * 60 / 1000))
        steps.append([keys[key], vb - t_vb])
        t_vb = vb
    return distinct, steps


def merge_steps(steps):
    merged = []
    for f, d in steps:
        if merged and merged[-1][0] == f and merged[-1][1] + d <= 255:
            merged[-1][1] += d
        else:
            while d > 255:
                merged.append([f, 255])
                d -= 255
            merged.append([f, d])
    return merged


def member_size(blobs, steps):
    head = 8 + 4 * len(blobs) + 2 * len(steps)
    return head + (-head % 4) + sum(len(b) for b in blobs)


def thin(distinct, blobs, steps, cap):
    """Drops frames until the member fits in cap bytes and MAX_FRAMES frames: each time the
    frame closest (fewest pixels changed) to the one before it in the loop, whose steps then
    show that one. Step 0's frame (the classic frame A) stays. Returns the frames kept, their
    blobs, the merged steps and how many frames were dropped."""
    alive = set(range(len(distinct)))
    seq = [f for f, _ in steps]
    diffs = {}
    dropped = 0
    while True:
        merged = merge_steps([[seq[i], d] for i, (_, d) in enumerate(steps)])
        if len(alive) <= MAX_FRAMES and member_size([blobs[i] for i in alive], merged) <= cap:
            break
        best = None
        for i in range(len(seq)):
            a, b = seq[i - 1], seq[i]
            if a == b:
                continue
            if (a, b) not in diffs:
                diffs[a, b] = int((distinct[a] != distinct[b]).sum())
            if best is None or diffs[a, b] < best[0]:
                best = (diffs[a, b], a, b)
        if best is None:
            break
        _, keep, drop = best
        if drop == seq[0]:
            keep, drop = drop, keep
        seq = [keep if f == drop else f for f in seq]
        alive.discard(drop)
        dropped += 1
    order = sorted(alive)
    renum = {f: i for i, f in enumerate(order)}
    merged = merge_steps([[renum[seq[i]], d] for i, (_, d) in enumerate(steps)])
    return [distinct[i] for i in order], [blobs[i] for i in order], merged, dropped


def stream_member(blobs, steps, box, scale):
    head = struct.pack("<BBHBBBB", len(blobs), scale, len(steps), *box)
    steps_blob = b"".join(struct.pack("BB", f, d) for f, d in steps)
    pos = len(head) + 4 * len(blobs) + len(steps_blob)
    pos += -pos % 4
    offsets = []
    for blob in blobs:
        offsets.append(pos)
        pos += len(blob)
    body = head + b"".join(struct.pack("<I", o) for o in offsets) + steps_blob
    body += b"\x00" * (-len(body) % 4)
    member = body + b"".join(blobs)
    assert len(member) == member_size(blobs, steps)
    return member


# ---------------------------------------------------------------------------------------------
# Classic files

def png_bytes(pixels, palette):
    """A 4-bit indexed PNG (the layout tools/process_mega_sprites.py writes)."""
    def chunk(kind, data):
        c = kind + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    h, w = pixels.shape
    packed = ((pixels[:, 0::2] << 4) | pixels[:, 1::2]).astype(np.uint8)
    raw = b"".join(b"\x00" + row.tobytes() for row in packed)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 4, 3, 0, 0, 0))
            + chunk(b"PLTE", b"".join(struct.pack("BBB", *c) for c in palette))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def pal_bytes(palette):
    """JASC-PAL with CRLF line endings, 16 colours."""
    lines = ["JASC-PAL", "0100", "16"] + [f"{r} {g} {b}" for r, g, b in palette]
    return ("\r\n".join(lines) + "\r\n").encode("ascii")


def classic_window(canvas, scale):
    """The 80x80 classic frame of a canvas drawn at scale (eighths) about the feet: frame pixel
    (x, y) shows texel (ANCHOR_U + (x - 40) * 8 // scale, ROOM_H + (y - FEET_Y) * 8 // scale), as
    MON_STREAM_TEXEL_U/V. At 1:1 that is the canvas at (CLASSIC_LEFT, CLASSIC_TOP)."""
    px = np.arange(CLASSIC)
    u = ANCHOR_U + (px - CLASSIC // 2) * SCALE_ONE // scale
    v = ROOM_H + (px - FEET_Y) * SCALE_ONE // scale
    return canvas[np.ix_(v, u)]


def classic_sheet(canvas_a, canvas_b, scale):
    """The 160x80 two-frame sheet: the classic window of each frame."""
    return np.concatenate([classic_window(canvas_a, scale), classic_window(canvas_b, scale)], axis=1)


# ---------------------------------------------------------------------------------------------
# One palette group: a species (male and female art) or a set of forms sharing a palette

def build_unit(unit):
    """unit: {"name", "faces": [{"key", "face", "gif", "shiny", "png"}],
    "normal_pal", "shiny_pal"}. A face with gif None only copies the sheet of face "copy"
    to its png. Returns members {key: bytes}, files {path: bytes} and a report."""
    max_member = unit.get("max_member", MAX_MEMBER)
    src, shiny = {}, {}
    for f in unit["faces"]:
        if f.get("gif"):
            src[f["key"]] = load_gif(f["gif"])
            shiny[f["key"]] = load_gif(f["shiny"]) if f.get("shiny") else []

    counts, votes = {}, {}
    matched = {}
    fixed = [f["key"] for f in unit["faces"] if f.get("fix") == "recolour_shiny" and shiny.get(f["key"])]
    for k, frames in src.items():
        if k not in fixed:
            count_colours(frames, counts)
            matched[k] = shiny_votes(frames, shiny[k], votes)
    for k in fixed:
        src[k] = recolour(shiny[k], votes)
        count_colours(src[k], counts)
        matched[k] = shiny_votes(src[k], shiny[k], votes)
    need = set(counts) - set(votes)
    for k, frames in src.items():
        if need:
            fuzzy_votes(frames, shiny[k], votes, need)
    shiny_of = {c: key_rgb(max(votes[c], key=votes[c].get)) if c in votes else key_rgb(c) for c in counts}
    unmatched = sum(1 for c in counts if c not in votes)
    lookup, slots = reduce_palette(counts, shiny_of, 15)
    pad = [(0, 0, 0)] * (15 - len(slots))
    palette = [TRANSPARENT] + [s[0] for s in slots] + pad
    shiny_pal = [TRANSPARENT] + [s[1] for s in slots] + pad
    indexer = Indexer(lookup, slots)

    members, files, report, sheets = {}, {}, {"faces": {}}, {}
    for f in unit["faces"]:
        k = f["key"]
        if k not in src:
            continue
        frames = src[k]
        scale = BACK_SCALE if f["face"] == "back" else SCALE_ONE
        frames, shrink = fit(frames, union_bbox(frames), scale)
        ubox = union_bbox(frames)
        crop, dx, dy = place(ubox, CANVAS_W if scale == SCALE_ONE else BACK_MAX_W)
        indexed = [index_frame(arr, crop, dx, dy, indexer) for arr, _ in frames]
        distinct, steps = build_steps(frames, indexed)
        w, h = crop[2] - crop[0], crop[3] - crop[1]
        box = (dx // 2, (w + 1) // 2, dy, h)
        blobs = []
        for canvas in distinct:
            raw = box_bytes(canvas, box)
            blobs.append(lz10(raw))
            assert lz77_decompress(blobs[-1]) == raw
        n_distinct = len(distinct)
        distinct, blobs, steps, dropped = thin(distinct, blobs, steps, max_member)
        members[k] = stream_member(blobs, steps, box, scale)
        sheets[k] = classic_sheet(distinct[steps[0][0]], distinct[steps[len(steps) // 2][0]], scale)
        report["faces"][f["label"]] = {
            "scale": scale / SCALE_ONE, "frames": len(frames), "distinct": n_distinct, "dropped": dropped,
            "steps": len(steps),
            "loop_vblanks": sum(d for _, d in steps), "bytes": len(members[k]),
            "union": [w, h], "canvas_top": dy,
            "cropped_rows": (ubox[3] - ubox[1]) - h, "cropped_cols": (ubox[2] - ubox[0]) - w,
            "shrink": round(shrink, 3), "shiny_frames_matched": matched[k],
        }
    for f in unit["faces"]:
        sheet = sheets.get(f["key"]) if f["key"] in sheets else sheets.get(f.get("copy"))
        if f.get("png") and sheet is not None:
            files[f["png"]] = png_bytes(sheet, palette)
    files[unit["normal_pal"]] = pal_bytes(palette)
    files[unit["shiny_pal"]] = pal_bytes(shiny_pal)
    report["colours"] = len(counts)
    report["shiny_unmatched_colours"] = unmatched
    return members, files, report


def unit_hash(unit):
    h = hashlib.sha1()
    with open(os.path.abspath(__file__), "rb") as f:
        h.update(f.read())
    h.update(json.dumps(unit, sort_keys=True).encode())
    for f in unit["faces"]:
        for p in (f.get("gif"), f.get("shiny")):
            if p:
                with open(p, "rb") as fh:
                    h.update(fh.read())
    return h.hexdigest()


def build_cached(unit):
    path = os.path.join(BUILT, f"{unit['name']}-{unit_hash(unit)}.pkl")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return unit["name"], pickle.load(f)
    try:
        result = build_unit(unit)
    except Exception as e:  # a bad source keeps the classic sprite
        return unit["name"], e
    os.makedirs(BUILT, exist_ok=True)
    with open(path + ".tmp", "wb") as f:
        pickle.dump(result, f)
    os.replace(path + ".tmp", path)
    return unit["name"], result


# ---------------------------------------------------------------------------------------------
# Units

def species_list():
    with open(os.path.join(ROOT, "generated/species.txt")) as f:
        return [line.strip()[len("SPECIES_"):].lower() for line in f if line.strip()]


def species_unit(name, sid):
    dex = DEX_OVERRIDE.get(name, sid)
    front, back = fetch("", dex), fetch("back/", dex)
    if not front or not back:
        return None
    sdir = os.path.join(ROOT, "res/pokemon", name)
    with open(os.path.join(sdir, "meson.build")) as f:
        built = f.read()
    faces = []
    for face, kind in (("back", "back/"), ("front", "")):
        # Female-only species (Blissey, Jynx, ...) build no male PNGs: the male member still
        # streams, through the female files' fallback
        png = os.path.join(sdir, f"male_{face}.png") if f"'male_{face}.png'" in built else None
        faces.append({"key": ["pokegra", sid * POKEGRA_FILES + FILE_OF["male", face]], "label": face,
                      "face": face, "gif": fetch(kind, dex), "shiny": fetch(kind + "shiny/", dex),
                      "png": png})
        if (name, face) in SOURCE_FIXES:
            faces[-1]["fix"] = SOURCE_FIXES[name, face]
    for face, kind in (("back", "back/"), ("front", "")):
        png = os.path.join(sdir, f"female_{face}.png")
        if not os.path.exists(png):
            continue
        male = ["pokegra", sid * POKEGRA_FILES + FILE_OF["male", face]]
        f = {"key": ["pokegra", sid * POKEGRA_FILES + FILE_OF["female", face]], "label": "female_" + face,
             "face": face, "png": png, "copy": male}
        gif = fetch(kind + "female/", dex)
        if gif:
            f["gif"] = gif
            f["shiny"] = fetch(kind + "shiny/female/", dex)
        faces.append(f)
    for f in faces:
        f["key"] = tuple(f["key"])
        if "copy" in f:
            f["copy"] = tuple(f["copy"])
    return {"name": name, "dex": dex, "faces": faces,
            "normal_pal": os.path.join(sdir, "normal.pal"), "shiny_pal": os.path.join(sdir, "shiny.pal"),
            "sprite_data": os.path.join(sdir, "sprite_data.json")}


def write_if_changed(path, data):
    if os.path.exists(path):
        with open(path, "rb") as f:
            if f.read() == data:
                return False
    with open(path, "wb") as f:
        f.write(data)
    return True


def zero_y_offsets(path):
    """y_offset is the blank rows under the static frame (the battle places the sprite that much
    lower). The canvas puts the animation's lowest row on the frame's last row, so the stream
    stands on the same line."""
    with open(path) as f:
        data = json.load(f)
    for face in ("front", "back"):
        for gender in data[face]["y_offset"]:
            data[face]["y_offset"][gender] = 0
    return write_if_changed(path, (json.dumps(data, indent=4) + "\n").encode())


def mega_list():
    """(base species, back character) of each Mega in src/pokemon_mega_data.c."""
    with open(os.path.join(ROOT, "src/pokemon_mega_data.c")) as f:
        text = f.read()
    return [(m.group(1).lower(), int(m.group(2)))
            for m in re.finditer(r"\.baseSpecies = SPECIES_(\w+),.*?\.spriteCharacter = (\d+),", text, re.S)]


def mega_back(name, base_h):
    """A Mega's still back member, as tall as its base form's back (base_h source rows at
    BACK_SCALE), and its report."""
    sheet = np.array(Image.open(os.path.join(ROOT, "res/pokemon", name, "forms/mega/back.png")))
    frame = sheet[:, :CLASSIC]
    l, t, r, b = bbox(frame != 0)
    crop, dx, dy = place((l, t, r, b), CANVAS_W)
    l, t, r, b = crop
    w, h = r - l, b - t
    scale = min(MAX_SCALE, max(BACK_SCALE, round(base_h * BACK_SCALE / h)))
    canvas = np.zeros((CANVAS_H, CANVAS_W), dtype=np.uint8)
    canvas[dy:dy + h, dx:dx + w] = frame[t:b, l:r]
    box = (dx // 2, (w + 1) // 2, dy, h)
    member = stream_member([lz10(box_bytes(canvas, box))], [(0, 255)], box, scale)
    return member, {"scale": scale / SCALE_ONE, "union": [w, h], "canvas_top": dy, "bytes": len(member),
                    "base_union_h": base_h}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--species", nargs="+", help="only these species (names as in generated/species.txt)")
    ap.add_argument("--seed", help="copy DIR/{anim,animback}/<dex>.gif into the cache first")
    ap.add_argument("--jobs", type=int, default=min(64, os.cpu_count() or 1))
    ap.add_argument("--max-member", type=int, default=MAX_MEMBER, help="stream size cap in bytes")
    args = ap.parse_args()
    if args.seed:
        seed(args.seed)

    names = species_list()
    wanted = set(args.species) if args.species else None
    if wanted and wanted - set(names):
        sys.exit(f"unknown species: {sorted(wanted - set(names))}")
    units = []
    for sid, name in enumerate(names):
        if name in SKIP_SPECIES or (wanted and name not in wanted):
            continue
        u = species_unit(name, sid)
        if u:
            u["max_member"] = args.max_member
            units.append(u)
        elif not name.startswith("mega"):
            print(f"{name}: no B/W art, classic")

    with Pool(args.jobs) as pool:
        results = dict(pool.imap_unordered(build_cached, units))

    members = [b""]
    pokegra = [0] * (len(names) * POKEGRA_FILES)
    otherpoke = []
    reports, changed = {}, 0
    for u in units:
        res = results[u["name"]]
        if isinstance(res, Exception):
            print(f"{u['name']}: FAILED ({res}), classic")
            continue
        unit_members, files, report = res
        for f in u["faces"]:
            m = unit_members.get(f["key"])
            if m is None:
                continue
            kind, idx = f["key"]
            table = pokegra if kind == "pokegra" else otherpoke
            table.extend([0] * (idx + 1 - len(table)))
            table[idx] = len(members)
            members.append(m)
        for path, data in files.items():
            changed += write_if_changed(path, data)
        if u.get("sprite_data"):
            changed += zero_y_offsets(u["sprite_data"])
        report["dex"] = u["dex"]
        report["bytes"] = sum(len(m) for m in unit_members.values())
        reports[u["name"]] = report

    megas = {}
    for name, character in mega_list():
        if name not in reports:
            if not wanted:
                print(f"mega {name}: base form has no stream, classic")
            continue
        member, megas[name] = mega_back(name, reports[name]["faces"]["back"]["union"][1])
        otherpoke.extend([0] * (character + 1 - len(otherpoke)))
        otherpoke[character] = len(members)
        members.append(member)

    members[0] = struct.pack(f"<4H{len(pokegra)}H{len(otherpoke)}H", INDEX_VERSION, len(pokegra), len(otherpoke), 0,
                             *pokegra, *otherpoke)
    tmp = OUT + ".tmp"
    write_narc(tmp, members)  # through a file, so an unchanged NARC keeps its mtime
    with open(tmp, "rb") as f:
        narc = f.read()
    os.remove(tmp)
    changed += write_if_changed(OUT, narc)

    with open(REPORT, "w") as f:
        json.dump(dict(reports, megas=megas), f, indent=1, sort_keys=True)
        f.write("\n")

    sizes = sorted(((len(m), i) for i, m in enumerate(members) if i), reverse=True)
    owner = {}
    for name, r in megas.items():
        owner.setdefault(r["bytes"], []).append(f"mega {name} back")
    for name, r in reports.items():
        for label, fr in r["faces"].items():
            owner.setdefault(fr["bytes"], []).append(f"{name} {label}")
    print(f"{len(reports)} species and {len(megas)} Megas, {len(members) - 1} streams, {sum(s for s, _ in sizes)} bytes of streams")
    print(f"{OUT}: {len(narc)} bytes; {changed} files changed")
    print("biggest members:", ", ".join(f"{owner.get(s, ['?'])[0]} {s}" for s, _ in sizes[:12]))
    for name, r in sorted(reports.items()):
        notes = [f"{label} {'shrunk %.3f' % fr['shrink'] if fr['shrink'] != 1 else ''}"
                 f"{' cropped %d rows' % fr['cropped_rows'] if fr['cropped_rows'] else ''}"
                 f"{' cropped %d cols' % fr['cropped_cols'] if fr['cropped_cols'] else ''}"
                 for label, fr in r["faces"].items() if fr["shrink"] != 1 or fr["cropped_rows"] or fr["cropped_cols"]]
        if notes:
            print(f"  fit {name}: {'; '.join(n.strip() for n in notes)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Builds res/prebuilt/battle/graphic/mon_stream.narc: Gen 5 (Black 2/White 2) animated battle
sprites, streamed one 128x96 frame at a time into a small texture per battler
(docs/living_battle_stage/sprite_stream.md).

Source: pokebw2's own MCSS data (/data/repos/pokebw2/res/pokemon, READ-ONLY), played and drawn by
mcss.py the way BW2's battle does, one 60 Hz tick at a time: the frames, their durations and the loop
length are BW2's, every part moving at full rate, in BW2's exact normal and shiny palettes. Each
species maps to pokebw2's folder by its national dex number (dex_numbers.json for the species added
after Arceus). A species pokebw2 lacks falls back to the PokeAPI B/W animated GIFs (the step 2 path,
build_gif_unit); today none does.

For each species it also rewrites res/pokemon/<species>/{male,female}_{front,back}.png and
normal.pal/shiny.pal from the same art, so the classic 80x80 sprite (other screens, and battle draws
that fall back to it) and the battler's palette slot match the stream. In sprite_data.json it sets
y_offset to 0 and the front's addl_y_offset to the species' hover (see Hover). The form species do the
same with their forms/<form>/{front,back}.png and palettes, and the Substitute doll with
.shared/substitute_{front,back}.png and substitute.pal.

Usage (needs PIL and numpy, e.g. ~/.venvs/desmume/bin/python):

    gen5_stream.py                    every species (front and back), the forms and the doll
    gen5_stream.py --species budew    only these (the NARC then holds only these: for tests)
    gen5_stream.py --jobs N           worker processes (default: all cores, at most 64)
    gen5_stream.py --max-member B     stream size cap (default MAX_MEMBER, 96 KB)
    gen5_stream.py --gif              the PokeAPI GIFs for every species (the step 2 build)
    gen5_stream.py --seed DIR         first copy DIR/{anim,animback}/<dex>.gif into the GIF cache

Results are cached in ~/.cache/gen5_sprites/built, keyed by this file, mcss.py and the inputs, so a
rerun takes seconds; output files are only written when they change.

Skipped: Spinda (the game paints its spots on the classic front per personality; see
sprite_stream.md), the Egg, Arceus's ??? form (BW2 has no such form).

Hover: BW2 has no altitude table; the hover is in the art, drawn about the foot point (mcss.py
ORIGIN). The canvas puts the foot point on the ground row's lower edge (row GROUND_V), so a back stands
and hovers exactly as in BW2. A front is moved down by its species' lift, the hover of its lowest
point over the whole loop (the least over the species' front faces: male, female, forms), and
sprite_data.json's addl_y_offset (the battle's shadow height, which raises enemy fronts) puts that back:
every front frame ends up where BW2 draws it, floaters keep their room above the ground row, and move
animations that aim at MON_SPRITE_SHADOW_HEIGHT aim at the body.

Fit: a front that would reach more than CROP_MAX rows above the canvas, or is wider than it, is scaled
down about its feet (and its lift with it); otherwise it loses its top rows. A back is only cropped
(drawn at 1.75x, the canvas's top rows are off the screen). Art is placed with its foot point on the
canvas's centre column, shifted sideways only as far as it must to fit.
Size: a stream bigger than MAX_MEMBER, or with more than 255 distinct frames, drops its most similar
frames until it fits ("dropped" in report.json): the frame before it in the loop takes its steps, so the
timing stays BW2's.

Megas: B/W has none, so each Mega's classic back (frame A of forms/mega/back.png, in its own palette)
becomes a one-frame stream at PL_OTHERPOKE's back character, standing on the ground row, at the scale
that makes it as tall as its base form's back (at least 1.75x, at most 2x); its classic front becomes a
one-frame stream at 1:1, standing on the ground row (the base form's y_offset and addl_y_offset are the
B/W art's, so the classic front would float by its blank rows). Streamed form faces and the doll get
y_offset 0 in HEIGHT_O (res/prebuilt/poketool/pokegra/height_o.narc), as the species do in sprite_data.json.

Member 0 of the NARC is the index (version 3; version 2 had the same index and 8-byte stream headers):

    u16 version (3), u16 numPokegra, u16 numOtherpoke, u16 reserved (0)
    u16 pokegra[numPokegra]       member for each PL_POKEGRA file, by PokemonSpriteTemplate
                                  .character = species * 6 + file. Files per species:
                                  0 female back, 1 male back, 2 female front, 3 male front
                                  (BuildPokemonSpriteTemplate adds 1 when not female),
                                  4 and 5 the palettes. 0 = no member; a female file with 0
                                  falls back to the male file (+1), and 0 there is classic.
    u16 otherpoke[numOtherpoke]   member for each PL_OTHERPOKE file, by character; 0 = none:
                                  the form species' forms, the Mega backs, the Substitute doll

Identical members are stored once (Arceus's forms differ only in their palettes). Every other member is
one stream:

    u8 numFrames, u8 scale, u16 numSteps
                                    scale: in eighths, 8 (fronts), 14 (backs) or 14 to 16
                                    (Mega backs); drawn at scale/8 the size about the feet
    u8 left, u8 width               the animation's box in the 128x96 canvas: bytes (2 pixels)
    u8 top, u8 height               and rows; outside it every frame is transparent
    u8 idleKind                     IDLE_NONE 0: BW2 restarts the loop, never idles (idle node
                                    count 0xff); IDLE_FREEZE 1: an idle holds the whole sprite;
                                    IDLE_POSE 2: an idle shows BW2's second sequence (a pose), with
                                    the idle nodes (flames...) still moving
    u8 numIdleSteps                 0 with IDLE_NONE
    u16 reserved                    0
    u32 frameOffset[numFrames]      from the start of the member, each 4-byte aligned
    {u8 frame, u8 duration}[numSteps]       the loop, duration in 1/60 s, at least 1
    {u8 frame, u8 duration}[numIdleSteps]   the idle clip: IDLE_CLIP_TICKS (64) ticks, the
                                    longest BW2 idle; same frame table
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
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools", "battle_stage"))
sys.path.insert(0, HERE)

import mcss  # noqa: E402
from nitro import lz77_decompress, write_narc  # noqa: E402

CACHE = os.path.expanduser("~/.cache/gen5_sprites")
BUILT = os.path.join(CACHE, "built")
URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-v/black-white/animated"
OUT = os.path.join(ROOT, "res/prebuilt/battle/graphic/mon_stream.narc")
REPORT = os.path.join(HERE, "report.json")
BW2_SPECIES = "/data/repos/pokebw2/generated/species.txt"

INDEX_VERSION = 3
HEADER = "<BBHBBBBBBH"  # numFrames, scale, numSteps, left, width, top, height, idleKind, numIdleSteps, reserved
HEADER_SIZE = struct.calcsize(HEADER)
IDLE_NONE, IDLE_FREEZE, IDLE_POSE = 0, 1, 2
POKEGRA_FILES = 6  # per species: female back, male back, female front, male front, normal, shiny
FILE_OF = {("female", "back"): 0, ("male", "back"): 1, ("female", "front"): 2, ("male", "front"): 3}

CANVAS_W, CANVAS_H = 128, 96  # a whole texture row wide
CLASSIC = 80
CLASSIC_LEFT = (CANVAS_W - CLASSIC) // 2  # the classic frame is the canvas at [24, 104) x [8, 88)
CLASSIC_TOP = (CANVAS_H - CLASSIC) // 2
GROUND_ROW = CLASSIC_TOP + CLASSIC - 1  # the classic frame's last row
GROUND_V = GROUND_ROW + 1  # the foot point is on this row's top edge (MON_STREAM_GROUND_V)
ROOM_H = GROUND_ROW + 1  # rows above (and on) the ground row
CROP_MAX = 8  # art at most this much taller than ROOM_H loses its top rows, taller art shrinks
ANCHOR_U = CANVAS_W // 2  # the canvas column on the classic frame's centre line: the foot point
FEET_Y = CLASSIC  # the classic frame row the feet stand on, at any scale
SCALE_ONE = 8  # member scales are in eighths
BACK_SCALE = 14  # 1.75x: Black/White draw back sprites at 2x, too big for the big ones here
MAX_SCALE = 16  # MON_STREAM_MAX_SCALE: 2x
BACK_MAX_W = min(CANVAS_W, 240 * SCALE_ONE // BACK_SCALE)  # 240 px, the widest sprite mesh (MESH_MAX_HALF_SIZE)
MAX_FRAMES = 255  # a step's frame is a u8
MAX_MEMBER = 96 * 1024  # bigger streams drop their most similar frames (ROM size, see sprite_stream.md)
TRANSPARENT = (180, 180, 180)  # colour 0, as the other sprite palettes in the repo

# National dex numbers of the species added after Arceus (species.txt order differs). Kept in a
# data file so that adding species doesn't change this file (its hash keys the build cache).
with open(os.path.join(HERE, "dex_numbers.json")) as _f:
    DEX_OVERRIDE = json.load(_f)
# Battle sprites from PL_OTHERPOKE (BuildPokemonSpriteTemplate), never from their pokegra files
FORM_SPECIES = {"unown", "castform", "deoxys", "burmy", "wormadam", "cherrim", "shellos",
                "gastrodon", "rotom", "giratina", "shaymin", "arceus"}
SKIP_SPECIES = {"none", "egg", "bad_egg", "spinda"} | FORM_SPECIES
# Our form directory (res/pokemon/<species>/forms/<form>) -> pokebw2's (res/pokemon/<species>/<dir>),
# checked against pokebw2's form_<n>.json types. Arceus's BW2 forms are palettes only, by type index
# (BW2 has no ??? type, Platinum's form 9: it stays classic).
_ARCEUS = ["fighting", "flying", "poison", "ground", "rock", "bug", "ghost", "steel", "fire", "water", "grass",
           "electric", "psychic", "ice", "dragon", "dark"]
FORM_BW2 = {
    "unown": dict({"base": ""}, **{c: f"form_{i + 1}" for i, c in enumerate("bcdefghijklmnopqrstuvwxyz")},
                  exc="form_26", que="form_27"),
    "castform": {"base": "", "sunny": "form_1", "rainy": "form_2", "snowy": "form_3"},
    "deoxys": {"base": "", "attack": "form_1", "defense": "form_2", "speed": "form_3"},
    "burmy": {"base": "", "sandy": "form_1", "trash": "form_2"},
    "wormadam": {"base": "", "sandy": "form_1", "trash": "form_2"},
    "shellos": {"base": "", "east_sea": "form_1"},
    "gastrodon": {"base": "", "east_sea": "form_1"},
    "cherrim": {"base": "", "sunny": "form_1"},
    "rotom": {"base": "", "heat": "form_1", "wash": "form_2", "frost": "form_3", "fan": "form_4", "mow": "form_5"},
    "giratina": {"base": "", "origin": "form_1"},
    "shaymin": {"base": "", "sky": "form_1"},
    "arceus": dict({"base": "", "mystery": None}, **{t: f"form_{i + 1}" for i, t in enumerate(_ARCEUS)}),
}
PALETTE_ONLY_FORMS = {"arceus"}  # the forms' art is the base form's
SUBSTITUTE_BW2 = os.path.join(mcss.BW2, "shared", "substitute")
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


def member_size(blobs, num_steps):
    head = HEADER_SIZE + 4 * len(blobs) + 2 * num_steps
    return head + (-head % 4) + sum(len(b) for b in blobs)


def thin(distinct, blobs, step_lists, cap, keep=()):
    """Drops frames until the member fits in cap bytes and MAX_FRAMES frames: each time the
    frame closest (fewest pixels changed) to the one before it in a step list (the loop, cyclic;
    the idle clip), whose steps then show that one, so every step keeps its duration. The frames in
    keep (step 0's, the classic frame A) stay. Returns the frames kept, their blobs, the merged step
    lists and how many frames were dropped."""
    alive = set(range(len(distinct)))
    seqs = [[f for f, _ in steps] for steps in step_lists]
    diffs = {}
    dropped = 0

    def merged_lists():
        return [merge_steps([[seq[i], d] for i, (_, d) in enumerate(steps)]) for seq, steps in zip(seqs, step_lists)]

    while True:
        merged = merged_lists()
        if len(alive) <= MAX_FRAMES and member_size([blobs[i] for i in alive], sum(len(m) for m in merged)) <= cap:
            break
        best = None
        for li, seq in enumerate(seqs):
            for i in range(0 if li == 0 else 1, len(seq)):
                a, b = seq[i - 1], seq[i]
                if a == b or (a in keep and b in keep):
                    continue
                if (a, b) not in diffs:
                    diffs[a, b] = int((distinct[a] != distinct[b]).sum())
                if best is None or diffs[a, b] < best[0]:
                    best = (diffs[a, b], a, b)
        if best is None:
            break
        _, keep_f, drop = best
        if drop in keep:
            keep_f, drop = drop, keep_f
        seqs = [[keep_f if f == drop else f for f in seq] for seq in seqs]
        alive.discard(drop)
        dropped += 1
    order = sorted(alive)
    renum = {f: i for i, f in enumerate(order)}
    seqs = [[renum[f] for f in seq] for seq in seqs]
    merged = merged_lists()
    return [distinct[i] for i in order], [blobs[i] for i in order], merged, dropped


def stream_member(blobs, steps, box, scale, idle_kind=IDLE_NONE, idle_steps=()):
    assert len(blobs) <= MAX_FRAMES and len(idle_steps) <= 255 and (idle_kind == IDLE_NONE) == (len(idle_steps) == 0)
    head = struct.pack(HEADER, len(blobs), scale, len(steps), *box, idle_kind, len(idle_steps), 0)
    steps_blob = b"".join(struct.pack("BB", f, d) for f, d in list(steps) + list(idle_steps))
    pos = len(head) + 4 * len(blobs) + len(steps_blob)
    pos += -pos % 4
    offsets = []
    for blob in blobs:
        offsets.append(pos)
        pos += len(blob)
    body = head + b"".join(struct.pack("<I", o) for o in offsets) + steps_blob
    body += b"\x00" * (-len(body) % 4)
    member = body + b"".join(blobs)
    assert len(member) == member_size(blobs, len(steps) + len(idle_steps))
    return member


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
    """The 160x80 two-frame sheet: the classic window of each frame. Its first four pixels are made
    transparent: the pokegra and otherpoke NCGRs are encrypted front to back (nitrogfx -scan with the
    .png.key) and the game takes the first u16 of the encrypted data as its seed, which only holds when
    those pixels are 0 (otherwise the whole classic sprite decodes to noise)."""
    sheet = np.concatenate([classic_window(canvas_a, scale), classic_window(canvas_b, scale)], axis=1)
    sheet[0, :4] = 0
    return sheet


# ---------------------------------------------------------------------------------------------
# One palette group: a species (male and female art) or a set of forms sharing a palette

def build_gif_unit(unit):
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
        distinct, blobs, (steps,), dropped = thin(distinct, blobs, [steps], max_member, keep={steps[0][0]})
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



# ---------------------------------------------------------------------------------------------
# BW2 MCSS faces (mcss.py)

def face_spec_key(spec):
    return (spec["anim"], spec["face"], bool(spec.get("female")))


def files_hash(paths):
    h = hashlib.sha1()
    for name in ("gen5_stream.py", "mcss.py"):
        with open(os.path.join(HERE, name), "rb") as f:
            h.update(f.read())
    for p in paths:
        h.update(p.encode())
        if p and os.path.exists(p):
            with open(p, "rb") as f:
                h.update(f.read())
    return h.hexdigest()


def anim_files(directory, face, female):
    names = ["multi_animations.nmar", "multi_cells.nmcr", "animations.nanr.lz11", "info.bin",
             "female.png" if female else None]
    out = [os.path.join(directory, f"{face}_{n}") for n in names if n]
    if not female:
        out.append(os.path.join(directory, f"{face}.png"))
    return out


def face_poses(face):
    """The loop's poses (one a tick), the idle clip's (or None) and the idle kind."""
    poses, wrap = mcss.battle_loop(face)
    clip = mcss.idle_clip(face, wrap)
    if clip is None:
        kind = IDLE_NONE
    elif len(face.nmar) > 1:
        kind = IDLE_POSE
    else:
        kind = IDLE_FREEZE
    return poses, clip, kind


def measure(spec):
    """Pass 1: the face's union box about the foot point at 1:1 (loop and idle clip), cached."""
    key = face_spec_key(spec)
    path = os.path.join(BUILT, "measure-" + files_hash(anim_files(*key)) + ".json")
    if os.path.exists(path):
        with open(path) as f:
            return key, json.load(f)
    face = mcss.Face(spec["anim"], spec["face"], spec.get("female", False))
    poses, clip, kind = face_poses(face)
    box = None
    for img in mcss.frames_of(face, list(dict.fromkeys(poses + (clip or [])))):
        b = mcss.bbox(img)
        if b:
            box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    ox, oy = mcss.ORIGIN
    res = {"left": box[0] - ox, "top": box[1] - oy, "right": box[2] - ox, "bottom": box[3] - oy,
           "loop": len(poses), "idle": kind, "frame0_bottom": mcss.bbox(mcss.render(face, poses[0]))[3] - oy}
    os.makedirs(BUILT, exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(res, f)
    os.replace(path + ".tmp", path)
    return key, res


def front_shrink(m):
    """The scale a front is drawn at so it fits: 1, or less when it would overflow the canvas's width
    or reach more than CROP_MAX rows above it (its own lift counted)."""
    w = m["right"] - m["left"]
    h = m["bottom"] - m["top"]  # feet to head, hover gap excluded once lifted
    room_h = ROOM_H + CROP_MAX
    lifted_h = h if m["bottom"] < 0 else -m["top"]
    if w <= CANVAS_W and lifted_h <= room_h:
        return 1.0
    return min(CANVAS_W / w, ROOM_H / lifted_h)


def to_rgba(img, palette):
    out = np.zeros(img.shape + (4,), dtype=np.uint8)
    pal = np.array(palette, dtype=np.uint8)
    m = img != 0
    out[m, :3] = pal[img[m]]
    out[m, 3] = 255
    return out


def shrink_frame(img, f, palette):
    """img about mcss.ORIGIN scaled by f with Pillow's box filter, colours back to the palette; returns
    the indices and the new origin."""
    rgba = Image.fromarray(to_rgba(img, palette), "RGBA")
    size = (max(1, round(img.shape[1] * f)), max(1, round(img.shape[0] * f)))
    arr = np.array(rgba.resize(size, Image.BOX))
    pal = np.array(palette[1:], dtype=np.int64)
    out = np.zeros(arr.shape[:2], dtype=np.uint8)
    m = arr[:, :, 3] >= 128
    if m.any():
        px = arr[m][:, :3].astype(np.int64)
        d = ((px[:, None, :] - pal[None, :, :]) ** 2).sum(-1)
        out[m] = 1 + d.argmin(1)
    return out, (round(mcss.ORIGIN[0] * f), round(mcss.ORIGIN[1] * f))


def place_mcss(m, f, lift, back):
    """Canvas placement of a face whose union box about the foot point (scaled by f) is m: the shift
    that keeps it inside the canvas, the box and the crops. Canvas pixel (c, r) shows the image's foot-
    relative pixel (c - ANCHOR_U - shift, r - GROUND_V - lift)."""
    left, right = int(np.floor(m["left"] * f)), int(np.ceil(m["right"] * f))
    top, bottom = int(np.floor(m["top"] * f)), int(np.ceil(m["bottom"] * f))
    c0, c1 = ANCHOR_U + left, ANCHOR_U + right
    max_w = BACK_MAX_W if back else CANVAS_W
    shift = 0
    if c1 - c0 <= max_w:
        if c0 < 0:
            shift = -c0
        elif c1 > CANVAS_W:
            shift = CANVAS_W - c1
    c0, c1 = max(0, c0 + shift), min(CANVAS_W, c1 + shift)
    if c1 - c0 > max_w:
        cut = c1 - c0 - max_w
        c0 += cut // 2
        c1 = c0 + max_w
    r0, r1 = GROUND_V + top + lift, GROUND_V + bottom + lift
    crop_top, crop_bottom = max(0, -r0), max(0, r1 - CANVAS_H)
    r0, r1 = max(0, r0), min(CANVAS_H, r1)
    cropped_cols = (right - left) - (c1 - c0)
    box = (c0 // 2, (c1 + 1) // 2 - c0 // 2, r0, r1 - r0)
    return {"shift": shift, "box": box, "crop_top": crop_top, "crop_bottom": crop_bottom, "cropped_cols": cropped_cols}


def canvas_of(img, origin, shift, lift, box):
    """The CANVAS_H x CANVAS_W canvas of a rendered frame, zero outside the box."""
    canvas = np.zeros((CANVAS_H, CANVAS_W), dtype=np.uint8)
    ox, oy = origin
    x0 = ox - ANCHOR_U - shift  # image column of canvas column 0
    y0 = oy - GROUND_V - lift
    sx0, sy0 = max(0, x0), max(0, y0)
    sx1, sy1 = min(img.shape[1], x0 + CANVAS_W), min(img.shape[0], y0 + CANVAS_H)
    canvas[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = img[sy0:sy1, sx0:sx1]
    left, width, top, height = box
    out = np.zeros_like(canvas)
    out[top:top + height, 2 * left:2 * (left + width)] = canvas[top:top + height, 2 * left:2 * (left + width)]
    return out


def ticks_to_steps(seq):
    """Per-tick frame ids -> merged (frame, duration) steps."""
    return merge_steps([[f, 1] for f in seq])


def build_mcss_face(spec, palette, f, lift, max_member):
    """One stream from a BW2 face: member bytes, the classic sheet and the report."""
    face = mcss.Face(spec["anim"], spec["face"], spec.get("female", False))
    poses, clip, kind = face_poses(face)
    m = measure(spec)[1]
    back = spec["face"] == "back"
    scale = BACK_SCALE if back else SCALE_ONE
    p = place_mcss(m, f, lift, back)
    box = p["box"]
    cache, keys, distinct = {}, {}, []

    def frame_id(pose):
        if pose not in cache:
            img = mcss.render(face, pose)
            origin = mcss.ORIGIN
            if f != 1.0:
                img, origin = shrink_frame(img, f, palette)
            canvas = canvas_of(img, origin, p["shift"], lift, box)
            k = canvas.tobytes()
            if k not in keys:
                keys[k] = len(distinct)
                distinct.append(canvas)
            cache[pose] = keys[k]
        return cache[pose]

    loop = [frame_id(q) for q in poses]
    idle = [frame_id(q) for q in clip] if clip is not None else []
    steps, idle_steps = ticks_to_steps(loop), ticks_to_steps(idle)
    blobs = []
    for canvas in distinct:
        raw = box_bytes(canvas, box)
        blobs.append(lz10(raw))
        assert lz77_decompress(blobs[-1]) == raw
    n_distinct = len(distinct)
    distinct, blobs, (steps, idle_steps), dropped = thin(distinct, blobs, [steps, idle_steps], max_member,
                                                         keep={steps[0][0]})
    member = stream_member(blobs, steps, box, scale, kind, idle_steps)
    sheet = classic_sheet(distinct[steps[0][0]], distinct[steps[len(steps) // 2][0]], scale)
    report = {
        "source": os.path.relpath(spec["anim"], mcss.BW2) + ("/female" if spec.get("female") else ""),
        "scale": scale / SCALE_ONE, "loop_vblanks": sum(d for _, d in steps), "bw2_loop": len(poses),
        "distinct": n_distinct, "frames": len(blobs), "dropped": dropped, "steps": len(steps),
        "idle": ["none", "freeze", "pose"][kind], "idle_steps": len(idle_steps), "bytes": len(member),
        "union": [box[1] * 2, box[3]], "canvas_top": box[2], "lift": lift, "shrink": round(f, 3),
        "shift_x": p["shift"], "cropped_rows": p["crop_top"], "cropped_bottom_rows": p["crop_bottom"],
        "cropped_cols": p["cropped_cols"], "hover": -m["bottom"], "frame0_hover": -m["frame0_bottom"],
    }
    return member, sheet, report


def build_mcss_unit(unit):
    """unit: {"name", "pal_dir", "faces": [{"key", "label", "face", "anim", "female", "png", "f", "lift"}],
    "normal_pal", "shiny_pal"}; faces with no "anim" copy face "copy"'s sheet to their png."""
    palette = mcss.load_pal(os.path.join(unit["pal_dir"], "normal.pal"))
    palette = [TRANSPARENT] + [tuple(c) for c in palette[1:16]]
    shiny_path = os.path.join(unit["pal_dir"], "shiny.pal")
    shiny_pal = [TRANSPARENT] + [tuple(c) for c in mcss.load_pal(shiny_path)[1:16]] if os.path.exists(shiny_path) else None
    members, files, sheets, report = {}, {}, {}, {"faces": {}}
    for f in unit["faces"]:
        if not f.get("anim"):
            continue
        member, sheets[f["key"]], report["faces"][f["label"]] = build_mcss_face(
            f, palette, f["f"], f["lift"], unit.get("max_member", MAX_MEMBER))
        members[f["key"]] = member
    for f in unit["faces"]:
        sheet = sheets.get(f["key"]) if f["key"] in sheets else sheets.get(f.get("copy"))
        if f.get("png") and sheet is not None:
            files[f["png"]] = png_bytes(sheet, palette)
    if unit.get("normal_pal"):
        files[unit["normal_pal"]] = pal_bytes(palette)
    if unit.get("shiny_pal") and shiny_pal:
        files[unit["shiny_pal"]] = pal_bytes(shiny_pal)
    report["palette"] = os.path.relpath(unit["pal_dir"], mcss.BW2)
    return members, files, report


def unit_hash(unit):
    paths = []
    for f in unit["faces"]:
        if unit["kind"] == "gif":
            paths += [f.get("gif") or "", f.get("shiny") or ""]
        elif f.get("anim"):
            paths += anim_files(f["anim"], f["face"], f.get("female", False))
    if unit["kind"] == "mcss":
        paths += [os.path.join(unit["pal_dir"], "normal.pal"), os.path.join(unit["pal_dir"], "shiny.pal")]
    h = hashlib.sha1(files_hash(paths).encode())
    h.update(json.dumps(unit, sort_keys=True, default=str).encode())
    return h.hexdigest()


def build_cached(unit):
    path = os.path.join(BUILT, f"{unit['name']}-{unit_hash(unit)}.pkl")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return unit["name"], pickle.load(f)
    try:
        result = build_gif_unit(unit) if unit["kind"] == "gif" else build_mcss_unit(unit)
    except Exception as e:  # a bad source keeps the classic sprite
        import traceback
        return unit["name"], RuntimeError(f"{e}\n{traceback.format_exc()}")
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


def bw2_folders():
    """National dex number -> pokebw2 res/pokemon folder."""
    out = {}
    with open(BW2_SPECIES) as f:
        names = [line.split()[0] for line in f if line.startswith("SPECIES_")]
    for dex, name in enumerate(names):
        d = os.path.join(mcss.BW2, name[len("SPECIES_"):].lower())
        if dex and os.path.isdir(d) and mcss.has_face(d, "front") and mcss.has_face(d, "back"):
            out[dex] = d
    return out


def meson_text(name):
    with open(os.path.join(ROOT, "res/pokemon", name, "meson.build")) as f:
        return f.read()


def mcss_species_unit(name, sid, bw2):
    sdir = os.path.join(ROOT, "res/pokemon", name)
    built = meson_text(name)
    faces = []
    for face in ("back", "front"):
        # Female-only species (Blissey, Jynx, ...) build no male PNGs: the male member still
        # streams, through the female files' fallback
        png = os.path.join(sdir, f"male_{face}.png") if f"'male_{face}.png'" in built else None
        faces.append({"key": ("pokegra", sid * POKEGRA_FILES + FILE_OF["male", face]), "label": face,
                      "face": face, "anim": bw2, "png": png})
    for face in ("back", "front"):
        png = os.path.join(sdir, f"female_{face}.png")
        if not os.path.exists(png):
            continue
        f = {"key": ("pokegra", sid * POKEGRA_FILES + FILE_OF["female", face]), "label": "female_" + face,
             "face": face, "png": png, "copy": ("pokegra", sid * POKEGRA_FILES + FILE_OF["male", face])}
        if os.path.exists(os.path.join(bw2, f"{face}_female.png")):
            f.update(anim=bw2, female=True)
        faces.append(f)
    return {"name": name, "kind": "mcss", "species": name, "pal_dir": bw2, "faces": faces,
            "normal_pal": os.path.join(sdir, "normal.pal"), "shiny_pal": os.path.join(sdir, "shiny.pal"),
            "sprite_data": os.path.join(sdir, "sprite_data.json")}


def form_units(name, bw2):
    """A unit per palette file of a form species: its forms' faces at their PL_OTHERPOKE characters."""
    entries = {int(k): v for k, v in re.findall(r"'(\d+)': files\('([^']+)'\)", meson_text(name))}
    sdir = os.path.join(ROOT, "res/pokemon", name)
    forms = {}  # form -> {"back": char, "front": char, "normal": path, "shiny": path}
    for num, rel in entries.items():
        m = re.match(r"forms/(\w+)/(back\.png|front\.png|normal\.pal|shiny\.pal)$", rel)
        if not m or m.group(1) == "mega":
            continue
        forms.setdefault(m.group(1), {})[m.group(2).split(".")[0]] = num if rel.endswith(".png") else rel
    units = {}
    for form, info in forms.items():
        sub = FORM_BW2[name].get(form)
        if sub is None:
            continue  # no BW2 form (Arceus ???): classic
        pal_dir = os.path.join(bw2, sub)
        anim = bw2 if name in PALETTE_ONLY_FORMS else pal_dir
        if not mcss.has_face(anim, "front") or not os.path.exists(os.path.join(pal_dir, "normal.pal")):
            continue
        # Forms sharing a palette file (Unown, Deoxys) are one unit; BW2 shares theirs too
        normal = info.get("normal") or forms["base"]["normal"]
        unit = units.setdefault(normal, {
            "name": f"{name}-{os.path.basename(os.path.dirname(normal))}", "kind": "mcss", "species": name,
            "pal_dir": pal_dir, "faces": [], "normal_pal": os.path.join(sdir, normal),
            "shiny_pal": os.path.join(sdir, info.get("shiny") or forms["base"]["shiny"])})
        for face in ("back", "front"):
            unit["faces"].append({"key": ("otherpoke", info[face]), "label": f"{form}_{face}", "face": face,
                                  "anim": anim, "png": os.path.join(sdir, f"forms/{form}/{face}.png")})
    return list(units.values())


def otherpoke_count():
    """PL_OTHERPOKE's species files (every otherpoke_index key), which the shared files follow:
    substitute_back, substitute_front, substitute.pal, shadows (make_pl_otherpoke.py)."""
    top = -1
    for name in os.listdir(os.path.join(ROOT, "res/pokemon")):
        p = os.path.join(ROOT, "res/pokemon", name, "meson.build")
        if os.path.exists(p):
            for k in re.findall(r"'(\d+)': files\(", open(p).read()):
                top = max(top, int(k))
    return top + 1


def substitute_unit():
    first = otherpoke_count()
    shared = os.path.join(ROOT, "res/pokemon/.shared")
    faces = [{"key": ("otherpoke", first + i), "label": face, "face": face, "anim": SUBSTITUTE_BW2,
              "png": os.path.join(shared, f"substitute_{face}.png")} for i, face in enumerate(("back", "front"))]
    return {"name": "substitute", "kind": "mcss", "species": None, "pal_dir": SUBSTITUTE_BW2, "faces": faces,
            "normal_pal": os.path.join(shared, "substitute.pal"), "shiny_pal": None}


def gif_species_unit(name, sid):
    dex = DEX_OVERRIDE.get(name, sid)
    front, back = fetch("", dex), fetch("back/", dex)
    if not front or not back:
        return None
    sdir = os.path.join(ROOT, "res/pokemon", name)
    built = meson_text(name)
    faces = []
    for face, kind in (("back", "back/"), ("front", "")):
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
    return {"name": name, "kind": "gif", "species": name, "dex": dex, "faces": faces,
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


def set_sprite_data(path, lift):
    """y_offset is the blank rows under the static frame (the battle places the sprite that much
    lower): 0, the canvas stands the art on its ground row. addl_y_offset (the front's shadow height,
    which raises enemy fronts) becomes the species' lift; None keeps it (the GIF path)."""
    with open(path) as f:
        data = json.load(f)
    for face in ("front", "back"):
        for gender in data[face]["y_offset"]:
            data[face]["y_offset"][gender] = 0
    if lift is not None:
        data["front"]["addl_y_offset"] = int(lift)
    return write_if_changed(path, (json.dumps(data, indent=4) + "\n").encode())


def mega_list():
    """(base species, back character) of each Mega in src/pokemon_mega_data.c."""
    with open(os.path.join(ROOT, "src/pokemon_mega_data.c")) as f:
        text = f.read()
    return [(m.group(1).lower(), int(m.group(2)))
            for m in re.finditer(r"\.baseSpecies = SPECIES_(\w+),.*?\.spriteCharacter = (\d+),", text, re.S)]


def mega_still(name, face, base_h=None):
    """A Mega's still member from frame A of forms/mega/<face>.png (in the Mega's own palette),
    standing on the ground row: a back as tall as its base form's back (base_h source rows at
    BACK_SCALE, from 1.75x to 2x), a front at 1:1. Returns the member and its report."""
    sheet = np.array(Image.open(os.path.join(ROOT, "res/pokemon", name, f"forms/mega/{face}.png")))
    frame = sheet[:, :CLASSIC]
    l, t, r, b = bbox(frame != 0)
    crop, dx, dy = place((l, t, r, b), CANVAS_W)
    l, t, r, b = crop
    w, h = r - l, b - t
    if face == "back":
        scale = min(MAX_SCALE, max(BACK_SCALE, round(base_h * BACK_SCALE / h)))
    else:
        scale = SCALE_ONE
    canvas = np.zeros((CANVAS_H, CANVAS_W), dtype=np.uint8)
    canvas[dy:dy + h, dx:dx + w] = frame[t:b, l:r]
    box = (dx // 2, (w + 1) // 2, dy, h)
    member = stream_member([lz10(box_bytes(canvas, box))], [(0, 255)], box, scale)
    report = {"scale": scale / SCALE_ONE, "union": [w, h], "canvas_top": dy, "bytes": len(member)}
    if base_h is not None:
        report["base_union_h"] = base_h
    return member, report


HEIGHT_O = os.path.join(ROOT, "res/prebuilt/poketool/pokegra/height_o.narc")
SUBSTITUTE_HEIGHT_O = (134, 135)  # ov12_022380BC.c: the doll's back and front


def height_o_index(character):
    """LoadPokemonSpriteYOffset's HEIGHT_O member for a form's PL_OTHERPOKE character: the same up to
    the Egg, 2 more from Shaymin on (HEIGHT_O has the doll's two at 134 and 135)."""
    return character + 2 if character >= 134 else character


def zero_height_o(characters, extra=()):
    """The forms' y_offsets (HEIGHT_O) to 0 for every streamed form face: the canvas stands the art
    on its ground row, as sprite_data.json's y_offset does for the species."""
    from nitro import read_narc
    members = [bytearray(m) for m in read_narc(HEIGHT_O)]
    for idx in [height_o_index(c) for c in characters] + list(extra):
        members[idx][0] = 0
    tmp = HEIGHT_O + ".tmp"
    write_narc(tmp, [bytes(m) for m in members])
    with open(tmp, "rb") as f:
        data = f.read()
    os.remove(tmp)
    return write_if_changed(HEIGHT_O, data)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--species", nargs="+", help="only these species (names as in generated/species.txt; "
                    "'substitute' for the doll)")
    ap.add_argument("--seed", help="copy DIR/{anim,animback}/<dex>.gif into the GIF cache first")
    ap.add_argument("--jobs", type=int, default=min(64, os.cpu_count() or 1))
    ap.add_argument("--max-member", type=int, default=MAX_MEMBER, help="stream size cap in bytes")
    ap.add_argument("--gif", action="store_true", help="PokeAPI GIFs for every species (step 2 build)")
    ap.add_argument("--no-forms", action="store_true", help="no form, doll or Mega front streams (for bisecting)")
    args = ap.parse_args()
    if args.seed:
        seed(args.seed)

    names = species_list()
    wanted = set(args.species) if args.species else None
    if wanted and wanted - set(names) - {"substitute"}:
        sys.exit(f"unknown species: {sorted(wanted - set(names) - {'substitute'})}")
    folders = {} if args.gif else bw2_folders()
    units = []
    for sid, name in enumerate(names):
        if wanted and name not in wanted:
            continue
        dex = DEX_OVERRIDE.get(name, sid)
        bw2 = folders.get(dex)
        if name in FORM_SPECIES:
            if bw2 and not args.no_forms:
                units += form_units(name, bw2)
            continue
        if name in SKIP_SPECIES:
            continue
        u = mcss_species_unit(name, sid, bw2) if bw2 else gif_species_unit(name, sid)
        if u:
            units.append(u)
        else:
            print(f"{name}: no B/W art, classic")
    if not args.gif and not args.no_forms and (not wanted or "substitute" in wanted):
        units.append(substitute_unit())
    for u in units:
        u["max_member"] = args.max_member

    # Pass 1: every MCSS face's box, for the fits and the species' lifts
    specs = {face_spec_key(f): f for u in units if u["kind"] == "mcss" for f in u["faces"] if f.get("anim")}
    with Pool(args.jobs) as pool:
        boxes = dict(pool.imap_unordered(measure, specs.values()))
    lifts = {}
    for u in units:
        for f in u["faces"]:
            if u["kind"] != "mcss" or not f.get("anim"):
                continue
            m = boxes[face_spec_key(f)]
            f["f"] = front_shrink(m) if f["face"] == "front" else 1.0
            if f["face"] == "front" and u["species"]:
                own = max(0, -int(np.ceil(m["bottom"] * f["f"])))
                lifts[u["species"]] = min(lifts.get(u["species"], own), own)
    for u in units:
        for f in u["faces"]:
            if u["kind"] == "mcss" and f.get("anim"):
                f["lift"] = lifts.get(u["species"], 0) if f["face"] == "front" else 0

    with Pool(args.jobs) as pool:
        results = dict(pool.imap_unordered(build_cached, units))

    members = [b""]
    stored = {}
    pokegra = [0] * (len(names) * POKEGRA_FILES)
    otherpoke = []
    reports, changed = {}, 0

    streamed_otherpoke = set()

    def add_member(table, idx, m):
        if table is otherpoke:
            streamed_otherpoke.add(idx)
        table.extend([0] * (idx + 1 - len(table)))
        if m not in stored:
            stored[m] = len(members)
            members.append(m)
        table[idx] = stored[m]

    sprite_data_done = set()
    for u in units:
        res = results[u["name"]]
        if isinstance(res, Exception):
            print(f"{u['name']}: FAILED ({res}), classic")
            continue
        unit_members, files, report = res
        for f in u["faces"]:
            m = unit_members.get(f["key"])
            if m is not None:
                kind, idx = f["key"]
                add_member(pokegra if kind == "pokegra" else otherpoke, idx, m)
        for path, data in files.items():
            changed += write_if_changed(path, data)
        sd = u.get("sprite_data") or (os.path.join(ROOT, "res/pokemon", u["species"], "sprite_data.json")
                                      if u.get("species") else None)
        if sd and sd not in sprite_data_done:
            sprite_data_done.add(sd)
            lift = None if u["kind"] == "gif" else lifts.get(u["species"], 0)
            changed += set_sprite_data(sd, lift)
            report["lift"] = lift
        report["source"] = u["kind"]
        report["bytes"] = sum(len(m) for m in unit_members.values())
        reports[u["name"]] = report

    megas = {}
    for name, character in mega_list():
        if name not in reports:
            if not wanted:
                print(f"mega {name}: base form has no stream, classic")
            continue
        member, back = mega_still(name, "back", reports[name]["faces"]["back"]["union"][1])
        add_member(otherpoke, character, member)
        megas[name] = {"back": back}
        if not args.no_forms:
            member, megas[name]["front"] = mega_still(name, "front")
            add_member(otherpoke, character + 1, member)

    form_chars = [f["key"][1] for u in units if u["kind"] == "mcss" and u["species"] in FORM_SPECIES
                  for f in u["faces"] if f["key"][1] in streamed_otherpoke]
    if form_chars or any(u["name"] == "substitute" for u in units):
        changed += zero_height_o(form_chars, SUBSTITUTE_HEIGHT_O if any(u["name"] == "substitute" and
                                                                        u["name"] in reports for u in units) else ())

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

    faces = [(name, label, fr) for name, r in reports.items() for label, fr in r["faces"].items()]
    sizes = sorted((fr["bytes"], f"{name} {label}") for name, label, fr in faces)
    print(f"{len(reports)} units ({sum(1 for r in reports.values() if r['source'] == 'mcss')} from pokebw2) and "
          f"{len(megas)} Megas, {len(faces)} faces, {len(members) - 1} members, "
          f"{sum(len(m) for m in members[1:])} bytes of streams")
    print(f"{OUT}: {len(narc)} bytes; {changed} files changed")
    print("biggest:", ", ".join(f"{n} {s}" for s, n in sizes[::-1][:12]))
    for name, label, fr in sorted(faces):
        notes = []
        if fr.get("shrink", 1) != 1:
            notes.append(f"shrunk {fr['shrink']}")
        for k in ("cropped_rows", "cropped_bottom_rows", "cropped_cols", "dropped", "shift_x"):
            if fr.get(k):
                notes.append(f"{k} {fr[k]}")
        if notes:
            print(f"  {name} {label}: {', '.join(notes)}")


if __name__ == "__main__":
    main()

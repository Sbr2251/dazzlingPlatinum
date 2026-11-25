#!/usr/bin/env python3
"""Shared helpers for the Solaceon texture kit (tools/solaceon_town/art/). Standard library only.

- Stock inputs are read from git at BASE_REV (the arc2 merge every Solaceon workstream codes against), so re-running
  never feeds back on itself.
- Indexed images are plain lists of rows of palette indices; palettes are lists of (r, g, b) in 8-bit, snapped to the
  DS 5-5-5 grid by `snap`.
- `Canvas` is a tiny RGBA compositor for contact sheets (nearest-neighbour scaling and a 3x5 pixel font).
- Previews go to PREVIEW_DIR: $SOL_PREVIEW_DIR, else ~/Documents/Solaceon Update/textures, else (when that is not
  writable, e.g. a sandboxed session) /tmp/Solaceon Update/textures.
"""
import json
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402
import png  # noqa: E402

BASE_REV = "50482f890"
SET010_REL = "res/field/maps/texture_sets/map_texture_set_010.nsbtx"
AREABM_TEXSET_REL = "res/prebuilt/fielddata/areadata/area_build_model/areabm_texset.narc"
AREA_BUILD_REL = "res/prebuilt/fielddata/areadata/area_build_model/area_build.narc"
AREA_DATA_REL = "res/prebuilt/fielddata/areadata/area_data.narc"
BUILD_MODEL_REL = "res/prebuilt/fielddata/build_model/build_model.narc"
ASSET_DIR = os.path.join(ROOT, "tools", "solaceon_town", "assets", "textures")

# area data entry -> town, for the prop (building) texture sets compared in decode_stock.py
TOWN_AREAS = {0xA: "solaceon", 0x8: "eterna", 0x9: "hearthome", 0xB: "veilstone"}


def preview_dir(sub=""):
    cands = [os.environ.get("SOL_PREVIEW_DIR"), os.path.expanduser("~/Documents/Solaceon Update/textures"),
             "/tmp/Solaceon Update/textures"]
    for c in cands:
        if not c:
            continue
        d = os.path.join(c, sub) if sub else c
        try:
            os.makedirs(d, exist_ok=True)
            t = os.path.join(d, ".w")
            open(t, "w").close()
            os.remove(t)
            return d
        except OSError:
            continue
    raise SystemExit("no writable preview dir")


# ---------------------------------------------------------------------------------------------------------------
# stock data at BASE_REV
# ---------------------------------------------------------------------------------------------------------------

_cache = {}


def git_bytes(rel, rev=BASE_REV):
    key = (rev, rel)
    if key not in _cache:
        _cache[key] = subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{rel}"], check=True,
                                     capture_output=True).stdout
    return _cache[key]


def narc_files(rel):
    """Member files of an unnamed NARC (same layout as tools/coronet_lava/narc.read_files), read from git."""
    key = ("narc", rel)
    if key in _cache:
        return _cache[key]
    d = git_bytes(rel)
    assert d[:4] == b"NARC"
    hdr_size, n_sections = struct.unpack_from("<HH", d, 12)
    sections, o = {}, hdr_size
    for _ in range(n_sections):
        magic, size = d[o:o + 4], struct.unpack_from("<I", d, o + 4)[0]
        sections[magic] = d[o:o + size]
        o += size
    btaf, gmif = sections[b"BTAF"], sections[b"GMIF"]
    n = struct.unpack_from("<H", btaf, 8)[0]
    files = []
    for i in range(n):
        a, b = struct.unpack_from("<II", btaf, 12 + 8 * i)
        files.append(gmif[8 + a:8 + b])
    _cache[key] = files
    return files


def set010():
    return nsbtx.parse(git_bytes(SET010_REL))


def area_entry(area):
    props, tex, _, light = struct.unpack_from("<4H", narc_files(AREA_DATA_REL)[area])
    return props, tex, light


def area_props(props_list):
    raw = narc_files(AREA_BUILD_REL)[props_list]
    n = struct.unpack_from("<H", raw)[0]
    return list(struct.unpack_from("<%dH" % n, raw, 2))


def prop_texset(props_list):
    return nsbtx.parse(narc_files(AREABM_TEXSET_REL)[props_list])


def build_model(i):
    return nsbmd.parse_bmd(narc_files(BUILD_MODEL_REL)[i])["models"][0]


def map_model(chunk):
    import mapdata
    u = mapdata.unpack(git_bytes(f"res/field/maps/data/map_data_{chunk:03d}.bin"))
    return nsbmd.parse_bmd(u["model"])["models"][0], mapdata.read_props(u["props"])


def decode_rgba(tex, pal_colors):
    rows, _ = nsbtx.decode(tex, pal_colors)
    return [[tuple(p) for p in r] for r in rows]


def decode_indices(tex):
    _, idx = nsbtx.decode(tex, [0] * 256)
    return idx


def pal_rgb(pal):
    return [nsbtx.rgb(c) for c in pal["colors"]]


# ---------------------------------------------------------------------------------------------------------------
# colour
# ---------------------------------------------------------------------------------------------------------------

def snap(c):
    """8-bit RGB -> the colour the DS shows for it (5 bits per channel, expanded like nsbtx.rgb)."""
    return nsbtx.rgb(nsbtx.bgr555(tuple(max(0, min(255, int(round(v)))) for v in c)))


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def mix(a, b, t):
    return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))


def ramp(keys, t):
    t = max(0.0, min(1.0, t))
    n = len(keys) - 1
    i = min(int(t * n), n - 1)
    return mix(keys[i], keys[i + 1], t * n - i)


def remap_by_lum(colors, used, keys):
    """Stock colours -> the ramp `keys` by luminance, normalised over the indices the texels use (the same rule as
    tools/world_art/chunkedit.recolour), snapped to 5-5-5."""
    ls = [lum(colors[i]) for i in used]
    lo, hi = min(ls), max(ls)
    return [snap(ramp(keys, (lum(c) - lo) / (hi - lo) if hi > lo else 0.5)) for c in colors]


# ---------------------------------------------------------------------------------------------------------------
# lake_verity export format
# ---------------------------------------------------------------------------------------------------------------

def export_texture(name, idx, palette, fmt="pltt16", repeat=(True, True), c0=0, out_dir=ASSET_DIR, extra=None):
    """Indexed texture -> <out_dir>/<name>.png (indexed, 4-bit or 2-bit) + <name>.json, as
    tools/lake_verity/assets/README.md describes. palette: list of RGB (already snapped). pltt16 opaque textures never
    use index 0 (it stays a dark spare colour); c0=1 makes index 0 transparent."""
    h, w = len(idx), len(idx[0])
    n = {"pltt16": 16, "pltt4": 4}[fmt]
    used = {v for r in idx for v in r}
    assert max(used) < n, (name, max(used))
    assert len(palette) <= n, (name, len(palette))
    assert len(name) <= 15, name
    pal = [snap(c) for c in palette] + [(0, 0, 0)] * (n - len(palette))
    os.makedirs(out_dir, exist_ok=True)
    png.write_indexed(os.path.join(out_dir, name + ".png"), w, h, idx, pal, bits=4 if n == 16 else 2,
                      transparent0=bool(c0))
    meta = {"format": fmt, "repeat": [bool(repeat[0]), bool(repeat[1])], "c0": int(c0),
            "color0_transparent": bool(c0)}
    meta.update(extra or {})
    json.dump(meta, open(os.path.join(out_dir, name + ".json"), "w"), indent=1)
    return meta


def export_a3i5(name, rgba_rows, repeat=(False, False), out_dir=ASSET_DIR, extra=None):
    """RGBA rows (RGB snapped, alpha quantised to 8 levels) -> <name>.png RGBA + <name>.json (format a3i5)."""
    h, w = len(rgba_rows), len(rgba_rows[0])
    cols = set()
    out = []
    for r in rgba_rows:
        row = []
        for p in r:
            a = round(p[3] * 7 / 255) * 255 // 7
            c = snap(p[:3]) if a else (0, 0, 0)
            cols.add(c)
            row.append(c + (a,))
        out.append(row)
    assert len(cols) <= 32, (name, len(cols))
    png.write_rgba(os.path.join(out_dir, name + ".png"), w, h, out)
    meta = {"format": "a3i5", "repeat": [bool(repeat[0]), bool(repeat[1])], "c0": 0, "color0_transparent": False}
    meta.update(extra or {})
    json.dump(meta, open(os.path.join(out_dir, name + ".json"), "w"), indent=1)
    return meta


# ---------------------------------------------------------------------------------------------------------------
# contact sheets
# ---------------------------------------------------------------------------------------------------------------

_FONT = {
    "A": "010101111101101", "B": "110101110101110", "C": "011100100100011", "D": "110101101101110",
    "E": "111100110100111", "F": "111100110100100", "G": "011100101101011", "H": "101101111101101",
    "I": "111010010010111", "J": "001001001101010", "K": "101101110101101", "L": "100100100100111",
    "M": "101111111101101", "N": "110101101101101", "O": "010101101101010", "P": "110101110100100",
    "Q": "010101101110011", "R": "110101110101101", "S": "011100010001110", "T": "111010010010010",
    "U": "101101101101111", "V": "101101101101010", "W": "101101111111101", "X": "101101010101101",
    "Y": "101101010010010", "Z": "111001010100111", "0": "111101101101111", "1": "010110010010111",
    "2": "110001010100111", "3": "110001010001110", "4": "101101111001001", "5": "111100110001110",
    "6": "011100111101111", "7": "111001010010010", "8": "111101111101111", "9": "111101111001110",
    "_": "000000000000111", "-": "000000111000000", ".": "000000000000010", ":": "000010000010000",
    "/": "001001010100100", "(": "010100100100010", ")": "010001001001010", "+": "000010111010000",
    "#": "101111101111101", "=": "000111000111000", ",": "000000000010100", "'": "010010000000000",
    "%": "101001010100101", "<": "001010100010001", ">": "100010001010100", "?": "110001010000010",
    " ": "000000000000000",
}


class Canvas:
    def __init__(self, w, h, bg=(24, 24, 32)):
        self.w, self.h = w, h
        self.px = [[tuple(bg) + (255,)] * w for _ in range(h)]

    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            if len(c) == 4 and c[3] < 255:
                if c[3] == 0:
                    return
                b = self.px[y][x]
                a = c[3] / 255
                c = tuple(int(b[k] + (c[k] - b[k]) * a) for k in range(3)) + (255,)
            self.px[y][x] = tuple(c[:3]) + (255,)

    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.put(xx, yy, c)

    def blit(self, rgba, x, y, scale=1, checker=True):
        for yy, row in enumerate(rgba):
            for xx, p in enumerate(row):
                for dy in range(scale):
                    for dx in range(scale):
                        if checker and len(p) == 4 and p[3] < 255:
                            ch = (72, 72, 80) if ((xx * scale + dx) // 4 + (yy * scale + dy) // 4) % 2 else (96, 96, 104)
                            self.put(x + xx * scale + dx, y + yy * scale + dy, ch)
                        self.put(x + xx * scale + dx, y + yy * scale + dy, p)

    def text(self, x, y, s, c=(230, 230, 230), scale=1):
        for ch in s.upper():
            g = _FONT.get(ch, _FONT["?"])
            for k, bit in enumerate(g):
                if bit == "1":
                    self.rect(x + (k % 3) * scale, y + (k // 3) * scale, scale, scale, c)
            x += 4 * scale
        return x

    def swatches(self, x, y, colors, size=6):
        for k, c in enumerate(colors):
            self.rect(x + k * size, y, size - 1, size - 1, tuple(c[:3]))

    def save(self, path):
        png.write_rgba(path, self.w, self.h, self.px)


def contact_sheet(path, items, title, cols=6, cell=136, scale_to=128):
    """items: [(label lines list, rgba rows, palette colours or None)]. Each texture scaled by an integer factor to
    fit scale_to px, label lines under it, palette swatches under the labels."""
    rows = (len(items) + cols - 1) // cols
    ch = scale_to + 32
    cv = Canvas(cols * cell + 8, rows * ch + 24)
    cv.text(6, 6, title, (255, 230, 150), 2)
    for k, (labels, rgba, pal) in enumerate(items):
        x0 = 8 + (k % cols) * cell
        y0 = 24 + (k // cols) * ch
        h, w = len(rgba), len(rgba[0])
        s = max(1, min(scale_to // w, scale_to // h))
        cv.rect(x0 - 1, y0 - 1, w * s + 2, h * s + 2, (60, 60, 70))
        cv.blit(rgba, x0, y0, s)
        ty = y0 + h * s + 3
        for ln in labels[:2]:
            cv.text(x0, ty, ln[:33])
            ty += 7
        if pal:
            cv.swatches(x0, ty, pal[:16], 7)
    cv.save(path)
    return path

#!/usr/bin/env python3
"""NSBTX (BTX0 / TEX0) reader, builder and PNG converter for map texture sets. See docs/lake_verity_redesign/pipeline.md.

Standard library only.

TEX0 header (0x3C bytes, offsets from the TEX0 block):
  0x00 'TEX0'  0x04 u32 block size          0x08 u32 0
  0x0C u16 texel data size >> 3             0x0E u16 texture dictionary offset   0x10 u32 0   0x14 u32 texel data offset
  0x18 u32 0   0x1C u16 4x4 texel size >> 3 0x1E u16 texture dictionary offset (again)  0x20 u32 0
  0x24 u32 4x4 texel data offset            0x28 u32 4x4 palette-index data offset       0x2C u32 0
  0x30 u16 palette data size >> 3           0x32 u16 0x8000 or 0 0x34 u32 palette dictionary offset   0x38 u32 palette data offset
Texture dictionary entries are 8 bytes: u32 TEXIMAGE_PARAM (offset>>3 | size | format | colour-0-transparent) and
u32 (width | height << 11 | 0x80000000). Palette dictionary entries are 4 bytes: u16 offset >> 3, u16 1 for a
4-colour palette (its hardware base is in 8-byte units; other palettes are 16-byte aligned).

Formats: 1 a3i5, 2 pltt4, 3 pltt16, 4 pltt256, 5 tex4x4, 6 a5i3, 7 direct.

Usage:
  python3 tools/lake_verity/nsbtx.py info <set.nsbtx>
  python3 tools/lake_verity/nsbtx.py decode <set.nsbtx> <out_dir> [map_data_NNN.bin ...]
      writes <texture>.png (indexed when paletted) + <texture>.json; the map models name the palette of each
      texture (texture and palette names differ, e.g. tree04_2 -> tree01); unmatched textures try the same name,
      name + "_pl", or the only palette with that prefix.
  python3 tools/lake_verity/nsbtx.py build <out.nsbtx> <texture_dir> [name ...]
      builds a set from <name>.png + <name>.json files (see encode_texture)
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "coronet_lava"))

from nsbmd import dict_build  # noqa: E402  (nnsdict.build with g3dcvtr node numbering)
import png  # noqa: E402

FMT_NAMES = {1: "a3i5", 2: "pltt4", 3: "pltt16", 4: "pltt256", 5: "tex4x4", 6: "a5i3", 7: "direct"}
FMT_IDS = {v: k for k, v in FMT_NAMES.items()}
BPP = {1: 8, 2: 2, 3: 4, 4: 8, 5: 2, 6: 8, 7: 16}
SIZES = {8: 0, 16: 1, 32: 2, 64: 3, 128: 4, 256: 5, 512: 6, 1024: 7}


def rgb(c):
    return ((c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31)


def bgr555(c):
    return (c[0] >> 3) | (c[1] >> 3) << 5 | (c[2] >> 3) << 10


def _dict(tex, o):
    n = tex[o + 1]
    dh = o + struct.unpack_from("<H", tex, o + 6)[0]
    esz, no = struct.unpack_from("<HH", tex, dh)
    return [(tex[dh + no + 16 * i:dh + no + 16 * i + 16].rstrip(b"\0").decode("latin1"),
             tex[dh + 4 + esz * i:dh + 4 + esz * (i + 1)]) for i in range(n)]


def texel_size(fmt, w, h):
    return w * h * BPP[fmt] // 8


def parse(data):
    """-> {"textures": [...], "palettes": [...], "header": {...}}. A texture carries its raw texels ("data", plus
    "index" for 4x4) and its offset; a palette carries its raw bytes (up to the next palette) and its offset."""
    if data[:4] == b"BTX0" or data[:4] == b"BMD0":
        n = struct.unpack_from("<H", data, 14)[0]
        offs = struct.unpack_from("<%dI" % n, data, 16)
        t = next(o for o in offs if data[o:o + 4] == b"TEX0")
    else:
        t = 0
    tex = data[t:t + struct.unpack_from("<I", data, t + 4)[0]]
    u16 = lambda o: struct.unpack_from("<H", tex, o)[0]  # noqa: E731
    u32 = lambda o: struct.unpack_from("<I", tex, o)[0]  # noqa: E731
    hdr = dict(tex_size=u16(0x0C) << 3, tex_dict=u16(0x0E), tex_data=u32(0x14), cmp_size=u16(0x1C) << 3,
               cmp_data=u32(0x24), cmp_index=u32(0x28), pal_size=u16(0x30) << 3, pal_flag=u16(0x32), pal_dict=u32(0x34),
               pal_data=u32(0x38))
    textures = []
    for name, e in _dict(tex, hdr["tex_dict"]):
        p, extra = struct.unpack("<II", e)
        fmt, w, h = (p >> 26) & 7, 8 << ((p >> 20) & 7), 8 << ((p >> 23) & 7)
        off = (p & 0xFFFF) << 3
        size = texel_size(fmt, w, h)
        tx = dict(name=name, fmt=fmt, w=w, h=h, c0=(p >> 29) & 1, off=off, param=p, extra=extra)
        if fmt == 5:
            tx["data"] = tex[hdr["cmp_data"] + off:hdr["cmp_data"] + off + size]
            tx["index"] = tex[hdr["cmp_index"] + off // 2:hdr["cmp_index"] + off // 2 + size // 2]
        else:
            tx["data"] = tex[hdr["tex_data"] + off:hdr["tex_data"] + off + size]
        textures.append(tx)
    pents = _dict(tex, hdr["pal_dict"])
    offs = sorted({struct.unpack("<H", e[:2])[0] << 3 for _, e in pents}) + [hdr["pal_size"]]
    palettes = []
    for name, e in pents:
        off, flag = struct.unpack("<HH", e)
        off <<= 3
        end = offs[offs.index(off) + 1]
        raw = tex[hdr["pal_data"] + off:hdr["pal_data"] + end]
        palettes.append(dict(name=name, off=off, pltt4=flag & 1, flag=flag, data=raw,
                             colors=list(struct.unpack("<%dH" % (len(raw) // 2), raw))))
    return {"textures": textures, "palettes": palettes, "header": hdr}


def decode(tx, pal):
    """Texture dict (from parse) + palette colours (bgr555 list, may be None for direct) ->
    (rgba rows, index rows or None)."""
    w, h, f, d = tx["w"], tx["h"], tx["fmt"], tx["data"]
    P = lambda i: rgb(pal[i]) if pal and i < len(pal) else (255, 0, 255)  # noqa: E731
    px, idx = [], None
    if f in (2, 3, 4):
        bpp = BPP[f]
        per = 8 // bpp
        idx = [[(d[(y * w + x) // per] >> (((y * w + x) % per) * bpp)) & ((1 << bpp) - 1) for x in range(w)]
               for y in range(h)]
        px = [[P(v) + ((0,) if tx["c0"] and v == 0 else (255,)) for v in row] for row in idx]
    elif f in (1, 6):
        idx = []
        for y in range(h):
            row, irow = [], []
            for x in range(w):
                b = d[y * w + x]
                v, a = (b & 31, (b >> 5) * 255 // 7) if f == 1 else (b & 7, (b >> 3) * 255 // 31)
                row.append(P(v) + (a,))
                irow.append(v)
            px.append(row)
            idx.append(irow)
    elif f == 7:
        for y in range(h):
            px.append([rgb(c) + ((255,) if c & 0x8000 else (0,)) for c in
                       struct.unpack_from("<%dH" % w, d, 2 * y * w)])
    elif f == 5:
        px = [[(0, 0, 0, 0)] * w for _ in range(h)]
        bw = w // 4
        for k in range(w * h // 16):
            by, bx = divmod(k, bw)
            blk = struct.unpack_from("<I", d, 4 * k)[0]
            ix = struct.unpack_from("<H", tx["index"], 2 * k)[0]
            base, mode = (ix & 0x3FFF) * 2, ix >> 14
            c0, c1 = P(base), P(base + 1)
            if mode == 0:
                cs = [c0, c1, P(base + 2), None]
            elif mode == 1:
                cs = [c0, c1, tuple((a + b) // 2 for a, b in zip(c0, c1)), None]
            elif mode == 2:
                cs = [c0, c1, P(base + 2), P(base + 3)]
            else:
                cs = [c0, c1, tuple((5 * a + 3 * b) // 8 for a, b in zip(c0, c1)),
                      tuple((3 * a + 5 * b) // 8 for a, b in zip(c0, c1))]
            for i in range(16):
                c = cs[(blk >> (2 * i)) & 3]
                px[by * 4 + i // 4][bx * 4 + i % 4] = c + (255,) if c else (0, 0, 0, 0)
    return px, idx


# ---------------------------------------------------------------------------------------------------------------
# builder
# ---------------------------------------------------------------------------------------------------------------

def build(textures, palettes, keep_offsets=False, pal_flag=0x8000):
    """textures: [{name, fmt, w, h, c0, data, index (4x4 only), off (used when keep_offsets)}];
    palettes: [{name, colors (bgr555) or data, pltt4 (0/1), off (used when keep_offsets)}].
    Without keep_offsets, texel blocks are laid out in list order (8-byte aligned) and palettes in list order
    (16-byte aligned, 8 for 4-colour palettes); identical texel / palette data is shared, like g3dcvtr does.
    Returns BTX0 bytes."""
    def pdata(p):
        return p["data"] if "data" in p else struct.pack("<%dH" % len(p["colors"]), *p["colors"])

    # texel areas
    tex_blob, cmp_blob, idx_blob = bytearray(), bytearray(), bytearray()
    seen, tex_offs = {}, []
    for t in textures:
        d = bytes(t["data"])
        assert len(d) == texel_size(t["fmt"], t["w"], t["h"]), t["name"]
        if t["fmt"] == 5:
            key = (5, d, bytes(t["index"]))
            if keep_offsets:
                off = t["off"]
            elif key in seen:
                off = seen[key]
            else:
                off = len(cmp_blob)
            seen.setdefault(key, off)
            end = off + len(d)
            cmp_blob.extend(b"\0" * max(0, end - len(cmp_blob)))
            cmp_blob[off:end] = d
            io = off // 2
            idx_blob.extend(b"\0" * max(0, io + len(t["index"]) - len(idx_blob)))
            idx_blob[io:io + len(t["index"])] = t["index"]
        else:
            key = (0, d)
            if keep_offsets:
                off = t["off"]
            elif key in seen:
                off = seen[key]
            else:
                tex_blob.extend(b"\0" * (-len(tex_blob) % 8))
                off = len(tex_blob)
            seen.setdefault(key, off)
            end = off + len(d)
            tex_blob.extend(b"\0" * max(0, end - len(tex_blob)))
            tex_blob[off:end] = d
        tex_offs.append(off)
    tex_blob.extend(b"\0" * (-len(tex_blob) % 8))
    cmp_blob.extend(b"\0" * (-len(cmp_blob) % 8))
    idx_blob.extend(b"\0" * (-len(idx_blob) % 4))
    # palettes
    pal_blob, pseen, pal_offs = bytearray(), {}, []
    for p in palettes:
        d = pdata(p)
        if keep_offsets:
            off = p["off"]
        elif d in pseen:
            off = pseen[d]
        else:
            pal_blob.extend(b"\0" * (-len(pal_blob) % (8 if p.get("pltt4") else 16)))
            off = len(pal_blob)
        pseen.setdefault(d, off)
        pal_blob.extend(b"\0" * max(0, off + len(d) - len(pal_blob)))
        pal_blob[off:off + len(d)] = d
        pal_offs.append(off)
    pal_blob.extend(b"\0" * (-len(pal_blob) % 8))
    # dictionaries
    tents = []
    for t, off in zip(textures, tex_offs):
        p = (off >> 3) | SIZES[t["w"]] << 20 | SIZES[t["h"]] << 23 | t["fmt"] << 26 | (1 << 29 if t.get("c0") else 0)
        extra = t.get("extra", t["w"] | t["h"] << 11 | 0x80000000)
        tents.append(struct.pack("<II", p, extra))
    pents = [struct.pack("<HH", off >> 3, p.get("flag", 1 if p.get("pltt4") else 0)) for p, off in zip(palettes, pal_offs)]
    tdict = dict_build([t["name"] for t in textures], tents)
    pdict = dict_build([p["name"] for p in palettes], pents)
    tex_dict_o = 0x3C
    pal_dict_o = tex_dict_o + len(tdict)
    tex_data_o = pal_dict_o + len(pdict)
    cmp_data_o = tex_data_o + len(tex_blob)
    cmp_idx_o = cmp_data_o + len(cmp_blob)
    pal_data_o = cmp_idx_o + len(idx_blob)
    size = pal_data_o + len(pal_blob)
    hdr = struct.pack("<4sII", b"TEX0", size, 0)
    hdr += struct.pack("<HHII", len(tex_blob) >> 3, tex_dict_o, 0, tex_data_o)
    hdr += struct.pack("<IHHIII", 0, len(cmp_blob) >> 3, tex_dict_o, 0, cmp_data_o, cmp_idx_o)
    hdr += struct.pack("<IHHII", 0, len(pal_blob) >> 3, pal_flag, pal_dict_o, pal_data_o)   # 0x8000 in 65 of 75 stock sets
    tex0 = hdr + tdict + pdict + bytes(tex_blob) + bytes(cmp_blob) + bytes(idx_blob) + bytes(pal_blob)
    return struct.pack("<4sHHIHHI", b"BTX0", 0xFEFF, 1, 0x14 + len(tex0), 0x10, 1, 0x14) + tex0


def vram_usage(parsed):
    """(texel bytes incl. 4x4 texels + index, palette bytes) that the set occupies in texture / palette VRAM."""
    h = parsed["header"]
    return h["tex_size"] + h["cmp_size"] + h["cmp_size"] // 2, h["pal_size"]


# ---------------------------------------------------------------------------------------------------------------
# PNG -> texture encoding
# ---------------------------------------------------------------------------------------------------------------

def _palette_from(img, maxn, keep_alpha=False):
    """(palette RGB list, index rows). Uses the PNG's own palette/indices when indexed, else collects exact
    colours (fails if there are more than maxn)."""
    if img.indices is not None:
        pal = [c[:3] for c in img.palette]
        n = max(max(r) for r in img.indices) + 1
        assert n <= maxn, f"texture uses {n} palette entries, format allows {maxn}"
        return pal[:max(n, 1)], img.indices
    cols, rows = [], []
    for row in img.pixels:
        r = []
        for p in row:
            c = tuple(v >> 3 << 3 for v in p[:3])
            if c not in cols:
                cols.append(c)
            r.append(cols.index(c))
        rows.append(r)
    assert len(cols) <= maxn, f"{len(cols)} colours, format allows {maxn} (quantise the PNG first)"
    return cols, rows


def encode_texture(name, img, fmt, c0=None):
    """png.Image + format name -> (texture dict, palette dict or None). For pltt4/16/256 the PNG should be indexed
    (index 0 transparent when c0); a3i5/a5i3 take the colour from the palette index (or exact colours) and the
    alpha from the pixel alpha; direct takes RGB + alpha >= 128."""
    f = FMT_IDS[fmt]
    w, h = img.width, img.height
    assert w in SIZES and h in SIZES and 8 <= w <= 1024 and 8 <= h <= 1024, (name, w, h)
    if f == 7:
        d = b"".join(struct.pack("<H", bgr555(p) | (0x8000 if p[3] >= 128 else 0)) for row in img.pixels for p in row)
        return dict(name=name, fmt=7, w=w, h=h, c0=0, data=d), None
    if f == 5:
        return encode_4x4(name, img)
    maxn = {1: 32, 2: 4, 3: 16, 4: 256, 6: 8}[f]
    pal, idx = _palette_from(img, maxn)
    if c0 is None:
        c0 = int(img.palette is not None and img.palette[0][3] == 0) if f in (2, 3, 4) else 0
    out = bytearray()
    if f in (2, 3, 4):
        bpp = BPP[f]
        per = 8 // bpp
        flat = [v for row in idx for v in row]
        for i in range(0, len(flat), per):
            b = 0
            for k in range(per):
                b |= flat[i + k] << (k * bpp)
            out.append(b)
    else:
        for y in range(h):
            for x in range(w):
                a = img.pixels[y][x][3]
                v = idx[y][x]
                out.append(v | (round(a * 7 / 255) << 5) if f == 1 else v | (round(a * 31 / 255) << 3))
    n = {2: 4, 3: 16, 4: 256, 1: 32, 6: 8}[f]
    pal = list(pal) + [(0, 0, 0)] * (n - len(pal)) if f == 2 else list(pal) + [(0, 0, 0)] * (-len(pal) % 4)
    colors = [bgr555(c) for c in pal]
    return dict(name=name, fmt=f, w=w, h=h, c0=int(bool(c0)), data=bytes(out)), \
        dict(name=name + "_pl", colors=colors, pltt4=int(f == 2))


def encode_4x4(name, img):
    """Simple 4x4-compressed encoder: each 4x4 block gets its two extreme colours plus the two hardware blends
    (mode 3), or mode 1 (two colours, their midpoint, transparent) when the block has transparent texels.
    Block palettes are shared when identical. Good enough for graybox / soft textures; not a quality encoder."""
    w, h = img.width, img.height
    blocks, index, pal, seen = bytearray(), bytearray(), [], {}
    for by in range(h // 4):
        for bx in range(w // 4):
            px = [img.pixels[by * 4 + i // 4][bx * 4 + i % 4] for i in range(16)]
            opaque = [p[:3] for p in px if p[3] >= 128]
            trans = len(opaque) < 16
            if not opaque:
                opaque = [(0, 0, 0)]
            lum = lambda c: 3 * c[0] + 6 * c[1] + c[2]  # noqa: E731
            a, b = min(opaque, key=lum), max(opaque, key=lum)
            a5, b5 = rgb(bgr555(a)), rgb(bgr555(b))
            if trans:
                cand = [a5, b5, tuple((x + y) // 2 for x, y in zip(a5, b5))]
                mode = 1
            else:
                cand = [a5, b5, tuple((5 * x + 3 * y) // 8 for x, y in zip(a5, b5)),
                        tuple((3 * x + 5 * y) // 8 for x, y in zip(a5, b5))]
                mode = 3
            word = 0
            for i, p in enumerate(px):
                if p[3] < 128:
                    v = 3
                else:
                    v = min(range(len(cand)), key=lambda k: sum((cand[k][j] - p[j]) ** 2 for j in range(3)))
                word |= v << (2 * i)
            blocks += struct.pack("<I", word)
            key = (bgr555(a), bgr555(b))
            if key not in seen:
                seen[key] = len(pal) // 2
                pal += list(key)
            index += struct.pack("<H", seen[key] | mode << 14)
    return dict(name=name, fmt=5, w=w, h=h, c0=0, data=bytes(blocks), index=bytes(index)), \
        dict(name=name + "_pl", colors=pal + [0] * (-len(pal) % 4), pltt4=0)


def load_texture_dir(tex_dir, names=None):
    """<name>.png + <name>.json ({"format", "repeat", optional "palette" name, "c0"}) -> (textures, palettes)."""
    names = names or sorted(f[:-4] for f in os.listdir(tex_dir) if f.endswith(".png"))
    textures, palettes = [], []
    for n in names:
        meta = {}
        jp = os.path.join(tex_dir, n + ".json")
        if os.path.exists(jp):
            meta = json.load(open(jp))
        t, p = encode_texture(n, png.read(os.path.join(tex_dir, n + ".png")), meta.get("format", "pltt16"),
                              meta.get("c0"))
        textures.append(t)
        if p:
            p["name"] = meta.get("palette", p["name"])
            palettes.append(p)
    return textures, palettes


# ---------------------------------------------------------------------------------------------------------------
# texture -> palette pairing
# ---------------------------------------------------------------------------------------------------------------

def pairs_from_models(paths):
    """{texture: palette} from the material bindings of NSBMD / map_data files."""
    import nsbmd
    out = {}
    for p in paths:
        for m in nsbmd.parse_bmd(nsbmd.map_model_bytes(p))["models"]:
            for mat in m["materials"]:
                if mat["texture"] and mat["palette"]:
                    out.setdefault(mat["texture"], mat["palette"])
    return out


# texture -> palette names in stock sets that no chunk model of Lake Verity binds and no name rule finds
KNOWN_PAIRS = {"allpeak": "apeak", "nbridge": "dun_bridge"}


def guess_palette(tex_name, pal_names, pairs):
    if tex_name in pairs and pairs[tex_name] in pal_names:
        return pairs[tex_name]
    if KNOWN_PAIRS.get(tex_name) in pal_names:
        return KNOWN_PAIRS[tex_name]
    for cand in (tex_name, tex_name + "_pl", tex_name.split(".")[0] + "_pl", tex_name.rstrip("0123456789_")):
        if cand in pal_names:
            return cand
    pre = [p for p in pal_names if p.startswith(tex_name[:4])]
    return pre[0] if len(pre) == 1 else None


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "info":
        s = parse(open(sys.argv[2], "rb").read())
        tv, pv = vram_usage(s)
        for t in s["textures"]:
            print(f"{t['name']:16s} {FMT_NAMES[t['fmt']]:8s} {t['w']:4d}x{t['h']:<4d} c0={t['c0']} off={t['off']} "
                  f"bytes={len(t['data'])}")
        for p in s["palettes"]:
            print(f"  pal {p['name']:16s} off={p['off']} colours={len(p['colors'])} pltt4={p['pltt4']}")
        print(f"{len(s['textures'])} textures, {len(s['palettes'])} palettes; texture VRAM {tv} bytes, "
              f"palette VRAM {pv} bytes")
    elif cmd == "decode":
        s = parse(open(sys.argv[2], "rb").read())
        out = sys.argv[3]
        os.makedirs(out, exist_ok=True)
        pairs = pairs_from_models(sys.argv[4:])
        pals = {p["name"]: p["colors"] for p in s["palettes"]}
        for t in s["textures"]:
            pn = guess_palette(t["name"], pals, pairs)
            px, idx = decode(t, pals.get(pn))
            fn = os.path.join(out, t["name"] + ".png")
            if idx is not None and t["fmt"] in (2, 3, 4):
                colors = [rgb(c) for c in (pals.get(pn) or [])][:1 << BPP[t["fmt"]]] or [(255, 0, 255)]
                colors += [(0, 0, 0)] * (max(max(r) for r in idx) + 1 - len(colors))
                png.write_indexed(fn, t["w"], t["h"], idx, colors, bits=max(2, BPP[t["fmt"]]) if BPP[t["fmt"]] > 2 else 2,
                                  transparent0=bool(t["c0"]))
            else:
                png.write_rgba(fn, t["w"], t["h"], px)
            json.dump({"format": FMT_NAMES[t["fmt"]], "repeat": [True, True], "palette": pn, "c0": t["c0"]},
                      open(os.path.join(out, t["name"] + ".json"), "w"))
        print(f"decoded {len(s['textures'])} textures to {out}")
    elif cmd == "build":
        tex, pal = load_texture_dir(sys.argv[3], sys.argv[4:] or None)
        open(sys.argv[2], "wb").write(build(tex, pal))
        print(f"wrote {sys.argv[2]}")


if __name__ == "__main__":
    main()

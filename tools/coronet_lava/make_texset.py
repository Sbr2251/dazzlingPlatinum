"""Builds texture set 074 (Mt. Coronet 1F South lava) from set 068. See docs/coronet_1f_lava/PLAN.md, Step 2.

Usage: python3 tools/coronet_lava/make_texset.py [--sheet]
  Writes res/field/maps/texture_sets/map_texture_set_074.nsbtx.
  --sheet also writes a before/after contact sheet to $OUT_DIR (default /tmp/coronet_lava; needs Pillow).

Rock and floor textures are recoloured by rewriting their palettes in place (texels untouched).
dun_sea gets the lava tile from make_lava.py. Its stock palette slot only holds 8 colours, so a new
16-colour palette is appended to the end of the palette block and dun_sea's palette dictionary entry
is repointed at it. Palette data is the last thing in TEX0, so nothing else moves.
The dun_sea texture (not its palette) is renamed to dun_mag: fldtanime.narc animates any texture named
dun_sea with water frames, and add_lava_anim.py registers lava frames under dun_mag instead.
dun_sside (the shore rim) gets new texels and palette from make_lava.py.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import btx  # noqa: E402
import make_lava  # noqa: E402
import nnsdict  # noqa: E402

ROOT = os.path.join(HERE, "..", "..")
SRC = os.path.join(ROOT, "res/field/maps/texture_sets/map_texture_set_068.nsbtx")
DST = os.path.join(ROOT, "res/field/maps/texture_sets/map_texture_set_074.nsbtx")

CLIFF = [(20, 18, 32), (39, 35, 60), (52, 47, 78), (66, 60, 96), (82, 76, 115)]
FLOOR = [(42, 32, 40), (56, 44, 54), (66, 52, 64), (78, 62, 74), (92, 74, 86)]
HANGER = [CLIFF[0], CLIFF[2], (170, 60, 18), (240, 120, 30), (255, 190, 80)]
OBSIDIAN = [(8, 6, 12), (20, 17, 30), (36, 32, 52), (62, 56, 86), (118, 108, 150)]

# (ramp, palette names) groups; each group is luminance-mapped onto its ramp
CLIFF_PALS = ["dun_wall_c", "dun_wall_e", "dun_wall_n", "dun_wall_s", "dun_wall_w", "dun_level", "dun_step",
              "dun_jump", "dun_down", "dun_apeak", "dun_slope", "wallsp1_01", "wallsp1_02", "wallsp1_03",
              "wallsp1_04", "wallsp1_05", "wallsp1_c"]
# holes, entrances and the lit wall variants carry a light gradient toward the exits; its bright end is kept
GLOW_PALS = ["dun_dhole", "dun_dhole2", "dun_dhole3", "dun_ent", "dun_ent2", "dun_ent3", "dun_wall_c2",
             "dun_wall_e2", "dun_wall_n2", "dun_wall_s2", "dun_wall_w2"]
FLOOR_PALS = ["dun_floor", "dun_floor2", "dun_floor3"]  # dun_floor4 shares dun_floor3's palette
GROUPS = [
    (CLIFF, CLIFF_PALS + GLOW_PALS),
    (FLOOR, FLOOR_PALS),
    (HANGER, ["dun_hanger"]),
    (OBSIDIAN, ["searock", "dun_imped"]),
]
# palettes whose index 0 is the transparent colour of a colour-0-transparent texture
TRANSPARENT0 = {"dun_apeak", "dun_dhole", "dun_dhole2", "dun_dhole3", "dun_down", "searock", "seaside3",
                "dun_imped", "bridge", "dun_bridge"}
# glow colours (stock luminance >= GLOW_LO) map onto a warm ember ramp instead of the stock white
GLOW_LO = 150
GLOW = [CLIFF[-1], (132, 74, 72), (196, 118, 84), (228, 166, 118)]
# dun_light is the translucent light shaft at the exits; stock is flat white
LIGHT = (232, 160, 108)
LAVA_TEX = b"dun_mag"
# textures whose palette name differs from the texture name
PAL_OF_TEX = {"dun_allpeak": "dun_apeak", "dun_sside": "seaside3", "dun_srock": "searock",
              "dun_shadow": "shadowchip", "dun_mag": "dun_sea"}


def lum(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def ramp(t, stops):
    t = max(0.0, min(1.0, t))
    f = t * (len(stops) - 1)
    i = min(int(f), len(stops) - 2)
    u = f - i
    a, b = stops[i], stops[i + 1]
    return tuple(round(a[k] + (b[k] - a[k]) * u) for k in range(3))


def rgb(c):
    return ((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3)


class TexSet:
    def __init__(self, data):
        self.d = bytearray(data)
        self.t = struct.unpack_from("<I", self.d, 16)[0]
        self.tex, self.info, self.texs, pals = btx.load_bytes(bytes(self.d))
        self.pal_off = dict(pals)
        pal_end = struct.unpack_from("<H", self.d, self.t + 0x30)[0] << 3
        offs = sorted(set(self.pal_off.values())) + [pal_end]
        self.pal_len = {o: (offs[offs.index(o) + 1] - o) // 2 for o in offs[:-1]}
        self.pal_dict_entry = self._pal_dict_entries()
        self.used = self._used_indices()

    def _used_indices(self):
        """Palette name -> indices referenced by texels. Stock palettes pad unused slots with white."""
        used = {}
        for t in self.texs:
            pal = PAL_OF_TEX.get(t["name"], t["name"].replace("dun_wallsp1", "wallsp1"))
            if pal not in self.pal_off or t["fmt"] not in (2, 3, 4):
                continue
            bpp = {2: 2, 3: 4, 4: 8}[t["fmt"]]
            per = 8 // bpp
            a = self.info["texData"] + t["off"]
            s = used.setdefault(pal, set())
            for i in range(t["w"] * t["h"]):
                s.add((self.tex[a + i // per] >> ((i % per) * bpp)) & ((1 << bpp) - 1))
        return used

    def _pal_dict_entries(self):
        base = self.t + self.info["plInfo"]
        n = self.d[base + 1]
        dh = base + struct.unpack_from("<H", self.d, base + 6)[0]
        esz = struct.unpack_from("<H", self.d, dh)[0]
        names = dh + struct.unpack_from("<H", self.d, dh + 2)[0]
        out = {}
        for i in range(n):
            nm = bytes(self.d[names + 16 * i:names + 16 * i + 16]).rstrip(b"\0").decode("latin1")
            out[nm] = dh + 4 + i * esz
        return out

    def pal_addr(self, name):
        return self.t + self.info["plData"] + self.pal_off[name]

    def get_pal(self, name):
        a = self.pal_addr(name)
        n = self.pal_len[self.pal_off[name]]
        return [rgb(struct.unpack_from("<H", self.d, a + 2 * i)[0]) for i in range(n)]

    def set_pal(self, name, colours):
        a = self.pal_addr(name)
        for i, c in enumerate(colours):
            struct.pack_into("<H", self.d, a + 2 * i, make_lava.bgr555(c))

    def set_texels(self, name, data):
        t = next(x for x in self.texs if x["name"] == name)
        size = t["w"] * t["h"] // 2
        assert t["fmt"] == 3 and len(data) == size, name
        a = self.t + self.info["texData"] + t["off"]
        self.d[a:a + size] = data

    def rename_tex(self, old, new):
        """Renames a texture dictionary entry in place and checks the patricia tree still finds every name."""
        nodes, names, offs = nnsdict.parse(self.d, self.t + self.info["texInfo"])
        i = names.index(old.encode().ljust(16, b"\0"))
        self.d[offs[i]:offs[i] + 16] = new.ljust(16, b"\0")
        names[i] = new.ljust(16, b"\0")
        assert all(nnsdict.lookup(nodes, names, n.rstrip(b"\0")) == k for k, n in enumerate(names)), new
        for t in self.texs:
            if t["name"] == old:
                t["name"] = new.decode()

    def append_pal(self, name, colours):
        """Appends a palette to the end of TEX0 and repoints name's dictionary entry at it."""
        pal_size_o = self.t + 0x30
        old = struct.unpack_from("<H", self.d, pal_size_o)[0] << 3
        assert self.t + self.info["plData"] + old == len(self.d), "palette block is not at the end of the file"
        blob = b"".join(struct.pack("<H", make_lava.bgr555(c)) for c in colours)
        assert len(blob) % 8 == 0
        self.d += blob
        struct.pack_into("<H", self.d, pal_size_o, (old + len(blob)) >> 3)
        struct.pack_into("<I", self.d, self.t + 4, len(self.d) - self.t)  # TEX0 block size
        struct.pack_into("<I", self.d, 8, len(self.d))                    # BTX0 file size
        struct.pack_into("<H", self.d, self.pal_dict_entry[name], old >> 3)
        self.pal_off[name] = old
        self.pal_len[old] = len(colours)


def recolour(ts):
    for stops, names in GROUPS:
        # normalise luminance over the whole group so relative brightness between textures survives
        entries = []
        for nm in names:
            pal = ts.get_pal(nm)
            for i in ts.used.get(nm, range(len(pal))):
                if i == 0 and nm in TRANSPARENT0:
                    continue
                if nm in GLOW_PALS and lum(pal[i]) >= GLOW_LO:
                    continue
                entries.append(lum(pal[i]))
        lo, hi = min(entries), max(entries)
        glow_hi = max([lum(c) for nm in names if nm in GLOW_PALS for c in ts.get_pal(nm)] or [255])
        for nm in names:
            out = []
            for i, c in enumerate(ts.get_pal(nm)):
                if i == 0 and nm in TRANSPARENT0:
                    out.append(c)
                elif nm in GLOW_PALS and lum(c) >= GLOW_LO:
                    out.append(ramp((lum(c) - GLOW_LO) / (glow_hi - GLOW_LO), GLOW))
                else:
                    out.append(ramp((lum(c) - lo) / (hi - lo or 1), stops))
            ts.set_pal(nm, out)


def build():
    ts = TexSet(open(SRC, "rb").read())
    recolour(ts)
    ts.set_texels("dun_sea", make_lava.texels_4bpp(make_lava.frames()[0]))
    ts.append_pal("dun_sea", make_lava.palette())
    ts.set_texels("dun_sside", make_lava.texels_4bpp(make_lava.shore_texels()))
    ts.set_pal("seaside3", make_lava.shore_palette(ts.get_pal("seaside3")[0]))
    ts.set_pal("dun_light", [LIGHT] * len(ts.get_pal("dun_light")))
    ts.rename_tex("dun_sea", LAVA_TEX)
    with open(DST, "wb") as f:
        f.write(ts.d)
    return DST


def contact_sheet(out_path):
    from PIL import Image

    names = ["dun_allpeak", "dun_dhole2", "dun_ent", "dun_floor", "dun_floor2", "dun_hanger", "dun_imped",
             "dun_level", "dun_sea", "dun_sside", "dun_srock", "dun_step", "dun_jump", "dun_wall_c", "dun_wall_e",
             "dun_wall_n", "dun_wall_s", "dun_wall_w"]
    cell = 136
    sheet = Image.new("RGBA", (len(names) * cell, 2 * cell), (96, 96, 96, 255))
    for row, path in enumerate((SRC, DST)):
        tex, info, texs, pals = btx.load(path)
        pals = dict(pals)
        for i, nm in enumerate(names):
            if nm == "dun_sea" and path == DST:
                nm = LAVA_TEX.decode()
            t = next(x for x in texs if x["name"] == nm)
            px = btx.decode(tex, info, t, pals[PAL_OF_TEX.get(nm, nm)])
            im = Image.new("RGBA", (t["w"], t["h"]))
            im.putdata([c for r in px for c in r])
            s = 128 // max(t["w"], t["h"])
            sheet.alpha_composite(im.resize((t["w"] * s, t["h"] * s), Image.NEAREST), (i * cell, row * cell))
    sheet.save(out_path)


def main():
    path = build()
    print(f"wrote {os.path.relpath(path, ROOT)}")
    if "--sheet" in sys.argv:
        out_dir = os.environ.get("OUT_DIR", "/tmp/coronet_lava")
        os.makedirs(out_dir, exist_ok=True)
        contact_sheet(os.path.join(out_dir, "set074_sheet.png"))
        print(f"wrote {out_dir}/set074_sheet.png")


if __name__ == "__main__":
    main()

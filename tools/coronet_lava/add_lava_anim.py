"""Registers the animated lava with the field texture animator. See docs/coronet_1f_lava/PLAN.md, Step 4.

Usage: python3 tools/coronet_lava/add_lava_anim.py  (safe to re-run)

fldtanime.narc member 0 lists {char name[16]; u8 frames[18][2]} entries, one per animated texture, as
(frame index, duration in VBlanks) pairs ending in 0xff. On map load every entry whose name is found in the
map's texture set gets member index+1, an NSBTX of frames, copied over that texture's texels by index.

Stock entry 9 animates any texture named dun_sea with water frames, so the lava texture is renamed dun_mag
(make_texset.py renames it in set 074; this script renames the material binding in map 351's model) and a new
dun_mag entry plus lava frame NSBTX is appended.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import make_lava  # noqa: E402
import narc  # noqa: E402
import nnsdict  # noqa: E402

ROOT = os.path.join(HERE, "..", "..")
FLDTANIME = os.path.join(ROOT, "res/prebuilt/data/fldtanime.narc")
MAP = os.path.join(ROOT, "res/field/maps/data/map_data_351.bin")
NAME = b"dun_mag"
ENTRY_SIZE = 16 + 18 * 2

# NNS texImageParam for a 16x16 format-3 texture, minus the address bits; extra param copied from stock frames
TEX_PARAM = (3 << 26) | (1 << 20) | (1 << 23)
TEX_EXTRA = 0x80008010


def frame_btx(frames, pal):
    texels = b"".join(make_lava.texels_4bpp(f) for f in frames)
    names = [NAME + b".%d" % (i + 1) for i in range(len(frames))]
    tex_dict = nnsdict.build(names, [struct.pack("<II", TEX_PARAM | (i * 128 >> 3), TEX_EXTRA)
                                     for i in range(len(frames))])
    pal_dict = nnsdict.build([NAME], [b"\0\0\0\0"])
    pal_data = b"".join(struct.pack("<H", make_lava.bgr555(c)) for c in pal)

    tex_dict_o = 0x3C
    pal_dict_o = tex_dict_o + len(tex_dict)
    tex_data_o = pal_dict_o + len(pal_dict)
    pal_data_o = tex_data_o + len(texels)
    size = pal_data_o + len(pal_data)
    tex0 = struct.pack("<4sII", b"TEX0", size, 0)
    tex0 += struct.pack("<HHII", len(texels) >> 3, tex_dict_o, 0, tex_data_o)
    tex0 += struct.pack("<IHHIII", 0, 0, tex_dict_o, 0, pal_data_o, pal_data_o)
    tex0 += struct.pack("<IHHII", 0, len(pal_data) >> 3, 0, pal_dict_o, pal_data_o)
    assert len(tex0) == tex_dict_o
    tex0 += tex_dict + pal_dict + texels + pal_data
    return struct.pack("<4sHHIHHI", b"BTX0", 0xFEFF, 1, 0x14 + len(tex0), 0x10, 1, 0x14) + tex0


def update_fldtanime():
    header, btnf, files = narc.read_files(FLDTANIME)
    table = bytearray(files[0])
    count = struct.unpack_from("<I", table, 0)[0]
    names = [bytes(table[4 + i * ENTRY_SIZE:20 + i * ENTRY_SIZE]).rstrip(b"\0") for i in range(count)]
    frames = make_lava.frames()
    assert len(frames) < 18
    entry = bytearray(NAME.ljust(16, b"\0") + b"\xff" * 36)
    for i in range(len(frames)):
        entry[16 + 2 * i:18 + 2 * i] = bytes((i, make_lava.FRAME_VBLANKS))
    if NAME in names:
        idx = names.index(NAME)
        table[4 + idx * ENTRY_SIZE:4 + (idx + 1) * ENTRY_SIZE] = entry
    else:
        idx = count
        table[4 + count * ENTRY_SIZE:4 + count * ENTRY_SIZE] = entry
        struct.pack_into("<I", table, 0, count + 1)
        assert len(files) == count + 1, "member count does not match the animation table"
        files.append(b"")
    files[0] = bytes(table)
    files[idx + 1] = frame_btx(frames, make_lava.palette())
    narc.write_files(FLDTANIME, header, btnf, files)
    return idx


def rename_map_texture():
    """Renames the dun_sea texture binding (not the palette one) in the map model's material dictionaries."""
    d = bytearray(open(MAP, "rb").read())
    old, new = b"dun_sea".ljust(16, b"\0"), NAME.ljust(16, b"\0")
    hits = [i for i in range(len(d) - 15) if d[i:i + 16] in (old, new)]
    # the texture-to-material dictionary precedes the palette-to-material one
    assert len(hits) == 2 and d[hits[1]:hits[1] + 16] == old, hits
    d[hits[0]:hits[0] + 16] = new
    open(MAP, "wb").write(d)


def main():
    idx = update_fldtanime()
    rename_map_texture()
    print(f"fldtanime entry {idx} = {NAME.decode()}, member {idx + 1}; map_data_351 binds {NAME.decode()}")


if __name__ == "__main__":
    main()

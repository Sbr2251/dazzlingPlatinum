"""Generic BTX0 dumper for Platinum mmodel members (read-only use of the repo)."""
import struct, re
from pathlib import Path

REPO = Path('/data/repos/dazzlingPlatinum')
MM = REPO / 'res/prebuilt/data/mmodel/mmodel'

def u16(d, o): return struct.unpack_from('<H', d, o)[0]
def u32(d, o): return struct.unpack_from('<I', d, o)[0]

def info_block(d, off):
    count = d[off + 1]
    # header: dummy(1) count(1) size(2), then unknown block (8 + 4*count), then data block (2+2 + n*unit), then names
    p = off + 4
    p += 8 + 4 * count
    unit = u16(d, p); p += 4
    entries = [d[p + i * unit: p + (i + 1) * unit] for i in range(count)]
    p += unit * count
    names = [d[p + 16 * i: p + 16 * (i + 1)].rstrip(b'\0').decode('latin1') for i in range(count)]
    return entries, names

def bgr(v):
    return ((v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, ((v >> 10) & 31) * 255 // 31)

def load(member):
    d = (MM / f'mmodel_{member:08d}.bin').read_bytes()
    assert d[:4] == b'BTX0'
    tex0 = u32(d, 16)
    ti = tex0 + u16(d, tex0 + 14)
    tb = tex0 + u32(d, tex0 + 20)
    pi = tex0 + u32(d, tex0 + 52)
    pb = tex0 + u32(d, tex0 + 56)
    ents, names = info_block(d, ti)
    pents, pnames = info_block(d, pi)
    pal_off = pb + (u16(pents[0], 0) << 3)
    pal = [bgr(u16(d, pal_off + 2 * i)) if pal_off + 2*i + 2 <= len(d) else (0,0,0) for i in range(16)]
    texs = []
    for n, e in zip(names, ents):
        p = u32(e, 0)
        w = 8 << ((p >> 20) & 7); h = 8 << ((p >> 23) & 7); fmt = (p >> 26) & 7
        st = tb + ((p & 0xFFFF) << 3)
        px = []
        if fmt == 3:
            for b in d[st: st + w * h // 2]:
                px += [b & 15, b >> 4]
        texs.append((n, w, h, fmt, px))
    def key(t):
        m = re.search(r'\.(\d+)$', t[0]); return int(m.group(1)) if m else 0
    texs.sort(key=key)
    return texs, pal, pnames

def gfx_member_map():
    names = (REPO / 'generated/object_events_gfx.txt').read_text().split()
    src = (REPO / 'src/overlay005/ov5_021FAF40.c').read_text()
    out = {}
    for m in re.finditer(r'\{\s*(OBJ_EVENT_GFX_\w+|0x[0-9A-Fa-f]+),\s*(0x[0-9A-Fa-f]+)\s*\}', src):
        k = m.group(1)
        if k.startswith('0x'):
            continue
        out.setdefault(k, int(m.group(2), 16))
    return out

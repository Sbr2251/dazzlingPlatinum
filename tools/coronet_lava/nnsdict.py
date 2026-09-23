"""NNS G3D resource dictionaries (NNSG3dResDict): patricia-tree name lookup plus a fixed-size entry block.

Layout: u8 revision, u8 count, u16 size, u16 0x08, u16 entry-block offset, then count+1 tree nodes
{u8 refBit, u8 left, u8 right, u8 entry}, then the entry block: u16 unit size, u16 name offset,
count * unit bytes of entry data, count * 16-byte zero-padded names.
Names are compared as four little-endian u32s; bit b is (word[b >> 5] >> (b & 31)) & 1.
"""
import struct


def bit(name, b):
    v = struct.unpack("<4I", name.ljust(16, b"\0"))
    return (v[b >> 5] >> (b & 31)) & 1


def parse(d, o):
    """Returns (nodes, names, name_offsets) for the dictionary at offset o of d."""
    n = d[o + 1]
    nodes = [tuple(d[o + 8 + 4 * i:o + 12 + 4 * i]) for i in range(n + 1)]
    eb = o + struct.unpack_from("<H", d, o + 6)[0]
    names_o = eb + struct.unpack_from("<H", d, eb + 2)[0]
    names = [bytes(d[names_o + 16 * i:names_o + 16 * i + 16]) for i in range(n)]
    return nodes, names, [names_o + 16 * i for i in range(n)]


def lookup(nodes, names, name):
    """Entry index for name, as NNS_G3dGetResDictIdxByName would find it, or None."""
    name = name.ljust(16, b"\0")
    root = nodes[0]
    if not root[1]:
        return None
    x = nodes[root[1]]
    while True:
        prev = x[0]
        x = nodes[x[2] if bit(name, x[0]) else x[1]]
        if prev <= x[0]:
            break
    return x[3] if names[x[3]] == name else None


def _tree(names):
    nodes = [[0x7F, 0, 0, 0]]
    keys = [n.ljust(16, b"\0") for n in names]

    def descend(k, stop):
        p, x = 0, nodes[0][1]
        while nodes[p][0] > nodes[x][0] and nodes[x][0] > stop:
            p, x = x, nodes[x][2] if bit(k, nodes[x][0]) else nodes[x][1]
        return p, x

    for i, k in enumerate(keys):
        _, leaf = descend(k, -1)
        other = keys[nodes[leaf][3]] if leaf else b"\0" * 16
        b = next(b for b in range(127, -1, -1) if bit(k, b) != bit(other, b))
        p, x = descend(k, b)
        t = len(nodes)
        nodes.append([b, t, x, i] if bit(k, b) == 0 else [b, x, t, i])
        if nodes[t][1] == t:
            nodes[t][1], nodes[t][2] = t, x
        else:
            nodes[t][1], nodes[t][2] = x, t
        if p == 0:
            nodes[0][1] = t
        elif bit(k, nodes[p][0]):
            nodes[p][2] = t
        else:
            nodes[p][1] = t
    return nodes


def build(names, entries):
    """Serialises a dictionary; entries are equal-length byte strings, one per name."""
    unit = len(entries[0])
    assert all(len(e) == unit for e in entries) and len(names) == len(entries)
    nodes = _tree(names)
    ofs_entry = 8 + 4 * len(nodes)
    size = ofs_entry + 4 + unit * len(names) + 16 * len(names)
    out = struct.pack("<BBHHH", 0, len(names), size, 8, ofs_entry)
    out += b"".join(bytes(n) for n in nodes)
    out += struct.pack("<HH", unit, 4 + unit * len(names))
    out += b"".join(entries)
    out += b"".join(n.ljust(16, b"\0") for n in names)
    return out

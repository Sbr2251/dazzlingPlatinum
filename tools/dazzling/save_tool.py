#!/usr/bin/env python3
"""Inspect and edit Dazzling Platinum saves (raw 512 KB .sav / save.bin, or a DeSmuME .dsv) for testing.

    save_tool.py info  <save>
    save_tool.py edit  <save> -o <out.sav> [--lead SLOT] [--held SLOT:ITEM_X ...] [--give ITEM_X:QTY ...]

SLOT is 1-6 (party order). Edits apply to both save copies and re-sign them (Pokemon checksums, block CRCs).
Item and species names come from generated/items.txt and generated/species.txt; an item's pocket from
res/items/data/<name>.json.
"""
import argparse
import json
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FLASH = 0x80000
REGION = 0x40000  # primary copy at 0, backup at 0x40000
SIGNATURE = 0x20060623
GENERAL_SIZE = 0xCF2C  # general block, footer in its last 20 bytes
MON_SIZE = 236
POCKETS = [('items', 165), ('keyItems', 50), ('tmHms', 100), ('mail', 12), ('medicine', 40), ('berries', 64),
           ('pokeballs', 15), ('battleItems', 30)]
POCKET_OF = {'POCKET_ITEMS': 'items', 'POCKET_KEY_ITEMS': 'keyItems', 'POCKET_TMHMS': 'tmHms', 'POCKET_MAIL': 'mail',
             'POCKET_MEDICINE': 'medicine', 'POCKET_BERRIES': 'berries', 'POCKET_BALLS': 'pokeballs',
             'POCKET_BATTLE_ITEMS': 'battleItems'}
ORDERS = ['ABCD', 'ABDC', 'ACBD', 'ACDB', 'ADBC', 'ADCB', 'BACD', 'BADC', 'BCAD', 'BCDA', 'BDAC', 'BDCA',
          'CABD', 'CADB', 'CBAD', 'CBDA', 'CDAB', 'CDBA', 'DABC', 'DACB', 'DBAC', 'DBCA', 'DCAB', 'DCBA']


def names(path):
    return [l.strip() for l in open(os.path.join(ROOT, path)) if l.strip()]


ITEMS = names('generated/items.txt')
SPECIES = names('generated/species.txt')


def item_id(name):
    name = name if name.startswith('ITEM_') else 'ITEM_' + name.upper()
    return ITEMS.index(name)


def item_name(i):
    return ITEMS[i] if 0 <= i < len(ITEMS) else f'item {i}'


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def prng_xor(data, seed):
    out = bytearray(data)
    for i in range(0, len(out), 2):
        seed = (0x41C64E6D * seed + 0x6073) & 0xFFFFFFFF
        w = struct.unpack_from('<H', out, i)[0] ^ (seed >> 16)
        struct.pack_into('<H', out, i, w)
    return out


class Mon:
    def __init__(self, raw):
        self.pid, _, self.checksum = struct.unpack_from('<IHH', raw, 0)
        blocks = prng_xor(raw[8:136], self.checksum)
        order = ORDERS[((self.pid >> 13) & 31) % 24]
        self.blocks = {order[i]: bytearray(blocks[i * 32:(i + 1) * 32]) for i in range(4)}
        self.party = prng_xor(raw[136:MON_SIZE], self.pid)
        self.head = bytearray(raw[0:8])

    def valid(self):
        data = b''.join(self.blocks[c] for c in 'ABCD')
        return self.pid != 0 and sum(struct.unpack('<64H', data)) & 0xFFFF == self.checksum

    species = property(lambda s: struct.unpack_from('<H', s.blocks['A'], 0)[0])
    held = property(lambda s: struct.unpack_from('<H', s.blocks['A'], 2)[0])
    level = property(lambda s: s.party[4])

    def set_held(self, item):
        struct.pack_into('<H', self.blocks['A'], 2, item)

    def encode(self):
        data = b''.join(self.blocks[c] for c in 'ABCD')
        self.checksum = sum(struct.unpack('<64H', data)) & 0xFFFF
        struct.pack_into('<H', self.head, 6, self.checksum)
        order = ORDERS[((self.pid >> 13) & 31) % 24]
        shuffled = b''.join(self.blocks[order[i]] for i in range(4))
        return bytes(self.head) + bytes(prng_xor(shuffled, self.checksum)) + bytes(prng_xor(self.party, self.pid))


def load(path):
    data = open(path, 'rb').read()
    if data.endswith(b'|-DESMUME SAVE-|'):
        data = data[:-122]
    data = bytearray(data[:FLASH].ljust(FLASH, b'\xff'))
    return data


def regions(data):
    out = []
    for base in (0, REGION):
        foot = base + GENERAL_SIZE - 20
        counter, _, size, sig = struct.unpack_from('<IIII', data, foot)
        if sig == SIGNATURE and size == GENERAL_SIZE:
            ok = crc16(data[base:foot]) == struct.unpack_from('<H', data, foot + 18)[0]
            out.append((base, counter, ok))
    return out


def find_party(data, base):
    for off in range(base, base + 0x400, 4):
        cap, count = struct.unpack_from('<ii', data, off)
        if cap == 6 and 1 <= count <= 6 and Mon(data[off + 8:off + 8 + MON_SIZE]).valid():
            return off, count
    raise SystemExit(f'no party found in the copy at {base:#x}')


def bag_pockets(data, party_off):
    off = party_off + 8 + 6 * MON_SIZE
    pockets = {}
    for name, n in POCKETS:
        pockets[name] = (off, n)
        off += 4 * n
    return pockets


def info(data):
    for base, counter, ok in regions(data):
        print(f'copy at {base:#07x}: save counter {counter}, checksum {"OK" if ok else "BAD"}')
        party, count = find_party(data, base)
        for i in range(count):
            m = Mon(data[party + 8 + i * MON_SIZE:party + 8 + (i + 1) * MON_SIZE])
            print(f'  {i + 1}. {SPECIES[m.species]:22s} Lv{m.level:3d}  holds {item_name(m.held) if m.held else "-"}')
        pockets = bag_pockets(data, party)
        for name in ('keyItems', 'items'):
            off, n = pockets[name]
            got = [(item_name(i), q) for i, q in (struct.unpack_from('<HH', data, off + 4 * k) for k in range(n)) if i]
            interesting = [f'{a} x{q}' for a, q in got if name == 'keyItems' or a.endswith('ITE') or 'STONE' in a]
            print(f'  {name}: {", ".join(interesting) or "-"}')


def edit(data, lead, held, give):
    for base, _, _ in regions(data):
        party, count = find_party(data, base)
        mons = [data[party + 8 + i * MON_SIZE:party + 8 + (i + 1) * MON_SIZE] for i in range(count)]
        if lead:
            mons.insert(0, mons.pop(lead - 1))
        for slot, item in held:
            m = Mon(mons[slot - 1]); m.set_held(item); mons[slot - 1] = m.encode()
        for i, raw in enumerate(mons):
            data[party + 8 + i * MON_SIZE:party + 8 + (i + 1) * MON_SIZE] = raw
        pockets = bag_pockets(data, party)
        for item, qty in give:
            stem = ITEMS[item][5:].lower()
            pocket = POCKET_OF[json.load(open(os.path.join(ROOT, 'res/items/data', stem + '.json')))['fieldPocket']]
            off, n = pockets[pocket]
            slots = [struct.unpack_from('<HH', data, off + 4 * k) for k in range(n)]
            k = next((k for k, (i, _) in enumerate(slots) if i == item), None)
            if k is None:
                k = next(k for k, (i, _) in enumerate(slots) if i == 0)
            struct.pack_into('<HH', data, off + 4 * k, item, qty)
        foot = base + GENERAL_SIZE - 20
        struct.pack_into('<H', data, foot + 18, crc16(data[base:foot]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['info', 'edit'])
    ap.add_argument('save')
    ap.add_argument('-o', '--out')
    ap.add_argument('--lead', type=int)
    ap.add_argument('--held', action='append', default=[])
    ap.add_argument('--give', action='append', default=[])
    a = ap.parse_args()
    data = load(a.save)
    if a.cmd == 'info':
        info(data)
        return
    if not a.out:
        sys.exit('edit needs -o')
    held = [(int(s), item_id(i)) for s, i in (h.split(':') for h in a.held)]
    give = [(item_id(i), int(q)) for i, q in (g.split(':') for g in a.give)]
    edit(data, a.lead, held, give)
    open(a.out, 'wb').write(data)
    info(data)


if __name__ == '__main__':
    main()
